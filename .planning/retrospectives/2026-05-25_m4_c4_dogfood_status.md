# M4 cycle 4 close · closed-loop dogfood + LIVE e2e · 2026-05-25

> Parent charter: DEC-V61-204 (Accepted) · sub-DEC · **M4 phase-close retro**
> commits `b8edb30` (dogfood + 404 fix) · `<this>` (live-run dogfood fix)
> 0 Codex · 0 Kogami
> **Status: C4 PASSES — closed loop proven against a REAL OpenFOAM 10 solve.
> M4 charter operationally COMPLETE.**

## 做了什么 (what)

- **`scripts/dogfood/m4_closed_loop.py`** (new): asserts the charter
  close-criterion 1-4 against a running backend. Setup/infra blockers exit 2
  ("not exercised"), never a fabricated pass.
- **404 fallback fix** in ReportFiguresPanel: unsolved cases 404/409 → friendly
  empty state (not a crit error). Real-backend discovery.
- **Stood up the live OpenFOAM 10 run** (user chose "stand up the live run"):
  pulled `openfoam/openfoam10-paraview56` (amd64), started it under
  `--platform linux/amd64` emulation as `cfd-openfoam` (entrypoint override
  `tail -f /dev/null`; USER 98765 matches the harness's expected uid).
  Verified icoFoam/gmshToFoam/blockMesh execute under QEMU emulation.
- Drove the full live pipeline + closed-loop assertion.

## C4 LIVE-RUN EVIDENCE (passes:true)

`smoke_simulation.py --base-url http://127.0.0.1:8001 --case backward_step`
→ **all F-series invariants PASS**: STL upload → gmsh mesh (2829 cells) →
setup-bc → **real icoFoam solve converged=True wall_time 1.5s** → run-history /
results-summary / field U+p all 200.

`m4_closed_loop.py --case-id imported_2026-05-25T09-00-12Z_9da7c214`:
1. ✅ POST /solve → 200 · converged=True · wall_time 1.48s (real icoFoam).
2. ✅ /residual-series source flipped `empty`→`log`; /results-summary finite
   U-magnitude stats (max=0.2783, 2829 cells).
3. ✅ /report-bundle → 200 · 4 artifacts · plane=[x,y].
4. ✅ no regression: V4 vitest 838 green.

Real-backend V4 Post visual spot-check (port 5188 → backend 8001, `/tmp/c4_spot/`):
all 4 figure cards present; the `|U| + 流线` card renders a **real matplotlib
PNG** (naturalWidth 1455 × 448, complete); provenance line
"v2_000000 · t=2s · 2,829 cells · lid_driven_cavity". **No page errors.**

## 为什么 (why)

- C4 is the charter close gate — prove the C2 trigger + C3 display loop against
  a real solver, not just mock mode. Done: a real icoFoam run produced real
  matplotlib figures shown in the V4 Post UI, end to end.
- The live run earned its keep by surfacing **two real bugs** mock mode missed:
  (a) unsolved cases 404/409 (→ ReportFiguresPanel fallback fix, in b8edb30);
  (b) my dogfood's `results-summary` assertion assumed a nested `u_magnitude`
  dict, but the live schema is flat `u_magnitude_{min,max,mean}` (fixed here).

## Infra note (load-bearing for re-running C4)

The solve/mesh stack hardcodes OpenFOAM 10 (`/opt/openfoam10/etc/bashrc`, 6
services + adapter). Host is arm64; Foundation OF10 is amd64-only, so the
`cfd-openfoam` container runs **under x86 emulation** (icoFoam LDC-class solves
complete in ~1.5s emulated — fine for dogfood; large meshes would be slow).
Bootstrap: `docker run -d --platform linux/amd64 --name cfd-openfoam
--entrypoint tail openfoam/openfoam10-paraview56:latest -f /dev/null`. The
container is left running for future live runs.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ sub-DEC | under DEC-V61-204; M4 phase-close retro |
| Codex | ✅ N/A | dogfood script + assertion fix; no security boundary |
| Kogami | ✅ N/A | opt-in; not summoned |
| Four-question gate | ✅ 4/4 | engineer-initiated solve · LLM-offline (icoFoam, no LLM) · canonical artifacts (run + PNGs) · advisory-only |
| Build / tests | ✅ green | vitest 838 (criterion 4) · live solve converged |
| Visual spot-check | ✅ PASS (real backend) | real matplotlib figures in V4 Post; no page errors |
| Dogfood live run | ✅ criteria 1-3 PASS (exit 0) | against real OpenFOAM 10 solve |
| Push | ⏳ pending | this retro + dogfood fix |

## 下次候选 (next)

M4 is operationally complete (C1 charter · C2 trigger · C3 display · C4 live
proof). The V4 post-Step-7 closed loop — build → Run → results → report — works
end to end against a real solver. Next milestone is a fresh charter (per the
M1-M6 roadmap v2); candidates: M5 post-processing depth or the deferred
GPU/CPU/temp telemetry (explicitly out-of-scope in DEC-V61-204). Await user
direction on the next milestone.

## Bottom line

The M4 charter is met: a real icoFoam solve, triggered from the V4 workbench,
refreshes results and renders real matplotlib report figures in V4 Post — the
closed loop the charter set out to wire, proven against a real solver.
