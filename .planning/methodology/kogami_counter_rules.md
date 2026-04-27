# Kogami-Claude-cosplay Counter Rules · v6.2

> Authoritative source for **how Kogami review affects** `autonomous_governance_counter_v61`.
> Established by **DEC-V61-087** (Accepted 2026-04-27) §5.
> Compatible with **RETRO-V61-001** counter rules (verified by Q4 dry-run).

## Core invariants (per DEC §5)

1. `autonomous_governance_counter_v61` continues to be defined by RETRO-V61-001
   (counts DECs with `autonomous_governance: true`).
2. Kogami does **NOT introduce** a new counter or counting path.
3. Kogami is a **gate** (necessary, not sufficient) on existing counter paths.
4. Historical DECs (V61-001..087) are NOT retroactively required to have
   `kogami_review_status` frontmatter. Kogami applies from V61-088 forward.

## §5.1 Truth table (5 artifact types)

Per DEC §5.1, exactly these 5 artifact types exist in the governance system:

| # | Artifact type | `autonomous_governance` field | counter increment | Appears in retro counter table | Required frontmatter |
|---|---|---|---|---|---|
| 1 | Normal DEC (`true`) | `true` | **+1** | YES | `kogami_review_status: APPROVED <date> <review_path>` (post-V61-088 only) |
| 2 | External-gate DEC (`false`) | `false` | **N/A** | YES (with N/A annotation per V61-006/011 precedent) | `kogami_review_status` field optional (only required if Kogami applicable) |
| 3 | Kogami review artifact | (no such field; not a DEC) | **+0** | NO (advisory chain) | `kogami_review_metadata: {prompt_sha256, trigger, ...}` |
| 4 | Kogami spawned sub-agent review | (no such field) | **+0** | NO | `spawned_by: kogami_review_<id>; depth: 1` |
| 5 | RETRO file | (no such field) | **+0** | N/A (RETRO IS the counter table container) | existing: `retro_id`, `trigger` |

## §5.2 N/A semantic boundary (clarification per Codex v3 R1 P1-2)

Two distinct uses of "N/A" in the counter table — they are NOT the same:

| Term | Meaning | Examples |
|---|---|---|
| External-gate N/A | DEC with `autonomous_governance: false` — counter SKIPPED for this DEC because user/external review is the gate | V61-006 (autonomous_governance: false), V61-011, V61-085 |
| Advisory-chain +0 | Artifact is NOT a DEC; it never enters counter table | Kogami review file, Kogami spawned sub-agent file, RETRO file |

When listing the counter table for an arc, use:
- `+1` for advance
- `N/A` for external-gate DECs (still listed for transparency)
- (do not list) advisory-chain artifacts (they don't appear in the counter table at all)

## §5.3 Frontmatter conventions

### For DECs (post-V61-088, when Kogami is applicable)

Add to DEC frontmatter:

```yaml
kogami_review_status: APPROVED 2026-MM-DD .planning/reviews/kogami/<topic>_<date>/review.md
# OR
kogami_review_status: APPROVED_WITH_COMMENTS 2026-MM-DD <path> · 3 P2 comments addressed inline
# OR
kogami_review_status: CHANGES_REQUIRED 2026-MM-DD <path> · DEC blocked at Status=Proposed pending revision
# OR (if Kogami not applicable per §4.2 must-NOT triggers)
kogami_review_status: NOT_APPLICABLE · routine commit (per kogami_triggers.md §Must NOT trigger)
```

### For Kogami review artifacts

Each `review.json` is paired with `invoke_meta.json` containing:
```json
{
  "wrapper_version": "1.0",
  "attempt": 1,
  "schema_ok": true,
  "prompt_sha256": "...",
  "empty_cwd": "/tmp/strategic_brief_cwd_...",
  "trigger": "phase_close_p3_t2",
  "artifact": "/path/to/reviewed_artifact.md",
  "invoked_at_utc": "2026-MM-DDTHH:MM:SSZ",
  "envelope": { ... claude -p envelope metadata ... }
}
```

`prompt_sha256` is the canonical reproducibility token (hashed prompt.txt, see DEC §3.3).

## §5.4 Kogami CHANGES_REQUIRED blocking rule

If Kogami returns `CHANGES_REQUIRED` on a DEC:
- DEC **cannot** advance from `Proposed` to `Accepted`
- author must address findings (patch DEC), then re-trigger Kogami
- Codex APPROVE alone is **not sufficient** to bypass Kogami CHANGES_REQUIRED
- Same direction holds: Kogami APPROVE alone does NOT bypass Codex CHANGES_REQUIRED

This is the **double-necessary gate** (per DEC §1, both must APPROVE for merge).

## §5.5 INCONCLUSIVE handling

If Kogami returns `INCONCLUSIVE` (schema validation failed twice OR Kogami self-aborts):
- Does NOT block merge (does not count as CHANGES_REQUIRED)
- DOES require an entry in the next RETRO under `kogami_inconclusive_log`
- counter advance proceeds normally if other gates pass
- After 3 INCONCLUSIVE outcomes within counter ≤ 5, mandatory mini-retro on Kogami reliability

Rationale: INCONCLUSIVE is a wrapper/subprocess failure mode (schema issue, timeout,
crash). It indicates Kogami didn't have a chance to judge — which is different from
Kogami judging negatively. We don't want a bug in the wrapper to block merges, but we
DO want frequent INCONCLUSIVE events to trigger investigation.

## §5.6 Compatibility verification (Q4 dry-run)

Per DEC §Q4 + Acceptance Criteria, the truth table above must NOT cause counter
drift on historical DECs.

Q4 dry-run tested 5 sample DECs:
- V61-006 (autonomous_governance: false, external-gate gold) → row 2 → counter unchanged ✓
- V61-011 (autonomous_governance: false, Q-2 R-A relabel) → row 2 → counter unchanged ✓
- V61-074 (autonomous_governance: true, P2-T1 ExecutorMode) → row 1 → counter +1 ✓
- V61-075 (autonomous_governance: true, P2-T2 substantialization) → row 1 → counter +1 ✓
- V61-086 (autonomous_governance: true, GOV-1 v0.7 docs) → row 1 → counter +1 ✓

All match STATE.md historical record (counter advanced exactly as shown). See
`scripts/governance/verify_q4_counter_truth_table.py` for the verifier.

## §5.7 RETRO counter table format (post-V61-088)

When a RETRO documents an arc that includes Kogami-reviewed DECs, the counter
table gets a new column:

| DEC | Title | autonomous_governance | counter | Codex rounds | Kogami review | Self-pass-rate |
|---|---|---|---|---|---|---|
| V61-088 | (example) | true | +1 | 1 R1 APPROVE | APPROVED 2026-MM-DD | 0.85 → APPROVED |
| V61-089 | (example external) | false | N/A | (n/a) | NOT_APPLICABLE | (n/a) |

The Kogami review column lists `APPROVED` / `APPROVED_WITH_COMMENTS` /
`CHANGES_REQUIRED` / `INCONCLUSIVE` / `NOT_APPLICABLE` per §5.3.

Historical DECs (V61-001..087) do NOT need this column backfilled. New columns
apply going forward only.
