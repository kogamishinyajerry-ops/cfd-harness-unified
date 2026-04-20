---
decision_id: DEC-V61-018
timestamp: 2026-04-21T03:30 local
scope: Path B · Phase 5 · PR-5d · Screen 6 Audit Package Builder UI + API route. FastAPI route (build POST + 5 download GETs) + React page with V&V40 mapping. **Post-merge Codex review returned CHANGES_REQUIRED** with 2 HIGH findings (empty-evidence bundles + broken byte-reproducibility) + 1 MEDIUM (V&V40 overstatement). Phase 5 is NOT complete until PR-5d.1 mitigations land.
autonomous_governance: true
claude_signoff: conditionally (pending PR-5d.1)
codex_tool_invoked: true
codex_diff_hash: 320bed1012ea55be73ef4cda77118d0dfe66e7bb
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md
codex_verdict: CHANGES_REQUIRED
counter_status: "v6.1 autonomous_governance counter 14 → 15. 4th consecutive Codex post-merge review."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 320bed10` removes route + schema + frontend
  + tests + staging dir gitignore entry. Layout nav returns to disabled.
  PR-5c/5b/5a from earlier are intact — their code has no dependency
  on PR-5d.)
notion_sync_status: synced 2026-04-21T03:40 (https://www.notion.so/348c68942bed81f1aa6bdb993c3fde2f) — Decisions DB page created Status=Proposed pending PR-5d.1 decision
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/18
github_merge_sha: 320bed1012ea55be73ef4cda77118d0dfe66e7bb
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 60%
  (Technical plumbing is correct — path traversal, HMAC handling,
  tests all pass review. BUT the SEMANTIC behavior is wrong: signs
  empty-evidence bundles + accepts nonexistent cases + breaks
  byte-reproducibility. Codex is right. Follow-up PR-5d.1 required
  before Phase 5 can honestly ship.)
supersedes: null
superseded_by: null
upstream: DEC-V61-017 (PR-5c.3 — signing module finalized)
followup_pr: PR-5d.1 (must land to close HIGH findings)
---

# DEC-V61-018: Phase 5 PR-5d — Screen 6 UI + API route (CHANGES_REQUIRED)

## Decision summary

Final Phase 5 main-sequence PR landed: FastAPI route + React page wiring PR-5a/5b/5c into an operator surface. 16 new route tests, full-stack regression 325/1skip green. TypeScript compiles clean.

**However**, post-merge Codex GPT-5.4 xhigh review returned **`CHANGES_REQUIRED`** with 2 HIGH findings that invalidate the honest claim "Phase 5 complete". PR-5d.1 is required before Phase 5 can ship.

## Codex findings (full detail)

Full report: `reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md` (token 143,521, 4th consecutive Codex review).

### HIGH #1 — Empty-evidence bundles signed as if they were real

`build_manifest(case_id=case_id, run_id=run_id)` is called without `run_output_dir`, `measurement`, `comparator_verdict`, or `audit_concerns`. The resulting manifest has `run.status="no_run_output"` and empty measurement fields. The bundle gets HMAC-signed anyway. Additionally, `POST /api/cases/nonexistent_case/runs/r1/...` returns 200 (test `test_unknown_case_id_still_builds_skeleton` blesses this behavior).

**Why this matters in a regulated context**: A signed "audit package" that contains no solver inputs, no outputs, no comparator verdict, and no case validation is not evidence — it's a dangerously misleading artifact. A reviewer trusting the signature would assume content provenance was also meaningful.

**Codex recommendation**: reject unknown case/run IDs, or require a resolved run-output/comparator source before signing. Alternatively, clearly demote this endpoint to a dry-run/mock export and gate it behind a UI flag so production operators don't produce it unintentionally.

### HIGH #2 — Byte-reproducibility contract broken at the operator endpoint

DEC-V61-013 documented byte-reproducibility as a core property (PR-5c HMAC stability depends on it). But PR-5d's route does not pass a stable `generated_at` to `build_manifest()`, so the builder auto-stamps current UTC on every POST. Codex probe: two identical POSTs one second apart produced different `generated_at`, different ZIP SHA-256, different HMAC.

**Why this matters**: Operators cannot reproduce or diff the same run's bundle. Signatures rotate merely because wall-clock time changed. External verifiers expecting deterministic re-derivation of the signed zip will see a divergence they can't explain.

**Codex recommendation**: derive `generated_at` from stable run metadata (e.g., hash of inputs + git SHA) so identical inputs produce identical outputs, OR move the human-readable build timestamp outside the signed canonical payload.

### MEDIUM — V&V40 checklist overstates FDA alignment

The 8-area checklist is a product-specific summary, not a faithful rendering of FDA 2023 CM&S guidance (which structures credibility around preliminary steps, credibility evidence categories, and credibility factors/goals — NOT this 8-row list). Several mapped fields (`run.inputs`, `run.outputs.solver_log_tail`, `measurement.*`) are absent from current bundles due to HIGH #1.

Reference: https://www.fda.gov/media/154985/download (FDA guidance PDF TOC p.3 lines 42-56)

**Codex recommendation**: rename to internal "evidence summary" until the real framework template exists, or align to guidance categories and only reference fields guaranteed to be present in the current bundle shape.

### Non-blocking notes

- Path-traversal guard: sound
- HMAC secret handling: no disclosure leak
- Staging directory: no race; cleanup gap acknowledged (ops work, PR-5e)
- FileResponse + Content-Disposition: correct
- Frontend state handling: no bugs
- Python 3.9 compatibility: broader issue (`pyproject.toml` says ≥3.9 but tests fail on 3.9.6) — not PR-5d-specific

## PR-5d.1 mitigation plan (queued)

Three concrete changes to close HIGH #1 + HIGH #2 + MEDIUM:

1. **Reject unknown case_id** at POST time:
   - Look up `case_id` in whitelist; return 404 `{"detail": "unknown case: <id>"}` if absent.
   - Remove `test_unknown_case_id_still_builds_skeleton` and replace with `test_unknown_case_id_returns_404`.
   - Optional: also require a resolved run_output_dir (or an explicit `mock_mode=true` query param that tags the manifest as dry-run and renames bundle files).

2. **Stable `generated_at`** in manifest:
   - Derive from deterministic inputs, e.g., `sha256(f"{case_id}|{run_id}|{repo_commit_sha}").hexdigest()[:12]` used as opaque build-id OR a caller-supplied `generated_at` query/body param.
   - Fallback to current UTC only if explicitly requested (`?real_time=true`).
   - Test: two POSTs with identical inputs → same ZIP SHA-256.

3. **V&V40 checklist renaming**:
   - Heading text: "FDA V&V40 credibility-evidence mapping" → "Internal V&V evidence summary (not a substitute for formal V&V40 template)".
   - Frontend + backend schema `vv40_checklist` → `evidence_summary` (or keep name but update label text).
   - Remove manifest field references that current skeleton bundles don't provide (or mark them as "expected when run artifacts are attached").

Estimated: ~80 LOC src + ~60 LOC tests. Can land in a single follow-up PR.

## Codex review-arc final tally

4 post-merge reviews across Phase 5 signing + UI:

| Round | PR | Tokens | Verdict | Outcome |
|---|---|---|---|---|
| 1 | PR-5c (#14) | 117,588 | APPROVED_WITH_NOTES | M1+M2+L1+L2 queued |
| 2 | PR-5c.1 (#15) | 76,152 | APPROVED_WITH_NOTES | M3 queued |
| 3 | PR-5c.2 (#16) | 94,316 | APPROVED_WITH_NOTES | Warning class issue |
| 4 | **PR-5d (#18)** | **143,521** | **CHANGES_REQUIRED** | **HIGH #1+#2, MED** |

Cumulative token cost: **431,577**. Round 4 was the highest-value review — caught semantic issues the prior rounds couldn't see (they covered the signing module alone; UI wiring reveals what the operator actually gets).

## 禁区 compliance

| Area | Touched? |
|---|---|
| `ui/backend/` (DEC-V61-003 turf) | YES — new route + schema + tests |
| `ui/frontend/` | YES — new page + routing + API client |
| `knowledge/**` | NOT TOUCHED |

## Counter

v6.1 autonomous_governance counter: 14 → **15**. 4 consecutive Codex reviews demonstrate the pattern works — counter discipline is earning its keep, this time by catching real semantic regressions a self-signed review would have missed.

## Reversibility

One `git revert -m 1 320bed10` restores PR-5c.3 main state with Screen 6 disabled in nav. This is the clean fallback if Kogami prefers to defer PR-5d.1 scope indefinitely.

## ⚠️ Honest status

**Phase 5 is NOT complete until PR-5d.1 closes HIGH #1 + HIGH #2.**

The technical plumbing landed correctly (path traversal, HMAC env, tests, frontend render). But the semantic surface — what an operator actually produces — currently generates misleading artifacts in a regulated-review context. Claiming Phase 5 complete now would be dishonest.

## Next steps — require Kogami decision

1. **Option X1** — Land PR-5d.1 now with all three fixes before proceeding.
2. **Option X2** — Revert PR-5d entirely; land a redesigned PR-5d-v2 with the fixes baked in.
3. **Option X3** — Accept the current state as "dry-run mock endpoint" explicitly and gate Screen 6 behind a feature flag until a real-run binding is wired (larger scope; deferred to Phase 5.5 or Phase 6).
4. **Option X4** — Defer PR-5d.1 to a later session; document CHANGES_REQUIRED in STATE + freeze Screen 6 nav/endpoint.

Default recommendation: **X1** (PR-5d.1 as immediate mechanical follow-up), sized at ~140 LOC total, mirrors the PR-5c → PR-5c.1/5c.2/5c.3 mechanical-followup pattern that already worked three times.
