"""DEC-V61-212 · shm_dict_extractor tests.

Coverage:

  - **Parametrized 9-profile sweep** (every in-repo `system/snappyHexMeshDict`,
    excluding the non-standard case_004_v64_mesh_conv_study `h2/`+`h4/`
    layout which is explicitly deferred per DEC §"non-feature 6"):
    each profile yields a non-None Mapping; baseline geometry-key set is
    asserted per profile.
  - **Per-shape canaries** for the four extractor outputs:
      * geometry: alias form (case_028) vs file form (case_006)
      * features: empty `()` (case_028 / case_006) vs populated (case_029)
      * refinementSurfaces.patchInfo.type: extracted verbatim from source
      * refinementRegions: key-set captured (case_029.refineBox)
      * addLayersControls: top-level keys only (no surface-name leak from
        `layers { surface { ... } }` sub-block)
  - **DEC R1/R2/R3 truth-chain risk** tests (tmp_path):
      * R1: features absent vs empty `()` vs malformed → None vs [] vs None
      * R2: patchInfo absent vs present-with-type vs present-no-type
            → no patchInfo key vs `{type: ...}` vs `{}`
      * R3: case_028 `name:` alias preserved (29 aliases, fabrication
            of 29 missing_geometry_ref would deluge the advisor)
  - **E2E hookup** test pipes case_028's + case_029's extracted dicts
    directly into `validate_shm_dict` and asserts the case-specific
    findings each produces (case_028 = clean 29-surface;
    case_029 = 1 known typo_suspicion for `nRelaxedIter` — see test
    docstring for advisor-CANONICAL_KEYS gap note).
  - **Source-file-missing / unreadable / no-block** edge cases.

DEC-211 parallel: this file mirrors `test_solver_block_extractor.py`'s
spirit (canaries + cross-profile sweep + tmp_path edges) but ships NO
drift-parity canary (DEC-V61-212 §"R4 NO drift-parity canary needed" —
the extractor returns a generic `Mapping[str, Any]` and does not
mirror any advisor dataclass/constants).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# Resolve repo root from this test file's location, mirroring DEC-211's
# test convention (avoids reliance on CWD).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PROFILES_DIR = _REPO_ROOT / ".planning" / "case_profiles"


# The 9 in-repo profiles shipping a STANDARD `system/snappyHexMeshDict`.
# (case_004_v64_mesh_conv_study's `h2/` + `h4/` snappyHexMeshDict files
# are non-standard sub-mesh-dirs explicitly deferred per DEC-V61-212
# §"non-feature 6" — that case returns None from the extractor.)
_PROFILES_WITH_STANDARD_SHM: tuple[str, ...] = (
    "case_004_v64_mesh_gen_v2_dicts",
    "case_006_v64_thermo_fpe_fix_dicts",
    "case_006_v64_val_full_2_dicts",
    "case_016_v64_thermo_fpe_fix_dicts",
    "case_028_apu_bay_ventilation_dicts",
    "case_028_v2_apu_bay_ventilation_dicts",
    "case_028_v3_apu_bay_ventilation_dicts",
    "case_028_v4_apu_bay_ventilation_dicts",
    "case_029_naca_stall_dicts",
)


# ---------------------------------------------------------------------
# Import the extractor under test. Per DEC-V61-212 §"Architectural
# placement", the module must be stdlib-only AND must not import from
# `geometry_ingest` (which would pull trimesh transitively in `.[ui]`
# environments). The package-level import is via __init__.
# ---------------------------------------------------------------------
from ui.backend.services.case_extractors import extract_shm_dict  # noqa: E402
from ui.backend.services.case_extractors import shm_dict_extractor  # noqa: E402


# =====================================================================
# Cross-profile sweep — every standard-layout profile parses.
# =====================================================================
@pytest.mark.parametrize("profile_name", _PROFILES_WITH_STANDARD_SHM)
def test_extract_returns_non_none_for_every_standard_profile(profile_name: str) -> None:
    """Every in-repo profile with `system/snappyHexMeshDict` must parse."""
    case_dir = _PROFILES_DIR / profile_name
    result = extract_shm_dict(case_dir)
    assert result is not None, f"extract returned None for {profile_name}"
    # At minimum the geometry block should be present in every in-repo SHM.
    assert "geometry" in result, (
        f"profile {profile_name} missing `geometry` key after extract"
    )


def test_profile_count_matches_dec_survey_2026_05_28() -> None:
    """Drift canary: if a new profile lands a `system/snappyHexMeshDict`,
    the cross-profile sweep above silently won't cover it. This test
    enumerates all profiles currently shipping a STANDARD-layout SHM and
    asserts the fixture tuple stays in sync. Update both when a new
    profile lands an SHM (mirror of DEC-211 footnote pattern for the
    initial 4→5 density-based solver recount).
    """
    discovered = sorted(
        p.parent.parent.name  # case_<x>_dicts
        for p in _PROFILES_DIR.glob("*/system/snappyHexMeshDict")
    )
    assert discovered == sorted(_PROFILES_WITH_STANDARD_SHM), (
        f"discovered={discovered} but fixture lists "
        f"{sorted(_PROFILES_WITH_STANDARD_SHM)}; update "
        "`_PROFILES_WITH_STANDARD_SHM` AND the DEC-V61-212 §Decision "
        "survey paragraph to reflect new profile(s)."
    )


def test_case_004_mesh_conv_study_returns_none_per_dec_non_feature_6() -> None:
    """case_004_v64_mesh_conv_study ships `h2/snappyHexMeshDict` +
    `h4/snappyHexMeshDict` instead of `system/snappyHexMeshDict`. Per
    DEC-V61-212 §"non-feature 6", v0.1 looks for `system/...` only and
    returns None (honest omission — a follow-on sub-DEC can add
    multi-mesh-dir handling).
    """
    case_dir = _PROFILES_DIR / "case_004_v64_mesh_conv_study_dicts"
    assert case_dir.is_dir(), "fixture profile missing — repo drift"
    assert extract_shm_dict(case_dir) is None


# =====================================================================
# Per-shape canaries — geometry block.
# =====================================================================
def test_geometry_alias_form_preserved_case_028() -> None:
    """case_028 idiom: `Outer_Surf.stl { type triSurfaceMesh; name Outer_Surf; }`.

    The alias capture is THE difference between 0 fabricated
    `missing_geometry_ref` findings (correct) and 29 fabricated criticals
    (DEC R3 risk). The extractor must capture both the literal key
    `Outer_Surf.stl` AND the `name` alias `Outer_Surf` so
    `validate_shm_dict._resolve_geometry_aliases` can resolve the
    refinementSurfaces entry `Outer_Surf` against either.
    """
    result = extract_shm_dict(
        _PROFILES_DIR / "case_028_apu_bay_ventilation_dicts"
    )
    assert result is not None
    geom = result["geometry"]
    assert "Outer_Surf.stl" in geom, "literal key missing"
    entry = geom["Outer_Surf.stl"]
    assert entry == {"type": "triSurfaceMesh", "name": "Outer_Surf"}, (
        f"alias capture broken: {entry}"
    )
    # All 29 entries should follow the same alias-form pattern.
    assert len(geom) == 29
    for key, val in geom.items():
        assert key.endswith(".stl"), f"unexpected key form: {key}"
        assert val.get("type") == "triSurfaceMesh"
        assert isinstance(val.get("name"), str), (
            f"missing name alias on {key}"
        )


def test_geometry_file_form_preserved_case_006() -> None:
    """case_006 idiom: `wing_surface_reference { type triSurfaceMesh; file "wing_surface_reference.stl"; }`.

    Bare key (no `.stl` suffix), `file:` attribute instead of `name:`.
    No alias resolution needed — literal key == canonical patch name.
    """
    result = extract_shm_dict(
        _PROFILES_DIR / "case_006_v64_thermo_fpe_fix_dicts"
    )
    assert result is not None
    geom = result["geometry"]
    assert "wing_surface_reference" in geom
    entry = geom["wing_surface_reference"]
    assert entry == {
        "type": "triSurfaceMesh",
        "file": "wing_surface_reference.stl",
    }, f"file-form capture broken: {entry}"
    # No `name:` alias for file-form entries (would over-fabricate).
    assert "name" not in entry


def test_geometry_mixed_form_case_029() -> None:
    """case_029 mixes STL geom (alias form) AND a `box` primitive.

    Both forms must coexist. The `box` entry has type+min+max (we
    discard numeric values per scope; only type captured).
    """
    result = extract_shm_dict(_PROFILES_DIR / "case_029_naca_stall_dicts")
    assert result is not None
    geom = result["geometry"]
    assert set(geom.keys()) == {"naca0012.stl", "refineBox"}
    assert geom["naca0012.stl"] == {
        "type": "triSurfaceMesh",
        "name": "naca0012",
    }
    # `refineBox` has type=box only (no name, no file).
    assert geom["refineBox"]["type"] == "box"
    assert "name" not in geom["refineBox"]
    assert "file" not in geom["refineBox"]


# =====================================================================
# Per-shape canaries — castellatedMeshControls.features.
# =====================================================================
def test_features_empty_case_028() -> None:
    """case_028 source: `features ();` — extractor emits `[]`."""
    result = extract_shm_dict(
        _PROFILES_DIR / "case_028_apu_bay_ventilation_dicts"
    )
    assert result is not None
    assert result["castellatedMeshControls"]["features"] == []


def test_features_populated_case_029() -> None:
    """case_029 source: `features ( { file "naca0012.eMesh"; level 5; } );`.

    Extractor captures the file string (level numeric value discarded).
    """
    result = extract_shm_dict(_PROFILES_DIR / "case_029_naca_stall_dicts")
    assert result is not None
    feats = result["castellatedMeshControls"]["features"]
    assert feats == [{"file": "naca0012.eMesh"}]


# =====================================================================
# Per-shape canaries — refinementSurfaces.patchInfo.type.
# =====================================================================
def test_patchinfo_type_captured_for_every_surface_case_028() -> None:
    """All 29 case_028 surfaces declare `patchInfo { type wall; }`."""
    result = extract_shm_dict(
        _PROFILES_DIR / "case_028_apu_bay_ventilation_dicts"
    )
    assert result is not None
    rs = result["castellatedMeshControls"]["refinementSurfaces"]
    assert len(rs) == 29
    for surf_name, surf_cfg in rs.items():
        assert surf_cfg == {"patchInfo": {"type": "wall"}}, (
            f"surface {surf_name} cfg unexpected: {surf_cfg}"
        )


def test_patchinfo_type_captured_case_028_v3_intake_duct_is_patch() -> None:
    """case_028_v3 differs from v1/v2/v4: intake_duct + vent_door are
    `patchInfo type patch;` (inflow/outflow), remaining 27 are walls.

    This proves the extractor reads the EXACT type token per source,
    not a guessed default — case-class discrimination across the
    case_028 v1/v2/v3/v4 lineage depends on this.
    """
    result = extract_shm_dict(
        _PROFILES_DIR / "case_028_v3_apu_bay_ventilation_dicts"
    )
    assert result is not None
    rs = result["castellatedMeshControls"]["refinementSurfaces"]
    assert rs["intake_duct"] == {"patchInfo": {"type": "patch"}}
    assert rs["vent_door"] == {"patchInfo": {"type": "patch"}}
    # Spot-check 2 walls.
    assert rs["Outer_Surf"] == {"patchInfo": {"type": "wall"}}
    assert rs["compressor"] == {"patchInfo": {"type": "wall"}}
    # Count types — should be 2 patch + 27 wall = 29 total.
    patch_count = sum(
        1 for c in rs.values() if c.get("patchInfo", {}).get("type") == "patch"
    )
    wall_count = sum(
        1 for c in rs.values() if c.get("patchInfo", {}).get("type") == "wall"
    )
    assert (patch_count, wall_count, len(rs)) == (2, 27, 29), (
        f"v3 type-split unexpected: patch={patch_count} wall={wall_count} "
        f"total={len(rs)}"
    )


# =====================================================================
# Per-shape canary — refinementRegions.
# =====================================================================
def test_refinement_regions_captured_case_029() -> None:
    """case_029 declares one region: `refineBox { mode inside; ... }`."""
    result = extract_shm_dict(_PROFILES_DIR / "case_029_naca_stall_dicts")
    assert result is not None
    rr = result["castellatedMeshControls"]["refinementRegions"]
    assert "refineBox" in rr
    # Values discarded — region body is `{}` placeholder.
    assert rr["refineBox"] == {}


def test_refinement_regions_empty_case_028() -> None:
    """case_028 source: `refinementRegions { }` — extractor emits `{}`."""
    result = extract_shm_dict(
        _PROFILES_DIR / "case_028_apu_bay_ventilation_dicts"
    )
    assert result is not None
    rr = result["castellatedMeshControls"]["refinementRegions"]
    assert rr == {}


# =====================================================================
# Per-shape canary — addLayersControls flat keys (no nested leak).
# =====================================================================
def test_addlayerscontrols_top_level_keys_only_case_029() -> None:
    """`addLayersControls.layers { naca0012 { nSurfaceLayers 10; } }` —
    extractor captures `layers` as a top-level key but does NOT recurse
    into the surface-name sub-block (would expose `naca0012` as a
    walked key during typo fuzzy-match and possibly false-fire on
    coincidental edit-distance matches).
    """
    result = extract_shm_dict(_PROFILES_DIR / "case_029_naca_stall_dicts")
    assert result is not None
    alc = result["addLayersControls"]
    # `layers` IS captured (it's a top-level addLayersControls key).
    assert "layers" in alc
    assert alc["layers"] is None  # no recursion into sub-block
    # `naca0012` MUST NOT appear as a key in addLayersControls (would be
    # leaked from `layers { naca0012 { ... } }` if extractor recursed).
    assert "naca0012" not in alc
    # Sanity: real top-level keys present.
    assert "expansionRatio" in alc
    assert "minMedialAxisAngle" in alc
    assert "nLayerIter" in alc


# =====================================================================
# DEC R1 truth-chain: features absent vs empty vs malformed.
# =====================================================================
def _write_shm(tmp_path: Path, body: str) -> Path:
    """Create a minimal case_dir with `system/snappyHexMeshDict` body."""
    sysd = tmp_path / "system"
    sysd.mkdir(parents=True)
    (sysd / "snappyHexMeshDict").write_text(body, encoding="utf-8")
    return tmp_path


def test_r1_features_absent_omits_key(tmp_path: Path) -> None:
    """No `features` key in source → `features` absent from extracted cmc.

    Distinguishable from empty `features ()` (which yields []). Per
    DEC R1: absent ≠ empty; never silently default to `[]`.
    """
    case_dir = _write_shm(
        tmp_path,
        """FoamFile { object snappyHexMeshDict; }
        castellatedMeshControls
        {
            refinementSurfaces { }
        }
        """,
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    cmc = result["castellatedMeshControls"]
    assert "features" not in cmc, (
        "DEC R1 violation: features absent in source but extractor "
        "emitted the key — would fabricate V86 from caller-supplied "
        "available_emeshes"
    )


def test_r1_features_literally_empty_yields_empty_list(tmp_path: Path) -> None:
    """Source `features ();` → extractor emits `features: []`.

    Empty IS meaningful (V86 case_011 root: empty `features ()` + .eMesh
    on disk = orphan finding fires). Don't conflate with absent.
    """
    case_dir = _write_shm(
        tmp_path,
        """castellatedMeshControls { features (); refinementSurfaces { } }
        """,
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    assert result["castellatedMeshControls"]["features"] == []


def test_r1_features_malformed_omits_key(tmp_path: Path) -> None:
    """Source has braces inside features but no `file` key in entries —
    parse-failure → omit key (DEC R1: would otherwise emit `[]` and
    fabricate V86 from caller-supplied .eMesh inventory).
    """
    case_dir = _write_shm(
        tmp_path,
        """castellatedMeshControls
        {
            features ( { level 5; } );
            refinementSurfaces { }
        }
        """,
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    cmc = result["castellatedMeshControls"]
    # Entry exists ({ level 5; }) but has no file → parse mismatch →
    # omit key (1 expected from `{` count, 0 parsed).
    assert "features" not in cmc, (
        f"DEC R1 violation: expected omission, got: {cmc.get('features')}"
    )


# =====================================================================
# DEC R2 truth-chain: refinementSurface.patchInfo three sub-cases.
# =====================================================================
def test_r2_patchinfo_absent_yields_empty_surface_dict(tmp_path: Path) -> None:
    """Source surface has no patchInfo block → emit `{<surf>: {}}`.

    Paths (b)/(c) still detect missing_geometry_ref on this surface;
    path (e) silently skips (no type → no constraint check). DEC R2
    refined behavior (preserves path-b/c reach for zero path-e cost
    in v0.1 since v0.1 doesn't supply normals).
    """
    case_dir = _write_shm(
        tmp_path,
        """castellatedMeshControls
        {
            refinementSurfaces
            {
                bare_surf { level (1 2); }
            }
        }
        """,
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    rs = result["castellatedMeshControls"]["refinementSurfaces"]
    assert "bare_surf" in rs
    assert rs["bare_surf"] == {}, (
        f"DEC R2 sub-case 1 violation: expected `{{}}`, got: {rs['bare_surf']}"
    )


def test_r2_patchinfo_with_type_yields_full_dict(tmp_path: Path) -> None:
    """Source `patchInfo { type symmetryPlane; }` → `{"patchInfo": {"type": "symmetryPlane"}}`."""
    case_dir = _write_shm(
        tmp_path,
        """castellatedMeshControls
        {
            refinementSurfaces
            {
                sym_surf { level (1 2); patchInfo { type symmetryPlane; } }
            }
        }
        """,
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    rs = result["castellatedMeshControls"]["refinementSurfaces"]
    assert rs["sym_surf"] == {"patchInfo": {"type": "symmetryPlane"}}


def test_r2_patchinfo_present_no_type_yields_empty_patchinfo(tmp_path: Path) -> None:
    """Source `patchInfo { }` (or `{ otherKey foo; }` without `type`) →
    `{"patchInfo": {}}`.

    Distinguishes from "no patchInfo at all" (`{}`) but path (e) still
    safely skips (no string type → not in _CONSTRAINED_PATCH_TYPES).
    Paths (b)/(c) reach preserved (DEC R2 refined behavior).
    """
    case_dir = _write_shm(
        tmp_path,
        """castellatedMeshControls
        {
            refinementSurfaces
            {
                puzzle_surf { level (1 2); patchInfo { unrelated x; } }
            }
        }
        """,
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    rs = result["castellatedMeshControls"]["refinementSurfaces"]
    assert rs["puzzle_surf"] == {"patchInfo": {}}, (
        f"DEC R2 sub-case 3 violation: expected empty patchInfo, "
        f"got: {rs['puzzle_surf']}"
    )


# =====================================================================
# DEC-V61-212 R1 (Codex R0 findings) truth-chain tests.
# =====================================================================
def test_r1_codex_p1_quoted_name_alias_stripped(tmp_path: Path) -> None:
    """Codex R0 P1 (DEC-V61-212 R1): source `name "wing";` must extract
    to `wing` (NOT `'"wing"'`).

    Before the R1 fix, `_strip_one_paren_layer` only stripped outer
    parens — quoted tokens leaked their delimiters through. Downstream
    `validate_shm_dict` then fabricated `missing_geometry_ref` for
    every quoted alias because `'wing'` (refinementSurfaces literal
    key) ≠ `'"wing"'` (extracted alias).

    Renamed to `_strip_quotes_and_parens`; quoted alias now normalizes
    correctly per the module docstring's longstanding promise.
    """
    case_dir = _write_shm(
        tmp_path,
        '''
        geometry { wing.stl { type triSurfaceMesh; name "wing"; } }
        castellatedMeshControls { refinementSurfaces { wing { patchInfo { type wall; } } } }
        ''',
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    entry = result["geometry"]["wing.stl"]
    assert entry == {"type": "triSurfaceMesh", "name": "wing"}, (
        f"Codex R0 P1 regression: quoted name leaked → {entry}"
    )


def test_r1_codex_p1_quoted_patch_type_stripped(tmp_path: Path) -> None:
    """Codex R0 P1 (DEC-V61-212 R1): source `patchInfo { type "symmetryPlane"; }`
    must extract to `symmetryPlane` (NOT `'"symmetryPlane"'`).

    Before the R1 fix, the quoted type leaked through and
    `_CONSTRAINED_PATCH_TYPES` membership test in advisor path (e)
    failed silently (`'"symmetryPlane"'` ∉ the frozenset). A real
    multi-normal constrained patch would go undetected.

    The check `type in _CONSTRAINED_PATCH_TYPES` only runs when
    `stl_face_normals` is supplied (v0.1 extractor doesn't supply
    them), so the operational impact for v0.1 is zero — but truth-chain
    requires the extracted token match what the source declared.
    """
    case_dir = _write_shm(
        tmp_path,
        '''
        geometry { wing { type triSurfaceMesh; } }
        castellatedMeshControls
        {
            refinementSurfaces
            {
                wing { level (1 2); patchInfo { type "symmetryPlane"; } }
            }
        }
        ''',
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    rs = result["castellatedMeshControls"]["refinementSurfaces"]
    assert rs["wing"] == {"patchInfo": {"type": "symmetryPlane"}}, (
        f"Codex R0 P1 regression: quoted patch type leaked → {rs['wing']}"
    )


def test_r1_codex_p1_quoted_geometry_type_stripped(tmp_path: Path) -> None:
    """Same P1 class: `type "triSurfaceMesh"` in geometry entry."""
    case_dir = _write_shm(
        tmp_path,
        '''
        geometry { wing.stl { type "triSurfaceMesh"; name wing; } }
        ''',
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    entry = result["geometry"]["wing.stl"]
    assert entry["type"] == "triSurfaceMesh", (
        f"Codex R0 P1 regression: quoted geometry type leaked → {entry}"
    )


def test_r1_codex_p1_paren_alias_still_stripped_after_rename(tmp_path: Path) -> None:
    """Regression canary: when the helper was renamed from
    `_strip_one_paren_layer` → `_strip_quotes_and_parens`, the
    existing V100-WIDEN paren-stripping behavior must remain intact.
    Source `name (region_hot_fluid);` extracts to `region_hot_fluid`
    (no change from pre-R1 behavior; the V100-WIDEN parens convention
    in foamDictionary output is still honored).
    """
    case_dir = _write_shm(
        tmp_path,
        '''
        geometry { hot.stl { type triSurfaceMesh; name (region_hot_fluid); } }
        ''',
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    entry = result["geometry"]["hot.stl"]
    assert entry["name"] == "region_hot_fluid", (
        f"R1 rename broke V100-WIDEN paren stripping: {entry}"
    )


def test_r1_codex_p2_include_does_not_swallow_next_key(tmp_path: Path) -> None:
    """Codex R0 P2 (DEC-V61-212 R1): an `#include` line inside
    addLayersControls must NOT consume the next semicolon and silently
    drop the following key.

    Before the R1 fix:
      - `#include "layers.inc"` (no trailing `;`)
      - `_parse_addlayerscontrols_keys` skipped `#` (no progress),
        read `include` as a key (alnum walk), then took scalar path,
        called `body.find(";", i)` which jumped past `"layers.inc"`
        to the `;` after `minMedianAxisAngle 90`.
      - Net: `include` falsely emitted as a key; `minMedianAxisAngle`
        (the V52 typo target!) silently dropped.

    R1 fix: when leading char is `#`, skip the directive's whole line.
    Test asserts: `minMedianAxisAngle` IS in the extracted key set;
    `include` is NOT.
    """
    case_dir = _write_shm(
        tmp_path,
        '''
        addLayersControls
        {
        #include "layers.inc"
        minMedianAxisAngle 90;
        expansionRatio 1.2;
        }
        ''',
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    alc = result["addLayersControls"]
    assert "minMedianAxisAngle" in alc, (
        "Codex R0 P2 regression: V52 typo target silently dropped after "
        f"#include — alc keys = {sorted(alc.keys())}"
    )
    assert "include" not in alc, (
        "Codex R0 P2 regression: `include` leaked as a fake key from "
        f"`#include` directive — alc keys = {sorted(alc.keys())}"
    )
    assert "expansionRatio" in alc  # downstream key still present


def test_r1_codex_p2_include_directive_variants(tmp_path: Path) -> None:
    """Same P2 class with other `#`-prefixed directives:
    `#includeIfPresent`, `#remove`, `#inputMode merge`. None should
    inject a fake key or eat the next semicolon.
    """
    case_dir = _write_shm(
        tmp_path,
        '''
        addLayersControls
        {
        #includeIfPresent "optional.inc"
        #inputMode merge
        firstLayerThickness 1e-5;
        }
        ''',
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    alc = result["addLayersControls"]
    assert "firstLayerThickness" in alc, (
        f"Codex R0 P2 regression on variant: firstLayerThickness "
        f"dropped — alc keys = {sorted(alc.keys())}"
    )
    # Neither `includeIfPresent` nor `inputMode` nor `merge` should leak.
    assert not any(
        k in alc for k in ("includeIfPresent", "inputMode", "merge", "remove")
    ), f"Codex R0 P2 regression: directive leaked as key → {sorted(alc.keys())}"


def test_r1_codex_p1_e2e_quoted_alias_no_fabricated_advisor_findings(
    tmp_path: Path,
) -> None:
    """Codex R0 P1 e2e: quoted name `name "wing"` + refinementSurfaces
    `wing` → fed through `validate_shm_dict` must produce ZERO
    `missing_geometry_ref` and ZERO `geometry_orphan` findings (the
    alias resolves correctly).

    Before R1, this same input produced both findings because the
    extracted alias was `'"wing"'` instead of `'wing'`. Skip-if-trimesh.
    """
    pytest.importorskip("trimesh")
    from ui.backend.services.geometry_ingest.shm_dict_validator import (
        validate_shm_dict,
    )

    case_dir = _write_shm(
        tmp_path,
        '''
        geometry { wing.stl { type triSurfaceMesh; name "wing"; } }
        castellatedMeshControls
        {
            refinementSurfaces { wing { patchInfo { type wall; } } }
        }
        ''',
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    report = validate_shm_dict(dict(result))
    bad = [
        f for f in report.findings
        if f.code in ("missing_geometry_ref", "geometry_orphan")
    ]
    assert bad == [], (
        f"Codex R0 P1 e2e regression: quoted alias caused "
        f"{len(bad)} fabricated finding(s): "
        f"{[(f.code, f.location) for f in bad]}"
    )


# =====================================================================
# DEC R3 truth-chain: case_028 alias preservation (already exercised
# by test_geometry_alias_form_preserved_case_028; here adds the
# concrete "no fabricated missing_geometry_ref" e2e assertion).
# =====================================================================
def test_r3_alias_preservation_prevents_fabricated_findings_case_028() -> None:
    """If extractor fails to capture the `name:` alias, advisor path (b)
    would emit 29 `missing_geometry_ref` criticals (one per
    refinementSurfaces entry that doesn't match the `.stl`-suffix
    literal key). This test asserts the extracted dict produces ZERO
    such findings when fed to `validate_shm_dict`.

    Skip-if-trimesh-missing (validate_shm_dict's `geometry_ingest`
    parent package imports trimesh transitively via
    `__init__.py → health_check`).
    """
    pytest.importorskip("trimesh")
    from ui.backend.services.geometry_ingest.shm_dict_validator import (
        validate_shm_dict,
    )

    result = extract_shm_dict(
        _PROFILES_DIR / "case_028_apu_bay_ventilation_dicts"
    )
    assert result is not None
    report = validate_shm_dict(dict(result))
    bad = [f for f in report.findings if f.code == "missing_geometry_ref"]
    assert bad == [], (
        f"DEC R3 violation: extractor lost name: alias → "
        f"{len(bad)} fabricated missing_geometry_ref findings (expected 0)"
    )


# =====================================================================
# E2E hookup test — real extracted dict → real advisor.
# =====================================================================
def test_e2e_case_028_through_validate_shm_dict() -> None:
    """End-to-end: case_028's extracted shm_dict fed to validate_shm_dict.

    Expected: clean report — 29 surfaces all wall-typed, 29 geometry
    entries with name alias, 0 orphans, 0 typos. Real
    case-discrimination proof (the DEC §"Why shm_dict next" claim).

    skip-if-trimesh-missing per shm_dict_validator's parent package.
    """
    pytest.importorskip("trimesh")
    from ui.backend.services.geometry_ingest.shm_dict_validator import (
        validate_shm_dict,
    )

    result = extract_shm_dict(
        _PROFILES_DIR / "case_028_apu_bay_ventilation_dicts"
    )
    assert result is not None
    report = validate_shm_dict(dict(result))
    # 29 surfaces all reference one of the 29 geometry entries via alias.
    assert report.critical_count == 0, (
        f"case_028 should have 0 criticals (all aliases resolve); got "
        f"{report.critical_count}: "
        f"{[f.code for f in report.findings if f.severity == 'critical']}"
    )
    # 29 geometry entries, all referenced — no orphans.
    orphans = [f for f in report.findings if f.code == "geometry_orphan"]
    assert orphans == [], f"expected no orphans, got {len(orphans)}"
    # 29 geometry names captured.
    assert len(report.geometry_names) == 29


def test_e2e_case_029_through_validate_shm_dict_known_typo_canary() -> None:
    """case_029 e2e — has 1 KNOWN advisor finding (NOT extractor bug):

    `addLayersControls.nRelaxedIter` is a real OpenFOAM key but is NOT
    in the advisor's CANONICAL_KEYS list, so the advisor flags it as a
    typo_suspicion (edit-distance 1 from `nRelaxIter`). This is an
    advisor gap, not an extractor bug. Test asserts:
      (a) The extractor correctly captures `nRelaxedIter` as a key
          (truth-chain: source said this; we don't filter advisor false-
          positives out at extraction).
      (b) The advisor produces exactly this one finding from this case
          (drift canary: if the advisor's CANONICAL_KEYS is updated
          to include `nRelaxedIter`, this test will fail with 0
          findings and signal "advisor patched, update this test").

    skip-if-trimesh-missing.
    """
    pytest.importorskip("trimesh")
    from ui.backend.services.geometry_ingest.shm_dict_validator import (
        validate_shm_dict,
    )

    result = extract_shm_dict(_PROFILES_DIR / "case_029_naca_stall_dicts")
    assert result is not None
    alc = result["addLayersControls"]
    assert "nRelaxedIter" in alc, "extractor lost addLayersControls.nRelaxedIter"
    report = validate_shm_dict(dict(result))
    # 1 typo_suspicion finding expected (the advisor-CANONICAL_KEYS gap).
    typos = [f for f in report.findings if f.code == "typo_suspicion"]
    assert len(typos) == 1, (
        f"expected 1 typo_suspicion (advisor CANONICAL_KEYS missing "
        f"`nRelaxedIter`), got {len(typos)}: {[f.location for f in typos]}"
    )
    assert "nRelaxedIter" in typos[0].location
    # NO other findings expected (case_029 geometry resolves cleanly).
    non_typo = [f for f in report.findings if f.code != "typo_suspicion"]
    assert non_typo == [], (
        f"unexpected non-typo findings for case_029: "
        f"{[(f.code, f.location) for f in non_typo]}"
    )


# =====================================================================
# File-missing / unreadable / no-block edge cases.
# =====================================================================
def test_missing_shm_file_returns_none(tmp_path: Path) -> None:
    """case_dir with no `system/snappyHexMeshDict` → None."""
    (tmp_path / "system").mkdir()
    assert extract_shm_dict(tmp_path) is None


def test_missing_system_dir_returns_none(tmp_path: Path) -> None:
    """case_dir with no `system/` dir → None."""
    assert extract_shm_dict(tmp_path) is None


def test_empty_file_returns_none(tmp_path: Path) -> None:
    """Empty SHM (no recognizable block) → None."""
    case_dir = _write_shm(tmp_path, "")
    assert extract_shm_dict(case_dir) is None


def test_comments_only_returns_none(tmp_path: Path) -> None:
    """SHM containing only comments → None."""
    case_dir = _write_shm(
        tmp_path,
        """// just a comment
        /* and a block comment
           spanning lines */
        """,
    )
    assert extract_shm_dict(case_dir) is None


def test_only_unrecognized_blocks_returns_none(tmp_path: Path) -> None:
    """SHM with blocks the extractor doesn't recognize → None.

    Honest signal: "I parsed zero useful information." Better None than
    `{}` (which a downstream caller might mistake for "successfully
    parsed an empty case").
    """
    case_dir = _write_shm(
        tmp_path,
        """snapControls { tolerance 2.0; }
        meshQualityControls { maxNonOrtho 65; }
        """,
    )
    assert extract_shm_dict(case_dir) is None


def test_partial_block_still_extracted(tmp_path: Path) -> None:
    """SHM with ONLY a geometry block (no cmc, no alc) → extract still
    returns the geometry. Per DEC: each top-level block is independently
    optional; presence of one is sufficient for a non-None return.
    """
    case_dir = _write_shm(
        tmp_path,
        """geometry { my_part.stl { type triSurfaceMesh; name my_part; } }
        """,
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    assert list(result.keys()) == ["geometry"]
    assert result["geometry"] == {
        "my_part.stl": {"type": "triSurfaceMesh", "name": "my_part"}
    }


def test_comment_stripping_handles_block_comments_with_braces(tmp_path: Path) -> None:
    """Block comments containing `{` `}` must be stripped before brace
    matching, else extractor may chase phantom braces from comment text.
    """
    case_dir = _write_shm(
        tmp_path,
        """/* This comment has { braces } { inside it } */
        geometry { real_part { type triSurfaceMesh; } }
        """,
    )
    result = extract_shm_dict(case_dir)
    assert result is not None
    assert result["geometry"] == {"real_part": {"type": "triSurfaceMesh"}}


# =====================================================================
# Cross-extractor packaging — `extract_shm_dict` IS the package re-export.
# =====================================================================
def test_extract_shm_dict_is_module_extract() -> None:
    """`case_extractors.extract_shm_dict` must be the same callable as
    `case_extractors.shm_dict_extractor.extract` (re-export only, not
    a wrapper that silently transforms output).
    """
    from ui.backend.services.case_extractors import (
        extract_shm_dict,
        shm_dict_extractor,
    )
    assert extract_shm_dict is shm_dict_extractor.extract


def test_extractor_module_loads_without_trimesh() -> None:
    """The extractor module must import cleanly in an environment WITHOUT
    `trimesh` available.

    DEC-V61-212 §"Architectural placement" requires stdlib-only — the
    same trimesh-transitive trap DEC-211 R0 P1 hit (via
    `geometry_ingest/__init__.py → health_check → import trimesh`)
    would silently fail here too if a future refactor sneaks an
    upstream import in.

    Subprocess isolation (instead of sys.modules introspection inside
    the test session, which is polluted by sibling e2e tests'
    `pytest.importorskip("trimesh")`): a fresh interpreter is started
    with `sys.modules['trimesh']=None` BEFORE any other import; the
    extractor module is then imported. If any transitive import of
    trimesh exists, the import fails with `ImportError` — the test
    asserts it does NOT.

    Mirrors DEC-211's `test_extractor_module_loads_without_trimesh`
    contract verbatim.
    """
    import subprocess

    repo_root = Path(__file__).resolve().parents[1]
    code = (
        "import sys\n"
        # Block trimesh BEFORE the extractor's import chain runs.
        "sys.modules['trimesh'] = None\n"
        "from ui.backend.services.case_extractors import shm_dict_extractor\n"
        "from ui.backend.services.case_extractors import extract_shm_dict\n"
        # Smoke-call the extractor on a non-existent dir → None (no I/O).
        "from pathlib import Path\n"
        "assert extract_shm_dict(Path('/nonexistent/case/dir')) is None\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"extractor import failed with trimesh blocked. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "OK" in result.stdout, (
        f"extractor smoke call failed silently. stdout={result.stdout!r}"
    )


def test_pure_function_no_writes(tmp_path: Path) -> None:
    """Extractor must not write to disk. Build a case_dir, snapshot mtime
    of the parent + system + the dict file, run extract, re-snapshot.
    All three must be unchanged (no side-effects).
    """
    case_dir = _write_shm(
        tmp_path,
        "geometry { my_part { type triSurfaceMesh; } }",
    )
    sys_dir = case_dir / "system"
    shm_file = sys_dir / "snappyHexMeshDict"
    snapshots = {
        p: (p.stat().st_mtime_ns, p.stat().st_size)
        for p in (case_dir, sys_dir, shm_file)
    }
    extract_shm_dict(case_dir)
    for p, (mt, sz) in snapshots.items():
        post_mt = p.stat().st_mtime_ns
        post_sz = p.stat().st_size
        assert (post_mt, post_sz) == (mt, sz), (
            f"extractor mutated {p}: mtime {mt}→{post_mt} size {sz}→{post_sz}"
        )
