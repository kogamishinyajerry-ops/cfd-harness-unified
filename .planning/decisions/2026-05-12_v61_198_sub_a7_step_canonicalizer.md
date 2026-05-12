---
decision_id: DEC-V61-198-sub-A7
title: A7 step_canonicalizer · STEP FILE_NAME timestamp canonicalization for byte-determinism
status: Accepted
parent_dec: V61-198
phase: A7 sub-DEC · harvest-003 priority #3
notion_sync_status: pending session-end batch
parent_artifacts:
  - .planning/patches/draft_a7_step_canonicalizer_2026-05-09.md (cycle 002 design)
  - .planning/methodology/industrial_case_solver_findings.md (V80 backfilled 2026-05-13)
  - .planning/cross_cuts/advisor_coverage_2026-05-09.md (harvest-003 priority #3)
  - ui/backend/services/geometry_ingest/step_canonicalizer.py (new module)
  - ui/backend/tests/test_step_canonicalizer.py (new test file)
  - ~/Desktop/case_012_hvac_supply_diffuser/scripts/build_cad.py (reference impl)
trigger: 4-case sediment of OCP STEP exporter wall-clock timestamp determinism failure (case_002a · case_005 · case_011 · case_012). harvest-003 #3 MEDIUM-HIGH priority. case_012 v1 carries case-local workaround; promote to main-project utility for cross-case inheritance per Pillar 2
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (sub-DEC scope · ~115 LOC source · pure utility module · no auth/signing/security boundary per v2.3 §2 · 10-test suite covers contract)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-12
confidence: high (additive new module · 10 new tests verify regex correctness + idempotency + byte-determinism + non-destructive operation · reference impl battle-tested in case_012)
---

# DEC-V61-198-sub-A7 · STEP canonicalizer

## 1. Why now

cadquery 2.7.0 + OCP STEP exporter writes a wall-clock timestamp
into every STEP file's `FILE_NAME(...)` header. Two byte-identical-
geometry runs of the same `build_cad.py` produce different SHA-256
hashes, breaking the Codex case-design protocol's determinism
contract. Observed in **4 case sandboxes**:

- case_002a APU bay (v1..v33 iterations)
- case_005 RAE M2129 S-duct
- case_011 plate-fin compact HX
- case_012 HVAC supply diffuser

case_012 carried a case-local workaround (`scripts/build_cad.py::canonicalize_step`).
harvest-003 priority scoring: **MEDIUM-HIGH** (4 × MED / 80 LOC).
The pattern is identical across all 4 cases → Pillar 2 trigger:
promote case-local utility to main-project module so all future
cadquery cases inherit it.

## 2. What changed

### Source: `ui/backend/services/geometry_ingest/step_canonicalizer.py` (NEW)

- `canonicalize_step_text(text, *, sentinel_timestamp) -> (str, int)`:
  surgical regex replacement on the `FILE_NAME(...)` 2nd quoted arg
  (per ISO 10303-21 `time_stamp` slot). Returns canonical text +
  replaced count. Returns count=0 when no `FILE_NAME` line found.
- `canonicalize_step_file(path, *, inplace, sentinel_timestamp) -> StepCanonicalizationReport`:
  file-level entry. `inplace=True` overwrites; `inplace=False` writes
  sibling `<stem>.canonical.step` leaving original intact. Idempotent
  via `is_already_canonical` signal (pre-canonical input is rewritten
  as no-op — same bytes in, same bytes out).
- `StepCanonicalizationReport` frozen dataclass: `path · replaced_lines ·
  original_sha256 · canonical_sha256 · is_already_canonical`.
- `DEFAULT_SENTINEL_TIMESTAMP = "1970-01-01T00:00:00"` (epoch; STEP-spec-
  compliant since spec mandates `time_stamp` but not wall-clock).

Surgical replacement preserves: author / organization /
preprocessor_version / originating_system / authorisation fields.
Reference impl (case_012) was more aggressive (truncated FILE_NAME at
author comma); A7 productized form is conservative.

### Tests: `ui/backend/tests/test_step_canonicalizer.py` (NEW)

10 tests:
- `test_canonicalize_text_replaces_timestamp` — basic replacement
- `test_canonicalize_text_idempotent` — running twice = same output
- `test_canonicalize_text_no_file_name_unchanged` — silent no-op
- `test_canonicalize_text_preserves_other_fields` — author etc. intact
- `test_canonicalize_text_preserves_geometry_lines` — CARTESIAN_POINT untouched
- `test_canonicalize_text_custom_sentinel` — override default sentinel
- `test_canonicalize_file_inplace_byte_determinism` — two-file cross-run check
- `test_canonicalize_file_not_inplace_writes_sibling` — non-destructive mode
- `test_canonicalize_file_already_canonical_signals` — idempotent on canonical input
- `test_canonicalize_file_returns_report_dataclass` — return-type contract

Run: `uv run python -m pytest ui/backend/tests/test_step_canonicalizer.py -v` → **10 passed in 0.05s**.

### LOC accounting

| Region | LOC |
|---|---|
| Source (`step_canonicalizer.py`) | ~115 |
| Tests (`test_step_canonicalizer.py`) | ~120 |
| **Total** | **~235** (under v2.3 sub-DEC <250 ceiling) |

## 3. V-row status changes

| V-row | Pre-A7 status | Post-A7 status |
|---|---|---|
| V80 (backfilled 2026-05-13) | (did not exist; case_012 finding lacked V-number) | `closed 2026-05-12 · A7 landed (DEC-V61-198-sub-A7)` |

**Numbering note**: case_012 case_index claimed "V49-V53 NEW" with one
of them being STEP timestamp determinism, but those V-numbers got
assigned to case_015/case_016 work that sedimented 2026-05-10/11.
This DEC backfills V80 to give the case_012 finding its V-row.
Same backfill pattern as V79 (D7 advisor-gap).

## 4. What does NOT change

- `FILE_DESCRIPTION` line (conservative first-pass per draft patch
  open-question resolution — extend only on per-evidence basis)
- `FILE_SCHEMA` / `DATA;` body / geometry primitives — untouched by
  regex; tests verify
- case_012's case-local `canonicalize_step` (kept for now; future
  case sub-sessions adopt the main-project module via import)
- Codex case-design protocol's determinism contract (unchanged;
  this DEC closes the implementation gap that the contract relied on)

## 5. Anti-patterns honored

- **No FILE_NAME line truncation** — case_012 reference impl was
  aggressive; A7 surgical regex preserves all other fields
- **No global STEP rewriting** — only the 2nd quoted arg touched
- **No silent failure on missing FILE_NAME** — caller gets
  `replaced_lines=0` signal to inspect
- **No mandatory side effect** — `inplace=False` mode for safe
  non-destructive workflows

## 6. Open questions resolved (from draft patch §"Open questions")

| Question | Resolution |
|---|---|
| Strip `FILE_DESCRIPTION` too? | **No** — conservative first-pass; only FILE_NAME. Extend per-evidence basis (no current case requires FILE_DESCRIPTION canonicalization) |
| Warn if no FILE_NAME line found? | **No-op + signal** — return `replaced_lines=0`; caller inspects. Silent because binary-STEP or non-OCP exporter is a legitimate input class |

## 7. Reversal cost

Low. To reverse:
- `rm ui/backend/services/geometry_ingest/step_canonicalizer.py`
- `rm ui/backend/tests/test_step_canonicalizer.py`
- Revert V80 row in V-series
- Revert priority #3 row in advisor_coverage_2026-05-09.md

No schema migration, no consumer changes, no dependency adds. New
module, isolated.

## 8. References

- Draft patch: `.planning/patches/draft_a7_step_canonicalizer_2026-05-09.md`
- V-series: V80 (backfilled by this DEC), V79 (sibling D7 backfill —
  parallel pattern of "case_012 finding lacked V-row")
- Harvest snapshot: `.planning/cross_cuts/advisor_coverage_2026-05-09.md`
  priority #3 row flipped to LANDED
- Reference impl: `~/Desktop/case_012_hvac_supply_diffuser/scripts/build_cad.py::canonicalize_step` (line 233)
- Parent DEC: V61-198 (APU bay strategic pivot · 5-artifact extraction
  list)
- Sibling sub-DEC: V61-198-sub-A2v2 (landed same day; harvest-003 #1)
