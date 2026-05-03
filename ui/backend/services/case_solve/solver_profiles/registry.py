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
        "write_control", "write_interval", "write_interval_decimal",
        "purge_write",
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

    # solvers: required to be a mapping. Each value is either:
    #   - a scalar (str/int/float) → normalized to {body: <str>, name_pad: 2}
    #     (Phase 1 backward-compat, used by simpleFoam.yaml)
    #   - a dict with required `body: str` and optional `name_pad: int`
    #     (Phase 2 extension for byte-identity to V61-107.5 pimpleFoam
    #     pFinal/UFinal 1-space pad)
    raw_solvers = raw.get("solvers", {})
    if not isinstance(raw_solvers, dict):
        raise TypeError(
            f"fv_solution.solvers must be a mapping; got {type(raw_solvers).__name__}"
        )
    solvers: dict[str, dict[str, Any]] = {}
    for sk, sv in raw_solvers.items():
        if isinstance(sv, (str, int, float)) and not isinstance(sv, bool):
            # Phase 1 string-typed entry: normalize to {body, name_pad: 2}.
            solvers[str(sk)] = {"body": str(sv), "name_pad": 2}
        elif isinstance(sv, dict):
            # Phase 2 SolverEntry-typed: must contain `body: str`,
            # optionally `name_pad: int`. Reject extra unknown keys.
            allowed_keys = {"body", "name_pad"}
            extra = set(sv.keys()) - allowed_keys
            if extra:
                raise TypeError(
                    f"fv_solution.solvers[{sk!r}] has unknown keys "
                    f"{sorted(extra)}; allowed: {sorted(allowed_keys)}"
                )
            if "body" not in sv:
                raise KeyError(
                    f"fv_solution.solvers[{sk!r}] (dict-typed) must have "
                    f"a 'body' field"
                )
            body = sv["body"]
            if not isinstance(body, (str, int, float)) or isinstance(body, bool):
                raise TypeError(
                    f"fv_solution.solvers[{sk!r}].body must be a scalar "
                    f"(str/int/float); got {type(body).__name__}"
                )
            name_pad = sv.get("name_pad", 2)
            if not isinstance(name_pad, int) or isinstance(name_pad, bool):
                raise TypeError(
                    f"fv_solution.solvers[{sk!r}].name_pad must be int; "
                    f"got {type(name_pad).__name__}"
                )
            if name_pad < 0:
                raise ValueError(
                    f"fv_solution.solvers[{sk!r}].name_pad must be >= 0; "
                    f"got {name_pad}"
                )
            solvers[str(sk)] = {"body": str(body), "name_pad": name_pad}
        else:
            raise TypeError(
                f"fv_solution.solvers[{sk!r}] must be a scalar (str/int/float) "
                f"or a dict with body+name_pad; got {type(sv).__name__}"
            )

    # control_block_fields: required to be a mapping. Nested values may
    # be scalars (rendered as `key value;`) OR a dict (rendered as a
    # nested OpenFOAM sub-dict, e.g. `residualControl { p 1e-3; }`).
    # Codex V61-112 R1 P2-3: validate the shape eagerly so a malformed
    # YAML edit fails ProfileSchemaError at load time, not OpenFOAM
    # runtime.
    raw_fields = raw["control_block_fields"]
    if not isinstance(raw_fields, dict):
        raise TypeError(
            f"fv_solution.control_block_fields must be a mapping; "
            f"got {type(raw_fields).__name__}"
        )
    for fk, fv in raw_fields.items():
        if isinstance(fv, dict):
            # Nested sub-dict (e.g. residualControl). Each leaf must be
            # a scalar — list/None/nested-dict-of-dict are rejected.
            for nk, nv in fv.items():
                if not isinstance(nv, (str, int, float)) or isinstance(nv, bool):
                    raise TypeError(
                        f"fv_solution.control_block_fields[{fk!r}][{nk!r}] "
                        f"must be a non-bool scalar (str/int/float); "
                        f"got {type(nv).__name__}"
                    )
        elif not isinstance(fv, (str, int, float, bool)):
            raise TypeError(
                f"fv_solution.control_block_fields[{fk!r}] must be a scalar "
                f"(str/int/float/bool) or nested mapping; got {type(fv).__name__}"
            )

    # Codex V61-112 R2 P2: control_block_name MUST be a string. The
    # previous str(...) coercion accepted null/list/dict and silently
    # rendered invalid OpenFOAM block headers (e.g. "None
    # { ... }" or "['SIMPLE'] { ... }"). Reject at load time.
    cbn = raw["control_block_name"]
    if not isinstance(cbn, str):
        raise TypeError(
            f"fv_solution.control_block_name must be a string; "
            f"got {type(cbn).__name__}"
        )

    kwargs: dict[str, Any] = {
        "solvers": solvers,
        "control_block_name": cbn,
        "control_block_fields": raw_fields,
    }
    if "relaxation_factors_fields" in raw:
        rff = raw["relaxation_factors_fields"]
        if not isinstance(rff, dict):
            raise TypeError(
                f"fv_solution.relaxation_factors_fields must be a mapping; "
                f"got {type(rff).__name__}"
            )
        kwargs["relaxation_factors_fields"] = {
            str(k): float(v) for k, v in rff.items()
        }
    if "relaxation_factors_equations" in raw:
        rfe = raw["relaxation_factors_equations"]
        if not isinstance(rfe, dict):
            raise TypeError(
                f"fv_solution.relaxation_factors_equations must be a mapping; "
                f"got {type(rfe).__name__}"
            )
        kwargs["relaxation_factors_equations"] = {
            str(k): float(v) for k, v in rfe.items()
        }
    return FvSolutionBlock(**kwargs)
