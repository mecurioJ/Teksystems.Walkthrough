# Databricks notebook source
# Data Generation Pipeline - Python
# Generates sample payment and fraud data for the medallion architecture

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, DecimalType, 
    TimestampType, IntegerType, ArrayType
)
from datetime import datetime, timedelta
import random
import json
from decimal import Decimal

# Import from teksystems-walkthrough wheel
try:
    from src.models import Payment, PaymentMethod, PaymentStatus
    from src.payment import PaymentProcessor, PaymentValidator
    from src.fraud import SimpleFraudEngine, InMemoryFraudStream
    from src.security import PCIDSSClassifier, TokenizationService
    print("✓ Successfully imported teksystems-walkthrough wheel package")
except ImportError as e:
    print(f"⚠ Warning: Could not import wheel package: {e}")
    print("  Falling back to inline implementation")

spark = SparkSession.builder.appName("data_generation_pipeline").getOrCreate()
spark.sparkContext.setLogLevel("INFO")

# COMMAND ----------

def generate_payment_records(num_records=100):
    """
    Generate sample payment records using PaymentProcessor
    
    Args:
        num_records: Number of payment records to generate
        
    Returns:
        List of payment dictionaries
    """
    print(f"🔄 Generating {num_records} payment records...")
    
    payments = []
    merchant_ids = [f"merchant_{i}" for i in range(1, 11)]
    customer_ids = [f"customer_{i}" for i in range(1, 51)]
    payment_methods = ["credit_card", "debit_card", "ach", "wire", "digital_wallet"]
    statuses = ["authorized", "captured", "declined", "refunded"]
    currencies = ["USD", "EUR", "GBP", "JPY"]
    
    processor = PaymentProcessor()
    
    for i in range(num_records):
        # Create payment
        payment = Payment(
            payment_id=f"PAY_{i:06d}",
            merchant_id=random.choice(merchant_ids),
            customer_id=random.choice(customer_ids),
            amount=Decimal(str(round(random.uniform(10, 5000), 2))),
            currency=random.choice(currencies),
            payment_method=PaymentMethod[random.choice(payment_methods).upper()],
            status=PaymentStatus.AUTHORIZED if random.random() > 0.1 else PaymentStatus.DECLINED,
            created_at=datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
            updated_at=datetime.utcnow()
        )
        
        # Tokenize sensitive data
        try:
            tokenized = processor.process_payment(payment)
            payment_dict = {
                "payment_id": payment.payment_id,
                "merchant_id": payment.merchant_id,
                "customer_id": payment.customer_id,
                "amount": float(payment.amount),
                "currency": payment.currency.value,
                "payment_method": payment.payment_method.value,
                "status": payment.status.value,
                "created_at": payment.created_at,
                "updated_at": payment.updated_at,
                "metadata": json.dumps({
                    "processor_token": tokenized.token if hasattr(tokenized, 'token') else None,
                    "tokenization_timestamp": datetime.utcnow().isoformat()
                })
            }
            payments.append(payment_dict)
        except Exception as e:
            print(f"  ⚠ Error processing payment {payment.payment_id}: {e}")
            payment_dict = {
                "payment_id": payment.payment_id,
                "merchant_id": payment.merchant_id,
                "customer_id": payment.customer_id,
                "amount": float(payment.amount),
                "currency": payment.currency.value,
                "payment_method": payment.payment_method.value,
                "status": payment.status.value,
                "created_at": payment.created_at,
                "updated_at": payment.updated_at,
                "metadata": "{}"
            }
            payments.append(payment_dict)
    
    print(f"✓ Generated {len(payments)} payment records")
    return payments

# COMMAND ----------

def generate_fraud_signals(payment_ids):
    """
    Generate fraud signals for payment records
    
    Args:
        payment_ids: List of payment IDs
        
    Returns:
        List of fraud signal dictionaries
    """
    print(f"🔄 Generating fraud signals for {len(payment_ids)} transactions...")
    
    fraud_signals = []
    fraud_engine = SimpleFraudEngine()
    
    for i, payment_id in enumerate(payment_ids):
        # Create a mock payment for fraud evaluation
        payment = Payment(
            payment_id=payment_id,
            merchant_id=f"merchant_{random.randint(1, 10)}",
            customer_id=f"customer_{random.randint(1, 50)}",
            amount=Decimal(str(round(random.uniform(10, 5000), 2))),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.AUTHORIZED
        )
        
        try:
            # Evaluate fraud risk
            fraud_signal = fraud_engine.evaluate(payment)
            
            signal_dict = {
                "signal_id": f"FRAUD_{i:06d}",
                "transaction_id": fraud_signal.transaction_id,
                "risk_score": float(fraud_signal.risk_score),
                "classification": fraud_signal.classification,
                "alert_level": fraud_signal.alert_level,
                "case_decision": fraud_signal.case_decision,
                "created_at": datetime.utcnow()
            }
            fraud_signals.append(signal_dict)
        except Exception as e:
            print(f"  ⚠ Error evaluating fraud for {payment_id}: {e}")
            signal_dict = {
                "signal_id": f"FRAUD_{i:06d}",
                "transaction_id": payment_id,
                "risk_score": 0.5,
                "classification": "MODERATE",
                "alert_level": "INFO",
                "case_decision": "REVIEW",
                "created_at": datetime.utcnow()
            }
            fraud_signals.append(signal_dict)
    
    print(f"✓ Generated {len(fraud_signals)} fraud signals")
    return fraud_signals

# COMMAND ----------

def load_raw_layer(payments, fraud_signals):
    """
    Load generated data into raw layer tables
    
    Args:
        payments: List of payment dictionaries
        fraud_signals: List of fraud signal dictionaries
    """
    print("🔄 Loading data into raw layer...")
    
    # Create payment transactions DataFrame
    payment_schema = StructType([
        StructField("payment_id", StringType()),
        StructField("merchant_id", StringType()),
        StructField("customer_id", StringType()),
        StructField("amount", DecimalType(18, 2)),
        StructField("currency", StringType()),
        StructField("payment_method", StringType()),
        StructField("status", StringType()),
        StructField("created_at", TimestampType()),
        StructField("updated_at", TimestampType()),
        StructField("metadata", StringType())
    ])
    
    payment_df = spark.createDataFrame(payments, schema=payment_schema)
    
    # Write to raw payment transactions
    payment_df.write.format("delta").mode("append").insertInto(
        "payments.raw.payment_transactions"
    )
    print(f"✓ Loaded {len(payments)} payment records to payments.raw.payment_transactions")
    
    # Create fraud signals DataFrame
    fraud_schema = StructType([
        StructField("signal_id", StringType()),
        StructField("transaction_id", StringType()),
        StructField("risk_score", DecimalType(5, 3)),
        StructField("classification", StringType()),
        StructField("alert_level", StringType()),
        StructField("case_decision", StringType()),
        StructField("created_at", TimestampType())
    ])
    
    fraud_df = spark.createDataFrame(fraud_signals, schema=fraud_schema)
    
    # Write to raw fraud signals
    fraud_df.write.format("delta").mode("append").insertInto(
        "payments.raw.fraud_signals"
    )
    print(f"✓ Loaded {len(fraud_signals)} fraud signals to payments.raw.fraud_signals")

# COMMAND ----------

# Main execution
if __name__ == "__main__" or True:  # Always run in notebook
    print("=" * 80)
    print("DATA GENERATION PIPELINE")
    print("=" * 80)
    print()
    
    # Generate payment and fraud data
    payments = generate_payment_records(num_records=100)
    payment_ids = [p["payment_id"] for p in payments]
    fraud_signals = generate_fraud_signals(payment_ids)
    
    # Load into raw layer
    load_raw_layer(payments, fraud_signals)
    
    # Show statistics
    print()
    print("📊 Pipeline Statistics:")
    print(f"   • Payments generated: {len(payments)}")
    print(f"   • Fraud signals generated: {len(fraud_signals)}")
    print(f"   • Timestamp: {datetime.utcnow().isoformat()}")
    print()
    print("✅ Data generation pipeline completed successfully!")
    print()
