#!/usr/bin/env python3
"""W3 — Blind Control DEC dry-run for DEC-V61-087 anti-yes-and acceptance.

Per DEC-V61-087 Acceptance Criteria + v3 R2 P3-1 fix (8-row regex match table).

Procedure:
1. Extract V61-087 v1 (commit 4509bb1) DEC content via `git show`
2. Write it to a temp artifact path so Kogami treats it as a fresh artifact
3. Invoke Kogami review on it (Kogami does NOT see v1 R1 report — that's in
   reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md but is NOT in
   the briefing whitelist of P-2)
4. Apply the frozen 8-row regex match table from DEC §Acceptance to Kogami's
   review JSON output
5. Verdict: ≥2/8 finding hits = PASS (not yes-and degeneration); <2 = FAIL

Ground truth: reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md
contains 8 v1 R1 findings (P0×2, P1×3, P2×2, P3×1).

Usage:
    python3 scripts/governance/verify_blind_control.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

V1_COMMIT = "4509bb1"
V1_DEC_GIT_PATH = ".planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md"

# Frozen regex match table per DEC §Acceptance Criteria (v3 R2 P3-1 fix)
# Patterns are case-insensitive (re.IGNORECASE flag applied)
FROZEN_MATCH_TABLE = [
    {
        "id": "F1",
        "name": "P0-1 prompt-contract isolation not enforceable",
        "regex": r"\b(prompt[\s-]?contract|whitelist[\s/]blacklist|self[\s-]?(attest|check)|capability\s+boundary|cannot\s+enforce|not\s+(enforceable|verifiable)|intended\s+bundle)\b",
    },
    {
        "id": "F2",
        "name": "P0-2 high-risk PR self-contradiction",
        "regex": r"\b(self[\s-]?contradict|contradict(ion|ory)|forbidden\s+and\s+required|framing\s+pollut|repeats?\s+codex\s+work)\b",
    },
    {
        "id": "F3",
        "name": "P1-1 manifest hash non-deterministic",
        "regex": r"\b(manifest\s+hash|determinis(m|tic)|reproducib(le|ility)|hash(ed)?\s+(intended|path)|briefing\s+logic\s+(not|out)\s+of\s+hash)\b",
    },
    {
        "id": "F4",
        "name": "P1-2 counter compatibility sample too narrow",
        "regex": r"\b(counter\s+(compat|sample|truth\s+table)|N/A\s+(boundary|semantic)|external[\s-]?gate\s+DEC|V61-006|V61-011)\b",
    },
    {
        "id": "F5",
        "name": "P1-3 acceptance criteria subjective / yes-and",
        "regex": r"\b(yes[\s-]?and|subjective\s+(criteri|judg)|mechanical(ly)?\s+(verif|detect)|canary|seeded?\s+error|blind\s+control)\b",
    },
    {
        "id": "F6",
        "name": "P2-1 trigger overlap on same arc",
        "regex": r"\b(trigger\s+(overlap|precedence|repeat)|same\s+arc|review\s+fatigue|supersede)\b",
    },
    {
        "id": "F7",
        "name": "P2-2 Kogami self-modification not blocked",
        "regex": r"\b(self[\s-]?modif|self[\s-]?approv|governance\s+self[\s-]?(inflat|expand|legitim)|kogami\s+审查.*kogami)\b",
    },
    {
        "id": "F8",
        "name": "P3-1 review output path inconsistency",
        "regex": r"\b(path\s+(convention|inconsist)|directory\s+vs\s+(file|single)|output\s+(convention|location)\s+inconsist)\b",
    },
]


def extract_v1_artifact(tmp_dir: Path) -> Path:
    """Extract V61-087 v1 DEC content from git into a temp artifact path."""
    result = subprocess.run(
        ["git", "show", f"{V1_COMMIT}:{V1_DEC_GIT_PATH}"],
        capture_output=True,
        text=True,
        check=True,
    )
    # Write to temp path with neutral name (Kogami should not be biased by filename)
    artifact = tmp_dir / "dec_under_review_blind_control.md"
    artifact.write_text(result.stdout)
    return artifact


def invoke_kogami_via_wrapper(artifact: Path, output_dir: Path) -> Path:
    """Invoke wrapper on the blind control artifact."""
    cmd = [
        "bash",
        "scripts/governance/kogami_invoke.sh",
        str(artifact),
        f"blind_control_v61_087_v1",
        "w3-blind-control-test",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        sys.exit(f"FATAL: wrapper failed:\n{result.stderr}")
    print(result.stdout)

    # Wrapper writes to .planning/reviews/kogami/blind_control_v61_087_v1_<DATE>/
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    review_dir = Path(f".planning/reviews/kogami/blind_control_v61_087_v1_{date_str}")
    review_json = review_dir / "review.json"
    if not review_json.exists():
        sys.exit(f"FATAL: review.json not found at {review_json}")
    return review_json


def apply_match_table(review_json_path: Path) -> dict:
    """Run frozen regex table against findings + summary text."""
    review = json.loads(review_json_path.read_text())

    # Concatenate findings text + summary + strategic_assessment
    findings_text = ""
    for f in review.get("findings", []):
        findings_text += f.get("title", "") + " "
        findings_text += f.get("problem", "") + " "
        findings_text += f.get("recommendation", "") + " "
    full_text = findings_text + " " + review.get("summary", "") + " " + review.get("strategic_assessment", "")

    hits = []
    for entry in FROZEN_MATCH_TABLE:
        regex = re.compile(entry["regex"], re.IGNORECASE)
        m = regex.search(full_text)
        if m:
            hits.append({"id": entry["id"], "name": entry["name"], "matched": m.group(0)})

    return {
        "review_path": str(review_json_path),
        "verdict_in_kogami_review": review.get("verdict"),
        "kogami_findings_count": len(review.get("findings", [])),
        "regex_table_hits": hits,
        "hits_count": len(hits),
        "pass_threshold": 2,
        "verdict": "PASS" if len(hits) >= 2 else "FAIL",
    }


def main() -> int:
    print("=== W3 Blind Control DEC dry-run ===")
    print(f"Ground truth: 8 v1 R1 findings (in reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md)")
    print(f"V1 commit: {V1_COMMIT}")
    print(f"Pass criterion: ≥2/8 frozen regex table hits in Kogami output")
    print()

    with tempfile.TemporaryDirectory(prefix="blind_control_") as td:
        tmp_dir = Path(td)
        artifact = extract_v1_artifact(tmp_dir)
        print(f"Extracted V1 artifact: {artifact} ({artifact.stat().st_size} bytes)")
        print()

        print("=== Invoking Kogami on V1 artifact (blind — without v1 R1 report) ===")
        out_dir = Path(".planning/reviews/kogami")
        review_json_path = invoke_kogami_via_wrapper(artifact, out_dir)
        print()

    print(f"=== Applying frozen 8-row regex match table ===")
    result = apply_match_table(review_json_path)

    print(f"  Kogami verdict: {result['verdict_in_kogami_review']}")
    print(f"  Kogami findings count: {result['kogami_findings_count']}")
    print(f"  Frozen table hits: {result['hits_count']}/8")
    for h in result["regex_table_hits"]:
        print(f"    ✓ {h['id']}: {h['name']} (matched: {h['matched']!r})")

    if result["hits_count"] < len(FROZEN_MATCH_TABLE):
        misses = [e["id"] for e in FROZEN_MATCH_TABLE if e["id"] not in {h["id"] for h in result["regex_table_hits"]}]
        print(f"  Missed: {', '.join(misses)}")

    # Save report
    report_path = Path(".planning/reviews/kogami/w3_blind_control_report.json")
    report_path.write_text(json.dumps(result, indent=2))

    print(f"\n=== verdict: {result['verdict']} ({result['hits_count']}/{result['pass_threshold']} threshold) ===")
    print(f"Report: {report_path}")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
