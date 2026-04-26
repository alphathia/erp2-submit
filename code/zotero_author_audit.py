"""Patch-for-documentation: multi-source author audit for the Zotero bulk-import bib.

Purpose.
    The Scopus retrieval pipeline returned 0% author coverage; extraction-time
    backfill brought it to 35%; a prior Crossref pass brought it to 97%. This
    script audits ALL ~660 entries in `manuscript/zotero_import.bib` against
    authoritative sources (Crossref → OpenAlex → Semantic Scholar) and
    regenerates the bib with the best available author data.

Scope.
    This is a **patch for documentation** — it does NOT read or write any
    reproducibility-trail artefact under `artifacts/`. It only reads the
    current `manuscript/zotero_import.bib` (to preserve Windows file-paths +
    non-author fields) and `artifacts/extraction/extraction_matrix.csv` as
    read-only metadata. All caches and audit outputs live under `manuscript/`.

Outputs.
    - manuscript/zotero_import.bib                         (regenerated)
    - manuscript/.zotero_author_audit_cache.json          (fresh cache)
    - manuscript/zotero_author_audit.md                    (patch documentation)

Sources consulted (in order; stop at first successful resolution).
    1. Crossref  — api.crossref.org/works/{doi}
    2. OpenAlex  — api.openalex.org/works/doi:{doi}
    3. Semantic Scholar — api.semanticscholar.org/graph/v1/paper/DOI:{doi}

Usage.
    python code/zotero_author_audit.py
    python code/zotero_author_audit.py --dry-run       # summary only, no writes
    python code/zotero_author_audit.py --limit 20      # sample first 20 for smoke test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
EXTRACTION_MATRIX = ROOT / "artifacts" / "extraction" / "extraction_matrix.csv"
ZOTERO_BIB = ROOT / "manuscript" / "zotero_import.bib"
CACHE = ROOT / "manuscript" / ".zotero_author_audit_cache.json"
AUDIT_MD = ROOT / "manuscript" / "zotero_author_audit.md"
USER_AGENT = "erp2-sms/1.0 (mailto:alpha@thethia.com)"

# Polite API timing (seconds between requests)
CROSSREF_DELAY = 0.1
OPENALEX_DELAY = 0.15
S2_DELAY = 1.0


# ---------------------------------------------------------------------------
# BibTeX helpers
# ---------------------------------------------------------------------------

def escape_bibtex(value: str) -> str:
    """Escape special chars for BibTeX brace-wrapped values."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    s = s.replace("\\", "\\\\")
    s = s.replace("{", "\\{").replace("}", "\\}")
    s = s.replace("&", "\\&")
    s = s.replace("%", "\\%")
    s = s.replace("#", "\\#")
    s = s.replace("$", "\\$")
    return s


def bibtex_authors(authors: list[str]) -> str:
    """Join a list of author names with ' and ' (BibTeX convention)."""
    return " and ".join(escape_bibtex(a) for a in authors if a)


def parse_extraction_authors(raw: str) -> list[str]:
    """Split extraction_matrix-style `;`-separated authors into a list."""
    if not raw or pd.isna(raw):
        return []
    return [a.strip() for a in str(raw).split(";") if a.strip()]


def doi_clean(doi: str) -> str:
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


# ---------------------------------------------------------------------------
# Authoritative-source cascade
# ---------------------------------------------------------------------------

def fetch_crossref(doi: str, session: requests.Session) -> tuple[list[str], str]:
    """Return (authors, note). Empty authors on failure."""
    try:
        r = session.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if r.status_code != 200:
            return ([], f"crossref http {r.status_code}")
        data = r.json().get("message", {})
        out = []
        for a in data.get("author", []):
            family = (a.get("family") or "").strip()
            given = (a.get("given") or "").strip()
            if family and given:
                out.append(f"{given} {family}")
            elif family:
                out.append(family)
            elif a.get("name"):
                out.append(a["name"].strip())
        return (out, "crossref_ok" if out else "crossref_empty")
    except Exception as e:
        return ([], f"crossref_error:{type(e).__name__}")


def fetch_openalex(doi: str, session: requests.Session) -> tuple[list[str], str]:
    try:
        r = session.get(
            f"https://api.openalex.org/works/doi:{doi}",
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if r.status_code != 200:
            return ([], f"openalex http {r.status_code}")
        data = r.json()
        out = []
        for a in data.get("authorships", []):
            display = (a.get("author") or {}).get("display_name", "").strip()
            if display:
                out.append(display)
        return (out, "openalex_ok" if out else "openalex_empty")
    except Exception as e:
        return ([], f"openalex_error:{type(e).__name__}")


def fetch_semantic_scholar(doi: str, session: requests.Session) -> tuple[list[str], str]:
    try:
        r = session.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            params={"fields": "authors"},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if r.status_code != 200:
            return ([], f"s2 http {r.status_code}")
        data = r.json()
        out = [a["name"].strip() for a in data.get("authors", []) if a.get("name")]
        return (out, "s2_ok" if out else "s2_empty")
    except Exception as e:
        return ([], f"s2_error:{type(e).__name__}")


def resolve_authors(doi: str, session: requests.Session) -> dict:
    """Cascade Crossref → OpenAlex → Semantic Scholar. Return {authors, source, notes}."""
    # Crossref
    authors, note = fetch_crossref(doi, session)
    time.sleep(CROSSREF_DELAY)
    if authors:
        return {"authors": authors, "source": "crossref", "notes": note}
    notes_chain = [note]
    # OpenAlex
    authors, note = fetch_openalex(doi, session)
    time.sleep(OPENALEX_DELAY)
    if authors:
        return {"authors": authors, "source": "openalex", "notes": "; ".join(notes_chain + [note])}
    notes_chain.append(note)
    # Semantic Scholar
    authors, note = fetch_semantic_scholar(doi, session)
    time.sleep(S2_DELAY)
    if authors:
        return {"authors": authors, "source": "semantic_scholar", "notes": "; ".join(notes_chain + [note])}
    notes_chain.append(note)
    return {"authors": [], "source": "none", "notes": "; ".join(notes_chain)}


# ---------------------------------------------------------------------------
# Audit comparison
# ---------------------------------------------------------------------------

def normalise_name(name: str) -> str:
    """Lowercase, strip punctuation + accents (ASCII fold), collapse spaces."""
    import unicodedata
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z ,]", "", s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    # Reduce "Last, First" and "First Last" to "Last First" (order-invariant)
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        s = " ".join(parts)
    tokens = s.split()
    return " ".join(sorted(tokens))  # token-set equivalent


def classify_delta(original: list[str], authoritative: list[str]) -> str:
    """Return one of: blank_filled, confirmed, updated, no_change, still_blank."""
    orig_norm = [normalise_name(a) for a in original if a]
    auth_norm = [normalise_name(a) for a in authoritative if a]
    if not orig_norm and not auth_norm:
        return "still_blank"
    if not orig_norm and auth_norm:
        return "blank_filled"
    if orig_norm and not auth_norm:
        return "no_change"  # keep original; cascade returned nothing
    # Both populated — compare
    if set(orig_norm) == set(auth_norm):
        return "confirmed"
    return "updated"


# ---------------------------------------------------------------------------
# zotero_import.bib parsing (reuse existing file's file-paths)
# ---------------------------------------------------------------------------

def parse_file_fields(bib_text: str) -> dict[str, str]:
    """Map citekey → full file = {...} field text (including trailing comma)."""
    out = {}
    entry_re = re.compile(r"@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}", re.DOTALL)
    for m in entry_re.finditer(bib_text):
        key = m.group(1).strip()
        body = m.group(2)
        fm = re.search(r"\n  file\s*=\s*(\{[^}]+\},?)", body)
        if fm:
            out[key] = fm.group(1)
    return out


def parse_manuscript_refs_section(bib_text: str) -> str:
    """Return the 'Section B' manuscript-reference entries verbatim."""
    marker = "% Section B"
    idx = bib_text.find(marker)
    if idx < 0:
        return ""
    return bib_text[idx:]


# ---------------------------------------------------------------------------
# Citekey generation (consistent with build_zotero_import.py)
# ---------------------------------------------------------------------------

def clean_citekey(paper_id: str, used: set[str]) -> str:
    if paper_id.startswith("doi:"):
        key = paper_id[4:]
    elif paper_id.startswith("fallback:"):
        key = paper_id[9:]
    else:
        key = paper_id
    key = "".join(c for c in key.lower() if c.isalnum())
    if not key:
        key = "entry"
    key = f"sms_{key}"
    if key in used:
        i = 1
        while f"{key}_{i}" in used:
            i += 1
        key = f"{key}_{i}"
    used.add(key)
    return key


def venue_type_to_bibtex(venue_type: str) -> tuple[str, str]:
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not write files.")
    parser.add_argument("--limit", type=int, default=0, help="Process only N papers (smoke test).")
    args = parser.parse_args()

    # Load inputs
    print(f"Reading {EXTRACTION_MATRIX.relative_to(ROOT)} …")
    em = pd.read_csv(EXTRACTION_MATRIX)
    print(f"  {len(em)} rows")

    print(f"Parsing existing {ZOTERO_BIB.relative_to(ROOT)} (to preserve Windows file-paths) …")
    bib_text = ZOTERO_BIB.read_text(encoding="utf-8")
    file_fields = parse_file_fields(bib_text)
    manuscript_refs = parse_manuscript_refs_section(bib_text)
    print(f"  {len(file_fields)} existing citekeys with file fields")

    # Load or init cache
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"  loaded audit cache: {len(cache)} entries")
    else:
        cache = {}

    # Iterate papers
    session = requests.Session()
    rows = em if args.limit == 0 else em.head(args.limit)
    total = len(rows)
    print(f"\nAuditing {total} papers against Crossref → OpenAlex → Semantic Scholar cascade …")

    delta_counts = {
        "blank_filled": 0,
        "confirmed": 0,
        "updated": 0,
        "no_change": 0,
        "still_blank": 0,
    }
    source_counts = {"crossref": 0, "openalex": 0, "semantic_scholar": 0, "none": 0, "cached": 0}
    audit_records = []

    for i, (_, row) in enumerate(rows.iterrows(), start=1):
        pid = row["paper_id"]
        doi = doi_clean(row.get("doi", ""))
        orig_authors = parse_extraction_authors(row.get("authors", ""))

        # Cache key: paper_id
        if pid in cache and cache[pid].get("_schema") == "v1":
            rec = cache[pid]
            source_counts["cached"] += 1
        else:
            if doi:
                result = resolve_authors(doi, session)
            else:
                result = {"authors": [], "source": "none", "notes": "no_doi"}
            rec = {
                "_schema": "v1",
                "paper_id": pid,
                "doi": doi,
                "original_authors": orig_authors,
                "authoritative_authors": result["authors"],
                "source": result["source"],
                "notes": result["notes"],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            rec["delta"] = classify_delta(orig_authors, result["authors"])
            cache[pid] = rec
            source_counts[result["source"]] = source_counts.get(result["source"], 0) + 1
            # Save cache periodically
            if i % 25 == 0:
                CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"  {i}/{total}: delta={rec['delta']}, src={result['source']}")

        delta_counts[rec["delta"]] += 1
        audit_records.append(rec)

    # Final cache save
    CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nAudit complete. Delta breakdown:")
    for k, v in delta_counts.items():
        print(f"  {k}: {v}")
    print(f"Source breakdown (API calls only):")
    for k, v in source_counts.items():
        print(f"  {k}: {v}")

    if args.dry_run:
        print("[dry-run] not writing zotero_import.bib or audit report")
        return 0

    # Rebuild zotero_import.bib entries
    print(f"\nRegenerating {ZOTERO_BIB.relative_to(ROOT)} …")
    entries = []
    used: set[str] = set()
    authored_count = 0
    file_attached_count = 0
    for _, row in em.iterrows():
        pid = row["paper_id"]
        rec = cache.get(pid, {})
        entry_type, venue_field = venue_type_to_bibtex(row.get("venue_type", ""))
        citekey = clean_citekey(pid, used)

        # Decide which authors to use. Priority:
        #  1. Audited authoritative (if this paper was in the cascade)
        #  2. Extraction-matrix authors (read fresh from CSV; covers unaudited
        #     papers when --limit is used, so we don't lose the 221 papers that
        #     had extraction authors)
        #  3. Empty (no data anywhere)
        authoritative = rec.get("authoritative_authors") or []
        fallback = parse_extraction_authors(row.get("authors", ""))
        if authoritative:
            authors = bibtex_authors(authoritative)
        elif fallback:
            authors = bibtex_authors(fallback)
        else:
            authors = ""

        title = escape_bibtex(row.get("title", ""))
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
        if rec.get("source") and rec["source"] != "none":
            notes_parts.append(f"authors_source={rec['source']}")
        note = escape_bibtex("; ".join(notes_parts)) if notes_parts else ""

        lines = [f"{entry_type}{{{citekey},"]
        if authors:
            lines.append(f"  author = {{{authors}}},")
            authored_count += 1
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
        # Preserve Windows file path from prior bib if present
        if citekey in file_fields:
            lines.append(f"  file = {file_fields[citekey]}")
            file_attached_count += 1
        lines.append("}")
        entries.append("\n".join(lines))

    now = datetime.now(timezone.utc).isoformat()
    header = (
        f"% Phase 8 Zotero bulk-import BibTeX — audited for author accuracy\n"
        f"% Regenerated: {now}\n"
        f"% Script: code/zotero_author_audit.py\n"
        f"% Audit sources: Crossref + OpenAlex + Semantic Scholar (cascade)\n"
        f"% Contents:\n"
        f"%   - {len(entries)} primary-study entries from extraction_matrix.csv\n"
        f"%   - {authored_count} entries with author field (vs 221 before audit)\n"
        f"%   - {file_attached_count} entries with PDF file attachment (Windows paths preserved)\n"
        f"%   - Manuscript-reference entries appended verbatim below\n"
        f"% Audit report: manuscript/zotero_author_audit.md\n\n\n"
        f"% ============================================================================\n"
        f"% Section A — {len(entries)} primary-study entries (authors audited)\n"
        f"% ============================================================================\n\n"
    )
    # Backup existing
    import shutil
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = ZOTERO_BIB.with_name(f"{ZOTERO_BIB.name}.bak-audit-{stamp}")
    shutil.copy2(ZOTERO_BIB, bak)
    print(f"  backup: {bak.relative_to(ROOT)}")

    ZOTERO_BIB.write_text(header + "\n\n".join(entries) + "\n\n" + manuscript_refs, encoding="utf-8")
    print(f"  wrote {ZOTERO_BIB.relative_to(ROOT)} ({ZOTERO_BIB.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"  authored entries: {authored_count}/{len(entries)} ({100*authored_count/len(entries):.1f}%)")
    print(f"  file-attached:    {file_attached_count}/{len(entries)}")

    # Emit audit report
    write_audit_report(cache, em, delta_counts, source_counts)
    print(f"  wrote {AUDIT_MD.relative_to(ROOT)}")
    return 0


def write_audit_report(
    cache: dict,
    em: pd.DataFrame,
    delta_counts: dict,
    source_counts: dict,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    total = len(em)
    updated = [r for r in cache.values() if r.get("delta") == "updated"]
    blank_filled = [r for r in cache.values() if r.get("delta") == "blank_filled"]
    still_blank = [r for r in cache.values() if r.get("delta") == "still_blank"]
    confirmed = sum(1 for r in cache.values() if r.get("delta") == "confirmed")

    lines = [
        "# Zotero-import author audit — documentation patch",
        "",
        f"**Generated:** {now}",
        f"**Script:** `code/zotero_author_audit.py`",
        f"**Scope:** `manuscript/zotero_import.bib` (not the reproducibility-trail extraction pipeline).",
        "",
        "## 1. Why this patch exists",
        "",
        "The Phase 2 Scopus retrieval (`artifacts/search/raw/scopus_20260413.csv`) returned 0% "
        "author coverage — the `authors` column was present but empty for all 4,156 rows. "
        "The OpenAlex-enrichment step (`artifacts/search/enriched/merged_openalex.csv`) brought "
        "author coverage to ~10%. By the time the corpus was screened + extracted into "
        "`artifacts/extraction/extraction_matrix.csv`, 221 of 640 papers (35%) had any author "
        "data. The remaining 65% arrived in Zotero-bulk-import blank.",
        "",
        "This audit re-fetches author data for **all** 640 primary-study entries from external "
        "authoritative sources in a cascade — Crossref → OpenAlex → Semantic Scholar — so the "
        "Zotero library delivered to the supervisors has consistent, citation-ready author data.",
        "",
        "## 2. Scope boundary (important for reproducibility)",
        "",
        "This audit is a **patch for documentation**. It writes only three files, all under "
        "`manuscript/`:",
        "",
        "- `manuscript/zotero_import.bib` — regenerated with audited authors.",
        "- `manuscript/.zotero_author_audit_cache.json` — per-paper audit records.",
        "- `manuscript/zotero_author_audit.md` — this report.",
        "",
        "It **does not modify** any reproducibility-trail artefact:",
        "",
        "- `artifacts/extraction/extraction_matrix.csv` — untouched; canonical Phase-3 output.",
        "- `artifacts/search/raw/*` and `artifacts/search/enriched/*` — untouched.",
        "- `artifacts/extraction/.crossref_author_cache.json` — untouched (Phase-7 artefact).",
        "",
        "Every downstream DoD check (Phase 4/5/6/7 dispatchers, paraphrase linter, "
        "supplementary zip) reads from the unmodified `extraction_matrix.csv` + synthesis "
        "artefacts, so this audit has zero effect on Phases 1–7 reproducibility claims.",
        "",
        "## 3. Audit method",
        "",
        "For each of 640 papers with a DOI, the cascade queried three sources in order and used "
        "the first source that returned a non-empty author list:",
        "",
        "1. **Crossref** (`api.crossref.org/works/{doi}`) — primary, covers DOI-registered works.",
        "2. **OpenAlex** (`api.openalex.org/works/doi:{doi}`) — fallback; broader preprint coverage.",
        "3. **Semantic Scholar** (`api.semanticscholar.org/graph/v1/paper/DOI:{doi}`) — final fallback.",
        "",
        "Polite-rate delays (0.1–1.0 s per request) were used. Names were returned in "
        "`Given Family` order and joined with ` and ` per BibTeX convention.",
        "",
        "Comparison against `extraction_matrix.csv` authors used a token-set normalisation "
        "(lowercase, accent-folded, punctuation-stripped, sorted token comparison) to classify "
        "each paper as:",
        "",
        "- `blank_filled` — extraction had no authors; audit found authors.",
        "- `confirmed` — extraction had authors; audit matches (token-set equal).",
        "- `updated` — extraction had authors; audit found a different (more-complete / corrected) list.",
        "- `no_change` — audit returned nothing; extraction's list is retained.",
        "- `still_blank` — neither extraction nor audit returned authors.",
        "",
        "## 4. Results",
        "",
        f"| Delta class | Count | % of {total} |",
        f"|---|---:|---:|",
    ]
    for k in ("blank_filled", "confirmed", "updated", "no_change", "still_blank"):
        n = delta_counts.get(k, 0)
        lines.append(f"| `{k}` | {n} | {100 * n / total:.1f}% |")

    lines += [
        "",
        "| Authoritative source | Count |",
        "|---|---:|",
    ]
    for k in ("crossref", "openalex", "semantic_scholar", "none", "cached"):
        if source_counts.get(k):
            lines.append(f"| {k} | {source_counts[k]} |")

    lines += [
        "",
        "## 5. Sample — papers with updated authors",
        "",
        "Papers where the audit produced a different list than extraction. These are cases where "
        "the extraction-matrix authors may have been truncated, partial, or in an incorrect order. "
        "Up to 20 samples shown.",
        "",
        "| paper_id | source | extraction authors | audited authors |",
        "|---|---|---|---|",
    ]
    for rec in updated[:20]:
        orig = "; ".join(rec.get("original_authors", []))[:80]
        auth = "; ".join(rec.get("authoritative_authors", []))[:80]
        lines.append(
            f"| `{rec['paper_id']}` | {rec.get('source','?')} | {orig} | {auth} |"
        )

    lines += [
        "",
        "## 6. Sample — papers where blanks were filled",
        "",
        f"{len(blank_filled)} papers had no authors in extraction_matrix and were successfully "
        "filled by the audit. First 15 shown.",
        "",
        "| paper_id | source | audited authors |",
        "|---|---|---|",
    ]
    for rec in blank_filled[:15]:
        auth = "; ".join(rec.get("authoritative_authors", []))[:90]
        lines.append(
            f"| `{rec['paper_id']}` | {rec.get('source','?')} | {auth} |"
        )

    lines += [
        "",
        f"## 7. Unresolved — still-blank after cascade ({len(still_blank)})",
        "",
        "Papers where neither extraction nor any external source returned authors. Typically "
        "`fallback:` paper_ids (no DOI) or very-new preprints not yet in Crossref/OpenAlex/S2.",
        "",
        "| paper_id | doi | notes |",
        "|---|---|---|",
    ]
    for rec in still_blank[:50]:
        lines.append(
            f"| `{rec['paper_id']}` | {rec.get('doi','')} | {rec.get('notes','')} |"
        )

    lines += [
        "",
        "## 8. How to re-run",
        "",
        "Cache at `manuscript/.zotero_author_audit_cache.json` persists all resolutions. Re-runs "
        "are instant unless the cache is deleted. To force a refresh, delete the cache and re-run:",
        "",
        "```",
        "rm manuscript/.zotero_author_audit_cache.json",
        "venv/bin/python code/zotero_author_audit.py",
        "```",
        "",
        "The script is idempotent: each run regenerates `zotero_import.bib` (backing up the "
        "previous version) and this audit report.",
    ]

    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
