"""V91.2 · V9.B Python pattern matcher contract tests.

Mirror of `ui/frontend/src/data/__tests__/advisor_pattern_matcher.contract.test.ts`
(26 TS tests) plus cross-language parity assertions (RS#38).

V91 reverse-stops covered:
    - RS#32: every rule has non-empty provenance (`buildRules`-time)
    - RS#33: commentary excludes "AI generates / AI suggests / ..." verbiage
    - RS#35: matcher imports limited to stdlib + typing (import-allowlist test)
    - RS#38: cross-language parity — same RunArtifactSlice → same MatchedCommentary

V130 carry: graceful predicate-throw degrade (matcher MUST NOT crash on
malformed artifact).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import List

import pytest

from ui.backend.services.v9_advisor import (
    AdvisorRule,
    ConvergenceStats,
    ForcesEntry,
    GoldDelta,
    MatchedCommentary,
    MatchSite,
    RunArtifactSlice,
    V9_ADVISOR_RULES,
    V9_RULESET_VERSION,
    match_advisor_patterns,
)
from ui.backend.services.v9_advisor.pattern_matcher import (
    js_to_exponential,
    js_to_fixed,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _converged_healthy() -> RunArtifactSlice:
    """Fixture mirroring TS CONVERGED_HEALTHY constant."""
    return RunArtifactSlice(
        run_id="R-OK-1",
        case_id="lid_driven_cavity",
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


# ---------------------------------------------------------------------------
# Ruleset shape integrity
# ---------------------------------------------------------------------------

class TestRulesetShape:
    def test_at_least_6_rules(self):
        assert len(V9_ADVISOR_RULES) >= 6

    def test_every_rule_has_nonempty_id(self):
        for rule in V9_ADVISOR_RULES:
            assert len(rule.id) > 0

    def test_every_rule_has_nonempty_commentary(self):
        for rule in V9_ADVISOR_RULES:
            assert len(rule.commentary.strip()) > 50

    def test_every_rule_has_nonempty_provenance(self):
        # RS#32 enforcement
        for rule in V9_ADVISOR_RULES:
            assert len(rule.provenance.strip()) > 0

    def test_rule_ids_are_unique(self):
        ids = [r.id for r in V9_ADVISOR_RULES]
        assert len(set(ids)) == len(ids)

    def test_ruleset_version_semver_ish(self):
        import re
        assert re.match(r"^v?\d+\.\d+\.\d+$", V9_RULESET_VERSION)

    def test_no_ai_verbiage_in_commentary(self):
        # RS#33 honest-framing carry from V90
        for rule in V9_ADVISOR_RULES:
            lower = rule.commentary.lower()
            assert "ai generates" not in lower
            assert "ai suggests" not in lower
            assert "ai diagnoses" not in lower
            assert "ai recommends" not in lower


# ---------------------------------------------------------------------------
# Positive cases — each rule matches its intended pattern
# ---------------------------------------------------------------------------

class TestPositiveCases:
    def test_r1_residual_oscillation_p(self):
        oscillating = [1e-2, 5e-3, 1.2e-2, 4e-3, 1.3e-2, 3.5e-3, 1.4e-2, 3e-3]
        slice_ = _converged_healthy()
        # Replace p residuals with oscillating pattern
        slice_ = RunArtifactSlice(
            **{**slice_.__dict__, "residuals": {**slice_.residuals, "p": oscillating}}
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(m.rule_id == "RESIDUAL_OSCILLATION_P_V9_R1" for m in matches)

    def test_r2_max_iters_reached(self):
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(
            **{**slice_.__dict__, "convergence_stats": ConvergenceStats(
                final_iter=5000, max_iters_reached=True, converged=False, elapsed_seconds=60.0
            )}
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(m.rule_id == "MAX_ITERS_REACHED_V9_R2" for m in matches)

    def test_r3_run_failed_nonzero_exit(self):
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(**{**slice_.__dict__, "success": False, "exit_code": 1})
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(m.rule_id == "RUN_FAILED_NONZERO_EXIT_V9_R3" for m in matches)

    def test_r4_gold_delta_exceeds_5_pct(self):
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(**{**slice_.__dict__, "gold_delta": GoldDelta(max_abs_pct=8.2)})
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(m.rule_id == "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4" for m in matches)

    def test_r5_forces_not_converged(self):
        drifty = [ForcesEntry(iteration=i, Cd=0.5 + i * 0.05, Cl=0.0, Cm=0.0) for i in range(20)]
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(**{**slice_.__dict__, "forces": drifty})
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(m.rule_id == "FORCES_NOT_CONVERGED_V9_R5" for m in matches)

    def test_r6_slow_convergence(self):
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(
            **{**slice_.__dict__, "convergence_stats": ConvergenceStats(
                final_iter=7500, max_iters_reached=False, converged=True, elapsed_seconds=240.0
            )}
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(m.rule_id == "SLOW_CONVERGENCE_V9_R6" for m in matches)

    def test_r7_residual_plateau_u(self):
        # 20 samples at ~1.5e-3 with tiny noise — variation <2%, value > 1e-4
        plateau = [1.5e-3 + (i % 3 - 1) * 1e-6 for i in range(20)]
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(
            **{**slice_.__dict__, "residuals": {**slice_.residuals, "U": plateau}}
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert any(m.rule_id == "RESIDUAL_PLATEAU_U_V9_R7" for m in matches)

    def test_r8_healthy_convergence(self):
        matches = match_advisor_patterns(_converged_healthy(), V9_ADVISOR_RULES)
        assert any(m.rule_id == "HEALTHY_CONVERGENCE_V9_R8" for m in matches)


# ---------------------------------------------------------------------------
# Negative cases — clean run does NOT trigger false positives
# ---------------------------------------------------------------------------

class TestNegativeCases:
    def test_r2_negative_clean_run_no_max_iters(self):
        matches = match_advisor_patterns(_converged_healthy(), V9_ADVISOR_RULES)
        assert not any(m.rule_id == "MAX_ITERS_REACHED_V9_R2" for m in matches)

    def test_r3_negative_success_true_no_failed_match(self):
        matches = match_advisor_patterns(_converged_healthy(), V9_ADVISOR_RULES)
        assert not any(m.rule_id == "RUN_FAILED_NONZERO_EXIT_V9_R3" for m in matches)

    def test_r4_negative_gold_delta_under_5_pct(self):
        matches = match_advisor_patterns(_converged_healthy(), V9_ADVISOR_RULES)
        assert not any(m.rule_id == "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4" for m in matches)

    # --- P2 W2.0: boundary true-negatives for R1/R5/R6/R7/R8 (close the
    # per-predicate test-debt; each pins the exact threshold so a future
    # predicate edit that loosens a comparator is caught). ---

    def test_r1_negative_amplitude_below_oscillation_threshold(self):
        # Alternating about the mean (>=2 sign flips) BUT amplitude ratio 0.2,
        # just under the 0.3 _is_oscillating threshold → must NOT match R1.
        sub_threshold = [1.2e-3, 0.8e-3, 1.2e-3, 0.8e-3, 1.2e-3, 0.8e-3, 1.2e-3, 0.8e-3]
        slice_ = RunArtifactSlice(
            **{**_converged_healthy().__dict__,
               "residuals": {**_converged_healthy().residuals, "p": sub_threshold}}
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(m.rule_id == "RESIDUAL_OSCILLATION_P_V9_R1" for m in matches)

    def test_r5_negative_force_drift_just_under_one_pct(self):
        # One 1.01 outlier among 1.00 → ~0.9% max drift, just under the 1%
        # threshold → must NOT match R5.
        forces = [ForcesEntry(iteration=i, Cd=1.0, Cl=0.0, Cm=0.0) for i in range(9)]
        forces.append(ForcesEntry(iteration=9, Cd=1.01, Cl=0.0, Cm=0.0))
        slice_ = RunArtifactSlice(**{**_converged_healthy().__dict__, "forces": forces})
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(m.rule_id == "FORCES_NOT_CONVERGED_V9_R5" for m in matches)

    def test_r6_negative_converged_just_under_5000_iters(self):
        # Converged at iter 4999 — one below the >=5000 slow-convergence
        # boundary → must NOT match R6.
        slice_ = RunArtifactSlice(
            **{**_converged_healthy().__dict__, "convergence_stats": ConvergenceStats(
                final_iter=4999, max_iters_reached=False, converged=True, elapsed_seconds=200.0
            )}
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(m.rule_id == "SLOW_CONVERGENCE_V9_R6" for m in matches)

    def test_r7_negative_low_plateau_below_1e4_floor(self):
        # A flat U history (variation <2%) but parked at ~5e-5, below the
        # 1e-4 mean-magnitude floor → a healthily-low residual, NOT a stuck
        # plateau → must NOT match R7.
        low_plateau = [5e-5 + (i % 3 - 1) * 1e-8 for i in range(20)]
        slice_ = RunArtifactSlice(
            **{**_converged_healthy().__dict__,
               "residuals": {**_converged_healthy().residuals, "U": low_plateau}}
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(m.rule_id == "RESIDUAL_PLATEAU_U_V9_R7" for m in matches)

    def test_r8_negative_converged_but_non_monotonic_p(self):
        # Converged, but the last-8 p history has a bump (not strictly
        # decreasing) → the "healthy" signature requires monotonic decrease,
        # so R8 must NOT match.
        bumpy = [1e-2, 5e-3, 6e-3, 1e-3, 5e-4, 2.5e-4, 1e-4, 5e-5]
        slice_ = RunArtifactSlice(
            **{**_converged_healthy().__dict__,
               "residuals": {**_converged_healthy().residuals, "p": bumpy}}
        )
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert not any(m.rule_id == "HEALTHY_CONVERGENCE_V9_R8" for m in matches)


# ---------------------------------------------------------------------------
# Graceful degrade (V90 carry · V9 reverse-stop #4)
# ---------------------------------------------------------------------------

class TestGracefulDegrade:
    def test_empty_artifact_no_crash(self):
        empty = RunArtifactSlice(run_id="R-empty", case_id="x", success=True, exit_code=0)
        matches = match_advisor_patterns(empty, V9_ADVISOR_RULES)
        assert isinstance(matches, list)

    def test_predicate_throwing_treated_as_no_match(self):
        def boom(_slice):
            raise RuntimeError("predicate boom")

        exploding = AdvisorRule(
            id="EXPLOSION_TEST",
            severity="info",
            commentary="test commentary placeholder of sufficient length for the validation guard",
            provenance="test/explosion",
            predicate=boom,
        )
        matches = match_advisor_patterns(_converged_healthy(), [exploding])
        assert matches == []


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_3_successive_calls_identical(self):
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(
            **{**slice_.__dict__, "convergence_stats": ConvergenceStats(
                final_iter=6000, max_iters_reached=False, converged=True, elapsed_seconds=200.0
            )}
        )
        out1 = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        out2 = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        out3 = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert out1 == out2 == out3


# ---------------------------------------------------------------------------
# Output sorting (severity stable: advise > warn > info)
# ---------------------------------------------------------------------------

class TestSorting:
    def test_advise_before_warn_before_info(self):
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(**{
            **slice_.__dict__,
            "success": False,         # R3 advise
            "exit_code": 1,
            "gold_delta": GoldDelta(max_abs_pct=10),  # R4 warn
        })
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        ranks = {"advise": 0, "warn": 1, "info": 2}
        last_rank = -1
        for m in matches:
            assert ranks[m.severity] >= last_rank
            last_rank = ranks[m.severity]


# ---------------------------------------------------------------------------
# MatchedCommentary structure + truncation
# ---------------------------------------------------------------------------

class TestMatchedCommentaryStructure:
    def test_each_match_has_required_fields(self):
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(**{**slice_.__dict__, "success": False, "exit_code": 137})
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        assert len(matches) > 0
        for m in matches:
            assert len(m.rule_id) > 0
            assert len(m.matched_at) > 0
            assert len(m.commentary_excerpt) > 0
            assert len(m.provenance) > 0
            assert m.severity in ("advise", "warn", "info")

    def test_commentary_excerpt_at_most_240_chars(self):
        slice_ = _converged_healthy()
        slice_ = RunArtifactSlice(**{**slice_.__dict__, "success": False, "exit_code": 1})
        matches = match_advisor_patterns(slice_, V9_ADVISOR_RULES)
        for m in matches:
            assert len(m.commentary_excerpt) <= 240


# ---------------------------------------------------------------------------
# V91 RS#35 · import-allowlist for matcher purity
# ---------------------------------------------------------------------------

class TestImportAllowlist:
    """RS#35: pattern_matcher.py + rules.py must NOT import network/IO/subprocess
    libraries. Allowed: stdlib + typing + intra-package."""

    ALLOWED_TOP_LEVEL = {
        "__future__", "math", "json", "dataclasses", "typing", "pathlib", "re",
    }
    DISALLOWED_PREFIXES = (
        "requests", "urllib", "httpx", "aiohttp", "socket", "subprocess",
        "os.system", "openai", "anthropic",
    )

    def _imports_in_file(self, path: Path) -> List[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    names.append(node.module)
        return names

    def test_pattern_matcher_imports_clean(self):
        path = REPO_ROOT / "ui/backend/services/v9_advisor/pattern_matcher.py"
        for name in self._imports_in_file(path):
            top = name.split(".")[0]
            assert top in self.ALLOWED_TOP_LEVEL, f"forbidden import: {name}"
            for forbidden in self.DISALLOWED_PREFIXES:
                assert not name.startswith(forbidden), f"disallowed: {name}"

    def test_rules_module_imports_clean(self):
        path = REPO_ROOT / "ui/backend/services/v9_advisor/rules.py"
        for name in self._imports_in_file(path):
            top = name.split(".")[0]
            assert top in self.ALLOWED_TOP_LEVEL, f"forbidden import: {name}"
            for forbidden in self.DISALLOWED_PREFIXES:
                assert not name.startswith(forbidden), f"disallowed: {name}"

    def test_manifest_adapter_imports_clean(self):
        path = REPO_ROOT / "ui/backend/services/v9_advisor/manifest_adapter.py"
        for name in self._imports_in_file(path):
            top = name.split(".")[0]
            assert top in self.ALLOWED_TOP_LEVEL, f"forbidden import: {name}"
            for forbidden in self.DISALLOWED_PREFIXES:
                assert not name.startswith(forbidden), f"disallowed: {name}"


# ---------------------------------------------------------------------------
# V91 RS#38 · Cross-language parity (JS toExponential / toFixed helpers)
# ---------------------------------------------------------------------------

class TestJSNumericFormatHelpers:
    @pytest.mark.parametrize("value,digits,expected", [
        (8.2, 2, "8.20"),
        (1.234, 2, "1.23"),
        (0.0, 2, "0.00"),
        (100.0, 0, "100"),
    ])
    def test_js_to_fixed_matches_js(self, value, digits, expected):
        assert js_to_fixed(value, digits) == expected

    @pytest.mark.parametrize("value,digits,expected", [
        (1.5e-3, 2, "1.50e-3"),   # JS: "1.50e-3" · Python default: "1.50e-03"
        (1.23e-5, 2, "1.23e-5"),
        (1.23e5, 2, "1.23e+5"),
        (1.23e-10, 2, "1.23e-10"),
        (1.0, 2, "1.00e+0"),
    ])
    def test_js_to_exponential_matches_js(self, value, digits, expected):
        assert js_to_exponential(value, digits) == expected


# ---------------------------------------------------------------------------
# RS#37 · JSON SSOT canonical form (Python-side enforcement)
# ---------------------------------------------------------------------------

class TestJSONSsotCanonical:
    JSON_PATH = REPO_ROOT / "ui/frontend/src/data/v9_advisor_rules.json"

    def test_canonical_form(self):
        raw = self.JSON_PATH.read_text(encoding="utf-8")
        expected = json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        assert raw == expected, "JSON SSOT must be canonical (RS#37)"

    def test_python_loads_same_rules_as_ts_corpus(self):
        # Side proof: 8 rules with expected IDs
        raw = self.JSON_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        assert data["version"] == V9_RULESET_VERSION
        loaded_ids = [r["id"] for r in data["rules"]]
        python_ids = [r.id for r in V9_ADVISOR_RULES]
        assert loaded_ids == python_ids, "Python join must preserve JSON order"
