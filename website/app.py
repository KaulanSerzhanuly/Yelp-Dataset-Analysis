"""
CS163 project web view: Yelp-themed tabbed report built from notebook chart outputs.

1) Optional: static/index.html (notebook exported as HTML from Colab/Jupyter).
2) Otherwise: reads .ipynb — skips markdown, code source, streams, errors, and
   non-image outputs; figures appear under Analytics / Preliminary Results tabs.
"""

from __future__ import annotations

import html
import json
import os
import requests
from pathlib import Path
from typing import Any

from flask import Flask, Response, send_from_directory

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
INTERACTIVE = STATIC / "interactive"
INFERENCE_URL = "https://restaurant-inference-940451978632.us-central1.run.app/predict"

_DEFAULT_NAMES = [
    "cs163prject.ipynb",
    "cs163prject (1).ipynb",
]


def _join_text(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return "".join(val)
    return str(val)


def _outputs_to_html_pretty(outputs: list[dict[str, Any]] | None) -> str:
    """Render only embedded chart images; skip HTML tables, plain text, etc."""
    parts: list[str] = []
    seen_png: set[str] = set()
    seen_jpg: set[str] = set()

    for out in outputs or []:
        ot = out.get("output_type")
        if ot == "stream":
            continue
        if ot == "error":
            continue
        elif ot in ("execute_result", "display_data"):
            data = out.get("data") or {}
            if "image/png" in data:
                png = data["image/png"]
                if isinstance(png, list):
                    png = "".join(png)
                raw = png.replace("\n", "").strip()
                if raw and raw not in seen_png:
                    seen_png.add(raw)
                    src = raw if raw.startswith("data:") else f"data:image/png;base64,{raw}"
                    parts.append(f'<figure class="figure"><img src="{src}" alt="Chart or figure"/></figure>')
            if "image/jpeg" in data:
                jpg = data["image/jpeg"]
                if isinstance(jpg, list):
                    jpg = "".join(jpg)
                raw = jpg.replace("\n", "").strip()
                if raw and raw not in seen_jpg:
                    seen_jpg.add(raw)
                    src = raw if raw.startswith("data:") else f"data:image/jpeg;base64,{raw}"
                    parts.append(f'<figure class="figure"><img src="{src}" alt="Chart or figure"/></figure>')
    return "\n".join(parts)


def _collect_figure_blocks(cells: list[dict[str, Any]]) -> list[str]:
    """Ordered list of <figure>...</figure> HTML fragments from code cell outputs."""
    blocks: list[str] = []
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        raw = _outputs_to_html_pretty(cell.get("outputs"))
        if not raw.strip():
            continue
        for piece in raw.split("</figure>"):
            piece = piece.strip()
            if "<figure" in piece:
                blocks.append(piece + "</figure>")
    return blocks


def _split_figures_for_tabs(figures: list[str]) -> tuple[list[str], list[str]]:
    """First chunk → Analytics, second → Preliminary Results (roughly half each)."""
    if not figures:
        return [], []
    n = len(figures)
    cut = (n + 1) // 2
    return figures[:cut], figures[cut:]


def _interactive_signature() -> float:
    """Max mtime of standalone Plotly HTML files; used so new files show without notebook resave."""
    if not INTERACTIVE.is_dir():
        return 0.0
    mtimes = [p.stat().st_mtime for p in INTERACTIVE.glob("*.html")]
    return max(mtimes) if mtimes else 0.0


# Ordered labels for the Interactive tab (matches major-findings narrative).
_INTERACTIVE_ORDER: list[tuple[str, str]] = [
    ("model_comparison.html", "Model comparison (Yelp vs Yelp + UberEats)"),
    ("hyp1_plot1.html", "Hypothesis 1 — Star ratings (plot 1)"),
    ("hyp1_plot2.html", "Hypothesis 1 — Star ratings (plot 2)"),
    ("hyp2_plot1.html", "Hypothesis 2 — Review count (plot 1)"),
    ("hyp2_plot2.html", "Hypothesis 2 — Review count (plot 2)"),
    ("hyp4_plot1.html", "Finding 4 — Complaint / sentiment (plot 1)"),
    ("hyp4_plot2.html", "Finding 4 — Complaint / sentiment (plot 2)"),
    ("hyp5_plot1.html", "Finding 5 — Sentiment (plot 1)"),
    ("hyp5_plot2.html", "Finding 5 — Sentiment (plot 2)"),
]


def _is_probably_html(path: Path) -> bool:
    """True if file looks like HTML (avoids serving a mis-saved notebook as index)."""
    try:
        head = path.read_bytes()[:800].lstrip()
    except OSError:
        return False
    return head.startswith(b"<!DOCTYPE") or head.startswith(b"<html") or head.startswith(b"<!--")


def _static_figure(rel: str, alt: str, caption: str) -> str:
    """One <figure> for PNG/JPEG under static/, or empty string if missing."""
    name = Path(rel).name
    p = STATIC / name
    if not p.is_file():
        return ""
    ext = p.suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        return ""
    alt_a = html.escape(alt, quote=True)
    cap = html.escape(caption)
    src = html.escape(f"/assets/{name}", quote=True)
    return (
        f'<figure class="figure" style="margin-top:1rem;">'
        f'<img src="{src}" alt="{alt_a}"/>'
        f'<figcaption class="figure-caption">{cap}</figcaption></figure>'
    )


def _landing_static_backup_figure() -> str:
    return (
        _static_figure(
            "viz_core.png",
            "Core static visualization",
            "Static overview (PNG) — optional backup if the iframe is slow to load.",
        )
        or _static_figure(
            "viz_text.png",
            "Summary visualization",
            "Static overview (PNG) — optional backup if the iframe is slow to load.",
        )
    )


def _findings_static_summary_block() -> str:
    t = _static_figure(
        "viz_text.png",
        "Text and sentiment static summary",
        "Static text/sentiment summary (PNG).",
    )
    c = _static_figure(
        "viz_core.png",
        "Core static summary",
        "Static core summary (PNG).",
    )
    if t and c:
        return f'<div class="two-col" style="margin-top: 1.5rem;">{t}{c}</div>'
    if t or c:
        return f'<div style="margin-top: 1.5rem;">{t}{c}</div>'
    return (
        '<p class="muted" style="margin-top:1.5rem;">No static summary images in '
        "<code>static/</code> (optional: add <code>viz_text.png</code> / <code>viz_core.png</code>).</p>"
    )


def _cloud_storage_notebook_sample_html() -> str:
    """
    Five sample rows copied from the saved output of restaurants.head() in
    cs163prject (1).ipynb, after restaurants = restaurants[review_count >= 50].
    """
    cols = ("Idx", "business_id", "name", "city", "state", "stars", "review_count", "is_open")
    rows = (
        ("3", "MTSW4McQd7CbVtyjqoe9mw", "St Honore Pastries", "Philadelphia", "PA", "4.0", "80", "1"),
        ("14", "0bPLkL0QhhPO5kt1_EXmNQ", "Zio's Italian Market", "Largo", "FL", "4.5", "100", "0"),
        ("15", "MUTTqe8uqyMdBl186RmNeA", "Tuna Bar", "Philadelphia", "PA", "4.0", "245", "1"),
        ("19", "ROeacJQwBeh05Rqg7F6TCg", "BAP", "Philadelphia", "PA", "4.5", "205", "1"),
        ("23", "9OG5YkX1g2GReZM0AskizA", "Romano's Macaroni Grill", "Reno", "NV", "2.5", "339", "1"),
    )
    thead = "<thead><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in cols) + "</tr></thead>"
    body_parts: list[str] = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
        body_parts.append(f"<tr>{cells}</tr>")
    tbody = "<tbody>" + "".join(body_parts) + "</tbody>"
    table = f'<table class="cloud-sample-table">{thead}{tbody}</table>'
    filter_code = 'restaurants = restaurants[restaurants["review_count"] &gt;= 50]'
    return (
        '<h3 style="margin-top: 1.35rem; font-family: var(--font-display); font-size: 1.05rem;">'
        "Sample rows (from the notebook)</h3>"
        '<p class="muted">Copied from the <strong>text output</strong> of <code>restaurants.head()</code> in '
        '<code>cs163prject (1).ipynb</code>, right after <code>'
        + filter_code
        + "</code>. The full table there has <strong>14 columns</strong> (we show eight here; "
        "<code>attributes</code>, <code>categories</code>, and <code>hours</code> are omitted so the sample fits the page).</p>"
        f'<div class="cloud-sample-wrap">{table}</div>'
        "<p><strong>What each column means.</strong></p>"
        '<ul class="points">'
        "<li><strong>Idx</strong> — original DataFrame index in that notebook run (not the row number in the full Yelp file).</li>"
        "<li><strong>business_id</strong> — Yelp’s unique key; use this when merging reviews or UberEats rows.</li>"
        "<li><strong>name / city / state</strong> — listing label and location fields used for maps and filters.</li>"
        "<li><strong>stars</strong> — average star rating on Yelp at snapshot time.</li>"
        "<li><strong>review_count</strong> — number of reviews; in this cohort every row has count <strong>≥ 50</strong> "
        "because of the filter above.</li>"
        "<li><strong>is_open</strong> — target for modeling: <strong>1</strong> = open, <strong>0</strong> = closed "
        "(e.g. row <strong>14</strong> is closed).</li>"
        "</ul>"
        "<p class=\"muted\"><strong>What each row is.</strong> One line = one restaurant. Example: row <strong>3</strong> "
        "is a Philadelphia bakery/tea shop with 80 reviews and still open; row <strong>23</strong> is a lower-star "
        "Italian chain location in Reno with more reviews but still marked open in the data.</p>"
    )


def _interactive_iframe_embed(filename: str, title: str) -> str:
    """Embed a Plotly HTML under static/interactive/, or a short placeholder if missing."""
    safe_name = Path(filename).name
    if not (INTERACTIVE / safe_name).is_file():
        return (
            f'<p class="muted">Missing <code>static/interactive/{html.escape(safe_name)}</code>. '
            f"Add the export, then refresh.</p>"
        )
    title_attr = html.escape(title, quote=True)
    src_path = html.escape(f"/assets/interactive/{safe_name}", quote=True)
    return (
        f'<div class="finding-iframe-wrap">'
        f'<iframe title="{title_attr}" src="{src_path}" loading="lazy" referrerpolicy="no-referrer"></iframe>'
        f"</div>"
    )


def _interactive_select_html() -> tuple[str, str]:
    """Returns (options_html, default_value) for the interactive figure dropdown."""
    on_disk = {p.name for p in INTERACTIVE.glob("*.html")} if INTERACTIVE.is_dir() else set()
    options: list[str] = []
    default_val = ""
    for fname, label in _INTERACTIVE_ORDER:
        if fname not in on_disk:
            continue
        options.append(f'<option value="{fname}">{label}</option>')
        if not default_val:
            default_val = fname
    for fname in sorted(on_disk):
        if fname in {x[0] for x in _INTERACTIVE_ORDER}:
            continue
        options.append(f'<option value="{fname}">{fname}</option>')
        if not default_val:
            default_val = fname
    return "".join(options), default_val


def _notebook_to_html(nb_path: Path) -> str:
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = data.get("cells", [])
    figures = _collect_figure_blocks(cells)
    analytics_figs, prelim_figs = _split_figures_for_tabs(figures)

    def _fig_stack(figs: list[str]) -> str:
        if not figs:
            return '<p class="muted">No chart images were found in saved notebook outputs. In Jupyter or Colab, use <strong>Run all</strong> so figures are embedded, then save the notebook.</p>'
        return '<div class="viz-stack">' + "".join(figs) + "</div>"

    nb_name = nb_path.name
    analytics_html = _fig_stack(analytics_figs)
    prelim_html = _fig_stack(prelim_figs)
    cloud_notebook_sample = _cloud_storage_notebook_sample_html()
    interactive_options, interactive_default = _interactive_select_html()
    n_interactive = len([p for p in INTERACTIVE.glob("*.html")]) if INTERACTIVE.is_dir() else 0
    has_interactive = bool(interactive_options.strip())
    interactive_block = f"""
        <div class="callout">
          <strong>Interactive figures.</strong>
          Standalone Plotly HTML files in <code>static/interactive/</code> are listed below.
          Files found: <strong>{n_interactive}</strong>.
        </div>
        <div class="interactive-controls">
          <label for="interactive-select"><strong>Select a figure</strong></label>
          <select id="interactive-select" data-default="{interactive_default}" {'disabled' if not has_interactive else ''}>
            {interactive_options if has_interactive else '<option value="">No interactive files found</option>'}
          </select>
        </div>
        <div class="interactive-frame-wrap">
          <iframe id="interactive-frame" title="Interactive figure" src="" loading="lazy" referrerpolicy="no-referrer"></iframe>
        </div>
        """

    landing_model_viz = _interactive_iframe_embed(
        "model_comparison.html",
        "Model comparison (interactive)",
    )
    landing_static_backup = _landing_static_backup_figure()
    findings_static_summary = _findings_static_summary_block()

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>CS163 — Yelp Dataset Analysis</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Fraunces:ital,opsz,wght@0,9..144,600;0,9..144,700;1,9..144,600&display=swap" rel="stylesheet"/>
<style>
:root {{
  --yelp-red: #d32323;
  --yelp-red-dark: #af1f1f;
  --yelp-cream: #faf6f1;
  --yelp-gold: #ffc72c;
  --ink: #1a1a1a;
  --muted: #5c5c5c;
  --card: #ffffff;
  --font-sans: "DM Sans", system-ui, -apple-system, sans-serif;
  --font-display: "Fraunces", Georgia, "Times New Roman", serif;
}}
*,*::before,*::after {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: var(--font-sans);
  color: var(--ink);
  background: var(--yelp-cream);
  line-height: 1.65;
}}
.hero {{
  background: linear-gradient(165deg, var(--yelp-red) 0%, var(--yelp-red-dark) 55%, #7a1515 100%);
  color: #fff;
  text-align: center;
  padding: clamp(1.75rem, 5vw, 2.75rem) clamp(1rem, 4vw, 2rem) 0;
  box-shadow: 0 8px 32px rgba(211, 35, 35, 0.25);
}}
.kicker {{
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.88);
  margin: 0 0 0.75rem;
}}
.hero h1 {{
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(1.65rem, 4.5vw, 2.35rem);
  line-height: 1.2;
  margin: 0 0 0.5rem;
  text-shadow: 0 1px 2px rgba(0,0,0,.15);
}}
.subtitle {{
  font-family: var(--font-display);
  font-size: clamp(0.95rem, 2.2vw, 1.1rem);
  font-weight: 500;
  opacity: 0.95;
  max-width: 38rem;
  margin: 0 auto;
  padding-bottom: 1.25rem;
}}
.nav {{
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  border-top: 1px solid rgba(255,255,255,.22);
  margin-top: 0.5rem;
}}
.nav button {{
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgba(255,255,255,.92);
  background: transparent;
  border: none;
  border-right: 1px solid rgba(255,255,255,.18);
  padding: 0.95rem 1.1rem;
  cursor: pointer;
  flex: 1 1 auto;
  min-width: 7rem;
  transition: background .15s ease, color .15s ease;
}}
.nav button:last-child {{ border-right: none; }}
.nav button:hover {{
  background: rgba(0,0,0,.12);
}}
.nav button.active {{
  background: rgba(0,0,0,.22);
  color: #fff;
}}
.nav button:focus-visible {{
  outline: 2px solid var(--yelp-gold);
  outline-offset: -2px;
}}
.meta {{
  text-align: center;
  font-size: 0.8rem;
  color: var(--muted);
  padding: 0.85rem 1rem;
}}
.wrap {{
  max-width: 52rem;
  margin: 0 auto;
  padding: 0 clamp(1rem, 4vw, 1.5rem) clamp(2.5rem, 6vw, 4rem);
}}
/* Landing: wider canvas + taller primary plot */
.wrap:has(#panel-landing.active) {{
  max-width: min(96vw, 76rem);
  padding-left: clamp(0.75rem, 2.5vw, 1.75rem);
  padding-right: clamp(0.75rem, 2.5vw, 1.75rem);
}}
@media (min-width: 1000px) {{
  #panel-landing .landing-hero-grid {{
    grid-template-columns: 0.88fr 1.35fr;
    gap: 1.75rem;
    align-items: start;
  }}
}}
#panel-landing .finding-iframe-wrap {{
  margin-top: 0.65rem;
}}
#panel-landing .finding-iframe-wrap iframe {{
  min-height: 28rem;
  height: min(82vh, 56rem);
}}
@media (max-width: 899px) {{
  #panel-landing .landing-hero-grid {{
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }}
  #panel-landing .landing-hero-grid > div:last-child {{ order: -1; }}
  #panel-landing .finding-iframe-wrap iframe {{
    min-height: 22rem;
    height: min(75vh, 32rem);
  }}
}}
.card {{
  background: var(--card);
  border-radius: 12px;
  padding: clamp(1.35rem, 4vw, 2rem) clamp(1.25rem, 4vw, 2.25rem);
  box-shadow: 0 4px 24px rgba(26, 26, 26, 0.06), 0 1px 3px rgba(26, 26, 26, 0.04);
  border: 1px solid rgba(26, 26, 26, 0.06);
}}
.card h2 {{
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--yelp-red-dark);
  margin: 0 0 0.65rem;
}}
.rule {{
  height: 3px;
  width: 4.5rem;
  background: linear-gradient(90deg, var(--yelp-gold), rgba(255, 199, 44, 0.35));
  border-radius: 2px;
  margin-bottom: 1.25rem;
}}
.card p {{ margin: 0 0 1rem; }}
.card p:last-child {{ margin-bottom: 0; }}
.lead {{ font-size: 1.05rem; color: #2d2d2d; }}
.muted {{ color: var(--muted); font-size: 0.95rem; }}
.panel {{ display: none; }}
.panel.active {{ display: block; }}
.callout {{
  margin-top: 1.35rem;
  padding: 1rem 1.15rem;
  background: linear-gradient(90deg, rgba(211, 35, 35, 0.08), rgba(255, 199, 44, 0.08));
  border-left: 4px solid var(--yelp-red);
  border-radius: 0 8px 8px 0;
}}
.callout strong {{ color: var(--yelp-red-dark); }}
.viz-stack {{
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-top: 0.5rem;
}}
.figure {{
  margin: 0;
  text-align: center;
}}
.figure img {{
  max-width: 100%;
  height: auto;
  border-radius: 10px;
  border: 1px solid rgba(26, 26, 26, 0.08);
  box-shadow: 0 8px 28px rgba(26, 26, 26, 0.08);
}}
ul.points {{
  margin: 0.5rem 0 0;
  padding-left: 1.2rem;
}}
ul.points li {{ margin-bottom: 0.45rem; }}
.two-col {{
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.25rem;
}}
@media (min-width: 900px) {{
  .two-col {{ grid-template-columns: 1.1fr 0.9fr; }}
}}
.figure-caption {{
  margin-top: 0.5rem;
  color: var(--muted);
  font-size: 0.92rem;
  text-align: center;
}}
.interactive-controls {{
  display: grid;
  gap: 0.35rem;
  margin-top: 1rem;
}}
.interactive-controls select {{
  width: 100%;
  max-width: 28rem;
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  border: 1px solid rgba(26, 26, 26, 0.18);
  background: #fff;
  font-family: var(--font-sans);
}}
.interactive-frame-wrap {{
  margin-top: 1rem;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(26, 26, 26, 0.10);
  box-shadow: 0 8px 28px rgba(26, 26, 26, 0.08);
  background: #fff;
}}
.interactive-frame-wrap iframe {{
  width: 100%;
  height: min(72vh, 760px);
  border: 0;
  display: block;
}}
.finding-iframe-wrap {{
  margin: 1rem 0 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(26, 26, 26, 0.10);
  box-shadow: 0 8px 28px rgba(26, 26, 26, 0.08);
  background: #fff;
}}
.finding-iframe-wrap iframe {{
  width: 100%;
  height: min(52vh, 520px);
  border: 0;
  display: block;
}}
h3.finding-title {{
  margin-top: 1.5rem;
  font-family: var(--font-display);
  font-size: 1.05rem;
}}
h3.finding-title:first-of-type {{ margin-top: 0.25rem; }}
.cloud-sample-wrap {{
  margin: 1rem 0 1.25rem;
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid rgba(26, 26, 26, 0.10);
  background: #fff;
  box-shadow: 0 4px 18px rgba(26, 26, 26, 0.06);
}}
.cloud-sample-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
  min-width: 36rem;
}}
.cloud-sample-table th,
.cloud-sample-table td {{
  padding: 0.55rem 0.65rem;
  text-align: left;
  border-bottom: 1px solid rgba(26, 26, 26, 0.08);
  vertical-align: top;
}}
.cloud-sample-table thead th {{
  background: linear-gradient(180deg, rgba(211, 35, 35, 0.09), rgba(255, 199, 44, 0.06));
  font-weight: 600;
  white-space: nowrap;
}}
.cloud-sample-table tbody tr:hover {{
  background: rgba(26, 26, 26, 0.03);
}}
.cloud-sample-table td:nth-child(2) {{
  font-family: ui-monospace, monospace;
  font-size: 0.78rem;
}}
</style></head><body>
<header class="hero">
  <p class="kicker">CS163 · Data-driven report</p>
  <h1>Predicting Restaurant Success Using Yelp &amp; UberEats Data</h1>
  <p class="subtitle">This project analyzes factors associated with whether restaurants remain open, using customer reviews, ratings, and delivery platform data. We relate observable signals to <strong>is_open</strong> (open vs. closed) in the Yelp business snapshot.</p>
  <nav class="nav" aria-label="Report sections">
    <button type="button" class="nav-btn active" data-tab="landing">Landing</button>
    <button type="button" class="nav-btn" data-tab="objectives">Project objectives</button>
    <button type="button" class="nav-btn" data-tab="methods">Analytical methods</button>
    <button type="button" class="nav-btn" data-tab="findings">Major findings</button>
    <button type="button" class="nav-btn" data-tab="cloud">Cloud storage</button>
    <button type="button" class="nav-btn" data-tab="interactive">Interactive</button>
    <button type="button" class="nav-btn" data-tab="prediction">Prediction Tool</button>
    <button type="button" class="nav-btn" data-tab="appendix">Appendix (notebook figures)</button>
  </nav>
</header>
<p class="meta">CS163 · Spring 2026 · Live view from <strong>{nb_name}</strong> (embedded chart outputs + static visuals)</p>
<div class="wrap">
  <div class="panels">
    <section id="panel-landing" class="panel card active" role="tabpanel">
      <h2>Landing page</h2>
      <div class="rule"></div>
      <p class="lead">This site summarizes our work on predicting restaurant “survival” (open vs. closed) using the <strong>Yelp Open Dataset</strong> merged with optional <strong>UberEats</strong>-style delivery signals.</p>
      <div class="two-col landing-hero-grid">
        <div>
          <p>We study whether easily observed signals—<strong>review volume</strong>, <strong>star ratings</strong>, <strong>review-text sentiment</strong>, and <strong>complaint-related language</strong>—are associated with <code>is_open</code> in the dataset snapshot.</p>
          <div class="callout">
            <strong>Key insights.</strong>
            <ul class="points">
              <li>Restaurants with <strong>more reviews</strong> are more likely to remain open.</li>
              <li><strong>Ratings</strong> have a smaller separating effect than expected (heavy overlap between groups).</li>
              <li><strong>Sentiment</strong> differs significantly but has limited predictive power on its own.</li>
              <li><strong>Delivery-platform data</strong> provides a slight improvement when added to Yelp features.</li>
            </ul>
          </div>
        </div>
        <div>
          <p class="muted" style="margin-top:0;">Primary visualization: <strong>model comparison</strong> (accuracy / F1 / ROC-AUC). Use the <strong>Interactive</strong> tab to explore all Plotly exports.</p>
          {landing_model_viz}
          {landing_static_backup}
        </div>
      </div>
      <div class="callout">
        <strong>Research question.</strong> Which observable Yelp (and optional delivery) signals are associated with whether a restaurant is open vs. closed?
      </div>
    </section>
    <section id="panel-objectives" class="panel card" role="tabpanel">
      <h2>Project objectives</h2>
      <div class="rule"></div>
      <p class="lead"><strong>Problem statement.</strong> This project investigates which factors are associated with whether a restaurant is <strong>open</strong> or <strong>closed</strong>.</p>
      <p><strong>Data sources.</strong></p>
      <ul class="points">
        <li><strong>Yelp Open Dataset</strong> (business attributes + reviews).</li>
        <li><strong>UberEats dataset</strong> (or similar delivery listing), merged via normalized name/address where applicable.</li>
      </ul>
      <ul class="points">
        <li><strong>Unit of analysis</strong>: one row per restaurant (<code>business_id</code>).</li>
        <li><strong>Target variable</strong>: <code>is_open</code> (<strong>1</strong> = open, <strong>0</strong> = closed).</li>
        <li><strong>Goal</strong>: test hypotheses with plots and statistics, then compare predictive models with and without delivery features.</li>
      </ul>
      <div class="callout">
        <strong>Hypotheses.</strong>
        <ul class="points">
          <li>Open restaurants have <strong>higher Yelp star ratings</strong>.</li>
          <li>Restaurants with <strong>more reviews</strong> are more likely to be open.</li>
          <li><strong>Positive sentiment</strong> in review text is associated with being open.</li>
          <li><em>Optional:</em> higher <strong>complaint</strong>-related language is associated with closure.</li>
          <li><em>Optional:</em> adding <strong>UberEats</strong> features improves prediction vs. Yelp-only models.</li>
        </ul>
      </div>
    </section>
    <section id="panel-methods" class="panel card" role="tabpanel">
      <h2>Analytical methods</h2>
      <div class="rule"></div>
      <p class="lead">We combine filtering + feature engineering with statistical tests and a baseline ML classifier.</p>
      <ul class="points">
        <li><strong>Data processing</strong>: filter to restaurants with <strong>≥ 50 reviews</strong>; clean/normalize names; <strong>merge Yelp + UberEats</strong> on matched listings (where used).</li>
        <li><strong>Feature engineering</strong>:
          <ul class="points">
            <li><code>log_reviews</code></li>
            <li><code>avg_sentiment</code></li>
            <li><code>avg_complaints</code></li>
            <li><code>delivery_presence</code> (and related delivery fields where available)</li>
          </ul>
        </li>
        <li><strong>Statistical methods</strong>: <strong>t-tests</strong> for comparing means; <strong>chi-square</strong> for categorical relationships where appropriate.</li>
        <li><strong>Machine learning</strong>: <strong>logistic regression</strong> classifier. Metrics: <strong>accuracy</strong>, <strong>F1 score</strong>, <strong>ROC-AUC</strong>.</li>
      </ul>
    </section>
    <section id="panel-findings" class="panel card" role="tabpanel">
      <h2>Major findings</h2>
      <div class="rule"></div>
      <p class="lead">Each finding pairs a visualization with a short interpretation (report draft). Interactive Plotly exports are embedded below; alternate views are in the <strong>Interactive</strong> tab.</p>

      <h3 class="finding-title">Finding 1: Star ratings</h3>
      <p>Open restaurants had a slightly higher average Yelp rating (<strong>3.77 vs. 3.64</strong> stars). A two-sample t-test indicated that this difference was statistically significant (<strong>p &lt; 0.001</strong>). However, the plot shows <strong>substantial overlap</strong> between the two groups, suggesting that star ratings alone provide <strong>limited predictive power</strong>.</p>
      {_interactive_iframe_embed("hyp1_plot1.html", "Finding 1 — star ratings (plot 1)")}
      {_interactive_iframe_embed("hyp1_plot2.html", "Finding 1 — star ratings (plot 2)")}

      <h3 class="finding-title">Finding 2: Review count</h3>
      <p>Open restaurants have <strong>substantially higher review counts</strong> than closed restaurants. The median and upper range of <code>log_reviews</code> are noticeably larger for open restaurants, indicating that businesses with greater customer engagement are more likely to remain in operation.</p>
      {_interactive_iframe_embed("hyp2_plot1.html", "Finding 2 — review count (plot 1)")}
      {_interactive_iframe_embed("hyp2_plot2.html", "Finding 2 — review count (plot 2)")}

      <h3 class="finding-title">Finding 3: UberEats features</h3>
      <p>Including UberEats features produced only a <strong>modest improvement</strong> in predictive performance. Restaurants listed on delivery platforms tended to be more likely to be open, which suggests that participation in food delivery is associated with continued operation. Variables such as <code>delivery_presence</code>, UberEats score/ratings, and price level did not <strong>substantially</strong> increase accuracy or ROC-AUC compared with Yelp-only models—much of the signal overlaps review volume and sentiment already captured on Yelp.</p>
      {_interactive_iframe_embed("model_comparison.html", "Model comparison — Yelp vs Yelp + UberEats")}

      <h3 class="finding-title">Finding 4: Complaint frequency</h3>
      <p>Closed restaurants exhibit <strong>higher complaint frequency</strong> than open restaurants. Complaint-related words such as “slow,” “rude,” and “overpriced” appear more often in reviews of businesses that are no longer operating. This supports the idea that negative customer experiences are associated with closure.</p>
      {_interactive_iframe_embed("hyp4_plot1.html", "Finding 4 — complaints / text (plot 1)")}
      {_interactive_iframe_embed("hyp4_plot2.html", "Finding 4 — complaints / text (plot 2)")}

      <h3 class="finding-title">Finding 5: Sentiment</h3>
      <p>Open restaurants have slightly higher average sentiment scores than closed restaurants. A t-test showed this difference is statistically significant (<strong>p &lt; 0.001</strong>), but the <strong>strong overlap</strong> between the two distributions suggests that sentiment alone has limited predictive power.</p>
      {_interactive_iframe_embed("hyp5_plot1.html", "Finding 5 — sentiment (plot 1)")}
      {_interactive_iframe_embed("hyp5_plot2.html", "Finding 5 — sentiment (plot 2)")}

      {findings_static_summary}
    </section>
    <section id="panel-cloud" class="panel card" role="tabpanel">
      <h2>Cloud storage</h2>
      <div class="rule"></div>
      <p class="lead">The Yelp Open Dataset is too large to version in Git or to ship inside a small web app. We rely on <strong>cloud storage</strong> for raw inputs, team handoffs, and reproducible analysis—while this site only serves <strong>aggregated results</strong> and pre-rendered visuals.</p>
      <p><strong>What stays in the cloud (not in the repo).</strong> Original Yelp JSON archives, optional UberEats extracts, and any full review-level tables live in shared storage. The notebook and pipeline read from there, filter to restaurants with at least fifty reviews, and build restaurant-level features such as <code>log_reviews</code>, <code>avg_sentiment</code>, and <code>avg_complaints</code>.</p>
      <p><strong>What we upload and why.</strong> Uploading to cloud storage keeps one canonical copy for the team, avoids emailing multi-gigabyte files, and lets Colab, Cloud Shell, or BigQuery attach to the same path. We only promote <em>small</em> derived artifacts (CSVs of features, model pickles, Plotly HTML, PNGs) into the deployment bundle when needed for grading or demos.</p>
      {cloud_notebook_sample}
      <h3 style="margin-top: 1.25rem; font-family: var(--font-display); font-size: 1.05rem;">Typical workflows</h3>
      <p><strong>Google Drive (collaboration).</strong> Zip the Yelp JSON (or a subset) into Drive, mount Drive in Colab, and unzip to the runtime disk. That matches how we discover archives under <code>MyDrive</code> and keeps credentials inside Google’s environment instead of on personal laptops.</p>
      <p><strong>Cloud Storage (GCS) buckets.</strong> For larger teams or automation, upload the archive with <code>gsutil cp</code> or the Cloud Console “Upload” action into a bucket (for example <code>gs://&lt;project-id&gt;-yelp-raw/</code>). Grant read access only to service accounts that need it. Colab or Vertex AI can stream or copy objects into the notebook VM without checking multi-gigabyte files into Git.</p>
      <p><strong>BigQuery (optional analytics).</strong> After load jobs or Dataflow pipelines land curated tables in BigQuery, SQL becomes the interface for aggregates. That is useful when you want restaurant-level metrics computed in the cloud rather than in a single Python process.</p>
      <p><strong>This App Engine site.</strong> The deployed application does <strong>not</strong> mount buckets at runtime. It ships static HTML, images, and interactive Plotly exports built ahead of time. If we needed live data, we would expose a narrow API or query layer—not the full review corpus.</p>
      <ul class="points">
        <li>Store <strong>raw</strong> Yelp JSON in Drive or GCS; never commit it to the repository.</li>
        <li>Upload <strong>processed</strong> restaurant-level CSV or Parquet after filtering (≥ 50 reviews) for faster reloads.</li>
        <li>Use <strong>consistent paths</strong> (Drive folder or bucket prefix) documented in the notebook so everyone runs the same pipeline.</li>
        <li>Version <strong>exports</strong> (model comparison HTML, figures) with dates or commit hashes when sharing with instructors.</li>
        <li>Keep <strong>secrets and keys</strong> out of the repo; use Cloud IAM, bucket ACLs, or Colab secrets for access.</li>
        <li>For course submission, a short paragraph plus this tab satisfies the “cloud storage” requirement: we describe <em>where</em> data lives and <em>how</em> uploads flow, without bundling the raw dataset.</li>
      </ul>
      <p class="muted"><strong>How to upload (quick).</strong> In the Google Cloud Console: Storage → your bucket → <strong>Upload files</strong>. From Cloud Shell: <code>gsutil cp ./restaurants_sample.csv gs://YOUR_BUCKET/path/</code>. In Drive: drag a CSV export into a shared folder, then mount Drive in Colab and <code>pd.read_csv</code> from that path.</p>
      <div class="callout">
        <strong>Summary.</strong> Cloud storage holds the heavy inputs; the web app shows the analysis outputs. Upload raw data once to Drive or GCS, run the notebook against that location, then deploy only the lightweight site bundle.
      </div>
    </section>
    <section id="panel-interactive" class="panel card" role="tabpanel">
      <h2>Interactive diagram</h2>
      <div class="rule"></div>
      <p class="muted">If you export interactive figures (Plotly) as standalone HTML, this page will automatically list and render them.</p>
      {interactive_block}
    </section>
    <section id="panel-prediction" class="panel card" role="tabpanel">
  <h2>Prediction Tool</h2>
  <div class="rule"></div>
  <p class="lead">
    This page demonstrates the Cloud Run machine learning inference service.
    The website sends restaurant features to the deployed API, which returns
    a predicted operating status and probability.
  </p>

  <div class="callout">
    <strong>Example input sent to Cloud Run:</strong>
    <ul class="points">
      <li>Stars: 4.5</li>
      <li>Log reviews: 5.3</li>
      <li>Average sentiment: 0.27</li>
      <li>Average complaints: 0.12</li>
      <li>Delivery presence: 1</li>
      <li>UberEats score: 4.6</li>
      <li>UberEats ratings: 500</li>
      <li>Price level: 2</li>
    </ul>
  </div>

  <div class="callout">
    <strong>Prediction result from Cloud Run:</strong>
    <p id="prediction-output">Loading prediction...</p>
  </div>
</section>
    <section id="panel-appendix" class="panel card" role="tabpanel">
      <h2>Appendix (notebook figures)</h2>
      <div class="rule"></div>
      <h3 style="margin-top: 1.25rem; font-family: var(--font-display);">Figures (part 1)</h3>
      {analytics_html}
      <h3 style="margin-top: 1.25rem; font-family: var(--font-display);">Figures (part 2)</h3>
      {prelim_html}
    </section>
  </div>
</div>
<script>
(function () {{
  var buttons = document.querySelectorAll(".nav-btn");
  var panels = document.querySelectorAll(".panel");
  buttons.forEach(function (btn) {{
    btn.addEventListener("click", function () {{
      var tab = btn.getAttribute("data-tab");
      buttons.forEach(function (b) {{ b.classList.toggle("active", b === btn); }});
      panels.forEach(function (p) {{
        p.classList.toggle("active", p.id === "panel-" + tab);
      }});
    }});
  }});

  var select = document.getElementById("interactive-select");
  var frame = document.getElementById("interactive-frame");
  function setInteractive(name) {{
    if (!select || !frame) return;
    if (!name) {{
      frame.removeAttribute("src");
      return;
    }}
    frame.setAttribute("src", "/assets/interactive/" + name);
  }}
  if (select) {{
    select.addEventListener("change", function () {{
      setInteractive(select.value);
    }});
    var def = select.getAttribute("data-default") || "";
    if (def && !select.value) {{
      select.value = def;
    }}
    var initial = select.value || def;
    if (initial) {{
      setInteractive(initial);
    }}
  }}
  var predictionOutput = document.getElementById("prediction-output");

if (predictionOutput) {{
  fetch("/predict-example")
    .then(function(response) {{
      return response.json();
    }})
    .then(function(data) {{
      if (data.error) {{
        predictionOutput.textContent = "Error: " + data.error;
      }} else {{
        var status = data.prediction === 1 ? "Open" : "Closed";
        var probability = (data.probability_open * 100).toFixed(1);
        predictionOutput.textContent =
          "Predicted Status: " + status +
          " | Probability Open: " + probability + "%";
      }}
    }})
    .catch(function(error) {{
      predictionOutput.textContent = "Could not load prediction.";
    }});
}}
}})();
</script>
</body></html>"""


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
_cached_key: tuple[float, float] | None = None


def _get_ipynb_report() -> str | None:
    global _cached_html, _cached_key
    nb = _find_notebook()
    if nb is None:
        return None
    nb_mtime = nb.stat().st_mtime
    iv_mtime = _interactive_signature()
    key = (nb_mtime, iv_mtime)
    if _cached_html is not None and _cached_key == key:
        return _cached_html
    _cached_html = _notebook_to_html(nb)
    _cached_key = key
    return _cached_html


app = Flask(__name__, static_folder=str(STATIC), static_url_path="/assets")
server = app


@app.route("/assets/<path:filename>")
def assets(filename: str):
    """
    App Engine deployments sometimes have assets at the repo root (not under static/).
    Prefer static/, but fall back to BASE/ to avoid broken images.
    """
    static_path = STATIC / filename
    if static_path.is_file():
        return send_from_directory(STATIC, filename)
    base_path = BASE / filename
    if base_path.is_file():
        return send_from_directory(BASE, filename)
    # Let Flask return a 404 (consistent with static behavior)
    return Response("Not found", status=404, mimetype="text/plain")

@app.route("/predict-example")
def predict_example():
    payload = {
        "log_reviews": 5.3,
        "stars": 4.5,
        "avg_sentiment": 0.27,
        "avg_complaints": 0.12,
        "delivery_presence": 1,
        "ubereats_score": 4.6,
        "ubereats_ratings": 500,
        "price_level": 2
    }

    try:
        response = requests.post(INFERENCE_URL, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
       
@app.route("/")
def index():
    static_index = STATIC / "index.html"
    if static_index.is_file() and _is_probably_html(static_index):
        return send_from_directory(STATIC, "index.html")
    base_index = BASE / "index.html"
    if base_index.is_file() and _is_probably_html(base_index):
        return send_from_directory(BASE, "index.html")
    html = _get_ipynb_report()
    if html is None:
        return Response(
            (
                "<h1>No report found</h1>"
                "<p>Add either:</p><ul>"
                "<li><code>static/index.html</code> or <code>index.html</code> next to <code>app.py</code> "
                "(real HTML only — not a notebook saved with the wrong extension), or</li>"
                "<li>your notebook as <code>cs163prject.ipynb</code> or "
                "<code>cs163prject (1).ipynb</code> in this folder (or set "
                "<code>NOTEBOOK_PATH</code>).</li>"
                "</ul>"
            ),
            mimetype="text/html",
            status=404,
        )
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
