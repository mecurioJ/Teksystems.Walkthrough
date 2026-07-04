"""Payment data models."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from datetime import datetime
from typing import Optional


class PaymentMethod(Enum):
    """Supported payment methods."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ACH = "ach"
    WIRE = "wire"
    DIGITAL_WALLET = "digital_wallet"


class PaymentStatus(Enum):
    """Payment lifecycle statuses."""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    DECLINED = "declined"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


@dataclass
class Payment:
    """Represents a payment transaction."""
    id: str
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    merchant_id: str
    customer_id: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        """Validate payment data."""
        if self.amount <= 0:
            raise ValueError("Amount must be positive")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("Currency must be a valid 3-letter code")
