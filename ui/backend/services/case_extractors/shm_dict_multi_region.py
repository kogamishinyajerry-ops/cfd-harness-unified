"""shm_dict_multi_region · multi-region sHM extractor (v0.1).

Per DEC-V61-217 W3.0.1. Wraps the single-region ``shm_dict_extractor`` to
produce a ``Mapping[str, RegionShmSnapshot | None]`` keyed by every region
named in a ``RegionPropertiesSnapshot``.

## Resolved topology (P2-close lesson 1 carry-forward)

Real ``chtMultiRegionSimpleFoam`` / ``chtMultiRegionFoam`` cases use ONE master
``system/snappyHexMeshDict`` that meshes the whole assembly.  Per-region
cellZone tagging is done via ``castellatedMeshControls.refinementSurfaces``
(each surface entry carries ``cellZone <name>; cellZoneInside inside|insidePoint``
etc.) and/or the top-level ``locationsInMesh`` / ``locationInMesh`` paren list.
``splitMeshRegions -cellZones`` then carves the physical regions.  There is NO
per-region ``system/<region>/snappyHexMeshDict`` file in any corpus case
(verified 2026-05-30 survey); the extractor does NOT attempt to locate such a
file.

**case_002b note**: 6 of the 7 declared solid regions were built via
``topoSet`` + ``extrudeToRegionMesh``, NOT via sHM.  For those regions the
master sHM carries no ``refinementSurface`` entry, so this extractor honestly
returns ``None`` per region (extruded — no sHM).  The charter passes-criterion
"7 region-keyed snapshots" is satisfied as "7 keys, possibly several ``None``",
not "7 populated snapshots".

## V90 + V92 handling

*V90* — ``locationsInMesh`` form: ``castellatedMeshControls`` uses a list of
``( (x y z) zoneName )`` pairs instead of a single ``locationInMesh (x y z)``.
This extractor parses the list and maps each ``zoneName`` to its declared seed
point, stored in ``RegionShmSnapshot.seed_point``.

*V92* — ``cellZoneInside`` heterogeneity: a single sHM can mix ``inside`` (ray-
cast), ``insidePoint`` (flood-fill from a declared seed), and ``outside`` (the
complement zone) across different regions.  This extractor surfaces the exact
mode token in ``RegionShmSnapshot.cell_zone_inside_mode`` so downstream V92
validators can distinguish per-region topology.

## Per-region snapshot shape (``RegionShmSnapshot``)

Each region name is present in the output mapping (the ``RegionPropertiesSnapshot``
is the authoritative source of region names).  Its value is:

  - ``None``                   — region name has no entry in ``refinementSurfaces``
                                  AND no ``locationsInMesh`` seed (honest "no sHM
                                  for this region — likely extruded or config gap")
  - ``RegionShmSnapshot(...)`` — the region IS referenced in the master sHM; the
                                  snapshot fields carry what the sHM declares
                                  (each independently optional per DEC-V61-213)

``RegionShmSnapshot`` fields (each **independently OPTIONAL**; absent in source
⇒ field ``None``, NOT fabricated):

  - ``cell_zone``             : ``str | None``  — ``cellZone`` token from
                                ``refinementSurfaces.<name>``
  - ``cell_zone_inside_mode`` : ``str | None``  — ``cellZoneInside`` mode
                                (``"inside"`` / ``"insidePoint"`` / ``"outside"`` /
                                ``None`` if not declared)
  - ``inside_point``          : ``tuple[float, float, float] | None``  — seed
                                declared in ``insidePoint ( x y z )``
  - ``seed_point``            : ``tuple[float, float, float] | None``  — seed
                                from the ``locationsInMesh`` or ``locationInMesh``
                                list entry for this zone
  - ``location_syntax``       : ``"locationsInMesh"`` | ``"locationInMesh"`` | ``None``
  - ``patch_info_type``       : ``str | None``  — ``patchInfo.type`` token, if
                                present in the refinementSurface block

  - ``surface_present``       : ``bool``  — whether a ``refinementSurfaces``
                                entry declares ``cellZone == <this region>``
                                (True even when no other field is declared —
                                DEC-V61-213 presence-vs-payload axis)
  - ``location_seed_present`` : ``bool``  — whether a ``locationsInMesh`` or
                                ``locationInMesh`` seed entry exists for this
                                region name

## Top-level output

``extract(case_dir, region_snapshot)``
  → ``Mapping[str, RegionShmSnapshot | None] | None``

Returns ``None`` (cannot even start the per-region map) when:
  - ``region_snapshot`` is ``None`` (caller could not build a snapshot),
  - both ``fluid_regions`` AND ``solid_regions`` are ``None`` on the snapshot
    (``Snapshot(None, None)`` — no region names to iterate; distinguish from
    an empty but parseable snapshot),
  - the master ``system/snappyHexMeshDict`` is missing/unreadable (no master
    sHM → no cellZone evidence for any region),
  - the master sHM produces ``None`` from ``shm_dict_extractor.extract()``
    (no recognizable block — honest refusal).

When ``region_snapshot`` is valid but regions tuple(s) are empty ``()``, the
output mapping is ``{}`` (zero regions to iterate).

## Scope-locked NON-features

  - Per-region ``system/<region>/snappyHexMeshDict``: NOT a real OpenFOAM
    convention in the corpus (verified 2026-05-30).  This extractor will NOT
    attempt to read such a file.  If one exists it is silently ignored.
  - ``#include`` directives in the master sHM: the single-region
    ``shm_dict_extractor`` scope-locks these out; so does this wrapper.
  - Macro substitution (``$macroName``): inherited scope-lock from
    ``shm_dict_extractor``.
  - Numeric quantitative values (``level``, ``nSurfaceLayers``, etc.): extracted
    by this module only where they are seed-point coordinates in
    ``locationsInMesh`` / ``insidePoint``; sizing values are NOT extracted.
  - **Only ``fluid`` + ``solid`` regions are iterated** — exactly those the
    ``RegionPropertiesSnapshot`` (W3.0 / DEC-V61-218) carries. That reader is
    scope-locked to the ``fluid`` and ``solid`` groups; a non-CHT group such as
    ``porous`` in ``regionProperties`` is NOT surfaced by W3.0 and therefore
    never reaches this wrapper — such regions do NOT appear in the output. This
    is an inherited boundary from DEC-V61-218's fluid/solid-only scope, NOT a
    silent drop introduced here (Codex R1 2026-05-30 P2: docstring corrected —
    it previously and wrongly claimed non-CHT groups "pass through transparently"
    via a field the upstream snapshot does not carry).
  - ``snapControls`` / ``meshQualityControls``: not extracted (mirrors
    ``shm_dict_extractor`` scope-lock).
  - Ambiguous source → honest ``None`` refusal (DEC-V61-218 discipline), NOT a
    first/last-match guess, in either of two cases: two ``refinementSurfaces``
    entries declaring the SAME ``cellZone <region>`` token, OR the same zone name
    appearing twice in ``locationsInMesh`` (Codex R1 2026-05-30 P2).
  - ``locationsInMesh`` syntax-vs-topology mismatch flag (≥2 STL geometries +
    list-form seeds): NOT surfaced as a boolean in v0.1; the raw evidence
    (``location_syntax`` + per-region ``seed_point``) is available to a caller.
    Deferred to a follow-on sub-DEC.
  - Legacy singular ``locationInMesh ( x y z )`` is ONE global seed, not
    per-region; ``location_syntax`` is recorded as ``"locationInMesh"`` but the
    global seed is NOT replicated into each region's ``seed_point`` (a per-region
    seed comes only from a ``locationsInMesh`` list entry or an ``insidePoint``).

## Region→surface association is by cellZone token, NOT entry name

A ``refinementSurfaces`` entry is named after its STL/geometry; the REGION it
tags is named by the ``cellZone <region>;`` token inside the entry body. These
need not be equal (red-team 2026-05-30 P1). This extractor maps a region to its
sHM info by matching the region name against ``cellZone`` tokens, so a case
whose geometry name differs from its region name (e.g. case_016) is handled
correctly. A surface declaring no ``cellZone`` token tags no region.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .region_properties_reader import RegionPropertiesSnapshot
from .shm_dict_extractor import (
    _find_matching_close,
    _find_nested_block,
    _find_paren_list,
    _find_top_level_block,
    _strip_comments,
    _strip_quotes_and_parens,
)

__all__ = ["extract", "RegionShmSnapshot"]


# ---------------------------------------------------------------------------
# Per-region snapshot dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegionShmSnapshot:
    """Per-region sHM snapshot derived from the master ``snappyHexMeshDict``.

    Per DEC-V61-213 key-presence-vs-payload-completeness: each field is
    independently optional (``None`` = not declared in source; absent in
    source ⇒ ``None``, NOT fabricated).

    NEW dataclass (no upstream equivalent) per DEC-V61-217 W3.0.1. Drift
    risk: NONE today (no upstream consumer class). If a future advisor
    consumes ``RegionShmSnapshot`` directly, a mirror-parity canary would
    be added at that point.
    """

    # Presence flags (independent of payload completeness per DEC-V61-213)
    surface_present: bool = False
    location_seed_present: bool = False

    # refinementSurfaces-derived fields
    cell_zone: str | None = None
    cell_zone_inside_mode: str | None = None
    inside_point: tuple[float, float, float] | None = None
    patch_info_type: str | None = None

    # locationsInMesh / locationInMesh seed
    seed_point: tuple[float, float, float] | None = None
    location_syntax: str | None = None


# ---------------------------------------------------------------------------
# Regex helpers for cellZone / cellZoneInside / insidePoint extraction
# ---------------------------------------------------------------------------

_CELL_ZONE_RE = re.compile(r"(?ms)\bcellZone\s+([^\s;{}]+)\s*;")
_CELL_ZONE_INSIDE_RE = re.compile(r"(?ms)\bcellZoneInside\s+([^\s;{}]+)\s*;")

# Three-float coordinate pattern: `( f f f )` where each float may be
# an integer, a decimal, or scientific notation (e.g. 1.5e-3, -0.5).
_FLOAT_RE = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
_XYZ_PAREN_RE = re.compile(
    r"\(\s*(" + _FLOAT_RE + r")\s+(" + _FLOAT_RE + r")\s+(" + _FLOAT_RE + r")\s*\)"
)


def _parse_xyz(text: str) -> tuple[float, float, float] | None:
    """Extract the first ``( x y z )`` triple from *text*.

    Returns a ``(float, float, float)`` tuple on success, ``None`` if no
    well-formed triple is found or the values cannot be cast to float.
    """
    m = _XYZ_PAREN_RE.search(text)
    if m is None:
        return None
    try:
        return (float(m.group(1)), float(m.group(2)), float(m.group(3)))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# refinementSurfaces block — per-region cell-zone parser
# ---------------------------------------------------------------------------

def _find_depth0_block(body: str, key: str) -> tuple[int, int] | None:
    """Find ``<key> { ... }`` at **brace-depth 0** of *body*; return inner span.

    Brace-depth-aware, UNLIKE ``shm_dict_extractor._find_top_level_block`` (which
    is only line-anchored ``^\\s*key\\s*{`` and so still matches a ``key {`` that
    sits indented inside a nested sub-block — Codex R0 2026-05-30 P2). A
    ``key`` token appearing inside a nested ``{ ... }`` is skipped. Returns the
    inner-body span ``(one-past-opening-brace, matching-close)`` or ``None``.
    """
    key_re = re.compile(r"\b" + re.escape(key) + r"\b")
    depth = 0
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c == "{":
            depth += 1
            i += 1
            continue
        if c == "}":
            if depth > 0:
                depth -= 1
            i += 1
            continue
        if depth == 0:
            m = key_re.match(body, i)
            if m is not None:
                j = m.end()
                while j < n and body[j].isspace():
                    j += 1
                if j < n and body[j] == "{":
                    close = _find_matching_close(body, j + 1, "{", "}")
                    if close is not None:
                        return (j + 1, close)
                i = m.end()
                continue
        i += 1
    return None


def _top_level_only(body: str) -> str:
    """Return *body* with every balanced ``{ ... }`` span removed, leaving only
    depth-0 text.

    Used so a ``cellZone`` / ``cellZoneInside`` / ``insidePoint`` declared inside
    a nested ``regions { ... }`` (per-surface-region) sub-block cannot leak into
    the surface's own scan and fabricate a region→cellZone mapping (red-team
    2026-05-30 P2). Paren ``( ... )`` lists (e.g. ``insidePoint (x y z)``) are
    preserved; only brace-delimited sub-blocks are stripped.
    """
    out: list[str] = []
    depth = 0
    for ch in body:
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _parse_region_surface_info(
    surf_body: str,
) -> dict[str, Any]:
    """Extract cellZone, cellZoneInside, insidePoint, patchInfo.type from a
    single ``refinementSurfaces.<name> { ... }`` body.

    Returns a dict with keys present only if declared (DEC-V61-213). The
    cellZone / cellZoneInside / insidePoint scans run over TOP-LEVEL text only
    (nested ``{ ... }`` sub-blocks stripped) so a value declared inside a
    nested ``regions { ... }`` sub-block cannot leak (red-team 2026-05-30 P2).
    """
    info: dict[str, Any] = {}

    # Depth-0 scan: a cellZone/cellZoneInside/insidePoint inside a nested
    # `regions { ... }` sub-block must NOT be attributed to this surface.
    top = _top_level_only(surf_body)

    m = _CELL_ZONE_RE.search(top)
    if m:
        info["cell_zone"] = _strip_quotes_and_parens(m.group(1))

    m = _CELL_ZONE_INSIDE_RE.search(top)
    if m:
        info["cell_zone_inside_mode"] = _strip_quotes_and_parens(m.group(1))

    # insidePoint ( x y z ) — optional seed for insidePoint mode (top-level only)
    ip_raw = _find_paren_list(top, "insidePoint")
    if ip_raw is not None:
        xyz = _parse_xyz("(" + ip_raw + ")")
        if xyz is not None:
            info["inside_point"] = xyz

    # patchInfo.type — the surface's OWN patchInfo block at brace-depth 0 (a
    # patchInfo buried inside a nested regions{} sub-block must NOT leak; Codex
    # R0 2026-05-30 P2 — `_find_top_level_block` is line-anchored, not
    # depth-aware, so use the depth-aware finder).
    pi_span = _find_depth0_block(surf_body, "patchInfo")
    if pi_span is not None:
        pi_inner = surf_body[pi_span[0]:pi_span[1]]
        type_m = re.search(r"\btype\s+([^\s;]+)\s*;", pi_inner)
        if type_m:
            info["patch_info_type"] = _strip_quotes_and_parens(type_m.group(1))

    return info


def _extract_all_refinement_surfaces(
    cmc_inner: str,
) -> dict[str, dict[str, Any]] | None:
    """Walk ``refinementSurfaces { <name> { ... } ... }`` and return a mapping
    of surface-name → per-region info dict.

    Returns ``None`` if the ``refinementSurfaces`` block is absent.
    Returns ``{}`` if the block is empty.
    """
    span = _find_nested_block(cmc_inner, "refinementSurfaces")
    if span is None:
        return None
    inner = cmc_inner[span[0]:span[1]]

    surfaces: dict[str, dict[str, Any]] = {}
    i = 0
    n = len(inner)
    while i < n:
        # Skip whitespace
        while i < n and inner[i].isspace():
            i += 1
        if i >= n:
            break
        # Read name token
        j = i
        while j < n and not inner[j].isspace() and inner[j] != "{":
            j += 1
        if j == i:
            i += 1
            continue
        name = inner[i:j]
        i = j
        # Skip whitespace to `{`
        while i < n and inner[i].isspace():
            i += 1
        if i >= n or inner[i] != "{":
            continue
        i += 1
        close = _find_matching_close(inner, i, "{", "}")
        if close is None:
            break
        surf_body = inner[i:close]
        surfaces[name] = _parse_region_surface_info(surf_body)
        i = close + 1
    return surfaces


# ---------------------------------------------------------------------------
# locationsInMesh / locationInMesh parsing
# ---------------------------------------------------------------------------

def _parse_locations_in_mesh(
    cmc_inner: str,
) -> tuple[dict[str, tuple[float, float, float]], str, set[str]] | None:
    """Parse ``locationsInMesh ( ((x y z) zoneName) ... )`` V90 form.

    Returns ``(zone_name → seed_point, "locationsInMesh", duplicate_zones)`` or
    ``None``. Each entry is ``( (x y z) zoneName )`` — the inner list contains
    pairs: a ``( x y z )`` triple then a bare zone-name token.

    *duplicate_zones* is the set of zone names that appear more than once: an
    ambiguous seed source (Codex R1 2026-05-30 P2). The caller refuses (``None``)
    for those regions rather than silently keeping an arbitrary last-wins seed,
    mirroring the duplicate-``cellZone`` refusal.
    """
    raw = _find_paren_list(cmc_inner, "locationsInMesh")
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return ({}, "locationsInMesh", set())

    result: dict[str, tuple[float, float, float]] = {}
    duplicate_zones: set[str] = set()
    i = 0
    n = len(stripped)
    while i < n:
        while i < n and stripped[i].isspace():
            i += 1
        if i >= n:
            break
        if stripped[i] != "(":
            # Not an entry opener — skip token
            j = i
            while j < n and not stripped[j].isspace() and stripped[j] not in ("(", ")"):
                j += 1
            i = j if j > i else i + 1
            continue
        # Consume the outer `(`
        i += 1
        close = _find_matching_close(stripped, i, "(", ")")
        if close is None:
            break
        entry_body = stripped[i:close]
        i = close + 1
        # Within the entry body: expect `( x y z ) zoneName`. Extract the
        # trailing zone-name token FIRST so a malformed-coords entry that still
        # names a zone is REFUSED (zone added to duplicate_zones → caller emits
        # None for that region) rather than silently dropped — a silent drop
        # reads downstream as honest absence, indistinguishable from an extruded
        # region (Codex R2 2026-05-30 P3).
        eb = entry_body.strip()
        name_m = re.search(r"([A-Za-z_]\w*)\s*$", eb)
        zone_name = name_m.group(1) if name_m is not None else None
        xyz = _parse_xyz(eb)
        if zone_name is None:
            # No attributable trailing zone token — cannot refuse a region we
            # cannot name. Documented scope-out (rare; the common typo is bad
            # coords WITH a name, handled below).
            continue
        if xyz is None:
            # Named zone but unparseable coords → malformed seed → refuse.
            duplicate_zones.add(zone_name)
            continue
        if zone_name in result:
            duplicate_zones.add(zone_name)
        result[zone_name] = xyz
    return result, "locationsInMesh", duplicate_zones


def _parse_location_in_mesh(
    cmc_inner: str,
) -> tuple[tuple[float, float, float], str] | None:
    """Parse legacy ``locationInMesh ( x y z )`` (singular) form.

    Returns ``(xyz_tuple, "locationInMesh")`` or ``None``.
    This is a global discard point, not per-region — callers use this
    only to detect the syntax form; per-region seeds are from
    ``insidePoint`` declarations inside ``refinementSurfaces``.
    """
    raw = _find_paren_list(cmc_inner, "locationInMesh")
    if raw is None:
        return None
    xyz = _parse_xyz("(" + raw + ")")
    if xyz is None:
        return None
    return xyz, "locationInMesh"


# ---------------------------------------------------------------------------
# Public extract entry-point
# ---------------------------------------------------------------------------

def extract(
    case_dir: Path,
    region_snapshot: RegionPropertiesSnapshot | None,
) -> Mapping[str, RegionShmSnapshot | None] | None:
    """Read the master ``system/snappyHexMeshDict`` and yield per-region snapshots.

    Parameters
    ----------
    case_dir:
        The root of the OpenFOAM case directory.
    region_snapshot:
        A ``RegionPropertiesSnapshot`` from ``region_properties_reader.extract()``.
        Drives the region iteration (authoritative for region names).

    Returns
    -------
    ``None``
        When: *region_snapshot* is ``None``; or both ``fluid_regions`` and
        ``solid_regions`` on the snapshot are ``None`` (``Snapshot(None, None)``,
        meaning the source ``regions ()`` entry was not populated with any
        group); or the master ``system/snappyHexMeshDict`` is missing /
        unreadable / yields no recognizable blocks.

    ``{}`` (empty mapping)
        When the snapshot has no region names (both tuples are empty ``()``).

    ``{region_name → RegionShmSnapshot | None}``
        One key per region from ``fluid_regions + solid_regions``.  ``None``
        value = this region has no ``refinementSurfaces`` entry AND no
        ``locationsInMesh`` seed in the master sHM (honest "no sHM for this
        region — likely extruded or topology gap").

    Per DEC-V61-130/132: **read-only** — ``Path.read_text`` is the sole I/O.
    No writes, no globals, no mutation.
    """
    # --- Guard: need a valid snapshot with at least one group declared ---
    if region_snapshot is None:
        return None
    if (
        region_snapshot.fluid_regions is None
        and region_snapshot.solid_regions is None
    ):
        # Snapshot(None, None) — no group was declared at all; cannot derive
        # any region names.  Honest refusal per DEC-V61-218 lesson.
        return None

    # Build the ordered list of all region names from the snapshot.
    all_regions: list[str] = list(
        (region_snapshot.fluid_regions or ())
        + (region_snapshot.solid_regions or ())
    )
    # Empty tuples → zero regions → return an empty mapping (not None).
    if not all_regions:
        return {}

    # --- Read the master sHM file directly ---
    # Do NOT gate on the single-region `shm_dict_extractor.extract()`: it returns
    # None for a sHM that declares no `refinementSurfaces`/`refinementRegions`,
    # which would wrongly reject valid **V90 `locationsInMesh`-only (seed-only)**
    # cases (Codex R2 2026-05-30 P2). Gate instead on file-exists + a parseable
    # `castellatedMeshControls` block — that block is where BOTH refinementSurfaces
    # AND the locationsInMesh seeds live, so its presence is the honest liveness
    # signal for per-region evidence.
    shm_path = case_dir / "system" / "snappyHexMeshDict"
    if not shm_path.is_file():
        return None
    try:
        raw = shm_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    body = _strip_comments(raw)

    cmc_span = _find_top_level_block(body, "castellatedMeshControls")
    if cmc_span is None:
        # No castellatedMeshControls block → no per-region sHM evidence at all
        # (neither surfaces nor seeds) → honest refusal.
        return None
    cmc_inner: str = body[cmc_span[0]:cmc_span[1]]

    # --- Parse refinementSurfaces, then RE-INDEX by cellZone token ---
    # A refinementSurfaces entry is named after the STL/geometry; the REGION it
    # tags is named by its `cellZone <region>;` token. The entry name need NOT
    # equal the region name (red-team 2026-05-30 P1: keying by entry name
    # mis-maps cases like case_016 where geometry name != cellZone). Index by
    # the cellZone token so region lookup is by region identity. A surface with
    # NO cellZone token tags no region and is dropped (cannot fabricate). Two
    # surfaces claiming the same cellZone → ambiguous → that region refuses.
    surf_map = _extract_all_refinement_surfaces(cmc_inner)
    cellzone_to_info: dict[str, dict[str, Any]] = {}
    duplicate_cellzones: set[str] = set()
    if surf_map:
        for info in surf_map.values():
            cz = info.get("cell_zone")
            if cz is None:
                continue
            if cz in cellzone_to_info:
                duplicate_cellzones.add(cz)
            cellzone_to_info[cz] = info

    # --- Parse locationsInMesh (V90) or locationInMesh (legacy singular) ---
    loc_map: dict[str, tuple[float, float, float]] = {}
    location_syntax: str | None = None
    duplicate_seeds: set[str] = set()

    lim_result = _parse_locations_in_mesh(cmc_inner)
    if lim_result is not None:
        loc_map, location_syntax, duplicate_seeds = lim_result
    else:
        li_result = _parse_location_in_mesh(cmc_inner)
        if li_result is not None:
            # Legacy form: ONE global seed, not per-region.
            # We record the syntax form but no per-region seed from this key.
            location_syntax = li_result[1]

    # Regions with an ambiguous source (a cellZone claimed by two surfaces OR a
    # locationsInMesh zone seeded twice) refuse — DEC-V61-218 honest-refusal.
    ambiguous_regions = duplicate_cellzones | duplicate_seeds

    # --- Build per-region snapshots ---
    result: dict[str, RegionShmSnapshot | None] = {}

    for region_name in all_regions:
        if region_name in ambiguous_regions:
            # Ambiguous source (duplicate cellZone token or duplicate
            # locationsInMesh seed) → honest refusal, NOT a last/first-match guess.
            result[region_name] = None
            continue
        surface_info = cellzone_to_info.get(region_name)
        surface_present = surface_info is not None
        seed_point = loc_map.get(region_name)
        location_seed_present = seed_point is not None

        if not surface_present and not location_seed_present:
            # Honest None: no sHM evidence for this region.
            result[region_name] = None
            continue

        snap = RegionShmSnapshot(
            surface_present=surface_present,
            location_seed_present=location_seed_present,
            cell_zone=surface_info.get("cell_zone") if surface_info else None,
            cell_zone_inside_mode=(
                surface_info.get("cell_zone_inside_mode") if surface_info else None
            ),
            inside_point=surface_info.get("inside_point") if surface_info else None,
            patch_info_type=(
                surface_info.get("patch_info_type") if surface_info else None
            ),
            seed_point=seed_point,
            # location_syntax is a FILE-level property (which seed syntax the
            # master sHM uses) — surface it on every region's snapshot even when
            # this region has no per-region seed, so legacy single-seed
            # `locationInMesh` cases don't silently drop the token (Codex R0
            # 2026-05-30 P2). A None seed_point with a non-None location_syntax
            # is the honest "file uses this syntax; no per-region seed" state.
            location_syntax=location_syntax,
        )
        result[region_name] = snap

    return result
