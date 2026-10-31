#!/usr/bin/env python3
"""Regenerate backend/sql/03_detections.sql from database/detections/*.sql."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["duplicate_invoices", "duplicate_payments", "overbilling", "missed_credits",
         "payment_mismatches", "unmatched_payments", "fuzzy_invoice_candidates"]
out = [
    "-- Step 3 - the detection queries. Each statement joins the loaded tables inside Exasol and returns one row per finding.",
    "-- GENERATED from database/detections/*.sql (the same queries the app runs). Do not edit by hand; re-run backend/build_sql_script.py.",
    "-- Overbilling tolerance is 0.02 (2%). Edit the number to change it. Fuzzy candidates are only narrowed by SQL here;",
    "-- the app and CLI score them with RapidFuzz.",
    "",
]
for name in ORDER:
    query = (ROOT / "database" / "detections" / f"{name}.sql").read_text(encoding="utf-8").replace("\r", "").strip().rstrip(";")
    query = re.sub(r"\{amount_tolerance!f\}", "0.02", query)
    out += [f"-- ===== {name.replace('_', ' ').upper()} =====", query + ";", ""]
(ROOT / "backend" / "sql" / "03_detections.sql").write_text("\n".join(out), encoding="utf-8")
print("wrote backend/sql/03_detections.sql")
