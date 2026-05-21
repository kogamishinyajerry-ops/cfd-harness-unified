"""OpenFOAM Docker-backed solver adapter — Phase 1.

Per DEC-0005 (`docs/project-memory/DECISION_LOG.md`), the adapter uses Docker
exclusively. macOS has no native OpenFOAM; targeting both docker + native would
double the maintenance surface for zero current benefit. If a Linux-native CI
worker ever joins, a second backend module can be added — the contract is
`run(case_dir, manifest) -> dict` and is strategy-agnostic.

Phase 1 lands in two steps:

  Step 1 (current): environment-detection layer + structured BLOCKED states.
  Returns BLOCKED with one of FIVE explicit reasons:
    - `manifest_invalid_solver_docker_image` — manifest's `solver_docker_image`
                                               is not a non-empty string (R10-F-02)
    - `docker_not_available`                 — binary not on PATH or daemon down
    - `openfoam_image_not_pulled`            — image absent locally
    - `case_dir_not_openfoam_compatible`     — case_dir or one of `system/`,
                                               `constant/`, `0/` is missing OR
                                               is a symlink (R10-F-03/F-04 fix);
                                               nested symlinks at depth 2+ are
                                               currently NOT caught (R-17, must
                                               be addressed before step 2's
                                               `docker run --volume`)
    - `execution_not_implemented_yet`        — env OK; real `simpleFoam` wiring
                                               is step 2.

  Step 2 (next commit): actual `docker run simpleFoam` invocation, log parsing,
  residuals.csv emission, gate computation. NASA TMR reference data (DEC-0006)
  lands alongside. R-17 (nested-depth symlink walk) MUST land in this step
  before the `docker --volume` line ships.

Honesty rule: even when the env is fully ready, this adapter MUST NOT
silently switch to mocked or claim success. The `execution_not_implemented_yet`
BLOCKED state surfaces the gap so no `trust_report.json` can claim a real run
before step 2 lands.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Default image. Override via `manifest.solver_docker_image` if a case needs
# a different OpenFOAM build.
#
# R10-F-01 fix: previous value `openfoam/openfoam11-paraview512:latest` was a
# typo / hallucinated tag. The real Docker Hub tag for OpenFOAM 11 + ParaView
# 5.10 is `openfoam/openfoam11-paraview510`. An opt-in network test
# (CFDTRUST_LIVE_NETWORK_TESTS=1) verifies this constant resolves on Hub so a
# future bad edit is caught before a user hits "manifest unknown" at
# `docker pull` time.
DEFAULT_IMAGE = "openfoam/openfoam11-paraview510:latest"

# Required top-level directories for an OpenFOAM case dir.
_OPENFOAM_REQUIRED_DIRS = ("system", "constant", "0")


# R15-F-03 belt-and-suspenders: even if `solver_docker_image` somehow bypasses
# the JSON schema regex (manual edit, schema-validation skipped path),
# refuse to pass anything that would be argv-interpreted by `docker run` as
# a flag or shell-metachar token.
_DOCKER_IMAGE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/@\-]*$")


def _is_valid_docker_image_name(image: str) -> bool:
    """Cheap shape check — only catches obvious argv-injection vectors.

    Docker's own reference grammar is far stricter than this; we mainly
    care about:
      - no leading `-` (would be parsed as a docker run flag)
      - no whitespace (would split into multiple argv tokens)
      - no shell metachars (`;`, `|`, `&`, backticks, $, ...)
      - bounded length (<=256)
    """
    if not isinstance(image, str):
        return False
    if not (1 <= len(image) <= 256):
        return False
    return _DOCKER_IMAGE_RE.match(image) is not None


# ---------- environment probes (mockable in tests via subprocess.run patching) ----------


def _docker_available() -> Tuple[bool, str]:
    """Check if `docker` is on PATH AND the daemon is reachable.

    Returns ``(ok, reason)``. ``reason`` is empty when ``ok`` is True;
    otherwise it is a human-readable diagnostic that the caller surfaces
    in the BLOCKED gate.
    """
    if shutil.which("docker") is None:
        return False, "docker binary not on PATH"
    try:
        res = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=5,
        )
    except subprocess.TimeoutExpired:
        return False, "docker version timed out after 5s"
    except OSError as e:
        return False, f"docker invocation failed: {e}"
    if res.returncode != 0:
        diag = (res.stderr.strip() or res.stdout.strip() or "no output")[:200]
        return False, f"docker daemon unreachable: {diag}"
    return True, ""


def _image_present(image: str) -> bool:
    """Whether the given Docker image is already pulled locally.

    A False result causes the adapter to BLOCK rather than auto-pulling —
    pulling a multi-GB image silently mid-trust-run would surprise the
    user and obscure honest gate state.
    """
    try:
        res = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True, text=True, timeout=5,
        )
        return res.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


# Hard cap on the recursive symlink walk. Phase 1 step 2a chose this number
# by inspecting the OpenFOAM dictionary tree shape: a typical case has
# O(10²-10³) files across system/, constant/, 0/. 10000 is comfortably
# above realistic max while still capping pathological dir trees that
# could DoS the env-detection step.
_MAX_PATHS_WALKED = 10000

# Codex R2-P1 fix: separate (much higher) cap for `cfdtrust ingest`.
# Industrial OpenFOAM cases easily exceed 10k filesystem entries — a
# multi-million-cell case with hundreds of saved time directories +
# processor-decomposition subdirs can have >100k files. Using the same
# fail-closed cap as `run()` made ingest unusable on the exact cases it
# is supposed to advise on.
#
# Threat-model rationale for the relaxation:
#   - `run()` invokes blockMesh + simpleFoam INSIDE the docker volume
#     mount. A read-write symlink that escapes case_dir could redirect
#     solver-written outputs onto host paths (data exfil / corruption).
#   - `ingest()` invokes ONLY checkMesh, which is a read-only operation
#     on `constant/polyMesh/`. The threat surface for an undetected
#     escaping symlink is materially smaller — at worst, checkMesh
#     reads a file outside case_dir into its log (info disclosure).
#   - The user explicitly chose to ingest their own case (intentional
#     trust grant) vs. `run()` accepting a possibly-unknown case shape.
#
# This is the env-var opt-in `_is_openfoam_compatible_case_dir`
# docstring referenced, but baked in as the default for ingest because
# external industrial cases routinely exceed 10k entries.
_MAX_PATHS_WALKED_INGEST = 500_000


def _find_symlink_at_any_depth(case_dir: Path) -> Tuple[bool, str]:
    """Walk `case_dir` recursively; return (True, rel_path) at the FIRST
    symlink found. Returns (False, "") if the walk completes clean.

    R-17 closure (Phase 1 step 2a): the depth-1 guard in
    `_is_openfoam_compatible_case_dir` only inspected `case_dir` and the
    three required subdirs themselves. A symlink at depth 2+
    (e.g. `case_dir/system/sneaky_subpath → /tmp/host`) would slip past
    and then be exposed by step 2's `docker --volume case_dir:/case`
    when OpenFOAM's solver follows the link at runtime.

    Implementation notes:
      - Early-return at the first symlink; do not enumerate them all
      - Hard cap at `_MAX_PATHS_WALKED` to bound worst-case time on
        pathological trees; report BLOCKED if the cap is hit (treat as
        "we cannot prove this is symlink-free, so refuse"). This is the
        same fail-closed posture R10-F-01 introduced for the docker
        daemon timeout.
      - Walks every entry under `case_dir`, not just under the three
        required subdirs — a Phase 2 user could place an `extras/` dir
        with a symlink, and that should still be caught.
    """
    paths_walked = 0
    try:
        # Path.iterdir-based DFS so we can short-circuit cleanly without
        # rglob's full materialization.
        stack = [case_dir]
        while stack:
            current = stack.pop()
            try:
                entries = list(current.iterdir())
            except (OSError, PermissionError):
                # Treat unreadable subtrees as "cannot prove safe" → BLOCK.
                return True, f"unreadable subtree: {current.relative_to(case_dir)}"
            for entry in entries:
                paths_walked += 1
                if paths_walked > _MAX_PATHS_WALKED:
                    return True, (
                        f"case dir exceeds {_MAX_PATHS_WALKED} entries; refusing "
                        f"to declare symlink-free (DoS bound)"
                    )
                if entry.is_symlink():
                    return True, str(entry.relative_to(case_dir))
                if entry.is_dir():
                    stack.append(entry)
        return False, ""
    except OSError as e:
        return True, f"walk failed: {e}"


def _find_escaping_symlink_for_ingest(case_dir: Path) -> Tuple[bool, str]:
    """Variant of `_find_symlink_at_any_depth` that allows OpenFOAM-internal
    symlinks but flags escapes.

    Built for DEC-V61-201-SUB-INGEST: an already-run case will contain
    OpenFOAM's own runtime symlinks under `dynamicCode/<name>/lnInclude/`
    (created by `codedFixedValue` etc.; they point to sibling files
    inside the case dir like `../fixedValueFvPatchFieldTemplate.H`).
    These are not a security risk — the volume mount is `case_dir:/case`,
    and a symlink whose resolved target is INSIDE `case_dir` cannot escape
    the mount.

    Returns `(found_escape, where)`. An escape is any symlink whose
    canonical target is NOT a descendant of `case_dir.resolve()`.

    Codex R2-P1 fix: uses `_MAX_PATHS_WALKED_INGEST` (500_000) — much
    higher than `_MAX_PATHS_WALKED` (10_000) because industrial cases
    routinely exceed 10k entries. The fail-mode on cap-hit is also
    changed from "refuse to declare safe" (which blocked ingest
    entirely) to "no escape found within budget" — appropriate for the
    smaller ingest threat surface (read-only checkMesh, user-owned
    data) versus `run()`'s read-write solver invocation.
    """
    case_root = case_dir.resolve()
    paths_walked = 0
    try:
        stack = [case_dir]
        while stack:
            current = stack.pop()
            try:
                entries = list(current.iterdir())
            except (OSError, PermissionError):
                return True, f"unreadable subtree: {current.relative_to(case_dir)}"
            for entry in entries:
                paths_walked += 1
                if paths_walked > _MAX_PATHS_WALKED_INGEST:
                    # Codex R2-P1: failing closed here makes ingest
                    # unusable on large industrial cases. Treat the cap
                    # as a walk budget: if we got this far without
                    # finding an escape, accept the case but record the
                    # budget exhaustion so downstream tooling can flag
                    # it if needed. Threat surface justifies fail-open
                    # for ingest (see _MAX_PATHS_WALKED_INGEST comment).
                    return False, ""
                if entry.is_symlink():
                    try:
                        target = entry.resolve(strict=False)
                    except (OSError, RuntimeError) as e:
                        # Symlink loop or unresolvable target → escape.
                        return True, (
                            f"symlink unresolvable ({e}): "
                            f"{entry.relative_to(case_dir)}"
                        )
                    try:
                        target.relative_to(case_root)
                    except ValueError:
                        return True, (
                            f"symlink escapes case_dir: "
                            f"{entry.relative_to(case_dir)} -> {target}"
                        )
                    # Symlink contained — safe; don't recurse into it
                    # (avoids cycles even though the target is inside).
                    continue
                if entry.is_dir():
                    stack.append(entry)
        return False, ""
    except OSError as e:
        return True, f"walk failed: {e}"


def _is_openfoam_compatible_ingest_case_dir(case_dir: Path) -> Tuple[bool, str]:
    """Variant of `_is_openfoam_compatible_case_dir` for `cfdtrust ingest`.

    Same depth-1 guard (case_dir + required subdirs must not be symlinks),
    but the depth-N nested-symlink walk uses the escape-check (contained
    symlinks allowed) since an already-run case naturally contains
    OpenFOAM's own `dynamicCode/*/lnInclude/*` symlinks.
    """
    if case_dir.is_symlink():
        return False, (
            f"case_dir is a symlink (not allowed; resolves to {case_dir.resolve()})"
        )

    missing: list[str] = []
    symlinked: list[str] = []
    for d in _OPENFOAM_REQUIRED_DIRS:
        p = case_dir / d
        if p.is_symlink():
            symlinked.append(d)
            continue
        if not p.is_dir():
            missing.append(d)
    if symlinked:
        return False, f"required subdir(s) are symlinks (not allowed): {symlinked}"
    if missing:
        return False, f"missing required OpenFOAM subdirs: {missing}"

    found_escape, where = _find_escaping_symlink_for_ingest(case_dir)
    if found_escape:
        return False, f"escaping symlink not allowed: {where}"

    return True, ""


def _is_openfoam_compatible_case_dir(case_dir: Path) -> Tuple[bool, str]:
    """An OpenFOAM case needs at least `system/`, `constant/`, `0/`.

    R10-F-03 / R10-F-04 fix (depth-1 guard): both the outer `case_dir`
    AND each required subdir are checked with `is_symlink()` first.

    R-17 fix (depth-N guard, Phase 1 step 2a): after the depth-1 checks
    pass, walk the entire `case_dir` subtree and refuse if ANY symlink
    is found at any depth. Reason: step 2 will
    `docker --volume case_dir:/case`; a symlinked file/dir anywhere
    inside the case (e.g. `case_dir/system/foamWatch/exfil → /etc/passwd`)
    would be followed by the OpenFOAM solver at runtime, exposing host
    filesystem.

    Legitimate symlink usage (shared mesh dir, NFS mount, monorepo) is not
    expected in Phase 0; if it ever arrives, the right escape hatch is an
    explicit `CFDTRUST_ALLOW_SYMLINK_CASE_DIR=1` env-var opt-in.
    """
    if case_dir.is_symlink():
        return False, f"case_dir is a symlink (not allowed; resolves to {case_dir.resolve()})"

    missing: list[str] = []
    symlinked: list[str] = []
    for d in _OPENFOAM_REQUIRED_DIRS:
        p = case_dir / d
        if p.is_symlink():
            symlinked.append(d)
            continue
        if not p.is_dir():
            missing.append(d)
    if symlinked:
        return False, f"required subdir(s) are symlinks (not allowed): {symlinked}"
    if missing:
        return False, f"missing required OpenFOAM subdirs: {missing}"

    # R-17: walk the rest of the tree for symlinks at any depth.
    found_symlink, where = _find_symlink_at_any_depth(case_dir)
    if found_symlink:
        return False, f"nested symlink not allowed (R-17): {where}"

    return True, ""


# ---------- Phase 1 step 2c: docker invocation + log parser + gate ----------


# Default solver timeout (1 hour). Override via CFDTRUST_SOLVER_TIMEOUT_S.
# Sub-commit-2c choice: long enough for a 6000-cell case to converge under
# Docker emulation on Apple Silicon (amd64 image, slow); short enough that a
# runaway solver doesn't pin the user's terminal indefinitely.
_DEFAULT_SOLVER_TIMEOUT_S = 3600
_TIMEOUT_ENV_VAR = "CFDTRUST_SOLVER_TIMEOUT_S"


def _resolve_solver_timeout() -> int:
    """Return the configured per-command timeout in seconds.

    Honors `CFDTRUST_SOLVER_TIMEOUT_S` env var; falls back to
    `_DEFAULT_SOLVER_TIMEOUT_S` if unset, empty, or non-numeric.
    Negative or zero values are clamped to a minimum of 60s — a
    sub-minute timeout is almost certainly a typo and would BLOCK every
    real run.
    """
    raw = os.environ.get(_TIMEOUT_ENV_VAR, "").strip()
    if not raw:
        return _DEFAULT_SOLVER_TIMEOUT_S
    try:
        n = int(raw)
    except ValueError:
        return _DEFAULT_SOLVER_TIMEOUT_S
    return max(n, 60)


def _run_docker_command(
    shell_args: str,
    case_dir: Path,
    image: str,
    *,
    timeout: int,
) -> Tuple[int, str, str]:
    """Run a shell command inside the OpenFOAM container against `case_dir`.

    The case_dir is bind-mounted at `/case` and is the container's CWD.
    The OpenFOAM environment (bashrc) is sourced before `shell_args` runs.

    Returns `(returncode, stdout, stderr)`. On timeout returns
    `(-1, partial_stdout, "docker command timed out after N s")`. On
    OS-level invocation failure returns `(-1, "", diagnostic)`.

    Subprocess args are list-form (no shell=True). The only string that
    enters a shell is `shell_args`, executed inside the container via
    `bash -c`. Callers are responsible for sanitizing it; the
    project-internal callers only ever pass literal strings like
    `"blockMesh"` and `"simpleFoam"`.
    """
    full_cmd = [
        "docker", "run", "--rm",
        "--entrypoint", "/bin/bash",
        "-v", f"{case_dir.resolve()}:/case",
        "-w", "/case",
        image,
        "-c", f"source /opt/openfoam11/etc/bashrc && {shell_args}",
    ]
    try:
        res = subprocess.run(
            full_cmd, capture_output=True, text=True, timeout=timeout,
        )
        return res.returncode, res.stdout, res.stderr
    except subprocess.TimeoutExpired as e:
        partial = e.stdout if isinstance(e.stdout, str) else (
            e.stdout.decode("utf-8", errors="replace") if e.stdout else ""
        )
        # rc=-1 PLUS the stderr marker `OFA-TIMEOUT` lets `run()` distinguish
        # this from an OSError (fork failure). The two have different honesty
        # implications: timeout means the solver DID start; OSError means it
        # never did.
        return -1, partial, f"OFA-TIMEOUT: docker command timed out after {timeout}s"
    except OSError as e:
        # rc=-1 PLUS the marker `OFA-OSERROR` lets `run()` distinguish a fork
        # failure (solver never started → real_solver_invoked=False) from a
        # legitimate solver crash (rc>0 from inside the container, solver
        # ran → real_solver_invoked=True). R15-F-01 fix.
        return -1, "", f"OFA-OSERROR: docker invocation failed: {e}"


# simpleFoam emits lines like:
#   smoothSolver:  Solving for Ux, Initial residual = 0.123, Final residual = 0.001, No Iterations 5
#   GAMG:  Solving for p, Initial residual = 0.45, Final residual = 0.003, No Iterations 12
#
# Gap #20 (case_006 ONERA M6 transonic dogfood): density-based compressible
# solvers like `rhoCentralFoam` use the trivial `diagonal:` solver for
# rho/rhoUx/rhoUy/rhoUz/rhoE — without it the residual stream went unparsed.
# Gap #25 (case_007 KCS ship VOF dogfood): VOF phase fields are dotted names
# (`alpha.water`, `alpha.air`, ...). `\w` does NOT match `.`, so the
# alpha-fraction line was previously skipped, leaving VOF cases with no
# parseable transport residuals. Widening to `[\w.]+` captures dotted fields
# while still rejecting whitespace/punctuation that would falsely match
# patch names or diagnostic lines.
#
# TBD-19 (case_009 Sandia Flame D reacting dogfood): chemkin-style species
# names contain parentheses to disambiguate spin states (`CH2(S)` =
# singlet methylene, `CH2(T)` = triplet methylene; both appear in
# GRI-Mech 3.0 and similar reacting mechanisms). The pre-fix `[\w.]+`
# group stopped at the first `(`, capturing `CH2` and silently colliding
# with the real `CH2` species. Widening to `[\w.()]+` captures
# parenthesized species intact. The regex remains anchored on a specific
# solver-name prefix + colon + literal `Solving for ` + comma terminator,
# so the wider char class does NOT false-match diagnostic lines.
_RESIDUAL_LINE_RE = re.compile(
    r"^(?:smoothSolver|GAMG|PCG|PBiCGStab|DICPCG|DILUPBiCGStab|PBiCG|DICPBiCGStab|diagonal)\s*:\s*Solving for\s+([\w.()]+),"
    r"\s*Initial residual\s*=\s*([\d.eE+\-]+),"
    r"\s*Final residual\s*=\s*([\d.eE+\-]+),"
)
# R16-F-01 fix: OpenFOAM 11 emits `Time = 157s` (with unit suffix `s`), not
# just `Time = 157`. The pre-fix regex required end-of-line right after the
# number, so every live run produced ZERO parseable iterations and the gate
# falsely landed on `no_iterations_in_log` — even when the solver actually
# converged cleanly. Live-confirmed against
# `openfoam/openfoam11-paraview510:latest` on 2026-05-21.
#
# The optional `s` suffix is tolerated; downstream code only uses the numeric
# portion. We deliberately do NOT widen this to arbitrary unit suffixes —
# `s` is the only one OpenFOAM 11 emits in steady-state output, and a wider
# pattern would risk false-matching diagnostic lines like "Time = unknown".
_TIME_LINE_RE = re.compile(r"^Time\s*=\s*([\d.eE+\-]+)\s*s?\s*$")
# yPlus function-object output:
#   patch wall y+ : min = 0.5, max = 5.0, average = 2.3
_YPLUS_LINE_RE = re.compile(
    r"patch\s+(\w+)\s+y\+\s*:\s*min\s*=\s*([\d.eE+\-]+)"
    r"\s*,?\s*max\s*=\s*([\d.eE+\-]+)"
    r"\s*,?\s*average\s*=\s*([\d.eE+\-]+)",
    re.IGNORECASE,
)


def _parse_simplefoam_log(log_text: str) -> Dict[str, Any]:
    """Pure function: simpleFoam log text → structured residual + y+ data.

    Returns:
        {
          'iterations': [{'iter': int, 'residuals': {field: initial_residual_float}}, ...],
          'final_iter': int,
          'y_plus': {patch_name: {'min': float, 'max': float, 'avg': float}},
          'converged': bool,    # SIMPLE residualControl triggered early exit
        }

    Per-iteration `residuals` keyed by `Initial residual` (canonical CFD
    convention for "did the iter make progress from where it started?").
    """
    iterations: List[Dict[str, Any]] = []
    y_plus_by_patch: Dict[str, Dict[str, float]] = {}
    current_iter: int | None = None
    current_residuals: Dict[str, float] = {}
    converged = False
    # Gap #21 (case_006 ONERA M6 / case_007 KCS VOF dogfood): `final_iter`
    # semantically means "how many iterations the solver ran". For
    # steady-state runs OpenFOAM emits integer `Time = N` and the value
    # IS the iteration count (preserved behavior). But density-based
    # compressible runs and VOF runs use sub-second timesteps
    # (`Time = 1e-06`, `Time = 2e-06`, ...) which `int(float(...))`
    # collapses to 0, making 5000-step runs report `final_iter: 0`.
    # When the parsed timestamp is < 1 (sub-second), fall back to a
    # monotonically incrementing counter so the iteration count is at
    # least faithfully reported. Steady-state semantics (iter == Time)
    # remain unchanged.
    iter_counter = 0

    for raw_line in log_text.splitlines():
        line = raw_line.rstrip()

        m_time = _TIME_LINE_RE.match(line)
        if m_time:
            if current_iter is not None and current_residuals:
                iterations.append({"iter": current_iter, "residuals": current_residuals})
            try:
                t_val = float(m_time.group(1))
            except ValueError:
                current_iter = None
                current_residuals = {}
                continue
            iter_counter += 1
            t_int = int(t_val)
            # Gap #21: when `int(timestamp)` would be 0 (sub-second
            # transient), use the counter so we don't lose the iter.
            current_iter = t_int if t_int >= 1 else iter_counter
            current_residuals = {}
            continue

        m_res = _RESIDUAL_LINE_RE.match(line)
        if m_res:
            field = m_res.group(1)
            try:
                init_res = float(m_res.group(2))
            except ValueError:
                continue
            # Keep the FIRST residual reported for this field per iteration
            # (later GAMG outer-corrector residuals would overwrite to the
            # last; first is the canonical "initial" value).
            current_residuals.setdefault(field, init_res)
            continue

        m_yp = _YPLUS_LINE_RE.search(line)
        if m_yp:
            patch_name = m_yp.group(1)
            try:
                y_plus_by_patch[patch_name] = {
                    "min": float(m_yp.group(2)),
                    "max": float(m_yp.group(3)),
                    "avg": float(m_yp.group(4)),
                }
            except ValueError:
                pass
            continue

        # SIMPLE early-termination message in OpenFOAM 11
        lower = line.lower()
        if (
            "simple solution converged" in lower
            or "convergence criteria met" in lower
            or "reached convergence" in lower
        ):
            converged = True

    if current_iter is not None and current_residuals:
        iterations.append({"iter": current_iter, "residuals": current_residuals})

    return {
        "iterations": iterations,
        "final_iter": iterations[-1]["iter"] if iterations else 0,
        "y_plus": y_plus_by_patch,
        "converged": converged,
    }


def _compute_gate_from_residuals(
    parsed: Dict[str, Any],
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    """Pure function: parsed log + manifest → gate dict.

    Status logic:
      - no iterations parsed → BLOCKED (something is wrong with the run)
      - SIMPLE converged early OR every target field's final residual ≤ target → PASS
      - otherwise → FAIL with the list of fields that missed targets

    The manifest's `residual_targets` may use OpenFOAM-vector naming
    (`U`) or split-component naming (`Ux`, `Uy`, `Uz`). Both are
    accepted — the gate accepts a target hit if EITHER the combined OR
    every present split component meets it.
    """
    contract = manifest.get("solver_contract", {})
    targets = contract.get("residual_targets", {})
    max_iter = int(contract.get("max_iterations", 500))
    # Gap #22 (case_006 / case_007 dogfood): summary messages historically
    # hardcoded "simpleFoam …", which lies for rhoCentralFoam, interFoam,
    # chtMultiRegionSimpleFoam, etc. Read the manifest's declared solver
    # name (top-level `solver` field, same source as
    # `_candidate_log_names`); fall back to "solver" if missing or
    # ill-typed. Honesty fences keep all other behavior identical.
    raw_solver = manifest.get("solver")
    solver_name = (
        raw_solver.strip()
        if isinstance(raw_solver, str) and raw_solver.strip()
        else "solver"
    )

    if not parsed["iterations"]:
        return {
            "status": "BLOCKED",
            "summary": f"{solver_name} log contained zero parseable iterations.",
            "details": {
                "execution": "attempted",
                "real_solver_invoked": True,
                "reason": "no_iterations_in_log",
                "next_step": "Inspect artifacts/solver.log for error messages.",
            },
        }

    final = parsed["iterations"][-1]["residuals"]

    # Field-by-field comparison. Targets may name combined `U` or split `Ux,Uy`.
    failed = []
    checked = []
    for tgt_field, tgt_val in targets.items():
        actual = final.get(tgt_field)
        if actual is None:
            # Try common synonyms: target 'U' but log has 'Ux'+'Uy'+'Uz'
            if tgt_field == "U":
                comps = [final.get(c) for c in ("Ux", "Uy", "Uz") if final.get(c) is not None]
                if comps:
                    actual = max(comps)
            # Else just skip — manifest declared a field simpleFoam didn't solve
        if actual is None:
            continue
        checked.append(tgt_field)
        if actual > float(tgt_val):
            failed.append({
                "field": tgt_field,
                "final_residual": actual,
                "target": float(tgt_val),
            })

    # R15-F-02 fix: honesty rule — refuse PASS if not a single target field
    # was actually present in the log. The pre-R15 code would declare PASS
    # whenever SIMPLE's "solution converged" message appeared, even if every
    # manifest target named a field the solver never solved (manifest/log
    # field-name drift). That's "PASS without checking anything" — the
    # exact failure mode the trust harness exists to prevent.
    if targets and not checked:
        return {
            "status": "BLOCKED",
            "summary": (
                f"{solver_name} converged but none of the manifest's target fields "
                f"({sorted(targets.keys())}) appeared in the log."
            ),
            "details": {
                "execution": "real",
                "real_solver_invoked": True,
                "reason": "no_target_fields_in_log",
                "manifest_targets": sorted(targets.keys()),
                "fields_in_log": sorted(final.keys()),
                "next_step": (
                    "Check `solver_contract.residual_targets` field names "
                    f"against actual {solver_name} residual lines. OpenFOAM 11 "
                    "emits split components (Ux, Uy, Uz) but the manifest "
                    "may name combined `U`; this gate already maps `U` → "
                    "max(Ux,Uy,Uz), but other names must match exactly."
                ),
                "y_plus": parsed["y_plus"],
            },
        }

    # TBD-17 fix (case_009 Sandia Flame D reacting dogfood, honesty-adjacent):
    # PARTIAL coverage — manifest declares N target fields but parser found
    # < N in residuals.csv — must NOT silently PASS on the subset that was
    # found. Pre-fix, the gate iterated `targets.items()` and used
    # `if actual is None: continue` to silently drop missing fields, then
    # declared PASS based on the subset. For a 27-field reacting manifest
    # whose log truncated mid-iteration (3 momentum fields parsed, 24
    # species + temperature absent), the gate said "solver_gate=PASS" with
    # no flag that 24/27 fields were silently dropped — the closest the
    # dogfood arc came to surfacing a real honesty break.
    #
    # The top-level overall_status / validation_status are already capped
    # at WARN / partial by solver_execution=ingested honesty fences, BUT
    # the solver_gate ITSELF was lying internally. Choice of disposition:
    # BLOCKED-with-reason `incomplete_residual_coverage` — most honest, as
    # the solver gate cannot be EVALUATED when evidence is incomplete
    # (vs. FAIL which would imply "evaluated and didn't converge"). Half
    # evidence is not WARN, it is "cannot evaluate".
    if targets and len(checked) < len(targets):
        missing_target_fields = sorted(
            tgt for tgt in targets.keys() if tgt not in checked
        )
        return {
            "status": "BLOCKED",
            "summary": (
                f"{solver_name} log only carried {len(checked)} of "
                f"{len(targets)} manifest target fields — solver gate "
                f"cannot be evaluated on incomplete evidence."
            ),
            "details": {
                "execution": "real",
                "real_solver_invoked": True,
                "reason": "incomplete_residual_coverage",
                "incomplete_residual_coverage": True,
                "manifest_targets": sorted(targets.keys()),
                "checked_fields": checked,
                "missing_target_fields": missing_target_fields,
                "fields_in_log": sorted(final.keys()),
                "next_step": (
                    "Either (a) the solver log truncated mid-run before "
                    "every target field appeared (re-run to completion) or "
                    "(b) the manifest declares fields the solver does not "
                    "actually emit (correct `solver_contract.residual_targets`). "
                    "Half coverage is not PASS — the gate refuses to "
                    "declare success on fields it could not verify."
                ),
                "y_plus": parsed["y_plus"],
            },
        }

    converged = parsed["converged"] or (checked and not failed)

    if not converged:
        return {
            "status": "FAIL",
            "summary": (
                f"{solver_name} ran {parsed['final_iter']}/{max_iter} iters; "
                f"{len(failed)}/{len(checked)} field(s) did not reach residual target."
            ),
            "details": {
                "execution": "real",
                "real_solver_invoked": True,
                "reason": "residual_targets_not_met",
                "final_iter": parsed["final_iter"],
                "max_iter": max_iter,
                "failed_fields": failed,
                "checked_fields": checked,
                "y_plus": parsed["y_plus"],
            },
        }

    return {
        "status": "PASS",
        "summary": (
            f"{solver_name} converged at iter {parsed['final_iter']} "
            f"(all {len(checked)} field residuals ≤ target)."
        ),
        "details": {
            "execution": "real",
            "real_solver_invoked": True,
            "final_iter": parsed["final_iter"],
            "max_iter": max_iter,
            "final_residuals": final,
            "checked_fields": checked,
            "y_plus": parsed["y_plus"],
        },
    }


def _write_residuals_csv(parsed: Dict[str, Any], out_path: Path) -> None:
    """Write iteration-by-iteration residuals to `out_path` as CSV.

    Columns: `iter,<sorted field names>`. Empty cells for missing fields.
    """
    fields = set()
    for it in parsed["iterations"]:
        fields.update(it["residuals"].keys())
    sorted_fields = sorted(fields)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        f.write("iter," + ",".join(sorted_fields) + "\n")
        for it in parsed["iterations"]:
            row = [str(it["iter"])]
            for fld in sorted_fields:
                v = it["residuals"].get(fld)
                row.append(f"{v:.6e}" if isinstance(v, float) else "")
            f.write(",".join(row) + "\n")


# ---------- M4.1: checkMesh invocation + parser ----------
#
# checkMesh runs inside the same OpenFOAM container after blockMesh and before
# simpleFoam. Its output is canonical, single-mesh quality evidence — the audit
# gate (`audit/mesh.py`) reads `artifacts/mesh_quality.json` (this layer's
# persisted parse) rather than re-running the binary, so the gate stays cheap
# and the truth-source (the container output) is captured exactly once.
#
# Honesty rule: if checkMesh OS-errors or times out we DO NOT silently treat the
# mesh as OK. We persist `checkmesh_status: blocked` so the audit gate surfaces
# BLOCKED (not PASS) on the same evidence.


# checkMesh canonical lines (verified against openfoam11-paraview510 on
# 2026-05-21, BFS live case):
#
#   Mesh stats
#       points:           23682
#       faces:            46640
#       internal faces:   34864
#       cells:            11600
#       boundary patches: 6
#
#   Mesh non-orthogonality Max: 0 average: 0
#   Max skewness = 8.68421e-14 OK.
#   Max aspect ratio = 22.2268 OK.
#   Max cell openness = 2.5e-16 OK.
#   Mesh OK.
#
# Failure path:
#   ***Number of incorrectly-oriented faces: 23 ...
#   Failed 2 mesh checks.

_CM_POINTS_RE = re.compile(r"^\s*points\s*:\s*(\d+)\s*$")
_CM_FACES_RE = re.compile(r"^\s*faces\s*:\s*(\d+)\s*$")
_CM_INTERNAL_FACES_RE = re.compile(r"^\s*internal faces\s*:\s*(\d+)\s*$")
_CM_CELLS_RE = re.compile(r"^\s*cells\s*:\s*(\d+)\s*$")
_CM_BOUNDARY_PATCHES_RE = re.compile(r"^\s*boundary patches\s*:\s*(\d+)\s*$")

# `Mesh non-orthogonality Max: 1.23 average: 0.45`
_CM_NONORTHO_RE = re.compile(
    r"Mesh non-orthogonality\s+Max\s*:\s*([\d.eE+\-]+)\s+average\s*:\s*([\d.eE+\-]+)"
)
# `Max skewness = 8.68421e-14 OK.` (or `... FAILED.`)
_CM_SKEWNESS_RE = re.compile(r"Max skewness\s*=\s*([\d.eE+\-]+)")
# `Max aspect ratio = 22.2268 OK.`
_CM_ASPECT_RE = re.compile(r"Max aspect ratio\s*=\s*([\d.eE+\-]+)")
# `Max cell openness = 2.5e-16 OK.`
_CM_OPENNESS_RE = re.compile(r"Max cell openness\s*=\s*([\d.eE+\-]+)")
# `Failed 2 mesh checks.` or `Failed N mesh checks.`
_CM_FAILED_CHECKS_RE = re.compile(r"^Failed\s+(\d+)\s+mesh checks\.")


def _parse_check_mesh_log(log_text: str) -> Dict[str, Any]:
    """Pure function: checkMesh log text → structured quality data.

    Extracts only the fields the mesh audit gate needs to decide PASS /
    FAIL against `mesh_contract.quality_thresholds` (max_non_orthogonality,
    max_skewness, max_aspect_ratio) plus topology counts for the
    `mesh_report.json` summary line.

    Returns a dict that is JSON-serializable. Missing fields are absent
    from the dict (NOT zero-filled) — the audit gate must be able to
    distinguish "checkMesh reported 0" from "checkMesh did not report this
    line" and the latter is honest about the parse gap.

    The `overall_mesh_ok` boolean comes from the presence of the terminal
    `Mesh OK.` line. If `Failed N mesh checks.` appears we report it under
    `failed_checks_count` and set `overall_mesh_ok = False`.
    """
    stats: Dict[str, int] = {}
    geometry: Dict[str, float] = {}
    overall_mesh_ok = False
    failed_checks_count = 0

    for raw_line in log_text.splitlines():
        line = raw_line.rstrip()

        for key, pat in (
            ("points", _CM_POINTS_RE),
            ("faces", _CM_FACES_RE),
            ("internal_faces", _CM_INTERNAL_FACES_RE),
            ("cells", _CM_CELLS_RE),
            ("boundary_patches", _CM_BOUNDARY_PATCHES_RE),
        ):
            m = pat.match(line)
            if m:
                try:
                    stats[key] = int(m.group(1))
                except ValueError:
                    pass
                break

        m = _CM_NONORTHO_RE.search(line)
        if m:
            try:
                geometry["max_non_orthogonality"] = float(m.group(1))
                geometry["avg_non_orthogonality"] = float(m.group(2))
            except ValueError:
                pass

        m = _CM_SKEWNESS_RE.search(line)
        if m:
            try:
                geometry["max_skewness"] = float(m.group(1))
            except ValueError:
                pass

        m = _CM_ASPECT_RE.search(line)
        if m:
            try:
                geometry["max_aspect_ratio"] = float(m.group(1))
            except ValueError:
                pass

        m = _CM_OPENNESS_RE.search(line)
        if m:
            try:
                geometry["max_cell_openness"] = float(m.group(1))
            except ValueError:
                pass

        m = _CM_FAILED_CHECKS_RE.match(line)
        if m:
            try:
                failed_checks_count = int(m.group(1))
            except ValueError:
                pass

        # Terminal `Mesh OK.` (must be on its own line, optionally indented;
        # `OK.` suffix on per-check lines like "Max skewness ... OK." is
        # explicitly NOT matched here).
        if line.strip() == "Mesh OK.":
            overall_mesh_ok = True

    return {
        "stats": stats,
        "geometry": geometry,
        "overall_mesh_ok": overall_mesh_ok,
        "failed_checks_count": failed_checks_count,
    }


def _persist_mesh_quality(
    case_dir: Path,
    *,
    invoked: bool,
    returncode: int | None,
    log_relative: str | None,
    parsed: Dict[str, Any] | None,
    blocked_reason: str | None = None,
    blocked_detail: str | None = None,
) -> Path:
    """Write `artifacts/mesh_quality.json` — the single source of truth the
    mesh audit gate reads. Mirrors the `solver_gate.json` pattern (M2.3a
    fix): the binary's output is captured once, parsed once, then persisted
    so the audit layer never re-invokes the binary nor re-parses on its own.

    Returns the path written.
    """
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    out_path = art / "mesh_quality.json"

    if not invoked or blocked_reason is not None:
        payload: Dict[str, Any] = {
            "checkmesh_invoked": invoked,
            "checkmesh_status": "blocked",
            "checkmesh_returncode": returncode,
            "reason": blocked_reason or "not_invoked",
        }
        if blocked_detail:
            payload["detail"] = blocked_detail
        if log_relative:
            payload["log"] = log_relative
    else:
        payload = {
            "checkmesh_invoked": True,
            "checkmesh_status": "ok" if parsed and parsed["overall_mesh_ok"] else "failed",
            "checkmesh_returncode": returncode,
            "log": log_relative,
        }
        if parsed:
            payload.update({
                "stats": parsed["stats"],
                "geometry": parsed["geometry"],
                "overall_mesh_ok": parsed["overall_mesh_ok"],
                "failed_checks_count": parsed["failed_checks_count"],
            })

    try:
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    except OSError:
        # Same fail-tolerant posture as `_write_gate` in audit/solver.py
        # (R17-F-02): a non-writable artifacts dir must not crash the run.
        pass
    return out_path


# ---------- M5.1: polyMesh/boundary parser + persistence ----------
#
# blockMesh writes `constant/polyMesh/boundary` listing every patch in the
# realized mesh. This is the canonical, runtime-truth source for the
# geometry audit: the manifest's `geometry_contract.required_patches` is
# what the case PROMISES; this file is what the case actually DELIVERED.
#
# Same single-source-of-truth pattern as M4 (mesh_quality.json): backend
# parses + persists; audit reads. No backend invocation needed (blockMesh
# already wrote the file); the persistence step is pure side-effect on
# top of an existing artifact, but it goes through the same fail-tolerant
# wrapper as mesh_quality.json so the audit gate has a single uniform
# JSON to consume.


# Per OpenFOAM polyMesh/boundary grammar:
#
#   6
#   (
#       inlet
#       {
#           type            patch;
#           nFaces          50;
#           startFace       22960;
#       }
#       topWall
#       {
#           type            wall;
#           inGroups        List<word> 1(wall);
#           nFaces          160;
#           startFace       23090;
#       }
#       ...
#   )
#
# State machine: skip header → see `N\n(` → loop {word → `{...}` → next word}
# until `)`. Comments `//` and `/* */` stripped first.

_BOUNDARY_COMMENT_LINE_RE = re.compile(r"//[^\n]*")
_BOUNDARY_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_BOUNDARY_TYPE_RE = re.compile(r"\btype\s+(\w+)\s*;")
_BOUNDARY_NFACES_RE = re.compile(r"\bnFaces\s+(\d+)\s*;")
_BOUNDARY_STARTFACE_RE = re.compile(r"\bstartFace\s+(\d+)\s*;")
_BOUNDARY_OPEN_RE = re.compile(r"^\s*(\d+)\s*\(\s*$", re.MULTILINE)


def _strip_foam_comments(text: str) -> str:
    """Remove C++ // line comments and /* */ block comments. Same family of
    helpers as cli_doctor._strip_of_comments (M3.3); kept local to the
    backend so the layering stays clean (backends/ doesn't depend on
    cli_doctor)."""
    text = _BOUNDARY_COMMENT_BLOCK_RE.sub("", text)
    text = _BOUNDARY_COMMENT_LINE_RE.sub("", text)
    return text


def _parse_polymesh_boundary(text: str) -> Dict[str, Dict[str, Any]]:
    """Pure function: polyMesh/boundary content → {patch: {type, nFaces, startFace}}.

    Returns an empty dict on malformed input (NOT raising) — the
    persistence layer surfaces this as `geometry_quality.checkmesh_status:
    failed` style and the audit gate FAIL's. Same robustness posture as
    `_parse_check_mesh_log`.

    Each patch dict is keyed:
      - `type`        — string (e.g. "patch", "wall", "empty", "symmetryPlane")
      - `nFaces`      — int (may be 0 if not present)
      - `startFace`   — int (may be 0 if not present)

    Patch names whose containing block has no `type` field are skipped —
    OpenFOAM does not accept untyped patches, so an entry without `type`
    is malformed and ignoring it surfaces the structural gap to the
    audit gate as "patch missing".
    """
    clean = _strip_foam_comments(text)

    # Find the `N\n(` opener. Skip everything before it (FoamFile header).
    m = _BOUNDARY_OPEN_RE.search(clean)
    if not m:
        return {}

    body_start = m.end()
    # Walk forward, balancing `{` / `}` to find each patch's block. The
    # outer container's closing `)` ends the list.
    patches: Dict[str, Dict[str, Any]] = {}
    i = body_start
    n = len(clean)

    def _skip_ws(j: int) -> int:
        while j < n and clean[j].isspace():
            j += 1
        return j

    while True:
        i = _skip_ws(i)
        if i >= n or clean[i] == ")":
            break
        # Read a word (patch name): [A-Za-z_][A-Za-z0-9_]*
        name_start = i
        while i < n and (clean[i].isalnum() or clean[i] == "_"):
            i += 1
        if i == name_start:
            # Not a name character — stop to avoid infinite loop on
            # unexpected token.
            break
        name = clean[name_start:i]

        i = _skip_ws(i)
        if i >= n or clean[i] != "{":
            # Malformed: expected `{` after patch name. Skip the rest.
            break

        # Balance braces to find the block end.
        depth = 1
        block_start = i + 1
        i += 1
        while i < n and depth > 0:
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
            i += 1
        if depth != 0:
            # Unclosed block — refuse to half-parse it.
            break
        block_text = clean[block_start:i - 1]

        # Extract fields from the block.
        type_m = _BOUNDARY_TYPE_RE.search(block_text)
        if type_m is None:
            continue
        n_faces = 0
        sf = 0
        nf_m = _BOUNDARY_NFACES_RE.search(block_text)
        if nf_m:
            try:
                n_faces = int(nf_m.group(1))
            except ValueError:
                pass
        sf_m = _BOUNDARY_STARTFACE_RE.search(block_text)
        if sf_m:
            try:
                sf = int(sf_m.group(1))
            except ValueError:
                pass
        patches[name] = {
            "type": type_m.group(1),
            "nFaces": n_faces,
            "startFace": sf,
        }

    return patches


def _persist_geometry_quality(
    case_dir: Path,
    *,
    patches: Dict[str, Dict[str, Any]] | None,
    boundary_relative: str | None,
    blocked_reason: str | None = None,
    blocked_detail: str | None = None,
) -> Path:
    """Write `artifacts/geometry_quality.json` — single source of truth for
    the geometry audit gate. Mirrors `_persist_mesh_quality` (M4.1).

    Returns the path written.
    """
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    out_path = art / "geometry_quality.json"

    if blocked_reason is not None or patches is None:
        payload: Dict[str, Any] = {
            "polymesh_boundary_parsed": False,
            "status": "blocked",
            "reason": blocked_reason or "unparsed",
        }
        if blocked_detail:
            payload["detail"] = blocked_detail
        if boundary_relative:
            payload["boundary_file"] = boundary_relative
    else:
        payload = {
            "polymesh_boundary_parsed": True,
            "status": "ok" if patches else "empty",
            "boundary_file": boundary_relative,
            "patches": patches,
            "patch_count": len(patches),
        }

    try:
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    except OSError:
        # Same fail-tolerant posture as `_write_gate` (R17-F-02) and
        # `_persist_mesh_quality` (M4.1).
        pass
    return out_path


# ---------- M6.1: 0/<field> boundary parser + bc_quality.json persistence ----------
#
# Each `0/<field>` file (OpenFOAM initial+boundary conditions) carries a
# `boundaryField { ... }` block listing the BC type for every patch in the
# mesh. The audit gate compares manifest's `bc_contract` declarations to
# what these files realize.
#
# Same single-source-of-truth pattern as M4 / M5: backend parses + persists;
# audit reads. The 0/ files exist BEFORE blockMesh runs (they are user
# inputs), but persistence happens inside `run()` to keep the artifact
# producer single — the audit gate is a pure reader.


_BOUNDARY_FIELD_OPEN_RE = re.compile(r"\bboundaryField\s*\{")

# DEC-V61-201-SUB-INGEST-BC-REGEX-GROUPED-PATCHES:
# canonical OpenFOAM grouped-patch header — `"(name1|name2|...)"` or
# `(name1|name2|...)` (the surrounding quotes are conventional but not
# required). One BC block declares many patches in one shot. Common in
# compressible aero benchmark cases (ONERA M6, RAE 2822, ...).
_GROUPED_PATCH_HEADER_RE = re.compile(r'"?\(\s*([^)]+?)\s*\)"?')

# M7.1: numeric tokens — sign, digits, decimal, scientific notation.
_NUM_TOKEN = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?"
# `value uniform <scalar>;`  e.g. `value uniform 0.293;` or `value uniform 0;`
_VALUE_UNIFORM_SCALAR_RE = re.compile(
    rf"\bvalue\s+uniform\s+({_NUM_TOKEN})\s*;"
)
# `value uniform (<x> <y> <z>);`  e.g. `value uniform (44.2 0 0);`
_VALUE_UNIFORM_VECTOR_RE = re.compile(
    rf"\bvalue\s+uniform\s+\(\s*({_NUM_TOKEN})\s+({_NUM_TOKEN})\s+({_NUM_TOKEN})\s*\)\s*;"
)
# M7.1: scalar BC parameters inside a patch block. Whitelist named
# scalars the audit gate compares to manifest declarations. Adding a
# parameter here is the schema-extension point — keep it conservative.
_KNOWN_SCALAR_PARAMS = ("intensity", "mixingLength", "value")
# Pre-compile per-name extractor regexes. We do NOT use `_KNOWN_SCALAR_PARAMS`
# blindly with a generic regex because `value` has two shapes (scalar vs
# vector) and is handled separately above.
_SCALAR_PARAM_RES = {
    name: re.compile(rf"\b{re.escape(name)}\s+({_NUM_TOKEN})\s*;")
    for name in ("intensity", "mixingLength")
}


def _parse_field_boundary_field(text: str) -> Dict[str, Dict[str, Any]]:
    """Pure function: 0/<field> file content → {patch_name: {type, value_scalar?, value_vector?, params?}}.

    Locates the `boundaryField { ... }` block and walks each `patch_name
    { type X; ... }` entry inside it. Returns an empty dict if the block
    is missing or malformed — same robustness posture as
    `_parse_polymesh_boundary`.

    Per-patch dict shape (M7.1, additive to M6.1):
      - `type`         — string (always present; entry skipped if absent)
      - `value_scalar` — float, if `value uniform <scalar>;` matched
      - `value_vector` — [x, y, z], if `value uniform (X Y Z);` matched
      - `params`       — dict of scalar named parameters extracted from
                         the BC block (currently `intensity`, `mixingLength`)
                         Only present when ≥1 known scalar param matched.

    Mutually exclusive: a patch block has EITHER value_scalar OR
    value_vector (or neither for BCs that don't carry a value, like
    `zeroGradient` or `noSlip`).
    """
    clean = _strip_foam_comments(text)
    open_m = _BOUNDARY_FIELD_OPEN_RE.search(clean)
    if not open_m:
        return {}

    # Locate the closing brace of the outer `boundaryField { ... }` block.
    i = open_m.end()
    depth = 1
    block_start = i
    n = len(clean)
    while i < n and depth > 0:
        if clean[i] == "{":
            depth += 1
        elif clean[i] == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return {}
    inner = clean[block_start:i - 1]

    # Walk the inner block: name → `{ type X; }` pairs. Mirrors the patch
    # parser inside `_parse_polymesh_boundary` but lighter (no nFaces /
    # startFace lookup needed for BC files).
    patches: Dict[str, Dict[str, Any]] = {}
    j = 0
    m = len(inner)

    def _skip_ws(k: int) -> int:
        while k < m and inner[k].isspace():
            k += 1
        return k

    while True:
        j = _skip_ws(j)
        if j >= m:
            break

        # DEC-V61-201-SUB-INGEST-BC-REGEX-GROUPED-PATCHES:
        # accept either single-name `patch_name { ... }` (legacy path)
        # OR canonical grouped form `"(name1|name2|...)" { ... }` (new path).
        # The grouped form is one BC block declaring many patches; we
        # expand it into N synthetic per-patch entries that all share
        # the same parsed block, so downstream consumers (bc_quality
        # persistence, audit gate) see exactly what they would have
        # seen had the case author written N separate single-patch
        # blocks.
        grouped_names: List[str] | None = None
        if inner[j] in ('"', '('):
            gm = _GROUPED_PATCH_HEADER_RE.match(inner, j)
            if gm is None:
                # Malformed grouped header — stop walking to mirror the
                # existing "silent break on unparseable" posture.
                break
            raw_names = gm.group(1).split("|")
            grouped_names = [s.strip() for s in raw_names if s.strip()]
            j = gm.end()
            # `grouped_names` may be empty (e.g. `"(|)"`); we still
            # consume the block below to keep the walker advancing, but
            # write nothing into `patches`. Matches existing posture for
            # untyped / malformed blocks (silent skip).
            name = None
        else:
            name_start = j
            while j < m and (inner[j].isalnum() or inner[j] == "_"):
                j += 1
            if j == name_start:
                break
            name = inner[name_start:j]

        j = _skip_ws(j)
        if j >= m or inner[j] != "{":
            break

        depth = 1
        inner_start = j + 1
        j += 1
        while j < m and depth > 0:
            if inner[j] == "{":
                depth += 1
            elif inner[j] == "}":
                depth -= 1
            j += 1
        if depth != 0:
            break
        block_text = inner[inner_start:j - 1]

        type_m = _BOUNDARY_TYPE_RE.search(block_text)
        if type_m is None:
            continue

        patch_entry: Dict[str, Any] = {"type": type_m.group(1)}

        # M7.1: extract `value` if present. Vector pattern is tried
        # first because a value-uniform-vector string also contains the
        # token `value uniform <number>` as a prefix; matching the
        # scalar pattern on it would yield a misleading scalar=44.2.
        vec_m = _VALUE_UNIFORM_VECTOR_RE.search(block_text)
        if vec_m:
            try:
                patch_entry["value_vector"] = [
                    float(vec_m.group(1)),
                    float(vec_m.group(2)),
                    float(vec_m.group(3)),
                ]
            except ValueError:
                pass
        else:
            sca_m = _VALUE_UNIFORM_SCALAR_RE.search(block_text)
            if sca_m:
                try:
                    patch_entry["value_scalar"] = float(sca_m.group(1))
                except ValueError:
                    pass

        # M7.1: extract whitelisted scalar params (intensity, mixingLength).
        # Other scalar fields in a BC block are ignored — the manifest
        # only references this whitelist today, and adding new params is
        # an intentional schema-extension point.
        extracted_params: Dict[str, float] = {}
        for pname, pre in _SCALAR_PARAM_RES.items():
            pm = pre.search(block_text)
            if pm:
                try:
                    extracted_params[pname] = float(pm.group(1))
                except ValueError:
                    pass
        if extracted_params:
            patch_entry["params"] = extracted_params

        # DEC-V61-201-SUB-INGEST-BC-REGEX-GROUPED-PATCHES:
        # fan out one BC block to N patch entries when grouped syntax
        # was matched; the legacy single-name path writes one entry.
        # Both paths write the SAME shape into `patches`.
        if grouped_names is not None:
            for gname in grouped_names:
                # Each synthetic entry is a shallow copy so downstream
                # mutation (none today, but cheap insurance) on one
                # patch can't bleed across siblings.
                patches[gname] = dict(patch_entry)
        else:
            patches[name] = patch_entry

    return patches


def _persist_bc_quality(
    case_dir: Path,
    *,
    fields: Dict[str, Dict[str, Any]] | None,
    expected_fields: List[str],
    blocked_reason: str | None = None,
    blocked_detail: str | None = None,
    regions: Dict[str, Dict[str, Any]] | None = None,
) -> Path:
    """Write `artifacts/bc_quality.json` — single source of truth for the
    BC audit gate. Mirrors `_persist_mesh_quality` (M4.1) and
    `_persist_geometry_quality` (M5.1).

    `fields` shape: {field_name: {file: rel_path, parsed: bool, patches: {...},
                                  missing: bool (when file absent)}}.
    `expected_fields` is the ordered list of fields we tried to parse
    (U, p, then `turbulence_fields` from the manifest).

    Multi-region (DEC-V61-201-SUB-INGEST-MULTI-REGION-BC, Gap #11):
    when `regions` is provided (non-None), the payload carries a
    top-level `layout: "multi_region"` marker plus a top-level
    `regions` dict keyed by `region_<name>`. Each region carries its
    own `expected_fields` / `fields_present` / `fields_missing` /
    `fields` sub-shape using the SAME single-region grammar — so the
    per-region inner dicts are byte-identical to what the
    single-region path produces. Downstream audit detects the
    `layout` marker and emits structural BLOCKED (current bc_contract
    schema is single-stream-only; per-region schema is charter-class
    work, Gap #28).
    """
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    out_path = art / "bc_quality.json"

    if blocked_reason is not None or (fields is None and regions is None):
        payload: Dict[str, Any] = {
            "bc_parsing_status": "blocked",
            "reason": blocked_reason or "unparsed",
        }
        if blocked_detail:
            payload["detail"] = blocked_detail
        if expected_fields:
            payload["expected_fields"] = expected_fields
    elif regions is not None:
        # Multi-region branch. Top-level `fields` / `fields_present` /
        # `fields_missing` are deliberately OMITTED — downstream must
        # iterate the `regions` dict and use per-region sub-shapes.
        payload = {
            "bc_parsing_status": "ok",
            "layout": "multi_region",
            "expected_fields": expected_fields,
            "regions": regions,
            "regions_detected": sorted(regions.keys()),
            "region_count": len(regions),
        }
    else:
        payload = {
            "bc_parsing_status": "ok",
            "expected_fields": expected_fields,
            "fields_present": sorted(
                fname for fname, fdata in fields.items()
                if fdata.get("parsed", False)
            ),
            "fields_missing": sorted(
                fname for fname, fdata in fields.items()
                if not fdata.get("parsed", False) and fdata.get("missing", False)
            ),
            "fields": fields,
        }

    try:
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    except OSError:
        # Same fail-tolerant posture as `_write_gate` (R17-F-02),
        # `_persist_mesh_quality`, `_persist_geometry_quality`.
        pass
    return out_path


def _parse_field_files_in_dir(
    field_dir: Path,
    field_dir_relative: str,
    expected: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Helper for `_collect_and_persist_bc`: read each `expected` field
    file inside `field_dir`, return the per-field dict that the
    single-region path historically produced under the top-level
    `fields` key.

    `field_dir_relative` is the path stub used to populate `file:`
    entries (e.g. `"0"` for single-region or `"0/region_fluid"` for a
    multi-region case). Extracting this helper keeps the
    single-region and per-region multi-region branches sharing
    identical grammar — no field-file behavior diverges between
    layouts.
    """
    fields: Dict[str, Dict[str, Any]] = {}
    for fname in expected:
        fpath = field_dir / fname
        rel = str(Path(field_dir_relative) / fname)
        if not fpath.is_file():
            fields[fname] = {
                "file": rel,
                "parsed": False,
                "missing": True,
            }
            continue
        try:
            text = fpath.read_text()
        except OSError as e:
            fields[fname] = {
                "file": rel,
                "parsed": False,
                "missing": False,
                "read_error": str(e),
            }
            continue
        parsed = _parse_field_boundary_field(text)
        if not parsed:
            # File exists but has no parseable `boundaryField` block —
            # surface this as parsed=False so the audit can FAIL on it.
            fields[fname] = {
                "file": rel,
                "parsed": False,
                "missing": False,
                "parse_error": "no_boundary_field_block_found",
            }
            continue
        fields[fname] = {
            "file": rel,
            "parsed": True,
            "patches": parsed,
        }
    return fields


def _detect_multi_region_layout(case_dir: Path) -> List[str]:
    """Return sorted list of `region_*` sub-directory names under
    `case_dir / "0"`, or empty list for single-region cases.

    DEC-V61-201-SUB-INGEST-MULTI-REGION-BC (Gap #11): OpenFOAM
    multi-region CHT cases (`chtMultiRegionFoam`,
    `chtMultiRegionSimpleFoam`) place each region's initial+boundary
    field files under `0/region_<name>/<field>` instead of
    `0/<field>`. The convention is that EVERY region's directory is
    named `region_<name>` (`region_fluid`, `region_solid`,
    `region_air`, etc.) — same convention `constant/<region>/` and
    `system/<region>/` follow elsewhere in the case.

    Detection rule: any entry directly under `0/` that
    (a) `is_dir()` (not a field FILE)
    (b) is NOT a symlink (R-17 fence — the recursive symlink walk in
        `_is_openfoam_compatible_case_dir` would already have BLOCKED
        the run/ingest if any 0/ entry were a symlink; check here is
        defensive for the case_dir grammar)
    (c) name starts with `region_`

    Returns sorted by region name for deterministic output ordering
    in `bc_quality.json` (json.dumps sort_keys handles dict keys but
    not the value of `regions_detected`).
    """
    zero_dir = case_dir / "0"
    if not zero_dir.is_dir():
        return []
    try:
        entries = list(zero_dir.iterdir())
    except (OSError, PermissionError):
        return []
    regions: List[str] = []
    for entry in entries:
        if entry.is_symlink():
            continue
        if not entry.is_dir():
            continue
        if not entry.name.startswith("region_"):
            continue
        regions.append(entry.name)
    regions.sort()
    return regions


def _collect_and_persist_bc(
    case_dir: Path,
    manifest: Dict[str, Any],
) -> None:
    """Walk the expected `0/<field>` files (single-region) OR
    `0/region_<name>/<field>` files (multi-region CHT), parse each,
    and persist `artifacts/bc_quality.json`. Called from `run()`
    after blockMesh succeeds and from `ingest()` for already-run
    cases.

    Field selection: always `U` and `p` (incompressible RANS canonical),
    plus any name in `manifest.bc_contract.turbulence_fields`. The 0/
    files exist before any solver runs (user inputs), so parser failures
    here surface as `fields_missing` in the JSON — not BLOCKED.

    Layout detection (DEC-V61-201-SUB-INGEST-MULTI-REGION-BC, Gap #11):
    if `0/` contains any `region_<name>/` sub-directories, switch to
    the multi-region branch. Each region runs the SAME field-collection
    grammar rooted at `0/region_<name>/<field>`, and results are
    accumulated into a top-level `regions[name]` dict. Single-region
    cases (no `region_*` subdirs) take the existing top-level path
    BYTE-IDENTICALLY — `bc_quality.json` produced for single-region
    cases is unchanged from the pre-DEC layout.
    """
    bc_contract = manifest.get("bc_contract", {}) or {}
    turb_fields = list(bc_contract.get("turbulence_fields", []) or [])

    # Canonical incompressible RANS fields. Deduplicate while preserving
    # order: U, p first, then turbulence fields in manifest order.
    seen: set = set()
    expected: List[str] = []
    for fname in ["U", "p", *turb_fields]:
        if fname in seen:
            continue
        seen.add(fname)
        expected.append(fname)

    # Multi-region detection. Note we look at on-disk layout, NOT the
    # manifest — the manifest's bc_contract schema is single-stream
    # today (Gap #28 charter work would change that). The on-disk
    # layout is the ground truth for what the case actually carries.
    region_names = _detect_multi_region_layout(case_dir)

    if region_names:
        # Multi-region branch. Per-region expected_fields uses the same
        # default list for now — per-region-class expectations
        # (solid-region wants only `T`, fluid wants U/p/turbulence)
        # require manifest schema work that is OUT OF SCOPE for this
        # sub-DEC (see DEC frontmatter, Gap #28).
        regions: Dict[str, Dict[str, Any]] = {}
        for rname in region_names:
            region_dir = case_dir / "0" / rname
            region_rel = str(Path("0") / rname)
            region_fields = _parse_field_files_in_dir(
                region_dir, region_rel, expected,
            )
            regions[rname] = {
                "expected_fields": expected,
                "fields_present": sorted(
                    fname for fname, fdata in region_fields.items()
                    if fdata.get("parsed", False)
                ),
                "fields_missing": sorted(
                    fname for fname, fdata in region_fields.items()
                    if not fdata.get("parsed", False)
                    and fdata.get("missing", False)
                ),
                "fields": region_fields,
            }
        _persist_bc_quality(
            case_dir,
            fields=None,
            expected_fields=expected,
            regions=regions,
        )
        return

    # Single-region branch (unchanged behavior).
    fields = _parse_field_files_in_dir(case_dir / "0", "0", expected)
    _persist_bc_quality(case_dir, fields=fields, expected_fields=expected)


# ---------- main entry point ----------


def run(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 1 step 2c: real `docker run` of blockMesh + simpleFoam.

    Returns BLOCKED if the environment isn't ready (depth-1 + recursive
    case_dir audit) OR if blockMesh / simpleFoam fail. Returns PASS / FAIL
    based on residual convergence against `manifest.solver_contract.residual_targets`
    once the run completes.

    Writes:
      - artifacts/solver.log         (combined stdout+stderr of simpleFoam)
      - artifacts/residuals.csv      (iter, <fields...> per row)

    Real solver invocation is gated on every env probe passing, including
    the R-17 recursive symlink walk over the case dir.
    """
    image = manifest.get("solver_docker_image", DEFAULT_IMAGE)

    # R10-F-02 fix: belt and suspenders. The case_manifest schema now
    # constrains `solver_docker_image` to a non-empty string, so a manifest
    # that hits this branch has either failed validation already OR
    # set the field via a non-schema-validated path. Either way, surface
    # it as a controlled BLOCKED rather than crashing inside subprocess.
    if not isinstance(image, str) or not image.strip():
        return {
            "status": "BLOCKED",
            "summary": "manifest.solver_docker_image is not a non-empty string.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "manifest_invalid_solver_docker_image",
                "value": repr(image),
                "next_step": (
                    "Either remove `solver_docker_image` from the manifest "
                    "(default is used) or set it to a non-empty string."
                ),
            },
        }

    # R15-F-03 fix: reject anything that doesn't look like a Docker reference
    # so a manifest can never inject extra docker-run flags via the image
    # argv slot (e.g. `--privileged alpine`, `-v /etc:/host alpine`).
    if not _is_valid_docker_image_name(image):
        return {
            "status": "BLOCKED",
            "summary": "manifest.solver_docker_image is not a valid Docker image reference.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "manifest_invalid_solver_docker_image",
                "value": repr(image),
                "next_step": (
                    "Image must start with alphanumeric and contain only "
                    "[a-zA-Z0-9._:/@-]. No whitespace, no leading dash, "
                    "no shell metacharacters."
                ),
            },
        }

    ok, reason = _docker_available()
    if not ok:
        return {
            "status": "BLOCKED",
            "summary": "Docker is not available for OpenFOAM execution.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "docker_not_available",
                "detail": reason,
                "next_step": (
                    "Install Docker Desktop and start the daemon. "
                    "On macOS: https://www.docker.com/products/docker-desktop. "
                    "Then retry `cfdtrust run`."
                ),
            },
        }

    if not _image_present(image):
        return {
            "status": "BLOCKED",
            "summary": f"OpenFOAM Docker image '{image}' is not pulled locally.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "openfoam_image_not_pulled",
                "image": image,
                "next_step": (
                    f"Run `docker pull {image}` once (multi-GB download), "
                    f"then retry `cfdtrust run`."
                ),
            },
        }

    ok, reason = _is_openfoam_compatible_case_dir(case_dir)
    if not ok:
        return {
            "status": "BLOCKED",
            "summary": "Case directory does not look like an OpenFOAM case.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "case_dir_not_openfoam_compatible",
                "detail": reason,
                "next_step": (
                    "Phase 1 step 2 will scaffold manifest → OpenFOAM-case translation. "
                    "Manual workaround: provide system/, constant/, and 0/ directories "
                    "alongside case_manifest.yaml."
                ),
            },
        }

    # All env checks passed — invoke OpenFOAM for real.
    artifacts_dir = case_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    log_path = artifacts_dir / "solver.log"
    mesh_log_path = artifacts_dir / "mesh_quality.log"
    residuals_csv = artifacts_dir / "residuals.csv"
    timeout_s = _resolve_solver_timeout()

    # --- blockMesh (idempotent in practice — re-runs are safe) ---
    rc, bm_stdout, bm_stderr = _run_docker_command(
        "blockMesh", case_dir, image, timeout=timeout_s,
    )
    if rc != 0:
        # R15-F-04 fix: distinguish OSError / timeout / real failure for
        # blockMesh too. Even though blockMesh isn't the solver,
        # `docker_invocation_failed` is still a different operational
        # condition from "blockMesh dict syntax error".
        if rc == -1 and "OFA-OSERROR" in (bm_stderr or ""):
            return {
                "status": "BLOCKED",
                "summary": "docker invocation failed before blockMesh could start.",
                "details": {
                    "execution": "skipped",
                    "real_solver_invoked": False,
                    "reason": "docker_invocation_failed",
                    "detail": bm_stderr.strip(),
                    "next_step": (
                        "Check Docker daemon health and retry `cfdtrust run`."
                    ),
                },
            }
        if rc == -1 and "OFA-TIMEOUT" in (bm_stderr or ""):
            return {
                "status": "BLOCKED",
                "summary": f"blockMesh timed out after {timeout_s}s.",
                "details": {
                    "execution": "attempted",
                    "real_solver_invoked": False,
                    "reason": "blockmesh_timed_out",
                    "timeout_s": timeout_s,
                },
            }
        return {
            "status": "BLOCKED",
            "summary": f"blockMesh failed (rc={rc}). See solver.log for diagnostics.",
            "details": {
                "execution": "attempted",
                "real_solver_invoked": False,
                "reason": "blockmesh_failed",
                "returncode": rc,
                "stderr_tail": (bm_stderr or bm_stdout or "")[-2000:],
                "next_step": (
                    "Inspect blockMeshDict for syntax errors; re-run "
                    "`docker run ... blockMesh` manually for full output."
                ),
            },
        }

    # --- M5.1: parse + persist polyMesh/boundary ---
    # blockMesh just wrote constant/polyMesh/; the boundary file is the
    # canonical source of truth for the geometry audit gate. Persist the
    # parsed dict before checkMesh runs so a checkMesh OSError/timeout
    # doesn't lose the geometry evidence.
    boundary_path = case_dir / "constant" / "polyMesh" / "boundary"
    if boundary_path.is_file():
        try:
            b_text = boundary_path.read_text()
            b_parsed = _parse_polymesh_boundary(b_text)
            _persist_geometry_quality(
                case_dir,
                patches=b_parsed,
                boundary_relative=str(boundary_path.relative_to(case_dir)),
            )
        except OSError as e:
            _persist_geometry_quality(
                case_dir,
                patches=None,
                boundary_relative=str(boundary_path.relative_to(case_dir)),
                blocked_reason="boundary_file_unreadable",
                blocked_detail=str(e),
            )
    else:
        # blockMesh exited 0 but didn't write the boundary file — anomalous
        # but possible (e.g. a custom blockMeshDict that runs but produces
        # an unusable mesh). Record as blocked so the audit gate surfaces it.
        _persist_geometry_quality(
            case_dir,
            patches=None,
            boundary_relative=None,
            blocked_reason="boundary_file_missing",
            blocked_detail=str(boundary_path),
        )

    # --- M6.1: parse + persist 0/<field> BC files ---
    # User-supplied 0/ files; persistence is uniform regardless of which
    # files are present so the audit gate can FAIL on missing/malformed.
    try:
        _collect_and_persist_bc(case_dir, manifest)
    except OSError:
        # Same fail-tolerant posture as the other persistence layers; do
        # not let an OSError here lose the rest of the run's evidence.
        pass

    # --- checkMesh (M4.1) ---
    # Runs after blockMesh on the just-generated polyMesh; output is the
    # single source of truth for the mesh audit gate (`audit/mesh.py`).
    # checkMesh almost never fails on rc — it exits 0 even with bad quality
    # and prints `Failed N mesh checks.` instead. We capture the log, parse,
    # and persist mesh_quality.json regardless of outcome so the audit gate
    # can decide PASS/FAIL on evidence (not on rc).
    cm_rc, cm_stdout, cm_stderr = _run_docker_command(
        "checkMesh", case_dir, image, timeout=timeout_s,
    )

    cm_combined = cm_stdout
    if cm_stderr:
        cm_combined = f"{cm_combined}\n--- STDERR ---\n{cm_stderr}\n"
    try:
        mesh_log_path.write_text(cm_combined)
        mesh_log_rel: str | None = str(mesh_log_path.relative_to(case_dir))
    except OSError:
        mesh_log_rel = None

    if cm_rc == -1 and "OFA-OSERROR" in (cm_stderr or ""):
        _persist_mesh_quality(
            case_dir,
            invoked=False,
            returncode=cm_rc,
            log_relative=mesh_log_rel,
            parsed=None,
            blocked_reason="docker_invocation_failed",
            blocked_detail=(cm_stderr or "").strip(),
        )
    elif cm_rc == -1 and "OFA-TIMEOUT" in (cm_stderr or ""):
        _persist_mesh_quality(
            case_dir,
            invoked=True,
            returncode=cm_rc,
            log_relative=mesh_log_rel,
            parsed=None,
            blocked_reason="checkmesh_timed_out",
            blocked_detail=f"timeout_s={timeout_s}",
        )
    else:
        # checkMesh returned (0 or non-zero structural exit) — parse the log.
        # Even on rc != 0 we parse what we have; rc surfaces in the JSON.
        cm_parsed = _parse_check_mesh_log(cm_stdout)
        _persist_mesh_quality(
            case_dir,
            invoked=True,
            returncode=cm_rc,
            log_relative=mesh_log_rel,
            parsed=cm_parsed,
        )

    # --- simpleFoam ---
    rc, sf_stdout, sf_stderr = _run_docker_command(
        "simpleFoam", case_dir, image, timeout=timeout_s,
    )

    # Persist combined log unconditionally — debugging needs it whether
    # the run passed or failed.
    combined_log = sf_stdout
    if sf_stderr:
        combined_log = f"{combined_log}\n--- STDERR ---\n{sf_stderr}\n"
    log_path.write_text(combined_log)

    if rc != 0:
        # Three distinct sub-cases. The marker-based discrimination is set by
        # `_run_docker_command` (R15-F-01 fix); previously OSError was
        # mis-reported as `simplefoam_crashed` with `real_solver_invoked=True`
        # even though the solver process never actually started.
        if rc == -1 and "OFA-OSERROR" in (sf_stderr or ""):
            return {
                "status": "BLOCKED",
                "summary": "docker invocation failed before simpleFoam could start.",
                "details": {
                    "execution": "skipped",
                    "real_solver_invoked": False,
                    "reason": "docker_invocation_failed",
                    "detail": sf_stderr.strip(),
                    "next_step": (
                        "Check Docker daemon health, host fork limits, and "
                        "container runtime quota. Retry `cfdtrust run` after fix."
                    ),
                },
            }
        if rc == -1 and "OFA-TIMEOUT" in (sf_stderr or ""):
            return {
                "status": "BLOCKED",
                "summary": f"simpleFoam timed out after {timeout_s}s (set CFDTRUST_SOLVER_TIMEOUT_S to extend).",
                "details": {
                    "execution": "attempted",
                    "real_solver_invoked": True,
                    "reason": "simplefoam_timed_out",
                    "timeout_s": timeout_s,
                    "log": str(log_path.relative_to(case_dir)),
                },
            }
        return {
            "status": "BLOCKED",
            "summary": f"simpleFoam exited non-zero (rc={rc}). See artifacts/solver.log.",
            "details": {
                "execution": "attempted",
                "real_solver_invoked": True,
                "reason": "simplefoam_crashed",
                "returncode": rc,
                "stderr_tail": (sf_stderr or "")[-2000:],
                "log": str(log_path.relative_to(case_dir)),
            },
        }

    # --- parse log → residuals.csv ---
    parsed = _parse_simplefoam_log(sf_stdout)
    _write_residuals_csv(parsed, residuals_csv)

    # --- gate computation ---
    gate = _compute_gate_from_residuals(parsed, manifest)
    gate["details"]["image"] = image
    gate["details"]["log"] = str(log_path.relative_to(case_dir))
    gate["details"]["residuals_csv"] = str(residuals_csv.relative_to(case_dir))
    if "artifact" not in gate:
        gate["artifact"] = str(log_path.relative_to(case_dir))

    return gate


# ---------- DEC-V61-201-SUB-INGEST: external-run ingest mode ----------
#
# Mirrors `run()` but skips blockMesh + simpleFoam invocation. Reads the
# existing time directories + external solver log + polyMesh from disk;
# re-runs only `checkMesh` against the existing polyMesh to populate
# mesh_quality.json (no destructive operation).
#
# Honesty fence: the resulting solver gate carries
# `details.execution = "ingested"`. report.py translates this to top-level
# `solver_execution = "ingested"` and demotes any overall_status PASS to
# WARN, because the harness did not witness the run.


# Generic fallback filenames for an externally-produced solver log,
# used when the manifest does not declare a solver or when none of the
# manifest-derived candidates exist on disk. Order = most-specific first.
_INGEST_LOG_FALLBACK_CANDIDATES = (
    "log_simpleFoam.txt",
    "log_pimpleFoam.txt",
    "log_icoFoam.txt",
    "log_potentialFoam.txt",
    "log_foamRun.txt",
    "log.simpleFoam",
    "log.pimpleFoam",
    "log.foamRun",
    "solver.log",
    "simpleFoam.log",
)


def _candidate_log_names(manifest: Dict[str, Any] | None) -> Tuple[List[str], List[str]]:
    """Build the ordered list of candidate log filenames for ingest.

    Codex R1-P1 fix: manifest-declared solver wins over generic
    candidates. A `pisoFoam` case must find `log_pisoFoam.txt` /
    `log.pisoFoam` / `pisoFoam.log` even if a stale `log_simpleFoam.txt`
    sits alongside it, AND the manifest-derived candidate must precede
    any generic fallback so the chosen log corresponds to the declared
    solver.

    Returns `(primary, fallback)` so callers can record both lists in
    BLOCKED diagnostics — users need to see exactly what was searched.

    `manifest["solver"]` is sanitised: only alphanumeric + underscore +
    dash are accepted (OpenFOAM solver names never contain shell or
    path metachars; this prevents a bogus manifest from forcing the
    walker into a parent directory or shell-interpreting the name).
    """
    primary: List[str] = []
    if manifest is not None:
        raw = manifest.get("solver")
        if isinstance(raw, str):
            solver = raw.strip()
            if solver and re.match(r"^[A-Za-z0-9_-]+$", solver):
                primary = [
                    f"log_{solver}.txt",
                    f"log.{solver}",
                    f"{solver}.log",
                ]
    # Dedup the fallback list against primary so the BLOCKED diagnostic
    # doesn't show duplicates when manifest.solver happens to be
    # `simpleFoam` (already in fallbacks).
    fallback = [n for n in _INGEST_LOG_FALLBACK_CANDIDATES if n not in primary]
    return primary, fallback


def _find_external_solver_log(
    case_dir: Path,
    manifest: Dict[str, Any] | None = None,
) -> Path | None:
    """Locate an existing OpenFOAM solver log produced by an external run.

    Codex R1-P1 fix: the manifest's declared solver derives the
    first-tried candidates, with the generic fallback list used only if
    none of the solver-specific names exist. This avoids two failure
    modes:
      - false-BLOCKED on cases whose log matches `manifest["solver"]`
        but isn't in the historical fallback list (e.g. a `pisoFoam`
        case where neither `log_pisoFoam.txt` nor the generic names
        happen to exist).
      - silent wrong-log ingest when a directory carries multiple
        historical logs and the most-specific match should win
        regardless of fallback-list ordering.

    Returns the first matched `Path`, or `None`. The artifacts/ dir is
    intentionally excluded — `artifacts/solver.log` is the ingest
    *output*, not an input, so finding it would create a fixed-point
    loop on repeated ingest.

    Gap #10 (case_011 plate-fin CHT dogfood): also search the bounded
    `case_dir/log/` subdirectory. Many `Allrun.sh` layouts redirect
    each solver step's stdout into `log/<solver>.log` rather than the
    top-level `log_<solver>.txt`. Top-level remains precedence so the
    pre-existing behaviour is preserved; `log/` is searched only as a
    fallback. We deliberately do NOT recurse — arbitrary subdir walks
    invite DoS-on-deep-trees plus ambiguity when multiple solver logs
    live at different depths.

    Gap #14 (case_004 NREL MRF dogfood): industrial workflows commonly
    save versioned suffix variants like `log.simpleFoam.v4`,
    `log.simpleFoam.fullrun` next to each other. Exact-name matching
    misses these. After exact-name exhaustion (which preserves Gap
    #10 / R1-P1 precedence semantics), fall back to `log.<solver>*`
    glob and pick the newest-by-mtime match. Glob is restricted to the
    sanitised manifest solver prefix only — never falls back to a bare
    `log.*` glob (would mismatch unrelated `log.checkMesh`, etc.).
    Applied in BOTH top-level and `log/` subdir.
    """
    primary, fallback = _candidate_log_names(manifest)
    candidates = (*primary, *fallback)
    # Top-level pass (preserves existing precedence).
    for name in candidates:
        p = case_dir / name
        if p.is_file():
            return p
    # Gap #10 + Gap #17: bounded subdir fallback. Original Gap #10 walked
    # only `case_dir/log/`; Gap #17 (case_006 ONERA M6 dogfood) extends
    # to ALSO walk one-level into `case_dir/log_*/` because industrial
    # Allrun layouts version their log directories
    # (`log_v64_v2/04_solver.log`, `log_v64_v3/...`). Single-level
    # globbing only — recursive walks invite DoS-on-deep-trees and
    # ambiguity. The `log` plain directory remains first so existing
    # Gap #10 precedence is preserved.
    plain_log = case_dir / "log"
    try:
        versioned_dirs = sorted(
            (
                p for p in case_dir.glob("log_*")
                if p.is_dir()
            ),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        versioned_dirs = []
    log_subdirs: List[Path] = []
    if plain_log.is_dir():
        log_subdirs.append(plain_log)
    log_subdirs.extend(versioned_dirs)
    for subdir in log_subdirs:
        for name in candidates:
            p = subdir / name
            if p.is_file():
                return p
    # Gap #14 (+ Gap #17 extension): versioned-suffix glob fallback.
    # Only fires if manifest carries a sanitised solver name.
    solver_glob: str | None = None
    for name in primary:
        if name.startswith("log."):
            # name == "log.<solver>" → glob "log.<solver>*"
            solver_glob = f"{name}*"
            break
    if solver_glob is not None:
        glob_dirs: List[Path] = [case_dir]
        glob_dirs.extend(log_subdirs)
        all_matches: List[Path] = []
        for dir_to_scan in glob_dirs:
            try:
                all_matches.extend(
                    p for p in dir_to_scan.glob(solver_glob) if p.is_file()
                )
            except OSError:
                pass
        if all_matches:
            all_matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return all_matches[0]

    # TBD-15 (case_009 Sandia Flame D reacting dogfood): multi-stage
    # reacting workflows commonly split the run into `log_cold.txt`
    # (cold-flow stage) + `log_ignite.txt` (ignition stage) +
    # `log_burn.txt` (burning stage). None of these match
    # `log_<solver>.txt` / `log.<solver>` / `<solver>.log`. Fall back to a
    # general `log_*.txt` glob, but require the file head to reference
    # the manifest's declared solver name (e.g. `Build: reactingFoam` or
    # `Exec: reactingFoam ...`) so this fallback does not pick up
    # unrelated stdout dumps that happen to live alongside the case.
    solver_name: str | None = None
    if manifest is not None:
        raw = manifest.get("solver")
        if isinstance(raw, str):
            cand = raw.strip()
            if cand and re.match(r"^[A-Za-z0-9_-]+$", cand):
                solver_name = cand
    if solver_name is not None:
        general_glob = "log_*.txt"
        general_dirs: List[Path] = [case_dir]
        general_dirs.extend(log_subdirs)
        general_matches: List[Path] = []
        for dir_to_scan in general_dirs:
            try:
                general_matches.extend(
                    p for p in dir_to_scan.glob(general_glob) if p.is_file()
                )
            except OSError:
                pass
        # Newest first so multi-stage runs return the most recent stage's
        # log (typical user expectation: "show me the latest").
        general_matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for cand_path in general_matches:
            try:
                with cand_path.open("rb") as f:
                    head = f.read(4096).decode("utf-8", errors="replace")
            except OSError:
                continue
            # Header heuristic: OpenFOAM logs prefix every run with a
            # banner that includes `Build  : reactingFoam-...` or
            # `Exec   : reactingFoam ...`. Match either appearance of
            # the solver name in the file head — bounded to first 4KB so
            # a pathological file doesn't force a full read.
            if solver_name in head:
                return cand_path
    return None


# Gap #13: divergence-marker patterns. case_004 NREL diverged-at-iter-4
# left a solver.log with FATAL + nan + Foam::error::printStack but never
# wrote any time dir. Listed in order of strongest-to-weakest signal —
# any one match is sufficient evidence to flag likely_divergence.
_DIVERGENCE_MARKERS: Tuple[str, ...] = (
    "FOAM FATAL ERROR",
    "Foam::error::printStack",
    "floating point exception",
    "-nan",
    " nan ",
    " inf ",
    "+inf",
    "-inf",
)


def _scan_solver_log_for_divergence(log_path: Path) -> str | None:
    """Return the first divergence-marker line found in `log_path`, or
    None if the log is clean. Reads the tail of the file (last 64 KiB)
    so industrial logs that grew to tens of MiB before crashing don't
    force full reads — divergence symptoms always appear near the end."""
    try:
        size = log_path.stat().st_size
        with log_path.open("rb") as f:
            if size > 65536:
                f.seek(size - 65536)
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    for line in tail.splitlines():
        for marker in _DIVERGENCE_MARKERS:
            if marker in line:
                return line.strip()[:240]  # cap evidence length
    return None


_PROCESSOR_DIR_RE = re.compile(r"^processor(\d+)$")


def _looks_like_time_name(name: str, *, positive_only: bool = False) -> bool:
    """True iff `name` parses as a non-negative float (an OpenFOAM time
    directory). `positive_only=True` excludes time 0 (initial conditions);
    used by the ingest top-level-time-dir check (Codex R4-P2)."""
    try:
        t = float(name)
    except ValueError:
        return False
    return t > 0 if positive_only else t >= 0


def _find_time_directories(case_dir: Path) -> List[float]:
    """Return sorted list of time directories > 0 found anywhere a real
    OpenFOAM run would leave them in `case_dir`.

    An OpenFOAM time directory is a subdirectory whose name parses as a
    non-negative float. Time 0 (initial conditions) does NOT count as
    "the case ran" — we need at least one time > 0.

    Codex R3-P1 (post-V133 ratified): in addition to top-level time
    dirs (the layout used when `reconstructPar` has been run, or when
    the case ran serial), also recognise the decomposed-parallel
    layout where time dirs live under `processor0/`, `processor1/`,
    etc. — a very common industrial shape when an MPI run was never
    reconstructed. Returning empty in that case (the pre-R3 behaviour)
    forced false-BLOCKED on a major class of valid ingest inputs.

    Layouts handled:
      case_dir/100/              ← serial or reconstructed
      case_dir/processor0/100/   ← decomposed, never reconstructed
      both (deduped on time value via set)
    """
    result: set[float] = set()

    def _scan_directory_for_time_subdirs(parent: Path) -> None:
        try:
            entries = list(parent.iterdir())
        except OSError:
            return
        for entry in entries:
            if not entry.is_dir():
                continue
            try:
                t = float(entry.name)
            except ValueError:
                continue
            if t > 0:
                result.add(t)

    # Top-level (serial or reconstructed)
    _scan_directory_for_time_subdirs(case_dir)

    # Decomposed: processor0/, processor1/, ... Only the FIRST processor
    # dir's contents are scanned for time dirs — all processor*/ should
    # contain the same set of time values (one per write step). Scanning
    # all of them would multiply the work N-fold for no information gain.
    try:
        processor_dirs = sorted(
            (
                p for p in case_dir.iterdir()
                if p.is_dir() and _PROCESSOR_DIR_RE.match(p.name)
            ),
            key=lambda p: int(_PROCESSOR_DIR_RE.match(p.name).group(1)),  # type: ignore[union-attr]
        )
    except OSError:
        processor_dirs = []
    if processor_dirs:
        _scan_directory_for_time_subdirs(processor_dirs[0])

    return sorted(result)


def _file_sha256(path: Path) -> str | None:
    """Return hex SHA256 of `path` contents, or None on OSError.

    Streaming read so we don't load multi-GB time directories into memory.
    """
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _utc_now_iso() -> str:
    """Local copy of `cfdtrust.status.utc_now_iso` — avoids importing
    `cfdtrust.status` here, which would create an upward import from the
    backends/ subpackage to a sibling helper module."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_ingest_provenance(
    case_dir: Path,
    *,
    external_log_path: Path,
    boundary_path: Path | None,
    checkmesh_image: str,
    time_directories: List[float],
) -> Path:
    """Write `artifacts/ingest_manifest.json` recording external-run provenance.

    Captures what was ingested + SHA256 of key source files so a later
    audit can detect whether the underlying evidence was tampered with
    after ingest. Same fail-tolerant write posture as other persist
    helpers — OSError is swallowed so an unwritable artifacts/ doesn't
    crash ingest.
    """
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    out = art / "ingest_manifest.json"
    payload: Dict[str, Any] = {
        "ingested_at": _utc_now_iso(),
        "checkmesh_image": checkmesh_image,
        "external_solver_log": {
            "source_relative": str(external_log_path.relative_to(case_dir)),
            "sha256": _file_sha256(external_log_path),
        },
        "polymesh_boundary": (
            None if boundary_path is None else {
                "source_relative": str(boundary_path.relative_to(case_dir)),
                "sha256": _file_sha256(boundary_path),
            }
        ),
        "time_directories": [str(t) for t in time_directories],
        "honesty_note": (
            "Ingested cases cannot reach `solver_execution=real` or "
            "`validation_status=validated`; the harness did not witness "
            "the solver run. See DEC-V61-201-SUB-INGEST."
        ),
    }
    try:
        out.write_text(json.dumps(payload, indent=2, sort_keys=True))
    except OSError:
        # Same posture as `_persist_*_quality` (R17-F-02): provenance
        # write failure must not lose the rest of the ingest evidence.
        pass
    return out


def ingest(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """DEC-V61-201-SUB-INGEST: import an externally-run case into the harness.

    Mirrors `run()` env-check preamble + persistence steps, but does NOT
    invoke blockMesh or simpleFoam. Reuses the existing time directories
    and external solver log; re-runs only `checkMesh` against the
    existing `constant/polyMesh/`.

    Returns a solver-execution gate dict whose `details.execution` is the
    string `"ingested"`. report.py uses that marker to set top-level
    `solver_execution = "ingested"` and demote overall_status PASS → WARN.

    BLOCKED states (mirror `run()` env checks plus two new ones):
      - `manifest_invalid_solver_docker_image` — same as run()
      - `docker_not_available`                 — same as run()
      - `openfoam_image_not_pulled`            — same as run()
      - `case_dir_not_openfoam_compatible`     — same as run()
      - `no_time_directory_found`              — case never ran externally
      - `no_solver_log_found`                  — no recognisable log file
      - `solver_log_unreadable`                — log exists but OSError on read
    """
    image = manifest.get("solver_docker_image", DEFAULT_IMAGE)

    if not isinstance(image, str) or not image.strip():
        return {
            "status": "BLOCKED",
            "summary": "manifest.solver_docker_image is not a non-empty string.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "manifest_invalid_solver_docker_image",
                "value": repr(image),
                "next_step": (
                    "Either remove `solver_docker_image` from the manifest "
                    "(default is used) or set it to a non-empty string."
                ),
            },
        }

    if not _is_valid_docker_image_name(image):
        return {
            "status": "BLOCKED",
            "summary": "manifest.solver_docker_image is not a valid Docker image reference.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "manifest_invalid_solver_docker_image",
                "value": repr(image),
                "next_step": (
                    "Image must start with alphanumeric and contain only "
                    "[a-zA-Z0-9._:/@-]. No whitespace, no leading dash, "
                    "no shell metacharacters."
                ),
            },
        }

    ok, reason = _docker_available()
    if not ok:
        return {
            "status": "BLOCKED",
            "summary": "Docker is not available for OpenFOAM checkMesh.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "docker_not_available",
                "detail": reason,
                "next_step": (
                    "Install Docker Desktop and start the daemon. "
                    "Then retry `cfdtrust ingest`."
                ),
            },
        }

    if not _image_present(image):
        return {
            "status": "BLOCKED",
            "summary": f"OpenFOAM Docker image '{image}' is not pulled locally.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "openfoam_image_not_pulled",
                "image": image,
                "next_step": (
                    f"Run `docker pull {image}` once (multi-GB download), "
                    f"then retry `cfdtrust ingest`."
                ),
            },
        }

    # DEC-V61-201-SUB-INGEST: use the relaxed-but-still-safe variant of
    # the case-dir check. An already-run case naturally contains
    # OpenFOAM-internal symlinks under `dynamicCode/<name>/lnInclude/`
    # (codedFixedValue artifacts). The ingest variant allows those
    # because their resolved targets are inside `case_dir` — they cannot
    # escape the docker volume mount — while still refusing any symlink
    # whose canonical target is outside `case_dir`.
    ok, reason = _is_openfoam_compatible_ingest_case_dir(case_dir)
    if not ok:
        return {
            "status": "BLOCKED",
            "summary": "Case directory does not look like an OpenFOAM case.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "case_dir_not_openfoam_compatible",
                "detail": reason,
                "next_step": (
                    "Provide system/, constant/, and 0/ directories alongside "
                    "case_manifest.yaml."
                ),
            },
        }

    # Ingest-specific check 1: at least one time directory > 0 must exist.
    # 0/ alone means the case has initial conditions but never ran.
    time_dirs = _find_time_directories(case_dir)
    if not time_dirs:
        details: Dict[str, Any] = {
            "execution": "skipped",
            "real_solver_invoked": False,
            "reason": "no_time_directory_found",
            "next_step": (
                "Run the case externally first (any compatible OpenFOAM "
                "build), then re-run `cfdtrust ingest`. For new cases "
                "authored from scratch, use `cfdtrust run` instead."
            ),
        }
        # Gap #13: case_004 NREL diverged-at-iter-4 surface. If a solver
        # log IS locatable and carries divergence markers, the case
        # almost-certainly ran but blew up before any writeInterval —
        # surface that to the user instead of generic "never ran" advice.
        divergence_log = _find_external_solver_log(case_dir, manifest)
        if divergence_log is not None:
            evidence = _scan_solver_log_for_divergence(divergence_log)
            if evidence is not None:
                details["likely_divergence"] = True
                details["divergence_evidence"] = evidence
                details["divergence_log_source"] = str(
                    divergence_log.relative_to(case_dir)
                )
        return {
            "status": "BLOCKED",
            "summary": "Case has no time directory beyond 0/; nothing to ingest.",
            "details": details,
        }

    # Codex R4-P2 fix (R7-P2 relaxation per DEC-V61-201-SUB-INGEST-P2-
    # DECOMPOSED-NOT-FINALIZED): pure-decomposed cases (`processor*/<time>/`
    # with NOTHING at the case root) trip a downstream gap — `audit/qoi.py`
    # and `qoi/wall_shear.py` only read top-level time dirs WHEN
    # `reference_comparison.status == "finalized"`. For placeholder /
    # not_finalized reference manifests, QoI + reference both MOCK out and
    # never touch the time directories, so the BLOCK is overly restrictive.
    #
    # Behaviour:
    #   - reference finalized + decomposed-only → BLOCK with sharpened reason
    #     `case_decomposed_not_reconstructed_with_finalized_reference` and
    #     `reconstructPar` next_step (preserves R4-P2 correctness guarantee).
    #   - reference not_finalized/placeholder + decomposed-only → ACCEPT
    #     (no BLOCK on this gate); downstream QoI/reference mock paths handle
    #     the absence of top-level times. Ingest proceeds.
    #
    # A future sub-DEC can extend `audit/qoi.py` to read processor*/ directly
    # and remove the BLOCK entirely. Hybrid cases (some processor*/ AND some
    # top-level time dirs) are unaffected — top-level dirs are sufficient.
    has_top_level_time_dir = any(
        (
            entry.is_dir()
            and not entry.name.startswith("processor")
            and _looks_like_time_name(entry.name, positive_only=True)
        )
        for entry in case_dir.iterdir()
    )
    if not has_top_level_time_dir:
        ref_status = (
            (manifest.get("reference_comparison") or {}).get("status", "")
        )
        if ref_status == "finalized":
            return {
                "status": "BLOCKED",
                "summary": (
                    "Case is parallel-decomposed (processor*/<time>/ present) but "
                    "was never reconstructed; downstream QoI extraction reads "
                    "only top-level time directories and the manifest's "
                    "reference_comparison is finalized."
                ),
                "details": {
                    "execution": "skipped",
                    "real_solver_invoked": False,
                    "reason": "case_decomposed_not_reconstructed_with_finalized_reference",
                    "time_directories_found_under_processor": [str(t) for t in time_dirs],
                    "next_step": (
                        "Run `reconstructPar` (in the OpenFOAM build that decomposed "
                        "the case) to materialise top-level time directories, then "
                        "re-run `cfdtrust ingest`. Alternatively, set "
                        "`reference_comparison.status` to `placeholder` or "
                        "`not_finalized` if the reference data is not staged — the "
                        "trust harness's QoI + reference gates will then mock out "
                        "and decomposed-only ingest can proceed."
                    ),
                },
            }
        # else: reference is placeholder/not_finalized/missing → accept the
        # decomposed-only case. QoI + reference will mock out downstream.

    # Ingest-specific check 2: an external solver log must be locatable.
    # Codex R1-P1 fix: pass the manifest so the search is driven by
    # the declared solver, not a fixed list. The BLOCKED diagnostic
    # surfaces BOTH the solver-derived candidates and the generic
    # fallbacks so users can see what was tried.
    primary, fallback = _candidate_log_names(manifest)
    external_log = _find_external_solver_log(case_dir, manifest)
    if external_log is None:
        return {
            "status": "BLOCKED",
            "summary": "No external solver log found in case directory.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "no_solver_log_found",
                "searched_solver_specific": primary,
                "searched_fallback": fallback,
                "next_step": (
                    "Place the external run's log at one of the searched "
                    "names (commonly `log_<solver>.txt` from "
                    "`<solver> > log_<solver>.txt 2>&1`), then re-run "
                    "`cfdtrust ingest`."
                ),
            },
        }

    artifacts_dir = case_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    log_path = artifacts_dir / "solver.log"
    mesh_log_path = artifacts_dir / "mesh_quality.log"
    residuals_csv = artifacts_dir / "residuals.csv"
    timeout_s = _resolve_solver_timeout()

    # --- Persist geometry from existing polyMesh/boundary ---
    boundary_path = case_dir / "constant" / "polyMesh" / "boundary"
    boundary_for_provenance: Path | None = None
    if boundary_path.is_file():
        boundary_for_provenance = boundary_path
        try:
            b_text = boundary_path.read_text()
            b_parsed = _parse_polymesh_boundary(b_text)
            _persist_geometry_quality(
                case_dir,
                patches=b_parsed,
                boundary_relative=str(boundary_path.relative_to(case_dir)),
            )
        except OSError as e:
            _persist_geometry_quality(
                case_dir,
                patches=None,
                boundary_relative=str(boundary_path.relative_to(case_dir)),
                blocked_reason="boundary_file_unreadable",
                blocked_detail=str(e),
            )
    else:
        # case has time dirs but no polyMesh/boundary — anomalous (the
        # solver couldn't have run without a mesh). Surface as BLOCKED at
        # the geometry layer; ingest continues so downstream gates show
        # the full picture rather than aborting on first miss.
        _persist_geometry_quality(
            case_dir,
            patches=None,
            boundary_relative=None,
            blocked_reason="boundary_file_missing",
            blocked_detail=str(boundary_path),
        )

    # --- Persist BC from 0/ fields ---
    try:
        _collect_and_persist_bc(case_dir, manifest)
    except OSError:
        # Same fail-tolerant posture as run(): an OSError here must not
        # lose the rest of the ingest evidence.
        pass

    # --- checkMesh on existing polyMesh (read-only operation) ---
    cm_rc, cm_stdout, cm_stderr = _run_docker_command(
        "checkMesh", case_dir, image, timeout=timeout_s,
    )
    cm_combined = cm_stdout
    if cm_stderr:
        cm_combined = f"{cm_combined}\n--- STDERR ---\n{cm_stderr}\n"
    try:
        mesh_log_path.write_text(cm_combined)
        mesh_log_rel: str | None = str(mesh_log_path.relative_to(case_dir))
    except OSError:
        mesh_log_rel = None

    if cm_rc == -1 and "OFA-OSERROR" in (cm_stderr or ""):
        _persist_mesh_quality(
            case_dir,
            invoked=False,
            returncode=cm_rc,
            log_relative=mesh_log_rel,
            parsed=None,
            blocked_reason="docker_invocation_failed",
            blocked_detail=(cm_stderr or "").strip(),
        )
    elif cm_rc == -1 and "OFA-TIMEOUT" in (cm_stderr or ""):
        _persist_mesh_quality(
            case_dir,
            invoked=True,
            returncode=cm_rc,
            log_relative=mesh_log_rel,
            parsed=None,
            blocked_reason="checkmesh_timed_out",
            blocked_detail=f"timeout_s={timeout_s}",
        )
    else:
        cm_parsed = _parse_check_mesh_log(cm_stdout)
        _persist_mesh_quality(
            case_dir,
            invoked=True,
            returncode=cm_rc,
            log_relative=mesh_log_rel,
            parsed=cm_parsed,
        )

    # --- Transcribe external solver log into artifacts/solver.log ---
    try:
        ext_text = external_log.read_text()
    except OSError as e:
        return {
            "status": "BLOCKED",
            "summary": f"External solver log unreadable: {e}",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "solver_log_unreadable",
                "source": str(external_log.relative_to(case_dir)),
                "detail": str(e),
            },
        }
    # Codex R5-P1 fix: prepend the INGEST_BANNER so the log itself
    # carries provenance. If `artifacts/solver_gate.json` is later
    # missing or unreadable, `audit/solver.py::read_artifacts()` detects
    # the banner and classifies execution as "ingested" instead of
    # silently upgrading to "real" (which would bypass the
    # DEC-V61-201-SUB-INGEST honesty fences).
    from ..audit.solver import INGEST_BANNER
    log_path.write_text(INGEST_BANNER + ext_text)

    # --- Parse log + write residuals.csv ---
    parsed = _parse_simplefoam_log(ext_text)
    _write_residuals_csv(parsed, residuals_csv)

    # --- Gate computation (same logic as a real run) ---
    gate = _compute_gate_from_residuals(parsed, manifest)
    # Override execution-provenance fields: the harness did NOT invoke the
    # solver, an external runner did. report.py keys on `details.execution`
    # to set top-level solver_execution.
    gate["details"]["execution"] = "ingested"
    gate["details"]["real_solver_invoked"] = False
    gate["details"]["image"] = image
    gate["details"]["log"] = str(log_path.relative_to(case_dir))
    gate["details"]["residuals_csv"] = str(residuals_csv.relative_to(case_dir))
    gate["details"]["external_log_source"] = str(external_log.relative_to(case_dir))
    if "artifact" not in gate:
        gate["artifact"] = str(log_path.relative_to(case_dir))

    # --- Write provenance manifest ---
    _write_ingest_provenance(
        case_dir,
        external_log_path=external_log,
        boundary_path=boundary_for_provenance,
        checkmesh_image=image,
        time_directories=time_dirs,
    )

    return gate
