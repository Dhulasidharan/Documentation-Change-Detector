"""
Comparator: detects changes between two snapshots.

ISOLATION GUARANTEE: this module imports neither Playwright nor the crawler,
and never touches the network. It only reads snapshot JSON files. All change
detection is performed on previously generated snapshots.

Strategy:
  1. Whole-document fast path: equal content_hash  -> identical, no work.
  2. Match sections by anchor id; equal section hash -> skip the expensive diff.
  3. Unmatched sections: fuzzy-match by heading text (handles reworded
     headings) before declaring removed / added.
  4. API signatures are diffed separately as high-value changes.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path

from config import HEADING_MATCH_RATIO


def load_snapshot(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _preview(text: str, limit: int = 200) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit] + "..."


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()


def _unified(old: dict, new: dict) -> list[str]:
    return list(
        difflib.unified_diff(
            (old["text"] or "").splitlines(),
            (new["text"] or "").splitlines(),
            fromfile=f"old::{old.get('heading')}",
            tofile=f"new::{new.get('heading')}",
            lineterm="",
        )
    )


def _modified_entry(old: dict, new: dict, renamed: bool) -> dict:
    # A genuine rename means the heading TEXT changed -- not merely that the
    # anchor id differed (Node changed its id scheme between versions, so id
    # matching can miss while the text is identical).
    renamed = (old.get("heading") or "").strip() != (new.get("heading") or "").strip()
    return {
        "id": new.get("id"),
        "old_id": old.get("id"),
        "heading": new.get("heading"),
        "old_heading": old.get("heading"),
        "heading_renamed": renamed,
        "similarity": round(_ratio(old["text"], new["text"]), 4),
        "old_hash": old.get("hash"),
        "new_hash": new.get("hash"),
        "diff": _unified(old, new),
    }


def _section_summary(sec: dict) -> dict:
    return {
        "id": sec.get("id"),
        "heading": sec.get("heading"),
        "level": sec.get("level"),
        "preview": _preview(sec.get("text", "")),
    }


def compare(old_snapshot: dict, new_snapshot: dict) -> dict:
    """Produce a structured change set from two snapshots."""
    old_secs = {s["id"]: s for s in old_snapshot["sections"]}
    new_secs = {s["id"]: s for s in new_snapshot["sections"]}

    identical = old_snapshot["content_hash"] == new_snapshot["content_hash"]

    modified: list[dict] = []
    unchanged_ids: list[str] = []

    # 1. Sections present in both, matched by anchor id.
    common_ids = old_secs.keys() & new_secs.keys()
    for sid in common_ids:
        o, n = old_secs[sid], new_secs[sid]
        if o["hash"] == n["hash"]:
            unchanged_ids.append(sid)               # hash match -> skip diff
        else:
            modified.append(_modified_entry(o, n, renamed=False))

    # 2. Reconcile unmatched sections via fuzzy heading matching.
    removed_ids = list(old_secs.keys() - new_secs.keys())
    added_ids = list(new_secs.keys() - old_secs.keys())

    still_removed: list[str] = []
    matched_added: set[str] = set()

    for rid in removed_ids:
        o = old_secs[rid]
        best_aid, best_ratio = None, 0.0
        for aid in added_ids:
            if aid in matched_added:
                continue
            r = _ratio(o.get("heading") or "", new_secs[aid].get("heading") or "")
            if r > best_ratio:
                best_aid, best_ratio = aid, r

        if best_aid is not None and best_ratio >= HEADING_MATCH_RATIO:
            n = new_secs[best_aid]
            matched_added.add(best_aid)
            if o["hash"] != n["hash"]:
                modified.append(_modified_entry(o, n, renamed=True))
            else:
                unchanged_ids.append(best_aid)
        else:
            still_removed.append(rid)

    still_added = [aid for aid in added_ids if aid not in matched_added]

    sections_added = [_section_summary(new_secs[a]) for a in still_added]
    sections_removed = [_section_summary(old_secs[r]) for r in still_removed]

    # 3. API signature changes (high-value).
    old_sigs = {s["signature"] for s in old_snapshot["api_signatures"]}
    new_sigs = {s["signature"] for s in new_snapshot["api_signatures"]}
    signatures_added = sorted(new_sigs - old_sigs)
    signatures_removed = sorted(old_sigs - new_sigs)

    return {
        "identical": identical,
        "old": {
            "url": old_snapshot["requested_url"],
            "resolved_version": old_snapshot["resolved_version"],
            "captured_at": old_snapshot["captured_at"],
            "content_hash": old_snapshot["content_hash"],
        },
        "new": {
            "url": new_snapshot["requested_url"],
            "resolved_version": new_snapshot["resolved_version"],
            "captured_at": new_snapshot["captured_at"],
            "content_hash": new_snapshot["content_hash"],
        },
        "summary": {
            "sections_added": len(sections_added),
            "sections_removed": len(sections_removed),
            "sections_modified": len(modified),
            "sections_unchanged": len(unchanged_ids),
            "signatures_added": len(signatures_added),
            "signatures_removed": len(signatures_removed),
        },
        "api_signature_changes": {
            "added": signatures_added,
            "removed": signatures_removed,
        },
        "sections_added": sections_added,
        "sections_removed": sections_removed,
        "sections_modified": modified,
    }
