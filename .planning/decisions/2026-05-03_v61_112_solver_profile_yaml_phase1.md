---
decision_id: DEC-V61-112
title: Solver-profile YAML migration · Phase 1 — schema + registry + simpleFoam profile (V61-102 Phase 3 supersedes step 1 of 4)
status: Proposed (2026-05-03 · authored under user 2026-05-03 autonomous-mode mandate "全权授予你开发，全都按你的建议继续，执行开发")
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-03
authored_under: V61-111 closure note: "V61-102 Phase 3 (solver-profile YAML migration) should consolidate this into a single canonical parser used by all readers" + V61-102 Phase 3 explicitly deferred at V61-102 closure
parent_decisions:
  - DEC-V61-102 (M-RESCUE manual override foundation · Phase 3 deferred to follow-up DEC — this DEC supersedes step 1 of 4 phases)
  - DEC-V61-111 (iter01 numerical setup fix · simpleFoam template authored INLINE in bc_setup_from_stl_patches; V61-112 extracts that into a reusable YAML profile)
  - DEC-V61-107.5 (pimpleFoam migration · channel pimpleFoam template originally inline; eligible for profile extraction in V61-112 Phase 2 follow-up)
  - RETRO-V61-001 (risk-tier triggers · multi-file backend route + new config schema = mandatory Codex pre-merge)
parent_artifacts:
  - reports/codex_tool_reports/v61_111_r1_r2_r3_r4_chain.md (V61-111 4-round chain · methodology lesson "parser parity matters" — V61-112 implements the consolidated parser pattern)
  - ui/backend/services/case_solve/bc_setup_from_stl_patches.py:700-926 (V61-111 inline simpleFoam + pimpleFoam template helpers — extraction targets for Phase 1)
  - ui/backend/services/case_solve/bc_setup.py:450-503 (LDC inline icoFoam template — extraction target deferred to Phase 3)
  - ui/backend/services/case_solve/bc_setup.py:822-906 (channel inline pimpleFoam template — extraction target deferred to Phase 4)
counter_impact: +1 (autonomous_governance: true · architectural foundation, no external gate required)
self_estimated_pass_rate: 60% (config schema + registry loader + ONE profile is bounded scope · V61-111 lessons applied — single-source-of-truth parser, no comment-stripping mismatches, dataclass-validated schema; expect Codex 2 rounds with possible 1-2 P2 schema-validation finer points)
notion_sync_status: pending (Notion MCP offline this session; sync queued for next online window)

# DEC-V61-112 · Solver-profile YAML migration · Phase 1

## Why now

V61-111 landed inline simpleFoam templates (controlDict + fvSchemes +
fvSolution) inside `bc_setup_from_stl_patches.py:700-926` as the
focused fix to unblock V61-106 §Phase 1.3. The 4-round Codex chain
to APPROVE found 4 substantive findings, all in the
override-handling layer that V61-111 had to extend (icoFoam vs
pimpleFoam vs simpleFoam mismatch detection, parser-parity with
`/solve` dispatch). The closure note at
`reports/codex_tool_reports/v61_111_r1_r2_r3_r4_chain.md` calls out
the canonical follow-up: **consolidate the inline templates into
YAML solver profiles so the dispatcher's parser is the canonical one
all readers share**.

V61-102 §Phase 3 was deferred for the same reason: extracting
hardcoded inline Python templates into YAML profiles is a clean-up
that subsumes ~3 different inline template sites
(`setup_bc_from_stl_patches` simpleFoam + pimpleFoam, `setup_ldc_bc`
icoFoam, `setup_channel_bc` pimpleFoam) but doesn't ship new user-
facing capability. V61-112 starts that arc.

**Bounded scope discipline (V61-088 surface-scan applied):**
this DEC files Phase 1 only — schema + registry + simpleFoam
profile. Phases 2-4 (pimpleFoam profile, LDC migration, channel
migration) follow as separate DECs. Each phase preserves
byte-repro for its target paths so the migration is safe + auditable.

## Decision

Adopt a **4-phase migration** scoped per Phase to bound Codex review
surface; this DEC ships **Phase 1 only**:

### Phase 1 (THIS DEC) — schema + registry + simpleFoam profile

#### 1.1 YAML schema

New file `ui/backend/services/case_solve/solver_profiles/schema.py`
defines a frozen dataclass `SolverProfile`:

```python
@dataclass(frozen=True, slots=True)
class SolverProfile:
    name: str                         # solver binary (simpleFoam / pimpleFoam / icoFoam)
    family: Literal["steady", "transient"]  # algorithm family
    control_dict: ControlDictBlock    # controlDict params (timestep, write strategy, CFL)
    fv_schemes: FvSchemesBlock        # ddt + grad + div + laplacian + snGrad
    fv_solution: FvSolutionBlock      # solvers + control block (PIMPLE/SIMPLE/PISO)
```

Each block is a frozen dataclass with the OpenFOAM dict fields as
typed attributes. **No raw-string passthrough** — every field is
explicit, validated, and rendered to OpenFOAM dict syntax via a
single `render()` method per block. This eliminates the
copy-paste-edit pattern in the 3 inline template sites.

#### 1.2 Profile registry

New file `ui/backend/services/case_solve/solver_profiles/registry.py`
loads YAML profiles from
`ui/backend/services/case_solve/solver_profiles/profiles/*.yaml`
into the dataclass schema. API:

```python
def load_profile(name: str) -> SolverProfile:
    """Returns the SolverProfile for the named solver. Raises
    ProfileNotFoundError on unknown name. Validates the YAML
    against the schema (missing fields → ProfileSchemaError).
    """
```

Profiles ship as YAML files alongside the loader so engineers can
read + edit without Python knowledge. Each YAML contains:
- `name`, `family`, `control_dict`, `fv_schemes`, `fv_solution`
matching the dataclass schema 1:1.

#### 1.3 simpleFoam profile

New file
`ui/backend/services/case_solve/solver_profiles/profiles/simpleFoam.yaml`
extracts the V61-111 inline simpleFoam template. Acceptance gate:
the rendered OpenFOAM dicts from `load_profile("simpleFoam").render()`
must be **byte-identical** to the V61-111 inline output for the
iter01 case parameters (end_time=200, mesh-class=tetrahedral STL).

#### 1.4 V61-111 simpleFoam call site rewrite

`bc_setup_from_stl_patches.py:_build_simplefoam_*` helpers replaced
with a single call:

```python
profile = load_profile("simpleFoam")
control_dict = profile.render_control_dict(end_time=end_time)
fv_schemes = profile.render_fv_schemes()
fv_solution = profile.render_fv_solution()
```

Existing simpleFoam tests (`test_solver_name_simplefoam_*`) continue
to pass byte-identical assertions — no test changes needed.

### Phase 2 (FOLLOW-UP DEC) — pimpleFoam profile

`bc_setup_from_stl_patches.py:_build_pimplefoam_*` helpers extracted
to `pimpleFoam.yaml`. Subsumes V61-107.5 channel template too
(prep work for Phase 4). Same byte-repro acceptance gate.

### Phase 3 (FOLLOW-UP DEC) — icoFoam profile + LDC migration

`bc_setup.py:setup_ldc_bc` inline icoFoam template extracted to
`icoFoam.yaml` (with `family=transient`, `mesh-class=hexahedral
blockMesh`). LDC dogfood byte-repro mandatory.

### Phase 4 (FOLLOW-UP DEC) — channel migration

`bc_setup.py:setup_channel_bc` rewired to use the Phase 2
pimpleFoam profile. Channel dogfood byte-repro mandatory.

## Schema details (Phase 1)

### ControlDictBlock

```yaml
application: simpleFoam
start_from: startTime
start_time: 0
stop_at: endTime
end_time_kind: iterations | seconds   # simpleFoam uses iterations
end_time_default: 200                  # iter01 default
delta_t_default: 1                     # 1 iteration step for SIMPLE
write_control: timeStep | runTime
write_interval: 50
purge_write: 0
write_format: ascii
write_precision: 6
write_compression: off
time_format: general
time_precision: 6
run_time_modifiable: true
adjust_time_step: null   # null=omitted (simpleFoam doesn't use it)
max_co: null
max_delta_t: null
```

`end_time` and `delta_t` are caller-overridable at render time;
all other fields are profile-pinned (engineers customize via the
V61-102 raw-dict editor, not the profile).

### FvSchemesBlock

```yaml
ddt_schemes: { default: steadyState }
grad_schemes: { default: "Gauss linear", "grad(U)": "cellLimited Gauss linear 1" }
div_schemes:
  default: none
  "div(phi,U)": "bounded Gauss linearUpwind grad(U)"
  "div((nuEff*dev2(T(grad(U)))))": "Gauss linear"
laplacian_schemes: { default: "Gauss linear corrected" }
interpolation_schemes: { default: linear }
sn_grad_schemes: { default: corrected }
```

### FvSolutionBlock

```yaml
solvers:
  p: { solver: GAMG, tolerance: 1e-06, relTol: 0.1, smoother: GaussSeidel }
  U: { solver: smoothSolver, smoother: symGaussSeidel,
       tolerance: 1e-05, relTol: 0.1, nSweeps: 1 }
control_block:
  name: SIMPLE
  fields:
    nNonOrthogonalCorrectors: 2
    pRefCell: 0
    pRefValue: 0
    residualControl:
      p: 1e-3
      U: 1e-4
relaxation_factors:
  fields: { p: 0.3 }
  equations: { U: 0.7 }
```

The `control_block.name` field selects PIMPLE / SIMPLE / PISO at
render time. Each name dictates which other fields are renderable
(SIMPLE has residualControl + relaxationFactors; PIMPLE has
nOuterCorrectors + nCorrectors etc.). Schema enforces this via
typed sub-dataclasses for each control-block flavor.

## Impact

### Positive
- Single canonical authoring path for solver dicts replaces 3
  inline template sites
- YAML profiles human-readable + version-controlled — engineers can
  audit + propose changes without touching Python
- Future solver additions (e.g. `interFoam` for multiphase) become
  "drop a YAML, register in loader" — no Python edit
- V61-102 raw-dict editor still works (override semantics
  unchanged); profiles are the AI authoring source-of-truth, not
  a frozen output
- Eliminates the copy-paste-edit pattern that bit V61-107.5 R14/R15
  (forgot divDevReff in fvSchemes) and V61-111 (mismatched
  PIMPLE/SIMPLE blocks)

### Negative
- New file surface: 1 schema module + 1 registry module + N YAML
  profiles + tests for each
- Phase 1 ships before Phase 2-4 land → 1 inline template site
  (simpleFoam) replaced with profile call; 2 inline sites
  (pimpleFoam in stl_patches, LDC, channel) still use the legacy
  inline pattern → temporary asymmetry until follow-up DECs land
- Migration tax per phase: byte-repro verification mandatory;
  failures land as `solver_diverged` HTTP 502 at /solve time

### Counter handling
- Counter v6.1 += 1 if Status flips to Accepted
- Codex pre-merge mandatory per RETRO-V61-001 (multi-file backend
  route + new config schema)
- No Kogami review trigger (per V61-094 P2 #1 bounding clause:
  no charter mod, workbench already line-A, counter <20 since
  RETRO, no risk-tier change)

## Acceptance criteria

1. `pytest ui/backend/tests/test_solver_profiles.py` 100% pass:
   - schema validates correct YAML
   - schema rejects malformed YAML (missing fields, wrong types)
   - registry loads `simpleFoam` profile successfully
   - registry raises `ProfileNotFoundError` on unknown name
   - rendered controlDict / fvSchemes / fvSolution match V61-111
     inline output byte-identically
2. `pytest ui/backend/tests/test_bc_setup_from_stl_patches.py` 100%
   pass: existing 53 tests unchanged (V61-111 contract preserved
   via byte-repro at the rendered-text level)
3. Codex pre-merge review APPROVE / APPROVE_WITH_COMMENTS
4. Status flip Proposed → Accepted with chain report at
   `reports/codex_tool_reports/v61_112_phase_1_chain.md`

## Out of scope

- Phase 2 pimpleFoam profile extraction (follow-up DEC)
- Phase 3 icoFoam profile + LDC migration (follow-up DEC)
- Phase 4 channel migration (follow-up DEC)
- Profile editing UI (engineer edits YAML directly via filesystem
  or future raw-profile-editor; out of V61-112 scope)
- Solver-profile parameter validation against OpenFOAM dictionary
  syntax rules (the schema enforces shape; OpenFOAM enforces
  semantics at /solve time as today)
- Migration of `_detect_solver_marker_overrides` to consume
  profile metadata (current implementation already V61-111 R3
  parser-parity'd; profile integration is Phase 5+ if ever needed)

## Alternatives considered

### Alt 1 · Single big-bang migration (all 4 phases at once)
Extract all 3 inline template sites in one DEC. **REJECTED** —
~1500 LOC change touching 4 BC-setup paths simultaneously, byte-
repro verification across LDC + channel + iter01 + cylinder live
runs, Codex review surface so large that 5-6 round chain is
likely. V61-088 surface-scan + V61-088 §11.4 quota awareness
both argue for bounded phases.

### Alt 2 · Skip the migration; document the inline pattern as canonical
Accept that 3 inline template sites is acceptable and document
the pattern as "solver-specific authoring lives in the bc_setup
module that owns the case-class". **REJECTED** — V61-107.5 R14/R15
+ V61-111 R1 prove the pattern produces real defects when copy-
paste-edit gets a field wrong. The single-source-of-truth gain is
worth the migration tax.

### Alt 3 · Use Python-native config (e.g. dataclass-only, no YAML)
Skip the YAML layer; profiles are pure Python dataclasses imported
at startup. **REJECTED** — engineers can't audit profile choices
without reading Python. YAML is the standard CFD-config format
(OpenFOAM tutorials ship YAML companion files for case
parameterization); this aligns with the user's expected mental
model.

**Selected**: Alt 4 (this DEC) — phased YAML migration, Phase 1
ships schema + registry + simpleFoam only.

## Process note

V61-112 Phase 1 explicitly applies the V61-088 pre-implementation
surface scan rule:

`Surface-scan-found: ui/backend/services/case_solve/bc_setup_from_stl_patches.py:700-926 (V61-111 inline simpleFoam template helpers) + ui/backend/services/case_solve/bc_setup.py:450-503 (LDC icoFoam) + ui/backend/services/case_solve/bc_setup.py:822-906 (channel pimpleFoam) · disposition: refactor existing (Phase 1 extracts simpleFoam only; Phases 2-4 follow)`

V61-112 is the canonical "consolidate parser/authoring across
multiple sites" pattern V61-111 closure recommended. Future
similar discoveries (e.g. multiple sites computing the same mesh
metric, multiple sites parsing the same log format) should follow
the same phased-migration discipline rather than big-bang
refactor.
