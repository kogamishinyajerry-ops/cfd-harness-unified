"""DEC-V61-075 P2-T2.3 · §6.3 hybrid-init reference-run resolver.

Resolves whether the AuditPackage corpus contains a previously-archived
``docker_openfoam`` manifest for a given case — the §6.3
``hybrid_init_reference_run_present`` flag that
``src.metrics.trust_gate.apply_executor_mode_routing`` consumes when
gating a HYBRID_INIT run.

Plane: ``src.audit_package`` is Plane.CONTROL (per
``src/_plane_assignment.py:50``). This module reads from the local
filesystem (``audit_package_root``) and returns a boolean — no
plane-boundary crossing. Callers in Plane.CONTROL (``TaskRunner``)
inject the flag into Plane.EVALUATION (``trust_gate``) so the routing
module never has to know about audit-package internals — preserves
``.importlinter`` Contract 2 (``src.metrics`` does NOT depend on
``src.audit_package`` or ``src.executor`` implementation details).

EXECUTOR_ABSTRACTION.md §6.3 quote:

    Verify the §5.1 byte-equality property held against the executor's
    claimed reference run. The reference is identified by the manifest's
    ``executor.contract_hash`` plus the case-profile's
    ``tolerance_policy_observables`` set; the auditor (TrustGate)
    resolves the reference SHA via the AuditPackage decision-trail.

This module's resolver implements the **first half** of the §6.3
requirement: presence detection. The contract-hash equality check
remains TrustGate-side once the reference manifest is identified.
HYBRID_INIT mode is fed False here when no reference exists, which
triggers the §6.3 ``hybrid_init_invariant_unverified`` WARN ceiling.

Skeleton scope (T2.3): scan signed-zip ``manifest.json`` payloads and
plain ``manifest.json`` files (e.g., during dev when artifacts are
unzipped for inspection). Each matched manifest must satisfy ALL of:

  1. ``manifest["case"]["id"]`` equals ``case_id`` OR ``case_id``
     appears in ``manifest["case"]["legacy_ids"]`` (rename history).
  2. ``manifest["executor"]["mode"]`` equals ``docker_openfoam``
     (per EXECUTOR_ABSTRACTION.md §3 absent-field forward-compat,
     a missing ``executor`` section is also treated as
     ``docker_openfoam``).
  3. ``manifest["measurement"]["comparator_verdict"]`` is in the
     success set (``PASS``, or absent on success-only bundles where
     the verdict was rolled up elsewhere — be permissive on this last
     check since pre-verdict bundles still anchor the §5.1 byte-
     equality contract).

A manifest that fails to parse (truncated file, malformed JSON, zip
without manifest.json) is **silently skipped** — the resolver MUST NOT
raise on a corrupt corpus entry, since auditors regularly archive
in-progress runs that may be partial. Silent skip mirrors
``manifest._load_decision_trail``'s tolerant-glob pattern.

The implementation is bounded by
``_MAX_MANIFESTS_SCANNED_PER_CALL`` to prevent a pathological
audit-package directory (e.g., 100k bundles from a CI archive) from
turning a single ``run_task`` into a multi-second filesystem walk.
Callers that need exhaustive resolution can raise the cap or invert
control via direct manifest enumeration.
"""

from __future__ import annotations

import json
import logging
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional

logger = logging.getLogger(__name__)

# Sentinel cap so a run-loop never burns >O(seconds) on a corpus walk.
# Picked an order-of-magnitude above realistic per-case archive depth
# (a single case rarely accumulates >1000 manifests). Operators with
# larger corpora can subclass / shadow the resolver and lift the cap.
_MAX_MANIFESTS_SCANNED_PER_CALL = 10_000

# Manifest filenames recognized when scanning. ``manifest.json`` is the
# canonical name written by ``src.audit_package.serialize`` (line 131).
_MANIFEST_FILENAME = "manifest.json"

# §6.1 docker_openfoam mode string. Mirrors the bare-string constant in
# ``src.metrics.trust_gate._EXECUTOR_MODE_DOCKER_OPENFOAM`` — kept as a
# module-local literal so this resolver does NOT import from
# ``src.executor`` (Plane.EXECUTION); ``src.audit_package`` is
# Plane.CONTROL and crosses Plane.EXECUTION via the manifest schema,
# not via direct imports of executor modules.
_EXECUTOR_MODE_DOCKER_OPENFOAM = "docker_openfoam"

# Comparator verdicts considered "successful" for §5.1 reference-run
# purposes. Pre-verdict manifests (no comparator section yet, e.g.,
# attestation-only bundles) are permitted because the §5.1 byte-
# equality contract is on canonical_artifacts content, not on a
# downstream verdict. Negative verdicts (FAIL, HAZARD) are excluded
# because a known-failed run cannot anchor a hybrid-init invariant.
_SUCCESS_VERDICTS: frozenset[str] = frozenset({"PASS"})
_NEGATIVE_VERDICTS: frozenset[str] = frozenset({"FAIL", "HAZARD"})


def _safe_load_manifest(payload: bytes) -> Optional[Dict[str, Any]]:
    """Decode ``payload`` as JSON; return None on any decode error.

    A corrupt manifest (truncated zip, hand-edited JSON, bad encoding)
    must not raise — the corpus walk continues to the next entry.
    """
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        # A top-level non-object manifest is malformed; treat as skip.
        return None
    return obj


def _iter_candidate_manifests(audit_package_root: Path) -> Iterator[Dict[str, Any]]:
    """Yield manifest dicts from every signed zip + plain
    ``manifest.json`` under ``audit_package_root``.

    Codex T2.3 post-commit P2-C fix: the cap is applied **during**
    iteration of ``rglob`` rather than after a ``sorted(rglob(...))``
    materialization. Building a sorted list would exhaust the full
    generator before the loop body, so the cap could never actually
    bound the traversal cost on a large corpus. We accept the
    determinism trade-off (zip + json scans are no longer
    lexicographically sorted) because the resolver is short-circuit
    by design — the **first** successful match wins (see
    ``has_docker_openfoam_reference_run`` body), so iteration order
    is never observable to callers. If a future debugging session
    needs deterministic order it can call ``sorted(...)`` outside the
    cap-bounded loop.

    Malformed entries silent-skip per module docstring.
    """
    if not audit_package_root.is_dir():
        return
    scanned = 0
    for zip_path in audit_package_root.rglob("*.zip"):
        if scanned >= _MAX_MANIFESTS_SCANNED_PER_CALL:
            return
        scanned += 1
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                if _MANIFEST_FILENAME not in zf.namelist():
                    continue
                payload = zf.read(_MANIFEST_FILENAME)
        except (zipfile.BadZipFile, OSError):
            continue
        manifest = _safe_load_manifest(payload)
        if manifest is not None:
            yield manifest
    for json_path in audit_package_root.rglob(_MANIFEST_FILENAME):
        if scanned >= _MAX_MANIFESTS_SCANNED_PER_CALL:
            return
        scanned += 1
        try:
            payload = json_path.read_bytes()
        except OSError:
            continue
        manifest = _safe_load_manifest(payload)
        if manifest is not None:
            yield manifest


def _manifest_matches_case(
    manifest: Mapping[str, Any],
    case_id: str,
    legacy_aliases: tuple[str, ...] = (),
) -> bool:
    """True when the manifest's case section identifies ``case_id`` or
    any of the caller-provided ``legacy_aliases``.

    Codex T2.3 post-commit P2-B fix: the rename relationship is
    bidirectional. Without ``legacy_aliases`` expansion, querying for a
    post-rename canonical id (e.g., ``duct_flow``) would miss every
    pre-rename manifest (whose ``case.id`` is still
    ``fully_developed_pipe`` and whose ``legacy_ids`` array has not
    been retroactively backfilled). Callers (``TaskRunner``) extract
    legacy aliases from the gold-standard YAML's ``legacy_case_ids``
    field and pass them here so the resolver matches both directions:

      - canonical → legacy (manifest.case.legacy_ids contains case_id)
      - legacy   → canonical (caller's legacy_aliases contains
        manifest.case.id)

    Codex T2.3 post-commit R2 P2 fix: malformed manifest ``case`` blobs
    (where ``case.id`` or a ``case.legacy_ids`` entry is a dict / list /
    other unhashable value) no longer raise ``TypeError`` from set
    construction. Non-string ids silent-skip per the resolver's
    tolerant-corpus contract; a single corrupt archive cannot break
    HYBRID_INIT routing for the entire scan.
    """
    case = manifest.get("case")
    if not isinstance(case, Mapping):
        return False
    manifest_id = case.get("id")
    manifest_legacy = case.get("legacy_ids")
    if not isinstance(manifest_legacy, list):
        manifest_legacy = []

    # Filter to string-typed ids only — set construction below would
    # raise TypeError on a dict/list value otherwise. Codex R2 P2.
    manifest_ids = {
        ident
        for ident in (manifest_id, *manifest_legacy)
        if isinstance(ident, str)
    }
    caller_ids = {ident for ident in (case_id, *legacy_aliases) if isinstance(ident, str)}
    return bool(caller_ids & manifest_ids)


def _manifest_is_docker_openfoam(manifest: Mapping[str, Any]) -> bool:
    """True when the executor section claims ``docker_openfoam`` mode
    (or the section is absent — pre-P2 zips per §3 forward-compat)."""
    executor = manifest.get("executor")
    if executor is None:
        # §3 + spike F-3: absent ``executor`` field means pre-P2 zip,
        # treat as ``docker_openfoam`` (the only mode that existed).
        return True
    if not isinstance(executor, Mapping):
        return False
    mode = executor.get("mode")
    return isinstance(mode, str) and mode == _EXECUTOR_MODE_DOCKER_OPENFOAM


def _manifest_is_successful(manifest: Mapping[str, Any]) -> bool:
    """True when the comparator verdict is in the success set or
    absent (pre-verdict manifest still anchors §5.1 canonical_artifacts).
    A negative verdict (FAIL / HAZARD) excludes the manifest."""
    measurement = manifest.get("measurement")
    if not isinstance(measurement, Mapping):
        return True  # absent measurement section → permissive
    verdict = measurement.get("comparator_verdict")
    if verdict is None:
        return True  # absent verdict → permissive (pre-verdict bundle)
    if not isinstance(verdict, str):
        return False  # malformed verdict (list, dict) → exclude
    if verdict in _NEGATIVE_VERDICTS:
        return False
    return verdict in _SUCCESS_VERDICTS or verdict not in _NEGATIVE_VERDICTS


def has_docker_openfoam_reference_run(
    case_id: str,
    *,
    audit_package_root: Path,
    legacy_aliases: tuple[str, ...] = (),
) -> bool:
    """Return True when ``audit_package_root`` archives at least one
    ``docker_openfoam`` manifest for ``case_id`` that anchors the
    §5.1 hybrid-init byte-equality invariant.

    Parameters
    ----------
    case_id
        Whitelist case id (post-rename canonical, e.g. ``"duct_flow"``).
    audit_package_root
        Directory holding signed-zip bundles (``*.zip`` containing
        ``manifest.json``) and/or plain ``manifest.json`` exports.
        ``rglob`` is used so per-case subdirectory layouts work.
    legacy_aliases
        Caller-provided pre-rename ids (e.g.,
        ``("fully_developed_pipe",)`` when ``case_id="duct_flow"``).
        A manifest matches when its ``case.id`` OR any
        ``case.legacy_ids`` entry intersects with
        ``{case_id, *legacy_aliases}`` — covers both the canonical→
        legacy and legacy→canonical directions of a rename per Codex
        T2.3 post-commit P2-B fix. Callers typically source these from
        ``knowledge/gold_standards/<case>.yaml::legacy_case_ids``.

    Returns
    -------
    bool
        - True: at least one matching manifest found, with
          ``executor.mode == docker_openfoam`` and a non-negative
          comparator verdict.
        - False: no matching manifest, or ``audit_package_root`` does
          not exist / is empty / contains only malformed entries.

    Raises
    ------
    None — all I/O errors and parse failures silent-skip per module
    docstring (corpus tolerance requirement).

    Notes
    -----
    The function is read-only and cache-free. Callers that invoke it
    on every ``run_task`` should consider memoizing per
    ``(case_id, audit_package_root, legacy_aliases)`` if profiling
    shows hot-path contention (T2.3 skeleton does NOT memoize —
    keeping the coupling surface small per RETRO-V61-001 baseline).
    """
    for manifest in _iter_candidate_manifests(audit_package_root):
        if not _manifest_matches_case(manifest, case_id, legacy_aliases):
            continue
        if not _manifest_is_docker_openfoam(manifest):
            continue
        if not _manifest_is_successful(manifest):
            continue
        return True
    return False


__all__ = ["has_docker_openfoam_reference_run"]
