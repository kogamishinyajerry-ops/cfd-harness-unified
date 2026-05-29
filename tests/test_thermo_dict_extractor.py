"""Tests for `ui.backend.services.case_extractors.thermo_dict_extractor`.

Per DEC-V61-213. Two layers (mirror DEC-V61-211 test pattern):

  (A) **Cross-case structural sweep** — parametrize over the 5 hConst
      in-repo profiles that ship ``constant/thermophysicalProperties``,
      assert each yields a non-None snapshot with the expected shape
      (top-level ``_mixture`` sentinel · single-species mixture body)
      and that ``ThermoModelTags.{transport, energy}`` matches the
      baseline (4 distinct tuples across 5).

  (B) **Edge-case units** — missing dir, missing required key,
      comment-buried key, duplicate key refusal, FoamFile one-liner
      header survives, sutherland-vs-const branching, eConst scope-out,
      macro refusal, ThermoModelTags companion shape, advisor
      truth-chain pin (is_clean=True on all 5 hConst profiles), live
      assemble_stack case-discrimination (compressible vs
      incompressible).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ui.backend.services.case_extractors import extract_thermo_dict_snapshot
from ui.backend.services.case_extractors.thermo_dict_extractor import (
    ThermoModelTags,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = REPO_ROOT / ".planning" / "case_profiles"

# Baseline ThermoModelTags mapping for the 5 hConst in-repo profiles.
# Verified 2026-05-28 by reading each file end-to-end (DEC-V61-213
# §"Why thermo_dict v0.1 has real discrimination"). 4 distinct
# (transport, energy) tuples across 5 profiles — that IS the case-
# discrimination signal.
#
# The 6th in-repo file (case_006_v64_val_full_2/_v24_rhocentralfoam_fallback)
# uses eConst → v0.1 scope-out, returns None — tested separately.
_HCONST_BASELINE: dict[str, dict[str, str]] = {
    "case_006_v64_thermo_fpe_fix_dicts": {
        "type": "hePsiThermo",
        "mixture": "pureMixture",
        "transport": "sutherland",
        "thermo": "hConst",
        "equation_of_state": "perfectGas",
        "energy": "sensibleEnthalpy",
    },
    "case_006_v64_val_full_2_dicts": {
        "type": "hePsiThermo",
        "mixture": "pureMixture",
        "transport": "const",
        "thermo": "hConst",
        "equation_of_state": "perfectGas",
        "energy": "sensibleEnthalpy",
    },
    "case_016_v64_thermo_fpe_fix_dicts": {
        "type": "hePsiThermo",
        "mixture": "pureMixture",
        "transport": "sutherland",
        "thermo": "hConst",
        "equation_of_state": "perfectGas",
        "energy": "sensibleInternalEnergy",
    },
    "case_030_v65_wedge15ma5_v106_2nd_witness_dicts": {
        "type": "hePsiThermo",
        "mixture": "pureMixture",
        "transport": "const",
        "thermo": "hConst",
        "equation_of_state": "perfectGas",
        "energy": "sensibleInternalEnergy",
    },
    "case_031_v65_naca0012_supersonic_v106_retry_dicts": {
        "type": "hePsiThermo",
        "mixture": "pureMixture",
        "transport": "sutherland",
        "thermo": "hConst",
        "equation_of_state": "perfectGas",
        "energy": "sensibleInternalEnergy",
    },
}

# Baseline mixture.specie.molWeight for the 5 hConst profiles
# (verified by direct grep of `molWeight` lines, 2026-05-28).
_HCONST_MOLWEIGHT: dict[str, float] = {
    "case_006_v64_thermo_fpe_fix_dicts": 28.96,
    "case_006_v64_val_full_2_dicts": 28.96,
    "case_016_v64_thermo_fpe_fix_dicts": 28.96,
    "case_030_v65_wedge15ma5_v106_2nd_witness_dicts": 11640.3,
    "case_031_v65_naca0012_supersonic_v106_retry_dicts": 28.9,
}

# The single in-repo eConst profile (v0.1 scope-out).
_ECONST_PROFILE_REL = (
    "case_006_v64_val_full_2_dicts/_v24_rhocentralfoam_fallback"
)


# ---- (A) cross-case structural sweep --------------------------------


@pytest.mark.parametrize("profile", sorted(_HCONST_BASELINE.keys()))
def test_extractor_returns_expected_shape_per_profile(profile: str) -> None:
    """Every hConst in-repo profile yields a (snapshot, tags) tuple with:
      - non-None snapshot whose single top-level key is the `_mixture`
        sentinel (DEC-V61-213 §Truth-chain R1),
      - `snap['_mixture']['specie']['molWeight']` is a float matching
        the baseline,
      - `snap['_mixture']['thermodynamics']['Cp']` is a float, `Hf` is
        present (all 5 profiles emit `Hf 0;` literally),
      - `Tlow` is INTENTIONALLY ABSENT from `thermodynamics` (truth-chain
        R2 — hConst has no polynomial range; advisor's species_tlows
        census stays empty ⇒ paths (a)/(b)/(c) vacuously pass ⇒
        `is_clean=True`),
      - `ThermoModelTags` matches the baseline mapping.

    If this fails on a baseline-listed profile: either the extractor
    regressed or the profile's thermo file was rewritten (truth-chain
    check — investigate which).
    """
    case_dir = PROFILES_DIR / profile
    if not case_dir.is_dir():
        pytest.skip(f"profile dir missing: {profile}")

    result = extract_thermo_dict_snapshot(case_dir)
    assert result is not None, (
        f"{profile}: extractor returned None, expected snapshot"
    )
    snap, tags = result

    # Top-level shape — single synthetic species key.
    assert list(snap.keys()) == ["_mixture"], (
        f"{profile}: snapshot top-level keys = {list(snap.keys())}, "
        f"expected ['_mixture']"
    )

    mix = snap["_mixture"]
    assert isinstance(mix, dict)
    assert set(mix.keys()) == {"specie", "thermodynamics", "transport"}, (
        f"{profile}: mixture body keys = {sorted(mix.keys())}, "
        f"expected {{specie, thermodynamics, transport}}"
    )

    # specie.molWeight present and matches baseline.
    assert "molWeight" in mix["specie"]
    assert mix["specie"]["molWeight"] == pytest.approx(_HCONST_MOLWEIGHT[profile])
    assert isinstance(mix["specie"]["molWeight"], float)

    # thermodynamics.Cp present and Hf present (all 5 profiles ship Hf 0;);
    # Tlow MUST be absent (truth-chain R2).
    assert "Cp" in mix["thermodynamics"]
    assert isinstance(mix["thermodynamics"]["Cp"], float)
    assert "Hf" in mix["thermodynamics"]
    assert isinstance(mix["thermodynamics"]["Hf"], float)
    assert "Tlow" not in mix["thermodynamics"], (
        f"{profile}: Tlow leaked into output — extractor must not "
        f"synthesize Tlow under hConst (DEC-V61-213 §R2)"
    )

    # ThermoModelTags companion matches baseline.
    expected = _HCONST_BASELINE[profile]
    assert tags == ThermoModelTags(**expected), (
        f"{profile}: tags = {tags!r}, expected ThermoModelTags(**{expected!r})"
    )


def test_extractor_covers_all_in_repo_hconst_profiles() -> None:
    """Canary: every profile that ships ``constant/thermophysicalProperties``
    AND uses ``thermo hConst`` is covered by the baseline. Catches silent
    drift if a new profile is added (would otherwise pass invisibly because
    parametrize only iterates the baseline).

    Profiles using ``thermo eConst`` (out-of-v0.1-scope) are tolerated in
    the on-disk set but excluded from the baseline; they are exercised by
    `test_econst_profile_returns_none` below.
    """
    if not PROFILES_DIR.is_dir():
        pytest.skip("case_profiles dir missing")
    on_disk_thermo_files = list(
        PROFILES_DIR.glob("*/constant/thermophysicalProperties")
    )
    # Filter to hConst by content-check (cheap stdlib check — avoids
    # invoking the extractor itself, which would create a circular
    # canary).
    hconst_on_disk: set[str] = set()
    for p in on_disk_thermo_files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "thermo" in text and "hConst" in text and "eConst" not in text:
            hconst_on_disk.add(p.parent.parent.name)

    listed = set(_HCONST_BASELINE.keys())
    missing = hconst_on_disk - listed
    assert not missing, (
        f"new hConst case_profiles not in baseline: {sorted(missing)} "
        f"— add to _HCONST_BASELINE after grep-verifying their thermoType tokens"
    )


def test_econst_profile_returns_none() -> None:
    """The single in-repo eConst profile is v0.1 scope-out → None.

    Pins the docstring §NON-features contract: ``thermo == eConst``
    causes the extractor to refuse a snapshot rather than emit Cv as
    Cp (which would be silent fabrication). If a future regression
    accidentally starts emitting eConst as hConst, this test breaks.
    """
    case_dir = PROFILES_DIR / _ECONST_PROFILE_REL
    if not (case_dir / "constant" / "thermophysicalProperties").is_file():
        pytest.skip(f"eConst profile missing: {_ECONST_PROFILE_REL}")
    result = extract_thermo_dict_snapshot(case_dir)
    assert result is None, (
        f"eConst profile must return None (v0.1 scope-out); got {result!r}"
    )


def test_distinct_transport_energy_tuples_count() -> None:
    """Pin the case-discrimination guarantee that motivated DEC-V61-213.

    The 5 hConst profiles split into 4 distinct ``(transport, energy)``
    tuples — that IS the differentiation signal the eval depends on.
    If this drops to 3 or rises to 5, a profile gained/lost a
    transport-energy combination, or a new profile was added without
    baseline updates. Either is a truth-chain alert.
    """
    tuples = {
        (b["transport"], b["energy"]) for b in _HCONST_BASELINE.values()
    }
    assert len(tuples) == 4, (
        f"distinct (transport, energy) tuple count = {len(tuples)}, "
        f"expected 4 (per DEC-V61-213 discrimination table). "
        f"Got tuples = {sorted(tuples)}"
    )


# ---- (B) edge-case units --------------------------------------------


def test_missing_constant_dir_returns_none(tmp_path: Path) -> None:
    """No `constant/` dir at all → None."""
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_missing_thermophysicalproperties_returns_none(tmp_path: Path) -> None:
    """`constant/` exists but no `thermophysicalProperties` file → None."""
    (tmp_path / "constant").mkdir()
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_nonexistent_case_dir_returns_none(tmp_path: Path) -> None:
    """A path that doesn't exist at all → None (no exception)."""
    assert extract_thermo_dict_snapshot(tmp_path / "nonexistent") is None


def test_no_thermotype_block_returns_none(tmp_path: Path) -> None:
    """File exists with FoamFile but no thermoType block → None.

    Pin: structurally-required blocks gate the snapshot per
    DEC-V61-213 §Honest-omission contract.
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "FoamFile { version 2.0; }\n"
        "mixture { specie { molWeight 28.96; } }\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_no_mixture_block_returns_none(tmp_path: Path) -> None:
    """File has thermoType but no mixture block → None."""
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "FoamFile { version 2.0; }\n"
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def _write_canonical_hconst_sutherland(case_dir: Path, mw: str = "28.96") -> None:
    """Helper: write a minimal canonical hConst+sutherland thermo file."""
    (case_dir / "constant").mkdir()
    (case_dir / "constant" / "thermophysicalProperties").write_text(
        "FoamFile { version 2.0; format ascii; class dictionary; "
        'location "constant"; object thermophysicalProperties; }\n'
        "\n"
        "thermoType\n"
        "{\n"
        "    type            hePsiThermo;\n"
        "    mixture         pureMixture;\n"
        "    transport       sutherland;\n"
        "    thermo          hConst;\n"
        "    equationOfState perfectGas;\n"
        "    specie          specie;\n"
        "    energy          sensibleEnthalpy;\n"
        "}\n"
        "\n"
        "mixture\n"
        "{\n"
        "    specie\n"
        "    {\n"
        f"        molWeight   {mw};\n"
        "    }\n"
        "    thermodynamics\n"
        "    {\n"
        "        Cp          1004.5;\n"
        "        Hf          0;\n"
        "    }\n"
        "    transport\n"
        "    {\n"
        "        As          1.458e-06;\n"
        "        Ts          110.4;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )


def test_missing_molweight_returns_none(tmp_path: Path) -> None:
    """Source has thermoType + mixture but specie block omits molWeight.

    Pin: DEC-V61-213 §Honest-omission — `mixture.specie.molWeight` is
    REQUIRED; absent or unparseable ⇒ snapshot None (never half-built).
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_commented_molweight_does_not_false_match(tmp_path: Path) -> None:
    """A `//`-commented `molWeight 99.0;` line must NOT poison the real
    `molWeight 28.96;` line read.

    Pin `_strip_comments` correctness. The extracted molWeight must be
    28.96, not 99.0.
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie {\n"
        "    // molWeight 99.0;   // previous experimental value\n"
        "    molWeight 28.96;\n"
        "  }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    result = extract_thermo_dict_snapshot(tmp_path)
    assert result is not None
    snap, _tags = result
    assert snap["_mixture"]["specie"]["molWeight"] == pytest.approx(28.96)


def test_block_commented_molweight_does_not_false_match(tmp_path: Path) -> None:
    """A `/* ... */` block comment hiding a fake molWeight must not
    poison the real value (mirror solver_block_extractor pattern).
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie {\n"
        "    /* multi-line\n"
        "       molWeight 99.0;\n"
        "       was the experimental value */\n"
        "    molWeight 28.96;\n"
        "  }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    result = extract_thermo_dict_snapshot(tmp_path)
    assert result is not None
    snap, _tags = result
    assert snap["_mixture"]["specie"]["molWeight"] == pytest.approx(28.96)


def test_foamfile_oneline_header_survives(tmp_path: Path) -> None:
    """One-line `FoamFile { … object thermophysicalProperties; }` headers
    (mirror case_006_v64_thermo_fpe_fix:11) must not false-match the
    paired-brace scan looking for `thermoType { … }` / `mixture { … }`.

    Pin DEC-V61-213 §Truth-chain R3: the paired-brace scan correctly
    identifies the top-level `thermoType`/`mixture` blocks and does NOT
    confuse them with the FoamFile one-liner's braces.
    """
    _write_canonical_hconst_sutherland(tmp_path)
    result = extract_thermo_dict_snapshot(tmp_path)
    assert result is not None
    snap, tags = result
    assert snap["_mixture"]["specie"]["molWeight"] == pytest.approx(28.96)
    assert tags.transport == "sutherland"
    assert tags.thermo == "hConst"


def test_duplicate_molweight_returns_none(tmp_path: Path) -> None:
    """Two `molWeight` lines inside specie block → snapshot None.

    Pin architecture invariant #4 (duplicate-key refusal). Silently
    picking the first match when the source is ambiguous would
    violate the truth-chain contract just like fabricating from
    macros did.
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie {\n"
        "    molWeight 28.96;\n"
        "    molWeight 28.97;\n"
        "  }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_duplicate_thermotype_returns_none(tmp_path: Path) -> None:
    """Two top-level `thermoType { … }` blocks → snapshot None."""
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport const;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_sutherland_emits_As_Ts_not_mu_Pr(tmp_path: Path) -> None:
    """transport=sutherland → snap.transport has {As, Ts} only."""
    _write_canonical_hconst_sutherland(tmp_path)
    result = extract_thermo_dict_snapshot(tmp_path)
    assert result is not None
    snap, _tags = result
    transport = snap["_mixture"]["transport"]
    assert set(transport.keys()) == {"As", "Ts"}
    assert transport["As"] == pytest.approx(1.458e-06)
    assert transport["Ts"] == pytest.approx(110.4)


def test_const_emits_mu_Pr_not_As_Ts(tmp_path: Path) -> None:
    """transport=const → snap.transport has {mu, Pr} only."""
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport const;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { mu 1.79e-5; Pr 0.71; }\n"
        "}\n",
        encoding="utf-8",
    )
    result = extract_thermo_dict_snapshot(tmp_path)
    assert result is not None
    snap, _tags = result
    transport = snap["_mixture"]["transport"]
    assert set(transport.keys()) == {"mu", "Pr"}
    assert transport["mu"] == pytest.approx(1.79e-5)
    assert transport["Pr"] == pytest.approx(0.71)


def test_partial_sutherland_returns_none(tmp_path: Path) -> None:
    """transport=sutherland but only `As` (no `Ts`) → snapshot None.

    Honest refusal — partial sutherland is a fabrication risk
    (DEC-V61-213 §scope-out: "either absent ⇒ snapshot None").
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { As 1.458e-06; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_partial_const_returns_none(tmp_path: Path) -> None:
    """transport=const but only `mu` (no `Pr`) → snapshot None."""
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport const;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { mu 1.79e-5; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_macro_molweight_returns_none(tmp_path: Path) -> None:
    """`molWeight $molWeight;` (macro substitution) is v0.1 scope-out.

    The numeric value regex won't match `$molWeight`, so `_parse_float`
    returns None ⇒ snapshot None. Pin: macro substitution is honest
    refusal, not fabrication (mirror DEC-V61-211 macro scope-out).
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight $molWeight; }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_tlow_intentionally_absent_under_hconst(tmp_path: Path) -> None:
    """Even if source happens to contain a `Tlow` line under hConst (it
    shouldn't, but a copy-paste experiment might leave one), the v0.1
    extractor does NOT extract it — hConst has no polynomial range.

    The truth is "this case uses hConst, there is no per-species
    polynomial Tlow"; the advisor's species_tlows census must remain
    empty so paths (a)/(b)/(c) vacuously pass. Pin DEC-V61-213 §R2.
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics {\n"
        "    Cp 1004.5;\n"
        "    Hf 0;\n"
        "    Tlow 250;   // stray copy-paste from a janaf experiment\n"
        "  }\n"
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    result = extract_thermo_dict_snapshot(tmp_path)
    assert result is not None
    snap, _tags = result
    assert "Tlow" not in snap["_mixture"]["thermodynamics"], (
        "extractor leaked stray Tlow into output; DEC-V61-213 §R2 "
        "forbids any Tlow emission under hConst"
    )


def test_unknown_transport_kind_returns_none(tmp_path: Path) -> None:
    """transport=polynomial (or any non-{sutherland,const}) → None.

    Pin v0.1 scope-out: polynomial / logPolynomial / icoTabulated /
    icoPolynomial etc. are documented NON-features.
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport polynomial;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { muCoeffs ( 1 0 0 0 0 0 0 0 ); }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_thermo_model_tags_is_frozen_dataclass() -> None:
    """ThermoModelTags is frozen — immutability pin (mirror DEC-V61-211)."""
    import dataclasses
    tags = ThermoModelTags(
        type="hePsiThermo",
        mixture="pureMixture",
        transport="sutherland",
        thermo="hConst",
        equation_of_state="perfectGas",
        energy="sensibleEnthalpy",
    )
    assert dataclasses.is_dataclass(tags)
    with pytest.raises(dataclasses.FrozenInstanceError):
        tags.type = "heRhoThermo"  # type: ignore[misc]


# ---- (B) advisor truth-chain pin ------------------------------------


@pytest.mark.parametrize("profile", sorted(_HCONST_BASELINE.keys()))
def test_advisor_returns_is_clean_for_all_hconst_profiles(profile: str) -> None:
    """DEC-V61-213 acceptance #4 — the critical truth-chain pin.

    For each of the 5 hConst profiles, feed the extracted snapshot
    directly into ``check_thermo_polynomial_range(snap, None)`` and
    assert:
      - ``report.findings == ()`` — no fabricated findings,
      - ``report.species_coverage.total_species_with_tlow == 0`` — the
        census is empty (Tlow absent under hConst is the truth).

    Lazy-imported under ``pytest.importorskip("trimesh")`` to keep
    module-load stdlib-only (the extractor itself does not import
    trimesh — the advisor does via geometry_ingest/__init__.py).
    """
    pytest.importorskip("trimesh")
    from ui.backend.services.geometry_ingest.thermo_polynomial_range_advisor import (
        check_thermo_polynomial_range,
    )

    case_dir = PROFILES_DIR / profile
    if not case_dir.is_dir():
        pytest.skip(f"profile dir missing: {profile}")
    result = extract_thermo_dict_snapshot(case_dir)
    assert result is not None
    snap, _tags = result

    report = check_thermo_polynomial_range(dict(snap), None)
    assert report.findings == (), (
        f"{profile}: advisor emitted findings on hConst input — "
        f"truth-chain violation. Findings: {report.findings}"
    )
    assert report.species_coverage.total_species_with_tlow == 0, (
        f"{profile}: species_tlows census non-empty "
        f"({report.species_coverage.total_species_with_tlow}); "
        f"expected 0 (no Tlow under hConst)"
    )
    assert report.is_clean is True


def test_assemble_stack_discriminates_compressible_vs_incompressible() -> None:
    """DEC-V61-213 acceptance #5 — live case-discrimination proof.

    case_006_v64_thermo_fpe_fix (compressible) ships thermo file →
    extract returns non-None → assemble_stack with thermo_dict=snap
    dispatches `thermo_polynomial_range_advisor`.

    case_021_v64_val_full_3_incomp (incompressible) ships NO thermo
    file → extract returns None → assemble_stack receives
    thermo_dict=None → `thermo_polynomial_range_advisor` NOT in the
    dispatched set.

    Skip if trimesh missing (advisor's transitive import chain).
    """
    pytest.importorskip("trimesh")
    from ui.backend.services.advisor_stack import assemble_stack

    # Compressible case — extract should yield a snapshot.
    comp_case = PROFILES_DIR / "case_006_v64_thermo_fpe_fix_dicts"
    if not comp_case.is_dir():
        pytest.skip("case_006_v64_thermo_fpe_fix_dicts missing")
    comp_result = extract_thermo_dict_snapshot(comp_case)
    assert comp_result is not None
    comp_snap, _comp_tags = comp_result
    report_comp = assemble_stack(thermo_dict=dict(comp_snap))
    comp_dispatched = {c.advisor_name for c in report_comp.advisor_calls}
    assert "thermo_polynomial_range_advisor" in comp_dispatched, (
        f"compressible case: thermo_polynomial_range_advisor not in "
        f"dispatched set = {sorted(comp_dispatched)}"
    )

    # Incompressible case — no thermo file, extract → None.
    incomp_case = PROFILES_DIR / "case_021_v64_val_full_3_incomp_dicts"
    if not incomp_case.is_dir():
        pytest.skip("case_021_v64_val_full_3_incomp_dicts missing")
    incomp_result = extract_thermo_dict_snapshot(incomp_case)
    assert incomp_result is None, (
        f"incompressible case: expected None from extract (no thermo "
        f"file), got {incomp_result!r}"
    )
    report_incomp = assemble_stack(thermo_dict=None)
    incomp_dispatched = {c.advisor_name for c in report_incomp.advisor_calls}
    assert "thermo_polynomial_range_advisor" not in incomp_dispatched, (
        f"incompressible case: thermo_polynomial_range_advisor unexpectedly "
        f"dispatched = {sorted(incomp_dispatched)}"
    )


# ---- (B) stdlib-only architectural promise --------------------------


def test_extractor_module_loads_without_trimesh() -> None:
    """Mirror DEC-V61-211 R0 P1 fix: the extractor module imports cleanly
    when trimesh is absent (``.[ui]`` env without ``[workbench]``).

    Pin via subprocess so the test environment's trimesh availability
    doesn't mask a real regression — the subprocess stubs ``trimesh``
    to None in ``sys.modules``, then imports the extractor and checks
    ``ThermoModelTags`` is reachable with the expected field set.
    """
    import os
    import subprocess
    import sys

    code = (
        "import sys\n"
        "sys.modules['trimesh'] = None\n"
        "from ui.backend.services.case_extractors import (\n"
        "    extract_thermo_dict_snapshot,\n"
        ")\n"
        "from ui.backend.services.case_extractors.thermo_dict_extractor "
        "import ThermoModelTags\n"
        "import dataclasses\n"
        "names = sorted(f.name for f in dataclasses.fields(ThermoModelTags))\n"
        "assert names == [\n"
        "    'energy', 'equation_of_state', 'mixture',\n"
        "    'thermo', 'transport', 'type',\n"
        "], names\n"
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


def test_return_type_is_tuple_of_mapping_and_tags(tmp_path: Path) -> None:
    """Pin the public return contract: `(Mapping[str, Any], ThermoModelTags)`.

    Defensive — a future refactor that accidentally swaps the tuple order
    or returns just the snapshot would break the eval layer silently.
    """
    _write_canonical_hconst_sutherland(tmp_path)
    result = extract_thermo_dict_snapshot(tmp_path)
    assert result is not None
    assert isinstance(result, tuple)
    assert len(result) == 2
    snap, tags = result
    assert isinstance(snap, dict)
    assert isinstance(tags, ThermoModelTags)


def test_unreadable_file_returns_none(tmp_path: Path) -> None:
    """OSError on read → None (mirror solver_block_extractor pattern).

    Simulate via a directory at the file path — read_text raises IsADirectoryError
    (a subclass of OSError) which the extractor catches.
    """
    (tmp_path / "constant").mkdir()
    # Create a DIRECTORY where the file should be — read_text will raise.
    (tmp_path / "constant" / "thermophysicalProperties").mkdir()
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_silent_tags_for_canonical_specie_token(tmp_path: Path) -> None:
    """The `specie specie;` line in thermoType is REQUIRED to construct
    ThermoModelTags even though the token value (`specie`) is invariant
    across all 6 in-repo profiles.

    Pin: dropping that line → snapshot None. (If a future profile uses
    a non-`specie` value, that's a meaningful divergence; v0.1
    requires presence + parseability but doesn't carry the value on
    the tags.)
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        # specie line intentionally omitted
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; }\n"
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_hf_optional_when_absent(tmp_path: Path) -> None:
    """`Hf` is OPTIONAL — absent ⇒ omitted from output (not key=None).

    Mirrors DEC-V61-132 truth-chain convention (omission, not
    fabrication; missing data is NOT a None-valued key).
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics { Cp 1004.5; }\n"  # no Hf
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    result = extract_thermo_dict_snapshot(tmp_path)
    assert result is not None
    snap, _tags = result
    thermo: dict[str, Any] = snap["_mixture"]["thermodynamics"]
    assert "Cp" in thermo
    assert "Hf" not in thermo  # absent in source ⇒ absent from output


def test_hf_duplicate_refuses_snapshot(tmp_path: Path) -> None:
    """Cadence Codex R1 (2026-05-30 · CRS P3) pin: when `Hf` key is
    PRESENT in source but duplicated (`Hf 0; Hf 1;`), the snapshot
    must refuse (return None) — NOT silently omit Hf as if absent.

    Pre-fix bug: `_single_match_or_none(_HF_RE, body)` returned None
    on both "Hf absent" and "Hf present but ambiguous", collapsing
    them into the same code path and emitting a snapshot with Hf
    silently omitted — hiding source ambiguity and violating the v0.1
    truth-chain/refusal contract.

    Post-fix: `_HF_KEY_PRESENCE_RE` detects the Hf key independently
    of numeric parseability; key present + value ambiguous ⇒ refuse.
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics { Cp 1004.5; Hf 0; Hf 1; }\n"  # DUPLICATE Hf — ambiguous
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None


def test_hf_macro_refuses_snapshot(tmp_path: Path) -> None:
    """Cadence Codex R1 (2026-05-30 · CRS P3) pin: when `Hf` key is
    PRESENT in source but its value is a macro (`Hf $heatOfFormation;`)
    or other unparseable form, the snapshot must refuse (return None)
    — NOT silently omit Hf as if absent. Same root cause and fix as
    test_hf_duplicate_refuses_snapshot.
    """
    (tmp_path / "constant").mkdir()
    (tmp_path / "constant" / "thermophysicalProperties").write_text(
        "thermoType {\n"
        "  type hePsiThermo;\n"
        "  mixture pureMixture;\n"
        "  transport sutherland;\n"
        "  thermo hConst;\n"
        "  equationOfState perfectGas;\n"
        "  specie specie;\n"
        "  energy sensibleEnthalpy;\n"
        "}\n"
        "mixture {\n"
        "  specie { molWeight 28.96; }\n"
        "  thermodynamics { Cp 1004.5; Hf $heatOfFormation; }\n"  # MACRO Hf
        "  transport { As 1.458e-06; Ts 110.4; }\n"
        "}\n",
        encoding="utf-8",
    )
    assert extract_thermo_dict_snapshot(tmp_path) is None
