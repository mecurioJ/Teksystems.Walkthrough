-- Databricks SQL
-- SQL Transformation Pipeline
-- Populates silver and gold layers from raw data

-- COMMAND ----------

-- SQL %md
-- # Medallion Transformation Pipeline (SQL)
-- 
-- This pipeline performs multi-layer transformations:
-- 1. **Raw → Silver**: Data cleaning, validation, and standardization
-- 2. **Silver → Gold**: Dimensional modeling and fact table creation

-- COMMAND ----------

-- ============================================================================
-- SILVER LAYER TRANSFORMATIONS
-- ============================================================================

-- COMMAND ----------

-- Silver Layer: Payment Validation
-- Clean, validate, and standardize payment transaction data

INSERT INTO payments.silver.payment_validated
SELECT
  pt.payment_id,
  pt.merchant_id,
  pt.customer_id,
  pt.amount,
  UPPER(pt.currency) as currency,
  CASE 
    WHEN LOWER(pt.payment_method) = 'credit_card' THEN 'CREDIT_CARD'
    WHEN LOWER(pt.payment_method) = 'debit_card' THEN 'DEBIT_CARD'
    WHEN LOWER(pt.payment_method) = 'ach' THEN 'ACH'
    WHEN LOWER(pt.payment_method) = 'wire' THEN 'WIRE'
    WHEN LOWER(pt.payment_method) = 'digital_wallet' THEN 'DIGITAL_WALLET'
    ELSE 'UNKNOWN'
  END as payment_method,
  CASE 
    WHEN LOWER(pt.status) = 'authorized' THEN 'AUTHORIZED'
    WHEN LOWER(pt.status) = 'captured' THEN 'CAPTURED'
    WHEN LOWER(pt.status) = 'declined' THEN 'DECLINED'
    WHEN LOWER(pt.status) = 'refunded' THEN 'REFUNDED'
    WHEN LOWER(pt.status) = 'failed' THEN 'FAILED'
    ELSE 'UNKNOWN'
  END as status,
  pt.created_at,
  pt.updated_at,
  'PCI_DSS_RESTRICTED' as pci_classification,
  current_timestamp() as load_ts
FROM payments.raw.payment_transactions pt
WHERE pt.created_at >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS
  AND pt.payment_id NOT IN (SELECT DISTINCT payment_id FROM payments.silver.payment_validated);

-- COMMAND ----------

-- Silver Layer: Fraud Signal Enrichment
-- Standardize and enrich fraud signals with classification

INSERT INTO payments.silver.fraud_enriched
SELECT
  fs.signal_id,
  fs.transaction_id,
  fs.risk_score,
  CASE 
    WHEN fs.risk_score >= 0.8 THEN 'HIGH'
    WHEN fs.risk_score >= 0.5 THEN 'MODERATE'
    WHEN fs.risk_score >= 0.2 THEN 'LOW'
    ELSE 'MINIMAL'
  END as classification,
  fs.alert_level,
  fs.case_decision,
  fs.created_at,
  current_timestamp() as enriched_at
FROM payments.raw.fraud_signals fs
WHERE fs.signal_id NOT IN (SELECT DISTINCT signal_id FROM payments.silver.fraud_enriched);

-- COMMAND ----------

-- ============================================================================
-- GOLD LAYER: DIMENSIONAL MODELING
-- ============================================================================

-- COMMAND ----------

-- Gold Layer: Merchant Dimension
-- Create merchant master data dimension

INSERT INTO payments.gold.dim_merchant
SELECT DISTINCT
  merchant_id,
  'Merchant ' || merchant_id as merchant_name,
  current_timestamp() as created_at
FROM payments.silver.payment_validated pv
WHERE merchant_id NOT IN (SELECT DISTINCT merchant_id FROM payments.gold.dim_merchant);

-- COMMAND ----------

-- Gold Layer: Customer Dimension
-- Create customer master data dimension with PII classification

INSERT INTO payments.gold.dim_customer
SELECT DISTINCT
  customer_id,
  'Customer ' || customer_id as customer_name,
  current_timestamp() as created_at
FROM payments.silver.payment_validated pv
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM payments.gold.dim_customer);

-- COMMAND ----------

-- ============================================================================
-- GOLD LAYER: FACT TABLES AND ANALYTICS
-- ============================================================================

-- COMMAND ----------

-- Gold Layer: Payment Fact Table
-- Create denormalized fact table combining payments and fraud signals

INSERT INTO payments.gold.fact_payments
SELECT
  pv.payment_id,
  pv.merchant_id,
  pv.customer_id,
  pv.amount,
  pv.currency,
  pv.status,
  fe.signal_id as fraud_signal_id,
  fe.risk_score,
  pv.created_at
FROM payments.silver.payment_validated pv
LEFT JOIN payments.silver.fraud_enriched fe
  ON pv.payment_id = fe.transaction_id
WHERE pv.payment_id NOT IN (SELECT DISTINCT payment_id FROM payments.gold.fact_payments);

-- COMMAND ----------

-- ============================================================================
-- SUMMARY STATISTICS
-- ============================================================================

-- COMMAND ----------

SELECT 
  COUNT(*) as raw_payment_records,
  (SELECT COUNT(*) FROM payments.raw.fraud_signals) as raw_fraud_signals,
  (SELECT COUNT(*) FROM payments.silver.payment_validated) as silver_payments,
  (SELECT COUNT(*) FROM payments.silver.fraud_enriched) as silver_fraud,
  (SELECT COUNT(*) FROM payments.gold.dim_merchant) as gold_merchants,
  (SELECT COUNT(*) FROM payments.gold.dim_customer) as gold_customers,
  (SELECT COUNT(*) FROM payments.gold.fact_payments) as gold_facts
FROM payments.raw.payment_transactions;

-- COMMAND ----------

-- Pipeline execution timestamp
SELECT 
  'SQL Transformation Pipeline' as pipeline_name,
  current_timestamp() as execution_timestamp,
  'SUCCESS' as status;
