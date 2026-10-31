import pandas as pd
import streamlit as st

from src.ui import ensure_state, next_step, page_header

ensure_state()
page_header("history")
runs = st.session_state["ll_runs"]
if not runs:
    st.info("No analysis runs in this session.")
else:
    st.dataframe(pd.DataFrame([
        {
            "Timestamp (UTC)": run["timestamp"],
            "Mode": run["mode"],
            "Source records": sum(run["records"].values()),
            "Findings": run["finding_count"],
            "Currencies": ", ".join(sorted(run["gross"])),
        }
        for run in reversed(runs)
    ]), width="stretch", hide_index=True)
next_step("history")
