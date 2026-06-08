"""
Central configuration for the Documentation Change Detection System.

This file holds ONLY configuration: URLs, selectors, paths, timeouts and
validation thresholds. It contains no documentation content -- no headings,
section names, API names or expected changes. Everything about the documents
themselves is discovered at runtime from the DOM.

Scope: this project supports exactly two pages, both generated from the same
Node.js documentation template, so template-specific selectors are safe to use.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
REPORTS_DIR = BASE_DIR / "reports" / "output"

# --------------------------------------------------------------------------- #
# Supported pages (same Node.js doc template -> shared selectors are reliable)
# --------------------------------------------------------------------------- #
OLD_URL = "https://r2.nodejs.org/dist/v25.0.0/docs/api/permissions.html"
NEW_URL = "https://nodejs.org/docs/latest/api/permissions.html"

# --------------------------------------------------------------------------- #
# Extraction selectors
#
# CONTENT_ROOT scopes everything to the documentation body, automatically
# excluding the global module sidebar and other navigation chrome.
# BLOCK_SELECTOR enumerates the block-level elements we treat as content.
# --------------------------------------------------------------------------- #
CONTENT_ROOT = "#apicontent"
BLOCK_SELECTOR = "h1, h2, h3, h4, h5, h6, p, pre, table, ul, ol"

# --------------------------------------------------------------------------- #
# Crawler (Playwright) settings
# --------------------------------------------------------------------------- #
NAV_TIMEOUT_MS = 30000
WAIT_UNTIL = "domcontentloaded"          # content is server-rendered; no need for networkidle
MAX_RETRIES = 3
RETRY_BACKOFF_S = 2.0
HEADLESS = True

# Block heavy, irrelevant resources to speed up loads.
BLOCKED_RESOURCE_TYPES = {"image", "font", "stylesheet", "media"}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 DocsChangeDetector/1.0"
)

# --------------------------------------------------------------------------- #
# Extraction validation thresholds.
#
# If a snapshot fails these checks the extraction is considered broken
# (e.g. a selector stopped matching) and NO snapshot is written.
# --------------------------------------------------------------------------- #
MIN_HEADINGS = 1
MIN_PARAGRAPHS = 1
MIN_CONTENT_LENGTH = 500

# --------------------------------------------------------------------------- #
# Comparator
#
# When a section's anchor id changes (because its heading was reworded), we
# fall back to fuzzy heading matching. A ratio at/above this threshold is
# treated as the same section, modified -- rather than remove + add.
# --------------------------------------------------------------------------- #
HEADING_MATCH_RATIO = 0.6
