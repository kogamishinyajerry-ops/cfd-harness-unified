# Red Team Round-12 Review — R11 γ-fix Meta Scan

**Scope:** adversarial probe of the round-11 γ batch (docstring rewrite, frozenset fence upgrade, schema `^\S` pattern, R-17 step-2 gate entry).
**Author:** test-red-team agent.
**Date:** 2026-05-20.
**Previous round:** `red_team_round11_review.md` (FAIL, 4 LOW).
**Verdict:** FAIL — 3 LOW. **No HIGH, no MED.** Findings are all edge-case input validation in the schema; defense-in-depth holds.

---

## Method

Seven probes against the γ surfaces:

| # | Probe                                                                                          | Expected           | Observed                  |
|---|------------------------------------------------------------------------------------------------|--------------------|---------------------------|
| 1 | Trailing whitespace `"real-image:tag   "`                                                      | reject at schema   | **accepted at schema**    |
| 2a | Leading zero-width space `​ image:tag`                                                   | reject at schema   | **accepted at schema**    |
| 2b | Leading non-breaking space ` image:tag`                                                  | reject at schema   | rejected ✓                |
| 2c | Leading line separator ` image:tag`                                                       | reject at schema   | rejected ✓                |
| 3 | Embedded newline `"image:tag\nrm -rf /"` (injection-style)                                     | reject at schema   | **accepted at schema** (subprocess list-form prevents exploit) |
| 4 | Frozenset fence with `known_good = frozenset()` (someone empties it during refactor)           | test fails closed  | fails closed ✓            |
| 5 | Frozenset fence with `DEFAULT_IMAGE` in both `known_good` AND `known_typos` (paradox)         | test fails closed  | fails closed (typo check fires first) ✓ |

Three of seven surfaced edge cases. All three are schema permissiveness for input that wouldn't actually exploit anything (subprocess list-form + docker's own image-name rejection are the downstream defenses). None are MED-or-higher.

---

## Findings

### R12-F-01 — LOW — schema accepts `solver_docker_image` with trailing whitespace

**File:** `src/cfdtrust/schemas/case_manifest.schema.json` — `solver_docker_image` pattern `"^\\S"`.

The `^\S` regex anchors to the first character. `"real-image:tag   "` (3 trailing spaces) starts with a non-whitespace, so passes. The adapter's `image.strip()` check is similarly satisfied (`"real-image:tag"` is truthy). The string reaches `subprocess.run(["docker", "image", "inspect", "real-image:tag   "])` and docker rejects with "invalid reference format".

**Live reproduction:**

```bash
$ raw['solver_docker_image'] = 'real-image:tag   '
$ validate_manifest(case)
→ ACCEPTS "real-image:tag   "
```

**Severity LOW — schema permissiveness, no exploit.** The user-facing outcome is correct (BLOCKED at docker layer). But R11-F-03 was framed as "the schema should reject garbage at validation time"; trailing whitespace is a kind of garbage. Belt is loose, suspenders hold.

**Fix sketch:** tighten pattern to `"^\\S(?:.*\\S)?$"` (must start AND end with non-whitespace). Or accept trailing whitespace as benign and document the rationale.

### R12-F-02 — LOW — leading U+200B zero-width space passes schema; other Unicode whitespace caught

**File:** same.

Python's `re` `\s` matches ASCII whitespace + most Unicode whitespace classes by default. But U+200B (ZERO WIDTH SPACE) is in Unicode category `Cf` (format), NOT `Zs` (space separator), so `\s` does not match it. Live:

```
U+200B leading      : schema ACCEPTS  (repr='​image:tag')   ← MISS
U+00A0 leading      : schema REJECTS  (non-breaking space, Zs)
U+2028 leading      : schema REJECTS  (line separator, Zl)
```

**Severity LOW — exotic input class, defense-in-depth holds.** A zero-width-space at position 0 of an image name is extremely unlikely to occur except via copy-paste accident (some IDE/editor inserts ZWSP) or deliberate evasion. Docker would still reject the image name. The cockpit's BLOCKED reason would just be `openfoam_image_not_pulled` instead of `manifest_invalid_solver_docker_image` — slightly less informative.

**Fix sketch:** add ZWSP-class chars to the regex: `"^[^\\s\\u200B-\\u200F\\uFEFF]"`. Or just leave it — the visible behavior is correct.

### R12-F-03 — LOW — schema accepts image string with embedded newline

**File:** same.

`"image:tag\nrm -rf /"` passes `^\S` because the first char is `i`. The minLength check passes. So the manifest validates. Subprocess receives the literal string:

```python
subprocess.run(["docker", "image", "inspect", "image:tag\nrm -rf /"], ...)
```

Because args is a list (not a shell string), the entire 22-character string is passed as ONE positional arg to docker. Docker rejects: "invalid reference format". No command execution occurs.

**Severity LOW — looks scary, fully neutralized.** The list-form subprocess is doing the heavy lifting here, exactly as designed. Schema accepting newline-bearing strings is sub-ideal but not exploitable.

**Fix sketch:** stricter pattern that prohibits control characters: `"^\\S[^\\n\\r\\t\\f\\v]*$"`. Or accept that the next layer (docker) is the right place to enforce image-name structure.

---

## What I tried that did NOT break

- **Fence empty-frozenset robustness**: removing all entries from `known_good` causes the test to fail closed. The test's docstring instructs maintainers to add via the `known_good = frozenset({...})` literal; an accidental empty doesn't pass silently. Fail-closed design is correct.
- **Fence paradox robustness**: if a maintainer puts `DEFAULT_IMAGE` in both `known_good` AND `known_typos` (mistakenly classifying a good image as a typo, or vice versa), the typo check fires first and the test fails. Inconsistency surfaces immediately. Good.
- **Schema regex against most Unicode whitespace**: ` ` (non-breaking space), ` ` (line separator), ` ` (paragraph separator) all REJECTED — Python `\s` covers Unicode Zs / Zl / Zp categories by default. Only the Cf-category ZWSP escapes (R12-F-02).
- **The R11-F-03 happy path**: `"openfoam/openfoam11-paraview510:latest"` (the legit default) passes both schema and adapter, no regression on the normal flow.
- **The R-17 entry's visibility**: `grep -n R-17 RISK_REGISTER.md` returns the new line; it'll show up in any text search of risks, ensuring step-2 design picks it up.

---

## Cumulative severity trend

| Round                       | CRIT | HIGH | MED | LOW | Total |
|-----------------------------|------|------|-----|-----|-------|
| 1 (bootstrap)               | 3    | 5    | 6   | 2   | 16    |
| 2 (Tier-1 meta)             | 0    | 1    | 4   | 2   | 7     |
| 3 (T1 fix meta)             | 1    | 1    | 2   | 1   | 5     |
| 4 (R3 batch w/ helper)      | 0    | 0    | 0   | 0   | 0     |
| 5 meta                      | 0    | 0    | 3   | 3   | 6     |
| 5 fix (α)                   | 0    | 0    | 0   | 0   | 0     |
| Tier-2 (β) self-check       | 0    | 0    | 0   | 0   | 0     |
| 6 (Tier-2 meta)             | 0    | 0    | 1   | 1   | 2     |
| 6 fix (α)                   | 0    | 0    | 0   | 0   | 0     |
| 7 (α meta)                  | 0    | 0    | 0   | 2   | 2     |
| 7 fix (β)                   | 0    | 0    | 0   | 0   | 0     |
| 8 (β meta)                  | 0    | 0    | 0   | 2   | 2     |
| 8 fix (β SSOT)              | 0    | 0    | 0   | 0   | 0     |
| 9 (β SSOT meta)             | 0    | 0    | 0   | 3   | 3     |
| Phase 1 step 1              | 0    | 0    | 0   | 0   | 0     |
| 10 (step 1 meta)            | 0    | 1    | 1   | 2   | 4     |
| 10 fix (γ)                  | 0    | 0    | 0   | 0   | 0     |
| 11 (γ meta)                 | 0    | 0    | 0   | 4   | 4     |
| 11 fix (γ)                  | 0    | 0    | 0   | 0   | 0     |
| **12 (γ meta)**             | **0**| **0**| **0**| **3**| **3** |

Severity trajectory:

```
Round 10 (new module):       1 HIGH + 1 MED + 2 LOW    (4 total)
Round 11 (small fixes #1):   0 HIGH + 0 MED + 4 LOW    (4 total)
Round 12 (small fixes #2):   0 HIGH + 0 MED + 3 LOW    (3 total)
```

R11 + R12 confirm the rolling-fix pattern: small commits → severity ceiling stays at LOW, count slowly drops. By round 13-14 we'd expect 0-1 LOW total (i.e., the first zero-finding round on the OpenFOAM adapter surface).

---

## Pattern observation — schema vs. subprocess defense layering

Three of three R12 findings live in the same architectural pattern:

**Schema layer (input validation)**: permissive on weird-but-not-exploit input.
**Adapter layer (`image.strip()`)**: catches one extra case (leading whitespace).
**Subprocess layer (list-form args)**: blocks all shell-injection vectors.
**Docker layer (image name parsing)**: rejects malformed image names.

Each finding is "the schema could have caught this earlier" — but the downstream layers DO catch it, and the user-facing outcome is always controlled BLOCKED. The honesty contract is preserved end-to-end.

This is actually the textbook defense-in-depth posture: the outermost layer is forgiving but the inner layers are strict. The cost of tightening the schema regex is a tiny gain in error-message specificity, not a security improvement.

For Phase 1 step 2 planning: this validates the design choice to use `subprocess.run(args=[list])` rather than `subprocess.run(shell=True, ...)`. The list-form is the actual defense; the schema is icing.

---

## Verdict

**FAIL** on the round-12 meta scan.

But — **none of the three R12 findings affect end-to-end correctness or security**. They are all "could the schema catch this earlier?" findings, and the answer is "yes but defense-in-depth catches it anyway."

The γ batch succeeded at closing R11-F-01..F-03 mechanically. R11-F-04 → R-17 in `RISK_REGISTER.md` is the right move (defers to step-2 design where the mount-strategy decision belongs).

---

## Recommended next options for the owner

1. **(α)** Fix R12-F-01 only — tighten pattern to `"^\\S(?:.*\\S)?$"` to reject both leading and trailing whitespace. ~5 min. Marginal value.
2. **(β)** Fix R12-F-01 + R12-F-03 — same regex change plus disallow control chars in image string. Both at once. ~10 min.
3. **(γ)** Document all three R12 LOWs as "schema permissiveness, accepted because defense-in-depth holds" — either in the schema's `description` field or as R-18..R-20 in `RISK_REGISTER.md`. Proceed to step 2. ~10 min. **Recommended.**
4. **(δ)** Start Phase 1 step 2 immediately; revisit R12 findings only if they manifest as user-visible regressions during step-2 dogfooding. Cheapest, but leaves the R12 findings undocumented.

My recommendation: **(γ)**. The pattern is clear: round 13 of polish would surface 1-2 more LOWs of the same character (schema permissiveness vs. defense-in-depth). The right move is to acknowledge the layering choice in the docs and move on to step 2 where the real value lives.

The step-2 work itself is what closes R-17 (the actual step-2 gate). Round 12 is a natural exit point from the polish loop.
