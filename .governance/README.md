# `.governance/` — audit trails for the cadence hook

Files written or referenced by `scripts/check_codex_cadence.py`. The two
log files have different lifecycles — one is local-only and per-developer
(runtime audit), the other is git-tracked and one-shot (historical
backfill).

## Files

### `codex_cadence_overrides.log` (gitignored, JSONL)

Append-only log written **at hook runtime** by every `CODEX_CADENCE_OVERRIDE=1`
push. One JSON object per line.

**Format** (round-3 F8 migration: was tab-separated 5-field, now JSONL):

```jsonl
{"ts": "<iso8601_utc>", "sha": "<short_sha>", "reason": "<text>", "n_triggers": <int>, "triggers": [<strings>]}
```

**Timestamp convention**: ISO 8601, **UTC** (the `+00:00` suffix is
explicit). Don't reinterpret as local time during forensic review.

**Why JSONL, not TSV**: round-3 finding F8 — TSV broke if `Override-reason:`
text contained a literal `\t` (e.g. pasted from a spreadsheet). JSONL
escapes tabs / quotes / newlines automatically and is jq-friendly.

**Why gitignored**: per-developer log. Concurrent overrides on different
machines would conflict if tracked. Audit aggregation is post-hoc (e.g.
quarterly retro reads each contributor's log).

To inspect:
```bash
jq -c '.' .governance/codex_cadence_overrides.log
# or filter by reason:
jq 'select(.reason | contains("rollback"))' .governance/codex_cadence_overrides.log
```

### `backfill_log.jsonl` (git-tracked, one-shot)

Historical entries reconstructed for overrides that happened **before**
the audit-log mechanism existed. Round-3 F18 closure: PR-1 (`b8bc4a7`)
silent override is the only historical entry today.

This file is **append-only** but written manually, not by the hook. New
entries should only be added if a historical audit gap is discovered
during retro review. Format identical to `codex_cadence_overrides.log`
plus a `"backfill": true` field and a `"round": "<which round flagged>"`.

## CI policy (round-3 F10)

**CI/runner contexts must NEVER override the cadence hook.**

`scripts/check_codex_cadence.py` detects `CI=true` (the de-facto standard
across GitHub Actions / GitLab CI / CircleCI / Travis / Buildkite /
Jenkins pipelines that set this env var) and **refuses** the override
even if `CODEX_CADENCE_OVERRIDE=1` is set with a valid reason.

**Reason**: CI runners are ephemeral. Anything they write to
`.governance/codex_cadence_overrides.log` is discarded with the runner.
If CI could override, the audit trail would be silently broken in the
exact context where automated bypass is most dangerous (anyone with
write access to a workflow could insert `CODEX_CADENCE_OVERRIDE=1
git push` and leave no trace).

**Required path for CI**: land a `Codex-verified: APPROVE|...` trailer
on HEAD before the CI push step runs. Risk-class gate honors that
trailer (round-2 Q14 design).

## Authority chain

- Round-1 (2026-04-25): cadence floor (count-based, stderr-only emit)
- Round-2 Q6 (2026-04-25): persistent TSV audit log + Override-reason
  requirement (`scripts/check_codex_cadence.py` + this README v1)
- Round-3 (2026-04-26): TSV → JSONL (F8), CI policy (F10),
  backfill log (F18), whitespace-strict reason check (F11),
  modification-aware risk detection (F5)

## Ownership

Files in this directory are **line A (governance / runtime guard)**.
Format changes require a doc update here AND a corresponding test
in `tests/test_codex_cadence_hook.py`.
