"""Tests for ``geometry_ingest.thermo_polynomial_range_advisor`` (A10).

Coverage (≥9 tests, mirroring A4 / A5 / A8 layout):

V41 + V93 regression pins:
  1. V41 channel-(b) regression — case_009 v1 53-species, 13 at Tlow=300
     + fuel_jet T=294 K → critical ``t_floor_breach``.
  2. V93 pre-ignition T-floor rule regression — fuel_jet T=294 K,
     N2 Tlow=300, safety_margin=5 K → critical ``t_floor_breach``.
  3. v1.5 patched-state regression — all 53 species at Tlow=200 K,
     fuel_jet T=294 K → 0 findings (closes the loop, no false positive).

Path (a) Tlow above canonical floor:
  4. Single species at Tlow=300 with no BCs supplied → warning
     ``tlow_above_canonical`` (path-a fires independent of path-b).
  5. All species at Tlow=200 → no ``tlow_above_canonical`` findings.

Path (b) pre-ignition T-floor (V93 rule):
  6. fixedValue T 305 K + max Tlow 300 K + safety_margin 5 K →
     ``305 - 5 = 300 == 300`` (no gap) → NO finding.
  7. fixedValue T 304 K + max Tlow 300 K + safety_margin 5 K → critical.

Path (c) typo suspicion fuzzy match:
  8. ``thermodynamcis`` typo (transposition of thermodynamics) → warning.
  9. Canonical-only species block → no typo_suspicion findings.

Path (d) species coverage + internalField + missing-block skip:
 10. SpeciesCoverage census buckets all three bands correctly.
 11. internalField below max(Tlow) - safety_margin → critical
     ``internal_t_below_tlow``.
 12. Empty thermo dict + None boundary_conditions → is_clean,
     no crash, coverage all zeros.
"""
from __future__ import annotations

from ui.backend.services.geometry_ingest.thermo_polynomial_range_advisor import (
    CANONICAL_THERMO_KEYS,
    CANONICAL_TLOW_FLOOR_K,
    DEFAULT_SAFETY_MARGIN_K,
    SpeciesCoverage,
    ThermoFinding,
    ThermoPolynomialRangeReport,
    check_thermo_polynomial_range,
)

# The 13 species that case_009 v1 measured at Tlow=300 K (V91 §Engineer
# symptom). Used to build a faithful regression fixture.
_V41_TLOW_300_SPECIES: tuple[str, ...] = (
    "N2", "AR", "CH3O", "HCCO", "HCCOH",
    "HCNN", "HCNO", "HNCO", "HOCN",
    "CH2CHO", "H2CN", "C3H7", "C3H8",
)

# A subset of "good" species (Tlow=200) — chosen to bring the total
# species count to 53 matching the v1 production dict size.
_V41_TLOW_200_SPECIES: tuple[str, ...] = tuple(
    f"SPECIES_{i:02d}" for i in range(53 - len(_V41_TLOW_300_SPECIES))
)


def _build_case_009_v1_thermo_dict() -> dict:
    """Synthesize the case_009 v1 thermo.compressibleGas shape."""
    d: dict = {}
    for sp in _V41_TLOW_300_SPECIES:
        d[sp] = {
            "specie": {"molWeight": 28.0},
            "thermodynamics": {
                "Tlow": 300,
                "Thigh": 5000,
                "Tcommon": 1000,
            },
            "transport": {"As": 1.4584e-06, "Ts": 110.4},
        }
    for sp in _V41_TLOW_200_SPECIES:
        d[sp] = {
            "specie": {"molWeight": 16.0},
            "thermodynamics": {
                "Tlow": 200,
                "Thigh": 3500,
                "Tcommon": 1000,
            },
            "transport": {"As": 1.4584e-06, "Ts": 110.4},
        }
    return d


def _build_case_009_v1_5_thermo_dict() -> dict:
    """Synthesize the case_009 v1.5 patched dict — all species at Tlow=200."""
    d: dict = {}
    for sp in _V41_TLOW_300_SPECIES + _V41_TLOW_200_SPECIES:
        d[sp] = {
            "specie": {"molWeight": 28.0},
            "thermodynamics": {
                "Tlow": 200,
                "Thigh": 3500,
                "Tcommon": 1000,
            },
            "transport": {"As": 1.4584e-06, "Ts": 110.4},
        }
    return d


def _sandia_flame_d_bc() -> dict:
    """Sandia Flame D ``0/T`` boundaryField shape."""
    return {
        "internalField": 300.0,
        "boundaryField": {
            "fuel_jet": {"type": "fixedValue", "value": 294.0},
            "coflow_air": {"type": "fixedValue", "value": 300.0},
            "pilot": {"type": "fixedValue", "value": 1880.0},
            "outflow": {"type": "zeroGradient"},
            "axis": {"type": "empty"},
        },
    }


# ---------------------------------------------------------------------- #
# 1. V41 channel-(b) regression — pin the v1 ground truth                #
# ---------------------------------------------------------------------- #
def test_v41_channel_b_regression_case_009_v1():
    """case_009 v1 production state — 13/53 species at Tlow=300; fuel_jet
    at 294 K — must surface BOTH path-(a) warnings AND a path-(b)
    critical. Closes V41 channel-(b) gap (V91-flagged)."""
    thermo = _build_case_009_v1_thermo_dict()
    bc = _sandia_flame_d_bc()
    report = check_thermo_polynomial_range(thermo, bc)

    assert isinstance(report, ThermoPolynomialRangeReport)
    # Path (a): 13 species warnings
    a_findings = [f for f in report.findings if f.code == "tlow_above_canonical"]
    assert len(a_findings) == 13, [f.species for f in a_findings]
    assert {f.species for f in a_findings} == set(_V41_TLOW_300_SPECIES)
    # Path (b): exactly one critical T-floor breach
    b_findings = [f for f in report.findings if f.code == "t_floor_breach"]
    assert len(b_findings) == 1
    assert b_findings[0].severity == "critical"
    # fuel_jet (294 K) is the offender; 294 - 5 = 289 < 300
    assert "fuel_jet" in b_findings[0].location
    assert "294" in b_findings[0].message
    assert "300" in b_findings[0].message
    # Coverage census shape
    assert report.species_coverage.at_canonical_floor == 40
    assert report.species_coverage.above_canonical_to_300 == 13
    assert report.species_coverage.above_300 == 0
    assert report.species_coverage.total_species_with_tlow == 53
    assert report.max_species_tlow == 300.0
    assert report.min_boundary_t == 294.0


# ---------------------------------------------------------------------- #
# 2. V93 pre-ignition T-floor rule regression — narrow single-species pin #
# ---------------------------------------------------------------------- #
def test_v93_pre_ignition_t_floor_rule_case_009_v1():
    """V93 codified rule on a minimal fixture: N2 Tlow=300, fuel_jet T=294,
    safety_margin=5 → 294 - 5 = 289 < 300 → critical t_floor_breach."""
    thermo = {
        "N2": {
            "specie": {"molWeight": 28.0134},
            "thermodynamics": {"Tlow": 300, "Thigh": 5000, "Tcommon": 1000},
            "transport": {"As": 1.4584e-06, "Ts": 110.4},
        },
        "CH4": {
            "specie": {"molWeight": 16.04},
            "thermodynamics": {"Tlow": 200, "Thigh": 3500, "Tcommon": 1000},
            "transport": {"As": 1.4584e-06, "Ts": 110.4},
        },
    }
    bc = {
        "boundaryField": {
            "fuel_jet": {"type": "fixedValue", "value": 294.0},
        },
    }
    report = check_thermo_polynomial_range(
        thermo, bc, safety_margin_k=DEFAULT_SAFETY_MARGIN_K
    )
    critical = [f for f in report.findings if f.severity == "critical"]
    assert len(critical) == 1
    assert critical[0].code == "t_floor_breach"
    assert critical[0].species == "N2"
    assert critical[0].location == "boundaryField.fuel_jet.value"
    # Suggestion mentions the canonical remediation tool
    assert critical[0].suggestion is not None
    assert "patch_janaf_tlow" in critical[0].suggestion


# ---------------------------------------------------------------------- #
# 3. v1.5 patched-state regression — closes the loop, no false positive   #
# ---------------------------------------------------------------------- #
def test_v1_5_patched_state_clean_case_009():
    """case_009 v1.5 — all 53 species at Tlow=200 K, fuel_jet T=294 K.
    294 - 5 = 289 >> 200, no path-(a) warnings, no path-(b) breach.
    Empirically confirms the V93 patch is the necessary-and-sufficient fix."""
    thermo = _build_case_009_v1_5_thermo_dict()
    bc = _sandia_flame_d_bc()
    report = check_thermo_polynomial_range(thermo, bc)
    assert report.is_clean, [
        (f.code, f.severity, f.location) for f in report.findings
    ]
    assert report.species_coverage.at_canonical_floor == 53
    assert report.species_coverage.above_canonical_to_300 == 0
    assert report.species_coverage.above_300 == 0
    assert report.max_species_tlow == 200.0


# ---------------------------------------------------------------------- #
# 4. Path (a) — single species Tlow=300 with no BCs supplied               #
# ---------------------------------------------------------------------- #
def test_path_a_tlow_above_canonical_warning_without_bc():
    """Path (a) must fire independent of BCs — surfaces the partial-patch
    state for an LES case whose boundaries happen to all be ≥ 300 K
    (no path-(b) breach), so coverage-only fail can still surface."""
    thermo = {
        "AR": {
            "thermodynamics": {"Tlow": 300, "Thigh": 5000, "Tcommon": 1000},
        },
        "H2O": {
            "thermodynamics": {"Tlow": 200, "Thigh": 3500, "Tcommon": 1000},
        },
    }
    report = check_thermo_polynomial_range(thermo, boundary_conditions=None)
    a_findings = [f for f in report.findings if f.code == "tlow_above_canonical"]
    assert len(a_findings) == 1
    assert a_findings[0].species == "AR"
    assert a_findings[0].severity == "warning"
    assert a_findings[0].location == "AR.thermodynamics.Tlow"
    # No T-floor finding (no BCs to compare against)
    assert not any(f.code == "t_floor_breach" for f in report.findings)


# ---------------------------------------------------------------------- #
# 5. Path (a) — canonical-only species set produces no warning            #
# ---------------------------------------------------------------------- #
def test_path_a_canonical_only_no_warning():
    """All species at Tlow=200 → no tlow_above_canonical findings."""
    thermo = {
        sp: {"thermodynamics": {"Tlow": 200, "Thigh": 3500, "Tcommon": 1000}}
        for sp in ("N2", "O2", "CH4", "H2O", "CO2")
    }
    report = check_thermo_polynomial_range(thermo, boundary_conditions=None)
    assert not any(f.code == "tlow_above_canonical" for f in report.findings)
    assert report.species_coverage.at_canonical_floor == 5
    assert report.species_coverage.above_canonical_to_300 == 0


# ---------------------------------------------------------------------- #
# 6. Path (b) — at the boundary (no gap) — NO finding                      #
# ---------------------------------------------------------------------- #
def test_path_b_exactly_at_boundary_no_finding():
    """fixedValue T 305 K + max Tlow 300 K + safety_margin 5 K →
    305 - 5 = 300 == 300 → no path-(b) breach (boundary case)."""
    thermo = {
        "N2": {"thermodynamics": {"Tlow": 300, "Thigh": 5000, "Tcommon": 1000}},
    }
    bc = {"boundaryField": {"inlet": {"type": "fixedValue", "value": 305.0}}}
    report = check_thermo_polynomial_range(thermo, bc, safety_margin_k=5.0)
    assert not any(f.code == "t_floor_breach" for f in report.findings)


# ---------------------------------------------------------------------- #
# 7. Path (b) — 1 K below the boundary → critical                          #
# ---------------------------------------------------------------------- #
def test_path_b_one_kelvin_below_boundary_critical():
    """fixedValue T 304 K + max Tlow 300 K + safety_margin 5 K →
    304 - 5 = 299 < 300 → critical t_floor_breach with 1 K gap message."""
    thermo = {
        "N2": {"thermodynamics": {"Tlow": 300, "Thigh": 5000, "Tcommon": 1000}},
    }
    bc = {"boundaryField": {"inlet": {"type": "fixedValue", "value": 304.0}}}
    report = check_thermo_polynomial_range(thermo, bc, safety_margin_k=5.0)
    breaches = [f for f in report.findings if f.code == "t_floor_breach"]
    assert len(breaches) == 1
    assert breaches[0].severity == "critical"
    # Gap is -1 K
    assert "-1" in breaches[0].message or "−1" in breaches[0].message


# ---------------------------------------------------------------------- #
# 8. Path (c) — typo Levenshtein suggestion                                #
# ---------------------------------------------------------------------- #
def test_path_c_typo_suspicion_warning():
    """``thermodynamcis`` (transposition typo of thermodynamics) → warning
    with suggestion 'thermodynamics'. Mirrors A8's typo pattern."""
    thermo = {
        "N2": {
            "specie": {"molWeight": 28.0},
            # The species block has a typo in the sub-block name
            "thermodynamcis": {  # noqa: typo on purpose
                "Tlow": 200,
                "Thigh": 3500,
            },
        },
    }
    report = check_thermo_polynomial_range(thermo, boundary_conditions=None)
    typo = [f for f in report.findings if f.code == "typo_suspicion"]
    assert len(typo) == 1
    assert typo[0].severity == "warning"
    assert typo[0].suggestion == "thermodynamics"
    assert typo[0].location == "N2.thermodynamcis"
    assert "thermodynamics" in typo[0].message


# ---------------------------------------------------------------------- #
# 9. Path (c) — canonical species block produces no typo                   #
# ---------------------------------------------------------------------- #
def test_path_c_canonical_only_no_typo():
    """All canonical keys → no typo_suspicion findings. Negative guard
    against fuzzy-match false-positives on canonical vocabulary."""
    thermo = {
        "N2": {
            "specie": {"molWeight": 28.0, "nMoles": 1.0},
            "thermodynamics": {
                "Tlow": 200,
                "Thigh": 3500,
                "Tcommon": 1000,
                "highCpCoeffs": [],
                "lowCpCoeffs": [],
            },
            "transport": {"As": 1.4584e-06, "Ts": 110.4},
            "equationOfState": {},
            "elements": {"N": 2},
        },
    }
    report = check_thermo_polynomial_range(thermo, boundary_conditions=None)
    assert not any(f.code == "typo_suspicion" for f in report.findings)
    # Sanity: every canonical key is in CANONICAL_THERMO_KEYS
    canonical_names = {k for k, _ in CANONICAL_THERMO_KEYS}
    assert {
        "specie", "thermodynamics", "transport", "equationOfState",
        "Tlow", "Thigh", "Tcommon", "highCpCoeffs", "lowCpCoeffs",
        "As", "Ts",
    }.issubset(canonical_names)


# ---------------------------------------------------------------------- #
# 10. SpeciesCoverage census buckets all three bands                       #
# ---------------------------------------------------------------------- #
def test_species_coverage_census_three_bands():
    """Mix Tlow at 200 / 250 / 300 / 350 → census splits across three bands."""
    thermo = {
        "S1": {"thermodynamics": {"Tlow": 200}},
        "S2": {"thermodynamics": {"Tlow": 200}},
        "S3": {"thermodynamics": {"Tlow": 250}},
        "S4": {"thermodynamics": {"Tlow": 300}},
        "S5": {"thermodynamics": {"Tlow": 350}},
    }
    report = check_thermo_polynomial_range(thermo, boundary_conditions=None)
    cov: SpeciesCoverage = report.species_coverage
    assert cov.at_canonical_floor == 2  # S1, S2
    assert cov.above_canonical_to_300 == 2  # S3 (250), S4 (300)
    assert cov.above_300 == 1  # S5 (350)
    assert cov.total_species_with_tlow == 5


# ---------------------------------------------------------------------- #
# 11. internalField below max(Tlow) - safety_margin → critical             #
# ---------------------------------------------------------------------- #
def test_internal_field_below_tlow_critical():
    """internalField=290 K, max(Tlow)=300 K, safety_margin=5 K →
    290 < 300 - 5 = 295 → critical internal_t_below_tlow."""
    thermo = {
        "N2": {"thermodynamics": {"Tlow": 300, "Thigh": 5000, "Tcommon": 1000}},
    }
    bc = {"internalField": 290.0}
    report = check_thermo_polynomial_range(thermo, bc, safety_margin_k=5.0)
    internal = [f for f in report.findings if f.code == "internal_t_below_tlow"]
    assert len(internal) == 1
    assert internal[0].severity == "critical"
    assert internal[0].location == "internalField"
    assert "290" in internal[0].message
    assert "300" in internal[0].message


# ---------------------------------------------------------------------- #
# 12. Missing-block skip — empty inputs do not crash + report is_clean     #
# ---------------------------------------------------------------------- #
def test_missing_blocks_silently_skipped():
    """Empty thermo dict + None boundary_conditions → no crash, is_clean,
    coverage all zeros. Mirrors A8's sliced-dict tolerance."""
    report = check_thermo_polynomial_range({}, None)
    assert report.is_clean
    assert report.species_coverage.total_species_with_tlow == 0
    assert report.max_species_tlow == 0.0
    assert report.min_boundary_t == 0.0
    # And a sliced thermo dict (species block missing 'thermodynamics')
    sliced = {"N2": {"specie": {"molWeight": 28.0}}}
    report2 = check_thermo_polynomial_range(sliced, None)
    assert report2.species_coverage.total_species_with_tlow == 0
    # Tolerates string-coerced numeric values too (OpenFOAM 'uniform N')
    bc_str = {
        "internalField": "uniform 300",
        "boundaryField": {
            "inlet": {"type": "fixedValue", "value": "uniform 294"},
        },
    }
    thermo3 = {"N2": {"thermodynamics": {"Tlow": "300"}}}
    report3 = check_thermo_polynomial_range(thermo3, bc_str, safety_margin_k=5.0)
    assert any(f.code == "t_floor_breach" for f in report3.findings)
    assert report3.min_boundary_t == 294.0


# Sanity: ThermoFinding immutable + symbol-export check
def test_finding_dataclass_frozen():
    f = ThermoFinding(
        code="tlow_above_canonical",
        severity="warning",
        location="N2.thermodynamics.Tlow",
        message="x",
    )
    try:
        f.code = "other"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("ThermoFinding should be frozen")


def test_canonical_constant_value():
    """Pin the canonical floor + safety margin to the documented values
    so retro readers can see V93 = 5 K and CHEMKIN floor = 200 K."""
    assert CANONICAL_TLOW_FLOOR_K == 200.0
    assert DEFAULT_SAFETY_MARGIN_K == 5.0
