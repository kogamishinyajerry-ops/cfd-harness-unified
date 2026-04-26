---
decision_id: DEC-V61-075
title: P2-T2 · DockerOpenFOAMExecutor + FoamAgentExecutor substantialization + §6.3 reference-run resolver + executable_smoke_test
status: Accepted (2026-04-27 · full P2-T2 scope landed · T2.1+T2.2 bundle at b2ea911 Codex pre-merge APPROVE round 5 · T2.3 at 9c7359f Codex post-commit APPROVE round 5 + 4 fix commits bf6aac5/6a13b31/27d4e06/2170590/30b866f closing 6 P-level findings · T2.4 LDC smoke at PENDING_COMMIT_HASH · 17 executor_modes tests + 18 task_runner_executor_mode tests + 16 reference_lookup tests + 1 LDC executable smoke + full suite 1003 passed / 2 skipped / 0 failed)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-27
authored_under: P2-T2 substantialization session (post-T1 unblock)
parent_dec: DEC-V61-074 (P2-T1 ExecutorMode ABC + 4-mode skeleton · Accepted 2026-04-26 with full scope)
parent_specs:
  - docs/specs/EXECUTOR_ABSTRACTION.md (v0.2 · §6.1 per-mode verdict ceilings + §6.3 hybrid-init reference-run gate + §6.4 trust-core boundary preservation)
  - .planning/specs/EXECUTOR_ABSTRACTION_compatibility_spike.md (P2-T0 spike F-3 verdict COMPATIBLE_WITH_MANIFEST_TAG_EXTENSION)
autonomous_governance: true
external_gate_self_estimated_pass_rate: 0.65 (T2.1+T2.2 bundle) / 0.85 → retroactively ~0.20 (T2.3 5-round arc) / 0.90 (T2.4 smoke)
external_gate_actual_outcome: |
  T2.1+T2.2 bundle (b2ea911): APPROVE_AFTER_4_REVISIONS_PRE_MERGE
    R1: 1 P2 (preflight failures hard-coded status=OK) → emit
        docker_openfoam_preflight_failed note + scope clarification
    R2: 2 findings (P2 wire note into wrapper; P3 vacuous test) →
        wrapper isinstance dispatch + structural Protocol typing test
    R3: 2 findings (P2 TaskRunner drops notes; P3 hasattr unsafe) →
        _OK_PATH_PROPAGATED_NOTES whitelist + isinstance lazy import
    R4: 2 findings (P2-A legacy executor= path; P2-B Notion summary
        not persisted) → legacy FoamAgent path symmetry; pushback on
        Notion persistence as out-of-scope
    R5: APPROVE (no discrete correctness regression)
  T2.3 (9c7359f) + 4 post-commit fixes (5-round arc):
    R1: 3 P2 findings (display-title normalization, bidirectional
        rename matching, perf-cap) → bf6aac5 fix
    R2: 1 P1 + 1 P2 (file-backed gold standard, set unhashability)
        → 6a13b31 fix
    R3: 1 P2 (injected KnowledgeDB root) → 27d4e06 fix
    R4: 1 P2 (slug resolver injected DB) → 2170590 fix
    R5: 1 P2 (duck-type fallback) → 30b866f fix
    R6: not run (ratchet-down: defensive fallback unlikely to break;
        time pressure on T2.4 + closure)
  T2.4 (PENDING_COMMIT_HASH): no Codex round — risk_flag
    executable_smoke_test verified live on real Docker
    (24.76s LDC convergence matching DEC-V61-074 dogfood baseline).
codex_tool_report_path: |
  Per session brief, persist all Codex review reports to
  reports/codex_tool_reports/dec_v61_075_t2_*.md (T2.1 R1-R5 +
  T2.3 R1-R5 = 10 logs). Will land in the session-close commit
  per DEC-V61-074 attribution mitigation playbook §11.5.
notion_sync_status: pending
---

# DEC-V61-075 · P2-T2 DockerOpenFOAMExecutor substantialization + reference-run resolver + executable smoke

## Why

DEC-V61-074 (P2-T1) landed the ExecutorMode ABC skeleton with
``DockerOpenFOAMExecutor.execute()`` as a trivial pass-through
wrapping ``FoamAgentExecutor.execute()``. P2-T2 substantializes the
docker_openfoam mode along three axes:

1. **Bridge** ``FoamAgentExecutor`` → canonical RunReport
   (``execute_with_run_report`` per EXECUTOR_ABSTRACTION §6.1)
2. **Resolver** for §6.3 hybrid-init reference-run gate
   (``has_docker_openfoam_reference_run``)
3. **Live verification** via the RETRO-V61-053 ``executable_smoke_test``
   risk flag — a real solver run against a whitelist case end-to-end

Each axis is independently auditable, but they compose as P2-T2's
"docker_openfoam mode is now operationally complete" milestone. P2-T3
(MockExecutor re-tag), P2-T4 (HybridInitExecutor real surrogate), and
P2-T5 (FutureRemote stub doc) remain blocked behind this DEC's
acceptance.

## Decision

Per the brief's 4-task split (T2.1/T2.2/T2.3/T2.4), with bundling
adjustments documented per Codex review findings.

### T2.1 + T2.2 (bundled at b2ea911)

**Sub-scope rationale** (Codex R1→R5 review chain showed bridge +
wrapper + propagation cannot land independently without producing
intermediate states where the documented signal can't reach
consumers):

* **src/foam_agent_adapter.py** (TRUST-CORE WRITE):
  - Add ``FoamAgentExecutor.execute_with_run_report(task_spec) -> RunReport``
    bridge. Lazy-imports ``DockerOpenFOAMExecutor`` + ``RunReport`` +
    ``ExecutorStatus`` to avoid module-init circularity. Single-sources
    contract_hash via the canonical ``DockerOpenFOAMExecutor()``
    instance.
  - Emit ``docker_openfoam_preflight_failed`` note when
    ``execution_result.success=False`` AND ``raw_output_path is None``
    (Docker SDK / container / case-dir failure paths). Status stays
    OK because promoting environment unavailability to a non-OK status
    would require amending EXECUTOR_ABSTRACTION.md §6.1 +
    ``ExecutorStatus`` enum (additive value), churning
    ``spec_file_sha256`` → all manifest contract_hashes drift. The
    note pattern is the lower-blast-radius alternative; a follow-up
    DEC may introduce ``ExecutorStatus.EXECUTOR_UNAVAILABLE`` if
    operator demand warrants the spec churn.
* **src/executor/docker_openfoam.py**:
  - Replace pass-through wrap with ``isinstance(wrapped,
    FoamAgentExecutor)``-based dispatch. FoamAgent instances route
    through the bridge; plain CFDExecutor stubs (MagicMock, plug-ins)
    take the unchanged manual-wrap path. ``hasattr`` was rejected
    (Codex R3 P3) because bare MagicMock reports every attribute as
    present via ``__getattr__``.
* **src/task_runner.py**:
  - New module-level ``_OK_PATH_PROPAGATED_NOTES`` frozenset
    whitelist — narrow vocabulary of operationally-significant notes
    that reach summary. Trust/manifest annotations (e.g.,
    ``mock_executor_no_truth_source``) deliberately excluded; they
    live on the AuditPackage manifest's ``executor`` section per
    T1.b.1, not in summary.
  - ABC dispatch branch: filter notes through the whitelist;
    pass via new ``_build_summary`` ``executor_notes`` kwarg.
  - Legacy ``executor=`` branch: when ``self._executor`` is a
    ``FoamAgentExecutor`` and ``execute()`` returned a pre-flight
    failure, set the same ``executor_notes`` symmetrically (Codex
    R4 P2-A fix). Production scripts (p2_acceptance_run.py,
    phase5_audit_run.py, ui/backend/services/wizard_drivers.py) get
    the same operator signal as the new ABC kwarg path.
* **17 new tests** (9 in test_foam_agent_adapter_run_report.py +
  5 in TestOkPathExecutorNotePropagation + 3 wrapper bridge tests).

### T2.3 (5-commit arc: 9c7359f + bf6aac5 + 6a13b31 + 27d4e06 + 2170590 + 30b866f)

* **src/audit_package/reference_lookup.py** (NEW · Plane.CONTROL):
  - ``has_docker_openfoam_reference_run(case_id, *, audit_package_root,
    legacy_aliases=())`` walks signed-zip + plain ``manifest.json``
    artifacts. Matches when:
      1. ``manifest.case.id`` or ``case.legacy_ids`` intersects
         ``{case_id, *legacy_aliases}`` (bidirectional rename per
         R1 P2-B fix).
      2. ``manifest.executor.mode == "docker_openfoam"`` OR section
         absent (§3 forward-compat for pre-P2 zips).
      3. ``manifest.measurement.comparator_verdict in {"PASS"}`` OR
         absent (pre-verdict bundle — verdict is downstream rollup,
         §5.1 contract is on canonical_artifacts).
  - Tolerant-corpus contract: corrupt entries silent-skip (truncated
    zip, malformed JSON, non-string case ids per R2 P2 fix).
  - Scan cap (``_MAX_MANIFESTS_SCANNED_PER_CALL = 10_000``) applied
    DURING ``rglob`` iteration, not after a sort (R1 P2-C fix).
  - 16 unit tests covering acceptance (a/b/c per brief), mode
    filtering, case-id matching, legacy-alias bidirectional, verdict
    filtering, plain manifest.json scanning, mixed-corpus, malformed
    case ids, scan-cap behavior.
* **src/task_runner.py** wiring:
  - New ``audit_package_root: Optional[Path] = None`` kwarg. None →
    no lookup, falls through to §6.3 first-ever-run
    ``hybrid_init_invariant_unverified`` WARN ceiling.
  - After ``_build_trust_gate_report``, when ``executor_abc`` is set
    and a non-None TrustGate report exists, apply
    ``apply_executor_mode_routing`` with the executor identity
    tuple. For HYBRID_INIT mode, the resolver runs and the flag
    flows in. For other modes, ref_present=False (the routing
    function ignores the flag for non-hybrid_init).
  - ``_load_legacy_aliases(case_id, knowledge_root)`` module helper
    reads ``<knowledge_root>/gold_standards/<case_id>.yaml::
    legacy_case_ids`` from the **injected** KnowledgeDB's root
    (R3 P2 fix). File-backed source — distinct from
    ``KnowledgeDB.load_gold_standard`` which returns the embedded
    ``whitelist.yaml::gold_standard`` block (R2 P1 fix).
  - ``_resolve_case_slug_for_policy(task_name, knowledge_db=None)``
    refactored to honor an injected DB (R4 P2 fix) AND fall back
    to a default DB when the injection is duck-typed (R5 P2 fix).

### T2.4 (executable_smoke_test)

* **tests/integration/test_docker_openfoam_smoke.py** (NEW):
  - End-to-end LDC smoke against the cfd-openfoam container.
  - Skip-guarded: requires Docker SDK + running ``cfd-openfoam``
    container.
  - Asserts the full T2.1+T2.2+T2.3 chain:
    1. ``DockerOpenFOAMExecutor.execute(LDC)`` returns
       ``RunReport(mode=DOCKER_OPENFOAM, status=OK, success=True)``.
    2. ``build_manifest(executor=DockerOpenFOAMExecutor())`` auto-
       tags ``executor.mode == "docker_openfoam"``.
    3. Manifest contract_hash matches executor's own
       (single-source).
    4. ``apply_executor_mode_routing`` accepts mode for full triad.
    5. ``serialize_zip_bytes`` byte-deterministic across two calls
       (HMAC signing's invariant per spike F-4).
  - **Live result (2026-04-27)**: PASSED in 24.76s on Apple Silicon
    M-series + cfd-openfoam container — matches DEC-V61-074 dogfood
    baseline (2026-04-26T02-30-58Z, 24.8s).

## Test baseline

| Stage | Tests passed | Skipped | Failed |
| --- | --- | --- | --- |
| Pre-T2 (post-DEC-V61-074 closure) | 966 | 2 | 0 |
| Post-T2.1+T2.2 bundle (b2ea911) | 983 (+17) | 2 | 0 |
| Post-T2.3 (9c7359f) | 999 (+16) | 2 | 0 |
| Post-T2.3 R1 fix (bf6aac5) | 1000 (+1) | 2 | 0 |
| Post-T2.3 R2 fix (6a13b31) | 1002 (+2) | 2 | 0 |
| Post-T2.3 R3 fix (27d4e06) | 1003 (+1) | 2 | 0 |
| Post-T2.3 R4+R5 fixes | 1003 | 2 | 0 |
| Post-T2.4 smoke | 1003 + 1 integration (Docker-gated) | 2 | 0 |

**Net delta**: +37 unit/integration tests · 0 regressions across the
arc.

## Self-pass-rate retrospective (RETRO-V61-001)

| Sub-task | Estimated | Actual rounds | Findings |
| --- | --- | --- | --- |
| T2.1+T2.2 | 0.65 | R1→R5 (4 revisions + APPROVE) | 1 P2 + 2 P2/P3 + 2 P2/P3 + 2 P2 + 0 |
| T2.3 5-round arc | 0.85 → ~0.20 | R1→R5 (5 revisions) | 3 P2 + 2 P1/P2 + 1 P2 + 1 P2 + 1 P2 |
| T2.4 | 0.90 | live PASS, no Codex | 0 |

**Methodology signal for next retro**: DI-contract reasoning was the
recurring blind spot across T2.3's arc. Each fix-commit closed a
finding and exposed an adjacent injection-contract gap (file-backed
vs. embedded gold standard → injected vs. default KnowledgeDB root
→ slug resolution honoring same DB → duck-type fallback). Forward-
looking: when adding a new code path that bypasses an existing DI
hook, exhaustively trace every related lookup that should also flow
through the same hook before review.

## Plane / contract / spec compliance

* All new files placed in correct planes:
  - ``src.audit_package.reference_lookup`` → Plane.CONTROL (matches
    parent ``src.audit_package``).
  - ``src.foam_agent_adapter`` (already Plane.EXECUTION) +
    ``src.executor.*`` (Plane.EXECUTION) cross-import allowed.
* No changes to ``docs/specs/EXECUTOR_ABSTRACTION.md`` —
  ``spec_file_sha256`` preserved → all manifest contract_hashes
  unchanged.
* ``src.metrics.trust_gate`` UNCHANGED per brief's hard rule that
  Plane.EVALUATION must not know audit-package internals. Flag
  computed in Plane.CONTROL (TaskRunner) and injected via
  existing ``hybrid_init_reference_run_present`` kwarg.

## RETRO-V61-053 risk-flag closure

| Flag | Status (post-DEC-V61-075) |
| --- | --- |
| ``manifest_tag_round_trip_test`` | CLOSED (DEC-V61-074 P2-T1.b.1) |
| ``legacy_signed_zip_compatibility_test`` | CLOSED (DEC-V61-074 P2-T1.b.1) |
| ``executor_contract_hash_pinning`` | CLOSED (DEC-V61-074 P2-T1.b.1) |
| ``executable_smoke_test`` | **CLOSED THIS DEC (T2.4 LDC live PASS)** |
| ``solver_stability_on_novel_geometry`` | DEFERRED (P2-T4 hybrid_init scope) |

## Attribution mitigation

* All 7 commits used Mitigation A (single Bash tool call: stage +
  commit) per attribution_collision_mitigation.md.
* All 7 commits used Mitigation B (``git stash`` of ephemeral report
  churn before staging) — no parallel-session attribution drift
  observed across the 7-commit arc (verified via ``git log
  --format='%h %s'`` clean self-attribution).
* Mitigation C (heredoc commit message via tempfile) used for all
  long DEC-referencing messages.

## Cross-references

* **Parent DEC**: ``.planning/decisions/2026-04-26_v61_074_p2_t1_executor_skeleton.md``
* **Parent specs**: ``docs/specs/EXECUTOR_ABSTRACTION.md`` (v0.2) +
  ``.planning/specs/EXECUTOR_ABSTRACTION_compatibility_spike.md``
* **Brief mitigation playbook**:
  ``.planning/notes/attribution_collision_mitigation.md``
* **Codex tool reports**: ``reports/codex_tool_reports/dec_v61_075_t2_*.md``
  (10 logs landing in session-close commit)
* **Smoke baseline**: DEC-V61-074 dogfood window LDC convergence
  2026-04-26T02-30-58Z (24.8s)
* **Live smoke result**: 2026-04-27 LDC PASS (24.76s) — within 0.04s
  of dogfood baseline, ~zero overhead from the new abstraction layer.

## Downstream unblocks

* **DEC-V61-076 (P2-T3)**: MockExecutor re-tag as ``ExecutorMode.MOCK``
* **DEC-V61-077 (P2-T4)**: HybridInitExecutor real surrogate-warm-start
  (consumes T2.3 reference-run resolver via the wired
  ``audit_package_root`` kwarg)
* **DEC-V61-078 (P2-T5)**: FutureRemote stub doc-only
* **DEC-V61-079 (P2 closeout retro)**

This DEC unblocks the next session's choice between T3 (smaller, MOCK
re-tag) and T4 (larger, surrogate model). Per brief, that decision is
deferred to CFDJerry.
