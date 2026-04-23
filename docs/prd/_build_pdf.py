"""Build PRD.pdf from PRD.md using Python-Markdown + Chrome headless."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).parent
MD_PATH = HERE / "PRD.md"
HTML_PATH = HERE / "PRD.html"
PDF_PATH = HERE / "PRD.pdf"

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
html { font-size: 11pt; }
body {
  font-family: "Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo", system-ui, -apple-system, sans-serif;
  color: #1a1a1a; line-height: 1.55; max-width: 780px; margin: 0 auto;
}
h1 { font-size: 22pt; border-bottom: 2px solid #111; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 15pt; color: #0b3d91; border-bottom: 1px solid #d0d7de; padding-bottom: 4px; margin-top: 1.4em; }
h3 { font-size: 12.5pt; color: #1b1b1b; margin-top: 1.1em; }
h4 { font-size: 11.5pt; color: #333; }
p, li { font-size: 10.5pt; }
code { background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-family: "Cascadia Code", Consolas, monospace; font-size: 9.5pt; }
pre { background: #0f172a; color: #e2e8f0; padding: 10px 12px; border-radius: 6px; overflow-x: auto; font-size: 9pt; }
pre code { background: transparent; color: inherit; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 0.6em 0; font-size: 10pt; }
th, td { border: 1px solid #d0d7de; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #f6f8fa; font-weight: 600; }
blockquote { border-left: 3px solid #0b3d91; padding-left: 10px; color: #444; margin-left: 0; }
hr { border: none; border-top: 1px dashed #c8c8c8; margin: 1.2em 0; }
strong { color: #0b3d91; }
a { color: #0b3d91; text-decoration: none; }
ul, ol { padding-left: 20px; }
li { margin: 2px 0; }
"""

HTML_TMPL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>hacker-dashboard PRD</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def build_html() -> None:
    md_text = MD_PATH.read_text(encoding="utf-8")
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
        output_format="html5",
    )
    HTML_PATH.write_text(HTML_TMPL.format(css=CSS, body=body), encoding="utf-8")


def build_pdf() -> None:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    browser = next((p for p in candidates if os.path.exists(p)), None)
    if not browser:
        sys.exit("No Chrome/Edge found")

    html_uri = HTML_PATH.resolve().as_uri()
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_PATH}",
        html_uri,
    ]
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        sys.exit(f"Chrome headless failed: rc={result.returncode}")
    if not PDF_PATH.exists():
        sys.exit("PDF was not produced")
    print(f"OK: {PDF_PATH} ({PDF_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    build_html()
    build_pdf()
