"""Helper functions."""

from decimal import Decimal


def format_currency(amount: Decimal, currency: str = "USD") -> str:
    """
    Format an amount as currency string.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:.2f}"
