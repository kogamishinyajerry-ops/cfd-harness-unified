# Kogami Review · v109_case_lock_pr_review · 2026-05-02

**Verdict**: `APPROVE_WITH_COMMENTS`
**Recommended next**: `merge`
**Trigger**: high-risk-pr
**Artifact**: `.planning/reviews/kogami/v109_case_lock_o_nofollow_2026-05-02/pr_review_packet.md`
**Prompt SHA256**: `ddb2653f3ba2633d84a0ecfac5b47d765d882c5de539ab6bc79b6f6b8864de53`

## Summary

DEC-V61-109 is a coherent, scope-appropriate fix for the V108-A documented residual on the shared case_lock primitive. Codex 2-round chain reached APPROVE with the R1 P2 closure demonstrating genuine pre/post-V109 distinguishing power. Strategic fit with M7.1 is sound; documented residuals (parent-path symlink, patch_classification belt-and-braces) are explicitly acknowledged with correct out-of-scope framing. Three P2/P3 findings on governance hygiene noted below.

## Strategic Assessment

Decision-arc coherence: STRONG. V107 (numerics) → V107.5 (solver migration) → V108-A (per-patch BC store) → V108-B (frontend panel) → V109 (closing the documented case_lock residual that V108-A could only document) is the correct sequencing. RETRO-V61-V107-V108 R1 ('read shared primitives before fd-hardening') is being lived out in V109's design — V109 reads case_lock's path-based open contract first and re-architects rather than layering. Roadmap fit: M7.1 imported-case → real-run hardening per Kogami's RETRO strategic-fit note is correctly cited; the cross-cutting threat model gap (case_lock symlink swap) is precisely the class of issue that becomes load-bearing once stranger-dogfood imported cases hit production at M7-M8. Retrospective completeness: R5 trigger procedurally honored (this Kogami review fires because of merge_risk_summary risk_class=high); R5 substantive close needs the §10.5.4a evaluation noted in finding #3. The packet's 'pragmatic-relaxation' avoidance is encouraging — the architectural close (revert cleanup on symlink_escape branch + document residual + new V109 closes residual) is the correct shape, not a verbatim shortcut.

## Findings

### [P2] Darwin openat race workaround scope-folding rationale not documented
**Position**: ?

**Problem**: §Reviewer ask 3 itself raises whether `_open_or_create_lock_fd` (Darwin kernel race workaround) should have been a separate DEC rather than absorbed into V109. The packet asks the question but does not commit a strategic answer. RETRO-V61-V107-V108 R1 explicitly recommended 'read shared primitives before fd-hardening on top of them' — the Darwin workaround is exactly the class of mid-implementation discovery that RETRO flagged, and bundling it without explicit rationale risks repeating the V107.5-R16 'pragmatic scope reduction' precedent that this same retro disposed as 'ONE-OFF, non-repeating'.

**Recommendation**: In the DEC body (or strategic package), commit to a position: either (a) the Darwin workaround is in-scope because it is a same-blast-radius portability fix without which V109's atomic open-or-create cannot land cross-platform, OR (b) split into a follow-up V109.1 micro-DEC. Recommendation (a) is defensible given the workaround is local to `_open_or_create_lock_fd` and shares the V109 threat model; pick it explicitly rather than leaving the question open.

### [P2] patch_classification belt-and-braces cleanup queued without DEC reference
**Position**: ?

**Problem**: §Documented residuals states 'Phase 2 cleanup to drop [_assert_fd_still_matches_path] is queued but out of V109 scope.' RETRO-V61-V107-V108 R5 (which this packet is the trigger for) and R4 (DEC backfill workstream) emphasize that residuals-as-paragraph-in-chain-report silently rot. Queueing 'Phase 2 cleanup' without a tracked DEC id (e.g., DEC-V61-110 placeholder or charter-future entry) recreates exactly the silent-rot risk that motivated V109 itself.

**Recommendation**: Add an explicit successor reference in the DEC frontmatter: either `unblocks_followup: DEC-V61-110-patch-classification-cleanup` (tracked-future) or a `.planning/charter-future/` entry pointing at the cleanup. The reference need not commit to a timeline; it must commit to durable trackability.

### [P2] §10.5.4a audit-required-surface treatment claim is asserted without evidence in packet
**Position**: ?

**Problem**: §Reviewer ask 2 explicitly invokes RETRO-V61-V107-V108 R5: 'case_lock O_NOFOLLOW residual must trigger §10.5.4a high-risk-PR Kogami when filed as DEC-V61-109'. The packet's merge_risk_summary correctly carries `risk_class=high` and triggers this Kogami review, satisfying the procedural half. However, the packet does not show whether methodology v2.0 §10.5.4a's 7-surface list was reviewed for an update — RETRO R5 specifically required: 'Update the §10.5.4a surface list in methodology v2.0 if the fix exposes new shared-infra primitives that warrant audit-required status (e.g., the new O_NOFOLLOW-protected open path).' The packet is silent on whether this update was performed or evaluated.

**Recommendation**: Add to the DEC body a one-line evaluation: either (a) 'The O_NOFOLLOW-protected case_lock open path is a hardening of an existing surface (already implicitly covered by surface #1 FoamAgentExecutor call sites and surface #5 user_drafts→TaskSpec plumbing); no §10.5.4a list addition required', OR (b) propose a new surface #8 explicitly. Closing R5 procedurally is necessary; closing it substantively requires this evaluation.

### [P3] Verification table mixes pre-existing baseline with V109 deltas without per-test attribution
**Position**: ?

**Problem**: §Verification states '835/839 full backend pass; 4 failures are pre-existing V108 baseline'. This is consistent with prior arc telemetry but the packet does not name the 4 specific failing tests inline, requiring a reviewer to cross-reference STATE.md ANCHOR-5 to confirm the baseline match. Minor hygiene gap.

**Recommendation**: List the 4 pre-existing failing test ids inline (test_case_export, test_convergence_attestor, test_g1_missing_target_quantity × 2 per STATE.md). Single-line addition; removes a cross-reference dependency.

