from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import uuid

import pandas as pd
from rapidfuzz.fuzz import ratio

CENT = Decimal("0.01")

SCHEMAS: dict[str, dict[str, tuple[str, ...]]] = {
    "suppliers": {
        "required": ("supplier_id", "supplier_name", "currency"),
        "optional": ("normalized_supplier_name", "active_status"),
    },
    "purchase_orders": {
        "required": ("po_id", "supplier_id", "approved_amount", "currency", "status"),
        "optional": ("supplier_name", "created_date"),
    },
    "invoices": {
        "required": ("invoice_id", "supplier_id", "invoice_number", "invoice_date", "amount", "currency"),
        "optional": ("supplier_name", "po_id", "due_date", "description"),
    },
    "payments": {
        "required": ("payment_id", "supplier_id", "payment_date", "amount", "currency", "status"),
        "optional": ("invoice_id", "payment_reference", "reversal_of"),
    },
    "credit_notes": {
        "required": ("credit_id", "supplier_id", "credit_date", "amount", "currency"),
        "optional": ("invoice_id", "applied", "reason"),
    },
}

DATE_COLUMNS = {"invoice_date", "due_date", "created_date", "payment_date", "credit_date"}
AMOUNT_COLUMNS = {"amount", "approved_amount"}


def money(value: object) -> Decimal:
    try:
        result = Decimal(str(value).strip()).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Invalid monetary amount: {value!r}") from None
    if not result.is_finite():
        raise ValueError("Monetary amount must be finite.")
    return result


def _norm(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


_ISO_DATE = re.compile(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}")


def _as_date(value: object) -> date:
    """Parse a date. ISO (YYYY-MM-DD) is exact; other layouts are read day-first (DD/MM/YYYY)
    so that 03/04/2026 is 3 April, not 4 March."""
    if isinstance(value, (date, datetime, pd.Timestamp)):
        parsed = pd.Timestamp(value)
    else:
        text = str(value).strip()
        parsed = pd.to_datetime(text, dayfirst=not _ISO_DATE.match(text), errors="raise")
    if pd.isna(parsed):
        raise ValueError(f"Invalid date: {value!r}")
    return parsed.date()


def _active_payment(row: dict, reversed_payment_ids: set[str]) -> bool:
    status = str(row.get("status", "")).strip().lower()
    payment_id = str(row.get("payment_id", "") or "")
    reversal_of = str(row.get("reversal_of", "") or "").strip()
    return (
        status in {"settled", "completed", "paid", "success", "succeeded"}
        and not reversal_of
        and payment_id not in reversed_payment_ids
    )


def _finding(
    *,
    category: str,
    supplier_id: str,
    currency: str,
    discrepancy: Decimal,
    exposure: Decimal,
    confidence: int,
    explanation: str,
    formula: str,
    sources: dict[str, list[str]],
    next_action: str,
    finding_id: str,
) -> dict:
    amount = abs(discrepancy)
    severity = "Critical" if amount >= 1_000_000 else "High" if amount >= 250_000 else "Medium" if amount >= 50_000 else "Low"
    return {
        "finding_id": finding_id,
        "category": category,
        "severity": severity,
        "supplier_id": supplier_id,
        "currency": currency,
        "gross_discrepancy_amount": amount,
        "estimated_recoverable_amount": max(Decimal("0.00"), exposure),
        "confidence": confidence,
        "explanation": explanation,
        "formula": formula,
        "sources": sources,
        "next_action": next_action,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _records(frame: pd.DataFrame | None) -> list[dict]:
    """Rows as dicts with missing values (NaN/NaT/None) normalised to "".

    Optional CSV columns that were blank arrive as NaN, which is truthy and stringifies to
    "nan" - previously every blank reversal_of made a payment look reversed.
    """
    if frame is None or frame.empty:
        return []
    cleaned = frame.astype(object).where(frame.notna(), "")
    return cleaned.to_dict("records")


def analyze(data: dict[str, pd.DataFrame], fuzzy_threshold: int = 90, po_tolerance_pct: Decimal = Decimal("2")) -> list[dict]:
    invoices = _records(data.get("invoices"))
    pos = {str(r.get("po_id")): r for r in _records(data.get("purchase_orders"))}
    payments = _records(data.get("payments"))
    credits = _records(data.get("credit_notes"))
    suppliers = {str(r.get("supplier_id")): r for r in _records(data.get("suppliers"))}
    findings: list[dict] = []
    reversed_payment_ids = {
        str(row.get("reversal_of")).strip()
        for row in payments
        if str(row.get("reversal_of", "") or "").strip()
    }
    invoice_by_id = {str(r["invoice_id"]): r for r in invoices if r.get("invoice_id")}
    by_supplier_ref: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in invoices:
        if row.get("invoice_id") and row.get("invoice_number"):
            by_supplier_ref[(str(row.get("supplier_id", "")), _norm(row["invoice_number"]))].append(row)

    duplicate_pairs: set[frozenset[str]] = set()
    for rows in by_supplier_ref.values():
        if len(rows) > 1:
            rows.sort(key=lambda row: str(row["invoice_id"]))
            anchor = rows[0]
            for duplicate in rows[1:]:
                pair = frozenset((str(anchor["invoice_id"]), str(duplicate["invoice_id"])))
                duplicate_pairs.add(pair)
                amount = min(money(anchor.get("amount", 0)), money(duplicate.get("amount", 0)))
                findings.append(_finding(
                    category="Duplicate invoice", supplier_id=str(anchor.get("supplier_id", "")),
                    currency=str(anchor.get("currency", "INR")), discrepancy=amount, exposure=amount, confidence=97,
                    explanation=f"Invoice references normalize to the same value for {anchor['invoice_id']} and {duplicate['invoice_id']}. Verify the original documents before treating this as a loss.",
                    formula=f"min({anchor['invoice_id']} amount, {duplicate['invoice_id']} amount)",
                    sources={"invoices": [str(anchor["invoice_id"]), str(duplicate["invoice_id"])]},
                    next_action="Compare the original supplier invoices and confirm whether both were legitimately issued.",
                    finding_id=f"DUP-INV-{anchor['invoice_id']}-{duplicate['invoice_id']}",
                ))

    # Fuzzy matching only proposes a review candidate; its amount is not treated as recoverable.
    by_supplier: dict[str, list[dict]] = defaultdict(list)
    for row in invoices:
        by_supplier[str(row.get("supplier_id", ""))].append(row)
    candidate_count = 0
    for group in by_supplier.values():
        ordered = sorted(group, key=lambda row: (str(row.get("currency", "")), str(row.get("invoice_date", ""))))
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                if candidate_count >= 20_000:
                    break
                if left.get("currency") != right.get("currency"):
                    continue
                try:
                    if abs(money(left["amount"]) - money(right["amount"])) > max(money(left["amount"]), money(right["amount"])) * Decimal("0.02"):
                        continue
                    if abs((_as_date(left["invoice_date"]) - _as_date(right["invoice_date"])).days) > 30:
                        continue
                except (KeyError, ValueError):
                    continue
                score = ratio(_norm(left.get("invoice_number", "")), _norm(right.get("invoice_number", "")))
                if score < fuzzy_threshold or score >= 100:
                    continue
                candidate_count += 1
                pair = frozenset((str(left["invoice_id"]), str(right["invoice_id"])))
                if pair in duplicate_pairs:
                    continue
                findings.append(_finding(
                    category="Possible duplicate invoice", supplier_id=str(left.get("supplier_id", "")),
                    currency=str(left.get("currency", "INR")), discrepancy=Decimal("0"), exposure=Decimal("0"),
                    confidence=int(score), explanation=f"Invoice references are {score:.0f}% similar and amounts are within 2%. This is only a candidate match, not a confirmed duplicate.",
                    formula="Recoverable amount withheld pending human review",
                    sources={"invoices": [str(left["invoice_id"]), str(right["invoice_id"])]},
                    next_action="Review invoice dates, descriptions, and original documents.",
                    finding_id=f"FUZZY-INV-{left['invoice_id']}-{right['invoice_id']}",
                ))
            if candidate_count >= 20_000:
                break

    by_invoice_payments: dict[str, list[dict]] = defaultdict(list)
    for row in payments:
        invoice_id = str(row.get("invoice_id", "") or "").strip()
        if invoice_id and _active_payment(row, reversed_payment_ids):
            by_invoice_payments[invoice_id].append(row)

    by_invoice_credits: dict[str, list[dict]] = defaultdict(list)
    for row in credits:
        invoice_id = str(row.get("invoice_id", "") or "").strip()
        if invoice_id:
            by_invoice_credits[invoice_id].append(row)

    for invoice_id, invoice in invoice_by_id.items():
        currency = str(invoice.get("currency", "INR"))
        invoice_amount = money(invoice.get("amount", 0))
        invoice_payments = by_invoice_payments.get(invoice_id, [])
        invoice_credits = by_invoice_credits.get(invoice_id, [])
        active_credits = [c for c in invoice_credits if str(c.get("applied", "")).lower() not in {"true", "1", "yes"}]
        credit_total = sum((money(c.get("amount", 0)) for c in active_credits), Decimal("0.00"))
        payable = max(Decimal("0.00"), invoice_amount - credit_total)
        payment_total = sum((money(p.get("amount", 0)) for p in invoice_payments), Decimal("0.00"))
        payment_ids = [str(p["payment_id"]) for p in invoice_payments]
        credit_ids = [str(c["credit_id"]) for c in active_credits]
        source = {"invoices": [invoice_id], "payments": payment_ids, "credit_notes": credit_ids}

        if len(invoice_payments) > 1:
            for first_index, first in enumerate(invoice_payments):
                for second in invoice_payments[first_index + 1:]:
                    if first.get("currency") != second.get("currency"):
                        continue
                    if money(first.get("amount", 0)) != money(second.get("amount", 0)):
                        continue
                    gap = abs((_as_date(first["payment_date"]) - _as_date(second["payment_date"])).days)
                    ref_a, ref_b = _norm(first.get("payment_reference", "")), _norm(second.get("payment_reference", ""))
                    if gap <= 30 and (not ref_a or not ref_b or ref_a != ref_b):
                        repeat_amount = money(second["amount"])
                        findings.append(_finding(
                            category="Possible duplicate payment", supplier_id=str(invoice.get("supplier_id", "")),
                            currency=currency, discrepancy=repeat_amount, exposure=min(repeat_amount, max(Decimal("0"), payment_total - payable)),
                            confidence=82, explanation=f"Two completed payments of {repeat_amount} share invoice {invoice_id}, with equal amounts within {gap} days. Validate settlement references and allocation.",
                            formula=f"min(repeated payment {repeat_amount}, max(0, {payment_total} paid - {payable} payable))",
                            sources={**source, "payments": [str(first["payment_id"]), str(second["payment_id"])]},
                            next_action="Check bank settlement evidence and confirm payment allocation.",
                            finding_id=f"DUP-PAY-{first['payment_id']}-{second['payment_id']}",
                        ))
                        break

        excess = max(Decimal("0.00"), payment_total - payable)
        if excess:
            findings.append(_finding(
                category="Overpayment", supplier_id=str(invoice.get("supplier_id", "")), currency=currency,
                discrepancy=excess, exposure=excess, confidence=93,
                explanation=f"Completed payments of {payment_total} exceed invoice {invoice_id}'s credit-adjusted payable of {payable}.",
                formula=f"max(0, {payment_total} completed payments - ({invoice_amount} invoice - {credit_total} unapplied credits))",
                sources=source, next_action="Verify settled payments, credits, and any documented split allocations.",
                finding_id=f"OVERPAY-{invoice_id}",
            ))

        for credit in active_credits:
            if credit.get("currency", currency) != currency:
                continue
            credit_amount = money(credit.get("amount", 0))
            if payment_total > 0:
                findings.append(_finding(
                    category="Unapplied credit note", supplier_id=str(invoice.get("supplier_id", "")),
                    currency=currency, discrepancy=credit_amount, exposure=min(credit_amount, max(Decimal("0"), payment_total - max(Decimal("0"), invoice_amount - credit_amount))),
                    confidence=90, explanation=f"Credit note {credit['credit_id']} is marked unapplied for invoice {invoice_id}; settled payments total {payment_total}.",
                    formula=f"min({credit_amount} credit, payment evidence above credit-adjusted balance)",
                    sources={"invoices": [invoice_id], "payments": payment_ids, "credit_notes": [str(credit["credit_id"])]},
                    next_action="Confirm whether the credit was included in the supplier remittance or request its application.",
                    finding_id=f"CREDIT-{credit['credit_id']}",
                ))

        po = pos.get(str(invoice.get("po_id", "")))
        if po and str(po.get("status", "")).lower() in {"approved", "active", "open"} and po.get("currency") == currency:
            po_amount = money(po.get("approved_amount", 0))
            variance = invoice_amount - po_amount
            allowed = po_amount * po_tolerance_pct / Decimal("100")
            if variance > allowed:
                findings.append(_finding(
                    category="Purchase order mismatch", supplier_id=str(invoice.get("supplier_id", "")),
                    currency=currency, discrepancy=variance, exposure=variance, confidence=88,
                    explanation=f"Invoice {invoice_id} is above approved PO {po.get('po_id')} by {variance}, exceeding the configured {po_tolerance_pct}% tolerance.",
                    formula=f"{invoice_amount} invoice - {po_amount} approved PO (tolerance {po_tolerance_pct}%)",
                    sources={"invoices": [invoice_id], "purchase_orders": [str(po["po_id"])]},
                    next_action="Check PO amendments, partial deliveries, tax treatment, and approved tolerance.",
                    finding_id=f"PO-VAR-{invoice_id}",
                ))

    for row in payments:
        if not _active_payment(row, reversed_payment_ids):
            continue
        invoice_id = str(row.get("invoice_id", "") or "").strip()
        if not invoice_id or invoice_id not in invoice_by_id:
            findings.append(_finding(
                category="Unmatched payment", supplier_id=str(row.get("supplier_id", "")),
                currency=str(row.get("currency", "INR")), discrepancy=money(row.get("amount", 0)),
                exposure=Decimal("0.00"), confidence=55,
                explanation="Completed payment could not be linked to a known invoice. Unmatched amount is not treated as recoverable.",
                formula="Requires review; no recoverable amount assumed",
                sources={"payments": [str(row.get("payment_id", ""))]},
                next_action="Review remittance advice, advance-payment records, and invoice references.",
                finding_id=f"UNMATCHED-{row.get('payment_id')}",
            ))

    for row in invoices:
        try:
            amount = money(row.get("amount", 0))
            invoice_date = _as_date(row.get("invoice_date"))
            due_date = _as_date(row["due_date"]) if row.get("due_date") else None
            if due_date and due_date < invoice_date:
                raise ValueError("Due date precedes invoice date")
            if not row.get("supplier_id") or not row.get("invoice_number"):
                raise ValueError("Missing supplier or invoice identifier")
        except (ValueError, TypeError, KeyError) as exc:
            findings.append(_finding(
                category="Data quality", supplier_id=str(row.get("supplier_id", "")),
                currency=str(row.get("currency", "INR")), discrepancy=Decimal("0"), exposure=Decimal("0"),
                confidence=100, explanation=f"Invoice {row.get('invoice_id', '(unknown)')}: {exc}.",
                formula="No financial exposure calculated for data-quality findings",
                sources={"invoices": [str(row.get("invoice_id", ""))]},
                next_action="Correct the source record and rerun validation.",
                finding_id=f"DATA-{row.get('invoice_id', uuid.uuid4().hex[:8])}",
            ))
    return findings


def unique_exposure(findings: list[dict]) -> dict[str, Decimal]:
    """Attribute each linked invoice case once, by currency, using the largest estimate."""
    parent: dict[tuple[str, str], tuple[str, str]] = {}

    def find(node: tuple[str, str]) -> tuple[str, str]:
        parent.setdefault(node, node)
        if parent[node] != node:
            parent[node] = find(parent[node])
        return parent[node]

    def union(left: tuple[str, str], right: tuple[str, str]) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    eligible: list[tuple[dict, list[tuple[str, str]]]] = []
    for finding in findings:
        if not finding["currency"] or finding["estimated_recoverable_amount"] <= 0:
            continue
        currency = str(finding["currency"])
        invoice_ids = finding["sources"].get("invoices", [])
        nodes = [(currency, str(invoice_id)) for invoice_id in invoice_ids]
        if not nodes:
            nodes = [(currency, finding["finding_id"])]
        for node in nodes:
            find(node)
        for node in nodes[1:]:
            union(nodes[0], node)
        eligible.append((finding, nodes))

    cases: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for finding, nodes in eligible:
        root = find(nodes[0])
        cases[root] = max(cases[root], finding["estimated_recoverable_amount"])
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for (currency, _), amount in cases.items():
        totals[currency] += amount
    return dict(totals)


def generate_demo(seed: int = 2026) -> tuple[dict[str, pd.DataFrame], dict[str, int]]:
    import random

    rng = random.Random(seed)
    suppliers = []
    for index in range(60):
        supplier_name = (
            f"{rng.choice(['Northstar', 'BlueOak', 'Silverline', 'Evergreen', 'Summit', 'Cedar'])} "
            f"{rng.choice(['Trading', 'Industries', 'Supply', 'Services'])} {index + 1:02d}"
        )
        suppliers.append({
            "supplier_id": f"SUP-{index + 1:04d}",
            "supplier_name": supplier_name,
            "normalized_supplier_name": _norm(supplier_name),
            "currency": "INR",
            "active_status": "active",
        })
    invoices, purchase_orders, payments, credits = [], [], [], []
    invoice_count = 3000
    for index in range(invoice_count):
        supplier = suppliers[index % len(suppliers)]
        amount = Decimal(rng.randrange(5_000, 250_000)).quantize(CENT)
        inv_date = date(2025, 1, 1) + timedelta(days=rng.randrange(640))
        po_id = f"PO-{index + 1:05d}"
        invoice_id = f"INV-{index + 1:05d}"
        po_amount = amount * Decimal("0.80") if index < 25 else amount
        purchase_orders.append({
            "po_id": po_id, "supplier_id": supplier["supplier_id"], "supplier_name": supplier["supplier_name"],
            "approved_amount": po_amount, "currency": "INR", "status": "approved", "created_date": inv_date,
        })
        invoices.append({
            "invoice_id": invoice_id, "supplier_id": supplier["supplier_id"], "supplier_name": supplier["supplier_name"],
            "invoice_number": f"{supplier['supplier_id'][-2:]}-{2025 + inv_date.year - 2025}-{index + 1000:05d}",
            "invoice_date": inv_date, "due_date": inv_date + timedelta(days=30), "po_id": po_id,
            "amount": amount, "currency": "INR", "description": rng.choice(["Equipment", "Consulting", "Freight", "Materials", "Maintenance"]),
        })
        if index % 17 != 0:
            paid = amount * Decimal("0.5") if index % 11 == 0 else amount
            payments.append({
                "payment_id": f"PAY-{len(payments) + 1:05d}", "supplier_id": supplier["supplier_id"],
                "invoice_id": invoice_id, "payment_date": inv_date + timedelta(days=rng.randrange(5, 45)),
                "amount": paid, "currency": "INR", "status": "settled",
                "payment_reference": f"REM-{index + 1:05d}", "reversal_of": "",
            })
            if paid < amount:
                payments.append({
                    "payment_id": f"PAY-{len(payments) + 1:05d}", "supplier_id": supplier["supplier_id"],
                    "invoice_id": invoice_id, "payment_date": inv_date + timedelta(days=50),
                    "amount": amount - paid, "currency": "INR", "status": "settled",
                    "payment_reference": f"REM-{index + 1:05d}-B", "reversal_of": "",
                })
        if index < 25:
            payments.append({
                "payment_id": f"PAY-{len(payments) + 1:05d}", "supplier_id": supplier["supplier_id"],
                "invoice_id": invoice_id, "payment_date": inv_date + timedelta(days=60),
                "amount": amount, "currency": "INR", "status": "settled",
                "payment_reference": f"REM-DUP-{index + 1:05d}", "reversal_of": "",
            })
        if index < 800:
            credits.append({
                "credit_id": f"CR-{index + 1:05d}", "supplier_id": supplier["supplier_id"],
                "invoice_id": invoice_id, "credit_date": inv_date + timedelta(days=10),
                "amount": (amount * Decimal("0.10")).quantize(CENT), "currency": "INR",
                "applied": index >= 30, "reason": "Synthetic volume rebate",
            })
    for index in range(30):
        source = invoices[100 + index]
        duplicate = source.copy()
        duplicate["invoice_id"] = f"INV-DUP-{index + 1:04d}"
        duplicate["invoice_date"] = source["invoice_date"] + timedelta(days=2)
        invoices.append(duplicate)
    for index in range(15):
        supplier = suppliers[index]
        payments.append({
            "payment_id": f"PAY-ADV-{index + 1:04d}", "supplier_id": supplier["supplier_id"],
            "invoice_id": "", "payment_date": date(2026, 10, 1), "amount": Decimal("12500.00"),
            "currency": "INR", "status": "settled", "payment_reference": f"ADV-{index + 1:04d}", "reversal_of": "",
        })
    data = {
        "suppliers": pd.DataFrame(suppliers),
        "purchase_orders": pd.DataFrame(purchase_orders),
        "invoices": pd.DataFrame(invoices),
        "payments": pd.DataFrame(payments),
        "credit_notes": pd.DataFrame(credits),
    }
    counts = {name: len(frame) for name, frame in data.items()}
    return data, counts


def validate_import(entity: str, uploaded: pd.DataFrame, mapping: dict[str, str], existing: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if entity not in SCHEMAS:
        raise ValueError(f"Unsupported data type: {entity}")
    schema = SCHEMAS[entity]
    missing = [column for column in schema["required"] if not mapping.get(column)]
    if missing:
        raise ValueError("Map all required fields: " + ", ".join(missing))
    accepted: list[dict] = []
    errors: list[dict] = []
    required = set(schema["required"])
    key = {"suppliers": "supplier_id", "purchase_orders": "po_id", "invoices": "invoice_id", "payments": "payment_id", "credit_notes": "credit_id"}[entity]
    seen = {value.strip().upper() for value in existing[key].astype(str)} if existing is not None and key in existing.columns else set()
    for row_number, raw in enumerate(uploaded.to_dict("records"), start=2):
        record = {}
        try:
            for field in (*schema["required"], *schema["optional"]):
                source = mapping.get(field)
                value = raw.get(source) if source else None
                if pd.isna(value):
                    value = None
                if value is None or (isinstance(value, str) and not value.strip()):
                    if field in required:
                        raise ValueError(f"Missing required value: {field}")
                    continue
                if field in AMOUNT_COLUMNS:
                    try:
                        record[field] = money(value)
                    except ValueError as exc:
                        raise ValueError(f"Invalid {field}: {exc}") from exc
                    if record[field] < 0:
                        raise ValueError(f"{field} must not be negative")
                elif field in DATE_COLUMNS:
                    try:
                        record[field] = _as_date(value)
                    except (ValueError, TypeError) as exc:
                        raise ValueError(f"Invalid {field}: {exc}") from exc
                elif field == "currency":
                    currency = str(value).strip().upper()
                    if len(currency) != 3 or not currency.isalpha():
                        raise ValueError("currency must be a 3-letter code")
                    record[field] = currency
                elif field == "applied":
                    record[field] = str(value).strip().lower() in {"1", "true", "yes", "y"}
                elif field == "supplier_name":
                    record[field] = " ".join(str(value).split())
                elif field in {"status", "active_status"}:
                    record[field] = str(value).strip().lower()
                elif field.endswith("_id") or field == "reversal_of":
                    record[field] = str(value).strip().upper()
                else:
                    record[field] = str(value).strip()
            record[key] = str(record[key]).strip().upper()
            if entity == "suppliers" and record.get("supplier_name"):
                record["normalized_supplier_name"] = _norm(record["supplier_name"])
            if record[key] in seen:
                raise ValueError(f"Duplicate {key}: {record[key]}")
            seen.add(record[key])
            if entity != "suppliers" and record.get("supplier_id") is not None:
                record["supplier_id"] = str(record["supplier_id"]).strip()
            accepted.append(record)
        except (ValueError, TypeError, KeyError) as exc:
            errors.append({"row": row_number, "reason": str(exc), **raw})
    return pd.DataFrame(accepted), pd.DataFrame(errors)


def csv_safe(frame: pd.DataFrame) -> bytes:
    safe = frame.copy()
    for column in safe.select_dtypes(include=["object", "string"]).columns:
        safe[column] = safe[column].map(
            lambda value: "'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")) else value
        )
    return safe.to_csv(index=False).encode("utf-8-sig")
