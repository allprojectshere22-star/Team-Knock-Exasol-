# LeakageLens

**Find money your business may be silently losing.**

LeakageLens is a Streamlit prototype for reviewing supplier-payables data. It imports CSVs, validates and normalizes rows, runs explainable invoice/payment/credit/PO checks, links findings to source records, supports reviewer notes, and exports findings.

> **Execution modes:** local demo analysis is available without database credentials. Exasol mode can initialize the configured schema, stage and replace all five source tables, execute the SQL detection queries, score SQL-narrowed fuzzy candidates, and persist audit findings/evidence. No live Exasol instance was configured here, so database compatibility and results have not been verified against a running cluster. Findings are investigation candidates, not proof of fraud or confirmed savings.

## What it does

- Load a reproducible synthetic dataset containing more than 10,000 fictional source records.
- Import suppliers, purchase orders, invoices, payments, and credit notes from CSV with field mapping.
- Validate required values, dates, currencies, monetary amounts, and duplicate record identifiers; download rejected rows.
- Detect exact and fuzzy duplicate-invoice candidates, possible repeated payments, invoice overpayments, PO variances, unapplied credits, unmatched completed payments, and invoice data-quality issues.
- Inspect supporting source rows and calculations, filter findings, record session-scoped review statuses/notes, and download CSV/JSON reports.
- Keep currency totals separate, use `Decimal` for financial calculations, exclude reversals from settled payments, and deduplicate connected invoice cases for estimated unique exposure.

Fuzzy invoice matches are candidates only and carry no estimated recoverable amount. Unmatched payments are not assumed to be losses. Exposure values are estimates for human review, not recovered funds.

## Project layout (EcoPulse UI + LeakageLens backend, one app)

```
app.py, pages/, src/      Streamlit UI (EcoPulse) and the Exasol integration it calls (src/exasol.py)
database/                 Schema and the detection SQL that runs inside Exasol (single source of truth)
backend/                  Headless LeakageLens: CLI runner + SQL-client scripts (reuse src/, no duplicate logic)
data/demo_csv/            Full demo dataset (10,009 records), identical to the in-app "Load demo dataset"
data/sample_csv/          Small CSV templates for the importer
frontend/                 Unused Vite starter (the UI is Streamlit)
```

One process runs everything: `streamlit run app.py`. Copy `.env.example` to `.env` and fill in the Exasol settings to use Exasol mode; without it the app runs in local mode. See `backend/README.md` for the command-line and SQL-client routes.

## Run locally

Requirements: Python 3.11 or later. Node.js is not needed; `frontend/` is an unused Vite starter.

### Windows PowerShell

```powershell
cd C:\path\to\EcoPulse
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```bash
cd /path/to/EcoPulse
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Open <http://localhost:8501>. From **Overview Dashboard**, load the synthetic dataset and run analysis. Or use **Data Import** to map and import CSV files. Loading demo data replaces loaded data and requires confirmation.

## CSV fields

The importer lets you map arbitrary source headers to the fields below. Required fields are marked **required**; other fields are optional.

| Dataset | Required | Optional |
|---|---|---|
| Suppliers | `supplier_id`, `supplier_name`, `currency` | `active_status` |
| Purchase orders | `po_id`, `supplier_id`, `approved_amount`, `currency`, `status` | `supplier_name`, `created_date` |
| Invoices | `invoice_id`, `supplier_id`, `invoice_number`, `invoice_date`, `amount`, `currency` | `supplier_name`, `po_id`, `due_date`, `description` |
| Payments | `payment_id`, `supplier_id`, `payment_date`, `amount`, `currency`, `status` | `invoice_id`, `payment_reference`, `reversal_of` |
| Credit notes | `credit_id`, `supplier_id`, `credit_date`, `amount`, `currency` | `invoice_id`, `applied`, `reason` |

Dates must be parseable. Currency must be a three-letter code. Identifiers are treated as strings. The importer rejects negative amounts and duplicate IDs; it does not perform foreign-exchange conversion or automatically allocate ambiguous payments.

## Analysis and calculations

Analysis rules live in `src/core.py`; the UI is split into the Streamlit pages under `pages/`.

- Duplicate invoices use supplier ID plus punctuation/case-normalized invoice reference. Fuzzy reference candidates are constrained by supplier and amount and are never automatically confirmed.
- Completed/settled payments are matched to invoice IDs; reversed, cancelled, and failed payments are excluded.
- Potential overpayment is `max(0, settled linked payments - (invoice amount - unapplied linked credits))`.
- PO mismatch compares invoice total to an approved PO using the configured tolerance. This prototype does not model line-level quantities, amendments, or multiple invoice allocations to one PO.
- Unapplied credits are surfaced only when payment evidence exists. Unmatched payments are surfaced with zero estimated recoverable amount.
- `Decimal` is used for money. Gross flagged discrepancies may overlap. Estimated unique exposure groups findings connected by invoice IDs and takes the largest estimate for each connected case, separately by currency.

Confidence values are heuristic scores, not probabilities. Tax, currency conversion, partial PO allocations, payment splits across invoices, price history, and many source-specific accounting rules require additional implementation and human review.

## Exasol-backed data loading and analysis

1. Copy `.env.example` to `.env` and set `EXASOL_DSN`, `EXASOL_USER`, and `EXASOL_PASSWORD` using values from your own Exasol Personal setup. The project does not supply a hostname or credentials. Keep `.env` private; it is ignored by Git.
2. Open **Settings → Test Exasol connection**. This runs `SELECT 1`.
3. Choose **Initialize or upgrade Exasol schema**. The configured schema must permit table creation. Source tables are defined in `database/schema.sql`; existing payment and audit tables are upgraded with required columns.
4. Load demo data or validate/import CSVs in **Data Import**. Confirm **Initialize schema and load snapshot to Exasol**. All five source tables are inserted into staging tables in batches over the encrypted Exasol connection first; then one DML transaction replaces the current source snapshot. If staging fails, target source tables are not deleted.
5. Open **Financial Audit** and run the analysis. Duplicate invoices/payments, PO overbilling, missed credits, payment mismatches, and unmatched payments execute as SQL in the configured Exasol schema. A SQL query narrows fuzzy invoice candidates; RapidFuzz scores those candidates and flags review-only findings.
6. Results, query times, source counts, audit status, finding rows, and SQL evidence are persisted in `AUDIT_RUNS`, `FINDINGS`, and `FINDING_EVIDENCE`. The active session displays the Exasol result set; reviewer status/notes remain session-scoped.

Schema/table SQL identifiers are restricted to a validated schema identifier and fixed table allowlists. Values are escaped by PyExasol and sent over the encrypted SQL connection; uploads are never interpreted as SQL and do not require a temporary HTTP transfer endpoint. The Exasol connection and SQL analysis require network access to the configured instance. Failures are shown explicitly; the app never silently falls back to local analysis. If the Exasol snapshot has no invoices and local session invoices are available, the Financial Audit page and dashboard offer an explicit local-analysis action that does not change Exasol.

## Tests and smoke checks

Run the automated tests:

```powershell
python -m pytest -q
```

Manual smoke checklist:

1. Run `python -m streamlit run app.py` and open the app.
2. Load the demo dataset; confirm counts exceed 10,000 records.
3. Run analysis and inspect an evidence panel and linked source records.
4. Change a finding status and note; navigate away and back in the same session.
5. Download findings CSV and JSON report.
6. Upload a small CSV with one valid and one invalid row; inspect/download validation errors.
7. If Exasol is available, initialize its schema, load a confirmed snapshot, run SQL analysis, and verify the audit ID and per-query timings.
8. Confirm the UI identifies the active mode and does not call estimated exposure recovered money.

## Known limitations

- No live Exasol instance was available for validation; SQL syntax, import compatibility, and analytical outputs need to be smoke-tested against the target Exasol Personal version.
- Reviewer notes/statuses and the History page view exist only in the current Streamlit session; Exasol audit runs/findings/evidence are persisted in database tables.
- Demo data is INR-only. No exchange-rate conversion.
- PO allocation, cross-invoice payment allocation, supplier historical-price anomaly analysis, line-level tax checks, PDF reports, and durable reviewer-change logs are not implemented.
- The active synthetic data generator is deterministic and uses no ground-truth labels in detection.
- This is a hackathon prototype, not production accounting software, a fraud determination, or a compliance certification.

## Data privacy

Uploaded CSV data is parsed and validated by the local Streamlit process. It is sent to the configured Exasol instance only after the user confirms the source-snapshot load. Use synthetic or approved data, restrict access to the local app and database, and avoid exposing uploaded records or credentials.

## Demo guide

See [docs/demo-script.md](docs/demo-script.md) for a short walkthrough with separate local and Exasol steps.

## License

Apache License 2.0; see [LICENSE](LICENSE).
