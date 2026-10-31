import json
import streamlit as st

from src.core import csv_safe, unique_exposure
from src.ui import counts, current_reviews, ensure_state, findings, next_step, page_header

ensure_state()
page_header("reports")
rows = findings()
if not rows:
    st.info("Run an analysis before exporting findings.")
    st.stop()
st.write("Exports include current findings and evidence. Currency totals are kept separate.")
table = current_reviews(rows)
st.download_button("Download findings CSV", csv_safe(table), "leakagelens-findings.csv", "text/csv", type="primary")
totals = {currency: str(value) for currency, value in unique_exposure(rows).items()}
summary = {
    "generated_at_utc": st.session_state.get("ll_last_run"),
    "data_mode": st.session_state["ll_mode"],
    "source_record_counts": counts(),
    "findings_by_type": table["type"].value_counts().to_dict(),
    "estimated_unique_exposure_by_currency": totals,
    "limitations": [
        "Demo-mode findings are indicators for human review, not proof of fraud or loss.",
        "Findings from Exasol mode were produced by SQL detection queries; local mode uses in-memory Python rules.",
        "Review state is held in the current Streamlit session.",
    ],
    "findings": [
        {
            **{key: (str(value) if hasattr(value, "as_tuple") else value) for key, value in finding.items() if key != "sources"},
            "sources": finding["sources"],
        }
        for finding in rows
    ],
}
st.download_button("Download evidence report JSON", json.dumps(summary, indent=2, default=str), "leakagelens-report.json", "application/json")
next_step("reports")
