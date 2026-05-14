"""Tests for ``geometry_ingest.bc_type_name_validity_advisor`` (D10).

Coverage (mirrors the D6 ``test_extra_body_advisor`` pattern · ≥ 8 tests):

  1.  ``test_known_standard_bc_passes`` — fixedValue / inletOutlet / wall / wallFunctions
  2.  ``test_foam_extend_only_bc_flagged_under_main_fork`` — case_006 V29 evidence rows
  3.  ``test_foam_extend_only_bc_tolerant_under_foam_extend_fork`` — fork-aware
  4.  ``test_unknown_typo_bc_flagged`` — ``fixedValeu`` typo → warning
  5.  ``test_empty_bc_specs_returns_empty_findings`` — trivially clean
  6.  ``test_sentinel_bc_names_pass`` — ``none_volume_reference`` not flagged
  7.  ``test_extract_bc_specs_from_parts_manifest_adapter`` — pipeline glue
  8.  ``test_case_006_v29_regression`` — full 6-declaration ground-truth replay
  9.  ``test_4q_gate_no_llm_imports`` — advisor source contains zero LLM tokens
 10.  ``test_4q_gate_no_case_dir_writes`` — advisor never touches the filesystem
 11.  ``test_invalid_input_types_handled_defensively``
 12.  ``test_fork_unknown_treats_foam_extend_as_warning`` — third fork branch
"""
from __future__ import annotations

import inspect
import io
import sys

import pytest

from ui.backend.services.geometry_ingest import bc_type_name_validity_advisor as mod
from ui.backend.services.geometry_ingest.bc_type_name_validity_advisor import (
    BcTypeNameReport,
    FOAM_EXTEND_ONLY_BCS,
    SENTINEL_BC_NAMES,
    STANDARD_OPENFOAM_BCS,
    ValidityVerdict,
    check_bc_type_name_validity,
    detect_invalid_bc_types,
    extract_bc_specs_from_parts_manifest,
)


# ---- 1. Standard BC names pass cleanly ------------------------------------


def test_known_standard_bc_passes() -> None:
    for name in (
        "fixedValue",
        "zeroGradient",
        "inletOutlet",
        "noSlip",
        "freestream",
        "kqRWallFunction",
        "omegaWallFunction",
        "nutUSpaldingWallFunction",
        "compressible::turbulentTemperatureCoupledBaffleMixed",
    ):
        verdict = check_bc_type_name_validity(name)
        assert verdict.verdict == "valid_standard", name
        assert verdict.severity == "pass", name
        assert verdict.suggested_fix is None, name

    bc_specs = [
        {
            "part_name": "wing_main",
            "fields": {
                "U": "noSlip",
                "p": "zeroGradient",
                "T": "zeroGradient",
                "nut": "nutUSpaldingWallFunction",
                "k": "kqRWallFunction",
                "omega": "omegaWallFunction",
            },
        }
    ]
    report = detect_invalid_bc_types(bc_specs)
    assert isinstance(report, BcTypeNameReport)
    assert report.is_clean
    assert report.findings == ()
    assert report.checked_count == 6
    assert report.parts_examined == 1
    assert report.critical_count == 0
    assert report.warning_count == 0


# ---- 2. Foam-extend-only BC names flagged critical under fork='main' -----


def test_foam_extend_only_bc_flagged_under_main_fork() -> None:
    # V29 evidence — case_006 farfield_inlet bc block
    bc_specs = [
        {
            "part_name": "farfield_inlet",
            "fields": {
                "U": "characteristicVelocityInletOutletVelocity",
                "p": "characteristicPressureInletOutletPressure",
                "T": "freestream",  # this one IS valid in ESI
            },
        }
    ]
    report = detect_invalid_bc_types(bc_specs, fork="main")
    assert not report.is_clean
    # 2 critical (U + p), T is freestream which is valid_standard
    assert report.critical_count == 2
    assert report.warning_count == 0
    fields_flagged = {f.field_name for f in report.findings}
    assert fields_flagged == {"U", "p"}
    for f in report.findings:
        assert f.verdict == "valid_foam_extend_only"
        assert f.severity == "critical"
        assert f.fork == "main"
        assert f.suggested_fix is not None
        # The advisor must surface the V29 ESI-fix hint
        assert "freestream" in f.suggested_fix or "waveTransmissive" in f.suggested_fix
        assert "V29" in f.suggested_fix or "freestream" in f.suggested_fix


# ---- 3. Tolerant on foam-extend fork -------------------------------------


def test_foam_extend_only_bc_tolerant_under_foam_extend_fork() -> None:
    """On a foam-extend fork, these BC names ARE valid; advisor must
    pass them as ``info`` (filtered out of findings, mirroring A5)."""
    bc_specs = [
        {
            "part_name": "farfield_inlet",
            "fields": {
                "U": "characteristicVelocityInletOutletVelocity",
                "p": "characteristicPressureInletOutletPressure",
            },
        }
    ]
    report = detect_invalid_bc_types(bc_specs, fork="foam-extend")
    assert report.is_clean
    assert report.findings == ()
    assert report.checked_count == 2
    assert report.fork == "foam-extend"


# ---- 4. Unknown / typo names emit warnings -------------------------------


def test_unknown_typo_bc_flagged() -> None:
    bc_specs = [
        {
            "part_name": "inlet_patch",
            "fields": {
                "U": "fixedValeu",      # typo
                "p": "totaIPressure",   # typo (capital-I instead of l)
            },
        }
    ]
    report = detect_invalid_bc_types(bc_specs)
    assert not report.is_clean
    assert report.critical_count == 0
    assert report.warning_count == 2
    for f in report.findings:
        assert f.verdict == "unknown"
        assert f.severity == "warning"
        assert f.suggested_fix is not None
        assert "not in the advisor's catalog" in f.suggested_fix


# ---- 5. Empty input ------------------------------------------------------


def test_empty_bc_specs_returns_empty_findings() -> None:
    report = detect_invalid_bc_types([])
    assert isinstance(report, BcTypeNameReport)
    assert report.is_clean
    assert report.findings == ()
    assert report.checked_count == 0
    assert report.parts_examined == 0


# ---- 6. Sentinel BC names pass silently ----------------------------------


def test_sentinel_bc_names_pass() -> None:
    # case_006 farfield_reference body declares this sentinel.
    bc_specs = [
        {
            "part_name": "farfield_reference",
            "fields": {
                "U": "none_volume_reference",
                "p": "none_volume_reference",
                "T": "none_volume_reference",
            },
        }
    ]
    report = detect_invalid_bc_types(bc_specs)
    assert report.is_clean
    assert report.findings == ()
    # Sentinel verdicts at the per-name level are info, not warning
    for name in ("none", "none_volume_reference", "n/a", "na", "placeholder"):
        v = check_bc_type_name_validity(name)
        assert v.verdict == "valid_sentinel", name
        assert v.severity == "info", name


# ---- 7. parts_manifest adapter ------------------------------------------


def test_extract_bc_specs_from_parts_manifest_adapter() -> None:
    manifest = {
        "parts": [
            {
                "name": "wing_main",
                "role": "solid_wall",
                "bc": {"U": "noSlip", "p": "zeroGradient"},
            },
            {
                "name": "farfield_inlet",
                "role": "farfield",
                "bc": {
                    "U": "characteristicVelocityInletOutletVelocity",
                    "p": "characteristicPressureInletOutletPressure",
                },
            },
            # Part with no bc: block — must be silently skipped
            {"name": "no_bc_part", "role": "construction_helper"},
            # Malformed entry — must not crash the extractor
            "not a dict",
        ]
    }
    bc_specs = extract_bc_specs_from_parts_manifest(manifest)
    assert len(bc_specs) == 2
    names = {s["part_name"] for s in bc_specs}
    assert names == {"wing_main", "farfield_inlet"}
    # End-to-end through the adapter
    report = detect_invalid_bc_types(bc_specs)
    assert report.critical_count == 2  # the two characteristic* on farfield_inlet
    assert report.parts_examined == 2


# ---- 8. case_006 V29 ground-truth regression ----------------------------


def test_case_006_v29_regression() -> None:
    """Ground-truth replay of the case_006 ONERA M6 6-declaration
    failure surfaced by M-STACK-TRACK-3 §gap2 (canonical V29 evidence).

    Three farfield parts each declare ``U: characteristicVelocityInletOutletVelocity``
    + ``p: characteristicPressureInletOutletPressure``. The stack
    previously silently passed all six; D10 must flag all six as
    critical when fork='main' (project default ESI v2312 image).
    """
    parts_manifest = {
        "parts": [
            {
                "name": "farfield_inlet",
                "role": "farfield",
                "bc": {
                    "U": "characteristicVelocityInletOutletVelocity",
                    "p": "characteristicPressureInletOutletPressure",
                    "T": "freestream",
                },
            },
            {
                "name": "farfield_outlet",
                "role": "farfield",
                "bc": {
                    "U": "characteristicVelocityInletOutletVelocity",
                    "p": "characteristicPressureInletOutletPressure",
                    "T": "freestream",
                },
            },
            {
                "name": "farfield_lateral",
                "role": "farfield",
                "bc": {
                    "U": "characteristicVelocityInletOutletVelocity",
                    "p": "characteristicPressureInletOutletPressure",
                    "T": "freestream",
                },
            },
        ]
    }
    bc_specs = extract_bc_specs_from_parts_manifest(parts_manifest)
    report = detect_invalid_bc_types(bc_specs, fork="main")
    assert report.parts_examined == 3
    assert report.checked_count == 9   # 3 parts × 3 fields
    assert report.critical_count == 6  # 3 parts × {U, p}; T=freestream is valid
    assert report.warning_count == 0
    # Verify every critical names a foam-extend-only BC and carries a fix
    for f in report.findings:
        assert f.verdict == "valid_foam_extend_only"
        assert f.severity == "critical"
        assert f.bc_type_name in FOAM_EXTEND_ONLY_BCS
        assert f.suggested_fix is not None


# ---- 9. 4Q gate · advisor source contains no LLM tokens -----------------


def test_4q_gate_no_llm_imports() -> None:
    """V130 advisor-not-driver — Q1: LLM offline OK.

    Inspect the advisor module's source for any import / reference to
    LLM provider SDKs. A future maintainer who adds ``import openai``
    by mistake will trip this test instantly.
    """
    src = inspect.getsource(mod)
    # Imports we explicitly forbid in advisor leaves
    for forbidden in (
        "import openai",
        "import anthropic",
        "import google.generativeai",
        "from openai",
        "from anthropic",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
    ):
        assert forbidden not in src, f"D10 advisor contains forbidden token: {forbidden}"


# ---- 10. 4Q gate · advisor performs no filesystem writes ---------------


def test_4q_gate_no_case_dir_writes(tmp_path, monkeypatch) -> None:
    """V132 advisory-only — Q4: AI advisory only.

    Stub the open() builtin to detect any write-mode call. The advisor
    should perform exactly zero filesystem writes regardless of input.
    """
    write_attempts: list[str] = []
    real_open = open

    def watcher(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            write_attempts.append(f"open({file!r}, {mode!r})")
        return real_open(file, mode, *args, **kwargs)

    import builtins
    monkeypatch.setattr(builtins, "open", watcher)

    bc_specs = [
        {
            "part_name": "wing_main",
            "fields": {
                "U": "characteristicVelocityInletOutletVelocity",
                "p": "fixedValue",
            },
        }
    ]
    _ = detect_invalid_bc_types(bc_specs)
    _ = check_bc_type_name_validity("fixedValue")
    _ = extract_bc_specs_from_parts_manifest({"parts": [{"name": "a", "bc": {"U": "noSlip"}}]})

    assert write_attempts == [], f"D10 attempted writes: {write_attempts}"


# ---- 11. Input validation -----------------------------------------------


def test_invalid_input_types_handled_defensively() -> None:
    # Non-string bc_type_name → TypeError
    with pytest.raises(TypeError):
        check_bc_type_name_validity(123)  # type: ignore[arg-type]

    # Non-dict entries in bc_specs are silently skipped
    bc_specs = [
        "string entry",                              # type: ignore[list-item]
        42,                                          # type: ignore[list-item]
        None,                                        # type: ignore[list-item]
        {"part_name": "ok", "fields": {"U": "noSlip"}},
        {"part_name": "missing_fields"},             # field block absent → skipped
        {"fields": {"U": "noSlip"}},                 # part_name absent → skipped
        {"part_name": 5, "fields": {"U": "noSlip"}}, # part_name non-str → skipped
    ]
    report = detect_invalid_bc_types(bc_specs)  # type: ignore[arg-type]
    # Only the 4th entry was well-formed; checked_count = its 1 field
    assert report.checked_count == 1
    assert report.is_clean

    # None input is safe (V130: silently degrade, never raise)
    assert detect_invalid_bc_types(None).checked_count == 0  # type: ignore[arg-type]

    # parts_manifest adapter accepts None / wrong shape silently
    assert extract_bc_specs_from_parts_manifest(None) == []
    assert extract_bc_specs_from_parts_manifest({"parts": "not a list"}) == []


# ---- 12. Unknown fork branch --------------------------------------------


def test_fork_unknown_treats_foam_extend_as_warning() -> None:
    v = check_bc_type_name_validity(
        "characteristicPressureInletOutletPressure", fork="unknown"
    )
    assert v.verdict == "valid_foam_extend_only"
    assert v.severity == "warning"   # not critical, not info — warning
    assert v.fork == "unknown"
    assert v.suggested_fix is not None


# ---- 13. Catalog disjointness sanity check ------------------------------


def test_catalogs_are_disjoint() -> None:
    """Same name appearing in both STANDARD and FOAM_EXTEND_ONLY would
    cause a verdict ambiguity. The catalogs must stay disjoint; this
    test will fire the day someone adds a name to the wrong frozenset.
    """
    assert STANDARD_OPENFOAM_BCS.isdisjoint(FOAM_EXTEND_ONLY_BCS)
    assert STANDARD_OPENFOAM_BCS.isdisjoint(SENTINEL_BC_NAMES)
    assert FOAM_EXTEND_ONLY_BCS.isdisjoint(SENTINEL_BC_NAMES)


# ---- V63-A Tier 1 sub-DEC M-D10-CATALOG-AUDIT (2026-05-14) --------------
# Tests 14-19: catalog audit · case-driven expansion 80 → ≥100 mainline BCs.
# Closes V62-A carry-over #2: future case BC names previously risked
# emitting false unknown-warnings under fork='main'.


# Ground-truth BC name sets extracted from the three V62-A LANDED cases'
# live OpenFOAM 0/ boundaryField type declarations (sedimented 2026-05-14).
# Sources:
#   - case_006 ONERA M6 transonic   · ~/Desktop/case_006_onera_m6_transonic/inputs/parts_manifest.yaml
#   - case_011 plate-fin compact HX · ~/Desktop/case_011_plate_fin_compact_hx/case/0/region_*/{U,T,p,p_rgh}
#   - case_016 m219 cavity DES      · ~/Desktop/case_016_m219_cavity_des_acoustic/case/0/{U,p,T,k,omega,nut,alphat}
CASE_006_BC_NAMES = frozenset({
    "freestream",
    "kqRWallFunction",
    "noSlip",
    "nutUSpaldingWallFunction",
    "omegaWallFunction",
    "symmetry",
    "zeroGradient",
})  # +2 foam-extend-only (characteristic*) + sentinel none_volume_reference handled separately
CASE_011_BC_NAMES = frozenset({
    "calculated",
    "compressible::turbulentTemperatureCoupledBaffleMixed",
    "fixedFluxPressure",
    "fixedValue",
    "flowRateInletVelocity",
    "inletOutlet",
    "pressureInletOutletVelocity",
    "slip",
    "zeroGradient",
})
CASE_016_BC_NAMES = frozenset({
    "calculated",
    "compressible::alphatWallFunction",
    "freestream",
    "freestreamPressure",
    "inletOutlet",
    "kqRWallFunction",
    "nutUSpaldingWallFunction",
    "omegaWallFunction",
    "waveTransmissive",
    "zeroGradient",
})


def test_catalog_size_at_least_100() -> None:
    """V63-A sub-DEC M-D10-CATALOG-AUDIT goal: STANDARD_OPENFOAM_BCS must
    cover ≥100 ESI v2412 mainline BCs (audited up from the 80-entry
    pre-V63-A baseline) so industrial case profiles do not emit false
    unknown-warnings on common mainline BC names. Floor is intentional
    — future case-driven additions are encouraged but the audit floor
    holds the line against accidental drift via removal."""
    assert len(STANDARD_OPENFOAM_BCS) >= 100, (
        f"STANDARD_OPENFOAM_BCS has {len(STANDARD_OPENFOAM_BCS)} entries; "
        f"V63-A audit floor is 100. Did someone remove an entry without "
        f"a sub-DEC? Catalog policy is append-only (see module docstring)."
    )


def test_case_006_onera_m6_bcs_all_recognized() -> None:
    """case_006 ONERA M6 transonic standard BC names must verdict to
    ``valid_standard``. The two foam-extend-only characteristic* names
    are tested separately in ``test_foam_extend_only_bc_flagged_under_main_fork``
    + the sentinel ``none_volume_reference`` in ``test_sentinel_bc_names_pass``."""
    for name in CASE_006_BC_NAMES:
        v = check_bc_type_name_validity(name, fork="main")
        assert v.verdict == "valid_standard", (
            f"case_006 BC name '{name}' should be valid_standard but is "
            f"'{v.verdict}'. Catalog regression?"
        )
        assert v.severity == "pass"


def test_case_011_v5b_bcs_all_recognized() -> None:
    """case_011 v5b plate-fin compact HX (steady-laminar-CHT-multi-stream
    · LANDED 2026-05-14 stack track c session 1). All BCs from 0/region_*/
    must verdict to ``valid_standard``."""
    for name in CASE_011_BC_NAMES:
        v = check_bc_type_name_validity(name, fork="main")
        assert v.verdict == "valid_standard", (
            f"case_011 v5b BC name '{name}' should be valid_standard but "
            f"is '{v.verdict}'. Catalog regression?"
        )
        assert v.severity == "pass"


def test_case_016_m219_bcs_all_recognized() -> None:
    """case_016 m219 cavity DES acoustic (compressible-DES-acoustic class
    · LANDED 2026-05-14 stack track c session 2). All BCs from 0/{U,p,T,
    k,omega,nut,alphat} boundaryField blocks must verdict to ``valid_standard``."""
    for name in CASE_016_BC_NAMES:
        v = check_bc_type_name_validity(name, fork="main")
        assert v.verdict == "valid_standard", (
            f"case_016 m219 BC name '{name}' should be valid_standard but "
            f"is '{v.verdict}'. Catalog regression?"
        )
        assert v.severity == "pass"


def test_no_overlap_between_standard_and_foam_extend() -> None:
    """V63-A invariant restated: expanding STANDARD must not collide with
    the foam-extend-only set. The catalogs would silently produce wrong
    verdicts if overlap existed (a foam-extend-only name treated as
    valid_standard would silence the V29 evidence row).

    This duplicates the intent of ``test_catalogs_are_disjoint`` but
    is named per the V63-A sub-DEC §Tests requirement so a future
    grep on the carry-over closure can find it directly."""
    overlap = STANDARD_OPENFOAM_BCS & FOAM_EXTEND_ONLY_BCS
    assert overlap == set(), (
        f"V63-A audit invariant violated: STANDARD and FOAM_EXTEND_ONLY "
        f"share {sorted(overlap)}. A foam-extend-only BC would be "
        f"falsely passed under fork='main' and the V29 evidence row "
        f"(case_006 ONERA M6 transonic) silenced."
    )


def test_new_BCs_emit_severity_ok_when_fork_main() -> None:
    """A representative sample of the V63-A new additions (wall velocity,
    LES inlet, radiation, multiphase contact-angle, atm wallFunctions,
    compressible::ns mirrors, prgh*Pressure family). Each must verdict
    to ``valid_standard`` + severity ``pass`` under fork='main' (the
    project default). Catches a future maintainer accidentally placing
    one of these in FOAM_EXTEND_ONLY_BCS instead of STANDARD_OPENFOAM_BCS."""
    v63_new_sample = [
        # Wall velocity (moving / rotating / translating)
        "rotatingWallVelocity",
        "movingWallVelocity",
        "translatingWallVelocity",
        # Slip variants
        "partialSlip",
        "fixedNormalSlip",
        # Inlet/outlet expansions
        "pressureInletOutletParSlipVelocity",
        "supersonicFreestream",
        "turbulentDFSEMInlet",
        "turbulentDigitalFilterInlet",
        # prgh* family (multiphase pressure)
        "prghPressure",
        "prghTotalPressure",
        # ABL / atm wall functions
        "atmAlphatkWallFunction",
        "atmEpsilonWallFunction",
        "atmNutkWallFunction",
        # Radiation
        "MarshakRadiation",
        "greyDiffusiveRadiation",
        "greyDiffusiveRadiationViewFactor",
        "wideBandDiffusiveRadiation",
        # Cyclic / coupled extensions
        "cyclicPeriodicAMI",
        "nonuniformTransformCyclic",
        "jumpCyclicAMI",
        # Compressible::ns mirrors
        "compressible::nutkWallFunction",
        "compressible::nutUSpaldingWallFunction",
        # Multiphase / VOF contact angle
        "alphaContactAngle",
        "constantAlphaContactAngle",
        "dynamicAlphaContactAngle",
        # Mapping derivatives
        "mappedFlowRate",
        "mappedMixed",
    ]
    for name in v63_new_sample:
        assert name in STANDARD_OPENFOAM_BCS, (
            f"V63-A audit invariant: '{name}' must be in STANDARD_OPENFOAM_BCS"
        )
        v = check_bc_type_name_validity(name, fork="main")
        assert v.verdict == "valid_standard", (
            f"V63-A new BC '{name}' verdict='{v.verdict}' under fork='main' — "
            f"should be valid_standard"
        )
        assert v.severity == "pass"
        assert v.suggested_fix is None

    # Detect-side: a mock bc_specs using a mix of new BCs must report clean
    bc_specs = [
        {
            "part_name": "rotor_hub",
            "fields": {
                "U": "rotatingWallVelocity",
                "nut": "compressible::nutUSpaldingWallFunction",
            },
        },
        {
            "part_name": "atm_inlet",
            "fields": {
                "k": "atmBoundaryLayerInletK",
                "epsilon": "atmEpsilonWallFunction",
                "nut": "atmNutkWallFunction",
            },
        },
        {
            "part_name": "rad_wall",
            "fields": {
                "G": "greyDiffusiveRadiation",
                "qr": "MarshakRadiation",
            },
        },
    ]
    report = detect_invalid_bc_types(bc_specs, fork="main")
    assert report.is_clean, (
        f"V63-A new BCs should produce clean report; got findings: "
        f"{[(f.field_name, f.bc_type_name, f.verdict) for f in report.findings]}"
    )
    assert report.checked_count == 7
    assert report.warning_count == 0
    assert report.critical_count == 0
