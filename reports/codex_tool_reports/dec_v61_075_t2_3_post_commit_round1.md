# DEC-V61-075 P2-T2.3 · Codex post-commit review · Round 1

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: commit `9c7359f` (T2.3 reference_lookup + TaskRunner wiring)
- **Date**: 2026-04-27
- **Codex command**: `codex review --commit 9c7359f --title "DEC-V61-075 P2-T2.3 post-commit · §6.3 hybrid-init reference-run resolver + TaskRunner wiring"`

## Findings

### 1. P2-A — Display title not normalized before reference-run lookup

When `TaskSpec.name` comes from a Notion page title or whitelist `name` field (a case `_resolve_case_slug_for_policy` already handles for the comparator path), the wiring passed the display string straight into `has_docker_openfoam_reference_run`. Archived manifests store `case.id` as the canonical slug, so a HYBRID_INIT run for `Lid-Driven Cavity` (display title) would miss an existing `docker_openfoam` reference and be wrongly capped at `hybrid_init_invariant_unverified`.

**Location**: `src/task_runner.py:512-514`

### 2. P2-B — Canonical case IDs don't match pre-rename manifests

The resolver only recognized a case when the manifest's `case.id` exactly matched OR `case_id` appeared in the manifest's `legacy_ids`. If the audit corpus contained bundles created before a rename (e.g., `fully_developed_pipe` before DEC-V61-011), querying for the current canonical id (`duct_flow`) never matched them — the old manifest's `legacy_ids` list was empty (rename is forward-only, old manifests cannot have new aliases retroactively backfilled). HYBRID_INIT downgraded to WARN even though a real reference run existed.

**Location**: `src/audit_package/reference_lookup.py:165-168`

### 3. P2-C — Scan cap was vacuous

`sorted(audit_package_root.rglob(...))` exhausts the full generator BEFORE the loop body starts, so `_MAX_MANIFESTS_SCANNED_PER_CALL = 10_000` could not actually bound traversal cost. On a large audit-package root, every HYBRID_INIT lookup paid a full-tree enumeration + sort before stopping at 10,000 entries — defeating the performance guard.

**Location**: `src/audit_package/reference_lookup.py:132`

## R2 closure (commit `bf6aac5`)

* P2-A: Route through `_resolve_case_slug_for_policy(task_spec.name)` (existing helper from DEC-V61-071 R1 F#1) before passing to `has_docker_openfoam_reference_run`.
* P2-B: Added `legacy_aliases: tuple[str, ...] = ()` parameter to `has_docker_openfoam_reference_run`. `_manifest_matches_case` now matches by intersection of `{case_id, *legacy_aliases}` with `{manifest.id, *manifest.legacy_ids}`. TaskRunner sources alias tuple from `KnowledgeDB.load_gold_standard` (corrected in R2).
* P2-C: Dropped `sorted()`, iterate `rglob` directly with cap applied during iteration. Documented determinism trade-off in `_iter_candidate_manifests` docstring (resolver short-circuits at first match → iteration order not externally observable).
* New test: `test_caller_provided_legacy_alias_matches_pre_rename_manifest`.

## Final disposition

R2 introduced 1 P1 + 1 P2 (file-backed gold standard misroute, set unhashability); R3 introduced 1 P2 (injected KnowledgeDB root); R4 introduced 1 P2 (slug resolver injected DB); R5 introduced 1 P2 (duck-type fallback). Full arc: bf6aac5 → 6a13b31 → 27d4e06 → 2170590 → 30b866f.
