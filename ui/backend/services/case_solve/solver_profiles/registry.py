"""DEC-V61-112 Phase 1 · Solver-profile YAML loader / registry.

Loads YAML profiles from
``ui/backend/services/case_solve/solver_profiles/profiles/*.yaml``
and validates them against :mod:`schema`. The registry caches
loaded profiles in-process; profiles are immutable post-load.

Public API:

* :func:`load_profile(name)` — returns ``SolverProfile`` or raises
* :func:`list_profile_names()` — list of available profile names
* :exc:`ProfileNotFoundError`
* :exc:`ProfileSchemaError`
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import (
    ControlDictBlock,
    FvSchemesBlock,
    FvSolutionBlock,
    SolverProfile,
)


class ProfileNotFoundError(ValueError):
    """The requested profile name has no YAML file in the profiles dir."""


class ProfileSchemaError(ValueError):
    """The YAML file exists but doesn't match the SolverProfile schema."""


_PROFILES_DIR = Path(__file__).parent / "profiles"

# In-process cache. Profiles are immutable post-load so this is safe
# across all concurrent requests.
_CACHE: dict[str, SolverProfile] = {}


def list_profile_names() -> list[str]:
    """Return sorted list of profile names available on disk."""
    if not _PROFILES_DIR.is_dir():
        return []
    return sorted(p.stem for p in _PROFILES_DIR.glob("*.yaml"))


def load_profile(name: str) -> SolverProfile:
    """Load and return the profile for ``name``.

    Raises :exc:`ProfileNotFoundError` if no ``<name>.yaml`` exists
    under the profiles dir. Raises :exc:`ProfileSchemaError` if the
    YAML doesn't validate against the schema (missing required
    field, wrong type for a typed attribute, etc.).
    """
    if name in _CACHE:
        return _CACHE[name]

    yaml_path = _PROFILES_DIR / f"{name}.yaml"
    if not yaml_path.is_file():
        raise ProfileNotFoundError(
            f"no profile named {name!r} under {_PROFILES_DIR}; "
            f"available: {list_profile_names()}"
        )

    try:
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProfileSchemaError(
            f"profile {name!r} YAML parse failed: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ProfileSchemaError(
            f"profile {name!r} top-level must be a mapping; got {type(raw).__name__}"
        )

    try:
        profile = _build_profile(name, raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise ProfileSchemaError(
            f"profile {name!r} schema mismatch: {exc}"
        ) from exc

    _CACHE[name] = profile
    return profile


def _build_profile(name: str, raw: dict[str, Any]) -> SolverProfile:
    """Construct a SolverProfile from a parsed YAML dict.

    Raises ValueError / KeyError / TypeError on schema mismatch;
    the caller wraps these into ProfileSchemaError.
    """
    _require_keys(raw, {"name", "family", "control_dict", "fv_schemes", "fv_solution"}, "top-level")
    if raw["name"] != name:
        raise ValueError(
            f"profile name field {raw['name']!r} != filename {name!r}"
        )
    family = raw["family"]
    if family not in ("steady", "transient"):
        raise ValueError(
            f"family must be 'steady' or 'transient', got {family!r}"
        )

    cd = _build_control_dict(raw["control_dict"])
    fs = _build_fv_schemes(raw["fv_schemes"])
    fv = _build_fv_solution(raw["fv_solution"])

    return SolverProfile(
        name=name,
        family=family,
        control_dict=cd,
        fv_schemes=fs,
        fv_solution=fv,
    )


def _require_keys(d: dict[str, Any], required: set[str], context: str) -> None:
    missing = required - set(d.keys())
    if missing:
        raise KeyError(f"{context}: missing required keys: {sorted(missing)}")


def _build_control_dict(raw: dict[str, Any]) -> ControlDictBlock:
    _require_keys(raw, {"application"}, "control_dict")
    # All other fields have schema defaults; pass them only if
    # present in YAML.
    kwargs: dict[str, Any] = {"application": raw["application"]}
    for key in (
        "start_from", "start_time", "stop_at",
        "end_time_default", "delta_t_default",
        "write_control", "write_interval", "purge_write",
        "write_format", "write_precision", "write_compression",
        "time_format", "time_precision", "run_time_modifiable",
        "adjust_time_step", "max_co", "max_delta_t_follows_delta_t",
        "iteration_floor",
    ):
        if key in raw:
            kwargs[key] = raw[key]
    return ControlDictBlock(**kwargs)


def _build_fv_schemes(raw: dict[str, Any]) -> FvSchemesBlock:
    kwargs: dict[str, Any] = {}
    for key in (
        "ddt_schemes", "grad_schemes", "div_schemes",
        "laplacian_schemes", "interpolation_schemes", "sn_grad_schemes",
    ):
        if key in raw:
            value = raw[key]
            if not isinstance(value, dict):
                raise TypeError(
                    f"fv_schemes.{key} must be a mapping; got {type(value).__name__}"
                )
            # Coerce all values to str; YAML may parse numerics.
            kwargs[key] = {str(k): str(v) for k, v in value.items()}
    return FvSchemesBlock(**kwargs)


def _build_fv_solution(raw: dict[str, Any]) -> FvSolutionBlock:
    _require_keys(raw, {"control_block_name", "control_block_fields"}, "fv_solution")
    kwargs: dict[str, Any] = {
        "solvers": {str(k): str(v) for k, v in raw.get("solvers", {}).items()},
        "control_block_name": raw["control_block_name"],
        "control_block_fields": raw["control_block_fields"],
    }
    if "relaxation_factors_fields" in raw:
        kwargs["relaxation_factors_fields"] = {
            str(k): float(v) for k, v in raw["relaxation_factors_fields"].items()
        }
    if "relaxation_factors_equations" in raw:
        kwargs["relaxation_factors_equations"] = {
            str(k): float(v) for k, v in raw["relaxation_factors_equations"].items()
        }
    return FvSolutionBlock(**kwargs)
