# Workbench × Persona Findings Index (F-series)

> **Living document.** Append a new row whenever a dogfood / live persona
> run surfaces a new persona-facing failure mode. Update Status when a
> finding is fixed, mitigated, or superseded. SSOT for all
> persona-facing workbench surface-area gaps.
>
> **B-extend arc closed 2026-05-07** per DEC-V61-198. F-series remains
> live for future single additions, but is no longer the primary
> dogfood substrate; industrial-case dogfood (V-series) takes that role.

## Complementary index — V-series (engineer/solver internals)

F-series captures **persona-facing** surface failures (REST API, route
taxonomy, OpenAPI descriptors, response shape). For **engineer-facing
solver / mesh internals** — failures that surface when a human + Claude
Code drive an industrial CAD case end-to-end — see the parallel index:

- `.planning/methodology/industrial_case_solver_findings.md` (V-series)
- `.planning/methodology/solver_convergence_playbook.md` (decision tree)

The two indices are **complementary, non-overlapping**. Quick
classification: if the failure would still happen with no LLM in the
loop, it is V-series; otherwise F-series.

## Why this index exists

The B-arc + B-extend arcs (V61-162 .. V61-197) accumulated 30+ live
DeepSeek-driven simulation runs against the workbench. Each run
surfaced one or more failure modes that **only manifest when a real
engineer-shaped LLM persona drives the workbench end-to-end**, not
when the workbench is exercised by its own M-series tests or the M3
RealSolverDriver internal flow. The cumulative list (F1..F15) is
itself a methodology artifact: future engineers adding new
persona-facing routes should scan this index first, because most of
the gaps below were caused by route surfaces that were correct for
internal callers but wrong for engineer-shaped callers.

This document is the entry point. Each row links to:
1. The DEC that surfaced or closed the finding
2. The fix commit (when applicable)
3. The lesson learned

## Status legend

- **closed** — fully fixed and live-verified
- **partial** — mitigated; structural fix deferred (e.g. F13)
- **open** — known gap, not yet addressed
- **superseded** — folded into a later finding

## Findings index

### F1 · `/api/cases/{id}/state` does not exist

| field | value |
|---|---|
| Surface | persona-side prompt referenced `/state`; workbench exposes `/state-preview` |
| Persona symptom | All 3 R3 personas burned 5-15 turns hunting for the right "where am I" route |
| Root cause | B.2 persona prompts written from a mental model that didn't match the actual route taxonomy |
| Fix | DEC-V61-167 (B.5.1 prompt update) — `/state-preview` + `/completeness` referenced explicitly; DEC-V61-168 added `/state` alias on workbench side |
| Status | **closed** |
| Lesson | If a route name is "engineer-conventional" (e.g. `/state`), expose it as an alias even if the canonical name is more precise. The cost of the alias is one line; the cost of every future persona burning turns hunting for it is unbounded. |

### F2 · 5-step workflow taxonomy is not discoverable

| field | value |
|---|---|
| Surface | persona POSTs `/workflow`, `/workflow/step`, `/steps`, `/step1_mesh` etc — none exist |
| Persona symptom | 20+ HTTP calls per persona trying engineer-conventional sub-paths before discovering the `import` vs `cases` taxonomy split |
| Root cause | Workbench mixes `/api/cases/{id}/...` (queries) with `/api/import/{id}/...` (mutations); engineer mental model expects unified `/cases/{id}/<step>` |
| Fix | DEC-V61-169 (B.5.3 actions discovery) — `GET /api/cases/{id}/actions` returns canonical URL list per step transition |
| Status | **closed** |
| Lesson | Persona-facing route taxonomies need a single discovery endpoint. Don't rely on persona reading `/openapi.json` — that's a fallback, not a primary path. |

### F3 · `GET /api/cases/{id}/physics` returned 405 (POST-only)

| field | value |
|---|---|
| Surface | physics route was POST-only; persona expected GET-then-POST pattern |
| Persona symptom | `experienced_fluent` persona on naca0012 hit 405, then POSTed a guess body and got 422 |
| Root cause | Engineer mental model: query state before mutating. Workbench had POST /physics but no GET counterpart. |
| Fix | DEC-V61-168 — added GET /physics returning current physics state |
| Status | **closed** |
| Lesson | Every mutation route should have a paired read route. The pair is what makes the surface idempotent-discoverable. |

### F4 · OpenAPI self-discovery works as a fallback

| field | value |
|---|---|
| Surface | `GET /api/openapi.json` returns full spec |
| Persona symptom | One persona discovered it mid-run after burning ~70% token budget |
| Root cause | Discoverability gap, not a bug — but the prompt didn't mention it as a fallback |
| Fix | DEC-V61-167 — persona prompts now mention `/api/openapi.json` as the explicit fallback when 404s accumulate |
| Status | **closed** |
| Lesson | Document discoverability fallbacks in the persona prompt. Tokens spent guessing routes are wasted; tokens spent reading openapi.json are recoverable. |

### F5 · BC `example_body` schemas didn't carry patch-discovery hints

| field | value |
|---|---|
| Surface | `/setup-bc` schema examples used canned LDC patches; persona didn't know to discover patches first on non-LDC geometry |
| Persona symptom | partial — coupled with F7 (patch discovery itself) |
| Root cause | Schema discoverability gap — examples were correct for LDC but didn't telegraph that other geometries need pre-discovery |
| Fix | DEC-V61-170 (B.5.5 schema examples + budget) — example_body now carries patch-discovery hints |
| Status | **closed** (coupled with F7) |
| Lesson | Schema examples carry implicit assumptions. Document them, or move them out of the example into prereq notes. |

### F6 · Per-turn input bandwidth blows budget on long runs

| field | value |
|---|---|
| Surface | persona_runner accumulated full `tool_result` content forever |
| Persona symptom | R3 cells hit max_input_tokens at step ~30-40; conversation became unviable |
| Root cause | Architectural: harness didn't prune old tool_results; every turn re-sent full body |
| Fix | DEC-V61-173 (B-ext.1) — `_prune_messages()` keeps last N turn pairs full, compresses older `tool_result.content` to one-liner stub |
| Status | **closed** |
| Lesson | Persona-driving harnesses MUST prune. Default `keep_full=3` (live runs use this); set to 0 only if you genuinely want full history (debugging). |

### F7 · STL patch discovery surface invisible

| field | value |
|---|---|
| Surface | personas didn't know to call `/face-annotations` + `/face-index` + `/patch-classification` before `/setup-bc` on non-LDC geometry |
| Persona symptom | pipe_expansion / debug R3 stuck at Step 4 setup-bc 422 |
| Root cause | Patch-split-before-BC was an undocumented prerequisite; no surface in `/actions` catalogue |
| Fix | DEC-V61-174 (B-ext.2) — face-annotations / face-index / patch-classification routes added to `/actions` catalogue + Step 4 prereq docs in persona prompts |
| Status | **closed** |
| Lesson | "Implicit prereq" is a contradiction in terms for persona-driven workflows. Make it explicit in `/actions`. |

### F8 · `/setup-bc?from_stl_patches=1` requires named-solid STL

| field | value |
|---|---|
| Surface | single-shell STL (no named solids) → from_stl_patches=1 returns 400 `no_named_patches` |
| Persona symptom | backward_step / pipe_expansion personas POSTed from_stl_patches=1 and got 400 with cryptic message |
| Root cause | Workbench requires named-solid STL for from_stl_patches=1 path; rejection message didn't suggest the LDC fallback or patch-classification alternative |
| Fix | partial — DEC-V61-175 (B-ext close) framed F8 as "async solve job lifecycle" originally; later reframed in B-ext-2 charter as schema-rejection that needs better error guidance. **Mitigation only**: persona prompts updated to detect 400 and fall back to LDC defaults + manual patch-classification. |
| Status | **partial** — error message could be more actionable; structural fix deferred |
| Lesson | Rejection messages on persona-facing routes should suggest the next-best path explicitly, not just describe the failure. |

### F9 · solver_runner crashed on `0.orig` time directory

| field | value |
|---|---|
| Surface | `_filter_numeric_time_dirs` in `solver_runner.py` called `float()` on directory names; `0.orig` raised ValueError |
| Persona symptom | R5 backward_step `/solve` returned 502 with cryptic Python traceback |
| Root cause | Filter assumed all time dirs are numeric; OpenFOAM `0.orig` is a backup directory standard but non-numeric |
| Fix | DEC-V61-180 (B-ext-3.1 + B-ext-3.2) — `_filter_numeric_time_dirs` now silently skips non-float-parseable names |
| Status | **closed** |
| Lesson | OpenFOAM directory conventions include non-numeric special names (`constant`, `system`, `0.orig`, `processor*`). Any code touching time directories must allowlist or robust-parse, not assume float-only. |

### F10 · setup-bc → polyMesh patch-name mismatch after re-mesh

| field | value |
|---|---|
| Surface | persona POSTed `/mesh` AFTER `/setup-bc` → polyMesh regenerated to single-patch state, but 0/p + 0/U still referenced `lid` + `fixedWalls` from the prior setup-bc |
| Persona symptom | `/solve` returned cryptic 502 `Cannot find patchField entry for patch0` |
| Root cause | F11's path mismatch was masked by this F10 mismatch — solver dies on field load before reaching the run-history persistence path |
| Fix | DEC-V61-182 (B-ext-3.2) — two-pronged: (a) `_check_mesh_bc_consistency` pre-flight in `run_icofoam` returns 409 `mesh_bc_mismatch` instead of 502; (b) `mesh_imported_case` post-success eagerly invalidates `0/`, `0.orig/`, and the manifest's `0/*` user-overrides so next setup-bc starts fresh |
| Status | **closed** |
| Lesson | Re-meshing is destructive to BC state. Either prevent it (CONFLICT route response) or invalidate downstream artifacts atomically. Persona prompts can't fix this — they don't have transactional semantics. |

### F11 · `/run-history` empty after `/solve` POST 200

| field | value |
|---|---|
| Surface | POST /solve route called `run_icofoam()` directly; never invoked `write_run_artifacts()` from the run_history module |
| Persona symptom | curl direct E2E (DEC-V61-184) showed /solve POST 200 with run_id, but /run-history returned empty `runs:[]` |
| Root cause | Workbench was wired primarily for the M3 RealSolverDriver flow which DOES persist artifacts; the /solve direct path predates run_history infrastructure and bypasses it |
| Fix | DEC-V61-188 (B-ext-4.2) — POST /solve now calls `write_run_artifacts()` with run_id + residuals + key_quantities. SolveSummary schema gains `run_id: str | None`. Best-effort: artifact-write OSError doesn't fail the response. |
| Status | **closed** |
| Lesson | When two execution paths reach the same workbench surface, both must hit the persistence side-effects. The "internal-only" path must be audited for parity with the persona path whenever new persistence is added. |

### F12 · LDC defaults on non-cube geometry → NaN U field

| field | value |
|---|---|
| Surface | `setup_ldc_bc` hardcodes `lid_velocity=(1,0,0)`, `nu=1e-3`, `Re=100` calibrated for the unit cube tutorial; on NACA0012 / backward_step / pipe_expansion geometry, this produces a "converged" residual but a NaN U field |
| Persona symptom | persona thought solve succeeded (residuals look fine), then `/results-summary` returned 422 `results_malformed` because the U field had 1500+ NaN entries |
| Root cause | LDC defaults are physically wrong for non-cube geometry; no signal to persona that they were wrong |
| Fix | DEC-V61-189 (B-ext-4.3) two-pronged: (a) persona prompts gain Step 4 mandatory `from_stl_patches=1` guidance for non-LDC geometry; (b) workbench `BCSetupResult.warnings` field; `setup_ldc_bc` populates `ldc_geometry_mismatch` warning when bbox aspect > 3.0 |
| Status | **closed** (mitigation; LDC defaults still load if persona ignores warning) |
| Lesson | Calibrated-for-tutorial defaults need a geometry-mismatch detector. Soft warnings in the response body are sufficient for persona consumption — they don't need to be load-bearing. |

### F13 · `/solve` returns 502 Bad Gateway under stress

| field | value |
|---|---|
| Surface | R9 produced 11× /solve 502 across naca0012 + pipe_expansion; manual repro: fresh case + /setup-bc (skipping /mesh) + /solve |
| Persona symptom | generic 502 `solver_diverged` with `simpleFoam exited with code 1` and a path to `log.icoFoam` (containing the actual `Cannot find file points in directory polyMesh` FOAM error) |
| Root cause | (a) **Path-layer**: missing polyMesh slipped through the F10 `_check_mesh_bc_consistency` pre-flight, which explicitly returns None when polyMesh is absent; (b) **Stress-layer**: ephemeral OpenFOAM container leak (R9 left `compassionate_neumann` running 42 min) suggests solver-spawn race or resource pressure under sustained automation |
| Fix | DEC-V61-193 (B-ext-5.2) — partial: `_check_mesh_present()` pre-flight catches missing polyMesh BEFORE the F10 check, returns structured 409 `mesh_missing` instead of 502. **Stress-layer NOT addressed.** |
| Status | **partial** — most-visible mode (missing polyMesh) closed; race / resource pressure deferred until it recurs under sustained load |
| Lesson | A 502 in a multi-step workflow is rarely just one bug. Triage the "obvious" mode first (missing artifact pre-flight); reserve race / resource fixes for when they recur post-mitigation. |

### F14 · DeepSeek API read timeout 15.5min

| field | value |
|---|---|
| Surface | R9 backward_step persona crashed at step 20 with `llm_chat_failed: The read operation timed out` after waiting 15.5 minutes (934s) on a chat-completion response |
| Persona symptom | persona ran out of attempts on first 502, no retry, never recovered |
| Root cause | `OpenAICompatClient` used `timeout=60.0` single value; httpx applied per-phase but the read deadline measures **between bytes**, not total request time. Slow trickle of TCP keepalives kept read socket below the per-byte deadline indefinitely. |
| Fix | DEC-V61-192 (B-ext-5.1) — `_DEFAULT_TIMEOUT = httpx.Timeout(connect=10, read=180, write=30, pool=30)`; `_post_with_retry()` wraps both `OpenAICompatClient.chat()` and `AnthropicClient.chat()` with 1 retry on `(ReadTimeout/WriteTimeout/ConnectTimeout/PoolTimeout/RemoteProtocolError/ConnectError)`; HTTP 4xx/5xx pass through untouched |
| Status | **closed** |
| Lesson | Single-value `timeout=60` on `httpx.Client` is a trap — it's per-phase but read-deadline is between-byte, not total. Always use explicit `httpx.Timeout(connect=, read=, write=, pool=)` for any client expecting potentially slow upstream. |

### F15 · `/results/{run_id}/field/U` structural mismatch

| field | value |
|---|---|
| Surface | `field_sample.py::_resolve_field_path` looks for `<case_dir>/<run_id>/<name>` |
| Persona symptom | (a) Path mismatch: F11's `write_run_artifacts` puts run dirs under `reports/<case_id>/runs/<run_id>/`; OpenFOAM writes under `<case_dir>/<final_time>/` (e.g. `/2/`); neither layout intersects with `<case_dir>/<run_id>/`. (b) Scalar-only parser: `_parse_internal_scalar_field` rejects U field's `nonuniform List<vector>` with 422 `field_unsupported`. |
| Root cause | Route was wired for the M3 RealSolverDriver flow with **visualization** (colormap) consumers in mind, not for **persona-side verdict computation** that needs raw vector data |
| Fix | DEC-V61-196 (B-ext-6.1) — Layer 1: `/solve` route creates `<case_dir>/<run_id>` → `<final_time_dir>` symlink (best-effort, silent OSError fallback). Layer 2: `_parse_internal_vector_field` for `nonuniform List<vector>`; `_VECTOR_FIELD_NAMES = {U, Uavg, U.air, U.water}` dispatch; `FieldSampleResult.components_per_cell` field; route emits `X-Field-Components: {1\|3}` header. |
| Status | **closed** for U + scalar fields. **Cell centers (Cx/Cy/Cz) still need writeCellCentres post-solve hook** — escalated to B-ext-7. |
| Lesson | The same workbench surface can be wired correctly for one consumer (M3 visualization) and wrong for another (persona verdict). When opening a route for new consumer, walk the entire pipeline (write path + serve path + parse path) rather than assuming the existing wiring is consumer-agnostic. |

## Cross-cutting lessons

### Pattern 1 — "Internal-only callers mask gaps"

F11 (run-history empty), F15 (field/U serves wrong layout) both share
this shape: a workbench surface was wired correctly for an internal
M-series caller (M3 RealSolverDriver, M-VIZ visualizer) but wrong for
the persona-driven /solve direct path. The internal caller exercised
one branch of the surface; the persona caller exercised a parallel
branch that was incomplete.

**Mitigation in code:** When introducing a new persona-facing entry
point that reaches existing internal infrastructure, audit BOTH
write path and serve path for parity.

**Mitigation in process:** Run the live-fire smoke test
(`scripts/dogfood/smoke_simulation.py`) after any change to a route
that's reachable from `/solve`, `/results-summary`, `/field/{name}`,
or `/run-history`.

### Pattern 2 — "One symptom, multiple modes"

F13 (/solve 502) had at least two modes (missing polyMesh + container
race). The 502 status code conflated them. Persona couldn't tell the
modes apart, neither could initial diagnosis.

**Mitigation:** Map workbench failure modes to **distinct HTTP status
codes** wherever possible (409 for missing prereq, 503 for container
unavailable, 502 only for genuine post-stage failure).

### Pattern 3 — "Persona budget exhaustion is a code smell"

F2 (taxonomy not discoverable), F4 (openapi.json not in prompt), F6
(per-turn input bandwidth) all manifested as persona running out of
budget before reaching the verdict step. The fix was sometimes
prompt-side, sometimes harness-side, sometimes workbench-side — but
the symptom was always "persona didn't reach Step 5/6".

**Mitigation:** Track `steps_to_first_verdict_or_drop` per cell × persona
across runs. Sustained increase = budget pressure surfacing somewhere
new.

### Pattern 4 — "Each fix surfaces the next layer"

F9 fix exposed F10 (mesh-after-setup-bc); F10 fix exposed F11
(run-history empty); F11 fix exposed F12 (LDC NaN); F12 fix exposed
F13 (502 modes) + F14 (API timeout); F15 split into two layers
itself. **5 R-iterations across B-ext-2/3/4 traversed five distinct
fix surfaces with verdict pass stuck at 0/3.**

**Mitigation:** This is normal for a workflow that spans many surfaces.
The trap is treating each layer as "the last one". V133 round-cap=3
exists specifically to break the "one more iteration will fix it"
loop and force a strategy pivot (e.g. B-ext-5's 1-cell focus).

## Methodology — how to file a new finding

1. **Run `scripts/dogfood/smoke_simulation.py`** to confirm the
   failure reproduces in the live-fire path (not just in your
   debugger).
2. **Capture the symptom** in the friction log JSONL — `event_type`
   should be `error` or an unexpected `api_call` status.
3. **Open a sub-DEC** in the active arc; reference this index in the
   References section.
4. **Append to this index** with all 7 fields (Surface / Persona symptom
   / Root cause / Fix / Status / Lesson / Pattern).
5. **Update `_VECTOR_FIELD_NAMES`-style allowlists** if the finding
   adds a new field type, route, or schema variant.
6. **If status=partial**, note the deferred sub-finding name (e.g.
   "F13 stress-layer") in the Status field for future audit.

## References

- `.planning/dogfood/DOGFOOD_REPORT_LIVE.md` — original F1-F4 origin
- `.planning/dogfood/DOGFOOD_REPORT_LIVE_PROGRESSION.md` — F5-F7
- `.planning/decisions/2026-05-07_v61_175_b_ext_close.md` — F8 origin (later reframed)
- `.planning/decisions/2026-05-07_v61_180..183_*.md` — F9 + F10 fix arc
- `.planning/decisions/2026-05-07_v61_188..189_*.md` — F11 + F12 fix arc
- `.planning/decisions/2026-05-07_v61_192..193_*.md` — F13 partial + F14 fix
- `.planning/decisions/2026-05-07_v61_196_*.md` — F15 fix
- `scripts/dogfood/smoke_simulation.py` — live-fire smoke (P2)
