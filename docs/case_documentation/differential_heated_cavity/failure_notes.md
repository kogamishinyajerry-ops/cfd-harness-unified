# Failure notes — differential_heated_cavity

> Free-form yaml/markdown — not a P4 KOM schema artifact.

## FM-DHC-1: Ra=10¹⁰ regime mismatch (retired)

- **Tag**: `regime_mismatch_unresolvable_mesh`
- **Trigger**: pre-DEC-V61-006 case configuration was Ra=10¹⁰ with Nu=30 gold (turbulent SST). Two compounding issues:
  1. Ra=10¹⁰ requires ~1000 wall-normal cells for BL resolution; adapter's 80-cell mesh undersamples by 10× → cannot converge to a meaningful Nu
  2. Nu=30 was inconsistent with the high-Ra literature (DNS/LES reports 100–325 at Ra=10¹⁰)
- **Symptom**: comparator reported PASS or FAIL but neither was meaningful — the adapter's resolved field was a coarse non-converged turbulent solve, the gold value was wrong by 3-10×, and the two errors mostly cancelled
- **Detected**: Q-1 hard-floor audit (DEC-ADWM-004 FUSE) + Gate Q-new Case 6 audit
- **Status**: RESOLVED — DEC-V61-006 P-2 (Path P-2 approved by Kogami 2026-04-20) downgraded Ra to 1e6, the canonical de Vahl Davis 1983 benchmark. This simultaneously closed three issues: (a) mesh-resolution precondition (40-80 cells now sufficient), (b) gold-reference accuracy (Nu=8.800 unambiguous within ±0.2%), (c) Q-1 hard-floor closure
- **Recovery note**: the historical Ra=10¹⁰ configuration was retired by DEC-V61-006. Recovery to that configuration would require `git revert -m 1` of PR #6 merge AND a mesh refinement effort (~1000 wall-normal cells) that is currently out-of-scope.

## FM-DHC-2: Phase 7 Docker cache hit obsolete adapter (cellCentre vs writeCellCentres)

- **Tag**: `docker_layer_cache_serves_stale_adapter`
- **Trigger**: Phase 7 (2026-04-16) Docker E2E run crashed at "Starting time loop" with `Unknown function type cellCentre` before iteration. Adapter source was already corrected to `writeCellCentres` (line 4422) but Docker layer cache served the older adapter
- **Symptom**: solver immediately died at t=0; CI run flagged FAIL
- **Detected**: Phase 7 Docker E2E logs
- **Status**: RESOLVED on rerun with current adapter; mitigation: rebuild Docker layer when src/foam_agent_adapter.py changes

## FM-DHC-3: ψ_max stream-function reconstruction noise floor

- **Tag**: `extraction_noise_floor_demotes_to_advisory`
- **Trigger**: ψ is reconstructed by cumulative trapezoidal ∫₀^y u_x dy with no-slip bottom-wall BC. Mass-conservation closure at the top wall (which should = 0 exactly) measures the integration noise floor.
- **Symptom**: when closure_residual_max_nondim / |ψ_max_gold_nondim| ≥ 1%, the extracted ψ_max is dominated by integration drift, not the physical ψ peak
- **Detected**: DEC-V61-057 Stage C audit
- **Status**: ACKNOWLEDGED — extractor `extract_psi_max` auto-demotes from HARD_GATED to PROVISIONAL_ADVISORY when the threshold is exceeded. Comparator reports the value but excludes from pass-fraction. Same pattern as LDC FM-LDC-4 (secondary vortices ψ noise floor).

## FM-DHC-4: Mean-over-y wall-gradient extractor refactor

- **Tag**: `extractor_methodology_clarified`
- **Trigger**: original Nu extractor had ambiguous methodology w.r.t. the wall-averaging direction
- **Detected**: EX-1-008 (commit 60952b6)
- **Status**: RESOLVED — EX-1-008 landed mean-over-y wall-adjacent gradient methodology; behavior is unchanged after the Ra downgrade

## Pattern themes

- **regime_mismatch_unresolvable_mesh**: target regime (Ra, Re, Re_τ) demands mesh resolution beyond what the adapter can produce. Recurs at plane_channel_flow (Re_τ=180 demands DNS but adapter is laminar icoFoam). P4 should auto-derive minimum mesh resolution from the declared regime + relevant length scale (δ_T, δ_99) and FAIL ingest if adapter mesh < required.
- **docker_layer_cache_serves_stale_adapter**: CI infrastructure. Suggests pre-commit hook or CI guard: Docker image rebuild triggered on `src/foam_agent_adapter.py` mtime.
- **extraction_noise_floor_demotes_to_advisory**: the **good** pattern — extractor measures its own noise floor and demotes the observable's gate role rather than emitting a noisy verdict. Same pattern at LDC secondary vortices. P4 should formalize this as a first-class observable role: `HARD_GATED_WITH_NOISE_FLOOR_DEMOTION`.
