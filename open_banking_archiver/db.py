import logging
from contextlib import contextmanager
from typing import Collection, Generator, Iterable, Mapping, cast

from open_banking_archiver.config import Config, resolve_config
from open_banking_archiver.model import (
    Account,
    Bank,
    ProviderType,
    Transaction,
    TransactionState,
)
from psycopg import Connection
from psycopg.rows import class_row
from psycopg.types.enum import EnumInfo, register_enum
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


def create_connection_string(config: Config) -> str:
    return (
        f"host={config.db_host} port={config.db_port} user={config.db_user} "
        f"password={config.db_password} dbname={config.db_name}"
    )


class PostgresDB:
    """
    Database class that interacts with the Postgres database, constructs
    queries, and handles connections
    """

    def __init__(self, config: Config) -> None:
        self.pool = ConnectionPool(create_connection_string(config))

    @contextmanager
    def conn(self) -> Generator[Connection, None, None]:
        with self.pool.connection() as conn:
            info = EnumInfo.fetch(conn, "transaction_state")
            assert info, "The enum type 'transaction_state' must be defined in the database"
            register_enum(info, conn, TransactionState)

            info = EnumInfo.fetch(conn, "provider_type")
            assert info, "The enum type 'provider_type' must be defined in the database"
            register_enum(info, conn, ProviderType)

            yield conn

    def close(self) -> None:
        logger.info("Closing database connection")
        self.pool.close()

    def get_bank_by_name(self, name: str) -> Bank | None:
        with self.conn() as conn:
            with conn.cursor(row_factory=class_row(Bank)) as curr:
                logger.debug("Retrieving bank '%s'", name)
                curr.execute(
                    """
                SELECT id, name, external_id, active_requisition_id, provider_type
                    FROM banks
                    WHERE name = %s
                    """,
                    (name,),
                )
                return curr.fetchone()

    def get_banks_by_ids(self, ids: Iterable[int]) -> Mapping[int, Bank]:
        ids = set(ids)
        with self.conn() as conn:
            with conn.cursor(row_factory=class_row(Bank)) as curr:
                logger.debug("Retrieving banks by IDs: %s", ids)
                curr.execute(
                    """
                    SELECT id, name, external_id, active_requisition_id, provider_type
                        FROM banks
                        WHERE id IN (%s)
                    """,
                    (", ".join(str(id) for id in ids),),
                )
                return {bank.id: bank for bank in curr.fetchall()}

    def get_banks(self) -> tuple[Bank, ...]:
        with self.conn() as conn:
            with conn.cursor(row_factory=class_row(Bank)) as curr:
                logger.debug("Retrieving all banks")
                curr.execute(
                    """
                    SELECT id, name, external_id, active_requisition_id, provider_type, activation_email_sent
                        FROM banks
                    """
                )
                return tuple(curr.fetchall())

    def get_account(self, external_id: str) -> Account | None:
        with self.conn() as conn:
            with conn.cursor(row_factory=class_row(Account)) as curr:
                logger.debug("Retrieving account with external ID: %s", external_id)
                curr.execute(
                    "SELECT id, bank_id, name, external_id FROM accounts WHERE external_id = %s", (external_id,)
                )
                return curr.fetchone()

    def get_accounts(self) -> tuple[Account, ...]:
        with self.conn() as conn:
            with conn.cursor(row_factory=class_row(Account)) as curr:
                logger.debug("Retrieving all accounts")
                curr.execute("SELECT id, bank_id, name, external_id FROM accounts")
                return tuple(curr.fetchall())

    def upsert_banks(self, banks: Collection[Bank]) -> None:
        with self.conn() as conn:
            with conn.cursor() as curr:
                logger.debug("Upserting %d banks", len(banks))
                try:
                    for bank in banks:
                        curr.execute(
                            """
                            INSERT INTO banks (name, external_id, provider_type)
                                VALUES (%(name)s, %(external_id)s, %(provider_type)s)
                                ON CONFLICT (external_id) DO UPDATE
                                SET name = %(name)s, provider_type = %(provider_type)s
                            """,
                            {
                                "name": bank.name,
                                "external_id": bank.external_id,
                                "provider_type": bank.provider_type,
                            },
                        )
                    conn.commit()
                except Exception:
                    conn.rollback()

    def update_bank(self, bank: Bank) -> None:
        with self.conn() as conn:
            with conn.cursor() as curr:
                logger.debug("Updating bank '%s'", bank.name)
                try:
                    curr.execute(
                        """
                        UPDATE banks
                            SET name = %s, external_id = %s, provider_type = %s,
                                active_requisition_id = %s, activation_email_sent = %s
                            WHERE id = %s
                        """,
                        (
                            bank.name,
                            bank.external_id,
                            bank.provider_type,
                            bank.active_requisition_id,
                            bank.activation_email_sent,
                            bank.id,
                        ),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()

    def set_activation_email_sent(self, bank_id: int, activation_email_sent: bool) -> None:
        with self.conn() as conn:
            with conn.cursor() as curr:
                logger.debug("Updating bank ID %s's activation_email_sent", bank_id)
                try:
                    curr.execute(
                        """
                        UPDATE banks
                            SET activation_email_sent = %s
                            WHERE id = %s
                        """,
                        (
                            activation_email_sent,
                            bank_id,
                        ),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()

    def clear_requisition_id(self, requisition_id: str) -> None:
        with self.conn() as conn:
            with conn.cursor() as curr:
                logger.debug("Clearing requisiton ID '%s'", requisition_id)
                try:
                    curr.execute(
                        """
                        UPDATE banks
                            SET active_requisition_id = NULL
                            WHERE active_requisition_id = %s
                        """,
                        (requisition_id,),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()

    def upsert_account(self, account: Account) -> Account:
        with self.conn() as conn:
            with conn.cursor(row_factory=class_row(Account)) as curr:
                logger.debug("Upserting account with external ID: %s", account.external_id)
                try:
                    curr.execute(
                        """
                        INSERT INTO accounts (bank_id, external_id, name)
                            VALUES (%(bank_id)s, %(external_id)s, %(name)s)
                            ON CONFLICT (bank_id, external_id)
                            DO UPDATE SET name = %(name)s
                            RETURNING id, bank_id, name, external_id
                    """,
                        {
                            "bank_id": account.bank_id,
                            "external_id": account.external_id,
                            "name": account.name,
                        },
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                return cast(Account, curr.fetchone())

    def upsert_transactions(self, transactions: Collection[Transaction]) -> None:
        with self.conn() as conn:
            with conn.cursor() as curr:
                logger.debug("Upserting %d transactions", len(transactions))
                try:
                    for transaction in transactions:
                        curr.execute(
                            """
                            INSERT INTO transactions (id, account_id, booking_time, sequence_number, remittance_info,
                                    transaction_code, currency, source_currency, source_amount, amount, exchange_rate,
                                    source_data, state
                                ) VALUES (
                                    %(id)s, %(account_id)s, %(booking_time)s, %(sequence_number)s, %(remittance_info)s,
                                    %(transaction_code)s, %(currency)s, %(source_currency)s, %(source_amount)s,
                                    %(amount)s, %(exchange_rate)s, %(source_data)s, %(state)s
                                ) ON CONFLICT (id) DO UPDATE SET
                                    account_id = %(account_id)s,
                                    booking_time = %(booking_time)s,
                                    sequence_number = %(sequence_number)s,
                                    remittance_info = %(remittance_info)s,
                                    transaction_code = %(transaction_code)s,
                                    currency = %(currency)s,
                                    source_currency = %(source_currency)s,
                                    source_amount = %(source_amount)s,
                                    amount = %(amount)s,
                                    exchange_rate = %(exchange_rate)s,
                                    source_data = %(source_data)s,
                                    state = %(state)s
                        """,
                            {
                                "id": transaction.id,
                                "account_id": transaction.account_id,
                                "booking_time": transaction.booking_time,
                                "sequence_number": transaction.sequence_number,
                                "remittance_info": transaction.remittance_info,
                                "transaction_code": transaction.transaction_code,
                                "currency": transaction.currency,
                                "source_currency": transaction.source_currency,
                                "source_amount": transaction.source_amount,
                                "amount": transaction.amount,
                                "exchange_rate": transaction.exchange_rate,
                                "source_data": Jsonb(transaction.source_data),
                                "state": transaction.state,
                            },
                        )

                    conn.commit()
                except Exception:
                    logger.exception("An error occurred while inserting transactions into the database")
                    conn.rollback()
                    raise


DB = PostgresDB(resolve_config())
