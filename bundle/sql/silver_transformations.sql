-- Silver Layer Transformations
-- This Databricks notebook contains transformations from raw to silver layer

-- COMMAND ----------

-- Bronze to Silver: Payments
-- Clean and standardize payment transactions

CREATE OR REPLACE TABLE payments.silver.payments_cleaned AS
SELECT
  payment_id,
  merchant_id,
  customer_id,
  CAST(amount AS DECIMAL(18, 2)) as amount,
  UPPER(currency) as currency,
  CASE 
    WHEN payment_method = 'credit_card' THEN 'CREDIT_CARD'
    WHEN payment_method = 'debit_card' THEN 'DEBIT_CARD'
    WHEN payment_method = 'ach' THEN 'ACH'
    WHEN payment_method = 'wire' THEN 'WIRE'
    WHEN payment_method = 'digital_wallet' THEN 'DIGITAL_WALLET'
    ELSE 'UNKNOWN'
  END as payment_method_normalized,
  CASE 
    WHEN status = 'authorized' THEN 'AUTHORIZED'
    WHEN status = 'captured' THEN 'CAPTURED'
    WHEN status = 'declined' THEN 'DECLINED'
    WHEN status = 'refunded' THEN 'REFUNDED'
    WHEN status = 'failed' THEN 'FAILED'
    ELSE 'UNKNOWN'
  END as status_normalized,
  CAST(created_at AS TIMESTAMP) as payment_created_at,
  CAST(updated_at AS TIMESTAMP) as payment_updated_at,
  current_timestamp() as processed_at,
  _metadata.file_path,
  _metadata.file_modification_time
FROM payments.raw.payments_raw
WHERE created_at >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS;

-- COMMAND ----------

-- Bronze to Silver: Fraud Signals
-- Enrich and standardize fraud signals

CREATE OR REPLACE TABLE payments.silver.fraud_signals_cleaned AS
SELECT
  signal_id,
  transaction_id,
  CAST(risk_score AS DECIMAL(3, 2)) as risk_score,
  CASE 
    WHEN risk_score < 0.25 THEN 'LOW'
    WHEN risk_score < 0.5 THEN 'MEDIUM'
    WHEN risk_score < 0.75 THEN 'HIGH'
    ELSE 'CRITICAL'
  END as risk_level_derived,
  risk_level,
  alerts,
  CASE 
    WHEN decision = 'approve' THEN 'APPROVED'
    WHEN decision = 'decline' THEN 'DECLINED'
    WHEN decision = 'review' THEN 'UNDER_REVIEW'
    WHEN decision = 'challenge' THEN 'CHALLENGED'
    WHEN decision = 'block' THEN 'BLOCKED'
    ELSE 'UNKNOWN'
  END as decision_normalized,
  CASE 
    WHEN case_status = 'pending' THEN 'PENDING'
    WHEN case_status = 'under_review' THEN 'UNDER_REVIEW'
    WHEN case_status = 'resolved' THEN 'RESOLVED'
    WHEN case_status = 'escalated' THEN 'ESCALATED'
    WHEN case_status = 'closed' THEN 'CLOSED'
    ELSE 'UNKNOWN'
  END as case_status_normalized,
  CAST(created_at AS TIMESTAMP) as signal_created_at,
  current_timestamp() as processed_at
FROM payments.raw.fraud_signals_raw
WHERE created_at >= CURRENT_TIMESTAMP() - INTERVAL 90 DAYS;

-- COMMAND ----------

-- Payment and Fraud Join
-- Combine payment and fraud data for enriched analysis

CREATE OR REPLACE TABLE payments.silver.payments_with_fraud AS
SELECT
  p.payment_id,
  p.merchant_id,
  p.customer_id,
  p.amount,
  p.currency,
  p.payment_method_normalized as payment_method,
  p.status_normalized as status,
  COALESCE(f.risk_score, 0.0) as risk_score,
  COALESCE(f.risk_level, 'NOT_EVALUATED') as fraud_risk_level,
  COALESCE(f.decision_normalized, 'NO_DECISION') as fraud_decision,
  f.alerts as fraud_alerts,
  CASE 
    WHEN f.decision_normalized IN ('DECLINED', 'BLOCKED') THEN 'HIGH_RISK'
    WHEN f.decision_normalized = 'CHALLENGED' THEN 'MEDIUM_RISK'
    WHEN f.risk_score > 0.5 THEN 'MEDIUM_RISK'
    WHEN f.risk_score > 0.25 THEN 'LOW_RISK'
    ELSE 'APPROVED'
  END as overall_risk_category,
  p.payment_created_at,
  p.payment_updated_at,
  COALESCE(f.signal_created_at, p.payment_created_at) as latest_event_at,
  p.processed_at
FROM payments.silver.payments_cleaned p
LEFT JOIN payments.silver.fraud_signals_cleaned f 
  ON p.payment_id = f.transaction_id;

-- COMMAND ----------

-- Transactions fact table (de-duplicated)
-- One record per payment with associated fraud info

CREATE OR REPLACE TABLE payments.silver.transactions_fact AS
SELECT
  payment_id as transaction_id,
  merchant_id,
  customer_id,
  amount,
  currency,
  payment_method,
  status,
  risk_score,
  fraud_risk_level,
  fraud_decision,
  overall_risk_category,
  payment_created_at as transaction_date,
  payment_updated_at,
  latest_event_at,
  ROW_NUMBER() OVER (PARTITION BY payment_id ORDER BY payment_updated_at DESC) as row_number,
  current_timestamp() as batch_timestamp
FROM payments.silver.payments_with_fraud
WHERE ROW_NUMBER() OVER (PARTITION BY payment_id ORDER BY payment_updated_at DESC) = 1;
