"""thermo_dict_multi_region · multi-region thermophysicalProperties extractor (v0.1).

Per DEC-V61-217 W3.0.2 (sub-DEC V61-220). Wraps per-region
``constant/<region>/thermophysicalProperties`` reads to produce a
``Mapping[str, RegionThermoSnapshot | None]`` keyed by every region named in a
``RegionPropertiesSnapshot``.

## Honest-refusal checklist (W3.0.2 carry-forward from W3.0.1)

1. **MALFORMED-INPUT**: unbalanced braces / unparseable thermoType → region None.
   Partial transport (key present, value unparseable) → that field None, never
   fabricated; but if the REQUIRED discriminator (thermoType block) is unparseable
   → whole region None.

2. **AMBIGUOUS/DUPLICATE**: duplicate thermoType OR duplicate mixture block in one
   region file → region None (reuse ``_count_top_level_blocks != 1``).  A property
   key appearing twice (e.g. two Cp) → that field None (refuse, don't last-wins)
   — ``_single_match_or_none`` discipline.

3. **NESTING-DEPTH**: every leaf-block scalar scan runs over depth-0 text only.
   The NEW solid helpers and the REUSED single-region leaf scanners
   (``_extract_thermo_model_tags`` / ``_extract_specie_block`` /
   ``_extract_transport_block`` / ``_extract_thermodynamics_block``) all strip
   nested ``{ ... }`` sub-blocks (``_strip_nested_blocks``) before matching, so a
   scalar declared ONLY inside a nested sub-block — including the load-bearing
   ``thermoType.type`` discriminator — is treated as ABSENT at the parent scope
   (field None, or region None for the discriminator), never fabricated. This
   closes the recurring W3.0/W3.0.1 "line-anchored-vs-brace-depth" defect class
   for BOTH the single- and multi-region paths (hardened together in W3.0.2).

4. **NAME-PATTERN-INFERENCE BAN**: ``kind`` comes ONLY from the snapshot (which
   tuple the region is in), NEVER from the region name string or the
   thermoType.type token.  The charter explicitly forbids name-pattern inference.

5. **CROSS-REGION INDEPENDENCE**: one region's malformed/missing file → that
   region None; every OTHER region parses normally.

6. **NO REGION DISCOVERY**: iterate ONLY the snapshot's regions; never enumerate
   the filesystem to discover regions (no fabricated regions).

## Per-region parse path

``constant/<region>/thermophysicalProperties`` is read for each region in
the snapshot (fluid_regions + solid_regions).

- File missing / unreadable (OSError) → region None.
- ``#include`` / ``#includeEtc`` / ``#calc`` / ``#codeStream`` / ``#remove``
  directives: v0.1 scope-out, ENFORCED — any ``#``-directive anywhere in the
  (comment-stripped) file → region None (honest refusal; the included content is
  unseen so the parsed values cannot be claimed complete). SURVEY confirmed zero
  such directives in the 6 scanned in-repo ``thermophysicalProperties`` files;
  the guard exists so a directive sitting inside an otherwise-parseable block is
  not silently skipped (W3.0.2 red-team P2).
- thermoType.type token drives the branch:
    * ``heSolidThermo``              → SOLID branch
    * ``heRhoThermo`` / ``hePsiThermo`` → FLUID branch
    * any other type token           → region None (unsupported model; no
      half-populated snapshot — single rule below)

## Required-field contract (Contract A · single-region symmetry · Codex R1)

A region yields a ``RegionThermoSnapshot`` ONLY when it is a fully-parseable,
SUPPORTED region; otherwise the region is ``None`` (and never poisons sibling
regions — the map is still returned with every region as a key). "Fully
parseable" = valid ``thermoType`` (hConst + pureMixture + a supported ``type``)
+ ``specie.molWeight`` + ``thermodynamics.Cp`` present, AND for FLUID a complete
transport block (``mu``+``Pr`` const, or ``As``+``Ts`` sutherland; an out-of-scope
transport model → region None). These required fields mirror the single-region
``thermo_dict_extractor`` refusal bar, so a malformed/incomplete file is never
reported as successfully parsed. For SOLID, ``kappa`` (constIso) and ``rho``
(rhoConst) are OPTIONAL payload — *forced* by the documented scope-out contracts
(constAnIso / non-rhoConst → snapshot with kappa/rho None), distinguishing
"valid solid, unsupported transport/EOS model" from a flat refusal.

## Branch logic

FLUID branch (heRhoThermo / hePsiThermo):
  Reuse single-region fluid transport helpers for sutherland / const.
  Populates mu/pr OR sutherland_as/sutherland_ts accordingly.

SOLID branch (heSolidThermo):
  New helpers ``_extract_solid_transport_kappa`` + ``_extract_rho_const``.
  constIso → single kappa scalar.
  constAnIso → v0.1 scope-out (kappa vector → kappa None, thermo_type still captured).
  rhoConst → rho extracted.
  Populates cp, hf (optional), mol_weight, kappa, rho.

## kind field

``kind`` is set from snapshot membership ONLY:
  - region in fluid_regions → 'fluid'
  - region in solid_regions → 'solid'
  - region in BOTH (ambiguous duplicate) → None for that region (honest refusal)

## Top-level API

``extract(case_dir, region_snapshot)``
  → ``Mapping[str, RegionThermoSnapshot | None] | None``

Returns ``None`` (cannot even start) when:
  - ``region_snapshot`` is ``None``
  - both ``fluid_regions`` AND ``solid_regions`` are ``None`` (no regions to iterate)

Returns ``{}`` when both tuples are empty ``()``.

Returns ``{region → snapshot_or_none}`` otherwise; every UNIQUE region name in
``fluid_regions ∪ solid_regions`` is a key (presence vs payload independently
optional per DEC-V61-213). A name appearing in BOTH tuples yields exactly one
key mapping to ``None`` (ambiguous kind — undecidable without the banned name
inference).

## Architectural placement

Mirrors DEC-V61-217 W3.0.1 ``shm_dict_multi_region`` exactly: stdlib-only
(``pathlib`` + ``re`` + ``dataclasses`` + ``typing``), pure function,
read-only (one ``Path.read_text`` per region), no route, no mutation, no import
from ``geometry_ingest`` (would pull ``trimesh`` transitively).

``RegionThermoSnapshot`` is a NEW dataclass — no upstream equivalent.
Drift risk: NONE today. If a future advisor consumes it directly, a
mirror-parity canary would be added (DEC-V61-211 R0 P1 pattern).

## Scope-locked NON-features (v0.1)

  - eConst thermo profiles (Cv instead of Cp): region None (inherited from
    single-region thermo_dict_extractor v0.1 scope-out).
  - constAnIso transport (kappa vector for solids): kappa field None, but
    thermo_type still captured.
  - Macro substitution ($var) and #include / #calc / #codeStream: honest
    region None (out-of-grammar for numeric value regex).
  - janaf-polynomial multi-species: region None.
  - Non-pureMixture shapes: region None.
  - Cross-region shared thermophysicalProperties (unusual; region None if
    the file is absent).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .region_properties_reader import RegionPropertiesSnapshot
from .thermo_dict_extractor import (
    ThermoModelTags,
    _count_nested_blocks,
    _count_top_level_blocks,
    _extract_specie_block,
    _extract_thermo_model_tags,
    _extract_transport_block,
    _find_matching_close,
    _find_nested_block,
    _find_top_level_block,
    _parse_float,
    _single_match_or_none,
    _strip_comments,
    _strip_nested_blocks,
    _CP_RE,
    _HF_KEY_PRESENCE_RE,
    _HF_RE,
    _MU_RE,
    _PR_RE,
    _AS_RE,
    _TS_RE,
    _MOL_WEIGHT_RE,
)

__all__ = ["extract", "RegionThermoSnapshot"]


# ---------------------------------------------------------------------------
# Depth-0 text stripping — SHARED with the single-region extractor's leaf
# scanners (``_strip_nested_blocks`` in thermo_dict_extractor.py, hardened
# together in W3.0.2 so the reused thermoType / specie / transport scanners and
# these new solid helpers all enforce the same depth-0 discipline). Aliased
# locally as the name the solid helpers below were written against. Strips every
# balanced ``{ ... }`` sub-block so a scalar key (Cp / kappa / molWeight) inside
# a nested sub-block cannot leak into the parent-block scan — the recurring
# W3.0/W3.0.1 nesting-depth defect class (checklist item 3).
# ---------------------------------------------------------------------------
_depth0_text = _strip_nested_blocks


# ---------------------------------------------------------------------------
# Out-of-grammar directive refusal: any unresolved OpenFOAM preprocessor
# directive (#include / #includeEtc / #calc / #codeStream / #remove / …) means
# the on-disk content is incomplete to us — we cannot honestly claim the parsed
# values are complete. ``#`` is used in OF dicts ONLY for directives, so a ``#``
# followed by a letter is an unambiguous directive marker → region None
# (documented v0.1 scope-out; W3.0.2 red-team P2 — caught a directive sitting
# inside an otherwise-parseable block being silently skipped).
# ---------------------------------------------------------------------------
_DIRECTIVE_RE = re.compile(r"#\s*[A-Za-z]")


# ---------------------------------------------------------------------------
# Kappa regex (constIso solid transport — single isotropic scalar).
# Same boundary discipline as the numeric matchers in thermo_dict_extractor.
# ---------------------------------------------------------------------------
_KEY_LEFT_BOUNDARY = r"(?:^|[\s;{])"
_NUMERIC_VALUE = r"[0-9eE+\-.]+"

_KAPPA_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}kappa\s+({_NUMERIC_VALUE})\s*;")
_KAPPA_KEY_PRESENCE_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}kappa\s")
# "kappa ( ... )" vector form check — used to detect constAnIso scope-out.
# If kappa is followed by a ``(`` before a ``;``, it is a vector (constAnIso).
_KAPPA_VECTOR_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}kappa\s*\(")

_RHO_RE = re.compile(rf"{_KEY_LEFT_BOUNDARY}rho\s+({_NUMERIC_VALUE})\s*;")
_TRANSPORT_TYPE_RE = re.compile(r"(?:^|[\s;{{])\btype\s+(\w+)\s*;")


# ---------------------------------------------------------------------------
# RegionThermoSnapshot frozen dataclass — per-region thermo snapshot.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegionThermoSnapshot:
    """Per-region thermophysicalProperties snapshot.

    Per DEC-V61-213 key-presence-vs-payload-completeness: each property field
    is independently optional (``None`` = absent in source or out of v0.1 scope,
    NOT fabricated).

    NEW dataclass (no upstream equivalent) per DEC-V61-217 W3.0.2 (sub-DEC V61-220).
    Drift risk: NONE today (no upstream consumer class). If a future advisor
    consumes ``RegionThermoSnapshot`` directly, a mirror-parity canary would
    be added at that point (DEC-V61-211 R0 P1 pattern).
    """

    # Discriminator fields (present when thermoType block is parseable)
    thermo_type: str                  # thermoType.type token (e.g. heRhoThermo)
    tags: ThermoModelTags             # full thermoType block 6-token descriptor

    # kind: derived ONLY from snapshot membership — NEVER inferred from name/type
    kind: str | None                  # 'fluid' | 'solid' | None (ambiguous)

    # Common fields (both fluid & solid can carry these)
    mol_weight: float | None = None   # mixture.specie.molWeight
    cp: float | None = None           # mixture.thermodynamics.Cp (hConst)
    hf: float | None = None           # mixture.thermodynamics.Hf (optional)

    # Fluid transport (sutherland OR const — mutually exclusive)
    mu: float | None = None           # const transport
    pr: float | None = None           # const transport
    sutherland_as: float | None = None  # sutherland As
    sutherland_ts: float | None = None  # sutherland Ts

    # Solid transport / EOS (heSolidThermo branch only)
    kappa: float | None = None        # constIso thermal conductivity
    rho: float | None = None          # rhoConst equationOfState


# ---------------------------------------------------------------------------
# New solid-specific helpers (constIso transport + rhoConst EOS)
# ---------------------------------------------------------------------------

def _extract_solid_transport_kappa(mixture_inner: str, transport_kind: str) -> float | None:
    """Extract ``kappa`` scalar from a ``constIso`` ``transport { kappa <v>; }`` block.

    Returns:
      - ``float``         → kappa successfully extracted (constIso branch)
      - ``None`` (scope-out) → declared transport model is NOT ``constIso`` (e.g.
        ``constAnIso`` / ``polynomial`` / any other token), OR kappa is a vector
        ``( x y z )`` (constAnIso shape)
      - ``None`` (absent/dup) → transport block absent or duplicate; kappa key absent,
        duplicate, or unparseable (honest refusal — NOT fabrication)

    **Gate on the DECLARED transport token** (``transport_kind`` = ``tags.transport``),
    symmetric with the fluid branch's strict sutherland/const gating (W3.0.2
    red-team P1): a scalar ``kappa`` under a ``constAnIso`` / ``polynomial``
    declaration must NOT be reported as an isotropic constIso value the file never
    declared. The thermo_type / tags are still captured at the region level,
    preserving the discriminator while honestly refusing the out-of-scope payload.
    """
    if transport_kind != "constIso":
        # Declared model is the documented v0.1 scope-out (constAnIso) or any
        # other transport token: honest kappa None (no fabrication of constIso
        # physics). thermo_type + tags remain captured at the caller.
        return None
    if _count_nested_blocks(mixture_inner, "transport") != 1:
        return None
    span = _find_nested_block(mixture_inner, "transport")
    if span is None:
        return None
    raw_body = mixture_inner[span[0]:span[1]]
    # Depth-0 scan only: strip nested sub-blocks before scalar key matching
    # (nesting-depth checklist item 3).
    body = _depth0_text(raw_body)

    # Belt-and-braces: a constIso block whose kappa is a vector ``( ... )`` is
    # malformed (vector kappa belongs to constAnIso, already gated out above) —
    # refuse rather than mis-read.
    if _KAPPA_VECTOR_RE.search(body):
        return None

    kappa_key_present = bool(_KAPPA_KEY_PRESENCE_RE.search(body))
    if not kappa_key_present:
        return None

    kappa_token = _single_match_or_none(_KAPPA_RE, body)
    if kappa_token is None:
        # Key present but not single-numeric → ambiguous/duplicate/macro → None
        return None
    return _parse_float(kappa_token)


def _extract_rho_const(mixture_inner: str, eos_kind: str) -> float | None:
    """Extract ``rho`` from a ``rhoConst`` ``equationOfState { rho <v>; }`` block.

    **Gate on the DECLARED EOS token** (``eos_kind`` = ``tags.equation_of_state``),
    symmetric with the solid-kappa transport gate (Codex R0 P2#2): a stray ``rho``
    key inside a NON-``rhoConst`` EOS block (e.g. ``polynomial`` / ``PengRobinsonGas``)
    must NOT be reported as a constant-density value the file never declared.

    Returns float on success, None if the EOS model is not ``rhoConst``, or the
    block is absent/dup, or rho is absent/dup/unparseable.
    """
    if eos_kind != "rhoConst":
        # Declared EOS is not constant-density: honest rho None (no fabrication
        # of a rhoConst value from a different model's stray rho key).
        return None
    if _count_nested_blocks(mixture_inner, "equationOfState") != 1:
        return None
    span = _find_nested_block(mixture_inner, "equationOfState")
    if span is None:
        return None
    raw_body = mixture_inner[span[0]:span[1]]
    # Depth-0 scan: strip nested sub-blocks to prevent nested rho from leaking.
    body = _depth0_text(raw_body)
    rho_token = _single_match_or_none(_RHO_RE, body)
    if rho_token is None:
        return None
    return _parse_float(rho_token)


# ---------------------------------------------------------------------------
# Per-region thermodynamics block for hConst (used for both fluid + solid)
# ---------------------------------------------------------------------------

def _extract_hconst_thermodynamics(mixture_inner: str) -> tuple[float | None, float | None] | None:
    """Extract (Cp, Hf) from ``thermodynamics { Cp <v>; Hf <v>; }`` block.

    Returns:
      - ``None``                  → thermodynamics block absent/dup, or Cp is
                                    absent/dup/unparseable (REQUIRED key)
      - ``(cp_float, hf_float)``  → Cp present and parsed; hf is ``None`` when Hf
                                    is absent (optional), honest None when Hf key
                                    is present but ambiguous/unparseable (refusal)

    This function is called for both fluid (heRhoThermo / hePsiThermo with hConst
    thermo) and solid (heSolidThermo with hConst thermo) branches.  Under v0.1,
    only hConst thermo is in-scope; eConst and janaf return None at the caller.

    Nesting-depth discipline (checklist item 3): scalar key scanning runs over
    depth-0 text ONLY (_depth0_text strips nested sub-blocks) so that a ``Cp``
    declared inside a nested sub-block (e.g. ``extra { Cp 999; }``) cannot leak
    to the parent thermodynamics block scan.
    """
    if _count_nested_blocks(mixture_inner, "thermodynamics") != 1:
        return None
    span = _find_nested_block(mixture_inner, "thermodynamics")
    if span is None:
        return None
    raw_body = mixture_inner[span[0]:span[1]]
    # Depth-0 scan: strip nested sub-blocks before scalar key matching.
    body = _depth0_text(raw_body)

    cp_token = _single_match_or_none(_CP_RE, body)
    if cp_token is None:
        return None
    cp = _parse_float(cp_token)
    if cp is None:
        return None

    # Hf is OPTIONAL. If the key appears in any form (including macro or duplicate),
    # it must single-match-numeric or we refuse (DEC-V61-213 / Codex R1 2026-05-30).
    hf: float | None = None
    if bool(_HF_KEY_PRESENCE_RE.search(body)):
        hf_token = _single_match_or_none(_HF_RE, body)
        if hf_token is None:
            # Hf key present but not single-match-numeric → ambiguous → refuse
            return None
        hf = _parse_float(hf_token)
        if hf is None:
            return None

    return (cp, hf)


# ---------------------------------------------------------------------------
# Per-region file parse
# ---------------------------------------------------------------------------

def _parse_region_thermo(
    file_path: Path,
    kind: str | None,
) -> RegionThermoSnapshot | None:
    """Parse ``thermophysicalProperties`` for one region; return snapshot or None.

    ``kind`` is passed in (already resolved from snapshot membership) and is
    stored on the snapshot verbatim — NO inference from file contents or name.
    """
    if not file_path.is_file():
        return None
    try:
        raw = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    body = _strip_comments(raw)

    # --- Out-of-grammar directive refusal (honest region None) ---
    # An unresolved #include / #calc / #codeStream / #remove anywhere in the file
    # means content we cannot see; the parsed values cannot honestly be claimed
    # complete. Refuse the whole region (documented v0.1 scope-out) rather than
    # silently skip the directive line and report a partial snapshot as complete.
    if _DIRECTIVE_RE.search(body):
        return None

    # --- thermoType block ---
    if _count_top_level_blocks(body, "thermoType") != 1:
        return None
    tt_span = _find_top_level_block(body, "thermoType")
    if tt_span is None:
        return None
    tt_inner = body[tt_span[0]:tt_span[1]]
    tags = _extract_thermo_model_tags(tt_inner)
    if tags is None:
        return None

    thermo_type = tags.type  # the thermoType.type token

    # --- v0.1 thermo/mixture scope-out (symmetric with single-region) ---
    # The single-region thermo_dict_extractor returns None for eConst (Cv not Cp)
    # and for non-pureMixture shapes; this wrapper's documented contract promises
    # the same. Refuse the WHOLE region rather than build a half-populated
    # snapshot (mol_weight/transport present, cp None) that a caller could mistake
    # for a successfully-parsed file (Codex R0 P2#1). thermo_type/tags are NOT
    # surfaced for these scope-outs — region None is the honest signal.
    if tags.thermo != "hConst":
        return None
    if tags.mixture != "pureMixture":
        return None

    # --- mixture block ---
    # We need the mixture body for all property extraction.
    if _count_top_level_blocks(body, "mixture") != 1:
        # Whole region None: mixture block absent or duplicate (required for props)
        # But we still captured thermo_type from thermoType — we must return None
        # here because we cannot build a valid snapshot without mixture.
        return None
    mx_span = _find_top_level_block(body, "mixture")
    if mx_span is None:
        return None
    mx_inner = body[mx_span[0]:mx_span[1]]

    # --- specie block → mol_weight (REQUIRED · single-region symmetry) ---
    # molWeight is a required key: the single-region thermo_dict_extractor refuses
    # a file whose specie block is absent/dup or whose molWeight is absent/dup/
    # unparseable. The wrapper must be symmetric → region None (Codex R1 P1), so a
    # malformed/incomplete file stays distinguishable from a valid one (no
    # half-populated snapshot a caller could mistake for a parsed file).
    specie_dict = _extract_specie_block(mx_inner)
    if specie_dict is None:
        return None
    mol_weight: float = specie_dict["molWeight"]

    # --- Branch on thermoType.type token (NOT on kind from snapshot) ---

    if thermo_type == "heSolidThermo":
        return _build_solid_snapshot(
            mx_inner=mx_inner,
            thermo_type=thermo_type,
            tags=tags,
            kind=kind,
            mol_weight=mol_weight,
        )

    if thermo_type in ("heRhoThermo", "hePsiThermo"):
        return _build_fluid_snapshot(
            mx_inner=mx_inner,
            thermo_type=thermo_type,
            tags=tags,
            kind=kind,
            mol_weight=mol_weight,
        )

    # Any other type token is an UNSUPPORTED thermo model: we have no parse
    # branch for its properties, so a snapshot would be half-populated (thermo_type
    # + molWeight, all physics fields None) — exactly the "looks parsed" hazard
    # Codex R1 flagged. Refuse the whole region (consistent single rule: a snapshot
    # is returned ONLY for a fully-parseable SUPPORTED region; otherwise region None).
    return None


def _build_solid_snapshot(
    mx_inner: str,
    thermo_type: str,
    tags: ThermoModelTags,
    kind: str | None,
    mol_weight: float,
) -> RegionThermoSnapshot | None:
    """Build a RegionThermoSnapshot for heSolidThermo branch, or None.

    **Cp is REQUIRED** (single-region symmetry · Codex R1 P1#2): a thermodynamics
    block that is absent/duplicate, or a Cp that is missing/ambiguous → region
    None (a malformed solid thermo file must not look parsed).

    ``kappa`` (constIso transport) and ``rho`` (rhoConst EOS) are OPTIONAL payload
    — this is *forced* by the documented scope-out contracts: a constAnIso /
    polynomial transport or a non-rhoConst EOS yields a snapshot with kappa/rho
    None (so the consumer sees "valid solid, unsupported transport/EOS model")
    rather than a flat refusal. A valid constIso+rhoConst solid populates both.
    """
    # Thermodynamics: hConst → Cp REQUIRED (+ optional Hf). (thermo == hConst is
    # already guaranteed — _parse_region_thermo gated non-hConst to region None.)
    thermo_result = _extract_hconst_thermodynamics(mx_inner)
    if thermo_result is None:
        return None
    cp, hf = thermo_result

    # Transport (optional payload): constIso kappa scalar — gated on the DECLARED
    # token so a scalar kappa under constAnIso/polynomial does not fabricate
    # isotropic physics (None for any non-constIso model).
    kappa = _extract_solid_transport_kappa(mx_inner, tags.transport)

    # EOS (optional payload): rhoConst rho — gated on the DECLARED token so a
    # stray rho under a non-rhoConst EOS model does not fabricate constant density.
    rho = _extract_rho_const(mx_inner, tags.equation_of_state)

    return RegionThermoSnapshot(
        thermo_type=thermo_type,
        tags=tags,
        kind=kind,
        mol_weight=mol_weight,
        cp=cp,
        hf=hf,
        kappa=kappa,
        rho=rho,
    )


def _build_fluid_snapshot(
    mx_inner: str,
    thermo_type: str,
    tags: ThermoModelTags,
    kind: str | None,
    mol_weight: float,
) -> RegionThermoSnapshot | None:
    """Build a RegionThermoSnapshot for heRhoThermo / hePsiThermo branch, or None.

    **Cp AND a complete transport block are REQUIRED** (single-region symmetry ·
    Codex R1 P1#1): the single-region ``_extract_transport_block`` returns None
    when the transport block is absent/duplicate, when ``mu``/``Pr`` (const) or
    ``As``/``Ts`` (sutherland) are incomplete, or when the transport model is an
    out-of-scope kind (polynomial / …). In every such case — plus a missing/
    ambiguous Cp — this wrapper returns region None, so a malformed/incomplete
    fluid thermo file is not reported as successfully parsed.
    """
    mu: float | None = None
    pr: float | None = None
    sutherland_as: float | None = None
    sutherland_ts: float | None = None

    # Thermodynamics: hConst → Cp REQUIRED (+ optional Hf). (thermo == hConst is
    # already guaranteed by the _parse_region_thermo scope-out gate.)
    thermo_result = _extract_hconst_thermodynamics(mx_inner)
    if thermo_result is None:
        return None
    cp, hf = thermo_result

    # Transport REQUIRED: reuse single-region helper (None when absent/dup/
    # incomplete or an out-of-scope transport model) → region None on failure.
    transport_dict = _extract_transport_block(mx_inner, tags.transport)
    if transport_dict is None:
        return None
    if tags.transport == "sutherland":
        sutherland_as = transport_dict.get("As")
        sutherland_ts = transport_dict.get("Ts")
    elif tags.transport == "const":
        mu = transport_dict.get("mu")
        pr = transport_dict.get("Pr")

    return RegionThermoSnapshot(
        thermo_type=thermo_type,
        tags=tags,
        kind=kind,
        mol_weight=mol_weight,
        cp=cp,
        hf=hf,
        mu=mu,
        pr=pr,
        sutherland_as=sutherland_as,
        sutherland_ts=sutherland_ts,
    )


# ---------------------------------------------------------------------------
# Public extract entry-point
# ---------------------------------------------------------------------------

def extract(
    case_dir: Path,
    region_snapshot: RegionPropertiesSnapshot | None,
) -> Mapping[str, RegionThermoSnapshot | None] | None:
    """Read per-region ``constant/<region>/thermophysicalProperties`` files.

    Parameters
    ----------
    case_dir:
        The root of the OpenFOAM case directory.
    region_snapshot:
        A ``RegionPropertiesSnapshot`` from ``region_properties_reader.extract()``.
        Authoritative source for region names and fluid/solid classification.

    Returns
    -------
    ``None``
        When: *region_snapshot* is ``None``; or both ``fluid_regions`` and
        ``solid_regions`` on the snapshot are ``None`` (``Snapshot(None, None)``
        — no region names to iterate; mirrors W3.0.1 guard contract).

    ``{}`` (empty mapping)
        When both tuples are empty ``()``.

    ``{region_name → RegionThermoSnapshot | None}``
        One key per UNIQUE region name in ``fluid_regions ∪ solid_regions``
        (a name listed in both tuples is de-duplicated to a single key).
        Value is ``None`` for a missing/unreadable/unparseable file, for a region
        failing the required-field contract, or for a region that appears in both
        fluid and solid (ambiguous kind); a ``RegionThermoSnapshot`` otherwise
        (with property fields independently optional per DEC-V61-213
        key-presence-vs-payload).

    Per DEC-V61-130/132: **read-only** — ``Path.read_text`` is the only I/O.
    No writes, no globals, no mutation.
    """
    # --- Guard: need a valid snapshot with at least one group declared ---
    if region_snapshot is None:
        return None
    if (
        region_snapshot.fluid_regions is None
        and region_snapshot.solid_regions is None
    ):
        # Snapshot(None, None): no group was declared at all; no region names
        # to iterate. Honest refusal (mirrors shm_dict_multi_region guard).
        return None

    # Build ordered region lists; resolve kind from snapshot membership.
    fluid_set: frozenset[str] = frozenset(region_snapshot.fluid_regions or ())
    solid_set: frozenset[str] = frozenset(region_snapshot.solid_regions or ())

    # All regions in order (fluid first, then solid), DE-DUPLICATED: a name that
    # appears in BOTH tuples must produce exactly ONE map key (Codex R2 P1) — the
    # result dict is keyed by name, so iterating a duplicate twice would silently
    # collapse it and leave the map with fewer keys than the snapshot declared.
    # ``dict.fromkeys`` preserves first-seen order; the in-both name is handled
    # below as ambiguous-kind → None (we do NOT refuse the whole snapshot — one
    # malformed region must not poison its siblings, cross-region independence).
    all_regions: list[str] = list(
        dict.fromkeys(
            (region_snapshot.fluid_regions or ())
            + (region_snapshot.solid_regions or ())
        )
    )
    if not all_regions:
        return {}

    result: dict[str, RegionThermoSnapshot | None] = {}

    for region_name in all_regions:
        in_fluid = region_name in fluid_set
        in_solid = region_name in solid_set

        if in_fluid and in_solid:
            # Ambiguous: appears in BOTH tuples — kind is undecidable without
            # name inference (which is BANNED). Honest None.
            result[region_name] = None
            continue

        kind: str | None = "fluid" if in_fluid else "solid"

        thermo_path = case_dir / "constant" / region_name / "thermophysicalProperties"

        # Each region parsed independently; errors here MUST NOT poison others.
        try:
            snap = _parse_region_thermo(thermo_path, kind)
        except Exception:  # noqa: BLE001 — defensive belt-and-braces
            snap = None

        result[region_name] = snap

    return result
