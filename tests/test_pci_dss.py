"""Tests for PCI-DSS data classification and tagging."""

import pytest
from src.security.pci_dss import (
    DataClassification,
    PCIDSSClassifier,
    PCIDataMasker,
    ColumnMetadata,
)


class TestDataClassification:
    """Test data classification enum."""

    def test_classification_values(self):
        """Test classification enum values."""
        assert DataClassification.PUBLIC.value == "public"
        assert DataClassification.INTERNAL.value == "internal"
        assert DataClassification.CONFIDENTIAL.value == "confidential"
        assert DataClassification.PCI_DSS_RESTRICTED.value == "pci_dss_restricted"
        assert DataClassification.PII_RESTRICTED.value == "pii_restricted"


class TestPCIDSSClassifier:
    """Test PCI-DSS classifier."""

    def test_card_number_classification(self):
        """Test card number is classified as PCI-DSS restricted."""
        result = PCIDSSClassifier.classify_column("card_number")
        assert result.classification == DataClassification.PCI_DSS_RESTRICTED
        assert result.is_masked
        assert result.mask_type == "tokenize"

    def test_pan_classification(self):
        """Test PAN field is classified as PCI-DSS restricted."""
        result = PCIDSSClassifier.classify_column("primary_account_number")
        assert result.classification == DataClassification.PCI_DSS_RESTRICTED
        assert result.is_masked

    def test_cvv_classification(self):
        """Test CVV is classified as PCI-DSS restricted."""
        result = PCIDSSClassifier.classify_column("cvv")
        assert result.classification == DataClassification.PCI_DSS_RESTRICTED
        assert result.mask_type == "tokenize"

    def test_cvc_classification(self):
        """Test CVC is classified as PCI-DSS restricted."""
        result = PCIDSSClassifier.classify_column("security_code")
        assert result.classification == DataClassification.PCI_DSS_RESTRICTED

    def test_cardholder_name_classification(self):
        """Test cardholder name is classified as PCI-DSS restricted."""
        result = PCIDSSClassifier.classify_column("cardholder_name")
        assert result.classification == DataClassification.PCI_DSS_RESTRICTED
        assert result.mask_type == "tokenize"

    def test_expiration_date_classification(self):
        """Test expiration date is classified as PCI-DSS restricted."""
        result = PCIDSSClassifier.classify_column("expiration_date")
        assert result.classification == DataClassification.PCI_DSS_RESTRICTED

    def test_pin_classification(self):
        """Test PIN is classified as PCI-DSS restricted."""
        result = PCIDSSClassifier.classify_column("pin")
        assert result.classification == DataClassification.PCI_DSS_RESTRICTED
        assert result.mask_type == "tokenize"

    def test_ssn_classification(self):
        """Test SSN is classified as PII restricted."""
        result = PCIDSSClassifier.classify_column("ssn")
        assert result.classification == DataClassification.PII_RESTRICTED
        assert result.is_masked

    def test_email_classification(self):
        """Test email is classified as PII restricted."""
        result = PCIDSSClassifier.classify_column("email")
        assert result.classification == DataClassification.PII_RESTRICTED
        assert result.mask_type == "partial"

    def test_phone_classification(self):
        """Test phone is classified as PII restricted."""
        result = PCIDSSClassifier.classify_column("phone")
        assert result.classification == DataClassification.PII_RESTRICTED
        assert result.mask_type == "partial"

    def test_public_field_classification(self):
        """Test non-sensitive field is classified as internal."""
        result = PCIDSSClassifier.classify_column("transaction_date")
        assert result.classification == DataClassification.INTERNAL
        assert not result.is_masked

    def test_amount_field_classification(self):
        """Test amount field is not PCI-DSS but is internal."""
        result = PCIDSSClassifier.classify_column("amount")
        assert result.classification == DataClassification.INTERNAL
        assert not result.is_masked

    def test_case_insensitive_matching(self):
        """Test column name matching is case insensitive."""
        result1 = PCIDSSClassifier.classify_column("CARD_NUMBER")
        result2 = PCIDSSClassifier.classify_column("Card_Number")
        result3 = PCIDSSClassifier.classify_column("card_number")
        
        assert result1.classification == result2.classification == result3.classification
        assert result1.classification == DataClassification.PCI_DSS_RESTRICTED

    def test_classify_table_columns(self):
        """Test classifying multiple columns in a table."""
        columns = ["payment_id", "card_number", "cvv", "customer_id", "amount"]
        result = PCIDSSClassifier.classify_table_columns("payments", columns)
        
        assert len(result) == 5
        assert result["card_number"].classification == DataClassification.PCI_DSS_RESTRICTED
        assert result["cvv"].classification == DataClassification.PCI_DSS_RESTRICTED
        assert result["customer_id"].classification == DataClassification.PII_RESTRICTED
        assert result["payment_id"].classification == DataClassification.INTERNAL
        assert result["amount"].classification == DataClassification.INTERNAL

    def test_get_restricted_fields(self):
        """Test identifying restricted fields from a column list."""
        columns = ["payment_id", "card_number", "cvv", "amount", "customer_id"]
        restricted = PCIDSSClassifier.get_restricted_fields(columns)
        
        assert "card_number" in restricted
        assert "cvv" in restricted
        assert "payment_id" not in restricted
        assert "amount" not in restricted
        # customer_id is PII, not PCI-DSS, so should not be in restricted
        assert "customer_id" not in restricted

    def test_get_pii_fields(self):
        """Test identifying PII fields from a column list."""
        columns = ["payment_id", "card_number", "customer_id", "email", "amount"]
        pii = PCIDSSClassifier.get_pii_fields(columns)
        
        assert "customer_id" in pii
        assert "email" in pii
        assert "payment_id" not in pii
        assert "card_number" not in pii  # This is PCI-DSS, not PII

    def test_column_metadata_structure(self):
        """Test ColumnMetadata structure and fields."""
        result = PCIDSSClassifier.classify_column("card_number")
        
        assert isinstance(result, ColumnMetadata)
        assert result.column_name == "card_number"
        assert result.data_type == "string"
        assert result.classification == DataClassification.PCI_DSS_RESTRICTED
        assert result.is_masked is True
        assert result.mask_type == "tokenize"
        assert result.description is not None


class TestPCIDataMasker:
    """Test data masking functions."""

    def test_mask_card_number_full(self):
        """Test masking a full card number."""
        masked = PCIDataMasker.mask_card_number("4532015112830366")
        assert masked == "*" * 12 + "0366"
        assert masked != "4532015112830366"
        assert masked.endswith("0366")

    def test_mask_card_number_short(self):
        """Test masking a short card number."""
        masked = PCIDataMasker.mask_card_number("123")
        assert masked == "****"

    def test_mask_card_number_empty(self):
        """Test masking empty card number."""
        masked = PCIDataMasker.mask_card_number("")
        assert masked == "****"

    def test_mask_cvv(self):
        """Test CVV masking is fully redacted."""
        masked = PCIDataMasker.mask_cvv("123")
        assert masked == "***"
        assert "123" not in masked

    def test_mask_name(self):
        """Test name masking shows only first initial."""
        masked = PCIDataMasker.mask_name("John Smith")
        assert masked == "J***"
        assert "John" not in masked
        assert "Smith" not in masked

    def test_mask_name_single(self):
        """Test masking single name."""
        masked = PCIDataMasker.mask_name("John")
        assert masked == "J***"

    def test_mask_name_empty(self):
        """Test masking empty name."""
        masked = PCIDataMasker.mask_name("")
        assert masked == "***"

    def test_mask_email(self):
        """Test email masking shows domain only."""
        masked = PCIDataMasker.mask_email("john.doe@example.com")
        assert masked == "j***@example.com"
        assert "john" not in masked.lower()
        assert ".doe" not in masked

    def test_mask_email_no_at(self):
        """Test masking invalid email."""
        masked = PCIDataMasker.mask_email("invalid")
        assert masked == "***"

    def test_mask_phone(self):
        """Test phone masking shows last 4 digits."""
        masked = PCIDataMasker.mask_phone("555-123-4567")
        assert masked == "*" * 8 + "4567"
        assert "555" not in masked
        assert "123" not in masked

    def test_mask_phone_short(self):
        """Test masking short phone number."""
        masked = PCIDataMasker.mask_phone("123")
        assert masked == "****"

    def test_mask_phone_empty(self):
        """Test masking empty phone."""
        masked = PCIDataMasker.mask_phone("")
        assert masked == "****"

    def test_masking_consistency(self):
        """Test that masking same value produces same result."""
        card = "4532015112830366"
        result1 = PCIDataMasker.mask_card_number(card)
        result2 = PCIDataMasker.mask_card_number(card)
        
        assert result1 == result2

    def test_masking_different_lengths(self):
        """Test masking preserves relative card length indicators."""
        card16 = "4532015112830366"  # 16 digits
        card15 = "378282246310005"   # 15 digits
        
        masked16 = PCIDataMasker.mask_card_number(card16)
        masked15 = PCIDataMasker.mask_card_number(card15)
        
        # Both should show last 4 digits
        assert masked16[-4:] == "0366"
        assert masked15[-4:] == "0005"


class TestPCIComplianceWorkflow:
    """Test integrated PCI-DSS compliance workflow."""

    def test_payment_table_classification_workflow(self):
        """Test classifying a payment table for compliance."""
        columns = [
            "payment_id",
            "merchant_id",
            "customer_id",
            "card_number",
            "cvv",
            "cardholder_name",
            "expiration_date",
            "amount",
            "currency",
            "status",
            "created_at",
        ]
        
        classified = PCIDSSClassifier.classify_table_columns("payments", columns)
        
        # Count restricted fields
        restricted_count = sum(
            1 for col in classified.values()
            if col.classification == DataClassification.PCI_DSS_RESTRICTED
        )
        
        # Should have 5 restricted columns: card_number, cvv, cardholder_name, expiration_date
        assert restricted_count >= 4
        
        # All restricted fields should be masked
        for col in classified.values():
            if col.classification == DataClassification.PCI_DSS_RESTRICTED:
                assert col.is_masked
                assert col.mask_type in ["tokenize", "redact", "partial"]

    def test_data_anonymization_workflow(self):
        """Test anonymizing sensitive payment data."""
        sensitive_payment = {
            "card_number": "4532015112830366",
            "cvv": "123",
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone": "555-123-4567",
        }
        
        anonymized = {
            "card_number": PCIDataMasker.mask_card_number(sensitive_payment["card_number"]),
            "cvv": PCIDataMasker.mask_cvv(sensitive_payment["cvv"]),
            "name": PCIDataMasker.mask_name(sensitive_payment["name"]),
            "email": PCIDataMasker.mask_email(sensitive_payment["email"]),
            "phone": PCIDataMasker.mask_phone(sensitive_payment["phone"]),
        }
        
        # Verify original data is masked
        assert anonymized["card_number"] != sensitive_payment["card_number"]
        assert anonymized["cvv"] != sensitive_payment["cvv"]
        assert anonymized["name"] != sensitive_payment["name"]
        
        # Verify masked data is still present
        assert "0366" in anonymized["card_number"]  # Last 4 of card
        assert "example.com" in anonymized["email"]  # Domain
        assert "4567" in anonymized["phone"]  # Last 4 of phone
