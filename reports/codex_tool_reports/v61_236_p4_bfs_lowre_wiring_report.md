# Codex review trail — DEC-V61-236 (P4 V71.B low-Re BFS live-wiring)

- **Relay**: 86gs gpt-5.4 xhigh (`CODEX_HOME=$HOME/.codex-relay codex review --commit <SHA>`)
- **Round cap**: 3 (R0 + 2 fix iterations)
- **Scope reviewed**: the V71B-FOLLOWUP-1 item-1 wiring slice — adapter `_docker_run_of11_rm` +
  `_execute_backward_facing_step_lowre` + `execute()` dispatch, `TaskRunner._verify_bfs_lowre` +
  the 4c branch, the `backward_facing_step_lowre` whitelist entry, the offline + opt-in-live tests,
  and the frozen backend-e2e evidence.

---

## R0 — commit `462902e` — CHANGES_REQUIRED (1 P1 + 1 P2)

Both findings are production-path reachability (the runtime-emergent class the cross-family
review exists to catch — the same class as DEC-V61-235 R0/R1).

### [P1] Undeclared `pyvista` runtime dependency — `src/foam_agent_adapter.py` (low-Re runner)

> In a clean repo environment created from `pyproject.toml`/`uv.lock`, this new path will fail
> after the solver finishes because `write_floor_faces_csv()` imports `pyvista`, but `pyvista`
> is not declared anywhere in the project dependencies. Since the low-Re runner always goes
> through this call before extracting QoIs, `backward_facing_step_lowre` is not actually runnable
> end-to-end on fresh machines or CI unless they happen to have that package installed out of band.

**Verified VALID.** `src/bfs_lowre_extractor.py:168,196` lazily `import pyvista`; `pyvista` was
absent from `pyproject.toml` and `uv.lock` entirely (present only in the dev `.venv` out-of-band).
The existing high-Re VTK paths (`comparator_gates.py:205`, `foam_agent_adapter.py:9890`) already
rely on pyvista but degrade gracefully (return None / `pyvista_missing` marker); the new low-Re
runner did not — its `except (FileNotFoundError, ValueError, KeyError)` did not catch `ImportError`,
so a clean env would always BLOCK, never produce a real result.

**R1 fix.** (a) Declared `pyvista>=0.44` in the `cfd-real-solver` optional-dependency group —
the same home as `docker>=7.0`, with a comment mirroring the docker "previously-implicit" rationale.
It is NOT a core dep because the OFFLINE gate-replay reads the frozen `proof/floor_faces.csv` with
stdlib only (MOCK + CI unit tests stay pyvista-free; verified — `bfs_lowre_extractor` imports pyvista
lazily, so module import does not require it). (b) Regenerated `uv.lock` (`uv lock`) → pyvista 0.48.4
+ vtk 9.6.2 + deps added, scoped `marker = "extra == 'cfd-real-solver'"`. (c) Added an explicit
`except ImportError` in the runner → an actionable BLOCK (`install -e '.[cfd-real-solver]'`) instead
of the generic belt-and-braces catch.

### [P2] Exact-name dispatch unreachable from display-title callers — `src/foam_agent_adapter.py` (execute dispatch)

> This dispatch only fires when `TaskSpec.name` is literally `backward_facing_step_lowre`. That
> works for the whitelist/batch path, but `NotionClient._parse_task()` sets `name` from the page
> title, so a low-Re BFS task launched through `run_all()` or any other display-title caller will
> fall through to the generic high-Re BFS branch instead of the new runner.

**Verified VALID-but-on-a-DORMANT-path.** `notion_client._parse_task` does set `name=get_title("Name")`
and `boundary_conditions={}`, so a Notion task would match neither the slug-name nor a resolved-BC
signal → fall through to the high-Re branch. HOWEVER: (i) the Notion path is **retired** (sponsor
directive 2026-06-09), and (ii) it is already **dormant** — `TaskRunner.run_all()` →
`NotionClient.list_pending_tasks()` raises `NotImplementedError` → `run_all()` returns `[]` (logs
"Notion not configured"). So no low-Re task can in fact be launched-and-mis-dispatched today. The
SUPPORTED entrypoints (whitelist→`run_batch` with name==id; direct `TaskSpec` construction / the
e2e test) reach the wiring correctly.

**R1 fix (addresses the spirit, strictly safer).** Broadened the dispatch to a DISJUNCTION:
`geometry==BACKWARD_FACING_STEP AND (name=='backward_facing_step_lowre' OR
boundary_conditions.wall_treatment=='resolved')`. The second disjunct routes any direct/display-title
caller that explicitly asks for the resolved treatment, even with a non-slug name. The high-Re sibling
(wall_function, never 'resolved') matches NEITHER → no false-positive; the runner re-FORCES
resolved+kOmegaSST and the gate machine-enforces y+<1, so a mislabelled coarse mesh cannot fake a
resolved PASS. Documented the retired/dormant Notion path in the dispatch comment. Added regression
`test_execute_routes_display_title_with_resolved_bc` (display-title + resolved-BC routes) and fixed
`test_execute_does_not_route_high_re_bfs_to_lowre_runner` to use a REALISTIC high-Re spec (wall_function,
not the unrealistic 'resolved' the old `_bfs_spec` injected).

**Note on evidence:** the R1 fixes are dispatch-breadth / dependency-declaration / error-path only —
they do NOT change the solver command, mesh, or extraction, so the frozen backend-e2e evidence
(`reports/showcase_aero/_v71b_bfs_lowre_backend_e2e/`, VTK byte-identical to the V&V probe) remains
valid and is not re-frozen.

**R1 regression**: tests/p4 67 passed / 2 skipped · full suite 2085 passed / 5 skipped ·
import-linter 5 kept / 0 broken · high-Re BFS byte-identical (blockMeshDict 13ac9387d7464d6a,
controlDict 9710a9da976b5fae).

---

## R1 — commit `53d8ca0` — CHANGES_REQUIRED (1 P1 + 1 P2)

Both findings are the symmetric consequences of the R1 fixes — exactly the runtime
reachability class the review is for.

### [P1] execute/verify dispatch ASYMMETRY — `src/foam_agent_adapter.py` ↔ `src/task_runner.py`

> For callers that go through `TaskRunner.run_task()` with a display-title BFS spec
> (`geometry_type=BACKWARD_FACING_STEP`, `boundary_conditions.wall_treatment='resolved'`),
> this new branch now executes `_execute_backward_facing_step_lowre()`, but `TaskRunner`
> still invokes `_verify_bfs_lowre()` only when `task_spec.name == 'backward_facing_step_lowre'`.
> The result is a real low-Re run reported as success but with `comparison_result=None`, so
> the specialized y+<1 / reattachment gate is silently skipped on the very caller class this
> change is trying to support.

**Verified VALID — a real bug the R1 P2 fix introduced.** Broadening the *execute* dispatch
(R1) without broadening the *verify* branch left them asymmetric: a resolved-BC display-title
spec executed a real solve but skipped the gate (`comparison_result=None`).

**R2 fix (root cause).** Extracted ONE shared predicate `is_bfs_lowre_dispatch(task_spec)` into
`src/models.py` (the four-plane leaf both planes already import — import-linter 5 kept/0 broken)
and made BOTH `execute()` dispatch AND the TaskRunner 4c branch call it. The two sites now
share a single SSOT predicate and cannot drift. +`test_run_task_verifies_display_title_resolved_bc_lowre`
(run_task on a display-title resolved-BC spec → `comparison_result` populated, gate PASS) +
`test_is_bfs_lowre_dispatch_shared_predicate` (4 cases: slug-name routes, resolved-BC routes,
high-Re wall_function does NOT, non-BFS geometry does NOT).

### [P2] pyvista also needed on the `workbench` install surface — `pyproject.toml`

> In a clean environment installed with `pip install -e '.[workbench]'`,
> `ui/backend/services/wizard_drivers.RealSolverDriver` can still launch
> `backward_facing_step_lowre`, but the dedicated runner will fail after the solve because it
> now imports `pyvista` and this dependency is only declared in `cfd-real-solver`.

**Verified VALID.** The `workbench` extra carries `docker>=7.0` explicitly so the
workbench-only install is runnable end-to-end; `RealSolverDriver` wraps
`FoamAgentExecutor.execute()`, which reaches the low-Re runner. pyvista was missing from
`workbench`, so `.[workbench]` would crash at the VTK read.

**R2 fix.** Declared `pyvista>=0.44` in the `workbench` extra too (same pattern + comment as its
`docker` line — no hidden cross-extras dependency on `cfd-real-solver`).

**R2 regression**: tests/p4 13 wiring/taskrunner passed · full suite 2087 passed / 5 skipped ·
import-linter 5 kept / 0 broken · high-Re BFS byte-identical.

---

## R2 — commit `8d18727` — CHANGES_REQUIRED (1 P2, no P1) · CAP REACHED

### [P2] Benchmark gate over-broadened to non-anchor resolved drafts — `src/task_runner.py`

> When a workbench/user-draft BFS spec has `boundary_conditions.wall_treatment: resolved`
> but a custom `name` (so `load_gold_standard(task_spec.name)` returns None), this new
> condition sends `run_task()` through `_verify_bfs_lowre()`. That verifier always compares
> against the `backward_facing_step_lowre` anchor, so a non-anchor resolved BFS draft (for
> example with different `Re`) will now be reported as PASS/FAIL against the benchmark
> instead of remaining unverified. The previous name-only check avoided this.

**Verified VALID — and it exposes that the R1 `wall_treatment` disjunct was an
over-correction.** The original R0 P2 (display-title reachability) was about the RETIRED +
already-dormant Notion path — a non-issue. The R1 disjunct, added to "fix" it, instead (i)
created the R1 P1 asymmetry and now (ii) mis-grades arbitrary resolved-BFS drafts against the
Re=5000 benchmark. The correct design was **name-only all along** (where R0 started).

**R2-followup fix (commit the R2-followup commit (this commit)).** Narrowed the SHARED `is_bfs_lowre_dispatch`
predicate BODY to **name-only** (`geometry==BACKWARD_FACING_STEP AND
name=='backward_facing_step_lowre'`) — the whitelist slug. This:
- resolves R2 P2 (the gate fires ONLY for THE Re=5000 anchor; non-anchor drafts stay
  unverified by it — they fall through to the generic path);
- PRESERVES the R1 P1 structural fix (execute + verify still call the ONE shared predicate,
  so they remain symmetric and cannot drift — only the predicate body narrowed);
- dispositions R0 P2 (display-title/Notion) as a documented non-issue (retired + dormant).
The pyvista declarations (R0 P1 + R1 P2) are unchanged. Tests inverted to match: a non-anchor
resolved draft does NOT route (`test_execute_does_not_route_nonanchor_resolved_bfs_draft`) and
is NOT benchmarked (`test_run_task_nonanchor_resolved_draft_not_benchmarked`); the slug anchor
IS verified symmetrically (`test_run_task_anchor_is_verified_symmetrically`); predicate 4-case
test updated.

**R2-followup regression**: tests/p4 14 wiring/taskrunner passed · full suite 2088 passed /
5 skipped · import-linter 5 kept / 0 broken · high-Re BFS byte-identical.

### Round-cap = 3 status

R0 + R1 + R2 = **3 rounds (cap reached)**. R2 carried **no P1** (one P2). Per the project rule
(`第 3 轮仍有 P1 → 交用户裁决；剩余 P2/P3 → retro 队列`), the lone P2 does not block — but it
was a genuine correctness bug, so it was FIXED (name-only revert to the R0-reviewed state)
rather than queued. Per the cap, NO 4th (R3) Codex round is auto-run; the R2-followup fix is
surfaced to the user (final authority) to either ratify as-is or authorise one confirmatory
review. The fix is a low-risk revert of the specific aspect R2 flagged; all R0/R1/R2 findings
are resolved.

**User decision (2026-06-09)**: authorised ONE confirmatory review (a cap override — user is
final authority) on the R2-followup commit f62aa1d.

---

## R3 (user-authorised confirmatory) — commit `f62aa1d` — CHANGES_REQUIRED (1 P1)

### [P1] Name-only key escapes the renamed canonical anchor — `src/models.py` ↔ `wizard_drivers`

> If a saved `ui/backend/user_drafts/backward_facing_step_lowre.yaml` changes only the
> human-readable `name`, `wizard_drivers._task_spec_from_case_id()` still launches that canonical
> case_id but populates `TaskSpec.name` from the edited field. With this name-only predicate, the
> run no longer reaches `_execute_backward_facing_step_lowre` or `_verify_bfs_lowre`; it falls back
> to the generic BFS path, and because `load_gold_standard()` has no inline gold for this anchor,
> `run_task()` reports a successful run with `comparison_result=None`. This is a live regression for
> the draft/editor path of the benchmark anchor.

**Verified VALID and reachable.** `_task_spec_from_case_id` reads `user_drafts/{case_id}.yaml`
first (the workbench editor's `PUT /api/cases/{id}/yaml` save surface) and sets
`name=entry.get("name", case_id)` — so a renamed anchor draft carries the edited display `name`
while still launched under the stable `case_id`. A name-only dispatch then lets it escape the
runner + gate → a SILENT UNVERIFIED PASS on the benchmark (the cardinal trust-harness sin). NOTE:
this is a LATENT pre-existing edge of the name-only approach (the same dispatch R0 shipped), not a
regression introduced by the followup; it surfaced only under the confirmatory deep read.

**Structural fix (user-chosen — closes the whole identity class).** Added a stable
`case_id: Optional[str]` field to `TaskSpec` (distinct from the editable `name`) and keyed
`is_bfs_lowre_dispatch` on `case_id or name` (case_id preferred; name fallback for direct
constructors that don't set it). Populated `case_id` at the three loaders that know the stable id:
`wizard_drivers._task_spec_from_case_id` (=case_id param — the R3 P1 site), `knowledge_db.list_whitelist_cases`
(=case["id"]), `task_runner._task_spec_from_case_id` (=case_id param). Now a renamed anchor draft
carries `case_id='backward_facing_step_lowre'` → routes + verifies; a non-anchor draft carries its
own case_id → stays unverified by this gate (R2 P2 preserved); direct constructors (e2e test) keep
working via the name fallback. The field defaults None → backward-compatible.

Tests: `test_renamed_canonical_anchor_draft_preserves_case_id_for_dispatch` (REAL
`_task_spec_from_case_id` loader: a renamed anchor draft → `case_id` preserved → routes) +
predicate cases a2 (renamed anchor routes) and b2 (case_id wins over a misleading display name) +
`test_run_task_renamed_anchor_still_verified`.

**R3-fix regression**: tests/p4 + wizard rename regression passed · full suite (tests/ +
ui/backend/tests/) tests/ 2088 passed/5 skipped + the real-loader rename regression passes; ui/backend/tests/ has 9 PRE-EXISTING failures (baseline-confirmed identical at b6d6151 — ZERO net-new from DEC-236: stale catalog-count + artifact/Docker real-run tests) · import-linter 5 kept / 0 broken · high-Re BFS byte-identical.

### Final round-cap status

R0 + R1 + R2 (cap) + R3 (user-authorised confirmatory) = 4 rounds. The structural fix above
(user-chosen) is followed by ONE final confirmatory review per the same user authorisation.
