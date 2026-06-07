# Contributing to cfd-harness-unified

Thanks for your interest in contributing. This project is an AI-CFD validation
and audit workbench, so contributions are reviewed for both software correctness
and evidence integrity.

## Project principles

1. **Evidence beats polish.** A visually convincing report must not hide missing,
   stale, or invalid solver evidence.
2. **No PASS without physics.** PASS/WARN/FAIL claims must be backed by gold
   standards, tolerance bands, solver artifacts, and explicit gates.
3. **Demo paths and evidence paths stay separate.** Mocked or educational flows
   should be clearly labeled and must not be promoted to validated claims.
4. **Changes should be reviewable.** Prefer small PRs with a clear scope, test
   plan, and rollback path.

## Before opening a PR

Please include:

- A short summary of the change and why it matters.
- The affected path: demo UI, backend API, solver adapter, gold standard,
  comparator/gate, report/audit package, documentation, or tests.
- The evidence level: mocked/demo-only, replayed artifact, real OpenFOAM run,
  analytical reference, or benchmark-backed validation.
- The commands you ran, including Python/backend/frontend test commands.
- Any known limitations or honest gaps.

## Suggested local checks

```bash
# Core Python suite
.venv/bin/pytest

# UI backend
.venv/bin/pytest ui/backend/tests -q

# UI frontend
(cd ui/frontend && npm run typecheck && npm run build)
```

Run narrower tests when your change is scoped, but state that clearly in the PR.

## PR review expectations

Review focuses on:

- Regression safety and clear failure behavior.
- Correct use of gold standards and tolerance bands.
- No tautological validation: QoIs should come from solver/output evidence, not
  from the reference value they are being compared against.
- Honest labeling of mocked, ingested, replayed, and real-solver evidence.
- Dependency and security impact.
- Documentation updates when user-facing behavior or claim boundaries change.

## Reporting issues

When filing a bug, include:

- The case or route affected.
- Steps to reproduce.
- Expected vs. observed behavior.
- Relevant logs, generated reports, or solver artifacts if available.
- Whether the issue affects demo output, evidence gates, or validation claims.

## Maintainer workflow

Codex or other code-review agents may be used for PR review, regression triage,
test-failure diagnosis, dependency/security review, and release-readiness checks.
Agent output is advisory: maintainers still own merges, claim boundaries, and
release decisions.
