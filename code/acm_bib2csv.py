"""Convert ACM Digital Library BibTeX exports to normalised CSV.

Task 2.2: Concatenates multiple .bib files exported from ACM DL
(one per search string S1–S6), deduplicates by DOI, normalises
fields to match the Scopus CSV column schema, and writes a single
timestamped CSV with metadata sidecar.

Usage:
    python code/acm_bib2csv.py
    python code/acm_bib2csv.py --input-dir path/to/bib/files
    python code/acm_bib2csv.py --output path/to/output.csv

Consumes:
    artifacts/search/raw/acm_raw/*.bib

Produces:
    artifacts/search/raw/acm_YYYYMMDD.csv
    artifacts/search/raw/acm_YYYYMMDD.csv.meta.json
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import bibtexparser
import pandas as pd

# ---------------------------------------------------------------------------
# Resolve project root (parent of code/)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent

# Force unbuffered stdout for progress visibility
sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_INPUT_DIR = ROOT / "artifacts" / "search" / "raw" / "acm_raw"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "search" / "raw"

# BibTeX entry type → (source_type, doctype)
# source_type: "j" = journal, "p" = conference proceedings
# doctype: human-readable label matching Scopus conventions
ENTRY_TYPE_MAP = {
    "inproceedings": ("p", "Conference Paper"),
    "article":       ("j", "Article"),
    "inbook":        ("p", "Book Chapter"),
    "proceedings":   ("p", "Proceedings"),
    "incollection":  ("p", "Book Chapter"),
    "phdthesis":     ("j", "Thesis"),
    "mastersthesis": ("j", "Thesis"),
    "misc":          ("p", "Other"),
}

# Output column order — must match scopus_20260413.csv exactly
OUTPUT_COLUMNS = [
    "doi", "title", "abstract", "source", "source_type", "doctype",
    "authkeywords", "pageRange", "scopus_id", "cited_by", "issn",
    "source_id", "open_access", "year", "authors", "affiliation",
    "search_path",
]


# ---------------------------------------------------------------------------
# BibTeX File Discovery
# ---------------------------------------------------------------------------

def discover_bib_files(input_dir: Path) -> list[Path]:
    """Find all .bib files in the input directory.

    Handles both regular and space-containing filenames.
    Returns files sorted by name for reproducibility.
    """
    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    bib_files = sorted(input_dir.glob("*.bib"))

    if not bib_files:
        print(f"ERROR: No .bib files found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    return bib_files


# ---------------------------------------------------------------------------
# BibTeX Parsing
# ---------------------------------------------------------------------------

def parse_bib_file(bib_path: Path) -> list[dict]:
    """Parse a single BibTeX file and return a list of entry dicts.

    Each entry dict contains the raw BibTeX fields plus:
      - 'ENTRYTYPE': the entry type (inproceedings, article, etc.)
      - '_source_file': the filename for provenance tracking

    Handles encoding issues by trying UTF-8 first, then latin-1.
    """
    # Try UTF-8 first, fall back to latin-1
    for encoding in ("utf-8", "latin-1"):
        try:
            text = bib_path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        print(f"  WARNING: Could not read {bib_path.name} with any encoding — skipping")
        return []

    # Configure parser for bibtexparser 1.x
    parser = bibtexparser.bparser.BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False

    try:
        db = bibtexparser.loads(text, parser=parser)
    except Exception as e:
        print(f"  WARNING: Failed to parse {bib_path.name}: {e}")
        return []

    # Tag each entry with source file for provenance
    for entry in db.entries:
        entry["_source_file"] = bib_path.name

    return db.entries


# ---------------------------------------------------------------------------
# Field Normalisation
# ---------------------------------------------------------------------------

def normalise_authors(author_str: str) -> str:
    """Convert BibTeX author format to semicolon-separated format.

    BibTeX: "Flores-Saviaga, Claudia and Hanrahan, Benjamin V. and Clarke, Steven"
    Output: "Flores-Saviaga, Claudia; Hanrahan, Benjamin V.; Clarke, Steven"

    Handles curly braces, trailing whitespace, and single-author entries.
    """
    if not author_str:
        return ""

    # Strip curly braces
    author_str = author_str.replace("{", "").replace("}", "")

    # Split on " and " (BibTeX author separator)
    authors = [a.strip() for a in author_str.split(" and ")]

    # Remove empty entries and join with semicolon
    return "; ".join(a for a in authors if a)


def normalise_keywords(keywords_str: str) -> str:
    """Convert comma-separated keywords to semicolon-separated.

    BibTeX: "generative ai, accessibility, ai coding assistants"
    Output: "generative ai; accessibility; ai coding assistants"
    """
    if not keywords_str:
        return ""

    # Strip curly braces
    keywords_str = keywords_str.replace("{", "").replace("}", "")

    # Split on comma, strip whitespace, rejoin with semicolon
    keywords = [k.strip() for k in keywords_str.split(",")]
    return "; ".join(k for k in keywords if k)


def normalise_pages(pages_str: str | None, articleno: str | None = None,
                    numpages: str | None = None) -> str | None:
    """Normalise page range to hyphen-separated format.

    BibTeX uses en-dash (–) or double-dash (--): "45–55" or "45--55"
    Output: "45-55"

    If pages is not available but articleno and numpages are,
    returns "articleno:numpages" as a fallback for page count estimation.
    """
    if pages_str:
        # Replace en-dash and double-dash with single hyphen
        normalised = pages_str.replace("–", "-").replace("--", "-").strip()
        return normalised

    # Fallback: use articleno:numpages if available
    if articleno and numpages:
        return f"art{articleno}:{numpages}pp"

    return None


def normalise_title(title_str: str) -> str:
    """Strip BibTeX curly braces from title.

    BibTeX sometimes wraps titles in braces to preserve capitalisation:
    "{A Large-Scale Survey}" → "A Large-Scale Survey"
    """
    if not title_str:
        return ""
    return title_str.replace("{", "").replace("}", "").strip()


def extract_doi_from_url(url_str: str) -> str | None:
    """Attempt to extract a DOI from a URL field.

    ACM DL URLs often contain the DOI:
    "https://doi.org/10.1145/3706598.3714008" → "10.1145/3706598.3714008"
    "https://doi-org.libproxy.smu.edu.sg/10.1145/..." → "10.1145/..."
    """
    if not url_str:
        return None

    match = re.search(r"(10\.\d{4,}/[^\s,;}{)>\]]+)", url_str)
    if match:
        return match.group(1).rstrip(".")
    return None


# ---------------------------------------------------------------------------
# Entry Normalisation
# ---------------------------------------------------------------------------

def normalise_entry(entry: dict) -> dict | None:
    """Convert a single BibTeX entry dict to the output column schema.

    Returns a dict with keys matching OUTPUT_COLUMNS, or None if the
    entry is missing a title (cannot be identified).
    """
    # Skip entries without a title
    title = normalise_title(entry.get("title", ""))
    if not title:
        print(f"  WARNING: Skipping entry with no title: {entry.get('ID', 'unknown')}")
        return None

    # Determine entry type and map to source_type / doctype
    entry_type = entry.get("ENTRYTYPE", "misc").lower()
    source_type, doctype = ENTRY_TYPE_MAP.get(entry_type, ("p", "Other"))

    # Extract DOI — try doi field first, then parse from url
    doi = entry.get("doi")
    if not doi:
        doi = extract_doi_from_url(entry.get("url", ""))

    # Determine source (venue name)
    # Conference papers → booktitle; journal articles → journal
    if entry_type in ("inproceedings", "inbook", "incollection"):
        source = entry.get("booktitle", "")
    elif entry_type == "article":
        source = entry.get("journal", "")
    else:
        source = entry.get("booktitle", entry.get("journal", ""))
    source = source.replace("{", "").replace("}", "").strip()

    # Parse year as integer
    year_str = entry.get("year", "")
    try:
        year = int(year_str)
    except (ValueError, TypeError):
        year = None

    # Normalise pages
    page_range = normalise_pages(
        entry.get("pages"),
        entry.get("articleno"),
        entry.get("numpages"),
    )

    return {
        "doi":          doi,
        "title":        title,
        "abstract":     entry.get("abstract", "").strip() or None,
        "source":       source or None,
        "source_type":  source_type,
        "doctype":      doctype,
        "authkeywords": normalise_keywords(entry.get("keywords", "")) or None,
        "pageRange":    page_range,
        "scopus_id":    None,       # Not available from ACM DL
        "cited_by":     None,       # Not available from BibTeX
        "issn":         entry.get("issn"),
        "source_id":    None,       # Not available from ACM DL
        "open_access":  None,       # Not available from BibTeX
        "year":         year,
        "authors":      normalise_authors(entry.get("author", "")),
        "affiliation":  None,       # Not available from BibTeX
        "search_path":  "ACM_DL",
    }


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(entries: list[dict]) -> list[dict]:
    """Remove duplicate entries by DOI (case-insensitive).

    Keeps the first occurrence of each DOI. Entries without DOI are
    all kept (they'll be deduped by title in Task 2.4).
    Returns the deduplicated list and logs the duplicate count.
    """
    seen_dois = set()
    unique = []
    duplicates = 0

    for entry in entries:
        doi = entry.get("doi")
        if doi:
            doi_lower = doi.lower().strip()
            if doi_lower in seen_dois:
                duplicates += 1
                continue
            seen_dois.add(doi_lower)
        unique.append(entry)

    if duplicates > 0:
        print(f"  Removed {duplicates} duplicate entries (by DOI)")

    return unique


# ---------------------------------------------------------------------------
# DataFrame Construction
# ---------------------------------------------------------------------------

def build_dataframe(entries: list[dict]) -> pd.DataFrame:
    """Build a DataFrame from normalised entries with correct column order.

    Ensures the output columns match scopus_20260413.csv exactly.
    """
    df = pd.DataFrame(entries)

    # Ensure all output columns exist (add missing as null)
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Reorder to match Scopus schema exactly
    df = df[OUTPUT_COLUMNS]

    return df


# ---------------------------------------------------------------------------
# CLI Argument Parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert ACM DL BibTeX exports to normalised CSV",
        epilog="Example: python code/acm_bib2csv.py",
    )
    parser.add_argument(
        "--input-dir", type=Path, default=DEFAULT_INPUT_DIR,
        help=f"Directory containing .bib files (default: {DEFAULT_INPUT_DIR.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output CSV path (default: artifacts/search/raw/acm_YYYYMMDD.csv)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point: discover, parse, normalise, deduplicate, write."""
    args = parse_args()

    # Resolve input directory
    input_dir = args.input_dir.resolve()

    # Default output path with today's date
    if args.output:
        output_path = args.output.resolve()
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        output_path = DEFAULT_OUTPUT_DIR / f"acm_{date_str}.csv"

    # ----- Step 1: Discover .bib files -----
    bib_files = discover_bib_files(input_dir)
    print(f"Found {len(bib_files)} .bib files in {input_dir}")

    # ----- Step 2: Parse all BibTeX files -----
    all_entries = []
    for bib_path in bib_files:
        entries = parse_bib_file(bib_path)
        print(f"  {bib_path.name}: {len(entries)} entries")
        all_entries.extend(entries)

    print(f"Total raw entries: {len(all_entries)}")

    if not all_entries:
        print("ERROR: No entries parsed from any .bib file", file=sys.stderr)
        sys.exit(1)

    # ----- Step 3: Normalise entries -----
    normalised = []
    skipped = 0
    for entry in all_entries:
        result = normalise_entry(entry)
        if result:
            normalised.append(result)
        else:
            skipped += 1

    print(f"Normalised: {len(normalised)} entries ({skipped} skipped)")

    # ----- Step 4: Deduplicate by DOI -----
    unique = deduplicate(normalised)
    print(f"After dedup: {len(unique)} unique entries")

    # ----- Step 5: Build DataFrame -----
    df = build_dataframe(unique)

    # ----- Step 6: Write output CSV -----
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import csv
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"\nWritten: {output_path} ({len(df)} rows)")

    # ----- Step 7: Write .meta.json sidecar -----
    # List all input .bib files as inputs for provenance
    input_files = [str(f.relative_to(ROOT)) for f in bib_files]
    write_with_meta(
        target_path=output_path,
        script="code/acm_bib2csv.py",
        inputs=input_files,
        seed=42,
    )
    meta_path = output_path.with_suffix(output_path.suffix + ".meta.json")
    print(f"Written: {meta_path}")

    # ----- Summary -----
    abstract_count = df["abstract"].notna().sum()
    doi_count = df["doi"].notna().sum()
    print(f"\nSummary:")
    print(f"  Rows: {len(df)}")
    print(f"  DOI non-null: {doi_count}/{len(df)}")
    print(f"  Abstract non-null: {abstract_count}/{len(df)}")
    print(f"  Year range: {df['year'].min()} – {df['year'].max()}")
    print(f"  Doctype distribution:")
    for dtype, count in df["doctype"].value_counts().items():
        print(f"    {dtype}: {count}")
    print(f"  Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
