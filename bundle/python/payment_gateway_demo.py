# Databricks notebook source
# Payment Gateway Demo
# This notebook demonstrates using the teksystems-walkthrough wheel package in Databricks

# COMMAND ----------

# Install the wheel from the bundle
%pip install /Workspace/Repos/[username]/Teksystems.Walkthrough/bundle/python/teksystems_walkthrough-0.1.0-py3-none-any.whl

# COMMAND ----------

from decimal import Decimal
from src.models import PaymentMethod
from src.api import PaymentAPI
from src.fraud import SimpleFraudEngine, InMemoryFraudStream
import json

# Initialize payment API with fraud detection
api = PaymentAPI(
    fraud_engine=SimpleFraudEngine(max_transaction_amount=Decimal("5000.00")),
    fraud_stream=InMemoryFraudStream(),
    enable_fraud_detection=True,
)

print("Payment Gateway API initialized in Databricks")

# COMMAND ----------

# Process a sample payment
payment_result = api.process_payment(
    amount=Decimal("150.00"),
    currency="USD",
    method=PaymentMethod.CREDIT_CARD,
    merchant_id="databricks_merchant",
    customer_id="customer_demo_001",
    card_token="tok_databricks_demo",
    description="Demo payment from Databricks notebook",
    capture_immediately=True,
)

print("Payment result:")
print(json.dumps(payment_result, indent=2, default=str))

# COMMAND ----------

# Process a high-risk payment (amount anomaly)
high_risk_result = api.process_payment(
    amount=Decimal("9999.00"),  # Exceeds default threshold
    currency="USD",
    method=PaymentMethod.CREDIT_CARD,
    merchant_id="databricks_merchant",
    customer_id="customer_high_risk",
    card_token="tok_databricks_highrisk",
    description="High-risk demo payment",
    capture_immediately=True,
)

print("High-risk payment result:")
print(json.dumps(high_risk_result, indent=2, default=str))

# COMMAND ----------

# Query fraud signals from the stream
if hasattr(api.fraud_stream, 'get_signals'):
    signals = api.fraud_stream.get_signals()
    print(f"Total fraud signals emitted: {len(signals)}")
    
    for signal in signals:
        print(f"\nTransaction: {signal.transaction_id}")
        print(f"  Risk Level: {signal.risk_level.value}")
        print(f"  Risk Score: {signal.risk_score}")
        print(f"  Decision: {signal.decision.value}")
        print(f"  Alerts: {[alert.value for alert in signal.alerts]}")
