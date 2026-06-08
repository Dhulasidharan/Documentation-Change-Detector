"""
Streamlit demo for the Node.js Documentation Change Detector.

This UI sits on top of the existing, verified pipeline (crawler -> extractor
-> comparator -> reports). It does not reimplement any extraction or
comparison logic; it calls `pipeline.run_pipeline` / `load_latest_outputs`
and renders their output. Every value shown is read from snapshots or the
generated change set -- nothing about the documents is hardcoded.

Run locally:  streamlit run app.py
"""

from __future__ import annotations

import subprocess
import sys
from typing import Optional

import streamlit as st

from config import BASE_DIR, NEW_URL, OLD_URL
from pipeline import load_latest_outputs

# --------------------------------------------------------------------------- #
# Page config
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Node.js Documentation Change Detector",
    page_icon="📘",
    layout="wide",
)

ARCHITECTURE_DIAGRAM = """\
Playwright
    ↓
DOM Extraction
    ↓
Structured Snapshots
    ↓
Hash Comparison
    ↓
Diff Engine
    ↓
Report Generation
"""

# Extraction statistics shown in the validation section (keys exist in every
# snapshot's `stats` block; labels are for display only).
STAT_FIELDS = [
    ("headings_found", "Headings Found"),
    ("paragraphs_found", "Paragraphs Found"),
    ("tables_found", "Tables Found"),
    ("code_blocks_found", "Code Blocks Found"),
    ("lists_found", "Lists Found"),
]


# --------------------------------------------------------------------------- #
# Pipeline helpers
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def _ensure_browser() -> bool:
    """Ensure Playwright's Chromium is present.

    On a developer machine this is a fast no-op; on a fresh hosting
    environment (e.g. Streamlit Community Cloud) it downloads the browser
    once per session. Failures are non-fatal -- the run will surface the real
    error if scraping still cannot start.
    """
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=False,
        capture_output=True,
    )
    return True


def _section_by_id(snapshot: dict, section_id: Optional[str]) -> Optional[dict]:
    """Look up a section's full record in a snapshot by its anchor id."""
    if section_id is None:
        return None
    for section in snapshot["sections"]:
        if section["id"] == section_id:
            return section
    return None


# --------------------------------------------------------------------------- #
# Rendering: static / informational
# --------------------------------------------------------------------------- #
def render_header() -> None:
    st.title("Node.js Documentation Change Detector")
    st.caption(
        "Compare Node.js documentation versions and automatically detect "
        "additions, removals, modifications, and API changes."
    )


def render_how_it_works() -> None:
    with st.expander("How It Works", expanded=False):
        st.markdown(
            "Each page is scraped with Playwright, reduced to a structured, "
            "order-preserving snapshot (headings, paragraphs, code, tables, "
            "lists, API signatures), hashed, and diffed **snapshot-to-snapshot** "
            "-- the comparator never touches the live pages."
        )
        st.code(ARCHITECTURE_DIAGRAM, language="text")


# --------------------------------------------------------------------------- #
# Rendering: overview + metrics (all values come from snapshots / change set)
# --------------------------------------------------------------------------- #
def render_overview(old_snapshot: dict, new_snapshot: dict) -> None:
    st.subheader("Overview")
    left, right = st.columns(2)
    with left:
        st.markdown("**Old Version**")
        st.markdown(f"### {old_snapshot['resolved_version']}")
        st.caption(old_snapshot["requested_url"])
    with right:
        st.markdown("**New Version**")
        st.markdown(f"### {new_snapshot['resolved_version']}")
        st.caption(new_snapshot["requested_url"])

    old, new = old_snapshot["stats"], new_snapshot["stats"]
    st.markdown(
        f"**Sections:** {old['sections_found']} → {new['sections_found']} "
        f"&nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**Signatures:** {old['signatures_found']} → {new['signatures_found']} "
        f"&nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**Paragraphs:** {old['paragraphs_found']} → {new['paragraphs_found']}",
        unsafe_allow_html=True,
    )


def render_summary_cards(change_set: dict) -> None:
    st.subheader("Summary")
    summary = change_set["summary"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Added Sections", summary["sections_added"])
    c2.metric("Modified Sections", summary["sections_modified"])
    c3.metric("Removed Sections", summary["sections_removed"])
    c4.metric("Added APIs", summary["signatures_added"])
    c5.metric("Removed APIs", summary["signatures_removed"])


def render_validation(old_snapshot: dict, new_snapshot: dict) -> None:
    st.subheader("Extraction Validation")
    st.caption("Proof that extraction worked -- statistics read from each snapshot.")
    old, new = old_snapshot["stats"], new_snapshot["stats"]
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Old · {old_snapshot['resolved_version']}**")
        for key, label in STAT_FIELDS:
            st.metric(label, old[key])
    with right:
        st.markdown(f"**New · {new_snapshot['resolved_version']}**")
        for key, label in STAT_FIELDS:
            st.metric(label, new[key], delta=new[key] - old[key])


# --------------------------------------------------------------------------- #
# Rendering: change tabs
# --------------------------------------------------------------------------- #
def _render_added(change_set: dict) -> None:
    added = change_set["sections_added"]
    if not added:
        st.info("No sections were added.")
        return
    for section in added:
        title = section["heading"] or "(untitled)"
        with st.expander(f"➕ {title}", expanded=False):
            st.markdown(f"**Section ID:** `{section['id']}`")
            st.markdown("**Content preview:**")
            st.write(section["preview"])


def _render_modified(
    change_set: dict, old_snapshot: dict, new_snapshot: dict
) -> None:
    modified = change_set["sections_modified"]
    if not modified:
        st.info("No sections were modified.")
        return
    for entry in modified:
        title = entry["heading"] or "(untitled)"
        label = f"✏️ {title} · similarity {entry['similarity']:.0%}"
        if entry["heading_renamed"]:
            label += "  (renamed)"
        with st.expander(label, expanded=False):
            st.markdown(f"**Section ID:** `{entry['id']}`")

            old_section = _section_by_id(old_snapshot, entry["old_id"])
            new_section = _section_by_id(new_snapshot, entry["id"])
            left, right = st.columns(2)
            with left:
                st.markdown("**Old Content**")
                st.write(old_section["text"] if old_section else "—")
            with right:
                st.markdown("**New Content**")
                st.write(new_section["text"] if new_section else "—")

            st.markdown("**Unified diff**")
            if entry["diff"]:
                st.code("\n".join(entry["diff"]), language="diff")
            else:
                st.caption("No line-level diff available.")


def _render_removed(change_set: dict) -> None:
    removed = change_set["sections_removed"]
    if not removed:
        st.info("No sections were removed.")
        return
    for section in removed:
        title = section["heading"] or "(untitled)"
        with st.expander(f"➖ {title}", expanded=False):
            st.markdown(f"**Section ID:** `{section['id']}`")
            st.markdown("**Content preview:**")
            st.write(section["preview"])


def _render_api_changes(change_set: dict) -> None:
    changes = change_set["api_signature_changes"]
    added, removed = changes["added"], changes["removed"]

    st.markdown("**Added Signatures**")
    if added:
        st.code("\n".join(f"+ {sig}" for sig in added), language="diff")
    else:
        st.info("No API signatures were added.")

    st.markdown("**Removed Signatures**")
    if removed:
        st.code("\n".join(f"- {sig}" for sig in removed), language="diff")
    else:
        st.info("No API signatures were removed.")


def render_change_tabs(
    change_set: dict, old_snapshot: dict, new_snapshot: dict
) -> None:
    st.subheader("Detected Changes")
    tab_added, tab_modified, tab_removed, tab_api = st.tabs(
        ["Added", "Modified", "Removed", "API Changes"]
    )
    with tab_added:
        _render_added(change_set)
    with tab_modified:
        _render_modified(change_set, old_snapshot, new_snapshot)
    with tab_removed:
        _render_removed(change_set)
    with tab_api:
        _render_api_changes(change_set)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def render_sidebar(results: Optional[dict]) -> None:
    """Render the fixed configuration + snapshot inspection."""
    st.sidebar.header("Configuration")
    # URLs are fixed for this demo (read-only).
    st.sidebar.text_input("Old version URL", value=OLD_URL, disabled=True)
    st.sidebar.text_input("New version URL", value=NEW_URL, disabled=True)

    st.sidebar.divider()
    st.sidebar.header("Snapshot Inspection")
    if results is None:
        st.sidebar.caption("Run a comparison to inspect snapshots.")
        return

    choice = st.sidebar.radio(
        "Snapshot", ["View Old Snapshot", "View New Snapshot"], index=0
    )
    snapshot = (
        results["old_snapshot"]
        if choice == "View Old Snapshot"
        else results["new_snapshot"]
    )
    st.sidebar.json(
        {
            "version": snapshot["resolved_version"],
            "resolved_url": snapshot["resolved_url"],
            "captured_at": snapshot["captured_at"],
            "content_hash": snapshot["content_hash"],
            "stats": snapshot["stats"],
        }
    )


# --------------------------------------------------------------------------- #
# Run handler
# --------------------------------------------------------------------------- #
def run_comparison() -> None:
    """Generate fresh snapshots, compare, and store results in session state.

    The pipeline runs in a SEPARATE PROCESS (via main.py). This is required on
    Windows: Streamlit executes the app in a worker thread whose asyncio loop
    cannot spawn subprocesses, so launching Playwright in-process raises
    NotImplementedError. A child process has a normal event loop and runs the
    scrape cleanly; the app then loads the snapshots it wrote to disk.
    """
    _ensure_browser()
    with st.spinner("Scraping pages, extracting snapshots and comparing..."):
        proc = subprocess.run(
            [sys.executable, "main.py"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )

    if proc.returncode == 0:
        st.session_state["results"] = load_latest_outputs()
        st.success("Comparison complete.")
    elif proc.returncode == 2:
        # Extraction validation failed (the extractor refused to write a snapshot).
        st.session_state["results"] = None
        st.error("No valid snapshot generated.")
        st.warning(f"Validation details:\n\n{proc.stderr.strip() or proc.stdout.strip()}")
    else:
        # Any other failure (e.g. network / browser) -- keep the app alive.
        st.session_state["results"] = None
        st.error("Pipeline failed before a comparison could be produced.")
        st.code((proc.stderr or proc.stdout or "Unknown error").strip())


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    render_header()
    render_how_it_works()

    # Prime session state from any previously generated snapshots on disk.
    if "results" not in st.session_state:
        st.session_state["results"] = load_latest_outputs()

    render_sidebar(st.session_state["results"])

    if st.button("Run Comparison", type="primary"):
        run_comparison()

    results = st.session_state.get("results")
    if not results:
        st.info(
            "No comparison loaded yet. Click **Run Comparison** to scrape both "
            "URLs and detect changes."
        )
        return

    old_snapshot = results["old_snapshot"]
    new_snapshot = results["new_snapshot"]
    change_set = results["change_set"]

    st.divider()
    render_overview(old_snapshot, new_snapshot)
    st.divider()
    render_summary_cards(change_set)
    st.divider()
    render_change_tabs(change_set, old_snapshot, new_snapshot)
    st.divider()
    render_validation(old_snapshot, new_snapshot)


if __name__ == "__main__":
    main()
