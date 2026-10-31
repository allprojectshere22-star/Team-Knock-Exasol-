import os
from datetime import datetime

import streamlit as st

from src.ui import PAGES, ensure_state

ensure_state()

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "").strip()

st.markdown(
    """
    <style>
    .ab-section { margin:2.6rem 0 1rem; }
    .ab-kicker { letter-spacing:.2em; font-size:.7rem; font-weight:700; color:var(--mint); }
    .ab-title { font-size:1.9rem; font-weight:700; letter-spacing:-.03em; color:var(--ink-strong); margin:.2rem 0 0; line-height:1.15; }
    .ab-sub { color:var(--muted); margin:.4rem 0 0; max-width:60ch; }
    .ab-stat { text-align:center; padding:1.2rem .6rem; border:1px solid var(--line); border-radius:16px;
      background:linear-gradient(150deg,var(--surface-2),var(--surface)); box-shadow:var(--shadow); }
    .ab-stat b { display:block; font-size:2.4rem; letter-spacing:-.03em; line-height:1.05;
      background:linear-gradient(90deg,#fff,#83e6aa); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
    .ab-stat span { color:var(--muted); font-size:.82rem; letter-spacing:.04em; }
    .ab-icon { width:48px; height:48px; border-radius:14px; display:grid; place-items:center; font-size:1.5rem; margin-bottom:.7rem;
      background:linear-gradient(145deg, rgba(131,230,170,.22), rgba(131,230,170,.05)); border:1px solid rgba(131,230,170,.28); }
    .ab-card-title { font-weight:650; font-size:1.08rem; color:var(--ink-strong); margin-bottom:.3rem; }
    .ab-card-text { color:var(--muted); font-size:.92rem; line-height:1.5; }
    .ab-line { display:flex; gap:.55rem; align-items:flex-start; color:#cfe3d6; font-size:.9rem; margin:.25rem 0; }
    .ab-line::before { content:"✓"; color:var(--mint); font-weight:700; }
    .ab-tl { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; position:relative; }
    .ab-tl-item { position:relative; padding-top:2.6rem; }
    .ab-tl-item::before { content:""; position:absolute; top:.85rem; left:1.6rem; right:-1rem; height:2px; background:linear-gradient(90deg,var(--mint),var(--line)); }
    .ab-tl-item:last-child::before { display:none; }
    .ab-tl-dot { position:absolute; top:0; left:0; width:30px; height:30px; border-radius:50%; display:grid; place-items:center; font-weight:700;
      color:#06150d; background:linear-gradient(135deg,var(--mint),var(--mint-deep)); box-shadow:0 0 18px rgba(131,230,170,.35); }
    .ab-badges { display:flex; flex-wrap:wrap; gap:.55rem; margin-top:.8rem; }
    .ab-badge { padding:.4rem .9rem; border-radius:999px; font-weight:600; font-size:.85rem; color:#d3e6da;
      background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.12); }
    .ab-badge.opt { border-style:dashed; color:var(--muted); }
    .ab-cta { position:relative; overflow:hidden; text-align:center; border-radius:22px; padding:2.6rem 1.5rem; margin-top:2.8rem; border:1px solid var(--line);
      background:radial-gradient(520px 220px at 50% 0%, rgba(131,230,170,.26), transparent 70%), linear-gradient(160deg,#133024,#0c1713); }
    .ab-cta h2 { margin:0 0 .4rem; font-size:2rem; }
    .ab-cta p { color:#b9cbc0; margin:0; }
    .ab-foot { text-align:center; color:var(--faint); font-size:.8rem; margin:2.2rem 0 .5rem; padding-top:1.2rem; border-top:1px solid var(--line-soft); }
    @media (max-width:900px){ .ab-tl{grid-template-columns:1fr 1fr;} .ab-tl-item::before{display:none;} }
    </style>
    """,
    unsafe_allow_html=True,
)


PAD = '<div style="height:.9rem"></div>'


def section(kicker: str, title: str, sub: str = "") -> None:
    sub_html = f'<p class="ab-sub">{sub}</p>' if sub else ""
    st.markdown(f'<div class="ab-section"><div class="ab-kicker">{kicker}</div><div class="ab-title">{title}</div>{sub_html}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ Hero
st.markdown(
    """
    <div class="ll-hero">
      <div class="ll-eyebrow">ABOUT LEAKAGELENS</div>
      <h1>Making every supplier payment accountable.</h1>
      <p>LeakageLens helps finance teams spot duplicate, excess and missed payments &mdash; and gives people the evidence they need to act on them.</p>
      <div class="ll-chips">
        <span class="ll-chip">Built for finance teams</span><span class="ll-chip">Human-in-the-loop</span><span class="ll-chip">Private by default</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ Numbers
stats = [("8", "Automated checks"), ("5", "Datasets compared"), ("4", "Steps from CSV to report"), ("0", "Records sent anywhere by default")]
for col, (num, label) in zip(st.columns(4), stats):
    col.markdown(f'<div class="ab-stat"><b>{num}</b><span>{label}</span></div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ Mission
section("OUR MISSION", "Money leaks quietly. We make it visible.",
        "Invoices, purchase orders, payments and credits live in different places. Leaks hide in the gaps between them.")
m1, m2, m3 = st.columns(3)
pillars = [
    ("🔍", "Detect", "Cross-checks every record against the others.", ["Duplicate invoices & payments", "Overpayments & PO overruns", "Credits that were never used"]),
    ("💡", "Explain", "Every finding says why it was raised.", ["Plain-English reason", "The exact calculation", "Links to the source records"]),
    ("🗂️", "Document", "Decisions are recorded, not lost in email.", ["Review status & notes", "CSV findings list", "JSON evidence pack"]),
]
for col, (icon, title, text, lines) in zip((m1, m2, m3), pillars):
    with col, st.container(border=True):
        bullets = "".join(f'<div class="ab-line">{l}</div>' for l in lines)
        st.markdown(f'<div class="ab-icon">{icon}</div><div class="ab-card-title">{title}</div><div class="ab-card-text">{text}</div><div style="margin-top:.7rem">{bullets}</div>{PAD}', unsafe_allow_html=True)

# ------------------------------------------------------------------ Process
section("HOW WE WORK", "From messy CSVs to an audit-ready report in four steps")
steps = [("1", "Import", "Upload five kinds of CSV. Bad rows are rejected with a reason."),
         ("2", "Audit", "Eight checks run in one click, locally or in Exasol."),
         ("3", "Review", "Open each finding, see the evidence, record a decision."),
         ("4", "Report", "Export the results to share with finance or auditors.")]
items = "".join(f'<div class="ab-tl-item"><div class="ab-tl-dot">{n}</div><div class="ab-card-title">{t}</div><div class="ab-card-text">{d}</div></div>' for n, t, d in steps)
st.markdown(f'<div class="ab-tl">{items}</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ Principles
section("PRINCIPLES", "What we stand for")
principles = [
    ("🧾", "Evidence first", "No finding without the records behind it."),
    ("🧑‍⚖️", "People decide", "The tool flags. A human confirms."),
    ("🔒", "Private by default", "Data stays in your session unless you choose a database."),
    ("📏", "Honest numbers", "Gross and unique exposure are kept apart. Nothing is called “saved” until confirmed."),
]
for col, (icon, title, text) in zip(st.columns(4), principles):
    with col, st.container(border=True):
        st.markdown(f'<div class="ab-icon">{icon}</div><div class="ab-card-title">{title}</div><div class="ab-card-text">{text}</div>{PAD}', unsafe_allow_html=True)

# ------------------------------------------------------------------ Audience
section("WHO IT'S FOR", "Made for the people who guard the payables process")
people = [
    ("Accounts payable", "Catch duplicates before they are paid, or chase them after."),
    ("Internal audit", "Get a repeatable, documented review of supplier payments."),
    ("Procurement", "See where invoices run past approved purchase orders."),
    ("Finance controllers", "Quantify exposure and track what was reviewed."),
]
for col, (title, text) in zip(st.columns(4), people):
    with col, st.container(border=True):
        st.markdown(f'<div class="ab-card-title">{title}</div><div class="ab-card-text">{text}</div>{PAD}', unsafe_allow_html=True)

# ------------------------------------------------------------------ Tech
section("UNDER THE HOOD", "Open, boring, reliable technology")
st.markdown(
    '<div class="ab-badges"><span class="ab-badge">Python</span><span class="ab-badge">Streamlit</span><span class="ab-badge">pandas</span>'
    '<span class="ab-badge">RapidFuzz</span><span class="ab-badge">Plotly</span><span class="ab-badge opt">Exasol (optional)</span></div>',
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ Honest note + FAQ
st.write("")
st.info("**Good to know:** findings are review candidates, not proof of loss or fraud. Always verify against the original documents before recovering money.",
        icon=":material/verified_user:")
section("QUESTIONS", "Frequently asked")
with st.expander("Is my data stored somewhere?"):
    st.write("Not by default. Records live in your browser session and disappear when it ends. Data goes to a database only if you explicitly load it to Exasol.")
with st.expander("Do I need a database?"):
    st.write("No. The same checks run locally in Python. Exasol mode runs them as SQL for larger datasets.")
with st.expander("How accurate are the findings?"):
    st.write("Each finding carries a confidence score, which is a heuristic rather than a probability. Some checks are review-only and never counted as recoverable money.")
with st.expander("What file format do you accept?"):
    st.write("CSV, up to 10 MB per file. The Start Here page has downloadable templates for every dataset.")

# ------------------------------------------------------------------ CTA
contact = (f'Questions? Write to <b>{CONTACT_EMAIL}</b>.' if CONTACT_EMAIL
           else "Questions? Reach out to the team that shared LeakageLens with you.")
st.markdown(
    f'<div class="ab-cta"><h2>Ready to see where your money goes?</h2><p>Load the demo data and run your first audit in under a minute.</p>'
    f'<p style="margin-top:.8rem;font-size:.9rem">{contact}</p></div>',
    unsafe_allow_html=True,
)
st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([1, 1.2, 1.2, 1])
c2.page_link(PAGES["start"][0], label="Take the guided tour", icon=PAGES["start"][2])
c3.page_link(PAGES["import"][0], label="Import your data", icon=PAGES["import"][2])

st.markdown(f'<div class="ab-foot">© {datetime.now().year} LeakageLens · Financial control intelligence · Built with Python &amp; Streamlit</div>', unsafe_allow_html=True)
