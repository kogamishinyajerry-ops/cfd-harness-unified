# Codex Pre-merge Review — DEC-V61-038 (Convergence Attestor A1..A6)

**Caller**: Claude Code Opus 4.7 (v6.2 Main Driver)
**Target DEC**: DEC-V61-038 — Pre-extraction convergence attestor A1 (solver_exit_clean), A2 (continuity_floor), A3 (residual_floor), A4 (solver_iteration_cap), A5 (bounding_recurrence), A6 (no_progress)
**Self-pass-rate**: 0.65 (≤0.70 triggers pre-merge Codex per RETRO-V61-001)
**Context**: Commits 7f29a64 + eb51dcf + 9716dd4 already landed to main; codex_verdict=pending; backfill pre-merge audit.

## Files to review

Primary:
- `src/convergence_attestor.py` (~609 LOC new CFD module)
- `scripts/phase5_audit_run.py` (attestor integration — runs BEFORE extraction)
- `ui/backend/services/validation_report.py` (new concern codes in hard-FAIL / HAZARD sets)
- `ui/backend/tests/test_convergence_attestor.py` (~394 LOC)
- `knowledge/attestor_thresholds.yaml` (per-case threshold overrides)

Context:
- `.planning/decisions/2026-04-22_phase8_dec038_convergence_attestor.md` (full DEC with expected verdict table across 10 cases)
- `.planning/decisions/2026-04-22_phase8_dec036b_gates_g3_g4_g5.md` (sibling post-extraction gates)

## Review criteria (CFD physics + log parsing + threshold calibration)

### 1. A1 solver_exit_clean
- Detects `FOAM FATAL IO ERROR`, `FOAM FATAL ERROR`, `Floating exception`, etc.
- Is the regex robust across OpenFOAM versions (v2306/v2312/dev)?
- Docker-swallowed-signal case: does the check read log tail for error strings OR rely on shell exit code? Should be BOTH.

### 2. A2 continuity_floor
- Threshold 1e-4 default; per-case override for cylinder (1e-3 unsteady).
- Overlap with G5 (`sum_local > 1e-2`): A2 HAZARD window is (1e-4, 1e-2]; G5 FAIL is > 1e-2.
- Is the tier split correct? A2=HAZARD does NOT force FAIL — is this intended?

### 3. A3 residual_floor
- Per-field residual targets (Ux/Uy/Uz/p/k/epsilon/omega default 1e-3).
- Per-case overrides: impinging_jet p_rgh 5e-3 (stagnation plateau), rayleigh_benard 2e-3 (oscillatory).
- **Critical**: verify the A3 parser reads the FINAL iteration's `Solving for X, Initial residual = ...` — not an early iter.
- Is per-field threshold lookup correct when case has a field not in defaults (e.g., T for buoyant cases)?

### 4. A4 solver_iteration_cap
- Detects `No Iterations 1000` (or configured cap) in ≥N consecutive outer iterations (N=3 default).
- **Round-2 Codex BLOCKER** (per commit eb51dcf): A4 must detect `p_rgh` cap on buoyantFoam. Verify the regex handles both `GAMG:  Solving for p, ...` and `GAMG:  Solving for p_rgh, ...` variants.
- **Round-2 nit** (commit 9716dd4): PBiCGStab regex ordering — verify regex parses `PBiCGStab:  Solving for X, Initial residual = A, Final residual = B, No Iterations C` with correct field extraction (field name BEFORE numerics).
- Block-counting: "3 consecutive" means truly consecutive outer iterations, or at least 3 hits within last N iters? Spec says consecutive — verify implementation.

### 5. A5 bounding_recurrence
- Counts `bounding X,` lines in last 50 iterations; FAIL if ≥30%.
- Does the windowing correctly identify "last 50 iterations" — by iter number parsed from log, or by line-count scanning from EOF?
- Laminar cases (LDC, DHC): no bounding lines → 0% → pass. Verify.

### 6. A6 no_progress
- Initial residual for any field fluctuates within 1 decade across last 50 iters.
- Sensitive to field selection. Is p_rgh on impinging_jet expected to hit A6? Per spec: impinging_jet A4 fires, A6 does NOT (p_rgh hits cap but each inner cycle decays a decade).
- Verify decade calculation: log10(max/min) > 1.0 → progressing; ≤1.0 → stuck.

### 7. Verdict engine tier split
- A1, A4 → always FAIL (hard)
- A2, A3, A5, A6 → default HAZARD, promotable to FAIL per-case override
- Verify `_derive_contract_status` implements the two-tier logic correctly.
- What happens when multiple concerns fire (A1 FAIL + A3 HAZARD)? Overall = FAIL (max severity).

### 8. LDC regression guard (critical)
- LDC must produce ATTEST_PASS. Is there an explicit integration test reading real LDC log?
- What's the margin? If LDC's actual final p residual is 8e-4 and floor is 1e-3, one noisy run flips it to FAIL. Verify margin is ≥ 2×.

### 9. Per-case YAML robustness
- `knowledge/attestor_thresholds.yaml`: is missing-case handling safe (fall back to defaults silently)?
- Are YAML keys validated against a schema or just dict-lookup?

### 10. Ordering: attestor BEFORE gates
- Spec says attestor runs first, gates second. Does `phase5_audit_run.py` enforce this ordering?
- If attestor short-circuits (ATTEST_FAIL), do gates still run for diagnostic completeness, or skip? Diagnostic completeness is preferred (both tiers populate concerns[] even if verdict is final).

## Expected output format

```
# Codex Review Verdict — DEC-V61-038

**Verdict**: APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED / BLOCK
**Self-pass-rate delta**: claude-estimated=0.65 → codex-independent=0.XX

## Findings

### Must-fix (blocker)
- [finding id] [file:line] [description] [recommended fix]

### Should-fix (nit)
- [finding id] [file:line] [description]

## CFD physics audit per check
- A1: [analysis]
- A2: [analysis]
- A3: [analysis + per-case threshold review]
- A4: [analysis + regex robustness]
- A5: [analysis + window semantics]
- A6: [analysis + decade math]

## Regression guards
- LDC ATTEST_PASS: [pass/fail + margin]
- Tier-split implementation: [correct/incorrect]
- Attestor-before-gates ordering: [correct/incorrect]

## Backward-compat concerns
- [...]

## Recommendation
- Ready for codex_verdict=APPROVED: YES / NO
- If NO, required changes: [...]
```

Be strict. This attestor is the convergence-level defense; a false approval lets non-converged runs pass audit. Target 80-180 lines output.
