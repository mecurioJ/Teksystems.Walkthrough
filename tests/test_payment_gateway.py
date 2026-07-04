"""Test suite for payment gateway."""

import pytest
from decimal import Decimal
from datetime import datetime

from src.models import Payment, PaymentMethod, PaymentStatus, Transaction, TransactionType, TransactionStatus
from src.payment import PaymentProcessor, PaymentValidator
from src.transactions import TransactionManager
from src.security import TokenizationService, EncryptionService
from src.api import PaymentAPI


class TestPaymentValidator:
    """Tests for payment validation."""
    
    def test_validate_amount_valid(self):
        """Test valid payment amounts."""
        assert PaymentValidator.validate_amount(Decimal("10.00"))
        assert PaymentValidator.validate_amount(Decimal("100000.00"))
    
    def test_validate_amount_invalid(self):
        """Test invalid payment amounts."""
        assert not PaymentValidator.validate_amount(Decimal("-10.00"))
        assert not PaymentValidator.validate_amount(Decimal("0"))
        assert not PaymentValidator.validate_amount(Decimal("9999999.99"))
    
    def test_validate_currency(self):
        """Test currency validation."""
        assert PaymentValidator.validate_currency("USD")
        assert PaymentValidator.validate_currency("EUR")
        assert not PaymentValidator.validate_currency("INVALID")


class TestPaymentProcessor:
    """Tests for payment processing."""
    
    def test_authorize_payment(self):
        """Test payment authorization."""
        processor = PaymentProcessor()
        payment = processor.authorize(
            amount=Decimal("100.00"),
            currency="USD",
            method=PaymentMethod.CREDIT_CARD,
            merchant_id="merchant_1",
            customer_id="customer_1",
        )
        
        assert payment.status == PaymentStatus.AUTHORIZED
        assert payment.amount == Decimal("100.00")
    
    def test_capture_payment(self):
        """Test payment capture."""
        processor = PaymentProcessor()
        payment = processor.authorize(
            amount=Decimal("100.00"),
            currency="USD",
            method=PaymentMethod.CREDIT_CARD,
            merchant_id="merchant_1",
            customer_id="customer_1",
        )
        
        captured = processor.capture(payment)
        assert captured.status == PaymentStatus.CAPTURED


class TestTransactionManager:
    """Tests for transaction management."""
    
    def test_create_transaction(self):
        """Test transaction creation."""
        manager = TransactionManager()
        transaction = manager.create_transaction(
            payment_id="pay_1",
            type=TransactionType.CHARGE,
            amount=Decimal("50.00"),
            currency="USD",
        )
        
        assert transaction.status == TransactionStatus.INITIATED
        assert transaction.amount == Decimal("50.00")
    
    def test_update_transaction_status(self):
        """Test transaction status update."""
        manager = TransactionManager()
        transaction = manager.create_transaction(
            payment_id="pay_1",
            type=TransactionType.CHARGE,
            amount=Decimal("50.00"),
            currency="USD",
        )
        
        updated = manager.update_status(transaction.id, TransactionStatus.COMPLETED)
        assert updated.status == TransactionStatus.COMPLETED


class TestTokenizationService:
    """Tests for payment tokenization."""
    
    def test_tokenize_and_retrieve(self):
        """Test tokenization and retrieval."""
        service = TokenizationService()
        card_number = "4532-1234-5678-9010"
        
        token = service.tokenize(card_number)
        assert token.startswith("tok_")
        assert service.retrieve(token) == card_number
    
    def test_mask_card_number(self):
        """Test card number masking."""
        service = TokenizationService()
        masked = service.mask_card_number("4532123456789010")
        assert masked.endswith("9010")
        assert "*" in masked


class TestEncryptionService:
    """Tests for encryption operations."""
    
    def test_hash_password(self):
        """Test password hashing."""
        service = EncryptionService()
        hashed = service.hash_password("password123")
        assert len(hashed) == 64  # SHA-256 hex digest length


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
