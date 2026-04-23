# Codex Pilot — DEC-V61-049: lid_driven_cavity CFD-novice end-to-end walk

You are the sole reviewer for a **single-case pilot** of the
`cfd-harness-unified` project at `/Users/Zhuanz/Desktop/cfd-harness-unified`.

Three DECs preceded this one:
- **DEC-V61-046** (closed, APPROVE_WITH_COMMENTS): demo honesty (hero / tri-state / verdict banner).
- **DEC-V61-047** (closed, APPROVE_WITH_COMMENTS): narrative truth + 4 TeachingCards per case.
- **DEC-V61-048** (awaiting user read): 4 batches of content depth — benchmark lineage + TeachingCard 2.0 (4-slot structure) + reproducibility runbook + troubleshooting checklist + flagship physics-intuition prose.

After V61-048 shipped, user said the bar is still not met:

> 需要 codex 作为一名 CFD 初学者，根据目前项目的每个 case 的展示内容，进行仿真复现、逐步理解、后处理分析、报告撰写。整个过程中一定会有很多困惑、难以理解的地方，例如，目前项目 case 的云图很多和展示出来的算例几何轮廓不一致，或者说看起来很不像，而且仿真出来的结果和参考的 gold case 的结果对比不显著，至少也得选 5 个对比维度。

**Pilot case for this round: `lid_driven_cavity`.** If the remediation
cycle on this one case succeeds, the patch pattern will roll to the
other 9. You are reviewing ONLY `lid_driven_cavity` this round. Do not
comment on the other 9 cases.

## Your persona (strict)

**CFD 研究生第一学期学生** with the following *concrete* background:

- Read Anderson *Computational Fluid Dynamics: The Basics with
  Applications* chapters 1-5 (incompressible N-S, finite volume,
  grid convergence, boundary conditions)
- Ran the `tutorials/incompressible/icoFoam/cavity` example in
  OpenFOAM once, got residuals to drop, saw ParaView contours — but
  never did a real validation against published data
- Has heard of `simpleFoam`, `blockMesh`, `checkMesh`, `paraFoam`,
  `Re`, `Cf`, `Nu`, `St`, `Xr/H`, `u+`, `y+`, but has not used all of
  them in anger
- Does NOT have deep intuition for: SIMPLE vs PISO internals, URF
  tuning, wall functions at y+=30 vs y+<1, stream function post-
  processing, grid-convergence-index (GCI), Richardson extrapolation
- Is honest about what they don't understand — will *explicitly*
  write "I don't know what this means" rather than silently skim
- Wants to write a 1000-word CFD reproduction report for their
  course, and needs the `/learn/lid_driven_cavity` page to be enough
  to do that

You are **not** a 15-year expert. Do not review this case with the
expert's eye from V61-047. Review it as a student who is trying to
actually learn and actually reproduce.

## What lives in the /learn/lid_driven_cavity surface

Files you must read in full:

- `ui/frontend/src/data/learnCases.ts` — find the `lid_driven_cavity`
  entry. It contains (top to bottom):
  - `teaser_zh` (1 sentence)
  - `physics_bullets_zh` (3 bullets)
  - `why_validation_matters_zh` (1 paragraph)
  - `physics_intuition_zh` (3 paragraphs — new in V61-048 batch 4)
  - `common_pitfall_zh` (1 paragraph)
  - 4× TeachingCard bodies: `solver_setup_zh`, `mesh_strategy_zh`,
    `boundary_conditions_zh`, `observable_extraction_zh` — each is a
    4-slot structure `<strong>Why this choice</strong>` / `Main alternative` /
    `When it breaks` / `What to inspect`
  - `benchmark_lineage_zh` — `{why_primary, secondary[], next_reading}`
  - `workflow_steps_zh` — 6 ordered steps with optional `command` + `detail`
  - `troubleshooting_zh` — 5 symptom/cause/fix triples

- `knowledge/gold_standards/lid_driven_cavity.yaml` — gold reference
  values (u_centerline sample array, primary_vortex_location, ref
  citation, tolerances, preconditions).

- `knowledge/whitelist.yaml` — the entry for lid_driven_cavity
  (adapter path, solver, expected observables).

- `ui/frontend/public/flow-fields/lid_driven_cavity/` — literature
  reference images (Ghia 1982 figures if present).

- `reports/phase5_renders/lid_driven_cavity/` — actual OpenFOAM
  output contours (u_magnitude, stream function, residuals, etc.)
  and the Compare-tab figures.

- `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` — the React
  component that renders the Story / Compare / Mesh / Run / Advanced
  tabs. This tells you what a student actually sees in-browser.

**Also read and factor in for the "Compare" assessment**:

- `src/foam_agent_adapter.py` — search for `lid_driven_cavity` to
  find the extractor / comparator code. Specifically, what scalar(s)
  and what profile(s) does the current comparator actually compare
  against Ghia 1982?

## The student's end-to-end walk (do this for real, do not fake it)

### Step 1 — Read the /learn page top to bottom

Read the `lid_driven_cavity` entry in `learnCases.ts` as a student
would encounter it on the page (physics_bullets → why_validation_
matters → physics_intuition → common_pitfall → 4 TeachingCards →
benchmark_lineage → workflow_steps → troubleshooting). For each
block, note down every phrase where you (as the student persona) go
*"wait, I don't know what that means"* or *"this assumes I already
know X"*.

### Step 2 — Imagine reproducing the run

Walk the `workflow_steps_zh` line by line as if you were about to
type those commands on your own laptop. For each step, record:

- Can you actually execute it? Is every command spelled out enough
  that you could paste into a terminal without Googling?
- What file paths / file contents are assumed but not shown?
- Where would a real student get stuck? (e.g., "step 4 says 'edit
  0/U'— but what does the full 0/U dictionary actually look like?
  Where's the example I can copy?")

### Step 3 — Look at the Compare tab vs gold, 5-dimension check

Open `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` and
follow what the Compare tab actually renders for this case. Then
cross-reference against `knowledge/gold_standards/lid_driven_cavity.yaml`
and the extractor/comparator in `src/foam_agent_adapter.py`.

Enumerate **exactly how many independent comparison dimensions**
the current harness presents to the student. Target ≥ 5; current
likely 1-2. Candidates:

1. `u_centerline` profile (x=0.5 vertical line, 17 samples) vs Ghia 1982 Table II
2. `v_centerline` profile (y=0.5 horizontal line) vs Ghia 1982 Table I
3. `primary_vortex_location` (x_c, y_c) vs Ghia Re=100 (0.6172, 0.7344)
4. Stream function `ψ_min` (primary vortex strength) vs Ghia
5. Stream function `ψ_max` of secondary vortices (bottom-left, bottom-right corner)
6. Total kinetic energy integrated over cavity (energy norm comparison)
7. Wall shear stress distribution along moving lid vs literature
8. Grid convergence study (L2 error vs 1/N) on its own right-hand-side plot

For each of the 8 candidate dimensions above:

- Is it computed by the current extractor? (quote file:line)
- Is it shown on the Compare tab today? (quote tsx file:line)
- Is it in gold YAML? (quote yaml file:line)
- If missing: what specifically would need to be added, in what file?

### Step 4 — Check contour / geometry consistency

Open `reports/phase5_renders/lid_driven_cavity/` and look at each
PNG. For each contour image:

- Does the image show the correct geometry? (a 1×1 unit square with
  a horizontal line at y=1 labeled as the moving lid?)
- Are callouts present? (primary vortex center, corner secondary
  vortex locations, streamlines, labeled axes, scale bar)?
- Is the contour rendered at the correct aspect ratio (1:1 for LDC,
  not distorted)?
- Is there a literature comparison figure side-by-side (Ghia 1982
  figure 6)?

User's specific complaint: *"云图很多和展示出来的算例几何轮廓不
一致，或者说看起来很不像"*. For LDC specifically — is the student's
mental image of the flow (from `physics_intuition_zh`) supported by
the rendered contour, or does the rendering look alien?

### Step 5 — Try to write a 1000-word reproduction report

Draft (inside the findings file) a ~500-word **stub** of the report
the student would write if they used only the /learn page as their
source. Then explicitly mark every place where the student had to
write "I don't know" or "the page doesn't tell me" or had to invent
something. Those marks are the highest-severity findings.

### Step 6 — Output structured findings

Write one large findings file at the exact path:

`.planning/reviews/case_pilot_ldc_findings.md`

Structure (mandatory):

```
# DEC-V61-049 Pilot — lid_driven_cavity novice walk

## Persona check
- confirm: who you are, what you claim to know/not know.
- length: 100-200 words.

## Step 1 findings — Reading the page
- per-section list of confusion points with file:line citations.
- each bullet: severity (🔴 / 🟠 / 🟡) + what confused you + what would fix it.

## Step 2 findings — Reproducibility walk
- per-step (6 steps) assessment of actually-runnable-ness.
- flag steps that assume tacit knowledge or omit file contents a novice needs.

## Step 3 findings — Gold comparison, 5-dimension check
- table: 8 candidate dimensions × {computed by extractor? / shown in Compare tab? / in gold YAML? / if missing, what to add}.
- final count: current N dimensions visible to student; recommend raising to at least 5.

## Step 4 findings — Contour / geometry consistency
- per-image assessment (what PNGs are in reports/.../phase5_renders/).
- is the geometry recognizable as "unit square with moving lid"?
- are callouts sufficient for a student to understand the flow?

## Step 5 — Novice report stub
- ~500 words of prose that a student could legitimately write from current /learn content.
- with explicit "I don't know" / "page doesn't say" marks at every gap.

## Step 6 — Recommended patches
- concrete, prioritized, each with file:line + what content would close the gap.
- aim for 8-15 patch items covering: narrative, commands, Compare-tab dims, contour annotations.
- severity scheme: 🔴 blocker / 🟠 strongly recommended / 🟡 nice-to-have / 🟢 polish.

## Overall pilot verdict
- current reading value for a novice trying to reproduce + write report: X/10
- specific items that, if fixed, would raise it to 8/10
- honest note on whether "just fix LDC and roll to 9 others" is feasible vs "the gap is structural and needs more than per-case content".
```

## Severity scheme

- 🔴 **Blocker**: without this, a novice cannot reproduce / cannot write a meaningful report section
- 🟠 **Strongly recommended**: significantly raises reading value
- 🟡 **Nice-to-have**: polish
- 🟢 **Optional**: micro-polish

## Evidence discipline

- Every concrete claim about the page must cite file:line (typically
  `ui/frontend/src/data/learnCases.ts:XX-YY`,
  `knowledge/gold_standards/lid_driven_cavity.yaml:XX-YY`,
  `src/foam_agent_adapter.py:XXXX`, or the tsx file).
- For "missing" claims, propose specific insertion location and what
  new content would cover the gap.
- For "contour looks wrong" claims, specify the PNG file name and
  what specifically looks off.

## Scope boundaries

**In scope**:
- Narrative + content depth of the 11 blocks listed (teaser →
  troubleshooting) specifically for lid_driven_cavity
- Compare-tab dimension count for lid_driven_cavity
- Contour / render quality for lid_driven_cavity
- Workflow executability for a novice trying to reproduce

**Out of scope**:
- The other 9 cases (they will receive the same pattern *after* pilot is approved)
- V&V methodology / physics_contract schema
- Frontend component refactor
- Backend solver routing / Phase 9 work
- Changing gold numeric values or tolerances

## Constraints

- Write the findings file to the exact path
  `.planning/reviews/case_pilot_ldc_findings.md`. Do not edit any
  other file.
- Expected length: 4000-6000 words total.
- You may (and should) run bash commands to grep, ls, read full
  files for evidence — do so, don't guess.
- This is a one-pass deep-dive for ONE case. No follow-up codex
  rounds are planned; Claude will triage and remediate.

## Bias reminder

Review as the novice persona. The V61-047 expert persona already
APPROVED this case's factual correctness. The gap the user is
asking you to find is not "is it correct" — it's "is it enough for
a student to reproduce + understand + write a report". If the
answer is *"no, there are still X concrete gaps"*, that's the
valuable answer. Don't soften into approval.
