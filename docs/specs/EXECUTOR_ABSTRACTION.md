---
spec_id: EXECUTOR_ABSTRACTION
title: Executor Abstraction Contract (v0.2 · local canonical mirror)
version: 0.2
status: ACTIVE_PROVISIONAL (2026-04-26 · pending PC-2 Codex APPROVE under DEC-V61-073 · promotes to ACTIVE on DEC-V61-073 flip)
authored_by: Claude Code Opus 4.7 (1M context · landing DEC-V61-073 PC-2)
authored_at: 2026-04-26
parent_phase: P2 — Executor Abstraction
parent_dec: DEC-V61-073
parent_audit: Notion @Opus 4.7 independent audit DEC-AUDIT-2026-04-26 (H4 finding)
notion_canonical: ecee8d970e8148ec8c714eba8f250110
notion_sync_status: pending
authoritative_consumers:
  - src/audit_package/manifest.py (SCHEMA_VERSION = 1; +`executor` field per §3)
  - src/audit_package/serialize.py (byte-determinism — mode-agnostic)
  - src/audit_package/sign.py (HMAC signing — covers `executor` field)
  - src/foam_agent_adapter.py (FoamAgentExecutor wrapped as DOCKER_OPENFOAM mode)
  - src/task_runner.py (TaskRunner dispatch on ExecutorMode)
  - src/metrics/** (TrustGate routing per §6 — read-only consumer of this spec; Plane.EVALUATION per ADR-001 line 73)
ratification_pre_conditions_for_p2_t1:
  - PC-1: DEC-V61-073 (this DEC) Status=Accepted
  - PC-2: this spec §5 + §6 landed + Codex APPROVE
  - PC-3: §10.5 token cap ≤100k landed + budget-cap unit test green
  - PC-4: §10.5.4a 7-surface list landed + smoke audit green
---

# Executor Abstraction Contract · v0.2

> **Why this doc exists**: P2 introduces an `ExecutorMode` ABC so the
> harness can dispatch a run through `mock`, `docker-openfoam`,
> `hybrid-init` (surrogate warm-start + OpenFOAM solve), or
> `future-remote` (HPC stub). DEC-V61-073 H4 (independent Opus 4.7 audit
> 2026-04-26) flagged that the original v0.1 doc claimed "contract
> preserved" for hybrid-init mode without formalizing what the contract
> *is*. This v0.2 fills that gap (§5) and introduces TrustGate executor-
> aware routing (§6).

## §1 · Scope and authority

This spec is the **repo-local canonical mirror** of the Notion
EXECUTOR_ABSTRACTION canonical doc (page id
`ecee8d970e8148ec8c714eba8f250110`). On disagreement, **the file you
are reading wins** — the Notion page mirrors this file post-merge, not
the other way around (per `~/.claude/MODEL_ROUTING.md` "git is the
verifiable code state + frontmatter truth; Notion is the human-readable
decision portal").

P2-T1 (DEC-V61-074, ExecutorMode ABC + 4-mode skeleton) is blocked
until §5 + §6 land here AND Codex APPROVES this v0.2.

## §2 · `ExecutorMode` enum

```python
class ExecutorMode(StrEnum):
    MOCK            = "mock"             # P2-T3 · re-tag of existing MockExecutor
    DOCKER_OPENFOAM = "docker_openfoam"  # P2-T1/T2 · wraps FoamAgentExecutor
    HYBRID_INIT     = "hybrid_init"      # P2-T4 · surrogate warm-start + OpenFOAM solve
    FUTURE_REMOTE   = "future_remote"    # P2-T5 · HPC stub, doc-only this milestone
```

Each mode owns:

| Field | Semantics |
| --- | --- |
| `mode` | The enum value above. |
| `version` | Semver pinned at manifest-build time. |
| `contract_hash` | SHA-256 of the frozen mode-contract spec file (this file's git SHA at the relevant section anchor). |

Reference: `EXECUTOR_ABSTRACTION_compatibility_spike.md` F-3.

## §3 · Manifest tagging (additive · no schema bump)

Per the P2-T0 compatibility spike (verdict
`COMPATIBLE_WITH_MANIFEST_TAG_EXTENSION`), AuditPackage manifests gain
a single additive top-level field:

```yaml
executor:
  mode: <mock | docker_openfoam | hybrid_init | future_remote>
  version: <semver>
  contract_hash: <sha256>
```

Properties (preserved from v0.1):

- **Additive** — readers that don't recognize the field treat it as
  opaque metadata (`VERSION_COMPATIBILITY_POLICY` §5 forward-compat).
- **Byte-deterministic** — enum + pinned semver + frozen spec hash.
- **Per-mode reproducibility** — two runs of the same case under the
  same mode produce byte-identical manifests; two runs under
  different modes differ ONLY in this field.
- **Legacy compatibility** — zips signed pre-P2 verify with `executor`
  field absent, treated as `mode = docker_openfoam`.

## §4 · Per-mode contract surface

| Mode | Produces canonical artifacts? | Subject to TrustGate full triad? | Notes |
| --- | --- | --- | --- |
| `mock` | No (synthetic artifacts) | No — ceiling `WARN` (note `mock_executor_no_truth_source`) | Used for plumbing tests + UI demos. Never "PASS". |
| `docker_openfoam` | Yes — direct OpenFOAM solve | Yes — full triad `PASS / WARN / FAIL` | Reference truth source. |
| `hybrid_init` | Yes — final OpenFOAM solve outputs (initializer artifacts excluded) | Yes — defers to OpenFOAM artifact (§5) | Surrogate is non-canonical input. |
| `future_remote` | (stub only this milestone) | (n/a — stub) | DEC-V61-078 sets the contract once a real backend lands. |

The above table is normative for §6 TrustGate routing. Modes added
post-v0.2 require an explicit row plus a §6 routing-table amendment.

## §5 · Hybrid-Init OpenFOAM-Truth Invariant (`§X.Y`)

> **Authority**: DEC-V61-073 H4 amendment + Pivot Charter "OpenFOAM 是
> 唯一真相源". Mirrors `.planning/specs/EXECUTOR_ABSTRACTION_hybrid_init_invariant.md`
> (which becomes redundant once Notion canonical syncs from this file).

### §5.1 · Invariant statement (formal)

For any whitelist case `c ∈ Cases`, any `seed s`, and any executor
`e ∈ {DOCKER_OPENFOAM, HYBRID_INIT}`:

```
canonical_artifacts(execute(e=HYBRID_INIT, c, s))
  ≡_bytes
canonical_artifacts(execute(e=DOCKER_OPENFOAM, c, s))
```

where:

- `canonical_artifacts(...)` is the set of fields the AuditPackage
  manifest pins as **physical-truth-source artifacts** for a run. As
  of `src/audit_package/manifest.py` (SCHEMA_VERSION = 1, `_RUN_INPUT_FILES`
  at line 51), this set is:
  - **Run inputs** (`inputs` dict, every entry collected when present —
    optional members do not break the contract if absent):
      - `system/controlDict`
      - `system/blockMeshDict`
      - `system/fvSchemes`
      - `system/fvSolution`
      - `system/sampleDict`
      - `constant/physicalProperties`
      - `constant/transportProperties`
      - `constant/turbulenceProperties`
      - `constant/g`
      - `0/` initial-field files **after the OpenFOAM solver writes
        them back** — i.e., the post-solve `0/` snapshot, not the
        pre-solve initializer-warm-start state. Recognized field
        filenames: `U`, `p`, `T`, `k`, `epsilon`, `omega`, `nut`,
        `alphat` (`_INITIAL_FIELD_FILES` at manifest.py:65).
  - **Run outputs** (`outputs` dict): `solver_log_name`,
    `solver_log_tail` (the last `_LOG_TAIL_LINES` (=120) of the solver
    log, which embeds final residuals + completion banner per
    manifest.py:67), and `postProcessing_sets_files` (sorted listing
    of `postProcessing/sets/` output files).
  These fields are extracted by `manifest.py:_load_run_inputs` (line
  186) / `_load_run_outputs` (line 206) and serialized byte-
  deterministically by `serialize.py` (`json.dumps(..., sort_keys=True)`,
  repo-relative POSIX paths, caller-injectable timestamps).
- `≡_bytes` is byte-for-byte equality of the serialized manifest's
  `inputs` + `outputs` subtrees (the rest of the manifest — git SHA,
  decision-trail glob, comparator verdict — is not part of the
  canonical-artifacts contract).
- `seed s` is captured by the
  `controlDict.startTime + writeInterval + randomSeed` triple where
  applicable.

If the AuditPackage manifest schema evolves (e.g. SCHEMA_VERSION 2
adds `final_residuals` as a top-level field rather than embedded in
`solver_log_tail`), the canonical_artifacts set above MUST be amended
in lockstep via a §5.1 update DEC.

### §5.2 · Surrogate-as-initializer is non-canonical

The hybrid-init mode's surrogate-warm-start step produces artifacts
under `reports/{case_id}/initializer/`. These are **explicitly
excluded** from `canonical_artifacts(...)`.

The invariant requires that the surrogate's contribution is **washed
out** by the OpenFOAM solver's convergence. If it isn't, the case is
malformed for hybrid-init use and the executor MUST return a
`MODE_NOT_APPLICABLE` status (the canonical name used throughout this
spec and the §5.4 test suite) instead of producing a divergent
canonical artifact set.

### §5.3 · Out-of-scope (clarifications)

The invariant does **not** require:

- That hybrid-init be faster than docker-openfoam — surrogate may
  speed convergence or may be net-slower; performance is not in scope.
- That hybrid-init succeed on every case — `MODE_NOT_APPLICABLE` is a
  legitimate verdict for cases without a usable surrogate model.
- That the surrogate model itself be deterministic — only its **effect
  on canonical_artifacts** must be (i.e., washed out by solver).

### §5.4 · Companion unit-test specification

Three test classes MUST exist under `tests/test_executor_modes/` before
P2-T1 ratification:

1. **`test_hybrid_init_byte_equal_to_docker_openfoam(case_id)`** —
   for each whitelist case with both reference docker-openfoam +
   hybrid-init runs, assert `canonical_artifacts` byte-equal.
2. **`test_hybrid_init_initializer_artifacts_not_in_canonical_set(case_id)`** —
   assert that files under `reports/{case_id}/initializer/` are absent
   from `canonical_artifacts(run)`.
3. **`test_trust_gate_warns_on_first_hybrid_init_run(case_id)`** —
   when no reference docker-openfoam run exists yet, TrustGate emits
   `MetricStatus.WARN` with note `hybrid_init_invariant_unverified`
   (per §6.3 below).

## §6 · TrustGate executor-aware routing (`§X.Z`)

> **Authority**: DEC-V61-073 H4 amendment Q5(b) finding + RETRO-V61-001
> Codex-per-risky-PR baseline (TrustGate verdicts must remain
> falsifiable across executor modes).

### §6.1 · Per-mode verdict ceilings

The TrustGate verdict vocabulary is the existing
`MetricStatus = {PASS, WARN, FAIL}` enum from
`src/metrics/base.py:37` (per `METRICS_AND_TRUST_GATES.md` v0.1
three-state decision). The brief's earlier shorthand
"PASS_WITH_DISCLAIMER" is rendered in this codebase as a
`WARN`-with-note pair. §6 uses the actual three-state vocabulary
throughout to stay consistent with the implementation.

| Mode | Verdict surface | Routing |
| --- | --- | --- |
| `docker_openfoam` | full triad `PASS` / `WARN` / `FAIL` | Full triad. The case-profile `tolerance_policy` resolves the verdict per `METRICS_AND_TRUST_GATES`. |
| `foam_agent` *(adapter identity for docker_openfoam at this layer)* | same as above | Full triad — adapter identity is a manifest field, not a routing dimension. |
| `mock` | **ceiling = `WARN`** with note `mock_executor_no_truth_source` | A `mock` run can NEVER reach `PASS`. Even if synthetic deviations are zero, the gate emits `WARN` with that note string. |
| `hybrid_init` | full triad on the **OpenFOAM** artifacts only | TrustGate consumes `canonical_artifacts(run)` per §5.1. Initializer artifacts are out-of-scope for verdict. The surrogate's contribution is **not** scored. |
| `future_remote` | (stub-only this milestone) | TrustGate refuses to score a `future_remote` manifest. The CLI/UI surfaces `mode_not_yet_implemented`. DEC-V61-078 sets the real contract. |

### §6.2 · Routing invariant

A TrustGate verdict is **mode-agnostic at the truth layer** — i.e.,
two runs of the same case under different modes (where both modes
reach truth-source artifacts per §4) produce verdicts that depend
ONLY on `canonical_artifacts(...)` content, not on `executor.mode`.
The mode is recorded in provenance but not used as a verdict input.

The `mock` ceiling and the `future_remote` refusal in §6.1 are
explicit exceptions that exist precisely **because** those modes do
not reach truth-source artifacts.

### §6.3 · Hybrid-init reference-run gate

When TrustGate evaluates a `RunReport` produced by `mode = hybrid_init`:

1. **Verify** the §5.1 byte-equality property held against the
   executor's claimed reference run. The reference is identified by
   the manifest's `executor.contract_hash` plus the case-profile's
   `tolerance_policy_observables` set; the auditor (TrustGate)
   resolves the reference SHA via the AuditPackage decision-trail.
2. **Treat** the surrogate-as-initializer step as **out-of-scope** for
   the gate verdict. TrustGate consumes only `canonical_artifacts`.
3. **Emit** `MetricStatus.WARN` with note
   `hybrid_init_invariant_unverified` if the reference docker-openfoam
   run is not yet present (e.g., first-ever hybrid-init run for this
   case). The case-profile owner must then trigger a reference
   docker-openfoam run to anchor the invariant.

### §6.4 · Trust-core boundary preservation

§6 routing logic lives entirely OUTSIDE the trust-core 5 modules
(`gold_standards/`, `auto_verifier/`, `convergence_attestor.py`,
`audit_package/`, `foam_agent_adapter.py`).

Per ADR-001 four-plane import-enforcement (line 73) and
`src/_plane_assignment.py:68` (`"src.metrics": Plane.EVALUATION`),
TrustGate routing logic lives in **`src/metrics/`** — the
TrustGate overall-verdict reducer landed under P1-T2 (DEC-V61-055)
and that is where §6.1 dispatch belongs. `src/metrics/` is a
read-only consumer of this spec; adding a new ExecutorMode does not
require modifying trust-core 5 modules.

(There is no `src/cfd_harness/trust_core/` package in this repo; some
historical brief language used that name forward-looking — the
authoritative location per ADR-001 is `src.metrics.*` in the
EVALUATION plane.)

Adding a new mode requires:

1. A new row in §4 contract-surface table.
2. A new row in §6.1 routing table.
3. A new `ExecutorMode` enum value + adapter implementation under the
   appropriate plane (EXECUTION for executors, EVALUATION for routing
   updates).
4. Codex review per RETRO-V61-001 baseline (any new adapter ≥5 LOC).

It does NOT require trust-core source changes.

## §7 · Risk-flag candidates for P2-T1 intake

Per RETRO-V61-053 addendum (post-R3 live-run defects), P2-T1 must
adopt the following risk flags during intake:

1. **`manifest_tag_round_trip_test`** — verify `read(write(manifest))`
   survives the new `executor` field.
2. **`legacy_signed_zip_compatibility_test`** — verify zips signed
   pre-P2 still verify (treating absent `executor` field as
   `DOCKER_OPENFOAM`).
3. **`executor_contract_hash_pinning`** — `contract_hash` is computed
   from this frozen spec file's git SHA, not the executor *class*
   (which would churn with implementation changes).
4. **`executable_smoke_test`** (V61-053) — every new mode lands with
   a smoke test that runs end-to-end against at least one whitelist
   case (or returns `MODE_NOT_APPLICABLE` cleanly).
5. **`solver_stability_on_novel_geometry`** (V61-053) — hybrid-init
   intake must include at least one geometry class outside the
   surrogate's training distribution; expected outcome is either
   convergence to truth-equivalent canonical_artifacts or
   `MODE_NOT_APPLICABLE`.

## §8 · Promotion + cross-references

### Promotion path

1. **Codex APPROVE** of this v0.2 (PC-2 acceptance gate).
2. **DEC-V61-073** flips Status from `ACCEPTED_WITH_AMENDMENTS_PENDING_LANDING`
   to `Accepted`, citing this commit hash.
3. **Notion canonical doc** (`ecee8d970e8148ec8c714eba8f250110`)
   syncs from this file post-flip.
4. **DEC-V61-074 (P2-T1)** kickoff cites §5 + §6 as prerequisite-met.

### Cross-references

- **Parent DEC**: `.planning/decisions/2026-04-26_v61_073_independent_audit_amendments.md`
- **Companion amendment (subsumed)**: `.planning/specs/EXECUTOR_ABSTRACTION_hybrid_init_invariant.md`
- **Companion spike**: `.planning/specs/EXECUTOR_ABSTRACTION_compatibility_spike.md`
- **TrustGate metrics contract**: `docs/specs/METRICS_AND_TRUST_GATES.md`
- **AuditPackage canonical JSON**: `docs/specs/AUDIT_PACKAGE_CANONICAL_JSON_SPEC.md`
- **Version-compat policy**: `docs/specs/VERSION_COMPATIBILITY_POLICY.md`
- **Notion canonical (post-sync)**: `ecee8d970e8148ec8c714eba8f250110`
- **§10.5 budget gate**: `scripts/methodology/sampling_audit.py` (PC-3)
- **§10.5.4a surface list**: `.planning/methodology/2026-04-26_v2_section_10_5_and_11_draft.md`
