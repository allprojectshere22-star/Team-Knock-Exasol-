# Synthetic data

LeakageLens creates reproducible fictional supplier data inside **Data Import**. Set a base invoice count (500–10,000) and seed (default `2026`). The four related source tables are invoices, approved purchase orders, payments, and credit notes. The base invoice count excludes deliberately duplicated invoice rows and associated seeded payment/credit rows; with seed `2026`, the default 4,000-invoice cohort produces 11,213 source rows (4,016 invoices, 4,000 purchase orders, 3,034 payments, and 163 credit notes).

Seeded cases cover duplicate invoices (including punctuation-only reference variations), PO overbilling, unapplied credits paid at gross value, repeated settled payments, and payment mismatches. `ground_truth` is returned separately by `src/generator.py` for evaluation; it is never uploaded to Exasol and is never read by production detection SQL.

No real supplier or customer data is included. Do not commit generated CSVs or customer financial data.
