---
session: 2026-04-27
session_page: https://www.notion.so/34fc68942bed81e4a691f4df136c48fe
review_source: Notion-Opus 4.7 post-hoc strategic sanity review
review_verdict: APPROVE_WITH_COMMENTS · counter +0 · advisory only
date: 2026-04-27
---

# Session 2026-04-27 follow-up backlog

Captures the four P2 advisory items from Notion-Opus's review.
**Action taken on the P1 (§3) is in `DEC-V61-088` (Status=Proposed)**;
this file is for the P2 items that don't warrant a DEC.

---

## P2 §1 · BUG-1 cancelled-exec_task integration smoke test

**Source**: review §1 last paragraph

**Concern**: cancelled-exec_task regression test was attempted in
`test_run_compare.py` but removed as brittle (asyncio.run + to_thread
+ thread-pool teardown ordering inside asyncio.run = loop-internal
mechanics; the test was racy). The defensive callback branch is small
+ has rationale comment, but the BUG-1 core regression path
(consumer-disconnect-doesn't-lose-verdict) is currently only covered
by the in-process unit test in `test_wizard_drivers.py::test_real_driver_consumer_disconnect_still_persists`.

**Notion-Opus suggestion**:
> 把这条路径改成 integration-style smoke (直接起 FastAPI TestClient +
> 提前断 SSE consumer + 验证 verdict.json 落地)

**Disposition**: backlog item · routine path. When next refactoring the
wizard tests OR if a BUG-1-class regression is suspected, write an
integration test that:
1. Starts a `TestClient` against `ui.backend.main:app`
2. Mocks `FoamAgentExecutor.execute` to return after a controllable delay
3. Initiates an SSE request, lets it run for N events, then disconnects
   the client mid-stream
4. Asserts `reports/<case>/runs/<run>/verdict.json` lands within timeout

**Owner**: next BUG-1-adjacent change in `wizard_drivers.py` triggers it.

---

## P2 §2 · CYLINDER-PHYSICS-1 follow-up tracker

**Source**: review §2

**Concern**: Notion-Opus accepts the YELLOW→GREEN reclassification (St
within 25% case_profile tolerance), but warns that:
> 25% 是 ceiling, 不是 floor — DEC-V61-053 R4 之后任何"再放宽"必须新开
> DEC, 不能 silent edit
> 应该开 CYLINDER-PHYSICS-1 follow-up tracker (scope = "St 系统性 -15%
> 偏低是否网格/时间步可解决"), 即使在 25% 容差下也跟踪

**Disposition**: open as a tracked follow-up, but NOT a DEC (no
governance change needed). File:
`.planning/case_profiles/circular_cylinder_wake.yaml::known_systematic_deviations`
(new section to add when next touching this case profile):

```yaml
known_systematic_deviations:
  - quantity: strouhal_number
    measured_dev_pct: -15.9  # at 2026-04-27T07-23-21Z run
    within_tolerance: true   # 25% per DEC-V61-053 R4
    candidate_root_causes:
      - boundary_layer_mesh_resolution_at_y_plus_max_above_cylinder_surface
      - domain_blockage_8pct_may_still_be_too_narrow_at_Re=100
      - transient_trim_2s_may_be_too_short_for_full_settling
      - numerical_diffusion_in_default_linearUpwind_grad_U_div_scheme
    investigation_status: deferred
    deferred_to_phase: 8 (case-quality sweep)
    notes: |
      Cd=0.01256 matches Williamson 1996 within 1.5%, suggesting
      mesh + numerics produce correct mean drag but under-resolve
      the wake periodicity. Worth bumping CYLINDER_ENDTIME_S 10→60s
      first (per DEC-V61-053 comment for ΔSt/St ≈ 3% precision)
      before refining mesh — cheaper diagnostic.
```

**Lock-in clause** (also in the same file): comment that says
"`tolerance_policy.strouhal_number.tolerance` is a ceiling, not a
floor; further relaxation requires a new DEC, not silent edit."

**Owner**: next time `circular_cylinder_wake.yaml` is touched.

---

## P2 §4 · `codex_arc_log.csv` Codex-arc telemetry

**Source**: review §4

**Concern**: 0/2 first-pass APPROVE in this session is N=2, statistically
meaningless. But should *start counting* now so when N≥10 we have data
to calibrate DEC-V61-087 §5's 0.55 self-pass-rate estimate.

**Disposition**: ops hygiene, not a DEC. Establish telemetry file:
`.planning/governance/codex_arc_log.csv` with header:

```
arc_id,date,artifact_path,first_pass_verdict,total_rounds,p0_count,p1_count,p2_count,final_verdict,notes
```

Backfill the 2 arcs from this session:

```
bug1_sse_disconnect_persistence,2026-04-27,ui/backend/services/wizard_drivers.py,CHANGES_REQUIRED,3,0,1,1,APPROVE_WITH_COMMENTS,session 2026-04-27 first arc
run_compare_api,2026-04-27,ui/backend/services/run_compare.py,CHANGES_REQUIRED,2,0,2,2,APPROVE_WITH_COMMENTS,session 2026-04-27 second arc
```

Calibration trigger: when row count ≥ 10 OR counter ≥ 20 (whichever
first), calibrate `first_pass_rate = sum(first_pass_verdict in {APPROVE,
APPROVE_WITH_COMMENTS}) / N`. If significantly off from DEC-V61-087's
0.55 design estimate, write to next RETRO recommending §5 threshold
update.

**Owner**: maintained by Claude Code as part of every Codex arc closeout
(append a row when committing the final review report). Backfill the
2 above when next touching `.planning/governance/`.

---

## P2 §5 · Cadence wording in startup prompts

**Source**: review §5

**Concern**: User repeatedly overrode my "stop here" recommendations in
this session (4× "继续"). Notion-Opus reads this as "user cost function
prioritizes context continuity over session-切分整洁度" — my stop-推荐
判断 not wrong, but the *wording* should change.

**Notion-Opus suggestion**:
> 改为 "natural checkpoint reached — 可在此处 commit + push;若继续推进,
> 下一目标推荐 X"

**Disposition**: behavioral change, no DEC needed. Apply to next session's
end-of-task summaries:
- ❌ "Recommended: stop here. Next session can do X."
- ✅ "Natural checkpoint reached at <commit>. If continuing, next concrete
  target: X."

This preserves the "stop candidate point" signal but doesn't push back
on the user's clear cost-function signal.

**Owner**: ongoing tone adjustment, no artifact.

---

## Summary table

| § | Severity | Type | Action |
|---|---|---|---|
| §1 | P2 | regression test | backlog: integration smoke when next BUG-1-adjacent change |
| §2 | P2 | case-quality | inline `known_systematic_deviations` next time touching `circular_cylinder_wake.yaml` |
| §3 | **P1** | methodology | **DEC-V61-088 drafted (Status=Proposed)** — awaits Kogami review |
| §4 | P2 | ops hygiene | `codex_arc_log.csv` telemetry; backfill 2 session arcs next time touching `.planning/governance/` |
| §5 | P2 | cadence | tone change in stop-recommendations |
