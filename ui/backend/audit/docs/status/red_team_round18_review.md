# Red Team Round-18 Review — M3 Meta Scan (Newbie-Ready CLI)

**Scope:** M3 milestone landed three new CLI subcommands — `cfdtrust init`, `cfdtrust verify-reference`, `cfdtrust doctor` — across ~700 LOC in three new modules (`cli_init.py`, `cli_verify.py`, `cli_doctor.py`) plus wiring in `cli.py`. New surface: user-supplied case-id and template-id strings, two file-system write paths (init clones, verify-fix rewrites manifest), one read-only static-audit path (doctor).
**Author:** test-red-team agent.
**Date:** 2026-05-21.
**Previous round:** `red_team_round17_review.md` (M2: 1 HIGH-class + 1 MED surfaced live; 2 LOW added in round-17 retrospective; all closed).
**Verdict:** **FAIL — 0/0/1/4 at probe time, 1 MED + 1 LOW CLOSED in same batch, 3 LOW DOCUMENTED-NOT-FIXED**. M3 added user-supplied-string surface (case-id, template-id) but no new trust gate, so the predicted ceiling of 1 MED held cleanly.

---

## Method

10 probes against the new CLI surface. Findings come in two flavors:
1. **User-string surface** (case-id, template-id) — classic path-traversal class. Predicted by the round-17 pattern update ("new trust boundary ≈ 1-2 MED"). M3 added ONE new trust boundary (user-supplied case naming) → exactly 1 MED came out, matching prediction.
2. **Internal-API consistency** (e.g. doctor's regex matching IC blocks) — informational; no honesty-rule violations.

| # | Probe                                                                  | Outcome    |
|---|------------------------------------------------------------------------|------------|
| 1 | `new_case_id` validated against alphanumeric pattern                    | clean (M3.1 already had `_CASE_ID_RE`) |
| 2 | **`template_case_id` validated against the same pattern**                | **R18-F-01 (MED)** |
| 3 | Template dir contains symlinks → shutil.copytree follows them?          | **R18-F-02 (LOW)** |
| 4 | `verify-reference --fix` regex-rewrite of manifest could mangle YAML    | clean (strict hex pattern, comment preserved) |
| 5 | `verify-reference --fix` non-atomic write (interrupt → corrupt manifest) | R18-F-03 (LOW info, deferred) |
| 6 | `doctor` IC patch coverage regex requires multi-line `{` block format   | R18-F-04 (LOW info, deferred) |
| 7 | `doctor` FO-output blacklist (`yPlus`, `phi`, ...) not exhaustive        | R18-F-05 (LOW info, deferred) |
| 8 | `doctor` blockMesh comment containing the word `boundary` causing false negative | clean — caught DURING M3.3 dev, fixed inline via `_strip_of_comments()` |
| 9 | `init` cleanup on partial failure leaves dangling target dir            | clean (each early-return uses `shutil.rmtree(target, ignore_errors=True)`) |
| 10 | `init` refuses to overwrite existing target dir                         | clean (exit code 2; round-trip test fences) |

---

## Findings

### R18-F-01 — MEDIUM — `cmd_init` didn't validate `template_case_id`; path-traversal possible (closed in this batch)

**File:** `src/cfdtrust/cli_init.py:cmd_init`.

Pre-fix code:

```python
if not _CASE_ID_RE.match(new_case_id):
    return 1  # rejects '../etc'
# ... no equivalent check on template_case_id
template_dir = cases_root / template_case_id
if not template_dir.is_dir():
    ...
```

The new-case-id was correctly fenced against path traversal but the **template** id was not. `cmd_init my_case --template ../../etc` would resolve `cases_root / "../../etc"` and (if that path was a real directory) clone its content into the new case dir. This is a **copy-in** of arbitrary host content — not a code-execution exploit, but a clear violation of the trust model's "case dir is self-contained" invariant.

Discovery: probe 2 of the round-18 scan after observing that `new_case_id` had a validator but `template_case_id` shared the same trust character without sharing the same validation.

**Fix (applied in this batch):** apply the same `_CASE_ID_RE` validation to `template_case_id`. Five attack inputs covered by the new test `test_r18_f01_template_id_path_traversal_blocked`: `../../etc`, `../sneaky`, `evil/sub`, `.hidden`, `1_starts_with_digit`. Test also asserts target dir is NOT created on refusal (no partial state).

### R18-F-02 — LOW — `cmd_init` followed symlinks inside the template dir (closed in this batch)

**File:** `src/cfdtrust/cli_init.py:cmd_init`.

Pre-fix `shutil.copytree(entry, target_dir / entry.name)` follows symlinks by default (`symlinks=False` semantics: "copy as content, not as link"). A future maliciously-planted template containing a symlink to e.g. `/etc/passwd` would have that file content copied into the new case dir as a regular file. Same family as the R-17 case-dir-symlink concern, applied at the template layer.

**Fix (applied in this batch):** before any copy, `template_dir.rglob("*")` for symlinks. Any → refuse with diagnostic + no partial state. New regression test `test_r18_f02_symlinked_template_refused`: plants a symlink in the template, asserts refusal AND that no target dir was created.

### R18-F-03 — LOW (informational) — `verify-reference --fix` writes the manifest non-atomically; DOCUMENTED, deferred

**File:** `src/cfdtrust/cli_verify.py:cmd_verify_reference`.

`Path.write_text(new_text)` is a write-then-flush, not write-to-tmp-then-rename. If interrupted mid-write (SIGKILL, power loss, full disk), the manifest could be left truncated or partially-overwritten.

**Why DOCUMENTED, not fixed in this batch:** the threat model says the user owns and trusts their case dir. A SIGKILL'd `verify-reference --fix` is no worse than a SIGKILL'd hand-edit of the manifest — and the user has VCS / backups. The fix (atomic rename via `Path.replace`) is small (~5 LOC) but breaks the pattern of "M3 closes only its own milestone findings." Logging as a future-batch fix; if M4 lands an atomic-write helper for any reason, fold this in.

### R18-F-04 — LOW (informational) — doctor IC patch coverage regex requires multi-line block format; DOCUMENTED

**File:** `src/cfdtrust/cli_doctor.py:_check_initial_conditions_cover_patches`.

The regex `^\s*{patch_name}\s*\{` matches `wall\n{`-style blocks (canonical OpenFOAM style). Inline-brace form `wall { type noSlip; }` on a single line is not matched. A case with inline-brace IC would falsely report "missing boundary blocks for patches: [wall]".

**Why DOCUMENTED, not fixed:** OpenFOAM's canonical convention is multi-line blocks; both flat_plate and BFS use it; the templated `init` cases will all use it. Tests fence the canonical form. Will revisit if a future case ships inline-brace style — a real test failure is more useful than speculative regex broadening.

### R18-F-05 — LOW (informational) — doctor's `fo_outputs` blacklist not exhaustive; DOCUMENTED

**File:** `src/cfdtrust/cli_doctor.py:_check_initial_conditions_cover_patches`.

Currently the IC check skips files whose name matches `{"yPlus", "wallShearStress", "phi", "uniform"}`. OpenFOAM has dozens of other FOs (vorticity, Cp, Co, magUMean, ...) that could write into `0/`. A future case using one of those would have doctor false-positive on it.

**Why DOCUMENTED, not fixed:** the right shape is probably "use OpenFOAM's actual list of FO names" but that list isn't part of any stable contract we control. Better approach: detect FO output by file header conventions (e.g. `nonuniform List<vector>` body without `boundaryField` block). Out of scope for M3; revisit when a case actually hits this.

---

## What was probed and worked

- **Path-traversal posture** held everywhere we expected it to: new-case-id is regex-fenced; template-case-id NOW is too (R18-F-01); symlinks in template refused (R18-F-02); manifest's `reference_csv` field still goes through the R16-F-05 absolute/relative + resolution check.
- **Cleanup on failure**: every failed-init code path now leaves the filesystem in pre-init state (no partial target dir). 8 negative tests fence this.
- **Cross-tool consistency**: doctor + verify-reference + init use the same SHA-256 computation function pattern (`_file_sha256`), same manifest-parse semantics, same exit-code conventions. No drift.
- **Doctor catches the post-M2.3b pattern**: `test_doctor_detects_wall_patch_not_in_required_patches` exercises exactly the configuration mistake M2.3b surfaced live — caught by doctor without ever running the solver.

---

## Cumulative severity trend

| Round                       | CRIT | HIGH-class | MED | LOW | Total |
|-----------------------------|------|------------|-----|-----|-------|
| 13 (2a meta)                | 0    | 0          | 0   | 0   | 0     |
| 14 (2b meta + fix)          | 0    | 0          | 1   | 2   | 3     |
| 15 (2c meta + fix)          | 0    | 0          | 2   | 2   | 4     |
| 16 (2d meta + fix)          | 0    | 0          | 2   | 5   | 7     |
| 17 (M2 meta + in-flight fix) | 0    | 1          | 1   | 2   | 4     |
| **18 (M3 meta + fix)**      | **0**| **0**      | **1**| **4**| **5** |

Trend: HIGH-class events stay concentrated in milestones that introduce new TRUST gates (M2 added solver-gate persistence + cross-case generality); milestones that introduce new USER surface but no new gate (M3) plateau at MED-class ceilings. Confirms the round-17 pattern.

---

## Pattern update — user-string surface adds MED, not HIGH

Reviewing rounds 14-18:

| Round | New surface           | New trust gates? | Findings   |
|-------|------------------------|------------------|------------|
| 14    | OF dictionary content  | yes (case_dir)   | 1 MED + 2 LOW |
| 15    | docker subprocess      | yes (host fork)  | 2 MED + 2 LOW |
| 16    | NASA external data     | yes (reference)  | 2 MED + 5 LOW |
| 17    | second case            | yes (cross-case generality) | **1 HIGH** + 1 MED + 2 LOW |
| **18** | **user-supplied strings (case-id, template-id)** | **NO new gate** | **1 MED + 4 LOW** |

User-string surface is a different shape from gate surface. The MED that comes out of it is always the same class (path-traversal / argv-injection / shell-injection — depending on what the string ends up controlling). HIGH-class events seem to require either a new trust gate OR a new cross-system integration (case-to-case interop, like M2).

Forward implication: M5 (AI advisor) and M4 (mesh_contract real) each introduce new TRUST GATES. Expect HIGH-class possibilities. M3-style "ergonomic CLI helpers" produce predictable MED ceilings.

---

## Verdict

**PASS** on M3.

The M3 milestone delivered three CLI helpers that close real user-pain gaps (newbie can scaffold a case, drift can be auto-bumped, static audit catches common misconfigs without a docker invocation). 192/192 pytest + 1 opt-in network skip. `make bootstrap-check` exit 0.

R18-F-01 (MED) closed in same batch — the path-traversal vector this introduced is fully fenced by `_CASE_ID_RE` applied symmetrically. R18-F-02 (LOW) closed in same batch. 3 LOW info findings documented with explicit decisions about deferral. No HIGH-class issues, no honesty-rule violations.

The doctor command now provides a STATIC audit path that catches M2.3b-class misconfigurations at scaffold time, not at run time. This is the architectural improvement M3 was supposed to deliver: M2's bugs become detectable in advance of incurring a docker run.

---

## Recommended next milestones (re-ranked after M3)

| # | Title | Brief                                                                                  | Predicted budget | Predicted findings |
|---|-------|----------------------------------------------------------------------------------------|------------------|--------------------|
| **M4** | Real Mesh Contract | Parse checkMesh log, enforce manifest y+ target, drop mesh_contract from MOCKED        | 6-8 crew-hour    | 1-2 MED (new trust gate) |
| **M5** | AI Advisor MVP | `cfdtrust advise <case>` reads trust_report, gives natural-language explanation        | 4-6 crew-hour    | 1-2 MED (AI advisor is a NEW trust class — must not fabricate evidence) |
| **M1** | First Validated PASS | Refine flat_plate to y+<5 + low-Re wall functions; first `validation_status: validated` in project history | 4-6 crew-hour | 0-1 LOW (no new code path; just config tuning) |

Recommendation: **M5 next**. M3 made the CLI newbie-ready; M5 makes the OUTPUT newbie-readable (natural-language explanation of trust_report.json). Together they form the "newbie-end-to-end" arc: someone unfamiliar with the project can init + run + understand a case. M4 is the highest V&V value but doesn't materially change "can a new user get started." M1 is the most prestige but doesn't expand harness capability.
