"""V92 confirm-on-retry scorer semantics (DEC-V92-charter).

Covers:
  1. pw_vote.py unit fixtures — all-pass / flaky-pass / confirmed-fail /
     nested suites / parse-error (fail-closed 0/0).
  2. score_stability.sh integration via STABILITY_TEST_CMD fake command —
     fail-once (transient, 0 penalty) vs fail-always (confirmed, −30 each).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PW_VOTE = REPO / "scripts" / "governance" / "v92_fleet" / "pw_vote.py"
STABILITY = REPO / "scripts" / "governance" / "v71_fleet" / "score_stability.sh"

sys.path.insert(0, str(PW_VOTE.parent))
from pw_vote import vote, main as pw_vote_main  # noqa: E402


def _spec(title, statuses):
    return {"title": title, "tests": [{"results": [{"status": s} for s in statuses]}]}


def _report(specs, nested=None):
    suite = {"specs": specs, "suites": nested or []}
    return {"suites": [suite]}


class TestPwVote:
    def test_all_pass(self):
        r = vote(_report([_spec("a", ["passed"]), _spec("b", ["passed"])]))
        assert (r["passed"], r["total"], r["flaky"], r["confirmed_failed"]) == (2, 2, 0, 0)

    def test_flaky_eventual_pass_is_not_penalized(self):
        # V91 class: spec #50 timed out under load, passed on retry
        r = vote(_report([_spec("visual #50", ["timedOut", "passed"]), _spec("b", ["passed"])]))
        assert r["passed"] == 2  # flaky spec COUNTS as passed (V92 vote)
        assert r["confirmed_failed"] == 0
        assert r["flaky"] == 1
        assert r["flaky_titles"] == ["visual #50"]

    def test_confirmed_fail_all_attempts(self):
        r = vote(_report([_spec("broken", ["failed", "failed", "failed"]), _spec("b", ["passed"])]))
        assert r["passed"] == 1
        assert r["confirmed_failed"] == 1
        assert r["failed_titles"] == ["broken"]
        assert r["flaky"] == 0

    def test_nested_suites_walked(self):
        inner = {"specs": [_spec("deep", ["failed", "passed"])], "suites": []}
        r = vote(_report([_spec("top", ["passed"])], nested=[inner]))
        assert r["total"] == 2
        assert r["passed"] == 2
        assert r["flaky"] == 1

    def test_v78_regression_class_would_have_scored_86(self):
        # 184 clean + 1 flaky-pass: V78 rule → 184/185 (pro-rate 59 → min 86);
        # V92 vote → 185/185 (full 60).
        specs = [_spec(f"s{i}", ["passed"]) for i in range(184)]
        specs.append(_spec("s50", ["timedOut", "passed"]))
        r = vote(_report(specs))
        assert r["passed"] == r["total"] == 185
        v78_passed = 184  # old all()-rule
        assert v78_passed * 60 // 185 == 59  # documents the V91 dip this fixes

    def test_parse_error_fails_closed(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        r = pw_vote_main(str(bad))
        assert (r["passed"], r["total"]) == (0, 0)
        assert r["parse_error"] is not None

    def test_cli_emits_json(self, tmp_path):
        f = tmp_path / "rep.json"
        f.write_text(json.dumps(_report([_spec("a", ["passed"])])))
        out = subprocess.run(
            [sys.executable, str(PW_VOTE), str(f)], capture_output=True, text=True, check=True
        )
        assert json.loads(out.stdout)["passed"] == 1


@pytest.fixture
def fake_test_cmd(tmp_path):
    """Returns a cmd that fails on invocation numbers listed in FAIL_ON."""
    counter = tmp_path / "count"
    counter.write_text("0")
    script = tmp_path / "fake.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f'c=$(cat "{counter}"); c=$((c+1)); echo "$c" > "{counter}"\n'
        'for n in $FAIL_ON; do [ "$c" -eq "$n" ] && exit 1; done\n'
        "exit 0\n"
    )
    script.chmod(0o755)
    return str(script)


def _run_stability(cmd, fail_on):
    env = dict(os.environ, STABILITY_TEST_CMD=cmd, FAIL_ON=fail_on)
    out = subprocess.run(
        ["bash", str(STABILITY)], capture_output=True, text=True, env=env, cwd=str(REPO)
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.mark.skipif(not (REPO / "ui" / "frontend").is_dir(), reason="ui/frontend required")
class TestStabilityConfirmOnRetry:
    def test_transient_flake_zero_penalty(self, fake_test_cmd):
        # run1 fails, its retry (invocation 2) passes → transient, score 100
        r = _run_stability(fake_test_cmd, "1")
        assert r["score"] == 100
        assert r["subscores"]["flake_count"] == 0
        assert r["subscores"]["transient_flake_count"] == 1

    def test_clean_run_score_100(self, fake_test_cmd):
        r = _run_stability(fake_test_cmd, "")
        assert r["score"] == 100
        assert r["subscores"]["transient_flake_count"] == 0

    def test_confirmed_fail_full_penalty(self, fake_test_cmd):
        # every invocation fails → 3 confirmed fails → 100 − 3×30 = 10
        r = _run_stability(fake_test_cmd, "1 2 3 4 5 6")
        assert r["score"] == 10
        assert r["subscores"]["flake_count"] == 3
        assert r["subscores"]["transient_flake_count"] == 0

    def test_d4_guard_flags_two_transients(self, fake_test_cmd):
        # run1 + run2 fail, both retries pass → 2 transients → D4 mini-retro flag
        r = _run_stability(fake_test_cmd, "1 3")
        assert r["score"] == 100
        assert r["subscores"]["transient_flake_count"] == 2
        assert any("mini-retro" in f for f in r["failures"])
