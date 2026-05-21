# Red Team Review — Tier-1 Fixes (Round 2)

- **Scope:** the Tier-1 fixes filed under `agent_events.jsonl[REDTEAM-T1-FIX-20260520]` (2026-05-20).
- **Reviewer:** test-red-team
- **Verdict on Tier-1 goal (close F-01 / F-02 / F-03):** **PASS — all 3 CRITICAL findings genuinely closed.**
- **Verdict on bootstrap overall:** **STILL FAIL** — Tier-1 introduced 1 new HIGH finding (T1-F-01) plus 6 smaller findings, and the Tier-2/3/4 residual from the original review is untouched.

> This review is a supplement to `red_team_bootstrap_review.md`, not a replacement.

---

## 1. Verification that the 3 CRITICAL findings are actually closed

### F-01 (cockpit hardcoded narrative) — **CLOSED**

- `tools/cwos_render_dashboard.py` rewritten. Agent Matrix, Decisions Needed, Next Best Actions, Bright Spots are all derived.
- **Live verification performed:** `mv .claude/agents/test-red-team.md /tmp/ && make cockpit` → Agent Matrix dropped from 13 to 12 rows. Restoring the file recovered the row. Cockpit observably depends on repo state, not on template text.
- No hardcoded narrative strings remain inside `render_md`. Grepped — only structural section headers and inline literals like `_None._`.

### F-02 (tasks.yaml PASS without backing events) — **CLOSED**

- Static `status: PASS` field removed from all 10 `tasks:` entries. The comment block at the top of `tasks.yaml` explicitly states "task status is NOT stored here."
- `cwos_status.py:task_summary()` now derives `by_status` from the latest event per `task_id` in `agent_events.jsonl`. Verified live: after status field removal but before backfilling events, `by_status` showed `{QUEUED: 10}` (honest in-progress state).
- 10 per-task PASS events backfilled (`PH0-{MEMORY,AGENTS,SKILLS,CLI,SCHEMA,CASE,STATUS,COCKPIT,TESTS,DOCS}-001`), each citing real evidence paths from the corresponding `evidence_required` list in `tasks.yaml`.
- All 10 events satisfy `tests/test_red_team_safety.py::test_pass_event_evidence_paths_exist_on_disk` (i.e., evidence paths actually resolve on disk).

### F-03 (schema allows mocked + validated) — **CLOSED**

- `trust_report.schema.json` now carries 3 `allOf if/then` clauses:
  1. `solver_execution == "mocked"` → `validation_status != "validated"`
  2. `overall_status == "PASS"` → `solver_execution == "real"`
  3. `validation_status == "validated"` → `solver_execution == "real"`
- 3 new pytest cases exercise each rejection path:
  - `test_schema_rejects_mocked_plus_validated`
  - `test_schema_rejects_mocked_plus_pass_overall`
  - `test_schema_rejects_validated_with_skipped_solver`
- **Live verification performed:** hand-constructed a `{mocked, validated}` dict → schema produced 2 errors. `{mocked, PASS overall}` → 1 error. The real current report still validates clean.

---

## 2. New findings introduced by the Tier-1 fixes

### T1-F-01 — Bright Spots ingests phantom-evidence PASS events without verifying paths exist. **HIGH.**

**Why this is genuinely new:** before Tier-1.2, the cockpit's Bright Spots was hardcoded prose. Now it's derived from `agent_events.jsonl` PASS events, but the derivation only checks that `evidence` is a non-empty list — it does NOT verify the cited paths exist on disk. The `test_pass_event_evidence_paths_exist_on_disk` safety test catches this at test time, but the **cockpit** would display the phantom claim until the next test run.

**Live repro (proven during this review, non-destructive):**

```
bright_spots picked up phantom PASS: 1
  summary: I shipped quantum CFD
  evidence (claimed): ['this/file/does/not/exist.py', 'also/fake/path.json']
```

A phantom-evidence PASS event injected into a tmp jsonl is happily displayed as a Bright Spot. The same defect F-08 identified at the event-write layer now exists at the cockpit-read layer.

**Fix:** in `derive_bright_spots`, skip events whose evidence paths do not all resolve to existing files. Add a counter to the Integrity Checks section: "Bright Spots filtered for phantom evidence: N."

### T1-F-02 — Frontmatter parser will silently mangle multi-line YAML block scalars. **MEDIUM.**

**Why:** `tools/cwos_render_dashboard.py:_parse_frontmatter` is a hand-rolled `line.partition(":")` parser. Current agent files all use single-line `description: ...` values — works fine. But the moment someone uses YAML block syntax:

```yaml
description: |
  Multi-line
  description here
```

the parser sets `description = "|"` (literal pipe) and the cockpit shows the agent's description as the single character `|`. Graceful failure mode (cockpit still renders), but the matrix is silently wrong.

**Fix:** replace `_parse_frontmatter` with `yaml.safe_load(frontmatter_block)`. PyYAML is already a project dependency.

### T1-F-03 — Schema enforcement is write-only; ingest path skips validation. **MEDIUM.**

**Why:** `src/cfdtrust/audit/report.py:assemble()` validates against the schema before writing. But `tools/cwos_status.py:discover_trust_reports()` just `json.loads()` the file — no schema validation. A hand-edited `trust_report.json` whose tamper is **internally consistent** (e.g., flip all three of `solver_execution: real`, `validation_status: validated`, `overall_status: PASS`) passes both the schema if/then clauses and the cockpit ingestion.

**Repro (logic-level, performed during this review):**
```
cockpit-style ingest of tampered report:
  overall_status=PASS  solver=real  validation=validated
schema errors (if validation were done at ingest): 0
Draft7Validator references in cwos_status.py: 0
```

The schema catches **inconsistent** lies (mocked+validated). It does NOT catch **consistent** lies (real+validated+PASS) because nothing cross-checks the report against the underlying artifacts (`solver.log` carries a "no real solver" banner that the cockpit never reads).

**Related residual:** original F-13 (tamper detection on `trust_report.json`) is unaddressed. Schema if/then narrows the attack surface but does not close it.

**Fix:**
1. `discover_trust_reports` should validate each loaded report and downgrade `overall_status` to `BLOCKED` (or surface a Integrity Checks row) when schema fails.
2. Add a schema constraint coupling `gates.*.status` to `overall_status` (e.g., if any gate is MOCKED, overall must not be PASS — currently enforced only by `_overall_status` in `report.py`).
3. The hash-chain tamper detection deferred from F-13 is the proper long-term answer.

### T1-F-04 — Retroactive PASS events are not programmatically distinguishable from real-time PASS events. **MEDIUM.**

**Why:** the 10 backfilled events from Tier-1.1 are honest only because the free-text `summary` field says "retroactive backfill." There is no schema field, no `verified_at` timestamp, no `retroactive: true` flag. A future tool / agent / auditor reading the log cannot programmatically tell whether a PASS event was filed at the moment the work was verified, or hours/days/weeks after the fact.

**Fix:** extend `tools/cwos_event.py` with an optional `--retroactive` flag that adds a `retroactive: true` field. Make `cwos_status.py` count retroactive PASS events separately in Integrity Checks: "Retroactive PASS events: N (review for staleness)."

### T1-F-05 — Self-certification persists at the meta-layer. **HIGH (pre-existing, re-surfaced).**

**Why:** every PASS event currently in `.cwos/agent_events.jsonl` was written by the same actor (this Claude session) wearing different agent personas. That includes:

- the original `PH0-BOOTSTRAP` event filed as `project-governor`
- the 10 retroactive per-task PASS events filed as `docs-knowledge-engineer` / `backend-engineer` / `system-architect` / `benchmark-director` / `progress-intelligence-agent` / `test-red-team`
- the `REDTEAM-T1-FIX-20260520` event filed as `project-governor` certifying my own Tier-1 fixes

The CLAUDE.md principle "Dev agents cannot validate their own work" and the test-red-team forbidden-action "may not approve your own prior findings" are entirely on the honor system. Tier-1 did not make this worse but did not improve it either.

**This is the same as deferred Tier-4 task 11.** Re-surfaced here to confirm Tier-1 did not address it.

**Fix:** Tier-4 task 11 — `cwos_event.py` should reject a PASS event whose `--agent` matches the `owner_agent` for that `task_id` in `tasks.yaml`. Forces at least two-actor sign-off in principle (though both actors can still be the same human/AI in practice — separation is procedural, not cryptographic).

### T1-F-06 — One pre-existing decision item silently dropped by the cockpit refactor. **LOW.**

**Why:** the old hardcoded "Decisions Needed" section included three items, the third being *"Approve the agent set in `.claude/agents/` before any agent acts on its mandate."* The new derivation reads from `OPEN_QUESTIONS.md`, which does not contain this item. The agent-set approval question is now invisible to the cockpit.

**Fix (small, principled):** either add `OQ-0006 — Approve the current `.claude/agents/` roster before granting authority` to `OPEN_QUESTIONS.md`, OR explicitly resolve it in `DECISION_LOG.md` as DEC-0005 with rationale.

### T1-F-07 — Orphan events are silently ignored. **LOW.**

**Why:** `task_summary` walks `tasks.yaml` and looks up each `task_id` in the event-derived `latest_status_per_task` dict. If a task is removed from `tasks.yaml` but its events remain in `agent_events.jsonl`, those events are dropped from the cockpit's task counts. Defensible (clean removal), but potentially conceals historical state.

**Fix (optional):** Integrity Checks section adds "Orphan event task_ids: [list]" so the user is warned when events reference tasks no longer in the registry.

---

## 3. What the Tier-1 fixes did NOT touch (residual from original review)

These remain open and were never claimed addressed by Tier-1. Listed for completeness.

| original id | severity | one-line |
|---|---|---|
| F-04 | HIGH | manifest `solver_backend` and adapter availability not coupled |
| F-05 | HIGH | `cfdtrust audit` runs the solver; semantics blurred |
| F-06 | HIGH | CLI exit codes do not propagate FAIL/BLOCKED |
| F-07 | HIGH | `cwos_event.py` accepts any `--agent` string |
| F-08 | HIGH | PASS-event evidence path existence not validated by `cwos_event.py` (NOTE: a test catches it post-facto; T1-F-01 is the cockpit-layer mirror of this gap) |
| F-09 | MEDIUM | no `.gitignore` |
| F-10 | MEDIUM | architecture doc references non-existent `cfdtrust/backends/openfoam.py` |
| F-11 | MEDIUM | `case_manifest.schema.json` has `additionalProperties: true` (typo holes) |
| F-12 | MEDIUM | `reference_comparison.status: finalized` does not require `source` |
| F-13 | MEDIUM | no tamper detection on `trust_report.json` (now partially mitigated by schema if/then per T1-F-03) |
| F-14 | MEDIUM | agent "Forbidden actions" lists are text-only |
| F-15 | LOW | NEXT_ACTIONS item 7 is a "do NOT" list |
| F-16 | LOW | Agent Matrix description duplicates `.md` body content |

---

## 4. Tests added by this review

**None.** Adding tests for T1-F-01 / T1-F-02 / T1-F-03 today would either (a) currently fail and break `make bootstrap-check`, or (b) require fixing the code first. Per the original rule from the bootstrap red-team-review skill, tests land alongside fixes, not before.

If you want a single safe addition I can make immediately: a test that asserts `cwos_render_dashboard.derive_bright_spots` rejects events whose evidence paths do not exist. That test would currently pass against the live log (all real evidence exists) but fail against synthetic phantom-evidence input. Tells me whether the Bright Spots layer is doing its filter job. Say the word.

---

## 5. Recommendation

**Verdict on Tier-1's stated scope:** PASS. The 3 CRITICAL findings F-01, F-02, F-03 are genuinely closed, with live verification on each. Tier-1 was not theatre.

**Verdict on the bootstrap as a whole:** still FAIL. Tier-1 introduced one HIGH-severity new finding (T1-F-01) plus 6 smaller ones. Combined with Tier-2/3/4 residual, the bootstrap still has 6 HIGH-or-higher findings.

**Recommended ordering for next pass (in priority order):**

1. **Fix T1-F-01** (cockpit Bright Spots checks evidence existence) — small, isolated, closes the worst Tier-1-introduced surface. Add the test alongside.
2. **Fix T1-F-02** (use `yaml.safe_load` for frontmatter) — small, hardens the cockpit against future agent-file changes.
3. **Land Tier-2 group as a batch**:
   - F-06 (CLI exit codes propagate FAIL)
   - F-07 + F-08 (cwos_event validates agent name + evidence path existence)
   - F-05 (separate audit from run)
   - F-11 (`case_manifest.schema.json` `additionalProperties: false`)
   - F-12 (`reference_comparison` finalized requires source)
4. **Then T1-F-03 closing pass**: `discover_trust_reports` validates against schema; add gates↔overall consistency constraint.
5. **Decide T1-F-04 / T1-F-05 / T1-F-06 / T1-F-07** explicitly. Each is small but introduces process commitments (retroactive markers, separate-author rule, decision drift handling).
6. **Tier-3 hygiene**: `.gitignore`, architecture doc alignment.

**Do NOT** start Phase 1 (real OpenFOAM adapter) until at least steps 1–4 land. Any false-pass surface remaining when real CFD enters the picture will be much harder to characterize than the same surface against a mocked solver, because the false-pass will look more convincing.

**Do NOT** rationalize T1-F-01 away as "the safety test catches it." The test catches it at test time; the cockpit lies between test runs. The cockpit is the human-facing artifact.
