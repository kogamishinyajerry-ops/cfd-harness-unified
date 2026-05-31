"""V91.2 · V9.B Python pattern matcher port.

Python port of `ui/frontend/src/data/advisor_pattern_matcher.ts`. Same
data shape, same predicate semantics, byte-identical commentary output
given the same RunArtifactSlice fixture.

V130 invariant honored BY CONSTRUCTION:
    - Pure function · no I/O · no fetch · no LLM · no subprocess
    - Only stdlib + typing imports
    - Reverse-stop #35: import-allowlist contract test enforces

Cross-language parity (RS#38): the TS matcher and this Python matcher
both load `ui/frontend/src/data/v9_advisor_rules.json` and dispatch
predicates by rule id. The parity test fixture (`__fixtures__/
v9_parity_fixtures.json`) is consumed by BOTH binders to verify they
emit byte-identical MatchedCommentary lists.

W2.0.6 (DEC-V61-209 NASA-convention slice extension · 2026-05-29):
Three optional structured fields appended to RunArtifactSlice so that
DEC-V61-209-style regional/integrated reference-comparison patterns can
be distilled into v9 rules WITHOUT changing TrustGate verdict logic and
WITHOUT touching cfdtrust tolerances. Scope-out: W2.0.6 is data-shape
only — no new predicates ship here. Future W2.1 rules consuming each
new field:

    - developed_region_gold_delta
        Regional analog of scalar gold_delta. Distinguishes near-LE
        noise (legitimate known-deviation pattern) from developed-region
        shape failures (real solver bug). W2.1 candidate rule:
        DEVELOPED_REGION_GOLD_DELTA_EXCEEDS_THRESHOLD (regional-warn
        complement to scalar R4 GOLD_DELTA_EXCEEDS_5PCT_V9_R4).

    - integrated_drag_pct
        NASA-convention global metric (integrated Cf drag %) paired
        with verification-station station_pct. W2.1 candidate rule:
        INTEGRATED_DRAG_OUT_OF_TOLERANCE (advisory mirror of the
        ADDENDUM-4 gate verdict — slice exposes the % so the rule can
        comment without re-running the gate).

    - reference_comparison_band_summary
        Near-LE band rollup (n_near_le_deviations · worst_near_le_pct ·
        x_floor_m) so a future predicate can distinguish "global delta
        high but only near-LE" (informational known-deviation pattern)
        from "delta high everywhere" (warn). W2.1 candidate rule:
        NEAR_LE_KNOWN_DEVIATION_PATTERN (info-severity advisory).

All three fields default None; per_point gate-mode cases and legacy
manifests honestly carry None (no fabrication · Law-1 advisor-not-driver
discipline). Truth-chain: every populated value traces verbatim to
trust_report.json keys produced by cfdtrust qoi.py — no recomputation
beyond a single `max()` over an existing list (worst_near_le_pct).

W3.0.6 (DEC-V61-215 multi-region RunArtifactSlice extension · 2026-05-30):
Two new frozen dataclasses (CoupledPatch, RegionSlice) and one optional
field (regions: Optional[List[RegionSlice]]) appended to RunArtifactSlice.
Additive-non-breaking: all ~59 legacy RunArtifactSlice( construction
sites stay unchanged because regions defaults None. This extension is a
frozen schema contract for W3.1 CHT rule distillation — no new predicates
ship here. W3.1 rules that consume these fields:

    - R13 COUPLED_INTERFACE_DANGLING_REF
        Reads RegionSlice.coupled_patches[*].neighbour_region vs region-name inventory.

    - R14 PER_REGION_THERMO_MISSING
        Reads RegionSlice.thermo_type / thermo_snapshot_ref.

    - R15 CONDUCTION_DOMINANCE
        Reads RegionSlice.kind to identify solid-heavy CHT topologies.

    - R16 FACE_ZONE_LOSS
        Reads RegionSlice.shm_snapshot_ref to cross-check snappyHexMesh
        face-zone output against expected coupling geometry.

Each RegionSlice field is independently optional (all default None) per
DEC-V61-213 presence-vs-payload independence contract: per-region payload
completeness is tracked separately from region-list presence. Refs
(shm_snapshot_ref, thermo_snapshot_ref) are opaque strings; this module
does NOT validate that they resolve — that is the caller's responsibility.
No fabrication: a RegionSlice carries only what the caller passes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Literal, Optional, Sequence

Severity = Literal["info", "warn", "advise"]


@dataclass(frozen=True)
class ForcesEntry:
    iteration: int
    Cd: float
    Cl: float
    Cm: float


@dataclass(frozen=True)
class ConvergenceStats:
    final_iter: int
    max_iters_reached: bool
    converged: bool
    elapsed_seconds: float


@dataclass(frozen=True)
class GoldDelta:
    max_abs_pct: float


# ---------------------------------------------------------------------------
# W2.0.6 · DEC-V61-209 NASA-convention regional structured fields
# ---------------------------------------------------------------------------
# Truth-chain: each field traces verbatim to trust_report.json keys
# produced by ui/backend/audit/cfdtrust/qoi/flat_plate_cf.py. No invented
# values · no LLM inference · single max() aggregation only.


@dataclass(frozen=True)
class DevelopedRegionGoldDelta:
    """Regional gold-delta rollup over the developed-region band.

    Source (gate_mode == 'nasa_integrated' only):
        trust_report.gates.reference_comparison.details.developed_region.{
            max_rel_error → max_abs_pct (× 100, fractional → pct)
            n_failures
            n_points
            developed_region_min_m → min_x_m
        }

    within_tolerance is intentionally omitted — derivable from
    n_failures == 0 by any consuming predicate.
    """

    max_abs_pct: float
    n_failures: int
    n_points: int
    min_x_m: float


@dataclass(frozen=True)
class IntegratedDragPct:
    """NASA-convention integrated-Cf drag % paired with verification-station.

    Source (gate_mode == 'nasa_integrated' only):
        trust_report.gates.reference_comparison.details.integrated_drag.{
            rel_error → pct (× 100)
            within_tolerance
        }
        trust_report.gates.reference_comparison.details.verification_station.{
            rel_error → station_pct (× 100 · Optional)
        }

    Paired by physical convention — verification_station Cf is the
    NASA-canonical pointwise sanity-check companion to integrated drag.
    """

    pct: float
    within_tolerance: bool
    station_pct: Optional[float] = None


@dataclass(frozen=True)
class ReferenceBandSummary:
    """Near-LE band rollup (known-deviation pattern discriminator).

    Source (gate_mode == 'nasa_integrated' only):
        trust_report.gates.reference_comparison.details.{
            n_known_deviations → n_near_le_deviations
            known_deviations[].rel_error → max(...) × 100 → worst_near_le_pct
            developed_region.developed_region_min_m → x_floor_m
                (fallback: manifest case_manifest reference_comparison.
                 developed_region_min_m)
        }

    worst_near_le_pct is COMPUTED by the deriver (single max() over an
    existing list — trust_report.json carries no precomputed 'worst'
    field; rel_error is fractional in source). None when
    n_near_le_deviations == 0.

    x_floor_m is Optional (cadence Codex R1 · 2026-05-30): the NASA-
    integrated gate schema does NOT require developed_region_min_m, and
    flat_plate_cf.py omits ``details.developed_region`` entirely when no
    developed-region guard is configured. In that valid case both
    source paths (developed_region.developed_region_min_m and the
    case_manifest reference_comparison fallback) yield no value, and
    the band summary is still meaningful (n_known_deviations + worst
    near-LE pct); x_floor_m simply stays None. NEVER fabricate 0.0 —
    that silently relabels "cutoff unknown" as "cutoff at the leading
    edge" and would mislead a future near-LE rule consumer (truth-chain
    violation).
    """

    n_near_le_deviations: int
    worst_near_le_pct: Optional[float]
    x_floor_m: Optional[float] = None


# ---------------------------------------------------------------------------
# W3.0.6 · DEC-V61-215 multi-region CHT schema extension
# ---------------------------------------------------------------------------
# Frozen data contract for W3.1 CHT rule distillation. No predicates here.
# No IO, no LLM, no subprocess — pure data shapes only.


@dataclass(frozen=True)
class CoupledPatch:
    """A single CHT-coupled boundary patch on a region interface.

    Fields
    ------
    patch_name : str
        The OpenFOAM boundary patch name (e.g. ``"heater_to_fluid"``).
    coupling_type : str
        The thermal boundary condition type string. Known valid values:
        - ``"compressible::turbulentTemperatureCoupledBaffleMixed"``
          (solid-fluid conduction coupling, case_011 topology)
        - ``"compressible::turbulentTemperatureRadCoupledMixed"``
          (radiation-coupled baffle, case_002b topology)
        - ``"humidityTemperatureCoupledMixed"``
          (humidity+temperature coupled)
        Stored verbatim as a free string (caller-validated, NOT a runtime-enforced
        enum — the catalog above is the recognized vocabulary, but any string is
        accepted; the manifest deriver is the trusted producer). W3.1 R13 rule
        reads this for mismatch detection.
    neighbour_region : Optional[str]
        The name of the adjacent coupled region. None when not extracted.

    Source: OpenFOAM ``0/T`` boundary condition entries for the region,
    extracted by the W3.x CHT surface extractor (not yet implemented).
    """

    patch_name: str
    coupling_type: str
    neighbour_region: Optional[str] = None


@dataclass(frozen=True)
class RegionSlice:
    """Per-region data snapshot carried inside RunArtifactSlice.regions.

    This is the frozen W3.1 contract: W3.1 CHT rule authors (R13–R16)
    read these fields. All payload fields are independently Optional per
    DEC-V61-213 presence-vs-payload independence.

    Fields
    ------
    name : str
        Region name as it appears in the OpenFOAM case directory
        (e.g. ``"fluid"``, ``"heater"``, ``"radiator_fin_1"``).

    kind : Optional[Literal["fluid", "solid"]]
        Physical role of the region, mirroring the W3.0.2
        ``RegionThermoSnapshot.kind`` domain (``str | None``): ``"fluid"`` /
        ``"solid"``, or **None when the upstream classification is ambiguous**
        (e.g. a region listed in BOTH the fluid and solid groups — W3.0.2 emits
        kind=None for exactly this case). Required to specify (no default), but
        None is a legitimate HONEST value: do NOT fabricate a fluid/solid label
        for an ambiguous region (DEC-V61-213 presence-vs-payload — a guessed
        label claims payload it does not have). The ``Literal`` is a
        caller-validated type hint, NOT runtime-enforced (no mypy gate in CI;
        subsystem convention — the manifest deriver is the trusted producer).
        R15 CONDUCTION_DOMINANCE reads this; None ⇒ dominance undeterminable
        for that region (the rule must skip it, not guess).

    thermo_type : Optional[str]
        Thermophysical model type string from W3.0.2
        ``RegionThermoSnapshot.thermo_type``
        (e.g. ``"heRhoThermo"``, ``"heSolidThermo"``).
        None when thermo dict was not extracted or region is absent.
        W3.1 R14 PER_REGION_THERMO_MISSING reads this field.

    coupled_patches : Optional[tuple[CoupledPatch, ...]]
        Tuple of coupled boundary patches for this region. None when
        coupling data was not extracted; empty tuple () when extraction
        ran and found zero coupled patches (presence-vs-payload
        distinction per DEC-V61-213). W3.1 R13 COUPLED_INTERFACE_DANGLING_REF
        reads neighbour_region (checked against the region inventory), not
        coupling_type.

    shm_snapshot_ref : Optional[str]
        Opaque string reference to the W3.0.1 RegionShmSnapshot for
        this region. NOT the object itself — kept as a string to decouple
        v9_advisor from case_extractors / trimesh (module boundary
        contract). W3.1 R16 FACE_ZONE_LOSS reads this ref.

    thermo_snapshot_ref : Optional[str]
        Opaque string reference to the W3.0.2 RegionThermoSnapshot for
        this region. NOT the object itself — same decoupling rationale
        as shm_snapshot_ref. W3.1 R14 reads this ref.

    W3.1 rule→field mapping (frozen contract):
        R13 COUPLED_INTERFACE_DANGLING_REF ← coupled_patches[*].neighbour_region (vs region inventory)
        R14 PER_REGION_THERMO_MISSING      ← thermo_type, thermo_snapshot_ref
        R15 CONDUCTION_DOMINANCE           ← kind
        R16 FACE_ZONE_LOSS                 ← shm_snapshot_ref
    """

    name: str
    kind: Optional[Literal["fluid", "solid"]]
    thermo_type: Optional[str] = None
    coupled_patches: Optional[tuple[CoupledPatch, ...]] = None
    shm_snapshot_ref: Optional[str] = None
    thermo_snapshot_ref: Optional[str] = None


@dataclass(frozen=True)
class RunArtifactSlice:
    run_id: str
    case_id: str
    success: bool
    exit_code: int
    residuals: Optional[Dict[str, List[float]]] = None
    forces: Optional[List[ForcesEntry]] = None
    convergence_stats: Optional[ConvergenceStats] = None
    gold_delta: Optional[GoldDelta] = None
    # W2.0.6 · DEC-V61-209 NASA-convention regional structured fields.
    # All three default None: per_point gate-mode cases, legacy V91-era
    # manifests without trust_report, and the ~100+ legacy instantiation
    # sites stay backward-compatible (additive-non-breaking contract).
    developed_region_gold_delta: Optional[DevelopedRegionGoldDelta] = None
    integrated_drag_pct: Optional[IntegratedDragPct] = None
    reference_comparison_band_summary: Optional[ReferenceBandSummary] = None
    # W3.0.6 · DEC-V61-215 multi-region CHT extension.
    # Default None: all ~59 legacy RunArtifactSlice( construction sites
    # stay compiling unchanged (additive-non-breaking contract).
    # None = no region info at all; [] = present but empty (0 regions
    # known); [RegionSlice(...)] = populated. Per DEC-V61-213:
    # presence-vs-payload independence is maintained independently.
    regions: Optional[List["RegionSlice"]] = None


@dataclass(frozen=True)
class MatchSite:
    matched_at: str


@dataclass(frozen=True)
class AdvisorRule:
    id: str
    severity: Severity
    commentary: str
    provenance: str
    # Pure predicate · returns MatchSite when triggered, None otherwise.
    # MUST NOT have side effects · MUST NOT call fetch/IO/LLM.
    predicate: Callable[[RunArtifactSlice], Optional[MatchSite]]


@dataclass(frozen=True)
class MatchedCommentary:
    rule_id: str
    matched_at: str
    commentary_excerpt: str
    provenance: str
    severity: Severity


_SEVERITY_RANK: Dict[str, int] = {"advise": 0, "warn": 1, "info": 2}


def _excerpt(commentary: str) -> str:
    """Truncate to first 240 chars · matches TS slice(0, 237) + '…'."""
    if len(commentary) > 240:
        return commentary[:237] + "…"  # U+2026 HORIZONTAL ELLIPSIS
    return commentary


def match_advisor_patterns(
    slice_: RunArtifactSlice,
    rules: Sequence[AdvisorRule],
) -> List[MatchedCommentary]:
    """Match a run artifact against the curated ruleset.

    Pure · deterministic · runs in <5ms for typical artifact sizes.
    Predicate exceptions are caught and treated as no-match (V90 carry).
    """
    matched: List[MatchedCommentary] = []

    for rule in rules:
        site: Optional[MatchSite]
        try:
            site = rule.predicate(slice_)
        except Exception:
            # V90 reverse-stop carry: matcher MUST NOT crash on malformed
            # artifact. Treat predicate exceptions as no-match · skip.
            site = None
        if site is None:
            continue

        matched.append(
            MatchedCommentary(
                rule_id=rule.id,
                matched_at=site.matched_at,
                commentary_excerpt=_excerpt(rule.commentary),
                provenance=rule.provenance,
                severity=rule.severity,
            )
        )

    # Stable sort: advise > warn > info, then by rule_id for tie-breaks.
    matched.sort(key=lambda m: (_SEVERITY_RANK[m.severity], m.rule_id))
    return matched


# ---------------------------------------------------------------------------
# Numeric formatting helpers · match JavaScript Number prototype output
# ---------------------------------------------------------------------------

def js_to_fixed(value: float, digits: int) -> str:
    """Mimic JS Number.prototype.toFixed(N) — fixed-point with N digits."""
    return f"{value:.{digits}f}"


def js_to_exponential(value: float, digits: int) -> str:
    """Mimic JS Number.prototype.toExponential(N).

    JS produces e.g. ``"1.23e-5"`` (1-digit exponent, no leading zero).
    Python ``:.2e`` produces ``"1.23e-05"`` (2-digit padded). This helper
    bridges the gap so R7's ``matched_at`` is byte-identical across TS
    and Python bindings (RS#38 cross-language parity).
    """
    s = f"{value:.{digits}e}"
    if "e" not in s:
        return s
    mantissa, exp = s.split("e")
    sign = exp[0] if exp[0] in "+-" else "+"
    digits_part = exp.lstrip("+-").lstrip("0") or "0"
    return f"{mantissa}e{sign}{digits_part}"
