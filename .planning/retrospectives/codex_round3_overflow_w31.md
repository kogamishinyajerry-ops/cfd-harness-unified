# Codex round-cap overflow · P3 W3.1 (DEC-V61-222)

> Per `/goal` Pattern B + RETRO-V61-001: when the Codex chain hits round cap = 3
> (R0 + 2 fix iterations) with a residual finding, the residual is recorded here,
> ratified by the user, and tracked — not iterated further.

- **Date**: 2026-05-31
- **Phase**: P3 W3.1 (CHT v9 rule distillation)
- **Chain**: R0 → R1 → R2, ALL CHANGES_REQUIRED, all CRS gpt-5.4 high (86gs 5-for-5
  unavailable). Report: `reports/codex_tool_reports/v61_222_chain_report.md`.

## The residual (Codex R2 P1 — RATIFIED as W3.2-deferred, not a defect)

**Finding**: the run-detail backend API (`ui/backend/schemas/run_history.py`
`RunDetail` + `ui/backend/services/run_history.py get_run_detail()`) does not emit
`regions`, so the CHT rules R13/R14 cannot be reached through the production UI
live-card path. (The R1 fix had added `regions` to the TS `RunDetail` interface +
the UI adapters but not the backend schema — a half-wired path + a TS↔Python
parity gap.)

**Why it is correct AND why it is NOT a W3.1 defect**: the finding is accurate —
the UI path is unreachable. But it is the same root the whole chain circled:
*full production reachability requires the producer side (real region data →
manifest → run-detail API), which the charter sequences to W3.2*. W3.1 can only
deliver the rules + forward-compat consumer infrastructure. A reviewer without the
charter's phase-sequencing context correctly keeps surfacing "another unwired
layer" (R0 deriver → R1 R15/R16 → R2 run-detail API).

**User adjudication (round-cap stop, 2026-05-31)**: revert the premature UI-adapter
wiring (`97b2ca6`); draw W3.1's honest boundary at the deriver/commentary path; the
entire UI live-card path + producer-side emission is one coherent W3.2 unit. The
R2 P1 is ratified as a tracked W3.2 deliverable.

## Tracked → W3.2 (contract defined in DEC-V61-222)

1. `build_manifest()` emits `manifest["regions"]` from the W3.0.x extractors.
2. The run-detail API (`run_history.py` schema + `get_run_detail()`) emits `regions`;
   re-add the UI `RunDetail`/`BridgeArtifact` field + adapter carry-through.
3. Add a per-region produced-mesh-presence field to `RegionSlice` → reground +
   re-ship R15 (CONDUCTION_DOMINANCE) + R16 (FACE_ZONE_LOSS).
4. Integration test: a real multi-region bundle fires ≥1 CHT rule end-to-end.

## Lessons (RETRO-V61-001 intake — post-R3 / chain-pattern)

1. **Cross-artifact review is load-bearing for advisor rules** (R1 defect class):
   R15/R16's faithfulness failure was only visible by reading the *extractors'*
   docstrings (declared-vs-produced-mesh). The same-family red-team validated the
   rules in isolation and missed it; Codex (异源) caught it. **New intake risk_flag**:
   `advisor-rule-vs-producer-semantics` — the understand phase for any v9/v-series
   rule phase MUST cross-reference the upstream data-producer's documented semantics,
   not just the frozen consumer contract.
2. **Rules-ahead-of-data sequencing invites a multi-round "unreachable" dance**: when
   a phase ships a consumer ahead of its producer, the producer-side boundary must
   be stated IN THE DIFF (code comments at the exact consumption sites) up front, so
   review assesses the documented deferral rather than re-discovering it each round.
3. **86gs xhigh 5-for-5 unavailable this session** (W3.0.1 502×2 · W3.0.2 stream-fail
   · W3.0.6 R2 hang · W3.1 R0 hang) — CRS carried every governance review (2 transient
   429s, cleared on paced retry). **Action**: a routing-policy DEC to promote CRS to
   governance-primary (effort=high) until 86gs stabilizes; note the xhigh→high effort
   downgrade has held governance quality across 6 reviews this session with no missed
   defect attributable to the lower effort.
