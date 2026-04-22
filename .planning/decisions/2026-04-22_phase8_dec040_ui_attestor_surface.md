---
decision_id: DEC-V61-040
timestamp: 2026-04-22T13:20 local
scope: |
  Phase 8 Sprint 1 — surface DEC-V61-038 attestor verdict (A1..A6)
  through the API and render it in the UI next to the scalar contract
  chip (DEC-V61-039 already added the pointwise profile verdict). The
  attestor was written into the audit fixtures at Phase 5a time but
  never threaded through ValidationReport until now; the UI saw only
  the scalar contract. Fix: ValidationReport gains an `attestation`
  field; frontend gains AttestorBadge + AttestorPanel components.

autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: pending
codex_rounds: 0
codex_verdict: pending
counter_status: |
  v6.1 autonomous_governance counter 27 → 28. Next retro at 30.
reversibility: fully-reversible — additive schema field + two React
  components + one fixture block. Revert = 5 files restored, fixtures
  unchanged semantically (attestation block is additive).
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
external_gate_self_estimated_pass_rate: 0.80
  (Narrow additive change, mirrors the DEC-V61-039 shape. Main risk:
  AttestorPanel visual layout on very narrow viewports — not exercised
  by backend tests.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-038 (convergence attestor A1..A6) — emits the verdict into
    the audit fixture; this DEC pipes it through to the UI.
  - DEC-V61-039 (LDC verdict reconciliation) — established the
    multi-verdict surface pattern (scalar + profile); this DEC extends
    it with the third tier (attestor).
  - User 2026-04-22: "按照你的建议来，一定要确保准确性、可靠性" —
    directive to make all three verdicts honestly visible.
---

# DEC-V61-040: UI tier — attestor verdict surface

## Why now

DEC-V61-038 planted the A1..A6 attestor at audit-fixture time but the
verdict dead-ended in the YAML; `/api/validation-report` never returned
it. The UI could only show the scalar contract — the same PASS-washing
surface area the 2026-04-22 deep-review flagged. With DEC-V61-039
already in place for profile verdicts, adding attestation completes
the honest 3-verdict rendering:

| Verdict           | Question answered                          |
|-------------------|---------------------------------------------|
| contract_status   | Did the scalar measurement land in band?    |
| profile_verdict   | How many gold profile points lie in band?   |
| attestation       | Did the solver actually converge cleanly?   |

LDC audit_real_run is the canonical split-brain case: contract=FAIL,
profile=PARTIAL (11/17), attestation=ATTEST_PASS. All three now
visible in the UI.

## What lands

1. `ui/backend/schemas/validation.py`:
   - `AttestVerdict` Literal (ATTEST_PASS/HAZARD/FAIL/NOT_APPLICABLE)
   - `AttestorCheck` BaseModel (check_id, verdict, concern_type, summary)
   - `AttestorVerdict` BaseModel (overall, checks[])
   - `ValidationReport.attestation: AttestorVerdict | None = None`

2. `ui/backend/services/validation_report.py`:
   - `_make_attestation(doc)` lifts the fixture's `attestation:` block
     (already written by phase5_audit_run.py) into the schema.
   - `build_validation_report` threads it into the response.

3. `ui/frontend/src/types/validation.ts`:
   - Matching `AttestVerdict`, `AttestorCheck`, `AttestorVerdict` types.
   - `ValidationReportExtras.attestation` field.

4. `ui/frontend/src/components/AttestorBadge.tsx`:
   - 4-state pill matching PassFailChip visual grammar.

5. `ui/frontend/src/components/AttestorPanel.tsx`:
   - Per-check (A1..A6) breakdown with verdict + summary + concern_type.

6. `ui/frontend/src/pages/ValidationReportPage.tsx`:
   - AttestorBadge next to PassFailChip in header.
   - Inline profile_verdict pill (DEC-V61-039 surfaced, was previously
     only accessible via the API).
   - AttestorPanel below concerns/preconditions grid.

7. Fixture backfill:
   `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml`
   gains an `attestation:` block with all-PASS A1..A6 (LDC converges
   cleanly — the only split-brain is scalar vs profile).

8. Tests: `test_dec040_attestation_surface.py`, 3 tests:
   - LDC audit_real_run returns ATTEST_PASS with 6 PASS checks
   - reference_pass (no solver log) returns null attestation
   - OpenAPI schema documents AttestorVerdict + AttestorCheck

## Live verification

```
contract_status: FAIL
profile_verdict: PARTIAL (11 / 17)
attestation.overall: ATTEST_PASS
attestation.checks: [('A1','PASS'),('A2','PASS'),('A3','PASS'),
                     ('A4','PASS'),('A5','PASS'),('A6','PASS')]
```

Backend: 200/200 tests green (197 → 200, +3 DEC-040).
Frontend: `tsc --noEmit` clean.

## Deferred / follow-up

- Backfilling `attestation:` blocks on the other 9 cases' audit
  fixtures — needs re-running `scripts/phase5_audit_run.py` for each,
  which is a Phase 5a refresh, not a DEC-040 concern. Until that
  happens, non-LDC cases surface `attestation: null` (handled — the
  UI renders "No solver log available for this run").
- TierRail component (SHOULD in research) is deferred until more cases
  leave Tier 3 (which needs DEC-042/043/044 per-case extractor fixes).

## Counter + Codex

27 → 28. Self-pass 0.80. Codex post-merge acceptable per RETRO-V61-001
(narrow additive change, mirrors DEC-V61-039 shape, > 0.70 threshold).
Will run Codex anyway given the sustained per-DEC validation cadence.

## Related

- DEC-V61-038 — upstream: writes the attestation into the fixture
- DEC-V61-039 — sibling: profile verdict reconciliation (same shape)
- DEC-V61-042+ (future) — per-case extractor fixes that will add
  attestation blocks to the remaining 9 fixtures
