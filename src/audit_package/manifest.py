"""Manifest builder for audit-package bundles (Phase 5 · PR-5a).

Produces a deterministic nested dict capturing everything a regulated-industry
reviewer needs to reconstruct a V&V claim:

- Case metadata (whitelist entry verbatim + git-pinned)
- Gold standard (full physics_contract + observables + git-pinned)
- Run inputs (controlDict / blockMeshDict / fvSchemes / fvSolution / 0/ fields)
- Run outputs (log tail + final residuals + postProcessing/sets output)
- Measurement (key_quantities from comparator)
- Comparator verdict + audit concerns
- Decision trail (DEC-V61-* referencing this case or its legacy aliases)
- Git repo commit SHA at manifest-build time
- Generation timestamp (ISO-8601 UTC, second precision)

Determinism guarantees (byte-stable across two identical invocations):
- All dict keys sort via ``json.dumps(..., sort_keys=True)`` in serializers.
- Timestamps are caller-injectable; when auto-generated they use UTC second
  precision.
- File paths stored as repo-relative POSIX strings.
- Git-log lookups use ``--format=%H`` (no timestamp). Absence of a git repo
  yields ``None`` rather than raising — the manifest still builds.
- Decision-trail discovery is deterministic: glob sorted, body-grep matched.

Non-goals for PR-5a:
- HMAC signing (PR-5c).
- Zip/PDF serialization (PR-5b).
- UI wiring (PR-5d).
- OpenFOAM solver invocation (out of scope; caller provides run_output_dir
  pointing at already-completed output from FoamAgentExecutor or MockExecutor).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

SCHEMA_VERSION = 1

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_WHITELIST_PATH = _REPO_ROOT / "knowledge" / "whitelist.yaml"
_GOLD_STANDARDS_ROOT = _REPO_ROOT / "knowledge" / "gold_standards"
_DECISIONS_ROOT = _REPO_ROOT / ".planning" / "decisions"

# Run-input files collected verbatim when present. Order-stable list.
_RUN_INPUT_FILES = (
    "system/controlDict",
    "system/blockMeshDict",
    "system/fvSchemes",
    "system/fvSolution",
    "system/sampleDict",
    "constant/physicalProperties",
    "constant/transportProperties",
    "constant/turbulenceProperties",
    "constant/momentumTransport",  # DEC-V61-059 Stage B: OF10 incompressible rename
    "constant/g",
)

# Common initial-field filenames under 0/
_INITIAL_FIELD_FILES = ("U", "p", "T", "k", "epsilon", "omega", "nut", "alphat")

# Number of log lines tail-read for solver_log_tail. Keeps manifest size bounded
# while preserving final residuals + completion banner.
_LOG_TAIL_LINES = 120


# ---------------------------------------------------------------------------
# Time helpers (caller-injectable for test determinism)
# ---------------------------------------------------------------------------

def _default_now_utc() -> str:
    """UTC timestamp, second precision, Z suffix."""
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git_sha_for_path(path: Path, repo_root: Path) -> Optional[str]:
    """Return the SHA of the latest commit touching ``path``.

    Uses ``git log -1 --format=%H -- <path>``. Returns None if git is
    unavailable, the path has no commit history, or the repo is shallow
    beyond this file. Never raises — the manifest still builds.
    """
    if not path.exists():
        return None
    try:
        relative = path.relative_to(repo_root)
    except ValueError:
        relative = path
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(relative)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = (result.stdout or "").strip()
    return sha if sha else None


def _git_repo_head_sha(repo_root: Path) -> Optional[str]:
    """Return HEAD SHA of repo_root's repo. None if git unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = (result.stdout or "").strip()
    return sha if sha else None


# ---------------------------------------------------------------------------
# Knowledge loaders
# ---------------------------------------------------------------------------

def _load_whitelist_entry(
    case_id: str,
    whitelist_path: Path,
    legacy_aliases: Sequence[str] = (),
) -> Optional[Dict[str, Any]]:
    """Pull the full case dict from whitelist.yaml by id OR legacy alias."""
    if not whitelist_path.exists():
        return None
    try:
        data = yaml.safe_load(whitelist_path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return None
    candidates = (case_id, *legacy_aliases)
    for case in data.get("cases", []):
        if case.get("id") in candidates:
            return case
    return None


def _load_gold_standard(
    case_id: str,
    gold_root: Path,
    legacy_aliases: Sequence[str] = (),
) -> Optional[Dict[str, Any]]:
    """Load the gold_standards YAML for case_id or any legacy alias."""
    if not gold_root.is_dir():
        return None
    for candidate in (case_id, *legacy_aliases):
        path = gold_root / f"{candidate}.yaml"
        if path.exists():
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    return data
            except (yaml.YAMLError, OSError):
                continue
    return None


# ---------------------------------------------------------------------------
# Run-output loaders
# ---------------------------------------------------------------------------

def _read_text_if_exists(path: Path) -> Optional[str]:
    """Read UTF-8 text from path; return None if absent or unreadable."""
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _load_run_inputs(run_output_dir: Path) -> Dict[str, Any]:
    """Collect verbatim OpenFOAM input files into a dict keyed by path."""
    inputs: Dict[str, Any] = {}
    for rel in _RUN_INPUT_FILES:
        text = _read_text_if_exists(run_output_dir / rel)
        if text is not None:
            inputs[rel] = text
    # Initial fields under 0/
    initial_fields: Dict[str, str] = {}
    zero_dir = run_output_dir / "0"
    if zero_dir.is_dir():
        for field_name in _INITIAL_FIELD_FILES:
            text = _read_text_if_exists(zero_dir / field_name)
            if text is not None:
                initial_fields[field_name] = text
    if initial_fields:
        inputs["0/"] = initial_fields
    return inputs


def _load_run_outputs(run_output_dir: Path) -> Dict[str, Any]:
    """Solver log tail + postProcessing/sets/ listing + final residuals."""
    outputs: Dict[str, Any] = {}

    # Solver log — scan for common names. DEC-V61-059 Stage B added
    # `log.pisoFoam` for the plane-channel laminar route (icoFoam
    # could not register a momentumTransportModel for the
    # wallShearStress FO).
    for log_name in ("log.simpleFoam", "log.icoFoam", "log.pisoFoam",
                     "log.pimpleFoam",
                     "log.buoyantFoam", "log.buoyantBoussinesqSimpleFoam"):
        log_path = run_output_dir / log_name
        if log_path.is_file():
            try:
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            outputs["solver_log_name"] = log_name
            outputs["solver_log_tail"] = "\n".join(lines[-_LOG_TAIL_LINES:])
            break

    # postProcessing/sets/ directory listing (not full content — that'd bloat
    # the manifest; zip bundle in PR-5b will include the files verbatim).
    pp_sets = run_output_dir / "postProcessing" / "sets"
    if pp_sets.is_dir():
        sets_files: List[str] = []
        for time_dir in sorted(pp_sets.iterdir()):
            if time_dir.is_dir():
                for f in sorted(time_dir.iterdir()):
                    if f.is_file():
                        sets_files.append(
                            str(f.relative_to(run_output_dir)).replace("\\", "/")
                        )
        if sets_files:
            outputs["postProcessing_sets_files"] = sets_files

    return outputs


# ---------------------------------------------------------------------------
# Decision trail
# ---------------------------------------------------------------------------

def _load_decision_trail(
    case_id: str,
    decisions_root: Path,
    legacy_aliases: Sequence[str] = (),
) -> List[Dict[str, str]]:
    """Find DEC-V61-* / DEC-ADWM-* records that mention case_id or aliases.

    Returns a deterministic sorted list of ``{"decision_id", "title",
    "relative_path"}`` dicts. Matches are body-grep against the full file.
    """
    if not decisions_root.is_dir():
        return []
    needles = (case_id, *legacy_aliases)
    trail: List[Dict[str, str]] = []
    for md in sorted(decisions_root.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not any(needle in text for needle in needles):
            continue
        decision_id = _extract_frontmatter_field(text, "decision_id")
        title = _extract_first_heading(text)
        trail.append({
            "decision_id": decision_id or md.stem,
            "title": title or md.stem,
            "relative_path": str(md.relative_to(decisions_root.parent.parent)).replace("\\", "/"),
        })
    # Sort by decision_id for stability
    trail.sort(key=lambda entry: entry["decision_id"])
    return trail


def _extract_frontmatter_field(text: str, field: str) -> Optional[str]:
    """Pull a top-level YAML frontmatter field (between ``---`` fences)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            break
        stripped = line.strip()
        if stripped.startswith(f"{field}:"):
            value = stripped[len(field) + 1:].strip()
            return value.strip('"\'') or None
    return None


def _extract_first_heading(text: str) -> Optional[str]:
    """First ``# Heading`` after optional frontmatter."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

# --- Phase 7e (DEC-V61-033, L4): embed Phase 7 artifacts into signed zip ---

# Deterministic YYYYMMDDTHHMMSSZ shape for run timestamps (mirrors 7a/7b/7c gates).
import re as _re
_PHASE7_TIMESTAMP_RE = _re.compile(r"^\d{8}T\d{6}Z$")


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_phase7_artifacts(
    case_id: str, run_id: str, repo_root: Path
) -> Optional[Dict[str, Any]]:
    """Collect Phase 7a/7b/7c artifacts for (case, run) into a manifest section.

    Returns dict with ``entries`` = sorted list of {zip_path, disk_path, sha256,
    size_bytes} dicts + ``schema_level: "L4"``. Returns None when no Phase 7
    artifacts exist for this run.

    Byte-reproducibility preserved:
    - Disk paths derive from deterministic timestamp folders.
    - SHA256 of each file is stable.
    - Entry list is sorted by ``zip_path``.
    - Manifest embeds hashes, not bytes — serialize.py then reads the files.

    Security: timestamp values read from Phase 7a/7b manifests are validated
    against _PHASE7_TIMESTAMP_RE (defense-in-depth against manifest tampering,
    mirrors Phase 7a `_TIMESTAMP_RE` + Phase 7c `_resolve_artifact_dir`).
    """
    import json as _json
    fields_root = repo_root / "reports" / "phase5_fields" / case_id
    renders_root = repo_root / "reports" / "phase5_renders" / case_id
    reports_root = repo_root / "reports" / "phase5_reports" / case_id

    entries: List[Dict[str, Any]] = []

    def _add(path: Path, zip_path: str) -> None:
        """Add a file to entries list if it exists, validates under a sanctioned root."""
        if not path.is_file():
            return
        try:
            resolved = path.resolve(strict=True)
        except (OSError, FileNotFoundError):
            return
        # Every zip entry must resolve under one of the three Phase 7 roots.
        ok = False
        for root in (fields_root, renders_root, reports_root):
            try:
                resolved.relative_to(root.resolve())
                ok = True
                break
            except (ValueError, OSError):
                continue
        if not ok:
            return
        entries.append({
            "zip_path": zip_path,
            "disk_path_rel": str(path.relative_to(repo_root)),
            "sha256": _sha256_of_file(path),
            "size_bytes": path.stat().st_size,
        })

    # Phase 7a — field artifacts (VTK + sample + residuals).
    f_manifest = fields_root / "runs" / f"{run_id}.json"
    if f_manifest.is_file():
        try:
            f_data = _json.loads(f_manifest.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            f_data = None
        if isinstance(f_data, dict):
            ts = f_data.get("timestamp")
            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
                case_ts_dir = fields_root / ts
                if case_ts_dir.is_dir():
                    for p in sorted(case_ts_dir.rglob("*")):
                        if not p.is_file():
                            continue
                        try:
                            rel = p.resolve().relative_to(case_ts_dir.resolve()).as_posix()
                        except (ValueError, OSError):
                            continue
                        # Skip huge non-essential files to keep zip sane.
                        if p.suffix.lower() == ".vtk" and p.stat().st_size > 50 * 1024 * 1024:
                            continue
                        _add(p, f"phase7/field_artifacts/{rel}")

    # Phase 7b — renders.
    r_manifest = renders_root / "runs" / f"{run_id}.json"
    if r_manifest.is_file():
        try:
            r_data = _json.loads(r_manifest.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            r_data = None
        if isinstance(r_data, dict):
            ts = r_data.get("timestamp")
            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
                r_ts_dir = renders_root / ts
                if r_ts_dir.is_dir():
                    for p in sorted(r_ts_dir.rglob("*")):
                        if not p.is_file():
                            continue
                        try:
                            rel = p.resolve().relative_to(r_ts_dir.resolve()).as_posix()
                        except (ValueError, OSError):
                            continue
                        _add(p, f"phase7/renders/{rel}")

    # Phase 7c — HTML + PDF comparison report. Report dir is keyed by the
    # same timestamp (7c service writes under reports/phase5_reports/{case}/{ts}/).
    # Pull the timestamp from the 7a manifest (authoritative).
    if f_manifest.is_file():
        try:
            f_data = _json.loads(f_manifest.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            f_data = None
        if isinstance(f_data, dict):
            ts = f_data.get("timestamp")
            if isinstance(ts, str) and _PHASE7_TIMESTAMP_RE.match(ts):
                pdf = reports_root / ts / f"{run_id}_comparison_report.pdf"
                if pdf.is_file():
                    _add(pdf, "phase7/comparison_report.pdf")

    if not entries:
        return None

    entries.sort(key=lambda d: d["zip_path"])
    return {
        "schema_level": "L4",
        "canonical_spec": "docs/specs/audit_package_canonical_L4.md",
        "entries": entries,
        "total_files": len(entries),
        "total_bytes": sum(e["size_bytes"] for e in entries),
    }


def build_manifest(
    *,
    case_id: str,
    run_id: str,
    run_output_dir: Optional[Path] = None,
    repo_root: Path = _REPO_ROOT,
    legacy_case_ids: Sequence[str] = (),
    measurement: Optional[Dict[str, Any]] = None,
    comparator_verdict: Optional[str] = None,
    audit_concerns: Optional[Sequence[Dict[str, Any]]] = None,
    build_fingerprint: Optional[str] = None,
    solver_name: Optional[str] = None,
    include_phase7: bool = True,
) -> Dict[str, Any]:
    """Assemble the audit-package manifest for a single case + run.

    Parameters
    ----------
    case_id
        Whitelist case id (post-rename canonical, e.g., ``"duct_flow"``).
    run_id
        Caller-supplied run identifier. Expected to be deterministic for
        reproducible bundles — e.g., hash of (case_id + input SHAs).
    run_output_dir
        Directory containing OpenFOAM outputs (produced by FoamAgentExecutor
        or MockExecutor). When None, the manifest's ``run.status`` becomes
        ``"no_run_output"`` and inputs/outputs sections are omitted — this
        is a legitimate shape for MOCK / dry-build bundles.
    repo_root
        Repository root for knowledge lookups and git SHA pinning.
    legacy_case_ids
        Old case ids that may appear in whitelist, gold files, or decision
        records (for rename histories like ``fully_developed_pipe`` →
        ``duct_flow`` per DEC-V61-011).
    measurement, comparator_verdict, audit_concerns
        Populated by the caller from the comparator's output. All optional;
        defaults to a skeleton with None/empty.
    build_fingerprint
        Deterministic identifier for this manifest. Renamed from
        ``generated_at`` per Codex round-5 L3 finding
        (DEC-V61-019): the value is derived from inputs rather than
        wall-clock time, so ``generated_at`` was a misleading label.
        When None, defaults to an ISO-UTC timestamp (fallback for legacy
        callers that did not yet switch to deterministic derivation).
        Production callers should pass a deterministic string
        (e.g., ``sha256(case_id|run_id)[:16]``) to preserve byte
        reproducibility.
    solver_name
        When known (typically from whitelist), recorded at ``run.solver``
        even if ``run_output_dir`` is None.

    Returns
    -------
    dict
        Nested manifest dict. See module docstring for schema.
    """
    aliases = tuple(legacy_case_ids)

    whitelist_entry = _load_whitelist_entry(case_id, _WHITELIST_PATH, aliases)
    gold_standard = _load_gold_standard(case_id, _GOLD_STANDARDS_ROOT, aliases)

    # If the gold file declares legacy_case_ids, fold them into alias set so
    # the decision-trail grep catches pre-rename DEC records too.
    extended_aliases: List[str] = list(aliases)
    if gold_standard:
        gold_legacy = gold_standard.get("legacy_case_ids")
        if isinstance(gold_legacy, list):
            for legacy in gold_legacy:
                if isinstance(legacy, str) and legacy not in extended_aliases:
                    extended_aliases.append(legacy)

    decision_trail = _load_decision_trail(
        case_id, _DECISIONS_ROOT, tuple(extended_aliases)
    )

    # Resolve the actual gold file path for SHA pinning. Prefer canonical;
    # fall back to legacy.
    gold_file_path: Optional[Path] = None
    for candidate in (case_id, *extended_aliases):
        p = _GOLD_STANDARDS_ROOT / f"{candidate}.yaml"
        if p.exists():
            gold_file_path = p
            break

    git_section: Dict[str, Optional[str]] = {
        "repo_commit_sha": _git_repo_head_sha(repo_root),
        "whitelist_commit_sha": _git_sha_for_path(_WHITELIST_PATH, repo_root),
        "gold_standard_commit_sha": (
            _git_sha_for_path(gold_file_path, repo_root) if gold_file_path else None
        ),
    }

    run_section: Dict[str, Any] = {"run_id": run_id}
    if solver_name:
        run_section["solver"] = solver_name
    if run_output_dir is not None and run_output_dir.is_dir():
        run_section["status"] = "output_present"
        run_section["output_dir"] = str(run_output_dir)
        inputs = _load_run_inputs(run_output_dir)
        if inputs:
            run_section["inputs"] = inputs
        outputs = _load_run_outputs(run_output_dir)
        if outputs:
            run_section["outputs"] = outputs
    else:
        run_section["status"] = "no_run_output"

    measurement_section: Dict[str, Any] = {
        "key_quantities": dict(measurement or {}),
        "comparator_verdict": comparator_verdict,
        "audit_concerns": list(audit_concerns or []),
    }

    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "manifest_id": f"{case_id}-{run_id}",
        "build_fingerprint": build_fingerprint or _default_now_utc(),
        "git": git_section,
        "case": {
            "id": case_id,
            "legacy_ids": list(extended_aliases),
            "whitelist_entry": whitelist_entry,
            "gold_standard": gold_standard,
        },
        "run": run_section,
        "measurement": measurement_section,
        "decision_trail": decision_trail,
    }
    # Phase 7e (DEC-V61-033): L4 schema — embed Phase 7 artifacts (field
    # captures, renders, comparison report PDF) into the signed zip.
    # Only attached when include_phase7=True AND artifacts exist for this run.
    if include_phase7:
        phase7 = _collect_phase7_artifacts(case_id, run_id, repo_root)
        if phase7 is not None:
            manifest["phase7"] = phase7
    return manifest
