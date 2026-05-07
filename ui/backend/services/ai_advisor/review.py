"""DEC-V61-158 (N6.2) · AI 审查 (case review) advisor service.

Read-only by construction. The service:

  1. Reads case state via :func:`enumerate_issues` (N5.2 — itself
     read-only) and :func:`build_beginner_report` (N5.1 — read-only).
  2. Retrieves relevant corpus chunks via the N6.1 loader.
  3. Either:
     a. Calls the LLM with a structured prompt and citation-grounding
        contract, OR
     b. Falls back to rule-based emission (consumes the N5.2
        IssueList directly), when the LLM provider is the mock.
  4. Drops any finding whose citation chunk_id does not resolve to a
     loaded corpus chunk.

The service does NOT import any symbol in
``KNOWN_MUTATION_FUNCTIONS`` (V132 Layer-C); the V132 Layer-A test
exercises the route across both LLM and offline branches and asserts
zero mutation symbols are invoked.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ui.backend.schemas.ai_advisor import (
    CitedChunk,
    FindingArea,
    FindingSeverity,
    ReviewFinding,
    ReviewResponse,
)
from ui.backend.schemas.honest_issue_list import IssueList, IssueScope
from ui.backend.services.ai_advisor.corpus_loader import (
    Corpus,
    LoadedChunk,
    get_default_corpus,
)
from ui.backend.services.case_issues import enumerate_issues
from ui.backend.services.llm_provider.base import (
    ChatMessage,
    ChatRequest,
    LLMProvider,
)
from ui.backend.services.llm_provider.factory import get_default_provider

logger = logging.getLogger(__name__)


# Mapping from N5.2 source_rule_id → corpus query keywords. Used by
# rule-based fallback to ground each issue in a corpus citation.
# Keywords are picked from the seed corpus' anchor headers + body
# tokens; if the corpus expands, this map must expand too.
_RULE_TO_CORPUS_QUERY: dict[str, str] = {
    # Geometry — no dedicated corpus doc yet; use BC-related when
    # surface meshing patches are missing
    "geometry_stl_missing": "boundary conditions patches",
    "geometry_bbox_missing": "boundary conditions patches",
    "geometry_no_named_patches": "boundary conditions patches",
    # Mesh
    "mesh_polymesh_missing": "mesh quality checkmesh",
    "mesh_zero_cells": "mesh quality checkmesh",
    "mesh_dense_warning": "mesh quality checkmesh",
    "mesh_low_count_warning": "mesh quality checkmesh",
    "mesh_checkmesh_failed": "mesh quality checkmesh",
    "mesh_severe_non_ortho_faces": "mesh quality non-orthogonality",
    # Physics — closest corpus seed is solver / BC docs
    "physics_dicts_missing": "solver selection",
    "physics_regime_missing": "solver selection",
    "physics_no_citation": "solver selection",
    # Solver
    "solver_no_derivation": "solver selection simpleFoam",
    "solver_tolerance_fast_survey": "under relaxation factors",
    "solver_les_subgrid_todo": "solver selection LES",
    # Output
    "output_residuals_stalled": "residual diagnostics",
    "output_run_log_missing": "residual diagnostics",
}


# IssueScope (N5.2) → FindingArea (N6.2). Both literals share the
# same five values so the cast is identity, but we keep the explicit
# map as a future-proofing point.
_SCOPE_TO_AREA: dict[IssueScope, FindingArea] = {
    "geometry": "geometry",
    "mesh": "mesh",
    "physics": "physics",
    "solver": "solver",
    "output": "output",
}


def _now_iso() -> str:
    return (
        datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    )


def _ground_issue_in_corpus(
    rule_id: str, corpus: Corpus
) -> Optional[CitedChunk]:
    """Best-effort corpus citation for a rule-based issue.

    Returns None if no corpus chunk matches; caller drops the finding
    in that case (per charter "missing chunk → finding dropped").
    """
    query = _RULE_TO_CORPUS_QUERY.get(rule_id)
    if not query:
        return None
    hits = corpus.find_relevant(query, top_k=1)
    if not hits:
        return None
    return hits[0].to_cited()


def _issue_list_to_findings(
    issues: IssueList, corpus: Corpus
) -> list[ReviewFinding]:
    """Convert N5.2 IssueList → N6.2 ReviewFinding[] with citations.

    Findings whose source_rule_id has no corpus mapping (or whose
    mapped query yields no hits) are dropped — citation grounding is
    mandatory.
    """
    findings: list[ReviewFinding] = []
    for issue in issues.issues:
        citation = _ground_issue_in_corpus(issue.source_rule_id, corpus)
        if citation is None:
            logger.debug(
                "Dropping rule-based finding %s — no corpus citation.",
                issue.source_rule_id,
            )
            continue
        findings.append(
            ReviewFinding(
                severity=issue.severity,
                area=_SCOPE_TO_AREA[issue.scope],
                message=issue.message,
                citation=citation,
                recommended_change=None,
                source="rule_based",
            )
        )
    return findings


def _is_mock_provider(provider: LLMProvider) -> bool:
    """True iff the provider is the mock (no DEEPSEEK_API_KEY set).

    Imported lazily so the schema-test path doesn't pull the
    DeepSeekProvider's httpx dependency tree.
    """
    from ui.backend.services.llm_provider.base import MockLLMProvider

    return isinstance(provider, MockLLMProvider)


def _build_review_prompt(
    *,
    case_id: str,
    issues: IssueList,
    relevant_chunks: list[LoadedChunk],
) -> list[ChatMessage]:
    """Assemble the LLM chat messages for review composition.

    System message locks the contract:
      * Output: JSON only, schema-conforming
      * No mutating language ("apply", "POST", "PUT", path slugs)
      * Each finding MUST cite a chunk_id from the supplied corpus
        block; the service drops findings with unresolvable chunk_ids
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

    system = (
        "You are a CFD case reviewer. You have READ-ONLY access. "
        "Never recommend writes, route calls, or [Apply] actions. "
        "Output valid JSON of shape "
        '{"findings": [{"severity": "critical|warning|info", '
        '"area": "geometry|mesh|physics|solver|output", '
        '"message": "<short factual statement>", '
        '"citation_chunk_id": "<exact chunk_id from CORPUS block>", '
        '"recommended_change": "<optional metadata-only suggestion>"}]}. '
        "Cite only chunk_ids from the CORPUS block. Drop any finding "
        "you cannot ground in a real chunk_id."
    )

    user = (
        f"CASE_ID: {case_id}\n\n"
        f"DETECTED ISSUES (N5.2 enumerator, structured):\n{issues_block}\n\n"
        f"CORPUS (relevant chunks):\n{corpus_block}\n\n"
        "Produce the JSON now."
    )

    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user),
    ]


def _parse_llm_findings(
    raw: str, corpus: Corpus
) -> tuple[list[ReviewFinding], int]:
    """Parse the LLM's JSON output into validated ReviewFindings.

    Returns ``(findings, dropped_count)``. Findings are dropped if:
      * JSON malformed (returns empty list, dropped_count = -1)
      * Missing required fields (Pydantic validation error)
      * citation_chunk_id does not resolve to a loaded corpus chunk
    """
    try:
        # Tolerate LLMs that wrap output in ```json fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].lstrip()
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("LLM review JSON parse failed: %s", exc)
        return ([], -1)

    if not isinstance(parsed, dict) or "findings" not in parsed:
        logger.warning("LLM review JSON missing 'findings' key.")
        return ([], -1)

    raw_findings = parsed.get("findings", [])
    if not isinstance(raw_findings, list):
        return ([], -1)

    findings: list[ReviewFinding] = []
    dropped = 0
    for raw_finding in raw_findings:
        if not isinstance(raw_finding, dict):
            dropped += 1
            continue
        chunk_id = raw_finding.get("citation_chunk_id")
        if not isinstance(chunk_id, str):
            dropped += 1
            continue
        loaded = corpus.get_chunk(chunk_id)
        if loaded is None:
            logger.info(
                "Dropping LLM finding citing unknown chunk_id=%s.", chunk_id
            )
            dropped += 1
            continue
        try:
            finding = ReviewFinding(
                severity=raw_finding.get("severity"),
                area=raw_finding.get("area"),
                message=raw_finding.get("message", ""),
                citation=loaded.to_cited(),
                recommended_change=raw_finding.get("recommended_change"),
                source="llm",
            )
        except Exception as exc:  # pydantic.ValidationError + bad-cast
            logger.info("Dropping malformed LLM finding: %s", exc)
            dropped += 1
            continue
        findings.append(finding)
    return (findings, dropped)


async def review_case(
    case_dir: Path,
    *,
    corpus: Optional[Corpus] = None,
    provider: Optional[LLMProvider] = None,
) -> ReviewResponse:
    """Build a ReviewResponse for the given case directory.

    Parameters mirror the route signature; both ``corpus`` and
    ``provider`` are injected during testing. Production callers
    omit them and get the process singletons.
    """
    if corpus is None:
        corpus = get_default_corpus()
    if provider is None:
        provider = get_default_provider()

    issues = enumerate_issues(case_dir)

    # LLM-offline branch: rule-based subset (N6.5 will broaden with
    # more rule-based emitters).
    if _is_mock_provider(provider):
        findings = _issue_list_to_findings(issues, corpus)
        return ReviewResponse(
            case_id=case_dir.name,
            findings=findings,
            llm_available=False,
            corpus_sha=corpus.stats.corpus_sha,
            degradation_note=(
                "DEEPSEEK_API_KEY unset — rule-based subset of N5.2 "
                "honest issue list grounded in corpus. N6.5 will "
                "broaden the rule-based emitter set."
            ),
            generated_at=_now_iso(),
        )

    # LLM branch: retrieve relevant corpus chunks, build prompt,
    # call provider, parse + ground citations.
    relevant_chunks: list[LoadedChunk] = []
    seen_ids: set[str] = set()
    # Build a query from the issue messages — what the engineer would
    # ask: "what's wrong with my mesh / physics / solver".
    if issues.issues:
        query_terms = " ".join(
            i.source_rule_id.replace("_", " ") for i in issues.issues
        )
    else:
        query_terms = "mesh quality solver selection boundary conditions"
    for chunk in corpus.find_relevant(query_terms, top_k=8):
        if chunk.chunk_id in seen_ids:
            continue
        seen_ids.add(chunk.chunk_id)
        relevant_chunks.append(chunk)

    messages = _build_review_prompt(
        case_id=case_dir.name,
        issues=issues,
        relevant_chunks=relevant_chunks,
    )

    try:
        request = ChatRequest(messages=messages, max_tokens=2048)
        response = await provider.chat(request)
        findings, dropped = _parse_llm_findings(response.content, corpus)
        if not findings and dropped <= 0:
            # LLM returned valid JSON but zero findings — that's a
            # legitimate "no issues" answer; pass through.
            pass
        return ReviewResponse(
            case_id=case_dir.name,
            findings=findings,
            llm_available=True,
            corpus_sha=corpus.stats.corpus_sha,
            degradation_note=None,
            generated_at=_now_iso(),
        )
    except Exception as exc:
        logger.warning(
            "LLM review failed (%s); falling through to rule-based.", exc
        )
        findings = _issue_list_to_findings(issues, corpus)
        return ReviewResponse(
            case_id=case_dir.name,
            findings=findings,
            llm_available=False,
            corpus_sha=corpus.stats.corpus_sha,
            degradation_note=(
                f"LLM call failed ({type(exc).__name__}); served "
                "rule-based subset."
            ),
            generated_at=_now_iso(),
        )


__all__ = ["review_case"]
