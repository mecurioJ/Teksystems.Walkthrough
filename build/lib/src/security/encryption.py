"""Encryption service for sensitive data."""

from typing import Optional
import hashlib
import hmac


class EncryptionService:
    """
    Handles encryption/decryption of sensitive payment data.
    
    For production, use industry-standard libraries (cryptography, PyCryptodome)
    with proper key management.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            secret_key: Secret key for HMAC operations (use secure key in production)
        """
        self.secret_key = secret_key or "dev-secret-key-change-in-production"
    
    def hash_password(self, password: str, algorithm: str = "sha256") -> str:
        """
        Hash a password using specified algorithm.
        
        Args:
            password: Password to hash
            algorithm: Hash algorithm (sha256, sha512)
            
        Returns:
            Hashed password
        """
        h = hashlib.new(algorithm)
        h.update(password.encode())
        return h.hexdigest()
    
    def generate_hmac(self, data: str) -> str:
        """
        Generate HMAC for data integrity verification.
        
        Args:
            data: Data to generate HMAC for
            
        Returns:
            HMAC digest
        """
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_hmac(self, data: str, signature: str) -> bool:
        """
        Verify HMAC signature.
        
        Args:
            data: Original data
            signature: HMAC signature to verify
            
        Returns:
            True if signature is valid
        """
        expected = self.generate_hmac(data)
        return hmac.compare_digest(expected, signature)
