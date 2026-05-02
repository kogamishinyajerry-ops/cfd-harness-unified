# STATE.md backfill — 2026-04-22 (post-attestor) through 2026-05-03

> Backfilled 2026-05-03 by Claude Code subagent after STATE.md drift was discovered. Covers DEC-V61-039..V61-110 (~65 decisions, 12 days). For full prose see individual DEC files. Splice this content into STATE.md after the existing "## 2026-04-22 — Phase 8 Sprint 1 — PASS-washing remediation" section.

---

## 2026-04-22 (afternoon/evening) — Phase 8 Sprint 1 close + multi-persona Codex iteration kickoff

Phase 8 Sprint 1's PASS-washing-cleanup chain landed 7 more DECs in the late-day window: 3-tier verdict surface (LDC/UI/attestor), 4 case-specific extractor fixes (wall_gradient / plane_channel u+ / NACA Cp / cylinder Strouhal-FFT), the Kogami-driven blocker-fix wave V61-045, and two demo-first multi-persona Codex iteration arcs (V61-046 / V61-047) that introduced the 3-persona + 2-persona Codex review pattern still in use.

**Verdict-surface DECs (39/40):**
- **DEC-V61-039** (counter 26→27): LDC verdict reconciliation — surfaces both `profile_verdict` (PARTIAL 11/17) and scalar (FAIL +370%) through ValidationReport instead of hiding the split. Codex skipped per self-pass 0.80 > 0.70 threshold (commit `8ca850e`).
- **DEC-V61-040** (counter 27→28): UI attestor surface — pipes DEC-038 A1..A6 attestor through API + AttestorBadge / AttestorPanel React components. Codex APPROVE in 3 rounds.

**Case-extractor fixes (4 DECs, all part of the PASS-washing cleanup chain):**
- **DEC-V61-042** (counter 28→29): Shared `src/wall_gradient.py` Fornberg 3-point stencil — root-cause fix for Nu extraction in DHC / impinging_jet / RBC. Plumbs `wall_coord` / `wall_value` / `wall_bc_type` through generators. Codex APPROVE in 4 rounds.
- **DEC-V61-043** (counter 29→30): plane_channel u+/y+ emitter via wallShearStress + line-sampler FOs. New `src/plane_channel_uplus_emitter.py`. Codex APPROVE in 2 rounds. Counter hits 30 — arc-size retro now due.
- **DEC-V61-044** (counter 30→31): NACA0012 surface Cp(x/c) sampler via `surfaces` FO (not volume-cell band averaging). New `src/airfoil_surface_sampler.py`. Codex APPROVE in 3 rounds.
- **DEC-V61-041** (counter 31→32): cylinder Strouhal FFT — retires the canonical-band hardcode (`if 50≤Re≤200: St=0.165`) and replaces with forceCoeffs FO + Cl(t) Hann-windowed DFT. Last PASS-washing shortcut in the codebase. Codex APPROVE in 2 rounds.

**V61-045 — Kogami-escalated multi-wave blocker fix:**
- **DEC-V61-045** (counter +1, COMPLETE via Kogami autonomous escalation): closes 8 Codex blockers across DEC-036b + DEC-038. 4 Waves landed (`61c7cd1`, `9e6f30f`, `49ba6e5`, `396cefe`, `ad0bad2`, `5433e20`, `8d9a74a`, `b1e4005`). 43 new tests. Final Codex CV-S003q-02 VERIFIED at `b1e4005` (303 passed + 1 skipped; impinging_jet A6 PASS; LDC ATTEST_PASS preserved). Started life as PROPOSAL; promoted via Kogami review per v6.2 governance.

**V61-046 / V61-047 — multi-persona Codex iteration arcs:**
- **DEC-V61-046** (counter 33): demo-first convergence + 3-persona Codex iteration loop — introduced the round-1 / round-2 / round-3 batch pattern across 3 reviewer personas. APPROVE_WITH_COMMENTS R3 across all 3 personas. 15 commits in scope (`87b3b39`..`f6d1743`). UI flips `/` → `/learn` default; Dashboard moves to `/pro`.
- **DEC-V61-047** (counter 34): 10-case CFD pedagogy review · expert + novice 2-persona iteration. APPROVE_WITH_COMMENTS R3 both personas. Story tab + teaching cards + evidence-collapse landed across 6 commits.

**Also landed earlier in the day** (predated the existing Phase 8 Sprint 1 narrative tail but worth recording):
- **DEC-V61-035** (counter 20→21, "phase7 deep review pass-washing fix"): minimum-fix correction DEC — flips default-run resolution `reference` → `audit_real_run` + relabels /learn visual-only section as "未完成金标准验证 / cannot be read as computed-PASS". 4 files changed.

**Counter**: 24 → 34 (10 additive DECs · 045 Kogami-escalated · 046/047 multi-persona arcs)
**RETRO-V61-003 (counter32 retro) lands today** at counter=32 covering DEC-V61-035..V61-041 arc (see RETROs section).
**Open**: V61-046/047 arc methodology becomes the template for V61-050+ Codex iteration discipline.

---

## 2026-04-23 — CFD case deep-dive arc (V61-048..V61-053): single-case pilot methodology birth

User read post-V61-047 closeout: *"现在几乎没有一个 case 有阅读价值"*. This pivots the day's work from "10-case uniform improvement" to "single-case pilot end-to-end" methodology.

- **DEC-V61-048** (counter 35): 10-case deep-read value review · 4-batch fanout (benchmark lineage / TeachingCard 2.0 / repro runbook / flagship physics-intuition). 4 commits (`fb83f0d`..`12de4fe`). Status: AWAITING_USER_READ — exit gate is user subjective pedagogy read, not Codex.
- **DEC-V61-049** (counter 36): LDC single-case pilot · CFD-novice end-to-end walk · pattern-before-rollout. 4 batches A+B+D+E landed (`6d8e8f5`..`4a3fbf1`). User judged V61-048 "still insufficient" → redirected to single-case sequential rollout. Compare tab gains 5 named dimensions but only 1 truly independent observable; sets up V61-050.
- **DEC-V61-050** (counter 37): LDC true multi-dimensional validation · 4 genuinely independent Ghia-1982 observables (u_centerline + v_centerline + primary vortex + secondary BL/BR). 4-round Codex arc (R1 CHANGES_REQUIRED 1H+3M+1L → R2 → R3 → R4 APPROVE clean). 9 commits (`1d3505c`..`715786e`). First Type I `methodology v2.0` apply.
- **DEC-V61-051** (counter 38, ABANDONED_PHASE_1): BFS visual upgrade hit a wall — adapter doesn't generate a step. Commit `4e4813f` reverted in `8ff71e4`. Codex `check_all_gates` returned G3 |U|=inf, G4 k<0 -6.41e+30, G5 continuity=5.25e+18 — gold YAML self-documents the hazard. Successor is V61-052.
- **DEC-V61-052** (counter 39): BFS adapter rewrite · multi-block geometry + fixture regen + LDC-style iteration loop. 5-round Codex arc (R1/R2 CHANGES_REQUIRED → R3 APPROVE_WITH_COMMENTS → R4 caption-staleness CHANGES_REQUIRED → R5 APPROVE clean per new F1-M2 two-tier close gate). 10 commits (`4ba4fd7`..`e830abf`). Xr/H=5.64 (-9.9% vs gold).
- **DEC-V61-053** (counter 40): cylinder Type I multi-dim · LDC-style v2.0 first-apply. 4-round Codex arc + 6 post-R3 live-run defects fixed in attempt-6 (self._db accessor, GAMG→PCG, extractor gating, sort-key, transient_trim defaults, FO executeControl). Status IN_PROGRESS_DEMONSTRATION_GRADE — strouhal=0.138 (16% dev), cd=1.379 (3.7% dev). 17 commits. **Drives RETRO-V61-053 addendum** introducing `executable_smoke_test` + `solver_stability_on_novel_geometry` risk_flags into intake template.

**Counter**: 34 → 40 (6 DECs · arc-size retro now well past trigger)
**Open**: V61-053 gold-grade follow-up needs CYLINDER_ENDTIME_S 10s→60s/200s bump.

---

## 2026-04-24 — RETRO-V61-053 lands (no DECs)

No new DECs landed; **RETRO-V61-053** (Python version parity + 3-round Codex calibration) authored covering the V61-053 arc and codifying the post-R3 live-run defect methodology. See RETROs section.

---

## 2026-04-25 — P1 Metrics & Trust arc (V61-054..V61-056) + 3 multi-dim case extensions (V61-057/058/061) + W2 G-9 attestation

Two parallel arcs land: the **P1 Trust Gate** infrastructure layer (54/55/56) and three more multi-dim CFD case extensions reusing the v2.0 methodology (DHC/NACA0012 + NACA mesh refinement). G-9 W2 Opus Gate attests the Foundation-Freeze.

**P1 Trust-Gate arc:**
- **DEC-V61-054** (counter 41): P1-T1 MetricsRegistry + 4 metric-class wrappers (Pointwise / Integrated / Spectral / Residual). Codex R1 CHANGES_REQUIRED (REF_SCALAR_KEYS leak + tolerance-policy leak + residual doc drift) → R2 APPROVE_WITH_COMMENTS clean close. 6 commits (`2b5ceb7`..`83f1161`).
- **DEC-V61-055** (counter 42): P1-T2 TrustGate reducer + P1-T3 CaseProfile.tolerance_policy schema + loader. R1 APPROVE_WITH_COMMENTS clean close (1 immutability finding fixed verbatim). 3 commits.
- **DEC-V61-056** (counter 43): P1-T5 task_runner TrustGateReport integration (first Control→Evaluation slice). R1 APPROVE_WITH_COMMENTS clean close (2 findings on ATTEST_NOT_APPLICABLE note + E2E coverage). Commit `bc91716`. 666 tests pass.

**Multi-dim case extensions (parallel arc, counter collides intentionally with P1):**
- **DEC-V61-057** (counter 41): differential_heated_cavity Type I multi-dim · de Vahl Davis 1983 · v2.0 second-apply. 4-round Codex arc (R1..R4 APPROVE_WITH_COMMENTS Stages C+D). Stage E live OpenFOAM run: Nu_avg=8.838 vs gold 8.800 → **+0.44% PASS** (672.4s wall). 4 cross-check observables wired but their fixture integration deferred.
- **DEC-V61-058** (counter 42): NACA0012 multi-dim · Type II 5-row · Ladson 1988 · v2.0 third-apply. 3-arc Codex sequence (pre-Stage-A REQUEST_CHANGES forcing case_type I→II downgrade + gold provenance pivot → R1 CHANGES_REQUIRED 1 BLOCKING α-routing statefulness → R2 APPROVE_WITH_COMMENTS). Stage E live sweep α∈{0,4,8}° solver-converged but 16k-cell mesh under-resolved. **Status: METHODOLOGY_COMPLETE_PHYSICS_FIDELITY_GAP_DOCUMENTED.**
- **DEC-V61-061** (counter 43): NACA0012 mesh refinement · v2.0 fourth-apply. 2 mesh iterations (16k → 43k → 96k cells). Cl@α=8° improves 0.491 → 0.625 → 0.675 (40% under → 17% under, gold 0.815). Status: ITERATION_IMPROVEMENT_TOPOLOGY_CEILING_REACHED — H-grid + wall-function ceiling at Cl≈0.68-0.72; clearing 5% gate requires C-grid AND/OR LowRe. Closed early (2/4 iter) to avoid infinite mesh loop.

**G-9 attestation (no counter impact):**
- **G-9 W2 Opus Gate · Foundation-Freeze Done + P1 Metrics & Trust Layer Active** — attested 2026-04-25T12:38+08:00 by Notion @Opus 4.7 (independent context). Authority: PIVOT_CHARTER §7 + ADR-002 §2.3 + RETRO-V61-005.

**Counter**: 40 → 43 (6 DECs · two parallel arcs share counter 41/42/43)
**RETROs landed today**: RETRO-V61-004 (P1 arc complete) + RETRO-V61-005 (ADR-002 W2 Gate arc) + RETRO-V61-006 (W4 prep R1 incident).
**Open**: P1-T4 ObservableDef formalization blocked on KNOWLEDGE_OBJECT_MODEL v1.0; NACA0012 5%-gate clearance needs architectural change (V61-062 candidate).

---

## 2026-04-26 — 治理收口 anchor session: GOV-1 v0.5+ enrichment + Independent Opus audit + P1-tail wiring + P2 kickoff

Largest single-day decision volume in this window. Two concurrent sessions: **Session A** (governance closure 071/072/073/074) + **Session B** (GOV-1 case enrichment 080/081/082/085/086). Independent Notion @Opus 4.7 audit ratifies session-A closure and unblocks P2.

**Session A — governance closure tail + P2 kickoff:**
- **DEC-V61-071** (autonomous_governance: false): wire `load_tolerance_policy` into task_runner._build_trust_gate_report (P1 trust-tail). R1 CHANGES_REQUIRED (slug resolution F#1 MED + lazy-load F#2 LOW, fix `f0f0f80`) → R2 APPROVE_WITH_COMMENTS clean close.
- **DEC-V61-072** (counter +1): Sampling Audit Anchor first execution · §10.5 active activation. 9 commits audited; 4 findings (2 HIGH + 2 MED) → §10.5.4a 5 surfaces added; sampling interval dropped 20→5.
- **DEC-V61-073** (autonomous_governance: false): independent Opus 4.7 audit ratification + 4 HIGH amendments + P2 kickoff HOLD → GREEN. 4 PCs landed (PC-2 EXECUTOR_ABSTRACTION v0.2 `50bb2eb` Codex R3 APPROVE; PC-3 sampling_audit.py `55f2642` R2 APPROVE; PC-4 §10.5.4a 7-surface canonical `25c4cd8` R3 APPROVE).
- **DEC-V61-074** (counter +1): P2-T1 ExecutorMode ABC + 4-mode skeleton + manifest tagging + dispatch + routing (full P2-T1 scope T1.a + T1.b). T1.a R3 APPROVE `16000ab` (3-round arc); T1.b.1 R2 APPROVE `f599129`; T1.b.2/T1.b.3 post-commit R2 APPROVE `8d7f990`. 49/49 executor tests + 119/119 audit_package tests + 966/968 full-suite.

**Session B — GOV-1 v0.5+ enrichment under audit:**
- **DEC-V61-080** (counter +1): GOV-1 Gold Case CaseProfile enrichment + tolerance citation backfill (10/10 cases, Option B docs-only). RATIFY_WITH_AMENDMENTS by independent audit; A1+A2+A3+A4-evidence+A5 landed at `4cb2aad`. Sets the AUTH-V61-080 CLASS-1/2/3 framework for following DECs.
- **DEC-V61-081** (counter +1): CCW Williamson 1996 DOI typo fix · CLASS-1 trivial. 4 occurrences in YAML + 1 in citations.bib. No Codex required.
- **DEC-V61-082** (counter +1): DCT Jones 1976 journal swap (IJHMT → ASME J Fluids Eng) + correlation form correction · CLASS-2 with substantive re-description. Status ACCEPTED_PENDING_CODEX_REVIEW.
- **DEC-V61-085** (autonomous_governance: false, PROPOSED): Pivot Charter §4.7 codification proposal · gold-value modification authority CLASS-1/2/3 line-drawing rule. Charter mod is CFDJerry's gate; **proposal only, not landed**.
- **DEC-V61-086** (counter +1): GOV-1 v0.7 · tier-(c) → tier-(a) citation trace pass · 1 upgrade + 7 honest fallback. CLASS-1 docs-only. Codex skipped (no risk-tier trigger fires).

**Forensic flake debug session (artifact, not full DEC):**
- **DEC-V61-FORENSIC-FLAKE-1** (counter +1): forensic identification — `test_build_trust_gate_report_resolves_display_title_to_slug` born flaky at `f0f0f80` (DEC-V61-071 R1) due to sys.modules pollution from `test_plane_guard_edge.py`.
- **DEC-V61-FORENSIC-FLAKE-1-FIX** (counter +1): test-isolation fix · sys.modules restore in polluter. Pure test-isolation fix, no src/** or knowledge/** touched.

**Counter**: 43 → ~52 (heavy day; 071/073/085 are non-counter; rest +1 each)
**RETROs landed**: RETRO-V61-005 (governance closure draft) + RETRO-V61-006 (Session B arc).
**Open**: V61-085 awaits CFDJerry Charter ratification; V61-082 awaits Codex review.

---

## 2026-04-27 — P2-T2 Docker substantialization + Kogami subprocess bootstrap + pre-implementation surface scan

Three structural DECs land: P2-T2 makes the Docker executor real; V61-087 introduces the Kogami subprocess governance gate (deprecating the Notion-Opus async review); V61-088 adds pre-implementation surface scan as routine startup discipline.

- **DEC-V61-075** (counter +1): P2-T2 · DockerOpenFOAMExecutor + FoamAgentExecutor substantialization + §6.3 reference-run resolver + executable_smoke_test. T2.1+T2.2 bundle Codex pre-merge APPROVE R5 `b2ea911` (5-round arc); T2.3 post-commit APPROVE R5 `9c7359f` after fixes `bf6aac5`/`6a13b31`/`27d4e06`/`2170590`/`30b866f` closing 6 P-level findings. T2.4 LDC smoke `57a0dc5`. 17 executor_modes tests + 18 task_runner_executor_mode tests + 16 reference_lookup tests + LDC executable smoke. 1003 passed / 2 skipped / 0 failed.
- **DEC-V61-087** (counter 52→53): **Kogami-Claude-cosplay 战略审查 subprocess bootstrap · 三层职责分离 · v6.1 → v6.2 governance evolution**. v3 R2 APPROVE_WITH_COMMENTS clean close (after v1+v2 R1 CHANGES_REQUIRED rejections — Tier 1 isolation primitives empirically failed on Claude Code 2.1.119; clean HOME breaks auth, --mcp-config alone doesn't disable MCP). Final approach uses `--strict-mcp-config` + `--tools ""`. Establishes Kogami as advisory gate for phase-close / RETRO drafts / high-risk PR (post-Codex-APPROVE) / counter ≥ 20 / autonomous_governance rule changes. Notion @Opus 4.7 deprecated. **Defines v6.2 four-role architecture: Claude Code (Opus 4.7) + Kogami subprocess + Codex (relay) + Notion archive.**
- **DEC-V61-088** (counter +1, PROPOSED): pre-implementation surface scan · 动手前 ROADMAP + 已有实现 grep as routine gate. Authored under Notion-Opus advisory P1 finding §3 ("run-compare API '再发现' event"). Awaits Kogami review per V61-087 §4.

**Counter**: 52 → 54 (V61-087 hits 53; V61-075 + V61-088 add 2)
**Open**: V61-088 Kogami review pending.

---

## 2026-04-28 — M-VIZ / M-RENDER / M-PANELS kickoff arc + M5.1/M6.1 trust-core micro-PRs + Pivot Charter Addendum 3

Largest single-day surface change since the Pivot Charter day. CFDJerry product-narrative criticism *"我要我的工作台能对标 ANSYS ... 不自动跳转下一步"* drives Addendum 3 ratification + 3 cascading milestone kickoffs (M-VIZ → M-RENDER-API → M-PANELS) under §4.c HARD ORDERING. M5.1 + M6.1 are smaller trust-core changes that complete just before.

**Trust-core micro-PRs:**
- **DEC-V61-089** (autonomous_governance: false, CLASS-1 docs-only): two-track invariant · gold-case-line ≠ workbench-line · parallelizable · share-downstream-only. Cross-session alignment anchor; no Kogami trigger.
- **DEC-V61-090** (counter +1): M6.1 trust-core micro-PR · `mesh_already_provided` flag + blockMesh skip when polyMesh exists. **Codex 8-round arc → APPROVE** + Kogami APPROVE_WITH_COMMENTS findings inline-addressed + CFDJerry explicit ratification. Commits `1831a77` + `be0cec6`.
- **DEC-V61-091** (counter +1): M5.1 trust-core micro-PR · TrustGate hard-cap on imported user-case verdicts (PASS_WITH_DISCLAIMER ceiling). Codex 3-round arc R1 APPROVE_WITH_COMMENTS → R3 APPROVE clean + Kogami APPROVE_WITH_COMMENTS + CFDJerry ratify. Commits `7f6e3f2` + `ce25e9e`.
- **DEC-V61-092** (counter +1): workbench nav-discoverability defect · expose `/workbench` from `/learn` + `/pro` shells. Codex 3-round arc R1 CHANGES_REQUIRED → R3 APPROVE clean. Commits `f7ff827` + `d7411ac`. Kogami not triggered (4-condition self-check).

**Pivot Charter Addendum 3 + milestone kickoff cascade:**
- **DEC-V61-093** (counter +1): **Pivot Charter Addendum 3 ratification — CAE-workbench interaction pivot** (engineer-in-the-loop · ANSYS-Fluent-class · per-step AI co-pilot). Codex SKIPPED (CLASS-1 docs-only) · Kogami APPROVE_WITH_COMMENTS · 4 findings addressed inline · CFDJerry ratify. Establishes 3D viewport center + engineer-driven step advance + Fluent 5-step template framing.
- **DEC-V61-094** (counter +1): M-VIZ kickoff · 3D viewport infrastructure (vtk.js · STL render · camera controls). First milestone under Addendum 3 §3.a. CLASS-1 docs-only kickoff; Kogami APPROVE_WITH_COMMENTS + CFDJerry ratify. Implementation arc closed same day at commit `36c4a78`.
- **DEC-V61-095** (counter +1): M-RENDER-API kickoff · backend geometry/mesh/field render endpoints · trimesh.export + glTF binary · second milestone. CLASS-1 docs-only kickoff. **Implementation arc closed 2026-04-28 · Codex APPROVE R5 · 7 findings closed across 5 rounds · arc commits `c4264f7`..`84fa4cf` (closure `3acdf14`).**
- **DEC-V61-096** (counter +1): M-PANELS kickoff · three-pane workbench shell + 5-step tree + AI 处理 / 下一步 / 上一步 button contract · third milestone. CLASS-1 docs-only kickoff; Codex SKIPPED at kickoff (will fire pre-merge during impl Step 8 per ≤70% gate). Kogami not triggered (4-condition pass).

**Counter**: 54 → ~61 (V61-090..V61-096 each +1; V61-089 docs-only no counter)
**Open**: M-PANELS implementation Steps 1-8 pending pre-merge Codex; M-VIZ Step-7 deferred face-naming feature recorded as Tier-B candidate.

---

## 2026-04-29 — M-AI-COPILOT kickoff (collab-first) + M-PANELS Phase-1A staging fix + M9 Tier-B AI kickoff + minimal channel executor

M-PANELS Phase-1A LDC end-to-end demo (V61-097, lands earlier in day) exposes a collab-first gap that motivates V61-098. CFDJerry catches a post-R3 staging-order regression on first dogfood. Then M9 Tier-B + minimal channel executor extend the loop to non-LDC geometry.

- **DEC-V61-098** (counter +1): **M-AI-COPILOT (collab-first) kickoff** — human-AI collaboration layer for arbitrary-STL workflows · 4 interaction primitives + face-pick + `face_annotations.yaml` + AIActionEnvelope · merges deferred M-PANELS face-pick. **Codex 7-round arc COMPLETE** (Steps 2+3 R3 APPROVE `67b0465`; Steps 6+7a R2 RESOLVED `b3e1720`; Step 7b R2 RESOLVED `0abdd74`). Kogami not triggered. **2026-04-30 gating swap**: human-CFDJerry visual smoke → Claude-Code-automated `scripts/smoke/dogfood_loop.py`.
- **DEC-V61-099** (counter +1): M-PANELS Phase-1A · post-R3 live-run defect closure — solver_streamer staging order regression. CFDJerry caught on first LDC dogfood after V61-097 R4 RESOLVED `c49fd11`. RETRO-V61-053-class post-R3 defect; pre-merge Codex mandated by RETRO-V61-001 OpenFOAM-solver-bug-fix trigger. `solver_streamer.py` lines 284-321 staging order rewrite.
- **DEC-V61-100** (counter +1): M9 Tier-B AI kickoff — productized pick→annotate→re-run loop + arbitrary-STL classifier roadmap. Era 1 LOOP SPINE first milestone. Step 1 `aa4d3f1` Codex APPROVE_WITH_COMMENTS; Step 2 `11b81ba` Codex 3-round R3 APPROVE; Step 3 `faa2e08` + `a54f4b7` + `6ae9a3b` Codex 3-round R3 APPROVE.
- **DEC-V61-101** (counter +1): minimal laminar channel executor — closes M9 dialog→annotate→re-run loop on the FIRST non-LDC geometry. Step 1 commits `b7986ba` + `e470618` + `44d1716` Codex 2-round R2 APPROVE. Bounded laminar slice (icoFoam, no turbulence model, no BL prism).

**Counter**: ~61 → ~65
**Open**: M11 / M12 mesh wizard + multi-solver still downstream; classifier still emits BLOCKED for cases beyond LDC + channel.

---

## 2026-04-30 — M-RESCUE foundation + adversarial-loop CAD defect closures (V61-103/104/107/107.5)

User direction: *"在CAD几何操作、算例设置方面，功能必须完全覆盖，否则项目就是不完整的，工程师在AI表现不佳的情况下，甚至无法手动介入，拯救算例"*. M-RESCUE introduces the manual-override foundation. Adversarial loop iter01-06 surfaces 9 critical/high pipeline defects, several POST-R3 — closed across 4 DECs.

- **DEC-V61-102** (counter +1): **M-RESCUE · Manual override foundation** — every AI-authored dict becomes engineer-editable. Phase 1 backend `8b4e602`..`7677496` Codex 7-round APPROVE_WITH_COMMENTS chain; Phase 2 frontend `323a326`..`658bf86` Codex 4-round APPROVE chain. Cross-cutting foundation; M10-M14 inherit. Adds `case_lock` primitive for manifest race-safety (root of subsequent V61-109 hardening cycle).
- **DEC-V61-103** (counter +1, PROPOSED): imported-case BC mapper · `/setup-bc?from_stl_patches=1` mode driven by named polyMesh patches. Adversarial iter02-03 proved the mesh + solver layers are CAD-agnostic — only LDC coupling is at `routes/case_solve.py:206`. Promotes the iter03 `author_dicts.py` workaround to first-class workflow.
- **DEC-V61-104** (counter +1): interior-obstacle topology · gmsh runner builds outer surface loop + reversed-inner loops for cases with interior bodies. Phase 1 commits `30b659b` + `bec98b2` (Codex chain R8 APPROVE_WITH_COMMENTS → R9 APPROVE clean). **2026-05-01 empirical correction**: probe across mesh densities lc=0.0085→0.001 confirmed gmsh single-loop addVolume ALREADY treats internal shells as obstacles; multi-loop scaffolding redundant but R8 containment guard valuable. Phase 1.5 re-scoped to investigate iter01's actual physics defect (BC/solver, not meshing).
- **DEC-V61-107** (counter +1): partial fvSchemes upgrade for non-orthogonal STL meshes (fvSchemes-only scope). Codex APPROVE R1 first round on `e929f01`. Self-pass 0.85 / actual 100% — calibration honest.
- **DEC-V61-107.5** (counter +1): **pimpleFoam migration for the named-patch BC mapper + post-flight rejection plumbing**. Codex APPROVE R20 commit `c924360` after **9 rounds R12-R20**. Self-pass 0.45 / actual ~10% — under-calibrated by ~0.30. Root cause: should have grep'd every `icoFoam` reference before first commit so migration surface was bounded. New SSE event surface (phase=error vs phase=completed) + FOAM FATAL block detection regex.

**Counter**: ~65 → ~70
**Open**: Adversarial iter01 physics defect (slow convergence + qualitative validation need) re-scoped to V61-106; M-RESCUE Phase 3 (case-rescue UX) still pending.

---

## 2026-05-01 — adversarial smoke as regression gate + analytical comparator + V61-108 Phase A (case_lock hardening)

Adversarial loop arc (iter01-06) operationalized as regression gate. Per-patch BC override store kicks off; case_lock R2-R10 hardening cycle exposes the architectural root of swap-to-symlink races.

- **DEC-V61-105** (counter +1, PROPOSED): adversarial smoke as hot-path regression gate · operationalizes RETRO-V61-053 `executable_smoke_test` risk_flag. Tools: `tools/adversarial/run_smoke.py` + `scripts/git_hooks/pre_push_adversarial_smoke.sh`. 9 defects fixed across iter01-06 (commits `b8053f9`..`27152d7` + smoke runner `d414367`).
- **DEC-V61-106** (counter +1, PROPOSED): analytical-comparator smoke verdicts — adds 4th `expected_status` class beyond converged / manual_bc_baseline / physics_validation_required. Lets adversarial cases declare physics-correctness checks the residual-only smoke runner can't catch (e.g. iter01 bypass-jet + downstream-recirculation pattern check).
- **DEC-V61-108-A** (counter +1): **per-patch BC classification override store** (Phase A · backend GET/PUT/DELETE with fd-based race-free I/O). Codex APPROVE R11 commit `dfb13db` after **11 rounds R1-R11**. Self-pass 0.55 / actual ~10% — under-calibrated by ~0.45. Root cause: should have read upstream `case_lock` primitive's source BEFORE writing first hardening line — case_lock's path-based open without `O_NOFOLLOW` was architectural root of every layer-cleanup attempt R2-R8. **Documents R9 residual** that lands as DEC-V61-109.

**Counter**: ~70 → ~73
**Open**: V61-108 Phase B frontend pending; V61-109 case_lock O_NOFOLLOW upstream fix queued per R9 residual.

---

## 2026-05-02 — V61-108 Phase B + V61-109 case_lock security arc (Codex + Kogami high-risk-PR review)

Phase B frontend lands. V61-109 closes the documented R9 residual at the case_lock primitive layer with high-risk-PR Kogami review.

- **DEC-V61-108-B** (counter +1): Step 3 per-patch BC classification override panel (Phase B · frontend wiring). Codex APPROVE R3 commit `f6d40e1` after 3 rounds R1-R3. R1 closure introduced single-token model that conflated case-invalidation with mutation-ordering, requiring R2→R3 dual-token split (caseGenRef vs saveSeqRef/committedSeqRef). Self-pass 0.55 / actual 0.33. Commits `4f1dd6c` / `c7cb785` / `f6d40e1` / `2b34191`.
- **DEC-V61-109** (counter +1): **case_lock O_NOFOLLOW upstream fix — close DEC-V61-108 Phase A R9 documented residual**. Codex 2-round arc R1 CHANGES_REQUIRED → R2 APPROVE on `85b88e3`. **Kogami high-risk-PR review APPROVE_WITH_COMMENTS** (4 findings closed inline: Darwin race workaround scope-folding, belt-and-braces cleanup tracked → V61-110 candidate, §10.5.4a audit-required-surface evaluation, verification table cross-reference). Recommended_next=merge. Commits `4a0fcd6` + `85b88e3`. Hardens shared-infra primitive against swap-to-symlink-at-OPEN moment. Self-pass 0.60 / actual 0.50 — calibration debt acknowledged from RETRO-V61-V107-V108 R1 baseline.

**Counter**: ~73 → ~75
**RETRO-V61-V107-V108 lands today** covering the V107 / V107.5 / V108-A / V108-B arc. See RETROs section.
**Open**: V61-110 candidate (patch_classification_store cleanup post-V109).

---

## 2026-05-03 — V61-110 framing correction (Codex catches the original "drop dead branch" intent as wrong)

Closes V61-109 successor candidate but with the scope inverted by Codex.

- **DEC-V61-110** (counter +1): Codex-corrected V109 framing in `patch_classification_store._assert_fd_still_matches_path` — **keep the S_ISLNK branch (not dead)**, update docstring + add post-lock-yield regression. Codex APPROVE R2 commit `767ed6c` after 2 rounds. R0 attempt `80ed3a8` (drop S_ISLNK branch) → Codex R1 CHANGES_REQUIRED: branch IS reachable on post-lock-yield symlink swap (V109's O_NOFOLLOW protects only case_lock's OPEN moment; once case_lock yields with dir_fd pinned, attacker can rename original case_dir away and plant symlink BEFORE _assert_fd_still_matches_path runs). R2 final scope: docstring-only correction + new regression test. **Original "drop dead branch" intent abandoned — Codex caught it as Codex-prevented regression, not post-R3 defect.** Self-pass 0.95 / R1 calibration validated.

**Counter**: ~75 → ~76
**Open**: STATE.md backfill (this file).

---

# RETROs landed in this window

| Retro ID | File | Trigger | Scope |
|---|---|---|---|
| **RETRO-V61-003** (counter32) | `2026-04-22_v61_counter32_retrospective.md` | counter ≥ 20 arc-size (RETRO-V61-001 cadence #2) | V61-035..V61-041 arc · counter 20→32 |
| **RETRO-V61-053** | `2026-04-24_retro_v61_053_python_parity.md` | incident-retro (R1+R2 CHANGES_REQUIRED on same DEC) | V61-053 cylinder arc · Python version parity + 3-round Codex calibration · introduces `executable_smoke_test` + `solver_stability_on_novel_geometry` risk_flags |
| **RETRO-V61-004** | `2026-04-25_p1_arc_complete_retrospective.md` | P1 phase-close + V61-054 R1 CHANGES_REQUIRED | P1 Metrics & Trust arc V61-054..V61-056 · counter 40→43 |
| **RETRO-V61-005 (W2 gate)** | `2026-04-25_retro_adr_002_w2_gate_arc.md` | incident-retro + phase-close (W2 Foundation-Freeze runtime layer Accepted) | ADR-002 W2 Gate · 3-round arc + same-day Accepted flip |
| **RETRO-V61-006 (W4 prep)** | `2026-04-25_retro_w4_prep_r1_incident.md` | incident-retro (R1 CHANGES_REQUIRED · 3 HIGH silent-runtime-failure) | ADR-002 W4 prep R1 same-day clean-close |
| **RETRO-V61-005 (governance closure)** | `2026-04-26_retro_v61_005_governance_closure_draft.md` | governance-window phase-close | 治理收口 2026-04-26 → 2026-05-03 window |
| **RETRO-V61-006 (Session B)** | `2026-04-26_retro_session_b_arc.md` | Session B v3 P-1 + P-2 close | V61-080..V61-085 + FORENSIC-FLAKE-1 + FORENSIC-FLAKE-1-FIX · GOV-1 enrichment + multi-class authority + citation integrity + test-isolation |
| **RETRO-V61-V107-V108** | `2026-05-02_v61_v107_v108_arc_retrospective.md` | arc-size + repeated under-calibration (V107.5 actual ~10% / V108-A actual ~10%) | V61-107 / V61-107.5 / V61-108-A / V61-108-B arc |

> Note: The 2026-04-25 + 2026-04-26 retros use overlapping `RETRO-V61-005` / `RETRO-V61-006` IDs across different files — the IDs were reassigned during the 治理收口 anchor session per Session-B's audit ratification path. Refer to each file's `retro_id:` / `retrospective_id:` frontmatter for canonical attribution.
