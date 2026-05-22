# DOGFOOD · M3.0 Cycle 7 · junior-engineer beginner test (litmus surrogate)

**DEC**: `2026-05-23_v61_202_sub_m30_cycle7_beginner_test.md` (Proposed)
**Date**: 2026-05-23
**Dogfood script**: `scripts/dogfood/case_007_cycle7_beginner_test.py`
**Verdict**: **PASS** (8/8 checks · all-PASS gate · post Codex R0+R1 P2 fixes)
**Codex**: R0 = 2 P2 (severity vacuous, transitions client-side) · R1 = 2 P2
(step-5 CTA not validated, target_step=0 crashes harness) — all fixed
verbatim, 2 rounds total under v2.3 cap=3.

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

## Checks (verbatim from the dogfood · post R2)

```
  [PASS] ≤20 decide() calls (junior 30-min budget)
  [PASS] Forward-only step arc (no back-edges, no repeats)
  [PASS] Backend topbar.target_step is well-formed (frm+1, ≤5, never -1)
  [PASS] Step-5 terminal CTA contract (submit_solve, target_step=None, enabled)
  [PASS] Reached step 5 (proves engine drives all the way to solveable)
  [PASS] Rail severity monotonically non-increasing within each step
  [PASS] Provenance log exists with one line per decide() call
  [PASS] Log lines record the step the agent was on (1..5)
```

### Severity trace (post R1 · severities now exercised for real)

| Step | Severity ranks | Reading |
|---|---|---|
| 1 | `[0]` | step_default · nothing to fill, engineer advances |
| 2 | `[0]` | step_default · same |
| 3 | `[3, 3, 0]` | **critical** (physics.solver) → **critical** (physics.turbulence_model) → step_default. Rank stays 3 across two different gap fields, then drops to 0 — monotonic non-increasing satisfied. |
| 4 | `[3, 0]` | **critical** (bc.patches) → step_default after canonical 3-patch fill |
| 5 | `[0]` | step_default · submit_solve enabled |

Step transitions captured directly from backend `topbar.target_step`:
`[(1, 2), (2, 3), (3, 4), (4, 5)]` — all strictly forward, all one-step.

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

## Codex closure (2 rounds · 4 P2 fixes verbatim · under v2.3 cap=3)

**R0** (2 P2):
- **P2 #1**: severity-monotonic check was reading `rail.severity` (no such
  field on the wire schema) and `SEVERITY_RANK` missed `critical`/`warning`
  (the gap vocabulary). Every frame collapsed to rank 0 → check vacuous.
  Fix: parse severity from `rail.provenance` (mirroring cycle 6 log writer)
  and extend rank map to cover both vocabularies. Severities now show
  rank 3 (critical) at the gap-driven frames, dropping to 0 as fills land.
- **P2 #2**: step advance ignored `topbar.target_step` — a back-edge or
  skip from the backend would still PASS. Fix: capture every transition
  in `step_transitions` and assert each is one-step forward (`to == frm+1`,
  `to ≤ 5`, never -1). New check #3 added.

**R1** (2 more P2 — second-order holes from the R0 fixes):
- **P2 #1**: step-5 terminal CTA not validated. If decide() regresses and
  emits `kind=next_step` or non-null `target_step` at step 5, the test
  still PASSed because `current_step == 5` broke out unconditionally.
  Fix: snapshot the step-5 topbar before breaking; validate
  `kind=submit_solve, target_step=None, enabled=True`. New check #4 added.
- **P2 #2**: `target_step=0` or negative would crash the harness on the
  next `/workbench_frame?step=0` GET before `transitions_well_formed`
  could fire. Fix: validate `1 <= target <= 5` before assigning; record
  `(current_step, bad_target)` so the existing check fails loudly with
  the offending payload visible.

## Bottom line

The dynamic workbench passes its litmus surrogate. A programmatic
engineer with no prior knowledge of the case can reach a solveable
state in 8 UI interactions by simply following what the rail asks for.
The provenance log captures every decision for post-hoc audit.

M3.0 milestone is closeable on the engine-side. Outstanding gaps
(real-engineer eval, domain-aware UI form helpers, failure-path
ergonomics) belong to M3.1.
