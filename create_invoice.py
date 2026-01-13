#!/usr/bin/env python3
"""
Invoice Generator Script
Generates PDF invoices matching the Byron invoice format.

Usage:
    python create_invoice.py --hours 200 --date 2025-12-02
    python create_invoice.py --csv line_items.csv --date 2025-12-02
    python create_invoice.py --hours 200 --rate 150 --description "Consulting Services"
"""

import argparse
import csv
import tomllib
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    if config_path is None:
        config_path = Path(__file__).parent / "config.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate PDF invoices")
    parser.add_argument("--hours", type=float, help="Number of hours worked")
    parser.add_argument("--rate", type=float, help="Hourly rate (default from config)")
    parser.add_argument("--description", type=str, help="Description for the line item")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"),
                        help="Invoice date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--csv", type=str, help="CSV file with columns: hours, description, rate")
    parser.add_argument("--output", type=str, help="Output PDF filename (auto-generated if not specified)")
    parser.add_argument("--config", type=str, help="Path to config file (default: config.toml)")
    return parser.parse_args()


def load_line_items_from_csv(csv_path: str) -> list[dict]:
    items = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                "hours": float(row["hours"]),
                "description": row["description"],
                "rate": float(row["rate"]),
            })
    return items


def format_currency(amount: float) -> str:
    return f"${amount:,.2f}"


def create_invoice(date_str: str, line_items: list[dict], output_path: str, config: dict[str, Any]):
    sender = config["sender"]
    client = config["client"]
    bank = config["bank"]
    invoice_cfg = config["invoice"]

    invoice_date = datetime.strptime(date_str, "%Y-%m-%d")
    invoice_number = f"{invoice_cfg['number_prefix']}{invoice_date.strftime('%Y-%m-%d')}"
    formatted_date = invoice_date.strftime("%B %d, %Y").replace(" 0", " ")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = {
        "normal": ParagraphStyle("Normal", fontName="Helvetica", fontSize=10),
        "sender": ParagraphStyle("Sender", fontName="Helvetica", fontSize=10, leading=14),
        "invoice_title": ParagraphStyle("InvoiceTitle", fontName="Helvetica-Bold", fontSize=28,
                                         textColor=colors.grey, alignment=TA_RIGHT),
        "meta": ParagraphStyle("Meta", fontName="Helvetica", fontSize=10, alignment=TA_RIGHT),
        "section_header": ParagraphStyle("SectionHeader", fontName="Helvetica-Bold", fontSize=10),
        "client": ParagraphStyle("Client", fontName="Helvetica", fontSize=10, leading=14),
        "center": ParagraphStyle("Center", fontName="Helvetica", fontSize=10, alignment=TA_CENTER),
        "center_bold": ParagraphStyle("CenterBold", fontName="Helvetica-Bold", fontSize=10,
                                       alignment=TA_CENTER),
        "note": ParagraphStyle("Note", fontName="Helvetica-Oblique", fontSize=9,
                               textColor=colors.grey, alignment=TA_CENTER),
        "thanks": ParagraphStyle("Thanks", fontName="Helvetica-BoldOblique", fontSize=10,
                                  alignment=TA_CENTER),
        "footer": ParagraphStyle("Footer", fontName="Helvetica", fontSize=8, alignment=TA_CENTER),
    }

    elements = []

    header_data = [
        [
            Paragraph(
                f"{sender['name']}<br/>{sender['address_1']}<br/>{sender['address_2']}<br/>"
                f"{sender['email']}<br/>{sender['phone']}",
                styles["sender"]
            ),
            Paragraph("INVOICE", styles["invoice_title"]),
        ],
        [
            "",
            Paragraph(f"<b>Date:</b> {formatted_date}<br/><b>Invoice #:</b> {invoice_number}",
                      styles["meta"]),
        ],
    ]
    header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("Bill To:", styles["section_header"]))
    elements.append(Spacer(1, 2))

    from reportlab.platypus import HRFlowable
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        f"{client['name']}<br/>{client['company']}<br/>{client['address_1']}<br/>{client['address_2']}",
        styles["client"]
    ))
    elements.append(Spacer(1, 0.25 * inch))

    table_data = [["Hours", "Description", "Rate", "Amount"]]

    total = Decimal("0")
    for item in line_items:
        hours = item["hours"]
        desc = item["description"]
        rate = item["rate"]
        amount = Decimal(str(hours)) * Decimal(str(rate))
        total += amount
        table_data.append([
            f"{hours:.1f}" if hours else "",
            desc,
            f"${rate:.2f}",
            format_currency(float(amount)),
        ])

    empty_rows_needed = max(0, 8 - len(table_data))
    for _ in range(empty_rows_needed):
        table_data.append(["", "", "", ""])

    table_data.append(["", "", "Total", format_currency(float(total))])

    col_widths = [0.8 * inch, 4.0 * inch, 1.0 * inch, 1.2 * inch]
    items_table = Table(table_data, colWidths=col_widths)

    table_style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (2, -1), "LEFT"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.black),
        ("BOX", (2, -1), (3, -1), 0.5, colors.black),
        ("LINEABOVE", (2, -1), (3, -1), 0.5, colors.black),
        ("FONTNAME", (2, -1), (3, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    items_table.setStyle(TableStyle(table_style))
    elements.append(items_table)
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        f"Account Number: {bank['account']}<br/>"
        f"ACH Routing Number: {bank['ach_routing']}<br/>"
        f"Wire Routing Number: {bank['wire_routing']}",
        styles["center"]
    ))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph(f"Make all checks payable to {sender['name']}", styles["note"]))
    elements.append(Spacer(1, 0.15 * inch))

    elements.append(Paragraph("Thank you for your business!", styles["thanks"]))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        f"{sender['name']} {sender['address_1']}, {sender['address_2']} Phone {sender['phone']} {sender['email']}",
        styles["footer"]
    ))

    doc.build(elements)
    print(f"Invoice created: {output_path}")


def main():
    args = parse_args()

    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)
    invoice_cfg = config["invoice"]

    if args.csv:
        line_items = load_line_items_from_csv(args.csv)
    elif args.hours:
        line_items = [{
            "hours": args.hours,
            "description": args.description or invoice_cfg["default_description"],
            "rate": args.rate or invoice_cfg["default_rate"],
        }]
    else:
        print("Error: Must provide either --hours or --csv")
        return

    if args.output:
        output_path = args.output
    else:
        date_formatted = args.date.replace("-", "")
        output_path = f"{invoice_cfg['filename_prefix']}_{date_formatted}.pdf"

    create_invoice(args.date, line_items, output_path, config)


if __name__ == "__main__":
    main()
