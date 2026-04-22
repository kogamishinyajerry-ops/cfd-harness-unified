"""DEC-V61-038: Pre-extraction convergence attestor A1..A6.

Complements DEC-V61-036b (post-extraction gates G3/G4/G5). Where G3/G4/G5
say "the extracted measurement cannot be trusted because the final-state
fields are broken", A1..A6 say "the run itself never physically converged
even if the solver exited 0".

Composition with gates:
    solver exit 0
    → attestor.attest(log)    → ATTEST_PASS / HAZARD / FAIL
    → if ATTEST_FAIL: contract FAIL (before extraction)
    → else: comparator_gates.check_all_gates(log, vtk)
    → if any gate: contract FAIL
    → else: comparator verdict

Checks:
    A1 solver_exit_clean       — no FOAM FATAL / floating exception  → FAIL
    A2 continuity_floor        — final sum_local ≤ case floor        → HAZARD
    A3 residual_floor          — final initial residuals ≤ target    → HAZARD
    A4 solver_iteration_cap    — pressure loop hit cap repeatedly    → FAIL
    A5 bounding_recurrence     — turbulence bounding in last N iters → HAZARD
    A6 no_residual_progress    — residuals stuck at plateau          → HAZARD

A1/A4 are hard FAIL (solver crashes / caps never acceptable).
A2/A3/A5/A6 default HAZARD; per-case thresholds can promote to FAIL
via knowledge/attestor_thresholds.yaml.

The attestor returns ATTEST_FAIL if ANY check FAILs; ATTEST_HAZARD if
only HAZARD-tier checks fire; else ATTEST_PASS.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

import yaml

from src.comparator_gates import parse_solver_log

# ---------------------------------------------------------------------------
# Thresholds (kept as module constants for backward compatibility; YAML-backed
# Thresholds resolution overlays these defaults when the registry is present)
# ---------------------------------------------------------------------------

A2_CONTINUITY_FLOOR = 1.0e-4           # incompressible steady; G5 fires at 1e-2
A3_RESIDUAL_FLOOR = 1.0e-3             # initial residual of any field
# Codex DEC-038 round-1 BLOCKER 1: A4 regex must cover every pressure
# solver + every pressure field name seen in the real audit logs.
# - Solver types: GAMG, PCG, DICPCG, PBiCG, DILUPBiCGStab
# - Pressure field names: p (incompressible), p_rgh (buoyant), pd
# - Multi-corrector PIMPLE loops emit multiple pressure solves per Time=
#   block; A4 must track BLOCKS not LINES (BLOCKER 2) so consecutive-hit
#   semantics match the DEC's "3 consecutive time steps" intent.
A4_PRESSURE_FIELD_RE = re.compile(
    # Codex DEC-038 round-2 nit: PBiCGStab:... would not match PBiCG
    # alternative because the next char after the 5-letter prefix is 'S'
    # not ':'. List PBiCGStab before PBiCG so regex alternation picks the
    # longer literal first.
    r"(?:GAMG|DICPCG|PCG|PBiCGStab|PBiCG|DILUPBiCGStab|smoothSolver)\s*:\s*"
    r"Solving for\s+(p(?:_rgh|d)?)\s*,"
    r".+?No Iterations\s+(\d+)"
)
A4_ITERATION_CAP_VALUES = (1000, 999, 998)  # solver-reported caps
A4_CONSECUTIVE = 3                     # how many consecutive time-step blocks = FAIL

A5_BOUNDING_WINDOW = 50                # last N iterations to inspect
A5_BOUNDING_RECURRENCE_FRAC = 0.30     # ≥ 30% of window bounded = HAZARD

A6_PROGRESS_WINDOW = 50
A6_PROGRESS_DECADE_FRAC = 1.0          # need > 1 decade decay over window

LOGGER = logging.getLogger(__name__)

_DEFAULT_THRESHOLDS_PATH = (
    Path(__file__).resolve().parent.parent / "knowledge" / "attestor_thresholds.yaml"
)
_KNOWN_A3_FIELDS = (
    "Ux",
    "Uy",
    "Uz",
    "p",
    "p_rgh",
    "k",
    "epsilon",
    "omega",
    "h",
    "nuTilda",
    "T",
)
_THRESHOLD_TOP_LEVEL_KEYS = frozenset({"schema_version", "defaults", "per_case"})


AttestVerdict = Literal[
    "ATTEST_PASS",
    "ATTEST_HAZARD",
    "ATTEST_FAIL",
    "ATTEST_NOT_APPLICABLE",  # no log available (reference/visual_only tiers)
]
CheckVerdict = Literal["PASS", "HAZARD", "FAIL"]


@dataclass(frozen=True)
class Thresholds:
    continuity_floor: float
    residual_floor: float
    residual_floor_per_field: dict[str, float]
    iteration_cap_detector_count: int
    bounding_recurrence_frac_threshold: float
    bounding_recurrence_window: int
    no_progress_decade_frac: float
    no_progress_window: int
    promote_to_fail: frozenset[str] = field(default_factory=frozenset)
    case_id: Optional[str] = None


@dataclass
class AttestorCheck:
    """Single check outcome (A1..A6)."""

    check_id: str              # "A1" .. "A6"
    concern_type: str          # "SOLVER_CRASH_LOG" / "CONTINUITY_NOT_CONVERGED" / ...
    verdict: CheckVerdict
    summary: str
    detail: str
    evidence: dict = field(default_factory=dict)


@dataclass
class AttestationResult:
    """Aggregate attestation: overall verdict + per-check breakdown.

    `concerns` is the subset of checks whose verdict is HAZARD or FAIL
    (PASS checks are not surfaced in the fixture to avoid clutter).
    """

    overall: AttestVerdict
    checks: list[AttestorCheck] = field(default_factory=list)

    @property
    def concerns(self) -> list[AttestorCheck]:
        return [c for c in self.checks if c.verdict != "PASS"]


_DEFAULT_THRESHOLDS = Thresholds(
    continuity_floor=A2_CONTINUITY_FLOOR,
    residual_floor=A3_RESIDUAL_FLOOR,
    residual_floor_per_field={field_name: A3_RESIDUAL_FLOOR for field_name in _KNOWN_A3_FIELDS},
    iteration_cap_detector_count=A4_CONSECUTIVE,
    bounding_recurrence_frac_threshold=A5_BOUNDING_RECURRENCE_FRAC,
    bounding_recurrence_window=A5_BOUNDING_WINDOW,
    no_progress_decade_frac=A6_PROGRESS_DECADE_FRAC,
    no_progress_window=A6_PROGRESS_WINDOW,
)


def _thresholds_to_mutable_dict(base: Thresholds) -> dict[str, Any]:
    return {
        "continuity_floor": base.continuity_floor,
        "residual_floor": base.residual_floor,
        "residual_floor_per_field": dict(base.residual_floor_per_field),
        "iteration_cap_detector_count": base.iteration_cap_detector_count,
        "bounding_recurrence_frac_threshold": base.bounding_recurrence_frac_threshold,
        "bounding_recurrence_window": base.bounding_recurrence_window,
        "no_progress_decade_frac": base.no_progress_decade_frac,
        "no_progress_window": base.no_progress_window,
        "promote_to_fail": frozenset(base.promote_to_fail),
    }


def _build_thresholds(payload: dict[str, Any], case_id: Optional[str]) -> Thresholds:
    return Thresholds(
        continuity_floor=float(payload["continuity_floor"]),
        residual_floor=float(payload["residual_floor"]),
        residual_floor_per_field=dict(payload["residual_floor_per_field"]),
        iteration_cap_detector_count=int(payload["iteration_cap_detector_count"]),
        bounding_recurrence_frac_threshold=float(
            payload["bounding_recurrence_frac_threshold"]
        ),
        bounding_recurrence_window=int(payload["bounding_recurrence_window"]),
        no_progress_decade_frac=float(payload["no_progress_decade_frac"]),
        no_progress_window=int(payload["no_progress_window"]),
        promote_to_fail=frozenset(payload["promote_to_fail"]),
        case_id=case_id,
    )


def _fallback_thresholds(case_id: Optional[str]) -> Thresholds:
    return _build_thresholds(_thresholds_to_mutable_dict(_DEFAULT_THRESHOLDS), case_id)


def _coerce_float(
    value: Any,
    *,
    fallback: float,
    path: Path,
    key_path: str,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        LOGGER.warning(
            "attestor thresholds: invalid numeric value for %s in %s: %r; using %.6g",
            key_path,
            path,
            value,
            fallback,
        )
        return fallback


def _coerce_int(
    value: Any,
    *,
    fallback: int,
    path: Path,
    key_path: str,
) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        LOGGER.warning(
            "attestor thresholds: invalid integer value for %s in %s: %r; using %d",
            key_path,
            path,
            value,
            fallback,
        )
        return fallback


def _apply_threshold_overrides(
    resolved: dict[str, Any],
    overrides: Any,
    *,
    path: Path,
    label: str,
) -> None:
    if overrides is None:
        return
    if not isinstance(overrides, dict):
        LOGGER.warning(
            "attestor thresholds: %s in %s is not a mapping; ignoring override",
            label,
            path,
        )
        return

    if "continuity_floor" in overrides:
        resolved["continuity_floor"] = _coerce_float(
            overrides["continuity_floor"],
            fallback=float(resolved["continuity_floor"]),
            path=path,
            key_path=f"{label}.continuity_floor",
        )
    if "residual_floor" in overrides:
        resolved["residual_floor"] = _coerce_float(
            overrides["residual_floor"],
            fallback=float(resolved["residual_floor"]),
            path=path,
            key_path=f"{label}.residual_floor",
        )
    if "residual_floor_per_field" in overrides:
        field_overrides = overrides["residual_floor_per_field"]
        if isinstance(field_overrides, dict):
            merged = dict(resolved["residual_floor_per_field"])
            # Merge semantics are intentional: case-specific overrides should
            # only replace the mentioned fields and preserve YAML defaults for
            # everything else.
            for field_name, raw_value in field_overrides.items():
                merged[str(field_name)] = _coerce_float(
                    raw_value,
                    fallback=float(merged.get(str(field_name), resolved["residual_floor"])),
                    path=path,
                    key_path=f"{label}.residual_floor_per_field.{field_name}",
                )
            resolved["residual_floor_per_field"] = merged
        else:
            LOGGER.warning(
                "attestor thresholds: %s.residual_floor_per_field in %s is not a mapping; ignoring override",
                label,
                path,
            )
    if "iteration_cap_detector_count" in overrides:
        resolved["iteration_cap_detector_count"] = _coerce_int(
            overrides["iteration_cap_detector_count"],
            fallback=int(resolved["iteration_cap_detector_count"]),
            path=path,
            key_path=f"{label}.iteration_cap_detector_count",
        )
    if "bounding_recurrence_frac_threshold" in overrides:
        resolved["bounding_recurrence_frac_threshold"] = _coerce_float(
            overrides["bounding_recurrence_frac_threshold"],
            fallback=float(resolved["bounding_recurrence_frac_threshold"]),
            path=path,
            key_path=f"{label}.bounding_recurrence_frac_threshold",
        )
    if "bounding_recurrence_window" in overrides:
        resolved["bounding_recurrence_window"] = _coerce_int(
            overrides["bounding_recurrence_window"],
            fallback=int(resolved["bounding_recurrence_window"]),
            path=path,
            key_path=f"{label}.bounding_recurrence_window",
        )
    if "no_progress_decade_frac" in overrides:
        resolved["no_progress_decade_frac"] = _coerce_float(
            overrides["no_progress_decade_frac"],
            fallback=float(resolved["no_progress_decade_frac"]),
            path=path,
            key_path=f"{label}.no_progress_decade_frac",
        )
    if "no_progress_window" in overrides:
        resolved["no_progress_window"] = _coerce_int(
            overrides["no_progress_window"],
            fallback=int(resolved["no_progress_window"]),
            path=path,
            key_path=f"{label}.no_progress_window",
        )
    if "promote_to_fail" in overrides:
        raw_promote = overrides["promote_to_fail"]
        if isinstance(raw_promote, (list, tuple, set, frozenset)):
            resolved["promote_to_fail"] = frozenset(str(item) for item in raw_promote)
        else:
            LOGGER.warning(
                "attestor thresholds: %s.promote_to_fail in %s is not a list-like value; ignoring override",
                label,
                path,
            )


@lru_cache(maxsize=32)
def _load_thresholds_cached(
    case_id: Optional[str],
    yaml_path_str: Optional[str],
) -> Thresholds:
    yaml_path = Path(yaml_path_str) if yaml_path_str is not None else _DEFAULT_THRESHOLDS_PATH
    if not yaml_path.is_file():
        LOGGER.warning(
            "attestor thresholds: YAML not found at %s; using hardcoded defaults",
            yaml_path,
        )
        return _fallback_thresholds(case_id)

    try:
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        LOGGER.warning(
            "attestor thresholds: failed to read %s (%s); using hardcoded defaults",
            yaml_path,
            exc,
        )
        return _fallback_thresholds(case_id)
    except yaml.YAMLError as exc:
        LOGGER.warning(
            "attestor thresholds: failed to parse %s (%s); using hardcoded defaults",
            yaml_path,
            exc,
        )
        return _fallback_thresholds(case_id)

    if not isinstance(raw, dict):
        LOGGER.warning(
            "attestor thresholds: root of %s is not a mapping; using hardcoded defaults",
            yaml_path,
        )
        return _fallback_thresholds(case_id)

    unknown_top_level = sorted(set(raw) - _THRESHOLD_TOP_LEVEL_KEYS)
    if unknown_top_level:
        LOGGER.warning(
            "attestor thresholds: unknown top-level keys in %s: %s",
            yaml_path,
            ", ".join(unknown_top_level),
        )

    if raw.get("schema_version") != 1:
        LOGGER.warning(
            "attestor thresholds: expected schema_version=1 in %s, got %r; continuing best-effort",
            yaml_path,
            raw.get("schema_version"),
        )

    resolved = _thresholds_to_mutable_dict(_DEFAULT_THRESHOLDS)
    _apply_threshold_overrides(
        resolved,
        raw.get("defaults"),
        path=yaml_path,
        label="defaults",
    )

    if case_id:
        per_case = raw.get("per_case")
        if isinstance(per_case, dict):
            _apply_threshold_overrides(
                resolved,
                per_case.get(case_id),
                path=yaml_path,
                label=f"per_case.{case_id}",
            )
        elif per_case is not None:
            LOGGER.warning(
                "attestor thresholds: per_case in %s is not a mapping; ignoring case overrides",
                yaml_path,
            )

    return _build_thresholds(resolved, case_id)


def load_thresholds(
    case_id: Optional[str] = None,
    yaml_path: Optional[Path] = None,
) -> Thresholds:
    """Load YAML-backed convergence thresholds with graceful fallback."""
    normalized_path = (
        str(Path(yaml_path).expanduser().resolve()) if yaml_path is not None else None
    )
    return _load_thresholds_cached(case_id, normalized_path)


# ---------------------------------------------------------------------------
# Per-check regexes (reuse parse_solver_log output where possible)
# ---------------------------------------------------------------------------

_INITIAL_RESIDUAL_RE = re.compile(
    r"Solving for\s+(\w+),\s*Initial residual\s*=\s*([\deE+.\-]+),"
    r"\s*Final residual\s*=\s*([\deE+.\-]+),\s*No Iterations\s+(\d+)"
)

_BOUNDING_LINE_RE = re.compile(r"^\s*bounding\s+(k|epsilon|omega|nuTilda|nut)\b")
# OpenFOAM writes `Time = 123` on its own line AND as `Time = 123s` with
# trailing `s`. Accept either form; trailing whitespace tolerated.
_TIME_STEP_RE = re.compile(r"^Time\s*=\s*[\deE+.\-]+s?\s*$")
_A1_FATAL_MARKER_RE = re.compile(
    r"FOAM FATAL IO ERROR|FOAM FATAL ERROR|^Floating point exception\b|Floating exception\b"
)


def _parse_residual_timeline(log_path: Path) -> dict[str, list[float]]:
    """Extract per-field Initial residual history across all iterations.

    Returns {"Ux": [...], "Uy": [...], "p": [...], "k": [...], "epsilon": [...]}.
    Order preserves the log's iteration order. Used by A3.
    """
    timeline: dict[str, list[float]] = {}
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = _INITIAL_RESIDUAL_RE.search(line)
            if not m:
                continue
            field_name = m.group(1)
            try:
                r0 = float(m.group(2))
            except ValueError:
                continue
            timeline.setdefault(field_name, []).append(r0)
    return timeline


def _parse_outer_iteration_residuals(log_path: Path) -> dict[str, list[float]]:
    """Extract per-field residuals from the first solve seen in each Time block.

    A6 should reason about outer-iteration progress, not every inner corrector
    solve. For each ``Time = ...`` block, only the first
    ``Solving for <field>, Initial residual = ...`` line per field is kept.
    Subsequent solves of the same field inside that block are treated as
    inner-loop corrections and ignored for the A6 plateau detector.
    """
    return {
        field_name: [residual for residual, _ in samples]
        for field_name, samples in _parse_outer_iteration_samples(log_path).items()
    }


def _parse_outer_iteration_samples(log_path: Path) -> dict[str, list[tuple[float, int]]]:
    """Extract ``(initial_residual, iterations)`` for the first solve per field.

    A6 uses the same outer-iteration grouping as `_parse_outer_iteration_residuals`,
    but keeps the solver's reported iteration count so it can ignore
    non-informative single-iteration algebraic updates and pressure fields that
    are already covered by A4's iteration-cap detector.
    """
    timeline: dict[str, list[tuple[float, int]]] = {}
    seen_fields_in_block: set[str] = set()
    in_time_block = False
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if _TIME_STEP_RE.match(line):
                seen_fields_in_block.clear()
                in_time_block = True
                continue
            if not in_time_block:
                continue
            m = _INITIAL_RESIDUAL_RE.search(line)
            if not m:
                continue
            field_name = m.group(1)
            if field_name in seen_fields_in_block:
                continue
            try:
                r0 = float(m.group(2))
                iterations = int(m.group(4))
            except ValueError:
                continue
            timeline.setdefault(field_name, []).append((r0, iterations))
            seen_fields_in_block.add(field_name)
    return timeline


def _parse_iteration_caps_per_block(log_path: Path) -> list[int]:
    """Return per-`Time = ...` block the MAX pressure-solver iteration count
    seen inside that block.

    Codex DEC-038 round-1 BLOCKER 2: A4 must count consecutive TIME STEPS
    (outer iterations), not consecutive solve lines — PIMPLE multi-corrector
    loops emit ≥2 pressure solves per block and the prior line-based count
    would false-fire after 1.5 blocks. Returns one entry per block; a
    block's count is the worst (max) pressure iteration count seen in it.
    Blocks with no pressure solve get 0 so A4 can explicitly reset the
    consecutiveness streak on gaps.
    """
    per_block_max: list[int] = []
    current_max = 0
    seen_any = False
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if _TIME_STEP_RE.match(line):
                if seen_any:
                    per_block_max.append(current_max)
                current_max = 0
                seen_any = True
                continue
            m = A4_PRESSURE_FIELD_RE.search(line)
            if m:
                try:
                    count = int(m.group(2))
                except ValueError:
                    continue
                if count > current_max:
                    current_max = count
        if seen_any:
            per_block_max.append(current_max)
    return per_block_max


def _parse_bounding_lines_per_step(log_path: Path) -> list[set[str]]:
    """Return list of sets, one per `Time =` block, containing fields that
    bounded in that block. Used by A5.
    """
    blocks: list[set[str]] = [set()]
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if _TIME_STEP_RE.match(line):
                blocks.append(set())
                continue
            m = _BOUNDING_LINE_RE.match(line)
            if m:
                blocks[-1].add(m.group(1))
    # Drop leading empty block before first `Time =`.
    if blocks and not blocks[0]:
        blocks.pop(0)
    return blocks


def _scan_a1_fatal_lines(log_path: Path) -> list[str]:
    if not log_path.is_file():
        return []

    fatal_lines: list[str] = []
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            normalized = line.strip()
            if not normalized:
                continue
            lower = normalized.lower()
            if "floating point exception trapping" in lower:
                continue
            if _A1_FATAL_MARKER_RE.search(normalized):
                fatal_lines.append(normalized[:240])
                if len(fatal_lines) >= 5:
                    break
    return fatal_lines


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_a1_solver_crash(log_path: Path, execution_result: Any = None) -> AttestorCheck:
    stats = parse_solver_log(log_path)
    fatal_lines: list[str] = []
    for line in stats.fatal_lines + _scan_a1_fatal_lines(log_path):
        if line and line not in fatal_lines:
            fatal_lines.append(line)
    exec_failed = getattr(execution_result, "success", None) is False
    exit_code = getattr(execution_result, "exit_code", None) if execution_result is not None else None

    if exec_failed or fatal_lines or stats.fatal_detected:
        evidence: dict[str, Any] = {"fatal_lines": fatal_lines[:3]}
        summary_parts: list[str] = []
        detail_parts: list[str] = []
        if exec_failed:
            evidence["execution_success"] = False
            evidence["exit_code"] = exit_code
            summary_parts.append(
                "execution_result.success=False"
                if exit_code is None
                else f"execution_result.success=False (exit_code={exit_code})"
            )
            detail_parts.append(
                "execution_result reported solver failure"
                if exit_code is None
                else f"execution_result reported solver failure with exit_code={exit_code}"
            )
        if fatal_lines or stats.fatal_detected:
            summary_parts.append(
                fatal_lines[0][:120] if fatal_lines else "fatal marker found in solver log"
            )
            detail_parts.append(
                "solver log contains a FOAM FATAL / floating exception marker"
            )
        return AttestorCheck(
            check_id="A1",
            concern_type="SOLVER_CRASH_LOG",
            verdict="FAIL",
            summary="; ".join(summary_parts)[:240],
            detail=(
                "DEC-V61-038 A1: "
                + "; ".join(detail_parts)
                + ". A1 fails if either the execution_result reports a non-zero-style "
                "failure or the log itself contains fatal markers, because either signal "
                "means the run cannot be trusted."
            )[:2000],
            evidence=evidence,
        )
    return AttestorCheck(
        check_id="A1",
        concern_type="SOLVER_CRASH_LOG",
        verdict="PASS",
        summary="no execution-result failure or fatal marker in log",
        detail="",
    )


def _check_a2_continuity_floor(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    stats = parse_solver_log(log_path)
    sl = stats.final_continuity_sum_local
    if sl is None:
        return AttestorCheck(
            check_id="A2", concern_type="CONTINUITY_NOT_CONVERGED", verdict="PASS",
            summary="no continuity line in log (case may not report it)",
            detail="",
        )
    if sl > thresholds.continuity_floor:
        # Codex DEC-038 round-1 A2/G5 split-brain comment: A2 stays strictly
        # HAZARD here to avoid conflict with G5, which hard-FAILs
        # `sum_local > 1e-2` on the gate side. Keeping A2 as HAZARD means
        # the attestor tier is purely diagnostic; the FAIL call belongs to
        # the gate layer. Previously A2 returned FAIL for >1e-2, but the
        # verdict engine did not hard-FAIL on CONTINUITY_NOT_CONVERGED, so
        # the semantics split across layers. Now A2 is always HAZARD-tier.
        verdict: CheckVerdict = "HAZARD"
        return AttestorCheck(
            check_id="A2",
            concern_type="CONTINUITY_NOT_CONVERGED",
            verdict=verdict,
            summary=(f"final sum_local={sl:.3g} > floor {thresholds.continuity_floor:.0e}")[:240],
            detail=(
                f"DEC-V61-038 A2: incompressible steady continuity error at "
                f"convergence should be ≤ {thresholds.continuity_floor:.0e}. Observed "
                f"final sum_local={sl:.6g}. Values between {thresholds.continuity_floor:.0e} "
                f"and 1e-2 are HAZARD (marginal convergence); >1e-2 is FAIL "
                "(DEC-036b G5 also fires)."
            )[:2000],
            evidence={"sum_local": sl, "threshold": thresholds.continuity_floor},
        )
    return AttestorCheck(
        check_id="A2", concern_type="CONTINUITY_NOT_CONVERGED", verdict="PASS",
        summary=f"final sum_local={sl:.3g} ≤ {thresholds.continuity_floor:.0e}",
        detail="",
    )


def _check_a3_residual_floor(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    timeline = _parse_residual_timeline(log_path)
    if not timeline:
        return AttestorCheck(
            check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET", verdict="PASS",
            summary="no residual lines parsed from log",
            detail="",
        )
    offenders: dict[str, float] = {}
    offender_thresholds: dict[str, float] = {}
    for field_name, history in timeline.items():
        last = history[-1]
        threshold = thresholds.residual_floor_per_field.get(
            field_name,
            thresholds.residual_floor,
        )
        if last > threshold:
            offenders[field_name] = last
            offender_thresholds[field_name] = threshold
    if offenders:
        sorted_off = sorted(offenders.items(), key=lambda kv: -kv[1])
        summary = (
            "final residuals above field targets: "
            + ", ".join(
                f"{field_name}={value:.3g}>{offender_thresholds[field_name]:.3g}"
                for field_name, value in sorted_off[:3]
            )
        )[:240]
        return AttestorCheck(
            check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET",
            verdict="HAZARD",
            summary=summary,
            detail=(
                "DEC-V61-038 A3: at convergence, SIMPLE/PISO initial residuals "
                "should be ≤ each field's configured threshold. Fields listed "
                "above have final-iteration Initial residuals exceeding their "
                "per-field targets. This "
                "may be physically expected for some cases (impinging_jet "
                "p_rgh, RBC oscillatory modes) — HAZARD not FAIL until a "
                "per-case override promotes it."
            )[:2000],
            evidence={
                "offenders": offenders,
                "thresholds_by_field": offender_thresholds,
                "default_threshold": thresholds.residual_floor,
            },
        )
    return AttestorCheck(
        check_id="A3", concern_type="RESIDUALS_ABOVE_TARGET", verdict="PASS",
        summary="all residuals ≤ their configured field thresholds",
        detail="",
    )


def _check_a4_iteration_cap(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    per_block = _parse_iteration_caps_per_block(log_path)
    if not per_block:
        return AttestorCheck(
            check_id="A4", concern_type="SOLVER_ITERATION_CAP", verdict="PASS",
            summary="no pressure solver iteration counts in log",
            detail="",
        )
    consecutive = 0
    max_consecutive = 0
    cap_hits = 0
    max_iterations = 0
    for b_max in per_block:
        if b_max > max_iterations:
            max_iterations = b_max
        if b_max in A4_ITERATION_CAP_VALUES or b_max >= 1000:
            consecutive += 1
            cap_hits += 1
            if consecutive > max_consecutive:
                max_consecutive = consecutive
            if consecutive >= thresholds.iteration_cap_detector_count:
                return AttestorCheck(
                    check_id="A4", concern_type="SOLVER_ITERATION_CAP",
                    verdict="FAIL",
                    summary=(
                        f"pressure solver hit {b_max} iterations in "
                        f"≥ {thresholds.iteration_cap_detector_count} consecutive time-step blocks"
                    )[:240],
                    detail=(
                        "DEC-V61-038 A4: pressure-velocity solver loop is "
                        f"hitting its iteration cap (~{b_max}) in at least "
                        f"{thresholds.iteration_cap_detector_count} consecutive time-step blocks "
                        "(Time = ... dividers). SIMPLE/PISO/PIMPLE coupling "
                        "has effectively failed — the solver is burning CPU "
                        "without reducing the residual. Hard FAIL."
                    )[:2000],
                    evidence={
                        "consecutive_cap_blocks": consecutive,
                        "max_consecutive_cap_blocks": max_consecutive,
                        "final_cap_value": b_max,
                        "total_blocks": len(per_block),
                    },
                )
        else:
            consecutive = 0
    return AttestorCheck(
        check_id="A4", concern_type="SOLVER_ITERATION_CAP", verdict="PASS",
        summary=(
            f"pressure solver peaked at {max_iterations} iterations; "
            f"max consecutive cap streak={max_consecutive}"
            if cap_hits
            else f"no capped pressure-solver blocks across {len(per_block)} time steps"
        )[:240],
        detail="",
    )


def _check_a5_bounding_recurrence(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    blocks = _parse_bounding_lines_per_step(log_path)
    if len(blocks) < 5:
        # Too few time steps to judge recurrence.
        return AttestorCheck(
            check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
            summary=f"only {len(blocks)} time-step blocks parsed",
            detail="",
        )
    window = blocks[-thresholds.bounding_recurrence_window:]
    if not window:
        return AttestorCheck(
            check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
            summary="no final-window blocks",
            detail="",
        )
    per_field_frac: dict[str, float] = {}
    for field_name in ("k", "epsilon", "omega", "nuTilda", "nut"):
        bounded_count = sum(1 for b in window if field_name in b)
        if bounded_count == 0:
            continue
        frac = bounded_count / len(window)
        per_field_frac[field_name] = frac
    offenders = {k: v for k, v in per_field_frac.items()
                 if v >= thresholds.bounding_recurrence_frac_threshold}
    if offenders:
        top = max(offenders.items(), key=lambda kv: kv[1])
        return AttestorCheck(
            check_id="A5", concern_type="BOUNDING_RECURRENT",
            verdict="HAZARD",
            summary=(
                f"{top[0]} bounded in {top[1]*100:.0f}% of last "
                f"{len(window)} iterations (threshold "
                f"{thresholds.bounding_recurrence_frac_threshold*100:.0f}%)"
            )[:240],
            detail=(
                "DEC-V61-038 A5: turbulence field is being clipped in a large "
                f"fraction of the FINAL {len(window)} iterations. Healthy "
                "convergence shows bounding events in early transients then "
                "stabilises. Recurrent bounding in the tail indicates the "
                "solution never settles — 'converged' residuals are an artefact "
                "of clipping, not physical equilibrium."
            )[:2000],
            evidence={"per_field_fraction": per_field_frac, "window": len(window)},
        )
    return AttestorCheck(
        check_id="A5", concern_type="BOUNDING_RECURRENT", verdict="PASS",
        summary=(
            f"bounding fractions in last {len(window)} iters: "
            + ", ".join(f"{k}={v:.0%}" for k, v in per_field_frac.items())
            if per_field_frac else f"no bounding in last {len(window)} iters"
        )[:240],
        detail="",
    )


def _check_a6_no_progress(log_path: Path, thresholds: Thresholds) -> AttestorCheck:
    sample_timeline = _parse_outer_iteration_samples(log_path)
    timeline = _parse_outer_iteration_residuals(log_path)
    if not timeline:
        return AttestorCheck(
            check_id="A6", concern_type="NO_RESIDUAL_PROGRESS", verdict="PASS",
            summary="no outer-iteration residuals parsed",
            detail="",
        )
    offenders: dict[str, dict[str, float]] = {}
    for field_name, history in timeline.items():
        sample_window = sample_timeline.get(field_name, [])[-thresholds.no_progress_window:]
        if len(sample_window) < 2:
            continue
        iterations_window = [iterations for _, iterations in sample_window]
        if all(iterations <= 1 for iterations in iterations_window):
            continue
        if field_name in {"p", "p_rgh", "pd"} and all(
            iterations in A4_ITERATION_CAP_VALUES for iterations in iterations_window
        ):
            continue
        window = history[-thresholds.no_progress_window:]
        lo = min(window)
        hi = max(window)
        if lo <= 0 or hi <= 0:
            continue
        # A6 only fires when residuals are STUCK AT A HIGH PLATEAU — i.e.,
        # still above the A3 floor. If residuals have already decayed to
        # convergence (< 1e-3), a small decade-range in the tail is just
        # machine-noise fluctuation, not "stuck". Guard against this
        # false positive (caught on LDC: Ux plateaued at 1e-5 with 0.02
        # decades range — that's converged, not stuck).
        threshold = thresholds.residual_floor_per_field.get(
            field_name,
            thresholds.residual_floor,
        )
        if hi < threshold:
            continue
        decades = math_log10(hi / lo) if hi > lo else 0.0
        if decades <= thresholds.no_progress_decade_frac:
            offenders[field_name] = {
                "decades": decades,
                "lo": lo,
                "hi": hi,
                "threshold": threshold,
                "window": len(window),
            }
    if offenders:
        worst = min(offenders.items(), key=lambda kv: kv[1]["decades"])
        return AttestorCheck(
            check_id="A6", concern_type="NO_RESIDUAL_PROGRESS",
            verdict="HAZARD",
            summary=(
                f"{worst[0]} residual range over last "
                f"{worst[1]['window']} outer iterations: "
                f"{worst[1]['lo']:.2e} – {worst[1]['hi']:.2e} "
                f"({worst[1]['decades']:.2f} decades)"
            )[:240],
            detail=(
                "DEC-V61-038 A6: first-solve residuals for the fields listed "
                f"above did not decay > {thresholds.no_progress_decade_frac:.1f} decade(s) "
                "over the recent outer-iteration window. Solver is "
                "stuck at a plateau; any scalar extracted from this 'converged' "
                "state is physically ambiguous."
            )[:2000],
            evidence={
                "offenders": offenders,
                "window": worst[1]["window"],
                "requested_window": thresholds.no_progress_window,
            },
        )
    return AttestorCheck(
        check_id="A6", concern_type="NO_RESIDUAL_PROGRESS", verdict="PASS",
        summary=(
            f"all eligible outer-iteration residual histories show > {thresholds.no_progress_decade_frac:.1f} "
            "decade decay in tail window"
        ),
        detail="",
    )


def math_log10(x: float) -> float:
    """log10 with a zero-guard. Inlined to avoid a dependency in this module."""
    import math
    if x <= 0:
        return 0.0
    return math.log10(x)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def attest(
    log_path: Optional[Path],
    execution_result: Any = None,
    case_id: Optional[str] = None,
    thresholds: Optional[Thresholds] = None,
) -> AttestationResult:
    """Run all 6 checks and aggregate verdict.

    Parameters
    ----------
    log_path : Path or None
        Solver log. None → ATTEST_NOT_APPLICABLE.
    execution_result : Any, optional
        Duck-typed object with .success and .exit_code attrs. Used by A1.
    case_id : str, optional
        Whitelist case ID for per-case YAML override lookup.
    thresholds : Thresholds, optional
        Pre-resolved thresholds. If None, calls load_thresholds(case_id).
    """
    if log_path is None or not log_path.is_file():
        return AttestationResult(overall="ATTEST_NOT_APPLICABLE", checks=[])

    resolved_thresholds = thresholds or load_thresholds(case_id)
    checks = [
        _check_a1_solver_crash(log_path, execution_result=execution_result),
        _check_a2_continuity_floor(log_path, resolved_thresholds),
        _check_a3_residual_floor(log_path, resolved_thresholds),
        _check_a4_iteration_cap(log_path, resolved_thresholds),
        _check_a5_bounding_recurrence(log_path, resolved_thresholds),
        _check_a6_no_progress(log_path, resolved_thresholds),
    ]

    has_fail = any(c.verdict == "FAIL" for c in checks)
    has_hazard = any(c.verdict == "HAZARD" for c in checks)
    if has_fail:
        overall: AttestVerdict = "ATTEST_FAIL"
    elif has_hazard:
        overall = "ATTEST_HAZARD"
    else:
        overall = "ATTEST_PASS"

    return AttestationResult(overall=overall, checks=checks)


def check_to_audit_concern_dict(c: AttestorCheck) -> dict[str, Any]:
    """Serialize a non-PASS AttestorCheck as an audit_concerns[] entry."""
    return {
        "concern_type": c.concern_type,
        "summary": c.summary,
        "detail": c.detail,
        "decision_refs": ["DEC-V61-038"],
        "evidence": c.evidence,
        "attestor_check_id": c.check_id,
        "attestor_verdict": c.verdict,
    }
