---
decision_id: DEC-V61-019
timestamp: 2026-04-21T04:30 local
scope: Path B · Phase 5 · PR-5d.1 · Three verbatim Codex-recommended fixes closing the `CHANGES_REQUIRED` verdict on PR-5d. HIGH #1 (unknown case_id → 404), HIGH #2 (stable `generated_at` for byte-reproducibility), MEDIUM (rename `vv40_checklist` → `evidence_summary`). Post-merge Codex review queued as round 5 to confirm closure.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: ca9fe0e525a92e8b52ea32092e228b0bf7ace73e
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_pr5d1_closure_review.md
codex_verdict: APPROVED_WITH_NOTES (2026-04-21T04:35 local · 95,221 tokens)
counter_status: "v6.1 autonomous_governance counter 15 → 16. 5th consecutive Codex post-merge review across Phase 5 (PR-5c, 5c.1, 5c.2, 5d, 5d.1). Overdue retrospective still owed — see P1 in new_session_kickoff."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 ca9fe0e` restores PR-5d's unsafe-sign-anything
  semantics + wall-clock-stamped manifest + V&V40 label. Staging dir
  structure unchanged; no migration cost either direction.)
notion_sync_status: pending-sync (round 5 verdict landed; Notion mirror queued)
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/19
github_merge_sha: ca9fe0e525a92e8b52ea32092e228b0bf7ace73e
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 90%
  (Self-estimate held. Codex round 5 returned APPROVED_WITH_NOTES with
  Critical/High/Medium all NONE. One Low/Informational note recorded:
  `generated_at` is now a deterministic hash fragment, but the field
  is still labelled as a timestamp in API/UI/docs. Queued as tech
  debt for a future rename to `build_fingerprint` or a real UTC
  timestamp carried outside the signed canonical payload. Codex
  explicitly confirmed the `|` delimiter collision concern is benign
  under the current whitelist and that full-manifest signatures still
  bind integrity regardless of the 16-hex prefix.)
supersedes: null
superseded_by: null
upstream: DEC-V61-018 (PR-5d — this DEC closes all three Codex findings)
kickoff_plan: .planning/phase5_audit_package_builder_kickoff.md
---

# DEC-V61-019: Phase 5 PR-5d.1 — Codex HIGH #1 + HIGH #2 + MEDIUM closure

## Decision summary

Mechanical follow-up PR addressing the three findings in the Codex
round-4 review of PR-5d (`reports/codex_tool_reports/2026-04-21_pr5d_screen6_review.md`,
verdict `CHANGES_REQUIRED`). All three fixes are verbatim implementations
of the `Suggested fix` bullet in the corresponding Codex finding.
Phase 5 now honestly ships: Screen 6 can no longer sign hollow bundles
for unknown cases, identical POSTs produce byte-identical signed zips,
and the UI labelling no longer implies FDA V&V40 compliance the artifact
does not provide.

## Changes

### HIGH #1 · Whitelist gate at POST

`ui/backend/routes/audit_package.py`:
- Imports `load_case_detail` from `ui.backend.services.validation_report`.
- POST handler calls it first; `None` → `HTTPException(status_code=404,
  detail=f"unknown case_id: {case_id!r} (not in knowledge/whitelist.yaml)")`.
- Existing HMAC-secret-missing guard is unchanged and still runs only
  after the whitelist check passes.

`ui/backend/tests/test_audit_package_route.py`:
- `test_unknown_case_id_still_builds_skeleton` (which blessed the
  unsafe behavior) replaced by `test_unknown_case_id_returns_404`
  asserting the 404 + `detail` substring.

### HIGH #2 · Deterministic `generated_at`

`ui/backend/routes/audit_package.py`:
- Imports `hashlib`.
- Before `build_manifest()`, computes
  `generated_at = hashlib.sha256(f"{case_id}|{run_id}".encode("utf-8")).hexdigest()[:16]`
  and passes it as the `generated_at=` kwarg. The kwarg was already
  exposed on `src.audit_package.build_manifest` for test byte-stability
  assertions (see `src/audit_package/manifest.py:314`).

`ui/backend/tests/test_audit_package_route.py`:
- `test_identical_posts_produce_byte_identical_zip`: two POSTs with the
  same `(case_id, run_id)` → same `generated_at`, same `signature_hex`,
  same SHA-256 of the downloaded `bundle.zip`.
- `test_different_run_ids_produce_different_bundles`: sanity guard that
  distinct inputs still diverge (no accidental cache-key collision).

### MEDIUM · `vv40_checklist` → `evidence_summary`

Backend:
- `ui/backend/schemas/audit_package.py`:
  `AuditPackageVvChecklistItem` → `AuditPackageEvidenceItem`; response
  field `vv40_checklist` → `evidence_summary`. Docstring clarifies this
  is a product-specific summary, NOT a faithful FDA/ASME V&V40 template,
  and notes that `run.inputs` / `run.outputs.*` / `measurement.*` fields
  are populated only when run artifacts are attached.
- `ui/backend/routes/audit_package.py`:
  `_VV40_CHECKLIST` → `_EVIDENCE_SUMMARY`. Module comment cites FDA
  guidance URL (`https://www.fda.gov/media/154985/download`) and
  explains the rename rationale.

Frontend:
- `ui/frontend/src/types/audit_package.ts`:
  `AuditPackageVvChecklistItem` → `AuditPackageEvidenceItem`; interface
  field renamed.
- `ui/frontend/src/pages/AuditPackagePage.tsx`:
  Section heading "FDA V&V40 credibility-evidence mapping" → "Internal
  V&V evidence summary" + subtitle disclaimer noting it's not a V&V40
  substitute. Page-level header description trimmed to remove FDA /
  aerospace / nuclear licensing claims that the current skeleton-bundle
  shape does not support.

Tests:
- `test_vv40_checklist_has_eight_areas` renamed to
  `test_evidence_summary_has_eight_areas`.
- `test_build_returns_200_with_expected_shape` now also asserts the
  legacy `vv40_checklist` key does not leak into the response JSON.

## Regression

```
pytest 9-file matrix → 327 passed + 1 skipped in 2.91s
                       (baseline 325 + 2 new byte-reproducibility tests)
pytest ui/backend/tests/test_audit_package_route.py → 18 passed
ui/frontend: npx tsc --noEmit → clean
```

Pre-existing deprecation warnings (`datetime.datetime.utcnow()` in
`correction_recorder.py:76` + `knowledge_db.py:220`) unchanged — they
predate PR-5d.1 and are queued as P4 tech-debt in the new-session
kickoff.

## Codex findings ledger (Phase 5 FINAL · rounds 1-5)

| ID | PR | Severity | Status | Resolution |
|---|---|---|---|---|
| HIGH #1 (unknown case_id) | PR-5d → 5d.1 | High | ✅ **CLOSED** (round 5 confirmed) | Whitelist 404 gate |
| HIGH #2 (byte-repro) | PR-5d → 5d.1 | High | ✅ **CLOSED** (round 5 confirmed) | Deterministic generated_at |
| MEDIUM (V&V40 label) | PR-5d → 5d.1 | Medium | ✅ **CLOSED** (round 5 confirmed) | Evidence-summary rename |
| M1 (env-var prefix) | PR-5c → 5c.1 | Medium | ✅ CLOSED earlier | Explicit prefix contract |
| M2 (sidecar v2) | PR-5c | Medium | 🔒 QUEUED | Governance DEC — kid/alg/domain metadata |
| M3 (legacy migration) | PR-5c.1 → 5c.2 | Medium | ✅ CLOSED earlier | Docs-only migration note |
| L1 (sidecar hex shape) | PR-5c → 5c.1 | Low | ✅ CLOSED earlier | ^[0-9a-fA-F]{64}$ regex |
| L2 (canonical JSON spec) | PR-5c | Low | 🔒 QUEUED | Public spec doc |
| **L3** (generated_at semantics) | **PR-5d.1 → future** | **Low** | **🔒 NEW — QUEUED** | **Rename to `build_fingerprint`, or move human-readable UTC timestamp outside signed canonical payload** |

Cumulative Codex token cost across Phase 5 rounds 1-5:
117,588 + 76,152 + 94,316 + 143,521 + 95,221 = **526,798 tokens**.

Round 4 (PR-5d) was the highest-value review — caught the semantic
HIGH findings that module-level rounds 1-3 couldn't see. Round 5
(PR-5d.1) was smaller-scope validation that the HIGH/MEDIUM closure
held and exposed only one Low/Informational follow-up item (L3 above).

## Codex round 5 · Low finding detail

> PR-5d.1 preserves byte reproducibility by replacing `generated_at`
> with a deterministic hash fragment, but the API/manifest/UI still
> present that field as a timestamp.

Evidence locations (per round-5 report):
- `ui/backend/routes/audit_package.py:167-175` — route computes
  `hashlib.sha256(f"{case_id}|{run_id}")[:16]`
- `src/audit_package/manifest.py:340-342` / `409-413` — `build_manifest`
  emits the kwarg verbatim in a field semantically named "timestamp"
- `ui/frontend/src/pages/AuditPackagePage.tsx:133-136` — UI label
  reads "Generated at" for a value that is now opaque hex
- `docs/ui_design.md:376-378` — design doc still describes timestamps
  as canonicalized UTC values

Why it matters: reviewers or downstream consumers will reasonably read
`generated_at` as a wall-clock build time. Current values are opaque
tokens like `a843980d36d97c10`.

**L3 mitigation paths (not applied in PR-5d.1, queued):**

A. **Rename the field end-to-end** to `build_fingerprint` or
   `deterministic_build_id`. Touches backend schema + route + tests +
   frontend types + frontend page label + manifest.py kwarg signature.
   ~25 LOC. Breaks any external consumers that depend on the current
   `generated_at` JSON key — OK for Phase 5 (no external consumers
   exist yet).

B. **Carry a real UTC timestamp outside the signed canonical payload.**
   Add `build_wall_time: str` field in the response + UI that is NOT
   part of `canonical_manifest_bytes()` input to HMAC. The signed
   `generated_at` stays as the deterministic fingerprint. Two humans
   reading the bundle still get a real timestamp; signatures stay
   byte-reproducible. ~40 LOC and more architectural.

Path B is more faithful to what "Generated at" means in human terms,
but adds a second metadata field. Path A is simpler and honest.
Decision deferred to Kogami; neither blocks Phase 5 shipping.

## Scope self-attestation

Within v6.1 autonomous turf:

| Area | Touched? |
|---|---|
| `ui/backend/` (DEC-V61-003 turf) | YES — route + schema + tests |
| `ui/frontend/` (DEC-V61-003 turf) | YES — types + page |
| `src/` | NOT TOUCHED — manifest.build_manifest kwarg surface unchanged |
| `knowledge/gold_standards/**` | NOT TOUCHED (禁区) |
| `knowledge/whitelist.yaml` `reference_values` | NOT TOUCHED (禁区) |
| `reports/codex_tool_reports/` | round 5 artifact pending |

## Honest status

**Phase 5 is now honestly complete**, conditional on Codex round 5
confirming closure. The technical plumbing was correct in PR-5d; PR-5d.1
makes the semantic surface honest. Screen 6 now:

- Refuses to sign bundles for cases not in the whitelist (404).
- Produces byte-identical signed zips for identical inputs
  (reproducibility contract from `docs/ui_roadmap.md:220-223` restored).
- Labels the 8-row table as an internal product-specific evidence
  summary rather than claiming FDA/ASME V&V40 compliance.

If Codex round 5 returns `APPROVED` or `APPROVED_WITH_NOTES`, Phase 5
closes at 4/4 and next work is either (a) the overdue v6.1 counter-15+
retrospective or (b) Phase 6 scoping per DEC-V61-002's phase plan.

If Codex round 5 returns `CHANGES_REQUIRED`, we open PR-5d.2 — same
mechanical-follow-up pattern as PR-5c → PR-5c.1 → PR-5c.2.

## Reversibility

`git revert -m 1 ca9fe0e` cleanly restores PR-5d semantics. The
`ui/frontend` types + page would regenerate on `tsc` without issue; the
backend routes would reaccept unknown case_id and re-stamp wall-clock
time. No migration cost either direction.
