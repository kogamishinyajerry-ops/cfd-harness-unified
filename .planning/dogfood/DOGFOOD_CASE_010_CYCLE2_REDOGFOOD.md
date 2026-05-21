# Dogfood: case_010 · cycle-2 re-dogfood post Gap #29 0.orig + Gap #31 turb-model derivation fixes · 2026-05-22

**Operator:** dogfood-only subagent (no engine modifications)
**Repo:** `/Users/Zhuanz/Desktop/cfd-audit-merge/` (M2.6 milestone cycle 2)
**Case:** `~/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case/`
**Baseline:** `_sandboxes/case_010_drivaer_fastback_les/case/DOGFOOD_CASE_010.md` (cycle-1, 2026-05-22 morning)
**Cycle-1 artifacts preserved at:** `_sandboxes/case_010_drivaer_fastback_les/case/artifacts.cycle1_baseline_backup/`

## What ran

- Command: `cfdtrust ingest <case>` then `cfdtrust audit <case>` then `cfdtrust report <case>`
- HEAD: `8981f63` (Merge: TBD-15 + TBD-20 spike-class)
- Wall clock (ingest): **real 0.14s / user 0.08 / sys 0.02** — BLOCK before any Docker invocation, as expected
- Exit code (ingest): **1** (environmental BLOCK per `_INGEST_ENV_BLOCKED`; correct fence behavior for "case has no time directory")
- Exit code (audit): **0**; exit code (report): **0**
- **Layout on disk:** `0.orig/` only (no `0/`) — same scaffold state documented in case profile

## What changed vs pre-cycle-1

| Aspect | Cycle-1 (2026-05-22 morning) | Cycle-2 (2026-05-22 this run) |
|---|---|---|
| Ingest BLOCK reason | `case_dir_not_openfoam_compatible` (rejected at directory-shape check because `0/` missing) | **`no_time_directory_found`** (advanced PAST directory-shape check; rejected at deeper time-dir check) — Gap #29 0.orig fallback verified at the gate |
| Ingest BLOCK error text | "Case directory does not look like an OpenFOAM case." + "Provide system/, constant/, and 0/ directories alongside case_manifest.yaml." | **"Case has no time directory beyond 0/; nothing to ingest."** + "Run the case externally first..." — **honest, accurate, actionable** for case_010's actual state (scaffold-only, v1 deliberately deferred solver run) |
| `_is_openfoam_compatible_ingest_case_dir` behavior on 0.orig-only | rejected | **accepted** (per `openfoam.py:284-316` Gap #29 patch: if `0/` is missing but `0.orig/` exists, treat as canonical pre-init shape and continue) |
| Gap #31 turb-model derivation (`_turb_fields_from_model` at `openfoam.py:1655-1678`) | function did not exist | **function exists** and handles `wale|smagorinsky|les-algebraic → [nut]`; `keqn|one-eq → [nut, nuSgs, k]`; `laminar|dns → []`; etc. — code path landed |
| End-to-end LES expected_fields verification | n/a | **NOT VERIFIABLE on case_010**: ingest still BLOCKs (correctly) at `no_time_directory_found`, before `_collect_and_persist_bc` runs. To verify `expected_fields == [U, p, nut]` for LES end-to-end would require a case with `0/` AND completed solver run AND `physics.turbulence_model: wale-les`. Code path inspected and looks correct; runtime witness deferred to v2/v3 case_010 OR to a different LES case with completed run. |

## Honesty fence status

- `solver_execution`: **skipped** (still correctly NOT `ingested` — engine refused to claim ingest happened on a case with no time dir)
- `overall_status`: **BLOCKED** (3 structural gates BLOCKED + solver BLOCKED → overall BLOCKED; same shape as cycle-1)
- `validation_status`: **not_validated** (fence intact)
- `bc_parsing_status`: **unknown / not_emitted** (bc_quality.json never written because `ingest` BLOCKed before reaching `_collect_and_persist_bc`; `bc_audit.json` is the `audit`-subcommand BLOCKED placeholder only — `bc_quality.json_missing`)
- `real_solver_invoked`: **false** (explicit in solver_execution.details — no ambiguity)
- All limitations + `MOCKED` qoi/reference markers preserved — no fabrication

## Net-new gaps surfaced

### Gap #34 (NEW · structural · charter-aligned) · Gap #31 turb-model derivation lands at code level but cannot be witnessed end-to-end on case_010 because it lives downstream of the `no_time_directory_found` BLOCK

**Symptom:** `_turb_fields_from_model` (LES → `[nut]`) exists in `openfoam.py:1655-1678` and is called from `_collect_and_persist_bc` (`openfoam.py:1759`). But `_collect_and_persist_bc` only runs as part of the ingest happy path AFTER the time-directory check at `openfoam.py:2717-2728`. case_010 v1 has no time directory (scaffold-only), so ingest correctly BLOCKs before bc_quality.json is written, and the LES derivation never fires. There is no `bc_quality.json` to inspect; `expected_fields == [U, p, nut]` for LES cannot be verified on this case.

This is **not** a bug in the Gap #31 fix — it's a coverage gap in cycle-2 verification. The LES derivation is correct by code-inspection but lacks a runtime witness in the cycle-2 dogfood set.

**Suggested fix scope:** EITHER (a) author / pull in a small LES test case that has a `0/` and a completed solver log (e.g. an OpenFOAM tutorial `pitzDaily` with WALE swapped in, ~1-min runtime) to drive end-to-end verification; OR (b) wire an `--inspection-only` mode (the cycle-1 baseline Gap #26 recommendation) that bypasses the time-directory check so structural parsers (incl. bc_quality + the LES derivation) can run on scaffold-only cases like case_010 v1. Option (b) is DEC-scale; option (a) is hours of work.

### Gap #26 (RECONFIRMED · structural · pre-existing) · Ingest BLOCK does not fall back to "do what audit can do given what's on disk"

**Symptom:** Same as cycle-1 baseline §"Gap #26". `0.orig/U`, `0.orig/p`, `0.orig/nut` exist with real BC data; `constant/polyMesh/boundary` has 4.644M cells / 6 patches. None of this is parsed because ingest BLOCKs at the time-dir check before any structural parser runs. `cfdtrust audit` (separate subcommand) produces BLOCKED placeholders (`*_quality.json_missing`) rather than actually walking the on-disk evidence.

**Reproducibility:** every case at scaffold / pre-solver-init state. case_010 v1 is the canonical example.

**Suggested fix scope:** see cycle-1 baseline Gap #26 — DEC-scale `--inspection-only` flag or new `cfdtrust inspect` subcommand. Same scope; cycle-2 confirms problem still exists post-Gap-#29.

### Gap #28 (RECONFIRMED · structural · UNCHANGED) · Zero engine awareness of LES SGS models / delta filters / `simulationType LES`

**Symptom:** Re-grep confirms zero matches for `WALE|dynamicKEqn|Smagorinsky|cubeRootVol|simulationType LES` in `ui/backend/audit/cfdtrust/`. **Wait** — cycle-2 DID add `wale|smagorinsky|les-algebraic|keqn|one-eq` recognition in `_turb_fields_from_model` (`openfoam.py:1669-1672`). This is a **partial closure** of Gap #28 narrowly scoped to expected-field derivation. The broader Gap #28 (read `constant/turbulenceProperties`, validate `simulationType LES`, validate `delta cubeRootVol`, validate `LESModel WALE` against a `turbulence_contract` schema) is still open.

**Suggested fix scope:** charter-scale `turbulence_contract` schema redesign per cycle-1 baseline §"Recommended follow-up sub-DECs" item 3. Cycle-2 closed the narrowest slice (expected-field branching) but did NOT land the full charter.

## Artifacts pointer

- Captures dir: `/Users/Zhuanz/Desktop/cfd-audit-merge/.demo/captures/2026-05-22T1530Z/stage_cycle2_case_010_redogfood.txt`
- `bc_quality.json`: **NOT WRITTEN** (ingest BLOCKed before `_collect_and_persist_bc`) — this is fence-correct behavior
- `trust_report.json`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case/artifacts/trust_report.json` (3630 bytes · `overall_status: BLOCKED`)
- `bc_audit.json`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case/artifacts/bc_audit.json` (181 bytes · `audit`-subcommand BLOCKED placeholder)
- `geometry_report.json`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case/artifacts/geometry_report.json` (187 bytes · BLOCKED placeholder)
- `mesh_report.json`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case/artifacts/mesh_report.json` (183 bytes · BLOCKED placeholder)
- `residuals.csv`: **NOT WRITTEN** (no solver ingest)
- Cycle-1 baseline backup: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_010_drivaer_fastback_les/case/artifacts.cycle1_baseline_backup/`

## Verdict

**Cycle-1 fix verified ✓ (partial · code path only)** — Gap #29 (0.orig fallback) landed cleanly: ingest no longer rejects with `case_dir_not_openfoam_compatible`; it now advances to the time-dir check and honestly reports `no_time_directory_found`. The fail-safe direction is preserved (no fabrication, correct fence behavior, `solver_execution: skipped` not `ingested`). Gap #31 turb-model derivation is in code (`_turb_fields_from_model` with WALE/Smagorinsky/kEqn branches) but **cannot be witnessed end-to-end on case_010** because it lives downstream of the time-dir BLOCK — flagged as Gap #34 (verification coverage gap, not engine bug). No regressions. Net-new gaps: 1 NEW (#34 verification coverage); 2 RECONFIRMED (#26 still-open inspection-only mode; #28 broader charter still open beyond the narrow expected-field slice).
