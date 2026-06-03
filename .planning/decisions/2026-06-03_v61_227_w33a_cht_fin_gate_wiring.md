---
decision_id: V61-227
title: P3 W3.3a — cht_analytical fin gate-wiring (QoI extractor + comparator + coverage test)
status: Accepted
parent_dec: V61-217 (P3 CHT charter) · V61-226 (W3.3a benchmark contract + research)
sibling_decs: V61-225 (W3.2b CHT live-run adapter) · V61-209 (gold-standard tolerance convention)
phase: P3 (CHT vertical) · W3.3a (analytical solid-side benchmark)
autonomous_governance: true
confidence: high
kogami_opt_in: false (additive V&V plumbing; reversible; no §11.1 workbench-freeze paths touched)
round_cap: 3
codex_review_relay: CRS gpt-5.4 high (R0–R2; R2 after CRS-502 outage → 86gs-flap → CRS-recovered); effort=high
codex_verdict: APPROVE (R2, cap=3 — R0 1×P2 → R1 2×P2 → R2 0 findings)
codex_tool_report_path: reports/codex_tool_reports/v61_227_w33a_gate_report.md
notion_sync_status: synced 2026-06-03 (https://app.notion.com/p/374c68942bed81a2a074f9183741b91f)
touches_shared_dec: knowledge/schemas/gold_standard_schema.json (additive enum: +CONJUGATE) · generic gold loaders hardened (data_collector, auto_verifier, manifest)
date: 2026-06-03
---

# DEC-V61-227 · P3 W3.3a cht_analytical fin gate-wiring

## Context

DEC-V61-226 authored the analytically-exact straight-fin gold standard
(`knowledge/gold_standards/cht_straight_fin.yaml`) and `84ce01d` proved it
reproduces in a live OF11 `foamRun -solver solid` solve (η 0.063%, tip 0.028%
error, adversarially CONFIRMED_WITH_CAVEATS). What remained was the
**production-code gate-wiring**: make the benchmark runnable *through a
comparison gate*, offline, with a coverage test — so CI reproduces the W3.3a
PASS from frozen artifacts with no Docker.

## Decision

Wire the benchmark through the **canonical `ResultComparator`** (the
`quantity`/`reference_values` multi-doc family — confirmed by an independent
read-only mapping workflow as authoritative for this gold, NOT `auto_verifier`'s
`observables` schema nor the out-of-scope `AutoVerifier`).

- **QoI extractor** `src/cht_fin_extractor.py` (**Execution Plane**, pure): parse
  `postProcessing/{basePower,finPower,baseT,tipT}/<t>/surfaceFieldValue.dat`
  (raw solver output) → `fin_efficiency = Q_base/(h·P·L·θ_b)`,
  `fin_tip_temperature_ratio = (T_tip−T_inf)/(T_base−T_inf)`. Inputs only; never
  the closed form (anti-tautology). Fail-closed on missing/NaN.
- **Gate** `src/cht_fin_gate.py` (**Control Plane**): `gate_fin_against_gold()` —
  extract → `ExecutionResult` → `ResultComparator.compare()` per gold doc.
  `cht_analytical` = reuse of the scalar-tolerance path (no bespoke comparator).
  Control is the only plane that may import both Execution + Evaluation (≡
  task_runner). **Energy closure** `|Q_base+Q_fin| ≤ 1e-3·|Q_base|` is a HARD
  gate component (Codex R1 P2-A).
- **Contract** `cht_straight_fin.yaml`: +`T_inf` to `fin_inputs` (gate sources
  every input from the locked contract). Schema: +`CONJUGATE` to the
  `flow_type` enum (fixed a pre-existing RED — corpus validator was failing on
  the W3.3a gold).
- **Plane SSOT** `_plane_assignment.py` + regenerated `.importlinter`
  (extractor=Execution, gate=Control); `lint-imports` 5/5 KEPT.
- **Coverage test** `tests/p3/test_cht_fin_gate.py`: drives the committed probe
  artifacts → gate PASS; anti-cheat (doctored Q_base / finPower / T_tip → FAIL;
  extracted ≠ gold reference; energy closure; missing input → raise).

## Scope / honesty boundary

Validates **solid conduction + imposed-h Robin BC** against the exact
adiabatic-tip fin. Does **NOT** flip runnable-coverage **1→2** — that requires
**W3.3b** (full two-region conjugate vs Gnielinski, fluid-produced h).
**runnable-coverage stays 1.** No coverage count fabricated.

## Codex chain (cap=3) — see codex_tool_report_path

- **R0** (`--commit e38b279`): CHANGES_REQUIRED · 1×P2 (multi-doc vs single-doc
  loaders). Fixed `cf2e0e9` (behaviour-preserving `safe_load_all`+first-doc;
  manifest left — already graceful).
- **R1** (`--base ea502f9`): CHANGES_REQUIRED · 2×P2 — [A] energy closure not
  gated (good catch); [B] manifest graceful-None = silent audit data loss. Fixed
  `b5bd8f2` (hard energy gate + manifest multi-doc wrapper preserving full
  contract).
- **R2** (`--base ea502f9`): **APPROVE** — "did not identify any discrete,
  actionable bugs introduced by this diff … internally consistent with existing
  callers and tests." (Relay: CRS 502 outage → 86gs flap → CRS recovered; clean
  CRS R2 completed.)

Commits: `e38b279` (feat) · `cf2e0e9` (R0) · `b5bd8f2` (R1). Full suite 1965
passed / 3 skipped.

## Next

W3.3b — full conjugate (two-region) vs Gnielinski, fluid-produced h → the
coverage 1→2 flip. (Adapter live-run dispatch wiring for the fin is out of scope
here; the fin is single-region `foamRun -solver solid`, gated offline.)
