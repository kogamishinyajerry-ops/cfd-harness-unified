#!/usr/bin/env python3
"""W2/Q4 — counter truth table dry-run for DEC-V61-087 §5.

Per DEC-V61-087 §Q4: assume Kogami already existed and approved each historical
DEC retroactively. Apply §5.1 truth table to compute counter_increment per DEC.
Then verify total matches STATE.md historical record (no drift).

Sample DECs (per DEC §Q4 v3 R2):
  - V61-006 (autonomous_governance: false, external-gate gold) → row 2 → +0
  - V61-011 (autonomous_governance: false, Q-2 R-A-relabel) → row 2 → +0
  - V61-074 (autonomous_governance: true, P2-T1)             → row 1 → +1
  - V61-075 (autonomous_governance: true, P2-T2)             → row 1 → +1
  - V61-086 (autonomous_governance: true, GOV-1 v0.7 docs)   → row 1 → +1

Total expected: +3 advances across 5 sample DECs.

Pass criterion: actual computation matches expected; no counter drift introduced
by the §5.1 truth table.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEC_DIR = Path(".planning/decisions")

# Sample DECs to dry-run (per DEC §Q4)
SAMPLES = [
    {"id": "V61-006", "expected_advance": 0, "expected_row": 2, "label": "external-gate B-class gold"},
    {"id": "V61-011", "expected_advance": 0, "expected_row": 2, "label": "external-gate Q-2 R-A relabel"},
    {"id": "V61-074", "expected_advance": 1, "expected_row": 1, "label": "P2-T1 ExecutorMode skeleton"},
    {"id": "V61-075", "expected_advance": 1, "expected_row": 1, "label": "P2-T2 docker_openfoam substantialization"},
    {"id": "V61-086", "expected_advance": 1, "expected_row": 1, "label": "GOV-1 v0.7 tier-(c)→(a) trace"},
]


def find_dec_file(dec_id: str) -> Path | None:
    """Find the DEC file by ID. Tries filename pattern then content search.

    Filename pattern: 2026-MM-DD_v61_NNN_*.md (newer DECs).
    Older DECs (V61-006/011) use descriptive filenames without v61_NNN; fall
    back to grep `decision_id: DEC-V61-NNN` in frontmatter.
    """
    nnn_int = int(dec_id.split("-")[1])

    # First: filename pattern (works for V61-074, V61-075, V61-086)
    pattern = f"*v61_{nnn_int:03d}_*.md"
    matches = list(DEC_DIR.glob(pattern))
    if matches:
        return matches[0]

    # Fall back: content search for decision_id frontmatter
    target = f"decision_id: DEC-V61-{nnn_int:03d}"
    for f in sorted(DEC_DIR.glob("*.md")):
        try:
            head = f.read_text()[:600]  # frontmatter is at top
            if target in head:
                return f
        except (OSError, UnicodeDecodeError):
            continue

    return None


def parse_frontmatter(text: str) -> dict:
    """Tiny YAML-ish parser for the autonomous_governance field only."""
    if not text.startswith("---\n"):
        return {}
    try:
        end = text.index("\n---\n", 4)
    except ValueError:
        return {}
    fm = text[4:end]

    out = {}
    for line in fm.splitlines():
        m = re.match(r"^(autonomous_governance|status):\s*(.+?)(?:\s*#.*)?$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip("'\"")
            # autonomous_governance: 'true' or 'false' string
            if key == "autonomous_governance":
                out[key] = val.lower() == "true"
            else:
                out[key] = val
    return out


def apply_truth_table(autonomous_governance: bool | None) -> tuple[int, int, str]:
    """Apply §5.1 truth table.

    Returns (counter_increment, row_number, label).
    """
    if autonomous_governance is True:
        return (1, 1, "Normal DEC (autonomous_governance: true)")
    if autonomous_governance is False:
        return (0, 2, "External-gate DEC (autonomous_governance: false, N/A)")
    return (-1, 0, "ERROR: autonomous_governance field missing or unparseable")


def main() -> int:
    print("=== W2/Q4 counter truth table dry-run ===")
    print(f"Sample size: {len(SAMPLES)} historical DECs")
    print()

    actual_total = 0
    expected_total = sum(s["expected_advance"] for s in SAMPLES)
    drifts = []

    for s in SAMPLES:
        path = find_dec_file(s["id"])
        if not path:
            drifts.append(f"DEC {s['id']} file not found in {DEC_DIR}")
            continue

        text = path.read_text()
        fm = parse_frontmatter(text)
        ag = fm.get("autonomous_governance")
        increment, row, label = apply_truth_table(ag)

        marker = "✓" if increment == s["expected_advance"] else "✗"
        print(f"  {marker} {s['id']:8} [{s['label']:50}] file={path.name}")
        print(f"      autonomous_governance: {ag} → row {row} ({label})")
        print(f"      expected +{s['expected_advance']}, computed +{increment}")
        if increment != s["expected_advance"]:
            drifts.append(
                f"DEC {s['id']}: expected +{s['expected_advance']}, computed +{increment} "
                f"(autonomous_governance={ag})"
            )
        actual_total += increment
        print()

    print(f"=== summary ===")
    print(f"  expected total advance: +{expected_total}")
    print(f"  computed total advance: +{actual_total}")
    print(f"  drift: {actual_total - expected_total}")
    print()

    verdict = "PASS" if actual_total == expected_total and not drifts else "FAIL"
    print(f"=== verdict: {verdict} ===")
    if drifts:
        print()
        print("Drifts detected:")
        for d in drifts:
            print(f"  - {d}")

    # Save report
    report = {
        "test": "Q4_counter_truth_table_dry_run",
        "verdict": verdict,
        "expected_total_advance": expected_total,
        "computed_total_advance": actual_total,
        "drift": actual_total - expected_total,
        "samples": [{**s, "computed_advance": apply_truth_table(parse_frontmatter((find_dec_file(s["id"]) or Path("/dev/null")).read_text() if find_dec_file(s["id"]) else "").get("autonomous_governance"))[0]} for s in SAMPLES],
        "drifts": drifts,
    }
    out_path = Path(".planning/reviews/kogami/w2_q4_counter_truth_table_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport: {out_path}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
