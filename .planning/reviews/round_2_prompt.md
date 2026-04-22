# Codex Round 2 — DEC-V61-046 remediation re-review

You are a 3-persona code & product reviewer for the `cfd-harness-unified`
project (root `/Users/Zhuanz/Desktop/cfd-harness-unified`). You already
produced `.planning/reviews/round_1_findings.md` (CHANGES_REQUIRED on all
3 roles, 0 blockers, ~15 major/minor) after reviewing commits
`87b3b39..a1feef9`.

**Your job this round**: decide whether the 4-commit remediation
addressed your round-1 findings, whether the 2 deferrals are
acceptable, whether any new regressions were introduced, and whether
the consolidated verdict should escalate to APPROVE /
APPROVE_WITH_COMMENTS, or stay CHANGES_REQUIRED for a round 3.

## Commits under review (round-2 scope)

All on `origin/main`, HEAD=`61140c4`. Re-review window is
`5c90ea1..61140c4` (the DEC proposal + 4 remediation batches + DEC
round-log update). Earlier commits `87b3b39..a1feef9` are already
accepted context from round 1.

- `6c53986` fix(contracts): **batch 1 — factual corrections**
  - `knowledge/gold_standards/lid_driven_cavity.yaml` — precondition #4
    split into two explicit-false preconditions (v_centerline reference
    values, primary_vortex_location); mesh wording "129² DNS-quality
    shoulder" → "Ghia high-resolution reference shoulder"
  - `knowledge/gold_standards/backward_facing_step.yaml` — turbulence
    model `kOmegaSST` → `kEpsilon` per actual adapter code; plateau
    wording `<2%` → regime-level phrasing
  - `knowledge/gold_standards/impinging_jet.yaml` — A4 iter-cap surfaced
    as symptom, root cause declared composite (URF / p-v coupling /
    thermal BC / axis patch), deferred to Phase 9
  - `knowledge/gold_standards/plane_channel_flow.yaml` — mesh labels
    "WR-LES/DNS" → honest "80³/160³ cells"
- `fa7d96d` fix(dashboard): **batch 2 — source-of-truth parity**
  - `src/report_engine/contract_dashboard.py` — 5 DashboardCaseSpec
    entries retarget `gold_file` to canonical yamls
    (lid_driven_cavity_benchmark → lid_driven_cavity, etc.);
    `report_case_id` intentionally kept legacy because on-disk run
    fixtures live at legacy paths
  - `tests/test_report_engine/test_contract_dashboard_report.py`:
    - new `test_dashboard_gold_files_match_canonical_whitelist_yamls`
    - new `test_normalize_contract_class_maps_satisfied_prefixes`
    - distribution assertion updated:
      SATISFIED=4, COMPATIBLE=1, COMPATIBLE_WITH_SILENT_PASS_HAZARD=1,
      PARTIALLY_COMPATIBLE=2,
      INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE=2, UNKNOWN=0
- `6911611` feat(learn): **batch 3 — buyer-facing demo front door**
  - `ui/frontend/src/pages/learn/LearnHomePage.tsx` — bilingual hero
    ("Prove a CFD result is physically trustworthy, not just
    numerically converged" + 让 CFD 结果可信而不只是收敛) + 3-strip
    differentiation (real-solver evidence, literature-backed
    comparator, signed audit package); buyer CTA strip (GitHub / Pro
    Workbench / mailto); student framing demoted to supporting teaser
  - `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` — new
    `PhysicsContractPanel` at top of Story tab surfacing
    `contract_status` verdict + preconditions list with
    [✓]/[~]/[✗] markers
  - `ui/frontend/src/components/learn/LearnLayout.tsx` — two
    placeholder-alert nav items removed
  - `ui/frontend/src/components/Layout.tsx` — sidebar tagline
    buyer-readable; Path-B provenance moved to footer
  - V&V40 wording softened to "inspired by, not equivalent"
- `93e84cf` fix(robustness): **batch 4 — edge cases & cleanup**
  - `ui/backend/routes/case_export.py` — new `_precondition_marker`
    helper covering 14 input shapes (True/False/"true"/"false"/
    "partial"/"partially"/1/0/None/unknown→✗)
  - `ui/backend/tests/test_case_export.py` — 2 new tests
    (three-state boolean/string coverage; live [✗] render from LDC
    explicit-false preconditions)
  - `ui/backend/services/validation_report.py` — 2 docstring drifts
    fixed (reference-first → audit_real_run-first per DEC-V61-035)
  - `ui/frontend/README.md` — 5173 → 5180
- `61140c4` docs(dec): round-1 round-log update (no code).

## Round-1 findings mapping (your own round-1 IDs)

| R1 ID | What you asked for | Where it was addressed | Accept? |
|---|---|---|---|
| R1-M1 | Hero not buyer-facing | `LearnHomePage.tsx` batch 3 | verify bilingual + buyer-friendly |
| R1-M2 | FAIL-dashboard first impression | PhysicsContractPanel surfaces contract_status up front in StoryTab | verify ordering |
| R1-M3 | No buyer CTA | CTA strip in LearnHomePage batch 3 | verify mailto / Pro / GitHub links present |
| R1-M4 | No differentiation | 3-strip in hero | verify clarity |
| R1-M5 | Placeholder alert nav | Removed in LearnLayout batch 3 | verify no dead links |
| R1-N1 | Sidebar tagline | Rewritten in Layout.tsx batch 3 | nit |
| R2-M1 | LDC precondition #4 should be false | LDC yaml batch 1 | verify split into #4 and #5 both false |
| R2-M2 | BFS `<2%` plateau overstated | BFS yaml batch 1 | verify regime wording |
| R2-M3 | plane_channel mesh labels WR-LES/DNS misleading | plane_channel yaml batch 1 | verify "80³/160³ cells" honest |
| R2-M4 | impinging_jet A4 root-cause | impinging_jet yaml batch 1 | verify composite root-cause wording + Phase 9 defer |
| R2-M5 | contract_status taxonomy refactor (3-field split) | **DEFERRED** per DEC-046 round log | **decide if deferral acceptable** |
| R2-M6 | V&V40 wording | Softened in LearnHomePage batch 3 | verify "inspired by" not "equivalent" |
| R2-M7 | Dashboard reads legacy gold | Batch 2 retarget | verify both in dashboard.py and PhysicsContractPanel |
| R2-M8 | Spalding fallback hard-hazard | **DEFERRED** per DEC-046 round log | **decide if deferral acceptable** |
| R2-N1 | "DNS-quality shoulder" | LDC wording batch 1 | nit |
| R3-M1 | Dashboard legacy gold paths | Batch 2 parity test | verify `report_case_id` kept-legacy rationale is sound |
| R3-M2 | BFS kOmegaSST wrong | BFS batch 1 | verify `kEpsilon` |
| R3-N1 | Missing prefix test | `test_normalize_contract_class_maps_satisfied_prefixes` batch 2 | verify |
| R3-N2 | 3-state marker edge cases | `_precondition_marker` batch 4 | verify 14 shapes sufficient |
| R3-N3 | No [✗] regression test | `test_export_bundle_renders_fail_marker_on_explicit_false` batch 4 | verify |
| R3-N4 | Docstring drift | Two fixes batch 4 | verify |
| R3-N5 | Frontend README 5173 | Batch 4 | verify 5180 |

## Two deferrals — decide explicitly

1. **R2-M5 (contract_status taxonomy refactor)** — rationale in DEC-046
   round log: splitting into base_verdict / scope_qualifier /
   hazard_flags ripples through dashboard + export + TypeScript types +
   10 YAMLs + tests; own DEC warranted. Current long-prefix strings are
   consumed by `_normalize_contract_class` via `.startswith()`, so no
   silent drift risk *today*. **Do you accept the deferral, or is this
   a round-2 blocker?**

2. **R2-M8 (Spalding-fallback hard-hazard)** — rationale: promoting the
   internal `cf_spalding_fallback_activated` flag to a first-class
   `AuditConcern` requires `foam_agent_adapter` change + concern-code
   plumbing across attestor/comparator. Current fallback path is
   documented `partial` in TFP gold precondition #4 with explicit
   follow-up audit note, not silently active. **Accept the deferral or
   raise as round-2 blocker?**

## What you must output

Write a full findings file to `.planning/reviews/round_2_findings.md`
with the following structure (same conventions as round 1):

```
# DEC-V61-046 Round 2 — Codex Consolidated Verdict

**Overall verdict**: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
**Blocker count**: N

## Role 1 — 商业立项 demo 评审专家
**Verdict**: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
- R1-M1 [verify]: status (addressed | partially | not addressed) — evidence (file:line)
- ... (continue for each R1-* item)
- New findings (if any): R1-M6, R1-N2, ...

## Role 2 — CFD 仿真专家工程师
**Verdict**: ...
- R2-M1 [verify]: ...
- R2-M5 [deferral]: **accept | reject** — reasoning
- R2-M8 [deferral]: **accept | reject** — reasoning
- ...
- New findings: ...

## Role 3 — Senior Code Reviewer
**Verdict**: ...
- R3-M1 [verify]: ...
- New findings: ...

## Regressions / new issues (any persona)
- ...

## Deferral judgment (single paragraph each)
- R2-M5:
- R2-M8:

## If CHANGES_REQUIRED: round-3 directive
Minimum set of changes to land APPROVE. Be specific (file:line + diff
intent).
```

## Severity scheme

- 🔴 **Blocker** — must fix before APPROVE
- 🟠 **Major** — should fix, but APPROVE_WITH_COMMENTS is acceptable if
  the deferral is explicit and surfaced
- 🟡 **Minor** — nice to have
- 🟢 **Nit** — no action needed

## Evidence discipline

- Every finding must cite `path:line` (or `path:start-end`)
- Every verify decision must name the specific commit sha you looked at
- Do not flag anything as a blocker without a concrete before/after
  diff argument
- If you cannot verify a claim (e.g., no way to run the frontend), say
  so and mark the finding as "not verified"

## Self-bias reminder

You wrote the round-1 findings. Resist the temptation to escalate
"partially addressed" items just because the remediation isn't exactly
what you would have written. The bar is: *does the demo now work for
its intended audience, are the physics claims honest, and is the code
correct*. If yes, APPROVE or APPROVE_WITH_COMMENTS — don't chain
rounds to demonstrate activity.

Output only `.planning/reviews/round_2_findings.md`. Do not edit any
other file.
