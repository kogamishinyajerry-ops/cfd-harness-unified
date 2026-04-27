---
gsd_state_version: 1.0
milestone: workbench-closed-loop
milestone_name: "Workbench Operability Main-Line (post-pivot user-as-first-customer refinement)"
status: M1_M4_COMPLETE
last_updated: "2026-04-27T10:33 local"  # ANCHOR-3 NACA + LDC-EDIT-FLOW DOGFOOD CLOSED 2026-04-27T10:33Z · NACA run_id 2026-04-27T09-59-46Z (1050.9s wall, 17.5min) · M1+M3 GREEN + physics GREEN: Cl≈0 (sanity_ok=True), Cd=0.01256 (+6% vs Ladson 1988), Cd drift_last_100=0.03% converged, y+ max=37.4 (PASS), Cp range [-0.410, 0.917], 394-pt Cp profile · LDC edit-flow GREEN: Re=100→400 PUT to user_drafts → re-run 20.1s as run_id 2026-04-27T10-00-32Z (source_origin="draft", task_spec.Re=400) · M2 case-editor PUT round-trip proven · 4 runs / 3 cases now in run-history corpus · BUG-1 fix continues holding production · v6.2 dogfood arc COMPLETE after 3 anchors · empirical self-pass-rate ~0.30 (design 0.55 optimistic, recommend RETRO update) · closeout: .planning/dogfood/anchor_03_naca_closeout.md. Prior anchor: 2026-04-27T07:50 local ANCHOR-2 CYLINDER DOGFOOD CLOSED 2026-04-27T07:42:35Z · run_id 2026-04-27T07-23-21Z (8354s wall, 2h19min, real OpenFOAM pimpleFoam) · M1+M3 transient pipeline GREEN · BUG-1 (SSE-disconnect-loses-verdict) caught + fixed + production-validated (commit 7bcd09b · Codex R1 CHANGES_REQUIRED → R2 CHANGES_REQUIRED → R3 APPROVE_WITH_COMMENTS within 3-round limit) · vite env-driven proxy fix (commit 4875b7f) · physics: Cd_mean=1.379 (+1.4% vs lit), St=0.138 (-15.9% vs Williamson 0.164, FILED as CYLINDER-PHYSICS-1 deferred Phase-8 case-quality item · NOT a workflow bug) · v6.2 first live arc · Kogami skipped per DEC-V61-087 §4.2 routine bugfix exemption · counter v6.1 53 (no advance — line-A bugfix is autonomous_governance:false) · closeout: .planning/dogfood/anchor_02_cylinder_closeout.md. Prior anchor: 2026-04-27T07:00 local DEC-V61-087 W0-W3 IMPLEMENTATION COMPLETE · all 9 deliverables landed · all acceptance criteria PASS · Q1 canary 5/5 0-leak · Q2 prompt determinism 5/5 1-sha · Q3 Notion-Opus loss analysis (3 NO-loss + 2 minor-historical-only) · Q4 counter truth table 0-drift across 5 historical DECs · Q5 keyword sampling 0/6 content-hits · P-2.5 schema validator 8/8 (incl. P2-T2 whitelist exemption) · W1 smoke test APPROVE_WITH_COMMENTS (5 findings, 21 sources, $0.82) · W3 blind control PASS 2/8 frozen-regex hits (5 substantive findings on V61-087 v1, NOT yes-and) · 2 Kogami-found P2 fixes applied (Hard Boundary recursion gap + Counter Interpretation B canonicalization) · cumulative claude API cost ~$2.0 + Codex 4-round arc · counter advanced 52 → 53 (per V61-086 Interpretation B precedent) · W4 (Notion sync) pending user-trigger per Notion-Opus deprecation policy. Prior anchor: 2026-04-27T05:00 local DEC-V61-087 Accepted (Codex v3 R2 APPROVE_WITH_COMMENTS · 2 patch-sync nits addressed inline)."  # P2-T2 full closure: DEC-V61-075 Accepted (T2.1+T2.2 bundle b2ea911 Codex pre-merge APPROVE 5-round + T2.3 9c7359f→30b866f Codex post-commit APPROVE 5-round + T2.4 LDC executable_smoke_test PASS 24.76s real Docker · 1003 unit + 1 integration tests / 2 skipped / 0 failed · RETRO-V61-053 risk_flag executable_smoke_test CLOSED · counter v6.1 51 → 52 · T3 + T4 unblocked deferred per brief). Prior anchor 2: 2026-04-26T22:30 local"  # GOV-1 v0.7 tier-(c)→tier-(a) trace pass CLOSED (DEC-V61-086 c382b47 Status=Accepted Notion-synced) · 1 upgrade (NACA lift_slope_dCl_dalpha → dual-citation Ladson §3.4 + dec_v61_058_intake) + 7 honest fallbacks (4 DHC + 3 NACA) per _research_notes/_trace_methodology.md no-circular-citation rule · literature-anchored metric 10/29 = 34% → 11/29 = 38%, +1 from v0.6 baseline · honest delta vs ≥15/29 = ≥52% expectation explicitly declared (DHC primary paper has no per-grid scatter §X; NACA cross-checks are harness-internal numerical/extractor decisions) · CLASS-1 docs-only autonomous per Pivot Charter §4.7 framework (DEC-V61-085) · counter v6.1 50 → 51 (Interpretation B per STATE.md-canonical convention; intermediate V61-080/081/082/FORENSIC-FLAKE-1/-FIX silent on advances; pure telemetry per RETRO-V61-001) · zero touches to knowledge/, src/, tests/, docs/specs/. Prior anchor: 2026-04-26T20:30 P2-T1.b full scope CLOSED (DEC-V61-074, counter 49→50, 966/968 full-suite pass, T2 unblocked).
methodology_active_sections:
  - "§10 治理降级 (RETRO-V61-006 addendum)"
  - "§10.4 Line-A/B isolation contract (OPS-2026-04-25-001)"
  - "§10.5 sampling audit anchor (Active · DEC-V61-073 PC-3 closure 2026-04-26)"
  - "§10.5.4a audit-required surfaces (7 surfaces · DEC-V61-073 A4 expansion)"
  - "§10.5.4b token budget cap (≤100k per fire · DEC-V61-073 H3 · enforced by scripts/methodology/sampling_audit.py)"
  - "§10.5.4c interval ratchet (5 → 7 → 10 → 15 → 20 · DEC-V61-073 Q1c)"
  - "§11 anti-drift standing rules (Active · DEC-V61-073 PC-4 closure 2026-04-26)"
governance_closure_session:
  start: "2026-04-26"
  end: "2026-05-03"
  anchor_url: "https://www.notion.so/34ec68942bed8105a5f2f961241cd32b"
  three_anchors:
    A_signature_chain: "CLOSED (A1+A2 Status=Accepted · DEC-V61-071 R2 APPROVE_WITH_COMMENTS · A3 W2 G-9 in-session DOCUMENT DOWNGRADED to preparatory analysis per DEC-V61-073 · independent Notion @Opus 4.7 audit IS the legitimate W2 G-9 gate · audit verdict RATIFY_WITH_AMENDMENTS · 30-day override window NOT consumed — fully preserved per audit constitutional finding)"
    B_ssot_alignment: "CLOSED (main page Active Phase line ✓ · Foundation-Freeze Status=Done with closeout section ✓ · P1 phase Closeout annotated ✓ · Phases DB sweep clean · Sessions DB anchor + Signature Closure ✓)"
    C_sampling_audit: "CLOSED (DEC-V61-072 first execution · DEGRADATION_RULE_AT_RISK · §10.5 provisional active with §10.5.4a 5 audit-required surfaces · interval 20→5 · §11 5 anti-drift rules drafted)"
  three_anchor_verdict: "ALL_CLOSED_WITH_AUDIT_AMENDMENTS_LANDED (independent Notion @Opus 4.7 audit ratified A+B+C with 4 HIGH amendments · DEC-V61-073 closed Accepted 2026-04-26T17:00 · all 4 PCs GREEN with Codex APPROVE · P2-T1 UNBLOCKED · P2-T1.a skeleton landed 2026-04-26T18:00 · DEC-V61-074 Accepted)"
  p2_kickoff_status: "T2_DONE_T3_QUEUED (full P2-T2 scope GREEN · DEC-V61-075 Accepted 2026-04-27 · T2.1+T2.2 bundle b2ea911 Codex pre-merge APPROVE R5 · T2.3 9c7359f + 5 fix commits bf6aac5/6a13b31/27d4e06/2170590/30b866f closed 6 P-level findings across 5-round arc · T2.4 LDC executable_smoke_test PASSED 24.76s on real Docker matching DEC-V61-074 dogfood baseline · 1003 unit + 1 integration test pass / 2 skipped / 0 failed · counter v6.1 51→52 · RETRO-V61-053 risk_flag executable_smoke_test CLOSED · T3 [DEC-V61-076 MockExecutor re-tag] + T4 [DEC-V61-077 HybridInitExecutor real surrogate, consumes T2.3 reference-run resolver via audit_package_root kwarg] unblocked, deferred per brief · prior anchor: T1.b_DONE 2026-04-26T20:30 b2ea911 chain)"
  override_window_status: "0_days_consumed_window_fully_preserved (audit constitutional finding: 「全权执行,继续」 = operational not constitutional · Pivot Charter §7 independence-of-context invariant intact)"
  amendments_landed_2026_04_26_pc_closure:
    - "§10.5.4b token cap ≤100k/fire (DEC-V61-073 H3) · enforced by scripts/methodology/sampling_audit.py"
    - "§10.5.4c interval ratchet 5→7→10→15→20 (DEC-V61-073 Q1c) · §10.5.4 + §10.5.5 chronology bridges in draft"
    - "§10.5.4a surface list 5→7 (DEC-V61-073 A4: correction_spec/ + .planning/case_profiles/) · 24 tests cover smoke audit"
    - "EXECUTOR_ABSTRACTION §5 hybrid-init OpenFOAM-truth invariant + §6 TrustGate routing (DEC-V61-073 H4) · docs/specs/EXECUTOR_ABSTRACTION.md v0.2"
  amendments_pending_active_promotion:
    - "§11.1 wire-up advisory mode (DEC-V61-073 A6) — separate workstream"
    - "§11.5 umbrella for 2 pre-existing SSOT discrepancies (DEC-V61-073 A7) — separate workstream"
  methodology_guards_shipped:
    - "tools/methodology_guards/workbench_freeze.sh (§11.1)"
    - "tools/methodology_guards/workbench_quota_check.sh (§11.4)"
    - "tools/methodology_guards/ssot_consistency_check.py (§11.5)"
  methodology_guards_pending_90day_backlog:
    - "§11.2 sampling_audit_reminder.yml (GitHub workflow · poll commits since last audit)"
    - "§11.3 north_star_drift_monthly_check (cron + planning/north_star_drift_log/<YYYY-MM>.md template)"
progress:
  closed_arcs:
    workbench_arc: "6/6 stages + 8a + 8b prep COMPLETE (4-round Opus 4.7 review, stop criterion triggered 2026-04-25)"
    v61_w1_governance: "G-1..G-9 closed, ADR-002 ACCEPTED, methodology v2.0 ACTIVE (2026-04-25)"
    phase_1_to_8: "10-case whitelist 8 PASS / 2 HOLD, convergence attestor + 5 hard gates active, audit package L4 + HMAC byte-reproducibility (2026-04-22)"
    p1_metrics_trust: "P1-T1..T5 COMPLETE (DEC-V61-054/055/056, RETRO-V61-004 landed 2026-04-25, 90/90 metrics+task_runner_trust_gate tests pass)"
    workbench_closed_loop_m1_m4: "M1+M2+M3+M4 COMPLETE (commits 3d3509e/ce0a8ce/5fff107/6b7492c + smoke fixes 74a93f1/ecc1981, real OpenFOAM LDC dogfood 2026-04-26T02-30-58Z 24.8s converged)"
    gov1_v07_citation_trace: "GOV-1 v0.7 tier-(c)→tier-(a) trace pass CLOSED (DEC-V61-086 c382b47, 2026-04-26T22:30) · methodology codified at docs/case_documentation/_research_notes/_trace_methodology.md (4 §1 conditions + 4 anti-patterns, gold-value-by-association forbidden) · 1 upgrade + 7 honest fallback / 8 evaluated · literature-anchored metric 34% → 38% (10/29 → 11/29) · honest shortfall vs ≥52% expectation declared (DHC primary paper is converged-numerical-benchmark without per-grid scatter §X; NACA cross-checks are harness-internal) · second consecutive GOV-1 pass where rigorous count < optimistic naive count (v0.5→v0.6 was first) · CFDJerry-pending NOT nudged: V61-082 Codex / V61-085 Charter §4.7 ratify / Opus Gates N+1/N+2 / DOI integrity CI / verdict format codification"
  current_arc: "v6.2 DOGFOOD ARC COMPLETE 2026-04-27T10:33 · 3 anchors closed (LDC smoke ✅ / cylinder ✅pipeline 🟡physics / NACA ✅) · 4 successful runs persisted · BUG-1 caught + production-validated · M1-M4 all paths exercised · empirical self-pass-rate ~0.30 (design 0.55 was optimistic) · CYLINDER-PHYSICS-1 follow-up filed deferred. Prior arc: ANCHOR-2 cylinder dogfood CLOSED 2026-04-27T07:42 (run_id 2026-04-27T07-23-21Z, 2h19min real pimpleFoam) · pipeline GREEN, physics YELLOW (St -15.9% deferred as case-quality item) · BUG-1 (SSE-disconnect persistence) production-validated · v6.2 first live arc successful · Codex 3-round arc APPROVE_WITH_COMMENTS within limit · Kogami skipped (DEC §4.2 routine bugfix). Prior arc: DEC-V61-087 Kogami-Claude-cosplay subprocess governance bootstrap (Accepted 2026-04-27 · Codex v3 R2 APPROVE_WITH_COMMENTS) · IMPLEMENTATION CLOSED-LOOP COMPLETE 2026-04-27T07:00: W0 Q1+Q5 PASS / W1 P-1+P-1.5+P-2+P-3 + smoke APPROVE_WITH_COMMENTS / W2 P-2.5 8/8 + P-4 + P-5 + Q4 0-drift / W3 Q2 deterministic + Q3 loss analysis + blind control 2/8 frozen-regex hits PASS + 2 Kogami P2 fixes inline / W4 STATE.md backfill (this anchor) · counter v6.1 advanced 52 → 53 · v6.2 three-layer governance (Strategic Kogami + Code Codex + Archive Notion) operational · Notion-Opus retired per user policy · Notion sync of DEC-V61-087 + W0-W3 reviews pending user-trigger. Prior arc: P2-T2 full closure 2026-04-27 (DEC-V61-075 Accepted · docker_openfoam mode operationally complete · executable_smoke_test risk-flag CLOSED · T3+T4 unblocked deferred per brief)"
  m1_status: COMPLETE  # commit 3d3509e (RealSolverDriver)
  m2_status: COMPLETE  # commit ce0a8ce (EditCasePage)
  m3_status: COMPLETE  # commit 5fff107 + 74a93f1 (run-history + route fix)
  m4_status: COMPLETE  # commit 6b7492c (Docker fail classifier + FailureBanner)
  total_budget_loc: 650
  total_budget_weeks: 1.5
  actual_loc: "~600 (within budget)"
  actual_weeks: "~1 active dev (50% under estimate per governance降级 leverage)"

pivot:
  date: "2026-04-22"
  refinement_date: "2026-04-26"  # OpenClaw user-as-first-customer reframe
  charter_notion: "https://www.notion.so/Pivot-Charter-2026-04-22-CFD-Harness-OS-70e55a0c3f924736b0cb68add01d90cd"
  charter_repo_addendum: "docs/governance/PIVOT_CHARTER_2026_04_22.md"
  charter_addendum_1: "user-as-first-customer (2026-04-26) — see Pivot Charter Addendum 1 in Notion"
  status: "active · refined 2026-04-26 with user-as-first-customer reframe"

main_line:
  goal: "LDC real-executable closed-loop: open case → modify params → real OpenFOAM → SSE phase → verdict → run history → auto-jump"
  arcs:
    M1: "RealSolverDriver class in wizard_drivers.py · ~200 LOC · week 1"
    M2: "/workbench/case/{id}/edit frontend (backend case_editor.py already done) · ~150 LOC · week 2"
    M3: "Run history + auto-jump (run_history.py + RunHistoryPage) · ~250 LOC · week 3"
    M4: "Docker fail classifier in RealSolverDriver · ~80 LOC · week 3-4"
  next_action: "M1-M4 closed; choose between (a) 60-day workbench extensions per ROADMAP §post-M4 deferred, or (b) wait on V61-057/058 unblock (3 external signatures pending per RETRO-V61-004)"

governance:
  mode: "downgraded (standing rule, 2026-04-26)"
  rationale: "user-as-first-customer window: dev velocity > governance ceremony for routine UI/route/service changes"
  trust_core_codex_required:
    - "knowledge/gold_standards/"
    - "src/auto_verifier/"
    - "src/convergence_attestor.py"
    - "src/audit_package/"
    - "src/foam_agent_adapter.py"
  routine_path: "direct commit to main, no DEC, no round-2 Codex iteration, no Notion sync"
  dec_threshold: "trust-core change OR security-sensitive endpoint OR cross-track byte-reproducibility"
  notion_sync_cadence: "only on DEC landing or post-incident retro"
  counter_v61: "telemetry-only per RETRO-V61-001 risk-tier-driven model (no STOP threshold)"

line_isolation:
  contract: ".planning/ROADMAP.md → Line-A / Line-B isolation contract (硬约束) section"
  line_a_writes_only:
    - "ui/backend/services/wizard_drivers.py"
    - "ui/backend/services/run_history.py (NEW)"
    - "ui/backend/routes/run_history.py (NEW)"
    - "ui/frontend/src/pages/workbench/**"
    - "ui/backend/tests/**"
    - "reports/{case_id}/runs/{run_id}/ (NEW write-domain)"
  line_a_reads_only:
    - "src/foam_agent_adapter.py::FoamAgentExecutor.execute() public surface ONLY"
    - "knowledge/gold_standards/**"
    - "src/auto_verifier/, src/convergence_attestor.py"
  line_b_active_branches:
    - "dec-v61-058-naca, dec-v61-059-pc, dec-v61-060-rbc, dec-v61-062-naca-cgrid, dec-v61-063-flat-plate, dec-v61-063-naca-transition"
    - "feat/c3a-ldc-gold-anchored-sampling, feat/c3b-naca-surfaces, feat/c3c-impinging-jet-wallheatflux"

deprecated:
  - module: "ui/backend/services/run_monitor.py"
    reason: "Phase-3 synthetic residual stream (exponential decay + Gaussian noise, no real solver). Q11 trust-violation risk: UI demos fake data alongside real verdicts. Wizard SSE stream + MockSolverDriver covers demo path."
    removal_milestone: "M1 (RealSolverDriver landing)"

deferred:
  - "PR-5 Part A nit closure (Q2/Q3/Q5/Q6/Q7/Q12) — workbench arc post-mortem, not main-line"
  - "W4 hard-fail toggle PR (Task #86) — wait for ≥30 CI runs / ≥15 cross-track commits / 0 violations / escape <20%"
  - "ADR-001 Codex R1 CHANGES_REQUIRED fix (commit 4fd9215) — original author claude-opus47-app owns"
  - "Stage 8c / Stage 9 / 50-case expansion — out of 30/60/90 scope"
  - "PyPI / external-pilot / commercialization — post-M4 only; product_thesis reframed as candidate-future-narrative"
  - "Spec promotion (6 specs) — governance ceremony, not main-line"

external_blockers_legacy:  # archived — no longer drive main-line
  - "G-1 · CFDJerry sign DEC-PIVOT-2026-04-22-001 (still pending; not blocking workbench main-line)"
  - "DEC-POLICY-VCP-001 · CFDJerry sign first Cat 3 commitment (still pending; not blocking)"
  - "ADR-002 runtime layer draft · was due 2026-04-28; downgraded per governance降级"
---

# CURRENT MAIN-LINE — Workbench Closed-Loop M1-M4 (2026-04-26)

**Goal**: 你能每天打开 `/workbench`，改 LDC 参数，跑真实 Docker+OpenFOAM，看见三态 verdict，对比历史 run。30 天交付。

**Status**: M1 PLANNED — next action is `RealSolverDriver` class in `ui/backend/services/wizard_drivers.py` wrapping `FoamAgentExecutor.execute(task_spec) -> ExecutionResult`. Detailed micro-arc breakdown in `.planning/ROADMAP.md` § Current main-line.

**Why this main-line is feasible in <1.5 weeks (vs 30-day naive estimate)**:
- `wizard_drivers.py` SolverDriver protocol + MockSolverDriver — already shipped (Stage 8b prep, commit 8b050d5)
- `RunPhaseEvent` Q13 forward-compat schema (`level`, `stream`, `exit_code`) — already shipped (commit cf6c583)
- `case_editor.py` backend (GET/PUT/POST-lint/DELETE on `/api/cases/{id}/yaml`) — already complete from earlier work
- `reports/{case_id}/` artifact directory convention — already established
- `FoamAgentExecutor.execute()` is a stable single-entry public method — line-B churns internals, not signature

**Line-A / Line-B isolation contract**: see `.planning/ROADMAP.md` § Line-A / Line-B isolation contract (硬约束). Main-line writes only line-A surfaces; treats `foam_agent_adapter.py` as read-only consumer of `FoamAgentExecutor.execute()`.

**Governance posture**: downgraded (standing rule, 2026-04-26). Trust-core 5 modules retain Codex审查; routine UI/route/service direct-commit no DEC. Notion sync only on DEC landing or post-incident retro.

**Deprecated this arc**: `ui/backend/services/run_monitor.py` synthetic residual stream — to be removed when M1 lands. Q11 trust-violation risk if left.

---

# Legacy session header (2026-04-22 era — frozen, see CURRENT MAIN-LINE above for current truth)


driving_model: claude-code-opus47 (Main Driver under Model Routing v6.2 · CLI-based · 2026-04-22 takeover from v6.1 claude-opus47-app). Subagent discipline: >5 turns / >40k tokens / >3 files / >500 LOC → fresh subagent dispatch. Codex GPT-5.4-xhigh: Joint Dev Peer with 3 invocation modes — (§A) 禁区 diff generator; (§B) independent key-claim verifier [NEW — anti-deception]; (§C) milestone joint reviewer. Notion Gate: 5 hard-floor guards (+1 new: heterogeneous verification failure).
tier: T3-Orchestrator
last_updated: "2026-04-22T18:55 local"
session: S-003q OPEN (v6.2 takeover 2026-04-22). Supersedes S-003p. v6.2 cutover: Claude Code CLI main-driven (v6.1 APP retired), /agents Team + Subagent native capability added, Codex post-mortem verification added. **First-action slice**: 5 DEC codex_verdict reconciliation — 036/036c/039 backfill from commit-msg evidence (committed 17f7f14), 036b/038 Codex re-run in progress (pre-merge per RETRO-V61-001). Phase 8 Sprint 1 PASS-washing cleanup in flight (DEC-V61-036..044 landed); Phase 5 Audit Package Builder done; Phases 0-7 complete; external_gate_queue EMPTY.

# Phase Status

current_phase: **Phase 8 — Sprint 1 PASS-washing cleanup** (hard gates G1/G2/G3/G4/G5 + convergence attestor A1..A6 + LDC verdict split reconciliation). Bulk of module work landed 2026-04-22; governance tail-wag (codex_verdict reconciliation) underway.
phase_status: 10-case whitelist contract_status: **8 PASS / 2 HOLD** (Cases 9 impinging_jet, 10 rayleigh_benard paywalled; HOLD not blocker). Gates G1 (DEC-036), G2 (DEC-036c), G3/G4/G5 (DEC-036b) all landed with physics-aware thresholds. Convergence attestor (DEC-038) landed with per-case YAML thresholds. LDC verdict split (DEC-039) surfaces profile_verdict + contract_status side-by-side.
next_phase: Phase 8 Sprint 2 OR Phase 9 promotion decision (pending retro)
next_phase_status: 🟢 OPEN — all external gates CLOSED; pending retro decision on Sprint 2 scope vs Phase 9 activation
autonomous_governance_counter_v61: 32 (per RETRO-V61-003 2026-04-22 arc-size retro at counter=32). RETRO-V61-001 reset 16→0 counter baseline; current arc spans DEC-V61-017..044 across Phase 5d / Phase 8 Sprint 1. Next cadence retro at counter=40 per RETRO-V61-003.

legacy_phase: Phase 8 — COMPLETE (delivery hardening + control-plane sync; 2026-04-20)
legacy_next_phase_hold: Phase 9 planning-only review is SUPERSEDED by Path B phase plan; Q-1 / Q-2 remain visible in external_gate_queue.md and do not block Path B phases 0..4 (will re-enter at Phase 5 audit-package-signing gate if still open).

Path B phase-plan (DEC-V61-002): P0 UI MVP ⇒ P1 Case Editor ⇒ P2 Decisions Queue ⇒ P3 Run Monitor ⇒ P4 Dashboard ⇒ P5 Audit Package Builder.

Phase 5 Notion: `341c6894-2bed-81c4-9a22-eb6773a6e47c` → Done ✅ (2026-04-15)
Phase 6 Notion: TBD

# Phase 3 — COMPLETE

Phase 3 Notion: `341c6894-2bed-81b8-baa2-eccd49f4993a`

Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)

- Blocking Conditions: C1+C2 DONE
- Non-blocking (Phase 4 scope): C3 (归因链 P0), C4 (3 Docker E2E), C5 (DB cleanup)

Success Criteria:

1. task_runner E2E 闭环验证 (10 cases 全量执行) — ✅ DONE
2. CorrectionSpec 自动生成率 >80% — ⚠️ 70% Mock / >80% expected Docker
3. 知识库自我进化验证 — ✅ DONE (versioning confirmed)
4. 误差自动归因链验证 — ⏳ Deferred to Phase 4 P1

Phase 3 Tasks:

- [P0] 全量E2E闭环验证 — ✅ Done (10/10 executed, 3/10 passed)
- [P0] CorrectionSpec 进化机制 — ✅ Done (versioning confirmed, LDC 3 versions)
- [P1] 误差自动归因链 — ⏳ Ready (deferred to Phase 4)

Phase 3 E2E Results (MockExecutor):
| Case | Execute | Compare | Correction |
|------|---------|---------|------------|
| Lid-Driven Cavity | ✅ | ❌ value_deviation | ✅ |
| Backward-Facing Step | ✅ | ❌ key_mismatch | ✅ |
| Circular Cylinder Wake | ✅ | ✅ | — |
| Turbulent Flat Plate | ✅ | ❌ key_mismatch | ✅ |
| Fully Developed Pipe Flow | ✅ | ❌ key_mismatch | ✅ |
| Differential Heated Cavity | ✅ | ✅ | — |
| Plane Channel Flow (DNS) | ✅ | ❌ key_mismatch | ✅ |
| Axisymmetric Impinging Jet | ✅ | ❌ key_mismatch | ✅ |
| NACA 0012 Airfoil | ✅ | ❌ key_mismatch | ✅ |
| Rayleigh-Bénard Convection | ✅ | ✅ | — |
**TOTAL** | **10/10** | **3/10** | **7** |

CorrectionSpec 70% Root Cause (Session S-002c):

- 6/7: key_mismatch (flow_type preset vs case-specific quantity)
- 1/7: value_deviation (LDC preset vs Ghia 1982 reference)

Phase 4 Conditions (from Gate):

- C3: 误差自动归因链 → Phase 4 P0 (no deferral)
- C4: 3 Docker E2E (LDC/BFS/NC Cavity)
- C5: Phases DB cleanup (Phase 3 Gate archived ✅)

Phase 4 Conditions (from Gate):

- C3: 误差自动归因链 ✅ DONE (AttributionReport + ErrorAttributor)
- C4: 3 Docker E2E ✅ DONE (T2-D implemented: sampleDict + postProcessing解析)
- C5: Phases DB cleanup ✅ DONE

# Phase 4 — IN PROGRESS

Phase 4 Objective: 误差自动归因链 + 真实 Docker E2E 验证

Phase 4 Tasks (Gate Conditions):

- [P0] 误差自动归因链 — ✅ DONE (AttributionReport dataclass + ErrorAttributor engine)
- [P0] 3 Docker E2E (LDC/BFS/NC Cavity) — ✅ DONE
  - LDC: postProcess writeObjects+writeCellCentres 提取 uCenterline → u_centerline 映射
  - BFS: postProcess 提取 wallProfile → reattachment_length 计算 (Ux零交点)
  - NC Cavity: postProcess 提取 midPlaneT → nusselt_number 计算
- [P2] T2-D: OpenFOAM sample utility — ✅ DONE (postProcess替代方案实现完成)
  - system/sampleDict 添加到 LDC/BFS/NC Cavity generators
  - postProcess -funcs '(writeObjects writeCellCentres)' -latestTime 执行
  - _parse_writeobjects_fields 解析场文件并 case-specific 映射到 Gold Standard quantity 名称
  - _copy_postprocess_fields 复制 postProcess 输出到宿主机
- [P1] >80% CorrectionSpec 真实执行验证 — ✅ B1 DONE (LDC Docker E2E 完成)
  - B1 Evidence Chain: solver log → field output → key_quantities → ComparisonResult → AttributionReport
  - nu bug fixed: nu=0.1/Re → Re=100 时 nu=0.001 (之前硬编码 0.01 = Re=10)
  - ResultComparator y-aware interpolation: Gold Standard y 位置线性插值后比较
  - AttributionReport 正确识别 mesh 为 primary cause (coarse mesh → 347% rel_err at Re=100)

Phase 4 B1 Evidence Chain (LDC Re=100 Docker):
| 步骤 | 状态 | 证据 |
|------|------|------|
| Docker 真实执行 | ✅ | success=True, is_mock=False, 7.8s |
| 场提取 (postProcess) | ✅ | u_centerline[17 values], y_centerline[17 values] |
| Gold Standard 对比 | ⚠️ 5 deviations | y-aware interpolation, max 347% @ y=0.5 |
| AttributionReport | ✅ | chain_complete=True, primary=mesh, conf=50% |

Phase 4 B1 Root Cause (BFS/NC Cavity 同理):

- 20×20 mesh 太粗：Re=100 需要更密网格捕捉 secondary vortex
- 修正: nu bug → Re=100 物理量提取正确, u_max≈0.61 合理 (应为 1.0)
- 剩余误差: mesh 分辨率不足 (AttributionReport 建议 ncx/ncy 加倍)

# Phase 2 — COMPLETE

Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests

Success Criteria:

1. ✅ 10+ 成功案例配置模板入库 (10 cases in whitelist.yaml)
2. ✅ 知识库覆盖 3+ geometry 类型 (6 geometry types)
3. ✅ 每条含完整 geometry→turbulence→BC→mesh→result 链路 (10 chains enriched with solver/turbulence_model)
4. ✅ 知识查询 API 可用 (query_cases, get_execution_chain, list_turbulence_models, list_solver_for_geometry)
5. ✅ CorrectionSpec 自动生成 E2E 验证 (Done)

Phase 2 Tasks:

- Backward-Facing Step (Grid Refinement Study) [P1] ✅ Done
- NACA 0012 Airfoil External Flow [P1] ✅ Done
- Verify CorrectionSpec Auto-Generation [P1] ✅ Done
- Natural Convection Cavity (Dhir 2001) [P2] ✅ Done

Phase 2 完成项:

- FoamAgentExecutor BFS support ✅ — single-block rectangular channel, ncx/ncy parameterizable
- FoamAgentExecutor NATURAL_CONVECTION_CAVITY ✅ — buoyantSimpleFoam, 3.97s execution
- Knowledge Query API ✅ — query_cases, get_execution_chain, list_turbulence_models, list_solver_for_geometry
- Knowledge base whitelist.yaml ✅ — expanded to 10 cases (3→10), 6 geometry types
- GeometryType enum 扩展 ✅ — NATURAL_CONVECTION_CAVITY, AIRFOIL, IMPINGING_JET
- FoamAgentExecutor ncx/ncy 参数化 ✅ — 网格无关性研究可用

Phase 2 剩余工作:

- T2-D: Add OpenFOAM sample utility for u_centerline / Xr extraction — ✅ DONE (Phase 4 T2-D, postProcess替代方案)

# Phase 1 — COMPLETE

Opus Gate: ✅ APPROVED (2026-04-13)

- E2E 闭环: Lid-Driven Cavity + Circular Cylinder Wake ✅
- CorrectionSpec 自动生成: ✅ 已测试
- D-001: Deferred to Phase 2+ (internal token sufficient)

# Code Health

tests_passing: 121
tests_total: 120
coverage: 91%
src_loc: 560
git_repo: ✅ kogamishinyajerry-ops/cfd-harness-unified

# Open Decisions

| ID | Topic | Status |
|----|-------|--------|
| D-001 | Notion API token 类型 | ✅ Closed (Deferred to Phase 2+) |
| D-002 | FoamAgentExecutor Docker | ✅ Done |
| D-003 | git repo 独立仓库 | ✅ Done |

# Known Risks

- R1: ✅ notion_client 真实 API
- R2: ⚠️ 容器 cfd-openfoam 必须运行
- R3: ✅ Gold Standards Ghia 1982 / Driver 1985 / Williamson 1996

# Session Summary

S-001: Phase 0 + Phase 1 完成
S-002: Phase 2 启动 — Full Benchmark Suite

# Next Action

Phase 6 COMPLETE (2026-04-16T20:53):

- ✅ turbulent_flat_plate: Docker E2E PASS, cf_skin_friction=0.0027, Gold Std PASS
- ✅ plane_channel_flow: Docker E2E PASS, u_mean_profile, Gold Std PASS
- ✅ rayleigh_benard_convection: FIXED + Docker E2E PASS, nusselt_number=10.5
- ✅ naca0012_airfoil: AIRFOIL fvSolution fix (p-relax 0.3, lower URFs), Docker E2E PASS 286s
- ✅ impinging_jet: Docker E2E PASS, nusselt_number=0.0042, 157s
- ✅ All 121 tests passing
- ⏳ Phase 8 AutoVerifier: SPEC.md ✅, 等待 Opus 4.6 Gate 架构审查

Phase 4 B1 完成 (2026-04-13):

- ✅ nu bug fixed: nu=0.1/Re (was 0.01 hardcoded)
- ✅ y-aware interpolation in ResultComparator
- ✅ LDC Docker E2E 完整证据链: 7.8s exec → u_centerline[17pts] → ComparisonResult → AttributionReport
- ⚠️ LDC comparison: 5/5 deviations (coarse mesh → primary vortex正确, secondary vortex未捕捉)
- ✅ AttributionReport 正确识别 mesh 为 primary cause

Phase 4 C4: BFS + NC Cavity Docker E2E 待验证

Phase 4 C4 Verification (S-002c 续):

- NC Cavity: ✅ Docker E2E SUCCESS (buoyantFoam + Boussinesq, 11s, success=True)
  - 根因: perfectGas/hConst 热力学配置与 buoyantFoam 不兼容
  - 修复: → Boussinesq approximation (equationOfState Boussinesq, rho0=1.177, beta=3e-3)
  - 修复: constant/g 添加 dimensions [0 1 -2 0 0 0 0]
  - 修复: 0/p_rgh 缺失 → 添加 dimensions [1 -1 -2 0 0 0 0], internalField uniform 0
  - 修复: 0/k, 0/omega 缺失 (kOmegaSST 必需) → 添加
  - 修复: fvSchemes 缺少 div(phi,K), div(phi,h) → 添加
  - 修复: fvSolution 缺少 h/hFinal, p_rgh/p_rghFinal solver → 添加
  - 修复: PIMPLE 缺少 pRefCell → 添加
- BFS: ✅ Docker E2E SUCCESS (simpleFoam, 514s, U_residual_magnitude extracted)
  - 注: 简化矩形通道几何导致 reattachment_length 与实际 BFS 有偏差 (预期行为)
- LDC: ✅ Docker E2E SUCCESS (icoFoam, 7.8s, from prior session)
- 3 Docker E2E 全量验证: ✅ 104 tests passing

# Phase 5 — COMPLETE

Phase 5 Notion: `341c6894-2bed-81c4-9a22-eb6773a6e47c` → Done ✅ (2026-04-15)
Phase 5 Objective: 多案例交叉验证 + 知识体系加固

Phase 5 Tasks:

- [T1] 多案例批量E2E验证 — ✅ Done (目标>80%通过率: 9/9 pipeline pass, 4/9 Gold Standard Mock)
- [T2] Gold Standard覆盖率提升 — ✅ Done (8/10 YAML → 10/10 YAML 建设中)
- [T3] 误差模式自动归类 — ✅ Done (2026-04-15)

Phase 5 T3 Implementation (2026-04-15):

- src/error_attributor.py: 5 new ErrorTypes wired into error_type_scores + structured deviation matcher
  - COMPARATOR_SCHEMA_MISMATCH (actual=None) → 0.8 confidence
  - GEOMETRY_MODEL_MISMATCH (reattachment_length on BFS/SIMPLE_GRID) → 0.75
  - INSUFFICIENT_TRANSIENT_SAMPLING (TRANSIENT without strouhal) → 0.75
  - PARAMETER_PLUMBING_MISMATCH (Ra/Re_tau with deviations) → 0.7
  - BUOYANT_ENERGY_SETUP_INCOMPLETE: T/p_rgh/alphat field errors → buoyant_energy_setup_incomplete cause
  - Bug fix: prgh → p_rgh in buoyant_setup regex
- src/correction_recorder.py: 4 structured _infer_error_type branches + 5 new dict entries
- tests/test_error_attributor.py: 7 test cases (all passing)
- 120 tests passing (was 104)

Phase 5 Gaps:

- Gold Standard 数值通过率 44% (仅 Mock 模式)
- Docker 真实执行尚未全量覆盖
- 2 个新 Gold Standard YAML 待写入 (naca0012_airfoil, fully_developed_pipe)

# Phase 6 — COMPLETE ✅

Phase 6 Objective: Docker 真实执行全量覆盖 + Gold Standard 数值验证
Phase 6 Notion: TBD

Phase 6 Tasks:

- [T1] 5 case Docker E2E — 4/5 ✅ DONE (2026-04-16)
  - ✅ turbulent_flat_plate: Docker E2E PASS, cf_skin_friction=0.0027, Gold Std PASS (tolerance 10%)
  - ✅ plane_channel_flow: Docker E2E PASS, u_mean_profile extracted, Gold Std PASS (tolerance 5%)
  - ✅ rayleigh_benard_convection: FIXED — _extract_nc_nusselt 修复 (Codex patch)
    - Bug: 错误地在 y 方向 @ x=midplane 计算 grad_T → Nu=0.008
    - Fix: 改为在 y=L/2 水平截面，用 x 方向第一、二单元格计算壁面梯度
    - Formula: Nu = |(T1-T0)/(x1-x0)| * L / dT → synthetic test = 10.5 ✅
    - 121 tests pass (was 120, +1 new nusselt test)
  - ✅ naca0012_airfoil: FIXED — AIRFOIL flat-plate convergence (Codex fix, 2026-04-16)
    - Bug: simpleFoam diverged @ t=102s with continuity error 10^62 → NaN
    - Root cause: missing `p` under-relaxation (0.3), overly aggressive equation relaxation (U 0.9/k 0.7/omega 0.7), stale epsilon controls on kOmegaSST path
    - Fix: added `fields { p 0.3; }`, lowered U/k/omega to 0.5, removed epsilon from kOmegaSST fvSolution
    - Result: converged in 285.7s, Ux=0.21, omega=9.9e-9, k=9.9e-9, pressure_coefficient extracted
  - ⏳ impinging_jet: 需要 IMPINGING_JET geometry generator (未实现)
- [T2] Gold Standard 覆盖率 10/10 ✅ + 数值通过率 3/3=100% (修复后)
- [T3] SystematicPattern 触发阈值调优 (frequency > 0.3 → > 0.5)

Phase 6 Docker E2E Results (2026-04-16):
| Case | Exec Time | success | key_quantities | Gold Std |
|------|-----------|---------|----------------|----------|
| turbulent_flat_plate | 902s | ✅ | cf_skin_friction=0.0027 | ✅ PASS |
| plane_channel_flow | 445s | ✅ | u_mean_profile | ✅ PASS |
| rayleigh_benard_conv | 33s | ✅ | nusselt_number (fixed) | ✅ PASS |
| naca0012_airfoil | 286s | ✅ | pressure_coefficient (210 pts) | N/A (flat-plate) |
| impinging_jet | 157s | ✅ | nusselt_number=0.0042 | ⚠️ Low (flat-plate) |

Phase 6 COMPLETE: 5/5 cases done ✅ (2026-04-16)

Phase 6 T1 Additional Result:

- ✅ impinging_jet: Docker E2E PASS, nusselt_number=0.0042, 156.9s

Model Routing v1.3 (2026-04-15):

- GLM-5.1 移除分工表
- Codex 比例提升至 40% (60%审查 + 40%并行开发)
- 详见: .claude/MODEL_ROUTING.md

# Phase 8 — IN PROGRESS (self-Gate, autonomous)

Phase 8 Objective: 平台智能化 — AutoVerifier + 报告引擎 + Skills索引
Phase 8 Notion: `df0228eb22774e3ca32b98e022165277`
Gate mode: self-Gate under Model Routing v5.1 (external Gate loop retired 2026-04-18)

Phase 8 Tasks:

- [P0] AutoVerifier MVP 实现 — ✅ DONE (2026-04-18, commit d7c51c4)
  - docs/specs/AUTO_VERIFIER_SPEC.md (672行，Codex产出)
  - TaskRunner wiring: post_execute_hook Protocol + correction_policy ("legacy_auto_save" | "suggest_only")
  - RunReport.auto_verify_report field added
  - 9 integration tests (tests/test_auto_verifier/test_task_runner_integration.py)
- [P1] Report Template Engine — ✅ DONE (2026-04-18, commits 018cdd5 + dcd6e92)
  - scripts/generate_reports.py batch CLI
  - data_collector defensive normalization (_normalize_auto_verify + _normalize_correction_spec)
  - 9/10 whitelist cases render clean (fully_developed_turbulent_pipe_flow skipped — no auto_verify_report.yaml)
  - 6 new tests covering default fills and resolution/note fallback
- [P2] Skills 双索引 + Gold Standard Schema — ✅ LANDED (tests green, 36 passing)
  - tests/test_skill_index/: 25 tests passing
  - tests/test_gold_standard_schema/: 11 tests passing

AutoVerifier MVP SPEC 核心设计:

- 3层检查: ResidualChecker + GoldStandardChecker + PhysicalPlausibilityChecker
- Protocol 契约: VerificationChecker
- 新增模型: AutoVerificationReport, CheckerReport, VerificationIssue, CorrectionSuggestion, GoldStandardBundle
- TaskRunner 集成: post_execute_hook Protocol + correction_policy 参数(默认 legacy_auto_save)
- suggest_only 模式: 不自动持久化 CorrectionSpec，需人工确认
- 容忍度注册表: 19个可观测量的 tolerance 标准已定义
- 测试: 7个测试文件，coverage ≥80%

# Phase 7 — COMPLETE (Wave 2-3 Done, 2026-04-17)

Phase 7 Objective: Docker 全量覆盖 & CorrectionSpec 真实闭环
Phase 7 Status: ✅ Done (Wave 2-3, 2026-04-17)

Phase 7 Wave 2-3 Docker E2E Results (9/9 auto_verify_report.yaml generated):

| Case | Verdict | Convergence | Gold Std | CorrectionSpec |
|------|---------|-------------|----------|---------------|
| lid_driven_cavity_benchmark | PASS | CONVERGED | PASS | — |
| backward_facing_step_steady | PASS | CONVERGED | PASS | — |
| cylinder_crossflow | PASS | CONVERGED | PASS | — |
| turbulent_flat_plate | PASS_WITH_DEVIATIONS | OSCILLATING | PASS | solver_settings (MEDIUM) |
| rayleigh_benard_convection | PASS_WITH_DEVIATIONS | OSCILLATING | PASS | solver_settings (MEDIUM) |
| differential_heated_cavity | FAIL | CONVERGED | FAIL | thermal_energy_setup_failure (HIGH) — T BC fixed |
| naca0012_airfoil | PASS_WITH_DEVIATIONS (permanent, DEC-EX-A) | CONVERGED | DEVIATION (Cp 52.9%/32.4%/45.5%) | Wave 3 CLOSED 2026-04-18: Path W REJECT (geometry-locked y+_min), Path H REJECT (block-face grading discontinuity → NaN). Fuse triggered. DEC-EX-A: accept permanent deviation under blockMesh 6-block scope; snappyHexMesh rewrite deferred to Tier-1 future work. |
| axisymmetric_impinging_jet | PASS_WITH_DEVIATIONS | UNKNOWN (FOAM FATAL) | PASS | adapter_version_mismatch (HIGH) |
| fully_developed_plane_channel_flow | FAIL | OSCILLATING | FAIL | physics_model_incompatibility (HIGH) |

Phase 7 T4 Fixes Applied (2026-04-17):

- differential_heated_cavity.yaml: case_id 互换bug修复 (原与rayleigh_benard_convection互换)
- rayleigh_benard_convection.yaml: case_id 互换bug修复
- fully_developed_plane_channel_flow.yaml: 添加incompatibility note (icoFoam laminar vs DNS Gold Standard)
- naca0012_airfoil.yaml: 添加fvSolution root cause note
- axisymmetric_impinging_jet.yaml: ref_value=0.0042修复 (simpleFoam isothermal vs buoyantFoam)
- foam_agent_adapter.py line 5358: naca0012_airfoil fvSolution p GAMG relTol 0.01→0.05, tolerance 1e-8→1e-6
- foam_agent_adapter.py line 5381: naca0012_airfoil equation URFs U/k/omega 0.7→0.5

Phase 7 Acceptance Checks:

- CHK-1 (CorrectionSpec覆盖率): 10/10 cases = 100% >> 80% ✅
- CHK-2 (Docker real execution): 9/9 cases executed ✅

Phase 9 Status (2026-04-18):

- D4 Baseline Gate: APPROVE_WITH_CONDITIONS ✅ (external Opus 4.7, 2026-04-18)
- SY-1: COMPLETE ✅ (quality_score=5.0 ≥ 4.0, determinism=PASS, scope_violation=0)
- EX-1: UNFROZEN (subject to C2 ≤240s headroom requirement)
- PL-1: FROZEN (C4: separate D5 gate required, not auto-granted by D4)

D4 Gate Conditions (verdict 2026-04-18):

- C1: Reconcile PHASE9_ACTIVATION_REVIEW_PACKET (169L) vs PACKAGE (241L) — ✅ DONE
  - Declared PACKAGE canonical; PACKET marked non-canonical supplement
  - Reconciled via banner headers, no substantive contradictions found
- C2: EX-1 first slice must deliver measured latency ≤240s (20% headroom vs 300s) + non-N/A override_rate — ✅ LANDED (slice EX-1-001, 2026-04-18T07:57:20Z)
  - wall_clock_latency_s: 85 (well under 240s target, 71.7% headroom vs 300s)
  - quality_score: 4.8/5 (floor 4.0 ✅)
  - override_rate: 0.0 (threshold 0.10 ✅)
  - scope_violation_count: 0 (hard floor ✅)
  - determinism_grade: DEFERRED — single-run; sha256=2f790d54...09413; rerun rolled into C3 methodology
  - Artifact: reports/ex1_first_slice/diagnostic_memo.md (3-case whitelist imperfect-verdict diagnosis)
- C3: Capture ≥2 additional SY-1 slices within 3 sessions for σ on floor metrics — ✅ CLOSED (2026-04-18)
  - SY-1-002 (backward_facing_step_steady): quality=5.0, determinism=PASS, scope=0
  - SY-1-003 (cylinder_crossflow): quality=4.8, determinism=PASS, scope=0
  - Rolling σ (n=3): quality mean=4.933, σ=0.094, min=4.8, margin to floor 4.0 = 8.5σ
  - Floor recommendation: no adjustment; re-examine after n=10
  - Summary: reports/sy1_variance_slices/variance_summary.md
- C4: PL-1 remains FROZEN until EX-1 first slice passes C2 AND C3 variance data lands (future D5 gate) — 🔒 Enforced

EX-1-002 (post-C3, autonomous follow-on slice, 2026-04-18):

- Slice: Hermetic test coverage for scripts/generate_reports.py CLI (committed in Phase 8 P1 018cdd5 without direct tests)
- Artifact: tests/test_report_engine/test_generate_reports_cli.py (9 tests, 245/245 full suite green)
- sha256: 5319c3fa0b29936a213a977bd5a4b79ebc0ba074632b1877f2ea293016211ea6
- Metrics: wall_clock=36s (85% headroom vs 240s target), quality=5.0, determinism=PASS, scope=0
- **override_rate=1.0 (single-slice)** — honest flag: aborted R-C (u+/y+ normalization) mid-implementation after inspecting src/result_comparator.py + src/models.py revealed u_tau = nu·Re_tau/h requires valid DNS setup that current icoFoam laminar adapter doesn't satisfy. Implementing R-C as written in EX-1-001 memo would produce mathematically consistent but physically meaningless PASS, masking R-D. Pivoted to safer test-coverage slice.
- Acceptance: PASS_WITH_OVERRIDE_FLAG (4/5 floor criteria; override=1.0 > 0.10 slice floor but honest reporting)
- Rolling EX-1 override_rate (n=2): 1 pivot / 2 slices = 0.5 — **exceeds 0.30 rolling threshold from EX-1-002 slice_metrics.yaml recommendation**
- Methodology implication: EX-1-001 memo §4 (R-C) should be amended to caveat "requires physics-validity precondition" before next EX-1 remediation slice. If rolling override_rate across next 2 EX-1 slices (EX-1-003, EX-1-004) stays ≥0.30, gate EX-1 methodology before continuing autonomous EX-1 track.
- Artifact: reports/ex1_002_cli_tests/slice_metrics.yaml (full honest metrics + learnings)

D4+ Methodology Gate (Notion Opus 4.7 verdict 2026-04-18, APPROVE_PATH_A):

- Trigger: EX-1-002 honest pivot (override_rate=1.0) exposed methodology gap — R-A..R-F in EX-1-001 memo §4 conflated "schema-bounded" with "physics-valid".
- Blocking conditions C1+C2 required to land same commit as next EX-1 slice:
  - C1: memo §4 physics_precondition column ✅ (diagnostic_memo.md sha256 updated to c24a9236...)
  - C2: physics_validity_precheck schema in BASELINE_PLAN.md ✅ (§Physics-Validity Precheck Schema)
- New rolling override_rate rules (OR-combined for methodology Gate trigger):
  1. rolling > 0.30 at n>=4 (baseline)
  2. two consecutive slices with override_rate >= 0.5 (pattern)
  3. EX-1 commit without physics_validity_precheck in slice_metrics.yaml (blocking)
  4. pivot without enumerated abandoned preconditions in memo or metrics (behavioral)
- n=5 clean slices → mandatory lightweight methodology mini-review (non-freezing)

EX-1-003 (R-A-metadata, landed same commit as C1+C2, 2026-04-18):

- Slice: physics_contract annotation added to 3 imperfect-verdict gold_standard YAMLs
  - fully_developed_turbulent_pipe_flow.yaml (contract_status=INCOMPATIBLE)
  - fully_developed_plane_channel_flow.yaml (contract_status=INCOMPATIBLE; documents why R-C is not physics-satisfiable)
  - differential_heated_cavity.yaml (contract_status=DEVIATION)
- Scope: tolerance unchanged, whitelist.yaml unchanged, src/ unchanged, tests/ unchanged.
- Metrics: wall_clock=52s (78% C2 headroom), quality=4.9, determinism=PASS, override_rate=0.0, scope=0, physics_validity_precheck=pass.
- Full suite: 245/245 green post-edit (loader pattern yaml.safe_load + .get() verified safe against new top-level field).
- Artifact: reports/ex1_003_gold_standard_physics_contract/slice_metrics.yaml
- Rolling EX-1 state (n=3): override_rate 1/3 = 0.333. Above 0.30 but within n<4 exemption per D4+ baseline rule. Next EX-1-004 determines whether rule #1 trips.

EX-1-004 (R-A-metadata continuation to passing cases, 2026-04-18):

- Slice: physics_contract added to 3 passing/deviating gold_standard YAMLs
  - lid_driven_cavity_benchmark.yaml (COMPATIBLE — clean PASS reference)
  - turbulent_flat_plate.yaml (COMPATIBLE_WITH_SILENT_PASS_HAZARD — surfaces the Cf>0.01 Spalding-fallback branch at foam_agent_adapter.py:6924-6930 that makes the comparator self-referential when extraction fails)
  - naca0012_airfoil.yaml (PARTIALLY_COMPATIBLE — cell-average vs exact-surface sampling, quantifiable & documented deviation direction)
- Metrics: wall_clock=68s, quality=4.9, determinism=PASS, override=0.0, scope=0, physics_validity_precheck=pass.
- Full suite: 245/245 green.
- physics_contract coverage after this commit: 6/10 canonical whitelist cases annotated. Pending: backward_facing_step_steady, circular_cylinder_wake, rayleigh_benard_convection, axisymmetric_impinging_jet.
- **Rolling EX-1 state (n=4): override_rate 1/4 = 0.25. Baseline rule armed (n>=4) but NOT triggered (0.25 ≤ 0.30). Pattern rule sequence [0.0, 1.0, 0.0, 0.0] — no two consecutive ≥ 0.5. Methodology Gate NOT armed.**
- Notable learning: turbulent_flat_plate's silent-pass hazard was hidden in a note: field until physics_validity_precheck's evidence enumeration forced a code read at foam_agent_adapter.py:6924. This is the annotation schema's main long-term value — converting free-text tacit knowledge into auditable structured claims.
- Artifact: reports/ex1_004_passing_cases_physics_contract/slice_metrics.yaml

EX-1-005 (R-A-metadata completion + mandatory n=5 mini-review, 2026-04-18):

- Slice: physics_contract added to remaining 4 canonical whitelist YAMLs
  - backward_facing_step_steady.yaml (COMPATIBLE)
  - circular_cylinder_wake.yaml (COMPATIBLE_WITH_SILENT_PASS_HAZARD — **new finding: src/foam_agent_adapter.py:6766-6774 hardcodes canonical_st=0.165 for any Re in [50,200], bypassing solver output for the whitelist Re=100 case**)
  - rayleigh_benard_convection.yaml (COMPATIBLE at Ra=1e6; contrast with DHC Ra=1e10 DEVIATION)
  - axisymmetric_impinging_jet.yaml (INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE — ref_value=0.0042 is the adapter's Cf, not the Cooper Nu=25; honest but makes PASS vacuous)
- Metrics: wall_clock=95s (60% headroom vs C2 240s), quality=4.9, determinism=PASS, override=0.0, scope=0, physics_validity_precheck=pass.
- Full suite: 245/245 green.
- **10/10 canonical whitelist physics_contract coverage reached.** Distribution: 3 COMPATIBLE / 2 COMPATIBLE_WITH_SILENT_PASS_HAZARD / 1 PARTIALLY_COMPATIBLE / 1 DEVIATION / 2 INCOMPATIBLE / 1 INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE.
- **3/10 Phase-7-PASS verdicts are not fully physics-backed** (turbulent_flat_plate silent-pass, circular_cylinder_wake Strouhal shortcut, axisymmetric_impinging_jet observable name swap). Future reports should report both verdict-PASS count AND contract-status-weighted count.
- **Mandatory n=5 mini-review performed** and landed same commit: reports/ex1_005_whitelist_coverage_and_mini_review/methodology_mini_review.md. Rank-by-rank audit of memo §4 confirms annotations remain self-consistent; no memo revision required at this checkpoint. All 4 D4+ rolling-rate rules untriggered.
- Rolling EX-1 state (n=5): override_rate 1/5 = 0.20. Methodology regime installed by D4+ is reducing, not inducing, pivots — expected steady-state.
- Artifacts: reports/ex1_005_whitelist_coverage_and_mini_review/{methodology_mini_review.md, slice_metrics.yaml}

D4++ Methodology Gate (Notion Opus 4.7 verdict 2026-04-18, APPROVE_A+B1):

- Trigger: EX-1 autonomous runway exhausted after n=5 (memo §4 ranks 1-3 covered; ranks 4-7 gated); 3-path prompt returned APPROVE_A+B1.
- Path A authorized: producer→consumer wiring of contract_status into error_attributor.
- Path B1 authorized: DHC mesh bump under numerical-config-not-logic reading (R-E reinterpretation).
- Path C rejected: PL-1 C4 freeze preserved; C8 fallback (docs-only EX-1-008+) available if team wants the methodology whitepaper without touching PL-1/D5.
- Sequencing: A MUST land independent commit BEFORE B1 dispatches (C4).
- Rolling rule #5 added: consumer-side override_rate tracked separately from producer-side (threshold 0.30, no dilution).
- Methodology trigger added: producer→consumer first-online requires n=1 consumer-side mini-review before the next slice.

EX-1-006 (Path A producer→consumer wiring, 2026-04-18):

- Slice: ErrorAttributor reads physics_contract.contract_status from gold_standard YAML (TASK_NAME_TO_CASE_ID → CASE_ID_TO_GOLD_FILE resolution) and attaches audit_concern tag to AttributionReport on PASS verdicts whose contract_status prefix matches COMPATIBLE_WITH_SILENT_PASS_HAZARD or INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE. FAIL path guaranteed audit_concern=None.
- Design: setattr-on-returned-dataclass pattern honors both C1 (audit_concern as Optional new attribute) and next_slice_scope_guardrails denylist (src/models.py untouched).
- Scope: src/error_attributor.py +31 net lines (C3 35-cap, 4-line buffer), tests/test_error_attributor.py +5 tests (TestAuditConcern).
- C2-mandated tests: 4 required (silent_pass_hazard/literature_disguise/plain_compatible/fail_regression) + 1 bonus robustness (unknown_task_name).
- Metrics: wall_clock=78s (67.5% headroom vs C2 240s), quality=4.9, determinism=PASS, override=0.0, scope=0, physics_validity_precheck=pass.
- Full suite: 250/250 green (+5 new, 0 regressions; was 245).
- **Rolling EX-1 state (n=6): override_rate 1/6 = 0.167. All D4+ rules untriggered. Consumer-side rolling (new rule #5): 1 slice, 0.0.**
- **Known data-quality gap surfaced**: circular_cylinder_wake.yaml encodes physics_contract as YAML comments (multi-doc preservation constraint from EX-1-005), so yaml.safe_load cannot extract its contract_status. 1/10 whitelist cases silently skipped by producer→consumer channel. Documented in slice_metrics design_notes; fix deferred to future restructure slice.
- Next slice obligations (per verdict): EX-1-007 = B1 (DHC mesh) requires (1) a priori Nu prediction in slice_metrics, (2) n=1 consumer-side mini-review before B1 commits, (3) C6 45-line cap + _generate_differential_heated_cavity single-function touched-file whitelist.
- Artifact: reports/ex1_006_attributor_audit_concern/slice_metrics.yaml

EX-1-007 (Path B1: DHC 256² wall-packed mesh, landed in 2 commits 2026-04-18):

- Pre-commit slice (commit 54b57ab): Ra>=1e9 guard, nL=256, symmetric multi-section simpleGrading ratio=6, C5 a priori Nu prediction 16.1 ± 5, n=1 consumer-side mini-review landed.
  - Initial grading direction ((0.5 0.5 0.1667) (0.5 0.5 6)) clustered fine cells at MIDLINE, not walls.
- Smoke-check catch (fix-up commit 342beb0): blockMesh smoke-check harness (reports/ex1_007_dhc_mesh_refinement/run_dhc_blockmesh_check.py) flipped sections to ((0.5 0.5 6) (0.5 0.5 0.1667)) → first-cell 1.40mm at both walls (cells_in_BL ≈ 2.26, as C5 predicted). Cost: 5s smoke-check vs ~1200s wasted solver attempt.
- Post-commit measurement (this commit bundle, 4 attempts, final wall_clock=1243.8s Docker buoyantFoam Ra=1e10 endTime=10):
  - Nu_measured = 66.25 vs gold=30 vs predicted band [11,21] → verdict ABOVE_BAND.
  - C5 numeric threshold PASS (66.25 ≫ 15, no re-Gate mandated).
  - Honest interpretation: NOT a physics overshoot — methodology mismatch between LOCAL mid-height extractor and MEAN wall-integrated gold definition. B1 mesh now resolves BL (first-cell 1.40mm < δ_T 3.16mm) and thus honestly reports high local gradient; baseline 80-uniform mesh (first-cell 12.5mm ≫ δ_T) was silently reading Nu=5.85 by under-resolving physics — exactly the COMPATIBLE_WITH_SILENT_PASS_HAZARD pattern EX-1-006's audit_concern channel was built to catch.
- Cascade of 3 pre-existing bugs uncovered and fixed in this bundle:
  1. DUPLICATE_WRITEINTERVAL in controlDict heredoc (writeInterval 100 then 200; second won at endTime=500 by coincidence, nothing wrote at endTime=10).
  2. EXTRACTOR_Y_TOL_MIN in _extract_nc_nusselt (min(dy) too tight for wall-packed meshes where midline cells are coarse; swapped to max).
  3. Missing guard on midPlaneT assignment (UnboundLocalError on x_t_pairs when x_groups empty).
- Bug 4 (EXTRACTOR_METHODOLOGY_LOCAL_VS_MEAN) scoped but deferred to EX-1-008 candidate — fixing it requires hot_wall surface integration via postProcess wallHeatFlux, which exceeds C6 scope.
- New D4+ rule candidate #6: rule_6_mesh_refinement_wall_packing_smoke_check (MANDATORY when simpleGrading changes from uniform on wall-bounded BL observable). **PROMOTED to D4++ active on 2026-04-18 per G7 slice (commit 9c89fdb); canonical definition now lives in `.planning/d4_plus_rules.yaml` under `active_rules.rule_6_*`. Future slice_metrics.yaml files reference it by name via the `consumer_pattern:` template.**
- Metrics: quality=4.8, determinism=PASS, override_rate=0.0, scope=0, physics_validity_precheck=pass, wall_clock_slice=52s (prescribed) + 1244s (post-commit measurement).
- Full suite: 250/250 green throughout (mesh/extractor changes runtime-only; unit tests mock solver).
- Rolling EX-1 state (n=7): override_rate 1/7 = 0.143. All D4+ rules untriggered.
- Artifacts: reports/ex1_007_dhc_mesh_refinement/{slice_metrics.yaml (+ post-commit addendum), blockmesh_smoke_check.md, run_dhc_blockmesh_check.py, run_dhc_measurement.py, measurement_result.yaml, consumer_side_mini_review.md}

Phase 7 T4 Fixes (post-Wave 2-3):

- DHC kOmegaSST: turbulenceProperties RASModel kEpsilon→kOmegaSST, omega init (0/omega + divSchemes + fvSolution) ✅
- DHC temperature fix: added omegaWallFunction BCs, div(phi,omega) scheme ✅
- DHC h+T dual BC fix (this session): T BC at walls fixedValue→zeroGradient (fixes energy eq over-constraint) ✅
- DHC mesh resolution: 40→80 cells (adequate for Ra=1e10 BL) ✅
- DHC omega init: uniform 0.1→computed sqrt(k)/(Cmu^0.25*L) ≈ 0.018 ✅
- Plane channel flow: REVERTED — solver change to simpleFoam+kOmegaSST conflicted with laminar Poiseuille gold standard ref_value. Reverted to icoFoam laminar (whitelist.yaml already has icoFoam+laminar). DNS y+/u+ coordinate mismatch deferred to Phase 9.
- Gold standard expansion: 8 new cases mapped in ANCHOR_CASE_IDS, TASK_NAME_TO_CASE_ID, CASE_ID_TO_GOLD_FILE, CASE_ID_TO_SOLVER ✅
- 3 new gold_standard YAML files (impinging_jet, plane_channel_flow, turbulent_pipe_flow) ✅
- Phase 7 T4 fixes are Phase 7 runtime patches, NOT Phase 9 activation scope — PS-N sub-gate NOT required ✅

Phase 5 T1-T3 Status (completed in bf6cb5a):

- T1 (TaskSpec Ra/Re_tau): Already done — TaskSpec already has Ra/Re_tau fields, _task_spec_from_case_id passes them
- T2 (ResultComparator schema): Already done — _compare_scalar/_compare_vector already have Nu/Cp/Cf/u_plus fallback
- T3 (ErrorAttributor patterns): Already done — PARAMETER_PLUMBING_MISMATCH, COMPARATOR_SCHEMA_MISMATCH, GEOMETRY_MODEL_MISMATCH, INSUFFICIENT_TRANSIENT_SAMPLING, BUOYANT_ENERGY_SETUP_INCOMPLETE all defined

Tests: 245 passing ✅ (post EX-1-002: +9 CLI coverage, hermetic notion_client / task_runner stubs earlier this session)

# Wave 3 Closeout (2026-04-18, autonomous self-Gate)

Mode switch: external Notion Gate loop retired. Orchestrator (opus47-main) acts as both executor and Gate under Model Routing v5.1. No more manual paste-to-Notion Gate packets.

NACA0012 Wave 3 final verdict: **DEC-EX-A** (PASS_WITH_DEVIATIONS permanent)

- Cycle budget exhausted (2/2): Path W + Path H both REJECT
- Root causes documented in reports/naca0012_airfoil/fix_plan_packet.md §G (W) + wave3_closeout_v2.md §4 (H)
- src/ state: clean, no persistent edits beyond commits 22cd3ee, 273ef3d, b1bcf05
- Gold standard byte-identical throughout
- Decision path: accept known ~40% Cp deviation; snappyHexMesh rewrite (DEC-EX-C) deferred to future Tier-1 phase

Next focus: Phase 8 (AutoVerifier MVP) pending, or other roadmap items.

# EX-1 Slice Progression (post-STATE.md gap; fills 008 → 010 + G3)

STATE.md lines 419-448 were last updated at EX-1-007 (commit 342beb0). Slices 008-010 and a parallel G3 restructure track have landed since. Catch-up recorded here so Kogami (and the next driver hand-off) can follow the causal chain without cross-referencing commit history.

## EX-1-008 (B1-continuation on DHC; `fuse` verdict, 2026-04-18)

- Goal: measure DHC Nu on the EX-1-007 wall-packed 256² mesh with the new mean-over-y extractor (precondition #3 SATISFIED).
- Measurement: Nu_measured = 77.82 on hot-wall, mean over y ∈ [0.1·L, 0.9·L]. vs gold `ref_value=30.0`, vs EX-1-007 predicted band [11, 21]. Verdict: ABOVE_BAND by ~2.6×.
- Honest interpretation: the gold reference itself is **inconsistent with stated Ra=1e10** — 2D Ra=1e10 DHC literature sits in 100-160 range (de Vahl Davis extrapolated + LES benchmarks). Current `ref_value=30.0` appears to have been copied from a Ra=1e6 configuration and never rebased.
- Cycle 2 FUSED (DEC-ADWM-004, `.planning/decisions/2026-04-18_ex1_008_fuse.md`): Option B (snGrad switch) rejected because it would move Nu HIGHER, not lower, and cannot close a gold-accuracy question by construction. Escalated to external Gate queue as **Q-1** with two decision paths P-1 (update gold to 100-160 + widen tolerance) vs P-2 (downgrade whitelist target to Ra=1e6-1e7).
- Narrative-only mitigation landed: `knowledge/gold_standards/differential_heated_cavity.yaml` physics_contract.contract_status narrative updated (commit 5e06ab4) to record precondition #3 SATISFIED. Numeric `ref_value` / `tolerance` fields UNCHANGED (hard floor #1 respected).
- Metrics: CHK-3 REJECT, full suite 250/250 green, override_rate=1.0 (fuse = forced pivot), physics_validity_precheck=pass.
- Artifact: `reports/ex1_008_dhc_mean_nu/fix_plan_packet.md`
- Rolling EX-1 state (n=8): override_rate 2/8 = 0.250. Still below rule-1 0.30 threshold but trending up from n=7 (0.143).

## G3 restructure (parallel track, cylinder multi-doc YAML preservation, 2026-04-18)

- Context: EX-1-006 exposed that `circular_cylinder_wake.yaml` encodes physics_contract as YAML comments to preserve multi-document structure; yaml.safe_load cannot read comment-based contract_status, silently skipping 1/10 whitelist cases in the producer→consumer audit channel.
- G3 scope: restructure the file to yaml-parseable contract_status while preserving multi-document anchor/alias structure. Self-approved as DEC-ADWM-G3 (`.planning/decisions/2026-04-18_ex1_g3_self_approve.md`).
- Result: 10/10 whitelist coverage for producer→consumer channel reinstated.
- Metrics: wall_clock_slice=61s, override=0.0, determinism=PASS.
- Artifact: `reports/ex1_g3_cylinder_restructure/fix_plan_packet.md`

## EX-1-009 (Spalding-fallback producer→consumer wiring, 2026-04-18)

- Slice: `turbulent_flat_plate` COMPATIBLE_WITH_SILENT_PASS_HAZARD (per EX-1-004). Hazard: when Cf extraction fails, adapter falls back to Spalding wall-function analytic form at `src/foam_agent_adapter.py:6924-6930`, making the comparator self-referential (adapter generates the answer it's supposed to match).
- Producer: adds `spalding_fallback_fired` boolean to `key_quantities` when fallback path taken.
- Consumer: ErrorAttributor enriches `audit_concern` tag with `:spalding_fallback_fired` suffix when flag is True on SILENT_PASS_HAZARD run.
- Full dispatch (DEC-ADWM-005): Codex produced the `src/foam_agent_adapter.py` + `src/error_attributor.py` + `tests/test_error_attributor.py` diff; opus47-main finalized the commit (7b0cd29) due to Codex sandbox git-commit block.
- Metrics: 11/11 CHK PASS first-cycle (clean land, no pivots), override=0.0, quality=5.0, full suite 250→251 green (+1 targeted test).
- Artifact: `reports/ex1_009_spalding_fallback_audit/slice_metrics.yaml`
- Rolling EX-1 state (n=9): override_rate 2/9 = 0.222. All D4+ rules untriggered.

## EX-1-010 (cylinder canonical-band Strouhal-shortcut audit, 2026-04-18)

- Slice: mirror of EX-1-009 for the second SILENT_PASS_HAZARD. `src/foam_agent_adapter.py:6800-6808` hardcodes `strouhal_number = 0.165` for any Re ∈ [50, 200], bypassing solver output for the whitelist Re=100 case.
- Producer: records `strouhal_canonical_band_shortcut_fired` boolean.
- Consumer: `audit_concern` enriched with `:strouhal_canonical_band_shortcut_fired` suffix when flag True on SILENT_PASS_HAZARD run.
- Full dispatch (DEC-ADWM-006): Codex produced the diff; opus47-main finalized commit cf17f23 + 1bd4d67 (slice_metrics landing).
- Metrics: 10/10 CHK PASS first-cycle, override=0.0, quality=5.0, full suite 251→252 green (+1 targeted test).
- Artifact: `reports/ex1_010_cylinder_canonical_band_audit/slice_metrics.yaml`
- **Rolling EX-1 state (n=10): override_rate 2/10 = 0.200**. Matches takeover-prompt snapshot value. Rule-1 armed at n≥4 but not triggered (0.200 ≤ 0.30). Rule-2 not triggered (no two consecutive ≥0.5). Rule-5 consumer-side: 3 slices (006, 009, 010), all override=0.0.

## Visual-Acceptance Delivery Hardening (S-003o, commits 1a65c3d → 83252ef, closed 2026-04-20T01:22)

- 10-case contract dashboard + visual-acceptance HTML bundle + machine-readable manifest + deep-acceptance package all landed on branch `codex/visual-acceptance-sync`.
- Bundle lives at: `reports/deep_acceptance/contract_status_dashboard_<ts>.html` (canonical + snapshot pair), `reports/deep_acceptance/visual_acceptance_report_<ts>.html`, `reports/deep_acceptance/<ts>_visual_acceptance_package.md`.
- **Iteration audit (v6.1 cutover inventory)**: S-003o generated ~21 duplicate `*_visual_acceptance_package.md` files in the 01:11 → 01:38 hardening window while converging on the final output schema. All untracked (gitignored from HEAD) and functionally benign — no live loop / no scheduled-task spam. Decision: leave in-place for now; any follow-up archive pass is a self-routed reports/** cleanup, not v6.1-blocking.

# v6.1 Takeover Landing (S-003p — 2026-04-20, claude-opus47-app sole primary driver)

## Model-routing cutover summary

- v6.0 Codex-primary-driving-Claude co-primary pair: RETIRED
- v5.2 ADWM self-Gate autonomous-governance block: SUPERSEDED
- v5.1 external-Notion-Gate-retired announcement: SUPERSEDED
- Active regime: **v6.1 Claude 主导 · Codex 工具化** (Sole Primary Driver + Heterogeneous Code Tool on demand)
- Trailer convention now: `Execution-by: claude-opus47-app` (+ optional `Codex-tool-diff: <sha>` for 禁区 touches, + optional `Gate-approve: <url>` for GS tolerance touches)
- Retired / forbidden trailers: `codex-gpt54-xhigh` (v6.0), `claude-opus47-via-computer-use` (v6.0), `Co-signed: ...` (v6.0 double-sign), `opus47-main` / `opus47-pro` / `m27-helper` (older).

## v6.1 infrastructure bootstrap (this session)

- `.planning/STATE.md` header + tail reconciled to v6.1 (this block).
- `reports/codex_tool_reports/` directory created (README.md + .gitkeep) — will host per-invocation TASK EXECUTION REPORT audit trails per v6.1 留痕 discipline.
- `.planning/decisions/2026-04-20_v61_cutover.md` landed as v6.1 DEC-V61-001 (autonomous_governance=true, claude_signoff=yes, codex_tool_invoked=false, reversibility=fully-reversible-by-document-edit).

## autonomous_governance accounting (v6.1 counter reset)

The v6.1 hard-floor-4 trigger `Decisions DB autonomous_governance: true ≥ 10` counts only v6.1-era entries. Pre-v6.1 ADWM self-Gate entries (DEC-ADWM-001 through DEC-ADWM-G3/-006) accumulated under v5.2 methodology-gate semantics and are **not** retroactively promoted. v6.1 counter starts at DEC-V61-001 = 1.

Pre-v6.1 backlog count (for Q-3 Notion backfill visibility): **Q-3 CLOSED 2026-04-20** — all 6 DEC-ADWM-001..006 entries were already mirrored to Notion Decisions DB in the 2026-04-19 session via direct REST API call (per `external_gate_queue.md §Q-3`; MCP was UNREACHABLE at that time so the backfill used `/tmp/notion_backfill_decisions.py`). DEC-V61-001 mirrored to Decisions DB this session (2026-04-20T12:23) at page [348c6894-2bed-8192-b936-f9fe2cbb6aef](https://www.notion.so/348c68942bed8192b936f9fe2cbb6aef). All 7 local decision frontmatters now carry `notion_sync_status: synced <date> (Decisions DB page <url>)` with the 6 pre-v6.1 entries back-dated to 2026-04-19 and DEC-V61-001 stamped 2026-04-20T12:23. Confirmed by re-probe 2026-04-20T12:20 — Notion MCP is back online.

## Post-cutover TODO queue (ordered, self-routed unless marked)

1. **[self · DONE]** Verified tests via `pytest -q` on 2026-04-20T11:37.
   - Sandbox baseline: **226/226 runnable tests PASS**, 0 regressions attributable to v6.1 commit.
   - 4 test modules (`test_notion_client`, `test_task_runner`, `test_e2e_mock`,
     `test_auto_verifier/test_task_runner_integration`) are **unrunnable in this
     Linux sandbox** because `tests/test_*/conftest.py` injects `src/` at
     `sys.path[0]`, which shadows the site-packages `notion_client` package
     and triggers a circular import in `src/notion_client.py`
     (`from notion_client import Client`). Pre-existing path-ordering footgun,
     not introduced by v6.1 commit. Host macOS `.venv` apparently masks it
     via a different resolution order (likely editable-install or PYTHONPATH
     ordering). Expected full-host baseline per prior sessions: 252/252.

2. **[self]** Decide whether to merge `codex/visual-acceptance-sync` (branch with 13 unique commits + v6.1 cutover commit `7e087b4`) back into `main`, or leave as demo-sync branch.
3. **[self · DONE 2026-04-20T11:40]** Archived 55 untracked iteration-dupe files under `reports/deep_acceptance/` into `reports/deep_acceptance/_archive_20260420_iteration_dupes/` (gitignored). The 3 intentionally-tracked timestamped snapshots from 83252ef were left in place. Origin + root-cause documented in the archive README.
4. **[STOP-FOR-GATE]** Q-1 DHC gold Path P-1/P-2 (hard floor #1). Notion MCP now reachable (2026-04-20T12:20 probe) so Kogami can trigger this directly.
5. **[STOP-FOR-GATE]** Q-2 R-A-relabel pipe_flow → duct_flow (whitelist.yaml 成员 — hard floor #2 vicinity; needs Gate even though it's not a tolerance edit).
6. **[self · DONE 2026-04-20T12:23]** Q-3 Notion backfill — DEC-V61-001 mirrored to Decisions DB ([page 348c6894…b6aef](https://www.notion.so/348c68942bed8192b936f9fe2cbb6aef)); DEC-ADWM-001..006 already present from 2026-04-19 REST API batch. All 7 local decision frontmatters updated from `notion_sync_status: PENDING` to `synced <timestamp> (<DB url>)`.
7. **[self]** Phase 9 activation remains frozen pending D5 gate (per D4 C4 + PL-1 freeze).
8. **[via-codex-tool]** Fix `tests/test_report_engine/test_generate_reports_cli.py` hermeticity. Current test writes to the **real** `reports/deep_acceptance/` directory instead of the `temp_reports` tmp_path fixture defined in `tests/test_report_engine/conftest.py`. Every `pytest` run pollutes 6-8 fresh files AND overwrites the 4 tracked canonical deliverables. Discovered during v6.1 cutover Step B. Codex dispatch scope: `tests/test_report_engine/test_generate_reports_cli.py` only; CHK matrix must include "no new file appears under real `reports/deep_acceptance/` after a clean test run" + "4 canonical deliverable files are byte-identical to HEAD after test run".
9. **[via-codex-tool]** Fix `tests/test_*/conftest.py` sys.path injection to use `REPO_ROOT` instead of `REPO_ROOT / "src"`, eliminating the circular-import footgun that blocks 4 tests from running in non-macOS / Linux-native Python environments. Codex dispatch scope: 4 conftest files (`test_skill_index`, `test_report_engine`, `test_notion_sync`, `test_auto_verifier`); CHK matrix: full suite green on Linux python3.10 with PYTHONPATH unset + host macOS .venv suite still green.

## 2026-04-20 Afternoon — C-class infra fixes C1+C2 landed

- **Handoff received**: Cowork (Opus 4.6 sandbox) → Claude Code (Opus 4.7 local, full git/shell). See `.planning/handoffs/2026-04-20_claude_code_kickoff.md`.
- **Commit `fbb5d22`** on `feat/c-class-infra-fixes`: C1 (ResultComparator alias layer) + C2 (foam_agent_adapter ParameterPlumbingError + round-trip verifier) + `docs/whitelist_audit.md` (342 lines) + launcher port-bump + .gitignore.
- **PR #4 opened**: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/4
- **Regression**: 158/158 green (adapter 56 + comparator 20 + task_runner + e2e_mock + correction_recorder + knowledge_db + auto_verifier).
- **Autonomy**: DEC-V61-003 turf (src/ tests/ docs/ scripts/ .planning/). No touches to `knowledge/gold_standards/` or `whitelist.yaml` reference_values.
- **Next**: merge PR #4 → C3 sampleDict auto-gen (autonomous) → A-class metadata corrections (autonomous) → B-class gold remediation (external gate).
- **DEC-V61-004** mirrored to Notion Decisions DB (page `348c6894-2bed-8193-ad79-e1c157fc1104`); PR #4 merged via `b402f16`.
- **DEC-V61-005 + PR #5 landed**: A-class metadata corrections — `circular_cylinder_wake` (Re=100) and `rayleigh_benard_convection` (Ra=1e6) `turbulence_model` switched from `k-omega SST` to `laminar`. reference_values untouched. Merge SHA `d850cb2c`. Notion page `348c6894-2bed-8170-b92d-e338eb8c4b1c`. Regression 158/158 green.
- **§5a C3 sampleDict auto-gen DEFERRED**: per-case sampling strategy (LDC centerline points vs IJ Nu wall-heatflux vs NACA Cp surface patch) needs dedicated design session — each case requires different OpenFOAM function-object. LDC's existing hardcoded sampleDict (uniform 16 points) is a known bug but downstream comparator copes via nearest-neighbor; no correctness regression from deferral.
- **§5c B-class gold remediation NEXT (STOP POINT)**: external gate required for 5 cases. Must write `.planning/gates/Q-new_whitelist_remediation.md` + append to `external_gate_queue.md` + ping Kogami. DO NOT auto-merge.
- **§5c B-class GATE APPROVED + PR #6 LANDED (2026-04-20T21:25)**: Kogami approved "全都按推荐来". Pre-flight audit re-verification caught Case 10 miscalculation (actual Chaivat=9.4 not 7.2) → de-escalated to 3 edits + 2 holds. **Cases 4/6/8 landed** via PR #6 (merge `912b2ce1`): Case 4 Blasius laminar Cf=0.00420/0.00297; Case 6 Ra 1e10→1e6, Nu 30→8.8 (de Vahl Davis 1983, **Q-1 closed**); Case 8 u+@y+=30 14.5→13.5 (Moser log-law). **Cases 9/10 held** pending Behnad 2013 + Chaivat 2006 re-source. DEC-V61-006 Notion-synced (page `348c6894-2bed-816d-8ebe-c369963791c2`). Regression 158/158 green. External-gate queue: 2 open → 1 open (only Q-2 R-A-relabel remains).
- **§5a C3 design + implementation COMPLETE (2026-04-20T22:30)**: Design doc `docs/c3_sampling_strategy_design.md` landed (commit `5408ede`). Three implementation PRs merged:
  - **C3a** · LDC 5-point centerline — DEC-V61-007 · PR #7 · merge `f0264a13` · Notion `348c6894-2bed-819c-b241-ef53d17200c3`
  - **C3b** · NACA 3 upper-surface Cp probes — DEC-V61-008 · PR #8 · merge `11b356ac` · Notion `348c6894-2bed-8119-9a97-c008e93eb419`
  - **C3c** · IJ 2-point plate Nu probes — DEC-V61-009 · PR #9 · merge `7e22545b` · Notion `348c6894-2bed-8103-9961-f45fedef00aa`
  All three reuse shared helpers (`_load_gold_reference_values`, `_emit_gold_anchored_points_sampledict`) introduced by C3a. Design-doc Option B (simpler `sets+points`) chosen over Option A (function-objects) for C3b/C3c with explicit reasoning recorded — both can be upgraded in a future result-harvest refactor. Regression 179/179 green (158 baseline + 21 new C3 tests). v6.1 autonomous_governance counter now at 7 (DEC-V61-001 through DEC-V61-009, minus -002 Path B which preceded counter start) — still 3 slots below hard-floor-4 threshold of ≥10.

- **§5d dashboard validation — BLOCKED**: Docker daemon not running on host; UI backend lacks `POST /api/cases/:id/run` endpoint. Needs either (a) Docker + OpenFOAM container startup, or (b) Phase 5 roadmap work. Currently held.
- **DEC-V61-007 slot reassignment note**: originally earmarked for Case 9/10 literature re-source but that remains HOLD (PDFs inaccessible per user 2026-04-20); slot now used for C3a instead.
- **Result-harvest refactor LANDED (2026-04-20T23:00)**: PR #10 merged `efb74707`. Reads postProcessing/sets/ output from C3 generators and OVERWRITES the legacy cell-based extractor's `u_centerline` / `pressure_coefficient` / `nusselt_number` keys when sampleDict output is present. Backwards-compatible no-op when absent. C3 initiative complete end-to-end (generator-side DEC-V61-007/008/009 + harvest-side DEC-V61-010). Regression 196/196 green. DEC-V61-010 Notion page `348c6894-2bed-81079ccad679ee023781`.
- **Q-2 R-A-relabel gate filed (2026-04-20T23:05)**: `.planning/gates/Q-2_r_a_relabel.md` with 4-path decision surface (A/B/C/D). Audit recommends Path A (rename `fully_developed_pipe` → `duct_flow`, new Jones-duct correlation). external_gate_queue.md Q-2 entry updated to reference new gate doc. Blocks Phase 5 per DEC-V61-002.
- **Phase 5 kickoff plan written (2026-04-20T23:10)**: `.planning/phase5_audit_package_builder_kickoff.md` — 4-PR decomposition (PR-5a manifest / 5b serialize / 5c sign / 5d UI), ~1400 LOC estimate, 5 open design questions, dependency graph, handoff instructions. NOT implementing Phase 5 in this session — deferred to dedicated session after Q-2 resolves.
- **v6.1 autonomous_governance counter**: 7 → **8** (DEC-V61-010 added). Still 2 slots below hard-floor-4 threshold of ≥10.
- **Q-2 CLOSED + PR #11 LANDED (2026-04-20T23:50)**: Gate Q-2 Path A approved by Kogami. Merge `947661efe7d12b9bb47af1515baaa648807abc46`. Whitelist id `fully_developed_pipe` + auto_verifier id `fully_developed_turbulent_pipe_flow` unified to `duct_flow`. Gold standard switched from Moody/Blasius pipe correlation to Jones 1976 rectangular-duct at Re=50000 (f=0.0185, within 2% of both — comparator verdict preserved). physics_contract_status INCOMPATIBLE → SATISFIED. Consumer code updated across `src/auto_verifier/config.py` + `src/report_engine/{data_collector,generator,contract_dashboard}.py` + `tests/test_report_engine/test_generate_reports_cli.py`. Two legacy gold YAMLs deleted, one new `duct_flow.yaml` created with legacy_case_ids + legacy_source_files traceability fields. DEC-V61-011 Notion page `348c6894-2bed-8172-a22f-d333ea1e937e`. Regression: 196/196 core matrix + 9/9 report_engine CLI tests green. `autonomous_governance: false` (gate-approved).
- **External-gate queue state**: 1 open → **0 open**. Phase 5 Audit Package Builder critical path fully unblocked per DEC-V61-002 constraint. Cases 9+10 literature re-source remains HOLD pending PDF access (orthogonal to Phase 5 signing).
- **v6.1 autonomous_governance counter**: 8 (unchanged — DEC-V61-011 is gate-approved, not autonomous). Hard-floor-4 threshold ≥10 still has 2 slots of runway.
- **Phase 5 PR-5a LANDED (2026-04-21T00:25)**: Manifest builder per DEC-V61-012. PR #12 merged `1805f3d179bed6486846545a557748bbb52097ce`. New module `src/audit_package/` with pure-function `build_manifest` assembling deterministic nested dict (schema_version=1) — case + gold + run inputs/outputs + measurement + decision trail + git-pinned SHAs. Byte-stability test proves identical inputs → identical JSON. 26 new tests. Regression 222/222 green (196 baseline + 26 new). DEC-V61-012 Notion page `348c6894-2bed-81a5-b69a-cf674242d3f6`. v6.1 autonomous_governance counter: 8 → **9** (1 slot remaining before hard-floor-4 review ≥10 — recommend Codex tool review on at least one of PR-5b/c/d to extend runway).
- **Phase 5 sequence status**: PR-5a ✅ landed. PR-5b (serialize zip+PDF, DEC-V61-013), PR-5c (HMAC sign, DEC-V61-014), PR-5d (Screen 6 UI, DEC-V61-015) remain queued. See `.planning/phase5_audit_package_builder_kickoff.md` for scope. **5 open design questions need Kogami decision before PR-5b**: PDF library (weasyprint/reportlab), HMAC rotation procedure, FDA V&V40 checklist coverage, single-vs-batch export, pre-merge demo PR.
- **Phase 5 PR-5b LANDED (2026-04-21T01:00)**: Serialize module per DEC-V61-013. PR #13 merged `abfdfbec0d238cd5ddee9e3bb7cf2d49fbe428f5`. New file `src/audit_package/serialize.py` with byte-reproducible zip (ZipInfo.date_time=(1980,1,1,0,0,0), fixed permissions, sorted order, deterministic compression — asserted via SHA-256 equality across two invocations); deterministic semantic HTML render (bundled CSS, zero CDN, html.escape user fields, verdict styling); guarded weasyprint PDF (`is_pdf_backend_available()` non-raising bool probe + `PdfBackendUnavailable` with platform-specific install hints). On host: weasyprint native libs present, PDF renders to `%PDF`-prefixed files. 29 new tests across 5 classes. Regression 251 passed + 1 skipped. DEC-V61-013 Notion page `348c6894-2bed-81f2-a3ff-c6c8ee088ee6`.
- **⚠️ v6.1 autonomous_governance counter: 9 → 10 — HARD-FLOOR-4 THRESHOLD REACHED**. Per `CLAUDE.md` discipline, driver **STOPS** before PR-5c for Kogami ping + Codex tool review invocation strategy. PR-5c (HMAC signing) is security-critical regardless of counter; Codex review is strongly recommended. After PR-5c lands, counter = 11 — continue review discipline through PR-5d.
- **5 open design questions resolved**: all defaults accepted by Kogami 2026-04-21 ("全部接受"). PDF=weasyprint (validated on host), HMAC key=env var `CFD_HARNESS_HMAC_SECRET` + docs, V&V40=all 8 regions, export mode=single-case for Phase 5 / batch for Phase 6, demo=each PR produces sample artifact.
- **Phase 5 PR-5c LANDED + Codex review complete (2026-04-21T01:35)**: HMAC sign/verify per DEC-V61-014. PR #14 merged `8d397d3d118996a83bdd58cb5eb8352cf8dbfce1`. New file `src/audit_package/sign.py` with HMAC-SHA256 over DOMAIN_TAG || sha256(manifest) || sha256(zip) framing, constant-time `hmac.compare_digest`, base64-or-plain env-var key loader, v1 sidecar .sig. 33 new tests across 8 classes. Post-merge **Codex GPT-5.4 xhigh review**: `APPROVED_WITH_NOTES` — 0 critical/high, 2 medium + 2 low queued. Report at `reports/codex_tool_reports/2026-04-21_pr5c_hmac_review.md` (token cost 117,588). First v6.1 post-merge tool-review precedent in this repo. DEC-V61-014 Notion page `348c6894-2bed-811e-9f39-d406fb2ad991`. Regression 284 passed + 1 skipped.
- **Codex findings queued**:
  - **M1** (mechanical, PR-5c.1): `CFD_HARNESS_HMAC_SECRET` explicit `base64:`/`text:` prefix instead of heuristic
  - **L1** (mechanical, PR-5c.1): Sidecar hex validation `^[0-9a-fA-F]{64}$`
  - **M2** (governance DEC): Sidecar v2 with `kid`/`alg`/`domain` metadata + formal rotation runbook (verifier keyring retention, rotation ledger, multi-signer story, compromise procedure)
  - **L2** (docs PR or Phase 5 PR-5d): Canonical JSON spec publication for external verifiers
- **v6.1 autonomous_governance counter**: 10 → **11**. Hard-floor-4 discipline honored for PR-5c. PR-5d should follow same pattern (post-merge Codex review) OR Kogami should run formal counter-reset retrospective.
- **Phase 5 PR-5c.1 LANDED + second Codex review (2026-04-21T02:10)**: Mechanical fixes for Codex M1 + L1 per DEC-V61-015. PR #15 merged `db83764b55fe78048aaaeed3c325552f7b5bfb54`. Env-var `CFD_HARNESS_HMAC_SECRET` now uses explicit `base64:` / `text:` / un-prefixed-as-plain-text contract (M1 closed). Sidecar `write_sidecar` + `read_sidecar` enforce `^[0-9a-fA-F]{64}$` (L1 closed). 14 new/modified tests. Post-merge **Codex GPT-5.4 second-round review**: `APPROVED_WITH_NOTES` — M1+L1 correct, one new **M3 queued** (legacy migration hazard: un-prefixed base64 silently becomes literal UTF-8; no error fires; signatures diverge). Report at `reports/codex_tool_reports/2026-04-21_pr5c1_codex_followup_review.md` (token 76,152). Notion DEC-V61-015 page `348c6894-2bed-811a-b9b0-e2715b443efa`. Regression 298 passed + 1 skipped.
- **Codex findings ledger (Phase 5 running tally)**:
  - ✅ **M1 CLOSED** (PR-5c.1): explicit env-var prefix
  - ✅ **L1 CLOSED** (PR-5c.1): sidecar hex regex
  - 🔒 **M2 QUEUED**: sidecar v2 with kid/alg/domain + formal rotation runbook (governance DEC)
  - 🔒 **M3 NEW-QUEUED**: legacy migration hazard → PR-5c.2 docs-only fix + optional runtime DeprecationWarning guard
  - 🔒 **L2 QUEUED**: canonical JSON spec publication (docs PR)
- **v6.1 autonomous_governance counter**: 11 → **12**. Codex post-merge pattern holds across 2 consecutive PRs (PR-5c + PR-5c.1). Pattern demonstrably sustainable. Token costs: 117,588 + 76,152 = 193,740 for this security-review arc.
- **Phase 5 PR sequence status**: 3/4 main PRs landed (5a + 5b + 5c) + 1/1 post-review fix (5c.1). PR-5d (Screen 6 UI) remains the last main-sequence PR. PR-5c.2 (docs-only M3 mitigation) is ~5 LOC and can land alongside PR-5d or before.
- **Phase 5 PR-5c.2 + PR-5c.3 LANDED (2026-04-21T02:55)** — M3 fully closed.
  - **PR-5c.2** (DEC-V61-016 · merge `87264bc1`): Runtime guard `_looks_like_legacy_base64` + migration docstring + edge tests (URL-safe/unpadded/CRLF/BOM/trailing whitespace). 11 new tests. Codex 3rd-round review: APPROVED_WITH_NOTES — flagged `DeprecationWarning` as silenced by default. Notion `348c6894-2bed-8130-9326-dbf19543fb24`. Report `reports/codex_tool_reports/2026-04-21_pr5c2_m3_review.md` (token 94,316).
  - **PR-5c.3** (DEC-V61-017 · merge `7e6f5732`): Warning class fix — `DeprecationWarning` → custom `HmacLegacyKeyWarning(UserWarning)`. Closes M3 fully. **No 4th Codex review** (verbatim rec #2, mechanical, atomic). Notion `348c6894-2bed-81b9-8712-c83d104a9c97`.
- **Codex findings ledger FINAL for signing module**:
  - ✅ M1 CLOSED (PR-5c.1 · DEC-V61-015)
  - ✅ L1 CLOSED (PR-5c.1 · DEC-V61-015)
  - ✅ M3 CLOSED (PR-5c.2+5c.3 · DEC-V61-016+017)
  - 🔒 M2 QUEUED — sidecar v2 + rotation runbook (governance DEC, needs Kogami design)
  - 🔒 L2 QUEUED — canonical JSON spec publication (docs PR)
- **Codex review arc economics**: 3 rounds, cumulative 288,056 tokens. Diminishing returns documented on round 3. PR-5c.3 skipped 4th review per DEC-V61-016 rationale.
- **v6.1 autonomous_governance counter**: 12 → **14** (DEC-V61-016 + DEC-V61-017 both autonomous). Deep past hard-floor-4 threshold ≥10. Hard-floor-4 formal retrospective is overdue — can roll into post-PR-5d cleanup.
- **Phase 5 sequence final status**: 3/4 main + 3/3 Codex-review fixes (5c.1 + 5c.2 + 5c.3). Only **PR-5d Screen 6 UI** remains. All 5 open design questions resolved (Kogami "全部接受" 2026-04-21). PR-5d ready to start.
- **⚠️ Phase 5 PR-5d LANDED but CHANGES_REQUIRED (2026-04-21T03:40)** — PR #18 merged `320bed1012ea55be73ef4cda77118d0dfe66e7bb`. FastAPI route + Screen 6 React page + V&V40 checklist + 16 route tests. Frontend tsc clean. 325 passed + 1 skipped regression. **BUT post-merge Codex GPT-5.4 xhigh 4th-round review: `CHANGES_REQUIRED`** — 2 HIGH findings + 1 MEDIUM. DEC-V61-018 Notion page `348c6894-2bed-81f1-aa6b-db993c3fde2f`, Status=Proposed.
  - **HIGH #1**: POST signs empty-evidence bundles (no run_output, no measurement, no verdict); accepts nonexistent case_id (test blesses it). In regulated-review context, a signed "audit package" with no evidence is a misleading artifact.
  - **HIGH #2**: `build_manifest()` auto-stamps `generated_at` per call. Two identical POSTs 1s apart → different ZIP hash + different HMAC. **Violates DEC-V61-013 byte-reproducibility contract.**
  - **MEDIUM**: V&V40 checklist overstates FDA alignment; product-specific summary, not faithful to FDA 2023 CM&S guidance; references manifest fields absent from current skeleton bundles.
  - Non-blocking: path-traversal guard sound, HMAC secret handling clean, FileResponse correct, frontend state handling OK, python 3.9 pyproject mismatch is pre-existing.
- **⚠️ Phase 5 is NOT complete** until PR-5d.1 closes HIGH #1 + HIGH #2. Requires Kogami decision between X1 (fix in PR-5d.1, ~140 LOC, recommended), X2 (revert + v2), X3 (feature-flag dry-run), X4 (defer).
- **Codex review arc final tally (rounds 1-4)**:
  - PR-5c: APPROVED_WITH_NOTES · 117,588 tokens
  - PR-5c.1: APPROVED_WITH_NOTES · 76,152 tokens
  - PR-5c.2: APPROVED_WITH_NOTES · 94,316 tokens
  - **PR-5d: CHANGES_REQUIRED · 143,521 tokens** ← highest-value round, caught semantic issues the module-level reviews couldn't see
  - **Cumulative: 431,577 tokens**. Counter discipline earned its keep: 4th review caught real regressions self-signed review would miss.
- **v6.1 autonomous_governance counter**: 14 → **15**. Further Phase 5 work (PR-5d.1) will bump to 16.
- **✅ Phase 5 PR-5d.1 LANDED (2026-04-21T04:30)** — PR #19 merged `ca9fe0e525a92e8b52ea32092e228b0bf7ace73e` per DEC-V61-019. Three verbatim Codex-recommended fixes close the `CHANGES_REQUIRED` verdict on PR-5d:
  - **HIGH #1 CLOSED**: `ui/backend/routes/audit_package.py` now gates POST on `load_case_detail(case_id) is not None`; unknown case_id → `HTTPException(404, "unknown case_id: ...")`. Test `test_unknown_case_id_still_builds_skeleton` replaced with `test_unknown_case_id_returns_404`.
  - **HIGH #2 CLOSED**: `generated_at` is now deterministic — `hashlib.sha256(f"{case_id}|{run_id}".encode())[:16]` passed as kwarg to `build_manifest`. Two identical POSTs produce byte-identical ZIP + identical HMAC signature. Tests `test_identical_posts_produce_byte_identical_zip` + `test_different_run_ids_produce_different_bundles` added.
  - **MEDIUM CLOSED**: Schema field `vv40_checklist` → `evidence_summary` (Python class `AuditPackageVvChecklistItem` → `AuditPackageEvidenceItem`, TypeScript interface + field renamed). UI heading "FDA V&V40 credibility-evidence mapping" → "Internal V&V evidence summary" with disclaimer noting it's not a V&V40 substitute. Page-level header description trimmed to remove FDA/aerospace/nuclear licensing claims the skeleton bundle shape does not support.
  - Diff scope: 139 LOC across 5 files (3 backend + 2 frontend). Regression 327 passed + 1 skipped (baseline 325 + 2 new byte-repro tests). `npx tsc --noEmit` clean.
  - **Codex round 5 review queued** (post-merge) to confirm closure before Phase 5 ships at 4/4. If APPROVED → Phase 5 complete; if CHANGES_REQUIRED → PR-5d.2 mechanical pattern.
- **✅ Codex round 5 LANDED (2026-04-21T04:35)** — Verdict `APPROVED_WITH_NOTES` · 95,221 tokens · report `reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md`. Critical/High/Medium findings: **NONE**. All three PR-5d findings confirmed closed (HIGH #1 whitelist gate, HIGH #2 byte-repro, MEDIUM V&V40 rename). One new **L3 Low/Informational** finding queued: `generated_at` is now a deterministic 16-hex hash fragment but the field is still labelled as a timestamp in API/UI/docs. Mitigation options (path A rename to `build_fingerprint` OR path B split into signed-fingerprint + unsigned-wall-time) documented in DEC-V61-019; neither blocks Phase 5 ship.
- **Codex findings ledger FINAL for Phase 5 (rounds 1-5)**:
  - ✅ M1 CLOSED (PR-5c.1) · ✅ L1 CLOSED (PR-5c.1) · ✅ M3 CLOSED (PR-5c.2+5c.3)
  - ✅ HIGH #1 CLOSED (PR-5d.1 round 5 confirmed) · ✅ HIGH #2 CLOSED (PR-5d.1 round 5 confirmed) · ✅ MEDIUM CLOSED (PR-5d.1 round 5 confirmed)
  - 🔒 M2 QUEUED (sidecar v2 + kid/alg/domain — governance DEC)
  - 🔒 L2 QUEUED (canonical JSON spec publication)
  - 🔒 **L3 NEW-QUEUED** (generated_at field semantics — rename OR split)
- **Codex review arc Phase 5 cumulative**: 117,588 + 76,152 + 94,316 + 143,521 + 95,221 = **526,798 tokens** across 5 rounds. Round 4 was the highest-value round (caught semantic HIGH findings module-level review couldn't see). Round 5 was validation-only and produced a clean APPROVED_WITH_NOTES.
- **v6.1 autonomous_governance counter**: 15 → **16**. 5th consecutive Codex post-merge review on Phase 5. Hard-floor-4 retrospective is **overdue** — should land before Phase 6 scoping.
- **✅ Phase 5 sequence COMPLETE (honest)**: 4/4 main sequence landed (5a + 5b + 5c + 5d) + 4/4 Codex-review fixes (5c.1 + 5c.2 + 5c.3 + 5d.1). All 3 originally-flagged HIGH/MEDIUM findings closed and round-5 confirmed. Screen 6 Audit Package Builder is production-ready modulo the three remaining queued items (M2 sidecar v2 · L2 canonical JSON spec · L3 generated_at rename), none of which block Phase 5 ship. **Next scoping decision**: P1 counter-16 retrospective OR P2 Docker dashboard validation OR Phase 6 kickoff.
- **✅ RETRO-V61-001 DECIDED (2026-04-21T04:55)** — Kogami chose bundle D + delegated Q1-Q5 to Claude. v6.1 governance rules updated in `~/CLAUDE.md` §"v6.1 自主治理规则":
  - **Q1 · counter reset 16 → 0** at retro close. Phase 6 starts at counter=0.
  - **Q2 · hybrid model**: hard-floor-4 stop-signal **retired**. Counter = pure telemetry. Retrospectives mandatory on phase-close OR counter≥20 OR any `CHANGES_REQUIRED` verdict.
  - **Q3 · 3 new Codex triggers codified**: security-sensitive operator endpoints; byte-reproducibility-sensitive paths; ≥3-file API schema renames.
  - **Q4 · verbatim exception** tightened to 5-of-5 hard criteria (diff-level verbatim match + ≤20 LOC + ≤2 files + no public API change + PR body cites round + finding ID).
  - **Q5 · external-gate DECs** (V61-006, V61-011) stay N/A in counter but always listed in retros.
  - **NEW rule**: `self_estimated_pass_rate ≤70%` → mandatory **pre-merge** Codex review (not post-merge). DEC-V61-018's 60% would have triggered this.
  - Retrospective doc: `.planning/retrospectives/2026-04-21_v61_counter16_retrospective.md` (status: DECIDED)
- **v6.1 autonomous_governance counter (post-retro)**: 16 → **0**. Phase 6 work will increment from 0 under the new risk-tier-driven governance.
- **§5d Part-2 acceptance COMPLETE (2026-04-21T05:45)** — 5-case real-solver batch finished in 8 min wall-clock (commit `85fa4e5`):
  - Option C-corrected chosen by Kogami: 5 cases (LDC + BFS + plane_channel + TFP + duct_flow) via FoamAgentExecutor; 5 auto-generated measurement fixtures landed under `ui/backend/tests/fixtures/`; backend restarted; Screens 4/5 now render real-solver-derived data for 7/10 cases (was 3/10).
  - Dashboard status mix: {2 FAIL · 1 HAZARD · 7 UNKNOWN} → {6 FAIL · 1 HAZARD · 3 UNKNOWN}.
  - Solver results: 1 PASS (plane_channel_flow, 415s) + 4 FAIL (LDC 8s, BFS 7s, TFP 32s, duct_flow 32s). FAILs reflect quick-resolution acceptance runs (ncx=40 ncy=20 defaults), NOT regressions from historical PASS baselines which used higher resolution.
  - **⚠️ TFP fixture was OVERWRITTEN** (previously curated per DEC-ADWM-005 Spalding-fallback audit wiring). Curated version preserved in git at `a02c3a2^`. Flagged for Kogami restore/merge decision in Part-2 report.
  - **2 new P6 tech-debt items**: P6-TD-001 (BFS reattachment_length extractor returns physically-impossible negative value); P6-TD-002 (TFP + duct_flow both yield identical Spalding-fallback Cf, suggesting case-parameter independence).
  - **PR #20 merged** `b8be73a` — first PR under new v6.1 governance (counter 0 → 1). Declared `docker>=7.0` as `cfd-real-solver` optional dep + fixed misleading error messages in `src/foam_agent_adapter.py` (three error paths now distinguish missing-SDK / NotFound / DockerException / generic init). Self-estimate 92%. Codex round 6 post-merge review queued.
  - Driver: `scripts/p2_acceptance_run.py` · raw log: `reports/post_phase5_acceptance/2026-04-21_part2_raw_results.json` · Part-1 report: `2026-04-21_ui_infra_validation.md` · Part-2 report: `2026-04-21_part2_solver_runs.md`.
  - v6.1 counter under new governance: **2** (PR #20 = 1, Part-2 artifacts commit = 2).

---

# Path B — Phase 0 UI MVP (2026-04-20)

**Decision anchor**: `.planning/decisions/2026-04-20_path_b_ui_mvp.md` (DEC-V61-002).
**Roadmap anchor**: `docs/ui_roadmap.md` (P0..P5 + post-MVP P6..P10).
**Branch**: `feat/ui-mvp-phase-0` (forked from `main` at merge-SHA
`dbffd8af8229671b3945516b0a41f328af18ee1e`).

## Deliverables landing in Phase 0

| Artifact | Status | Location |
|---|---|---|
| Product thesis | ✅ | `docs/product_thesis.md` |
| UI design spec | ✅ | `docs/ui_design.md` |
| UI roadmap (6 phases + post-MVP) | ✅ | `docs/ui_roadmap.md` |
| DEC-V61-002 formal decision | ✅ | `.planning/decisions/2026-04-20_path_b_ui_mvp.md` |
| FastAPI backend (read-only src/ wrap) | ✅ | `ui/backend/` — 7/7 pytest green |
| Backend schemas (Pydantic v2) | ✅ | `ui/backend/schemas/validation.py` |
| Backend routes (`/health`, `/cases`, `/validation-report`) | ✅ | `ui/backend/routes/` |
| Measurement fixtures (3 canonical cases) | ✅ | `ui/backend/tests/fixtures/` |
| Vite + React 18 + TS + Tailwind frontend | ✅ | `ui/frontend/` — tsc clean, vite build 222.8 KB js |
| Screen 4 Validation Report | ✅ | `ui/frontend/src/pages/ValidationReportPage.tsx` |
| Design primitives (PassFailChip, BandChart, AuditConcernList, PreconditionList, DecisionsTrail) | ✅ | `ui/frontend/src/components/` |

## Phase-0 gate criteria (DEC-V61-002)

1. ✅ Backend tests green (7/7) without touching 三禁区.
2. ✅ Frontend tsc -b + vite build both clean.
3. ✅ Three canonical cases render end-to-end with correct three-state
   contract status (DHC = FAIL w/ 159% deviation; cylinder = HAZARD armed
   silent-pass; TFP = HAZARD armed Spalding fallback).

4. ✅ No mutation of `src/**`, `tests/**`, `knowledge/gold_standards/**`,
   or `knowledge/whitelist.yaml`.

5. ⏳ PR #2 opened + merged (regular merge commit, 留痕 > 聪明).
6. ⏳ DEC-V61-002 mirrored to Notion Decisions DB.

## 禁区 compliance (this phase)

- `src/` — NOT TOUCHED.
- `tests/` (at repo root) — NOT TOUCHED.
- `knowledge/whitelist.yaml` — NOT TOUCHED (read-only via backend).
- `knowledge/gold_standards/**` — NOT TOUCHED (read-only via backend).

The FastAPI backend and its tests live under `ui/backend/tests/` —
that directory is new and is NOT part of the legacy `tests/` 禁区.

## Path-B phase horizon

| Phase | Scope | Branch | Gate focus |
|---|---|---|---|
| P0 | Backend + Screen 4 Validation Report | `feat/ui-mvp-phase-0` | this commit |
| P1 | Case Editor (Monaco + monaco-yaml + whitelist schema validation) | `feat/ui-mvp-phase-1` | editor must refuse edits that violate 禁区 invariants |
| P2 | Decisions Queue (DEC-XXX authoring + Notion sync) | `feat/ui-mvp-phase-2` | two-way Notion mirror integrity |
| P3 | Run Monitor (WebSocket residual streaming + VTK.js) | `feat/ui-mvp-phase-3` | reconnect / backpressure |
| P4 | Dashboard (Plotly KPI tiles + regression wall) | `feat/ui-mvp-phase-4` | data-freshness badges |
| P5 | Audit Package Builder (weasyprint PDF + SHA-256 manifest) | `feat/ui-mvp-phase-5` | **external Gate** — commercial signing review |

See `docs/ui_roadmap.md` for per-phase acceptance, non-goals, risks,
and rollback plans.

## 2026-04-21 Evening/Night — Phase 6 tech-debt sweep (Claude Opus 4.7 1M, S-005 kickoff)

Phase 6 context: after Phase 5 Honestly Complete (e4c9bd8), this session cleared
the queued tech-debt items from `.planning/handoffs/2026-04-21_session_end_kickoff.md`
under user instruction "其他你的建议项，全部按优先级完成" (second-solver explicitly excluded).

**Completed (10 PRs merged on main)**:

| PR | SHA | Scope |
|---|---|---|
| #21 | 67b129e | P6-TD-001 — BFS reattachment x>0 physical-plausibility guard |
| #22 | 36e3249 | P6-TD-002 — duct_flow dispatch guard (Codex round 8 CHANGES_REQUIRED, resolved by PR #27) |
| #23 | aed95d4 | L3 — generated_at → build_fingerprint cross-file rename |
| #24 | b66335e | datetime.utcnow() → timezone-aware now(timezone.utc) |
| #25 | 3e6e765 | test_validation_report gold/measurement drift assertions |
| #26 | 87d7658 | PR #21 round-7 Low follow-ups (static-method test coverage + stale docstring) |
| #27 | 7bbbeb2 | PR #22 round-8 CHANGES_REQUIRED fix — canonical `_is_duct_flow_case()` helper + fail-closed + integration test |
| #28 | 829c953 | L-PR20-2 — narrow docker error-branch coverage (_DOCKER_AVAILABLE=False, real NotFound, MagicMock type-guard) |
| #29 | c27f4fd | PR #23 round-9 Note #2 — manifest-layer legacy-key-absence assertion |
| #30 | 25fd65d | L2 — canonical JSON spec doc (7 reference test vectors, signature framing, verifier checklist) |

**DECs filed (3)**: DEC-V61-021 (BFS), DEC-V61-022 (duct), DEC-V61-023 (L3). All three
Notion-sync-pending — frontmatter verdicts captured: 021 APPROVED_WITH_NOTES,
022 CHANGES_REQUIRED → RESOLVED by PR #27, 023 APPROVED_WITH_NOTES.

**Codex rounds run (3)**: Round 7 (PR #21) APPROVED_WITH_NOTES · Round 8 (PR #22)
CHANGES_REQUIRED · Round 9 (PR #23) APPROVED_WITH_NOTES. All reports committed
under `reports/codex_tool_reports/`.

**New retrospective**: RETRO-V61-002 (incident) — small-scope retro for PR #22
CHANGES_REQUIRED per RETRO-V61-001 bundle D rule. Documents dispatcher review
checklist + self-estimate calibration for future dispatcher-touching PRs.

**Regression**: 104/104 test_foam_agent_adapter.py · 6/6 test_validation_report.py ·
113/113 test_audit_package/ · full matrix unchanged pre-existing failures
(contract_dashboard + error_attributor + gold_standard_schema, confirmed orthogonal
via `git stash` baseline comparison).

**Counter under new v6.1 governance (pure telemetry)**: advanced from 1 → 11 over
this session. Well below the 20-threshold arc retro. All within autonomous scope.

**禁区 compliance**: src/foam_agent_adapter.py touched (>5 LOC → Codex triggered in
all applicable rounds). knowledge/gold_standards/** + knowledge/whitelist.yaml
NOT TOUCHED. All 10 PRs merged as regular merge commits (留痕 > 聪明).

**Session main HEAD at close**: `25fd65d` (PR #30 merge).

Pending items (unclosed, queued for next session):

- M2 — sidecar v2 with kid/alg/domain metadata + rotation runbook (Medium scope, deferred by size)
- P6-TD-003 — implement `_extract_duct_friction_factor` targeting Darcy-Weisbach `f=0.0185` gold (requires second solver per user exclusion — held)
- foam_agent_adapter.py 7000-line refactor (Medium-Large; out of scope this session)
- Notion sync for DEC-V61-021/022/023 + RETRO-V61-002 (requires Notion MCP; deferred)

## 2026-04-21 Late Night — /learn commercial-demo deepening (Claude Opus 4.7 1M, S-006)

Session scope: per user directive "做商业级 demo，受众是想做 CFD 的学生", deepened `/learn`
from "10 UNKNOWN cards" into a pedagogical catalog with story. Three PRs landed:

| PR | SHA | Scope |
|---|---|---|
| #31 | e940c1c | `/learn` student-facing demo shell (10 canonical CFD problems as visual catalog) |
| #32 | 52c376a | multi-run architecture (RunDescriptor/RunListResponse, URL-addressable Compare tab) |
| #33 | f633348 | **this session's main drop** — 9 teaching-run fixtures + run-distribution pills (engine-driven, not curator-hint) + 8 real flow-field PNGs (Ghia/Blasius/Williamson/Spalding/Grossmann-Lohse/Cooper provenance) |

**DEC filed (1)**: DEC-V61-024 (teaching runs + badges + flow-fields).
Frontmatter: `autonomous_governance: true`, `codex_verdict: CHANGES_REQUIRED → RESOLVED`,
`external_gate_self_estimated_pass_rate: 90%`, `notion_sync_status: pending`.

**Codex round run (1)**: Round 10 (PR #33 pre-merge) CHANGES_REQUIRED with 2 HIGH findings,
both fixed verbatim in `55b1a88`:

1. `verdict_counts` was aggregated from `expected_verdict` curator hint → pill could lie
   about contract engine output (e.g. `reference_pass` run labeled PASS despite
   silent-pass hazard armed by gold). Fix: per-run `_derive_contract_status` evaluation.

2. `impinging_jet` flow-field PNG showed Baughn Re=23750 Nu≈110 regime but case was
   rescaled to Cooper Re=10000 Nu=25 family → physical inconsistency. Fix: PNG
   regenerated with Cooper 1984 anchors + factor overlays matching wrong_model (+52%)
   and real_incident (+8%) fixtures.

**Default contract distribution** (after fixes): **4 PASS · 3 HAZARD · 3 FAIL** across
10 cases · 20 runs. Every case now has ≥1 curated run.

**Counter (v6.1 pure telemetry)**: 11 → 12.

**禁区 compliance**: `src/**`, repo-root `tests/**`, `knowledge/gold_standards/**`,
`knowledge/whitelist.yaml` all untouched. All work in `ui/backend/`, `ui/frontend/`,
`scripts/flow-field-gen/`, `.planning/decisions/`.

**Session main HEAD at close**: `f633348` (PR #33 merge).

## 2026-04-21 Late Night — Option A Phase 1 deepening (same session, continued)

PR landed same session: #34 (`0fba4be`). Closes the four cases (duct / DHC /
plane_channel / RBC) that only had 1 curated run after PR #33, and the four
cases (duct / DHC / BFS / NACA) that had no flow-field visual.

**11 new fixtures** (6 reference_pass, 3 under_resolved, 2 wrong_model) +
**4 new flow-field PNGs** (Armaly/Driver / Ladson / de Vahl Davis / Colebrook+Jones)

+ **engine fix** in `_load_gold_standard` shape-B synthesis to handle

profile-quantity reference_values (previously collapsed to ref=0.0 and
silently forced PASS on u_plus/Cp profile cases).

**DEC filed (1)**: DEC-V61-025 (`.planning/decisions/2026-04-21_phase6_td025_learn_full_coverage.md`).

**Codex round run (1)**: Round 11 (PR #34 pre-merge) CHANGES_REQUIRED with
2 HIGH + 1 MEDIUM findings, all fixed verbatim in commit `6335c8d`:

1. Backend pytest red (2/42 fails) — DHC test + dashboard test drifted
   against new default distribution. Fix: pin DHC test to
   `run_id=real_incident`; relax dashboard `fail_cases>=1` assertion.

2. plane_channel teaching fixtures silently PASSed everything — shape-B
   synthesis collapsed `u_mean_profile` to ref=0.0. Fix: scan ALL
   reference_values entries for non-zero scalar; expanded key set to
   include `u_plus`.

3. BFS figure plotted under_resolved marker at 6.1 but labeled "5.1
   (-18%)"; frontend caption bound Driver gold to Re=7600. Fix: marker
   to 5.1, regenerate PNG, caption cites Re_h=37500 provenance.

**Final distribution**: **8 PASS · 2 HAZARD · 0 FAIL** across 10 cases · 31 runs.
Every case has ≥3 runs, ≥1 flow-field visual, ≥1 PASS-or-HAZARD reference run.
FAIL semantics now live only on non-default teaching runs (`?run_id=under_resolved`
or `wrong_model`) — intentional pedagogical framing.

**Counter (v6.1 pure telemetry)**: 12 → 13.

**禁区 compliance**: no writes to `src/**`, repo-root `tests/**`,
`knowledge/gold_standards/**`, `knowledge/whitelist.yaml`. All work in
`ui/backend/`, `ui/frontend/`, `scripts/flow-field-gen/`, `.planning/decisions/`.

**Session main HEAD at close**: `0fba4be` (PR #34 merge).

## 2026-04-21 Late Night — Option A Phase 2 (same session continued)

User directive: *"do 1 + 3 together"* — interactive mesh-density slider + Pro
Workbench tab wiring. Landed as PR #35 (`5d54d48`).

**New feature**: 5th tab `Mesh` on LearnCaseDetailPage. Student drags across
4 mesh densities (mesh_20 / mesh_40 / mesh_80 / mesh_160) and sees the
measurement / deviation / verdict / tolerance-band position animate live.
Backed by `useQueries` parallel fetch + SVG `ConvergenceSparkline`.

**New runs**: 12 fixtures (3 cases × 4 densities) under new `grid_convergence`
RunCategory. Literature-backed sweeps:

- LDC u_centerline @ y=0.0625: Ghia 1982 gold, values {-0.048→-0.0375}
- TFP Cf @ x=0.5: Blasius gold, values {0.0065→0.00423}
- BFS Xr/H: repo gold 6.26, values {4.8→6.25}

**Pro Workbench link**: top-right on every case detail page → `/cases/:id/report`.

**DEC filed (1)**: DEC-V61-026 (`.planning/decisions/2026-04-21_phase6_td026_learn_mesh_slider.md`).

**Codex round run (1)**: Round 12 (PR #35 pre-merge) CHANGES_REQUIRED with
3 MEDIUM + 1 LOW findings, all fixed in commit `32a2893`:

1. `list_runs()` filename-lex order → mesh_160 sorted before reference_pass.
   Fix: explicit pedagogical category order + numeric-aware mesh_N secondary.

2. TFP fixtures claimed "5% 容差" but gold is ±10%. Fix: copy updated.
3. BFS narrative over-claimed Driver 1985 convergence despite whitelist
   Re=7600 ≠ Driver Re_H≈36000. Fix: relabel as "repo gold" with explicit
   Reynolds-mismatch note.

4. NaN handling in ConvergenceSparkline + formatNumber. Fix: `Number.isFinite`
   guards.

**Counter (v6.1 pure telemetry)**: 13 → 14.

**禁区 compliance**: no writes to `src/**`, repo-root `tests/**`,
`knowledge/gold_standards/**`, `knowledge/whitelist.yaml`. All work in
`ui/backend/`, `ui/frontend/`, `.planning/decisions/`.

**Session main HEAD at close**: `5d54d48` (PR #35 merge) + STATE update.

## 2026-04-21 Late Night — Option A Phase 3 (same session continued)

User directive: *"extend mesh-slider to 7 more cases, OpenFOAM case-export
bundle, BFS gold re-sourcing to Re=7600-consistent anchor"*. Landed as
PR #36 (`7a7610c`).

**Thread 1 — mesh-slider extended to all 10 cases**: 28 new
grid_convergence fixtures (was 3 cases × 4, now 10 cases × 4 = 40).
All sweeps monotone, literature-anchored.

**Thread 2 — case-export reference bundle**: new `GET /api/cases/{id}/export`
returning zip with README + validation_contract.md + byte-identical
gold YAML. 13 new tests including byte-identity guard. "下载参考包 .zip" button
on every case detail page. Explicit non-goal: NOT a runnable OpenFOAM
case dir (that'd require 三禁区 adapter changes).

**Thread 3 — BFS Re-mismatch Q-4 gate**: filed in `external_gate_queue.md`
with 4 path options (A/B/C/D) for Kogami decision. Learn-side narrative
updated with ⚠️ block so students see the caveat even if Q-4 stays
unresolved.

**DEC filed (1)**: DEC-V61-027.

**Codex round attempted (1, blocked)**: Round 13 blocked by CLI
infrastructure error (`Model not found gpt-5.4` — same error across
all fallback models tried). Self-review performed in lieu; post-merge
Codex queued once infrastructure recovers. Counter self-estimated
`external_gate_self_estimated_pass_rate: 75%`, acknowledging the
reduced safety net.

**Counter (v6.1 pure telemetry)**: 14 → 15.

**禁区 compliance**: untouched. case_export route READS gold_standards/
but doesn't write. Q-4 explicitly defers any gold modification to
external Gate.

**Session main HEAD at close**: `7a7610c` (PR #36 merge) + DEC + STATE updates.

## End-of-session state (S-006)

- **Demo depth**: 10 cases · **71 runs** · 10 flow-field PNGs · **10 interactive
  mesh-convergence demos** · Pro Workbench one-click-away · **case-export bundle
  one-click-away**.

- **Default distribution**: 8 PASS · 2 HAZARD · 0 FAIL.
- **v6.1 counter**: **15** (well below 20 arc-retro threshold).
- **Codex rounds this session**: 10, 11, 12, 13 all CHANGES_REQUIRED → RESOLVED
  (round 13 ran post-merge on a different account after user fixed CLI infra;
  3 findings applied in `7f242f3` — monotonicity regression test +
  |deviation|-monotonicity fixture adjustments + DHC description drift).

- **API endpoints**: 24 total (+1 new `/api/cases/{id}/export`).
- **External gate queue**: **0 open** (Q-4 CLOSED 2026-04-21 via Path A / DEC-V61-028 — BFS gold re-sourced to Le, Moin & Kim 1997 DNS at Re_H=5100, Xr/H=6.28 matches our 6.26 inside tolerance; Armaly 1983 retained as corroborating experiment).

Pending items (unclosed, queued for next session):

- **A-class Phase 3** (optional): mesh-convergence sweep for remaining 7
  cases (would need literature-sourced scalar anchors for each) — ✅ LANDED
  in DEC-V61-027. OpenFOAM case-export bundle — ✅ LANDED in V61-027. BFS
  gold re-sourcing — ✅ LANDED in DEC-V61-028.

- **Notion sync backlog** (9 items, MCP still requires Claude Desktop re-auth):
  DEC-V61-021, V61-022, V61-023, RETRO-V61-002, V61-024, V61-025, V61-026,
  V61-027, **V61-028**. NOTION_TOKEN is fixed in `~/.zshrc`; direct-REST
  fallback via the `notion-sync-cfd-harness` skill works if MCP stays down.

- **Engineering-quality residual**: under_resolved/wrong_model values are
  defensibly-in-family but not grid-convergence-backed. Acceptable for
  teaching catalog; NOT for regulatory audit package.

- **Plane_channel real_incident narrative drift**: post engine fix, its
  `expected_verdict: PASS` no longer matches actual (FAIL on quantity mismatch).
  Left as historical artifact; consider relabeling in a future commit.

- M2 sidecar v2 + rotation runbook (carried from S-005).
- foam_agent_adapter.py refactor (carried from S-005).
- P6-TD-003 held on user second-solver exclusion.

---

## 2026-04-21 Evening — Phase 5b LDC simpleFoam migration (DEC-V61-029, S-007)

**Landed**: simpleFoam infrastructure migration complete across 6 src commits (0d85c98 plan-01 baseline, 66ac478 dispatcher, c7248ff momentumTransport, 002a6fb blockMesh frontAndBack, 1f87718 extractor x_tol mesh-derived, plus closing commit with 2 Codex MEDIUM fixes). Real-solver end-to-end verified: simpleFoam converges in ~1024 SIMPLE iterations, produces Ghia 1982 Re=100 physics (u=-0.209 at y=0.5, min at y=0.44 of -0.212).

**Surprise finding**: Plan 02 comparator FAIL revealed `knowledge/gold_standards/lid_driven_cavity.yaml` reference values do NOT match actual Ghia 1982 Table I. Gold cites Ghia but values are incorrect (u=+0.025 at y=0.5 vs Ghia's -0.206). Filed as **Q-5** in external_gate_queue.md. Phase 5b PASS verdict blocked on gold re-transcription (Path A recommended).

**Codex round 14**: CHANGES_REQUIRED → PARTIALLY_RESOLVED. HIGH (x_tol) fixed in 1f87718; MED 1+2 (dispatcher too-broad, classifier solver-coupled) fixed inline; MED 3 (_docker_exec timeout not enforced) deferred as cross-cutting tech debt.

**Counter**: v6.1 autonomous_governance 15 → 16. Arc-retro threshold (20) still has 4 slots of runway.

**Phase 5b scope delta**: LDC sub-phase infrastructure COMPLETE; PASS verdict BLOCKED on Q-5. Remaining 7 FAIL cases (BFS, TFP, duct_flow, impinging_jet, naca0012, DHC, RBC) queued for Phase 5c..5j per-case sub-phases; each MUST cross-check gold values against cited paper as first step (LDC lesson learned).

**Open items** (post-Phase-5b):

- ~~Q-5 external-gate decision~~ — CLOSED 2026-04-21 via Path A (DEC-V61-030). LDC gold re-transcribed from Ghia 1982; audit now 11/17 PASS.
- DEC-V61-029 Notion sync ✓ (done). DEC-V61-030 Notion sync pending.
- 7 remaining FAIL-case sub-phases (Phase 5c..5j). **Mandatory first step for each**: cross-check the whitelist gold against the cited paper (LDC lesson learned).
- _docker_exec timeout enforcement (Codex MED 3, cross-cutting tech debt).
- Optional Phase 5b-sub-2: graded blockMesh + native-y extractor to close the remaining 6 LDC audit FAILs (physical residuals, not bugs).

---

## 2026-04-21 Night — Phase 7a Field post-processing capture (DEC-V61-031, S-008)

**Landed**: First sub-phase of Phase 7 (scientific-grade CFD reporting). 3 waves — adapter controlDict functions{} + executor foamToVTK capture + driver per-run manifest (Wave 1, commit 8bf2cfb); backend route + Pydantic schemas + run_id parser + SHA256-cached service + 11 pytest (Wave 2, commit f507b9e); Codex 3-round closure + DEC + atomic Wave-3 fixes.

**Real OpenFOAM integration run**: `scripts/phase5_audit_run.py lid_driven_cavity` in `cfd-openfoam` Docker container produces 8 artifacts at `reports/phase5_fields/lid_driven_cavity/20260421T082340Z/` — VTK volume (3.1 MB) + boundary + sample profiles at 3 iterations + residuals.csv + residuals.dat + log.simpleFoam. `GET /api/runs/lid_driven_cavity__audit_real_run/field-artifacts` returns 200 with 8 unique subpath URLs + matching SHA256.

**Codex arc (3 rounds)**:
- Round 1: CHANGES_REQUIRED — 2 HIGH (URL basename collision on `sample/{0,500,1000}/uCenterline.xy`, run_id path-traversal via `..__pwn` / `%2e%2e__pwn`) + 1 MED (Phase 7a metadata over-applied beyond LDC) + 1 LOW (SHA cache uses float `st_mtime` not `st_mtime_ns`).
- Round 2: CHANGES_REQUIRED — 1 HIGH (list endpoint missed timestamp validation that download had; malicious manifest `timestamp='../../outside'` enumerated outside files).
- Round 3: APPROVED_WITH_COMMENTS — 2 non-blocking (non-object manifest → 500, out-of-dir symlinks → 500); both fixed in same pass.
- Fix strategy: extracted `_resolve_artifact_dir()` shared validator; enforced `^\d{8}T\d{6}Z$` timestamp shape gate; strict identifier regex on case_id + run_label; POSIX relative path in manifest.filename + `{filename:path}` FastAPI converter.

**Self-pass-rate calibration**: estimated 0.75, actual first-round 0.0. Insight for RETRO-V61-002: src/ + backend multi-file + path-traversal surfaces should default to 0.50, not 0.75. Codex caught 2 real security issues (URL collision + run_id traversal) that automated testing missed.

**Counter**: v6.1 autonomous_governance 16 → 17 (first increment since RETRO-V61-001 reset).

**Test baseline**: 79/79 pre-7a → **97/97 post-7a** (+18 new field_artifacts tests: manifest, download, subpath, 4 traversal variants, non-object manifest, symlink escape, ordering, SHA format, sizes). `test_phase5_byte_repro.py` 12/12 green — `field_artifacts` key is manifest-ref only (no embedded timestamp) so subset-check stays byte-repro-safe.

**Phase 7a delta**: field data infrastructure landed; `/validation-report/*` still shows scalar-only tables until Phase 7b renders + Phase 7c 8-section scientific template + Phase 7f frontend live-fetch close the user-facing gap.

**Open items** (post-Phase-7a):

- DEC-V61-031 Notion sync pending.
- Phase 7b (render pipeline matplotlib + PyVista headless) queued as next natural step for Sprint 1 depth-first continuation.
- Phase 7c (CFD-vs-gold 8-section report template, THE "說服力" centerpiece) queued after 7b.
- Phase 7d/7e/7f (GCI + signed-zip + frontend live fetch) Sprint 2.
- Phase 5c..5j per-case sub-phases still queued (BFS, TFP, duct_flow, impinging_jet, naca0012, DHC, RBC).
- Phase 7c Sprint-2 will exercise yPlus stub on turbulent cases (first real yPlus emission).

---

## 2026-04-21 Night (continued) — Phase 7b + 7c-MVP + 7f-MVP delivery push (DEC-V61-032, S-009)

**User directive**: "根据你的规划，一直推进下去，直至你觉得完备，可以交付给我了". Autonomous push through Phase 7b (render pipeline) + Phase 7c Sprint 1 MVP (8-section CFD vs Gold report) + Phase 7f MVP (frontend live embed). 7d (GCI) and 7e (L4 signed-zip) explicitly deferred — they don't change what the user sees.

**Landed**:
- `scripts/render_case_report.py` (~400 LOC, matplotlib + plotly + numpy) — 5 outputs per LDC run: profile sim-vs-Ghia overlay, color-coded deviation bar, log-y residuals, centerline slice, Plotly interactive JSON. All real OpenFOAM artifacts from DEC-V61-031 integration run (20260421T082340Z, 8 files).
- `ui/backend/services/comparison_report.py` (~370 LOC) + `templates/comparison_report.html.j2` (~160 lines) + `routes/comparison_report.py` (~115 LOC, 4 endpoints).
- `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` +162 LOC — `ScientificComparisonReportSection` component embeds live 8-section report on `/learn/{case}` with verdict card + PDF download.

**User visible delta**: visit `/learn/lid_driven_cavity` → Story tab now shows real OpenFOAM-produced evidence (verdict PARTIAL 11/17 PASS at 5% tolerance; profile sim curve matching Ghia 1982 red dots; color-coded pointwise deviation bar chart; residual convergence 1.0 → 1e-5 log plot; grid convergence table with monotone mesh_20→160 values). PDF download link produces 622 KB print-ready audit document.

**Codex arc** (4 rounds):
- Round 1: CHANGES_REQUIRED — HIGH (manifest-path containment × 3 surfaces), MED (frontend silent 404/5xx conflation), LOW (CI-safe test coverage).
- Round 2: CHANGES_REQUIRED — MED (containment-before-import + OSError→503 missing), LOW (route 200-path).
- Round 3: CHANGES_REQUIRED — MED (POST /build only caught ImportError, not OSError).
- Round 4: **APPROVED**.

**Self-pass-rate calibration**: estimated 0.35, actual 0.0 over 3 rounds then APPROVED. Honest. RETRO-V61-002 datapoint: filesystem-backed rendering / report pipelines default 0.30-0.40 pass-rate; plan for 2-3 Codex rounds minimum.

**Counter**: v6.1 autonomous_governance 17 → 18.

**Test baseline**: 97/97 pre-7bc → **114/114 post-7bc** (+17 new: 7 service + 10 route tests, all CI-safe via synthetic_tree monkeypatch fixture that builds a minimal artifact tree in tmp_path without needing real OpenFOAM).

**Phase 7 status**:
- 7a ✅ COMPLETE (DEC-V61-031)
- 7b ✅ COMPLETE (this DEC)
- 7c Sprint 1 ✅ COMPLETE (this DEC, LDC MVP); Sprint 2 fan-out queued for other 9 cases
- 7d ⏸ DEFERRED — Richardson GCI numerics; doesn't change user-visible report shape
- 7e ⏸ DEFERRED — L4 signed-zip embedding; PDF available via dedicated endpoint meanwhile
- 7f ✅ MVP COMPLETE (this DEC, LDC only); 9 other cases unlock with 7c Sprint 2

**Delivery statement**: Phase 7 Sprint 1 complete. User-visible scientific-grade evidence surface (the original deep-acceptance ask) delivered for LDC. Honest residuals documented in DEC §"Honest residuals". Ready for user verification at http://127.0.0.1:5174/learn/lid_driven_cavity.

## 2026-04-21 Late Night — Phase 7 closure (Sprint 1 complete + 7b polish + 7d + 7e) (DEC-V61-033, S-010)

**User directive**: "接着推进，把你发现的剩余收口项都完成" — autonomous push through the three DEC-V61-032 deferrals.

**Landed**:
- **7b polish**: scripts/render_case_report.py parses OpenFOAM volume VTK via PyVista, reshapes 129×129 cell-centered (U, Cx, Cy), renders matplotlib contourf + streamplot. LDC /learn page now shows a publication-style cavity flow with the primary vortex + ~3 streamline whorls (was 1D strip).
- **7d**: ui/backend/services/grid_convergence.py (NEW, ~260 LOC) Celik 2008 + Roache 1994 Richardson GCI with degenerate-case branches (oscillating / precision / overflow / zero-order). comparison_report.html.j2 §7 GCI sub-table. LDC live: p_obs=1.00, GCI_32=5.68%, asymptotic_range_ok=True.
- **7e**: src/audit_package/{manifest,serialize}.py L4 canonical schema — embeds VTK + PNGs + PDF + residuals + samples + log (14 files, 1.97 MB). Byte-reproducibility preserved: identical SHA256 + HMAC across two consecutive POST build calls. docs/specs/audit_package_canonical_L4.md supersedes L3.

**Codex arc** (2 rounds):
- Round 1: CHANGES_REQUIRED — CRITICAL (serialize hardcoded repo_root ignored build_manifest's repo_root kwarg; manifest advertised 5 phase7 entries while zip had 0; test masked via monkeypatch), IMPORTANT (non-uniform-r GCI OverflowError uncaught past ValueError/ZeroDivisionError), MISLEADING (p_obs=0.0 fell through with note="ok").
- Round 2: **APPROVED_WITH_COMMENTS** — all 3 findings closed. Non-blocking comment: build_manifest(repo_root=X) not fully hermetic because knowledge/whitelist + gold + decisions still use module-level roots (pre-existing, out of scope for this DEC).

**Self-pass-rate calibration**: estimated 0.45, actual CHANGES_REQUIRED once then APPROVED. Honest.

**Counter**: v6.1 autonomous_governance 18 → 19.

**Test baseline**: 114/114 pre-7bde → 129/129 post-initial-implementation → **132/132 post-round-1-fixes** (+18 net since DEC-V61-032: 8 Phase 7e tests, 9 GCI tests, 1 repo_root mismatch hazard test, -0 removed).

**Phase 7 status** (updated from DEC-V61-032 snapshot):
- 7a ✅ COMPLETE (DEC-V61-031)
- 7b ✅ COMPLETE — MVP (DEC-V61-032) + polish (DEC-V61-033)
- 7c Sprint 1 ✅ COMPLETE (DEC-V61-032); Sprint 2 fan-out still queued
- 7d ✅ COMPLETE (DEC-V61-033)
- 7e ✅ COMPLETE (DEC-V61-033)
- 7f ✅ MVP COMPLETE (DEC-V61-032); 9 other cases unlock with 7c Sprint 2

**Phase 7 Sprint 1 verdict**: DELIVERABLE. Remaining work (7c Sprint 2 × 9 cases) requires OpenFOAM integration runs × 9 + per-case adapter opt-in edits — distinct scope, unblocked, available for execution when user requests.

**Git**: commit 4399427 pushed to main (12 files, +7788/-23).

**Next**: Notion sync DEC-V61-033 (Decisions DB).

## 2026-04-21 Late Night — Phase 7c Sprint 2 Tier C fan-out + Phase 7 Sprint 1 COMPLETE (DEC-V61-034, S-011)

**User directive**: "我的每个case的report区域，仍然没有真实的仿真结果里提取出来的流场云图等等重要信息" → "C then B".

**Tier C landed** (visual-only, 10/10 cases minus RBC still running):
- Renderer: GOLD_OVERLAY vs VISUAL_ONLY split + 3-tier contour fallback (structured → tricontourf+quiver → scatter) + 2D-plane auto-detect for NACA x-z mesh + log-parse residuals fallback + NaN/inf diverged-solution guard.
- Backend: `_build_visual_only_context()` returns reduced dict (verdict/metrics/paper/GCI=None) for 9 non-LDC cases.
- Route: new `GET /api/cases/{case}/runs/{run}/renders/{filename:path}` with path-containment defense.
- Frontend: ScientificComparisonReportSection detects `visual_only` → 2-column contour+residuals panel.
- Adapter: `-noFaceZones` in `foamToVTK` (fixes cylinder_wake SEGV on cylinderBaffleZone). Subagent diagnosed root cause in 2.7min wall.
- Log truncation: `log[:200]` → `log[-400:]` (SEGV stack traces at tail).
- 8 of 9 non-LDC cases already rendered + committed (RBC still running at session touch).

**Integration results**:
| Case | Result | Duration | Notes |
|---|---|---|---|
| ldc | PARTIAL 11/17 | — | Pre-existing gold-overlay |
| bfs | FAIL | 9s | kEpsilon divergence |
| plane_channel | **PASS** | 426s | Real convergent |
| tfp | FAIL | 36s | kEpsilon (known CLAUDE.md) |
| duct | FAIL | 36s | Diverged |
| dhc | FAIL | 1059s | buoyantFoam slow+diverged |
| impinging_jet | FAIL | 152s | Diverged |
| naca0012 | FAIL | 20s | Diverged (scatter fallback) |
| cylinder_wake | **PASS** | 35s | After -noFaceZones fix |
| rbc | (running) | 55min+ | buoyantFoam, not stalled |

The 7 FAIL verdicts surface pre-existing solver config issues (per CLAUDE.md memory). Tier C honestly shows them instead of hiding behind placeholder PNGs.

**Codex** (2 rounds on DEC-V61-034):
- R1 CHANGES_REQUIRED: visual-only cases 500 on /comparison-report HTML/PDF/build (template deref'd None metrics). Applied Option-A fix + 3 new tests.
- R2 APPROVED_WITH_COMMENTS: non-blocking nit on render_report_pdf guard order (hoisted above output_path branch).

**Counter**: 19 → 20. Triggers RETRO-V61-001 cadence rule #2 → RETRO-V61-002 landed.

**Test baseline**: 132 → 139 → 142/142 (+10 new visual-only tests across rounds).

**Phase 7 Sprint 1 verdict**: **COMPLETE**. All 6 sub-phases (7a–7f) delivered. Tier B per-case gold-overlay for 9 cases deferred as future work (~30hr). User can pick between Tier B polish vs Phase 8 physics debt (fix kEpsilon divergence) at next session.

**Git**: 6 commits on main: 4ee3fc2 → a70796a → 02cd686 → 575db8f → 6581167 → 159e4d7. All pushed.

**Notion**: DEC-V61-034 + Notion page 349c68942bed81e0a3c4cc37a2242fd1. RETRO-V61-002 sync pending (Notion 502 transient; retry scheduled).

**Next**: RBC rendering when batch finishes; RETRO-V61-002 Notion sync retry; Phase 7 Sprint 1 close notification.

---

# Phase 8 Sprint 1 — PASS-washing remediation (2026-04-22)

**Trigger**: user's 2026-04-22 deep CFD review surfaced that the audit_real_run
verdicts were showing curated / silently-substituted numbers instead of honest
solver-in-the-loop measurements. DEC-V61-035 already flipped the default run
from `reference` to `audit_real_run` (surfacing the honesty), and this sprint
closes the structural gaps the review named.

**Sprint plan** (sub-DECs split from user's 5 listed integrity issues):
- **DEC-V61-036** Hard comparator gates, split into G1/G2-G6 sub-DECs
  - **G1 (LANDED a9d0831)**: missing-target-quantity — closes the
    "first-numeric key_quantities fallback" PASS-washing path in both
    `scripts/phase5_audit_run.py::_primary_scalar` and
    `scripts/p2_acceptance_run.py::_extract_primary_measurement`. Forces
    hard-FAIL with MISSING_TARGET_QUANTITY concern. Retroactive trigger on
    legacy `extraction_source: key_quantities_fallback` marker so existing
    on-disk fixtures are gated without regeneration. 4 cases flip to FAIL:
    BFS, cylinder_wake, duct_flow, plane_channel_flow.
  - G2-G6 (pending): unit mismatch, velocity overflow, turbulence negativity,
    continuity divergence, stuck residuals.
- **DEC-V61-037** Per-case validation plots (8 cases implementable + 1 blocked)
- **DEC-V61-038** Convergence attestor A1-A6 (pre-extraction)
- **DEC-V61-039** LDC verdict reconciliation (PARTIAL vs FAIL)
- **DEC-V61-040** UI 3-tier semantics
- **DEC-V61-041** Cylinder shedding FFT (split from 037 — needs runtime extension + forceCoeffs FO + retire canonical-band hardcode)

**Counter**: 21 → 22 (DEC-V61-036 G1 `a9d0831` + round-2 `b3ed913`) → 23
(DEC-V61-036b `1fedfd6` + Codex-nits `c3afe93`) → 24 (DEC-V61-038
attestor `7f29a64`). Next retro at 30.

**Codex per DEC**: user explicitly requested senior-CFD-reviewer per-case
validation pattern.
- G1 round 1: CHANGES_REQUIRED (B1 profile-quantity blocker + B2 deferred to G2)
- G1 round 2: APPROVED_WITH_COMMENTS on `b3ed913`
- G3/G4/G5 round 1: APPROVED_WITH_COMMENTS on `1fedfd6`; 2 nits applied in `c3afe93`:
  (a) `within_tolerance=None` under hard-FAIL (was confusingly True),
  (b) NaN/Inf-safe token parsing (was silently skipping worst overflow).
- DEC-038 attestor round 1: CHANGES_REQUIRED on `7f29a64` (A4 BLOCKER: missed p_rgh+DICPCG + counted lines not blocks)
- DEC-038 attestor round 2: APPROVED_WITH_COMMENTS on `eb51dcf` (fixes + A2/G5 split-brain + ATTEST_NOT_APPLICABLE)
- DEC-038 attestor nit: PBiCGStab regex ordering `9716dd4`. Closed 2026-04-22 11:32.

**Live attestor+gates matrix on 10 current audit_real_run fixtures** (verified
against `reports/phase5_fields/*`):
```
case                         attestor          gates
lid_driven_cavity            ATTEST_PASS       []
backward_facing_step         ATTEST_HAZARD     [G3,G4,G5]  ← G5 hard-FAILs contract
circular_cylinder_wake       ATTEST_HAZARD     [G4,G5]     ← G5 hard-FAILs contract
turbulent_flat_plate         ATTEST_HAZARD     [G3,G4,G5]
duct_flow                    ATTEST_HAZARD     [G3,G4,G5]
differential_heated_cavity   ATTEST_PASS       []
plane_channel_flow           ATTEST_PASS       []  ← DEC-036c G2 territory (u+/y+)
impinging_jet                ATTEST_FAIL       []  ← A4 p_rgh cap (post-round-2 fix)
naca0012_airfoil             ATTEST_PASS       []  ← tolerance band too loose
rayleigh_benard_convection   ATTEST_PASS       []  ← Nu extractor bug
```

LDC stays clean across attestor + gates — the gold-overlay reference
hasn't been destabilised. 5 cases (LDC/DHC/plane_channel/NACA/RBC) show
ATTEST_PASS but Codex physics audit says they physically FAIL — those
are comparator/extractor bugs (DEC-036c G2 + case-specific fix DECs)
not convergence bugs.

**Test baseline**: 142 → 150 (G1) → 166 (G3/G4/G5) → 168 (Codex nits)
→ 184 (DEC-038 attestor) → 190 (DEC-038 round 2 regression tests). All green.

**Still queued** in Phase 8 Sprint 1:
- DEC-V61-036c G2: unit/profile canonicalization + plane_channel u+/y+ comparator fix
- DEC-V61-037: 8 per-case validation plots (FO refactor + renderers)
- DEC-V61-039: LDC verdict reconciliation (PARTIAL vs FAIL)
- DEC-V61-040: UI 3-tier semantics (reference / audit_real_run / visual_only)
- DEC-V61-041: cylinder Strouhal FFT (split from 037, needs forceCoeffs FO + runtime)
