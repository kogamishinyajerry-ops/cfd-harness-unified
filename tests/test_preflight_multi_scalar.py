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
