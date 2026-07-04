"""Transaction lifecycle management."""

from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, List
import uuid

from src.models import Transaction, TransactionType, TransactionStatus


class TransactionManager:
    """Manages transaction records and history."""
    
    def __init__(self):
        """Initialize transaction manager."""
        self._transactions: Dict[str, Transaction] = {}
    
    def create_transaction(
        self,
        payment_id: str,
        type: TransactionType,
        amount: Decimal,
        currency: str,
        description: Optional[str] = None,
    ) -> Transaction:
        """
        Create a new transaction record.
        
        Args:
            payment_id: Associated payment ID
            type: Type of transaction
            amount: Transaction amount
            currency: Currency code
            description: Optional description
            
        Returns:
            Created transaction object
        """
        transaction = Transaction(
            id=str(uuid.uuid4()),
            payment_id=payment_id,
            type=type,
            status=TransactionStatus.INITIATED,
            amount=amount,
            currency=currency,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            description=description,
        )
        self._transactions[transaction.id] = transaction
        return transaction
    
    def update_status(
        self,
        transaction_id: str,
        status: TransactionStatus,
        error_message: Optional[str] = None,
    ) -> Transaction:
        """
        Update transaction status.
        
        Args:
            transaction_id: Transaction ID
            status: New status
            error_message: Optional error message
            
        Returns:
            Updated transaction
        """
        if transaction_id not in self._transactions:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        transaction = self._transactions[transaction_id]
        transaction.status = status
        transaction.updated_at = datetime.utcnow()
        if error_message:
            transaction.error_message = error_message
        return transaction
    
    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Retrieve a transaction by ID."""
        return self._transactions.get(transaction_id)
    
    def get_payment_transactions(self, payment_id: str) -> List[Transaction]:
        """Get all transactions for a payment."""
        return [t for t in self._transactions.values() if t.payment_id == payment_id]
