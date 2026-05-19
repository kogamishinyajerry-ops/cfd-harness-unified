# ARC-GOAL · V91 · V9 Substantiation Arc · 27th V110 advisor-class · 5th "CFD能力" verbatim re-issue · **14-arc no-scoring-change streak target** · **Active 2026-05-18**

> **Charter**: `.planning/decisions/2026-05-18_v91_charter_dec.md` (Accepted B311)
> **Predecessor**: DEC-V90-close (13-arc streak ATTAINED · 6 strategic-pivot blueprints V4-V9 LANDED)
> **Target**: 16-pillar min ≥99 · 2-consecutive close gate under V78 scoring (unchanged)
> **Pattern**: V86/V88/V90 (verbatim AFTER LAND-then-substantiate = next-LAND) inverse — V91 = verbatim AFTER LAND = substantiate
> **Cohort**: V90 (V9 LAND) → **V91 (V9 substantiate)**

## North Star

V90 landed V9 as a pure-presentational frontend surface. V91 makes V9
cross-cut the **audit trail** so that audit_package.zip downloads carry
the same human-curated commentary that the live UI shows — byte-pinned by
HMAC, byte-reproducible across re-emission. CFD researchers reviewing
historical bundles see exactly what the advisor said at run time.

Secondary: JSON SSOT for the rule corpus (commentary + provenance) — TS
and Python bindings both load from the same canonical JSON, eliminating
cross-language drift risk.

Tertiary: extend V130 BY-CONSTRUCTION discipline to the backend matcher
(no network · no subprocess · no filesystem · only manifest-dict input).

## Done dim checklist

- [x] **V90-DONE-COMPOSITE carry** — V9 LAND closed · 13-arc streak ATTAINED · 6 strategic-pivot blueprints LANDED
- [ ] **V91-DONE-COMPOSITE** — Rule corpus JSON SSOT landed (V91.1) · Python matcher port + 26 contract tests + cross-lang parity (V91.2) · sidecar emission + byte-repro test (V91.3) · 14-arc streak target via 2-consec ≥99 close gate (V91.4)

## Sub-DEC progress

- [x] **V91.1 · Rule corpus JSON SSOT** — `ui/frontend/src/data/v9_advisor_rules.json` (canonical · 6053 bytes UTF-8) · TS rebind via `buildRules()` joining JSON data with PREDICATES_BY_ID lookup · 5 contract tests pass (RS#37 canonical · RS#32 provenance · uniqueness · shape) · B312
- [x] **V91.2 · Python pattern matcher port** — `ui/backend/services/v9_advisor/pattern_matcher.py` + `rules.py` + `__init__.py` · pure-function matcher · `js_to_exponential` + `js_to_fixed` helpers (JS-numeric-format parity) · 37 contract tests + 8 cross-language parity tests = 45 Python tests pass · 7 TS parity tests pass (cross-language byte-identical on 6 frozen fixtures × 8 rules) · B313
- [x] **V91.3 · Audit-package commentary sidecar** — `manifest_adapter.py` (new) + `src/audit_package/serialize.py` extended (8 LOC additive sidecar dispatch) + `ui/backend/routes/audit_package.py` extended (6 LOC commentary injection) · `commentary/matched.json` byte-reproducibly emitted into bundle.zip · 12 contract tests including 3× byte-repro + SHA-256 cross-check · existing 192 audit_package tests still green (HMAC sig intact) · V132=9 unchanged · B314
- [x] **V91.4 · V78 fleet close + DEC + retro · 14-arc streak ATTAINED** · DEC-V91-close + V91 retro WRITTEN · B315

## Reverse-stops (NEW in V91)

35. V9.D sidecar matcher MUST NOT add network I/O · subprocess · filesystem read beyond manifest-dict argument
36. V9.D MUST be byte-reproducible: `serialize_zip_bytes(manifest)` × 2 → identical bytes including new sidecar
37. JSON SSOT MUST be canonical (sorted keys · UTF-8 · trailing newline)
38. Python matcher output MUST be byte-identical to TS matcher output given identical RunArtifactSlice fixtures (cross-language parity)
39. Manifest adapter MUST gracefully degrade when log_tail parse fails (return empty commentary not crash)

## Fleet criteria (16 pillars · V78 unchanged · V91 SAME)

| # | Agent | V90 close | V91 |
|---|---|---|---|
| 1-16 | (all) | 100 (iter-0=100 · iter-2=100 · iter-3=100 · iter-1=70 flake disposed) | **100/100 target** (V9 substantiation = backend-add; iter-0 may dip if stability scorer hits flake, accept 1-extra-iter if needed) |
| ~~17~~ | ~~(declined)~~ | ~~NOT added~~ | **STILL NOT added (14-arc streak target)** |

## Iteration tracker

| Iter | Date | min(16) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V91 baseline) | 2026-05-18 | **100** | high | (none below 100) | All V91 substrate landed pre-score · 185/185 Playwright + 3/3 vitest · iter-0 over-meet held | `.planning/scores/V91_iter_0.md` |
| 1 (close confirm) | 2026-05-18 | **100** | high | (none below 100) | 185/185 Playwright + 3/3 vitest · **2-CONSEC CLOSE GATE MET (iter-0+iter-1)** | `.planning/scores/V91_iter_1.md` |
| 2 (post-gate flake) | 2026-05-18 | 86 | (n/a) | ux (184/185 PW · spec #50 timeout 5s) | Load-induced flake (post-gate · sequential run after iter-1 left system hot) · NOT regression · isolation rerun = 1/1 PASS in 8.9s | `.planning/scores/V91_iter_2.md` |
| 3 (flake reproduced under load) | 2026-05-18 | 86 | (n/a) | ux (same spec #50 timeout) | Same flake reproduced under continued multi-process scoring load · documented as V78 1-vote-veto-on-load-sensitive-metric · same class as V90 iter-1 stability flake | `.planning/scores/V91_iter_3.md` |
| 4 (post-Codex-fix · stash corruption surfaced) | 2026-05-18 | 65 | (n/a) | smoke (frontend build TS errors · `setCameraPreset` missing) | Discovered during Codex-fix verification: prior `git stash push --keep-index -u` + pop sequence (used for Codex narrow-scope review) silently FAILED to restore ~25 M tracked files (V76-V90 backlog), wiping component mounts in WorkbenchShellV3 + `setCameraPreset` from viewport_kernel.ts. NOT a V91 regression — pre-existing V76-V90 state that the stash dance corrupted in working tree. Triggered full stash-restore protocol. | `.planning/scores/V91_iter_4.md` |
| 5 (partial recovery) | 2026-05-18 | 75 | (n/a) | ux (124/153 PW · 29 fail · 32 missing specs) | Smoke recovered (setCameraPreset manually re-added) BUT V81/V84/V85 e2e specs still failed because WorkbenchShellV3 component-mount restoration was incomplete (`useSolverConfigStateV8` import missing · DemoBannerV4 mount missing · etc.). Confirmed root cause: stash apply silently doesn't restore tracked-M files when conflicting with current working-tree state. | `.planning/scores/V91_iter_5.md` |
| 6 (full recovery · Codex fixes intact) | 2026-05-18 | **100** | high | (none below 100) | All 25 M tracked files restored via bulk `git checkout stash@{0} -- <each>`. V91 untracked files moved aside during apply then re-injected (with Codex-fixed manifest_adapter.py + test_v9_audit_sidecar.py preserved). 786 frontend + 195 backend tests green · tsc clean. **Close gate RE-CONFIRMED post-Codex-fix on recovered state.** | `.planning/scores/V91_iter_6.md` |
| 7 (2-consec post-recovery) | 2026-05-18 | **100** | high | (none below 100) | **iter-6 + iter-7 = post-recovery 2-consec ≥99**. State stable + Codex round-1 fixes (P1#2 solver_success · P1#3 schema · P2#4 regex) live in final V91 state. | `.planning/scores/V91_iter_7.md` |

## V91 outcome

- **Close gate**: ✅ **MET at iter-0 + iter-1** (initial · 100/100 · 2-consec ≥99) AND ✅ **RE-CONFIRMED at iter-6 + iter-7** (post-Codex-fix + post-stash-recovery · 100/100 · 2-consec ≥99)
- **14-arc no-scoring-change streak**: ✅ **ATTAINED**
- **V130 defense layers**: 7 (V83-V91 · added: Python module-import allowlist + JSON SSOT byte-pinning)
- **V132 endpoints**: 9 (unchanged · V91 extended existing audit-package route response)
- **6 strategic-pivot blueprints**: V4-V9 all LANDED + V9 substantiated (UI runtime + audit trail)
- **Post-gate flakes (iter-2/3)**: V78 1-vote-veto class · NOT regression · same class as V90 iter-1 (now 2-arc evidence for V78 scorer evolution Open Q)
- **Stash-corruption incident (iter-4/5)**: `git stash push --keep-index -u` + pop SILENTLY drops M tracked file restoration when subsequent state has conflicts. Recovery via explicit `git checkout stash@{0} -- <files>` for each M file. **V92 Open Q: never use `git stash` for Codex-review-narrow-scoping; use targeted commit-and-revert OR `--paths` flag instead.**
- **Codex round-1 fixes preserved**: P1#2 (solver_success-based crash detection) · P1#3 (real-schema observables list + singleton key_quantities) · P2#4 (`Time = Ns` regex with optional `s?`) all live in V91 final state · 3 new tests confirm

— V91 ARC-GOAL · 2026-05-18 · **CLOSED** · **14-arc streak ATTAINED · V9 axis fully cross-cuts UI + audit-trail**
