import pandas as pd
import streamlit as st

from src.core import SCHEMAS, csv_safe, validate_import
from src.ui import counts, data, ensure_state, has_data, load_demo, next_step, page_header

ensure_state()
page_header("import")
st.info("CSV files are validated locally. Uploading the accepted snapshot to Exasol requires explicit confirmation. "
        "Not sure what columns you need? The Start Here page has downloadable CSV templates.", icon=":material/info:")

with st.expander("Load reproducible synthetic demo data"):
    st.write("The sample contains fictional suppliers, invoices, purchase orders, completed payments, duplicate records, and unapplied credits.")
    if has_data():
        confirm = st.checkbox("I understand loading demo data replaces the currently loaded source records.", key="confirm_demo_replace")
    else:
        confirm = True
    if st.button("Load demo dataset", disabled=not confirm, type="primary"):
        summary = load_demo()
        st.success(f"Loaded {sum(summary.values()):,} synthetic records: " + ", ".join(f"{k.replace('_', ' ')} {v:,}" for k, v in summary.items()))
        st.rerun()

st.subheader("Upload a source CSV")
entity = st.selectbox("Dataset", list(SCHEMAS), format_func=lambda x: x.replace("_", " ").title())
uploaded = st.file_uploader("Choose a CSV file (maximum 10 MB)", type=["csv"])
if uploaded and uploaded.size > 10 * 1024 * 1024:
    st.error("This file is larger than 10 MB. Split it into smaller CSV files and try again.")
    uploaded = None
if uploaded:
    try:
        raw = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        st.error(f"Could not read CSV: {exc}")
        st.stop()
    st.write(f"{len(raw):,} rows · {len(raw.columns)} columns")
    st.dataframe(raw.head(8), width="stretch", hide_index=True)
    fields = (*SCHEMAS[entity]["required"], *SCHEMAS[entity]["optional"])
    mapping = {}
    for field in fields:
        choices = ["— skip —", *raw.columns]
        detected = next((col for col in raw.columns if col.strip().lower() == field), "— skip —")
        mapping[field] = st.selectbox(
            f"{field}{' *' if field in SCHEMAS[entity]['required'] else ''}",
            choices, index=choices.index(detected), key=f"map_{entity}_{field}",
        )
        if mapping[field] == "— skip —":
            mapping[field] = ""
    import_mode = st.radio("Import behavior", ["Append records", "Replace this dataset"], horizontal=True)
    replace_confirm = True
    if import_mode == "Replace this dataset":
        replace_confirm = st.checkbox(f"Confirm replacing {len(data()[entity]):,} existing {entity.replace('_', ' ')} records.")
    if st.button("Validate and import", type="primary", disabled=(import_mode == "Replace this dataset" and not replace_confirm)):
        try:
            accepted, errors = validate_import(entity, raw, mapping, None if import_mode == "Replace this dataset" else data()[entity])
            if import_mode == "Replace this dataset":
                data()[entity] = accepted
            elif not accepted.empty:
                data()[entity] = pd.concat([data()[entity], accepted], ignore_index=True)
            st.session_state["ll_validation_errors"] = errors
            st.session_state["ll_findings"] = []
            st.session_state["ll_exasol_loaded"] = False
            st.session_state["ll_exasol_counts"] = {}
            st.session_state["ll_mode"] = "Local mode · uploaded data"
            st.success(f"Accepted {len(accepted):,}; rejected {len(errors):,}; existing-ID duplicates are rejected.")
        except ValueError as exc:
            st.error(str(exc))

errors = st.session_state.get("ll_validation_errors", pd.DataFrame())
if not errors.empty:
    st.subheader("Rejected rows")
    st.dataframe(errors, width="stretch", hide_index=True)
    st.download_button("Download validation errors CSV", csv_safe(errors), "validation-errors.csv", "text/csv")

st.subheader("Active dataset")
st.dataframe(pd.DataFrame([{"Dataset": key.replace("_", " ").title(), "Records": value} for key, value in counts().items()]), hide_index=True, width="stretch")

st.subheader("Load the current snapshot into Exasol")
st.write("This replaces all five corresponding source tables in the configured Exasol schema. The upload is staged first; existing tables are replaced only after all stage loads succeed.")
load_confirmation = st.checkbox(
    "I confirm that this will replace the current Exasol source snapshot with the records shown above.",
    key="confirm_exasol_replace",
)
if st.button("Initialize schema and load snapshot to Exasol", disabled=(not load_confirmation or not has_data()), type="primary"):
    try:
        from src.exasol import replace_source_data
        with st.spinner("Staging source records and replacing the Exasol snapshot…"):
            loaded_counts = replace_source_data(data())
        st.session_state["ll_exasol_loaded"] = True
        st.session_state["ll_exasol_counts"] = loaded_counts
        st.session_state["ll_mode"] = "Exasol · source snapshot loaded"
        st.session_state["ll_findings"] = []
        st.success("Exasol source snapshot replaced: " + ", ".join(f"{name.replace('_', ' ')} {count:,}" for name, count in loaded_counts.items()))
    except (RuntimeError, ValueError) as exc:
        st.error(f"Exasol load failed. The existing source tables were not intentionally replaced unless the staged transaction committed: {exc}")
next_step("import")
