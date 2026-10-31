# Sample CSVs for the Data Import page

Import in this order: suppliers, purchase_orders, invoices, payments, credit_notes
(choose the dataset in the dropdown, upload the file, then click **Validate and import**).

Seeded cases: 2 PO overbilling invoices, 1 punctuation-variant duplicate invoice (INV-010 / INV-900),
1 repeated payment (PAY-020 / PAY-900), 3 unapplied credits paid at gross value, 1 unmatched advance payment,
1 reversed payment (PAY-902 reverses PAY-030).
`invoices.csv` also has 5 deliberately bad rows (bad date, bad amount, duplicate ID, bad currency, negative amount)
that must be rejected: expect "accepted 62, rejected 5".
