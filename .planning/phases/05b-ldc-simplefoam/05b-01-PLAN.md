---
phase: 05b-ldc-simplefoam
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/foam_agent_adapter.py
autonomous: true
requirements:
  - LDC-SOLVER-SWAP
  - LDC-MESH-129
  - LDC-FRONTANDBACK-EMPTY

must_haves:
  truths:
    - "Generated case dir's system/controlDict contains `application     simpleFoam;`"
    - "Generated case dir's system/fvSchemes contains `ddtSchemes` with `default steadyState;`"
    - "Generated case dir's system/fvSolution contains a `SIMPLE` block (not `PISO`) with `consistent yes;`"
    - "Generated case dir's system/blockMeshDict uses 129×129 mesh (hex ... (129 129 1) simpleGrading (1 1 1))"
    - "Generated case dir's system/blockMeshDict has a `frontAndBack` patch of type `empty`; `wall3` and `wall4` z-face wall patches are removed"
    - "Generated case dir's 0/U + 0/p declare `frontAndBack` with type `empty` and no longer declare `wall3` / `wall4`"
    - "FoamAgentExecutor._is_lid_driven_cavity_case dispatcher still routes both `simpleFoam` and (historical) `icoFoam` requests to _generate_lid_driven_cavity"
  artifacts:
    - path: "src/foam_agent_adapter.py"
      provides: "_generate_lid_driven_cavity emits simpleFoam case; _render_block_mesh_dict 129×129 + frontAndBack empty"
      contains: "application     simpleFoam"
  key_links:
    - from: "src/foam_agent_adapter.py::_generate_lid_driven_cavity"
      to: "src/foam_agent_adapter.py::_render_block_mesh_dict"
      via: "direct call at the top of the generator"
      pattern: "self._render_block_mesh_dict\\(task_spec\\)"
    - from: "_render_block_mesh_dict"
      to: "frontAndBack empty patch"
      via: "inline string template with 129 129 1 block cell count and frontAndBack patch"
      pattern: "frontAndBack\\s*\\{[\\s\\S]*?type\\s+empty"
---

<objective>
Rewrite the `lid_driven_cavity` OpenFOAM case generator in `src/foam_agent_adapter.py` so it emits a simpleFoam (steady-state SIMPLE) case instead of icoFoam (transient PISO). Mesh goes from 20×20 to 129×129 to match Ghia 1982. z-faces switch from `wall` patches to a single `frontAndBack empty` patch (standard OpenFOAM 2D pseudo-3D pattern). All physical parameters (Re, nu, U_lid, convertToMeters) remain parametric via TaskSpec.

Purpose: Phase 5a shipped a real-solver audit pipeline but LDC fails against Ghia 1982 because icoFoam transient + 20×20 mesh does not reach steady state in a viable wall-time budget. Prior Phase 5b attempt (reverted) confirmed icoFoam at 129×129 even after 30 characteristic times produces wrong-signed u-profile — solver swap is mandatory (RESEARCH.md "Prior Phase 5b attempt — findings"). This plan is the src/ rewrite half of the work; Plan 02 regenerates the fixture and validates.

Output: Updated `src/foam_agent_adapter.py` with ~80–120 LOC diff concentrated in two functions (`_generate_lid_driven_cavity`, `_render_block_mesh_dict`). No new files. No test changes in this plan — tests run in Plan 02.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/05b-ldc-simplefoam/05b-CONTEXT.md
@.planning/phases/05b-ldc-simplefoam/05b-RESEARCH.md
@CLAUDE.md

<interfaces>
<!-- From the already-read codebase. Executor SHOULD NOT re-explore. -->

From src/foam_agent_adapter.py (current state — this is what must be rewritten):

```python
# Lines ~640-949: _generate_lid_driven_cavity
# Currently emits:
#   - controlDict:   application icoFoam; endTime 10; deltaT 0.005; writeInterval 2000
#   - fvSchemes:     ddtSchemes { default Euler; }; divSchemes div(phi,U) Gauss linear
#   - fvSolution:    solvers { p (PCG+DIC); pFinal; U (smoothSolver+GaussSeidel) };
#                    PISO { nCorrectors 2; nNonOrthogonalCorrectors 0; pRefCell 0; pRefValue 0; }
#   - 0/U:           boundaryField { lid (fixedValue 1 0 0); wall1..4 (noSlip); }
#   - 0/p:           boundaryField { lid (zeroGradient); wall1..4 (zeroGradient); }
#   - sampleDict:    gold-anchored points sampler at physical (0.5, y, 0.0) — KEEP AS IS
#
# Lines ~6463-6543: _render_block_mesh_dict
# Currently emits:
#   convertToMeters 0.1;
#   vertices ( 8 corners of unit cube x z-thickness 0.1 );
#   blocks ( hex (0 1 2 3 4 5 6 7) (20 20 1) simpleGrading (1 1 1) );
#   boundary ( lid, wall1 (x=0), wall2 (x=1), wall3 (z=0), wall4 (z=0.1) );
#   # wall3 = face (0 1 5 4) z=0 back
#   # wall4 = face (4 5 6 7) z=0.1 front
#   # Both z-faces are declared as wall type — this is the bug for simpleFoam 2D.
```

**Confirmed escaping style (verified during planning — no branching needed):**
- `_render_block_mesh_dict` is a Python **f-string** (`return f"""..."""`) and uses `{{` / `}}` for literal OpenFOAM dictionary braces.
- `_generate_lid_driven_cavity` emission blocks also use f-strings with `{{` / `}}` doubled literal braces.
- When writing the new template bodies below, **use `{{` and `}}` for literal braces**; single `{var}` is reserved for Python substitution. Do NOT introduce `.format()` or raw strings.

From TaskSpec (src/task_runner.py or adjacent):
```python
# TaskSpec has at minimum: .name, .Re, .boundary_conditions (dict)
# Re default 100; boundary_conditions.get("lid_velocity_u", 1.0) used in blockmesh
# nu_val = 0.1 / Re is the existing formula — KEEP.
```

From FoamAgentExecutor dispatcher (src/foam_agent_adapter.py):
```python
# _is_lid_driven_cavity_case(task_spec, solver_name) returns True for lid_driven_cavity case.
# Dispatcher must continue to return True for BOTH "simpleFoam" (new) AND "icoFoam" (historical
# back-compat — gold yaml solver_info.name metadata still says icoFoam). Do NOT narrow the check.
```

From knowledge/gold_standards/lid_driven_cavity.yaml:
```
# Ghia 1982 Re=100 LDC u_centerline, 17 y-points y∈[0.0625..1.0], tolerance 5%.
# solver_info.name field in gold yaml says "icoFoam" — this is HISTORICAL metadata
# about Ghia's solver, NOT a constraint on our solver choice. We explicitly swap to
# simpleFoam; do not touch the gold yaml (三禁区 #3).
```
</interfaces>

<decision_refs>
Per .planning/phases/05b-ldc-simplefoam/05b-CONTEXT.md:
- D-SOLVER: simpleFoam (LOCKED) — replaces icoFoam
- D-MESH: 129×129 uniform hex, 1 cell in z (LOCKED)
- D-ZFACE: frontAndBack empty patch; remove wall3/wall4 z-face walls (LOCKED — Option 1 from RESEARCH.md §"2D pseudo-3D BCs")
- D-PHYS: Re/nu/U_lid/convertToMeters remain parametric via TaskSpec (LOCKED)
- D-SCHEMES / D-SOLVERCFG / D-CONTROLDICT: verbatim values from CONTEXT.md `<specifics>` section (Claude's Discretion, concrete values locked in by Context)
</decision_refs>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Rewrite _render_block_mesh_dict — 129×129 cells + frontAndBack empty patch</name>
  <files>src/foam_agent_adapter.py</files>
  <read_first>
    - src/foam_agent_adapter.py lines 6463-6543 (current _render_block_mesh_dict implementation)
    - .planning/phases/05b-ldc-simplefoam/05b-CONTEXT.md section `<specifics>` → `### blockMeshDict target (frontAndBack empty patch)`
  </read_first>
  <action>
    **Step 0 (CONFIRM escaping style before editing — no branching expected, but verify):**

    The planner has pre-confirmed the current `_render_block_mesh_dict` is an f-string with `{{` / `}}` literal braces. Before emitting the new content, do a 3-line sanity check:
    ```bash
    sed -n '6469p' src/foam_agent_adapter.py | grep -q 'return f"""' && echo "OK: f-string confirmed"
    sed -n '6478p;6483p' src/foam_agent_adapter.py | grep -cE '^\{\{|^\}\}' | grep -q '^2$' && echo "OK: doubled braces confirmed"
    ```
    If BOTH checks pass (expected — planner verified this): proceed using `{{` / `}}` for literal braces in the new template.
    If EITHER check fails (unexpected — file may have drifted): STOP, surface the drift to orchestrator, do NOT guess alternative escaping. No branching logic is authorized for this plan — drift = abort.

    **Step 1 — Rewrite the function body:**

    Modify `_render_block_mesh_dict` in `src/foam_agent_adapter.py` (around lines 6463-6543). Keep the function signature unchanged: `def _render_block_mesh_dict(self, task_spec: TaskSpec) -> str:`. Keep the existing `lid_u = float(task_spec.boundary_conditions.get("lid_velocity_u", 1.0))` extraction at the top (even if unused in the returned string — it may be referenced elsewhere and removing it is out of scope).

    Replace the returned f-string so the emitted blockMeshDict has EXACTLY this structure (keep FoamFile header identical; only the body below changes). Remember: `{{` and `}}` are Python-level escapes that render as literal `{` and `}` in the emitted OpenFOAM text.

    ```
    convertToMeters 0.1;

    vertices
    (
        (0 0 0)
        (1 0 0)
        (1 1 0)
        (0 1 0)
        (0 0 0.1)
        (1 0 0.1)
        (1 1 0.1)
        (0 1 0.1)
    );

    blocks
    (
        hex (0 1 2 3 4 5 6 7) (129 129 1) simpleGrading (1 1 1)
    );

    edges
    (
    );

    boundary
    (
        lid
        {{
            type            wall;
            faces           ((3 7 6 2));
        }}
        wall1
        {{
            type            wall;
            faces           ((0 4 7 3));
        }}
        wall2
        {{
            type            wall;
            faces           ((1 2 6 5));
        }}
        frontAndBack
        {{
            type            empty;
            faces
            (
                (0 1 5 4)
                (4 5 6 7)
            );
        }}
    );

    mergePatchPairs
    (
    );
    ```

    Two concrete changes versus current code:
    1. Cell count: `(20 20 1)` → `(129 129 1)`.
    2. Patches: DELETE the existing `wall3` (face `(0 1 5 4)`, z=0 back) and `wall4` (face `(4 5 6 7)`, z=0.1 front) blocks. REPLACE them with a single `frontAndBack` patch of type `empty` whose `faces` list contains BOTH `(0 1 5 4)` AND `(4 5 6 7)`.

    Keep `lid`, `wall1` (face `(0 4 7 3)`, x=0), and `wall2` (face `(1 2 6 5)`, x=1) unchanged.

    CRITICAL vertex-face mapping from the existing code (DO NOT re-derive — use exactly what the current code has, only moving wall3/wall4 into frontAndBack):
    - lid: `((3 7 6 2))` → y=1 top (the driven wall)
    - wall1: `((0 4 7 3))` → x=0 left
    - wall2: `((1 2 6 5))` → x=1 right
    - wall3 (REMOVE): `((0 1 5 4))` → z=0 back → goes into frontAndBack
    - wall4 (REMOVE): `((4 5 6 7))` → z=0.1 front → goes into frontAndBack

    The file is a Python f-string with doubled braces (`{{` / `}}` for literal braces, single `{}` for Python substitution). Preserve that escaping when writing the new template.

    Do NOT modify any other function in this file in this task.
  </action>
  <verify>
    <automated>cd /Users/Zhuanz/Desktop/cfd-harness-unified && .venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from src.foam_agent_adapter import FoamAgentExecutor
from src.task_runner import TaskRunner
tr = TaskRunner(executor=FoamAgentExecutor())
spec = tr._task_spec_from_case_id('lid_driven_cavity')
fx = FoamAgentExecutor()
txt = fx._render_block_mesh_dict(spec)
assert '(129 129 1)' in txt, 'mesh not 129x129'
assert 'frontAndBack' in txt, 'frontAndBack patch missing'
assert 'type            empty' in txt, 'empty type missing'
assert '(0 1 5 4)' in txt and '(4 5 6 7)' in txt, 'z-face quads missing from frontAndBack'
# The old wall3/wall4 bare patch blocks must not appear; check they are not declared as walls anymore.
# The faces themselves are legitimate (they ARE the z-faces); what we assert is no 'wall3 {' or 'wall4 {' patch header remains.
assert 'wall3' not in txt, 'old wall3 patch header still present'
assert 'wall4' not in txt, 'old wall4 patch header still present'
assert '(20 20 1)' not in txt, 'old 20x20 mesh literal still present'
print('BLOCKMESH OK')
"
</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '(129 129 1)' src/foam_agent_adapter.py` returns ≥ 1
    - `grep -c 'frontAndBack' src/foam_agent_adapter.py` returns ≥ 1
    - Line-range-bounded check: `sed -n '6463,6545p' src/foam_agent_adapter.py | grep -cE '^\s+wall3\s*$|^\s+wall4\s*$'` returns 0 (no wall3/wall4 patch headers inside the function body)
    - The automated verify block above exits 0 and prints `BLOCKMESH OK`
  </acceptance_criteria>
  <done>
    `_render_block_mesh_dict` emits a 129×129 mesh with a single `frontAndBack` empty patch covering both z-faces, and the old `wall3`/`wall4` patch declarations are gone. Python inline smoke test passes.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Rewrite _generate_lid_driven_cavity — controlDict + fvSchemes + fvSolution for simpleFoam</name>
  <files>src/foam_agent_adapter.py</files>
  <read_first>
    - src/foam_agent_adapter.py lines 640-949 (current _generate_lid_driven_cavity implementation — controlDict, fvSchemes, fvSolution emission blocks)
    - .planning/phases/05b-ldc-simplefoam/05b-CONTEXT.md sections: `### simpleFoam controlDict target`, `### simpleFoam fvSchemes target`, `### simpleFoam fvSolution target`
    - .planning/phases/05b-ldc-simplefoam/05b-RESEARCH.md sections: `## simpleFoam architecture`, `## fvSchemes rationale`, `## fvSolution rationale`
  </read_first>
  <action>
    Modify `_generate_lid_driven_cavity` in `src/foam_agent_adapter.py` (around lines 640-949). All emission blocks in this function are Python f-strings with `{{` / `}}` doubled literal braces (same style as Task 1 — planner confirmed). Use that escaping for any dictionary braces in the new content.

    Make three discrete edits to the three file-emission blocks (controlDict at ~line 686, fvSchemes at ~line 741, fvSolution at ~line 787). Do NOT touch the `physicalProperties` block (unchanged — Re/nu logic keeps working), the `sampleDict` block (LOCKED — RESEARCH.md "Post-processing sampling" says leave as-is), or the blockMeshDict call (unchanged — Task 1 handled the blockmesh changes).

    **Edit A — controlDict body (replace current icoFoam block):**

    Replace the existing controlDict body (the string between the FoamFile header close `// * * * ... //` and the final `// *** //` closer) with:
    ```
    application     simpleFoam;

    startFrom       startTime;

    startTime       0;

    stopAt          endTime;

    endTime         2000;

    deltaT          1;

    writeControl    timeStep;

    writeInterval   2000;

    purgeWrite      0;

    writeFormat     ascii;

    writePrecision  6;

    writeCompression off;

    timeFormat      general;

    timePrecision   6;

    runTimeModifiable true;
    ```
    Changes versus current: `application icoFoam` → `application simpleFoam`; `endTime 10` → `endTime 2000`; `deltaT 0.005` → `deltaT 1`. `writeInterval 2000` stays (still writes only final snapshot).

    **Edit B — fvSchemes body (replace current Euler+Gauss-linear block):**

    Replace the existing fvSchemes body with (remember `{{` / `}}` for literal braces):
    ```
    ddtSchemes
    {
        default         steadyState;
    }

    gradSchemes
    {
        default         Gauss linear;
    }

    divSchemes
    {
        default         none;
        div(phi,U)      bounded Gauss limitedLinearV 1;
        div((nuEff*dev2(T(grad(U))))) Gauss linear;
    }

    laplacianSchemes
    {
        default         Gauss linear corrected;
    }

    interpolationSchemes
    {
        default         linear;
    }

    snGradSchemes
    {
        default         corrected;
    }

    wallDist
    {
        method          meshWave;
    }
    ```
    Changes versus current: `ddtSchemes default Euler` → `default steadyState`; `div(phi,U) Gauss linear` → `div(phi,U) bounded Gauss limitedLinearV 1`; ADD `div((nuEff*dev2(T(grad(U))))) Gauss linear;` entry; ADD `interpolationSchemes`, `snGradSchemes`, `wallDist` blocks (all standard for simpleFoam).

    **Edit C — fvSolution body (replace current PISO block):**

    Replace the existing fvSolution body with:
    ```
    solvers
    {
        p
        {
            solver          GAMG;
            tolerance       1e-06;
            relTol          0.1;
            smoother        GaussSeidel;
        }

        U
        {
            solver          smoothSolver;
            smoother        GaussSeidel;
            tolerance       1e-05;
            relTol          0.1;
            nSweeps         1;
        }
    }

    SIMPLE
    {
        nNonOrthogonalCorrectors 0;
        consistent      yes;
        pRefCell        0;
        pRefValue       0;
        residualControl
        {
            p               1e-5;
            U               1e-5;
        }
    }

    relaxationFactors
    {
        equations
        {
            U               0.9;
        }
        fields
        {
            p               0.3;
        }
    }
    ```
    Changes versus current: p solver PCG+DIC → GAMG+GaussSeidel; DELETE the `pFinal` block (PISO-only, meaningless under SIMPLE); `PISO { nCorrectors 2; ... }` → `SIMPLE { consistent yes; residualControl { p 1e-5; U 1e-5; } }`; ADD `relaxationFactors` block with U=0.9 and p=0.3.

    **Edit D — 0/U boundaryField (replace wall3/wall4 entries with frontAndBack):**

    In the `0/U` emission block (around lines ~869-891), replace the `wall3` and `wall4` entries with a single `frontAndBack` entry of type `empty`. Keep `lid` (fixedValue 1 0 0), `wall1` (noSlip), `wall2` (noSlip) unchanged. Delete `wall3` and `wall4` entries entirely. New `0/U` boundaryField block:
    ```
    boundaryField
    {
        lid
        {
            type            fixedValue;
            value           uniform (1 0 0);
        }
        wall1
        {
            type            noSlip;
        }
        wall2
        {
            type            noSlip;
        }
        frontAndBack
        {
            type            empty;
        }
    }
    ```

    **Edit E — 0/p boundaryField (analogous):**

    In the `0/p` emission block (around lines ~922-944), replace `wall3` and `wall4` entries with `frontAndBack { type empty; }`. Keep `lid`, `wall1`, `wall2` as `zeroGradient`. New `0/p` boundaryField block:
    ```
    boundaryField
    {
        lid
        {
            type            zeroGradient;
        }
        wall1
        {
            type            zeroGradient;
        }
        wall2
        {
            type            zeroGradient;
        }
        frontAndBack
        {
            type            empty;
        }
    }
    ```

    Do NOT touch `_is_lid_driven_cavity_case` (~line 7178) or `_extract_ldc_centerline` (~line 7427) — CONTEXT.md explicitly forbids.
  </action>
  <verify>
    <automated>cd /Users/Zhuanz/Desktop/cfd-harness-unified && .venv/bin/python -c "
import sys, tempfile, pathlib
sys.path.insert(0, '.')
from src.foam_agent_adapter import FoamAgentExecutor
from src.task_runner import TaskRunner

# --- Dispatcher smoke (BLOCKER #3 fix): exercise the full routing path ---
runner = TaskRunner(executor=FoamAgentExecutor())
spec = runner._task_spec_from_case_id('lid_driven_cavity')
fx = FoamAgentExecutor()
assert fx._is_lid_driven_cavity_case(spec, 'simpleFoam') is True, 'dispatcher regression on simpleFoam LDC case'
assert fx._is_lid_driven_cavity_case(spec, 'icoFoam') is True, 'dispatcher back-compat broken for icoFoam'
print('dispatcher OK')

# --- Full generator smoke: emit case dir and inspect all files ---
with tempfile.TemporaryDirectory() as td:
    cd = pathlib.Path(td) / 'ldc'
    fx._generate_lid_driven_cavity(cd, spec)

    ctrl = (cd / 'system' / 'controlDict').read_text()
    schemes = (cd / 'system' / 'fvSchemes').read_text()
    sol = (cd / 'system' / 'fvSolution').read_text()
    u = (cd / '0' / 'U').read_text()
    p = (cd / '0' / 'p').read_text()
    bmd = (cd / 'system' / 'blockMeshDict').read_text()

    # controlDict
    assert 'application     simpleFoam' in ctrl, 'controlDict solver wrong'
    assert 'endTime         2000' in ctrl, 'controlDict endTime wrong'
    assert 'deltaT          1' in ctrl, 'controlDict deltaT wrong'
    assert 'icoFoam' not in ctrl, 'icoFoam still present in controlDict'

    # fvSchemes
    assert 'default         steadyState' in schemes, 'fvSchemes ddt not steadyState'
    assert 'bounded Gauss limitedLinearV 1' in schemes, 'fvSchemes div(phi,U) wrong'
    assert 'div((nuEff*dev2(T(grad(U)))))' in schemes, 'fvSchemes missing deviatoric term'
    assert 'wallDist' in schemes, 'fvSchemes missing wallDist'

    # fvSolution
    assert 'SIMPLE' in sol, 'fvSolution missing SIMPLE'
    assert 'PISO' not in sol, 'fvSolution still has PISO'
    assert 'consistent      yes' in sol, 'fvSolution SIMPLE missing consistent yes'
    assert 'GAMG' in sol, 'fvSolution missing GAMG'
    assert 'pFinal' not in sol, 'fvSolution still has pFinal (PISO artifact)'
    assert 'relaxationFactors' in sol, 'fvSolution missing relaxationFactors'
    assert 'residualControl' in sol, 'fvSolution missing residualControl'

    # 0/U + 0/p
    assert 'frontAndBack' in u and 'type            empty' in u, '0/U missing frontAndBack empty'
    assert 'frontAndBack' in p and 'type            empty' in p, '0/p missing frontAndBack empty'
    # wall3/wall4 entries in 0/U and 0/p must be gone
    assert 'wall3' not in u and 'wall4' not in u, '0/U still has wall3/wall4 BC entries'
    assert 'wall3' not in p and 'wall4' not in p, '0/p still has wall3/wall4 BC entries'

    # blockMesh sanity (should be Task 1 output)
    assert '(129 129 1)' in bmd, 'blockMesh not 129x129'
    assert 'frontAndBack' in bmd, 'blockMesh missing frontAndBack'

print('LDC CASE GEN OK')
"
</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'application     simpleFoam' src/foam_agent_adapter.py` returns ≥ 1
    - `grep -c 'steadyState' src/foam_agent_adapter.py` returns ≥ 1 (in the LDC fvSchemes block)
    - Line-range-bounded check (WARNING #4 fix): `sed -n '640,960p' src/foam_agent_adapter.py | grep -cE 'application\s+icoFoam'` returns 0 (no icoFoam inside `_generate_lid_driven_cavity` body — other cases elsewhere in the file may legitimately still reference icoFoam and are out of scope)
    - `grep -c 'consistent      yes' src/foam_agent_adapter.py` returns ≥ 1 (in the LDC fvSolution)
    - `grep -c 'bounded Gauss limitedLinearV 1' src/foam_agent_adapter.py` returns ≥ 1
    - **Dispatcher smoke (BLOCKER #3): the automated verify block prints `dispatcher OK` BEFORE `LDC CASE GEN OK` — both must appear or the task fails.**
    - The automated verify block above exits 0 and prints both `dispatcher OK` and `LDC CASE GEN OK`
    - Total diff on `src/foam_agent_adapter.py` vs git HEAD is ≥ 50 LOC and ≤ 150 LOC (sanity bound: CONTEXT.md estimates 80-120 LOC). Check: `git diff --stat src/foam_agent_adapter.py`
  </acceptance_criteria>
  <done>
    `_generate_lid_driven_cavity` emits a simpleFoam case (steady-state SIMPLE + SIMPLEC + GAMG p + bounded limitedLinearV div + `frontAndBack empty` BCs). The inline python smoke test passes (both dispatcher smoke and full case gen). The file still imports, parses, and `_render_block_mesh_dict` + `_generate_lid_driven_cavity` can both be called without exception on a `lid_driven_cavity` TaskSpec. Dispatcher `_is_lid_driven_cavity_case` still returns True for both `simpleFoam` and `icoFoam` solver name inputs.
  </done>
</task>

</tasks>

<verification>
After both tasks:
1. Run `cd /Users/Zhuanz/Desktop/cfd-harness-unified && .venv/bin/python -c "from src.foam_agent_adapter import FoamAgentExecutor; FoamAgentExecutor()"` — module must import cleanly.
2. The combined inline smoke test from Task 2 (which also exercises Task 1's blockMeshDict AND the dispatcher path) must pass — both `dispatcher OK` and `LDC CASE GEN OK` printed.
3. `git diff --stat src/foam_agent_adapter.py` shows changes concentrated in two hunks (the `_generate_lid_driven_cavity` body around lines 640-950 and the `_render_block_mesh_dict` body around lines 6463-6545). No other functions modified.
</verification>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| case-generator → OpenFOAM solver input | The adapter writes untrusted-by-construction TaskSpec-derived numbers (Re, lid_u) into blockMeshDict and physicalProperties. TaskSpec itself is sourced from the backend controlled API, not end-user input, but the emit path is a minor injection surface. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05b-01 | Tampering | `_render_block_mesh_dict` f-string substitution of `task_spec.boundary_conditions["lid_velocity_u"]` | accept | lid_u is already coerced to float via `float(...)`. TaskSpec comes from server-side `_task_spec_from_case_id("lid_driven_cavity")` which is a hardcoded case; no external injection path in this plan. |
| T-05b-02 | DoS | simpleFoam endTime=2000 iterations on 129×129 mesh | accept | Expected wall time 30-90 s per Phase 5a baseline; bounded by endTime; audit_package build has its own timeout layer. No amplification — case runs are executor-queue-limited. |
| T-05b-03 | Repudiation | Change in solver semantics without audit trail | mitigate | Plan 03 records DEC-V61-NNN with decision rationale and commit SHA. Plan 02 regenerates the audit fixture which embeds the new commit_sha. |
</threat_model>

<success_criteria>
1. `src/foam_agent_adapter.py` diff present; both target functions rewritten.
2. Inline smoke tests in Task 1 and Task 2 both exit 0 (Task 2 prints both `dispatcher OK` and `LDC CASE GEN OK`).
3. No changes to `_is_lid_driven_cavity_case`, `_extract_ldc_centerline`, or `_emit_gold_anchored_points_sampledict` usage (三禁区 preserved). `_is_lid_driven_cavity_case` verified via dispatcher smoke test to still route both simpleFoam and icoFoam correctly.
4. No changes to `knowledge/gold_standards/lid_driven_cavity.yaml` (三禁区 #3).
5. No changes to tests or fixtures yet — Plan 02's responsibility.
</success_criteria>

<output>
After completion, create `.planning/phases/05b-ldc-simplefoam/05b-01-SUMMARY.md` documenting:
- Diff line count on `src/foam_agent_adapter.py`
- List of the five edits (A: controlDict, B: fvSchemes, C: fvSolution, D: 0/U, E: 0/p) + Task 1's blockMeshDict edit
- Confirmation both inline smoke tests printed OK (`dispatcher OK` + `LDC CASE GEN OK`)
- Note: fixture regeneration + backend pytest is Plan 02
</output>
</content>
</invoke>