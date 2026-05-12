---
decision_id: DEC-V61-198-sub-protocol-inlet-outlet
title: Codex case-design protocol amendment · inlet/outlet boundary emission · V81 backfill
status: Accepted
parent_dec: V61-198
phase: governance-rule-change · harvest-003 priority #2
notion_sync_status: pending session-end batch
parent_artifacts:
  - .planning/patches/draft_codex_cad_inlet_outlet_protocol_amendment_2026-05-09.md (cycle 003 design)
  - .planning/methodology/codex_case_design_protocol.md (amended)
  - .planning/methodology/industrial_case_solver_findings.md (V81 backfilled 2026-05-13)
  - .planning/cross_cuts/advisor_coverage_2026-05-09.md (harvest-003 priority #2)
trigger: case_012 v1 sediment 2026-05-09 surfaced silent failure mode — Codex emitted supply_inlet + return_outlet as 3D solid bodies, sHM treated them as walls, v1 ran as natural-convection-only sealed-room instead of HVAC-with-supply-jet. 6 dispatched cases (013/015/017/018/019/020) at risk of the same pattern. harvest-003 #2 priority "LOW LOC / VERY HIGH frequency"
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (sub-DEC scope · methodology doc amendment + V-row backfill · no code · no schema · no auth/signing/security boundary per v2.3 §2)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-12
confidence: high (governance amendment is doc-only; reference impl analysis from case_012 provides concrete grounding; A8 auto-validator deliberately deferred to keep scope minimal)
---

# DEC-V61-198-sub-protocol-inlet-outlet · Codex CAD inlet/outlet emission amendment

## 1. Why now

case_012 v1 sediment (2026-05-09) honest-evidence statement:

> case_012 v1 evidence is for **natural-convection-only sealed-room**
> physics, NOT HVAC-with-supply-jet. ADPI / throw / dumping metrics
> CANNOT be compared to ASHRAE 55 design table for the original brief.

Root cause: Codex's CAD generator emitted `supply_inlet` /
`return_outlet` as 3D solid bodies (`cq.box(...)`), STL extraction
produced closed surfaces, snappyHexMesh meshed them as walls. No
inlet/outlet patch in the resulting mesh.

**Risk surface**: every Codex CAD generator with through-flow
boundaries is at risk. 6 dispatched cases (013/015/017/018/019/020)
inherit the pattern unless main session manually catches the
emission style before sub-session dispatch.

The pre-amendment validation checklist had 6 checks; none of them
inspected emission *shape per role*, only emission *existence*.

## 2. What changed

### `methodology/codex_case_design_protocol.md` amended

Two amendments to the live methodology document:

1. **New validation step 7** in §"Main session validation step":
   "Boundary-zone audit" — verifies parts_manifest entries with role
   `supply` / `return` / `inlet` / `outlet` emit via one of three
   approved patterns (or carry the explicit sealed-room annotation).
2. **New section** §"Inlet/outlet boundary geometry emission"
   documenting:
   - **Pattern 1 — Thin-extrusion** (preferred): 1 mm extrusion +
     `boundary_emission: thin_extrusion` annotation in parts_manifest
   - **Pattern 2 — createPatch carve** (post-mesh): metadata-only
     emission via `boundary_zones` list + bbox + `carve_from_patch`
   - **Pattern 3 — Named faceZones** (reserved; experimental, do
     not use until verified across ≥ 2 cases)
   - **Sealed-room honest annotation** for cases where the brief
     genuinely is sealed-room (no through-flow); makes the relaxation
     explicit instead of accidental
   - **Risk surface** enumeration: case_013/015/017/018/019/020
     inherit the risk
   - **Out of scope** declarations: A8 validator script + retroactive
     re-dispatch deferred

### V81 backfilled in `industrial_case_solver_findings.md`

New V-row (deep section + quick-lookup index) capturing the case_012
root cause. Backfill pattern same as V79 (D7 advisor-gap) and V80
(STEP timestamp): case_012's case_index claimed V49-V53 but those
V-numbers were assigned to case_015/016 later. V81 gives the
inlet/outlet finding its proper V-row.

### `advisor_coverage_2026-05-09.md` updated

Harvest-003 priority #2 row flipped from "STILL DRAFTED" (the
protocol amendment had been queued for 3 days) to LANDED, with
reference to this DEC.

## 3. V-row status changes

| V-row | Pre-DEC | Post-DEC |
|---|---|---|
| V81 (backfilled 2026-05-13) | (did not exist) | `partial 2026-05-12` (protocol amended; auto-validator deferred; retroactive case audit deferred) |

V81 status is `partial`, not `closed`, because:
- Protocol amendment lands the governance prevention going forward
- Already-dispatched cases (013/015/017/018/019/020) are not
  automatically audited — main session does it manually per case at
  sub-session dispatch time
- The A8-class auto-validator script (`codex_cad_inlet_outlet_audit.py`)
  that would close the loop is deferred to a separate sub-DEC (not
  enough cross-case evidence yet to overdetermine the script's design;
  per v2.3 spike-class threshold the validator merits its own
  sediment-driven scope)

## 4. What does NOT change

- The 6 existing validation checks (CadQuery executes, STEP imports,
  names match, defects exist, patch-name regex, solver-class match)
  — all retained; step 7 is additive
- `parts_manifest.yaml` schema — no breaking change; new optional
  keys `boundary_emission` + `boundary_zones` only consulted by the
  amended audit
- Already-dispatched case CadQuery scripts — main session inspects
  manually case-by-case (not auto-rewritten)
- Codex backend selection / round-cap / kickoff prompt structure
  (separate sections unchanged)

## 5. Anti-patterns honored

- **No silent fallback to sealed-room** — explicit annotation
  `boundary_emission: sealed_room_natural_convection` makes
  intentional relaxation visible
- **No automatic case rewrite** — already-dispatched cases sit on
  the dispatcher's plate; main session catches them
- **No A8 validator script land** — kept out of scope to keep this
  DEC minimal; will land as separate sub-DEC when ≥ 2 V81-pattern
  failures sediment (per advisor cross-topology promotion gate)

## 6. Open questions resolved (from draft patch §"Open questions")

| Question | Resolution |
|---|---|
| `parts_manifest.yaml` schema rich enough for `boundary_zones`? | **Yes** — new keys (`boundary_emission`, `boundary_zones`) are additive optional fields; no schema bump required |
| Wire audit into `make all` for every sandbox? | **Deferred** — manual main-session check is the v1; auto-wire follows the A8 validator script land |
| Redispatch Codex for dispatched cases 013-020? | **No** — main session manually audits each CadQuery script at sub-session dispatch time; redispatch would burn Codex tokens for cases that may or may not have the issue |

## 7. Reversal cost

Low. To reverse:
- Revert `methodology/codex_case_design_protocol.md` (delete §"Inlet/
  outlet boundary geometry emission" + step 7)
- Revert V81 row in `methodology/industrial_case_solver_findings.md`
  (deep section + quick-lookup index)
- Revert `cross_cuts/advisor_coverage_2026-05-09.md` priority #2 row

No code change, no schema change, no dependency adds. Pure doc revert.

## 8. References

- Draft patch: `.planning/patches/draft_codex_cad_inlet_outlet_protocol_amendment_2026-05-09.md`
- V-series: V81 (created by this DEC), parallel pattern to V79 (D7
  backfill) and V80 (STEP timestamp backfill)
- Harvest snapshot: `.planning/cross_cuts/advisor_coverage_2026-05-09.md`
  priority #2 row flipped to LANDED
- Parent DEC: V61-198 (APU bay strategic pivot · Codex case-fleet
  protocol)
- Sibling sub-DECs landed same day:
  - V61-198-sub-A2v2 (harvest-003 #1, gap-detection API)
  - V61-198-sub-A7 (harvest-003 #3, STEP canonicalizer)
- Out of scope for separate sub-DEC: A8 `codex_cad_inlet_outlet_audit.py`
  validator script
