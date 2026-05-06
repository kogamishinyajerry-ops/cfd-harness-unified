---
decision_id: DEC-V61-132
dec_id: V61-132
title: N1.2 · MUTATING_ROUTES registry + behavioral sentinel test + pre-commit grep lint
status: Proposed (drafted 2026-05-06 · awaiting Codex APPROVE + Kogami clearance)
parent_dec: V61-130
parent_artifacts:
  - .planning/decisions/2026-05-06_v61_130_strategic_pivot_ai_advisor.md
  - .planning/decisions/2026-05-06_v61_131_envelope_hard_strip_regenerate_mesh_deprecate.md
  - ui/backend/services/ai_actions/__init__.py
  - ui/backend/services/llm_coach/tool_registry.py
  - ui/backend/routes/ai_chat.py
  - ui/backend/routes/ai_coach.py
  - .pre-commit-config.yaml
phase: N1 (workbench-first / AI is advisor) · sub-DEC 1.2
trigger: V130 charter §4 N1.2 — Kogami P1 finding #3 close (grep alone is brittle for a load-bearing contract; behavioral test is the merge gate)
autonomous_governance: true
counter_impact: +1
counter_value_after: 29 (V131=28)
codex_review_relay: 86gs (xhigh) primary; CRS (high) fallback if 86gs 503
kogami_review_path: .planning/reviews/kogami/v61_132_n1_2_mutating_routes_2026-05-06/ (to be created on draft commit)
notion_sync_status: pending (session-end batch)
confidence: med
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-06
---

# DEC-V61-132 · N1.2 · MUTATING_ROUTES registry + behavioral contract

## 1. Goal

Make V130 Principle B ("AI is advisor, not actor") **load-bearing at the
test layer**, not just the implementation layer.

V131 stripped two AI dispatch paths (envelope mode, `regenerate_mesh`
tool) of their mutation calls. That removed the *current* violations.
N1.2 prevents the *next* violation: a future engineer wires a new AI
path (an advisory route, a new tool handler, an LLM-driven feature) and
unintentionally adds a mutation call.

Two enforcement layers, per V130 §4 N1.2:

1. **MUTATING_ROUTES registry** — single SSOT module listing every
   case-mutating endpoint. Future endpoints added to this set become
   automatically covered without touching tests.
2. **Behavioral sentinel test** — instantiates AI dispatch handlers
   with a sentinel HTTP/route client recording every outbound call;
   asserts the call set is GET-only AND no path matches MUTATING_ROUTES.
   This is the **merge gate** — failure blocks merge.

A third advisory layer (grep lint pre-commit hook) is wired but is
**warning-only**, not a merge gate. Brittle string matching is unsuitable
for load-bearing contract enforcement (per Kogami P1 #3 close); the
behavioral test is the truth source.

## 2. Scope

### 2.1 In scope (R0)

**MUTATING_ROUTES registry module** — new file
`ui/backend/services/ai_actions/mutating_routes.py`:

- `MUTATING_ROUTES: frozenset[tuple[str, str]]` — HTTP-surface SSOT.
  Initial contents (per V130 §2 Principle B):
  - `("POST", "/api/import/{case_id}/mesh")` — meshImported
  - `("POST", "/api/import/{case_id}/setup-bc")` — setupBC (envelope and non-envelope alike, both routes mutate)
  - `("PUT", "/api/cases/{case_id}/face-annotations")` — face_annotations writer
  - `("POST", "/api/cases/{case_id}/dicts")` — dict mutator
  - `("POST", "/api/cases/{case_id}/run")` — solver kick
- `KNOWN_MUTATION_FUNCTIONS: frozenset[tuple[str, str]]` — Python-symbol
  SSOT (the layer that the behavioral test actually polices, given AI
  dispatch is in-process). `(module_path, symbol_name)` pairs:
  - `("ui.backend.services.case_solve", "setup_ldc_bc")`
  - `("ui.backend.services.case_solve", "setup_channel_bc")`
  - `("ui.backend.services.mesh_import", "mesh_imported_case")`
  - any future case-mutation function added by a downstream DEC.
- Helpers:
  - `is_mutating_route(method: str, path: str) -> bool` — normalizes
    case_id segments and matches against MUTATING_ROUTES.
  - `iter_mutation_symbols() -> Iterator[tuple[str, str]]` — used by
    the static namespace-binding test (Layer-C).
- Module docstring cross-references V130 §2 Principle B and V132 (this
  DEC). New registry entries MUST cite the upstream DEC adding the
  endpoint or function.
- `__all__ = ["MUTATING_ROUTES", "KNOWN_MUTATION_FUNCTIONS", "is_mutating_route", "iter_mutation_symbols"]`.

**Behavioral sentinel test** — new file
`tests/test_ai_advisor_contract.py`:

**Architectural correction**: V130 §4 N1.2 originally specified a "sentinel
HTTP client" — but AI dispatch in this codebase is **in-process Python
function calls** (`setup_ldc_bc`, `setup_channel_bc`, `mesh_imported_case`),
not outbound HTTP. There is no `httpx`/`requests` use in
`services/ai_actions/` or `services/llm_coach/`. The HTTP-client sentinel
would capture nothing.

R0 implements the equivalent enforcement at the actual dispatch layer:
**known-mutation-function patching + FastAPI route-level case-state diff**.

Layer-A · Patched-function sentinel (in-process Python dispatch):
- `_MutationSentinel` is a dataclass holding `(name, args, kwargs)` records.
- A `pytest` fixture monkey-patches the known mutation symbols
  (`setup_ldc_bc`, `setup_channel_bc`, `mesh_imported_case`, plus any
  symbol added to a `KNOWN_MUTATION_FUNCTIONS` registry — see §3.1) at
  their import sites within AI dispatch modules with a sentinel that
  appends to the record list AND raises `_MutationViolation`.
- Tests run AI dispatch entrypoints across their full branch matrix:
  - `test_envelope_no_mutation_*`: confident / uncertain / blocked /
    force_blocked / force_uncertain (5 cases) of
    `setup_bc_with_annotations`.
  - `test_tool_registry_no_mutation_*`: every tool in `list_tools()`,
    parametrized — fails if any handler invokes a sentinel symbol.

Layer-B · FastAPI route-level case-state diff (HTTP boundary, for routes):
- **Scope-down decision (2026-05-06)**: Layer-B in its full form
  (TestClient hitting `/ai-chat` / `/ai-coach/stream` /
  `/ai-coach/apply-proposal` with case-tree byte-identity diffs)
  requires LLM mocking + real case fixture + async streaming-route
  test plumbing. R0 ships only registry-validation smoke tests
  (`test_known_mutating_routes_set_is_non_empty`,
  `test_is_mutating_route_normalizes_case_id_segments`) that exercise
  `MUTATING_ROUTES` + `is_mutating_route()` correctness without
  invoking routes.
- **Deferred to N1.3 (DEC-V61-133)**: full FastAPI route-level
  case-state diff. Rationale: Layer-A patches the mutation symbols
  at module load, so any AI route that calls a known mutation
  function still triggers the sentinel — Layer-A indirectly covers
  symbol-call route attacks. The unique value of full Layer-B is
  catching novel attack vectors (a future AI route writing files via
  subprocess, raw `pathlib.write_text`, etc.) — that's a real but
  low-likelihood class given V131's strip + Layer-C's import-graph
  guard. Defer is acceptable for R0; V133 promotes it when the
  TestClient + LLM mock plumbing is ready.

Layer-C · Static namespace-binding check (defense in depth):
- For each AI dispatch module file (`services/ai_actions/__init__.py`,
  `services/ai_actions/classifier/__init__.py`,
  `services/llm_coach/tool_registry.py`, `routes/ai_chat.py`,
  `routes/ai_coach.py`), assert via `ast.parse` that no module-level
  `import` or `from ... import` statement names a symbol in
  `KNOWN_MUTATION_FUNCTIONS`. Bound-but-unused is treated as same risk
  class as called-once because the next code edit can flip bound to called.
- This is implemented as a single test
  `test_ai_modules_do_not_import_mutation_functions` iterating the
  AI module file list.

**Pre-commit grep lint hook** — added to `.pre-commit-config.yaml`:

- New `local` hook `ai-path-mutation-grep` running
  `scripts/governance/check_ai_path_mutations.sh` on staged files
  matching `^ui/backend/services/(ai_actions|llm_coach)/` or
  `^ui/backend/routes/ai_.*\.py$`.
- Script string-matches for: `requests.post`, `requests.put`,
  `requests.delete`, `client.post`, `client.put`, `client.delete`,
  `\.meshImported(`, `\.setupBC(`, `mesh_imported_case(`,
  `setup_ldc_bc(`, `setup_channel_bc(`.
- Match found → hook prints `[ai-path-mutation-grep] WARNING: ...` and
  exits **0** (warning-only, not blocking). Rationale: false-positives
  (e.g., a doc comment quoting the symbol) are unacceptable on a merge
  gate; behavioral test is the gate. Grep is the fast warning layer.

### 2.2 Out of scope (deferred)

- **AI-path import cleanliness static analyzer** — V130 §4 N1.2
  mentions a `scripts/governance/check_ai_path_imports.py` static
  analyzer of the import graph. Defer to N1.3 (DEC-V61-133) per Kogami
  P3 finding "ship enforcement incrementally"; the behavioral test in
  R0 already catches calls; the import-graph rule is a stronger but
  more brittle layer.
- **Pre-merge CI integration** — the behavioral test runs in the
  existing `pytest` invocation; no new CI workflow file. Adding the
  test to a dedicated job is N1.3 territory.
- **Frontend-side advisor contract** — the frontend already calls
  legacy non-envelope routes for mutation per V131 §3.1. A frontend
  contract test is not in V130's scope; charter §3.5 covers it via
  human review at PR time.

## 3. Contract specification

### 3.1 MUTATING_ROUTES SSOT discipline

The set is closed-by-default. Adding a new mutation endpoint requires:

1. Add the `(method, path_pattern)` pair to `MUTATING_ROUTES`.
2. Cite the upstream DEC in the module docstring's change log section.
3. The behavioral sentinel test re-runs with the expanded set; if any
   AI path was already calling the new endpoint, the test fails and
   blocks merge until the violation is resolved.

This means: registry entries are append-only modulo deprecation. A
deprecated endpoint is removed by deleting the entry **and** the route
handler in the same commit; the behavioral test's assertion that AI
paths don't hit the path becomes vacuously true.

### 3.2 Behavioral test gate semantics

The test is **the** merge gate, equal in weight to the existing
`test_*_envelope_route.py` and `test_*_tool_registry.py` suites.
Failure semantics:

- Layer-A patched-function sentinel raised → test fails with the
  symbol name + args/kwargs for triage. Means an AI dispatch path
  invoked a known mutation function.
- Layer-B case-state diff non-empty → test fails with the diff
  (changed file path + before/after sha256). Means an AI route caused
  on-disk mutation regardless of the symbol path used (catches future
  HTTP-based mutation, subprocess-based mutation, etc.).
- Layer-C namespace binding found → test fails with module + symbol
  name. Means an AI dispatch module imports a mutation function (even
  if not called yet); same risk class as called-once because the next
  code edit can flip bound to called.

### 3.3 Grep lint warning semantics

The hook runs on `pre-commit run --all-files` (CI integration via
existing pre-commit workflow) and on local commits. Match → human
notice; the hook does NOT exit non-zero.

Rationale: a doc comment that legitimately quotes `mesh_imported_case(`
in a deprecation note (V131-style) should not block a commit. The
warning is for fast feedback ("you may have wired a mutation"); the
behavioral test is the actual gate.

## 4. Verification

R0 checklist:

- [ ] New `mutating_routes.py` module exists with all 5 initial entries
      + `is_mutating_route` helper + `__all__`.
- [ ] `tests/test_ai_advisor_contract.py` runs green; covers all 4
      dispatch entrypoints listed in §2.1.
- [ ] Behavioral test FAILS when intentionally regressed: temporarily
      re-add a `setup_ldc_bc` call to `setup_bc_with_annotations`
      confident branch, run pytest, observe failure with captured
      payload. Revert. (This is the falsifiability check per V130 §2
      Principle A "concrete capability lists are falsifiable".)
- [ ] Pre-commit grep lint emits warning when a staged file under
      `ui/backend/services/ai_actions/` contains `mesh_imported_case(`;
      exits 0; commit succeeds.
- [ ] Existing pytest suite green (no regression).
- [ ] Existing pre-commit hooks (import-linter, codex-cadence) still
      pass.
- [ ] V131 contract still holds: envelope confident no longer mutates
      (test_setup_bc_envelope_route.py green).

## 5. Predicted Codex rounds

V123 §L1 calibration: contract change touching new module + behavioral
test + pre-commit hook. Three surfaces, all narrow.

Predict **3-4 rounds** to APPROVE:
- R0: initial draft. Likely findings around `path_pattern` matching
  semantics (case_id normalization), test sentinel completeness
  (which `httpx.Client` methods does it stub?), grep regex robustness.
- R1-R2: close P1 + P2 from R0/R1.
- R3: branch-level review confirming closure; APPROVE.

Lower bound 3 because the scope is tight and well-specified; upper
bound 4 if Codex flags any subtle test-framework interaction (e.g.,
fixture hierarchy, sentinel client thread-safety).

Confidence per CLAUDE.md v2.2: **med** — backend governance enforcement
is not routine, but scope is narrow and the V131 baseline gives clean
test fixtures to extend.

## 6. Risks

- **Layer-A symbol-list staleness**: `KNOWN_MUTATION_FUNCTIONS` lists
  symbols by import path. If the next mutation function gets added
  but isn't registered in this set, Layer-A passes vacuously.
  Mitigation: Layer-B (case-state diff) catches it operationally — any
  on-disk mutation flunks the byte-identity check regardless of the
  function name used. Layer-A is fast feedback; Layer-B is the
  belt-and-suspenders. New mutation functions added by future DECs
  MUST update `KNOWN_MUTATION_FUNCTIONS` in the same commit; the V133
  ROADMAP addendum (planned) calls this out explicitly.
- **Layer-B fixture brittleness**: case-state diff requires a
  representative case fixture per test. If a fixture is malformed or
  the AI route legitimately reads files (mtime updates), false
  positives kick in. Mitigation: fixture uses `os.walk` + content
  sha256 (not mtime), so read-only access doesn't flag. Read-without-
  write is permitted by V130 Principle B; only write violates.
- **Path normalization edge cases**: `{case_id}` placeholder matching
  must handle UUIDs, hex IDs, and any future case-id schema. R0 uses
  a regex `[0-9a-fA-F-]+` for case_id segments; future case-id schemas
  not matching this pattern require registry entries with explicit
  alternative placeholders.
- **Grep false positives in code comments**: V131 commit messages and
  source docstrings legitimately reference `setup_ldc_bc(` etc. The
  warning-only semantics handle this; the human evaluates each
  warning. If false-positive volume becomes annoying (>1/week), N1.3
  can refactor to AST-based matching.
- **Future AI path bypassing the test**: if a downstream DEC adds an
  AI dispatch entrypoint not listed in the test's coverage map, the
  new entrypoint is policed by the grep lint warning (advisory) but
  not the behavioral test (gate) until the test's parametrization is
  extended. Mitigation: V133 (planned) adds an `AI_DISPATCH_ENTRYPOINTS`
  registry that the behavioral test iterates, making coverage
  declarative. R0 hardcodes the 4 entrypoints.

## 7. Decision

**R0 (this commit)**: registry module + behavioral sentinel test + grep
lint hook + falsifiability check (intentional regression run during
verification). Push for Codex review on 86gs gpt-5.4 xhigh. On APPROVE,
advance to Accepted; trigger Kogami review (governance contract
implementation = high-risk PR per project CLAUDE.md three-layer
governance).

On Kogami APPROVE_WITH_COMMENTS or APPROVE: advance to N2.

## 8. Surface-scan (per DEC-V61-088)

ROADMAP scan: matches V130 §4 N1.2; current ROADMAP.md does not
predate this DEC's spec.

Existing-implementation grep:
- `mutating_routes`: no matches in `ui/backend/services/`
  (new file, no collision).
- `_RecordingHTTPClient`: no matches anywhere (new test class).
- `check_ai_path_mutations.sh`: `scripts/governance/` does not have it
  (new file).
- `ai-path-mutation-grep` pre-commit hook id: not present in
  `.pre-commit-config.yaml`.

Disposition: **clean** — all new files; surface-scan trailer will
read `Surface-scan: clean` on R0 commit.
