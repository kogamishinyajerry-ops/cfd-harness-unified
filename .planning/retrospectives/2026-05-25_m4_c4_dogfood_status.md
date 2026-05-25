# M4 cycle 4 status · closed-loop dogfood · 2026-05-25

> Parent charter: DEC-V61-204 (Accepted) · sub-DEC
> commit `b8edb30` · 0 Codex (script + small fix) · 0 Kogami
> **Status: dogfood authored + loop validated to the solver boundary; live
> run BLOCKED on infra — charter NOT yet operationally complete.**

## 做了什么 (what)

- **`scripts/dogfood/m4_closed_loop.py`** (new): the charter's required dogfood.
  Asserts close-criterion 1-4 against a backend base-url: (1) POST /solve →
  exit_code 0 / converged; (2) /residual-series source flips off "empty" +
  /results-summary finite U stats; (3) /report-bundle 4 figures OR a classified
  matplotlib-500 fallback; (4) vitest reminder for no-regression. Setup/infra
  blockers (container down / case not imported / no mesh) → exit 2
  ("not exercised"), with precise remediation — **never a fabricated pass**.
- **404 fallback fix** in ReportFiguresPanel (real-backend discovery): unsolved
  cases return report-bundle 404 ("case not found", no working dir) or 409
  ("no time directories"); both now map to the friendly empty state, +1 test.

## 为什么 (why)

- C4 is the charter close gate: prove the C2 trigger + C3 display loop against a
  **real solver**, not just mock mode. The dogfood is the programmatic half of
  that proof (the charter literally says "verified by a dogfood script that
  asserts 1-4 programmatically").
- Running it against the live backend (8001) surfaced two real facts the
  mock-mode C2/C3 spot-checks couldn't: (a) the 404-vs-409 unsolved-case
  behavior (→ the fallback fix); (b) the precise live-run prerequisites.

## C4 live-run blocker (honest — why passes:true is NOT claimed)

Criteria 1-3 require an actual icoFoam run, which needs:
1. **cfd-openfoam container** — currently DOWN (only old `case028*` containers,
   exited 9 days ago). `run_icofoam` connects to a container named `cfd-openfoam`.
2. **A built case** — NO imported case has a `polyMesh` (none solvable).
   `lid_driven_cavity` isn't in the imported workspace at all (solve → 404);
   `circular_cylinder_wake` is imported with `system/controlDict` + geometry but
   no mesh (solve → would 409 mesh_missing).

Standing this up = bring up the container + run the full build pipeline
(import → mesh → BC) on a case + a ~60s solve. That is infra/pipeline work
beyond validating the (already shipped + tested) C2/C3 code, so it is the
charter's explicit remaining gate, surfaced to the user rather than fabricated.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ sub-DEC | under DEC-V61-204; commit-governed |
| Codex | ✅ N/A | dogfood script + 10-line classifier fix; no security boundary; <500 LOC |
| Kogami | ✅ N/A | opt-in; not summoned |
| Four-question gate | ✅ 4/4 | unchanged (engineer-initiated · LLM-offline · artifacts · advisory-only) |
| Build / tests | ✅ green | tsc -b exit 0 · vitest 838 (criterion 4 holds) · ReportFiguresPanel now 8 |
| Visual spot-check | ✅ N/A (documented) | no UI change beyond the 404→empty classifier (covered by unit test); C2/C3 spot-checks stand |
| Dogfood live run | ⏭ exit 2 (blocked) | solver/case not ready — precise remediation printed; criteria 1-3 not exercised |
| Push | ✅ b8edb30 | dbc2cee..b8edb30 |

## 下次候选 (next) — user decision

The M4 **implementation** is complete + shipped (C1 charter · C2 run-trigger ·
C3 report display), fully unit-tested, Codex-reviewed, and mock-mode visually
verified. The remaining work is the **live e2e run** to flip C4 to passes:true:

- **Option A — stand up the live run**: bring up cfd-openfoam, build a case
  (LDC is the smallest: import → blockMesh → BCs), run the dogfood end-to-end,
  capture a real-backend visual spot-check, then mark the charter operationally
  complete. Heavier infra work; may surface case-build issues.
- **Option B — accept impl-complete + dogfood-ready**: treat C4's live run as a
  documented gate to run when the solver env is up (the dogfood is ready and
  will assert 1-4 the moment a built case + container exist). Move to the next
  milestone now.

## Bottom line

C2+C3 wired the V4 closed loop end-to-end and it's proven in mock mode + at the
API layer up to the solver boundary. The only thing standing between here and
charter-complete is a real OpenFOAM run, which needs infra stood up — a clean
decision point, not a hidden failure.
