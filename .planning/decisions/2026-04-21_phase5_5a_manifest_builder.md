---
decision_id: DEC-V61-012
timestamp: 2026-04-21T00:15 local
scope: Path B · Phase 5 · PR-5a · Audit package manifest builder. First of 4 Phase 5 PRs. Introduces src/audit_package/ module with pure-function build_manifest that assembles a deterministic nested dict (schema_version=1) capturing case metadata + gold + run inputs/outputs + measurement + decision trail + git-pinned SHAs. No signing or serialization yet.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 1805f3d1` removes the new src/audit_package/
  module + tests. No changes to knowledge/, whitelist, existing src
  files, or UI. The new module is isolated and self-contained —
  reverting cleanly restores pre-Phase-5 state.)
notion_sync_status: synced 2026-04-21T00:25 (https://www.notion.so/348c68942bed81a5b69acf674242d3f6) — Decisions DB page created with Scope=Project, Status=Accepted, Canonical Follow-up=PR #12 URL
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/12
github_merge_sha: 1805f3d179bed6486846545a557748bbb52097ce
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 97%
  (Pure src/ module creation on autonomous turf. 26 unit tests covering
  loaders + integration + byte-stability. No禁区 touches. Determinism
  guarantees documented in module docstring. Reversibility is clean —
  new module has no consumers yet; removal = no side effects.)
supersedes: null
superseded_by: null
upstream: DEC-V61-011 (Q-2 closed → Phase 5 unblocked per DEC-V61-002)
kickoff_plan: .planning/phase5_audit_package_builder_kickoff.md
---

# DEC-V61-012: Phase 5 PR-5a — Audit package manifest builder

## Decision summary

First of 4 Phase 5 sub-PRs per the kickoff plan at `.planning/phase5_audit_package_builder_kickoff.md`. Introduces a new Python module `src/audit_package/` with a pure-function `build_manifest` that assembles a deterministic nested dict containing all evidence needed for a regulated-industry V&V audit package.

This is the **source-of-truth builder**: downstream PR-5b serializes the dict to zip/PDF, PR-5c signs with HMAC, PR-5d wires it into the Screen 6 UI. PR-5a itself has no UI, no serialization, no cryptography — it's just the deterministic assembly.

## Schema (schema_version = 1)

```
{
  "schema_version": 1,
  "manifest_id": "<case_id>-<run_id>",
  "generated_at": "ISO-8601 UTC, second precision",
  "git": {
    "repo_commit_sha": <HEAD>,
    "whitelist_commit_sha": <latest touching knowledge/whitelist.yaml>,
    "gold_standard_commit_sha": <latest touching the gold file>,
  },
  "case": {
    "id": "duct_flow",
    "legacy_ids": ["fully_developed_pipe", ...],
    "whitelist_entry": {<full dict from whitelist.yaml>},
    "gold_standard": {<full dict from gold_standards/<id>.yaml>},
  },
  "run": {
    "run_id": "<caller-supplied>",
    "status": "output_present" | "no_run_output",
    "solver": "simpleFoam",
    "inputs": {"system/controlDict", "system/blockMeshDict", ..., "0/": {...}},
    "outputs": {"solver_log_name", "solver_log_tail", "postProcessing_sets_files"},
  },
  "measurement": {
    "key_quantities": {<from comparator>},
    "comparator_verdict": "PASS" | "FAIL" | "HAZARD" | None,
    "audit_concerns": [{"code": "...", "severity": "..."}, ...],
  },
  "decision_trail": [
    {"decision_id": "DEC-V61-011", "title": "...", "relative_path": ".planning/decisions/..."},
  ],
}
```

## Determinism guarantees

1. **Caller-injectable `generated_at`** — tests inject a fixed timestamp to assert byte-stable output.
2. **Git-SHA pinning at build time** — any subsequent edit of whitelist or gold requires a new build; the SHA captured in the manifest is the answer-of-record.
3. **Git-absent → `None`, not raise** — manifest builds successfully even outside a git working tree.
4. **Decision-trail discovery is deterministic** — glob-sorted filenames, body-grep on `case_id` + legacy aliases (auto-expanded from `gold.legacy_case_ids` — so a `duct_flow` manifest picks up the `fully_developed_pipe` DECs via Q-2 rename history).
5. **File paths as repo-relative POSIX strings** — no absolute paths in the dict.
6. **Log tail bounded at 120 lines** — keeps manifest dict size reasonable; the zip bundle in PR-5b will include full logs.

The byte-stability test (`test_byte_stable_across_two_invocations`) proves two calls with identical inputs + `generated_at` produce identical `json.dumps(..., sort_keys=True)`.

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (DEC-V61-003 turf) | YES — new `src/audit_package/` module (~350 LOC) |
| `tests/` | YES — new `tests/test_audit_package/` (~26 tests) |
| `knowledge/**` | READ-ONLY (loads whitelist + gold; no writes) |
| `.planning/decisions/**` | READ-ONLY (grep for decision trail; no writes) |
| Notion DB destruction | NOT TOUCHED (one new page) |

## Regression

```
pytest tests/test_foam_agent_adapter.py tests/test_result_comparator.py \
       tests/test_task_runner.py tests/test_e2e_mock.py \
       tests/test_correction_recorder.py tests/test_knowledge_db.py \
       tests/test_auto_verifier tests/test_audit_package -q
→ 222 passed in 1.50s
```

196 prior baseline + 26 new across 5 test classes.

## Non-goals (deferred to subsequent Phase 5 PRs)

- **PR-5b** (`src/audit_package/serialize.py`) — deterministic zip + weasyprint PDF serialization from the manifest dict. Must produce byte-identical zip from identical dict. Design question from kickoff plan: weasyprint vs reportlab. DEC-V61-013.
- **PR-5c** (`src/audit_package/sign.py`) — HMAC-SHA256 over `(manifest_canonical_json, zip_bytes)`, sidecar `.sig` file, round-trip verify, constant-time compare. HMAC key from env var `CFD_HARNESS_HMAC_SECRET`. DEC-V61-014.
- **PR-5d** — FastAPI route + React Screen 6 page wiring the above into the UI, with FDA V&V40 checklist mapping. DEC-V61-015.

## Counter status

v6.1 autonomous_governance counter: 8 → **9**. Hard-floor-4 threshold is ≥10 autonomous DECs → **1 slot remaining** before the next self-review-of-autonomy trigger. Recommendation: Codex tool review for at least one of the upcoming PR-5b/c/d to stretch the counter and introduce a second pair of eyes before the threshold fires.

## Reversibility

One `git revert -m 1 1805f3d1` removes `src/audit_package/` + `tests/test_audit_package/` entirely. No consumers exist yet (PR-5b/c/d haven't landed), so there's nothing to break. Clean revert.

## Next steps

1. Mirror this DEC to Notion Decisions DB.
2. Update `.planning/STATE.md` with PR-5a landing.
3. Confirm with Kogami on 5 open design questions from kickoff plan (PDF library, HMAC rotation, V&V40 scope, export mode, demo PR) before starting PR-5b.
4. Start PR-5b serialize module when design questions resolved.
