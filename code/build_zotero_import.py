"""Task 8.1 — Build the Zotero bulk-import BibTeX file.

Consumes `artifacts/extraction/extraction_matrix.csv` + `retrieval_status.csv`
and produces `manuscript/zotero_import.bib` for the user to import into Zotero.

Design: design/8_1_build_zotero_import.md
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
EXTRACTION_MATRIX = ROOT / "artifacts" / "extraction" / "extraction_matrix.csv"
RETRIEVAL_STATUS = ROOT / "artifacts" / "extraction" / "retrieval_status.csv"
FULLTEXT_DIR = ROOT / "artifacts" / "extraction" / "fulltext"
PHASE7_BIB = ROOT / "manuscript" / "references.bib"
OUT = ROOT / "manuscript" / "zotero_import.bib"
CROSSREF_CACHE = ROOT / "artifacts" / "extraction" / ".crossref_author_cache.json"
CROSSREF_UA = "erp2-sms/1.0 (mailto:alpha@thethia.com)"


def clean_citekey(paper_id: str, used: set[str]) -> str:
    """Produce a deterministic, BibTeX-safe citekey from paper_id."""
    # Strip `doi:` or `fallback:` prefix
    if paper_id.startswith("doi:"):
        key = paper_id[4:]
    elif paper_id.startswith("fallback:"):
        key = paper_id[9:]
    else:
        key = paper_id
    # Keep only lowercase letters + digits
    key = "".join(c for c in key.lower() if c.isalnum())
    if not key:
        key = "entry"
    key = f"sms_{key}"
    # Collision handling
    if key in used:
        i = 1
        while f"{key}_{i}" in used:
            i += 1
        key = f"{key}_{i}"
    used.add(key)
    return key


def escape_bibtex(value: str) -> str:
    """Escape special chars for BibTeX brace-wrapped values."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    # Escape literal braces (uncommon but possible) and ampersands
    s = s.replace("\\", "\\\\")
    s = s.replace("{", "\\{").replace("}", "\\}")
    s = s.replace("&", "\\&")
    s = s.replace("%", "\\%")
    s = s.replace("#", "\\#")
    s = s.replace("$", "\\$")
    return s


def authors_to_bibtex(authors: str) -> str:
    """Convert a `;`-separated authors string to BibTeX `and`-separated."""
    if not authors or pd.isna(authors):
        return ""
    parts = [a.strip() for a in str(authors).split(";") if a.strip()]
    return " and ".join(escape_bibtex(p) for p in parts)


def venue_type_to_bibtex(venue_type: str) -> tuple[str, str]:
    """Return (entry_type, venue_field_name) based on venue_type."""
    vt = (str(venue_type) if not pd.isna(venue_type) else "").lower()
    if "journal" in vt:
        return "@article", "journal"
    if "conference" in vt or "proceedings" in vt or "workshop" in vt:
        return "@inproceedings", "booktitle"
    if "book" in vt:
        return "@inbook", "booktitle"
    if "preprint" in vt or "arxiv" in vt:
        return "@misc", "howpublished"
    if "thesis" in vt:
        return "@phdthesis", "school"
    return "@misc", "howpublished"


def doi_clean(doi: str) -> str:
    """Strip 'doi:' / 'https://doi.org/' prefix; return lowercase normalised DOI or empty."""
    if not doi or pd.isna(doi):
        return ""
    s = str(doi).strip()
    if s.startswith("doi:"):
        s = s[4:]
    if s.startswith("fallback:"):
        return ""
    if s.startswith("https://doi.org/"):
        s = s[len("https://doi.org/"):]
    return s.lower()


def build_primary_entry(
    row,
    file_map: dict[str, Path],
    used: set[str],
    author_enrichment: dict[str, str],
) -> str:
    entry_type, venue_field = venue_type_to_bibtex(row.get("venue_type", ""))
    citekey = clean_citekey(row["paper_id"], used)
    title = escape_bibtex(row.get("title", ""))
    authors = authors_to_bibtex(row.get("authors", ""))
    # If extraction didn't produce authors but Crossref enrichment did, use the enrichment.
    if not authors:
        enriched = author_enrichment.get(row.get("paper_id", ""), "")
        if enriched:
            authors = enriched
    year = row.get("year", "")
    try:
        year = int(year)
    except Exception:
        year = ""
    venue = escape_bibtex(row.get("venue", ""))
    doi = doi_clean(row.get("doi", ""))
    notes_parts = []
    if not pd.isna(row.get("sample_size", "")) and str(row.get("sample_size", "")).strip():
        notes_parts.append(f"sample_size={row['sample_size']}")
    if not pd.isna(row.get("sample_description", "")) and str(row.get("sample_description", "")).strip():
        notes_parts.append(f"sample={row['sample_description'][:200]}")
    note = escape_bibtex("; ".join(notes_parts)) if notes_parts else ""

    # File attachment (Better BibTeX 3-field form: description:path:mimetype).
    # On Windows, the drive-letter colon is escaped as `\:` and path separators
    # are forward slashes so the BibTeX parser doesn't split on "C:" and doesn't
    # treat backslashes as escape characters. Non-Windows paths need no change.
    file_field = ""
    pdf_path = file_map.get(row["paper_id"])
    if pdf_path and pdf_path.exists():
        path_str = str(pdf_path).replace("\\", "/")
        # Escape drive-letter colon (e.g., "C:" -> "C\:") — ignores the POSIX case where no drive letter exists
        path_str = re.sub(r"^([A-Za-z]):/", r"\1\\:/", path_str)
        file_field = f"{pdf_path.name}:{path_str}:application/pdf"

    lines = [f"{entry_type}{{{citekey},"]
    if authors:
        lines.append(f"  author = {{{authors}}},")
    if title:
        lines.append(f"  title = {{{title}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if venue:
        lines.append(f"  {venue_field} = {{{venue}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    if note:
        lines.append(f"  note = {{{note}}},")
    if file_field:
        lines.append(f"  file = {{{file_field}}},")
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Crossref author enrichment
# ---------------------------------------------------------------------------

def load_crossref_cache() -> dict[str, str]:
    if CROSSREF_CACHE.exists():
        try:
            return json.loads(CROSSREF_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_crossref_cache(cache: dict[str, str]) -> None:
    CROSSREF_CACHE.parent.mkdir(parents=True, exist_ok=True)
    CROSSREF_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def fetch_crossref_authors(doi: str) -> str:
    """Return BibTeX-formatted authors string for a DOI, or empty on failure."""
    url = f"https://api.crossref.org/works/{doi}"
    try:
        r = requests.get(url, headers={"User-Agent": CROSSREF_UA}, timeout=10)
        if r.status_code != 200:
            return ""
        data = r.json().get("message", {})
        authors = data.get("author", [])
        parts = []
        for a in authors:
            family = a.get("family", "").strip()
            given = a.get("given", "").strip()
            if family and given:
                parts.append(f"{given} {family}")
            elif family:
                parts.append(family)
            elif a.get("name"):
                parts.append(a["name"].strip())
        return " and ".join(escape_bibtex(p) for p in parts)
    except Exception:
        return ""


def enrich_missing_authors(em: pd.DataFrame, skip: bool = False) -> dict[str, str]:
    """Crossref-enrich papers with missing authors; cache to .crossref_author_cache.json."""
    cache = load_crossref_cache()
    if skip:
        print("  Crossref enrichment skipped (--no-enrich)")
        return cache

    blank_mask = em["authors"].isna() | (em["authors"].astype(str).str.strip() == "")
    todo = em.loc[blank_mask, ["paper_id", "doi"]].copy()
    # Normalise DOI: strip optional "doi:" prefix; drop rows without a DOI
    todo["clean_doi"] = todo["doi"].astype(str).str.replace("^doi:", "", regex=True).str.strip()
    todo = todo[todo["clean_doi"].str.len() > 0]
    # Drop rows whose DOI is a fallback-hash (paper_id like "fallback:abc123")
    todo = todo[~todo["clean_doi"].str.startswith("fallback:")]

    missing = [
        (pid, d)
        for pid, d in zip(todo["paper_id"], todo["clean_doi"])
        if pid not in cache or not cache[pid]
    ]
    if not missing:
        print(f"  Crossref enrichment: all {len(todo)} blank-author papers already cached")
        return cache

    print(f"  Crossref enrichment: fetching {len(missing)} / {len(todo)} blank-author papers …")
    fetched = 0
    for i, (pid, doi) in enumerate(missing, start=1):
        authors = fetch_crossref_authors(doi)
        cache[pid] = authors
        if authors:
            fetched += 1
        if i % 25 == 0:
            print(f"    {i}/{len(missing)} fetched {fetched} resolved so far")
            save_crossref_cache(cache)
        # Polite delay: Crossref recommends ~50 req/sec; we use 100 ms for safety
        time.sleep(0.1)
    save_crossref_cache(cache)
    print(f"  Crossref enrichment complete: {fetched} / {len(missing)} resolved")
    return cache


def build_file_map() -> dict[str, Path]:
    """Map paper_id → absolute PDF path via retrieval_status.csv."""
    rs = pd.read_csv(RETRIEVAL_STATUS)
    out: dict[str, Path] = {}
    for _, row in rs.iterrows():
        sf = row.get("safe_filename", "")
        if pd.isna(sf) or not str(sf).strip():
            continue
        pdf = FULLTEXT_DIR / str(sf)
        if pdf.exists():
            out[row["paper_id"]] = pdf.resolve()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Summarise without writing the output file.")
    parser.add_argument("--no-enrich", action="store_true",
                        help="Skip Crossref author enrichment (use only extraction_matrix author data).")
    args = parser.parse_args()

    print(f"Building Zotero bulk-import from {EXTRACTION_MATRIX.relative_to(ROOT)} + "
          f"{RETRIEVAL_STATUS.relative_to(ROOT)}")

    em = pd.read_csv(EXTRACTION_MATRIX)
    file_map = build_file_map()
    print(f"  {len(em)} primary-study rows in extraction_matrix.csv")
    print(f"  {len(file_map)} PDFs mapped from retrieval_status.csv")

    # Crossref enrichment for blank-author rows
    author_enrichment = enrich_missing_authors(em, skip=args.no_enrich)

    used: set[str] = set()
    primary_entries = [
        build_primary_entry(row, file_map, used, author_enrichment)
        for _, row in em.iterrows()
    ]
    # Count how many now have an author field
    authored = sum(1 for e in primary_entries if "\n  author = {" in e)
    print(f"  {len(primary_entries)} primary-study BibTeX entries generated ({authored} with author field)")

    # Read the 17 manuscript-reference entries verbatim
    ref_entries_text = PHASE7_BIB.read_text(encoding="utf-8") if PHASE7_BIB.exists() else ""
    import re
    n_refs = len(re.findall(r"^@\w+\{", ref_entries_text, flags=re.MULTILINE))
    print(f"  {n_refs} manuscript-reference entries carried from {PHASE7_BIB.relative_to(ROOT)}")

    if args.dry_run:
        attached = sum(1 for e in primary_entries if "file = {" in e)
        print(f"\n[dry-run] Would write {OUT.relative_to(ROOT)} with:")
        print(f"  - {len(primary_entries)} primary entries ({attached} with PDF attached)")
        print(f"  - {n_refs} reference entries")
        return 0

    # Backup existing
    if OUT.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = OUT.with_name(f"{OUT.name}.bak-{stamp}")
        shutil.copy2(OUT, bak)
        print(f"  backed up existing {OUT.name} → {bak.name}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    attached = sum(1 for e in primary_entries if "file = {" in e)
    header = (
        f"% Phase 8 Zotero bulk-import BibTeX\n"
        f"% Generated: {now}\n"
        f"% Script: code/build_zotero_import.py\n"
        f"% Contents:\n"
        f"%   - {len(primary_entries)} primary-study entries from extraction_matrix.csv\n"
        f"%   - PDF file attachments: {attached} (absolute paths under {FULLTEXT_DIR.relative_to(ROOT)})\n"
        f"%   - {n_refs} manuscript-reference entries carried from manuscript/references.bib\n"
        f"% Import into Zotero: File -> Import -> select this file.\n"
        f"% After Zotero CrossRef enrichment finishes, export:\n"
        f"%   File -> Export Library -> Better BibTeX -> manuscript/references_zotero.bib.\n"
        f"\n\n"
        f"% ============================================================================\n"
        f"% Section A — {len(primary_entries)} primary-study entries\n"
        f"% ============================================================================\n\n"
    )
    section_b_header = (
        f"\n\n% ============================================================================\n"
        f"% Section B — {n_refs} manuscript-reference entries (verbatim from Phase-7 references.bib)\n"
        f"% ============================================================================\n\n"
    )
    OUT.write_text(header + "\n\n".join(primary_entries) + section_b_header + ref_entries_text, encoding="utf-8")
    print(f"\nOK wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024 / 1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
