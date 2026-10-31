# Three-minute LeakageLens prototype walkthrough

Use the local steps for a demo without Exasol. To demonstrate Exasol-backed analysis, configure a reachable Exasol Personal instance first and follow the marked database steps. The project author has not verified a live database connection in this workspace.

| Time | Action | Narration |
|---|---|---|
| 0:00–0:20 | Open Overview Dashboard. | “LeakageLens helps reviewers investigate discrepancies across supplier invoices, orders, payments, and credits. Alerts are review candidates—not proof of fraud or confirmed savings.” |
| 0:20–0:45 | Load the synthetic demo data. Show the mode and source counts. | “This sample is reproducible fictional data. The current prototype analyzes it locally; no customer information is uploaded to an external service.” |
| 0:45–1:10 | Open Financial Audit and run analysis. If Exasol is configured, first load the snapshot in Data Import and select Exasol mode. | “In local mode, rules run against the session dataset. In Exasol mode, SQL detection queries run in the configured database, and RapidFuzz scores SQL-filtered fuzzy candidates.” |
| 1:10–1:50 | Open Findings Explorer; choose a duplicate invoice or payment; show formula and supporting records. | “Every alert links to its source records and shows a calculation. A heuristic confidence score is not a probability, and unmatched amounts are not assumed to be recoverable.” |
| 1:50–2:15 | Show the dashboard currency totals. | “Gross flagged amounts can overlap. Estimated unique exposure groups linked invoice findings and attributes the largest estimate once. Neither is reported as money saved.” |
| 2:15–2:35 | Change a review status and add a note. | “Review decisions are separate from the original evidence. In this prototype notes are held only for the current session; recovery tracking is not implemented.” |
| 2:35–3:00 | Download the CSV or JSON report. Briefly show the audit ID and query timings if Exasol was used. | “Mapped CSV imports validate locally. Exasol mode stages and replaces source tables, then persists audit findings and evidence. Reviewer status changes remain session-scoped.” |

Do not use real financial records in a public recording. Never claim Exasol analysis or recovered funds unless independently verified.
