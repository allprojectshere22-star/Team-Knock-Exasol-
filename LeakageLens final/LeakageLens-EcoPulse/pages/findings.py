import streamlit as st

from src.ui import current_reviews, ensure_state, findings, format_money, next_step, page_header, source_records

ensure_state()
page_header("findings")
rows = findings()
if not rows:
    st.info("No findings available. Load records and run an analysis first.")
    st.stop()

categories = sorted({row["category"] for row in rows})
statuses = ["New", "Under Review", "Confirmed", "False Positive", "Resolved"]
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    category = c1.selectbox("Finding type", ["All", *categories])
    severity = c2.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"])
    status = c3.selectbox("Review status", ["All", *statuses])
review_map = st.session_state["ll_reviews"]
filtered = [
    row for row in rows
    if (category == "All" or row["category"] == category)
    and (severity == "All" or row["severity"] == severity)
    and (status == "All" or review_map.get(row["finding_id"], {}).get("status", "New") == status)
]
st.dataframe(current_reviews(filtered), width="stretch", hide_index=True)
if not filtered:
    st.info("No findings match the selected filters.")
    st.stop()

selected_id = st.selectbox("Open finding", [row["finding_id"] for row in filtered])
finding = next(row for row in filtered if row["finding_id"] == selected_id)
st.subheader(f"{finding['category']} · {finding['finding_id']}")
with st.container(border=True):
    info, money_col = st.columns([3, 2])
    with info:
        st.write(finding["explanation"])
        st.markdown(f"**Severity:** {finding['severity']} · **Confidence:** {finding['confidence']}% *(heuristic score, not a probability)*")
        st.markdown(f"**Calculation:** `{finding['formula']}`")
        st.markdown(f"**Suggested next action:** {finding['next_action']}")
    with money_col:
        st.metric("Gross discrepancy", format_money(finding["gross_discrepancy_amount"], finding["currency"]))
        st.metric("Estimated recoverable", format_money(finding["estimated_recoverable_amount"], finding["currency"]))
with st.expander("Show supporting records", expanded=True):
    for table, frame in source_records(finding).items():
        st.markdown(f"**{table.replace('_', ' ').title()}**")
        st.dataframe(frame, width="stretch", hide_index=True)
    if not source_records(finding):
        st.caption("No linked source rows are available for this finding.")

current = review_map.get(selected_id, {})
with st.form(f"review_{selected_id}"):
    chosen_status = st.selectbox("Review status", statuses, index=statuses.index(current.get("status", "New")))
    notes = st.text_area("Reviewer notes", value=current.get("notes", ""))
    st.caption("Marking a finding resolved does not record money as recovered. Recovery amounts are not tracked in this prototype.")
    if st.form_submit_button("Save review"):
        from datetime import datetime, timezone
        review_map[selected_id] = {
            "status": chosen_status,
            "notes": notes,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        st.toast("Review saved for this session.", icon=":material/check_circle:")
        st.rerun()
next_step("findings")
