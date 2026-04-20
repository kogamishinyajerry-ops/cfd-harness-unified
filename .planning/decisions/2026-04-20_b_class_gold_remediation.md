---
decision_id: DEC-V61-006
timestamp: 2026-04-20T21:15 local
scope: Path B · B-class gold-value remediation (3 of 5 Gate Q-new cases accepted · 2 held). Edits `knowledge/whitelist.yaml` `reference_values` + `parameters` + associated `knowledge/gold_standards/*.yaml` observable `ref_value` + physics_contract for Cases 4 (Turbulent Flat Plate), 6 (DHC — closes Q-1 with P-2), and 8 (Plane Channel). Cases 9 (Impinging Jet) and 10 (Rayleigh-Bénard) held pending literature re-source.
autonomous_governance: false  # external-gate decision, Kogami approved
claude_signoff: yes
codex_tool_invoked: false  # Kogami review was the external gate; Codex not re-dispatched
codex_diff_hash: null
codex_tool_report_path: null
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 <merge-sha>` restores pre-gate whitelist +
  gold_standards state. No adapter code changes, no test deletions —
  158/158 regression held green before and after. Reversal loses three
  gold improvements but gains back Q-1 open state. No dependent
  artifacts are invalidated by reversal.)
notion_sync_status: synced 2026-04-20T21:25 (https://www.notion.so/348c68942bed816d8ebec369963791c2) — Decisions DB page created with Scope=Project, Status=Accepted, Canonical Follow-up=PR #6 URL, body covers per-case decisions + honest miscalculation catch + Q-1 closure
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/6
github_merge_sha: 912b2ce124581ecb9afd1ada4528c6da913da979
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_approval: Kogami approved 2026-04-20 via direct session instruction ("全都按你推荐来" → "按这个修正计划执行"). Gate decision surface from `.planning/gates/Q-new_whitelist_remediation.md`; per-case A/P/C/D selection:
  Case 4: A (Blasius laminar substitution)
  Case 6: P-2 (Ra=1e10 → Ra=1e6 de Vahl Davis benchmark) — subsumes Q-1
  Case 8: A (u+@y+=30: 14.5 → 13.5 per Moser 1999 log-law)
  Case 9: C (hold — literature re-source pending; audit discrepancy 4-5× too large to edit without Behnad 2013 paper verification)
  Case 10: C (hold — audit's initial "Chaivat gives 7.2" was a miscalculation; recompute gives 9.4, current 10.5 is 11.5% off vs description's own correlation, within 15% tolerance; Chaivat 2006 paper re-read pending)
supersedes: null  # Does not supersede Q-1 formally; DEC-ADWM-004 P-2 path adopted here → Q-1 closes
superseded_by: null
upstream: DEC-V61-004 (C1+C2 infra fixes) · DEC-V61-005 (A-class metadata) · DEC-ADWM-004 (Q-1 hard-floor record, now resolved by this DEC's Case 6 P-2)
---

# DEC-V61-006: B-class gold-value remediation (Cases 4, 6, 8 accepted · Cases 9, 10 held)

## Decision summary

Gate Q-new filed in prior session (`.planning/gates/Q-new_whitelist_remediation.md`) requested per-case A/B/C/D decisions for 5 audit-identified gold-value discrepancies. Kogami approved "全都按推荐来" after a mid-deliberation retraction where Claude caught its own Case 10 miscalculation (`Chaivat at Ra=1e6` gives 9.4, not 7.2 as original audit claimed) and revised the recommendation to **3 edits + 2 holds**:

| Case | Decision | Change |
|---|---|---|
| 4 Turbulent Flat Plate | A (Blasius) | turbulence_model SST → laminar; Cf@x=0.5: 0.0076→0.00420; Cf@x=1.0: 0.0061→0.00297; reference + description + source updated |
| 6 Differential Heated Cavity | P-2 (regime downgrade) | Ra: 1e10→1e6; Nu@Ra=1e6: 30→8.8 (de Vahl Davis 1983); turbulence_model SST→laminar; **closes Q-1** |
| 8 Plane Channel | A (Moser 13.5) | u+@y+=30: 14.5→13.5 (log-law (1/0.41)·ln(30)+5.2=13.49); others untouched |
| 9 Impinging Jet | C (hold) | Added HOLD comment block; no edit. 25→~115 audit-proposed delta too large without Behnad 2013 paper verification |
| 10 Rayleigh-Bénard | C (hold) | Added HOLD comment block; no edit. Current 10.5 is within 15% tolerance of description's Chaivat correlation (9.4); Chaivat 2006 re-read pending |

## Honesty note — why Case 10 got de-escalated

During pre-flight verification the driver caught its own audit error:
- **Audit claim (original, Q-new doc)**: "Chaivat correlation at Ra=1e6 gives 7.2"
- **Manual recompute during PR #6 preflight**: `0.229 × (10^6)^0.269 = 0.229 × 41.12 = 9.41`
- **Conclusion**: audit was wrong by 30%. Current whitelist gold 10.5 is 11.5% off the correlation's own evaluation — within the 15% tolerance. Not a confident edit candidate.

The driver paused, reported the error to Kogami, and proposed reducing the scope from 5 edits to 3. Kogami approved the revised 3-edit plan. This interaction is **on-record** as an example of pre-flight audit re-verification catching an error before it landed as a Gate-approved edit.

## 禁区 compliance

| Area | Touched? |
|---|---|
| #1 `src/` and `tests/` | NOT TOUCHED |
| #2 `knowledge/gold_standards/**` — **EXTERNAL GATE (now approved)** | TOUCHED: turbulent_flat_plate.yaml + differential_heated_cavity.yaml + plane_channel_flow.yaml per Gate Q-new decision |
| #3 `knowledge/whitelist.yaml` `reference_values` + `parameters` — **EXTERNAL GATE (now approved)** | TOUCHED: 4 entries modified (Cases 4, 6, 8, 9-comment, 10-comment) per Gate Q-new decision |
| #4 Notion DB destruction | NOT TOUCHED (one new page creation only) |

Both #2 and #3 were explicitly authorized by Gate Q-new approval from Kogami. This is **not** an autonomous action — `autonomous_governance: false` reflects this. The DEC serves as the landing record + Notion mirror seed.

## Regression

```
pytest tests/test_foam_agent_adapter.py tests/test_result_comparator.py \
       tests/test_task_runner.py tests/test_e2e_mock.py \
       tests/test_correction_recorder.py tests/test_knowledge_db.py \
       tests/test_auto_verifier -q
→ 158 passed in 0.94s
```

Fixtures do not hard-code specific Cf/Nu/u+ numbers; they reference the whitelist entries by id and accept whatever gold the whitelist declares. Changing gold values therefore does not break tests under MOCK executor mode.

## Expected dashboard impact

- **Case 4 Turbulent Flat Plate**: Previous regime was mis-specified (SST + turbulent Spalding at Re_x=25000 laminar region). Adapter may have been Spalding-fallback-firing silently. Under laminar contract with mesh-resolved Blasius extraction, Cf should match 0.00420 within 10% organically. If extraction fails the gap will be real (not formula-substituted), making the PASS/FAIL signal honest for the first time.
- **Case 6 DHC**: Prior Nu=5.85 measurement vs Nu=30 gold was ~80% under-prediction. At Ra=1e6 with gold=8.8, adapter's existing 40-80 cell mesh is sufficient and mesh-resolved Nu should land in 7.5-9.0 range → within 10% tolerance. Strong candidate for HAZARD→PASS flip.
- **Case 8 Plane Channel**: Prior u+@y+=30 gap was 14.5 vs adapter output; if adapter returns correct log-law (~13.5) the new gold will match within 5% tolerance. Strong candidate for PASS.

Net dashboard prediction for post-PR #6 state: 3 cases newly viable for PASS (Case 4 if adapter extraction clean; Case 6 almost certain; Case 8 almost certain), plus Cases 1 (LDC) and 10 (Rayleigh-Bénard post A-class) already reasonable. Target ≥5 PASS from §2 now achievable.

## Q-1 closure

DEC-ADWM-004 FUSE record filed 2026-04-18 with Q-1 as hard-floor #1 (DHC gold accuracy at Ra=1e10). This DEC's Case 6 adoption of **Path P-2** (regime downgrade to Ra=1e6) is one of the two decision paths DEC-ADWM-004 explicitly named. Q-1 closes with this DEC.

Post-merge: update `.planning/external_gate_queue.md` §Q-1 header with `~~` strike-through + closure note pointing to DEC-V61-006.

## Rejected alternatives

1. **Edit all 5 cases per original audit numbers** — REJECTED pre-flight: Case 10 audit number was a miscalculation (actual Chaivat at Ra=1e6 = 9.4, not 7.2). Landing a wrong number silently would have been worse than filing a gate for autonomous gold edit authority.
2. **Keep current DHC Ra=1e10 (Path P-1)** with Nu re-sourced to 120–160 literature range and tolerance widened to 25% — REJECTED: Path P-2 (Ra downgrade) is simultaneously more physical (40-80 cells is adequate at Ra=1e6, infeasible at Ra=1e10), smaller (one numerical edit vs. adapter mesh overhaul), and more canonical (de Vahl Davis 1983 is a textbook benchmark cited >40×).
3. **Bundle Case 9 into this PR with a rough Behnad-2013 number** — REJECTED: the 4-5× discrepancy between current 25 and audit-proposed ~115 is too large to "commit-and-adjust". Reading the Behnad paper first is cheap insurance. Case 9 stays HOLD with visible TODO comment.
4. **Edit Case 10 Nu → 9.4** (exact Chaivat evaluation) — REJECTED: Chaivat 2006 paper almost certainly cites a specific Nu measurement or different correlation not identical to `Nu = 0.229·Ra^0.269`. The description field's correlation is one of several in the paper; without re-reading we can't be sure 9.4 is the authoritative number.
5. **Fix y+=5 and y+=100 rows in plane_channel_flow along with y+=30** — REJECTED: the y+=100 row (22.8) does look anomalous (log-law gives ~16.4, Moser centerline ~18.3) and y+=5 (5.4) is ~10% off linear sublayer (5.0). Both are out of audit §5.2 scope and would expand a Gate-scoped decision without approval. Queued as follow-up. Inline comment flags the anomaly for future audit.

## Next steps (queued, not this DEC)

1. Commit + push this DEC + edits as PR #6.
2. On merge: mirror DEC-V61-006 to Notion Decisions DB; update DEC-ADWM-004 Notion page with closure note; strike Q-1 in external_gate_queue.md + add Q-new closure note.
3. §5d: full dashboard validation run to measure actual ≥5 PASS from §2.
4. Case 9 literature re-source (Behnad 2013) → future DEC-V61-007.
5. Case 10 Chaivat 2006 re-read → either DEC-V61-007 or folded into the same.
6. §5a C3 sampleDict auto-gen design session (deferred).
