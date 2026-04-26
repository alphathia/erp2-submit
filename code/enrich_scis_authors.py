"""Fill the empty `authors` field in scis_enriched.csv via a local-first cascade.

Why this exists:
    Scopus CSV export returned zero author fields; ACM DL export filled 468/469
    rows. scis_enriched.csv thus has 468/4625 (10 %) author coverage at Phase 2
    enrichment exit. Phase 8 manuscript preparation and the decision-register
    trace both benefit from dense author coverage on the full 4625-row table.

Cascade (first hit wins; each row's source is recorded):
    1. ORIGINAL — row already has a non-empty `authors` value (ACM rows).
    2. CROSSREF_CACHE — `.crossref_author_cache.json` (keyed `doi:{doi}`).
    3. EXTRACTION_MATRIX — `extraction_matrix.csv` (640 included papers).
    4. CROSSREF_API — `api.crossref.org/works/{doi}` (reuses
       fetch_crossref_authors from build_zotero_import.py).
    5. OPENALEX_API — `api.openalex.org/works/https://doi.org/{doi}`.

Format convention:
    Every NEW fill is normalised to `"First Last; First Last"` (matches
    extraction_matrix.csv). The existing 468 ACM-style rows are preserved
    as-is to avoid de-inversion errors on compound surnames / middle initials.

Idempotence:
    Newly-fetched Crossref strings are appended to `.crossref_author_cache.json`
    atomically after every 50 lookups; a crash loses at most 50 records.

Output:
    artifacts/search/enriched/scis_enriched_withauthor.csv
        Same columns as scis_enriched.csv + one new column:
        `authors_source` ∈ {original, crossref_cache, extraction_matrix,
                            crossref_api, openalex_api, missing_doi, api_failure}

Usage:
    python code/enrich_scis_authors.py               # full run (API calls)
    python code/enrich_scis_authors.py --dry-run     # local only; report gaps
    python code/enrich_scis_authors.py --limit 100   # smoke-test first 100 API lookups
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
SCIS_IN  = ROOT / "artifacts" / "search" / "enriched" / "scis_enriched.csv"
SCIS_OUT = ROOT / "artifacts" / "search" / "enriched" / "scis_enriched_withauthor.csv"
CROSSREF_CACHE = ROOT / "artifacts" / "extraction" / ".crossref_author_cache.json"
EXTRACTION_MATRIX = ROOT / "artifacts" / "extraction" / "extraction_matrix.csv"

CROSSREF_UA = "erp2-sms/1.0 (mailto:alpha@thethia.com)"
OPENALEX_MAILTO = "alpha@thethia.com"

SLEEP_BETWEEN_CALLS = 0.1   # polite-pool pacing
CACHE_SAVE_EVERY    = 50


# ---------------------------------------------------------------------------
# Author-string formatting
# ---------------------------------------------------------------------------
def format_crossref_author(entry: dict) -> str:
    """Extract 'Given Family' from a Crossref 'author' object."""
    given = (entry.get("given") or "").strip()
    family = (entry.get("family") or "").strip()
    if given and family:
        return f"{given} {family}"
    return family or given or (entry.get("name") or "").strip()


def format_openalex_author(authorship: dict) -> str:
    """Extract display_name from an OpenAlex authorship record."""
    author = authorship.get("author") or {}
    return (author.get("display_name") or "").strip()


def normalize_bibtex_and_string(s: str) -> str:
    """`A and B and C` (BibTeX) -> `A; B; C`."""
    if not s:
        return ""
    # Split on " and " (case-insensitive, whitespace-tolerant) so we don't break
    # author names that happen to contain "and".
    parts = re.split(r"\s+and\s+", s, flags=re.IGNORECASE)
    return "; ".join(p.strip() for p in parts if p.strip())


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------
def load_crossref_cache() -> dict:
    if not CROSSREF_CACHE.exists():
        return {}
    try:
        return json.loads(CROSSREF_CACHE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  [warn] crossref cache unreadable: {exc}", file=sys.stderr)
        return {}


def save_crossref_cache(cache: dict) -> None:
    CROSSREF_CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CROSSREF_CACHE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(CROSSREF_CACHE)


# ---------------------------------------------------------------------------
# Extraction-matrix lookup (local, semicolon-separated already)
# ---------------------------------------------------------------------------
def load_extraction_matrix_authors() -> dict:
    if not EXTRACTION_MATRIX.exists():
        return {}
    em = pd.read_csv(EXTRACTION_MATRIX, dtype=str).fillna("")
    lookup: dict = {}
    for _, r in em.iterrows():
        doi = r["doi"].strip().lower()
        auth = r["authors"].strip()
        if doi and auth:
            lookup[doi] = auth
    return lookup


# ---------------------------------------------------------------------------
# API fetchers
# ---------------------------------------------------------------------------
def fetch_crossref_authors(doi: str, timeout: float = 10.0) -> str:
    """Return `"First Last; First Last"` for a DOI, or empty on failure."""
    url = f"https://api.crossref.org/works/{doi}"
    try:
        r = requests.get(url, headers={"User-Agent": CROSSREF_UA},
                         timeout=timeout)
        if r.status_code != 200:
            return ""
        data = r.json()
        authors = data.get("message", {}).get("author", [])
        names = [format_crossref_author(a) for a in authors]
        names = [n for n in names if n]
        return "; ".join(names)
    except Exception:
        return ""


def fetch_openalex_authors(doi: str, timeout: float = 10.0) -> str:
    """Return `"First Last; First Last"` for a DOI via OpenAlex, or empty."""
    url = (f"https://api.openalex.org/works/https://doi.org/{doi}"
           f"?mailto={OPENALEX_MAILTO}")
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return ""
        data = r.json()
        authorships = data.get("authorships", [])
        names = [format_openalex_author(a) for a in authorships]
        names = [n for n in names if n]
        return "; ".join(names)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Main enrichment pass
# ---------------------------------------------------------------------------
def enrich(dry_run: bool = False, limit_api: int | None = None) -> int:
    if not SCIS_IN.exists():
        print(f"[x] {SCIS_IN} not found.", file=sys.stderr)
        return 1

    df = pd.read_csv(SCIS_IN, dtype=str).fillna("")
    print(f"Loaded {len(df)} rows from {SCIS_IN.relative_to(ROOT)}")

    df["authors_source"] = ""
    df["doi_lower"] = df["doi"].str.strip().str.lower()

    # Existing authors -> source = 'original'
    has_orig = df["authors"].str.strip() != ""
    df.loc[has_orig, "authors_source"] = "original"
    print(f"  original (ACM): {int(has_orig.sum())} rows")

    # Pre-load local sources
    cc = load_crossref_cache()
    cc_by_doi = {k.replace("doi:", "").lower(): v for k, v in cc.items()}
    em_authors = load_extraction_matrix_authors()
    print(f"  crossref cache entries: {len(cc_by_doi)}")
    print(f"  extraction_matrix authors: {len(em_authors)}")

    # Rows missing authors
    need_mask = ~has_orig
    need = df[need_mask].copy()
    print(f"\nRows needing authors: {len(need)}")
    print(f"  with DOI: {(need['doi_lower'] != '').sum()}")
    print(f"  without DOI: {(need['doi_lower'] == '').sum()}")

    # Phase 1 — local fills
    filled_cache = 0
    filled_em = 0
    missing_doi = 0
    still_need: list[int] = []  # indices needing API

    for idx, row in need.iterrows():
        doi = row["doi_lower"]
        if not doi:
            df.at[idx, "authors_source"] = "missing_doi"
            missing_doi += 1
            continue
        # Crossref cache first (BibTeX-format, normalise)
        if doi in cc_by_doi:
            df.at[idx, "authors"] = normalize_bibtex_and_string(cc_by_doi[doi])
            df.at[idx, "authors_source"] = "crossref_cache"
            filled_cache += 1
            continue
        # extraction_matrix (already `;`-format)
        if doi in em_authors:
            df.at[idx, "authors"] = em_authors[doi]
            df.at[idx, "authors_source"] = "extraction_matrix"
            filled_em += 1
            continue
        still_need.append(idx)

    print(f"\n=== Local fill results ===")
    print(f"  crossref_cache: {filled_cache}")
    print(f"  extraction_matrix: {filled_em}")
    print(f"  missing_doi (cannot fill): {missing_doi}")
    print(f"  still need API lookup: {len(still_need)}")

    if dry_run:
        print("\n--dry-run: skipping API calls; not writing output.")
        return 0

    # Phase 2 — Crossref API
    n_api_attempts = 0
    filled_cr_api = 0
    cr_failures: list[int] = []

    if limit_api is not None:
        still_need = still_need[:limit_api]
        print(f"\n--limit {limit_api}: processing first {len(still_need)} API calls")

    print(f"\n=== Crossref API pass ({len(still_need)} DOIs) ===")
    for i, idx in enumerate(still_need, 1):
        doi = df.at[idx, "doi_lower"]
        authors = fetch_crossref_authors(doi)
        n_api_attempts += 1
        if authors:
            df.at[idx, "authors"] = authors
            df.at[idx, "authors_source"] = "crossref_api"
            # also save to cache for next run
            cc[f"doi:{doi}"] = " and ".join(authors.split("; "))
            filled_cr_api += 1
        else:
            cr_failures.append(idx)
        if i % 50 == 0:
            save_crossref_cache(cc)
            print(f"  [{i}/{len(still_need)}] filled {filled_cr_api} "
                  f"(cache checkpointed; failures so far {len(cr_failures)})")
        time.sleep(SLEEP_BETWEEN_CALLS)
    save_crossref_cache(cc)
    print(f"  Crossref API complete: {filled_cr_api} filled, "
          f"{len(cr_failures)} failures.")

    # Phase 3 — OpenAlex fallback for Crossref failures
    filled_oa_api = 0
    oa_failures: list[int] = []
    print(f"\n=== OpenAlex fallback ({len(cr_failures)} DOIs) ===")
    for i, idx in enumerate(cr_failures, 1):
        doi = df.at[idx, "doi_lower"]
        authors = fetch_openalex_authors(doi)
        if authors:
            df.at[idx, "authors"] = authors
            df.at[idx, "authors_source"] = "openalex_api"
            filled_oa_api += 1
        else:
            df.at[idx, "authors_source"] = "api_failure"
            oa_failures.append(idx)
        if i % 50 == 0:
            print(f"  [{i}/{len(cr_failures)}] filled {filled_oa_api} "
                  f"(failures so far {len(oa_failures)})")
        time.sleep(SLEEP_BETWEEN_CALLS)
    print(f"  OpenAlex fallback complete: {filled_oa_api} filled, "
          f"{len(oa_failures)} residual failures.")

    # Drop helper col and write
    df = df.drop(columns=["doi_lower"])
    SCIS_OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SCIS_OUT, index=False)
    print(f"\n[OK] wrote {SCIS_OUT.relative_to(ROOT)}")

    # Final tally
    src_counts = df["authors_source"].value_counts().to_dict()
    total_filled = (df["authors"].str.strip() != "").sum()
    print(f"\n=== FINAL AUTHOR COVERAGE ===")
    print(f"  total rows:      {len(df)}")
    print(f"  rows with authors: {int(total_filled)} "
          f"({100 * total_filled / len(df):.1f} %)")
    print(f"  by source:")
    for k, v in sorted(src_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:<24} {v}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fill empty authors in scis_enriched.csv via local + API cascade.")
    p.add_argument("--dry-run", action="store_true",
                   help="Local fills only; report coverage; do not write output.")
    p.add_argument("--limit", type=int, default=None,
                   help="Cap API lookups (for smoke-test).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    return enrich(dry_run=args.dry_run, limit_api=args.limit)


if __name__ == "__main__":
    sys.exit(main())
