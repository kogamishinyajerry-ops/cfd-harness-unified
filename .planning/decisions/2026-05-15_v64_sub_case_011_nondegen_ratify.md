---
decision_id: DEC-V64-A-sub-M-V64A-CASE-011-NONDEGEN-RATIFY
title: case_011 plate-fin HX V93/V94 degenerate-substrate disposition ratification · 4-candidate trade-off + Path A (PARTIAL rebadge) ratified · Done #5 carry-over #1 CLOSED via rebadge · 3/4 → 4/4 ✓ MET
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 1 · M-V64A-CASE-011-NONDEGEN-RATIFY (V63-A carry-over #1 disposition · per V63-A close §3.1 user-ratification precedent · Path A ratified 2026-05-15)
notion_sync_status: synced 2026-05-15 (https://www.notion.so/361c68942bed8171b6aeecfe3e5fbd14)
authored_by: Claude Code Opus 4.7 (1M context) · main session B62
authored_at: 2026-05-15
confidence: med
---

## Status

**Accepted 2026-05-15** — user ratified **Path A · PARTIAL rebadge** per
V63-A close §3.1 precedent (see §7 ratification record). case_011 v5b
stays PARTIAL forever as user-ratified case-side state; case_011 case-side
FULL upgrade not pursued in V64-A. V63-A carry-over #1 **CLOSED via
rebadge** — V64-A ARC-GOAL Done #5 advances 3/4 → 4/4 ✓ MET this dispatch.

Sub-DEC initial-Proposed state (4-candidate surveys + 9-dim trade-off
matrix + 2-frame recommendation in §3-§5) preserved verbatim below as the
ratification record. §7 holds the user-marked path.

This sub-DEC is **ratification + plan**. It does NOT itself run a solver,
swap substrate, refactor `01_extract_surfaces.py`, or modify
`case_011 v5b` artifacts. Path-specific deliverables (retro for A,
substrate dicts skeleton or extractor refactor plan for B1/B2/B3) land in
a follow-up commit AFTER user picks a path.

---

## 0. Scope

In-scope (this Proposed sub-DEC):

1. Frame the case_011 disposition question against V63-A close §3.1
   ratification precedent + V64-A charter Triggered Redirect condition.
2. Clarify the **V93 vs V94 corpus label drift** (the "V93
   degenerate-physics" label used in V63-A close §3.1 and ARC-GOAL is a
   case_011-specific shorthand; the upstream corpus root-cause is V-row
   **V94** [STL face-label loss via `cq.exporters.export()`]).
3. Enumerate 4 candidate paths (A: PARTIAL rebadge · B1: heated-channel
   swap · B2: case_011 STL pipeline re-extraction per V94 §Fix(2) ·
   B3: shell-and-tube swap).
4. Provide a 9-dim trade-off matrix.
5. Provide a recommendation **with rationale and tradeoff disclosure** —
   not a unilateral decision.
6. Hold a §7 ratification-record placeholder for user to mark path.
7. Document Done #5 carry-over #1 closure semantics per ratified path.

Out of scope:

- Actual solver run on case_011 v5b OR any substrate alternative (per
  brief: "Substrate-swap solver run · 归后续 sub-DEC if Option B chosen")
- Refactor of `case_011 ~/Desktop/case_011_plate_fin_compact_hx/scripts/01_extract_surfaces.py`
  (if Option B2 chosen, the refactor is a follow-up sub-DEC)
- Modification of `case_011 v5b` existing substrate artifacts (V63-A
  LANDED · frozen reference)
- Advisor stack edits (case_011 V93/V94 substrate issue does not require
  advisor change · `D11 stl_face_label_validator` already catches the V94
  signature firmly)
- `case_004` work (B57 follow-up F-NEW-3 fix is a separate sub-DEC)
- `case_006` / `case_016` work (B61 thermo-FPE scope · separate)
- ARC-GOAL.md edits / Notion sync (main session reconciles at
  session-end)
- New V-row landing (V101+ remains V-series corpus expansion via case
  evidence, not this disposition sub-DEC)

---

## 1. Context

### 1.1 V63-A close §3.1 precedent (verbatim)

> "PARTIAL → FULL upgrade requires real solver convergence + literature
> comparison · semantics rebadge requires user ratification · NOT
> unilateral"

V63-A established the precedent that PARTIAL semantics is admissible as
Done-dim MET when (a) limit is case-side, AND (b) advisor stack predicted
the limit pre-run, AND (c) user explicitly ratifies. V63-A inherited
3 PARTIAL reports (case_011 / case_004 / case_016) under this precedent.

### 1.2 V64-A charter Triggered Redirect (verbatim)

> "case_011 substrate 永远 V93 degenerate · 无可换 non-degenerate substrate
> 路径 → 重新 classify PARTIAL semantics + 用户裁决 (per V63 close §3.1
> precedent)"

This redirect is the **conservative framing** — it triggers if the
"forever V93 degenerate + no alternative substrate path" premise is true.
§2 below addresses whether that premise is fully accurate (the V-series
corpus V94 entry itself documents a known substrate-rebuild path).

### 1.3 case_011 v5b validation report (PARTIAL evidence summary)

Per `.planning/validation_reports/v63_case_011_v5b_validation_report.md`
§7.2 + §8 row 6:

- **case_011 v5b ran 200 SIMPLE iterations on chtMultiRegionSimpleFoam
  cleanly** (≥3-orders residual reduction across momentum + energy +
  pressure · cumulative continuity drift −2.72e-14)
- **degenerate-physics state**: solver equilibrated to ~360 K conduction
  steady-state because `polyMesh` has **0 flow-boundary patches** in
  `region_hot_fluid` + `region_cold_fluid` (full attribution chain in
  validation report §7.2)
- **root cause**: `cq.exporters.export(wp_m, str(out), exportType="STL",
  ...)` in `scripts/01_extract_surfaces.py` (case_011 root, lines 36-42)
  emits each region as a **single watertight STL surface without
  face-zone metadata** — sHM cannot recover named `hot_inlet/outlet`,
  `cold_inlet/outlet`, `hot/cold_walls` patches
- **literature reference blocked**: Kays-London ε ≈ 0.466 / Q ≈ 225 W
  (case_profile-declared) requires `m_dot_hot = m_dot_cold = 0.05 kg/s`
  flow-through BCs that the substrate cannot host
- **advisor stack performed correctly**: D11 `stl_face_label_validator`
  fires 6 `orphan_declared_label` findings on the 6 lost face labels (V94
  canonical replay · regression-test-anchored) — stack predicted the
  degeneracy pre-run, no false-negative

The V63-A B46 substrate extension (`DEC-V63-A-sub-M-CASE-011-SUBSTRATE`)
brought case_011 V-row capture to **7/9 firm** (the highest single-case in
V63-A). The substrate sediment is the strongest in the V64-A roster.

---

## 2. Label clarification · "V93 degenerate-physics" vs V-series corpus V93

The case_011 disposition discussion in V63-A close §3.1 + V64-A charter
+ ARC-GOAL Triggered Redirect uses the label **"V93 degenerate-physics"**
as a case_011-specific semantic shorthand. The actual V-series corpus
V93 entry, at
`.planning/methodology/industrial_case_solver_findings.md:1372`, is:

> V93 · Reacting low-Mach pre-ignition T floor rule — `min(boundary
> fixedValue T)` must satisfy `≥ max(per-species Tlow in
> constant/thermo.compressibleGas)`; chemkinToFoam can leave per-species
> Tlow=300 even after a global-header patch (V41), so post-conversion
> sweep is mandatory [case_009 v1.5 cleanup 2026-05-14]

i.e., corpus V93 is `case_009` reacting-low-Mach, **not** case_011.

The actual corpus root-cause for case_011's degenerate-physics state is
**V-row V94** (`industrial_case_solver_findings.md:1384`):

> V94 · STL files emitted by cq.exporters.export() carry NO face-zone
> labels — single-shell watertight surfaces lose CAD-stage face names;
> downstream sHM creates only one undifferentiated boundary patch per
> region pair, so any case_profile referencing named inlet/outlet/
> external-wall patches cannot host the intended flow physics
> [case_011 v1 2026-05-09 · surfaced 2026-05-14 by case_011 v3
> sub-session solver e2e attempt]

V94's §Fix lists **three** prescribed remediation paths:

1. Per-case immediate: BC catch-all wildcards (LANDED in case_011 v3 sub-session · runs but degenerate physics)
2. **Per-case CAD-side fix (case_011 future)**: refactor `scripts/build_cad.py` + `scripts/01_extract_surfaces.py` to emit `cq.Assembly` with face naming → per-face STLs (`hot_inlet.stl`, `hot_outlet.stl`, `hot_walls.stl`, etc.) → snappyHexMeshDict declares all as named triSurfaceMesh patches. **Estimated 60-100 LOC.**
3. Cross-case methodology fix: `stl_face_label_validator` advisor (LANDED as **D11** under V63-A `DEC-V63-A-sub-D11` · ~21 KB · V94 6-orphan canonical replay)

V94 §Fix(3) (the advisor) is the V63-A LANDED outcome (D11). V94 §Fix(2)
(the CAD/STL pipeline rebuild) is **the engineering path that DOES exist**
for case_011 — directly contradicting the V64-A charter Triggered
Redirect's "无可换 non-degenerate substrate 路径" premise IF the premise
is read strictly.

The redirect premise is **partially correct**: there is no externally
available non-degenerate substrate to swap into (case_011's CAD source
is bespoke), but there IS an internal substrate-rebuild path
documented in the corpus. Option **B2** below captures this path.

Disposition: this sub-DEC uses **"V93/V94 degenerate-substrate"** as the
disambiguated label going forward. Corpus V93 and case_011 disposition
are separate concerns.

---

## 3. Candidate paths

### 3.1 Option A · PARTIAL rebadge (V63-A §3.1 precedent inheritance)

- **Premise**: case_011 v5b stays PARTIAL **forever** under V63-A §3.1
  user-ratified semantics. case_011 case-side FULL upgrade not pursued
  in V64-A (or any future arc unless re-opened).
- **What gets recorded**: this sub-DEC marks the rebadge as the ratified
  disposition; a retro file
  (`.planning/retrospectives/2026-05-15_case_011_partial_rebadge.md`)
  documents (a) why no swap was chosen, (b) the V94 §Fix(2) path
  acknowledged-but-not-taken, (c) the trade-off rationale.
- **What does NOT happen**: no substrate dicts authored, no solver
  re-run, no `01_extract_surfaces.py` refactor, no new validation report.
  case_011 v5b artifacts (substrate inputs + v3 solver log + B46 retro +
  V63-A validation report) remain canonical V63-A reference.
- **Done #5 carry-over #1**: **CLOSED via rebadge** · counter 3/4 → 4/4 ✓
  (Done dimension MET)
- **Done dimension impact**: Done #5 hits MET threshold this dispatch.
  Done #4 (PARTIAL upgrade closure) unaffected for case_011 path (the
  case_011 PARTIAL was never going to become FULL under Option A).
- **case_011 sediment**: preserved frozen (V-row 7/9 firm carry-forward
  · Done #6 over-met 3/2 continues to count case_011 7/9 contribution).

### 3.2 Option B1 · Substrate swap to internal-flow heated channel

- **Premise**: build a new case substrate — simple 3D rectangular duct
  with hot wall (e.g., constant-wall-T = 420 K) + cold bulk fluid flow
  (e.g., U_inlet = 1 m/s, T_inlet = 300 K). Bulk-fluid-dominated
  convection regime · no STL face-label fragility (single-block hex mesh
  + named patches at duct ends).
- **Canonical comparison**: Kays-Crawford constant-wall-T fully-developed
  Nu correlation (`Nu_D = 3.657` for circular, `Nu_D ≈ 3.61` for
  rectangular aspect ratio 1:1 laminar), OR Gnielinski for transitional/
  turbulent. Source: Kays & Crawford "Convective Heat and Mass Transfer"
  (4th ed., 2005, §9.5 + §9.7) — textbook canonical, well-tabulated.
- **What gets built**: new case directory under
  `~/Desktop/case_011_heated_channel/` (parallel to case_011) OR new
  case_017/case_021 placeholder under
  `~/Desktop/case_*/`. Substrate: CAD (simple primitive,
  ~150 LOC build_cad), case_profile.md (new), substrate inputs (new
  thin_wall / interface specs / shm_dict / parts_manifest), 0/orig BCs,
  controlDict / fvSchemes / fvSolution dicts.
- **What gets discarded**: case_011 v5b sediment is NOT discarded
  (frozen V63-A reference), but case_011 V-row 7/9 firm becomes
  **case_011-only**; the new case starts at ~1-2/9 V-row capture (no
  thin_wall sliver, no D5 30 µm gap, no V94 face-label loss).
- **Done #5 carry-over #1**: **plan-only · not closed** this dispatch
  (this sub-DEC ratifies path + records swap-target spec; the actual
  swap implementation + solver run + validation report are downstream
  sub-DECs). Counter stays 3/4.
- **Done dimension impact**: this sub-DEC does NOT advance Done #5.
  Downstream solver-run sub-DEC would advance Done #1 (FULL report
  count) IF heated-channel substrate converges + matches Kays-Crawford.

### 3.3 Option B2 · case_011 STL pipeline re-extraction (V94 §Fix(2) path)

- **Premise**: refactor `~/Desktop/case_011_plate_fin_compact_hx/scripts/01_extract_surfaces.py`
  (+ likely `scripts/build_cad.py`) to emit per-face STLs via
  `cq.Assembly` with face naming. Same CAD geometry, same case_profile,
  same Kays-London reference, same V-row sediment. Estimated
  **60-100 LOC** per V94 §Fix(2) entry + ~50 LOC snappyHexMeshDict
  geometry block update for the named patches.
- **Canonical comparison**: Kays-London ε ≈ 0.466 / Q ≈ 225 W ± 20%
  (case_profile-declared, preserved). Source: Kays & London "Compact
  Heat Exchangers" (3rd ed., 1984, §10 plate-fin family) — handbook
  canonical, tabulated by surface designation.
- **What gets built**: per V94 §Fix(2), an updated `01_extract_surfaces.py`
  using `cq.Assembly` + named `cq.Sketch.face("Tagged")` to emit
  `hot_inlet.stl` / `hot_outlet.stl` / `hot_walls.stl` /
  `cold_inlet.stl` / `cold_outlet.stl` / `cold_walls.stl` /
  `solid.stl` files; updated `case/system/snappyHexMeshDict` geometry
  block declaring each STL as a named triSurfaceMesh patch; new 0/orig
  BC files referencing the named patches with `flowRateInletVelocity` /
  `pressureInletOutletVelocity` etc. **No new CAD or case_profile**.
- **Asset reuse**: maximally high. V64-A charter §"V63-A 资产复用清单"
  V64-A choice rationale is 5/5; this path preserves it. D11
  `stl_face_label_validator` validates the new face-zone STL post-refactor
  (canonical V94 regression test #11) — closes V94's "[QUESTIONABLE]"
  promotion-gate marker.
- **Risks** (called out explicitly): (a) re-extract pipeline rebuild not
  guaranteed to converge to Kays-London ε ≈ 0.466 — case_011 v5b mesh
  retention issues (cold 115% / solid 36.9% / 988 illegal faces in v5b)
  may persist; (b) `cq.Assembly` face-tagging convention requires
  CAD-stage support for named faces, which may need build_cad.py touch
  beyond 01_extract_surfaces.py alone; (c) mesh budget (~15M cells in
  v5b) implies any re-run is a multi-hour wall-clock event on 1-CPU
  Docker.
- **Done #5 carry-over #1**: **plan-only · not closed** this dispatch
  (this sub-DEC ratifies path; the actual refactor + new STL emit +
  re-mesh + solver run + validation report are 1-2 downstream sub-DECs).
  Counter stays 3/4.
- **Done dimension impact**: this sub-DEC does NOT advance Done #5.
  Downstream sub-DEC chain would advance Done #1 (FULL report count)
  AND Done #4 (PARTIAL upgrade closure) IF re-extract substrate
  converges + matches Kays-London — **two Done dims potentially
  advanced via this path**, vs Option B1's single Done dim.

### 3.4 Option B3 · Substrate swap to shell-and-tube HX

- **Premise**: build a new case substrate — canonical shell-and-tube
  industrial HX (e.g., 1 shell pass + 2 or 4 tube passes, 8-16 tubes,
  baffle-supported). Industrially standard HX class.
- **Canonical comparison**: Bell-Delaware method (TEMA / handbook
  canonical) OR Kern method. Source: Kakac & Liu "Heat Exchangers:
  Selection, Rating, and Thermal Design" (3rd ed., 2012, §8 Bell-Delaware
  + §11 Kern); also Shah & Sekulić "Fundamentals of Heat Exchanger
  Design" (2003, §9). Industrially canonical.
- **What gets built**: new case directory; CAD with tube bundle (CadQuery
  multi-cylinder assembly, ~250-400 LOC), shell, baffles; complex mesh
  topology (per-tube wall layer + shell-side cross-flow region); 0/orig
  BCs (tube-side mass flow + shell-side mass flow, possibly periodic);
  case_profile.md (new, Bell-Delaware Q-vs-ΔP design point declared).
- **What gets discarded**: case_011 v5b sediment frozen (same as B1).
  Tube-bundle mesh resolution at tube wall is non-trivial.
- **Risks**: (a) tube-bundle CAD non-trivial; (b) mesh resolution at
  tube-wall boundary layer for shell-side cross-flow requires careful
  refinement (likely sHM + addLayers); (c) Bell-Delaware delta
  comparison requires correct baffle configuration matching the
  correlation's assumptions (segmental baffle cut, baffle spacing
  ratios) — more configuration sensitivity than B1.
- **Done #5 carry-over #1**: **plan-only · not closed** (same as B1/B2).
- **Done dimension impact**: this sub-DEC does NOT advance Done #5.
  Downstream solver-run could advance Done #1 IF mesh + solver +
  Bell-Delaware delta succeed — high engineering risk path.

### 3.5 Option C · Defer (sub-DEC stays Proposed)

- **Premise**: user wants more time to evaluate, OR wants to first see
  outcome of B61 thermo-FPE fix (which unlocks case_016 + case_006 path),
  OR wants to deprioritize case_011 entirely in V64-A.
- **What happens**: this sub-DEC commits as Proposed (NOT Accepted).
  No retro, no substrate dicts, no extractor refactor.
- **Done #5 carry-over #1**: NOT closed. Counter stays 3/4.

---

## 4. Trade-off matrix (9 dimensions · all 5 options)

| Dim | A: rebadge | B1: heated-channel | B2: re-extract STL | B3: shell-tube | C: defer |
|---|---|---|---|---|---|
| **LOC cost (one-time)** | 0 (frozen) | ~300-500 (new CAD + case_profile + 0/orig + substrate inputs + dicts) | **~60-100** (01_extract_surfaces.py refactor per V94 §Fix(2)) + ~50 (sHMD update) | ~400-600 (CAD + tube-bundle + case_profile + substrate · most complex) | 0 |
| **Wall-clock (engineering)** | 0 (frozen) | 2-4 sessions (new case bootstrap + V-row evolution) | **1-2 sessions** (within case_011 v6/v7 envelope) | 3-5 sessions (tube-bundle CAD + mesh resolution iteration) | 0 |
| **Canonical reference** | n/a | Kays-Crawford Nu_D ≈ 3.657 (laminar) / Gnielinski (turb) · textbook tabulated | **Kays-London ε ≈ 0.466 / Q ≈ 225 W ± 20% · handbook canonical · case_profile-declared (preserved)** | Bell-Delaware / Kern · TEMA-canonical handbook | n/a |
| **Advisor stack compat** | trivial (no run) | new substrate dicts needed; A2-v2 D5 / V94 / V30 may not fire on new geometry (re-discover V-rows) | **full reuse**: D11 validates per-face STL post-refactor (canonical V94 test); A2-v2 D5 30 µm gap preserved; V30 sliver class preserved | new substrate dicts; tube-side V-rows novel | unchanged |
| **V-row impact** | preserve **7/9 firm** (frozen) | reset to ~1-2/9 (new case · re-discover sediment) | **preserve 7/9 firm + likely +1 new V-row** for re-extract success / failure mode (V101+ candidate) | reset to ~1-2/9 (new case) | preserve 7/9 (frozen pending) |
| **Done #5 carry-over #1 closure** | **CLOSED via rebadge · 3/4 → 4/4 ✓ MET** | plan-only · stays 3/4 (solver run is downstream sub-DEC) | plan-only · stays 3/4 (refactor + run is 1-2 downstream sub-DECs) | plan-only · stays 3/4 | not closed · 3/4 (status quo) |
| **Done #1 (FULL) potential** | 0 (forever PARTIAL by design) | 1 candidate path (if heated-channel converges + Nu delta < tol) | **1 candidate path · highest sediment-reuse · case_011 → FULL** (also closes Done #4 case_011 PARTIAL→FULL) | 1 candidate path · highest engineering risk | 0 |
| **V64-A schedule impact** | 0 (frees session for thermo-FPE fix / Done #1 ROI) | 2-4 sessions block other Tier 1 | **1-2 sessions within Tier 1 budget** (parallel-safe with thermo-FPE per ARC-GOAL §下一步建议 B62) | 3-5 sessions block Tier 1 | 0 (defers decision) |
| **Risk: convergence to literature** | n/a (no compare) | medium · Kays-Crawford is well-validated correlation; bulk-fluid convection is benign | **medium-high** · Kays-London compact-fin ε ≈ 0.466 is handbook ± 20% tolerance, plus v5b mesh retention issues (988 illegal faces) may persist after re-extract | medium · Bell-Delaware well-validated but mesh + baffle config sensitive | n/a |

---

## 5. Recommendation

**Two distinct frames yield two distinct recommendations**:

### 5.1 Frame 1: V64-A arc-close speed priority → Option A (PARTIAL rebadge)

If V64-A priority is **closing Done #5 to 4/4 MET this session** and
freeing subsequent sessions for thermo-FPE fix (Done #1 highest ROI per
ARC-GOAL §下一步建议 candidate ranking — "B61 = M-V64A-THERMO-FPE-FIX"
unlocks case_016 + case_006 双 case potential FULL), Option A is the
right call. case_011 v5b PARTIAL credit is preserved (V63-A §3.1
precedent), V-row 7/9 firm preserved, no session-budget consumed.
**Trade-off**: case_011 FULL upgrade is forever closed; Done #1 stays
0/3 strict from case_011 contribution; Done #4 case_011 PARTIAL stays
PARTIAL (3rd PARTIAL stays PARTIAL by design — V64-A targets "≥ 2 / 3
PARTIAL upgraded OR explicitly re-classified with documented rationale"
which Option A *satisfies via re-classification*).

### 5.2 Frame 2: case_011 sediment preservation + Done #1 + #4 maximization → Option B2 (re-extract STL)

If V64-A priority is **maximizing case_011 PARTIAL → FULL upgrade
likelihood while preserving the V-row 7/9 firm sediment**, Option B2 is
the engineering-strongest path. It follows V94 §Fix(2)'s documented
prescription (60-100 LOC + sHMD update), maintains 100% case_011 asset
reuse (CAD, case_profile, Kays-London reference, V-row sediment all
preserved), validates D11 advisor as side-effect (closes D11
"[QUESTIONABLE]" promotion-gate marker), and unlocks BOTH Done #1
(potential 0→1/3 strict FULL via case_011) AND Done #4 (potential 0→1/2
PARTIAL→FULL upgrade) via the same refactor. **Trade-off**: Done #5
stays 3/4 this dispatch (carry-over #1 is plan-only · solver run is
downstream sub-DEC); 1-2 additional sessions consumed in V64-A budget;
convergence to Kays-London ε ≈ 0.466 not guaranteed (v5b mesh quality
issues may persist).

### 5.3 Why NOT B1 or B3

Both B1 (heated channel) and B3 (shell-tube) are **substrate swaps that
discard case_011 sediment AND don't close Done #5** — they pay the
substrate-discovery cost of a swap without compensating sediment-reuse.
B2 dominates B1 on asset reuse + Done #4 + literature reference quality;
A dominates B1/B3 on Done #5 closure speed. B1/B3 are weakest on the
2-frame analysis above; neither is recommended.

### 5.4 Pragmatic call (Claude Code session synthesis)

**If user values V64-A close speed → A. If user values case_011 FULL
arrival → B2.**

The choice depends on user's V64-A priority weighting. ARC-GOAL §下一步建议
explicitly ranks the candidates by Done #1 strict FULL ROI; under that
ranking case_011 NONDEGEN-RATIFY is **#3** (推 Done #5 but 不解 Done #1
directly under A; **could** advance Done #1 under B2 but slower than
thermo-FPE fix). This suggests A is the V64-A-schedule-pragmatic call
**unless user wants case_011 FULL specifically** (then B2). B1/B3 are
not recommended in either frame.

This recommendation is **advisory**. User explicitly ratifies per V63-A
close §3.1 precedent.

---

## 6. Codex / Kogami / Notion compliance

- **Codex review**: SKIPPED. This sub-DEC is documentation-only (no
  source / route / signing / security boundary touched). v2.3
  1-sync-trigger does not apply. Round count: 0.
- **Kogami invocation**: NOT requested. v2.3 opt-in only; user did not
  invoke. Ratification semantics is an engineering trade-off decision
  (the same class as V63-A §3.1 user-ratification), not a strategic
  narrative event.
- **Notion sync**: NOT synced this dispatch (Status: Proposed). Per
  v2.3 round-1 loosen rule, only Status=Accepted DECs sync at
  session-end. Sub-DEC will sync IF user ratifies and Status flips to
  Accepted in a follow-up commit.
- **Surface scan trailer**: clean (no source files touched this commit;
  documentation-only).

---

## 7. Ratification record · USER-MARKED

Per V63-A close §3.1 precedent — the ratification is **explicit** and
**NOT unilateral**. User picked path via AskUserQuestion in B62 dispatch
(question header: "case_011 path"; option chosen verbatim:
"A · PARTIAL rebadge (推荐 schedule-pragmatic)").

```
RATIFIED PATH:        A (PARTIAL rebadge)
RATIFICATION DATE:    2026-05-15
RATIFIED BY:          User (cfd-harness-unified maintainer · session B62 main dispatch)
RATIFICATION VEHICLE: AskUserQuestion answer in B62 turn (single-select · option A · "A · PARTIAL rebadge (推荐 schedule-pragmatic)")
RATIONALE (option description verbatim):
  "case_011 v5b stays PARTIAL forever · V63-A §3.1 precedent inherited ·
   V-row 7/9 firm preserved · Done #5 carry-over #1 CLOSED via rebadge ·
   3/4 → 4/4 ✓ MET 本 dispatch · 0 LOC · 0 wall-clock · 释放 session
   budget 给 B61 thermo-FPE fix (Done #1 最高 ROI) · 代价: case_011 FULL
   upgrade forever closed"
```

### 7.1 Ratified semantics (binding for V64-A + downstream arcs)

1. **case_011 v5b PARTIAL classification is frozen as canonical V63-A
   reference**. Validation report
   `v63_case_011_v5b_validation_report.md` (verdict PARTIAL · V93/V94
   degenerate-physics caveat) is the perpetual case_011 e2e validation
   record. No PARTIAL → FULL upgrade pursued for case_011 in V64-A.
2. **V94 §Fix(2) path (re-extract via cq.Assembly with face naming) is
   acknowledged-but-not-taken in V64-A**. The engineering path remains
   documented (V94 §Fix(2) verbatim · `industrial_case_solver_findings.md:1384`)
   and may be re-opened in a future arc IF case_011 FULL becomes
   strategically valuable. This is NOT a permanent foreclosure — it is a
   V64-A schedule-pragmatic deferral.
3. **case_011 sediment preserved frozen** (V-row 7/9 firm carry-forward
   in Done #6 over-met 3/2 contribution; substrate inputs `inputs/
   thin_wall_inputs.yaml` + `interface_bodies.json` + `interface_specs.json`
   per V63-A B46 LANDED; D11 V94 canonical replay test #11 anchored on
   case_011 substrate).
4. **V63-A carry-over #1 (case_011 substrate swap) is CLOSED via
   rebadge**. V64-A Done #5 counter advances 3/4 → 4/4 ✓ MET this
   dispatch (B62 commit).
5. **V64-A Done #4 (PARTIAL upgrade closure) crediting**: V64-A charter
   §Done dim #4 threshold reads "≥ 2 / 3 PARTIAL upgraded to FULL **OR
   explicitly re-classified with documented rationale**". Path A
   satisfies the **OR-clause** ("explicitly re-classified with
   documented rationale"). case_011 PARTIAL is re-classified as
   "perpetually PARTIAL · case-side substrate limit · V94 §Fix(2)
   acknowledged not taken · V64-A schedule-pragmatic" — documented
   rationale in §5.1 of this DEC + ratification record §7 + retro file
   §3-§4. case_011 contributes **1 / 3 toward Done #4 ≥ 2 / 3
   threshold via re-classification crediting**. Done #4 remains
   contingent on case_004 + case_016 PARTIAL→FULL upgrade (B61
   thermo-FPE fix + B57 F-NEW-3 blade CAD fix tracks).
6. **PARTIAL semantics precedent (V63-A §3.1) is inherited verbatim**.
   Future case-substrate ratifications may invoke the same precedent
   chain (V63-A §3.1 → V64-A §7 of this DEC as next-link governance
   citation).

---

## 8. Path-specific deliverables (post-ratification)

### 8.1 If Option A ratified

- Update this file Status: Proposed → Accepted; populate §7 ratification
  record with `RATIFIED PATH: A`
- Create
  `.planning/retrospectives/2026-05-15_case_011_partial_rebadge.md`
  documenting: (a) V94 §Fix(2) path acknowledged-but-not-taken with
  reason, (b) V64-A schedule-pragmatic frame applied, (c) V63-A §3.1
  precedent inherited verbatim, (d) Done #5 carry-over #1 closure
  semantics, (e) case_011 v5b sediment frozen list
- Commits:
  1. `docs(v64-case011-ratify): sub-DEC ... Accepted · ratification record A (rebadge) + V63 close §3.1 precedent invocation` (this file, Status: Accepted)
  2. `docs(v64-case011-ratify): retro · V94 §Fix(2) acknowledged not taken · V64-A schedule-pragmatic · Done #5 3/4 → 4/4 ✓ MET` (retro file)
- ARC-GOAL.md edit (main session reconciles): Tier 1 row
  `M-V64A-CASE-011-NONDEGEN` `[ ]` → `[x]` with commit hashes; counter
  block: 当前 V63-A carry-over closure: 3/4 → **4/4 ✓ MET**; Done dims
  MET: 1/6 → **2/6** (Done #5 + Done #3 both MET); 下一步建议 updated.

### 8.2 If Option B1 or B3 ratified

- Update this file Status: Accepted; populate §7 with `RATIFIED PATH: B1`
  or `RATIFIED PATH: B3` + selected canonical reference (Kays-Crawford or
  Bell-Delaware)
- Create
  `.planning/case_profiles/case_011_v64_nondegen_dicts/` (or new
  `case_017_<name>/` if user wants a new case_id) skeleton with:
  - `case_profile_draft.md` (new substrate scope · canonical reference
    citation · expected literature delta tolerance)
  - `substrate_dict_skeleton/` (placeholder layout for thin_wall_inputs
    / interface_bodies / interface_specs / parts_manifest pending CAD)
  - `canonical_reference_citation.md` (Kays-Crawford or Bell-Delaware
    primary source + edition + page reference)
- Commits:
  1. `docs(v64-case011-ratify): sub-DEC ... Accepted · ratification record B1/B3 + selected canonical + swap plan` (this file)
  2. `feat(v64-case011-swap-plan): case_011_v64_nondegen_dicts/ skeleton + canonical reference citations` (skeleton dir)
- ARC-GOAL.md edit (main session): Tier 1 row stays `[ ]` because
  carry-over #1 is plan-only · annotate "ratification path B1/B3 ·
  downstream sub-DECs M-V64A-CASE-011-NONDEGEN-IMPL + M-V64A-VAL-FULL-4
  pending"

### 8.3 If Option B2 ratified

- Update this file Status: Accepted; populate §7 with `RATIFIED PATH: B2`
- Create
  `.planning/case_profiles/case_011_v64_nondegen_dicts/` skeleton (same
  case_011 case-id, indicates v6/v7 within-case revision) with:
  - `extractor_refactor_plan.md` (per V94 §Fix(2): 01_extract_surfaces.py
    cq.Assembly refactor sketch · 60-100 LOC estimate · build_cad.py
    face-tagging touch list · sHMD geometry block update plan)
  - `face_zone_stl_inventory.md` (target named STLs: hot_inlet,
    hot_outlet, hot_walls, cold_inlet, cold_outlet, cold_walls,
    solid · with face-naming convention)
  - `canonical_reference_citation.md` (Kays-London ε ≈ 0.466 / Q ≈ 225 W
    preserved · case_profile-declared · primary source citation)
  - `risk_log.md` (v5b mesh retention issues 988 illegal faces +
    cellZoneInside topology + cq.Assembly face-tagging support
    investigation needs)
- Commits:
  1. `docs(v64-case011-ratify): sub-DEC ... Accepted · ratification record B2 (re-extract) + V94 §Fix(2) path + plan` (this file)
  2. `feat(v64-case011-reextract-plan): case_011_v64_nondegen_dicts/ skeleton · extractor refactor plan + face_zone STL inventory + risk log` (skeleton dir)
- ARC-GOAL.md edit (main session): Tier 1 row stays `[ ]` because
  refactor is downstream · annotate "ratification path B2 · downstream
  sub-DECs M-V64A-CASE-011-REEXTRACT + M-V64A-VAL-FULL-CASE-011 pending"

### 8.4 If Option C ratified (defer)

- This file stays Status: Proposed (do NOT flip to Accepted)
- §7 ratification record populated with `RATIFIED PATH: C-defer` +
  rationale (e.g., "B61 thermo-FPE fix outcome 优先 · 再回 case_011")
- Single commit:
  1. `docs(v64-case011-ratify): sub-DEC ... Proposed · 4-candidate trade-off + recommendation + deferred per user` (this file)
- ARC-GOAL.md edit (main session): Tier 1 row stays `[ ]` · annotate
  "ratification deferred per B62 · revisit candidate"

---

## 9. v2.3 compliance

- **Scope class**: sub-DEC. 1 ratification + plan document · 1 retro
  (path A) OR 1 skeleton dir (path B1/B2/B3) OR 0 follow-up (path C).
  Frontmatter satisfies 6 required v2.3 fields (decision_id / title /
  status / parent_dec / phase / notion_sync_status) + optional
  authored_by / authored_at / confidence.
- **Cadence floor (30)**: not triggered. No source LOC churn; this
  sub-DEC is purely a ratification document.
- **Codex review**: skipped per §6. No security boundary touched.
- **Kogami invocation**: not requested per §6.
- **Notion sync**: gated by Status. Stays out of sync until ratified
  to Accepted.
- **DEC scope-driven**: ratification scope · cross-cuts 0 shared code
  paths in this dispatch (path B follow-up sub-DECs would cross >1 path
  · those are separate sub-DECs not this one).
- **4Q gate inline**: Q1 (LLM offline · this sub-DEC writes Markdown
  with no LLM advisor calls), Q2 (artifact emitted · this file), Q3
  (TrustGate · every candidate cites literature/V-corpus/charter source
  · §3.1/§3.2/§3.3/§3.4 each carry primary-source citation), Q4
  (advisor-only · ratification is engineering decision not advisor
  output). All 4 PASS.
- **Spike-class**: not applicable. This is a ratification sub-DEC, not
  a code-change spike. DEC frontmatter required.
- **Surface scan trailer**: clean (no source files touched).

---

## 10. Open follow-ups (per ratified path · NOT blocking Proposed status)

1. **Path A**: V94 §Fix(2) path stays acknowledged-but-not-taken in
   V64-A; future arc may re-open case_011 if PARTIAL→FULL becomes
   strategically valuable.
2. **Path B1/B3**: downstream sub-DECs M-V64A-CASE-011-SWAP-IMPL +
   M-V64A-VAL-FULL-4 (new) must define the swap-target case_id, CAD
   provenance, mesh strategy.
3. **Path B2**: downstream sub-DECs M-V64A-CASE-011-REEXTRACT-IMPL
   (refactor 01_extract_surfaces.py + build_cad.py + snappyHexMeshDict +
   0/orig BCs) + M-V64A-VAL-FULL-CASE-011 (re-mesh + run + Kays-London
   delta + report). D11 cross-validation gate `[QUESTIONABLE]` marker
   discharge upon successful per-face-STL emit.
4. **Path C**: revisit candidate after B61 thermo-FPE fix lands; may
   re-evaluate priority once Done #1 strict FULL contribution from
   case_016 + case_006 path becomes clear.
5. **Label canonicalization** (any path): future V-series corpus entries
   should NOT use "V93 degenerate-physics" as a casual case_011 label
   (the actual V93 is case_009 reacting low-Mach T-floor rule).
   Recommended canonical label: "V94-induced degenerate physics" OR
   "case_011 conduction-dominated equilibration state".

---

## 11. Cross-references

- Parent DEC: `2026-05-15_v64_charter_dec.md` (DEC-V64-A-charter)
- V63-A close §3.1 precedent: `.planning/decisions/2026-05-15_v63_close_dec.md` §3.1
- V64-A charter Triggered Redirect: `2026-05-15_v64_charter_dec.md` §Triggered redirect
- ARC-GOAL active: `.planning/ARC-GOAL.md` (V64-A · Tier 1 row M-V64A-CASE-011-NONDEGEN)
- V63-A case_011 substrate DEC: `.planning/decisions/2026-05-15_v63_sub_case_011_substrate.md` (DEC-V63-A-sub-M-CASE-011-SUBSTRATE · V-row 3/9 → 7/9 firm)
- V63-A case_011 validation report (PARTIAL): `.planning/validation_reports/v63_case_011_v5b_validation_report.md`
- V-series corpus: V93 (case_009 reacting · `industrial_case_solver_findings.md:1372`) + V94 (case_011 STL face-label loss · `industrial_case_solver_findings.md:1384` · §Fix(2) is the Option B2 prescription)
- D11 advisor (V94 catcher · LANDED): `.planning/decisions/2026-05-14_v63_sub_d11_stl_face_label.md`
- case_011 case profile: `.planning/case_profiles/case_011_plate_fin_compact_hx.md`
- Predecessor case_011 v3 sub-DEC (V94 surfacing): `.planning/decisions/2026-05-14_v61_198_sub_case_011_v3_solver_e2e.md`

---

**End of Accepted sub-DEC.** Ratified Path A · PARTIAL rebadge · V63-A close §3.1 precedent inherited · Done #5 3/4 → 4/4 ✓ MET this dispatch · retro file `.planning/retrospectives/2026-05-15_case_011_partial_rebadge.md` lands as commit-2 in B62 chain.
