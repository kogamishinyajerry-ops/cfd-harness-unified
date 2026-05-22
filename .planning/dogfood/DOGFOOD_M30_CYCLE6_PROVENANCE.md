# DOGFOOD · M3.0 Cycle 6 · decide() provenance audit_v2 log

**DEC**: `2026-05-23_v61_202_sub_m30_cycle6_provenance_audit_v2.md` (Accepted)
**Date**: 2026-05-23
**Dogfood script**: `scripts/dogfood/case_007_cycle6_provenance.py`
**Verdict**: **PASS** (7/7 checks · all-PASS gate)
**Codex**: R0 = 3 findings (2 P2 + 1 P3, 0 P1) · R1 = APPROVE · 2 rounds.
**Push-review** (M3.0 close-batch) caught 1 additional P2: passive
refetch dedup by state_sha (cycle 6 log was overcounting React Query
revalidations). Fix landed in close-batch commit; 12/12 unit tests PASS.

---

## What this cycle adds

A fire-and-forget JSONL audit log for every `decide(CaseState) → WorkbenchFrame`
call, written to `ui/backend/user_drafts/audit_v2/<case_id>/decisions.jsonl`.
One record per call captures the **input state** (`step`, `focus_patch`,
`state_sha`, `manifest_state_sha`) and **the choices decide() made** (rail
primary kind/title, topbar CTA kind/target_step/enabled, bottom card count
+ severities, viewport overlay count).

Purpose: post-hoc retro of *"what did the workbench tell engineer Y at
time T — and was that the right thing to say?"*. This is the foundational
data layer for the cycle-7 junior-engineer beginner test plus future
calibration retros on the SSOT 4 UI-content drivers.

---

## Litmus alignment (DEC-V61-202 charter)

| Litmus pressure point | Coverage |
|---|---|
| Engineer-side: workbench surfaces the **right** next decision | The log captures **what was surfaced** so we can audit whether decide() drove the engineer to the right field at the right step |
| AI-side: AI stays **advisory-only**, not driver | Provenance log = pure audit; AI does not read it during decide() — V130 four-question gate intact |
| Truth chain: artifacts as truth, not chat history | Log uses `state_sha` + `manifest_state_sha` from the frame, anchored to the same content hashes the workbench computes |

---

## Checks (verbatim from the dogfood script · all PASS)

```
=== Cycle 6 provenance dogfood ===

  [PASS] Log file created at expected path
  [PASS] Log has exactly 5 lines (one per frame call)
  [PASS] All log lines parse as valid JSON
  [PASS] state_sha + manifest_state_sha on lines match frames
  [PASS] focus_patch captured per-line (set / null faithful)
  [PASS] Schema fields present (rail_primary.kind / topbar_cta.kind / bottom_card_count)
  [PASS] replay_decisions.py reads the log and prints a header

Verdict: PASS
```

### What each check actually proves

| Check | What it locks in |
|---|---|
| Log file at documented path | The path contract `audit_v2/<safe_case_id>/decisions.jsonl` holds, including the `_safe_case_id` sanitizer normalisation |
| 5 lines for 5 calls | No write loss; no double-write; one record per `decide()` invocation as advertised |
| All lines parse | JSONL discipline holds under append-only writes; never produces partial / corrupted records (the `json.dumps` + single-write in `log_decision` is correct) |
| `state_sha` + `manifest_state_sha` match frame | The log isn't drifting from the frame — what's logged is exactly what was returned to the UI |
| `focus_patch` faithful (inlet / outlet / null) | The most volatile of the 4 SSOT drivers round-trips through the log without coercion |
| Schema fields present | Replay tooling has the shape it expects; future retros won't trip on missing keys |
| Reader smoke | `scripts/audit_v2/replay_decisions.py` round-trips the format end-to-end |

---

## Test coverage delta

`ui/backend/tests/test_workbench_decide_provenance.py` — **11 / 11 PASS** (8 at R0 + 3 R1 regressions):
1. JSONL line parseable with the schema fields actually used by the writer
2. Multiple calls append, don't overwrite
3. `focus_patch` captured when set, `null` when absent
4. Failing log write does **not** break `decide()` (fire-and-forget contract)
5. Every line is independently valid JSON (no corruption under writes)
6. `WORKBENCH_PROVENANCE_DISABLED=1` short-circuits the writer
7. Case-id sanitization blocks path-traversal (`../etc/passwd` → `.._etc_passwd`)
8. `bottom_card_severities` captured

Plus an autouse conftest fixture
(`ui/backend/tests/conftest.py::_disable_workbench_provenance_by_default`)
sets the disable flag for the whole suite, so the rest of the backend tests
don't accidentally start writing audit files into the working tree.

---

## Security posture

- `_safe_case_id`: regex `[^a-zA-Z0-9_\-.]` → `_`; explicit reject of pure-dot
  names (`{"", ".", ".."}` and `set(safe) == {"."}`), replacing with a
  hashed `_invalid_<hash>` directory so a traversal probe can never resolve
  to `audit_v2/..` or `audit_v2/.`.
- `decide()` wraps `log_decision()` in `try/except: pass` as defense in
  depth — even if the sanitizer one day had a hole, the frame returns.
- `log_decision()` itself swallows every exception and warns; no probe
  signal leaks to the UI.

---

## Replay reader UX

`python3 scripts/audit_v2/replay_decisions.py <case_id> [--field PATH]
[--limit N] [--audit-dir DIR]`

Default compact view:
```
TIMESTAMP                      | STEP | FOCUS    | RAIL.KIND     | RAIL.TITLE                                    | TOPBAR.KIND   | CARDS
```

With `--field rail_primary.title` it dumps just that dotted field per line
— used by future retros for grep-style "show me every decision the
workbench made about the inlet patch on this case".

---

## What this does **not** prove (carry forward to cycle 7)

- Whether the rail/topbar/cards the workbench actually surfaced are the
  *right* ones. This cycle only proves we can audit what it did surface;
  the rightness audit is cycle 7's junior-engineer beginner test.
- Long-term durability under thousands of writes (single-line writes are
  atomic on POSIX append at typical record sizes, but we haven't stress-
  tested a 1M-line log).
- Log rotation / archival. Out of scope; cycle 7 may surface that need.

---

## Bottom line

The provenance plumbing is in. Every `decide()` call now leaves an audit
trail. Cycle 7 can lean on this log to test the litmus directly: have a
junior engineer drive the workbench end-to-end on case_007, then replay
the log and ask "did the workbench actually steer them toward the right
next decision at each step?".
