# How LeakageLens works (plain English)

LeakageLens looks for money a company may be losing on supplier payments. It compares four kinds of records:
**invoices** (what suppliers bill you), **purchase orders** (what you agreed to buy), **payments** (what you paid) and
**credit notes** (refunds a supplier owes you). Anything that does not add up becomes a **finding** for a person to review.

## The flow

1. **Start Here** - the guide. Shows your progress, the recommended next step, what every page does, what each check means,
   the CSV columns you need (with downloadable templates) and a short FAQ.
2. **Data Import** - upload CSVs (or load the demo data). Each row is validated; bad rows are rejected with a reason.
3. **Financial Audit** - press *Run analysis*. Eight checks run and produce findings; after a successful run, LeakageLens opens the Overview Dashboard.
4. **Overview Dashboard** - the summary: counts, money at risk by currency, charts and the largest findings.
5. **Findings Explorer** - the working screen. Filter, open a finding, read the explanation and calculation, inspect the
   linked records and save a review decision (New, Under Review, Confirmed, False Positive, Resolved).
6. **Transaction Explorer** - search the raw loaded records to verify a finding.
7. **Reports** - download findings as CSV and a full evidence pack as JSON.
8. **Audit History** - a log of runs in this session. **Settings** - optional Exasol database connection.

Every page shows a 4-step tracker (Import data > Run audit > Review findings > Export report), a
"What is this page for?" box, and a **Next step** link at the bottom.

## The checks

| Check | Meaning | Counted as exposure? |
|---|---|---|
| Duplicate invoice | Same supplier, same invoice number (punctuation ignored) | Yes |
| Possible duplicate invoice | Very similar numbers, amounts and dates | No - review only |
| Overpayment | Paid more than invoice minus unapplied credits | Yes |
| Possible duplicate payment | Two equal settled payments on one invoice within 30 days | Yes |
| Unapplied credit note | Supplier credit exists but invoice was paid in full | Yes |
| Purchase order mismatch | Invoice higher than approved PO beyond the tolerance % | Yes |
| Unmatched payment | Completed payment with no known invoice | No - review only |
| Data quality | Invalid dates or missing identifiers on an invoice | No - review only |

## Terms

- **Gross discrepancy** - the raw flagged amount; several checks can flag the same invoice, so it can double-count.
- **Estimated unique exposure** - the amount at risk when each linked invoice group is counted once. Use this one.
- **Confidence** - 0-100 heuristic score, not a probability.
- **Severity** - by amount: Low < 50,000; Medium >= 50,000; High >= 250,000; Critical >= 1,000,000.

Findings are leads for a human to check, not proof of loss or fraud.
