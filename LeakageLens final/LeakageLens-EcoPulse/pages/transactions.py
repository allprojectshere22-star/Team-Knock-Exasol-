import streamlit as st

from src.ui import data, ensure_state, next_step, page_header

ensure_state()
page_header("transactions")
dataset = st.selectbox("Source dataset", list(data()), format_func=lambda value: value.replace("_", " ").title())
frame = data()[dataset]
if frame.empty:
    st.info("No records in this dataset.")
else:
    query = st.text_input("Search rows", placeholder="Search identifiers, supplier, status…")
    shown = frame
    if query:
        mask = frame.astype(str).apply(lambda col: col.str.contains(query, case=False, regex=False, na=False)).any(axis=1)
        shown = frame[mask]
    st.caption(f"{len(shown):,} of {len(frame):,} records")
    st.dataframe(shown, width="stretch", hide_index=True)
next_step("transactions")
