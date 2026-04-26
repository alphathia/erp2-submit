"""Scopus search executor — Path A (API) and Path B (CSV import).

Task 2.1: Execute Scopus search against the query template and produce
a timestamped raw CSV with metadata sidecar.

Supports two access paths per research_plan_sms.md §3:
  Path A: Elsevier Scopus Search API (paginated, rate-limited)
  Path B: Web UI CSV import (normalises column names to match API output)

Usage:
    python code/scopus_search.py --path A
    python code/scopus_search.py --path A --query artifacts/protocol/scopus_query_template.txt
    python code/scopus_search.py --path B --input /path/to/exported_scopus.csv

Consumes:
    artifacts/protocol/scopus_query_template.txt (Path A)
    .env  ELSEVIER_API_KEY (Path A)
    User-exported Scopus CSV (Path B)

Produces:
    artifacts/search/raw/scopus_YYYYMMDD.csv
    artifacts/search/raw/scopus_YYYYMMDD.csv.meta.json
    Appends one row to decision_register.csv
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Force unbuffered stdout so progress lines appear immediately
# (critical when running in background or piped)
sys.stdout.reconfigure(line_buffering=True)

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Resolve project root (parent of code/)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent

# Add project root to path so we can import code.utils
sys.path.insert(0, str(ROOT))
from code.utils import git_sha, write_with_meta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Scopus API endpoints
SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
SCOPUS_ABSTRACT_URL = "https://api.elsevier.com/content/abstract/scopus_id"

# Default paths
DEFAULT_QUERY_PATH = ROOT / "artifacts" / "protocol" / "scopus_query_template.txt"
OUTPUT_DIR = ROOT / "artifacts" / "search" / "raw"

# API pagination and rate-limiting
# Standard Scopus API keys allow max 25 results/page.
# Institutional/premium keys may allow up to 200.
MAX_PER_PAGE = 25
REQUEST_DELAY = 0.5         # Seconds between API calls (polite delay)
REQUEST_TIMEOUT = 30        # Seconds before a single request times out
MAX_RETRIES = 3             # Max retry attempts for transient errors
BACKOFF_BASE = 2            # Exponential backoff multiplier

# DoD-required output columns (Task 2.1)
REQUIRED_COLUMNS = [
    "doi", "title", "abstract", "year", "source",
    "doctype", "authkeywords", "pageRange",
]

# ---------------------------------------------------------------------------
# Scopus API field → output column mapping
#
# The Scopus Search API returns fields with namespace prefixes (dc:, prism:).
# We map them to clean, consistent column names for downstream consumers
# (Task 2.3 openalex_enrich.py, Task 2.4 dedup.py / page_filter.py).
# ---------------------------------------------------------------------------
API_FIELD_MAP = {
    "prism:doi":              "doi",
    "dc:title":               "title",
    "dc:description":         "abstract",
    "prism:coverDate":        "cover_date",    # ISO date → extract year
    "prism:publicationName":  "source",
    "prism:aggregationType":  "source_type",   # "Journal" or "Conference Proceeding"
    "subtypeDescription":     "doctype",       # "Article", "Conference Paper", etc.
    "authkeywords":           "authkeywords",
    "prism:pageRange":        "pageRange",
    "dc:identifier":          "scopus_id",     # Scopus EID
    "citedby-count":          "cited_by",
    "prism:issn":             "issn",
    "source-id":              "source_id",
    "openaccess":             "open_access",
}

# Comma-separated field list for the API request
API_FIELD_LIST = ",".join(API_FIELD_MAP.keys())

# ---------------------------------------------------------------------------
# Scopus web UI export → output column mapping (case-insensitive)
#
# The Scopus web UI CSV uses different column headers than the API.
# This map normalises them to the same output schema.
# ---------------------------------------------------------------------------
WEB_EXPORT_MAP = {
    "title":            "title",
    "authors":          "authors",
    "year":             "year",
    "source title":     "source",
    "doi":              "doi",
    "abstract":         "abstract",
    "document type":    "doctype",
    "author keywords":  "authkeywords",
    "source type":      "source_type",
    "eid":              "scopus_id",
    "cited by":         "cited_by",
    "issn":             "issn",
    "open access":      "open_access",
    "page start":       "_page_start",   # Intermediate; combined into pageRange
    "page end":         "_page_end",     # Intermediate; combined into pageRange
    "affiliations":     "affiliation",
}


# ---------------------------------------------------------------------------
# API Key Loading
# ---------------------------------------------------------------------------

def load_api_key(cli_override: str | None = None) -> str:
    """Load the Elsevier API key from CLI arg, env var, or .env file.

    Priority: CLI --api-key > ELSEVIER_API_KEY env var > .env file.
    Exits with a helpful message if the key is not found.
    """
    # 1. CLI override
    if cli_override:
        return cli_override

    # 2. Environment variable (may already be set or loaded by dotenv)
    key = os.environ.get("ELSEVIER_API_KEY")
    if key:
        return key

    # 3. Try loading from .env file in project root
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("ELSEVIER_API_KEY=") and len(line) > len("ELSEVIER_API_KEY="):
                return line.split("=", 1)[1].strip()

    # Key not found anywhere
    print("ERROR: ELSEVIER_API_KEY not found.", file=sys.stderr)
    print("Set it in one of:", file=sys.stderr)
    print("  1. CLI: --api-key YOUR_KEY", file=sys.stderr)
    print("  2. Environment: export ELSEVIER_API_KEY=YOUR_KEY", file=sys.stderr)
    print("  3. File: .env (see .env.example)", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Query Loading
# ---------------------------------------------------------------------------

def load_query(query_path: Path) -> str:
    """Read the Scopus query template and flatten it to a single line.

    The template file (scopus_query_template.txt) contains the query with
    indentation and newlines for readability. The API needs a single-line
    string with normalised whitespace.
    """
    if not query_path.exists():
        print(f"ERROR: Query template not found: {query_path}", file=sys.stderr)
        sys.exit(1)

    raw = query_path.read_text(encoding="utf-8")

    # Collapse all whitespace (newlines, tabs, multiple spaces) into single spaces
    flattened = " ".join(raw.split())
    return flattened


# ---------------------------------------------------------------------------
# Path A: Scopus Search API
# ---------------------------------------------------------------------------

def _scopus_api_request(
    query: str,
    api_key: str,
    start: int = 0,
) -> dict:
    """Execute a single Scopus Search API request with retry logic.

    Returns the parsed JSON response dict.
    Handles HTTP 429 (rate limit) with exponential backoff and
    HTTP 5xx (server errors) with fixed-delay retries.
    """
    headers = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json",
    }
    params = {
        "query": query,
        "count": MAX_PER_PAGE,
        "start": start,
        "sort": "coverDate",
        "field": API_FIELD_LIST,
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                SCOPUS_SEARCH_URL,
                headers=headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            # --- Success ---
            if resp.status_code == 200:
                return resp.json()

            # --- Authentication error ---
            if resp.status_code == 401:
                print("ERROR: HTTP 401 — API key invalid or expired.", file=sys.stderr)
                sys.exit(1)

            # --- Rate limited ---
            if resp.status_code == 429:
                wait = BACKOFF_BASE ** attempt
                print(f"  Rate limited (429). Waiting {wait}s before retry {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(wait)
                continue

            # --- Quota exceeded (often returns 429 but check headers) ---
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining is not None and int(remaining) <= 0:
                print(f"ERROR: Scopus API quota exceeded. Reset: {resp.headers.get('X-RateLimit-Reset')}", file=sys.stderr)
                sys.exit(1)

            # --- Server error ---
            if resp.status_code >= 500:
                print(f"  Server error ({resp.status_code}). Retry {attempt + 1}/{MAX_RETRIES} in 5s...")
                time.sleep(5)
                continue

            # --- Bad request (query too long, count too high, etc.) ---
            if resp.status_code == 400:
                print(f"ERROR: HTTP 400 — Bad request: {resp.text[:300]}", file=sys.stderr)
                print("  Common causes:", file=sys.stderr)
                print(f"  - 'count' parameter too high for your API tier (current: {MAX_PER_PAGE})", file=sys.stderr)
                print("  - Malformed query syntax", file=sys.stderr)
                print("  - Query string exceeds maximum length", file=sys.stderr)
                sys.exit(1)

            # --- Other errors ---
            print(f"ERROR: Unexpected HTTP {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
            sys.exit(1)

        except requests.exceptions.Timeout:
            print(f"  Timeout. Retry {attempt + 1}/{MAX_RETRIES}...")
            time.sleep(BACKOFF_BASE ** attempt)
            continue

        except requests.exceptions.ConnectionError as e:
            print(f"  Connection error: {e}. Retry {attempt + 1}/{MAX_RETRIES}...")
            time.sleep(BACKOFF_BASE ** attempt)
            continue

    # All retries exhausted
    print("ERROR: All retries exhausted for Scopus API request.", file=sys.stderr)
    sys.exit(1)


def _parse_api_entry(entry: dict) -> dict:
    """Parse a single Scopus API search result entry into a flat dict.

    Maps Scopus namespaced fields (dc:title, prism:doi, etc.) to clean
    column names using API_FIELD_MAP. Extracts year from prism:coverDate.
    Handles the 'author' field which is a list of dicts.
    """
    row = {}
    for api_field, col_name in API_FIELD_MAP.items():
        row[col_name] = entry.get(api_field)

    # Extract year from cover_date (ISO format: "2024-04-14")
    cover_date = row.pop("cover_date", None)
    if cover_date:
        try:
            row["year"] = int(cover_date[:4])
        except (ValueError, TypeError):
            row["year"] = None
    else:
        row["year"] = None

    # Parse author list — Scopus returns a list of {"authname": "...", ...}
    author_list = entry.get("author")
    if isinstance(author_list, list):
        row["authors"] = "; ".join(
            a.get("authname", "") for a in author_list
        )
    else:
        row["authors"] = None

    # Parse affiliation — take first affiliation name
    affil_list = entry.get("affiliation")
    if isinstance(affil_list, list) and affil_list:
        row["affiliation"] = affil_list[0].get("affilname", None)
    else:
        row["affiliation"] = None

    return row


def fetch_scopus_api(query: str, api_key: str) -> tuple[pd.DataFrame, int]:
    """Fetch all results from the Scopus Search API with pagination.

    Returns a tuple of (DataFrame, total_results_count).
    Paginates through all results using the opensearch:totalResults field.
    """
    all_rows = []
    start = 0
    total_results = None
    pages_fetched = 0

    print(f"Querying Scopus API (max {MAX_PER_PAGE} results/page)...")

    while True:
        # Polite delay between requests (skip on first request)
        if start > 0:
            time.sleep(REQUEST_DELAY)

        data = _scopus_api_request(query, api_key, start)

        # Parse the search-results envelope
        search_results = data.get("search-results", {})

        # Get total count on first page
        if total_results is None:
            total_results = int(search_results.get("opensearch:totalResults", 0))
            print(f"  Total results: {total_results}")

            if total_results == 0:
                print("  WARNING: Query returned zero results.")
                break

        # Parse entries from this page
        entries = search_results.get("entry", [])

        # Scopus returns {"error": "Result set was empty"} for empty pages
        if not entries or (len(entries) == 1 and "error" in entries[0]):
            break

        for entry in entries:
            all_rows.append(_parse_api_entry(entry))

        pages_fetched += 1
        print(f"  Page {pages_fetched}: fetched {len(entries)} entries (total so far: {len(all_rows)})")

        # Check if we've fetched all results
        start += MAX_PER_PAGE
        if start >= total_results:
            break

    print(f"  Done. {len(all_rows)} entries fetched across {pages_fetched} pages.")

    df = pd.DataFrame(all_rows)
    return df, total_results or 0


# ---------------------------------------------------------------------------
# Abstract Retrieval API
#
# The Scopus Search API often omits abstracts (dc:description) depending on
# the API key tier. This function backfills missing abstracts by calling the
# Scopus Abstract Retrieval API for each record that has a scopus_id.
# ---------------------------------------------------------------------------

def _fetch_single_abstract(scopus_id: str, api_key: str) -> str | None:
    """Fetch the abstract for a single paper via the Abstract Retrieval API.

    Parameters
    ----------
    scopus_id : str
        The Scopus EID (e.g., "SCOPUS_ID:85012345678").
    api_key : str
        Elsevier API key.

    Returns
    -------
    str or None
        The abstract text, or None if not available or on error.
    """
    # Strip the "SCOPUS_ID:" prefix if present to get the numeric part
    eid = scopus_id.replace("SCOPUS_ID:", "").strip()

    url = f"{SCOPUS_ABSTRACT_URL}/{eid}"
    headers = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json",
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

            if resp.status_code == 200:
                data = resp.json()
                # Navigate the nested response to find the abstract
                core_data = (
                    data
                    .get("abstracts-retrieval-response", {})
                    .get("coredata", {})
                )
                abstract = core_data.get("dc:description")
                return abstract if abstract else None

            if resp.status_code == 404:
                # Paper not found — no abstract available
                return None

            if resp.status_code == 429:
                wait = BACKOFF_BASE ** attempt
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                time.sleep(5)
                continue

            # Other errors — skip this paper
            return None

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            time.sleep(BACKOFF_BASE ** attempt)
            continue

    # All retries exhausted
    return None


def enrich_abstracts(df: pd.DataFrame, api_key: str) -> int:
    """Backfill missing abstracts in the DataFrame using the Abstract Retrieval API.

    Iterates rows where 'abstract' is null and 'scopus_id' is available,
    fetches the abstract, and updates the DataFrame in place.

    Parameters
    ----------
    df : pd.DataFrame
        The search results DataFrame (modified in place).
    api_key : str
        Elsevier API key.

    Returns
    -------
    int
        Number of abstracts successfully retrieved.
    """
    # Identify rows needing abstract enrichment
    needs_abstract = df["abstract"].isna() & df["scopus_id"].notna()
    total_to_fetch = needs_abstract.sum()

    if total_to_fetch == 0:
        print("  All abstracts already populated — skipping enrichment.")
        return 0

    print(f"Enriching abstracts via Abstract Retrieval API ({total_to_fetch} to fetch)...")

    fetched = 0
    failed = 0

    for idx in df[needs_abstract].index:
        scopus_id = df.at[idx, "scopus_id"]

        # Polite delay between requests
        if fetched + failed > 0:
            time.sleep(REQUEST_DELAY)

        abstract = _fetch_single_abstract(scopus_id, api_key)

        if abstract:
            df.at[idx, "abstract"] = abstract
            fetched += 1
        else:
            failed += 1

        # Progress report every 100 papers
        done = fetched + failed
        if done % 100 == 0 or done == total_to_fetch:
            print(f"  Progress: {done}/{total_to_fetch} "
                  f"(fetched: {fetched}, no abstract: {failed})")

    print(f"  Abstract enrichment complete: {fetched} fetched, {failed} unavailable.")
    return fetched


# ---------------------------------------------------------------------------
# Path B: Web UI CSV Import
# ---------------------------------------------------------------------------

def import_scopus_csv(input_path: Path) -> pd.DataFrame:
    """Import and normalise a Scopus web UI CSV export.

    Reads the CSV, renames columns to match the API output schema using
    case-insensitive matching, and computes pageRange from Page start/end.
    """
    if not input_path.exists():
        print(f"ERROR: Input CSV not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Importing Scopus web export: {input_path}")
    df = pd.read_csv(input_path, dtype=str)
    print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")

    # Build case-insensitive rename map
    rename_map = {}
    lower_to_col = {c.lower().strip(): c for c in df.columns}
    for web_col_lower, norm_col in WEB_EXPORT_MAP.items():
        if web_col_lower in lower_to_col:
            rename_map[lower_to_col[web_col_lower]] = norm_col

    df = df.rename(columns=rename_map)

    # Compute pageRange from _page_start and _page_end if they exist
    if "_page_start" in df.columns and "_page_end" in df.columns:
        df["pageRange"] = df.apply(
            lambda r: f"{r['_page_start']}-{r['_page_end']}"
            if pd.notna(r.get("_page_start")) and pd.notna(r.get("_page_end"))
            else None,
            axis=1,
        )
        df = df.drop(columns=["_page_start", "_page_end"], errors="ignore")

    # Ensure year is numeric if present
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    return df


# ---------------------------------------------------------------------------
# Validation and Output
# ---------------------------------------------------------------------------

def validate_output(df: pd.DataFrame) -> list[str]:
    """Check that all DoD-required columns are present.

    Returns a list of missing column names (empty if valid).
    Does not fail — the caller decides how to handle warnings.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return missing


def write_output(df: pd.DataFrame, search_path: str, output_dir: Path) -> Path:
    """Write the search results CSV with a date-stamped filename.

    Adds a 'search_path' column to record provenance (A or B).
    Returns the path to the written CSV.
    """
    # Add provenance column
    df["search_path"] = search_path

    # Date-stamped filename
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    output_path = output_dir / f"scopus_{date_str}.csv"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"  Written: {output_path} ({len(df)} rows)")

    return output_path


# ---------------------------------------------------------------------------
# Decision Register Logging
# ---------------------------------------------------------------------------

def log_to_decision_register(
    query: str,
    search_path: str,
    row_count: int,
    output_path: Path,
) -> None:
    """Append a scopus_search_executed row to decision_register.csv.

    Per claude.md: every non-trivial judgement goes in the register.
    Search execution with query string and result count is auditable.
    """
    register_path = ROOT / "decision_register.csv"
    timestamp = datetime.now(timezone.utc).isoformat()

    # Truncate query for the rationale field (avoid overly long CSV cells)
    query_preview = query[:200] + "..." if len(query) > 200 else query

    row = {
        "timestamp": timestamp,
        "phase": "2",
        "paper_id": "N/A",
        "decision": "scopus_search_executed",
        "rule_applied": "Petersen 2015 §5",
        "rationale": (
            f"Query: {query_preview}. "
            f"Path: {search_path}. "
            f"Results: {row_count} rows. "
            f"Output: {output_path.relative_to(ROOT)}"
        ),
        "rater_initials": "AT",
    }

    # Append to CSV (create header if file is empty/header-only)
    file_exists = register_path.exists()
    with open(register_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"  Logged to decision_register.csv")


# ---------------------------------------------------------------------------
# Metadata Sidecar
# ---------------------------------------------------------------------------

def write_search_meta(
    output_path: Path,
    query: str,
    search_path: str,
    total_results: int,
    pages_fetched: int | None,
    input_source: str,
) -> None:
    """Write .meta.json with standard fields plus search-specific metadata.

    Extends the standard write_with_meta format with a search_metadata
    block containing path, total results, query string, etc.
    """
    # Write the standard sidecar first
    write_with_meta(
        target_path=output_path,
        script="code/scopus_search.py",
        inputs=[input_source],
        seed=42,
    )

    # Now read it back and add search_metadata
    meta_path = output_path.with_suffix(output_path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["search_metadata"] = {
        "path": search_path,
        "total_results": total_results,
        "query_string": query,
        "api_pages_fetched": pages_fetched,
        "execution_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"  Written: {meta_path}")


# ---------------------------------------------------------------------------
# CLI Argument Parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Execute Scopus search (Path A: API, Path B: CSV import)",
        epilog="Example: python code/scopus_search.py --path A",
    )
    parser.add_argument(
        "--path", required=True, choices=["A", "B"],
        help="Access path: A = Scopus API, B = web UI CSV import",
    )
    parser.add_argument(
        "--query", type=Path, default=DEFAULT_QUERY_PATH,
        help="Path to query template (Path A only, default: scopus_query_template.txt)",
    )
    parser.add_argument(
        "--input", type=Path, default=None, dest="input_csv",
        help="Path to user-exported Scopus CSV (Path B only)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=OUTPUT_DIR,
        help="Output directory (default: artifacts/search/raw/)",
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="Elsevier API key override (default: reads from .env)",
    )
    parser.add_argument(
        "--enrich-abstracts", action="store_true", default=False,
        help="Attempt abstract enrichment via Abstract Retrieval API (requires institutional API key with META_ABS access)",
    )

    args = parser.parse_args()

    # Validate Path B requires --input
    if args.path == "B" and args.input_csv is None:
        parser.error("--input is required for Path B")

    return args


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point: route to Path A or Path B, then validate and write output."""
    args = parse_args()

    query_string = ""     # Will hold the flattened query for logging
    total_results = 0     # Total results reported by API or row count
    pages_fetched = None  # Only applicable to Path A
    input_source = ""     # Input file path for meta.json

    # ----- Path A: Scopus Search API -----
    if args.path == "A":
        api_key = load_api_key(args.api_key)
        # Resolve to absolute path so relative_to(ROOT) works
        query_path = args.query.resolve()
        query_string = load_query(query_path)
        input_source = str(query_path.relative_to(ROOT))

        print(f"Path A: Scopus Search API")
        print(f"  Query template: {query_path}")
        print(f"  Query length: {len(query_string)} chars")

        df, total_results = fetch_scopus_api(query_string, api_key)
        pages_fetched = (total_results + MAX_PER_PAGE - 1) // MAX_PER_PAGE if total_results > 0 else 0

        # ----- Abstract enrichment via Abstract Retrieval API -----
        # NOTE: Disabled by default. The standard Elsevier API key only
        # supports the META view; META_ABS and FULL views return HTTP 401.
        # Abstracts will be backfilled via OpenAlex in Task 2.3 instead.
        # To attempt enrichment (requires institutional API key), pass
        # --enrich-abstracts explicitly.
        if args.enrich_abstracts and len(df) > 0:
            enrich_abstracts(df, api_key)
        else:
            null_count = df["abstract"].isna().sum() if "abstract" in df.columns else len(df)
            if null_count > 0:
                print(f"  Note: {null_count} abstracts are null — will be backfilled via OpenAlex (Task 2.3)")

    # ----- Path B: Web UI CSV Import -----
    elif args.path == "B":
        query_string = f"imported from {args.input_csv}"
        input_source = str(args.input_csv)

        print(f"Path B: Web UI CSV import")
        df = import_scopus_csv(args.input_csv)
        total_results = len(df)

    # ----- Validate required columns -----
    missing = validate_output(df)
    if missing:
        print(f"  WARNING: Missing DoD-required columns: {missing}", file=sys.stderr)
        print(f"  The output CSV will be written but may fail downstream validation.", file=sys.stderr)

    # ----- Handle empty results -----
    if len(df) == 0:
        print("  WARNING: No results. Writing empty CSV with headers.")
        # Create an empty DataFrame with required columns
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)

    # ----- Write output CSV -----
    output_path = write_output(df, args.path, args.output_dir)

    # ----- Write .meta.json sidecar -----
    write_search_meta(
        output_path=output_path,
        query=query_string,
        search_path=args.path,
        total_results=total_results,
        pages_fetched=pages_fetched,
        input_source=input_source,
    )

    # ----- Log to decision register -----
    log_to_decision_register(query_string, args.path, len(df), output_path)

    # ----- Summary -----
    print(f"\nScopus search complete.")
    print(f"  Path: {args.path}")
    print(f"  Rows: {len(df)}")
    print(f"  Output: {output_path}")
    if missing:
        print(f"  ⚠ Missing columns: {missing}")
    else:
        print(f"  ✓ All required columns present")


if __name__ == "__main__":
    main()
