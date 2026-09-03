"""Export a Research Brief evaluation JSON file into a comprehensive, readable PDF."""
import argparse
import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


def safe(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


def render_markdown_prose(text: str, styles: dict) -> list:
    elements = []
    lines = text.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            elements.append(Spacer(1, 3))
            continue
        if stripped.startswith("# "):
            elements.append(Paragraph(safe(stripped[2:]), styles["BriefTitle"]))
        elif stripped.startswith("## "):
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(safe(stripped[3:]), styles["BriefSection"]))
        elif stripped.startswith("### "):
            elements.append(Spacer(1, 3))
            elements.append(Paragraph(safe(stripped[4:]), styles["BriefSubSection"]))
        elif stripped.startswith("- "):
            elements.append(Paragraph(f"• {safe(stripped[2:])}", styles["BriefBullet"]))
        else:
            elements.append(Paragraph(safe(stripped), styles["BriefBody"]))
    return elements


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.input.with_suffix(".pdf")
    report = json.loads(args.input.read_text(encoding="utf-8"))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DocTitle", parent=styles["Title"], fontSize=16, leading=20, textColor=HexColor("#1A365D"), spaceAfter=6))
    styles.add(ParagraphStyle(name="MetaStyle", parent=styles["Normal"], fontSize=8, leading=10, textColor=HexColor("#4A5568"), spaceAfter=10))
    styles.add(ParagraphStyle(name="CaseHeader", parent=styles["Heading2"], fontSize=12, leading=14, textColor=HexColor("#2B6CB0"), spaceBefore=6, spaceAfter=4))
    styles.add(ParagraphStyle(name="SubHeader", parent=styles["Heading3"], fontSize=9.5, leading=12, textColor=HexColor("#2D3748"), spaceBefore=4, spaceAfter=2))
    styles.add(ParagraphStyle(name="BriefTitle", parent=styles["Normal"], fontSize=11, leading=14, fontName="Helvetica-Bold", textColor=HexColor("#1A202C"), spaceAfter=4))
    styles.add(ParagraphStyle(name="BriefSection", parent=styles["Normal"], fontSize=9, leading=12, fontName="Helvetica-Bold", textColor=HexColor("#2C5282"), spaceBefore=4, spaceAfter=2))
    styles.add(ParagraphStyle(name="BriefSubSection", parent=styles["Normal"], fontSize=8.5, leading=11, fontName="Helvetica-Bold", textColor=HexColor("#4A5568"), spaceBefore=3, spaceAfter=1))
    styles.add(ParagraphStyle(name="BriefBody", parent=styles["Normal"], fontSize=8, leading=10.5, textColor=HexColor("#1A202C"), spaceAfter=3))
    styles.add(ParagraphStyle(name="BriefBullet", parent=styles["Normal"], fontSize=8, leading=10.5, leftIndent=10, textColor=HexColor("#2D3748"), spaceAfter=2.5))
    styles.add(ParagraphStyle(name="MetaBox", parent=styles["Normal"], fontSize=7.5, leading=9.5, textColor=HexColor("#4A5568"), spaceAfter=4))

    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    story = [
        Paragraph("Research Brief Agent — Supervisor Brief Evaluation", styles["DocTitle"]),
        Paragraph(safe(json.dumps(report["metadata"], indent=2)), styles["MetaStyle"]),
        Spacer(1, 4),
    ]

    for index, row in enumerate(report["results"], 1):
        story.append(Paragraph(f"Case {index}: {row['id']} — Category: {row['category'].upper()}", styles["CaseHeader"]))
        
        story.append(Paragraph("Clarified User Request & Context", styles["SubHeader"]))
        story.append(Paragraph(safe(json.dumps(row["input"], indent=2)), styles["MetaBox"]))
        
        story.append(Paragraph("Generated Research Brief", styles["SubHeader"]))
        if row.get("generated_research_brief"):
            story.extend(render_markdown_prose(row["generated_research_brief"], styles))
        else:
            story.append(Paragraph("None", styles["BriefBody"]))
        
        story.append(Spacer(1, 4))
        story.append(Paragraph("Agent Self-Evaluation", styles["SubHeader"]))
        if row.get("self_evaluation"):
            story.extend(render_markdown_prose(row["self_evaluation"], styles))
        else:
            story.append(Paragraph("None", styles["BriefBody"]))

        story.append(Spacer(1, 4))
        story.append(Paragraph("Evaluation Score & Heuristic Reasoning", styles["SubHeader"]))
        story.append(Paragraph(safe(json.dumps(row["score"], indent=2)), styles["MetaBox"]))

        if index < len(report["results"]):
            story.append(PageBreak())

    doc.build(story)
    print(output)


if __name__ == "__main__":
    main()

