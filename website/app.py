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
INTERACTIVE = STATIC / "interactive"

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
    interactive_files = sorted([p.name for p in INTERACTIVE.glob("*.html")]) if INTERACTIVE.is_dir() else []
    interactive_options = "".join([f'<option value="{name}">{name}</option>' for name in interactive_files])
    interactive_block = (
        f"""
        <div class="callout">
          <strong>How to add interactive graphs.</strong>
          Export any Plotly chart to a standalone HTML file and place it in <code>static/interactive/</code>.
          Files found: <strong>{len(interactive_files)}</strong>.
        </div>
        <div class="interactive-controls">
          <label for="interactive-select"><strong>Select a figure</strong></label>
          <select id="interactive-select" {'disabled' if not interactive_files else ''}>
            {interactive_options if interactive_files else '<option value="">No interactive files found</option>'}
          </select>
        </div>
        <div class="interactive-frame-wrap">
          <iframe id="interactive-frame" title="Interactive figure" src="" loading="lazy" referrerpolicy="no-referrer"></iframe>
        </div>
        """
        if True
        else ""
    )

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
</style></head><body>
<header class="hero">
  <p class="kicker">CS163 · Data-driven report</p>
  <h1>Yelp Restaurant Open vs. Closed Analysis</h1>
  <p class="subtitle">Which observable Yelp (and optional delivery-platform) signals are associated with whether a restaurant is <strong>open</strong> or <strong>closed</strong> in the dataset?</p>
  <nav class="nav" aria-label="Report sections">
    <button type="button" class="nav-btn active" data-tab="landing">Landing</button>
    <button type="button" class="nav-btn" data-tab="objectives">Project objectives</button>
    <button type="button" class="nav-btn" data-tab="methods">Analytical methods</button>
    <button type="button" class="nav-btn" data-tab="findings">Major findings</button>
    <button type="button" class="nav-btn" data-tab="interactive">Interactive</button>
    <button type="button" class="nav-btn" data-tab="appendix">Appendix (notebook figures)</button>
  </nav>
</header>
<p class="meta">CS163 · Spring 2026 · Live view from <strong>{nb_name}</strong> (embedded chart outputs + static visuals)</p>
<div class="wrap">
  <div class="panels">
    <section id="panel-landing" class="panel card active" role="tabpanel">
      <h2>Landing page</h2>
      <div class="rule"></div>
      <p class="lead">This site summarizes our work on predicting restaurant “survival” (open vs. closed) using the <strong>Yelp Open Dataset</strong> and optional delivery-platform signals.</p>
      <div class="two-col">
        <div>
          <p>We study whether easily observed signals—like <strong>review volume</strong>, <strong>star ratings</strong>, and <strong>review-text sentiment</strong>—are associated with a restaurant being open (<code>is_open=1</code>) or closed (<code>is_open=0</code>) in the dataset snapshot.</p>
          <div class="callout">
            <strong>Key insights (preliminary).</strong>
            <ul class="points">
              <li><strong>Review volume matters:</strong> restaurants with more reviews are more likely to be open.</li>
              <li><strong>Ratings matter less than expected:</strong> star distributions overlap heavily between open/closed businesses.</li>
              <li><strong>Sentiment is statistically different but weak:</strong> average sentiment has limited predictive power by itself.</li>
              <li><strong>Delivery-platform data can help slightly</strong> (optional extension) when combined with Yelp signals.</li>
            </ul>
          </div>
        </div>
        <div>
          <figure class="figure">
            <img src="/assets/viz_core.png" alt="Core visualization"/>
            <figcaption class="figure-caption">Core results visualization (static).</figcaption>
          </figure>
        </div>
      </div>
      <p class="muted">If you’re currently building the model-comparison visualization, you can export it as a PNG into <code>static/</code> (for a static embed) or as a Plotly HTML file into <code>static/interactive/</code> (for an interactive embed).</p>
      <div class="callout">
        <strong>Research question.</strong> Which observable Yelp signals (ratings, engagement, text sentiment, complaint language) are associated with restaurants being open vs. closed in the dataset?
      </div>
    </section>
    <section id="panel-objectives" class="panel card" role="tabpanel">
      <h2>Project objectives</h2>
      <div class="rule"></div>
      <p class="lead">Problem statement: this project investigates which factors are associated with whether a restaurant is <strong>open</strong> or <strong>closed</strong> in the dataset.</p>
      <p><strong>Data sources.</strong> Primary source is the <strong>Yelp Open Dataset</strong> (business + reviews). Optional extension is merging delivery-platform (e.g., UberEats-style) availability via approximate matching on normalized name/address.</p>
      <ul class="points">
        <li><strong>Unit of analysis</strong>: one row per restaurant (<code>business_id</code>).</li>
        <li><strong>Target variable</strong>: <code>is_open</code> (1 = open, 0 = closed).</li>
        <li><strong>Goal</strong>: identify which features differ between open and closed restaurants, then evaluate simple predictive models.</li>
      </ul>
      <div class="callout">
        <strong>Hypotheses (high level).</strong>
        We test whether open restaurants tend to have (1) higher star ratings, (2) more reviews, and (3) more positive average sentiment.
      </div>
    </section>
    <section id="panel-methods" class="panel card" role="tabpanel">
      <h2>Analytical methods</h2>
      <div class="rule"></div>
      <p class="lead">We combine filtering + feature engineering with statistical tests and a baseline ML classifier.</p>
      <ul class="points">
        <li><strong>Data processing</strong>: filter businesses to restaurants; restrict analyses to restaurants with ≥ 50 reviews for stable text aggregates; normalize names/addresses for Yelp↔delivery-platform matching (optional).</li>
        <li><strong>Feature engineering</strong>:
          <ul class="points">
            <li><code>log_reviews</code>: log(1 + review_count)</li>
            <li><code>avg_sentiment</code>: average review sentiment (e.g., VADER compound)</li>
            <li><code>avg_complaints</code>: simple complaint-token frequency/rate (dictionary-based)</li>
            <li><code>delivery_presence</code>: indicator for presence on delivery platform (optional)</li>
          </ul>
        </li>
        <li><strong>Statistical methods</strong>: two-sample t-tests (numeric features), chi-square tests (categorical associations where relevant).</li>
        <li><strong>Machine learning</strong>: logistic regression classifier with evaluation metrics <strong>accuracy</strong>, <strong>F1</strong>, and <strong>ROC-AUC</strong>.</li>
      </ul>
      <div class="callout">
        <strong>Cloud data storage?</strong>
        If you keep the full Yelp JSON locally for analysis, the web app should ship only <em>outputs</em> (plots + small derived tables).
        If you want the site to query data live, a good next step is storing aggregated features in a managed service (e.g., BigQuery / Cloud SQL) and serving only the filtered restaurant-level table to the app.
      </div>
    </section>
    <section id="panel-findings" class="panel card" role="tabpanel">
      <h2>Major findings</h2>
      <div class="rule"></div>
      <p class="lead">Preliminary results from our hypothesis tests (from the submitted report draft).</p>
      <h3 style="margin-top: 1.25rem; font-family: var(--font-display);">Hypothesis 1: Open restaurants have higher average Yelp star ratings.</h3>
      <ul class="points">
        <li><strong>Result</strong>: t-test (t = 11.94), (p &lt; 0.001).</li>
        <li><strong>Interpretation</strong>: statistically significant difference, but distributions overlap heavily; ratings alone are a weak separator.</li>
      </ul>
      <h3 style="margin-top: 1.25rem; font-family: var(--font-display);">Hypothesis 2: Restaurants with more reviews are more likely to be open.</h3>
      <ul class="points">
        <li><strong>Result</strong>: t-test (t = 22.86), (p &lt; 0.001).</li>
        <li><strong>Interpretation</strong>: open restaurants have higher median and overall review-count distribution; engagement is a stronger signal.</li>
      </ul>
      <h3 style="margin-top: 1.25rem; font-family: var(--font-display);">Hypothesis 3: Restaurants with more positive average sentiment are more likely to be open.</h3>
      <ul class="points">
        <li><strong>Result</strong>: t-test (t = 6.97), (p &lt; 0.001); correlation (≈ 0.049).</li>
        <li><strong>Interpretation</strong>: sentiment differs slightly but is weakly related to status; limited predictive power alone.</li>
      </ul>
      <div class="two-col" style="margin-top: 1.5rem;">
        <figure class="figure">
          <img src="/assets/viz_text.png" alt="Text/sentiment visualization"/>
          <figcaption class="figure-caption">Text-based results visualization (static).</figcaption>
        </figure>
        <figure class="figure">
          <img src="/assets/viz_core.png" alt="Core visualization"/>
          <figcaption class="figure-caption">Core results visualization (static).</figcaption>
        </figure>
      </div>
      <p class="muted" style="margin-top: 1rem;">You can replace these static images with interactive versions by exporting Plotly HTML into <code>static/interactive/</code> and using the Interactive tab.</p>
    </section>
    <section id="panel-interactive" class="panel card" role="tabpanel">
      <h2>Interactive diagram</h2>
      <div class="rule"></div>
      <p class="muted">If you export interactive figures (Plotly) as standalone HTML, this page will automatically list and render them.</p>
      {interactive_block}
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
    if (select.value) {{
      setInteractive(select.value);
    }}
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
