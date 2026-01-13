# Agent Instructions

## Project Overview

Python CLI tool that generates PDF invoices using ReportLab.

## Commands

- **Install dependencies**: `uv sync`
- **Run**: `python create_invoice.py --hours 100 --date 2025-01-01`
- **Type check**: `uv run mypy create_invoice.py` (if mypy is added)

## Structure

- `create_invoice.py` - Main script with invoice generation logic
- `config.toml` - Configuration file with sender/client/bank info (gitignored)
- `config.example.toml` - Example config template
- `sample_line_items.csv` - Example CSV input file
- `pyproject.toml` - Project configuration and dependencies

## Dependencies

- Python 3.10+
- reportlab >= 4.0.0

## Code Conventions

- Use type hints for function parameters and return values
- Constants for sender/client info are at module level
- Use Decimal for currency calculations to avoid floating point errors
