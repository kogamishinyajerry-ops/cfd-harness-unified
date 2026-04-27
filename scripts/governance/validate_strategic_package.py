#!/usr/bin/env python3
"""P-2.5 — Strategic Package validator for Kogami high-risk PR triggers.

Per DEC-V61-087 §4.4 (v3 R2 fix · structured YAML schema replaces free prose):

intent_summary.md schema:
  roadmap_milestone: string · regex `^(M\\d+|P\\d+(-T\\d+)?|W\\d+)(\\..+)?$`
  business_goal: string · ≤50 words · plain language
  affected_subsystems: list of strings · each 1-5 words · no LOC, no file paths
  rationale: optional string · ≤100 words · regex blacklist applied here ONLY

merge_risk_summary.md schema:
  risk_class: enum {low, medium, high}
  reversibility: enum {easy, medium, hard}
  blast_radius: enum {bounded, cross-system, everything}
  rationale: optional string · ≤100 words · regex blacklist applied here ONLY

Regex blacklist (applied to `rationale` field text only, not to enums or lists):
  - \\bP[0-3]\\b (word-boundary, case-sensitive — won't match P2-T2)
  - \\bCodex\\b (case-sensitive)
  - \\bround\\s+\\d+\\b (case-insensitive)
  - \\bfinding(s)?\\b (case-insensitive)
  - \\b(CHANGES_REQUIRED|APPROVE_WITH_COMMENTS|APPROVE)\\b (case-sensitive enums)
  - \\S+\\.\\w+:\\d+\\b  (e.g. foo.py:42)

Usage:
    python3 scripts/governance/validate_strategic_package.py \\
        --intent <intent_summary.md> \\
        --risk <merge_risk_summary.md>

Exit code:
    0 = both files pass
    1 = at least one schema violation (printed to stderr)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# yaml import is optional; if not installed, fall back to a tiny inline parser
try:
    import yaml
except ImportError:
    yaml = None


# ───── schemas ─────

INTENT_REQUIRED = ["roadmap_milestone", "business_goal", "affected_subsystems"]
INTENT_OPTIONAL = ["rationale"]
RISK_REQUIRED = ["risk_class", "reversibility", "blast_radius"]
RISK_OPTIONAL = ["rationale"]

ROADMAP_MILESTONE_RE = re.compile(r"^(M\d+|P\d+(-T\d+)?|W\d+)(\..+)?$")
RISK_CLASS_VALUES = {"low", "medium", "high"}
REVERSIBILITY_VALUES = {"easy", "medium", "hard"}
BLAST_RADIUS_VALUES = {"bounded", "cross-system", "everything"}

INTENT_GOAL_WORD_CAP = 50
INTENT_SUBSYSTEM_WORDS_MAX = 5
RATIONALE_WORD_CAP = 100

BLACKLIST_REGEXES = [
    (re.compile(r"\bP[0-3]\b"), "Codex severity letter (P0/P1/P2/P3)"),
    (re.compile(r"\bCodex\b"), "Codex name"),
    (re.compile(r"\bround\s+\d+\b", re.IGNORECASE), "Codex round reference"),
    (re.compile(r"\bfinding(s)?\b", re.IGNORECASE), "Codex finding reference"),
    (re.compile(r"\b(CHANGES_REQUIRED|APPROVE_WITH_COMMENTS|APPROVE)\b"), "Codex verdict enum"),
    (re.compile(r"\S+\.\w+:\d+\b"), "file:line citation (looks like Codex finding)"),
]


# ───── helpers ─────


def parse_yaml(text: str) -> dict:
    """Parse YAML; if pyyaml absent, fall back to a tiny line parser sufficient
    for the schemas above (key: scalar / key: list)."""
    if yaml is not None:
        return yaml.safe_load(text) or {}

    # Minimal fallback parser
    out: dict = {}
    cur_list_key = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("- "):
            value = line.lstrip()[2:].strip().strip("'\"")
            if cur_list_key is None:
                raise ValueError(f"unexpected list item without key: {raw_line!r}")
            out.setdefault(cur_list_key, []).append(value)
            continue
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if value == "":
                cur_list_key = key
                out[key] = []
            else:
                cur_list_key = None
                out[key] = value
    return out


def word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))


def check_blacklist(field_name: str, text: str) -> list[str]:
    errors = []
    for regex, label in BLACKLIST_REGEXES:
        m = regex.search(text)
        if m:
            errors.append(f"{field_name} contains blacklisted pattern '{label}' (matched: {m.group(0)!r})")
    return errors


# ───── validators ─────


def validate_intent(text: str) -> list[str]:
    errors = []
    try:
        data = parse_yaml(text)
    except Exception as e:
        return [f"intent_summary YAML parse error: {e}"]

    if not isinstance(data, dict):
        return ["intent_summary root must be a YAML mapping"]

    for k in INTENT_REQUIRED:
        if k not in data:
            errors.append(f"intent_summary missing required field: {k}")

    rm = data.get("roadmap_milestone")
    if isinstance(rm, str) and not ROADMAP_MILESTONE_RE.match(rm.strip()):
        errors.append(f"intent_summary.roadmap_milestone {rm!r} does not match {ROADMAP_MILESTONE_RE.pattern!r}")

    goal = data.get("business_goal")
    if isinstance(goal, str):
        wc = word_count(goal)
        if wc > INTENT_GOAL_WORD_CAP:
            errors.append(f"intent_summary.business_goal is {wc} words, cap is {INTENT_GOAL_WORD_CAP}")

    subs = data.get("affected_subsystems")
    if subs is not None:
        if not isinstance(subs, list):
            errors.append("intent_summary.affected_subsystems must be a list")
        else:
            for i, s in enumerate(subs):
                if not isinstance(s, str):
                    errors.append(f"intent_summary.affected_subsystems[{i}] must be a string")
                    continue
                wc = word_count(s)
                if not (1 <= wc <= INTENT_SUBSYSTEM_WORDS_MAX):
                    errors.append(
                        f"intent_summary.affected_subsystems[{i}] is {wc} words, "
                        f"must be 1-{INTENT_SUBSYSTEM_WORDS_MAX}"
                    )

    rationale = data.get("rationale")
    if rationale:
        wc = word_count(str(rationale))
        if wc > RATIONALE_WORD_CAP:
            errors.append(f"intent_summary.rationale is {wc} words, cap is {RATIONALE_WORD_CAP}")
        errors.extend(check_blacklist("intent_summary.rationale", str(rationale)))

    return errors


def validate_risk(text: str) -> list[str]:
    errors = []
    try:
        data = parse_yaml(text)
    except Exception as e:
        return [f"merge_risk_summary YAML parse error: {e}"]

    if not isinstance(data, dict):
        return ["merge_risk_summary root must be a YAML mapping"]

    for k in RISK_REQUIRED:
        if k not in data:
            errors.append(f"merge_risk_summary missing required field: {k}")

    rc = data.get("risk_class")
    if isinstance(rc, str) and rc.strip() not in RISK_CLASS_VALUES:
        errors.append(f"merge_risk_summary.risk_class {rc!r} not in {sorted(RISK_CLASS_VALUES)}")

    rev = data.get("reversibility")
    if isinstance(rev, str) and rev.strip() not in REVERSIBILITY_VALUES:
        errors.append(f"merge_risk_summary.reversibility {rev!r} not in {sorted(REVERSIBILITY_VALUES)}")

    br = data.get("blast_radius")
    if isinstance(br, str) and br.strip() not in BLAST_RADIUS_VALUES:
        errors.append(f"merge_risk_summary.blast_radius {br!r} not in {sorted(BLAST_RADIUS_VALUES)}")

    rationale = data.get("rationale")
    if rationale:
        wc = word_count(str(rationale))
        if wc > RATIONALE_WORD_CAP:
            errors.append(f"merge_risk_summary.rationale is {wc} words, cap is {RATIONALE_WORD_CAP}")
        errors.extend(check_blacklist("merge_risk_summary.rationale", str(rationale)))

    return errors


# ───── CLI ─────


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intent", type=Path, help="path to intent_summary.md")
    ap.add_argument("--risk", type=Path, help="path to merge_risk_summary.md")
    args = ap.parse_args()

    if not args.intent and not args.risk:
        sys.exit("usage: validate_strategic_package.py --intent <p> --risk <p>")

    all_errors: list[str] = []

    if args.intent:
        if not args.intent.exists():
            all_errors.append(f"intent file not found: {args.intent}")
        else:
            all_errors.extend(validate_intent(args.intent.read_text()))

    if args.risk:
        if not args.risk.exists():
            all_errors.append(f"risk file not found: {args.risk}")
        else:
            all_errors.extend(validate_risk(args.risk.read_text()))

    if all_errors:
        for e in all_errors:
            print(f"REJECT: {e}", file=sys.stderr)
        return 1

    print("PASS: strategic package valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
