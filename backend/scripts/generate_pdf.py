"""
Professional Technical Design Document PDF Generator for ShortlistAI.
Reads docs/submission/technical-design-document.md and compiles a beautifully
typeset, publication-grade PDF using ReportLab with headers, footers, tables, and code formatting.
"""
from __future__ import annotations

import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Preformatted
)
from reportlab.pdfgen import canvas

MD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "submission", "technical-design-document.md"))
PDF_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "submission", "technical-design-document.pdf"))


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header (Pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, letter[1] - 36, "ShortlistAI — Technical Design Document (v1.0 Production Candidate)")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

        # Footer (All pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 45, letter[0] - 54, 45)
        self.drawString(54, 32, "Confidential — For Technical Evaluation & Hiring Assessment Only")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 32, page_str)
        self.restoreState()


def compile_pdf():
    print(f"Reading markdown from: {MD_PATH}")
    with open(MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#475569"),
        spaceAfter=18,
    )
    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )
    h3_style = ParagraphStyle(
        "H3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3,
    )
    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f8fafc"),
        borderPadding=6,
        spaceAfter=8,
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    story = []

    lines = content.split("\n")
    i = 0
    in_code = False
    code_buffer = []

    while i < len(lines):
        line = lines[i]

        # Fenced code block toggle
        if line.strip().startswith("```"):
            if in_code:
                # Flush code block
                code_text = "\n".join(code_buffer)
                story.append(Preformatted(code_text, code_style))
                story.append(Spacer(1, 4))
                code_buffer = []
                in_code = False
            else:
                in_code = True
                code_buffer = []
            i += 1
            continue

        if in_code:
            code_buffer.append(line)
            i += 1
            continue

        # Markdown tables
        if line.strip().startswith("|") and line.strip().endswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            # Parse markdown table
            parsed_rows = []
            for r_idx, t_line in enumerate(table_lines):
                if re.match(r"^\|(\s*[-:]+[-|\s:]*)\|$", t_line):
                    continue  # Separator row
                raw_cells = [c.strip() for c in t_line.split("|")[1:-1]]
                row_cells = []
                for c in raw_cells:
                    # Clean markdown formatting inside cell
                    clean_c = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", c)
                    style = table_header_style if len(parsed_rows) == 0 else table_cell_style
                    row_cells.append(Paragraph(clean_c, style))
                if row_cells:
                    parsed_rows.append(row_cells)

            if parsed_rows:
                # Table column widths
                col_count = len(parsed_rows[0])
                available_width = letter[0] - 108
                col_width = available_width / col_count

                tbl = Table(parsed_rows, colWidths=[col_width] * col_count)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 6))
            continue

        # Title
        if line.startswith("# ") and not line.startswith("## "):
            text = line[2:].strip()
            story.append(Paragraph(text, title_style))
            i += 1
            continue

        # Subtitle metadata
        if line.startswith("**System Name:**") or line.startswith("**Document Version:**"):
            clean = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line)
            story.append(Paragraph(clean, subtitle_style))
            i += 1
            continue

        # Headings
        if line.startswith("## "):
            text = line[3:].strip()
            story.append(Paragraph(text, h1_style))
            i += 1
            continue

        if line.startswith("### "):
            text = line[4:].strip()
            story.append(Paragraph(text, h2_style))
            i += 1
            continue

        if line.startswith("#### "):
            text = line[5:].strip()
            story.append(Paragraph(text, h3_style))
            i += 1
            continue

        # Horizontal rule
        if line.strip() == "---":
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Bullet points
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            bullet_text = line.strip()[2:]
            bullet_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", bullet_text)
            bullet_text = re.sub(r"`(.*?)`", r"<font name='Courier'>\1</font>", bullet_text)
            story.append(Paragraph(f"• {bullet_text}", bullet_style))
            i += 1
            continue

        # Numbered list
        num_match = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if num_match:
            num = num_match.group(1)
            item_text = num_match.group(2)
            item_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", item_text)
            item_text = re.sub(r"`(.*?)`", r"<font name='Courier'>\1</font>", item_text)
            story.append(Paragraph(f"<b>{num}.</b> {item_text}", bullet_style))
            i += 1
            continue

        # Paragraph text
        if line.strip():
            p_text = line.strip()
            p_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", p_text)
            p_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", p_text)
            p_text = re.sub(r"`(.*?)`", r"<font name='Courier'>\1</font>", p_text)
            story.append(Paragraph(p_text, body_style))
        else:
            story.append(Spacer(1, 3))

        i += 1

    print(f"Building PDF document with {len(story)} flowable elements...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] PDF successfully created: {PDF_PATH} ({os.path.getsize(PDF_PATH)} bytes)")


if __name__ == "__main__":
    compile_pdf()

