---
decision_id: DEC-V61-202-SUB-M31-CYCLE4-LES-EXTENSION-REGISTRY-EXTRACT
title: M3.1 cycle 4 — LES family skeleton extension + registry extraction to shared module
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: R0 (2 P2: pimpleFoam path + LES_*-prefixed) → R1 (1 P2: bare LES) → R2 (1 P2: les_transient rename) → R3 (1 P1: backward-compat shim — user-ratified non-issue, same-day rename had zero production exposure)
final_commit: a7d300b
user_ratification: 2026-05-24 AskUserQuestion — "Accept R3 P1 as non-issue, close cycle 4 (Recommended)"
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.1 cycle 4 (3rd skeleton entry + module extraction trigger)
notion_sync_status: synced 2026-05-24 (https://www.notion.so/36ac68942bed81af8e3ee0d3882510f2)
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M31-CYCLE1-FORM-HELPER-SHIPVOF
  - DEC-V61-202-SUB-M31-CYCLE3-RANS-FAMILY-SKELETON
---

## Why

Two converging triggers:

1. **Registry extraction trigger fires**. Cycle-1 TODO + cycle-3 R0
   P2 stopgap both said "extract `_FORM_HELPER_SKELETONS` +
   `_SOLVER_TO_CASE_FAMILY_CANDIDATES` + `_CASE_FAMILIES_WITH_HELPERS`
   to a shared module when registry grows past 3 entries". Adding a
   3rd skeleton triggers extraction. The duplicate
   `_CASE_FAMILIES_WITH_HELPERS` in analyzer.py becomes auto-derived
   from the canonical registry, eliminating the drift risk Codex
   cycle-3 R0 flagged.

2. **LES coverage gap**. M3.0 retro Open Question #5 noted that
   cycle 4's multi-regime dogfood proved 4 regime classes don't crash
   decide() but only ship-VOF was exercised end-to-end. LES is the
   most common 3rd-helper candidate after ship_vof + RANS — pisoFoam
   + LES turbulence is the dominant incompressible transient case.

## What

### In scope

1. **New module `ui/backend/services/case_family_registry.py`**:
   - `FORM_HELPER_SKELETONS: dict[tuple[str, str], dict]` — moved
     from workbench_decide.py
   - `SOLVER_TO_CASE_FAMILY_CANDIDATES: dict[str, frozenset[str]]` —
     moved from analyzer.py
   - `CASE_FAMILIES_WITH_HELPERS: frozenset[str]` — auto-derived
     from `FORM_HELPER_SKELETONS` keys (single source of truth)
   - `helper_candidate_applies(solver: str | None, turbulence_model:
     str | None) -> bool` — extracted gate function

2. **New entry: les_incompressible**:
   ```python
   ("bc.patches", "les_incompressible"): {
       "inlet":  {"patch_type": "fixedValue",   "fields": {"U": [5.0, 0.0, 0.0]}},
       "outlet": {"patch_type": "zeroGradient", "fields": {"p": "zeroGradient"}},
       "wall":   {"patch_type": "noSlip",       "fields": {}},
   },
   ```
   Same 3-patch structural shape (cycle-1 pattern proven). Placeholder
   velocity 5 m/s — engineers override post-apply.

3. **New solver candidate**: `pisoFoam → {les_incompressible}`.
   pisoFoam is transient incompressible; gated on turbulence_model
   being LES-class (Smagorinsky, dynamicSmagorinsky, kEqn,
   dynamicKEqn, WALE). RANS-class or laminar pisoFoam runs don't
   match LES skeleton.

4. **Extracted gate function** `helper_candidate_applies()`:
   per-solver predicate consolidating cycle-3's inline laminar check
   plus the new LES check. Cleaner than scattered solver-name
   string-compare branches.

5. **Import updates**:
   - `ui/backend/services/workbench_decide.py`: remove
     `_FORM_HELPER_SKELETONS`, import from new module
   - `ui/backend/services/case_completeness/analyzer.py`: remove
     `_SOLVER_TO_CASE_FAMILY_CANDIDATES`,
     `_CASE_FAMILIES_WITH_HELPERS`,
     `_case_family_helper_candidate_applies`; replace with imports

6. **Tests** (add to existing files):
   - `test_decide_attaches_les_bc_patches_skeleton_on_step4_pisofoam`
   - `test_decide_les_skeleton_uses_5ms_velocity_distinguishes_from_rans`
   - `test_imported_pisofoam_smagorinsky_case_without_case_family_emits_warning`
   - `test_imported_pisofoam_laminar_case_no_warning` (gate negative)
   - `test_imported_pisofoam_kOmegaSST_case_no_warning` (RANS-gate negative)
   - `test_registry_extracted_module_has_3_skeletons` (sanity check)

### Out of scope (later cycles)

- compressible_steady (rhoSimpleFoam) — cycle 5+
- chtMultiRegion (CHT) — cycle 6+
- LES sub-families (channel-LES, jet-LES) — needs UI to disambiguate
- Skeleton field-level validation (Smagorinsky constant ranges,
  etc.) — orthogonal cycle

## Closure criteria

- [ ] New module `case_family_registry.py` exists with 3 skeleton
      entries + per-solver gate
- [ ] analyzer.py + workbench_decide.py import from new module (no
      local duplicates)
- [ ] 6 new tests added per matrix above, all pass
- [ ] Existing 79 backend tests still pass (no regressions from
      extraction)
- [ ] Frontend regression PASS (917+ tests; no UI change expected)
- [ ] Codex review ≤ 3 rounds (v2.3 cap)
- [ ] DEC Proposed → Accepted
- [ ] Notion sync (session-end, Accepted DECs only)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Import-cycle: analyzer ↔ workbench_decide via registry | New registry imports nothing project-internal — pure data + functions. Safe |
| `CASE_FAMILIES_WITH_HELPERS` auto-derivation breaks if FORM_HELPER_SKELETONS gets `(field_path, family)` tuples where field_path varies | Cycle 1-4 all use `bc.patches`; auto-derive via `frozenset(family for (fp, family) in FORM_HELPER_SKELETONS.keys())` — robust to multiple field_paths per family |
| LES turbulence model list is incomplete (misses WALE, dynamicKEqn variants) | Cycle 4 ships {Smagorinsky, dynamicSmagorinsky, kEqn, dynamicKEqn, WALE}; cycle 5+ can extend as production data shows other models in use |
| pisoFoam users running RANS turbulence are common (DES, transient RANS) | The gate correctly excludes them — they get no LES advisory, percentage stays at 100% |
| Existing fixtures using pisoFoam without case_family suddenly drop to 80% | Surface scan: `grep pisoFoam` reveals existing fixtures; verify each case_family declared or path is laminar/RANS turbulence (which the gate excludes) |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Cycle-1 TODO: "Extract to shared registry when 3+ entries"
- Cycle-3 R0 P2 stopgap: `_CASE_FAMILIES_WITH_HELPERS` duplicates
  registry knowledge; extraction eliminates this
- M3.0 retro Open Question #5: multi-regime coverage of decide()
- User mandate 2026-05-24: "如果完成了一个步骤，获得了下一步的建议，
  则自动执行每一个新的建议"

Surface-scan-found:
  · `ui/backend/services/workbench_decide.py::_FORM_HELPER_SKELETONS`
  · `ui/backend/services/case_completeness/analyzer.py::_SOLVER_TO_CASE_FAMILY_CANDIDATES`
  · `ui/backend/services/case_completeness/analyzer.py::_CASE_FAMILIES_WITH_HELPERS`
  · `ui/backend/services/case_completeness/analyzer.py::_case_family_helper_candidate_applies`

Disposition: extract (move to new shared module); analyzer + decide
gain import; no parallel-new file conflict; no rename of existing
function names downstream.
