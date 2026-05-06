---
decision_id: DEC-V61-134
dec_id: DEC-V61-134
title: N2 phase charter · Mesh control parity (sizing field + region refinement + prism layer + checkMesh advisor)
status: Accepted
parent_dec: V61-130
phase: N2
notion_sync_status: pending
parent_artifacts:
  - .planning/strategic/n2_kickoff/spec_2026-05-07.md
  - .planning/decisions/2026-05-06_v61_130_strategic_pivot_ai_advisor.md
  - .planning/decisions/2026-05-06_v61_132_n1_2_mutating_routes_registry_behavioral_contract.md
  - .planning/decisions/2026-05-07_v61_133_governance_simplification_b_plus.md
trigger: V130 charter mandates workbench-first parity build-out; M2 (mesh control) is the first capability phase post-N1 (AI auto-mutation deprecation)
autonomous_governance: true
counter_impact: +1
codex_review_relay: pending
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-07
confidence: med
---

# DEC-V61-134 · N2 Phase Charter · Mesh Control Parity

## Status
**Accepted 2026-05-07** — user mandate "全权授权你推进，按照你的建议来". Sub-DEC sequencing locked serial (per Rationale §"Why no parallel work"). Spec §8 Q1/Q2/Q3 default decisions adopted (Q1: gmsh+addLayers only; Q2: inline code constants for v0; Q3: reuse `cases/regression/elbow_duct/` with overrides).

## Context

V130 (strategic pivot · 2026-05-06) established that AI is an *advisor*, not an actor. N1 (V131 envelope hard-strip + V132 mutating-routes contract + V133 governance simplification) closed the deprecation arc — AI auto-apply paths are now contract-enforced absent.

The workbench's mesh control surface (B-module) is at ~25% of an industrial preprocessor's expected capability. M2 in the long-horizon roadmap (`project_cfd_harness_roadmap_v2.md`) calls for parity build-out to ~60%. **N2 is M2's implementation phase.**

Prior mesh feature work (V123 mesh quality adviser, V124 target cell count, V125 lc override, V126 checkMesh integration, V127 mesh quality card, V128 patch chip coloring, V129a per-patch severe non-ortho) covered **measurement** and **chip-level diagnosis**, but did NOT add **engineer-driven control surface**. N2 is that addition.

## Decision

Adopt the **N2 four-step phase plan** in `.planning/strategic/n2_kickoff/spec_2026-05-07.md`:

| Sub-phase | Capability | Slim DEC ID (planned) | Risk | Pre-merge Codex? |
|---|---|---|---|---|
| **N2.1** | Sizing field (base / min / max / curvature / proximity) | DEC-V61-135 | medium | per Opus confidence |
| **N2.2** | Region refinement zones (box / sphere) | DEC-V61-136 | medium | per Opus confidence |
| **N2.3** | Prism layer (snappyHexMesh addLayers) | DEC-V61-137 | **high** | **yes** (V132 registry change) |
| **N2.4** | checkMesh advisor (read-only suggestions) | DEC-V61-138 | low | no |

**Sequencing**: strict serial N2.1 → N2.2 → N2.3 → N2.4. Rationale in spec §4.

## Rationale

### Why charter DEC, not 4 slim DECs only

Per V133 §2.2 scope-driven rule, charter DEC is required when scope spans ≥3 modules **and** introduces a new architectural surface. N2:
- Touches `services/meshing_gmsh/` (existing) + `services/meshing_snappy/` (NEW for N2.3) + `services/mesh_quality/advisor.py` (NEW for N2.4) + `routes/mesh_imported.py` + new `routes/mesh_prism_layers.py` (NEW for N2.3) + `case_scaffold/bc_injector.py` (sHM stub → full dict)
- Introduces snappyHexMesh container exec path (parallel to `gmshToFoam`)
- Adds **a new mutating route** which triggers V132 contract migration (high blast radius)

This is exactly the "cross ≥3 modules + governance contract change" pattern V133 §2.2 reserves for full charter DECs.

### Why this sequence

- **N2.1 first**: stays in gmsh, no container path change, builds the `MeshSizingField` schema that N2.2 reuses
- **N2.2 second**: extends gmsh sizing-field surface; same container path; depends on N2.1 schema
- **N2.3 third**: introduces snappyHexMesh container exec — highest blast radius. Doing it last means N2.1 + N2.2 are stable when the new mutator lands; one V132 registry migration instead of multiple
- **N2.4 last**: read-only advisory; references controls from N2.1-N2.3 in suggestion templates. Building first would force advice rewrites as controls land

### Why no parallel work

V133 valued workflow simplification over throughput. Parallel sub-phases would:
1. Force schema coordination overhead (N2.1 schema vs N2.2 reuse-by-id)
2. Risk dual V132 registry migrations if N2.3 starts before N2.1/N2.2 finalize POST body
3. Trigger Codex review interleaving (one chain per sub-DEC, max 3 rounds; parallel = 3+ active chains)

Strict serial keeps each sub-DEC's cap=3 chain independent and trivially auditable.

## Workbench-first acceptance (V130 Principle B)

Every sub-DEC MUST satisfy these gates before Status=Accepted:

1. **LLM-offline reachability**: with `LLM_PROVIDER=disabled` env, engineer completes the full mesh control flow via Step 2 UI. No LLM call required.
2. **AI advisor surface is GET-only**: any AI helper added is `is_mutating_route() == False`. Application happens through existing manual controls.
3. **V132 contract preserved**: `tests/test_ai_advisor_contract.py` Layer-A + Layer-C green. New tool dispatchers (if any) registered.
4. **No "apply this fix" UI button**: N2.4's structured recommendations render as copy-able text, NOT as click-to-apply actions.

## Out of scope

- AI advisor RAG knowledge base (M6 / N6 territory)
- Mesh post-processing field rendering (M5 / N5 territory)
- Solver scheme / URF controls (M4 / N4 territory)
- Compressible / turbulence model selection (M3 / N3 territory)
- Multi-engine choice (only gmsh + addLayers; castellated/snap as alternative tier deferred per spec §8 Q1)
- Parallel sub-DEC work (see Rationale)

## Threat model

| Threat | Vector | Mitigation |
|---|---|---|
| New `/api/import/{case_id}/mesh/prism-layers` endpoint mis-registered as read-only, bypassing V132 | Forgetting to add to `MUTATING_ROUTES` | Layer-C AST namespace-binding test catches; PR check `ai-path-mutation-grep` warns; sub-DEC N2.3 acceptance §3 explicit |
| snappyHexMesh container divergence on multi-solid STL (V61-129a territory) | addLayers stage non-convergence | Reuse V129a per-patch severe-non-ortho data; reject prism config on flagged patches with structured 422 |
| Engineer constructs invalid bbox (zero-volume / out-of-domain) | N2.2 zone payload | Backend validates against case AABB; structured 422 with `failing_check: refinement_zone_invalid` |
| N2.4 advice template suggests value that crashes mesher | Bad heuristic in `advisor.py` | Templates produce text + recommended_change metadata; engineer reviews before retyping |
| Codex review chain on N2.3 hits V133 cap=3 | High-LOC + new container path | Pre-emptive scope narrowing (only `walls` patch in initial sub-DEC; multi-patch in N2.3-extend) per spec §6 |
| Notion main-control-page drift | Forgot Active block update | Charter DEC landing triggers Notion sync per V133 batch-at-session-end |

## Verification (charter-level — not sub-DEC level)

- [ ] Spec doc `.planning/strategic/n2_kickoff/spec_2026-05-07.md` exists and is reachable from this DEC's frontmatter
- [ ] Sub-DECs N2.1-N2.4 will use **slim 6-field** schema (per V133)
- [ ] Each sub-DEC's PR includes the V130 Principle B acceptance checklist results
- [ ] Notion main control page Active block updated within session-end of charter Acceptance
- [ ] N2 phase counter increments only by sub-DEC count (charter is +1, sub-DECs +1 each → N2 final counter delta = 5)

## Counter / governance bookkeeping

- `counter_impact: +1` (charter DEC)
- Sub-DECs: +4 (N2.1-N2.4)
- N2 phase total counter delta: **+5**
- No Kogami review (opt-in per V133; charter DEC is governance-shaped but does NOT change governance rules — it implements V130 charter)

## Self-bootstrap exception

This DEC does NOT need a self-bootstrap clause: it is a child of V130 (charter), not a governance-rule-change DEC. Standard authoring path applies.

## Calibration window

Track during N2 execution:
- R0 Codex APPROVE rate on sub-DECs (target ≥30% per V133 calibration window)
- Number of sub-DECs that hit the round cap=3 ceiling (target = 0; ≥1 = signal that N2.3 scope was too wide)
- Workbench-first gate fails (target = 0; ≥1 = signal V130 contract leaks back in)

If sub-DEC count exceeds 4 (i.e., N2.x or N2.y splits emerge), update this charter with `Status: Amended` and append the new sub-DEC IDs.

## References

- DEC-V61-130 · Strategic pivot to AI-as-advisor
- DEC-V61-131 · N1.1 envelope hard-strip
- DEC-V61-132 · N1.2 MUTATING_ROUTES registry + behavioral contract
- DEC-V61-133 · N1.3 (informal) · B+ governance simplification charter
- `.planning/strategic/n2_kickoff/spec_2026-05-07.md` · Full design spec
- `feedback_cfd_harness_ai_advisor_pivot.md` · V130 strategic context
- `project_cfd_harness_roadmap_v2.md` · M1-M6 long-horizon roadmap
