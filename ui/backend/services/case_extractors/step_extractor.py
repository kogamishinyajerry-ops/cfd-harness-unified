"""STEP-path extractor · case_dir → StepArtifacts | None (v0.1).

Per DEC-V61-214. Discovers the canonical ``step_path`` for a case
directory plus the pre-staged geometry bbox/extents that
``geometry_ingest.unit_detector.detect_unit`` consumes
(``advisor_stack.py:898-915``; ``unit_detector.py:165-169``).

Extracted shape::

    StepArtifacts(
        step_path: str | None,             # first *.step/*.stp/*.STEP/*.STP under
                                           # <case_dir> root then <case_dir>/cad/
        bbox_max_extent_raw: float | None, # max(dx,dy,dz) from cad/bbox.json `bbox`
                                           # with manifest.json fallback
        body_extents_raw: list[float] | None,
                                           # cad/bbox.json `extents` (or manifest fallback)
    )

The extractor returns ``None`` when **all three** fields are
unresolvable for the case dir — collapsing the "no STEP + no bbox + no
extents" case into a single ``None`` (cleanest contract because the
single downstream consumer ``assemble_stack`` gates dispatch on
``step_path is not None`` and populated bbox/extents without a
step_path are useless). When at least ``step_path`` resolves, the
returned ``StepArtifacts`` may carry per-field ``None``s on the bbox
and extents (independent honest omissions — DEC-V61-214 §Truth-chain
R2). When bbox/extents are present but ``step_path`` is absent, the
extractor still collapses to ``None`` (consumer-gated by step_path).

## Architectural placement

Mirrors DEC-V61-211 ``solver_block_extractor`` + DEC-V61-212
``shm_dict_extractor`` + DEC-V61-213 ``thermo_dict_extractor``
exactly: stdlib-only (``pathlib`` + ``json`` + ``dataclasses`` +
``typing``), pure function, read-only, no route, no mutation, no
import from ``geometry_ingest`` (would pull ``trimesh`` transitively
via ``__init__.py → health_check``). ``StepArtifacts`` is a NEW
dataclass — no upstream class exists today so no mirror parity canary
is needed.

The discovery logic is **lifted** from the HTTP path's
``ai_review.py:_autodiscover_step`` (root-then-cad/, per-suffix
sorted glob) and the bbox/extents subset of
``ai_review.py:_autodiscover_geometry_metadata`` (``cad/bbox.json``
with ``manifest.json`` fallback). The arithmetic is lifted from
``ai_review.py:_bbox_max_extent`` (``max(dx, dy, dz)`` from a 6-tuple
``bbox``) — BUT the HTTPException(400) failure paths are replaced
with ``return None`` per-field, because this extractor's transport is
silent omission, not HTTP error (DRAFT §v0.1 In).

## Scope-locked v0.1 — extractor will NOT do any of these

  - **Open the STEP file** — for any purpose (B-rep parsing, header
    re-read, PRODUCT entity inspection, mojibake byte sniffing). The
    extractor only checks for file *existence* by path glob; it never
    reads the ``.step`` file's bytes. DRAFT §Scope locking line 158-159.
    The single downstream consumer ``unit_detector`` already handles
    STEP-header SI_UNIT / CONVERSION_BASED_UNIT parsing internally
    (``unit_detector.parse_step_header_unit``, ``unit_detector.py:81-139``);
    duplicating that here would be drift risk.

  - **Parse the ISO 10303-21 HEADER section** (FILE_DESCRIPTION /
    FILE_NAME / FILE_SCHEMA / originating_system / preprocessor /
    schema AP203/AP214/AP242). The workflow brief framed this as v0.1
    scope, but the DRAFT correctly identified that (a) the single
    consumer (``unit_detector``) doesn't need any of those fields
    beyond the LENGTH unit which ``parse_step_header_unit`` already
    handles, and (b) opening the STEP file violates the stdlib-only +
    pure-discovery contract. The 6 sample STEP files in
    ``.venv/share/doc/gmsh/`` span 4 exporters (ST-DEVELOPER v8,
    THEOREM SOLUTIONS / UG, 3DEXPERIENCE AP214, Open CASCADE 7.8) and
    3 schemas (CONFIG_CONTROL_DESIGN AP203, CONFIGURATION_CONTROL_3D_DESIGN
    AP203 ED2, AUTOMOTIVE_DESIGN AP214) — all parseable but ZERO of
    them feed an in-repo case_profile today, so building this
    machinery now would be speculative infrastructure with no
    validation surface. Defer to v0.2 sub-DEC IF a future advisor
    needs originating_system / schema beyond the unit decision.

  - **Detect mojibake / decode Chinese PRODUCT entity names**
    (ST-Developer X2 escape, GBK-mangled raw bytes — see
    ``~/.claude/projects/-Users-Zhuanz/memory/reference_step_chinese_mojibake.md``
    for the decoding recipe). Requires opening the STEP file at byte
    level, which is explicitly out of scope per the bullet above. A
    future sub-DEC ``DEC-V61-2XX · step_brep_inspector`` triggered by
    an APU 0507/0527-class case sedimenting a real STEP with Chinese
    PRODUCT names into ``.planning/case_profiles/`` will scope a
    separate extractor that DOES open the STEP file and either (i)
    flag mojibake presence as a structural advisory finding, or (ii)
    decode + re-emit clean names. That extractor will live alongside
    ``step_extractor``, NOT replace it. Today: ZERO in-repo STEPs
    carry mojibake (the 6 ``.venv`` samples are clean ASCII), so the
    deferral is honest, not avoidance.

  - **Synthesize bbox/extents from the STEP geometry when
    ``bbox.json`` is absent.** Requires OpenCascade / FreeCAD — would
    violate the stdlib-only contract. Honest omission contract:
    ``bbox.json`` absent ⇒ ``bbox_max_extent_raw=None``, NOT
    synthesized. Same architectural promise as siblings 211/212/213.

  - **Disambiguate multiple STEP files in the same case** by
    heuristic (size / mtime / name match). v0.1 contract: first
    sorted-win, byte-stable with the HTTP path's
    ``_autodiscover_step``. DRAFT §v0.1 Out line 65-66. Sub-DEC if a
    real case ever ships ≥2 STEPs and the first-sorted-wins behaviour
    is wrong.

  - **Recurse into vendored directories** (``.venv/``,
    ``node_modules/``). The extractor checks ONLY
    ``(case_dir, case_dir/cad)`` — no ``os.walk``, no
    ``.glob('**/*.step')``, no ancestor traversal. DRAFT §Truth-chain
    risks line 148-151. The ONLY in-repo STEPs are gmsh tutorials
    under ``.venv/share/doc/gmsh/{tutorials,examples}/``; a bug that
    recursed would silently leak tutorial STEPs into eval discovery.
    Pinned via ``test_no_recursion_into_vendored_dirs``.

  - **Cache across calls.** Pure read-every-time. Mirrors siblings.

  - **Write anything to disk.** Pure read-only.

## Why step v0.1 is honest discrimination = 1 output today

Per DEC-V61-214 §"Case-differentiation signal (honest)": **zero** of
27 ``*_dicts/`` profiles ship ``.step`` / ``.stp`` / ``bbox.json`` /
``cad/`` directories today (verified 2026-05-28). The extractor
returns ``None`` for all of them — that IS the correct honest output:
they have no CAD, ``unit_detector`` should not dispatch, and the eval
sees a deterministic 27/27 absence row.

The extractor's value is unlocked **the instant** a future case
(e.g., APU bay 0527, case_002a/b with CAD) sediments a STEP into its
profile dir; the extractor then starts producing non-None and
``unit_detector`` joins the dispatch set without any other code
change. We accept the 1-output-today situation because (a) the
absence row itself is a case-class signal the eval can assert, and
(b) the cost is low and the future-proofing is free.

## Truth-chain risks specific to this extractor

  1. **STEP present but unparseable**: the extractor never opens the
     STEP file, so it cannot encounter parse failure.
     ``unit_detector`` handles header-parse failure
     (``parse_step_header_unit`` returns ``(None, evidence)``). v0.1's
     contract: "the file exists and is readable as a path string."
     Truth chain stays clean.

  2. **bbox.json present but malformed**: per-field honest omission
     (``bbox_max_extent_raw=None`` and/or ``body_extents_raw=None``,
     independently), NOT all-or-nothing refusal — different from
     ``solver_block``'s whole-snapshot refusal because the fields
     here are independent and the downstream advisor
     (``unit_detector``) tolerates partial input per its docstring at
     ``unit_detector.py:170-173``. DEC-V61-213 R1 key-presence carry-
     forward: distinguish "no bbox.json" (key absent) from
     "bbox.json has malformed bbox key" (key present, shape wrong) —
     both yield ``None`` for the affected field, but each path is
     tested separately so silent drift between them is caught.

  3. **STEP file collision with vendored / tutorial paths**: see the
     ``no recursion into vendored dirs`` bullet above. Only
     ``<case_dir>`` and ``<case_dir>/cad/`` are inspected.

## Estimated truth-chain wire

| Field | Source on disk | Lift target | Consumer site |
|---|---|---|---|
| ``step_path`` | first ``*.step``/``*.stp``/``*.STEP``/``*.STP`` under ``<case>`` then ``<case>/cad/`` (sorted) | ``ai_review.py:342-356`` | ``advisor_stack.py:898-911`` ⇒ ``unit_detector.detect_unit(step_path=…)`` |
| ``bbox_max_extent_raw`` | ``max(dx,dy,dz)`` from ``cad/bbox.json`` ``bbox`` (6-tuple); ``manifest.json`` fallback | ``ai_review.py:505-531`` arithmetic (REPLACE HTTPException → ``return None``) | ``advisor_stack.py:901-902`` ⇒ ``detect_unit(bbox_max_extent_raw=…)`` |
| ``body_extents_raw`` | ``cad/bbox.json`` ``extents`` list; ``manifest.json`` fallback | ``ai_review.py:380-401`` | ``advisor_stack.py:903-904`` ⇒ ``detect_unit(body_extents_raw=…)`` |
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

__all__ = ["extract", "StepArtifacts"]


# ----------------------------------------------------------------------
# StepArtifacts — return shape.
# ----------------------------------------------------------------------
# Frozen dataclass (mirrors sibling DEC-V61-211 / -213 style). All three
# fields are independently Optional so callers can detect partial source
# coverage per the DRAFT §Truth-chain R2 per-field honest-omission
# contract.
#
# Drift risk: NONE today (no upstream class to drift against). When a
# future advisor consumes ``StepArtifacts`` directly, a parity canary
# can be added at that point (mirror DEC-211 R0 P1 pattern). Today the
# consumer (``unit_detector.detect_unit``) accepts three loose kwargs,
# so the dataclass is local-only and the extractor's __init__.py export
# layer just unpacks the fields.
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class StepArtifacts:
    """STEP path + pre-staged geometry metadata for one case dir.

    Each field is independently Optional. A returned ``StepArtifacts``
    with ``step_path is None`` AND both bbox/extents None is collapsed
    to a top-level ``None`` by ``extract`` (see module docstring) — so
    if ``extract`` returns a ``StepArtifacts`` instance, ``step_path``
    is guaranteed non-None. The bbox and extents fields may
    independently be None on per-field honest omission.

    See DEC-V61-214 §"v0.1 scope" + §Truth-chain R2.
    """

    step_path: str | None = None
    bbox_max_extent_raw: float | None = None
    body_extents_raw: list[float] | None = None


# ----------------------------------------------------------------------
# STEP path discovery — lifted from ai_review.py:_autodiscover_step.
# ----------------------------------------------------------------------
# Per-suffix sorted() iteration (NOT a concatenated glob over all four
# suffixes). On case-insensitive filesystems (HFS+ / APFS default) a
# concatenated glob like ``sub.glob('*.step')`` followed by
# ``sub.glob('*.STEP')`` could match the same physical file twice; the
# per-suffix iteration here yields each suffix bucket independently and
# the first hit per outer (root vs cad) wins, so case-insensitivity
# cannot cause double-yield. DRAFT §Codex review line 128-131
# pre-empt; pinned by ``test_sort_determinism_case_insensitive_filesystem``.
# ----------------------------------------------------------------------
_STEP_SUFFIX_PATTERNS: tuple[str, ...] = ("*.step", "*.stp", "*.STEP", "*.STP")


def _discover_step_path(case_dir: Path) -> str | None:
    """Find the first STEP file under ``case_dir`` then ``case_dir/cad/``.

    Returns the absolute path string (JSON-safe), or None when no STEP
    file is found in either of the two allowed locations.

    NO recursion: only the immediate contents of ``case_dir`` and
    ``case_dir/cad/`` are inspected. The ``.venv/`` / ``node_modules/``
    no-recursion contract (DRAFT §Truth-chain risks #3) is enforced
    structurally by not using ``**`` in the glob and not iterating
    subdirectories.
    """
    for sub in (case_dir, case_dir / "cad"):
        if not sub.is_dir():
            continue
        for suffix in _STEP_SUFFIX_PATTERNS:
            for p in sorted(sub.glob(suffix)):
                if p.is_file():
                    return str(p.resolve())
    return None


# ----------------------------------------------------------------------
# bbox / extents discovery — lifted from ai_review.py:_autodiscover_geometry_metadata.
# ----------------------------------------------------------------------
# Search order (first hit wins per field, manifest.json is a FALLBACK
# only — it does NOT override an existing cad/bbox.json field). DRAFT
# §Codex review line 132-133 pre-empt; pinned by
# ``test_manifest_does_not_override_cad_bbox``.
# ----------------------------------------------------------------------
def _load_json_dict(path: Path) -> dict | None:
    """Read a JSON file as a dict; return None on any failure.

    All failure modes (missing file, JSONDecodeError, UnicodeDecodeError,
    top-level non-dict, OSError on read) collapse to None — silent
    per-field honest omission is the contract.

    Codex CRS R0 P3 carry-forward: ``read_text(encoding="utf-8")`` raises
    ``UnicodeDecodeError`` (a subclass of ``ValueError``, not ``OSError``)
    on non-UTF-8 bytes. Externally generated or partially corrupted
    metadata MUST collapse to silent omission — never raise out to the
    eval caller — so ``UnicodeDecodeError`` is caught alongside ``OSError``.
    """
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _compute_bbox_max_extent(bbox: object) -> float | None:
    """Compute ``max(dx, dy, dz)`` from a 6-tuple bbox. None on any failure.

    Lifted from ``ai_review.py:_bbox_max_extent`` at :505-531 BUT with
    every HTTPException(400) path replaced by ``return None`` — the
    extractor's transport model is silent honest omission, not HTTP
    error (DRAFT §v0.1 In line 53-54).

    DEC-V61-213 R1 carry-forward: when the ``bbox`` key is structurally
    present but unparseable as the expected shape (arity ≠ 6 / non-list
    / non-numeric element), the field collapses to None. This shape-
    transfers the R1 "key present but ambiguous → honest refuse" lesson
    from regex-based keys to JSON-key-presence checks.

    Adversarial guard (DEC-V61-214 R1 carry-forward — NaN/Inf
    contagion): ``json.loads`` is permissive by default and accepts
    JS-style ``NaN`` / ``Infinity`` / ``-Infinity`` literals, which
    ``float()`` then silently propagates. ``max(nan, ...)`` returns
    ``nan``, which would silently mis-bucket the downstream
    ``unit_detector`` threshold comparisons (every comparison against
    nan is False). Honest-omission contract: non-finite element ⇒
    refuse the whole field (return None), do NOT pass through.
    """
    if not isinstance(bbox, list):
        return None
    if len(bbox) != 6:
        return None
    try:
        vals = [float(x) for x in bbox]
    except (TypeError, ValueError, OverflowError):
        return None
    if not all(math.isfinite(v) for v in vals):
        return None
    return max(vals[3] - vals[0], vals[4] - vals[1], vals[5] - vals[2])


def _coerce_extents(extents: object) -> list[float] | None:
    """Coerce the ``extents`` JSON value to ``list[float]``. None on failure.

    Honest omission contract:
      - non-list → None,
      - any element not coercible to float → None (whole field, not
        partial),
      - any element non-finite (``nan`` / ``+inf`` / ``-inf``) → None
        (whole field). Parity with ``_compute_bbox_max_extent`` per
        DEC-V61-214 R1 adversarial finding: ``json.loads`` accepts
        JS-style ``NaN`` / ``Infinity`` literals and would otherwise
        contaminate downstream ``unit_detector`` threshold
        comparisons (every comparison against nan is False).
    """
    if not isinstance(extents, list):
        return None
    try:
        vals = [float(x) for x in extents]
    except (TypeError, ValueError, OverflowError):
        return None
    if not all(math.isfinite(v) for v in vals):
        return None
    return vals


def _discover_geometry_metadata(
    case_dir: Path,
) -> tuple[float | None, list[float] | None]:
    """Return ``(bbox_max_extent_raw, body_extents_raw)`` for ``case_dir``.

    Search order (first hit wins per field):
      1. ``<case_dir>/cad/bbox.json``  → ``bbox`` / ``extents``
      2. ``<case_dir>/manifest.json``  → ``bbox`` / ``extents`` (fallback only)

    Each field is resolved independently — a ``cad/bbox.json`` with a
    valid ``extents`` list but a malformed ``bbox`` key yields
    ``(None, [...])``, NOT a whole-pair refusal.
    """
    bbox_max: float | None = None
    extents: list[float] | None = None

    # Track per-field KEY-PRESENCE in cad/bbox.json (DEC-V61-213 R1
    # carry-forward + Codex CRS R0 P2 R1 fix). When the cad/bbox.json
    # key is structurally PRESENT but the value is malformed (arity ≠ 6,
    # non-numeric, non-finite, non-list), the per-field value collapses
    # to None — but the manifest.json fallback MUST NOT then overwrite
    # that None with a stale manifest value. "Key present but malformed
    # in primary source" is an HONEST OMISSION, not a "field absent"
    # signal. Conflating the two would let stale manifest values
    # silently mask a real bug in the freshly written cad/bbox.json,
    # which is exactly the contagion DEC-213 R1 was designed to prevent.
    cad_bbox_key_present = False
    cad_extents_key_present = False

    cad_doc = _load_json_dict(case_dir / "cad" / "bbox.json")
    if cad_doc is not None:
        if "bbox" in cad_doc:
            cad_bbox_key_present = True
            bbox_max = _compute_bbox_max_extent(cad_doc.get("bbox"))
        if "extents" in cad_doc:
            cad_extents_key_present = True
            extents = _coerce_extents(cad_doc.get("extents"))

    # manifest.json fallback — ONLY for fields whose KEY is absent
    # from cad/bbox.json. A present-but-malformed cad/bbox.json key
    # stays as honest None (silent-stale-data refusal · Codex CRS R0 P2).
    need_manifest_bbox = bbox_max is None and not cad_bbox_key_present
    need_manifest_extents = extents is None and not cad_extents_key_present
    if need_manifest_bbox or need_manifest_extents:
        manifest_doc = _load_json_dict(case_dir / "manifest.json")
        if manifest_doc is not None:
            if need_manifest_bbox and "bbox" in manifest_doc:
                bbox_max = _compute_bbox_max_extent(manifest_doc.get("bbox"))
            if need_manifest_extents and "extents" in manifest_doc:
                extents = _coerce_extents(manifest_doc.get("extents"))

    return bbox_max, extents


# ----------------------------------------------------------------------
# Public entry point.
# ----------------------------------------------------------------------
def extract(case_dir: Path) -> StepArtifacts | None:
    """Read CAD artifacts from ``case_dir`` → ``StepArtifacts | None``.

    Returns ``None`` when ``step_path`` cannot be resolved — bbox and
    extents are useless to the downstream consumer
    (``assemble_stack`` gates ``unit_detector`` dispatch on
    ``step_path is not None``), so the cleanest contract is to collapse
    the entire result to ``None`` rather than emit a ``StepArtifacts``
    with a non-None bbox but absent step_path.

    Otherwise returns a ``StepArtifacts`` with ``step_path`` populated
    and ``bbox_max_extent_raw`` / ``body_extents_raw`` independently
    populated or ``None`` per the honest-omission contract.

    Per DEC-V61-130/132, this function is **read-only** — only file
    existence checks, ``Path.glob``, and ``Path.read_text`` are used;
    no writes, no route, no mutation, no recursion into vendored
    directories, no opening of the ``.step`` file itself.
    """
    step_path = _discover_step_path(case_dir)
    if step_path is None:
        return None

    bbox_max, extents = _discover_geometry_metadata(case_dir)

    return StepArtifacts(
        step_path=step_path,
        bbox_max_extent_raw=bbox_max,
        body_extents_raw=extents,
    )
