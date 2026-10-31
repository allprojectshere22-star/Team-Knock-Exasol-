import streamlit as st

from src.ui import (counts, ensure_state, findings, has_data, next_step, page_header,
                    run_analysis, show_local_analysis_recovery)

ensure_state()
page_header("audit")
if st.session_state.get("ll_exasol_loaded"):
    st.success("Exasol mode: analysis executes the configured SQL detection queries against the loaded Exasol snapshot. SQL timing and run ID are recorded.")
else:
    st.info("Demo/local mode: analysis runs against the active session data in Python. Load a snapshot into Exasol from Data Import to run database-backed SQL analysis.")
st.write("Fuzzy reference matches are review candidates only and never receive an estimated recoverable amount.")
with st.expander("Analysis settings"):
    s1, s2 = st.columns(2)
    # Values live in session state (initialised by ensure_state); passing a default as well triggers a Streamlit warning.
    s1.slider("Fuzzy invoice-reference threshold", 70, 100, key="ll_threshold")
    s2.number_input("Purchase-order tolerance (%)", 0.0, 50.0, step=0.5, key="ll_po_tolerance")
st.subheader("Records in current analysis scope")
st.dataframe([{"Dataset": name.replace("_", " ").title(), "Records": value} for name, value in counts().items()], hide_index=True, width="stretch")
if not show_local_analysis_recovery("audit_run_local"):
    if not has_data():
        st.warning("Load synthetic demo data or import CSV records before running the analysis.")
    elif st.button("Run analysis", type="primary"):
        try:
            label = "Executing detection SQL in Exasol…" if st.session_state.get("ll_exasol_loaded") else "Checking invoices, payments, credits, and approved purchase orders…"
            with st.spinner(label):
                rows = run_analysis()
            st.success(f"Analysis complete: {len(rows):,} findings from {sum(counts().values()):,} source records.")
            metadata = st.session_state.get("ll_exasol_last_run")
            if st.session_state.get("ll_exasol_loaded") and metadata:
                st.caption(f"Exasol audit ID: {metadata['run_id']}")
                st.json(metadata["query_times_seconds"])
        except (RuntimeError, ValueError) as exc:
            st.error(f"Analysis failed; no local fallback was used: {exc}")
            show_local_analysis_recovery("audit_recover_local")
        else:
            st.switch_page("pages/dashboard.py")
if findings():
    st.caption(f"Current analysis contains {len(findings()):,} findings. Re-running replaces this in-memory result set.")
if findings():
    next_step("audit")
