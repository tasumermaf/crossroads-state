#!/usr/bin/env python3
"""Build the optional PDF from paper/methods.md. Requires ReportLab only."""
from html import escape
from pathlib import Path
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                               TableStyle, Preformatted, KeepTogether, HRFlowable,
                               CondPageBreak)

ROOT = Path(__file__).resolve().parents[1]
PURPLE = colors.HexColor("#4D286C")
GREEN = colors.HexColor("#256755")
INK = colors.HexColor("#20212A")
styles = getSampleStyleSheet()
styles.add(ParagraphStyle("PaperTitle", fontName="Times-Bold", fontSize=25,
                          leading=29, textColor=PURPLE, spaceAfter=12))
styles.add(ParagraphStyle("PaperSubtitle", fontName="Helvetica", fontSize=13,
                          leading=17, textColor=GREEN, spaceAfter=16))
styles.add(ParagraphStyle("PaperBody", fontName="Times-Roman", fontSize=10.8,
                          leading=14.4, textColor=INK, spaceAfter=8))
styles.add(ParagraphStyle("PaperLead", parent=styles["PaperBody"], keepWithNext=True))
styles.add(ParagraphStyle("PaperH2", fontName="Helvetica-Bold", fontSize=13,
                          leading=17, textColor=PURPLE, spaceBefore=18,
                          spaceAfter=8, keepWithNext=True))
styles.add(ParagraphStyle("PaperH3", fontName="Helvetica-Bold", fontSize=10.5,
                          leading=14, textColor=GREEN, spaceBefore=10,
                          spaceAfter=5, keepWithNext=True))
styles.add(ParagraphStyle("PaperCell", fontName="Helvetica", fontSize=8.4,
                          leading=11, textColor=INK))
styles.add(ParagraphStyle("PaperCode", fontName="Courier", fontSize=8.3,
                          leading=11.5, textColor=GREEN, leftIndent=12,
                          spaceAfter=10, spaceBefore=4))
styles.add(ParagraphStyle("PaperRef", fontName="Times-Roman", fontSize=8.4,
                          leading=11, textColor=INK, spaceAfter=10,
                          splitLongWords=True))


def inline(text):
    text = escape(text)
    return re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)


def footer(canvas, doc):
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setStrokeColor(colors.HexColor("#D9D0DF"))
    canvas.line(0.8*inch, 0.62*inch, width-0.8*inch, 0.62*inch)
    canvas.setFillColor(PURPLE)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(0.8*inch, 0.43*inch, "TASUMER MAF  |  EXACT STATE / PARTIAL OBSERVATION / REVERSIBLE RECOVERY")
    canvas.drawRightString(width-0.8*inch, 0.43*inch, str(doc.page))
    canvas.restoreState()


def build():
    lines = (ROOT / "paper" / "methods.md").read_text().splitlines()
    story, i, in_refs = [], 0, False
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("# "):
            story += [Paragraph(inline(line[2:]), styles["PaperTitle"])]
            i += 1
        elif line.startswith("## "):
            title = line[3:]
            if title.startswith("8. "):
                story.append(CondPageBreak(2.6*inch))
            if title == "A reproducible synthetic test environment":
                style = styles["PaperSubtitle"]
            else:
                style = styles["PaperH2"]
            in_refs = title == "References"
            story.append(Paragraph(inline(title), style))
            i += 1
        elif line.startswith("### "):
            if line.startswith("### 3.3 "):
                story.append(CondPageBreak(2.0*inch))
            story.append(Paragraph(inline(line[4:]), styles["PaperH3"]))
            i += 1
        elif line.startswith("    "):
            block = []
            while i < len(lines) and lines[i].startswith("    "):
                block.append(lines[i][4:])
                i += 1
            code = Preformatted("\n".join(block), styles["PaperCode"], maxLineLength=90)
            box = Table([[code]], colWidths=[5.05*inch], hAlign="LEFT")
            box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F7F5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBEFORE", (0, 0), (0, -1), 1.2, GREEN),
            ]))
            story.extend([KeepTogether([box]), Spacer(1, 8)])
        elif line.startswith("| "):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [x.strip() for x in lines[i].strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+", c) for c in cells):
                    rows.append([Paragraph(inline(c), styles["PaperCell"]) for c in cells])
                i += 1
            widths = [3.6*inch, 1.45*inch] if len(rows[0]) == 2 else [0.55*inch, 2.0*inch, 2.5*inch]
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9E1EE")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7F5")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, PURPLE),
                ("LINEBELOW", (0, -1), (-1, -1), 0.4, GREEN),
            ]))
            story += [KeepTogether([table]), Spacer(1, 10)]
        else:
            if re.match(r"^\d+\. ", line):
                story.append(Paragraph(inline(line), styles["PaperBody"]))
                i += 1
                continue
            paragraph = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "    ")) and not re.match(r"^\d+\. ", lines[i]):
                paragraph.append(lines[i].strip())
                i += 1
            text = " ".join(paragraph)
            stylename = "PaperRef" if in_refs else "PaperLead" if (text.endswith(":") or text.endswith(" is")) else "PaperBody"
            story.append(Paragraph(inline(text), styles[stylename]))
    target = ROOT / "paper" / "exact-state-recovery.pdf"
    doc = SimpleDocTemplate(str(target), pagesize=(612, 792),
                            rightMargin=0.86*inch, leftMargin=0.86*inch,
                            topMargin=0.66*inch, bottomMargin=1.05*inch,
                            title="Exact State, Partial Observation, and Reversible Recovery",
                            author="TASUMER MAF", subject="Synthetic exact-state methods and reproducibility")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(target.name)


if __name__ == "__main__":
    build()
