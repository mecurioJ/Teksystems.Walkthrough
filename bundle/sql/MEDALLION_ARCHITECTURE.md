# Databricks Medallion Architecture Bundle: Payments

This bundle implements a complete medallion architecture (Bronze/Raw → Silver → Gold) for payment processing data, including fraud detection signals and analytics.

## Architecture Overview

### Layers

#### RAW Layer (Bronze)
- **Purpose**: Inbound streams from external systems
- **Schema**: `payments.raw`
- **Tables**:
  - `payments_raw` - Raw transactions from payment processor
  - `fraud_signals_raw` - Raw fraud signals from fraud engine
- **Volume**: 
  - `gl_reconciliation` - External volume for GL file reconciliation

#### SILVER Layer (Transformation)
- **Purpose**: Cleaned, standardized, and enriched data
- **Schema**: `payments.silver`
- **Tables**:
  - `payments_cleaned` - Standardized payment transactions
  - `fraud_signals_cleaned` - Normalized fraud signals
  - `payments_with_fraud` - Payment + fraud enriched data
  - `transactions_fact` - De-duplicated transaction records

#### GOLD Layer (Analytics)
- **Purpose**: Business-ready dimensions, facts, and metrics
- **Schema**: `payments.gold`

##### Dimensions
- `dim_date` - Calendar dimension (730 days history)
- `dim_merchant` - Merchant master data
- `dim_customer` - Customer profiles with risk metrics
- `dim_payment_method` - Payment method lookup

##### Facts
- `fact_transactions` - Denormalized transaction facts for performance

##### Metric Views
- `metric_daily_payment_summary` - Daily KPIs and aggregations
- `metric_fraud_analytics` - Fraud metrics by merchant
- `metric_customer_risk_profile` - Customer risk classification

## File Structure

```
bundle/
├── databricks_medallion.yml      # Main bundle configuration
├── sql/
│   ├── silver_transformations.sql    # Silver layer transformations
│   └── gold_dimensions_facts_metrics.sql # Gold layer schemas
├── README.md                     # This file
└── python/
    └── teksystems_walkthrough-0.1.0-py3-none-any.whl
```

## Key Features

### 1. Medallion Architecture
- **Separation of Concerns**: Each layer has a specific purpose
- **Data Quality**: Progressive cleaning and enrichment
- **Performance**: Denormalized gold layer for fast queries
- **Scalability**: Supports growing data volumes

### 2. Fraud Integration
- Raw fraud signals from ML engine
- Enrichment with payment data
- Risk scoring and categorization
- Fraud impact analysis (blocked volume, rates)

### 3. Analytics Metrics
- Daily payment summaries (volume, count, success rates)
- Fraud metrics by merchant and customer
- Customer risk profiling
- Trend analysis

### 4. Data Governance
- Clear naming conventions
- Timestamp tracking (processed_at, loaded_at)
- Metadata capture (_metadata columns)
- Audit trails

## Deployment

### Prerequisites
- Databricks workspace with Unity Catalog enabled
- Cluster with Spark 14.3.x or later
- Admin permissions to create catalogs

### Deploy to Dev Environment

```bash
databricks bundle deploy --target dev
```

### Deploy to Staging/Prod

```bash
databricks bundle deploy --target staging
# or
databricks bundle deploy --target prod
```

## Usage

### Query Daily Payment Summary
```sql
SELECT * FROM payments.gold.metric_daily_payment_summary
WHERE calendar_date >= CURRENT_DATE - INTERVAL 7 DAYS
ORDER BY calendar_date DESC;
```

### Analyze Fraud Patterns
```sql
SELECT * FROM payments.gold.metric_fraud_analytics
WHERE fraud_block_rate_pct > 1.0
ORDER BY fraud_block_rate_pct DESC;
```

### Customer Risk Assessment
```sql
SELECT * FROM payments.gold.metric_customer_risk_profile
WHERE risk_classification IN ('HIGH_RISK', 'VERY_HIGH_RISK')
ORDER BY transaction_count DESC;
```

## Data Pipeline

```
Raw Payment Data ──→ payments_cleaned ──→ payments_with_fraud ──→ fact_transactions ──→ Gold Metrics
    (raw)               (silver)             (silver)              (gold)              (gold)
         ↘                                     ↑
          ╚──→ fraud_signals_cleaned ────────╝
```

## Table Schemas

### dim_date
- Comprehensive date/calendar table
- 730 days of historical data
- Useful for time-based joins and aggregations

### dim_merchant & dim_customer
- Aggregate statistics (transaction counts, risk scores)
- Last updated timestamp
- Enable deduplication and SCD Type 1 patterns

### fact_transactions
- Denormalized design for query performance
- Includes pre-calculated amounts (captured, refunded, failed, fraud_blocked)
- Supports drilling into any dimension

### Metric Views
- Aggregated KPIs for business reporting
- Regular refresh recommended (hourly or daily)
- Designed for BI tool consumption

## Performance Considerations

1. **Partitioning**: Consider partitioning tables by date for large volumes
2. **Caching**: Metric views can be materialized for performance
3. **Refresh Schedule**: Set appropriate refresh intervals based on data freshness requirements
4. **Clustering**: Use transaction_date or merchant_id for better scan performance

## Security

- Role-Based Access Control (RBAC) via Unity Catalog
- Column-level security for sensitive fields
- Audit logging for compliance
- GL volume protected for reconciliation data

## Maintenance

### Adding New Dimensions
1. Create table in gold schema with `dim_` prefix
2. Join from fact_transactions in metric views
3. Update documentation

### Backfilling Data
Use the 90-day window defined in silver layer transformations.
Adjust `INTERVAL 90 DAYS` as needed for your retention policy.

### Monitoring
- Monitor table sizes and growth rates
- Track transformation execution times
- Set up alerts for data quality issues
- Monitor fraud signal latency

## Integration with Payment Gateway

The bundle integrates with:
- `teksystems_walkthrough` Python package (payment processing)
- Fraud detection engine (SimpleFraudEngine or MLFraudEngine)
- Kafka streams (fraud signals)
- Databricks SQL endpoints

## Future Enhancements

- Real-time streaming with Structured Streaming
- Predictive fraud models integrated into silver layer
- Advanced customer segmentation
- Automated alerts based on anomalies
- Cross-border payment analysis
- Payment reconciliation workflows
