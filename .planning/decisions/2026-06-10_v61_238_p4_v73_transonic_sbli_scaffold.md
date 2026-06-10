---
decision_id: DEC-V61-238
title: P4 V73.A · civil-aircraft scope pivot — V72 VOF parked at A-slice; RAE 2822 Case 9 transonic-SBLI vertical scaffold (gold + extractor + gate + tests; NO solve, coverage stays 3)
status: Accepted (autonomous under sponsor full-delegation + civil-aircraft scope mandate 2026-06-10 · Codex chain see frontmatter below)
parent_dec: DEC-V61-207 (Blueprint v4 vertical-first) · DEC-V61-237 (V72.A scaffold, now parked) · DEC-V61-234 (wedge backend-wiring precedent) · DEC-V61-224(b) (image-gating provision)
phase: P4 (V73 arc · transonic shock/boundary-layer interaction on a lifting surface · capability matrix §6 gap#2)
notion_sync_status: n/a (Notion retired per sponsor 2026-06-09)
autonomous_governance: true   # sponsor mandate 2026-06-10: "批准你全权推进下一个里程碑开发，注意，我只要民用飞机设计相关的CFD能力" — counter +1
confidence: high
date: 2026-06-10
loop_auditor: "FLAG (design review, pre-implementation) — all 7 must-fixes adopted, see §4"
codex_tool_report_path: reports/codex_tool_reports/2026-06-10_v73a_scaffold_R{0,1,2}.md
codex_review_relay: 86gs (gpt-5.4 xhigh · R0 CHANGES_REQUIRED [P1 snapshot-mixing, P2 origin-dependent x/c, P2 missing declared-gold leg] fixed d3309bb → R1 CHANGES_REQUIRED [P1 restart-duplicate ties, P2 face-centre span over-strict] fixed → R2)
---

# DEC-V61-238 · V73.A transonic-SBLI scaffold + civil-aircraft scope pivot

## TL;DR

Sponsor narrowed the delegation: **civil-aircraft-design CFD capability only**.
Consequence (a): the V72 VOF arc is **PARKED at the A-slice** — the landed,
Codex-clean scaffold (DEC-V61-237) stays; V72.B/C (live probe + wiring) do
not proceed under this mandate. Consequence (b): the next vertical is **V73 =
RAE 2822 Case 9** (M=0.734, α=2.79° corrected, Re_c=6.5e6) — THE canonical
transonic-cruise benchmark for civil airliner wings. This slice lands the
OFFLINE scaffold only: gold + pure extractor + fail-closed two-tier gate +
65 tests, mirroring the wedge/V72.A cadence. **No solver runs in this slice;
runnable-coverage stays 3** (breadth-depth on the already-covered kOmegaSST
COMP-STEADY cell — stated explicitly; nothing here can flip 3→4).

## §1 V72 parking record (scope honesty, not cancellation)

- Dam-break VOF is generic free-surface physics, not civil-aircraft-specific.
  Documented re-entry: **fuel-tank slosh** (DEC-V61-201 names "aerospace
  tank-slosh" as the VOF application target) — if/when the sponsor green-lights
  it, V72.B/C resume on top of the landed scaffold unchanged.
- Sunk cost ≈ 0: V72.A is pure offline code (no adapter/UI coupling), tests
  keep running in CI, gold stays DECLARED-NOT-VERIFIED + PROVISIONAL.
- V72A-FOLLOWUP-1 (pre-existing full-suite collection fragility) remains
  queued — unaffected by parking.

## §2 Candidate selection (oracle-quality discipline · civil-aircraft lens)

| Candidate | Verdict | Why |
|---|---|---|
| **RAE 2822 Case 9** | **SELECTED** | Canonical civil-transonic SBLI benchmark (AGARD AR-138); B109 in-repo spec exists (V67A substrate research); closes matrix §6 gap#2 ("NACA0012 M=0.8 just below shock-formation threshold" — shock capture on a lifting surface never judged); 2D = tractable mesh; rhoSimpleFoam already runnable-proven |
| ONERA M6 | blocked | 3D swept wing (mesh cost ≫) + this repo's documented rhoCentralFoam transonic divergence history (V27-V29 lessons) |
| CRM-HLS | blocked | Geometry not in this repo (cross-repo case_003 profile); high-lift ≠ cruise; 393k-facet STL ≫ scaffold scope |
| NACA0012 M=0.8 deepening | rejected | Stays below shock-formation threshold — cannot certify shock capture |

## §3 Two-tier oracle (full spec in gold header + `src/transonic_airfoil_gate.py`)

- **Tier 1 SANITY (always enforced, closed forms re-derived in tests)**:
  C0a/b/c freestream three-way consistency — **measured** solved-field probe ≈
  **declared** 0/ BCs ≈ **gold** target (|ΔM|≤0.005, |Δα|≤0.2°, Re rough ±10%
  via the case's own Sutherland μ) · C1 stagnation ceiling max Cp ∈ [1.0,
  Cp_stag+0.05] · C3 supersonic pocket min Cp_upper < Cp* ≈ −0.647 · C4 shock
  detector (≥5-pt plateau below Cp*−0.05, jump ≥0.3× pocket depth, ≤2 Cp*
  crossings, ≥30-pt upper surface fail-closed) + x/c ∈ (0.2, 0.9) · C5 force
  ranges · C6 independent contour-integrated Cl_p vs forceCoeffs Cl_fc ≤5%.
  Verdict capped at **SANITY-PASS** — never "validated", never coverage.
- **NO C2 vacuum-floor gate — removed as a tautology (self-caught)**: with the
  measured-freestream normalization, p∞/q∞ ≡ 2/(γM²) is an algebraic identity,
  so Cp ≥ Cp_vac ⟺ p_abs ≥ 0, which the extractor already enforces. A gate
  that cannot independently fire is fake rigor (MicroCOMAC 批20 重言式教训).
  Identity is test-documented (`test_vacuum_floor_identity_documented`).
- **Tier 2 — AGARD AR-138 anchor, role-aware (loop-auditor F5)**: candidates
  keyed by QoI with roles — `cl` (rel 5%) + `shock_xc` (atol 0.05) ENFORCED;
  `cd` ADVISORY (turbulence-model-dependent — reported, never judged); Cp(x/c)
  profile band PROFILE-PENDING. **All values null + DECLARED-NOT-VERIFIED**
  (ballparks Cl≈0.803 / Cd≈0.0168 / shock≈0.55 recorded as prose only — an
  undigitized consumable number is a fake anchor, V72.A F1 lesson). Consumer-
  side enforcement: status enum fail-closed + provenance required + anchor
  meta-gate (candidate band must sit inside its own tier-1 sanity range) +
  **role completeness pin** (ENFORCED set == {cl, shock_xc} pinned in code;
  a gold alone can neither grow nor shrink the judged set — raises GoldError).

## §4 loop-auditor design review (pre-implementation · FLAG · all 7 adopted)

| # | Finding | Adoption |
|---|---|---|
| F1 P1 | 0/-only freestream check spoofable by doctored BC files | C0 three-way: MEASURED upstream probe of the solved field ≈ declared ≈ gold; α direction gate; Re rough check via case's own μ(T∞) |
| F2 P1 | forceCoeffs FO trusted alone = solver self-report | C6: independent contour-integrated pressure Cl (Cn·cosα−Ca·sinα from ordered surface points) within 5% of FO Cl |
| F3 P2 | naive Cp*-crossing detector promotes wiggles to shocks | plateau ≥5 pts below Cp*−0.05 · jump ≥0.3× pocket depth · ≤2 crossings · ≥30-pt surface fail-closed (each guard negative-tested) |
| F4 P2 | Case 9 operating-point convention dispute (nominal M=0.730/α=3.19 vs corrected M=0.734/α=2.79) | gold pins corrected + `operating_point_verification: DECLARED-NOT-VERIFIED` + `user_adjudication_pending` field; pin test keeps the dispute visible |
| F5 P2 | flat tier-2 (all QoIs equal) lets model-dependent Cd gate physics | role-aware candidates: Cd ADVISORY, enforced set pinned {cl, shock_xc}, Cp profile PROFILE-PENDING |
| F6 P3 | existing `airfoil_surface_sampler` z-sign split breaks on RAE 2822 aft-loading (lower surface crosses z=0) | nearest-neighbour contour chaining (jump fail-closed) + split at LE, upper = higher-mean-z branch; regression test with camber 0.05x³ |
| F7 P3 | gates without per-gate negative fixtures = unproven teeth | doctored-case discipline: every tier-1 gate bitten by a case violating exactly it (`TestTier1SanityGates`, 11 tests) |

Self-caught additions beyond the audit: (a) C2 tautology removal (§3);
(b) Cn/Ca contour-integral **sign derivation fixed pre-commit** — for CCW
traversal the outward normal is (dz,−dx)/ds ⇒ Cn=+∮Cp dx, Ca=−∮Cp dz (initial
draft had both flipped; caught by deriving the unit-square known-value test);
(c) `CylinderStrouhalError` from the reused coefficient.dat parser wrapped so
the gate's fail-closed contract stays single-typed.

## §5 Image gating (DEC-V61-224(b) · probed 2026-06-10 on this machine)

- (a) **PRIMARY pinned**: ESI `opencfd/openfoam-default:2312` — `rhoSimpleFoam`
  confirmed native arm64 (alongside rhoCentralFoam/rhoPimpleFoam/sonicFoam).
  Runner reuse: wedge `_docker_run_esi_rm` fresh `--rm` pattern (DEC-V61-234).
- (b) Adapter wiring + cfdtrust reconciliation: **deferred to V73.C** (wedge
  precedent — enum + dispatch land with the wiring slice).
- (c) **FALLBACK**: `rhoCentralFoam` pseudo-transient with the V27-V29
  divergence lessons applied (adjustTimeStep maxCo 0.5/0.3 · no DILU ·
  ESI freestream BC family).

## §6 Files (this slice)

- `knowledge/gold_standards/rae2822_case9.yaml` (NEW — two-tier oracle SSOT)
- `src/transonic_airfoil_extractor.py` (NEW — Execution plane; probe/BC/raw
  parsers, contour chaining + LE split, compressible Cp off MEASURED
  freestream, ∮Cp cross-check, guarded shock detector; fail-closed)
- `src/transonic_airfoil_gate.py` (NEW — Control plane; tier-1 SANITY +
  role-aware tier-2; `coverage_impact` explanatory string, **NO
  coverage_eligible field** — breadth anchor cannot flip coverage)
- `src/_plane_assignment.py` + `.importlinter` (regenerated same commit)
- `tests/p4/test_transonic_{gold,extractor,gate}.py` (NEW — 65 tests)
- `.planning/cfd_capability_matrix.md` (§6 gap#2 dated annotation: V73 OPEN)

## §7 四问门控

- **LLM 离线可跑**: YES — gold/extractor/gate/tests deterministic offline; no
  LLM in any path.
- **artifacts**: YES — gate emits structured verdict (per-gate booleans,
  measured QoIs, tier-2 mode + notes); V73.B/C add frozen REPRODUCE/EVIDENCE.
- **TrustGate 解释**: YES (forward) — SANITY-PASS cap + PROVISIONAL tier-2 +
  coverage_impact string keep any consumer honest; TrustGate wiring lands
  with V73.C alongside the runner.
- **AI advisory-only**: YES — no mutating route, no UI surface; pure
  evaluation-side scaffold.

## §8 Verification (this slice)

- `pytest -q tests/p4/` → **176 passed, 2 skipped** (65 new; wedge/BFS/
  dam-break untouched).
- `lint-imports --config .importlinter` → 5 contracts kept, 0 broken.
- Full-suite collection fragility: pre-existing, unchanged (V72A-FOLLOWUP-1);
  verification protocol = tests/p4 + per-file runs (DEC-V61-237 §Verification).

## §9 Slice plan (V73 arc)

- **V73.A (this DEC)**: offline scaffold. Coverage stays 3.
- **V73.B**: live probe — RAE 2822 case_definition (structured C-grid mesh,
  rhoSimpleFoam + kOmegaSST + Sutherland, y+≤1, freestreamProbe + forceCoeffs
  + surfaces FOs matching the extractor contract) hand-run in a fresh ESI
  --rm container; REPRODUCE.md + frozen artifacts; gate replays SANITY.
  Anchor digitization (AGARD AR-138) + operating-point adjudication land here.
- **V73.C**: backend wiring — GeometryType enum + adapter dispatch +
  TaskRunner verify + whitelist name==id + cfdtrust reconciliation +
  backend-e2e frozen evidence + matrix row annotation (rhoSimpleFoam row
  gains rae2822_case9; **coverage stays 3**, stated again at flip-time).

## §10 USER adjudication queue (surfaced, not blocking this slice)

1. **Operating point**: corrected (M=0.734/α=2.79, pinned) vs nominal
   (M=0.730/α=3.19) vs B109's mixed form (M=0.730/α=2.79) — gold field
   `user_adjudication_pending` keeps the dispute loud until ratified.
2. **V72 unparking**: fuel-tank-slosh re-entry (civil-aircraft VOF) — yes/no/
   later.

## Surface scan (V61-088)

ROADMAP/matrix: maps to capability-matrix §6 gap#2 (annotated this commit).
Grep `rae2822|RAE 2822|transonic_airfoil` over src/ ui/backend/ scripts/:
zero prior implementation (the existing `naca0012_transonic` anchor is a
different case with a different gold; `airfoil_surface_sampler` z-sign split
documented as the F6 anti-pattern, NOT extended — new specialized vertical
per wedge/V72 precedent). **Surface-scan: clean · disposition: new.**

## Rollback

git revert of this slice's commit(s); no adapter/UI/state coupling.
