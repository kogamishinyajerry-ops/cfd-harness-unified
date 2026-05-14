---
decision_id: DEC-V64-A-sub-M-VAL-CASE-016-FULL
title: V64-A first sub-DEC · case_016 m219 cavity DES acoustic PARTIAL → FULL conversion attempt · solver window extension trial · PARTIAL v2 verdict (compound gating exposed)
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 1 · M-VAL-CASE-016-FULL (PARTIAL → FULL conversion attempt · charter named this the "cheapest unblock" path)
notion_sync_status: pending
authored_by: Claude Code Opus 4.7 (1M context) · main session B53
authored_at: 2026-05-15
confidence: med
codex_review_relay: skipped (v2.3 1-sync-trigger · case substrate + documentation · no auth/signing/security-boundary touch)
kogami_review: skipped (v2.3 opt-in only · user did not invoke)
autonomous_governance: true
---

# DEC-V64-A-sub-M-VAL-CASE-016-FULL · case_016 PARTIAL → FULL conversion attempt

## Status

**Accepted 2026-05-15** — sub-DEC records the conversion-attempt evidence + charter premise refutation. Verdict on FULL milestone: **PARTIAL v2** (not FULL). V64-A Done dim #1 stays **0/3 FULL**.

This sub-DEC is `Accepted` (not `Proposed`) because the **recording itself** is the deliverable — the brief explicitly authorized "如果延长后 solver 不稳定 → 完整记录 PARTIAL v2 · 不掩盖". The PARTIAL verdict + compound-gating evidence + charter-premise refutation is what was contracted, and that is delivered. Accepting the sub-DEC closes the dispatch contract; it does not claim the FULL milestone was achieved.

## Goal (verbatim from B53 dispatch + V64-A North Star §1)

> "落地 V64-A 首个 sub-DEC — M-VAL-CASE-016-FULL (case_016 m219 cavity DES acoustic 从 PARTIAL → FULL · 把 solver window 从 17× 过短延长到能解 Rossiter mode 1 · 完成 Heller-Bliss SPL 实验对比 · 推 V64-A Done dim #1 0/3 → 1/3)"

Verbatim from V64-A charter North Star:

> "把 V63-A 的 2/3 PARTIAL validation reports 真正推到 FULL · 实际跑 OpenFOAM solver 到收敛 · ... ≥3 篇工业级 FULL validation reports 真实验证收敛 + 文献对比 + V-row attribution · 让 V62/V63 advisor stack 第一次"经实验数据验证过"而不只是"advisor 自审 PASS"."

## Scope (what changed in this sub-DEC)

**Substrate change** (outside repo, in `~/Desktop/case_016_m219_cavity_des_acoustic/`):
- `case/system/controlDict::endTime`: `0.0005` → `0.040` (intent · sed-patched to `0.020` at run launch by `scripts/08_run_solver.sh`)
- All other config files unchanged (mesh, thermo, turbulence, BCs, fvSchemes, fvSolution, initial state)

**Repo changes** (this sub-DEC commit chain):
- `.planning/validation_reports/v64_case_016_m219_cavity_des_acoustic_full_v2.md` (NEW — 12-section validation report v2)
- `.planning/case_profiles/case_016_m219_cavity_des_acoustic.md` (updated — v2 sub-section appended for substrate diff + crash forensics trace)
- `.planning/decisions/2026-05-15_v64_sub_val_case_016_full.md` (NEW — this file)

**Out of scope** (per dispatch contract):
- No advisor source change (`ui/backend/services/advisor_stack.py` + advisor files all untouched)
- No mesh refinement (273k cells unchanged from v1)
- No Notion sync (main session session-end batch)
- No Codex review (case substrate is not a security boundary per v2.3 1-sync-trigger)
- No Kogami review (opt-in only per V133; user did not invoke)
- No kill of port-occupying process

## Solver v2 run trace (1-paragraph summary; full forensics in v2 report §3)

`STAGE=solver END=0.020 bash scripts/08_run_solver.sh` launched `rhoPimpleFoam` inside Docker container `gifted_galileo` (image `opencfd/openfoam-default:2312`, `linuxARM64GccDPInt32Opt`, host arch = arm64, no Rosetta). Solver completed 26 timesteps from `t = 6.85e-05 s` to `t = 0.0012422023 s` (≈ 2.5× v1's window) at sustained rate ~26 μs sim / s wall (~1.7 s wall per step) before crashing on PIMPLE iteration 2 of timestep 28 with `sigFpe` (FE_DIVBYZERO / FE_INVALID) in `libfluidThermophysicalModels.so` frame #4 of the OpenFOAM stack trace. ExecutionTime at crash = 46.92 s wall. Cumulative continuity at last successful timestep = 1.2403e-07 (v1 baseline was 8.5e-08 at t = 0.0005 s — drifted upward but within transonic-startup envelope). Pressure-control p_max trajectory was within plausible bounds (peak 763 kPa on PISO step 1 startup impulse, then relaxed to ~160-180 kPa quasi-stable). The fault chain through `libm.so.6` → `libfluidThermophysicalModels.so` strongly suggests a `pow/exp/log/sqrt` domain violation during T-dependent property evaluation (likely `sutherlandTransport::μ(T)` or `hConst::H(T)` hitting `T ≤ 0` or extreme T from a local energy-solver overshoot, possibly shock-induced cell-local).

**All 26 probe pressure readings at the K05 (0.279, 0, -0.101) and K09 (0.483, 0, -0.101) Kulite sensor locations remained locked at the freestream 101,325 Pa for the entire 1.24 ms window.** The cavity shear layer never developed enough perturbation to reach the probes at this window (L_cavity / U_inf flow-through ≈ 1.75 ms; achieved ~70% of one flow-through). **No measurable acoustic time series was captured.** The brief's downstream deliverables — Welch FFT SPL spectrum, 1/3-octave SPL, Heller-Bliss / AGARD CP-437 SPL delta — are all unattainable from this run, by construction of the achieved window.

## Heller-Bliss SPL delta table (analytical only; no measured comparison possible)

Per v2 report §4.2, evaluated for m219 (U_inf=290, L=0.508, M=0.85, canonical α=0.25, κ=0.57):

| Rossiter mode n | Heller-Bliss canonical (Hz) | Published m219 K09 (Hz) | Δ Hz | Δ % |
|---|---|---|---|---|
| 1 | 164.4 | 142.0 | +22.4 | +15.8 |
| 2 | 383.6 | 353.0 | +30.6 | +8.7 |
| 3 | 602.7 | 592.0 | +10.7 | +1.8 |
| 4 | 821.9 | 813.0 | +8.9 | +1.1 |

Alternative empirical fit (`α=0.40, κ=0.65`, high-M cavity papers):

| n | Hz | Δ vs published Hz | Δ % |
|---|---|---|---|
| 1 | 143.4 | +1.4 | +1.0 |
| 2 | 382.4 | +29.4 | +8.3 |
| 3 | 621.4 | +29.4 | +5.0 |
| 4 | 860.4 | +47.4 | +5.8 |

m219 does not admit a single Rossiter (α, κ) pair across all 4 modes — shock-induced phase modulation regime at M ≥ 0.8 (well-documented; not novel).

**Brief's required delta-table format** ("frequency delta Hz % error / amplitude delta dB error / 1/3 octave SPL delta") cannot be produced from v2 run. **SPL columns omitted by construction.** This is the same gating the v1 retro flagged; v2 did not narrow it.

## Charter premise refutation

`DEC-V64-A-charter` Status §3 (line: "M-V64A-VAL-CASE-016-FULL first candidate · cheapest unblock path · **solver already converged 8.5e-8, only window extension needed**") is empirically refuted by v2's run.

| Charter claim | v2 evidence |
|---|---|
| "solver already converged 8.5e-8" | Only at the v1 window endpoint t = 0.0005 s. At t = 0.0012 s cumulative continuity drifted to 1.2403e-07 (still good); at t = 0.00124 PIMPLE iter 2, solver CRASHED in thermophysical model. Convergence inside 0.5 ms is not equivalent to convergence at 35-70 ms target. |
| "only window extension needed" | Window extension is necessary but not sufficient. Substrate also needs solver-config refinement (initial deltaT ramp / pressure tolerance / thermo limiter or polynomialTransport / possibly mesh refinement near LE / possibly fall back from IDDES to DDES first). |
| "cheapest unblock path" | Direct measurement says case_016 → FULL requires solving a NEW substrate problem (thermo-FPE stability) before the original window-extension problem can even be attempted. This is a 2-axis problem, not 1-axis. The charter's "cheapest" framing depended on it being 1-axis. |

## V-row attribution v2 delta (vs v1 B50)

| V-row | v1 state | v2 state |
|---|---|---|
| V52-V57 (LANDED upstream from HANDOFF) | LANDED | unchanged |
| V81 fail-class (advisor pass artifacts) | 2 findings | unchanged (no v2 stack invocation) |
| **V-candidate v2-new-1** `case_016-class compressible-DES-acoustic substrate: rhoPimpleFoam+sutherland+kOmegaSSTIDDES m219 produces solver-FPE in libfluidThermophysicalModels at t > 1.24 ms under v1 controlDict` | n/a | **[QUESTIONABLE 2026-05-15]** — single-case observation; promotion to LANDED requires second-case corroboration (different cavity / different M / same thermo) |
| **V-candidate v2-new-2** `Heller-Bliss canonical (α=0.25, κ=0.57) overpredicts m219 mode 1 by +15.8%; m219 spectrum does not admit single (α, κ) pair across 4 modes — high-M shock-phase regime` | n/a | **[QUESTIONABLE 2026-05-15]** — literature analysis, not v2 measurement |
| **V-candidate v2-new-3** `Charter elevation discipline: "convergence at v1 window" ≠ "convergence at target window"; future charter drafts naming a "cheapest unblock" must verify convergence-at-target before claiming` | n/a | **[QUESTIONABLE 2026-05-15]** — process candidate; promotion via V64-A close DEC or methodology doc |

**Net delta**: 3 V-candidates surfaced; 0 LANDED in v2 (single-case substrate per the standard QUESTIONABLE protocol).

## Backward compatibility

- v1 PARTIAL retro `.planning/validation_reports/v63_case_016_m219_cavity_des_acoustic_validation_report.md` **untouched** — preserved as diff baseline.
- v1 evidence directories `case/log.v1/` + `case/postProcessing.v1/` **archived in-sandbox** before v2 run (not in repo).
- v2 evidence `case/log/` + `case/postProcessing/` is **current sandbox state** post-v2 crash.
- For Done-dim-#1 PARTIAL-credit accounting: v1 + v2 are **two retros on the same case**. To avoid double-counting, V64-A close DEC should count at most one of v1/v2 toward the 3-PARTIAL-credit tally.

## Done-dim accounting at this commit

| V64-A Done dim | Before v2 | After v2 | Δ |
|---|---|---|---|
| #1 ≥3 FULL validation reports | 0/3 FULL · 2 PARTIAL (case_011 + case_004 + case_016-v1 if counted; or 2 unique cases per de-double-counting) | **0/3 FULL** · 2-or-3 PARTIAL depending on accounting | no FULL advancement |
| (other dims) | per charter | unchanged this sub-DEC | — |

Brief's stated target ("推 V64-A Done dim #1 0/3 → 1/3") = **NOT MET**.
Brief's authorized fallback path ("PARTIAL v2 不掩盖") = **MET**.

## Surface scan + v2.3 compliance

| Gate | Evidence |
|---|---|
| Surface-scan | `grep -rin "case_016.*FULL\|VAL-CASE-016" .planning/` returns 0 prior FULL artifact (v1 PARTIAL retro + ARC-GOAL B50 line + 1 methodology playbook line are the prior touches; no name collision). `Surface-scan: clean` trailer. |
| v2.3 sub-DEC scope | 3 shared code paths: case_016 controlDict (sandbox) + v2 validation report (repo) + this sub-DEC (repo). At charter-trigger threshold but no schema change, no security boundary, no contract break. Authored as sub-DEC per v2.3 round-1 loosen. |
| Codex review | skipped per v2.3 1-sync-trigger (case substrate + documentation; no auth/signing/security-boundary touch) |
| Kogami review | skipped per V133 opt-in (user did not invoke) |
| Notion sync | pending main session session-end batch (Status=Accepted only per v2.3) |
| Counter | +1 `autonomous_governance: true` |
| confidence | med (high on crash forensics + Heller-Bliss math; med on charter-premise-refutation framing) |
| Q1 LLM-offline | not exercised this sub-DEC (no advisor invocation; v1 stack pass is authoritative) |
| Q2 artifacts | YES — `case/log/rhoPimpleFoam.txt` 109,031 bytes + probe file 31 lines preserved on disk + v1 archives preserved |
| Q3 TrustGate | YES — verdict + reasoning visible in v2 report §1, §3, §6, §7 |
| Q4 advisory-only | YES — sub-DEC is Accepted by Claude Code main session B53 dispatch; user reconciles into V64-A roadmap; charter premise refutation is **surfaced**, not auto-applied |

## Next-step recommendations to main session

1. **Update `DEC-V64-A-charter` (or write a charter-supplement DEC, or fold into V64-A close DEC)** to refute the "solver already converged 8.5e-8, only window extension needed" claim. v2's evidence is that 8.5e-8 was a 0.5 ms-window observation, not a production-window guarantee.
2. **Re-tier M-V64A-VAL-CASE-016-FULL** — split into M-VAL-CASE-016-STABILITY-FIX (prerequisite) + M-VAL-CASE-016-WINDOW-EXT + M-VAL-CASE-016-FULL-COMPARE; OR defer case_016 to a later V64-A tier and promote the charter's case_004 / case_006 / case_011 candidates to Tier 1.
3. **For the next V64-A FULL attempt** — pick the candidate with the simplest single-axis gating (most likely case_011 v5b non-degenerate substrate per V62-A TRACK-1-rerun PASS evidence, where the solver path is already well-trodden).
4. **Do not** retry case_016 with the current `case/system/{controlDict, thermophysicalProperties, fvSchemes, fvSolution}` substrate at any window ≥ 1.5 ms — the FPE failure mode is now reproduced; further runs without a stability fix will burn wall budget repeating the same crash.

## Pointers

- v2 validation report: `.planning/validation_reports/v64_case_016_m219_cavity_des_acoustic_full_v2.md`
- v1 validation report: `.planning/validation_reports/v63_case_016_m219_cavity_des_acoustic_validation_report.md` (untouched)
- Case profile: `.planning/case_profiles/case_016_m219_cavity_des_acoustic.md`
- Charter DEC: `.planning/decisions/2026-05-15_v64_charter_dec.md` (`DEC-V64-A-charter`)
- V63 close DEC: `.planning/decisions/2026-05-15_v63_close.md` (predecessor)
- Sandbox HANDOFF: `~/Desktop/case_016_m219_cavity_des_acoustic/HANDOFF.md`
- Solver launch script: `~/Desktop/case_016_m219_cavity_des_acoustic/scripts/08_run_solver.sh`
- Postp script (window-guard-honest): `~/Desktop/case_016_m219_cavity_des_acoustic/scripts/09_compute_rossiter_modes.py`

---

*Authored by: Claude Code Opus 4.7 (1M context) main session · B53 V64-A first sub-DEC dispatch · 2026-05-15 · `Accepted` · confidence: med*
