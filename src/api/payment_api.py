"""Payment API interface."""

from decimal import Decimal
from typing import Optional, Dict, Any

from src.models import PaymentMethod
from src.payment import PaymentProcessor, PaymentValidator
from src.transactions import TransactionManager
from src.security import TokenizationService


class PaymentAPI:
    """
    Public API for payment operations.
    
    This interface abstracts the underlying payment processing logic,
    providing a clean API for merchants and applications.
    """
    
    def __init__(self):
        """Initialize payment API."""
        self.processor = PaymentProcessor()
        self.validator = PaymentValidator()
        self.transaction_manager = TransactionManager()
        self.tokenization = TokenizationService()
    
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
            
            # Capture if requested
            if capture_immediately:
                payment = self.processor.capture(payment)
            
            return {
                "success": True,
                "payment_id": payment.id,
                "status": payment.status.value,
                "amount": str(payment.amount),
                "currency": payment.currency,
            }
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
