# EX-1 Methodology Mini-Review (mandatory at n=5)

- Trigger: `BASELINE_PLAN.md §Rolling Override Rate Thresholds` — "at n=5 clean slices with no hard rule triggered, a lightweight methodology mini-review is still run (does NOT freeze the track) to re-examine the physics_precondition annotations in EX-1-001 memo §4 against observed implementation experience."
- Performed: 2026-04-18, inline with EX-1-005 commit
- Mode: lightweight, non-freezing; bundled with EX-1-005 same commit

## 1. Slice sample under review

| # | slice_id | type | override_rate | contract discoveries |
|---|---|---|---|---|
| 1 | EX-1-001 | diagnostic memo (R-A..R-F ranked) | 0.0 | 3 imperfect cases catalogued |
| 2 | EX-1-002 | CLI test coverage (pivot from R-C) | 1.0 | R-C physics-precondition exposed → memo §4 revised |
| 3 | EX-1-003 | physics_contract → 3 imperfect cases | 0.0 | INCOMPATIBLE / INCOMPATIBLE / DEVIATION |
| 4 | EX-1-004 | physics_contract → 3 passing cases | 0.0 | **turbulent_flat_plate Cf>0.01 Spalding fallback silent-pass hazard** (new finding) |
| 5 | EX-1-005 | physics_contract → 4 remaining cases + this review | 0.0 | **circular_cylinder_wake Strouhal hardcoded canonical_st=0.165 silent-pass hazard** (new finding); **axisymmetric_impinging_jet ref_value=0.0042 is Cf not Nu** — already documented, now elevated to contract_status |

Rolling after EX-1-005: `[0.0, 1.0, 0.0, 0.0, 0.0]` — rolling override_rate = **0.20** (1/5). All Gate rules remain untriggered.

## 2. Are the memo §4 physics_precondition annotations still self-consistent?

**Per-rank audit (memo §4 revised table, sha256 c24a9236…):**

- **Rank 1 (R-A-metadata, satisfiable today):** Validated 4 times (EX-1-003, EX-1-004 ×3 but treated as one slice, EX-1-005). No failures, no pivots. Consistent.
- **Rank 2 (R-E-mesh, satisfiable today):** UNUSED as of n=5. Pending a future slice. The satisfiability claim in the memo rests on "Phase 7 T4 demonstrated adapter supports mesh grading" — still verified, but untested under the new methodology regime.
- **Rank 3 (R-A-relabel, satisfiable today with Decision):** UNUSED. Blocked in current guardrail because relabel touches whitelist.yaml; path to use it requires a dedicated gate.
- **Ranks 4–7 (precondition-unmet or D5-gated):** Correctly identified. EX-1-002 proved rank 4 (R-C) is not satisfiable; no slice has attempted ranks 5–7.

**Verdict on memo §4 self-consistency:** ✅ **Consistent**. The ranked table has correctly gated implementer behaviour: every attempted slice has stayed in ranks 1–3, and the one pivot (EX-1-002) was away from rank 4 exactly as the annotation predicts. No annotation requires revision at this checkpoint.

## 3. New methodology findings from n=1..5 experience

### 3.1 The annotation schema surfaces silent-pass hazards that were tacit in `note:` fields

Two independent silent-pass hazards surfaced during EX-1-004 + EX-1-005 only because `physics_validity_precheck.evidence_refs` forced an extractor code read:

1. **turbulent_flat_plate**: `src/foam_agent_adapter.py:6924-6930` falls back to the Spalding formula when extracted Cf > 0.01, making the comparator self-referential under extraction failure.
2. **circular_cylinder_wake**: `src/foam_agent_adapter.py:6766-6774` hardcodes `canonical_st = 0.165` for any Re in [50, 200], bypassing the solver's pressure field entirely for the whitelist Re=100 configuration.

Both were hiding in free-text `note:` fields or not disclosed at all. Both are now captured as `contract_status: COMPATIBLE_WITH_SILENT_PASS_HAZARD` with specific evidence_ref citations. This is the annotation schema's highest-leverage behavior — it is the primary methodology win of the D4+ APPROVE_PATH_A regime.

### 3.2 contract_status vocabulary has expanded organically

After 5 slices the vocabulary is: `COMPATIBLE` (2), `COMPATIBLE_WITH_SILENT_PASS_HAZARD` (2), `PARTIALLY_COMPATIBLE` (1), `DEVIATION` (1), `INCOMPATIBLE` (2), `INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE` (1), plus "COMPATIBLE but limited-Ra" semantics in rayleigh_benard.

This 6-ish value vocabulary is ad-hoc; a future slice should either (a) normalize to a small enum and promote it to `schemas.py`, or (b) leave it as free-form strings and defer enum-ification until a downstream consumer (error_attributor) actually queries it.

**Recommendation:** LEAVE AS FREE-FORM for now. Premature enum-ification would freeze the vocabulary before the error_attributor has told us which axes matter. Revisit when a first consumer of `physics_contract` lands.

### 3.3 Evidence_ref drift risk

Every physics_contract's evidence_ref cites a specific src/ file:line. If those lines drift (refactor, renumber), the evidence becomes stale silently. No automated check exists today.

**Recommendation:** Defer automated line-number drift-check to a future PL-1 slice (post D5). For now, document the risk. A cheap mitigation is to anchor on function names rather than line numbers — partial compliance in recent annotations (ldc cites `_extract_ldc_centerline`; BFS cites `_extract_bfs_reattachment`).

### 3.4 Rolling override_rate has stabilized at 0.20

After the single EX-1-002 honest pivot, 3 subsequent slices have held override_rate=0.0 with the new physics_validity_precheck in place. The methodology regime installed by D4+ verdict is reducing, not inducing, pivots. This is the expected steady-state and should be restated in the next STATE.md update.

## 4. Calibration check against D4+ verdict rules

| rule | state after n=5 | verdict |
|---|---|---|
| #1 baseline: n≥4 rolling > 0.30 | rolling=0.20, n=5 | ✅ NOT triggered |
| #2 pattern: 2 consecutive ≥0.5 | [0.0, 1.0, 0.0, 0.0, 0.0] | ✅ NOT triggered |
| #3 precheck schema present on every EX-1 slice | every slice since EX-1-003 includes it | ✅ compliant |
| #4 abandoned preconditions enumerated on pivots | EX-1-002 override_history + learnings sections enumerate the R-C preconditions | ✅ compliant |

## 5. Recommendations for EX-1-006+

1. **Continue R-A-metadata only until a meaningful downstream consumer lands.** Further annotation passes without a reader will hit diminishing returns. The obvious next producer→consumer step is: wire `error_attributor` to read `contract_status` and auto-categorize verdict deviations.
2. **If attempting R-E (DHC mesh bump) next, run physics_validity_precheck with care** — the `src/` mesh-constant change must declare "numerical-config, not logic" explicitly or the guardrail bounded-scope test will flag it. Prefer to request gate re-confirmation that R-E fits the src/** whitelist.
3. **A PL-1 slice should produce a cross-case summary** reading `contract_status` across all 10 annotated YAMLs and emit a Phase 10 methodology document — but PL-1 is C4-frozen until D5, so deferred.
4. **Do NOT rush to land R-A-relabel (rank 3)** just to use it. The whitelist.yaml edit it requires is outside current guardrails; it needs a dedicated gate.

## 6. Conclusion

**Methodology mini-review PASS.** No rules triggered. Annotations self-consistent. Two substantive silent-pass-hazard discoveries validate the schema's value. No memo §4 revision required at this checkpoint. Track continues.

---

Produced: 2026-04-18 (EX-1-005 commit)
Reviewed by: opus47-main (self-Gate)
Next mandatory review trigger: another D4-level methodology threshold breach (no scheduled review otherwise)
