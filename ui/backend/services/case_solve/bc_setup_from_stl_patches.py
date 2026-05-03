"""DEC-V61-103 Phase 1 · BC dict authoring driven by named polyMesh patches.

The legacy ``setup_ldc_bc`` and ``setup_channel_bc`` paths each assume
a fixed patch topology baked into the executor. Imported CAD geometries
that have proper named patches in ``polyMesh/boundary`` (after the
DEC-V61-102 defect-2a fix preserves them) need a 3rd executor that:

1. Reads the patch list from ``constant/polyMesh/boundary``
2. Maps each patch name to a default BC class via a project-level table
3. Authors 7 OpenFOAM-10 dicts referencing the actual patch names
4. Wraps the multi-file write in V61-102's ``_atomic_commit_dicts`` so
   the user-override invariant + 2-phase commit semantics apply

Engineers can fine-tune any field via the V61-102 raw-dict editor
post-author; this executor only sets sane defaults.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np

from ui.backend.services.case_manifest import (
    CaseLockError,
    case_lock,
    is_user_override,
    mark_ai_authored,
)
from ui.backend.services.render.polymesh_parser import (
    parse_faces,
    parse_points,
)

from .bc_setup import _atomic_commit_dicts


class BCClass(str, Enum):
    """BC archetype that determines the (U, p) field templates emitted
    for a given patch. Engineers pick the archetype via patch name; the
    raw-dict editor handles overrides for the long tail of cases this
    table doesn't cover.
    """

    VELOCITY_INLET = "velocity_inlet"
    PRESSURE_OUTLET = "pressure_outlet"
    NO_SLIP_WALL = "no_slip_wall"
    SYMMETRY = "symmetry"


# Default mapping by patch name (case-insensitive). The fallback for
# unrecognized names is NO_SLIP_WALL with a warning (the engineer can
# override via raw-dict editor).
_DEFAULT_PATCH_CLASS: dict[str, BCClass] = {
    "inlet": BCClass.VELOCITY_INLET,
    "in": BCClass.VELOCITY_INLET,
    "outlet": BCClass.PRESSURE_OUTLET,
    "out": BCClass.PRESSURE_OUTLET,
    "wall": BCClass.NO_SLIP_WALL,
    "walls": BCClass.NO_SLIP_WALL,
    "symmetry": BCClass.SYMMETRY,
    "sym": BCClass.SYMMETRY,
    "top": BCClass.NO_SLIP_WALL,
    "bottom": BCClass.NO_SLIP_WALL,
    "front": BCClass.NO_SLIP_WALL,
    "back": BCClass.NO_SLIP_WALL,
    "left": BCClass.NO_SLIP_WALL,
    "right": BCClass.NO_SLIP_WALL,
    "fixedwalls": BCClass.NO_SLIP_WALL,
    "blade": BCClass.NO_SLIP_WALL,
    "obstacle": BCClass.NO_SLIP_WALL,
}


# Inlet velocity magnitude (m/s) used when no override is present.
# Default 0.5 m/s; the direction is computed per-patch from face
# normals (defect-6 fix: rotated geometries used to have flow ram
# into walls because the direction was hardcoded to global +x).
_DEFAULT_INLET_SPEED: float = 0.5
_DEFAULT_NU: float = 1.0e-3
# icoFoam timestep + endTime defaults. Conservative — engineer can
# tune via raw-dict editor (system/controlDict).
_DEFAULT_DELTA_T: float = 0.01
_DEFAULT_END_TIME: float = 5.0


class StlPatchBCError(RuntimeError):
    """Raised when stl-patch-driven BC setup can't proceed.

    ``failing_check`` is one of:

    * ``mesh_not_setup`` — ``constant/polyMesh/boundary`` missing
    * ``no_named_patches`` — boundary file exists but has no patches
      (or only the legacy single-patch ``patch0``); caller should fall
      through to the LDC executor instead
    * ``write_failed`` — atomic commit failed (rolled back)
    * ``case_lock_failed`` — couldn't acquire case lock (concurrent
      writer); 409
    * ``solver_dicts_partial_override`` — DEC-V61-107.5 / Codex R12
      P1: subset of {controlDict, fvSchemes, fvSolution} is
      user-overridden but not all three; the new pimpleFoam template
      authors all three together as a coherent solver-config group,
      so a partial override would leave a mix of icoFoam-era +
      pimpleFoam-era dicts that OpenFOAM would reject at startup.
      Engineer must either revert all overrides (re-author from
      AI defaults) or override all three together.
    """

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


@dataclass(frozen=True, slots=True)
class StlPatchBCResult:
    case_id: str
    case_dir: Path
    patches: tuple[tuple[str, BCClass], ...]
    # Per-patch inlet velocity vector (only populated for VELOCITY_INLET
    # patches; defect-6 fix means the direction follows each patch's
    # inward normal). ``inlet_speed`` is the scalar magnitude common
    # to all inlets.
    inlet_speed: float
    inlet_velocities: tuple[tuple[str, tuple[float, float, float]], ...]
    nu: float
    delta_t: float
    end_time: float
    # DEC-V61-111: solver actually authored into controlDict. Reflects
    # ``solver_name`` after fallback (icoFoam → pimpleFoam upgrade per
    # V61-107.5; unknown → pimpleFoam default).
    solver_name: str
    written_files: tuple[str, ...]
    skipped_user_overrides: tuple[str, ...]
    warnings: tuple[str, ...]


# DEC-V61-111: solvers the dict plan can author. ``icoFoam`` is
# DEPRECATED for the named-patch path (V61-107.5 found it produces
# NaN on STL meshes regardless of dt); a request for icoFoam is
# upgraded to pimpleFoam with a warning. simpleFoam is the new
# steady-state path for cases like iter01 where the intent is a
# bypass-jet steady solution at low Re.
_SUPPORTED_SOLVERS: frozenset[str] = frozenset({"pimpleFoam", "simpleFoam"})
_DEFAULT_SOLVER: str = "pimpleFoam"


_PATCH_RE = re.compile(
    r"(\w+)\s*\{[^}]*nFaces\s+(\d+)[^}]*startFace\s+(\d+)[^}]*\}",
    re.DOTALL,
)


# BCClass → OpenFOAM constraint type that the polyMesh ``boundary``
# file must declare. Constraint-type patches (symmetry, wedge, cyclic,
# empty, processor) require the boundary file's ``type`` to match the
# field BC dict's constraint type — otherwise icoFoam exits with FATAL
# IO ERROR ``patch type 'patch' not constraint type 'symmetry'``.
# gmshToFoam emits all patches as ``type patch`` by default, so we
# rewrite affected patches in-place during BC setup.
#
# Wall patches are NOT rewritten: ``type patch`` + ``noSlip`` field BC
# is valid OpenFOAM (no constraint requirement), and the cosmetic
# ``type wall`` upgrade is out of scope for the symmetry-defect fix.
_CONSTRAINT_PATCH_TYPES: dict[BCClass, str] = {
    BCClass.SYMMETRY: "symmetry",
}


def _read_patch_ranges(boundary_path: Path) -> list[tuple[str, int, int]]:
    """Return ordered ``[(name, startFace, nFaces), ...]`` from
    ``constant/polyMesh/boundary``. Skips the OpenFOAM ``FoamFile``
    header dict.
    """
    text = boundary_path.read_text()
    out: list[tuple[str, int, int]] = []
    for m in _PATCH_RE.finditer(text):
        name = m.group(1)
        if name == "FoamFile":
            continue
        nfaces = int(m.group(2))
        start = int(m.group(3))
        out.append((name, start, nfaces))
    return out


def _read_named_patches(boundary_path: Path) -> list[str]:
    """Convenience wrapper returning patch names only."""
    return [name for name, _start, _n in _read_patch_ranges(boundary_path)]


_FIELD_LINE_RE = re.compile(r"^(\s*)(type|physicalType)(\s+)(\w+)(\s*;\s*)$")


def _strip_line_comment(line: str) -> str:
    """Remove OpenFOAM ``//`` line comments. Block comments
    ``/* ... */`` are out of scope (gmshToFoam doesn't emit them
    inside patch blocks)."""
    idx = line.find("//")
    return line if idx < 0 else line[:idx]


def _rewrite_polymesh_boundary_constraint_types(
    boundary_text: str,
    patches_with_class: list[tuple[str, BCClass]],
) -> str | None:
    """Return rewritten ``constant/polyMesh/boundary`` content with
    ``type`` and ``physicalType`` upgraded to the OpenFOAM constraint
    type for any patch whose BCClass is in ``_CONSTRAINT_PATCH_TYPES``.

    Returns ``None`` when no rewrites are needed (no constraint patches
    in the case) — caller skips the extra atomic-commit entry.

    Adversarial-loop iter06 defect-8 closure: half-pipe with symmetry
    plane caused icoFoam FATAL IO ERROR because the field BC dict
    declared ``type symmetry`` while the boundary file kept
    gmshToFoam's default ``type patch`` for that patch.

    Implementation note (Codex post-merge round-1 finding closure):
    line-based parser that tracks patch context via brace depth and
    strips line comments before matching the ``type`` / ``physicalType``
    fields. Earlier regex-only version could rewrite commented-out
    ``// type patch;`` text while leaving the live field unchanged,
    or fail entirely on a stray ``}`` inside a comment.

    Caller responsibility: read the boundary file under the case_lock
    so the read/rewrite/write sequence is one critical section. The
    function takes the pre-read text rather than a Path to make the
    locking discipline explicit at the call site.
    """
    rewrites = {
        name: _CONSTRAINT_PATCH_TYPES[cls]
        for name, cls in patches_with_class
        if cls in _CONSTRAINT_PATCH_TYPES
    }
    if not rewrites:
        return None

    lines = boundary_text.splitlines(keepends=True)
    out_lines: list[str] = []
    current_patch: str | None = None
    block_depth = 0
    pending_patch_name: str | None = None
    name_token_re = re.compile(r"^\s*(\w+)\s*$")

    for line in lines:
        logic_line = _strip_line_comment(line)

        if current_patch is None and pending_patch_name is None:
            m = name_token_re.match(logic_line)
            if m and m.group(1) in rewrites:
                pending_patch_name = m.group(1)
                out_lines.append(line)
                continue

        if current_patch is None and pending_patch_name is not None:
            if "{" in logic_line:
                current_patch = pending_patch_name
                pending_patch_name = None
                block_depth = logic_line.count("{") - logic_line.count("}")
                out_lines.append(line)
                continue
            # Pending name but no opening brace yet; pass through.
            out_lines.append(line)
            # If this line has non-whitespace content other than the
            # name itself, it was a false positive (e.g. ``symmetry``
            # appeared as a value or list element). Drop the pending
            # tracker.
            if logic_line.strip():
                pending_patch_name = None
            continue

        if current_patch is not None:
            block_depth += logic_line.count("{") - logic_line.count("}")
            field_match = _FIELD_LINE_RE.match(logic_line.rstrip("\n").rstrip("\r"))
            if field_match and block_depth >= 1:
                indent, field_name, sep, _value, tail = field_match.groups()
                new_value = rewrites[current_patch]
                trailing = "\n" if line.endswith("\n") else ""
                out_lines.append(
                    f"{indent}{field_name}{sep}{new_value}{tail.rstrip()}{trailing}"
                )
            else:
                out_lines.append(line)
            if block_depth <= 0:
                current_patch = None
                block_depth = 0
            continue

        out_lines.append(line)

    return "".join(out_lines)


def _compute_patch_inward_normals(
    case_dir: Path,
    patch_ranges: list[tuple[str, int, int]],
) -> dict[str, np.ndarray]:
    """For each patch, compute the average INWARD-pointing unit normal
    (the direction flow must enter to actually go into the fluid).

    OpenFOAM boundary face normals point OUT of the fluid domain
    (away from the cell that owns the face). For a velocity inlet,
    the BC velocity vector should point INWARD = ``-outward_normal``.

    Returns a dict ``{patch_name: unit_inward_normal_3vec}``. Patches
    with degenerate (zero-area) face sets get a zero vector — the
    caller falls back to the legacy hardcoded direction in that case.
    """
    polymesh = case_dir / "constant" / "polyMesh"
    points_path = polymesh / "points"
    faces_path = polymesh / "faces"
    if not points_path.is_file() or not faces_path.is_file():
        return {name: np.zeros(3) for name, _s, _n in patch_ranges}
    try:
        points = parse_points(points_path)
        faces = parse_faces(faces_path)
    except Exception:  # noqa: BLE001 — parser raises on malformed; treat as no-data
        return {name: np.zeros(3) for name, _s, _n in patch_ranges}

    out: dict[str, np.ndarray] = {}
    for name, start, n in patch_ranges:
        if n <= 0:
            out[name] = np.zeros(3)
            continue
        # Average the per-face Newell-method normal (sum of outward
        # cross products around each polygon ring), normalize to unit
        # length. Newell handles non-planar quads/n-gons gracefully.
        avg_n = np.zeros(3)
        for face_idx in range(start, start + n):
            if face_idx >= len(faces):
                continue
            ring = faces[face_idx]
            # Newell's method: sum of (curr × next) cross products.
            n_v = np.zeros(3)
            for i in range(len(ring)):
                p_curr = points[ring[i]]
                p_next = points[ring[(i + 1) % len(ring)]]
                n_v[0] += (p_curr[1] - p_next[1]) * (p_curr[2] + p_next[2])
                n_v[1] += (p_curr[2] - p_next[2]) * (p_curr[0] + p_next[0])
                n_v[2] += (p_curr[0] - p_next[0]) * (p_curr[1] + p_next[1])
            avg_n += n_v
        norm = float(np.linalg.norm(avg_n))
        if norm < 1e-12:
            out[name] = np.zeros(3)
        else:
            outward = avg_n / norm
            # Inward = -outward (flow into fluid is opposite to the
            # outward boundary normal).
            out[name] = -outward
    return out


# Canonical role tokens scanned across compound patch names. Priority
# order matters: a name like ``inlet_wall_seam`` should classify as an
# inlet (the actual flow boundary) rather than a wall, so inlet/outlet/
# symmetry are checked before wall. Each entry is (token_substring,
# class). Tokens are matched as substrings of the lowercased name.
_CANONICAL_ROLE_TOKENS: tuple[tuple[str, BCClass], ...] = (
    ("inlet", BCClass.VELOCITY_INLET),
    ("outlet", BCClass.PRESSURE_OUTLET),
    ("symmetry", BCClass.SYMMETRY),
    ("wall", BCClass.NO_SLIP_WALL),
)


def _classify_patch(
    name: str,
    *,
    overrides: dict[str, BCClass] | None = None,
) -> tuple[BCClass, str | None]:
    """Map a patch name to a BCClass via the project default table.
    Returns (class, warning_or_None). Unrecognized names fall through
    to NO_SLIP_WALL with a warning.

    Lookup order:
        0. DEC-V61-108 Phase A: per-patch user override from
           ``system/patch_classification.yaml``. Engineer-authored
           overrides take precedence over every heuristic step
           below — this is the bridge from the 3D viewport's
           click-to-classify UX into the BC mapper.
        1. Exact case-insensitive match against ``_DEFAULT_PATCH_CLASS``
           (covers single-token names like ``inlet``, ``walls``,
           ``left``, ``top``).
        2. Strip a trailing ``_<digits>`` or ``<digits>`` suffix and
           retry (canonical multi-instance numbering like ``inlet_1``,
           ``walls01``).
        3. Canonical role-token scan: search for ``inlet`` / ``outlet`` /
           ``symmetry`` / ``wall`` as a substring (priority order: inlet
           before outlet before symmetry before wall). Handles compound
           CAD-export names where the role token is embedded:
           ``outlet_branch`` → outlet, ``left_inlet`` → inlet,
           ``inlet_main`` → inlet, ``walls_perimeter`` → wall.
           Codex post-merge finding (defect-7 follow-up): the previous
           strip-after-first-underscore rule mis-classified ``left_inlet``
           as wall because ``left`` matched the default wall token.
        4. Fall through to NO_SLIP_WALL with warning.
    """
    if overrides is not None and name in overrides:
        return overrides[name], None
    lower = name.lower()
    cls = _DEFAULT_PATCH_CLASS.get(lower)
    if cls is not None:
        return cls, None
    # Step 2: strip trailing digits.
    stripped = re.sub(r"_?\d+$", "", lower)
    if stripped and stripped != lower:
        cls = _DEFAULT_PATCH_CLASS.get(stripped)
        if cls is not None:
            return cls, None
    # Step 3: canonical role-token substring scan, prioritized.
    for token, token_cls in _CANONICAL_ROLE_TOKENS:
        if token in lower:
            return token_cls, None
    return (
        BCClass.NO_SLIP_WALL,
        f"patch {name!r} not in default classification table; "
        f"defaulting to no-slip wall (override via raw-dict editor "
        f"if needed)",
    )


# DEC-V61-108 Phase A: sidecar holding per-patch user-authored
# classification overrides. Lives at
# ``<case_dir>/system/patch_classification.yaml`` (system/ is already
# the engineer-owned dict directory under the V61-102 raw-dict editor
# convention, so co-locating here keeps the case directory tidy and
# the lifecycle bound to the case). Format:
#
#   schema_version: 1
#   overrides:
#     <patch_name_as_in_polymesh_boundary>: <bc_class_str>
#     ...
#
# Reads return {} for missing/malformed files (the heuristic still
# runs unaltered). Writes are managed by the patch-classification
# route, which is the single point of validation.
_PATCH_CLASSIFICATION_REL = "system/patch_classification.yaml"
_PATCH_CLASSIFICATION_SCHEMA_VERSION = 1


def load_patch_classification_overrides(case_dir: Path) -> dict[str, BCClass]:
    """Return ``{patch_name: BCClass}`` from the sidecar, or ``{}``.

    Tolerates a missing file (no overrides yet) and a malformed file
    (treated as empty so the heuristic still runs — the route layer
    is responsible for surfacing parse errors at write time).
    Unknown ``bc_class`` strings are silently dropped, NOT raised:
    a stale override referencing a removed class shouldn't block
    BC authoring on the rest of the case.
    """
    p = case_dir / _PATCH_CLASSIFICATION_REL
    if not p.is_file():
        return {}
    try:
        import yaml  # local import — yaml is already a project dep
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    raw = data.get("overrides")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, BCClass] = {}
    for patch_name, cls_str in raw.items():
        if not isinstance(patch_name, str) or not isinstance(cls_str, str):
            continue
        try:
            out[patch_name] = BCClass(cls_str)
        except ValueError:
            continue
    return out


def _u_block(
    name: str,
    cls: BCClass,
    inlet_u: tuple[float, float, float],
) -> str:
    if cls == BCClass.VELOCITY_INLET:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            fixedValue;\n"
            f"        value           uniform ({inlet_u[0]:.6g} {inlet_u[1]:.6g} {inlet_u[2]:.6g});\n"
            f"    }}\n"
        )
    if cls == BCClass.PRESSURE_OUTLET:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            zeroGradient;\n"
            f"    }}\n"
        )
    if cls == BCClass.NO_SLIP_WALL:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            noSlip;\n"
            f"    }}\n"
        )
    if cls == BCClass.SYMMETRY:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            symmetry;\n"
            f"    }}\n"
        )
    raise ValueError(f"unhandled BCClass: {cls}")


def _p_block(name: str, cls: BCClass) -> str:
    if cls == BCClass.PRESSURE_OUTLET:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            fixedValue;\n"
            f"        value           uniform 0;\n"
            f"    }}\n"
        )
    if cls == BCClass.SYMMETRY:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            symmetry;\n"
            f"    }}\n"
        )
    # Velocity inlet + walls both use zeroGradient on p.
    return (
        f"    {name}\n"
        f"    {{\n"
        f"        type            zeroGradient;\n"
        f"    }}\n"
    )


_SOLVER_GROUP = (
    "system/controlDict", "system/fvSchemes", "system/fvSolution",
)
# DEC-V61-107.5 / Codex R16 closure rationale: the override-content
# guard's job is to catch the ONE dominant defect class — engineer
# overrides controlDict and reverts to icoFoam, AI re-authors
# pimpleFoam fvSolution → solver aborts with cryptic error. Earlier
# rounds (R13 P2-B, R14 P1+P2, R15 P2-A+P2-B, R16 P2+P3) chased
# subtler defect classes via regex: PISO/PIMPLE blocks (R14),
# divDevReff in fvSchemes (R14, R15), divSchemes default fallback
# (R15, R16), comment-stripping precedence (R15, R16). Each round
# closed real issues but the regex stack now competes with OpenFOAM's
# own parser — a battle we can't win statically.
#
# Pragmatic scope reduction (R16 closure): catch ONLY `application
# icoFoam;` literal in user-overridden controlDict (the originally
# motivating defect, dominant in the wild because that's the only
# one-line revert engineers do). Long-tail mismatches in fvSchemes
# / fvSolution still surface as `solver_diverged` (HTTP 502) at
# /solve time with the OpenFOAM error in the response — the
# engineer sees the real cause directly rather than a static-guard
# false positive/negative.
_ICOFOAM_APPLICATION_RE = re.compile(
    r"^\s*application\s+icoFoam\s*;",
    re.MULTILINE,
)
# DEC-V61-111 / Codex R1 P1-1: solver-aware mismatch detection. When
# the AI authors simpleFoam, a user-overridden controlDict that
# carries ``application pimpleFoam;`` (a stale value from the prior
# pimpleFoam-default era) is now the dangerous mismatch — same shape
# as the icoFoam-vs-pimpleFoam mismatch the original guard caught.
# Mirror pattern for completeness.
_PIMPLEFOAM_APPLICATION_RE = re.compile(
    r"^\s*application\s+pimpleFoam\s*;",
    re.MULTILINE,
)
_SIMPLEFOAM_APPLICATION_RE = re.compile(
    r"^\s*application\s+simpleFoam\s*;",
    re.MULTILINE,
)
# Comment stripping for the `application` regex. R17 P3 closure:
# strip both line `// ...` and block `/* ... */` comments in a single
# alternation pass to avoid the precedence flaw that bit R15. Using
# alternation rather than two sequential subs keeps each match
# independent, so a `// /* */` line is correctly handled by the line
# branch and a `/* // */` block by the block branch.
_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)


def _detect_solver_marker_overrides(
    case_dir: Path, *, ai_solver: str
) -> list[str]:
    """Return user-overridden controlDict iff it carries an
    ``application <solver>;`` literal that mismatches the solver the
    AI is authoring AND not all 3 solver-group files are user-
    overridden (full-group override = engineer owns coherence, guard
    steps out).

    DEC-V61-111 / Codex R1 P1-1 expansion: pre-V61-111 this guard only
    caught ``application icoFoam;`` because the AI always authored
    pimpleFoam. With simpleFoam now an AI-authored option, the
    dangerous mismatch class extended: if AI authors simpleFoam and
    user-overridden controlDict still says ``application pimpleFoam;``
    (stale from the prior era), the AI's simpleFoam fvSchemes/
    fvSolution would mismatch on disk (SIMPLE block expected by
    simpleFoam vs PIMPLE in fvSolution), aborting OpenFOAM at startup
    with a cryptic dictionary error. Generalized: catch any
    application-name in user-overridden controlDict that disagrees
    with the resolved AI solver.

    Scope: still catches only the dominant defect class
    (controlDict-only override mismatch). Long-tail mismatches (PISO
    block in user fvSolution under AI-pimpleFoam, etc.) continue to
    surface as solver_diverged at /solve time with the OpenFOAM error
    in the response — see DEC-V61-107.5 R16 closure rationale above.
    """
    overridden_status: dict[str, bool] = {
        rel: is_user_override(case_dir, relative_path=rel)
        for rel in _SOLVER_GROUP
    }
    if all(overridden_status.values()):
        # Engineer fully owns the solver group.
        return []

    rel = "system/controlDict"
    if not overridden_status[rel]:
        return []
    try:
        raw = (case_dir / rel).read_text()
    except OSError:
        return [rel]
    content = _COMMENT_RE.sub("", raw)
    # icoFoam in user controlDict is ALWAYS a mismatch (AI never
    # authors icoFoam after V61-107.5), regardless of which solver
    # the AI is currently authoring.
    if _ICOFOAM_APPLICATION_RE.search(content):
        return [rel]
    # When AI authors simpleFoam, pimpleFoam in user controlDict is
    # a mismatch (AI's SIMPLE-block fvSolution would clash with user's
    # transient PIMPLE controlDict).
    if ai_solver == "simpleFoam" and _PIMPLEFOAM_APPLICATION_RE.search(content):
        return [rel]
    # When AI authors pimpleFoam, simpleFoam in user controlDict is
    # a mismatch (AI's PIMPLE-block fvSolution would clash with user's
    # steady-state SIMPLE controlDict).
    if ai_solver == "pimpleFoam" and _SIMPLEFOAM_APPLICATION_RE.search(content):
        return [rel]
    return []


# Backward-compat alias so existing call sites and tests that import
# the original symbol keep working. New code should call
# ``_detect_solver_marker_overrides`` directly with the resolved
# AI solver name.
def _detect_icofoam_marker_overrides(case_dir: Path) -> list[str]:
    """DEC-V61-111: thin shim over ``_detect_solver_marker_overrides``
    pinning ai_solver=pimpleFoam (the pre-V61-111 default). Retained
    for tests + any caller still on the legacy signature; the
    in-tree call site in ``setup_bc_from_stl_patches`` was rewired
    to the new function.
    """
    return _detect_solver_marker_overrides(case_dir, ai_solver=_DEFAULT_SOLVER)


def _build_dict_plan(
    patches_with_class: list[tuple[str, BCClass]],
    *,
    inlet_u_per_patch: dict[str, tuple[float, float, float]],
    nu: float,
    delta_t: float,
    end_time: float,
    solver_name: str = _DEFAULT_SOLVER,
) -> list[tuple[str, str]]:
    """Compose the 7-dict (rel, content) plan for the named patches.

    ``inlet_u_per_patch`` carries one velocity vector per VELOCITY_INLET
    patch (defect-6 fix: each inlet's direction comes from its own
    polyMesh face normals, so rotated geometries get flow heading into
    the duct rather than into walls).

    ``solver_name`` selects the solver-specific controlDict / fvSchemes /
    fvSolution templates. DEC-V61-111: branches between pimpleFoam
    (V61-107.5 default for transient cases) and simpleFoam (steady-state
    SIMPLE algorithm for cases where intent.json declares ``solver.name:
    simpleFoam`` — appropriate for low-Re internal flow with
    bypass jets like iter01 where transient PIMPLE diverges to NaN
    regardless of dt).
    """
    u_blocks = "".join(
        _u_block(name, cls, inlet_u_per_patch.get(name, (0.0, 0.0, 0.0)))
        for name, cls in patches_with_class
    )
    p_blocks = "".join(_p_block(name, cls) for name, cls in patches_with_class)

    # DEC-V61-111: solver-specific controlDict / fvSchemes / fvSolution.
    if solver_name == "simpleFoam":
        control_dict = _build_simplefoam_control_dict(end_time)
        fv_schemes = _build_simplefoam_fv_schemes()
        fv_solution = _build_simplefoam_fv_solution()
    else:
        # pimpleFoam (default) — the V61-107.5 transient path.
        control_dict = _build_pimplefoam_control_dict(end_time, delta_t)
        fv_schemes = _build_pimplefoam_fv_schemes()
        fv_solution = _build_pimplefoam_fv_solution()

    plan: list[tuple[str, str]] = [
        (
            "0/U",
            'FoamFile { version 2.0; format ascii; class volVectorField; '
            'location "0"; object U; }\n'
            "dimensions      [0 1 -1 0 0 0 0];\n"
            "internalField   uniform (0 0 0);\n"
            "boundaryField\n"
            "{\n"
            f"{u_blocks}"
            "}\n",
        ),
        (
            "0/p",
            'FoamFile { version 2.0; format ascii; class volScalarField; '
            'location "0"; object p; }\n'
            "dimensions      [0 2 -2 0 0 0 0];\n"
            "internalField   uniform 0;\n"
            "boundaryField\n"
            "{\n"
            f"{p_blocks}"
            "}\n",
        ),
        (
            "constant/physicalProperties",
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "constant"; object physicalProperties; }\n'
            "transportModel  Newtonian;\n"
            f"nu              [0 2 -1 0 0 0 0] {nu};\n",
        ),
        (
            "constant/momentumTransport",
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "constant"; object momentumTransport; }\n'
            "simulationType laminar;\n",
        ),
        (
            "system/controlDict",
            control_dict,
        ),
        (
            "system/fvSchemes",
            fv_schemes,
        ),
        (
            "system/fvSolution",
            fv_solution,
        ),
    ]
    return plan


def _build_pimplefoam_control_dict(end_time: float, delta_t: float) -> str:
    """DEC-V61-107.5 pimpleFoam controlDict template (default solver
    for the named-patch path). Adjustable timestep with maxCo=0.5 gates
    CFL stability on tetrahedral STL meshes with high-aspect-ratio
    cells (iter01 blade-gap region etc.).
    """
    return (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        # DEC-V61-107.5 (2026-05-01): switched from icoFoam to
        # pimpleFoam for the named-patch path. icoFoam in OpenFOAM-10
        # has no setDeltaT.H include so adjustTimeStep keys are
        # ignored — fixed dt + tetrahedral STL meshes with high
        # aspect-ratio cells in tight gap regions force CFL_max >> 1
        # → NaN regardless of the global dt chosen.
        "application pimpleFoam;\n"
        "startFrom startTime;\n"
        "startTime 0;\n"
        "stopAt endTime;\n"
        f"endTime {end_time};\n"
        f"deltaT {delta_t};\n"
        "writeControl runTime;\n"
        "writeInterval 1.0;\n"
        "purgeWrite 0;\n"
        "writeFormat ascii;\n"
        "writePrecision 6;\n"
        "writeCompression off;\n"
        "timeFormat general;\n"
        "timePrecision 6;\n"
        "runTimeModifiable true;\n"
        "adjustTimeStep yes;\n"
        "maxCo 0.5;\n"
        # Codex R12 P2: maxDeltaT honors caller's delta_t (callers
        # rely on the cap for residual sampling cadence). pimpleFoam
        # can still scale DOWN for stability.
        f"maxDeltaT {delta_t};\n"
    )


def _build_pimplefoam_fv_schemes() -> str:
    """DEC-V61-107 / V61-107.5 pimpleFoam fvSchemes: linearUpwind for
    convection (handles sharp interior obstacles without NaN
    oscillation), corrected laplacian/snGrad for non-orthogonal
    tetrahedral meshes.
    """
    return (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        "ddtSchemes  { default Euler; }\n"
        "gradSchemes { default Gauss linear; }\n"
        # V61-107: linearUpwind avoids NaN on convection-dominated
        # flow past sharp interior obstacles. V61-107.5: pimpleFoam
        # routes through divDevReff which evaluates
        # div((nuEff*dev2(T(grad(U))))) — needs explicit scheme even
        # for laminar simulationType.
        "divSchemes  { default none; div(phi,U) Gauss linearUpwind grad(U); "
        "div((nuEff*dev2(T(grad(U))))) Gauss linear; }\n"
        # V61-107: corrected (not orthogonal) — tetrahedral STL
        # meshes are inherently non-orthogonal.
        "laplacianSchemes { default Gauss linear corrected; }\n"
        "interpolationSchemes { default linear; }\n"
        "snGradSchemes { default corrected; }\n"
    )


def _build_pimplefoam_fv_solution() -> str:
    """DEC-V61-107.5 pimpleFoam fvSolution: PIMPLE block with
    nOuterCorrectors=1 to keep numerics close to the icoFoam-style
    PISO loop for the cube/channel baseline.
    """
    return (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSolution; }\n'
        "solvers\n"
        "{\n"
        "    p  { solver PCG; preconditioner DIC; tolerance 1e-06; "
        "relTol 0.05; }\n"
        "    pFinal { $p; relTol 0; }\n"
        "    U  { solver smoothSolver; smoother symGaussSeidel; "
        "tolerance 1e-05; relTol 0; }\n"
        "    UFinal { $U; relTol 0; }\n"
        "}\n"
        "PIMPLE\n"
        "{\n"
        "    nOuterCorrectors 1;\n"
        "    nCorrectors 2;\n"
        "    nNonOrthogonalCorrectors 2;\n"
        "    pRefCell 0;\n"
        "    pRefValue 0;\n"
        "}\n"
    )


def _build_simplefoam_control_dict(end_time: float) -> str:
    """DEC-V61-111 simpleFoam controlDict template (steady-state SIMPLE
    algorithm). For low-Re internal flow with bypass jets like iter01
    where transient PIMPLE diverges to NaN regardless of dt — the
    underlying issue is that iter01 is a STEADY problem whose
    transient discretization spends itself fighting initial-condition
    decay rather than reaching the physical bypass-jet flow field.

    simpleFoam does iteration-based marching (deltaT=1 = one
    iteration), so endTime is interpreted as iteration count, not
    seconds. adjustTimeStep + maxCo are NOT used (no physical time
    coordinate). Convergence is gated by SIMPLE residualControl in
    fvSolution.
    """
    # simpleFoam treats endTime as iteration count when deltaT=1.
    # If caller passed end_time<5 (low value typical of transient
    # smoke budgeting), bump to 100 minimum so the steady solver
    # has enough iterations to converge from the zero-IC.
    iterations = max(int(end_time), 100)
    return (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "application simpleFoam;\n"
        "startFrom startTime;\n"
        "startTime 0;\n"
        "stopAt endTime;\n"
        f"endTime {iterations};\n"
        # SIMPLE iteration step is unitless; deltaT=1 gives 1
        # iteration per Time= step in the log.
        "deltaT 1;\n"
        "writeControl timeStep;\n"
        # Write final state + a few intermediates (every 50 iter)
        # so callers extracting the last time directory get the
        # converged solution.
        "writeInterval 50;\n"
        "purgeWrite 0;\n"
        "writeFormat ascii;\n"
        "writePrecision 6;\n"
        "writeCompression off;\n"
        "timeFormat general;\n"
        "timePrecision 6;\n"
        "runTimeModifiable true;\n"
        # adjustTimeStep / maxCo / maxDeltaT are NOT meaningful for
        # simpleFoam (no physical time). Omitted by design.
    )


def _build_simplefoam_fv_schemes() -> str:
    """DEC-V61-111 simpleFoam fvSchemes: ddtSchemes steadyState
    (zeroes the ddt term so the iteration is a true steady marching
    rather than transient), bounded linearUpwind for convection
    (steady-state-bounded-corrected), corrected laplacian/snGrad for
    non-orthogonal tetrahedral STL meshes.
    """
    return (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        # steadyState ddt scheme zeroes the d/dt term → iteration is
        # pure spatial marching, not transient. This is the principal
        # difference from pimpleFoam and the reason simpleFoam
        # reaches the steady physical solution iteratively without
        # the transient initial-condition explosion that diverges
        # iter01 in pimpleFoam.
        "ddtSchemes  { default steadyState; }\n"
        "gradSchemes { default Gauss linear; "
        "grad(U) cellLimited Gauss linear 1; }\n"
        # bounded prefix is the OpenFOAM-recommended steady-state
        # convection scheme — adds a boundedness correction that
        # keeps SIMPLE from diverging when the flow field is far
        # from steady (initial iterations).
        "divSchemes  { default none; div(phi,U) bounded Gauss linearUpwind grad(U); "
        "div((nuEff*dev2(T(grad(U))))) Gauss linear; }\n"
        "laplacianSchemes { default Gauss linear corrected; }\n"
        "interpolationSchemes { default linear; }\n"
        "snGradSchemes { default corrected; }\n"
    )


def _build_simplefoam_fv_solution() -> str:
    """DEC-V61-111 simpleFoam fvSolution: SIMPLE block with relaxation
    factors p=0.3, U=0.7 (OpenFOAM tutorial-standard for laminar
    SIMPLE), residualControl 1e-3/1e-4 (loose convergence appropriate
    for adversarial-loop case validation; engineers can tighten via
    raw-dict editor).

    Key difference from pimpleFoam: NO PIMPLE block; instead a SIMPLE
    block + relaxationFactors block. simpleFoam reads SIMPLE not PIMPLE.
    """
    return (
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSolution; }\n'
        "solvers\n"
        "{\n"
        # GAMG is the OpenFOAM-recommended pressure solver for
        # SIMPLE. PCG is fine but GAMG converges faster on the
        # smoothly-varying steady pressure field.
        "    p  { solver GAMG; tolerance 1e-06; relTol 0.1; "
        "smoother GaussSeidel; }\n"
        "    U  { solver smoothSolver; smoother symGaussSeidel; "
        "tolerance 1e-05; relTol 0.1; nSweeps 1; }\n"
        "}\n"
        "SIMPLE\n"
        "{\n"
        # nNonOrthogonalCorrectors handles the corrected laplacian/snGrad
        # schemes' non-orthogonal mesh terms.
        "    nNonOrthogonalCorrectors 2;\n"
        "    pRefCell 0;\n"
        "    pRefValue 0;\n"
        # residualControl gates convergence: when both p AND U
        # initial residuals fall below the listed tolerance,
        # simpleFoam stops iterating. 1e-3/1e-4 are loose targets
        # appropriate for adversarial-case validation; the converged
        # check in run_smoke also enforces finiteness.
        "    residualControl\n"
        "    {\n"
        "        p   1e-3;\n"
        "        U   1e-4;\n"
        "    }\n"
        "}\n"
        "relaxationFactors\n"
        "{\n"
        # OpenFOAM-tutorial-standard SIMPLE relaxation factors for
        # laminar incompressible. p=0.3 damps pressure-correction
        # over-shoot; U=0.7 is the standard momentum factor.
        "    fields\n"
        "    {\n"
        "        p   0.3;\n"
        "    }\n"
        "    equations\n"
        "    {\n"
        "        U   0.7;\n"
        "    }\n"
        "}\n"
    )


def setup_bc_from_stl_patches(
    case_dir: Path,
    *,
    case_id: str,
    inlet_speed: float = _DEFAULT_INLET_SPEED,
    nu: float = _DEFAULT_NU,
    delta_t: float = _DEFAULT_DELTA_T,
    end_time: float = _DEFAULT_END_TIME,
    solver_name: str | None = None,
) -> StlPatchBCResult:
    """Author the OpenFOAM dict tree using named patches from polyMesh/boundary.

    Idempotent. The atomic commit + V61-102 user-override invariant
    means: dicts the engineer manually edited (via raw-dict editor →
    manifest source=user) are NOT clobbered by re-runs.

    ``solver_name`` (DEC-V61-111) selects the solver-specific
    controlDict / fvSchemes / fvSolution templates:

    * ``None`` or unrecognized → ``pimpleFoam`` (default, V61-107.5
      transient PIMPLE) with a warning if the caller asked for something
      else.
    * ``"pimpleFoam"`` → V61-107.5 transient PIMPLE template.
    * ``"simpleFoam"`` → steady-state SIMPLE template (iter01-class
      cases where transient PIMPLE diverges to NaN).
    * ``"icoFoam"`` → upgraded to ``pimpleFoam`` with a warning. icoFoam
      on STL meshes was found to NaN regardless of dt (V61-107.5
      empirical finding); the upgrade path keeps callers from silently
      hitting that failure mode.

    Raises ``StlPatchBCError`` with structured ``failing_check`` for
    every detectable failure mode; the route maps each to an HTTP 4xx
    code.
    """
    # DEC-V61-111: resolve the requested solver to one of the
    # supported authoring paths. Unknown / icoFoam → pimpleFoam with
    # a warning; None → pimpleFoam silent default. Resolved name
    # written into the result for callers to verify.
    solver_warnings: list[str] = []
    if solver_name in (None, ""):
        resolved_solver = _DEFAULT_SOLVER
    elif solver_name == "icoFoam":
        resolved_solver = "pimpleFoam"
        solver_warnings.append(
            "solver_name='icoFoam' upgraded to 'pimpleFoam' per "
            "DEC-V61-107.5 (icoFoam on STL meshes produces NaN "
            "regardless of dt)."
        )
    elif solver_name in _SUPPORTED_SOLVERS:
        resolved_solver = solver_name
    else:
        resolved_solver = _DEFAULT_SOLVER
        solver_warnings.append(
            f"solver_name={solver_name!r} unrecognized; defaulting to "
            f"{_DEFAULT_SOLVER}. Supported: {sorted(_SUPPORTED_SOLVERS)}."
        )
    boundary_path = case_dir / "constant" / "polyMesh" / "boundary"
    if not boundary_path.is_file():
        raise StlPatchBCError(
            f"polyMesh/boundary missing at {boundary_path} — run mesh "
            "generation before BC setup",
            failing_check="mesh_not_setup",
        )
    patch_ranges = _read_patch_ranges(boundary_path)
    if not patch_ranges:
        raise StlPatchBCError(
            f"polyMesh/boundary has no patches at {boundary_path}",
            failing_check="no_named_patches",
        )
    patch_names = [name for name, _s, _n in patch_ranges]
    if patch_names == ["patch0"]:
        # Legacy single-patch (defaultFaces) path — the LDC or channel
        # executor is the right entry point, not this one.
        raise StlPatchBCError(
            "polyMesh/boundary has only the legacy ``patch0`` — the "
            "STL was imported without named solids. Use setup_ldc_bc "
            "or setup_channel_bc instead.",
            failing_check="no_named_patches",
        )

    # DEC-V61-108 Phase A · Codex R1 P2: classification, inlet-velocity
    # synthesis, and plan-build all happen INSIDE the case_lock below
    # so a concurrent PUT /patch-classification cannot land between
    # override-read and dict-author. Pre-lock state below is limited
    # to caller arguments + read-only polyMesh ground truth.
    warnings: list[str] = list(solver_warnings)

    try:
        with case_lock(case_dir):
            # DEC-V61-108 R1 P2: load overrides + classify INSIDE the
            # lock. Same critical section as the dict commit below, so
            # the on-disk dicts and the saved override state agree on
            # exit (no observable interleaving with route PUT/DELETE,
            # which take the same lock).
            overrides = load_patch_classification_overrides(case_dir)
            patches_with_class: list[tuple[str, BCClass]] = []
            for name in patch_names:
                cls, warning = _classify_patch(name, overrides=overrides)
                patches_with_class.append((name, cls))
                if warning:
                    warnings.append(warning)

            # Defect-6 fix: compute per-patch inward normals so velocity
            # inlets get flow direction matching the actual patch
            # orientation. polyMesh/faces is read-only ground truth so
            # this read inside the lock is cheap.
            inward_normals = _compute_patch_inward_normals(
                case_dir, patch_ranges
            )
            inlet_u_per_patch: dict[str, tuple[float, float, float]] = {}
            fallback_axis = np.array([1.0, 0.0, 0.0])
            for name, cls in patches_with_class:
                if cls != BCClass.VELOCITY_INLET:
                    continue
                n_in = inward_normals.get(name, np.zeros(3))
                if float(np.linalg.norm(n_in)) < 1e-9:
                    # Degenerate patch (no readable faces) — fall back to
                    # +x axis. Engineers can override via raw-dict editor.
                    n_in = fallback_axis
                    warnings.append(
                        f"patch {name!r}: could not read face normals from "
                        f"polyMesh; defaulting inlet velocity to "
                        f"{inlet_speed} m/s along +x. Override via "
                        f"raw-dict editor if the geometry isn't axis-aligned."
                    )
                u_vec = inlet_speed * n_in
                inlet_u_per_patch[name] = (
                    float(u_vec[0]), float(u_vec[1]), float(u_vec[2])
                )

            plan = _build_dict_plan(
                patches_with_class,
                inlet_u_per_patch=inlet_u_per_patch,
                nu=nu,
                delta_t=delta_t,
                end_time=end_time,
                solver_name=resolved_solver,
            )
            # Codex R13 P2-A + P2-B closure (V61-107.5) + Codex R1
            # P1-1 closure (V61-111): content-aware solver-marker
            # check, INSIDE case_lock so override status can't flip
            # between check and commit. The AI authors either
            # pimpleFoam (default) or simpleFoam (V61-111). The
            # dangerous case isn't "any single-file override" (which
            # Codex R13 P2-B correctly flagged as too aggressive —
            # engineers legitimately tune endTime / deltaT / relTol in
            # single files); it's specifically when a user-overridden
            # controlDict carries an ``application <solver>;`` literal
            # that mismatches the solver the AI is currently
            # authoring. That + AI-authored other-solver dicts in the
            # OTHER files = OpenFOAM startup abort.
            _solver_offenders = _detect_solver_marker_overrides(
                case_dir, ai_solver=resolved_solver
            )
            if _solver_offenders:
                raise StlPatchBCError(
                    "solver-dict group contains user-overridden file(s) "
                    f"with application-name marker mismatching AI-authored "
                    f"{resolved_solver}: {_solver_offenders}. "
                    "AI-authored solver dicts in the other slots would "
                    "mismatch on disk and OpenFOAM would abort at startup. "
                    "Either: (a) revert the overrides via raw-dict editor "
                    "reset, or (b) also override the OTHER files to a "
                    f"coherent {resolved_solver} template, or (c) request "
                    "the matching solver via ``solver_name`` query param.",
                    failing_check="solver_dicts_partial_override",
                )
            # Defect-8 (iter06) + Codex post-merge MED: if any patch has
            # a constraint-type BCClass (symmetry, …), rewrite
            # ``constant/polyMesh/boundary`` so its ``type`` matches the
            # field BC dict. Otherwise icoFoam exits with FATAL IO ERROR
            # on the constraint-type mismatch. The boundary file is read
            # INSIDE case_lock so the read/rewrite/write sequence is one
            # critical section — no TOCTOU window where another writer
            # could clobber a stale snapshot. Included in the atomic
            # commit so a partial write rolls back with the dicts.
            boundary_rewrite = _rewrite_polymesh_boundary_constraint_types(
                boundary_path.read_text(), patches_with_class
            )
            if boundary_rewrite is not None:
                plan.append(("constant/polyMesh/boundary", boundary_rewrite))
            try:
                written, skipped = _atomic_commit_dicts(case_dir, plan)
            except OSError as exc:
                raise StlPatchBCError(
                    f"atomic commit failed: {exc}",
                    failing_check="write_failed",
                ) from exc
            if written:
                mark_ai_authored(
                    case_dir,
                    relative_paths=list(written),
                    action="setup_bc_from_stl_patches",
                    detail={
                        "patches": [
                            {"name": name, "bc_class": cls.value}
                            for name, cls in patches_with_class
                        ],
                        "warnings": warnings,
                    },
                )
            # DEC-V61-111 / Codex R1 P2-1: if controlDict was skipped
            # because the engineer owns it, the on-disk
            # ``application <solver>;`` is the truth — not the
            # ``resolved_solver`` we wanted to author. Read the actual
            # field from the on-disk controlDict so callers
            # (smoke runner, frontend, tests) see what /solve will
            # actually run, not what /setup-bc was asked to write.
            if "system/controlDict" in skipped:
                try:
                    actual_text = (case_dir / "system/controlDict").read_text(
                        encoding="utf-8", errors="replace"
                    )
                    actual_text = _COMMENT_RE.sub("", actual_text)
                    m = re.search(
                        r"^\s*application\s+([A-Za-z][A-Za-z0-9_]*)\s*;",
                        actual_text,
                        re.MULTILINE,
                    )
                    if m and m.group(1) != resolved_solver:
                        warnings.append(
                            f"solver_name reports {m.group(1)!r} (read from "
                            f"user-overridden system/controlDict on disk) "
                            f"rather than the requested {resolved_solver!r}; "
                            f"`/solve` will run {m.group(1)} per the override. "
                            f"Revert the controlDict override via raw-dict "
                            f"editor to honor the requested solver."
                        )
                        resolved_solver = m.group(1)
                except OSError:
                    # If we can't read the override, fall through with
                    # the requested resolved_solver unchanged. Down-
                    # stream solve will surface OS errors directly.
                    pass
    except CaseLockError as exc:
        raise StlPatchBCError(
            f"case lock acquisition failed: {exc}",
            failing_check="case_lock_failed",
        ) from exc

    return StlPatchBCResult(
        case_id=case_id,
        case_dir=case_dir,
        patches=tuple(patches_with_class),
        inlet_speed=inlet_speed,
        inlet_velocities=tuple(inlet_u_per_patch.items()),
        nu=nu,
        delta_t=delta_t,
        end_time=end_time,
        solver_name=resolved_solver,
        written_files=written,
        skipped_user_overrides=skipped,
        warnings=tuple(warnings),
    )
