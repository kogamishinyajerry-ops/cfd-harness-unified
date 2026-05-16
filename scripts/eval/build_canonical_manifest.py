#!/usr/bin/env python3
"""Build SHA-256 manifest for the canonical eval set.

Walks `.planning/evals/canonical/` and `.planning/evals/runs/`, computes SHA-256
for each .md file, writes MANIFEST.sha256 with one line per file:

    <sha256>  <relpath>

The manifest is the byte-repro contract: subsequent verification runs MUST
produce identical hashes for unchanged files. Drift indicates either:
  (a) intentional edit that needs `--update` to refresh the manifest
  (b) accidental corruption / unexpected modification

Usage:
  python3 scripts/eval/build_canonical_manifest.py            # build/verify
  python3 scripts/eval/build_canonical_manifest.py --update   # refresh manifest

Exit codes:
  0 = manifest matches all files (or --update succeeded)
  1 = drift detected (file modified vs manifest)
  2 = missing file referenced in manifest
  3 = orphan file present but not in manifest
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = ROOT / ".planning" / "evals"
MANIFEST = EVAL_ROOT / "MANIFEST.sha256"

PLANNING_ROOT = ROOT / ".planning"
TRACKED_DIRS = [
    EVAL_ROOT / "canonical",
    EVAL_ROOT / "runs",
    PLANNING_ROOT / "decisions",
    PLANNING_ROOT / "methodology",
    PLANNING_ROOT / "sdk",
]


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_tracked_files() -> list[Path]:
    files = []
    for d in TRACKED_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.md")):
            if p.is_file():
                files.append(p)
    return files


def build_manifest():
    files = collect_tracked_files()
    lines = []
    for p in files:
        rel = p.relative_to(ROOT)
        sha = sha256_of(p)
        lines.append(f"{sha}  {rel}")
    MANIFEST.write_text("\n".join(lines) + "\n")
    print(f"Wrote {MANIFEST} with {len(files)} entries.")


def verify_manifest() -> int:
    if not MANIFEST.exists():
        print(f"Manifest missing: {MANIFEST}", file=sys.stderr)
        print("Run with --update to create it.", file=sys.stderr)
        return 2

    expected = {}
    for line in MANIFEST.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            print(f"Malformed manifest line: {line!r}", file=sys.stderr)
            return 2
        sha, rel = parts
        expected[rel] = sha

    actual_files = {str(p.relative_to(ROOT)): p for p in collect_tracked_files()}
    expected_paths = set(expected.keys())
    actual_paths = set(actual_files.keys())

    missing = expected_paths - actual_paths
    orphan = actual_paths - expected_paths

    exit_code = 0
    if missing:
        print(f"MISSING (in manifest but file gone): {len(missing)}", file=sys.stderr)
        for m in sorted(missing):
            print(f"  {m}", file=sys.stderr)
        exit_code = 2

    if orphan:
        print(f"ORPHAN (file exists but not in manifest): {len(orphan)}", file=sys.stderr)
        for o in sorted(orphan):
            print(f"  {o}", file=sys.stderr)
        exit_code = max(exit_code, 3)

    drift = []
    for rel in sorted(expected_paths & actual_paths):
        actual_sha = sha256_of(actual_files[rel])
        if actual_sha != expected[rel]:
            drift.append((rel, expected[rel], actual_sha))

    if drift:
        print(f"DRIFT (content changed vs manifest): {len(drift)}", file=sys.stderr)
        for rel, exp_sha, act_sha in drift:
            print(f"  {rel}: expected {exp_sha[:16]}..., got {act_sha[:16]}...", file=sys.stderr)
        exit_code = max(exit_code, 1)

    if exit_code == 0:
        print(f"OK · {len(expected)} files verified · no drift / missing / orphan.")
    return exit_code


def main() -> int:
    args = sys.argv[1:]
    if "--update" in args:
        build_manifest()
        return 0
    return verify_manifest()


if __name__ == "__main__":
    sys.exit(main())
