# Codex Case-Design Request · case_003

> **Status**: drafted 2026-05-07 evening; **NOT yet sent to Codex**.
> Awaiting user confirmation before invoking
> `codex-relay-with gpt-5.5`.
>
> **What this is**: the prompt main session will send to Codex
> (acting as case 出题者) to design case_003. Codex's response will
> be saved at `kickoff/case_003_codex_response.md` and validated
> per `codex_case_design_protocol.md` §"Main session validation
> step" before being formatted into a sub-session kickoff.

## Target

| field | value |
|---|---|
| case_id | `case_003_<short_name>` (Codex picks short_name) |
| solver_class_target | external high-Re + boundary layer (incompressible-RANS) |
| numerics_class | incompressible-RANS (root, no inheritance) |
| coverage map row to fill | "External flow + high-Re + boundary layer" — currently 🟧 NOT YET COVERED |
| CAD source priority | Tier 1 (public aerospace reference) preferred; Tier 3 (CadQuery from-scratch) fallback |
| defect injection count | 2 |
| sandbox path suggestion | `~/Desktop/case_003_<short_name>/` |

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 (case designer) for the
cfd-harness-unified project. The project main session is asking
you to design ONE industrial CFD case end-to-end so a Claude Code
sub-session can execute it.

This is your design task, not your solver task. You design; the
sub-session runs.

## Project context (read first)

cfd-harness-unified is a CFD harness over OpenFOAM. Per
DEC-V61-198 (2026-05-07 strategic charter), the project's
development philosophy is "container that accumulates industrial
CFD experience" — each industrial case extends a solver-class
coverage axis and feeds the V-series finding index.

Two cases are already covered:
- case_002a (APU bay buoyantSimpleFoam, internal flow + buoyancy)
- case_002b (APU bay CHT, multi-region thermal coupling)

The next solver-class target is **external high-Re + boundary
layer** — currently uncovered. You design case_003 to fill this
row.

## Required reading (in cfd-harness-unified repo)

Read these in order before designing:
1. `.planning/methodology/codex_case_design_protocol.md` — your
   contract (5 deliverables + validation steps)
2. `.planning/methodology/component_bank.md` — Tier-3 fallback
   menu (you may pick from this if Tier 1 doesn't fit)
3. `.planning/methodology/public_cad_sources.md` — Tier 1+2
   catalog (PRIORITY — check first)
4. `.planning/case_profiles/case_002a_apu_bay_buoyant_simple.md`
   AND `case_002b_apu_bay_cht.md` — examples of the case-thread
   pattern your design will inherit
5. `.planning/methodology/industrial_case_solver_findings.md` —
   V-series; note Pattern 6 (numerics-class inheritance). Your
   design is incompressible-RANS so it inherits NONE of the
   compressible-buoyant-RANS findings (V3-V13, V15) — those won't
   apply

## Hard constraints

1. **Solver class**: external high-Re + boundary layer
   (incompressible-RANS). Solver target is `simpleFoam` (steady)
   or `pimpleFoam` (transient if v2 needs it)
2. **CAD source priority**: Tier 1 first (NASA CRM / ONERA M6 /
   DLR-F6 / NACA Trap Wing / DPW-W1 / etc. from
   public_cad_sources.md). Tier 3 fallback only if no Tier 1 fits
3. **Defect injection**: exactly 2 defects from defect catalog
   (D1-D10 in component_bank.md). Document in defect manifest
4. **Patch naming**: all body names must satisfy
   `^[A-Za-z][A-Za-z0-9_]*$` (OpenFOAM rule)
5. **Determinism**: CadQuery script must regenerate byte-identical
   STEP given identical inputs
6. **Industrial flavor**: case must be recognizable as a real
   industrial component, not a contrived academic toy
7. **Reference-data preservation** (if Tier 1): inject defects in
   regions OUTSIDE published experimental measurement zones; note
   `reference_data_validity` in defect manifest

## Your 5 deliverables

Per codex_case_design_protocol.md §"What Codex returns", produce:

### 1. Engineering brief (Markdown)

Sections (mandatory): Component picked + bank ID / Engineering
question / Physics signature / Parts inventory / Boundary conditions
plan / Expected metrics / Hypothesized failure modes (V-findings
prediction) / Defect injection summary / Sub-session estimated
effort.

### 2. CAD generation script (Python, executable)

CadQuery preferred; FreeCAD CLI subprocess fallback only if
CadQuery cannot express the geometry. Script must:
- Be deterministic
- Take `--out <path>` CLI arg
- Include parameters as named module constants
- Have 1-line comments at decision points
- Fetch from cache if Tier 1 (public source); generate locally if
  Tier 3
- Inject the 2 defects programmatically (not as accidents)
- Export STEP at the path

### 3. STEP file path

The output path the script writes to. Sub-session will run the
script themselves and compare; you provide the canonical reference.

### 4. Parts manifest YAML

Per protocol schema. Body-name → CFD-role mapping covering all
patches (walls + inlet + outlet + symmetry + farfield).

### 5. Defect manifest YAML

Per protocol schema. For each of the 2 defects:
- Catalog ID (D1..D10)
- Description + location
- Measurement + verification command
- Expected advisor to catch it
- Hypothesized V-series match

## Format your response

Wrap your full response in clear section headers:

```
## Deliverable 1 — Engineering brief
<markdown>

## Deliverable 2 — CAD generation script
```python
<full script>
```

## Deliverable 3 — STEP file path
<single path string>

## Deliverable 4 — Parts manifest
```yaml
<full yaml>
```

## Deliverable 5 — Defect manifest
```yaml
<full yaml>
```
```

## Round budget

The main session will validate your output. If validation fails
(STEP doesn't open, patch names invalid, defect not actually
present, etc.), you get up to 2 revision rounds before the case
is escalated to user.

## What you should NOT do

- Do NOT design the case to be easy. Industrial CAD is messy;
  keep the messiness
- Do NOT skip the defect injection — that's explicit value, not a
  bug
- Do NOT pick Ahmed body / NACA airfoil / Sajben diffuser —
  these are Lane B validation references, not Lane A industrial
  cases. Tier 1 picks like NASA CRM / ONERA M6 / DLR-F6 are valid
- Do NOT write a CAD script that requires interactive GUI input —
  must run headless via `python build_cad.py --out <path>`
- Do NOT propose new defect types not in the catalog (D1-D10 in
  component_bank.md). If you think a new defect class is needed,
  flag it in your response separately as "catalog extension
  proposal"

## Begin
```

## Validation checklist (main session runs after Codex responds)

Before writing the per-case kickoff:

- [ ] CAD source picked (Tier 1 / 2 / 3 declared)
- [ ] If Tier 1: source URL valid + license confirmed
- [ ] Component picked (matches solver-class)
- [ ] CadQuery script executes locally (`python build_cad.py
      --out /tmp/test.step`)
- [ ] Generated STEP opens in FreeCAD without errors
- [ ] FreeCAD reports body count + names matching parts manifest
- [ ] All patch names satisfy `^[A-Za-z][A-Za-z0-9_]*$`
- [ ] Both injected defects measurable in geometry (run defect
      verification commands)
- [ ] Defect manifest field `expected_advisor_to_catch` references
      a real main-project advisor (`thin_wall_advisor`,
      `virtual_interface_detector`, `geometry_surgery`,
      `mass_conservation_pre_flight`, `patch_detector`,
      `stl_loader.health_check`)
- [ ] BC plan is OpenFOAM-valid (no impossible combinations)
- [ ] Engineering brief targets external-RANS solver class

## If validation fails

Send revision request to Codex with the specific failed checks.
Round-cap: 2 revision attempts.

## After validation passes

1. Save Codex response at
   `kickoff/case_003_codex_response.md`
2. Format per-case kickoff at `kickoff/case_003_<name>.md`
   (template + Codex brief slot)
3. Update `case_proposal_queue.md` with row in Dispatched section
4. Tell user: "case_003 kickoff ready. Open new Claude Code
   session and paste contents of `kickoff/case_003_<name>.md`."

## Why this is request, not yet sent

Per project governance (and user pattern), main session does NOT
fire external Codex calls without explicit user confirmation.
Cost / accountability dictate the user OK's the prompt before it
goes out. Once user confirms, main session runs:

```bash
codex-relay-with gpt-5.5 < .planning/methodology/kickoff/case_003_codex_request.md
```

and saves the response.
