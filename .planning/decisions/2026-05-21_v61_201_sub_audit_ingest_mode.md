---
decision_id: DEC-V61-201-SUB-INGEST
title: cfdtrust ingest mode — load externally-run cases into the audit engine
status: Accepted
parent_dec: DEC-V61-201
phase: post-merge sub-DEC
notion_sync_status: synced 2026-05-22 (https://www.notion.so/367c68942bed812894dadee49f80a6e4)
codex_review_rounds: 7
codex_review_round1_verdict: CHANGES_REQUIRED (P1 log selection + P2 CLI exit + P3 explain WARN)
codex_review_round2_verdict: CHANGES_REQUIRED (P1 DoS bound + 2× P2 state-machine bugs)
codex_review_round3_verdict: CHANGES_REQUIRED (P1 decomposed parallel time-dir detection)
codex_review_round3_relay: crs (effort=high, fallback after 86gs 502 Upstream access forbidden)
codex_review_round4_verdict: CHANGES_REQUIRED (P2 explain WARN-contributor bug + P2 processor*/ QoI downstream gap)
codex_review_round4_relay: crs (effort=high, 86gs still 502)
codex_review_round5_verdict: CHANGES_REQUIRED (P1 honesty-fence leak when solver_gate.json missing)
codex_review_round5_relay: 86gs (recovered, effort=xhigh)
codex_review_round6_verdict: CHANGES_REQUIRED (P1 state-clobber on blocked-precondition ingest; P2 hard-coded WARN in banner-fallback DEFERRED to DEC-V61-201-SUB-INGEST-P2-FOLLOWUP per user 2026-05-21)
codex_review_round6_relay: 86gs stream interrupted → crs (effort=high)
codex_review_round7_verdict: CHANGES_REQUIRED (P1 over-broad BLOCKED guard suppresses legitimate post-residual BLOCKEDs + P2 decomposed-only BLOCK too aggressive for not_finalized references) — BOTH DEFERRED per user 2026-05-21 hard-stop discipline at 7 rounds (avoids N1.1 anti-pattern)
codex_review_round7_relay: 86gs (effort=xhigh)
review_chain_terminated: 2026-05-21 (user explicit stop after R7; remaining findings are tracked as known_limitations + follow-up sub-DECs, NOT iterated further)
known_limitations:
  - case_decomposed_not_reconstructed BLOCKs ingest for ALL manifests, but `audit/qoi.py` only needs top-level times when reference_comparison.status=="finalized". Decomposed-only cases with placeholder/not_finalized references could be ingested today. Tracked in DEC-V61-201-SUB-INGEST-P2-DECOMPOSED-NOT-FINALIZED. UX-only restriction, not a correctness break. [R7 P2]
closed_by_followup:
  - banner-fallback in read_artifacts hard-coded WARN → CLOSED by DEC-V61-201-SUB-INGEST-P2-FOLLOWUP (recompute via _parse_simplefoam_log + _compute_gate_from_residuals; LANDED 2026-05-22, worktree-agent-a7e599b4f6b581d31). [R6 P2]
  - solver.ingest's BLOCKED-skip guard was gate-status-only; over-suppressed post-residual BLOCKEDs (e.g., no_iterations_in_log) that should persist → CLOSED by DEC-V61-201-SUB-INGEST-P1-GUARD-DISCRIMINATE (tightened guard to also require details.execution=="skipped"; LANDED 2026-05-22, worktree-agent-a99d74ec81d8094d9, +2 functional LOC + 2 tests, 407→409 passing). [R7 P1]
---

## Why

case_027 Hagen-Poiseuille dogfood (`_sandboxes/case_027_hagen_poiseuille_pipe/
case_v65/DOGFOOD_CASE_027.md`) proved the audit subsystem has no path to advise
on cases that were run outside the harness. The engine assumes
`cfdtrust run → its own backend produces *_quality.json → audit reads`.

V-series corpus (case_003..case_028, APU bay, etc.) is hundreds of OFv2312
externally-run cases. Without an ingest path the audit engine is a closed
loop limited to its 3 bundled cases.

## What

Add `cfdtrust ingest <case_dir>` as a new CLI subcommand that:

1. Validates the case directory looks like an OpenFOAM case (reuse `run`'s env
   checks: Docker present, image pulled, system/constant/0 dirs).
2. Verifies it has been **externally executed**: at least one time directory
   beyond `0/` exists, and a solver log can be located.
3. Invokes `checkMesh` in the harness's Docker image against the existing
   `constant/polyMesh/` (does NOT re-run blockMesh or simpleFoam).
4. Reuses existing persistence helpers to write:
   - `artifacts/geometry_quality.json` from `_parse_polymesh_boundary`
   - `artifacts/mesh_quality.json` from `_parse_check_mesh_log`
   - `artifacts/bc_quality.json` via `_collect_and_persist_bc`
5. Locates the external solver log (searches `log_<solver>.txt`,
   `log.<solver>`, `<solver>.log`, `solver.log`) and transcribes it to
   `artifacts/solver.log`.
6. Parses the log → writes `artifacts/residuals.csv` via existing
   `_parse_simplefoam_log` + `_write_residuals_csv`.
7. Writes `artifacts/ingest_manifest.json` recording: source log path,
   SHA256 of source log, SHA256 of polyMesh/boundary, ingest timestamp,
   cfdtrust version, Docker image used for checkMesh.
8. Returns a solver gate with `details.execution = "ingested"`.

## Honesty fence (added to trust_report.schema.json)

- `solver_execution` enum extended: `["real", "mocked", "skipped", "ingested"]`
- Existing fences preserved unchanged:
  - `validation_status == "validated"` requires `solver_execution == "real"`
  - `overall_status == "PASS"` requires `solver_execution == "real"`
- `report.py` demotes `overall_status` from PASS to WARN when
  `solver_execution == "ingested"` (post-hoc honesty step — harness didn't
  witness the run, so cannot certify full PASS even if every gate is PASS).
- Mocked-solver schema rules (Red Team F-03) carried over to ingested:
  ingested + validated combo blocked at schema level via existing
  `validated → real` rule.

## What ingest does NOT do

- Does NOT re-run blockMesh or simpleFoam (would destroy existing time dirs +
  may fail on OpenFOAM-fork incompatibility).
- Does NOT verify the ingested log matches the current case files (a future
  enhancement could SHA the relevant `0/` + `constant/` files at run-time
  and store them; for MVP we trust the user's claim that the log corresponds
  to the current files).
- Does NOT permit `validation_status = "validated"` on ingested cases —
  validation requires a harness-witnessed run.

## Scope class (per v2.3)

Sub-DEC under DEC-V61-201. Not charter:
- Single subsystem touched (`ui/backend/audit/`).
- Additive CLI command + additive schema enum value.
- No cross-subsystem coupling.

## Acceptance criteria

- [ ] `cfdtrust ingest _sandboxes/case_027_hagen_poiseuille_pipe/case_v65`
      produces all 3 `*_quality.json` artifacts + `solver.log` + `residuals.csv`
      + `ingest_manifest.json`.
- [ ] `cfdtrust report` on the ingested case writes `solver_execution=ingested`
      in trust_report.json.
- [ ] `cfdtrust explain` produces gate-by-gate output reflecting actual mesh +
      BC state, not BLOCKED-due-to-missing-artifacts.
- [ ] pytest: 2 new ingest-specific tests in `cfdtrust_tests/` (synthetic case
      + schema rule).
- [ ] Existing 360-test suite still passes.

## Codex review

confidence: med (multi-file, schema-touch). Will run `codex-review-relay --base
main` after commit; round cap = 3 per V133.
