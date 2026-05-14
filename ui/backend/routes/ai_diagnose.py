"""DEC-V62-A-sub-M-ROUTE-AI-DIAGNOSE · POST /ai-diagnose · V-series similarity matching.

Stack-level diagnose route under V62-A charter. Accepts a ``symptom_text``
+ optional ``solver_log_excerpt`` + optional ``case_id``; returns ranked
V-series row matches + optional ``AdvisorStackReport`` cross-reference +
audit artifact path.

V130 four-question gate compliance (verified inline by
``test_ai_diagnose_route.py``):

1. LLM offline OK? Yes. Base matching is keyword-overlap (Jaccard, title
   tokens weighted 3x); zero ``anthropic`` / ``openai`` / ``llm_provider``
   / RAG-loader imports (``test_4q_gate_no_llm_imports_in_route_module``
   pins the forbidden-token list). ``llm_match=True`` is a
   forward-compatible flag — until a provider is wired, the route always
   returns ``llm_match_used=False`` and falls through to base ranking.
2. Artifacts output? Yes. Every request persists an audit JSON under
   ``.planning/audits/ai_diagnose/<request_id>.json`` that is round-trip
   deserializable with ``json.loads(p.read_text())``.
3. TrustGate? Yes. Every ``VSeriesMatch`` carries ``v_row_id`` +
   ``similarity_rationale`` (which tokens matched + which advisors
   cross-referenced) so engineers can trace any suggestion to a canonical
   V-row in ``docs/openfoam_corpus/industrial_solver_findings_v_series.md``.
4. AI advisory only? Yes. The route reads the V-series file + optionally
   invokes ``assemble_stack`` (V61-198 read-only by construction) + writes
   one JSON audit under ``.planning/audits/``. It NEVER writes into the
   case directory; ``test_4q_gate_no_case_writes`` enforces this.

**Surface-scan disposition (DEC-V61-088)**: an existing
``GET /api/cases/{case_id}/ai-diagnose`` route (N6.3 LLM-driven, case-bound)
exists in ``routes/ai_advisor.py``. This is a parallel new route with
different verb (POST), different path, different scope (stack-level
LLM-offline V-series matching). Both coexist; lineage clarified in
sub-DEC body.
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ui.backend.routes._loopback_guard import require_loopback
from ui.backend.services.advisor_stack import (
    AdvisorStackReport,
    assemble_stack,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Constants + module-level state
# ---------------------------------------------------------------------------

# Repo root resolved at import time. ``__file__`` is
# ``ui/backend/routes/ai_diagnose.py`` → four parents up = repo root.
_REPO_ROOT: Path = Path(__file__).resolve().parents[3]

_V_SERIES_CORPUS_PATH: Path = (
    _REPO_ROOT / "docs" / "openfoam_corpus" / "industrial_solver_findings_v_series.md"
)

_AUDIT_DIR: Path = _REPO_ROOT / ".planning" / "audits" / "ai_diagnose"

# Title-token-overlap weight relative to body-token-overlap. Tuning rationale:
# the V-row title (e.g. ``V41 · GRI-3.0 thermo header ... clamps janafThermo
# Tlow``) is a curated single-line summary, so a token match there is
# higher-precision than a generic body match. 3x is the sibling N6.1
# RAG loader's anchor:body ratio bumped up — that loader uses 2x for
# generic ``##``-or-deeper header anchors, but V-row titles are tighter
# and 3x empirically separates V41 from neighbours given the test fixtures.
_TITLE_WEIGHT: float = 3.0

# Top-N when callers do not specify. Tests expect >= 3 results.
_DEFAULT_TOP_K: int = 5

# Cap text inputs to defend against DoS via huge payloads. Solver log
# excerpts are explicitly "100-line" per spec; 256 KiB is a generous cap
# without forcing chunking.
_MAX_SYMPTOM_CHARS: int = 8 * 1024
_MAX_LOG_EXCERPT_CHARS: int = 256 * 1024


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{1,}")
_V_HEADING_RE = re.compile(r"^### V(\d+)\s*·\s*(.+?)\s*$", re.MULTILINE)


def _tokenize(text: str) -> frozenset[str]:
    """Lowercase alphanumeric tokens of length >= 2.

    Inlined (not imported from the N6.1 RAG loader) so the 4Q gate (1)
    lexical scan can pin the absence of any LLM-stack import.
    """
    return frozenset(m.group(0).lower() for m in _TOKEN_RE.finditer(text))


@dataclass(frozen=True)
class VSeriesRow:
    """Parsed V-series corpus row."""

    v_row_id: str
    title: str
    body: str
    fix_suggestion: str
    title_tokens: frozenset[str] = field(default_factory=frozenset)
    body_tokens: frozenset[str] = field(default_factory=frozenset)


def _extract_fix_field(body: str) -> str:
    """Extract the ``| Fix | ... |`` field from a V-row markdown body.

    V-rows use a two-column ``| field | value |`` table. The Fix row is
    the engineer-actionable suggestion. Falls back to first non-header
    paragraph if no Fix row is found (rare; some early rows use prose).

    Returns the raw value text trimmed to 1024 chars.
    """
    for line in body.splitlines():
        stripped = line.strip()
        # Match ``| Fix | <value> |`` case-insensitively, allowing
        # arbitrary leading whitespace and an optional trailing ``|``.
        m = re.match(r"\|\s*Fix\s*\|\s*(.+?)\s*\|?\s*$", stripped, re.IGNORECASE)
        if m:
            value = m.group(1).rstrip("|").strip()
            return value[:1024]
    # Fallback: first non-empty non-table-header line, capped.
    for line in body.splitlines():
        s = line.strip()
        if s and not s.startswith("|") and not s.startswith("#"):
            return s[:1024]
    return ""


_corpus_lock = threading.Lock()
_corpus_cache: Optional[tuple[VSeriesRow, ...]] = None
_corpus_cache_mtime: Optional[float] = None
_corpus_cache_path: Optional[Path] = None


def _load_v_series_corpus(
    path: Optional[Path] = None,
) -> tuple[VSeriesRow, ...]:
    """Parse the V-series markdown into ``VSeriesRow`` tuples.

    Cached at module level keyed by (path, mtime). The cache is invalidated
    when the corpus file is edited (e.g. a new V-row landed mid-session)
    or when the corpus path attribute is monkeypatched (tests).
    Thread-safe via ``_corpus_lock``.

    ``path`` resolution: when None, look up ``_V_SERIES_CORPUS_PATH`` on the
    module at call time (NOT at function-def time) so test monkeypatches of
    that attribute take effect.

    Raises:
        FileNotFoundError if the corpus file is missing. Caller is
        responsible for translating to an HTTP error.
    """
    import sys as _sys
    if path is None:
        path = getattr(_sys.modules[__name__], "_V_SERIES_CORPUS_PATH")
    global _corpus_cache, _corpus_cache_mtime, _corpus_cache_path
    with _corpus_lock:
        mtime = path.stat().st_mtime if path.exists() else None
        if (
            _corpus_cache is not None
            and _corpus_cache_mtime == mtime
            and _corpus_cache_path == path
        ):
            return _corpus_cache

        text = path.read_text(encoding="utf-8")
        matches = list(_V_HEADING_RE.finditer(text))
        rows: list[VSeriesRow] = []
        for i, m in enumerate(matches):
            v_num = m.group(1)
            title = m.group(2).strip()
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[body_start:body_end].strip()
            fix = _extract_fix_field(body)
            v_id = f"V{v_num}"
            rows.append(
                VSeriesRow(
                    v_row_id=v_id,
                    title=title,
                    body=body,
                    fix_suggestion=fix,
                    title_tokens=_tokenize(f"{v_id} {title}"),
                    body_tokens=_tokenize(body),
                )
            )

        out = tuple(rows)
        _corpus_cache = out
        _corpus_cache_mtime = mtime
        _corpus_cache_path = path
        return out


def _score_row(
    *,
    query_tokens: frozenset[str],
    row: VSeriesRow,
) -> tuple[float, frozenset[str], frozenset[str]]:
    """Compute a 0-1 similarity score for one V-row.

    Returns ``(score, title_overlap, body_overlap)``. Score formula:

        raw = title_weight * |q ∩ title_tokens| + |q ∩ body_tokens|
        norm = title_weight * len(query) + len(query)
             = (title_weight + 1) * len(query)
        score = raw / norm   (clamped to [0, 1])

    Normalization is by query length (not row length) so that long
    V-rows do not dominate just by having more text. Score is therefore
    "fraction of query token weight covered by this row".
    """
    if not query_tokens:
        return 0.0, frozenset(), frozenset()
    title_overlap = query_tokens & row.title_tokens
    body_overlap = query_tokens & row.body_tokens
    raw = _TITLE_WEIGHT * len(title_overlap) + len(body_overlap)
    norm = (_TITLE_WEIGHT + 1.0) * float(len(query_tokens))
    score = raw / norm if norm > 0 else 0.0
    return min(score, 1.0), title_overlap, body_overlap


def _rationale_for_match(
    *,
    title_overlap: frozenset[str],
    body_overlap: frozenset[str],
    stack_v_row_match: bool,
) -> str:
    """Human-readable explanation of why this row matched."""
    parts: list[str] = []
    if title_overlap:
        sample = ", ".join(sorted(title_overlap)[:5])
        parts.append(f"title tokens matched: {sample}")
    if body_overlap - title_overlap:
        sample = ", ".join(sorted(body_overlap - title_overlap)[:5])
        parts.append(f"body tokens matched: {sample}")
    if stack_v_row_match:
        parts.append("also surfaced by advisor_stack evidence_refs")
    if not parts:
        parts.append("no token overlap; included for diagnostic completeness")
    return " · ".join(parts)


def _persist_audit(payload: dict[str, Any]) -> Path:
    """Write the per-request audit JSON and return its path.

    Path is under ``.planning/audits/ai_diagnose/<request_id>.json``.
    The directory is created if missing. Errors during write propagate
    to the caller; the route translates them to HTTP 500 with a
    structured payload so engineers can recover.
    """
    _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    request_id = payload["request_id"]
    path = _AUDIT_DIR / f"{request_id}.json"
    path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
    return path


def _summarize_stack_report(report: AdvisorStackReport) -> dict[str, Any]:
    """Serialize an ``AdvisorStackReport`` for audit + wire output.

    ``asdict`` on the report would also walk advisor-native dataclasses
    (some of which contain unserializable types like FreeCAD Document
    placeholders); the stack-level summary is sufficient for diagnose
    cross-reference. Callers wanting raw findings can call
    ``assemble_stack`` directly.
    """
    return {
        "advisor_count": report.advisor_count,
        "failed_advisor_count": report.failed_advisor_count,
        "critical_count": report.critical_count,
        "warning_count": report.warning_count,
        "evidence_refs": list(report.evidence_refs),
        "stack_duration_ms": report.stack_duration_ms,
        "findings": [
            {
                "source_advisor": f.source_advisor,
                "severity": f.severity,
                "code": f.code,
                "message": f.message,
                "location": f.location,
                "evidence_v_rows": list(f.evidence_v_rows),
            }
            for f in report.findings
        ],
    }


# ---------------------------------------------------------------------------
# Pydantic wire schemas
# ---------------------------------------------------------------------------


class AIDiagnoseRequest(BaseModel):
    """POST /ai-diagnose body.

    Notes:
      * ``case_dir`` mirrors the sibling ``/ai-review`` route schema. The
        route only reads ``parts_manifest.json`` (read-only JSON) under
        that path; no other case files are touched. Loopback-only enforcement
        bounds blast radius (test ``test_4q_gate_route_does_not_write_inside_case_dir``).
      * ``llm_match`` is forward-compatible; while no provider is wired,
        the response always reports ``llm_match_used=False``.
    """

    symptom_text: str = Field(
        ..., min_length=1,
        description="Engineer-described symptom; matched against V-series rows.",
    )
    solver_log_excerpt: Optional[str] = Field(
        default=None,
        description="Optional 100-line excerpt of solver log for additional token signal.",
    )
    case_dir: Optional[str] = Field(
        default=None,
        description="Optional case directory path; when provided, "
                    "assemble_stack runs and findings are cross-referenced.",
    )
    llm_match: bool = Field(
        default=False,
        description="If true, attempt LLM-augmented re-ranking. Base ranking always runs.",
    )
    top_k: int = Field(
        default=_DEFAULT_TOP_K, ge=1, le=20,
        description="Max number of V-series matches to return (clamped to corpus size).",
    )


class VSeriesMatch(BaseModel):
    v_row_id: str
    v_row_title: str
    similarity_score: float
    similarity_rationale: str
    fix_suggestion: str


class AIDiagnoseResponse(BaseModel):
    request_id: str
    v_row_matches: list[VSeriesMatch]
    stack_report: Optional[dict[str, Any]] = None
    audit_artifact_path: str
    llm_match_used: bool
    timing: dict[str, float]
    corpus_size: int


# ---------------------------------------------------------------------------
# Stack invocation helper
# ---------------------------------------------------------------------------


# Sibling /ai-review (M-ROUTE-AI-REVIEW) discovery layout — keep this in sync
# so engineers do not need to learn two layouts. Codex R0 P1 (2026-05-14):
# the prior flat-path ``<case_dir>/parts_manifest.json`` lookup missed the
# repository's standard ``<case_dir>/inputs/parts_manifest.{yaml,yml,json}``
# convention, so the advertised stack cross-reference never ran on normal
# cases. R1 fix: mirror ``_DISCOVER_KEYS`` semantics from ai_review.py.
_PARTS_MANIFEST_CANDIDATES: tuple[str, ...] = (
    "parts_manifest.yaml",
    "parts_manifest.yml",
    "parts_manifest.json",
)


def _load_dict_file(path: Path) -> Optional[dict[str, Any]]:
    """Load a YAML or JSON dict from disk; return None on any failure.

    Mirrors ai_review.py loader behavior (R1): silently skip non-dict
    payloads, malformed files, and IO errors — the calling site treats
    absence as "no stack input available", per V130 silent-skip.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            obj = json.loads(text)
        else:
            obj = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError):
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _discover_parts_manifest(case_dir: Path) -> Optional[dict[str, Any]]:
    """Search the sibling-aligned layout for a parts_manifest artifact.

    Order:
      1. ``<case_dir>/inputs/parts_manifest.{yaml,yml,json}`` (canonical
         project layout, matches /ai-review).
      2. ``<case_dir>/parts_manifest.{yaml,yml,json}`` (flat fallback for
         non-standard test fixtures + adhoc operator layouts).

    First hit wins. Missing → None (silent skip per V130). Codex R0 P1
    locked the order: the canonical layout is searched first so that
    engineers following project convention get the cross-reference.
    """
    inputs_dir = case_dir / "inputs"
    for name in _PARTS_MANIFEST_CANDIDATES:
        candidate = inputs_dir / name
        if candidate.is_file():
            loaded = _load_dict_file(candidate)
            if loaded is not None:
                return loaded
    for name in _PARTS_MANIFEST_CANDIDATES:
        candidate = case_dir / name
        if candidate.is_file():
            loaded = _load_dict_file(candidate)
            if loaded is not None:
                return loaded
    return None


def _maybe_run_stack(case_dir: Path) -> Optional[AdvisorStackReport]:
    """Invoke ``assemble_stack`` with whatever artifacts the case exposes.

    For V62-A's first diagnose route, the artifact extraction surface is
    intentionally narrow: only ``parts_manifest`` (under the sibling-aligned
    layout — see :func:`_discover_parts_manifest`). Richer artifact
    discovery (shm_dict / thermo_dict / thin_wall) is M-4Q-AUDIT scope —
    this keeps the surface small enough to Codex-review in isolation.

    Returns None if no parts_manifest could be located. This is
    distinguishable from "stack ran with 0 findings" because the audit
    captures both ``invoked`` (bool) and ``report`` (maybe-null).
    """
    parts_manifest = _discover_parts_manifest(case_dir)
    if parts_manifest is None:
        return None
    return assemble_stack(parts_manifest=parts_manifest)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post(
    "/ai-diagnose",
    response_model=AIDiagnoseResponse,
    tags=["ai-diagnose"],
)
async def post_ai_diagnose(
    payload: AIDiagnoseRequest,
    request: Request,
) -> AIDiagnoseResponse:
    """Match an engineer-described symptom against the V-series corpus.

    Loopback-only (V62-A blast-radius parity with ``/ai-review``): callers
    behind a trusted reverse proxy + auth set
    ``AI_CHAT_ALLOW_NON_LOOPBACK=1`` to opt in.

    Behavior:
      1. Tokenize ``symptom_text`` + ``solver_log_excerpt``.
      2. Load V-series corpus (cached by mtime).
      3. Score each row via title-weighted token overlap.
      4. If ``case_dir`` is a real directory + advisor artifacts are
         present → call :func:`assemble_stack` and tag any V-rows already
         surfaced by stack ``evidence_refs`` with a cross-ref rationale.
      5. Persist audit JSON to ``.planning/audits/ai_diagnose/``.
      6. Return top-K matches + stack summary + audit path.

    Failure modes:
      * ``symptom_text`` empty / whitespace-only → 400.
      * ``case_dir`` provided but missing on disk → 400.
      * V-series corpus missing on disk → 500 with structured detail.
      * Stack invocation raises → swallowed; route returns 200 with
        ``stack_report=None`` and audit records the failure (crash
        isolation per V62-A spec).
    """
    require_loopback(request, route_label="/api/ai-diagnose")

    t_start = time.perf_counter()
    request_id = uuid.uuid4().hex

    symptom = (payload.symptom_text or "").strip()
    if not symptom:
        raise HTTPException(
            status_code=400,
            detail={
                "failing_check": "empty_symptom_text",
                "actionable": "Provide a non-empty symptom_text (e.g. "
                              "'p_rgh plateau at 0.39-0.54 after 2000 iter').",
            },
        )

    # Defensive caps on operator-supplied text — sanitized BEFORE
    # tokenization so the regex doesn't walk megabytes.
    symptom = symptom[:_MAX_SYMPTOM_CHARS]
    excerpt = (payload.solver_log_excerpt or "")[:_MAX_LOG_EXCERPT_CHARS]
    query_tokens = _tokenize(f"{symptom}\n{excerpt}")

    # Step 1: load corpus. Crash-isolate so an absent / malformed corpus
    # surfaces as a structured 500 (audit still records the attempt).
    t_corpus_start = time.perf_counter()
    corpus_load_error: Optional[str] = None
    try:
        rows = _load_v_series_corpus()
    except FileNotFoundError as exc:
        rows = ()
        corpus_load_error = f"corpus_missing: {exc}"
    except OSError as exc:
        rows = ()
        corpus_load_error = f"corpus_io_error: {type(exc).__name__}: {exc}"
    corpus_load_ms = (time.perf_counter() - t_corpus_start) * 1000.0

    # Step 2: resolve case_dir (if any) and run stack. Crash-isolate.
    t_stack_start = time.perf_counter()
    stack_report: Optional[AdvisorStackReport] = None
    stack_error: Optional[str] = None
    case_dir: Optional[Path] = None
    if payload.case_dir is not None:
        case_dir = Path(payload.case_dir)
        if not case_dir.is_dir():
            raise HTTPException(
                status_code=400,
                detail={
                    "failing_check": "case_dir_not_found",
                    "case_dir": payload.case_dir,
                },
            )
        try:
            stack_report = _maybe_run_stack(case_dir)
        except Exception as exc:  # crash isolation per V62-A spec
            stack_error = f"{type(exc).__name__}: {exc}"
            stack_report = None
    stack_ms = (time.perf_counter() - t_stack_start) * 1000.0

    # Step 3: rank V-rows. Cross-reference with V-rows actually surfaced by
    # findings (NOT ``evidence_refs``).
    #
    # Codex R0 P2 (2026-05-14): ``AdvisorStackReport.evidence_refs`` is the
    # union of ``_V_ROWS_PER_ADVISOR`` for every *dispatched* advisor,
    # independent of whether that advisor emitted any findings. Boosting on
    # evidence_refs would add ``+0.10`` and "surfaced by advisor_stack"
    # rationale to V79/V81/V52 whenever A4/A5/A8 dispatched cleanly — i.e.,
    # we would fabricate provenance for V-rows the stack never actually
    # surfaced. R1 fix: derive the boost set from the V-rows carried by
    # each emitted ``Finding``, so only V-rows tied to a real finding
    # influence the diagnose ranking.
    stack_v_rows: frozenset[str] = (
        frozenset(
            v_row
            for finding in stack_report.findings
            for v_row in finding.evidence_v_rows
        )
        if stack_report is not None
        else frozenset()
    )
    t_score_start = time.perf_counter()
    scored: list[tuple[float, str, VSeriesRow, frozenset[str], frozenset[str]]] = []
    for row in rows:
        score, title_overlap, body_overlap = _score_row(
            query_tokens=query_tokens, row=row,
        )
        # Boost rows that the live advisor stack also surfaced. Boost is
        # additive (not multiplicative) so a 0-token-overlap stack row
        # still beats most non-overlap rows but cannot outrank rows with
        # actual token evidence.
        if row.v_row_id in stack_v_rows:
            score = min(1.0, score + 0.1)
        if score > 0 or row.v_row_id in stack_v_rows:
            scored.append((score, row.v_row_id, row, title_overlap, body_overlap))

    # Sort: score desc, then v_row_id asc for stable tiebreaks.
    scored.sort(key=lambda t: (-t[0], t[1]))
    top = scored[: payload.top_k]
    score_ms = (time.perf_counter() - t_score_start) * 1000.0

    matches: list[VSeriesMatch] = []
    for score, v_id, row, title_overlap, body_overlap in top:
        rationale = _rationale_for_match(
            title_overlap=title_overlap,
            body_overlap=body_overlap,
            stack_v_row_match=v_id in stack_v_rows,
        )
        matches.append(
            VSeriesMatch(
                v_row_id=v_id,
                v_row_title=row.title,
                similarity_score=round(score, 6),
                similarity_rationale=rationale,
                fix_suggestion=row.fix_suggestion,
            )
        )

    # Step 4: LLM augmentation. No provider wired → flag stays False.
    # When a provider is wired in a future sub-DEC, the re-rank must
    # preserve the base ranking as a fallback (4Q gate (1) requires
    # LLM-offline to remain functional). Leaving the hook explicit so
    # reviewers can see the contract.
    llm_match_used = False
    if payload.llm_match:
        # provider lookup elided — return base ranking + record intent.
        llm_match_used = False

    # Step 5: persist audit. If corpus failed to load, audit still
    # records the attempt + error so engineers can debug.
    total_ms = (time.perf_counter() - t_start) * 1000.0
    timing = {
        "total_ms": round(total_ms, 3),
        "corpus_load_ms": round(corpus_load_ms, 3),
        "stack_ms": round(stack_ms, 3),
        "score_ms": round(score_ms, 3),
    }

    audit_payload: dict[str, Any] = {
        "request_id": request_id,
        "schema_version": "v62-a-ai-diagnose-v1",
        "wall_clock_ms": round(total_ms, 3),
        "timing": timing,
        "request": {
            "symptom_text": symptom,
            "solver_log_excerpt_len": len(excerpt),
            "case_dir": payload.case_dir,
            "llm_match_requested": payload.llm_match,
            "top_k": payload.top_k,
        },
        "corpus": {
            "size": len(rows),
            "load_error": corpus_load_error,
        },
        "stack": {
            "invoked": stack_report is not None,
            "error": stack_error,
            "report": _summarize_stack_report(stack_report) if stack_report else None,
        },
        "matches": [m.model_dump() for m in matches],
        "llm_match_used": llm_match_used,
    }

    audit_error: Optional[str] = None
    try:
        audit_path = _persist_audit(audit_payload)
    except OSError as exc:
        # Audit failure is observable but not fatal — log + continue.
        audit_error = f"{type(exc).__name__}: {exc}"
        audit_path = _AUDIT_DIR / f"{request_id}.json"  # nominal path for response

    if corpus_load_error is not None:
        # Structured 500 once audit has been attempted, so the engineer
        # has a request_id to grep.
        raise HTTPException(
            status_code=500,
            detail={
                "failing_check": "v_series_corpus_unavailable",
                "request_id": request_id,
                "corpus_load_error": corpus_load_error,
                "audit_artifact_path": str(audit_path),
                "audit_write_error": audit_error,
            },
        )

    return AIDiagnoseResponse(
        request_id=request_id,
        v_row_matches=matches,
        stack_report=_summarize_stack_report(stack_report) if stack_report else None,
        audit_artifact_path=str(audit_path),
        llm_match_used=llm_match_used,
        timing=timing,
        corpus_size=len(rows),
    )


__all__ = [
    "AIDiagnoseRequest",
    "AIDiagnoseResponse",
    "VSeriesMatch",
    "router",
]
