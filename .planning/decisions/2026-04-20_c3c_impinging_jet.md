---
decision_id: DEC-V61-009
timestamp: 2026-04-20T22:20 local
scope: Path B · C3c · Impinging Jet gold-anchored Nu-probe sampleDict. Third and final C3 PR. Extends _generate_impinging_jet to emit system/sampleDict at r/d probe points 1mm above the impingement plate. Completes C3 sequence (LDC + NACA + IJ).
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 7e22545b` removes the IJ generator tail-patch and
  4 new tests. No new helpers added — C3a helpers remain intact. No
  whitelist, gold_standards, or controlDict/boundary touches.)
notion_sync_status: synced 2026-04-20T22:30 (https://www.notion.so/348c68942bed81039961f45fedef00aa) — Decisions DB page created with Scope=Project, Status=Accepted, Canonical Follow-up=PR #9 URL
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/9
github_merge_sha: 7e22545b3bba17044f3268c5d3002406147547b8
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 97%
  (Pure src/ + tests/ change. 179/179 regression green. Reuses C3a
  helpers without modifying them. Design-doc deviation (Option B over
  Option A) explicit with reason recorded — same pattern as C3b.)
supersedes: null
superseded_by: null
upstream: DEC-V61-007 (C3a helpers) · DEC-V61-008 (C3b NACA precedent for Option B)
design_doc: docs/c3_sampling_strategy_design.md
---

# DEC-V61-009: C3c · Impinging Jet gold-anchored Nu-probe sampleDict

## Decision summary

Third and final C3 PR. Appends gold-anchored sampleDict emission to `_generate_impinging_jet` at probe points 1mm above the impingement plate, using the r/d coordinates from whitelist `reference_values`.

| r/d | Physical (x, y, z) |
|---|---|
| 0.0 | (0, 0, 0.001) — stagnation probe above plate center |
| 1.0 | (D, 0, 0.001) = (0.05, 0, 0.001) |

Set name: `plateProbes`. Fields: `(T U)`. Axis: `x`. Header records `D`, `T_inlet`, `T_plate`, and a TBD marker for Nu derivation.

## Option B over Option A — reasoning

Design doc §3.3 preferred Option A (`wallHeatFlux` function-object). This PR implements **Option B** (probe `sets` + `type points`) because:

1. **Case 9 gold Nu values (25, 12) are on HOLD** per Gate Q-new C-verdict (Behnad 2013 paper paywalled; user confirmed PDFs inaccessible 2026-04-20). Sampling infrastructure is **orthogonal** to gold-value correctness and can land independently.
2. **r_over_d COORDINATES remain stable** regardless of Nu-value revision — Option B uses only the coords.
3. **Reuses C3a helpers unmodified** (like C3b did). No new helpers, no controlDict mutation, no adapter result-harvest changes.
4. **Option A (wallHeatFlux FO) would consolidate better with C3b's surfaces/Cp post-processing into a single result-harvest refactor PR** than with this generator-side infrastructure PR. Sequencing concern, not correctness concern.

Option A remains the preferred long-term design. It can be adopted later as a consolidated refactor covering C3b (Cp from surfaces output) AND C3c (Nu from wallHeatFlux output) together, with one review surface.

## C3 sequence completion

| PR | Scope | Merge | DEC |
|---|---|---|---|
| C3a | LDC 5-point centerline | `f0264a13` (PR #7) | V61-007 |
| C3b | NACA 3 upper-surface Cp probes | `11b356ac` (PR #8) | V61-008 |
| C3c | IJ 2-point plate Nu probes | `7e22545b` (PR #9) | V61-009 |

All three reuse the same two helpers (`_load_gold_reference_values`, `_emit_gold_anchored_points_sampledict`) introduced by C3a. Pattern is now established; any future case can adopt the same pattern with 10-20 LOC in its generator.

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (DEC-V61-003 turf) | YES — IJ generator tail-patch ~30 LOC |
| `tests/` | YES — +4 new tests |
| `knowledge/**` | NOT TOUCHED |
| Notion DB destruction | NOT TOUCHED |

## Regression

```
pytest 7-file matrix → 179 passed in 1.12s
```

175 baseline (post-C3b) + 4 new `TestImpingingJetGoldAnchoredSampling` tests covering: whitelist-id trigger, display-name trigger, off-whitelist no-op, header records D + T_inlet + T_plate + TBD.

## Next steps (queued)

1. **Result-harvest refactor** (cross-cutting, single PR): read back the three new sampleDict outputs and convert to comparator keys — LDC u_centerline (already working under C1 aliases), NACA Cp via (p-p_inf)/(0.5·U²), IJ Nu via wall-gradient derivation. This is the place to also decide whether to upgrade IJ to Option A (wallHeatFlux FO) at that time.
2. **§5d dashboard validation** — still gated on Docker daemon startup + OpenFOAM container availability.
3. **Case 9/10 literature re-source** — still HOLD pending paper access (user cannot obtain PDFs; both Elsevier paywalled).

## Reversibility

One `git revert -m 1 7e22545b` restores the IJ generator to its pre-C3c state. C3a helpers and C3b NACA code remain intact (they're independent). No cross-cutting impact.
