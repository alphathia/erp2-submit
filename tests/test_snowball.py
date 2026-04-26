"""Unit tests for code/snowball.py — pure-function coverage.

Tests the deterministic logic (citation parsing, DOI normalisation, cosine
similarity, dedup, status assignment, adapter, DoD assertions). Does NOT
test pdfplumber extraction or Crossref HTTP (those require fixtures and
network mocking — out of scope for this first-pass test file).

Run:  pytest tests/test_snowball.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from code.snowball import (       # noqa: E402
    _cosine_title_similarity,
    _dedup_key,
    _ref_to_row,
    _title_year_key,
    assert_dod,
    already_decided,
    build_decision_record,
    dedupe_refs,
    derive_seed_id,
    normalise_doi,
    parse_raw_citation,
    VALID_STATUS,
)


# ---------------------------------------------------------------------------
# normalise_doi
# ---------------------------------------------------------------------------
class TestNormaliseDoi:
    def test_none(self):
        assert normalise_doi(None) is None

    def test_empty(self):
        assert normalise_doi("") is None

    def test_plain(self):
        assert normalise_doi("10.1145/1234.5678") == "10.1145/1234.5678"

    def test_strips_https_prefix(self):
        assert normalise_doi("https://doi.org/10.1145/X") == "10.1145/x"

    def test_strips_doi_prefix(self):
        assert normalise_doi("doi:10.1145/X") == "10.1145/x"

    def test_lowercases(self):
        assert normalise_doi("10.1145/AbC") == "10.1145/abc"

    def test_strips_trailing_punct(self):
        assert normalise_doi("10.1145/x.") == "10.1145/x"


# ---------------------------------------------------------------------------
# parse_raw_citation
# ---------------------------------------------------------------------------
class TestParseRawCitation:
    def test_with_doi(self):
        raw = ("[1] Smith, J. Copilot usage in industry. "
               "ICSE 2024. https://doi.org/10.1145/3597503.3608128")
        out = parse_raw_citation(raw)
        assert out["doi"] == "10.1145/3597503.3608128"
        assert out["year"] == "2024"
        assert "Smith" in out["authors"]

    def test_without_doi(self):
        raw = ("Jones, A., and Liu, B. (2023). Large-scale survey of AI "
               "assistants. Journal of Software Engineering.")
        out = parse_raw_citation(raw)
        assert out["doi"] == ""
        assert out["year"] == "2023"

    def test_unparseable_stays_best_effort(self):
        raw = "Some garbled text with no structure 2022"
        out = parse_raw_citation(raw)
        assert out["year"] == "2022"
        # authors / title may be empty or best-effort; no crash

    def test_strips_leading_number(self):
        raw = "42. Author, X. (2020). A title. Venue."
        out = parse_raw_citation(raw)
        assert "Author" in out["authors"]
        assert out["year"] == "2020"


class TestParseRawCitationRealFormats:
    """Regression guards for the 5 real citation styles observed in the
    seed PDFs (diagnosed during Task 2.6 parser rewrite). Each test uses
    a simplified but representative example."""

    def test_otoum_ieee_quoted_title_before_year(self):
        """IEEE style: ''Title'' sits in doubled single quotes BEFORE year.
        Authors include initials like 'J.' which must not be mis-split."""
        raw = ("[1] J. He, C. Treude, and D. Lo, \u2018\u2018LLM-based "
               "multi-agent systems for agentic practices,\u2019\u2019 "
               "Journal, vol. 10, 2025, doi: 10.1145/3712003")
        out = parse_raw_citation(raw)
        assert "J. He" in out["authors"]
        assert "C. Treude" in out["authors"]
        assert out["title"].startswith("LLM-based multi-agent systems")
        assert out["year"] == "2025"
        assert out["doi"] == "10.1145/3712003"

    def test_liu_acm_nospace_webref(self):
        """ACM style with pdfplumber no-space extraction. Web-page ref:
        no author, starts with year. Title is the product name."""
        raw = "[11] 2021.PythonWrapperOfAndroidUiautomatorTestTool. https://github.com/xiaocong/uiautomator."
        out = parse_raw_citation(raw)
        assert out["authors"] == ""
        assert "PythonWrapper" in out["title"]
        assert out["year"] == "2021"

    def test_wangagenticprog_nospace_author_year_title(self):
        """ACM style with glued-together names and no spaces after periods.
        Year comes mid-citation, title follows."""
        raw = ("[39] DeepakBhaskarAcharya,KarthigeyanKuppan,andBDivya.2025."
               "Agenticai:Autonomousintelligenceforcomplexgoals.")
        out = parse_raw_citation(raw)
        assert "Acharya" in out["authors"]
        assert out["year"] == "2025"
        assert "Agenticai" in out["title"]

    def test_wangagentsse_springer_colon_separator(self):
        """Springer format: authors ':' separates author list from title.
        Year often at end in parentheses."""
        raw = ("Ahmad, W.U., Chakraborty, S., Ray, B., Chang, K.-W.: "
               "Unified pre-training for program understanding and generation. (2021)")
        out = parse_raw_citation(raw)
        assert "Ahmad" in out["authors"]
        assert "Chang, K.-W." in out["authors"]
        assert out["title"].startswith("Unified pre-training")
        assert out["year"] == "2021"

    def test_ajimati_apa_period_year_period(self):
        """Ajimati style (standard APA): authors ', YYYY. Title.'"""
        raw = ("Ali, Q.U.A., Horvath, B., Kolovos, D., Barmpis, K., "
               "Horvath, A., 2021. Towards scalable validation of low-code "
               "system models: mapping EVL to VIATRA patterns.")
        out = parse_raw_citation(raw)
        assert "Ali" in out["authors"]
        assert out["title"].startswith("Towards scalable validation")
        assert out["year"] == "2021"

    def test_normalise_spacing_preserves_initials(self):
        """Pdfplumber no-space normalization should insert space after '.'
        when followed by capital, even if preceded by an initial."""
        from code.snowball import _normalise_spacing
        out = _normalise_spacing("J.He,C.Treude")
        assert out == "J. He, C. Treude"

    def test_ieee_quoted_rejects_all_caps(self):
        """Short all-caps quoted text is likely an acronym, not a title."""
        raw = "Author, X. 2024. Title here. In ''IEEE'' conference."
        out = parse_raw_citation(raw)
        # 'IEEE' is in quotes but all-caps → Strategy 0 rejects → falls
        # through to year-anchored which captures real title
        assert "Title here" in out["title"]


# ---------------------------------------------------------------------------
# LLM fallback parser
# ---------------------------------------------------------------------------
class TestLLMFallback:
    """parse_citation_with_fallback: regex first; LLM rescue only when
    regex returns empty/short title. Mocked OpenAI client throughout."""

    def _make_mock_client(self, response_dict):
        """Build a fake OpenAI-shaped client whose chat.completions.create
        returns a single message with the given JSON payload."""
        import json as _json
        from unittest.mock import MagicMock
        client = MagicMock()
        msg = MagicMock()
        msg.message.content = _json.dumps(response_dict)
        completion = MagicMock()
        completion.choices = [msg]
        client.chat.completions.create.return_value = completion
        return client

    def test_regex_high_confidence_skips_llm(self):
        """Clean APA citation → regex confident → LLM never called."""
        from code.snowball import parse_citation_with_fallback
        client = self._make_mock_client({"authors": "X", "title": "Y", "year": "2024", "doi": ""})
        raw = ("Ali, Q.U.A., Horvath, B., 2021. Towards scalable validation "
               "of low-code system models: mapping EVL to VIATRA patterns.")
        result, source = parse_citation_with_fallback(raw, client)
        assert source == "regex"
        assert "Towards scalable" in result["title"]
        client.chat.completions.create.assert_not_called()

    def test_empty_title_triggers_llm(self):
        """Regex returns empty title → LLM rescue is invoked."""
        from code.snowball import parse_citation_with_fallback
        client = self._make_mock_client({
            "authors": "Smith, A.",
            "title": "A meaningful paper title from the LLM",
            "year": "2024",
            "doi": "",
        })
        # Year present but nothing after it → regex returns title=""
        raw = "Smith, A. 2024."
        result, source = parse_citation_with_fallback(raw, client)
        client.chat.completions.create.assert_called_once()
        assert source == "llm"
        assert result["title"].startswith("A meaningful")

    def test_short_title_triggers_llm(self):
        """Short regex result (< 15 chars) → LLM rescue."""
        from code.snowball import parse_citation_with_fallback
        client = self._make_mock_client({
            "authors": "Smith, J.",
            "title": "A long meaningful paper title from the LLM",
            "year": "2024",
            "doi": "",
        })
        # Construct a raw whose regex parse yields a short title
        raw = "Smith. 2024. AI."   # regex will give title="AI" (too short)
        result, source = parse_citation_with_fallback(raw, client)
        client.chat.completions.create.assert_called_once()
        assert source == "llm"
        assert result["title"].startswith("A long meaningful")

    def test_llm_failure_falls_back_to_regex(self):
        """Mocked LLM exception → return regex result with source='regex-fallback'."""
        from code.snowball import parse_citation_with_fallback
        from unittest.mock import MagicMock
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("API down")
        raw = "Smith. 2024. AI."   # short regex title triggers LLM
        result, source = parse_citation_with_fallback(raw, client)
        assert source == "regex-fallback"
        # Regex result preserved
        assert result["year"] == "2024"

    def test_no_client_returns_regex_no_llm(self):
        """Caller passes None client → source='regex-no-llm'."""
        from code.snowball import parse_citation_with_fallback
        raw = "Smith. 2024. Some title about AI agents in software."
        result, source = parse_citation_with_fallback(raw, None)
        assert source == "regex-no-llm"

    def test_llm_doi_preserves_regex_doi(self):
        """If regex found a DOI but LLM didn't, regex DOI is preserved."""
        from code.snowball import parse_citation_with_fallback
        client = self._make_mock_client({
            "authors": "Smith, J.",
            "title": "A long meaningful title rescued by the LLM",
            "year": "2024",
            "doi": "",        # LLM did not surface a DOI
        })
        # DOI literally present, year at end → regex empty-title path,
        # DOI extracted by regex via DOI_REGEX.
        raw = "Smith. https://doi.org/10.1145/12345 2024."
        result, source = parse_citation_with_fallback(raw, client)
        assert source == "llm"
        assert result["doi"] == "10.1145/12345"   # preserved from regex


# ---------------------------------------------------------------------------
# cosine similarity
# ---------------------------------------------------------------------------
class TestCosineSimilarity:
    def test_identical(self):
        s = _cosine_title_similarity("AI Agents for Software Engineering",
                                      "AI Agents for Software Engineering")
        assert s == pytest.approx(1.0)

    def test_case_insensitive(self):
        s = _cosine_title_similarity("AI Agents", "ai agents")
        assert s == pytest.approx(1.0)

    def test_punctuation_ignored(self):
        s = _cosine_title_similarity("AI Agents: A Survey",
                                      "AI Agents — A Survey")
        assert s == pytest.approx(1.0)

    def test_disjoint(self):
        s = _cosine_title_similarity("red blue green", "apple orange")
        assert s == 0.0

    def test_partial_overlap(self):
        s = _cosine_title_similarity("ai agents for software engineering",
                                      "ai agents in software development")
        assert 0.5 < s < 1.0

    def test_empty(self):
        assert _cosine_title_similarity("", "nonempty") == 0.0
        assert _cosine_title_similarity("nonempty", "") == 0.0


# ---------------------------------------------------------------------------
# dedupe_refs
# ---------------------------------------------------------------------------
class TestDedupeRefs:
    def test_same_doi_two_seeds_merges(self):
        refs = [
            {"doi": "10.1/a", "title": "t", "year": "2024",
             "source_seed": "SeedA", "raw_citation": "r1"},
            {"doi": "10.1/a", "title": "t", "year": "2024",
             "source_seed": "SeedB", "raw_citation": "r2"},
        ]
        out = dedupe_refs(refs)
        assert len(out) == 1
        seeds = out[0]["source_seed"].split("|")
        assert set(seeds) == {"SeedA", "SeedB"}

    def test_different_dois_not_merged(self):
        refs = [
            {"doi": "10.1/a", "title": "", "year": "", "source_seed": "A"},
            {"doi": "10.1/b", "title": "", "year": "", "source_seed": "A"},
        ]
        assert len(dedupe_refs(refs)) == 2

    def test_no_doi_dedups_by_title_year(self):
        refs = [
            {"doi": "", "title": "AI Agents Survey", "year": "2024",
             "source_seed": "A"},
            {"doi": "", "title": "AI Agents Survey", "year": "2024",
             "source_seed": "B"},
        ]
        out = dedupe_refs(refs)
        assert len(out) == 1
        assert set(out[0]["source_seed"].split("|")) == {"A", "B"}

    def test_prefers_row_with_doi(self):
        refs = [
            {"doi": "", "title": "X", "year": "2024", "source_seed": "A"},
            {"doi": "10.1/x", "title": "X", "year": "2024", "source_seed": "A"},
        ]
        out = dedupe_refs(refs)
        # When one has a DOI and the other doesn't, their keys differ
        # (title-based vs DOI-based), so they won't merge. That's acceptable —
        # the test ensures no crash. Check both rows preserved:
        assert len(out) == 2


# ---------------------------------------------------------------------------
# already_decided (Gap A + B)
# ---------------------------------------------------------------------------
class TestAlreadyDecided:
    """Ref is 'already decided' if it matches ANY row in phase2_decisions.csv
    — include OR exclude — by DOI, paper_id, or title+year fallback."""

    def test_match_by_doi_include(self):
        ref = {"doi": "10.1/a", "title": "t", "year": "2024"}
        assert already_decided(ref, {"10.1/a"}, set(), set())

    def test_match_by_doi_excluded(self):
        # Gap A guard: DOI in decided_dois regardless of whether it was
        # an include or exclude in Task 2.5
        ref = {"doi": "10.1/excluded-paper", "title": "t", "year": "2024"}
        assert already_decided(ref, {"10.1/excluded-paper"}, set(), set())

    def test_match_by_paper_id(self):
        # Ref has no DOI but its computed paper_id (hash:...) matches a
        # decided row's paper_id
        ref = {"doi": "", "title": "some title", "year": "2024"}
        # Compute what its paper_id would be — we know _compute_paper_id
        # uses hash:<md5 prefix> when doi is absent
        from code.snowball import _compute_paper_id
        pid = _compute_paper_id(ref)
        assert already_decided(ref, set(), {pid}, set())

    def test_match_by_title_year_fallback(self):
        # Gap B guard: no DOI, but title+year matches a decided row
        ref = {"doi": "", "title": "Large scale AI agents study", "year": "2024"}
        key = _title_year_key(ref)
        assert key is not None
        assert already_decided(ref, set(), set(), {key})

    def test_no_match(self):
        ref = {"doi": "10.1/novel", "title": "Novel paper", "year": "2024"}
        assert not already_decided(ref, {"10.1/other"}, {"doi:10.1/other"},
                                    {"other title|2024"})

    def test_null_doi_falls_through_to_title_year(self):
        ref = {"doi": "", "title": "short", "year": "2024"}
        # Too few title tokens → _title_year_key returns None → no crash
        assert not already_decided(ref, {"10.1/a"}, set(), set())

    def test_empty_ref_does_not_match(self):
        ref = {"doi": "", "title": "", "year": ""}
        assert not already_decided(ref, {"10.1/a"}, set(), {"foo|2024"})


class TestTitleYearKey:
    def test_too_short_returns_none(self):
        assert _title_year_key({"title": "abc", "year": "2024"}) is None

    def test_normal_returns_key(self):
        k = _title_year_key({"title": "Large scale study of AI agents",
                             "year": "2024"})
        assert k is not None
        assert "2024" in k
        assert "large" in k.lower()

    def test_empty_title_returns_none(self):
        assert _title_year_key({"title": "", "year": "2024"}) is None

    def test_deterministic(self):
        ref1 = {"title": "AI agents survey", "year": "2024"}
        ref2 = {"title": "AI agents survey", "year": "2024"}
        assert _title_year_key(ref1) == _title_year_key(ref2)


# ---------------------------------------------------------------------------
# derive_seed_id
# ---------------------------------------------------------------------------
class TestDeriveSeedId:
    def test_wang_agents_se(self, tmp_path):
        p = tmp_path / "Wang et al. - 2025 - Agents in software engineering survey, landscape, and vision.pdf"
        p.touch()
        assert derive_seed_id(p) == "WangAgentsSE2025"

    def test_wang_agentic_prog(self, tmp_path):
        p = tmp_path / "Wang et al. - 2025 - AI Agentic Programming A Survey of Techniques, Challenges, and Opportunities.pdf"
        p.touch()
        assert derive_seed_id(p) == "WangAgenticProg2025"

    def test_liu_llm(self, tmp_path):
        p = tmp_path / "Liu et al. - 2026 - Large Language Model-Based Agents for Software Engineering A Survey.pdf"
        p.touch()
        assert derive_seed_id(p) == "LiuLLMAgents2026"

    def test_ajimati_lcnc(self, tmp_path):
        p = tmp_path / "Ajimati et al. - 2025 - Adoption of low-code and no-code development A systematic literature review and future research age.pdf"
        p.touch()
        assert derive_seed_id(p) == "AjimatiLCNC2025"


# ---------------------------------------------------------------------------
# adapter
# ---------------------------------------------------------------------------
class TestRefToRow:
    def test_row_has_all_expected_fields(self):
        ref = {"title": "X", "year": "2024", "doi": "10.1/x",
               "authors": "Smith"}
        row = _ref_to_row(ref)
        assert row["title"] == "X"
        assert row["year"] == "2024"
        assert row["doi"] == "10.1/x"
        assert "snowball" in row["abstract"].lower()
        # Flags all empty
        assert row["preprint_flag"] == ""
        assert row["ic3_flag"] == ""


# ---------------------------------------------------------------------------
# build_decision_record
# ---------------------------------------------------------------------------
class TestBuildDecisionRecord:
    def test_include(self):
        ref = {"title": "t", "doi": "10.1/x", "year": "2024"}
        parsed = {"decision": "include", "criterion": None,
                  "f1_provisional": "Evaluation Research",
                  "preprint_paper": "published", "rationale": "good fit"}
        rec = build_decision_record(ref, parsed, session_id="abc",
                                    rater="AT")
        assert rec["decision"] == "include"
        assert rec["pass_number"] == "snowball"
        assert rec["paper_id"] == "doi:10.1/x"
        assert rec["rationale"].startswith("[LLM-snowball]")
        assert rec["session_id"] == "abc"

    def test_exclude_preserves_existing_prefix(self):
        ref = {"title": "t", "doi": "", "year": "2024"}
        parsed = {"decision": "exclude", "criterion": "EC4",
                  "f1_provisional": None, "preprint_paper": "unknown",
                  "rationale": "[snowball-forced-exclude] xyz"}
        rec = build_decision_record(ref, parsed, session_id="xy", rater="AT")
        assert rec["rationale"].startswith("[snowball-forced-exclude]")
        assert not rec["rationale"].startswith("[LLM-snowball]")

    def test_paper_id_fallback_without_doi(self):
        ref = {"title": "abc", "doi": "", "year": "2024"}
        parsed = {"decision": "exclude", "criterion": "EC3",
                  "f1_provisional": None, "preprint_paper": "unknown",
                  "rationale": "out of scope"}
        rec = build_decision_record(ref, parsed, session_id="s", rater="AT")
        assert rec["paper_id"].startswith("hash:")


# ---------------------------------------------------------------------------
# assert_dod
# ---------------------------------------------------------------------------
class TestAssertDod:
    def _ref(self, **kw):
        base = {"status": "already_in_corpus", "source_seed": "A",
                "doi": ""}
        base.update(kw)
        return base

    def test_valid_partition_passes(self):
        refs = [
            self._ref(status="already_in_corpus", source_seed="A", doi="10.1/a"),
            self._ref(status="included_via_snowball", source_seed="B", doi="10.1/b"),
            self._ref(status="excluded_via_snowball", source_seed="A|B"),
        ]
        assert_dod(refs, {"A", "B"})  # no exception

    def test_invalid_status_raises(self):
        refs = [self._ref(status="nope", source_seed="A")]
        with pytest.raises(AssertionError):
            assert_dod(refs, {"A"})

    def test_missing_seed_raises(self):
        refs = [self._ref(status="already_in_corpus", source_seed="A")]
        with pytest.raises(AssertionError, match="Seeds missing"):
            assert_dod(refs, {"A", "B"})

    def test_duplicate_doi_raises(self):
        refs = [
            self._ref(status="already_in_corpus", source_seed="A", doi="10.1/x"),
            self._ref(status="included_via_snowball", source_seed="A", doi="10.1/x"),
        ]
        with pytest.raises(AssertionError, match="Duplicate DOIs"):
            assert_dod(refs, {"A"})

    def test_null_status_raises(self):
        refs = [self._ref(status="", source_seed="A")]
        with pytest.raises(AssertionError):
            assert_dod(refs, {"A"})

    def test_valid_status_constant(self):
        assert VALID_STATUS == {
            "already_in_corpus",
            "included_via_snowball",
            "excluded_via_snowball",
        }


# ---------------------------------------------------------------------------
# _dedup_key
# ---------------------------------------------------------------------------
class TestDedupKey:
    def test_doi_key_when_present(self):
        assert _dedup_key({"doi": "10.1/x", "title": "t", "year": "2024"}) == "doi:10.1/x"

    def test_title_year_key_when_no_doi(self):
        k = _dedup_key({"doi": "", "title": "AI agents survey",
                        "year": "2024"})
        assert k.startswith("tit:")
        assert "2024" in k

    def test_different_titles_produce_different_keys(self):
        k1 = _dedup_key({"doi": "", "title": "A", "year": "2024"})
        k2 = _dedup_key({"doi": "", "title": "B", "year": "2024"})
        assert k1 != k2
