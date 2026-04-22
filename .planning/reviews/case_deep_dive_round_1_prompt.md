# Codex Round 1 — DEC-V61-048: 10-case 深度阅读价值评审

You are reviewing `/learn` pages of the `cfd-harness-unified` project
at `/Users/Zhuanz/Desktop/cfd-harness-unified`, as a **single
deep-dive reviewer**. The user has already judged the previous two
DECs' codex approvals insufficient:

> 我觉得现在几乎没有一个 case 有阅读价值

DEC-V61-046 closed demo honesty (hero, tri-state, contract status).
DEC-V61-047 closed factual correctness + added 4 `TeachingCard`s per
case (solver / mesh / BC / extraction). Both got APPROVE_WITH_COMMENTS
from 2-persona (expert + novice) codex reviews. **Do not replicate
those reviews.** This round's bar is different and higher.

## Your persona

**资深 CFD 教学专家 + 技术作家** — 15+ years of OpenFOAM practice (same
seniority as V61-047 expert) PLUS **experience writing published CFD
pedagogy**: textbook chapters (Ferziger-Perić level), Ansys/COMSOL
training materials, CFD Online / CFD-Wiki tutorial essays, conference
tutorials. You are now being asked a **different** question than
rounds V61-046/047 asked:

> Would you assign each of these 10 `/learn` case pages as **reading
> material in a graduate CFD methodology course**? If not, for each
> case, what specifically is the page missing to reach that bar?

**Not** "is it factually correct" (V61-047 handled that).
**Not** "can a first-click novice understand the homepage" (V61-047
novice persona handled that).
**But**: is the content **worth 20-30 minutes of careful reading**?
Does it teach something a textbook or tutorial essay would teach, or
is it just a UI demonstration of physics_contract fields?

## The 10 cases in scope

Each case lives in:
- `ui/frontend/src/data/learnCases.ts` (authoritative narrative source
  — read the full entry per case, including the 4 TeachingCard
  fields and comments).
- `knowledge/gold_standards/<case_id>.yaml` (physics_contract,
  reference_values, precondition details, solver_info, mesh_info).
- `ui/frontend/public/flow-fields/<case_id>/*.png` (literature
  reference images).
- `reports/<case_id>/phase5_renders/*.png` (actual OpenFOAM output).
- `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` (tabs layout
  — Story / Compare / Mesh / Run / Advanced).

| case_id | difficulty | displayName |
|---|---|---|
| lid_driven_cavity | intro | Lid-Driven Cavity |
| backward_facing_step | core | Backward-Facing Step |
| circular_cylinder_wake | core | Circular Cylinder Wake |
| turbulent_flat_plate | intro (renamed laminar) | Flat Plate (laminar Blasius regime) |
| plane_channel_flow | advanced | Plane Channel (incompatibility teaching case) |
| impinging_jet | advanced | Impinging Jet (geometry + solver gap teaching) |
| naca0012_airfoil | core | NACA 0012 Airfoil |
| rayleigh_benard_convection | advanced | Rayleigh-Bénard Convection |
| differential_heated_cavity | core (downgraded Ra=1e6) | Differential Heated Cavity (Ra=1e6 benchmark) |
| duct_flow | advanced | Fully Developed Turbulent Square Duct |

## What to evaluate per case

For EACH case, walk its full `/learn` surface (Story tab is
load-bearing; Compare / Mesh / Run / Advanced carry supporting
weight) against a textbook-chapter bar on these axes:

### A. Historical & research context
- Is the case's role in CFD history / validation lineage explained?
  (e.g. LDC is where "benchmark" emerged as a standard practice; Le-
  Moin-Kim is the DNS that forced CFD to admit 2%-band reference
  errors exist).
- Is the benchmark citation (Ghia 1982, Le-Moin-Kim 1997, Williamson
  1996, Baughn 1989, de Vahl Davis 1983, Ladson 1996) more than a
  name — is the student told **why this paper, not another**?
- Are **alternative benchmarks / refinements** mentioned so a curious
  student knows what to read next?

### B. Physical intuition
- Can a student understand from the page alone **what the flow looks
  like** physically — stagnation point, separation, reattachment,
  vortex shedding, thermal plume, etc.?
- Are the **regime transitions** (Re_crit, transition to turbulence,
  bifurcations) explained, or just numerical thresholds listed?
- Is there a **mental model** anchor (like: "cavity flow is essentially
  a closed circulation driven by lid shear — the corner vortex
  structure is the fingerprint")?

### C. Numerical / meshing pedagogy
- Does the mesh strategy narrate the **trade-off** (why 40 cells not
  20, why wall grading, why y+≈1 or <30, how mesh scale ties to
  physics scale)?
- Does the solver choice narrate the **alternative** (why icoFoam not
  pimpleFoam, why kOmegaSST not k-ε, why SIMPLE not PISO)?
- Are the BC types explained at the level of **what they represent
  physically**, not just the OpenFOAM keyword?

### D. Workflow visibility
- Is there a **from-zero pipeline** shown: "to reproduce this, the
  steps are (1) prepare blockMeshDict, (2) run blockMesh, (3) apply
  BC via /constant/..., (4) launch simpleFoam, (5) sample observable
  via extractor, (6) run comparator against gold..."?
- Does the page link OpenFOAM commands or code snippets inline so a
  student can actually reproduce?

### E. Visualization density
- How many figures per case? (today: typically 1 literature image +
  1 actual contour + 1 residual PNG = 3 images max, often only 1-2).
- Is there a **mesh block diagram** showing domain dimensions + patch
  types (the student should see geometry at a glance)?
- Are contours **annotated** with callouts (stagnation point,
  separation line, primary vortex, thermal plume)?
- Is there a **flow regime map** (e.g. BFS: Re vs Xr/H curve with
  current working point marked; cylinder: Re vs St showing plateau)?

### F. Failure-mode / diagnostic walk
- Does the page teach **what goes wrong** and how you'd recognize it?
  (e.g. "if residuals stall, check URF; if Xr/H < 0 you're sampling
  wrong side of step; if Nu(0) is 50% too high your k-ε is doing
  the well-known driving jet stagnation over-prediction").
- Is there a **troubleshooting checklist** ordered by likelihood?

### G. Depth vs density
- Estimated total word count of narrative content per case today vs
  what a textbook chapter would have.
- Is the **TeachingCard** body too terse (today: 2-3 sentences;
  textbook: 5-8 sentences with concrete numbers + citation-link)?

## Output structure

Write one large findings file: `.planning/reviews/case_deep_dive_round_1_findings.md`.

**Structure**:

```
# DEC-V61-048 Round 1 — 10-case 深度阅读价值评审

## Overall judgment
- 总体"阅读价值"评分 (1-10):
- 主要结构性问题 (not per-case, but common across cases):
  - ...
- 最值得读的 2-3 case (现状):
- 最需要补的 2-3 case:

## Per-case deep-dive

### 1. lid_driven_cavity
**Current reading value**: X/10
**If I were assigning reading material**: would assign | skip | conditional-on-補

[4-6 paragraphs covering axes A-G above, written as a textbook editor's critique of the current content. Cite file:line for every claim about what's present or missing.]

**Concrete补齐 list** (prioritized):
- 🔴 historical context: 当前只说"几乎每一本 CFD 教材的第一个算例"，应补充 why Ghia 1982 而不是 Burggraf 1966 / Botella-Peyret 1998，以及 Re=100/400/1000 的学习路径.  file: ui/frontend/src/data/learnCases.ts:42-46
- 🟠 mesh block diagram: 缺 domain schematic 显示顶盖箭头 + 4 边 BC 标签 + 129² 网格例子. suggested placement: new section before Mesh tab.
- 🟠 contour annotation: reports/<ldc>/phase5_renders/contour_u_magnitude.png 无 callouts, 学生看不懂主涡和二级涡位置.
- 🟡 Ghia 1982 数据如何被当作 "gold" 的历史: 当年实验 + 其他文献的分歧.
- ... (5-10 items per case, each with severity + file:line + concrete action)

### 2. backward_facing_step
...

### 3-10. (same structure for each remaining case)

## Cross-case patterns
- TeachingCard bodies systematically lack XYZ: [specific recommendations]
- All 10 cases lack [common missing element]: [specific recommendation]
- 3-4 cases share [specific pedagogy gap]: [bulk remediation suggestion]

## Summary: recommended batch plan for Claude

Grouped by theme, not per-case, for efficient implementation:
- Batch A: [theme + affected cases + estimated LOC]
- Batch B: ...
- ...

Aim for 4-6 batches that each add meaningful pedagogy value.
```

## Severity scheme

- 🔴 **Must-fix for textbook-grade**: 没这个内容这 case 不值得分配给学生读
- 🟠 **Strongly recommended**: 有了显著提升 reading value
- 🟡 **Nice to have**: 锦上添花
- 🟢 **Optional**: polish

## Evidence discipline

- Every concrete claim about what the page contains must cite
  `file:line` (typically `ui/frontend/src/data/learnCases.ts:XX-YY`
  or `knowledge/gold_standards/<case>.yaml:XX-YY`).
- For "what's missing" claims, propose a specific insertion location
  (which file, before/after which current section, what new content
  would cover the gap).
- Where image additions would help, specify the image type (ASCII
  block diagram, SVG annotation overlay, additional literature PNG,
  etc.) — don't just say "add a picture".

## Scope boundaries (explicit)

**In scope** for this review:
- Content depth & narrative density in `learnCases.ts` per case
- The 4 TeachingCard bodies per case (solver_setup_zh, etc.)
- Gold YAML contract_status / precondition pedagogy quality
- Image density on the Story tab
- Pipeline-walkthrough existence

**Out of scope**:
- Backend Tier-C `_VISUAL_ONLY_CASES` upgrade (V61-047 F3 deferred)
- Gold numeric values (do not propose changing ref_value, tolerance,
  or precondition satisfaction levels)
- Frontend framework / component refactor (don't suggest rebuilding
  LearnCaseDetailPage)
- V&V methodology / physics_contract field schema

## Don't

- Don't re-review V61-046 demo-honesty items (hero, tri-state,
  verdict banner) — those are closed.
- Don't re-review V61-047 factual correctness items (TFP laminar,
  plane_channel incompatibility, DHC Ra=1e6) — also closed.
- Don't suggest adding more `case_id`s to the whitelist — we're at 10
  and staying at 10.
- Don't suggest migrations to other tools (Jupyter notebooks, static
  MDX, etc.) — we're staying on the Vite + React surface.

## Constraints

- Expected length: 8-12k words total (long-form review, not a ticket
  list). Per-case blocks: 400-800 words; cross-case patterns: 300-500;
  batch plan: 500-800.
- You may run bash commands to grep or ls or read full files for
  evidence — do so, don't guess.
- Write the findings file to the exact path
  `.planning/reviews/case_deep_dive_round_1_findings.md`. Do not edit
  any other file.
- This is a one-pass deep-dive. No round 2 unless user explicitly
  requests one later.

## Bias reminder

You are NOT being asked whether the current pages are correct (they
are, per V61-047). You are being asked whether they are **worth
reading as CFD pedagogy material**. The honest answer might be "no"
across all 10 cases — that's fine, say so with evidence. Your value
here is **specific, actionable remediation items per case**, not
another overall APPROVE/REJECT call.
