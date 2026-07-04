# Pipeline Execution Guide

## Overview

The Teksystems.Walkthrough bundle includes two complementary data pipelines:

1. **Data Generation Pipeline** (Python) - Generates synthetic payment data
2. **SQL Transformation Pipeline** (SQL/Python) - Transforms data through medallion layers

## Pipeline Jobs

| Job | ID | Type | Purpose |
|-----|--|----|---------|
| Data Generation | 301872156246768 | Python | Generate 100 payments + fraud signals |
| SQL Transformation | 287887081625290 | SQL/Python | Transform raw → silver → gold |

## Running Pipelines

### Option 1: Manual Execution

Run data generation first, then transformations:

```bash
# Generate test data
databricks jobs run-now --job-id 301872156246768

# Wait for completion (check job run ID), then run transformations
databricks jobs run-now --job-id 287887081625290
```

### Option 2: Scheduled Execution (Future)

Add cron schedules to `databricks.yml`:

```yaml
resources:
  jobs:
    data_generation_pipeline:
      ...
      schedule:
        quartz_cron_expression: "0 0 * * *"  # Daily at midnight
        timezone_id: "UTC"
        pause_status: "UNPAUSED"
    
    sql_transformation_pipeline:
      ...
      schedule:
        quartz_cron_expression: "0 1 * * *"  # Daily at 1 AM (after data gen)
        timezone_id: "UTC"
        pause_status: "UNPAUSED"
```

Then redeploy:
```bash
databricks bundle deploy --target dev
```

## Data Pipeline Details

### Phase 1: Data Generation

**File**: `bundle/python_pipelines/data_generation_pipeline.py`

**Inputs**:
- Configuration: 100 payment records, 10 merchants, 50 customers

**Outputs**:
- `payments.raw.payment_transactions`: 100 records
  - Fields: payment_id, merchant_id, customer_id, amount, currency, payment_method, status, timestamps, metadata
  - Tokenized sensitive payment data via PaymentProcessor
  
- `payments.raw.fraud_signals`: 100 signals
  - Fields: signal_id, transaction_id, risk_score, classification, alert_level, case_decision, created_at
  - Risk scores computed by SimpleFraudEngine

**Data Characteristics**:
- Amounts: $10 - $5,000 USD
- Payment methods: Credit Card, Debit Card, ACH, Wire, Digital Wallet
- Fraud risk scores: 0.0 - 1.0 (scaled)
- Timestamps: Last 24 hours from execution time

### Phase 2: SQL Transformations

**File**: `bundle/python_pipelines/sql_transformation_pipeline.py`

**Silver Layer** (Cleaned & Standardized):
- `payments.silver.payment_validated`
  - Standardized enums (CREDIT_CARD, DEBIT_CARD, etc.)
  - Normalized currency to uppercase
  - Added PCI classification column
  - Deduplicated (won't re-insert existing payment_ids)
  - 90-day filter (recent data only)

- `payments.silver.fraud_enriched`
  - Standardized risk classification (HIGH, MODERATE, LOW, MINIMAL)
  - Enriched with alert levels
  - Deduplicated by signal_id

**Gold Layer** (Analytics Ready):
- `payments.gold.dim_merchant`
  - Distinct merchants from silver payments
  - Merchant name (generated from ID)
  - Created timestamp

- `payments.gold.dim_customer`
  - Distinct customers from silver payments
  - Customer name (generated from ID)
  - PII classification applied
  - Created timestamp

- `payments.gold.fact_payments`
  - Denormalized fact table
  - Payment details with joined fraud signal data
  - Left outer join (some payments may have no fraud signals)
  - Deduplicated by payment_id

## Monitoring & Verification

### Check Job Status

```bash
# Get specific job details
databricks jobs get --job-id 301872156246768

# List recent runs
databricks jobs list-runs --job-id 301872156246768 --limit 5
```

### Verify Data in Workspace

```sql
-- Check raw layer row counts
SELECT COUNT(*) as payment_count FROM payments.raw.payment_transactions;
SELECT COUNT(*) as fraud_count FROM payments.raw.fraud_signals;

-- Check silver layer
SELECT COUNT(*) as validated_count FROM payments.silver.payment_validated;
SELECT COUNT(*) as enriched_count FROM payments.silver.fraud_enriched;

-- Check gold layer
SELECT COUNT(*) as merchant_count FROM payments.gold.dim_merchant;
SELECT COUNT(*) as customer_count FROM payments.gold.dim_customer;
SELECT COUNT(*) as fact_count FROM payments.gold.fact_payments;

-- Sample fact table with fraud signals
SELECT 
  f.payment_id,
  f.amount,
  f.status,
  f.risk_score,
  f.fraud_signal_id
FROM payments.gold.fact_payments f
WHERE f.fraud_signal_id IS NOT NULL
LIMIT 10;
```

## Troubleshooting

### Pipeline Fails Due to Missing Data
**Symptom**: Silver transformation fails with "payments.raw.payment_transactions not found"

**Solution**:
1. Run Data Generation Pipeline first
2. Wait for completion (check status in Databricks)
3. Then run SQL Transformation Pipeline

### Duplicate Data After Re-runs
**Expected Behavior**: Pipelines have deduplication logic
- Silver layer: Checks `payment_id` / `signal_id` to avoid duplicates
- Gold layer: Checks `payment_id` to avoid fact table duplicates

**Note**: Running the pipeline multiple times will not create duplicates, only new data

### Wheel Package Not Found
**Symptom**: "ModuleNotFoundError: No module named 'src'"

**Solution**:
- Ensure wheel is included in bundle: `bundle/python/teksystems_walkthrough-0.1.0-py3-none-any.whl`
- Wheel is automatically referenced in job configuration
- If missing, rebuild with: `python -m build` and copy to bundle/python/

## PCI-DSS Compliance

Both pipelines respect PCI-DSS data classification:

- **Raw Layer**: All data marked as PCI_DSS_RESTRICTED
- **Silver Layer**: Classification inherited from raw
- **Gold Layer**: Customer dimension marked PII_RESTRICTED

Sensitive fields (card numbers, CVV) are tokenized by PaymentProcessor before reaching Databricks.

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Data Generation Runtime | ~30-60 seconds |
| SQL Transformation Runtime | ~30-45 seconds |
| Total E2E Runtime | ~2 minutes |
| Raw Data Size | ~500 KB (100 payments) |
| Gold Layer Size | ~300 KB (dimension + fact) |
| Incremental Cost | Minimal (serverless compute) |

## Next Steps

1. **Test Pipelines**: Run manually first to verify data
2. **Add Scheduling**: Configure cron schedules for daily/hourly runs
3. **Add Notifications**: Configure job notifications for failures
4. **Monitor Quality**: Add data quality checks in transformation pipeline
5. **Extend**: Add more payment processors, fraud models, or downstream consumers

## Files Reference

- **Configuration**: `databricks.yml` (defines job specs, schedules, timeouts)
- **Python Pipeline**: `bundle/python_pipelines/data_generation_pipeline.py`
- **SQL Pipeline**: `bundle/python_pipelines/sql_transformation_pipeline.py`
- **SQL Script**: `bundle/sql_pipelines/sql_transformation_pipeline.sql` (standalone)
- **Wheel Package**: `bundle/python/teksystems_walkthrough-0.1.0-py3-none-any.whl`
