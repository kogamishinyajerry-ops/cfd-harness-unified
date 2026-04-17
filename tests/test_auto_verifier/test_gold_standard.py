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

