# `.governance/` — local audit trails

Local-only audit logs produced by governance hooks. Files in this directory
are gitignored (per-developer log; tracking them would cause conflicts on
concurrent overrides).

## Files

### `codex_cadence_overrides.log` (gitignored)

Append-only log written by `scripts/check_codex_cadence.py` whenever
`CODEX_CADENCE_OVERRIDE=1` is used to bypass the cadence / risk-class
gates. One line per override.

Format (tab-separated):

```
<iso8601_timestamp>\t<short_sha>\t<reason>\t<n_triggers>\t<triggers_joined>
```

Authority: Opus 4.7 round-2 review 2026-04-26 Q6. Round-1 emit was stderr
only ("OVERRIDE active") — round-2 review flagged that as failing the
RETRO-V61-001 governance bar (no durable audit trail).

To inspect:

```bash
cat .governance/codex_cadence_overrides.log
# or, with a grep for a specific reason:
grep "rollback" .governance/codex_cadence_overrides.log
```

## Ownership

This directory is part of the **line A (governance / runtime guard)**
track. Changes to the `.log` format require a doc update here.
