"""Guards against schema.sql drifting from the columns the loader and detections use."""
from __future__ import annotations

import re
from pathlib import Path

from src.exasol import SOURCE_TABLES

DATABASE = Path(__file__).resolve().parents[1] / "database"


def _schema_columns() -> dict[str, set[str]]:
    text = (DATABASE / "schema.sql").read_text(encoding="utf-8")
    tables = {}
    for name, body in re.findall(r"CREATE TABLE IF NOT EXISTS \w+\.(\w+)\s*\((.*?)\n\);", text, re.S | re.I):
        columns = set()
        for part in re.split(r",\s*(?![^()]*\))", body):
            token = part.strip().split()
            if token and token[0].upper() not in {"PRIMARY", "FOREIGN", "CONSTRAINT"}:
                columns.add(token[0].upper())
        tables[name.upper()] = columns
    return tables


def test_every_loaded_column_exists_in_schema():
    schema = _schema_columns()
    for table, columns in SOURCE_TABLES.values():
        missing = set(columns) - schema[table]
        assert not missing, f"{table} is missing {sorted(missing)} in database/schema.sql"


def test_credit_notes_have_currency_for_missed_credit_detection():
    assert "CURRENCY" in _schema_columns()["CREDIT_NOTES"]
    assert "c.CURRENCY" in (DATABASE / "detections" / "missed_credits.sql").read_text(encoding="utf-8")
