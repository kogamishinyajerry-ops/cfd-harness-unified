# Product Thesis: CFD Harness Unified

> **One-sentence pitch.** A CFD workbench where every simulation run
> exports a regulator-ready audit package that maps measurement ↔ gold
> standard ↔ tolerance ↔ literature citation ↔ commit SHA ↔ decision
> trail in a single signed bundle — so that compliance reviewers can
> accept results as-is instead of asking for spreadsheets.

Elected 2026-04-20 by DEC-V61-002. Owner: Kogami / CFDJerry. Status:
Phase 0 in flight.

## The problem

Regulated industries that rely on CFD — commercial aerospace, medical
device (FDA V&V40), nuclear (NQA-1), automotive crash/FSI — must produce
extensive evidence that each simulation is:

1. Built on a **verified solver** (right mathematics, right
   discretization)
2. **Validated** against experimental or analytical data with stated
   uncertainty
3. **Re-runnable** from the exact same inputs years later
4. **Traceable**: every tolerance, every numeric constant, every
   boundary-condition choice must point to a literature reference or
   an internal authority memo

Existing commercial workbenches (ANSYS Fluent, STAR-CCM+, SimScale,
COMSOL) do all four poorly. Their V&V story is a best-practices PDF
plus some template documents; the actual evidence is hand-assembled
in Word, Excel, and email threads after the run completes. A 2023
informal survey of aerospace CFD leads put the post-run compliance
effort at **30-60 engineer-hours per validated case**, dominated by
citation hunting and screenshot curation.

The core pain is not that the simulation is wrong. It is that the
simulation is correct but **cannot prove it was correct** without a
week of paperwork.

## The solution

Move V&V from a post-run document-assembly task to an **enforced
property of the workflow**. The engineer cannot run a simulation
without first having the case pass a machine-checkable `physics_
contract` (gold-standard reference value, tolerance band, mesh-
resolution precondition, regime-applicability check). The run's
result is automatically compared to the contract. Every
non-compliance is logged with a human-readable `audit_concern`
string (e.g. `COMPATIBLE_WITH_SILENT_PASS_HAZARD:spalding_fallback_
confirmed`). The accumulated evidence is one-click exportable as a
signed zip + PDF.

This is a narrow repositioning of the existing `cfd-harness-unified`
codebase. The repo already has the three essential ingredients:

- **Whitelist of 10 literature-cited benchmark cases**
  (`knowledge/whitelist.yaml`) spanning internal/external,
  incompressible/natural-convection, laminar/turbulent regimes
- **Physics contracts** in `knowledge/gold_standards/*.yaml` with
  `ref_value`, `tolerance`, `reference_correlation_context`, and
  `preconditions[].satisfied_by_current_adapter` booleans
- **Auto-verifier + error attributor**
  (`src/auto_verifier/`, `src/error_attributor.py`) that emits
  `audit_concern` at runtime and routes `SILENT_PASS_HAZARD` flags
  to the appropriate consumer

What is missing is the **user-facing surface** that makes the
contract-driven workflow legible to non-governance-literate users
(compliance officers, external reviewers, team members who weren't
in the room when the contract was drafted). That surface is the
UI MVP this thesis commissions.

## Why now

Three forces converge in 2026:

- **FDA finalized V&V40** for medical-device computational modeling
  in 2023; aerospace is harmonizing around similar evidentiary
  standards via ASME V&V 40 and DO-178C's emerging ML annexes.
  Demand for auditable CFD evidence is no longer theoretical.
- **LLM-assisted CFD case setup** (NVIDIA Modulus, academic
  Agent-FOAM variants) is moving faster than the governance layer
  that would make it trustworthy in regulated contexts. The agent
  can now write an OpenFOAM case; no product yet says "and here is
  why you can trust the case it wrote." That gap is the product.
- **The `cfd-harness-unified` codebase has crossed the maturity
  threshold** (v6.1 cutover, 10 cases green, ADWM decision discipline
  with 6 accepted decisions) where the governance layer is substrate,
  not research. Productizing now captures the compounded work; waiting
  lets it drift back toward being a private research tool.

## Differentiator versus incumbents

| Dimension | ANSYS Workbench | STAR-CCM+ | SimScale | **This product (Path B)** |
|---|---|---|---|---|
| CAD / geometry | World-class | World-class | Adequate | **Not built** (import STL/STEP + defer to imported meshes; Phase 5+ consider Salome/FreeCAD integration) |
| Mesh generation | World-class | World-class | Adequate | **Not built** (expose snappyHexMesh + cfMesh via CLI wrapper; do not compete on UX) |
| Physics breadth | Everything | Everything | Broad | **Narrow & deep** (incompressible + natural convection + RANS turbulence initially; explicitly defer compressible/multiphase/FSI to post-MVP) |
| Solver performance | Best-in-class | Best-in-class | OpenFOAM-backed | **OpenFOAM-only** via existing Foam-Agent executor |
| V&V workflow | Best-practices PDF + templates | Best-practices PDF + templates | Templates | **First-class enforced workflow** — cases cannot run without passing contract; runs cannot produce output without audit trail |
| Audit package export | Not a product feature | Not a product feature | Not a product feature | **One-click; signed zip + PDF; reviewer checklist mapping** |
| AI-drafted case setup | Roadmap item | Proprietary | Beta | **Core workflow** (agent drafts → contract gates → human approves) |
| Price point | $50k-$250k/seat/year | $50k-$250k/seat/year | $30k-$150k/seat/year | **Target $20k-$60k/seat/year** (premium vs. SimScale free tier, priced on audit-package value not seat-hours) |
| Buyer persona | CFD engineer | CFD engineer | CFD engineer | **Compliance officer buys it; CFD engineer uses it** |

The decisive column is the last row. Commercial CFD is bought by the
engineer today; regulated-CFD audit pain lands on the compliance side
of the house. This product aligns purchase authority with pain
ownership.

## Non-goals (aggressively maintained)

Path B wins by being narrow. These are explicitly **not** in scope:

- **General CAD workbench.** We import geometry, we do not author it.
- **Compressible / multiphase / reacting / FSI physics.** All out of
  MVP. Can be added post-product-market-fit if pulled by regulated
  customers with specific needs.
- **Mesh-generation UX.** `snappyHexMesh` and `cfMesh` remain CLI
  tools wrapped by the harness; we do not build a visual mesher.
- **Desktop installer / native Windows client.** Web-first. Desktop
  is a post-MVP distribution concern.
- **Free public tier.** The audit-package value proposition does
  not translate to hobbyist use; a freemium strategy would dilute
  the narrative. Trials are gated behind a compliance conversation.
- **Open-core licensing.** The UI code MAY become open source
  post-MVP; the audit-package signing + verification pipeline stays
  closed-source because it is the commercial moat.

## Commercial model hypothesis

Primary revenue: **annual per-seat subscription**, tiered by audit-
package volume (runs/month with signed export). Rough pricing ladder:

- **Solo Researcher** ($6k/year, 25 audit packages/month, single
  user): targets academic labs + 1-person consulting practices
- **Regulated Team** ($25k/year/seat, unlimited packages, 3+ seats):
  targets aerospace primes' CFD groups, medical device simulation
  teams
- **Enterprise** ($60k+/year/seat, dedicated support, SOC2, private
  deployment option): targets Tier-1 defense, big pharma, Tier-1
  auto OEMs

Secondary revenue: **per-audit-package professional services**
($5k-$25k per major validation campaign) — consulting-adjacent, used
to close deals and staff expertise. Target: 20-30% of year-1 revenue.

Target markets, ordered by ease-of-entry:
1. **FDA-regulated medical device CFD consultancies** (Dassault
   Simulia BIOVIA is the natural incumbent; our wedge is V&V40 audit
   packaging, which they do not productize)
2. **Aerospace supplier CFD groups** (Tier-2/3 suppliers to Boeing /
   Airbus / Embraer; compliance burden is disproportionately heavier
   than at primes; budget sensitivity is high)
3. **Academic + national-lab validation programs** (NASA Langley,
   DOE labs, university regulated-CFD consortia; slow sales cycle
   but high credibility)
4. **Nuclear CFD** (NQA-1 market; small but under-served)
5. **Automotive crash / FSI** (largest market but incumbents are
   entrenched; deprioritized for MVP)

## Key risks (to be validated in Phase 0..5)

- **Market-size risk**: regulated-CFD audit pain is real but the
  segment may be smaller than the $5-10M ARR required to sustain
  standalone product development. Validation: 10 discovery
  conversations with named compliance officers by end of Phase 2.
- **Build-vs-buy risk**: ANSYS may ship an audit-package feature
  in 2027-2028 once regulators push hard enough. Our counter: depth
  of domain knowledge (physics-contract library, ADWM decision
  discipline) is harder to copy than the UI is; ship in time to
  own the category name.
- **UX risk**: compliance officers are not CFD experts. If the UI
  surfaces too much solver jargon, the audit-package buyer cannot
  evaluate it in their own hands. Validation: Phase 5 audit-package
  PDF tested in blind review with a non-CFD compliance officer.
- **Solver-dependency risk**: OpenFOAM-only limits us to what
  OpenFOAM can simulate. For Phase 5+ consider adding a second
  executor (SU2, code_saturne) to de-risk; for MVP this is
  acceptable scope reduction.

## MVP definition (what "MVP complete" means)

Per DEC-V61-002, the MVP is complete when all six phases have
merged and the following acceptance demonstration passes end-to-end:

1. **Compliance officer persona** logs into the web app with SSO
2. Sees the **Project Dashboard** with 10-case contract-status matrix
3. Drills into the **differential_heated_cavity** case (known deviation)
4. Reviews the **Validation Report** showing Nu=77.82 vs ref=30.0
   with `audit_concern` explaining BL-resolution gap + Q-1 gate status
5. Opens the **Decisions Queue** and sees DEC-ADWM-004 + Q-1 external
   gate escalation with full decision trail
6. Triggers **Audit Package Export**; receives signed zip + PDF
7. Verifies HMAC signature against published verification procedure
8. Concludes review and clicks **Approve-for-External-Submission**

When that 8-step demo runs cleanly on production infrastructure with
real (not mock) OpenFOAM runs, MVP is declared complete and the
product enters its first limited-release customer pilot.

## Related documents

- `docs/ui_design.md` — information architecture, screens, visual
  language, tech stack
- `docs/ui_roadmap.md` — per-phase gate criteria, risk register,
  estimates
- `.planning/decisions/2026-04-20_path_b_ui_mvp.md` — DEC-V61-002
  formal record
- `.planning/STATE.md` — live project state (updated post-Phase-0)
- `.planning/external_gate_queue.md` — Q-1/Q-2/Q-4 external-gate
  items (UI MVP does NOT unblock Q-1/Q-2 — they remain external-gate)
