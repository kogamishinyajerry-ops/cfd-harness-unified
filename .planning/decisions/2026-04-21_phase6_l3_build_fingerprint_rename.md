---
decision_id: DEC-V61-023
timestamp: 2026-04-21T06:35 local
scope: L3 fix (Codex round-5 finding from DEC-V61-019). End-to-end rename of the audit-package manifest field `generated_at` → `build_fingerprint`. PR-5d.1 had made it a deterministic `sha256(case_id|run_id)[:16]` to preserve byte-reproducibility, but the old name misled reviewers who reasonably read values like `a843980d36d97c10` as wall-clock timestamps. Path A chosen (rename) over Path B (split signed fingerprint + unsigned wall-time).
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: aed95d4<FULL_SHA_TO_CONFIRM>
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_pr23_build_fingerprint_review.md
codex_verdict: pending (round 9 queued after rounds 7+8)
counter_status: "v6.1 autonomous_governance counter 3 → 4."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 <merge>` restores the `generated_at` name. No
  behavior change; only identifier renaming.)
notion_sync_status: pending
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/23
github_merge_sha: <to-fill-after-merge>
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 94%
  (Mechanical cross-file rename, 10 files, 61/-36 LOC. No behavior
  change; value is identical, only the identifier changes. Residual 6%:
  hypothetical external HTTP-API consumers depending on the old
  `generated_at` JSON key — none known; Phase 5 is v1 shipping.
  `src/report_engine/*` uses an independent `generated_at` for the
  contract-dashboard report and is NOT touched.)
supersedes: null
superseded_by: null
upstream: DEC-V61-019 (PR-5d.1 / L3 open question resolved here)
---

# DEC-V61-023: L3 — generated_at → build_fingerprint rename

## Rename scope

10 files. audit_package subsystem only:

- `src/audit_package/manifest.py` (kwarg + manifest field)
- `src/audit_package/serialize.py` (HTML renderer label)
- `ui/backend/routes/audit_package.py` (local variable + build_manifest call)
- `ui/backend/schemas/audit_package.py` (response field + Field docstring)
- `ui/backend/tests/test_audit_package_route.py` (4 assertions + new
  negative assertion for legacy key absence)
- `ui/frontend/src/types/audit_package.ts` (interface field)
- `ui/frontend/src/pages/AuditPackagePage.tsx` (UI label "Generated at"
  → "Build fingerprint" in `<code>` for monospace legibility)
- `tests/test_audit_package/test_manifest.py` (9 kwarg + dict-key refs)
- `tests/test_audit_package/test_serialize.py` (2 refs)
- `tests/test_audit_package/test_sign.py` (1 ref)

**Explicitly NOT renamed**: `src/report_engine/*` uses its own
independent `generated_at` for the contract-dashboard report (a real
datetime); unrelated to audit_package byte-repro.

## Regression

- 131/131 on the three audit_package test modules
- Full 9-file matrix 330/1skip (unchanged from P6-TD-002 baseline)
- `tsc --noEmit` on `ui/frontend` clean

## Codex round 9

Trigger: ≥3-file API schema rename per v6.1 new governance rule (Q3
codified in RETRO-V61-001). Review covers the cross-file consistency
of the rename + absence of stale references + frontend label accuracy.

## Closes

DEC-V61-019 L3 open question. No open-item cost from this work
(dedicated commit, no tech debt added).
