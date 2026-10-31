# LeakageLens architecture

## Current runtime

`app.py` configures Streamlit and navigation. Each route in `pages/` renders a product workflow. `src/core.py` contains synthetic-data generation, field validation, Decimal arithmetic, detection rules, exposure grouping, and CSV-safe export. `src/ui.py` shares session-state accessors and report helpers across pages.

The local backend analyzes synthetic or imported session data in Python. The Exasol backend in `src/exasol.py` initializes the configured schema, inserts all five dataframes into generated staging tables in batches over the encrypted SQL connection, and replaces the source tables only after all stage loads succeed. The target-table delete/insert operations run in one DML transaction. Source snapshots are never silently redirected to a local database.

## Source data

The source entities are `suppliers`, `purchase_orders`, `invoices`, `payments`, and `credit_notes`. Monetary columns are normalized to `Decimal` for rule calculations. The CSV importer maps user-selected columns to the canonical names, validates required fields and rejects repeated identifiers. It keeps accepted and rejected rows separate and supports explicit append or replace.

## Analysis flow

1. Load an explicit local snapshot to Exasol from the Data Import page.
2. Read source counts from Exasol and create a persisted `AUDIT_RUNS` record.
3. Execute fixed SQL files for duplicate invoice/payment candidates, PO overbilling, missed credits, mismatches, and unmatched payments. Thresholds are formatted as safe numeric literals; the configured schema is validated.
4. Execute the fuzzy-candidate SQL, then score only its output using RapidFuzz. Fuzzy results have zero estimated recovery.
5. Normalize returned findings into shared UI objects and persist finding/evidence records with the audit ID and per-query execution time.
6. Group findings connected by invoice IDs to calculate estimated unique exposure by currency. Comparisons and totals do not combine currencies.
7. Present the Exasol result set and locally held review status/notes. Exports include active findings/evidence.

Fuzzy results and unmatched payments have zero estimated recovery. Exposure is not a claim of realized loss or recovered cash.

## Exasol boundary

Exasol is active only after a successful explicit snapshot load. Failed Exasol queries are surfaced; no local-analysis fallback is presented as database results. The app has not been verified against a live Exasol instance in this environment. Review statuses remain session-scoped, and persisted records contain audit outputs/evidence, not subsequent review edits.

## Limitations

The current prototype does not implement FX conversion, many-to-many payment allocations, PO amendment/partial-delivery accounting, supplier price-history baselines, or PDF reports. It is not production-ready or an accounting authority.
