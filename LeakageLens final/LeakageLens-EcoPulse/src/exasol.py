from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import re
import uuid
import json

import pandas as pd
import pyexasol
from rapidfuzz.fuzz import ratio

from src.core import money, unique_exposure

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TABLES = {
    "suppliers": ("SUPPLIERS", ("SUPPLIER_ID", "SUPPLIER_NAME", "NORMALIZED_SUPPLIER_NAME", "CURRENCY", "ACTIVE_STATUS")),
    "purchase_orders": ("PURCHASE_ORDERS", ("PO_ID", "SUPPLIER_ID", "SUPPLIER_NAME", "APPROVED_AMOUNT", "CURRENCY", "STATUS", "CREATED_DATE")),
    "invoices": ("INVOICES", ("INVOICE_ID", "SUPPLIER_ID", "SUPPLIER_NAME", "INVOICE_NUMBER", "PO_ID", "INVOICE_DATE", "DUE_DATE", "AMOUNT", "CURRENCY", "DESCRIPTION")),
    "payments": ("PAYMENTS", ("PAYMENT_ID", "SUPPLIER_ID", "INVOICE_ID", "PAYMENT_DATE", "AMOUNT", "CURRENCY", "STATUS", "PAYMENT_REFERENCE", "REVERSAL_OF")),
    "credit_notes": ("CREDIT_NOTES", ("CREDIT_ID", "SUPPLIER_ID", "INVOICE_ID", "CREDIT_DATE", "AMOUNT", "CURRENCY", "APPLIED", "REASON")),
}
ANALYSIS_SQL = (
    "duplicate_invoices",
    "duplicate_payments",
    "overbilling",
    "missed_credits",
    "payment_mismatches",
    "unmatched_payments",
)
INSERT_BATCH_SIZE = 250
DECIMAL_COLUMNS = {"APPROVED_AMOUNT", "AMOUNT"}
DATE_COLUMNS = {"CREATED_DATE", "INVOICE_DATE", "DUE_DATE", "PAYMENT_DATE", "CREDIT_DATE"}


class ExasolConfigurationError(ValueError):
    """The Exasol connection settings are incomplete or unsafe."""


def configuration() -> dict[str, object]:
    dsn = os.getenv("EXASOL_DSN", "").strip()
    user = os.getenv("EXASOL_USER", "").strip()
    password = os.getenv("EXASOL_PASSWORD", "")
    schema = os.getenv("EXASOL_SCHEMA", "LEAKAGELENS").strip().upper()
    if not dsn or not user or not password:
        raise ExasolConfigurationError(
            "Set EXASOL_DSN, EXASOL_USER, and EXASOL_PASSWORD in the environment or .env file."
        )
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", schema):
        raise ExasolConfigurationError("EXASOL_SCHEMA must be a simple SQL identifier.")
    return {
        "dsn": dsn,
        "user": user,
        "password": password,
        "schema": schema,
        "encryption": os.getenv("EXASOL_ENCRYPTION", "1").strip().lower() in {"1", "true", "yes"},
    }


def connect():
    settings = configuration()
    try:
        return pyexasol.connect(
            dsn=settings["dsn"],
            user=settings["user"],
            password=settings["password"],
            encryption=settings["encryption"],
        )
    except pyexasol.ExaError as exc:
        message = str(exc).replace(str(settings["password"]), "[redacted]")
        raise RuntimeError(f"Exasol connection failed ({type(exc).__name__}): {message}") from exc


def _runtime_database_error(exc) -> RuntimeError:
    password = os.getenv("EXASOL_PASSWORD", "")
    message = str(exc).replace(password, "[redacted]") if password else str(exc)
    return RuntimeError(f"Exasol operation failed ({type(exc).__name__}): {message}")


def _schema() -> str:
    return str(configuration()["schema"])


def _qualified(table: str, schema: str | None = None) -> str:
    allowed = {item[0] for item in SOURCE_TABLES.values()} | {"AUDIT_RUNS", "FINDINGS", "FINDING_EVIDENCE"}
    if table not in allowed and not re.fullmatch(r"LL_STAGE_[A-F0-9]{12}", table):
        raise ValueError(f"Unsupported Exasol table: {table}")
    return f"{schema or _schema()}.{table}"


def _sql_statements(path: Path) -> list[str]:
    statements = []
    for part in path.read_text(encoding="utf-8").split(";"):
        lines = [line for line in part.splitlines() if not line.lstrip().startswith("--")]
        query = "\n".join(lines).strip()
        if query:
            statements.append(query)
    return statements


def initialize_schema(connection=None) -> None:
    owns_connection = connection is None
    connection = connection or connect()
    schema = _schema()
    try:
        for statement in _sql_statements(ROOT / "database" / "schema.sql"):
            connection.execute(statement.replace("LEAKAGELENS", schema))
        _ensure_schema_columns(connection, schema)
    except pyexasol.ExaError as exc:
        raise _runtime_database_error(exc) from exc
    finally:
        if owns_connection:
            connection.close()


def _ensure_schema_columns(connection, schema: str) -> None:
    definitions = {
        "PAYMENTS": {
            "CURRENCY": "VARCHAR(3)",
            "PAYMENT_REFERENCE": "VARCHAR(200)",
        },
        "CREDIT_NOTES": {
            "CURRENCY": "VARCHAR(3)",
        },
        "AUDIT_RUNS": {
            "QUERY_TIMINGS": "VARCHAR(2000)",
        },
    }
    for table, columns in definitions.items():
        statement = connection.execute(
            "SELECT COLUMN_NAME FROM EXA_ALL_COLUMNS "
            "WHERE COLUMN_SCHEMA = {schema!s} AND COLUMN_TABLE = {table!s}",
            {"schema": schema, "table": table},
        )
        existing = {str(row[0]).upper() for row in statement.fetchall()}
        for column, data_type in columns.items():
            if column not in existing:
                connection.execute(
                    f"ALTER TABLE {_qualified(table, schema)} ADD COLUMN {column} {data_type}"
                )


def test_connection() -> dict[str, object]:
    connection = connect()
    try:
        statement = connection.execute("SELECT 1")
        statement.fetchone()
        return {"connected": True, "execution_seconds": getattr(statement, "execution_time", None)}
    finally:
        connection.close()


def _table_frame(entity: str, frame: pd.DataFrame) -> pd.DataFrame:
    _, columns = SOURCE_TABLES[entity]
    result = frame.copy()
    rename = {
        "approved_amount": "APPROVED_AMOUNT",
        "amount": "AMOUNT",
        "created_date": "CREATED_DATE",
        "invoice_date": "INVOICE_DATE",
        "due_date": "DUE_DATE",
        "payment_date": "PAYMENT_DATE",
        "credit_date": "CREDIT_DATE",
        "supplier_id": "SUPPLIER_ID",
        "supplier_name": "SUPPLIER_NAME",
        "normalized_supplier_name": "NORMALIZED_SUPPLIER_NAME",
        "active_status": "ACTIVE_STATUS",
        "po_id": "PO_ID",
        "invoice_id": "INVOICE_ID",
        "invoice_number": "INVOICE_NUMBER",
        "currency": "CURRENCY",
        "status": "STATUS",
        "description": "DESCRIPTION",
        "payment_id": "PAYMENT_ID",
        "payment_reference": "PAYMENT_REFERENCE",
        "reversal_of": "REVERSAL_OF",
        "credit_id": "CREDIT_ID",
        "applied": "APPLIED",
        "reason": "REASON",
    }
    result = result.rename(columns=rename)
    for column in columns:
        if column not in result:
            result[column] = None
    result = result.loc[:, list(columns)]
    for column in ("STATUS", "ACTIVE_STATUS"):
        if column in result:
            result[column] = result[column].map(lambda value: str(value).strip().upper() if pd.notna(value) else None)
    for column in ("SUPPLIER_ID", "PO_ID", "INVOICE_ID", "INVOICE_NUMBER", "PAYMENT_ID", "PAYMENT_REFERENCE", "REVERSAL_OF", "CREDIT_ID", "CURRENCY"):
        if column in result:
            result[column] = result[column].map(lambda value: str(value).strip() if pd.notna(value) and str(value).strip() else None)
    for column in ("SUPPLIER_ID", "PO_ID", "INVOICE_ID", "PAYMENT_ID", "CREDIT_ID", "CURRENCY"):
        if column in result:
            result[column] = result[column].map(lambda value: value.upper() if isinstance(value, str) else value)
    if entity == "suppliers" and "NORMALIZED_SUPPLIER_NAME" in result:
        result["NORMALIZED_SUPPLIER_NAME"] = result.apply(
            lambda row: row["NORMALIZED_SUPPLIER_NAME"]
            if pd.notna(row["NORMALIZED_SUPPLIER_NAME"]) and str(row["NORMALIZED_SUPPLIER_NAME"]).strip()
            else re.sub(r"[^A-Z0-9]", "", str(row["SUPPLIER_NAME"] or "").upper()),
            axis=1,
        )
    for column in ("APPROVED_AMOUNT", "AMOUNT"):
        if column in result:
            result[column] = result[column].map(lambda value: str(money(value)) if pd.notna(value) and str(value).strip() else None)
    if "APPLIED" in result:
        result["APPLIED"] = result["APPLIED"].map(
            lambda value: None if pd.isna(value) else str(value).strip().lower() in {"true", "1", "yes", "y"}
        )
    for column in ("INVOICE_DATE", "DUE_DATE", "CREATED_DATE", "PAYMENT_DATE", "CREDIT_DATE"):
        if column in result:
            result[column] = result[column].map(
                lambda value: value.isoformat() if hasattr(value, "isoformat") else (str(value) if pd.notna(value) and str(value).strip() else None)
            )
    for column, dtype in result.dtypes.items():
        if pd.api.types.is_object_dtype(dtype):
            result[column] = result[column].map(lambda value: None if pd.isna(value) else value)
    return result


def _insert_frame(connection, entity: str, frame: pd.DataFrame, table: str, schema: str) -> None:
    """Insert a normalized frame using the encrypted SQL connection, not temporary HTTP TLS."""
    columns = SOURCE_TABLES[entity][1]
    target = _qualified(table, schema)
    column_sql = ",".join(columns)

    for batch_start in range(0, len(frame), INSERT_BATCH_SIZE):
        batch = frame.iloc[batch_start:batch_start + INSERT_BATCH_SIZE]
        parameters = {}
        rows = []
        for row_offset, values in enumerate(batch.itertuples(index=False, name=None)):
            expressions = []
            for column, value in zip(columns, values):
                key = f"v_{row_offset}_{column.lower()}"
                if column == "APPLIED":
                    expressions.append("NULL" if value is None or pd.isna(value) else ("TRUE" if bool(value) else "FALSE"))
                elif column in DECIMAL_COLUMNS:
                    parameters[key] = value
                    expressions.append("{" + key + "!d}")
                elif column in DATE_COLUMNS:
                    parameters[key] = value
                    expressions.append("CAST({" + key + "!s} AS DATE)")
                else:
                    parameters[key] = value
                    expressions.append("{" + key + "!s}")
            rows.append("(" + ",".join(expressions) + ")")

        query = f"INSERT INTO {target} ({column_sql}) VALUES " + ",".join(rows)
        connection.execute(query, parameters)


def replace_source_data(data: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Stage all source tables over TLS, then replace the Exasol snapshot in one DML transaction."""
    connection = connect()
    schema = _schema()
    staging: dict[str, str] = {}
    try:
        initialize_schema(connection)
        for entity, (table, columns) in SOURCE_TABLES.items():
            stage = f"LL_STAGE_{uuid.uuid4().hex[:12].upper()}"
            staging[table] = stage
            connection.execute(
                f"CREATE TABLE {_qualified(stage, schema)} AS "
                f"SELECT {','.join(columns)} FROM {_qualified(table, schema)} WHERE 1 = 0"
            )
            frame = _table_frame(entity, data.get(entity, pd.DataFrame()))
            if not frame.empty:
                _insert_frame(connection, entity, frame, stage, schema)

        connection.set_autocommit(False)
        try:
            for table, stage in staging.items():
                connection.execute(f"DELETE FROM {_qualified(table, schema)}")
                connection.execute(
                    f"INSERT INTO {_qualified(table, schema)} SELECT * FROM {_qualified(stage, schema)}"
                )
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.set_autocommit(True)

        counts = source_counts(connection)
    except pyexasol.ExaError as exc:
        raise _runtime_database_error(exc) from exc
    finally:
        import sys
        active_error = sys.exc_info()[0] is not None
        cleanup_errors = []
        for stage in staging.values():
            try:
                connection.execute(f"DROP TABLE {_qualified(stage, schema)}")
            except Exception as exc:
                cleanup_errors.append(exc)
        connection.close()
        if cleanup_errors and not active_error:
            raise RuntimeError(
                f"Source snapshot loaded, but {len(cleanup_errors)} staging table(s) could not be removed."
            ) from cleanup_errors[0]
    return counts


def source_counts(connection=None) -> dict[str, int]:
    owns_connection = connection is None
    connection = connection or connect()
    try:
        counts = {}
        for entity, (table, _) in SOURCE_TABLES.items():
            statement = connection.execute(f"SELECT COUNT(*) FROM {_qualified(table)}")
            counts[entity] = int(statement.fetchone()[0])
        return counts
    finally:
        if owns_connection:
            connection.close()


def _split_ids(value: object) -> list[str]:
    return [part for part in str(value or "").split("|") if part]


def _to_finding(row: dict[str, object], run_id: str) -> dict:
    category = str(row["CATEGORY"])
    invoice_ids = _split_ids(row.get("INVOICE_ID"))
    if category.lower() in {"duplicate invoice", "possible duplicate invoice"}:
        invoice_ids.extend(_split_ids(row.get("SOURCE_IDS")))
    elif category.lower() == "overbilling" or category.lower() == "purchase order mismatch":
        invoice_ids = _split_ids(row.get("INVOICE_ID"))
    else:
        invoice_ids = _split_ids(row.get("INVOICE_ID"))
    invoice_ids = list(dict.fromkeys(invoice_ids))
    payment_ids = _split_ids(row.get("PAYMENT_IDS"))
    credit_ids = _split_ids(row.get("CREDIT_IDS"))
    po_ids = _split_ids(row.get("PO_ID"))
    difference = money(row.get("DIFFERENCE") or 0)
    expected = money(row.get("EXPECTED_AMOUNT") or 0)
    observed = money(row.get("OBSERVED_AMOUNT") or 0)
    confidence = int(Decimal(str(row.get("CONFIDENCE") or 0)) * 100)
    category_lower = category.lower()
    if category_lower == "unmatched payment":
        exposure = Decimal("0.00")
    elif category_lower == "payment mismatch" and observed <= expected:
        exposure = Decimal("0.00")
    else:
        exposure = abs(difference)
    amount = abs(difference)
    severity = "Critical" if amount >= 1_000_000 else "High" if amount >= 250_000 else "Medium" if amount >= 50_000 else "Low"
    original_id = str(row["FINDING_ID"])
    return {
        "finding_id": f"{original_id}-{run_id[:8]}",
        "category": category,
        "severity": severity,
        "supplier_id": str(row.get("SUPPLIER_ID") or ""),
        "currency": str(row.get("CURRENCY") or ""),
        "gross_discrepancy_amount": amount,
        "estimated_recoverable_amount": exposure,
        "confidence": confidence,
        "explanation": str(row.get("EXPLANATION") or ""),
        "formula": f"Expected {expected}; observed {observed}; difference {difference}",
        "sources": {
            "invoices": invoice_ids,
            "payments": payment_ids,
            "purchase_orders": po_ids,
            "credit_notes": credit_ids,
        },
        "evidence": str(row.get("EVIDENCE_TEXT") or ""),
        "source_ids": str(row.get("SOURCE_IDS") or ""),
        "next_action": str(row.get("NEXT_ACTION") or "Review the source transactions."),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "expected_amount": expected,
        "observed_amount": observed,
        "difference": difference,
    }


def _result_rows(statement) -> list[dict[str, object]]:
    columns = list(statement.col_names)
    return [dict(zip(columns, row)) for row in statement.fetchall()]


def _store_run(
    connection,
    run_id: str,
    counts: dict[str, int],
    findings: list[dict],
    status: str,
    error: str = "",
    query_times: dict[str, float] | None = None,
) -> None:
    invoice_count = counts.get("invoices", 0)
    po_count = counts.get("purchase_orders", 0)
    payment_count = counts.get("payments", 0)
    credit_count = counts.get("credit_notes", 0)
    gross_by_currency: dict[str, Decimal] = {}
    for finding in findings:
        currency = finding["currency"]
        gross_by_currency[currency] = gross_by_currency.get(currency, Decimal("0")) + finding["gross_discrepancy_amount"]
    totals_comparable = len(gross_by_currency) <= 1
    gross_total = sum(gross_by_currency.values(), Decimal("0")) if totals_comparable else None
    unique_values = unique_exposure(findings)
    unique_total = sum(unique_values.values(), Decimal("0")) if len(unique_values) <= 1 else None
    if status == "RUNNING":
        connection.execute(
            f"INSERT INTO {_qualified('AUDIT_RUNS')} "
            "(AUDIT_ID, STARTED_AT, STATUS, INVOICE_COUNT, PO_COUNT, PAYMENT_COUNT, CREDIT_COUNT, FINDING_COUNT, GROSS_FLAGGED, POTENTIAL_EXPOSURE) "
            "VALUES ({audit_id!s}, CURRENT_TIMESTAMP, 'RUNNING', {invoice_count!d}, {po_count!d}, "
            "{payment_count!d}, {credit_count!d}, 0, 0, 0)",
            {"audit_id": run_id, "invoice_count": invoice_count, "po_count": po_count, "payment_count": payment_count, "credit_count": credit_count},
        )
        return

    connection.execute(
        f"UPDATE {_qualified('AUDIT_RUNS')} SET COMPLETED_AT = CURRENT_TIMESTAMP, STATUS = {{status!s}}, "
        "FINDING_COUNT = {finding_count!d}, GROSS_FLAGGED = {gross!d}, POTENTIAL_EXPOSURE = {exposure!d}, "
        "ERROR_MESSAGE = {error!s}, QUERY_TIMINGS = {query_timings!s} WHERE AUDIT_ID = {audit_id!s}",
        {
            "status": status,
            "finding_count": len(findings),
            "gross": gross_total,
            "exposure": unique_total,
            "error": error[:1900],
            "query_timings": json.dumps(query_times or {}, separators=(",", ":"))[:1900],
            "audit_id": run_id,
        },
    )
    if status != "COMPLETED":
        return
    for finding in findings:
        sources = finding["sources"]
        connection.execute(
            f"INSERT INTO {_qualified('FINDINGS')} "
            "(FINDING_ID, AUDIT_ID, CATEGORY, INVOICE_ID, PO_ID, PAYMENT_IDS, CREDIT_IDS, "
            "EXPECTED_AMOUNT, OBSERVED_AMOUNT, DIFFERENCE, CONFIDENCE, EXPLANATION, NEXT_ACTION, "
            "REVIEW_STATUS, REVIEW_NOTES, EXPOSURE_AMOUNT, GROSS_AMOUNT, CONFIRMED_RECOVERY, CREATED_AT) "
            "VALUES ({finding_id!s}, {audit_id!s}, {category!s}, {invoice_ids!s}, {po_ids!s}, "
            "{payment_ids!s}, {credit_ids!s}, {expected!d}, {observed!d}, {difference!d}, "
            "{confidence!f}, {explanation!s}, {next_action!s}, 'NEW', '', {exposure!d}, "
            "{gross!d}, 0, CURRENT_TIMESTAMP)",
            {
                "finding_id": finding["finding_id"],
                "audit_id": run_id,
                "category": finding["category"][:80],
                "invoice_ids": "|".join(sources["invoices"])[:100],
                "po_ids": "|".join(sources["purchase_orders"])[:250],
                "payment_ids": "|".join(sources["payments"])[:500],
                "credit_ids": "|".join(sources["credit_notes"])[:500],
                "expected": finding["expected_amount"],
                "observed": finding["observed_amount"],
                "difference": finding["difference"],
                "confidence": Decimal(finding["confidence"]) / 100,
                "explanation": finding["explanation"][:1900],
                "next_action": finding["next_action"][:950],
                "exposure": finding["estimated_recoverable_amount"],
                "gross": finding["gross_discrepancy_amount"],
            },
        )
        connection.execute(
            f"INSERT INTO {_qualified('FINDING_EVIDENCE')} "
            "(EVIDENCE_ID, FINDING_ID, EVIDENCE_TYPE, EVIDENCE_TEXT, SOURCE_IDS, CREATED_AT) "
            "VALUES ({evidence_id!s}, {finding_id!s}, 'EXASOL_SQL', {evidence!s}, {source_ids!s}, CURRENT_TIMESTAMP)",
            {
                "evidence_id": f"{finding['finding_id']}-E",
                "finding_id": finding["finding_id"],
                "evidence": finding["evidence"][:1900],
                "source_ids": finding["source_ids"][:950],
            },
        )


def _fuzzy_findings(connection, threshold: int, tolerance: float, run_id: str) -> tuple[list[dict], float]:
    query = (ROOT / "database" / "detections" / "fuzzy_invoice_candidates.sql").read_text(encoding="utf-8")
    query = query.replace("LEAKAGELENS", _schema())
    statement = connection.execute(query, {"amount_tolerance": tolerance})
    result = []
    for row in _result_rows(statement):
        left_ref = str(row.get("LEFT_REFERENCE") or "")
        right_ref = str(row.get("RIGHT_REFERENCE") or "")
        score = ratio(re.sub(r"[^A-Z0-9]", "", left_ref.upper()), re.sub(r"[^A-Z0-9]", "", right_ref.upper()))
        if score < threshold or score >= 100:
            continue
        source_ids = [str(row["LEFT_ID"]), str(row["RIGHT_ID"])]
        result.append({
            "finding_id": f"FUZZY-INV-{source_ids[0]}-{source_ids[1]}-{run_id[:8]}",
            "category": "Possible duplicate invoice",
            "severity": "Low",
            "supplier_id": str(row.get("SUPPLIER_ID") or row.get("LEFT_SUPPLIER_ID") or ""),
            "currency": str(row.get("CURRENCY") or ""),
            "gross_discrepancy_amount": Decimal("0.00"),
            "estimated_recoverable_amount": Decimal("0.00"),
            "confidence": int(score),
            "explanation": f"SQL narrowed these invoices by supplier, amount, and date; their references score {score:.0f}% similar. This is an unconfirmed candidate.",
            "formula": f"RapidFuzz normalized reference similarity = {score:.0f}%",
            "sources": {
                "invoices": source_ids,
                "payments": [],
                "purchase_orders": [str(value) for value in (row.get("LEFT_PO"), row.get("RIGHT_PO")) if value],
                "credit_notes": [],
            },
            "evidence": (
                f"References: {left_ref!r} and {right_ref!r}; suppliers: "
                f"{row.get('LEFT_SUPPLIER')} and {row.get('RIGHT_SUPPLIER')}; "
                f"amounts: {row.get('LEFT_AMOUNT')} and {row.get('RIGHT_AMOUNT')}; "
                f"dates: {row.get('LEFT_DATE')} and {row.get('RIGHT_DATE')}."
            ),
            "source_ids": "|".join(source_ids),
            "next_action": "Review invoice dates, descriptions, supplier details, and source documents.",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "expected_amount": Decimal("0.00"),
            "observed_amount": Decimal("0.00"),
            "difference": Decimal("0.00"),
        })
    return result, float(statement.execution_time or 0)


def run_analysis(fuzzy_threshold: int = 90, po_tolerance_pct: float = 2.0) -> tuple[list[dict], dict[str, object]]:
    connection = connect()
    run_id = str(uuid.uuid4())
    tolerance = float(Decimal(str(po_tolerance_pct)) / Decimal("100"))
    started = datetime.now(timezone.utc)
    findings: list[dict] = []
    query_times: dict[str, float] = {}
    try:
        counts = source_counts(connection)
        if not counts["invoices"]:
            raise ValueError("The Exasol invoice table is empty. Load a source snapshot before analysis.")
        _store_run(connection, run_id, counts, findings, "RUNNING")
        try:
            for name in ANALYSIS_SQL:
                query = (ROOT / "database" / "detections" / f"{name}.sql").read_text(encoding="utf-8")
                query = query.replace("LEAKAGELENS", _schema())
                statement = connection.execute(query, {"amount_tolerance": tolerance})
                query_times[name] = float(statement.execution_time or 0)
                findings.extend(_to_finding(row, run_id) for row in _result_rows(statement))
            fuzzy_findings, query_times["fuzzy_invoice_candidates"] = _fuzzy_findings(
                connection, fuzzy_threshold, tolerance, run_id
            )
            findings.extend(fuzzy_findings)
            connection.set_autocommit(False)
            try:
                _store_run(connection, run_id, counts, findings, "COMPLETED", query_times=query_times)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.set_autocommit(True)
        except Exception as exc:
            error = str(exc).replace(str(configuration()["password"]), "[redacted]")
            _store_run(connection, run_id, counts, findings, "FAILED", error, query_times)
            raise
        return findings, {
            "run_id": run_id,
            "mode": "Exasol",
            "records": counts,
            "finding_count": len(findings),
            "started_at": started.isoformat(timespec="seconds"),
            "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "query_times_seconds": query_times,
        }
    except pyexasol.ExaError as exc:
        raise _runtime_database_error(exc) from exc
    finally:
        connection.close()
