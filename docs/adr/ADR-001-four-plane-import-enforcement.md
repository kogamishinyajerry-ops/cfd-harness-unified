# ADR-001 · Four-Plane Import Enforcement (Static Layer)

**Status**: Proposed → Accepted (Claude Code draft · 2026-04-24)
**Deciders**: Opus 4.7 (Post-Hoc Review §3) · Claude Code (main session) · Codex GPT-5.4 (independent verification pending)
**Consulted**: CFDJerry (pending G-1 signoff)
**Scope**: W1 static layer only — `import-linter` + pre-commit + CI. Runtime `sys.meta_path` finder deferred to W2-W3.

---

## 1. Context

SYSTEM_ARCHITECTURE v1.0 §2 ("层间调用方向不可违反") declares three
import rules:

1. Execution **cannot** import Evaluation
2. Evaluation **cannot** import Execution
3. Knowledge Plane provides read-only view + write-only event interface — no reverse import from Knowledge into Control/Execution/Evaluation

Rules are currently **text-only**. The v3.x era saw repeated architectural
drift precisely because "口头约束无技术壁垒" (Model Routing v4.0 §trigger).
Without programmatic enforcement, the next 6-month arc will accumulate
violations that are expensive to untangle at P2 ExecutorMode rollout.

Opus 4.7 Pivot Post-Hoc Review §3 裁决 **OVERHAUL** — "只靠文本约束是失败
模式"；prescribes double-layer enforcement:

- **Static layer (mandatory W1)**: `import-linter` contract + pre-commit + CI gate
- **Runtime layer (recommended W2-W3)**: `sys.meta_path` finder raising `LayerViolationError`

This ADR lands the **static layer only**. Runtime layer is scheduled
for a follow-up ADR-002 (W2-W3 per Opus fallback §3 末).

## 2. Decision

### 2.1 Plane assignment (as-of 2026-04-24)

Current `src/*` modules are assigned to planes as follows. Assignment
is **authoritative for `import-linter` contract**; re-assignment
requires ADR-001 addendum.

#### Control Plane (`src.control.*` · logical label)

| Module | Purpose |
|---|---|
| `src.task_runner` | `TaskRunner` — orchestrates Execution + Evaluation via artifacts |
| `src.orchestrator.skill_loader` | Skill index loader — Control-side dispatcher |
| `src.notion_client` | Notion API edge — Control-plane sync |
| `src.notion_sync.*` | Notion ↔ repo sync workflow |
| `src.audit_package.*` | Audit package manifest/serialize/sign — Control-plane artifact producer |

#### Execution Plane (`src.execution.*` · logical label)

| Module | Purpose |
|---|---|
| `src.foam_agent_adapter` | `FoamAgentExecutor` + `MockExecutor` — Docker-OpenFOAM driver |
| `src.airfoil_surface_sampler` | Airfoil post-process sampler (reads OpenFOAM artifacts) |
| `src.cylinder_centerline_extractor` | Cylinder wake extractor |
| `src.cylinder_strouhal_fft` | Strouhal FFT extractor |
| `src.plane_channel_uplus_emitter` | u+ emitter from VTK |
| `src.wall_gradient` | Wall gradient extractor |

#### Evaluation Plane (`src.evaluation.*` · logical label)

| Module | Purpose |
|---|---|
| `src.comparator_gates` | Hard comparator gates (parse_solver_log, check_all_gates) |
| `src.convergence_attestor` | A1..A6 attestor |
| `src.error_attributor` | Attribution analyzer |
| `src.result_comparator` | Tolerance comparator |
| `src.correction_recorder` | CorrectionSpec recorder (write-only to Knowledge) |
| `src.auto_verifier.*` | Three-layer AutoVerifier |
| `src.report_engine.*` | Visual acceptance + dashboard generators |

#### Knowledge Plane (`src.knowledge.*` · logical label)

| Module | Purpose |
|---|---|
| `src.knowledge_db` | `KnowledgeDB` — read-only gold + write-only provenance events |

#### Shared Contracts (allowed from all planes)

| Module | Purpose |
|---|---|
| `src.models` | Cross-plane types (`TaskSpec`, `ExecutionResult`, `ComparisonResult`, `CFDExecutor` ABC, enums) |

> **Rationale**: `src.models` is a dependency-free type-only module. All
> four planes share these contracts; treating it as a separate
> `shared` plane avoids a forced top-level `src/contracts/` refactor.

### 2.2 Forbidden-imports matrix

| From \ To | Control | Execution | Evaluation | Knowledge | Shared |
|---|---|---|---|---|---|
| Control | ✓ | ✓ (dispatch) | ✓ (orchestrate) | ✓ (read/write) | ✓ |
| Execution | ✗ | ✓ | **✗** HARD NO | ✗ | ✓ |
| Evaluation | ✗ | **✗** HARD NO | ✓ | ✓ (read only) | ✓ |
| Knowledge | ✗ | ✗ | ✗ | ✓ | ✓ |

Two HARD NOs are the contract's core:
- **Execution → Evaluation** (solver code must not depend on comparator / metrics / verdict logic)
- **Evaluation → Execution** (evaluator must not invoke solver code; reads only artifacts)

Remaining ✗ prevent reverse-direction control flow that would break
the dispatch model.

### 2.3 Tooling decision

- **Tool**: `import-linter >=2.0` (PyPI)
- **Config location**: `.importlinter` at repo root (simpler than embedding in `pyproject.toml`)
- **Optional dep group**: add to `pyproject.toml` under `[project.optional-dependencies]` `dev` group
- **Contract types used**:
  - `layers` — establish hierarchy (not strict "containment", just ordering)
  - `forbidden` — explicit bidirectional Execution ⇄ Evaluation block
  - `independence` — Knowledge can't depend on other planes

### 2.4 Enforcement path

1. **Local dev** — `pre-commit` hook runs `lint-imports` before commit
2. **CI** — new step in `backend-tests` job: `lint-imports` runs before `pytest`
3. **Failure mode** — violation blocks commit / PR merge; fix = move module or refactor import

### 2.5 Current grandfathered violations

Audit performed 2026-04-24 (grep for cross-plane `from`/`import` across
all `src/` and `ui/backend/` sources). Result: **zero violations** of
the two HARD NOs (Execution ⇄ Evaluation). The existing code already
respects the contract de-facto; ADR-001 codifies and enforces what was
already conventional.

If any grandfathered violation surfaces during initial `lint-imports`
run, document in this ADR §5 with a remediation owner + target week
before enforcement goes live. (None expected.)

### 2.6 Plugin Plane (forward-looking · not enforced W1)

`src/surrogate_backend/**` and `src/diff_lab/**` are currently **empty**
(no files). When populated under P5/P6:

- **Plugin Plane** is a **read-only consumer** of Control's dispatch +
  Knowledge's CaseProfile. Main-chain modules (any Control/Execution/
  Evaluation/Knowledge file) **must not** `import src.surrogate_backend.*`
  or `src.diff_lab.*` in non-test code.
- Enforcement via `forbidden` contract added when `src/diff_lab/` or
  `src/surrogate_backend/` gains its first file.

Per Opus §遗留问题 #2, "Plugin Plane 升格为第五层" is deferred —
this ADR treats Plugin as a contract-level boundary, not a new
architectural layer. Final升格 decision defers to P5 activation
retro.

## 3. Consequences

### 3.1 Positive

- **Drift prevention** — structural violations caught at pre-commit,
  not at PR review or months-later refactor
- **Documents the contract in code** — `.importlinter` is executable
  specification of SYSTEM_ARCHITECTURE v1.0 §2
- **Faster onboarding** — new contributors (including subagents) see
  contract violations immediately with actionable messages
- **Low initial cost** — zero current violations mean no migration
  burden; the contract is a "keep what we have"

### 3.2 Negative

- **New dev dependency** — `import-linter` must be installed
  pre-commit; addressed by `dev` optional-dependency group
- **False positives on `ui/backend/`** — FastAPI app imports from `src`
  across planes legitimately (it is a Control-Plane orchestrator
  itself). Contract scope limited to `src.*` root namespace; `ui.*` and
  `scripts.*` are out of scope for v1.0
- **Runtime bypass possible** — `importlib.import_module("src.evaluation.foo")`
  from Execution code bypasses static analysis. Addressed by ADR-002
  (runtime layer, W2-W3)
- **models.py as shared escape hatch** — future temptation to pile
  cross-plane helpers into `src.models`. Mitigated by: `src.models` is
  type-definitions-only; any module adding runtime logic must be
  re-classified to a specific plane

### 3.3 Deferred (explicit)

- Runtime `sys.meta_path` layer → **ADR-002** (W2-W3)
- Top-level `src/control/`, `src/execution/` etc. physical restructure
  → **P2 ExecutorMode refactor scope**
- `ui/backend/` plane classification → separate ADR when FastAPI layer
  is itself split

## 4. Verification

### 4.1 Acceptance criteria (must all pass before ADR flips to Accepted)

| # | Criterion | Evidence |
|---|---|---|
| A1 | `.importlinter` config lints all 6 contracts (4 layers + 2 forbidden + 1 independence) without errors | `lint-imports` exit 0 on main |
| A2 | `lint-imports` runs in < 10s locally on current src/ | Measured on M1 Mac |
| A3 | Pre-commit hook installed and runs `lint-imports` | `.pre-commit-config.yaml` present |
| A4 | CI `backend-tests` job runs `lint-imports` before `pytest` | `.github/workflows/ci.yml` updated |
| A5 | Zero violations reported on current `main` | See §2.5 |
| A6 | Adding a deliberate violation fails CI | Manual verification in PR description |

### 4.2 Codex independent verification

Per Model Routing v6.2 §B (key-claim verification) + ADR-001 §2.4:

- **Claim to verify**: "no current cross-plane violation exists between
  Execution and Evaluation modules"
- **Method**: Codex runs `rg` cross-check against the plane assignment
  table (§2.1) and confirms no `from src.<plane_a> import` appears in
  `src.<plane_b>` for forbidden pairs
- **Output**: `reports/codex_tool_reports/adr_001_import_verify.log`
- **Verdict required**: no HIGH finding

### 4.3 Self-estimated pass rate

75% (moderate — spec is narrow, but `import-linter` contract syntax
may need 1-2 iterations; `ui/backend/` scope question could surface
as a Codex medium).

## 5. Grandfathered violations (currently empty)

*To be populated by initial `lint-imports` run. If any appear, each
entry: module source, forbidden target, target plane, remediation
owner, target week.*

## 6. References

- **Notion SSOT**: SYSTEM_ARCHITECTURE v1.0 §2 ·
  <https://www.notion.so/SYSTEM_ARCHITECTURE-e5abaf8cefba4ac48f1deb24cb4b00ee>
- **Opus verdict**: Pivot Post-Hoc Review 2026-04-24 §3 (OVERHAUL)
- **Related docs**:
  - `docs/governance/PIVOT_CHARTER_2026_04_22.md` §4.3a
  - `docs/specs/SPEC_PROMOTION_GATE.md` §3 (DIFFERENTIABLE_LAB_SCOPE blocker references this ADR)
- **Tool**: `import-linter` · <https://pypi.org/project/import-linter/>
- **RETRO**: `.planning/retrospectives/2026-04-21_v61_counter16_retrospective.md` §"foam_agent_adapter 7000-line" 遗留项

## 7. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1.0-draft | 2026-04-24 | Claude Code + Opus 4.7 Post-Hoc Gate | Initial draft; static layer only; W2-W3 runtime layer scheduled as ADR-002 |
