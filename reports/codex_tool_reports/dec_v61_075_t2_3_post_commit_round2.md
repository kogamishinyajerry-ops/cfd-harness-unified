# DEC-V61-075 P2-T2.3 · Codex post-commit review · Round 2

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: commit `bf6aac5` (T2.3 R1 fix bundle)
- **Date**: 2026-04-27
- **Codex command**: `codex review --commit bf6aac5 --title "DEC-V61-075 P2-T2.3 post-commit Codex R2 · verify R1 P2-A/B/C closure"`

## Findings

### 1. P1 — `KnowledgeDB.load_gold_standard()` returns embedded gold_standard, not file-backed `legacy_case_ids`

The R1 fix sourced legacy aliases from `self._db.load_gold_standard(canonical_case_id)`. But `KnowledgeDB.load_gold_standard()` returns the embedded `whitelist.yaml::gold_standard` block — that block does NOT contain rename metadata. For example, `duct_flow`'s aliases live only in `knowledge/gold_standards/duct_flow.yaml::legacy_case_ids` (file-backed). In a HYBRID_INIT run for `duct_flow` with a pre-rename manifest whose `case.id` is `fully_developed_pipe`, `legacy_aliases` stays empty and the run is still capped at `hybrid_init_invariant_unverified` — the R1 P2-B fix was vacuous.

**Location**: `src/task_runner.py:527-530`

### 2. P2 — `_manifest_matches_case` raises `TypeError` on unhashable `case.id`

If a scanned manifest has `case.id` or an item in `case.legacy_ids` as an object/array, the set construction `{manifest_id, *manifest_legacy} - {None}` raises `TypeError: unhashable type`. That aborts `has_docker_openfoam_reference_run()` instead of treating the bad manifest as a non-match — a single malformed archive breaks HYBRID_INIT trust-gate routing rather than being silently skipped (regresses the tolerant-corpus contract).

**Location**: `src/audit_package/reference_lookup.py:202-203`

## R3 closure (commit `6a13b31`)

* P1: New `_load_legacy_aliases(case_id)` module-level helper in `src.task_runner` reads `knowledge/gold_standards/<case_id>.yaml` directly via `yaml.safe_load`. Failure to load (file missing, malformed YAML, field absent, non-list value, non-string entries) returns empty tuple — must NOT raise, mirrors `src.audit_package.manifest::_load_gold_standard`.
* P2: Filter to `isinstance(ident, str)` before set construction in `_manifest_matches_case`. Non-string entries silent-skip; rest of the legacy_ids list still matches normally.
* New tests: `test_malformed_case_id_does_not_raise` + `test_hybrid_init_resolves_legacy_aliases_from_file_backed_gold_standard` (uses real `knowledge/gold_standards/duct_flow.yaml`).

## Final disposition

R3 introduced 1 P2 (injected KnowledgeDB root); R4 + R5 each 1 P2 (slug DB → duck-type fallback). Full arc: 6a13b31 → 27d4e06 → 2170590 → 30b866f.
