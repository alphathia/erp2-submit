"""Interactive title/abstract screening harness for Task 2.5.

Pipeline step 7: Presents each candidate paper and captures the rater's
decision (include/exclude/defer), criterion (for exclusions), provisional
F1 Wieringa class, preprint_paper flag, and optional rationale.

Three passes supported:
  --pass 1 (default):   main pass over all candidates with ic5_status != fail
  --pass 2:             resolve decision=defer rows only (d key disabled)
  --review-mode:        intra-rater consistency check on a 10% sample

Usage:
    python code/screening_harness.py
    python code/screening_harness.py --order rank --batch-goal 100
    python code/screening_harness.py --pass 2
    python code/screening_harness.py --review-mode --sample-fraction 0.1

Consumes:
    artifacts/search/post_filtered.csv
    artifacts/protocol/codebook.md  (for --help hints on F1 classes)

Produces:
    artifacts/screening/phase2_decisions.csv  (append-only main pass)
    artifacts/screening/phase2_review.csv     (review-mode only)
    artifacts/screening/included_set.csv      (derived on completion)
    artifacts/screening/borderline_log.csv    (derived on completion)
    Appends rows to decision_register.csv
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import csv
import hashlib
import json
import os
import sys
import textwrap
import time
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyperclip
import readchar
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta

# ---------------------------------------------------------------------------
# Constants — paths
# ---------------------------------------------------------------------------

DEFAULT_INPUT = ROOT / "artifacts" / "search" / "post_filtered.csv"
OUTPUT_DIR = ROOT / "artifacts" / "screening"
DECISIONS_CSV = OUTPUT_DIR / "phase2_decisions.csv"
REVIEW_CSV = OUTPUT_DIR / "phase2_review.csv"
INCLUDED_CSV = OUTPUT_DIR / "included_set.csv"
BORDERLINE_CSV = OUTPUT_DIR / "borderline_log.csv"

# ---------------------------------------------------------------------------
# Constants — decision vocabulary
# ---------------------------------------------------------------------------

# Exclusion criteria — number key → (code, label)
EXCLUSION_CRITERIA = {
    "1": ("EC1", "Solution Proposal only (Wieringa)"),
    "2": ("EC2", "Validation Research / benchmark without human users (Wieringa)"),
    "3": ("EC3", "Outside SE domain"),
    "4": ("EC4", "Secondary study (survey/SLR)"),
    "5": ("EC5", "Short paper (<4 pages), poster, extended abstract"),
    "6": ("EC6", "Full text not retrievable within two weeks"),
}

# F1 Wieringa classes — shortcut key → class name
F1_CLASSES = {
    "r": "Evaluation Research",
    "v": "Validation Research",
    "s": "Solution Proposal",
    "p": "Philosophical",
    "o": "Opinion",
    "x": "Personal Experience",
}

# preprint_paper values — key → value
PREPRINT_VALUES = {
    "p": "preprint",
    "P": "published",
    "m": "mixed",
    "u": "unknown",
}

# F1 auto-fill rules by exclusion criterion (EC1→SP, EC2→VR deterministic)
F1_AUTOFILL = {
    "EC1": "Solution Proposal",
    "EC2": "Validation Research",
}

# Output columns for phase2_decisions.csv
DECISION_COLUMNS = [
    "paper_id", "doi", "title", "year", "venue", "scis_rank",
    "decision", "criterion", "f1_provisional", "preprint_paper",
    "rationale", "timestamp", "first_decision_timestamp",
    "rater_initials", "session_id", "pass_number",
]

# Back history size
MAX_BACK = 10

# ---------------------------------------------------------------------------
# Loading & Filtering
# ---------------------------------------------------------------------------

def load_input(path: Path) -> pd.DataFrame:
    """Load post_filtered.csv and filter out ic5_status=fail rows."""
    if not path.exists():
        print(f"ERROR: Input CSV not found: {path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(path, dtype=str)
    # Filter out rows that already failed IC5 — they don't need screening
    screenable = df[df["ic5_status"] != "fail"].copy().reset_index(drop=True)
    return screenable


def compute_paper_id(row: pd.Series) -> str:
    """Compute paper_id from dedup_group (preferred) or DOI-based fallback."""
    group = row.get("dedup_group")
    if pd.notna(group) and str(group).strip():
        return str(group)
    # Fallback: use DOI or a title-hash
    doi = row.get("doi")
    if pd.notna(doi) and str(doi).strip():
        return f"doi:{str(doi).strip().lower()}"
    # Last resort: hash of title
    title = str(row.get("title", "")).strip()
    return f"hash:{hashlib.md5(title.encode('utf-8')).hexdigest()[:12]}"


def load_existing_decisions(path: Path) -> pd.DataFrame:
    """Load phase2_decisions.csv if it exists; else return empty frame."""
    if not path.exists():
        return pd.DataFrame(columns=DECISION_COLUMNS)
    return pd.read_csv(path, dtype=str)


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------

def order_candidates(df: pd.DataFrame, order: str, seed: int) -> pd.DataFrame:
    """Order candidate rows per the chosen strategy."""
    if order == "doi":
        return df.sort_values("doi", na_position="last", kind="stable").reset_index(drop=True)
    if order == "recent":
        # Year desc (most recent first)
        df = df.copy()
        df["_year_int"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
        df = df.sort_values("_year_int", ascending=False, kind="stable")
        return df.drop(columns=["_year_int"]).reset_index(drop=True)
    if order == "rank":
        # SCIS A* first, then A, B, Not found
        rank_score = {"A*": 3, "A": 2, "B": 1, "Not found": 0}
        df = df.copy()
        df["_rank_score"] = df["scis_rank"].map(lambda r: rank_score.get(str(r), 0))
        df = df.sort_values("_rank_score", ascending=False, kind="stable")
        return df.drop(columns=["_rank_score"]).reset_index(drop=True)
    if order == "random":
        return df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# UI / Display (using rich)
# ---------------------------------------------------------------------------

console = Console()


def build_paper_panel(row: pd.Series, index: int, total: int,
                      session_stats: dict) -> Panel:
    """Build a rich Panel for a single paper display."""
    # Extract fields safely
    doi = str(row.get("doi", "")).strip() or "(no DOI)"
    venue = str(row.get("source", "")).strip() or "(no venue)"
    year = str(row.get("year", "")).strip() or "?"
    scis_acr = str(row.get("scis_acronym", "")).strip()
    scis_vtype = str(row.get("scis_venue_type", "")).strip()
    scis_rank = str(row.get("scis_rank", "")).strip()
    ic5 = str(row.get("ic5_status", "")).strip()
    page_count = str(row.get("page_count", "")).strip()

    # Build flags string
    flags = []
    if str(row.get("preprint_flag", "")).lower() in ("true", "1"):
        flags.append("[yellow]preprint[/yellow]")
    if str(row.get("retracted_flag", "")).lower() in ("true", "1"):
        flags.append("[red]retracted[/red]")
    if str(row.get("paratext_flag", "")).lower() in ("true", "1"):
        flags.append("[magenta]paratext[/magenta]")
    if pd.notna(row.get("ic3_flag")) and str(row.get("ic3_flag")).strip():
        flags.append("[bold red]⚠ IC3 mismatch — verify DOI with O key[/bold red]")
    flags_text = " | ".join(flags) if flags else "[green](none)[/green]"

    # SCIS badge
    if scis_rank != "Not found":
        scis_badge = f"[bold cyan][{scis_acr} · {scis_vtype} · {scis_rank}][/bold cyan]"
    else:
        scis_badge = "[dim]Not in SCIS list[/dim]"

    # Title and abstract
    title = str(row.get("title", "")).strip() or "(no title)"
    abstract = str(row.get("abstract", "")).strip()
    abstract_display = abstract if abstract else "[red]⚠ No abstract available[/red]"

    # manual_review indicator
    if ic5 == "manual_review":
        ic5_display = "[yellow]manual_review[/yellow] — Policy A: trust abstract; page verified at Task 3.1"
    else:
        ic5_display = f"[green]{ic5}[/green] ({page_count} pages)" if page_count else f"[green]{ic5}[/green]"

    # Session stats
    stats_line = (
        f"Session: {session_stats['decided']} decided   |  "
        f"[green]✓ {session_stats['include']} include[/green]   "
        f"[red]✗ {session_stats['exclude']} exclude[/red]   "
        f"[yellow]? {session_stats['defer']} defer[/yellow]"
    )

    # Assemble panel body
    body_lines = [
        f"[bold]DOI:[/bold]     {doi}",
        f"[bold]Venue:[/bold]   {venue}",
        f"[bold]SCIS:[/bold]    {scis_badge}",
        f"[bold]Year:[/bold]    {year}       [bold]ic5_status:[/bold] {ic5_display}",
        f"[bold]Flags:[/bold]   {flags_text}",
        "─" * 78,
        "[bold]TITLE[/bold]",
        title,
        "─" * 78,
        "[bold]ABSTRACT[/bold]",
        abstract_display,
        "─" * 78,
        stats_line,
        "",
        "[bold][i][/bold]nclude  [bold][e][/bold]xclude  [bold][d][/bold]efer  "
        "[bold][b][/bold]ack  [bold][?][/bold]help  [bold][q][/bold]uit  "
        "[bold][O][/bold]pen-DOI  [bold][L][/bold]LM-hint",
    ]

    title_line = f"ERP2-SMS Screening   Paper {index + 1}/{total} ({(index+1)/total*100:.1f}%)"
    return Panel("\n".join(body_lines), title=title_line, border_style="blue")


def show_help() -> None:
    """Display the help screen with all shortcuts and criteria."""
    console.clear()
    table = Table(title="Screening Harness Help", show_lines=True)
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Action")

    main_keys = [
        ("i", "Include (→ F1 sub-prompt → preprint → rationale)"),
        ("e", "Exclude (→ criterion sub-prompt → F1 auto-fill or prompt → preprint → rationale)"),
        ("d", "Defer (borderline; resolve in --pass 2)"),
        ("b", "Back — undo last decision (up to 10 back)"),
        ("?", "Show this help"),
        ("q", "Save state and quit"),
        ("s", "Skip (no decision; creates gap for second pass)"),
        ("F", "Show codebook F1 definitions"),
        ("O", "Open DOI URL in browser (IC3 verification)"),
        ("L", "Copy title+abstract to clipboard for LLM consultation; prefix rationale with [LLM-assisted]"),
    ]
    for k, v in main_keys:
        table.add_row(k, v)
    console.print(table)

    console.print("\n[bold]Exclusion criteria (sub-prompt after 'e'):[/bold]")
    for k, (code, label) in EXCLUSION_CRITERIA.items():
        console.print(f"  [cyan]{k}[/cyan] → {code}: {label}")

    console.print("\n[bold]F1 Wieringa classes (sub-prompt for includes and EC3–EC6 exclusions):[/bold]")
    for k, v in F1_CLASSES.items():
        console.print(f"  [cyan]{k}[/cyan] → {v}")

    console.print("\n[bold]preprint_paper values:[/bold]")
    for k, v in PREPRINT_VALUES.items():
        console.print(f"  [cyan]{k}[/cyan] → {v}")

    console.print("\n[dim]Press any key to return to screening...[/dim]")
    readchar.readkey()


# ---------------------------------------------------------------------------
# Sub-prompts (capture criterion, F1, preprint_paper, rationale)
# ---------------------------------------------------------------------------

def prompt_exclusion_criterion() -> str | None:
    """Prompt for exclusion criterion. Returns EC code or None (back out)."""
    console.print("\n[bold yellow]Which criterion?[/bold yellow]")
    for key, (code, label) in EXCLUSION_CRITERIA.items():
        console.print(f"  [cyan]{key}[/cyan] {code}: {label}")
    console.print("  [cyan]↵[/cyan] Cancel (back to main prompt)")

    while True:
        key = readchar.readkey()
        if key in ("\r", "\n", readchar.key.ENTER):
            return None
        if key in EXCLUSION_CRITERIA:
            code, label = EXCLUSION_CRITERIA[key]
            console.print(f"[green]→ {code}[/green]")
            return code


def prompt_f1_class(optional: bool = False) -> str | None:
    """Prompt for F1 Wieringa class. If optional, '↵' returns None."""
    console.print("\n[bold yellow]Provisional F1 Wieringa class?[/bold yellow]")
    for k, v in F1_CLASSES.items():
        console.print(f"  [cyan]{k}[/cyan] {v}")
    if optional:
        console.print("  [cyan]↵[/cyan] Skip (optional)")

    while True:
        key = readchar.readkey()
        if optional and key in ("\r", "\n", readchar.key.ENTER):
            return None
        if key in F1_CLASSES:
            cls = F1_CLASSES[key]
            console.print(f"[green]→ {cls}[/green]")
            return cls


def prompt_preprint_paper(default: str) -> str:
    """Prompt for preprint_paper; default accepted by Enter."""
    console.print(
        f"\n[bold yellow]preprint_paper[/bold yellow] "
        f"(default=[green]{default}[/green]):   "
        f"[cyan]p[/cyan]reprint  [cyan]P[/cyan]ublished  "
        f"[cyan]m[/cyan]ixed  [cyan]u[/cyan]nknown  [cyan]↵[/cyan]accept"
    )
    while True:
        key = readchar.readkey()
        if key in ("\r", "\n", readchar.key.ENTER):
            return default
        if key in PREPRINT_VALUES:
            val = PREPRINT_VALUES[key]
            console.print(f"[green]→ {val}[/green]")
            return val


def prompt_rationale() -> str:
    """Prompt for optional rationale (free text)."""
    console.print("\n[bold yellow]Rationale[/bold yellow] "
                  "(optional, press Enter to skip; prefix with [LLM-assisted] "
                  "if LLM was used):")
    try:
        text = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        text = ""
    return text


def compute_preprint_default(row: pd.Series) -> str:
    """Derive default preprint_paper from existing flags."""
    preprint = str(row.get("preprint_flag", "")).lower() in ("true", "1")
    ic3 = pd.notna(row.get("ic3_flag")) and str(row.get("ic3_flag")).strip()
    if preprint or ic3:
        return "preprint"
    return "published"


# ---------------------------------------------------------------------------
# Decision I/O
# ---------------------------------------------------------------------------

def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def append_decision(csv_path: Path, record: dict) -> None:
    """Atomically append a decision row to CSV. Creates header if new file."""
    ensure_output_dir()
    file_exists = csv_path.exists() and csv_path.stat().st_size > 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DECISION_COLUMNS,
                                quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in DECISION_COLUMNS})


def truncate_last_row(csv_path: Path) -> dict | None:
    """Remove the last data row from csv_path and return it as a dict."""
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path, dtype=str)
    if len(df) == 0:
        return None
    last = df.iloc[-1].to_dict()
    df.iloc[:-1].to_csv(csv_path, index=False, quoting=csv.QUOTE_ALL)
    return last


def update_decision_in_place(csv_path: Path, paper_id: str,
                              updates: dict) -> None:
    """Update a specific row (by paper_id) in phase2_decisions.csv.

    Used in --pass 2 to overwrite a defer row with a firm decision.
    Preserves first_decision_timestamp.
    """
    df = pd.read_csv(csv_path, dtype=str)
    mask = df["paper_id"] == paper_id
    if not mask.any():
        raise ValueError(f"paper_id {paper_id} not found in {csv_path}")

    idx = df[mask].index[0]
    # Preserve original timestamp as first_decision_timestamp
    if pd.isna(df.at[idx, "first_decision_timestamp"]) or \
       not str(df.at[idx, "first_decision_timestamp"]).strip():
        df.at[idx, "first_decision_timestamp"] = df.at[idx, "timestamp"]

    # Apply updates
    for k, v in updates.items():
        df.at[idx, k] = v

    df.to_csv(csv_path, index=False, quoting=csv.QUOTE_ALL)


# ---------------------------------------------------------------------------
# Decision gathering (the main prompt flow)
# ---------------------------------------------------------------------------

def gather_decision(row: pd.Series, session_stats: dict,
                    allow_defer: bool = True) -> dict | None:
    """Display paper and gather a decision. Returns record dict or None (skip/back).

    Record dict contains: decision, criterion, f1_provisional,
                          preprint_paper, rationale
    Returns a sentinel {'_action': 'back' | 'quit' | 'skip'} for special keys.
    """
    while True:
        panel = build_paper_panel(row, session_stats["index"],
                                  session_stats["total"], session_stats)
        console.clear()
        console.print(panel)

        key = readchar.readkey()

        if key == "q":
            return {"_action": "quit"}
        if key == "b":
            return {"_action": "back"}
        if key == "s":
            return {"_action": "skip"}
        if key == "?":
            show_help()
            continue
        if key == "O":
            doi = str(row.get("doi", "")).strip()
            if doi:
                url = f"https://doi.org/{doi}" if not doi.startswith("http") else doi
                try:
                    webbrowser.open(url)
                    console.print(f"[green]Opened {url}[/green]")
                except Exception as e:
                    console.print(f"[red]Could not open browser: {e}[/red]")
                time.sleep(1)
            continue
        if key == "L":
            # Copy title + abstract to clipboard for LLM consultation
            title = str(row.get("title", "")).strip()
            abstract = str(row.get("abstract", "")).strip()
            flags_text = []
            if str(row.get("preprint_flag", "")).lower() in ("true", "1"):
                flags_text.append("preprint")
            if pd.notna(row.get("ic3_flag")) and str(row.get("ic3_flag")).strip():
                flags_text.append("IC3 mismatch")
            flags_str = f"Flags: {', '.join(flags_text)}\n\n" if flags_text else ""
            clip = (
                f"SE-agent screening consult (prefix rationale with [LLM-assisted])\n\n"
                f"{flags_str}"
                f"TITLE: {title}\n\n"
                f"ABSTRACT:\n{abstract}\n"
            )
            try:
                pyperclip.copy(clip)
                console.print("[green]Copied to clipboard. Consult LLM in another "
                              "window, then return and decide.[/green]")
            except Exception as e:
                console.print(f"[red]Clipboard error: {e}[/red]")
            time.sleep(1)
            continue

        if key == "i":
            return handle_include(row)
        if key == "e":
            return handle_exclude(row)
        if key == "d":
            if allow_defer:
                return handle_defer(row)
            console.print("[yellow]Defer is disabled in --pass 2. "
                          "Please choose include or exclude.[/yellow]")
            time.sleep(1)
            continue

        # Unrecognised key — ignore and re-display
        continue


def handle_include(row: pd.Series) -> dict:
    """Gather the sub-fields needed for an include decision."""
    f1 = prompt_f1_class(optional=False)
    preprint_default = compute_preprint_default(row)
    preprint = prompt_preprint_paper(preprint_default)
    rationale = prompt_rationale()
    return {
        "decision": "include",
        "criterion": "",
        "f1_provisional": f1,
        "preprint_paper": preprint,
        "rationale": rationale,
    }


def handle_exclude(row: pd.Series) -> dict:
    """Gather the sub-fields needed for an exclude decision."""
    criterion = prompt_exclusion_criterion()
    if criterion is None:
        # User backed out of criterion prompt — treat as no-op
        return {"_action": "back_out"}

    # F1 auto-fill for EC1/EC2; prompt for EC3-EC6
    if criterion in F1_AUTOFILL:
        f1 = F1_AUTOFILL[criterion]
        console.print(f"[dim]F1 auto-filled: {f1} "
                      f"({criterion} → {f1} by definition)[/dim]")
    else:
        f1 = prompt_f1_class(optional=False)

    preprint_default = compute_preprint_default(row)
    preprint = prompt_preprint_paper(preprint_default)
    rationale = prompt_rationale()
    return {
        "decision": "exclude",
        "criterion": criterion,
        "f1_provisional": f1,
        "preprint_paper": preprint,
        "rationale": rationale,
    }


def handle_defer(row: pd.Series) -> dict:
    """Gather minimal info for a deferred decision."""
    # Optional F1 for defer
    f1 = prompt_f1_class(optional=True)
    preprint_default = compute_preprint_default(row)
    preprint = prompt_preprint_paper(preprint_default)
    rationale = prompt_rationale()
    return {
        "decision": "defer",
        "criterion": "",
        "f1_provisional": f1 or "",
        "preprint_paper": preprint,
        "rationale": rationale,
    }


# ---------------------------------------------------------------------------
# Main Pass (pass 1)
# ---------------------------------------------------------------------------

def run_main_pass(input_df: pd.DataFrame, args: argparse.Namespace,
                   session_id: str, rater: str) -> None:
    """Run the main screening pass over all undecided candidates."""
    # Load existing decisions and filter to get the queue
    existing = load_existing_decisions(DECISIONS_CSV)
    decided_ids = set(existing["paper_id"].astype(str)) if len(existing) > 0 else set()

    # Compute paper_ids for input
    input_df = input_df.copy()
    input_df["_paper_id"] = input_df.apply(compute_paper_id, axis=1)
    queue = input_df[~input_df["_paper_id"].isin(decided_ids)].reset_index(drop=True)

    total = len(queue) + len(decided_ids)
    console.print(f"[bold]Main pass (1):[/bold] {len(decided_ids)} already decided, "
                  f"{len(queue)} to screen.")

    if len(queue) == 0:
        console.print("[green]✓ All candidates decided in the main pass.[/green]")
        console.print("[dim]Run with --pass 2 to resolve deferrals (if any).[/dim]")
        return

    # Order the queue
    queue = order_candidates(queue, args.order, args.seed)

    # Session stats
    session_stats = {
        "decided": 0,
        "include": 0,
        "exclude": 0,
        "defer": 0,
        "index": 0,
        "total": total,
    }
    batch_start = time.time()
    back_history: list[str] = []

    i = 0
    while i < len(queue):
        row = queue.iloc[i]
        paper_id = row["_paper_id"]
        session_stats["index"] = len(decided_ids) + i

        record_fields = gather_decision(row, session_stats, allow_defer=True)

        if record_fields is None:
            continue

        if record_fields.get("_action") == "quit":
            print_session_summary(session_stats, batch_start)
            return
        if record_fields.get("_action") == "back":
            if not back_history:
                console.print("[yellow]Nothing to back out of.[/yellow]")
                time.sleep(0.5)
                continue
            # Pop last decided paper_id, re-queue it
            popped = back_history.pop()
            removed = truncate_last_row(DECISIONS_CSV)
            if removed:
                session_stats["decided"] -= 1
                decision = removed.get("decision", "")
                if decision in session_stats:
                    session_stats[decision] -= 1
                decided_ids.discard(popped)
                console.print(f"[yellow]Backed out: {popped} "
                              f"(decision was {decision})[/yellow]")
                time.sleep(0.5)
                # Insert the popped paper back at current position
                popped_row = input_df[input_df["_paper_id"] == popped].iloc[0]
                queue = pd.concat([
                    queue.iloc[:i],
                    popped_row.to_frame().T,
                    queue.iloc[i:],
                ], ignore_index=True)
                continue
        if record_fields.get("_action") == "skip":
            i += 1
            continue
        if record_fields.get("_action") == "back_out":
            continue

        # Build the full record
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "paper_id": paper_id,
            "doi": str(row.get("doi", "")).strip(),
            "title": str(row.get("title", "")).strip(),
            "year": str(row.get("year", "")).strip(),
            "venue": str(row.get("source", "")).strip(),
            "scis_rank": str(row.get("scis_rank", "")).strip(),
            "decision": record_fields["decision"],
            "criterion": record_fields["criterion"],
            "f1_provisional": record_fields["f1_provisional"],
            "preprint_paper": record_fields["preprint_paper"],
            "rationale": record_fields["rationale"],
            "timestamp": now,
            "first_decision_timestamp": "",
            "rater_initials": rater,
            "session_id": session_id,
            "pass_number": "1",
        }

        append_decision(DECISIONS_CSV, record)

        # Update stats
        session_stats["decided"] += 1
        session_stats[record_fields["decision"]] += 1

        decided_ids.add(paper_id)
        back_history.append(paper_id)
        if len(back_history) > MAX_BACK:
            back_history = back_history[-MAX_BACK:]

        i += 1

        # Check batch goal
        if args.batch_goal and session_stats["decided"] >= args.batch_goal:
            console.print(f"\n[bold green]Batch goal reached "
                          f"({args.batch_goal} decisions).[/bold green]")
            print_session_summary(session_stats, batch_start)
            return

    print_session_summary(session_stats, batch_start)
    console.print("[bold green]✓ Main pass complete.[/bold green]")

    # Derive outputs (included_set and borderline_log)
    derive_outputs()


# ---------------------------------------------------------------------------
# Second Pass (pass 2) — resolve defers
# ---------------------------------------------------------------------------

def run_second_pass(input_df: pd.DataFrame, args: argparse.Namespace,
                     session_id: str, rater: str) -> None:
    """Pass 2: present all decision=defer rows for firm resolution."""
    existing = load_existing_decisions(DECISIONS_CSV)
    defers = existing[existing["decision"] == "defer"]

    if len(defers) == 0:
        console.print("[green]✓ No deferred rows to review — pass 2 skipped.[/green]")
        derive_outputs()
        return

    console.print(f"[bold]Second pass (2):[/bold] {len(defers)} deferred "
                  f"papers to resolve.")

    # Build a map paper_id → input row (for display)
    input_df = input_df.copy()
    input_df["_paper_id"] = input_df.apply(compute_paper_id, axis=1)

    session_stats = {
        "decided": 0, "include": 0, "exclude": 0, "defer": 0,
        "index": 0, "total": len(defers),
    }
    batch_start = time.time()

    for i, (_, defer_row) in enumerate(defers.iterrows()):
        paper_id = defer_row["paper_id"]
        candidates = input_df[input_df["_paper_id"] == paper_id]
        if len(candidates) == 0:
            console.print(f"[red]Skipping {paper_id} — not found in input[/red]")
            continue
        src_row = candidates.iloc[0]
        session_stats["index"] = i

        record_fields = gather_decision(src_row, session_stats,
                                         allow_defer=False)

        if record_fields is None:
            continue
        if record_fields.get("_action") == "quit":
            print_session_summary(session_stats, batch_start)
            return
        if record_fields.get("_action") == "skip":
            continue
        if record_fields.get("_action") == "back_out":
            continue

        # Update in place (preserving first_decision_timestamp)
        now = datetime.now(timezone.utc).isoformat()
        updates = {
            "decision": record_fields["decision"],
            "criterion": record_fields["criterion"],
            "f1_provisional": record_fields["f1_provisional"],
            "preprint_paper": record_fields["preprint_paper"],
            "rationale": record_fields["rationale"],
            "timestamp": now,
            "session_id": session_id,
            "pass_number": "2",
        }
        update_decision_in_place(DECISIONS_CSV, paper_id, updates)

        session_stats["decided"] += 1
        session_stats[record_fields["decision"]] += 1

    print_session_summary(session_stats, batch_start)
    console.print("[bold green]✓ Second pass complete.[/bold green]")
    derive_outputs()


# ---------------------------------------------------------------------------
# Review Mode — intra-rater consistency
# ---------------------------------------------------------------------------

def run_review_mode(input_df: pd.DataFrame, args: argparse.Namespace,
                     session_id: str, rater: str) -> None:
    """Re-screen a random sample with priors hidden, compare agreement."""
    import numpy as np

    # Assert all decisions complete (no defers)
    existing = load_existing_decisions(DECISIONS_CSV)
    if len(existing) == 0:
        console.print("[red]ERROR: No decisions in phase2_decisions.csv[/red]")
        sys.exit(1)
    defer_count = (existing["decision"] == "defer").sum()
    if defer_count > 0:
        console.print(f"[red]ERROR: {defer_count} deferred rows remain. "
                      f"Run --pass 2 first.[/red]")
        sys.exit(1)

    # Sample
    np.random.seed(args.sample_seed)
    n_sample = max(1, int(len(existing) * args.sample_fraction))
    sample_ids = np.random.choice(existing["paper_id"].values,
                                   size=n_sample, replace=False)
    sample_ids = set(sample_ids)
    console.print(f"[bold]Review mode:[/bold] sampling {n_sample} of "
                  f"{len(existing)} papers (fraction={args.sample_fraction}, "
                  f"seed={args.sample_seed})")

    # Build input lookup
    input_df = input_df.copy()
    input_df["_paper_id"] = input_df.apply(compute_paper_id, axis=1)

    # Check for existing review file — skip already-re-reviewed
    if REVIEW_CSV.exists():
        existing_review = pd.read_csv(REVIEW_CSV, dtype=str)
        already_reviewed = set(existing_review["paper_id"].astype(str))
        sample_ids -= already_reviewed
        console.print(f"[dim]Resuming: {len(already_reviewed)} already re-reviewed; "
                      f"{len(sample_ids)} remaining.[/dim]")

    session_stats = {
        "decided": 0, "include": 0, "exclude": 0, "defer": 0,
        "index": 0, "total": n_sample,
    }
    batch_start = time.time()

    for i, paper_id in enumerate(sample_ids):
        candidates = input_df[input_df["_paper_id"] == paper_id]
        if len(candidates) == 0:
            continue
        src_row = candidates.iloc[0]
        session_stats["index"] = i

        # Hide priors — the gather_decision function doesn't show them
        record_fields = gather_decision(src_row, session_stats, allow_defer=False)

        if record_fields is None:
            continue
        if record_fields.get("_action") == "quit":
            break
        if record_fields.get("_action") == "skip":
            continue
        if record_fields.get("_action") == "back_out":
            continue

        now = datetime.now(timezone.utc).isoformat()
        record = {
            "paper_id": paper_id,
            "doi": str(src_row.get("doi", "")).strip(),
            "title": str(src_row.get("title", "")).strip(),
            "year": str(src_row.get("year", "")).strip(),
            "venue": str(src_row.get("source", "")).strip(),
            "scis_rank": str(src_row.get("scis_rank", "")).strip(),
            "decision": record_fields["decision"],
            "criterion": record_fields["criterion"],
            "f1_provisional": record_fields["f1_provisional"],
            "preprint_paper": record_fields["preprint_paper"],
            "rationale": record_fields["rationale"],
            "timestamp": now,
            "first_decision_timestamp": "",
            "rater_initials": rater,
            "session_id": session_id,
            "pass_number": "review",
        }
        append_decision(REVIEW_CSV, record)

        session_stats["decided"] += 1
        session_stats[record_fields["decision"]] += 1

    print_session_summary(session_stats, batch_start)

    # Compute agreement if review file exists
    if REVIEW_CSV.exists():
        compute_and_report_agreement()


def compute_and_report_agreement() -> None:
    """Compare phase2_decisions.csv and phase2_review.csv; report kappa."""
    first = load_existing_decisions(DECISIONS_CSV)
    second = pd.read_csv(REVIEW_CSV, dtype=str)
    merged = first.merge(second, on="paper_id", suffixes=("_first", "_second"))

    if len(merged) == 0:
        console.print("[yellow]No overlapping papers for agreement calc.[/yellow]")
        return

    agree = (merged["decision_first"] == merged["decision_second"]).sum()
    total = len(merged)
    percent_agreement = agree / total * 100

    # Cohen's kappa (exclude defer)
    non_defer = merged[(merged["decision_first"].isin(["include", "exclude"])) &
                       (merged["decision_second"].isin(["include", "exclude"]))]
    if len(non_defer) > 0:
        po = (non_defer["decision_first"] == non_defer["decision_second"]).sum() / len(non_defer)
        # Marginals
        pf_inc = (non_defer["decision_first"] == "include").sum() / len(non_defer)
        ps_inc = (non_defer["decision_second"] == "include").sum() / len(non_defer)
        pe = pf_inc * ps_inc + (1 - pf_inc) * (1 - ps_inc)
        kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    else:
        kappa = float("nan")

    console.print()
    console.print(Panel(
        f"[bold]Intra-rater consistency report[/bold]\n\n"
        f"Sample size:       {total}\n"
        f"Agreements:        {agree}\n"
        f"Percent agreement: {percent_agreement:.1f}%\n"
        f"Cohen's kappa:     {kappa:.3f}\n\n"
        f"Target: ≥90% agreement",
        title="Review Mode Report",
        border_style="green" if percent_agreement >= 90 else "yellow",
    ))

    # Log to decision register
    log_to_decision_register(
        "intra_rater_consistency_measured",
        "Single-rater consistency check per Ali & Petersen 2014",
        (f"Sample size: {total}. Agreement: {agree}/{total} "
         f"({percent_agreement:.1f}%). Cohen's kappa: {kappa:.3f}. "
         f"Target ≥90%."),
    )


# ---------------------------------------------------------------------------
# Derive Outputs
# ---------------------------------------------------------------------------

def derive_outputs() -> None:
    """Generate included_set.csv and borderline_log.csv from decisions."""
    if not DECISIONS_CSV.exists():
        return
    df = pd.read_csv(DECISIONS_CSV, dtype=str)
    ensure_output_dir()

    # included_set.csv
    inc = df[df["decision"] == "include"].copy()
    inc_cols = ["paper_id", "doi", "title", "year", "venue", "scis_rank",
                "f1_provisional", "preprint_paper"]
    inc[inc_cols].to_csv(INCLUDED_CSV, index=False, quoting=csv.QUOTE_ALL)
    console.print(f"[green]✓ Written: {INCLUDED_CSV.relative_to(ROOT)} "
                  f"({len(inc)} rows)[/green]")

    # borderline_log.csv
    bor = df[df["decision"] == "defer"].copy()
    bor.to_csv(BORDERLINE_CSV, index=False, quoting=csv.QUOTE_ALL)
    console.print(f"[green]✓ Written: {BORDERLINE_CSV.relative_to(ROOT)} "
                  f"({len(bor)} rows)[/green]")

    # Write meta for phase2_decisions.csv
    write_with_meta(
        target_path=DECISIONS_CSV,
        script="code/screening_harness.py",
        inputs=[str(DEFAULT_INPUT.relative_to(ROOT))],
        seed=42,
    )


# ---------------------------------------------------------------------------
# Decision Register
# ---------------------------------------------------------------------------

def log_to_decision_register(decision: str, rule: str, rationale: str) -> None:
    """Append a row to decision_register.csv."""
    register_path = ROOT / "decision_register.csv"
    timestamp = datetime.now(timezone.utc).isoformat()
    row = {
        "timestamp": timestamp,
        "phase": "2",
        "paper_id": "N/A",
        "decision": decision,
        "rule_applied": rule,
        "rationale": rationale,
        "rater_initials": os.environ.get("RATER_INITIALS", "AT"),
    }
    with open(register_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)


# ---------------------------------------------------------------------------
# Session Summary
# ---------------------------------------------------------------------------

def print_session_summary(stats: dict, start_time: float) -> None:
    """Print a session summary panel."""
    elapsed = time.time() - start_time
    rate = stats["decided"] / elapsed if elapsed > 0 else 0
    summary = (
        f"[bold]Session summary[/bold]\n"
        f"Decided this session: {stats['decided']}\n"
        f"  Include: {stats['include']}\n"
        f"  Exclude: {stats['exclude']}\n"
        f"  Defer:   {stats['defer']}\n"
        f"Elapsed: {elapsed:.0f}s ({rate*60:.1f} papers/min)\n"
    )
    console.print(Panel(summary, border_style="blue"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive title/abstract screening harness (Task 2.5)",
        epilog="Example: python code/screening_harness.py --order rank --batch-goal 100",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"Input CSV (default: {DEFAULT_INPUT.relative_to(ROOT)})")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help=f"Output directory (default: {OUTPUT_DIR.relative_to(ROOT)})")
    parser.add_argument("--order", choices=["doi", "recent", "rank", "random"],
                        default="doi", help="Ordering strategy (default: doi)")
    parser.add_argument("--seed", type=int, default=42, help="Seed for --order random")
    parser.add_argument("--batch-goal", type=int, default=None,
                        help="Exit after N decisions with summary")
    parser.add_argument("--rater", type=str,
                        default=os.environ.get("RATER_INITIALS", "AT"),
                        help="Rater initials")
    parser.add_argument("--paper-id", type=str, default=None,
                        help="Jump to a specific paper")
    parser.add_argument("--pass", type=int, dest="pass_num", default=1,
                        choices=[1, 2],
                        help="Pass number: 1=main, 2=defer-resolution (default 1)")
    parser.add_argument("--review-mode", action="store_true", default=False,
                        help="Intra-rater consistency mode")
    parser.add_argument("--sample-fraction", type=float, default=0.1,
                        help="Review sample fraction (default 0.1)")
    parser.add_argument("--sample-seed", type=int, default=42,
                        help="Review sample seed (default 42)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    session_id = str(uuid.uuid4())[:8]
    rater = args.rater

    console.print(Panel(
        f"[bold]ERP2-SMS Screening Harness[/bold]\n"
        f"Session ID: {session_id}\n"
        f"Rater:      {rater}\n"
        f"Pass:       {'review' if args.review_mode else args.pass_num}",
        border_style="cyan",
    ))

    # Load input
    input_path = args.input.resolve()
    input_df = load_input(input_path)
    console.print(f"Loaded {len(input_df)} candidate rows (ic5_status != fail).")

    # Dispatch to the appropriate mode
    if args.review_mode:
        run_review_mode(input_df, args, session_id, rater)
    elif args.pass_num == 2:
        run_second_pass(input_df, args, session_id, rater)
    else:
        run_main_pass(input_df, args, session_id, rater)


if __name__ == "__main__":
    main()
