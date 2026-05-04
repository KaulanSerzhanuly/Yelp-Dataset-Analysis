"""
CS163 project web view: Yelp-themed tabbed report built from notebook chart outputs.

1) Optional: static/index.html (notebook exported as HTML from Colab/Jupyter).
2) Otherwise: reads .ipynb — skips markdown, code source, streams, errors, and
   non-image outputs; figures appear under Analytics / Preliminary Results tabs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from flask import Flask, Response, send_from_directory

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

_DEFAULT_NAMES = [
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
</style></head><body>
<header class="hero">
  <p class="kicker">CS163 · Data-driven report</p>
  <h1>Yelp Restaurant Open vs. Closed Analysis</h1>
  <p class="subtitle">Exploring ratings, review volume, and review text signals linked to whether a restaurant is open in the Yelp Open Dataset.</p>
  <nav class="nav" aria-label="Report sections">
    <button type="button" class="nav-btn active" data-tab="overview">Overview</button>
    <button type="button" class="nav-btn" data-tab="dataset">Dataset</button>
    <button type="button" class="nav-btn" data-tab="methods">Methods</button>
    <button type="button" class="nav-btn" data-tab="analytics">Analytics</button>
    <button type="button" class="nav-btn" data-tab="results">Preliminary results</button>
  </nav>
</header>
<p class="meta">CS163 · Spring 2026 · Live view from <strong>{nb_name}</strong> (chart outputs only)</p>
<div class="wrap">
  <div class="panels">
    <section id="panel-overview" class="panel card active" role="tabpanel">
      <h2>Project overview</h2>
      <div class="rule"></div>
      <p class="lead">This report summarizes exploratory work on the <strong>Yelp Open Dataset</strong>, focused on restaurants and the binary <strong>is_open</strong> label (open vs. closed at the time of the snapshot).</p>
      <p>We connect structured business fields—such as star ratings and review counts—to patterns in review text, including sentiment and simple “complaint” word rates for businesses with enough reviews. The goal is descriptive: highlight factors that differ between open and closed listings, and support later modeling (for example logistic regression with held-out evaluation).</p>
      <div class="callout">
        <strong>Research question.</strong> Which observable Yelp signals (ratings, engagement, text sentiment, complaint language) are associated with restaurants being open vs. closed in the dataset?
      </div>
    </section>
    <section id="panel-dataset" class="panel card" role="tabpanel">
      <h2>Dataset</h2>
      <div class="rule"></div>
      <p>Primary source is the <strong>Yelp Open Dataset</strong> (business and review JSON). Businesses are filtered to those whose categories include “Restaurant.” Review-based features use reviews tied to each business; analyses that require stable text summaries often restrict to restaurants with at least a minimum review count.</p>
      <p>An optional extension (not required for this page) is to merge in <strong>UberEats</strong>-style marketplace fields by matching on normalized name and address to study whether delivery-platform signals add predictive value beyond Yelp alone.</p>
      <ul class="points">
        <li><strong>Unit of analysis:</strong> one row per restaurant (<code>business_id</code>).</li>
        <li><strong>Outcome:</strong> <code>is_open</code> (1 = open, 0 = closed).</li>
        <li><strong>Key predictors:</strong> stars, review count, text sentiment (e.g. VADER compound), complaint-token rate.</li>
      </ul>
    </section>
    <section id="panel-methods" class="panel card" role="tabpanel">
      <h2>Methods</h2>
      <div class="rule"></div>
      <p>Code in the notebook loads JSON lines, cleans and filters the restaurant subset, and builds aggregates from reviews where needed. Text sentiment uses a lightweight lexicon model; complaint frequency can be defined as the rate of occurrence of a small dictionary of negative-service terms in review text.</p>
      <p>For classification-style questions, a common approach is a <strong>scikit-learn</strong> pipeline: numeric scaling, optional one-hot encoding for geography, and <strong>logistic regression</strong> with <code>class_weight</code> to mitigate imbalance, evaluated with <strong>F1</strong> and <strong>ROC-AUC</strong> on a train/test split.</p>
      <p class="muted">Figures below are rendered from the latest saved matplotlib (or similar) outputs embedded in the notebook.</p>
    </section>
    <section id="panel-analytics" class="panel card" role="tabpanel">
      <h2>Analytics</h2>
      <div class="rule"></div>
      <p class="muted">First half of embedded figures from the notebook (execution order).</p>
      {analytics_html}
    </section>
    <section id="panel-results" class="panel card" role="tabpanel">
      <h2>Preliminary results</h2>
      <div class="rule"></div>
      <p class="muted">Remaining figures from the notebook. Interpret alongside class balance and snapshot timing—correlation is not causation.</p>
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
