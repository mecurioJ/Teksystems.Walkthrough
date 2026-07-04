# Databricks Medallion Architecture Bundle

## Overview

This bundle implements a complete **medallion data architecture** for payment processing on Databricks with three distinct layers:

```
Raw Data Stream                Silver Layer               Gold Layer
(Payment Processor)            (Transformation)          (Analytics)
     ↓                              ↓                         ↓
  RAW Schema                   SILVER Schema              GOLD Schema
  ├─ payments_raw         ├─ payments_cleaned     ├─ Dimensions
  ├─ fraud_signals_raw    ├─ fraud_signals_clean  │  ├─ dim_date
  └─ GL Volume            ├─ payments_with_fraud  │  ├─ dim_merchant
                          └─ transactions_fact    │  ├─ dim_customer
                                                  │  └─ dim_payment_method
                                                  ├─ Facts
                                                  │  └─ fact_transactions
                                                  └─ Metric Views
                                                     ├─ metric_daily_payment_summary
                                                     ├─ metric_fraud_analytics
                                                     └─ metric_customer_risk_profile
```

## Catalog Structure

**Catalog**: `payments`

### RAW Schema (Bronze Layer)
**Purpose**: Ingest raw data from external systems
- **Tables**:
  - `payments_raw` - Payment transactions from processor
  - `fraud_signals_raw` - Fraud detection signals
- **Volumes**:
  - `gl_reconciliation` - GL file reconciliation storage

### SILVER Schema (Transformation Layer)
**Purpose**: Clean, normalize, and enrich data
- **Tables**:
  - `payments_cleaned` - Standardized payment data
  - `fraud_signals_cleaned` - Normalized fraud signals
  - `payments_with_fraud` - Enriched payment + fraud data
  - `transactions_fact` - De-duplicated transaction records

### GOLD Schema (Analytics Layer)
**Purpose**: Business-ready analytics and reporting
- **Dimensions** (4 tables):
  - `dim_date` - 730-day calendar (time-based queries)
  - `dim_merchant` - Merchant master with metrics
  - `dim_customer` - Customer profiles with risk data
  - `dim_payment_method` - Payment method lookup
- **Facts** (1 table):
  - `fact_transactions` - Denormalized transaction data
- **Metric Views** (3 views):
  - `metric_daily_payment_summary` - Daily KPIs
  - `metric_fraud_analytics` - Fraud by merchant
  - `metric_customer_risk_profile` - Customer risk classification

## Bundle Contents

```
bundle/
├── databricks_medallion.yml              # Main bundle configuration
│                                         # Defines all resources and targets
├── README.md                             # Quick reference guide
├── python/
│   ├── teksystems_walkthrough-0.1.0-py3-none-any.whl
│   │                                     # Wheel package with payment processing
│   │                                     # Includes: models, payment, fraud, security, api
│   └── payment_gateway_demo.py           # Demo notebook
├── sql/
│   ├── MEDALLION_ARCHITECTURE.md         # Detailed architecture documentation
│   ├── silver_transformations.sql        # Silver layer SQL DDL
│   ├── gold_dimensions_facts_metrics.sql # Gold layer SQL DDL
│   └── medallion_pipeline.py             # Orchestration notebook
└── BUNDLE_SUMMARY.md                     # This file
```

## Key Features

### 1. **Data Quality & Governance**
- Clear layer separation (raw → silver → gold)
- Standardized naming conventions
- Audit trails (timestamps, metadata capture)
- 90-day data retention in silver layer

### 2. **Fraud Integration**
- Fraud signals from ML engine ingested in raw
- Risk scoring and categorization in silver
- Fraud impact metrics in gold (blocked volume, rates)
- Customer risk profiling based on fraud signals

### 3. **Performance Optimized**
- Denormalized gold fact table for fast queries
- Pre-computed aggregations in metric views
- Efficient joins via dimension tables
- Support for incremental processing

### 4. **Analytics Ready**
- Daily payment summaries (volume, success rates, risks)
- Fraud patterns by merchant and customer
- Customer risk classification (low/medium/high/very high)
- Time-based analysis via date dimension

## Deployment

### Prerequisites
```bash
# Ensure workspace has Unity Catalog enabled
# Verify databricks CLI is configured
databricks auth status
```

### Deploy to Development
```bash
cd bundle
databricks bundle validate --target dev
databricks bundle deploy --target dev
```

### Deploy to Staging/Production
```bash
databricks bundle deploy --target staging
# or
databricks bundle deploy --target prod
```

## Usage Examples

### Query Daily Metrics
```sql
SELECT 
  calendar_date,
  total_transactions,
  successful_transactions,
  fraud_blocked_transactions,
  success_rate_pct,
  avg_risk_score
FROM payments.gold.metric_daily_payment_summary
WHERE calendar_date >= CURRENT_DATE - INTERVAL 7 DAYS
ORDER BY calendar_date DESC;
```

### Analyze High-Risk Merchants
```sql
SELECT 
  merchant_name,
  total_transactions,
  fraud_block_rate_pct,
  avg_risk_score,
  fraud_blocked_volume
FROM payments.gold.metric_fraud_analytics
WHERE fraud_block_rate_pct > 2.0
ORDER BY fraud_blocked_volume DESC;
```

### Customer Risk Assessment
```sql
SELECT 
  customer_name,
  risk_classification,
  transaction_count,
  avg_risk_score,
  fraud_blocked_count,
  last_transaction_date
FROM payments.gold.metric_customer_risk_profile
WHERE risk_classification IN ('HIGH_RISK', 'VERY_HIGH_RISK')
ORDER BY max_risk_score DESC;
```

## Data Pipeline Flow

```
1. Raw Ingestion
   Payment Processor → payments_raw
   Fraud Engine → fraud_signals_raw

2. Silver Transformations
   payments_raw → payments_cleaned (standardization)
   fraud_signals_raw → fraud_signals_cleaned (normalization)
   
3. Data Enrichment
   payments_cleaned + fraud_signals_cleaned → payments_with_fraud
   payments_with_fraud → transactions_fact (deduplication)

4. Gold Analytics
   transactions_fact → fact_transactions (denormalized)
   fact_transactions + dim_* → metric_* views (aggregations)

5. Analytics Consumption
   BI Tools → metric views
   Dashboards → fact_transactions
   ML/Reporting → dimensions
```

## Table Details

### Fact Table: fact_transactions
**Grain**: One row per transaction
**Size**: Typically <500M rows for 2+ years of data
**Columns**: 30+ including amounts, status, fraud info, dates
**Optimization**: Partition by transaction_date for large volumes

### Dimension Tables
- **dim_date**: 730 rows (2 years)
- **dim_merchant**: 10K-100K rows (depends on unique merchants)
- **dim_customer**: 100K-10M rows (depends on customer base)
- **dim_payment_method**: ~5-10 rows (static/slow-changing)

### Metric Views
- **metric_daily_payment_summary**: Refresh daily (1 row/day)
- **metric_fraud_analytics**: Refresh hourly (1 row/merchant)
- **metric_customer_risk_profile**: Refresh hourly (1 row/customer)

## Performance Tuning

### Queries Run Slow?
1. Check table statistics: `ANALYZE TABLE payments.gold.fact_transactions COMPUTE STATISTICS`
2. Partition large tables by date
3. Use metric views instead of custom aggregations
4. Filter by date range when possible

### Data Refresh Too Slow?
1. Use incremental processing (process last 1-7 days)
2. Partition by date in silver layer
3. Cache frequently accessed dimension tables
4. Use OPTIMIZE ZORDER BY for hot tables

### Storage Growing Fast?
1. Archive data older than 2 years to external storage
2. Use Delta format compression
3. Set retention policies in Unity Catalog
4. Monitor with `DESCRIBE EXTENDED` and `INFORMATION_SCHEMA`

## Integration Points

### With Payment Processing
- `teksystems_walkthrough` Python package (wheel)
- Payment API produces events → raw.payments_raw
- Fraud engine produces signals → raw.fraud_signals_raw

### With BI Tools
- Query metric views directly (read-only)
- Use fact_transactions for drill-down analysis
- Connect dimensions for context

### With ML/AI
- Export fact_transactions for model training
- Use metric views for feature engineering
- Fraud engine predictions → silver.fraud_signals_cleaned

## Security & Compliance

- **Row-Level Security**: Use Unity Catalog object-level permissions
- **Column-Level Security**: Mask sensitive payment data if needed
- **Audit Logging**: Delta transaction logs automatically captured
- **Encryption**: DBFS (managed) or customer-managed keys (external volumes)
- **Data Governance**: Lineage tracking via Unity Catalog

## Monitoring & Alerts

### Recommended Metrics to Monitor
- Daily transaction volume growth
- Fraud signal processing latency
- Schema table sizes and growth rate
- Pipeline execution time
- Data quality (null checks, anomalies)

### Set Up Alerts For
- Unexpected fraud spike (>10% blocked)
- Pipeline execution failure
- Table size exceeding thresholds
- Data freshness SLA violations

## Maintenance Tasks

### Daily
- Monitor pipeline execution
- Check fraud signal ingestion lag
- Review high-risk transaction alerts

### Weekly
- Analyze fraud patterns
- Customer risk profile updates
- Performance trend analysis

### Monthly
- Archive old data
- Update statistics
- Review and optimize slow queries
- Capacity planning

## Future Enhancements

- **Real-Time Streaming**: Use Structured Streaming for sub-second latency
- **Predictive Fraud**: Integrate ML models into silver layer
- **Advanced Segmentation**: Customer cohort analysis
- **Payment Reconciliation**: GL volume auto-reconciliation
- **Cross-Border Analysis**: Multi-currency and region-based metrics
- **Anomaly Detection**: Automated alert rules based on metrics
- **Data Quality Framework**: Great Expectations or dbt testing

## Support & Documentation

- **Architecture Details**: See `sql/MEDALLION_ARCHITECTURE.md`
- **SQL Examples**: See `sql/*.sql` files
- **Pipeline Code**: See `sql/medallion_pipeline.py`
- **Python Package**: See `python/teksystems_walkthrough-0.1.0-py3-none-any.whl`

## Quick Links

- Databricks SQL: https://docs.databricks.com/sql/
- Unity Catalog: https://docs.databricks.com/data-governance/unity-catalog/
- Medallion Architecture: https://docs.databricks.com/lakehouse/architecture/
- Bundle Documentation: https://docs.databricks.com/dev-tools/bundles/

---

**Version**: 0.1.0  
**Last Updated**: 2026-07-04  
**Status**: Ready for Deployment ✓
