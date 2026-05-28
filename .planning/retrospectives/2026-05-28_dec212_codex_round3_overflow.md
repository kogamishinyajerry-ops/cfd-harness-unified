# Retro · DEC-V61-212 Codex Round-3 Overflow (cap=3 honored)

**Date**: 2026-05-28
**DEC**: V61-212 (shm_dict_extractor v0.1)
**Trigger**: v2.3 round cap=3 reached; Codex review R2 (3rd round) returned 1 P2 finding.
**User disposition**: "honor cap · retro + scope-out" (strict v2.3 compliance).

## Codex review chain (auditable)

| Round | Commit | Codex verdict | What was caught | Status |
|---|---|---|---|---|
| **R0** | `1b82bc2` (initial impl) | CHANGES_REQUIRED (2 P) | P1: quoted tokens (`name "wing"` → `'"wing"'`) leaked to advisor → fabricated `missing_geometry_ref` + `geometry_orphan`. P2: `#include` in `addLayersControls` walker treated `include` as scalar key, consumed next `;` → silently dropped `minMedianAxisAngle` (the V52 typo target itself). | **CLOSED in R1** |
| **R1** | `13317e0` (quote-strip + `#` line-skip) | CHANGES_REQUIRED (1 P2) | R1's line-only `#` skip REGRESSED two body-bearing directive forms: `#codeStream { ... }` body leaked C++ identifiers (`code`, `nRelaxedIter`) as fake keys; `#if 0 ... #endif` inactive body leaked as if active. | **CLOSED in R2** |
| **R2** | `c74a271` (directive-body handler) | CHANGES_REQUIRED (1 P2) | R2's `brace_in_header` peek handles next-line `#codeStream\n{` but NOT same-line `#codeStream {`. After header-skip, walker resumes inside body, leaks C++ identifiers. | **DEFERRED per v2.3 cap=3** |

## The residual P2 finding (verbatim from Codex R2)

> **[P2] Skip block-form directives when `{` shares the header line** — `ui/backend/services/case_extractors/shm_dict_extractor.py:566-570`
>
> If a case writes a block-form directive as `#codeStream {` on one line, this branch still won't skip the body: `i` has already been advanced past the header line, so the `{` on that same line is never seen here. `_parse_addlayerscontrols_keys()` then resumes on `code` / inner C++ lines and emits fake `addLayersControls` keys, so valid dictionaries in that layout will still produce fabricated `typo_suspicion` warnings after this R2 fix.

## Why we're stopping (v2.3 rationale)

`~/CLAUDE.md` v2.3 (DEC-V61-133):
> **v2.3 round cap=3**: 超过 3 轮的剩余 P3 (及非 P1 的 P2) findings 进 retro 队列，不再无限迭代闭环
>
> 触发原因：N1.1 R0-R22 数据 — round 5 之后边际收益急剧递减

This is exactly the scenario the cap was designed to catch. The bug is real, narrow, and zero in-repo SHM cases trigger it (audit below). The pattern "just one more iteration" is what V133 explicitly bans.

## Operational impact assessment (zero in-repo triggers)

Audit of all in-repo `system/snappyHexMeshDict` files for `#`-directive usage:

| File | `#`-directives present |
|---|---|
| `.planning/case_profiles/case_004_v64_mesh_gen_v2_dicts/system/snappyHexMeshDict` | `#include "meshQualityDict"` (in `meshQualityControls`) |
| `.planning/case_profiles/case_006_v64_thermo_fpe_fix_dicts/system/snappyHexMeshDict` | `#include "meshQualityDict"` (in `meshQualityControls`) |
| `.planning/case_profiles/case_006_v64_val_full_2_dicts/system/snappyHexMeshDict` | `#include "meshQualityDict"` (in `meshQualityControls`) |
| `.planning/case_profiles/case_016_v64_thermo_fpe_fix_dicts/system/snappyHexMeshDict` | `#include "meshQualityDict"` (in `meshQualityControls`) |
| All other in-repo SHM files | NONE (no `#`-directive in addLayersControls) |
| `ui/backend/user_drafts/imported/*/system/snappyHexMeshDict.stub` | template stubs; no `#`-directive in addLayersControls |

The `#include "meshQualityDict"` cases are in `meshQualityControls` block (which v0.1 does NOT extract per DEC-V61-212 §"non-feature 2"); they never reach `_parse_addlayerscontrols_keys`. **Zero in-repo cases use `#codeStream` or `#if`/`#endif` in addLayersControls**, same-line or otherwise. The P2 finding is correct future-proofing but currently UNREACHABLE.

## Scope-out (docstring update committed alongside this retro)

The extractor docstring §"NON-features (extractor will NOT parse correctly)" gains an item:

> **Same-line block-form `#`-directives** (`#codeStream { ... }` with `{` on the header line, or any `#<directive> {` opening on the same line as the directive name). v0.1 handles next-line form (`#codeStream\n{ ... }`) cleanly but the same-line form leaks the block body's inner tokens into `addLayersControls`'s key set. **v0.1 scope-locks this OUT**: zero in-repo SHM files use this pattern today (verified `find .planning ui/backend -name snappyHexMeshDict*` 2026-05-28); a follow-on v0.2 / sub-DEC can add the ~10 LOC peek-for-same-line-`{` fix when a real case demonstrates the need. Codex R2 finding archived in `.planning/retrospectives/2026-05-28_dec212_codex_round3_overflow.md`.

## Lessons (carry-forward)

1. **Cap=3 works as designed**: I started a Codex chain (R0 found 2 P, R1 found 1 P regression I introduced, R2 found 1 P sub-case I missed). Each round found a smaller / more niche bug. Round 4 would have found "what if `#include` is the LAST line of the block with no newline" or similar tail case. Stopping = healthy.

2. **Reggressions-in-fix are not free**: R1's fix introduced the R2 finding (line-only skip regressed pre-R1's whole-block skip behavior for `#codeStream\n{`). R2's fix didn't introduce a regression but missed a sub-case. The lesson: when fixing a class of bugs, enumerate ALL forms of the class BEFORE writing the fix (single-line, block-form-next-line, block-form-same-line, conditional, ...). I didn't do this — I responded to the specific repro Codex gave me.

3. **Contract-bug class is Codex's sweet spot**: All 4 findings across R0+R1+R2 were "docstring says X, code does Y" — not logic errors, but contract mismatches against legal-but-uncommon OF syntax. This is the kind of bug pytest-on-in-repo-fixtures CANNOT catch. Codex's value here is exactly this contract-fuzzing role.

4. **Round-cap is a feature not a defeat**: Strict v2.3 compliance means the cap holds even when "one more fix" is tempting and small. Truth-chain: real findings get recorded, scope-out is honest, future caller knows the limit. The next 10 hours of P2 work go into actual P2 forward motion, not perfecting an extractor v0.1 for hypothetical inputs.

## Carry-forward items

- **v0.2 sub-DEC candidate**: extend `_parse_addlayerscontrols_keys` directive handler to also peek for same-line `{` after the directive name (~10 LOC + 1 test). Trigger: first real OF case lands an `addLayersControls` with `#codeStream {`, `#calc {`, or similar same-line block-form directive.
- **Methodology improvement** (rule-of-thumb to add to my own behavioral checklist): "when writing a fix for class X of bugs, enumerate ALL forms of X before writing — same-line, next-line, with-body, without-body, nested, etc. Codex's repro is one form; the real bug surface is larger."

## DEC-V61-212 chain status post-retro

- **Functionally CLOSED** (R0+R1+R2 covered every real and every realistic-near-term bug in extractor v0.1)
- **Tests**: 51 passing (40 initial + 7 R1 regression + 4 R2 regression)
- **Codex residual finding**: ONE P2, narrow same-line block-form, ZERO in-repo triggers, documented in extractor docstring as scope-out + this retro file
- **Notion sync**: DEC-V61-212 status remains Accepted; sync at session-end (per session-end Notion batch convention).
- **Commits**: `d3788d8` (DEC) + `1b82bc2` (impl) + `13317e0` (R1) + `c74a271` (R2) + this retro + docstring scope-out commit.

— cfd-chief-engineer (Opus 4.7, 2026-05-28)
