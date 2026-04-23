---
retro_id: RETRO-V61-053
title: DEC-V61-053 cylinder arc · Python version parity + 3-round Codex calibration
date: 2026-04-24
trigger: incident-retro (CHANGES_REQUIRED on R1 AND R2 of same DEC)
related_dec: DEC-V61-053
counter_at_retro: 40
---

## Incident summary

DEC-V61-053 is the first DEC to natively satisfy methodology v2.0 (F1-M1 Stage 0
intake + F1-M2 two-tier close). The arc took **3 Codex rounds** to reach
APPROVE — matching the LDC V61-050 Type I precedent. Two distinct
`CHANGES_REQUIRED` verdicts in the same DEC triggers the
`incident-retro` lane (per CLAUDE.md v6.1 autonomous-governance rules).

Codex round outcomes:

| Round | Verdict | Findings |
|-------|---------|----------|
| Plan (Stage 0) | APPROVE_PLAN_WITH_CHANGES | 7 intake edits: blockage 20%, laminar override, u_deficit semantics, Batch B split, forceCoeffs axis, cylinder_crossflow alias, Batch D preflight |
| R1 (post-B1+B2) | CHANGES_REQUIRED | 1H (count-based windowing) + 3M (residual blockage, mesh coarsening, y/z filter missing) + 1L (stale rename promise) |
| R2 (post-R1-fixes + B3) | CHANGES_REQUIRED | Python 3.9 f-string syntax error + 3 stale doc locations the R1 fix missed |
| R3 (post-R2-fixes) | **APPROVE** | Clean |

Final: 11 commits in the DEC arc, B1+B2+B3+C F1-M2-clean.

## What went right

1. **Intake-level risk prediction was accurate.** Round 1 CHANGES_REQUIRED
   landed findings that mapped 1:1 against intake `risk_flags`:
   - `domain_blockage_mismatch` (HIGH) → MED-1 residual blockage
   - `u_mean_centerline_new_extractor` (HIGH) → HIGH-1 windowing bug
   - `sampleDict_interpolation_and_scaling` (MED) → MED-3 y/z filter missing
   - Only `mesh_density` wasn't explicitly intake-flagged — this is a
     methodology gap (see below).

2. **Pass-rate calibration was honest.** Intake predicted 0.30 round-1 pass
   rate; actual was 0 (CHANGES_REQUIRED). That's below target but the gap
   is explainable: intake accounted for adapter + extractor risk, not for
   the sampling-wiring interaction effect. Estimating lower would have been
   more honest, but 0.30 was within the RETRO-V61-001 "pre-merge Codex
   required at ≤70%" band which did fire correctly.

3. **F1-M2 two-tier close worked as designed.** R1 CHANGES_REQUIRED → R2 →
   R2 CHANGES_REQUIRED → R3 → R3 APPROVE. The gate didn't let
   APPROVE_WITH_COMMENTS sneak through; every "almost clean" verdict got a
   mandatory follow-up round. This is exactly what methodology v2.0 was
   designed for (BFS V61-052 round-4 back-fill was the original
   incident that drove F1-M2).

4. **Batch-splitting after Codex plan review prevented blast-radius bugs.**
   Original batch plan had B1 as one commit; Codex pre-Stage-A review split
   it into B1a (adapter physics) + B1b (sampling infrastructure) + B2
   (extractor module) + B3 (wiring). The py3.9 syntax bug landed in B1a
   only; the split made it easy to bisect and fix without touching B1b/B2/B3.

## What went wrong

### P0 · Python version parity (new methodology gap)

**Incident**: Round 2 FAIL on `python3 -m py_compile src/foam_agent_adapter.py`
with `SyntaxError: f-string: expecting '}'` at line 4795. The nested
multi-line f-string conditional I wrote in B1a parses under Python 3.12
(project `.venv`) but not under Python 3.9 (system `python3`, Codex shim
default, CI shim default).

**Why it happened**: I verified syntax locally with `./.venv/bin/python -c "import ast; ast.parse(...)"` which passed. But `.venv` is 3.12 while both
Codex's compile check and system CI default to 3.9. PEP-701 relaxed
f-string grammar was adopted in 3.12; 3.9 has stricter rules that reject
nested multi-line expressions with embedded f-strings.

**Methodology implication**: The intake v2.0 `risk_flags` template does NOT
include a `python_version_parity` category. Adding one would have caught
this at Batch A (when my local syntax passed but nothing verified 3.9
parity). Recommended retroactive P2 patch to the LDC methodology page §8:
- Add `python_version_parity` to the intake risk_flags template
- Add a mandatory step in Stage A: run `python3 -m py_compile <changed_files>` 
  even if .venv tests pass
- Consider adding `.pre-commit-config.yaml` hook for dual-version compile

### P1 · Mesh-density risk not in intake

**Incident**: Round 1 MED-2 surfaced that my (400, 200, 1) block scaling was
a 50% coarsening vs. pre-B1 resolution (old 0.05D → new 0.075D near cylinder).
Intake had a `forceCoeffs_axis_convention` risk but no `mesh_density_on_grow`
risk.

**Why it happened**: When I picked domain-grow option (b), I focused on
blockage (the HIGH risk) and treated mesh as an afterthought. The implicit
assumption "scale cells proportionally" became "halve the resolution
because the mesh scaled 3x but I only scaled 2x".

**Methodology implication**: Add a `mesh_density_on_domain_change` risk flag
to the intake template for any DEC that changes blockMesh dimensions. Very
narrow — only fires when dx or dy changes by > 10%. Low-friction addition.

### P2 · Stale alias doc not caught by R1 fix

**Incident**: Round 2 MED-1 surfaced that `cylinder_crossflow.yaml` (the
legacy alias) still had pre-B1 wording in 3 places (geometry_assumption,
laminar precondition, blockage precondition), even though I had updated
those same sections in `circular_cylinder_wake.yaml` during R1 fixes.

**Why it happened**: My R1 fix commit updated circular_cylinder_wake.yaml
carefully but I "merged" the same physics_contract block into the alias
only partially. The "keep in sync" comment was honored in spirit
(contract_status line matched) but not in letter (individual precondition
blocks drifted).

**Methodology implication**: Two-file syncs are brittle. When a Batch A
decision says "sync both files", the Batch A verification should include a
diff-contract check that asserts the two physics_contract blocks are
field-wise identical modulo comments. Low-priority follow-up; probably
better solved by the post-V61-053 alias-consolidation DEC that deletes
cylinder_crossflow.yaml entirely.

## Numeric calibration metrics

Compare DEC-V61-053 to prior Type I / Type II arcs:

| DEC | Type | Intake est. | Rounds | Actual outcome | Arc/round | Notes |
|-----|------|-------------|--------|----------------|-----------|-------|
| V61-050 (LDC) | I | 0.70 (late-arc) | 4 | APPROVE r4 | retrofit | Pre-v2.0; no intake signature |
| V61-052 (BFS) | II | 0.45 | 5 (incl. r4 back-fill) | APPROVE r5 | back-fill | V61-052 exposed the F1-M2 gap |
| V61-053 (cyl) | I | **0.30** | **3** | **APPROVE r3** | **on-target** | First v2.0 first-apply |

V61-053 is the first DEC where:
- intake + plan-review scoped the arc before code
- 3-round Codex arc completes on schedule (intake predicted 3-4 soft target)
- F1-M2 gates caught an APPROVE_WITH_COMMENTS path that would have closed silently under v1.0

## Recommendations for future DECs

1. **Adopt P0/P1 methodology patches** (python_version_parity + mesh_density_on_domain_change) into the intake template at `.planning/intake/TEMPLATE.yaml` (needs creating; V61-053 was free-form).

2. **Batch D can start** from this clean B1+B2+B3+C state. It's frontend (Compare-tab multi-dim UI + solver_output figure) and will need its own Codex round post-close per F1-M2. Audit fixture regen remains the blocker for end-to-end Batch D verification but not for code landing.

3. **Intake template lesson**: add a `verified_on` field listing actual Python versions (3.9 AND 3.12) that all Stage A commits must compile under. Belongs in P2 methodology patch.

4. **Retro cadence** — this is the first DEC-arc incident retro under v2.0 F1-M2 rules. The "write retro when CHANGES_REQUIRED fires twice in same DEC" trigger works; keeping it.

## Counter status

`autonomous_governance_counter_v61`: **40** after DEC-V61-053 lands. Up from
39 (V61-052 close). Well under any soft-review threshold. V61-053 still
IN_PROGRESS (Batch D + fixture regen pending) so no counter bump yet from
full close.

## Cross-refs

- DEC file: `.planning/decisions/2026-04-23_cfd_cylinder_multidim_dec053.md`
- Intake: `.planning/intake/DEC-V61-053_circular_cylinder_wake.yaml`
- Codex logs: `reports/codex_tool_reports/dec_v61_053_{plan_review,round1,round2,round3}.log`
- Methodology: Notion page `34bc68942bed8189be77c703cc62d0f4` §8 (v2.0 patches)
