from __future__ import annotations

from pathlib import Path

import json
import yaml

from scripts.validate_gold_standards import (
    load_schema,
    load_gold_standard_payload,
    main,
    validate_directory,
    validate_gold_standard,
)


def test_schema_json_parseable(repo_root: Path):
    schema_path = repo_root / "knowledge" / "schemas" / "gold_standard_schema.json"
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert "$defs" in data
    assert "Relationships" in data["$defs"]


def test_structured_alias_files_include_relationships(repo_root: Path):
    alias_files = [
        repo_root / "knowledge" / "gold_standards" / "lid_driven_cavity_benchmark.yaml",
        repo_root / "knowledge" / "gold_standards" / "backward_facing_step_steady.yaml",
        repo_root / "knowledge" / "gold_standards" / "cylinder_crossflow.yaml",
    ]
    for path in alias_files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        relationships = data.get("relationships", {})
        assert "solver_reuse" in relationships
        assert "geometry_similarity" in relationships
        assert "physics_analogy" in relationships


def test_validator_passes_current_corpus(repo_root: Path):
    results = validate_directory(
        repo_root / "knowledge" / "gold_standards",
        repo_root / "knowledge" / "schemas" / "gold_standard_schema.json",
    )
    assert results
    assert all(ok for ok, _ in results.values())


def test_validator_is_deterministic(repo_root: Path):
    schema = load_schema(repo_root / "knowledge" / "schemas" / "gold_standard_schema.json")
    target = repo_root / "knowledge" / "gold_standards" / "lid_driven_cavity_benchmark.yaml"
    left = validate_gold_standard(target, schema)
    right = validate_gold_standard(target, schema)
    assert left == right


def test_payload_loader_supports_structured_and_legacy(repo_root: Path):
    structured = load_gold_standard_payload(
        repo_root / "knowledge" / "gold_standards" / "lid_driven_cavity_benchmark.yaml"
    )
    legacy = load_gold_standard_payload(
        repo_root / "knowledge" / "gold_standards" / "lid_driven_cavity.yaml"
    )
    assert isinstance(structured, dict)
    assert isinstance(legacy, list)


def test_validator_rejects_missing_required_field(tmp_path: Path, repo_root: Path):
    schema = load_schema(repo_root / "knowledge" / "schemas" / "gold_standard_schema.json")
    broken = tmp_path / "broken.yaml"
    broken.write_text("case_id: broken_case\nobservables: []\n", encoding="utf-8")
    ok, errors = validate_gold_standard(broken, schema)
    assert not ok
    assert errors


def test_validator_cli_reports_success(monkeypatch, capsys, repo_root: Path):
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_gold_standards.py",
            "--schema",
            str(repo_root / "knowledge" / "schemas" / "gold_standard_schema.json"),
            "--gold-dir",
            str(repo_root / "knowledge" / "gold_standards"),
        ],
    )
    try:
        main()
    except SystemExit as exc:
        assert exc.code == 0
    output = capsys.readouterr().out
    assert "ALL VALIDATED" in output


def test_load_payload_empty_file_raises(tmp_path: Path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    try:
        load_gold_standard_payload(empty)
    except ValueError as exc:
        assert "Empty YAML file" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty YAML payload")


def test_validator_cli_missing_gold_dir(monkeypatch, capsys, repo_root: Path):
    missing_dir = repo_root / "does-not-exist"
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_gold_standards.py",
            "--schema",
            str(repo_root / "knowledge" / "schemas" / "gold_standard_schema.json"),
            "--gold-dir",
            str(missing_dir),
        ],
    )
    try:
        main()
    except SystemExit as exc:
        assert exc.code == 1
    output = capsys.readouterr().out
    assert "Gold standards directory not found" in output


def test_validator_cli_no_yaml_files(monkeypatch, capsys, tmp_path: Path, repo_root: Path):
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_gold_standards.py",
            "--schema",
            str(repo_root / "knowledge" / "schemas" / "gold_standard_schema.json"),
            "--gold-dir",
            str(tmp_path),
        ],
    )
    try:
        main()
    except SystemExit as exc:
        assert exc.code == 1
    output = capsys.readouterr().out
    assert "No .yaml files found" in output


def test_validator_cli_verbose_failure_reports_nested_errors(monkeypatch, capsys, tmp_path: Path, repo_root: Path):
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        "case_id: broken_case\nsource: broken\nobservables:\n  - tolerance: 0.1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_gold_standards.py",
            "--schema",
            str(repo_root / "knowledge" / "schemas" / "gold_standard_schema.json"),
            "--gold-dir",
            str(tmp_path),
            "--verbose",
        ],
    )
    try:
        main()
    except SystemExit as exc:
        assert exc.code == 1
    output = capsys.readouterr().out
    assert "VALIDATION FAILED" in output
    assert "observables" in output or "load_error" in output
