"""case_manifest.yaml loader + validator."""
from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Dict

import yaml
from jsonschema import Draft7Validator


SCHEMA_PACKAGE = "cfdtrust.schemas"
SCHEMA_FILENAME = "case_manifest.schema.json"


class ManifestError(Exception):
    """Raised when a case_manifest.yaml is missing or invalid."""


def case_dir(path: str | Path) -> Path:
    p = Path(path)
    if not p.exists():
        raise ManifestError(f"case directory does not exist: {p}")
    if not p.is_dir():
        raise ManifestError(f"case path is not a directory: {p}")
    return p


def manifest_path(path: str | Path) -> Path:
    p = case_dir(path) / "case_manifest.yaml"
    if not p.exists():
        raise ManifestError(f"case_manifest.yaml not found in: {path}")
    return p


def load_schema() -> Dict[str, Any]:
    with resources.files(SCHEMA_PACKAGE).joinpath(SCHEMA_FILENAME).open("r") as f:
        return json.load(f)


def load_manifest(path: str | Path) -> Dict[str, Any]:
    mp = manifest_path(path)
    with mp.open("r") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ManifestError(f"manifest is not a mapping: {mp}")
    return data


def validate_manifest(path: str | Path) -> Dict[str, Any]:
    """Load + validate. Return the parsed manifest if valid; raise ManifestError otherwise."""
    data = load_manifest(path)
    schema = load_schema()
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        lines = []
        for e in errors:
            loc = "/".join(str(p) for p in e.absolute_path) or "<root>"
            lines.append(f"  - {loc}: {e.message}")
        raise ManifestError(
            "case_manifest.yaml failed schema validation:\n" + "\n".join(lines)
        )
    return data
