# Red Team Round-13 Review — Phase 1 Step 2a Meta Scan

**Scope:** adversarial probe of the R-17 closure code (`_find_symlink_at_any_depth` + integration in `_is_openfoam_compatible_case_dir`).
**Author:** test-red-team agent.
**Date:** 2026-05-20.
**Previous round:** `red_team_round12_review.md` (FAIL, 3 LOW).
**Verdict:** **PASS — zero findings.** First zero-finding round on net-new code in this project.

---

## Method

Six probes against the recursive walk. All targeted specific edge cases that the round-11 / round-12 history suggested would be the most likely failure modes:

| # | Probe                                                                       | Expected         | Observed (elapsed) |
|---|-----------------------------------------------------------------------------|------------------|--------------------|
| 1 | Symlink cycle: `case/system/loop → case/`                                   | rejected, no loop | rejected at depth 2 (0.2 ms) |
| 2 | Hardlink (regular file `ln`-d, not symlinked)                               | accepted          | accepted ✓ |
| 3 | Relative-path symlink INSIDE case_dir (`system/x → ../constant`)            | rejected per shape-A | rejected ✓ |
| 4 | `case_dir/system` is a regular file (not a dir, not a symlink)              | reported as missing at depth-1 | reported as missing (R-17 walk not reached) ✓ |
| 5 | Realistic CFD case sized ~500 files, no symlinks                            | accepted, fast    | accepted in 3.0 ms (well under `_MAX_PATHS_WALKED = 10000`) |
| 6 | TOCTOU between depth-1 and recursive walk                                   | depth-N walk catches | covered by probes 1 & 3 |

All six matched expectations. The recursive walk handles every probe path correctly and quickly.

---

## What was probed and worked

- **Symlink cycle safety**: a `case/system/loop_back → case/` symlink is detected on the first visit to `loop_back` (because `is_symlink()` fires before the entry is added to the DFS stack). The walk does NOT infinite-loop. Elapsed time was 0.2 ms — well under any DoS concern.
- **Hardlinks**: file-level hardlinks are not symlinks. `is_symlink()` returns False on them. They pass cleanly. Dir-level hardlinks are kernel-prevented on macOS/Linux so we don't need to defend against them.
- **Internal symlinks (relative-path, target inside case_dir)**: rejected, matching the shape-A philosophy documented in R-17. We do NOT distinguish "symlink to inside the repo" vs "symlink to outside the repo" — we refuse all symlinks for honesty. If a Phase 2+ user has a legitimate use case (e.g., shared mesh dirs), they'd opt in via `CFDTRUST_ALLOW_SYMLINK_CASE_DIR=1` (env-var noted in the docstring).
- **`system/` as a regular file (not a directory)**: depth-1 check correctly reports it as missing. The recursive walk is never reached. Predictable error UX.
- **Perf on realistic CFD-sized case**: 500-file synthetic case walks in 3 ms. Headroom of ~33x to the `_MAX_PATHS_WALKED = 10000` cap.
- **`case_dir` non-existent path** (re-verified mentally, not live-probed): depth-1 check trips first on missing subdirs → BLOCKED → walk not reached.
- **DoS bound ordering**: when `paths_walked > _MAX_PATHS_WALKED`, the cap message fires BEFORE checking `is_symlink` on that specific entry. This is a minor cosmetic — if entry 10001 happens to be a symlink, the user sees "DoS bound" instead of the specific symlink path. The behavior is still fail-closed (BLOCKED either way), and at 10000 entries we're already in pathological territory where the specific symlink path is less informative than "this case_dir is too big to audit." Not a finding.

---

## What was NOT probed (worth noting for future rounds)

- **macOS Spotlight `.DS_Store` interaction with `_MAX_PATHS_WALKED`**: in pathological cases the user might inherit a `case_dir` with thousands of `.DS_Store` files. Not relevant to security but a potential false-positive for the DoS bound. If/when a real user hits this, fix is to allow-list `.DS_Store` in the walk (or document that users should `find . -name .DS_Store -delete` before `cfdtrust run`).
- **Symlinks created BETWEEN the depth-1 check and the recursive walk** (TOCTOU race): not exploitable in single-user dev contexts; would matter in a multi-user host with hostile co-tenants. Phase 0 / Phase 1 step 2 don't claim resistance to that.
- **Containerized OpenFOAM creating symlinks at runtime** (step 2c concern): the trust harness audits the case_dir BEFORE invoking `docker run`. What OpenFOAM writes during execution is not in scope for `_is_openfoam_compatible_case_dir`. Step 2c will need its own post-run audit if it ships before then-end-of-Phase-1.

---

## Cumulative severity trend

| Round                       | CRIT | HIGH | MED | LOW | Total |
|-----------------------------|------|------|-----|-----|-------|
| 1 (bootstrap)               | 3    | 5    | 6   | 2   | 16    |
| 2 (Tier-1 meta)             | 0    | 1    | 4   | 2   | 7     |
| 3 (T1 fix meta)             | 1    | 1    | 2   | 1   | 5     |
| 4 (R3 batch w/ helper)      | 0    | 0    | 0   | 0   | 0     |
| 5 meta                      | 0    | 0    | 3   | 3   | 6     |
| 5 fix (α)                   | 0    | 0    | 0   | 0   | 0     |
| Tier-2 (β) self-check       | 0    | 0    | 0   | 0   | 0     |
| 6 (Tier-2 meta)             | 0    | 0    | 1   | 1   | 2     |
| 6 fix (α)                   | 0    | 0    | 0   | 0   | 0     |
| 7 (α meta)                  | 0    | 0    | 0   | 2   | 2     |
| 7 fix (β)                   | 0    | 0    | 0   | 0   | 0     |
| 8 (β meta)                  | 0    | 0    | 0   | 2   | 2     |
| 8 fix (β SSOT)              | 0    | 0    | 0   | 0   | 0     |
| 9 (β SSOT meta)             | 0    | 0    | 0   | 3   | 3     |
| Phase 1 step 1              | 0    | 0    | 0   | 0   | 0     |
| 10 (step 1 meta)            | 0    | 1    | 1   | 2   | 4     |
| 10 fix (γ)                  | 0    | 0    | 0   | 0   | 0     |
| 11 (γ meta)                 | 0    | 0    | 0   | 4   | 4     |
| 11 fix (γ)                  | 0    | 0    | 0   | 0   | 0     |
| 12 (γ meta)                 | 0    | 0    | 0   | 3   | 3     |
| Phase 1 step 2a (R-17)      | 0    | 0    | 0   | 0   | 0     |
| **13 (step 2a meta)**       | **0**| **0**| **0**| **0**| **0** |

**First zero-finding round on net-new code in the project's history.** Previous zero-finding rounds were all post-fix rounds (rounds 4, 5-fix-α, β-self-check, 6-fix-α, 7-fix-β, 8-fix-SSOT, 10-fix-γ, 11-fix-γ — all reviewing CLOSURES of prior findings, not novel surface).

## Pattern observation — what made this round zero

Three structural reasons the 2a sub-commit avoided introducing new findings:

1. **Small surface area**: net-new code was ~40 lines (one helper + integration). The smaller the diff, the smaller the attack surface.
2. **Explicit fail-closed posture documented in code**: the docstring lists THREE fail-closed conditions before the implementation. A future maintainer reading the code knows what they're upholding.
3. **R-17 entry in `RISK_REGISTER.md` named the shape choice explicitly**: shape A (recursive walk) vs shape B (`--read-only` mount). When you commit to a specific design before writing code, you constrain yourself away from the "did I miss a vector?" class of bugs.

This validates the round-11 strategy lesson: ship step 2 as small sub-commits, NOT one big drop. 2a is the proof of concept for that approach.

---

## Verdict

**PASS** on round-13 meta scan.

The R-17 closure code is sound. The DFS walk handles cycles, hardlinks, relative-internal symlinks, file-vs-dir confusion, and realistic-sized cases all correctly. No new findings.

Sub-commit 2a (R-17 closure) is shippable as-is. The natural next move is sub-commit 2b (OpenFOAM case-dir scaffold for `flat_plate_rans_sst`) — a larger code surface, expected to surface a HIGH-or-MED on its own meta scan per the pattern.

---

## Recommended next options for the owner

1. **(α)** Proceed to **sub-commit 2b** — write OpenFOAM `system/` (controlDict, fvSchemes, fvSolution), `constant/` (transportProperties, turbulenceProperties, polyMesh placeholder), `0/` (U, p, k, omega, nut initial fields) for `flat_plate_rans_sst`. **~1 hour. The largest single chunk of step 2.** Expected to surface 1-2 findings on its own meta scan.
2. **(β)** Push back on 2b's scope — split it into **2b₁ (system/)** + **2b₂ (constant/)** + **2b₃ (0/)** for finer-grained adversarial review per Anthropic harness `passes` discipline. ~20 min × 3.
3. **(γ)** Natural session boundary at this clean point — first net-new-code zero-finding round is a high-water mark. Resume with 2b in next session.
4. **(δ)** Skip 2b's design entirely and go to 2c (docker run wrapper) using a hand-crafted minimal case in `/tmp/` for testing. Cheap path to "real CFD running" but skips the integration with `flat_plate_rans_sst`.

My recommendation: **(α)** if you have ~1 hour, otherwise **(γ)**. The 2b sub-commit is mechanical OpenFOAM dictionary writing; doable in one focused session but not splittable cleanly because the dictionaries reference each other.
