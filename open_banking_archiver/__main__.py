import logging
import time
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from sys import stdout
from typing import Any
from uuid import uuid4

import click
import requests
from open_banking_archiver.config import resolve_config
from open_banking_archiver.db import DB
from open_banking_archiver.email import Email
from open_banking_archiver.logging import CLIFormatter, StreamHandler
from open_banking_archiver.model import (
    Account,
    Bank,
    ProviderType,
    Transaction,
    TransactionState,
)
from open_banking_archiver.open_banking_client import OPEN_BANKING_CLIENT
from tabulate import tabulate

logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", is_flag=True)
@click.option("--log-format", type=click.Choice(["cli", "formatted"], case_sensitive=False), default="cli")
@click.option(
    "--log-level", type=click.Choice(list(logging.getLevelNamesMapping().keys()), case_sensitive=False), default="INFO"
)
def cli(verbose: bool, log_format: str, log_level: str) -> None:
    log_level_no = logging.getLevelNamesMapping()[log_level]

    if log_format == "cli":
        handler = StreamHandler()
        handler.setFormatter(CLIFormatter())
        logging.basicConfig(
            handlers=(handler,),
            level=logging.DEBUG if verbose else logging.INFO,
        )
    else:
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            handlers=(logging.StreamHandler(stdout),),
            level=log_level_no,
        )


@cli.group()
def ls() -> None:
    ...


@click.command()
def list_accounts() -> None:
    accounts = sorted(DB.get_accounts(), key=lambda x: x.id)
    bank_ids = tuple(account.bank_id for account in accounts)
    banks = DB.get_banks_by_ids(bank_ids)
    print(
        tabulate(
            tuple(
                (
                    account.id,
                    account.name,
                    account.external_id,
                    bank.name if (bank := banks.get(account.bank_id)) else "Not Found",
                )
                for account in accounts
            ),
            headers=("ID", "Name", "External ID", "Bank Name"),
            tablefmt="grid",
        )
    )


ls.add_command(list_accounts, "accounts")


@click.command()
def list_banks() -> None:
    banks = sorted(DB.get_banks(), key=lambda x: x.name)
    print(
        tabulate(
            tuple(
                (bank.id, bank.name, bank.external_id, bank.active_requisition_id, bank.provider_type.name)
                for bank in banks
            ),
            headers=("ID", "Name", "External ID", "Active Requisition ID", "Provider Type"),
            tablefmt="grid",
        )
    )


ls.add_command(list_banks, "banks")


@cli.group()
def sync() -> None:
    ...


@click.command()
def sync_banks() -> None:
    logger.debug("Retrieving list of banks from Nordigen")
    OPEN_BANKING_CLIENT.refresh_token()
    banks = tuple(
        Bank(id=0, name=response["name"], external_id=response["id"], provider_type=ProviderType.open_banking)
        for response in OPEN_BANKING_CLIENT.institution.get_institutions()
    )
    logger.debug("Retrieved %d banks from Nordigen", len(banks))
    DB.upsert_banks(banks)
    logger.info("Synced %d banks to the database", len(banks))


sync.add_command(sync_banks, "banks")


@click.command()
def sync_accounts() -> None:
    banks = tuple(bank for bank in DB.get_banks() if bank.active_requisition_id)
    OPEN_BANKING_CLIENT.refresh_token()

    count = 0
    for bank in banks:
        requisition = OPEN_BANKING_CLIENT.requisition.get_requisition_by_id(bank.active_requisition_id)
        if requisition["status"] != "LN":
            continue

        for account_id in requisition["accounts"]:
            count += 1
            details = OPEN_BANKING_CLIENT.account_api(account_id).get_details()["account"]
            account = Account(
                id=0,
                bank_id=bank.id,
                name=details["details"],
                external_id=details["resourceId"],
            )
            DB.upsert_account(account)

    logger.info("Synced %d accounts to the database", count)


sync.add_command(sync_accounts, "accounts")


def parse_transactions_response(account: Account, response: dict[str, Any]) -> tuple[Transaction, ...]:
    results: list[Transaction] = []
    current_booking_time = datetime(1900, 1, 1)
    sequence_number = 1

    for objs, state in (
        (reversed(response["booked"]), TransactionState.booked),
        (reversed(response["pending"]), TransactionState.pending),
    ):
        for obj in objs:
            if "transactionId" not in obj:
                continue

            booking_time = datetime.fromisoformat(obj["bookingDateTime"])
            if booking_time == current_booking_time:
                sequence_number += 1
            else:
                sequence_number = 1

            current_booking_time = booking_time

            source_amount: str | None = obj.get("currencyExchange", {}).get("instructedAmount", {}).get("amount")
            rate: str | None = obj.get("currencyExchange", {}).get("exchangeRate")

            results.append(
                Transaction(
                    id=obj["transactionId"],
                    account_id=account.id,
                    booking_time=datetime.fromisoformat(obj["bookingDateTime"]),
                    sequence_number=sequence_number,
                    remittance_info=obj["remittanceInformationUnstructured"],
                    amount=Decimal(obj["transactionAmount"]["amount"]),
                    currency=obj["transactionAmount"]["currency"],
                    source_amount=Decimal(source_amount) if source_amount else None,
                    source_currency=obj.get("currencyExchange", {}).get("sourceCurrency"),
                    exchange_rate=float(rate) if rate else None,
                    source_data=obj,
                    state=state,
                    transaction_code=obj.get("proprietaryBankTransactionCode"),
                )
            )

    return tuple(results)


@click.command()
@click.option(
    "--poll-interval",
    default=0,
    help="Poll interval in seconds to sync transactions to the database",
)
def sync_transactions(poll_interval: int) -> None:
    while True:
        OPEN_BANKING_CLIENT.refresh_token()
        banks = tuple(bank for bank in DB.get_banks() if bank.active_requisition_id)
        for bank in banks:
            requisition = OPEN_BANKING_CLIENT.requisition.get_requisition_by_id(
                requisition_id=bank.active_requisition_id
            )
            if requisition["status"] == "LN":
                DB.set_activation_email_sent(bank.id, False)
            else:
                if not bank.activation_email_sent:
                    Email().send_link(resolve_config().user_email, bank, requisition["link"])

                    # Mark the bank as having its activation email sent so we
                    # don't send an email twice
                    DB.set_activation_email_sent(bank.id, True)

                continue

            for account_id in requisition["accounts"]:
                account_api = OPEN_BANKING_CLIENT.account_api(id=account_id)
                details = account_api.get_details()["account"]

                account = Account(
                    id=0,
                    bank_id=bank.id,
                    name=details["details"],
                    external_id=details["resourceId"],
                )
                account = DB.upsert_account(account)

                logger.debug("Requesting transactions for account ID %s", account_id)

                transactions_response = account_api.get_transactions()["transactions"]

                transactions = parse_transactions_response(account, transactions_response)
                DB.upsert_transactions(transactions)
                logger.info(
                    "Synced %d transactions of %s account at %s to the database",
                    len(transactions),
                    account.name,
                    bank.name,
                )

        if poll_interval > 0:
            logger.debug("Sleeping for %d seconds", poll_interval)
            time.sleep(poll_interval)
        else:
            return


sync.add_command(sync_transactions, "transactions")


@cli.command()
@click.argument("bank_name")
def link(bank_name: str) -> None:
    bank = DB.get_bank_by_name(bank_name)
    if not bank:
        logger.error("Unable to find bank with name '%s'", bank_name)
        return

    OPEN_BANKING_CLIENT.refresh_token()

    requisition: dict | None = None

    if bank.active_requisition_id:
        try:
            requisition = OPEN_BANKING_CLIENT.requisition.get_requisition_by_id(bank.active_requisition_id)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code != 404:
                raise

    if requisition:
        if requisition["status"] == "LN":
            logger.info("Link with %s already active. Link: %s", bank_name, requisition["link"])
        else:
            logger.info(
                "Link with %s exists but is not active. Unlink it first using `unlink '%s'`", bank_name, bank_name
            )
    else:
        init = OPEN_BANKING_CLIENT.initialize_session(
            redirect_uri="https://www.google.com",
            institution_id=bank.external_id,
            reference_id=str(uuid4()),
            max_historical_days=730,
            access_valid_for_days=90,
        )
        bank = replace(bank, active_requisition_id=init.requisition_id)
        DB.update_bank(bank)
        logger.info("Link: %s", init.link)


@cli.command()
@click.argument("bank_name")
def unlink(bank_name: str) -> None:
    bank = DB.get_bank_by_name(bank_name)
    if not bank:
        logger.error("Unable to find bank with name '%s'", bank_name)
        return

    OPEN_BANKING_CLIENT.refresh_token()

    requisition: dict | None = None

    if bank.active_requisition_id:
        try:
            requisition = OPEN_BANKING_CLIENT.requisition.get_requisition_by_id(bank.active_requisition_id)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code != 404:
                raise

    if requisition:
        bank = replace(bank, active_requisition_id=None)
        DB.update_bank(bank)
        logger.info("Link with %s exists and has been removed.", bank_name)
    else:
        logger.info("No link currently exists with %s", bank_name)


@cli.command()
@click.argument("bank_name")
def status(bank_name: str) -> None:
    bank = DB.get_bank_by_name(bank_name)
    if not bank:
        logger.error("Unable to find bank with name '%s'", bank_name)
        return

    requisition: dict | None = None

    if bank.active_requisition_id:
        OPEN_BANKING_CLIENT.refresh_token()

        try:
            requisition = OPEN_BANKING_CLIENT.requisition.get_requisition_by_id(bank.active_requisition_id)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code != 404:
                raise

    if requisition and requisition["status"] == "LN":
        logger.info("Link with %s: ACTIVE", bank_name)
    elif requisition:
        logger.info("Link with %s: %s", bank_name, requisition["status"])
    else:
        logger.info("Link with %s: INACTIVE", bank_name)


@cli.command()
def prune() -> None:
    requisition_ids_db = {bank.active_requisition_id for bank in DB.get_banks() if bank.active_requisition_id}

    OPEN_BANKING_CLIENT.refresh_token()
    requisitions = OPEN_BANKING_CLIENT.requisition.get_requisitions()
    requisition_ids_api = {requisition["id"] for requisition in requisitions["results"]}
    for requisition in requisitions["results"]:
        if requisition["status"] != "LN" or requisition["id"] not in requisition_ids_db:
            logger.info("Deleting requisition ID %s", requisition["id"])
            OPEN_BANKING_CLIENT.requisition.delete_requisition(requisition["id"])

    for orphan_id in requisition_ids_db.difference(requisition_ids_api):
        DB.clear_requisition_id(orphan_id)


if __name__ == "__main__":
    cli()
