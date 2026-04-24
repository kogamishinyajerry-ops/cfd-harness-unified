"""CaseProfile loader · P1-T3.

Reads `.planning/case_profiles/{case_id}.yaml` and returns the
`tolerance_policy` dict in the shape `MetricsRegistry.evaluate_all`
expects: `{observable_name: {"tolerance": <float>, ...}}`.

Schema (CaseProfile v1 · additive to G-6 risk_flags):

    case_id: <str>
    schema_version: 1
    last_assessed: <YYYY-MM-DD>
    last_assessed_by: <str>

    risk_flags:             # G-6 (existing)
      - flag_id: ...
        triggered: ...
        justification: ...

    tolerance_policy:       # P1-T3 (NEW · optional block)
      <observable_name>:
        tolerance: <float>  # relative tolerance 0..1 (e.g. 0.05 = 5%)
      <observable_name>:
        tolerance: <float>
      ...

Absent `tolerance_policy` block or absent case file ⇒ empty dict
(downstream MetricsRegistry falls through to observable_def.tolerance).

Plane: Evaluation. Reads YAML via file I/O (not module import) —
ADR-001 plane contracts govern Python import graph, not file reads.
Allowed to read from `.planning/case_profiles/` (repo-relative config).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


# Repo-root-relative path. Resolved lazily so tests can override.
_DEFAULT_CASE_PROFILES_DIR = Path(".planning/case_profiles")


class CaseProfileError(Exception):
    """Raised when a CaseProfile YAML file is malformed beyond
    recoverable defaults (e.g. YAML syntax error, unexpected top-level
    type, tolerance_policy not a dict)."""


def _resolve_case_profiles_dir(override: Optional[Path]) -> Path:
    if override is not None:
        return override
    # Walk up from this module's file to find the repo root (where
    # .planning lives). Falls back to cwd-relative if structure changes.
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / ".planning" / "case_profiles"
        if candidate.is_dir():
            return candidate
    return _DEFAULT_CASE_PROFILES_DIR


def load_case_profile(
    case_id: str,
    *,
    case_profiles_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Return the full parsed CaseProfile dict, or None if the file is absent.

    Used mainly by `load_tolerance_policy`; exposed for callers that need
    other sections (risk_flags, last_assessed, etc.).

    Raises CaseProfileError on malformed YAML.
    """
    root = _resolve_case_profiles_dir(case_profiles_dir)
    path = root / f"{case_id}.yaml"
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            parsed = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise CaseProfileError(
            f"CaseProfile YAML malformed for {case_id!r} at {path}: {exc}"
        ) from exc

    if parsed is None:
        # Empty file — treat as missing sections rather than error.
        return {}
    if not isinstance(parsed, dict):
        raise CaseProfileError(
            f"CaseProfile {case_id!r} top-level must be a mapping; got "
            f"{type(parsed).__name__} at {path}"
        )
    return parsed


def load_tolerance_policy(
    case_id: str,
    *,
    case_profiles_dir: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """Load `tolerance_policy` for `case_id` in the shape that
    `MetricsRegistry.evaluate_all` accepts.

    Returns an empty dict when:
    - Case file is absent
    - File is empty / present but no tolerance_policy block

    Raises CaseProfileError when:
    - YAML is malformed
    - `tolerance_policy` exists but is not a mapping
    - A per-observable entry exists but is not a mapping
    - A `tolerance` field is present but is not a finite number
    """
    profile = load_case_profile(case_id, case_profiles_dir=case_profiles_dir)
    if not profile:
        return {}

    raw = profile.get("tolerance_policy")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise CaseProfileError(
            f"CaseProfile {case_id!r} tolerance_policy must be a mapping; "
            f"got {type(raw).__name__}"
        )

    normalized: Dict[str, Dict[str, Any]] = {}
    for obs_name, entry in raw.items():
        if not isinstance(obs_name, str) or not obs_name.strip():
            raise CaseProfileError(
                f"CaseProfile {case_id!r} tolerance_policy key must be a "
                f"non-empty string; got {obs_name!r}"
            )
        if not isinstance(entry, dict):
            raise CaseProfileError(
                f"CaseProfile {case_id!r} tolerance_policy[{obs_name!r}] "
                f"must be a mapping; got {type(entry).__name__}"
            )
        tol = entry.get("tolerance")
        if tol is not None:
            if not isinstance(tol, (int, float)) or isinstance(tol, bool):
                raise CaseProfileError(
                    f"CaseProfile {case_id!r} tolerance_policy[{obs_name!r}]."
                    f"tolerance must be a number; got {type(tol).__name__}"
                )
            if tol != tol:  # NaN guard (float('nan') != itself)
                raise CaseProfileError(
                    f"CaseProfile {case_id!r} tolerance_policy[{obs_name!r}]."
                    f"tolerance is NaN"
                )
        normalized[obs_name] = dict(entry)  # defensive copy

    return normalized
