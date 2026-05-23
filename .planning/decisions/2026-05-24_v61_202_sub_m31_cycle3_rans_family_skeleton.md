---
decision_id: DEC-V61-202-SUB-M31-CYCLE3-RANS-FAMILY-SKELETON
title: M3.1 cycle 3 — domain-aware form helper · rans_steady_incompressible bc.patches skeleton
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: R0 (2 P2) → R1 (1 P2 - same as cycle-1 R7 ratified defeat) → R2 APPROVE
final_commit: 436d4b8
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.1 cycle 3 (registry extension to RANS family)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M31-CYCLE1-FORM-HELPER-SHIPVOF  # cycle 1 shipped the registry pattern
  - DEC-V61-202-SUB-M31-CYCLE2-UI-LABELER-SCALAR-INPUT  # cycle 2 closes case_family UI affordance
---

## Why

Cycle 1 ships `_FORM_HELPER_SKELETONS` with exactly one entry
(`(bc.patches, ship_vof)`). The cycle-1 retro explicitly recommended
"M3.1 cycle 2 should extend to one more family (recommend
`rans_steady_incompressible` since cycle 4's multiphysics dogfood
already exercises it) to prove the lookup pattern scales."

Cycle 2 took the case_family UI labeler path first because the
unactionable Step-1 rail prompt was a more user-visible defect.
Cycle 3 now lands the cycle-1-recommended extension: add a second
`(field_path, case_family)` entry + a second
`_SOLVER_TO_CASE_FAMILY_CANDIDATES` mapping for simpleFoam, validating
that:

1. The registry pattern accepts multiple entries cleanly
2. Demand-driven advisory generalizes (interFoam fires ship_vof
   candidate; simpleFoam fires rans_steady_incompressible candidate;
   no cross-pollination)
3. The TODO in cycle 1's "extract to shared registry" comment can
   stay deferred — two entries is still inline-comfortable; the
   extract triggers at 3+

## What

### In scope

1. **Backend — `_FORM_HELPER_SKELETONS`**: add entry
   ```python
   ("bc.patches", "rans_steady_incompressible"): {
       "inlet":  {"patch_type": "fixedValue",   "fields": {"U": [10.0, 0.0, 0.0]}},
       "outlet": {"patch_type": "zeroGradient", "fields": {"p": "zeroGradient"}},
       "wall":   {"patch_type": "noSlip",       "fields": {}},
   },
   ```
   The structural shape is intentionally identical to `ship_vof`
   (inlet/outlet/wall — minimal RANS-external-aero baseline). The
   placeholder velocity is 10 m/s (flat_plate fixture default) —
   engineers override post-apply. Other RANS sub-families (channel
   with cyclic, BFS with step) are future cycle scope.

2. **Backend — `_SOLVER_TO_CASE_FAMILY_CANDIDATES`**: add
   ```python
   "simpleFoam": frozenset({"rans_steady_incompressible"}),
   ```
   simpleFoam → {rans_steady_incompressible}; previously had no
   helper candidate (cycle-1/2 only knew interFoam → ship_vof).

3. **Backend — advisory copy**: update the case_family warning's
   `why` text to mention both candidates contextually. The text
   should adapt to the current solver: interFoam → ship_vof
   suggestion, simpleFoam → rans_steady_incompressible suggestion.

4. **Backend — tests**:
   - `test_decide_attaches_rans_bc_patches_skeleton_on_step4_simplefoam`
     (analog of ship_vof skeleton test for simpleFoam manifest)
   - `test_decide_no_cross_pollination_simplefoam_does_not_get_ship_vof_skeleton`
   - `test_imported_simplefoam_case_without_case_family_emits_warning`
     (UPDATE: was a negative test; flip to positive now that simpleFoam
     has a candidate)
   - `test_imported_simplefoam_case_with_rans_family_no_warning`
     (positive cleanup case)

5. **Frontend — `INLINE_EDITABLE_SCALAR_PATHS`**: no change (cycle 2's
   allow-list already covers `case_family` for both flavors).

6. **Dogfood** — extend or add: walk a simpleFoam case through the
   labeling-then-skeleton flow analogous to cycle 1's dogfood.

### Out of scope (later cycles)

- **LES / compressible / CHT extensions** — cycle 4+
- **Sub-family handling** (channel-cyclic, BFS-step, atmospheric-BL)
  — needs UI to disambiguate; cycle 5+
- **Type-aware skeleton fields** (velocity numerics validation,
  turbulence intensity bounds) — cycle 6+
- **Registry extraction to shared module** — triggers at 3+ entries;
  cycle 4 if a third family is added

## Closure criteria

- [ ] `_FORM_HELPER_SKELETONS` gains the RANS entry
- [ ] `_SOLVER_TO_CASE_FAMILY_CANDIDATES` gains the simpleFoam entry
- [ ] Backend tests added (4 from matrix above)
- [ ] Existing tests still pass (the simpleFoam negative test must
      flip to positive — cycle-1's `test_imported_simplefoam_case_without_case_family_no_warning`
      becomes outdated, replace with the warning-firing positive)
- [ ] Frontend regression PASS (915+ tests; expect no change)
- [ ] Codex review ≤ 3 rounds (v2.3 cap)
- [ ] DEC Proposed → Accepted
- [ ] Notion sync (session-end, Accepted DECs only)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| RANS skeleton velocity (10 m/s) doesn't match engineer's case | Same disclaimer as cycle 1's 1.0 m/s ship_vof — placeholder, engineer overrides. The skeleton accelerates dict-shape typing, not physics defaulting |
| simpleFoam isn't always RANS-steady (could be steady laminar, transitional, etc.) | The candidate set means "this solver could benefit from a RANS-class skeleton", not "this case IS RANS-steady". Engineer still labels explicitly via cycle-2 UI input. Per cycle 1 R1 rationale (no auto-classification) |
| The cycle-1 negative test (`test_imported_simplefoam_case_without_case_family_no_warning`) now becomes outdated | Replace it with the positive test (warning fires for simpleFoam too). Document the rationale change in commit message |
| Existing fixtures using simpleFoam without case_family suddenly drop to 80% | All fixture cases either declare case_family or set physics.solver to a non-candidate. Surface scan: `grep simpleFoam ui/backend/audit/cases/*/case_manifest.yaml` + check whether each has case_family. If not, fixtures need case_family added or test must mark them as known-warning |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Cycle-1 DEC bottom-line explicitly recommended this work as cycle 2;
  cycle 2 took UI labeler first, this cycle now lands the registry
  extension as cycle 3
- M3.0 retro Open Question #2 (domain-aware UI form helpers across
  case families)
- User authorization 2026-05-24: "如果完成了一个步骤，获得了下一步的建议，
  则自动执行每一个新的建议"

Surface-scan-found: `ui/backend/services/workbench_decide.py::_FORM_HELPER_SKELETONS` +
`ui/backend/services/case_completeness/analyzer.py::_SOLVER_TO_CASE_FAMILY_CANDIDATES` ·
disposition: extend (add 2nd entry to each); no parallel-new file,
no rename, no break.
