---
decision_id: DEC-V61-203
title: Frontend tsc -b pre-commit build gate (governance-rule-change)
status: Accepted
parent_dec: DEC-V61-133 (v2.3 B+ governance baseline) · trigger: M3.11 red-build slip
phase: M3.13 (continuation session 2026-05-25 · workbench-dynamic-guided arc)
notion_sync_status: synced 2026-05-25 (https://www.notion.so/36bc68942bed8159a193de0b45de7ce5)
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

- **CI mirror — ALREADY SATISFIED (verified M3.14, 2026-05-25).** The
  `frontend-build` job in `.github/workflows/ci.yml` (lines 155-178) already
  runs `npm run typecheck` (`tsc --noEmit`) **and** `npm run build`
  (`tsc -b && vite build`) on `push: [main]` + `pull_request: [main,
  codex/stack-*]`. The M3.11 error surfaces in both `tsc --noEmit` and `tsc -b`,
  so CI's typecheck step would have caught it. **No CI change made** — adding a
  redundant tsc step would be pointless duplication. The real root cause of the
  M3.11 slip was NOT a missing CI check but that the branch sat ~87 commits
  ahead and **unpushed**, so CI never ran. The M3.13 local pre-commit gate is
  precisely the layer that closes that gap (catches pre-commit, before push).
- **Residual (branch-protection, NOT a code change — needs GitHub admin):**
  `frontend-build` runs post-push on direct pushes to `main`, so a `--no-verify`
  + direct-push of a red build would land before CI goes red. Making
  `frontend-build` a **required, merge-blocking status check** (+ requiring PRs
  into `main`) is a GitHub branch-protection setting, not a yaml edit. Flagged
  for the user to configure if desired.
