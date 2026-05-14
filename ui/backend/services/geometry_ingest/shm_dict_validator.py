"""snappyHexMeshDict pre-flight validator (A8 advisor).

Closes V52 (case_012 sHM key typo class · ``minMedianAxisAngle`` instead
of canonical ``minMedialAxisAngle``), V86 (case_011 features-list
orphaning · ``surfaceFeatureExtract`` writes ``.eMesh`` files but
``snappyHexMeshDict.castellatedMeshControls.features ()`` is an empty
list, leaving the upstream stage output unconsumed), V99 (case_003 v2
STL-driven ``symmetryPlane``-typed refinementSurface FAILS planarity
when source STL is a closed multi-face shell — sHM concatenates multiple
cut sides and checkMesh rejects with ``non-planar``) and V100 (case_003
v2 entry-point type-guard gap · passing a non-dict raised an opaque
``'str' object has no attribute 'get'`` deep in ``_walk_dict_keys``
instead of a typed, actionable error at the API boundary).

Design choice — pure dict consumer (mirrors A4 :mod:`face_orientation_advisor`
and A5 :mod:`inlet_outlet_validator`):

The advisor consumes a parsed ``snappyHexMeshDict`` dict + a caller-
supplied ``available_emeshes`` set + a caller-supplied
``stl_face_normals`` map (V99 widening). Dictionary parsing AND STL
face-normal extraction are both the caller's responsibility — typically
via a thin ``foamDictionary``-or-pyfoam adapter on the case directory
and a ``trimesh``/``numpy-stl`` loader on the surface mesh. Keeping the
file-IO boundary outside the advisor:

* matches the A4/A5/A7 sibling pattern (pure dict in → dataclass report
  out, no runtime CFD-utility dependency)
* makes the advisor unit-testable without OpenFOAM/trimesh installed in CI
* lets the caller decide which on-disk form to authoritatively parse
  (case-local `system/snappyHexMeshDict` vs in-memory template)

References:

- V52 in ``cross_cuts/v_series_2026-05-09_case_012_append.md``
  (case_012 v1 typo-class sediment)
- V86 in ``methodology/industrial_case_solver_findings.md``
  (case_011 v1 features-list orphan sediment)
- V99 + V100 in ``docs/openfoam_corpus/industrial_solver_findings_v_series.md``
  (case_003 v2 STL/dict cross-consistency + API type-guard sediments)
- Draft patch ``.planning/patches/draft_a8_shm_dict_validator_2026-05-09.md``
- Parent sub-DECs: V61-198-sub-A8 (2026-05-14, V52+V86) ·
  V61-198-sub-A8-widening-V99-V100 (2026-05-14, V99+V100)
- Sibling validator pattern: ``face_orientation_advisor.py`` (A4),
  ``inlet_outlet_validator.py`` (A5)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# Canonical key vocabulary worth fuzzy-matching against. Each entry is a
# (canonical, parent_block) pair so a typo can be rejected with both the
# correct spelling AND the dict path it belongs in. Drawn from V52
# evidence + the surrounding addLayersControls / castellatedMeshControls /
# snapControls blocks of OpenFOAM-ESI 2312 ``snappyHexMeshDict``.
CANONICAL_KEYS: tuple[tuple[str, str], ...] = (
    ("minMedialAxisAngle", "addLayersControls"),
    ("nFeatureSnapIter", "snapControls"),
    ("implicitFeatureSnap", "snapControls"),
    ("explicitFeatureSnap", "snapControls"),
    ("multiRegionFeatureSnap", "snapControls"),
    ("resolveFeatureAngle", "castellatedMeshControls"),
    ("nCellsBetweenLevels", "castellatedMeshControls"),
    ("maxNonOrtho", "meshQualityControls"),
    ("maxBoundarySkewness", "meshQualityControls"),
    ("maxInternalSkewness", "meshQualityControls"),
    ("nGrow", "addLayersControls"),
    ("featureAngle", "addLayersControls"),
    ("expansionRatio", "addLayersControls"),
    ("finalLayerThickness", "addLayersControls"),
    ("minThickness", "addLayersControls"),
    ("nLayerIter", "addLayersControls"),
    ("nRelaxIter", "addLayersControls"),
)

_LEVENSHTEIN_MAX: int = 2
"""Fuzzy-match ceiling for typo suggestion (V52 was distance 1)."""

# V99 — patchInfo.type values that mathematically demand a single-normal
# (planar / colinear) source surface. STL-driven refinementSurfaces
# carrying any of these types must have all face normals colinear within
# ``_COLINEAR_DEVIATION_MAX``; otherwise sHM will concatenate multiple
# cut sides into the named patch and checkMesh will reject the mesh.
_CONSTRAINED_PATCH_TYPES: frozenset[str] = frozenset(
    {"symmetryPlane", "wedge", "empty", "cyclic", "cyclicAMI"}
)

_COLINEAR_DEVIATION_MAX: float = 0.05
"""Max ``1 - |dot(ref, n_i)|`` allowed before face normals are flagged
as multi-normal (V99 default: 0.05 ≈ ~18° of orientation slack — loose
enough for tessellation rounding, tight enough to catch case_003's
0.556 deviation)."""


@dataclass(frozen=True)
class ShmFinding:
    """One audit result for one snappyHexMeshDict issue."""

    code: str          # "missing_geometry_ref" | "missing_region_ref" |
    #                    "orphaned_emesh_feature" | "typo_suspicion" |
    #                    "geometry_orphan" | "missing_emesh_file" |
    #                    "multi_normal_constrained_patch"  (V99 widening)
    severity: str      # "warning" | "critical"
    location: str      # dict path, e.g. "castellatedMeshControls.features[2]"
    message: str
    suggestion: str | None = None


@dataclass(frozen=True)
class ShmDictReport:
    """Outcome of :func:`validate_shm_dict`."""

    findings: tuple[ShmFinding, ...]
    geometry_names: tuple[str, ...]
    features_files: tuple[str, ...]

    @property
    def is_clean(self) -> bool:
        """True iff no critical or warning finding was produced."""
        return len(self.findings) == 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


def _levenshtein(a: str, b: str) -> int:
    """Standard iterative Levenshtein distance (no external dep)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]


def _suggest_for_unknown_key(key: str, parent_block: str) -> str | None:
    """Return canonical suggestion if a known key is within edit distance."""
    best: tuple[int, str] | None = None
    for canonical, _block in CANONICAL_KEYS:
        if canonical == key:
            return None  # exact match — not a typo
        d = _levenshtein(key, canonical)
        if d <= _LEVENSHTEIN_MAX and (best is None or d < best[0]):
            best = (d, canonical)
    return best[1] if best is not None else None


def _max_normal_deviation(
    normals: list[tuple[float, float, float]] | tuple[tuple[float, float, float], ...],
) -> float | None:
    """Max ``1 - |dot(ref, n_i)|`` across L2-normalized face normals.

    Returns ``None`` if fewer than two non-zero-length normals are
    present (a single face / empty list is trivially colinear). The
    reference direction is the first non-zero unit vector; ``abs()`` on
    the dot product accepts opposite-pointing normals on the same plane
    as planar (sHM-emitted symmetryPlane patches usually agree in sign,
    but a closed-shell STL can mix orientations).
    """
    unit: list[tuple[float, float, float]] = []
    for nx, ny, nz in normals:
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length == 0.0:
            continue
        unit.append((nx / length, ny / length, nz / length))
    if len(unit) < 2:
        return None
    rx, ry, rz = unit[0]
    max_dev = 0.0
    for ux, uy, uz in unit[1:]:
        dot = abs(rx * ux + ry * uy + rz * uz)
        dev = 1.0 - dot
        if dev > max_dev:
            max_dev = dev
    return max_dev


def _suggestion_for_constrained_patch(patch_type: str, surf_name: str) -> str:
    """Build the V99 downgrade suggestion text per declared patchInfo.type."""
    if patch_type == "symmetryPlane":
        return (
            f"downgrade refinementSurfaces.{surf_name}.patchInfo.type to "
            "`patch` and use `slip` on 0/U (slip preserves zero-normal-flux "
            "semantics without the symmetryPlane planarity assertion), OR "
            "re-author the STL as a single planar facet group, OR declare "
            "the symmetry plane as a face of the blockMeshDict bg block "
            "(named-patch path) instead of an STL refinementSurface"
        )
    if patch_type in {"wedge", "empty"}:
        return (
            f"ensure {surf_name}.stl is a single planar face matching the "
            f"`{patch_type}` constraint, OR declare the patch via "
            "blockMeshDict bg-block named-patch path instead of an STL "
            "refinementSurface"
        )
    # cyclic / cyclicAMI
    return (
        f"ensure {surf_name}.stl resolves to a single-normal patch; cyclic "
        "pairs additionally require both halves to share identical normals "
        "and matched face counts — consider blockMeshDict cyclic declaration"
    )


def _walk_dict_keys(node: Any, path: str, out: list[tuple[str, str, str]]) -> None:
    """Recursively collect (key, parent_block, full_path) triples.

    parent_block is the dict path's last segment (e.g. "addLayersControls"),
    used to disambiguate typo suggestions to the correct enclosing block.
    """
    if not isinstance(node, dict):
        return
    parent_block = path.rsplit(".", 1)[-1] if path else ""
    for k, v in node.items():
        full_path = f"{path}.{k}" if path else k
        out.append((str(k), parent_block, full_path))
        _walk_dict_keys(v, full_path, out)


def validate_shm_dict(
    parsed_dict: dict[str, Any],
    *,
    available_emeshes: frozenset[str] | set[str] | None = None,
    stl_face_normals: dict[str, list[tuple[float, float, float]]]
    | dict[str, tuple[tuple[float, float, float], ...]]
    | None = None,
) -> ShmDictReport:
    """Audit a parsed snappyHexMeshDict against V52/V86/V99/V100 failure modes.

    Expected ``parsed_dict`` shape (subset; only fields read here are
    documented):

    .. code-block:: yaml

       geometry:
         region_hot_fluid: { type: triSurfaceMesh, file: "region_hot_fluid.stl" }
         region_solid:     { type: triSurfaceMesh, file: "region_solid.stl" }
       castellatedMeshControls:
         features:
           - { file: "region_hot_fluid.eMesh", level: 2 }
           - { file: "region_solid.eMesh",     level: 3 }
         refinementSurfaces:
           region_hot_fluid: { level: [2, 2] }
           symmetry_plane:   { level: [1, 1], patchInfo: { type: symmetryPlane } }
         refinementRegions:
           region_solid: { mode: inside, levels: ((1e15 3)) }
         minMedianAxisAngle: 90    # V52 typo — should be minMedialAxisAngle
       addLayersControls:
         minMedialAxisAngle: 90
         ...

    Detection logic:

    (a) ``castellatedMeshControls.features[*].file`` — if
        ``available_emeshes`` is supplied (non-None) and a file string is
        not in the set, emit ``missing_emesh_file`` critical. If
        ``features`` is an empty list AND ``available_emeshes`` is non-
        empty, emit ``orphaned_emesh_feature`` critical (V86 root).

    (b) ``castellatedMeshControls.refinementSurfaces`` keys — each must
        appear in ``geometry``. Missing → ``missing_geometry_ref``
        critical. (Inverse: a geometry key with no refinementSurfaces
        AND no refinementRegions reference → ``geometry_orphan``
        warning.)

    (c) ``castellatedMeshControls.refinementRegions`` keys — each must
        appear in ``geometry``. Missing → ``missing_region_ref`` critical.

    (d) Any key under top-level blocks (or nested blocks) that fuzzy-
        matches a CANONICAL key with edit distance ≤ 2 but is NOT itself
        canonical → ``typo_suspicion`` warning with suggestion.

    (e) **V99 widening** — when ``stl_face_normals`` is supplied (non-
        None), for each refinementSurfaces entry whose
        ``patchInfo.type`` is in ``_CONSTRAINED_PATCH_TYPES``
        (``symmetryPlane`` / ``wedge`` / ``empty`` / ``cyclic`` /
        ``cyclicAMI``), verify the face normals supplied for that patch
        name are colinear within ``_COLINEAR_DEVIATION_MAX``. Multi-
        normal source STLs on constrained-patch types produce
        ``multi_normal_constrained_patch`` critical findings with a
        downgrade-and-slip suggestion (per case_003 v2 workaround).
        Patches without a corresponding normals entry are silently
        skipped — caller decides what they can measure.

    (f) **V100 widening** — entry-point ``isinstance(parsed_dict, dict)``
        type-guard. Non-dict input raises ``TypeError`` with the actual
        type name plus a recommended caller-side helper invocation
        (``PyFoam.RunDictionary.ParsedParameterFile`` or
        ``foamDictionary``) instead of the opaque
        ``'str' object has no attribute 'get'`` AttributeError that
        previously surfaced deep in ``_walk_dict_keys``.

    Missing top-level blocks are silently skipped — the dict may be
    sliced (e.g. only ``geometry`` and ``castellatedMeshControls``
    present in a partial template).

    Raises:
        TypeError: when ``parsed_dict`` is not a ``dict`` (V100 widening).
    """
    # --- Path (f): V100 entry-point type-guard -------------------------
    if not isinstance(parsed_dict, dict):
        raise TypeError(
            "validate_shm_dict expects a parsed dict[str, Any]; got "
            f"{type(parsed_dict).__name__}. Pre-parse OpenFOAM dict files "
            "with `PyFoam.RunDictionary.ParsedParameterFile(<path>)"
            ".getValueDict()` or `foamDictionary -value -entry ROOT "
            "<path>` and pass the resulting dict in. The advisor is a "
            "pure dict consumer by design (see module docstring) and "
            "does not do file IO."
        )

    findings: list[ShmFinding] = []
    geometry = parsed_dict.get("geometry") or {}
    geometry_names = tuple(geometry.keys()) if isinstance(geometry, dict) else ()

    cmc = parsed_dict.get("castellatedMeshControls") or {}
    if not isinstance(cmc, dict):
        cmc = {}

    # --- Path (a): features list ---------------------------------------
    features_node = cmc.get("features", None)
    features_files: list[str] = []
    if isinstance(features_node, list):
        for idx, feat in enumerate(features_node):
            if not isinstance(feat, dict):
                continue
            fname = feat.get("file")
            if isinstance(fname, str):
                features_files.append(fname)
                if available_emeshes is not None and fname not in available_emeshes:
                    findings.append(
                        ShmFinding(
                            code="missing_emesh_file",
                            severity="critical",
                            location=f"castellatedMeshControls.features[{idx}].file",
                            message=(
                                f"features list references '{fname}' but the file "
                                "is not present in the case's triSurface/.eMesh set"
                            ),
                            suggestion=(
                                f"either generate {fname} via surfaceFeatureExtract or "
                                "remove the entry"
                            ),
                        )
                    )
        # V86 root: features list is empty AND .eMesh files exist on disk.
        if (
            len(features_node) == 0
            and available_emeshes is not None
            and len(available_emeshes) > 0
        ):
            findings.append(
                ShmFinding(
                    code="orphaned_emesh_feature",
                    severity="critical",
                    location="castellatedMeshControls.features",
                    message=(
                        "features () is an empty list but "
                        f"{sorted(available_emeshes)} .eMesh file(s) exist in "
                        "constant/triSurface — surfaceFeatureExtract output is "
                        "orphaned (V86 case_011 failure mode); explicit/multi"
                        "RegionFeatureSnap will have nothing to act on"
                    ),
                    suggestion=(
                        "wire each .eMesh into features list, e.g. "
                        "{ file \"region_hot_fluid.eMesh\"; level 2; }"
                    ),
                )
            )

    # --- Path (b): refinementSurfaces references geometry --------------
    rs = cmc.get("refinementSurfaces") or {}
    if isinstance(rs, dict):
        for surf_name in rs.keys():
            if surf_name not in geometry_names:
                findings.append(
                    ShmFinding(
                        code="missing_geometry_ref",
                        severity="critical",
                        location=f"castellatedMeshControls.refinementSurfaces.{surf_name}",
                        message=(
                            f"refinementSurfaces entry '{surf_name}' has no "
                            "matching geometry{} entry"
                        ),
                        suggestion=(
                            f"add geometry.{surf_name} block OR remove the "
                            "refinementSurfaces entry"
                        ),
                    )
                )

    # --- Path (c): refinementRegions references geometry ---------------
    rr = cmc.get("refinementRegions") or {}
    if isinstance(rr, dict):
        for reg_name in rr.keys():
            if reg_name not in geometry_names:
                findings.append(
                    ShmFinding(
                        code="missing_region_ref",
                        severity="critical",
                        location=f"castellatedMeshControls.refinementRegions.{reg_name}",
                        message=(
                            f"refinementRegions entry '{reg_name}' has no "
                            "matching geometry{} entry"
                        ),
                        suggestion=(
                            f"add geometry.{reg_name} block OR remove the "
                            "refinementRegions entry"
                        ),
                    )
                )

    # --- Path (b'): geometry orphan (no refinement reference at all) ---
    refed = set()
    if isinstance(rs, dict):
        refed.update(rs.keys())
    if isinstance(rr, dict):
        refed.update(rr.keys())
    for gname in geometry_names:
        if gname not in refed:
            findings.append(
                ShmFinding(
                    code="geometry_orphan",
                    severity="warning",
                    location=f"geometry.{gname}",
                    message=(
                        f"geometry '{gname}' is not referenced by "
                        "refinementSurfaces or refinementRegions"
                    ),
                    suggestion=None,
                )
            )

    # --- Path (e): V99 constrained-patch STL face-normal cross-check ---
    # Only runs when the caller supplied STL face normals. Walks
    # refinementSurfaces, reads patchInfo.type, and (for constrained
    # types) verifies the named patch's STL normals are colinear within
    # tolerance. The advisor never reads the STL itself — caller is
    # responsible for the trimesh / numpy-stl extraction (per A4 sibling
    # pattern; keeps A8 OpenFOAM-utility-free + unit-testable in CI).
    if stl_face_normals is not None and isinstance(rs, dict):
        for surf_name, surf_cfg in rs.items():
            if not isinstance(surf_cfg, dict):
                continue
            patch_info = surf_cfg.get("patchInfo") or {}
            if not isinstance(patch_info, dict):
                continue
            patch_type = patch_info.get("type")
            if not isinstance(patch_type, str):
                continue
            if patch_type not in _CONSTRAINED_PATCH_TYPES:
                continue
            normals = stl_face_normals.get(surf_name)
            if normals is None:
                continue  # caller has no measurement for this patch
            max_dev = _max_normal_deviation(normals)
            if max_dev is None:
                continue  # single-face / empty list — trivially planar
            if max_dev <= _COLINEAR_DEVIATION_MAX:
                continue  # within tolerance — V99 not triggered
            findings.append(
                ShmFinding(
                    code="multi_normal_constrained_patch",
                    severity="critical",
                    location=(
                        f"castellatedMeshControls.refinementSurfaces."
                        f"{surf_name}.patchInfo.type"
                    ),
                    message=(
                        f"refinementSurfaces.{surf_name} declares "
                        f"patchInfo.type `{patch_type}` (single-normal "
                        "constraint) but the supplied STL face normals "
                        f"span 1-|dot(ref, n)| = {max_dev:.3f}, exceeding "
                        f"the {_COLINEAR_DEVIATION_MAX:.2f} colinear "
                        "tolerance. sHM will cut multiple sides into this "
                        "patch and checkMesh will reject the mesh with a "
                        "`non-planar` error (V99 case_003 v2 failure mode)"
                    ),
                    suggestion=_suggestion_for_constrained_patch(
                        patch_type, surf_name
                    ),
                )
            )

    # --- Path (d): typo suspicion via fuzzy match ----------------------
    walked: list[tuple[str, str, str]] = []
    _walk_dict_keys(parsed_dict, "", walked)
    canonical_set = {k for k, _ in CANONICAL_KEYS}
    seen_typo_paths: set[str] = set()
    for key, parent_block, full_path in walked:
        if key in canonical_set:
            continue  # exact canonical key — skip
        suggestion = _suggest_for_unknown_key(key, parent_block)
        if suggestion is None:
            continue
        if full_path in seen_typo_paths:
            continue
        seen_typo_paths.add(full_path)
        findings.append(
            ShmFinding(
                code="typo_suspicion",
                severity="warning",
                location=full_path,
                message=(
                    f"key '{key}' resembles canonical '{suggestion}' "
                    f"(edit distance ≤ {_LEVENSHTEIN_MAX}) — likely typo"
                ),
                suggestion=suggestion,
            )
        )

    return ShmDictReport(
        findings=tuple(findings),
        geometry_names=geometry_names,
        features_files=tuple(features_files),
    )
