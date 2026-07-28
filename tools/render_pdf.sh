#!/usr/bin/env bash
# render_pdf.sh HTML_IN PDF_OUT [--single-page]
#
# Renders a client deliverable to PDF. Exists so PDF generation is a plain
# command (narrowly allowlistable) instead of an inline python3 invocation —
# per the 2026-07-28 fleet harden plan: narrow the command, never widen the
# permission to an interpreter.
#
#   default        paginated letter (216x279mm)
#   --single-page  one continuous page, height measured from content
#                  (the format Dr. Goldsmith gets for demo/report decks)
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: render_pdf.sh HTML_IN PDF_OUT [--single-page]" >&2
  exit 2
fi

IN="$1"; OUT="$2"; MODE="${3:-}"
[ -r "$IN" ] || { echo "render_pdf.sh: cannot read $IN" >&2; exit 2; }
mkdir -p "$(dirname "$OUT")"

RENDER_IN="$IN" RENDER_OUT="$OUT" RENDER_MODE="$MODE" python3 - <<'PY'
import os
from weasyprint import HTML

src, out, mode = os.environ["RENDER_IN"], os.environ["RENDER_OUT"], os.environ["RENDER_MODE"]
html = open(src).read()

if mode == "--single-page":
    # Two-pass: probe tall, then grow to the first height that fits one page.
    if "@page" not in html:
        html = html.replace("<style>", "<style>\n@page { size: 216mm 5000mm; margin: 0; }", 1)
    height = 300.0
    while height <= 5000.0:
        doc = HTML(string=html.replace("5000mm", f"{height}mm"), base_url=src).render()
        if len(doc.pages) == 1:
            doc.write_pdf(out)
            print(f"{out} (single page, {height}mm)")
            break
        height += 20.0
    else:
        raise SystemExit("render_pdf.sh: content exceeds 5000mm; use paginated mode")
else:
    doc = HTML(string=html, base_url=src).render()
    doc.write_pdf(out)
    print(f"{out} ({len(doc.pages)} pages)")
PY
