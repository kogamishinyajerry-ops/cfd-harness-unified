"""V91.3 · V9.D · Manifest → RunArtifactSlice adapter.

Derives a RunArtifactSlice from the existing audit-package manifest dict
shape so the V9 matcher can run against it without requiring the run
pipeline to emit a separate artifact.

Inputs read from manifest:
    - manifest["measurement"]["comparator_verdict"]
        → success (PASS → True · FAIL → False · None → True)
        → convergence_stats.converged (mirrors success)
    - manifest["measurement"]["key_quantities"] + manifest["case"]["gold_standard"]
        → gold_delta.max_abs_pct (max relative deviation across observables)
    - manifest["run"]["outputs"]["solver_log_tail"]
        → convergence_stats.max_iters_reached (regex "reached.*maxIter" or "Maximum iter")
        → convergence_stats.final_iter (last "Time = N" or "Iteration N")

W2.0.6 (DEC-V61-209 NASA-convention regional fields · 2026-05-29):
    - manifest["trust_report"]["gates"]["reference_comparison"]["details"]
        Discriminated by ``details.gate_mode == 'nasa_integrated'``.
        Per_point or absent gate_mode → all three new fields stay None
        (honest scope-out: per_point cases have no regional payload to
        truthfully expose).

        → developed_region_gold_delta (from details.developed_region.{
            max_rel_error, n_failures, n_points, developed_region_min_m})
            W2.1 candidate rule:
            DEVELOPED_REGION_GOLD_DELTA_EXCEEDS_THRESHOLD (regional-warn
            complement to scalar R4 GOLD_DELTA_EXCEEDS_5PCT_V9_R4).

        → integrated_drag_pct (from details.integrated_drag.{rel_error,
            within_tolerance} + details.verification_station.rel_error)
            W2.1 candidate rule: INTEGRATED_DRAG_OUT_OF_TOLERANCE
            (advisory mirror of ADDENDUM-4 gate verdict).

        → reference_comparison_band_summary (from details.{
            n_known_deviations, known_deviations[].rel_error} +
            details.developed_region.developed_region_min_m fallback to
            manifest case_manifest reference_comparison.developed_region_min_m)
            W2.1 candidate rule: NEAR_LE_KNOWN_DEVIATION_PATTERN
            (info-severity advisory).

    Defensive contract: malformed trust_report sub-dicts (non-dict
    entries · non-numeric rel_error · missing keys) yield None for the
    affected field — never a crash (V90 RS#34 graceful-empty extends to
    W2.0.6). Pure dict-in / dataclass-out — RS#35 import allowlist
    unchanged ({__future__, math, json, dataclasses, typing, pathlib, re}).

    Production-wiring status (cadence Codex R1 · 2026-05-30 CRS P2 #1):
    The production audit-package builder ``src/audit_package/manifest.py
    build_manifest()`` does NOT currently inject a top-level
    ``trust_report`` key into the manifest dict it produces. The
    nasa_integrated branch above is therefore exercised end-to-end ONLY
    by synthetic test fixtures (test_v9_pattern_matcher.py
    TestW2_0_6_Deriver). On real audit-package builds, all three new
    slice fields stay None and the slice degrades gracefully to the
    pre-W2.0.6 shape (R1-R9 predicates unchanged · `gold_delta` scalar
    still derived from `case.gold_standard.observables` + measurement
    pathway).

    W2.0.7 (deliberately NOT in W2.0.6 scope · separate sub-DEC) will
    wire `build_manifest()` to inject the trust_report subset the deriver
    expects (read from `<case_dir>/artifacts/trust_report.json` when it
    exists; absent → manifest has no trust_report key; deriver leaves
    new fields None — graceful-degrade-by-design). W2.0.6 deliberately
    lands the data contract first so W2.0.7 wiring + W2.1 rule
    distillation are scoped to their own sub-DECs (sub-DEC scope-driven
    per CLAUDE.md v2.3). DO NOT add yaml/json file IO to this module
    to "close the gap" — RS#35 allowlist forbids and any IO belongs in
    the builder, not the pure deriver.

NOT derived (history-array data absent from manifest schema):
    - residuals (per-iter history)
    - forces (per-iter history)

Consequence: 3 of 8 V9 rules dormant in production until manifest schema
widens (R1 residual_oscillation_p · R5 forces_not_converged · R7
residual_plateau_u). Documented as V91 retro Open Q.

V130: this function is pure (reads dict argument, returns dataclass).
No I/O. No network. No subprocess. RS#35 import-allowlist enforced.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .pattern_matcher import (
    ConvergenceStats,
    CoupledPatch,
    DevelopedRegionGoldDelta,
    GoldDelta,
    IntegratedDragPct,
    MatchedCommentary,
    ReferenceBandSummary,
    RegionSlice,
    RunArtifactSlice,
    match_advisor_patterns,
)
from .rules import V9_ADVISOR_RULES, V9_RULESET_VERSION


# Regex patterns reading from solver log tail. Conservative — only fire
# when we're confident. Manifest is the only data source; no fallback.
_RE_MAX_ITERS = re.compile(
    r"(?:Maximum iterations reached|reached.*maxIter|maxIter\s+exceeded)",
    re.IGNORECASE,
)
# V91 Codex P2 #4: real OpenFOAM logs often write "Time = 0.998s" with a
# trailing "s" (seconds unit) — keep the unit optional so transient-solver
# logs also yield final_iter.
_RE_TIME_LINE = re.compile(r"^\s*Time\s*=\s*(\d+(?:\.\d+)?)\s*s?\s*$", re.MULTILINE)
_RE_ITER_LINE = re.compile(r"^\s*Iteration\s+(\d+)\b", re.MULTILINE | re.IGNORECASE)


def _parse_final_iter(log_tail: str) -> Optional[int]:
    """Find the last 'Time = N' or 'Iteration N' marker in log_tail.

    OpenFOAM steady solvers emit 'Time = N' (where N is the iteration
    number for SIMPLE/PISO loops). Transient solvers emit floating-point
    timestamps. The final iteration is whichever value appears latest.
    """
    times = [float(m) for m in _RE_TIME_LINE.findall(log_tail)]
    iters = [int(m) for m in _RE_ITER_LINE.findall(log_tail)]
    candidates: List[float] = []
    if times:
        candidates.append(times[-1])
    if iters:
        candidates.append(float(iters[-1]))
    if not candidates:
        return None
    # Take the max — both kinds of marker may co-exist; pick the latest.
    return int(max(candidates))


def _regions_from_manifest(manifest: Dict[str, Any]) -> Optional[List[RegionSlice]]:
    """Parse manifest["regions"] → Optional[List[RegionSlice]].

    manifest["regions"] contract (W3.2 forward-compat · DEC-V61-213):
        Each entry mirrors RegionSlice:
          {
            "name": str,                          # required — None/missing → skip entry
            "kind": "fluid" | "solid" | null,     # None when ambiguous or absent
            "thermo_type": str | null,
            "coupled_patches": [
              {"patch_name": str, "coupling_type": str,
               "neighbour_region": str | null}
            ] | null,
            "shm_snapshot_ref": str | null,
            "thermo_snapshot_ref": str | null
          }

    This key is emitted by W3.2 audit-integration, which feeds the output of
    the W3.0.x multi-region extractors (region_properties_reader /
    shm_dict_multi_region / thermo_dict_multi_region) into the manifest builder.
    Current single-region and legacy manifests omit the key entirely → regions=None
    → R13–R14 gracefully silent (R15/R16 deferred — Codex R1, DEC-V61-222).

    RESIDUAL W3.2 GAP: This adapter is READY. The production audit-package
    builder (src/audit_package/manifest.py build_manifest()) does NOT yet emit
    manifest["regions"]. W3.2 must add that emission. Until then, all real audit
    bundles take the "no regions key → return None" path and R13–R14 are silent
    in production. This is the correct honest behavior (DEC-V61-213
    presence-vs-payload independence: absent key = not extracted, not empty).

    Three-state preservation (per DEC-V61-213):
        - manifest has no "regions" key → None  (not extracted / legacy)
        - manifest["regions"] == []             → []  (present, zero regions)
        - manifest["regions"] is a populated list → List[RegionSlice]

    Presence-vs-payload per field:
        - "kind": missing/None → None (HONEST-REFUSAL; never fabricate)
        - "thermo_type": missing/None → None
        - "coupled_patches": missing → None (not extracted)
                             [] → ()  (extracted, zero)
                             populated → tuple[CoupledPatch, ...]
        - refs: missing/None → None

    BULLETPROOF-GRACEFUL: runs on the PRODUCTION HOT PATH (every audit bundle
    not just CHT). Any structural error (non-list regions, non-dict entry, wrong
    types, null name) yields None for that entry or the whole result; the deriver
    MUST NEVER raise. A crash here would break every audit bundle's commentary.
    """
    if "regions" not in manifest:
        return None
    raw = manifest["regions"]
    if not isinstance(raw, list):
        # Structural error — malformed; return None to avoid breaking audit bundle
        return None
    if len(raw) == 0:
        return []
    try:
        result: List[RegionSlice] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue  # skip malformed entries; do not crash
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                continue  # name required; skip entry with missing/null/empty name
            kind_raw = entry.get("kind")
            if kind_raw not in ("fluid", "solid", None):
                kind_raw = None  # coerce unknown strings → None (honest)
            thermo_type = entry.get("thermo_type")
            if not isinstance(thermo_type, str):
                thermo_type = None
            shm_snapshot_ref = entry.get("shm_snapshot_ref")
            if not isinstance(shm_snapshot_ref, str):
                shm_snapshot_ref = None
            thermo_snapshot_ref = entry.get("thermo_snapshot_ref")
            if not isinstance(thermo_snapshot_ref, str):
                thermo_snapshot_ref = None
            # coupled_patches: missing/null → None (not extracted)
            #                  [] → ()  (extracted, zero patches)
            #                  populated list → tuple[CoupledPatch, ...]
            cp_raw = entry.get("coupled_patches")
            coupled_patches: Optional[tuple]
            if cp_raw is None and "coupled_patches" not in entry:
                coupled_patches = None  # key absent — not extracted
            elif cp_raw is None:
                coupled_patches = None  # explicit null — treat as not extracted
            elif not isinstance(cp_raw, list):
                coupled_patches = None  # malformed — safe default
            elif len(cp_raw) == 0:
                coupled_patches = ()
            else:
                patches: List[CoupledPatch] = []
                for cp in cp_raw:
                    if not isinstance(cp, dict):
                        continue
                    pname = cp.get("patch_name")
                    ctype = cp.get("coupling_type")
                    if not isinstance(pname, str) or not isinstance(ctype, str):
                        continue  # skip malformed patch
                    neighbour = cp.get("neighbour_region")
                    if not isinstance(neighbour, str):
                        neighbour = None
                    patches.append(CoupledPatch(
                        patch_name=pname,
                        coupling_type=ctype,
                        neighbour_region=neighbour,
                    ))
                coupled_patches = tuple(patches) if patches else ()
            result.append(RegionSlice(
                name=name,
                kind=kind_raw,
                thermo_type=thermo_type,
                coupled_patches=coupled_patches,
                shm_snapshot_ref=shm_snapshot_ref,
                thermo_snapshot_ref=thermo_snapshot_ref,
            ))
        return result
    except Exception:
        # Catch-all: anything unexpected returns None (safe degrade).
        # A crash here would break every audit bundle.
        return None


def derive_slice_from_manifest(manifest: Dict[str, Any]) -> RunArtifactSlice:
    """Build a RunArtifactSlice from audit-package manifest dict shape.

    Tolerates missing fields gracefully — returns a slice with whatever
    data is available. Predicates that need missing fields will return
    None (matcher's documented behavior).
    """
    case = manifest.get("case") or {}
    run = manifest.get("run") or {}
    measurement = manifest.get("measurement") or {}
    outputs = run.get("outputs") or {}

    case_id = case.get("id") or ""
    run_id = run.get("run_id") or ""
    verdict = measurement.get("comparator_verdict")
    log_tail = outputs.get("solver_log_tail") or ""
    key_quantities = measurement.get("key_quantities") or {}

    # V91 Codex P1 #2 fix: success / exit_code are SOLVER-HEALTH signals,
    # not comparator-verdict signals. Real audit manifests carry
    # ``measurement.key_quantities.solver_success`` for the clean-run-vs-crash
    # distinction; comparator_verdict only reports whether output matched
    # gold (physics drift can FAIL on a perfectly clean run). Treating
    # FAIL as a crash falsely fires R3 (RUN_FAILED_NONZERO_EXIT) which
    # claims the solver died, which it didn't.
    solver_success = key_quantities.get("solver_success") if isinstance(key_quantities, dict) else None
    if solver_success is False:
        success = False
        exit_code = 1
    else:
        # solver_success is True OR absent (older manifests lack the field);
        # treat as nominal — R3 will not fire.
        success = True
        exit_code = 0

    # Gold delta — compute max |actual - expected| / |expected| * 100.
    #
    # V91 Codex P1 #3 fix: real audit manifests carry gold_standard.observables
    # as a LIST of {name, ref_value, tolerance, unit, ...} records, and
    # measurement.key_quantities as a SINGLETON record {quantity, value, ...}
    # (one observation per audit pass). Old dict-shaped fixtures
    # {name: ref_value} are accepted as fallback for backward-compat with
    # ad-hoc test fixtures.
    gold_delta: Optional[GoldDelta] = None
    gs = case.get("gold_standard") or {}
    raw_observables = gs.get("observables") if isinstance(gs, dict) else None

    # Normalize observables → list[(name, ref_value)] tuples
    obs_pairs: List[tuple[str, float]] = []
    if isinstance(raw_observables, list):
        for entry in raw_observables:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            ref = entry.get("ref_value")
            if isinstance(name, str) and isinstance(ref, (int, float)) and ref != 0:
                obs_pairs.append((name, float(ref)))
    elif isinstance(raw_observables, dict):
        # Legacy/test-fiction dict shape {name: ref_value}
        for name, ref in raw_observables.items():
            if isinstance(name, str) and isinstance(ref, (int, float)) and ref != 0:
                obs_pairs.append((name, float(ref)))

    if obs_pairs and isinstance(key_quantities, dict):
        # Real-world key_quantities shape: singleton {quantity, value, ...}
        singleton_quantity = key_quantities.get("quantity")
        singleton_value = key_quantities.get("value")
        is_singleton = isinstance(singleton_quantity, str) and isinstance(singleton_value, (int, float))

        max_pct: Optional[float] = None
        for name, ref in obs_pairs:
            actual: Optional[float] = None
            if is_singleton:
                # Match by exact name OR substring prefix (handles
                # "u_centerline[y=0.3750]" matching observable "u_centerline").
                if singleton_quantity == name or singleton_quantity.startswith(name):
                    actual = float(singleton_value)
            else:
                # Multi-key dict shape (test fiction): direct name lookup
                cand = key_quantities.get(name)
                if isinstance(cand, (int, float)):
                    actual = float(cand)
            if actual is None:
                continue
            pct = abs(actual - ref) / abs(ref) * 100.0
            if max_pct is None or pct > max_pct:
                max_pct = pct
        if max_pct is not None:
            gold_delta = GoldDelta(max_abs_pct=max_pct)

    # Convergence stats — parse log_tail. If log_tail missing, stats=None
    # → R2, R6, R8 dormant. Converged status is now decoupled from comparator
    # verdict (per Codex P1 #2 disposition): converged means "solver
    # converged" — a separate concept from "output matches gold".
    convergence_stats: Optional[ConvergenceStats] = None
    if log_tail:
        max_iters_reached = bool(_RE_MAX_ITERS.search(log_tail))
        final_iter = _parse_final_iter(log_tail)
        # converged = solver ran cleanly AND did not hit iteration cap.
        # Comparator verdict is intentionally NOT a factor here.
        converged = success and not max_iters_reached
        if final_iter is not None:
            convergence_stats = ConvergenceStats(
                final_iter=final_iter,
                max_iters_reached=max_iters_reached,
                converged=converged,
                elapsed_seconds=0.0,  # not in manifest yet
            )

    # ------------------------------------------------------------------
    # W2.0.6 · DEC-V61-209 NASA-convention regional structured fields.
    # Discriminated by gate_mode == 'nasa_integrated'. Per_point or
    # absent gate_mode → all three fields stay None (honest scope-out).
    # All branches defensive-guard with isinstance + try/except float
    # conversion — malformed sub-dicts return None for that field, not a
    # crash (V90 RS#34 graceful-empty contract extends to W2.0.6).
    # ------------------------------------------------------------------
    developed_region_gold_delta: Optional[DevelopedRegionGoldDelta] = None
    integrated_drag_pct: Optional[IntegratedDragPct] = None
    reference_comparison_band_summary: Optional[ReferenceBandSummary] = None

    trust_report = manifest.get("trust_report")
    if isinstance(trust_report, dict):
        gates = trust_report.get("gates")
        ref_block = gates.get("reference_comparison") if isinstance(gates, dict) else None
        details = ref_block.get("details") if isinstance(ref_block, dict) else None
        if not isinstance(details, dict):
            details = {}
        gate_mode = details.get("gate_mode")

        if gate_mode == "nasa_integrated":
            # (1) developed_region branch
            dev = details.get("developed_region")
            if isinstance(dev, dict):
                try:
                    max_rel = dev.get("max_rel_error")
                    n_fail = dev.get("n_failures")
                    n_pts = dev.get("n_points")
                    dev_min_m = dev.get("developed_region_min_m")
                    if (
                        isinstance(max_rel, (int, float))
                        and isinstance(n_fail, int)
                        and isinstance(n_pts, int)
                        and isinstance(dev_min_m, (int, float))
                    ):
                        developed_region_gold_delta = DevelopedRegionGoldDelta(
                            max_abs_pct=float(max_rel) * 100.0,
                            n_failures=int(n_fail),
                            n_points=int(n_pts),
                            min_x_m=float(dev_min_m),
                        )
                except (TypeError, ValueError):
                    developed_region_gold_delta = None

            # (2) integrated_drag branch (paired with verification_station)
            idr = details.get("integrated_drag")
            if isinstance(idr, dict):
                try:
                    rel_err = idr.get("rel_error")
                    within = idr.get("within_tolerance")
                    if isinstance(rel_err, (int, float)) and isinstance(within, bool):
                        station = details.get("verification_station")
                        station_pct: Optional[float] = None
                        if isinstance(station, dict):
                            st_rel = station.get("rel_error")
                            if isinstance(st_rel, (int, float)):
                                try:
                                    station_pct = float(st_rel) * 100.0
                                except (TypeError, ValueError):
                                    station_pct = None
                        integrated_drag_pct = IntegratedDragPct(
                            pct=float(rel_err) * 100.0,
                            within_tolerance=bool(within),
                            station_pct=station_pct,
                        )
                except (TypeError, ValueError):
                    integrated_drag_pct = None

            # (3) band_summary branch (near-LE known-deviation rollup)
            n_dev = details.get("n_known_deviations")
            if isinstance(n_dev, int):
                try:
                    kd = details.get("known_deviations")
                    if not isinstance(kd, list):
                        kd = []
                    rel_errors: List[float] = []
                    for row in kd:
                        if not isinstance(row, dict):
                            continue
                        v = row.get("rel_error")
                        if isinstance(v, (int, float)):
                            try:
                                rel_errors.append(float(v))
                            except (TypeError, ValueError):
                                continue
                    worst_pct: Optional[float] = (
                        max(rel_errors) * 100.0 if rel_errors else None
                    )
                    # x_floor_m: prefer details.developed_region.developed_region_min_m,
                    # fall back to manifest case_manifest reference_comparison
                    # (callers must inject pre-parsed). Final fallback 0.0
                    # only if both absent — defensive default.
                    x_floor: Optional[float] = None
                    if isinstance(dev, dict):
                        dev_min_m = dev.get("developed_region_min_m")
                        if isinstance(dev_min_m, (int, float)):
                            try:
                                x_floor = float(dev_min_m)
                            except (TypeError, ValueError):
                                x_floor = None
                    if x_floor is None:
                        case_manifest = manifest.get("case_manifest")
                        if isinstance(case_manifest, dict):
                            ref_cm = case_manifest.get("reference_comparison")
                            if isinstance(ref_cm, dict):
                                cm_floor = ref_cm.get("developed_region_min_m")
                                if isinstance(cm_floor, (int, float)):
                                    try:
                                        x_floor = float(cm_floor)
                                    except (TypeError, ValueError):
                                        x_floor = None
                    # Cadence Codex R1 (2026-05-30 · CRS P2 #2): do NOT
                    # fabricate x_floor=0.0 when both source paths fail.
                    # The NASA-integrated gate schema does not require
                    # developed_region_min_m; flat_plate_cf.py omits
                    # details.developed_region entirely when no developed-
                    # region guard is configured. Substituting 0.0 silently
                    # relabels "cutoff unknown" as "cutoff at the leading
                    # edge", which would mislead a future near-LE rule
                    # consumer (truth-chain violation). x_floor_m is
                    # Optional now; absence is the honest answer.
                    reference_comparison_band_summary = ReferenceBandSummary(
                        n_near_le_deviations=int(n_dev),
                        worst_near_le_pct=worst_pct,
                        x_floor_m=x_floor,
                    )
                except (TypeError, ValueError):
                    reference_comparison_band_summary = None

    # W3.1 · DEC-V61-215 multi-region CHT extension.
    # _regions_from_manifest returns None when the manifest has no "regions"
    # key (all current single-region + legacy manifests) → R13–R14 silently
    # dormant. When W3.2 wires build_manifest() to emit manifest["regions"],
    # the CHT rules activate automatically through this path.
    # See _regions_from_manifest docstring for the full W3.2 gap statement.
    regions = _regions_from_manifest(manifest)

    return RunArtifactSlice(
        run_id=run_id,
        case_id=case_id,
        success=success,
        exit_code=exit_code,
        # residuals + forces dormant in V91 scope — see module docstring
        convergence_stats=convergence_stats,
        gold_delta=gold_delta,
        # W2.0.6 · DEC-V61-209 NASA-convention regional structured fields
        developed_region_gold_delta=developed_region_gold_delta,
        integrated_drag_pct=integrated_drag_pct,
        reference_comparison_band_summary=reference_comparison_band_summary,
        # W3.1 · DEC-V61-215 multi-region CHT regions
        regions=regions,
    )


def matches_for_manifest(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compute matched commentary list for a manifest dict.

    Returns canonical-JSON-ready dicts (not dataclass instances) so the
    caller can serialize to the audit-package zip without further work.
    """
    slice_ = derive_slice_from_manifest(manifest)
    matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
    return [
        {
            "rule_id": m.rule_id,
            "matched_at": m.matched_at,
            "commentary_excerpt": m.commentary_excerpt,
            "provenance": m.provenance,
            "severity": m.severity,
        }
        for m in matches
    ]


def commentary_section_for_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Build the manifest's top-level ``commentary`` section.

    Schema:
        {
            "version": "v9.0.0",
            "matched": [<MatchedCommentary dicts>, ...]
        }

    Empty matched list is still a valid section (audit-trail completeness:
    a clean run that triggered no rules still records "we checked").
    """
    return {
        "version": V9_RULESET_VERSION,
        "matched": matches_for_manifest(manifest),
    }
