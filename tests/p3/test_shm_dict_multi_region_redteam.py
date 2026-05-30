"""RED-TEAM (LENS A · topology + parser correctness) for
``ui.backend.services.case_extractors.shm_dict_multi_region``.

Per DEC-V61-217 W3.0.1 test-red-team pass (lens=topology-correctness).
These tests encode the failure surfaces found in the 2026-05-30 red-team
review. Each is grounded in REAL OpenFOAM convention (verified against the
in-repo corpus sHM dicts and the V90/V92 industrial findings), NOT a
convenient synthetic shape.

**Status 2026-05-30**: the four findings below were all CONFIRMED defects in the
implementer's first cut and have since been FIXED by the main session before
Codex review (cellZone-token keying + brace-depth-0 scan + duplicate refusal).
The tests now assert the FIXED behavior; they were written first as
``xfail(strict=True)`` BUG markers and flipped to passing guards once the root
cause landed, so the corrected behavior stays pinned and cannot silently regress.

Ground-truth references:
  * ``.planning/case_profiles/case_016_v64_thermo_fpe_fix_dicts/system/snappyHexMeshDict``
    — surface key ``fwh_porous_surface`` declares ``cellZone fwh_inside``
      (surface name != cellZone name — the realistic case).
  * ``.planning/case_profiles/case_004_v64_mesh_gen_v2_dicts/system/snappyHexMeshDict``
    — surface ``rotating_cellzone`` with ``cellZone rotating_cellzone`` and a
      comment "cellZone naming matches MRFProperties" (cellZone is the
      authoritative link, not the surface name).
  * ``industrial_case_solver_findings.md`` V90/V92 — canonical multi-region sHM
    is single-master-sHM + cellZones; V90 single-STL form uses a nested
    ``regions { ... }`` sub-dict under one ``refinementSurfaces.<name>``.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from ui.backend.services.case_extractors import extract_shm_dict_multi_region
from ui.backend.services.case_extractors.region_properties_reader import (
    RegionPropertiesSnapshot,
)

_FOAMFILE_HEADER = (
    "FoamFile\n"
    "{\n"
    "    version 2.0;\n"
    "    format ascii;\n"
    "    class dictionary;\n"
    "    object snappyHexMeshDict;\n"
    "}\n"
    "castellatedMesh true;\n"
    "snap true;\n\n"
)


def _write(case_dir: Path, body: str) -> None:
    (case_dir / "system").mkdir(exist_ok=True)
    (case_dir / "system" / "snappyHexMeshDict").write_text(body, encoding="utf-8")


def _snap(
    fluid: tuple[str, ...] | None,
    solid: tuple[str, ...] | None,
) -> RegionPropertiesSnapshot:
    return RegionPropertiesSnapshot(fluid_regions=fluid, solid_regions=solid)


# ---------------------------------------------------------------------------
# FINDING 1 (P1 · FIXED): region keyed by cellZone token, not surface name.
# In real OF the region in regionProperties maps to the ``cellZone <token>``,
# which can DIFFER from the surface name (case_016: surface ``fwh_porous_surface``
# -> cellZone ``fwh_inside``). The fix indexes refinementSurfaces by cellZone token.
# ---------------------------------------------------------------------------

def test_region_keyed_by_cellzone_token_not_surface_name() -> None:
    """The region name in regionProperties == cellZone token; surface key differs.

    case_016 / chtMultiRegionHeater shape: refinementSurface key is the
    geometry/STL alias (``heater_geom``); the cellZone token (``heater``) is the
    actual region name. The extractor must find regions via the cellZone token.
    """
    d = Path(tempfile.mkdtemp())
    _write(
        d,
        _FOAMFILE_HEADER
        + "castellatedMeshControls\n{\n"
        + "  refinementSurfaces\n  {\n"
        + "    heater_geom { level (1 2); cellZone heater; cellZoneInside inside; }\n"
        + "    air_geom    { level (1 2); cellZone air;    cellZoneInside inside; }\n"
        + "  }\n  refinementRegions {}\n}\n",
    )
    result = extract_shm_dict_multi_region(d, _snap(("air",), ("heater",)))
    assert result is not None
    # Found via the cellZone token even though the surface keys differ.
    assert result["heater"] is not None, "region 'heater' (a declared cellZone) lost"
    assert result["heater"].cell_zone == "heater"
    assert result["air"] is not None, "region 'air' (a declared cellZone) lost"
    # The geometry/surface names must NOT leak in as phantom regions.
    assert "heater_geom" not in result
    assert "air_geom" not in result


def test_divergent_surface_name_does_not_fabricate_a_region() -> None:
    """Fail-closed guard: a region named after the SURFACE (geometry) key — not a
    cellZone token — must resolve to ``None``, never a name-based fabrication.

    Surface ``heater_geom`` declares ``cellZone heater``. Asking for a region
    literally named ``heater_geom`` (the geometry alias, which is NOT a cellZone)
    must be ``None`` — the extractor keys on cellZone tokens, not surface names.
    """
    d = Path(tempfile.mkdtemp())
    _write(
        d,
        _FOAMFILE_HEADER
        + "castellatedMeshControls\n{\n"
        + "  refinementSurfaces\n  {\n"
        + "    heater_geom { cellZone heater; cellZoneInside inside; }\n"
        + "  }\n  refinementRegions {}\n}\n",
    )
    result = extract_shm_dict_multi_region(d, _snap((), ("heater_geom",)))
    assert result is not None
    assert result["heater_geom"] is None, (
        "a surface/geometry name is not a cellZone — must not fabricate a region"
    )


# ---------------------------------------------------------------------------
# FINDING 2 (P1 · FIXED): a pure WALL/patch refinementSurface (no cellZone) must
# NOT mint a region. case_016's `inflow`/`outflow`/`cavity_le_wall` are
# refinementSurfaces but not cellZone-bearing regions. The fix: surface_present
# is established only by a cellZone token, so a bare patch surface tags no region.
# ---------------------------------------------------------------------------

def test_wall_surface_without_cellzone_is_not_a_region() -> None:
    """A boundary-patch refinementSurface (no cellZone) must NOT mint a region.

    In a real master sHM, ``inflow``/``outflow``/wall surfaces are
    refinementSurfaces but are NOT cellZone-bearing regions. A region named after
    such a surface must be honest ``None``, not a fabricated "is in the sHM" signal.
    """
    d = Path(tempfile.mkdtemp())
    _write(
        d,
        _FOAMFILE_HEADER
        + "castellatedMeshControls\n{\n"
        + "  refinementSurfaces\n  {\n"
        + "    inflow  { level (0 0); patchInfo { type patch; } }\n"
        + "    outflow { level (0 0); patchInfo { type patch; } }\n"
        + "  }\n  refinementRegions {}\n}\n",
    )
    result = extract_shm_dict_multi_region(d, _snap(("inflow",), ("outflow",)))
    assert result is not None
    assert result["inflow"] is None, "boundary patch 'inflow' fabricated as a region"
    assert result["outflow"] is None, "boundary patch 'outflow' fabricated as a region"


# ---------------------------------------------------------------------------
# FINDING 3 (P1 · FIXED): cross-region field contamination. A refinementSurface
# carrying a nested ``regions { sub_a {...} sub_b {...} }`` sub-dict (canonical V90
# single-STL multi-region form) was parsed by regex over the WHOLE body with no
# brace-depth awareness, stitching cell_zone from sub_a + inside_point from sub_b.
# The fix: depth-0 scan (`_top_level_only`) — the parent declares no own cellZone,
# so it tags no region (honest None) and no fields are mixed.
# ---------------------------------------------------------------------------

def test_nested_regions_parent_without_own_cellzone_is_none() -> None:
    """A surface whose only cellZones live in a nested ``regions {}`` sub-dict, with
    no own top-level cellZone, tags NO region — the parent is honest ``None`` and
    no fields are stitched across sub-regions (mixed-provenance fabrication).
    """
    d = Path(tempfile.mkdtemp())
    _write(
        d,
        _FOAMFILE_HEADER
        + "castellatedMeshControls\n{\n"
        + "  refinementSurfaces\n  {\n"
        + "    wholeAssembly\n    {\n"
        + "      level (1 2);\n"
        + "      regions\n      {\n"
        + "        sub_a { cellZone sub_a; cellZoneInside inside; }\n"
        + "        sub_b { cellZone sub_b; cellZoneInside insidePoint; insidePoint (9 9 9); }\n"
        + "      }\n"
        + "    }\n"
        + "  }\n  refinementRegions {}\n}\n",
    )
    result = extract_shm_dict_multi_region(d, _snap(("wholeAssembly",), ()))
    assert result is not None
    # Parent declares no own top-level cellZone -> tags no region -> honest None.
    assert result["wholeAssembly"] is None, (
        "parent surface with only nested-sub-region cellZones must not become a "
        "region with stitched mixed-provenance fields"
    )


def test_single_stl_regions_subdict_subregions_are_not_surfaced() -> None:
    """The nested ``regions{}`` sub-region names are not first-class regions today.

    The region names a single-STL multi-region case lists in regionProperties
    (``sub_a``) are NOT discoverable as top-level refinementSurface cellZones
    (only the nested sub-dict declares them). Documented blind spot: surfacing
    them would be a deliberate future FIX, so this guard intentionally breaks then.
    """
    d = Path(tempfile.mkdtemp())
    _write(
        d,
        _FOAMFILE_HEADER
        + "castellatedMeshControls\n{\n"
        + "  refinementSurfaces\n  {\n"
        + "    wholeAssembly { level (1 2); regions { sub_a { cellZone sub_a; } } }\n"
        + "  }\n  refinementRegions {}\n}\n",
    )
    result = extract_shm_dict_multi_region(d, _snap(("sub_a",), ()))
    assert result is not None
    # sub_a is a nested cellZone of the single STL, not a top-level cellZone.
    assert result["sub_a"] is None


# ---------------------------------------------------------------------------
# FINDING 4 (P1 follow-on · FIXED): duplicate cellZone token. Two surfaces
# declaring the SAME cellZone token is ambiguous; the fix refuses (honest None)
# rather than silently picking the first match.
# ---------------------------------------------------------------------------

def test_duplicate_cellzone_token_yields_honest_none() -> None:
    """A cellZone token declared by two different surfaces is ambiguous → None.

    ``shared_zone`` is the cellZone of both ``surf_A`` and ``surf_B``. The region
    resolves to honest ``None`` (DEC-V61-218 refusal), not a first-match guess.
    """
    d = Path(tempfile.mkdtemp())
    _write(
        d,
        _FOAMFILE_HEADER
        + "castellatedMeshControls\n{\n"
        + "  refinementSurfaces\n  {\n"
        + "    surf_A { cellZone shared_zone; cellZoneInside inside; }\n"
        + "    surf_B { cellZone shared_zone; cellZoneInside insidePoint; insidePoint (1 1 1); }\n"
        + "  }\n  refinementRegions {}\n}\n",
    )
    result = extract_shm_dict_multi_region(d, _snap(("shared_zone",), ()))
    assert result is not None
    assert result["shared_zone"] is None, (
        "duplicate cellZone token must refuse (None), not silently pick first match"
    )
