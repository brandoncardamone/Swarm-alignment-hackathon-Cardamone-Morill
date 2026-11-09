"""Convert report/paper_final.md to a formatted Word file (report/paper_final.docx) with embedded figures.

Handles the subset of Markdown the paper uses: headings, paragraphs, **bold** / *italic*, bullet and numbered
lists (one nesting level), pipe tables, images and block quotes."""
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from swarm_oversight.config import ROOT

SRC = ROOT / "report" / "paper_final.md"
OUT = ROOT / "report" / "paper_final.docx"
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")


def add_runs(par, text, size=None, bold_all=False):
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            r = par.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            r = par.add_run(part[1:-1])
            r.italic = True
        elif part.startswith("`") and part.endswith("`"):
            r = par.add_run(part[1:-1])
            r.font.name = "Consolas"
        else:
            r = par.add_run(part)
        if bold_all:
            r.bold = True
        if size:
            r.font.size = Pt(size)


def shade(cell, hex_fill):
    tc = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hex_fill)
    tc.append(sh)


def add_table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, body = cells[0], [r for r in cells[2:]]
    t = doc.add_table(rows=1 + len(body), cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(header):
        c = t.rows[0].cells[j]
        c.text = ""
        add_runs(c.paragraphs[0], h, size=8, bold_all=True)
        shade(c, "F1F0EC")
    for i, r in enumerate(body, start=1):
        for j, v in enumerate(r[: len(header)]):
            c = t.rows[i].cells[j]
            c.text = ""
            add_runs(c.paragraphs[0], v, size=8)
    doc.add_paragraph()


def main():
    lines = SRC.read_text().splitlines()
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(0.9)
        s.top_margin = s.bottom_margin = Inches(0.8)
    i, first_h1 = 0, True
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or ln.strip() == "---":
            i += 1
            continue
        if ln.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            add_table(doc, block)
            continue
        m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", ln.strip())
        if m:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(ROOT / "report" / m.group(1)), width=Inches(6.4))
            i += 1
            continue
        if ln.startswith("#"):
            level = len(ln) - len(ln.lstrip("#"))
            text = ln.lstrip("#").strip()
            if level == 1 and first_h1:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                add_runs(p, text, size=17, bold_all=True)
                first_h1 = False
            else:
                h = doc.add_heading(level=min(level, 3))
                add_runs(h, text)
                for r in h.runs:
                    r.font.color.rgb = RGBColor(0x0B, 0x0B, 0x0B)
            i += 1
            continue
        if ln.startswith(">"):
            p = doc.add_paragraph(style="Intense Quote")
            add_runs(p, ln.lstrip("> ").strip())
            i += 1
            continue
        bm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", ln)
        if bm:
            indent = len(bm.group(1)) >= 2
            numbered = bm.group(2)[0].isdigit()
            style = ("List Number 2" if indent else "List Number") if numbered else (
                "List Bullet 2" if indent else "List Bullet")
            text = bm.group(3)
            i += 1
            while i < len(lines) and lines[i].startswith("    ") and not re.match(r"^\s*([-*]|\d+\.)\s", lines[i]):
                text += " " + lines[i].strip()
                i += 1
            p = doc.add_paragraph(style=style)
            add_runs(p, text)
            continue
        text = ln.strip()
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||!\[|>|\s*([-*]|\d+\.)\s|---)", lines[i]):
            text += " " + lines[i].strip()
            i += 1
        p = doc.add_paragraph()
        centered = text.startswith("**") and ("Independent" in text or "Morrill" in text or "Apart" in text) or \
            text in ("With",) or text.startswith("*Research conducted")
        if centered:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        small = text.startswith("**Figure") or text.startswith("**Table")
        add_runs(p, text, size=9 if small else None)
    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    sys.exit(main())
