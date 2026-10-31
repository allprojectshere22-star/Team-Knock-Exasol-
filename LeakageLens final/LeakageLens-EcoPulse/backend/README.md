# LeakageLens backend (headless)

Everything that runs inside Exasol, usable without the web UI. It shares code with the app:
the schema and detection SQL live in `../database/`, and the CLI calls `../src/exasol.py`.

| Path | Purpose |
|---|---|
| `leakagelens_cli.py` | Create schema, optionally load CSVs, run all detections in Exasol, print findings and unique exposure. |
| `sql/02_load_demo_data.sql` | `IMPORT ... FROM LOCAL CSV FILE` statements for `data/demo_csv/` (for EXAplus or similar clients). |
| `sql/03_detections.sql` | The 7 detection queries as one script. Generated from `database/detections/`; regenerate with `python backend/build_sql_script.py`. |
| `build_sql_script.py` | Regenerates `sql/03_detections.sql`. |

## Command line (from the project root)

```
pip install -r requirements.txt
cp .env.example .env            # fill in EXASOL_DSN, EXASOL_USER, EXASOL_PASSWORD
python backend/leakagelens_cli.py --load data/demo_csv     # first run: create, load, analyse
python backend/leakagelens_cli.py                          # later runs: analyse what is loaded
python backend/leakagelens_cli.py --tolerance 5            # allow 5% over a purchase order
```

## Any Exasol SQL client

1. Run `database/schema.sql`.
2. Run `backend/sql/02_load_demo_data.sql` from the project root (needs LOCAL CSV import support).
3. Run each statement in `backend/sql/03_detections.sql`.

## Expected result on the demo data

The unique recoverable exposure is INR 7,107,157.40 (overlapping findings on one invoice are counted once).

## Verification status

The Python rule engine reproduces the figure above on `data/demo_csv/`. The Exasol path (schema, load, SQL detections, CLI)
has **not** been run against a live Exasol server; connection and LOCAL-import behaviour depend on your instance.
