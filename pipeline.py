"""
Orchestration layer for the existing pipeline.

This module wires together the already-verified components
(crawler -> extractor -> comparator -> reports) into reusable functions so
that both the CLI (`main.py`) and the Streamlit app (`app.py`) call identical
logic. It does NOT modify the extraction or comparison engines.

Flow:  fetch_raw -> build_snapshot -> (persist) -> compare -> write reports
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from config import NEW_URL, OLD_URL, REPORTS_DIR, SNAPSHOTS_DIR
from crawler.fetcher import fetch_raw
from extractor.extractor import build_snapshot
from comparator.comparator import compare, load_snapshot
from reports.report import write_json, write_markdown

REPORT_JSON_NAME = "change_report.json"
REPORT_MD_NAME = "change_report.md"


def capture_snapshot(label: str, url: str) -> tuple[Path, dict]:
    """Scrape -> extract -> validate -> persist one snapshot.

    Raises ExtractionError (from the extractor) if validation fails; in that
    case no snapshot file is written.
    """
    raw = fetch_raw(url)
    snapshot = build_snapshot(url, raw["resolved_url"], raw)

    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS_DIR / f"snapshot_{label}_{snapshot['resolved_version']}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2, ensure_ascii=False)
    return path, snapshot


def run_pipeline(old_url: str = OLD_URL, new_url: str = NEW_URL) -> dict:
    """Generate fresh snapshots for both URLs, compare them and write reports.

    Returns a result bundle consumed by both the CLI and the Streamlit app.
    """
    old_path, old_snapshot = capture_snapshot("old", old_url)
    new_path, new_snapshot = capture_snapshot("new", new_url)

    change_set = compare(old_snapshot, new_snapshot)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / REPORT_JSON_NAME
    md_path = REPORTS_DIR / REPORT_MD_NAME
    write_json(change_set, json_path)
    write_markdown(change_set, md_path)

    return {
        "old_path": old_path,
        "new_path": new_path,
        "old_snapshot": old_snapshot,
        "new_snapshot": new_snapshot,
        "change_set": change_set,
        "json_report": json_path,
        "md_report": md_path,
    }


def load_latest_outputs() -> Optional[dict]:
    """Load the most recent persisted snapshots from disk and recompute the
    change set (comparator reads snapshots only). Returns None if no snapshot
    pair exists yet.
    """
    old_files = sorted(
        SNAPSHOTS_DIR.glob("snapshot_old_*.json"), key=lambda p: p.stat().st_mtime
    )
    new_files = sorted(
        SNAPSHOTS_DIR.glob("snapshot_new_*.json"), key=lambda p: p.stat().st_mtime
    )
    if not old_files or not new_files:
        return None

    old_path, new_path = old_files[-1], new_files[-1]
    old_snapshot = load_snapshot(old_path)
    new_snapshot = load_snapshot(new_path)
    change_set = compare(old_snapshot, new_snapshot)

    return {
        "old_path": old_path,
        "new_path": new_path,
        "old_snapshot": old_snapshot,
        "new_snapshot": new_snapshot,
        "change_set": change_set,
        "json_report": REPORTS_DIR / REPORT_JSON_NAME,
        "md_report": REPORTS_DIR / REPORT_MD_NAME,
    }
