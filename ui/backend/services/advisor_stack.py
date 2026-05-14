"""V62-A advisor stack assembly layer (M-STACK-ASSEMBLY · sub-DEC of V62 charter).

Converts the 8 LANDED `geometry_ingest` advisors (V61-198 substrate arc) from
loose modules into one composable dispatch layer that downstream
``/ai-review`` and ``/ai-diagnose`` routes can call once and receive a unified
``AdvisorStackReport``.

V130 thesis (advisor-not-driver) compliance — four-question gate:

1. **LLM offline OK?** Yes. This module imports only from
   ``geometry_ingest``; no ``anthropic`` / ``openai`` / ``corpus_loader``
   dependency. Test ``test_stack_zero_llm_imports`` enforces this
   structurally.
2. **Artifacts output?** Yes. ``AdvisorStackReport`` is a frozen dataclass
   built from frozen tuples; callers can pickle / JSON-encode it directly
   for persistence under ``.planning/audits/``.
3. **TrustGate?** Yes. Every ``Finding`` carries ``source_advisor``
   (module name) and ``evidence_v_rows`` (canonical V-row IDs from
   ``industrial_solver_findings_v_series.md``).
4. **AI advisory only?** Yes. The stack imports advisor functions but
   never calls anything that mutates a case directory; the underlying
   advisors are themselves read-only by V132 architecture lock.

Routing rules (pure dict-consumer dispatch, 0 LLM):

============================  =========================================
Provided artifact             Advisors dispatched
============================  =========================================
``parts_manifest``            A4 ``check_face_orientation`` +
                              A5 ``validate_inlet_outlet_emission`` +
                              D10 ``detect_invalid_bc_types`` (when
                              ``parts[i].bc`` blocks are present)
``bc_specs`` (explicit)       D10 ``detect_invalid_bc_types`` (wins over
                              parts_manifest auto-extraction)
``interface_bodies`` +        A2-v2 ``detect_virtual_interfaces`` +
``interface_specs``           ``should_have_been_shared_with_unintended_gap``
``shm_dict``                  A8 ``validate_shm_dict``
                              (with V99 widening if ``stl_face_normals``)
``thermo_dict``               A10 ``check_thermo_polynomial_range``
``step_path``                 unit_detector ``detect_unit``
``thin_wall_inputs``          thin_wall ``detect_thin_wall_patches_at_risk``
``stl_bbox_set`` (≥1 entry)   D6 ``check_extra_bodies_in_fluid`` (V55 ·
                              case_016 debris cube class · combines with
                              parts_manifest when provided)
============================  =========================================

ALL applicable advisors run on every call (no opt-out per artifact).
Each advisor invocation is wrapped in try/except — if one advisor
raises, the failure is recorded as an ``AdvisorCall`` with
``status='error'`` and the stack continues. Callers can detect crashes
via ``AdvisorStackReport.failed_advisor_count``.

**Out-of-scope advisors** (intentionally NOT in the stack):

- ``cad_ingest_freecad`` (A1) — operational STEP loader, requires FreeCAD
  install, returns a Document not a Finding-shaped report.
- ``geometry_surgery`` (A3) — operational mesh decimator, mutates
  meshes; not advisory.
- ``step_canonicalizer`` (A7) — operational file rewriter, mutates STEP
  bytes; not advisory.

These three are utilities consumed by upstream ingestion code; promoting
them to "advisors" would conflate operational and advisory layers and
violate V130. A future ``operation_stack`` module could compose them if
needed; that is out of scope for V62-A.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
import time
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


_PARENT_PKG = "ui.backend.services.geometry_ingest"


def _ensure_parent_package_loaded() -> types.ModuleType:
    """Ensure ``ui.backend.services.geometry_ingest`` is in ``sys.modules``.

    Resolution order:

    1. **Already cached** (workbench-env test runner, or a prior
       caller already executed the real ``__init__.py``) → return the
       cached entry untouched. No surprises for downstream code that
       relies on the package's normal re-exports
       (``IngestReport`` / ``canonical_stl_bytes`` / etc.).
    2. **Real init succeeds** (workbench env: ``trimesh`` installed) →
       return the real package. Downstream ``from
       ui.backend.services.geometry_ingest import IngestReport`` keeps
       working exactly as before — no shadowing.
    3. **Real init fails** (``[ui]``-only env: no ``trimesh``) → install
       a stdlib ``ModuleType`` placeholder with ``__path__`` set to the
       package directory so the advisor leaves can still load. The
       placeholder does NOT carry the workbench-only re-exports
       (``IngestReport``, ``canonical_stl_bytes``, …); any downstream
       code touching those symbols in a ``[ui]``-only deployment is
       already broken by missing ``trimesh`` regardless of this module.

    Codex evolution log:
      - R0 P1 (2026-05-14): naive ``from ui.backend.services.geometry_ingest
        import ...`` ran ``__init__.py`` → trimesh crash in ``[ui]`` env.
      - R1 P2 (2026-05-14): leaf-only ``spec_from_file_location`` left
        the parent package missing from ``sys.modules`` so subsequent
        normal imports still re-triggered the real init.
      - R2 P1 (2026-05-14): unconditional placeholder shadowed the real
        package in workbench env, breaking ``IngestReport`` imports when
        ``advisor_stack`` was loaded first.
      - R3 (2026-05-14): try-real-first + fallback-placeholder
        (this code) — both envs get what they need.
    """
    existing = sys.modules.get(_PARENT_PKG)
    if existing is not None:
        return existing
    try:
        importlib.import_module(_PARENT_PKG)
    except ImportError:
        # Real init failed — typically ``[ui]``-only env without trimesh.
        # Drop any partial cache entry the failed import may have left
        # behind so the placeholder is the canonical record.
        sys.modules.pop(_PARENT_PKG, None)
        pkg_dir = Path(__file__).parent / "geometry_ingest"
        placeholder = types.ModuleType(_PARENT_PKG)
        placeholder.__path__ = [str(pkg_dir)]
        placeholder.__file__ = str(pkg_dir / "__init__.py")
        sys.modules[_PARENT_PKG] = placeholder
        return placeholder
    return sys.modules[_PARENT_PKG]


def _load_advisor(modname: str) -> Any:
    """Load an advisor submodule directly from disk.

    Registers under ``ui.backend.services.geometry_ingest.<modname>`` in
    ``sys.modules`` AND attaches as an attribute on the parent placeholder
    so that:

    1. ``import ui.backend.services.geometry_ingest.<modname>`` finds the
       cached entry without re-running ``__init__.py``;
    2. ``from ui.backend.services.geometry_ingest import <modname>``
       resolves the attribute on the placeholder;
    3. test-time ``monkeypatch.setattr(<advisor_mod>, "fn", ...)`` patches
       the same module object the stack dispatches against.
    """
    parent = _ensure_parent_package_loaded()
    qualified = f"{_PARENT_PKG}.{modname}"
    if qualified in sys.modules:
        cached = sys.modules[qualified]
        if not hasattr(parent, modname):
            setattr(parent, modname, cached)
        return cached
    src = Path(__file__).parent / "geometry_ingest" / f"{modname}.py"
    spec = importlib.util.spec_from_file_location(qualified, src)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"could not load advisor submodule {qualified}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    setattr(parent, modname, module)
    return module


bc_type_name_validity_advisor = _load_advisor("bc_type_name_validity_advisor")
extra_body_advisor = _load_advisor("extra_body_advisor")
face_orientation_advisor = _load_advisor("face_orientation_advisor")
inlet_outlet_validator = _load_advisor("inlet_outlet_validator")
shm_dict_validator = _load_advisor("shm_dict_validator")
solver_block_advisor = _load_advisor("solver_block_advisor")
stl_face_label_validator = _load_advisor("stl_face_label_validator")
thermo_polynomial_range_advisor = _load_advisor("thermo_polynomial_range_advisor")
thin_wall_advisor = _load_advisor("thin_wall_advisor")
unit_detector = _load_advisor("unit_detector")
virtual_interface_detector = _load_advisor("virtual_interface_detector")


# V-row evidence per advisor (canonical IDs from
# `docs/openfoam_corpus/industrial_solver_findings_v_series.md`).
# Tuples are ordered by sediment-landing date for audit predictability.
_V_ROWS_PER_ADVISOR: dict[str, tuple[str, ...]] = {
    "bc_type_name_validity_advisor": ("V29",),
    "extra_body_advisor": ("V55",),
    "face_orientation_advisor": ("V79", "V87"),
    "inlet_outlet_validator": ("V81",),
    "shm_dict_validator": ("V52", "V86", "V99", "V100"),
    "solver_block_advisor": ("V27", "V28"),
    "stl_face_label_validator": ("V94",),
    "thermo_polynomial_range_advisor": ("V41", "V93"),
    "thin_wall_advisor": ("V10",),
    "unit_detector": ("V20", "V96"),
    "virtual_interface_detector": (
        "V22", "V25", "V33", "V36", "V42", "V43", "V50",
    ),
}


@dataclass(frozen=True)
class Finding:
    """Normalized finding shape across all advisors.

    Each advisor's native finding type (``FaceOrientationFinding``,
    ``BoundaryFinding``, ``ShmFinding``, ``ThermoFinding``,
    ``ThinWallWarning``, etc.) is translated into this shape by
    ``_normalize_*`` helpers. The advisor's native dataclass is kept on
    ``raw`` for callers that need full detail.
    """

    source_advisor: str           # advisor module name (audit + TrustGate)
    severity: str                 # "info" | "warning" | "critical" | "fail" | "pass"
    code: str                     # advisor-specific code
    message: str                  # engineer-readable summary
    location: str | None          # body / patch / dict-path / file path
    evidence_v_rows: tuple[str, ...]  # V-row IDs for TrustGate
    raw: Any                      # native advisor finding dataclass


@dataclass(frozen=True)
class AdvisorCall:
    """Audit-trail entry for one dispatched advisor invocation.

    Codex R0 P2 fix (2026-05-14): on the error path, ``output`` carries
    a JSON-serializable dict ``{"exception_type": str, "message": str}``
    instead of the raw ``Exception`` object. This keeps
    ``json.dumps(asdict(report))`` reliable on the partial-failure path
    that crash isolation is supposed to preserve. Callers needing the
    live exception should re-raise from the calling site or run the
    advisor directly (the stack does not retain exception tracebacks).
    """

    advisor_name: str         # e.g., "shm_dict_validator"
    status: str               # "ok" | "error"
    input_summary: str        # serialized input description, ≤200 chars
    output: Any               # native report dataclass, or {"exception_type", "message"} on error
    duration_ms: float        # wall-clock advisor runtime
    version: str              # source-module identifier (file path proxy)


# Codex R0 P2 fix (2026-05-14): treat A5's "fail" severity as blocking
# alongside "critical". A5 ``inlet_outlet_validator`` is the only LANDED
# advisor using the "fail" label (V81 protocol violations) and they are
# at least as actionable as A4/A8/A10 "critical" findings. Prior code
# silently classified every V81 fail as 0/0, under-reporting blocking
# findings to any route gate consuming these helpers.
_BLOCKING_SEVERITIES: frozenset[str] = frozenset({"critical", "fail"})


@dataclass(frozen=True)
class AdvisorStackReport:
    """Aggregate output from one ``assemble_stack`` invocation."""

    findings: tuple[Finding, ...]
    advisor_calls: tuple[AdvisorCall, ...]
    evidence_refs: tuple[str, ...]    # union of all V-rows surfaced
    stack_duration_ms: float
    advisor_count: int                # number of dispatched advisors

    @property
    def failed_advisor_count(self) -> int:
        return sum(1 for c in self.advisor_calls if c.status == "error")

    @property
    def critical_count(self) -> int:
        """Count of blocking findings (severity in {critical, fail})."""
        return sum(1 for f in self.findings if f.severity in _BLOCKING_SEVERITIES)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


def _module_version(module: Any) -> str:
    """Return a stable identifier for an advisor module.

    Uses ``__file__`` relative to the repo root so the version is git-
    diff-friendly. We deliberately do NOT call ``git rev-parse`` — that
    would add a subprocess + filesystem dependency to a pure-Python
    advisory layer. Callers needing exact commit attribution should pair
    the report with their own ``git rev-parse HEAD``.
    """
    f = getattr(module, "__file__", None)
    if not f:
        return f"<{module.__name__}>"
    return Path(f).name


def _summarize(value: Any, *, max_chars: int = 200) -> str:
    """Truncate-safe input description for audit trail."""
    s = repr(value)
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 3] + "..."


def _normalize_bc_type_name(
    report: bc_type_name_validity_advisor.BcTypeNameReport,
) -> tuple[Finding, ...]:
    advisor = "bc_type_name_validity_advisor"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    return tuple(
        Finding(
            source_advisor=advisor,
            severity=f.severity,
            code=f"bc_type_{f.verdict}",
            message=f.detail,
            location=f"{f.part_name}.bc.{f.field_name}",
            evidence_v_rows=rows,
            raw=f,
        )
        for f in report.findings
    )


def _normalize_face_orientation(
    report: face_orientation_advisor.FaceOrientationReport,
) -> tuple[Finding, ...]:
    advisor = "face_orientation_advisor"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    return tuple(
        Finding(
            source_advisor=advisor,
            severity=f.severity,
            code="face_orientation_deviation",
            message=(
                f"{f.body_name}: actual normal deviates "
                f"{f.angle_deviation_deg:.2f}° from intended "
                f"(tolerance {f.tolerance_deg:.2f}°)"
            ),
            location=f.body_name,
            evidence_v_rows=rows,
            raw=f,
        )
        for f in report.findings
    )


def _normalize_inlet_outlet(
    report: inlet_outlet_validator.InletOutletValidationReport,
) -> tuple[Finding, ...]:
    advisor = "inlet_outlet_validator"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    out: list[Finding] = []
    for f in report.findings:
        # Skip "pass" findings to keep stack output focused on actionable
        # items; pass-state is recoverable from the raw report.
        if f.severity == "pass":
            continue
        out.append(
            Finding(
                source_advisor=advisor,
                severity=f.severity,
                code=f"inlet_outlet_{f.role}",
                message=f"{f.body_name} ({f.role}): {f.reason}",
                location=f.body_name,
                evidence_v_rows=rows,
                raw=f,
            )
        )
    return tuple(out)


def _normalize_shm(
    report: shm_dict_validator.ShmDictReport,
) -> tuple[Finding, ...]:
    advisor = "shm_dict_validator"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    return tuple(
        Finding(
            source_advisor=advisor,
            severity=f.severity,
            code=f.code,
            message=f.message,
            location=f.location,
            evidence_v_rows=rows,
            raw=f,
        )
        for f in report.findings
    )


def _normalize_face_label(
    report: stl_face_label_validator.FaceLabelReport,
) -> tuple[Finding, ...]:
    advisor = "stl_face_label_validator"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    return tuple(
        Finding(
            source_advisor=advisor,
            severity=f.severity,
            code=f.code,
            message=f.detail,
            location=f.location,
            evidence_v_rows=rows,
            raw=f,
        )
        for f in report.findings
    )


def _normalize_extra_body(
    report: extra_body_advisor.ExtraBodyReport,
) -> tuple[Finding, ...]:
    advisor = "extra_body_advisor"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    return tuple(
        Finding(
            source_advisor=advisor,
            severity=f.severity,
            code=f"d6_{f.finding_type}",
            message=f.detail,
            location=f.body_name,
            evidence_v_rows=rows,
            raw=f,
        )
        for f in report.findings
    )


def _normalize_thermo(
    report: thermo_polynomial_range_advisor.ThermoPolynomialRangeReport,
) -> tuple[Finding, ...]:
    advisor = "thermo_polynomial_range_advisor"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    return tuple(
        Finding(
            source_advisor=advisor,
            severity=f.severity,
            code=f.code,
            message=f.message,
            location=f.location,
            evidence_v_rows=rows,
            raw=f,
        )
        for f in report.findings
    )


def _normalize_solver_block(
    report: solver_block_advisor.SolverBlockReport,
) -> tuple[Finding, ...]:
    advisor = "solver_block_advisor"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    return tuple(
        Finding(
            source_advisor=advisor,
            severity=f.severity,
            code=f.code,
            message=f.detail,
            location=f.location,
            evidence_v_rows=rows,
            raw=f,
        )
        for f in report.findings
    )


def _normalize_thin_wall(
    warnings: Sequence[thin_wall_advisor.ThinWallWarning],
) -> tuple[Finding, ...]:
    advisor = "thin_wall_advisor"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    return tuple(
        Finding(
            source_advisor=advisor,
            severity=w.severity,
            code="thin_wall_at_risk",
            message=w.message,
            location=w.patch_name,
            evidence_v_rows=rows,
            raw=w,
        )
        for w in warnings
    )


def _normalize_unit(
    detection: unit_detector.UnitDetection,
) -> tuple[Finding, ...]:
    """Surface a Finding only when the unit decision is UNKNOWN or
    confidence is low — high-confidence MM/M results are recoverable from
    the AdvisorCall.output and don't need to clutter findings."""
    advisor = "unit_detector"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    if detection.decision == unit_detector.GeometricUnit.UNKNOWN:
        severity = "warning"
        message = (
            "Unit could not be inferred from STEP header or bbox magnitude; "
            "engineer review required"
        )
    elif detection.confidence < 0.5:
        severity = "info"
        message = (
            f"Unit decided as {detection.decision.value} but confidence "
            f"is low ({detection.confidence:.2f}); review evidence"
        )
    else:
        return ()
    return (
        Finding(
            source_advisor=advisor,
            severity=severity,
            code="unit_inference",
            message=message,
            location=None,
            evidence_v_rows=rows,
            raw=detection,
        ),
    )


def _normalize_interfaces(
    detected: Sequence[virtual_interface_detector.DetectedInterface],
    *,
    gap_threshold_mm: float,
) -> tuple[Finding, ...]:
    advisor = "virtual_interface_detector"
    rows = _V_ROWS_PER_ADVISOR[advisor]
    out: list[Finding] = []
    for d in detected:
        if not d.matched:
            out.append(
                Finding(
                    source_advisor=advisor,
                    severity="warning",
                    code="interface_unmatched",
                    message=f"{d.patch_name}: {d.diagnostic}",
                    location=d.patch_name,
                    evidence_v_rows=rows,
                    raw=d,
                )
            )
            continue
        if virtual_interface_detector.should_have_been_shared_with_unintended_gap(
            d, max_gap_mm=gap_threshold_mm
        ):
            out.append(
                Finding(
                    source_advisor=advisor,
                    severity="critical",
                    code="d1_unintended_gap",
                    message=(
                        f"{d.patch_name}: facing-face candidates with "
                        f"sub-mm gap "
                        f"({d.inter_face_gap_mm:.4f} mm) — D1-class defect"
                    ),
                    location=d.patch_name,
                    evidence_v_rows=rows,
                    raw=d,
                )
            )
    return tuple(out)


def _should_dispatch_face_label_validator(
    *,
    shm_stl_face_normals: Mapping[str, Any] | None,
    parts_manifest: Mapping[str, Any] | None,
    shm_dict: Mapping[str, Any] | None,
) -> bool:
    """Decide whether D11 has anything meaningful to validate.

    Returns True iff at least one of:

    1. ``shm_stl_face_normals`` is provided with at least one entry —
       the STL inventory exists, so the orphan path (a) can fire.
    2. ``parts_manifest`` declares ``face_labels:`` on at least one
       part — manifest-internal paths (b)/(c) precondition.
    3. ``shm_dict`` carries either ``castellatedMeshControls.refinementSurfaces.<surf>.regions``
       or ``castellatedMeshControls.patches`` entries — path (c) reads
       these as the source of face-label references.

    The gate exists to keep advisor_count stable on legacy callers that
    pass parts_manifest without face_labels (the typical V62-A test
    fixture shape); dispatching D11 there would inflate ``advisor_count``
    by 1 on every existing test for no informational gain.
    """
    if isinstance(shm_stl_face_normals, Mapping) and len(shm_stl_face_normals) > 0:
        return True
    if isinstance(parts_manifest, Mapping):
        parts = parts_manifest.get("parts") or []
        if isinstance(parts, list):
            for entry in parts:
                if isinstance(entry, dict):
                    labels = entry.get("face_labels")
                    if isinstance(labels, list) and len(labels) > 0:
                        return True
    if isinstance(shm_dict, Mapping):
        cmc = shm_dict.get("castellatedMeshControls")
        if isinstance(cmc, Mapping):
            refsurfs = cmc.get("refinementSurfaces")
            if isinstance(refsurfs, Mapping):
                for surf_body in refsurfs.values():
                    if isinstance(surf_body, Mapping):
                        regions = surf_body.get("regions")
                        if isinstance(regions, Mapping) and len(regions) > 0:
                            return True
            patches = cmc.get("patches")
            if isinstance(patches, list) and len(patches) > 0:
                return True
    return False


def _dispatch(
    *,
    advisor_name: str,
    module: Any,
    input_summary: str,
    func: Any,
    args: tuple,
    kwargs: dict,
    normalize: Any,
    advisor_calls: list[AdvisorCall],
    findings: list[Finding],
) -> None:
    """Single advisor invocation with timing + crash isolation."""
    t0 = time.perf_counter()
    try:
        output = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        normalized = normalize(output)
        findings.extend(normalized)
        advisor_calls.append(
            AdvisorCall(
                advisor_name=advisor_name,
                status="ok",
                input_summary=input_summary,
                output=output,
                duration_ms=elapsed_ms,
                version=_module_version(module),
            )
        )
    except Exception as exc:  # crash isolation per spec
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        # JSON-serializable error payload — see AdvisorCall docstring +
        # Codex R0 P2 (2026-05-14).
        error_payload = {
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }
        advisor_calls.append(
            AdvisorCall(
                advisor_name=advisor_name,
                status="error",
                input_summary=input_summary,
                output=error_payload,
                duration_ms=elapsed_ms,
                version=_module_version(module),
            )
        )


def assemble_stack(
    *,
    parts_manifest: Mapping[str, Any] | None = None,
    interface_bodies: Mapping[str, virtual_interface_detector.BodyGeometry] | None = None,
    interface_specs: Sequence[virtual_interface_detector.InterfaceSpec] | None = None,
    interface_gap_threshold_mm: float = 1.0,
    shm_dict: Mapping[str, Any] | None = None,
    shm_available_emeshes: frozenset[str] | set[str] | None = None,
    shm_stl_face_normals: Mapping[str, Sequence[tuple[float, float, float]]] | None = None,
    thermo_dict: Mapping[str, Any] | None = None,
    thermo_boundary_conditions: Mapping[str, Any] | None = None,
    step_path: Path | str | None = None,
    step_bbox_max_extent_raw: float | None = None,
    step_body_extents_raw: list[float] | None = None,
    thin_wall_inputs: Mapping[str, Any] | None = None,
    bc_specs: Sequence[Mapping[str, Any]] | None = None,
    bc_fork: str = "main",
    stl_bbox_set: Mapping[str, Any] | None = None,
    extra_body_containment_tol_mm: float = 0.0,
    solver_block_snapshot: solver_block_advisor.SolverBlockSnapshot | None = None,
    **_unused: Any,  # forward-compatible (silently ignored, NOT logged)
) -> AdvisorStackReport:
    """Dispatch all applicable advisors based on provided artifacts.

    Returns a single ``AdvisorStackReport`` aggregating findings,
    per-advisor call audit trail, and union of evidence V-rows. Each
    advisor runs at most once; advisors whose required artifact is not
    provided are silently skipped (the absence is visible via
    ``advisor_count`` < total LANDED).

    All keyword-only arguments. Forward-compatible: unrecognized kwargs
    are accepted and ignored (do NOT raise) so future callers can pass
    new artifacts without breaking older stack versions.

    Raises:
        Never. Per-advisor failures are isolated; total catastrophic
        failure (e.g., the ``time`` module disappearing) would still
        raise — but no advisor's domain logic can take down the stack.
    """
    t_stack_start = time.perf_counter()
    findings: list[Finding] = []
    advisor_calls: list[AdvisorCall] = []
    advisors_dispatched: set[str] = set()

    if parts_manifest is not None:
        advisors_dispatched.add("face_orientation_advisor")
        _dispatch(
            advisor_name="face_orientation_advisor",
            module=face_orientation_advisor,
            input_summary=f"parts_manifest with {len(parts_manifest.get('parts') or [])} parts",
            func=face_orientation_advisor.check_face_orientation,
            args=(parts_manifest,),
            kwargs={},
            normalize=_normalize_face_orientation,
            advisor_calls=advisor_calls,
            findings=findings,
        )

        advisors_dispatched.add("inlet_outlet_validator")
        _dispatch(
            advisor_name="inlet_outlet_validator",
            module=inlet_outlet_validator,
            input_summary=f"parts_manifest with {len(parts_manifest.get('parts') or [])} parts",
            func=inlet_outlet_validator.validate_inlet_outlet_emission,
            args=(parts_manifest,),
            kwargs={},
            normalize=_normalize_inlet_outlet,
            advisor_calls=advisor_calls,
            findings=findings,
        )

    # D10 bc_type_name_validity dispatch (DEC-V62-A-sub-D10 · M-STACK-TRACK-3
    # §gap2 · V29 evidence row): explicit bc_specs win; else auto-extract from
    # parts_manifest['parts'][*]['bc'] blocks. Either path → dispatch when
    # there is at least one entry to check.
    bc_specs_resolved: list[dict[str, Any]] | None = None
    if bc_specs is not None:
        bc_specs_resolved = [dict(s) for s in bc_specs if isinstance(s, Mapping)]
    elif parts_manifest is not None:
        extracted = bc_type_name_validity_advisor.extract_bc_specs_from_parts_manifest(
            dict(parts_manifest)
        )
        if extracted:
            bc_specs_resolved = extracted
    if bc_specs_resolved:
        advisors_dispatched.add("bc_type_name_validity_advisor")
        _dispatch(
            advisor_name="bc_type_name_validity_advisor",
            module=bc_type_name_validity_advisor,
            input_summary=(
                f"{len(bc_specs_resolved)} parts with bc blocks "
                f"(fork={bc_fork})"
            ),
            func=bc_type_name_validity_advisor.detect_invalid_bc_types,
            args=(bc_specs_resolved,),
            kwargs={"fork": bc_fork},
            normalize=_normalize_bc_type_name,
            advisor_calls=advisor_calls,
            findings=findings,
        )

    if interface_bodies is not None and interface_specs is not None:
        advisors_dispatched.add("virtual_interface_detector")
        _dispatch(
            advisor_name="virtual_interface_detector",
            module=virtual_interface_detector,
            input_summary=f"{len(interface_bodies)} bodies, {len(interface_specs)} specs",
            func=virtual_interface_detector.detect_virtual_interfaces,
            args=(interface_bodies, interface_specs),
            kwargs={},
            normalize=lambda d: _normalize_interfaces(d, gap_threshold_mm=interface_gap_threshold_mm),
            advisor_calls=advisor_calls,
            findings=findings,
        )

    if shm_dict is not None:
        advisors_dispatched.add("shm_dict_validator")
        # Convert mutable mapping to dict for the validator (it accepts dict).
        shm_kwargs: dict[str, Any] = {}
        if shm_available_emeshes is not None:
            shm_kwargs["available_emeshes"] = shm_available_emeshes
        if shm_stl_face_normals is not None:
            shm_kwargs["stl_face_normals"] = dict(shm_stl_face_normals)
        _dispatch(
            advisor_name="shm_dict_validator",
            module=shm_dict_validator,
            input_summary=f"shm_dict keys={sorted(shm_dict.keys())[:5]}",
            func=shm_dict_validator.validate_shm_dict,
            args=(dict(shm_dict),),
            kwargs=shm_kwargs,
            normalize=_normalize_shm,
            advisor_calls=advisor_calls,
            findings=findings,
        )

    # D11 stl_face_label_validator dispatch (DEC-V63-A-sub-D11 ·
    # M-STACK-TRACK-1 §8 enhancement #3 · V94 evidence row).
    # Dispatches when there is face-label data to validate against:
    #   (1) explicit shm_stl_face_normals provided (STL inventory in
    #       hand — all 3 detection paths can fire), OR
    #   (2) parts_manifest declares face_labels on any part (paths
    #       (b) and (c) still meaningful without the STL contrast), OR
    #   (3) shm_dict carries refinementSurfaces.<surf>.regions or
    #       castellatedMeshControls.patches[] (path (c) requires only
    #       the shm reference walk + the parts_manifest declared union).
    # Otherwise silently skipped per V130. The advisor returns empty
    # when nothing to validate (no key-side polution).
    if _should_dispatch_face_label_validator(
        shm_stl_face_normals=shm_stl_face_normals,
        parts_manifest=parts_manifest,
        shm_dict=shm_dict,
    ):
        advisors_dispatched.add("stl_face_label_validator")
        _dispatch(
            advisor_name="stl_face_label_validator",
            module=stl_face_label_validator,
            input_summary=(
                "stl_face_normals="
                f"{None if shm_stl_face_normals is None else len(shm_stl_face_normals)} keys, "
                "parts_manifest="
                f"{None if parts_manifest is None else len(parts_manifest.get('parts') or [])} parts, "
                f"shm_dict={'yes' if shm_dict is not None else 'no'}"
            ),
            func=stl_face_label_validator.validate_face_label_consistency,
            args=(
                dict(shm_stl_face_normals) if shm_stl_face_normals is not None else None,
                dict(parts_manifest) if parts_manifest is not None else None,
                dict(shm_dict) if shm_dict is not None else None,
            ),
            kwargs={},
            normalize=_normalize_face_label,
            advisor_calls=advisor_calls,
            findings=findings,
        )

    # D6 extra_body_advisor dispatch (DEC-V63-A-sub-M-D6-HTTP-WIRE ·
    # V55 evidence row · case_016 10 mm debris cube class).
    #
    # Dispatch gate (Codex R1 P2 + P3 fix · 2026-05-14):
    #
    #   (P2) parts_manifest MUST be present. D6 detects three classes:
    #        unregistered_body / body_in_fluid_region /
    #        undeclared_inclusion. The latter two require manifest-side
    #        bbox+role data; the first compares the STL inventory
    #        against the manifest's body set. Without a manifest the
    #        comparison collapses to "every STL body is unregistered",
    #        flooding the report with bogus criticals on case_dir
    #        layouts where ``manifest.json`` carries ``stl_bbox_set`` but
    #        ``inputs/parts_manifest.*`` failed to load. Suppress
    #        instead.
    #
    #   (P3) stl_bbox_set MUST contain ≥1 *coercible* bbox. The advisor
    #        promises malformed entries are silently dropped via
    #        ``_coerce_bbox`` — applying that check at the gate too means
    #        a pure-malformed inventory does NOT inflate advisor_count
    #        or add V55 to evidence_refs (the dispatch would otherwise
    #        signal "D6 ran successfully" when in fact no body was
    #        evaluated).
    coercible_bbox_count = 0
    if isinstance(stl_bbox_set, Mapping) and parts_manifest is not None:
        coercible_bbox_count = sum(
            1
            for v in stl_bbox_set.values()
            if extra_body_advisor._coerce_bbox(v) is not None
        )
    if coercible_bbox_count > 0:
        advisors_dispatched.add("extra_body_advisor")
        _dispatch(
            advisor_name="extra_body_advisor",
            module=extra_body_advisor,
            input_summary=(
                f"stl_bbox_set={len(stl_bbox_set)} entries "
                f"({coercible_bbox_count} coercible), "
                f"parts_manifest={len(parts_manifest.get('parts') or [])} parts, "
                f"tol_mm={extra_body_containment_tol_mm}"
            ),
            func=extra_body_advisor.check_extra_bodies_in_fluid,
            args=(
                dict(parts_manifest),
                dict(stl_bbox_set),
            ),
            kwargs={"containment_tol_mm": extra_body_containment_tol_mm},
            normalize=_normalize_extra_body,
            advisor_calls=advisor_calls,
            findings=findings,
        )

    if thermo_dict is not None:
        advisors_dispatched.add("thermo_polynomial_range_advisor")
        thermo_args: tuple[Any, ...] = (dict(thermo_dict),)
        if thermo_boundary_conditions is not None:
            thermo_args = (dict(thermo_dict), dict(thermo_boundary_conditions))
        _dispatch(
            advisor_name="thermo_polynomial_range_advisor",
            module=thermo_polynomial_range_advisor,
            input_summary=f"thermo species={sorted(thermo_dict.keys())[:5]}",
            func=thermo_polynomial_range_advisor.check_thermo_polynomial_range,
            args=thermo_args,
            kwargs={},
            normalize=_normalize_thermo,
            advisor_calls=advisor_calls,
            findings=findings,
        )

    if step_path is not None:
        advisors_dispatched.add("unit_detector")
        unit_kwargs: dict[str, Any] = {}
        if step_bbox_max_extent_raw is not None:
            unit_kwargs["bbox_max_extent_raw"] = step_bbox_max_extent_raw
        if step_body_extents_raw is not None:
            unit_kwargs["body_extents_raw"] = list(step_body_extents_raw)
        _dispatch(
            advisor_name="unit_detector",
            module=unit_detector,
            input_summary=f"step_path={step_path}",
            func=unit_detector.detect_unit,
            args=(),
            kwargs={"step_path": step_path, **unit_kwargs},
            normalize=_normalize_unit,
            advisor_calls=advisor_calls,
            findings=findings,
        )

    # solver_block_advisor dispatch (DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2 ·
    # V27 + V28 evidence rows · case_006 ONERA M6 v1 2026-05-08 pre-fix
    # snapshot). Pure substrate consumer: fires only when caller supplies a
    # SolverBlockSnapshot. Silently no-op on non-density-based-symmetric
    # solver classes (the advisor itself returns empty findings; the
    # dispatch still counts since the advisor was invoked successfully).
    if solver_block_snapshot is not None:
        advisors_dispatched.add("solver_block_advisor")
        _dispatch(
            advisor_name="solver_block_advisor",
            module=solver_block_advisor,
            input_summary=(
                f"solver={solver_block_snapshot.solver}, "
                f"adjustTimeStep={solver_block_snapshot.adjust_time_step}, "
                f"preconditioners={len(solver_block_snapshot.preconditioners)}"
            ),
            func=solver_block_advisor.check_solver_block,
            args=(solver_block_snapshot,),
            kwargs={},
            normalize=_normalize_solver_block,
            advisor_calls=advisor_calls,
            findings=findings,
        )

    if thin_wall_inputs is not None:
        advisors_dispatched.add("thin_wall_advisor")
        _dispatch(
            advisor_name="thin_wall_advisor",
            module=thin_wall_advisor,
            input_summary=(
                f"{len(thin_wall_inputs.get('patches') or [])} patches, "
                f"cell_size={thin_wall_inputs.get('background_cell_size')}"
            ),
            func=thin_wall_advisor.detect_thin_wall_patches_at_risk,
            args=(
                thin_wall_inputs.get("patches") or (),
                thin_wall_inputs.get("refinement_levels") or {},
                thin_wall_inputs.get("background_cell_size") or 0.0,
            ),
            kwargs={
                k: v for k, v in thin_wall_inputs.items()
                if k in {"min_cells_per_thickness"}
            },
            normalize=_normalize_thin_wall,
            advisor_calls=advisor_calls,
            findings=findings,
        )

    # Union of evidence V-rows across actually-dispatched advisors.
    evidence_set: set[str] = set()
    for name in advisors_dispatched:
        evidence_set.update(_V_ROWS_PER_ADVISOR.get(name, ()))
    evidence_refs = tuple(sorted(evidence_set))

    stack_duration_ms = (time.perf_counter() - t_stack_start) * 1000.0

    return AdvisorStackReport(
        findings=tuple(findings),
        advisor_calls=tuple(advisor_calls),
        evidence_refs=evidence_refs,
        stack_duration_ms=stack_duration_ms,
        advisor_count=len(advisors_dispatched),
    )


__all__ = [
    "AdvisorCall",
    "AdvisorStackReport",
    "Finding",
    "assemble_stack",
]
