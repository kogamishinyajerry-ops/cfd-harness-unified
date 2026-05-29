# P3 CHT kickoff considerations — pre-charter notes · 2026-05-30

> **THIS IS NOT A CHARTER.** This document is a set of charter-authoring considerations
> distilled from the P2 phase-close (`retrospectives/2026-05-30_p2_phase_close.md`) to
> inform the main-session author of the P3 charter DEC. The user MUST spawn the charter
> DEC separately (governance-rule-impacting / new compute type → CLAUDE.md scope-driven
> DEC trigger). Producing the charter is **not** the scope of the subagent that wrote
> this file.
>
> Parent: `strategic/blueprint_v4_2026-05-27.md` (Blueprint v4 §4 — P3 = CHT 2nd compute type)
> Sibling: `strategic/p2_plan_2026-05-27.md` (P2 plan format precedent for what a phase plan looks like)
> Status: **DRAFT NOTES** · not a phase plan · not Status=Accepted · not Notion-synced
> Author: subagent under `gsd-quick`-class doc-task (no Codex, no Kogami; documentation-only)

---

## What P3 is (per Blueprint v4)

| Field | Value |
|---|---|
| Phase | **P3 · Add CHT (2nd compute type)** |
| Goal | Wire `chtMultiRegionSimpleFoam` end-to-end (currently declared-only per `foam_agent_adapter.py:739`) → validate (plate-fin / blade-cooling) → sediment death-chains |
| Exit gate | CHT benchmark passes its tolerance gate end-to-end through the workbench, runnable-coverage = 2 |
| Why now | P1 (RANS-aero V&V loop) and P2 (pre-flight + ruleset distillation) both closed. CHT is the second runnable-coverage compute type per Strategy A vertical-first sequence. |

CHT today (from `blueprint_v4_2026-05-27.md` §6):
- ❌ NOT runnable (declared in `solver_derivation.py`, routes to safe defaults in `foam_agent_adapter.py:739`)
- Knowledge present: `case_002b_apu_bay_cht.md` reference profile + plate-fin compact HX V-series row (industrial dogfood sediment per DEC-V61-198)

P3 close gates the third runnable compute type after incompressible RANS aero (P1) and buoyant transient (already runnable per Blueprint v4 §6 row 2).

---

## Charter considerations (3-5 distilled from P2)

### Consideration 1 — sequencing constraint: **slice extension MUST precede rule distillation**

P2 proved that distilling V-series lessons into v9 rules requires widening the data
contract first (`DEC-V61-215` W2.0.6) before writing rules (`DEC-V61-216` W2.1). The
scalar `RunArtifactSlice` saturated at R9; the regional / nested-dataclass extension
was non-negotiable, not an optimization. **The P1-close blindspot retro finding 5
predicted this; P2 confirmed it; P3 should plan around it.**

**Concrete recommendation**: budget **two sub-DECs per CHT distillation increment** —
a "W3.0.6-equivalent" CHT-specific slice extension (region-temperature-delta,
interface-flux-residual, coupling-iteration-convergence) BEFORE any "W3.1-equivalent"
CHT advisor rules. Trying to write CHT rules against the existing scalar slice will
manufacture theater rules with no discriminating power (same class as the W1.1 circular
pre-flight finding from `2026-05-28_p1_close_p2_blindspot_findings.md` finding 1).

**Source**: `2026-05-30_p2_phase_close.md` lessons §7; `p2_plan_2026-05-27.md` W2 meta-finding lines 77-87; `2026-05-28_p1_close_p2_blindspot_findings.md` finding 5.

### Consideration 2 — multi-region case-dir architectural impact

All four P2 extractors (`solver_block_extractor.py`, `shm_dict_extractor.py`,
`thermo_dict_extractor.py`, `step_extractor.py`) assumed **single-region** layout
(`constant/`, `system/`, `0/`). CHT requires **multi-region** layout (`constant/<region>/`,
`system/<region>/`, `0/<region>/`) plus a NEW `regionProperties` reader.

**Concrete recommendation**: the P3 charter should explicitly inventory which P2
extractors cleanly extend to multi-region (likely `solver_block_extractor` at the
top-level `controlDict` layer — `chtMultiRegionSimpleFoam` still has a top-level
controlDict) vs which need **region-aware variants** (`shm_dict`, `thermo_dict`).
Plan sub-DECs analogous to DEC-V61-211..214 but with per-region iteration. Survey
real CHT-bearing cases (e.g. `case_002b` reference profile + APU-bay external
sandbox templates per DEC-V61-198 + plate-fin compact HX dogfood) for region-naming
conventions **BEFORE** designing the `regionProperties` reader — the P2 carry-forward
pattern "enumerate ALL forms BEFORE writing" applies directly.

**Source**: `2026-05-30_p2_phase_close.md` lessons §1, carry-forward pattern §5; `blueprint_v4_2026-05-27.md` §6.

### Consideration 3 — V&V benchmark selection is a charter-level decision

DEC-V61-209 established the "**integrated metric + per-point developed-region +
verification station**" triple-pass NASA convention for incompressible RANS aero;
that selection took 8 cycles to settle. CHT has **no NASA TMR analogue** — the
benchmark + gate convention must be picked deliberately at charter time, not
discovered mid-implementation.

**Concrete recommendation**: the P3 charter must pre-resolve four sub-questions
that are governance-rule-impacting (so they go in the charter body, not in a
sub-DEC):
1. **Which benchmark?** (candidates: NIST plate-fin correlations; Vargas-Bejan
   compact-HX correlations; a specific tabulated journal paper; a textbook CHT
   case from Patankar / Bejan / Kays-Crawford).
2. **What gate-mode analogue?** (the DEC-V61-209 `gate_mode: nasa_integrated`
   convention requires a CHT counterpart that is **gameable on neither metric
   alone** — e.g. integrated heat-transfer-coefficient + station Nusselt number,
   or effectiveness + wall-temperature profile).
3. **What tolerance?** (DEC-V61-209 used 10% per NASA convention with explicit
   citation; CHT tolerance must be similarly cited, not engineered-to-pass).
4. **Who cites the benchmark?** (truth-chain: the canonical Re/U/L/ν analogue
   for CHT must be sourced and machine-readable, mirroring the W1.0 gold-standard
   `canonical_conditions` pattern from P2).

**Source**: `2026-05-30_p2_phase_close.md` lessons §2; `blueprint_v4_2026-05-27.md` §4 P3 exit gate; `p2_plan_2026-05-27.md` W1.0 pattern.

### Consideration 4 — pre-state P3 v0.1 scope-outs in the charter to avoid mid-implementation overrides

Workflow autonomy (DEC-V61-214) showed the design phase will (correctly) override
brief framing when the framing conflicts with what an honest data contract supports.
**The remedy is to pre-state scope-outs in the charter** so the design phase doesn't
need to override the brief.

**Concrete recommendation**: explicitly enumerate which CHT capabilities are OUT
of v0.1 scope in the charter body. Candidates to scope-out (each with deferred-trigger):
- **Conjugate radiation** — only conduction + convection in v0.1; radiation is
  separate compute-type complexity.
- **Porous-media coupling** — separate solver family, not chtMultiRegionSimpleFoam.
- **Phase-change CHT** — no melting/solidification in v0.1.
- **Turbulent-flow heat transfer** — start with laminar CHT OR lock to a single
  turbulence model (Blueprint v4 §6 buoyantFoam already runnable suggests opening
  with buoyancy-driven CHT before turbulent CHT).
- **Time-resolved CHT** — `chtMultiRegionSimpleFoam` is steady-state; deferring
  transient variants (`chtMultiRegionFoam` etc.) is principled.

**Source**: `2026-05-30_p2_phase_close.md` lessons §6; DEC-V61-214 §"Out of scope" precedent.

### Consideration 5 — governance topology pre-registration (Codex relay + Kogami opt-in)

P2 sub-DECs ran as Codex-only chains (cap=3, APPROVE_WITH_COMMENTS). P3 charter is a
**larger-blast-radius decision** than any P2 sub-DEC: new compute type, runnable-coverage
Law 1 directly invoked, multi-region architectural impact across `case_extractors/` +
`manifest_adapter` + advisor stack + `cfdtrust` runner.

**Concrete recommendation**: the charter author should make the governance topology
explicit in charter frontmatter / preamble:
- **Kogami opt-in?** Per V133 / project CLAUDE.md "When to consider invoking Kogami":
  charter / governance-rule-change DECs where independent second opinion is desired.
  P3 satisfies the trigger; user-decision whether to invoke. (P2 sub-DECs did NOT
  invoke Kogami; P3 charter is a larger decision than any P2 sub-DEC.)
- **Codex relay primary + fallback pre-registration.** Pre-state `codex_review_relay:
  86gs (primary) → CRS (fallback if 429/quota tight)` in the charter frontmatter
  per DEC-V61-214 / DEC-V61-216 precedent. P2 saw exactly one 86gs xhigh 429 → CRS
  reconciliation; pre-registering avoids ad-hoc fallback documentation.
- **Round cap = 3** per v2.3; pre-state expected count (charter-class often R0 + 1
  fix; if R2 still has P1, escalate to user not iterate).

**Source**: `2026-05-30_p2_phase_close.md` cadence + Codex discipline observations; `~/Desktop/cfd-audit-merge/CLAUDE.md` "Three-layer governance" + "When to consider invoking Kogami"; DEC-V61-133.

---

## Reading list for the charter author

Order matters — read top-down.

| Order | Path | Why |
|---|---|---|
| 1 | `~/Desktop/cfd-audit-merge/CLAUDE.md` | Project governance SSOT (Kogami opt-in, Codex round cap=3, DEC scope-driven, Notion sync rules, /goal CFD patterns) |
| 2 | `.planning/strategic/blueprint_v4_2026-05-27.md` | Charter precedent: 8-section product-blueprint structure (North Star → diagnosis → 3 laws → strategy → phase table → debt → coverage map → kept-from-v3 → governance) |
| 3 | `.planning/strategic/p2_plan_2026-05-27.md` | **Phase-plan precedent** — what a phase plan looks like (workstreams table + passes-criterion + size estimates + guardrails + open question for sponsor). P3 plan should mirror this format. |
| 4 | `.planning/decisions/2026-05-27_v61_207_blueprint_v4_vertical_first.md` | Charter DEC precedent — full frontmatter shape + body structure for a charter-class DEC. The P3 charter DEC should mirror this template. |
| 5 | `.planning/retrospectives/2026-05-30_p2_phase_close.md` | This phase-close retro — captures lessons and carry-forward patterns to reuse in P3 |
| 6 | `.planning/retrospectives/2026-05-28_p1_close_p2_blindspot_findings.md` | P1 close + 5 blind-spot findings (especially finding 5 = scalar-rule space saturation; the same sequencing constraint repeats in P3) |
| 7 | `.planning/decisions/2026-05-27_v61_209_flat_plate_vv_de_fake.md` | DEC-V61-209 V&V loop precedent — how a benchmark validation gate is structured (gate-mode, NASA-canonical convention, ADDENDUM trail). CHT benchmark gate should mirror the architecture. |
| 8 | `.planning/decisions/2026-05-30_v61_216_w21_substantive_distillation.md` | DEC-V61-216 distillation precedent — how a rule sub-DEC is structured (truth-chain table + W2.0.6 field citation + R0+R1 atomic Codex chain) |
| 9 | `.planning/decisions/2026-05-28_v61_211_solver_block_extractor.md` and `_v61_212_shm_dict_extractor.md` | Extractor precedent (single-region) — P3 multi-region extractors will be sub-DECs analogous to these |
| 10 | `~/Desktop/cfd-audit-merge/ui/backend/services/foam_agent_adapter.py:739` (and surrounding) | The "declared-only" code path that P3 needs to make runnable — concrete starting point for the implementation scope estimate |
| 11 | `.planning/case_profiles/case_002b_apu_bay_cht.md` (if extant — verify path) and `case_011_plate_fin_compact_hx.md` (verify) | CHT reference profiles already sedimented per DEC-V61-198 — survey what region-naming conventions they assume |
| 12 | `.planning/decisions/2026-05-07_v61_133_governance_simplification_b_plus.md` | v2.3 governance baseline (Kogami opt-in trigger semantics for charter-class DECs) |

---

## Open questions for user decision (resolve BEFORE charter draft)

These are **load-bearing** decisions — answer wrong, the charter is wrong. The
subagent that wrote this doc is not authorized to answer them.

1. **P3 scope: pure CHT solver only, or CHT + conjugate radiation?**
   Recommended (per Consideration 4): **pure conduction + convection in v0.1**.
   Conjugate radiation is separate compute-type complexity and would re-trip the
   scalar-space saturation by spreading data-contract work across two solver
   families. User to ratify.

2. **First CHT benchmark: plate-fin compact HX (industrial) or a textbook
   canonical (academic)?**
   Recommended pre-charter input: a textbook canonical case (e.g. Patankar §6 or
   Bejan compact-HX canonical) is faster to a DEC-V61-209-class V&V loop because
   the canonical reference is tabulated and citable. Industrial plate-fin (per
   DEC-V61-198 sediment) is the dogfood case for AFTER the V&V loop closes — same
   architecture as flat-plate (V&V) → APU-bay (dogfood). User decides which.

3. **Kogami opt-in for the P3 charter?**
   P3 satisfies the charter / governance-rule-change trigger (per V133). User to
   decide whether to invoke (independent strategic review on the 5 considerations
   above + benchmark selection) or skip (Codex APPROVE-only on the charter DEC).
   P2 sub-DECs did NOT invoke Kogami; P3 is structurally larger. Either choice
   defensible — must be made explicit in the charter frontmatter.

4. **Runnable laminar CHT first, or runnable turbulent CHT first?**
   Recommended: **start laminar.** Blueprint v4 §6 row 2 has buoyantFoam already
   runnable (laminar buoyancy-driven); building CHT laminar first reuses the
   wall-treatment validation work. Turbulent CHT can be a P3 follow-on. User to
   ratify or override.

5. **CHT V&V tolerance + benchmark cite at charter time, or in a sub-DEC?**
   The DEC-V61-209 path put tolerance + benchmark in the V&V DEC (sub-DEC, not
   charter). Recommended P3 charter does the same: charter names the **benchmark
   family** + **gate-mode shape** (Consideration 3 sub-questions 1+2), leaves
   exact tolerance number + canonical-conditions data file to a "DEC-V61-Y CHT
   benchmark V&V" sub-DEC. User to ratify.

---

## Explicit non-goals of this document

- **NOT a P3 charter.** No charter DEC ID assigned; no Status=Accepted; no Notion sync; no Codex review. The user spawns the charter DEC separately when the open questions above are resolved.
- **NOT a P3 phase plan.** The format precedent is `p2_plan_2026-05-27.md` — that document is authored AFTER the charter, by the cfd-chief-engineer (L2) or main session, and goes through its own sponsor approval before building.
- **NOT a feature implementation.** No code change recommended in this document; only charter-authoring considerations.
- **NOT a Codex review trigger.** Documentation per RETRO-V61-001 cadence; no `Codex-verified` trailer required on the commit that lands this file.
- **NOT a Kogami invocation.** Kogami strategic review (if user chooses opt-in per Consideration 5) is invoked on the **charter draft**, not on these notes.

---

## What "P3 ready-to-charter" means in STATE.md

STATE.md `last_updated` advance (ANCHOR-24) marks P3 as **READY-TO-CHARTER**, not
in-progress. The semantic distinction:

- **READY-TO-CHARTER** = the prior phase (P2) is structurally closed (all sub-DECs
  Accepted, no post-R3 defects, retrospective landed, considerations doc landed);
  the next phase's charter is the next decision a user can make. **No work
  starts** until the charter lands.
- **IN-PROGRESS** = the charter has landed Status=Accepted and an executor (cfd-chief-
  engineer L2 or main session) is building against a phase plan.

If the user wants P3 to enter IN-PROGRESS, the charter DEC must land first.
