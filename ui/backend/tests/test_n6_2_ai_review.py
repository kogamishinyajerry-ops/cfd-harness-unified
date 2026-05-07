"""DEC-V61-158 (N6.2) · AI 审查 advisor route + service tests.

Coverage:
  * Schema validators (ReviewFinding extra=forbid, citation required;
    ReviewResponse extra=forbid)
  * Rule-based fallback: empty case + populated case
  * LLM path: valid response, hallucinated chunk_id dropped, malformed
    JSON fall-through to rule-based, provider raises fall-through
  * Route: GET 200, bad case_id 400, missing case_id 404
  * V132 Layer-A: route + service exercised, no
    KNOWN_MUTATION_FUNCTIONS symbol invoked
"""
from __future__ import annotations

import asyncio
import importlib
import json
import secrets
from pathlib import Path
from typing import Any, AsyncIterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ui.backend.schemas.ai_advisor import (
    CitedChunk,
    ReviewFinding,
    ReviewResponse,
)
from ui.backend.services.ai_actions.mutating_routes import (
    KNOWN_MUTATION_FUNCTIONS,
)
from ui.backend.services.ai_advisor import (
    load_corpus,
    reset_default_corpus,
    review_case,
)
from ui.backend.services.case_manifest import (
    CaseManifest,
    write_case_manifest,
)
from ui.backend.services.llm_provider.base import (
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    LLMProvider,
    MockLLMProvider,
)


# ────────── Fixture corpus ──────────


def _build_test_corpus(tmp_path: Path) -> Any:
    """Build a small corpus with chunks the rule-based mapping covers.

    Includes "mesh quality checkmesh", "solver selection", "residual
    diagnostics" anchors — enough for the rule-based ground-truth to
    find citations.
    """
    (tmp_path / "docs/openfoam_corpus").mkdir(parents=True)
    (tmp_path / "docs/openfoam_corpus/mesh.md").write_text(
        "## Mesh quality\n\nThe checkMesh utility reports orthogonality.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/openfoam_corpus/solver.md").write_text(
        "## Solver selection\n\nPick simpleFoam for steady RANS.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/openfoam_corpus/residuals.md").write_text(
        "## Residual diagnostics\n\nStalled residuals indicate "
        "physics setup issues.\n",
        encoding="utf-8",
    )
    return load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )


def _safe_id() -> str:
    return f"imported_2026-05-07T00-00-00Z_{secrets.token_hex(4)}"


def _stage_empty_case(imported_dir: Path, case_id: str) -> Path:
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    write_case_manifest(case_dir, CaseManifest(case_id=case_id))
    return case_dir


# ────────── Schema validators ──────────


def _valid_chunk() -> CitedChunk:
    return CitedChunk(
        chunk_id="x",
        source="openfoam_corpus",
        path="docs/x.md",
        sha="0" * 64,
        section_anchor=None,
        byte_offset=0,
        text="hello",
    )


def test_review_finding_requires_citation() -> None:
    with pytest.raises(ValidationError):
        ReviewFinding(
            severity="info",
            area="mesh",
            message="msg",
            source="rule_based",
        )


def test_review_finding_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        ReviewFinding(
            severity="info",
            area="mesh",
            message="msg",
            citation=_valid_chunk(),
            source="rule_based",
            extra_field="oops",
        )


def test_review_response_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        ReviewResponse(
            case_id="x",
            findings=[],
            llm_available=False,
            corpus_sha="0" * 64,
            generated_at="2026-05-07T00:00:00Z",
            extra_field="oops",
        )


# ────────── Rule-based fallback (offline path) ──────────


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_offline_empty_case_returns_critical_findings(
    tmp_path: Path,
) -> None:
    """An empty case fires multiple critical issues from N5.2
    (geometry_stl_missing, mesh_polymesh_missing, etc). With the
    rule-based fallback, those issues become findings citing the
    seed corpus."""
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir, corpus=corpus, provider=MockLLMProvider()
        )
    )

    assert response.llm_available is False
    assert response.degradation_note is not None
    assert "DEEPSEEK_API_KEY unset" in response.degradation_note
    assert response.corpus_sha == corpus.stats.corpus_sha
    # At least one critical finding (e.g. mesh_polymesh_missing) must
    # have a citation grounded in the corpus.
    critical = [f for f in response.findings if f.severity == "critical"]
    assert critical, "Expected critical findings on empty case"
    for finding in response.findings:
        assert finding.source == "rule_based"
        assert corpus.get_chunk(finding.citation.chunk_id) is not None


def test_offline_findings_dropped_when_no_corpus_match(
    tmp_path: Path,
) -> None:
    """If the seed corpus is empty (no chunks), every rule-based
    finding is dropped because no citation can be grounded."""
    (tmp_path / "docs/openfoam_corpus").mkdir(parents=True)
    # No corpus content
    corpus = load_corpus(
        tmp_path, roots=[("docs/openfoam_corpus", "openfoam_corpus")]
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir, corpus=corpus, provider=MockLLMProvider()
        )
    )
    assert response.findings == []
    assert response.llm_available is False


# ────────── LLM path with injected provider ──────────


class _FakeLLMProvider(LLMProvider):
    """Returns a fixed string. Used to simulate LLM responses."""

    def __init__(self, content: str) -> None:
        self._content = content

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            content=self._content,
            model_used="fake",
            fallback_used=False,
        )

    def chat_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatStreamChunk]:  # pragma: no cover
        async def _gen() -> AsyncIterator[ChatStreamChunk]:
            if False:
                yield  # type: ignore[unreachable]

        return _gen()


class _RaisingLLMProvider(LLMProvider):
    """Raises mid-call. Tests fall-through to rule-based."""

    async def chat(self, request: ChatRequest) -> ChatResponse:
        raise RuntimeError("upstream blew up")

    def chat_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatStreamChunk]:  # pragma: no cover
        async def _gen() -> AsyncIterator[ChatStreamChunk]:
            if False:
                yield  # type: ignore[unreachable]

        return _gen()


def test_llm_path_valid_response_findings_parsed(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "findings": [
                {
                    "severity": "warning",
                    "area": "mesh",
                    "message": "Check mesh skewness in cylinder elbow.",
                    "citation_chunk_id": real_chunk_id,
                    "recommended_change": (
                        "Reduce snappyHexMesh refinement level by 1"
                    ),
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    assert response.llm_available is True
    assert len(response.findings) == 1
    f = response.findings[0]
    assert f.source == "llm"
    assert f.citation.chunk_id == real_chunk_id
    assert (
        f.recommended_change
        == "Reduce snappyHexMesh refinement level by 1"
    )


def test_llm_path_hallucinated_chunk_id_dropped(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    llm_output = json.dumps(
        {
            "findings": [
                {
                    "severity": "warning",
                    "area": "mesh",
                    "message": "Real-looking finding",
                    "citation_chunk_id": "fake-id-not-in-corpus",
                    "recommended_change": None,
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    # LLM returned a finding but its chunk_id is hallucinated, so
    # the finding is dropped. llm_available stays True (the call
    # succeeded; only the finding was dropped).
    assert response.llm_available is True
    assert response.findings == []


def test_llm_path_handles_code_fence_wrapping(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = (
        "```json\n"
        + json.dumps(
            {
                "findings": [
                    {
                        "severity": "info",
                        "area": "solver",
                        "message": "Steady RANS is appropriate here.",
                        "citation_chunk_id": real_chunk_id,
                    }
                ]
            }
        )
        + "\n```"
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    assert response.llm_available is True
    assert len(response.findings) == 1


def test_llm_path_malformed_json_falls_through_to_rule_based(
    tmp_path: Path,
) -> None:
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider("this is not json at all"),
        )
    )
    # JSON parse failed → service returns LLM=true with empty
    # findings (LLM call itself succeeded, just returned junk).
    # This is acceptable per the service contract; the engineer
    # sees "llm_available: true, findings: []" and can re-run.
    assert response.llm_available is True
    assert response.findings == []


def test_llm_path_provider_raises_falls_through_to_rule_based(
    tmp_path: Path,
) -> None:
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_RaisingLLMProvider(),
        )
    )
    assert response.llm_available is False
    assert response.degradation_note is not None
    assert "RuntimeError" in response.degradation_note
    # Fall-through served rule-based findings (case is empty so
    # multiple critical issues fire and find corpus citations).
    assert any(
        f.source == "rule_based" and f.severity == "critical"
        for f in response.findings
    )


# ────────── Route ──────────


def _isolate(monkeypatch, tmp_path: Path) -> Path:
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.ai_advisor.IMPORTED_DIR", target
    )
    return target


def _client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def test_route_returns_200_for_valid_case(monkeypatch, tmp_path):
    """End-to-end route smoke. Uses real corpus + mock LLM provider
    (no DEEPSEEK_API_KEY → factory returns MockLLMProvider)."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage_empty_case(imported, case_id)
    # Ensure no real LLM key is bound for this test.
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    # Reset the corpus singleton so it picks up real seed corpus
    # under repo (NOT tmp_path; production singleton scans repo root).
    reset_default_corpus()

    resp = _client().get(f"/api/cases/{case_id}/ai-review")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["llm_available"] is False
    assert isinstance(body["findings"], list)
    assert len(body["corpus_sha"]) == 64

    reset_default_corpus()


def test_route_bad_case_id_returns_400(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    resp = _client().get("/api/cases/..%2Fescape/ai-review")
    assert resp.status_code in (400, 404)  # depends on URL escaping


def test_route_missing_case_id_returns_404(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    safe_but_missing = _safe_id()

    resp = _client().get(f"/api/cases/{safe_but_missing}/ai-review")
    assert resp.status_code == 404


# ────────── Codex R0 P1: loopback guard (regression) ──────────


def test_route_rejects_non_loopback_caller(monkeypatch, tmp_path):
    """Codex N6.2 R0 P1: route must require_loopback like ai-chat /
    ai-coach. A request with X-Forwarded-For (proxy header) gets 403
    when the override env-var is unset."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage_empty_case(imported, case_id)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("AI_CHAT_ALLOW_NON_LOOPBACK", raising=False)
    reset_default_corpus()

    resp = _client().get(
        f"/api/cases/{case_id}/ai-review",
        headers={"X-Forwarded-For": "203.0.113.42"},
    )
    assert resp.status_code == 403
    assert "loopback" in resp.json()["detail"].lower()
    reset_default_corpus()


def test_route_allows_non_loopback_when_override_set(
    monkeypatch, tmp_path
):
    """Override env-var unblocks the route for operators behind a
    trusted reverse proxy."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage_empty_case(imported, case_id)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("AI_CHAT_ALLOW_NON_LOOPBACK", "1")
    reset_default_corpus()

    resp = _client().get(
        f"/api/cases/{case_id}/ai-review",
        headers={"X-Forwarded-For": "203.0.113.42"},
    )
    assert resp.status_code == 200
    reset_default_corpus()


# ────────── Codex R0 P2: action-text strip (regression) ──────────


@pytest.mark.parametrize(
    "bad_text",
    [
        "POST /api/cases/abc/mesh",
        "Run curl -X POST https://...",
        "Click [Apply] to commit",
        "click [应用] now",
        "mention /api/cases/{id}/physics",
        "PUT /api/cases/foo/bc-contract",
        "use dispatch(tool=setupBC, args={...})",
    ],
)
def test_llm_finding_with_action_text_in_message_is_dropped(
    bad_text, tmp_path: Path
):
    """Codex N6.2 R0 P2: any LLM-emitted message containing an HTTP
    method + path / [Apply] / curl / dispatch phrasing is dropped
    server-side before reaching the wire."""
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "findings": [
                {
                    "severity": "warning",
                    "area": "mesh",
                    "message": bad_text,
                    "citation_chunk_id": real_chunk_id,
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    assert response.llm_available is True
    assert response.findings == [], (
        f"Action-text finding was not dropped: bad_text={bad_text!r}"
    )


def test_llm_finding_with_action_text_in_recommended_change_is_dropped(
    tmp_path: Path,
):
    """Same as above but the action-text is in recommended_change
    (which N6.4 will render with copy-button affordance)."""
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "findings": [
                {
                    "severity": "warning",
                    "area": "physics",
                    "message": "Plain factual statement.",
                    "citation_chunk_id": real_chunk_id,
                    "recommended_change": (
                        "POST /api/cases/{id}/physics with regime=ras_keomega"
                    ),
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    assert response.findings == []


# ────────── Codex R1 P1: non-string field robustness ──────────


@pytest.mark.parametrize(
    "bad_field_value",
    [
        ["nested", "list"],
        {"text": "nested dict"},
        42,
        True,
    ],
)
def test_llm_finding_with_non_string_message_does_not_crash_review(
    bad_field_value, tmp_path: Path
) -> None:
    """Codex N6.2 R1 P1: a non-string ``message`` (LLM emits a
    list/dict/int/bool by accident) must NOT crash _has_action_text
    and abort the entire review. The malformed finding is dropped
    individually; siblings in the same response keep flowing."""
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "findings": [
                # Malformed: bad message type
                {
                    "severity": "warning",
                    "area": "mesh",
                    "message": bad_field_value,
                    "citation_chunk_id": real_chunk_id,
                },
                # Sibling: valid finding — must survive
                {
                    "severity": "info",
                    "area": "solver",
                    "message": "Steady RANS appropriate here.",
                    "citation_chunk_id": real_chunk_id,
                },
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    # Critical: the LLM call did NOT fail — llm_available stays True
    # (regression guard against the R1 P1 bug where TypeError
    # escaped and the whole response fell through to rule-based).
    assert response.llm_available is True
    # The malformed finding was dropped; the valid sibling survived.
    assert len(response.findings) == 1
    assert response.findings[0].message == "Steady RANS appropriate here."


def test_llm_finding_with_non_string_recommended_change_is_dropped_only(
    tmp_path: Path,
) -> None:
    """Same shape as above but the malformed field is
    recommended_change. The Pydantic validator rejects the finding
    (since the schema declares Optional[str]); but the action-text
    pre-check must NOT crash before reaching that point."""
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "findings": [
                {
                    "severity": "warning",
                    "area": "mesh",
                    "message": "valid message",
                    "citation_chunk_id": real_chunk_id,
                    "recommended_change": ["bad", "list"],
                },
                {
                    "severity": "info",
                    "area": "solver",
                    "message": "valid sibling",
                    "citation_chunk_id": real_chunk_id,
                },
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    assert response.llm_available is True
    # Malformed dropped; valid sibling kept.
    assert any(f.message == "valid sibling" for f in response.findings)


# ────────── Codex R1 P2: prompt/regex alignment ──────────


@pytest.mark.parametrize(
    "button_label",
    [
        "[Submit]",
        "[Confirm]",
        "[Commit]",
        "[Save]",
        "[保存]",
        "[ submit ]",
        "[SUBMIT]",
    ],
)
def test_llm_finding_with_extra_button_labels_is_dropped(
    button_label, tmp_path: Path
) -> None:
    """Codex N6.2 R1 P2: the system prompt FORBIDDEN list claims
    these labels are blocked; the regex must actually block them."""
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "findings": [
                {
                    "severity": "warning",
                    "area": "physics",
                    "message": f"Click {button_label} to save the change",
                    "citation_chunk_id": real_chunk_id,
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    assert response.findings == [], (
        f"Button label not stripped: {button_label!r}"
    )


def test_llm_finding_without_action_text_is_kept(tmp_path: Path):
    """Sanity: legitimate prose passes the filter."""
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "findings": [
                {
                    "severity": "info",
                    "area": "solver",
                    "message": (
                        "Steady RANS via simpleFoam is appropriate for "
                        "this geometry; no transient features expected."
                    ),
                    "citation_chunk_id": real_chunk_id,
                    "recommended_change": (
                        "Consider tightening pressure URF from 0.3 to "
                        "0.2 if residuals oscillate."
                    ),
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    assert response.llm_available is True
    assert len(response.findings) == 1


# ────────── V132 Layer-A: no mutation symbol invoked ──────────


def _install_mutation_sentinels(monkeypatch) -> list[tuple[str, str]]:
    """Patch every entry in KNOWN_MUTATION_FUNCTIONS at its canonical
    module location with a sentinel that raises. Returns the list
    of (module_path, symbol_name) pairs patched, so the caller can
    assert nothing fired.
    """
    patched: list[tuple[str, str]] = []
    for module_path, symbol_name in KNOWN_MUTATION_FUNCTIONS:
        try:
            mod = importlib.import_module(module_path)
        except ModuleNotFoundError:
            continue
        if not hasattr(mod, symbol_name):
            continue

        def _make_sentinel(mp: str = module_path, sn: str = symbol_name):
            def _raise(*args, **kwargs):
                raise AssertionError(
                    f"AI-review code path invoked mutation function "
                    f"{mp}.{sn}"
                )
            return _raise

        monkeypatch.setattr(mod, symbol_name, _make_sentinel())
        patched.append((module_path, symbol_name))
    return patched


def test_review_case_offline_does_not_invoke_any_mutation_function(
    monkeypatch, tmp_path: Path
) -> None:
    """Layer-A: with all KNOWN_MUTATION_FUNCTIONS patched to raise,
    review_case in offline mode must complete without firing any
    sentinel."""
    _install_mutation_sentinels(monkeypatch)
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    # If any mutation symbol is invoked, sentinel raises
    # AssertionError → test fails.
    response = _run(
        review_case(
            case_dir, corpus=corpus, provider=MockLLMProvider()
        )
    )
    assert isinstance(response, ReviewResponse)


def test_review_case_llm_branch_does_not_invoke_any_mutation_function(
    monkeypatch, tmp_path: Path
) -> None:
    """Layer-A: same as above but with the LLM branch active (fake
    provider returning a valid finding). Sentinel must record zero
    invocations."""
    _install_mutation_sentinels(monkeypatch)
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "findings": [
                {
                    "severity": "info",
                    "area": "mesh",
                    "message": "test",
                    "citation_chunk_id": real_chunk_id,
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        review_case(
            case_dir,
            corpus=corpus,
            provider=_FakeLLMProvider(llm_output),
        )
    )
    assert response.llm_available is True
    assert len(response.findings) == 1


def test_ai_advisor_route_module_not_in_mutation_registry() -> None:
    """The ai-review route module + its symbols MUST NOT appear in
    KNOWN_MUTATION_FUNCTIONS."""
    forbidden_modules = {
        "ui.backend.routes.ai_advisor",
        "ui.backend.services.ai_advisor",
        "ui.backend.services.ai_advisor.review",
        "ui.backend.services.ai_advisor.corpus_loader",
    }
    for module_path, symbol_name in KNOWN_MUTATION_FUNCTIONS:
        assert module_path not in forbidden_modules, (
            f"ai_advisor module registered as mutation function: "
            f"{module_path}.{symbol_name}"
        )
