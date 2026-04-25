"""Batch C test for preflight multi-scalar gate · DEC-V61-053.

Exercises scripts/preflight_case_visual.py::_check_scalar_contract against
synthetic audit + gold fixtures placed in tmp_path via monkeypatch. Covers:
  - cylinder-style 4-scalar case: primary PASS + secondary all PASS → 4 pass checks
  - one secondary out of tolerance → that check FAILs while others PASS
  - case without `secondary_scalars` → single-scalar check unchanged (back-compat)
  - unknown secondary key → ignored (no KeyError)
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import scripts.preflight_case_visual as pf


def _install_fixtures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    case_id: str,
    gold_docs: list[dict],
    measurement: dict,
) -> None:
    """Write gold + audit measurement YAMLs and monkeypatch preflight to use them."""
    gold_dir = tmp_path / "knowledge" / "gold_standards"
    gold_dir.mkdir(parents=True, exist_ok=True)
    gold_path = gold_dir / f"{case_id}.yaml"
    with gold_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump_all(gold_docs, fh)

    meas_path = (tmp_path / "ui" / "backend" / "tests" / "fixtures" / "runs"
                 / case_id / "audit_real_run_measurement.yaml")
    meas_path.parent.mkdir(parents=True, exist_ok=True)
    with meas_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(measurement, fh)

    monkeypatch.setattr(pf, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pf, "_GOLD_ROOT", gold_dir)


def _cyl_gold_multi_scalar() -> list[dict]:
    """Synthetic 4-doc gold YAML mirroring circular_cylinder_wake.yaml shape."""
    return [
        {  # St (primary)
            "quantity": "strouhal_number",
            "reference_values": [{"value": 0.164, "unit": "dimensionless"}],
            "tolerance": 0.05,
        },
        {  # cd_mean (secondary)
            "quantity": "cd_mean",
            "reference_values": [{"value": 1.33, "unit": "dimensionless"}],
            "tolerance": 0.05,
        },
        {  # cl_rms (secondary)
            "quantity": "cl_rms",
            "reference_values": [{"value": 0.048, "unit": "dimensionless"}],
            "tolerance": 0.05,
        },
    ]


def test_multi_scalar_all_within_tolerance_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All 3 gates (1 primary + 2 secondary) within tolerance → 3 PASS checks."""
    case_id = "cyl_test_pass_pass_pass"
    measurement = {
        "measurement": {
            "value": 0.163,  # St: 0.6% low
            "quantity": "strouhal_number",
            "secondary_scalars": {
                "cd_mean": 1.34,   # 0.75% high
                "cl_rms": 0.050,   # 4% high
            },
        },
    }
    _install_fixtures(monkeypatch, tmp_path,
                      case_id=case_id,
                      gold_docs=_cyl_gold_multi_scalar(),
                      measurement=measurement)
    checks = pf._check_scalar_contract(case_id)
    assert len(checks) == 3
    assert all(c.level == "pass" for c in checks), [c.summary for c in checks]


def test_multi_scalar_one_secondary_fails_others_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Primary PASS + cd_mean FAIL (1.55 vs 1.33 = +16.5%) + cl_rms PASS →
    3 checks total, 2 pass + 1 fail."""
    case_id = "cyl_test_primary_pass_cd_fail"
    measurement = {
        "measurement": {
            "value": 0.163,  # St: pass
            "quantity": "strouhal_number",
            "secondary_scalars": {
                "cd_mean": 1.55,   # +16.5% — FAIL
                "cl_rms": 0.049,   # 2% high — pass
            },
        },
    }
    _install_fixtures(monkeypatch, tmp_path,
                      case_id=case_id,
                      gold_docs=_cyl_gold_multi_scalar(),
                      measurement=measurement)
    checks = pf._check_scalar_contract(case_id)
    statuses = {c.name: c.level for c in checks}
    assert statuses["scalar contract"] == "pass"
    assert statuses["secondary scalar (cd_mean)"] == "fail"
    assert statuses["secondary scalar (cl_rms)"] == "pass"


def test_no_secondary_scalars_is_single_scalar_backcompat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BFS/LDC style: measurement has no `secondary_scalars`. Assert we still
    get exactly 1 scalar-contract check (the primary), no KeyError."""
    case_id = "bfs_style_single"
    measurement = {
        "measurement": {
            "value": 5.65,
            "quantity": "reattachment_length",
        },
    }
    gold_docs = [
        {
            "quantity": "reattachment_length",
            "reference_values": [{"value": 6.26, "unit": "dimensionless"}],
            "tolerance": 0.10,
        },
    ]
    _install_fixtures(monkeypatch, tmp_path,
                      case_id=case_id,
                      gold_docs=gold_docs,
                      measurement=measurement)
    checks = pf._check_scalar_contract(case_id)
    assert len(checks) == 1
    assert checks[0].name == "scalar contract"
    assert checks[0].level == "pass"


def test_unknown_secondary_key_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If `secondary_scalars` includes a key not present in gold YAML (e.g.
    a legacy diagnostic value), it should be silently skipped, not raise."""
    case_id = "cyl_test_unknown_secondary"
    measurement = {
        "measurement": {
            "value": 0.164,
            "quantity": "strouhal_number",
            "secondary_scalars": {
                "cd_mean": 1.33,
                "wake_width_diagnostic": 2.1,  # not in gold → ignored
            },
        },
    }
    _install_fixtures(monkeypatch, tmp_path,
                      case_id=case_id,
                      gold_docs=_cyl_gold_multi_scalar(),
                      measurement=measurement)
    checks = pf._check_scalar_contract(case_id)
    # Primary + cd_mean only (cl_rms absent in measurement; wake_width unknown)
    names = {c.name for c in checks}
    assert "scalar contract" in names
    assert "secondary scalar (cd_mean)" in names
    assert "secondary scalar (wake_width_diagnostic)" not in names
    assert "secondary scalar (cl_rms)" not in names


# ---------------------------------------------------------------------------
# DEC-V61-057 Codex round-4 F1-MED · schema_v2 normalization
# ---------------------------------------------------------------------------


def _dhc_schema_v2_gold_doc() -> list[dict]:
    """Synthetic single-doc schema_v2 gold YAML mirroring the DHC shape."""
    return [
        {
            "schema_version": 2,
            "case_id": "differential_heated_cavity_test",
            "source": "test fixture",
            "observables": [
                {
                    "name": "nusselt_number",
                    "ref_value": 8.8,
                    "tolerance": {"mode": "relative", "value": 0.10},
                    "gate_status": "HARD_GATED",
                },
                {
                    "name": "nusselt_max",
                    "ref_value": 17.925,
                    "tolerance": {"mode": "relative", "value": 0.07},
                    "gate_status": "HARD_GATED",
                },
                {
                    "name": "psi_max_center",
                    "ref_value": 16.750,
                    "tolerance": {"mode": "relative", "value": 0.08},
                    "gate_status": "PROVISIONAL_ADVISORY",
                },
            ],
        }
    ]


def test_schema_v2_primary_is_evaluated_not_warned(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Codex round-4 F1-MED regression: schema_v2 gold YAML (no per-doc
    `quantity:` blocks) must be normalized + evaluated, not silently
    dropped to `warn` with 'no quantity block'."""
    case_id = "dhc_schema_v2_test"
    measurement = {
        "measurement": {
            "value": 8.7,
            "quantity": "nusselt_number",
        },
    }
    _install_fixtures(monkeypatch, tmp_path,
                      case_id=case_id,
                      gold_docs=_dhc_schema_v2_gold_doc(),
                      measurement=measurement)
    checks = pf._check_scalar_contract(case_id)
    primary = next(c for c in checks if c.name == "scalar contract")
    assert primary.level == "pass", (
        f"expected pass, got {primary.level}: {primary.detail}"
    )


def test_schema_v2_secondary_observables_evaluated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """schema_v2 secondaries (e.g. nusselt_max, psi_max_center) coming via
    measurement.secondary_scalars must look up observables[] entries —
    previously only the legacy `quantity:` doc-walk was consulted."""
    case_id = "dhc_schema_v2_secondary_test"
    measurement = {
        "measurement": {
            "value": 8.7,
            "quantity": "nusselt_number",
            "secondary_scalars": {
                "nusselt_max": 17.5,         # within 7% → pass
                "psi_max_center": 16.5,      # within 8% → advisory pass
            },
        },
    }
    _install_fixtures(monkeypatch, tmp_path,
                      case_id=case_id,
                      gold_docs=_dhc_schema_v2_gold_doc(),
                      measurement=measurement)
    checks = pf._check_scalar_contract(case_id)
    by_name = {c.name: c for c in checks}
    assert "secondary scalar (nusselt_max)" in by_name
    assert by_name["secondary scalar (nusselt_max)"].level == "pass"
    psi_check = by_name["secondary scalar (psi_max_center)"]
    assert psi_check.level in ("pass", "warn"), (
        f"advisory observable should never be 'fail', got {psi_check.level}"
    )
    assert "[advisory]" in psi_check.detail


def test_schema_v2_advisory_outside_tolerance_emits_warn_not_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Out-of-tolerance PROVISIONAL_ADVISORY observable returns 'warn'
    (yellow), not 'fail' (red) — so preflight does not block live run on
    an advisory miss."""
    case_id = "dhc_advisory_outside_test"
    measurement = {
        "measurement": {
            "value": 8.7,
            "quantity": "nusselt_number",
            "secondary_scalars": {
                "psi_max_center": 25.0,  # +49%, way outside 8% — still advisory
            },
        },
    }
    _install_fixtures(monkeypatch, tmp_path,
                      case_id=case_id,
                      gold_docs=_dhc_schema_v2_gold_doc(),
                      measurement=measurement)
    checks = pf._check_scalar_contract(case_id)
    psi_check = next(
        c for c in checks if c.name == "secondary scalar (psi_max_center)"
    )
    assert psi_check.level == "warn"
    assert "[advisory]" in psi_check.detail


def test_schema_v2_real_dhc_gold_yaml_still_loads() -> None:
    """End-to-end smoke against the real on-disk DHC gold YAML (schema_v2):
    the primary scalar contract is evaluated (pass or fail), NOT silently
    warned about a missing `quantity:` block."""
    checks = pf._check_scalar_contract("differential_heated_cavity")
    primary = next(c for c in checks if c.name == "scalar contract")
    assert primary.level in ("pass", "fail"), (
        f"expected pass/fail, got {primary.level}: {primary.detail}"
    )
    assert "no quantity block" not in primary.detail
    assert "no observable for" not in primary.detail
