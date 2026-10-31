#!/usr/bin/env python3
"""Headless LeakageLens: run the Exasol backend without the web UI.

This is a thin wrapper over src/exasol.py, the same code the Streamlit app uses,
so the CLI and the app always run identical schema, loading and detection logic.

Usage (from the project root):
  python backend/leakagelens_cli.py --load data/demo_csv     # first run: create, load, analyse
  python backend/leakagelens_cli.py                          # later runs: analyse what is loaded
  python backend/leakagelens_cli.py --tolerance 5            # allow 5% over a purchase order
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

try:
    from dotenv import load_dotenv  # noqa: E402
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.core import unique_exposure  # noqa: E402
from src import exasol  # noqa: E402


def read_csv_folder(folder: Path) -> dict[str, pd.DataFrame]:
    """Read suppliers/purchase_orders/invoices/payments/credit_notes CSVs (any header case)."""
    data = {}
    for entity in exasol.SOURCE_TABLES:
        path = folder / f"{entity}.csv"
        if not path.exists():
            sys.exit(f"Missing {path}")
        data[entity] = pd.read_csv(path, dtype=str, keep_default_na=False)
    return data


def report(findings: list[dict], top: int = 15) -> None:
    if not findings:
        print("No findings.")
        return
    print(f"\nTotal findings: {len(findings):,}")
    by_category: dict[str, list[Decimal]] = defaultdict(list)
    for item in findings:
        by_category[item["category"]].append(item["gross_discrepancy_amount"])
    print("\nPer category (count, gross amount flagged):")
    for category, amounts in sorted(by_category.items(), key=lambda kv: -sum(kv[1])):
        print(f"  {category:<28} {len(amounts):>5}  {sum(amounts):>16,.2f}")
    print("\nBiggest single findings:")
    for item in sorted(findings, key=lambda f: f["gross_discrepancy_amount"], reverse=True)[:top]:
        invoices = ",".join(item["sources"]["invoices"]) or "-"
        print(f"  {item['category']:<28} {invoices:<24} {item['currency']} {item['gross_discrepancy_amount']:>14,.2f}")
    print("\nUnique recoverable exposure (overlapping findings on one invoice counted once):")
    for currency, amount in unique_exposure(findings).items():
        print(f"  {currency} {amount:,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LeakageLens detections inside Exasol.")
    parser.add_argument("--load", type=Path, help="folder with the five source CSV files, e.g. data/demo_csv")
    parser.add_argument("--tolerance", type=float, default=2.0, help="allowed overbilling in percent of the PO amount (default 2)")
    parser.add_argument("--fuzzy", type=int, default=90, help="fuzzy invoice-reference threshold, 0-100 (default 90)")
    args = parser.parse_args()
    try:
        print("Creating schema and tables...")
        exasol.initialize_schema()
        if args.load:
            print(f"Loading CSV files from {args.load} ...")
            for entity, count in exasol.replace_source_data(read_csv_folder(args.load)).items():
                print(f"  {entity:<16} {count:>7} rows")
        print("Running detections inside Exasol...")
        findings, meta = exasol.run_analysis(fuzzy_threshold=args.fuzzy, po_tolerance_pct=args.tolerance)
        for name, seconds in meta["query_times_seconds"].items():
            print(f"  {name:<26} {seconds:>7.3f}s")
        report(findings)
    except (exasol.ExasolConfigurationError, RuntimeError, ValueError) as exc:
        sys.exit(f"Error: {exc}")


if __name__ == "__main__":
    main()
