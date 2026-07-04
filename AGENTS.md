# AI Agent Instructions for Teksystems.Walkthrough

## Project Overview

**Teksystems.Walkthrough** is a learning project exploring payment gateway implementation patterns and best practices. It includes case study analysis from `Payment_Gateway_Case_Study.docx` and practical implementation using Databricks.

## Quick Start for Agents

### Python & Dependencies
- **Python version**: 3.14 (pinned in `.python-version`)
- **Package manager**: `uv` (modern Python package manager)
- **Dependency file**: `pyproject.toml` - update this when adding packages
- **Virtual environment**: Use `.venv` or let `uv` manage it automatically

### Development Commands
```bash
uv sync              # Install dependencies
python main.py       # Run the main script
```

## Project Structure

- `main.py` - Entry point for the application
- `databricks.yml` - Databricks bundle configuration (dev mode enabled)
- `pyproject.toml` - Project metadata and dependencies
- `Payment_Gateway_Case_Study.docx` - Case study documentation
- `.python-version` - Python version specification (3.14)

## Databricks Integration

This project uses **Databricks Declarative Bundles** for infrastructure as code:
- Bundle name: `Teksystems.Walkthrough`
- Default target: `dev` (development mode)
- Workspace: Configured in `databricks.yml` targets
- When implementing features: Consider how code could be deployed/executed on Databricks

**Relevant commands:**
```bash
databricks bundle validate  # Validate bundle config
databricks bundle deploy    # Deploy to workspace
```

## Code Conventions

- **Style**: Follow PEP 8 (use `black` or similar if added)
- **Type hints**: Encouraged for new functions
- **Imports**: Organize as stdlib → third-party → local
- **Testing**: Create tests alongside feature implementation
- **Documentation**: Docstrings for public functions; comments only for non-obvious logic

## When Working on Payment Gateway Features

1. Reference `Payment_Gateway_Case_Study.docx` for context and requirements
2. Consider security implications (PCI-DSS patterns, encryption, tokenization)
3. Design for scalability on Databricks (distributed processing where applicable)
4. Document assumptions about payment flows and failure scenarios
5. Test with realistic transaction patterns and edge cases

## Project Maturity

This is an early-stage project. Focus on:
- Clear, maintainable code over premature optimization
- Incremental feature development
- Documentation of key decisions
- Keeping dependencies minimal until needed

## Common Workflows

### Adding a New Feature
1. Update `pyproject.toml` if new dependencies needed
2. Implement in `main.py` or create new module
3. Run locally: `python main.py`
4. Verify Databricks bundle config still validates

### Working with Dependencies
```bash
uv add <package>          # Add and install
uv sync                   # Install from lock file
uv pip list               # List installed packages
```

## Questions?

If you need context on payment gateway architecture, the case study document and this `AGENTS.md` are your starting points. For Databricks-specific questions, refer to `databricks.yml` configuration.
