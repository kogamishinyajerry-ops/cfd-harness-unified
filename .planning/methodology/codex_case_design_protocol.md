# Codex Case-Design Protocol

> **Purpose**: define the contract between the project main session
> and Codex (acting as case 出题者). Codex designs an industrial CFD
> case — picks a real-flavored component, generates the CAD via
> local tooling, injects intentional defects, writes the engineering
> brief — and hands it back as 5 deliverables. Main session validates
> Codex output and dispatches it to a sub-session for execution.
>
> **Why this exists**: established 2026-05-07 evening per user reframe
> ("you should pair with Codex as 出题者, drive local CAD, inject
> defects"). Replaces the original `case_list.md` static-roster
> model.

## Three-actor split (clarified)

| Actor | Role | Outputs |
|---|---|---|
| **Project main session** (Claude Code, this session) | Orchestrator + harvester | Codex prompts; sub-session kickoffs; harvest sediment back to V-series + advisor + corpus |
| **Codex** (gpt-5.4 / 5.5 / 5.3-codex via codex-relay) | Case designer / 出题者 | Engineering brief + CAD generation script + STEP file + parts manifest + defect manifest |
| **Sub-session** (Claude Code, fresh terminal per case) | Case executor | OpenFOAM run + V-series sediment + reference profile + final report |

## What main session asks Codex (request schema)

When main session decides to enqueue a new case, it sends Codex a
structured request via codex-relay. The request includes:

```yaml
case_id: case_<NNN>_<short_name>
solver_class_target: <one of: incompressible-RANS, compressible-buoyant-RANS,
                              external-high-Re-RANS, rotating-machinery,
                              compressible-shock-density-based, ...>
component_bank_pick:
  preferred: <component bank ID, e.g. A1 plate-fin heat sink>
  alternative_ok: true | false
defect_injection_count: 1 | 2
defect_injection_hint: <one or two defect catalog IDs from defect catalog>
cad_tool_preference: cadquery | freecad | open
sandbox_path_suggestion: ~/Desktop/case_<NNN>_<short_name>/
non_negotiables:
  - geometry must export valid STEP that FreeCAD `Import.insert` can read with named bodies preserved
  - parts manifest names must satisfy OpenFOAM patch naming (^[A-Za-z][A-Za-z0-9_]*$)
  - injected defects must be in defect catalog (D1..D10) and documented in defect manifest
  - solver class must match target; mismatch = invalid
  - defects must be REAL (not just declared) — the CAD as exported must actually contain the defect
verification_steps_main_session_will_run:
  - cadquery script executes deterministically
  - STEP file opens in FreeCAD without errors
  - parts manifest names match STEP body labels
  - defect manifest claims match STEP geometry (e.g. claimed "sub-mm gap" → measure inter-body min distance < 0.5 mm)
```

Main session then formats a Codex prompt that asks for the 5
deliverables below.

## CAD source priority (public sources first, generation as fallback)

**2026-05-07 evening user addendum**: Codex must check public
aerospace CAD repositories **before** generating from scratch.
Real industrial components from NASA / ONERA / DLR / NREL etc.
are higher fidelity than anything Codex can generate ad-hoc, AND
they come with reference data + community history that aids
V-finding interpretation.

Priority cascade:

1. **Tier 1 · published reference geometries** (NASA CRM, DLR-F6,
   ONERA M6, NREL wind turbine, NASA E3 engine concepts, ...)
   → see `public_cad_sources.md` for the curated catalog
2. **Tier 2 · open community libraries** (GrabCAD industrial-aero
   tag, FreeCAD library, OpenSCAD aerospace) — sanity-check
   license + quality before consuming
3. **Tier 3 · Codex from-scratch generation via CadQuery / FreeCAD
   CLI** — fallback when Tier 1/2 doesn't fit the requested
   solver-class + component combo

Defect injection still applies regardless of source — even a
NASA CRM STEP may need a controlled defect injection (e.g.,
deliberately introduce a sub-mm gap at the wing-body junction)
to keep V-series productive. Public sources are starting material;
they're not exempt from "real industrial CAD has imperfections".

Codex's case-design response must report:
- Which tier the geometry came from
- If Tier 1/2: source URL + license + quality assessment
- If Tier 3: justification (why no Tier 1/2 fit)
- Defect injection plan (catalog IDs) + how injected (post-import
  CadQuery boolean ops on Tier-1 STEP, or built-in for Tier-3)

## What Codex returns (5 deliverables)

### Deliverable 1 — Engineering brief (Markdown)

Single file, plain markdown. Sections:

1. **Component picked** + bank ID + why this component fits the
   solver-class
2. **Engineering question**: 1-2 sentence problem statement (what
   does the engineer want to know?)
3. **Physics signature**: solver target, expected Reynolds /
   Mach / Prandtl / Grashof, expected regime
4. **Parts inventory**: list of named bodies in the assembly with
   their CFD role (wall_hot / wall / inlet / outlet / symmetry /
   farfield)
5. **Boundary conditions plan**: per-patch BC type + expected
   value (mass flow / pressure / temperature)
6. **Expected metrics to report**: e.g., ΔP, Cd, max wall T,
   convergence behaviour
7. **Hypothesized failure modes** (Codex's prediction of which
   V-series findings the case will surface based on the geometry
   + defects)
8. **Defect injection summary**: which catalog defects (1-2) were
   injected and why
9. **Sub-session estimated effort**: hours / version count

### Deliverable 2 — CAD generation script (Python, executable)

A standalone `.py` file using **CadQuery** (preferred) or
**FreeCAD CLI subprocess** (fallback). Requirements:

- **Deterministic**: running it twice produces byte-identical STEP
- **Self-contained**: declares all dependencies at top; uses only
  CadQuery/build123d/FreeCAD + numpy
- **Parametric**: key dimensions are named module-level constants
  so reviewer can vary them
- **Comments at decision points**: each non-trivial geometric
  operation (boolean union, fillet, defect injection) has a 1-line
  comment explaining intent
- **Exit code 0 on success**, non-zero on error
- **Output**: writes STEP file to a path passed via CLI arg

Example skeleton:

```python
"""case_NNN_<name> · CAD generator (CadQuery)
Designed by Codex per cfd-harness-unified case-design protocol.
"""
import argparse
import cadquery as cq

# === Parameters (named constants for reviewer override) ===
BODY_LENGTH_MM = 200.0
FIN_HEIGHT_MM = 30.0
FIN_THICKNESS_MM = 1.5
FIN_GAP_MM = 4.0  # nominal — defect injection mutates this for one fin
NUM_FINS = 8
DEFECT_GAP_FIN_INDEX = 3   # which fin gets the sub-mm gap defect
DEFECT_GAP_OFFSET_MM = 0.3 # the defect: this fin sits 0.3 mm offset from its slot

def build():
    base = cq.Workplane("XY").box(BODY_LENGTH_MM, 60.0, 5.0).val()
    fins = []
    for i in range(NUM_FINS):
        x = (i - NUM_FINS/2) * (FIN_THICKNESS_MM + FIN_GAP_MM)
        if i == DEFECT_GAP_FIN_INDEX:
            x += DEFECT_GAP_OFFSET_MM   # injected defect D1
        fin = cq.Workplane("XY", origin=(x, 0, 5.0)).box(
            FIN_THICKNESS_MM, 60.0, FIN_HEIGHT_MM
        ).val()
        fins.append(fin)
    # ... assemble + name bodies + return
    return assembly

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()
    asm = build()
    asm.save(args.out, exportType="STEP")
```

### Deliverable 3 — STEP file (binary artifact)

Output of running deliverable 2. File path:
`<sandbox>/inputs/cad_codex_v1.step`

The sub-session may regenerate from deliverable 2; the STEP from
Codex's run is the canonical reference (verifies determinism).

### Deliverable 4 — Parts manifest (YAML)

Lists every named body in the STEP + its CFD role. Format:

```yaml
case_id: case_<NNN>_<name>
cad_source: codex-designed (cadquery)
generation_script: scripts/build_cad.py
step_file: inputs/cad_codex_v1.step
units_in_step: mm  # convert in stl_loader if needed
parts:
  - name: heat_sink_base
    role: wall_hot
    expected_T: 350  # K
    notes: "primary heat-source surface"
  - name: fin_0
    role: wall_hot
    expected_T: 350
  - name: fin_1
    role: wall_hot
    expected_T: 350
  # ...
  - name: inlet
    role: mass_flow_inlet
    mdot: 0.05  # kg/s
    T_in: 298   # K
  - name: outlet
    role: pressure_outlet
    p_gauge: 0
  - name: domain_walls
    role: wall_adiabatic
patch_naming_check:
  - all names match ^[A-Za-z][A-Za-z0-9_]*$  # OpenFOAM rule
  - no duplicate names
  - no spaces or hyphens
```

### Deliverable 5 — Defect manifest (YAML)

Documents the intentional defects. Sub-session uses this as a
**ground-truth checklist**: did the main-project advisors detect
these defects pre-meshing?

```yaml
case_id: case_<NNN>_<name>
defect_count: 2
defects:
  - id: D1  # from defect catalog
    description: "sub-mm gap between fin_3 and base"
    location:
      bodies_involved: [base, fin_3]
      coords_mm: [x=12, y=0, z=5]  # approximate gap location
    measurement:
      claimed_gap_mm: 0.3
      verification_command: "freecad --console -c <script that measures min distance>"
    expected_advisor_to_catch: virtual_interface_detector  # or thin_wall_advisor, etc.
    hypothesized_v_series_match: V2  # or V8 / V10 etc.
  - id: D8
    description: "fin_5 thickness reduced to 0.8 mm (sub-mm thin shell)"
    location:
      bodies_involved: [fin_5]
    measurement:
      claimed_thickness_mm: 0.8
    expected_advisor_to_catch: thin_wall_advisor
    hypothesized_v_series_match: V10
```

## Main session validation step (between Codex output and sub-session dispatch)

Before pasting the kickoff into a sub-session, main session runs:

1. **Run the CadQuery script** in a temp dir — does it execute
   cleanly? Does it produce a STEP file?
2. **Open the STEP** with FreeCAD CLI (`FreeCADCmd -c <verify
   script>`) — does it import? Are body names preserved?
3. **Cross-check parts manifest names** against actual STEP body
   labels — match?
4. **Verify defect claims** — measure inter-body min distance for
   D1 / face count for D2 / etc. The defect must actually exist,
   not just be claimed
5. **Patch-name regex check** — all names match
   `^[A-Za-z][A-Za-z0-9_]*$`
6. **Solver-class match** — does the engineering brief actually
   target the requested solver class?

If any check fails → main session asks Codex to fix (round-cap=2
per v2.3 governance). After 2 rounds, escalate to user or fall
back to a different component bank pick.

If all checks pass → main session writes the case-specific kickoff
prompt (using the template) and presents to user for sub-session
dispatch.

## Codex backend selection

Per project model-routing rules (v2.3):

| Codex backend | When |
|---|---|
| **86gs `gpt-5.5` (xhigh)** | Primary — case-design needs strong architectural reasoning + valid CadQuery |
| **86gs `gpt-5.3-codex` (xhigh)** | Fallback if 5.5 hits rate limit — pure codegen sweet spot |
| **86gs `gpt-5.4` (xhigh)** | Self-pass-rate baseline if 5.5/5.3 unavailable |
| **CRS `gpt-5.4` (high)** | Only if 86gs entirely down — cost-saving fallback |

Invocation: `codex-relay-with gpt-5.5 "<prompt>"` for one-shot
case-design. The full request goes in one prompt; Codex returns
all 5 deliverables in one structured response.

## Per-case kickoff prompt structure (after Codex validation)

Once Codex output passes validation, main session writes:

`.planning/methodology/kickoff/case_<NNN>_<name>.md`

This file:
1. Inherits the standard `case_kickoff_prompt_template.md` body
2. Inserts Codex's brief as the case-specific section
3. Points at the validated CadQuery script + STEP + manifests
4. Adds an "expected defect verification" checklist (sub-session
   confirms defects are detected by advisors)

Sub-session is then dispatched with this kickoff.

## Round-cap on Codex revisions

Per v2.3 governance: round cap = 3 revisions per Codex case
design. If after 3 revisions the case still fails validation,
escalate to user (the case is designed-out, not us-being-picky).

Most cases land in 1-2 rounds; pathological cases may need 3.

## Where Codex outputs land in the repo

```
.planning/
├── methodology/
│   ├── codex_case_design_protocol.md   ← this file
│   ├── component_bank.md
│   ├── case_kickoff_prompt_template.md
│   └── kickoff/
│       ├── case_003_<name>.md          ← kickoff for sub-session
│       ├── case_003_<name>_codex_request.md  ← prompt sent to Codex
│       ├── case_003_<name>_codex_response.md ← Codex's brief (deliverable 1)
│       └── case_003_<name>_validation.md     ← main session's validation report
└── case_proposal_queue.md
```

CadQuery script + STEP + manifests live in the **sub-session's
desktop sandbox** at `~/Desktop/case_<NNN>_<name>/inputs/` — not in
the main repo (heavy artifacts; case-thread owns them).

## What this protocol does NOT do

- Does NOT replace the case execution (sub-session still runs the
  case end-to-end; Codex only designs)
- Does NOT have Codex pick the solver class (main session decides
  what solver-class the next case targets, based on coverage map)
- Does NOT bypass the kickoff template (Codex's brief becomes the
  case-specific section; the template's hard guardrails still apply
  to sub-session)
- Does NOT make Codex an authority on numerics (Codex may suggest
  solver settings; sub-session decides actual values per
  solver_convergence_playbook)

## Update cadence

Update this protocol when:
- A new validation step proves necessary from a failed Codex output
- A defect catalog row is added (cross-link in defect injection)
- A new CAD tool is added to the toolchain (currently CadQuery
  primary, FreeCAD CLI fallback)
- Round-cap behavior changes

## References

- `component_bank.md` — Codex's menu of components
- `case_kickoff_prompt_template.md` — sub-session briefing
- `case_proposal_queue.md` — Codex-fed roster (replaces case_list.md)
- DEC-V61-198 — strategic philosophy SSOT
- ~/CLAUDE.md model-routing v2.3 — Codex backend selection
