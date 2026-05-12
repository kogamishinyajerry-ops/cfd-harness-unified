# Industrial Component Bank · Codex Case-Design Menu

> **What this is.** A taxonomy of realistic industrial CFD
> components, organized by solver class. When the main session asks
> Codex to design a new case, Codex picks **one component** from this
> bank, designs it via local CAD tooling (CadQuery / FreeCAD CLI),
> and outputs a STEP file with **intentional defects** to mimic real
> industrial CAD ingest reality.
>
> **Why this exists.** My original `case_list.md` (deleted 2026-05-07
> by user reframe) used canonical academic benchmarks (Ahmed body,
> NACA airfoil, Sajben diffuser) — these come from "out-of-the-box
> designed" research cases and bypass the project's actual
> industrial-CFD reality (CATIA-style multi-body STEP with imperfect
> exports). Real value comes from cases that **start with messy
> CAD**, because that's what the harness must handle.

## How Codex uses this bank

When asked "design a new case in solver-class X with industrial
flavor", Codex must:

1. **Pick one component** from the matching solver-class table below
2. **Generate it via CadQuery** (preferred) or FreeCAD CLI (fallback)
3. **Inject 1-2 intentional defects** from the Defect Catalog (§ Defect catalog)
4. **Output 5 deliverables** per `codex_case_design_protocol.md`

Codex MAY propose a component NOT in this bank if it has good
industrial-flavor justification, but should default to the bank for
predictability.

## Bank organization

Components grouped by **fluid-internal numerics class** (per V-series
Pattern 6) — not by solver name. This makes V-finding inheritance
explicit: a new case in class X inherits all V-findings tagged X
regardless of solver.

---

## Class A · incompressible-RANS (external & internal high-Re, no thermal coupling primary)

Solver candidates: `simpleFoam`, `pisoFoam` steady, `pimpleFoam` transient.

| # | Component | Industrial sector | Geometric complexity | Why interesting |
|---|---|---|---|---|
| A1 | **Plate-fin heat sink** (CPU / power-electronics cooler) | Electronics thermal | 5-15 named solids (base + N fins) | Multi-body, narrow gaps between fins, Reynolds 10³-10⁵ depending on fan |
| A2 | **Centrifugal fan housing (volute, no impeller)** | HVAC, automotive | 2-3 bodies (housing + cutwater + outlet duct) | Spiral channel, sharp cutwater edge, non-axisymmetric |
| A3 | **Manifold with 3-4 branches** (intake / exhaust / coolant) | Automotive, marine | 3-5 bodies | Branching with non-orthogonal angles, plenum-junction boundary layer separation |
| A4 | **Bicycle / motorcycle frame** (downsampled aero hull) | Sports / consumer | 3-6 bodies (down tube + top tube + seat tube + wheels-as-disc) | Bluff-body external aero with multi-component interaction |
| A5 | **Submarine periscope / antenna mast in cross-flow** | Defense / marine | 1-3 bodies (mast + base + fairing) | Bluff-body with attachment, vortex shedding |

Defect-injection sweet spots:
- A1 fin spacing: gap < 2 mm between adjacent fin shells (V10 / thin-wall trap)
- A2 cutwater: vertex-coincident sliver on the spiral-to-outlet transition
- A3 branch junction: non-watertight at the merge (V2 BREP face mismatch)

---

## Class B · compressible-buoyant-RANS (internal flow with strong heat sources)

Solver candidates: `buoyantSimpleFoam`, `buoyantPimpleFoam`, `chtMultiRegion*Foam`.

Inherits V3-V13 from APU bay (case_002a). Pattern 6 cascade:

| # | Component | Industrial sector | Geometric complexity | Why interesting |
|---|---|---|---|---|
| B1 | **Server rack with multiple heat sources** | Data center cooling | 5-10 bodies (chassis + boards + drives) | CHT-friendly extension (case_002b precedent), multi-T heat sources |
| B2 | **Engine bay (simplified)** | Automotive | 4-8 bodies (engine block + manifold + turbo + accessories) | Hot-component venting, similar to APU bay topology but new geometry |
| B3 | **LED street-light heat dissipation assembly** | Lighting | 3-6 bodies (LED chip + pad + housing + heat sink) | Multi-scale (mm chip + cm fins) thermal coupling |
| B4 | **Microwave oven cavity with food load** | Appliance | 2-3 bodies (cavity + waveguide + dielectric load — load = thermal source) | Convective cavity flow with cyclic forcing approximation |
| B5 | **Industrial oven with conveyor product** | Manufacturing | 3-5 bodies (chamber + heaters + product slabs) | Forced + buoyant convection in mixed regime |

---

## Class C · external-high-Re-RANS (specifically aero / hydro external, may overlap A4/A5)

Solver candidates: `simpleFoam`, `pimpleFoam` (transient).

| # | Component | Industrial sector | Geometric complexity | Why interesting |
|---|---|---|---|---|
| C1 | **Truck side-mirror + housing** | Automotive aero | 2-4 bodies (mirror glass + housing + arm + bracket) | Bluff-body external, separation around housing, real CAD complexity |
| C2 | **Wind turbine blade root + fairing junction** | Renewable energy | 2-3 bodies | Where blade meets hub — high curvature transition with stall potential |
| C3 | **UAV fuselage + wing junction (simplified)** | Aerospace | 3-5 bodies | Wing-body junction vortex, classic aerospace headache |
| C4 | **Building array (array of 3-5 buildings)** | Civil / urban wind | 3-5 boxes with details | Urban canyon flow, sheltering effects |

---

## Class D · rotating-machinery (MRF or sliding-mesh)

Solver candidates: `simpleFoam` + MRF, `pimpleFoam` + AMI.

| # | Component | Industrial sector | Geometric complexity | Why interesting |
|---|---|---|---|---|
| D1 | **Centrifugal pump impeller + volute (full)** | Process / water treatment | 2 bodies (impeller + volute) + cellZone | Standard rotating-machinery validation, head-vs-flow curve |
| D2 | **Mixer tank with paddle / Rushton turbine** | Chemical process | 2-3 bodies (tank + impeller + baffles) | Steady MRF good v1, sliding-mesh later |
| D3 | **Cooling fan in shroud** (CPU or industrial) | Electronics / HVAC | 2 bodies (fan blades + shroud) | Lower Re than D1, simpler geometry |
| D4 | **Marine propeller in open water** | Marine | 1-2 bodies (propeller + hub) | Free-stream rotating, thrust prediction |

---

## Class E · compressible-shock-density-based (transonic / supersonic)

Solver candidates: `rhoCentralFoam`, `sonicFoam`.

| # | Component | Industrial sector | Geometric complexity | Why interesting |
|---|---|---|---|---|
| E1 | **Converging-diverging nozzle** | Aerospace / chemical | 1 body (axisymmetric) | Classical Mach 1 transition, shock at design Mach |
| E2 | **Supersonic intake (oblique-shock + normal-shock)** | Aerospace | 2-3 bodies | Multi-shock interaction, real intake geometry |
| E3 | **Steam-turbine stator vane (single passage)** | Power generation | 2-3 bodies (vane + endwalls) | Transonic blade passage, periodic boundaries |

---

## Defect catalog (intentional injection)

Real industrial CAD has **systematic defects** that the harness
must handle. Codex must inject 1-2 of these per case to keep
sub-session V-series productive.

| Defect | What it looks like | Mimics | Test value |
|---|---|---|---|
| **D1 · sub-mm gap between bodies** | Two adjacent solids meant to mate, separated by 0.1-0.5 mm gap | CATIA assembly tolerance drift | sHM merges or leaves sliver — V8 / V10 |
| **D2 · over-dense triangulation** | One body has 100k+ faces when 5k would suffice | CATIA "fine" tessellation default | A3 geometry surgery is exercised — V8 |
| **D3 · non-manifold shared face** | Two bodies share an interface but the faces are NOT identical (different parametric directions / vertex orderings) | CATIA non-manifold export | A2 virtual-interface-detector exercised — V2 |
| **D4 · sliver on a spiral / fillet edge** | Tiny degenerate face at curvature transition | CAD boolean operation rounding | sHM concave / max-skewness — V8 |
| **D5 · slightly mis-aligned shared face** | Bodies "share" a face but offset by 1-5 μm | Boolean tolerance error | Same as D3 but harder to detect — V2 |
| **D6 · floating tiny body** | Stray debris solid (e.g., 1mm cube floating) inside the assembly | CAD history not cleaned up | patch_detector + STL ingest robustness |
| **D7 · wrong-normal-direction face** | A face has reversed normal (inside ↔ outside flipped) | CAD boolean failure | sHM `locationInMesh` ambiguity |
| **D8 · sub-mm thin shell** | One body is 0.5-2 mm thick (e.g., a heat sink fin) | Real industrial thin features | thin_wall_advisor exercised — V10 |
| **D9 · over-aggressive simplification** | A curved surface approximated by 4-6 facets | CAD "low" tessellation | sHM blob, false geometry |
| **D10 · open shell (non-watertight)** | A body has missing faces — open hole | CAD repair incomplete | STL `health_check` watertight = false |

**Codex picks 1-2 defects per case** from this catalog, documents
them in the defect manifest, and the sub-session's job is to (a)
detect the defect via main-project advisors, (b) work around it,
and (c) report whether the advisor caught it pre-meshing.

This is how we **stress-test main project's CAD-handling
capabilities case-by-case**.

---

## Lane B · Validation references (occasional, NOT primary substrate)

Used only when we want to validate a main-project capability
against a published benchmark. NOT the primary case roster.

| # | Validation case | What it validates |
|---|---|---|
| LB1 | Ahmed body 25°/35° | y+ advisor accuracy, Cd parity with wind tunnel |
| LB2 | NACA 0012 airfoil at Re=6×10⁶ | Cl/Cd parity with NASA TMR |
| LB3 | Backward-facing step (Driver-Seegmiller) | Reattachment length, RANS verification |
| LB4 | Sajben transonic diffuser | Shock capture, compressible-RANS verification |
| LB5 | Ercoftac mixing tank with Rushton | Rotating-frame validation |

These run when we explicitly need a benchmark check; they do NOT
flow through the Codex case-design protocol.

## Update cadence

Update this bank when:
- A new solver class is added (new section)
- A new defect category emerges from a real case (new row in catalog)
- A component is run multiple times across cases — promote to
  "frequently selected" annotation
- User flags a real industrial component they want represented
  (add to relevant class)

## References

- `codex_case_design_protocol.md` — what Codex returns when picking
  from this bank
- `case_proposal_queue.md` — case roster (Codex-fed, Lane A)
- `industrial_case_solver_findings.md` — V-series (defect catalog
  rows back-link to V-findings the defects exercise)
- DEC-V61-198 — strategic philosophy SSOT
