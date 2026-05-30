"""RED-TEAM lens-2 (NESTING-DEPTH + HONEST-REFUSAL COMPLETENESS).

Per RED-TEAM review of DEC-V61-218 W3.0.2 ``thermo_dict_multi_region``.

These tests target the recurring W3.0/W3.0.1 "line-anchored-vs-brace-depth"
defect class.  The W3.0.2 module added a ``_depth0_text`` depth-stripper and
applies it in its NEW solid helpers (``_extract_solid_transport_kappa`` /
``_extract_rho_const`` / ``_extract_hconst_thermodynamics``).  BUT the module
also REUSES three helpers from ``thermo_dict_extractor`` for leaf-scalar
extraction that DO NOT depth-strip:

  - ``_extract_thermo_model_tags``  (thermoType.type / transport / ... tokens)
  - ``_extract_specie_block``       (mixture.specie.molWeight)
  - ``_extract_transport_block``    (fluid mu/Pr OR As/Ts)

A scalar key declared ONLY inside a nested sub-block of the located block
therefore LEAKS into the parent scan via ``_single_match_or_none`` (one match
found, accepted as the parent value).  That is silent FABRICATION, not honest
refusal.

The module docstring (item 3, NESTING-DEPTH) explicitly promises a nested
sub-dict value must NOT leak to the parent.  These tests pin that promise on
the REUSED helper paths, where it is currently violated.

The honest behavior is:
  - a value present ONLY in a nested sub-block is treated as ABSENT at the
    parent scope -> field None (payload) or whole-region None (when the leaked
    value is the REQUIRED thermoType.type discriminator).

Also pins the documented #include honest-refusal contract (module docstring
lines 40-43 / 100-101: ``#include`` -> region None) which is currently violated
for a directive sitting inside an otherwise-parseable block.
"""
from __future__ import annotations

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
# LEAK 1 (most severe): thermoType.type ONLY in a nested decoy sub-block.
# The REQUIRED discriminator is fabricated from a nested block -> a fully-built
# snapshot with a leaked thermo_type / wrong branch.  Honest behavior: the
# parent thermoType has no own ``type`` token, so tags are incomplete -> region
# None (refuse).  Currently the nested ``type heSolidThermo;`` leaks.
# ---------------------------------------------------------------------------

def test_thermotype_type_only_in_nested_block_must_refuse(tmp_path: Path) -> None:
    """RED-TEAM: thermoType.type present ONLY in a nested ``decoy { type ...; }``.

    The parent thermoType body has every OTHER token but no own ``type``.
    Honest behavior: tags incomplete -> region None.  A nested-block value must
    NOT satisfy the REQUIRED discriminator (NESTING-DEPTH checklist item 3).
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    mixture pureMixture; transport const;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "    decoy { type heSolidThermo; }\n"   # nested decoy 'type'
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie       { molWeight 28.96; }\n"
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport    { mu 1.8e-5; Pr 0.713; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "leak_type", content)
    result = extract_thermo_dict_multi_region(tmp_path, _snap(fluid=("leak_type",), solid=()))

    assert result is not None
    s = result["leak_type"]
    assert s is None, (
        "thermoType.type declared ONLY in a nested sub-block must NOT satisfy "
        "the required discriminator; region must be None (nested-leak fabrication "
        f"of the discriminator). Got snapshot with thermo_type="
        f"{getattr(s, 'thermo_type', None)!r}."
    )


# ---------------------------------------------------------------------------
# LEAK 2: mixture.specie.molWeight ONLY in a nested sub-block -> fabricated.
# ---------------------------------------------------------------------------

def test_molweight_only_in_nested_specie_subblock_not_fabricated(tmp_path: Path) -> None:
    """RED-TEAM: specie body has NO own molWeight, only ``sub { molWeight 999; }``.

    Honest behavior: mol_weight is absent at the specie scope -> field None.
    Currently ``_extract_specie_block`` scans the raw specie body (no depth
    strip), single-matches the nested 999, and fabricates mol_weight=999.
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture pureMixture; transport const;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie       { sub { molWeight 999.0; } }\n"   # nested-only
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport    { mu 1.8e-5; Pr 0.713; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "leak_mw", content)
    result = extract_thermo_dict_multi_region(tmp_path, _snap(fluid=("leak_mw",), solid=()))

    assert result is not None
    s = result["leak_mw"]
    # Contract A (Codex R1): molWeight is REQUIRED (single-region symmetry).
    # Absent at specie depth-0 (only nested) → region None. The nested 999 is
    # NOT fabricated either way — the no-leak intent is preserved.
    assert s is None, (
        "molWeight present ONLY in a nested specie sub-block is absent at the "
        "required scope → region None; the nested value must NOT be used. Got "
        f"{getattr(s, 'mol_weight', None)!r}."
    )


# ---------------------------------------------------------------------------
# LEAK 3: fluid const transport mu/Pr ONLY in a nested sub-block -> fabricated.
# ---------------------------------------------------------------------------

def test_fluid_const_mu_pr_only_in_nested_transport_not_fabricated(tmp_path: Path) -> None:
    """RED-TEAM: transport body has NO own mu/Pr, only ``sub { mu 999; Pr 9; }``.

    Honest behavior: mu/Pr absent at transport scope -> mu None, pr None.
    Currently ``_extract_transport_block`` scans the raw transport body and
    fabricates mu=999, pr=9 from the nested sub-block.
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture pureMixture; transport const;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie       { molWeight 28.96; }\n"
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport    { sub { mu 999.0; Pr 9.0; } }\n"   # nested-only
        + "}\n"
    )
    _write_thermo(tmp_path, "leak_mu", content)
    result = extract_thermo_dict_multi_region(tmp_path, _snap(fluid=("leak_mu",), solid=()))

    assert result is not None
    s = result["leak_mu"]
    # Contract A (Codex R1): a complete fluid transport block is REQUIRED. mu/Pr
    # present ONLY in a nested sub-block are absent at transport depth-0 → region
    # None. The nested 999/9 are NOT fabricated — no-leak intent preserved.
    assert s is None, (
        "const transport mu/Pr present ONLY in a nested sub-block are absent at "
        "the required transport scope → region None; nested values must NOT be "
        f"used. Got mu={getattr(s, 'mu', None)!r} pr={getattr(s, 'pr', None)!r}."
    )


# ---------------------------------------------------------------------------
# LEAK 4: fluid sutherland As/Ts ONLY in a nested sub-block -> fabricated.
# ---------------------------------------------------------------------------

def test_fluid_sutherland_as_ts_only_in_nested_transport_not_fabricated(tmp_path: Path) -> None:
    """RED-TEAM: sutherland transport body has NO own As/Ts, only nested.

    Honest behavior: sutherland_as / sutherland_ts None.  Currently fabricated
    from the nested ``wrap { As ...; Ts ...; }``.
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture pureMixture; transport sutherland;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie       { molWeight 28.96; }\n"
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport    { wrap { As 9.99e-6; Ts 888.0; } }\n"   # nested-only
        + "}\n"
    )
    _write_thermo(tmp_path, "leak_suth", content)
    result = extract_thermo_dict_multi_region(tmp_path, _snap(fluid=("leak_suth",), solid=()))

    assert result is not None
    s = result["leak_suth"]
    # Contract A (Codex R1): a complete sutherland transport (As+Ts) is REQUIRED.
    # Present ONLY in a nested sub-block → absent at transport depth-0 → region
    # None. The nested values are NOT fabricated — no-leak intent preserved.
    assert s is None, (
        "sutherland As/Ts present ONLY in a nested sub-block are absent at the "
        "required transport scope → region None; nested values must NOT be used. "
        f"Got As={getattr(s, 'sutherland_as', None)!r} "
        f"Ts={getattr(s, 'sutherland_ts', None)!r}."
    )


# ---------------------------------------------------------------------------
# #include honest-refusal contract (module docstring lines 40-43 / 100-101).
# ---------------------------------------------------------------------------

def test_include_directive_inside_mixture_must_refuse_region(tmp_path: Path) -> None:
    """RED-TEAM: a ``#include`` inside the mixture block must yield region None.

    Module docstring promises ``#include`` -> honest region None (out-of-grammar).
    A directive sitting inside an otherwise-parseable block is currently SKIPPED
    silently (no regex matches the line) and the rest parses to a non-None
    snapshot -> the documented honest-refusal contract is violated.

    A reader that cannot see the included content cannot honestly claim the
    parsed values are complete; honest behavior is region None.
    """
    content = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture pureMixture; transport const;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + '    #include "extraProps.foam"\n'   # directive inside parseable block
        + "    specie       { molWeight 28.96; }\n"
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport    { mu 1.8e-5; Pr 0.713; }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "inc_region", content)
    result = extract_thermo_dict_multi_region(tmp_path, _snap(fluid=("inc_region",), solid=()))

    assert result is not None
    s = result["inc_region"]
    assert s is None, (
        "a #include directive inside the mixture block must yield region None "
        "(documented honest refusal); the included content is unseen and the "
        "extracted values cannot honestly be claimed complete. Got a non-None "
        f"snapshot with cp={getattr(s, 'cp', None)!r} mol_weight="
        f"{getattr(s, 'mol_weight', None)!r}."
    )


# ---------------------------------------------------------------------------
# Cross-region: a nested-leak region must NOT poison good regions (independence
# holds today), AND the leak region itself must refuse rather than fabricate.
# ---------------------------------------------------------------------------

def test_cross_region_nested_leak_isolated_and_refused(tmp_path: Path) -> None:
    """RED-TEAM: nested-leak region alongside a clean region.

    The clean region must stay intact (independence — currently honored).
    The leak region must NOT fabricate molWeight/As/Ts from nested sub-blocks.
    """
    good = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heSolidThermo; mixture pureMixture; transport constIso;\n"
        + "    thermo hConst; equationOfState rhoConst; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie         { molWeight 26.98; }\n"
        + "    thermodynamics { Cp 896; Hf 0; }\n"
        + "    transport      { kappa 167.0; }\n"
        + "    equationOfState { rho 2700.0; }\n"
        + "}\n"
    )
    leak = (
        _FOAMFILE_HDR
        + "thermoType\n{\n"
        + "    type heRhoThermo; mixture pureMixture; transport sutherland;\n"
        + "    thermo hConst; equationOfState perfectGas; specie specie;\n"
        + "    energy sensibleEnthalpy;\n"
        + "}\n\n"
        + "mixture\n{\n"
        + "    specie       { sub { molWeight 12345.0; } }\n"
        + "    thermodynamics { Cp 1005; Hf 0; }\n"
        + "    transport    { wrap { As 9.9e-6; Ts 777.0; } }\n"
        + "}\n"
    )
    _write_thermo(tmp_path, "good_solid", good)
    _write_thermo(tmp_path, "leak_fluid", leak)

    result = extract_thermo_dict_multi_region(
        tmp_path, _snap(fluid=("leak_fluid",), solid=("good_solid",))
    )
    assert result is not None

    gs = result["good_solid"]
    assert gs is not None
    assert gs.kappa == 167.0 and gs.mol_weight == 26.98, (
        "clean region must stay intact (cross-region independence): "
        f"kappa={gs.kappa!r} mol_weight={gs.mol_weight!r}"
    )

    # Contract A (Codex R1): leak_fluid has molWeight + sutherland As/Ts ONLY in
    # nested sub-blocks → both required scopes empty → region None. The nested
    # 12345 / 9.9e-6 / 777 are NOT fabricated. Crucially good_solid is unaffected
    # (the whole point: a malformed region does not poison its siblings).
    lf = result["leak_fluid"]
    assert lf is None, (
        "leak_fluid (nested-only molWeight + nested-only transport) must refuse "
        f"to region None, not fabricate from nested sub-blocks. Got "
        f"mol_weight={getattr(lf, 'mol_weight', None)!r} "
        f"As={getattr(lf, 'sutherland_as', None)!r} "
        f"Ts={getattr(lf, 'sutherland_ts', None)!r}."
    )
