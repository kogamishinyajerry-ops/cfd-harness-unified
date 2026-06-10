#!/usr/bin/env python3
"""V92 confirm-on-retry vote for Playwright JSON reports (DEC-V92-charter D2).

A spec PASSES if ANY attempt passed (playwright --retries semantics).
  - flaky          = eventually passed, but >=1 failed attempt (telemetry, 0 penalty)
  - confirmed_fail = no attempt passed (drives the pro-rate penalty)

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
            for t in sp.get("tests", []):
                yield sp.get("title", "?"), t
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
    for title, t in walk(report.get("suites", [])):
        results = t.get("results", [])
        out["total"] += 1
        any_pass = any(r.get("status") == "passed" for r in results)
        any_fail = any(r.get("status") != "passed" for r in results)
        if any_pass:
            out["passed"] += 1
            if any_fail:
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
