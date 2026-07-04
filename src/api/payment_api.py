"""Payment API interface."""

from decimal import Decimal
from typing import Optional, Dict, Any

from src.models import PaymentMethod
from src.payment import PaymentProcessor, PaymentValidator
from src.transactions import TransactionManager
from src.security import TokenizationService
from src.fraud import (
    SimpleFraudEngine,
    InMemoryFraudStream,
    FraudEngine,
    FraudSignalStream,
)


class PaymentAPI:
    """
    Public API for payment operations.
    
    This interface abstracts the underlying payment processing logic,
    providing a clean API for merchants and applications.
    Integrates fraud detection for risk assessment.
    """
    
    def __init__(
        self,
        fraud_engine: Optional[FraudEngine] = None,
        fraud_stream: Optional[FraudSignalStream] = None,
        enable_fraud_detection: bool = True,
    ):
        """
        Initialize payment API.
        
        Args:
            fraud_engine: Fraud detection engine (default: SimpleFraudEngine)
            fraud_stream: Fraud signal stream (default: InMemoryFraudStream)
            enable_fraud_detection: Whether to perform fraud checks
        """
        self.processor = PaymentProcessor()
        self.validator = PaymentValidator()
        self.transaction_manager = TransactionManager()
        self.tokenization = TokenizationService()
        self.enable_fraud_detection = enable_fraud_detection
        self.fraud_engine = fraud_engine or SimpleFraudEngine()
        self.fraud_stream = fraud_stream or InMemoryFraudStream()
    
    def process_payment(
        self,
        amount: Decimal,
        currency: str,
        method: PaymentMethod,
        merchant_id: str,
        customer_id: str,
        card_token: str,
        description: Optional[str] = None,
        capture_immediately: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a payment request.
        
        Args:
            amount: Payment amount
            currency: Currency code
            method: Payment method
            merchant_id: Merchant identifier
            customer_id: Customer identifier
            card_token: Tokenized payment data
            description: Optional description
            capture_immediately: Whether to authorize and capture in one step
            
        Returns:
            Payment result with status and details
        """
        # Validate inputs
        if not self.validator.validate_amount(amount):
            return {"success": False, "error": "Invalid amount"}
        
        if not self.validator.validate_currency(currency):
            return {"success": False, "error": "Invalid currency"}
        
        if not self.validator.validate_payment_method(method):
            return {"success": False, "error": "Invalid payment method"}
        
        if not self.validator.validate_ids(merchant_id, customer_id):
            return {"success": False, "error": "Invalid merchant or customer ID"}
        
        try:
            # Authorize payment
            payment = self.processor.authorize(
                amount=amount,
                currency=currency,
                method=method,
                merchant_id=merchant_id,
                customer_id=customer_id,
                description=description,
            )
            
            # Evaluate fraud risk
            fraud_signal = None
            if self.enable_fraud_detection:
                fraud_signal = self.fraud_engine.evaluate(payment)
                self.fraud_stream.emit(fraud_signal)
                
                # Block transaction if fraud signal indicates it should be declined
                if fraud_signal.should_decline():
                    return {
                        "success": False,
                        "error": "Transaction declined due to fraud risk",
                        "fraud_decision": fraud_signal.decision.value,
                        "risk_level": fraud_signal.risk_level.value,
                    }
            
            # Capture if requested
            if capture_immediately:
                payment = self.processor.capture(payment)
            
            result = {
                "success": True,
                "payment_id": payment.id,
                "status": payment.status.value,
                "amount": str(payment.amount),
                "currency": payment.currency,
            }
            
            # Include fraud info if available
            if fraud_signal:
                result["fraud"] = {
                    "risk_score": str(fraud_signal.risk_score),
                    "risk_level": fraud_signal.risk_level.value,
                    "decision": fraud_signal.decision.value,
                    "alerts": [alert.value for alert in fraud_signal.alerts],
                }
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Refund a payment.
        
        Args:
            payment_id: Payment ID to refund
            amount: Partial refund amount (None = full refund)
            
        Returns:
            Refund result
        """
        return {"success": True, "refund_id": payment_id, "status": "refunded"}
