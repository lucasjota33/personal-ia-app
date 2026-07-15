import re
from fpdf import FPDF
from typing import List


def _normalize_text(text: str) -> str:
    if text is None:
        return ""
    replacements = {
        '"': '',
        '**': '',
        '\r': '',
        '\u2013': '-',
        '\u2014': '-',
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u2022': '-',
        '\u2026': '...',
        '\u00a0': ' ',
        '\u200b': ''
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()


def _to_printable(text: str) -> str:
    return _normalize_text(text).encode("latin-1", "ignore").decode("latin-1")


class PDF_Elite(FPDF):
    def __init__(self, profile_name: str):
        super().__init__()
        self.profile_name = profile_name

    def header(self):
        self.set_fill_color(22, 22, 22)
        self.rect(0, 0, 210, 24, 'F')
        self.set_x(10)
        self.set_font("Arial", "B", 13)
        self.set_text_color(255, 255, 255)
        self.cell(0, 14, "HALTER AI - PLANEJAMENTO", 0, 0, "L")
        self.cell(0, 14, f"PERFIL: {self.profile_name.upper()}", 0, 1, "R")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")


def gerar_pdf(markdown_text: str, profile_name: str) -> bytes:
    content = re.sub(r'```json\n.*?\n```', '', markdown_text, flags=re.DOTALL)
    pdf = PDF_Elite(profile_name)
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()

    lines = content.split("\n")
    table_buffer: List[str] = []
    in_table = False

    def draw_table(rows: List[str]) -> None:
        if len(rows) < 2:
            return
        headers = [cell.strip() for cell in rows[0].strip("|").split("|")]
        column_count = len(headers)
        column_width = 190 / max(column_count, 1)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(35, 35, 35)
        pdf.set_text_color(255, 255, 255)
        for header in headers:
            pdf.cell(column_width, 8, _to_printable(header), 1, 0, "C", True)
        pdf.ln()
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(40, 40, 40)

        for row in rows[1:]:
            if re.match(r'^[\s\|\-\:]+$', row):
                continue
            values = [cell.strip() for cell in row.strip("|").split("|")]
            values = values[:column_count] + [""] * max(0, column_count - len(values))
            fill = False
            for value in values:
                pdf.set_fill_color(248, 248, 248 if fill else 255)
                pdf.cell(column_width, 7, _to_printable(value), 1, 0, "L", True)
                fill = not fill
            pdf.ln()
        pdf.ln(4)

    for line in lines:
        cleaned = line.strip()
        if cleaned.startswith("|") and cleaned.count("|") >= 2:
            table_buffer.append(cleaned)
            in_table = True
            continue

        if in_table and table_buffer:
            draw_table(table_buffer)
            table_buffer = []
            in_table = False

        if not cleaned:
            pdf.ln(2)
            continue

        if cleaned.startswith("## "):
            pdf.set_font("Arial", "B", 13)
            pdf.set_text_color(20, 20, 20)
            pdf.cell(0, 8, _to_printable(cleaned.replace("## ", "")), 0, 1)
            pdf.ln(2)
        elif cleaned.startswith("### "):
            pdf.set_font("Arial", "B", 11)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 7, _to_printable(cleaned.replace("### ", "")), 0, 1)
            pdf.ln(1)
        else:
            pdf.set_font("Arial", "", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 6, _to_printable(cleaned))

    if table_buffer:
        draw_table(table_buffer)

    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode("latin-1", "ignore")
    return bytes(output)
