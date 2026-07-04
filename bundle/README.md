# Teksystems.Walkthrough Bundle

This directory contains the Databricks Declarative Automation Bundle (DAB) for the payment gateway project.

## Structure

- `python/` - Python wheel package and demo notebooks
  - `teksystems_walkthrough-0.1.0-py3-none-any.whl` - Compiled wheel package
  - `payment_gateway_demo.py` - Demo notebook using the payment gateway API

## Building the Wheel

The wheel package is built from the modular Python source in the project root. To rebuild:

```bash
cd ..
uv run python -m build --wheel
cp dist/teksystems_walkthrough-0.1.0-py3-none-any.whl bundle/python/
```

## Deploying the Bundle

Deploy to Databricks workspace:

```bash
databricks bundle deploy --target dev
```

## Bundle Resources

### Jobs
- `payment_gateway_job` - Main job for processing payments with fraud detection
  - Includes the wheel package as a library
  - Runs on a new cluster with Spark 14.3.x
  - Task: `process_payments` - Executes the payment processing logic

## Installation in Databricks

The wheel package will be automatically installed on the cluster via the `libraries` configuration in databricks.yml. It provides:

- `src.payment` - Payment processing module
- `src.fraud` - Fraud detection and signal streaming
- `src.security` - Tokenization and encryption services
- `src.api` - Public payment API
- `src.models` - Data models
- `src.transactions` - Transaction management
- `src.utils` - Utilities and helpers

## Configuration

Update `databricks.yml` with your workspace host before deploying.
