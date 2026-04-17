from auto_verifier import PhysicsChecker


def test_l3_mass_conserved():
    report = PhysicsChecker().check({"mass_flow_in": 1.0, "mass_flow_out": 0.995})
    assert report.status == "PASS"


def test_l3_mass_warning():
    report = PhysicsChecker().check({"mass_flow_in": 1.0, "mass_flow_out": 0.97})
    assert report.status == "WARN"
    assert "mass_imbalance_warning" in report.warnings


def test_l3_mass_fail():
    report = PhysicsChecker().check({"mass_flow_in": 1.0, "mass_flow_out": 0.8})
    assert report.status == "FAIL"
    assert "mass_imbalance_failure" in report.warnings

