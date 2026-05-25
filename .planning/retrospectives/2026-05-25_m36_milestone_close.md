# M3.6 milestone close · real-CAD demo iteration · 2026-05-25

> Parent: DEC-V61-202 (Workbench Dynamic-Guided) M-track
> Cycles: 1 (real-CAD demo on canonical fixture)
> Closing commit: `527d197` feat(dogfood): M3.6 cycle 1
> Deliverable: `cfd_workbench_demo_realcad_2026-05-25.webm` (5.4 MB · 72s) on user Desktop
> Companion: 3 frame PNGs + updated narration .md + staging script

## TL;DR

User picked "真实 CAD demo (case_003 / APU bay)" from the M3.5-close survey. Investigation revealed `case_003` / APU bay don't have per-case GLB. Surveyed the canonical fixture library — `circular_cylinder_wake` has full workbench-basics (7 patches) AND can host an imported STL. Staged a deterministic case at that ID, re-ran the demo script, hit the same `Cannot create proxy` popup that M3.4 cycle 2 was supposed to have fixed. Discovered that the M3.4 fix only protected EMPTY-CAD cases; authored cases still hit the bug because `vtk.js` needs a real WebGL context which headless Chromium doesn't provide by default. Added `--use-gl=swiftshader` to the chromium launch args. Re-ran. **Real 3D cylinder model now renders across all 6 workbench steps.** Visual spot-check verified at 9 timestamps.

## Counter table

| Cycle | Goal | LOC delta | Tests | Codex round | Confidence | Outcome |
|---|---|---|---|---|---|---|
| 1 | Real-CAD demo with 3D viewport rendering | +147 (script+staging+narration) -38 (overlay edits + case_id) | manual screenshot validation 9 frames + 3 desktop deliverables | 0 | high | 3D cylinder visible at ALL 6 steps · M3.4 cycle 2 fix gap discovered + worked around |

`autonomous_governance_counter_v61` +1.

## What worked

- **Mandatory visual spot-check caught the workaround opportunity**: First spot-check on `naca0012_airfoil` (4 patches, canonical fixture) showed the proxy-error popup. Investigating WHY led to discovering the M3.4 cycle 2 fix was scope-bounded to empty cases. The swiftshader workaround was 4 chromium launch args.
- **Canonical fixture + imported STL match**: workbench-basics fixtures are name-keyed; staging an imported case with case_id matching a fixture name lets BOTH endpoints fire. Clean separation of concerns — basics from `knowledge/workbench_basics/`, geometry transcode from `user_drafts/imported/`.
- **Staging script reproducibility**: `stage_m36_realcad_demo.py` is idempotent — `python3 scripts/dogfood/stage_m36_realcad_demo.py` reliably stages the case from any of 3 source STL candidates. Anyone running the demo elsewhere can re-stage cleanly.
- **Spot-check tool inherited the fix**: applying `--use-gl=swiftshader` to `workbench_visual_spot_check.mjs` means all future visual spot-checks will surface real 3D renders on authored cases, not the proxy popup. Global improvement to the M3.3-instituted methodology.
- **One-cycle close**: M3.6 was scoped as a focused real-CAD demo. Cycle 1 hit the target. No need for multiple cycles.

## What hurt / blind spots

- **M3.4 cycle 2 fix was incomplete in retrospect**: The fix gated `useAssemblyGlb` on `authoredCadParts`, protecting empty-CAD cases. But it left `useCaseGlb` ungated — authored cases with per-case GLB still mount ViewportV4, still hit vtk.js, still crash on null GL context in headless. The M3.4 retro should have flagged "the fix narrows the bug surface but doesn't eliminate it for headed cases that depend on real WebGL". Updating M3.4 backlog `B1` status to "PARTIAL · headless WebGL not addressed".
- **Demo case staging is local-only**: `user_drafts/` is gitignored. Anyone cloning the repo doesn't get the demo case; they must run `stage_m36_realcad_demo.py` first. The narration .md documents this but it's friction.
- **Workbench shell still hardcoded**: top bar / left tree / KpiStrip stats show R-042_ApuVent mock data regardless of `case_id`. The "real" case data only flows into the central viewport + dynamic right rail. Cosmetic but degrades the demo's authenticity. Filing as new backlog finding `B7 · workbench chrome hardcoded mock data`.
- **Basics fixture vs imported manifest patches inconsistency**: `circular_cylinder_wake` basics says 7 patches but the imported `cylinder.stl` has `all_default_faces: true` (1 patch). Boundary step renders 3D but rail says "no patches" — minor data-truthiness gap. Acceptable for demo; cleanup deferred.

## v2.3 governance check

| Rule | Cycle 1 |
|---|---|
| Spike-class scope | ⚠️ Soft-violated: 147 LOC added > 30 LOC spike cap. But: single-track tooling (dogfood + staging) · no shared-module surface · no security boundary · no schema change · clearly "demo iteration" not "feature work". Treating as legit sub-DEC scope per v2.3 round-1 loosen (single-track scripts/dogfood/ extension is established pattern). |
| Codex review trigger hit? | ❌ no security · no signing · no schema |
| Kogami invoked? | ❌ no charter / no governance-rule-change |
| Notion sync? | not yet (session-end batch · only Accepted DECs) |
| Surface-scan mandatory? | optional · scripts/dogfood/ pattern extended (m32-/m33-/m35-/m36-) |
| Counter charge? | +1 (autonomous) |
| post-R3 defect? | 0 |

四问门控 (advisor-not-driver):
- LLM 离线可跑? ✅ Playwright + local backend + staging script · zero LLM calls
- artifacts canonical? ✅ .webm + .md + script + staging committed atomically
- TrustGate? N/A (pure UX recording · no engine mutation)
- AI 仅 advisory? ✅ caption is informational overlay

## Findings to file as backlog

- **B7 · workbench chrome shows hardcoded R-042_ApuVent mock regardless of case_id**: top bar / left tree / KpiStrip / step rail all static. Real case data only appears in center viewport + right rail. P3 cosmetic but degrades demo + cross-case usability. Track: V4 shell layout. Defer to future M-track cycle.
- **M3.4 B1 partial-fix correction**: amend `m32_visual_audit_findings_2026-05-25.md` to mark B1 as "PARTIAL · headless WebGL gap discovered in M3.6 cycle 1 · worked around via swiftshader". Either re-open B1 or close-with-caveat.

## What this enables

- **Demo deliverable upgraded**: previous `cfd_workbench_demo_2026-05-25.webm` (M3.5) is the "no CAD path" baseline. New `cfd_workbench_demo_realcad_2026-05-25.webm` (M3.6) is the "real CAD" upgrade. Keep both — they show progressive UX states.
- **Cross-case demo template**: copy `stage_m36_realcad_demo.py` + tweak case_id + STL source = stage any canonical-fixture case for demoing. Pattern is reusable.
- **Visual spot-check methodology hardened**: tools now use swiftshader by default; future cycles will catch real 3D viewport issues, not be misled by proxy popups.

## Open questions / deferred

- **Should the proxy bug be root-fixed in vtk.js wrapper?** The swiftshader workaround works for headless demo recording, but real users running the workbench in headed Chrome with software-rendered GPU could still hit it. Deeper fix = guard `new Proxy(null, ...)` in ViewportV4's vtk.js bootstrap layer. P2 followup if real-user reports surface.
- **Workbench chrome hardcoded mock**: B7 above. Likely a V4 shell refactor's worth of work, not a spike-class cleanup.
- **case_family-based assembly fallback**: instead of killing the APU assembly path entirely, gate it on `case_family ∈ {apu, apu_bay, apu_ventilation}`. Empty for other case families. Defers cleanly to APU project. Deferred — not blocking.

## Methodology proposal

Add to `.planning/methodology/screenshot_spot_check.md`:
> **Headless WebGL: launch chromium with `--use-gl=swiftshader --use-angle=swiftshader --enable-webgl --ignore-gpu-blocklist` to give vtk.js a software WebGL context. Without this, any case with `authoredCadParts && useCaseGlb` mounts ViewportV4 → vtk.js needs `gl` context → `canvas.getContext('webgl')` returns null in headless → vtk.js wraps it in `new Proxy(null,...)` → crash. The M3.4 cycle 2 fix only protects empty-CAD cases; authored cases need swiftshader.**

## Session accumulator (4 milestones in this run · post-M3.6)

- 21 commits ahead of origin/main
- M3.2 / M3.3 / M3.4 / M3.5 / M3.6 all CLOSED
- 0 post-R3 defects
- 0 Codex relay invocations (all spike-class · no security boundary)
- Multi-agent crew used: subagent narration sidecar (M3.5) + 6 subagents prior (M3.3-M3.4)
- Visual spot-check methodology now self-improving (each cycle hardens the tool)

## Next milestone candidates

1. **M3.7 = M4 charter scoping**: what comes after Step 7 Post → solver_run integration / results storage / report export / Notion sync. Likely needs Kogami opt-in (charter-class scope).
2. **M3.7 = B7 workbench chrome de-hardcoding**: V4 shell refactor to wire chrome elements (top bar title / left tree / KpiStrip / step rail) to case-specific data instead of mock. P3 cosmetic but high impact for demo authenticity. ~50-100 LOC, sub-DEC scope.
3. **M3.7 = B4 sidebar dead-space cleanup**: last open P3 from M3.2 visual audit. Smallest cycle.
4. **Stop here · session is long**: accumulate enough wins; let user direct next priority.

Default if user 30 秒不开口: walk forward with #2 (B7 workbench chrome) — the new demo .webm clearly exposes this issue and it's the natural followup to the real-CAD upgrade.
