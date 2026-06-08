"""
Reports: render a change set as JSON and Markdown.

Pure formatting -- takes the comparator's change set and writes files.
"""

from __future__ import annotations

import json
from pathlib import Path


def write_json(change_set: dict, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(change_set, fh, indent=2, ensure_ascii=False)


def _fmt_signature_block(title: str, sigs: list[str]) -> list[str]:
    if not sigs:
        return []
    lines = [f"### {title}", ""]
    lines += [f"- `{s}`" for s in sigs]
    lines.append("")
    return lines


def write_markdown(change_set: dict, path: str | Path) -> None:
    old, new = change_set["old"], change_set["new"]
    summary = change_set["summary"]
    lines: list[str] = []

    lines.append("# Documentation Change Report")
    lines.append("")
    lines.append(
        f"Comparing **{old['resolved_version']}** -> **{new['resolved_version']}**"
    )
    lines.append("")
    lines.append(f"- Old: {old['url']}  \n  captured {old['captured_at']}")
    lines.append(f"- New: {new['url']}  \n  captured {new['captured_at']}")
    lines.append("")

    if change_set["identical"]:
        lines.append("> No changes detected (identical content hash).")
        _write(lines, path)
        return

    lines.append("## Summary")
    lines.append("")
    lines.append("| Change | Count |")
    lines.append("| --- | ---: |")
    lines.append(f"| Sections added | {summary['sections_added']} |")
    lines.append(f"| Sections removed | {summary['sections_removed']} |")
    lines.append(f"| Sections modified | {summary['sections_modified']} |")
    lines.append(f"| Sections unchanged | {summary['sections_unchanged']} |")
    lines.append(f"| API signatures added | {summary['signatures_added']} |")
    lines.append(f"| API signatures removed | {summary['signatures_removed']} |")
    lines.append("")

    sigs = change_set["api_signature_changes"]
    if sigs["added"] or sigs["removed"]:
        lines.append("## API Signature Changes")
        lines.append("")
        lines += _fmt_signature_block("Added", sigs["added"])
        lines += _fmt_signature_block("Removed", sigs["removed"])

    if change_set["sections_added"]:
        lines.append("## Added Sections")
        lines.append("")
        for s in change_set["sections_added"]:
            lines.append(f"### + {s['heading'] or '(untitled)'}  `#{s['id']}`")
            lines.append("")
            lines.append(f"> {s['preview']}")
            lines.append("")

    if change_set["sections_removed"]:
        lines.append("## Removed Sections")
        lines.append("")
        for s in change_set["sections_removed"]:
            lines.append(f"### - {s['heading'] or '(untitled)'}  `#{s['id']}`")
            lines.append("")
            lines.append(f"> {s['preview']}")
            lines.append("")

    if change_set["sections_modified"]:
        lines.append("## Modified Sections")
        lines.append("")
        for m in change_set["sections_modified"]:
            header = m["heading"] or "(untitled)"
            if m["heading_renamed"]:
                header += f"  (renamed from \"{m['old_heading']}\")"
            lines.append(f"### ~ {header}  `#{m['id']}`")
            lines.append("")
            lines.append(f"Similarity: {m['similarity']:.2%}")
            lines.append("")
            if m["diff"]:
                lines.append("```diff")
                lines.extend(m["diff"])
                lines.append("```")
                lines.append("")

    _write(lines, path)


def _write(lines: list[str], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
