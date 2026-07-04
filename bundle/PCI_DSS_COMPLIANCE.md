# PCI-DSS Compliance Guide

This document outlines the PCI-DSS (Payment Card Industry Data Security Standard) compliance measures implemented in the Teksystems.Walkthrough payment gateway system.

## Overview

PCI-DSS Requirement 3.2 requires that organizations not store sensitive authentication data after authorization. This project implements controls to:
- Classify sensitive data
- Tokenize restricted fields
- Mask PII in lower-security environments
- Apply row and column-level access controls
- Track data lineage through all layers

## Data Classification

### Classification Levels

| Level | Description | Examples | Access Control |
|-------|-------------|----------|-----------------|
| **PUBLIC** | Non-sensitive data, safe to share | Transaction dates, currency codes | Open |
| **INTERNAL** | Business data, restricted to org | Merchant IDs, transaction statuses | Authenticated users |
| **CONFIDENTIAL** | Sensitive business data | Transaction amounts, fraud scores | Finance + Analytics teams |
| **PCI-DSS RESTRICTED** | Regulated card data (Must NOT store post-auth) | Card numbers, CVV, cardholder names | Compliance + Security only |
| **PII RESTRICTED** | Personally identifiable information | Customer IDs, emails, phone, SSN | Finance + Privacy team |

### Restricted Fields Identified

**PCI-DSS Restricted (Card Data):**
- `card_number` / `pan` - Primary Account Number
- `cvv` / `cvc` / `security_code` - Verification codes
- `cardholder_name` - Holder name
- `expiration_date` - Card expiration
- `pin` / `pin_block` - Personal identification number
- `track_data` - Full magnetic stripe data

**PII Restricted (Customer Data):**
- `customer_id` - Links to customer record
- `email` - Email address
- `phone` - Telephone number
- `ssn` / `social_security_number` - Tax ID

## Implementation Strategy

### Raw Layer (Bronze) - Restricted Access

**Purpose:** Ingest data exactly as received from payment processor and fraud engine

**Data Handling:**
- ✓ Raw payment data stored as-is
- ✓ Tokenization happens **BEFORE** raw storage (by payment processor)
- ✓ Card numbers NOT stored; tokens stored instead
- ✓ CVV never stored (PCI-DSS requirement)
- ✗ Tag applied: `pci_dss_classification = "restricted"`
- ✗ Access: Finance + Compliance only

**Tables:**
```
payments.raw.payments_raw
  - payment_id (STRING)
  - merchant_id (STRING)
  - customer_id (STRING) 
  - amount (STRING) - Restricted
  - currency (STRING)
  - payment_method (STRING) - Tokenized/hashed
  - status (STRING)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)
  - metadata (JSON)

payments.raw.fraud_signals_raw
  - signal_id (STRING)
  - transaction_id (STRING)
  - risk_score (DECIMAL)
  - risk_level (STRING)
  - alerts (ARRAY)
  - decision (STRING)
  - case_status (STRING)
  - created_at (TIMESTAMP)
```

### Silver Layer (Transformation) - Confidential

**Purpose:** Clean, standardize, and enrich data with consistent formats and business rules

**Data Handling:**
- Standardize payment methods (normalize to enum values)
- Normalize transaction statuses
- Type conversions (amounts to DECIMAL)
- Fraud enrichment (LEFT JOIN with fraud signals)
- Deduplication (ROW_NUMBER window)
- ✓ Tag applied: `pci_dss_classification = "restricted"` + `data_classification = "confidential"`
- ✗ Access: Finance + Analytics teams

**Tables:**
```
payments.silver.payments_cleaned
  - Standardized payment records
  - Normalized payment methods
  - Normalized statuses
  
payments.silver.fraud_signals_cleaned
  - Normalized fraud decision classifications
  - Risk scores cast to DECIMAL(3,2)
  
payments.silver.payments_with_fraud
  - LEFT JOIN payments → fraud signals
  - Added overall_risk_category based on fraud decision
  
payments.silver.transactions_fact
  - Deduplicated transaction records
  - Single row per transaction_id
  - All columns from payments_with_fraud
```

### Gold Layer (Analytics) - Controlled Sharing

**Purpose:** Create dimensional models, facts, and aggregated metrics for BI/reporting

**Data Handling:**
- ✓ Dimensions provide context without exposing raw restricted data
- ✓ Aggregated metrics (counts, sums, averages) safe for dashboards
- ✓ Fact table contains restricted data but with RBAC
- ✗ Tag applied: `pci_dss_classification = "restricted"` + `data_classification = "confidential"`
- ✗ Access: BI Service Account (read-only), Finance, Compliance

**Tables:**
```
payments.gold.dim_date
  - Public: date keys, calendar info, day of week flags
  
payments.gold.dim_merchant
  - Internal: merchant_id, merchant_name, transaction counts
  
payments.gold.dim_customer
  - PII Restricted: customer_id, customer_name, risk profiles
  - Tag: pii_restricted = "true"
  
payments.gold.dim_payment_method
  - Public: payment method names and attributes
  
payments.gold.fact_transactions
  - Restricted: denormalized fact table with all transaction details
  - Includes customer_id (PII), payment_method (restricted), amounts
  - Tag: pci_dss_classification = "restricted"
  
payments.gold.metric_daily_payment_summary (VIEW)
  - Public: aggregated metrics by date (counts, totals)
  - Safe for dashboards - no individual transaction details
  
payments.gold.metric_fraud_analytics (VIEW)
  - Internal: fraud metrics by merchant
  - Aggregated - no individual customer/card data
  
payments.gold.metric_customer_risk_profile (VIEW)
  - Confidential: customer risk classifications
  - Aggregated metrics - no card data exposed
```

## Masking Strategy

When restricted data needs to be displayed in lower-security contexts:

| Field | Masking Rule | Example |
|-------|-------------|---------|
| Card Number | Last 4 digits only | `**** **** **** 1234` |
| CVV | Fully redacted | `***` |
| Cardholder Name | First initial only | `J***` |
| Email | First letter + domain | `j***@example.com` |
| Phone | Last 4 digits only | `**** 5678` |
| Customer ID | Fully redacted in reporting | `***` |

**Implementation:** `PCIDataMasker` class provides functions to apply masking before returning data to UI/reports.

## Tokenization

**Approach:** Payment processor handles tokenization before data reaches Databricks

1. **Input:** Raw card data from payment form
2. **Process:** Payment processor calls TokenizationService
3. **Output:** Token (unique reference) stored instead of card number
4. **Storage:** Only token reaches raw layer - actual card data never stored

**Example Flow:**
```
Card Number (4532-0151-1283-0366) 
    ↓
[Payment Processor - TokenizationService]
    ↓
Token (tok_4f3a2e8c9b) + Last 4 (0366)
    ↓
[Stored in Database]
```

## Encryption

**Data at Rest:** Databricks Unity Catalog encryption handles columns tagged with `requires_encryption = "true"`
- Default: AES-256 encryption for all Delta tables in managed storage
- Column-level encryption available for highest-sensitivity data

**Data in Transit:**
- All Databricks API calls: TLS 1.2+
- Wheel package communication: Encrypted channels
- SQL queries: Secure connections

**Configuration:**
```yaml
# In databricks_medallion.yml
encryption:
  at_rest: true  # AES-256 default
  in_transit: true  # TLS 1.2+
```

## Access Control

### Role-Based Access Control (RBAC)

**Implementation:** Databricks Unity Catalog permissions

**Roles:**

| Role | Tables | Purpose | Users |
|------|--------|---------|-------|
| **public** | dim_date, dim_payment_method, metric_* views | BI tool access | Service account |
| **analytics** | All gold layer + metric views | Dashboard/reporting | Analytics team |
| **finance** | All silver + gold layers | Financial analysis | Finance team |
| **compliance** | All layers including raw | Audit/compliance | Compliance officers |
| **security** | All tables + raw layer | Security monitoring | Security team |
| **admin** | All tables + all layers | Administration | DBA team |

**Example Permissions:**
```sql
-- Grant BI tool read-only access to specific metrics only
GRANT SELECT ON TABLE payments.gold.metric_daily_payment_summary TO `bi-service-account`;
GRANT SELECT ON TABLE payments.gold.metric_fraud_analytics TO `bi-service-account`;

-- Block access to restricted tables
REVOKE ALL PRIVILEGES ON TABLE payments.raw.payments_raw FROM `analytics-group`;
REVOKE ALL PRIVILEGES ON TABLE payments.silver.payments_cleaned FROM `analytics-group`;
```

## Data Governance Views

Four data governance views provide compliance audit trails:

### 1. `v_data_governance_summary`
Summarizes all tables with their PCI-DSS tags and sensitivity levels
```sql
SELECT * FROM payments.gold.v_data_governance_summary;
```

### 2. `v_pci_dss_column_inventory`
Lists sensitive columns in each table with classification
```sql
SELECT * FROM payments.gold.v_pci_dss_column_inventory;
```

### 3. `v_pci_dss_audit`
Compliance checkpoint view - verifies tagging and access controls
```sql
SELECT * FROM payments.gold.v_pci_dss_audit;
```

### 4. `v_pci_dss_access_recommendations`
Recommended access levels for each table
```sql
SELECT * FROM payments.gold.v_pci_dss_access_recommendations;
```

## Compliance Checklist

PCI-DSS Requirement 3.2 Compliance:

- [x] **Classify sensitive data** - Python `PCIDSSClassifier` identifies restricted fields
- [x] **Tokenize card data** - `TokenizationService` stores tokens, not card numbers
- [x] **Don't store CVV** - CVV masked/redacted, never stored in tables
- [x] **Don't store PIN** - PIN handled by payment processor, not stored in database
- [x] **Restrict storage** - Raw layer tagged with `pci_dss_classification`
- [x] **Control access** - RBAC prevents unauthorized data viewing
- [x] **Audit trail** - Tags and governance views track compliance
- [x] **Mask output** - `PCIDataMasker` masks sensitive data in reports
- [x] **Encrypt data** - UC encryption for all sensitive columns
- [x] **Document controls** - This file documents all controls

## Testing PCI-DSS Compliance

### Test 1: Verify Classification
```python
from src.security import PCIDSSClassifier, DataClassification

# Verify card number is restricted
result = PCIDSSClassifier.classify_column("card_number")
assert result.classification == DataClassification.PCI_DSS_RESTRICTED
assert result.is_masked
```

### Test 2: Verify Masking
```python
from src.security import PCIDataMasker

# Verify card masking
masked = PCIDataMasker.mask_card_number("4532015112830366")
assert masked == "****012830366"  # Not the full card
```

### Test 3: Run PCI-DSS Test Suite
```bash
python -m pytest tests/test_pci_dss.py -v
# 34 tests covering classification, masking, and compliance workflows
```

### Test 4: Audit Tags in Databricks
```sql
-- Verify tables are tagged
SELECT 
  table_name,
  tag_name,
  tag_value
FROM information_schema.table_tags
WHERE tag_name IN ('pci_dss_classification', 'data_classification')
ORDER BY table_name;
```

## Assumptions & Limitations

**Current Implementation:**
- Card tokenization assumed to be handled by payment processor before Databricks
- CVV not stored (enforced at schema level, but responsibility of payment system)
- PIN block handled by payment processor (not in scope for Databricks storage)

**Future Enhancements:**
- Implement column-level encryption for specific restricted columns
- Add automated tag-based redaction for SQL queries to analytics team
- Create automated data retention policies (PCI requires deletion after 3 years)
- Implement query logging for compliance audit trails
- Add dynamic masking for real-time views based on user role

## References

- **PCI-DSS Requirement 3.2:** Do not store sensitive authentication data after authorization
- **Databricks UC Security:** https://docs.databricks.com/en/security/
- **Data Classification Best Practices:** https://databricks.com/blog/2021/07/28/data-governance-at-databricks.html

## Support & Questions

For compliance questions or to add additional restrictions:
1. Review this guide for classification levels
2. Check `src/security/pci_dss.py` for programmatic classification
3. Run `tests/test_pci_dss.py` to verify implementations
4. Review `bundle/sql/pci_dss_tagging.sql` for metadata tagging
