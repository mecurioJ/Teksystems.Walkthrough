"""Transaction data models."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from datetime import datetime
from typing import Optional


class TransactionType(Enum):
    """Types of transactions."""
    CHARGE = "charge"
    REFUND = "refund"
    DISPUTE = "dispute"
    REVERSAL = "reversal"


class TransactionStatus(Enum):
    """Transaction processing statuses."""
    INITIATED = "initiated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclass
class Transaction:
    """Represents a transaction record."""
    id: str
    payment_id: str
    type: TransactionType
    status: TransactionStatus
    amount: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate transaction data."""
        if self.amount <= 0:
            raise ValueError("Amount must be positive")
