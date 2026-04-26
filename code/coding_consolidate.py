"""Task 4.1 — Consolidate pass-1 codes into canonical labels.

Cruzes & Dybå Step 3 (translation): group semantically-equivalent pass-1
`descriptive_code`s from `open_codes_pass1.csv` under canonical labels,
preserving a bidirectional trace  canonical_label ↔ pass1_codes ↔ passage_ids.

Algorithm (per design/4_1_coding_consolidate.md §2):
    Phase A  Embed each unique descriptive_code (sentence-transformers).
    Phase B  Agglomerative cluster with cosine-distance threshold.
    Phase C  LLM-propose a 2-5 word canonical label per multi-member cluster.
    Phase D  Interactive rater review — approve / rename / split / merge /
             view-passages / quit. State persisted after every decision.
    Phase E  Emit `artifacts/synthesis/consolidated_codes.csv`.

Usage:
    python code/coding_consolidate.py                  # fresh interactive run
    python code/coding_consolidate.py --resume          # continue a prior session
    python code/coding_consolidate.py --dry-run         # cluster+label, print, exit
    python code/coding_consolidate.py --threshold 0.30  # tighter clusters
    python code/coding_consolidate.py --rater AT        # override confirmer id
    python code/coding_consolidate.py --verify          # DoD invariants check
    python code/coding_consolidate.py --stats           # compression ratio + histogram
    python code/coding_consolidate.py --input path.csv  # override input (fixture test)
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
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
OPEN_CODES_CSV    = ROOT / "artifacts" / "extraction" / "open_codes_pass1.csv"
PASSAGES_DIR      = ROOT / "artifacts" / "extraction" / "raw_passages"
SYNTH_DIR         = ROOT / "artifacts" / "synthesis"
CONSOLIDATED_CSV  = SYNTH_DIR / "consolidated_codes.csv"
STATE_JSON        = SYNTH_DIR / ".consolidate_state.json"
EMBEDDINGS_NPZ    = SYNTH_DIR / ".embeddings_cache.npz"
SKIPPED_CSV       = SYNTH_DIR / ".consolidate_skipped.csv"
PROGRESS_MD       = SYNTH_DIR / "consolidate_progress.md"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"
DEFAULT_THRESHOLD   = 0.35
DEFAULT_LLM_MODEL   = "gemini-3-flash-preview"

CONSOLIDATED_COLUMNS = [
    "canonical_label", "pass1_codes", "in_vivo_codes",
    "passage_ids", "cluster_size", "confirmed_by",
    "confirmed_at", "notes",
]

VAGUE_LABELS = {
    "general", "other", "misc", "miscellaneous", "uncategorized",
    "uncategorised", "general usage", "general pattern", "general interaction",
    "various", "mixed", "usage", "pattern", "unlabeled", "unlabelled",
}

PASSAGE_ID_PATTERN = re.compile(r"^(doi|fallback):[^:]+:P\d{3}$")


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha1_of(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def input_sha1(unique_codes: list[str]) -> str:
    """Stable hash of the sorted unique descriptive codes."""
    return sha1_of("\n".join(sorted(unique_codes)))


def passage_md_filename(paper_id: str) -> str:
    return safe_paper_id_to_filename(paper_id).replace(".pdf", ".md")


# ---------------------------------------------------------------------------
# Input loader
# ---------------------------------------------------------------------------
def load_open_codes(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found — run code/extraction.py first.")
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    if len(df) == 0:
        raise ValueError(f"{csv_path} is empty.")
    needed = {"paper_id", "passage_id", "in_vivo_code", "descriptive_code"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"{csv_path} missing columns: {missing}")
    return df


# ---------------------------------------------------------------------------
# Phase A — Embedding
# ---------------------------------------------------------------------------
def compute_embeddings(unique_codes: list[str], model_name: str) -> np.ndarray:
    """Embed each unique descriptive_code; cache by SHA1 of inputs."""
    cache_key = sha1_of("\n".join(sorted(unique_codes)) + "|" + model_name)
    if EMBEDDINGS_NPZ.exists():
        try:
            data = np.load(EMBEDDINGS_NPZ, allow_pickle=True)
            if str(data.get("cache_key")) == cache_key:
                print(f"Embeddings cache hit ({len(unique_codes)} codes).")
                return data["embeddings"]
        except Exception:
            pass  # corrupt cache — fall through and recompute

    print(f"Embedding {len(unique_codes)} unique codes with {model_name}...")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(
            "sentence-transformers not installed. "
            "Run: pip install sentence-transformers scikit-learn"
        ) from e
    model = SentenceTransformer(model_name)
    emb = model.encode(
        unique_codes, show_progress_bar=False,
        convert_to_numpy=True, normalize_embeddings=True,
    )
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(EMBEDDINGS_NPZ, embeddings=emb, cache_key=cache_key)
    return emb


# ---------------------------------------------------------------------------
# Phase B — Clustering
# ---------------------------------------------------------------------------
def cluster_embeddings(embeddings: np.ndarray, threshold: float) -> np.ndarray:
    """Agglomerative clustering with complete linkage over cosine distance."""
    try:
        from sklearn.cluster import AgglomerativeClustering
    except ImportError as e:
        raise ImportError(
            "scikit-learn not installed. Run: pip install scikit-learn"
        ) from e
    clusterer = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=threshold,
        metric="cosine",
        linkage="complete",
    )
    return clusterer.fit_predict(embeddings)


# ---------------------------------------------------------------------------
# Phase C — Canonical-label proposal via Gemini
# ---------------------------------------------------------------------------
LABEL_SYSTEM_PROMPT = """You produce concise analytic labels for qualitative-research code clusters.

Given a cluster of first-pass codes, produce ONE canonical label that captures
the shared concept.

STRICT rules:
- 2 to 5 words. No more, no less.
- Title Case. No trailing punctuation. No quotation marks.
- Do NOT copy verbatim paper language from the in-vivo codes.
- Do NOT use vague words such as: general, other, misc, usage, pattern.
- The label must distinguish this cluster from other clusters.

Return ONLY the label string, nothing else."""


def _label_is_vague(label: str) -> bool:
    if not label:
        return True
    return label.lower().strip() in VAGUE_LABELS


def _label_is_wellformed(label: str) -> bool:
    if _label_is_vague(label):
        return False
    words = label.split()
    return 2 <= len(words) <= 5


def _fallback_label(descriptive: list[str]) -> str:
    """Deterministic fallback when the LLM can't produce a clean label."""
    stop = {"with", "using", "from", "this", "that", "when", "into",
            "such", "about", "what", "code", "user"}
    counter: Counter[str] = Counter()
    for d in descriptive:
        for w in re.split(r"[\s\-_/]+", d.lower()):
            if len(w) >= 4 and w not in stop and w.isalpha():
                counter[w] += 1
    top = [w for w, _ in counter.most_common(3)]
    if len(top) < 2 and descriptive:
        top = descriptive[0].split()[:3]
    if len(top) < 2:
        top = ["Unlabeled", "Cluster"]
    return " ".join(w.capitalize() for w in top[:3])


def propose_label_llm(client, model: str,
                      descriptive: list[str],
                      in_vivo: list[str]) -> str:
    """Ask Gemini for a canonical label; validate + retry + fallback."""
    desc_block = "\n".join(f"  - {d}" for d in descriptive[:40])
    vivo_block = "\n".join(f"  - {v}" for v in in_vivo[:40])
    user = (
        f"Descriptive codes in this cluster:\n{desc_block}\n\n"
        f"In-vivo phrasings (for grounding only; do NOT copy):\n{vivo_block}\n\n"
        f"Return a single canonical label (2-5 words, Title Case)."
    )
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[LABEL_SYSTEM_PROMPT + "\n\n" + user],
                config={"temperature": 0.2},
            )
            label = (response.text or "").strip().strip('"\'')
            label = label.split("\n")[0].strip().rstrip(".!?,;:")
            if _label_is_wellformed(label):
                return label
        except Exception as exc:
            if attempt == 2:
                print(f"  [warn] label LLM failed after retries: {exc}",
                      file=sys.stderr)
    return _fallback_label(descriptive)


# ---------------------------------------------------------------------------
# State file I/O
# ---------------------------------------------------------------------------
def save_state(state: dict) -> None:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_JSON.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_JSON)
    # Refresh the human-readable progress snapshot on every save so the rater
    # (or a supervisor tailing the file) can watch the session live. Silent on
    # error — progress MD is a convenience, not a correctness artefact.
    try:
        _write_progress_md_silent(state, PROGRESS_MD)
    except Exception as exc:
        print(f"  [warn] progress MD refresh failed: {exc}", file=sys.stderr)


def _write_progress_md_silent(state: dict, out_path: Path) -> None:
    """Render the progress markdown from in-memory state; no stdout."""
    body = _render_progress_md(state)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")


def load_state() -> dict | None:
    if not STATE_JSON.exists():
        return None
    try:
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[warn] could not read state file: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Passage lookup (for [v]iew-passages in the rater UI)
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


# ---------------------------------------------------------------------------
# Cluster construction from labels array
# ---------------------------------------------------------------------------
def build_clusters(
    unique_codes: list[str],
    labels: np.ndarray,
    desc_to_invivo: dict[str, list[str]],
    desc_to_passages: dict[str, list[str]],
) -> list[dict]:
    """Materialise cluster objects from clustering output."""
    clusters: list[dict] = []
    n = int(labels.max()) + 1 if len(labels) else 0
    for cid in range(n):
        members = [unique_codes[i]
                   for i in range(len(unique_codes)) if labels[i] == cid]
        in_vivo: list[str] = []
        member_passage_map: list[list[str]] = []  # [[passage_id, code], ...]
        for m in members:
            in_vivo.extend(desc_to_invivo.get(m, []))
            for pid in desc_to_passages.get(m, []):
                member_passage_map.append([pid, m])
        clusters.append({
            "cluster_id": cid,
            "members": members,
            "in_vivo": list(dict.fromkeys(in_vivo)),
            "member_passage_map": member_passage_map,
            "proposed_label": "",
            "status": "pending",
            "final_label": "",
            "confirmed_at": "",
            "confirmed_by": "",
            "notes": "",
        })
    return clusters


# ---------------------------------------------------------------------------
# Phase D — Interactive rater review
# ---------------------------------------------------------------------------
def interactive_review(state: dict, rater: str) -> None:
    clusters = state["clusters"]
    # Sort pending largest first; iterate until none remain (splits add new
    # pending clusters mid-flight, so recompute each iteration).
    while True:
        pending = [c for c in clusters if c["status"] == "pending"]
        if not pending:
            break
        pending.sort(key=lambda c: -len(c["members"]))
        total = len(pending)
        cluster = pending[0]
        aborted = _prompt_cluster(cluster, clusters, rater, 1, total)
        save_state(state)
        if aborted:
            print("Session aborted; state saved. Re-run --resume to continue.")
            return


def _prompt_cluster(cluster: dict, all_clusters: list[dict],
                    rater: str, idx: int, total: int) -> bool:
    """Return True if the rater aborted the session."""
    members = cluster["members"]
    size_flag = "  ⚠ large cluster" if len(members) > 50 else ""
    print("=" * 72)
    print(f"Cluster {cluster['cluster_id']}  "
          f"(size {len(members)}){size_flag}  "
          f"[{idx}/{total} pending]")
    print(f"Proposed label: \"{cluster['proposed_label']}\"")
    print("Member codes:")
    for m in members[:12]:
        print(f"  - {m}")
    if len(members) > 12:
        print(f"  ... and {len(members) - 12} more")
    print()
    while True:
        choice = input(
            "Action [a]pprove / [r]ename / [s]plit / "
            "[m]erge-into <id> / [e]dit <id> / "
            "[v]iew-passages / [q]uit: "
        ).strip()
        if not choice:
            continue
        cmd = choice[0].lower()
        if cmd == "a":
            cluster["status"] = "approved"
            cluster["final_label"] = cluster["proposed_label"]
            cluster["confirmed_at"] = utcnow_iso()
            cluster["confirmed_by"] = rater
            print(f"  ✓ approved: {cluster['final_label']}")
            return False
        if cmd == "r":
            new_label = input("  New label (2-5 words, Title Case): ").strip()
            if not _label_is_wellformed(new_label):
                print("  ✗ must be 2-5 words and not a vague word; try again.")
                continue
            cluster["status"] = "approved"
            cluster["final_label"] = new_label
            cluster["confirmed_at"] = utcnow_iso()
            cluster["confirmed_by"] = rater
            cluster["notes"] = "renamed by rater"
            print(f"  ✓ renamed: {new_label}")
            return False
        if cmd == "s":
            _split_cluster(cluster, all_clusters)
            print(f"  ↘ split into {len(cluster['members'])} singletons")
            return False
        if cmd == "m":
            target_id = _prompt_target_id(choice)
            if target_id is None:
                continue
            target = next((c for c in all_clusters
                           if c["cluster_id"] == target_id), None)
            if target is None or target is cluster:
                print(f"  ✗ no other cluster with id {target_id}")
                continue
            if target["status"] in {"split", "merged"}:
                print(f"  ✗ cluster {target_id} is {target['status']}; "
                      f"cannot merge into a terminal cluster "
                      f"(members would be dropped at emit).")
                continue
            _merge_into(cluster, target)
            print(f"  ⇒ merged into cluster {target_id} "
                  f"(\"{target.get('final_label') or target['proposed_label']}\")")
            return False
        if cmd == "e":
            target_id = _prompt_target_id(choice)
            if target_id is None:
                continue
            target = next((c for c in all_clusters
                           if c["cluster_id"] == target_id), None)
            if target is None:
                print(f"  ✗ no cluster with id {target_id}")
                continue
            if target is cluster:
                print(f"  ✗ that is the current cluster; "
                      f"use [r]ename / [s]plit directly.")
                continue
            if target["status"] in {"merged", "split"}:
                print(f"  ✗ cluster {target_id} is {target['status']}; "
                      f"cannot reopen.")
                continue
            prior_label = (target.get("final_label", "")
                           or target.get("proposed_label", ""))
            prior_by = target.get("confirmed_by", "")
            prior_at = target.get("confirmed_at", "")
            edit_note = (f"edited {utcnow_iso()} "
                         f"(was '{prior_label}' by {prior_by} at {prior_at})")
            target["notes"] = (
                (target.get("notes", "") + "; " + edit_note).strip("; "))
            target["status"] = "pending"
            target["final_label"] = ""
            target["confirmed_at"] = ""
            target["confirmed_by"] = ""
            print(f"  ↺ reopened cluster {target_id} "
                  f"(was \"{prior_label}\")")
            _prompt_cluster(target, all_clusters, rater, 1, 1)
            print(f"  ← back to cluster {cluster['cluster_id']}")
            continue
        if cmd == "v":
            _view_passages(cluster)
            continue
        if cmd == "q":
            return True
        print("  unknown action; try again.")


def _prompt_target_id(choice: str) -> int | None:
    parts = choice.split()
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            pass
    raw = input("  target cluster id: ").strip()
    try:
        return int(raw)
    except ValueError:
        print("  ✗ cluster id must be an integer")
        return None


def _split_cluster(cluster: dict, all_clusters: list[dict]) -> None:
    """Replace one cluster with N singletons (one per member)."""
    cluster["status"] = "split"
    cluster["notes"] = "split by rater — members reopened as singletons"
    next_id = max(c["cluster_id"] for c in all_clusters) + 1
    for m in cluster["members"]:
        member_passages = [
            [pid, mcode] for pid, mcode in cluster["member_passage_map"]
            if mcode == m
        ]
        singleton_in_vivo = []
        # Propagate any in-vivo phrasings linked to this code
        for pid, mcode in member_passages:
            if mcode == m:
                singleton_in_vivo.append(m)  # conservative fallback
        all_clusters.append({
            "cluster_id": next_id,
            "members": [m],
            "in_vivo": list(dict.fromkeys(singleton_in_vivo)),
            "member_passage_map": member_passages,
            "proposed_label": m.title(),
            "status": "pending",
            "final_label": "",
            "confirmed_at": "",
            "confirmed_by": "",
            "notes": f"split from cluster {cluster['cluster_id']}",
        })
        next_id += 1


def _merge_into(cluster: dict, target: dict) -> None:
    """Absorb cluster's members into target; mark cluster as merged."""
    target["members"].extend(cluster["members"])
    target["in_vivo"].extend(cluster.get("in_vivo", []))
    target["in_vivo"] = list(dict.fromkeys(target["in_vivo"]))
    target["member_passage_map"].extend(cluster["member_passage_map"])
    cluster["status"] = "merged"
    cluster["notes"] = f"merged into cluster {target['cluster_id']}"
    cluster["final_label"] = (
        target.get("final_label") or target.get("proposed_label") or "")


def _view_passages(cluster: dict) -> None:
    shown = 0
    for pid, code in cluster["member_passage_map"][:5]:
        parts = pid.rsplit(":", 1)
        if len(parts) != 2:
            continue
        paper_id, passage_id = parts
        text = find_passage_text(paper_id, passage_id)
        print(f"\n  [{pid}]  code=\"{code}\"")
        if text:
            print(f"    {text[:400]}")
        else:
            print("    (passage not found in raw_passages/)")
        shown += 1
    if shown == 0:
        print("  (no passages available)")


# ---------------------------------------------------------------------------
# Phase E — Emit consolidated_codes.csv
# ---------------------------------------------------------------------------
def emit_consolidated(state: dict) -> int:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    seen_labels: set[str] = set()
    for c in state["clusters"]:
        if c["status"] in {"split", "merged"}:
            continue
        if c["status"] != "approved":
            raise ValueError(
                f"cluster {c['cluster_id']} status={c['status']}; "
                f"review incomplete — re-run with --resume")
        label = c["final_label"]
        if label in seen_labels:
            # Deterministic disambiguation — append cluster id
            label = f"{label} ({c['cluster_id']})"
        seen_labels.add(label)

        pass1 = list(dict.fromkeys(c["members"]))
        in_vivo = list(dict.fromkeys(c.get("in_vivo", [])))
        passages = list(dict.fromkeys(
            pid for pid, _code in c["member_passage_map"]))
        rows.append({
            "canonical_label": label,
            "pass1_codes": json.dumps(pass1, ensure_ascii=False),
            "in_vivo_codes": json.dumps(in_vivo, ensure_ascii=False),
            "passage_ids": json.dumps(passages, ensure_ascii=False),
            "cluster_size": len(pass1),
            "confirmed_by": c["confirmed_by"],
            "confirmed_at": c["confirmed_at"],
            "notes": c.get("notes", ""),
        })

    with open(CONSOLIDATED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=CONSOLIDATED_COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# --verify path — DoD invariants
# ---------------------------------------------------------------------------
def run_verify(input_csv: Path | None = None) -> int:
    raw_path = input_csv or OPEN_CODES_CSV
    if not CONSOLIDATED_CSV.exists():
        print(f"✗ {CONSOLIDATED_CSV} not found — run consolidation first.")
        return 1
    if not raw_path.exists():
        print(f"✗ {raw_path} not found.")
        return 1
    print(f"Verifying {CONSOLIDATED_CSV.name} against {raw_path.name}")
    cons = pd.read_csv(CONSOLIDATED_CSV, dtype=str).fillna("")
    raw = pd.read_csv(raw_path, dtype=str).fillna("")
    raw_codes = set(c for c in raw["descriptive_code"].unique() if c.strip())

    errors = 0

    # Invariant 1: every raw descriptive code appears in exactly one list
    seen: Counter[str] = Counter()
    for _, row in cons.iterrows():
        for c in json.loads(row["pass1_codes"]):
            seen[c] += 1
    missing = raw_codes - set(seen)
    dups = {c: n for c, n in seen.items() if n > 1}
    extras = set(seen) - raw_codes
    if missing:
        print(f"✗ {len(missing)} descriptive code(s) missing from consolidated:")
        for m in list(missing)[:10]:
            print(f"    - {m!r}")
        errors += 1
    if dups:
        print(f"✗ {len(dups)} code(s) appear in more than one canonical label")
        errors += 1
    if extras:
        print(f"✗ {len(extras)} code(s) in consolidated not present in source")
        errors += 1

    # Invariant 2: canonical labels are unique
    labels = cons["canonical_label"].tolist()
    if len(set(labels)) != len(labels):
        print("✗ duplicate canonical labels")
        errors += 1

    # Invariant 3: passage_ids well-formed
    bad = 0
    for _, row in cons.iterrows():
        for pid in json.loads(row["passage_ids"]):
            if not PASSAGE_ID_PATTERN.match(pid):
                bad += 1
                if bad <= 5:
                    print(f"    malformed passage_id: {pid!r}")
    if bad:
        print(f"✗ {bad} malformed passage_id(s)")
        errors += 1

    # Invariant 4: confirmed_by non-empty on every row
    empty_conf = (cons["confirmed_by"].str.strip() == "").sum()
    if empty_conf:
        print(f"✗ {empty_conf} row(s) with empty confirmed_by")
        errors += 1

    if errors == 0:
        ratio = len(cons) / len(raw_codes) if raw_codes else 0
        print(f"✓ DoD passed — {len(cons)} canonical labels from "
              f"{len(raw_codes)} unique pass-1 codes "
              f"(compression ratio {ratio:.2f})")
        if not (0.15 <= ratio <= 0.40):
            print(f"  ⚠ compression ratio outside typical 0.15–0.40 band")
        return 0
    print(f"\n✗ {errors} invariant violation(s).")
    return 1


# ---------------------------------------------------------------------------
# --stats path — compression ratio + cluster-size histogram
# ---------------------------------------------------------------------------
def run_report(out_path: Path | None = None) -> int:
    """Read .consolidate_state.json and emit a Markdown progress snapshot.

    Read-only — safe to invoke while an interactive session is running (the
    state file is written atomically via tmp-replace in `save_state`).
    """
    out = out_path or PROGRESS_MD
    if not STATE_JSON.exists():
        print(f"✗ {STATE_JSON} not found — no session state to report on.",
              file=sys.stderr)
        return 1
    try:
        state = json.loads(STATE_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"✗ could not read state file: {exc}", file=sys.stderr)
        return 1

    clusters = state.get("clusters", [])
    if not clusters:
        print("✗ state file has no clusters.", file=sys.stderr)
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_render_progress_md(state), encoding="utf-8")
    status_counts: Counter[str] = Counter(c["status"] for c in clusters)
    approved = [c for c in clusters if c["status"] == "approved"]
    by_rater = [c for c in approved if c["confirmed_by"] != "auto-singleton"]
    by_auto = [c for c in approved if c["confirmed_by"] == "auto-singleton"]
    print(f"Written: {out.relative_to(ROOT)} ({out.stat().st_size:,} bytes)")
    print(f"Summary: approved={status_counts.get('approved', 0)} "
          f"pending={status_counts.get('pending', 0)} "
          f"split={status_counts.get('split', 0)} "
          f"merged={status_counts.get('merged', 0)} "
          f"(rater-confirmed={len(by_rater)}, auto={len(by_auto)})")
    return 0


def _render_progress_md(state: dict) -> str:
    """Pure function: state → markdown string. No I/O, no stdout.

    Produces a *flat* listing of every cluster in the session state, sorted
    by cluster ID ascending. Each entry shows exactly the four fields
    requested: cluster ID, proposed label, member codes (all of them, no
    truncation), and status. Supplementary info (final label when renamed,
    confirmation trail, merge/split notes) is included where it exists in
    state so the listing remains a faithful audit artefact.
    """
    clusters = state.get("clusters", [])
    status_counts: Counter[str] = Counter(c["status"] for c in clusters)
    approved = [c for c in clusters if c["status"] == "approved"]
    by_rater = [c for c in approved if c["confirmed_by"] != "auto-singleton"]
    by_auto = [c for c in approved if c["confirmed_by"] == "auto-singleton"]
    total_members = sum(len(c["members"]) for c in clusters)

    md: list[str] = []
    # ---------- Header ----------
    md.append("# Task 4.1 — Full Cluster Listing")
    md.append("")
    md.append(f"> Generated: `{utcnow_iso()}`")
    md.append(f"> State file: `{STATE_JSON.relative_to(ROOT)}`")
    md.append(f"> Session started: `{state.get('started_at', '?')}`  |  "
              f"rater: `{state.get('rater', '?')}`  |  "
              f"threshold: `{state.get('threshold', '?')}`  |  "
              f"LLM: `{state.get('llm_model', '?')}`")
    md.append("")

    # ---------- Summary ----------
    md.append("## Summary")
    md.append("")
    md.append("| Status | Count | % |")
    md.append("|---|---:|---:|")
    total = len(clusters)
    for k in ["pending", "approved", "split", "merged"]:
        n = status_counts.get(k, 0)
        pct = (100.0 * n / total) if total else 0.0
        md.append(f"| {k} | {n} | {pct:.1f} |")
    md.append(f"| **total** | **{total}** | **100.0** |")
    md.append("")
    md.append(f"Approved breakdown: rater-confirmed = **{len(by_rater)}**, "
              f"auto-singleton = **{len(by_auto)}**.")
    md.append(f"Total member pass-1 codes across all clusters: "
              f"**{total_members}**.")
    md.append("")

    # ---------- All clusters, flat listing, cluster_id ascending ----------
    md.append("## All clusters")
    md.append("")
    md.append("Every cluster in the session state is listed below, sorted by "
              "cluster ID ascending. Each entry shows the four required "
              "fields: **cluster ID**, **proposed label**, **member codes** "
              "(every member, no truncation), and **status**.")
    md.append("")

    for c in sorted(clusters, key=lambda x: x["cluster_id"]):
        cid = c["cluster_id"]
        proposed = c.get("proposed_label") or "(no proposed label)"
        status = c["status"]
        size = len(c["members"])
        size_flag = "  ⚠ large" if size > 50 else ""

        # Heading: Cluster id + size
        md.append(f"### Cluster {cid}  (size {size}){size_flag}")
        md.append(f"**Status:** `{status}`")
        md.append(f"**Proposed label:** \"{proposed}\"")

        # Optional context lines — only shown when present in state
        final = c.get("final_label", "") or ""
        if final and final != proposed:
            md.append(f"**Final label:** \"{final}\"  "
                      f"*(renamed by rater)*")
        if status == "approved":
            conf_by = c.get("confirmed_by", "")
            conf_at = c.get("confirmed_at", "")
            if conf_by:
                md.append(f"*Confirmed by* `{conf_by}` *at* `{conf_at}`")
        notes = c.get("notes", "") or ""
        if notes and notes != "renamed by rater":
            md.append(f"*Note:* {notes}")
        md.append("")

        # Member codes — every one, no cap
        md.append(f"Member codes ({size}):")
        for m in c["members"]:
            md.append(f"  - `{m}`")
        md.append("")

    return "\n".join(md) + "\n"


def run_stats() -> int:
    if not CONSOLIDATED_CSV.exists():
        print(f"✗ {CONSOLIDATED_CSV} not found.")
        return 1
    cons = pd.read_csv(CONSOLIDATED_CSV, dtype=str).fillna("")
    raw = pd.read_csv(OPEN_CODES_CSV, dtype=str).fillna("")
    raw_codes = [c for c in raw["descriptive_code"].unique() if c.strip()]
    sizes = cons["cluster_size"].astype(int)
    print(f"Canonical labels      : {len(cons)}")
    print(f"Unique pass-1 codes   : {len(raw_codes)}")
    print(f"Compression ratio     : {len(cons) / max(1, len(raw_codes)):.3f}")
    print(f"Cluster size min/med/max: "
          f"{sizes.min()} / {int(sizes.median())} / {sizes.max()}")
    buckets = [(1, 2), (2, 3), (3, 5), (5, 10),
               (10, 25), (25, 50), (50, int(sizes.max()) + 1)]
    print("Size histogram:")
    for lo, hi in buckets:
        cnt = ((sizes >= lo) & (sizes < hi)).sum()
        label = f"[{lo},{hi})"
        print(f"  {label:>10}  {cnt:>4}  {'█' * min(40, cnt)}")
    return 0


# ---------------------------------------------------------------------------
# .env / API-key loader (mirrors code/extraction.py)
# ---------------------------------------------------------------------------
def load_api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("GOOGLE_API_KEY=") and len(line) > len("GOOGLE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError("GOOGLE_API_KEY not found in env or .env")


# ---------------------------------------------------------------------------
# Dry-run summary
# ---------------------------------------------------------------------------
def print_dry_run(state: dict) -> None:
    clusters = state["clusters"]
    singletons = sum(1 for c in clusters if len(c["members"]) == 1)
    multi = len(clusters) - singletons
    sizes = [len(c["members"]) for c in clusters]
    print("\n=== DRY RUN summary (no files written) ===")
    print(f"Clusters: {len(clusters)} "
          f"(singletons {singletons}, multi-member {multi})")
    print(f"Largest cluster size: {max(sizes) if sizes else 0}")
    print(f"Total members: {sum(sizes)}")
    top = sorted(clusters, key=lambda c: -len(c["members"]))[:10]
    print("\nTop 10 clusters by size:")
    for c in top:
        print(f"  #{c['cluster_id']:>4}  size {len(c['members']):>3}  "
              f"→ {c['proposed_label']!r}")
        for m in c["members"][:3]:
            print(f"            - {m}")
        if len(c["members"]) > 3:
            print(f"            ... +{len(c['members']) - 3} more")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task 4.1 — consolidate pass-1 codes into canonical labels")
    p.add_argument("--resume", action="store_true",
                   help="Continue a prior interactive session.")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                   help=f"Cosine-distance threshold (default {DEFAULT_THRESHOLD}).")
    p.add_argument("--dry-run", action="store_true",
                   help="Cluster + propose labels, print summary, exit.")
    p.add_argument("--rater", type=str,
                   default=os.environ.get("RATER_INITIALS", "AT"),
                   help="Rater initials for confirmed_by (default $RATER_INITIALS or AT).")
    p.add_argument("--verify", action="store_true",
                   help="Check DoD invariants on existing consolidated_codes.csv.")
    p.add_argument("--stats", action="store_true",
                   help="Print compression ratio and cluster-size histogram.")
    p.add_argument("--report", action="store_true",
                   help="Write a Markdown progress snapshot (read-only; safe during active session).")
    p.add_argument("--report-out", type=str, default=None,
                   help=f"Output path for --report (default {PROGRESS_MD.relative_to(ROOT)}).")
    p.add_argument("--embed-model", type=str, default=DEFAULT_EMBED_MODEL,
                   help=f"sentence-transformers model (default {DEFAULT_EMBED_MODEL}).")
    p.add_argument("--llm-model", type=str, default=DEFAULT_LLM_MODEL,
                   help=f"Gemini model for label proposal (default {DEFAULT_LLM_MODEL}).")
    p.add_argument("--input", type=str, default=None,
                   help="Override input CSV path (for fixture tests).")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()

    print("=" * 72)
    print("  Task 4.1 — Consolidate pass-1 codes (Cruzes & Dybå Step 3)")
    print("=" * 72)

    if args.verify:
        input_csv = Path(args.input).resolve() if args.input else None
        return run_verify(input_csv)
    if args.stats:
        return run_stats()
    if args.report:
        out = Path(args.report_out).resolve() if args.report_out else None
        return run_report(out)

    csv_path = Path(args.input).resolve() if args.input else OPEN_CODES_CSV
    raw = load_open_codes(csv_path)

    # Drop rows with empty descriptive_code; log them for audit
    empty_mask = raw["descriptive_code"].str.strip() == ""
    if empty_mask.any():
        SYNTH_DIR.mkdir(parents=True, exist_ok=True)
        raw[empty_mask].to_csv(SKIPPED_CSV, index=False, quoting=csv.QUOTE_ALL)
        print(f"Skipped {empty_mask.sum()} row(s) with empty descriptive_code "
              f"(logged to {SKIPPED_CSV.relative_to(ROOT)})")
    raw = raw[~empty_mask].copy()

    unique_codes = sorted(raw["descriptive_code"].unique())
    print(f"Loaded {len(raw)} open-code row(s); "
          f"{len(unique_codes)} unique descriptive_code(s).")

    this_hash = input_sha1(unique_codes)

    # --- Resume path ---
    if args.resume:
        state = load_state()
        if state is None:
            print(f"✗ no state file at {STATE_JSON}; nothing to resume.",
                  file=sys.stderr)
            return 1
        if state.get("input_csv_sha1") != this_hash:
            print(
                f"✗ input has changed since prior session "
                f"(sha1 {state.get('input_csv_sha1','?')[:10]} → "
                f"{this_hash[:10]}). Start a fresh run.",
                file=sys.stderr)
            return 1
        print(f"Resumed session started {state.get('started_at','?')}; "
              f"{sum(1 for c in state['clusters'] if c['status']=='pending')} "
              f"cluster(s) still pending.")
        interactive_review(state, args.rater)
        _finalize_if_complete(state)
        return 0

    # --- Fresh run ---
    # Build maps: descriptive_code → list of in_vivo codes, passage_ids
    desc_to_invivo: dict[str, list[str]] = {}
    desc_to_passages: dict[str, list[str]] = {}
    for _, row in raw.iterrows():
        d = row["descriptive_code"]
        v = row["in_vivo_code"]
        desc_to_invivo.setdefault(d, []).append(v)
        desc_to_passages.setdefault(d, []).append(
            f"{row['paper_id']}:{row['passage_id']}")
    # Dedupe and keep stable order
    for d in desc_to_invivo:
        desc_to_invivo[d] = list(dict.fromkeys(desc_to_invivo[d]))

    embeddings = compute_embeddings(unique_codes, args.embed_model)
    labels = cluster_embeddings(embeddings, args.threshold)
    n_clusters = int(labels.max()) + 1 if len(labels) else 0
    print(f"Clustered {len(unique_codes)} codes → {n_clusters} group(s) "
          f"at threshold {args.threshold}.")

    clusters = build_clusters(
        unique_codes, labels, desc_to_invivo, desc_to_passages)

    # --- Phase C: label proposal ---
    # Singletons auto-approved with their own descriptive as label.
    # Multi-member clusters go through the LLM.
    needs_llm = [c for c in clusters if len(c["members"]) > 1]
    for c in clusters:
        if len(c["members"]) == 1:
            c["proposed_label"] = c["members"][0].title()
            c["status"] = "approved"
            c["final_label"] = c["proposed_label"]
            c["confirmed_at"] = utcnow_iso()
            c["confirmed_by"] = "auto-singleton"

    if needs_llm:
        from google import genai
        print(f"Proposing labels for {len(needs_llm)} multi-member cluster(s) "
              f"via {args.llm_model}...")
        client = genai.Client(api_key=load_api_key())
        for i, c in enumerate(needs_llm, 1):
            c["proposed_label"] = propose_label_llm(
                client, args.llm_model, c["members"], c["in_vivo"])
            if i % 20 == 0 or i == len(needs_llm):
                print(f"  [{i}/{len(needs_llm)}] clusters labelled")
    else:
        print("No multi-member clusters — all singletons, all auto-approved.")

    state = {
        "schema_version": 1,
        "input_csv_sha1": this_hash,
        "started_at": utcnow_iso(),
        "rater": args.rater,
        "threshold": args.threshold,
        "embed_model": args.embed_model,
        "llm_model": args.llm_model,
        "clusters": clusters,
    }

    if args.dry_run:
        print_dry_run(state)
        return 0

    save_state(state)
    print(f"State saved → {STATE_JSON.relative_to(ROOT)}")
    print(f"Starting interactive review ({len(needs_llm)} clusters need rater "
          f"input; {len(clusters) - len(needs_llm)} singletons auto-approved).\n")
    interactive_review(state, args.rater)
    _finalize_if_complete(state)
    return 0


def _finalize_if_complete(state: dict) -> None:
    if all(c["status"] in {"approved", "split", "merged"}
           for c in state["clusters"]):
        n = emit_consolidated(state)
        print(f"\n✓ wrote {n} canonical row(s) → "
              f"{CONSOLIDATED_CSV.relative_to(ROOT)}")
        print(f"  run  python code/coding_consolidate.py --verify  "
              f"to check DoD invariants")
    else:
        remaining = sum(1 for c in state["clusters"] if c["status"] == "pending")
        print(f"\n{remaining} cluster(s) still pending. "
              f"Re-run --resume to continue.")


if __name__ == "__main__":
    sys.exit(main())
