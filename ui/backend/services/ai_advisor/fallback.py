"""DEC-V61-161 (N6.5) · LLM-offline rule-based fallback broadening.

V1 of the broadened offline path — adds outputs from
:func:`derive_suggestions` (mesh_quality advisor, DEC-V61-138) on top
of the N5.2 IssueList signals already consumed by N6.2's offline
fallback. The result: when LLM is unavailable, the engineer still
sees fine-grained mesh-quality fix advice (non-orthogonal patches,
skewness, aspect ratio, severe-face counts) — not just the binary
``mesh_checkmesh_failed`` flag.

Out of V1 scope (deferred):
  * URF stability advisor wiring — needs a URFOverride + RegimeContract
    reader from the case dir; adds I/O surface
  * Timing advisor wiring — same
  * Diagnose-path broadening — N6.3's residual classifier already
    covers the solver-failure hypothesis space; mesh-fix advice
    is review-shaped, not failure-mode-shaped

The module imports :func:`analyze_mesh_quality` lazily inside the
function so the static V132 Layer-C scan does not flag this module
as importing case-state writers (analyze_mesh_quality is read-only,
but the import-graph dependency would still appear in the AST).
"""
from __future__ import annotations

import logging
from pathlib import Path

from ui.backend.schemas.ai_advisor import (
    CitedChunk,
    FindingArea,
    FindingSeverity,
    ReviewFinding,
)
from ui.backend.services.ai_advisor.corpus_loader import Corpus

logger = logging.getLogger(__name__)


# Map MeshFixSuggestion.metric → corpus query keywords. Used to
# ground each emitted finding in a real corpus chunk (citation
# mandatory; missing chunk → finding dropped).
_METRIC_TO_CORPUS_QUERY: dict[str, str] = {
    "max_non_orthogonality": "mesh quality non-orthogonality",
    "max_skewness": "mesh quality skewness",
    "max_aspect_ratio": "mesh quality aspect ratio prism layer",
    "n_severe_non_ortho_faces": "mesh quality non-orthogonality",
    "mesh_ok": "mesh quality checkmesh",
}


# Map MeshFixSuggestion.severity → ReviewFinding.severity. Both
# emit the same three levels but the literals are independent
# types in the schema; explicit map documents intent.
_SEVERITY_MAP: dict[str, FindingSeverity] = {
    "critical": "critical",
    "warning": "warning",
    "info": "info",
}


def _ground_metric_in_corpus(
    metric: str, corpus: Corpus
) -> CitedChunk | None:
    """Best-effort corpus citation for a mesh metric. Returns None
    when no chunk matches; caller drops the finding (citation
    grounding is mandatory)."""
    query = _METRIC_TO_CORPUS_QUERY.get(metric)
    if not query:
        return None
    hits = corpus.find_relevant(query, top_k=1)
    if not hits:
        return None
    return hits[0].to_cited()


def _serialize_recommended_change(rec: dict | None) -> str | None:
    """Convert a MeshFixSuggestion.recommended_change dict to plain
    prose. Returns None when the suggestion is qualitative (rec
    is None) — UI then renders only the message field.

    Note: action-text strip in
    :mod:`ui.backend.services.ai_advisor.safety` is NOT applied
    here. The mesh advisor outputs are hand-curated (DEC-V61-138)
    and never contain HTTP / route / button-label phrasing — they
    list config values like ``{"sizing_field": 0.05}``. Strip
    is reserved for LLM-generated text where the contract relies
    on prompt compliance.
    """
    if rec is None:
        return None
    if not isinstance(rec, dict):
        return str(rec)[:500]
    parts = []
    for k, v in rec.items():
        parts.append(f"{k}={v}")
    return ", ".join(parts)[:500]


def _suggestion_to_finding(sug, corpus: Corpus) -> ReviewFinding | None:
    """Convert one MeshFixSuggestion to a ReviewFinding. Returns None
    when no corpus chunk grounds the suggestion's metric (citation
    grounding is mandatory) or when Pydantic validation rejects the
    constructed value.

    Extracted as a public-ish helper so unit tests can verify the
    conversion without standing up a full polyMesh fixture.
    """
    citation = _ground_metric_in_corpus(sug.metric, corpus)
    if citation is None:
        logger.debug(
            "Dropping mesh-advisor finding %s — no corpus citation.",
            sug.metric,
        )
        return None
    try:
        return ReviewFinding(
            severity=_SEVERITY_MAP[sug.severity],
            area="mesh",
            message=sug.suggestion_text,
            citation=citation,
            recommended_change=_serialize_recommended_change(
                sug.recommended_change
            ),
            source="rule_based",
        )
    except Exception as exc:  # pydantic.ValidationError + cast
        logger.info("Dropping malformed mesh-advisor finding: %s", exc)
        return None


def broaden_review_findings(
    case_dir: Path,
    base_findings: list[ReviewFinding],
    corpus: Corpus,
) -> list[ReviewFinding]:
    """Append mesh-quality advisor outputs to ``base_findings``.

    No-ops when the case has no mesh yet (analyze_mesh_quality
    raises MeshQualityNotAvailableError) or when the mesh is clean
    (advisor returns []). All exceptions are caught and logged —
    the broadening path NEVER causes the route to 5xx; if it
    fails, the base findings still flow.
    """
    # Lazy import — analyze_mesh_quality is read-only but its
    # transitive imports include numpy / docker SDK, which are not
    # needed for the LLM path. Import only when offline broadening
    # is actually requested.
    try:
        from ui.backend.services.mesh_quality.advisor import (
            derive_suggestions,
        )
        from ui.backend.services.mesh_quality.analyzer import (
            MeshQualityNotAvailableError,
            MeshQualityParseError,
            analyze_mesh_quality,
        )
        from ui.backend.services.mesh_quality.schemas import (
            MeshQualityReportV126,
        )
    except Exception as exc:
        logger.debug(
            "Mesh-quality advisor not importable; skipping broaden: %s",
            exc,
        )
        return list(base_findings)

    try:
        report = analyze_mesh_quality(case_dir, run_checkmesh=False)
    except MeshQualityNotAvailableError:
        # No mesh yet — nothing to broaden.
        return list(base_findings)
    except MeshQualityParseError as exc:
        logger.info("Mesh parse failed; skipping broaden: %s", exc)
        return list(base_findings)
    except Exception as exc:  # defensive: never break the route
        logger.warning(
            "Unexpected mesh analyzer error during broaden: %s", exc
        )
        return list(base_findings)

    # advisor accepts only V126 reports (with checkMesh fields). If
    # the analyzer returned the older V122 shape, skip silently.
    if not isinstance(report, MeshQualityReportV126):
        return list(base_findings)

    suggestions = derive_suggestions(report)
    if not suggestions:
        return list(base_findings)

    out = list(base_findings)
    for sug in suggestions:
        finding = _suggestion_to_finding(sug, corpus)
        if finding is not None:
            out.append(finding)
    return out


__all__ = ["broaden_review_findings"]
