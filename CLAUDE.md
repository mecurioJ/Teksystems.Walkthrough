# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is an early-stage project for implementing payment gateway patterns.
- **Core Logic**: Located in `main.py`.
- **Requirements & Context**: Defined in `Payment_Gateway_Case_Study.docx`. Reference this for all feature implementation.
- **Infrastructure**: Managed via Databricks Declarative Bundles (DABs) in `databricks.yml`.

## Development Commands
### Basic Setup & Run
- `uv sync` - Install/update dependencies
- `python main.py` - Run the application locally
- `uv add <package>` - Add a new dependency

### Databricks Workflow
- `databricks bundle validate` - **Always run** before committing changes to `databricks.yml` or related infrastructure.
- `databricks bundle deploy` - Deploy to the configured `dev` environment.

### Testing & Quality
- `python -m pytest` - Run the test suite.
- `python -m pytest -k payment` - Run tests matching the "payment" pattern.
- `uv` - Used for environment management and linting/formatting (via `pyproject.toml`).

## Architecture & Standards
- **Code Style**: Follow PEP 8. Use type hints for all new functions.
- **Imports**: Organize as `stdlib` -> `third-party` -> `local`.
- **Databricks Integration**:
  - Use `.py` extension with `# COMMAND ----------` markers for notebooks.
  - Target `dev` by default in `databrirm.yml`.
- **Payment Logic**:
  - Prioritize security patterns (encryption, tokenization) from the case study.
  - Implement explicit error handling for all payment-related operations.
  - Validate all transaction inputs (e.g., check for zero, negative, or excessive amounts).

## Git & Commits
- **Format**: `<type>: <subject>` (e.g., `feat: add payment token validation`)
- **Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- **Requirement**: Run `python main.py` or the test suite before every commit.

## Internal Tools & Context
- **Memory**: Use the `.claude/projects/.../memory/` directory to track project decisions.
- **Skills**:
  - `/simplify` - Use for refactoring and code optimization.
  - `databricks` - Use for managing Databricks resources.
- **Search**: Reference `Payment_Gateway_Case_Study.docx` for logic specifics and `AGENTS.md` for general project rules.
