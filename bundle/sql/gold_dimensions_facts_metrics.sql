-- Gold Layer: Dimensions, Facts, and Metrics
-- Business-ready analytics tables

-- COMMAND ----------

-- DIMENSION: Date Dimension
-- Calendar table for temporal analysis

CREATE OR REPLACE TABLE payments.gold.dim_date AS
WITH date_range AS (
  SELECT CAST(DATE_TRUNC('day', DATEADD(day, -seq, CURRENT_DATE)) AS DATE) as date_key
  FROM (SELECT EXPLODE(SEQUENCE(0, 730))) t(seq)
)
SELECT
  CAST(FORMAT_STRING('%04d%02d%02d', YEAR(date_key), MONTH(date_key), DAY(date_key)) AS STRING) as date_key,
  date_key as calendar_date,
  YEAR(date_key) as year,
  QUARTER(date_key) as quarter,
  MONTH(date_key) as month_number,
  DATE_FORMAT(date_key, 'MMMM') as month_name,
  WEEK(date_key) as week_number,
  DAY(date_key) as day_of_month,
  DAYOFWEEK(date_key) as day_of_week,
  DATE_FORMAT(date_key, 'EEEE') as day_name,
  CASE 
    WHEN DAYOFWEEK(date_key) IN (1, 7) THEN 1 
    ELSE 0 
  END as is_weekend,
  CASE 
    WHEN MONTH(date_key) IN (1, 4, 7, 10) AND DAY(date_key) = 1 THEN 1
    ELSE 0
  END as is_quarter_start
FROM date_range;

-- COMMAND ----------

-- DIMENSION: Merchant Dimension
-- Unique merchants with attributes

CREATE OR REPLACE TABLE payments.gold.dim_merchant AS
SELECT DISTINCT
  merchant_id,
  merchant_id as merchant_code,
  CASE 
    WHEN LENGTH(merchant_id) > 0 THEN CONCAT('Merchant_', merchant_id)
    ELSE 'Unknown'
  END as merchant_name,
  COUNT(*) OVER (PARTITION BY merchant_id) as total_transactions,
  CURRENT_TIMESTAMP() as last_updated
FROM payments.silver.transactions_fact
GROUP BY merchant_id;

-- COMMAND ----------

-- DIMENSION: Customer Dimension
-- Unique customers with risk profiles

CREATE OR REPLACE TABLE payments.gold.dim_customer AS
SELECT DISTINCT
  customer_id,
  customer_id as customer_code,
  CASE 
    WHEN LENGTH(customer_id) > 0 THEN CONCAT('Customer_', customer_id)
    ELSE 'Unknown'
  END as customer_name,
  COUNT(*) OVER (PARTITION BY customer_id) as total_transactions,
  AVG(risk_score) OVER (PARTITION BY customer_id) as avg_risk_score,
  MAX(risk_score) OVER (PARTITION BY customer_id) as max_risk_score,
  SUM(CASE WHEN fraud_decision = 'DECLINED' THEN 1 ELSE 0 END) 
    OVER (PARTITION BY customer_id) as fraud_decline_count,
  CURRENT_TIMESTAMP() as last_updated
FROM payments.silver.transactions_fact;

-- COMMAND ----------

-- DIMENSION: Payment Method Dimension
-- Payment method lookup

CREATE OR REPLACE TABLE payments.gold.dim_payment_method AS
SELECT DISTINCT
  payment_method,
  payment_method as method_code,
  CASE 
    WHEN payment_method = 'CREDIT_CARD' THEN 'Credit Card'
    WHEN payment_method = 'DEBIT_CARD' THEN 'Debit Card'
    WHEN payment_method = 'ACH' THEN 'Bank Transfer (ACH)'
    WHEN payment_method = 'WIRE' THEN 'Wire Transfer'
    WHEN payment_method = 'DIGITAL_WALLET' THEN 'Digital Wallet'
    ELSE 'Other'
  END as method_name,
  CASE 
    WHEN payment_method IN ('CREDIT_CARD', 'DEBIT_CARD') THEN 'Card'
    WHEN payment_method IN ('ACH', 'WIRE') THEN 'Bank'
    WHEN payment_method = 'DIGITAL_WALLET' THEN 'Wallet'
    ELSE 'Other'
  END as method_category
FROM payments.silver.transactions_fact
WHERE payment_method IS NOT NULL
GROUP BY payment_method;

-- COMMAND ----------

-- FACT: Transactions Fact Table
-- Denormalized fact table for performance

CREATE OR REPLACE TABLE payments.gold.fact_transactions AS
SELECT
  t.transaction_id,
  CAST(FORMAT_STRING('%04d%02d%02d', YEAR(t.transaction_date), MONTH(t.transaction_date), DAY(t.transaction_date)) AS STRING) as date_key,
  t.merchant_id,
  t.customer_id,
  t.payment_method,
  t.amount as transaction_amount,
  t.currency,
  CAST(t.amount AS DECIMAL(18, 2)) as amount_usd,
  t.status as payment_status,
  t.risk_score,
  t.fraud_risk_level,
  t.fraud_decision,
  t.overall_risk_category,
  CASE 
    WHEN t.status = 'CAPTURED' THEN t.amount
    ELSE 0
  END as captured_amount,
  CASE 
    WHEN t.status = 'REFUNDED' THEN t.amount
    ELSE 0
  END as refunded_amount,
  CASE 
    WHEN t.status IN ('DECLINED', 'FAILED') THEN t.amount
    ELSE 0
  END as failed_amount,
  CASE 
    WHEN t.fraud_decision = 'DECLINED' THEN t.amount
    ELSE 0
  END as fraud_blocked_amount,
  t.transaction_date as transaction_timestamp,
  t.payment_updated_at as status_updated_at,
  CURRENT_TIMESTAMP() as loaded_at
FROM payments.silver.transactions_fact t;

-- COMMAND ----------

-- METRIC VIEW: Daily Payment Summary
-- Daily aggregated payment metrics

CREATE OR REPLACE VIEW payments.gold.metric_daily_payment_summary AS
SELECT
  d.calendar_date,
  d.year,
  d.quarter,
  d.month_number,
  d.month_name,
  d.week_number,
  d.day_name,
  COUNT(DISTINCT f.transaction_id) as total_transactions,
  COUNT(DISTINCT f.merchant_id) as active_merchants,
  COUNT(DISTINCT f.customer_id) as active_customers,
  SUM(f.transaction_amount) as total_volume,
  AVG(f.transaction_amount) as avg_transaction_amount,
  MIN(f.transaction_amount) as min_transaction_amount,
  MAX(f.transaction_amount) as max_transaction_amount,
  STDDEV(f.transaction_amount) as stddev_transaction_amount,
  SUM(CASE WHEN f.payment_status = 'CAPTURED' THEN 1 ELSE 0 END) as successful_transactions,
  SUM(CASE WHEN f.payment_status IN ('DECLINED', 'FAILED') THEN 1 ELSE 0 END) as failed_transactions,
  SUM(CASE WHEN f.fraud_decision = 'DECLINED' THEN 1 ELSE 0 END) as fraud_blocked_transactions,
  CAST(SUM(CASE WHEN f.payment_status = 'CAPTURED' THEN 1 ELSE 0 END) AS FLOAT) 
    / NULLIF(COUNT(DISTINCT f.transaction_id), 0) * 100 as success_rate_pct,
  AVG(f.risk_score) as avg_risk_score,
  COUNT(CASE WHEN f.overall_risk_category = 'HIGH_RISK' THEN 1 END) as high_risk_count,
  COUNT(CASE WHEN f.overall_risk_category = 'MEDIUM_RISK' THEN 1 END) as medium_risk_count,
  COUNT(CASE WHEN f.overall_risk_category = 'LOW_RISK' THEN 1 END) as low_risk_count,
  SUM(f.captured_amount) as captured_volume,
  SUM(f.refunded_amount) as refunded_volume,
  SUM(f.fraud_blocked_amount) as fraud_blocked_volume
FROM payments.gold.dim_date d
LEFT JOIN payments.gold.fact_transactions f ON d.date_key = CAST(FORMAT_STRING('%04d%02d%02d', YEAR(f.transaction_timestamp), MONTH(f.transaction_timestamp), DAY(f.transaction_timestamp)) AS STRING)
GROUP BY 
  d.calendar_date, d.year, d.quarter, d.month_number, d.month_name, 
  d.week_number, d.day_name;

-- COMMAND ----------

-- METRIC VIEW: Fraud Analytics
-- Fraud-focused metrics by dimension

CREATE OR REPLACE VIEW payments.gold.metric_fraud_analytics AS
SELECT
  f.merchant_id,
  dm.merchant_name,
  COUNT(DISTINCT f.transaction_id) as total_transactions,
  COUNT(DISTINCT f.customer_id) as unique_customers,
  SUM(f.transaction_amount) as total_volume,
  COUNT(CASE WHEN f.fraud_decision = 'DECLINED' THEN 1 END) as fraud_blocked_count,
  SUM(CASE WHEN f.fraud_decision = 'DECLINED' THEN f.transaction_amount ELSE 0 END) as fraud_blocked_volume,
  CAST(COUNT(CASE WHEN f.fraud_decision = 'DECLINED' THEN 1 END) AS FLOAT) 
    / NULLIF(COUNT(DISTINCT f.transaction_id), 0) * 100 as fraud_block_rate_pct,
  AVG(f.risk_score) as avg_risk_score,
  MAX(f.risk_score) as max_risk_score,
  COUNT(CASE WHEN f.overall_risk_category = 'HIGH_RISK' THEN 1 END) as high_risk_transactions,
  COUNT(CASE WHEN f.overall_risk_category = 'MEDIUM_RISK' THEN 1 END) as medium_risk_transactions,
  COUNT(CASE WHEN f.payment_status = 'CAPTURED' THEN 1 ELSE 0 END) as successful_captures,
  COUNT(CASE WHEN f.payment_status IN ('DECLINED', 'FAILED') THEN 1 ELSE 0 END) as failed_transactions,
  CURRENT_TIMESTAMP() as metric_calculated_at
FROM payments.gold.fact_transactions f
LEFT JOIN payments.gold.dim_merchant dm ON f.merchant_id = dm.merchant_id
GROUP BY f.merchant_id, dm.merchant_name;

-- COMMAND ----------

-- METRIC VIEW: Customer Risk Profile
-- Customer-level risk and behavior metrics

CREATE OR REPLACE VIEW payments.gold.metric_customer_risk_profile AS
SELECT
  f.customer_id,
  dc.customer_name,
  COUNT(DISTINCT f.transaction_id) as transaction_count,
  COUNT(DISTINCT f.merchant_id) as merchant_count,
  SUM(f.transaction_amount) as total_volume,
  AVG(f.risk_score) as avg_risk_score,
  MAX(f.risk_score) as max_risk_score,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.risk_score) as median_risk_score,
  COUNT(CASE WHEN f.overall_risk_category = 'HIGH_RISK' THEN 1 END) as high_risk_count,
  COUNT(CASE WHEN f.overall_risk_category = 'MEDIUM_RISK' THEN 1 END) as medium_risk_count,
  COUNT(CASE WHEN f.payment_status = 'CAPTURED' THEN 1 ELSE 0 END) as successful_transactions,
  COUNT(CASE WHEN f.fraud_decision = 'DECLINED' THEN 1 END) as fraud_blocked_count,
  SUM(CASE WHEN f.fraud_decision = 'DECLINED' THEN f.transaction_amount ELSE 0 END) as fraud_blocked_amount,
  CASE 
    WHEN AVG(f.risk_score) > 0.7 THEN 'VERY_HIGH_RISK'
    WHEN AVG(f.risk_score) > 0.5 THEN 'HIGH_RISK'
    WHEN AVG(f.risk_score) > 0.25 THEN 'MEDIUM_RISK'
    ELSE 'LOW_RISK'
  END as risk_classification,
  MAX(f.transaction_timestamp) as last_transaction_date,
  CURRENT_TIMESTAMP() as profile_calculated_at
FROM payments.gold.fact_transactions f
LEFT JOIN payments.gold.dim_customer dc ON f.customer_id = dc.customer_id
GROUP BY f.customer_id, dc.customer_name;
