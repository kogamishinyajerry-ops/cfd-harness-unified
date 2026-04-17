#!/usr/bin/env python3
"""Validate Gold Standard YAML files against the JSON schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from jsonschema import Draft7Validator


def load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load the JSON schema."""
    return json.loads(schema_path.read_text(encoding="utf-8"))


def load_gold_standard_payload(yaml_path: Path) -> Any:
    """Load a gold standard YAML file as either a structured dict or legacy doc list."""
    docs = list(yaml.safe_load_all(yaml_path.read_text(encoding="utf-8")))
    if not docs:
        raise ValueError("Empty YAML file")
    if len(docs) == 1 and isinstance(docs[0], dict) and "observables" in docs[0]:
        return docs[0]
    return docs


def _format_error(error) -> str:  # noqa: ANN001
    path = "/".join(str(item) for item in error.absolute_path)
    if path:
        return f"{path}: {error.message}"
    return error.message


def validate_gold_standard(yaml_path: Path, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate one Gold Standard YAML file against the schema."""
    try:
        payload = load_gold_standard_payload(yaml_path)
    except Exception as exc:
        return False, [f"load_error: {exc}"]

    validator = Draft7Validator(schema)
    errors = sorted(
        (_format_error(error) for error in validator.iter_errors(payload)),
        key=str,
    )
    return len(errors) == 0, list(errors)


def validate_directory(gold_dir: Path, schema_path: Path) -> Dict[str, Tuple[bool, List[str]]]:
    """Validate all YAML files in a directory."""
    schema = load_schema(schema_path)
    results: Dict[str, Tuple[bool, List[str]]] = {}
    for yaml_path in sorted(gold_dir.glob("*.yaml")):
        results[yaml_path.name] = validate_gold_standard(yaml_path, schema)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Gold Standard YAML files")
    parser.add_argument(
        "--schema",
        default="knowledge/schemas/gold_standard_schema.json",
        help="Path to JSON schema",
    )
    parser.add_argument(
        "--gold-dir",
        default="knowledge/gold_standards",
        help="Directory containing Gold Standard YAML files",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    gold_dir = Path(args.gold_dir)
    schema_path = Path(args.schema)
    if not gold_dir.exists():
        print(f"ERROR: Gold standards directory not found: {gold_dir}")
        sys.exit(1)
    if not schema_path.exists():
        print(f"ERROR: Schema not found: {schema_path}")
        sys.exit(1)

    yaml_files = sorted(gold_dir.glob("*.yaml"))
    if not yaml_files:
        print(f"ERROR: No .yaml files found in {gold_dir}")
        sys.exit(1)

    results = validate_directory(gold_dir, schema_path)
    passed = 0
    total = len(results)

    for filename in sorted(results):
        ok, errors = results[filename]
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {filename} ({len(errors)} errors)")
        if args.verbose and errors:
            for error in errors:
                print(f"       {error}")

    print(f"\n=== Result: {passed}/{total} files passed ===")
    if passed == total:
        print("ALL VALIDATED")
        sys.exit(0)

    print("VALIDATION FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()
