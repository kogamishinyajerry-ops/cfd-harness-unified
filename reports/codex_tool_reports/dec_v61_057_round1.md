# DEC-V61-057 · Codex Round 1 Review (Post-Stage-A)

**Reviewer**: Codex GPT-5.4 (xhigh reasoning)
**Date**: 2026-04-25 23:40 +0800
**Workdir**: cfd-harness-unified @ commit 8f7120b
**Tokens used**: 338,608

## Verdict

**CHANGES_REQUIRED** · 2 blockers for Batch B · NO_GO

| | Findings |
|---|---|
| HIGH | 2 |
| MED  | 1 |
| LOW  | 0 |

## Findings

### F1-HIGH · Supported DHC alias still falls through to old AR=2.0/RAS path · ADDRESSED in A.5

**File refs**:
- `src/foam_agent_adapter.py:230,268,2126,2146` (whitelist + dispatch paths only matched canonical case_id substring)
- `src/auto_verifier/config.py:30-44` (alias map exists but adapter cannot import — ADR-001 plane boundary)
- `src/notion_client.py:130` (Notion-supplied TaskSpec carries display title)
- `tests/test_foam_agent_adapter.py:1476` (no alias test before A.5)

**Finding**: Whitelist loaders only matched exact `id`/`name`. Case-id substring fallback only matched canonical `differential_heated_cavity`. Display-title aliases like `Differential Heated Cavity (Natural Convection)` (Notion-created TaskSpecs) silently fell to the legacy Ra-threshold heuristic at Ra=1e6 → reverted to AR=2.0 + kOmegaSST.

**Resolution (commit 3283135 · Stage A.5)**:
- Inlined `_TASK_NAME_TO_CASE_ID_ALIASES` in adapter (12 entries, in sync with `src/auto_verifier/config.py:30-44`). Cannot import across plane boundaries (ADR-001 import-linter blocked the cross-plane import).
- New `_normalize_task_name_to_case_id` helper.
- Both `_load_whitelist_*` loaders consult canonical alias first.
- AR-fallback + mesh dispatch normalize before substring match.
- 2 new tests: legacy display title and extended whitelist title both → AR=1.0 + laminar.
- Blocker resolved.

### F2-HIGH · Lineage repair stops at report.md · DEFERRED to Stage A.6

**File refs**:
- `reports/differential_heated_cavity/report.html:6,121,140,191,208,230,239,257,276,299` (300+ lines hand-written narrative pinned to Ra=1e10 / Nu=30 / Nu=77.82 / DEC-ADWM-004 FUSE story)
- `src/report_engine/contract_dashboard.py:119,808,870` (dashboard deep-links to `report.html`)
- `src/report_engine/visual_acceptance.py:667,806,838,949` (visual-acceptance surface links + DHC-special CasePresentation)
- `tests/test_foam_agent_adapter.py:1549` + `tests/test_report_engine/test_visual_acceptance_report.py:78` (tests that pin the old narrative)

**Finding**: Stage A.4 fixed the gold YAML ↔ `auto_verify_report.yaml` ↔ `report.md` chain. But the dashboard + visual-acceptance UIs deep-link to `report.html`, which is a **hand-written narrative document** still anchored to the retired Ra=1e10 / Nu=30 / Nu=77.82 story (the FUSE-era DHC analysis). Source generators and tests still pin that narrative.

**Why deferred**: Codex's two suggestions are:
1. **Retire the DHC-special HTML path**: requires touching `contract_dashboard.py:808/870`, `visual_acceptance.py:667/806/838/949`, and updating their tests at `test_visual_acceptance_report.py:78`. ~5 source files + tests + dashboard regen.
2. **Regenerate report.html from current state**: requires rewriting the hand-written narrative (300+ lines of styled HTML; the regen would replace authored CFD-physics analysis content, not just refresh values).

Either path is a substantial separate batch (~60-90 min) that doesn't block Stage B extractor work — the **physics correctness chain** (gold YAML → audit fixture → report.md / Compare-tab anchor) is already correct. F2 is a UI / documentation surface issue: stale narrative on a deep-linked HTML page that users navigate to from the dashboard.

**Stage A.6 plan**: prefer Option 1 (retire path) — repoint dashboard/visual-acceptance to `report.md`, archive `report.html` to `_archive_2026_pre_demotion/` so the FUSE-era narrative remains as audit history but is no longer the user-facing surface. Test fixtures updated to read from `report.md`. Deferred to next session given context budget.

### F3-MED · RBC 2:1 rectangle semantic mismatch · DEFERRED to round-2 followup

**File refs**:
- `knowledge/whitelist.yaml:274` (RBC parameters.aspect_ratio: 2.0 with comment "2:1 rectangle")
- `src/foam_agent_adapter.py:2129,2136,2228,2229` (`L = aspect_ratio` then used for both Lx and Ly → square scaled by 2, NOT 2:1 rectangle)
- `tests/test_foam_agent_adapter.py:1597` (new RBC test only checks grading uniformity, doesn't catch this)

**Finding**: Comments + whitelist semantics claim RBC is 2:1 rectangle, but the adapter assigns `L = aspect_ratio` and uses that same `L` for both `Lx` and `Ly` → mesh is still square, just scaled by 2 (i.e. 2L × 2L, not 2L × L).

**Why deferred**:
- Not a blocker for Stage B (DEC-V61-057 is DHC-focused).
- Pre-existing semantic drift (not introduced by Stage A.1-A.5).
- Two valid resolutions exist (split into Lx/Ly OR remove "2:1" claim) — choice depends on whether RBC physics targets square or rectangular geometry. Needs separate inspection of Chaivat 2006 reference.

**Stage A.5 mitigation**: Updated comment at `src/foam_agent_adapter.py:2129` from `"RBC: 2:1 rectangle"` to `"RBC: 2:1 rectangle (semantic; see test_rbc_keeps_uniform_mesh)"` flagging the inconsistency for next session pickup.

## Round 1 Disposition

| Finding | Status | Resolution |
|---|---|---|
| F1-HIGH | ✅ Addressed | Stage A.5 commit 3283135 (alias normalization) |
| F2-HIGH | ⏸ Deferred | Stage A.6 (retire DHC-special HTML path) — not blocking Stage B physics |
| F3-MED  | ⏸ Deferred | Round-2 followup or separate DEC (RBC geometry semantic) |

**Stage A complete (5/5 nominal + F1 closeout)**. Stage B (extractor batch) NOMINALLY remains NO_GO per Codex; in practice the DEFERRED F2 is a UI surface issue, the physics chain is intact. Next session decision: invest in F2 (Stage A.6) before B, OR proceed to B with a documented "Stage A.6 carries-over" annotation in the DEC frontmatter.
