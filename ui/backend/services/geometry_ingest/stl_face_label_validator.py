"""STL face-label consistency advisor (D11).

Detects the V94 face-label-loss death-class — STL files emitted from a
CAD pipeline that discards face-zone names (canonically
``cq.exporters.export()``'s single-watertight-shell behaviour) carry no
per-face label metadata. Downstream sHM cannot create the named patches
the case profile asks for; the engineer writes BCs aspirationally on
``hot_inlet`` / ``hot_outlet`` / ``hot_walls`` but the substrate only
ever materialises one undifferentiated ``region_hot_fluid`` patch, and
the solver silently degenerates into a sealed-conduction problem instead
of the intended flow-through HX. case_011 v1 (2026-05-09 sediment ·
surfaced 2026-05-14 by v3 sub-session solver e2e attempt) is the
canonical reference; V99 and V81 are sibling members of the same
"CAD→STL→sHM contract gap" family.

Design choice — pure dict consumer (mirrors A8 ``shm_dict_validator`` /
A10 ``thermo_polynomial_range_advisor`` / D6 ``extra_body_advisor`` /
D10 ``bc_type_name_validity_advisor``):

The advisor consumes three already-parsed inputs and performs only set
arithmetic + dict walks — no FreeCAD, trimesh, OpenFOAM, or LLM
dependency. STL parsing stays in the caller (typically the
``shm_dict_validator`` V99-widening upstream that already turns STL
files into a ``stl_face_normals`` mapping).

Three detection paths:

(a) ``orphan_declared_label`` — **warning** — a face label appears in
    a part's ``face_labels:`` declaration but is NOT a key in
    ``stl_face_normals``. The classic V94 sighting: manifest claims
    ``hot_inlet`` exists but the cq.exporters output only contains the
    parent body label (``region_hot_fluid``). Downstream sHM cannot
    create a ``hot_inlet`` patch from a label that never made it into
    the STL.

(b) ``duplicate_face_label_in_manifest`` — **warning** — the same face
    label is declared by ≥2 parts in ``parts_manifest['parts']``. sHM /
    BC orchestration cannot disambiguate which part's patch a BC
    references when two parts both claim ``hot_inlet``; the engineer
    will see at-best a confusing patch-name collision at meshing time
    and at-worst a silently wrong BC application. (The dict-keyed
    ``stl_face_normals`` cannot itself express duplicate labels — keys
    are unique — so duplicate detection lives at the manifest layer,
    which is the layer the engineer authors and the layer where the
    duplicate is recoverable before it propagates into STL emission.)

(c) ``shm_reference_undeclared_in_manifest`` — **warning** — the
    ``shm_dict`` references a face label (via
    ``castellatedMeshControls.refinementSurfaces.<surf>.regions.<label>``
    or via the ``castellatedMeshControls.patches`` list) that is NOT
    declared in any part's ``face_labels:``. Detects "the engineer wrote
    the sHM dict assuming patches exist that the manifest never
    declared". A8 already covers ``refinementSurfaces.<surf>`` keying
    against the ``geometry`` block; D11 supplements A8 by walking one
    level deeper into per-surface ``regions:`` (which is where face
    labels live, distinct from geometry surface names).

Anti-scope (per V62-A B34 retro TRACK-1 §8 #3 + V63-A charter #1):

- does NOT detect STL geometric quality (watertightness, flipped
  normals, non-manifold edges) — that is V41/V79/V87 territory and
  already covered by ``face_orientation_advisor`` + caller-side STL
  loaders.
- does NOT detect STL UNIT mismatches — ``unit_detector`` is the SSOT.
- does NOT replace A8 ``shm_dict_validator``. A8 keys
  ``refinementSurfaces.<surf>`` against ``geometry``; D11 keys
  ``refinementSurfaces.<surf>.regions.<label>`` (one level deeper)
  against face-label declarations. The two advisors share NO finding
  codes — A8 emits ``missing_geometry_ref`` /
  ``geometry_orphan`` / ``typo_suspicion``; D11 emits
  ``orphan_declared_label`` / ``duplicate_face_label_in_manifest`` /
  ``shm_reference_undeclared_in_manifest``.
- does NOT load STL itself — caller-side trimesh / cadquery /
  freecad_step_to_stl emits ``stl_face_normals`` upstream.
- does NOT mutate any case directory. V130 advisor-not-driver — the
  advisor only ever returns a frozen report; the caller decides what
  to do.

Expected ``parts_manifest`` schema (subset; only fields read here):

.. code-block:: yaml

   parts:
     - name: region_hot_fluid
       role: region_fluid
       face_labels: [hot_inlet, hot_outlet, hot_walls]   # NEW for D11
     - name: region_cold_fluid
       role: region_fluid
       face_labels: [cold_inlet, cold_outlet, cold_walls]
     - name: region_solid
       role: solid
       # face_labels omitted → no D11 contribution from this part

Expected ``stl_face_normals`` schema (V99 compat):

.. code-block:: python

   {
     "region_hot_fluid": [(nx, ny, nz), ...],   # one entry per STL solid block
     "region_cold_fluid": [(nx, ny, nz), ...],  # → if cq.exporters only emits
     "region_solid": [(nx, ny, nz), ...],       #   parent-body labels, the
                                                #   D11 (a) path will fire on
                                                #   every face_labels entry
   }

Expected ``shm_dict`` schema (subset):

.. code-block:: yaml

   castellatedMeshControls:
     refinementSurfaces:
       region_hot_fluid:
         level: [2, 2]
         regions:                       # KEYS here are face labels
           hot_inlet:
             level: [3, 3]
             patchInfo: { type: patch }
           hot_outlet: { level: [3, 3], patchInfo: { type: patch } }
     patches:                           # OR alternative top-level patches
       - name: hot_inlet
         patchInfo: { type: patch }

References:

- V94 in ``docs/openfoam_corpus/industrial_solver_findings_v_series.md``
  (case_011 v1 2026-05-09 sediment · surfaced 2026-05-14 v3 sub-session)
- V62-A B34 retro M-STACK-TRACK-1-rerun
  ``.planning/retrospectives/2026-05-14_stack_track_c_session_1_rerun_case_011_v5b.md``
  §8 #3 (sole remaining open enhancement after V99-WIDEN + REQ-SCHEMA-EXPAND)
- Parent sub-DEC: ``DEC-V63-A-sub-D11`` (this advisor)
- Sibling validator pattern: ``bc_type_name_validity_advisor.py`` (D10
  · 2026-05-14 single-case-land precedent)
- A8 widening precedent ``shm_dict_validator.py`` ``stl_face_normals``
  argument (DEC-V62-A-sub-A8-V99-WIDEN) — D11 reads the same upstream
  input without owning the STL parse.

Promotion gate (single-case-land per A2 v1 / D6 / D10 precedent):
single case_011 V94 evidence at landing; [QUESTIONABLE] marker carried
until a 2nd industrial case sediments a face-label-loss class (case_013
/ case_015 CHT-LES are forward-loaded candidates per case_proposal_queue).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---- Dataclasses -----------------------------------------------------------


@dataclass(frozen=True)
class FaceLabelFinding:
    """One face-label-consistency finding."""

    advisor_name: str            # always "stl_face_label_validator"
    severity: str                # "warning" (D11 emits no critical today)
    code: str                    # "orphan_declared_label" | "duplicate_face_label_in_manifest" | "shm_reference_undeclared_in_manifest"
    face_label: str
    location: str                # human-readable dict path, e.g. "parts_manifest.parts[2].face_labels[0]"
    detail: str
    evidence_v_rows: tuple[str, ...]   # always at least ("V94",)
    suggested_fix: str | None


@dataclass(frozen=True)
class FaceLabelReport:
    """Outcome of :func:`validate_face_label_consistency`.

    The three label sets are exposed verbatim on the report so callers
    can audit the inputs without re-parsing.
    """

    findings: tuple[FaceLabelFinding, ...]
    declared_labels: tuple[str, ...]            # union of all parts_manifest face_labels
    stl_labels: tuple[str, ...]                 # keys of stl_face_normals
    shm_referenced_labels: tuple[str, ...]      # face labels referenced by shm_dict

    @property
    def is_clean(self) -> bool:
        return len(self.findings) == 0

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")


# ---- Helpers ---------------------------------------------------------------


def _collect_declared_labels(
    parts_manifest: dict[str, Any] | None,
) -> tuple[dict[str, list[str]], tuple[str, ...]]:
    """Walk ``parts_manifest['parts']`` and collect face_labels per part.

    Returns ``(per_part_labels, ordered_union)`` where
    ``per_part_labels[part_name] = [label, ...]`` and
    ``ordered_union`` preserves first-seen order across parts. Parts
    without a string ``name`` or without a list-shaped ``face_labels``
    are silently skipped per V130 (degrade silently, never raise).
    """
    per_part: dict[str, list[str]] = {}
    ordered: list[str] = []
    seen: set[str] = set()
    if not isinstance(parts_manifest, dict):
        return per_part, tuple(ordered)
    parts = parts_manifest.get("parts") or []
    if not isinstance(parts, list):
        return per_part, tuple(ordered)
    for entry in parts:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        labels_raw = entry.get("face_labels")
        if not isinstance(name, str) or not isinstance(labels_raw, list):
            continue
        cleaned: list[str] = []
        for label in labels_raw:
            if not isinstance(label, str):
                continue
            stripped = label.strip()
            if not stripped:
                continue
            cleaned.append(stripped)
            if stripped not in seen:
                seen.add(stripped)
                ordered.append(stripped)
        if cleaned:
            per_part[name] = cleaned
    return per_part, tuple(ordered)


def _collect_stl_labels(
    stl_face_normals: dict[str, Any] | None,
) -> tuple[str, ...]:
    """Return the keys of ``stl_face_normals`` as an ordered tuple.

    Non-string keys are silently skipped. The advisor never inspects the
    normals themselves — A4 ``face_orientation_advisor`` is the SSOT for
    normal-vector audits; D11 only needs to know which labels physically
    exist in the STL inventory.
    """
    if not isinstance(stl_face_normals, dict):
        return ()
    out: list[str] = []
    for key in stl_face_normals:
        if isinstance(key, str):
            stripped = key.strip()
            if stripped:
                out.append(stripped)
    return tuple(out)


def _collect_shm_referenced_labels(
    shm_dict: dict[str, Any] | None,
) -> tuple[tuple[str, str], ...]:
    """Walk shm_dict and collect (label, location) pairs.

    Two reference idioms are covered:

    1. ``castellatedMeshControls.refinementSurfaces.<surf>.regions``
       keys — the canonical OpenFOAM face-label refinement convention.
    2. ``castellatedMeshControls.patches`` list of dicts, each with a
       ``name:`` field — the alternative top-level patches block used
       by some case templates.

    Locations are surfaced verbatim into findings so the engineer can
    grep the offending dict path. Per V130 missing / malformed shapes
    degrade silently.
    """
    if not isinstance(shm_dict, dict):
        return ()
    out: list[tuple[str, str]] = []
    cmc = shm_dict.get("castellatedMeshControls")
    if isinstance(cmc, dict):
        refsurfs = cmc.get("refinementSurfaces")
        if isinstance(refsurfs, dict):
            for surf_name, surf_body in refsurfs.items():
                if not isinstance(surf_name, str) or not isinstance(surf_body, dict):
                    continue
                regions = surf_body.get("regions")
                if not isinstance(regions, dict):
                    continue
                for label, _ in regions.items():
                    if not isinstance(label, str):
                        continue
                    stripped = label.strip()
                    if not stripped:
                        continue
                    out.append((
                        stripped,
                        f"shm_dict.castellatedMeshControls.refinementSurfaces.{surf_name}.regions.{stripped}",
                    ))
        patches = cmc.get("patches")
        if isinstance(patches, list):
            for idx, entry in enumerate(patches):
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                if not isinstance(name, str):
                    continue
                stripped = name.strip()
                if not stripped:
                    continue
                out.append((
                    stripped,
                    f"shm_dict.castellatedMeshControls.patches[{idx}].name",
                ))
    return tuple(out)


# ---- Public API ------------------------------------------------------------


def validate_face_label_consistency(
    stl_face_normals: dict[str, Any] | None,
    parts_manifest: dict[str, Any] | None,
    shm_dict: dict[str, Any] | None,
) -> FaceLabelReport:
    """Audit a (parts_manifest, stl_face_normals, shm_dict) triple for V94-class drift.

    Three detection paths fire as warnings when their pre-conditions are
    met; otherwise the report stays clean. All three inputs are optional
    — when an input is absent, detections that depend on it silently
    degrade (per V130, never raise on missing input).

    Args:
        stl_face_normals: V99-compat mapping ``{stl_solid_label:
            list_of_face_normals}``. Only the keys are inspected.
        parts_manifest: standard parts manifest dict; each ``parts[i]``
            entry may carry a ``face_labels: [str, ...]`` list.
        shm_dict: parsed snappyHexMeshDict (subset). Reads only
            ``castellatedMeshControls.refinementSurfaces.<surf>.regions``
            keys and ``castellatedMeshControls.patches[].name``.

    Returns:
        :class:`FaceLabelReport` whose ``findings`` carry the three
        detection paths in source order (manifest walk → manifest
        walk → shm walk).
    """
    per_part, declared_union = _collect_declared_labels(parts_manifest)
    stl_labels = _collect_stl_labels(stl_face_normals)
    stl_set = set(stl_labels)
    declared_set = set(declared_union)
    shm_refs = _collect_shm_referenced_labels(shm_dict)

    findings: list[FaceLabelFinding] = []

    # ---- (a) orphan_declared_label ---------------------------------------
    # Manifest declares face labels but the STL inventory does not contain
    # corresponding solid keys. Classic V94 sighting (cq.exporters single-
    # shell emission losing CAD-stage face names).
    if stl_face_normals is not None:
        for part_name, labels in per_part.items():
            for idx, label in enumerate(labels):
                if label in stl_set:
                    continue
                findings.append(
                    FaceLabelFinding(
                        advisor_name="stl_face_label_validator",
                        severity="warning",
                        code="orphan_declared_label",
                        face_label=label,
                        location=(
                            f"parts_manifest.parts['{part_name}'].face_labels[{idx}]"
                        ),
                        detail=(
                            f"part '{part_name}' declares face label "
                            f"'{label}' but the STL inventory has no "
                            f"corresponding solid key — sHM will not be "
                            f"able to create a '{label}' patch (V94 face-"
                            f"label-loss class · likely cause: CAD→STL "
                            f"pipeline emitted single-shell solid without "
                            f"face-zone metadata, e.g. cq.exporters.export "
                            f"without cq.Assembly face naming)"
                        ),
                        evidence_v_rows=("V94",),
                        suggested_fix=(
                            "Re-emit the STL with explicit face naming "
                            "(per-face STL via cq.Assembly + cq.Sketch.face('Tagged'), "
                            "or FreeCAD MeshPart with STEP face-label sidecar), "
                            "or post-process the existing mesh with topoSet "
                            "+ createPatch to split the parent patch into "
                            f"the declared '{label}' (and siblings)."
                        ),
                    )
                )

    # ---- (b) duplicate_face_label_in_manifest -----------------------------
    # The same face label is declared by ≥2 parts. sHM/BC orchestration
    # cannot disambiguate; the duplicate is recoverable at the manifest
    # layer (which is where the engineer can act) before the conflict
    # propagates into STL emission.
    label_to_parts: dict[str, list[str]] = {}
    for part_name, labels in per_part.items():
        for label in labels:
            label_to_parts.setdefault(label, []).append(part_name)
    for label, owners in label_to_parts.items():
        if len(owners) >= 2:
            findings.append(
                FaceLabelFinding(
                    advisor_name="stl_face_label_validator",
                    severity="warning",
                    code="duplicate_face_label_in_manifest",
                    face_label=label,
                    location=(
                        f"parts_manifest.parts[*].face_labels (declared by "
                        f"{len(owners)} parts: {sorted(owners)})"
                    ),
                    detail=(
                        f"face label '{label}' is declared by parts "
                        f"{sorted(owners)} — when both parts emit STLs "
                        f"with the same solid label, sHM cannot "
                        f"disambiguate which patch a BC targeting "
                        f"'{label}' applies to (V94-adjacent: face-label "
                        f"namespace ambiguity at the orchestration layer)"
                    ),
                    evidence_v_rows=("V94",),
                    suggested_fix=(
                        f"Rename face labels to be globally unique across "
                        f"parts (e.g. '{label}' → '{label}_<part_prefix>'), "
                        "or merge the conflicting parts into one if they "
                        "logically share the same physical face."
                    ),
                )
            )

    # ---- (c) shm_reference_undeclared_in_manifest -------------------------
    # shm_dict references a face label (via refinementSurfaces.<surf>.regions
    # or via patches[].name) that no part declares. Engineer authored sHM
    # assuming the patch will exist, but the manifest never declared it —
    # either rename in sHM or add to manifest.
    seen_shm: set[str] = set()
    for label, location in shm_refs:
        if label in declared_set:
            continue
        # Suppress duplicate emit when the same label appears at multiple
        # shm locations — first location wins; the engineer can fix the
        # root cause once.
        if label in seen_shm:
            continue
        seen_shm.add(label)
        findings.append(
            FaceLabelFinding(
                advisor_name="stl_face_label_validator",
                severity="warning",
                code="shm_reference_undeclared_in_manifest",
                face_label=label,
                location=location,
                detail=(
                    f"shm_dict references face label '{label}' at "
                    f"{location} but no parts_manifest entry declares "
                    f"this label under face_labels — the sHM dict was "
                    f"authored assuming a patch that the manifest never "
                    f"promised the STL would carry (V94 cross-layer "
                    f"drift between sHM intent and manifest contract)"
                ),
                evidence_v_rows=("V94",),
                suggested_fix=(
                    f"Either add '{label}' to the relevant part's "
                    "face_labels in parts_manifest (and ensure the CAD "
                    "stage actually emits a labeled face), or remove "
                    "the reference from shm_dict if the patch was an "
                    "authoring leftover."
                ),
            )
        )

    shm_referenced_labels = tuple(sorted({label for label, _ in shm_refs}))

    return FaceLabelReport(
        findings=tuple(findings),
        declared_labels=declared_union,
        stl_labels=stl_labels,
        shm_referenced_labels=shm_referenced_labels,
    )


__all__ = [
    "FaceLabelFinding",
    "FaceLabelReport",
    "validate_face_label_consistency",
]
