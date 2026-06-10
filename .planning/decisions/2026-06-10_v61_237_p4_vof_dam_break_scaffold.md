---
decision_id: DEC-V61-237
title: P4 V72.A · VOF dam-break vertical scaffold (gold + extractor + gate + tests; NO solve, NO coverage claim)
status: Accepted (autonomous under sponsor full-delegation 2026-06-10 · Codex chain R0 2×P2 fixed 480e1c7 → R1 clean zero-finding)
parent_dec: DEC-V61-207 (Blueprint v4 vertical-first) · DEC-V61-224(b) (image-gating provision) · DEC-V61-234 (wedge backend-wiring precedent)
phase: P4 (V72 arc · first multiphase-VOF compute type · capability matrix "interFoam (VOF) — GAP-TRACKED V72+ candidate")
notion_sync_status: n/a (Notion retired per sponsor 2026-06-09)
autonomous_governance: true   # sponsor mandate 2026-06-10: "批准你全权推进下一个里程碑开发" — milestone selection + slice scoping delegated; counter +1
confidence: high
date: 2026-06-10
loop_auditor: "FLAG (design review, pre-implementation) — all 6 must-fixes adopted, see §4"
codex_tool_report_path: reports/codex_tool_reports/2026-06-10_v72a_scaffold_R{0,1}.md
codex_review_relay: 86gs (gpt-5.4 xhigh · R0 [P2 anchor-completeness, P2 pinned-time] both fixed -> R1 zero-finding clean)
---

# DEC-V61-237 · V72.A VOF dam-break scaffold

## TL;DR

Open the V72 arc (first **multiphase-VOF** compute type, per Blueprint v4 §4
P4+ sequencing: compressible ✅ coverage=3 → VOF → LES). This slice lands the
OFFLINE scaffold only — gold standard + pure extractor + fail-closed two-tier
gate + 38 tests — mirroring the wedge V71.A cadence (DEC-V61-232 scaffold →
233 live probe → 234 backend wiring + flip). **No solver runs in this slice;
runnable-coverage stays 3; nothing here is "validated".**

## Milestone selection rationale (sponsor full-delegation 2026-06-10)

- P1 COMPLETE (DEC-V61-210) · P2 CLOSED (DEC-V61-217) · P3 MET coverage=2
  (DEC-V61-228) · P4 in progress coverage=3 (DEC-V61-234/235/236, user-ratified
  2026-06-09). Blueprint v4 §4 P4+ names the next compute types: "rhoCentralFoam
  (ONERA M6) → VOF → LES…, each gated on runnable + validated".
- `.planning/cfd_capability_matrix.md` already tracks "interFoam (VOF)" as
  **GAP-TRACKED: V72+ candidate** — this arc is the project's own named next gap.
- Open V71B followups are slices, not milestones: FOLLOWUP-1 item 2 (advisor
  live-caller wiring) and FOLLOWUP-2 (editor-identity, user-ratified KNOWN
  LIMITATION) remain queued, untouched by this DEC.

## Benchmark + anchor (oracle-quality discipline)

Geometry = OpenFOAM-tutorial damBreak column WITHOUT the obstacle: a=0.1461 m,
h0=0.2922 m (= 2a exactly ⇒ **Martin & Moyce 1952 n²=2 column**), tank 0.584 m,
2D. QoI = dimensionless surge-front Z = x_front/a at T ∈ {1.0, 2.0}
(T = n·t·√(g/a); t = T·√(a/2g) = 0.086293/0.172586 s — re-derived in tests).

**Two-tier oracle** (full spec in the gold header + `src/dam_break_gate.py`):
- **Tier 1 SANITY** (closed-form, always enforced): G0 initial column intact ·
  G1 strict Ritter upper bound Z(T) < 2T (reduction Z_Ritter=2T proven for any
  aspect ratio; experiment ~15% slower ⇒ bound only, NEVER band target) ·
  G2 monotone collapse · G3 collapse floor Z(T_last)>1.5 (kills the Z≡1.0
  unrun-case tautology) · G4 water-volume conservation ≤1% · G5 α boundedness.
  Verdict naming capped at **SANITY-PASS** — not validation, not coverage.
- **Tier 2 M&M experimental band ±10%**: candidates **null +
  DECLARED-NOT-VERIFIED** — the commonly quoted Z≈2.0@T=1.0 *violates the
  Ritter bound under this file's convention* (loop-auditor F1 live catch: a
  time-normalization clash; under M&M variables literature reads ~1.3-1.5).
  Values stay null until digitized from the primary source (M&M 1952 Part IV)
  or trusted reproduction (Ubbink 1997). Consumer-side enforcement in the gate:
  status enum fail-closed + provenance required + **anchor meta-gate
  Z·(1+tol) < 2T** (violating anchor ⇒ REJECTED_ANCHOR, never consumed).
  `coverage_eligible` is true ONLY for sanity-pass + tier-2 ENFORCED + pass.

## §4 loop-auditor design review (pre-implementation · FLAG · all adopted)

| # | Finding | Adoption |
|---|---|---|
| F1 P1 | Candidate anchor Z≈2.0@T=1 violates own Ritter bound (convention clash) | Candidates nulled; anchor meta-gate in gate + gold self-test |
| F2 P1 | Gold status field flippable without trace | 3 pins: test pins DECLARED-NOT-VERIFIED; enum fail-closed; VERIFIED requires non-empty provenance (negative tests for each) |
| F3 P2 | Tier-1 window [floor, 2T) too wide to call "validated" | Verdict named SANITY-PASS; "validated" forbidden in tier-1 output (test-asserted) |
| F4 P2 | Tier-1 has no run-provenance | Declared in gold header + gate docstring; provenance comes from V72.B/C frozen-evidence chain |
| F5 P3 | Volume integral source unspecified | Extractor requires cell-volumes field V; missing ⇒ hard error, no uniform-mesh fallback |
| F6 P3 | max(x) front splash-sensitive | min-wet-cells guard (≥3) + declared limitation |

Self-caught addition: original G3 floor 2.5 could false-BLOCK a correct
solution (literature Z(T=2)≈2.2-2.5 under the M&M convention) — lowered to 1.5
(anti-tautology intent unchanged; correct solutions clear it by ≥0.7).

## Image gating (DEC-V61-224(b) provision · probed 2026-06-10 on this machine)

- (a) **PRIMARY pinned**: ESI `opencfd/openfoam-default:2312` — `interFoam`
  confirmed at `/usr/lib/openfoam/openfoam2312/platforms/linuxARM64GccDPInt32Opt/bin/interFoam`
  (native arm64). Runner reuse: wedge `_docker_run_esi_rm` (DEC-V61-234).
- (b) Adapter wiring + cfdtrust reconciliation: **deferred to V72.C** (this
  slice touches no adapter code — wedge precedent: enum + dispatch land with
  the wiring slice, avoiding a dispatchable-but-misrouted enum window).
- (c) **FALLBACK**: OF11 Foundation `openfoam/openfoam11-paraview510`
  `foamRun -solver incompressibleVoF` (VoF module libs confirmed present;
  image is linux/amd64 EMULATED on this arm64 host — slower, fallback only).

## Files (this slice)

- `knowledge/gold_standards/dam_break_collapse.yaml` (NEW — two-tier oracle SSOT)
- `src/dam_break_extractor.py` (NEW — Execution plane; pure; ascii alpha.water
  + C + V; anti-tautology: never reads solver isoSurface output; fail-closed)
- `src/dam_break_gate.py` (NEW — Control plane; tier-1 SANITY + tier-2
  consumer-side enforcement; `coverage_eligible` explicit)
- `src/_plane_assignment.py` + `.importlinter` (regenerated, same commit, ADR-001/002)
- `tests/p4/test_dam_break_{gold,extractor,gate}.py` (NEW — 38 tests: every
  tier-1 gate bitten by a doctored case; tier-2 triad negatives; gold pins)

## 四问门控

- **LLM 离线可跑**: YES — gold/extractor/gate/tests are deterministic offline
  code; no LLM in any path.
- **artifacts**: YES — gate emits a structured verdict (summary + per-gate
  booleans + z_by_T); V72.B/C add frozen REPRODUCE/EVIDENCE dirs.
- **TrustGate 解释**: YES (forward) — `coverage_eligible=False` until tier-2
  VERIFIED keeps any TrustGate consumer honest; wiring to TrustGate verdict
  reduction lands with V72.C alongside the runner.
- **AI advisory-only**: YES — no mutating route, no UI surface; pure
  evaluation-side scaffold.

## Verification (this slice)

- `pytest -q tests/p4/` → 111 passed, 2 skipped (38 new; wedge/BFS untouched).
- `lint-imports --config .importlinter` → 5 contracts kept, 0 broken.
- Affected-by-fragility files run individually → 7/8 green;
  `tests/test_auto_verifier/test_task_runner_integration.py` fails on ANY
  fresh checkout — **pre-existing landmine, proven not-ours**: pristine
  c4d275d reproduces the identical 8-file collection error set (zero V72.A
  files involved). Root cause (sys.path-poisoning conftests masked only in
  cfd-audit-merge by the editable-install .pth) + fix proposal queued as
  **V72A-FOLLOWUP-1** (`.planning/followups/v72a_fullsuite_collection_fragility.md`).

## Slice plan (V72 arc)

- **V72.A (this DEC)**: offline scaffold. Coverage stays 3.
- **V72.B**: live probe — case_definition (blockMesh + setFields + interFoam,
  writeFormat ascii, pinned write times, writeCellCentres/Volumes) hand-run in
  a fresh ESI --rm container; REPRODUCE.md + frozen probe artifacts; gate
  replays SANITY against them. Tier-2 anchor digitization (M&M primary /
  Ubbink) happens here; anchor flips to VERIFIED with provenance + meta-gate.
- **V72.C**: backend wiring — GeometryType enum + `_execute_vof_dam_break`
  early short-circuit + TaskRunner `_verify_vof_dam_break` + whitelist
  name==id entry (236-R3 rename-escape lesson) + cfdtrust reconciliation +
  backend-e2e frozen evidence + capability-matrix flip **3→4** (only if gate
  `coverage_eligible == true`).

## Surface scan (V61-088)

ROADMAP/matrix: VOF maps to capability matrix "GAP-TRACKED: V72+ candidate".
Grep `dam.break|damBreak|interFoam|VOF` over src/ ui/backend/ scripts/: zero
prior implementation (cfdtrust ingest has generic VOF log plumbing only —
Gap #25/#21/#48, untouched here). **Surface-scan: clean · disposition: new
specialized vertical per wedge precedent.**

## Rollback

git revert of this slice's commit(s); no adapter/UI/state coupling.
