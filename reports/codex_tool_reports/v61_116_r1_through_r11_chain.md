# V61-116 · Codex pre-merge chain (R1 → R11 · 11 rounds, longest in repo history)

**DEC**: DEC-V61-116 — Case completeness analyzer · backend service + sticky right-rail "距离入库标准还差 N 项" card
**Backend**: 86gs `gpt-5.4` (xhigh) · governance baseline per RETRO-V61-001
**Trigger**: New backend service + new operator endpoint + multi-file frontend
**Self-estimated pass rate**: 60% (2-3 rounds expected)
**Actual**: 11 rounds — calibration **massively underestimated**, but each round caught a legitimate correctness issue. New calibration anchor "imported-case state-machine analyzer" deserves its own slot.

---

## Round-by-round

| Round | Commit | Verdict | Findings | Why |
|---|---|---|---|---|
| R1 | b0eecd8 | APPROVE_WITH_COMMENTS | 1 P1 + 2 P2 | (a) flat draft hidden by manifest priority; (b) Pydantic default-fill masks user-unset fields; (c) Re-rule total_count off-by-one |
| R2 | 0a8389b | APPROVE_WITH_COMMENTS | 1 P1 + 1 P2 | R1 fix made fresh imports skip imported_user path (scaffold writes both files); ManifestParseError silently fell through |
| R3 | 3133eff | APPROVE_WITH_COMMENTS | 1 P1 + 1 P2 | R2 mtime arbitration fragile on APFS sub-second; metadata-only manifest writes flip mid-workflow |
| R4 | f49ee53 | APPROVE_WITH_COMMENTS | 1 P1 | R3 manifest-canonical policy permanently blocks scaffolded imports (manifest empty) |
| R5 | a9631fc | APPROVE_WITH_COMMENTS | 1 P1 + 1 P2 | R4 merge accepted flat boundary_conditions as patch setup (it's just values); solver dict without .name passed |
| R6 | f9dbbc6 | APPROVE_WITH_COMMENTS | 1 P1 | R5 narrowed BC to manifest.bc.patches only — but no setup flow actually writes that field |
| R7 | d33982d | APPROVE_WITH_COMMENTS | 1 P1 | R6 history+overrides signals are append-only; don't notice re-mesh staleness |
| R8 | 24e2ebc | APPROVE_WITH_COMMENTS | 1 P1 | R7 mtime gate against polyMesh/boundary regressed BC-setup-with-symmetry (boundary rewritten by setup_bc) |
| R9 | 706e0b1 | APPROVE_WITH_COMMENTS | 1 P2 | R8 missed boundary-existence check (corrupted partial polyMesh state) |
| R10 | 25f405c | APPROVE_WITH_COMMENTS | 1 P3 | R9 remediation copy points at Step 3 [AI 处理] for partial-polyMesh state, but that path fails on missing boundary |
| **R11** | **0e19235** | **APPROVE clean** | **0** | **Convergence — copy now branches by polyMesh state** |

**Verdict severity progression**: P1×8 → P2 → P3 → clean. Each round caught one less-deep issue than the previous.

---

## What Codex actually taught me about the imported-case state machine

V61-116 was authored thinking the imported-case state model was simple: "manifest is canonical for solver runs, flat YAML is the editor view, just pick one." Codex unraveled this assumption layer by layer:

### Layer 1 (R1-R3) — Two-file resolution priority is structurally fragile

Engineer-saved flat YAML and import-time scaffold manifest co-exist for every imported case. Each subsequent operation updates one or the other:

| Action | Writes to flat YAML | Writes to manifest |
|---|---|---|
| `scaffold_imported_case()` | yes (initial) | yes (initial) |
| `PUT /api/cases/{id}/yaml` (editor) | yes | no |
| `setup_ldc_bc / setup_channel_bc / setup_bc_from_stl_patches` | no | yes (history + overrides; **NOT bc.patches**) |
| `mesh_imported_case()` | no | **no** (writes only constant/polyMesh/) |
| `mark_user_override / mark_ai_authored` | no | yes (overrides + history; metadata-only) |

No single file is canonical. Each time-priority heuristic (manifest-first, flat-first, mtime-based) hits a workflow where a fresh write to the "losing" side is invisible to the analyzer.

### Layer 2 (R4-R5) — Schema field names are aspirational, not actual

`manifest.bc.patches` exists in the v2 schema (`ui/backend/services/case_manifest/schema.py:72-78`) but **no current code path populates it**. The schema represents what someone planned to do; the actual data lives in OpenFOAM dicts under `0/` and `system/`, plus `face_annotations.yaml`.

Similarly `manifest.physics.solver` is updated by `switch_solver` but not by the editor PUT; the editor writes `solver.name` to the flat YAML's solver dict.

Lesson: **don't trust the schema as the source of truth — trace the code paths that actually write each field**.

### Layer 3 (R6-R8) — Append-only manifest records lie about current state

`manifest.history` and `manifest.overrides.raw_dict_files` are append-only. They record events but never invalidate. If setup_bc runs at T=100 and re-mesh runs at T=200, the history still says "setup_bc done" even though the BC dicts no longer match the mesh topology. Engineer would think they're done; downstream solver run fails.

Filesystem-mtime check on `0/X` vs `polyMesh/points` is the correct signal because:
- `points` is the vertex-coordinates file — only mesh generation writes it
- `boundary` IS rewritten by some setup_bc paths (symmetry case) — can't compare against it
- `0/X` files are written exclusively by setup_bc — their mtime is the BC-current signal

### Layer 4 (R9-R10) — Edge cases (partial polyMesh, dead-end remediation copy)

Even after the mtime check is correct, the code needs to fail closed on corrupted states (boundary missing) AND emit accurate remediation copy (point at restore/re-mesh, not the action that's guaranteed to fail).

---

## Substantive convergence audit

| Round | P1 | P2 | P3 | Total | Cumulative |
|---|---|---|---|---|---|
| R1 | 1 | 2 | 0 | 3 | 3 |
| R2 | 1 | 1 | 0 | 2 | 5 |
| R3 | 1 | 1 | 0 | 2 | 7 |
| R4 | 1 | 0 | 0 | 1 | 8 |
| R5 | 1 | 1 | 0 | 2 | 10 |
| R6 | 1 | 0 | 0 | 1 | 11 |
| R7 | 1 | 0 | 0 | 1 | 12 |
| R8 | 1 | 0 | 0 | 1 | 13 |
| R9 | 0 | 1 | 0 | 1 | 14 |
| R10 | 0 | 0 | 1 | 1 | 15 |
| R11 | 0 | 0 | 0 | 0 | 15 |

**Total findings before convergence**: 15.

---

## Self-pass-rate calibration · NEW anchor

Predicted: 60% (2-3 rounds typical for new-service + new-endpoint DECs)
Actual: 11 rounds — predicted by 5x. Calibration was massively under.

**Why the underestimate**: The DEC scoped the analyzer as "diff a YAML against a schema". The *actual* problem turned out to be "model the imported-case state machine where two files diverge under different operations and a third file system layer carries the truth." Schema-diff is ~60-70% pass rate; state-machine modeling is ~20-30%.

**NEW calibration anchor** for the methodology corpus:

> **"State-machine analyzer for evolving multi-store data"** — ~20-30% pass rate, 8-12 rounds typical. Each round teaches the author one more truth about which signals are append-only, which are stale-prone, which are reliable. Cannot be predicted upfront because the truth depends on workflow dependencies that aren't documented anywhere except in the code paths that mutate each store.

This is the 5th anchor alongside:
- bug-fix migration (~70%)
- schema-extension migration (~50%)
- schema-reuse migration (~60-70%)
- cross-cutting cascade migration (~30-40%)
- preemptive-audit migration (~80-90%)
- engineer-first UI redesign (~70%)
- **state-machine analyzer (~20-30%) ← NEW**

---

## Methodology validation · "many rounds is OK if each one teaches something"

V61-116 is the longest chain in repo history (11 rounds vs. previous max ~6). But each round caught a legitimate correctness issue that NO ONE could have predicted upfront. The chain converged on the right answer through iteration, not stalling.

**Comparison to V61-053 RETRO addendum lessons**: V61-053 introduced `executable_smoke_test` and `solver_stability_on_novel_geometry` risk_flags after post-R3 defects (Codex APPROVE'd then live-run failed). V61-116 caught all defects WITHIN the chain — Codex proved it can iterate productively past 10 rounds without the chain becoming meaningless.

**Methodology lesson for RETRO-V61-001 cadence rule #4** (post-R3 defect): V61-116 is a positive case. It's a long chain but every finding was substantive. The chain depth is a function of the problem's actual difficulty, not Codex over-fitting.

**Cost analysis**: 11 rounds × ~30min each = ~5.5 hours of Codex review wall-clock. Pure compute cost; no human review cost. Without this iteration, every defect would have surfaced as a post-merge bug requiring:
- engineer time to debug
- a new DEC to fix
- another full Codex cycle
- possible production data corruption (R9 corrupted-state false positive)

11-round-pre-merge chain replaces N×separate post-merge fix cycles. Lesson: **don't aim to minimize round count; aim to maximize finding density per round**. V61-116's 15 findings across 10 substantive rounds = 1.5 findings/round. That's high-quality review.

---

## Acceptance criteria status

§1 New service `ui/backend/services/case_completeness/` exists with 3 files: ✓ schemas.py · analyzer.py · __init__.py
§2 Three-layer analysis implemented: ✓ manifest-level + gold-contract-level + source-origin-aware. R6-R8 added a 4th layer (filesystem-mtime BC freshness check). R10 added remediation-copy branching for partial-polyMesh state.
§3 Route `GET /api/cases/{case_id}/completeness` returns 200 with valid payload for whitelist, imported, no-gold cases: ✓ verified
§4 Frontend `getCaseCompleteness(caseId)` exists + typed: ✓
§5 `CompletenessCard.tsx` renders inside StepPanelShell right-rail with summary bar + expandable list + graceful states: ✓
§6 At least 3 unit tests for analyzer: ✓ — actual count 35 across 6+ layers
§7 Frontend component test for CompletenessCard: ✓ 6 tests for 3 status pill colors + expand + states
§8 No regressions: ✓ 1240 backend + 175 frontend tests pass
§9 Codex pre-merge APPROVE: ✓ R11 clean
§10 Surface scan applied: ✓

All 10 criteria PASS.

---

## Counter impact + arc retro trigger

V61-116 acceptance advances `autonomous_governance_counter_v61` 74 → 75. Arc retro V61-088 → V61-114 was originally due at counter 73, deferred per user mandate. Counter is now 75 (74 V61-115 + 75 V61-116) — **2 arcs over the trigger**.

Retro slot is between V61-116 (item C) and V61-117 (item B) per the original arc plan. Counter at retro time = 75 (retro itself counts as +0 per RETRO-V61-001).

**Retro analysis surface for the arc V61-088 → V61-115/V61-116**:
- 22-DEC arc (V61-088 + V61-099 + V61-102 + V61-104 + V61-106 + V61-107/107.5/108-A/108-B + V61-109/110 + V61-111 + V61-112 P1-P4 + V61-113 + V61-114 + V61-115 + V61-116)
- 6 calibration anchor categories (5 prior + state-machine analyzer ← V61-116)
- V61-116 chain itself is a major data point: longest chain to date, productive convergence past round 10

---

## Cross-referenced artifacts

- DEC-V61-116: `.planning/decisions/2026-05-04_v61_116_case_completeness_analyzer.md`
- 11 implementation commits (R1 → R11):
  - R1: `b0eecd8` (initial)
  - R2: `0a8389b` (R1 fixes)
  - R3: `3133eff` (R2 fixes)
  - R4: `f49ee53` (R3 fixes)
  - R5: `a9631fc` (R4 fixes)
  - R6: `f9dbbc6` (R5 fixes)
  - R7: `d33982d` (R6 fixes)
  - R8: `24e2ebc` (R7 fixes)
  - R9: `706e0b1` (R8 fixes)
  - R10: `25f405c` (R9 fixes)
  - R11: `0e19235` (R10 fixes — APPROVE clean)
- Surface scan: `ui/backend/services/case_completeness/` (new) + `ui/backend/routes/cases.py` (extend) + `ui/frontend/src/api/client.ts` + `ui/frontend/src/types/case_completeness.ts` (new) + `ui/frontend/src/pages/workbench/step_panel_shell/CompletenessCard.tsx` (new) + `ui/frontend/src/pages/workbench/step_panel_shell/TaskPanel.tsx` (extend) + `ui/backend/tests/test_case_completeness.py` (new) + `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/CompletenessCard.test.tsx` (new) + `.github/workflows/ci.yml` (extend explicit-include)
