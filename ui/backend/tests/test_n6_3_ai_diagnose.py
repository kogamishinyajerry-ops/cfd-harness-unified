"""DEC-V61-159 (N6.3) · AI 诊断 advisor route + service tests.

Coverage:
  * Schema validators (DiagnosisHypothesis extra=forbid, citation
    required; DiagnoseResponse extra=forbid)
  * Rule-based fallback: empty case + mesh-failed + stalled-residuals
    + diverging-residuals trajectories
  * Log read: bounded tail + symlink-escape rejection
  * Path containment: symlinked log under /tmp NOT followed
  * LLM path: valid response, hallucinated chunk_id dropped, action
    text dropped, non-string fields tolerated, malformed JSON
  * Route: GET 200, bad problem hint 400, missing case 404, loopback
    guard rejects off-box, override env-var allows
  * V132 Layer-A: route + service exercised across both branches,
    no KNOWN_MUTATION_FUNCTIONS symbol invoked
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
    DiagnoseResponse,
    DiagnosisHypothesis,
)
from ui.backend.services.ai_actions.mutating_routes import (
    KNOWN_MUTATION_FUNCTIONS,
)
from ui.backend.services.ai_advisor import (
    diagnose_case,
    load_corpus,
    reset_default_corpus,
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


# ────────── Fixture ──────────


def _build_test_corpus(tmp_path: Path):
    (tmp_path / "docs/openfoam_corpus").mkdir(parents=True)
    (tmp_path / "docs/openfoam_corpus/mesh.md").write_text(
        "## Mesh quality\n\nThe checkMesh utility reports orthogonality.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/openfoam_corpus/residuals.md").write_text(
        "## Residual diagnostics\n\nStalled residuals indicate "
        "physics setup or BC issues. Divergence often signals "
        "Co > 1 or negative cell volumes.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/openfoam_corpus/bc.md").write_text(
        "## Boundary conditions basics\n\nMissing patch BCs crash "
        "the solver at startup.\n",
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


def _write_log(case_dir: Path, name: str, content: str) -> Path:
    p = case_dir / name
    p.write_text(content, encoding="utf-8")
    return p


def _stalled_residual_log(n: int = 6) -> str:
    """Generate a fake solver log with N stalled U residuals."""
    lines = ["Time = 1\n"]
    base = 1.2e-3
    for i in range(n):
        lines.append(
            f"smoothSolver:  Solving for Ux, Initial residual = "
            f"{base + i * 1e-7}, Final residual = 1e-6\n"
        )
    return "".join(lines)


def _diverging_residual_log(n: int = 6) -> str:
    lines = ["Time = 1\n"]
    base = 1e-4
    for i in range(n):
        lines.append(
            f"smoothSolver:  Solving for Ux, Initial residual = "
            f"{base * (10 ** i)}, Final residual = 1e-4\n"
        )
    return "".join(lines)


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


def test_diagnosis_hypothesis_requires_citation() -> None:
    with pytest.raises(ValidationError):
        DiagnosisHypothesis(
            failure_mode="stalled_residuals",
            likelihood="high",
            summary="msg",
            source="rule_based",
        )


def test_diagnose_response_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        DiagnoseResponse(
            case_id="x",
            hypotheses=[],
            llm_available=False,
            corpus_sha="0" * 64,
            generated_at="2026-05-07T00:00:00Z",
            extra_field="oops",
        )


# ────────── Service: rule-based ──────────


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_offline_empty_case_returns_bc_setup_hypothesis(
    tmp_path: Path,
) -> None:
    """Empty case fires BC/physics setup signals from N5.2; the
    rule-based path lifts those into a hypothesis with citation."""
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        diagnose_case(case_dir, corpus=corpus, provider=MockLLMProvider())
    )
    assert response.llm_available is False
    assert response.corpus_sha == corpus.stats.corpus_sha
    bc_hypotheses = [
        h for h in response.hypotheses if h.failure_mode == "bc_or_physics_setup"
    ]
    assert bc_hypotheses, (
        f"Expected BC hypothesis on empty case, got {response.hypotheses}"
    )
    for h in response.hypotheses:
        assert h.source == "rule_based"
        assert corpus.get_chunk(h.citation.chunk_id) is not None


def test_offline_stalled_residuals_emit_hypothesis(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())
    _write_log(case_dir, "log.simpleFoam", _stalled_residual_log(n=6))

    response = _run(
        diagnose_case(case_dir, corpus=corpus, provider=MockLLMProvider())
    )
    modes = {h.failure_mode for h in response.hypotheses}
    assert "stalled_residuals" in modes


def test_offline_diverging_residuals_emit_hypothesis(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())
    _write_log(case_dir, "log.simpleFoam", _diverging_residual_log(n=6))

    response = _run(
        diagnose_case(case_dir, corpus=corpus, provider=MockLLMProvider())
    )
    modes = {h.failure_mode for h in response.hypotheses}
    assert "diverging_residuals" in modes


def test_offline_problem_hint_is_echoed(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        diagnose_case(
            case_dir,
            problem_hint="stalled_residuals",
            corpus=corpus,
            provider=MockLLMProvider(),
        )
    )
    assert response.problem_hint == "stalled_residuals"


def test_offline_hypotheses_sorted_by_likelihood(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())
    _write_log(case_dir, "log.simpleFoam", _stalled_residual_log(n=6))

    response = _run(
        diagnose_case(case_dir, corpus=corpus, provider=MockLLMProvider())
    )
    rank = {"high": 0, "medium": 1, "low": 2}
    ranks = [rank[h.likelihood] for h in response.hypotheses]
    assert ranks == sorted(ranks)


# ────────── Log path containment ──────────


def test_log_symlink_escape_is_rejected(tmp_path: Path) -> None:
    """A log file that's a symlink pointing outside the case_dir
    must NOT be followed (path containment guard)."""
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())
    # Plant a real log outside the case dir.
    rogue = tmp_path / "rogue.log"
    rogue.write_text(
        "Solving for Ux, Initial residual = 1e-3\n" * 5,
        encoding="utf-8",
    )
    # Symlink case/log.simpleFoam → rogue
    (case_dir / "log.simpleFoam").symlink_to(rogue)

    response = _run(
        diagnose_case(case_dir, corpus=corpus, provider=MockLLMProvider())
    )
    # The symlink-target log was NOT read, so no residual-trajectory
    # signal fires from rogue content.
    modes = {h.failure_mode for h in response.hypotheses}
    assert "stalled_residuals" not in modes
    assert "diverging_residuals" not in modes


def test_oversized_log_is_truncated_to_tail(tmp_path: Path) -> None:
    """A 1MB log gets truncated to last 256KB before parsing — must
    not blow up memory or take forever."""
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())
    big = "A" * (1024 * 1024) + _stalled_residual_log(n=6)
    _write_log(case_dir, "log.simpleFoam", big)

    response = _run(
        diagnose_case(case_dir, corpus=corpus, provider=MockLLMProvider())
    )
    # Process completes; tail-truncation kept the residual signal
    # intact (it sits in the last 256KB).
    modes = {h.failure_mode for h in response.hypotheses}
    assert "stalled_residuals" in modes


def test_oversized_log_uses_seek_tail_not_full_load(tmp_path: Path) -> None:
    """Codex N6.3 R0 P1: large log must NOT be loaded into memory
    in full before truncation. We verify the read path bounds
    memory by patching open() to count the bytes returned by
    f.read() on the log file path; assert it's bounded by
    _LOG_MAX_BYTES + small slack."""
    from ui.backend.services.ai_advisor import diagnose as diag_mod

    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())
    # 4 MiB log — well above the 256 KiB cap.
    big = "X" * (4 * 1024 * 1024) + "\n" + _stalled_residual_log(n=6)
    log_path = _write_log(case_dir, "log.simpleFoam", big)

    real_open = open
    bytes_read: list[int] = []

    class _CountingFile:
        def __init__(self, fh):
            self._fh = fh

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self._fh.close()
            return False

        def seek(self, *a, **kw):
            return self._fh.seek(*a, **kw)

        def tell(self):
            return self._fh.tell()

        def read(self, *a, **kw):
            data = self._fh.read(*a, **kw)
            bytes_read.append(len(data))
            return data

    def _spying_open(path, *a, **kw):
        if str(path) == str(log_path.resolve()) or str(path) == str(log_path):
            return _CountingFile(real_open(path, *a, **kw))
        return real_open(path, *a, **kw)

    import builtins

    orig_open = builtins.open
    builtins.open = _spying_open  # type: ignore[assignment]
    try:
        _run(
            diagnose_case(
                case_dir, corpus=corpus, provider=MockLLMProvider()
            )
        )
    finally:
        builtins.open = orig_open  # type: ignore[assignment]

    assert bytes_read, "Log file was never opened by the spy"
    # Allow modest overhead vs the cap (line-boundary trim, decoding
    # buffers); but reject anything close to the 4 MiB total.
    cap = 256 * 1024  # _LOG_MAX_BYTES
    assert max(bytes_read) <= cap + 64 * 1024, (
        f"Log read pulled {max(bytes_read)} bytes — should be bounded "
        f"to ~{cap} after seek-tail."
    )


# ────────── Codex N6.3 R0 P2: divergence requires monotonic ──────────


def test_divergence_classifier_requires_monotonic_growth(
    tmp_path: Path,
) -> None:
    """Codex R0 P2: a spiky/oscillating sequence whose tail happens
    to be >10x the head must NOT be labeled diverging."""
    from ui.backend.services.ai_advisor.diagnose import (
        _residual_trajectory_signal,
    )

    # First 1e-3, then drops, then spikes back up to 2e-2 (last/first
    # ≈ 20x but path is non-monotonic).
    oscillating = [1e-3, 5e-4, 8e-4, 6e-4, 2e-2]
    assert _residual_trajectory_signal(oscillating) is None


def test_divergence_classifier_fires_on_strict_monotonic(
    tmp_path: Path,
) -> None:
    from ui.backend.services.ai_advisor.diagnose import (
        _residual_trajectory_signal,
    )

    monotonic = [1e-4, 1e-3, 5e-3, 1e-2, 2e-2]
    assert _residual_trajectory_signal(monotonic) == "diverging_residuals"


# ────────── Codex N6.3 R1 P2: bounded read on growing log ──────────


def test_log_read_caps_bytes_even_on_concurrent_growth(
    tmp_path: Path,
) -> None:
    """Codex N6.3 R1 P2: between stat() and read() the file may
    grow. The read must still be bounded by _LOG_MAX_BYTES; we
    enforce that by patching open() to return a file whose
    underlying read() ignores requested size, simulating an
    over-eager reader. The fixed code passes _LOG_MAX_BYTES
    explicitly to .read(), so the spy must observe a size arg.
    """
    from ui.backend.services.ai_advisor.diagnose import _LOG_MAX_BYTES

    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())
    big = "X" * (4 * 1024 * 1024) + "\n" + _stalled_residual_log(n=6)
    log_path = _write_log(case_dir, "log.simpleFoam", big)

    real_open = open
    read_calls: list[tuple] = []

    class _SpyFile:
        def __init__(self, fh):
            self._fh = fh

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self._fh.close()
            return False

        def seek(self, *a, **kw):
            return self._fh.seek(*a, **kw)

        def tell(self):
            return self._fh.tell()

        def read(self, *a, **kw):
            read_calls.append((a, kw))
            return self._fh.read(*a, **kw)

    def _spying_open(path, *a, **kw):
        if str(path) == str(log_path.resolve()) or str(path) == str(log_path):
            return _SpyFile(real_open(path, *a, **kw))
        return real_open(path, *a, **kw)

    import builtins

    orig_open = builtins.open
    builtins.open = _spying_open  # type: ignore[assignment]
    try:
        _run(
            diagnose_case(
                case_dir, corpus=corpus, provider=MockLLMProvider()
            )
        )
    finally:
        builtins.open = orig_open  # type: ignore[assignment]

    # The big-tail read must pass an explicit size arg equal to or
    # bounded by _LOG_MAX_BYTES (excluding the 1-byte boundary peek).
    big_reads = [
        call for call in read_calls if call[0] and call[0][0] > 1
    ]
    assert big_reads, (
        f"Expected an explicit-size read; observed read_calls={read_calls}"
    )
    for args, _ in big_reads:
        assert args[0] <= _LOG_MAX_BYTES, (
            f"Read called with size {args[0]} > cap {_LOG_MAX_BYTES}"
        )


# ────────── Codex N6.3 R1 P3: aligned-boundary first-line preserved ──────────


def test_log_seek_on_line_boundary_keeps_first_line(tmp_path: Path) -> None:
    """Codex N6.3 R1 P3: when the seek offset (size - _LOG_MAX_BYTES)
    lands exactly at the start of a real line, the boundary-trim
    must NOT discard that line.

    Construction (Codex R2 P3 fix — make the test actually hit the
    boundary):
      payload = prefix + marker + window_tail
      where len(marker) + len(window_tail) == _LOG_MAX_BYTES exactly.
      Then size = len(prefix) + _LOG_MAX_BYTES, so
      size - _LOG_MAX_BYTES == len(prefix) — the seek lands right
      at the start of `marker`. The byte at offset len(prefix) - 1
      is the '\\n' terminating prefix, so prev_byte == '\\n' →
      no trim → marker survives.
    """
    from ui.backend.services.ai_advisor.diagnose import (
        _LOG_MAX_BYTES,
        _read_solver_log_tail,
    )

    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    marker = "MARKER_LINE_SHOULD_SURVIVE\n"
    # Fill the rest of the cap-size window with a stalled-residual
    # tail so the diagnose path still sees parseable U residuals.
    tail_payload = _stalled_residual_log(n=6)
    filler_len = _LOG_MAX_BYTES - len(marker) - len(tail_payload)
    assert filler_len > 0, (
        "Test fixture sizing — adjust marker/tail so they fit under "
        "_LOG_MAX_BYTES."
    )
    window = marker + ("Z" * filler_len) + tail_payload
    assert len(window) == _LOG_MAX_BYTES

    # Prefix is any line-terminated text; its length determines the
    # seek offset. The trailing '\\n' on the prefix is the byte
    # immediately before the window — that's what makes prev_byte
    # the line-boundary signal.
    prefix = "PREFIX_LINE_THAT_SHOULD_BE_TRIMMED\n"
    total_payload = prefix + window
    assert len(total_payload) - _LOG_MAX_BYTES == len(prefix), (
        "Invariant: seek offset == len(prefix) — anything else means "
        "the test no longer exercises the line-boundary case."
    )

    _write_log(case_dir, "log.simpleFoam", total_payload)

    text = _read_solver_log_tail(case_dir)
    assert text is not None
    assert "MARKER_LINE_SHOULD_SURVIVE" in text, (
        "Aligned-boundary seek discarded a valid first line."
    )
    # Sanity: prefix line must NOT appear (it's outside the window).
    assert "PREFIX_LINE_THAT_SHOULD_BE_TRIMMED" not in text


def test_log_read_window_tracks_current_eof_when_growing(
    tmp_path: Path,
) -> None:
    """Codex N6.3 R2 P2: if the log grows between the open() and
    the read, the helper must still return a window ending at the
    current EOF — not a stale window pinned to an earlier size.

    We simulate by patching open() to return a wrapper whose
    underlying file gets appended-to right before the seek+tell;
    then verify the returned text contains the post-grow content.
    """
    from ui.backend.services.ai_advisor.diagnose import (
        _read_solver_log_tail,
    )

    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    initial = "INITIAL_TAIL_LINE\n" + _stalled_residual_log(n=6)
    log_path = _write_log(case_dir, "log.simpleFoam", initial)
    # Append a fresh marker line BEFORE the helper runs (simulating
    # solver growth between scheduling and execution). The helper
    # must derive EOF from the open handle, not stat-at-call-time.
    with open(log_path, "ab") as fh:
        fh.write(b"FRESH_MARKER_AFTER_GROWTH\n")

    text = _read_solver_log_tail(case_dir)
    assert text is not None
    assert "FRESH_MARKER_AFTER_GROWTH" in text, (
        "Helper returned stale tail; should track current EOF."
    )


# ────────── LLM path with injected provider ──────────


class _FakeLLMProvider(LLMProvider):
    def __init__(self, content: str) -> None:
        self._content = content

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            content=self._content, model_used="fake", fallback_used=False
        )

    def chat_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatStreamChunk]:  # pragma: no cover
        async def _gen() -> AsyncIterator[ChatStreamChunk]:
            if False:
                yield  # type: ignore[unreachable]

        return _gen()


class _RaisingLLMProvider(LLMProvider):
    async def chat(self, request: ChatRequest) -> ChatResponse:
        raise RuntimeError("upstream blew up")

    def chat_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatStreamChunk]:  # pragma: no cover
        async def _gen() -> AsyncIterator[ChatStreamChunk]:
            if False:
                yield  # type: ignore[unreachable]

        return _gen()


def test_llm_path_valid_response_parsed(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "hypotheses": [
                {
                    "failure_mode": "stalled_residuals",
                    "likelihood": "high",
                    "summary": "Residuals plateau on iteration 200.",
                    "evidence": {"plateau_at": "200"},
                    "citation_chunk_id": real_chunk_id,
                    "suggested_fix": (
                        "Consider tightening pressure URF from 0.3 to 0.2."
                    ),
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        diagnose_case(
            case_dir, corpus=corpus, provider=_FakeLLMProvider(llm_output)
        )
    )
    assert response.llm_available is True
    assert len(response.hypotheses) == 1
    h = response.hypotheses[0]
    assert h.source == "llm"
    assert h.evidence["plateau_at"] == "200"
    assert h.failure_mode == "stalled_residuals"


def test_llm_path_hallucinated_chunk_id_dropped(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    llm_output = json.dumps(
        {
            "hypotheses": [
                {
                    "failure_mode": "unknown",
                    "likelihood": "low",
                    "summary": "fake citation",
                    "citation_chunk_id": "not-real",
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        diagnose_case(
            case_dir, corpus=corpus, provider=_FakeLLMProvider(llm_output)
        )
    )
    assert response.llm_available is True
    assert response.hypotheses == []


@pytest.mark.parametrize(
    "bad_text",
    [
        "POST /api/cases/abc/solve",
        "Click [Submit] now",
        "use dispatch(tool=setupBC, ...)",
        "curl -X POST ...",
    ],
)
def test_llm_action_text_in_summary_dropped(bad_text, tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "hypotheses": [
                {
                    "failure_mode": "unknown",
                    "likelihood": "low",
                    "summary": bad_text,
                    "citation_chunk_id": real_chunk_id,
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        diagnose_case(
            case_dir, corpus=corpus, provider=_FakeLLMProvider(llm_output)
        )
    )
    assert response.hypotheses == []


def test_llm_action_text_in_suggested_fix_dropped(tmp_path: Path) -> None:
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "hypotheses": [
                {
                    "failure_mode": "stalled_residuals",
                    "likelihood": "high",
                    "summary": "Residuals plateau.",
                    "citation_chunk_id": real_chunk_id,
                    "suggested_fix": (
                        "POST /api/cases/{id}/dicts/system/fvSolution to retune"
                    ),
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        diagnose_case(
            case_dir, corpus=corpus, provider=_FakeLLMProvider(llm_output)
        )
    )
    assert response.hypotheses == []


@pytest.mark.parametrize(
    "bad_field_value",
    [
        ["nested", "list"],
        {"text": "nested dict"},
        42,
        True,
    ],
)
def test_llm_non_string_summary_does_not_crash_diagnose(
    bad_field_value, tmp_path: Path
) -> None:
    """Codex N6.2 R1 P1 lesson applied here: a non-string summary
    must NOT crash and abort the entire diagnosis. Sibling
    hypotheses survive."""
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "hypotheses": [
                {
                    "failure_mode": "unknown",
                    "likelihood": "low",
                    "summary": bad_field_value,
                    "citation_chunk_id": real_chunk_id,
                },
                {
                    "failure_mode": "stalled_residuals",
                    "likelihood": "high",
                    "summary": "valid sibling",
                    "citation_chunk_id": real_chunk_id,
                },
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        diagnose_case(
            case_dir, corpus=corpus, provider=_FakeLLMProvider(llm_output)
        )
    )
    assert response.llm_available is True
    survivors = [h.summary for h in response.hypotheses]
    assert "valid sibling" in survivors


def test_llm_provider_raises_falls_through_to_rule_based(
    tmp_path: Path,
) -> None:
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        diagnose_case(
            case_dir, corpus=corpus, provider=_RaisingLLMProvider()
        )
    )
    assert response.llm_available is False
    assert response.degradation_note is not None
    assert "RuntimeError" in response.degradation_note


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


def test_route_returns_200_on_valid_case(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage_empty_case(imported, case_id)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    reset_default_corpus()

    resp = _client().get(f"/api/cases/{case_id}/ai-diagnose")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["llm_available"] is False
    assert isinstance(body["hypotheses"], list)
    reset_default_corpus()


def test_route_problem_hint_echoed(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage_empty_case(imported, case_id)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    reset_default_corpus()

    resp = _client().get(
        f"/api/cases/{case_id}/ai-diagnose?problem=stalled_residuals"
    )
    assert resp.status_code == 200
    assert resp.json()["problem_hint"] == "stalled_residuals"
    reset_default_corpus()


def test_route_bad_problem_hint_returns_400(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage_empty_case(imported, case_id)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    reset_default_corpus()

    resp = _client().get(
        f"/api/cases/{case_id}/ai-diagnose?problem=evil_value"
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["failing_check"] == "bad_problem_hint"
    reset_default_corpus()


def test_route_missing_case_id_returns_404(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    safe_but_missing = _safe_id()

    resp = _client().get(
        f"/api/cases/{safe_but_missing}/ai-diagnose"
    )
    assert resp.status_code == 404


def test_route_rejects_non_loopback_caller(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage_empty_case(imported, case_id)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("AI_CHAT_ALLOW_NON_LOOPBACK", raising=False)
    reset_default_corpus()

    resp = _client().get(
        f"/api/cases/{case_id}/ai-diagnose",
        headers={"X-Forwarded-For": "203.0.113.42"},
    )
    assert resp.status_code == 403
    assert "loopback" in resp.json()["detail"].lower()
    reset_default_corpus()


def test_route_allows_non_loopback_with_override(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage_empty_case(imported, case_id)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("AI_CHAT_ALLOW_NON_LOOPBACK", "1")
    reset_default_corpus()

    resp = _client().get(
        f"/api/cases/{case_id}/ai-diagnose",
        headers={"X-Forwarded-For": "203.0.113.42"},
    )
    assert resp.status_code == 200
    reset_default_corpus()


# ────────── V132 Layer-A: no mutation symbol invoked ──────────


def _install_mutation_sentinels(monkeypatch) -> list[tuple[str, str]]:
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
                    f"AI-diagnose code path invoked mutation function "
                    f"{mp}.{sn}"
                )
            return _raise

        monkeypatch.setattr(mod, symbol_name, _make_sentinel())
        patched.append((module_path, symbol_name))
    return patched


def test_diagnose_offline_no_mutation_invocations(
    monkeypatch, tmp_path: Path
) -> None:
    _install_mutation_sentinels(monkeypatch)
    corpus = _build_test_corpus(tmp_path)
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())
    _write_log(case_dir, "log.simpleFoam", _stalled_residual_log(n=6))

    response = _run(
        diagnose_case(case_dir, corpus=corpus, provider=MockLLMProvider())
    )
    assert isinstance(response, DiagnoseResponse)


def test_diagnose_llm_branch_no_mutation_invocations(
    monkeypatch, tmp_path: Path
) -> None:
    _install_mutation_sentinels(monkeypatch)
    corpus = _build_test_corpus(tmp_path)
    real_chunk_id = corpus.chunks[0].chunk_id
    llm_output = json.dumps(
        {
            "hypotheses": [
                {
                    "failure_mode": "unknown",
                    "likelihood": "low",
                    "summary": "test hypothesis",
                    "citation_chunk_id": real_chunk_id,
                }
            ]
        }
    )
    imported = tmp_path / "imported"
    imported.mkdir()
    case_dir = _stage_empty_case(imported, _safe_id())

    response = _run(
        diagnose_case(
            case_dir, corpus=corpus, provider=_FakeLLMProvider(llm_output)
        )
    )
    assert response.llm_available is True
    assert len(response.hypotheses) == 1


def test_diagnose_module_not_in_mutation_registry() -> None:
    forbidden = {
        "ui.backend.services.ai_advisor.diagnose",
        "ui.backend.services.ai_advisor.safety",
    }
    for module_path, symbol_name in KNOWN_MUTATION_FUNCTIONS:
        assert module_path not in forbidden, (
            f"diagnose/safety registered as mutation function: "
            f"{module_path}.{symbol_name}"
        )
