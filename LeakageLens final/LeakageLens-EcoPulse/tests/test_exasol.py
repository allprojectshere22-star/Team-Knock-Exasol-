from datetime import date
from decimal import Decimal

import pandas as pd
import pytest
from pyexasol.formatter import ExaFormatter
from types import SimpleNamespace

from src import exasol


def test_configuration_requires_connection_secrets(monkeypatch):
    monkeypatch.delenv("EXASOL_DSN", raising=False)
    monkeypatch.delenv("EXASOL_USER", raising=False)
    monkeypatch.delenv("EXASOL_PASSWORD", raising=False)
    with pytest.raises(exasol.ExasolConfigurationError, match="EXASOL_DSN"):
        exasol.configuration()


def test_configuration_rejects_unsafe_schema_identifier(monkeypatch):
    monkeypatch.setenv("EXASOL_DSN", "db.example:8563")
    monkeypatch.setenv("EXASOL_USER", "user")
    monkeypatch.setenv("EXASOL_PASSWORD", "not-a-real-secret")
    monkeypatch.setenv("EXASOL_SCHEMA", "LL; DROP SCHEMA USERS")
    with pytest.raises(exasol.ExasolConfigurationError, match="SQL identifier"):
        exasol.configuration()


def test_table_frame_orders_columns_and_normalizes_source_values():
    frame = pd.DataFrame([{
        "supplier_id": " sup-1 ", "supplier_name": "  Sample Supplier  ",
        "currency": "INR", "active_status": "active",
    }])
    loaded = exasol._table_frame("suppliers", frame)
    assert list(loaded.columns) == list(exasol.SOURCE_TABLES["suppliers"][1])
    assert loaded.iloc[0]["SUPPLIER_ID"] == "SUP-1"
    assert loaded.iloc[0]["CURRENCY"] == "INR"
    assert loaded.iloc[0]["ACTIVE_STATUS"] == "ACTIVE"
    assert loaded.iloc[0]["NORMALIZED_SUPPLIER_NAME"] == "SAMPLESUPPLIER"


def test_sql_row_is_mapped_to_source_linked_exasol_finding():
    finding = exasol._to_finding({
        "FINDING_ID": "PAY-DUP-P1-P2",
        "CATEGORY": "Duplicate payment",
        "INVOICE_ID": "I1",
        "PO_ID": "PO1",
        "PAYMENT_IDS": "P1|P2",
        "CREDIT_IDS": None,
        "EXPECTED_AMOUNT": Decimal("100.00"),
        "OBSERVED_AMOUNT": Decimal("200.00"),
        "DIFFERENCE": Decimal("100.00"),
        "CONFIDENCE": Decimal("0.99"),
        "EXPLANATION": "SQL detected two equal payments.",
        "NEXT_ACTION": "Check statements.",
        "EVIDENCE_TEXT": "Source evidence.",
        "SOURCE_IDS": "P1|P2",
        "SUPPLIER_ID": "S1",
        "CURRENCY": "INR",
    }, "12345678-1234-1234-1234-123456789012")
    assert finding["category"] == "Duplicate payment"
    assert finding["sources"]["invoices"] == ["I1"]
    assert finding["sources"]["payments"] == ["P1", "P2"]
    assert finding["estimated_recoverable_amount"] == Decimal("100.00")
    assert finding["confidence"] == 99
    assert finding["evidence"] == "Source evidence."


def test_exasol_analysis_executes_all_sql_detection_queries(monkeypatch):
    class Result:
        execution_time = 0.012
        col_names = []
        rows = []

        def fetchone(self):
            return ({"INVOICES": 4, "PURCHASE_ORDERS": 4, "PAYMENTS": 3, "CREDIT_NOTES": 1, "SUPPLIERS": 2}.get(self.table, 0),)

        def fetchall(self):
            return self.rows

    class Connection:
        def __init__(self):
            self.queries = []
            self.parameters = []
            self.closed = False
            self.formatter = ExaFormatter(SimpleNamespace(options={"quote_ident": False}))

        def execute(self, query, query_params=None):
            if query_params:
                query = self.formatter.format(query, **query_params)
            self.queries.append(query)
            self.parameters.append(query_params)
            result = Result()
            result.table = next((name for name in ("INVOICES", "PURCHASE_ORDERS", "PAYMENTS", "CREDIT_NOTES", "SUPPLIERS") if f"FROM LEAKAGELENS.{name}" in query), "")
            if "'Overbilling' AS CATEGORY" in query:
                result.col_names = [
                    "FINDING_ID", "CATEGORY", "INVOICE_ID", "PO_ID", "PAYMENT_IDS", "CREDIT_IDS",
                    "EXPECTED_AMOUNT", "OBSERVED_AMOUNT", "DIFFERENCE", "CONFIDENCE", "EXPLANATION",
                    "NEXT_ACTION", "EVIDENCE_TEXT", "SOURCE_IDS", "SUPPLIER_ID", "CURRENCY",
                ]
                result.rows = [(
                    "OVER-I1", "Overbilling", "I1", "PO1", None, None,
                    Decimal("100"), Decimal("120"), Decimal("20"), Decimal("0.98"),
                    "Invoice exceeds the approved PO.", "Check amendment.", "Invoice and PO compared.",
                    "I1|PO1", "S1", "INR",
                )]
            return result

        def close(self):
            self.closed = True

        def set_autocommit(self, value):
            self.autocommit = value

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

    connection = Connection()
    monkeypatch.setattr(exasol, "connect", lambda: connection)
    monkeypatch.setattr(exasol, "_schema", lambda: "LEAKAGELENS")
    findings, metadata = exasol.run_analysis()
    parameterized_detection_queries = [
        params for params in connection.parameters
        if isinstance(params, dict) and "amount_tolerance" in params
    ]
    assert len(parameterized_detection_queries) == 7  # Six SQL rules plus SQL-narrowed fuzzy candidates.
    assert metadata["mode"] == "Exasol"
    assert metadata["records"]["invoices"] == 4
    assert len(metadata["query_times_seconds"]) == 7
    assert len(findings) == 1
    assert findings[0]["category"] == "Overbilling"
    assert findings[0]["sources"]["invoices"] == ["I1"]
    assert findings[0]["estimated_recoverable_amount"] == Decimal("20.00")
    assert connection.committed
    assert connection.closed


def test_source_replacement_imports_all_stages_before_target_deletes(monkeypatch):
    class Result:
        def __init__(self, value=0):
            self.value = value

        def fetchone(self):
            return (self.value,)

    class Connection:
        def __init__(self):
            self.tables = {table: 9 for table, _ in exasol.SOURCE_TABLES.values()}
            self.stage_targets = {}
            self.imported_stages = []
            self.events = []

        def execute(self, query, query_params=None):
            self.events.append(query)
            if query.startswith("CREATE TABLE"):
                stage = query.split("CREATE TABLE ")[1].split(" AS ")[0].split(".")[1]
                target = query.rsplit(" FROM ", 1)[1].split(" WHERE ", 1)[0].split(".")[1]
                self.stage_targets[stage] = target
            elif query.startswith("INSERT INTO") and " VALUES " in query:
                stage = query.split("INSERT INTO ")[1].split(" ")[0].split(".")[1]
                self.imported_stages.append(stage)
                self.tables[stage] = 1
            elif query.startswith("DELETE FROM"):
                table = query.split("DELETE FROM ")[1].split(".")[1]
                self.tables[table] = 0
            elif query.startswith("INSERT INTO"):
                target = query.split("INSERT INTO ")[1].split(" ")[0].split(".")[1]
                stage = query.rsplit(" FROM ", 1)[1].split(".")[1]
                self.tables[target] = self.tables.get(stage, 0)
            elif query.startswith("SELECT COUNT(*)"):
                table = query.rsplit(".", 1)[1]
                return Result(self.tables.get(table, 0))
            return Result()

        def set_autocommit(self, value):
            self.events.append(f"AUTOCOMMIT {value}")

        def commit(self):
            self.events.append("COMMIT")

        def rollback(self):
            self.events.append("ROLLBACK")

        def close(self):
            self.events.append("CLOSE")

    connection = Connection()
    monkeypatch.setattr(exasol, "connect", lambda: connection)
    monkeypatch.setattr(exasol, "_schema", lambda: "LEAKAGELENS")
    monkeypatch.setattr(exasol, "initialize_schema", lambda conn: None)
    data = {
        name: pd.DataFrame([{}]) if name == "suppliers" else pd.DataFrame()
        for name in exasol.SOURCE_TABLES
    }
    counts = exasol.replace_source_data(data)
    first_delete = next(index for index, query in enumerate(connection.events) if query.startswith("DELETE FROM"))
    assert len([query for query in connection.events[:first_delete] if query.startswith("CREATE TABLE")]) == 5
    assert len(connection.imported_stages) == 1
    assert connection.events.index("COMMIT") > first_delete
    assert counts["suppliers"] == 1
    assert all(counts[name] == 0 for name in counts if name != "suppliers")


def test_insert_frame_uses_escaped_values_and_typed_literals():
    class Connection:
        def __init__(self):
            self.queries = []
            self.formatter = ExaFormatter(SimpleNamespace(options={"quote_ident": False}))

        def execute(self, query, query_params=None):
            self.queries.append(self.formatter.format(query, **query_params))

    connection = Connection()
    frame = exasol._table_frame("credit_notes", pd.DataFrame([{
        "credit_id": "C1",
        "supplier_id": "S1",
        "credit_date": "2026-01-02",
        "amount": "25.50",
        "currency": "USD",
        "applied": "yes",
        "reason": "reviewer's credit",
    }]))

    exasol._insert_frame(connection, "credit_notes", frame, "LL_STAGE_0123456789AB", "LEAKAGELENS")

    assert len(connection.queries) == 1
    query = connection.queries[0]
    assert "CAST('2026-01-02' AS DATE)" in query
    assert "'25.50'" not in query
    assert "25.50" in query
    assert "TRUE" in query
    assert "'reviewer''s credit'" in query


def test_failed_stage_import_does_not_delete_existing_source_tables(monkeypatch):
    class Result:
        def fetchone(self):
            return (0,)

    class Connection:
        def __init__(self):
            self.queries = []
            self.closed = False

        def execute(self, query, query_params=None):
            self.queries.append(query)
            if query.startswith("INSERT INTO") and " VALUES " in query:
                raise RuntimeError("simulated stage import failure")
            return Result()

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(exasol, "connect", lambda: connection)
    monkeypatch.setattr(exasol, "_schema", lambda: "LEAKAGELENS")
    monkeypatch.setattr(exasol, "initialize_schema", lambda conn: None)
    data = {
        name: pd.DataFrame([{}]) if name == "suppliers" else pd.DataFrame()
        for name in exasol.SOURCE_TABLES
    }
    with pytest.raises(RuntimeError, match="stage import failure"):
        exasol.replace_source_data(data)
    assert not any(query.startswith("DELETE FROM") for query in connection.queries)
    assert connection.closed
