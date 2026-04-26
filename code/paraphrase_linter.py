"""Task 4.2 — Paraphrase linter (Cruzes & Dybå confirmability guardrail).

Rule (per design/4_2_interaction_taxonomy.md §3):
    No contiguous N-word string (default N=15) in interaction_taxonomy.md
    may appear verbatim in any file under artifacts/extraction/raw_passages/.
    A match means the rater copied a passage instead of paraphrasing it.

Exit codes:
    0  — no violations, DoD passes
    1  — ≥1 violation, DoD fails (block Phase 5 entry)

Usage:
    python code/paraphrase_linter.py
    python code/paraphrase_linter.py --n 20             # stricter
    python code/paraphrase_linter.py --target FILE      # alt. target markdown
    python code/paraphrase_linter.py --self-test
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = ROOT / "artifacts" / "synthesis" / "interaction_taxonomy.md"
PASSAGES_DIR = ROOT / "artifacts" / "extraction" / "raw_passages"

DEFAULT_N = 15
WORD_RE = re.compile(r"[a-z0-9]+")

# Strip common markdown syntax before tokenising. The goal is to compare
# the *prose* of the taxonomy against the *prose* of passages, not the
# incidental markdown formatting.
MD_STRIP_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"```.*?```", re.DOTALL), " "),          # fenced code blocks
    (re.compile(r"`[^`]*`"), " "),                       # inline code
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), " "),          # images
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),      # links → keep text
    (re.compile(r"^\s*#+\s*", re.MULTILINE), ""),        # heading markers
    (re.compile(r"^\s*[-*+]\s+", re.MULTILINE), ""),     # list bullets
    (re.compile(r"^\s*\d+\.\s+", re.MULTILINE), ""),     # numbered bullets
    (re.compile(r"[*_~]{1,3}"), ""),                     # bold/italic/strike
    (re.compile(r"^>\s*", re.MULTILINE), ""),            # blockquotes
]


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------
def strip_markdown(text: str) -> str:
    for pattern, repl in MD_STRIP_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def tokenise(text: str) -> list[str]:
    """Lowercase, alphanumeric-only tokens. Punctuation / casing do not
    let a rater sneak a verbatim copy past the linter."""
    return WORD_RE.findall(text.lower())


def line_of_ngram(text: str, ngram: tuple[str, ...]) -> int:
    """Best-effort: find the first source line number containing the
    first word of the n-gram sequence. Used for violation reporting."""
    first = ngram[0]
    for i, line in enumerate(text.splitlines(), 1):
        if first in line.lower():
            return i
    return 0


# ---------------------------------------------------------------------------
# Violation detection
# ---------------------------------------------------------------------------
def ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def build_passage_index(passages_dir: Path, n: int) -> tuple[set[tuple[str, ...]], dict[tuple[str, ...], str]]:
    """Return (all_ngrams_set, ngram → first_file map) across every
    raw_passages/*.md file. The map is keyed by the exact tuple so a
    violation can be reported with the source passage file."""
    all_set: set[tuple[str, ...]] = set()
    first_file: dict[tuple[str, ...], str] = {}
    if not passages_dir.exists():
        return all_set, first_file
    for fp in sorted(passages_dir.glob("*.md")):
        text = strip_markdown(fp.read_text(encoding="utf-8", errors="ignore"))
        tokens = tokenise(text)
        for ng in ngrams(tokens, n):
            all_set.add(ng)
            first_file.setdefault(ng, fp.name)
    return all_set, first_file


def lint(target_path: Path, passages_dir: Path, n: int) -> int:
    """Return exit code: 0 if clean, 1 if ≥1 violation."""
    if not target_path.exists():
        print(f"✗ target not found: {target_path}", file=sys.stderr)
        return 1
    if not passages_dir.exists():
        print(f"✗ passages dir not found: {passages_dir}", file=sys.stderr)
        return 1

    raw_target = target_path.read_text(encoding="utf-8", errors="ignore")
    stripped_target = strip_markdown(raw_target)
    tokens = tokenise(stripped_target)
    target_ngrams = ngrams(tokens, n)
    if not target_ngrams:
        print(f"  note: target has <{n} tokens — nothing to lint.")
        return 0

    passage_set, passage_first_file = build_passage_index(passages_dir, n)
    if not passage_set:
        print("  note: no passages indexed — DoD cannot confirm "
              "non-copying; treat as clean but document the gap.")
        return 0

    violations = sorted(target_ngrams & passage_set)
    if not violations:
        print(f"✓ paraphrase linter clean — no {n}-word string in "
              f"{target_path.relative_to(ROOT)} appears in "
              f"{passages_dir.relative_to(ROOT)}/ "
              f"({len(target_ngrams):,} target n-grams checked).")
        return 0

    print(f"✗ {len(violations)} verbatim-copy violation(s) detected "
          f"({n}-word window):\n", file=sys.stderr)
    for v in violations:
        phrase = " ".join(v)
        src = passage_first_file.get(v, "?")
        line_hint = line_of_ngram(raw_target, v)
        print(f"VIOLATION: \"{phrase}\"", file=sys.stderr)
        print(f"  — near line {line_hint} of "
              f"{target_path.relative_to(ROOT)}", file=sys.stderr)
        print(f"  — also in raw_passages/{src}", file=sys.stderr)
        print("", file=sys.stderr)
    print(f"Fix: rewrite each phrase above in your own words.",
          file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Self-test (in-memory — no files touched)
# ---------------------------------------------------------------------------
def run_self_test() -> int:
    """Exercise tokenise, ngrams, and match-finding in isolation."""
    passage = "the rater accepted every inline completion without review"
    target_clean = "participants generally took the suggestions as-is"
    target_dirty = ("before the interview we observed that "
                    "the rater accepted every inline completion without review")

    n = 5
    p_set = ngrams(tokenise(passage), n)
    clean_set = ngrams(tokenise(target_clean), n)
    dirty_set = ngrams(tokenise(target_dirty), n)

    checks = [
        ("clean vs passage should have no overlap", not (p_set & clean_set)),
        ("dirty vs passage SHOULD have overlap", bool(p_set & dirty_set)),
        ("tokeniser lowercases", tokenise("Hello WORLD") == ["hello", "world"]),
        ("tokeniser strips punct", tokenise("foo, bar.") == ["foo", "bar"]),
        ("markdown stripper kills fenced code",
         "secret" not in tokenise(strip_markdown("```\nsecret\n```"))),
        ("markdown stripper keeps link text",
         "clicktext" in tokenise(strip_markdown("[clicktext](http://x)"))),
    ]
    for desc, ok in checks:
        print(("  ✓ " if ok else "  ✗ ") + desc)
    passed = sum(1 for _, ok in checks if ok)
    print(f"self-test: {passed}/{len(checks)} "
          f"{'PASS' if passed == len(checks) else 'FAIL'}")
    return 0 if passed == len(checks) else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task 4.2 paraphrase linter — no verbatim 15-word copies")
    p.add_argument("--n", type=int, default=DEFAULT_N,
                   help=f"N-gram length (default {DEFAULT_N}).")
    p.add_argument("--target", type=str, default=str(DEFAULT_TARGET),
                   help="Target markdown file to lint "
                        f"(default {DEFAULT_TARGET.relative_to(ROOT)}).")
    p.add_argument("--passages-dir", type=str, default=str(PASSAGES_DIR),
                   help="Directory of raw passages to compare against.")
    p.add_argument("--self-test", action="store_true",
                   help="Run in-memory unit checks and exit.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()
    return lint(Path(args.target).resolve(),
                Path(args.passages_dir).resolve(), args.n)


if __name__ == "__main__":
    sys.exit(main())
