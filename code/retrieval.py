"""Task 3.1 — Obtain full texts for included papers.

Iterates included_set.csv, attempts automated PDF retrieval via Unpaywall,
Semantic Scholar, and arXiv, then tracks status in retrieval_status.csv.
Papers not retrievable within 14 days are excluded under EC6.

Interruption-safe: writes retrieval_status.csv after every paper so that
a killed process loses at most the current download. On re-run, already-
retrieved papers are skipped automatically.

Usage:
    python code/retrieval.py                        # full run
    python code/retrieval.py --dry-run --limit 5    # check first 5 without downloading
    python code/retrieval.py --retry-failed          # re-attempt failed papers
    python code/retrieval.py --check-ec6             # only check EC6 deadline
    python code/retrieval.py --manual <paper_id>     # mark a manual download as retrieved

Consumes:
    artifacts/screening/included_set.csv
    .env: UNPAYWALL_EMAIL (required for Unpaywall API)

Produces:
    artifacts/extraction/fulltext/{safe_paper_id}.pdf
    artifacts/extraction/retrieval_status.csv (+ .meta.json)
    EC6 exclusion rows in decision_register.csv

Design: design/3_1_retrieval.md
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, date
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
INCLUDED_SET    = ROOT / "artifacts" / "screening" / "included_set.csv"
FULLTEXT_DIR    = ROOT / "artifacts" / "extraction" / "fulltext"
STATUS_CSV      = ROOT / "artifacts" / "extraction" / "retrieval_status.csv"
REGISTER        = ROOT / "decision_register.csv"

EC6_DEADLINE_DAYS = 14

STATUS_COLUMNS = [
    "paper_id", "doi", "title", "venue", "scis_rank",
    "safe_filename",
    "status", "source", "pdf_url",
    "attempts", "first_attempt_date", "last_attempt_date",
    "retrieved_at", "file_size_bytes", "notes",
]

# API settings
UNPAYWALL_BASE    = "https://api.unpaywall.org/v2"
SEMSCHOLAR_BASE   = "https://api.semanticscholar.org/graph/v1/paper"
ARXIV_PDF_BASE    = "https://arxiv.org/pdf"
REQUEST_TIMEOUT   = 60
DOWNLOAD_TIMEOUT  = 120
UNPAYWALL_DELAY   = 0.15   # ~7 req/sec (conservative vs 10/sec limit)
SEMSCHOLAR_DELAY  = 1.1    # free tier: 1 req/sec
MAX_RETRIES       = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def safe_paper_id_to_filename(paper_id: str) -> str:
    """Convert paper_id to a filesystem-safe PDF filename.

    'doi:10.1145/3597503.3608128' → 'doi_10.1145_3597503.3608128.pdf'
    """
    safe = paper_id.replace(":", "_").replace("/", "_")
    return f"{safe}.pdf"


def load_unpaywall_email(cli_override: str | None = None) -> str | None:
    """Load UNPAYWALL_EMAIL from CLI → env var → .env file."""
    if cli_override:
        return cli_override
    email = os.environ.get("UNPAYWALL_EMAIL")
    if email:
        return email
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("UNPAYWALL_EMAIL=") and len(line) > len("UNPAYWALL_EMAIL="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                return val if val else None
    return None


def _print_paper_header(idx: int, total: int, paper_id: str, title: str,
                        doi: str) -> None:
    """Print a visible per-paper header for console tracking."""
    pct = idx / total * 100 if total else 0
    print(f"\n{'─' * 70}")
    print(f"  [{idx}/{total}] ({pct:.1f}%)")
    print(f"  paper_id: {paper_id}")
    print(f"  doi:      {doi}")
    print(f"  title:    {title[:80]}")
    print(f"{'─' * 70}")


# ---------------------------------------------------------------------------
# Retrieval tiers
# ---------------------------------------------------------------------------
def try_unpaywall(doi: str, email: str) -> tuple[str | None, str]:
    """Query Unpaywall for an open-access PDF URL.

    Returns (url_or_None, status_note).
    """
    url = f"{UNPAYWALL_BASE}/{doi}?email={email}"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return None, f"unpaywall_network_error: {exc}"
    if r.status_code == 404:
        return None, "unpaywall_not_found"
    if r.status_code != 200:
        return None, f"unpaywall_http_{r.status_code}"
    try:
        data = r.json()
    except (json.JSONDecodeError, ValueError):
        return None, "unpaywall_bad_json"
    # Try best_oa_location first
    oa = data.get("best_oa_location") or {}
    pdf_url = oa.get("url_for_pdf") or oa.get("url")
    if pdf_url:
        return pdf_url, "unpaywall_ok"
    # Try all oa_locations
    for loc in data.get("oa_locations") or []:
        pdf_url = loc.get("url_for_pdf") or loc.get("url")
        if pdf_url:
            return pdf_url, "unpaywall_ok_alt_location"
    return None, "unpaywall_no_oa_location"


def try_semantic_scholar(doi: str) -> tuple[str | None, str]:
    """Query Semantic Scholar for an open-access PDF URL.

    Returns (url_or_None, status_note).
    """
    url = f"{SEMSCHOLAR_BASE}/DOI:{doi}?fields=openAccessPdf"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return None, f"semscholar_network_error: {exc}"
    if r.status_code == 404:
        return None, "semscholar_not_found"
    if r.status_code == 429:
        return None, "semscholar_rate_limited"
    if r.status_code != 200:
        return None, f"semscholar_http_{r.status_code}"
    try:
        data = r.json()
    except (json.JSONDecodeError, ValueError):
        return None, "semscholar_bad_json"
    oa_pdf = data.get("openAccessPdf") or {}
    pdf_url = oa_pdf.get("url")
    if pdf_url:
        return pdf_url, "semscholar_ok"
    return None, "semscholar_no_oa_pdf"


def try_arxiv(doi: str, preprint_paper: str) -> tuple[str | None, str]:
    """Construct an arXiv PDF URL if the paper is a preprint.

    Returns (url_or_None, status_note).
    """
    # Check if DOI itself points to arXiv
    arxiv_match = re.search(r"arxiv[./:](\d{4}\.\d{4,5})", doi, re.IGNORECASE)
    if arxiv_match:
        arxiv_id = arxiv_match.group(1)
        return f"{ARXIV_PDF_BASE}/{arxiv_id}.pdf", "arxiv_from_doi"
    # Check if preprint_paper flag suggests arXiv
    if preprint_paper in ("preprint", "mixed"):
        # Can't construct URL without arXiv ID — would need Crossref/OpenAlex
        return None, "arxiv_no_id_in_doi"
    return None, "arxiv_not_preprint"


ARXIV_API_BASE = "http://export.arxiv.org/api/query"


def try_arxiv_search(title: str, doi: str) -> tuple[str | None, str]:
    """Search arXiv by title to find a preprint version of a published paper.

    Many published papers (ICSE, FSE, TSE, etc.) also have arXiv preprints
    under a different DOI. This tier searches arXiv's API by title and
    returns the PDF URL if a close match is found.

    Returns (url_or_None, status_note).
    """
    if not title or len(title) < 15:
        return None, "arxiv_search_skip_short_title"
    # Clean title for arXiv query — remove special chars
    clean_title = re.sub(r"[^\w\s]", " ", title).strip()
    # Truncate to first ~100 chars for search (arXiv API has query limits)
    query_title = clean_title[:100]
    params = {
        "search_query": f'ti:"{query_title}"',
        "max_results": "3",
        "sortBy": "relevance",
    }
    try:
        r = requests.get(ARXIV_API_BASE, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return None, f"arxiv_search_network_error: {exc}"
    if r.status_code != 200:
        return None, f"arxiv_search_http_{r.status_code}"

    # Parse Atom XML response for arXiv IDs
    # Look for <id>http://arxiv.org/abs/XXXX.XXXXX</id> entries
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return None, "arxiv_search_bad_xml"

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)
    if not entries:
        return None, "arxiv_search_no_results"

    # Check each result for title similarity
    title_lower = title.lower().strip()
    for entry in entries:
        entry_title_el = entry.find("atom:title", ns)
        if entry_title_el is None or not entry_title_el.text:
            continue
        entry_title = " ".join(entry_title_el.text.split()).strip()
        # Simple containment check — the arXiv title should substantially
        # overlap with our title
        entry_lower = entry_title.lower().strip()
        # Check if one is a substring of the other, or high word overlap
        words_ours = set(title_lower.split())
        words_arxiv = set(entry_lower.split())
        if len(words_ours) < 3:
            continue
        common = words_ours & words_arxiv
        overlap = len(common) / max(len(words_ours), len(words_arxiv))
        if overlap < 0.6:
            continue
        # Extract arXiv ID from the entry's <id> element
        id_el = entry.find("atom:id", ns)
        if id_el is None or not id_el.text:
            continue
        # ID format: http://arxiv.org/abs/2312.12345vN
        arxiv_match = re.search(r"(\d{4}\.\d{4,5})", id_el.text)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
            return (f"{ARXIV_PDF_BASE}/{arxiv_id}.pdf",
                    f"arxiv_search_match_overlap={overlap:.2f}_id={arxiv_id}")

    return None, "arxiv_search_no_match"


def _transform_to_pdf_url(url: str, doi: str = "") -> list[str]:
    """Generate candidate direct-PDF URLs from a landing-page URL or DOI.

    Many publisher URLs point to HTML landing pages, not the PDF itself.
    This function returns a list of candidate direct-PDF URLs for known
    publishers, most-specific first. The caller tries them in order.

    Returns a list of URLs (may be empty if no transformation known).
    """
    candidates = []

    # Springer / Nature: https://link.springer.com/article/10.1007/... → .../content/pdf/10.1007/...pdf
    if "springer.com" in url or "nature.com" in url:
        if doi:
            candidates.append(f"https://link.springer.com/content/pdf/{doi}.pdf")

    # Wiley: https://onlinelibrary.wiley.com/doi/10.1002/... → .../doi/pdfdirect/10.1002/...
    if "wiley.com" in url:
        if doi:
            candidates.append(f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}")

    # ACM: https://dl.acm.org/doi/10.1145/... → .../doi/pdf/10.1145/...
    if "acm.org" in url:
        if doi:
            candidates.append(f"https://dl.acm.org/doi/pdf/{doi}")

    # IEEE: doi.org redirect → ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=...
    # (Harder to construct — skip for now; institutional access more reliable)

    # ScienceDirect (Elsevier): /science/article/pii/... → /science/article/pii/.../pdf
    if "sciencedirect.com" in url and "/pii/" in url:
        if not url.endswith("/pdf"):
            candidates.append(url.rstrip("/") + "/pdf")

    # DOI.org redirect — try the DOI directly at known publishers
    if "doi.org" in url and doi:
        candidates.append(f"https://link.springer.com/content/pdf/{doi}.pdf")
        candidates.append(f"https://dl.acm.org/doi/pdf/{doi}")
        candidates.append(f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}")

    return candidates


# Headers that tell publishers we want PDF, not HTML
_PDF_HEADERS = {
    "Accept": "application/pdf,*/*;q=0.1",
    "User-Agent": "ERP2-SMS retrieval.py (academic research)",
}


def download_pdf(url: str, dest: Path, doi: str = "",
                 dry_run: bool = False) -> tuple[bool, str]:
    """Download a PDF from url to dest. Returns (success, note).

    Strategy:
      1. Try the given URL with Accept: application/pdf header.
      2. If that returns HTML (not PDF), try publisher-specific direct-PDF
         URL transformations (Springer, ACM, Wiley, Elsevier).
      3. In dry-run mode, performs a HEAD request only (no download).
    """
    if dry_run:
        try:
            r = requests.head(url, timeout=REQUEST_TIMEOUT,
                              allow_redirects=True, headers=_PDF_HEADERS)
            content_type = r.headers.get("content-type", "")
            content_len = r.headers.get("content-length", "?")
            return True, (f"dry_run_head_ok: status={r.status_code}, "
                          f"type={content_type[:40]}, size={content_len}")
        except requests.RequestException as exc:
            return False, f"dry_run_head_error: {exc}"

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Build URL candidate list: original URL first, then publisher transforms
    urls_to_try = [url] + _transform_to_pdf_url(url, doi)
    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for u in urls_to_try:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    for url_idx, try_url in enumerate(unique_urls):
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(try_url, timeout=DOWNLOAD_TIMEOUT,
                                 stream=True, headers=_PDF_HEADERS,
                                 allow_redirects=True)
                if r.status_code != 200:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
                    break  # try next URL candidate
                # Check content-type before writing — skip HTML responses
                content_type = r.headers.get("content-type", "").lower()
                if "html" in content_type and url_idx < len(unique_urls) - 1:
                    # HTML response and we have more URLs to try — skip
                    break
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                # Quick validation before returning
                if dest.exists() and dest.stat().st_size > 10000:
                    with open(dest, "rb") as f:
                        if f.read(5).startswith(b"%PDF"):
                            return True, f"download_ok_url{url_idx}"
                # Not a valid PDF — delete and try next URL
                dest.unlink(missing_ok=True)
                break  # next URL candidate
            except requests.RequestException as exc:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                break  # next URL candidate

    return False, f"download_failed_all_{len(unique_urls)}_urls"


def validate_pdf(path: Path) -> tuple[bool, str]:
    """Check that a downloaded file is actually a PDF.

    Returns (valid, note).
    """
    if not path.exists():
        return False, "file_not_found"
    size = path.stat().st_size
    if size < 10_000:  # 10KB minimum
        return False, f"too_small_{size}bytes"
    with open(path, "rb") as f:
        header = f.read(5)
    if not header.startswith(b"%PDF"):
        return False, "not_pdf_header"
    return True, f"valid_pdf_{size}bytes"


# ---------------------------------------------------------------------------
# Status tracking (interruption-safe)
# ---------------------------------------------------------------------------
def load_status(path: Path) -> pd.DataFrame:
    """Load existing retrieval_status.csv, or return empty frame."""
    if path.exists() and path.stat().st_size > 0:
        df = pd.read_csv(path, dtype=str).fillna("")
        # Ensure all columns present
        for col in STATUS_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame(columns=STATUS_COLUMNS)


def save_status(df: pd.DataFrame, path: Path) -> None:
    """Write retrieval_status.csv atomically (full overwrite — file is small)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df[STATUS_COLUMNS].to_csv(path, index=False, quoting=csv.QUOTE_ALL)


def reconcile_with_included(included: pd.DataFrame,
                             status: pd.DataFrame) -> pd.DataFrame:
    """Merge included_set with existing status, initialising new rows.

    Returns a status DataFrame with one row per included paper.
    """
    # Ensure paper_id is the key
    existing_ids = set(status["paper_id"].astype(str)) if len(status) else set()
    new_rows = []
    for _, row in included.iterrows():
        pid = str(row["paper_id"])
        if pid not in existing_ids:
            new_rows.append({
                "paper_id":          pid,
                "doi":               row.get("doi", ""),
                "title":             row.get("title", ""),
                "venue":             row.get("venue", ""),
                "scis_rank":         row.get("scis_rank", ""),
                "safe_filename":     safe_paper_id_to_filename(pid),
                "status":            "pending",
                "source":            "",
                "pdf_url":           "",
                "attempts":          "0",
                "first_attempt_date": "",
                "last_attempt_date":  "",
                "retrieved_at":       "",
                "file_size_bytes":    "0",
                "notes":             "",
            })
        else:
            # Backfill venue/scis_rank for existing rows that lack them
            idx = status.index[status["paper_id"] == pid]
            if len(idx) > 0:
                i = idx[0]
                if not status.at[i, "venue"]:
                    status.at[i, "venue"] = row.get("venue", "")
                if not status.at[i, "scis_rank"]:
                    status.at[i, "scis_rank"] = row.get("scis_rank", "")
    if new_rows:
        new_df = pd.DataFrame(new_rows, columns=STATUS_COLUMNS)
        status = pd.concat([status, new_df], ignore_index=True)
    return status


def reconcile_existing_pdfs(status: pd.DataFrame,
                             fulltext_dir: Path) -> pd.DataFrame:
    """Check for PDFs already on disk (pilot or prior runs) and mark retrieved."""
    for i, row in status.iterrows():
        if row["status"] == "retrieved":
            continue
        safe_fn = row["safe_filename"]
        if not safe_fn:
            continue
        pdf_path = fulltext_dir / safe_fn
        if pdf_path.exists():
            valid, note = validate_pdf(pdf_path)
            if valid:
                status.at[i, "status"] = "retrieved"
                status.at[i, "source"] = "existing_on_disk"
                status.at[i, "file_size_bytes"] = str(pdf_path.stat().st_size)
                status.at[i, "retrieved_at"] = datetime.now(timezone.utc).isoformat()
                status.at[i, "notes"] = note
    # Also check pilot PDFs with human-readable names
    if fulltext_dir.exists():
        existing_pdfs = {p.name: p for p in fulltext_dir.glob("*.pdf")}
        for i, row in status.iterrows():
            if row["status"] == "retrieved":
                continue
            title = row.get("title", "")
            doi = row.get("doi", "")
            # Try to match by DOI substring in filename
            for fn, fp in existing_pdfs.items():
                if doi and doi.split("/")[-1] in fn:
                    valid, note = validate_pdf(fp)
                    if valid:
                        status.at[i, "status"] = "retrieved"
                        status.at[i, "source"] = "pilot"
                        status.at[i, "file_size_bytes"] = str(fp.stat().st_size)
                        status.at[i, "retrieved_at"] = datetime.now(timezone.utc).isoformat()
                        status.at[i, "notes"] = f"pilot_pdf={fn}"
                        break
    return status


# ---------------------------------------------------------------------------
# EC6 deadline check
# ---------------------------------------------------------------------------
def check_ec6_deadline(status: pd.DataFrame) -> list[dict]:
    """Find papers past the EC6 deadline. Returns list of exclusion dicts."""
    today = date.today()
    exclusions = []
    for i, row in status.iterrows():
        if row["status"] not in ("failed", "pending"):
            continue
        first_attempt = row.get("first_attempt_date", "")
        if not first_attempt:
            continue
        try:
            first_date = date.fromisoformat(first_attempt[:10])
        except (ValueError, TypeError):
            continue
        days_elapsed = (today - first_date).days
        if days_elapsed >= EC6_DEADLINE_DAYS:
            status.at[i, "status"] = "ec6_excluded"
            exclusions.append({
                "paper_id":   row["paper_id"],
                "doi":        row["doi"],
                "title":      row["title"],
                "attempts":   row["attempts"],
                "days":       days_elapsed,
                "last_error": row.get("notes", ""),
            })
    return exclusions


def log_ec6_exclusions(exclusions: list[dict], rater: str) -> None:
    """Append EC6 exclusion rows to decision_register.csv."""
    for exc in exclusions:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "3",
            "paper_id": exc["paper_id"],
            "decision": "ec6_excluded_not_retrievable",
            "rule_applied": "EC6 — full text not retrievable within 14 days",
            "rationale": (
                f"Paper not retrieved after {exc['attempts']} attempts over "
                f"{exc['days']} days. Last note: {exc['last_error'][:200]}"
            ),
            "rater_initials": rater,
        }
        first = not REGISTER.exists() or REGISTER.stat().st_size == 0
        with open(REGISTER, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if first:
                writer.writeheader()
            writer.writerow(row)


# ---------------------------------------------------------------------------
# Main retrieval logic
# ---------------------------------------------------------------------------
def retrieve_one_paper(row_idx: int, status: pd.DataFrame,
                       fulltext_dir: Path, email: str | None,
                       dry_run: bool = False,
                       skip_unpaywall: bool = False,
                       skip_semscholar: bool = False) -> str:
    """Attempt to retrieve one paper. Updates status DataFrame in-place.

    Returns the final status: 'retrieved', 'failed', or 'dry_run_checked'.
    """
    row = status.iloc[row_idx]
    doi = row["doi"]
    paper_id = row["paper_id"]
    safe_fn = row["safe_filename"]
    preprint = row.get("preprint_paper", "")
    dest = fulltext_dir / safe_fn
    today_str = date.today().isoformat()

    # --- Check on disk FIRST (user may have placed it manually) ---
    if dest.exists():
        valid, note = validate_pdf(dest)
        if valid:
            print(f"  ✓ Already on disk: {safe_fn} ({note})")
            status.at[row_idx, "status"] = "retrieved"
            status.at[row_idx, "source"] = "manual_on_disk"
            status.at[row_idx, "file_size_bytes"] = str(dest.stat().st_size)
            status.at[row_idx, "retrieved_at"] = datetime.now(timezone.utc).isoformat()
            status.at[row_idx, "notes"] = f"found_on_disk; {note}"
            return "retrieved"

    # Update attempt tracking
    attempts = int(row.get("attempts") or 0) + 1
    status.at[row_idx, "attempts"] = str(attempts)
    if not row.get("first_attempt_date"):
        status.at[row_idx, "first_attempt_date"] = today_str
    status.at[row_idx, "last_attempt_date"] = today_str

    notes_parts: list[str] = []

    if not doi:
        status.at[row_idx, "status"] = "failed"
        status.at[row_idx, "notes"] = "no_doi"
        print(f"  ✗ No DOI — cannot auto-retrieve")
        return "failed"

    # --- Tier 1: Unpaywall ---
    if not skip_unpaywall and email:
        print(f"  → Tier 1: Unpaywall...", end=" ", flush=True)
        time.sleep(UNPAYWALL_DELAY)
        pdf_url, note = try_unpaywall(doi, email)
        notes_parts.append(note)
        if pdf_url:
            print(f"found URL")
            print(f"    URL: {pdf_url[:100]}")
            ok, dl_note = download_pdf(pdf_url, dest, doi=doi, dry_run=dry_run)
            notes_parts.append(dl_note)
            if ok:
                if dry_run:
                    print(f"  ✓ [DRY-RUN] PDF available ({dl_note})")
                    status.at[row_idx, "status"] = "dry_run_checked"
                    status.at[row_idx, "source"] = "unpaywall"
                    status.at[row_idx, "pdf_url"] = pdf_url
                    status.at[row_idx, "notes"] = "; ".join(notes_parts)
                    return "dry_run_checked"
                valid, v_note = validate_pdf(dest)
                notes_parts.append(v_note)
                if valid:
                    size = dest.stat().st_size
                    print(f"  ✓ Retrieved via Unpaywall ({size:,} bytes)")
                    status.at[row_idx, "status"] = "retrieved"
                    status.at[row_idx, "source"] = "unpaywall"
                    status.at[row_idx, "pdf_url"] = pdf_url
                    status.at[row_idx, "retrieved_at"] = datetime.now(timezone.utc).isoformat()
                    status.at[row_idx, "file_size_bytes"] = str(size)
                    status.at[row_idx, "notes"] = "; ".join(notes_parts)
                    return "retrieved"
                else:
                    print(f"  ✗ Unpaywall PDF invalid: {v_note}")
                    dest.unlink(missing_ok=True)
            else:
                print(f"  ✗ Unpaywall download failed: {dl_note}")
        else:
            print(f"no OA ({note})")
    elif not email:
        notes_parts.append("unpaywall_skipped_no_email")
        print(f"  → Tier 1: Unpaywall — SKIPPED (no UNPAYWALL_EMAIL)")

    # --- Tier 2: Semantic Scholar ---
    if not skip_semscholar:
        print(f"  → Tier 2: Semantic Scholar...", end=" ", flush=True)
        time.sleep(SEMSCHOLAR_DELAY)
        pdf_url, note = try_semantic_scholar(doi)
        notes_parts.append(note)
        if pdf_url:
            print(f"found URL")
            print(f"    URL: {pdf_url[:100]}")
            ok, dl_note = download_pdf(pdf_url, dest, doi=doi, dry_run=dry_run)
            notes_parts.append(dl_note)
            if ok:
                if dry_run:
                    print(f"  ✓ [DRY-RUN] PDF available ({dl_note})")
                    status.at[row_idx, "status"] = "dry_run_checked"
                    status.at[row_idx, "source"] = "semantic_scholar"
                    status.at[row_idx, "pdf_url"] = pdf_url
                    status.at[row_idx, "notes"] = "; ".join(notes_parts)
                    return "dry_run_checked"
                valid, v_note = validate_pdf(dest)
                notes_parts.append(v_note)
                if valid:
                    size = dest.stat().st_size
                    print(f"  ✓ Retrieved via Semantic Scholar ({size:,} bytes)")
                    status.at[row_idx, "status"] = "retrieved"
                    status.at[row_idx, "source"] = "semantic_scholar"
                    status.at[row_idx, "pdf_url"] = pdf_url
                    status.at[row_idx, "retrieved_at"] = datetime.now(timezone.utc).isoformat()
                    status.at[row_idx, "file_size_bytes"] = str(size)
                    status.at[row_idx, "notes"] = "; ".join(notes_parts)
                    return "retrieved"
                else:
                    print(f"  ✗ Semantic Scholar PDF invalid: {v_note}")
                    dest.unlink(missing_ok=True)
            else:
                print(f"  ✗ Semantic Scholar download failed: {dl_note}")
        else:
            print(f"no OA ({note})")

    # --- Tier 3: arXiv ---
    print(f"  → Tier 3: arXiv...", end=" ", flush=True)
    pdf_url, note = try_arxiv(doi, preprint)
    notes_parts.append(note)
    if pdf_url:
        print(f"found URL")
        print(f"    URL: {pdf_url[:100]}")
        ok, dl_note = download_pdf(pdf_url, dest, doi=doi, dry_run=dry_run)
        notes_parts.append(dl_note)
        if ok:
            if dry_run:
                print(f"  ✓ [DRY-RUN] PDF available ({dl_note})")
                status.at[row_idx, "status"] = "dry_run_checked"
                status.at[row_idx, "source"] = "arxiv"
                status.at[row_idx, "pdf_url"] = pdf_url
                status.at[row_idx, "notes"] = "; ".join(notes_parts)
                return "dry_run_checked"
            valid, v_note = validate_pdf(dest)
            notes_parts.append(v_note)
            if valid:
                size = dest.stat().st_size
                print(f"  ✓ Retrieved via arXiv ({size:,} bytes)")
                status.at[row_idx, "status"] = "retrieved"
                status.at[row_idx, "source"] = "arxiv"
                status.at[row_idx, "pdf_url"] = pdf_url
                status.at[row_idx, "retrieved_at"] = datetime.now(timezone.utc).isoformat()
                status.at[row_idx, "file_size_bytes"] = str(size)
                status.at[row_idx, "notes"] = "; ".join(notes_parts)
                return "retrieved"
            else:
                print(f"  ✗ arXiv PDF invalid: {v_note}")
                dest.unlink(missing_ok=True)
        else:
            print(f"  ✗ arXiv download failed: {dl_note}")
    else:
        print(f"skip ({note})")

    # --- Tier 4: arXiv title search (last resort — many published papers
    #     have arXiv preprints under a different DOI) ---
    title = row.get("title", "")
    if title:
        print(f"  → Tier 4: arXiv title search...", end=" ", flush=True)
        time.sleep(0.5)  # arXiv API rate: ~1 req/sec
        pdf_url, note = try_arxiv_search(title, doi)
        notes_parts.append(note)
        if pdf_url:
            print(f"found match!")
            print(f"    URL: {pdf_url[:100]}")
            ok, dl_note = download_pdf(pdf_url, dest, doi=doi, dry_run=dry_run)
            notes_parts.append(dl_note)
            if ok:
                if dry_run:
                    print(f"  ✓ [DRY-RUN] PDF available ({dl_note})")
                    status.at[row_idx, "status"] = "dry_run_checked"
                    status.at[row_idx, "source"] = "arxiv_search"
                    status.at[row_idx, "pdf_url"] = pdf_url
                    status.at[row_idx, "notes"] = "; ".join(notes_parts)
                    return "dry_run_checked"
                valid, v_note = validate_pdf(dest)
                notes_parts.append(v_note)
                if valid:
                    size = dest.stat().st_size
                    print(f"  ✓ Retrieved via arXiv search ({size:,} bytes)")
                    status.at[row_idx, "status"] = "retrieved"
                    status.at[row_idx, "source"] = "arxiv_search"
                    status.at[row_idx, "pdf_url"] = pdf_url
                    status.at[row_idx, "retrieved_at"] = datetime.now(timezone.utc).isoformat()
                    status.at[row_idx, "file_size_bytes"] = str(size)
                    status.at[row_idx, "notes"] = "; ".join(notes_parts)
                    return "retrieved"
                else:
                    print(f"  ✗ arXiv search PDF invalid: {v_note}")
                    dest.unlink(missing_ok=True)
            else:
                print(f"  ✗ arXiv search download failed: {dl_note}")
        else:
            print(f"no match ({note})")

    # --- All tiers failed ---
    print(f"  ✗ All tiers failed — status=failed (attempt #{attempts})")
    status.at[row_idx, "status"] = "failed"
    status.at[row_idx, "notes"] = "; ".join(notes_parts)
    return "failed"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task 3.1 — Retrieve full-text PDFs for included papers",
    )
    p.add_argument("--input", type=Path, default=INCLUDED_SET)
    p.add_argument("--output-dir", type=Path, default=FULLTEXT_DIR)
    p.add_argument("--status-csv", type=Path, default=STATUS_CSV)
    p.add_argument("--retry-failed", action="store_true",
                   help="Re-attempt papers with status=failed")
    p.add_argument("--check-ec6", action="store_true",
                   help="Only check EC6 deadline; log exclusions")
    p.add_argument("--limit", type=int, default=None,
                   help="Process first N pending papers (smoke test)")
    p.add_argument("--manual", type=str, default=None,
                   help="Mark a specific paper_id as manually retrieved")
    p.add_argument("--email", type=str, default=None,
                   help="Unpaywall email (overrides .env)")
    p.add_argument("--skip-unpaywall", action="store_true")
    p.add_argument("--skip-semantic-scholar", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="Check API availability but don't download PDFs")
    p.add_argument("--rater", type=str,
                   default=os.environ.get("RATER_INITIALS", "AT"))
    return p.parse_args()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("  ERP2-SMS Task 3.1 — Full-Text Retrieval")
    print("=" * 70)
    if args.dry_run:
        print("  *** DRY-RUN MODE — no PDFs will be downloaded ***\n")

    # Load included set
    if not args.input.exists():
        print(f"ERROR: {args.input} not found", file=sys.stderr)
        return 1
    included = pd.read_csv(args.input, dtype=str).fillna("")
    print(f"Included papers: {len(included)}")

    # Load / initialise status
    status = load_status(args.status_csv)
    status = reconcile_with_included(included, status)

    # Reconcile existing PDFs on disk (pilot + prior runs + manual downloads)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pre_reconcile_retrieved = (status["status"] == "retrieved").sum()
    status = reconcile_existing_pdfs(status, args.output_dir)
    post_reconcile_retrieved = (status["status"] == "retrieved").sum()
    newly_found = post_reconcile_retrieved - pre_reconcile_retrieved
    save_status(status, args.status_csv)
    if newly_found > 0:
        print(f"\n✓ Found {newly_found} PDFs already on disk "
              f"(manual downloads / prior runs)")
    pdfs_on_disk = len(list(args.output_dir.glob("*.pdf")))
    print(f"PDFs on disk: {pdfs_on_disk} files in {args.output_dir.relative_to(ROOT)}/")
    print(f"  (Tip: place manually downloaded PDFs here using the "
          f"safe_filename from retrieval_status.csv)")

    # Handle --manual
    if args.manual:
        pid = args.manual
        mask = status["paper_id"] == pid
        if not mask.any():
            print(f"ERROR: paper_id '{pid}' not in status CSV", file=sys.stderr)
            return 1
        idx = mask.idxmax()
        safe_fn = status.at[idx, "safe_filename"]
        pdf_path = args.output_dir / safe_fn
        if not pdf_path.exists():
            print(f"ERROR: PDF not found at {pdf_path}. Place it there first.",
                  file=sys.stderr)
            return 1
        valid, note = validate_pdf(pdf_path)
        if not valid:
            print(f"ERROR: PDF at {pdf_path} is invalid: {note}", file=sys.stderr)
            return 1
        status.at[idx, "status"] = "retrieved"
        status.at[idx, "source"] = "manual"
        status.at[idx, "retrieved_at"] = datetime.now(timezone.utc).isoformat()
        status.at[idx, "file_size_bytes"] = str(pdf_path.stat().st_size)
        status.at[idx, "notes"] = f"manual; {note}"
        save_status(status, args.status_csv)
        print(f"✓ Marked '{pid}' as manually retrieved ({pdf_path.name})")
        return 0

    # Handle --check-ec6
    if args.check_ec6:
        exclusions = check_ec6_deadline(status)
        if exclusions:
            print(f"\n⚠ EC6 deadline reached for {len(exclusions)} papers:")
            for exc in exclusions:
                print(f"  - {exc['paper_id']}: {exc['attempts']} attempts, "
                      f"{exc['days']} days")
            log_ec6_exclusions(exclusions, args.rater)
            save_status(status, args.status_csv)
            print(f"✓ Logged {len(exclusions)} EC6 exclusions to "
                  f"{REGISTER.relative_to(ROOT)}")
        else:
            print("✓ No papers past EC6 deadline")
        return 0

    # Pre-retrieval summary
    retrieved = (status["status"] == "retrieved").sum()
    failed = (status["status"] == "failed").sum()
    pending = (status["status"] == "pending").sum()
    ec6 = (status["status"] == "ec6_excluded").sum()
    dry_checked = (status["status"] == "dry_run_checked").sum()
    print(f"\nStatus before retrieval:")
    print(f"  retrieved:       {retrieved}")
    print(f"  failed:          {failed}")
    print(f"  pending:         {pending}")
    print(f"  ec6_excluded:    {ec6}")
    if dry_checked:
        print(f"  dry_run_checked: {dry_checked}")

    # Load email for Unpaywall
    email = load_unpaywall_email(args.email)
    if email:
        print(f"\nUnpaywall email: {email}")
    else:
        print(f"\n⚠ No UNPAYWALL_EMAIL — Tier 1 (Unpaywall) will be skipped")
        print(f"  Set UNPAYWALL_EMAIL in .env or pass --email <your@email>")

    # Determine which papers to process
    if args.retry_failed:
        # Re-attempt failed papers
        queue_mask = status["status"].isin(["failed", "pending"])
        # Reset dry_run_checked too if re-running
        queue_mask = queue_mask | (status["status"] == "dry_run_checked")
    else:
        queue_mask = status["status"].isin(["pending", "dry_run_checked"])

    queue_indices = status.index[queue_mask].tolist()
    if args.limit:
        queue_indices = queue_indices[:args.limit]

    total_queue = len(queue_indices)
    print(f"\nPapers to process: {total_queue}"
          f"{f' (--limit {args.limit})' if args.limit else ''}")
    if total_queue == 0:
        print("Nothing to do.")
        _print_final_summary(status, args.dry_run)
        return 0

    # --- Main retrieval loop ---
    counts = {"retrieved": 0, "failed": 0, "dry_run_checked": 0}
    for seq, row_idx in enumerate(queue_indices, 1):
        row = status.iloc[row_idx]
        _print_paper_header(seq, total_queue, row["paper_id"],
                            row["title"], row["doi"])
        result = retrieve_one_paper(
            row_idx, status, args.output_dir, email,
            dry_run=args.dry_run,
            skip_unpaywall=args.skip_unpaywall,
            skip_semscholar=args.skip_semantic_scholar,
        )
        counts[result] = counts.get(result, 0) + 1

        # Interruption-safe: save after every paper
        save_status(status, args.status_csv)

        # Progress summary every 25 papers
        if seq % 25 == 0 or seq == total_queue:
            print(f"\n  === Progress: {seq}/{total_queue} "
                  f"(retrieved={counts.get('retrieved', 0)}, "
                  f"failed={counts.get('failed', 0)}) ===")

    # --- Write meta sidecar ---
    write_with_meta(
        args.status_csv,
        script="code/retrieval.py",
        inputs=[str(args.input.relative_to(ROOT))],
        seed=42,
    )

    # --- Final summary ---
    print()
    _print_final_summary(status, args.dry_run)

    # --- Exit code ---
    still_pending = status["status"].isin(["pending", "failed"]).sum()
    if still_pending > 0:
        print(f"\n⚠ {still_pending} papers still pending/failed — "
              f"re-run with --retry-failed or download manually")
        return 2
    return 0


def _print_final_summary(status: pd.DataFrame, dry_run: bool) -> None:
    """Print the final status distribution."""
    print("=" * 70)
    print("  Final status summary")
    print("=" * 70)
    for st, cnt in status["status"].value_counts().items():
        pct = cnt / len(status) * 100
        print(f"  {st:20s} {cnt:5d} ({pct:5.1f}%)")

    if not dry_run:
        # Source distribution for retrieved papers
        retrieved = status[status["status"] == "retrieved"]
        if len(retrieved) > 0:
            print(f"\n  Retrieval sources (for {len(retrieved)} retrieved):")
            for src, cnt in retrieved["source"].value_counts().items():
                print(f"    {src:25s} {cnt:5d}")

    print(f"\n  Total: {len(status)} papers")
    print(f"  Status CSV: {STATUS_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
