"""Fraud detection engine interface and implementation."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional, Dict, List
from datetime import datetime

from src.models import Payment
from .models import FraudSignal, RiskLevel, AlertType, CaseDecision, CaseStatus


class FraudEngine(ABC):
    """Abstract base class for fraud detection engines."""
    
    @abstractmethod
    def evaluate(self, payment: Payment, context: Optional[Dict] = None) -> FraudSignal:
        """
        Evaluate a payment for fraud risk.
        
        Args:
            payment: Payment object to evaluate
            context: Optional additional context (customer history, device info, etc.)
            
        Returns:
            FraudSignal with risk assessment and decision
        """
        pass


class SimpleFraudEngine(FraudEngine):
    """
    Basic fraud detection engine using simple rules and heuristics.
    
    Rules evaluated:
    - Amount threshold
    - Velocity checks
    - Basic velocity limits
    - Currency validation
    """
    
    def __init__(
        self,
        max_transaction_amount: Decimal = Decimal("10000.00"),
        velocity_limit: int = 5,
        time_window_minutes: int = 60,
    ):
        """Initialize fraud engine with configurable thresholds."""
        self.max_transaction_amount = max_transaction_amount
        self.velocity_limit = velocity_limit
        self.time_window_minutes = time_window_minutes
        self._transaction_history: List[Dict] = []
    
    def evaluate(
        self,
        payment: Payment,
        context: Optional[Dict] = None,
    ) -> FraudSignal:
        """
        Evaluate payment using simple rule-based logic.
        
        Args:
            payment: Payment to evaluate
            context: Optional context with customer/device info
            
        Returns:
            FraudSignal with assessment
        """
        context = context or {}
        alerts: List[AlertType] = []
        risk_score = Decimal("0.1")  # Base risk score
        ml_scores = {}
        
        # Check amount anomaly
        if payment.amount > self.max_transaction_amount:
            alerts.append(AlertType.AMOUNT_ANOMALY)
            risk_score += Decimal("0.3")
        
        # Check velocity
        recent_transactions = self._get_recent_transactions(
            payment.customer_id,
            self.time_window_minutes,
        )
        if len(recent_transactions) >= self.velocity_limit:
            alerts.append(AlertType.VELOCITY_EXCEEDED)
            risk_score += Decimal("0.2")
        
        # Check location mismatch (if context provided)
        if context.get("previous_location") and context.get("current_location"):
            if context["previous_location"] != context["current_location"]:
                alerts.append(AlertType.UNUSUAL_LOCATION)
                risk_score += Decimal("0.15")
        
        # Check device fingerprint (if context provided)
        if context.get("device_mismatch"):
            alerts.append(AlertType.DEVICE_FINGERPRINT_MISMATCH)
            risk_score += Decimal("0.15")
        
        # Record transaction for velocity checks
        self._transaction_history.append({
            "customer_id": payment.customer_id,
            "timestamp": datetime.utcnow(),
            "amount": payment.amount,
        })
        
        # Determine risk level and decision
        risk_level = self._score_to_risk_level(risk_score)
        decision = self._determine_decision(risk_level, alerts)
        
        # Create fraud signal
        signal = FraudSignal(
            transaction_id=payment.id,
            risk_score=min(risk_score, Decimal("1.0")),
            risk_level=risk_level,
            alerts=alerts,
            decision=decision,
            case_status=CaseStatus.PENDING,
            merchant_id=payment.merchant_id,
            customer_id=payment.customer_id,
            amount=payment.amount,
            currency=payment.currency,
            ml_scores=ml_scores,
            metadata={"engine": "simple", "context_used": bool(context)},
        )
        
        return signal
    
    def _get_recent_transactions(
        self,
        customer_id: str,
        time_window_minutes: int,
    ) -> List[Dict]:
        """Get transactions from a customer within time window."""
        cutoff = datetime.utcnow()
        recent = []
        
        for trans in self._transaction_history:
            age_minutes = (cutoff - trans["timestamp"]).total_seconds() / 60
            if age_minutes <= time_window_minutes and trans["customer_id"] == customer_id:
                recent.append(trans)
        
        return recent
    
    def _score_to_risk_level(self, score: Decimal) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score >= Decimal("0.75"):
            return RiskLevel.CRITICAL
        elif score >= Decimal("0.5"):
            return RiskLevel.HIGH
        elif score >= Decimal("0.25"):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _determine_decision(
        self,
        risk_level: RiskLevel,
        alerts: List[AlertType],
    ) -> CaseDecision:
        """Determine case decision based on risk level and alerts."""
        if risk_level == RiskLevel.CRITICAL:
            return CaseDecision.BLOCK
        elif risk_level == RiskLevel.HIGH:
            # Block if certain critical alerts present
            if AlertType.BIN_BLACKLIST in alerts or AlertType.VELOCITY_BY_IP in alerts:
                return CaseDecision.DECLINE
            return CaseDecision.REVIEW
        elif risk_level == RiskLevel.MEDIUM:
            return CaseDecision.CHALLENGE
        else:
            return CaseDecision.APPROVE


class MLFraudEngine(FraudEngine):
    """
    Machine learning-based fraud detection engine.
    
    This is a placeholder for ML model integration.
    In production, this would load and use actual ML models.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize ML fraud engine.
        
        Args:
            model_path: Path to trained ML model
        """
        self.model_path = model_path
        self._model = None
    
    def evaluate(
        self,
        payment: Payment,
        context: Optional[Dict] = None,
    ) -> FraudSignal:
        """
        Evaluate payment using ML model.
        
        Args:
            payment: Payment to evaluate
            context: Optional context
            
        Returns:
            FraudSignal with ML-based assessment
        """
        context = context or {}
        
        # In production, would:
        # 1. Extract features from payment and context
        # 2. Load ML model
        # 3. Run inference
        # 4. Interpret predictions
        
        # Placeholder implementation
        risk_score = Decimal("0.3")
        ml_scores = {
            "model_score": 0.35,
            "confidence": 0.92,
        }
        
        signal = FraudSignal(
            transaction_id=payment.id,
            risk_score=risk_score,
            risk_level=RiskLevel.MEDIUM,
            alerts=[AlertType.ML_PREDICTION],
            decision=CaseDecision.APPROVE,
            case_status=CaseStatus.PENDING,
            merchant_id=payment.merchant_id,
            customer_id=payment.customer_id,
            amount=payment.amount,
            currency=payment.currency,
            ml_scores=ml_scores,
            metadata={"engine": "ml", "model_path": self.model_path},
        )
        
        return signal
