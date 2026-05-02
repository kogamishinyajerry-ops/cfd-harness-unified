# Codex Review Chain · DEC-V61-108 Phase B (R1 → R3)

**DEC**: DEC-V61-108 Phase B — Step 3 per-patch BC classification override panel (frontend wiring)
**Risk-tier triggers** (per RETRO-V61-001):
  - Multi-file frontend change (4 source + 1 test = 5 TS/TSX files)
  - New API contract surface (3 client methods, new request body type)
  - Step3SetupBC modification
  - Async state-sync semantics on the workbench hot path
**Relay backend**: 86gamestore (`~/.codex-relay`, gpt-5.4, xhigh effort)
**Outcome**: APPROVE on R3 (`f6d40e1`) after 3 rounds

## Why this many rounds

R1 found 4 valid issues — 2 HIGH (race, caseId-stale), 1 MED (test gaps), 1 LOW (load-error UX). My closure for R1 introduced a subtler bug: a single `stateGenRef` conflated case-invalidation with mutation ordering, which R2 caught (an older save that succeeded after a newer save FAILED was dropped; saves stranded in-flight face-index GETs). R3 verified the dual-token split (caseGen vs saveSeq/committedSeq) closes both without regressing R1's protections.

## Round-by-round

### R1 — CHANGES_REQUIRED · 4 findings (initial commit `4f1dd6c`)
- **P1 #1** (HIGH): `handleChange` race — out-of-order resolves can regress UI to stale snapshot.
- **P1 #2** (HIGH): `caseId` swap in place keeps stale state — engineer can submit case-A patches against case B.
- **P2** (MED): tests don't cover reversed-resolution or caseId-mid-flight.
- **P3** (LOW): load-error path collapses `ApiError.detail` into generic message.

### R1 closure (`c7cb785`)
- Single `stateGenRef` monotonic counter, bumped on every mutation; `isStale()` guards every setState.
- `cancelledRef` for unmount; caseId effect resets all case-scoped state + bumps gen.
- `<PatchClassificationPanel key={caseId} ... />` at mount site for full-remount on caseId swap (defense in depth).
- Extracted `formatApiErrorDetail(e)` and used in BOTH load + handleChange catch paths.
- Added 2 vitest cases: "rejects out-of-order PUT resolutions" + "drops a stale GET after caseId changes".

### R2 — CHANGES_REQUIRED · 2 findings
- **P1** (HIGH): single token drops successful older save when newer save FAILS — `committedSeq` advances on dispatch but newer save never won.
- **P3** (HIGH): same token guards `getFaceIndex` — any save in flight strands picked-face highlight.

### R2 closure (`f6d40e1`)
- Split into 3 refs:
  - `caseGenRef`: bumped only on caseId change. Used by initial-GET load + getFaceIndex.
  - `saveSeqRef`: monotonic counter; bumped on each save dispatch to mint mySeq.
  - `committedSeqRef`: highest save-seq actually applied to state. Save commits iff (caseGen unchanged) AND (mySeq > committedSeq). Failed saves leave `committedSeq` untouched.
- Initial-GET load also gets `committedSeqRef > 0` guard so a slow GET can't clobber a save's authoritative full-state response.
- 2 new regression tests: "commits an older save's response after a newer save fails" + "preserves faceIndex when a save lands before it resolves".

### R3 — APPROVE · 0 findings
> "`caseGenRef` now gates only case-scoped work (initial GET and `getFaceIndex`), while `saveSeqRef`/`committedSeqRef` ensure an older save is dropped only if a newer save has actually committed... The `committedSeqRef > 0` initial-GET guard is correctly scoped to committed saves, not merely issued ones. The new tests are genuinely async, not synchronously resolved."

## Verification preserved across the chain
- 11 PatchClassificationPanel tests + 96 broader shell tests = **107 → 109 shell tests, all green**
- 165/165 full frontend vitest passing on initial commit
- `tsc --noEmit` clean on every commit

## Counter

Per RETRO-V61-001 telemetry: each Codex round increments `autonomous_governance_counter_v61` by 1. R1–R3 = 3 increments on DEC-V61-108 Phase B. Combined with Phase A's 11 (R1–R11) = 14 ticks across the V108 arc. Adding V107.5's 9 (R12–R20) = **23 ticks total since the last retro boundary**. Eligible for arc-size retro.

## Honest scope

R1 surfaced 4 real defects in legitimate territory. R2's 2 follow-ons were a genuine emergent bug from R1's closure — collapsing two distinct concerns (case invalidation, mutation ordering) into a single token broke them both in opposite directions: case-scoped work like face-index got false-positively invalidated by saves, while real save-vs-save ordering got false-positively driven by issuance order rather than commit order. R3 verified the dual-token split is the correct decomposition.

## Future work

The patch_classification panel is now production-quality from a concurrency standpoint. Phase B is closed at the data-binding layer.

Open opportunities (not blocked by this DEC):
- **Bulk operations**: the panel currently fires one PUT per dropdown change. A "set all unannotated to no_slip_wall" bulk action would need a new backend route or a sequenced client batch.
- **Conflict surfacing**: if two browsers PUT the same patch concurrently, the second overwrites silently. The face-annotations endpoint uses `if_match_revision` for this — `patch-classification` could adopt the same pattern in a future DEC if multi-user editing becomes a real workflow.
- **Picked-face → patch reverse highlight**: clicking a row in the panel could highlight the corresponding patch in the viewport (reverse direction). Requires plumbing through FacePickContext + viewport selection state.
