"""Task 4.2 Step 4 (LLM-assisted) — Pre-classify all 707 canonical labels
with Gemini, then run the same interactive rater confirmation loop with
the LLM suggestion + explanation shown above the action prompt.

Design: design/4_2_taxonomy_classify_llmassist.md

Key differences vs code/taxonomy_classify.py:
  - Phase A: batched Gemini pre-pass classifies every canonical label
    (unless already cached). Cache lives at
    artifacts/synthesis/.taxonomy_classify_llmsuggest.json.
  - Phase B: above the standard action menu, the rater sees the LLM's
    suggested mode (1-5 or r) and a 1-2 sentence explanation. The action
    menu is unchanged: [1-5/r/?/v/s/q]. If the rater's choice differs
    from the LLM's suggestion, a note "overrode LLM X -> Y" is
    auto-appended for the audit trail.
  - State is SHARED with the base script
    (artifacts/synthesis/.taxonomy_classify_state.json) so prior rater
    work (Step-3 placements + any manual Step-4 rows) is preserved;
    rows are augmented with llm_mode / llm_explanation on load.

CLI:
    python code/taxonomy_classify_llmassist.py                 # pre-pass + loop
    python code/taxonomy_classify_llmassist.py --resume        # same, explicit
    python code/taxonomy_classify_llmassist.py --refresh-llm   # re-run pre-pass
    python code/taxonomy_classify_llmassist.py --batch 10
    python code/taxonomy_classify_llmassist.py --llm-model gemini-2.5-pro
    python code/taxonomy_classify_llmassist.py --pre-only      # stop after pre-pass
    python code/taxonomy_classify_llmassist.py --stats
    python code/taxonomy_classify_llmassist.py --verify
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Project setup — reuse helpers from the base classifier and Task 4.1
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.taxonomy_classify import (                       # noqa: E402
    MODES, MODE_KEYS, SYNTH_DIR, CONSOLIDATED_CSV, TAXONOMY_MD,
    PASSAGES_DIR, CLASSIFY_CSV, COLUMNS, STATE_JSON,
    load_labels, labels_placed_in_taxonomy, view_passages,
    print_stats, tally, emit_csv, run_verify, utcnow_iso, print_menu,
    load_state, save_state, initial_state as base_initial_state,
)
from code.coding_consolidate import load_api_key            # noqa: E402

# ---------------------------------------------------------------------------
# LLM pre-pass artefacts
# ---------------------------------------------------------------------------
LLM_SUGGEST_JSON       = SYNTH_DIR / ".taxonomy_classify_llmsuggest.json"
RESID_SUBSUGGEST_JSON  = SYNTH_DIR / ".taxonomy_classify_resid_subsuggest.json"

# Default model. `gemini-3.1-pro-preview` is the best-quality Gemini
# currently exposed; override at the CLI with --llm-model if you want
# `gemini-2.5-pro` (stable GA) or `gemini-3-flash-preview` (cheapest).
DEFAULT_LLM_MODEL  = "gemini-3.1-pro-preview"
DEFAULT_BATCH_SIZE = 20
VALID_MODE_KEYS    = {"1", "2", "3", "4", "5", "r"}
VALID_RESID_SUBS   = {"outcome", "affordance", "constraint", "meta"}


LLM_SYSTEM_PROMPT = """You are a qualitative-research assistant classifying canonical labels from a thematic synthesis of empirical papers on AI agents in software engineering.

Classify each canonical label into EXACTLY ONE of 5 interaction modes along a delegation-depth axis (Assistive -> Autonomous), or mark it as Residuals / Cross-cutting if it describes outcomes, affordances, constraints, or meta-observations rather than a mode of interaction.

MODES (choose one key per label):

1 - Inline Completion
    Human authors code in-flow; AI produces short inline continuations
    (tokens to a few lines) that the human accepts, modifies, or rejects
    immediately. Unit = single accept/reject decision. No conversational
    turn required.
    IS: autocomplete, Copilot-style inline suggestions, accept/reject.
    IS NOT: iterative prompting via a chat (that is Mode 2).

2 - Conversational Prompting
    Human describes intent in natural language; AI responds per turn;
    human iterates over multiple turns until output is usable.
    Unit = prompt-response turn.
    IS: chat, iterative prompt refinement, dialogue, turn-taking
        including debugging via dialogue.
    IS NOT: inline accept/reject (Mode 1); visual surface (Mode 3);
        multi-step autonomous task execution (Mode 5).

3 - Visual / Declarative Composition
    Human composes software via visual / declarative surface - drag-drop
    blocks, flow-chart nodes, configuration forms,
    natural-language-to-workflow pipelines. AI generates underlying
    implementation (logic, data models, workflow steps).
    Unit = declarative specification, NOT a free-text prompt.
    IS: low-code / no-code / visual-AI-platform evidence.
    IS NOT: free-text chat (Mode 2).

4 - Review & Validation
    AI or human performs an EVALUATIVE reading of code / AI output -
    detecting hallucinations, assessing quality, localising defects,
    providing or soliciting feedback, trust / security judgement.
    Unit = evaluative judgement.
    IS: hallucination detection, code review, quality assessment,
        feedback generation about code, over-reliance critique,
        trust/security concerns about AI output.
    IS NOT: generation of new code (Modes 1/2/5).

5 - Delegated Task Execution
    Human scopes a task (generate tests, fix a bug, refactor a module,
    build a workflow); AI executes end-to-end or across multiple sub-steps;
    human reviews at checkpoints or at completion.
    Unit = the TASK, not the prompt or suggestion.
    IS: automated test suite generation, automated bug triage/fix, agentic
        workflows, multi-step code synthesis at task scope, autonomous
        orchestration.
    IS NOT: single-turn prompt-response (Mode 2); token-level suggestion
        (Mode 1).

r - Residuals / Cross-cutting
    Not a mode of interaction. Describes one of:
      - OUTCOME (productivity gain, accuracy change, satisfaction)
      - AFFORDANCE / SURFACE (IDE integration, toolchain depth)
      - CONSTRAINT (context window, cognitive load)
      - META-OBSERVATION (adoption drivers, barriers)
    Use r when the label describes HOW WELL an interaction went, or
    the conditions around an interaction, rather than the interaction
    itself.

RESIDUALS TESTS (apply in order before choosing r):
    1. Axis test: where on Assistive -> Autonomous does it sit? No answer
       -> Residuals.
    2. WHAT-vs-HOW-WELL: description of interaction (mode) vs evaluation
       of interaction (Residuals).
    3. Mode-specificity: would this label apply equally across all 5
       modes? If yes -> Residuals.
    4. 60% rule: if >=60% of the member pass-1 codes describe one specific
       mode, assign that mode - NOT Residuals.

OUTPUT FORMAT (strict):
Return a single JSON object with one key, "classifications", whose value
is an array. One element per input label, in input order. Each element:
    {
        "canonical_label": "<exact text, unchanged>",
        "mode":            "<one of: 1, 2, 3, 4, 5, r>",
        "explanation":     "<1-2 sentences, <=30 words, naming the
                             discriminating signal>"
    }

Do NOT include any text outside the JSON object. Do NOT add extra keys.
The response must start with '{' and end with '}'."""


# ---------------------------------------------------------------------------
# LLM suggestion cache
# ---------------------------------------------------------------------------
def load_llm_cache() -> dict:
    if not LLM_SUGGEST_JSON.exists():
        return {}
    try:
        return json.loads(LLM_SUGGEST_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  [warn] llmsuggest cache unreadable: {exc}", file=sys.stderr)
        return {}


def save_llm_cache(cache: dict) -> None:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LLM_SUGGEST_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(LLM_SUGGEST_JSON)


def _format_label_for_prompt(row: pd.Series) -> dict:
    try:
        members = json.loads(row["pass1_codes"]) if row["pass1_codes"] else []
    except json.JSONDecodeError:
        members = []
    return {
        "canonical_label": row["canonical_label"],
        "cluster_size": int(row["cluster_size"]),
        "member_codes": members[:12],  # cap to keep input tokens modest
    }


def _extract_json_object(text: str):
    """Be permissive: find the first '{' and last '}' and parse between."""
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _validate_classification(item, expected_labels):
    if not isinstance(item, dict):
        return None
    lbl = item.get("canonical_label", "")
    mode = item.get("mode", "")
    if lbl not in expected_labels:
        return None
    if mode not in VALID_MODE_KEYS:
        return None
    return lbl


def llm_classify_batch(client, model: str, batch: list) -> dict:
    """Return {canonical_label: {mode, explanation}} for each label in batch.

    On parse failure, recursively splits the batch; final single-label
    failure yields mode="" with a fallback explanation (rater sees it).
    """
    if not batch:
        return {}
    user_payload = {"labels": [
        {"canonical_label": b["canonical_label"],
         "cluster_size": b["cluster_size"],
         "member_codes": b["member_codes"]}
        for b in batch
    ]}
    user = (f"Input labels (classify each; output array in same order):\n"
            f"```json\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}"
            f"\n```")
    expected_labels = [b["canonical_label"] for b in batch]

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[LLM_SYSTEM_PROMPT + "\n\n" + user],
                config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            parsed = _extract_json_object(response.text or "")
            if parsed and isinstance(parsed.get("classifications"), list):
                result = {}
                for item in parsed["classifications"]:
                    lbl = _validate_classification(item, expected_labels)
                    if lbl is None:
                        continue
                    result[lbl] = {
                        "mode": item["mode"],
                        "explanation": (
                            item.get("explanation") or ""
                        ).strip()[:240],
                    }
                if len(result) == len(batch):
                    return result
        except Exception as exc:
            print(f"    [warn] batch call failed (attempt {attempt + 1}): {exc}",
                  file=sys.stderr)
        time.sleep(1.0 + attempt)

    # Fallback: recurse on smaller batches
    if len(batch) > 1:
        mid = len(batch) // 2
        left = llm_classify_batch(client, model, batch[:mid])
        right = llm_classify_batch(client, model, batch[mid:])
        return {**left, **right}

    # Single-label persistent failure - punt to the rater.
    return {batch[0]["canonical_label"]: {
        "mode": "",
        "explanation": "LLM unable to classify - rater review required.",
    }}


def run_pre_pass(labels: pd.DataFrame, model: str, batch_size: int,
                 refresh: bool) -> dict:
    cache = {} if refresh else load_llm_cache()
    all_labels = labels["canonical_label"].tolist()
    to_do = [l for l in all_labels if l not in cache]
    if not to_do:
        print(f"LLM cache complete - {len(cache)} label(s) already cached.")
        return cache
    print(f"LLM pre-pass: {len(to_do)} label(s) to classify "
          f"({len(cache)} already cached) via {model}.")

    try:
        from google import genai
    except ImportError as e:
        raise ImportError("google-genai not installed. "
                          "Run: pip install google-genai") from e
    client = genai.Client(api_key=load_api_key())

    to_do_rows = labels[labels["canonical_label"].isin(to_do)].copy()
    batches: list = []
    cur: list = []
    for _, row in to_do_rows.iterrows():
        cur.append(_format_label_for_prompt(row))
        if len(cur) >= batch_size:
            batches.append(cur)
            cur = []
    if cur:
        batches.append(cur)

    classified = 0
    for i, batch in enumerate(batches, 1):
        t0 = time.time()
        results = llm_classify_batch(client, model, batch)
        cache.update(results)
        classified += len(results)
        save_llm_cache(cache)
        dt = time.time() - t0
        print(f"  [{i}/{len(batches)}] batch of {len(batch)} -> "
              f"{len(results)} classified in {dt:0.1f}s. "
              f"Running total {classified}/{len(to_do)}.")

    unresolved = [l for l in to_do
                  if l not in cache or not cache[l].get("mode")]
    if unresolved:
        print(f"  [warn] {len(unresolved)} label(s) unresolved after pre-pass; "
              f"rater will see empty suggestions.", file=sys.stderr)
    return cache


# ---------------------------------------------------------------------------
# State augmentation — share .taxonomy_classify_state.json with the base
# script so prior Step-3 placements + any manual Step-4 rows are kept.
# ---------------------------------------------------------------------------
def augment_state_with_llm(state: dict, cache: dict) -> None:
    """Attach llm_mode / llm_explanation to every row from the cache.

    Existing row keys are left intact; unknown labels get empty fields.
    """
    for r in state["rows"]:
        s = cache.get(r["canonical_label"], {})
        r["llm_mode"] = s.get("mode", "")
        r["llm_explanation"] = s.get("explanation", "")
    state["variant"] = "llmassist"
    state.setdefault("schema_version", 1)


# ---------------------------------------------------------------------------
# Interactive loop — same menu as base, with LLM suggestion shown above.
# ---------------------------------------------------------------------------
def mode_name(key: str) -> str:
    for m in MODES:
        if m["key"] == key:
            return m["name"]
    return "(unknown)"


def prompt_label(row: dict, idx: int, total: int):
    """Return an action key, '__STATS__', or None (quit).

    Display order:
        label + cluster_size
        member pass-1 codes
        LLM suggestion + explanation (if any)
        action prompt [1-5/r/?/v/s/q]
    """
    try:
        members = json.loads(row["pass1_codes"]) if row["pass1_codes"] else []
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

    llm_mode = (row.get("llm_mode") or "").strip()
    llm_expl = (row.get("llm_explanation") or "").strip()
    print()
    if llm_mode and llm_mode in VALID_MODE_KEYS:
        print(f"  LLM suggests [{llm_mode}] {mode_name(llm_mode)}")
        if llm_expl:
            print(f"  LLM explains: {llm_expl}")
    else:
        msg = llm_expl or "(no LLM suggestion available for this label)"
        print(f"  LLM suggests: <none>  -  {msg}")

    while True:
        raw = input("action [1-5/r/?/v/s/q] "
                    "(append ' <note>' for a boundary-case note): ").strip()
        if not raw:
            continue
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
            # If the rater overrode a valid LLM suggestion, auto-note it
            # for the audit trail (skip when rater's pick == LLM's pick
            # and when no LLM suggestion existed).
            if (llm_mode and llm_mode in VALID_MODE_KEYS
                    and cmd in VALID_MODE_KEYS and cmd != llm_mode):
                auto_note = f"overrode LLM {llm_mode} -> {cmd}"
                row["notes"] = (row.get("notes", "") + " | " + auto_note
                                ).strip(" |")
            if note_text:
                row["notes"] = (row.get("notes", "") + " | " + note_text
                                ).strip(" |")
            return cmd
        print(f"  unknown action {cmd!r}; valid: 1 2 3 4 5 r ? v s q "
              f"(optionally + space + note)")


def interactive_classify(state: dict, rater: str) -> None:
    rows = state["rows"]
    while True:
        pending = [r for r in rows if r["mode"] in ("", "?")]
        if not pending:
            break
        pending.sort(key=lambda r: (-r["cluster_size"], r["canonical_label"]))
        row = pending[0]
        idx = len(rows) - len(pending) + 1

        action = prompt_label(row, idx, len(rows))
        if action is None:
            save_state(state)
            print("\nSession saved - re-run to continue.")
            return
        if action == "__STATS__":
            print_stats(state)
            continue
        row["mode"] = action
        row["confirmed_by"] = rater
        row["confirmed_at"] = utcnow_iso()
        row["source"] = "step4_llmassist"
        save_state(state)
    print("\n[OK] all labels classified.")
    print_stats(state)


# ---------------------------------------------------------------------------
# Residuals sub-categorisation (Step 4.5) — see design/4_2_residuals_subcategorise.md
# ---------------------------------------------------------------------------
RESID_SYSTEM_PROMPT = """You are classifying canonical labels that have already been determined to be Residuals / Cross-cutting — they describe something ABOUT an interaction, not an interaction itself.

Assign EACH input label to EXACTLY ONE of four sub-categories:

outcome    - Measures an effect of an interaction: productivity, accuracy,
             velocity, satisfaction, error-reduction, learning gain.
             Examples: "Accelerated Engineering Velocity", "Positive User
             Sentiment", "Impact On Accuracy Outcomes".

affordance - Describes an enabling surface, integration, or tooling depth
             that shapes interactions without being one. Examples:
             "Workflow Integration Depth", "Integrated Development
             Tooling Workflows".

constraint - Describes something that LIMITS or constrains the interaction:
             context window, cognitive load, latency, skill gap,
             restricted scope. Examples: "Restricted Contextual Scope",
             "Substantial Processing Lag", "Regulating Cognitive
             Processing Demands".

meta       - Research framing, methodology, or adoption driver/inhibitor
             study finding — a meta-observation about the phenomenon
             rather than a measurement, surface, or limit. Examples:
             "Adoption Drivers And Inhibitors", "Survey Research
             Procedures".

TIE-BREAK RULES (apply in order):
 1. Effect/measurement -> outcome.
 2. Enabling surface/tooling -> affordance.
 3. Limiting condition -> constraint.
 4. Framing/driver/inhibitor -> meta.
 5. If outcome vs. meta is genuinely ambiguous, prefer outcome (concreter).
 6. If affordance vs. constraint is genuinely ambiguous, inspect the
    valence: enabling -> affordance; limiting -> constraint.

OUTPUT FORMAT (strict):
Return a single JSON object with one key, "subclassifications", whose value
is an array. One element per input label, in input order. Each element:
    {
        "canonical_label": "<exact text, unchanged>",
        "subcategory":     "<one of: outcome, affordance, constraint, meta>",
        "explanation":     "<1 sentence, <=30 words, naming the
                             discriminating signal>"
    }

Do NOT include any text outside the JSON object. Do NOT add extra keys.
The response must start with '{' and end with '}'."""


def load_resid_cache() -> dict:
    if not RESID_SUBSUGGEST_JSON.exists():
        return {}
    try:
        return json.loads(RESID_SUBSUGGEST_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  [warn] resid cache unreadable: {exc}", file=sys.stderr)
        return {}


def save_resid_cache(cache: dict) -> None:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    tmp = RESID_SUBSUGGEST_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(RESID_SUBSUGGEST_JSON)


def _validate_sub(item, expected_labels):
    if not isinstance(item, dict):
        return None
    lbl = item.get("canonical_label", "")
    sub = (item.get("subcategory") or "").strip().lower()
    if lbl not in expected_labels:
        return None
    if sub not in VALID_RESID_SUBS:
        return None
    return lbl


def llm_subclassify_batch(client, model: str, batch: list) -> dict:
    """Return {canonical_label: {subcategory, explanation}} per batch.

    Mirrors llm_classify_batch's recurse-on-failure pattern.
    """
    if not batch:
        return {}
    user_payload = {"labels": [
        {"canonical_label": b["canonical_label"],
         "cluster_size": b["cluster_size"],
         "member_codes": b["member_codes"]}
        for b in batch
    ]}
    user = (f"Input Residuals labels (assign each a sub-category; output array "
            f"in same order):\n```json\n"
            f"{json.dumps(user_payload, ensure_ascii=False, indent=2)}\n```")
    expected = [b["canonical_label"] for b in batch]

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[RESID_SYSTEM_PROMPT + "\n\n" + user],
                config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            parsed = _extract_json_object(response.text or "")
            if parsed and isinstance(parsed.get("subclassifications"), list):
                result: dict = {}
                for item in parsed["subclassifications"]:
                    lbl = _validate_sub(item, expected)
                    if lbl is None:
                        continue
                    result[lbl] = {
                        "subcategory": (item["subcategory"] or "").strip().lower(),
                        "explanation": (item.get("explanation") or "")
                                       .strip()[:240],
                    }
                if len(result) == len(batch):
                    return result
        except Exception as exc:
            print(f"    [warn] sub batch failed (attempt {attempt + 1}): {exc}",
                  file=sys.stderr)
        time.sleep(1.0 + attempt)

    if len(batch) > 1:
        mid = len(batch) // 2
        left = llm_subclassify_batch(client, model, batch[:mid])
        right = llm_subclassify_batch(client, model, batch[mid:])
        return {**left, **right}

    return {batch[0]["canonical_label"]: {
        "subcategory": "",
        "explanation": "LLM unable to sub-classify - defaulted to empty.",
    }}


def run_resid_subpass(model: str, batch_size: int, refresh: bool) -> int:
    """Run the Residuals sub-categorisation pass end-to-end.

    Reads taxonomy_classifications.csv, picks mode=='r' rows, LLM-classifies
    uncached ones into {outcome, affordance, constraint, meta}, writes the
    results back to the CSV with two new columns. Returns 0 on success.
    """
    if not CLASSIFY_CSV.exists():
        print(f"[x] {CLASSIFY_CSV} not found - run Step 4 first.",
              file=sys.stderr)
        return 1
    if not CONSOLIDATED_CSV.exists():
        print(f"[x] {CONSOLIDATED_CSV} not found - run Task 4.1 first.",
              file=sys.stderr)
        return 1

    cls = pd.read_csv(CLASSIFY_CSV, dtype=str).fillna("")
    cons = pd.read_csv(CONSOLIDATED_CSV, dtype=str).fillna("")
    cons["cluster_size"] = cons["cluster_size"].astype(int)
    cons_by_label = {r["canonical_label"]: r for _, r in cons.iterrows()}

    residuals = cls[cls["mode"] == "r"].copy()
    n_resid = len(residuals)
    if n_resid == 0:
        print("[x] no Residuals (mode='r') rows found - nothing to do.",
              file=sys.stderr)
        return 1
    print(f"Residuals to sub-categorise: {n_resid}")

    cache = {} if refresh else load_resid_cache()
    cached_now = sum(1 for lbl in residuals["canonical_label"]
                     if lbl in cache and cache[lbl].get("subcategory") in VALID_RESID_SUBS)
    to_do = [lbl for lbl in residuals["canonical_label"]
             if lbl not in cache or cache[lbl].get("subcategory") not in VALID_RESID_SUBS]
    print(f"Cache hits: {cached_now} / {n_resid}; "
          f"to classify: {len(to_do)} via {model}.")

    if to_do:
        try:
            from google import genai
        except ImportError as e:
            raise ImportError("google-genai not installed. "
                              "Run: pip install google-genai") from e
        client = genai.Client(api_key=load_api_key())

        # Build batch payloads
        batches: list = []
        cur: list = []
        for lbl in to_do:
            cons_row = cons_by_label.get(lbl)
            if cons_row is None:
                members = []
                size = 0
            else:
                try:
                    members = json.loads(cons_row["pass1_codes"] or "[]")
                except json.JSONDecodeError:
                    members = []
                size = int(cons_row["cluster_size"])
            cur.append({
                "canonical_label": lbl,
                "cluster_size": size,
                "member_codes": members[:12],
            })
            if len(cur) >= batch_size:
                batches.append(cur)
                cur = []
        if cur:
            batches.append(cur)

        classified = 0
        for i, batch in enumerate(batches, 1):
            t0 = time.time()
            results = llm_subclassify_batch(client, model, batch)
            cache.update(results)
            classified += len(results)
            save_resid_cache(cache)
            dt = time.time() - t0
            print(f"  [{i}/{len(batches)}] sub-batch of {len(batch)} -> "
                  f"{len(results)} classified in {dt:0.1f}s. "
                  f"Running total {classified}/{len(to_do)}.")

    # Backfill columns on the CSV in-place (all rows; non-Residuals stay "")
    if "residuals_subcategory" not in cls.columns:
        cls["residuals_subcategory"] = ""
    if "residuals_subexplanation" not in cls.columns:
        cls["residuals_subexplanation"] = ""

    updated = 0
    missing = []
    for idx in cls.index:
        if cls.at[idx, "mode"] != "r":
            cls.at[idx, "residuals_subcategory"] = ""
            cls.at[idx, "residuals_subexplanation"] = ""
            continue
        lbl = cls.at[idx, "canonical_label"]
        s = cache.get(lbl, {})
        sub = s.get("subcategory", "")
        if sub in VALID_RESID_SUBS:
            cls.at[idx, "residuals_subcategory"] = sub
            cls.at[idx, "residuals_subexplanation"] = s.get("explanation", "")
            updated += 1
        else:
            missing.append(lbl)

    # Atomic write — temp path then replace.
    tmp = CLASSIFY_CSV.with_suffix(".csv.tmp")
    cls.to_csv(tmp, index=False, quoting=1)  # csv.QUOTE_ALL = 1
    tmp.replace(CLASSIFY_CSV)

    # Tally
    sub_counts = cls[cls["mode"] == "r"]["residuals_subcategory"].value_counts()
    print()
    print("=" * 78)
    print(f"  RESIDUALS SUB-CATEGORY TALLY   (n={n_resid})")
    print("=" * 78)
    for k in ["outcome", "affordance", "constraint", "meta", ""]:
        n = int(sub_counts.get(k, 0))
        name = k if k else "<unresolved>"
        pct = (100.0 * n / n_resid) if n_resid else 0.0
        print(f"  [{name:<11}]  {n:>4}  ({pct:5.1f}%)")
    print("=" * 78)

    if missing:
        print(f"\n[warn] {len(missing)} Residual(s) unresolved — "
              f"re-run with --refresh-resid-llm or hand-assign.",
              file=sys.stderr)
        for m in missing[:5]:
            print(f"    - {m}", file=sys.stderr)
        return 2

    print(f"\n[OK] {updated} Residual(s) sub-categorised; "
          f"{CLASSIFY_CSV.relative_to(ROOT)} updated with "
          f"'residuals_subcategory' + 'residuals_subexplanation'.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task 4.2 Step 4 (LLM-assisted) - pre-classify all "
                    "canonical labels with Gemini, then interactively "
                    "confirm each with rater adjudication.")
    p.add_argument("--resume", action="store_true",
                   help="Continue an existing session (implicit when "
                        "state file exists).")
    p.add_argument("--rater", type=str,
                   default=os.environ.get("RATER_INITIALS", "TBS"),
                   help="Rater initials for confirmed_by (default TBS).")
    p.add_argument("--stats", action="store_true",
                   help="Print the current tally and exit.")
    p.add_argument("--verify", action="store_true",
                   help="Check partition invariants on "
                        "taxonomy_classifications.csv.")
    p.add_argument("--refresh-llm", action="store_true",
                   help="Discard the LLM cache and re-run the pre-pass.")
    p.add_argument("--batch", type=int, default=DEFAULT_BATCH_SIZE,
                   help=f"LLM batch size (default {DEFAULT_BATCH_SIZE}).")
    p.add_argument("--llm-model", type=str, default=DEFAULT_LLM_MODEL,
                   help=f"Gemini model (default {DEFAULT_LLM_MODEL}).")
    p.add_argument("--pre-only", action="store_true",
                   help="Run only the LLM pre-pass; don't enter the loop.")
    p.add_argument("--subcategorise-residuals", action="store_true",
                   help="Residuals-only post-pass: classify each mode='r' "
                        "label into {outcome, affordance, constraint, meta}. "
                        "Updates taxonomy_classifications.csv in place.")
    p.add_argument("--refresh-resid-llm", action="store_true",
                   help="Discard the Residuals sub-category cache and "
                        "re-run the sub-pass.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    print("=" * 78)
    print("  Task 4.2 Step 4 (LLM-assisted) - taxonomy classifier")
    print("=" * 78)

    if args.verify:
        return run_verify()

    # Step 4.5 — Residuals sub-categorisation runs independently of the
    # Step-4 pre-pass/loop. Exit after it finishes.
    if args.subcategorise_residuals:
        return run_resid_subpass(args.llm_model, args.batch,
                                 args.refresh_resid_llm)

    labels = load_labels()

    # ---- Load or bootstrap the SHARED state file ----
    if STATE_JSON.exists():
        state = load_state()
        if state is None:
            print(f"[x] state file unreadable at {STATE_JSON}.", file=sys.stderr)
            return 1
        print(f"Loaded shared state (started {state.get('started_at','?')}, "
              f"rater {state.get('rater','?')}). "
              f"{len(state['rows'])} rows.")
    else:
        placed = labels_placed_in_taxonomy()
        state = base_initial_state(labels, placed, args.rater)
        n_placed = sum(1 for r in state["rows"] if r["mode"])
        print(f"Fresh session. {len(labels)} total labels. "
              f"{n_placed} already placed via Step-3 strawman (skipped). "
              f"{len(labels) - n_placed} to classify.")
        save_state(state)

    # --stats is a quick read-only report; do not trigger the LLM.
    if args.stats:
        augment_state_with_llm(state, load_llm_cache())
        print_stats(state)
        return 0

    # ---- LLM pre-pass (ensures cache covers every canonical label) ----
    cache = run_pre_pass(labels, args.llm_model, args.batch, args.refresh_llm)

    # ---- Merge LLM suggestions into the rows and persist ----
    augment_state_with_llm(state, cache)
    save_state(state)

    # Summary so the rater sees the assist coverage before entering the loop.
    n_rows        = len(state["rows"])
    n_already     = sum(1 for r in state["rows"] if r["mode"])
    n_pending     = n_rows - n_already
    n_llm_valid   = sum(1 for r in state["rows"]
                        if r.get("llm_mode") in VALID_MODE_KEYS)
    n_pending_llm = sum(1 for r in state["rows"]
                        if not r["mode"]
                        and r.get("llm_mode") in VALID_MODE_KEYS)
    print()
    print(f"LLM assist coverage: {n_llm_valid}/{n_rows} labels have a "
          f"suggestion.")
    print(f"Pending for rater: {n_pending} labels "
          f"({n_pending_llm} with LLM suggestion).")

    if args.pre_only:
        print("--pre-only: pre-pass complete; not entering loop.")
        return 0

    print_menu()
    interactive_classify(state, args.rater)
    n = emit_csv(state)
    print(f"\n[OK] wrote {n} rows to {CLASSIFY_CSV.relative_to(ROOT)}")
    print("  run  python code/taxonomy_classify_llmassist.py --verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
