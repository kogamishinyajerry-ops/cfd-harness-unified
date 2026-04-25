import math

from auto_verifier import GoldStandardComparator


def test_l2_all_pass():
    gold = {
        "observables": [
            {"name": "lift", "ref_value": 1.0, "tolerance": {"mode": "relative", "value": 0.05}},
            {
                "name": "profile",
                "ref_value": [{"x": 0.0, "value": 0.0}, {"x": 1.0, "value": 2.0}],
                "tolerance": {"mode": "relative", "value": 0.10},
            },
        ]
    }
    sim = {"lift": 1.01, "profile": [0.0, 2.02], "profile_x": [0.0, 1.0]}

    report = GoldStandardComparator().compare(gold, sim)
    assert report.overall == "PASS"


def test_l2_partial_pass():
    gold = {
        "observables": [
            {"name": "a", "ref_value": 1.0, "tolerance": {"mode": "relative", "value": 0.05}},
            {"name": "b", "ref_value": 2.0, "tolerance": {"mode": "relative", "value": 0.05}},
            {"name": "c", "ref_value": 3.0, "tolerance": {"mode": "relative", "value": 0.05}},
            {"name": "d", "ref_value": 4.0, "tolerance": {"mode": "relative", "value": 0.05}},
        ]
    }
    sim = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.4}

    report = GoldStandardComparator().compare(gold, sim)
    assert report.overall == "PASS_WITH_DEVIATIONS"


def test_l2_fail():
    gold = {
        "observables": [
            {"name": "a", "ref_value": 1.0, "tolerance": {"mode": "relative", "value": 0.05}},
            {"name": "b", "ref_value": 2.0, "tolerance": {"mode": "relative", "value": 0.05}},
            {"name": "c", "ref_value": 3.0, "tolerance": {"mode": "relative", "value": 0.05}},
        ]
    }
    sim = {"a": 1.5, "b": 2.8, "c": 3.0}

    report = GoldStandardComparator().compare(gold, sim)
    assert report.overall == "FAIL"


def test_l2_zero_ref():
    gold = {
        "observables": [
            {"name": "pressure_offset", "ref_value": 0.0, "tolerance": {"mode": "relative", "value": 0.05}}
        ]
    }
    sim = {"pressure_offset": 5.0e-7}

    report = GoldStandardComparator().compare(gold, sim)
    observable = report.observables[0]
    assert observable.rel_error is None
    assert observable.abs_error == 5.0e-7
    assert observable.within_tolerance


def test_l2_nan_sim():
    gold = {
        "observables": [
            {"name": "drag", "ref_value": 1.0, "tolerance": {"mode": "relative", "value": 0.05}}
        ]
    }
    sim = {"drag": math.nan}

    report = GoldStandardComparator().compare(gold, sim)
    assert report.overall == "FAIL"
    assert not report.observables[0].within_tolerance


# DEC-V61-057 Stage C — gate_status semantics tests
# (PROVISIONAL_ADVISORY excluded from pass-fraction; backward-compat default)

class TestGateStatusSemantics:
    """Verify HARD_GATED vs PROVISIONAL_ADVISORY split (DEC-V61-057 §C)."""

    def test_default_gate_status_is_hard_gated(self):
        """Backward compat: omitting gate_status → HARD_GATED."""
        gold = {
            "observables": [
                {"name": "x", "ref_value": 1.0, "tolerance": {"mode": "relative", "value": 0.05}},
            ]
        }
        sim = {"x": 1.0}
        report = GoldStandardComparator().compare(gold, sim)
        assert report.overall == "PASS"
        assert report.observables[0].gate_status == "HARD_GATED"

    def test_advisory_observable_excluded_from_overall_verdict(self):
        """Advisory check that fails its tolerance must NOT degrade overall."""
        gold = {
            "observables": [
                {
                    "name": "hard_pass",
                    "ref_value": 1.0,
                    "tolerance": {"mode": "relative", "value": 0.05},
                    "gate_status": "HARD_GATED",
                },
                {
                    "name": "advisory_fail",
                    "ref_value": 10.0,
                    "tolerance": {"mode": "relative", "value": 0.05},
                    "gate_status": "PROVISIONAL_ADVISORY",
                },
            ]
        }
        # Advisory misses by 100%; hard-gate passes.
        sim = {"hard_pass": 1.0, "advisory_fail": 20.0}
        report = GoldStandardComparator().compare(gold, sim)
        assert report.overall == "PASS"  # advisory failure does NOT pull down overall
        # But the advisory failure surfaces as a non-blocking warning.
        assert any(
            w.startswith("advisory_observable_outside_tolerance:advisory_fail")
            for w in report.warnings
        )

    def test_only_advisory_observables_returns_skipped(self):
        """No HARD_GATED → can't form a verdict → SKIPPED."""
        gold = {
            "observables": [
                {
                    "name": "advisory_only",
                    "ref_value": 1.0,
                    "tolerance": {"mode": "relative", "value": 0.05},
                    "gate_status": "PROVISIONAL_ADVISORY",
                },
            ]
        }
        sim = {"advisory_only": 1.0}
        report = GoldStandardComparator().compare(gold, sim)
        assert report.overall == "SKIPPED"
        assert "no_hard_gated_observables" in report.warnings

    def test_advisory_check_still_propagates_within_tolerance_field(self):
        """Advisory observables are *measured* (rendered), just not *gated*."""
        gold = {
            "observables": [
                {
                    "name": "hard", "ref_value": 1.0,
                    "tolerance": {"mode": "relative", "value": 0.05},
                },
                {
                    "name": "advisory", "ref_value": 1.0,
                    "tolerance": {"mode": "relative", "value": 0.05},
                    "gate_status": "PROVISIONAL_ADVISORY",
                },
            ]
        }
        sim = {"hard": 1.0, "advisory": 1.02}
        report = GoldStandardComparator().compare(gold, sim)
        by_name = {c.name: c for c in report.observables}
        assert by_name["advisory"].within_tolerance is True
        assert by_name["advisory"].gate_status == "PROVISIONAL_ADVISORY"

    def test_dhc_gold_yaml_loads_with_5_observables(self):
        """Parse the live DHC gold YAML — 1 headline + 3 cross-checks + 1 advisory."""
        from pathlib import Path
        import yaml

        gold_path = (
            Path(__file__).resolve().parents[2]
            / "knowledge" / "gold_standards" / "differential_heated_cavity.yaml"
        )
        gold = yaml.safe_load(gold_path.read_text(encoding="utf-8"))
        observables = gold["observables"]
        assert len(observables) == 5
        names = {o["name"] for o in observables}
        assert names == {
            "nusselt_number", "nusselt_max",
            "u_max_centerline_v", "v_max_centerline_h",
            "psi_max_center",
        }
        statuses = {o["name"]: o.get("gate_status", "HARD_GATED") for o in observables}
        assert statuses == {
            "nusselt_number": "HARD_GATED",
            "nusselt_max": "HARD_GATED",
            "u_max_centerline_v": "HARD_GATED",
            "v_max_centerline_h": "HARD_GATED",
            "psi_max_center": "PROVISIONAL_ADVISORY",
        }
