# Documentation Change Detection System

Compares two versions of the same Node.js documentation page and reports
additions, removals and modifications. All structure is discovered from the
DOM at runtime -- no headings, section names or API names are hardcoded.

## Pipeline

```
URL -> crawler (Playwright) -> extractor -> snapshot.json
                                                 |
                          old snapshot ----+----- new snapshot
                                           v
                                      comparator   (reads snapshots only)
                                           v
                                   reports (JSON + Markdown)
```

The comparator never accesses the network; it reads only snapshot files.

## Components

| Folder        | Responsibility |
| ------------- | -------------- |
| `crawler/`    | Load the page with Playwright; retries; resource blocking. |
| `extractor/`  | DOM walker + snapshot builder (sections, hashes, signatures, validation). |
| `comparator/` | Snapshot-vs-snapshot diff (hash fast-path, id + fuzzy matching). |
| `reports/`    | Render the change set as JSON and Markdown. |
| `snapshots/`  | Persisted snapshot JSON. |
| `config.py`   | URLs, selectors, thresholds (no content). |
| `pipeline.py` | Orchestration shared by the CLI and the app (single source of truth). |
| `main.py`     | CLI presenter over `pipeline.run_pipeline`. |
| `app.py`      | Streamlit demo UI (Phase 3) on top of the pipeline. |

## Snapshot shape

```jsonc
{
  "requested_url": "...",
  "resolved_url": "...",
  "resolved_version": "v25.0.0",
  "title": "...",
  "captured_at": "<iso8601>",
  "content_hash": "<sha256 of normalized content>",
  "stats": { "headings_found": 0, "paragraphs_found": 0, "...": 0 },
  "api_signatures": [ { "name": "...", "params": "...", "signature": "...", "section_id": "..." } ],
  "elements": [ { "type": "heading", "level": 2, "text": "...", "html": "...", "id": "..." } ],
  "sections": [ { "id": "...", "heading": "...", "html": "...", "text": "...", "hash": "...", "api_signatures": [] } ]
}
```

`elements` preserves document order; each `section` stores raw `html` and
extracted `text` plus a `sha256` content hash used to skip unchanged sections.

## Setup & run

```powershell
pip install -r requirements.txt
playwright install chromium
python main.py
```

Outputs:
- `snapshots/snapshot_old_<version>.json`, `snapshots/snapshot_new_<version>.json`
- `reports/output/change_report.json`, `reports/output/change_report.md`

## Validation

Before a snapshot is written it must pass: `headings_found > 0`,
`paragraphs_found > 0`, `content_length > threshold`. Otherwise extraction
fails and no snapshot is produced (the selectors likely broke).

## Streamlit demo (`app.py`)

A web UI that sits on top of the existing pipeline -- it does not reimplement
any extraction or comparison logic, it calls `pipeline.run_pipeline` and
renders the result. Every value shown comes from the snapshots / change set.

Features: version overview with metadata deltas, summary metric cards
(added / modified / removed sections, added / removed APIs), a **Run
Comparison** button that regenerates fresh snapshots, tabs for
**Added / Modified / Removed / API Changes** (modified shows old vs new
content plus a unified `diff`), a sidebar snapshot inspector, an extraction
**validation** panel, and a **How It Works** architecture section.

### Run locally

```powershell
pip install -r requirements.txt
playwright install chromium
streamlit run app.py
```

The app opens at http://localhost:8501. On first load it shows the most
recent snapshots already on disk; click **Run Comparison** to scrape both
URLs live. If extraction fails validation, the app shows
"No valid snapshot generated." with the validation details rather than
crashing.

### Deploy to Streamlit Community Cloud

1. Push the project to a public GitHub repo.
2. On https://share.streamlit.io create a new app pointing at `app.py` on the
   default branch.
3. Cloud reads `requirements.txt` (pip) and `packages.txt` (the apt libraries
   Chromium needs, already included).
4. Playwright's Chromium binary is downloaded at runtime: `app.py` calls
   `playwright install chromium` once per session (cached via
   `st.cache_resource`), so no build hook is required.

Notes:
- The first run on a cold cloud instance is slow (browser download) and then
  caches.
- Live scraping needs `nodejs.org` / `r2.nodejs.org` to be reachable from the
  host. Because the repo ships pre-generated snapshots in `snapshots/`, the
  app still renders a full comparison on load even if outbound scraping is
  blocked -- only the **Run Comparison** button needs network.

### Suggested README screenshots

Capture these from a running app for the portfolio README:
1. **Hero** -- title, subtitle, summary metric cards, version overview.
2. **Modified tab** -- a section expander open showing the old-vs-new columns
   and the unified `diff` (e.g. the FFI addition in *Permission Model*).
3. **API Changes tab** -- the added signatures list.
4. **Sidebar snapshot inspector** -- the JSON metadata + extraction stats.
5. **How It Works** -- the architecture diagram expanded.
