"""
CS163 project web view: descriptions + results + visuals only.

"""

from __future__ import annotations

import html as html_module
import json
import os
import re
from pathlib import Path
from typing import Any

from flask import Flask, Response, send_from_directory

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

_DEFAULT_NAMES = [
    "cs163prject.ipynb",
]


def _join_text(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return "".join(val)
    return str(val)


def _code_step_description(source: str) -> str:
    """Short label from comments / first line — not the full notebook code."""
    text = source.strip()
    if not text:
        return "Analysis step"

    lines = text.splitlines()
    comment_lines: list[str] = []
    for line in lines:
        s = line.strip()
        if s.startswith("#") and not s.startswith("#!"):
            comment_lines.append(s.lstrip("#").strip())
        elif s == "" and comment_lines:
            break
        elif comment_lines and not s.startswith("#"):
            break
    if comment_lines:
        joined = " · ".join(comment_lines[:4])
        return (joined[:220] + "…") if len(joined) > 220 else joined

    first = next((ln.strip() for ln in lines if ln.strip()), "")
    if len(first) > 140:
        return first[:137] + "…"
    return first or "Analysis step"


def _stream_is_noise(text: str, stream_name: str | None) -> bool:
    if stream_name == "stderr":
        return True
    if len(text) > 1800:
        return True
    lines = text.strip().splitlines()
    if len(lines) > 35:
        return True
    if sum(1 for ln in lines if "/" in ln and (".json" in ln or ".zip" in ln or "content/" in ln)) > 12:
        return True
    return False


def _outputs_to_html_pretty(outputs: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    for out in outputs or []:
        ot = out.get("output_type")
        if ot == "stream":
            text = _join_text(out.get("text", ""))
            name = out.get("name")
            if _stream_is_noise(text, name):
                continue
            parts.append(f'<pre class="stream">{html_module.escape(text.strip())}</pre>')
        elif ot == "error":
            tb = _join_text(out.get("traceback", []))
            parts.append(f'<pre class="error">{html_module.escape(tb)}</pre>')
        elif ot in ("execute_result", "display_data"):
            data = out.get("data") or {}
            if "text/html" in data:
                th = data["text/html"]
                if isinstance(th, list):
                    th = "".join(th)
                parts.append(f'<div class="html-output">{th}</div>')
            if "image/png" in data:
                png = data["image/png"]
                if isinstance(png, list):
                    png = "".join(png)
                raw = png.replace("\n", "").strip()
                src = raw if raw.startswith("data:") else f"data:image/png;base64,{raw}"
                parts.append(f'<figure class="figure"><img src="{src}" alt="Chart or figure"/></figure>')
            if "image/jpeg" in data:
                jpg = data["image/jpeg"]
                if isinstance(jpg, list):
                    jpg = "".join(jpg)
                raw = jpg.replace("\n", "").strip()
                src = raw if raw.startswith("data:") else f"data:image/jpeg;base64,{raw}"
                parts.append(f'<figure class="figure"><img src="{src}" alt="Chart or figure"/></figure>')
            if "text/plain" in data and "text/html" not in data:
                if "image/png" not in data and "image/jpeg" not in data:
                    tp = data["text/plain"]
                    if isinstance(tp, list):
                        tp = "".join(tp)
                    if len(tp) > 6000:
                        tp = tp[:5997] + "…"
                    parts.append(f'<pre class="result">{html_module.escape(tp)}</pre>')
    return "\n".join(parts)


def _markdown_to_simple_html(text: str) -> str:
    """Very light formatting: # headers and **bold** — no extra dependencies."""
    escaped = html_module.escape(text.strip())
    lines = escaped.split("\n")
    out: list[str] = []
    in_para: list[str] = []
    def flush_para() -> None:
        nonlocal in_para
        if in_para:
            body = " ".join(in_para)
            body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
            out.append(f'<p class="md-p">{body}</p>')
            in_para = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            flush_para()
            out.append(f'<h3 class="md-h3">{stripped[4:]}</h3>')
        elif stripped.startswith("## "):
            flush_para()
            out.append(f'<h2 class="md-h2">{stripped[3:]}</h2>')
        elif stripped.startswith("# "):
            flush_para()
            out.append(f'<h2 class="md-h2">{stripped[2:]}</h2>')
        elif stripped == "":
            flush_para()
        else:
            seg = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
            in_para.append(seg)
    flush_para()
    return "\n".join(out) if out else f'<p class="md-p">{escaped}</p>'


def _notebook_to_html(nb_path: Path) -> str:
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = data.get("cells", [])
    chunks: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
        "<title>CS163 — Yelp Analysis</title>",
        '<link rel="preconnect" href="https://fonts.googleapis.com"/>',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>',
        '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:wght@600;700&display=swap" rel="stylesheet"/>',
        "<style>",
        ":root{--bg:#f8f9fc;--surface:#ffffff;--text:#1a1d26;--muted:#5c6370;--border:#e8eaef;",
        "--accent:#c4122e;--accent-soft:#fde8ec;--shadow:0 4px 24px rgba(26,29,38,.06);--radius:14px;}",
        "*{box-sizing:border-box;}",
        "body{margin:0;font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--text);",
        "line-height:1.55;}",
        ".container{max-width:820px;margin:0 auto;padding:32px 20px 64px;}",
        "header{text-align:center;margin-bottom:40px;padding-bottom:28px;border-bottom:1px solid var(--border);}",
        "header .kicker{font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:8px;}",
        "header h1{font-family:'Fraunces',Georgia,serif;font-size:clamp(1.75rem,4vw,2.35rem);font-weight:700;margin:0 0 10px;color:var(--text);}",
        "header .sub{color:var(--muted);font-size:1rem;max-width:520px;margin:0 auto;}",
        ".block{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);",
        "padding:22px 24px;margin-bottom:20px;box-shadow:var(--shadow);}",
        ".block-desc{border-left:4px solid var(--accent);background:linear-gradient(90deg,var(--accent-soft),var(--surface));}",
        ".block-result{border-left:4px solid #2d6cdf;}",
        ".step-label{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:6px;}",
        ".step-summary{font-size:1.05rem;font-weight:500;color:var(--text);margin-bottom:14px;}",
        ".md-h2{font-family:'Fraunces',Georgia,serif;font-size:1.35rem;margin:0 0 12px;color:var(--text);}",
        ".md-h3{font-size:1.1rem;margin:16px 0 8px;color:var(--text);}",
        ".md-p{margin:0 0 10px;color:var(--text);}",
        ".md-p:last-child{margin-bottom:0;}",
        ".stream,.result,.error{font-size:13px;padding:14px 16px;border-radius:10px;overflow-x:auto;margin-top:12px;",
        "border:1px solid var(--border);background:#fafbfe;}",
        ".result{border-left:3px solid #2d6cdf;}",
        ".error{border-left:3px solid var(--accent);background:#fff5f6;}",
        ".html-output{margin-top:12px;border-radius:10px;overflow:hidden;border:1px solid var(--border);}",
        ".figure{margin:16px 0 0;text-align:center;}",
        ".figure img{max-width:100%;height:auto;border-radius:10px;border:1px solid var(--border);box-shadow:var(--shadow);}",
        ".empty-hint{font-size:13px;color:var(--muted);font-style:italic;margin-top:8px;}",
        "footer{margin-top:48px;text-align:center;font-size:12px;color:var(--muted);}",
        "</style></head><body>",
        '<div class="container">',
        "<header>",
        '<p class="kicker">CS163 · Data-driven report</p>',
        "<h1>Yelp Dataset Analysis</h1>",
        '<p class="sub">Narrative, key results, and figures from your notebook — not full source code.</p>',
        "</header>",
    ]

    for cell in cells:
        ct = cell.get("cell_type")
        src = _join_text(cell.get("source", ""))

        if ct == "markdown" and src.strip():
            chunks.append('<article class="block block-desc">')
            chunks.append(_markdown_to_simple_html(src))
            chunks.append("</article>")

        elif ct == "code":
            out_html = _outputs_to_html_pretty(cell.get("outputs"))
            summary = _code_step_description(src)
            if not out_html.strip():
                continue
            chunks.append('<article class="block block-result">')
            chunks.append('<div class="step-label">What this step shows</div>')
            chunks.append(f'<div class="step-summary">{html_module.escape(summary)}</div>')
            chunks.append(out_html)
            chunks.append("</article>")

    chunks.append(
        f'<footer>Generated from <code>{html_module.escape(nb_path.name)}</code> · presentation mode</footer>'
    )
    chunks.append("</div></body></html>")
    return "\n".join(chunks)


def _find_notebook() -> Path | None:
    env = os.environ.get("NOTEBOOK_PATH", "").strip()
    names = [env] + _DEFAULT_NAMES if env else list(_DEFAULT_NAMES)
    for name in names:
        if not name:
            continue
        p = BASE / name
        if p.is_file():
            return p
    return None


_cached_html: str | None = None
_cached_mtime: float | None = None


def _get_ipynb_report() -> str | None:
    global _cached_html, _cached_mtime
    nb = _find_notebook()
    if nb is None:
        return None
    mtime = nb.stat().st_mtime
    if _cached_html is not None and _cached_mtime == mtime:
        return _cached_html
    _cached_html = _notebook_to_html(nb)
    _cached_mtime = mtime
    return _cached_html


app = Flask(__name__, static_folder=str(STATIC), static_url_path="/assets")
server = app


@app.route("/")
def index():
    static_index = STATIC / "index.html"
    if static_index.is_file():
        return send_from_directory(STATIC, "index.html")
    html = _get_ipynb_report()
    if html is None:
        return Response(
            (
                "<h1>No report found</h1>"
                "<p>Add either:</p><ul>"
                "<li><code>static/index.html</code> (export notebook as HTML), or</li>"
                "<li>your notebook as <code>cs163prject (1).ipynb</code> in this folder.</li>"
                "</ul>"
            ),
            mimetype="text/html",
            status=404,
        )
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
