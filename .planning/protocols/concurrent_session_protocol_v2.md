# Concurrent Session Protocol v2

> Drafted under audit amendment A5 (DEC-V61-080 RATIFY_WITH_AMENDMENTS, 2026-04-26)
> Applies to any future Claude Code Session B (or other concurrent / parallel session)
> running alongside an active main-line session. NOT yet ratified by Opus Gate;
> binding only on Session B v2 unless promoted by separate DEC.

## Why this exists

GOV-1 v0.5 ran as Session B concurrent with Session A's PC-2/3/4 + DEC-V61-073
work. The independent audit (RATIFY_WITH_AMENDMENTS, 2026-04-26) found two real
coordination failures even though path isolation held:

1. **HEAD baseline drift** — user's stated baseline was `8e19555`; actual main
   HEAD at session open was `55f2642` (Session A had merged 7 commits between
   prompt-write and session-open)
2. **Dirty working-tree handoff** — Session B inherited `reports/*` modifications
   + `.planning/strategic/` untracked files from Session A's in-progress work

This protocol formalizes coordination primitives so v2 won't repeat these.

## Protocol primitives

### P-CSP-1 · HEAD baseline reconfirmation at handoff

Before any Session B v2 commit, both sessions must confirm baselines:

**Session A (or main-line session) reports**:
- Last commit SHA: `git log -1 --pretty=%H`
- Branch state: `git rev-parse --abbrev-ref HEAD`
- Any unmerged work in flight: `git status --short` (paths only, no content)

**Session B (or parallel session) confirms before opening**:
- Checked-out HEAD matches Session A's reported SHA: `git log -1 --pretty=%H`
- If mismatch: STOP, reconcile via `git fetch + git checkout <reported_sha>` or
  by explicit user authorization to proceed at a different baseline

This eliminates the "user prompt cites HEAD X but actual HEAD is Y" pattern
that occurred in v0.5. Catch the drift at session open, not at audit close.

### P-CSP-2 · Dirty working-tree enumeration in inherited context

Session B's "Inherited Context" property in the Sessions DB MUST list:

- Each modified file (`git status --short -uno`) with file path AND size
- Each untracked file (`git status --short --untracked-files=all`) with path AND size
- Whether each will be touched (write) or ignored (read-only) by Session B

Example for v0.5 (retroactive):
```
Modified:
 M reports/deep_acceptance/contract_status_dashboard.html        (12 KB)  IGNORE — Session A
 M reports/deep_acceptance/contract_status_dashboard_manifest.json (4 KB) IGNORE — Session A
 M reports/deep_acceptance/visual_acceptance_report.html         (8 KB)  IGNORE — Session A
 M reports/deep_acceptance/visual_acceptance_report_manifest.json (4 KB) IGNORE — Session A
 M reports/differential_heated_cavity/report.md                  (2 KB)  IGNORE — Session A
Untracked:
 ?? .planning/strategic/                                          (dir)   IGNORE — Session A
```

This makes the implicit "I won't touch these" promise explicit and
auditable. If Session B later DOES touch one of these paths, the audit
trail catches it.

### P-CSP-3 · Mid-session HEAD-drift check at ~50% mark

At approximately the midpoint of expected Session B duration (estimated
by commit count or by elapsed time), Session B runs a HEAD-drift check:

```bash
git fetch origin main 2>/dev/null
LOCAL=$(git rev-parse main)
REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "$LOCAL")
if [ "$LOCAL" != "$REMOTE" ]; then
  echo "HEAD drift detected: local=$LOCAL remote=$REMOTE"
  echo "Recommend: git pull --rebase, re-verify hard boundaries vs new baseline"
fi
```

If drift is detected mid-session, Session B should:
1. Halt at next clean checkpoint (commit boundary)
2. Re-verify hard boundaries against the new baseline (e.g., did Session A
   merge changes to a path that Session B was about to write?)
3. Decide: rebase + continue, or escalate to user for guidance

### P-CSP-4 · Path-isolation contract in DEC frontmatter

Every Session B DEC must declare its write paths explicitly in frontmatter:

```yaml
session_b_write_paths:
  - docs/case_documentation/**     # primary deliverable
  - .planning/decisions/2026-04-26_v61_080_*.md  # this DEC
  - .planning/audit_evidence/**    # audit-amendment artifacts (post-audit)
  - .planning/protocols/**         # this protocol doc (post-audit A5)
session_b_read_only_paths:
  - knowledge/**
  - src/cfd_harness/trust_core/**
  - docs/specs/EXECUTOR_ABSTRACTION.md
  - docs/methodology/**
  - scripts/methodology/sampling_audit.py
session_b_inherited_dirty_state:
  - reports/deep_acceptance/                        # Session A in-progress
  - reports/differential_heated_cavity/report.md    # Session A in-progress
  - .planning/strategic/                            # Session A untracked
```

This formalizes what was implicit in v0.5 (path isolation lived only in
prose) and gives audit a checkable invariant.

### P-CSP-5 · Auditor evidence bundle (constitutional finding 1 from audit)

For independent-context Pivot Charter §7 audits where the repo is private,
attach to the Notion DEC page (or commit to `.planning/audit_evidence/`):

- A `git log --stat <baseline>..<head>` snapshot for each declared
  read-only path (must show empty)
- File hashes (SHA256) for canonical artifacts (whitelist.yaml, gold YAMLs,
  trust_core/__init__.py, etc.) at session open AND session close (must
  match)

This prevents independence-of-context audits from degrading to
"control-plane only" when the repo is private. The audit can verify
boundaries from the Notion side without needing repo access.

## Adoption status

- **v2 (this doc)**: drafted 2026-04-26 under audit amendment A5
- **v2.1**: pending Opus Gate ratification (or CFDJerry implicit acceptance
  via Session B v2 launch using these primitives)
- **Promotion to all parallel sessions**: requires separate DEC + Pivot
  Charter appendix update

## What this protocol does NOT change

- Hard-boundary discipline (still enumerated per-DEC)
- Git commit hygiene (still per-amendment atomic commits)
- Notion sync workflow (still via `notion-sync-cfd-harness` skill)
- Session A's main-line authority (still authoritative for shared paths)

This is purely a coordination layer on top of existing primitives.
