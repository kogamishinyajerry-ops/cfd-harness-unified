"""Tests for ``ui.backend.services.case_extractors.shm_dict_multi_region``.

Per DEC-V61-217 W3.0.1. All fixtures are synthetic (``tmp_path``); no real
OpenFOAM case directories are required.

Topology resolution (load-bearing, carried from SPEC 2 survey 2026-05-30):
  Real ``chtMultiRegionSimpleFoam`` / ``chtMultiRegionFoam`` cases use ONE master
  ``system/snappyHexMeshDict`` (design fork **a**).  Per-region cellZone tagging
  is done via ``castellatedMeshControls.refinementSurfaces.<name>.{cellZone ...;
  cellZoneInside ...}`` and/or top-level ``locationsInMesh``/``locationInMesh``.
  There is NO per-region ``system/<region>/snappyHexMeshDict`` in any corpus case
  (verified 2026-05-30).  The extractor's locating strategy is master-sHM +
  cellZone-derived, not file-per-region.

  case_002b note: 6 of the 7 regions are extruded (no sHM) → output has 7 keys
  but up to 6 honest ``None`` values.  Fixtures here that demonstrate "7 populated
  snapshots" use a synthetic all-in-one-sHM layout (all 7 cellZone-tagged) to
  separately pin that path.
"""
from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ui.backend.services.case_extractors import extract_shm_dict_multi_region
from ui.backend.services.case_extractors import shm_dict_multi_region
from ui.backend.services.case_extractors.region_properties_reader import (
    RegionPropertiesSnapshot,
)
from ui.backend.services.case_extractors.shm_dict_multi_region import RegionShmSnapshot

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Fixture writers (mirror W3.0 conventions)
# ---------------------------------------------------------------------------

def _write_master_shm(case_dir: Path, body: str) -> None:
    """Write *body* to ``<case_dir>/system/snappyHexMeshDict``."""
    (case_dir / "system").mkdir(exist_ok=True)
    (case_dir / "system" / "snappyHexMeshDict").write_text(body, encoding="utf-8")


def _write_region_properties(case_dir: Path, content: str) -> None:
    """Write *content* to ``<case_dir>/constant/regionProperties``."""
    (case_dir / "constant").mkdir(exist_ok=True)
    (case_dir / "constant" / "regionProperties").write_text(content, encoding="utf-8")


def _make_region_props(fluid_names: str, solid_names: str) -> str:
    """Build a minimal canonical ``regionProperties`` file string."""
    return (
        "FoamFile\n"
        "{\n"
        "    version     2.0;\n"
        "    format      ascii;\n"
        "    class       dictionary;\n"
        '    location    "constant";\n'
        "    object      regionProperties;\n"
        "}\n"
        "regions\n"
        "(\n"
        f"    fluid       ({fluid_names})\n"
        f"    solid       ({solid_names})\n"
        ");\n"
    )


def _make_region_snapshot(
    fluid: tuple[str, ...] | None,
    solid: tuple[str, ...] | None,
) -> RegionPropertiesSnapshot:
    """Helper to build a ``RegionPropertiesSnapshot`` without touching the FS."""
    return RegionPropertiesSnapshot(fluid_regions=fluid, solid_regions=solid)


# ---------------------------------------------------------------------------
# Shared SHM bodies for multi-fixture reuse
# ---------------------------------------------------------------------------

_FOAMFILE_HEADER = (
    "FoamFile\n"
    "{\n"
    "    version 2.0;\n"
    "    format ascii;\n"
    "    class dictionary;\n"
    "    object snappyHexMeshDict;\n"
    "}\n"
    "castellatedMesh true;\n"
    "snap true;\n"
    "addLayers false;\n\n"
)


def _make_7region_shm_locationsInMesh() -> str:
    """Master sHM using V90 ``locationsInMesh`` for 7 cellZone-tagged regions.

    Topology: synthetic all-in-one-sHM (case_011/015 style) with 7 surfaces,
    each declaring ``cellZone <name>; cellZoneInside insidePoint``.  This is
    the fixture for "7 populated snapshots" — distinct from the real case_002b
    shape where 6 regions are extruded.
    """
    return (
        _FOAMFILE_HEADER
        + "geometry\n"
        + "{\n"
        + "    region_fluid.stl    { type triSurfaceMesh; name region_fluid; }\n"
        + "    Outer_Surf.stl      { type triSurfaceMesh; name Outer_Surf; }\n"
        + "    Inner_Surf.stl      { type triSurfaceMesh; name Inner_Surf; }\n"
        + "    Plane_Outer_Surf.stl { type triSurfaceMesh; name Plane_Outer_Surf; }\n"
        + "    firewall.stl        { type triSurfaceMesh; name firewall; }\n"
        + "    frames_beams.stl    { type triSurfaceMesh; name frames_beams; }\n"
        + "    APU_door.stl        { type triSurfaceMesh; name APU_door; }\n"
        + "}\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationsInMesh\n"
        + "    (\n"
        + "        ((0.50 0.40 0.30) region_fluid)\n"
        + "        ((0.50 0.40 0.62) Outer_Surf)\n"
        + "        ((0.50 0.40 0.10) Inner_Surf)\n"
        + "        ((0.50 0.78 0.30) Plane_Outer_Surf)\n"
        + "        ((0.12 0.40 0.30) firewall)\n"
        + "        ((0.88 0.40 0.30) frames_beams)\n"
        + "        ((0.50 0.05 0.30) APU_door)\n"
        + "    );\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        region_fluid     { level (1 2); cellZone region_fluid;     cellZoneInside inside;      }\n"
        + "        Outer_Surf       { level (1 2); cellZone Outer_Surf;       cellZoneInside insidePoint; insidePoint (0.50 0.40 0.62); }\n"
        + "        Inner_Surf       { level (1 2); cellZone Inner_Surf;       cellZoneInside insidePoint; insidePoint (0.50 0.40 0.10); }\n"
        + "        Plane_Outer_Surf { level (1 2); cellZone Plane_Outer_Surf; cellZoneInside insidePoint; insidePoint (0.50 0.78 0.30); }\n"
        + "        firewall         { level (1 2); cellZone firewall;         cellZoneInside insidePoint; insidePoint (0.12 0.40 0.30); }\n"
        + "        frames_beams     { level (1 2); cellZone frames_beams;     cellZoneInside insidePoint; insidePoint (0.88 0.40 0.30); }\n"
        + "        APU_door         { level (1 2); cellZone APU_door;         cellZoneInside insidePoint; insidePoint (0.50 0.05 0.30); }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
        + "addLayersControls { relativeSizes true; }\n"
    )


def _make_3region_shm_legacy() -> str:
    """Master sHM using legacy ``locationInMesh`` for 3 regions (case_011 shape).

    Each surface declares ``cellZoneInside insidePoint`` + ``insidePoint ( x y z )``.
    """
    return (
        _FOAMFILE_HEADER
        + "geometry\n"
        + "{\n"
        + "    hot_fluid.stl  { type triSurfaceMesh; name region_hot_fluid; }\n"
        + "    cold_fluid.stl { type triSurfaceMesh; name region_cold_fluid; }\n"
        + "    solid.stl      { type triSurfaceMesh; name region_solid; }\n"
        + "}\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.09 0.06 0.04);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        region_hot_fluid\n"
        + "        {\n"
        + "            level (1 2);\n"
        + "            cellZone region_hot_fluid;\n"
        + "            cellZoneInside insidePoint;\n"
        + "            insidePoint (0.090 0.05825 0.045);\n"
        + "            patchInfo { type wall; }\n"
        + "        }\n"
        + "        region_cold_fluid\n"
        + "        {\n"
        + "            level (1 2);\n"
        + "            cellZone region_cold_fluid;\n"
        + "            cellZoneInside insidePoint;\n"
        + "            insidePoint (0.09175 0.060 0.027);\n"
        + "            patchInfo { type wall; }\n"
        + "        }\n"
        + "        region_solid\n"
        + "        {\n"
        + "            level (1 2);\n"
        + "            cellZone region_solid;\n"
        + "            cellZoneInside insidePoint;\n"
        + "            insidePoint (0.090 0.060 0.0191);\n"
        + "        }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
        + "addLayersControls { relativeSizes true; }\n"
    )


# ---------------------------------------------------------------------------
# A. Happy path — synthetic 7-region all-in-one-sHM (case_002b cellZone shape)
# ---------------------------------------------------------------------------

def test_synthetic_all_in_one_shm_7_populated_snapshots(tmp_path: Path) -> None:
    """A. Synthetic all-in-one-sHM with 7 cellZone-tagged regions yields 7 keys.

    NOTE: this is a SYNTHETIC all-in-one-sHM layout (NOT the real case_002b
    shape — real case_002b extrudes 6/7 solids and yields 6 honest None; see
    ``test_case_002b_honest_extruded_solids_yield_none``, the canonical
    acceptance gate). This fixture separately pins the all-7-cellZone-tagged
    path so the charter's "7 region-keyed snapshots" wording is exercised where
    every region really is sHM-tagged.
    """
    _write_master_shm(tmp_path, _make_7region_shm_locationsInMesh())
    snap = _make_region_snapshot(
        fluid=("region_fluid",),
        solid=(
            "Outer_Surf",
            "Inner_Surf",
            "Plane_Outer_Surf",
            "firewall",
            "frames_beams",
            "APU_door",
        ),
    )
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert len(result) == 7
    all_keys = set(result.keys())
    assert all_keys == {
        "region_fluid",
        "Outer_Surf",
        "Inner_Surf",
        "Plane_Outer_Surf",
        "firewall",
        "frames_beams",
        "APU_door",
    }
    for name, region_snap in result.items():
        assert region_snap is not None, f"region {name!r} unexpectedly None"
        assert isinstance(region_snap, RegionShmSnapshot)
        assert region_snap.surface_present, f"region {name!r}: surface_present is False"


def test_case_002b_honest_extruded_solids_yield_none(tmp_path: Path) -> None:
    """A (honest case_002b shape). Master sHM covers only fluid; 6 extruded solids
    have no sHM entry.

    DEC-V61-218 lesson: extruded regions must produce honest ``None``, NOT
    fabricated snapshots.  Pin "7 keys, 1 populated + 6 honest None".
    """
    # Master sHM that only mentions the fluid region
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry\n"
        + "{\n"
        + "    region_bay_air.stl { type triSurfaceMesh; name region_bay_air; }\n"
        + "}\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.4 0.3);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        region_bay_air\n"
        + "        {\n"
        + "            level (1 2);\n"
        + "            cellZone region_bay_air;\n"
        + "            cellZoneInside inside;\n"
        + "        }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(
        fluid=("region_bay_air",),
        solid=(
            "Inner_Surf",
            "Outer_Surf",
            "Plane_Outer_Surf",
            "firewall_front_solid",
            "firewall_behind_solid",
            "Frame_solid",
        ),
    )
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert len(result) == 7
    # 1 fluid region should have a non-None snapshot
    fluid_snap = result.get("region_bay_air")
    assert fluid_snap is not None
    assert isinstance(fluid_snap, RegionShmSnapshot)
    assert fluid_snap.surface_present
    # 6 extruded solids should be honest None
    extruded = [
        "Inner_Surf",
        "Outer_Surf",
        "Plane_Outer_Surf",
        "firewall_front_solid",
        "firewall_behind_solid",
        "Frame_solid",
    ]
    for name in extruded:
        assert result[name] is None, f"extruded region {name!r} should be None"


# ---------------------------------------------------------------------------
# B. Happy path — case_011 shape (3 regions, legacy locationInMesh)
# ---------------------------------------------------------------------------

def test_case_011_shape_3_region_snapshots(tmp_path: Path) -> None:
    """B. case_011-shaped 3-region fixture (2 fluid + 1 solid) yields 3 snapshots.

    Pin DEC-V61-217 W3.0.1 charter passes-criteria for the 3-region path.
    Each snapshot must be non-None with surface_present=True.
    """
    _write_master_shm(tmp_path, _make_3region_shm_legacy())
    snap = _make_region_snapshot(
        fluid=("region_hot_fluid", "region_cold_fluid"),
        solid=("region_solid",),
    )
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert len(result) == 3
    assert set(result.keys()) == {"region_hot_fluid", "region_cold_fluid", "region_solid"}
    for name, region_snap in result.items():
        assert region_snap is not None, f"region {name!r} unexpectedly None"
        assert region_snap.surface_present


# ---------------------------------------------------------------------------
# C. V90 modern locationsInMesh — no empty cellZones (the known-failure pin)
# ---------------------------------------------------------------------------

def test_v90_locationsInMesh_all_regions_non_empty(tmp_path: Path) -> None:
    """C. V90 ``locationsInMesh`` syntax: each named seed entry yields a non-None
    snapshot.

    V90 known-failure-mode: a real OF sHM produced empty cellZones because
    ``locationsInMesh`` seeds were not correctly wired to per-region zones.
    This test pins that the extractor surfaces each declared seed as a
    NON-empty snapshot (location_seed_present=True), not a ``None`` or ``{}``.

    DEC-V61-217 W3.0.1 charter: "demonstrably handles V90 modern
    ``locationsInMesh`` syntax without empty cellZones".
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry\n"
        + "{\n"
        + "    hot.stl  { type triSurfaceMesh; name region_hot_fluid; }\n"
        + "    cold.stl { type triSurfaceMesh; name region_cold_fluid; }\n"
        + "    wall.stl { type triSurfaceMesh; name region_solid; }\n"
        + "}\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationsInMesh\n"
        + "    (\n"
        + "        ((0.090 0.05825 0.045) region_hot_fluid)\n"
        + "        ((0.09175 0.060 0.027) region_cold_fluid)\n"
        + "        ((0.090 0.060 0.0191) region_solid)\n"
        + "    );\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        region_hot_fluid  { cellZone region_hot_fluid;  cellZoneInside inside; }\n"
        + "        region_cold_fluid { cellZone region_cold_fluid; cellZoneInside inside; }\n"
        + "        region_solid      { cellZone region_solid;      cellZoneInside inside; }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(
        fluid=("region_hot_fluid", "region_cold_fluid"),
        solid=("region_solid",),
    )
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    for name, region_snap in result.items():
        assert region_snap is not None, (
            f"V90: region {name!r} is None — locationsInMesh seed not surfaced"
        )
        assert region_snap.location_seed_present, (
            f"V90: region {name!r} has location_seed_present=False"
        )
        assert region_snap.location_syntax == "locationsInMesh", (
            f"V90: expected syntax 'locationsInMesh', got {region_snap.location_syntax!r}"
        )
        assert region_snap.seed_point is not None, (
            f"V90: region {name!r} seed_point is None"
        )
        assert len(region_snap.seed_point) == 3


# ---------------------------------------------------------------------------
# D. V92 cellZoneInside heterogeneity distinguished
# ---------------------------------------------------------------------------

def test_v92_cellZoneInside_modes_distinguished(tmp_path: Path) -> None:
    """D. V92 ``cellZoneInside inside`` vs ``insidePoint`` heterogeneity.

    Hybrid fixture (v5b-shape): one region uses ``inside``, another uses
    ``insidePoint``.  The extractor must capture per-region mode distinctly
    (not normalize both to one mode) so a downstream V92 validator can tell
    them apart.

    DEC-V61-217 W3.0.1 charter: "demonstrably distinguishes V92
    ``cellZoneInside`` inside-topology heterogeneity".
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry\n"
        + "{\n"
        + "    cold.stl  { type triSurfaceMesh; name region_cold_fluid; }\n"
        + "    solid.stl { type triSurfaceMesh; name region_solid; }\n"
        + "}\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.09 0.06 0.04);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        region_cold_fluid\n"
        + "        {\n"
        + "            level (1 2);\n"
        + "            cellZone region_cold_fluid;\n"
        + "            cellZoneInside inside;\n"
        + "        }\n"
        + "        region_solid\n"
        + "        {\n"
        + "            level (1 2);\n"
        + "            cellZone region_solid;\n"
        + "            cellZoneInside insidePoint;\n"
        + "            insidePoint (0.090 0.060 0.0191);\n"
        + "        }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(
        fluid=("region_cold_fluid",),
        solid=("region_solid",),
    )
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    cold_snap = result["region_cold_fluid"]
    solid_snap = result["region_solid"]
    assert cold_snap is not None
    assert solid_snap is not None
    # The two modes must be distinct
    assert cold_snap.cell_zone_inside_mode == "inside", (
        f"Expected 'inside', got {cold_snap.cell_zone_inside_mode!r}"
    )
    assert solid_snap.cell_zone_inside_mode == "insidePoint", (
        f"Expected 'insidePoint', got {solid_snap.cell_zone_inside_mode!r}"
    )
    assert cold_snap.cell_zone_inside_mode != solid_snap.cell_zone_inside_mode, (
        "V92: both regions have the same cellZoneInside mode — heterogeneity lost"
    )
    # insidePoint region should carry an inside_point coordinate
    assert solid_snap.inside_point is not None
    assert len(solid_snap.inside_point) == 3


# ---------------------------------------------------------------------------
# E. Missing-region-sHM honest handling
# ---------------------------------------------------------------------------

def test_missing_region_in_shm_yields_honest_none(tmp_path: Path) -> None:
    """E (absent tag). regionProperties declares 3 regions; sHM only tags 2.

    The 2 tagged regions yield real snapshots; the 1 untagged yields honest
    ``None``.  DEC-V61-218 lesson: do NOT fabricate a cellZone mapping for
    an untagged region.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry\n"
        + "{\n"
        + "    hot.stl   { type triSurfaceMesh; name region_hot_fluid; }\n"
        + "    cold.stl  { type triSurfaceMesh; name region_cold_fluid; }\n"
        + "}\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.09 0.06 0.04);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        region_hot_fluid  { cellZone region_hot_fluid;  cellZoneInside inside; }\n"
        + "        region_cold_fluid { cellZone region_cold_fluid; cellZoneInside inside; }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    # 3 regions in snapshot but only 2 in the sHM
    snap = _make_region_snapshot(
        fluid=("region_hot_fluid", "region_cold_fluid"),
        solid=("region_solid",),
    )
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert len(result) == 3
    assert result["region_hot_fluid"] is not None
    assert result["region_cold_fluid"] is not None
    assert result["region_solid"] is None, (
        "untagged region must yield honest None, not a fabricated snapshot"
    )


def test_present_but_empty_tag_yields_snapshot_not_none(tmp_path: Path) -> None:
    """E (present-but-empty-payload). A surface declares ``cellZone <region>`` but
    NOTHING else (no cellZoneInside / insidePoint / patchInfo).

    Per the cellZone-token association (red-team 2026-05-30 P1), region presence
    is established by the ``cellZone`` tag; "present-but-empty" means the tag
    exists but the rest of the payload is absent. Pin DEC-V61-213
    presence-vs-payload separation: surface_present=True, payload fields None,
    snapshot non-None.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { bay_geom.stl { type triSurfaceMesh; name bay_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        # cellZone tag present (-> region present) but no other payload.
        + "        bay_geom { cellZone region_empty; }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=("region_empty",), solid=())
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    region_snap = result["region_empty"]
    assert region_snap is not None, (
        "cellZone-tagged region with empty payload must yield non-None snapshot"
    )
    assert region_snap.surface_present is True
    assert region_snap.cell_zone == "region_empty"
    # payload fields beyond the tag are None (nothing else was declared)
    assert region_snap.cell_zone_inside_mode is None
    assert region_snap.inside_point is None
    assert region_snap.patch_info_type is None


# ---------------------------------------------------------------------------
# E'. Region→surface association is by cellZone TOKEN, not entry NAME
#     (red-team 2026-05-30 P1 anti-circularity pins — these FAIL on the
#     original entry-name-keyed implementation, PASS on the cellZone-keyed fix)
# ---------------------------------------------------------------------------

def test_region_found_by_cellzone_token_not_entry_name(tmp_path: Path) -> None:
    """RED-TEAM P1: the refinementSurfaces entry name (STL/geometry) DIFFERS from
    the region's cellZone token — the region must still be found via the
    cellZone token, not the entry name (case_016-shape).

    On the original entry-name-keyed code, ``region_solid`` would NOT be found
    (surf_map key is ``APU_body_geom``) and would wrongly yield ``None``.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { APU_body.stl { type triSurfaceMesh; name APU_body_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        # entry name 'APU_body_geom' != cellZone token 'region_solid'
        + "        APU_body_geom { level (2 2); cellZone region_solid; cellZoneInside inside; }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=(), solid=("region_solid",))
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    region_snap = result["region_solid"]
    assert region_snap is not None, (
        "region must be matched by its cellZone token, not the surface entry name"
    )
    assert region_snap.surface_present is True
    assert region_snap.cell_zone == "region_solid"
    assert region_snap.cell_zone_inside_mode == "inside"
    # The geometry/entry name must NOT leak in as a phantom region.
    assert "APU_body_geom" not in result


def test_nested_regions_subblock_cellzone_does_not_leak(tmp_path: Path) -> None:
    """RED-TEAM P2: a ``cellZone`` declared inside a nested ``regions { ... }``
    per-surface-region sub-block must NOT leak to the parent surface and must
    NOT fabricate a phantom region.

    The geometry surface declares NO own cellZone; only a nested
    ``regions { innerWall { cellZone LEAKED_ZONE; } }`` does. The parent surface
    therefore tags no region, so neither ``LEAKED_ZONE`` nor the geometry name
    may appear as a populated region.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { duct.stl { type triSurfaceMesh; name duct; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        duct\n"
        + "        {\n"
        + "            level (1 2);\n"
        + "            regions { innerWall { cellZone LEAKED_ZONE; patchInfo { type wall; } } }\n"
        + "        }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    # snapshot asks for both the leaked token and the real geometry name
    snap = _make_region_snapshot(fluid=(), solid=("LEAKED_ZONE", "duct"))
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    # Neither may be a populated snapshot — the parent surface tags no region.
    assert result["LEAKED_ZONE"] is None, "nested cellZone leaked to a phantom region"
    assert result["duct"] is None, "geometry name fabricated a region with no cellZone"


def test_duplicate_cellzone_token_yields_honest_none(tmp_path: Path) -> None:
    """RED-TEAM P1 follow-on: two refinementSurfaces entries declaring the SAME
    ``cellZone token`` is an ambiguous source → that region yields honest
    ``None`` (DEC-V61-218 refusal), not a silent first-match guess.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry\n"
        + "{\n"
        + "    a.stl { type triSurfaceMesh; name geom_a; }\n"
        + "    b.stl { type triSurfaceMesh; name geom_b; }\n"
        + "}\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        geom_a { cellZone dup_zone; cellZoneInside inside; }\n"
        + "        geom_b { cellZone dup_zone; cellZoneInside insidePoint; insidePoint (1 1 1); }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=(), solid=("dup_zone",))
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert result["dup_zone"] is None, (
        "duplicate cellZone token must refuse (None), not silently pick first match"
    )


# ---------------------------------------------------------------------------
# F. Malformed-input refusal (parametrized)
# ---------------------------------------------------------------------------

def test_none_region_snapshot_returns_none(tmp_path: Path) -> None:
    """F(i). ``region_snapshot=None`` → extractor returns ``None``.

    The snapshot is the authoritative region-name source; without it there
    is nothing to iterate.
    """
    _write_master_shm(
        tmp_path,
        _FOAMFILE_HEADER
        + "geometry { a.stl { type triSurfaceMesh; } }\n"
        + "castellatedMeshControls { refinementSurfaces {} refinementRegions {} }\n",
    )
    result = extract_shm_dict_multi_region(tmp_path, None)
    assert result is None


def test_both_groups_none_snapshot_returns_none(tmp_path: Path) -> None:
    """F (snapshot(None,None)). ``Snapshot(None, None)`` → ``None``.

    ``Snapshot(None, None)`` means no group was declared in the source
    ``regions ()`` entry — there are no region names to iterate.
    Distinct from ``Snapshot((), ())`` which means declared-but-empty.
    """
    _write_master_shm(
        tmp_path,
        _FOAMFILE_HEADER
        + "geometry { a.stl { type triSurfaceMesh; } }\n"
        + "castellatedMeshControls { refinementSurfaces {} refinementRegions {} }\n",
    )
    result = extract_shm_dict_multi_region(
        tmp_path, RegionPropertiesSnapshot(fluid_regions=None, solid_regions=None)
    )
    assert result is None


def test_both_groups_empty_tuple_returns_empty_mapping(tmp_path: Path) -> None:
    """F (snapshot((),())). ``Snapshot((), ())`` → empty mapping ``{}``, NOT ``None``.

    Declared-but-empty groups → valid snapshot, zero regions → empty mapping.
    """
    _write_master_shm(
        tmp_path,
        _FOAMFILE_HEADER
        + "geometry { a.stl { type triSurfaceMesh; } }\n"
        + "castellatedMeshControls { refinementSurfaces {} refinementRegions {} }\n",
    )
    result = extract_shm_dict_multi_region(
        tmp_path, RegionPropertiesSnapshot(fluid_regions=(), solid_regions=())
    )
    assert result is not None
    assert result == {}


def test_missing_master_shm_returns_none(tmp_path: Path) -> None:
    """F(ii). Master ``system/snappyHexMeshDict`` missing → ``None``."""
    snap = _make_region_snapshot(fluid=("air",), solid=("metal",))
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is None


@pytest.mark.parametrize(
    "shm_body",
    [
        "FoamFile { version 2.0; object snappyHexMeshDict; }\n// only comments\n",
        "// purely comments, no blocks\n/* another comment */\n",
        "",
    ],
    ids=["comments-only", "pure-comments", "empty-file"],
)
def test_unparseable_master_shm_returns_none(tmp_path: Path, shm_body: str) -> None:
    """F(iii). Master sHM is present but yields no recognizable blocks → ``None``."""
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=("air",), solid=("metal",))
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is None


# ---------------------------------------------------------------------------
# G. Per-region presence vs payload-completeness (DEC-V61-213)
# ---------------------------------------------------------------------------

def test_presence_vs_payload_distinct_encodings_are_not_equal(tmp_path: Path) -> None:
    """G. PIN DEC-V61-213: region-tagged-but-no-extra-payload ≠ region-not-in-sHM.

    ``surface_present=True`` (cellZone tag present, no other payload)
    vs ``None`` (absent from sHM entirely).

    These two must NOT encode identically.  If a future refactor collapses
    absent-region and present-but-empty-payload to the same value, this breaks.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { tag.stl { type triSurfaceMesh; name tag_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        # cellZone tag present (region present) but no further payload.
        + "        tag_geom { cellZone tagged_region; }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(
        fluid=("tagged_region",),
        solid=("untagged_region",),
    )
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    tagged_snap = result["tagged_region"]
    untagged_snap = result["untagged_region"]
    assert tagged_snap is not None, "present (cellZone-tagged) region must not be None"
    assert tagged_snap.surface_present is True
    assert tagged_snap.cell_zone_inside_mode is None  # empty payload beyond the tag
    assert untagged_snap is None, "absent region must be None"
    # The two encodings are NOT equal (the V213 separation)
    assert tagged_snap != untagged_snap, (
        "DEC-V61-213 separation collapsed: present-but-empty and absent-from-sHM "
        "have the same encoding"
    )


# NOTE: the original workflow added a strict-xfail
# `test_nested_subblock_cellzone_does_not_leak_to_parent` documenting RT-W3.0.1-1
# as an OPEN leak. That leak is now FIXED (brace-depth-0 scan in
# `_top_level_only`) and the correct behavior is pinned by
# `test_nested_regions_subblock_cellzone_does_not_leak` above (a passing test).
# The xfail was removed rather than flipped because, under the cellZone-token
# keying, a surface declaring no cellZone tags no region at all (so the parent
# `r1` is honestly None, not a present-with-None-cell_zone snapshot) — the old
# premise no longer holds.


# ---------------------------------------------------------------------------
# H. RegionPropertiesSnapshot drives the iteration
# ---------------------------------------------------------------------------

def test_snapshot_is_authoritative_for_region_set(tmp_path: Path) -> None:
    """H. The ``RegionPropertiesSnapshot`` is the authoritative region-name set.

    A cellZone name in sHM that is NOT in the snapshot does NOT appear in the
    output.  A region name in the snapshot but absent from sHM does NOT crash
    and yields ``None``.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry\n"
        + "{\n"
        + "    in_snap.stl     { type triSurfaceMesh; name in_snapshot; }\n"
        + "    not_in_snap.stl { type triSurfaceMesh; name not_in_snapshot; }\n"
        + "}\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        in_snapshot     { cellZone in_snapshot;     cellZoneInside inside; }\n"
        + "        not_in_snapshot { cellZone not_in_snapshot; cellZoneInside inside; }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    # Snapshot only declares "in_snapshot"; "not_in_snapshot" is in sHM but NOT snapshot
    snap = _make_region_snapshot(fluid=("in_snapshot",), solid=())
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert "in_snapshot" in result
    assert "not_in_snapshot" not in result, (
        "snapshot is authoritative: cellZone in sHM but absent from snapshot "
        "must NOT appear in output"
    )
    assert result["in_snapshot"] is not None


def test_region_in_snapshot_absent_from_shm_does_not_crash(tmp_path: Path) -> None:
    """H (no crash). A region in the snapshot but absent from sHM yields ``None``,
    no exception.
    """
    _write_master_shm(
        tmp_path,
        _FOAMFILE_HEADER
        + "geometry { a.stl { type triSurfaceMesh; name known_region; } }\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces { known_region { cellZone known_region; cellZoneInside inside; } }\n"
        + "    refinementRegions {}\n"
        + "}\n",
    )
    snap = _make_region_snapshot(
        fluid=("known_region", "phantom_region"),
        solid=(),
    )
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert result.get("phantom_region") is None  # no crash, honest None
    assert result.get("known_region") is not None


# ---------------------------------------------------------------------------
# I. Stdlib-only / trimesh-free pin (subprocess)
# ---------------------------------------------------------------------------

def test_extractor_module_loads_without_trimesh() -> None:
    """I. Mirror DEC-V61-211 R0 P1 fix: module imports cleanly when ``trimesh``
    is absent.

    Subprocess stubs ``trimesh`` to ``None``, imports
    ``extract_shm_dict_multi_region``, smoke-calls on a nonexistent dir → ``None``,
    prints 'OK'.  Pin: no transitive trimesh pull (no geometry_ingest import).
    """
    code = (
        "import sys\n"
        "sys.modules['trimesh'] = None\n"
        "from pathlib import Path\n"
        "from ui.backend.services.case_extractors import extract_shm_dict_multi_region\n"
        "from ui.backend.services.case_extractors import shm_dict_multi_region\n"
        "result = extract_shm_dict_multi_region(Path('/nonexistent_dir_xyz'), None)\n"
        "assert result is None\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        timeout=30,
    )
    assert result.returncode == 0 and result.stdout.strip() == "OK", (
        f"extractor failed to import without trimesh.\n"
        f"  stdout: {result.stdout!r}\n"
        f"  stderr: {result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# J. Package re-export contract
# ---------------------------------------------------------------------------

def test_package_reexport_is_module_extract() -> None:
    """J. ``case_extractors.extract_shm_dict_multi_region`` is the same object as
    ``shm_dict_multi_region.extract``.

    Mirror ``test_extract_shm_dict_is_module_extract`` (sibling extractor test).
    """
    assert extract_shm_dict_multi_region is shm_dict_multi_region.extract


def test_all_now_has_seven_extractors() -> None:
    """J. ``case_extractors.__all__`` must list SEVEN extractors (SIX→SEVEN after W3.0.2).

    Drift canary on the ``__init__`` edit: if a future re-export is added or
    removed without updating ``__all__``, this test breaks.
    Updated from SIX→SEVEN when ``thermo_dict_multi_region`` was added (W3.0.2).
    """
    import ui.backend.services.case_extractors as pkg
    assert len(pkg.__all__) == 7, (
        f"Expected 7 extractors in __all__, got {len(pkg.__all__)}: {pkg.__all__}"
    )
    assert "extract_shm_dict_multi_region" in pkg.__all__
    assert "extract_thermo_dict_multi_region" in pkg.__all__


def test_region_shm_snapshot_is_frozen_dataclass() -> None:
    """J. ``RegionShmSnapshot`` is a frozen dataclass.

    Pin immutability contract (mirrors ``test_thermo_model_tags_is_frozen_dataclass``).
    """
    snap = RegionShmSnapshot(
        surface_present=True,
        cell_zone="my_zone",
        cell_zone_inside_mode="insidePoint",
    )
    assert dataclasses.is_dataclass(snap)
    assert snap.surface_present is True
    assert snap.cell_zone == "my_zone"
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.cell_zone = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# K. Purity / read-only
# ---------------------------------------------------------------------------

def test_pure_function_no_writes(tmp_path: Path) -> None:
    """K. Running ``extract`` must not modify any file on disk.

    Check mtime + size of ``system/snappyHexMeshDict`` and
    ``constant/regionProperties`` before and after extraction.
    """
    _write_master_shm(tmp_path, _make_3region_shm_legacy())
    _write_region_properties(
        tmp_path,
        _make_region_props(
            fluid_names="region_hot_fluid region_cold_fluid",
            solid_names="region_solid",
        ),
    )
    snap = _make_region_snapshot(
        fluid=("region_hot_fluid", "region_cold_fluid"),
        solid=("region_solid",),
    )

    shm_path = tmp_path / "system" / "snappyHexMeshDict"
    rp_path = tmp_path / "constant" / "regionProperties"
    shm_stat_before = shm_path.stat()
    rp_stat_before = rp_path.stat()

    _ = extract_shm_dict_multi_region(tmp_path, snap)

    shm_stat_after = shm_path.stat()
    rp_stat_after = rp_path.stat()

    assert shm_stat_before.st_mtime == shm_stat_after.st_mtime, "sHM mtime changed!"
    assert shm_stat_before.st_size == shm_stat_after.st_size, "sHM size changed!"
    assert rp_stat_before.st_mtime == rp_stat_after.st_mtime, "regionProperties mtime changed!"
    assert rp_stat_before.st_size == rp_stat_after.st_size, "regionProperties size changed!"


# ---------------------------------------------------------------------------
# CODEX R0 (CRS · 2026-05-30) regression pins
#   P2a: nested patchInfo must NOT leak to the parent region (depth-0 finder).
#   P2b: legacy locationInMesh syntax token must be preserved on snapshots.
# ---------------------------------------------------------------------------

def test_nested_patchinfo_does_not_leak_to_parent(tmp_path: Path) -> None:
    """CODEX R0 P2a: a ``patchInfo`` inside a nested ``regions { ... }`` sub-block
    must NOT be attributed to the parent region.

    The parent surface declares ``cellZone region_x`` (so the region is present)
    and has NO own ``patchInfo``; only a nested ``regions { inner { patchInfo {
    type leaked_type; } } }`` does. The honest value for the parent's
    ``patch_info_type`` is ``None`` — line-anchored matching would wrongly pick
    the indented nested ``patchInfo``.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { x.stl { type triSurfaceMesh; name x_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        x_geom\n"
        + "        {\n"
        + "            level (1 2);\n"
        + "            cellZone region_x;\n"
        + "            regions { inner { patchInfo { type leaked_type; } } }\n"
        + "        }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=(), solid=("region_x",))
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    region_snap = result["region_x"]
    assert region_snap is not None
    assert region_snap.cell_zone == "region_x"
    assert region_snap.patch_info_type is None, (
        "nested patchInfo leaked to parent — depth-0 finder failed; "
        f"got patch_info_type={region_snap.patch_info_type!r}"
    )


def test_parent_patchinfo_at_depth0_still_extracted(tmp_path: Path) -> None:
    """Guard the other side of CODEX R0 P2a: a parent's OWN depth-0 ``patchInfo``
    must still be extracted (the depth-aware finder must not over-correct)."""
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { x.stl { type triSurfaceMesh; name x_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        x_geom { cellZone region_x; patchInfo { type mappedWall; } }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=(), solid=("region_x",))
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert result["region_x"].patch_info_type == "mappedWall"


def test_legacy_locationInMesh_syntax_preserved(tmp_path: Path) -> None:
    """CODEX R0 P2b: a legacy global ``locationInMesh ( x y z )`` case must
    preserve ``location_syntax == "locationInMesh"`` on each region's snapshot,
    even though the global form yields no per-region seed.

    The dataclass advertises ``locationInMesh`` as a supported syntax token;
    gating it on ``location_seed_present`` dropped it for the common single-seed
    form. The honest state is ``location_syntax="locationInMesh"`` with
    ``seed_point=None`` (global seed not replicated per-region).
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { x.stl { type triSurfaceMesh; name x_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        x_geom { cellZone region_x; cellZoneInside inside; }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=(), solid=("region_x",))
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    region_snap = result["region_x"]
    assert region_snap is not None
    assert region_snap.location_syntax == "locationInMesh", (
        f"legacy locationInMesh syntax dropped; got {region_snap.location_syntax!r}"
    )
    # Global seed is NOT replicated into the per-region seed_point (documented).
    assert region_snap.seed_point is None
    assert region_snap.location_seed_present is False


# ---------------------------------------------------------------------------
# CODEX R1 (CRS · 2026-05-30) regression pins
#   P2a: only fluid+solid (the snapshot's groups) are iterated; non-CHT groups
#        that W3.0 does not surface are an inherited boundary, not a silent drop.
#   P2b: duplicate locationsInMesh zone seed → honest refusal (not last-wins).
# ---------------------------------------------------------------------------

def test_only_snapshot_groups_iterated_no_phantom_porous(tmp_path: Path) -> None:
    """CODEX R1 P2a: the output keys are exactly the snapshot's fluid+solid
    regions. A cellZone in the sHM whose name is NOT in the snapshot (e.g. a
    ``porous`` zone W3.0 did not surface) does NOT appear — the snapshot is
    authoritative; W3.0.1 cannot invent regions the snapshot does not carry.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { x.stl { type triSurfaceMesh; name x_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationInMesh (0.5 0.5 0.5);\n"
        + "    refinementSurfaces\n"
        + "    {\n"
        + "        air_geom    { cellZone air;        cellZoneInside inside; }\n"
        + "        porous_geom { cellZone porous_zone; cellZoneInside inside; }\n"
        + "    }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    # snapshot carries only the fluid region 'air' (W3.0 surfaces fluid+solid only)
    snap = _make_region_snapshot(fluid=("air",), solid=())
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert set(result.keys()) == {"air"}, (
        "output must contain exactly the snapshot's regions, not sHM cellZones "
        "absent from the snapshot"
    )
    assert result["air"] is not None


def test_duplicate_locationsInMesh_seed_yields_honest_none(tmp_path: Path) -> None:
    """CODEX R1 P2b: the same zone name seeded twice in ``locationsInMesh`` is an
    ambiguous source → that region refuses (``None``), not a silent last-wins seed
    (symmetric with the duplicate-cellZone refusal).
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { x.stl { type triSurfaceMesh; name x_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationsInMesh\n"
        + "    (\n"
        + "        ((0.10 0.10 0.10) dup_zone)\n"
        + "        ((0.90 0.90 0.90) dup_zone)\n"
        + "    );\n"
        + "    refinementSurfaces { }\n"
        + "    refinementRegions {}\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=("dup_zone",), solid=())
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert result["dup_zone"] is None, (
        "duplicate locationsInMesh seed must refuse (None), not keep last-wins"
    )


# ---------------------------------------------------------------------------
# CODEX R2 (CRS · 2026-05-30) regression pins (fixed at cap=3, user-ratified)
#   P2: seed-only V90 sHM (locationsInMesh, NO refinementSurfaces) is valid.
#   P3: malformed locationsInMesh entry (named, bad coords) refuses that zone.
# ---------------------------------------------------------------------------

def test_seed_only_v90_shm_without_refinementsurfaces(tmp_path: Path) -> None:
    """CODEX R2 P2: a valid V90 case that defines cellZones purely via
    ``locationsInMesh`` (NO ``refinementSurfaces`` block) must NOT be rejected
    as "no master sHM" — each seeded region yields
    ``location_seed_present=True``.
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { x.stl { type triSurfaceMesh; name x_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationsInMesh\n"
        + "    (\n"
        + "        ((0.10 0.10 0.10) region_hot_fluid)\n"
        + "        ((0.90 0.90 0.90) region_solid)\n"
        + "    );\n"
        # NOTE: deliberately NO refinementSurfaces / refinementRegions blocks.
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=("region_hot_fluid",), solid=("region_solid",))
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None, "seed-only V90 sHM wrongly rejected as no-master"
    assert len(result) == 2
    for name in ("region_hot_fluid", "region_solid"):
        snap_r = result[name]
        assert snap_r is not None, f"seed-only region {name!r} lost"
        assert snap_r.location_seed_present is True
        assert snap_r.seed_point is not None
        assert snap_r.location_syntax == "locationsInMesh"
        # No refinementSurfaces → no cellZone tag for these regions.
        assert snap_r.surface_present is False


def test_malformed_locationsInMesh_entry_refuses_named_zone(tmp_path: Path) -> None:
    """CODEX R2 P3: a ``locationsInMesh`` entry that names a zone but has
    unparseable coordinates must REFUSE that zone (None), not silently drop it
    (which would read as honest absence).
    """
    shm_body = (
        _FOAMFILE_HEADER
        + "geometry { x.stl { type triSurfaceMesh; name x_geom; } }\n\n"
        + "castellatedMeshControls\n"
        + "{\n"
        + "    locationsInMesh\n"
        + "    (\n"
        + "        ((0.10 0.10 0.10) good_zone)\n"
        + "        ((NOT COORDS HERE) typo_zone)\n"
        + "    );\n"
        + "    refinementSurfaces { }\n"
        + "}\n"
    )
    _write_master_shm(tmp_path, shm_body)
    snap = _make_region_snapshot(fluid=("good_zone", "typo_zone"), solid=())
    result = extract_shm_dict_multi_region(tmp_path, snap)
    assert result is not None
    assert result["good_zone"] is not None, "well-formed seed lost"
    assert result["typo_zone"] is None, (
        "malformed-coords seed must refuse the named zone, not silently drop it"
    )
