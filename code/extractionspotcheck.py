"""Task 3.3 — Independent spot-check of extraction.py output.

Uses GPT-5.4 (a DIFFERENT model family from Gemini 3.1 Pro which did the
extraction) to independently verify the extraction quality. Cross-model
disagreements surface real extraction errors.

Supports two modes:
  - Batch API (default): 50% cost discount, results in 1-6 hours
  - Synchronous (--sync): immediate results, 2× cost

Sampling strategies:
  - Stratified (default): A* oversampled (30%), A (20%), B (15%), Not found (8%)
  - Random: pure random 10% with --seed for reproducibility

Usage:
    python code/extractionspotcheck.py --limit 25          # submit batch
    python code/extractionspotcheck.py --status             # check batch
    python code/extractionspotcheck.py --download           # fetch results
    python code/extractionspotcheck.py --summary            # human-readable report
    python code/extractionspotcheck.py --sync --limit 3     # immediate (3 papers)

Design: design/3_3_extractionspotcheck.md
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import pdfplumber
from pydantic import BaseModel, Field

# Silence pdfminer noise
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.retrieval import safe_paper_id_to_filename  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EXTRACTION_DIR   = ROOT / "artifacts" / "extraction"
MATRIX_CSV       = EXTRACTION_DIR / "extraction_matrix.csv"
PASSAGES_DIR     = EXTRACTION_DIR / "raw_passages"
CAP_ANNOT_CSV    = EXTRACTION_DIR / "capability_annotations.csv"
OPEN_CODES_CSV   = EXTRACTION_DIR / "open_codes_pass1.csv"
FULLTEXT_DIR     = EXTRACTION_DIR / "fulltext"
RESULTS_CSV      = EXTRACTION_DIR / "spotcheck_results.csv"
SUMMARY_MD       = EXTRACTION_DIR / "spotcheck_summary.md"
BATCH_STATE_JSON = EXTRACTION_DIR / "spotcheck_batch_state.json"
BATCH_INPUT_JSONL = EXTRACTION_DIR / "spotcheck_batch_input.jsonl"

DEFAULT_MODEL    = "gpt-5.4"
SYNC_DELAY       = 1.5  # seconds between synchronous calls

# Stratified sampling rates by SCIS rank
STRATIFIED_RATES = {"A*": 0.30, "A": 0.20, "B": 0.15, "Not found": 0.08}

# ---------------------------------------------------------------------------
# Checklist definition (from 3_3_extraction_checklist.md)
# ---------------------------------------------------------------------------
CHECKS = [
    # Category A — Metadata
    {"id": "A1", "cat": "A", "desc": "paper_id matches doi", "rq": "All"},
    {"id": "A2", "cat": "A", "desc": "title matches actual paper", "rq": "All"},
    {"id": "A3", "cat": "A", "desc": "venue and venue_type correct", "rq": "RQ1"},
    {"id": "A4", "cat": "A", "desc": "year is publication year", "rq": "RQ1"},
    {"id": "A5", "cat": "A", "desc": "sample_size is human-participant count", "rq": "RQ1"},
    {"id": "A6", "cat": "A", "desc": "sample_description captures who was studied", "rq": "RQ1,RQ2"},
    # Category B — Facets
    {"id": "B1", "cat": "B", "desc": "F1 matches Wieringa criteria (EvRes needs N>=5 + empirical section + usage findings)", "rq": "RQ1"},
    {"id": "B2", "cat": "B", "desc": "F1 revision vs Phase 2 provisional justified", "rq": "RQ1"},
    {"id": "B3", "cat": "B", "desc": "F2 methodology correctly identified", "rq": "RQ1"},
    {"id": "B4", "cat": "B", "desc": "F3 population matches participants", "rq": "RQ1,RQ2"},
    {"id": "B5", "cat": "B", "desc": "F3 context matches setting", "rq": "RQ1,RQ2"},
    {"id": "B6", "cat": "B", "desc": "F4 SDLC — all relevant activities tagged (no under-tagging)", "rq": "RQ1,RQ3"},
    {"id": "B7", "cat": "B", "desc": "F4 SDLC — no over-tagging (only evidenced activities)", "rq": "RQ1,RQ3"},
    {"id": "B8", "cat": "B", "desc": "F5 modality correct multi-select", "rq": "RQ1,RQ2"},
    {"id": "B9", "cat": "B", "desc": "F5 paradigm (Pro-code/Low-code/No-code) based on actual usage", "rq": "RQ1"},
    {"id": "B10", "cat": "B", "desc": "F5 tool_name — all tools listed", "rq": "RQ1"},
    # Category C — Passages
    {"id": "C1", "cat": "C", "desc": "passages are verbatim (not paraphrased)", "rq": "RQ2"},
    {"id": "C2", "cat": "C", "desc": "passages describe how users interact with AI tool", "rq": "RQ2"},
    {"id": "C3", "cat": "C", "desc": "sufficient passages per paper (3-8 for EvRes)", "rq": "RQ2"},
    {"id": "C4", "cat": "C", "desc": "relevance tags appropriate", "rq": "RQ2,RQ3"},
    {"id": "C5", "cat": "C", "desc": "section attribution correct", "rq": "RQ2"},
    # Category D — Capabilities
    {"id": "D1", "cat": "D", "desc": "only evidenced capabilities annotated (no over-annotation)", "rq": "RQ3"},
    {"id": "D2", "cat": "D", "desc": "no missed capabilities (no under-annotation)", "rq": "RQ3"},
    {"id": "D3", "cat": "D", "desc": "capability_ids are valid (from 19 harmonised list)", "rq": "RQ3"},
    {"id": "D4", "cat": "D", "desc": "evidence field is specific (not vague)", "rq": "RQ3"},
    # Category E — Open codes
    {"id": "E1", "cat": "E", "desc": "in_vivo_code is author's exact words", "rq": "RQ2"},
    {"id": "E2", "cat": "E", "desc": "descriptive_code is meaningful analytic label", "rq": "RQ2"},
    {"id": "E3", "cat": "E", "desc": "every passage has >=1 open code", "rq": "RQ2"},
    {"id": "E4", "cat": "E", "desc": "codes are consistent across papers", "rq": "RQ2"},
]

CAT_NAMES = {
    "A": "Metadata", "B": "Facets", "C": "Passages",
    "D": "Capabilities", "E": "OpenCodes",
}

# ---------------------------------------------------------------------------
# Pydantic response schema
# ---------------------------------------------------------------------------
class CheckResult(BaseModel):
    check_id: str
    verdict: Literal["pass", "fail", "uncertain"]
    current_value: str
    suggested_value: str = ""
    rationale: str

class SpotCheckResponse(BaseModel):
    paper_id: str
    checks: list[CheckResult]

# JSON schema for OpenAI structured output
RESPONSE_JSON_SCHEMA = {
    "name": "SpotCheckResponse",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "paper_id": {"type": "string"},
            "checks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "check_id": {"type": "string"},
                        "verdict": {"type": "string", "enum": ["pass", "fail", "uncertain"]},
                        "current_value": {"type": "string"},
                        "suggested_value": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["check_id", "verdict", "current_value", "suggested_value", "rationale"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["paper_id", "checks"],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an INDEPENDENT QUALITY AUDITOR for a Systematic Mapping Study titled "How Do People Use AI Agents for Software Engineering?"

A different AI model (Gemini 3.1 Pro) was used to extract structured data from academic papers. Your job is to VERIFY that extraction by reading the original paper yourself and checking the extraction against a checklist.

You are NOT re-extracting. You are AUDITING. For each check:
- Read the relevant part of the paper
- Compare what the paper actually says against what the extraction claims
- Give a verdict

For each check, return a verdict:
- "pass": the extraction is correct — the paper supports this coding
- "fail": the extraction has an error — provide what the correct value should be in suggested_value
- "uncertain": cannot determine from the paper — flag for human review

Be STRICT on (highest-impact errors):
- B1/F1 (Wieringa classification): Evaluation Research requires N≥5 + dedicated empirical section + usage findings beyond tool correctness. Solution Proposal = tool description dominates, user study <5. Validation Research = benchmark is primary.
- B6/B7 (F4 SDLC Activity): check for BOTH under-tagging (missed activities the paper covers) and over-tagging (activities tagged without evidence)
- C1 (Verbatim passages): must be EXACT quotes from the paper, not paraphrases — check character-by-character
- D1/D2 (Capabilities): must be actually demonstrated/studied in the paper, not just mentioned in passing or future work

Be LENIENT on (minor issues):
- A2 (title): minor formatting differences acceptable
- C5 (section attribution): approximate section names are fine
- E2 (descriptive codes): reasonable analytic labels are subjective — only flag if clearly wrong

IMPORTANT: Your role is to catch errors the extraction model made. Focus on disagreements. Agreement means the extraction is likely correct. For each check, put the CURRENT extraction value in current_value and your suggested correction (if any) in suggested_value."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_openai_api_key(cli_override: str | None = None) -> str:
    """Load OPENAI_API_KEY from CLI → env → .env."""
    if cli_override:
        return cli_override
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY=") and len(line) > len("OPENAI_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                return val
    raise ValueError("OPENAI_API_KEY not found. Set in .env or pass --api-key.")


def extract_paper_text(pdf_path: Path, max_chars: int = 50000) -> str:
    """Extract text from PDF via pdfplumber for verification."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
        full = "\n\n".join(pages)
        return full[:max_chars]
    except Exception as exc:
        return f"(PDF extraction failed: {exc})"


def load_extraction_data(paper_id: str) -> dict:
    """Load all extraction outputs for one paper as a dict."""
    # Matrix row
    matrix = pd.read_csv(MATRIX_CSV, dtype=str).fillna("")
    row = matrix[matrix["paper_id"] == paper_id]
    matrix_data = row.iloc[0].to_dict() if len(row) > 0 else {}

    # Passages
    safe = safe_paper_id_to_filename(paper_id).replace(".pdf", ".md")
    passage_path = PASSAGES_DIR / safe
    passages_text = passage_path.read_text(encoding="utf-8") if passage_path.exists() else "(no passages file)"

    # Capability annotations
    caps = pd.read_csv(CAP_ANNOT_CSV, dtype=str).fillna("") if CAP_ANNOT_CSV.exists() else pd.DataFrame()
    cap_rows = caps[caps["paper_id"] == paper_id] if len(caps) > 0 else pd.DataFrame()
    cap_list = [r.to_dict() for _, r in cap_rows.iterrows()]

    # Open codes
    codes = pd.read_csv(OPEN_CODES_CSV, dtype=str).fillna("") if OPEN_CODES_CSV.exists() else pd.DataFrame()
    code_rows = codes[codes["paper_id"] == paper_id] if len(codes) > 0 else pd.DataFrame()
    code_list = [r.to_dict() for _, r in code_rows.iterrows()]

    return {
        "matrix": matrix_data,
        "passages": passages_text,
        "capabilities": cap_list,
        "open_codes": code_list,
    }


def build_user_message(paper_id: str, paper_text: str,
                       extraction: dict, checks_to_run: list[str]) -> str:
    """Build the user message with paper text + extraction + check list."""
    m = extraction["matrix"]
    checks_text = "\n".join(
        f"- {c['id']}: {c['desc']} [RQ: {c['rq']}]"
        for c in CHECKS if c["cat"] in checks_to_run
    )
    return f"""PAPER TEXT (extracted from PDF):
{paper_text}

---

EXISTING EXTRACTION FOR {paper_id}:

Matrix row:
  paper_id: {m.get('paper_id', '')}
  title: {m.get('title', '')}
  authors: {m.get('authors', '')}
  year: {m.get('year', '')}
  venue: {m.get('venue', '')}
  venue_type: {m.get('venue_type', '')}
  doi: {m.get('doi', '')}
  sample_size: {m.get('sample_size', '')}
  sample_description: {m.get('sample_description', '')}
  study_duration: {m.get('study_duration', '')}
  f1_contribution_type: {m.get('f1_contribution_type', '')}
  f2_research_methodology: {m.get('f2_research_methodology', '')}
  f3_population: {m.get('f3_population', '')}
  f3_context: {m.get('f3_context', '')}
  f4_sdlc_activity: {m.get('f4_sdlc_activity', '')}
  f5_tool_modality: {m.get('f5_tool_modality', '')}
  f5_tool_paradigm: {m.get('f5_tool_paradigm', '')}
  f5_tool_name: {m.get('f5_tool_name', '')}
  extraction_source: {m.get('extraction_source', '')}

Raw passages (first 3000 chars):
{extraction['passages'][:3000]}

Capability annotations:
{json.dumps(extraction['capabilities'][:10], indent=2)}

Open codes (first 10):
{json.dumps(extraction['open_codes'][:10], indent=2)}

---

CHECKS TO EVALUATE:
{checks_text}

For EACH check listed above, provide a verdict (pass/fail/uncertain) with rationale. Put the current extraction value in current_value and your suggested correction in suggested_value (empty if pass)."""


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------
def sample_papers(matrix: pd.DataFrame, limit: int | None,
                  strategy: str, seed: int) -> pd.DataFrame:
    """Sample papers for spot-check."""
    rng = np.random.default_rng(seed)

    if strategy == "random":
        n = limit or max(1, int(len(matrix) * 0.10))
        n = min(n, len(matrix))
        indices = rng.choice(len(matrix), size=n, replace=False)
        return matrix.iloc[sorted(indices)].copy()

    # Stratified sampling
    # Get SCIS rank — may need to merge from extraction_status or retrieval_status
    if "scis_rank" not in matrix.columns or matrix["scis_rank"].isna().all():
        # Try to get from extraction_status
        ext_status_path = EXTRACTION_DIR / "extraction_status.csv"
        if ext_status_path.exists():
            ext = pd.read_csv(ext_status_path, dtype=str).fillna("")
            matrix = matrix.merge(
                ext[["paper_id", "scis_rank"]].drop_duplicates("paper_id"),
                on="paper_id", how="left", suffixes=("", "_ext"),
            )
            if "scis_rank_ext" in matrix.columns:
                matrix["scis_rank"] = matrix["scis_rank"].fillna(matrix["scis_rank_ext"])
                matrix.drop(columns=["scis_rank_ext"], inplace=True)
        matrix["scis_rank"] = matrix.get("scis_rank", pd.Series(["Not found"] * len(matrix))).fillna("Not found")

    sampled = []
    total_budget = limit or max(1, int(len(matrix) * 0.10))
    remaining = total_budget

    for rank in ["A*", "A", "B", "Not found"]:
        stratum = matrix[matrix["scis_rank"] == rank]
        if len(stratum) == 0:
            continue
        rate = STRATIFIED_RATES.get(rank, 0.08)
        n = max(1, int(len(stratum) * rate))
        n = min(n, len(stratum), remaining)
        if n > 0:
            indices = rng.choice(len(stratum), size=n, replace=False)
            sampled.append(stratum.iloc[sorted(indices)])
            remaining -= n
        if remaining <= 0:
            break

    if not sampled:
        return matrix.head(0)
    result = pd.concat(sampled, ignore_index=True)
    print(f"  Sampling strategy: {strategy}")
    print(f"  Sampled by rank: " + ", ".join(
        f"{rank}={len(result[result['scis_rank']==rank])}"
        for rank in ["A*", "A", "B", "Not found"]
        if len(result[result["scis_rank"] == rank]) > 0
    ))
    return result


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------
def build_batch_jsonl(sampled: pd.DataFrame, model: str,
                      checks_to_run: list[str]) -> Path:
    """Build JSONL input file for OpenAI Batch API."""
    BATCH_INPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    total = len(sampled)
    count = 0
    total_input_chars = 0
    print(f"  Building batch JSONL ({total} papers)...")
    with open(BATCH_INPUT_JSONL, "w", encoding="utf-8") as f:
        for idx, (_, row) in enumerate(sampled.iterrows(), 1):
            paper_id = row["paper_id"]
            safe_fn = safe_paper_id_to_filename(paper_id)
            pdf_path = FULLTEXT_DIR / safe_fn
            title = row.get("title", "")[:60]

            # Progress per paper (pdfplumber extraction can be slow)
            has_pdf = pdf_path.exists()
            print(f"    [{idx}/{total}] {paper_id} "
                  f"({'PDF' if has_pdf else 'no-PDF'}) {title}",
                  end="", flush=True)

            paper_text = extract_paper_text(pdf_path) if has_pdf else "(no PDF available — abstract-only paper)"
            extraction = load_extraction_data(paper_id)
            user_msg = build_user_message(paper_id, paper_text, extraction, checks_to_run)
            custom_id = f"spotcheck_{safe_fn.replace('.pdf', '')}"

            line = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "reasoning_effort": "medium",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": RESPONSE_JSON_SCHEMA,
                    },
                },
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
            count += 1
            msg_len = len(user_msg)
            total_input_chars += msg_len
            print(f" ({msg_len:,} chars)")

    est_tokens = total_input_chars // 4
    est_cost = est_tokens * 2.50 / 1e6 + count * 2000 * 11.25 / 1e6
    print(f"  ✓ Built {BATCH_INPUT_JSONL.relative_to(ROOT)}")
    print(f"    {count} requests, ~{est_tokens:,} input tokens")
    print(f"    Estimated batch cost: ${est_cost:.2f}")
    return BATCH_INPUT_JSONL


def submit_batch(client, model: str) -> str:
    """Upload JSONL + create batch. Returns batch ID."""
    batch_file = client.files.create(
        file=open(BATCH_INPUT_JSONL, "rb"),
        purpose="batch",
    )
    print(f"  Uploaded file: {batch_file.id}")

    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"description": "ERP2-SMS extraction spot-check"},
    )
    print(f"  Batch created: {batch.id} (status={batch.status})")

    # Persist state
    state = {
        "batch_id": batch.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "status": batch.status,
        "input_file_id": batch_file.id,
        "output_file_id": None,
    }
    BATCH_STATE_JSON.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return batch.id


def check_batch_status(client) -> dict:
    """Check current batch status."""
    if not BATCH_STATE_JSON.exists():
        print("ERROR: No batch state found. Run without --status first.")
        return {}
    state = json.loads(BATCH_STATE_JSON.read_text())
    batch = client.batches.retrieve(state["batch_id"])
    state["status"] = batch.status
    if batch.output_file_id:
        state["output_file_id"] = batch.output_file_id
    BATCH_STATE_JSON.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"  Batch: {state['batch_id']}")
    print(f"  Status: {batch.status}")
    if hasattr(batch, "request_counts") and batch.request_counts:
        rc = batch.request_counts
        print(f"  Completed: {rc.completed}/{rc.total} "
              f"(failed: {rc.failed})")
    return state


def download_batch_results(client) -> int:
    """Download batch results → spotcheck_results.csv. Returns row count."""
    if not BATCH_STATE_JSON.exists():
        print("ERROR: No batch state found.")
        return 0
    state = json.loads(BATCH_STATE_JSON.read_text())
    if not state.get("output_file_id"):
        # Try refreshing
        state = check_batch_status(client)
    if not state.get("output_file_id"):
        print(f"ERROR: Batch not yet complete (status={state.get('status')})")
        return 0

    print(f"  Downloading results from {state['output_file_id']}...")
    content = client.files.content(state["output_file_id"])
    raw_lines = content.text.strip().split("\n")
    print(f"  Downloaded {len(raw_lines)} result lines")

    # Load matrix for paper metadata
    matrix = pd.read_csv(MATRIX_CSV, dtype=str).fillna("")
    matrix_lookup = {r["paper_id"]: r for _, r in matrix.iterrows()}

    # Parse results → CSV
    print(f"  Parsing results...")
    rows = []
    parsed_papers = 0
    total_fails = 0
    for line in raw_lines:
        entry = json.loads(line)
        custom_id = entry.get("custom_id", "")
        response_body = entry.get("response", {}).get("body", {})
        choices = response_body.get("choices", [])
        if not choices:
            continue
        content_str = choices[0].get("message", {}).get("content", "")
        try:
            result = json.loads(content_str)
        except json.JSONDecodeError:
            continue

        paper_id = result.get("paper_id", "")
        meta = matrix_lookup.get(paper_id, {})

        parsed_papers += 1
        paper_fails = 0
        for check in result.get("checks", []):
            check_def = next((c for c in CHECKS if c["id"] == check.get("check_id")), None)
            verdict = check.get("verdict", "")
            if verdict == "fail":
                paper_fails += 1
                total_fails += 1
            rows.append({
                "paper_id": paper_id,
                "title": meta.get("title", ""),
                "venue": meta.get("venue", ""),
                "scis_rank": meta.get("scis_rank", ""),
                "extraction_source": meta.get("extraction_source", ""),
                "check_id": check.get("check_id", ""),
                "check_category": check_def["cat"] if check_def else "",
                "check_description": check_def["desc"] if check_def else "",
                "rq_served": check_def["rq"] if check_def else "",
                "verdict": verdict,
                "current_value": check.get("current_value", ""),
                "suggested_value": check.get("suggested_value", ""),
                "rationale": check.get("rationale", ""),
                "human_verified": "",
                "human_notes": "",
            })
        status_icon = "✓" if paper_fails == 0 else f"✗ ({paper_fails} fails)"
        print(f"    [{parsed_papers}/{len(raw_lines)}] {paper_id} {status_icon}")

    print(f"  Parsed {parsed_papers} papers, {total_fails} total fails")

    # Write CSV
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(RESULTS_CSV, index=False, quoting=csv.QUOTE_ALL)
        print(f"  Written: {RESULTS_CSV.relative_to(ROOT)} ({len(rows)} rows, "
              f"{df['paper_id'].nunique()} papers)")
    return len(rows)


# ---------------------------------------------------------------------------
# Synchronous mode
# ---------------------------------------------------------------------------
def run_sync(client, sampled: pd.DataFrame, model: str,
             checks_to_run: list[str]) -> int:
    """Run spot-check synchronously (immediate results)."""
    from openai import OpenAI

    matrix = pd.read_csv(MATRIX_CSV, dtype=str).fillna("")
    matrix_lookup = {r["paper_id"]: r for _, r in matrix.iterrows()}

    rows = []
    total_fails = 0
    total_uncertain = 0
    start_time = time.time()
    for seq, (_, row) in enumerate(sampled.iterrows(), 1):
        paper_id = row["paper_id"]
        safe_fn = safe_paper_id_to_filename(paper_id)
        pdf_path = FULLTEXT_DIR / safe_fn
        meta = matrix_lookup.get(paper_id, {})

        print(f"\n{'─' * 60}")
        print(f"  [{seq}/{len(sampled)}] {paper_id}")
        print(f"    title: {meta.get('title', '')[:70]}")
        print(f"    venue: {meta.get('venue', '')} [{meta.get('scis_rank', '')}]")
        print(f"    source: {'PDF' if pdf_path.exists() else 'abstract-only'}")

        paper_text = extract_paper_text(pdf_path) if pdf_path.exists() else "(no PDF)"
        extraction = load_extraction_data(paper_id)
        user_msg = build_user_message(paper_id, paper_text, extraction, checks_to_run)

        print(f"    → Sending to {model}...", end=" ", flush=True)
        time.sleep(SYNC_DELAY)

        try:
            response = client.chat.completions.create(
                model=model,
                reasoning_effort="medium",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": RESPONSE_JSON_SCHEMA,
                },
            )
            content_str = response.choices[0].message.content
            result = json.loads(content_str)
        except Exception as exc:
            print(f"FAILED ({exc})")
            continue

        checks = result.get("checks", [])
        fails = sum(1 for c in checks if c.get("verdict") == "fail")
        uncertain = sum(1 for c in checks if c.get("verdict") == "uncertain")
        total_fails += fails
        total_uncertain += uncertain
        print(f"OK ({len(checks)} checks: {fails} fail, {uncertain} uncertain)")

        for check in checks:
            check_def = next((c for c in CHECKS if c["id"] == check.get("check_id")), None)
            rows.append({
                "paper_id": paper_id,
                "title": meta.get("title", ""),
                "venue": meta.get("venue", ""),
                "scis_rank": meta.get("scis_rank", ""),
                "extraction_source": meta.get("extraction_source", ""),
                "check_id": check.get("check_id", ""),
                "check_category": check_def["cat"] if check_def else "",
                "check_description": check_def["desc"] if check_def else "",
                "rq_served": check_def["rq"] if check_def else "",
                "verdict": check.get("verdict", ""),
                "current_value": check.get("current_value", ""),
                "suggested_value": check.get("suggested_value", ""),
                "rationale": check.get("rationale", ""),
                "human_verified": "",
                "human_notes": "",
            })

        if fails > 0:
            for c in checks:
                if c.get("verdict") == "fail":
                    print(f"    ✗ {c['check_id']}: {c.get('rationale', '')[:80]}")

        # Progress summary every 10 papers
        if seq % 10 == 0 or seq == len(sampled):
            elapsed = time.time() - start_time
            rate = seq / elapsed if elapsed > 0 else 0
            remaining_est = (len(sampled) - seq) / rate if rate > 0 else 0
            print(f"\n  === Progress: {seq}/{len(sampled)} | "
                  f"fails={total_fails} uncertain={total_uncertain} | "
                  f"elapsed={elapsed:.0f}s | "
                  f"~{remaining_est:.0f}s remaining ===")

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(RESULTS_CSV, index=False, quoting=csv.QUOTE_ALL)
        elapsed = time.time() - start_time
        print(f"\n{'─' * 60}")
        print(f"  ✓ Written: {RESULTS_CSV.relative_to(ROOT)} "
              f"({len(rows)} rows, {df['paper_id'].nunique()} papers)")
        print(f"  Total: {total_fails} fails, {total_uncertain} uncertain, "
              f"{len(rows) - total_fails - total_uncertain} pass")
        print(f"  Elapsed: {elapsed:.0f}s")
    return len(rows)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def generate_summary() -> None:
    """Generate spotcheck_summary.md from results CSV."""
    if not RESULTS_CSV.exists():
        print(f"ERROR: {RESULTS_CSV.relative_to(ROOT)} not found")
        return
    df = pd.read_csv(RESULTS_CSV, dtype=str).fillna("")
    n_papers = df["paper_id"].nunique()
    n_checks = len(df)

    verdicts = df["verdict"].value_counts().to_dict()
    pass_n = verdicts.get("pass", 0)
    fail_n = verdicts.get("fail", 0)
    unc_n = verdicts.get("uncertain", 0)

    lines = [
        f"# Extraction Spot-Check Summary\n",
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"> Model: GPT-5.4 (independent verifier)",
        f"> Extractor: Gemini 3.1 Pro\n",
        f"Papers checked: **{n_papers}**",
        f"Total checks: **{n_checks}** ({n_papers} × {n_checks // n_papers if n_papers else 0} checks/paper)\n",
        f"## Verdict distribution\n",
        f"| Verdict | Count | % |",
        f"|---------|------:|--:|",
    ]
    for v in ["pass", "fail", "uncertain"]:
        c = verdicts.get(v, 0)
        p = c / n_checks * 100 if n_checks else 0
        lines.append(f"| {v} | {c} | {p:.1f}% |")

    # Failures by category
    fails = df[df["verdict"] == "fail"]
    lines.append(f"\n## Failures by check category ({len(fails)} total)\n")
    lines.append(f"| Category | Fails | Top failing check |")
    lines.append(f"|----------|------:|-------------------|")
    for cat in ["A", "B", "C", "D", "E"]:
        cat_fails = fails[fails["check_category"] == cat]
        top = cat_fails["check_id"].value_counts().index[0] if len(cat_fails) > 0 else "-"
        lines.append(f"| {cat} ({CAT_NAMES.get(cat, '')}) | {len(cat_fails)} | {top} |")

    # Failures by RQ
    lines.append(f"\n## Failures by Research Question\n")
    lines.append(f"| RQ | Fail count | Most impacted check |")
    lines.append(f"|----|----------:|---------------------|")
    for rq in ["RQ1", "RQ2", "RQ3"]:
        rq_fails = fails[fails["rq_served"].str.contains(rq, na=False)]
        top = rq_fails["check_id"].value_counts().index[0] if len(rq_fails) > 0 else "-"
        lines.append(f"| {rq} | {len(rq_fails)} | {top} |")

    # Papers needing review
    paper_issues = df[df["verdict"].isin(["fail", "uncertain"])].groupby("paper_id").agg(
        fails=("verdict", lambda x: (x == "fail").sum()),
        uncertain=("verdict", lambda x: (x == "uncertain").sum()),
        title=("title", "first"),
        scis_rank=("scis_rank", "first"),
    ).sort_values(["fails", "uncertain"], ascending=False)

    lines.append(f"\n## Papers needing human review ({len(paper_issues)} papers)\n")
    lines.append(f"| paper_id | SCIS | fails | uncertain | title |")
    lines.append(f"|----------|------|------:|----------:|-------|")
    for pid, r in paper_issues.head(20).iterrows():
        lines.append(f"| {pid} | {r['scis_rank']} | {r['fails']} | {r['uncertain']} | {r['title'][:50]} |")

    lines.append(f"\n## Action items\n")
    lines.append(f"- [ ] Review all {fail_n} 'fail' rows in `spotcheck_results.csv`")
    lines.append(f"- [ ] For each confirmed fail: `python code/extraction.py --paper-id \"<paper_id>\"`")
    lines.append(f"- [ ] Log corrections to `decision_register.csv` with `decision='extraction_spot_check'`")
    lines.append(f"- [ ] Review {unc_n} 'uncertain' rows — open PDF and verify manually")

    md = "\n".join(lines)
    SUMMARY_MD.write_text(md, encoding="utf-8")
    print(f"  Written: {SUMMARY_MD.relative_to(ROOT)}")
    print(f"\n  Pass: {pass_n} ({pass_n/n_checks*100:.1f}%) | "
          f"Fail: {fail_n} ({fail_n/n_checks*100:.1f}%) | "
          f"Uncertain: {unc_n} ({unc_n/n_checks*100:.1f}%)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Independent spot-check of extraction.py output",
    )
    p.add_argument("--limit", type=int, default=None,
                   help="Total papers to sample")
    p.add_argument("--paper-id", type=str, default=None,
                   help="Check one specific paper")
    p.add_argument("--strategy", choices=["stratified", "random"],
                   default="stratified",
                   help="Sampling: stratified (A* oversampled) or random")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for reproducible sampling")
    p.add_argument("--sync", action="store_true",
                   help="Synchronous mode (immediate, 2× cost)")
    p.add_argument("--status", action="store_true",
                   help="Check batch status")
    p.add_argument("--download", action="store_true",
                   help="Download batch results")
    p.add_argument("--summary", action="store_true",
                   help="Generate summary from existing results")
    p.add_argument("--model", type=str, default=DEFAULT_MODEL)
    p.add_argument("--api-key", type=str, default=None)
    p.add_argument("--checks", type=str, default="A,B,C,D,E",
                   help="Check categories to run (comma-separated)")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("  ERP2-SMS Extraction Spot-Check (Independent Audit)")
    print(f"  Verifier: {args.model} | Extractor: Gemini 3.1 Pro")
    print("=" * 70)

    # --- Summary mode ---
    if args.summary:
        generate_summary()
        return 0

    # --- Init OpenAI client ---
    from openai import OpenAI
    api_key = load_openai_api_key(args.api_key)
    client = OpenAI(api_key=api_key)

    # --- Status mode ---
    if args.status:
        check_batch_status(client)
        return 0

    # --- Download mode ---
    if args.download:
        n = download_batch_results(client)
        if n > 0:
            generate_summary()
        return 0

    # --- Sample papers ---
    if not MATRIX_CSV.exists():
        print(f"ERROR: {MATRIX_CSV.relative_to(ROOT)} not found")
        return 1
    matrix = pd.read_csv(MATRIX_CSV, dtype=str).fillna("")
    print(f"  Extracted papers in matrix: {len(matrix)}")

    checks_to_run = [c.strip() for c in args.checks.split(",")]
    active_checks = [c for c in CHECKS if c["cat"] in checks_to_run]
    print(f"  Checks: {len(active_checks)} across categories {args.checks}")

    if args.paper_id:
        sampled = matrix[matrix["paper_id"] == args.paper_id]
        if len(sampled) == 0:
            print(f"ERROR: paper_id '{args.paper_id}' not in extraction_matrix")
            return 1
    else:
        sampled = sample_papers(matrix, args.limit, args.strategy, args.seed)

    print(f"  Papers to check: {len(sampled)}")
    if len(sampled) == 0:
        return 0

    # --- Sync mode ---
    if args.sync:
        print(f"\n  Mode: SYNCHRONOUS (immediate results)\n")
        n = run_sync(client, sampled, args.model, checks_to_run)
        if n > 0:
            generate_summary()
        return 0

    # --- Batch mode ---
    print(f"\n  Mode: BATCH (results in ~1-6 hours, 50% cost discount)\n")
    build_batch_jsonl(sampled, args.model, checks_to_run)
    batch_id = submit_batch(client, args.model)
    print(f"\n  ✓ Batch submitted: {batch_id}")
    print(f"  Next steps:")
    print(f"    python code/extractionspotcheck.py --status      # check progress")
    print(f"    python code/extractionspotcheck.py --download    # fetch results")
    return 0


if __name__ == "__main__":
    sys.exit(main())
