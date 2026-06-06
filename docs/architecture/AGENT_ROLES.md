# Agent Roles — the multi-agent division-of-labor system (honest SSOT)

> **Positioning**: cfd-harness-unified is a *multi-role agentic system* for CFD validation —
> a fleet of single-responsibility roles, each owning exactly one job and handing a typed
> artifact to the next. It **reads like a coordinated agent team because it is one** — but
> every consequential decision is made by **deterministic rules**, and the AI is kept in
> the **passenger seat by construction** (advisor-not-driver). *The intelligence is in the
> contract, not in any model.*
>
> This doc is the human-readable SSOT. The honesty invariants below are **machine-enforced**:
> - role-class fence → `tests/architecture/test_role_taxonomy.py`
> - import-plane law → `src/_plane_assignment.py` (`PLANE_OF`) + `src/_plane_guard.py` + `.importlinter`
>
> Grounded in a read-only architecture audit (2026-06-06, AST-verified). Last verified HEAD: see git.

---

## 1. Three role classes (the honesty axis)

Every node is one of three classes. **Do not conflate them** — that conflation is the #1
way this system gets mis-described.

| Class | Count | What it is | May it use an LLM? | May it change a verdict? |
|---|---|---|---|---|
| **Deterministic** | ~24 | Executes the case, computes metrics, **decides the verdict**, signs the bundle. if/else, thresholds, relative-error, worst-wins, HMAC. | **No** (enforced) | Yes — by deterministic rule |
| **Read-only advisor** | ~8 | Annotates evidence, suggests corrections/findings. Receives dict copies. | Yes (DeepSeek) **or** rule-based fallback | **No** — never gates/mutates |
| **Agentic (dogfood)** | ~5 LLM surfaces | Genuine autonomous tool-use LLM personas — a **test harness**. | Yes (real) | **No** — off the production solve path |
| *(aspirational)* | ~4 | Skeleton modes (`MODE_NOT_*`), not yet wired. | — | — |

---

## 2. Deterministic spine (execute → decide → sign · zero LLM)

The deterministic backbone, mapped onto the import-plane law (`PLANE_OF`):

| Role | Plane | Source |
|---|---|---|
| 🪢 工头 TaskRunner (fixed 8-step orchestration) | CONTROL | `src/task_runner.py:433 run_task` |
| 🐳 求解执行器 FoamAgentExecutor (Docker OpenFOAM; **not** an LLM — "Foam-Agent" is the external CFD tool) | EXECUTION | `src/foam_agent_adapter.py` |
| executor backends (mock / docker_openfoam / hybrid_init) | EXECUTION | `src/executor/` |
| field/QoI extractors (airfoil, cylinder, cht, channel, wall_gradient, dhc) | EXECUTION | `src/*_extractor*.py`, `src/wall_gradient.py` |
| 📉 收敛背书员 convergence attestor (A1–A6) | EVALUATION | `src/convergence_attestor.py` |
| ⚖️ 结果比对员 ResultComparator + comparator gates | EVALUATION | `src/result_comparator.py`, `src/comparator_gates.py` |
| 🔬 三查验收官 AutoVerifier (report-only, never gates) | EVALUATION | `src/auto_verifier/` |
| 🏛️ 信任脊柱 worst-wins reducer + mode ceilings | EVALUATION | `src/metrics/trust_gate.py` |
| error attributor / correction recorder | EVALUATION | `src/error_attributor.py`, `src/correction_recorder.py` |
| 🚪 六道契约门 TrustGate 6-gate (cfdtrust) | (verdict plane) | `ui/backend/audit/cfdtrust/audit/report.py` |
| 🔏 签名封存 audit_package (byte-reproducible + HMAC) | CONTROL | `src/audit_package/` |
| knowledge DB / notion sync | KNOWLEDGE / CONTROL | `src/knowledge_db/`, `src/notion_sync/` |
| import-law SSOT + runtime guard | BOOTSTRAP | `src/_plane_assignment.py`, `src/_plane_guard.py` |

**Enforced invariant**: none of the 92 solve-plane files (`src/` + `ui/backend/audit/cfdtrust/`
+ `ui/backend/audit/tools/`) imports any LLM surface. See `test_role_taxonomy.py`
(`test_solve_plane_has_zero_llm_imports`, AST-based, with a non-vacuous control assertion).

---

## 3. Read-only advisors (suggest · never decide)

AI participates **only** as a read-only advisor. The advisor stack and the V9 commentary
layer annotate evidence and suggest corrections — but they never change a verdict, never
gate a signature, and never touch a case directory.

| Advisor surface | Source | Note |
|---|---|---|
| 🔎 advisor_stack (11 domain advisors) | `ui/backend/services/advisor_stack.py` | dict-consumer dispatch; see `ADVISOR_COVERAGE.md` |
| 💡 CorrectionSuggester (template, suggest-only) | `src/auto_verifier/correction_suggester.py` | never auto-applies |
| 📝 V9 commentary (frozen rule predicates, **no LLM**) | `ui/backend/services/v9_advisor/` | annotates signed bundle, no gating |
| 🤖 production DeepSeek advisor (ai_advisor/ai_chat/ai_coach/ai_review/ai_diagnose) | `ui/backend/services/ai_advisor/`, `ui/backend/routes/ai_*.py` | **real LLM**, advisory-only; rule-based fallback when `DEEPSEEK_API_KEY` unset |

> **Honest nuance — the one human-gated mutation path.** `POST /api/ai-coach/apply-proposal`
> (`ui/backend/routes/ai_coach.py:474`) is the *only* place an LLM-originated proposal can
> become a real case-directory mutation. It is **not autonomous**: the LLM *proposes*, a
> human must explicitly **Accept**, and then a deterministic dispatcher (`dispatch_tool` +
> `write_audit`) applies what the human approved. advisor-proposes → human-decides →
> deterministic-code-applies. Still advisor-not-driver; the gate is the human, in code.

---

## 4. Agentic tier (genuine autonomous LLM — but a fenced-off test harness)

The **only** genuine autonomous LLM agents live in the dogfood harness — real tool-use
personas (Sonnet 4.6 / DeepSeek V4 Pro / gpt-5.4) driving a workbench over HTTP. They are:

- **off the production solve path** — `src/` and `ui/backend/` never import `scripts.dogfood`
  (enforced by `test_agentic_dogfood_harness_not_imported_by_production`);
- **dry-run by default** — `--live` is opt-in; default substitutes a scripted mock + mock transport;
- **graded deterministically** — a frozen literature-referenced value ± tolerance
  (`check_verdict`), **not** LLM self-assessment;
- **Opus-forbidden** — `assert_non_opus()` blocks any `opus` model (anti echo-chamber).

Source: `scripts/dogfood/` (`orchestrate.py`, `harness.py`, `llm_clients.py`). See its README banner.

---

## 5. Why the AI cannot reach the driver's seat (enforced, not promised)

1. **Import-plane law** — `PLANE_OF` declares each module's plane; `.importlinter` (static) +
   `_plane_guard` (runtime `sys.meta_path`) reject illegal inter-plane imports. *EVALUATION
   code physically cannot import EXECUTION code.*
2. **Role-class fence** (this milestone) — `test_role_taxonomy.py` adds the missing assertion
   that the **solve/verdict plane imports zero LLM**, with a control proving the boundary is real.
3. **worst-wins + honesty demotion** — every verdict flows through monotone-down-only reducers;
   a mocked / un-witnessed run can structurally never launder itself into a PASS.
4. **byte-reproducible + HMAC signature** — fail-closed; the same case re-runs byte-identical.

---

## 6. Honest gaps (NOT yet) + optimization roadmap

See `.demo/AGENT_SYSTEM_MAP.md` §4–§5 for the full list. In brief: orchestration is a static
fixed sequence (not adaptive); correction is suggest-only (no closed auto-loop); two parallel
worst-wins reducers coexist (P1 unify, DEC); `FoamAgentExecutor` name is misleading (P1 rename,
DEC); AutoVerifier is frozen to 10 anchor cases. **Optimization principle: honestly strengthen
the real division of labor — never fabricate autonomy.**
