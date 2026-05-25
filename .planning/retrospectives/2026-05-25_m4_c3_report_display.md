# M4 cycle 3 close · V4 report-bundle display · 2026-05-25

> Parent charter: DEC-V61-204 (Accepted) · sub-DEC
> commit `bd40329` · 1 Codex round (R0 CHANGES_REQUIRED → R1 RESOLVED) · 0 Kogami

## 做了什么 (what)

Surfaced the backend matplotlib figure bundle (contour-streamlines / pressure /
vorticity / centerline) inside the V4 Post right column.

- **`useReportBundle.ts`** (new): React Query `GET /report-bundle`, key
  `["v4-report-bundle", caseId]`, 60s staleTime, errors surfaced for the
  component to classify. Auto-fetches (no AI-run button — advisor-not-driver).
- **`ReportFiguresPanel.tsx`** (new): stacked figure cards + provenance line
  (cache_version / cell_count / case_kind), captions derived from `plane_axes`.
  Classified graceful fallback — **never a crash** (charter requirement):
  409 → "no run yet" · 500+matplotlib → "report unavailable on this build" ·
  503/other → error state.
- **`ModeRendererPost`**: mounts the panel after `ConvergenceGauge`.
- **`useSolveRun`**: now also invalidates `v4-report-bundle` on solve success,
  so a fresh run re-renders the figures (ties C2→C3).
- **`handlers.ts`**: report-bundle MSW mock (SVG data-URI figures).

## 为什么 (why)

- C3 completes the *display* half of the M4 closed loop (C2 was the trigger):
  the V3→V4 consolidation left these figures behind in the retired
  Step5ResultsGrid. Now built cases show their research-grade figures in V4.
- The fallback classification is the charter's explicit ask: a `.[ui]` build
  without matplotlib returns HTTP 500 ("matplotlib is required") — V4 must show
  an honest "unavailable on this build" state, not a crash or a silent blank.
- **Codex earned its round** (2 real P2 correctness bugs, not style):
  (1) `removeQueries()` doesn't refetch an active observer in TanStack Query v5
  → stale card stuck; (2) hardcoded x-y captions are wrong on x-z/y-z slabs.
  Both fixed verbatim; a regression test now locks the plane_axes captions.
  This is exactly the "LOC>500 risk surface → run Codex, don't override"
  governance path (the diff was 509 LOC, mostly the new component + tests).

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ sub-DEC | under charter DEC-V61-204; commit-message-governed |
| Codex | ✅ R0→R1 RESOLVED | 509 LOC tripped RISK_LOC_THRESHOLD=500 → ran `codex-review-relay --base origin/main` (86gs gpt-5.4 xhigh, per CLAUDE.md, NOT override); 2×P2 fixed verbatim; round cap not approached |
| Kogami | ✅ N/A | opt-in; not summoned |
| Four-question gate (V130) | ✅ 4/4 | LLM-offline · canonical artifacts · TrustGate (provenance) · advisory-only (read-only) |
| Build / tests | ✅ green | tsc -b exit 0 · vitest 838 passed (79 files); +7 ReportFiguresPanel +3 useReportBundle |
| Frontend gate (M3.13) | ✅ fired+Passed | touched `.tsx` → tsc -b ran |
| Visual spot-check | ✅ PASS | mock mode: 4 figures render in V4 Post with provenance line; first img naturalWidth>0 (`/tmp/c3_spot/`) |
| Cadence | ✅ Passed | Codex-verified trailer on HEAD reset the floor |
| Push | ✅ bd40329 | 9de8683..bd40329 · admin direct-push |

## 下次候选 (next)

- **C4 · e2e dogfood + close retro** — the charter's final cycle. Real backend
  (circular_cylinder_wake or lid_driven_cavity): build → **Run** (C2) → results
  refresh → **report figures** (C3), with a scripted dogfood asserting the
  charter close-criterion 1-4 programmatically + a real-backend visual
  spot-check. This is where the run-trigger and figures get their real-solver
  proof (mock-mode covered the UI surfaces in C2/C3). On C4 pass the M4 charter
  is operationally complete.

## Bottom line

The V4 Post step now shows the backend report figures as provenance-labelled
canonical artifacts, with an honest fallback for matplotlib-absent builds. With
C2 (trigger) + C3 (display) landed, the closed loop is wired end-to-end inside
V4; C4 proves it against a real solver and closes the charter.
