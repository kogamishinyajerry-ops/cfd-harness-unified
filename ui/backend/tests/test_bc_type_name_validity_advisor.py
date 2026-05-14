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
