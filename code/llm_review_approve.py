"""Import rater-approved LLM review rows into phase2_decisions.csv.

After `code/llm_review.py` produces `llm_review.csv`, the human rater
opens it in a spreadsheet and marks `approved=True` for each row they
accept (optionally editing decision/criterion/f1/preprint first). This
script copies all approved rows into `phase2_decisions.csv` so they
become part of the formal screening record.

Unapproved rows remain in llm_review.csv for re-review or can be
handled interactively via code/screening_harness.py.

Usage:
    python code/llm_review_approve.py
    python code/llm_review_approve.py --dry-run  # report what would be imported

Consumes:
    artifacts/screening/llm_review.csv (with rater-set approved column)

Produces:
    artifacts/screening/phase2_decisions.csv (appended)
    Appends row to decision_register.csv
"""

import argparse
import csv
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)

LLM_REVIEW_PATH = ROOT / "artifacts" / "screening" / "llm_review.csv"
DECISIONS_PATH = ROOT / "artifacts" / "screening" / "phase2_decisions.csv"

# Schema of phase2_decisions.csv
DECISION_COLUMNS = [
    "paper_id", "doi", "title", "year", "venue", "scis_rank",
    "decision", "criterion", "f1_provisional", "preprint_paper",
    "rationale", "timestamp", "first_decision_timestamp",
    "rater_initials", "session_id", "pass_number",
]


def is_approved(val) -> bool:
    """Treat 'True', 'true', '1', 'yes', 'y' as approved."""
    if val is None or pd.isna(val):
        return False
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "y")


def is_override(val) -> bool:
    """Same logic as approved."""
    return is_approved(val)


def load_llm_reviews(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    return pd.read_csv(path, dtype=str)


def load_decisions(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=DECISION_COLUMNS)
    return pd.read_csv(path, dtype=str)


def build_decision_record(llm_row: pd.Series, session_id: str,
                          rater: str) -> dict:
    """Convert an approved llm_review row to a phase2_decisions row."""
    now = datetime.now(timezone.utc).isoformat()
    # Rationale: keep the LLM rationale but indicate rater override if flagged
    rationale = llm_row.get("rationale", "") or ""
    if is_override(llm_row.get("rater_override")):
        rationale = f"[rater-override] {rationale}"
    return {
        "paper_id":                llm_row.get("paper_id", ""),
        "doi":                     llm_row.get("doi", ""),
        "title":                   llm_row.get("title", ""),
        "year":                    llm_row.get("year", ""),
        "venue":                   llm_row.get("venue", ""),
        "scis_rank":               llm_row.get("scis_rank", ""),
        "decision":                llm_row.get("decision", ""),
        "criterion":               llm_row.get("criterion", ""),
        "f1_provisional":          llm_row.get("f1_provisional", ""),
        "preprint_paper":          llm_row.get("preprint_paper", ""),
        "rationale":               rationale,
        "timestamp":               now,
        "first_decision_timestamp": llm_row.get("timestamp", ""),
        "rater_initials":          rater,
        "session_id":              session_id,
        "pass_number":             "llm-approved",
    }


def append_decision(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists() and path.stat().st_size > 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DECISION_COLUMNS, quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in DECISION_COLUMNS})


def log_to_decision_register(imported: int, overridden: int,
                              skipped: int) -> None:
    """Record the import to the decision register."""
    register_path = ROOT / "decision_register.csv"
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "2",
        "paper_id": "N/A",
        "decision": "llm_reviews_approved",
        "rule_applied": "Task 2.5 §16 (LLM-assisted screening workflow)",
        "rationale": (
            f"Imported {imported} LLM-reviewed papers into "
            f"phase2_decisions.csv. Of these, {overridden} had rater "
            f"overrides. {skipped} llm_review rows were not approved "
            f"and remain for re-review or harness handling."
        ),
        "rater_initials": os.environ.get("RATER_INITIALS", "AT"),
    }
    with open(register_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import approved LLM reviews into phase2_decisions.csv",
    )
    parser.add_argument("--input", type=Path, default=LLM_REVIEW_PATH,
                        help=f"LLM review CSV (default: {LLM_REVIEW_PATH.relative_to(ROOT)})")
    parser.add_argument("--output", type=Path, default=DECISIONS_PATH,
                        help=f"phase2_decisions.csv path (default: {DECISIONS_PATH.relative_to(ROOT)})")
    parser.add_argument("--dry-run", action="store_true", default=False,
                        help="Show what would be imported without writing")
    parser.add_argument("--rater", type=str,
                        default=os.environ.get("RATER_INITIALS", "AT"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    llm = load_llm_reviews(args.input)
    existing = load_decisions(args.output)
    already_decided = set(existing["paper_id"].astype(str)) if len(existing) > 0 else set()

    # Filter rows
    approved_mask = llm["approved"].apply(is_approved)
    approved = llm[approved_mask]
    not_approved = llm[~approved_mask]

    # Drop any already-decided papers
    new_rows = approved[~approved["paper_id"].astype(str).isin(already_decided)]
    already = approved[approved["paper_id"].astype(str).isin(already_decided)]

    # Report
    print(f"LLM review rows:         {len(llm)}")
    print(f"Marked approved:         {len(approved)}")
    print(f"Not approved (skipped):  {len(not_approved)}")
    print(f"Already in decisions:    {len(already)}")
    print(f"To import:               {len(new_rows)}")
    override_count = int(new_rows["rater_override"].apply(is_override).sum()) if len(new_rows) > 0 else 0
    print(f"Of which rater-overrode: {override_count}")

    # Distribution
    if len(new_rows) > 0:
        print("\nDecision distribution (to import):")
        for d, c in new_rows["decision"].value_counts().items():
            print(f"  {d}: {c}")

    if args.dry_run:
        print("\n[dry-run] No changes written.")
        return

    if len(new_rows) == 0:
        print("\nNothing to import.")
        return

    # Write
    session_id = str(uuid.uuid4())[:8]
    for _, row in new_rows.iterrows():
        record = build_decision_record(row, session_id, args.rater)
        append_decision(args.output, record)

    # Log
    log_to_decision_register(len(new_rows), override_count, len(not_approved))

    print(f"\n✓ Imported {len(new_rows)} rows into {args.output.relative_to(ROOT)}")
    print(f"  Session ID: {session_id}")
    print(f"  {len(not_approved)} unapproved rows remain in llm_review.csv for "
          f"re-review or interactive screening.")


if __name__ == "__main__":
    main()
