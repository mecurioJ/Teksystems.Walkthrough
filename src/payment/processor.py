"""Core payment processing logic."""

from decimal import Decimal
from typing import Optional
from datetime import datetime
import uuid

from src.models import Payment, PaymentStatus, PaymentMethod
from src.security import TokenizationService


class PaymentProcessor:
    """Handles payment processing operations."""
    
    def __init__(self, tokenization_service: Optional[TokenizationService] = None):
        """Initialize payment processor."""
        self.tokenization_service = tokenization_service or TokenizationService()
    
    def authorize(
        self,
        amount: Decimal,
        currency: str,
        method: PaymentMethod,
        merchant_id: str,
        customer_id: str,
        description: Optional[str] = None,
    ) -> Payment:
        """
        Authorize a payment without capturing funds.
        
        Args:
            amount: Payment amount
            currency: Currency code (ISO 4217)
            method: Payment method
            merchant_id: Merchant identifier
            customer_id: Customer identifier
            description: Optional payment description
            
        Returns:
            Authorized payment object
        """
        payment = Payment(
            id=str(uuid.uuid4()),
            amount=amount,
            currency=currency,
            method=method,
            status=PaymentStatus.AUTHORIZED,
            merchant_id=merchant_id,
            customer_id=customer_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            description=description,
        )
        return payment
    
    def capture(self, payment: Payment) -> Payment:
        """
        Capture funds from an authorized payment.
        
        Args:
            payment: Authorized payment object
            
        Returns:
            Captured payment object
        """
        if payment.status != PaymentStatus.AUTHORIZED:
            raise ValueError(f"Cannot capture payment with status: {payment.status}")
        
        payment.status = PaymentStatus.CAPTURED
        payment.updated_at = datetime.utcnow()
        return payment
    
    def refund(self, payment: Payment, amount: Optional[Decimal] = None) -> Payment:
        """
        Refund a captured payment.
        
        Args:
            payment: Captured payment to refund
            amount: Partial refund amount (None = full refund)
            
        Returns:
            Refunded payment object
        """
        if payment.status != PaymentStatus.CAPTURED:
            raise ValueError(f"Cannot refund payment with status: {payment.status}")
        
        if amount and amount > payment.amount:
            raise ValueError("Refund amount exceeds payment amount")
        
        payment.status = PaymentStatus.REFUNDED
        payment.updated_at = datetime.utcnow()
        return payment
