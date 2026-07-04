"""Payment validation logic."""

from decimal import Decimal
from src.models import PaymentMethod


class PaymentValidator:
    """Validates payment data and business rules."""
    
    MIN_AMOUNT = Decimal("0.01")
    MAX_AMOUNT = Decimal("999999.99")
    VALID_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD"}
    
    @classmethod
    def validate_amount(cls, amount: Decimal) -> bool:
        """Validate payment amount."""
        if not isinstance(amount, Decimal):
            return False
        return cls.MIN_AMOUNT <= amount <= cls.MAX_AMOUNT
    
    @classmethod
    def validate_currency(cls, currency: str) -> bool:
        """Validate currency code."""
        return currency.upper() in cls.VALID_CURRENCIES
    
    @classmethod
    def validate_payment_method(cls, method: PaymentMethod) -> bool:
        """Validate payment method."""
        return isinstance(method, PaymentMethod)
    
    @classmethod
    def validate_ids(cls, merchant_id: str, customer_id: str) -> bool:
        """Validate merchant and customer IDs."""
        return bool(merchant_id and customer_id and len(merchant_id) > 0 and len(customer_id) > 0)
