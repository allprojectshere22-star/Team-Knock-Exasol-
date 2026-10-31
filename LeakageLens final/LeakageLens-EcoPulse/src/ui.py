from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
import streamlit as st

from src.core import SCHEMAS, analyze, generate_demo, unique_exposure


PALETTE = ["#83e6aa", "#7cc4ff", "#f2c65c", "#ff9f7b", "#c39bff", "#5fd0c4"]
SEVERITY_COLORS = {"Critical": "#ff7b7b", "High": "#ffaa5a", "Medium": "#f2c65c", "Low": "#83e6aa"}


def style_fig(fig, height: int = 340):
    """Apply the LeakageLens dark theme to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif", color="#c9d8ce", size=12),
        colorway=PALETTE, height=height, margin=dict(l=4, r=4, t=48, b=4),
        title=dict(font=dict(size=15, color="#f4faf6"), x=0, xanchor="left"),
        legend=dict(orientation="h", yanchor="top", y=-0.22, x=0, title_text=""),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)", zeroline=False, title_text="")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.07)", zeroline=False)
    return fig


# ---------------------------------------------------------------------------
# Guided-flow helpers: progress tracker, per-page help, "next step" links
# ---------------------------------------------------------------------------
PAGES = {
    "start": ("pages/start_here.py", "Start Here", ":material/explore:"),
    "dashboard": ("pages/dashboard.py", "Overview Dashboard", ":material/dashboard:"),
    "import": ("pages/data_import.py", "Data Import", ":material/upload_file:"),
    "audit": ("pages/financial_audit.py", "Financial Audit", ":material/query_stats:"),
    "findings": ("pages/findings.py", "Findings Explorer", ":material/troubleshoot:"),
    "transactions": ("pages/transactions.py", "Transaction Explorer", ":material/account_tree:"),
    "history": ("pages/history.py", "Audit History", ":material/history:"),
    "reports": ("pages/reports.py", "Reports", ":material/file_download:"),
    "settings": ("pages/settings.py", "Settings", ":material/settings:"),
}

# key -> (workflow step 1-4 or None, one-line purpose, how-to bullets, next page key, next label)
PAGE_INFO = {
    "dashboard": (None, "Your results at a glance: how many problems were found and how much money is involved.",
                  ["The four tiles count open findings, serious ones, all findings and loaded records.",
                   "Exposure shows the money that may be at risk, split by currency.",
                   "Charts show which kinds of problem cost the most and how severe they are.",
                   "The table lists the biggest findings first."],
                  "findings", "Investigate the findings"),
    "import": (1, "Bring your supplier records into LeakageLens. Nothing is analysed on this page.",
               ["Choose which dataset you are uploading (suppliers, purchase orders, invoices, payments or credit notes).",
                "Upload a CSV, then match each required field to one of your columns.",
                "Click Validate and import. Rows with problems are rejected and listed with the reason.",
                "Optional: send the data to an Exasol database so the checks run as SQL."],
               "audit", "Run the audit"),
    "audit": (2, "Run the checks that look for leaked money: duplicates, overpayments, missed credits and more.",
              ["Optionally adjust the two settings (how similar invoice numbers must be, and the allowed PO tolerance).",
               "Click Run analysis.",
               "Every problem found becomes a finding you can review."],
              "dashboard", "See the results"),
    "findings": (3, "Review each problem one by one, see the evidence, and record your decision.",
                 ["Filter the list by type, severity or review status.",
                  "Open a finding to read the explanation, the calculation and the linked invoices, payments and credits.",
                  "Set a review status (for example Confirmed or False Positive) and add notes, then Save review."],
                 "reports", "Export a report"),
    "transactions": (3, "Search the raw records you loaded, to double-check a finding against the source data.",
                     ["Pick a dataset.", "Type any ID, supplier or status into the search box."],
                     "findings", "Back to findings"),
    "history": (None, "A log of every audit you ran in this session.",
                ["Each row is one run: time, mode, records analysed and findings produced.",
                 "History is cleared when the browser session resets."],
                "audit", "Run another audit"),
    "reports": (4, "Download the results to share with finance or auditors.",
                ["Findings CSV: a spreadsheet-friendly list of every finding.",
                 "Evidence JSON: the full detail including the source record IDs behind each finding."],
                "history", "View audit history"),
    "settings": (None, "Connection and analysis settings, plus the limits of this prototype.",
                 ["Test the Exasol connection and create the database tables (optional).",
                  "Review the current analysis settings and privacy notes."],
                 "start", "Back to the guide"),
}

STEPS = [("Import data", "import"), ("Run audit", "audit"), ("Review findings", "findings"), ("Export report", "reports")]


def progress() -> dict:
    """Where the user is in the workflow, derived from session state."""
    ensure_state()
    rows = st.session_state["ll_findings"]
    reviewed = sum(1 for r in st.session_state["ll_reviews"].values() if r.get("status") not in (None, "New"))
    return {
        "loaded": has_data(),
        "audited": bool(rows) or bool(st.session_state.get("ll_last_run")),
        "findings": len(rows),
        "reviewed": reviewed,
        "records": sum(counts().values()),
    }


def next_recommended() -> tuple[str, str]:
    """(page key, reason) for the most useful next action."""
    p = progress()
    if not p["loaded"]:
        return "import", "No data yet - import your CSVs, or load the demo data from the dashboard."
    if not p["audited"]:
        return "audit", "Your data is loaded but has not been checked yet."
    if p["findings"] and not p["reviewed"]:
        return "findings", f"{p['findings']:,} findings are waiting for review."
    return "reports", "Export your results to share them."


def stepper_html(current: int | None) -> str:
    p = progress()
    done = [p["loaded"], p["audited"], p["reviewed"] > 0, False]
    parts = []
    for index, (label, _) in enumerate(STEPS, start=1):
        state = "done" if done[index - 1] and index != current else "now" if index == current else "todo"
        mark = "&#10003;" if state == "done" else str(index)
        parts.append(f'<div class="ll-flow-step {state}"><span class="ll-flow-dot">{mark}</span><span class="ll-flow-label">{label}</span></div>')
    return '<div class="ll-flow">' + '<span class="ll-flow-line"></span>'.join(parts) + "</div>"


def page_header(key: str, title: str | None = None) -> None:
    """Title, workflow tracker and a short 'what is this page' help box."""
    step, purpose, how, _, _ = PAGE_INFO[key]
    title = title or PAGES[key][1]
    left, right = st.columns([3, 1], vertical_alignment="center")
    with left:
        st.title(title)
        st.caption(purpose)
    with right:
        st.markdown(f'<div style="text-align:right"><span class="ll-pill">{st.session_state["ll_mode"]}</span></div>', unsafe_allow_html=True)
    st.markdown(stepper_html(step), unsafe_allow_html=True)
    with st.expander("What is this page for? How do I use it?", icon=":material/help:"):
        st.markdown("\n".join(f"{i}. {line}" for i, line in enumerate(how, start=1)))


def next_step(key: str) -> None:
    """A clear call-to-action linking to the next page in the flow."""
    _, _, _, target, label = PAGE_INFO[key]
    path, name, icon = PAGES[target]
    st.write("")
    with st.container(border=True):
        a, b = st.columns([3, 1], vertical_alignment="center")
        a.markdown(f"**Next step:** {label}")
        b.page_link(path, label=name, icon=icon)


def empty_data() -> dict[str, pd.DataFrame]:
    return {name: pd.DataFrame() for name in SCHEMAS}


def ensure_state() -> None:
    st.session_state.setdefault("ll_data", empty_data())
    st.session_state.setdefault("ll_findings", [])
    st.session_state.setdefault("ll_reviews", {})
    st.session_state.setdefault("ll_runs", [])
    st.session_state.setdefault("ll_mode", "Demo mode")
    st.session_state.setdefault("ll_threshold", 90)
    st.session_state.setdefault("ll_po_tolerance", 2.0)
    st.session_state.setdefault("ll_validation_errors", pd.DataFrame())
    st.session_state.setdefault("ll_exasol_loaded", False)
    st.session_state.setdefault("ll_exasol_counts", {})


def data() -> dict[str, pd.DataFrame]:
    ensure_state()
    return st.session_state["ll_data"]


def findings() -> list[dict]:
    ensure_state()
    return st.session_state["ll_findings"]


def counts() -> dict[str, int]:
    if st.session_state.get("ll_exasol_loaded"):
        return dict(st.session_state.get("ll_exasol_counts", {}))
    return {name: len(frame) for name, frame in data().items()}


def has_data() -> bool:
    return any(counts().values())


def show_local_analysis_recovery(button_key: str) -> bool:
    if not st.session_state.get("ll_exasol_loaded") or counts().get("invoices", 0) != 0:
        return False

    st.warning("The Exasol source snapshot has no invoices.")
    if data()["invoices"].empty:
        st.info("Load invoice data in Data Import, then load the source snapshot into Exasol.")
        st.page_link("pages/data_import.py", label="Open Data Import", icon=":material/upload_file:")
        return True

    st.info("Invoices are available in this session. You can run this analysis locally without changing Exasol.")
    if st.button("Run locally with current session data", key=button_key):
        st.session_state["ll_exasol_loaded"] = False
        st.session_state["ll_exasol_counts"] = {}
        st.session_state["ll_mode"] = "Local mode · session data"
        try:
            with st.spinner("Checking the current session data locally…"):
                result = run_analysis()
        except (RuntimeError, ValueError) as exc:
            st.error(f"Local analysis failed: {exc}")
        else:
            label = "finding" if len(result) == 1 else "findings"
            st.success(f"Local analysis complete: {len(result):,} {label}.")
            st.rerun()
    return True


def format_money(amount: Decimal | int | float, currency: str) -> str:
    return f"{currency} {Decimal(str(amount)):,.2f}"


def run_analysis() -> list[dict]:
    ensure_state()
    metadata = None
    if st.session_state.get("ll_exasol_loaded"):
        from src.exasol import run_analysis as run_exasol_analysis
        result, metadata = run_exasol_analysis(
            fuzzy_threshold=int(st.session_state["ll_threshold"]),
            po_tolerance_pct=float(st.session_state["ll_po_tolerance"]),
        )
    else:
        result = analyze(
            data(),
            fuzzy_threshold=int(st.session_state["ll_threshold"]),
            po_tolerance_pct=Decimal(str(st.session_state["ll_po_tolerance"])),
        )
    st.session_state["ll_findings"] = result
    run = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": st.session_state["ll_mode"],
        "records": counts(),
        "finding_count": len(result),
        "gross": {},
        "unique": unique_exposure(result),
    }
    if metadata:
        run.update(metadata)
        st.session_state["ll_mode"] = "Exasol · SQL analysis"
        st.session_state["ll_exasol_last_run"] = metadata
    gross: dict[str, Decimal] = {}
    for finding in result:
        currency = finding["currency"]
        gross[currency] = gross.get(currency, Decimal("0")) + finding["gross_discrepancy_amount"]
    run["gross"] = gross
    st.session_state["ll_runs"].append(run)
    st.session_state["ll_last_run"] = run["timestamp"]
    return result


def load_demo() -> dict[str, int]:
    ensure_state()
    sample, record_counts = generate_demo()
    st.session_state["ll_data"] = sample
    st.session_state["ll_findings"] = []
    st.session_state["ll_reviews"] = {}
    st.session_state["ll_validation_errors"] = pd.DataFrame()
    st.session_state["ll_mode"] = "Demo mode · synthetic data"
    st.session_state["ll_exasol_loaded"] = False
    st.session_state["ll_exasol_counts"] = {}
    return record_counts


def current_reviews(rows: list[dict]) -> pd.DataFrame:
    records = []
    reviews = st.session_state.get("ll_reviews", {})
    for finding in rows:
        review = reviews.get(finding["finding_id"], {})
        records.append({
            "finding_id": finding["finding_id"],
            "type": finding["category"],
            "supplier": finding["supplier_id"],
            "amount": finding["gross_discrepancy_amount"],
            "currency": finding["currency"],
            "severity": finding["severity"],
            "confidence": finding["confidence"],
            "review_status": review.get("status", "New"),
        })
    return pd.DataFrame(records)


def source_records(finding: dict) -> dict[str, pd.DataFrame]:
    result = {}
    table_for_type = {
        "invoices": ("invoices", "invoice_id"),
        "payments": ("payments", "payment_id"),
        "purchase_orders": ("purchase_orders", "po_id"),
        "credit_notes": ("credit_notes", "credit_id"),
    }
    for source_type, (table, key) in table_for_type.items():
        ids = finding.get("sources", {}).get(source_type, [])
        frame = data().get(table, pd.DataFrame())
        if ids and not frame.empty and key in frame:
            result[table] = frame[frame[key].astype(str).isin(ids)]
    return result
