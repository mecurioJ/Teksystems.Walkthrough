# Databricks notebook source
# SQL Transformation Pipeline
# Populates silver and gold layers from raw data

# COMMAND ----------

# MAGIC %md
# MAGIC # Medallion Transformation Pipeline (SQL)
# MAGIC 
# MAGIC This pipeline performs multi-layer transformations:
# MAGIC 1. **Raw → Silver**: Data cleaning, validation, and standardization
# MAGIC 2. **Silver → Gold**: Dimensional modeling and fact table creation

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ============================================================================
# MAGIC -- SILVER LAYER TRANSFORMATIONS
# MAGIC -- ============================================================================

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Silver Layer: Payment Validation
# MAGIC -- Clean, validate, and standardize payment transaction data
# MAGIC 
# MAGIC INSERT INTO payments.silver.payment_validated
# MAGIC SELECT
# MAGIC   pt.payment_id,
# MAGIC   pt.merchant_id,
# MAGIC   pt.customer_id,
# MAGIC   pt.amount,
# MAGIC   UPPER(pt.currency) as currency,
# MAGIC   CASE 
# MAGIC     WHEN LOWER(pt.payment_method) = 'credit_card' THEN 'CREDIT_CARD'
# MAGIC     WHEN LOWER(pt.payment_method) = 'debit_card' THEN 'DEBIT_CARD'
# MAGIC     WHEN LOWER(pt.payment_method) = 'ach' THEN 'ACH'
# MAGIC     WHEN LOWER(pt.payment_method) = 'wire' THEN 'WIRE'
# MAGIC     WHEN LOWER(pt.payment_method) = 'digital_wallet' THEN 'DIGITAL_WALLET'
# MAGIC     ELSE 'UNKNOWN'
# MAGIC   END as payment_method,
# MAGIC   CASE 
# MAGIC     WHEN LOWER(pt.status) = 'authorized' THEN 'AUTHORIZED'
# MAGIC     WHEN LOWER(pt.status) = 'captured' THEN 'CAPTURED'
# MAGIC     WHEN LOWER(pt.status) = 'declined' THEN 'DECLINED'
# MAGIC     WHEN LOWER(pt.status) = 'refunded' THEN 'REFUNDED'
# MAGIC     WHEN LOWER(pt.status) = 'failed' THEN 'FAILED'
# MAGIC     ELSE 'UNKNOWN'
# MAGIC   END as status,
# MAGIC   pt.created_at,
# MAGIC   pt.updated_at,
# MAGIC   'PCI_DSS_RESTRICTED' as pci_classification,
# MAGIC   current_timestamp() as load_ts
# MAGIC FROM payments.raw.payment_transactions pt
# MAGIC WHERE pt.created_at >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS
# MAGIC   AND pt.payment_id NOT IN (SELECT DISTINCT payment_id FROM payments.silver.payment_validated);

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Silver Layer: Fraud Signal Enrichment
# MAGIC -- Standardize and enrich fraud signals with classification
# MAGIC 
# MAGIC INSERT INTO payments.silver.fraud_enriched
# MAGIC SELECT
# MAGIC   fs.signal_id,
# MAGIC   fs.transaction_id,
# MAGIC   fs.risk_score,
# MAGIC   CASE 
# MAGIC     WHEN fs.risk_score >= 0.8 THEN 'HIGH'
# MAGIC     WHEN fs.risk_score >= 0.5 THEN 'MODERATE'
# MAGIC     WHEN fs.risk_score >= 0.2 THEN 'LOW'
# MAGIC     ELSE 'MINIMAL'
# MAGIC   END as classification,
# MAGIC   fs.alert_level,
# MAGIC   fs.case_decision,
# MAGIC   fs.created_at,
# MAGIC   current_timestamp() as enriched_at
# MAGIC FROM payments.raw.fraud_signals fs
# MAGIC WHERE fs.signal_id NOT IN (SELECT DISTINCT signal_id FROM payments.silver.fraud_enriched);

# COMMAND ----------

# MAGIC %md
# MAGIC ## GOLD LAYER: DIMENSIONAL MODELING

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Gold Layer: Merchant Dimension
# MAGIC -- Create merchant master data dimension
# MAGIC 
# MAGIC INSERT INTO payments.gold.dim_merchant
# MAGIC SELECT DISTINCT
# MAGIC   merchant_id,
# MAGIC   'Merchant ' || merchant_id as merchant_name,
# MAGIC   current_timestamp() as created_at
# MAGIC FROM payments.silver.payment_validated pv
# MAGIC WHERE merchant_id NOT IN (SELECT DISTINCT merchant_id FROM payments.gold.dim_merchant);

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Gold Layer: Customer Dimension
# MAGIC -- Create customer master data dimension with PII classification
# MAGIC 
# MAGIC INSERT INTO payments.gold.dim_customer
# MAGIC SELECT DISTINCT
# MAGIC   customer_id,
# MAGIC   'Customer ' || customer_id as customer_name,
# MAGIC   current_timestamp() as created_at
# MAGIC FROM payments.silver.payment_validated pv
# MAGIC WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM payments.gold.dim_customer);

# COMMAND ----------

# MAGIC %md
# MAGIC ## GOLD LAYER: FACT TABLES AND ANALYTICS

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Gold Layer: Payment Fact Table
# MAGIC -- Create denormalized fact table combining payments and fraud signals
# MAGIC 
# MAGIC INSERT INTO payments.gold.fact_payments
# MAGIC SELECT
# MAGIC   pv.payment_id,
# MAGIC   pv.merchant_id,
# MAGIC   pv.customer_id,
# MAGIC   pv.amount,
# MAGIC   pv.currency,
# MAGIC   pv.status,
# MAGIC   fe.signal_id as fraud_signal_id,
# MAGIC   fe.risk_score,
# MAGIC   pv.created_at
# MAGIC FROM payments.silver.payment_validated pv
# MAGIC LEFT JOIN payments.silver.fraud_enriched fe
# MAGIC   ON pv.payment_id = fe.transaction_id
# MAGIC WHERE pv.payment_id NOT IN (SELECT DISTINCT payment_id FROM payments.gold.fact_payments);

# COMMAND ----------

# MAGIC %md
# MAGIC ## SUMMARY STATISTICS

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC   COUNT(*) as raw_payment_records,
# MAGIC   (SELECT COUNT(*) FROM payments.raw.fraud_signals) as raw_fraud_signals,
# MAGIC   (SELECT COUNT(*) FROM payments.silver.payment_validated) as silver_payments,
# MAGIC   (SELECT COUNT(*) FROM payments.silver.fraud_enriched) as silver_fraud,
# MAGIC   (SELECT COUNT(*) FROM payments.gold.dim_merchant) as gold_merchants,
# MAGIC   (SELECT COUNT(*) FROM payments.gold.dim_customer) as gold_customers,
# MAGIC   (SELECT COUNT(*) FROM payments.gold.fact_payments) as gold_facts
# MAGIC FROM payments.raw.payment_transactions;

# COMMAND ----------

print("✅ SQL Transformation Pipeline completed successfully!")
print(f"Execution timestamp: {datetime.utcnow().isoformat()}")

from datetime import datetime
