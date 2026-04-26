"""LLM-based first-pass screening for Task 2.5.

Runs an LLM (default: OpenAI gpt-4o-mini) over each post-filtered paper
and generates a screening decision + criterion + F1 class + preprint flag.
Outputs a CSV that the human rater reviews in a spreadsheet, approves
(or overrides) each row, and then exports approved rows into
phase2_decisions.csv via code/llm_review_approve.py (or manual copy).

Why GPT-4o-mini: cheapest capable model (~$0.15/$0.60 per MTok in/out).
Full 4093-paper run costs ≈$0.50-$1.00. Claude Haiku 4.5 available as
an alternative (--model claude-haiku-4-5) at ~8x the cost.

Usage:
    python code/llm_review.py
    python code/llm_review.py --model gpt-4o-mini --max-papers 100
    python code/llm_review.py --resume

Consumes:
    artifacts/search/post_filtered.csv
    artifacts/protocol/inclusion_exclusion.md
    artifacts/protocol/codebook.md (F1 definitions)
    .env (OPENAI_API_KEY)

Produces:
    artifacts/screening/llm_review.csv (one row per paper)
    artifacts/screening/llm_review.csv.meta.json
    Appends row to decision_register.csv
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_INPUT = ROOT / "artifacts" / "search" / "post_filtered.csv"
OUTPUT_PATH = ROOT / "artifacts" / "screening" / "llm_review.csv"
CODEBOOK_PATH = ROOT / "artifacts" / "protocol" / "codebook.md"
IE_PATH = ROOT / "artifacts" / "protocol" / "inclusion_exclusion.md"

# --- Model pricing table (USD per million tokens) ---
# Update as providers change pricing.
MODEL_PRICING = {
    # OpenAI
    "gpt-4o-mini":   {"input": 0.15, "output": 0.60, "provider": "openai"},
    "gpt-5-mini":    {"input": 0.25, "output": 2.00, "provider": "openai"},
    "gpt-4o":        {"input": 2.50, "output": 10.00, "provider": "openai"},
}

# --- Output columns ---
# 'abstract' is included immediately after title so the rater can review
# decision + context without cross-referencing post_filtered.csv.
OUTPUT_COLUMNS = [
    "paper_id", "doi", "title", "abstract", "year", "venue", "scis_rank",
    "decision", "criterion", "f1_provisional", "preprint_paper",
    "rationale",       # LLM-generated, rater may edit
    "llm_reasoning",   # LLM's internal reasoning (for audit)
    "llm_model",
    "llm_tokens_input",
    "llm_tokens_output",
    "llm_cost_usd",
    "timestamp",
    "approved",         # Rater sets True after review
    "rater_override",   # True if rater changed LLM decision during review
]

# --- Progress / rate limiting ---
REQUEST_DELAY = 0.2       # seconds between requests
MAX_RETRIES = 3
BACKOFF_BASE = 2
SUMMARY_EVERY = 25        # summary banner interval (per-paper line is always printed)

# --- ANSI colour codes for per-paper status line ---
COLOUR_RESET  = "\033[0m"
COLOUR_GREEN  = "\033[32m"   # include
COLOUR_RED    = "\033[31m"   # exclude
COLOUR_YELLOW = "\033[33m"   # defer
COLOUR_DIM    = "\033[2m"


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_system_prompt(codebook_excerpt: str, ie_excerpt: str) -> str:
    """Assemble the system prompt for the LLM.

    Includes the codebook F1 definitions and the IC/EC criteria so the
    LLM has all context needed to classify a paper deterministically.
    """
    return f"""You are a research assistant for a Systematic Mapping Study (SMS)
on "How Do People Use AI Agents for Software Engineering?".

Your job is to classify a candidate paper based on title and abstract.
You must apply the inclusion/exclusion criteria below and provide a
provisional Wieringa F1 class.

---
INCLUSION / EXCLUSION CRITERIA:
{ie_excerpt}

---
F1 WIERINGA CLASSES (provisional):
{codebook_excerpt}

---
DECISION RULES:
1. If the paper clearly satisfies all IC and no EC apply → decision = "include"
2. If any EC clearly applies → decision = "exclude" with the matching criterion (EC1..EC6)
3. If ambiguous (could be either, or abstract is insufficient) → decision = "defer"

F1 AUTO-FILL RULES:
- EC1 (Solution Proposal only) → f1_provisional = "Solution Proposal"
- EC2 (Validation Research / benchmark) → f1_provisional = "Validation Research"
- For include / EC3–EC6: choose one of {{Evaluation Research, Validation Research,
  Solution Proposal, Philosophical, Opinion, Personal Experience}}
- For defer: pick best-guess F1 class if possible, else omit

PREPRINT_PAPER:
- "preprint" if paper is only on arXiv or a preprint server (no formal publication)
- "published" if the venue is a real peer-reviewed journal/conference
- "mixed" if it's a published paper with an accompanying arXiv preprint
- "unknown" if ambiguous

RESPONSE FORMAT (strict JSON, no extra text):
{{
  "decision":        "include" | "exclude" | "defer",
  "criterion":       "EC1" | "EC2" | ... | "EC6" | null,
  "f1_provisional":  "Evaluation Research" | "Validation Research" | ... | null,
  "preprint_paper":  "preprint" | "published" | "mixed" | "unknown",
  "rationale":       "<one-sentence justification for the rater>",
  "llm_reasoning":   "<2-3 sentences of internal reasoning for audit>"
}}

Be conservative: if in doubt, prefer "defer" over forcing an include/exclude.
"""


def build_user_message(row: pd.Series) -> str:
    """Format the paper info for the LLM user message."""
    title = str(row.get("title", "")).strip()
    abstract = str(row.get("abstract", "")).strip() or "(no abstract available)"
    venue = str(row.get("source", "")).strip()
    year = str(row.get("year", "")).strip()
    scis_rank = str(row.get("scis_rank", "")).strip()
    doi = str(row.get("doi", "")).strip()

    # Flags
    flags = []
    if str(row.get("preprint_flag", "")).lower() in ("true", "1"):
        flags.append("preprint_flag=True (OpenAlex says submittedVersion)")
    if pd.notna(row.get("ic3_flag")) and str(row.get("ic3_flag")).strip():
        flags.append("IC3 mismatch (Scopus=journal/conf, OpenAlex=repository)")
    if str(row.get("retracted_flag", "")).lower() in ("true", "1"):
        flags.append("retracted")
    if str(row.get("paratext_flag", "")).lower() in ("true", "1"):
        flags.append("paratext (editorial/front-matter)")
    flag_str = "; ".join(flags) if flags else "(none)"

    return f"""Paper to classify:

TITLE: {title}

ABSTRACT: {abstract}

VENUE: {venue}
YEAR: {year}
DOI: {doi}
SCIS rank: {scis_rank}
Enrichment flags: {flag_str}

Classify this paper per the criteria. Return strict JSON only."""


# ---------------------------------------------------------------------------
# LLM Call (OpenAI)
# ---------------------------------------------------------------------------

def _clean_key(raw: str) -> str:
    """Strip whitespace and any surrounding quotes from an env-file value."""
    s = raw.strip()
    # Strip matched surrounding quotes (single or double)
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1]
    return s.strip()


def load_api_key(cli_override: str | None = None) -> tuple[str, str]:
    """Load OPENAI_API_KEY; return (key, source_label).

    Priority (first match wins):
      1. --api-key CLI override
      2. .env file in project root  ← preferred; project-specific source of truth
      3. OPENAI_API_KEY shell environment variable  ← last-resort fallback

    Why .env before shell env var: the shell env var is commonly stale
    (users forget they `export`ed an old key in their shell rc). The
    .env file is the project's authoritative config.

    Strips surrounding quotes and whitespace from the loaded value.
    """
    if cli_override:
        return _clean_key(cli_override), "--api-key CLI flag"

    # Prefer .env file over env var — prevents stale-shell-var issues
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY=") and len(line) > len("OPENAI_API_KEY="):
                val = line.split("=", 1)[1]
                return _clean_key(val), f".env ({env_path.relative_to(ROOT)})"

    # Fallback to shell env var
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return _clean_key(env_key), "OPENAI_API_KEY env var"

    print("ERROR: OPENAI_API_KEY not found in --api-key, .env, or env var",
          file=sys.stderr)
    print("Set it in .env: OPENAI_API_KEY=sk-...", file=sys.stderr)
    sys.exit(1)


def validate_api_key(key: str) -> None:
    """Sanity-check key format before spending attempts on API calls."""
    if not key:
        print("ERROR: OPENAI_API_KEY is empty", file=sys.stderr)
        sys.exit(1)
    if not (key.startswith("sk-") or key.startswith("sess-")):
        print(f"ERROR: OPENAI_API_KEY looks malformed "
              f"(got {len(key)} chars starting with '{key[:8]}...')",
              file=sys.stderr)
        print("Expected format: sk-... or sk-proj-...", file=sys.stderr)
        sys.exit(1)


def call_openai(client, model: str, system_prompt: str,
                user_message: str) -> tuple[dict, dict]:
    """Call OpenAI chat completions. Returns (parsed_json, usage_stats).

    Fails fast on authentication/permission errors (retrying doesn't help).
    Retries only on transient errors (rate limit, server error, network).
    """
    # Import specific exception types for targeted handling
    from openai import (
        AuthenticationError,
        PermissionDeniedError,
        NotFoundError,
        BadRequestError,
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        InternalServerError,
    )

    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,   # deterministic for reproducibility
                max_tokens=600,
            )
            content = resp.choices[0].message.content
            usage = {
                "input_tokens": resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            }
            try:
                parsed = json.loads(content)
                return parsed, usage
            except json.JSONDecodeError as e:
                print(f"  [WARN] JSON parse error: {e} — raw: {content[:200]}")
                return {"decision": "defer", "rationale": f"JSON parse error: {e}",
                        "llm_reasoning": content[:500]}, usage

        # --- Fatal errors (do NOT retry — bail immediately) ---
        except AuthenticationError as e:
            print(f"\n[FATAL] OpenAI authentication failed (401).", file=sys.stderr)
            print(f"  Your API key was rejected. Check that:", file=sys.stderr)
            print(f"  1. OPENAI_API_KEY in .env has NO surrounding quotes", file=sys.stderr)
            print(f"  2. The key has NO trailing whitespace or newline characters", file=sys.stderr)
            print(f"  3. The key is active at https://platform.openai.com/api-keys", file=sys.stderr)
            print(f"  4. The key has access to the selected model", file=sys.stderr)
            print(f"  Underlying error: {e}", file=sys.stderr)
            sys.exit(1)
        except PermissionDeniedError as e:
            print(f"\n[FATAL] OpenAI permission denied (403). "
                  f"Key lacks access to model '{model}'. Try --model gpt-4o-mini.",
                  file=sys.stderr)
            sys.exit(1)
        except NotFoundError as e:
            print(f"\n[FATAL] Model '{model}' not found (404). "
                  f"Check --model value.", file=sys.stderr)
            sys.exit(1)
        except BadRequestError as e:
            print(f"\n[FATAL] Bad request (400): {e}", file=sys.stderr)
            sys.exit(1)

        # --- Transient errors (retry with backoff) ---
        except RateLimitError as e:
            wait = BACKOFF_BASE ** attempt * 2  # longer wait for rate limit
            print(f"  [WARN] Rate limit ({type(e).__name__}). "
                  f"Retry {attempt+1}/{MAX_RETRIES} in {wait}s...")
            time.sleep(wait)
        except (APITimeoutError, APIConnectionError, InternalServerError) as e:
            wait = BACKOFF_BASE ** attempt
            print(f"  [WARN] Transient error ({type(e).__name__}): {e}. "
                  f"Retry {attempt+1}/{MAX_RETRIES} in {wait}s...")
            time.sleep(wait)
        except Exception as e:
            # Unknown error — retry once, then give up
            wait = BACKOFF_BASE ** attempt
            print(f"  [WARN] Unexpected error ({type(e).__name__}): {e}. "
                  f"Retry {attempt+1}/{MAX_RETRIES} in {wait}s...")
            time.sleep(wait)

    raise RuntimeError(f"All {MAX_RETRIES} retries exhausted")


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return USD cost for a single request."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0
    return (input_tokens / 1_000_000) * pricing["input"] + \
           (output_tokens / 1_000_000) * pricing["output"]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def load_codebook_excerpt() -> str:
    """Extract F1 section from codebook.md."""
    text = CODEBOOK_PATH.read_text(encoding="utf-8")
    # Grab F1 section
    start = text.find("## F1")
    end = text.find("## F2")
    if start == -1 or end == -1:
        return text[:3000]  # fallback
    return text[start:end].strip()


def load_ie_excerpt() -> str:
    """Load the entire inclusion_exclusion.md as context."""
    return IE_PATH.read_text(encoding="utf-8").strip()


def compute_paper_id(row: pd.Series) -> str:
    """Compute paper_id from dedup_group or DOI."""
    group = row.get("dedup_group")
    if pd.notna(group) and str(group).strip():
        return str(group)
    doi = row.get("doi")
    if pd.notna(doi) and str(doi).strip():
        return f"doi:{str(doi).strip().lower()}"
    import hashlib
    title = str(row.get("title", "")).strip()
    return f"hash:{hashlib.md5(title.encode('utf-8')).hexdigest()[:12]}"


def load_input(path: Path) -> pd.DataFrame:
    """Load post_filtered.csv and filter ic5_status=fail rows."""
    if not path.exists():
        print(f"ERROR: Input not found: {path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(path, dtype=str)
    return df[df["ic5_status"] != "fail"].copy().reset_index(drop=True)


def load_existing_reviews(path: Path) -> set:
    """Load set of paper_ids already processed (for --resume).

    If the existing file's schema differs from OUTPUT_COLUMNS (e.g., we
    added a column in a later version), migrate it by reading + re-writing
    with the new schema. Missing columns are filled with empty strings.
    """
    if not path.exists():
        return set()
    df = pd.read_csv(path, dtype=str)

    # Detect and migrate schema drift
    existing_cols = list(df.columns)
    if existing_cols != OUTPUT_COLUMNS:
        missing = [c for c in OUTPUT_COLUMNS if c not in existing_cols]
        extra = [c for c in existing_cols if c not in OUTPUT_COLUMNS]
        print(f"  [INFO] Existing {path.name} has older schema; migrating in place.")
        if missing:
            print(f"         Adding columns: {missing}")
            for c in missing:
                df[c] = ""
        if extra:
            print(f"         Dropping columns: {extra}")
            df = df.drop(columns=extra)
        # Reorder to match OUTPUT_COLUMNS
        df = df[OUTPUT_COLUMNS]
        df.to_csv(path, index=False, quoting=csv.QUOTE_ALL)
        print(f"         Migration complete — {len(df)} rows preserved.")

    return set(df["paper_id"].astype(str))


def append_review(path: Path, record: dict) -> None:
    """Atomically append a review row to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists() and path.stat().st_size > 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in OUTPUT_COLUMNS})


def log_to_decision_register(stats: dict, output_path: Path) -> None:
    """Append llm_review_executed row to decision_register.csv."""
    register_path = ROOT / "decision_register.csv"
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "2",
        "paper_id": "N/A",
        "decision": "llm_review_executed",
        "rule_applied": "Single-rater + LLM assist (Task 2.5 §16)",
        "rationale": (
            f"LLM review: {stats['processed']}/{stats['total']} papers "
            f"classified by {stats['model']}. "
            f"Decisions: include={stats['include']}, exclude={stats['exclude']}, "
            f"defer={stats['defer']}. "
            f"Total tokens: {stats['tokens_in']} in, {stats['tokens_out']} out. "
            f"Total cost: ${stats['cost_usd']:.4f}. "
            f"Output: {output_path.relative_to(ROOT)}. "
            f"Rater will review each row and set approved=True before importing."
        ),
        "rater_initials": os.environ.get("RATER_INITIALS", "AT"),
    }
    with open(register_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LLM-based first-pass screening (Task 2.5)",
        epilog="After this runs, open artifacts/screening/llm_review.csv "
               "in a spreadsheet, review each row, set approved=True, "
               "then use code/llm_review_approve.py to import into "
               "phase2_decisions.csv.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        choices=list(MODEL_PRICING.keys()),
                        help="LLM model (default: gpt-4o-mini)")
    parser.add_argument("--api-key", type=str, default=None,
                        help="OpenAI API key (default: reads from .env)")
    parser.add_argument("--max-papers", type=int, default=None,
                        help="Max papers to process this run")
    parser.add_argument("--resume", action="store_true", default=True,
                        help="Skip papers already in output CSV (default: True)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    output_path = args.output.resolve()
    input_path = args.input.resolve()

    # Load and validate API key
    api_key, key_source = load_api_key(args.api_key)
    validate_api_key(api_key)
    print(f"Loaded API key ({len(api_key)} chars, prefix '{api_key[:8]}...', "
          f"suffix '...{api_key[-5:]}') from {key_source}")

    # Instantiate client
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    # Load inputs
    print(f"Loading {input_path}...")
    df = load_input(input_path)
    print(f"  {len(df)} candidate rows (ic5_status != fail)")

    # Resume: skip already-processed
    df["_paper_id"] = df.apply(compute_paper_id, axis=1)
    total_candidates = len(df)
    done: set[str] = set()

    if output_path.exists():
        if args.resume:
            done = load_existing_reviews(output_path)
            df = df[~df["_paper_id"].isin(done)].reset_index(drop=True)
        else:
            # --no-resume explicitly requested — warn before overwriting work
            print(f"  [WARN] --no-resume: existing {output_path.name} will be ignored "
                  f"but NOT deleted. You may end up with duplicate rows.")

    # Prominent resume-status banner
    print()
    print("=" * 60)
    print("  Resume status")
    print("=" * 60)
    print(f"  Output file:         {output_path.relative_to(ROOT)}")
    print(f"  Total candidates:    {total_candidates}")
    print(f"  Already processed:   {len(done)} "
          f"({len(done)/total_candidates*100:.1f}%)" if total_candidates else "  Already processed:   0")
    print(f"  Remaining this run:  {len(df)}")
    if args.resume and output_path.exists() and len(done) > 0:
        print(f"  Resumed from:        {output_path.name} (--resume ON, default)")
    print("=" * 60)
    print()

    if args.max_papers:
        df = df.head(args.max_papers)
        print(f"Capped at --max-papers {args.max_papers}")
        print()

    if len(df) == 0:
        print("[green]✓ Nothing to do — all candidates already processed.[/green]")
        print(f"Review the existing {output_path.name} and run code/llm_review_approve.py "
              f"when ready.")
        return

    # Load codebook + I/E criteria for system prompt
    print("Loading codebook and I/E criteria...")
    codebook_excerpt = load_codebook_excerpt()
    ie_excerpt = load_ie_excerpt()
    system_prompt = build_system_prompt(codebook_excerpt, ie_excerpt)
    print(f"  System prompt: {len(system_prompt)} chars")

    # Cost estimate
    pricing = MODEL_PRICING[args.model]
    est_tokens_per_paper = len(system_prompt) // 4 + 500  # rough: chars / 4
    est_cost_per_paper = (est_tokens_per_paper / 1_000_000) * pricing["input"] + \
                         (300 / 1_000_000) * pricing["output"]
    est_total = est_cost_per_paper * len(df)
    print(f"\n  Model: {args.model}")
    print(f"  Pricing: ${pricing['input']}/MTok in, ${pricing['output']}/MTok out")
    print(f"  Estimated cost: ${est_cost_per_paper:.4f}/paper × {len(df)} = ${est_total:.2f}")
    print()

    # Process loop
    stats = {
        "processed": 0, "include": 0, "exclude": 0, "defer": 0,
        "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
        "total": len(df), "model": args.model,
    }
    start_time = time.time()

    # Global position counter (includes previously-done papers for continuity)
    already_done_count = len(done)

    for i, row in df.iterrows():
        paper_id = row["_paper_id"]

        # Delay between calls (respect rate limits)
        if stats["processed"] > 0:
            time.sleep(REQUEST_DELAY)

        # Build user message
        user_msg = build_user_message(row)

        # Call LLM (fatal errors sys.exit inside; only transient retries return here)
        try:
            parsed, usage = call_openai(client, args.model, system_prompt, user_msg)
        except Exception as e:
            # Transient retry limit exhausted — log and skip this paper
            print(f"  [ERROR] {paper_id}: {e}")
            continue

        # Compute cost
        cost = compute_cost(args.model, usage["input_tokens"], usage["output_tokens"])

        # Build record
        decision = parsed.get("decision", "defer")
        record = {
            "paper_id": paper_id,
            "doi": str(row.get("doi", "")).strip(),
            "title": str(row.get("title", "")).strip(),
            "abstract": str(row.get("abstract", "")).strip(),
            "year": str(row.get("year", "")).strip(),
            "venue": str(row.get("source", "")).strip(),
            "scis_rank": str(row.get("scis_rank", "")).strip(),
            "decision": decision,
            "criterion": parsed.get("criterion") or "",
            "f1_provisional": parsed.get("f1_provisional") or "",
            "preprint_paper": parsed.get("preprint_paper") or "unknown",
            "rationale": f"[LLM-reviewed] {parsed.get('rationale', '')}",
            "llm_reasoning": parsed.get("llm_reasoning", ""),
            "llm_model": args.model,
            "llm_tokens_input": usage["input_tokens"],
            "llm_tokens_output": usage["output_tokens"],
            "llm_cost_usd": f"{cost:.6f}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "approved": "",           # rater sets later
            "rater_override": "",     # rater sets later
        }
        # Append IMMEDIATELY so the work is saved if the run is killed
        append_review(output_path, record)

        # Update stats
        stats["processed"] += 1
        if decision in ("include", "exclude", "defer"):
            stats[decision] += 1
        stats["tokens_in"] += usage["input_tokens"]
        stats["tokens_out"] += usage["output_tokens"]
        stats["cost_usd"] += cost

        # --- Per-paper status line (printed on EVERY paper) ---
        sym = {"include": "✓", "exclude": "✗", "defer": "?"}.get(decision, "!")
        col = {"include": COLOUR_GREEN, "exclude": COLOUR_RED,
               "defer": COLOUR_YELLOW}.get(decision, "")
        crit = (parsed.get("criterion") or "-")[:4]
        f1 = (parsed.get("f1_provisional") or "-")[:22]
        title_short = str(row.get("title", ""))[:60]
        position = already_done_count + stats["processed"]
        print(f"  [{position:4d}/{total_candidates}] "
              f"{col}{sym} {decision:<8s}{COLOUR_RESET} "
              f"{crit:<4s} F1={f1:<22s} "
              f"| {COLOUR_DIM}{title_short}{COLOUR_RESET}")

        # --- Summary banner (every SUMMARY_EVERY papers + final) ---
        if stats["processed"] % SUMMARY_EVERY == 0 or \
           stats["processed"] == len(df):
            elapsed = time.time() - start_time
            rate = stats["processed"] / elapsed if elapsed > 0 else 0
            remaining_session = (len(df) - stats["processed"]) / rate if rate > 0 else 0
            total_remaining = total_candidates - position
            print()
            print(f"  {'─' * 60}")
            print(f"  ▶ Session: {stats['processed']}/{len(df)} "
                  f"(overall {position}/{total_candidates}) | "
                  f"inc={stats['include']} exc={stats['exclude']} "
                  f"def={stats['defer']}")
            print(f"  ▶ Cost:    ${stats['cost_usd']:.4f}  |  "
                  f"Tokens: {stats['tokens_in']:,} in / "
                  f"{stats['tokens_out']:,} out")
            print(f"  ▶ Rate:    {rate*60:.1f}/min  |  "
                  f"ETA session: {remaining_session/60:.1f} min")
            if total_remaining > stats["processed"]:
                est_total_min = total_remaining / rate / 60 if rate > 0 else 0
                est_total_cost = stats["cost_usd"] * total_candidates / stats["processed"] \
                                 if stats["processed"] > 0 else 0
                print(f"  ▶ Overall: ~{est_total_min:.0f} min remaining for full corpus  "
                      f"| est. total cost ${est_total_cost:.2f}")
            print(f"  {'─' * 60}")
            print()

    # Write meta
    write_with_meta(
        target_path=output_path,
        script="code/llm_review.py",
        inputs=[str(input_path.relative_to(ROOT)),
                str(CODEBOOK_PATH.relative_to(ROOT)),
                str(IE_PATH.relative_to(ROOT))],
        seed=0,  # LLM temperature=0 but API is not truly deterministic
    )
    # Extend meta with LLM run stats
    meta_path = output_path.with_suffix(output_path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["llm_run_stats"] = {
        "model":              args.model,
        "papers_processed":   stats["processed"],
        "decisions": {
            "include": stats["include"],
            "exclude": stats["exclude"],
            "defer":   stats["defer"],
        },
        "tokens_input":       stats["tokens_in"],
        "tokens_output":      stats["tokens_out"],
        "cost_usd":           round(stats["cost_usd"], 6),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    # Log to decision register
    log_to_decision_register(stats, output_path)

    # Final summary
    print()
    print("=" * 60)
    print("  LLM Review Summary")
    print("=" * 60)
    print(f"  Papers processed: {stats['processed']} / {len(df)}")
    print(f"  include: {stats['include']}  exclude: {stats['exclude']}  defer: {stats['defer']}")
    print(f"  Total tokens: {stats['tokens_in']} in, {stats['tokens_out']} out")
    print(f"  Total cost:   ${stats['cost_usd']:.4f}")
    print(f"  Output:       {output_path}")
    print()
    print("  NEXT STEPS:")
    print("  1. Open llm_review.csv in a spreadsheet")
    print("  2. Review each row's decision, criterion, f1_provisional, preprint_paper")
    print("  3. Edit as needed; set approved=True for rows you accept")
    print("  4. Save the CSV")
    print("  5. Run: python code/llm_review_approve.py")


if __name__ == "__main__":
    main()
