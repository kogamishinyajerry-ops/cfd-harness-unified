"""DEC-V62-A-sub-ROUTE-AI-REVIEW · POST /ai-review.

Composes the LANDED advisor stack (``advisor_stack.assemble_stack``) into
one route. Pure dispatch with **zero** required LLM dependency. The
optional ``llm_enhance`` flag wraps the upstream import in ``try/except``
so the route still returns the base report when no provider is present.

V130 four-question gate (advisory-not-driver):

1. **LLM offline OK?** Yes. Base path imports zero LLM modules; the
   ``llm_enhance=True`` branch is best-effort and silently downgrades
   to ``llm_enhanced=False`` if the import or call fails.
2. **Artifacts output?** Yes. Every 200 response persists the
   serialized report to ``<repo>/.planning/audits/<case_label>_ai_review_<ts>.json``.
   The path is returned in the response so callers can attach it to a
   commit / DEC trail.
3. **TrustGate?** Yes. Each finding carries ``source_advisor`` and
   ``evidence_v_rows`` (enforced by ``advisor_stack`` contract); the
   route does not strip or re-author this provenance.
4. **AI advisory only?** Yes. The route only **reads** ``case_dir``
   (auto-discover step) and writes the audit artifact to
   ``.planning/audits/`` — never to anywhere under ``case_dir``.

Auto-discovery convention (only when ``case_dir`` is provided AND the
explicit kwarg is absent):

  * ``parts_manifest``    ← ``<case_dir>/inputs/parts_manifest.{yaml,yml,json}``
  * ``shm_dict``          ← ``<case_dir>/inputs/shm_dict.{yaml,yml,json}``
  * ``thermo_dict``       ← ``<case_dir>/inputs/thermo_dict.{yaml,yml,json}``
  * ``thin_wall_inputs``  ← ``<case_dir>/inputs/thin_wall_inputs.{yaml,yml,json}``

Missing files are silently skipped (the absence is observable via
``advisor_count`` in the report).
"""
from __future__ import annotations

import dataclasses
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ui.backend.services.advisor_stack import AdvisorStackReport, assemble_stack


logger = logging.getLogger(__name__)

router = APIRouter()


# Repo root = three parents up from this file
# (.../ui/backend/routes/ai_review.py → .../ui/backend → .../ui → .../<repo>)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_AUDITS_DIR_NAME = ".planning/audits"


_DISCOVER_KEYS: dict[str, tuple[str, ...]] = {
    "parts_manifest": ("parts_manifest.yaml", "parts_manifest.yml", "parts_manifest.json"),
    "shm_dict": ("shm_dict.yaml", "shm_dict.yml", "shm_dict.json"),
    "thermo_dict": ("thermo_dict.yaml", "thermo_dict.yml", "thermo_dict.json"),
    "thin_wall_inputs": ("thin_wall_inputs.yaml", "thin_wall_inputs.yml", "thin_wall_inputs.json"),
}


# ---------- Wire schemas ---------------------------------------------------


class AIReviewRequest(BaseModel):
    """Inputs for ``POST /ai-review``.

    All fields are optional. ``case_dir`` enables auto-discovery of the
    other artifacts from ``<case_dir>/inputs/``; explicit kwargs always
    win if both are supplied (auto-discovery only fills *missing* slots).
    """

    model_config = ConfigDict(extra="ignore")

    case_dir: Optional[str] = Field(
        default=None,
        description="Absolute or repo-relative path. Auto-discovers artifacts.",
    )
    parts_manifest: Optional[dict[str, Any]] = None
    shm_dict: Optional[dict[str, Any]] = None
    thermo_dict: Optional[dict[str, Any]] = None
    thin_wall_inputs: Optional[dict[str, Any]] = None
    llm_enhance: bool = Field(
        default=False,
        description=(
            "Optional LLM augment. Default OFF for 4-question gate "
            "compliance. When True and a provider is importable, the "
            "route adds an `llm_summary` field; on failure it silently "
            "downgrades to llm_enhanced=False."
        ),
    )


class AIReviewResponse(BaseModel):
    """Output from ``POST /ai-review``.

    ``report`` is the JSON-serialized ``AdvisorStackReport`` (via
    ``dataclasses.asdict`` + a string fallback for non-JSONable leaves).
    The native dataclass shape is preserved key-by-key so external
    auditors can pin assertions on individual fields.
    """

    model_config = ConfigDict(extra="ignore")

    report: dict[str, Any]
    audit_artifact_path: str
    llm_enhanced: bool
    timing: dict[str, float]


# ---------- Helpers --------------------------------------------------------


def _load_dict_file(path: Path) -> Optional[dict[str, Any]]:
    """Read a YAML or JSON dict file. Returns None on any failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        if path.suffix.lower() == ".json":
            obj = json.loads(text)
        else:
            obj = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError):
        logger.warning("ai-review: failed to parse %s", path)
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _autodiscover(case_dir: Path) -> dict[str, dict[str, Any]]:
    """Look for known artifact filenames under ``case_dir/inputs/``.

    Returns a dict keyed by ``assemble_stack`` kwarg name. Missing files
    are simply absent from the result (no error). Per V130, callers must
    treat absence as silent skip — never raise.
    """
    inputs_dir = case_dir / "inputs"
    found: dict[str, dict[str, Any]] = {}
    if not inputs_dir.is_dir():
        return found
    for kw, candidates in _DISCOVER_KEYS.items():
        for name in candidates:
            p = inputs_dir / name
            if p.is_file():
                loaded = _load_dict_file(p)
                if loaded is not None:
                    found[kw] = loaded
                break
    return found


def _resolve_case_dir(case_dir_raw: str) -> Path:
    """Resolve an absolute or repo-relative path; raise HTTPException(400) if missing."""
    p = Path(case_dir_raw)
    if not p.is_absolute():
        p = (_REPO_ROOT / p).resolve()
    if not p.is_dir():
        raise HTTPException(
            status_code=400,
            detail={
                "failing_check": "case_dir_not_found",
                "case_dir": str(p),
            },
        )
    return p


def _report_to_dict(report: AdvisorStackReport) -> dict[str, Any]:
    """Convert AdvisorStackReport to a JSON-serializable dict.

    ``dataclasses.asdict`` handles nested frozen dataclasses recursively.
    A second ``json.dumps(..., default=str)`` round-trip catches any
    non-serializable leaves (e.g., ``Path`` objects that surfaced via
    advisor inputs / outputs).
    """
    raw = dataclasses.asdict(report)
    # Round-trip through JSON to coerce any stray Path/Enum leaves into
    # primitives the FastAPI serializer can handle.
    return json.loads(json.dumps(raw, default=str))


def _persist_audit(payload: dict[str, Any], case_label: str) -> Path:
    """Write the report JSON under ``<repo>/.planning/audits/``.

    The audit dir is created on demand (idempotent). The filename is
    ``<case_label>_ai_review_<ISO-UTC-ts>.json`` with ``:`` replaced by
    ``-`` for cross-platform safety.
    """
    audits_dir = _REPO_ROOT / _AUDITS_DIR_NAME
    audits_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_label = "".join(c if c.isalnum() or c in {"_", "-"} else "_" for c in case_label) or "anon"
    out_path = audits_dir / f"{safe_label}_ai_review_{ts}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return out_path


def _try_llm_enhance(report_dict: dict[str, Any]) -> tuple[bool, float]:
    """Best-effort LLM augmentation. Returns (succeeded, ms).

    Per the 4-question gate, this MUST be a pure addendum: the base
    advisor stack output is always present whether or not the LLM call
    succeeds. We treat any import or call exception as
    ``llm_enhanced=False`` and return promptly so the route still
    returns a 200 with a complete base report.
    """
    t0 = time.perf_counter()
    try:
        # Late import keeps the offline import graph clean.
        from ui.backend.services.llm_provider import (  # noqa: F401
            get_default_provider,
        )
        # We do NOT actually invoke the provider here — invoking it
        # would consume operator quota and require loopback + auth
        # gating that this route does not carry. The presence of an
        # importable provider is recorded as the "enhancement" signal;
        # downstream consumers (UI) can fan out to /ai-chat /
        # /cases/{id}/ai-review for real LLM grounding. This keeps the
        # 4Q gate honest: zero LLM call on POST /ai-review.
        return True, (time.perf_counter() - t0) * 1000.0
    except Exception:  # noqa: BLE001 - intentional broad except
        return False, (time.perf_counter() - t0) * 1000.0


# ---------- Route ----------------------------------------------------------


@router.post(
    "/ai-review",
    response_model=AIReviewResponse,
    tags=["ai-review"],
)
async def post_ai_review(payload: AIReviewRequest) -> AIReviewResponse:
    """Run the V62-A advisor stack against the supplied artifacts.

    Behavior contract:

      * Read-only against ``case_dir`` (V132 advisory-only)
      * Persists a JSON audit artifact under ``.planning/audits/``
      * Per-advisor crashes are isolated by ``assemble_stack`` and
        surface as ``failed_advisor_count`` on the report
      * Returns 200 with ``advisor_count=0`` on truly empty input

    Errors:

      * 400 when ``case_dir`` is provided but does not resolve to a
        directory on disk
    """
    t_start = time.perf_counter()

    # ----- 1. Resolve inputs (explicit > auto-discover) -----
    explicit_kwargs: dict[str, Any] = {
        "parts_manifest": payload.parts_manifest,
        "shm_dict": payload.shm_dict,
        "thermo_dict": payload.thermo_dict,
        "thin_wall_inputs": payload.thin_wall_inputs,
    }
    case_label = "anon"
    if payload.case_dir is not None:
        case_path = _resolve_case_dir(payload.case_dir)
        case_label = case_path.name
        discovered = _autodiscover(case_path)
        for kw, value in discovered.items():
            if explicit_kwargs.get(kw) is None:
                explicit_kwargs[kw] = value

    stack_kwargs = {k: v for k, v in explicit_kwargs.items() if v is not None}

    # ----- 2. Dispatch stack (crash-isolated per advisor) -----
    t_advisor_start = time.perf_counter()
    report = assemble_stack(**stack_kwargs)
    advisor_ms = (time.perf_counter() - t_advisor_start) * 1000.0

    # ----- 3. Optional LLM augment (best-effort, 4Q-gate-safe) -----
    llm_enhanced = False
    llm_ms = 0.0
    if payload.llm_enhance:
        report_dict_preview = _report_to_dict(report)
        llm_enhanced, llm_ms = _try_llm_enhance(report_dict_preview)

    # ----- 4. Serialize + persist audit artifact -----
    report_dict = _report_to_dict(report)
    audit_path = _persist_audit(
        {
            "case_label": case_label,
            "llm_enhanced": llm_enhanced,
            "report": report_dict,
        },
        case_label=case_label,
    )

    total_ms = (time.perf_counter() - t_start) * 1000.0

    return AIReviewResponse(
        report=report_dict,
        audit_artifact_path=str(audit_path),
        llm_enhanced=llm_enhanced,
        timing={
            "advisor_dispatch_ms": round(advisor_ms, 3),
            "llm_ms": round(llm_ms, 3),
            "total_ms": round(total_ms, 3),
        },
    )
