"""Tests for ``geometry_ingest.shm_dict_validator`` (A8 advisor).

Coverage (≥13 tests, mirroring A4/A5 layout · widened 2026-05-14 by
DEC-V61-198-sub-A8-widening-V99-V100 to add V99 + V100 paths):

V52 + V86 regression pins:
  1. V52 typo regression — case_012 ``minMedianAxisAngle`` typo flagged
     with ``minMedialAxisAngle`` suggestion + edit-distance ≤ 2.
  2. V86 features-list orphan regression — case_011 empty features ()
     with present .eMesh files flagged as critical.

Path (a) features list (V86 family):
  3. features list with all referenced .eMesh present → no
     ``missing_emesh_file`` finding.
  4. features list referencing an .eMesh not in available_emeshes
     → critical ``missing_emesh_file``.

Path (b) refinementSurfaces ↔ geometry:
  5. refinementSurfaces entry without matching geometry → critical
     ``missing_geometry_ref``.

Path (c) refinementRegions ↔ geometry:
  6. refinementRegions entry without matching geometry → critical
     ``missing_region_ref``.

Path (d) typo suspicion fuzzy match:
  7. Canonical-only dict produces NO typo_suspicion findings (negative).

Block / sliced-input handling:
  8. Missing castellatedMeshControls block silently skipped (sliced
     dict still validates without raising).
  9. Geometry referenced by neither refinementSurfaces nor
     refinementRegions → ``geometry_orphan`` warning.

Path (e) V99 widening — STL face-normal vs patchInfo.type cross-check:
 10. V99 regression — case_003 v2 symmetry_plane with 5-side closed-box
     STL (multi-normal) + patchInfo.type=symmetryPlane → critical
     ``multi_normal_constrained_patch`` with downgrade-to-`patch`-+-slip
     suggestion.
 11. V99 passing — single-normal STL + patchInfo.type=symmetryPlane →
     no V99 finding (legitimate planar symmetry plane).
 12. V99 not-applicable — multi-normal STL + patchInfo.type=patch →
     no V99 finding (unconstrained patch type, multi-normal is fine).

Path (f) V100 widening — entry-point type-guard:
 13. V100 regression — passing a str (path-string-as-input) raises
     ``TypeError`` with actionable message that names the offending
     type AND recommends the PyFoam / foamDictionary pre-parse helper.
"""
from __future__ import annotations

import pytest

from ui.backend.services.geometry_ingest.shm_dict_validator import (
    CANONICAL_KEYS,
    ShmDictReport,
    ShmFinding,
    validate_shm_dict,
)


def test_v52_typo_regression_case_012():
    # case_012 v1: addLayersControls.minMedianAxisAngle 90 — typo of
    # canonical minMedialAxisAngle. sHM raises FOAM FATAL IO ERROR
    # after a multi-minute mesh run; A8 must catch it pre-flight.
    parsed = {
        "addLayersControls": {
            "minMedianAxisAngle": 90,
            "expansionRatio": 1.2,
            "minThickness": 0.1,
        }
    }
    report = validate_shm_dict(parsed)
    assert isinstance(report, ShmDictReport)
    typo_findings = [f for f in report.findings if f.code == "typo_suspicion"]
    assert len(typo_findings) == 1, report.findings
    f = typo_findings[0]
    assert f.severity == "warning"
    assert f.location == "addLayersControls.minMedianAxisAngle"
    assert f.suggestion == "minMedialAxisAngle"
    assert "minMedialAxisAngle" in f.message


def test_v86_features_list_orphan_regression_case_011():
    # case_011 v1: surfaceFeatureExtract wrote 3 .eMesh files
    # (region_hot_fluid / region_cold_fluid / region_solid) but
    # snappyHexMeshDict.castellatedMeshControls.features () was empty,
    # so multiRegionFeatureSnap had nothing to act on.
    parsed = {
        "geometry": {
            "region_hot_fluid": {"type": "triSurfaceMesh", "file": "region_hot_fluid.stl"},
            "region_cold_fluid": {"type": "triSurfaceMesh", "file": "region_cold_fluid.stl"},
            "region_solid": {"type": "triSurfaceMesh", "file": "region_solid.stl"},
        },
        "castellatedMeshControls": {
            "features": [],
            "refinementSurfaces": {
                "region_hot_fluid": {"level": [2, 2]},
                "region_cold_fluid": {"level": [2, 2]},
                "region_solid": {"level": [3, 3]},
            },
        },
    }
    available = {
        "region_hot_fluid.eMesh",
        "region_cold_fluid.eMesh",
        "region_solid.eMesh",
    }
    report = validate_shm_dict(parsed, available_emeshes=available)
    orphan = [f for f in report.findings if f.code == "orphaned_emesh_feature"]
    assert len(orphan) == 1
    assert orphan[0].severity == "critical"
    assert "region_hot_fluid.eMesh" in orphan[0].message
    assert orphan[0].suggestion is not None
    # geometry_names + features_files should accurately reflect input
    assert set(report.geometry_names) == {
        "region_hot_fluid",
        "region_cold_fluid",
        "region_solid",
    }
    assert report.features_files == ()


def test_features_list_all_emeshes_present_no_missing_finding():
    parsed = {
        "geometry": {
            "region_hot_fluid": {"type": "triSurfaceMesh"},
            "region_solid": {"type": "triSurfaceMesh"},
        },
        "castellatedMeshControls": {
            "features": [
                {"file": "region_hot_fluid.eMesh", "level": 2},
                {"file": "region_solid.eMesh", "level": 3},
            ],
            "refinementSurfaces": {
                "region_hot_fluid": {"level": [2, 2]},
                "region_solid": {"level": [3, 3]},
            },
        },
    }
    available = {"region_hot_fluid.eMesh", "region_solid.eMesh"}
    report = validate_shm_dict(parsed, available_emeshes=available)
    assert not any(f.code == "missing_emesh_file" for f in report.findings)
    assert not any(f.code == "orphaned_emesh_feature" for f in report.findings)
    assert set(report.features_files) == {
        "region_hot_fluid.eMesh",
        "region_solid.eMesh",
    }


def test_features_list_references_missing_emesh_critical():
    parsed = {
        "geometry": {"region_hot_fluid": {"type": "triSurfaceMesh"}},
        "castellatedMeshControls": {
            "features": [
                {"file": "region_hot_fluid.eMesh", "level": 2},
                {"file": "region_TYPO.eMesh", "level": 2},
            ],
            "refinementSurfaces": {"region_hot_fluid": {"level": [2, 2]}},
        },
    }
    available = {"region_hot_fluid.eMesh"}
    report = validate_shm_dict(parsed, available_emeshes=available)
    missing = [f for f in report.findings if f.code == "missing_emesh_file"]
    assert len(missing) == 1
    assert missing[0].severity == "critical"
    assert "region_TYPO.eMesh" in missing[0].message
    assert missing[0].location == "castellatedMeshControls.features[1].file"


def test_refinement_surfaces_missing_geometry_critical():
    parsed = {
        "geometry": {"region_hot_fluid": {"type": "triSurfaceMesh"}},
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "region_hot_fluid": {"level": [2, 2]},
                "ghost_surface_unknown": {"level": [3, 3]},
            },
        },
    }
    report = validate_shm_dict(parsed)
    missing = [f for f in report.findings if f.code == "missing_geometry_ref"]
    assert len(missing) == 1
    assert missing[0].severity == "critical"
    assert "ghost_surface_unknown" in missing[0].message
    assert missing[0].location.endswith("ghost_surface_unknown")


def test_refinement_regions_missing_geometry_critical():
    parsed = {
        "geometry": {"region_hot_fluid": {"type": "triSurfaceMesh"}},
        "castellatedMeshControls": {
            "refinementRegions": {
                "region_hot_fluid": {"mode": "inside", "levels": "((1e15 3))"},
                "phantom_region": {"mode": "inside", "levels": "((1e15 2))"},
            },
        },
    }
    report = validate_shm_dict(parsed)
    missing = [f for f in report.findings if f.code == "missing_region_ref"]
    assert len(missing) == 1
    assert missing[0].severity == "critical"
    assert "phantom_region" in missing[0].message


def test_canonical_only_dict_produces_no_typo_suspicion():
    # All keys here are exact canonicals → walker should NOT emit any
    # typo_suspicion finding. Negative test guarding fuzzy-match
    # false-positives against the canonical vocabulary.
    parsed = {
        "addLayersControls": {
            "minMedialAxisAngle": 90,
            "expansionRatio": 1.2,
            "minThickness": 0.1,
            "nGrow": 0,
            "featureAngle": 30,
        },
        "snapControls": {
            "nFeatureSnapIter": 10,
            "implicitFeatureSnap": True,
            "explicitFeatureSnap": False,
            "multiRegionFeatureSnap": True,
        },
    }
    report = validate_shm_dict(parsed)
    typo_findings = [f for f in report.findings if f.code == "typo_suspicion"]
    assert typo_findings == []
    # Sanity: every canonical key listed is reachable from the walker
    canonical_names = {k for k, _ in CANONICAL_KEYS}
    assert "minMedialAxisAngle" in canonical_names


def test_sliced_dict_missing_top_level_blocks_silently_skipped():
    # The advisor must accept partial dicts (e.g. only addLayersControls
    # present in a sub-template) without raising or false-positively
    # emitting "missing block" findings.
    parsed = {
        "addLayersControls": {"minMedialAxisAngle": 90},
    }
    report = validate_shm_dict(parsed)
    # No castellated block → no features/refinement findings; no
    # geometry block → no geometry-orphan findings. Only path (d) typo
    # walk runs, and the dict here is canonical → clean.
    assert report.is_clean
    assert report.geometry_names == ()
    assert report.features_files == ()


def test_geometry_orphan_warning_when_unreferenced():
    # geometry block declares a name that neither refinementSurfaces
    # nor refinementRegions reference → warning (not critical, since
    # this is dead config not a runtime fault).
    parsed = {
        "geometry": {
            "region_hot_fluid": {"type": "triSurfaceMesh"},
            "dead_orphan_solid": {"type": "triSurfaceMesh"},
        },
        "castellatedMeshControls": {
            "refinementSurfaces": {"region_hot_fluid": {"level": [2, 2]}},
        },
    }
    report = validate_shm_dict(parsed)
    orphans = [f for f in report.findings if f.code == "geometry_orphan"]
    assert len(orphans) == 1
    assert orphans[0].severity == "warning"
    assert orphans[0].location == "geometry.dead_orphan_solid"
    # And conversely, the referenced one should NOT be flagged
    assert not any(
        f.location == "geometry.region_hot_fluid"
        for f in report.findings
        if isinstance(f, ShmFinding)
    )


# ---------------------------------------------------------------------------
# V99 widening (DEC-V61-198-sub-A8-widening-V99-V100, 2026-05-14):
# STL face-normal vs patchInfo.type cross-check.
# ---------------------------------------------------------------------------


def test_v99_regression_case_003_symmetry_plane_multi_normal_critical():
    # case_003 v2 ground truth: source STL symmetry_plane.stl is a
    # closed thin axis-aligned bounding box; sHM captured 5 of 6 sides
    # and concatenated them into the named patch. With
    # patchInfo.type=symmetryPlane the patch normals span 0.556 of
    # unit-vector deviation from the patch mean — checkMesh rejected
    # the otherwise-valid mesh. A8 must flag this pre-mesh.
    parsed = {
        "geometry": {
            "symmetry_plane": {
                "type": "triSurfaceMesh",
                "file": "symmetry_plane.stl",
            },
        },
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "symmetry_plane": {
                    "level": [1, 1],
                    "patchInfo": {"type": "symmetryPlane"},
                },
            },
        },
    }
    # 5 of 6 axis-aligned faces of a closed-box STL (matches the
    # case_003 v2 ground-truth — V99 row in v_series.md L1314).
    stl_normals = {
        "symmetry_plane": [
            (1.0, 0.0, 0.0),
            (-1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, -1.0, 0.0),
            (0.0, 0.0, 1.0),
        ],
    }
    report = validate_shm_dict(parsed, stl_face_normals=stl_normals)
    multi_normal = [
        f for f in report.findings if f.code == "multi_normal_constrained_patch"
    ]
    assert len(multi_normal) == 1, report.findings
    f = multi_normal[0]
    assert f.severity == "critical"
    assert f.location == (
        "castellatedMeshControls.refinementSurfaces."
        "symmetry_plane.patchInfo.type"
    )
    assert "symmetryPlane" in f.message
    assert "non-planar" in f.message  # ties to checkMesh failure mode
    # symmetryPlane-specific suggestion must mention the slip workaround
    # (the actual case_003 v2 fix applied in session 6).
    assert f.suggestion is not None
    assert "patch" in f.suggestion  # downgrade hint
    assert "slip" in f.suggestion


def test_v99_single_normal_symmetry_plane_passes():
    # A legitimate symmetry-plane STL — a single planar quad (4 facets
    # all sharing the same +Y normal, modulo tessellation noise within
    # the 0.05 deviation tolerance). A8 must NOT emit a finding here:
    # symmetryPlane with a single-normal STL is the correct use case.
    parsed = {
        "geometry": {
            "symmetry_plane": {
                "type": "triSurfaceMesh",
                "file": "symmetry_plane.stl",
            },
        },
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "symmetry_plane": {
                    "level": [0, 0],
                    "patchInfo": {"type": "symmetryPlane"},
                },
            },
        },
    }
    # 4 triangular facets, all +Y, with sub-tolerance tessellation
    # perturbation in the third component (1e-3 → deviation ≪ 0.05).
    stl_normals = {
        "symmetry_plane": [
            (0.0, 1.0, 0.0),
            (0.0, 1.0, 0.001),
            (0.0, 1.0, -0.001),
            (0.0, 1.0, 0.0),
        ],
    }
    report = validate_shm_dict(parsed, stl_face_normals=stl_normals)
    assert not any(
        f.code == "multi_normal_constrained_patch" for f in report.findings
    ), report.findings


def test_v99_multi_normal_patch_type_not_constrained_no_finding():
    # Same multi-normal STL as the V99 regression test, but
    # patchInfo.type is the unconstrained `patch` (the actual case_003
    # v2 workaround applied in session 6). A8 must NOT flag this — the
    # `patch` type imposes no normal-uniqueness constraint, so a multi-
    # face STL is perfectly fine.
    parsed = {
        "geometry": {
            "symmetry_plane": {
                "type": "triSurfaceMesh",
                "file": "symmetry_plane.stl",
            },
        },
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "symmetry_plane": {
                    "level": [0, 0],
                    "patchInfo": {"type": "patch"},
                },
            },
        },
    }
    stl_normals = {
        "symmetry_plane": [
            (1.0, 0.0, 0.0),
            (-1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, -1.0, 0.0),
            (0.0, 0.0, 1.0),
        ],
    }
    report = validate_shm_dict(parsed, stl_face_normals=stl_normals)
    assert not any(
        f.code == "multi_normal_constrained_patch" for f in report.findings
    ), report.findings


# ---------------------------------------------------------------------------
# V100 widening (DEC-V61-198-sub-A8-widening-V99-V100, 2026-05-14):
# entry-point type-guard for non-dict input.
# ---------------------------------------------------------------------------


def test_v100_type_guard_str_input_raises_actionable_typeerror():
    # case_003 v2 root cause: engineer passed a path string per the
    # natural "validator on a file path" mental model. Previously this
    # raised an opaque ``AttributeError: 'str' object has no attribute
    # 'get'`` deep in _walk_dict_keys. Now must raise a typed,
    # actionable TypeError at the API boundary that (a) names the
    # offending type, (b) recommends a caller-side pre-parse helper.
    with pytest.raises(TypeError) as exc_info:
        validate_shm_dict("system/snappyHexMeshDict")  # type: ignore[arg-type]
    msg = str(exc_info.value)
    # Must NOT be the opaque AttributeError that used to surface.
    assert "has no attribute 'get'" not in msg
    # Must name the offending type so caller can fix the call site.
    assert "str" in msg
    # Must reference at least one recommended pre-parse helper (per the
    # V100 fix spec: PyFoam OR foamDictionary, advisor doesn't care
    # which the caller picks).
    assert ("PyFoam" in msg) or ("foamDictionary" in msg)
    # Must restate the contract so caller understands why.
    assert "dict" in msg.lower()


# ---------------------------------------------------------------------------
# V99-WIDEN (DEC-V62-A-sub-A8-V99-WIDEN, 2026-05-14):
# native OpenFOAM ``name:`` alias resolution + V100-WIDEN parens-stripping.
# Closes M-STACK-TRACK-1 §8 enhancement #1 (case_011 v5b 6/8 false-positives).
# ---------------------------------------------------------------------------


def test_v99_widening_recognizes_name_alias_form_case_011_v5b():
    # case_011 v5b verbatim shape: geometry keyed by .stl filename + a
    # `name:` alias that is the canonical patch token referenced by
    # refinementSurfaces. Pre-widening this produced 6 false-positives
    # (3 missing_geometry_ref + 3 geometry_orphan). After widening:
    # 0 findings.
    parsed = {
        "geometry": {
            "region_hot_fluid.stl": {
                "type": "triSurfaceMesh",
                "name": "region_hot_fluid",
            },
            "region_cold_fluid.stl": {
                "type": "triSurfaceMesh",
                "name": "region_cold_fluid",
            },
            "region_solid.stl": {
                "type": "triSurfaceMesh",
                "name": "region_solid",
            },
        },
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "region_hot_fluid": {"level": [1, 2]},
                "region_cold_fluid": {"level": [2, 3]},
                "region_solid": {"level": [3, 4]},
            },
            "refinementRegions": {},
        },
    }
    report = validate_shm_dict(parsed)
    assert not any(
        f.code == "missing_geometry_ref" for f in report.findings
    ), report.findings
    assert not any(
        f.code == "geometry_orphan" for f in report.findings
    ), report.findings
    # geometry_names tuple is preserved as literal keys for backward compat.
    assert set(report.geometry_names) == {
        "region_hot_fluid.stl",
        "region_cold_fluid.stl",
        "region_solid.stl",
    }


def test_v99_widening_strips_parentheses_v100_widen():
    # V100-WIDEN: foamDictionary -value -entry may wrap single-word
    # tokens in `(...)` (wordList round-trip). `name (region_hot_fluid)`
    # must resolve to the same canonical identifier as
    # `name region_hot_fluid` so refinementSurfaces references match.
    parsed = {
        "geometry": {
            "region_hot_fluid.stl": {
                "type": "triSurfaceMesh",
                "name": "(region_hot_fluid)",
            },
        },
        "castellatedMeshControls": {
            "refinementSurfaces": {"region_hot_fluid": {"level": [1, 2]}},
        },
    }
    report = validate_shm_dict(parsed)
    assert not any(
        f.code == "missing_geometry_ref" for f in report.findings
    ), report.findings
    assert not any(
        f.code == "geometry_orphan" for f in report.findings
    ), report.findings


def test_v99_widening_backward_compat_literal_form():
    # The pre-V99-WIDEN literal-key form (no `name:` attribute) must
    # continue to work unchanged — V52/V86 regression suite and the
    # majority of internally authored fixtures use this shape.
    parsed = {
        "geometry": {
            "region_hot_fluid": {"type": "triSurfaceMesh"},
            "ghost_surface_unknown_in_geometry": {"type": "triSurfaceMesh"},
        },
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "region_hot_fluid": {"level": [2, 2]},
                "ghost_surface_unknown_in_refsurf": {"level": [3, 3]},
            },
        },
    }
    report = validate_shm_dict(parsed)
    # ghost_surface_unknown_in_refsurf has no matching geometry entry →
    # still emits missing_geometry_ref (literal-form check intact).
    missing = [f for f in report.findings if f.code == "missing_geometry_ref"]
    assert len(missing) == 1
    assert "ghost_surface_unknown_in_refsurf" in missing[0].message
    # ghost_surface_unknown_in_geometry is unreferenced → still emits
    # geometry_orphan (Path b' literal-form behavior intact).
    orphans = [f for f in report.findings if f.code == "geometry_orphan"]
    assert len(orphans) == 1
    assert orphans[0].location == "geometry.ghost_surface_unknown_in_geometry"


def test_v99_widening_mixed_form_in_same_dict():
    # Heterogeneous dict: one geometry entry uses alias form, one uses
    # literal form. Both flavours must resolve correctly within the same
    # validation pass (no all-or-nothing branch).
    parsed = {
        "geometry": {
            "region_hot_fluid.stl": {
                "type": "triSurfaceMesh",
                "name": "region_hot_fluid",  # alias form
            },
            "region_solid": {"type": "triSurfaceMesh"},  # literal form
        },
        "castellatedMeshControls": {
            "refinementSurfaces": {
                "region_hot_fluid": {"level": [1, 2]},  # matches alias
                "region_solid": {"level": [3, 4]},  # matches literal
            },
        },
    }
    report = validate_shm_dict(parsed)
    assert not any(
        f.code == "missing_geometry_ref" for f in report.findings
    ), report.findings
    assert not any(
        f.code == "geometry_orphan" for f in report.findings
    ), report.findings


def test_v99_widening_does_not_consume_unrelated_name_keys():
    # `name:` keys outside the geometry block (e.g. inside patchInfo,
    # inside thin_wall input shapes, inside features entries) must NOT
    # be consumed as geometry aliases. Path (b)/(b')/(c) only inspect
    # geometry.*.name; anything else is left to its own validator.
    parsed = {
        "geometry": {
            "region_hot_fluid.stl": {
                "type": "triSurfaceMesh",
                "name": "region_hot_fluid",
            },
        },
        "castellatedMeshControls": {
            # ghost_via_features should NOT become a valid geometry name
            # just because it appears as a `name` value inside a feature.
            "features": [
                {"file": "region_hot_fluid.eMesh", "level": 2,
                 "name": "ghost_via_features"},
            ],
            "refinementSurfaces": {
                "region_hot_fluid": {
                    "level": [1, 2],
                    "patchInfo": {
                        "type": "patch",
                        # `name` inside patchInfo: must NOT alias geometry.
                        "name": "ghost_via_patchinfo",
                    },
                },
                "ghost_via_features": {"level": [2, 2]},
            },
        },
    }
    report = validate_shm_dict(parsed)
    # ghost_via_features in refinementSurfaces has no matching geometry
    # alias and no literal geometry key → must still emit
    # missing_geometry_ref (proves alias resolution did not bleed into
    # the features/patchInfo `name` keys).
    missing = [f for f in report.findings if f.code == "missing_geometry_ref"]
    assert len(missing) == 1
    assert "ghost_via_features" in missing[0].message
