import streamlit as st

from src.ui import ensure_state, next_step, page_header

ensure_state()
page_header("settings")
st.subheader("Execution mode")
st.info("Exasol mode is activated only after an explicit source snapshot load. Otherwise, analysis runs locally against the active session dataset.")
st.write(f"**Current mode:** {st.session_state['ll_mode']}")
st.subheader("Exasol connection")
st.caption("Settings are read from environment variables or the project .env file; credentials are never displayed.")

if st.button("Test Exasol connection"):
    try:
        from src.exasol import test_connection
        result = test_connection()
        st.success(f"Connection test passed (SELECT 1, {result['execution_seconds'] or 0:.3f}s).")
    except (RuntimeError, ValueError) as exc:
        st.error(f"Connection test failed: {exc}")

if st.button("Initialize or upgrade Exasol schema"):
    try:
        from src.exasol import initialize_schema
        initialize_schema()
        st.success("Configured source, audit, and evidence tables are ready.")
    except (RuntimeError, ValueError) as exc:
        st.error(f"Schema initialization failed: {exc}")

st.subheader("Analysis settings")
st.write(f"Fuzzy invoice-reference threshold: **{st.session_state['ll_threshold']}%**")
st.write(f"Purchase-order mismatch tolerance: **{st.session_state['ll_po_tolerance']}%**")
st.subheader("Privacy and limitations")
st.markdown(
    "- CSV validation is local; an explicit upload replaces source tables in Exasol.\n"
    "- Demo data is fictional; ground-truth labels are not used by detection rules.\n"
    "- Exasol SQL analysis results and evidence are persisted. Reviewer status edits remain session-scoped.\n"
    "- Estimated exposure is not confirmed recovery. This prototype does not record recovered money."
)
next_step("settings")
