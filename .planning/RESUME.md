# RESUME.md · cfd-harness-unified next-session pickup

> **Generated**: 2026-05-24T20:30 local (session-end checkpoint)
> **Last DEC commit**: `1ccb4b3` (M32 cycle 3 DEC close)
> **Updated**: 2026-05-24T23:45 — M3.2 cycle 4 landed as spike-class (commit `f09bc9d`, copy body_text button); no DEC; no Notion entry per v2.3 spike-class rules
> **Session arc**: M3.1 milestone close + M3.2 cycles 1-3 (11 sub-DECs accepted; all Notion-synced) + M3.2 cycle 4 spike-class

---

## Where we are

**Milestone M3.1 (workbench dynamic guided UX, engine-side) = CLOSEABLE.**
**Milestone M3.2 (workbench frontend severity + actionability) = IN PROGRESS, 3 cycles landed.**

Parent charter: `DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED`.

## What landed this session (11 sub-DECs)

| Cycle | DEC ID | Final commit | Notion |
|---|---|---|---|
| M3.1 C1 | DEC-V61-202-SUB-M31-CYCLE1-FORM-HELPER-SHIPVOF | `4b701ea` + `a116981` | [36ac6894...474657](https://www.notion.so/36ac68942bed819d9ea7e7833f474657) |
| M3.1 C2 | DEC-V61-202-SUB-M31-CYCLE2-UI-LABELER-SCALAR-INPUT | `aaade23` | [36ac6894...64ac8f](https://www.notion.so/36ac68942bed819395b9d018fbc4ac8f) |
| M3.1 C3 | DEC-V61-202-SUB-M31-CYCLE3-RANS-FAMILY-SKELETON | `436d4b8` | [36ac6894...4ac8f](https://www.notion.so/36ac68942bed819395b9d018fbc4ac8f) |
| M3.1 C4 | DEC-V61-202-SUB-M31-CYCLE4-LES-EXTENSION-REGISTRY-EXTRACT | `a7d300b` | [36ac6894...10f2](https://www.notion.so/36ac68942bed81af8e3ee0d3882510f2) |
| M3.1 C5 | DEC-V61-202-SUB-M31-CYCLE5-FAILURE-PATH-DOGFOOD | `46880cc` | [36ac6894...d547](https://www.notion.so/36ac68942bed8187ba36f2b3134dd547) |
| M3.1 C6 | DEC-V61-202-SUB-M31-CYCLE6-PATCH-TYPE-PRESERVATION | `d64551c` | [36ac6894...0daf](https://www.notion.so/36ac68942bed81679d0af4274afb0daf) |
| M3.1 C7 | DEC-V61-202-SUB-M31-CYCLE7-CORRUPTED-MANIFEST-RAIL | `0e912b0` | [36ac6894...c755](https://www.notion.so/36ac68942bed8156854dfee0533bc755) |
| M3.1 C8 | DEC-V61-202-SUB-M31-CYCLE8-PATCH-TYPE-ENUM-WARNING | `cf1541b` | [36ac6894...7aa](https://www.notion.so/36ac68942bed81c0b401d3fd6016e7aa) |
| M3.2 C1 | DEC-V61-202-SUB-M32-CYCLE1-RAIL-SEVERITY-SURFACING | `c91ae09` | [36ac6894...5ba8](https://www.notion.so/36ac68942bed8162a7eee92e87d95ba8) |
| M3.2 C2 | DEC-V61-202-SUB-M32-CYCLE2-TOPBAR-SEVERITY-DISABLED | `7a6737e` | [36ac6894...4f50](https://www.notion.so/36ac68942bed81f4883adf9ffcc64f50) |
| M3.2 C3 | DEC-V61-202-SUB-M32-CYCLE3-COPY-FIELD-PATH | `28951f1` | [36ac6894...9fe7](https://www.notion.so/36ac68942bed812c9a97ed017c259fe7) |

**Retro**: `.planning/retrospectives/2026-05-24_m31_milestone_close.md` (commit `9fed473`, 290 lines, NOT synced to Notion per SSOT rule).

## Cycle-5 failure-path bug closure matrix (all FIXED)

| Bug | Severity | Fixed in cycle | Regression test |
|---|---|---|---|
| BUG-CYCLE5-1 (PATCH no type validation) | P1 | 6 | `test_manifest_patch_type_preservation` (23 unit tests) + dogfood step 5 |
| BUG-CYCLE5-2 (cascade blocks revert) | P1 | 6 (bundled) | dogfood step 6 |
| BUG-CYCLE5-3 (analyzer misses corruption) | P2 | 7 | `test_workbench_decide_corrupted_manifest` (9 unit tests) + dogfood step 8 |
| BUG-CYCLE5-4 (typo'd patch_type silently OK) | P3 | 8 | `test_case_completeness_patch_type_warning` (16 unit tests) |

Total new test coverage: **48 unit tests + 4 dogfood steps**.

## Open M3.2 work (start here next session)

### Cycle 5+ candidates (cycle 4 = copy body_text · LANDED 2026-05-24 commit `f09bc9d` spike-class)

1. **Toast notification** ("已复制 / Copied" floating message) — **TOP candidate for cycle 5**: now compounds value across cycle-3 field_path button + cycle-4 body_text button; sub-DEC (touches shared paths · ≥50 LOC expected · NOT spike-class)
2. **Copy validation error reason from analyzer** — analyzer-side surfacing (backend touch)
3. **Open in IDE / "Reveal in Finder"** — OS integration via `vscode://` URL scheme (could be spike-class if URL-only)
4. **Raw YAML viewer modal** — requires backend YAML fetch route
5. **"Replace whole node" UI recovery affordance** — for legacy-corrupted manifests (M3.1 cycle 6 deferred)

### M3.2 charter open questions (from retro §"Open questions for M3.2 charter")

1. Should "replace whole node" UI recovery be in M3.2 scope?
2. Cockpit `project_status.json` SHA-lag → graduate to dedicated cockpit-pipeline DEC?
3. V63-A catalog drift canary — add to base `[ui]` test suite or runtime-only is fine?
4. Pre-cap-3 guard: "if Codex precedence/source-of-truth finding twice, declare charter-class"?

## Methodology lessons captured (load-bearing for M3.2+)

1. **Failure-path dogfood pattern works** — 100% bug closure within milestone arc. Apply to focus-pick + multi-physics flag-mismatch dogfoods next.
2. **Precedence/source-of-truth Codex findings ≥2 = charter-class signal** — Cycle 1 8-round arc would have been 2-round with this guard.
3. **Cross-module import surface-scan pre-flight** — Verify `head -50 package/__init__.py | grep -i import` for heavy deps before any `from package.module import X`. Cycle 8 R1 trimesh leak postmortem.
4. **Catalog-reuse checklist**: (a) import-tree clean, (b) intentional exclusions match use case, (c) overloaded semantics reconcile. Cycle 8 3-round arc → 1 round with this.
5. **Static drift-detection > importlib.reload** for SSOT-mirror invariants. Cycle 8 R2's `test_v63a_catalog_is_subset_of_known_types` is the pattern.
6. **Manifest-only contract (cycle 1 R7) is load-bearing** — Cycles 3 and 6 inherited it. Any future architectural ratification should be documented as a contract this strongly.

## V130 four-question gate audit (8/8 M3.1 cycles)

All cycles answer Y/Y/Y/Y:
- LLM offline — does it run? ✓
- Artifacts canonical (manifest/json/yaml)? ✓
- TrustGate-explainable (provenance on every decision)? ✓
- AI advisory-only (no auto-writes by AI)? ✓

Advisor-not-driver contract held across all 8 cycles including programmatic dogfood.

## Counter telemetry

- M3.0 counter delta: +8
- M3.1 counter delta: +8
- M3.2 counter so far: +3 (cycles 1-3)
- Cumulative M3 counter: +19 (from 73 → 84+? exact transition depends on M2 closure baseline)
- post-R3 defects M3.1: 0
- user-ratifications M3.1: 4 / 8 = 50% (healthy band 30-60%)
- Codex APPROVE-at-R0: 1 / 8 (12.5% — cycle 7 ideal cycle)

## Codex round economy (this session)

| Cycle | Rounds | Closure |
|---|---|---|
| M3.1 C1 | 8 (R0-R8) | user-ratified R7 (manifest-only contract) |
| M3.1 C2 | 4 (R0-R3) | clean APPROVE R3 |
| M3.1 C3 | 3 (R0-R2) | clean APPROVE R2 |
| M3.1 C4 | 4 (R0-R3) | user-ratified R3 (same-day rename non-issue) |
| M3.1 C5 | 4 (R0-R3) | user-ratified R3 (msg-only scan fix) |
| M3.1 C6 | 2 (R0-R1) | user-ratified R1 (cockpit SHA structural) |
| M3.1 C7 | 1 (R0) | clean APPROVE R0 (ideal cycle) |
| M3.1 C8 | 3 (R0-R2) | clean APPROVE R2 (inline fix at cap=3) |
| M3.2 C1 | 2 (R0-R1) | clean APPROVE R1 |
| M3.2 C2 | 2 (R0-R1) | clean APPROVE R1 |
| M3.2 C3 | 2 (R0-R1) | clean APPROVE R1 |

Total ~35 rounds across 11 sub-DECs (avg 3.2 rounds/cycle, dragged up by cycle 1 outlier). Without C1: 27 / 10 = 2.7 avg.

## File map (most-touched paths this session)

### Backend (engine)
- `ui/backend/services/workbench_decide.py` — `_FORM_HELPER_SKELETONS`, `_STRUCTURAL_META_PATHS`, `_rail_from_problem`/`_rail_from_gap` severity passthrough
- `ui/backend/services/manifest_patch.py` — `_check_type_preservation`, `_compare_subtree_types`
- `ui/backend/services/case_completeness/analyzer.py` — `_KNOWN_OPENFOAM_PATCH_TYPES`, `_FIELD_LEVEL_BC_TYPES` (inline-copied STANDARD_OPENFOAM_BCS), `_SOLVER_TO_CASE_FAMILY_CANDIDATES`
- `ui/backend/services/case_family_registry.py` — **new SSOT module** (cycle 4 extraction)
- `ui/backend/services/workbench_decide_provenance.py` — reads `frame.rail_primary.severity` directly (no string scraping)
- `ui/backend/schemas/workbench_frame.py` — `RailPrimary.severity: Severity = "info"`

### Frontend (workbench)
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicFramePanel.tsx` — inline-edit affordance, `toneFor(rail)` 4-tone helper, `CopyFieldPathButton`
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicTopbarCta.tsx` — `railSeverity` prop + `DISABLED_CLASS_BY_SEVERITY`
- `ui/frontend/src/pages/workbench/StepPanelShell.tsx` + `v4/WorkbenchShellV4.tsx` — both threaded `railSeverity={dynamicFrame.rail_primary.severity}`
- `ui/frontend/src/types/workbench_frame.ts` — mirrors backend severity field

### Tests
- `ui/backend/tests/test_manifest_patch_type_preservation.py` (NEW, 23 tests)
- `ui/backend/tests/test_workbench_decide_corrupted_manifest.py` (NEW, 9 tests)
- `ui/backend/tests/test_case_completeness_patch_type_warning.py` (NEW, 16 tests)
- `ui/backend/tests/test_workbench_decide_rail_severity.py` (NEW, 11 tests)
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/__tests__/DynamicFramePanel.test.tsx` (32 tests total)
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/__tests__/DynamicTopbarCta.test.tsx` (11 tests)
- `scripts/dogfood/case_007_cycle5_failure_path.py` (10/10 PASS)

## Standing constraints (still in force)

- **Manifest-only contract** for solver field (cycle 1 R7 ratified; load-bearing)
- **Codex round cap = 3** per v2.3 DEC-V61-133 (R0 + 2 fix iterations; ratification can extend or close)
- **Kogami opt-in only** (auto-triggers废止 per v2.3); user explicitly invokes
- **DEC scope-driven**: charter / ≥3 shared paths / governance-rule-change → full DEC; sub-DEC for narrower
- **Notion sync**: Accepted-only, session-end batch (retros stay local)
- **Four-question gate** (V130): LLM offline / artifacts canonical / TrustGate / advisor-only — all 4 must be Y
- **No port squatting / no schedule-date gating / no CFDJerry visual smoke gating**
- **`codex-relay` skill** is Claude Code's own responsibility; do not push commands to user

## Next-session entry checklist

1. **Read this RESUME.md first** (you're here)
2. Skim `.planning/STATE.md` ANCHOR-23 (top of file) for full session narrative
3. Decide M3.2 cycle 4 direction (see "Open M3.2 work" above) — user mandate is continuous milestone progress
4. If picking cycle 4 from the candidate list, do pre-implementation surface scan per V61-088:
   - ROADMAP scan
   - existing-implementation grep
   - file new sub-DEC with predecessors pointing to M3.2 cycles 1-3
5. Spike-class (≤30 LOC + 1 test) is fine for the toast/copy-body_text variants — those won't need DEC

## Bottom line

M3.1 closes with a fully-drained cycle-5 backlog, no post-merge defects, 50% user-ratification rate matching v2.3 design intent, zero V131 spirals. M3.2 is bootstrapped through the severity-visibility foundation (cycles 1-2) and the first actionability affordance (cycle 3). Engine-side is closeable; the frontend actionability thread is open and ready for cycle 4+ expansion.

**Recommendation for next session**: pick a cycle 4 direction from the open-list above; spike-class if applicable; otherwise sub-DEC + Codex round cap=3 + session-end Notion sync.
