"""RED-TEAM (adversarial pins) for ``thermo_dict_multi_region``.

Per DEC-V61-218 W3.0.2. Two core adversarial scenarios:

1. NAME-INFERENCE TRAP: region names deliberately mislead; the snapshot
   (fluid_regions / solid_regions membership) is the ONLY authoritative
   kind source. The file's thermoType.type token also does not determine kind.

2. constAnIso kappa vector in a solid region: thermo_type captured, kappa None.

These tests exercise the NAME-PATTERN-INFERENCE BAN (checklist item 4) as
the W3.0.1 circular-fixture analogue: the NAME MISLEADS; the SNAPSHOT is
authoritative.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from ui.backend.services.case_extractors import extract_thermo_dict_multi_region
from ui.backend.services.case_extractors.region_properties_reader import (
    RegionPropertiesSnapshot,
)

_FOAMFILE_HDR = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      thermophysicalProperties;
}
"""


def _snap(
    fluid: tuple[str, ...] | None,
    solid: tuple[str, ...] | None,
) -> RegionPropertiesSnapshot:
    return RegionPropertiesSnapshot(fluid_regions=fluid, solid_regions=solid)


def _write_thermo(case_dir: Path, region: str, content: str) -> None:
    d = case_dir / "constant" / region
    d.mkdir(parents=True, exist_ok=True)
    (d / "thermophysicalProperties").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# NAME-INFERENCE TRAP 1:
# Region named 'aluminum_solid' BUT is in fluid_regions of the snapshot
# AND file declares heRhoThermo → kind MUST be 'fluid' (from snapshot).
# A name-based implementation would infer 'solid' from 'aluminum_solid'.
# A thermoType-based implementation would infer 'solid' from heSolidThermo.
# ---------------------------------------------------------------------------

def test_name_says_solid_snapshot_says_fluid_kind_is_fluid(tmp_path: Path) -> None:
    """RED-TEAM: region named 'aluminum_solid' is in fluid_regions.
    File declares heRhoThermo.
    kind MUST be 'fluid' — from snapshot, not from name or thermo_type.
    """
    fluid_thermo = (
        _FOAMFILE_HDR
        + "thermoType\n"
        + "{\n"
        + "    type            heRhoThermo;\n"
        + "    mixture         pureMixture;\n"
        + "    transport       const;\n"
        + "    thermo          hConst;\n"
        + "    equationOfState perfectGas;\n"
        + "    specie          specie;\n"
        + "    energy          sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n"
        + "{\n"
        + "    specie       { molWeight 28.96; }\n"
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport    { mu 1.8e-5; Pr 0.713; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "aluminum_solid", fluid_thermo)

    # TRAP: name says "aluminum_solid" but snapshot puts it in fluid_regions
    snap = _snap(fluid=("aluminum_solid",), solid=())
    result = extract_thermo_dict_multi_region(tmp_path, snap)

    assert result is not None
    s = result["aluminum_solid"]
    assert s is not None
    assert s.kind == "fluid", (
        f"NAME-INFERENCE TRAP: kind must be 'fluid' (from snapshot), "
        f"got {s.kind!r}. Name 'aluminum_solid' must NOT influence kind."
    )
    assert s.thermo_type == "heRhoThermo"


# ---------------------------------------------------------------------------
# NAME-INFERENCE TRAP 2:
# Region named 'fluid_zone' BUT is in solid_regions of the snapshot
# AND file declares heSolidThermo → kind MUST be 'solid' (from snapshot).
# ---------------------------------------------------------------------------

def test_name_says_fluid_snapshot_says_solid_kind_is_solid(tmp_path: Path) -> None:
    """RED-TEAM: region named 'fluid_zone' is in solid_regions.
    File declares heSolidThermo.
    kind MUST be 'solid' — from snapshot, not from name or thermo_type.
    """
    solid_thermo = (
        _FOAMFILE_HDR
        + "thermoType\n"
        + "{\n"
        + "    type            heSolidThermo;\n"
        + "    mixture         pureMixture;\n"
        + "    transport       constIso;\n"
        + "    thermo          hConst;\n"
        + "    equationOfState rhoConst;\n"
        + "    specie          specie;\n"
        + "    energy          sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n"
        + "{\n"
        + "    specie         { molWeight 26.98; }\n"
        + "    thermodynamics { Cp 896.0; Hf 0; }\n"
        + "    transport      { kappa 167.0; }\n"
        + "    equationOfState { rho 2700.0; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "fluid_zone", solid_thermo)

    # TRAP: name says "fluid_zone" but snapshot puts it in solid_regions
    snap = _snap(fluid=(), solid=("fluid_zone",))
    result = extract_thermo_dict_multi_region(tmp_path, snap)

    assert result is not None
    s = result["fluid_zone"]
    assert s is not None
    assert s.kind == "solid", (
        f"NAME-INFERENCE TRAP: kind must be 'solid' (from snapshot), "
        f"got {s.kind!r}. Name 'fluid_zone' must NOT influence kind."
    )
    assert s.thermo_type == "heSolidThermo"


# ---------------------------------------------------------------------------
# NAME-INFERENCE TRAP 3 (compound):
# Combination test — two regions in same call, both names misleading.
# ---------------------------------------------------------------------------

def test_compound_name_inference_trap_both_kinds_correct(tmp_path: Path) -> None:
    """RED-TEAM: compound trap — 'water_fluid' is solid; 'steel_solid' is fluid.

    Both use names that suggest the opposite kind.  kind must match the
    snapshot in both cases — not the name.
    """
    # 'water_fluid' is in solid_regions → kind must be 'solid'
    solid_body = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heSolidThermo; mixture pureMixture; transport constIso;\n"
        + "    thermo hConst; equationOfState rhoConst; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 18.0; }\n"
        + "    thermodynamics { Cp 4182.0; Hf 0; }\n"
        + "    transport { kappa 0.6; }\n"
        + "    equationOfState { rho 998.0; }\n"
        + "}\n"
    )
    # 'steel_solid' is in fluid_regions → kind must be 'fluid'
    fluid_body = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture pureMixture; transport const;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 28.96; }\n"
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport { mu 1.8e-5; Pr 0.713; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "water_fluid", solid_body)
    _write_thermo(tmp_path, "steel_solid", fluid_body)

    snap = _snap(fluid=("steel_solid",), solid=("water_fluid",))
    result = extract_thermo_dict_multi_region(tmp_path, snap)

    assert result is not None

    water = result["water_fluid"]
    steel = result["steel_solid"]

    assert water is not None
    assert steel is not None

    assert water.kind == "solid", (
        f"'water_fluid' is in solid_regions → kind='solid'; got {water.kind!r}"
    )
    assert steel.kind == "fluid", (
        f"'steel_solid' is in fluid_regions → kind='fluid'; got {steel.kind!r}"
    )


# ---------------------------------------------------------------------------
# NAME-INFERENCE TRAP 4 (thermo_type-to-kind ban):
# A file declaring heSolidThermo in a fluid_regions region must NOT cause
# the extractor to set kind='solid' based on the type token.
# ---------------------------------------------------------------------------

def test_hesolidthermo_file_in_fluid_region_kind_is_fluid(tmp_path: Path) -> None:
    """RED-TEAM: file declares heSolidThermo but the region is in fluid_regions.
    kind must be 'fluid' — thermoType.type must NOT override snapshot membership.

    This is a mis-configured case, but the honest response is kind='fluid'
    (snapshot is authoritative); not kind='solid' (type-based inference).
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heSolidThermo; mixture pureMixture; transport constIso;\n"
        + "    thermo hConst; equationOfState rhoConst; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 47.87; }\n"
        + "    thermodynamics { Cp 520; Hf 0; }\n"
        + "    transport { kappa 21.9; }\n"
        + "    equationOfState { rho 4510.0; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "solid_file_fluid_region", content)

    # The SNAPSHOT says this region is fluid
    snap = _snap(fluid=("solid_file_fluid_region",), solid=())
    result = extract_thermo_dict_multi_region(tmp_path, snap)

    assert result is not None
    s = result["solid_file_fluid_region"]
    assert s is not None
    assert s.kind == "fluid", (
        f"thermoType.type='heSolidThermo' must NOT override snapshot: "
        f"kind should be 'fluid', got {s.kind!r}"
    )


# ---------------------------------------------------------------------------
# constAnIso pin: thermo_type captured, kappa is None
# ---------------------------------------------------------------------------

def test_constaniso_transport_thermo_type_captured_kappa_none(tmp_path: Path) -> None:
    """RED-TEAM: solid region with constAnIso (kappa vector) transport.
    thermo_type must be captured ('heSolidThermo'); kappa must be None (scope-out).
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heSolidThermo; mixture pureMixture; transport constAnIso;\n"
        + "    thermo hConst; equationOfState rhoConst; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie         { molWeight 47.87; }\n"
        + "    thermodynamics { Cp 520; Hf 0; }\n"
        # constAnIso kappa is a vector — out of v0.1 scope
        + "    transport      { kappa (5.8 5.8 10.0); }\n"
        + "    equationOfState { rho 4510.0; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "aniso_Ti", content)

    snap = _snap(fluid=(), solid=("aniso_Ti",))
    result = extract_thermo_dict_multi_region(tmp_path, snap)

    assert result is not None
    s = result["aniso_Ti"]
    assert s is not None, "constAnIso region must still produce a non-None snapshot"
    assert s.thermo_type == "heSolidThermo", (
        f"thermo_type must be captured even on constAnIso scope-out; got {s.thermo_type!r}"
    )
    assert s.kappa is None, (
        f"constAnIso kappa vector is v0.1 scope-out; kappa must be None, got {s.kappa!r}"
    )
    assert s.kind == "solid"


# ---------------------------------------------------------------------------
# Ambiguous region (both fluid and solid) → honest None for that region
# ---------------------------------------------------------------------------

def test_region_in_both_fluid_and_solid_yields_none(tmp_path: Path) -> None:
    """RED-TEAM: a region name appearing in BOTH fluid_regions and solid_regions
    is ambiguous — kind cannot be determined without name inference (BANNED).
    That region must yield None. Other regions must be unaffected.
    """
    _write_thermo(tmp_path, "ambiguous_region", (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture pureMixture; transport const;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 28.96; }\n"
        + "    thermodynamics { Cp 1005; }\n"
        + "    transport { mu 1.8e-5; Pr 0.713; }\n"
        + "}\n"
    ))
    _write_thermo(tmp_path, "clean_region", (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heSolidThermo; mixture pureMixture; transport constIso;\n"
        + "    thermo hConst; equationOfState rhoConst; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 26.98; }\n"
        + "    thermodynamics { Cp 896; }\n"
        + "    transport { kappa 167.0; }\n"
        + "    equationOfState { rho 2700.0; }\n"
        + "}\n"
    ))

    # ambiguous_region appears in BOTH tuples
    snap = _snap(
        fluid=("ambiguous_region", "clean_region"),
        solid=("ambiguous_region",),
    )
    result = extract_thermo_dict_multi_region(tmp_path, snap)

    assert result is not None
    assert result["ambiguous_region"] is None, (
        "region in both fluid and solid is ambiguous → must be None (no name inference)"
    )
    # clean_region is only in fluid_regions; it should be fine
    assert result["clean_region"] is not None
    assert result["clean_region"].kind == "fluid"


# ---------------------------------------------------------------------------
# SOLID-TRANSPORT-TYPE GATING GAP (RED-TEAM lens-1 finding, 2026-05-30)
#
# Asymmetry vs the fluid branch: _extract_transport_block (fluid) strictly
# refuses any transport_kind that is not sutherland/const, returning None.
# But _extract_solid_transport_kappa (solid) does NOT gate on
# tags.transport at all — it scrapes ANY scalar ``kappa <v>;`` regardless of
# the declared transport model. The constAnIso scope-out is enforced ONLY by
# a fragile vector-paren heuristic (_KAPPA_VECTOR_RE), not by the declared
# tags.transport token. Result: a solid file declaring an out-of-scope
# transport model (constAnIso / polynomial / ...) still gets a fabricated
# isotropic kappa scalar — attributing a constIso physics meaning the file
# author did NOT declare. These pins assert the HONEST behaviour (kappa None
# when the declared transport model is not constIso).
# ---------------------------------------------------------------------------

def test_solid_constaniso_scalar_kappa_must_be_none(tmp_path: Path) -> None:
    """RED-TEAM: solid thermoType declares ``transport constAnIso`` (the documented
    v0.1 scope-out) but the transport block carries a SCALAR kappa (file
    inconsistency / partial author edit).

    constAnIso is anisotropic — reporting a single isotropic kappa scalar for it
    fabricates a physics meaning the file did NOT declare. kappa MUST be None.
    The existing ``test_constaniso_*`` fixtures only use the VECTOR form, so the
    type-token-vs-scalar mismatch path is never exercised (circular fixture).
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heSolidThermo; mixture pureMixture; transport constAnIso;\n"
        + "    thermo hConst; equationOfState rhoConst; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 47.87; }\n"
        + "    thermodynamics { Cp 520; Hf 0; }\n"
        + "    transport { kappa 21.9; }\n"  # scalar kappa under constAnIso decl
        + "    equationOfState { rho 4510.0; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "aniso_scalar_solid", content)
    snap = _snap(fluid=(), solid=("aniso_scalar_solid",))
    result = extract_thermo_dict_multi_region(tmp_path, snap)

    assert result is not None
    s = result["aniso_scalar_solid"]
    assert s is not None
    assert s.thermo_type == "heSolidThermo"
    assert s.tags.transport == "constAnIso"
    assert s.kappa is None, (
        "constAnIso is the documented v0.1 scope-out; a scalar kappa under a "
        "constAnIso declaration must be honest None (refuse), NOT extracted as "
        f"an isotropic value. Got kappa={s.kappa!r} — FABRICATED constIso meaning."
    )


def test_solid_out_of_scope_transport_kappa_must_be_none(tmp_path: Path) -> None:
    """RED-TEAM: solid thermoType declares an out-of-scope transport model
    (``polynomial``) but the transport block carries a scalar ``kappa``.

    The fluid branch honestly refuses an out-of-scope transport (mu/Pr → None);
    the solid branch must be symmetric. kappa MUST be None when tags.transport
    is not ``constIso``.
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heSolidThermo; mixture pureMixture; transport polynomial;\n"
        + "    thermo hConst; equationOfState rhoConst; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 47.87; }\n"
        + "    thermodynamics { Cp 520; Hf 0; }\n"
        + "    transport { type polynomial; kappa 99.9; }\n"
        + "    equationOfState { rho 4510.0; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "poly_solid", content)
    snap = _snap(fluid=(), solid=("poly_solid",))
    result = extract_thermo_dict_multi_region(tmp_path, snap)

    assert result is not None
    s = result["poly_solid"]
    assert s is not None
    assert s.thermo_type == "heSolidThermo"
    assert s.tags.transport == "polynomial"
    assert s.kappa is None, (
        "out-of-scope transport model (polynomial) must yield honest kappa=None, "
        "symmetric with the fluid branch refusal. Got kappa="
        f"{s.kappa!r} — FABRICATED constIso scalar from a non-constIso model."
    )


def test_solid_partial_missing_rho_is_honest_none(tmp_path: Path) -> None:
    """RED-TEAM (honest-refusal pin): solid with kappa + cp present but NO
    equationOfState block → rho must be honest None, never fabricated; the
    snapshot is still produced (presence-vs-payload, DEC-V61-213). Pins the
    SOLID-PROPERTY no-fabrication contract that no existing test covers.
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heSolidThermo; mixture pureMixture; transport constIso;\n"
        + "    thermo hConst; equationOfState rhoConst; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 47.87; }\n"
        + "    thermodynamics { Cp 520; Hf 0; }\n"
        + "    transport { kappa 21.9; }\n"
        # NO equationOfState block → rho must be honest None
        + "}\n"
    )
    _write_thermo(tmp_path, "partial_solid", content)
    snap = _snap(fluid=(), solid=("partial_solid",))
    result = extract_thermo_dict_multi_region(tmp_path, snap)

    assert result is not None
    s = result["partial_solid"]
    assert s is not None
    assert s.kappa == pytest.approx(21.9)
    assert s.cp == pytest.approx(520.0)
    assert s.rho is None, "missing equationOfState → rho must be honest None, not fabricated"


# ---------------------------------------------------------------------------
# Codex R0 P2 carry-back (2026-05-30): v0.1 model scope-outs must REFUSE the
# region (symmetric with single-region thermo_dict_extractor), not build a
# half-populated snapshot a caller could mistake for a parsed file.
# ---------------------------------------------------------------------------

def test_econst_region_must_refuse_whole_region(tmp_path: Path) -> None:
    """RED-TEAM (Codex R0 P2#1): a fluid region declaring ``thermo eConst``
    (Cv not Cp — documented v0.1 scope-out) must yield region None, NOT a
    snapshot with mu/Pr/mol_weight populated and cp None.
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture pureMixture; transport const;\n"
        + "    thermo eConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleInternalEnergy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 28.96; }\n"
        + "    thermodynamics { Cv 717.5; Hf 0; }\n"
        + "    transport { mu 1.8e-5; Pr 0.713; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "econst_fluid", content)
    result = extract_thermo_dict_multi_region(tmp_path, _snap(fluid=("econst_fluid",), solid=()))
    assert result is not None
    assert result["econst_fluid"] is None, (
        "eConst is the documented v0.1 scope-out; the region must refuse (None), "
        "symmetric with the single-region extractor, not return a partial snapshot."
    )


def test_non_puremixture_region_must_refuse_whole_region(tmp_path: Path) -> None:
    """RED-TEAM (Codex R0 P2#1): a region declaring a non-``pureMixture`` shape
    (e.g. ``reactingMixture``) must yield region None — multi-species mechanism
    shapes are out of v0.1 scope (single-region refuses them too).
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture reactingMixture; transport const;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 28.96; }\n"
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport { mu 1.8e-5; Pr 0.713; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "reacting_fluid", content)
    result = extract_thermo_dict_multi_region(tmp_path, _snap(fluid=("reacting_fluid",), solid=()))
    assert result is not None
    assert result["reacting_fluid"] is None, (
        "non-pureMixture (reactingMixture) is out of v0.1 scope; region must "
        "refuse (None), not report a populated snapshot."
    )


def test_solid_non_rhoconst_eos_stray_rho_must_be_none(tmp_path: Path) -> None:
    """RED-TEAM (Codex R0 P2#2): a solid declaring a NON-``rhoConst`` EOS
    (``polynomial``) that nonetheless carries a stray ``rho`` key must yield
    rho=None — reporting it as a constant density fabricates a model the file
    never declared (symmetric with the constIso kappa gate). The snapshot is
    still built (kappa/cp present) — presence-vs-payload (DEC-V61-213).
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heSolidThermo; mixture pureMixture; transport constIso;\n"
        + "    thermo hConst; equationOfState polynomial; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 47.87; }\n"
        + "    thermodynamics { Cp 520; Hf 0; }\n"
        + "    transport { kappa 21.9; }\n"
        + "    equationOfState { rho 4510.0; }\n"  # stray rho under non-rhoConst EOS
        + "}\n"
    )
    _write_thermo(tmp_path, "poly_eos_solid", content)
    result = extract_thermo_dict_multi_region(tmp_path, _snap(fluid=(), solid=("poly_eos_solid",)))
    assert result is not None
    s = result["poly_eos_solid"]
    assert s is not None
    assert s.thermo_type == "heSolidThermo"
    assert s.tags.equation_of_state == "polynomial"
    assert s.kappa == pytest.approx(21.9)
    assert s.cp == pytest.approx(520.0)
    assert s.rho is None, (
        "non-rhoConst EOS with a stray rho key must yield rho=None (honest), "
        f"not a fabricated constant density. Got rho={s.rho!r}."
    )


def test_region_name_in_both_tuples_single_key_none(tmp_path: Path) -> None:
    """RED-TEAM (Codex R2 P1): a region name listed in BOTH fluid_regions and
    solid_regions must produce exactly ONE map key (de-duplicated), mapping to
    None (ambiguous kind) — never silently collapse/overwrite so the map ends up
    with fewer keys than the snapshot declared. A clean sibling stays intact.
    """
    # 'amb' appears in both tuples; 'clean' is a normal fluid region.
    clean = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture pureMixture; transport const;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie { molWeight 28.96; }\n"
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport { mu 1.8e-5; Pr 0.713; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "clean", clean)
    # 'amb' has a perfectly valid file, but its kind is undecidable (in both tuples).
    _write_thermo(tmp_path, "amb", clean)

    result = extract_thermo_dict_multi_region(
        tmp_path, _snap(fluid=("clean", "amb"), solid=("amb",))
    )
    assert result is not None
    assert set(result.keys()) == {"clean", "amb"}, (
        "a name in both tuples must de-duplicate to ONE key, not collapse a "
        f"sibling out of the map. Got keys={sorted(result.keys())!r}."
    )
    assert result["amb"] is None, (
        "ambiguous-kind region (in both fluid and solid) must map to None, not a "
        "snapshot built by guessing the kind."
    )
    assert result["clean"] is not None, "unambiguous sibling must stay intact"
    assert result["clean"].kind == "fluid"
