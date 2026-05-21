# Red Team Review — Round 5 (Meta scan of Round-4 fix)

- **Scope:** the round-4 fix landed under `agent_events.jsonl[REDTEAM-R3-FIX-20260520]`. Specifically:
  - new `tools/cwos_paths.py` (`path_is_safe_relative`, `evidence_paths_all_safe_and_exist`, `iter_pass_events_with_evidence`, `count_phantom_pass_events`)
  - `tools/cwos_render_dashboard.py` (importlib loader, `sanitize_table_cell`, refactored `derive_bright_spots` / `derive_agent_matrix`)
  - `tools/cwos_status.py` (importlib loader, phantom metric, RED override)
  - `tests/conftest.py` (tools/ on sys.path)
  - `tests/test_red_team_safety.py` (10 new tests)
- **Reviewer:** test-red-team (meta pass)
- **Verdict on round-4 stated scope (close R3-F-01..F-05):** **PASS** — verified live + via tests. The path-safety contract is structurally sound.
- **Verdict on round-4 mechanism quality:** **PASS with caveats** — three MEDIUM input-validation gaps and three LOW test/coverage gaps. No CRITICAL or HIGH bypass found. **First round since the bootstrap where the new findings are all MEDIUM-or-lower.**

> This is the smallest finding set so far. The "pattern break" of `cwos_paths.py` as single source of truth genuinely holds — the gaps below are all in *input validation completeness*, not in *algorithm correctness*.

---

## 1. Attack matrix run against `path_is_safe_relative`

Live ran 16 payload variants. Results:

| payload | verdict | expected | notes |
|---|---|---|---|
| `CLAUDE.md` | PASS | ok | ✓ |
| `src/cfdtrust/cli.py` | PASS | ok | ✓ |
| `/etc/hosts` | reject | reject | ✓ (R3-F-01 closed) |
| `../../../etc/hosts` | reject | reject | ✓ (R3-F-01 closed) |
| `..` | reject | reject | ✓ |
| `a/../b/CLAUDE.md` | reject | n/a | ✓ (doesn't exist) |
| `""` (empty string) | reject | reject | ✓ |
| `None` | reject | reject | ✓ |
| `123` (int) | reject | reject | ✓ |
| whitespace `"   "` | reject | reject | ✓ |
| `src\\cfdtrust\\cli.py` (Windows-style) | reject | reject | ✓ (unix treats `\` as literal char) |
| `src//cfdtrust/cli.py` | PASS | ok | ✓ (resolve normalizes) |
| **`.` (current dir)** | **PASS** | reject? | **R5-F-02** |
| **`CLAUDE.md/` (trailing slash on file)** | **PASS** | reject | **R5-F-03** |
| **`CLAUDE.md\x00evil` (null byte)** | **UNCAUGHT ValueError** | reject | **R5-F-01** |

Three payloads produced unexpected behavior. Details below.

---

## 2. New findings

### R5-F-01 — Null byte in evidence path crashes the safety check. **MEDIUM.**

**Evidence:** `Path.resolve()` calls `lstat()` which raises `ValueError` (not `OSError`) on null-byte filenames. `path_is_safe_relative` only catches `OSError`:

```python
try:
    resolved = candidate.resolve()
    resolved_root = repo_root.resolve()
except OSError as e:
    return False, f"resolve failed: {e}"
```

**Live repro:**
```
=== null byte handling ===
  UNCAUGHT: ValueError: lstat: embedded null character in path
```

A check function that *crashes* on malformed input is worse than one that *rejects* it: anywhere the check is called inside a comprehension or aggregation, the exception propagates and tears down the whole pipeline. `count_phantom_pass_events` would die mid-loop. The cockpit refresh fails. The "safe and exists" check turns into a denial-of-service primitive — any actor with write access to `agent_events.jsonl` can shoot down the cockpit by appending one tampered event.

**Fix:** widen the `except` to `(OSError, ValueError)`. Same one-line change.

### R5-F-02 — `evidence: ["."]` (the repo itself) passes as valid evidence. **MEDIUM.**

**Evidence:**
```
=== evidence "." (the repo itself) ===
  result: ok=True, reason=
  → an event claiming evidence=["."] is meaningless but passes
```

`(repo_root / ".").resolve() == repo_root.resolve()` and `repo_root.exists()` is True. So `evidence: ["."]` returns `(True, "")` — meaning a PASS event with this evidence would be accepted, appear in Bright Spots, and not trigger the phantom counter.

**Sub-issue (more dangerous variant):** `evidence_paths_all_safe_and_exist` iterates over its input. If a tampered event has `evidence: "."` (a JSON string, not a list — see schema gap R4-F-* below), the iterator yields one char `"."` and `all(...)` returns True. **The string-instead-of-list attack also succeeds**:

```
=== evidence is a string not a list ===
  evidence="CLAUDE.md" (string): all_safe=False
  → iterates over chars: each char is a 1-char "path" treated as evidence
```

But evidence="." (one-char string) WOULD pass because the single character `.` resolves to the repo. Reproducible.

**Threat model:** requires direct tamper of `agent_events.jsonl` (cwos_event.py's argparse forces a list via `nargs="*"`). Same threat model as F-13. Still a bypass at the verification layer.

**Fix:**
1. In `path_is_safe_relative`, reject paths that resolve to `repo_root` itself (only files *under* the repo count as evidence). Trivial: `if resolved == resolved_root: return False, "evidence cannot be the repo root itself"`.
2. In `evidence_paths_all_safe_and_exist`, type-check that `evidence` is a `list[str]`, not iterable-of-anything. Reject otherwise.

### R5-F-03 — `CLAUDE.md/` (trailing slash on a regular file) accepted as safe. **LOW.**

**Evidence:**
```
=== trailing slash on file ===
  result: ok=True, reason=
```

`(repo_root / "CLAUDE.md/").resolve()` returns `/path/to/repo/CLAUDE.md` (POSIX semantics: trailing slash on a regular file is tolerated). `.exists()` is True. So a path-spec that implies "this is a directory" passing the check is a minor type-confusion: the cockpit cell shows `CLAUDE.md/` which would mislead a reader into thinking the evidence is a directory.

**Threat:** purely cosmetic / type-disclosure. Not a privilege boundary. Low.

**Fix (optional):** add `if resolved.is_dir() and not rel.endswith("/"):` style check — but the cleaner version is just to require evidence be a regular file:

```python
if not resolved.is_file():
    return False, f"evidence must be a regular file: {rel}"
```

That also closes R5-F-02 (`.` resolves to a directory = repo root, not a file).

---

## 3. Test-coverage gaps from round-4

### R4-F-01 — `test_overall_status_red_when_phantom_count_positive` doesn't exercise the override. **MEDIUM.**

**Evidence:** the test body proves only that `cwos_paths.count_phantom_pass_events(...)` returns 1 for a phantom event. The RED-override conditional in `cwos_status.main`:

```python
if phantom_count > 0:
    overall = "RED"
```

…is not invoked by any automated test. It was verified live (manual phantom-event injection → cockpit went RED), but a future refactor that deletes the conditional would not be caught by `make bootstrap-check`.

**Fix:** refactor `cwos_status.main` to accept `events_log` and `output_path` kwargs (defaulting to module constants for back-compat). Add a test that calls `main(events_log=tmp_log, output_path=tmp_output)` against a tmp log with a phantom event, reads the produced JSON, asserts `overall_status == "RED"`. ~15 LOC + 1 test.

### R4-F-02 — Trust Loop Status table doesn't sanitize cells. **LOW.**

**Evidence:** in `render_md`:

```python
lines.append(
    f"| `{r.get('case_id')}` | {_status_emoji(r.get('overall_status',''))} {r.get('overall_status')} "
    f"| {r.get('solver_execution')} | {r.get('validation_status')} | `{r.get('path')}` |"
)
```

None of `case_id`, `path`, etc. go through `sanitize_table_cell`. `trust_report.schema.json` only requires `case_id: {"type": "string", "minLength": 1}` — no character constraints. A case named `"foo | bar"` would break this table the same way agent descriptions would break the Agent Matrix.

**Threat:** none today (current case is `flat_plate_rans_sst`). Cosmetic break of the cockpit if a future case_id has special chars.

**Fix:** apply `sanitize_table_cell` to each cell value. ~6 LOC.

### R4-F-03 — `project_status.json` structure not asserted for `metrics.phantom_evidence_pass_events`. **LOW.**

**Evidence:** `test_cwos_status_writes_project_status_json` asserts only that top-level keys `overall_status`, `phase`, `tasks`, `trust_reports` are present. The new `metrics.phantom_evidence_pass_events` field could be silently dropped in a refactor and this test would still pass.

**Fix:** extend the test to assert `data["metrics"]["phantom_evidence_pass_events"]` is an int and `data["overall_status"]` is one of {GREEN, AMBER, RED}. ~2 LOC.

---

## 4. What round-4 got right

- **Pattern break held**: the path-safety check exists in *exactly one place*. `cwos_paths.py` is the only file in the project that contains `(repo_root / rel).resolve()` followed by a containment check.
- **Algorithm is correct** for absolute paths, `..` traversal, and symlink escape — all three closed in round-4 and re-verified clean by this round-5 attack matrix.
- **RED override works** — live verified by injecting then removing a phantom event. Cockpit flips RED→AMBER as expected.
- **Sanitize handles its declared scope** — pipe and newline removed cleanly. Doesn't claim to handle every markdown special char and shouldn't.
- **Defensive type rejection works** — `None`, `int`, empty string, whitespace, Windows separators all rejected (different messages, all `(False, ...)` returns).

## 5. Pattern observations

Compare findings-per-round:

| round | new findings | severities | notes |
|---|---|---|---|
| 1 (bootstrap) | 16 | 3C / 5H / 6M / 2L | original review of bootstrap |
| 2 (T1 = close C-findings) | 7 | 1H / 4M / 2L | introduced T1-F-01 etc. |
| 3 (T1-F-01/F-02 = HIGH closure) | 5 | 1H / 2M / 1L + R3-F-05 | introduced R3-F-01 (path traversal) |
| 4 (R3-F-* batch + helper extract) | 0 known | n/a | this review |
| **5 (meta of round 4)** | **6** | **0H / 3M / 3L** | **first round with no HIGH** |

**Severity is monotonically decreasing.** Round 1 had CRITICAL findings; round 5 has none above MEDIUM. The pattern of "each round introduces a same-severity bypass" is broken.

The three R5-F-* findings are real but small — input-validation completeness rather than algorithm flaws. Closing them is ~15 LOC + 4 tests.

---

## 6. Recommendation

**Verdict on round-4:** PASS on stated scope. PASS-with-caveats on mechanism quality.

**Three options for the next move, in roughly equal-merit order:**

**Option α — Land a small "R5 batch" (~25 LOC + 4 tests):**
- R5-F-01: catch `ValueError` in addition to `OSError`
- R5-F-02: require `resolved.is_file()` (closes both repo-itself and string-iteration variant)
- R4-F-01: refactor `cwos_status.main` to take kwargs + add RED-override test
- Defer R5-F-03, R4-F-02, R4-F-03 (all LOW cosmetic/coverage gaps)

This makes round-5 the first "everything green" round. Worth aiming for.

**Option β — Accept R5-F-* as known LOW-MEDIUM and advance to Tier-2 (F-04..F-08 from the original review).** Five HIGH findings on CLI exit codes, manifest/adapter coupling, audit/run separation, cwos_event agent allowlist, and write-time evidence-path check. Higher absolute impact than polishing R5-F-* would be.

**Option γ — Stop the meta-recursion deliberately and advance to Phase 1 (real OpenFOAM adapter)** with R5-F-* + Tier-2 as documented residual. **Red Team continues to advise against this** — Tier-2's F-04 (manifest declares openfoam but mocked silently substitutes) is exactly the kind of false-pass surface that becomes more dangerous when a real solver enters the picture. The mocked-vs-real coupling needs to be tight before Phase 1.

---

## 7. Net assessment

Round 4 is the cleanest round of work in the project to date. The architectural choice — one shared contract instead of duplicated checks — is what closed the per-round-introduces-new-bypass pattern. The remaining gaps are no longer the "I left the door wide open" kind; they are the "the door is solid but the hinges have one missing screw" kind. Real, fixable, no longer scary.

**Suggested next step:** option **α** — small R5 batch — because:
- it's the first plausibly-end-state milestone for the trust-mechanism layer
- it tests the architectural pattern by exercising it once more without expanding scope
- closing R4-F-01 (RED-override test) is genuinely valuable: the override is the project's primary "the cockpit cannot lie" enforcement

Then option β (Tier-2). Phase 1 only after Tier-2.
