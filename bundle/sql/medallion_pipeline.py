# Databricks notebook source
# Payment Processing Medallion Architecture Pipeline
# Orchestrates transformations from raw → silver → gold

# COMMAND ----------

# MAGIC %md
# MAGIC # Medallion Architecture Pipeline
# MAGIC 
# MAGIC This notebook orchestrates the data transformations for the payment processing medallion architecture:
# MAGIC 
# MAGIC - **Raw Layer**: Inbound payment and fraud signals
# MAGIC - **Silver Layer**: Cleaned, standardized, and enriched data
# MAGIC - **Gold Layer**: Business-ready dimensions, facts, and analytics

# COMMAND ----------

from pyspark.sql import SparkSession
from datetime import datetime
import logging

spark = SparkSession.builder.appName("payment_medallion").getOrCreate()
logger = logging.getLogger(__name__)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Validate Raw Data

# COMMAND ----------

def validate_raw_tables():
    """Validate that raw tables exist and contain data"""
    try:
        # Check payments_raw
        payment_count = spark.sql("SELECT COUNT(*) as cnt FROM payments.raw.payments_raw").collect()[0]['cnt']
        logger.info(f"Payments raw table: {payment_count} records")
        
        # Check fraud_signals_raw
        fraud_count = spark.sql("SELECT COUNT(*) as cnt FROM payments.raw.fraud_signals_raw").collect()[0]['cnt']
        logger.info(f"Fraud signals raw table: {fraud_count} records")
        
        return payment_count > 0 or fraud_count > 0
    except Exception as e:
        logger.warning(f"Raw tables validation error: {e}")
        return False

print(f"Raw tables validated: {validate_raw_tables()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Silver Layer Transformations

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Silver Layer: Payments Cleaned
# MAGIC CREATE OR REPLACE TABLE payments.silver.payments_cleaned AS
# MAGIC SELECT
# MAGIC   payment_id,
# MAGIC   merchant_id,
# MAGIC   customer_id,
# MAGIC   CAST(amount AS DECIMAL(18, 2)) as amount,
# MAGIC   UPPER(currency) as currency,
# MAGIC   CASE 
# MAGIC     WHEN payment_method = 'credit_card' THEN 'CREDIT_CARD'
# MAGIC     WHEN payment_method = 'debit_card' THEN 'DEBIT_CARD'
# MAGIC     WHEN payment_method = 'ach' THEN 'ACH'
# MAGIC     WHEN payment_method = 'wire' THEN 'WIRE'
# MAGIC     WHEN payment_method = 'digital_wallet' THEN 'DIGITAL_WALLET'
# MAGIC     ELSE 'UNKNOWN'
# MAGIC   END as payment_method_normalized,
# MAGIC   CASE 
# MAGIC     WHEN status = 'authorized' THEN 'AUTHORIZED'
# MAGIC     WHEN status = 'captured' THEN 'CAPTURED'
# MAGIC     WHEN status = 'declined' THEN 'DECLINED'
# MAGIC     WHEN status = 'refunded' THEN 'REFUNDED'
# MAGIC     WHEN status = 'failed' THEN 'FAILED'
# MAGIC     ELSE 'UNKNOWN'
# MAGIC   END as status_normalized,
# MAGIC   CAST(created_at AS TIMESTAMP) as payment_created_at,
# MAGIC   CAST(updated_at AS TIMESTAMP) as payment_updated_at,
# MAGIC   current_timestamp() as processed_at
# MAGIC FROM payments.raw.payments_raw
# MAGIC WHERE created_at >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Silver Layer: Fraud Signals Cleaned
# MAGIC CREATE OR REPLACE TABLE payments.silver.fraud_signals_cleaned AS
# MAGIC SELECT
# MAGIC   signal_id,
# MAGIC   transaction_id,
# MAGIC   CAST(risk_score AS DECIMAL(3, 2)) as risk_score,
# MAGIC   risk_level,
# MAGIC   alerts,
# MAGIC   CASE 
# MAGIC     WHEN decision = 'approve' THEN 'APPROVED'
# MAGIC     WHEN decision = 'decline' THEN 'DECLINED'
# MAGIC     WHEN decision = 'review' THEN 'UNDER_REVIEW'
# MAGIC     WHEN decision = 'challenge' THEN 'CHALLENGED'
# MAGIC     WHEN decision = 'block' THEN 'BLOCKED'
# MAGIC     ELSE 'UNKNOWN'
# MAGIC   END as decision_normalized,
# MAGIC   CAST(created_at AS TIMESTAMP) as signal_created_at,
# MAGIC   current_timestamp() as processed_at
# MAGIC FROM payments.raw.fraud_signals_raw
# MAGIC WHERE created_at >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Silver Layer: Payments with Fraud Enrichment
# MAGIC CREATE OR REPLACE TABLE payments.silver.payments_with_fraud AS
# MAGIC SELECT
# MAGIC   p.payment_id,
# MAGIC   p.merchant_id,
# MAGIC   p.customer_id,
# MAGIC   p.amount,
# MAGIC   p.currency,
# MAGIC   p.payment_method_normalized as payment_method,
# MAGIC   p.status_normalized as status,
# MAGIC   COALESCE(f.risk_score, 0.0) as risk_score,
# MAGIC   COALESCE(f.risk_level, 'NOT_EVALUATED') as fraud_risk_level,
# MAGIC   COALESCE(f.decision_normalized, 'NO_DECISION') as fraud_decision,
# MAGIC   f.alerts as fraud_alerts,
# MAGIC   CASE 
# MAGIC     WHEN f.decision_normalized IN ('DECLINED', 'BLOCKED') THEN 'HIGH_RISK'
# MAGIC     WHEN f.decision_normalized = 'CHALLENGED' THEN 'MEDIUM_RISK'
# MAGIC     WHEN COALESCE(f.risk_score, 0) > 0.5 THEN 'MEDIUM_RISK'
# MAGIC     WHEN COALESCE(f.risk_score, 0) > 0.25 THEN 'LOW_RISK'
# MAGIC     ELSE 'APPROVED'
# MAGIC   END as overall_risk_category,
# MAGIC   p.payment_created_at,
# MAGIC   p.payment_updated_at,
# MAGIC   COALESCE(f.signal_created_at, p.payment_created_at) as latest_event_at,
# MAGIC   p.processed_at
# MAGIC FROM payments.silver.payments_cleaned p
# MAGIC LEFT JOIN payments.silver.fraud_signals_cleaned f 
# MAGIC   ON p.payment_id = f.transaction_id;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Silver Layer: Transactions Fact (Deduplicated)
# MAGIC CREATE OR REPLACE TABLE payments.silver.transactions_fact AS
# MAGIC SELECT
# MAGIC   payment_id as transaction_id,
# MAGIC   merchant_id,
# MAGIC   customer_id,
# MAGIC   amount,
# MAGIC   currency,
# MAGIC   payment_method,
# MAGIC   status,
# MAGIC   risk_score,
# MAGIC   fraud_risk_level,
# MAGIC   fraud_decision,
# MAGIC   overall_risk_category,
# MAGIC   payment_created_at as transaction_date,
# MAGIC   payment_updated_at,
# MAGIC   latest_event_at,
# MAGIC   current_timestamp() as batch_timestamp
# MAGIC FROM (
# MAGIC   SELECT *,
# MAGIC     ROW_NUMBER() OVER (PARTITION BY payment_id ORDER BY payment_updated_at DESC) as row_number
# MAGIC   FROM payments.silver.payments_with_fraud
# MAGIC ) dedup
# MAGIC WHERE row_number = 1;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Gold Layer: Dimensions, Facts, and Metrics

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Dimension: Date
# MAGIC CREATE OR REPLACE TABLE payments.gold.dim_date AS
# MAGIC WITH date_range AS (
# MAGIC   SELECT CAST(DATE_TRUNC('day', DATEADD(day, -seq, CURRENT_DATE)) AS DATE) as date_key
# MAGIC   FROM (SELECT EXPLODE(SEQUENCE(0, 730))) t(seq)
# MAGIC )
# MAGIC SELECT
# MAGIC   CAST(FORMAT_STRING('%04d%02d%02d', YEAR(date_key), MONTH(date_key), DAY(date_key)) AS STRING) as date_key,
# MAGIC   date_key as calendar_date,
# MAGIC   YEAR(date_key) as year,
# MAGIC   QUARTER(date_key) as quarter,
# MAGIC   MONTH(date_key) as month_number,
# MAGIC   DATE_FORMAT(date_key, 'MMMM') as month_name,
# MAGIC   WEEK(date_key) as week_number,
# MAGIC   DAY(date_key) as day_of_month,
# MAGIC   DAYOFWEEK(date_key) as day_of_week,
# MAGIC   DATE_FORMAT(date_key, 'EEEE') as day_name,
# MAGIC   CASE WHEN DAYOFWEEK(date_key) IN (1, 7) THEN 1 ELSE 0 END as is_weekend,
# MAGIC   CASE WHEN MONTH(date_key) IN (1, 4, 7, 10) AND DAY(date_key) = 1 THEN 1 ELSE 0 END as is_quarter_start
# MAGIC FROM date_range;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Dimension: Merchant
# MAGIC CREATE OR REPLACE TABLE payments.gold.dim_merchant AS
# MAGIC SELECT DISTINCT
# MAGIC   merchant_id,
# MAGIC   merchant_id as merchant_code,
# MAGIC   CONCAT('Merchant_', merchant_id) as merchant_name,
# MAGIC   COUNT(*) OVER (PARTITION BY merchant_id) as total_transactions,
# MAGIC   CURRENT_TIMESTAMP() as last_updated
# MAGIC FROM payments.silver.transactions_fact;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Dimension: Customer
# MAGIC CREATE OR REPLACE TABLE payments.gold.dim_customer AS
# MAGIC SELECT DISTINCT
# MAGIC   customer_id,
# MAGIC   customer_id as customer_code,
# MAGIC   CONCAT('Customer_', customer_id) as customer_name,
# MAGIC   COUNT(*) OVER (PARTITION BY customer_id) as total_transactions,
# MAGIC   AVG(risk_score) OVER (PARTITION BY customer_id) as avg_risk_score,
# MAGIC   MAX(risk_score) OVER (PARTITION BY customer_id) as max_risk_score,
# MAGIC   SUM(CASE WHEN fraud_decision = 'DECLINED' THEN 1 ELSE 0 END) OVER (PARTITION BY customer_id) as fraud_decline_count,
# MAGIC   CURRENT_TIMESTAMP() as last_updated
# MAGIC FROM payments.silver.transactions_fact;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Fact: Transactions
# MAGIC CREATE OR REPLACE TABLE payments.gold.fact_transactions AS
# MAGIC SELECT
# MAGIC   t.transaction_id,
# MAGIC   CAST(FORMAT_STRING('%04d%02d%02d', YEAR(t.transaction_date), MONTH(t.transaction_date), DAY(t.transaction_date)) AS STRING) as date_key,
# MAGIC   t.merchant_id,
# MAGIC   t.customer_id,
# MAGIC   t.payment_method,
# MAGIC   t.amount as transaction_amount,
# MAGIC   t.currency,
# MAGIC   t.status as payment_status,
# MAGIC   t.risk_score,
# MAGIC   t.fraud_risk_level,
# MAGIC   t.fraud_decision,
# MAGIC   t.overall_risk_category,
# MAGIC   CASE WHEN t.status = 'CAPTURED' THEN t.amount ELSE 0 END as captured_amount,
# MAGIC   CASE WHEN t.status = 'REFUNDED' THEN t.amount ELSE 0 END as refunded_amount,
# MAGIC   CASE WHEN t.status IN ('DECLINED', 'FAILED') THEN t.amount ELSE 0 END as failed_amount,
# MAGIC   CASE WHEN t.fraud_decision = 'DECLINED' THEN t.amount ELSE 0 END as fraud_blocked_amount,
# MAGIC   t.transaction_date as transaction_timestamp,
# MAGIC   t.payment_updated_at as status_updated_at,
# MAGIC   CURRENT_TIMESTAMP() as loaded_at
# MAGIC FROM payments.silver.transactions_fact t;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Metric View: Daily Payment Summary
# MAGIC CREATE OR REPLACE VIEW payments.gold.metric_daily_payment_summary AS
# MAGIC SELECT
# MAGIC   d.calendar_date,
# MAGIC   d.year,
# MAGIC   d.quarter,
# MAGIC   d.month_number,
# MAGIC   COUNT(DISTINCT f.transaction_id) as total_transactions,
# MAGIC   COUNT(DISTINCT f.merchant_id) as active_merchants,
# MAGIC   COUNT(DISTINCT f.customer_id) as active_customers,
# MAGIC   SUM(f.transaction_amount) as total_volume,
# MAGIC   AVG(f.transaction_amount) as avg_transaction_amount,
# MAGIC   COUNT(CASE WHEN f.payment_status = 'CAPTURED' THEN 1 END) as successful_transactions,
# MAGIC   COUNT(CASE WHEN f.payment_status IN ('DECLINED', 'FAILED') THEN 1 END) as failed_transactions,
# MAGIC   COUNT(CASE WHEN f.fraud_decision = 'DECLINED' THEN 1 END) as fraud_blocked_transactions,
# MAGIC   CAST(COUNT(CASE WHEN f.payment_status = 'CAPTURED' THEN 1 END) AS FLOAT) / NULLIF(COUNT(DISTINCT f.transaction_id), 0) * 100 as success_rate_pct,
# MAGIC   AVG(f.risk_score) as avg_risk_score,
# MAGIC   SUM(f.captured_amount) as captured_volume,
# MAGIC   SUM(f.fraud_blocked_amount) as fraud_blocked_volume
# MAGIC FROM payments.gold.dim_date d
# MAGIC LEFT JOIN payments.gold.fact_transactions f 
# MAGIC   ON d.date_key = CAST(FORMAT_STRING('%04d%02d%02d', YEAR(f.transaction_timestamp), MONTH(f.transaction_timestamp), DAY(f.transaction_timestamp)) AS STRING)
# MAGIC GROUP BY d.calendar_date, d.year, d.quarter, d.month_number;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Metric View: Fraud Analytics
# MAGIC CREATE OR REPLACE VIEW payments.gold.metric_fraud_analytics AS
# MAGIC SELECT
# MAGIC   f.merchant_id,
# MAGIC   dm.merchant_name,
# MAGIC   COUNT(DISTINCT f.transaction_id) as total_transactions,
# MAGIC   COUNT(DISTINCT f.customer_id) as unique_customers,
# MAGIC   SUM(f.transaction_amount) as total_volume,
# MAGIC   COUNT(CASE WHEN f.fraud_decision = 'DECLINED' THEN 1 END) as fraud_blocked_count,
# MAGIC   SUM(CASE WHEN f.fraud_decision = 'DECLINED' THEN f.transaction_amount ELSE 0 END) as fraud_blocked_volume,
# MAGIC   CAST(COUNT(CASE WHEN f.fraud_decision = 'DECLINED' THEN 1 END) AS FLOAT) / NULLIF(COUNT(DISTINCT f.transaction_id), 0) * 100 as fraud_block_rate_pct,
# MAGIC   AVG(f.risk_score) as avg_risk_score,
# MAGIC   COUNT(CASE WHEN f.overall_risk_category = 'HIGH_RISK' THEN 1 END) as high_risk_transactions
# MAGIC FROM payments.gold.fact_transactions f
# MAGIC LEFT JOIN payments.gold.dim_merchant dm ON f.merchant_id = dm.merchant_id
# MAGIC GROUP BY f.merchant_id, dm.merchant_name;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create Metric View: Customer Risk Profile
# MAGIC CREATE OR REPLACE VIEW payments.gold.metric_customer_risk_profile AS
# MAGIC SELECT
# MAGIC   f.customer_id,
# MAGIC   dc.customer_name,
# MAGIC   COUNT(DISTINCT f.transaction_id) as transaction_count,
# MAGIC   COUNT(DISTINCT f.merchant_id) as merchant_count,
# MAGIC   SUM(f.transaction_amount) as total_volume,
# MAGIC   AVG(f.risk_score) as avg_risk_score,
# MAGIC   MAX(f.risk_score) as max_risk_score,
# MAGIC   COUNT(CASE WHEN f.overall_risk_category = 'HIGH_RISK' THEN 1 END) as high_risk_count,
# MAGIC   COUNT(CASE WHEN f.payment_status = 'CAPTURED' THEN 1 END) as successful_transactions,
# MAGIC   COUNT(CASE WHEN f.fraud_decision = 'DECLINED' THEN 1 END) as fraud_blocked_count,
# MAGIC   CASE 
# MAGIC     WHEN AVG(f.risk_score) > 0.7 THEN 'VERY_HIGH_RISK'
# MAGIC     WHEN AVG(f.risk_score) > 0.5 THEN 'HIGH_RISK'
# MAGIC     WHEN AVG(f.risk_score) > 0.25 THEN 'MEDIUM_RISK'
# MAGIC     ELSE 'LOW_RISK'
# MAGIC   END as risk_classification,
# MAGIC   MAX(f.transaction_timestamp) as last_transaction_date
# MAGIC FROM payments.gold.fact_transactions f
# MAGIC LEFT JOIN payments.gold.dim_customer dc ON f.customer_id = dc.customer_id
# MAGIC GROUP BY f.customer_id, dc.customer_name;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Pipeline Summary

# COMMAND ----------

def print_pipeline_summary():
    """Print summary of created tables and views"""
    try:
        schema_tables = spark.sql("SHOW TABLES IN payments.silver").collect()
        print(f"\n✓ Silver Layer: {len(schema_tables)} tables created")
        for table in schema_tables:
            print(f"  - {table.tableName}")
        
        gold_tables = spark.sql("SHOW TABLES IN payments.gold").collect()
        print(f"\n✓ Gold Layer: {len(gold_tables)} tables/views created")
        for table in gold_tables:
            print(f"  - {table.tableName}")
        
        print(f"\n✓ Pipeline completed successfully at {datetime.now()}")
        return True
    except Exception as e:
        logger.error(f"Pipeline summary error: {e}")
        return False

print_pipeline_summary()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Execution Complete
# MAGIC 
# MAGIC - ✓ Raw layer validated
# MAGIC - ✓ Silver layer transformations created
# MAGIC - ✓ Gold layer dimensions and facts created
# MAGIC - ✓ Metric views for analytics ready
