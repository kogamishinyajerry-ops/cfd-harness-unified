"""DEC-V61-154 (N5.3) · audit V2 manifest builder + canonical bytes.

Walks case state and computes:
  * case_state_sha — SHA-256 of canonical case-state bytes
                     (sorted file/key order over polyMesh +
                     physical dicts + BC dicts)
  * solver_log_sha — SHA-256 of log.<solver> when present
  * figure_shas    — SHA-256 per figure under postProcessing/figures/

Byte-reproducibility (charter §"verification" final bullet):
  ``canonical_manifest_bytes(manifest)`` excludes ``authored_at`` from
  the serialized bytes. Two runs at different times against the same
  case state produce identical canonical bytes → identical case_state_sha.

V132: read-only walk; no disk write; no V132 mutator. The HMAC
signing path (when integrated into the existing audit_package zip
builder) reuses the V61-014 signing infrastructure with no new
secret per charter §threat-model row 3.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from ui.backend.schemas.audit_v2_manifest import ProvenanceManifest


# ────────── Public surface ──────────


def build_provenance_manifest(case_dir: Path) -> ProvenanceManifest:
    """Walk the case directory and produce a :class:`ProvenanceManifest`.

    Always returns a manifest — missing optional artifacts (solver log,
    figures) leave the corresponding fields None / empty rather than
    raising.
    """
    case_state_sha = _compute_case_state_sha(case_dir)
    solver_log_sha = _compute_solver_log_sha(case_dir)
    figure_shas = _compute_figure_shas(case_dir)
    return ProvenanceManifest(
        case_id=case_dir.name,
        case_state_sha=case_state_sha,
        solver_log_sha=solver_log_sha,
        figure_shas=figure_shas,
        dec_trail=[],
        authored_at=datetime.now(tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    )


def canonical_manifest_bytes(manifest: ProvenanceManifest) -> bytes:
    """Byte-reproducible serialization. Excludes wall-clock
    ``authored_at`` so two builds at different times produce identical
    canonical bytes for the same case state.

    Used by the HMAC signing path (existing src/audit_package/sign.py
    `sign(manifest, zip_bytes, key)` — pass `canonical_manifest_bytes`
    output as the manifest argument to keep HMAC stable across
    re-builds)."""
    payload = manifest.model_dump(exclude={"authored_at"})
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# ────────── case_state_sha ──────────


# Files included in the case-state SHA, in stable order. Each file's
# bytes contribute to a single rolling hash; missing files are
# skipped (their absence still affects the SHA via length-of-skipped
# canonical record).
_CASE_STATE_FILES_ORDER: tuple[str, ...] = (
    # polyMesh — defines geometry + mesh topology
    "constant/polyMesh/points",
    "constant/polyMesh/owner",
    "constant/polyMesh/neighbour",
    "constant/polyMesh/boundary",
    "constant/polyMesh/faces",
    # physics dicts (N3.3 outputs)
    "constant/physicalProperties",
    "constant/momentumTransport",
    # BC dicts (N4.1 outputs)
    "0.orig/U",
    "0.orig/p",
    # solver dicts (engineer / profile YAML rendered)
    "system/controlDict",
    "system/fvSchemes",
    "system/fvSolution",
)


def _compute_case_state_sha(case_dir: Path) -> str:
    """Compute SHA-256 over the canonical case-state byte stream.

    Stream layout per file:
        b"<rel_path>:" + b"<size_in_bytes>:" + raw_bytes + b"\\n"

    Missing files contribute `b"<rel_path>:MISSING\\n"` so their
    absence is reflected in the hash (engineer adding a previously-
    missing file changes the SHA)."""
    h = hashlib.sha256()
    for rel in _CASE_STATE_FILES_ORDER:
        path = case_dir / rel
        h.update(rel.encode("utf-8"))
        h.update(b":")
        if path.is_file():
            try:
                data = path.read_bytes()
            except OSError:
                h.update(b"UNREADABLE\n")
                continue
            h.update(str(len(data)).encode("utf-8"))
            h.update(b":")
            h.update(data)
            h.update(b"\n")
        else:
            h.update(b"MISSING\n")
    return h.hexdigest()


# ────────── solver_log_sha ──────────


_LOG_CANDIDATES = (
    "log.icoFoam",
    "log.simpleFoam",
    "log.pimpleFoam",
    "log.buoyantSimpleFoam",
    "log.buoyantPimpleFoam",
)


def _compute_solver_log_sha(case_dir: Path) -> str | None:
    for name in _LOG_CANDIDATES:
        path = case_dir / name
        if path.is_file():
            try:
                return hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                return None
    return None


# ────────── figure_shas ──────────


def _compute_figure_shas(case_dir: Path) -> dict[str, str]:
    """Walk postProcessing/figures/ and SHA every file. Returns a
    sorted dict keyed on filename (NOT path — leaf only) so two
    builds in different working directories produce the same dict.
    """
    figures_dir = case_dir / "postProcessing" / "figures"
    if not figures_dir.is_dir():
        return {}
    out: dict[str, str] = {}
    for path in sorted(figures_dir.iterdir()):
        if not path.is_file():
            continue
        try:
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        out[path.name] = sha
    return out
