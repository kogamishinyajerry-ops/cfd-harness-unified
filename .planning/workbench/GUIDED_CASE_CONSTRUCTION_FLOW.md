# Guided Case Construction Flow · SSOT

> **Established**: 2026-05-22 (post-cycle-6 strategic pivot)
> **Governs**: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED (charter-class)
> **Memory anchor**: [feedback_cfd_workbench_dynamic_guided_pivot](../../../.claude/projects/-Users-Zhuanz/memory/feedback_cfd_workbench_dynamic_guided_pivot.md)
> **Supersedes (amends, not replaces)**: blueprint v3 "UI 四区域稳定布局" — regions stay stable; **content within each region MUST be dynamic per step + case state.**

---

## 0 · What this is + isn't

**IS**: the product spec for how a **CFD newcomer or mid-level engineer** is walked, step-by-step, through building a complete OpenFOAM case inside the workbench, with the UI **deciding what to show next based on the case's current state + what's blocking progress**, not based on a fixed page-layout template.

**IS NOT**:
- A new audit-engine charter (audit-engine deepening is closed per 2026-05-22 pivot)
- An LLM-driven autopilot (V130 invariant intact — AI stays advisor, not driver)
- A replacement for the V3 4-region layout (regions stay; content inside is dynamic)
- A wizard with rigid forward-only navigation (engineers can jump back/forward; UI re-decides per state)

## 1 · Target user

- **Primary**: CFD beginner who can spell "Reynolds number" but has never run OpenFOAM blockMesh manually
- **Secondary**: mid-level CFD engineer who knows commercial CAE (Fluent / STAR-CCM+) but is new to OpenFOAM's dictionary-driven workflow
- **Out of scope**: expert OpenFOAM user — they don't need the workbench; they `vim controlDict` directly

**The litmus test**: can someone who has done **one** CFD class in undergrad sit down at the workbench, pick "external aerodynamics over a cylinder", and ship a converged Re=100 case in **≤ 30 minutes of clock time** with the workbench guiding every decision?

## 2 · The 5-step spine (V3 baseline · CONTENT now dynamic)

| Step | Name | Engineer's question | Default focus | Done when |
|---|---|---|---|---|
| 1 | **Geometry** | "what shape am I simulating?" | viewport: imported geom; rail: import + sanity panel | STL/STEP ingested · checkGeom green · named patches enumerated |
| 2 | **Mesh** | "is the mesh good enough?" | viewport: mesh + cell-count overlay; rail: refinement region builder | checkMesh OK · cell count plausible (1k-10M) · BL flags resolved |
| 3 | **Physics** | "which solver + turbulence + fluid?" | rail: regime picker (steady/transient · incompressible/compressible · turbulence model); viewport: dim + Reynolds badge | regime fixed · solver selected (simpleFoam / pimpleFoam / interFoam · ...) |
| 4 | **BCs** | "what happens at each face?" | viewport: per-patch focus (auto-zoom to focused patch); rail: BC type picker per patch | every patch has typed BC for every expected field |
| 5 | **Solve + Postp** | "did it converge + what's the answer?" | viewport: residual chart + slice; rail: run controls + QoI cards | residuals below target · QoI stable · advisor surfaces post-run findings |

**Stable across steps** (V3 4-region layout — DO NOT mutate):
- TopBar (case id · solver badge · LIVE pill · save state)
- Step Spine (the 5 steps above; current step highlighted; jump-back allowed)
- Viewport + Artifacts (main visualization)
- Engineer Control Rail (right-side action panel)

**Dynamic per step + state** (THE pivot · this is what was固化 before):
- WHICH controls appear in the rail
- WHICH overlays appear in the viewport
- WHICH advisor cards appear in the bottom panel
- WHICH next-step CTA appears in TopBar
- WHICH error/warn surfaces are foregrounded

## 3 · The four UI-content drivers (per user 2026-05-22 quote)

The workbench UI content for the current frame is decided by **4 inputs**, evaluated server-side (or client-side from `runDetail` + manifest) on every state transition:

### Driver 1 · **Current step**
Which of the 5 steps the engineer is on. Default starting frame.

### Driver 2 · **Case's most-pressing problem**
The single biggest thing blocking progress. Examples:
- Step 2 + checkMesh emits "non-orthogonality > 70" → rail foregrounds "fix non-orthogonality" with curated suggestions (snappyHexMesh refinement / surface remesh) **before** asking about BL parameters.
- Step 4 + manifest has `bc_contract.thermal_fields=[T]` but `0/T` missing → rail foregrounds "your physics declared T but you have no temperature BC yet"; viewport auto-focuses inlet (where T usually starts being defined).
- Step 5 + residuals plateau above target → rail foregrounds "convergence stall" with Gap-#48-style curated diagnosis (mesh quality? relaxation? scheme?).

The audit engine (the thing we just closed deepening) is **the input to driver 2** — every contract gap surfaces here, not as a verdict card buried in artifacts.

### Driver 3 · **What information needs to be filled in (just-in-time)**
The next required field. Examples:
- Step 1 done, Step 2 entered, manifest has `mesh_contract.y_plus_target` empty → rail foregrounds y+ picker with a "what should I pick?" tooltip linked to V-row evidence.
- Step 3 picks `simpleFoam` → step 4 rail asks for inlet velocity FIRST (not pressure first), because simpleFoam needs velocity-led BC.
- Step 3 picks `interFoam` → step 4 rail asks for phase fractions + `alpha.water` BC before asking about pressure (which is now `p_rgh` per Gap #48).

**No omnibus forms.** A single field per ask when the case has unresolved upstream constraints; batched fields only when constraints are resolved.

### Driver 4 · **What area of the case the user is focused on**
Spatial / structural focus. Examples:
- Engineer clicks "inlet" patch in viewport → rail auto-switches to inlet BC editor; advisor cards filtered to inlet-relevant.
- Engineer drags refinement region around a wing leading edge → rail switches to surface refinement settings; mesh-step CTA "preview mesh" foregrounded.
- Engineer expands "residual chart" panel → bottom panel shows residual-shaped advisor cards (oscillation patterns, monotone slow descent, etc.).

Focus is captured through:
- DOM events (click / hover / focus on viewport elements + rail tabs)
- URL query state (`?step=4&patch=inlet`) so deep-links are reproducible
- Last-action heuristic (engineer just typed in inlet velocity → infer focus = inlet)

## 4 · State-machine sketch

```
CaseState = {
  step: 1..5,
  manifest: case_manifest.yaml (typed against schema),
  artifacts: {audit/*.json, mesh_report.json, bc_quality.json, ...},
  focus: {patch?: string, region?: string, panel?: string},
  pendingFields: string[],          // driver 3 source
  problems: Problem[],              // driver 2 source (audit-engine output)
  lastAction: ActionEvent,          // driver 4 source
}

UIFrame = decide(CaseState):
  rail.primary       = pickRailPrimary(step, problems[0], pendingFields[0], focus)
  viewport.overlays  = pickOverlays(step, focus, problems)
  bottom.cards       = pickAdvisorCards(step, focus, artifacts)
  topbar.cta         = pickCTA(step, problems, pendingFields)
```

Every state mutation (rail interaction, viewport click, manifest patch, new artifact landed) calls `decide(CaseState)` again. **The UI is a pure function of state.** Static layouts that don't change with state = anti-pattern.

## 5 · Anti-patterns (what 固化 looks like)

| 固化 anti-pattern | What it produces | Why bad |
|---|---|---|
| Single static rail with all 12 controls always shown | Beginner overwhelmed; doesn't know which control to touch first | Driver 3 ignored |
| Generic "Run" button always visible regardless of mesh state | Beginner clicks Run on broken mesh → wastes solver minutes | Driver 2 ignored |
| Patch list as a flat dropdown; no auto-focus on patch click | Engineer scrolls; no spatial grounding | Driver 4 ignored |
| All advisor cards rendered always | Cards become noise; engineer ignores them | Drivers 2 + 4 ignored |
| Step Spine allows clicking step 5 before step 1 done | Engineer ends up solving an empty case | Step preconditions ignored |
| Wizard with rigid forward-only flow | Engineer can't iterate (CFD is iterative by nature) | Over-constrained |

## 6 · Honored invariants (NOT changed by this pivot)

- **V130 four-question gate**: every new workbench surface MUST answer (a) LLM-offline runnable, (b) artifacts as truth, (c) TrustGate explainable, (d) AI advisory-only.
- **AI = advisor, not driver** (per `feedback_cfd_harness_ai_advisor_pivot`): the dynamic UI is driven by **state**, not by an LLM "thinking" about what to show next. LLM remains advisor on the right rail.
- **Artifacts as truth**: drivers 2 + 3 + 4 source state from manifest + artifact files, not from inferred / hallucinated state.
- **Engine refuses to lie** (Gap #32 / #44 / #46 trust beats): the audit engine remains honest; dynamic UI just SURFACES its honesty in the right place at the right time.

## 7 · Out of scope (parking lot)

- **AI auto-completing manifests**: V130 forbids. Manifest comes from engineer + helper widgets (linked to curated V-row tooltips), not from LLM.
- **AI-driven Step Spine ordering**: Step ordering is fixed (1→2→3→4→5 forward by default; backward navigation allowed). LLM doesn't decide ordering.
- **"Beginner mode" vs "expert mode" toggle**: superficially attractive but encodes 固化 (expert mode = static layout). Same dynamic engine serves both; experts will just hit fewer "problem" surfaces because their cases land cleaner.
- **Multi-user collaboration / live cursors**: separate concern. This SSOT is single-user.
- **Non-OpenFOAM backends**: OpenFOAM-first. Other backends (SU2, code_saturne) reuse the same state-machine when they show up.

## 8 · Success criteria (charter-level)

A reasonable end-state for the **first** workbench-guided-UX iteration (M3.0 cycle 1 candidate):

1. **5-step spine renders** with current-step highlight + per-step "what to do next" CTA derived from `CaseState`, not hardcoded.
2. **At least 3 dynamic-content slots wired** (rail / viewport-overlay / bottom-advisor) responding to `problems[0]` + `pendingFields[0]` + `focus`.
3. **case_007 KCS ship VOF dogfood**: a junior engineer (or simulation thereof) can go from empty case dir to `0/alpha.water` BC declared in ≤ 10 click+type interactions, with the workbench surfacing Gap #48 / Gap #49 problems the moment they arise (without the engineer reading bc_quality.json directly).
4. **Anti-pattern check**: at every state transition, **at least one** of `rail.primary` / `viewport.overlays` / `bottom.cards` / `topbar.cta` differs from the previous frame.

Failure modes that fail this charter:
- Static layout that doesn't respond to manifest changes
- "Beginner mode" toggle (固化 in disguise)
- LLM call required to render the next frame
- Engineer has to read raw artifact JSON to find the blocker

## 9 · Implementation rolling questions (NOT scope; just track)

- Where does `decide(CaseState)` live — backend (Python) returning a frame descriptor, or frontend (React) computing from `runDetail`? Probably backend for testability; frontend renders the descriptor.
- How does the audit engine's `problems` list get prioritized into `problems[0]`? Severity (FAIL > WARN > info) × step-relevance (step-N problems before step-(N+k) problems).
- What's the minimum manifest patch surface? Probably PATCH endpoints per top-level section (`bc_contract` / `mesh_contract` / `vof_contract` / ...), so frontend can apply one field at a time without re-uploading the whole YAML.
- Provenance trail: every dynamic surface decision must be inspectable. "Why is rail showing the y+ picker?" → click → "because mesh_contract.y_plus_target is empty AND step=2 AND no upstream problems". This is the trustchain analog for UI.

## 10 · Related artifacts

- DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED (charter — `.planning/decisions/2026-05-22_v61_202_workbench_dynamic_guided.md`)
- Memory: `feedback_cfd_workbench_dynamic_guided_pivot`
- Memory: `feedback_cfd_harness_ai_advisor_pivot` (advisor-not-driver)
- Memory: `feedback_claude_code_is_the_advisor` (Claude Code session = advisor surface)
- Memory: `feedback_cfd_four_question_gate` (4Q gate · extend with "5th: does this serve guided UX?")
- Memory: `project_cfd_harness_blueprint_v3` (UI 4-region layout · amended by this SSOT)
- Blueprint V3 INDEX (region layout baseline)
- Blueprint V9 INDEX (post-run advisor — composes with this; advisor cards become bottom-panel content under driver 2)

---

**This is the SSOT.** Future workbench DECs / sub-DECs MUST reference this doc and answer: "which of the 4 drivers does this serve?" If none, the work doesn't belong in the guided-UX charter.
