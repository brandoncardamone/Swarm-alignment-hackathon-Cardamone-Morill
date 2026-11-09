"""Fill the official Apart template (.docx) with report/paper_final.md, keeping the template's own styles.

Usage: python scripts/fill_apart_template.py <template.docx> <output.docx>
The template file is never modified; a new file is written."""
import copy
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from swarm_oversight.config import ROOT

SRC = ROOT / "report" / "paper_final.md"
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")


def add_runs(par, text, size=None, bold_all=False, italic_all=False):
    for part in INLINE.split(text):
        if not part:
            continue
        b = i = False
        if part.startswith("**") and part.endswith("**"):
            part, b = part[2:-2], True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, i = part[1:-1], True
        elif part.startswith("`") and part.endswith("`"):
            part = part[1:-1]
        r = par.add_run(part)
        r.bold = b or bold_all or None
        r.italic = i or italic_all or None
        if size:
            r.font.size = Pt(size)
    return par


def set_cell_text(cell, lines, bold_first=False):
    """Replace a cell's content with lines separated by line breaks, keeping the first paragraph's style."""
    p = cell.paragraphs[0]
    for extra in cell.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    for k, ln in enumerate(lines):
        r = p.add_run(ln)
        if bold_first and k == 0:
            r.bold = True
        if k < len(lines) - 1:
            r.add_break()


def borders(table):
    tbl = table._tbl
    pr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "BFBEB8")
        b.append(e)
    pr.append(b)


def shade(cell, fill):
    pr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), fill)
    pr.append(sh)


def parse_front(md):
    title = re.search(r"^# (.+)$", md, re.M).group(1).strip()
    a = md.index("## Abstract") + len("## Abstract")
    b = md.index("---", a)
    abstract = " ".join(md[a:b].split())
    body = md[md.index("## 1. Introduction"):]
    return title, abstract, body


def main(template, out):
    md = SRC.read_text()
    title, abstract, body = parse_front(md)
    doc = Document(template)

    # --- header table: title, authors, abstract
    head = doc.tables[0]
    tcell = head.rows[0].cells[0]
    tp = next(p for p in tcell.paragraphs if p.text.strip() == "PROJECT TITLE")
    runs = tp.runs
    runs[0].text = title
    for r in runs[1:]:
        r.text = ""
    acell = head.rows[1].cells[0]
    outer = acell.tables[0]  # 1x3 (merged) holding "With Apart Research" + author grid
    grid = outer.rows[0].cells[0].tables[0]
    authors = [("Brandon Cardamone", "Independent researcher"), ("Will Morrill", "[Affiliation]")]
    cells = [grid.rows[r].cells[c] for r in range(2) for c in range(3)]
    for k, cell in enumerate(cells):
        if k < len(authors):
            set_cell_text(cell, list(authors[k]), bold_first=True)
        else:
            set_cell_text(cell, [""])
    abox = acell.tables[1].rows[0].cells[0]
    p = abox.paragraphs[0]
    for extra in abox.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    p.add_run(abstract)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # --- remove guidance: everything in the body after the header table (keep section properties)
    bodyel = doc.element.body
    started = False
    for el in list(bodyel.iterchildren()):
        if el is head._tbl:
            started = True
            continue
        if started and el.tag != qn("w:sectPr"):
            bodyel.remove(el)

    normal = doc.styles["normal"]

    def para(text="", style=None, size=None, align=None, indent=None, space_after=4):
        p = doc.add_paragraph(style=style or normal)
        if text:
            add_runs(p, text, size=size)
        if align is not None:
            p.alignment = align
        pf = p.paragraph_format
        pf.space_after = Pt(space_after)
        if indent is not None:
            pf.left_indent = Inches(indent)
            pf.first_line_indent = Inches(-0.18)
        return p

    lines = body.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s or s == "---":
            i += 1
            continue
        if ln.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in block]
            header, data = rows[0], rows[2:]
            t = doc.add_table(rows=1 + len(data), cols=len(header))
            borders(t)
            for j, h in enumerate(header):
                c = t.rows[0].cells[j]
                add_runs(c.paragraphs[0], h, size=8, bold_all=True)
                shade(c, "F1F0EC")
            for r_i, r in enumerate(data, start=1):
                for j, v in enumerate(r[: len(header)]):
                    add_runs(t.rows[r_i].cells[j].paragraphs[0], v, size=8)
            para(space_after=2)
            continue
        m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", s)
        if m:
            p = para(align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
            p.add_run().add_picture(str(ROOT / "report" / m.group(1)), width=Inches(6.3))
            i += 1
            continue
        if ln.startswith("#"):
            level = len(ln) - len(ln.lstrip("#"))
            text = ln.lstrip("#").strip()
            doc.add_heading(text, level=2 if level <= 2 else 3)
            i += 1
            continue
        # section-5 sub-headings that the template formats as Heading 3
        hm = re.match(r"^\*\*(Limitations|Future work|Implications)\.\*\*\s*(.*)$", s)
        if hm:
            name = {"Future work": "Future Work"}.get(hm.group(1), hm.group(1))
            doc.add_heading(name, level=3)
            rest = hm.group(2)
            i += 1
            if rest:
                para(rest)
            continue
        if s.startswith(">"):
            para(s.lstrip("> "), indent=0.3)
            i += 1
            continue
        bm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", ln)
        if bm:
            depth = 1 if len(bm.group(1)) >= 2 else 0
            marker = bm.group(2) if bm.group(2)[0].isdigit() else ("•" if depth == 0 else "–")
            text = bm.group(3)
            i += 1
            while i < len(lines) and lines[i].startswith("    ") and not re.match(r"^\s*([-*]|\d+\.)\s", lines[i]):
                text += " " + lines[i].strip()
                i += 1
            para(f"{marker} {text}", indent=0.28 + 0.25 * depth, space_after=2)
            continue
        text = s
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||!\[|>|\s*([-*]|\d+\.)\s|---)", lines[i]):
            text += " " + lines[i].strip()
            i += 1
        cap = text.startswith("**Figure") or text.startswith("**Table")
        para(text, size=9 if cap else None, space_after=8 if cap else 4)
    doc.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
