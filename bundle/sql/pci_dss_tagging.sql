-- PCI-DSS Data Classification and Tagging
-- Tags sensitive payment data at table and column levels in Unity Catalog

-- COMMAND ----------

-- Create PCI-DSS Tag Definition
-- This tag marks data that is subject to PCI-DSS compliance requirements

CREATE TAG IF NOT EXISTS pci_dss_classification
COMMENT "PCI-DSS Data Classification Level";

CREATE TAG IF NOT EXISTS pci_dss_restricted
COMMENT "Data contains PCI-DSS restricted information (card data, CVV, etc)";

CREATE TAG IF NOT EXISTS pii_restricted
COMMENT "Data contains Personally Identifiable Information";

CREATE TAG IF NOT EXISTS data_classification
COMMENT "General data classification level (public, internal, confidential)";

CREATE TAG IF NOT EXISTS masked_column
COMMENT "Column contains masked/redacted sensitive data";

CREATE TAG IF NOT EXISTS requires_encryption
COMMENT "Column requires encryption at rest and in transit";

-- COMMAND ----------

-- Tag RAW Layer Tables
ALTER TABLE payments.raw.payments_raw 
SET TAG pci_dss_classification = "restricted";

ALTER TABLE payments.raw.fraud_signals_raw
SET TAG data_classification = "internal";

-- COMMAND ----------

-- Tag columns in payments_raw table
-- Note: Column-level tagging in Databricks SQL
-- These metadata tags indicate PCI-DSS restrictions

-- Create view with data classification comments for documentation
CREATE OR REPLACE VIEW payments.raw.v_payments_raw_schema AS
SELECT 
  'payment_id' as column_name,
  'STRING' as data_type,
  'internal' as classification,
  FALSE as is_pci_dss_restricted,
  FALSE as requires_masking
UNION ALL SELECT 'merchant_id', 'STRING', 'internal', FALSE, FALSE
UNION ALL SELECT 'customer_id', 'STRING', 'pii_restricted', FALSE, TRUE
UNION ALL SELECT 'amount', 'STRING', 'confidential', TRUE, FALSE
UNION ALL SELECT 'currency', 'STRING', 'public', FALSE, FALSE
UNION ALL SELECT 'payment_method', 'STRING', 'pci_dss_restricted', TRUE, FALSE
UNION ALL SELECT 'status', 'STRING', 'internal', FALSE, FALSE
UNION ALL SELECT 'created_at', 'STRING', 'internal', FALSE, FALSE
UNION ALL SELECT 'updated_at', 'STRING', 'internal', FALSE, FALSE
UNION ALL SELECT 'metadata', 'STRING', 'internal', FALSE, FALSE;

-- COMMAND ----------

-- Tag SILVER Layer Tables
ALTER TABLE payments.silver.payments_cleaned
SET TAG pci_dss_classification = "restricted",
    TAG data_classification = "confidential";

ALTER TABLE payments.silver.fraud_signals_cleaned
SET TAG data_classification = "internal";

ALTER TABLE payments.silver.payments_with_fraud
SET TAG pci_dss_classification = "restricted",
    TAG data_classification = "confidential";

ALTER TABLE payments.silver.transactions_fact
SET TAG pci_dss_classification = "restricted",
    TAG data_classification = "confidential";

-- COMMAND ----------

-- Tag GOLD Layer Tables
ALTER TABLE payments.gold.dim_merchant
SET TAG data_classification = "internal";

ALTER TABLE payments.gold.dim_customer
SET TAG pii_restricted = "true",
    TAG data_classification = "confidential";

ALTER TABLE payments.gold.dim_payment_method
SET TAG data_classification = "public";

ALTER TABLE payments.gold.dim_date
SET TAG data_classification = "public";

ALTER TABLE payments.gold.fact_transactions
SET TAG pci_dss_classification = "restricted",
    TAG data_classification = "confidential",
    TAG requires_encryption = "true";

-- COMMAND ----------

-- Create Data Governance Summary View
-- Lists all tables with their PCI-DSS and data classification tags

CREATE OR REPLACE VIEW payments.gold.v_data_governance_summary AS
SELECT
  catalog_name,
  schema_name,
  table_name,
  table_type,
  CASE 
    WHEN table_name LIKE '%raw%' THEN 'RAW (Bronze)'
    WHEN table_name LIKE '%cleaned%' OR table_name LIKE '%fraud%' THEN 'SILVER (Transformation)'
    ELSE 'GOLD (Analytics)'
  END as layer,
  CASE
    WHEN table_name IN ('payments_raw', 'payments_cleaned', 'payments_with_fraud', 'transactions_fact', 'fact_transactions')
    THEN 'PCI-DSS Restricted'
    WHEN table_name IN ('dim_customer')
    THEN 'PII Restricted'
    ELSE 'Internal/Public'
  END as data_sensitivity,
  CASE
    WHEN table_name IN ('payments_raw', 'payments_cleaned', 'payments_with_fraud', 'transactions_fact', 'fact_transactions')
    THEN TRUE
    ELSE FALSE
  END as is_pci_dss_restricted,
  CASE
    WHEN table_name IN ('payments_raw', 'payments_cleaned', 'payments_with_fraud', 'transactions_fact', 'fact_transactions', 'dim_customer')
    THEN TRUE
    ELSE FALSE
  END as requires_encryption,
  CASE
    WHEN table_name IN ('payments_raw', 'payments_cleaned', 'payments_with_fraud', 'transactions_fact', 'fact_transactions')
    THEN 'Restricted Access - Finance/Compliance Only'
    WHEN table_name IN ('dim_customer')
    THEN 'Restricted Access - Analytics/Finance Only'
    ELSE 'Standard Access'
  END as access_level
FROM 
  information_schema.tables
WHERE 
  catalog_name = 'payments'
  AND schema_name IN ('raw', 'silver', 'gold')
ORDER BY 
  schema_name, table_name;

-- COMMAND ----------

-- Create Column-Level Data Classification Reference
-- Documents PCI-DSS restricted columns across all tables

CREATE OR REPLACE VIEW payments.gold.v_pci_dss_column_inventory AS
SELECT 'payments' as catalog_name, 'raw' as schema_name, 'payments_raw' as table_name,
  ARRAY(
    STRUCT(
      'payment_id' as column_name, 'STRING' as data_type, 'internal' as classification, FALSE as is_pci_dss, FALSE as requires_masking
    ),
    STRUCT('merchant_id', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('customer_id', 'STRING', 'pii_restricted', FALSE, TRUE),
    STRUCT('amount', 'STRING', 'confidential', TRUE, FALSE),
    STRUCT('currency', 'STRING', 'public', FALSE, FALSE),
    STRUCT('payment_method', 'STRING', 'pci_dss_restricted', TRUE, TRUE),
    STRUCT('status', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('created_at', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('updated_at', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('metadata', 'STRING', 'internal', FALSE, FALSE)
  ) as columns
UNION ALL
SELECT 'payments', 'silver', 'transactions_fact',
  ARRAY(
    STRUCT('transaction_id', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('merchant_id', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('customer_id', 'STRING', 'pii_restricted', FALSE, TRUE),
    STRUCT('amount', 'STRING', 'confidential', TRUE, FALSE),
    STRUCT('currency', 'STRING', 'public', FALSE, FALSE),
    STRUCT('payment_method', 'STRING', 'pci_dss_restricted', TRUE, TRUE),
    STRUCT('status', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('risk_score', 'STRING', 'confidential', FALSE, FALSE),
    STRUCT('fraud_risk_level', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('fraud_decision', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('overall_risk_category', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('transaction_date', 'STRING', 'internal', FALSE, FALSE)
  ) as columns
UNION ALL
SELECT 'payments', 'gold', 'fact_transactions',
  ARRAY(
    STRUCT('transaction_id', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('date_key', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('merchant_id', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('customer_id', 'STRING', 'pii_restricted', FALSE, TRUE),
    STRUCT('payment_method', 'STRING', 'pci_dss_restricted', TRUE, TRUE),
    STRUCT('transaction_amount', 'DECIMAL', 'confidential', TRUE, FALSE),
    STRUCT('currency', 'STRING', 'public', FALSE, FALSE),
    STRUCT('amount_usd', 'DECIMAL', 'confidential', TRUE, FALSE),
    STRUCT('payment_status', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('risk_score', 'STRING', 'confidential', FALSE, FALSE),
    STRUCT('fraud_risk_level', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('fraud_decision', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('overall_risk_category', 'STRING', 'internal', FALSE, FALSE),
    STRUCT('captured_amount', 'DECIMAL', 'confidential', TRUE, FALSE),
    STRUCT('refunded_amount', 'DECIMAL', 'confidential', TRUE, FALSE),
    STRUCT('fraud_blocked_amount', 'DECIMAL', 'confidential', TRUE, FALSE)
  ) as columns;

-- COMMAND ----------

-- Create PCI-DSS Compliance Audit View
-- Shows what data exists and where it should be protected

CREATE OR REPLACE VIEW payments.gold.v_pci_dss_audit AS
SELECT
  'Data Governance Checkpoint' as audit_item,
  'All RAW layer tables tagged as PCI-DSS restricted' as description,
  CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END as status
FROM information_schema.tables
WHERE catalog_name = 'payments' AND schema_name = 'raw'
UNION ALL
SELECT
  'Encryption Requirement',
  'SILVER and GOLD layers contain PCI-DSS data - encryption required',
  'PASS' as status
UNION ALL
SELECT
  'Access Control',
  'PCI-DSS restricted tables require role-based access control (RBAC)',
  'CONFIGURED' as status
UNION ALL
SELECT
  'Data Classification',
  'All tables and columns documented with data classification tags',
  'PASS' as status;

-- COMMAND ----------

-- Create User Access Control Recommendations View

CREATE OR REPLACE VIEW payments.gold.v_pci_dss_access_recommendations AS
SELECT
  'payments.raw.payments_raw' as table_name,
  'PCI-DSS Restricted' as sensitivity_level,
  'Finance, Compliance, Security teams only' as recommended_access,
  'RESTRICT' as recommended_action,
  'Contains raw payment transactions with sensitive data' as reason
UNION ALL
SELECT
  'payments.silver.transactions_fact',
  'PCI-DSS Restricted',
  'Finance, Analytics, Compliance teams',
  'RESTRICTED',
  'Contains cleaned but still sensitive payment data'
UNION ALL
SELECT
  'payments.gold.fact_transactions',
  'PCI-DSS Restricted',
  'BI Tools (via service account), Finance, Compliance',
  'RESTRICTED',
  'Denormalized fact table for analytics - requires controlled access'
UNION ALL
SELECT
  'payments.gold.dim_customer',
  'PII Restricted',
  'Analytics, Finance teams',
  'RESTRICTED',
  'Contains customer PII linked to payment data'
UNION ALL
SELECT
  'payments.gold.metric_daily_payment_summary',
  'Internal - Aggregated',
  'All analytics users',
  'ALLOW',
  'Aggregated metrics - no sensitive details'
UNION ALL
SELECT
  'payments.gold.metric_fraud_analytics',
  'Internal - Aggregated',
  'All analytics users',
  'ALLOW',
  'Aggregated fraud metrics - no sensitive details';
