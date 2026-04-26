"""Task 3.2 + 3.3 — LLM-assisted extraction + open coding (combined).

Reads each included paper's PDF (or abstract if PDF unavailable) via
Gemini 3.1 Pro, and in a single LLM call extracts:
  - Extraction matrix row (Region 1 metadata + Region 2 facets)
  - Raw passages (verbatim quotes with passage IDs)
  - Capability annotations (paper_id × capability_id)
  - Open codes (in-vivo + descriptive per passage)

Usage:
    python code/extraction.py --dry-run --limit 3   # review before committing
    python code/extraction.py                        # extract all retrieved papers
    python code/extraction.py --abstract-only        # Mode B for all papers
    python code/extraction.py --verify               # DoD checks

Consumes:
    artifacts/extraction/fulltext/{safe_paper_id}.pdf
    artifacts/screening/included_set.csv
    artifacts/extraction/retrieval_status.csv
    artifacts/protocol/codebook.md, extraction_schema.md, capability_list.csv

Produces:
    artifacts/extraction/extraction_matrix.csv
    artifacts/extraction/raw_passages/{safe_paper_id}.md
    artifacts/extraction/capability_annotations.csv
    artifacts/extraction/open_codes_pass1.csv
    artifacts/extraction/memo.md
    artifacts/extraction/extraction_status.csv

Design: design/3_2_extraction.md
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
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional

import pandas as pd
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta  # noqa: E402
from code.retrieval import safe_paper_id_to_filename  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
INCLUDED_SET      = ROOT / "artifacts" / "screening" / "included_set.csv"
RETRIEVAL_STATUS  = ROOT / "artifacts" / "extraction" / "retrieval_status.csv"
FULLTEXT_DIR      = ROOT / "artifacts" / "extraction" / "fulltext"
EXTRACTION_DIR    = ROOT / "artifacts" / "extraction"
MATRIX_CSV        = EXTRACTION_DIR / "extraction_matrix.csv"
PASSAGES_DIR      = EXTRACTION_DIR / "raw_passages"
CAP_ANNOT_CSV     = EXTRACTION_DIR / "capability_annotations.csv"
OPEN_CODES_CSV    = EXTRACTION_DIR / "open_codes_pass1.csv"
MEMO_MD           = EXTRACTION_DIR / "memo.md"
EXTRACT_STATUS    = EXTRACTION_DIR / "extraction_status.csv"
REGISTER          = ROOT / "decision_register.csv"
POST_FILTERED     = ROOT / "artifacts" / "search" / "post_filtered.csv"
DECISIONS_CSV     = ROOT / "artifacts" / "screening" / "phase2_decisions.csv"

# Protocol files for system prompt
CODEBOOK_PATH     = ROOT / "artifacts" / "protocol" / "codebook.md"
SCHEMA_PATH       = ROOT / "artifacts" / "protocol" / "extraction_schema.md"
CAPABILITY_PATH   = ROOT / "artifacts" / "protocol" / "capability_list.csv"

DEFAULT_MODEL     = "gemini-3.1-pro-preview"
REQUEST_DELAY     = 0.0   # per-worker sleep before API call (0 for concurrent workers; retry loop handles 429s)
DEFAULT_WORKERS   = 10    # ThreadPoolExecutor size for concurrent extraction
MAX_RETRIES       = 3
MAX_PDF_BYTES     = 50 * 1024 * 1024   # 50 MB — Gemini inline limit
MAX_PDF_PAGES     = 1000               # Gemini page limit for PDF input

# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------
VALID_F1 = [
    "Evaluation Research", "Validation Research", "Solution Proposal",
    "Philosophical", "Opinion", "Personal Experience",
]
VALID_F2 = [
    "Survey", "Interview", "Case Study", "Experiment",
    "Field Study", "Mining Study", "Mixed",
]
VALID_F3_POP = [
    "Professional SWE", "Student", "Citizen Developer",
    "OSS Contributor", "Mixed", "N/A",
]
VALID_F3_CTX = ["Industry", "Education", "OSS", "Lab", "N/A"]
VALID_F5_PARADIGM = ["Pro-code", "Low-code", "No-code"]
VALID_CAP_IDS = {
    "CAP_CODEGEN", "CAP_CODECOMP", "CAP_PROGREPAIR", "CAP_TESTING",
    "CAP_DEBUGGING", "CAP_CODEREVIEW", "CAP_REFACTORING", "CAP_DOCGEN",
    "CAP_CODESEARCH", "CAP_CODESUM", "CAP_CODETRANS", "CAP_VULNDET",
    "CAP_REQENG", "CAP_SYSDESIGN", "CAP_CICD", "CAP_COMMITMSG",
    "CAP_PLANNING", "CAP_MULTIAGENT", "CAP_SELFREFLECT",
}


class MatrixRow(BaseModel):
    paper_id: str
    title: str
    authors: str = Field(description="Semicolon-separated author list")
    year: int
    venue: str
    venue_type: Literal["journal", "conference"]
    doi: str
    sample_size: Optional[int] = Field(default=None)
    sample_description: Optional[str] = Field(default=None)
    study_duration: Optional[str] = Field(default=None)
    f1_contribution_type: Literal[
        "Evaluation Research", "Validation Research",
        "Solution Proposal", "Philosophical", "Opinion",
        "Personal Experience"]
    f2_research_methodology: Literal[
        "Survey", "Interview", "Case Study", "Experiment",
        "Field Study", "Mining Study", "Mixed"]
    f3_population: Literal[
        "Professional SWE", "Student", "Citizen Developer",
        "OSS Contributor", "Mixed", "N/A"]
    f3_context: Literal["Industry", "Education", "OSS", "Lab", "N/A"]
    f4_sdlc_activity: str = Field(
        description="Pipe-delimited from: Requirements|Design|Coding|Testing|"
                    "Code Review|Debugging|CI/CD|Documentation|Project Management")
    f5_tool_modality: str = Field(
        description="Pipe-delimited from: Autocomplete|Conversational|"
                    "IDE-Integrated|Autonomous")
    f5_tool_paradigm: Literal["Pro-code", "Low-code", "No-code"]
    f5_tool_name: str = Field(description="Semicolon-separated tool names")


class Passage(BaseModel):
    passage_id: str = Field(description="P001, P002, etc.")
    text: str = Field(description="Verbatim quote from the paper")
    section: str = Field(description="Section where passage appears")
    relevance: Literal[
        "interaction_mode", "capability_claim",
        "usage_pattern", "challenge", "benefit", "other"]


class CapabilityAnnotation(BaseModel):
    capability_id: str
    evidence: str


class OpenCode(BaseModel):
    passage_id: str
    in_vivo_code: str = Field(description="Author's exact phrase")
    descriptive_code: str = Field(description="Analytic label 2-5 words")
    coder_notes: Optional[str] = Field(default=None)


class ExtractionResult(BaseModel):
    extraction_matrix: MatrixRow
    raw_passages: List[Passage]
    capability_annotations: List[CapabilityAnnotation]
    open_codes: List[OpenCode]


# ---------------------------------------------------------------------------
# Matrix CSV columns (Region 1 + 2 + 3 pointers)
# ---------------------------------------------------------------------------
MATRIX_COLUMNS = [
    "paper_id", "title", "authors", "year", "venue", "venue_type", "doi",
    "sample_size", "sample_description", "study_duration",
    "f1_contribution_type", "f2_research_methodology",
    "f3_population", "f3_context",
    "f4_sdlc_activity", "f5_tool_modality", "f5_tool_paradigm", "f5_tool_name",
    "raw_passages_file", "capability_annotations_file",
    "open_codes_tagged", "extraction_source", "extraction_complete", "notes",
]

CAP_ANNOT_COLUMNS = ["paper_id", "capability_id", "evidence"]
OPEN_CODES_COLUMNS = [
    "paper_id", "passage_id", "in_vivo_code", "descriptive_code", "coder_notes",
]
EXTRACT_STATUS_COLUMNS = [
    "paper_id", "title", "authors", "year",
    "venue", "scis_rank", "scis_venue_type",
    "abstract", "status", "extraction_source", "timestamp", "model",
    "input_tokens", "output_tokens", "cost_usd", "notes",
]


# ---------------------------------------------------------------------------
# .env / API key loading
# ---------------------------------------------------------------------------
def load_google_api_key(cli_override: str | None = None) -> str:
    """Load GOOGLE_API_KEY from CLI → env var → .env file."""
    if cli_override:
        return cli_override
    key = os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("GOOGLE_API_KEY=") and len(line) > len("GOOGLE_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                return val
    raise ValueError(
        "GOOGLE_API_KEY not found. Set in .env or pass --api-key."
    )


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------
def build_system_prompt() -> str:
    """Assemble the system prompt from codebook + schema + capabilities."""
    codebook = CODEBOOK_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    cap_df = pd.read_csv(CAPABILITY_PATH, dtype=str).fillna("")
    cap_list = "\n".join(
        f"- {r['capability_id']}: {r['label']}"
        for _, r in cap_df.drop_duplicates("capability_id").iterrows()
    )

    return f"""You are a research assistant for a Systematic Mapping Study (SMS)
titled "How Do People Use AI Agents for Software Engineering?"

Your task: read the attached academic paper and extract structured data
according to the extraction schema and codebook below. Return strict JSON
conforming to the ExtractionResult schema.

=== CODEBOOK (F1-F5 Definitions) ===
{codebook}

=== EXTRACTION SCHEMA ===
{schema}

=== CAPABILITY LIST (19 IDs) ===
{cap_list}

=== EXTRACTION RULES ===
1. F1 must be one of the 6 Wieringa classes. Apply operational thresholds:
   - Evaluation Research: dedicated empirical section + N≥5 human participants + usage findings
   - Validation Research: benchmark evaluation is primary (HumanEval, SWE-bench)
   - Solution Proposal: tool description dominates, user study <5 or absent
2. F4 and F5 modality are pipe-delimited multi-select (e.g. "Coding|Testing|Debugging")
3. Raw passages must be VERBATIM quotes from the paper — do NOT paraphrase
4. Each passage needs passage_id (P001, P002...), verbatim text, section location, and relevance tag
5. For each passage, assign an in-vivo code (author's exact phrase) and a descriptive code (your 2-5 word analytic label)
6. Capability annotations: only annotate capabilities with clear evidence — do not infer
7. If a field cannot be determined, use null for optional fields
8. For paper_id: use the format "doi:10.xxxx/yyyy" (lowercase, no URL prefix)
9. `sample_size` is the count of HUMAN PARTICIPANTS ONLY. Do NOT populate it
   with artifact counts (e.g. number of bug reports, patch reviews, code
   samples, generated outputs, repositories mined, benchmark instances). If
   the study has no human participants (purely dataset/benchmark-based), set
   `sample_size` to null. However, `sample_description` should still
   summarise the study sample — for dataset-only studies, describe the
   artefact sample (e.g., "100 Android apps", "587 patch reviews",
   "36,000 generated code snippets"). Only set `sample_description` to null
   if the paper reports no sample information at all.
10. `f3_population` and `f3_context` describe human study participants and
    their setting. If the paper has no human participants (dataset-only,
    benchmark evaluation, mining study of artifacts with no human subjects),
    set BOTH `f3_population` and `f3_context` to "N/A". Do NOT infer a
    population from the data source (e.g. a paper mining GitHub repos with no
    human subjects is "N/A" / "N/A", NOT "OSS Contributor" / "OSS").
"""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------
def extract_one_paper(
    client,
    model: str,
    system_prompt: str,
    pdf_path: Path | None,
    paper_meta: dict,
    abstract: str = "",
) -> tuple[ExtractionResult | None, dict, str]:
    """Call Gemini to extract structured data from one paper.

    Returns (result_or_None, usage_dict, error_note).
    """
    from google.genai import types

    contents = []

    # Build content parts
    if pdf_path and pdf_path.exists():
        pdf_bytes = pdf_path.read_bytes()
        contents.append(
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
        )
        user_msg = (
            f"Extract per the schema above.\n"
            f"paper_id: {paper_meta['paper_id']}\n"
            f"doi: {paper_meta['doi']}\n"
            f"Phase 2 F1 provisional: {paper_meta.get('f1_provisional', '')}"
        )
        source = "fulltext"
    else:
        # Mode B: abstract-only
        user_msg = (
            f"This paper's full text is not available. Extract what you can "
            f"from the metadata below. Raw passages will be empty.\n\n"
            f"paper_id: {paper_meta['paper_id']}\n"
            f"doi: {paper_meta['doi']}\n"
            f"Title: {paper_meta['title']}\n"
            f"Authors: {paper_meta.get('authors', '')}\n"
            f"Year: {paper_meta.get('year', '')}\n"
            f"Venue: {paper_meta.get('venue', '')}\n"
            f"Abstract: {abstract}\n"
            f"Phase 2 F1 provisional: {paper_meta.get('f1_provisional', '')}"
        )
        source = "abstract_only"

    contents.append(system_prompt + "\n\n" + user_msg)

    usage = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": ExtractionResult.model_json_schema(),
                },
            )
            # Parse usage if available
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                um = response.usage_metadata
                usage["input_tokens"] = getattr(um, "prompt_token_count", 0) or 0
                usage["output_tokens"] = getattr(um, "candidates_token_count", 0) or 0
                # Gemini 3.1 Pro standard: $2/MTok in, $12/MTok out
                usage["cost_usd"] = round(
                    usage["input_tokens"] * 2.0 / 1e6 +
                    usage["output_tokens"] * 12.0 / 1e6, 4
                )

            result = ExtractionResult.model_validate_json(response.text)
            return result, usage, source
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                print(f"  [warn] attempt {attempt+1} failed: {exc}; "
                      f"retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
            else:
                return None, usage, f"error: {exc}"

    return None, usage, "max_retries_exceeded"


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def append_matrix_row(result: ExtractionResult, source: str,
                      notes: str = "") -> None:
    """Append one row to extraction_matrix.csv."""
    MATRIX_CSV.parent.mkdir(parents=True, exist_ok=True)
    m = result.extraction_matrix
    row = {
        "paper_id": m.paper_id, "title": m.title, "authors": m.authors,
        "year": m.year, "venue": m.venue, "venue_type": m.venue_type,
        "doi": m.doi, "sample_size": m.sample_size or "",
        "sample_description": m.sample_description or "",
        "study_duration": m.study_duration or "",
        "f1_contribution_type": m.f1_contribution_type,
        "f2_research_methodology": m.f2_research_methodology,
        "f3_population": m.f3_population, "f3_context": m.f3_context,
        "f4_sdlc_activity": m.f4_sdlc_activity,
        "f5_tool_modality": m.f5_tool_modality,
        "f5_tool_paradigm": m.f5_tool_paradigm,
        "f5_tool_name": m.f5_tool_name,
        "raw_passages_file": f"artifacts/extraction/raw_passages/"
                             f"{safe_paper_id_to_filename(m.paper_id).replace('.pdf', '.md')}",
        "capability_annotations_file": "artifacts/extraction/capability_annotations.csv",
        "open_codes_tagged": "true",
        "extraction_source": source,
        "extraction_complete": "true",
        "notes": notes,
    }
    file_exists = MATRIX_CSV.exists() and MATRIX_CSV.stat().st_size > 0
    with open(MATRIX_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MATRIX_COLUMNS,
                                quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in MATRIX_COLUMNS})


def write_passages(result: ExtractionResult) -> None:
    """Write raw_passages/{safe_paper_id}.md."""
    PASSAGES_DIR.mkdir(parents=True, exist_ok=True)
    pid = result.extraction_matrix.paper_id
    safe = safe_paper_id_to_filename(pid).replace(".pdf", ".md")
    path = PASSAGES_DIR / safe
    lines = [f"# Raw Passages — {pid}\n"]
    for p in result.raw_passages:
        lines.append(f"\n## {p.passage_id}\n")
        lines.append(f"- **Section:** {p.section}\n")
        lines.append(f"- **Relevance:** {p.relevance}\n")
        lines.append(f"- **Text:**\n\n> {p.text}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def append_capability_annotations(result: ExtractionResult) -> None:
    """Append capability annotation rows."""
    CAP_ANNOT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pid = result.extraction_matrix.paper_id
    file_exists = CAP_ANNOT_CSV.exists() and CAP_ANNOT_CSV.stat().st_size > 0
    with open(CAP_ANNOT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAP_ANNOT_COLUMNS,
                                quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()
        for ca in result.capability_annotations:
            writer.writerow({
                "paper_id": pid,
                "capability_id": ca.capability_id,
                "evidence": ca.evidence,
            })


def append_open_codes(result: ExtractionResult) -> None:
    """Append open-code rows."""
    OPEN_CODES_CSV.parent.mkdir(parents=True, exist_ok=True)
    pid = result.extraction_matrix.paper_id
    file_exists = OPEN_CODES_CSV.exists() and OPEN_CODES_CSV.stat().st_size > 0
    with open(OPEN_CODES_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OPEN_CODES_COLUMNS,
                                quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()
        for oc in result.open_codes:
            writer.writerow({
                "paper_id": pid,
                "passage_id": oc.passage_id,
                "in_vivo_code": oc.in_vivo_code,
                "descriptive_code": oc.descriptive_code,
                "coder_notes": oc.coder_notes or "",
            })


# ---------------------------------------------------------------------------
# Extraction status tracking
# ---------------------------------------------------------------------------
def load_extraction_status() -> pd.DataFrame:
    if EXTRACT_STATUS.exists() and EXTRACT_STATUS.stat().st_size > 0:
        df = pd.read_csv(EXTRACT_STATUS, dtype=str).fillna("")
        for col in EXTRACT_STATUS_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame(columns=EXTRACT_STATUS_COLUMNS)


def save_extraction_status(df: pd.DataFrame) -> None:
    EXTRACT_STATUS.parent.mkdir(parents=True, exist_ok=True)
    df[EXTRACT_STATUS_COLUMNS].to_csv(
        EXTRACT_STATUS, index=False, quoting=csv.QUOTE_ALL)


def update_extraction_status(
    status_df: pd.DataFrame, paper_id: str,
    status: str, source: str, model: str,
    usage: dict, notes: str = "",
    title: str = "", venue: str = "",
    scis_rank: str = "", scis_venue_type: str = "",
    abstract: str = "", **kwargs,
) -> pd.DataFrame:
    """Add or update one row in extraction_status."""
    row = {
        "paper_id": paper_id,
        "title": title,
        "authors": kwargs.get("authors", ""),
        "year": kwargs.get("year", ""),
        "venue": venue,
        "scis_rank": scis_rank,
        "scis_venue_type": scis_venue_type,
        "abstract": abstract[:500],  # truncate for CSV readability
        "status": status,
        "extraction_source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "input_tokens": str(usage.get("input_tokens", 0)),
        "output_tokens": str(usage.get("output_tokens", 0)),
        "cost_usd": str(usage.get("cost_usd", 0.0)),
        "notes": notes,
    }
    mask = status_df["paper_id"] == paper_id
    if mask.any():
        for k, v in row.items():
            status_df.loc[mask, k] = v
    else:
        status_df = pd.concat(
            [status_df, pd.DataFrame([row])], ignore_index=True)
    return status_df


# ---------------------------------------------------------------------------
# F1 revision check
# ---------------------------------------------------------------------------
def check_f1_revision(paper_id: str, llm_f1: str, provisional_f1: str,
                      rater: str) -> bool:
    """Compare LLM F1 vs Phase 2 provisional. Log revision if different."""
    if not provisional_f1 or llm_f1 == provisional_f1:
        return False
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "3",
        "paper_id": paper_id,
        "decision": "f1_revised",
        "rule_applied": "Task 3.2 extraction confirms/revises F1 (Wieringa)",
        "rationale": (
            f"F1 revised: '{provisional_f1}' → '{llm_f1}' based on "
            f"full-text extraction by {DEFAULT_MODEL}."
        ),
        "rater_initials": rater,
    }
    first = not REGISTER.exists() or REGISTER.stat().st_size == 0
    with open(REGISTER, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if first:
            writer.writeheader()
        writer.writerow(row)
    return True


# ---------------------------------------------------------------------------
# Abstract loader (Mode B)
# ---------------------------------------------------------------------------
def load_abstract(doi: str) -> str:
    """Try to load abstract from post_filtered.csv or phase2_decisions.csv."""
    if POST_FILTERED.exists():
        pf = pd.read_csv(POST_FILTERED, dtype=str).fillna("")
        match = pf[pf["doi"].str.lower() == doi.lower()]
        if len(match) > 0:
            abstract = match.iloc[0].get("abstract", "")
            if abstract:
                return abstract
    return "(abstract not available)"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task 3.2+3.3 — LLM-assisted extraction + open coding",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Call LLM + show results, but don't write output files")
    p.add_argument("--limit", type=int, default=None,
                   help="Process first N pending papers")
    p.add_argument("--paper-id", type=str, default=None,
                   help="Extract one specific paper")
    p.add_argument("--abstract-only", action="store_true",
                   help="Force Mode B (abstract-only) for all papers")
    p.add_argument("--retry-failed", action="store_true",
                   help="Re-attempt previously failed extractions")
    p.add_argument("--verify", action="store_true",
                   help="Run DoD checks on existing outputs")
    p.add_argument("--model", type=str, default=DEFAULT_MODEL)
    p.add_argument("--api-key", type=str, default=None)
    p.add_argument("--rater", type=str,
                   default=os.environ.get("RATER_INITIALS", "AT"))
    p.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                   help=f"Concurrent extraction workers (default {DEFAULT_WORKERS}). "
                        f"Use 1 for serial behaviour.")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("  ERP2-SMS Task 3.2 + 3.3 — Extraction + Open Coding")
    print("=" * 70)
    if args.dry_run:
        print("  *** DRY-RUN — LLM will be called but NO files written ***\n")

    # --- Verify mode ---
    if args.verify:
        return _run_verify()

    # --- Load inputs ---
    if not INCLUDED_SET.exists():
        print(f"ERROR: {INCLUDED_SET} not found", file=sys.stderr)
        return 1
    included = pd.read_csv(INCLUDED_SET, dtype=str).fillna("")
    print(f"Included papers: {len(included)}")

    # Load retrieval status
    retrieval = pd.DataFrame()
    if RETRIEVAL_STATUS.exists():
        retrieval = pd.read_csv(RETRIEVAL_STATUS, dtype=str).fillna("")
    retrieved_pids = set(
        retrieval[retrieval["status"] == "retrieved"]["paper_id"].astype(str)
    ) if len(retrieval) else set()
    print(f"PDFs retrieved: {len(retrieved_pids)}")

    # Load extraction status
    ext_status = load_extraction_status()
    already_extracted = set(
        ext_status[ext_status["status"] == "extracted"]["paper_id"].astype(str)
    ) if len(ext_status) else set()
    print(f"Already extracted: {len(already_extracted)}")

    # Load enrichment data from post_filtered (SCIS rank, abstract, authors)
    scis_data: dict[str, dict] = {}
    if POST_FILTERED.exists():
        pf = pd.read_csv(POST_FILTERED, dtype=str).fillna("")
        for _, r in pf.iterrows():
            scis_data[r.get("doi", "").lower()] = {
                "scis_rank": r.get("scis_rank", ""),
                "scis_venue_type": r.get("scis_venue_type", ""),
                "abstract": r.get("abstract", ""),
                "authname": r.get("authname", ""),
            }

    # --- Build queue ---
    if args.paper_id:
        queue = included[included["paper_id"] == args.paper_id]
        if len(queue) == 0:
            print(f"ERROR: paper_id '{args.paper_id}' not in included_set",
                  file=sys.stderr)
            return 1
    elif args.retry_failed:
        failed_pids = set(
            ext_status[ext_status["status"] == "failed"]["paper_id"].astype(str)
        ) if len(ext_status) else set()
        queue = included[included["paper_id"].isin(failed_pids)]
    else:
        pending_pids = set(included["paper_id"].astype(str)) - already_extracted
        queue = included[included["paper_id"].isin(pending_pids)]

    if args.limit:
        queue = queue.head(args.limit)

    total_queue = len(queue)
    print(f"Papers to extract: {total_queue}"
          f"{f' (--limit {args.limit})' if args.limit else ''}")
    if total_queue == 0:
        print("Nothing to do.")
        return 0

    # --- Init Gemini client ---
    from google import genai
    api_key = load_google_api_key(args.api_key)
    client = genai.Client(api_key=api_key)
    print(f"Gemini client initialised (model={args.model})")

    # --- Build system prompt ---
    system_prompt = build_system_prompt()
    print(f"System prompt: {len(system_prompt)} chars\n")

    # --- Main extraction loop ---
    # Shared state (both paths mutate these; final summary reads them).
    counts = {"extracted": 0, "failed": 0, "f1_revisions": 0}
    total_cost = 0.0

    if args.workers <= 1:
        # =========================================================
        # SYNCHRONOUS PATH — one paper at a time, verbose per-step
        # printing ("Sending to model..." then "OK (tokens, cost)"
        # on the same flow). Exactly preserves the original serial
        # behaviour for single-paper runs, debugging, or when rate
        # limits require strict one-at-a-time.
        # =========================================================
        print("Mode: synchronous (workers=1)\n")
        for seq, (_, row) in enumerate(queue.iterrows(), 1):
            paper_id = row["paper_id"]
            doi = row["doi"]
            title = row["title"]
            f1_prov = row.get("f1_provisional", "")
            venue = row.get("venue", "")

            # Determine mode
            safe_fn = safe_paper_id_to_filename(paper_id)
            pdf_path = FULLTEXT_DIR / safe_fn
            if args.abstract_only or paper_id not in retrieved_pids:
                mode = "B (abstract-only)"
                pdf_use = None
            else:
                pdf_size = pdf_path.stat().st_size if pdf_path.exists() else 0
                pdf_pages_est = pdf_size // 4000
                if pdf_size > MAX_PDF_BYTES or pdf_pages_est > MAX_PDF_PAGES:
                    mode = "B (abstract-only — PDF too large)"
                    pdf_use = None
                else:
                    mode = "A (full-text PDF)"
                    pdf_use = pdf_path

            # SCIS enrichment
            scis_info = scis_data.get(doi.lower(), {})
            scis_rank_val = scis_info.get("scis_rank", row.get("scis_rank", ""))
            scis_vtype = scis_info.get("scis_venue_type", "")
            paper_abstract = scis_info.get("abstract", "")
            authors_str = scis_info.get("authname", "")
            year_str = row.get("year", "")

            status_kwargs = dict(
                title=title, venue=venue, scis_rank=scis_rank_val,
                scis_venue_type=scis_vtype, abstract=paper_abstract,
                authors=authors_str, year=year_str,
            )

            pct = seq / total_queue * 100
            print(f"\n{'─' * 70}")
            print(f"  [{seq}/{total_queue}] ({pct:.1f}%) — Mode {mode}")
            print(f"  paper_id:  {paper_id}")
            print(f"  title:     {title[:75]}")
            print(f"  venue:     {venue} [{scis_rank_val}]")
            if pdf_use:
                size = pdf_path.stat().st_size if pdf_path.exists() else 0
                pages_est = size // 4000
                print(f"  PDF:       {size:,} bytes (~{pages_est} pages)")
            print(f"{'─' * 70}")

            print(f"  → Sending to {args.model}...", end=" ", flush=True)
            abstract = ((paper_abstract or "(abstract not available)")
                        if not pdf_use else "")
            paper_meta = {
                "paper_id": paper_id, "doi": doi, "title": title,
                "year": row.get("year", ""), "venue": venue,
                "authors": "", "f1_provisional": f1_prov,
            }

            if REQUEST_DELAY:
                time.sleep(REQUEST_DELAY)
            result, usage, source = extract_one_paper(
                client, args.model, system_prompt,
                pdf_use, paper_meta, abstract,
            )

            if result is None:
                print(f"FAILED ({source})")
                counts["failed"] += 1
                if not args.dry_run:
                    ext_status = update_extraction_status(
                        ext_status, paper_id, "failed", source,
                        args.model, usage, source, **status_kwargs,
                    )
                    save_extraction_status(ext_status)
                continue

            total_cost += usage.get("cost_usd", 0)
            m = result.extraction_matrix
            print(f"OK ({usage['input_tokens']} in, {usage['output_tokens']} out, "
                  f"${usage['cost_usd']:.3f})")

            f1_match = "✓" if m.f1_contribution_type == f1_prov else "REVISED"
            print(f"  F1: {m.f1_contribution_type} ({f1_match} vs Phase 2)")
            print(f"  F2: {m.f2_research_methodology} | "
                  f"F3: {m.f3_population} × {m.f3_context}")
            print(f"  F4: {m.f4_sdlc_activity}")
            print(f"  F5: {m.f5_tool_modality} × {m.f5_tool_paradigm}")
            print(f"  Tools: {m.f5_tool_name}")
            print(f"  Sample: {m.sample_size or '?'} — "
                  f"{(m.sample_description or '')[:60]}")
            print(f"  Passages: {len(result.raw_passages)} | "
                  f"Capabilities: {len(result.capability_annotations)} | "
                  f"Open codes: {len(result.open_codes)}")

            if m.f1_contribution_type != f1_prov and f1_prov:
                if not args.dry_run:
                    check_f1_revision(paper_id, m.f1_contribution_type,
                                      f1_prov, args.rater)
                counts["f1_revisions"] += 1
                print(f"  ⚠ F1 REVISED: '{f1_prov}' → '{m.f1_contribution_type}'")

            if args.dry_run:
                print("\n  --- DRY-RUN JSON preview (first passage + first code) ---")
                if result.raw_passages:
                    p = result.raw_passages[0]
                    print(f"  Passage {p.passage_id} [{p.relevance}] ({p.section}):")
                    print(f"    \"{p.text[:150]}...\"")
                if result.open_codes:
                    oc = result.open_codes[0]
                    print(f"  Code {oc.passage_id}: "
                          f"in_vivo=\"{oc.in_vivo_code[:60]}\" "
                          f"→ desc=\"{oc.descriptive_code}\"")
                if result.capability_annotations:
                    ca = result.capability_annotations[0]
                    print(f"  Cap: {ca.capability_id} — {ca.evidence[:80]}")
            else:
                append_matrix_row(result, source)
                write_passages(result)
                append_capability_annotations(result)
                append_open_codes(result)
                ext_status = update_extraction_status(
                    ext_status, paper_id, "extracted", source,
                    args.model, usage, **status_kwargs,
                )
                save_extraction_status(ext_status)
                print("  ✓ Written: matrix row + passages + annotations + codes")

            counts["extracted"] += 1

            if seq % 25 == 0 or seq == total_queue:
                print(f"\n  === Progress: {seq}/{total_queue} "
                      f"(extracted={counts['extracted']}, "
                      f"failed={counts['failed']}, "
                      f"cost=${total_cost:.2f}) ===")

        # End synchronous path
        pass  # fall through to final summary

    else:
        # =========================================================
        # ASYNCHRONOUS PATH — ThreadPoolExecutor with write_lock
        # serialising all shared-state mutations (counters,
        # ext_status DataFrame, CSV appends, decision_register,
        # stdout). Only the long-running LLM call runs lock-free.
        # =========================================================
        completed = 0
        write_lock = threading.Lock()
        # Boxed ref so workers can rebind the ext_status DataFrame returned
        # by update_extraction_status() (fresh concat when adding new rows).
        ext_status_box = {"df": ext_status}
        print(f"Mode: asynchronous (workers={args.workers})\n")

        def process_one_paper(row: pd.Series) -> None:
            """Extract one paper. Safe to run concurrently.

            Only the long-running LLM call happens lock-free; every
            shared-state mutation (counters, ext_status DataFrame, CSV
            appends, decision register, stdout) is serialised under
            write_lock so output files stay row-consistent and
            non-interleaved.
            """
            nonlocal total_cost, completed

            paper_id = row["paper_id"]
            doi = row["doi"]
            title = row["title"]
            f1_prov = row.get("f1_provisional", "")
            venue = row.get("venue", "")

            # --- Mode determination (pure reads: safe outside the lock) ---
            safe_fn = safe_paper_id_to_filename(paper_id)
            pdf_path = FULLTEXT_DIR / safe_fn
            pdf_size = 0
            pdf_pages_est = 0
            if args.abstract_only or paper_id not in retrieved_pids:
                mode = "B (abstract-only)"
                pdf_use = None
            else:
                pdf_size = pdf_path.stat().st_size if pdf_path.exists() else 0
                pdf_pages_est = pdf_size // 4000
                if pdf_size > MAX_PDF_BYTES or pdf_pages_est > MAX_PDF_PAGES:
                    mode = "B (abstract-only — PDF too large)"
                    pdf_use = None
                else:
                    mode = "A (full-text PDF)"
                    pdf_use = pdf_path

            # SCIS enrichment (read-only dict access is thread-safe)
            scis_info = scis_data.get(doi.lower(), {})
            scis_rank_val = scis_info.get("scis_rank", row.get("scis_rank", ""))
            scis_vtype = scis_info.get("scis_venue_type", "")
            paper_abstract = scis_info.get("abstract", "")
            authors_str = scis_info.get("authname", "")
            year_str = row.get("year", "")

            status_kwargs = dict(
                title=title, venue=venue, scis_rank=scis_rank_val,
                scis_venue_type=scis_vtype, abstract=paper_abstract,
                authors=authors_str, year=year_str,
            )

            # --- LLM call (LOCK-FREE — the expensive part) ---
            # Use the already-loaded scis_data abstract instead of re-reading
            # post_filtered.csv per call (matters under concurrency).
            abstract = ((paper_abstract or "(abstract not available)")
                        if not pdf_use else "")
            paper_meta = {
                "paper_id": paper_id, "doi": doi, "title": title,
                "year": row.get("year", ""), "venue": venue,
                "authors": "", "f1_provisional": f1_prov,
            }
            if REQUEST_DELAY:
                time.sleep(REQUEST_DELAY)
            result, usage, source = extract_one_paper(
                client, args.model, system_prompt,
                pdf_use, paper_meta, abstract,
            )

            # --- Serialised: counters, file writes, stdout ---
            with write_lock:
                completed += 1
                my_seq = completed
                pct = my_seq / total_queue * 100

                lines = [
                    f"\n{'─' * 70}",
                    f"  [{my_seq}/{total_queue}] ({pct:.1f}%) — Mode {mode}",
                    f"  paper_id:  {paper_id}",
                    f"  title:     {title[:75]}",
                    f"  venue:     {venue} [{scis_rank_val}]",
                ]
                if pdf_use:
                    lines.append(
                        f"  PDF:       {pdf_size:,} bytes "
                        f"(~{pdf_pages_est} pages)"
                    )
                lines.append(f"{'─' * 70}")

                if result is None:
                    lines.append(f"  → {args.model}: FAILED ({source})")
                    counts["failed"] += 1
                    if not args.dry_run:
                        ext_status_box["df"] = update_extraction_status(
                            ext_status_box["df"], paper_id, "failed", source,
                            args.model, usage, source, **status_kwargs,
                        )
                        save_extraction_status(ext_status_box["df"])
                    if my_seq % 25 == 0 or my_seq == total_queue:
                        lines.append(
                            f"\n  === Progress: {my_seq}/{total_queue} "
                            f"(extracted={counts['extracted']}, "
                            f"failed={counts['failed']}, "
                            f"cost=${total_cost:.2f}) ==="
                        )
                    print("\n".join(lines), flush=True)
                    return

                total_cost += usage.get("cost_usd", 0)
                m = result.extraction_matrix
                lines.append(
                    f"  → {args.model}: OK ({usage['input_tokens']} in, "
                    f"{usage['output_tokens']} out, "
                    f"${usage['cost_usd']:.3f})"
                )

                f1_match = "✓" if m.f1_contribution_type == f1_prov else "REVISED"
                lines.append(
                    f"  F1: {m.f1_contribution_type} ({f1_match} vs Phase 2)"
                )
                lines.append(
                    f"  F2: {m.f2_research_methodology} | "
                    f"F3: {m.f3_population} × {m.f3_context}"
                )
                lines.append(f"  F4: {m.f4_sdlc_activity}")
                lines.append(
                    f"  F5: {m.f5_tool_modality} × {m.f5_tool_paradigm}"
                )
                lines.append(f"  Tools: {m.f5_tool_name}")
                lines.append(
                    f"  Sample: {m.sample_size or '?'} — "
                    f"{(m.sample_description or '')[:60]}"
                )
                lines.append(
                    f"  Passages: {len(result.raw_passages)} | "
                    f"Capabilities: {len(result.capability_annotations)} | "
                    f"Open codes: {len(result.open_codes)}"
                )

                if m.f1_contribution_type != f1_prov and f1_prov:
                    if not args.dry_run:
                        check_f1_revision(paper_id, m.f1_contribution_type,
                                          f1_prov, args.rater)
                    counts["f1_revisions"] += 1
                    lines.append(
                        f"  ⚠ F1 REVISED: '{f1_prov}' → "
                        f"'{m.f1_contribution_type}'"
                    )

                if args.dry_run:
                    lines.append(
                        "\n  --- DRY-RUN JSON preview "
                        "(first passage + first code) ---"
                    )
                    if result.raw_passages:
                        p = result.raw_passages[0]
                        lines.append(
                            f"  Passage {p.passage_id} [{p.relevance}] "
                            f"({p.section}):"
                        )
                        lines.append(f'    "{p.text[:150]}..."')
                    if result.open_codes:
                        oc = result.open_codes[0]
                        lines.append(
                            f'  Code {oc.passage_id}: '
                            f'in_vivo="{oc.in_vivo_code[:60]}" '
                            f'→ desc="{oc.descriptive_code}"'
                        )
                    if result.capability_annotations:
                        ca = result.capability_annotations[0]
                        lines.append(
                            f"  Cap: {ca.capability_id} — {ca.evidence[:80]}"
                        )
                else:
                    # Write order matters for resume-ability: append
                    # matrix/passages/annotations/codes FIRST, then mark
                    # status='extracted' last so a crash mid-write leaves
                    # the paper re-queueable rather than silently skipped.
                    append_matrix_row(result, source)
                    write_passages(result)
                    append_capability_annotations(result)
                    append_open_codes(result)
                    ext_status_box["df"] = update_extraction_status(
                        ext_status_box["df"], paper_id, "extracted", source,
                        args.model, usage, **status_kwargs,
                    )
                    save_extraction_status(ext_status_box["df"])
                    lines.append(
                        "  ✓ Written: matrix row + passages + "
                        "annotations + codes"
                    )

                counts["extracted"] += 1

                if my_seq % 25 == 0 or my_seq == total_queue:
                    lines.append(
                        f"\n  === Progress: {my_seq}/{total_queue} "
                        f"(extracted={counts['extracted']}, "
                        f"failed={counts['failed']}, "
                        f"cost=${total_cost:.2f}) ==="
                    )

                print("\n".join(lines), flush=True)

        # Dispatch the queue across the pool.
        rows_to_process = [r for _, r in queue.iterrows()]
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(process_one_paper, r)
                for r in rows_to_process
            ]
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as exc:
                    with write_lock:
                        print(f"\n[ERROR] worker raised: {exc}",
                              file=sys.stderr, flush=True)

        # Reclaim the final DataFrame reference so any downstream code in
        # main() sees the fully-updated status.
        ext_status = ext_status_box["df"]

    # --- Final summary ---
    print(f"\n{'=' * 70}")
    print(f"  Extraction complete")
    print(f"{'=' * 70}")
    print(f"  Extracted:     {counts['extracted']}")
    print(f"  Failed:        {counts['failed']}")
    print(f"  F1 revisions:  {counts['f1_revisions']}")
    print(f"  Total cost:    ${total_cost:.2f}")
    if args.dry_run:
        print(f"\n  *** DRY-RUN: no files written ***")

    if counts["failed"] > 0:
        return 2
    return 0


# ---------------------------------------------------------------------------
# DoD verification
# ---------------------------------------------------------------------------
def _run_verify() -> int:
    """Run Task 3.2 + 3.3 DoD assertions on existing outputs."""
    print("\n=== DoD Verification ===\n")
    errors = 0

    if not MATRIX_CSV.exists():
        print("✗ extraction_matrix.csv not found")
        return 1
    matrix = pd.read_csv(MATRIX_CSV, dtype=str).fillna("")
    included = pd.read_csv(INCLUDED_SET, dtype=str).fillna("")
    print(f"Matrix rows: {len(matrix)} / Included: {len(included)}")

    # Check F1-F5 non-null
    facet_cols = [
        "f1_contribution_type", "f2_research_methodology",
        "f3_population", "f3_context", "f4_sdlc_activity",
        "f5_tool_modality", "f5_tool_paradigm",
    ]
    for col in facet_cols:
        nulls = (matrix[col] == "").sum()
        if nulls > 0:
            print(f"  ✗ {col}: {nulls} null values")
            errors += 1
        else:
            print(f"  ✓ {col}: all non-null")

    # Check raw_passages files exist
    missing_passages = 0
    for _, row in matrix.iterrows():
        safe = safe_paper_id_to_filename(row["paper_id"]).replace(".pdf", ".md")
        if not (PASSAGES_DIR / safe).exists():
            missing_passages += 1
    if missing_passages:
        print(f"  ✗ {missing_passages} raw_passages files missing")
        errors += 1
    else:
        print(f"  ✓ All {len(matrix)} raw_passages files exist")

    # Check open codes coverage
    if OPEN_CODES_CSV.exists():
        codes = pd.read_csv(OPEN_CODES_CSV, dtype=str).fillna("")
        print(f"  Open codes: {len(codes)} rows across "
              f"{codes['paper_id'].nunique()} papers")
    else:
        print(f"  ✗ open_codes_pass1.csv not found")
        errors += 1

    if errors == 0:
        print(f"\n✓ All DoD checks passed")
        return 0
    else:
        print(f"\n✗ {errors} DoD issues found")
        return 1


if __name__ == "__main__":
    sys.exit(main())
