# Simple Invoice Creator

Generate PDF invoices using Python and ReportLab.

## Installation

```bash
uv sync
```

## Configuration

Copy the example config and fill in your details:

```bash
cp config.example.toml config.toml
```

Edit `config.toml` with your sender info, client info, and bank details.

## Usage

### Single line item

```bash
uv run create_invoice.py --hours 200 --date 2025-12-02
uv run create_invoice.py --hours 200 --rate 150 --description "Consulting Services"
```

### Multiple line items from CSV

```bash
uv run create_invoice.py --csv sample_line_items.csv --date 2025-12-02
```

CSV format:
```csv
hours,description,rate
100,Software Development,150
50,Code Review,150
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--hours` | - | Number of hours worked |
| `--rate` | from config | Hourly rate |
| `--description` | from config | Line item description |
| `--date` | today | Invoice date (YYYY-MM-DD) |
| `--csv` | - | CSV file with line items |
| `--output` | auto-generated | Output PDF filename |
| `--config` | config.toml | Path to config file |

## Output

Generates a PDF invoice with filename based on the `filename_prefix` in config (e.g., `Invoice_20251202.pdf`).
