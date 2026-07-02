#!/usr/bin/env python3
"""Render DASHBOARD_V2_BUILD_PLAN.md → clean white-bg A4 PDF for counter-check."""
import markdown
from pathlib import Path
from playwright.sync_api import sync_playwright

SRC = Path("docs/DASHBOARD_V2_BUILD_PLAN.md")
OUT = Path("docs/DASHBOARD_V2_BUILD_PLAN.pdf")

html_body = markdown.markdown(
    SRC.read_text(),
    extensions=["tables", "fenced_code", "sane_lists", "toc"],
)

CSS = """
@page { size: A4; margin: 16mm 14mm; background:#ffffff; }
html { background:#ffffff; }
body { background:#ffffff; color:#111827; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
       font-size:10.5px; line-height:1.5; max-width:none; }
h1 { font-size:21px; color:#0b0b0c; border-bottom:3px solid #f59e0b; padding-bottom:6px; margin:0 0 10px; }
h2 { font-size:15px; color:#0b0b0c; border-bottom:1px solid #e5e7eb; padding-bottom:3px; margin:20px 0 8px; }
h3 { font-size:12.5px; color:#b45309; margin:14px 0 5px; }
p, li { margin:4px 0; }
strong { color:#0b0b0c; }
code { background:#f3f4f6; padding:1px 4px; border-radius:3px; font-size:9.5px; color:#b91c1c; }
pre { background:#f8fafc; border:1px solid #e5e7eb; border-radius:6px; padding:8px; overflow:auto; }
blockquote { border-left:3px solid #f59e0b; background:#fffbeb; margin:8px 0; padding:6px 12px; color:#374151; font-size:10px; }
table { border-collapse:collapse; width:100%; margin:8px 0; font-size:9.5px; }
th { background:#111827; color:#fff; text-align:left; padding:5px 7px; }
td { border:1px solid #e5e7eb; padding:5px 7px; vertical-align:top; }
tr:nth-child(even) td { background:#f9fafb; }
hr { border:none; border-top:1px solid #e5e7eb; margin:16px 0; }
"""

html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}</body></html>"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.set_content(html, wait_until="networkidle")
    pg.pdf(path=str(OUT), format="A4", print_background=True,
           margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    b.close()

print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
