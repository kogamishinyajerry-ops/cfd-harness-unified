---
decision_id: V61-224
title: P3 solver-environment re-assessment — runner/image fork re-diagnosis + Blueprint v4 provision (charter addendum to DEC-V61-217)
status: Accepted
accepted_date: 2026-06-03
parent_dec: V61-217 (P3 CHT charter — this corrects its W3.2/W3.3 runnability premise)
sibling_decs: V61-223 (W3.2a generation side — corrects its §Context docker-SDK blocker claim) · V61-210 (cfdtrust canonical V&V runner — the actually-runnable backend) · V61-207 (Blueprint v4 charter — §4 amended here)
phase: P3 (Blueprint v4) · charter addendum / strategic re-assessment
autonomous_governance: true
confidence: high
kogami_opt_in: false (documentation-only strategic correction, user-directed in 2026-06-03 takeover; the EXECUTABLE reconciliation A/B is a separate future DEC that WILL carry Codex)
codex_review_relay: N/A — documentation/strategic addendum, zero code/security surface (per the p3_cht_kickoff_considerations.md documentation-class precedent · RETRO-V61-001 cadence)
codex_verdict: N/A (no code change)
notion_sync_status: synced 2026-06-03 (https://app.notion.com/p/374c68942bed812bac03fd819b087cec)
touches_shared_dec: V61-217 (charter exit-gate premise) · V61-223 (§Context correction) · V61-207 (Blueprint v4 §4)
date: 2026-06-03
ratified_by: user (chose "先战略复核 + charter addendum" in 2026-06-03 takeover); diagnosis from a 5-agent read-only verification fan-out + direct adapter/cfdtrust grep
---

# DEC-V61-224 · P3 solver-environment re-assessment (charter addendum)

## Context

A 2026-06-03 deep-takeover audit (5 independent read-only verification agents +
direct grep of `src/foam_agent_adapter.py` and
`ui/backend/audit/cfdtrust/backends/openfoam.py`) re-examined why P3's runnable
core has not advanced (runnable-coverage frozen at **1** through W3.0/W3.1/W3.2a).
It found that the charter (DEC-V61-217) and the W3.2a sub-DEC (DEC-V61-223)
**mis-identify the W3.2b live-run blocker**, and that the true blocker is a
**two-backend runner/image fork** the project has not reconciled. This addendum
records the corrected diagnosis, holds runnable-coverage at 1, pauses forward
W3.2, and amends Blueprint v4 §4 — but **defers the executable A/B decision to
the user**.

## Re-diagnosis (what is actually true)

**Refuted claim** (DEC-V61-223 §Context, lines ~35-37): *"the environment has the
docker CLI + OpenFOAM images but NOT the docker Python SDK (so live execution
short-circuits)."* This is **FALSE**: under the project runtime
`uv run python -c "import docker"` → **7.1.0** (importable). Only the bare-system
`python3` lacks it — irrelevant, since the adapter runs under `.venv`/uv.

**The real root — a two-backend runner/image fork:**

| Backend | Wiring | Runnable here? |
|---|---|---|
| `src/foam_agent_adapter.py` — the **charter's chosen** TaskSpec→solver path (W3.2/W3.3 exit gate routes through it) | Hardwired to Foundation **OF10**: image `cfd-workbench/openfoam-v10:arm64` (`:605`), container `cfd-openfoam` (`:529`), `source /opt/openfoam10/etc/bashrc` (`:8386`); ESI-only solver name `chtMultiRegionSimpleFoam` (`:778`). Zero `foamRun`/OF11 awareness. | ❌ image + container **absent on disk** |
| `ui/backend/audit/cfdtrust/backends/openfoam.py` — the V&V runner (DEC-V61-210) that produced **runnable-coverage = 1** | Foundation **OF11** image `openfoam/openfoam11-paraview510` (present on disk; `flat_plate`/`channel_flow` `solver.log` show `foamRun -solver incompressibleFluid`) | ✅ runs |

OF11 (Foundation) has **no** `chtMultiRegionSimpleFoam` binary (it is an
ESI-Group solver name); OF11 does CHT via **`foamRun -solver multiRegion`**
(`foamRun` + `libsolid.so` confirmed present in the OF11 image). So the charter
wired P3's exit gate (`TaskSpec → foam_agent_adapter → chtMultiRegionSimpleFoam →
audit`, DEC-V61-217 W3.2/W3.3 rows) to a path that **cannot run in this
environment** — a dead OF10 image + an ESI solver name the present OF11 fork
does not provide.

**Not all bad news**: the W3.2a R1 verification DID run `blockMesh` on the
generated case in the ESI `opencfd/openfoam-default:2312` image →
`Writing polyMesh with 3 cellZones` (region_hot_fluid 160 / region_solid 80 /
region_cold_fluid 160, 7 region-prefixed patches). So the generated topology is
live-valid; `splitMeshRegions -cellZones` + the solve are what remain unproven.

## What this addendum changes (Accepted)

1. **runnable-coverage stays at 1.** Under Blueprint v4 Law 1, W3.0/W3.1/W3.2a
   are *knowledge/scaffolding*, not coverage — no CHT solver has run. STATE must
   not read "P3 progressing" on the basis of green offline slices.
2. **Forward W3.2 is PAUSED** (W3.2c producer-side / W3.2d R15-R16 reground do
   not land) until the A/B runner decision below is made — to stop the offline
   stack growing around an unrunnable core (the exact pathology Blueprint v4 was
   authored to end: "the trust layer outran the runnable engine", §1).
3. **DEC-V61-223 §Context corrected** (docker-SDK claim → this re-diagnosis;
   audit trail preserved inline) and finalized to Accepted.
4. **Blueprint v4 §4 amended** with a **solver-environment / image-reconciliation
   provision** (below) — the blueprint assumed every compute type is locally
   runnable; the OF-Foundation-vs-ESI fork split breaks that assumption, and
   **P4 (rhoCentralFoam) + P4+ (VOF/LES) will re-hit the same wall**.

## The decision that is now OPEN (user)

This addendum does NOT pick the runner path — it surfaces it as the next
load-bearing decision:

- **Option A — reconcile + run (honors Law 1, closes P3).** Re-target
  `foam_agent_adapter` from the dead OF10/ESI wiring to the OF11 image +
  `foamRun -solver multiRegion` convention the `cfdtrust` backend already drives
  (image on disk). Then run W3.2a's generated case end-to-end →
  `splitMeshRegions -cellZones` → solve → audit → flip runnable-coverage **1→2**
  and dissolve the two-backend fork. This is a real W3.2b code/infra slice
  (its own sub-DEC + Codex), but the infrastructure is present, not missing.
- **Option B — stay offline, freeze coverage=1, document the gap.** Resume the
  offline W3.2c/d slices, hold coverage at 1, and add a remote/CI solver runner
  to the blueprint as future work. Honest scaffolding; defers the run.

**Latent-risk check required before either** (cheap, high-info): confirm whether
runnable-coverage = 1 (RANS) even executes through `foam_agent_adapter` in THIS
environment — it was validated via `cfdtrust`, NOT the adapter, whose wired OF10
image is absent. If the adapter cannot run RANS either, the fork is a
project-wide execution-path staleness, not a CHT-only issue.

## Blueprint v4 §4 amendment (provision added)

> **Solver-environment / image-reconciliation provision (added 2026-06-03,
> DEC-V61-224).** "Runnable" (Law 1) is image-gated: the OpenFOAM **Foundation**
> (`foamRun -solver <module>`) and **ESI** (named solvers, e.g.
> `chtMultiRegionSimpleFoam`) forks ship different solver sets. Before a phase
> claims a compute type as a runnable target, it MUST pin (a) which fork/image
> provides the solver, (b) that the workbench execution backend
> (`foam_agent_adapter`) is wired to that image — reconciled with the `cfdtrust`
> V&V backend, not divergent from it — and (c) a fallback (remote/CI runner) if
> the solver cannot run on the local image. P3 surfaced this; P4 (rhoCentralFoam)
> and P4+ (VOF/LES/MRF) inherit it.

## Governance (DEC-level meta)

- `autonomous_governance: true` (counter +1 on Accept).
- **Codex/Kogami: skipped** — documentation/strategic correction, no code or
  security-boundary surface (mirrors the `p3_cht_kickoff_considerations.md`
  documentation-class precedent). The **executable** reconciliation (Option A)
  is a separate future sub-DEC that WILL carry the full Codex round-cap=3 chain.
- Four-question gate: N/A to a documentation addendum (no runnable surface, no
  artifact mutation, no advisor route).
- Notion: `pending_accepted` → session-end batch (Accepted-only sync rule).

## Evidence appendix

- `uv run python -c "import docker"` → `7.1.0`; `python3` → ModuleNotFoundError.
- `docker images` → `openfoam/openfoam11-paraview510:latest` only; no OF10 / no
  `cfd-workbench/openfoam-v10`; no `cfd-openfoam` container.
- `src/foam_agent_adapter.py`: `:529` `CONTAINER_NAME="cfd-openfoam"` · `:605`
  image `cfd-workbench/openfoam-v10:arm64` · `:778` `solver_name="chtMultiRegionSimpleFoam"`
  · `:8386` `source /opt/openfoam10/etc/bashrc`; `grep foamRun|multiRegion` → 0 hits.
- `ui/backend/audit/cfdtrust/backends/openfoam.py` + `cases/*/artifacts/solver.log`
  → OF11 `openfoam/openfoam11-paraview510` via `foamRun -solver incompressibleFluid`.
- `reports/codex_tool_reports/v61_223_w32a_report.md` R1 → blockMesh in ESI
  `opencfd/openfoam-default:2312` → "Writing polyMesh with 3 cellZones".
- DEC-V61-217 W3.2/W3.3 rows → exit gate routes `foam_agent_adapter →
  chtMultiRegionSimpleFoam`; Blueprint v4 §1 names `foam_agent_adapter.py` the
  "declared-only" path (the v4-motivating diagnosis, here recurring in P3).

— cfd-chief-engineer (L2), 2026-06-03 takeover audit
