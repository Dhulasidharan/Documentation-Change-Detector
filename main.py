"""
Documentation Change Detection System -- CLI entry point.

This is a thin presenter over `pipeline.run_pipeline`. The pipeline is the
single source of truth shared with the Streamlit app; this file only adds
console output.

Flow (snapshot-mediated):

    URL -> crawler (Playwright) -> extractor -> snapshot JSON (on disk)
        -> comparator (snapshots only) -> reports (JSON + Markdown)
"""

from __future__ import annotations

import sys

from extractor.extractor import ExtractionError
from pipeline import run_pipeline


def _print_stats(label: str, snapshot: dict) -> None:
    stats = snapshot["stats"]
    print(f"\n[{label}] {snapshot['requested_url']}")
    print(f"  resolved version : {snapshot['resolved_version']}")
    print(f"  resolved url     : {snapshot['resolved_url']}")
    print(f"  content hash     : {snapshot['content_hash'][:16]}...")
    for key in (
        "headings_found",
        "paragraphs_found",
        "code_blocks_found",
        "tables_found",
        "lists_found",
        "sections_found",
        "signatures_found",
        "content_length",
    ):
        print(f"  {key:<17}: {stats[key]}")


def run() -> int:
    print("==> Running pipeline (scrape -> extract -> compare -> report)...")
    try:
        results = run_pipeline()
    except ExtractionError as exc:
        print(f"\nEXTRACTION FAILED -- no snapshot written.\n  {exc}", file=sys.stderr)
        return 2

    _print_stats("old", results["old_snapshot"])
    _print_stats("new", results["new_snapshot"])

    s = results["change_set"]["summary"]
    print("\n==> Change summary")
    print(f"  identical            : {results['change_set']['identical']}")
    print(f"  sections added       : {s['sections_added']}")
    print(f"  sections removed     : {s['sections_removed']}")
    print(f"  sections modified    : {s['sections_modified']}")
    print(f"  sections unchanged   : {s['sections_unchanged']}")
    print(f"  signatures added     : {s['signatures_added']}")
    print(f"  signatures removed   : {s['signatures_removed']}")
    print(
        f"\n  reports: {results['json_report'].name}, {results['md_report'].name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
