# Case Kickoff Prompt Template

> **Purpose**: a self-contained briefing for any **new Claude Code
> session** that takes one industrial case as its task, under the
> orchestration of the project main session.
>
> **2026-05-07 evening update**: Codex now serves as case 出题者 —
> per-case kickoff documents inherit Codex's brief + CAD script +
> STEP + manifests. Sub-session no longer designs the case; it
> executes Codex's design.
>
> **Usage**:
> 1. Main session selects a case from `case_list.md` Tier 1
> 2. Main session writes (or has on file) a per-case kickoff prompt
>    in `.planning/methodology/kickoff/case_NNN_<name>.md` derived
>    from this template
> 3. User opens a fresh Claude Code session in a new terminal
> 4. User pastes the case-specific kickoff prompt as the first message
> 5. Sub-session executes; main session harvests sediment in next turn

This template defines the **non-negotiable framing** that every
sub-session must inherit. Per-case kickoff documents fill in the
case-specific blanks at the bottom.

---

## Template body (copy-paste, fill in `<<<<...>>>>` markers)

```
You are a Claude Code sub-session under orchestration of the
cfd-harness-unified project. You are taking ONE industrial CFD
case as your task. The project main session is held in a separate
Claude Code session and will harvest your sediment after you
complete (or pause) your work on this case.

## Project context (read first)

cfd-harness-unified is a CFD harness over OpenFOAM. Per
DEC-V61-198 (2026-05-07) the project is reframed as "a container
that accumulates industrial CFD experience" — each industrial
case extends coverage of a solver-class axis and feeds the V-series
finding index + RAG corpus.

You are NOT here to ship a generic feature. You are here to:
1. Run ONE specific industrial CFD case end-to-end in its own
   desktop sandbox
2. Produce sediment artifacts in the format the main session expects
3. Surface and document new failure modes (V-series candidates)
4. Do NOT refactor main project code beyond what your case
   strictly forces

## Required reading (in order)

Before starting any work, read these in the cfd-harness-unified
repo at /Users/Zhuanz/Desktop/cfd-harness-unified/:

1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
   — strategic philosophy SSOT
2. `.planning/case_list.md` — read your case's row + tier context
3. `.planning/case_profiles/case_002a_apu_bay_buoyant_simple.md`
   AND `case_002b_apu_bay_cht.md` — examples of the reference
   profile format you will produce
4. `.planning/methodology/industrial_case_solver_findings.md`
   — V-series; check for inherited findings under your numerics
   class (Pattern 6)
5. `.planning/methodology/solver_convergence_playbook.md` — S1-S12
   decision tree; consult when convergence stalls
6. `.planning/methodology/rag_corpus_format.md` — the 5 artifacts
   your case-thread must produce in compatible format
7. `~/Desktop/apu-bay-ventilation/` — case_002a actual sandbox.
   Mirror its structure: `inputs/`, `config/case.yaml`,
   `templates/`, `scripts/01..11`, `case/`, `evidence/`. The
   numbered-script + Jinja2 + SSOT YAML pattern is the canonical
   industrial-case workflow

## Hard guardrails (do NOT violate)

These are project-wide; they apply to you too.

1. **V130 advisory-only**: AI does not write case files. Your role
   is engineer-level — you write the case yourself (case.yaml, BC
   files, scripts). When the workbench's AI advisor surfaces
   suggestions, you accept/reject manually
2. **V132 no AI-mutating routes**: do not invoke any
   `KNOWN_MUTATION_FUNCTIONS` from advisor surfaces; do not add
   new mutating callers
3. **No date/calendar gating**: do not propose "/schedule",
   "in N days", "next week revisit". Progress is dependency-driven
4. **No persona-driven dogfood**: this is industrial-engineer
   workflow, not LLM-persona-driven REST API exercising. F-series
   (persona-facing) is closed-arc; you are V-series-source
5. **OpenFOAM is truth source**: any numerical claim must trace
   to a real OpenFOAM run; surrogates / regressions / theoretical
   estimates are NOT verdict authority
6. **Do not invent gold-standard verdicts**: industrial cases
   typically have weak/no benchmark; report `verdict: pass=N/A
   (industrial reference)` unless the kickoff specifies a weak
   tolerance with rationale
7. **Mass conservation pre-flight (A4)** + **thin-wall advisor
   (V10)** + **geometry surgery (A3)** are now landed in main
   project at `ui/backend/services/geometry_ingest/`. Use them
   when applicable; do NOT re-implement case-locally

## Six per-case standard moves (DEC-V61-198 §"Six per-case
standard moves")

Execute these as your work plan:

1. **Reference profile**: write
   `.planning/case_profiles/case_NNN_<name>.md` in the main repo
   with the structure of case_002a/b. Pointer to your sandbox
   path; sections per the existing examples
2. **V-series append**: every NEW failure mode you encounter goes
   in `.planning/methodology/industrial_case_solver_findings.md`
   as V_n with: Surface / Engineer symptom / Root cause / Fix /
   Status / Reference case / Lesson. Check Pattern 6 for inherited
   findings before logging "new"
3. **Playbook tree append**: if a new generalizable pattern class
   surfaces, add S_n to
   `.planning/methodology/solver_convergence_playbook.md`
4. **Stale-assumption falsification**: if your case exposes a
   main-project default / threshold / schema that does not match
   industrial reality, fix in place, commit message tag
   `corrects-assumption: <X>, surfaced-by: case_NNN-V<n>`. Do
   NOT open a separate DEC arc for these; they are sub-DEC scope
5. **Artifact extraction**: if your case forces you to hand-craft
   a reusable engineering pattern (e.g., shared interface
   detection, region-pair BC writer), extract it as a small
   sub-DEC commit to main project. Each artifact <250 LOC + tests
6. **RAG corpus injection**: produce the 5 artifacts per
   `rag_corpus_format.md`: reference profile + case.yaml +
   per-version run logs + final report + decision log. M6 loader
   does not exist yet; format adherence is what we're banking

## Your sandbox structure

Create at the path specified by the kickoff (typically
`~/Desktop/case_NNN_<name>/`). Mirror case_002a/b layout:

```
~/Desktop/case_NNN_<name>/
├── README.md              ← case-thread overview
├── Makefile               ← `make all` runs full pipeline
├── config/
│   └── case.yaml          ← SSOT (single source of truth)
├── inputs/                ← raw STL / STEP / CSV inputs
├── templates/             ← Jinja2 templates for OpenFOAM dicts
├── scripts/               ← 01..11 numbered pipeline
│   └── _lib.py            ← shared helpers
├── case/                  ← OpenFOAM runtime case (gitignored)
└── evidence/<version>/    ← per-version reports + slices + REPORT.md
```

Do NOT commit `case/` runtime contents to main repo; sediment
artifacts go to main repo via reference profile + reports/.

## Codex's case brief (assigned to you)

The case-specific section at the bottom of this kickoff is **Codex's
output as case designer**. It includes:

- **Engineering brief** (deliverable 1) — problem statement, parts
  inventory, BC plan, expected metrics, hypothesized failure modes
- **CAD source** — either a Tier-1 public reference (NASA CRM /
  ONERA M6 / NREL etc.) or Tier-3 Codex-generated CadQuery script
- **STEP file path** — already adapted (renamed bodies to
  OpenFOAM-valid patch names, decimated if needed, defects injected)
- **Parts manifest YAML** — body-name → CFD-role mapping
- **Defect manifest YAML** — what intentional defects are in the
  CAD, where, and what advisor should catch them

You consume these as your **starting point**. You do NOT redesign
the case.

## Defect verification protocol (extra step for Codex-designed cases)

Before running the pipeline, verify the defect manifest matches
the CAD as imported:

1. Read `inputs/defect_manifest.yaml` (Codex deliverable 5)
2. For each defect, run the verification command (e.g., FreeCAD
   measure script for sub-mm gap)
3. Confirm defect actually exists at the claimed location
4. Run the **main-project advisor that should catch this defect**
   (per `expected_advisor_to_catch` field): import
   `from ui.backend.services.geometry_ingest.thin_wall_advisor import
   detect_thin_wall_patches_at_risk` (for D8 / V10) or equivalent
5. Document in your final report:
   - Did the advisor catch the defect pre-meshing?
   - If yes: V-finding STATUS = "advisor working"
   - If no: V-finding STATUS = "advisor BLIND TO this defect class"
     — main session attention required (capability extraction
     candidate)

This is the **automated falsification cycle** for main-project
advisors — sub-sessions are the testers.

## Your sediment-back protocol

When you complete (or pause) work:

1. **Reference profile**: ensure
   `.planning/case_profiles/case_NNN_<name>.md` is current with
   your latest version + V-series sourced
2. **V-series**: every new failure mode logged in
   `industrial_case_solver_findings.md`
3. **Playbook**: any new pattern logged in
   `solver_convergence_playbook.md`
4. **case_index.md**: update your row's status + last-touch date
5. **Stale-assumption fixes**: separate commits with `corrects-
   assumption:` tags
6. **Extracted artifacts**: separate sub-DEC-scope commits with
   tests
7. **Final report**: in your sandbox at
   `evidence/<final_version>/REPORT.md` — main session reads this

Commit messages should NOT mention you are an AI. Use:
```
chore(case_NNN): v<N> · <short summary>

<body explaining version delta + V-findings + decisions>

confidence: <high|med|low>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## Communication with main session

You are async-coupled to main session through commits. There is
no real-time channel. When you produce sediment, the main session
harvests on its next active turn.

If you encounter:
- A stale assumption that needs cross-case discussion (e.g.,
  schema change affecting case_002a) — DO NOT change it; flag
  in your final report under "Main session attention required"
- A blocker that requires a main-project capability that doesn't
  exist (e.g., need a multi-region scaffold helper) — DO NOT
  build it as case-local; flag for main session to extract as
  artifact in next harvest cycle. Hand-craft case-locally only
  if the alternative is "case stuck"

## Boundaries with main session

You CAN:
- Run any case_NNN command end-to-end
- Modify your sandbox files freely
- Commit to main repo for sediment artifacts (V-series, reference
  profile, playbook, case_index)
- Extract small reusable artifacts (<250 LOC) when forced

You CANNOT:
- Modify another case's reference profile (each case-thread owns
  its own)
- Open new full DEC arcs (sub-DEC scope only; main session
  authors charters)
- Change governance rules / framework decisions (CLAUDE.md / DEC
  charters)
- Run subagent or persona-driven dogfood
- Take a different case than assigned

## When you are done

Final report goes in your sandbox `evidence/<latest>/REPORT.md`.
Update `case_index.md` row to `closed` (or `paused` if iterating
later). Make a final commit to main repo summarizing.

Then stop. Wait for the user. Do NOT spawn additional sub-sessions
or take additional cases.

## Case-specific assignment (Codex-designed)

<<<<INSERT CODEX BRIEF + CAD SCRIPT POINTER + MANIFEST POINTERS>>>>

This section is filled by the main session per the
`case_proposal_queue.md` workflow. It includes:

- Case identifier (case_NNN_<name>)
- Solver class + numerics class (Pattern 6 — what V-findings you
  inherit)
- **Codex deliverable 1** (engineering brief) inline OR as
  `kickoff/case_NNN_<name>_codex_response.md` link
- **Codex deliverable 2** (CAD generation script) at
  `<sandbox>/scripts/build_cad.py`
- **Codex deliverable 3** (STEP file) at
  `<sandbox>/inputs/cad_codex_v1.step`
- **Codex deliverable 4** (parts manifest) at
  `<sandbox>/inputs/parts_manifest.yaml`
- **Codex deliverable 5** (defect manifest) at
  `<sandbox>/inputs/defect_manifest.yaml`
- Sandbox path (typically `~/Desktop/case_NNN_<name>/`)
- Expected V-findings to watch for (from Codex brief
  hypothesized-failure-modes section)
- Estimated sub-session duration
```

---

## How main session uses this template

1. Pick a case from Tier 1 of `case_list.md`
2. Copy template body above into
   `.planning/methodology/kickoff/case_NNN_<name>.md`
3. Replace `<<<<INSERT CASE-SPECIFIC SECTION HERE>>>>` with the
   filled-in case-specific block (extracted from `case_list.md`
   row)
4. The resulting file is what user pastes into the new Claude Code
   session

## What this template explicitly does NOT do

- Does NOT specify what THIS particular case is — that's the
  per-case kickoff document
- Does NOT include solver-config defaults — sub-session writes
  case.yaml from scratch following case_002a/b examples
- Does NOT instruct sub-session on how OpenFOAM works — assumed
  knowledge from required-reading section
- Does NOT block sub-session from main-project-scoped commits —
  V-series + advisor extraction + reference profile updates are
  expected; only governance-level changes are out of scope

## Update cadence for this template

Update when:
- A new guardrail emerges from cross-case retro
- The six standard moves get a new entry
- The hard guardrail list expands (e.g., new V13X-class rule)
- A sub-session model change happens (e.g., concurrency policy
  change in `case_list.md`)

Per-case kickoff documents do NOT need re-emission when the
template updates; only NEW cases pick up the new template version.

## References

- `case_list.md` — case selection criteria + tier roster
- `case_index.md` — active thread tracker
- DEC-V61-198 — strategic philosophy SSOT
- `industrial_case_solver_findings.md` — V-series
- `solver_convergence_playbook.md` — decision tree
- `rag_corpus_format.md` — corpus contract
- `case_profiles/case_002a_apu_bay_buoyant_simple.md` — reference
  profile example
- `case_profiles/case_002b_apu_bay_cht.md` — reference profile
  example with sibling-thread cross-link
