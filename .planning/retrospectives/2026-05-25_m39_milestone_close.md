# M3.9 milestone close · 2026-05-25

> Parent charter: `DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED`
> 1 cycle · spike-class · 0 DEC files · 0 Codex rounds · 0 Kogami · final commit `f8c895d`

## 做了什么 (what)

1. **Closed B4 as WON'T-FIX (BY-DESIGN)** — the last open finding from the
   2026-05-25 M3.2 visual audit (left-rail dead vertical space, P3). No code
   change to `LeftRailV4.tsx`. Disposition + evidence written to
   `.planning/backlog/m32_visual_audit_findings_2026-05-25.md`.
2. **Hardened `scripts/dogfood/workbench_visual_spot_check.mjs`** — added
   `--base-url` / `--port` flags (default `$CFD_FRONTEND_PORT` or 5180, matching
   vite.config). Removed the hardcoded `localhost:5173` that disagreed with the
   project's own vite default.
3. **Captured B4 evidence screenshot** at `/tmp/m39_b4_check/` (empty seed,
   step=geometry) — first spot-check run of this session, validating the
   hardened tool end-to-end.

## 为什么 (why)

- **B4 is not a defect.** industrial-ui-comparator (parity 8/10, high
  confidence) confirmed empty surface below a top-anchored model tree is the
  industry-standard norm — Hyperworks Model Browser, Abaqus/CAE Model Tree,
  ANSYS Mechanical Outline, Simcenter Sim Navigator all leave it empty. Filling
  it (minimap / recent-activities / `flex-1` stretch) would be an anti-pattern
  that *reduces* parity, and completeness % is already surfaced in 3 places
  (LeftRailV4 tree rows, RightPanelV4 CompletenessCard, BottomBarV4). The
  cautious-engineer call was to verify-then-close, not fabricate a fix for a
  phantom defect. Explore agent confirmed no reusable footer was needed and
  none should be built.
- **The spot-check port bug was load-bearing.** The mandate requires running
  `workbench_visual_spot_check.mjs` before every cycle close, but its hardcoded
  `:5173` broke the instant vite used its real default (5180). Discovered the
  hard way: a stale StructureOptimizer `vite preview` was squatting IPv6
  `[::1]:5180`, so `localhost` resolved IPv6-first and playwright hit the wrong
  app. Fixed by (a) the `--base-url`/`--port` flags and (b) targeting explicit
  `127.0.0.1`. Per port rule: did NOT kill the StructureOptimizer process
  (not mine); restarted only my own vite on free port 5188 → backend 8001.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ spike-class | ≤30 LOC (10 ins / 6 del), no schema/contract break → commit-message-only, no DEC file |
| Codex round cap=3 | ✅ N/A | 0 rounds — no security boundary / byte-repro / auth path touched |
| Kogami opt-in | ✅ not invoked | no user召唤; no charter-class trigger |
| Four-question gate (V130) | ✅ Y/Y/Y/Y | LLM-offline (dev tool + cosmetic disposition) · artifacts canonical (PNG + markdown) · TrustGate (disposition cites comparator + file:line) · AI advisory-only (comparator advised, Opus decided; no AI auto-writes) |
| Port rule | ✅ honored | did not kill StructureOptimizer squatter; used free port 5188 |
| Date/schedule gating | ✅ none | |
| Visual spot-check before close | ✅ done | `/tmp/m39_b4_check/*.png` |
| Surface-scan (V61-088) | ✅ trailer present | found StatusStrip v3 footer pattern · disposition: not-reused (redundant) |
| Multi-agent crew | ✅ used | industrial-ui-comparator (parity verdict) + Explore (reuse scan), parallel, ≤800/600 token budgets |

## 下次候选 (next)

M3.2-M3.9 closed. Visual-audit backlog now fully drained (B1/B2/B3/B5/B6 closed
in M3.4; B4 closed BY-DESIGN here). Remaining candidates:

- **M3.10 = vtk.js proxy bug root-fix (P2)** ← *picked for immediate next milestone*.
  Guard the unguarded `new Proxy(null, ...)` in ViewportV4's vtk.js bootstrap
  (located at `RenderWindow.js:243` per M3.4 cycle-5 subagent). Removes the need
  for the `--use-gl=swiftshader` headless workaround and the M3.4 B1 partial-fix
  caveat (authored cases still hit the proxy bug in headless). Real engineering
  value, higher than cosmetic.
- **M4 charter scoping** (deferred) — post-Step-7 solver_run / results / report /
  Notion sync. Multi-day; needs Kogami opt-in (user must召唤). NOT started
  autonomously per v2.3.
- Carry-overs: vscode:// jump · raw YAML viewer modal · "replace whole node" UI
  recovery · backend `gap.why` enrichment · workbench-basics ↔ manifest
  cross-validation.

## Bottom line

M3.9 is the lightest possible honest milestone: one phantom finding retired with
a defensible industrial-parity verdict, one latent infra bug fixed so every
future visual cycle works. Zero fabrication, zero process pollution. The
visual-audit backlog is empty; the next milestone moves to real correctness
work (vtk.js proxy root-fix).
