#!/usr/bin/env python3
"""Validate Gold Standard YAML files against the JSON schema."""
import argparse, json, sys, yaml
from pathlib import Path

def validate_gold_standard(yaml_path: Path, schema: dict) -> tuple[bool, list]:
    """Validate a Gold Standard YAML file against the schema.

    Returns (pass, errors).
    """
    errors = []

    # Load YAML (multi-document)
    try:
        docs = list(yaml.safe_load_all(open(yaml_path)))
    except Exception as e:
        return False, [f"YAML parse error: {e}"]

    if not docs:
        return False, ["Empty YAML file"]

    for i, doc in enumerate(docs):
        # Required fields per document
        for field in ['quantity', 'reference_values', 'tolerance', 'source']:
            if field not in doc:
                errors.append(f"doc[{i}]: missing required field '{field}'")

        # quantity must be non-empty string
        q = doc.get('quantity', '')
        if not isinstance(q, str) or not q:
            errors.append(f"doc[{i}]: 'quantity' must be a non-empty string, got {type(q).__name__}")

        # reference_values must be non-empty list
        rv = doc.get('reference_values', [])
        if not isinstance(rv, list) or len(rv) == 0:
            errors.append(f"doc[{i}] ({q}): 'reference_values' must be a non-empty list")
        else:
            for j, ref in enumerate(rv):
                if not isinstance(ref, dict):
                    errors.append(f"doc[{i}][{j}]: reference_values[{j}] must be a dict, got {type(ref).__name__}")

        # tolerance: must be number in [0, 1] or structured dict
        tol = doc.get('tolerance')
        if tol is None:
            errors.append(f"doc[{i}] ({q}): 'tolerance' is required")
        elif isinstance(tol, (int, float)):
            if not (0 <= tol <= 1):
                errors.append(f"doc[{i}] ({q}): tolerance={tol} out of range [0, 1]")
        elif isinstance(tol, dict):
            if 'mode' not in tol:
                errors.append(f"doc[{i}] ({q}): tolerance dict missing 'mode' field")
        else:
            errors.append(f"doc[{i}] ({q}): tolerance must be number or dict, got {type(tol).__name__}")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description='Validate Gold Standard YAML files')
    parser.add_argument('--schema', default='knowledge/schemas/gold_standard_schema.json',
                        help='Path to JSON schema')
    parser.add_argument('--gold-dir', default='knowledge/gold_standards',
                        help='Directory containing Gold Standard YAML files')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    gold_dir = Path(args.gold_dir)
    if not gold_dir.exists():
        print(f"ERROR: Gold standards directory not found: {gold_dir}")
        sys.exit(1)

    yaml_files = sorted(gold_dir.glob('*.yaml'))
    if not yaml_files:
        print(f"ERROR: No .yaml files found in {gold_dir}")
        sys.exit(1)

    total = 0
    passed = 0
    results = {}

    for yaml_path in yaml_files:
        ok, errors = validate_gold_standard(yaml_path, None)
        results[yaml_path.name] = (ok, errors)
        total += 1
        if ok:
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"
        print(f"[{status}] {yaml_path.name} ({len(errors)} errors)")
        if args.verbose and errors:
            for e in errors[:5]:
                print(f"       {e}")
            if len(errors) > 5:
                print(f"       ... and {len(errors)-5} more")

    print(f"\n=== Result: {passed}/{total} files passed ===")
    if passed == total:
        print("ALL VALIDATED")
        sys.exit(0)
    else:
        print("VALIDATION FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
