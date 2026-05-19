"""V69.1 · canonical eval case YAML frontmatter schema validator.

Runs as part of pre-commit + per-iter physics scorer to ensure every
`.planning/evals/canonical/E*.md` file has a complete frontmatter shape.

Usage:
    python3 scripts/governance/validate_canonical_eval_schema.py

Exit code 0 = all files valid · non-zero = schema violation (path + reason
printed to stderr).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_DIR = REPO_ROOT / ".planning" / "evals" / "canonical"

REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "eval_case_id": str,
    "case_id": str,
    "title": str,
    "v_row_attribution": (str, list),
    "v_row_class": str,
    "physics_regime": str,
    "status": str,
    "sandbox_path": str,
    "substrate_lineage": str,
    "expected_verdict_signature": str,
}


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Extract the leading --- ... --- YAML block. Returns None if absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None
    body = "\n".join(lines[1:end_idx])
    try:
        loaded = yaml.safe_load(body)
    except yaml.YAMLError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def validate_one(path: Path) -> list[str]:
    """Return list of error strings for one case file. Empty list = valid."""
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"unreadable: {exc}"]
    fm = parse_frontmatter(text)
    if fm is None:
        return ["missing or malformed YAML frontmatter"]
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in fm:
            errors.append(f"missing required field: {field}")
            continue
        value = fm[field]
        if not isinstance(value, expected_type):
            errors.append(
                f"field {field!r}: expected {expected_type}, got "
                f"{type(value).__name__}"
            )
    # eval_case_id should match filename prefix
    expected_prefix = path.stem.split("_")[0]
    declared_id = str(fm.get("eval_case_id", ""))
    if declared_id and declared_id != expected_prefix:
        errors.append(
            f"eval_case_id={declared_id!r} doesn't match filename prefix "
            f"{expected_prefix!r}"
        )
    return errors


def main() -> int:
    if not CANONICAL_DIR.is_dir():
        print(f"canonical dir missing: {CANONICAL_DIR}", file=sys.stderr)
        return 2
    case_files = sorted(
        p
        for p in CANONICAL_DIR.glob("E*.md")
        if p.is_file() and not p.name.startswith("_")
    )
    if not case_files:
        print("no canonical case files found", file=sys.stderr)
        return 2
    total_errors = 0
    for path in case_files:
        errors = validate_one(path)
        if errors:
            total_errors += len(errors)
            for err in errors:
                print(f"{path.relative_to(REPO_ROOT)}: {err}", file=sys.stderr)
    if total_errors:
        print(
            f"\nFAIL · {total_errors} schema violation(s) across "
            f"{len(case_files)} canonical eval case file(s)",
            file=sys.stderr,
        )
        return 1
    print(
        f"OK · {len(case_files)} canonical eval case files validate "
        f"against schema ({len(REQUIRED_FIELDS)} required fields each)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
