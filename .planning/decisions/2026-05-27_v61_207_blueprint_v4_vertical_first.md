---
decision_id: DEC-V61-207
title: Blueprint v4 charter — vertical-first (incompressible RANS aero) + runnable-coverage law + V&V loop + AI distillation path
status: Accepted
parent_dec: DEC-V61-130 (AI-advisor pivot) · evolves blueprint_v3_2026-05-07 · corrects DEC-V61-198 coverage accounting
phase: Blueprint v4 (product-blueprint layer · strategy selection)
notion_sync_status: synced 2026-05-29 (https://www.notion.so/36fc68942bed81d3a30dc3f37b0fb8df)
autonomous_governance: false
confidence: high
date: 2026-05-27
ratified_by: user (chose Strategy A vertical-first + first vertical "incompressible RANS aero" + "write as Blueprint v4 charter", 2026-05-27)
---

# DEC-V61-207 · Blueprint v4 charter — vertical-first + runnable-coverage

## TL;DR

A deep re-think of the development blueprint (requested by the user, framed as a
commercial-CAE design engineer) found the project has grown **two layers at very
different rates**: a deep trust/knowledge layer (truth-chain, V-series 85+
death-chains, 12+ compute-type profiles) and a **narrow runnable engine**
(incompressible RANS + buoyant-transient only; compressible/CHT/VOF/LES are
*declared-but-not-runnable* or profile-only). The APU "industrial CFD" ran in an
external sandbox, not the workbench executor.

The user selected **Strategy A · vertical-first** with first vertical
**incompressible RANS aero**, and ratified it as **Blueprint v4** (full content:
`.planning/strategic/blueprint_v4_2026-05-27.md`).

## Decision

1. **Strategy A · vertical-first**: make 1–2 compute types bulletproof
   end-to-end before adding the next. First vertical = **incompressible RANS
   aero** (external + wall-bounded).
2. **Law 1 · Runnable-coverage**: a compute type is "covered" only when its
   solver runs end-to-end AND a benchmark passes its tolerance gate. Profiles /
   death-chains are knowledge, not coverage. (Corrects DEC-V61-198 accounting;
   keeps its container-of-experience flywheel.)
3. **Law 2 · V&V loop as a first-class flow**: `run → compare-to-gold →
   quantified error → TrustGate verdict` (v9 R4 as the gate).
4. **Law 3 · AI distillation path**: the Claude session distills V-series
   death-chains into the versioned offline v9 ruleset (8 rules today → grow);
   the ruleset ships and runs without AI. Pre-flight signals (mesh/BC/physics)
   are the unlock to distill setup-class findings.

## Development path (risk-first)

P1 harden the RANS-aero vertical + close the V&V loop → P2 close the AI loop
(pre-flight signals + ruleset distillation + pre-flight review) → P3 add CHT
end-to-end → P4+ compressible/VOF/LES, each gated on runnable+validated.
Continuous: clear the 3 cosmetic truth-chain fakes (cluster chip / solver
KPI+telemetry / DOE); grow v9 from V-series.

## Kept unchanged

Blueprint v3 North Star, 4-region UI, four-question gate, AI-advisor-only
(DEC-V61-130), container philosophy (DEC-V61-198, corrected by Law 1).

## Governance

- Charter / direction change. **Kogami strategic review available (opt-in) but
  not invoked** — user ratified the direction directly.
- No code changed by this DEC; it is the strategy SSOT that sequences subsequent
  P1+ sub-DECs.
- Supersedes blueprint_v3 **as the product-blueprint layer**; does not supersede
  DEC-V61-130 / DEC-V61-198 / sub-DECs.

## Ratification

User explicitly chose (2026-05-27): Strategy A (vertical-first) · first vertical
incompressible RANS aero · land as Blueprint v4 charter. Status = Accepted.
notion_sync_status = pending (session-end batch sync, Accepted DEC).
