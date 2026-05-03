# V61-113 · Codex pre-merge chain (R1 APPROVE)

**DEC**: DEC-V61-113 — solver-profile loader lazy-validation audit (preemptive hardening sweep)
**Backend**: 86gs `gpt-5.4` (xhigh) · governance baseline per RETRO-V61-001
**Trigger**: backend module + config schema validation + ≤70% self-pass-rate gate borderline
**Self-estimated pass rate**: 70% (HIGH baseline — preemptive, KNOWN patterns, narrow scope)
**Actual**: 1 round APPROVE — slight HONEST underestimate.

---

## R1 (commit 0abf18f) — APPROVE clean

> "Static review of the loader hardening and accompanying tests did not reveal a concrete correctness regression in the modified paths. The new validations and error wrapping appear internally consistent with the existing call sites that translate `ProfileSchemaError` into service-layer failures."

---

## Why this DEC cleared in a single round

V61-113 is the first single-round DEC in the session's V61-111 → V61-112 → V61-113 arc. Prior arc round counts:
- V61-111 (iter01 numerical setup fix): 4 rounds
- V61-112 Phase 1 (simpleFoam): 3 rounds
- V61-112 Phase 2 (pimpleFoam): 3 rounds
- V61-112 Phase 3 (icoFoam): 2 rounds
- V61-112 Phase 4 (channel · cascade): 6 rounds
- **V61-113 (lazy-validation audit): 1 round** ← shortest

The 1-round outcome is NOT luck. It's the direct application of V61-112 methodology lessons:
1. **Phase 1 R1 P2-3 lesson** (eager nested-shape validation) — applied to fv_schemes value-types
2. **Phase 4 R1+R2 lesson** (validate transient-field types at load time) — same pattern, sibling field set
3. **Phase 4 cascade lesson** (validate at stage 1 to prevent downstream cascade) — applied preemptively to top-level sub-block shapes
4. **Phase 4 chain report's "5-stage cascade" guidance** — explicitly limit DEC scope to stages 1-2 (validation + service-error wrap) since stages 3-5 (route mapping, regression test, CI exposure) were already established by V61-112's downstream work

The DEC body §Process note explicitly cited each prior lesson and which stage it addresses. Codex's static review confirmed no gaps.

---

## Methodology validation: preemptive audit driven by prior chain reports works

V61-113 is the first executable validation that V61-112's methodology lessons (captured in chain reports) work as a forward-defense mechanism. The pattern:

1. Codex catches gap N in DEC X round Y → recorded in chain report § Methodology lesson
2. Author of DEC X+1 reads the lesson, applies same fix preemptively to sibling surfaces
3. Codex round 1 on DEC X+1: APPROVE clean (sibling gap caught in author-time review, not in Codex review)

This is the chain-report-as-knowledge-transfer pattern that justifies the writing cost of detailed methodology-lesson sections in V61-112 chain reports. **RETRO-V61-001 candidate intake**: each retro should explicitly track "lessons-applied count" — the number of forward DECs that explicitly cite + apply prior chain-report methodology lessons. Leading indicator that the chain-report methodology layer is paying off.

---

## Substantive convergence audit

| Round | P1 | P2 | P3 | Total | Δ vs prior |
|-------|----|----|----|-------|-----------|
| R1 | 0 | 0 | 0 | 0 | (clean baseline · APPROVE) |

No findings. Direct first-pass approve.

---

## Self-pass-rate calibration

- **Predicted**: 70% (HIGH baseline — preemptive, known patterns, narrow scope)
- **Actual**: 1 round APPROVE
- **Calibration verdict**: **honest slight underestimate**. 70% predicted "1-2 rounds; possible P3 nits"; got 0 nits.

For RETRO-V61-001 trend, V61-113 establishes a 4th calibration baseline:
- schema-extension migration: ~50% (Phases 1+2)
- schema-reuse migration: ~60-70% (Phase 3)
- cross-cutting cascade migration: ~30-40% (Phase 4)
- **preemptive-audit migration (driven by prior chain reports): ~80-90%** ← NEW anchor

The high pass-rate of preemptive audits incentivizes filing them as discrete DECs rather than rolling them into the next feature DEC where they'd add round-count noise.

---

## Cross-referenced artifacts

- DEC-V61-113: `.planning/decisions/2026-05-03_v61_113_solver_profile_lazy_validation_audit.md`
- V61-112 chain reports (parent methodology source):
  - `reports/codex_tool_reports/v61_112_phase1_r1_r2_r3_chain.md`
  - `reports/codex_tool_reports/v61_112_phase4_r1_r6_chain.md`
- Implementation commit: `0abf18f`
- Tests: 18 new V61-113 + 110 V61-112+V61-113 + 1215 CI-equivalent regression-clean
- Surface scan: `solver_profiles/registry.py:93-120 + :210-224` · disposition `extend existing`
