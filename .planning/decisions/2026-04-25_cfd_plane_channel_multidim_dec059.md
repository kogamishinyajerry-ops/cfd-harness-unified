---
decision_id: DEC-V61-059
title: plane_channel_flow Type II multi-dim validation · u_tau headline + 3-profile gates · case 6 · v2.0 first-apply
status: COMPLETE_DEMONSTRATION_GRADE (2026-04-25 · Stage A 4 Codex rounds APPROVE r4 · Stage B live OpenFOAM run end-to-end at 520.7s wall · 3 post-R3 OF10-emitter-API-drift defects fixed in commits a71e8ec/4af21a2/42158e2 + perf-tuning 59198cf · Stage B sub-arc 2 Codex rounds APPROVE_WITH_COMMENTS r6 · A.4.b/A.5.b kOmegaSST RANS path + gold-YAML regen at Re_τ=395 deferred to follow-up DEC)
supersedes_gate: DEC-V61-036c (G2 territory marker · STATE.md:1313)
intake_ref: .planning/intake/DEC-V61-059_plane_channel_flow.yaml
methodology_version: "v2.0 (first-apply, not retroactive · see Notion methodology page §8/§9)"
commits_in_scope:
  # ----- Stage A.1 (G2 detector standalone PR #38) -----
  - 48cf994 feat(comparator_gates) G2 canonical-band shortcut detector for plane-channel u+/y+
  # ----- Stage A intake + landings -----
  - bb98f15 intake(plane_channel) DEC-V61-059 Stage 0 · v1 draft (Type II, headline=u_tau)
  - fd12b12 feat(plane_channel) A.2 secondary observable extractors
  - 30ae22b feat(plane_channel) A.3 wall-symmetric blockMesh grading + ncy=80 lock
  - cb6737b feat(plane_channel) A.4.a turbulence_model_used contract + turbulenceProperties
  - c3c347f test(plane_channel) A.6 alias normalization parity
  - 55b3759 intake(plane_channel) mark A.2/A.3/A.4.a/A.6 LANDED, A.4.b/A.5 deferred
  # ----- Stage A Codex rounds 1-4 -----
  - 55f32db fix(plane_channel) apply Codex round-1 F1+F2 (bc-stamp trust + hyphen normalize)
  - 0a649d7 fix(plane_channel) apply Codex round-2 F3+F4 (verdict-engine wiring + SNR floor)
  - 3ae5cdf fix(plane_channel) apply Codex round-3 F5+F6 (log-law band + driver guard)
  - fb2ea78 docs(plane_channel) Codex round-4 CLEAN CLOSE — Stage A locked
  # ----- Stage B post-R3 fix stack -----
  - a71e8ec fix(plane_channel) A.4.a OF10 momentumTransport rename
  - 4af21a2 fix(plane_channel) A.4.a icoFoam → pisoFoam (Stage B post-R3)
  - 59198cf perf(plane_channel) A.4.a Stage B runtime tuning
  - 42158e2 fix(plane_channel) A.4.a OF10 uLine filename
  - 0a90dea data(plane_channel) A.5-shaped fixture · Stage B passes
  - 522eaa0 intake(plane_channel) mark Stage B LANDED + log 3 post-R3 defects
  # ----- Stage B sub-arc Codex rounds 5-6 -----
  - eb67a96 fix(plane_channel) apply Codex round-5 F7+F8 (reader field-aware + downstream consumers)
  - efae759 fix(plane_channel) apply Codex round-6 F9+F10 (coexistence test + log-name order)
  # ----- Cross-DEC retro update -----
  - d4e5247 retro(v61-053) addendum row for V61-059 post-R3 hits
codex_verdict: |
  Stage A 4 rounds F1-M2-clean: R1 CHANGES_REQUIRED (2 P2) → R2 CHANGES_REQUIRED (1 P1 + 1 P2) → R3 CHANGES_REQUIRED (1 P2 + 1 P3) → R4 CLEAN APPROVE.
  Stage B sub-arc 2 rounds: R5 CHANGES_REQUIRED (2 P2) → R6 APPROVE_WITH_COMMENTS (2 P3).
  Total = 6 Codex rounds. Sub-arc rounds 5-6 are bookkept against
  the Stage B sub-arc clock per intake §7-batch-B note ("post-Stage-B
  fix stack re-opens the Codex review surface"), not against the
  original 4-round Stage A budget.
autonomous_governance: true
autonomous_governance_counter_v61: 41
external_gate_self_estimated_pass_rate: 0.40
external_gate_self_estimated_pass_rate_source: .planning/intake/DEC-V61-059_plane_channel_flow.yaml
external_gate_actual_outcome_partial: |
  6-round Codex arc. Stage A R1 pass-rate ACTUAL = 0% (CHANGES_REQUIRED, 2 findings)
  vs estimated 0.40 — within RETRO-V61-001 ≤70% pre-merge-Codex band, fired correctly.
  Stage B live OpenFOAM run on commit 42158e2 (cumulative post-R3 stack a71e8ec +
  4af21a2 + 59198cf + 42158e2) ran end-to-end in 520.7s wall: solver_success=true,
  measurement.value=1.9176 @ y_plus=5, 3 deviations vs Moser/Kim DNS gold (laminar
  vs turbulent — physics-honest hard FAIL), G2 silent (correct), comparator
  produces concrete deviations on canonical y+ ∈ {5, 30, 100}. **THREE post-R3
  hidden defects** all variants of OpenFOAM-version-emitter API drift:
  (1) constant/turbulenceProperties → momentumTransport (OF10 rename),
  (2) icoFoam → pisoFoam (icoFoam doesn't register a momentumTransportModel),
  (3) <set>_<field>.xy → <set>.xy (OF10 sets-FO emits one packed file).
  Plus runtime tuning to bring 3-hour wall down to 9 minutes per case. RETRO-V61-053
  addendum captured all three as the OpenFOAM-version-emitter API drift class.
  Stage B sub-arc rounds 5-6 caught 4 additional findings (F7-F10) introduced by
  the post-R3 fix stack itself; all landed.
external_gate_caveat: |
  Type II DEC (1 primary scalar u_tau + 3 profile gates: C_f, Re_tau, u_plus_profile).
  Adapter `_generate_steady_internal_channel` is the central touch point.
  Cross-plane: Execution + Evaluation aliases pinned by alias-parity tests.
  Codex log archive: reports/codex_tool_reports/dec_v61_059_plan_review_round{1,2,3,4}.md +
  reports/codex_tool_reports/dec_v61_059_round{5,6}.md. Live-run log archive:
  reports/phase5_audit/dec_v61_059_stage_b_live_run_v{4,5}.log.
codex_tool_report_path: |
  reports/codex_tool_reports/dec_v61_059_plan_review_round{1,2,3,4}.md
  reports/codex_tool_reports/dec_v61_059_round{5,6}.md
notion_sync_status: pending — sync DEC frontmatter + retro narrative on next session sweep
github_sync_status: dec-v61-059-pc branch · 19 commits ahead of fb2ea78 (round-4 baseline)
related:
  - DEC-V61-036b (comparator gates G3/G4/G5 — canonical-band shortcut detector G2 added here)
  - DEC-V61-036c (G2 territory marker · STATE.md:1313 → CLEARED by this DEC)
  - DEC-V61-043 (plane-channel u+/y+ emitter — wallShearStress + uLine FO setup)
  - DEC-V61-050 (LDC Type I precedent · 4 rounds)
  - DEC-V61-052 (BFS Type II precedent · 5 rounds incl. F1-M2 back-fill)
  - DEC-V61-053 (cylinder Type I · 3+2 rounds · same OpenFOAM-version-emitter API drift class · RETRO addendum)
deferred_followups:
  - "A.4.b: full simpleFoam + RAS file emission + whitelist flip plane_channel_flow → solver=simpleFoam, turbulence_model=kOmegaSST, Re_τ=395"
  - "A.5.b: gold YAML observables[] regen (4 HARD-GATED entries: u_tau, C_f, Re_tau, u_plus_profile @ Re_τ=395) + auto_verify_report.yaml + 3-way invariant test"
  - "Stage C: PREFLIGHT GATE WIRING (gold YAML schema_v2 observables[] → 4 HARD_GATED; comparator_gates G1-G5 iterate over HARD_GATED only) — depends on A.5.b"
  - "Stage D: COMPARE-TAB MULTI-DIM ANCHOR CARDS + audit fixture regen + report.md template update — depends on A.5.b"
  - "Centralize `FOAM_SOLVER_LOG_NAMES` (Codex round-6 F10 follow-up)"
---

## Stage 0 · Case Intake (F1-M1 v2.0 hard gate)

Signed intake: [`.planning/intake/DEC-V61-059_plane_channel_flow.yaml`](../intake/DEC-V61-059_plane_channel_flow.yaml).

Key determinations:
- **case_type = II** (1 primary scalar `u_tau` + 3 profile gates: `C_f`, `Re_tau`, `u_plus_profile`)
- **primary_gate_count = 4**
- **codex_budget_rounds = 4** soft target, round 5 health check, round 6 force abandon (F6-M1)
- **estimated_pass_rate_round1 = 0.40** (G2 detector + adapter + extractor + cross-plane verdict-engine integration are all net-new surface area)

**In-scope observables**: `u_tau`, `C_f`, `Re_tau`, `u_plus_profile` (interpolated at canonical y+ ∈ {5, 30, 100}).
**Out-of-scope** (enforced by §3b): full simpleFoam + RAS path (A.4.b), gold YAML regen (A.5.b), preflight HARD_GATED schema migration (Stage C), Compare-tab multi-dim cards (Stage D).

## Stage A · 4-round Codex arc

See RETRO-V61-059 §1 for the round-by-round breakdown. Highlights:

- **R1**: F1 (P2) bc-stamp trust — caller override could bypass G2 by metadata declaration alone. Fixed via `_emits_rans_path = False` flag locking bc to "laminar" until A.4.b flips RAS path. F2 (P2) hyphen-normalize — canonicalizer only matched camelCase but whitelist uses `k-omega SST`. Fixed via strip-based normalization.
- **R2**: F3 (**P1**, structural depth finding) — G2 concern type was MISSING from `_HARD_FAIL_CONCERNS` in `validation_report.py`. The gate was firing but the verdict engine ignored it. Toothless. Fix added the concern type to the hard-fail set. F4 (P2) SNR floor — `min(spacings)` was optimistic. Fixed to `max(spacings)`.
- **R3**: F5 (P2) log-law band over-tight — `has_loglaw = any(yp >= 30.0)` counted y+=100 centerline as log-law. Fixed to `(10.0, 60.0)` window. F6 (P3) driver guard — G2 was wrapped in a phase7a artifact-presence gate but G2 is artifact-independent. Fixed.
- **R4**: CLEAN APPROVE (commit `fb2ea78`).

## Stage B · live OpenFOAM run + 3 post-R3 defects + sub-arc

Stage B production audit run on round-4 baseline crashed at simulated 4.6s with `FOAM FATAL ERROR: Unable to find turbulence model in the database` from inside the wallShearStress function-object. Three distinct defects, all variants of **OpenFOAM-version-emitter API drift** (per RETRO-V61-053 §10). See RETRO-V61-059 §2 for the table.

The Stage B sub-arc (rounds 5-6) closed F7+F8 (P2) and F9+F10 (P3) introduced by the post-R3 fix stack. APPROVE_WITH_COMMENTS at sub-arc round 2.

**Final Stage B verdict** on commit `42158e2`: solver_success=true, end-to-end 520.7s wall, key_quantities populated with full u+/y+ profile + secondary observables, comparator emits 3 concrete deviations (laminar at Re=13750 sits well below Moser/Kim DNS turbulent gold), G2 stays silent (correct: profile far outside canonical band). **The FAIL is physics-honest, not pipeline bug.** A.4.b/A.5.b will land the kOmegaSST RANS path that closes the physics gap.

## Stage E close conditions (intake §9)

- ✅ All Codex round-N findings landed in commits (Stage A R1-R3 + Stage B sub-arc R5)
- ✅ Clean Codex round-(N+1) verdict ∈ {APPROVE, APPROVE_WITH_COMMENTS} per F1-M2 (Stage A R4 = APPROVE; Stage B sub-arc R6 = APPROVE_WITH_COMMENTS)
- ✅ Executable smoke test passes (Stage B end-to-end 520.7s wall, full extractor + comparator path)
- ✅ DEC-036c G2 territory marker cleared from STATE.md
- 🔜 DEC frontmatter `notion_sync_status` = synced (queued for next Notion-access session)
- ✅ `autonomous_governance_counter_v61` incremented (40 → 41 with this DEC)
- ✅ RETRO-V61-059 written (this DEC's RETRO file + addendum row in V61-053 RETRO)
- ⏳ G2 standalone PR (`fix-comparator-g2-uplus-yplus` / PR #38) MERGE pending — required before V61-057 / V61-058 stage close per cross-session protocol

## Counter accounting

`autonomous_governance_counter_v61`: **41** post-V61-059. Up from
40 (V61-053 close). The Stage B sub-arc rounds 5-6 are accounted to
the V61-059 DEC arc, not as separate DECs.
