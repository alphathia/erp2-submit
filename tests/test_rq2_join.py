"""Unit test for code/analysis_rq2_variation.py join chain.

Verifies the regex for paper_id extraction from passage_ids and the
explode-then-distinct logic on a 3-passage fixture.

Run:  pytest tests/test_rq2_join.py -v
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from code.analysis_rq2_variation import PASSAGE_RE  # noqa: E402


def test_passage_regex_extracts_paper_id() -> None:
    """Regex should strip :P### suffix and preserve the doi:... prefix."""
    m = PASSAGE_RE.match("doi:10.1109/msr66628.2025.00105:P001")
    assert m is not None
    assert m.group(1) == "doi:10.1109/msr66628.2025.00105"


def test_passage_regex_handles_multiple_passages_same_paper() -> None:
    """Two passages from the same paper should map to the same paper_id."""
    p1 = PASSAGE_RE.match("doi:10.1145/abc.2024:P001").group(1)
    p2 = PASSAGE_RE.match("doi:10.1145/abc.2024:P007").group(1)
    assert p1 == p2 == "doi:10.1145/abc.2024"


def test_passage_regex_rejects_malformed() -> None:
    """No :P### suffix → no match."""
    assert PASSAGE_RE.match("doi:10.1145/abc.2024") is None
    assert PASSAGE_RE.match("10.1145/abc.2024:P001") is None


def test_explode_distinct_logic() -> None:
    """Verify the explode + DISTINCT (canonical_label, paper_id) step.

    Three passages across two papers, two labels. The distinct pairs
    should be {(L1,p1),(L1,p2),(L2,p1)}.
    """
    fixture = pd.DataFrame([
        {"canonical_label": "L1",
         "passage_ids": json.dumps(["doi:X/p1:P001", "doi:X/p2:P001"])},
        {"canonical_label": "L2",
         "passage_ids": json.dumps(["doi:X/p1:P002"])},
    ])

    rows = []
    for _, r in fixture.iterrows():
        for pid in json.loads(r["passage_ids"]):
            m = PASSAGE_RE.match(pid)
            if m:
                rows.append(
                    {"canonical_label": r["canonical_label"],
                     "paper_id": m.group(1)})
    df = pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)

    assert df.shape[0] == 3, f"Expected 3 distinct pairs, got {df.shape[0]}"
    assert set(df["paper_id"].unique()) == {"doi:X/p1", "doi:X/p2"}
    assert df[df["canonical_label"] == "L1"]["paper_id"].nunique() == 2
    assert df[df["canonical_label"] == "L2"]["paper_id"].nunique() == 1
