---
decision_id: DEC-V64-A-sub-M-V64A-D11-CROSS-VAL
title: D11 stl_face_label_validator cross-validation on case_018 / case_019 / case_020
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 3 · M-V64A-D11-CROSS-VAL (V63-A close DEC §8 carry-over #4)
notion_sync_status: pending (session-end batch sync per v2.3 cadence)
autonomous_governance: true
confidence: med
date_decided: 2026-05-15
codex_review_relay: skipped (no security-boundary touch · v2.2 1-sync-trigger N/A · synthetic substrate YAML + read-only advisor invocation + docs)
codex_round_cap: N/A (no Codex review chain initiated)
kogami_review: skipped (V133 opt-in only · user did not invoke)
spike_class: false (sub-DEC scope · 3 substrate files + runner + evidence + matrix + validation report + sub-DEC)
surface_scan: clean (no new top-level routes/ or pages/ · audit + docs + scripts/v64_d11_cross_val/ scoped)
---

# DEC-V64-A-sub-M-V64A-D11-CROSS-VAL · D11 cross-validation on case_018 / case_019 / case_020

> Tier-3 V64-A milestone: cross-validate D11 (stl_face_label_validator,
> 21 KB · LANDED V63-A B39 via single-case case_011 v5b) on 3 additional
> case archetypes per V63-A close DEC §8 carry-over #4. Substrate
> immutability respected: case_018/019/020 were unmaterialized at start
> of session; additive synthetic substrate derived from kickoff
> codex_response Deliverable 4 parts manifests.

## §1 Context

V63-A close DEC §8 carry-over #4 (verbatim):

> | 4 | D11 cross-case validation (case_018/019/020 · single-case-land
> | discipline) | M-D11-DRAFT sub-DEC | V64-A Tier 3:
> | **M-V64A-D11-CROSS-VAL** |

V63-A landed D11 via single-case case_011 v5b (6 orphan fires · V94
canonical replay · M-D11-DRAFT sub-DEC `DEC-V63-A-sub-D11`). The
[QUESTIONABLE] marker in the D11 source docstring §promotion gate (line
137-140) was carried forward pending a 2nd industrial case sediment. This
milestone discharges that pending state through 3-case cross-val without
requiring case materialization.

## §2 Substrate state diagnosis

case_018 / case_019 / case_020 had **no materialized substrate**:
- No `case_profiles/case_0XX*` files
- No `~/Desktop/case_0XX_*` sandbox directories
- Existing: kickoff dispatch docs under `.planning/methodology/kickoff/`
  carrying codex_request + codex_response pairs (Deliverable 2 CAD
  script + Deliverable 4 parts manifest YAML + Deliverable 5 defect
  manifest)

This is the substrate-gap scenario in the dispatching brief's reverse
condition #1. Per V63-A close §8 carry-over scope authorization on
substrate extension (additive only · do NOT touch existing case
substrate), built minimal synthetic substrate from kickoff specs.

## §3 Decision

**Land D11 cross-val verdict: 3 / 3 PASS.** Specifically:

1. Build additive synthetic substrate (parts_manifest + stl_face_normals
   + shm_dict) under `.planning/audits/d11_cross_val/<case>/substrate.yaml`
   for each of case_018 / case_019 / case_020, derived verbatim from
   kickoff codex_response Deliverable 4.
2. Run D11 directly (`validate_face_label_consistency`) and through
   `assemble_stack` for each case via
   `scripts/v64_d11_cross_val/run_d11_cross_val.py` (env -i offline
   invocation).
3. Capture per-case evidence under `<case>/d11_evidence.json`.
4. Author cross-case matrix at `<case>/../cross_case_matrix.md` +
   validation report at `.planning/validation_reports/v64_d11_cross_val.md`.

**Verdict**: D11 fires correctly on each archetype:

| Case | Archetype | Expected | Actual | Match |
|---|---|---|---|---|
| case_018 cyclone | canonical V94: 4 face-labels on single region_air STL | 4 orphan | 4 orphan | ✅ |
| case_019 Kenics | partial V94: 3 pipe face-labels + 8 mixer body-patches | 3 orphan | 3 orphan | ✅ |
| case_020 porous filter | V94 counter-example: 9 patches emitted as bodies | 0 findings (dispatched) | 0 findings (dispatched) | ✅ |

D11 path coverage by this cross-val:
- Path (a) `orphan_declared_label`: 7 fires across 2 cases (canonical
  + partial archetype).
- Path (b) `duplicate_face_label_in_manifest`: 0 fires (kickoff
  patch_naming_check blocks reject duplicates by construction).
- Path (c) `shm_reference_undeclared_in_manifest`: 0 fires (kickoff
  shm references align with face_labels by construction).
- Dispatch gate: fires on all 3 cases. case_020 verifies gate fires
  via `stl_face_normals non-empty` leg alone (with face_labels and shm
  regions both empty) → D11 walks to a clean report (correctly silent).

## §4 V94 V-row attribution

**Firm across all 3 archetypes.** All 7 path-(a) fires carry
`evidence_v_rows=("V94",)` per stl_face_label_validator.py line 380. No
cross-case re-attribution. No F-NEW row candidates discovered.

The V94 sighting in
`docs/openfoam_corpus/industrial_solver_findings_v_series.md` was
authored from a single case_011 v1 sediment (2026-05-09 surfaced
2026-05-14). This cross-val confirms the V94 death-class is general
across 3 substantively different industrial archetypes (cyclone single-
region · Kenics mixer multi-element with mixed-body-vs-face-label
authoring · porous filter all-patches-as-bodies). [QUESTIONABLE] marker
in stl_face_label_validator.py docstring §promotion gate (L137-140)
can now be retired — 2nd and 3rd industrial-case validation are
captured here.

## §5 F-NEW row candidates

**Count: 0.**

D11 surfaced no behavioral surprises. No false positives (case_020
silent as expected). No false negatives (case_018 + case_019 fired the
predicted count). No new advisor-gap patterns. The cross-val is
informational-zero on V-series extension — D11 already covers the face-
label-loss class on the 3 representative archetypes.

If future materialization of case_018/019/020 (real CAD + real STL
emission + real sHM run) surfaces second-order phenomena (e.g.,
cq.exporters tessellation-fragmented ghost solids, 0-area STL faces from
MeshPart edge-cases), those would be V94 sub-variants or V100+
extensions — out of scope here.

## §6 V64-A Done dim impact

- **Done #5 (V63-A carry-over closure)**: 2 / ≥4 → **3 / ≥4** via this
  closure of carry-over #4. One more closure from {#1 case_011 non-
  degen substrate · #2 second half [F-NEW-3 fix] · #3 case_016 window
  extension} required for Done #5 MET.
- **Done #1 / #2 / #3 / #4 / #6**: unaffected (this is a Tier 3
  close-track milestone, not a FULL validation report or PARTIAL
  upgrade or V-row capture).

## §7 Scope discipline (antithesis honored)

Per the dispatching brief antithesis list:
- ❌ ARC-GOAL.md unchanged
- ❌ Advisor stack source unchanged
- ❌ D11 source unchanged
- ❌ case_004 / case_006 / case_011 unchanged
- ❌ No Done #5 inflation (3 / 3 cross-val PASS → 3 / 4 advancement;
  not 4 / 4)
- ❌ No D11 false positive / false negative coverage (none discovered
  → none claimed)
- ❌ V94 V-row semantics unchanged (the sighting text is intact;
  cross-val firms rather than rewrites attribution)

## §8 Codex review status

**Skipped.** Per `~/CLAUDE.md` v2.3 (DEC-V61-133) + RETRO-V61-001
risk-tier:
1. No security-sensitive boundary touch (no route, no auth, no signing)
2. No byte-reproducibility-sensitive path (synthetic YAML data +
   read-only pure-function advisor invocation)
3. No Phase E2E ≥3 consecutive failure context

Confidence: med. Skipping per brief expectation ("Codex sync skip /
mandatory 状态 (expected: skipped · no security boundary)").

## §9 Kogami review status

**Skipped.** Per V133 (2026-05-07): Kogami auto-trigger废止;
user-invoke-only. User did not invoke for this milestone.

## §10 Artifacts (this commit chain · B60)

- `scripts/v64_d11_cross_val/__init__.py` (5 LOC)
- `scripts/v64_d11_cross_val/run_d11_cross_val.py` (197 LOC) — shared
  runner; reads per-case YAML, runs D11 direct + via stack, writes
  evidence JSON, reports match.
- `.planning/audits/d11_cross_val/case_018/substrate.yaml` (77 LOC)
- `.planning/audits/d11_cross_val/case_019/substrate.yaml` (96 LOC)
- `.planning/audits/d11_cross_val/case_020/substrate.yaml` (84 LOC)
- `.planning/audits/d11_cross_val/case_018/d11_evidence.json`
- `.planning/audits/d11_cross_val/case_019/d11_evidence.json`
- `.planning/audits/d11_cross_val/case_020/d11_evidence.json`
- `.planning/audits/d11_cross_val/cross_case_matrix.md`
- `.planning/validation_reports/v64_d11_cross_val.md`
- `.planning/decisions/2026-05-15_v64_sub_d11_cross_val.md` (this sub-DEC)

## §11 4Q gate (echoed in each B60 commit body)

- **Q1 LLM-offline**: runner drops LLM keys via `env -i` invocation +
  `os.environ.pop` before backend import; D11 + advisor_stack are
  pure-function Python with zero LLM dependency.
- **Q2 artifacts**: 3 substrate YAML + 3 evidence JSON + 1 cross-case
  matrix + 1 validation report + 1 sub-DEC + runner package.
- **Q3 TrustGate**: every D11 finding carries
  `evidence_v_rows=("V94",)` per stl_face_label_validator.py L380;
  every substrate cites kickoff codex_response source path:line; matrix
  cites D11 source paths (L356/L392/L431/L556).
- **Q4 advisor-only**: D11 is advisor not driver; cross-val is read-
  only validation. No advisor source mutation. No case substrate
  mutation. No stack registration mutation.

## §12 References

- V63-A close DEC `.planning/decisions/2026-05-15_v63_close_dec.md` §8
  carry-over #4 (this milestone's authorization)
- V63-A D11 land sub-DEC
  `.planning/decisions/2026-05-14_v63_sub_d11_stl_face_label.md`
  (parent of this cross-val effort)
- V64-A charter `.planning/decisions/2026-05-15_v64_charter_dec.md` +
  `.planning/2026-05-15_v64_charter.md`
- D11 source
  `ui/backend/services/geometry_ingest/stl_face_label_validator.py`
- D11 dispatch `ui/backend/services/advisor_stack.py` L556-602 +
  L789-827
- V94 V-row `docs/openfoam_corpus/industrial_solver_findings_v_series.md`
  §V94
- V63-A B47 case_011 v5b substrate runner
  `scripts/v63_case_011_substrate/run_extended.py` (template for B60
  runner)
- Cross-case matrix `.planning/audits/d11_cross_val/cross_case_matrix.md`
- Validation report `.planning/validation_reports/v64_d11_cross_val.md`

---

**Sediment author**: Claude Code Opus 4.7 (1M context) sub-session B60 ·
2026-05-15 · confidence: med (3/3 PASS verdict grounded in expected-vs-
actual match; expected_findings authored before running; substrate
data derived verbatim from kickoff codex_response Deliverable 4).
