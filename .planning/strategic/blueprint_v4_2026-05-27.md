# Blueprint v4 · Vertical-First, Runnable-Coverage CFD Workbench · 2026-05-27

> **Authored**: 2026-05-27 by Claude Code Opus 4.7 (1M context), as a commercial-CAE design engineer.
> **Triggered by**: User request to deeply rethink the development blueprint / path / planning, after the M5.5 truth-chain de-fake + manifest→WorkbenchBasics deriver (DEC-V61-206) exposed how far the trust layer had outrun the runnable engine.
> **Ratified by**: User, 2026-05-27 — chose **Strategy A (vertical-first)**, first vertical **incompressible RANS aero**, and "write as Blueprint v4 charter".
> **Charter DEC**: DEC-V61-207.
> **Evolves (as product-blueprint layer)**: `blueprint_v3_2026-05-07.md` — keeps its North Star, 4-region UI, and four-question gate; adds three laws (runnable-coverage, V&V loop, AI distillation) and selects a strategy.
> **Does NOT supersede**: DEC-V61-130 (AI-advisor pivot), DEC-V61-198 (APU container philosophy — corrected, not rejected), individual sub-DECs.
> **Memory mirror**: `~/.claude/projects/-Users-Zhuanz/memory/project_cfd_harness_blueprint_v4.md` (to be written).

---

## 0. North Star (unchanged from v3, sharpened)

> An open, **OpenFOAM-backed** CFD workbench whose UI **structurally cannot lie** (real-derived data or honest 待识别, never fabrication), whose simulation pipeline **runs without the AI in the loop**, and whose AI is a **versioned, offline, deterministic diagnostic ruleset distilled from real failure experience** — advisory, never a driver.

The moat is **trust + auditability + a distilled failure corpus**, not feature parity with Fluent/STAR-CCM+.

---

## 1. The diagnosis that motivated v4

The project grew **two layers at very different rates**:

| Layer | State (2026-05-27) | Evidence |
|---|---|---|
| **Knowledge / Trust** | Deep, ahead of commercial tools | Truth-chain (survived a 3-round Codex faithfulness drill on the deriver), TrustGate, gold standards, byte-repro/signing, **V-series 85+ real death-chains**, 12+ compute-type *profiles* |
| **Runnable engine** | Narrow | Executor runs **incompressible RANS + buoyant-transient only** (icoFoam/simpleFoam/pimpleFoam/buoyantFoam). `buoyantSimpleFoam` / `chtMultiRegionSimpleFoam` / `rhoCentralFoam` are **declared in `solver_derivation.py` but route to safe defaults — not runnable** (`foam_agent_adapter.py` dispatch; the old `:739` line ref is stale — see DEC-V61-224, which also re-diagnosed the deeper OF10/ESI-vs-OF11/foamRun runner fork). ~4 academic RANS cases confirmed end-to-end **via the `cfdtrust` OF11 backend, not this adapter**. |

**The APU-bay industrial case ran in an external sandbox with hand-written templates, not through the workbench executor.** So "the workbench does industrial CFD" was true only via *engineer + Claude + external templates*.

**The latent risk**: a tool that documents a death-chain for ONERA M6 transonic but cannot run a compressible solver. The inversion (trust-first) is *correct* for a regulated/aerospace audience; the *error* is that "coverage" was allowed to mean **documented** when, for an engineering tool, it must mean **runnable + validated**.

---

## 2. Three laws added in v4

### Law 1 · Runnable-coverage
A compute type is **"covered" only when its solver runs end-to-end AND a benchmark passes its tolerance gate.** Profiles, reference pointers, and death-chains are **knowledge**, not coverage. This corrects the DEC-V61-198 accounting (which let profiled cases count as coverage) **without rejecting** its container-of-experience philosophy — the flywheel stays, the unit of progress changes.

### Law 2 · The V&V loop is a first-class flow
`run → compare-to-gold → quantified error → TrustGate verdict`, with the v9 ruleset's `GOLD_DELTA_EXCEEDS_5_PCT` (R4) as the gate. ~80% built (gold standards + checkMesh + v9 R4 exist); v4 **closes it as one product flow**. This is the credibility feature: every result the tool produces carries a quantified error vs a benchmark.

### Law 3 · AI productization path (explicit)
> **The Claude Code session is the senior engineer who distills death-chains into the versioned offline ruleset; the ruleset ships and runs without AI.**

The product's "AI" is **the v9 ruleset + its growth process**, not live inference. Today: V-series 85+ findings → v9 ruleset only **8 rules** (`ui/backend/services/v9_advisor/rules.py`), and the matcher only consumes *post-hoc* residual/force stats. The distillation gap + the missing *pre-flight* signals are the AI roadmap (P2). This is how "AI advisor" survives reaching a customer with no Claude Code.

---

## 3. Strategy: A · Vertical-first (chosen)

Pick **1–2 compute types**, make them bulletproof end-to-end before adding the next. Redefine "covered" = runnable + benchmark-passed.

**First vertical: incompressible RANS aero** (external + wall-bounded — flat plate, airfoil, turbine cascade). Rationale: already has a runnable base; fastest path to a closed V&V loop; kΩSST is wired (validate y+/wall-treatment + mesh robustness); aligns with the user's aerospace domain where validated-narrow beats unvalidated-broad.

**Rejected alternative (B · advisory cockpit)**: ingest artifacts from any external OpenFOAM run and only review/diagnose. Rejected because trust is most valuable attached to results the tool *produces*, and certification rewards V&V depth over breadth.

---

## 4. Development path (risk-first)

| Phase | Goal | Exit gate |
|---|---|---|
| **P1 · Harden the RANS-aero vertical** | Mesh robustness on real curved CAD (fix gmsh-F2 prism-on-curved failure / commit sHM layer path); validate kΩSST wall treatment + y+; **close the V&V loop** on flat-plate / airfoil / turbine-cascade | ≥1 benchmark passes tolerance gate end-to-end through the workbench, with quantified error shown in TrustGate |
| **P2 · Close the AI loop on the vertical** | (a) **Pre-flight signals** = mesh-quality + BC-consistency + y+ estimate + regime-check as structured artifacts; (b) expand v9 ruleset to consume them → distill the *setup-class* V-series findings; (c) **pre-flight review** (catch setup errors before solve) | v9 ruleset grows from 8 → covers the top setup-error classes; review runs offline + advisory-only on a real case |
| **P3 · Add CHT (2nd compute type)** | Wire `chtMultiRegionSimpleFoam` **end-to-end** (currently declared-only) → validate (plate-fin / blade cooling) → sediment death-chains | CHT benchmark passes tolerance gate; runnable-coverage = 2 |
| **P4+ · Compressible, then the rest** | rhoCentralFoam (ONERA M6) → VOF → LES…, each gated on runnable + validated | each new compute type runnable + benchmark-passed before the next |
| **Continuous** | Clear the 3 cosmetic fakes (§5); grow v9 from V-series; monthly industrial dogfood **but each new compute type must become runnable, not just profiled** | truth-chain brand stays spotless; corpus→ruleset flywheel turning |

**Explicitly deferred**: DOE/optimization UI (honestly 示意 today — keep), sizing-field / region-refinement UI (DEC-V61-198 already downgraded — template+YAML suffices), broad physics UI before the runnable path exists.

**Solver-environment / image-reconciliation provision** *(added 2026-06-03 · DEC-V61-224)*: "Runnable" (Law 1) is **image-gated**. The OpenFOAM **Foundation** fork (`foamRun -solver <module>`) and the **ESI** fork (named solvers, e.g. `chtMultiRegionSimpleFoam`) ship different solver sets. Before a phase claims a compute type as a runnable target it MUST pin **(a)** which fork/image provides the solver, **(b)** that the workbench execution backend (`foam_agent_adapter`) is wired to that image and **reconciled with** the `cfdtrust` V&V backend — not divergent from it, and **(c)** a fallback (remote/CI runner) if the solver cannot run on the local image. *P3 surfaced this the hard way: the charter wired CHT's exit gate through `foam_agent_adapter` → a nonexistent Foundation-OF10 image + the ESI-only name `chtMultiRegionSimpleFoam`, while the only runnable backend (`cfdtrust`) uses Foundation-OF11 via `foamRun`. P4 (rhoCentralFoam) + P4+ (VOF/LES/MRF) inherit this provision.*

---

## 5. Truth-chain debt to clear (continuous, small, high brand-value)

Localized fabrication that survived the M5.5 de-fake (each undercuts the brand when seen):
- `TopBarV4.tsx:51` — `STATIC_CLUSTER = "Cluster-01 [128 核]"` (no backend) → wire real host meta or remove.
- `solverBlueprint.ts:19-69` — `SOLVER_BLUEPRINT_KPIS` + GPU/CPU/MEM telemetry chips (marked "preview") → real solver-host endpoint or honest 待识别.
- `doeBlueprint.ts` — DOE mode fully illustrative (honestly marked) → keep until a DOE backend exists.

Default: **remove / honest-mark now** rather than carry "preview" fakes.

---

## 6. Compute-type coverage map — REFRAMED by Law 1

Status = **runnable** (not documented). Profiles/death-chains tracked separately as *knowledge*, not coverage.

| Compute type | Runnable? | Knowledge (V-series / profile) | Target phase |
|---|---|---|---|
| Incompressible RANS (wall-bounded / external) | ⚙️ partial → **P1 target** (validate + V&V loop) | flat plate / pipe / cavity / Couette + turbine cascade | **P1** |
| Internal + buoyancy (transient) | ✅ buoyantFoam runnable | APU bay (external sandbox) | — (validate later) |
| CHT (conjugate heat transfer) | ❌ declared-only | case_002b, plate-fin profile | **P3** |
| Compressible / transonic | ❌ declared-only | ONERA M6 / RAE M2129 profiles | P4 |
| Multiphase / VOF | ❌ not wired | KCS ship profile | P4+ |
| Rotating machinery (MRF/SRF) | ❌ not wired | NREL phase VI profile | P4+ |
| Combustion / reacting | ❌ not wired | Sandia Flame D profile | P4+ |
| Transient LES / DES | ⚙️ pimpleFoam base | DrivAer / M219 profiles | P4+ |

---

## 7. Kept from v3 (unchanged)

- **4-region UI** (TopBar / Process Spine / Viewport+Artifacts / Engineer Control Rail / Truth Chain). Do not diffuse pages.
- **Four-question gate** on every PR/DEC: (1) LLM-offline runnable? (2) clear artifacts? (3) TrustGate/completeness/audit explains trust? (4) AI advisory-only, no mutating route?
- **AI = advisor, not driver** (DEC-V61-130); `MUTATING_ROUTES` / `KNOWN_MUTATION_FUNCTIONS` interception.
- **Container-of-experience** philosophy (DEC-V61-198) — corrected by Law 1, not rejected.

---

## 8. Governance alignment

- **CLAUDE.md v2.3** — Opus 4.7 primary / Codex relay (round cap=3) / Kogami opt-in / Notion archive.
- **Kogami**: this is a charter / direction change — Kogami strategic review is *available* (opt-in) but **not invoked** unless the user requests it.
- Priority on conflict: top-level CLAUDE.md > this blueprint v4 > roadmap_v2 > individual DEC.

**One-line**: *Validated-narrow beats documented-broad. Cover one vertical end-to-end, close the V&V loop, distill the corpus into the offline ruleset — then earn the next compute type.*
