from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Any


@dataclass(frozen=True)
class Bank:
    id: int
    name: str
    external_id: str
    provider_type: ProviderType
    active_requisition_id: str = ""


@dataclass(frozen=True)
class Account:
    id: int
    bank_id: int
    name: str
    external_id: str


class TransactionState(Enum):
    pending = auto()
    booked = auto()


class ProviderType(Enum):
    open_banking = auto()
    monzo = auto


@dataclass(frozen=True)
class Transaction:
    id: str
    account_id: int
    booking_time: datetime
    sequence_number: int
    remittance_info: str
    transaction_code: str | None
    amount: Decimal
    currency: str
    source_amount: float | None
    source_currency: str | None
    exchange_rate: float | None
    state: TransactionState
    source_data: Any
