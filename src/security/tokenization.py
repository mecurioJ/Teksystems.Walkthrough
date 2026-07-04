"""Payment tokenization service (PCI-DSS compliance)."""

import uuid
from typing import Dict, Optional


class TokenizationService:
    """
    Tokenizes sensitive payment data to reduce PCI-DSS scope.
    
    This service replaces actual card/payment details with tokens,
    storing sensitive data separately from transaction records.
    """
    
    def __init__(self):
        """Initialize tokenization service."""
        self._tokens: Dict[str, str] = {}
    
    def tokenize(self, sensitive_data: str, data_type: str = "card") -> str:
        """
        Create a token for sensitive payment data.
        
        Args:
            sensitive_data: The sensitive data to tokenize (e.g., card number)
            data_type: Type of data (card, bank_account, etc.)
            
        Returns:
            A token to use instead of the actual data
        """
        token = f"tok_{uuid.uuid4().hex[:16]}"
        self._tokens[token] = sensitive_data
        return token
    
    def retrieve(self, token: str) -> Optional[str]:
        """
        Retrieve original data from token (internal use only).
        
        Args:
            token: The token created by tokenize()
            
        Returns:
            Original data or None if token invalid
        """
        return self._tokens.get(token)
    
    def mask_card_number(self, card_number: str) -> str:
        """
        Create a masked version of a card number for display.
        
        Args:
            card_number: Full card number
            
        Returns:
            Masked card number (e.g., "****-****-****-1234")
        """
        if len(card_number) < 4:
            return "*" * len(card_number)
        return "*" * (len(card_number) - 4) + card_number[-4:]
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token to prevent further use.
        
        Args:
            token: The token to revoke
            
        Returns:
            True if revoked, False if token not found
        """
        return self._tokens.pop(token, None) is not None
