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

## R1 — commit `<PENDING>` — verdict PENDING
