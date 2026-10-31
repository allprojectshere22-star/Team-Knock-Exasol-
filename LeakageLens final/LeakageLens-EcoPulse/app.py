from __future__ import annotations

from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

st.set_page_config(page_title="LeakageLens · Financial Intelligence", page_icon="◈",
                   layout="wide", initial_sidebar_state="expanded")

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #0a110e;  --bg-2: #0d1813;  --surface: #101d18;  --surface-2: #14241c;
  --line: #253a30;  --line-soft: #1b2d24;
  --ink: #e8f1eb;  --ink-strong: #f4faf6;  --muted: #93a69b;  --faint: #6b7f74;
  --mint: #83e6aa;  --mint-deep: #3fbf7a;  --mint-wash: rgba(131,230,170,.10);
  --warn: #f2c65c;  --danger: #ff7b7b;  --info: #7cc4ff;
  --radius: 14px;  --radius-sm: 10px;
  --shadow: 0 1px 0 rgba(255,255,255,.03) inset, 0 8px 24px rgba(0,0,0,.28);
  --ease: cubic-bezier(.2,.7,.2,1);
}

/* ---------- Base ---------- */
html, body, .stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp select, .stApp button {
  font-family: 'Inter', 'Aptos', 'Segoe UI', system-ui, sans-serif;
}
/* Never touch icon fonts */
[data-testid="stIconMaterial"], .material-icons, [class*="material-symbols"] {
  font-family: 'Material Symbols Rounded', 'Material Icons' !important; font-feature-settings: 'liga';
}
.stApp {
  background:
    radial-gradient(900px 480px at 85% -5%, rgba(131,230,170,.10), transparent 60%),
    radial-gradient(700px 400px at -5% 105%, rgba(63,191,122,.07), transparent 60%),
    var(--bg);
  color: var(--ink);
}
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1320px; }

/* Keep the header available for the sidebar toggle; hide only non-navigation chrome. */
#MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; height: 0; }
header[data-testid="stHeader"] { background: transparent; }

/* ---------- Typography ---------- */
h1, h2, h3, h4 { color: var(--ink-strong); letter-spacing: -.03em; font-weight: 650; }
h1 { font-size: 2.1rem; line-height: 1.15; padding-bottom: .25rem; }
h2 { font-size: 1.45rem; margin-top: 1.6rem; }
h3 { font-size: 1.12rem; }
p, li, label, [data-testid="stMarkdownContainer"] { color: var(--ink); line-height: 1.6; }
small, [data-testid="stCaptionContainer"] { color: var(--muted); }
a { color: var(--mint); text-decoration-color: rgba(131,230,170,.4); text-underline-offset: 3px; }
a:hover { color: #b6f5cf; }
code, pre, kbd { font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace; font-size: .86em; }
code { background: var(--surface-2); border: 1px solid var(--line-soft); border-radius: 6px; padding: .1em .4em; color: #c9f5d7; }
hr { border-color: var(--line-soft); margin: 1.4rem 0; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0e1a14 0%, var(--bg-2) 100%);
  border-right: 1px solid var(--line-soft);
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: .5rem; }
section[data-testid="stSidebar"] h2 { font-size: 1.25rem; margin: .2rem 0 0; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { letter-spacing: .14em; font-size: .68rem; color: var(--faint); }
.st-key-ll_page_navigation [data-testid="stIconMaterial"] { font-size: 14px !important; line-height: 1; }

/* Navigation links (supports older and newer Streamlit markup) */
[data-testid="stSidebarNav"] a, a[data-testid="stSidebarNavLink"] {
  border-radius: var(--radius-sm); margin: 2px 8px; padding: .5rem .75rem;
  color: var(--muted); font-weight: 500; transition: background .18s var(--ease), color .18s var(--ease);
}
[data-testid="stSidebarNav"] a:hover, a[data-testid="stSidebarNavLink"]:hover { background: var(--mint-wash); color: var(--ink-strong); }
[data-testid="stSidebarNav"] a[aria-current="page"], a[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: linear-gradient(90deg, rgba(131,230,170,.18), rgba(131,230,170,.05));
  color: var(--mint); box-shadow: inset 2px 0 0 var(--mint);
}

[data-testid="stNavSectionHeader"], [data-testid="stSidebarNav"] span[data-testid="stHeader"] {
  color: var(--faint); font-size: .68rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 600;
}

/* ---------- Metric cards ---------- */
[data-testid="stMetric"] {
  position: relative; overflow: hidden;
  background: linear-gradient(150deg, var(--surface-2), var(--surface));
  border: 1px solid var(--line); border-radius: var(--radius);
  padding: 18px 20px 16px; box-shadow: var(--shadow);
  transition: transform .2s var(--ease), border-color .2s var(--ease);
}
[data-testid="stMetric"]::before {
  content: ""; position: absolute; inset: 0 0 auto 0; height: 2px;
  background: linear-gradient(90deg, var(--mint), transparent 70%); opacity: .75;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); border-color: #3a5d4a; }
[data-testid="stMetricLabel"] p { color: var(--muted); font-size: .78rem; font-weight: 500; letter-spacing: .06em; text-transform: uppercase; }
[data-testid="stMetricValue"] { color: var(--ink-strong); font-size: 1.85rem; font-weight: 650; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
[data-testid="stMetricDelta"] { font-size: .8rem; font-weight: 500; }

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: var(--radius-sm); border: 1px solid #36563f; background: #12281c; color: #d3f7e0;
  font-weight: 600; padding: .5rem 1.1rem; transition: all .18s var(--ease);
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  border-color: var(--mint); background: #17341f; color: #fff; transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(131,230,170,.12);
}
.stButton > button:active { transform: translateY(0); }
button[kind="primary"], [data-testid="stBaseButton-primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, var(--mint), var(--mint-deep)) !important;
  border-color: transparent !important; color: #06150d !important;
}
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover { filter: brightness(1.08); color: #04100a !important; }
button:focus-visible, a:focus-visible, [role="tab"]:focus-visible, input:focus-visible {
  outline: 2px solid var(--mint) !important; outline-offset: 2px;
}

/* ---------- Inputs ---------- */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], .stNumberInput input, .stTextInput input {
  background: var(--surface) !important; border-color: var(--line) !important; border-radius: var(--radius-sm) !important;
}
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-baseweb="textarea"]:focus-within {
  border-color: var(--mint) !important; box-shadow: 0 0 0 3px var(--mint-wash) !important;
}
[data-testid="stWidgetLabel"] p { color: var(--muted); font-size: .85rem; font-weight: 500; }
[data-testid="stFileUploaderDropzone"] {
  background: var(--surface); border: 1.5px dashed #34503f; border-radius: var(--radius);
  transition: border-color .2s var(--ease), background .2s var(--ease);
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--mint); background: var(--surface-2); }

/* ---------- Tabs ---------- */
[data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid var(--line-soft); }
button[role="tab"] { color: var(--muted); font-weight: 500; padding: .6rem 1rem; border-radius: var(--radius-sm) var(--radius-sm) 0 0; }
button[role="tab"]:hover { color: var(--ink-strong); background: var(--mint-wash); }
button[role="tab"][aria-selected="true"] { color: var(--mint); }
[data-baseweb="tab-highlight"] { background: var(--mint); height: 2px; }
[data-baseweb="tab-border"] { display: none; }

/* ---------- Containers, expanders, tables ---------- */
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); overflow: hidden; }
[data-testid="stExpander"] summary:hover { background: var(--surface-2); }
div[data-testid="stDataFrame"], div[data-testid="stTable"] {
  border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow);
}
div[data-testid="stPlotlyChart"], div[data-testid="stArrowVegaLiteChart"] { background: transparent; }
/* Bordered containers (st.container(border=True)) become cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--line) !important; border-radius: var(--radius) !important;
  background: linear-gradient(160deg, rgba(20,36,28,.75), rgba(16,29,24,.75)); box-shadow: var(--shadow);
}
.ll-pill { display:inline-flex; align-items:center; gap:.45rem; padding:.3rem .8rem; border-radius:999px; font-size:.78rem; font-weight:600;
  color:#bff1d2; background:var(--mint-wash); border:1px solid rgba(131,230,170,.3); }
.ll-pill::before { content:""; width:7px; height:7px; border-radius:50%; background:var(--mint); box-shadow:0 0 8px var(--mint); }
.ll-step { display:flex; gap:.9rem; align-items:flex-start; }
.ll-step-n { flex:0 0 auto; width:30px; height:30px; border-radius:50%; display:grid; place-items:center; font-weight:700;
  color:#06150d; background:linear-gradient(135deg,var(--mint),var(--mint-deep)); }
.ll-step h4 { margin:.1rem 0 .2rem; font-size:1rem; } .ll-step p { margin:0; color:var(--muted); font-size:.9rem; }

/* ---------- Alerts ---------- */
div[data-testid="stAlert"] { border-radius: var(--radius); border: 1px solid var(--line); backdrop-filter: blur(4px); }

/* ---------- Progress / status ---------- */
[data-testid="stProgress"] > div > div > div { background: linear-gradient(90deg, var(--mint-deep), var(--mint)); border-radius: 999px; }
[data-testid="stStatusWidget"], [data-testid="stSpinner"] { color: var(--mint); }

/* ---------- Scrollbars ---------- */
* { scrollbar-width: thin; scrollbar-color: #2c4638 transparent; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #2c4638; border-radius: 999px; border: 2px solid var(--bg); }
::-webkit-scrollbar-thumb:hover { background: #3d6150; }

/* ---------- Page fade-in ---------- */
.block-container { animation: ll-fade .35s var(--ease) both; }
@keyframes ll-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}

/* ---------- Reusable helper classes for pages ---------- */
.ll-brand { display: flex; align-items: center; gap: .65rem; padding: .35rem .25rem .1rem; }
.ll-logo {
  width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; font-size: 1.25rem; font-weight: 700;
  color: #06150d; background: linear-gradient(135deg, var(--mint), var(--mint-deep)); box-shadow: 0 6px 18px rgba(131,230,170,.25);
}
.ll-brand-name { font-size: 1.15rem; font-weight: 650; color: var(--ink-strong); letter-spacing: -.02em; line-height: 1.1; }
.ll-brand-sub { font-size: .66rem; letter-spacing: .16em; color: var(--faint); margin-top: 2px; }
.ll-card { background: linear-gradient(150deg, var(--surface-2), var(--surface)); border: 1px solid var(--line); border-radius: var(--radius); padding: 1.1rem 1.25rem; box-shadow: var(--shadow); }
.ll-badge { display: inline-block; padding: .15rem .6rem; border-radius: 999px; font-size: .72rem; font-weight: 600; letter-spacing: .03em; border: 1px solid transparent; }
.ll-critical { color: #ffb0b0; background: rgba(255,123,123,.12); border-color: rgba(255,123,123,.35); }
.ll-high     { color: #ffcf9a; background: rgba(255,170,90,.12);  border-color: rgba(255,170,90,.35); }
.ll-medium   { color: #f2e08a; background: rgba(242,198,92,.12);  border-color: rgba(242,198,92,.35); }
.ll-low      { color: #a9e8c2; background: rgba(131,230,170,.10); border-color: rgba(131,230,170,.30); }


/* ---------- Hero, workflow tracker, chips, page links ---------- */
.ll-hero { position:relative; overflow:hidden; border:1px solid var(--line); border-radius:22px; padding:2.4rem 2.4rem 2rem; margin-bottom:1.2rem;
  background: radial-gradient(600px 260px at 90% 0%, rgba(131,230,170,.24), transparent 65%),
              radial-gradient(500px 300px at 0% 100%, rgba(124,196,255,.12), transparent 60%),
              linear-gradient(160deg,#133024,#0c1713);
  box-shadow: 0 24px 60px rgba(0,0,0,.4); }
.ll-hero::after { content:""; position:absolute; inset:0; pointer-events:none;
  background-image: linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px);
  background-size: 38px 38px; -webkit-mask-image: radial-gradient(ellipse at 85% 15%, #000, transparent 70%); mask-image: radial-gradient(ellipse at 85% 15%, #000, transparent 70%); }
.ll-hero > * { position:relative; z-index:1; }
.ll-hero h1 { font-size:2.7rem; line-height:1.08; margin:.35rem 0 .9rem; max-width:26ch; padding:0;
  background: linear-gradient(90deg,#ffffff,#c4f7d8 55%,#83e6aa); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
.ll-hero p { max-width:64ch; color:#b9cbc0; font-size:1.02rem; margin:0; }
.ll-eyebrow { letter-spacing:.22em; font-size:.72rem; font-weight:700; color:var(--mint); }
.ll-chips { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1.2rem; }
.ll-chip { padding:.35rem .85rem; border-radius:999px; font-size:.8rem; font-weight:600; color:#d3e6da;
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.14); backdrop-filter:blur(6px); }

.ll-flow { display:flex; align-items:center; gap:.5rem; margin:.2rem 0 1rem; flex-wrap:wrap; }
.ll-flow-step { display:flex; align-items:center; gap:.5rem; padding:.3rem .85rem .3rem .35rem; border-radius:999px;
  border:1px solid var(--line-soft); background:var(--surface); font-size:.82rem; color:var(--faint); font-weight:600; }
.ll-flow-dot { width:22px; height:22px; border-radius:50%; display:grid; place-items:center; font-size:.72rem; background:#1b2d24; color:var(--muted); }
.ll-flow-step.done { color:#bff1d2; border-color:rgba(131,230,170,.35); }
.ll-flow-step.done .ll-flow-dot { background:var(--mint); color:#06150d; }
.ll-flow-step.now { color:var(--ink-strong); border-color:var(--mint); background:var(--mint-wash);
  box-shadow:0 0 0 3px rgba(131,230,170,.08), 0 0 22px rgba(131,230,170,.18); }
.ll-flow-step.now .ll-flow-dot { background:linear-gradient(135deg,var(--mint),var(--mint-deep)); color:#06150d; }
.ll-flow-line { flex:0 0 22px; height:2px; background:linear-gradient(90deg,var(--line),var(--line-soft)); border-radius:2px; }

[data-testid="stPageLink"] a { border:1px solid var(--line); border-radius:10px; padding:.4rem .8rem; background:var(--surface-2); color:var(--mint); font-weight:600; transition:all .18s var(--ease); }
[data-testid="stPageLink"] a:hover { border-color:var(--mint); background:var(--mint-wash); transform:translateY(-1px); }
.ll-hero + div h4, h4 { letter-spacing:-.01em; }
h2 { padding-top:.4rem; }

/* Equal-height card rows: columns stretch and their (bordered) block fills the column */
[data-testid="stColumn"] { display: flex; flex-direction: column; }
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] { flex: 1 1 auto; }
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:only-child { flex: 1 1 auto; }
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:only-child > [data-testid="stVerticalBlock"] { flex: 1 1 auto; }
/* Bordered containers in recent Streamlit versions */
[data-testid="stVerticalBlock"][class*="border"], [data-testid="stVerticalBlock"][style*="border"] { border-radius: var(--radius); }

/* ---------- Responsive ---------- */
@media (max-width: 760px) {
  .block-container { padding: 1.2rem 1rem 3rem; }
  h1 { font-size: 1.6rem; }
  [data-testid="stMetricValue"] { font-size: 1.5rem; }
}
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")

navigation = st.navigation({
    "Guide": [
        st.Page("pages/start_here.py", title="Start Here", icon=":material/explore:", url_path="start", default=True),
        st.Page("pages/about.py", title="About", icon=":material/info:", url_path="about"),
    ],
    "Monitor": [
        st.Page("pages/dashboard.py", title="Overview Dashboard", icon=":material/dashboard:", url_path="overview"),
    ],
    "Audit": [
        st.Page("pages/data_import.py", title="Data Import", icon=":material/upload_file:", url_path="data-import"),
        st.Page("pages/financial_audit.py", title="Financial Audit", icon=":material/query_stats:", url_path="financial-audit"),
    ],
    "Investigate": [
        st.Page("pages/findings.py", title="Findings Explorer", icon=":material/troubleshoot:", url_path="findings"),
        st.Page("pages/transactions.py", title="Transaction Explorer", icon=":material/account_tree:", url_path="transactions"),
    ],
    "Records": [
        st.Page("pages/history.py", title="Audit History", icon=":material/history:", url_path="history"),
        st.Page("pages/reports.py", title="Reports", icon=":material/file_download:", url_path="reports"),
    ],
    "System": [
        st.Page("pages/settings.py", title="Settings", icon=":material/settings:", url_path="settings"),
    ],
})

PAGE_FILES = {
    "": "pages/start_here.py",
    "about": "pages/about.py",
    "overview": "pages/dashboard.py",
    "data-import": "pages/data_import.py",
    "financial-audit": "pages/financial_audit.py",
    "findings": "pages/findings.py",
    "transactions": "pages/transactions.py",
    "history": "pages/history.py",
    "reports": "pages/reports.py",
    "settings": "pages/settings.py",
}

current_path = navigation.url_path
page_history = st.session_state.setdefault("ll_navigation_history", [])
previous_path = st.session_state.get("ll_navigation_current")
if previous_path and previous_path != current_path:
    page_history.append(previous_path)
    del page_history[:-20]
st.session_state["ll_navigation_current"] = current_path

with st.container(horizontal=True, horizontal_alignment="distribute", gap="small", key="ll_page_navigation"):
    if st.button(
        "Back",
        key="ll_global_back",
        icon=":material/arrow_back:",
        disabled=not page_history,
    ):
        target_path = page_history.pop()
        st.session_state["ll_navigation_current"] = target_path
        st.switch_page(PAGE_FILES[target_path])
    st.page_link(PAGE_FILES[""], label="Home", icon=":material/home:")

navigation.run()
