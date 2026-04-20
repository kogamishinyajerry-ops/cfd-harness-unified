---
decision_id: DEC-V61-008
timestamp: 2026-04-20T22:00 local
scope: Path B · C3b · NACA 0012 gold-anchored Cp sampleDict (second of 3 C3 PRs). Extends _generate_airfoil_flow to emit system/sampleDict at 3 upper-surface x/c coordinates from whitelist reference_values. Reuses C3a helpers (_load_gold_reference_values, _emit_gold_anchored_points_sampledict).
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 11b356ac` removes the generator tail-patch and
  the 4 new tests. No new helpers added by this PR — C3a helpers
  remain intact. No whitelist, gold_standards, or adapter result-
  harvest changes.)
notion_sync_status: synced 2026-04-20T22:05 (https://www.notion.so/348c68942bed81199a97c008e93eb419) — Decisions DB page created with Scope=Project, Status=Accepted, Canonical Follow-up=PR #8 URL
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/8
github_merge_sha: 11b356ac0d52ba518d387036c95adf7b2b947e96
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 97%
  (Pure src/ + tests/ change. 175/175 regression green. Reuses C3a
  helpers without modifying them, so no cross-cutting risk. Design
  doc pre-landed — deviation from §3.2 is explicit: Option B chosen
  over Option A with reason recorded in commit message and PR body.)
supersedes: null
superseded_by: null
upstream: DEC-V61-007 (C3a — established the shared helpers)
design_doc: docs/c3_sampling_strategy_design.md
---

# DEC-V61-008: C3b · NACA 0012 gold-anchored Cp sampleDict

## Decision summary

Second of three planned C3 PRs. Adds a `type points` sampleDict to the NACA 0012 airfoil generator at the 3 upper-surface locations corresponding to whitelist `reference_values` x/c coordinates.

| x/c | Physical (x, y, z) | Field |
|---|---|---|
| 0.0 | (0, 0, 0) — leading edge | p |
| 0.3 | (0.3·chord, 0, half_thickness(0.3)·chord) | p |
| 1.0 | (chord, 0, 0) — trailing edge | p |

Set name: `airfoilCp`. Axis: `x`. Header records `chord` and `U_inf` for downstream Cp conversion traceability (`Cp = (p - p_inf) / (0.5·U_inf²)`).

## Design choice — Option B over Option A

Design doc §3.2 flagged Option A (`surfaces` function-object) as "preferred" for asymmetric / non-zero AoA cases. This PR implements **Option B** (`sets` + `type points` at upper-surface coords) because:

1. **Adapter doesn't implement AoA rotation** — the current code uses a fixed OBJ surface aligned with the x-axis. Non-zero AoA is untested/unsupported.
2. **NACA 0012 at AoA=0 is symmetric** → upper-surface Cp mirrors lower-surface; sampling upper alone captures the full distribution.
3. **Option B reuses C3a helpers directly** (`_load_gold_reference_values`, `_emit_gold_anchored_points_sampledict`) without adding a new surfaces-dict emitter. Keeps PR scope small.
4. **Option A would have required adapter result-harvest changes** (VTK parsing, arclength interpolation) that are orthogonal to the sampling-side question this PR addresses.

If the adapter ever adds AoA support, Option A becomes the correct upgrade path.

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (DEC-V61-003 turf) | YES — generator tail-patch, ~40 LOC |
| `tests/` | YES — +4 new tests |
| `knowledge/**` | NOT TOUCHED |
| Notion DB destruction | NOT TOUCHED |

## Regression

```
pytest 7-file matrix → 175 passed in 1.02s
```

171 baseline (post-C3a) + 4 new:
- `TestNaca0012GoldAnchoredSampling × 4`: whitelist-name trigger, off-whitelist no-op, chord scaling, header metadata (chord + U_inf).

## Non-goals

- **Post-harvest Cp interpolation** from raw sample output — belongs in a follow-up PR once all 3 C3 generators land. At that point the result-harvester can be refactored once, consistently, across LDC / NACA / IJ.
- **AoA rotation** — out of C3 scope.
- **Lower-surface sampling** — only needed for non-zero AoA.
- **Surfaces function-object** (Option A) — documented as future upgrade path.

## Next

- **C3c** — Impinging Jet `wallHeatFlux` function-object on impingement plate + Nu-from-q conversion. ~180 LOC. Last of 3 C3 PRs. Will land as DEC-V61-009.
- After C3c: potential follow-up PR for result-harvest side (Cp interpolation, Nu post-processing) if dashboard validation exposes gaps.
- §5d dashboard validation still gated on Docker daemon.

## Reversibility

One `git revert -m 1 11b356ac` removes the generator tail-patch and 4 tests. C3a helpers (introduced in DEC-V61-007) remain intact — they're generator-agnostic. No cross-cutting changes.
