---
spec_id: EXECUTOR_ABSTRACTION_compatibility_spike
title: P2-T0 · Audit Package compatibility spike (P2-T1 prerequisite)
status: SPIKE_COMPLETE_VERDICT_COMPATIBLE_WITH_MANIFEST_TAG (2026-04-26 · authored under 治理收口 anchor session full-execution mandate)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-26
parent_phase: P2 — Executor Abstraction (https://www.notion.so/8832b5d52f3d4c7281255a9ddc394ea6)
parent_task: P2-T0 spike card (https://www.notion.so/34ec68942bed815187a8c8e0a64b4e74)
authoritative_consumers:
  - src/audit_package/manifest.py (SCHEMA_VERSION = 1)
  - src/audit_package/serialize.py (byte-deterministic JSON)
  - src/foam_agent_adapter.py (FoamAgentExecutor.execute)
  - src/task_runner.py (TaskRunner orchestrates ExecutorMode dispatch)
verdict: COMPATIBLE_WITH_MANIFEST_TAG_EXTENSION
notion_sync_status: pending
---

# P2-T0 Compatibility Spike · ExecutorMode ABC vs Audit Package L4 byte-reproducibility

## Question

Can the existing AuditPackage L4 signed-zip schema (DEC-V61-033 era · `src/audit_package/manifest.py SCHEMA_VERSION=1`) absorb the upcoming ExecutorMode ABC (mock / docker-openfoam / hybrid-init / future-remote) without breaking byte-reproducibility?

## Verdict: COMPATIBLE WITH MANIFEST-TAG EXTENSION

P2-T1 (ExecutorMode ABC implementation) is **GO**. Migration plan is NOT required; one additive manifest field tagging closes the gap.

## Findings

### F-1 · Current AuditPackage assumes single execution path

`src/audit_package/manifest.py` builds a manifest from:
- whitelist case metadata (`knowledge/whitelist.yaml`)
- gold-standard metadata (`knowledge/gold_standards/`)
- run inputs (`system/controlDict`, `system/blockMeshDict`, etc.)
- run outputs (`solver_log_tail` + `final_residuals` + `postProcessing/`)
- comparator verdict
- decision-trail (`.planning/decisions/DEC-V61-*`)
- git SHA at manifest-build time
- ISO-8601 UTC timestamp (caller-injectable for determinism)

There is **no field** today indicating which executor produced the run. Every artifact path implicitly assumes Docker-OpenFOAM execution via FoamAgentExecutor. If P2's ExecutorMode ABC adds mock / hybrid-init / future-remote modes, the manifest would silently lose this distinguishing context.

### F-2 · Byte-reproducibility holds across modes IF executor identity is captured

`src/audit_package/serialize.py` enforces:
- All dict keys sort via `json.dumps(..., sort_keys=True)`
- Timestamps caller-injectable (UTC second precision when auto-generated)
- File paths stored as repo-relative POSIX strings
- Git-log lookups use `--format=%H` (no timestamp)
- Decision-trail discovery is deterministic (glob sorted, body-grep matched)

These guarantees are **mode-agnostic** — they describe how the manifest is serialized, not how the underlying artifacts were produced. Two runs of the same case under the same ExecutorMode produce byte-identical manifests today. Two runs of the same case under *different* ExecutorModes would also produce byte-identical manifests today, which is the **bug**: the manifest cannot distinguish them.

### F-3 · Single additive field closes the gap

Add to the manifest top-level:

```yaml
executor:
  mode: <mock | docker-openfoam | hybrid-init | future-remote>
  version: <semver pinned at manifest-build time>
  contract_hash: <sha256 of ExecutorMode ABC's frozen contract spec>
```

Properties:
- **Additive · no schema_version bump required** — readers that don't recognize the field treat it as opaque metadata (per VERSION_COMPATIBILITY_POLICY §5 forward-compat semantics).
- **Byte-deterministic** — `mode` is an enum, `version` is pinned at build time, `contract_hash` is SHA-256 of a versioned spec file.
- **Per-mode reproducibility** — two runs of the same case under the same mode produce byte-identical manifests; two runs under different modes produce manifests that differ ONLY in this field.

### F-4 · HMAC-signed zip remains valid

`src/audit_package/sign.py` signs the entire serialized manifest. The new `executor` field becomes part of the signed payload — no signing-layer changes required. Existing signed bundles remain verifiable since they predate the field; verifiers tolerate missing `executor` field as `mode=docker-openfoam` (the de-facto current mode).

## Migration plan

**Not required**. Single additive field landing under P2-T1 (ExecutorMode ABC implementation):

1. P2-T1 implements `src/executor/base.py::ExecutorMode` enum + `ExecutorAbc` ABC.
2. P2-T1 wraps `FoamAgentExecutor` as `ExecutorMode.DOCKER_OPENFOAM`.
3. P2-T1 adds `executor` field to `manifest.py::build_manifest(...)` accepting `executor: ExecutorAbc` parameter, defaulting to `DOCKER_OPENFOAM` for back-compat.
4. P2-T2 adds `MockExecutor` re-tagged as `ExecutorMode.MOCK`.
5. P2-T3 adds hybrid-init mode. P2-T4 adds future-remote stub.

## Risk-flag candidates for P2-T1 intake

1. **manifest_tag_round_trip_test** — verify `read(write(manifest))` survives the new field.
2. **legacy_signed_zip_compatibility_test** — verify zips signed pre-P2 still verify (treating absent `executor` field as `DOCKER_OPENFOAM`).
3. **executor_contract_hash_pinning** — ensure `contract_hash` is computed from a frozen spec file, not the executor class itself (which would churn with implementation changes).

## Pre-conditions for P2-T1

- [ ] This spec promoted from `SPIKE_COMPLETE` → `Active` in Canonical Docs DB.
- [ ] DEC-V61-074 (proposed) explicitly accepts the additive-field migration plan.
- [ ] P1 tail (DEC-V61-071) ACCEPTED ✓ (already complete)

## Cross-references

- `src/audit_package/manifest.py` (lines 1-30 docstring · SCHEMA_VERSION = 1)
- `src/audit_package/serialize.py` (byte-determinism guarantees)
- `src/audit_package/sign.py` (HMAC signing)
- `src/foam_agent_adapter.py:520` (FoamAgentExecutor class) · `:563` (execute method)
- `src/task_runner.py:170` (TaskRunner orchestrates execute → ResultComparator)
- DEC-V61-033 (Phase 7 Sprint 1 closure · audit-package L4 signed-zip era)
- VERSION_COMPATIBILITY_POLICY v1.0 (forward-compat field semantics)
- EXECUTOR_ABSTRACTION canonical doc (Notion: ecee8d970e8148ec8c714eba8f250110)
