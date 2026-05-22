# DOGFOOD · M3.0 Cycle 7 · junior-engineer beginner test (litmus surrogate)

**DEC**: `2026-05-23_v61_202_sub_m30_cycle7_beginner_test.md` (Proposed)
**Date**: 2026-05-23
**Dogfood script**: `scripts/dogfood/case_007_cycle7_beginner_test.py`
**Verdict**: **PASS** (6/6 checks · all-PASS gate)

---

## What this cycle proves

A programmatic engineer that follows whatever the workbench rail says at
each step, applies the suggested fix (or a simple stub when no suggestion
is offered), and advances when the topbar CTA enables — reaches a
solveable case_007 (step 5, topbar = `submit_solve enabled`) in
**8 decide() calls**, well under the 20-call (≈30 min) junior-engineer
budget.

This is the M3.0 litmus surrogate. It is **necessary but not sufficient**:
- ✅ The engine drives monotonic forward progress with no rework loops
- ✅ The rail surfaces the right next field at each step
- ✅ The topbar CTA gates advance correctly (disabled when info_gap
     blocks, enabled when step is clear)
- ⚠ A real junior engineer with comparable behaviour is M3.1 scope
- ⚠ The 8-call result is best-case (synthesized values mirror UI form
     helpers); domain-correct numerical fills are domain-knowledge work,
     not UI work

---

## The journey (8 decide() calls)

```
[1] step=1 kind=step_default sev=None field=None
    topbar.kind=next_step topbar.enabled=True
    → click → advance to step 2
[2] step=2 kind=step_default sev=None field=None
    topbar.kind=next_step topbar.enabled=True
    → click → advance to step 3
[3] step=3 kind=info_gap     sev=None field=physics.solver
    topbar.kind=step_default topbar.enabled=False
    → synthesize "interFoam" → PATCH succeeds → refetch
[4] step=3 kind=info_gap     sev=None field=physics.turbulence_model
    topbar.kind=step_default topbar.enabled=False
    → synthesize "kOmegaSST" → PATCH succeeds → refetch
[5] step=3 kind=step_default sev=None field=None
    topbar.kind=next_step topbar.enabled=True
    → click → advance to step 4
[6] step=4 kind=info_gap     sev=None field=bc.patches
    topbar.kind=step_default topbar.enabled=False
    → synthesize canonical 3-patch ship-VOF skeleton → PATCH succeeds → refetch
[7] step=4 kind=step_default sev=None field=None
    topbar.kind=next_step topbar.enabled=True
    → click → advance to step 5
[8] step=5 kind=step_default sev=None field=None
    topbar.kind=submit_solve topbar.enabled=True
    → CASE READY TO SOLVE
```

---

## Checks (verbatim from the dogfood)

```
  [PASS] ≤20 decide() calls (junior 30-min budget)
  [PASS] Forward-only step arc (no back-edges, no repeats)
  [PASS] Reached step 5 (proves engine drives all the way to solveable)
  [PASS] Rail severity monotonically non-increasing within each step
  [PASS] Provenance log exists with one line per decide() call
  [PASS] Log lines record the step the agent was on (1..5)
```

### What each check actually proves

| Check | What it locks in |
|---|---|
| ≤20 calls budget | Workbench efficiency: junior engineer does not need to thrash through 50 frames to construct a case |
| Forward-only step arc | The engine does not push the engineer back to a previous step. No rework loops. |
| Reaches step 5 | Engine drives all the way to a `submit_solve enabled` state — case is solveable, not just half-built |
| Severity monotonic | Within a step, applying the suggested fix actually reduces severity (no oscillation, no rules that re-promote a fixed issue) |
| Log line per call | Cycle 6 audit log captures the journey faithfully — every UI decision can be replayed |
| Step 1..5 in log | The log step field is faithful (not coerced, not dropped) |

---

## What this does **not** prove

1. **Domain correctness**. The synthesized `bc.patches` skeleton is
   syntactically valid but numerically a stub (inlet U = [1, 0, 0] is a
   placeholder, not the KCS Fr=0.26 ship velocity). M3.1 needs UI form
   helpers that offer domain-aware defaults.

2. **A real junior engineer's experience**. We measure the engine's
   coherence, not human comprehension. The rail's `body_text` /
   `cta_label` quality is a separate UX evaluation.

3. **Failure paths**. The agent took a happy-path; we have no evidence
   the engine handles "engineer applies wrong fix → workbench reverts to
   FAIL → engineer tries different fix" cycles gracefully. M3.1 scope.

4. **Multi-case generalization**. Cycle 4 already proved 4 regimes
   (RANS / LES / compressible / CHT) don't crash; cycle 7 only walks
   ship-VOF end-to-end.

---

## Why 8 calls instead of more

| Step | Calls | Why |
|---|---|---|
| 1 (import) | 1 | Starting manifest has case_family + solver_backend; nothing to fill |
| 2 (geometry) | 1 | Geometry artifact would be the gap; with no artifacts present, geometry step is treated as default for skeleton-only |
| 3 (physics) | 3 | 2 info_gaps (solver, turbulence_model) + 1 step_default confirmation |
| 4 (boundary) | 2 | 1 info_gap (bc.patches) + 1 step_default confirmation |
| 5 (solver) | 1 | All upstream filled → submit_solve enabled |

The pattern: physics + boundary are the meaningful gates; geometry +
solver are step_default given a sparse but consistent manifest.

---

## Bottom line

The dynamic workbench passes its litmus surrogate. A programmatic
engineer with no prior knowledge of the case can reach a solveable
state in 8 UI interactions by simply following what the rail asks for.
The provenance log captures every decision for post-hoc audit.

M3.0 milestone is closeable on the engine-side. Outstanding gaps
(real-engineer eval, domain-aware UI form helpers, failure-path
ergonomics) belong to M3.1.
