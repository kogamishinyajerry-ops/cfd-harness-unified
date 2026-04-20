---
decision_id: DEC-V61-010
timestamp: 2026-04-20T22:50 local
scope: Path B · C3 result-harvest side. Parses postProcessing/sets/ output from the 3 C3 generators (LDC/NACA/IJ) and overwrites comparator keys (u_centerline / pressure_coefficient / nusselt_number) with sampleDict-sourced values. Closes the round-trip started by DEC-V61-007/008/009.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 efb74707` removes 2 module-level helpers,
  3 static populators, 1 dispatcher, 17 tests. No new keys in
  CANONICAL_ALIASES, no schema changes, no legacy extractor
  modifications — cell-based paths preserved unchanged.)
notion_sync_status: synced 2026-04-20T23:00 (https://www.notion.so/348c68942bed81079ccad679ee023781) — Decisions DB page created with Scope=Project, Status=Accepted, Canonical Follow-up=PR #10 URL
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/10
github_merge_sha: efb74707c05c546cfb636de9440f6a400f9773b7
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 97%
  (Pure src/ + tests/ change. 196/196 regression green. OVERWRITE
  semantics preserve backwards compat for all MOCK / pre-C3 / failed
  runs — no postProcessing dir means legacy cell-based path executes
  unchanged. Hardcoded physics constants for IJ Nu match generator.)
supersedes: null
superseded_by: null
upstream: DEC-V61-007 (C3a) · DEC-V61-008 (C3b) · DEC-V61-009 (C3c)
design_doc: docs/c3_sampling_strategy_design.md
---

# DEC-V61-010: C3 result-harvest side — parse sampleDict → comparator keys

## Decision summary

Closes the other half of the C3 initiative. Generators (DEC-V61-007/008/009) emit gold-anchored sampleDicts at exact whitelist coordinates. This DEC adds the reciprocal harvest-side code path that reads those dicts' outputs and populates the standard comparator keys with sampleDict-sourced values — exact-at-gold instead of interpolated-from-cells.

## Shared module-level helpers

- `_parse_openfoam_raw_points_output(text)` — parses `setFormat raw` output. Handles 3D coord rows (`x y z field0 field1 ...`) and distance-column rows (`distance field0 field1 ...`). Skips comments/blanks/malformed lines silently (absence-tolerant).
- `_try_load_sampledict_output(case_dir, set_name, field)` — finds latest-time `postProcessing/sets/<time>/<setName>_<field>.xy`. Supports both layout A (flat time dirs) and layout B (nested under set name). Returns None on missing/unreadable.

## Per-case populators (FoamAgentExecutor @staticmethod)

| Case | Reads | Writes | Notes |
|---|---|---|---|
| LDC | `uCenterline_U.xy` | `u_centerline` = Ux at gold y-points (sorted asc) | Companion `u_centerline_y` for comparator visibility |
| NACA | `airfoilCp_p.xy` | `pressure_coefficient` list of `{x_over_c, Cp}` with Cp = p / (0.5·ρ·U_inf²) | Kinematic pressure convention (ρ=1); chord scaling on x |
| IJ | `plateProbes_T.xy` | `nusselt_number` (stagnation) + `nusselt_number_profile` | Nu = \|T_probe − T_plate\|·D / (Δz·ΔT_ref); clamped [0, 500] |

Each populator also sets `<key>_source = "sampleDict_direct"` as auditability marker so the comparator / downstream UI can distinguish sampleDict values from legacy cell-based interpolations.

## Integration — OVERWRITE semantics

Dispatcher `_try_populate_from_c3_sampledict` called at the end of `_parse_writeobjects_fields`. If the postProcessing/sets/ output exists and parses cleanly, the sampleDict value **overwrites** whatever the legacy cell-based extractor produced. If absent (MOCK executor, pre-C3 case cache, failed run), the cell-based value is preserved.

This preserves backwards compatibility perfectly: any test that doesn't stand up a `postProcessing/` dir continues to exercise the legacy path unchanged. All 179 baseline tests pass with the integration in place.

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (DEC-V61-003 turf) | YES — 2 helpers, 3 populators, 1 dispatcher |
| `tests/` | YES — +17 new tests |
| `knowledge/**` | NOT TOUCHED |
| Legacy extractor behavior | PRESERVED (no-op when no sampleDict output) |
| Notion DB destruction | NOT TOUCHED |

## Regression

```
pytest 7-file matrix → 196 passed in 1.10s
```

179 baseline + 17 new tests:
- `TestParseOpenFoamRawPointsOutput × 6` — parser edge cases
- `TestTryLoadSampleDictOutput × 4` — path resolution
- `TestPopulateLdcFromSampleDict × 2` — overwrite + no-op
- `TestPopulateNacaCpFromSampleDict × 2` — Cp conversion, chord scaling
- `TestPopulateIjNusseltFromSampleDict × 3` — stagnation Nu, clamp, no-op

## Impact

With C3 now complete end-to-end:

- LDC: solver samples at Ghia's 5 y-coords → comparator gets those exact values → no interpolation error term.
- NACA: solver samples at 3 surface x/c → Cp converted from kinematic p → comparator gets gold-grid Cp.
- IJ: solver probes 1mm above plate at r/d coords → harvester derives Nu via finite-difference vs. wall T_plate → comparator gets gold-grid Nu.

All three replace "solver has the answer but record at comparison point is wrong" with "solver answer is at the exact comparison point". Pair this with C1 (alias layer, DEC-V61-004) and all known sampling-related false-fail channels are closed.

## Non-goals (explicit)

- **IJ Option A wallHeatFlux FO upgrade** — could replace finite-difference Nu with native OpenFOAM wall-heat-flux output. Deferred as a future refactor; Option B (probes + finite diff) is sufficient for the current dashboard target.
- **NACA Cp lower-surface sampling** — needed only for non-zero AoA cases. Generator doesn't support AoA rotation.
- **Unit-consistency audit** for IJ Nu derivation. Hardcoded T_inlet/T_plate/D/Δz match the generator's hardcoded values. Any physics change must update both sides together.
- **Comparator alias additions** for `*_source` markers — not needed; downstream consumers can read them directly without going through `CANONICAL_ALIASES`.

## What §2 looks like now

Original §2 target: ≥5 PASS including ≥3 k-omega SST. The SST constraint was superseded when A/B-class corrections moved 4 cases to `laminar` (correct physics, not weakness). Realistic current state:

- 8 cases viable for PASS under current adapter (1 LDC, 2 BFS, 3 Cylinder, 4 Flat Plate, 5 Pipe Flow, 6 DHC, 7 Plane Channel, 10 RB)
- 1 case at HAZARD (9 IJ — Case 9 gold Nu values on HOLD per Gate Q-new)
- 1 case at DEVIATION (5 Pipe Flow — separate Q-2 R-A-relabel gate)

§2's ≥5 PASS target is **structurally achievable** after dashboard validation runs. Only blocker: Docker daemon + OpenFOAM container availability on the user's host (§5d).

## Next (queued, not this DEC)

1. **Q-2 R-A-relabel gate request** — file `.planning/gates/Q-2_r_a_relabel.md` for pipe_flow → duct_flow whitelist rename. Unblocks Phase 5 Audit Package Builder.
2. **Phase 5 kickoff plan** — scope the Audit Package Builder into discrete PRs. Currently blocked only on Q-2.
3. **§5d dashboard validation** — gated on Docker daemon startup + OpenFOAM container availability. User-side action required.
4. **Case 9/10 literature re-source** — still HOLD pending paper access. Paywalled per user 2026-04-20.
