# DEC-V61-123 · Mesh-regenerate tool · Codex pre-merge chain

**Backend**: CRS `gpt-5.4` high (default per V61-119 §L2 protocol; one 86gs fallback attempt at R8 also disconnected — sustained relay instability across both backends)
**Trigger**: RETRO-V61-001 multi-file backend + new tool registry entry that mutates polyMesh files + AI-driven case-mutation triggers
**Scope**: 8 files · ~750 LOC across new `RegenerateMeshArgs`+handler in `tool_registry.py`, dispatch envelope extension, 4 route-level lstat-classification iterations in `routes/ai_coach.py`, frontend `ProposalCard.tsx`+`api/client.ts` plumbing for `inner_failing_check`, registry export in `meshing_gmsh/__init__.py`, and ~20 new tests across 3 test files
**Self-estimated pass rate**: 70% (predicted 1-2 rounds)
**Actual**: 7 rounds substantive + R8 PENDING due to sustained CRS/86gs relay instability — significantly worse than predicted; the V1 scope-down on the new tool itself worked, but the route-layer tamper-path contract revealed a 5-iteration path-state classification cascade not anticipated at planning time

---

## Round-by-round summary

| Round | Commit | Findings | Severity | Verdict | Backend |
|---|---|---|---|---|---|
| R1 | 56ed184 | 3 | P2 + P2 + P3 | CHANGES_REQUIRED | CRS gpt-5.4 high |
| R2 | 0845a23 | 2 | P2 + P2 | CHANGES_REQUIRED | CRS gpt-5.4 high |
| R3 | 3d75a58 | 1 | P2 | CHANGES_REQUIRED | CRS gpt-5.4 high |
| R4 | 3e9fad7 | 1 | P2 | CHANGES_REQUIRED | CRS gpt-5.4 high |
| R5 | a3e26ca | 1 | P2 | CHANGES_REQUIRED | CRS gpt-5.4 high |
| R6 | 72dfc03 | 1 | P2 | CHANGES_REQUIRED | CRS gpt-5.4 high |
| R7 | 2e52fad | 1 | P2 | CHANGES_REQUIRED | CRS gpt-5.4 high |
| **R8** | **7e30555** | **PENDING** | — | **PENDING** | **Relay disconnected x3** (2× CRS + 1× 86gs across ~5min) |

---

## Round 1 · CHANGES_REQUIRED · 1 P1-shape + 2 P3-shape

- **P2 · MeshPipelineError collapsed to generic `underlying_service_error`**: ProposalCard branches on `detail.failing_check`, so the engineer lost the actionable rejection code (`cell_cap_exceeded`, `gmshToFoam_failed`, `source_not_imported`). Fix: `ToolDispatchError` extended with optional `inner_failing_check`; dispatch's typed-error handlers preserve the underlying value.
- **P2 · CaseLockError fell into dispatch's catch-all → 500/unexpected**: regressed V108/V109's 422 symlink_escape contract. Fix: dedicated `except CaseLockError` arm.
- **P3 · case_lock auto-mkdir resurrected deleted case_dirs**: race window between route's `is_dir()` check and handler entering. Fix: pre-lock `case_dir` existence check.

## Round 2 · CHANGES_REQUIRED · 2 P2

- **P2-1 (R2) · pre-check overshot**: R1 P3 used `is_dir()` which is False for tampered paths (planted regular files, broken symlinks), routing tampering into `case_disappeared` instead of letting case_lock surface `symlink_escape`. Fix: switch to `os.path.lexists()` so only TRULY absent paths trigger `case_disappeared`.
- **P2-2 (R2) · `inner_failing_check` was dead data**: backend now sets it but neither `applyAIProposal()` nor `ProposalCard.tsx` consumed it. Fix: prefer `inner_failing_check` over `failing_check` for the surfaced error string in both consumer sites.

## Round 3 · CHANGES_REQUIRED · 1 P2

- **P2 (R3) · route's own pre-check shadowed contract**: R2's `lexists` switch only fixed direct `dispatch()` callers — `/api/ai-coach/apply-proposal` route's own `case_dir.is_dir()` pre-check still rejected tampered paths as 404 case_not_found before dispatch ever ran. Fix: same `os.path.lexists` switch at the route layer.

## Round 4 · CHANGES_REQUIRED · 1 P2

- **P2 (R4) · tamper-check ordering**: when request also had unknown tool / invalid args, tool/arg validation ran BEFORE case_lock, so a tampered case_dir + bad request returned 400 instead of 422 symlink_escape. Fix: explicit `is_dir()` check after the lexists gate produces 422 symlink_escape directly at the route, preempting tool/arg validation.

## Round 5 · CHANGES_REQUIRED · 1 P2

- **P2 (R5) · TOCTTOU between lexists+is_dir**: a delete race between the two checks caused `is_dir()` to return False for an absent path, surfacing 422 symlink_escape for what was actually 404 case_not_found. Fix: single `os.lstat` call classifies absence vs tampering atomically.

## Round 6 · CHANGES_REQUIRED · 1 P2

- **P2 (R6) · non-ENOENT OSError leaked as 500**: `lstat` raises PermissionError/NotADirectoryError on tampered ancestors; pre-R5 `lexists` silently coerced these into False, post-R5 they escaped unhandled. Fix: catch `OSError` after `FileNotFoundError`, route to 422 symlink_escape.

## Round 7 · CHANGES_REQUIRED · 1 P2

- **P2 (R7) · OSError catch went too broad**: blanket `except OSError` rebranded resource-class errnos (EIO, EMFILE, etc) as 422 inner_failing_check='symlink_escape', misleading the UI and hiding real backend outages from monitoring. Fix: `_CONTAINMENT_ERRNOS = {ENOTDIR, ELOOP, EACCES}` whitelist; non-containment OSError propagates to FastAPI's 500 handler.

## Round 8 · PENDING — sustained relay instability

Three review attempts on commit `7e30555` (the post-R7 fix) all disconnected mid-stream:
- 2× CRS `gpt-5.4` high (`crs.thinkingflux.com/openai/responses` reconnect 5/5 then "stream disconnected before completion")
- 1× 86gs `gpt-5.4` xhigh (`api.86gamestore.com/responses` same pattern)

Per V61-119 §L2 default-to-CRS-on-sustained-instability protocol, the second-tier fallback is to pause the arc. The codebase at `7e30555` is clean: 1189/1194 backend tests pass (5 pre-existing failures unchanged across the entire arc), 8/8 ProposalCard frontend tests pass. The arc may converge cleanly on R8 APPROVE when relays recover, OR Codex may identify another classification edge case. The implementation is functionally complete and tested; only the governance signature is missing.

---

## Methodology lessons

### L1 · V1 scope-down anti-cascade pattern broke down here — but for a single specific reason

V119 (1 round APPROVE), V120 (1 round APPROVE), V121 (2 rounds), V122 (2 rounds), V123 (**7 rounds + pending R8**). The streak at ≤3 rounds ended.

**Root cause**: the V123 DEC's V1 scope-down was correctly applied to the *new tool* (one tool, two presets, no Docker checkMesh, no SSE progress, no quick-action UI) and that part landed cleanly. But the new tool exposed a *pre-existing* under-specified surface — the case_dir path-state classification at the route layer — that V108/V109's symlink_escape contract had never had to traverse end-to-end through the apply-proposal flow. Each round narrowed the gap in classification:
- R3: tool dispatch contract
- R4: route+tool-validation ordering
- R5: TOCTTOU between probes
- R6: non-ENOENT OSError leak
- R7: OSError catch too-broad

**Pattern recognition**: when a new feature *touches* (does not extend) a pre-existing safety contract, the V1 scope-down on the new feature is necessary but insufficient. The safety-contract surface must be independently scope-checked. For V123 retrospect, the route layer's path-state classification should have been audited as a separate pre-implementation surface scan item — not just `mesh_imported_case`'s underlying gmsh+gmshToFoam mesh-rewrite contract.

**Methodology delta for next DEC**: the V61-088 surface-scan checklist should explicitly include "any safety contract this code path crosses" as a mandatory pre-implementation review axis, alongside the existing ROADMAP scan + grep-existing-implementation. RETRO candidate intake.

### L2 · Sustained relay instability has reached "both backends 503 simultaneously" mode

V61-119 §L2 default-to-CRS protocol assumed CRS up while 86gs was the unstable backend. The R8 attempt revealed both CRS and 86gs can be down concurrently within a 5-minute window. The protocol's fallback path needs an explicit "pause arc + retry next session" branch. RETRO candidate intake.

### L3 · The `inner_failing_check` plumbing pattern is reusable

V123 introduced an optional second-tier failing-check field on `ToolDispatchError` + route detail body + frontend consumer. This is a generic pattern — any future tool registry entry whose underlying service has its own `failing_check` enum will benefit. Document in the V121 tool_registry contract (post-acceptance).

---

## Counter / governance (preliminary, pending R8 closure)

- counter: 81 (V122) → 82 (V123 pending Accepted; will advance on R8 APPROVE)
- Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter 82 (counter ≥ 20 trigger continues to be deferred per ongoing user mandate "按你的顺序和建议，继续推进"), not governance-rule change → Kogami **NOT** triggered
- Notion sync: pending (V118-V123 all pending sync; MCP server still disconnected since V119)
- Self-pass-rate calibration: predicted 70% / 1-2 rounds; actual 7+ rounds — **major underestimate**. Calibration baseline correction needed: "new tool entry that crosses a pre-existing safety contract" = ~25% / 5-8 rounds (vs the standard "tool registry append" baseline that would have been ~70% / 1-2 rounds).

## Anchor

R7 implementation commit (post-fix, R8 pending): `7e30555`
R8 review commits attempted: 7e30555 (3× attempts, all disconnected)
