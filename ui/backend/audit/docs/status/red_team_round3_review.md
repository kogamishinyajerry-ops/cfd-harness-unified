# Red Team Review — Round 3 (Meta scan of T1-F-01 + T1-F-02 fix)

- **Scope:** the fix landed under `agent_events.jsonl[REDTEAM-T1-F01-F02-FIX-20260520]` (2026-05-20). Specifically:
  - `tools/cwos_render_dashboard.py`: `_parse_frontmatter` (yaml.safe_load), `derive_bright_spots`, `_evidence_paths_exist`, `count_phantom_evidence_pass_events`, Integrity Checks new row
  - `tests/test_red_team_safety.py`: 7 new test cases
- **Reviewer:** test-red-team (meta pass)
- **Verdict on round-3 stated scope (close T1-F-01 + T1-F-02 for the documented attack):** **PASS** — both addressed.
- **Verdict on round-3 mechanism quality:** **FAIL** — introduced a HIGH-severity bypass (R3-F-01) in the very code that was supposed to close the phantom-evidence hole. The fix is leaky at the same severity class as the issue it claimed to fix.

> Pattern matches round-2: scope met, but the fix added new attack surface. Do not promote round-3 to "done" without fixing R3-F-01.

---

## 1. New findings

### R3-F-01 — Path traversal in `_evidence_paths_exist` bypasses the phantom filter. **HIGH (effectively CRITICAL given it defeats the round-3 promise).**

**Evidence:** `tools/cwos_render_dashboard.py`:

```python
def _evidence_paths_exist(event: Dict[str, Any], repo_root: Path) -> bool:
    return all((repo_root / rel).exists() for rel in event.get("evidence", []))
```

`pathlib.Path("/repo") / "/etc/hosts"` returns `Path("/etc/hosts")` — pathlib drops the left operand when the right is absolute. So any evidence entry that is either:

- an **absolute path** to a real file outside the repo (e.g. `/etc/hosts`, `/Users/.../some-real-file`), OR
- a **`..` traversal** that escapes `repo_root` (e.g. `../../../etc/hosts`)

will `.exists()` against a real-but-irrelevant system file and pass the filter.

**Live repro (performed during this review):**

```
=== R3-F-01: path traversal in _evidence_paths_exist ===

  Path(repo) / "/etc/passwd" = /etc/passwd
  exists? True

  Phantom event with evidence=["/etc/hosts"]:
    bright_spots displayed: 1  (should be 0)
    phantom_count: 0  (should be 1)

  Phantom event with evidence=["../../../../etc/hosts"]:
    bright_spots displayed: 1  (should be 0)
    phantom_count: 0  (should be 1)
```

Both attacks defeat the phantom check. The cockpit happily shows the phantom event AND reports `phantom_count: 0` — the integrity counter lies about the lie.

**Same flaw is also present in the round-1 safety test** `tests/test_red_team_safety.py::test_pass_event_evidence_paths_exist_on_disk`:

```python
for rel in e.get("evidence", []):
    if not (repo_root / rel).exists():
        offenders.append(...)
```

Same pattern → same vulnerability. The round-3 fix copied this pattern unchanged. So **two checkpoints (test + cockpit) are both bypassed by the same trick.**

**Fix:** in both places, require the resolved evidence path to be (a) relative, and (b) contained within `repo_root` after resolution. Reject absolute paths and `..`-escapes explicitly.

```python
def _evidence_path_is_safe_and_exists(rel: str, repo_root: Path) -> bool:
    if Path(rel).is_absolute():
        return False
    try:
        full = (repo_root / rel).resolve()
        full.relative_to(repo_root.resolve())  # raises if outside
    except (ValueError, OSError):
        return False
    return full.exists()
```

Then add 2 new pytest cases: one for absolute path, one for `..` traversal. Both should FAIL today and PASS after the fix.

---

### R3-F-02 — Pipe character in agent `description` breaks the cockpit Agent Matrix table. **MEDIUM (pre-existing exposure, round-3 did not add protection).**

**Evidence:** `derive_agent_matrix` puts the raw description string directly into a markdown table cell:

```python
lines.append(f"| `{name}` | {short} | `{rel}` |")
```

If an agent file's frontmatter is `description: "Reviews | injects | columns"`, the rendered row becomes:

```
| `evil` | Reviews | injects | columns | path |
```

A 3-column table row turned into a 6-column row. Markdown renderers parse this as an extra-wide row, downstream rows align wrong, the whole Agent Matrix becomes garbage.

**Status:** none of the current 13 agent files contain pipes. So the cockpit currently renders fine. But round-2 (cockpit derivation) made this possible by reading whatever the file says, and round-3 (yaml.safe_load) preserved that exposure.

**Fix:** in `derive_agent_matrix`, escape pipes (`|` → `\|`) and collapse whitespace before placing into the cell.

---

### R3-F-03 — Block-scalar description (newlines) breaks Agent Matrix row. **MEDIUM (newly possible after round-3 yaml.safe_load).**

**Evidence:** before round-3, the old hand-rolled `_parse_frontmatter` would collapse `description: |` into the literal pipe character. The cockpit would show description as `|` — visibly wrong, but the table layout stayed intact.

After round-3, `yaml.safe_load` correctly parses block scalars and returns multi-line strings. The cockpit then puts the multi-line string into a table cell:

```
| `multiline` | First line of description
Second line that should NOT appear in table cell | path |
```

The newline splits the markdown row across physical lines, breaking the table.

**Live repro confirmed.**

**Fix:** in `derive_agent_matrix`, replace newlines with spaces before placing into the cell (and apply with same pipe-escape from R3-F-02). The 140-char truncation happens after.

---

### R3-F-04 — `phantom_evidence_count` is display-only; doesn't gate `overall_status`. **LOW.**

**Evidence:** `tools/cwos_render_dashboard.py:render_md` computes and displays `phantom_evidence_count` in the Integrity Checks section. But `tools/cwos_status.py` computes `overall_status` from mocked/real counts and `pass_without_evidence`, NOT from phantom-evidence count.

So a cockpit with `phantom_count: 5` could still show `Overall Status: GREEN` if all other gates pass. The phantom integrity-check line says `(must be 0)` but the system doesn't actually enforce it.

Same flavor as the pre-existing display-vs-aggregation gap on `pass_without_evidence` (which the cockpit DOES factor into the RED override — let me verify…). Actually let me check.

Looking at `cwos_status.py`:
```python
if ev_sum["pass_without_evidence"]:
    overall = "RED"
```

So pass_without_evidence DOES force RED. But phantom count is computed only in render_dashboard, not in cwos_status. The cockpit displays the count but the project_status.json overall_status never sees it.

**Fix:** move phantom counting into `cwos_status.py` so the metric is part of `project_status.json`, and add the RED override there. Render layer keeps just the display.

---

### R3-F-05 — Round-1 safety test propagates the same path-traversal flaw. **HIGH (counterpart to R3-F-01).**

**Evidence:** `tests/test_red_team_safety.py::test_pass_event_evidence_paths_exist_on_disk` uses identical `(repo_root / rel).exists()` logic. A PASS event with absolute-path or `..`-traversal evidence would silently pass this test too. The test is co-defective with the cockpit filter.

**This is the most embarrassing finding:** the safety test that was supposed to catch F-08 is itself defeated by the same trick that defeats T1-F-01's fix. The "safety net" has the same hole as the surface it was guarding.

**Fix:** same as R3-F-01 — apply the `is_absolute() / relative_to(repo_root)` guard in both places.

---

## 2. What round-3 got right

To balance the review:

- **T1-F-02 (yaml.safe_load) is genuinely solid.** All 13 agent files parse correctly. Multi-line, colon-in-value, garbage input handled. Real-agent smoke test catches future drift. 5 of 5 yaml tests pass meaningfully.

- **T1-F-01 closes the *documented* attack.** Relative-path phantom evidence (the demo from round-2: `evidence: ["this/file/does/not/exist.py"]`) is correctly filtered. The bypass only emerges with absolute or `..` paths, which is a stronger attack model than the original demo.

- **Phantom counter integrated into Integrity Checks** is the right ergonomics — putting the count next to "PASS events without evidence" makes the failure modes side-by-side comparable.

---

## 3. Pre-existing findings re-confirmed (still open)

These were noted in earlier reviews and remain unaddressed; they are not new to round-3 but their priority is now visible against the freshly-introduced R3-F-01.

| id | one-line | from |
|---|---|---|
| F-04..F-08 | five HIGH findings on CLI/manifest/event integrity | original bootstrap review |
| F-09..F-14 | six MEDIUM findings on hygiene/architecture/schema | original bootstrap review |
| T1-F-03 | schema validates on write, not on read | round-2 review |
| T1-F-04 | retroactive events have no schema marker | round-2 review |
| T1-F-05 | self-certification persists | round-2 review |

---

## 4. Recommendation

**Verdict on round-3:** mixed.
- T1-F-01 + T1-F-02 closed for the documented attacks ✓
- R3-F-01 introduced a stronger-attack-model bypass in the same file ✗
- R3-F-05 reveals the round-1 safety test had the same flaw all along ✗
- R3-F-02 / R3-F-03 expose markdown injection in the cockpit table renderer ✗
- R3-F-04 is the display-vs-aggregation pattern again ✗

**Required next step (single small batch, do this before anything else):**

1. **Tighten `_evidence_paths_exist`** to reject absolute paths and out-of-repo resolutions. Apply the same guard in `test_pass_event_evidence_paths_exist_on_disk`. Closes R3-F-01 + R3-F-05.
2. **Add 4 pytest cases**: (a) absolute-path evidence is rejected; (b) `..`-traversal evidence is rejected; (c) safe relative path is accepted; (d) symlink escape is rejected.
3. **Sanitize Agent Matrix cells**: pipe-escape + newline-flatten before truncation. Closes R3-F-02 + R3-F-03.
4. **Add 2 pytest cases**: pipe in description renders to escaped pipe; newline collapsed to space.
5. **Optionally move phantom-counting into `cwos_status.py`** and let it override overall_status to RED if phantom_count > 0. Closes R3-F-04.

Estimated size: ~30 LOC + 6 tests. Smaller than round-3 was.

**Do NOT** proceed to Tier-2 or Phase 1 until R3-F-01 is closed. Path traversal in a trust harness is exactly the failure mode the project was built to refuse.

**Do NOT** call this round "done" yet. The round-3 fix as it stands moves the attack surface from "naive phantom" (round-2) to "sophisticated phantom" (round-3) without raising the cost meaningfully. A 1-line tweak from an attacker still bypasses the integrity check.
