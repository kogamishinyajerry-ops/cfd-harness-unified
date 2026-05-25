---
decision_id: DEC-V61-203
title: Frontend tsc -b pre-commit build gate (governance-rule-change)
status: Accepted
parent_dec: DEC-V61-133 (v2.3 B+ governance baseline) · trigger: M3.11 red-build slip
phase: M3.13 (continuation session 2026-05-25 · workbench-dynamic-guided arc)
notion_sync_status: pending (session-end batch · per v2.3 Accepted-only)
autonomous_governance: false
confidence: high
date: 2026-05-25
ratified_by: user ("A", 2026-05-25 — explicit selection of the proposed gate)
---

# DEC-V61-203 · Frontend `tsc -b` pre-commit build gate

## TL;DR

Add a `pre-commit` hook that runs `tsc -b` for `ui/frontend` and **blocks the
commit on a typecheck failure**, scoped to commits that touch
`ui/frontend/**/*.{ts,tsx}`. Closes the gap that let a prior session commit a
RED frontend build to HEAD undetected.

## Why (governance-rule-change → full DEC + user ratification)

This changes the commit gate for **all** future frontend work (broad workflow
blast radius), so per v2.3 (`DEC-V61-133`) it is a governance-rule-change
warranting a full DEC, not a spike-class commit. It was **not** done
autonomously; surfaced as a recommendation in the M3.11/M3.12 retros and
ratified by the user ("A") on 2026-05-25.

**Trigger evidence**: the prior session closed "7 milestones" (HEAD `2648adf`)
while `tsc -b` was RED — `TopBarV4.tsx:67` passed an optional `activeStep`
(`V4PipelineStepId | undefined`) to a hook requiring it defined. `npm run build`
(`tsc -b && vite build`) would have failed. No gate caught it; it surfaced a
full session later and was fixed in M3.11 (`06448b1`). The existing pre-commit
hooks gate Python (import-linter), corpus-drift, and AI-path mutations — but
**nothing gated the frontend build**.

## Scope / mechanics

- Hook id `frontend-typecheck` in `.pre-commit-config.yaml`, `stages: [pre-commit]`.
- `files: ^ui/frontend/.*\.(ts|tsx)$` — fires only when frontend TS/TSX is
  staged (no tax on backend/docs commits).
- `pass_filenames: false` — `tsc -b` is a project-graph build, not a per-file
  check; it always typechecks the whole frontend project (incremental via
  `.tsbuildinfo`, so repeat runs are fast).
- Entry `scripts/governance/check_frontend_typecheck.sh`: resolves repo root via
  git, runs the **local** `ui/frontend/node_modules/.bin/tsc -b`, propagates its
  exit code.
- **Fresh-checkout safety**: if local `tsc` is absent (no `npm install`), the
  hook WARNS and exits 0 — it must not block on a missing toolchain, only on a
  real code defect.

## Why pre-commit (not pre-push)

The observed failure mode was a red build persisting across a whole session of
**local** commits (84 ahead of origin, rarely pushed). A pre-push gate would not
fire until a push that may not happen for days; a pre-commit gate makes every
red frontend commit impossible. The ~3-5 s incremental `tsc -b` cost is accepted
in exchange for a guaranteed-green frontend HEAD.

## Override

Intentional bypass is audited via shell history:
`SKIP=frontend-typecheck git commit ...` or `git commit --no-verify`.

## Verification (this DEC)

- Positive: `pre-commit run frontend-typecheck --files <clean .ts>` → **Passed**.
- Negative: throwaway `src/__m313_gate_probe.ts` with `const n: number = "x"`
  → hook **Failed** (TS2322 + override hint); probe removed → **Passed** again
  (incremental cache clean).
- Baseline `tsc -b` is currently GREEN (M3.11 unblocked it), so the gate does not
  block existing work.

## Rollback

Delete the `frontend-typecheck` hook block from `.pre-commit-config.yaml` (and
optionally the script). No code depends on it; removal is a one-commit revert.

## Four-question gate

LLM-offline (build/type tooling) · artifacts canonical (n/a) · TrustGate (n/a) ·
AI advisory-only (no AI). All Y / n-a.

## Follow-up

Mirror the same gate in CI (`.github/workflows/ci.yml`) so a `--no-verify`
bypass can't reach the remote default branch unchecked. Out of scope here
(local gate first); noted for the next governance touch.
