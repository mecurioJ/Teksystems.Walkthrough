"""Main entry point for the payment gateway application."""

from decimal import Decimal
from src.models import PaymentMethod
from src.api import PaymentAPI
from src.utils import setup_logger, format_currency


def main():
    """Run the payment gateway application."""
    logger = setup_logger(__name__)
    
    logger.info("Starting Teksystems Payment Gateway Walkthrough")
    
    # Initialize API
    api = PaymentAPI()
    logger.info("Payment API initialized")
    
    # Example payment processing
    result = api.process_payment(
        amount=Decimal("99.99"),
        currency="USD",
        method=PaymentMethod.CREDIT_CARD,
        merchant_id="merchant_demo",
        customer_id="customer_demo",
        card_token="tok_visa_test",
        description="Demo payment",
        capture_immediately=True,
    )
    
    logger.info(f"Payment result: {result}")
    
    if result["success"]:
        amount = Decimal(result["amount"])
        currency = result["currency"]
        formatted = format_currency(amount, currency)
        logger.info(f"Successfully processed payment: {formatted}")
    else:
        logger.error(f"Payment failed: {result['error']}")


if __name__ == "__main__":
    main()
