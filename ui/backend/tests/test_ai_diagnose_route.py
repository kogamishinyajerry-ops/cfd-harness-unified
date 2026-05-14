"""Route-level tests for POST /api/ai-diagnose (DEC-V62-A-sub-M-ROUTE-AI-DIAGNOSE).

Coverage (matches sub-DEC §test spec · ≥10 tests):

  1. V41-like symptom ('janafThermo limit warnings') → V41 in top-3
  2. V92-like symptom ('cellZoneInside inside solid region missing') → V92 in top-3
  3. LLM offline + llm_match=True → 200, llm_match_used=False, base ranking works
  4. Audit artifact JSON round-trips
  5. TrustGate: every match has v_row_id + similarity_rationale
  6. Crash isolation: V-series load failure → 500 structured detail + audit logged
  7. 4Q gate compliance: route does not write inside case_dir
  8. ≥3 top matches when corpus has hits; ranking strictly descending
  9. case_dir provided → assemble_stack invoked + stack_report populated
 10. Empty symptom → 400 with actionable error
 11. case_dir provided but missing → 400 with actionable error
 12. solver_log_excerpt boosts otherwise-low-scoring rows
 13. top_k clamps response length
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routes import ai_diagnose as ai_diagnose_route
from ui.backend.services import advisor_stack as advisor_stack_module


# ---------- Helpers / fixtures --------------------------------------------


_REAL_CORPUS_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs" / "openfoam_corpus" / "industrial_solver_findings_v_series.md"
)


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FastAPI:
    """Build a FastAPI app with /api/ai-diagnose mounted; audit dir → tmp.

    The V-series corpus path is left pointing at the real repo file so
    similarity-matching tests exercise the real corpus content. Audit
    output is redirected into ``tmp_path`` so tests are hermetic.
    """
    monkeypatch.setattr(
        ai_diagnose_route, "_AUDIT_DIR", tmp_path / ".planning" / "audits" / "ai_diagnose",
    )
    # Invalidate the module-level corpus cache so prior tests in this
    # session do not leak a monkeypatched fixture into this one.
    monkeypatch.setattr(ai_diagnose_route, "_corpus_cache", None, raising=False)
    monkeypatch.setattr(ai_diagnose_route, "_corpus_cache_mtime", None, raising=False)

    a = FastAPI()
    a.include_router(ai_diagnose_route.router, prefix="/api")
    return a


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _parts_manifest_basic() -> dict[str, Any]:
    """A4 V79 D7 case + A5 V81 violation (shared with test_ai_review_route)."""
    return {
        "parts": [
            {
                "name": "louver_vane_2",
                "actual_face_normal": [0.7880, -0.6157, 0.0],
                "expected_face_normal": [0.0, -1.0, 0.0],
                "tolerance_deg": 4.0,
            },
            {"name": "supply_inlet", "role": "inlet"},
        ]
    }


def _top_v_ids(body: dict[str, Any], k: int = 3) -> list[str]:
    return [m["v_row_id"] for m in body["v_row_matches"][:k]]


# ---------- Tests ----------------------------------------------------------


def test_v41_symptom_top_3_match(client: TestClient) -> None:
    """V41 fires on 'janafThermo limit warnings'."""
    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "janafThermo out of temperature range warnings flood, Tlow=300 species",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    top_ids = _top_v_ids(body, k=3)
    assert "V41" in top_ids, f"V41 missing from top-3: {top_ids}"


def test_v92_symptom_top_3_match(client: TestClient) -> None:
    """V92 fires on 'cellZoneInside inside solid region missing'."""
    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": (
                "cellZoneInside inside fails on complex internal void STL "
                "with fuse_many union, empty cellZone for plate+fin"
            ),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    top_ids = _top_v_ids(body, k=3)
    assert "V92" in top_ids, f"V92 missing from top-3: {top_ids}"


def test_llm_match_true_returns_llm_match_used_false_offline(
    client: TestClient,
) -> None:
    """4Q gate (1): LLM provider not wired → base ranking still works,
    llm_match_used=False."""
    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "janafThermo Tlow species range",
            "llm_match": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["llm_match_used"] is False
    # base ranking should still surface something (corpus has ≥1 match)
    assert len(body["v_row_matches"]) >= 1


def test_audit_artifact_round_trips(
    client: TestClient, tmp_path: Path,
) -> None:
    """Persisted audit JSON is round-trip deserializable."""
    resp = client.post(
        "/api/ai-diagnose",
        json={"symptom_text": "kOmegaSST wall function NaN at iter 3"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    audit_path = Path(body["audit_artifact_path"])
    assert audit_path.is_file(), f"audit not persisted: {audit_path}"
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert payload["request_id"] == body["request_id"]
    assert payload["schema_version"] == "v62-a-ai-diagnose-v1"
    assert "matches" in payload
    assert "timing" in payload
    assert "corpus" in payload
    assert payload["corpus"]["size"] >= 80  # corpus has ~100 rows


def test_trust_gate_every_match_carries_v_row_id_and_rationale(
    client: TestClient,
) -> None:
    """TrustGate per 4Q (3): every surfaced match must carry v_row_id +
    similarity_rationale so engineers can audit."""
    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "GAMG p_rgh agglomeration fails on prism layers thin walls",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["v_row_matches"], "expected at least one match"
    for m in body["v_row_matches"]:
        assert re.match(r"^V\d+$", m["v_row_id"]), m
        assert m["v_row_title"]
        assert m["similarity_rationale"]
        assert 0.0 <= m["similarity_score"] <= 1.0


def test_corpus_load_failure_crash_isolated_with_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """V-series corpus missing → structured 500 with audit_artifact_path."""
    bogus = tmp_path / "nonexistent_v_series.md"
    monkeypatch.setattr(
        ai_diagnose_route, "_V_SERIES_CORPUS_PATH", bogus,
    )
    monkeypatch.setattr(ai_diagnose_route, "_corpus_cache", None, raising=False)
    monkeypatch.setattr(ai_diagnose_route, "_corpus_cache_mtime", None, raising=False)

    resp = client.post(
        "/api/ai-diagnose",
        json={"symptom_text": "anything"},
    )
    assert resp.status_code == 500, resp.text
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "v_series_corpus_unavailable"
    assert "request_id" in detail
    # Audit was still attempted before raising
    assert "audit_artifact_path" in detail


def test_4q_gate_route_does_not_write_inside_case_dir(
    client: TestClient, tmp_path: Path,
) -> None:
    """V130 advisor-not-driver: route reads from case_dir but does not write."""
    case_dir = tmp_path / "case_readonly"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    before = {
        p: p.read_bytes()
        for p in case_dir.rglob("*")
        if p.is_file()
    }
    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "face orientation deviation D7 louver vane",
            "case_dir": str(case_dir),
        },
    )
    assert resp.status_code == 200, resp.text
    after = {
        p: p.read_bytes()
        for p in case_dir.rglob("*")
        if p.is_file()
    }
    assert before == after, f"4Q gate violated: case_dir modified."


def test_at_least_3_matches_ranking_descending(client: TestClient) -> None:
    """top_k>=3 + ranking strictly non-increasing by similarity_score."""
    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": (
                "mesh quality skewness GAMG preconditioner SIGFPE wall function NaN "
                "thermo Tlow species cellZone"
            ),
            "top_k": 5,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    matches = body["v_row_matches"]
    assert len(matches) >= 3, f"expected ≥3 matches, got {len(matches)}"
    scores = [m["similarity_score"] for m in matches]
    assert scores == sorted(scores, reverse=True), (
        f"ranking not descending: {scores}"
    )


def test_case_dir_provided_invokes_assemble_stack(
    client: TestClient, tmp_path: Path,
) -> None:
    """case_dir + parts_manifest.json → stack_report populated."""
    case_dir = tmp_path / "case_with_parts"
    case_dir.mkdir()
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "face orientation D7 deviation",
            "case_dir": str(case_dir),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stack_report"] is not None, "stack should have run"
    assert body["stack_report"]["advisor_count"] >= 1


def test_empty_symptom_returns_400_with_actionable_error(
    client: TestClient,
) -> None:
    resp = client.post(
        "/api/ai-diagnose",
        json={"symptom_text": "   "},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "empty_symptom_text"
    assert "actionable" in detail


def test_missing_case_dir_returns_400(
    client: TestClient, tmp_path: Path,
) -> None:
    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "test",
            "case_dir": str(tmp_path / "does_not_exist"),
        },
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "case_dir_not_found"


def test_solver_log_excerpt_contributes_to_matching(
    client: TestClient,
) -> None:
    """Adding solver_log_excerpt should at minimum not reduce signal;
    typically increases relevant token overlap."""
    # Vague symptom with no V-row keywords by itself
    bare = client.post(
        "/api/ai-diagnose",
        json={"symptom_text": "solver crashed unexpectedly"},
    )
    assert bare.status_code == 200
    bare_body = bare.json()

    # Same symptom + solver-log-shaped excerpt that names a specific failure
    augmented = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "solver crashed unexpectedly",
            "solver_log_excerpt": (
                "GAMG: cannot reduce residual below tolerance for p_rgh\n"
                "prism layer non-orthogonal cells thin wall agglomeration\n"
            ),
        },
    )
    assert augmented.status_code == 200
    aug_body = augmented.json()

    # Augmented call should yield at least as many matches as the bare one.
    assert len(aug_body["v_row_matches"]) >= len(bare_body["v_row_matches"])
    # Augmented top match score should be >= bare top match score (more
    # tokens in query → no fewer overlaps possible).
    if bare_body["v_row_matches"] and aug_body["v_row_matches"]:
        assert (
            aug_body["v_row_matches"][0]["similarity_score"]
            >= bare_body["v_row_matches"][0]["similarity_score"]
            or aug_body["v_row_matches"][0]["v_row_id"]
            != bare_body["v_row_matches"][0]["v_row_id"]
        )


def test_top_k_clamps_response_length(client: TestClient) -> None:
    """top_k=2 → response carries ≤ 2 matches even if more would qualify."""
    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": (
                "mesh skewness GAMG preconditioner thermo Tlow cellZone "
                "face orientation thin wall"
            ),
            "top_k": 2,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["v_row_matches"]) <= 2


def test_4q_gate_no_llm_imports_in_route_module() -> None:
    """4Q (1) inline: route source contains no LLM provider / corpus_loader
    imports. Lexical scan defends against future regressions where a
    well-intentioned refactor wires in an LLM dependency."""
    src = Path(ai_diagnose_route.__file__).read_text(encoding="utf-8")
    forbidden_tokens = (
        "from anthropic",
        "import anthropic",
        "from openai",
        "import openai",
        "from ui.backend.services.llm_provider",
        "from ui.backend.services.ai_advisor",
        "corpus_loader",
    )
    hits = [tok for tok in forbidden_tokens if tok in src]
    assert not hits, f"4Q (1) violation: forbidden imports found: {hits}"


def test_stack_crash_isolation_route_still_returns_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """If assemble_stack raises, the route swallows the exception and
    returns 200 with stack_report=None (crash isolation per V62-A spec)."""
    case_dir = tmp_path / "case_for_crash"
    case_dir.mkdir()
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    def _boom(**kwargs: Any) -> None:
        raise RuntimeError("simulated advisor stack failure")

    monkeypatch.setattr(ai_diagnose_route, "assemble_stack", _boom)

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "anything",
            "case_dir": str(case_dir),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stack_report"] is None
    # Audit captures the failure
    audit = json.loads(Path(body["audit_artifact_path"]).read_text())
    assert audit["stack"]["error"] is not None
    assert "simulated advisor stack failure" in audit["stack"]["error"]


# ---------- Codex R0 (2026-05-14) regression tests ------------------------


def test_p1_canonical_layout_inputs_parts_manifest_invokes_stack(
    client: TestClient, tmp_path: Path,
) -> None:
    """Codex R0 P1: stack must run when parts_manifest lives under
    ``<case_dir>/inputs/`` (the project-standard layout used by
    /ai-review and existing case fixtures), not just under the flat
    ``<case_dir>/`` path."""
    case_dir = tmp_path / "case_canonical_layout"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "face orientation deviation D7",
            "case_dir": str(case_dir),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stack_report"] is not None, (
        "P1 regression: inputs/-layout case_dir should have invoked stack"
    )
    assert body["stack_report"]["advisor_count"] >= 1


def test_p1_yaml_parts_manifest_loaded_under_inputs(
    client: TestClient, tmp_path: Path,
) -> None:
    """Codex R0 P1 follow-up: YAML candidates under inputs/ are loaded."""
    case_dir = tmp_path / "case_yaml_layout"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    import yaml as _yaml
    (inputs / "parts_manifest.yaml").write_text(
        _yaml.safe_dump(_parts_manifest_basic()), encoding="utf-8",
    )

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "face orientation",
            "case_dir": str(case_dir),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stack_report"] is not None
    assert body["stack_report"]["advisor_count"] >= 1


def test_p2_boost_uses_findings_evidence_not_dispatched_advisors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Codex R0 P2: stack V-row boost must be derived from the
    ``evidence_v_rows`` carried by actual emitted Findings, NOT from
    ``AdvisorStackReport.evidence_refs`` (which unions every dispatched
    advisor's static V-row mapping regardless of findings)."""
    case_dir = tmp_path / "case_for_p2"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    # Patch assemble_stack to return a report where:
    #   - evidence_refs claims V77, V88 (would falsely boost those rows)
    #   - findings is empty (no V-rows actually surfaced)
    # The boost set must therefore be empty.
    from ui.backend.services.advisor_stack import AdvisorStackReport

    def _fake_stack(**_kwargs: Any) -> AdvisorStackReport:
        return AdvisorStackReport(
            findings=(),
            advisor_calls=(),
            evidence_refs=("V77", "V88"),
            stack_duration_ms=0.1,
            advisor_count=2,
        )

    monkeypatch.setattr(ai_diagnose_route, "assemble_stack", _fake_stack)

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "obscure-query-no-corpus-overlap-xyzqwerty",
            "case_dir": str(case_dir),
            "top_k": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # None of the surfaced matches should claim "surfaced by advisor_stack"
    # rationale, because no Finding actually carried any V-row.
    surfaced_v_ids = {
        m["v_row_id"]
        for m in body["v_row_matches"]
        if "advisor_stack" in m["similarity_rationale"]
    }
    assert surfaced_v_ids == set(), (
        f"P2 regression: V-rows boosted from evidence_refs without findings: "
        f"{surfaced_v_ids}"
    )


def test_p2_boost_applied_for_v_rows_in_actual_findings(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Codex R0 P2 positive-case: when a Finding actually carries V41 in
    its evidence_v_rows, V41 must be boosted in the diagnose ranking."""
    case_dir = tmp_path / "case_with_real_finding"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    from ui.backend.services.advisor_stack import (
        AdvisorStackReport,
        Finding,
    )

    # Codex R1 P2 (2026-05-14): use a real advisor code (``tlow_above_canonical``)
    # that the narrow finding-code → V-row map points to V41. Fabricated
    # codes get dropped per R2 narrowing semantics.
    fabricated_finding = Finding(
        source_advisor="thermo_polynomial_range_advisor",
        severity="critical",
        code="tlow_above_canonical",
        message="test finding",
        location=None,
        evidence_v_rows=("V41", "V93"),
        raw=None,
    )

    def _fake_stack(**_kwargs: Any) -> AdvisorStackReport:
        return AdvisorStackReport(
            findings=(fabricated_finding,),
            advisor_calls=(),
            evidence_refs=("V79", "V81"),  # noise; must NOT influence boost
            stack_duration_ms=0.1,
            advisor_count=1,
        )

    monkeypatch.setattr(ai_diagnose_route, "assemble_stack", _fake_stack)

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "obscure-no-overlap-tokens",
            "case_dir": str(case_dir),
            "top_k": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    v41_matches = [m for m in body["v_row_matches"] if m["v_row_id"] == "V41"]
    assert v41_matches, "V41 should be surfaced when tlow_above_canonical fires"
    assert "advisor_stack" in v41_matches[0]["similarity_rationale"]

    # V79/V81 are in evidence_refs but NOT a code in findings → must NOT be boosted.
    # V93 is in evidence_v_rows of the finding but the code ``tlow_above_canonical``
    # narrows to V41 only — V93 must NOT be boosted either (Codex R1 P2 narrowing).
    for v_id in ("V79", "V81", "V93"):
        matched = [m for m in body["v_row_matches"] if m["v_row_id"] == v_id]
        for m in matched:
            assert "advisor_stack" not in m["similarity_rationale"], (
                f"{v_id} should not claim stack-cross-ref under narrow map"
            )


# ---------- Codex R1 (2026-05-14) regression tests ------------------------


def test_r1p2_first_existing_manifest_wins_no_fallback_on_malformed(
    client: TestClient, tmp_path: Path,
) -> None:
    """Codex R1 P2.1: when the canonical primary manifest exists but is
    malformed, the route must NOT silently fall back to a later candidate.
    Cross-referencing stale fallback data is worse than skipping the
    cross-reference entirely."""
    case_dir = tmp_path / "case_malformed_primary"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    # Primary: malformed YAML
    (inputs / "parts_manifest.yaml").write_text(
        "::not::valid::yaml:: [\n", encoding="utf-8",
    )
    # Fallback that would silently take over under the old "loop until
    # load succeeds" semantics:
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "face orientation",
            "case_dir": str(case_dir),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Malformed primary → manifest treated as unavailable → stack does
    # not run. Fall-back JSON must NOT be silently consumed.
    assert body["stack_report"] is None, (
        "R1 P2.1 regression: malformed primary should make stack "
        "unavailable, not fall through to JSON sibling"
    )


def test_r1p2_finding_code_narrow_map_excludes_advisor_wide_v_rows(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Codex R1 P2.2: when an advisor emits a finding whose advisor-wide
    evidence_v_rows tuple is wider than the specific finding-code → V-row
    narrowing, only the narrowed V-rows must be boosted. V-rows in the
    wide tuple but NOT in the narrow map for that code must NOT be
    boosted ('fabricated provenance')."""
    case_dir = tmp_path / "case_for_r1_p2"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    from ui.backend.services.advisor_stack import (
        AdvisorStackReport,
        Finding,
    )

    # Real A8 shm code `typo_suspicion` — advisor stamps the wide tuple
    # (V52, V86, V99, V100). Narrow map ties this specific code to V52
    # only — the other three must NOT be boosted.
    typo_finding = Finding(
        source_advisor="shm_dict_validator",
        severity="warning",
        code="typo_suspicion",
        message="test",
        location=None,
        evidence_v_rows=("V52", "V86", "V99", "V100"),
        raw=None,
    )

    def _fake_stack(**_kwargs: Any) -> AdvisorStackReport:
        return AdvisorStackReport(
            findings=(typo_finding,),
            advisor_calls=(),
            evidence_refs=("V52", "V86", "V99", "V100"),
            stack_duration_ms=0.1,
            advisor_count=1,
        )

    monkeypatch.setattr(ai_diagnose_route, "assemble_stack", _fake_stack)

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "obscure-zero-token-overlap-xyzqwerty",
            "case_dir": str(case_dir),
            "top_k": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # V52 is in the narrow map → should be boosted + carry stack rationale
    v52_matches = [m for m in body["v_row_matches"] if m["v_row_id"] == "V52"]
    assert v52_matches, "V52 should appear (narrow-map boost)"
    assert "advisor_stack" in v52_matches[0]["similarity_rationale"]

    # V86, V99, V100 are in the wide advisor tuple but NOT the narrow map
    # for code typo_suspicion → must NOT be boosted nor flagged.
    for v_id in ("V86", "V99", "V100"):
        wide_matched = [
            m for m in body["v_row_matches"] if m["v_row_id"] == v_id
        ]
        for m in wide_matched:
            assert "advisor_stack" not in m["similarity_rationale"], (
                f"R1 P2.2 regression: {v_id} boosted from advisor-wide "
                f"tuple under code typo_suspicion (should narrow to V52 only)"
            )


def test_r1p2_unmapped_finding_code_does_not_boost(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Codex R1 P2.2 corollary: a finding code NOT in the narrow map
    contributes nothing to the boost set (no fabricated provenance from
    advisor-wide tuples). Under-boosting is safer than fabricating."""
    case_dir = tmp_path / "case_unmapped_code"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    from ui.backend.services.advisor_stack import (
        AdvisorStackReport,
        Finding,
    )

    unmapped_finding = Finding(
        source_advisor="some_advisor",
        severity="warning",
        code="brand_new_unmapped_code",
        message="test",
        location=None,
        evidence_v_rows=("V41", "V52", "V79"),
        raw=None,
    )

    def _fake_stack(**_kwargs: Any) -> AdvisorStackReport:
        return AdvisorStackReport(
            findings=(unmapped_finding,),
            advisor_calls=(),
            evidence_refs=(),
            stack_duration_ms=0.1,
            advisor_count=1,
        )

    monkeypatch.setattr(ai_diagnose_route, "assemble_stack", _fake_stack)

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "no-overlap-zzz",
            "case_dir": str(case_dir),
            "top_k": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    for v_id in ("V41", "V52", "V79"):
        wide_matched = [
            m for m in body["v_row_matches"] if m["v_row_id"] == v_id
        ]
        for m in wide_matched:
            assert "advisor_stack" not in m["similarity_rationale"], (
                f"R1 P2.2 corollary: {v_id} boosted from unmapped code "
                f"`brand_new_unmapped_code` (should contribute nothing)"
            )


# ---------- Codex R2 (2026-05-14) verbatim-landing regression tests ------


def test_r2p2_code_collision_thermo_typo_does_not_boost_shm_v52(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Codex R2 P2.1: ``typo_suspicion`` is emitted by BOTH
    shm_dict_validator (→ V52) and thermo_polynomial_range_advisor
    (species-name typo, not V52). The narrow map must key by
    ``(source_advisor, code)`` so a thermo typo finding does not
    fabricate sHM V52 provenance."""
    case_dir = tmp_path / "case_for_r2_collision"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    from ui.backend.services.advisor_stack import (
        AdvisorStackReport,
        Finding,
    )

    thermo_typo = Finding(
        source_advisor="thermo_polynomial_range_advisor",
        severity="warning",
        code="typo_suspicion",
        message="species name typo",
        location=None,
        evidence_v_rows=("V41", "V93"),
        raw=None,
    )

    def _fake_stack(**_kwargs: Any) -> AdvisorStackReport:
        return AdvisorStackReport(
            findings=(thermo_typo,),
            advisor_calls=(),
            evidence_refs=("V41", "V93"),
            stack_duration_ms=0.1,
            advisor_count=1,
        )

    monkeypatch.setattr(ai_diagnose_route, "assemble_stack", _fake_stack)

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "obscure-no-overlap-yyy",
            "case_dir": str(case_dir),
            "top_k": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # V52 is the shm typo V-row — must NOT be boosted when thermo emits typo.
    v52_matches = [m for m in body["v_row_matches"] if m["v_row_id"] == "V52"]
    for m in v52_matches:
        assert "advisor_stack" not in m["similarity_rationale"], (
            "R2 P2.1 regression: V52 (shm) boosted from a thermo "
            "typo_suspicion finding — code collision not disambiguated"
        )


def test_r2p2_real_shm_v99_code_multi_normal_constrained_patch(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Codex R2 P2.2: A8 emits ``multi_normal_constrained_patch`` for
    V99 (the V99-widening). The narrow map must use the real code, not
    a phantom name."""
    case_dir = tmp_path / "case_for_r2_v99"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    from ui.backend.services.advisor_stack import (
        AdvisorStackReport,
        Finding,
    )

    v99_finding = Finding(
        source_advisor="shm_dict_validator",
        severity="critical",
        code="multi_normal_constrained_patch",
        message="V99 widening test",
        location="patch_foo",
        evidence_v_rows=("V52", "V86", "V99", "V100"),
        raw=None,
    )

    def _fake_stack(**_kwargs: Any) -> AdvisorStackReport:
        return AdvisorStackReport(
            findings=(v99_finding,),
            advisor_calls=(),
            evidence_refs=(),
            stack_duration_ms=0.1,
            advisor_count=1,
        )

    monkeypatch.setattr(ai_diagnose_route, "assemble_stack", _fake_stack)

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "obscure-no-overlap-zzz",
            "case_dir": str(case_dir),
            "top_k": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    v99_matches = [m for m in body["v_row_matches"] if m["v_row_id"] == "V99"]
    assert v99_matches, (
        "R2 P2.2 regression: V99 lost because old map used phantom "
        "`non_planar_symmetry_patch` instead of real "
        "`multi_normal_constrained_patch`"
    )
    assert "advisor_stack" in v99_matches[0]["similarity_rationale"]


def test_r2p2_thermo_internal_t_below_tlow_maps_to_v93(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Codex R2 P2.2: A10 emits ``internal_t_below_tlow`` for the V93
    companion check. Must be in the narrow map."""
    case_dir = tmp_path / "case_for_r2_v93_companion"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.json").write_text(
        json.dumps(_parts_manifest_basic()), encoding="utf-8",
    )

    from ui.backend.services.advisor_stack import (
        AdvisorStackReport,
        Finding,
    )

    finding = Finding(
        source_advisor="thermo_polynomial_range_advisor",
        severity="critical",
        code="internal_t_below_tlow",
        message="V93 companion test",
        location=None,
        evidence_v_rows=("V41", "V93"),
        raw=None,
    )

    def _fake_stack(**_kwargs: Any) -> AdvisorStackReport:
        return AdvisorStackReport(
            findings=(finding,),
            advisor_calls=(),
            evidence_refs=(),
            stack_duration_ms=0.1,
            advisor_count=1,
        )

    monkeypatch.setattr(ai_diagnose_route, "assemble_stack", _fake_stack)

    resp = client.post(
        "/api/ai-diagnose",
        json={
            "symptom_text": "obscure-aaa",
            "case_dir": str(case_dir),
            "top_k": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    v93_matches = [m for m in body["v_row_matches"] if m["v_row_id"] == "V93"]
    assert v93_matches, "R2 P2.2 regression: V93 lost (internal_t_below_tlow missing from map)"
    assert "advisor_stack" in v93_matches[0]["similarity_rationale"]
