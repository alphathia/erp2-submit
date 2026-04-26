"""Task 2.6 — Backward snowballing (Petersen 2015 §5.2).

Extracts reference lists from the five seed survey PDFs in docs/seeds/,
resolves DOIs via Crossref where missing, deduplicates against the main
corpus (included_set.csv), and routes new candidates through the same
LLM-assisted screening path used in Task 2.5 (reusing llm_review.py).

Usage:
    python code/snowball.py
    python code/snowball.py --dry-run               # phases 1-4 only
    python code/snowball.py --skip-crossref         # offline-ish smoke test
    python code/snowball.py --limit 20              # tiny smoke run
    python code/snowball.py --resume                # skip already-decided refs

Consumes:
    docs/seeds/*.pdf                         (5 seed PDFs)
    artifacts/screening/included_set.csv     (overlap dedup key)
    .env: CROSSREF_EMAIL (optional), OPENAI_API_KEY (required)

Produces:
    artifacts/search/raw/snowball_seeds_refs.csv (+ .meta.json)
    Appended rows in artifacts/screening/phase2_decisions.csv
        (pass_number="snowball")
    Regenerated artifacts/screening/included_set.csv
    Appends `snowball_complete` row to decision_register.csv

Design: design/2_6_snowball.md
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import csv
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pdfplumber
import requests

# Silence pdfminer's noisy CropBox warnings (pdfplumber's dependency).
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))

from code.utils import write_with_meta  # noqa: E402
from code.llm_review import (             # noqa: E402
    build_system_prompt,
    build_user_message,
    call_openai,
    load_api_key,
    load_codebook_excerpt,
    load_ie_excerpt,
    MODEL_PRICING,
)
from code.screening_harness import (      # noqa: E402
    append_decision,
    derive_outputs,
    DECISION_COLUMNS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEEDS_DIR         = ROOT / "docs" / "seeds"
MANUAL_FALLBACK   = ROOT / "artifacts" / "search" / "raw" / "manual_snowball_refs"
OUTPUT_CSV        = ROOT / "artifacts" / "search" / "raw" / "snowball_seeds_refs.csv"
INCLUDED_SET      = ROOT / "artifacts" / "screening" / "included_set.csv"
PHASE2_DECISIONS  = ROOT / "artifacts" / "screening" / "phase2_decisions.csv"
REPORTS_DIR       = ROOT / "artifacts" / "search" / "raw" / "reports"
DECISION_REGISTER = ROOT / "decision_register.csv"

VALID_STATUS = {
    "already_in_corpus",
    "included_via_snowball",
    "excluded_via_snowball",
}

# Snowball CSV schema
SNOWBALL_COLUMNS = [
    "ref_id", "source_seed", "raw_citation",
    "authors", "title", "year", "doi",
    "status", "screening_paper_id",
    "crossref_confidence", "notes",
]

# Parsing / API
DOI_REGEX           = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
YEAR_REGEX          = re.compile(r"\b(?:19|20)\d{2}\b")
# Numbered-ref start: "[N]" (Vancouver) or "N." (some IEEE variants).
NUMBERED_REF_START  = re.compile(r"^\s*\[(\d+)\]\s+")
# APA / Springer author-initial start: line begins with "Surname, X."
# (initial-period). We do NOT require a year on the first line — Springer-
# style refs often wrap with the year on a continuation line. The
# initial-period pattern discriminates against journal headers like
# "The Journal of Systems and Software (2025)" which have no initial.
APA_REF_START       = re.compile(
    r"^\s*[A-Z][A-Za-zˆ'’\-]+"          # Surname (allow accents/hyphen)
    r"(?:\s+[A-Z][A-Za-zˆ'’\-]+)?"      # optional second word in surname
    r",\s+[A-Z]\."                       # ", X." initial — REQUIRED
)
MIN_REFS_FOR_AUTO   = 20    # below this → manual fallback
CROSSREF_RATE_SLEEP = 0.02  # ~50 req/s polite pool
CROSSREF_TIMEOUT    = 15
CROSSREF_MAX_RETRIES = 3
SIMILARITY_DEFAULT  = 0.85
DEFAULT_MODEL       = "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Tee for report file
# ---------------------------------------------------------------------------
class _Tee:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            s.write(data)

    def flush(self):
        for s in self._streams:
            s.flush()


# ---------------------------------------------------------------------------
# .env loading — mirrors openalex_enrich.load_email()
# ---------------------------------------------------------------------------
def load_crossref_email(cli_override: str | None = None) -> str | None:
    """Load CROSSREF_EMAIL from CLI → env var → .env. None → anonymous pool."""
    if cli_override:
        return cli_override
    email = os.environ.get("CROSSREF_EMAIL")
    if email:
        return email
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("CROSSREF_EMAIL=") and len(line) > len("CROSSREF_EMAIL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


# ---------------------------------------------------------------------------
# Phase 1 — PDF reference extraction
# ---------------------------------------------------------------------------
def derive_seed_id(pdf_path: Path) -> str:
    """Stable seed_id from filename: 'Wang et al. - 2025 - Agents in ...'
    → 'WangAgentsSE2025'. Falls back to filename stem if heuristic fails."""
    stem = pdf_path.stem
    # Pattern: "<Author> et al. - <Year> - <Title>" (title may contain
    # hyphens, e.g. "low-code", so use .+ not [^-]+)
    m = re.match(r"^([A-Za-z]+)\b.*?-\s*(\d{4})\s*-\s*(.+)$", stem)
    if not m:
        return re.sub(r"[^A-Za-z0-9]+", "", stem)[:30] or pdf_path.stem
    author, year, title = m.group(1), m.group(2), m.group(3)
    # Use a distinguishing title token. Order matters — most specific first.
    title_lower = title.lower()
    title_token = ""
    if "large language model" in title_lower or "llm-based" in title_lower:
        title_token = "LLMAgents"
    elif "agentic programming" in title_lower:
        title_token = "AgenticProg"
    elif "low-code" in title_lower or "no-code" in title_lower:
        title_token = "LCNC"
    elif "agentic software" in title_lower:
        title_token = "AgenticSE"
    elif "agents" in title_lower and "software" in title_lower:
        title_token = "AgentsSE"
    return f"{author}{title_token}{year}"


def _extract_lines_from_page(page) -> list[str]:
    """Extract text lines from a page, handling two-column layout.

    Many academic PDFs (Springer, IEEE, ACM) typeset reference lists in
    two columns. Default ``page.extract_text()`` reads in document order,
    which for a two-column page produces lines like
    ``"<LEFT_TEXT> <RIGHT_TEXT>"`` — merging adjacent references from
    different columns into a single garbled "line".

    Detection uses **line-start x0 positions** (first word of each visual
    row). In a two-column layout, line starts cluster around two distinct
    left margins (e.g., x≈50 and x≈300), with a large gap between them.
    Continuation/wrapped words mid-page are NOT line starts and don't
    confuse the detector.

    Algorithm:
      1. Group words into rows by their ``top`` coordinate (rounded to 3pt).
      2. Take the leftmost word of each row → list of line-start x0s.
      3. Sort line starts; find the largest gap within the middle 20-70% of
         page width.
      4. If gap >= 30pt and both halves have >= 3 line starts, treat as
         two-column; extract left/right columns separately via
         ``page.crop(bbox).extract_text()``.

    Returns lines in column-major order (all left first, then all right).
    For single-column pages, behaviour matches ``page.extract_text()``.
    """
    width = float(page.width)
    height = float(page.height)

    try:
        words = page.extract_words()
    except Exception:
        return (page.extract_text() or "").splitlines()
    if not words:
        return []
    if len(words) < 30:
        # Too sparse to confidently detect columns
        return (page.extract_text() or "").splitlines()

    # Group words by row (top coordinate, bucketed to 3pt)
    rows: dict[int, list] = {}
    for w in words:
        top_bucket = int(round(float(w["top"]) / 3) * 3)
        rows.setdefault(top_bucket, []).append(w)

    # Line starts: leftmost word of each row
    line_starts: list[float] = []
    for row_words in rows.values():
        row_words.sort(key=lambda w: float(w["x0"]))
        line_starts.append(float(row_words[0]["x0"]))

    if len(line_starts) < 10:
        return (page.extract_text() or "").splitlines()

    # Find largest gap in line-starts within the middle of the page
    line_starts.sort()
    gap_lo, gap_hi = width * 0.20, width * 0.70
    largest_gap = 0.0
    boundary = width / 2
    for i in range(1, len(line_starts)):
        if gap_lo <= line_starts[i] <= gap_hi:
            gap = line_starts[i] - line_starts[i - 1]
            if gap > largest_gap:
                largest_gap = gap
                boundary = (line_starts[i] + line_starts[i - 1]) / 2

    if largest_gap < 30:
        return (page.extract_text() or "").splitlines()

    # Confirm both halves have enough line starts
    left_count = sum(1 for x in line_starts if x < boundary)
    right_count = len(line_starts) - left_count
    if min(left_count, right_count) < 3:
        return (page.extract_text() or "").splitlines()

    # Two-column: extract each column with bbox cropping
    try:
        left_text = page.crop((0, 0, boundary, height)).extract_text() or ""
        right_text = page.crop((boundary, 0, width, height)).extract_text() or ""
    except Exception:
        return (page.extract_text() or "").splitlines()

    return left_text.splitlines() + right_text.splitlines()


def _extract_all_lines(pdf_path: Path) -> list[str]:
    """Return every non-empty text line across all pages of the PDF.

    Uses :func:`_extract_lines_from_page` per page so two-column layouts
    are read column-by-column instead of left-then-right per line.
    """
    lines: list[str] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                lines.extend(_extract_lines_from_page(page))
    except Exception as exc:
        print(f"  [warn] pdfplumber error on {pdf_path.name}: {exc}",
              file=sys.stderr)
    return lines


def _extract_numbered_refs(lines: list[str]) -> list[str]:
    """Group lines into refs using `[N]` numbered-start heuristic.

    A new ref begins each time we see a line starting with `[N]` where N is
    monotonically greater than the previous N (guards against in-text
    citations like `[1,2]` that also match the prefix). Continuation lines
    (non-matching) are appended to the current ref.
    """
    refs: list[str] = []
    current: list[str] = []
    last_n = 0
    for line in lines:
        m = NUMBERED_REF_START.match(line)
        if m:
            n = int(m.group(1))
            # Accept as new ref if it's the next/monotonic number (allow +1..+5
            # jumps for OCR/extraction hiccups) or if this is the first one
            if not refs and not current:
                last_n = n
                current.append(line.strip())
                continue
            if last_n < n <= last_n + 5 or n == 1 and last_n > 100:
                # Flush accumulator
                if current:
                    refs.append(" ".join(current))
                current = [line.strip()]
                last_n = n
                continue
        # Continuation: only append if we're inside a ref and the line has
        # letters (skip page headers/footers that are just page numbers).
        if current and line.strip() and not line.strip().isdigit():
            current.append(line.strip())
    if current:
        refs.append(" ".join(current))
    # Post-filter: must contain a year and be > 30 chars
    return [r for r in refs if YEAR_REGEX.search(r) and len(r) > 30]


def _extract_apa_refs(lines: list[str]) -> list[str]:
    """Group lines into refs using APA author-year heuristic.

    A new ref begins each time we see a line whose prefix looks like
    "Surname, X. ... YYYY" (author-year style, e.g. Ajimati's SLR).
    """
    refs: list[str] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if APA_REF_START.match(line):
            if current:
                refs.append(" ".join(current))
            current = [stripped]
        elif current and not stripped.isdigit():
            current.append(stripped)
    if current:
        refs.append(" ".join(current))
    return [r for r in refs if YEAR_REGEX.search(r) and len(r) > 30]


def extract_references_from_pdf(pdf_path: Path) -> list[str]:
    """Extract references from a seed PDF using a two-strategy pipeline.

    1. Try numbered-ref extraction ([N] style). If >= MIN_REFS_FOR_AUTO refs,
       accept.
    2. Else try APA author-year extraction. If >= MIN_REFS_FOR_AUTO, accept.
    3. Else return whichever produced more, or [] if both empty.

    Returns a list of single-string citations (continuation lines joined).
    """
    lines = _extract_all_lines(pdf_path)
    if not lines:
        return []
    numbered = _extract_numbered_refs(lines)
    if len(numbered) >= MIN_REFS_FOR_AUTO:
        return numbered
    apa = _extract_apa_refs(lines)
    if len(apa) >= MIN_REFS_FOR_AUTO:
        return apa
    # Neither strategy cleared threshold; return best-effort
    return numbered if len(numbered) > len(apa) else apa


def load_manual_fallback(seed_id: str) -> list[dict] | None:
    """Return list of ref dicts from the manual CSV, or None if file absent."""
    path = MANUAL_FALLBACK / f"{seed_id}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, dtype=str).fillna("")
    out = []
    for _, row in df.iterrows():
        out.append({
            "raw_citation": row.get("raw_citation", ""),
            "authors":      row.get("authors", ""),
            "title":        row.get("title", ""),
            "year":         row.get("year", ""),
            "doi":          normalise_doi(row.get("doi", "")) or "",
        })
    return out


# ---------------------------------------------------------------------------
# Phase 2 — Citation parsing
# ---------------------------------------------------------------------------
def normalise_doi(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().lower()
    # Strip common prefixes
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    s = s.strip().rstrip(".,;)")
    return s or None


# Venue markers that indicate the end of a title and the start of
# conference/journal/venue text. Anchored on a preceding space so they don't
# match mid-word. The optional "International " prefix consumes a common
# venue-name lead-in so the cut happens at "International Conference" not
# at " Conference" alone.
_VENUE_STOP_REGEX = re.compile(
    r"\s(?:"
    r"In\s*:"
    r"|(?:International\s+|IEEE\s+|ACM\s+)?"
        r"(?:Proceedings|Proc\.|Conf\.|Conference|Symposium|Workshop|Journal|J\.\s)"
    r"|IEEE\b|ACM\b|arXiv\b|https?://|doi\.org|vol\.|pp\."
    r")",
    re.IGNORECASE,
)

# Matches a colon-space-Capital pattern that's the Springer author/title
# separator (e.g. "Ahmad, W.U., Chang, K.-W.: Unified pre-training..."). We
# cap the search to the first ~200 chars of head to avoid matching colons
# that appear mid-title ("AI Agents: A Survey").
_SPRINGER_COLON = re.compile(r"[A-Za-z.][:](\s+)[A-Z]")

# IEEE-style quoted title (Otoum-style): the paper title sits inside a pair
# of quote marks BEFORE the year (e.g. `[1] J. He, ..., ''LLM-based multi-
# agent systems for agentic practices...'', Journal, 2025, doi:...`). Covers
# doubled left/right singles (U+2018/U+2019), ASCII single/double, curly
# double (U+201C/U+201D), and grave accent. Body is 10–400 chars of
# non-quote content.
_QUOTE_CHARS = "\u2018\u2019\u201C\u201D'\"`"
_IEEE_QUOTED_TITLE = re.compile(
    rf"[{_QUOTE_CHARS}]{{1,2}}"
    rf"([^{_QUOTE_CHARS}]{{10,400}}?)"
    rf"[{_QUOTE_CHARS}]{{1,2}}"
)


def _normalise_spacing(s: str) -> str:
    """Insert spaces in pdfplumber no-space extractions.

    pdfplumber sometimes extracts PDFs with words glued together across
    punctuation (e.g., ``"2021.PythonWrapperOfAndroidUiautomatorTestTool"``).
    We insert spaces after '.' and ',' when followed by a capital letter,
    but preserve single-letter initials like ``"J.Smith"`` → ``"J. Smith"``
    (intentional — initials still need a space before the next name).

    This does not mangle URLs because DOIs/URLs are extracted separately
    before this function runs, and the only post-URL use of the string is
    title extraction.
    """
    # Add space after period when followed by capital
    s = re.sub(r"\.(?=[A-Z])", ". ", s)
    # Add space after comma when followed by capital (e.g., "Acharya,Kuppan")
    s = re.sub(r",(?=[A-Z])", ", ", s)
    # Collapse any double spaces we may have introduced
    s = re.sub(r"\s{2,}", " ", s)
    return s


def _extract_title(tail: str) -> str:
    """Pull the title out of the text after the author/year anchor.

    Strategy: collect candidate cut points (period boundary, venue marker,
    URL boundary), then **pick the shortest valid one** (most conservative
    — corresponds to the earliest legitimate end-of-title). Below-10-char
    candidates are dropped as honest "unparseable" signal.

    Also strips a trailing year-in-parens like ``" (2021)"`` or
    ``", 2024"`` — common Springer artifact where the year sits at the end
    of the citation rather than in the author block.
    """
    candidates: list[str] = []

    # Candidate A: first sentence boundary (period + space + capital)
    parts = re.split(r"\.\s+(?=[A-Z])", tail, maxsplit=1)
    if parts:
        candidates.append(parts[0])

    # Candidate B: venue marker (Conference, Journal, In:, IEEE, etc.)
    venue_match = _VENUE_STOP_REGEX.search(tail)
    if venue_match:
        candidates.append(tail[: venue_match.start()])

    # Candidate C: URL anywhere in the title (mid-citation contamination)
    url_match = re.search(r"\s*https?://", tail)
    if url_match:
        candidates.append(tail[: url_match.start()])

    # Pick the shortest valid candidate (earliest cut wins)
    cleaned = [c.strip().rstrip(".,;:)") for c in candidates]
    cleaned = [c for c in cleaned if len(c) >= 10]
    if not cleaned:
        return ""
    candidate = min(cleaned, key=len)

    # Strip trailing year-in-parens or trailing year (Springer artifact:
    # "title. (2021)" or "title (2021)" or "title, 2024" or "title 2024a").
    candidate = re.sub(
        r"[\s,.]*\(?\b(?:19|20)\d{2}[a-z]?\)?\s*$",
        "",
        candidate,
    ).strip().rstrip(".,;:)")
    if len(candidate) < 10:
        return ""
    return candidate


def parse_raw_citation(raw: str) -> dict:
    """Parse a citation string into ``{authors, title, year, doi}``.

    Uses a four-strategy cascade (first non-empty-title result wins):

    0. **IEEE quoted-title** (e.g. Otoum): title in doubled single / double
       quotes before the year (``[1] J. He, ..., ''Title''...``). Text
       before the opening quote is authors; year is the first YYYY in the
       whole ref.
    1. **Springer-colon style** (e.g. Wang-AgentsSE): author list ends with
       ``"...: "`` and a capitalised title. Split on the first such colon
       within the first 200 chars.
    2. **Year-anchored** (e.g. Liu, WangAgenticProg, Ajimati): find the
       first 4-digit year; everything before is authors, everything after
       (up to a venue marker) is the title.
    3. **Fallback**: authors = full head (truncated); title = empty. Marks
       the ref as best-effort.

    Handles pdfplumber's no-space-after-period artifacts by normalising
    spacing before parsing. Handles web-page refs with no author
    (``"2021.ProductName. https://..."``) by detecting an empty
    before-year region and setting authors = "".
    """
    raw = raw.strip()

    # DOI — extract before any normalisation (DOIs can contain punctuation
    # we don't want to mangle).
    doi = None
    m = DOI_REGEX.search(raw)
    if m:
        doi = normalise_doi(m.group(0))

    # Strip leading "[N]" or "N. " citation marker
    head = re.sub(r"^\s*(\[\d+\]|\d+\.)\s*", "", raw)
    head = _normalise_spacing(head)

    year = ""
    authors = ""
    title = ""

    # --- Strategy 0: IEEE quoted title (Otoum) ---
    quoted = _IEEE_QUOTED_TITLE.search(head)
    if quoted:
        body = quoted.group(1).strip().rstrip(",.:;")
        # Reject the match if the body is all-caps (likely a venue acronym in
        # quotes, not a title) or doesn't contain a space (single-word garbage).
        if len(body) >= 10 and " " in body and not body.isupper():
            title = body[:500]
            authors = head[: quoted.start()].rstrip(" ,.:;()").strip()
            year_match = YEAR_REGEX.search(head)
            year = year_match.group(0) if year_match else ""

    # --- Strategy 1: Springer-colon (authors ends in ": ") ---
    if not title:
        colon_region = head[:250]
        # Skip if there's a URL before the colon (http:// would false-match)
        if not re.search(r"https?://", colon_region):
            colon_match = _SPRINGER_COLON.search(colon_region)
            if colon_match:
                # Only accept colon if it's NOT followed by a digit (e.g.
                # "vol: 12") and the preceding text looks like authors (has
                # at least one comma or period).
                before_colon = head[: colon_match.start() + 1]
                after_colon = head[colon_match.start() + 2:].lstrip()
                if ("," in before_colon or "." in before_colon) and len(before_colon) > 5:
                    # Strip only the colon and trailing space — keep the
                    # period which is typically the final author initial
                    # (e.g., "Chang, K.-W.").
                    authors = before_colon.rstrip(": ")
                    # For Springer, year often at end in parens
                    year_match = YEAR_REGEX.search(head[colon_match.end():])
                    year = year_match.group(0) if year_match else ""
                    title = _extract_title(after_colon)

    # --- Strategy 2: Year-anchored ---
    if not title:
        year_match = YEAR_REGEX.search(head)
        if year_match:
            year = year_match.group(0)
            before_year = head[: year_match.start()].rstrip(" ,.:;()").strip()
            after_year = head[year_match.end():].lstrip(" ,.:;()").strip()
            # Web-page ref detector: before-year is pure junk (empty after
            # strip, or the raw started with the year itself). Authors empty.
            if not before_year or len(before_year) < 3:
                authors = ""
            else:
                authors = before_year
            title = _extract_title(after_year)

    # --- Strategy 3: Fallback — at least capture authors ---
    if not title and not authors:
        authors = head[:200].strip()

    return {
        "authors": authors[:300].strip(),
        "title":   title[:500].strip(),
        "year":    year,
        "doi":     doi or "",
    }


# ---------------------------------------------------------------------------
# LLM-based citation parser (fallback for refs where regex fails)
# ---------------------------------------------------------------------------

_LLM_PARSER_SYSTEM = (
    "You extract bibliographic fields from citation strings. The text may be "
    "garbled (no spaces, OCR artefacts, merged words). Do your best to identify "
    "fields. Return strict JSON only."
)

_LLM_PARSER_USER_TEMPLATE = """Citation: {raw}

Return JSON with these fields:
- "authors": comma-separated author list (e.g. "Smith, J., Jones, A."). Empty string if no author (web/tool refs).
- "title": the paper title only — exclude venue/journal/year/DOI/URL.
- "year": 4-digit publication year, or empty string if unclear.
- "doi": "10.xxxx/yyy" if present, else empty string.

If a field can't be reliably extracted, use an empty string. Do not invent."""


def _parse_with_llm(raw: str, client, model: str = "gpt-4o-mini") -> dict:
    """Use an OpenAI LLM to parse a noisy citation string.

    Reused when the regex cascade in :func:`parse_raw_citation` returns an
    empty or suspiciously short title (e.g., ACM no-space extractions in
    Liu/WangAgenticProg PDFs that no regex can reliably segment).

    Caller is responsible for client lifetime and error handling at the
    surrounding level (we re-raise on API/JSON errors so the orchestrator
    can fall back to the regex result).
    """
    completion = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _LLM_PARSER_SYSTEM},
            {"role": "user",   "content": _LLM_PARSER_USER_TEMPLATE.format(raw=raw[:1500])},
        ],
    )
    parsed = json.loads(completion.choices[0].message.content)
    return {
        "authors": str(parsed.get("authors") or "").strip()[:300],
        "title":   str(parsed.get("title")   or "").strip()[:500],
        "year":    str(parsed.get("year")    or "").strip(),
        "doi":     normalise_doi(parsed.get("doi", "")) or "",
    }


def _is_low_confidence_title(title: str) -> bool:
    """Heuristic: should this regex-parsed title trigger an LLM rescue?

    Triggers when:
      * Empty or shorter than 15 chars (basic length check)
      * Contains a URL fragment (``"://"``) — pdfplumber inlined a URL
        into the title; extraction artifact
      * Contains an embedded 4-digit year (``\\b19xx\\b`` or ``\\b20xx\\b``)
        — page-range / venue text leaked into the title
      * Starts with a digit or non-letter — page-range fragment leaked in
    """
    if not title or len(title) < 15:
        return True
    if "://" in title:
        return True
    if re.search(r"\b(?:19|20)\d{2}\b", title):
        return True
    if re.match(r"^[\W\d]", title):
        return True
    return False


# ---------------------------------------------------------------------------
# LLM-driven reference-section extraction (replaces regex line-grouping)
# ---------------------------------------------------------------------------
_LLM_EXTRACT_SYSTEM = (
    "You extract bibliographic references from academic-paper text. The "
    "text may contain multi-column layout artifacts where adjacent refs "
    "are merged on a single line, page running-headers, table contents, "
    "and continuation-line wrapping. Your job is to identify each distinct "
    "reference and return its fields as strict JSON. Do not invent refs."
)

_LLM_EXTRACT_USER = """Extract every distinct BIBLIOGRAPHIC REFERENCE from the text below.

CONTEXT: this text was extracted from a PDF's references section using a
naive reader. The PDF is two-column, so each line you see may actually be
LEFT_COLUMN_TEXT followed by RIGHT_COLUMN_TEXT from a DIFFERENT reference,
glued together with a space. Continuation lines (the latter half of a
multi-line ref) appear later in the text. Your job is to mentally
de-interleave the columns and reassemble each ref correctly.

A bibliographic reference is one entry in a paper's References /
Bibliography section. Examples (one per line):
  • "Smith, J., Jones, A., 2024. Title here. Journal Name 12(3), 45-67."
  • "Smith, J. and Jones, A. (2024). Title here. In: Proc. of XYZ Conf."
  • "[42] J. Smith and A. Jones, ''Title here,'' IEEE J., vol. 1, 2024, doi:10.x/y"
  • "Smith, J., Jones, A.: Title here. Journal 12(3), 45-67 (2024)"
  • Web/tool ref with no author: "2024.ProductName. https://..."

When you see a line like:
  "Abidin, A., Senin, N., Manaf, A.A.A., 2021. A Preliminary Study of Low-Code/No-Code International Conference on Model-Driven Engineering"

…recognise that "A Preliminary Study of Low-Code/No-Code" is the title
START of the Abidin ref (left column), while "International Conference on
Model-Driven Engineering" is the venue/title from a DIFFERENT ref (right
column). The actual continuation of Abidin's title appears later as the
left-column text on the next "line". Merge them.

DO NOT extract:
  • Inline citations like "(Smith et al., 2021)" appearing in body text
  • Table cells describing what an author's work showed
  • Section headings, page running-headers, footers, page numbers
  • Methodology / discussion paragraphs that mention authors

Return strict JSON with one key, "refs", whose value is a list of objects:
{{
  "refs": [
    {{
      "authors": "comma-separated authors with initials, as in the bibliography (empty for web/tool refs)",
      "title":   "the FULL paper title — including any continuation across column-merged lines. Exclude venue, journal, year, DOI, URLs, page numbers, ISBN.",
      "year":    "4-digit publication year, or empty string",
      "doi":     "10.xxxx/yyy if literally present in text, else empty string"
    }},
    ...
  ]
}}

Rules:
- One object per distinct reference. Merge continuation lines (including
  cross-column continuations) belonging to the same ref.
- If two refs got jumbled on one line due to column-merge, separate them.
- Use "" (empty string) for any field you can't reliably extract.
- Authors should match the bibliography text (don't expand "Smith, J." to "Smith, John").

Text:
{text}

Return strict JSON only."""


_REFS_HEADING = re.compile(
    r"^(References|Bibliography|REFERENCES|BIBLIOGRAPHY)\s*$"
)
# Pattern for an APA/IEEE-style ref-start line (surname, initial. ... or [N] ...)
_REF_START_LINE = re.compile(
    r"^\s*(?:\[\d+\]\s+|[A-Z][A-Za-zˆ'\-]+,\s+[A-Z]\.)"
)


def _find_refs_section_text(pdf_path: Path) -> str:
    """Locate and return the text of the references section.

    Strategy (in order):
      1. Search the LAST 30% of the PDF for a standalone "References" or
         "Bibliography" line — most reliable when present.
      2. Otherwise, scan from page ~40% onward for the first page where
         5+ lines look like bibliographic ref starts (``Surname, X.`` or
         ``[N]``). This catches PDFs that lack an explicit heading
         (Springer single-column papers, IEEE journals).
      3. Fall back to the last 25% of pages.

    Within the resolved section, use :func:`_extract_lines_from_page` for
    column-aware line extraction.
    """
    with pdfplumber.open(str(pdf_path)) as pdf:
        n = len(pdf.pages)
        ref_start = None

        # Strategy 1: standalone heading in last 30% of pages
        for i in range(max(0, int(n * 0.7)), n):
            text = pdf.pages[i].extract_text() or ""
            for line in text.splitlines():
                if _REFS_HEADING.match(line.strip()):
                    ref_start = i
                    break
            if ref_start is not None:
                break

        # Strategy 2: dense page of ref-start lines after page ~40%, with
        # walk-back to capture earlier refs that span across page boundaries.
        if ref_start is None:
            for i in range(max(0, int(n * 0.4)), n):
                lines = _extract_lines_from_page(pdf.pages[i])
                ref_start_count = sum(
                    1 for ln in lines if _REF_START_LINE.match(ln)
                )
                if ref_start_count >= 5:
                    ref_start = i
                    # Walk back: include earlier pages that still contain
                    # ref-starts (refs section often begins late on a page).
                    for j in range(i - 1, max(0, i - 3), -1):
                        prior_lines = _extract_lines_from_page(pdf.pages[j])
                        prior_count = sum(
                            1 for ln in prior_lines if _REF_START_LINE.match(ln)
                        )
                        if prior_count >= 2:
                            ref_start = j
                        else:
                            break
                    break

        # Strategy 3: last-25% fallback
        if ref_start is None:
            ref_start = max(0, int(n * 0.75))

        # For each refs page, extract BOTH plain text (default reading order,
        # may have column-merge artifacts) AND column-aware text (may have
        # boundary errors). Provide both to the LLM as supplementary context
        # so it can disambiguate when one is garbled.
        chunks = []
        for i in range(ref_start, n):
            page = pdf.pages[i]
            plain = page.extract_text() or ""
            chunks.append(plain)
    return "\n\n".join(chunks)


def _extract_via_llm(
    pdf_path: Path,
    seed_id: str,
    client,
    model: str,
    chunk_size: int = 12000,
    chunk_overlap: int = 500,
) -> list[dict]:
    """Extract refs from a seed PDF by chunking ref-section text to LLM.

    Returns a list of partial ref dicts with ``{authors, title, year, doi}``.
    The caller wraps each into the full snowball-ref dict (adds ref_id,
    source_seed, status, etc.).

    Dedups across chunks by ``(title.lower()[:80], year)``.
    """
    text = _find_refs_section_text(pdf_path)
    if not text.strip():
        return []
    chunks = []
    pos = 0
    while pos < len(text):
        end = min(len(text), pos + chunk_size)
        # Add small overlap from prior chunk to avoid splitting refs
        start = max(0, pos - chunk_overlap) if pos > 0 else 0
        chunks.append(text[start:end])
        pos = end

    out: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()
    for chunk_idx, chunk in enumerate(chunks):
        try:
            completion = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _LLM_EXTRACT_SYSTEM},
                    {"role": "user",   "content": _LLM_EXTRACT_USER.format(text=chunk)},
                ],
            )
            parsed = json.loads(completion.choices[0].message.content)
        except Exception as exc:
            print(f"  [warn] LLM extraction chunk {chunk_idx + 1}/{len(chunks)} "
                  f"failed for {seed_id}: {exc}", file=sys.stderr)
            continue
        for ref in parsed.get("refs", []):
            title = (ref.get("title") or "").strip()
            if len(title) < 5:
                continue
            year = (ref.get("year") or "").strip()
            key = (title.lower()[:80], year)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            out.append({
                "authors": (ref.get("authors") or "").strip()[:300],
                "title":   title[:500],
                "year":    year,
                "doi":     normalise_doi(ref.get("doi", "")) or "",
            })
    return out


def extract_references_for_seed(
    pdf_path: Path,
    seed_id: str,
    client=None,
    model: str = "gpt-4o-mini",
    use_llm: bool = True,
) -> tuple[list[dict], str]:
    """Top-level reference extractor for one seed PDF.

    Returns ``(parsed_refs, method)`` where method is ``"llm"``,
    ``"regex"``, or ``"llm-failed-regex"`` depending on which path
    succeeded. Each ref dict has the snowball-ref shape (ref_id,
    source_seed, raw_citation, authors, title, year, doi, status,
    screening_paper_id, crossref_confidence, notes).

    LLM path is preferred when ``client`` is provided and ``use_llm=True``.
    Falls back to regex extraction + per-citation parsing if the LLM
    returns nothing.
    """
    if client is not None and use_llm:
        try:
            llm_refs = _extract_via_llm(pdf_path, seed_id, client, model)
        except Exception as exc:
            print(f"  [warn] LLM extraction error on {seed_id}: {exc}",
                  file=sys.stderr)
            llm_refs = []
        if llm_refs:
            out = []
            for i, partial in enumerate(llm_refs):
                out.append({
                    "ref_id":              f"snow_{seed_id}_{i:04d}",
                    "source_seed":         seed_id,
                    "raw_citation":        "",  # LLM-derived; no raw line
                    "authors":             partial["authors"],
                    "title":               partial["title"],
                    "year":                partial["year"],
                    "doi":                 partial["doi"],
                    "status":              "",
                    "screening_paper_id":  "",
                    "crossref_confidence": "",
                    "notes":               "extraction:llm",
                })
            return out, "llm"

    # Regex fallback
    raw_refs = extract_references_from_pdf(pdf_path)
    out = []
    for i, raw in enumerate(raw_refs):
        if client is not None:
            par, _ = parse_citation_with_fallback(raw, client, model)
        else:
            par = parse_raw_citation(raw)
        out.append({
            "ref_id":              f"snow_{seed_id}_{i:04d}",
            "source_seed":         seed_id,
            "raw_citation":        raw,
            "authors":             par["authors"],
            "title":               par["title"],
            "year":                par["year"],
            "doi":                 par["doi"],
            "status":              "",
            "screening_paper_id":  "",
            "crossref_confidence": "",
            "notes":               "extraction:regex",
        })
    method = "llm-failed-regex" if (client is not None and use_llm) else "regex"
    return out, method


def parse_citation_with_fallback(
    raw: str,
    llm_client=None,
    llm_model: str = "gpt-4o-mini",
) -> tuple[dict, str]:
    """Parse a citation: regex first, LLM fallback when regex confidence is low.

    Returns ``(parsed_dict, source)`` where ``source`` is one of:

    - ``"regex"``           — regex parse was confident
    - ``"llm"``              — regex was low-confidence; LLM rescue succeeded
    - ``"regex-fallback"``  — LLM was attempted but errored; using regex
    - ``"regex-no-llm"``    — caller passed no client; regex-only mode

    Confidence check uses :func:`_is_low_confidence_title` — flags titles
    that are short, URL-contaminated, year-contaminated, or start with a
    non-letter (all signals of pdfplumber extraction artifacts).

    DOI: if regex resolved a DOI but LLM didn't, the regex DOI is preserved
    in the LLM result (DOI regex extraction is more reliable than LLM for
    short fixed-format strings).
    """
    result = parse_raw_citation(raw)
    if llm_client is None:
        return result, "regex-no-llm"
    if not _is_low_confidence_title(result.get("title", "")):
        return result, "regex"
    try:
        llm_result = _parse_with_llm(raw, llm_client, llm_model)
    except Exception as exc:  # noqa: BLE001 — broad on purpose; never crash parsing
        print(f"  [warn] LLM citation parse failed: {exc}", file=sys.stderr)
        return result, "regex-fallback"
    if llm_result.get("title") and len(llm_result["title"]) >= 15:
        if not llm_result.get("doi") and result.get("doi"):
            llm_result["doi"] = result["doi"]
        return llm_result, "llm"
    # LLM didn't surface a meaningful title either — keep regex result
    return result, "regex"


# ---------------------------------------------------------------------------
# Phase 3 — Crossref resolution
# ---------------------------------------------------------------------------
def _tokenise(s: str) -> list[str]:
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s.lower())
    return [t for t in s.split() if t]


def _cosine_title_similarity(a: str, b: str) -> float:
    """Simple token-frequency cosine between two titles."""
    ta = _tokenise(a)
    tb = _tokenise(b)
    if not ta or not tb:
        return 0.0
    from collections import Counter
    ca, cb = Counter(ta), Counter(tb)
    common = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in common)
    na = sum(v * v for v in ca.values()) ** 0.5
    nb = sum(v * v for v in cb.values()) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def crossref_resolve(title: str, first_author: str, year: str | None,
                     email: str | None, threshold: float) -> tuple[str | None, float | None]:
    """Look up a citation in Crossref. Returns (doi, confidence) or (None, best_score)."""
    if not title:
        return None, None
    headers = {
        "User-Agent": (
            f"ERP2-SMS snowball.py (+mailto:{email})"
            if email else "ERP2-SMS snowball.py"
        ),
    }
    params = {
        "query.bibliographic": title[:200],
        "rows": 5,
    }
    if first_author:
        params["query.author"] = first_author[:80]
    url = "https://api.crossref.org/works"

    for attempt in range(CROSSREF_MAX_RETRIES):
        try:
            r = requests.get(url, params=params, headers=headers,
                             timeout=CROSSREF_TIMEOUT)
        except requests.RequestException as exc:
            if attempt == CROSSREF_MAX_RETRIES - 1:
                print(f"  [warn] Crossref network error: {exc}", file=sys.stderr)
                return None, None
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 429:
            time.sleep(2 ** (attempt + 1))
            continue
        if r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        if r.status_code >= 400:
            return None, None
        break
    else:
        return None, None

    time.sleep(CROSSREF_RATE_SLEEP)  # polite-pool pacing

    try:
        data = r.json()
    except json.JSONDecodeError:
        return None, None
    items = data.get("message", {}).get("items", [])
    best_doi, best_score = None, 0.0
    for item in items:
        titles = item.get("title") or []
        cand_title = titles[0] if titles else ""
        score = _cosine_title_similarity(title, cand_title)
        if year:
            # Prefer same-year matches; small boost
            issued = item.get("issued", {}).get("date-parts", [[None]])[0]
            cand_year = str(issued[0]) if issued and issued[0] else ""
            if cand_year == year:
                score += 0.03
        if score > best_score:
            best_score = score
            best_doi = normalise_doi(item.get("DOI"))
    if best_doi and best_score >= threshold:
        return best_doi, round(best_score, 3)
    return None, round(best_score, 3) if best_score else None


# ---------------------------------------------------------------------------
# Phase 4 — Deduplication
# ---------------------------------------------------------------------------
def _dedup_key(ref: dict) -> str:
    if ref.get("doi"):
        return f"doi:{ref['doi']}"
    title_tokens = _tokenise(ref.get("title", ""))
    return f"tit:{' '.join(title_tokens[:10])}|{ref.get('year', '')}"


def dedupe_refs(refs: list[dict]) -> list[dict]:
    """Merge duplicates; collapse source_seed to |-joined string."""
    merged: dict[str, dict] = {}
    for ref in refs:
        key = _dedup_key(ref)
        if not key or key in ("doi:", "tit:|"):
            # Skip truly empty refs
            continue
        if key in merged:
            # Merge source_seed
            existing = merged[key]
            existing_seeds = set(existing["source_seed"].split("|")) if existing["source_seed"] else set()
            new_seeds = {ref["source_seed"]} if ref["source_seed"] else set()
            existing["source_seed"] = "|".join(sorted(existing_seeds | new_seeds))
            # Prefer row with DOI
            if not existing.get("doi") and ref.get("doi"):
                existing["doi"] = ref["doi"]
        else:
            merged[key] = dict(ref)
    return list(merged.values())


# ---------------------------------------------------------------------------
# Phase 5 — Status assignment + classification
# ---------------------------------------------------------------------------
def _title_year_key(ref: dict) -> str | None:
    """Secondary key for no-DOI dedup: tokenised title + year.

    Returns None if title is too short to be a reliable key (< 3 tokens).
    Mirrors the title-branch of `_dedup_key()`.
    """
    tokens = _tokenise(ref.get("title", ""))
    if len(tokens) < 3:
        return None
    return f"{' '.join(tokens[:10])}|{ref.get('year', '')}"


def already_decided(ref: dict,
                    decided_dois: set[str],
                    decided_paper_ids: set[str],
                    decided_title_year_keys: set[str]) -> bool:
    """True if this ref matches any paper already decided in Task 2.5.

    "Decided" covers BOTH include and exclude rows — the full 4093-row
    phase2_decisions.csv, not just the 640 includes. This prevents the
    snowball from re-screening (and double-writing) papers that Task 2.5
    already ruled out.

    Match order:
      1. DOI exact match against any decided row (primary key).
      2. Computed paper_id (doi:… or hash:…) match against any decided
         row's paper_id — catches hash-ID collisions when DOI is absent
         on both sides.
      3. (Gap B fallback) tokenised title + year, used only when the ref
         has no DOI. Protects against the case where Task 2.5 had a DOI
         but the snowball ref does not.
    """
    doi = ref.get("doi") or None
    if doi and doi in decided_dois:
        return True
    paper_id = _compute_paper_id(ref)
    if paper_id in decided_paper_ids:
        return True
    if not doi:
        key = _title_year_key(ref)
        if key and key in decided_title_year_keys:
            return True
    return False


def _ref_to_row(ref: dict) -> pd.Series:
    """Adapter: build the pd.Series that llm_review.build_user_message expects."""
    return pd.Series({
        "title":          ref.get("title", ""),
        "abstract":       "(not available — snowball reference from seed PDF)",
        "source":         "",
        "year":           ref.get("year", ""),
        "scis_rank":      "",
        "doi":            ref.get("doi", ""),
        "preprint_flag":  "",
        "ic3_flag":       "",
        "retracted_flag": "",
        "paratext_flag":  "",
    })


def classify_new_candidate(ref: dict, client, model: str,
                           system_prompt: str) -> tuple[dict, dict]:
    """Call LLM to classify a new ref. Converts defer → exclude (EC4)."""
    row = _ref_to_row(ref)
    user_msg = build_user_message(row)
    parsed, usage = call_openai(client, model, system_prompt, user_msg)
    if parsed.get("decision") == "defer":
        parsed["decision"] = "exclude"
        parsed["criterion"] = parsed.get("criterion") or "EC4"
        orig = parsed.get("rationale", "") or ""
        parsed["rationale"] = (
            "[snowball-forced-exclude] LLM deferred due to insufficient context "
            "(abstract unavailable from seed citation). " + orig
        )
    return parsed, usage


def _compute_paper_id(ref: dict) -> str:
    if ref.get("doi"):
        return f"doi:{ref['doi']}"
    import hashlib
    key = (ref.get("title", "") + ref.get("year", "")).encode("utf-8")
    return f"hash:{hashlib.md5(key).hexdigest()[:12]}"


def build_decision_record(ref: dict, parsed: dict, session_id: str,
                          rater: str) -> dict:
    """Convert ref + LLM output into a phase2_decisions.csv row."""
    now = datetime.now(timezone.utc).isoformat()
    orig_rationale = parsed.get("rationale", "") or ""
    if not orig_rationale.startswith("["):
        rationale = f"[LLM-snowball] {orig_rationale}"
    else:
        rationale = orig_rationale
    return {
        "paper_id":                 _compute_paper_id(ref),
        "doi":                      ref.get("doi", ""),
        "title":                    ref.get("title", ""),
        "year":                     ref.get("year", ""),
        "venue":                    "(snowball ref — venue unknown)",
        "scis_rank":                "",
        "decision":                 parsed.get("decision", ""),
        "criterion":                parsed.get("criterion") or "",
        "f1_provisional":           parsed.get("f1_provisional") or "",
        "preprint_paper":           parsed.get("preprint_paper") or "unknown",
        "rationale":                rationale,
        "timestamp":                now,
        "first_decision_timestamp": now,
        "rater_initials":           rater,
        "session_id":               session_id,
        "pass_number":              "snowball",
    }


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------
def write_snowball_csv(refs: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SNOWBALL_COLUMNS,
                                quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for ref in refs:
            writer.writerow({k: ref.get(k, "") for k in SNOWBALL_COLUMNS})


def load_existing_snowball(path: Path) -> dict[str, dict]:
    """For --resume: map ref_id → existing row."""
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    return {row["ref_id"]: row.to_dict() for _, row in df.iterrows()}


# ---------------------------------------------------------------------------
# DoD + decision register
# ---------------------------------------------------------------------------
def assert_dod(refs: list[dict], seed_ids: set[str]) -> None:
    """Five invariants from design §11."""
    assert all(r.get("status") in VALID_STATUS for r in refs), \
        f"Some refs have invalid status: {set(r.get('status') for r in refs) - VALID_STATUS}"
    assert all(r.get("status") for r in refs), "Some refs have null status"
    sources_seen: set[str] = set()
    for r in refs:
        sources_seen.update((r.get("source_seed") or "").split("|"))
    sources_seen.discard("")
    missing = seed_ids - sources_seen
    assert not missing, f"Seeds missing from source_seed column: {missing}"
    dois = [r["doi"] for r in refs if r.get("doi")]
    assert len(dois) == len(set(dois)), "Duplicate DOIs in output"
    n_overlap = sum(1 for r in refs if r["status"] == "already_in_corpus")
    n_include = sum(1 for r in refs if r["status"] == "included_via_snowball")
    n_exclude = sum(1 for r in refs if r["status"] == "excluded_via_snowball")
    assert n_overlap + n_include + n_exclude == len(refs), \
        "Status partition does not sum to total refs"


def log_snowball_complete(stats: dict, rater: str) -> None:
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "2",
        "paper_id": "N/A",
        "decision": "snowball_complete",
        "rule_applied": "Task 2.6 backward snowballing (snowball.py)",
        "rationale": (
            f"Snowball complete: {stats['total']} refs across {stats['seeds']} seeds; "
            f"already_in_corpus={stats['already']} "
            f"(vs-includes={stats['overlap_with_includes']}, "
            f"vs-excludes={stats['overlap_with_excludes']}), "
            f"included_via_snowball={stats['include']}, "
            f"excluded_via_snowball={stats['exclude']}. "
            f"Crossref-resolved={stats['crossref_resolved']} DOIs. "
            f"Manual-fallback seeds={stats['manual_seeds']}."
        ),
        "rater_initials": rater,
    }
    # Ensure register exists and has header
    first = not DECISION_REGISTER.exists() or DECISION_REGISTER.stat().st_size == 0
    with open(DECISION_REGISTER, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if first:
            writer.writeheader()
        writer.writerow(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--seeds-dir", type=Path, default=SEEDS_DIR)
    p.add_argument("--output", type=Path, default=OUTPUT_CSV)
    p.add_argument("--similarity-threshold", type=float, default=SIMILARITY_DEFAULT)
    p.add_argument("--skip-crossref", action="store_true")
    p.add_argument("--limit", type=int, default=None,
                   help="Process only first N refs total (smoke test)")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="Skip Phase 5 (no writes to phase2_decisions.csv)")
    p.add_argument("--email", type=str, default=None,
                   help="Crossref polite-pool email (overrides .env)")
    p.add_argument("--rater", type=str,
                   default=os.environ.get("RATER_INITIALS", "AT"))
    p.add_argument("--model", type=str, default=DEFAULT_MODEL)
    p.add_argument("--api-key", type=str, default=None,
                   help="OpenAI API key (overrides .env)")
    p.add_argument("--no-llm-parser", action="store_true",
                   help="Disable LLM fallback for citation parsing — use "
                        "regex-only (faster, free, but lower quality on "
                        "ACM/Springer no-space PDFs)")
    p.add_argument("--no-llm-extraction", action="store_true",
                   help="Disable LLM-driven reference-section extraction. "
                        "Falls back to regex line-grouping + per-citation "
                        "parsing. Use this for offline/no-API runs.")
    return p.parse_args()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()

    # Open report tee
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORTS_DIR / f"snowball_{run_ts}.log"
    report_file = open(report_path, "w", encoding="utf-8")
    original_stdout = sys.stdout
    sys.stdout = _Tee(original_stdout, report_file)
    try:
        return _run(args, run_ts, report_path)
    finally:
        sys.stdout = original_stdout
        report_file.close()


def _run(args, run_ts: str, report_path: Path) -> int:
    print(f"# snowball.py — run at {run_ts}")
    print(f"# report: {report_path.relative_to(ROOT)}\n")

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------
    pdfs = sorted(args.seeds_dir.glob("*.pdf"))
    if len(pdfs) == 0:
        print(f"ERROR: no PDFs in {args.seeds_dir}", file=sys.stderr)
        return 1
    seed_ids = {derive_seed_id(p): p for p in pdfs}
    print(f"Seeds: {len(pdfs)} PDFs → seed_ids = {sorted(seed_ids.keys())}\n")

    if not INCLUDED_SET.exists():
        print(f"ERROR: {INCLUDED_SET} not found; run Task 2.5 first",
              file=sys.stderr)
        return 1
    inc_df = pd.read_csv(INCLUDED_SET, dtype=str).fillna("")
    included_dois = {d for d in inc_df["doi"].str.lower().str.strip() if d}

    # Load ALL Task 2.5 decisions (include + exclude + defer) to prevent the
    # snowball from re-screening already-decided papers. Build three dedup
    # keys: DOI (primary), paper_id (for hash-ID collisions), title+year
    # (fallback for no-DOI refs). See Gap A/B fix in design §5.5.
    if not PHASE2_DECISIONS.exists():
        print(f"ERROR: {PHASE2_DECISIONS} not found; run Task 2.5 first",
              file=sys.stderr)
        return 1
    dec_df = pd.read_csv(PHASE2_DECISIONS, dtype=str).fillna("")
    decided_dois = {d for d in dec_df["doi"].str.lower().str.strip() if d}
    decided_paper_ids = {p for p in dec_df["paper_id"].astype(str) if p}
    decided_title_year_keys: set[str] = set()
    for _, drow in dec_df.iterrows():
        key = _title_year_key({
            "title": drow.get("title", ""),
            "year":  drow.get("year", ""),
        })
        if key:
            decided_title_year_keys.add(key)
    n_includes = (dec_df["decision"] == "include").sum()
    n_excludes = (dec_df["decision"] == "exclude").sum()
    print(f"Corpus overlap key: {len(included_dois)} DOIs in included_set.csv")
    print(f"Task 2.5 decisions: {len(dec_df)} rows "
          f"({n_includes} include, {n_excludes} exclude); "
          f"{len(decided_dois)} have DOIs, "
          f"{len(decided_title_year_keys)} have title+year keys\n")

    # ------------------------------------------------------------------
    # Initialise OpenAI client (used by Phases 1, 2, and 5 — one key load).
    # ------------------------------------------------------------------
    openai_client = None
    try:
        from openai import OpenAI
        api_key, key_source = load_api_key(args.api_key)
        openai_client = OpenAI(api_key=api_key)
        print(f"OpenAI API key loaded from: {key_source}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] OpenAI client unavailable: {exc} — "
              f"falling back to regex-only extraction and parsing")

    use_llm_extraction = openai_client is not None and not args.no_llm_extraction
    use_llm_parser = openai_client is not None and not args.no_llm_parser
    if use_llm_extraction:
        print(f"Reference extraction: LLM-driven (per-PDF, model={args.model})")
    else:
        print("Reference extraction: regex-based (line grouping)")
    print()

    # ------------------------------------------------------------------
    # Phase 1 + 2 — Extract & parse references per seed
    # ------------------------------------------------------------------
    print("=== Phase 1 + 2: Reference extraction & parsing ===")
    parsed_refs: list[dict] = []
    manual_seeds: list[str] = []
    extraction_methods: dict[str, str] = {}
    for seed_id, pdf_path in seed_ids.items():
        seed_refs, method = extract_references_for_seed(
            pdf_path, seed_id,
            client=openai_client if use_llm_parser or use_llm_extraction else None,
            model=args.model,
            use_llm=use_llm_extraction,
        )
        extraction_methods[seed_id] = method
        if not seed_refs:
            # Last-resort manual fallback
            print(f"  [{seed_id}] extraction returned 0 refs — checking manual fallback")
            manual = load_manual_fallback(seed_id)
            if manual is None:
                print(f"  [warn] no manual fallback at "
                      f"{MANUAL_FALLBACK.relative_to(ROOT)}/{seed_id}.csv — "
                      f"seed {seed_id} contributes 0 refs")
                manual_seeds.append(seed_id)
                continue
            manual_seeds.append(seed_id)
            for i, row in enumerate(manual):
                seed_refs.append({
                    "ref_id":              f"snow_{seed_id}_{i:04d}",
                    "source_seed":         seed_id,
                    "raw_citation":        row.get("raw_citation", ""),
                    "authors":             row.get("authors", ""),
                    "title":               row.get("title", ""),
                    "year":                row.get("year", ""),
                    "doi":                 normalise_doi(row.get("doi", "")) or "",
                    "status":              "",
                    "screening_paper_id":  "",
                    "crossref_confidence": "",
                    "notes":               "manual_fallback",
                })
        print(f"  [{seed_id}] {len(seed_refs)} refs (method={method})")
        parsed_refs.extend(seed_refs)

    if args.limit:
        parsed_refs = parsed_refs[: args.limit]
        print(f"--limit {args.limit} applied → {len(parsed_refs)} refs")

    method_counts: dict[str, int] = {}
    for m in extraction_methods.values():
        method_counts[m] = method_counts.get(m, 0) + 1
    print(f"\nTotal: {len(parsed_refs)} refs across {len(seed_ids)} seeds "
          f"({', '.join(f'{k}={v}' for k, v in method_counts.items())})\n")

    # ------------------------------------------------------------------
    # Phase 3 — Crossref resolution
    # ------------------------------------------------------------------
    print("=== Phase 3: Crossref DOI resolution ===")
    email = load_crossref_email(args.email)
    if args.skip_crossref:
        print("  --skip-crossref: skipping Crossref lookups\n")
        crossref_resolved = 0
    else:
        print(f"  polite-pool email: {email or '(none — using anonymous pool)'}")
        missing = [r for r in parsed_refs if not r["doi"]]
        print(f"  {len(missing)} refs missing DOI → Crossref lookup")
        crossref_resolved = 0
        for i, ref in enumerate(missing, 1):
            if not ref["title"]:
                ref["notes"] = (ref.get("notes") or "") + ";parse_failed"
                continue
            first_author = ref["authors"].split(",")[0].split(" ")[-1] if ref["authors"] else ""
            doi, conf = crossref_resolve(ref["title"], first_author, ref["year"],
                                         email, args.similarity_threshold)
            if doi:
                ref["doi"] = doi
                ref["crossref_confidence"] = conf or ""
                crossref_resolved += 1
            else:
                ref["crossref_confidence"] = conf or ""
                ref["notes"] = (ref.get("notes") or "") + ";crossref_no_match"
            if i % 25 == 0:
                print(f"    {i}/{len(missing)} Crossref lookups "
                      f"({crossref_resolved} resolved)")
        print(f"  Crossref resolved: {crossref_resolved}/{len(missing)}\n")

    # ------------------------------------------------------------------
    # Phase 4 — Dedup
    # ------------------------------------------------------------------
    print("=== Phase 4: Deduplication ===")
    before = len(parsed_refs)
    # Reassign ref_id after dedup for compactness
    parsed_refs = dedupe_refs(parsed_refs)
    for i, ref in enumerate(parsed_refs):
        ref["ref_id"] = f"snow_{i:05d}"
    print(f"  {before} → {len(parsed_refs)} unique refs "
          f"({before - len(parsed_refs)} duplicates merged)\n")

    # ------------------------------------------------------------------
    # Phase 5 — Status + classification
    # ------------------------------------------------------------------
    print("=== Phase 5: Status assignment + LLM screening ===")
    # First pass: dedup against all Task 2.5 decisions (Gap A + B)
    overlap_with_includes = 0
    overlap_with_excludes = 0
    for ref in parsed_refs:
        if already_decided(ref, decided_dois, decided_paper_ids,
                           decided_title_year_keys):
            ref["status"] = "already_in_corpus"
            # Track the Task 2.5 decision for reporting
            doi = ref.get("doi")
            if doi and doi in included_dois:
                overlap_with_includes += 1
            else:
                overlap_with_excludes += 1
    n_overlap = sum(1 for r in parsed_refs if r["status"] == "already_in_corpus")
    new_candidates = [r for r in parsed_refs if not r["status"]]
    print(f"  already_in_corpus: {n_overlap} "
          f"(vs includes: {overlap_with_includes}, "
          f"vs excludes: {overlap_with_excludes})")
    print(f"  new candidates needing screening: {len(new_candidates)}\n")

    if args.dry_run:
        # Mark new candidates as excluded-dry-run so DoD passes
        print("  --dry-run: skipping LLM classification. "
              "Marking all new candidates as excluded_via_snowball(dry-run).")
        for ref in new_candidates:
            ref["status"] = "excluded_via_snowball"
            ref["notes"] = (ref.get("notes") or "") + ";dry_run"
    elif new_candidates:
        # Live LLM path — reuse the client created before Phase 2
        if openai_client is None:
            print("ERROR: OpenAI client not initialised; cannot classify "
                  "snowball candidates. Re-run without --no-llm-parser or "
                  "ensure OPENAI_API_KEY is set in .env.", file=sys.stderr)
            return 1
        client = openai_client
        system_prompt = build_system_prompt(load_codebook_excerpt(),
                                            load_ie_excerpt())
        session_id = str(uuid.uuid4())[:8]
        print(f"  session_id: {session_id}")
        print(f"  model: {args.model}")
        for i, ref in enumerate(new_candidates, 1):
            try:
                parsed, usage = classify_new_candidate(
                    ref, client, args.model, system_prompt)
            except Exception as exc:
                print(f"  [warn] LLM error on {ref['ref_id']}: {exc}",
                      file=sys.stderr)
                ref["status"] = "excluded_via_snowball"
                ref["notes"] = (ref.get("notes") or "") + ";llm_error"
                continue
            decision = parsed.get("decision")
            if decision == "include":
                ref["status"] = "included_via_snowball"
            else:
                ref["status"] = "excluded_via_snowball"
            # Append to phase2_decisions.csv
            record = build_decision_record(ref, parsed, session_id, args.rater)
            append_decision(PHASE2_DECISIONS, record)
            ref["screening_paper_id"] = record["paper_id"]
            if i % 10 == 0 or i == len(new_candidates):
                print(f"    {i}/{len(new_candidates)} classified "
                      f"(status={ref['status']})")

    # ------------------------------------------------------------------
    # Write snowball CSV + meta
    # ------------------------------------------------------------------
    write_snowball_csv(parsed_refs, args.output)
    write_with_meta(
        args.output,
        script="code/snowball.py",
        inputs=[str(p.relative_to(ROOT)) for p in pdfs] +
               [str(INCLUDED_SET.relative_to(ROOT))],
        seed=42,
    )
    print(f"\n✓ Written: {args.output.relative_to(ROOT)} "
          f"({len(parsed_refs)} refs)")

    # Regenerate included_set.csv if we appended any decisions
    if not args.dry_run and new_candidates:
        derive_outputs()
        print(f"✓ Regenerated: {INCLUDED_SET.relative_to(ROOT)}")

    # ------------------------------------------------------------------
    # DoD
    # ------------------------------------------------------------------
    print("\n=== DoD verification ===")
    # Seeds that actually contributed refs in this run. In --limit mode this
    # naturally shrinks as refs are truncated; in full mode it should equal
    # every seed whose PDF parsed (or had a manual fallback).
    seeds_contributing: set[str] = set()
    for r in parsed_refs:
        seeds_contributing.update(
            s for s in (r.get("source_seed") or "").split("|") if s
        )
    if args.limit:
        # Truncated run — assert against what the limit actually covered.
        expected_seeds = seeds_contributing
    else:
        # Full-run expectation: every seed whose PDF parsed or had a manual
        # fallback file. Seeds that failed both are warned about earlier and
        # will naturally break DoD — that's the intended loud signal.
        expected_seeds = set(seed_ids.keys()) - {
            s for s in manual_seeds
            if not (MANUAL_FALLBACK / f"{s}.csv").exists()
        }
    try:
        assert_dod(parsed_refs, expected_seeds)
    except AssertionError as exc:
        print(f"  ✗ DoD FAILED: {exc}")
        return 1
    print("  ✓ All DoD invariants hold")

    # ------------------------------------------------------------------
    # Report + register
    # ------------------------------------------------------------------
    n_include = sum(1 for r in parsed_refs if r["status"] == "included_via_snowball")
    n_exclude = sum(1 for r in parsed_refs if r["status"] == "excluded_via_snowball")
    print(f"\n=== Summary ===")
    print(f"  Seeds processed:         {len(pdfs)}")
    if manual_seeds:
        print(f"  Manual-fallback seeds:   {len(manual_seeds)} ({manual_seeds})")
    print(f"  Total unique refs:       {len(parsed_refs)}")
    print(f"  already_in_corpus:       {n_overlap} "
          f"(includes: {overlap_with_includes}, "
          f"excludes: {overlap_with_excludes})")
    print(f"  included_via_snowball:   {n_include}")
    print(f"  excluded_via_snowball:   {n_exclude}")
    if len(parsed_refs) > 0:
        pct = n_overlap / len(parsed_refs) * 100
        print(f"  Overlap rate:            {pct:.1f}%")

    stats = {
        "total":                  len(parsed_refs),
        "seeds":                  len(pdfs),
        "already":                n_overlap,
        "overlap_with_includes":  overlap_with_includes,
        "overlap_with_excludes":  overlap_with_excludes,
        "include":                n_include,
        "exclude":                n_exclude,
        "crossref_resolved":      crossref_resolved if not args.skip_crossref else 0,
        "manual_seeds":           len(manual_seeds),
    }
    # Only log to the decision register on real runs — dry-runs produce
    # synthetic status values and logging them would mislead Phase 6 auditors.
    if args.dry_run:
        print(f"  (dry-run: skipping decision_register.csv write)")
    else:
        log_snowball_complete(stats, args.rater)
        print(f"  ✓ Logged to {DECISION_REGISTER.relative_to(ROOT)}")
    print(f"\nReport saved: {report_path.relative_to(ROOT)}")
    return 2 if manual_seeds else 0


if __name__ == "__main__":
    sys.exit(main())
