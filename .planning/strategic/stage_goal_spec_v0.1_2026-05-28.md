# Stage Goal Spec v0.1 — lifecycle overlay on Blueprint v4 · 2026-05-28

> **Status**: DRAFT overlay (pending session-end ratification stamp — sub-DEC pointer or DEC-V61-207 addendum).
> **Author**: cfd-chief-engineer (Opus 4.7, L2).
> **Parent / SSOT**: `blueprint_v4_2026-05-27.md` (DEC-V61-207). This is an **overlay**, not a replacement.
> **Triggered by**: user-provided "AI CFD Goal-Stack" 9-stage lifecycle framework (2026-05-28), adopted as **overlay** (user choice, this session).
> **Conflict rule**: top-level `~/CLAUDE.md` > Blueprint v4 > **this overlay** > roadmap > individual DEC. Where this doc and Blueprint v4 disagree, Blueprint v4 wins.

---

## 0. What this is — and is NOT

**IS**: a single honest map from the framework's "AI CFD engineering organization" **9-stage lifecycle** onto this project's *real* artifacts, drawing the **advisor-not-driver constitutional boundary**, and adding a per-stage **Non-goal / Exit-Gate / Failure-Signal** discipline for the stages that are active or next.

**IS NOT**:
- A new SSOT. Blueprint v4's North Star, three laws, 4-region UI, and four-question gate stand unchanged.
- A re-derivation of philosophy already written (blueprint v4 §0–§7 holds it). This overlay *points*, it does not duplicate.
- A pivot. AI-advisor-not-driver (DEC-V61-130/132) is untouched.
- A Goal Book with 15 chapters. That would be the exact theater RETRO-2026-05-28 finding-5 warns against (process-completion masquerading as value).

The framework's core thesis — *goal is architecture; benchmark adjudicates; agents execute; memory accumulates; human decides the forks* — is **adopted**. The 9-stage scaffold is **mapped, not imported wholesale**, because two of its stages are constitutionally forbidden here (§1) and most of the rest already exist (§2).

---

## 1. The one fork the framework forces — and the ruling

The framework's **Stage 4 (受控修复闭环 / controlled repair)** and **Stage 8 (自动生成 case / case generation)** describe an **AI-as-operator**: AI proposes patches, mutates the case, re-runs, and generates new case files. This project made a deliberate, load-bearing strategic turn to **AI-as-advisor-not-driver** (DEC-V61-130, DEC-V61-132; enforced by `MUTATING_ROUTES` / `KNOWN_MUTATION_FUNCTIONS` interception + the four-question gate).

**Ruling (this overlay):** Stages 4 and 8 are **🔒 CONSTITUTIONALLY LOCKED**, not "deferred". They are *forbidden under the current charter*. They appear on the map only so the lifecycle is **honest about what we have chosen not to build** — not as a roadmap.

**Unlock condition** (recorded so the boundary is auditable, not so it is planned): a **charter-level DEC** that explicitly reverses DEC-V61-130/132, passes Kogami strategic review (opt-in, but advisable for a charter reversal of this size), and re-answers all four gate questions for the operator behavior. Absent that DEC, any code path that mutates or generates a case dir is a governance violation regardless of how it is framed.

> This is the truth-chain move: the framework is beautiful and internally coherent, but adopting it silently would reverse a core SSOT by omission. We draw the line in ink.

---

## 2. The lifecycle map — 9 stages → project reality

| Stage (framework) | Project reality (artifact) | Status | Boundary |
|---|---|---|---|
| **-1 Constitution / Goal language** | Blueprint v4 §0 North Star + three laws · `~/CLAUDE.md` v2.3 · DEC-130/132/207 · four-question gate | ✅ PRESENT (scattered) | this overlay unifies the *map*; SSOT stays in blueprint v4 |
| **0 Minimal high-value seed** | **Chosen ≠ framework's.** Framework proposes "Case Autopsy & Repair Loop" (repair-first). We chose **V&V-first vertical** = incompressible RANS aero (flat plate → NASA TMR gate, DEC-209/210). | ✅ DONE (P1 closed) | divergence is intentional: repair-first = operator (locked §1); V&V-first = advisor-compatible |
| **1 Observable harness** | `cfdtrust` pipeline (`validate-manifest`/`audit`/`run`/`report`) · real Docker simpleFoam · `trust_report.json` · reproducible | ✅ DONE | source-artifact pollution guard (MOCK in-repo, real solve on demand) |
| **2 Benchmark / eval** | canonical eval set **30 cases E01–E30** + `test_canonical_advisor_eval.py` (static) + v9 W2.0 predicate tests | ⚙️ **PARTIAL — the live gap** | see §4: behavioral adjudication missing |
| **3 Read-only diagnosis** | `advisor_stack.py` (11+ geometry/solver advisors) · `v9_advisor` (R1–R9 convergence) · `preflight.py` (5 categories) | ⚙️ IN PROGRESS (P2 W1/W2) | advisory-only enforced; `test_stack_zero_llm_imports` |
| **4 Controlled repair** | — | 🔒 **LOCKED** | reverses DEC-130/132 → needs charter DEC (§1) |
| **5 Experience memory** | V-series corpus (`industrial_solver_findings_v_series.md`, 85+ rows) · S-playbook · **Law-3 distillation into offline v9 ruleset** | ⚙️ IN PROGRESS | distillation gap: 85 findings → 9 rules (P2 W2) |
| **6 Multi-agent team** | cfd-chief-engineer + crew v2 (DEC-V61-208) · DEV-crew L0→L1→L2 ladder | ⚙️ IN PROGRESS, governance-bounded | Anthropic-canon §7: single-agent ≥ multi-agent today; don't over-orchestrate |
| **7 Evolve agent / self-evolution** | — (Kogami exists but opt-in; no auto-mutating evolve loop) | ⏸️ DEFERRED + governance-skeptical | v2.3 retired Kogami auto-trigger on purpose; do NOT restart on "orchestration era" narrative |
| **8 Auto-generate cases** | — | 🔒 **LOCKED** | reverses DEC-130/132 → needs charter DEC (§1) |
| **9 Aircraft-design workflow** | APU-bay industrial case (external sandbox, not workbench executor) | 🌅 FAR | gated on Law-1 runnable-coverage reaching compressible/CHT (P3/P4) |

**Reading the map**: of 9 framework stages, **4 are done/present** (-1, 0, 1), **3 in progress** (3, 5, 6), **1 is the live gap** (2), **2 are constitutionally locked** (4, 8), and **2 are deferred/far** (7, 9). The project is *further along* than the framework's greenfield framing assumes — its value to us is the **discipline** (Non-goal/Gate/Failure-Signal) and the **finger on the Stage-2 gap**, not the stage list.

---

## 3. Per-stage Goal / Non-goal / Exit-Gate / Failure-Signal — ACTIVE & NEXT stages only

> Deliberately omitted for locked (4/8), deferred (7), far (9), and done (-1/0/1) stages — writing gates for forbidden or finished work is theater. Where Blueprint v4 §4 already defines a phase exit gate, this **points to it** rather than restating.

### Stage 2 · Benchmark / eval (the live gap)
- **Goal**: the eval set must *adjudicate* advisor/ruleset quality behaviorally, not just check documentation shape — so "did adding rule N help?" has a machine answer.
- **Non-goal**: NOT a full behavioral rerun of all 30 cases (many reference external sandboxes / not-yet-landed F-NEW advisors — see `KNOWN_F_NEW_ADVISORS`). NOT a real-solve-per-case gate (cost). NOT more scalar rules before the judge exists (finding-5).
- **Exit gate**: ≥1 advisory system (v9 ruleset OR a subset of advisor_stack) has a **behavioral eval** that runs the real evaluator against labeled inputs and asserts the expected firing set, with cross-rule discrimination (right rule fires AND wrong rules stay silent). LLM-offline, deterministic, in CI sweep.
- **Failure signal**: rule count grows while the only "eval" is a doc-shape check → we are saturating (finding-5) with no adjudicator. *If a new rule lands and nothing executes to confirm it changes a verdict, stop and build the judge first.*

### Stage 3 · Read-only diagnosis
- **Goal**: catch setup-class and convergence-class death-modes offline + advisory-only (Blueprint v4 P2 exit gate governs).
- **Non-goal**: never a pass/fail gate that *blocks* a solve or *tunes* a V&V tolerance (those are DEC-209's, untouchable). Never a mutating route.
- **Exit gate**: → **Blueprint v4 §4 P2 exit gate** ("v9 ruleset grows 8→ top setup-error classes; review runs offline + advisory-only on a real case").
- **Failure signal**: a "diagnosis" that can only be reproduced by re-reading the same artifact it claims to diagnose (circular theater — exactly W1.1, RETRO finding-1). *If the check validates self-consistency instead of physical correctness, it's circular; split it (W1.0→W1.1′ pattern).*

### Stage 5 · Experience memory (Law-3 distillation)
- **Goal**: every closed/playbook V-row that maps to the active vertical becomes an offline rule with V-row provenance + true/false fixtures.
- **Non-goal**: NOT distilling open domain gaps (VOF/LES/compressible) before their compute type is runnable (Law-1). NOT rules with fabricated provenance (RETRO finding-2 — now guarded by `test_v9_provenance_validity.py`).
- **Exit gate**: top RANS-aero-adjacent closed V-rows distilled; each rule cites a *resolvable* V-row; provenance guard green.
- **Failure signal**: a rule's provenance cites a `.md`/V-row that does not resolve (fabrication) → caught by the provenance guard; *if the guard ever goes vacuous (no rule cites a repo path), the canary `test_at_least_one_rule_exercises_the_path_guard` must fire.*

### Stage 6 · Multi-agent team
- **Goal**: add a role only when a high-frequency failure class, an independent I/O boundary, and a measurable output justify it (framework's own activation principle, which matches v2.3).
- **Non-goal**: NOT adding agents for architectural symmetry. NOT replacing Codex relay (independent异源 review) with same-family subagents. NOT restarting Kogami auto-trigger.
- **Exit gate**: a new agent must demonstrably raise an eval/benchmark score OR lower human cognitive load, with no rise in system entropy.
- **Failure signal**: agent count rises but no handoff artifact is verifiable, or two agents write the same resource → stop, consolidate (Anthropic-canon §7: single-agent often ≥ multi-agent).

---

## 4. Stage-2 detail — the eval-layer truth (verified 2026-05-28)

The eval layer has **four rungs**; three exist, one is the gap:

| Rung | Artifact | State |
|---|---|---|
| Unit-behavioral (per-advisor, synthetic input) | `ui/backend/tests/test_advisor_stack.py` (31 tests) | ✅ |
| Predicate-behavioral (per v9 rule, true/false fixture) | v9 W2.0 (`afeeb4a`) + R9 (`c3435e4`) | ✅ |
| Case-level **documentation** (frontmatter shape + advisor-name existence + aggregate count) | `ui/backend/tests/test_canonical_advisor_eval.py` | ✅ (explicitly *static* — see its docstring L17–20) |
| Case-level **behavioral** (run evaluator on real input → assert expected firing set + no false positives) | `tests/test_v9_ruleset_behavioral_eval.py` (v9, `a609f58`) + `tests/test_advisor_stack_real_case_behavioral_spike.py` (advisor_stack, 1 real case = case_021, `ffaba27`) | ✅ for v9 ruleset; ✅ 1-case spike for advisor_stack (proves pattern); follow-on sub-DEC extends to other 12 manifest-bearing profiles |

`test_canonical_advisor_eval.py` says it plainly: *"does NOT call `assemble_stack` per case because the canonical eval files document expected behavior … not full case YAML/dict inputs."* So the documented "expected firings" in E01–E30 are **asserted to be well-formed, never executed**. That is finding-5 at the benchmark layer: we can add rules, but nothing adjudicates whether they change a verdict.

**Next-increment candidates:**
- **2a · v9 cross-rule behavioral eval** — ✅ **LANDED** (`a609f58`, 2026-05-28). 8 fixtures (4 single-rule discrimination + 4 co-firing) assert the *complete* fired set; 10/10 pass. v9 ruleset has no cross-rule false-positives on these fixtures; co-firing semantics (R4+R8, R3+R9, R6+R8, R5+R8) now adjudicated.
- **2b · advisor_stack case-behavioral eval** — ✅ **1-case SPIKE LANDED** (`ffaba27`, 2026-05-28). Spike outcome: (i) production `_autodiscover` adapter expects `inputs/` dir that NO in-repo case has → cannot blindly lift; (ii) 13 case_profiles ship top-level `parts_manifest.yaml` directly consumable by `assemble_stack(parts_manifest=...)`; (iii) case_021 (= E02) deterministically dispatches `{face_orientation, inlet_outlet}` with 0 findings — physically correct for a clean validated NASA TMR case. Manifest-pool size canary pinned at ≥10. **Follow-on sub-DEC (NOT in spike)**: per-case physical labeling for the other 12 manifest-bearing profiles + build `shm_dict` / `thermo_dict` / `step` extractors from OF `system/`+`constant/` dumps to unlock FULL E-case firing-set assertions (currently parts_manifest-driven subset only) + decide whether the production adapter should also discover top-level `parts_manifest.yaml`.

---

## 5. Non-goals of THIS overlay (anti-theater self-binding)

- Not re-opening the seed choice (Stage 0 is done; V&V-first stands).
- Not adding lifecycle stages beyond the framework's 9.
- Not building Stages 4/8 (locked) or 7 (deferred) under any reframing.
- Not auto-syncing this to Notion (session-end, Status=Accepted DECs only — this is a draft overlay).
- Not spawning a Workflow / multi-agent fan-out (no ultrawork invoked this session).

---

## 6. Governance (four-question gate on this overlay)

| Question | Answer |
|---|---|
| LLM-offline runnable? | N/A — strategy doc, no runtime code |
| Clear artifacts? | this file; the Stage-2 increment (2a) will emit pytest + fixtures |
| TrustGate / audit explains trust? | the overlay's value *is* honesty about each stage's real maturity (§2, §4) |
| AI advisory-only, no mutating route? | ✅ doc only; Stages 4/8 (mutation) explicitly locked (§1) |

- **Codex**: not a mandatory sync-trigger (no security boundary / auth / signing; no code). The Stage-2 increment, if it touches correctness-critical shared code, gets a Codex review (round cap=3) at that point.
- **Kogami**: opt-in; a charter *reversal* (Stage 4/8 unlock) would be a high-value Kogami trigger, but this overlay *preserves* the charter, so not invoked.
- **Ratification**: pending session-end — either a thin sub-DEC ("Stage Goal Spec overlay adopted") or a one-line addendum to DEC-V61-207. Recorded here, not auto-stamped.

---

**One-line**: *The framework gave us a lifecycle and a discipline; we map it onto what's already built, lock the two stages that would reverse advisor-not-driver, and aim the discipline at the one real gap — a benchmark that adjudicates instead of just documenting.*
