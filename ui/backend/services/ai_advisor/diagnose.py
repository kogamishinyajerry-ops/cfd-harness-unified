"""DEC-V61-159 (N6.3) · AI 诊断 (case diagnose) advisor service.

Read-only by construction. The service:

  1. Reads case state via :func:`enumerate_issues` (N5.2 — read-only)
     and the per-case solver log (path-restricted to ``case_dir/log.*``,
     bounded to last 200 lines).
  2. Retrieves relevant corpus chunks via the N6.1 loader.
  3. Either:
     a. Calls the LLM with a structured diagnostic prompt and
        citation-grounding contract, OR
     b. Falls back to rule-based hypotheses derived from the
        IssueList + residual-trajectory pattern, when the LLM
        provider is the mock OR LLM call fails.
  4. Drops any hypothesis whose citation does not resolve, or whose
     ``summary`` / ``suggested_fix`` text contains action-text patterns
     (server-side advisory-only enforcement, shared with N6.2).

Read-only file ops only: log files are read with ``open()`` after a
``Path.is_file()`` + ``.resolve()`` containment check that prevents
symlink escape from ``case_dir``.
"""
from __future__ import annotations

import io
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ui.backend.schemas.ai_advisor import (
    CitedChunk,
    DiagnoseResponse,
    DiagnosisHypothesis,
    FailureMode,
    HypothesisLikelihood,
)
from ui.backend.schemas.honest_issue_list import IssueList
from ui.backend.services.ai_advisor.corpus_loader import (
    Corpus,
    LoadedChunk,
    get_default_corpus,
)
from ui.backend.services.ai_advisor.safety import has_action_text
from ui.backend.services.case_issues import enumerate_issues
from ui.backend.services.llm_provider.base import (
    ChatMessage,
    ChatRequest,
    LLMProvider,
)
from ui.backend.services.llm_provider.factory import get_default_provider

logger = logging.getLogger(__name__)


# Bounded log read: last N lines × N chars cap. Prevents prompt
# explosion + memory pressure on engineer-supplied giant logs.
_LOG_TAIL_LINES = 200
_LOG_MAX_BYTES = 256 * 1024  # 256 KiB

# Solver log filename whitelist (matches N5.2 enumerator's set).
_LOG_BASENAMES: tuple[str, ...] = (
    "log.icoFoam",
    "log.simpleFoam",
    "log.pimpleFoam",
    "log.buoyantSimpleFoam",
    "log.buoyantPimpleFoam",
)

# Failure-mode → corpus query keywords (offline path) + the
# rule-id signals that drive the rule-based hypothesis emission.
_FAILURE_MODE_QUERY: dict[FailureMode, str] = {
    "stalled_residuals": "residual diagnostics solver convergence",
    "diverging_residuals": "residual diagnostics divergence",
    "mesh_quality_critical": "mesh quality checkmesh non-orthogonality",
    "bc_or_physics_setup": "boundary conditions solver selection",
    "unknown": "residual diagnostics solver",
}

# U-residual extraction reused from N5.2 enumerator pattern (kept
# local to avoid an N5.2 → N6 reverse import edge).
_RES_RE = re.compile(
    r"Solving for U[xX]?[yY]?[zZ]?,\s*Initial residual\s*=\s*([-0-9.eE+]+)",
)


def _now_iso() -> str:
    return (
        datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    )


def _read_solver_log_tail(case_dir: Path) -> Optional[str]:
    """Return the last N lines of the case's solver log, or None.

    Path containment: each candidate is resolved and checked to live
    under ``case_dir.resolve()`` before reading. Symlinks pointing
    outside the case directory are rejected.

    Bounded read (Codex N6.3 R0 P1): for files larger than
    ``_LOG_MAX_BYTES``, seek to the tail rather than loading the
    entire file into memory. A 1 GiB log is read as 256 KiB +
    one ``stat`` call, not 1 GiB into RAM.
    """
    try:
        case_root = case_dir.resolve()
    except OSError:
        return None
    for basename in _LOG_BASENAMES:
        candidate = case_dir / basename
        if not candidate.is_file():
            continue
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        # Containment: resolved log path MUST be under case_root.
        try:
            resolved.relative_to(case_root)
        except ValueError:
            logger.warning(
                "Skipping log %s — symlink escapes case_dir.", candidate
            )
            continue
        try:
            with open(resolved, "rb") as fh:
                # Codex N6.3 R2 P2: derive the EOF from the open
                # file handle (not a separate stat()) so the tail
                # window ends at the current EOF — a live solver
                # appending bytes between stat() and read() will not
                # cause us to return a stale window pinned to the
                # old size.
                fh.seek(0, io.SEEK_END)
                current_size = fh.tell()
                seek_offset = max(0, current_size - _LOG_MAX_BYTES)
                # Codex N6.3 R1 P2: pass an explicit read length so
                # the cap holds regardless of further growth between
                # this seek and the read.
                if seek_offset > 0:
                    # Codex N6.3 R1 P3: peek the byte immediately
                    # before the window. If it is '\n' the window
                    # starts on a clean line boundary — keep the
                    # whole window. If it is anything else we landed
                    # mid-line and must trim through the first '\n'.
                    fh.seek(seek_offset - 1)
                    prev_byte = fh.read(1)
                    data = fh.read(_LOG_MAX_BYTES)
                    if prev_byte != b"\n":
                        nl_idx = data.find(b"\n")
                        if nl_idx != -1:
                            data = data[nl_idx + 1 :]
                else:
                    fh.seek(0)
                    data = fh.read(_LOG_MAX_BYTES)
        except OSError:
            continue
        try:
            text = data.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            continue
        lines = text.splitlines()
        return "\n".join(lines[-_LOG_TAIL_LINES:])
    return None


def _extract_recent_u_residuals(text: str, *, n: int = 5) -> list[float]:
    out: list[float] = []
    for m in _RES_RE.finditer(text):
        try:
            out.append(float(m.group(1)))
        except ValueError:
            continue
    return out[-n:]


def _residual_trajectory_signal(
    residuals: list[float],
) -> Optional[FailureMode]:
    """Classify a residual sequence into a failure_mode signal.

    Returns None when the sequence is empty, oscillating, or
    converging cleanly.

    Codex N6.3 R0 P2: divergence requires **monotonic** growth,
    not just first-vs-last ratio. A spiky/oscillating run whose
    final sample happens to land >10x above the first must NOT
    be labeled diverging — that's the wrong top hypothesis and
    misleads the engineer toward Co-reduction fixes when the
    real issue is solver instability.
    """
    if len(residuals) < 2:
        return None
    # Diverging: monotonic increase across every consecutive pair
    # AND ≥10x ratio from first to last.
    first = residuals[0]
    last = residuals[-1]
    if first > 0 and last / first > 10.0:
        is_monotonic_increasing = all(
            residuals[i] >= residuals[i - 1] for i in range(1, len(residuals))
        )
        if is_monotonic_increasing:
            return "diverging_residuals"
        # Falls through: ratio satisfied but not monotonic →
        # oscillating; no signal emitted (uncertain trajectory
        # is better than wrong hypothesis).
    # Stalled: every consecutive delta below 1% relative.
    for i in range(1, len(residuals)):
        prev = residuals[i - 1]
        curr = residuals[i]
        if prev == 0:
            return None
        rel = abs(curr - prev) / abs(prev)
        if rel >= 0.01:
            return None
    return "stalled_residuals"


def _ground_in_corpus(
    failure_mode: FailureMode, corpus: Corpus
) -> Optional[CitedChunk]:
    """Best-effort corpus citation for a rule-based hypothesis.

    Returns None when no corpus chunk matches; caller drops the
    hypothesis (citation grounding is mandatory).
    """
    query = _FAILURE_MODE_QUERY.get(failure_mode)
    if not query:
        return None
    hits = corpus.find_relevant(query, top_k=1)
    if not hits:
        return None
    return hits[0].to_cited()


def _rule_based_hypotheses(
    issues: IssueList,
    log_tail: Optional[str],
    corpus: Corpus,
) -> list[DiagnosisHypothesis]:
    """Derive hypotheses from N5.2 issue signals + residual trajectory.

    No LLM, no prose generation. Each hypothesis carries structured
    evidence keyed off the case state the engineer can verify.
    """
    out: list[DiagnosisHypothesis] = []
    rule_ids = {i.source_rule_id for i in issues.issues}

    # Mesh-quality signal
    mesh_signals = {
        "mesh_checkmesh_failed",
        "mesh_severe_non_ortho_faces",
        "mesh_zero_cells",
    }
    if rule_ids & mesh_signals:
        citation = _ground_in_corpus("mesh_quality_critical", corpus)
        if citation is not None:
            triggers = sorted(rule_ids & mesh_signals)
            out.append(
                DiagnosisHypothesis(
                    failure_mode="mesh_quality_critical",
                    likelihood="high",
                    summary=(
                        "checkMesh reports severe quality issues; "
                        "solver results may be unreliable until mesh "
                        "is rebuilt."
                    ),
                    evidence={"triggered_rules": ",".join(triggers)},
                    citation=citation,
                    suggested_fix=None,
                    source="rule_based",
                )
            )

    # BC / physics signal
    bc_signals = {
        "physics_dicts_missing",
        "physics_regime_missing",
        "geometry_no_named_patches",
    }
    if rule_ids & bc_signals:
        citation = _ground_in_corpus("bc_or_physics_setup", corpus)
        if citation is not None:
            triggers = sorted(rule_ids & bc_signals)
            out.append(
                DiagnosisHypothesis(
                    failure_mode="bc_or_physics_setup",
                    likelihood="high",
                    summary=(
                        "Boundary or physics setup is incomplete; "
                        "solver may crash at startup or produce "
                        "garbage results."
                    ),
                    evidence={"triggered_rules": ",".join(triggers)},
                    citation=citation,
                    suggested_fix=None,
                    source="rule_based",
                )
            )

    # Residual-trajectory signal (stalled / diverging)
    if log_tail:
        residuals = _extract_recent_u_residuals(log_tail, n=5)
        traj_mode = _residual_trajectory_signal(residuals)
        if traj_mode is not None:
            citation = _ground_in_corpus(traj_mode, corpus)
            if citation is not None:
                if traj_mode == "stalled_residuals":
                    summary = (
                        "U residuals plateaued; consecutive deltas "
                        "below 1% relative change."
                    )
                else:
                    summary = (
                        "U residuals trending upward by more than 10x; "
                        "solver is diverging."
                    )
                out.append(
                    DiagnosisHypothesis(
                        failure_mode=traj_mode,
                        likelihood="high",
                        summary=summary,
                        evidence={
                            "last_residuals": ",".join(
                                f"{r:.3e}" for r in residuals
                            ),
                        },
                        citation=citation,
                        suggested_fix=None,
                        source="rule_based",
                    )
                )

    return out


def _build_diagnose_prompt(
    *,
    case_id: str,
    issues: IssueList,
    log_tail: Optional[str],
    relevant_chunks: list[LoadedChunk],
    problem_hint: Optional[FailureMode],
) -> list[ChatMessage]:
    """Assemble the LLM chat messages for diagnosis composition.

    System prompt locks the same advisory-only contract enforced by
    N6.2 (no route descriptors, no button labels, no shell mutations);
    server-side ``has_action_text`` is the backstop.
    """
    corpus_block_lines: list[str] = []
    for chunk in relevant_chunks:
        anchor = chunk.section_anchor or "<preamble>"
        snippet = chunk.text[:400].replace("\n", " ")
        corpus_block_lines.append(
            f"chunk_id={chunk.chunk_id} | path={chunk.path} | "
            f"section={anchor} | text={snippet}"
        )
    corpus_block = (
        "\n".join(corpus_block_lines) if corpus_block_lines else "(no chunks)"
    )

    issues_block_lines: list[str] = []
    for issue in issues.issues:
        issues_block_lines.append(
            f"- [{issue.severity}] {issue.scope}/{issue.source_rule_id}: "
            f"{issue.message}"
        )
    issues_block = (
        "\n".join(issues_block_lines) if issues_block_lines else "(no issues)"
    )

    log_block = (
        f"```\n{log_tail}\n```"
        if log_tail
        else "(no solver log present)"
    )

    hint_block = (
        f"PROBLEM HINT: engineer suspects '{problem_hint}'. Bias your "
        "ranking accordingly but enumerate other plausible modes too.\n\n"
        if problem_hint
        else ""
    )

    system = (
        "You are a CFD case diagnostic assistant. You have READ-ONLY "
        "access. Never recommend writes, route calls, or button "
        "actions. FORBIDDEN in 'summary' and 'suggested_fix': any HTTP "
        "method + path (e.g. 'POST /api/...'), any '/api/...' string, "
        "any button-style label like [Apply] / [Submit] / [Confirm] / "
        "[Commit] / [Save] / [应用] / [提交] / [执行] / [保存], "
        "any curl/wget command, any 'dispatch(tool=...)' phrasing. The "
        "server drops hypotheses whose text contains those patterns. "
        "Output valid JSON of shape "
        '{"hypotheses": [{"failure_mode": "stalled_residuals|'
        'diverging_residuals|mesh_quality_critical|bc_or_physics_setup|'
        'unknown", "likelihood": "high|medium|low", '
        '"summary": "<short factual statement>", '
        '"evidence": {"<key>": "<stringified value>"}, '
        '"citation_chunk_id": "<exact chunk_id from CORPUS block>", '
        '"suggested_fix": "<optional metadata-only prose>"}]}. '
        "Cite only chunk_ids from the CORPUS block. Drop any hypothesis "
        "you cannot ground in a real chunk_id."
    )

    user = (
        f"CASE_ID: {case_id}\n\n"
        f"{hint_block}"
        f"DETECTED ISSUES (N5.2 enumerator):\n{issues_block}\n\n"
        f"SOLVER LOG TAIL (last {_LOG_TAIL_LINES} lines):\n{log_block}\n\n"
        f"CORPUS (relevant chunks):\n{corpus_block}\n\n"
        "Produce the JSON now."
    )

    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user),
    ]


def _parse_llm_hypotheses(
    raw: str, corpus: Corpus
) -> tuple[list[DiagnosisHypothesis], int]:
    """Parse LLM JSON output into validated DiagnosisHypotheses.

    Same drop semantics as N6.2 ``_parse_llm_findings``: malformed
    JSON / missing fields / hallucinated chunk_id / action-text in
    summary or suggested_fix → drop the individual hypothesis,
    keep siblings.
    """
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].lstrip()
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("LLM diagnose JSON parse failed: %s", exc)
        return ([], -1)

    if not isinstance(parsed, dict) or "hypotheses" not in parsed:
        logger.warning("LLM diagnose JSON missing 'hypotheses' key.")
        return ([], -1)

    raw_list = parsed.get("hypotheses", [])
    if not isinstance(raw_list, list):
        return ([], -1)

    hypotheses: list[DiagnosisHypothesis] = []
    dropped = 0
    for raw_h in raw_list:
        if not isinstance(raw_h, dict):
            dropped += 1
            continue
        chunk_id = raw_h.get("citation_chunk_id")
        if not isinstance(chunk_id, str):
            dropped += 1
            continue
        loaded = corpus.get_chunk(chunk_id)
        if loaded is None:
            logger.info(
                "Dropping LLM hypothesis citing unknown chunk_id=%s.",
                chunk_id,
            )
            dropped += 1
            continue

        candidate_summary = raw_h.get("summary", "")
        candidate_fix = raw_h.get("suggested_fix")
        if has_action_text(candidate_summary) or has_action_text(
            candidate_fix
        ):
            logger.info(
                "Dropping LLM hypothesis with action-text "
                "(summary=%r suggested_fix=%r).",
                candidate_summary,
                candidate_fix,
            )
            dropped += 1
            continue

        # Evidence: server-side stringify any non-string values so
        # the schema (dict[str, str]) accepts the wire shape.
        raw_evidence = raw_h.get("evidence", {})
        if not isinstance(raw_evidence, dict):
            raw_evidence = {}
        evidence: dict[str, str] = {}
        for k, v in raw_evidence.items():
            if not isinstance(k, str):
                continue
            evidence[k] = str(v) if v is not None else ""

        try:
            hyp = DiagnosisHypothesis(
                failure_mode=raw_h.get("failure_mode"),
                likelihood=raw_h.get("likelihood"),
                summary=candidate_summary,
                evidence=evidence,
                citation=loaded.to_cited(),
                suggested_fix=candidate_fix,
                source="llm",
            )
        except Exception as exc:
            logger.info("Dropping malformed LLM hypothesis: %s", exc)
            dropped += 1
            continue
        hypotheses.append(hyp)
    return (hypotheses, dropped)


_LIKELIHOOD_RANK: dict[HypothesisLikelihood, int] = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def _is_mock_provider(provider: LLMProvider) -> bool:
    from ui.backend.services.llm_provider.base import MockLLMProvider

    return isinstance(provider, MockLLMProvider)


async def diagnose_case(
    case_dir: Path,
    *,
    problem_hint: Optional[FailureMode] = None,
    corpus: Optional[Corpus] = None,
    provider: Optional[LLMProvider] = None,
) -> DiagnoseResponse:
    """Build a DiagnoseResponse for the given case.

    Parameters
    ----------
    problem_hint
        Optional failure-mode the engineer suspects. The route
        validates this against the ``FailureMode`` literal before
        calling the service.
    """
    if corpus is None:
        corpus = get_default_corpus()
    if provider is None:
        provider = get_default_provider()

    issues = enumerate_issues(case_dir)
    log_tail = _read_solver_log_tail(case_dir)

    if _is_mock_provider(provider):
        hypotheses = _rule_based_hypotheses(issues, log_tail, corpus)
        hypotheses.sort(
            key=lambda h: (_LIKELIHOOD_RANK[h.likelihood], h.failure_mode)
        )
        return DiagnoseResponse(
            case_id=case_dir.name,
            problem_hint=problem_hint,
            hypotheses=hypotheses,
            llm_available=False,
            corpus_sha=corpus.stats.corpus_sha,
            degradation_note=(
                "DEEPSEEK_API_KEY unset — rule-based hypotheses derived "
                "from N5.2 issue signals + residual trajectory pattern."
            ),
            generated_at=_now_iso(),
        )

    # LLM path
    relevant_chunks: list[LoadedChunk] = []
    seen_ids: set[str] = set()
    query_terms: list[str] = []
    if problem_hint:
        query_terms.append(_FAILURE_MODE_QUERY[problem_hint])
    if issues.issues:
        query_terms.append(
            " ".join(i.source_rule_id.replace("_", " ") for i in issues.issues)
        )
    if not query_terms:
        query_terms.append("residual diagnostics mesh quality solver")
    query = " ".join(query_terms)
    for chunk in corpus.find_relevant(query, top_k=8):
        if chunk.chunk_id in seen_ids:
            continue
        seen_ids.add(chunk.chunk_id)
        relevant_chunks.append(chunk)

    messages = _build_diagnose_prompt(
        case_id=case_dir.name,
        issues=issues,
        log_tail=log_tail,
        relevant_chunks=relevant_chunks,
        problem_hint=problem_hint,
    )

    try:
        request = ChatRequest(messages=messages, max_tokens=2048)
        response = await provider.chat(request)
        hypotheses, _dropped = _parse_llm_hypotheses(response.content, corpus)
        hypotheses.sort(
            key=lambda h: (_LIKELIHOOD_RANK[h.likelihood], h.failure_mode)
        )
        return DiagnoseResponse(
            case_id=case_dir.name,
            problem_hint=problem_hint,
            hypotheses=hypotheses,
            llm_available=True,
            corpus_sha=corpus.stats.corpus_sha,
            degradation_note=None,
            generated_at=_now_iso(),
        )
    except Exception as exc:
        logger.warning(
            "LLM diagnose failed (%s); falling through to rule-based.",
            exc,
        )
        hypotheses = _rule_based_hypotheses(issues, log_tail, corpus)
        hypotheses.sort(
            key=lambda h: (_LIKELIHOOD_RANK[h.likelihood], h.failure_mode)
        )
        return DiagnoseResponse(
            case_id=case_dir.name,
            problem_hint=problem_hint,
            hypotheses=hypotheses,
            llm_available=False,
            corpus_sha=corpus.stats.corpus_sha,
            degradation_note=(
                f"LLM call failed ({type(exc).__name__}); served "
                "rule-based hypotheses."
            ),
            generated_at=_now_iso(),
        )


__all__ = ["diagnose_case"]
