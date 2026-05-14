"""Extra-body-in-fluid advisor (D6).

Detects bodies that sHM would silently treat as a no-slip wall inside a
fluid region — the FOD-inspection class problem surfaced by V55
(case_016 10 mm debris cube at (320, 18, -79) mm inside the M219 cavity,
sedimented 2026-05-11). sHM happily meshes around a fully-disjoint
internal solid; without an advisor, the engineer has no surfaced
warning that the assembly contains a body the brief never declared.

Design choice — pure dict consumer (mirrors A4 face_orientation_advisor /
A5 inlet_outlet_validator / A8 shm_dict_validator / A10
thermo_polynomial_range_advisor):

The advisor consumes a parts_manifest dict whose body entries already
carry their AABB in millimetres, plus a separately-prepared STL bbox
set from the caller's STL loader. STL loading (trimesh, fast_simplification,
etc.) stays in the caller; this module performs only numeric
bbox-containment arithmetic. Benefits:

* matches the sibling-advisor pattern (pure dict in → dataclass report
  out, no FreeCAD / trimesh / numpy runtime dependency)
* unit-testable in a no-FreeCAD-no-trimesh pytest env
* lets the caller batch / cache STL loads (a per-call STL re-load would
  dominate cost for typical 10-20 body cases)

Three detection types:

(a) ``unregistered_body`` — **critical** — body present in the STL set
    but absent from parts_manifest. The most common case_016-class
    sighting: helper-body / construction-body / FOD debris exported
    alongside legitimate parts without an entry in the manifest.

(b) ``body_in_fluid_region`` — **warning** — a body declared with a
    solid-class role whose AABB lies fully inside another body's AABB
    that is declared with a fluid-class role. The "I have an extra
    body but I logged it as a regular solid; nobody noticed it sits
    inside the cavity" sighting.

(c) ``undeclared_inclusion`` — **warning** — two solid-class bodies
    whose AABBs overlap (one fully inside the other) without an entry
    in ``parts_manifest['declared_inclusions']``. The "engineer knew
    body X is meant to be inside body Y; just forgot to declare it"
    sighting. Once declared, the same geometry passes silently.

Anti-scope (per advisor_candidates_a4_a8.md §D6):
- does NOT detect bodies partially inside / partially outside (overlap
  classifier V59 covers that)
- does NOT load STL itself (caller-side trimesh / fast_simplification
  is the source of truth for STL bbox)
- does NOT call out to FreeCAD or any CAD-library runtime

References:

- V55 in ``industrial_case_solver_findings.md`` (case_016 first injection
  · 10 mm debris cube · defect_manifest.yaml expected_advisor_to_catch:
  none_landed)
- V55 mirror in ``docs/openfoam_corpus/industrial_solver_findings_v_series.md``
- Pre-drafted spec in
  ``.planning/methodology/advisor_candidates_a4_a8.md`` §D6_advisor
- Parent sub-DEC: V62-A-charter (D6 promote · 2026-05-14)
- Sibling validator pattern: ``face_orientation_advisor.py`` (A4)
- A2 v1 precedent: single-case-land with [QUESTIONABLE] marker pending
  ≥2-case cross-validation (case_018 dispatched but not sedimented as
  of 2026-05-14)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Bbox = tuple[float, float, float, float, float, float]
"""AABB tuple: (xmin, ymin, zmin, xmax, ymax, zmax) in mm."""

FLUID_ROLES: frozenset[str] = frozenset({"fluid", "region_air", "region_fluid"})
"""Roles a body can declare to be treated as fluid region in containment math.

The case_016 sandbox uses ``region_air`` for the cavity volume. Generic
``fluid`` covers other cases (case_003 plenum, case_011 plate-fin shell,
etc.). ``region_fluid`` is included as a forward-compat alias.
"""

SOLID_ROLES: frozenset[str] = frozenset(
    {"solid", "internal_wall", "structural", "debris", "wall_solid"}
)
"""Roles a body can declare to be treated as solid (the "thing that could
silently end up inside fluid" class).

A role outside both ``FLUID_ROLES`` and ``SOLID_ROLES`` is treated as
``solid`` by default (defensive default — V55 root cause was a body
with no declared role at all).
"""


@dataclass(frozen=True)
class ExtraBodyFinding:
    """One audit result for one body."""

    body_name: str
    finding_type: str  # "unregistered_body" | "body_in_fluid_region" | "undeclared_inclusion"
    severity: str  # "critical" | "warning"
    container_name: str | None  # the body whose AABB contains body_name (None for unregistered)
    detail: str


@dataclass(frozen=True)
class ExtraBodyReport:
    """Outcome of :func:`check_extra_bodies_in_fluid`."""

    findings: tuple[ExtraBodyFinding, ...]
    registered_count: int  # bodies declared in parts_manifest
    stl_count: int  # bodies present in STL bbox set
    suspected_extras: tuple[str, ...]  # convenience: body_names with any finding

    @property
    def is_clean(self) -> bool:
        """True iff no body produced any finding."""
        return len(self.findings) == 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


def _coerce_bbox(value: Any) -> Bbox | None:
    """Coerce a 6-element iterable to a normalized Bbox, or None.

    Normalizes (xmin,xmax) etc. to ensure xmin ≤ xmax. Anything that
    cannot be coerced (None, wrong length, non-numeric) → None so the
    caller can decide to skip the body.
    """
    if value is None:
        return None
    try:
        if len(value) != 6:
            return None
    except TypeError:
        return None
    try:
        coords = tuple(float(v) for v in value)
    except (TypeError, ValueError):
        return None
    xmin, ymin, zmin, xmax, ymax, zmax = coords
    if xmax < xmin:
        xmin, xmax = xmax, xmin
    if ymax < ymin:
        ymin, ymax = ymax, ymin
    if zmax < zmin:
        zmin, zmax = zmax, zmin
    return (xmin, ymin, zmin, xmax, ymax, zmax)


def _bbox_contains(outer: Bbox, inner: Bbox, *, tol_mm: float = 0.0) -> bool:
    """True iff `outer` AABB fully contains `inner` AABB.

    A point-inclusive containment with optional tolerance. A 10 mm cube
    at (320, 18, -79) mm with bbox [315,13,-84,325,23,-74] is contained
    by a cavity bbox of [0,-200,-200,600,200,200] only if every cube
    extremum lies within the cavity extremum.
    """
    ox0, oy0, oz0, ox1, oy1, oz1 = outer
    ix0, iy0, iz0, ix1, iy1, iz1 = inner
    return (
        ox0 - tol_mm <= ix0
        and ox1 + tol_mm >= ix1
        and oy0 - tol_mm <= iy0
        and oy1 + tol_mm >= iy1
        and oz0 - tol_mm <= iz0
        and oz1 + tol_mm >= iz1
    )


def _classify_role(role: Any) -> str:
    """Map a raw role string to {'fluid', 'solid'} (defaults to 'solid').

    Defensive default — V55 root cause was an undeclared / un-roled
    body (the debris cube had no manifest entry at all). When we DO see
    a manifest entry but the role is missing or unknown, treat it as a
    solid so it gets evaluated for fluid-region containment rather than
    silently skipped.
    """
    if not isinstance(role, str):
        return "solid"
    if role in FLUID_ROLES:
        return "fluid"
    return "solid"


def check_extra_bodies_in_fluid(
    parts_manifest: dict[str, Any],
    stl_bbox_set: dict[str, Any],
    *,
    containment_tol_mm: float = 0.0,
) -> ExtraBodyReport:
    """Audit a parts_manifest + STL bbox set for D6-class extra bodies.

    Expected schema (subset; only the fields read here are documented):

    .. code-block:: yaml

       parts:
         - name: region_air        # the cavity / fluid domain
           role: region_air        # fluid-class
           bbox: [xmin, ymin, zmin, xmax, ymax, zmax]  # mm
         - name: cavity_wall
           role: solid
           bbox: [...]
       declared_inclusions:        # OPTIONAL — bodies engineer knowingly nested
         - outer: outer_shell
           inner: probe_holder

    Caller-prepared ``stl_bbox_set`` maps body name → 6-tuple bbox in mm
    (typically computed via ``trimesh.bounds`` after STL load).

    Returns:
        :class:`ExtraBodyReport` with one finding per detected anomaly,
        plus aggregate counts. Bodies absent from one side but present
        in the other are noted; partial-overlap (neither fully contains
        the other) is silently skipped per anti-scope §V59.
    """
    findings: list[ExtraBodyFinding] = []
    parts = parts_manifest.get("parts") or []
    declared_inclusions_raw = parts_manifest.get("declared_inclusions") or []

    manifest_bbox: dict[str, Bbox] = {}
    manifest_role: dict[str, str] = {}
    for part in parts:
        if not isinstance(part, dict):
            continue
        name = part.get("name")
        if not isinstance(name, str):
            continue
        bbox = _coerce_bbox(part.get("bbox"))
        if bbox is not None:
            manifest_bbox[name] = bbox
        manifest_role[name] = _classify_role(part.get("role"))

    stl_bbox: dict[str, Bbox] = {}
    for stl_name, raw in stl_bbox_set.items():
        coerced = _coerce_bbox(raw)
        if coerced is not None and isinstance(stl_name, str):
            stl_bbox[stl_name] = coerced

    declared_pairs: set[tuple[str, str]] = set()
    for entry in declared_inclusions_raw:
        if not isinstance(entry, dict):
            continue
        outer = entry.get("outer")
        inner = entry.get("inner")
        if isinstance(outer, str) and isinstance(inner, str):
            declared_pairs.add((outer, inner))

    # Detection (a) — unregistered_body: STL set has body not in manifest
    for stl_name in stl_bbox:
        if stl_name not in manifest_role:
            findings.append(
                ExtraBodyFinding(
                    body_name=stl_name,
                    finding_type="unregistered_body",
                    severity="critical",
                    container_name=None,
                    detail=(
                        f"body '{stl_name}' present in STL set but absent "
                        f"from parts_manifest — sHM will mesh it as a "
                        f"no-slip wall without engineer awareness "
                        f"(V55 case_016 sighting class)"
                    ),
                )
            )

    # Detection (b) — body_in_fluid_region: solid-role body bbox ⊂ fluid-role body bbox
    fluid_bodies = [n for n, r in manifest_role.items() if r == "fluid"]
    solid_bodies = [n for n, r in manifest_role.items() if r == "solid"]

    for solid_name in solid_bodies:
        solid_bbox = manifest_bbox.get(solid_name)
        if solid_bbox is None:
            continue
        for fluid_name in fluid_bodies:
            fluid_bbox = manifest_bbox.get(fluid_name)
            if fluid_bbox is None:
                continue
            if _bbox_contains(fluid_bbox, solid_bbox, tol_mm=containment_tol_mm):
                # declared inclusion suppresses the warning (engineer
                # explicitly acknowledged this is intentional, e.g. an
                # internal_wall whose role got coerced upstream)
                if (fluid_name, solid_name) in declared_pairs:
                    continue
                findings.append(
                    ExtraBodyFinding(
                        body_name=solid_name,
                        finding_type="body_in_fluid_region",
                        severity="warning",
                        container_name=fluid_name,
                        detail=(
                            f"solid body '{solid_name}' AABB sits fully "
                            f"inside fluid region '{fluid_name}' AABB; "
                            f"sHM will cellZone-it as a no-slip wall — "
                            f"verify this is intentional and add a "
                            f"declared_inclusions entry if so"
                        ),
                    )
                )

    # Detection (c) — undeclared_inclusion: solid ⊂ solid without declaration
    for inner_name in solid_bodies:
        inner_bbox = manifest_bbox.get(inner_name)
        if inner_bbox is None:
            continue
        for outer_name in solid_bodies:
            if outer_name == inner_name:
                continue
            outer_bbox = manifest_bbox.get(outer_name)
            if outer_bbox is None:
                continue
            if not _bbox_contains(
                outer_bbox, inner_bbox, tol_mm=containment_tol_mm
            ):
                continue
            # Avoid double-reporting when bboxes are identical (both
            # contain each other under tolerance) — only emit when the
            # outer is strictly larger.
            ox0, oy0, oz0, ox1, oy1, oz1 = outer_bbox
            ix0, iy0, iz0, ix1, iy1, iz1 = inner_bbox
            outer_vol = (ox1 - ox0) * (oy1 - oy0) * (oz1 - oz0)
            inner_vol = (ix1 - ix0) * (iy1 - iy0) * (iz1 - iz0)
            if outer_vol <= inner_vol:
                continue
            if (outer_name, inner_name) in declared_pairs:
                continue
            findings.append(
                ExtraBodyFinding(
                    body_name=inner_name,
                    finding_type="undeclared_inclusion",
                    severity="warning",
                    container_name=outer_name,
                    detail=(
                        f"solid '{inner_name}' AABB sits fully inside "
                        f"solid '{outer_name}' AABB without a "
                        f"declared_inclusions entry; if intentional "
                        f"(e.g. probe holder inside instrumentation "
                        f"cowling) declare the pair, else investigate"
                    ),
                )
            )

    suspected = tuple(sorted({f.body_name for f in findings}))
    return ExtraBodyReport(
        findings=tuple(findings),
        registered_count=len(manifest_role),
        stl_count=len(stl_bbox),
        suspected_extras=suspected,
    )
