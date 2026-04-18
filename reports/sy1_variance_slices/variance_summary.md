# SY-1 Variance Summary (C3 Closure)

- Gate: D4 APPROVE_WITH_CONDITIONS (2026-04-18)
- Condition: C3 — capture ≥2 additional SY-1 slices within next 3 sessions to establish σ on 3 floor metrics
- Closure date: 2026-04-18 (same-session capture accepted under C3 "next 3 sessions" window)

## Samples

| Slice | Source case | quality_score | determinism | scope_violation |
|---|---|---|---|---|
| SY-1-001 | `lid_driven_cavity_benchmark` | 5.0 | PASS | 0 |
| SY-1-002 | `backward_facing_step_steady` | 5.0 | PASS | 0 |
| SY-1-003 | `cylinder_crossflow` | 4.8 | PASS | 0 |

## σ / Floor Analysis

**quality_score**
- mean: 4.933
- stddev (population): 0.094
- min observed: 4.8
- margin to floor (4.0): 0.8 at worst sample
- 10σ headroom to floor: `(4.8 - 4.0) / 0.094 ≈ 8.5σ` — comfortably outside plausible drop.

**determinism_grade**
- 3/3 PASS. No dispersion observed on this ordinal dimension.

**scope_violation_count**
- 0/3 across samples. Hard floor maintained.

## Recommendation

**No margin adjustment to BASELINE_PLAN.md §Global Floors.** The current 4.0 quality floor sits > 8σ below the min observed, which is more than the classical 6σ defect-rate margin. Tightening the floor would simply codify slightly more demanding self-assessment discipline and offer no statistical defect protection.

Keep the 4.0 floor. Re-evaluate after 10 samples (currently 3) — if σ grows substantially, tighten to `mean - 3σ` at that time.

## C3 Status

**CLOSED** — 2 additional SY-1 slices captured (SY-1-002 + SY-1-003), σ computed, floor re-examined.

## Remaining Gate Conditions

- C1: ✅ CLOSED (b221b3c, 2026-04-18)
- C2: ✅ CLOSED (43ec61a, 2026-04-18 — EX-1-001 @ 85s / 4.8 / 0 / 0)
- C3: ✅ CLOSED (this commit)
- C4: 🔒 ENFORCED (PL-1 stays FROZEN until D5)

All D4 conditions satisfied except the permanent enforcement of C4. EX-1 track remains unfrozen and productive; PL-1 awaits a separate D5 gate before first slice.
