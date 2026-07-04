"""Fraud signal data models."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, List


class RiskLevel(Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of fraud alerts."""
    VELOCITY_EXCEEDED = "velocity_exceeded"
    AMOUNT_ANOMALY = "amount_anomaly"
    CARD_NOT_PRESENT_MISMATCH = "card_not_present_mismatch"
    UNUSUAL_LOCATION = "unusual_location"
    DEVICE_FINGERPRINT_MISMATCH = "device_fingerprint_mismatch"
    BIN_BLACKLIST = "bin_blacklist"
    THREE_D_SECURE_FAILURE = "three_d_secure_failure"
    VELOCITY_BY_CARD = "velocity_by_card"
    VELOCITY_BY_IP = "velocity_by_ip"
    DUPLICATE_TRANSACTION = "duplicate_transaction"
    ML_PREDICTION = "ml_prediction"


class CaseDecision(Enum):
    """Fraud case decision outcomes."""
    APPROVE = "approve"
    DECLINE = "decline"
    REVIEW = "review"
    CHALLENGE = "challenge"
    BLOCK = "block"


class CaseStatus(Enum):
    """Status of a fraud case."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


@dataclass
class FraudSignal:
    """Represents a fraud signal emitted by the fraud engine."""
    
    transaction_id: str
    risk_score: Decimal
    risk_level: RiskLevel
    alerts: List[AlertType] = field(default_factory=list)
    decision: CaseDecision = CaseDecision.APPROVE
    case_status: CaseStatus = CaseStatus.PENDING
    case_id: Optional[str] = None
    merchant_id: str = ""
    customer_id: str = ""
    amount: Decimal = Decimal("0.00")
    currency: str = "USD"
    ml_scores: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate fraud signal data."""
        if not (Decimal("0") <= self.risk_score <= Decimal("1")):
            raise ValueError("Risk score must be between 0 and 1")
        if self.amount < 0:
            raise ValueError("Amount must be non-negative")
    
    def is_high_risk(self) -> bool:
        """Check if this signal indicates high risk."""
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    
    def should_decline(self) -> bool:
        """Check if the decision is to decline the transaction."""
        return self.decision in (CaseDecision.DECLINE, CaseDecision.BLOCK)
    
    def to_dict(self) -> Dict:
        """Convert signal to dictionary (for Kafka serialization)."""
        return {
            "transaction_id": self.transaction_id,
            "risk_score": str(self.risk_score),
            "risk_level": self.risk_level.value,
            "alerts": [alert.value for alert in self.alerts],
            "decision": self.decision.value,
            "case_status": self.case_status.value,
            "case_id": self.case_id,
            "merchant_id": self.merchant_id,
            "customer_id": self.customer_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "ml_scores": self.ml_scores,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
