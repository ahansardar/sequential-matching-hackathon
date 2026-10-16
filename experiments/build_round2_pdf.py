"""Build the reviewer PDF deterministically from ROUND2_SUBMISSION.md."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/ahansardar/sequential-matching-hackathon"
RELEASE_REF = "round2-final-v2"
LINK = re.compile(r"\[([^]]+)]\(([^)]+)\)")
CODE = re.compile(r"`([^`]+)`")


def _inline(text: str) -> str:
    """Convert the small inline-Markdown subset used by the report."""
    tokens: list[str] = []

    def hold(value: str) -> str:
        tokens.append(value)
        return f"@@TOKEN{len(tokens) - 1}@@"

    text = LINK.sub(
        lambda match: hold(
            '<link href="{}" color="#175A7A">{}</link>'.format(
                escape(
                    match.group(2)
                    if re.match(r"https?://", match.group(2))
                    else f"{REPOSITORY}/blob/{RELEASE_REF}/{match.group(2)}"
                ),
                escape(match.group(1).strip("`")),
            )
        ),
        text,
    )
    text = CODE.sub(
        lambda match: hold(f'<font name="Courier">{escape(match.group(1))}</font>'),
        text,
    )
    text = escape(text)
    for index, value in enumerate(tokens):
        text = text.replace(f"@@TOKEN{index}@@", value)
    return text


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=22,
            textColor=colors.HexColor("#173B4D"),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#175A7A"),
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=11,
            textColor=colors.HexColor("#173B4D"),
            spaceBefore=5,
            spaceAfter=2,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.4,
            textColor=colors.HexColor("#20282D"),
            spaceAfter=3.3,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.1,
            leading=10.1,
            leftIndent=10,
            firstLineIndent=0,
            spaceAfter=1.8,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=6.4,
            leading=8.0,
            leftIndent=5,
            rightIndent=5,
            borderColor=colors.HexColor("#D7E1E5"),
            borderWidth=0.5,
            borderPadding=5,
            backColor=colors.HexColor("#F5F8F9"),
            spaceAfter=5,
        ),
        "table": ParagraphStyle(
            "TableText",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=6.8,
            leading=8.0,
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=8.0,
            textColor=colors.white,
        ),
    }


def _table(lines: list[str], style: dict, width: float) -> Table:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    rows.pop(1)
    data = []
    for row_index, row in enumerate(rows):
        cell_style = style["table_head"] if row_index == 0 else style["table"]
        data.append([Paragraph(_inline(cell), cell_style) for cell in row])
    column_count = len(data[0])
    if column_count == 2:
        widths = [width * 0.31, width * 0.69]
    elif column_count >= 5:
        widths = [width * 0.25] + [width * 0.75 / (column_count - 1)] * (column_count - 1)
    else:
        widths = [width / column_count] * column_count
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#175A7A")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C6CC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7F8")]),
    ]))
    return table


def _story(markdown: str, styles: dict, width: float) -> list:
    lines = markdown.splitlines()
    story: list = []
    index = 0
    paragraph: list[str] = []

    def flush_paragraph():
        if paragraph:
            story.append(Paragraph(_inline(" ".join(paragraph)), styles["body"]))
            paragraph.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        if line.startswith("```"):
            flush_paragraph()
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(escape(lines[index]))
                index += 1
            story.append(Paragraph("<br/>".join(code_lines), styles["code"]))
        elif line.startswith("| ") and index + 1 < len(lines) and re.match(r"^\|[-: |]+\|$", lines[index + 1]):
            flush_paragraph()
            table_lines = [line, lines[index + 1]]
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.append(_table(table_lines, styles, width))
            story.append(Spacer(1, 4))
            continue
        elif line.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[2:]), styles["title"]))
        elif line.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[3:]), styles["h2"]))
        elif line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[4:]), styles["h3"]))
        elif re.match(r"^(?:- |\d+\. )", line):
            flush_paragraph()
            item_text = re.sub(r"^(?:- |\d+\. )", "", line)
            story.append(Paragraph("-&nbsp; " + _inline(item_text), styles["bullet"]))
        elif not line:
            flush_paragraph()
        else:
            paragraph.append(line)
        index += 1
    flush_paragraph()
    return story


def build_pdf(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=15 * mm,
        title="LuminaX Round 2 final report",
        author="Team LuminaX",
        subject="Sequential reciprocal matching policy and public evidence",
        invariant=1,
    )
    styles = _styles()

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D7E1E5"))
        canvas.line(16 * mm, 12 * mm, A4[0] - 16 * mm, 12 * mm)
        canvas.setFont("Helvetica", 6.8)
        canvas.setFillColor(colors.HexColor("#65757C"))
        canvas.drawString(16 * mm, 8.5 * mm, "LuminaX | Round 2 | observable-only evidence")
        canvas.drawRightString(A4[0] - 16 * mm, 8.5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(_story(source.read_text(encoding="utf-8"), styles, document.width), onFirstPage=decorate, onLaterPages=decorate)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "ROUND2_SUBMISSION.md")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "output" / "pdf" / "LuminaX_Round2_Final_Report.pdf",
    )
    args = parser.parse_args()
    build_pdf(args.source, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
