"""Enrich extraction_matrix.csv with abstract + SCIS venue/ranking metadata.

Task 3.4 — pulls four columns (abstract, scis_acronym, scis_venue_type, scis_rank)
from post_filtered.csv onto each extraction_matrix row via DOI-primary /
title-fallback join. Writes extraction_matrix_enrich.csv preserving all 24
original columns plus the 4 enrichment columns plus an `enrich_match_method`
provenance column.

See design/3_4_extraction_matrix_enrich.md for the full specification.

Usage:
    python code/extraction_matrix_enrich.py
    python code/extraction_matrix_enrich.py --verify

Consumes:
    artifacts/extraction/extraction_matrix.csv (640 rows, 24 cols)
    artifacts/search/post_filtered.csv (4246 rows, 36 cols)

Produces:
    artifacts/extraction/extraction_matrix_enrich.csv (640 rows, 29 cols)
    artifacts/extraction/extraction_matrix_enrich.csv.meta.json
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta

DEFAULT_MATRIX = ROOT / "artifacts" / "extraction" / "extraction_matrix.csv"
DEFAULT_POST_FILTERED = ROOT / "artifacts" / "search" / "post_filtered.csv"
DEFAULT_OUTPUT = ROOT / "artifacts" / "extraction" / "extraction_matrix_enrich.csv"

ABSTRACT_NA = "abstract not available"
SCIS_NOT_FOUND = "Not found"

ENRICH_COLUMNS = ["abstract", "scis_acronym", "scis_venue_type", "scis_rank"]


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)


def normalize_doi(raw) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip().lower()
    if not s or s in ("nan", "none"):
        return ""
    for prefix in _DOI_PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    s = s.rstrip("/").strip()
    return s


def normalize_title(raw) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip().lower()
    if not s or s == "nan":
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Tie-break for duplicate keys in post_filtered
# ---------------------------------------------------------------------------

def _score_pf_row(row) -> tuple[int, int]:
    """Higher tuple wins. (abstract-present, rank-found)."""
    abstract_present = 1 if (pd.notna(row.get("abstract")) and str(row.get("abstract")).strip()) else 0
    rank_found = 1 if str(row.get("scis_rank", "")).strip() not in ("", SCIS_NOT_FOUND, "nan") else 0
    return (abstract_present, rank_found)


def build_index(pf: pd.DataFrame, key_col_normalized: pd.Series) -> dict:
    """Build {normalized_key: pf_row_index} with deterministic tie-break."""
    idx: dict[str, int] = {}
    for i, key in enumerate(key_col_normalized):
        if not key:
            continue
        if key not in idx:
            idx[key] = i
        else:
            existing = pf.iloc[idx[key]]
            candidate = pf.iloc[i]
            if _score_pf_row(candidate) > _score_pf_row(existing):
                idx[key] = i
    return idx


# ---------------------------------------------------------------------------
# Enrichment core
# ---------------------------------------------------------------------------

def enrich(em: pd.DataFrame, pf: pd.DataFrame) -> pd.DataFrame:
    pf_doi_norm = pf["doi"].map(normalize_doi)
    pf_title_norm = pf["title"].map(normalize_title)

    doi_index = build_index(pf, pf_doi_norm)
    title_index = build_index(pf, pf_title_norm)

    em_out = em.copy()
    out_abstract: list[str] = []
    out_acronym: list[str] = []
    out_venue_type: list[str] = []
    out_rank: list[str] = []
    out_method: list[str] = []

    for _, row in em.iterrows():
        em_doi_key = normalize_doi(row.get("doi"))
        em_title_key = normalize_title(row.get("title"))
        pf_row_idx = None
        method = "unmatched"

        if em_doi_key and em_doi_key in doi_index:
            pf_row_idx = doi_index[em_doi_key]
            method = "doi"
        elif em_title_key and em_title_key in title_index:
            pf_row_idx = title_index[em_title_key]
            method = "title"

        if pf_row_idx is not None:
            pf_row = pf.iloc[pf_row_idx]
            abstract_val = pf_row.get("abstract")
            if pd.isna(abstract_val) or not str(abstract_val).strip():
                abstract_val = ABSTRACT_NA
            else:
                abstract_val = str(abstract_val)
            acronym_val = str(pf_row.get("scis_acronym", SCIS_NOT_FOUND)).strip() or SCIS_NOT_FOUND
            venue_type_val = str(pf_row.get("scis_venue_type", SCIS_NOT_FOUND)).strip() or SCIS_NOT_FOUND
            rank_val = str(pf_row.get("scis_rank", SCIS_NOT_FOUND)).strip() or SCIS_NOT_FOUND
        else:
            abstract_val = ABSTRACT_NA
            acronym_val = SCIS_NOT_FOUND
            venue_type_val = SCIS_NOT_FOUND
            rank_val = SCIS_NOT_FOUND

        out_abstract.append(abstract_val)
        out_acronym.append(acronym_val)
        out_venue_type.append(venue_type_val)
        out_rank.append(rank_val)
        out_method.append(method)

    em_out["abstract"] = out_abstract
    em_out["scis_acronym"] = out_acronym
    em_out["scis_venue_type"] = out_venue_type
    em_out["scis_rank"] = out_rank
    em_out["enrich_match_method"] = out_method
    return em_out


# ---------------------------------------------------------------------------
# Rigor checks + diagnostic report
# ---------------------------------------------------------------------------

def check_and_report(em: pd.DataFrame, enriched: pd.DataFrame) -> list[str]:
    """Run academic-rigor invariants. Return list of failure messages."""
    failures: list[str] = []

    if len(enriched) != len(em):
        failures.append(f"Row count mismatch: input {len(em)} vs output {len(enriched)}")

    for col in em.columns:
        if col not in enriched.columns:
            failures.append(f"Original column missing from output: {col}")
            continue
        left = em[col].reset_index(drop=True)
        right = enriched[col].reset_index(drop=True)
        if not left.equals(right):
            failures.append(f"Values in column '{col}' were mutated")

    for col in ENRICH_COLUMNS + ["enrich_match_method"]:
        if col not in enriched.columns:
            failures.append(f"Enrichment column missing from output: {col}")

    return failures


def print_report(em: pd.DataFrame, enriched: pd.DataFrame) -> None:
    print("=" * 72)
    print("Task 3.4 — extraction_matrix_enrich diagnostic report")
    print("=" * 72)
    print(f"Input rows:  {len(em)}  (extraction_matrix.csv)")
    print(f"Output rows: {len(enriched)}  (extraction_matrix_enrich.csv)")
    print(f"Input cols:  {len(em.columns)}  Output cols: {len(enriched.columns)}")

    print("\n-- Match method distribution --")
    method_counts = enriched["enrich_match_method"].value_counts()
    for method, n in method_counts.items():
        print(f"  {method:<12} {n:>4}  ({n / len(enriched):.1%})")

    print("\n-- Abstract coverage --")
    n_real = (enriched["abstract"] != ABSTRACT_NA).sum()
    n_na = (enriched["abstract"] == ABSTRACT_NA).sum()
    print(f"  real abstract         {n_real:>4}  ({n_real / len(enriched):.1%})")
    print(f"  abstract not avail.   {n_na:>4}  ({n_na / len(enriched):.1%})")

    print("\n-- SCIS rank distribution (enriched) --")
    for rank, n in enriched["scis_rank"].value_counts(dropna=False).items():
        print(f"  {str(rank):<12} {n:>4}  ({n / len(enriched):.1%})")

    print("\n-- SCIS venue_type distribution (enriched) --")
    for vt, n in enriched["scis_venue_type"].value_counts(dropna=False).items():
        print(f"  {str(vt):<12} {n:>4}  ({n / len(enriched):.1%})")

    unmatched = enriched[enriched["enrich_match_method"] == "unmatched"]
    if len(unmatched) > 0:
        print(f"\n-- UNMATCHED rows ({len(unmatched)}) --")
        for _, row in unmatched.iterrows():
            print(f"  {row['paper_id']}  doi={row.get('doi', '')}  title={row.get('title', '')[:80]}")
    else:
        print("\n-- UNMATCHED rows: none --")

    title_matched = enriched[enriched["enrich_match_method"] == "title"]
    if len(title_matched) > 0:
        print(f"\n-- TITLE-fallback matches ({len(title_matched)}) --")
        for _, row in title_matched.iterrows():
            print(f"  {row['paper_id']}  title={row.get('title', '')[:80]}")


# ---------------------------------------------------------------------------
# Verify mode
# ---------------------------------------------------------------------------

def verify(output_path: Path, matrix_path: Path) -> int:
    if not output_path.exists():
        print(f"[verify] FAIL: output not found at {output_path}", file=sys.stderr)
        return 1
    em = pd.read_csv(matrix_path)
    enriched = pd.read_csv(output_path)
    failures = check_and_report(em, enriched)
    print_report(em, enriched)
    if failures:
        print("\n[verify] FAILURES:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\n[verify] All invariants passed.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX),
                        help="Path to extraction_matrix.csv")
    parser.add_argument("--post-filtered", default=str(DEFAULT_POST_FILTERED),
                        help="Path to post_filtered.csv")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT),
                        help="Path to extraction_matrix_enrich.csv")
    parser.add_argument("--verify", action="store_true",
                        help="Re-check an existing output instead of regenerating")
    args = parser.parse_args()

    matrix_path = Path(args.matrix)
    output_path = Path(args.output)

    if args.verify:
        return verify(output_path, matrix_path)

    pf_path = Path(args.post_filtered)
    print(f"Loading {matrix_path} ...")
    em = pd.read_csv(matrix_path)
    print(f"  {len(em)} rows, {len(em.columns)} cols")

    print(f"Loading {pf_path} ...")
    pf = pd.read_csv(pf_path)
    print(f"  {len(pf)} rows, {len(pf.columns)} cols")

    for col in ("doi", "title", "abstract", "scis_acronym", "scis_venue_type", "scis_rank"):
        if col not in pf.columns:
            print(f"ERROR: required column '{col}' missing from post_filtered.csv", file=sys.stderr)
            return 1

    print("Enriching ...")
    enriched = enrich(em, pf)

    failures = check_and_report(em, enriched)
    print_report(em, enriched)

    if failures:
        print("\nFAILURES — not writing output:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_path, index=False)
    write_with_meta(
        output_path,
        script="code/extraction_matrix_enrich.py",
        inputs=[str(matrix_path.relative_to(ROOT)), str(pf_path.relative_to(ROOT))],
    )
    print(f"\nWrote {output_path}")
    print(f"Wrote {output_path.with_suffix('.csv.meta.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
