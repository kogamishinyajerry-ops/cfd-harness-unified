---
decision_id: DEC-V61-139
dec_id: DEC-V61-139
title: N3 phase charter · Physics / Materials Layer (MaterialContract + RegimeContract + derived solver)
status: Accepted
parent_dec: V61-130
phase: N3
notion_sync_status: pending
parent_artifacts:
  - .planning/strategic/blueprint_v3_2026-05-07.md
  - .planning/strategic/n3_n6_outline_2026-05-07.md
  - .planning/decisions/2026-05-06_v61_130_strategic_pivot_ai_advisor.md
  - .planning/decisions/2026-05-06_v61_132_n1_2_mutating_routes_registry_behavioral_contract.md
  - .planning/decisions/2026-05-07_v61_133_governance_simplification_b_plus.md
  - .planning/decisions/2026-05-07_v61_134_n2_mesh_control_parity_charter.md
trigger: V130 charter mandates workbench-first parity build-out; M3 (physics / materials layer) is the post-N2 capability phase delivering structured fluid + thermal + turbulence regime contracts that N4 (BC + solver unification) consumes
autonomous_governance: true
counter_impact: +1
codex_review_relay: pending
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-07
confidence: high
---

# DEC-V61-139 · N3 Phase Charter · Physics / Materials Layer

## Status

**Accepted 2026-05-07** — user mandate "go,允许你一直N2 → N3 → N4 → N5（serial）". N2 phase closed cleanly (DEC-V61-134 charter + DEC-V61-135 sizing + DEC-V61-136 region refinement + DEC-V61-137 prism layer + DEC-V61-138 advisor). N3 begins per blueprint v3 §convergence sequencing.

## Context

V130 (strategic pivot · 2026-05-06) established AI as advisor, not actor. N1 closed the deprecation arc; N2 (just closed) delivered engineer-driven mesh control. **N3 is the physics / materials parity phase** — the workbench currently has free-text raw-dict editing of `constant/physicalProperties` and `constant/momentumTransport` (DEC-V61-102 allowlist) but **no structured contract** for material properties or turbulence regime selection.

That gap forces engineers to either (a) memorize OpenFOAM dict syntax or (b) lean on the AI coach to construct dicts — exactly the AI-as-actor pattern V130 deprecated. N3 closes the gap with structured contracts the engineer fills via form, not chat.

Prior physics-related work (DEC-V61-102 allowlist, V104 raw-dict route, V107+ tolerance editor, the regression case fixtures) established **mechanical surfaces** for editing dict files. N3 adds the **semantic layer above** them: typed material properties, regime selection with applicability bounds, and a derivation table that maps regime → solver name (which N4 then consumes as a default-with-override).

## Decision

Adopt the **N3 five-step phase plan** in `.planning/strategic/n3_n6_outline_2026-05-07.md` §1:

| Sub-phase | Capability | Slim DEC ID (planned) | Risk | Pre-merge Codex? |
|---|---|---|---|---|
| **N3.1** | `MaterialContract` schema (fluid: name + ρ + ν + Pr; thermal: cp + k; with literature citation field) | DEC-V61-140 | medium | per Opus confidence |
| **N3.2** | `RegimeContract` schema (laminar / RANS-RAS / RANS-kOmegaSST / LES-stub; with Re/Ma/y+ applicability bounds) | DEC-V61-141 | medium | per Opus confidence |
| **N3.3** | Step "Physics" panel UI (Beginner presets / Power full editor) — slots into Step 3 left rail OR new tab | DEC-V61-142 | medium | per Opus confidence |
| **N3.4** | Solver derivation: regime → solver name (icoFoam / simpleFoam / pimpleFoam / buoyantSimpleFoam) — read-only mapping table | DEC-V61-143 | low | no |
| **N3.5** | CaseProfile tolerance binding: regime → default tolerance template (uses existing CaseProfile machinery) | DEC-V61-144 | low | no |

**Sequencing**: strict serial N3.1 → N3.2 → N3.3 → N3.4 → N3.5. Rationale below.

**N6 parallel-eligible after N3.4 lands** (per user authorization "N6 唯一可在 N3 后并行的 phase（因为它读 case state 不写）"). N6 advisor is read-only and consumes regime + material + solver state once N3.4 stabilizes the solver derivation table.

## Rationale

### Why charter DEC, not 5 slim DECs only

Per V133 §2.2 scope-driven rule, charter DEC is required when scope spans ≥3 modules **and** introduces a new architectural surface. N3:

- Adds `services/physics/` (NEW module — material + regime contracts + writer)
- Modifies `services/case_scaffold/bc_injector.py` (regime → field initial values)
- Modifies `services/case_completeness/analyzer.py` (physics fill rate gauge)
- Modifies `services/case_dicts/allowlist.py` (structured-write coexists with raw-write)
- Adds `routes/physics.py` (NEW — POST `/api/cases/{id}/physics` to commit MaterialContract + RegimeContract)
- Modifies `services/ai_actions/mutating_routes.py` (V132 registry — new mutator)
- Modifies frontend Step 3 (left rail OR new tab) + `pages/workbench/step_panel_shell/types.ts` (new schemas)

Cross 7 modules + new structured architectural surface + new V132 mutator = full charter DEC pattern.

### Why this sequence

- **N3.1 first**: MaterialContract is the foundation; RegimeContract may reference material name (e.g., for citation cross-link). No coupling to UI yet.
- **N3.2 second**: RegimeContract introduces applicability bounds that reference physical properties (Pr from N3.1 for thermal regime gating). Building first would force schema rewrites.
- **N3.3 third**: UI consumes both schemas. Building before backend = mocking the wire shape, then refactoring.
- **N3.4 fourth**: solver derivation depends on regime literal stabilizing. Read-only mapping table; no UI risk.
- **N3.5 last**: tolerance binding closes the loop. Zero-risk addition once N3.4 derivation table is fixed.

### Why no parallel sub-DEC work within N3

Same reasoning as N2 charter §"Why no parallel work":
1. Schema coordination overhead between N3.1 and N3.2 (Pr / applicability cross-references)
2. Single V132 registry migration when N3.3 lands (one mutator: POST `/api/cases/{id}/physics`)
3. Codex review chain stays auditable per sub-DEC (V133 cap=3)

**N6 parallel is permitted** because N6 reads physics state, never writes. No V132 collision.

## Workbench-first acceptance (V130 Principle B)

Every N3 sub-DEC MUST satisfy these gates before Status=Accepted (Blueprint v3 §5 four-question gate):

1. **Q1 LLM-offline reachability**: with `LLM_PROVIDER=disabled`, engineer completes the full physics-setup flow via Step 3 UI. No LLM call required.
2. **Q2 artifacts output**: physics commit writes `constant/physicalProperties` + `constant/momentumTransport` (or successor `turbulenceProperties` for newer OpenFOAM) — engineer can `cat` the case directory and see legible OpenFOAM dict files.
3. **Q3 audit explainable**: CaseProfile (or successor TrustGate) shows regime + material with citation, derivation chain (regime → solver), and source provenance (preset library vs engineer-typed).
4. **Q4 AI advisory only**: any AI helper added (e.g., "suggest k-ω SST given your Re") is read-only — the suggestion appears in chat / sidebar, never auto-applies. New AI helpers MUST register in V132 dispatch path with `is_mutating_route() == False`.

## Out of scope

- Compressibility transitions (Mach > 0.3) — deferred to M3-extend
- Multi-phase, combustion, radiation, magnetohydrodynamics — M4+ in roadmap_v2
- Custom material library (engineer-defined materials) — defer to N3-extend; v0 ships water/air/oil only
- LES sub-grid model selection (LES is stubbed per outline) — deferred to M3-extend
- Wall function selection auto-derivation — N4 territory
- BC type per-patch (uses regime, but is N4.1)
- Solver dict editor with diff (N4.2)

## Threat model

| Threat | Vector | Mitigation |
|---|---|---|
| New `POST /api/cases/{id}/physics` mis-registered as read-only, bypassing V132 | Forgetting to add to `MUTATING_ROUTES` in N3.3 | Layer-C AST namespace-binding test catches; PR check `ai-path-mutation-grep` warns; sub-DEC N3.3 acceptance §3 explicit |
| Regime applicability bounds (Re/Ma/y+) parameterize from research that may be wrong / dated | Hard-coded thresholds in `RegimeContract` validator | Cite source in metadata field per regime; never auto-warn; engineer reads citation, decides (Q4 advisory-only) |
| Solver derivation table mismatches regime → engineer ends up with broken case | Stale mapping in N3.4 | Mark each row with `tested_against_case` regression-suite ID; missing test = blocked from N3.4 acceptance |
| Material library bootstrap drift (water/air/oil values diverge from canonical refs) | Hand-typed constants in N3.1 | Cite source per material (e.g., NIST webbook URL) in `MaterialContract.citation`; Layer-A test asserts citation present for all bundled materials |
| Frontend Step 3 panel placement breaks existing BC face annotation muscle memory | N3.3 UI placement (left rail vs new tab) | Charter chooses placement explicitly; N3.3 sub-DEC acceptance includes screenshot of Step 3 layout pre/post |
| Existing raw-dict route (V102 allowlist) and structured route (N3.3 mutator) drift | Two writers for same dict file | Structured writer is authoritative when present; raw-edit path adds `Last-Modified-By` header indicating last writer; tests assert round-trip via either path produces identical dict |
| N6 (AI advisor) starts in parallel before N3.4 derivation table stabilizes | Race between N6 read and N3.4 schema lock | N6 parallel-eligible **only after N3.4 lands**; charter pins this dependency |

## Verification (charter-level — not sub-DEC level)

- [x] Outline doc `.planning/strategic/n3_n6_outline_2026-05-07.md` §1 exists and is reachable
- [ ] Sub-DECs N3.1-N3.5 will use **slim 6-field** schema (per V133 §2.2)
- [ ] Each sub-DEC's PR includes the V130 Principle B / Blueprint v3 four-question gate results
- [ ] N6 charter (DEC-V61-145 planned) explicitly waits on N3.4 acceptance commit SHA
- [ ] Notion main control page Active block updated within session-end of charter Acceptance
- [ ] N3 phase counter increments only by sub-DEC count (charter +1, sub-DECs +5 → N3 final delta = 6)

## Counter / governance bookkeeping

- `counter_impact: +1` (charter DEC)
- Sub-DECs: +5 (N3.1-N3.5)
- N3 phase total counter delta: **+6**
- No Kogami review (opt-in per V133; charter implements V130, not a governance-rule change)

## Self-bootstrap exception

This DEC does NOT need a self-bootstrap clause: it is a child of V130 (charter), not a governance-rule-change DEC. Standard authoring path applies.

## Calibration window

Track during N3 execution:
- R0 Codex APPROVE rate on sub-DECs (target ≥30% per V133 calibration window)
- Number of sub-DECs hitting V133 round cap=3 (target = 0; ≥1 = signal sub-DEC scope was too wide)
- Workbench-first gate fails (target = 0; ≥1 = V130 contract leak)
- Material library citation completeness (target = 100% bundled materials cite a public-source URL)

If sub-DEC count exceeds 5 (i.e., N3.x emerges for additional materials / regimes), update this charter with `Status: Amended` and append the new sub-DEC IDs.

## References

- DEC-V61-130 · Strategic pivot to AI-as-advisor
- DEC-V61-132 · MUTATING_ROUTES registry contract
- DEC-V61-133 · B+ governance simplification
- DEC-V61-134 · N2 phase charter (sibling)
- DEC-V61-138 · N2.4 checkMesh advisor (immediate predecessor — closes N2)
- `.planning/strategic/blueprint_v3_2026-05-07.md` · Product blueprint
- `.planning/strategic/n3_n6_outline_2026-05-07.md` · N3-N6 long-horizon outline
