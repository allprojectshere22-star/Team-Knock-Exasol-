# Troubleshooting

## Exasol is not configured

Create `.env` from `.env.example`, populate `EXASOL_DSN`, `EXASOL_USER`, and `EXASOL_PASSWORD`, and restart Streamlit. The application does not display the password. If using a hosted environment, supply the values through its secret manager instead of committing `.env`.

## Connection refused or timeout

- Confirm Exasol Personal is running and listening on the configured DSN/port.
- Check network routing, firewall rules, TLS/encryption settings, and the host's accepted client IP.
- Test **Settings → Test Exasol connection** from the machine running Streamlit.
- Do not put a URL scheme (for example, `https://`) in `EXASOL_DSN`; use the Exasol host and port format expected by PyExasol.

## Permission or missing-table errors

Use an Exasol user permitted to create the configured schema and tables. Click **Settings → Initialize or upgrade Exasol schema**, then in **Data Import** confirm **Initialize schema and load snapshot to Exasol**. Confirm `EXASOL_SCHEMA` matches the intended schema.

## CSV validation or load errors

Use the header names documented in the README. Keep IDs unique within each table; use non-negative numeric monetary values; provide parseable dates. Include optional `reversal_of` and `reason` columns (blank where not applicable) if the source export lacks these fields. Check that each invoice's PO/payment/credit references use the expected source identifiers.

## SQL errors on the target Exasol release

No target Exasol instance was available during offline testing. Review the SQL statement identified in the Streamlit error/log, confirm the Exasol version's supported syntax and user privileges, and validate each query in a non-production schema. Report the exact Exasol version and failing query before changing SQL; do not treat local pytest success as database verification.

## Synthetic sample does not appear in Exasol

Generation creates a local session dataset. Initialize the schema and explicitly load the snapshot from **Data Import** before running **Financial Audit** in Exasol mode. Check the displayed source counts and audit ID.

## Streamlit / Python package installation

Use a supported Python version, recreate the virtual environment if it contains incompatible packages, and install dependencies with `python -m pip install -r requirements.txt`. The dependency manifest is the source of truth.
