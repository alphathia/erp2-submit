"""Task 8.2 — Reconcile Phase-7 hand-authored bibliography with Zotero master export.

Consumes `manuscript/references.bib` (17 Phase-7 entries) + `manuscript/references_zotero.bib`
(user's Zotero export after the Task 8.1 bulk-import). Produces:
  - manuscript/references.bib  (REPLACED) — Zotero entries re-keyed to match inline citekeys;
                                             Phase-7 fallbacks retained where no Zotero match
  - manuscript/references_diff.md  (NEW)  — audit trail
  - manuscript/draft.md + appendix.md     — inline citekeys rewritten where matches found

Design: design/8_2_reconcile_bib.md
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHASE7_BIB = ROOT / "manuscript" / "references.bib"
ZOTERO_BIB = ROOT / "manuscript" / "references_zotero.bib"
DRAFT_MD = ROOT / "manuscript" / "draft.md"
APPENDIX_MD = ROOT / "manuscript" / "appendix.md"
DIFF_MD = ROOT / "manuscript" / "references_diff.md"


# ---------------------------------------------------------------------------
# BibTeX parsing (minimal regex parser for well-formed input)
# ---------------------------------------------------------------------------

def parse_bibtex(text: str) -> list[dict]:
    """Parse a BibTeX file into a list of entry dicts.

    Each entry: {citekey, type, raw, fields: {lower_name: value}}
    where `raw` is the full entry text (for round-tripping).
    """
    entries = []
    # Match @type{citekey, ...fields...} with balanced braces
    pattern = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)
    for m in pattern.finditer(text):
        start = m.start()
        # Find matching closing brace
        depth = 0
        i = text.find("{", start)
        end = i
        while i < len(text):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
            i += 1
        raw = text[start : end + 1]
        fields = {}
        # Extract fields after the citekey comma
        body = raw[raw.find(",") + 1 : raw.rfind("}")]
        # Simple field matching: name = {value} or name = "value"
        for fm in re.finditer(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\")", body):
            name = fm.group(1).lower()
            value = fm.group(2)
            if value.startswith("{"):
                value = value[1:-1]
            elif value.startswith('"'):
                value = value[1:-1]
            fields[name] = value.strip()
        entries.append(
            dict(type=m.group(1).lower(), citekey=m.group(2).strip(), raw=raw, fields=fields)
        )
    return entries


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def normalise_doi(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    if s.startswith("https://doi.org/"):
        s = s[len("https://doi.org/") :]
    if s.startswith("doi:"):
        s = s[4:]
    return s


def extract_arxiv_id(fields: dict) -> str:
    for f in ("eprint", "url", "note", "doi"):
        v = fields.get(f, "")
        m = re.search(r"(?:arxiv[.:/])(\d{4}\.\d{4,5})", v, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


def first_author_surname(author_field: str) -> str:
    if not author_field:
        return ""
    first = author_field.split(" and ")[0].strip()
    # Handle "Last, First" vs "First Last"
    if "," in first:
        return first.split(",")[0].strip().lower()
    # Assume last token is the surname
    tokens = first.split()
    return tokens[-1].lower() if tokens else ""


def title_similarity(a: str, b: str) -> float:
    na = re.sub(r"[^a-z0-9 ]", "", a.lower()).strip()
    nb = re.sub(r"[^a-z0-9 ]", "", b.lower()).strip()
    return difflib.SequenceMatcher(None, na, nb).ratio()


def find_zotero_match(phase7_entry: dict, zotero_entries: list[dict]) -> dict | None:
    p_doi = normalise_doi(phase7_entry["fields"].get("doi", ""))
    # Primary — DOI match
    if p_doi:
        for z in zotero_entries:
            if normalise_doi(z["fields"].get("doi", "")) == p_doi:
                return z
    # Fallback 1 — arXiv ID
    p_arxiv = extract_arxiv_id(phase7_entry["fields"])
    if p_arxiv:
        for z in zotero_entries:
            if extract_arxiv_id(z["fields"]) == p_arxiv:
                return z
    # Fallback 2 — fuzzy author+year+title
    p_year = phase7_entry["fields"].get("year", "").strip()
    p_author = first_author_surname(phase7_entry["fields"].get("author", ""))
    p_title = phase7_entry["fields"].get("title", "")
    if not (p_year and p_author and p_title):
        return None
    best = None
    best_score = 0.0
    for z in zotero_entries:
        if z["fields"].get("year", "").strip() != p_year:
            continue
        if first_author_surname(z["fields"].get("author", "")) != p_author:
            continue
        sim = title_similarity(p_title, z["fields"].get("title", ""))
        if sim > best_score:
            best_score = sim
            best = z
    if best_score >= 0.8:
        return best
    return None


# ---------------------------------------------------------------------------
# Citekey rewriting
# ---------------------------------------------------------------------------

def rewrite_citekeys(text: str, mapping: dict[str, str]) -> tuple[str, int]:
    """Replace each phase7_key with zotero_key in `[...]` citation brackets.

    Returns (new_text, replacement_count).
    """
    count = 0

    def replace_bracket(m: re.Match) -> str:
        nonlocal count
        inner = m.group(1)
        # Split on `;` to handle multi-key brackets
        keys = [k.strip() for k in inner.split(";")]
        new_keys = []
        for k in keys:
            if k in mapping:
                new_keys.append(mapping[k])
                count += 1
            else:
                new_keys.append(k)
        return "[" + "; ".join(new_keys) + "]"

    # Only match brackets that look like citations (all-lowercase-digit-underscore + ';' + whitespace)
    new_text = re.sub(
        r"\[([a-z][a-z0-9_;\s]+)\]",
        replace_bracket,
        text,
    )
    return new_text, count


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------

def assemble_reconciled_bib(
    phase7: list[dict],
    zotero: list[dict],
    matches: dict[str, dict],
) -> str:
    """Build the replaced references.bib.

    For each Phase-7 citekey:
      - If matched: copy the Zotero entry's raw text but replace its citekey with
        the Phase-7 citekey (so inline [citekey] still resolves). Actually we
        rewrite the DRAFT's citekeys to match Zotero's — so copy Zotero raw
        verbatim, keyed on Zotero's own citekey.
      - If unmatched: copy the Phase-7 raw entry verbatim (fallback).
    """
    now = datetime.now(timezone.utc).isoformat()
    matched_count = sum(1 for m in matches.values() if m)
    unmatched_count = len(phase7) - matched_count
    header = (
        f"% Phase 8 reconciled bibliography\n"
        f"% Phase-7 entries: {len(phase7)}\n"
        f"% Zotero export entries: {len(zotero)}\n"
        f"% Matched: {matched_count}; Unmatched (Phase-7 fallback retained): {unmatched_count}\n"
        f"% Generated: {now}\n"
        f"% Zotero source: manuscript/references_zotero.bib\n\n"
    )
    entries = []
    for p in phase7:
        z = matches.get(p["citekey"])
        entries.append(z["raw"] if z else p["raw"])
    return header + "\n\n".join(entries) + "\n"


def write_diff_report(
    phase7: list[dict],
    zotero: list[dict],
    matches: dict[str, dict],
    match_method: dict[str, str],
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    matched = [p for p in phase7 if matches.get(p["citekey"])]
    unmatched = [p for p in phase7 if not matches.get(p["citekey"])]
    used_zotero_keys = {m["citekey"] for m in matches.values() if m}
    unused_zotero = [z for z in zotero if z["citekey"] not in used_zotero_keys]

    lines = [
        f"# references.bib reconciliation audit — {now[:10]}",
        f"",
        f"Phase-7 → Zotero matching; inputs: "
        f"{len(phase7)} Phase-7 entries + {len(zotero)} Zotero entries.",
        f"",
        f"## Matched ({len(matched)})",
        f"",
        f"| Phase-7 key | Zotero key | Method | Identifier |",
        f"|---|---|---|---|",
    ]
    for p in matched:
        z = matches[p["citekey"]]
        method = match_method.get(p["citekey"], "?")
        ident = normalise_doi(p["fields"].get("doi", "")) or extract_arxiv_id(p["fields"]) or "(fuzzy)"
        lines.append(f"| {p['citekey']} | {z['citekey']} | {method} | {ident} |")
    lines.append("")
    lines.append(f"## Unmatched Phase-7 citekeys ({len(unmatched)})")
    lines.append("")
    lines.append("Entries retained in output `references.bib` as Phase-7 fallback.")
    lines.append("")
    lines.append("| Phase-7 key | Title | Year | Reason |")
    lines.append("|---|---|---|---|")
    for p in unmatched:
        title = p["fields"].get("title", "")[:80]
        year = p["fields"].get("year", "")
        reason = "no DOI and no fuzzy match" if not normalise_doi(p["fields"].get("doi", "")) else "DOI not in Zotero export"
        lines.append(f"| {p['citekey']} | {title} | {year} | {reason} |")
    lines.append("")
    lines.append(f"## Zotero entries not cited in manuscript (informational, {len(unused_zotero)})")
    lines.append("")
    lines.append(
        f"The Zotero library contains {len(unused_zotero)} entries "
        f"not cited inline in draft.md or appendix.md. Expected — the user's Zotero "
        f"master library is typically larger than any single paper's citation set."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Report matching without writing any files.")
    parser.add_argument("--force", action="store_true",
                        help="Proceed even if Zotero export has fewer entries than Phase-7.")
    args = parser.parse_args()

    if not ZOTERO_BIB.exists():
        print(f"ERROR: {ZOTERO_BIB.relative_to(ROOT)} does not exist.")
        print("User must first export their Zotero library: File → Export Library")
        print(f"→ Better BibTeX → Save As {ZOTERO_BIB.relative_to(ROOT)}")
        return 2

    print(f"Parsing {PHASE7_BIB.relative_to(ROOT)} …")
    phase7 = parse_bibtex(PHASE7_BIB.read_text(encoding="utf-8"))
    print(f"  {len(phase7)} Phase-7 entries")

    print(f"Parsing {ZOTERO_BIB.relative_to(ROOT)} …")
    zotero = parse_bibtex(ZOTERO_BIB.read_text(encoding="utf-8"))
    print(f"  {len(zotero)} Zotero entries")

    # Match
    print("Matching Phase-7 entries against Zotero export …")
    matches: dict[str, dict | None] = {}
    match_method: dict[str, str] = {}
    for p in phase7:
        z = find_zotero_match(p, zotero)
        matches[p["citekey"]] = z
        if z:
            if normalise_doi(p["fields"].get("doi", "")) and normalise_doi(z["fields"].get("doi", "")):
                match_method[p["citekey"]] = "DOI"
            elif extract_arxiv_id(p["fields"]):
                match_method[p["citekey"]] = "arXiv ID"
            else:
                match_method[p["citekey"]] = "fuzzy (author+year+title)"
    matched_count = sum(1 for m in matches.values() if m)
    unmatched_count = len(phase7) - matched_count
    print(f"  Matched: {matched_count}; Unmatched: {unmatched_count}")

    if args.dry_run:
        print("[dry-run] diff report preview:")
        print(write_diff_report(phase7, zotero, matches, match_method))
        return 0 if unmatched_count == 0 else 1

    # Backups
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for p in (PHASE7_BIB, DRAFT_MD, APPENDIX_MD):
        bak = p.with_name(f"{p.name}.bak-before-zotero-{stamp}")
        shutil.copy2(p, bak)
        print(f"  backup: {bak.relative_to(ROOT)}")

    # Write reconciled references.bib
    reconciled = assemble_reconciled_bib(phase7, zotero, matches)
    PHASE7_BIB.write_text(reconciled, encoding="utf-8")
    print(f"  wrote {PHASE7_BIB.relative_to(ROOT)}")

    # Rewrite citekeys in draft + appendix
    mapping = {p["citekey"]: matches[p["citekey"]]["citekey"] for p in phase7 if matches.get(p["citekey"])}
    total_replacements = 0
    for p in (DRAFT_MD, APPENDIX_MD):
        old_text = p.read_text(encoding="utf-8")
        new_text, count = rewrite_citekeys(old_text, mapping)
        if count:
            p.write_text(new_text, encoding="utf-8")
            print(f"  rewrote {count} citekey occurrences in {p.relative_to(ROOT)}")
            total_replacements += count
    print(f"  total citekey replacements: {total_replacements}")

    # Diff report
    diff_text = write_diff_report(phase7, zotero, matches, match_method)
    DIFF_MD.write_text(diff_text, encoding="utf-8")
    print(f"  wrote {DIFF_MD.relative_to(ROOT)}")

    print()
    if unmatched_count == 0:
        print("OK all Phase-7 citekeys matched in Zotero export.")
        return 0
    print(f"WARN {unmatched_count} unmatched Phase-7 citekey(s); fallback entries retained in references.bib.")
    print(f"     See {DIFF_MD.relative_to(ROOT)} §Unmatched for the list.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
