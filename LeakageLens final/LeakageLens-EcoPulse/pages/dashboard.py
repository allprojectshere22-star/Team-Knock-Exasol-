import pandas as pd
import plotly.express as px
import streamlit as st

from src.core import unique_exposure
from src.ui import (PALETTE, SEVERITY_COLORS, counts, current_reviews, ensure_state, findings, format_money, has_data,
                    load_demo, next_step, page_header, run_analysis, show_local_analysis_recovery, style_fig)

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]

ensure_state()

page_header("dashboard")

if show_local_analysis_recovery("dashboard_run_local"):
    st.stop()

# ---------- Empty state: guided start ----------
if not has_data():
    with st.container(border=True):
        st.subheader("Get started in three steps")
        s1, s2, s3 = st.columns(3)
        steps = [
            ("1", "Load data", "Import your supplier, invoice, PO, payment and credit-note CSVs — or load the synthetic demo set."),
            ("2", "Run the audit", "Duplicate invoices, overpayments, PO overbilling, unapplied credits and unmatched payments are checked."),
            ("3", "Review findings", "Open each finding, inspect the linked records, and record a review decision."),
        ]
        for col, (n, head, body) in zip((s1, s2, s3), steps):
            col.markdown(f'<div class="ll-step"><div class="ll-step-n">{n}</div><div><h4>{head}</h4><p>{body}</p></div></div>', unsafe_allow_html=True)
        st.write("")
        if st.button("Load synthetic demo dataset", type="primary", icon=":material/science:"):
            loaded = load_demo()
            st.toast(f"Loaded {sum(loaded.values()):,} synthetic source records.", icon=":material/check_circle:")
            st.rerun()
    st.stop()

# ---------- Data loaded, not analysed ----------
rows = findings()
if not rows and not st.session_state.get("ll_last_run"):
    with st.container(border=True):
        st.warning("Records are loaded, but no analysis has been run yet.")
        if st.button("Run analysis", type="primary", icon=":material/play_arrow:"):
            try:
                with st.spinner("Analyzing active source records…"):
                    run_analysis()
                st.rerun()
            except (RuntimeError, ValueError) as exc:
                st.error(f"Analysis failed; no local fallback was used: {exc}")
                show_local_analysis_recovery("dashboard_recover_local")

# ---------- KPIs ----------
reviews = st.session_state.get("ll_reviews", {})
open_count = sum(reviews.get(f["finding_id"], {}).get("status", "New") in {"New", "Under Review"} for f in rows)
high_count = sum(f["severity"] in {"Critical", "High"} for f in rows)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Open findings", f"{open_count:,}")
k2.metric("High / critical", f"{high_count:,}")
k3.metric("Findings total", f"{len(rows):,}")
k4.metric("Source records", f"{sum(counts().values()):,}")

if not rows:
    if st.session_state.get("ll_last_run"):
        st.success("Analysis completed; no findings were returned.")
    st.stop()

# ---------- Exposure by currency ----------
gross, unique = {}, unique_exposure(rows)
for f in rows:
    if f["currency"]:
        gross[f["currency"]] = gross.get(f["currency"], 0) + f["gross_discrepancy_amount"]
st.subheader("Exposure by currency")
for currency in sorted(set(gross) | set(unique)):
    with st.container(border=True):
        g, u = st.columns(2)
        g.metric(f"Gross flagged · {currency}", format_money(gross.get(currency, 0), currency))
        u.metric(f"Estimated unique exposure · {currency}", format_money(unique.get(currency, 0), currency))
st.caption("Gross discrepancy can include overlapping rule alerts. Unique exposure counts each linked invoice group once. Neither figure is money saved.")

# ---------- Charts ----------
bar_col, pie_col = st.columns([3, 2])
with bar_col, st.container(border=True):
    totals = {}
    for f in rows:
        key = (f["category"], f["currency"] or "—")
        totals[key] = totals.get(key, 0) + float(f["estimated_recoverable_amount"])
    bar = pd.DataFrame([{"Finding type": k[0], "Currency": k[1], "Exposure": v} for k, v in totals.items()])
    fig = px.bar(bar, x="Exposure", y="Finding type", color="Currency", orientation="h", title="Estimated exposure by type",
                 color_discrete_sequence=PALETTE)
    fig.update_yaxes(categoryorder="total ascending", gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(style_fig(fig), width="stretch")
with pie_col, st.container(border=True):
    sev = pd.DataFrame([{"Severity": s, "Findings": sum(f["severity"] == s for f in rows)} for s in SEVERITY_ORDER])
    sev = sev[sev["Findings"] > 0]
    pie = px.pie(sev, names="Severity", values="Findings", hole=0.58, title="Findings by severity",
                 color="Severity", color_discrete_map=SEVERITY_COLORS, category_orders={"Severity": SEVERITY_ORDER})
    pie.update_traces(textinfo="value", marker=dict(line=dict(color="#0a110e", width=2)))
    st.plotly_chart(style_fig(pie), width="stretch")

# ---------- Largest findings ----------
st.subheader("Largest findings")
table = current_reviews(rows).sort_values("amount", ascending=False).head(12)
table["amount"] = table["amount"].astype(float)
st.dataframe(
    table, width="stretch", hide_index=True,
    column_config={
        "finding_id": st.column_config.TextColumn("Finding", width="medium"),
        "type": "Type", "supplier": "Supplier",
        "amount": st.column_config.NumberColumn("Amount", format="%,.2f"),
        "currency": st.column_config.TextColumn("Cur.", width="small"),
        "severity": "Severity",
        "confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%d%%"),
        "review_status": "Review",
    },
)
st.caption(f"Last analysis: {st.session_state.get('ll_last_run', 'not run')}")

with st.expander("Source record counts"):
    st.dataframe(pd.DataFrame([{"Dataset": n.replace("_", " ").title(), "Records": c} for n, c in counts().items()]),
                 width="stretch", hide_index=True)
next_step("dashboard")
