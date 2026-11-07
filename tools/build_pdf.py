"""Build the recruiter PDFs (pdf/offer_sheet.pdf, pdf/case_study.pdf) from docs/*.md.

Markdown -> HTML (A4 print stylesheet) -> PDF with headless Chrome. Draft notes
(blockquote lines containing 'DRAFT') are dropped. Prints the page count of each PDF
and renders page previews to pdf/preview_*.png.
"""
import re
import subprocess
import sys
from pathlib import Path

import markdown
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DOCS = {"offer_sheet": ("docs/offer_sheet.md", 1), "case_study": ("docs/case_study.md", 2)}

CSS = """
@page { size: A4; margin: 12mm 15mm 11mm 15mm; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 9.6pt;
       line-height: 1.38; color: #1d1d1f; }
h1 { font-size: 17pt; margin: 0 0 2pt; color: #0b3d2e; }
h1 + p em { color: #555; font-size: 10.5pt; }
h2 { font-size: 11.5pt; margin: 9pt 0 3pt; color: #0b3d2e; border-bottom: 1px solid #cfd8d3; padding-bottom: 1pt; }
h2, h3 { break-after: avoid; }
table, img { break-inside: avoid; }
h3 { font-size: 10.5pt; margin: 8pt 0 2pt; color: #0b3d2e; }
p { margin: 3pt 0; }
ul, ol { margin: 2pt 0 4pt; padding-left: 15pt; }
li { margin: 1.5pt 0; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0; font-size: 8.9pt; }
th, td { border: 1px solid #cfd8d3; padding: 2.5pt 5pt; text-align: left; vertical-align: top; }
th { background: #eef3f0; }
blockquote { margin: 3pt 0; padding: 2pt 8pt; border-left: 3px solid #3dcd58; color: #444; font-size: 8.8pt; }
img { display: block; width: 70%; margin: 2pt auto; }
hr { border: 0; border-top: 1px solid #cfd8d3; margin: 6pt 0; }
code { font-size: 8.5pt; }
.steps { display: flex; align-items: stretch; gap: 6pt; margin: 6pt 0 10pt; }
.step { flex: 1; border: 1.5px solid #3dcd58; border-radius: 8pt; padding: 8pt 10pt; text-align: center; background: #f4fbf5; }
.step .num { display: inline-block; width: 18pt; height: 18pt; line-height: 18pt; border-radius: 50%;
             background: #3dcd58; color: white; font-weight: bold; font-size: 10pt; }
.step .title { font-size: 13pt; font-weight: bold; color: #0b3d2e; margin: 3pt 0 2pt; }
.step .txt { font-size: 9pt; color: #333; }
.arrow { align-self: center; font-size: 18pt; color: #3dcd58; }
.timeline { position: relative; height: 44pt; margin: 6pt 6% 4pt; }
.tl-bar { position: absolute; top: 8pt; left: 6pt; right: 6pt; height: 3pt; background: linear-gradient(90deg, #3dcd58, #bbb); border-radius: 2pt; }
.tl-point { position: absolute; top: 2pt; font-size: 9pt; display: flex; flex-direction: column; }
.tl-left { left: 0; align-items: flex-start; } .tl-right { right: 0; align-items: flex-end; text-align: right; }
.dot { width: 15pt; height: 15pt; border-radius: 50%; }
.dot.green { background: #3dcd58; } .dot.grey { background: #999; }
.lbl { margin-top: 3pt; line-height: 1.25; }
img.wide { width: 88%; }
.callout { margin: 10pt auto 6pt; width: 70%; text-align: center; background: #0b3d2e; color: white;
           border-radius: 10pt; padding: 12pt 10pt; }
.callout .big { font-size: 30pt; font-weight: bold; letter-spacing: .5pt; }
.callout .small { font-size: 10.5pt; color: #cfeedd; margin-top: 2pt; }
"""


def md_to_html(md_text: str, base: Path) -> str:
    lines = [l for l in md_text.splitlines() if not (l.startswith(">") and "DRAFT" in l)]
    # python-markdown needs a blank line before a list that follows a paragraph
    is_item = lambda l: bool(re.match(r"^(\s*[-*]|\s*\d+\.)\s", l))
    fixed = []
    for l in lines:
        if is_item(l) and fixed and fixed[-1].strip() and not is_item(fixed[-1]) and not fixed[-1].startswith("|"):
            fixed.append("")
        fixed.append(l)
    lines = fixed
    body = markdown.markdown("\n".join(lines), extensions=["tables", "sane_lists"])
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><base href="{base.as_uri()}/">'
            f"<style>{CSS}</style></head><body>{body}</body></html>")


def build(name: str, src: str, max_pages: int) -> bool:
    src_path = ROOT / src
    html_path = ROOT / "pdf" / f"{name}.html"
    pdf_path = ROOT / "pdf" / f"{name}.pdf"
    html_path.write_text(md_to_html(src_path.read_text(), src_path.parent))
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                   check=True, capture_output=True)
    doc = pymupdf.open(pdf_path)
    for i, page in enumerate(doc):
        page.get_pixmap(dpi=110).save(ROOT / "pdf" / f"preview_{name}_p{i + 1}.png")
    ok = doc.page_count <= max_pages
    print(f"{name}: {doc.page_count} page(s), target {max_pages} -> {'OK' if ok else 'TOO LONG'}")
    return ok


if __name__ == "__main__":
    results = [build(n, s, m) for n, (s, m) in DOCS.items()]
    sys.exit(0 if all(results) else 1)
