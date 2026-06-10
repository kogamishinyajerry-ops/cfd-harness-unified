#!/usr/bin/env python3
"""V92 confirm-on-retry vote for Playwright JSON reports (DEC-V92-charter D2).

Vote unit = spec (not test instance). Each tests[] entry (one per
playwright project, e.g. CROSSBROWSER=1 matrix) votes instance-level
first — instance ok if ANY attempt passed (--retries semantics) — then
aggregates to the spec:
  - passed         = every project instance has >=1 passing attempt
  - flaky          = passed, but >=1 instance needed a retry (telemetry, 0 penalty)
  - confirmed_fail = >=1 instance where NO attempt passed (drives the
                     pro-rate penalty; a hard fail on one browser is
                     never masked by a pass on another)
A spec is counted exactly once regardless of project count (Codex R0 P2).

Replaces the V78 rule `all(r.status == "passed")` which 1-vote-vetoed a
spec on a single load-induced transient (V90/V91 retro Open Q #1).

Usage: pw_vote.py <playwright_report.json>
Emits one JSON object on stdout:
  {"passed": int, "total": int, "flaky": int, "confirmed_failed": int,
   "flaky_titles": [...], "failed_titles": [...], "parse_error": str|null}
On parse failure: zeros + parse_error set (matches V78 fail-closed behavior).
"""
import json
import sys


def walk(suites):
    for s in suites:
        for sp in s.get("specs", []):
            if sp.get("tests", []):
                yield sp.get("title", "?"), sp["tests"]
        yield from walk(s.get("suites", []))


def vote(report: dict) -> dict:
    out = {
        "passed": 0,
        "total": 0,
        "flaky": 0,
        "confirmed_failed": 0,
        "flaky_titles": [],
        "failed_titles": [],
        "parse_error": None,
    }
    for title, tests in walk(report.get("suites", [])):
        out["total"] += 1
        inst_ok, inst_flaky = [], []
        for t in tests:
            results = t.get("results", [])
            any_pass = any(r.get("status") == "passed" for r in results)
            any_fail = any(r.get("status") != "passed" for r in results)
            inst_ok.append(any_pass)
            inst_flaky.append(any_pass and any_fail)
        if all(inst_ok):
            out["passed"] += 1
            if any(inst_flaky):
                out["flaky"] += 1
                out["flaky_titles"].append(title)
        else:
            out["confirmed_failed"] += 1
            out["failed_titles"].append(title)
    return out


def main(path: str) -> dict:
    try:
        with open(path) as f:
            report = json.load(f)
        return vote(report)
    except Exception as exc:  # fail-closed: 0/0 like V78 parse-error branch
        return {
            "passed": 0,
            "total": 0,
            "flaky": 0,
            "confirmed_failed": 0,
            "flaky_titles": [],
            "failed_titles": [],
            "parse_error": str(exc),
        }


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1]), ensure_ascii=False))
