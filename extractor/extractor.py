"""
Extractor: turns raw DOM blocks into a structured, order-preserving snapshot.

Responsibilities (single):
  * Define WHAT counts as content (the DOM walker + selectors).
  * Build the snapshot: ordered elements, sections, hashes, API signatures,
    extraction statistics and resolved version.
  * Validate the extraction before a snapshot is allowed to exist.

It does NOT drive the browser (that is the crawler) and does NOT compare
snapshots (that is the comparator).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone

# --------------------------------------------------------------------------- #
# DOM walker
#
# Runs inside the page. Collects the *top-level* block elements within the
# content root in document order. "Top-level" means a block that is not nested
# inside another captured block -- so a <ul> inside an <li>, or a <p> inside an
# <li>, is captured once as part of its outer block, never twice.
#
# For each block it returns:
#   type      heading | paragraph | code | table | list
#   level     heading depth (1-6) or null
#   language  code language from `language-*` class, or null
#   id        anchor slug (from the heading's `a.mark` / element id), or null
#   text      cleaned text (whitespace-collapsed; code keeps its line breaks)
#   html      raw outerHTML (kept for debugging / validation)
# --------------------------------------------------------------------------- #
DOM_WALKER_JS = r"""
(args) => {
  const root = document.querySelector(args.root);
  if (!root) return { title: document.title, elements: null };

  const blockSel = args.blocks;
  const isBlock = (el) => el.matches(blockSel);

  const all = Array.from(root.querySelectorAll(blockSel));

  // Keep only blocks with no block ancestor inside the root.
  const topLevel = all.filter((el) => {
    let p = el.parentElement;
    while (p && p !== root) {
      if (isBlock(p)) return false;
      p = p.parentElement;
    }
    return true;
  });

  const elements = topLevel.map((el) => {
    const tag = el.tagName.toLowerCase();
    let type, level = null, language = null;

    if (/^h[1-6]$/.test(tag)) {
      type = "heading";
      level = parseInt(tag.substring(1), 10);
    } else if (tag === "p") {
      type = "paragraph";
    } else if (tag === "pre") {
      type = "code";
      const code = el.querySelector("code");
      if (code) {
        const m = (code.className || "").match(/language-([\w-]+)/);
        if (m) language = m[1];
      }
    } else if (tag === "table") {
      type = "table";
    } else {
      type = "list";
    }

    // Anchor id: the heading's `a.mark` carries the stable slug.
    const mark = el.querySelector("a.mark, a[id]");
    const id = el.id || (mark ? mark.id : null) || null;

    // Clean text: drop UI chrome before reading text -- the trailing "#"
    // anchor link and the per-snippet copy buttons (which the doc template
    // renders with a language label, e.g. "bashcopy"). Prose is never inside
    // these elements, so removing them is safe.
    const clone = el.cloneNode(true);
    clone
      .querySelectorAll("a.mark, .code-toolbar, button")
      .forEach((node) => node.remove());

    let text;
    if (type === "code") {
      // Read only the inner <code>, excluding the copy button and language
      // label that the doc template renders inside <pre> as UI chrome.
      const code = clone.querySelector("code") || clone;
      text = code.textContent.replace(/^\n+/, "").replace(/\n+$/, "");
    } else {
      text = clone.textContent.replace(/\s+/g, " ").trim();
    }

    return { type, level, language, id, text, html: el.outerHTML };
  });

  return { title: document.title, elements };
}
"""


class ExtractionError(Exception):
    """Raised when extraction fails validation; no snapshot should be written."""


# Matches a documented API signature, e.g. `permission.has(scope[, reference])`.
# Captures the dotted name and the raw parameter list.
_SIGNATURE_RE = re.compile(r"([A-Za-z_$][\w$.]*)\s*\(([^()]*)\)")


def _normalize(text: str) -> str:
    """Unicode-normalize and collapse whitespace for stable hashing/diffing."""
    text = unicodedata.normalize("NFC", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").lower()
    text = re.sub(r"[^\w]+", "-", text).strip("-")
    return text


def _resolve_version(title: str | None, resolved_url: str | None) -> str:
    """Discover the version string from the page title, falling back to the URL."""
    for source in (title or "", resolved_url or ""):
        m = re.search(r"v\d+\.\d+\.\d+", source)
        if m:
            return m.group(0)
    return "unknown"


def _extract_signatures(text: str) -> list[dict]:
    """Pull API signatures out of a heading's text."""
    sigs = []
    for name, params in _SIGNATURE_RE.findall(text or ""):
        params = params.strip()
        sigs.append(
            {
                "name": name,
                "params": params,
                "signature": f"{name}({params})",
            }
        )
    return sigs


def _build_sections(elements: list[dict]) -> list[dict]:
    """Group ordered elements into sections, each starting at a heading."""
    sections: list[dict] = []
    current: dict | None = None
    index = 0

    def finalize(sec: dict) -> dict:
        text = "\n".join(p for p in sec["_text_parts"] if p)
        html = "\n".join(sec["_html_parts"])
        return {
            "id": sec["id"],
            "heading": sec["heading"],
            "level": sec["level"],
            "html": html,
            "text": text,
            "hash": _sha256(_normalize(text)),
            "api_signatures": sec["signatures"],
        }

    for el in elements:
        if el["type"] == "heading":
            if current is not None:
                sections.append(finalize(current))
            sec_id = el["id"] or _slugify(el["text"]) or f"__section_{index}"
            current = {
                "id": sec_id,
                "heading": el["text"],
                "level": el["level"],
                "signatures": _extract_signatures(el["text"]),
                "_text_parts": [el["text"]],
                "_html_parts": [el["html"]],
            }
            index += 1
        else:
            if current is None:
                # Content before the first heading (preamble).
                current = {
                    "id": "__preamble",
                    "heading": None,
                    "level": None,
                    "signatures": [],
                    "_text_parts": [],
                    "_html_parts": [],
                }
            current["_text_parts"].append(el["text"])
            current["_html_parts"].append(el["html"])

    if current is not None:
        sections.append(finalize(current))
    return sections


def _collect_signatures(sections: list[dict]) -> list[dict]:
    """Deduplicate API signatures across sections (high-value change targets)."""
    seen: dict[str, dict] = {}
    for sec in sections:
        for sig in sec["api_signatures"]:
            key = sig["signature"]
            if key not in seen:
                seen[key] = {**sig, "section_id": sec["id"]}
    return sorted(seen.values(), key=lambda s: s["signature"])


def build_snapshot(requested_url: str, resolved_url: str, raw: dict) -> dict:
    """
    Build a validated snapshot from raw DOM data.

    Raises ExtractionError if the page yielded too little content, in which
    case the caller must NOT persist a snapshot.
    """
    elements = raw.get("elements")
    title = raw.get("title")

    if elements is None:
        raise ExtractionError(
            f"Content root not found on page (selector matched nothing): {requested_url}"
        )

    sections = _build_sections(elements)
    api_signatures = _collect_signatures(sections)

    # Statistics (proof of extraction).
    full_text = "\n".join(el["text"] for el in elements)
    stats = {
        "headings_found": sum(1 for e in elements if e["type"] == "heading"),
        "paragraphs_found": sum(1 for e in elements if e["type"] == "paragraph"),
        "code_blocks_found": sum(1 for e in elements if e["type"] == "code"),
        "tables_found": sum(1 for e in elements if e["type"] == "table"),
        "lists_found": sum(1 for e in elements if e["type"] == "list"),
        "sections_found": len(sections),
        "signatures_found": len(api_signatures),
        "elements_found": len(elements),
        "content_length": len(full_text),
    }

    _validate(stats, requested_url)

    return {
        "requested_url": requested_url,
        "resolved_url": resolved_url,
        "resolved_version": _resolve_version(title, resolved_url),
        "title": title,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": _sha256(_normalize(full_text)),
        "stats": stats,
        "api_signatures": api_signatures,
        "elements": elements,        # document order preserved
        "sections": sections,
    }


def _validate(stats: dict, url: str) -> None:
    """Fail loudly if extraction looks broken."""
    from config import MIN_HEADINGS, MIN_PARAGRAPHS, MIN_CONTENT_LENGTH

    problems = []
    if stats["headings_found"] < MIN_HEADINGS:
        problems.append(
            f"headings_found={stats['headings_found']} < {MIN_HEADINGS}"
        )
    if stats["paragraphs_found"] < MIN_PARAGRAPHS:
        problems.append(
            f"paragraphs_found={stats['paragraphs_found']} < {MIN_PARAGRAPHS}"
        )
    if stats["content_length"] < MIN_CONTENT_LENGTH:
        problems.append(
            f"content_length={stats['content_length']} < {MIN_CONTENT_LENGTH}"
        )

    if problems:
        raise ExtractionError(
            "FAIL EXTRACTION for {url}: ".format(url=url) + "; ".join(problems)
        )
