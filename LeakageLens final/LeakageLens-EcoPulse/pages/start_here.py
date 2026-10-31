import io

import pandas as pd
import streamlit as st

from src.core import SCHEMAS
from src.ui import (PAGES, ensure_state, load_demo, next_recommended, progress, stepper_html)

ensure_state()
p = progress()

# ---------------------------------------------------------------- Hero
chips = [
    f"{p['records']:,} records loaded" if p["loaded"] else "No data loaded yet",
    f"{p['findings']:,} findings" if p["audited"] else "Audit not run",
    f"{p['reviewed']:,} reviewed" if p["reviewed"] else "Nothing reviewed",
]
chip_html = "".join(f'<span class="ll-chip">{c}</span>' for c in chips)
st.markdown(
    f"""
    <div class="ll-hero">
      <div class="ll-eyebrow">SUPPLIER PAYABLES AUDIT</div>
      <h1>Find the money your business is silently losing.</h1>
      <p>LeakageLens compares your <b>invoices</b>, <b>purchase orders</b>, <b>payments</b> and <b>credit notes</b>
      to spot duplicates, overpayments and missed credits &mdash; then walks you through reviewing each one.</p>
      <div class="ll-chips">{chip_html}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- Next step
key, reason = next_recommended()
path, name, icon = PAGES[key]
with st.container(border=True):
    a, b, c = st.columns([4, 1.4, 1.6], vertical_alignment="center")
    a.markdown(f"#### Your next step: {name}")
    a.caption(reason)
    b.page_link(path, label=f"Go to {name}", icon=icon)
    if not p["loaded"]:
        if c.button("Or load demo data", type="primary", icon=":material/science:"):
            load_demo()
            st.toast("Demo data loaded - now run the audit.", icon=":material/check_circle:")
            st.rerun()

# ---------------------------------------------------------------- The 4-step flow
st.header("How it works in four steps")
st.markdown(stepper_html(None), unsafe_allow_html=True)
flow = [
    ("1", "Import data", "pages/data_import.py", ":material/upload_file:",
     "Upload CSV files for suppliers, purchase orders, invoices, payments and credit notes. Bad rows are rejected with a reason.",
     "Output: clean records in memory"),
    ("2", "Run the audit", "pages/financial_audit.py", ":material/query_stats:",
     "Eight automatic checks compare the records against each other and flag anything that doesn't add up.",
     "Output: a list of findings"),
    ("3", "Review findings", "pages/findings.py", ":material/troubleshoot:",
     "Open each finding, read the plain-English explanation and calculation, inspect the linked records, and mark a decision.",
     "Output: reviewed findings"),
    ("4", "Export a report", "pages/reports.py", ":material/file_download:",
     "Download a CSV list and a JSON evidence pack to send to your finance team or auditors.",
     "Output: files you can share"),
]
cols = st.columns(4)
for col, (n, title, page, icon_, body, out) in zip(cols, flow):
    with col, st.container(border=True):
        st.markdown(f'<div class="ll-step"><div class="ll-step-n">{n}</div><div><h4>{title}</h4></div></div>', unsafe_allow_html=True)
        st.write(body)
        st.caption(out)
        st.page_link(page, label=f"Open {title.lower()}", icon=icon_)

# ---------------------------------------------------------------- Checks
st.header("What the audit looks for")
checks = [
    ("Duplicate invoice", "The same supplier billed the same invoice number twice (punctuation ignored).", "AB-1010 and ab 1010", "Counted"),
    ("Possible duplicate invoice", "Very similar invoice numbers with similar amount and date.", "AB-1010 vs AB-1011", "Review only"),
    ("Overpayment", "You paid more than the invoice minus any unapplied credits.", "Invoice 1,000 but 2,000 paid", "Counted"),
    ("Possible duplicate payment", "Two settled payments of the same amount on one invoice within 30 days.", "Two payments of 1,000", "Counted"),
    ("Unapplied credit note", "The supplier issued a credit, but the invoice was still paid in full.", "Credit 150 never used", "Counted"),
    ("Purchase order mismatch", "The invoice is higher than the approved PO by more than the tolerance %.", "PO 1,000, invoice 1,300", "Counted"),
    ("Unmatched payment", "A completed payment that matches no known invoice (e.g. an advance).", "Payment with blank invoice", "Review only"),
    ("Data quality", "An invoice with an invalid date or missing identifier.", "Due date before invoice date", "Review only"),
]
for row in (checks[:4], checks[4:]):
    cols = st.columns(4)
    for col, (name, body, example, counted) in zip(cols, row):
        badge = "ll-low" if counted == "Counted" else "ll-medium"
        with col, st.container(border=True):
            st.markdown(f'##### {name}\n<span class="ll-badge {badge}">{counted}</span>', unsafe_allow_html=True)
            st.write(body)
            st.caption(f"Example: {example}")
st.caption("\"Counted\" findings add to estimated exposure. \"Review only\" findings are flagged for a human but never counted as recoverable money.")

# ---------------------------------------------------------------- Terms
st.header("Plain-English glossary")
g1, g2 = st.columns(2)
with g1, st.container(border=True):
    st.markdown("**Gross discrepancy**  \nThe raw amount a rule flagged. Several rules can flag the same invoice, so this can double-count.")
    st.markdown("**Estimated unique exposure**  \nThe money possibly at risk after counting each linked invoice group only once. This is the safer number to quote.")
    st.markdown("**Confidence**  \nA 0-100 score for how strongly the evidence supports the finding. It is a heuristic, not a probability.")
with g2, st.container(border=True):
    st.markdown("**Severity**  \nBased on the amount: Low under 50,000 &middot; Medium from 50,000 &middot; High from 250,000 &middot; Critical from 1,000,000.")
    st.markdown("**Review status**  \nYour decision on a finding: New, Under Review, Confirmed, False Positive or Resolved.")
    st.markdown("**Neither figure is money saved.**  \nFindings are leads for a human to check, not proof of loss.")

# ---------------------------------------------------------------- Data guide
st.header("What your CSV files need")
st.caption("Column names should match exactly (case-insensitive). Dates are best as YYYY-MM-DD; other layouts are read day-first.")
EXAMPLES = {
    "suppliers": {"supplier_id": "SUP-001", "supplier_name": "Northstar Trading", "currency": "INR"},
    "purchase_orders": {"po_id": "PO-001", "supplier_id": "SUP-001", "approved_amount": "50000.00", "currency": "INR", "status": "approved", "created_date": "2026-01-10"},
    "invoices": {"invoice_id": "INV-001", "supplier_id": "SUP-001", "invoice_number": "AB-1001", "invoice_date": "2026-01-15", "amount": "50000.00", "currency": "INR", "po_id": "PO-001", "due_date": "2026-02-14", "description": "Materials"},
    "payments": {"payment_id": "PAY-001", "supplier_id": "SUP-001", "payment_date": "2026-02-10", "amount": "50000.00", "currency": "INR", "status": "settled", "invoice_id": "INV-001", "payment_reference": "REM-001", "reversal_of": ""},
    "credit_notes": {"credit_id": "CR-001", "supplier_id": "SUP-001", "credit_date": "2026-01-20", "amount": "1500.00", "currency": "INR", "invoice_id": "INV-001", "applied": "false", "reason": "Rebate"},
}
tabs = st.tabs([n.replace("_", " ").title() for n in SCHEMAS])
for tab, (entity, schema) in zip(tabs, SCHEMAS.items()):
    with tab:
        left, right = st.columns([3, 1], vertical_alignment="top")
        with left:
            st.markdown("**Required:** " + ", ".join(f"`{c}`" for c in schema["required"]))
            st.markdown("**Optional:** " + (", ".join(f"`{c}`" for c in schema["optional"]) or "none"))
            st.dataframe(pd.DataFrame([EXAMPLES[entity]]), hide_index=True, width="stretch")
        with right:
            buffer = io.StringIO()
            pd.DataFrame([EXAMPLES[entity]]).to_csv(buffer, index=False)
            st.download_button("Download template", buffer.getvalue(), f"{entity}_template.csv", "text/csv",
                               key=f"tpl_{entity}", icon=":material/download:")

# ---------------------------------------------------------------- FAQ
st.header("Common questions")
with st.expander("Where does my data go?"):
    st.write("By default it stays in this browser session's memory and disappears when the session ends. "
             "It is only sent to a database if you explicitly click the Exasol load button on Data Import.")
with st.expander("Do I need Exasol?"):
    st.write("No. Without Exasol, the same checks run locally in Python. Exasol mode runs them as SQL against a database, which scales to larger data.")
with st.expander("I just want to try it"):
    st.write("Use the 'load demo data' button above. It creates fictional suppliers and seeded problems so every check has something to find.")
with st.expander("Why did some rows get rejected on import?"):
    st.write("Each rejected row has a reason (bad date, non-numeric amount, duplicate ID, invalid currency or negative amount). Fix them in your CSV or download the error list from Data Import.")
with st.expander("Is a finding proof of fraud or loss?"):
    st.write("No. Findings are review candidates. Always verify against original documents before recovering money.")
