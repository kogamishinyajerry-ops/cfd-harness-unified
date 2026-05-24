# DOGFOOD · M3.1 Cycle 5 · failure-path ergonomics

**DEC**: `2026-05-24_v61_202_sub_m31_cycle5_failure_path_dogfood.md` (Proposed)
**Date**: 2026-05-24
**Dogfood script**: `scripts/dogfood/case_007_cycle5_failure_path.py`
**Verdict**: **FAIL on initial run (cycle-5 close) · PASS after cycle-6 fix lands** (BUG-1, BUG-2 closed by `DEC-V61-202-SUB-M31-CYCLE6-PATCH-TYPE-PRESERVATION`)
**Cycle 5 scope**: document the failure path, file backlog. Do NOT
fix bugs in this cycle. M3.0 retro Open Question #3 closure: the
workbench's failure-path behavior is now inventoried, not just
hypothesized.

**Codex R0 P2+P3 hardening (cycle-5 in-cycle fix, NOT a bug-fix)**:
the dogfood's negative-path predicates were tightened so that future
unrelated 4xx responses (state-SHA mismatch, route contract
regression) cannot false-PASS the cycle-5 contract. Step-5's
`struct_rejected` now requires the response to carry a
type/dict/schema-named validation_errors entry. Step-4's typo
predicate now requires either (a) accepted AND manifest contains the
typo'd value, OR (b) rejected with validation_errors naming
type/value/schema/patch_type. This keeps the cycle-5 regression
signal honest as the codebase evolves.

---

## What the dogfood walked

```
1. Empty manifest → import (no case_family, no bc.patches)
2. PATCH case_family=ship_vof              → forward progress
3. PATCH bc.patches=<canonical 3-patch skeleton> → forward progress
4. PATCH bc.patches.inlet.patch_type=fixedValue_typo  (typo mistake)
5. PATCH bc.patches.inlet="not_a_dict"     (struct-wrong mistake)
6. PATCH bc.patches.inlet.patch_type=fixedValue       (revert)
7. GET frame                                (verify rail clear)
```

## Verdict per step

| Step | Action | Expected | Actual | Verdict |
|------|--------|----------|--------|---------|
| 1 | GET frame on empty manifest | rail surfaces case_family gap | ✓ | PASS |
| 2 | PATCH case_family=ship_vof | 200 success=true | ✓ | PASS |
| 3 | PATCH bc.patches=skeleton | 200 success=true, inlet.patch_type='fixedValue' | ✓ | PASS |
| 4 | PATCH typo `fixedValue_typo` | accept-or-reject coherently (not crash) | accepted silently, manifest carries typo | PASS (predicate met) but **bug-worthy** |
| 5 | PATCH struct-wrong `"not_a_dict"` | reject (inlet must stay dict) | **accepted**, `inlet` overwritten to string | **FAIL** |
| 5 | manifest inlet stays a dict | inlet remains dict | inlet became string | **FAIL** |
| 6 | PATCH revert `inlet.patch_type=fixedValue` | 200 success=true, restored | **400 error** (can't traverse string-valued `inlet`) | **FAIL** |
| 6 | manifest inlet.patch_type=fixedValue | restored | **None** (revert blocked) | **FAIL** |
| 7 | final rail returns to step_default | rail clear | rail IS step_default, but manifest is **corrupted** | PASS predicate, **bug-worthy** |

## Bugs surfaced (cycle-6+ backlog)

### BUG-CYCLE5-1 [P1] · `manifest_patch` accepts wrong-typed values at structural nodes — **FIXED in cycle 6**

**Symptom**: PATCH `bc.patches.inlet = "not_a_dict"` succeeds with
status=200 + success=true. The manifest's `inlet` field is overwritten
from a dict to a string, breaking the schema contract.

**Expected**: 200 + success=false + validation_errors describing the
type mismatch ("expected dict, got str"). The manifest should NOT be
mutated.

**Impact**: Any engineer who mistypes the value of a structural patch
node corrupts the entire patch entry. Recovery requires manually
editing the YAML on disk — the workbench has no path back.

**Fix scope estimate**: medium. `manifest_patch._apply_value()` needs
to validate the new value's type against the existing value's type
(or against the Pydantic schema) before writing. Pydantic re-validation
of the full manifest post-patch would catch this.

**Cycle-6 sub-DEC candidate.** → Fixed by `DEC-V61-202-SUB-M31-CYCLE6-PATCH-TYPE-PRESERVATION` (`_check_type_preservation` helper in `manifest_patch.py`).

### BUG-CYCLE5-2 [P1] · String-corrupted node blocks downstream revert PATCH — **FIXED in cycle 6 (same root)**

**Symptom**: After BUG-CYCLE5-1 corrupts `bc.patches.inlet` to a
string, attempting PATCH `bc.patches.inlet.patch_type = "fixedValue"`
returns 400. The path parser can't traverse a string node, so the
engineer cannot use the same workbench affordance to undo the damage.

**Expected**: either (a) BUG-1 prevents the corruption in the first
place (preferred), or (b) the PATCH endpoint provides a clear
"the path traversal failed at segment X (was string, expected dict)"
error AND a recovery affordance (e.g. "replace whole node").

**Impact**: cascade-blocks recovery. Same root cause as BUG-1; fix
to BUG-1 likely fixes this too.

**Cycle-6 sub-DEC candidate (likely bundled with BUG-1 fix).** → Confirmed: same root, fixed by cycle 6's type preservation. Once BUG-1 prevents the corruption, step-6 revert PATCH succeeds (path traversal never has to descend through a string node).

### BUG-CYCLE5-3 [P2] · Final rail shows step_default despite corrupted manifest

**Symptom**: Step 7 fetches the frame at step 4 with a manifest where
`bc.patches.inlet` is the string `"not_a_dict"` (no patch_type field).
The rail returns `kind=step_default` ("ready to proceed") instead
of surfacing the corruption as a new gap or fail.

**Expected**: the case_completeness analyzer or workbench_decide's
audit pipeline should detect that `bc.patches.inlet` no longer
matches the BCSection.PatchSpec schema, surface as a critical gap or
FAIL on the rail.

**Impact**: engineers see "ready" on a structurally invalid case.
Submit-solve would crash at runtime.

**Fix scope estimate**: medium. Either (a) BUG-1 prevents corruption
upstream (preferred), or (b) the analyzer adds a "manifest schema
re-validation" check that runs on the post-PATCH manifest before
declaring completeness.

**Cycle-6 / cycle-7 sub-DEC candidate.**

### BUG-CYCLE5-4 [P3] · Silent acceptance of typo'd `patch_type` values

**Symptom**: PATCH `bc.patches.inlet.patch_type = "fixedValue_typo"`
succeeds with no validation warning. `fixedValue_typo` is not a real
OpenFOAM patch type.

**Expected**: this might be intentional (OpenFOAM accepts arbitrary
strings here and validates at solver-startup time). But for engineer
ergonomics, the workbench could surface a warning when patch_type
is not in the known-OpenFOAM-types enum (fixedValue, zeroGradient,
noSlip, slip, symmetry, empty, cyclic, processor, etc.).

**Impact**: typos manifest at solver-run time as cryptic OpenFOAM
errors instead of at the workbench's BC step.

**Fix scope estimate**: small (~30 LOC). Add an enum-validation
warning in case_completeness for known patch_type values. Optional —
weigh ergonomics vs free-text flexibility.

**Cycle-7+ sub-DEC candidate (low priority).**

## What this dogfood proves

1. **The happy path works**. Steps 1-3 are clean — labeling +
   skeleton application + manifest write all succeed.

2. **The system DOES NOT validate types at PATCH time**. This is the
   load-bearing finding. `manifest_patch` writes any JSON-serializable
   value at any field_path without consulting the Pydantic schema.

3. **The downstream analyzer DOES NOT catch type-corrupted manifests**.
   Either by design (analyzer assumes manifest passed Pydantic) or by
   oversight. Either way, post-corruption the rail says "ready".

4. **Recovery via the same affordance is blocked**. Engineers who
   corrupt their manifest via the PATCH endpoint cannot un-corrupt
   it via the same endpoint — path traversal fails on corrupted nodes.

These are all real engineering hazards. The dogfood surfaced them in
~150 LOC of script + one execution. **This is exactly what M3.0 retro
Open Question #3 predicted: failure-path coverage finds bugs the
happy-path surrogate cannot.**

## What this dogfood does NOT prove

- Concurrent-edit conflict behavior (covered by `manifest_state_sha`
  separately, not exercised here)
- Multi-step undo / history rewind (out of cycle 5 scope)
- UI's response to backend FAIL state (this is API-only)
- Network-failure handling (no fault injection in this dogfood)
- Solver-runtime failure modes (this is pre-solve only)

## Backlog summary

| Bug | Severity | Cycle for fix | Status |
|---|---|---|---|
| BUG-CYCLE5-1 (PATCH no type validation) | P1 | cycle 6 | **FIXED** (DEC-V61-202-SUB-M31-CYCLE6) |
| BUG-CYCLE5-2 (cascade blocks revert) | P1 | cycle 6 (bundled with -1) | **FIXED** (same root) |
| BUG-CYCLE5-3 (analyzer misses corruption) | P2 | cycle 7 | OPEN — out of cycle-6 scope (analyzer-side hardening for non-PATCH corruption paths) |
| BUG-CYCLE5-4 (typo'd patch_type) | P3 | cycle 7+ | OPEN — ergonomics layer |

## Bottom line

Cycle 5 ships **the inventory**, not the fixes. M3.0 retro's prediction
that the happy path "took the happy path; we have no evidence" is now
upgraded to "we have evidence: the failure path has real bugs". Per
cycle-5 DEC scope, fixes are cycle 6+ work with their own sub-DECs.

The dogfood will live as a regression test once BUG-1/2/3 are fixed —
the verdict should flip from FAIL to PASS as each fix lands.
