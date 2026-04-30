# DEC-V61-102 Codex Review Chain · M-RESCUE Phase 1 + Phase 2

Authored 2026-04-30 by Claude Code Opus 4.7 (1M context).
Owner: cfd-harness-unified workbench.

This report consolidates the Codex GPT-5.4 review chain that cleared
DEC-V61-102 (M-RESCUE Manual Override Foundation) through both
Phase 1 (backend) and Phase 2 (frontend). It maps each round's
findings to the closing commit so the audit trail is reconstructable.

## Phase 1 · backend

| Round | Commit reviewed | Verdict | Findings | Closure commit |
|-------|-----------------|---------|----------|----------------|
| 0 | `8b4e602` | initial implementation | n/a | n/a |
| 1 | `8b4e602` | CHANGES_REQUIRED | P1 (user-override invariant), P2 (transportProperties→physicalProperties path), P3 (history detail merge) | `1818ad2` |
| 2 | `1818ad2` | CHANGES_REQUIRED | HIGH (race lock missing), MEDIUM (preview drift) | `4361ef7` |
| 3 | `4361ef7` | CHANGES_REQUIRED | MEDIUM symlink-escape via `O_NOFOLLOW`, MEDIUM weak race tests, LOW reentrancy claim | `7f3c53d` |
| 4 | `7f3c53d` | CHANGES_REQUIRED | MEDIUM real-route race test bypassed AI lock, MEDIUM non-atomic file+manifest pair | `bf82f05` |
| 5 | `bf82f05` | CHANGES_REQUIRED | MEDIUM per-file (not transactional) atomic, MEDIUM weak race assertions, LOW tempfile leaks | `2dea32a` |
| 6 | `2dea32a` | CHANGES_REQUIRED | MEDIUM partial-write tempfile leak, LOW manifest tempfile leak, LOW underspecified test | `d583107` |
| 7 | `d583107` (= `7677496` after trailer) | **APPROVE_WITH_COMMENTS** ✅ | 0 blocking; comment on pre-existing crash-consistency gap between file commit and manifest commit (out of scope) | merged to origin/main |

### Phase-1 deliverables (verified by Codex)
- `services/case_manifest/`: v2 schema with override tracking, atomic
  read/write via tempfile + os.replace.
- `services/case_manifest/locking.py`: per-case `case_lock` advisory
  flock with `O_NOFOLLOW` symlink-escape protection.
- `services/case_solve/bc_setup.py`: 2-phase transactional commit
  (`_atomic_commit_dicts`) for the 7 LDC dicts and 7 channel dicts.
- `routes/case_dicts.py`: GET/POST surface for raw dict edits with
  etag-protected race detection + symlink_escape mapping to 422.
- `routes/case_inspect.py`: state-preview endpoint surfacing
  `next_action_will_overwrite` warnings.
- 152 tests in the Phase-1 suite passing × 3 stable runs.

## Phase 2 · frontend

| Round | Commit reviewed | Verdict | Findings | Closure commit |
|-------|-----------------|---------|----------|----------------|
| 0 | `323a326` | initial implementation | n/a | n/a |
| 1 | `323a326` | CHANGES_REQUIRED | P1 (broken etag flow), P2 (destructive collapse), P3 (tautological tests) | `0ea4a73` |
| 2 | `0ea4a73` | CHANGES_REQUIRED | MEDIUM cross-step navigation discards unsaved edits | `71a90d7` |
| 3 | `71a90d7` | CHANGES_REQUIRED | MEDIUM case_id guard missing, MEDIUM draft+etag rebase defeats conflict protection | `55e014e` (= `658bf86` after trailer) |
| 4 | `55e014e` | **APPROVE** ✅ | 0 blocking; LOW items (4) narrow empty-write window and (6) silent quota fallback explicitly deferred | merged to origin/main |

### Phase-2 deliverables (verified by Codex)
- `types/case_dicts.ts`: wire shapes mirroring backend schemas.
- `api/client.ts`: `listRawDicts`, `getRawDict`, `postRawDict` with
  structured `ApiError.detail` preservation on 4xx.
- `components/RawDictEditor.tsx`: CodeMirror editor with tab list,
  source/edited_at badges, etag-protected save flow, structured
  error UX (409 refresh, 422 validation, 422 symlink_escape, force-
  bypass), sessionStorage persistence keyed by `caseId + path`,
  `case_id` and `path` guards on populate/persist useEffects, draft
  etag preserved across remount → save surfaces 409 if server moved on.
- `pages/workbench/.../Step3SetupBC.tsx`: collapsible "Advanced ·
  edit raw dicts" section, lazy-mount on first open, sticky after
  open so collapse doesn't unmount.
- 13 RawDictEditor unit tests (151 total frontend tests passing).

## Codex coverage matrix

| Concern class | Phase 1 | Phase 2 |
|---------------|---------|---------|
| Race condition / atomicity | rounds 2, 4, 5, 6 | rounds 1, 2, 3 |
| Security (symlink, XSS) | round 3 | round 0, 1 |
| Test rigor (regression-detection) | rounds 5, 6 | rounds 1, 2, 3 |
| API contract correctness | round 3 | rounds 0, 3 |
| Cross-state consistency | round 4, 5 | rounds 2, 3 |

## Account hygiene

All Codex calls during this chain were verified against real Plus
accounts (paauhtgaiah@gmail.com, score 80% → 53% over the chain) per
RETRO-V61-001 + the user's "drain Plus before Pro" directive
(memory entry `feedback_no_pro_when_plus_available`). The Pro
account `ramaiamandhabdbs@gmail.com` was never engaged.

The `mahbubaamyrss@gmail.com` account was switched OFF at the start
of the chain after the user identified that cx-auto's JWT-based tier
detection had misclassified it as Plus when it was actually Pro
(memory: `reference_codex_account_tiers.md`).
