# InsightBot

A rule-based (non-ML) multilingual news extraction pipeline and dashboard.
Fetches raw HTML from a configured list of English/Arabic/Russian
news/blog URLs, extracts `{title, body, date}` with a pattern-matching
heuristic engine, stores results to JSON/CSV plus an optional MongoDB or
MySQL database, exposes a Flask REST API + server-rendered UI with
admin-approved accounts, and exports aggregate stats for a Tableau
dashboard.

**Live demo:** https://insightbot-sandy.vercel.app
(deployed on Vercel; the user/bookmark database runs on ephemeral
serverless storage there, so registrations and bookmarks may reset
between requests -- see [Deployment](#deployment) below.)

**Out of scope (explicitly not implemented):** sentiment analysis, fake
news detection, machine translation. The extraction engine is
rule-based throughout -- no ML/NLP models are used to identify
title/body/date.

---

## Architecture

```
config/
  sites.yaml               40 training + 10 held-out site URLs (language-tagged)
  extraction_rules.yaml    optional per-domain CSS-selector overrides

insightbot/
  ingestion/       fetcher.py (requests, default) + scrapy_crawler.py (optional
                    fallback for link discovery) -> raw_store.py (HTML + metadata to disk)
  preprocessing/    cleaner.py: strip script/style/nav/ads/boilerplate,
                    normalize unicode (NFC) + whitespace
  extraction/       rules.py: the rule engine (title/body/date heuristics)
                    domain_rules.py: loads extraction_rules.yaml overrides
                    dates.py: EN/AR/RU date parsing
  storage/          json_csv_store.py (always-on flat files)
                    db_store.py (Mongo/MySQL writers + a uniform read
                    "repository" the API queries regardless of backend)
                    models.py (SQLAlchemy ORM model for the MySQL backend)
  evaluation/       evaluate.py: scores extraction vs. manual ground truth,
                    training set vs. held-out set
  scheduler/        scheduler.py: APScheduler daily cron-equivalent job
  api/              Flask app factory, JWT auth (register/login/admin-approve),
                    article list/search/detail endpoints, dashboard stats endpoint
  web/              Jinja templates + small vanilla-JS frontend (login,
                    register, article list w/ language filter + search, detail view)
  dashboard/        aggregate.py: computes/exports stats CSVs for Tableau
  pipeline.py       orchestrates ingestion -> preprocessing -> extraction -> storage

scripts/            run_pipeline.py, run_evaluation.py, init_db.py (CLI entry points)
tests/              pytest unit tests for cleaner + extraction rule engine
data/               raw/ (fetched HTML+metadata), processed/ (articles.json/csv),
                    exports/ (dashboard CSVs)
```

Each layer only talks to the layer(s) directly below it through plain
Python function calls / dataclasses -- there's no hidden coupling, so any
layer can be swapped (e.g. add a new storage backend) without touching
the others.

---

## Setup

Requires Python 3.11+ (developed against 3.11-3.14).

```bash
python -m venv venv
# Windows: venv\Scripts\activate       macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set INSIGHTBOT_ADMIN_EMAIL / INSIGHTBOT_ADMIN_PASSWORD at minimum,
# and INSIGHTBOT_SECRET_KEY to a real random string.
```

`scrapy`, `pymongo`, and `PyMySQL` in requirements.txt are optional --
the app runs fine without them as long as you don't use the Scrapy
crawler or set `INSIGHTBOT_DB_BACKEND=mongo`/`mysql`. If you don't need
them, feel free to remove those three lines before installing.

### Fill in real site URLs

Edit `config/sites.yaml` and replace the placeholder URLs under
`training:` (40 sites) and `held_out:` (10 sites) with real news/blog
article URLs, keeping the `language: en|ar|ru` tags accurate. The
`held_out` sites must be ones you never look at while adding entries to
`config/extraction_rules.yaml` -- that separation is what makes the
evaluation report in step 5 meaningful.

## Running

```bash
# 1. Initialize the user-auth DB + bootstrap the admin account
python scripts/init_db.py

# 2. Run one ingestion pass over the training sites (writes data/raw,
#    data/processed/articles.{json,csv}, and the configured DB backend)
python scripts/run_pipeline.py --group training

# 3. Start the API + web UI
python -m insightbot.api.app
# -> http://localhost:5000  (register, then have the admin approve you
#    via POST /api/auth/approve/<id>, or log in directly as the
#    bootstrap admin)

# 4. (optional) Start the daily scheduler as a long-lived process
python -m insightbot.scheduler.scheduler
# -- or use OS cron instead, see the docstring in
#    insightbot/scheduler/scheduler.py

# 5. Export dashboard stats for Tableau
python -m insightbot.dashboard.aggregate

# 6. Run the evaluation report (training vs. held-out accuracy)
python scripts/run_evaluation.py
```

### Tests

```bash
pytest tests/ -v
```

---

## Deployment

**Live:** https://insightbot-sandy.vercel.app

The web app (`insightbot/api/app.py`, Flask) is deployed to Vercel as a
Python serverless function:

- `api/index.py` -- entrypoint that imports and exposes `app`
- `api/requirements.txt` -- a trimmed dependency list (just the Flask
  stack + PyYAML; the ingestion side's `scrapy`/`pymongo`/`PyMySQL` are
  never imported by the web app, so they're left out of the deployed
  bundle)
- `vercel.json` -- routes every request to `api/index.py`
- `data/processed/articles.{json,csv}` are committed (force-added past
  `.gitignore`) so the live site has real seeded articles to show

Required production env vars (`vercel env add <NAME> production`):
`INSIGHTBOT_SECRET_KEY`, `INSIGHTBOT_ADMIN_EMAIL`,
`INSIGHTBOT_ADMIN_PASSWORD`, `INSIGHTBOT_DB_BACKEND=none`, and
`INSIGHTBOT_SQLALCHEMY_URI=sqlite:////tmp/insightbot_app.db`.

**Known limitation:** Vercel's Python runtime has a read-only filesystem
except `/tmp`, and `/tmp` is not shared across serverless instances or
persisted between cold starts. Article browsing/search/filters are
unaffected (that data ships with the deployment bundle), but the
user/bookmark SQLite database lives in `/tmp`, so registrations,
approvals, and bookmarks can reset unpredictably between requests. For
reliable auth in production, point `INSIGHTBOT_SQLALCHEMY_URI` at a real
hosted database (e.g. Postgres on Neon/Supabase) instead.

---

## How the extraction rules were derived

The engine is a **generic heuristic first**, with **per-domain overrides
as an escape hatch** -- not the other way around -- so it generalizes to
sites it has never seen (the whole point of the held-out evaluation set).

**Title.** Every `<h1>`/`<h2>` on the page is a candidate. Each is scored
by: tag weight (`h1` > `h2`), a bonus if its class/id contains
title-like hints (`title`, `headline`, `heading`), a bonus if it's
nested inside `<header>` or `<article>`, a small bonus for appearing
earlier in the document, and a length sanity filter (8-220 characters,
which rules out nav labels and full sentences accidentally marked up as
headings). The highest scorer wins. If no candidate survives, it falls
back to `<meta property="og:title">`, then the `<title>` tag with a
trailing `" | Site Name"` suffix stripped.

*Why this generalizes:* it never assumes a specific class name is
present -- the hints are a bonus, not a requirement -- so a completely
unseen site with a bare `<h1>Some Headline</h1>` and no classes at all
still gets extracted correctly (see `tests/test_extraction.py::test_generic_extraction_handles_unfamiliar_div_based_structure`).

**Body.** This was the hardest part to get right, because news sites'
"main content" `<div>` naming is completely inconsistent, while site
chrome (nav, related-articles rails, share widgets) reliably looks the
same in one specific way: **it has a lot of text inside `<a>` tags
relative to its total text.** So the engine:

1. Strips `<script>/<style>/<nav>/<footer>/<aside>/<form>` outright, and
   any element whose class/id matches a boilerplate keyword list (`nav`,
   `sidebar`, `related`, `comment`, `share`, `cookie`, etc.) -- built
   from inspecting the training-set sites' markup.
   `<header>` is deliberately **not** blanket-stripped, since
   `<article><header><h1>...` is the standard HTML5 pattern and
   stripping it would delete titles, not just chrome.
2. For every remaining `<p>`/`<div>` with >=25 characters of text and a
   link-density (`link_text_len / total_text_len`) under 0.5, computes a
   score from its length and a small bonus per comma (a cheap proxy for
   "this reads like prose, not a list of links"), and adds that score to
   its parent *and* (at half weight) grandparent container. This is a
   simplified version of the density-scoring idea behind
   Readability.js/Boilerpipe.
3. The container with the highest aggregate score is taken as the
   article body; its `<p>` children are joined in document order.
4. If nothing scores (e.g. a page with no `<p>` tags at all), it falls
   back to the single longest `<p>`/`<div>` text block on the page --
   the literal "longest contiguous block" rule from the original spec.

**Date.** Checked in order: a per-domain CSS override if configured;
then a fixed list of common structured tags
(`meta[property=article:published_time]`, `meta[name=pubdate]`,
`meta[itemprop=datePublished]`, `<time datetime>`, etc.); then a regex
scan of the page's visible text for ISO dates, `DD/MM/YYYY`, English
month names, Arabic month names (`٥ يناير ٢٠٢٦`, handles Arabic-Indic
digits), and Russian month names (`5 января 2026`). Returns `None`
rather than guessing when nothing matches.

**Per-domain overrides** (`config/extraction_rules.yaml`) exist for the
rare site where the generic heuristic gets it wrong -- e.g. a title
that's actually a styled `<div>` rather than a heading tag. They're
CSS selectors, tried first, with the generic heuristic as the automatic
fallback if the selector matches nothing (so a site redesign that breaks
a selector degrades gracefully instead of returning nothing).

### Assumptions made

- Article title is either a genuine heading tag (`h1`/`h2`) or, failing
  that, recoverable from `<title>`/`og:title` -- sites that render the
  title purely via client-side JS with no server-rendered fallback are
  out of scope (this is a static-HTML scraper, not a headless browser).
- "Body" means the main article prose; the density-scoring heuristic
  assumes prose paragraphs have low link density, which holds for
  articles but not, e.g., a page that's mostly a bulleted list of links
  (a "best of" roundup post would extract poorly).
- Dates are assumed to be the *publication* date; the regex scan doesn't
  try to distinguish a publish date from an "updated" date if both
  appear in visible text -- the first match wins.
- One canonical body per page: extraction is not paginated (a
  "continue reading on page 2" article only extracts page 1's content).

---

## Evaluation methodology

`insightbot/evaluation/evaluate.py` re-runs the exact same pipeline used
in production (`insightbot.pipeline.process_one`) against every URL that
has a matching entry in `insightbot/evaluation/ground_truth/{group}_ground_truth.json`,
and scores:

- **Title accuracy**: string-similarity ratio (`difflib.SequenceMatcher`,
  whitespace/case-normalized) >= 0.85 counts as correct.
- **Body accuracy**: same similarity metric, threshold 0.60 (bodies are
  long, so exact/near-exact match is too strict -- this checks the
  extracted text is substantially the right passage, not a boilerplate
  or wrong-section match).
- **Date accuracy**: exact match against the manually verified ISO date.

**The ground truth JSON files ship with placeholder entries.** Fill in
`insightbot/evaluation/ground_truth/training_ground_truth.json` and
`held_out_ground_truth.json` with the real title (exact) and the first
~200 characters of the real body (paste from the live page) for each URL
you added to `config/sites.yaml`, then run:

```bash
python scripts/run_evaluation.py
```

This prints a side-by-side accuracy report (training vs. held-out) and
writes the full per-site breakdown to `data/exports/evaluation_report.json`.
**A large accuracy gap between training and held-out is the signal to
watch** -- it means the heuristic (or your `extraction_rules.yaml`
overrides) overfit to the training sites' specific markup rather than
generalizing.

---

## Building the Tableau dashboard

`python -m insightbot.dashboard.aggregate` (or `POST /api/dashboard/export`
as an admin user) writes four flat CSVs to `data/exports/`:

| File | Columns | Use |
|---|---|---|
| `by_domain.csv` | `domain, article_count` | Bar chart: articles per source |
| `by_language.csv` | `language, article_count` | Pie/bar: EN vs AR vs RU volume |
| `by_date.csv` | `date, article_count` | Line chart: articles over time |
| `keyword_freq.csv` | `keyword, language, frequency` | Word-frequency bar chart or word cloud, per language |

To build the dashboard in Tableau Desktop:

1. **Connect** -> **Text File** -> select all four CSVs from `data/exports/`
   (Tableau will let you add them as separate data sources, or relate
   them via a blank join since they don't share a key -- treat them as
   independent sources feeding separate sheets).
2. Build one sheet per CSV:
   - `by_domain.csv`: horizontal bar, `domain` on Rows, `SUM(article_count)`
     on Columns, sorted descending.
   - `by_language.csv`: pie or bar chart, `language` as the dimension.
   - `by_date.csv`: line chart, `date` on Columns (set as a Date field),
     `SUM(article_count)` on Rows.
   - `keyword_freq.csv`: bar chart or word cloud, filter to one
     `language` at a time (use a filter/parameter to switch), `keyword`
     on Rows sorted by `SUM(frequency)` descending, top 20.
3. Combine all four sheets onto one **Dashboard** (New Dashboard), and
   add a language filter (from the `by_language` sheet, "Use as Filter")
   that cross-filters the keyword-frequency sheet.
4. To keep the dashboard current, re-run
   `python -m insightbot.dashboard.aggregate` after each ingestion run
   (or add it as a step at the end of the scheduled daily job) and hit
   **Refresh** on the Tableau data sources -- since they're plain CSVs,
   Tableau just re-reads the files, no extract republish needed unless
   you built a `.hyper` extract instead of a live connection.

---

## Non-functional targets

- **<5s/page**: `fetcher.py` uses a 5-second `requests` timeout
  (`INSIGHTBOT_REQUEST_TIMEOUT`) with retries capped, and
  `pipeline.process_one` records `elapsed_seconds` per site;
  `scripts/run_pipeline.py` flags any site that exceeded 5s in its
  summary output.
- **Graceful degradation**: every extraction stage (title/body/date) is
  independently try/excepted in `extraction/rules.py`'s
  `extract_article`, so one field failing never blocks the others; the
  whole pipeline (`pipeline.process_one`) has an outer guard so one bad
  site can never crash a batch run; `clean_soup` uses BeautifulSoup's
  tolerant `html.parser`, which doesn't raise on malformed markup.
- **Modularity**: see Architecture above -- ingestion, preprocessing,
  extraction, storage, API, and UI are separate packages with no
  circular imports.
