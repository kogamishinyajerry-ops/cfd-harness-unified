#!/usr/bin/env python3
"""Structural integrity verification for the V66-B canonical eval set.

Checks:
  1. INDEX.md exists and contains a roster table referencing E01..E30
  2. Each Ennn case is documented either as detail file (E*_*.md) or in a
     batched file (B*_*.md) whose body mentions the case ID
  3. Every advisor rule cited in INDEX.md actually exists in
     `.planning/methodology/advisor_rules_v66b_expansion.md`
     OR the V64-A baseline rules referenced in the SDK doc
  4. Every eval run log references only valid case IDs

Exit codes:
  0 = structural integrity verified
  1 = missing case documentation
  2 = orphan advisor rule reference
  3 = run log cites invalid case ID
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = ROOT / ".planning" / "evals"
CANONICAL = EVAL_ROOT / "canonical"
RUNS = EVAL_ROOT / "runs"
ADVISOR_RULES_V66B = ROOT / ".planning" / "methodology" / "advisor_rules_v66b_expansion.md"
SDK_DOC = ROOT / ".planning" / "sdk" / "V66B_advisor_sdk.md"

# Eval case IDs the framework defines
EXPECTED_CASE_IDS = [f"E{n:02d}" for n in range(1, 31)]


def check_index_roster() -> tuple[int, list[str]]:
    index = CANONICAL / "INDEX.md"
    if not index.exists():
        return 1, ["INDEX.md missing"]
    content = index.read_text()
    missing = []
    for cid in EXPECTED_CASE_IDS:
        if cid not in content:
            missing.append(cid)
    return (1 if missing else 0), missing


def check_case_documentation() -> tuple[int, dict]:
    """Each E** must appear in either a detail file or a batched file body."""
    missing = {}
    for cid in EXPECTED_CASE_IDS:
        # Detail file pattern: E01_*.md
        detail_glob = list(CANONICAL.glob(f"{cid}_*.md"))
        if detail_glob:
            continue
        # Batched file containing the case ID in its body
        batched_hit = False
        for bf in CANONICAL.glob("B*_*.md"):
            body = bf.read_text()
            # Look for the case section header pattern `## E07 ·` etc
            if re.search(rf"## *{cid}\b", body):
                batched_hit = True
                break
        if not batched_hit:
            missing[cid] = "no detail file and not in any batched file"
    return (1 if missing else 0), missing


def collect_advisor_rules() -> set:
    rules = set()
    # V66-B new rules
    if ADVISOR_RULES_V66B.exists():
        body = ADVISOR_RULES_V66B.read_text()
        # Match `## RULE N · `name` (...)` pattern
        for m in re.finditer(r"## *RULE *\d+ *·.*?`([a-z_][a-z0-9_]*)`", body):
            rules.add(m.group(1))
    # V64-A baseline rules from SDK doc §2 list
    if SDK_DOC.exists():
        body = SDK_DOC.read_text()
        for m in re.finditer(r"`([a-z_][a-z0-9_]*_advisor)`", body):
            rules.add(m.group(1))
        for m in re.finditer(r"`(shm_dict_validator|stl_face_label_validator|virtual_interface_detector|unit_detector|inlet_outlet_validator|bc_type_name_validity_advisor)`", body):
            rules.add(m.group(1))
    return rules


KNOWN_V13X_CANDIDATES = {
    "compressibility_regime_advisor",
    "mesh_resolution_advisor",
    "rhoCentralFoam_compatibility_advisor",
    "separation_resolution_advisor",
    "shock_capture_quality_advisor",
    "substrate_inspection_advisor",
    "statistics_averaging_advisor",
    "turbulence_model_advisor",
    "yplus_target_validation_advisor",
    "residual_gate_qualifier_advisor",
    "transition_onset_validator_advisor",
    "shock_capturing_scheme_advisor",
    "multi_element_high_lift_advisor",
}


def check_advisor_references() -> tuple[int, list]:
    """Find advisor rule names cited in INDEX.md / eval files; verify they exist
    OR are explicitly registered V13x candidates."""
    known = collect_advisor_rules() | KNOWN_V13X_CANDIDATES
    cited = set()
    for f in list(CANONICAL.rglob("*.md")) + list(RUNS.rglob("*.md")):
        body = f.read_text()
        for m in re.finditer(r"`([a-z_][a-z0-9_]*_advisor)`", body):
            cited.add(m.group(1))
        for m in re.finditer(r"`(shm_dict_validator|stl_face_label_validator|virtual_interface_detector|unit_detector|inlet_outlet_validator|bc_type_name_validity_advisor)`", body):
            cited.add(m.group(1))

    orphan = sorted(cited - known)
    return (2 if orphan else 0), orphan


def check_run_log_case_refs() -> tuple[int, dict]:
    """Run logs cite case IDs; verify all are in EXPECTED_CASE_IDS."""
    invalid = {}
    for f in RUNS.rglob("*.md"):
        body = f.read_text()
        # Find E** references like `E03`, `E16`, etc.
        cited = set(re.findall(r"\bE\d{2}\b", body))
        bad = sorted(c for c in cited if c not in EXPECTED_CASE_IDS)
        if bad:
            invalid[f.name] = bad
    return (3 if invalid else 0), invalid


def main() -> int:
    overall = 0
    rc, missing_idx = check_index_roster()
    if rc:
        print(f"FAIL · INDEX missing case IDs: {missing_idx}", file=sys.stderr)
        overall = max(overall, rc)
    else:
        print(f"OK · INDEX roster references all {len(EXPECTED_CASE_IDS)} case IDs")

    rc, missing_doc = check_case_documentation()
    if rc:
        print(f"FAIL · Cases lacking documentation:", file=sys.stderr)
        for cid, why in missing_doc.items():
            print(f"  {cid}: {why}", file=sys.stderr)
        overall = max(overall, rc)
    else:
        print(f"OK · All {len(EXPECTED_CASE_IDS)} cases documented (detail or batched)")

    rc, orphans = check_advisor_references()
    if rc:
        print(f"FAIL · Cited advisor rules not in SDK / rules doc:", file=sys.stderr)
        for o in orphans:
            print(f"  {o}", file=sys.stderr)
        overall = max(overall, rc)
    else:
        print(f"OK · All advisor rule citations resolve")

    rc, bad_refs = check_run_log_case_refs()
    if rc:
        print(f"FAIL · Run logs cite invalid case IDs:", file=sys.stderr)
        for fn, ids in bad_refs.items():
            print(f"  {fn}: {ids}", file=sys.stderr)
        overall = max(overall, rc)
    else:
        print(f"OK · Run logs cite only valid case IDs")

    if overall == 0:
        print("\n=== eval set structural integrity verified ===")
    return overall


if __name__ == "__main__":
    sys.exit(main())
