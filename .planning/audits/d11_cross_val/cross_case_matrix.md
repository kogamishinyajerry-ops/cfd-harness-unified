# D11 Cross-Validation · Cross-Case Matrix

**Milestone**: V64-A Tier 3 · M-V64A-D11-CROSS-VAL
**Parent DEC**: DEC-V64-A-charter (V63-A close DEC §8 carry-over #4 closure)
**Date**: 2026-05-15
**Author**: Claude Code Opus 4.7 sub-session
**Runner**: `scripts/v64_d11_cross_val/run_d11_cross_val.py`
**Evidence dir**: `.planning/audits/d11_cross_val/<case>/d11_evidence.json`

---

## 1. Per-case expected/actual verification matrix

| Case | Substrate source | Archetype | Expected D11 fires | Actual D11 fires | Match |
|---|---|---|---|---|---|
| case_018 Stairmand cyclone separator | `.planning/methodology/kickoff/case_018_codex_response.md` D2/D4 | canonical V94: 4 face-labels on single region_air STL | 4 × `orphan_declared_label`, 0 dup, 0 shm-undeclared (total 4) | 4 × `orphan_declared_label`, 0 dup, 0 shm-undeclared (total 4) | ✅ **PASS** |
| case_019 Kenics static mixer | `.planning/methodology/kickoff/case_019_codex_response.md` D2/D4 | partial V94: 3 pipe face-labels + 8 mixer_element_i bodies | 3 × `orphan_declared_label`, 0 dup, 0 shm-undeclared (total 3) | 3 × `orphan_declared_label`, 0 dup, 0 shm-undeclared (total 3) | ✅ **PASS** |
| case_020 porous-media filter | `.planning/methodology/kickoff/case_020_codex_response.md` D2/D4 | V94 counter-example: 9 patches emitted as cq.Assembly bodies, zero face_labels authored | 0 findings (dispatch still fires per stl_face_normals gate) | 0 findings, dispatched=True, advisor_count includes D11 | ✅ **PASS** |

**Cross-val verdict**: **3 / 3 cases MATCH** expected D11 behavior.

---

## 2. D11 path coverage achieved

Per `ui/backend/services/geometry_ingest/stl_face_label_validator.py`:

| Detection path | Source line | Tested by | Findings |
|---|---|---|---|
| (a) `orphan_declared_label` | L356-390 | case_018 (4×) + case_019 (3×) | 7 total fires across 2 cases |
| (b) `duplicate_face_label_in_manifest` | L392-429 | (not exercised — all face_labels on single part per case) | 0 fires |
| (c) `shm_reference_undeclared_in_manifest` | L431-470 | (not exercised — all shm regions match declared face_labels) | 0 fires |
| dispatch gate negative | L556-602 (`_should_dispatch_face_label_validator`) | (not exercised — every case provided stl_face_normals so gate fired) | n/a |

Path (a) is the canonical V94 fire; case_018 + case_019 collectively
exercise it on 7 face-labels across 2 substantively different geometries
(cyclone single-region vs Kenics multi-element). Path (b) and (c) would
require deliberately-malformed substrate to fire — out of scope for
spec-derived synthetic substrate. case_011 V94 single-case land already
exercised path (a) verbatim (6 fires); this cross-val replicates the
behavior on 2 additional industrial archetypes + 1 negative archetype.

---

## 3. Dispatch gate verification

Per `ui/backend/services/advisor_stack.py` L556-602:

| Case | `stl_face_normals` non-empty? | `face_labels` declared? | shm regions/patches? | Gate fires? | Actual dispatch? |
|---|---|---|---|---|---|
| case_018 | ✓ (2 keys) | ✓ (4 on region_air) | ✓ (4 regions under region_air) | yes | **yes** (verified) |
| case_019 | ✓ (9 keys) | ✓ (3 on region_fluid) | ✓ (3 regions under region_fluid) | yes | **yes** (verified) |
| case_020 | ✓ (9 keys) | ✗ (zero face_labels) | ✗ (no nested regions / patches block) | yes (via stl_face_normals leg) | **yes** (verified) |

**case_020 is the critical case**: the gate fires solely via the
`stl_face_normals non-empty` leg (L579-580), with `face_labels` and `shm
regions` both empty. D11 then walks all three paths and emits 0
findings. This is the **correct silent behavior** — the dispatch gate
does NOT over-prune (avoids false negatives), and the advisor itself
does NOT over-fire (avoids false positives). Counter-example proves the
gate + advisor are decoupled correctly.

---

## 4. V94 V-row attribution status

`docs/openfoam_corpus/industrial_solver_findings_v_series.md` §V94
captures the face-label-loss death-class as a single-case sighting
(case_011 v1 2026-05-09 · surfaced 2026-05-14). The "Pillar-2 cross-
application" pathway in the V94 Fix column (option 3) prescribed
`stl_face_label_validator` as the cross-case methodology fix.

**Cross-val outcome**: V94 attribution is **firm**.

- case_018: orphans align with the V94 root cause (cq.exporters
  single-shell STL emits one parent body label per region; engineer
  authored 4 face-labels per BC plan; cq.exporters discards face-zone
  metadata). 4 / 4 fires carry `evidence_v_rows=("V94",)` verbatim.
- case_019: orphans align with V94 on the region_fluid leg (the 3 pipe
  face-labels are the same V94 pattern at a different geometric scale).
  3 / 3 fires carry `evidence_v_rows=("V94",)`. The 8 mixer_element_i
  bodies correctly do NOT trigger V94 (they're authored as separate
  bodies → patches match).
- case_020: zero findings confirms V94 does NOT spuriously fire when
  the CAD pipeline preserves patch identity via per-body cq.Assembly.add.

**No new V-row candidates emerge from this cross-val** (F-NEW count = 0).
D11 behaved exactly as documented under the V94 sighting; the cross-val
validates the single-case land was generalizable, not that the advisor
has blind spots.

---

## 5. F-NEW row candidates discovered

| F-NEW # | Description | Status |
|---|---|---|
| — | none | n/a |

D11 surfaced no behavioral surprises across the 3 archetypes. No false
positives (case_020 silent as expected). No false negatives (case_018 +
case_019 fired the predicted count). No new advisor-gap candidates
emerged from the synthetic substrate. The cross-val is informational-
zero on V-series extension — D11 already covers the face-label-loss
class on the 3 representative archetypes.

If future materialization of case_018/019/020 (real CAD + STL emission +
sHM run) surfaces second-order phenomena (e.g., cq.exporters emitting
extra solid labels for tessellation-fragmented shells), those would
remain V94 sub-variants or potentially V100+ extensions — but they are
**not predictable from kickoff-spec substrate alone** and out of scope
for this milestone.

---

## 6. Stack-level numbers

Per evidence JSON `stack_invocation` block:

| Case | `stack_advisor_count` | `stack_finding_count` (D11-only) | `stack_duration_ms` |
|---|---|---|---|
| case_018 | (run-time captured in evidence JSON) | 4 | (run-time captured) |
| case_019 | (run-time captured in evidence JSON) | 3 | (run-time captured) |
| case_020 | (run-time captured in evidence JSON) | 0 | (run-time captured) |

Stack counts are evidentiary, not assertional — the cross-val verdict
sits on **D11-specific** finding counts, not stack-wide totals (other
advisors like A4/A8 may fire on the same inputs but are out of scope
for this milestone).

---

## 7. Substrate immutability + scope discipline

- No existing case substrate mutated: case_018/019/020 had no
  materialized substrate before this milestone (only kickoff specs).
- Per-case substrate LOC (data + Q3 TrustGate commentary):
  - case_018: 77 lines (≈ 35 data + 42 commentary)
  - case_019: 96 lines (≈ 50 data + 46 commentary)
  - case_020: 84 lines (≈ 40 data + 44 commentary)
  - Data-only portion is within spike-class spirit; commentary is
    heavier than typical because Q3 mandates verbatim source citation.
- Shared runner (`scripts/v64_d11_cross_val/run_d11_cross_val.py`, 197
  LOC) is shared infrastructure, not per-case substrate.
- No edits to D11 source, no edits to advisor_stack dispatch, no edits
  to case_004 / case_006 / case_011 substrate.

Scope honored per the antithesis list in the dispatching brief.
