"""PCI-DSS Data Classification and Tagging Module"""

from enum import Enum
from typing import Dict, List, Set
from dataclasses import dataclass


class DataClassification(Enum):
    """Data classification levels for PCI-DSS compliance"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PCI_DSS_RESTRICTED = "pci_dss_restricted"
    PII_RESTRICTED = "pii_restricted"


@dataclass
class ColumnMetadata:
    """Metadata for a column including PCI-DSS classification"""
    column_name: str
    data_type: str
    classification: DataClassification
    is_masked: bool = False
    mask_type: str = None  # full, partial, redact, tokenize
    description: str = None


class PCIDSSClassifier:
    """
    Classifies data fields as PCI-DSS restricted based on content and schema.
    
    PCI-DSS Restricted Data Includes:
    - Primary Account Number (PAN/card number)
    - Cardholder name
    - Service code
    - CVC/CVV
    - Expiration date
    - PIN block
    - Full track data
    """
    
    # Fields that are always PCI-DSS restricted
    RESTRICTED_FIELDS = {
        "card_number", "pan", "primary_account_number",
        "cvv", "cvc", "security_code", "verification_code",
        "cardholder_name", "expiration_date", "expiry_date", "exp_date",
        "pin", "pin_block", "track_data", "full_track",
        "ksn", "key_serial_number",
    }
    
    # Fields that typically need masking
    MASK_FIELDS = {
        "card_number", "pan",  # Mask to **** XXXX
        "cvv", "cvc",  # Fully redact
        "pin", "pin_block",  # Fully redact
        "cardholder_name",  # Mask name
        "ssn", "social_security_number",  # PII
        "email", "phone",  # PII when linked to card data
    }
    
    @classmethod
    def classify_column(cls, column_name: str, data_type: str = "string") -> ColumnMetadata:
        """
        Classify a column as PCI-DSS restricted or not.
        
        Args:
            column_name: Name of the column
            data_type: Databricks data type
            
        Returns:
            ColumnMetadata with classification and masking info
        """
        column_lower = column_name.lower()
        
        # Check if field is PCI-DSS restricted
        is_restricted = any(
            restricted in column_lower 
            for restricted in cls.RESTRICTED_FIELDS
        )
        
        if is_restricted:
            classification = DataClassification.PCI_DSS_RESTRICTED
        elif any(pii in column_lower for pii in {"ssn", "email", "phone", "customer_id"}):
            classification = DataClassification.PII_RESTRICTED
        else:
            classification = DataClassification.INTERNAL
        
        # Determine masking strategy
        is_masked = False
        mask_type = None
        
        if is_restricted or classification == DataClassification.PII_RESTRICTED:
            is_masked = True
            if any(f in column_lower for f in {"card", "pan", "cvv", "cvc", "pin"}):
                mask_type = "tokenize"  # Replace with token
            elif any(f in column_lower for f in {"name", "email", "phone"}):
                mask_type = "partial"  # Show first/last few chars
            else:
                mask_type = "redact"  # Fully redact
        
        return ColumnMetadata(
            column_name=column_name,
            data_type=data_type,
            classification=classification,
            is_masked=is_masked,
            mask_type=mask_type,
            description=f"PCI-DSS Classification: {classification.value}"
        )
    
    @classmethod
    def classify_table_columns(cls, table_name: str, columns: List[str]) -> Dict[str, ColumnMetadata]:
        """
        Classify all columns in a table.
        
        Args:
            table_name: Name of the table
            columns: List of column names
            
        Returns:
            Dictionary mapping column names to their metadata
        """
        return {
            col: cls.classify_column(col)
            for col in columns
        }
    
    @classmethod
    def get_restricted_fields(cls, columns: List[str]) -> Set[str]:
        """Get list of PCI-DSS restricted fields from a column list."""
        return {
            col for col in columns
            if cls.classify_column(col).classification == DataClassification.PCI_DSS_RESTRICTED
        }
    
    @classmethod
    def get_pii_fields(cls, columns: List[str]) -> Set[str]:
        """Get list of PII restricted fields from a column list."""
        return {
            col for col in columns
            if cls.classify_column(col).classification == DataClassification.PII_RESTRICTED
        }


class PCIDataMasker:
    """Masking functions for sensitive data"""
    
    @staticmethod
    def mask_card_number(card_number: str) -> str:
        """Mask card number to **** **** **** XXXX"""
        if not card_number or len(card_number) < 4:
            return "****"
        return "*" * (len(card_number) - 4) + card_number[-4:]
    
    @staticmethod
    def mask_cvv(cvv: str) -> str:
        """Fully redact CVV"""
        return "***"
    
    @staticmethod
    def mask_name(name: str) -> str:
        """Mask name to show only first letter"""
        if not name or len(name) == 0:
            return "***"
        parts = name.split()
        return f"{parts[0][0]}***" if parts else "***"
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email to show domain only"""
        if "@" not in email:
            return "***"
        local, domain = email.split("@")
        return f"{local[0]}***@{domain}"
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone to show last 4 digits"""
        if len(phone) < 4:
            return "****"
        return "*" * (len(phone) - 4) + phone[-4:]
