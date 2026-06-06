---
decision_id: V61-229
title: FoamAgentExecutor → DockerOpenFOAMSolverExecutor — honesty-by-naming rename + §10.5.4a gate widening
status: Proposed
accepted_date:
parent_dec:
phase: positioning-optimization (multi-agent role taxonomy arc)
autonomous_governance: true
confidence: high
kogami_opt_in: false
round_cap: 3
codex_review_relay: 86gs gpt-5.4 xhigh (PENDING — relay stalled this session; review queued before any push/merge)
codex_verdict: pending
codex_tool_report_path:
notion_sync_status: N/A (Proposed; syncs only on Accepted)
touches_shared_dec: §10.5.4a audit-required-surface #1 gate (scripts/methodology/sampling_audit.py — governance-rule-change) · EXECUTOR_MODE routing (string "foam_agent" preserved) · byte-reproducibility / signing contract (preserved, guard-tested)
---

# DEC-V61-229 · FoamAgentExecutor → DockerOpenFOAMSolverExecutor (honesty-by-naming)

## Context

The role-taxonomy audit (2026-06-06, see `docs/architecture/AGENT_ROLES.md` +
`.demo/AGENT_SYSTEM_MAP.md`) flagged `FoamAgentExecutor` as the single most
misleading symbol in the codebase: it is a **deterministic Docker+OpenFOAM
subprocess adapter with zero LLM**, but the name "Agent" reads as an autonomous
LLM agent — directly contradicting the advisor-not-driver positioning. Renaming
the class symbol makes the deterministic nature self-evident at every call site.

A read-only rename-readiness audit (5-agent workflow) found the rename is
**byte-reproducibility-safe** (contract_hash = `sha256(spec_file_sha256 | MODE.value
| VERSION)` at `src/executor/base.py:271` — qualname-independent; guard test
`test_hash_invariant_under_subclass_qualname_change` proves it), BUT surfaced a
**governance landmine**: `scripts/methodology/sampling_audit.py:71` hardcoded a regex
`FoamAgentExecutor\.execute\(` as the **§10.5.4a audit-required-surface #1 gate**.
A naive rename would make real call sites read `DockerOpenFOAMSolverExecutor.execute(`,
so the regex would **silently stop matching → the governance gate goes blind while
staying green** (its test feeds a synthetic old-name fixture). This is why the rename
required a DEC (governance-rule-change), not a routine refactor.

## Decision

1. Rename the class symbol `FoamAgentExecutor` → `DockerOpenFOAMSolverExecutor`
   (`src/foam_agent_adapter.py:520`) and update all rename-safe **symbol** references
   (imports / instantiations / isinstance / staticmethod self-calls) across 8 source
   + 2 test files (21 symbol lines).
2. Add a backward-compat module-scope alias `FoamAgentExecutor = DockerOpenFOAMSolverExecutor`
   so legacy imports keep resolving.
3. **Widen** the §10.5.4a gate regex to match BOTH names:
   `(?:FoamAgentExecutor|DockerOpenFOAMSolverExecutor)\s*\.\s*execute\s*\(` —
   the gate label string `1.FoamAgentExecutor_call_sites` is **preserved** (serialized
   report key). Add `test_surface1_catches_renamed_executor_dec_v61_229` proving the
   gate fires on the new name (regression guard against re-blinding).

## Must-preserve (NOT touched — verified)

- EXECUTOR_MODE dispatch string `"foam_agent"` (`task_runner.py:384/388`).
- Module path / filename `src.foam_agent_adapter` / `foam_agent_adapter.py`
  (`_plane_assignment.py:54` PLANE_OF key + `.importlinter` + CI).
- ExecutorMode StrEnum values (`"docker_openfoam"`, `"mock"`, …) — serialized into manifest/contract_hash.
- Serialized f-strings: `phase5_audit_run.py:484`, `phase5_audit_run_foam_agent` source field.
- HMAC signing DOMAIN_TAG.

## Verification

- 511 passed, 2 skipped across guard suite: `test_audit_package/{serialize,sign,manifest}`
  (byte-repro + signing), `test_executor_modes/*` (contract-hash pinning),
  `test_task_runner*`, `test_foam_agent_adapter*` (alias), `test_wizard_drivers`
  (patch targets updated), `test_sampling_audit` (gate, incl. new regression test),
  `tests/architecture` (role-taxonomy fence).
- Import smoke: `DockerOpenFOAMSolverExecutor is FoamAgentExecutor` (alias identity).

## Reversibility / blast radius

- **Reversibility**: high — pure symbol rename + alias; `git revert` restores; alias means
  even a partial revert keeps imports resolving.
- **Blast radius**: medium — 11 files, but no behavior change and no serialized-byte change
  (guard-tested). The only contract touched is the §10.5.4a gate, widened (strictly more
  coverage, never less).

## Status note

Status=Proposed pending Codex review (86gs relay stalled this session). Per project
governance, this governance-rule-change requires Codex APPROVE before push/merge.
Code committed on branch `feat/agent-role-taxonomy-fence` (NOT pushed). On Codex
APPROVE → Status=Accepted + Notion sync.
