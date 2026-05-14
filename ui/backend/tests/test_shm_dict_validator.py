"""Tests for ``geometry_ingest.shm_dict_validator`` (A8 advisor).

Coverage (≥9 tests, mirroring A4/A5 layout):

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
"""
from __future__ import annotations

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
