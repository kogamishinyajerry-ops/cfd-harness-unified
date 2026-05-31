"""V9.W2.1 · DEC-V61-216 R10/R11/R12 advisor-rule unit tests.

Per-rule positive + boundary-negative coverage for the three W2.1
distillations of DEC-V61-209 P1 post-run lessons:

    - R10 KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10 (info)
        Honest known-known surfacing of the demoted-near-LE pattern:
        scalar gold-delta drift fully explained by the cataloged
        OpenFOAM-kΩSST-vs-CFL3D near-LE formulation discrepancy.

    - R11 DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11 (warn)
        Real solver-bug regional shape advisory: per-point failures
        past the developed_region_min_m = 0.1 m floor are qualitatively
        different from R4 scalar amplitude drift.

    - R12 INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12 (warn)
        NASA-convention dual-metric XOR: integrated-Cf drag PASS/FAIL
        disagrees with Cf@verification_station PASS/FAIL → integration-
        pipeline bug class (DEC-V61-209 lines 226-231 stale time-dir
        incident).

Truth-chain (LAW 2): every test cites the DEC-V61-209 ADDENDUM § and
the W2.0.6 slice field it exercises.

Following the test_v9_pattern_matcher.py established pattern: shared
_converged_healthy() helper, TestPositiveCases asserts fire,
TestNegativeCases pins the discriminator boundaries (including the
KNOWN-GAP scope-outs that mirror DEC-V61-215 R1 honest-None contract).
"""

from __future__ import annotations

import pytest

from ui.backend.services.v9_advisor import (
    ConvergenceStats,
    DevelopedRegionGoldDelta,
    ForcesEntry,
    GoldDelta,
    IntegratedDragPct,
    ReferenceBandSummary,
    RunArtifactSlice,
    V9_ADVISOR_RULES,
    match_advisor_patterns,
)


# ---------------------------------------------------------------------------
# Shared fixtures · mirrors test_v9_pattern_matcher._converged_healthy
# ---------------------------------------------------------------------------


def _converged_healthy() -> RunArtifactSlice:
    """Healthy converged slice. Three W2.0.6 fields default None."""
    return RunArtifactSlice(
        run_id="R-OK-1",
        case_id="flat_plate_rans_sst",
        success=True,
        exit_code=0,
        residuals={
            "p": [1e-2, 5e-3, 2.5e-3, 1e-3, 5e-4, 2.5e-4, 1e-4, 5e-5],
            "U": [1e-2, 5e-3, 2.5e-3, 1e-3, 5e-4, 2.5e-4, 1e-4, 5e-5],
        },
        forces=[
            ForcesEntry(iteration=i, Cd=0.95 + (i % 2) * 0.001, Cl=0.0, Cm=0.0)
            for i in range(20)
        ],
        convergence_stats=ConvergenceStats(
            final_iter=800,
            max_iters_reached=False,
            converged=True,
            elapsed_seconds=28.0,
        ),
        gold_delta=GoldDelta(max_abs_pct=0.75),
    )


def _known_deviation_pattern() -> RunArtifactSlice:
    """Canonical DEC-V61-209 ADDENDUM 5 #2 demoted-near-LE fingerprint.

    Real OF11 PASS profile: integrated-Cf 0.83%, station Cf 1.28% (both
    inside 10%), developed region 0 failures, 4 near-LE known_deviations
    (worst ~14.7%). gold_delta scalar would otherwise trip R4 because
    the near-LE band poisons the scalar max.
    """
    return RunArtifactSlice(
        **{
            **_converged_healthy().__dict__,
            "gold_delta": GoldDelta(max_abs_pct=8.2),
            "developed_region_gold_delta": DevelopedRegionGoldDelta(
                max_abs_pct=0.95, n_failures=0, n_points=50, min_x_m=0.1
            ),
            "integrated_drag_pct": IntegratedDragPct(
                pct=1.8, within_tolerance=True, station_pct=2.1
            ),
            "reference_comparison_band_summary": ReferenceBandSummary(
                n_near_le_deviations=6, worst_near_le_pct=14.7, x_floor_m=0.1
            ),
        }
    )


# ---------------------------------------------------------------------------
# R10 · KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10 — positive + negatives
# ---------------------------------------------------------------------------


class TestR10KnownDeviationPatternNearLE:
    """W2.1 · DEC-V61-209 ADDENDUM 5 #2.

    R10 is INFORMATIONAL; fires only when scalar drift is fully explained
    by the cataloged near-LE OpenFOAM-kΩSST-vs-CFL3D formulation
    discrepancy. Inverse-polarity to R11 (R10 short-circuits at
    n_failures != 0 → R11 territory).
    """

    def test_r10_positive_canonical_demoted_near_le_pattern(self):
        """Fires on the canonical DEC-V61-209 demoted-near-LE fingerprint."""
        matches = match_advisor_patterns(_known_deviation_pattern(), V9_ADVISOR_RULES)
        ids = {m.rule_id for m in matches}
        assert "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" in ids
        # R10 matched_at string is byte-stable for cross-language parity.
        r10 = next(m for m in matches if m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10")
        assert r10.matched_at == "near_le_known_dev_n6_worst14.70pct"
        # R10 is info; R4 also fires at warn (sorts first).
        assert r10.severity == "info"
        assert "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4" in ids

    def test_r10_negative_developed_region_field_none(self):
        """KNOWN-GAP scope-out (DEC-V61-215 graceful-skip): per_point gate
        cases legitimately carry developed_region_gold_delta=None →
        R10 silently skips even when other fields would qualify.
        """
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "developed_region_gold_delta": None,
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        )

    def test_r10_negative_integrated_drag_field_none(self):
        """Legacy V91-era manifests have integrated_drag_pct=None → silent skip."""
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "integrated_drag_pct": None,
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        )

    def test_r10_negative_band_summary_field_none(self):
        """No reference_band_summary → no claim about near-LE band → silent skip."""
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "reference_comparison_band_summary": None,
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        )

    def test_r10_negative_gold_delta_at_or_below_5pct(self):
        """R10 requires R4-equivalent amplitude floor (>5%); 5.00 exact is
        NOT > 5 → no fire. Pins the `> 5.0` vs `>= 5.0` discriminator.
        """
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "gold_delta": GoldDelta(max_abs_pct=5.0),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        )

    def test_r10_negative_developed_region_has_failures(self):
        """Developed region carries failures → R11 territory, NOT R10."""
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "developed_region_gold_delta": DevelopedRegionGoldDelta(
                    max_abs_pct=8.5, n_failures=2, n_points=50, min_x_m=0.1
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        )
        # R11 should pick up the slice instead (polarity-pair).
        assert any(
            m.rule_id == "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" for m in matches
        )

    def test_r10_negative_integrated_drag_failing(self):
        """NASA dual-metric gate failing → not the demoted-near-LE pattern."""
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=12.5, within_tolerance=False, station_pct=2.1
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        )

    def test_r10_negative_no_near_le_deviations(self):
        """n_near_le_deviations == 0 → nothing to claim is near-LE → no fire.

        With the canonical PASS-shape underneath this slice (developed_region
        clean + integrated/station agree on PASS) no W2.1 rule fires;
        R4 still fires on the scalar drift.
        """
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "reference_comparison_band_summary": ReferenceBandSummary(
                    n_near_le_deviations=0, worst_near_le_pct=None, x_floor_m=0.1
                ),
            }
        )
        ids = {
            m.rule_id for m in match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        }
        assert "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" not in ids
        # R4 still fires on the scalar drift.
        assert "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4" in ids

    def test_r10_negative_x_floor_unknown_known_gap(self):
        """KNOWN-GAP (DEC-V61-215 R1 carry-forward): x_floor_m=None →
        cutoff unknown → R10 refuses to claim the deviation lives in the
        documented near-LE band. NEVER fabricate 0.0 as a sentinel.

        Mirrors test_derive_slice_band_summary_x_floor_absent_stays_none_
        not_zero in test_v9_pattern_matcher.py and is the rule-side
        enforcement of the truth-chain invariant.
        """
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "reference_comparison_band_summary": ReferenceBandSummary(
                    n_near_le_deviations=6,
                    worst_near_le_pct=14.7,
                    x_floor_m=None,
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        )

    def test_negative_station_pct_failing_does_not_fire_per_codex_r1(self) -> None:
        """Codex CRS R0 P2 R1 pin (R10 station-gate hardening).

        DEC-V61-209 ADDENDUM 4: the NASA dual-metric gate is a paired
        PASS/PASS contract — BOTH integrated AND station must clear
        NASA_TOL_PCT=10.0. A slice where integrated drag is in tolerance
        (within_tolerance=True) but station_pct > 10.0 is NOT a "demoted
        near-LE known deviation" — it's the R12-class discrepancy that
        R10 must NOT mask by emitting an informational match.
        """
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=1.8, within_tolerance=True, station_pct=12.5
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        ), "R10 falsely fired on station_pct=12.5 > NASA_TOL_PCT=10.0 (Codex CRS R0 P2)"

    def test_negative_station_pct_missing_does_not_fire_per_codex_r1(self) -> None:
        """Codex CRS R0 P2 R1 pin (R10 half-data refusal).

        When integrated_drag_pct.station_pct is None (verification_station
        block absent) the NASA dual-metric gate is INCOMPLETE — R10
        refuses to demote on half-data per the truth-chain discipline,
        mirroring R12's "station_pct is None → no fire" contract.
        """
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=1.8, within_tolerance=True, station_pct=None
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        ), "R10 falsely fired on station_pct=None (NASA gate incomplete · Codex CRS R0 P2)"

    def test_positive_station_pct_at_nasa_boundary_inclusive_fires_per_codex_r1(
        self,
    ) -> None:
        """Codex CRS R0 P3 R1 pin (R10 boundary-inclusive parity with R12).

        The NASA gate is `<=` (matches flat_plate_cf.py
        `station_rel <= tolerance`), so a slice with station_pct EXACTLY
        at 10.0 is IN tolerance and R10 SHOULD fire. The previous strict
        `<` semantics would have silently dropped this slice from R10
        — this test pins the boundary as inclusive.
        """
        slice_ = RunArtifactSlice(
            **{
                **_known_deviation_pattern().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=1.8, within_tolerance=True, station_pct=10.0
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        ), "R10 missed station_pct=10.0 (NASA boundary inclusive · Codex CRS R0 P3)"


# ---------------------------------------------------------------------------
# R11 · DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11 — positive + negatives
# ---------------------------------------------------------------------------


class TestR11DevelopedRegionShapeMismatch:
    """W2.1 · DEC-V61-209 ADDENDUM 5 #1.

    R11 fires on a real per-point structural failure past the LE-exclusion
    floor (x ≥ developed_region_min_m = 0.1 m). Polarity-paired with R10
    via the n_failures discriminator.
    """

    def test_r11_positive_developed_region_per_point_failures(self):
        """Real per-point shape failure → R11 fires with byte-stable matched_at."""
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "gold_delta": GoldDelta(max_abs_pct=12.5),
                "developed_region_gold_delta": DevelopedRegionGoldDelta(
                    max_abs_pct=18.0, n_failures=3, n_points=50, min_x_m=0.1
                ),
                "integrated_drag_pct": IntegratedDragPct(
                    pct=11.2, within_tolerance=False, station_pct=9.8
                ),
                "reference_comparison_band_summary": ReferenceBandSummary(
                    n_near_le_deviations=2, worst_near_le_pct=8.0, x_floor_m=0.1
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        r11 = [m for m in matches if m.rule_id == "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11"]
        assert len(r11) == 1
        assert r11[0].matched_at == "developed_region_failures_3of50_max18.00pct"
        assert r11[0].severity == "warn"
        # R10 must NOT fire (n_failures > 0 short-circuits R10).
        assert not any(
            m.rule_id == "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" for m in matches
        )

    def test_r11_negative_developed_region_field_none(self):
        """KNOWN-GAP scope-out: per_point gate cases legitimately carry
        developed_region_gold_delta=None → silent skip.
        """
        # Healthy slice — developed_region_gold_delta is None by default.
        matches = match_advisor_patterns(_converged_healthy(), V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" for m in matches
        )

    def test_r11_negative_zero_failures_high_amplitude(self):
        """n_failures == 0 even if max_abs_pct is high → no per-point fail
        → R11 must NOT fire. The amplitude came from a within-tolerance
        worst-case, not from a shape mismatch.
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "developed_region_gold_delta": DevelopedRegionGoldDelta(
                    max_abs_pct=9.5, n_failures=0, n_points=50, min_x_m=0.1
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" for m in matches
        )

    def test_r11_negative_amplitude_at_or_below_5pct(self):
        """Discriminator floor matches R4 scalar: max_abs_pct=5.0 exact is
        NOT > 5 → no fire. Single-point grazing the gate tolerance is not
        a solver-bug signal worth surfacing at warn severity.
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "developed_region_gold_delta": DevelopedRegionGoldDelta(
                    max_abs_pct=5.0, n_failures=1, n_points=50, min_x_m=0.1
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" for m in matches
        )

    def test_r11_negative_amplitude_just_under_5pct(self):
        """Boundary pin: max_abs_pct=4.99 with n_failures=1 → just under
        the 5% floor → R11 must NOT fire. Pins the > 5.0 comparator vs
        a regression that would loosen it to >= 5.0.
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "developed_region_gold_delta": DevelopedRegionGoldDelta(
                    max_abs_pct=4.99, n_failures=1, n_points=50, min_x_m=0.1
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" for m in matches
        )

    def test_r11_negative_amplitude_drift_only_no_failures(self):
        """KNOWN-GAP per design: a slice that shows only amplitude drift
        (developed_region max_abs_pct high) but NO regional shape mismatch
        (n_failures=0) must NOT fire R11. R4 may still fire on scalar
        drift, but R11 is reserved for the per-point shape signal.
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "gold_delta": GoldDelta(max_abs_pct=7.0),  # R4 fires here
                "developed_region_gold_delta": DevelopedRegionGoldDelta(
                    max_abs_pct=6.5, n_failures=0, n_points=50, min_x_m=0.1
                ),
            }
        )
        ids = {
            m.rule_id for m in match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        }
        assert "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" not in ids
        assert "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4" in ids


# ---------------------------------------------------------------------------
# R12 · INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12 — positive + negatives
# ---------------------------------------------------------------------------


class TestR12IntegratedVsStationDiscrepancy:
    """W2.1 · DEC-V61-209 ADDENDUM 4 + lines 226-231.

    R12 fires only when the two NASA-canonical metrics DISAGREE on
    PASS/FAIL at NASA_TOL_PCT=10.0. Strict XOR — agreement (both pass
    or both fail) is no-fire.
    """

    def test_r12_positive_xor_station_fails_integrated_passes(self):
        """Integrated passes (within_tolerance=True), station fails
        (station_pct=11.5 ≥ 10) → XOR triggers R12 with byte-stable matched_at.
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "developed_region_gold_delta": DevelopedRegionGoldDelta(
                    max_abs_pct=1.5, n_failures=0, n_points=50, min_x_m=0.1
                ),
                "integrated_drag_pct": IntegratedDragPct(
                    pct=1.5, within_tolerance=True, station_pct=11.5
                ),
                "reference_comparison_band_summary": ReferenceBandSummary(
                    n_near_le_deviations=0, worst_near_le_pct=None, x_floor_m=0.1
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        r12 = [
            m for m in matches if m.rule_id == "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12"
        ]
        assert len(r12) == 1
        assert r12[0].matched_at == "integrated_drag_1.50pct_vs_station_11.50pct"
        assert r12[0].severity == "warn"

    def test_r12_positive_xor_integrated_fails_station_passes(self):
        """Inverse XOR: integrated fails, station passes — the canonical
        DEC-V61-209 stale-time-dir incident class (lines 226-231).
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=11.2, within_tolerance=False, station_pct=9.8
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(
            m.rule_id == "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12" for m in matches
        )

    def test_r12_negative_integrated_drag_field_none(self):
        """Legacy V91-era manifests + per_point gate-mode cases have
        integrated_drag_pct=None → silent skip.
        """
        matches = match_advisor_patterns(_converged_healthy(), V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12" for m in matches
        )

    def test_r12_negative_station_pct_none(self):
        """verification_station block absent → station_pct=None → refusing
        to fire on half-data (DEC-V61-215 honest scope-out mirror).
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=1.5, within_tolerance=True, station_pct=None
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12" for m in matches
        )

    def test_r12_negative_both_pass_boundary_pin(self):
        """Boundary pin: station_pct=9.99 just under 10% AND
        within_tolerance=True → both PASS → R12 must NOT fire.
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=1.0, within_tolerance=True, station_pct=9.99
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12" for m in matches
        )

    def test_r12_negative_both_fail_agreement(self):
        """Companion pin: station_pct=10.01 just over 10% AND
        within_tolerance=False → both FAIL → R12 must NOT fire
        (agreement, not disagreement).
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=11.0, within_tolerance=False, station_pct=10.01
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12" for m in matches
        )

    def test_r12_negative_station_at_exact_tolerance_is_pass_per_codex_r1(self):
        """Codex CRS R0 P3 R1 pin (R12 boundary-inclusive — REPLACES
        previous strict-less-than pin which encoded the buggy semantics).

        NASA gate convention is `<=` (matches flat_plate_cf.py
        `station_rel <= tolerance`). A slice with station_pct EXACTLY
        10.0 is IN tolerance → station PASSES → both integrated and
        station PASS → no XOR → R12 does NOT fire.

        The previous test asserted R12 DID fire at station_pct=10.0 —
        that test was pinning a wrong behavior (strict `<` was the bug
        Codex flagged). This test now pins the corrected `<=` semantics
        for both Python and the TS mirror.
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=1.5, within_tolerance=True, station_pct=10.0
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(
            m.rule_id == "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12"
            for m in matches
        ), "R12 falsely fired at station_pct=10.0 (NASA boundary inclusive · Codex CRS R0 P3)"

    def test_r12_positive_station_just_over_tolerance_fires_per_codex_r1(self):
        """Codex CRS R0 P3 R1 pin (R12 boundary just-over → fires).

        Companion to the inclusive-boundary test above: station_pct
        EXACTLY 10.0001 (or any value > 10.0) is OUT of tolerance →
        station FAILS → integrated PASSES → XOR → R12 fires. Pins the
        post-fix discriminator at the just-over edge.
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "integrated_drag_pct": IntegratedDragPct(
                    pct=1.5, within_tolerance=True, station_pct=10.0001
                ),
            }
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(
            m.rule_id == "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12"
            for m in matches
        ), "R12 missed station_pct=10.0001 (just-over NASA boundary · Codex CRS R0 P3)"


# ---------------------------------------------------------------------------
# Cross-rule interaction · LAW 3 cross-language parity is asserted in
# test_v9_cross_language_parity.py; here we pin the Python-side semantic
# expectations on co-firing patterns that the fixtures exercise.
# ---------------------------------------------------------------------------


class TestR10R11R12CoFiring:
    """Polarity contracts between the three new rules + cross-fire with R4."""

    def test_r4_and_r10_co_fire_on_demoted_near_le(self):
        """Canonical demoted-near-LE: R4 (warn) AND R10 (info) co-fire,
        R11/R12 do NOT. Severity ordering: R4 sorts before R10.
        """
        matches = match_advisor_patterns(_known_deviation_pattern(), V9_ADVISOR_RULES)
        ids = [m.rule_id for m in matches]
        # R4 sorts first (warn=1 < info=2).
        r4_idx = ids.index("GOLD_DELTA_EXCEEDS_5_PCT_V9_R4")
        r10_idx = ids.index("KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10")
        assert r4_idx < r10_idx
        assert "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" not in ids
        assert "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12" not in ids

    def test_r10_r11_inverse_polarity_on_n_failures(self):
        """Same slice EXCEPT developed_region.n_failures: 0 → R10, ≥1 → R11.

        The discriminator is n_failures, sharply paired.
        """
        base = _known_deviation_pattern()
        # n_failures=0 → R10 fires, R11 does not.
        ids_clean = {
            m.rule_id for m in match_advisor_patterns(base, V9_ADVISOR_RULES)
        }
        assert "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" in ids_clean
        assert "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" not in ids_clean

        # Flip n_failures=2, amplitude>5 → R11 fires, R10 does not.
        flipped = RunArtifactSlice(
            **{
                **base.__dict__,
                "developed_region_gold_delta": DevelopedRegionGoldDelta(
                    max_abs_pct=18.0, n_failures=2, n_points=50, min_x_m=0.1
                ),
            }
        )
        ids_flipped = {
            m.rule_id for m in match_advisor_patterns(flipped, V9_ADVISOR_RULES)
        }
        assert "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" in ids_flipped
        assert "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" not in ids_flipped

    def test_r12_orthogonal_to_r10_r11(self):
        """R12 fires independently on PASS/FAIL XOR, regardless of R10/R11
        state. Pin: R12 fires on a slice with clean developed region +
        zero near-LE (so R10/R11 silent) but station_pct=11.5.
        """
        slice_ = RunArtifactSlice(
            **{
                **_converged_healthy().__dict__,
                "developed_region_gold_delta": DevelopedRegionGoldDelta(
                    max_abs_pct=1.5, n_failures=0, n_points=50, min_x_m=0.1
                ),
                "integrated_drag_pct": IntegratedDragPct(
                    pct=1.5, within_tolerance=True, station_pct=11.5
                ),
                "reference_comparison_band_summary": ReferenceBandSummary(
                    n_near_le_deviations=0, worst_near_le_pct=None, x_floor_m=0.1
                ),
            }
        )
        ids = {m.rule_id for m in match_advisor_patterns(slice_, V9_ADVISOR_RULES)}
        assert "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12" in ids
        assert "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" not in ids
        assert "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" not in ids


# ---------------------------------------------------------------------------
# Ruleset surface assertions (W2.1 specific)
# ---------------------------------------------------------------------------


class TestW2_1_RulesetSurface:
    """Pin the W2.1 ruleset shape — version bump + 12 rules + R10/R11/R12 wired."""

    def test_ruleset_contains_r10_r11_r12(self):
        ids = {r.id for r in V9_ADVISOR_RULES}
        assert "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10" in ids
        assert "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11" in ids
        assert "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12" in ids

    def test_ruleset_has_14_rules(self):
        """W2.1 = +3 rules over the 9 landed through R9 → 12 total.
        W3.1 = +2 CHT rules R13+R14 shipped → 14 total.
        R15 (CONDUCTION_DOMINANCE) + R16 (FACE_ZONE_LOSS) deferred per
        Codex R1 (DEC-V61-222): frozen W3.0.6 schema carries DECLARED topology
        (kind from regionProperties, shm_snapshot_ref sHM-vs-extruded) but NOT
        produced-mesh presence; faithful R15/R16 require a future W3.2
        mesh-presence field."""
        assert len(V9_ADVISOR_RULES) == 14

    @pytest.mark.parametrize(
        "rule_id,expected_severity",
        [
            ("KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10", "info"),
            ("DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11", "warn"),
            ("INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12", "warn"),
        ],
    )
    def test_severity_mapping(self, rule_id, expected_severity):
        rule = next(r for r in V9_ADVISOR_RULES if r.id == rule_id)
        assert rule.severity == expected_severity

    @pytest.mark.parametrize(
        "rule_id,must_appear_in_provenance",
        [
            ("KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10", "ADDENDUM 5"),
            ("DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11", "ADDENDUM 5"),
            ("INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12", "ADDENDUM 4"),
        ],
    )
    def test_provenance_cites_dec_v61_209_addendum(
        self, rule_id, must_appear_in_provenance
    ):
        """LAW 2: every W2.1 rule MUST cite its DEC-V61-209 ADDENDUM."""
        rule = next(r for r in V9_ADVISOR_RULES if r.id == rule_id)
        assert must_appear_in_provenance in rule.provenance
        assert "DEC-V61-209" in rule.provenance or "v61_209" in rule.provenance
