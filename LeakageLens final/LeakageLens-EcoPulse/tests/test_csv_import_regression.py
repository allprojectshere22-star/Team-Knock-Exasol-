from decimal import Decimal

import pandas as pd

from src.core import SCHEMAS, analyze, validate_import


def _load(entity, rows):
    raw = pd.DataFrame(rows, dtype=str)
    fields = (*SCHEMAS[entity]["required"], *SCHEMAS[entity]["optional"])
    mapping = {f: (f if f in raw.columns else "") for f in fields}
    accepted, errors = validate_import(entity, raw, mapping, None)
    assert errors.empty
    return accepted


def test_blank_optional_columns_do_not_hide_payments():
    """Blank reversal_of used to become NaN -> 'nan' -> every payment looked reversed."""
    invoices = _load("invoices", [dict(invoice_id="I1", supplier_id="S1", invoice_number="A-1",
                                       invoice_date="2026-01-05", amount="1000", currency="INR")])
    payments = _load("payments", [
        dict(payment_id="P1", supplier_id="S1", payment_date="2026-02-01", amount="1000", currency="INR",
             status="settled", invoice_id="I1", reversal_of=""),
        dict(payment_id="P2", supplier_id="S1", payment_date="2026-02-02", amount="1000", currency="INR",
             status="settled", invoice_id="I1", reversal_of=""),
    ])
    findings = analyze({"invoices": invoices, "payments": payments}, 90, Decimal("2"))
    assert any(f["category"] == "Overpayment" for f in findings)
    assert not any(f["category"] == "Data quality" for f in findings)


def test_dates_are_day_first_unless_iso():
    from src.core import _as_date
    assert str(_as_date("2026-03-04")) == "2026-03-04"
    assert str(_as_date("03/04/2026")) == "2026-04-03"
