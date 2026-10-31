from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from src.core import analyze, csv_safe, generate_demo, money, unique_exposure, validate_import


def source_data():
    return {
        "suppliers": pd.DataFrame([{"supplier_id": "S1", "supplier_name": "Supplier", "currency": "INR"}]),
        "purchase_orders": pd.DataFrame([{
            "po_id": "PO1", "supplier_id": "S1", "approved_amount": Decimal("100.00"),
            "currency": "INR", "status": "approved",
        }]),
        "invoices": pd.DataFrame([{
            "invoice_id": "I1", "supplier_id": "S1", "supplier_name": "Supplier",
            "invoice_number": "INV-1", "invoice_date": date(2026, 1, 1), "due_date": date(2026, 2, 1),
            "po_id": "PO1", "amount": Decimal("100.00"), "currency": "INR",
        }]),
        "payments": pd.DataFrame([
            {"payment_id": "P1", "supplier_id": "S1", "invoice_id": "I1", "payment_date": date(2026, 1, 2),
             "amount": Decimal("100.00"), "currency": "INR", "status": "settled", "payment_reference": "R1", "reversal_of": ""},
            {"payment_id": "P2", "supplier_id": "S1", "invoice_id": "I1", "payment_date": date(2026, 1, 3),
             "amount": Decimal("100.00"), "currency": "INR", "status": "settled", "payment_reference": "R2", "reversal_of": ""},
        ]),
        "credit_notes": pd.DataFrame(),
    }


def test_money_uses_decimal_rounding():
    assert money("10.005") == Decimal("10.01")
    with pytest.raises(ValueError):
        money("not-money")


def test_duplicate_payment_and_overpayment_are_deduplicated():
    findings = analyze(source_data())
    assert {row["category"] for row in findings} >= {"Possible duplicate payment", "Overpayment"}
    assert unique_exposure(findings)["INR"] == Decimal("100.00")


def test_reversed_payment_does_not_increase_exposure():
    data = source_data()
    data["payments"].loc[1, "reversal_of"] = "P2"
    findings = analyze(data)
    assert not any(row["category"] == "Overpayment" for row in findings)


def test_payment_reversed_by_later_record_is_excluded():
    data = source_data()
    data["payments"] = data["payments"].iloc[:1].copy()
    data["payments"] = pd.concat([
        data["payments"],
        pd.DataFrame([{
            "payment_id": "P-REV", "supplier_id": "S1", "invoice_id": "I1",
            "payment_date": date(2026, 1, 4), "amount": Decimal("100.00"),
            "currency": "INR", "status": "reversed", "payment_reference": "R1",
            "reversal_of": "P1",
        }]),
    ], ignore_index=True)
    findings = analyze(data)
    assert not any(row["category"] == "Overpayment" for row in findings)


def test_duplicate_invoice_references_are_linked():
    data = source_data()
    duplicate = data["invoices"].iloc[0].to_dict()
    duplicate.update({"invoice_id": "I2", "invoice_number": "inv 1"})
    data["invoices"] = pd.concat([data["invoices"], pd.DataFrame([duplicate])], ignore_index=True)
    findings = analyze(data)
    duplicate_finding = next(row for row in findings if row["category"] == "Duplicate invoice")
    assert duplicate_finding["sources"]["invoices"] == ["I1", "I2"]


def test_linked_invoice_findings_are_one_exposure_case():
    findings = [
        {"currency": "INR", "estimated_recoverable_amount": Decimal("40"), "finding_id": "A", "sources": {"invoices": ["I1"]}},
        {"currency": "INR", "estimated_recoverable_amount": Decimal("25"), "finding_id": "B", "sources": {"invoices": ["I1", "I2"]}},
        {"currency": "INR", "estimated_recoverable_amount": Decimal("30"), "finding_id": "C", "sources": {"invoices": ["I2"]}},
        {"currency": "USD", "estimated_recoverable_amount": Decimal("12"), "finding_id": "D", "sources": {"invoices": ["I2"]}},
    ]
    assert unique_exposure(findings) == {"INR": Decimal("40"), "USD": Decimal("12")}


def test_import_reports_invalid_rows_and_normalizes_values():
    raw = pd.DataFrame([
        {"id": "I1", "supplier": "S1", "ref": "INV-1", "date": "2026-01-01", "amount": "20.10", "ccy": "inr"},
        {"id": "I2", "supplier": "S1", "ref": "INV-2", "date": "bad-date", "amount": "10", "ccy": "INR"},
    ])
    mapping = {
        "invoice_id": "id", "supplier_id": "supplier", "invoice_number": "ref",
        "invoice_date": "date", "amount": "amount", "currency": "ccy",
    }
    accepted, rejected = validate_import("invoices", raw, mapping)
    assert len(accepted) == 1
    assert accepted.iloc[0]["currency"] == "INR"
    assert accepted.iloc[0]["amount"] == Decimal("20.10")
    assert len(rejected) == 1
    assert "invoice_date" in rejected.iloc[0]["reason"]


def test_csv_export_escapes_spreadsheet_formulas():
    result = csv_safe(pd.DataFrame({"value": ["=2+2", "+SUM(A1)", "safe"]})).decode("utf-8-sig")
    assert "'=2+2" in result
    assert "'+SUM(A1)" in result
    assert "safe" in result


def test_demo_dataset_is_deterministic_and_over_ten_thousand_records():
    first, first_counts = generate_demo()
    second, second_counts = generate_demo()
    assert sum(first_counts.values()) >= 10_000
    assert first_counts == second_counts
    assert first["invoices"].equals(second["invoices"])
    assert first["payments"].equals(second["payments"])
