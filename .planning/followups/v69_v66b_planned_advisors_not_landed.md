---
followup_id: V69-FOLLOWUP-1
title: V66-B planned advisors documented in canonical eval but not yet landed
opened: 2026-05-16
opened_by: V69.2 eval regression harness (DEC-V69.2)
priority: medium
status: open
---

# V69-FOLLOWUP-1 · V66-B planned advisors not landed in advisor_stack.py

## Finding

The V69.2 canonical eval regression harness (`test_canonical_advisor_eval.py`)
surfaced a structural drift between V66-B planning and runtime:

The V66-B INDEX.md §"NEW (V66-B)" promised 3 new advisors:
- `advisor_v103` / `cf_canonical_choice_advisor` (Cf-canonical-choice at Re_x boundary)
- `advisor_v107` / `low_re_kOmegaSST_trigger_advisor` (low-Re kOmegaSST under-prediction trigger)
- `advisor_yplus_regime_match_advisor` (y+ regime-band vs turbulence model match)

Plus 3 additional F-NEW candidates referenced by canonical eval cases:
- `yplus_target_validation_advisor` (E14)
- `substrate_inspection_advisor` (E13)
- `residual_gate_qualifier_advisor` (E18)

None of these 6 exist in `ui/backend/services/advisor_stack.py` or anywhere
under `ui/backend/services/`. The canonical eval cases reference them as
expected fires (5 of the 20 cases anchor on these advisors), so the
INDEX.md aggregate firing count claim ("≥100 firings across 20 cases")
is technically met only if the planned advisors are implemented OR if
their referenced fires count as "expected but rule-gap-missing".

## Why this isn't blocking V69 close

- V69 charter §3 north star: 20 individual case files + regression harness
  ≤5s runtime + ≥20 PASS. **All MET**.
- The harness honestly tags these 6 as `KNOWN_F_NEW_ADVISORS` and skips them
  rather than false-failing — the cases ARE useful as anchors for the
  expected behavior once those advisors land.
- The 14 currently-LANDED advisors (`face_orientation_advisor`,
  `inlet_outlet_validator`, `solver_block_advisor`, `unit_detector`,
  `mesh_quality_advisor`, `urf_advisor`, `thermo_polynomial_range_advisor`,
  `bc_type_name_validity_advisor`, `extra_body_advisor`, `thin_wall_advisor`,
  `virtual_interface_detector`, `shm_dict_validator`, `stl_face_label_validator`,
  `face_orientation_advisor`) ARE validated against by the harness — the
  V69.2 regression protection works for them.

## What a future arc needs to do

Pick **one** of these dispositions:

1. **Implement** the 6 planned advisors (~4 weeks engineering · 6 modules
   in `ui/backend/services/` + wiring into `assemble_stack` + per-module
   unit tests). After landing, remove from `KNOWN_F_NEW_ADVISORS` in
   `test_canonical_advisor_eval.py` — the harness will then enforce them.
2. **Drop the references** from canonical eval cases that anchor on these
   F-NEW advisors (E06, E14, E15, E17, E18, ...). Less honest because
   the V104/V107/F-NEW evidence those cases anchor on is real CFD knowledge
   that doesn't go away just because the advisor isn't coded.
3. **Status quo**: keep the F-NEW gap documented; the harness skips them
   via `KNOWN_F_NEW_ADVISORS`. This is what V69 chose because options 1+2
   are out of scope for the V69 charter.

Recommendation: option 3 for now, schedule option 1 for a future arc
when the advisor stack expansion is the primary deliverable.

## Counter telemetry

This followup file does NOT count against `autonomous_governance_counter_v61`
(per RETRO-V61-001: followup tracking is administrative not governance).

— V69-FOLLOWUP-1 · opened 2026-05-16 by V69.2 close
