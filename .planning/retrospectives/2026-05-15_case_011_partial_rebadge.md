# case_011 plate-fin compact HX · V93/V94 degenerate-substrate disposition RETRO · Path A (PARTIAL rebadge) ratified

> **Disposition outcome (2026-05-15 · B62)**: case_011 v5b PARTIAL classification
> **frozen forever** under V63-A close §3.1 user-ratified PARTIAL semantics
> precedent. V64-A carry-over #1 **CLOSED via rebadge**; Done #5 counter
> advances 3/4 → 4/4 ✓ MET this dispatch. V94 §Fix(2) re-extract path
> (refactor `01_extract_surfaces.py` to `cq.Assembly` with face naming)
> acknowledged-but-not-taken in V64-A; NOT permanently foreclosed.

**Companion DEC**: `DEC-V64-A-sub-M-V64A-CASE-011-NONDEGEN-RATIFY`
(`.planning/decisions/2026-05-15_v64_sub_case_011_nondegen_ratify.md`,
Accepted 2026-05-15 · commit `2b45502`).

---

## §1 Why this retro exists

V63-A close DEC §3.1 (Accepted 2026-05-15 · `DEC-V63-A-close`) established
a governance precedent: PARTIAL → FULL upgrade requires real solver
convergence + literature comparison; **semantics rebadge requires user
ratification · NOT unilateral**. V64-A inherited 3 PARTIAL reports
(case_011 v5b + case_004 NREL Phase VI + case_016 m219 cavity), with the
V64-A charter Triggered Redirect explicitly flagging case_011 for
"semantics rebadge OR substrate swap" disposition. This retro documents
the engineering and governance trail behind the **Path A · PARTIAL
rebadge** ratification.

The retro is the case-side governance artifact (DEC is the
ratification + plan); together they constitute the closed-form trail
for V63-A carry-over #1.

---

## §2 What was on the table (4 candidates · summary)

| Path | Premise | LOC | Wall-clock | Done #5 impact | Done #1 potential | Asset reuse |
|---|---|---|---|---|---|---|
| **A · PARTIAL rebadge (RATIFIED)** | case_011 v5b PARTIAL forever · re-classify via V63-A §3.1 precedent | 0 | 0 | **CLOSED via rebadge · 3/4 → 4/4 ✓ MET** | 0 (forever PARTIAL) | sediment frozen (100% preserved as V63-A canonical reference) |
| B1 · heated-channel swap | new case · bulk-fluid convection · Kays-Crawford Nu | ~300-500 | 2-4 sessions | plan-only · stays 3/4 | 1 candidate path | sediment lost (V-row reset ~1-2/9) |
| B2 · case_011 STL re-extract (V94 §Fix(2)) | refactor `01_extract_surfaces.py` → `cq.Assembly` face naming · same plate-fin geometry + Kays-London ref | ~60-100 + sHMD | 1-2 sessions | plan-only · stays 3/4 | 1 path · highest sediment-reuse | 100% case_011 preserved + D11 validates per-face STL |
| B3 · shell-and-tube swap | new case · canonical TEMA HX · Bell-Delaware/Kern | ~400-600 | 3-5 sessions | plan-only · stays 3/4 | 1 path · highest engineering risk | sediment lost |

Full 9-dim trade-off matrix in companion DEC §4. Verbatim option
descriptions surfaced to user via AskUserQuestion (B62 turn) — user
picked Path A.

---

## §3 V94 §Fix(2) path · acknowledged-but-NOT-taken

The V-series corpus V94 entry (`industrial_case_solver_findings.md:1384` ·
"STL files emitted by cq.exporters.export() carry NO face-zone labels")
lists three remediation paths. V94 §Fix(2) verbatim:

> **Per-case CAD-side fix (case_011 future)**: refactor `scripts/build_cad.py`
> to emit hot_fluid + cold_fluid as `cq.Assembly` with `cq.Sketch.face("Tagged")`
> or equivalent face-naming, then `01_extract_surfaces.py` writes per-face
> STLs (`hot_inlet.stl`, `hot_outlet.stl`, `hot_walls.stl`, etc.) plus
> snappyHexMeshDict's geometry block declares all of them as triSurfaceMesh
> with named patches. Alternatively: write a `topoSet`+`createPatch` post-mesh
> stage that splits the `region_hot_fluid_to_domain0` patch into `hot_inlet`
> (by spatial filter: faces at x=0 or x=L) + `hot_outlet` (other side) +
> `hot_external_walls`. **Estimated 60-100 LOC.**

The path is **engineering-real and corpus-documented**. The
V64-A charter Triggered Redirect "无可换 non-degenerate substrate 路径"
premise is therefore **partially overstated** — there IS no external
substrate to swap into, but there IS an internal substrate-rebuild path
within the case_011 envelope.

### §3.1 Why Path A was ratified despite B2 being engineering-strongest

The choice is **V64-A schedule-pragmatic**, not an engineering
deficiency in B2. Reasoning chain (verbatim from B62 ratification
dialogue · user choice option description):

> "case_011 v5b stays PARTIAL forever · V63-A §3.1 precedent inherited ·
> V-row 7/9 firm preserved · Done #5 carry-over #1 CLOSED via rebadge ·
> 3/4 → 4/4 ✓ MET 本 dispatch · 0 LOC · 0 wall-clock · 释放 session
> budget 给 B61 thermo-FPE fix (Done #1 最高 ROI) · 代价: case_011 FULL
> upgrade forever closed"

ARC-GOAL `下一步建议` candidate ranking explicitly placed
**M-V64A-THERMO-FPE-FIX** as the highest Done #1 ROI candidate (战略
系统修 · 解锁 case_016 + case_006 双 case 同时 PARTIAL→FULL upgrade
potential · 双 dim 推进 = Done #1 + Done #4 同时). case_011
NONDEGEN-RATIFY ranked #3 with the explicit note "推 Done #5 但 不解
Done #1 directly under A". Selecting Path A frees the session budget
that B2 would have consumed (1-2 sessions) toward the higher-ROI
thermo-FPE work.

### §3.2 Path A is NOT a permanent foreclosure of B2

The V94 §Fix(2) path remains **corpus-documented and engineering-real**.
Future arc may re-open case_011 under V64-A successor (V65+) IF:

- case_011 PARTIAL → FULL becomes strategically valuable (e.g., compact
  HX validation tier sought for OSS release or paper publication)
- thermo-FPE fix succeeds and unlocks case_016 + case_006 FULL,
  freeing schedule for case_011 within V64-A residual budget
- new case_011-class case (case_013 / case_015 CHT-LES candidate) needs
  V94-discharge path and brings case_011 along

The disposition is **V64-A-scoped** rebadge, not a "permanently
case_011 forecloses" decision. Companion DEC §7.1 #2 records this
distinction explicitly.

---

## §4 V63-A §3.1 precedent inheritance verbatim chain

Governance precedent chain anchored to:

```
V63-A close DEC §3.1 (Accepted 2026-05-15 · DEC-V63-A-close)
  → "PARTIAL → FULL upgrade requires real solver convergence + literature
     comparison · semantics rebadge requires user ratification · NOT
     unilateral"
  → 3 PARTIAL reports credited toward Done #4 MET (case_011 + case_004 +
     case_016 all under same precedent · §3.1 enumerates each report's
     case-side-limit + advisor-stack-self-flagged status)

V64-A inherits the precedent unchanged:
  → V64-A charter §"Inherited rules from V62-A + V63-A" ratified verbatim
  → V64-A charter §"v2.3 governance compliance" anti-命题 (semantics
     rebadge must be user-ratified · NOT unilateral)
  → ARC-GOAL.md §"Done 条件 不算 Done 的反命题" anti-命题 explicit

V64-A Path A ratification inherits:
  → User picks via explicit AskUserQuestion (single-select · option text
     describing all 4 candidates + 9-dim trade-off + 2-frame recommendation)
  → Ratification recorded in companion DEC §7 with ratification vehicle
     attribution
  → Done #5 advances 3/4 → 4/4 ✓ MET; counter pure-telemetry per V133

Future arc (V65+) may invoke:
  → V63-A §3.1 → V64-A B62 §7 of DEC-V64-A-sub-M-V64A-CASE-011-NONDEGEN-RATIFY
     → next-link case-substrate ratification
```

The chain extends without modification. PARTIAL semantics precedent has
now exercised:
- V63-A close §3.1 (3 cases · all PARTIAL · 3/3 Done #4)
- V64-A B62 (1 case · perpetually PARTIAL via rebadge · 1/3 Done #4
  OR-clause)

Total: 4 PARTIAL ratifications under the precedent · 0 unilateral
rebadge attempts · governance grade preserved.

---

## §5 Done dimension impact (V64-A ARC-GOAL counter)

Pre-B62:
- Done #5 (V63-A carry-over closure): 3 / ≥4 ✓ 距 MET 差 1
- Done #4 (PARTIAL → FULL OR re-classified): 0 / ≥2

Post-B62 (Path A ratified):
- **Done #5: 4 / ≥4 ✓ MET this dispatch** — case_011 substrate is the
  4th carry-over closed (after #2 first half mesh gen v2 B54 ✓ · #6
  case_006 substrate v2 B55 ✓ · #4 D11 cross-val B60 ✓ · #1 case_011
  substrate rebadge B62 ✓)
- **Done #4: 1 / ≥2 via OR-clause re-classification credit** — case_011
  contributes "explicitly re-classified with documented rationale"
  (V64-A charter §Done dim #4 threshold OR-clause); the case_011 PARTIAL
  is the 1st re-classification credit under V64-A. case_004 + case_016
  PARTIAL → FULL upgrades remain contingent on B61 thermo-FPE fix + B57
  F-NEW-3 blade CAD fix downstream tracks.

ARC-GOAL.md edit reconciled by **main session** (NOT B62 scope):
- Tier 1 row `M-V64A-CASE-011-NONDEGEN` `[ ]` → `[x]` with B62 commit
  hashes (`2b45502` sub-DEC + `<retro-commit>` retro)
- 当前 V63-A carry-over closure: `3 / ≥4 ✓ 距 Done #5 MET 差 1` →
  `4 / ≥4 ✓ MET` (case_011 rebadge B62 added)
- 当前 V63-A PARTIAL upgrade closure: `0 / ≥2` → `1 / ≥2 via re-classification`
  (case_011 OR-clause credit added · case_004 + case_016 still pending)
- 当前 Done dims MET: `1 / 6 ✓` → `2 / 6 ✓` (Done #5 + Done #3 both MET)
- 下一步建议 update: ARC-GOAL `B62 = M-V64A-CASE-011-NONDEGEN-RATIFY`
  candidate ranked #3 was selected as Path A (rebadge) · scope-disjoint
  with B61 thermo-FPE achieved; next priorities = B61 outcome + Done #1
  strict FULL via thermo-FPE / blade CAD / new incompressible canonical
  paths

---

## §6 case_011 v5b sediment FROZEN list (canonical V63-A reference)

Path A ratification freezes case_011 v5b artifacts as **canonical V63-A
reference**. The artifact list (all preserved · NOT modified · NOT
deleted):

### §6.1 On-disk (case_011 root: `~/Desktop/case_011_plate_fin_compact_hx/`)

- `inputs/cad_codex_v1.step` (1.96 MB ASCII STEP · 3 regions ·
  2026-05-09 build_cad.py output)
- `inputs/thin_wall_inputs.yaml` (5 patches · canonical D8 + D5 +
  hot/cold fin · V63-A B46 LANDED)
- `inputs/interface_bodies.json` (2 bodies · separator_plate_3_4
  front + rear-offset · V63-A B46 LANDED)
- `inputs/interface_specs.json` (1 spec · mode=shared · D5 30 µm
  separator_3_4_d5_interface · V63-A B46 LANDED)
- `case/constant/triSurface/region_{hot_fluid,cold_fluid,solid}.stl`
  (3 single-shell watertight surfaces · V94 canonical class)
- `case/system/snappyHexMeshDict` v5b live (fragmented-mesh-mitigation
  iteration #6 · V85+V89+V92 hybrid · v3 sub-session sediment)
- `case/log/05_chtMultiRegionSimpleFoam.log` (6,921 lines · 200 SIMPLE
  iter · ≥3-orders residual reduction · −2.72e-14 continuity drift)
- `evidence/v3/{mesh,solver}_summary.json` (re-parsed v2.0 schema)
- `evidence/v3/REPORT.md` (degenerate-physics caveat §5.1)
- `evidence/v1/{thin_wall_d8,a2_d5,step_validation,mesh_summary}.json`

### §6.2 In-repo (cfd-harness-unified planning artifacts)

- `.planning/case_profiles/case_011_plate_fin_compact_hx.md` (canonical
  case profile · Kays-London ε ≈ 0.466 / Q ≈ 225 W reference declared)
- `.planning/validation_reports/v63_case_011_v5b_validation_report.md`
  (V63-A B48 LANDED · PARTIAL verdict · 11 advisor findings · attribution
  chain CAD→STL→sHM→solver complete)
- `.planning/decisions/2026-05-15_v63_sub_case_011_substrate.md`
  (V63-A B46 sub-DEC · V-row 3/9 → 7/9 firm · Done #6 cross-case 3/3
  MET)
- `.planning/decisions/2026-05-14_v61_198_sub_case_011_v3_solver_e2e.md`
  (V61 v3 sub-session sub-DEC · V94 surfacing)
- `.planning/retrospectives/2026-05-15_case_011_v5b_substrate_extension.md`
  (B46 retro)
- `.planning/retrospectives/2026-05-14_stack_track_c_session_1_case_011_v5b.md`
  (TRACK-1 retro)
- `.planning/retrospectives/2026-05-14_stack_track_c_session_1_rerun_case_011_v5b.md`
  (TRACK-1-rerun retro · 100% PASS adoption B33)
- `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_2_case_011.md`
  (v3 sub-session retro)
- `.planning/cross_cuts/v_series_case_011_append_2026-05-09.md`
  (V47-V50 + S22-S23 case_011 append)
- `.planning/methodology/kickoff/case_011_{validation,plate_fin_compact_hx,codex_request,codex_response}.md`
- `scripts/v63_case_011_substrate/run_extended.py` (V63-A B46 Path B
  Python runner · 7 advisors · 11 findings · LANDED)
- `scripts/v63_case_011_substrate/stack_report_{http_path_a_b48,python_extended}.json`
  (V63-A B48 Path A + Path B reports)
- `scripts/v63_case_011_substrate/audit_artifact_http_path_a_b48.json`
  (V63-A B48 audit-side snapshot)

### §6.3 V-series corpus contribution (preserved · V-row 7/9 firm)

- V10 thin_wall (D8 0.6 mm canonical) · firm
- V20+V96 unit_detector · firm
- V22+V25+V33+V36+V42+V43+V50 A2-v2 plate-plate adjacency (D5 30 µm) ·
  firm (the 7 cross-case V-rows that fire on the D5 substrate)
- V30 thin_wall sliver class (multi-patch) · firm
- V94 face-label loss (D11 canonical 6-orphan replay) · firm
- D5 sub-mm plate-plate offset (30 µm) · firm
- D8 0.6 mm rear fin (shares V10) · firm

Total: **7 distinct V-rows + 2 shared = 9/9 mentioned · 7/9 firm**.
This is the highest single-case V-row capture in V63-A, contributing to
Done #6 over-met 3/2 clause-1 (case_011 7/9 firm + case_004 5/9 firm +
case_006 5/9 firm).

### §6.4 D11 advisor anchoring

D11 `stl_face_label_validator` (V63-A `DEC-V63-A-sub-D11` LANDED · 21
KB · 3 detection paths) regression-test #11 is **anchored on case_011
V94 canonical 6-orphan replay**. The advisor remains LANDED; the
canonical regression test continues to fire firmly on case_011 substrate.

V64-A `DEC-V64-A-sub-M-V64A-D11-CROSS-VAL` (B60 LANDED) cross-validated
D11 on case_018 (cyclone V94 4 orphan ✓) + case_019 (Kenics partial V94
3 orphan ✓) + case_020 (porous filter V94 counter-example 0 dispatch ✓);
D11 [QUESTIONABLE] promotion-gate marker dischargeable per B60.

case_011 remains the **primary D11 anchor** even after cross-validation —
the V94 canonical 6-orphan replay (parts_manifest with face_labels
overlay + stl_face_normals 3 parent-body keys) is the exact regression
test that D11 was authored against.

---

## §7 4Q gate inline echo (V64-A inherited rule per ARC-GOAL §沿用 V62-A + V63-A 不变规则)

| Q | Gate | Verification this dispatch | Verdict |
|---|---|---|---|
| Q1 | LLM offline · workflow runs without LLM keys | This sub-DEC + retro are Markdown documentation. No LLM advisor calls in authoring path. Companion DEC (commit `2b45502`) + this retro (commit-2 of B62) authored in Claude Code Opus 4.7 (1M context) main session with no external LLM advisory dispatch. case_011 v5b substrate · advisor stack · validation report all unchanged (NOT re-run this dispatch · all are V63-A LANDED artifacts) | PASS |
| Q2 | artifacts emitted | Companion DEC `.planning/decisions/2026-05-15_v64_sub_case_011_nondegen_ratify.md` (614 lines · Status: Accepted · commit `2b45502`) + this retro `.planning/retrospectives/2026-05-15_case_011_partial_rebadge.md` (commit-2 pending). Pre-existing case_011 v5b artifacts (§6.1, §6.2) preserved unchanged | PASS |
| Q3 | TrustGate · explainable trail | Companion DEC §3 enumerates 4 candidate paths with primary-source citations: Kays-London (3rd ed 1984 §10) for case_011 reference; Kays-Crawford (4th ed 2005 §9.5/§9.7) for B1; Kakac & Liu (3rd ed 2012 §8/§11) + Shah & Sekulić (2003 §9) for B3; V-series corpus V93+V94 verbatim citations from `industrial_case_solver_findings.md:1372,1384`; V63-A close §3.1 verbatim governance citation. §7 ratification record + §7.1 ratified semantics enumerate binding outcomes (6 numbered items). User ratification vehicle attributed (AskUserQuestion · single-select · option text verbatim) | PASS |
| Q4 | advisor-only · NOT driver | Ratification is engineering trade-off decision (user-marked per V63-A §3.1 precedent). Advisor stack untouched (`ui/backend/services/advisor_stack.py` + all 11 LANDED advisors A1/A2-v2/A3/A4/A5/A7/A8/A10/D6/D10/D11 unchanged). D11 V94 catcher continues to fire firmly on case_011 substrate. No case directory mutations. No automated override of engineer judgment. case_011 v5b artifacts frozen as V63-A canonical reference per §6 above | PASS |

All 4 gates PASS. The dispatch is a **governance-grade ratification +
documentation work**; the "4Q gate" applies trivially because no
runtime / no advisor / no case directory mutation is in scope.

---

## §8 v2.3 compliance + governance counter

- **Scope class**: sub-DEC + retro (documentation only · 2 files · 0
  source LOC). Below charter threshold (no schema break · no security
  boundary · 0 shared code paths cross-cut).
- **Counter (autonomous_governance · pure-telemetry per V133)**: +1
  for companion DEC (commit `2b45502` · counter for V64-A arc tracks
  arc-size in retro reconcile · no STOP semantics)
- **DEC frontmatter**: 6 required v2.3 fields (decision_id / title /
  status / parent_dec / phase / notion_sync_status) + 3 optional
  (authored_by / authored_at / confidence) all populated in companion
  DEC
- **Codex review**: skipped (no security boundary · no source change ·
  no routes/ai_review.py / pages/ touch · v2.2 1-sync-trigger does not
  apply). Round count: 0.
- **Kogami invocation**: not requested (v2.3 opt-in only · user did not
  invoke `scripts/governance/kogami_invoke.sh`). Ratification semantics
  is engineering trade-off decision class, identical to V63-A §3.1
  user-ratification — not a strategic narrative event requiring
  independent strategic review.
- **Notion sync**: pending session-end batch. Companion DEC Status =
  Accepted → qualifies for sync per v2.3 round-1 loosen rule (only
  Accepted DECs sync; retro stays repo-only per same rule). Main session
  reconciles session-end batch.
- **Cadence floor (30)**: not triggered. 0 source LOC churn.
- **Spike-class**: not applicable (this is sub-DEC, not code-change
  spike).
- **Surface scan trailer**: clean. No source files touched. No new
  top-level routes/ / pages/ created.
- **pre-implementation surface-scan**: skipped per DEC-V61-088 skip
  clause "documentation-only ratification".
- **4Q gate**: all 4 PASS per §7 above. Inline echo recorded.

---

## §9 Open follow-ups (per Path A ratification · NOT blocking B62)

1. **V94 §Fix(2) re-extract path stays acknowledged-but-not-taken in
   V64-A**. Future arc may re-open IF (a) case_011 PARTIAL → FULL becomes
   strategically valuable, OR (b) thermo-FPE fix unlocks case_016 +
   case_006 FULL freeing V64-A residual schedule, OR (c) new
   case_011-class case (case_013 / case_015 CHT-LES candidate) needs
   V94-discharge path and brings case_011 along.
2. **Label canonicalization** (corpus hygiene): future V-series corpus
   entries should NOT use "V93 degenerate-physics" as a casual case_011
   label (corpus V93 is case_009 reacting-low-Mach T-floor rule;
   case_011 degenerate root cause is corpus V94 STL face-label loss).
   Recommended canonical label going forward: **"V94-induced degenerate
   physics"** OR **"case_011 conduction-dominated equilibration state"**.
   This sub-DEC + retro use the disambiguated label
   "V93/V94 degenerate-substrate" deliberately. V63-A close §3.1 +
   ARC-GOAL Triggered Redirect language ("V93 degenerate") preserved
   verbatim in historical references but not extended in new artifacts.
3. **ARC-GOAL.md reconcile** (main session · NOT B62 scope): Tier 1 row
   `M-V64A-CASE-011-NONDEGEN` `[ ]` → `[x]` with B62 commit hashes ·
   Done #5 counter advance 3/4 → 4/4 ✓ MET annotation · Done #4
   re-classification credit 0/2 → 1/2 OR-clause annotation · 下一步建议
   block re-anchor (B61 outcome dependency + Done #1 strict FULL
   candidate ranking refresh after Path A landed).
4. **Notion sync** session-end batch: companion DEC (Accepted) qualifies;
   this retro stays repo-only per v2.3 round-1 loosen rule.
5. **case_011 v5b sediment preservation discipline**: §6 freeze-list
   becomes the canonical V63-A case_011 artifact inventory. Future
   refactors / consolidations / sediment audits should treat the list
   as immutable reference set; deletions require V64-B-or-later
   governance review (V64-A is rebadge-not-delete).

---

## §10 Governance precedent extension (V63-A §3.1 → V64-A B62)

V63-A close §3.1 (Accepted 2026-05-15) established precedent **for
PARTIAL admission as Done-dim MET**:
- Limit must be case-side (substrate / mesh / runtime / experimental
  data access · not stack-internal logic gap)
- Advisor stack must have predicted / classified / flagged the limit
  pre-run
- User explicitly ratifies the PARTIAL crediting

V64-A B62 extends the precedent to **PARTIAL admission AS PERPETUAL via
rebadge** (V64-A charter Done #4 OR-clause "explicitly re-classified
with documented rationale"):
- Same 3 conditions as V63-A §3.1 (case-side limit · advisor-self-flagged
  · user-ratified)
- PLUS: documented rationale for non-pursuit of FULL upgrade (V94
  §Fix(2) acknowledged-but-not-taken with reason)
- PLUS: explicit forecast on future arc re-openability (§3.2 above)

Future case-substrate ratification chains may invoke:

```
V63-A §3.1 → V64-A B62 §7.1 of DEC-V64-A-sub-M-V64A-CASE-011-NONDEGEN-RATIFY
                                  → ... (next-link case-substrate ratification)
```

Provided each new link satisfies the 3 V63-A §3.1 conditions + 2 V64-A
B62 extensions (rationale documentation + future-arc re-openability
disclosure).

---

## §11 Confidence + signed-off chain

- **confidence: med**. Numerical claims sourced from V63-A close DEC
  (governance), V64-A charter DEC (governance), validation report
  (case-side e2e), V-series corpus V93+V94 (sediment), and AskUserQuestion
  ratification vehicle (user-explicit). Trade-off matrix is engineering
  judgment (LOC estimates, wall-clock estimates, asset-reuse assessment) —
  numerical precision is informed-estimate not measured.
- **Signed-off chain**:
  - Authored by: Claude Code Opus 4.7 (1M context) · main session B62
  - Ratified by: User (cfd-harness-unified maintainer) via AskUserQuestion
    answer · 2026-05-15
  - Governance anchored to: V63-A close DEC §3.1 (Accepted 2026-05-15) +
    V64-A charter DEC §"Inherited rules" (Accepted 2026-05-15)
  - Companion DEC: `DEC-V64-A-sub-M-V64A-CASE-011-NONDEGEN-RATIFY`
    (commit `2b45502`)
- **Anti-命题 self-check** (V64-A charter §反命题 verification):
  - ❌ "PARTIAL → FULL upgrade through 'rewriting PARTIAL semantics'
    bypassing actual convergence" — NOT applicable here (Path A is
    re-classification not upgrade; semantics is user-ratified via
    explicit AskUserQuestion vehicle not unilateral; V64-A charter Done
    #4 OR-clause explicitly admits "OR explicitly re-classified with
    documented rationale" path)
  - ❌ "V-row alias 灌水" — NOT applicable (no new V-rows authored;
    case_011 sediment V-row 7/9 firm preserved frozen; future
    V-series V101+ corpus entries are separate scope)

---

**End of retro.** Path A · PARTIAL rebadge · V63-A close §3.1 precedent
inherited · Done #5 carry-over #1 CLOSED via rebadge · 3/4 → 4/4 ✓ MET ·
V94 §Fix(2) re-extract path acknowledged-but-not-taken (NOT permanently
foreclosed) · case_011 v5b sediment frozen as canonical V63-A reference.
B62 commits: companion DEC `2b45502` + this retro `<commit-2>`.
