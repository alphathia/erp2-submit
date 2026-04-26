"""Task 4.2 Step 4 — Interactive canonical-label → interaction-mode classifier.

Purpose:
    Rater bulk-classifies the ~666 canonical labels not already placed
    via the Step-3 top-40 strawman review. Five modes + Residuals/Cross-
    cutting + Defer, with inline mode definitions and passage preview.

Input:
    artifacts/synthesis/consolidated_codes.csv
    artifacts/synthesis/interaction_taxonomy.md   (to skip Step-3 placements)
    artifacts/extraction/raw_passages/*.md        (for [v]iew preview)

Output:
    artifacts/synthesis/taxonomy_classifications.csv
    artifacts/synthesis/.taxonomy_classify_state.json   (resumable)

Usage:
    python code/taxonomy_classify.py                     # fresh run
    python code/taxonomy_classify.py --resume            # continue prior session
    python code/taxonomy_classify.py --rater TBS         # override rater id
    python code/taxonomy_classify.py --stats             # print current tally
    python code/taxonomy_classify.py --verify            # DoD: partition check
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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.retrieval import safe_paper_id_to_filename  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SYNTH_DIR       = ROOT / "artifacts" / "synthesis"
CONSOLIDATED_CSV = SYNTH_DIR / "consolidated_codes.csv"
TAXONOMY_MD     = SYNTH_DIR / "interaction_taxonomy.md"
PASSAGES_DIR    = ROOT / "artifacts" / "extraction" / "raw_passages"
CLASSIFY_CSV    = SYNTH_DIR / "taxonomy_classifications.csv"
STATE_JSON      = SYNTH_DIR / ".taxonomy_classify_state.json"

# ---------------------------------------------------------------------------
# Mode definitions — MIRROR interaction_taxonomy.md §Mode N
# (Kept concise for inline display; the full operational definitions live
# in the taxonomy markdown and are rewritten at Step 5.)
# ---------------------------------------------------------------------------
MODES: list[dict] = [
    {"key": "1", "name": "Inline Completion",
     "gloss": "Human authors code; AI produces short inline continuations; "
              "accept/reject per-token — no conversational turn."},
    {"key": "2", "name": "Conversational Prompting",
     "gloss": "Human describes intent in natural language; AI responds per "
              "turn; human iterates. Unit = prompt-response turn."},
    {"key": "3", "name": "Visual / Declarative Composition",
     "gloss": "Human composes via visual/declarative surface (drag-drop, "
              "forms, workflow nodes); AI generates underlying logic. "
              "Low-code / no-code signal."},
    {"key": "4", "name": "Review & Validation",
     "gloss": "Evaluative reading of code or AI output — hallucination "
              "detection, quality assessment, feedback, trust/security."},
    {"key": "5", "name": "Delegated Task Execution",
     "gloss": "AI takes multi-step initiative — generates full artefacts, "
              "walks debugging sessions, orchestrates workflows. Human "
              "steers at boundaries, not per-token. Folds HITL Delegation + "
              "Autonomous Orchestration (may re-split at Step 6)."},
    {"key": "r", "name": "Residuals / Cross-cutting",
     "gloss": "Outcome, affordance, constraint, or surface that cuts "
              "across modes — not a mode itself. E.g., productivity, "
              "accuracy, tooling integration, cognitive load."},
    {"key": "?", "name": "Defer to Step 6",
     "gloss": "Ambiguous; re-surface later when passages can be read."},
]
MODE_KEYS = {m["key"] for m in MODES}


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def passage_md_filename(paper_id: str) -> str:
    return safe_paper_id_to_filename(paper_id).replace(".pdf", ".md")


# ---------------------------------------------------------------------------
# Load inputs
# ---------------------------------------------------------------------------
def load_labels() -> pd.DataFrame:
    if not CONSOLIDATED_CSV.exists():
        raise FileNotFoundError(
            f"{CONSOLIDATED_CSV} not found — run Task 4.1 first.")
    df = pd.read_csv(CONSOLIDATED_CSV, dtype=str).fillna("")
    df["cluster_size"] = df["cluster_size"].astype(int)
    return df


# Regex patterns pull Step-3 placements from the taxonomy markdown.
# Each Mode section begins `## Mode N — <name>`; every placement row is
# `| … | <Canonical label> | <size> | … | …`. We scan by mode header and
# collect canonical labels in the following table, stopping at the next
# `---` or `## ` heading.
MODE_HEADER_RE = re.compile(r"^##\s+Mode\s+(\d+)\s+—\s+(.+?)\s*$", re.M)
RESIDUAL_HEADER_RE = re.compile(r"^##\s+Residuals\s*/\s*Cross-Cutting",
                                re.M | re.I)
# Third column is size — tolerate markdown emphasis like **16** and "14 ".
TABLE_ROW_RE = re.compile(r"^\|[^|]*\|\s*([^|]+?)\s*\|\s*[\d*\s]+\|",
                          re.M)


def labels_placed_in_taxonomy() -> dict[str, str]:
    """Return {canonical_label: mode_key} for every row already placed
    in interaction_taxonomy.md (Step-3 strawman + rater edits)."""
    if not TAXONOMY_MD.exists():
        return {}
    text = TAXONOMY_MD.read_text(encoding="utf-8")
    placed: dict[str, str] = {}
    # Slice the document at each top-level section header
    splits: list[tuple[int, str]] = []  # (char_offset, tag)
    for m in MODE_HEADER_RE.finditer(text):
        splits.append((m.start(), m.group(1)))  # tag = mode number
    for m in RESIDUAL_HEADER_RE.finditer(text):
        splits.append((m.start(), "r"))
    splits.sort()
    splits.append((len(text), None))  # sentinel
    for i in range(len(splits) - 1):
        start, tag = splits[i]
        end, _ = splits[i + 1]
        if tag is None:
            continue
        section = text[start:end]
        for row_match in TABLE_ROW_RE.finditer(section):
            label = row_match.group(1).strip()
            # Skip table headers ("Canonical label")
            if label.lower().startswith("canonical"):
                continue
            placed.setdefault(label, tag)
    return placed


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------
def load_state() -> dict | None:
    if not STATE_JSON.exists():
        return None
    try:
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[warn] state file unreadable: {exc}", file=sys.stderr)
        return None


def save_state(state: dict) -> None:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(STATE_JSON)


def initial_state(labels: pd.DataFrame, placed: dict[str, str],
                  rater: str) -> dict:
    rows: list[dict] = []
    for _, r in labels.iterrows():
        lbl = r["canonical_label"]
        placed_key = placed.get(lbl)
        row = {
            "canonical_label": lbl,
            "cluster_size": int(r["cluster_size"]),
            "pass1_codes": r["pass1_codes"],
            "passage_ids": r["passage_ids"],
            "mode": placed_key or "",
            "source": "step3" if placed_key else "",
            "confirmed_by": "TBS-step3" if placed_key else "",
            "confirmed_at": utcnow_iso() if placed_key else "",
            "notes": "",
        }
        rows.append(row)
    return {
        "schema_version": 1,
        "started_at": utcnow_iso(),
        "rater": rater,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Passage preview
# ---------------------------------------------------------------------------
def find_passage_text(paper_id: str, passage_id: str) -> str:
    fp = PASSAGES_DIR / passage_md_filename(paper_id)
    if not fp.exists():
        return ""
    text = fp.read_text(encoding="utf-8", errors="ignore")
    marker = f"## {passage_id}"
    if marker not in text:
        return ""
    chunk = text.split(marker, 1)[1]
    nxt = chunk.find("\n## P")
    body = chunk[:nxt] if nxt != -1 else chunk
    return body.strip()


def view_passages(row: dict) -> None:
    try:
        pids = json.loads(row["passage_ids"]) if row["passage_ids"] else []
    except json.JSONDecodeError:
        pids = []
    if not pids:
        print("  (no passage_ids on this label)")
        return
    shown = 0
    for pid in pids[:3]:
        parts = pid.rsplit(":", 1)
        if len(parts) != 2:
            continue
        paper_id, passage_id = parts
        text = find_passage_text(paper_id, passage_id)
        print(f"\n  [{pid}]")
        if text:
            print(f"    {text[:500]}")
        else:
            print("    (passage not found in raw_passages/)")
        shown += 1
    if shown == 0:
        print("  (no passages available)")


# ---------------------------------------------------------------------------
# Interactive loop
# ---------------------------------------------------------------------------
def print_menu() -> None:
    print()
    print("=" * 78)
    print("  MODE MENU — press the key then Enter")
    print("=" * 78)
    for m in MODES:
        print(f"  [{m['key']}] {m['name']:<40} {m['gloss'][:70]}")
    print(f"  [v] view passage(s)   [s] stats   [q] quit (state saved)")
    print("=" * 78)


def prompt_label(row: dict, idx: int, total: int) -> str | None:
    """Return mode key or None if user quit."""
    try:
        members = json.loads(row["pass1_codes"])
    except json.JSONDecodeError:
        members = []
    print()
    print("-" * 78)
    print(f"[{idx}/{total}]  size={row['cluster_size']}  "
          f"label: \"{row['canonical_label']}\"")
    print("-" * 78)
    print("Member pass-1 codes:")
    for m in members[:8]:
        print(f"  - {m}")
    if len(members) > 8:
        print(f"  ... +{len(members) - 8} more")
    while True:
        raw = input("action [1-5/r/?/v/s/q] "
                    "(append ' <note>' for a boundary-case note): ").strip()
        if not raw:
            continue
        # Split first token (command) from optional trailing note text.
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        note_text = parts[1].strip() if len(parts) > 1 else ""
        if cmd == "q":
            return None
        if cmd == "v":
            view_passages(row)
            continue
        if cmd == "s":
            return "__STATS__"
        if cmd in MODE_KEYS:
            if note_text:
                row["notes"] = (row.get("notes", "") + " | " + note_text
                                ).strip(" |")
            return cmd
        print(f"  unknown action {cmd!r}; valid: "
              f"1 2 3 4 5 r ? v s q (optionally + space + note)")


def tally(state: dict) -> Counter[str]:
    c: Counter[str] = Counter()
    for row in state["rows"]:
        c[row["mode"] or "unassigned"] += 1
    return c


def print_stats(state: dict) -> None:
    c = tally(state)
    total = sum(c.values())
    print()
    print("=" * 78)
    print("  CURRENT TALLY")
    print("=" * 78)
    labels_by_key = {m["key"]: m["name"] for m in MODES}
    for key in ["1", "2", "3", "4", "5", "r", "?", "unassigned"]:
        n = c.get(key, 0)
        name = labels_by_key.get(key, "(unassigned)")
        pct = (100.0 * n / total) if total else 0.0
        print(f"  [{key}]  {name:<40} {n:>4}  ({pct:5.1f}%)")
    print(f"  {'TOTAL':<47} {total:>4}")
    print("=" * 78)


def interactive_classify(state: dict, rater: str) -> None:
    rows = state["rows"]
    while True:
        pending = [r for r in rows if r["mode"] in ("", "?")]
        if not pending:
            break
        # Sort: size DESC, then label ASC — strongest-signal labels first
        pending.sort(key=lambda r: (-r["cluster_size"], r["canonical_label"]))
        total_pending = len(pending)
        row = pending[0]
        idx = len(rows) - total_pending + 1

        action = prompt_label(row, idx, len(rows))
        if action is None:
            save_state(state)
            print("\nSession saved — re-run with --resume to continue.")
            return
        if action == "__STATS__":
            print_stats(state)
            continue
        row["mode"] = action
        row["confirmed_by"] = rater
        row["confirmed_at"] = utcnow_iso()
        row["source"] = "step4"
        save_state(state)
    print("\n✓ all labels classified.")
    print_stats(state)


# ---------------------------------------------------------------------------
# Emit CSV + verify
# ---------------------------------------------------------------------------
COLUMNS = ["canonical_label", "cluster_size", "mode", "confirmed_by",
           "confirmed_at", "source", "notes"]


def emit_csv(state: dict) -> int:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLASSIFY_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for row in state["rows"]:
            if not row["mode"] or row["mode"] == "?":
                continue  # skip deferred/unassigned
            w.writerow({k: row.get(k, "") for k in COLUMNS})
    return sum(1 for r in state["rows"]
               if r["mode"] and r["mode"] != "?")


def run_verify() -> int:
    if not CLASSIFY_CSV.exists():
        print(f"✗ {CLASSIFY_CSV} not found.", file=sys.stderr)
        return 1
    if not CONSOLIDATED_CSV.exists():
        print(f"✗ {CONSOLIDATED_CSV} not found.", file=sys.stderr)
        return 1
    cls = pd.read_csv(CLASSIFY_CSV, dtype=str).fillna("")
    cons = pd.read_csv(CONSOLIDATED_CSV, dtype=str).fillna("")
    raw_labels = set(cons["canonical_label"])
    cls_labels = set(cls["canonical_label"])
    missing = raw_labels - cls_labels
    extras = cls_labels - raw_labels
    dups = [l for l, n in Counter(cls["canonical_label"]).items() if n > 1]
    errors = 0
    if missing:
        print(f"✗ {len(missing)} canonical label(s) unclassified:")
        for m in sorted(list(missing))[:10]:
            print(f"    - {m!r}")
        errors += 1
    if extras:
        print(f"✗ {len(extras)} label(s) in classifications not in source")
        errors += 1
    if dups:
        print(f"✗ {len(dups)} duplicate canonical label(s)")
        errors += 1
    # Mode distribution
    valid = {"1", "2", "3", "4", "5", "r"}
    bad_mode = cls[~cls["mode"].isin(valid)]
    if len(bad_mode):
        print(f"✗ {len(bad_mode)} row(s) with invalid mode "
              f"(must be 1-5 or r)")
        errors += 1
    if errors == 0:
        print(f"✓ partition verify passed — {len(cls_labels)} labels "
              f"classified into modes "
              f"{sorted(cls['mode'].unique().tolist())}")
        print(cls["mode"].value_counts().to_string())
        return 0
    return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task 4.2 Step 4 — interactive canonical-label "
                    "→ interaction-mode classifier")
    p.add_argument("--resume", action="store_true",
                   help="Continue an existing session.")
    p.add_argument("--rater", type=str,
                   default=os.environ.get("RATER_INITIALS", "TBS"),
                   help="Rater initials for confirmed_by.")
    p.add_argument("--stats", action="store_true",
                   help="Print the current tally and exit.")
    p.add_argument("--verify", action="store_true",
                   help="Check partition invariants on taxonomy_classifications.csv.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    print("=" * 78)
    print("  Task 4.2 Step 4 — interactive taxonomy classifier")
    print("=" * 78)

    if args.verify:
        return run_verify()

    # Load or initialise state
    if args.resume or STATE_JSON.exists():
        state = load_state()
        if state is None:
            print(f"✗ no state at {STATE_JSON}; run without --resume first.",
                  file=sys.stderr)
            return 1
        print(f"Resuming session started {state.get('started_at','?')}; "
              f"rater {state.get('rater','?')}.")
    else:
        labels = load_labels()
        placed = labels_placed_in_taxonomy()
        state = initial_state(labels, placed, args.rater)
        print(f"Fresh session. {len(labels)} total labels. "
              f"{sum(1 for r in state['rows'] if r['mode'])} "
              f"already placed via Step-3 strawman (skipped). "
              f"{sum(1 for r in state['rows'] if not r['mode'])} "
              f"to classify.")
        save_state(state)

    if args.stats:
        print_stats(state)
        return 0

    interactive_classify(state, args.rater)
    n = emit_csv(state)
    print(f"\n✓ wrote {n} rows to {CLASSIFY_CSV.relative_to(ROOT)}")
    print("  run  python code/taxonomy_classify.py --verify  "
          "to check the partition")
    return 0


if __name__ == "__main__":
    sys.exit(main())
