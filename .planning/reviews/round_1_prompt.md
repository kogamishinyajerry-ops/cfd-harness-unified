# Multi-Role Review — Round 1 · Demo-First Convergence

**Project**: `cfd-harness-unified`
**Branch**: `main`
**Review scope**: The last 6 commits form a "demo-first convergence round"
(2026-04-22). Review the complete changeset and the current state of the demo.

**Recent commits (newest first)**:
1. `a1feef9` chore(dev-server): pin frontend dev port to 5180
2. `f89cfd0` fix(export): 3-state precondition marker + contract_status headline
3. `47bc235` feat(contracts): backfill physics_contract for 4 cases + SATISFIED class
4. `700dccb` feat(ui): make /learn the default front door; Dashboard → /pro
5. `335c4b4` test(cleanup): align stale tests with post-DEC contracts
6. `87b3b39` fix(contracts): Python 3.12 + jsonschema + UNKNOWN note_map

**Running state**: `./scripts/start-ui-dev.sh` is live (backend :8000, Vite :5180).
`pytest tests/ ui/backend/tests` passes 784 / 2 skipped.

---

## Your job

Play **THREE roles** sequentially in a single review pass. For each role,
produce structured findings with severity classification. Be rigorous and
specific — vague advice is useless.

After all three roles, write a **consolidated convergence verdict** and a
**prioritized action list** that the implementer (Claude) can turn directly
into code changes.

**Severity scheme** (use consistently):
- 🔴 BLOCKER — ship-stopping problem
- 🟠 MAJOR — not a blocker but materially weakens the deliverable
- 🟡 MINOR — polish / nit
- 🟢 PRAISE — explicitly call out things done right (reviewers who only
  find fault teach the wrong lesson)

---

## Role 1 · 商业立项 demo 评审专家

You are a partner at an industry / venture fund evaluating this as a **funded
demo for an AI-CFD workbench startup**. The audience for `/learn` is a
potential customer (aerospace / automotive / power-generation CFD team lead
or head of engineering) or a technical due-diligence reviewer from a fund.

Questions to answer:

1. **30-second value proposition test**: open `http://127.0.0.1:5180/learn` cold.
   Within 30 seconds, can a decision-maker understand what this tool does and
   why it matters? If not, what's blocking?

2. **Narrative coherence**: does the 10-case catalog → case-detail (Story →
   Compare → Mesh → Run → Advanced) flow tell a single convincing story, or
   does it feel like a disconnected set of demos?

3. **Differentiation**: what is this demo's actual differentiated claim
   against (a) SimScale / Ansys cloud, (b) ML-surrogate-model benchmarks,
   (c) generic LLM-powered CFD assistants? Is that claim visible in the demo
   itself, or only in prose?

4. **Trust-building vs. trust-destroying signals**: the demo deliberately
   surfaces FAIL verdicts and INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE
   labels. Does that read as "refreshingly honest and credible" to a buyer,
   or "the tool can't even pass its own tests"? Where's the line?

5. **Call-to-action surface**: what does a user who is impressed by `/learn`
   do next? Is there a clear path from "this is interesting" to "I want to
   evaluate this seriously for my team"?

6. **Friction points** — list every moment during first-touch where a buyer
   might bail (e.g., Chinese-only text blocking non-CN buyers, jargon without
   context, broken links, broken runs, dashboard showing too many FAILs).

7. **"Why now" / market timing**: is there a visible hook that makes this
   specifically 2026-relevant, or does it look like generic V&V tooling that
   could have been built in 2018?

8. **Revenue model readability**: without reading a pitch deck, can a buyer
   infer how this monetizes (enterprise license? per-seat SaaS? audit-package
   sale?)? If that's deliberately absent, is the decision correct?

---

## Role 2 · CFD 仿真专家工程师

You are a senior CFD engineer (PhD or 10+ years industry, AIAA V&V member,
has done real F-16/C919/turbomachinery OpenFOAM + commercial-solver work).
Your evaluation posture: you are skeptical of AI-assisted CFD tools because
you have seen too many that hide physics errors behind nice UIs.

Required reading (in this order):

- `README.md` — project framing
- `knowledge/gold_standards/lid_driven_cavity.yaml` — my LDC physics_contract
- `knowledge/gold_standards/backward_facing_step.yaml` — my BFS contract
- `knowledge/gold_standards/plane_channel_flow.yaml` — my plane_channel contract
- `knowledge/gold_standards/impinging_jet.yaml` — my impinging_jet contract
- `knowledge/gold_standards/turbulent_flat_plate.yaml` — precedent reference
- `src/foam_agent_adapter.py` at the line numbers I cited (e.g., 810, 1178-1184,
  3113, 3270, 5184-5185)
- `src/convergence_attestor.py` + `src/comparator_gates.py`
- `.planning/research/physics_contracts_research.md`
- `.planning/STATE.md` (skim — it's 1300+ lines; focus on lines 1278-1305)

Questions to answer rigorously:

1. **LDC contract validity**: is `SATISFIED_FOR_U_CENTERLINE_ONLY` correct?
   Are the 5 preconditions physically accurate? The claim that
   `v_centerline` is "Ghia Table II indexed by x but labelled 'y'" — verify
   against Ghia 1982 actually, not just trust my claim. Is precondition #4
   as `partial` the right severity, or should it be `false`?

2. **BFS contract validity**: is the Xr/H plateau argument (7600 vs 5100
   DNS, <2% drift) actually true? What does the Le/Moin/Kim data say about
   Xr/H vs Re_H slope in this regime? Is the `partial` on turbulence-model
   (RANS vs DNS) the right severity for a literature comparison?

3. **plane_channel contract validity**: is labeling it
   `INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE` the correct verdict?
   Or is it too harsh — e.g., could icoFoam with strong boundary forcing
   actually sustain turbulence at Re_τ≈180 if the mesh is fine enough?
   Is my diagnosis (laminar N-S → Poiseuille) a simplification that misses
   nuance?

4. **impinging_jet contract validity**: is axis-patch-empty vs wedge as
   bad as I claim? Is a 2D planar slice at Re=10k really "not comparable"
   to axisymmetric Cooper 1984 data, or is it a known modeling shortcut
   with tolerable error? Separately, is A4 p_rgh iteration-cap the right
   diagnosis, or is it a symptom of a different underlying solver-config
   problem (e.g., underrelaxation, schemes, BC inconsistency)?

5. **Cross-case consistency**: do the 10 gold_standards YAML files use
   consistent semantics for contract_status? Are `SATISFIED`, `COMPATIBLE`,
   `SATISFIED_UNDER_LAMINAR_CONTRACT`, `SATISFIED_FOR_U_CENTERLINE_ONLY`
   well-differentiated or are they redundant naming variants of the same idea?

6. **V&V methodology fidelity**: does the attestor (A1..A6) + comparator gate
   (G1..G5) + three-state precondition-marker architecture map to actual
   ASME V&V40 / V&V20 practice, or is it ad-hoc governance language dressed
   up? Name the methodology gaps.

7. **Adapter contract drift risk**: if a new adapter developer changes
   `_generate_*` for a case without touching the gold YAML, does the
   physics_contract block become a lie? Is there any mechanism that would
   catch that drift, or is it purely a human-review gate?

8. **Silent-pass hazard completeness**: the `cylinder_crossflow` gold says
   the Strouhal extractor is a hardcoded shortcut and earns
   `COMPATIBLE_WITH_SILENT_PASS_HAZARD`. Are there similar hardcoded
   shortcuts in OTHER cases that should have also gotten this label but
   didn't? Grep for them.

---

## Role 3 · Senior Code Reviewer (standard)

Full diff review of the 6 commits against `e6f264d` (the pre-round base).
Focus on:

1. Correctness of `_normalize_contract_class` with the new `SATISFIED` prefix
   ordering. Verify `SATISFIED_UNDER_LAMINAR_CONTRACT` resolves to `SATISFIED`
   and not accidentally to `COMPATIBLE` via a shorter-prefix race.

2. `_render_contract_md` three-state marker: edge cases — what if
   `satisfied_by_current_adapter` is `None`, a dict, a number, a boolean
   passed as the string `"true"` or `"True"`? Is the `isinstance(satisfied, str)`
   narrow path correct, or should it also lowercase-match `"true"`/`"false"`
   strings? Any security / XSS angle via `escape(condition)` / `escape(ev)`?

3. Routing change `/` → `/learn`, Dashboard → `/pro`. Any URL dead-ends
   that would 404 a production bookmark from before the move? Any tests
   that still exercise `/` as Dashboard?

4. Test coverage of the new paths:
   - `test_export_renders_physics_contract_with_three_state_markers` —
     does it cover the `[✗]` case? The `None` case?
   - Any tests that enumerate all 10 cases against the new dashboard
     distribution (3 SATISFIED / 3 COMPATIBLE / ...)?

5. Commit-message accuracy: do the commit bodies accurately describe what
   the commits did? Any over-claiming (e.g., "zero UNKNOWN" — is that
   actually true in every code path, or just in the main dashboard render)?

6. Any residual `5173` references in the repo that the port-pin commit
   missed? Grep.

---

## Required output

Write **`.planning/reviews/round_1_findings.md`** (overwrite if exists).

Schema:

```markdown
# Round 1 Multi-Role Findings

**Date**: <iso-date>
**Reviewer**: Codex GPT-5.4 (3-persona sequential)
**Scope**: 6 commits from `87b3b39` → `a1feef9`

## Role 1 · 商业立项 demo 评审专家

### Verdict: [PASS_WITH_CHANGES | CHANGES_REQUIRED | BLOCK]

### 🔴 BLOCKERS
- [finding-id] one-line headline
  - **why**: ...
  - **evidence**: file:line or specific URL behavior
  - **suggested fix**: ...

### 🟠 MAJOR
(same schema)

### 🟡 MINOR
(same schema)

### 🟢 PRAISE
(bullet list)

## Role 2 · CFD 仿真专家工程师

### Verdict: [...]

(same schema)

## Role 3 · Senior Code Reviewer

### Verdict: [...]

(same schema)

---

## Consolidated convergence verdict

[APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED | BLOCK]

## Prioritized action list

Numbered 1..N, each with:
- **Who** (role 1 / 2 / 3)
- **Severity**
- **Effort estimate** (S / M / L)
- **Concrete change** (which file, what to change)

Order by: blockers first, then ROI (high-severity / low-effort top).
```

**Constraints**:
- Do NOT write any source code. Review only.
- Verify CFD claims against actual files / line numbers / external literature
  you have knowledge of. Do not fabricate file:line citations.
- Be concrete: a finding like "improve the UX" is rejected; "LearnHomePage
  CatalogCard.teaser_zh for lid_driven_cavity is 82 chars and overflows the
  3/2 aspect-ratio illustration container on viewports <768px" is accepted.
- Time box: aim for high-signal findings, not exhaustive. 15-25 total findings
  across all roles is a good target.
