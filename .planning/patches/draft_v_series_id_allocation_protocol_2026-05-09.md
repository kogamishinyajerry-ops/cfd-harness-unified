# DRAFT patch · V-series ID allocation protocol (cross-session collision prevention)

> **Status**: DRAFT · suggested-only · NOT auto-applied
> **Author**: harvest cycle 003 · 2026-05-09
> **Target**: main session for landing as governance-rule-change
> **Scope**: methodology amendment + one-time renumbering sweep
> **Triggers**: case_011 + case_012 sub-sessions both allocated
> V49 and V50 to different findings in their append files

## Why this patch

case_011 sub-session executed 2026-05-09 01:19 (commit `bd099f3`) and
allocated V47/V48/V49/V50. case_012 sub-session executed 2026-05-09
02:32 (commit `999d9b9`) and **independently** allocated V49/V50/V51/
V52/V53. Neither sub-session knew about the other's allocations
because:

1. The V-series master file (`industrial_case_solver_findings.md`)
   ends at V46; both sub-sessions read it as their last-known
   high-water-mark
2. Append files (`v_series_*_append_2026-05-09.md`) are written but
   never integrated back into the master before the next sub-session
   reads it
3. There's no allocation registry between the master file and the
   sub-session's "next available V-row" choice

**Result**: V49 means "case_011 A2 plate-plate PASS" OR "case_012 A2
9th cross-topology PASS" depending on which file you read. V50 means
"case_011 thin_wall 7th topology" OR "case_012 D7 advisor-gap
surfacer". Cross-references in case_index.md, INDEX.md, and the
case-profile files compound the ambiguity.

This is the **first instance of cross-session V-row collision** but
will recur as soon as case_013-020 sub-sessions run in any kind of
parallel.

## Surface scan

`grep -rn "V47\|V48\|V49\|V50\|V51\|V52\|V53" /Users/Zhuanz/Desktop/cfd-harness-unified/.planning/` —
~30 cross-references across case_index.md, INDEX.md, both append
files, case_011/012 reference profiles. No central registry exists.

## Recommended protocol

### Option A (cheapest, applied retroactively this cycle)

**File-time-of-commit ordering**: case_011 sediment commit landed
first (`bd099f3` at 01:19); case_012 follows. Therefore case_011 keeps
V47/V48/V49/V50 and case_012 renumbers V49→V51, V50→V52, V51→V53,
V52→V54, V53→V55.

**One-time renumbering sweep**:
1. Edit `v_series_2026-05-09_case_012_append.md` — change all V49/V50/
   V51/V52/V53 references to V51/V52/V53/V54/V55
2. Edit `case_index.md` row 28 (case_012) — V49-V53 → V51-V55
3. Edit `INDEX.md` line 71 + line 89-95 — D7 reference V50 → V52
4. Edit `case_profiles/case_012_hvac_supply_diffuser.md` — V49 → V51,
   V50 → V52, V51 → V53, V52 → V54, V53 → V55
5. Edit drafted patches A6/A7/A8 cross-references
6. Edit harvest 003 report cross-references (this file)

Effort: ~12 string replacements with grep -l → sed loop. ~30 min.

### Option B (durable protocol going forward)

**Allocation registry file** at `.planning/methodology/v_series_allocation_log.md`
(append-only):

```
## V-series allocation log

| V-id | Allocated by | Allocated at (commit/date) | Topic shorthand |
|---|---|---|---|
| V47 | case_011 sub-session | bd099f3 / 2026-05-09 01:19 | chtMultiRegionFoam multi-stream BC |
| V48 | case_011 sub-session | bd099f3 / 2026-05-09 01:19 | sHM compact-fin snap cliff |
| ...
```

**Sub-session allocation rule** (added to `case_kickoff_prompt_template.md`
hard guardrails):

> Before allocating a new V-row, **read** `v_series_allocation_log.md`
> AND check uncommitted/unmerged append files for in-flight reservations.
> Reserve your range by appending rows BEFORE writing the append file.
> If you encounter an in-flight reservation that overlaps your range,
> bump your start ID past the highest reserved ID.

**Why this works**: even if two sub-sessions run in parallel, the
allocation log is the linearization point. The first sub-session to
commit the allocation log wins their range; the second reads the
committed range and bumps. Same idea as `git fetch --tags` before
allocating a release tag.

**Effort**: ~50 LOC to add the log + 1 paragraph in the kickoff
template.

### Option C (defer the problem)

Sub-session sediments use scoped IDs (e.g., `V-case_011-1` instead of
`V47`); harvester promotes to global numbering when sediment integrates
into the master V-series file.

**Effort**: small; cost is loss of cross-case grep convenience (a
finding's stable global ID matters for the RAG corpus).

## Recommendation

**Apply Option A this cycle (renumber case_012 to V51-V55) AND adopt
Option B for case_013-020 onward.** Option C is theoretically clean
but loses the engineering ergonomics that make V-rows useful.

## Open questions

- Should the allocation log have a "reserved by, not yet committed" tier
  (for in-flight sub-sessions that haven't pushed)? Useful but adds
  process overhead.
- When the V-series master file gets V47-V55 integrated (next harvest
  cycle's main-session sweep), should the allocation log be auto-purged
  to keep it < 500 lines, or kept as an audit trail?

## Cross-references

- `industrial_case_solver_findings.md` — V-series master (ends V46)
- `v_series_case_011_append_2026-05-09.md` — case_011 V47-V50
- `v_series_2026-05-09_case_012_append.md` — case_012 V49-V53 (collision)
- `case_kickoff_prompt_template.md` § "Hard guardrails" — proposed insertion
- DEC-V61-198 — strategic philosophy SSOT
