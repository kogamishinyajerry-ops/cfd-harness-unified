---
decision_id: DEC-V61-205
title: M5 charter — V4 post-processing depth (truth-chain: real overlays, no fake telemetry)
status: Accepted
parent_dec: DEC-V61-204-M4-POST-STEP7-CLOSED-LOOP (M4 closed loop · operationally complete)
phase: M5 cycle 1 (charter scoping · continuation session 2026-05-25)
notion_sync_status: synced 2026-05-25 (https://www.notion.so/36bc68942bed8144a947ce2a9baef9a6)
autonomous_governance: false
confidence: high
date: 2026-05-25
ratified_by: user (chose "M5 post-processing depth" as next milestone 2026-05-25)
---

# DEC-V61-205 · M5 charter — V4 post-processing depth

## TL;DR

Deepen V4 Post so it shows **real** post-processing, not blueprint placeholders.
A surface-scan found the heavy infra is already built — real `foamToVTK` surface
+ `streamLine` exports (backend) are already wired into `ViewportV4.attachVtp`
(vtk.js XMLPolyDataReader + tube filter all present). The gap is (1) it's never
been **proven on a real solve**, and (2) V4 Post still renders **hardcoded fake
telemetry** (`POST_BLUEPRINT_VERDICT` "通过 · +4.2% flow", fake mini-charts, a
fixed 65% gauge) while the backend holds real comparison data. M5 is a **focused
verify-and-truthify milestone, NOT a net-new viz build.**

## Surface-scan finding (2026-05-25 · Explore + targeted verification)

| Capability | State | Evidence |
|---|---|---|
| VTP surface overlay | ✅ backend real + V4 wired | `/post/surface.vtp` (case_visualize.py:124) real foamToVTK; `ViewportV4` attaches (ViewportV4.tsx:260-295); `viewport_kernel.attachVtp` + XMLPolyDataReader (viewport_kernel.ts:468-897) |
| VTP streamline overlay | ✅ backend real + V4 wired | `/post/streamlines.vtp` (case_visualize.py:175) real streamLine; attached (ViewportV4.tsx:297-329) w/ tube filter |
| VTP loader | ✅ EXISTS | `attachVtp(url, role, scalarRange)` — no loader to build |
| **VTP overlay proven on real solve** | ❌ **UNVERIFIED** | C4 spot-check hit `PostEmptyViewport` (no GLB in that view); never seen rendering real surface/streamlines e2e |
| **Real verdict / comparison in V4** | 🟠 **FAKE** | `POST_BLUEPRINT_VERDICT.flowGainPct=4.2 / temperatureDeltaPct=0.8` hardcoded (postBlueprint.ts:40-44), rendered as a "PASS" pill (ModeRendererPost.tsx:668-674); backend comparison-report exists (comparison_report.py routes) but V4 ignores it |
| Mini profile charts | 🟠 FAKE | `POST_BLUEPRINT_MINI_CHARTS` fixed 11-pt sample arrays (postBlueprint.ts:46-68) |
| Convergence/coverage gauge | 🟠 FAKE | `POST_BLUEPRINT_RADIAL_GAUGE.valuePct=65` hardcoded, `achieved` always true |
| Field probes (click→U/p) | ❌ MISSING | no point-sample endpoint; no V4 pick-value UI |

## Theme

**Make V4 Post tell the truth.** A workbench whose north star is the truth chain
+ canonical artifacts (four-question gate V130) must not ship a hardcoded "通过 ·
+4.2%" verdict. M5 proves the real overlays render and replaces fake telemetry
with real run-derived data or honest empty states.

## In scope

- **C1 (this DEC)**: charter + surface-scan.
- **C2 · VTP overlays proven + hardened**: verify real surface + streamline
  overlays render in V4 Post on a real solved case (live, like M4 C4); wire the
  velocity legend from the **real** VTP scalar range (not the [0,1] fallback);
  add vitest for the attach path; graceful degrade when a VTP is absent (no run)
  — never a crash.
- **C3 · de-fake the verdict pill**: replace the hardcoded `POST_BLUEPRINT_VERDICT`
  with the **real** backend comparison verdict + deltas (comparison-report
  context route), or an honest "no baseline" state when none exists. This is the
  highest-priority honesty fix (a fake PASS verdict is the worst offender).
- **C4 · honest-ify or back the remaining placeholders**: the mini profile
  charts + coverage gauge either become run-derived or honest empty/“blueprint”-
  labelled states (no silent fake data). + close retro with a live spot-check.

## Out of scope

- **Field probes (interactive click→U/p sampling)** — net-new backend
  (`postProcess`/`sample` endpoint) + V4 pick UI. Real value, but a separate
  build; candidate for M6 or an M5 stretch only if C2-C4 land cleanly.
- GPU/CPU/temp solver telemetry — still deferred (per DEC-V61-204 out-of-scope).
- New solver / export **engines** — foamToVTK + streamLine + comparison all
  exist; M5 is verify + surface, not new compute.
- Reviving V3 post views.

## Expected cycles

3-4 (C2 overlays · C3 verdict de-fake · C4 placeholders + retro; C3/C4 may
merge if the comparison context is thin for non-LDC cases).

## Close criterion (passes:true iff ALL hold)

1. On a real solved case (the C4 imported case or a fresh LDC), V4 Post renders
   the real foamToVTK surface overlay **and** streamline overlay in the viewport
   (visual spot-check screenshot), with the velocity legend driven by the real
   VTP scalar range.
2. `grep POST_BLUEPRINT_VERDICT` shows it is no longer rendered as a truth claim
   — the verdict pill reflects real comparison data or an explicit no-baseline
   state. Same for the gauge + mini-charts (real-backed or honest-labelled).
3. No regression: V4 vitest green; no crash when a case has no run (overlays +
   panels degrade to honest empty states).
4. Verified by an extended dogfood (overlay URLs 200 + scalar range present on a
   solved case) + a real-backend visual spot-check in the close retro.

## Four-question gate (V130)

- **LLM offline / runs?** ✅ all post-proc is foamToVTK / streamLine / parsed
  logs — no LLM.
- **Artifacts canonical?** ✅ VTP files + comparison context are file-backed run
  artifacts; the whole point of M5 is to *stop* showing non-artifact fake data.
- **TrustGate explainable?** ✅ overlays carry the run's scalar range; the verdict
  becomes a real provenance-backed comparison, not a hardcoded claim.
- **AI advisory-only?** ✅ read-only display of solve outputs; no AI action.

## Decided defaults

1. **Verdict source** → the backend `comparison-report/context` JSON (real
   gold-vs-measured for LDC; honest "visual-only, no baseline" for BFS/channel/
   etc.). No new comparison compute.
2. **Fake placeholders** → prefer real run-derived data; where a run doesn't
   carry it, show an explicit honest empty/"reference" label rather than fake
   numbers. Removing a fake panel is acceptable if no real source exists.
3. **Live proof** → reuse the M4 cfd-openfoam path (OpenFOAM 10 amd64 emulated)
   + a solved imported case for the C2/C4 spot-checks.

## Gating

C2 starts with this charter Accepted (now true) + parent DEC-V61-204 complete
(true). Implementation cycles are sub-DECs / spike-class under this charter.

## Rollback

Charter-only DEC; no code. Unwind = mark Status=Rejected/Superseded.

## Kogami

Not summoned (opt-in per v2.3). M5 is lower strategic risk than M4 (verify +
truthify already-built infra, no new arc); the honesty framing is a continuation
of the established truth-chain / advisor-not-driver SSOT, not a new direction. If
the verdict-source design (C3) turns out strategically ambiguous, invoke then.
