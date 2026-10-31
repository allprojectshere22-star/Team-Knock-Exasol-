"""Build the original LeakageLens ExaThon pitch deck."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path(__file__).with_name("LeakageLens-pitch-deck.pptx")
NAVY = RGBColor(10, 20, 16)
SURFACE = RGBColor(17, 34, 25)
GREEN = RGBColor(117, 226, 164)
WHITE = RGBColor(236, 245, 238)
MUTED = RGBColor(157, 179, 165)
LINE = RGBColor(43, 69, 52)


def textbox(slide, x, y, w, h, text, size, color=WHITE, bold=False):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(0)
    frame.margin_right = Inches(0)
    frame.margin_top = Inches(0)
    frame.margin_bottom = Inches(0)
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.font.name = "Aptos"
    paragraph.font.size = Pt(size)
    paragraph.font.bold = bold
    paragraph.font.color.rgb = color
    return shape


def base_slide(presentation, number, section):
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    textbox(slide, 0.65, 0.32, 3.2, 0.35, "◈  LEAKAGELENS", 14, GREEN, True)
    textbox(slide, 9.6, 0.32, 3.0, 0.35, section.upper(), 10, MUTED, True)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.65), Inches(0.82), Inches(12.0), Inches(0.015))
    line.fill.solid()
    line.fill.fore_color.rgb = LINE
    line.line.fill.background()
    textbox(slide, 0.65, 7.1, 7.0, 0.2, "EXATHON INDIA 2026  ·  MONEY, RISK & REGULATION", 8, MUTED)
    textbox(slide, 12.0, 7.05, 0.5, 0.25, f"{number:02d}", 9, GREEN, True)
    return slide


def card(slide, x, y, w, h, heading, body, number=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = SURFACE
    shape.line.color.rgb = LINE
    if number:
        textbox(slide, x + 0.22, y + 0.14, 0.5, 0.35, number, 14 if h >= 1 else 10, GREEN, True)
        offset = 0.65
    else:
        offset = 0.22
    if h < 1:
        textbox(slide, x + offset, y + 0.08, w - offset - 0.18, 0.28, heading, 12, WHITE, True)
        textbox(slide, x + 0.22, y + 0.39, w - 0.44, 0.3, body, 9, MUTED)
    else:
        textbox(slide, x + offset, y + 0.16, w - offset - 0.18, 0.45, heading, 17, WHITE, True)
        textbox(slide, x + 0.22, y + 0.78, w - 0.44, h - 0.92, body, 12, MUTED)


def build():
    deck = Presentation()
    deck.slide_width = Inches(13.333)
    deck.slide_height = Inches(7.5)

    slide = base_slide(deck, 1, "The opportunity")
    textbox(slide, 0.85, 1.55, 10.8, 1.6, "Find the money your business\nis silently losing.", 37, WHITE, True)
    textbox(slide, 0.9, 3.55, 8.4, 0.8,
            "Evidence-led supplier payment audits, powered by Exasol SQL.", 21, GREEN)
    textbox(slide, 0.9, 5.7, 8.5, 0.55,
            "LeakageLens  |  A financial controls product for ExaThon India 2026", 14, MUTED)
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(11.0), Inches(1.65), Inches(0.12), Inches(3.7))
    accent.fill.solid()
    accent.fill.fore_color.rgb = GREEN
    accent.line.fill.background()
    textbox(slide, 11.35, 1.65, 1.2, 3.7, "INVOICES\n\nPURCHASE\nORDERS\n\nPAYMENTS\n\nCREDITS", 12, MUTED, True)

    slide = base_slide(deck, 2, "The problem")
    textbox(slide, 0.75, 1.1, 11.7, 0.75, "Small breaks in financial controls add up.", 30, WHITE, True)
    card(slide, 0.75, 2.25, 3.75, 1.65, "Duplicate payments", "Same supplier invoice settled more than once.", "01")
    card(slide, 4.8, 2.25, 3.75, 1.65, "Duplicate invoices", "Resubmissions hidden by changed references.", "02")
    card(slide, 8.85, 2.25, 3.75, 1.65, "Overbilling", "Invoice amounts drift above approved PO value.", "03")
    card(slide, 2.75, 4.35, 3.75, 1.65, "Missed credits", "Supplier adjustments fail to reach the balance.", "04")
    card(slide, 6.8, 4.35, 3.75, 1.65, "Payment mismatches", "Settled amounts do not match net payable.", "05")

    slide = base_slide(deck, 3, "The solution")
    textbox(slide, 0.75, 1.1, 11.5, 0.75, "One audit trail. Five targeted controls.", 30, WHITE, True)
    card(slide, 0.75, 2.15, 2.8, 2.0, "01  Load", "Import or generate invoices, POs, payments, and credit notes.")
    card(slide, 3.8, 2.15, 2.8, 2.0, "02  Reconcile", "Exasol SQL joins and aggregates source records at scale.")
    card(slide, 6.85, 2.15, 2.8, 2.0, "03  Explain", "Every alert links IDs, amounts, variance, and evidence.")
    card(slide, 9.9, 2.15, 2.8, 2.0, "04  Review", "Humans decide; notes and recovery stay auditable.")
    textbox(slide, 1.0, 5.0, 11.0, 0.8,
            "SQL does the reconciliation. RapidFuzz scores only SQL-filtered invoice candidates.", 18, GREEN, True)

    slide = base_slide(deck, 4, "Built for trust")
    textbox(slide, 0.75, 1.1, 11.7, 0.75, "A finding is a starting point—not a savings claim.", 28, WHITE, True)
    card(slide, 0.8, 2.15, 5.55, 1.55, "Evidence before escalation",
         "Expected vs observed values, source IDs, confidence, explanation, and next action.")
    card(slide, 6.95, 2.15, 5.55, 1.55, "No double counting",
         "Overlapping invoice cases are linked; potential exposure takes one conservative estimate per case.")
    card(slide, 0.8, 4.15, 5.55, 1.55, "Review stays human",
         "New → Under Review → Confirmed Issue / False Positive → Resolved.")
    card(slide, 6.95, 4.15, 5.55, 1.55, "Recovery stays separate",
         "Gross flagged, potential exposure, awaiting verification, and confirmed recovery are distinct.")

    slide = base_slide(deck, 5, "The product")
    textbox(slide, 0.75, 1.1, 11.7, 0.75, "From import to investigation in one workspace.", 28, WHITE, True)
    labels = [
        ("Overview", "Source counts, severity, category exposure, and priority queue."),
        ("Data Import", "Reproducible synthetic data, CSV validation, schema/load controls."),
        ("Financial Audit", "Parameterized thresholds and Exasol SQL execution."),
        ("Findings Explorer", "Search, filter, linked source records, review decisions."),
        ("Audit History + Reports", "Persisted runs, reconciliation exports, evidence bundles."),
    ]
    y = 2.05
    for index, (heading, body) in enumerate(labels, 1):
        card(slide, 1.0, y, 11.1, 0.77, heading, body, f"{index:02d}")
        y += 0.91

    slide = base_slide(deck, 6, "ExaThon India 2026")
    textbox(slide, 0.75, 1.1, 11.7, 0.75, "Financial controls, made actionable.", 30, WHITE, True)
    card(slide, 0.8, 2.2, 5.5, 1.65, "Analytical foundation",
         "Exasol Personal + SQL · Python · Streamlit · pandas · RapidFuzz · Plotly")
    card(slide, 6.9, 2.2, 5.5, 1.65, "Safe demonstration",
         "Fictional, seeded data with separate ground truth. No real customer financial data.")
    textbox(slide, 1.0, 4.45, 11.1, 0.6,
            "Next: connect and verify the target Exasol Personal instance, then record the 3-minute demo.", 17, GREEN, True)
    textbox(slide, 1.0, 5.3, 11.1, 0.55,
            "Potential exposure is an estimate pending human verification—not confirmed savings.", 13, MUTED)

    deck.save(OUT)
    print(f"Created {OUT}")


if __name__ == "__main__":
    build()
