# Red Team Round-11 Review — γ-fix Meta Scan

**Scope:** adversarial probe of the round-10 γ batch (R10-F-01 image tag fix + R10-F-02 schema/adapter double-fence + R10-F-03/R10-F-04 case_dir symlink guards).
**Author:** test-red-team agent.
**Date:** 2026-05-20.
**Previous round:** `red_team_round10_review.md` (FAIL, 1 HIGH + 1 MED + 2 LOW).
**Verdict:** FAIL — 4 LOW. **No HIGH, no MEDIUM** — severity ceiling back to LOW after the γ HIGH was closed.

---

## Method

Six probes against the new code surface introduced by γ:

| # | Probe                                                                          | Expected            | Observed |
|---|--------------------------------------------------------------------------------|---------------------|----------|
| 1 | Schema accepts whitespace-only `solver_docker_image: "   "`, adapter rejects   | reject in both      | **schema accepts; only adapter rejects (drift)** |
| 2 | Regression fence catches future typo `paraview511` / `paraview513` / `paraview500` | catches             | **misses 3/4** |
| 3 | Docstring lists all 5 BLOCKED reasons after γ added `manifest_invalid_...`     | listed              | **only 4 listed (drift)** |
| 4 | Symlink at depth 2: `case_dir/system/sneaky_subpath → /tmp/host`               | rejected            | **passes (`is_dir`/`is_symlink` only inspects depth 1)** |
| 5 | Empty string `solver_docker_image: ""` — schema reject path                    | rejected            | rejected ✓ |
| 6 | Subprocess argument injection via crafted image string                         | safe (list-form)    | safe ✓ |

Four of six surfaced findings. None are MED-or-higher; all are documentation drift, fence breadth, or contract drift that doesn't allow false PASS.

---

## Findings

### R11-F-01 — LOW — docstring drift after γ added a 5th BLOCKED reason

**File:** `src/cfdtrust/backends/openfoam.py:9-16` (header docstring).

```python
  Step 1 (this commit): environment-detection layer + structured BLOCKED states.
  Returns BLOCKED with one of four explicit reasons:
    - `docker_not_available`
    - `openfoam_image_not_pulled`
    - `case_dir_not_openfoam_compatible` — missing `system/`, `constant/`, or `0/`
    - `execution_not_implemented_yet`
```

γ added a 5th BLOCKED reason — `manifest_invalid_solver_docker_image` — and changed `case_dir_not_openfoam_compatible` to also fire on symlinks. The header docstring still says "four" reasons and still describes the case-dir reason as "missing... `0/`" with no mention of symlink rejection.

A future maintainer reading the docstring would not know the symlink contract exists, may remove the `is_symlink()` guard during a refactor as "redundant," and re-open R10-F-03 / R10-F-04.

**Severity LOW — documentation drift, not exploit.** Fix is a one-paragraph docstring edit.

### R11-F-02 — LOW — regression fence catches only the exact known typo, not the class

**File:** `tests/test_red_team_safety.py` — `test_openfoam_default_image_tag_is_not_the_known_typo`.

```python
assert "paraview512" not in ofa.DEFAULT_IMAGE
```

Catches: `paraview512` typo.
Misses (live-probed): `paraview511`, `paraview513`, `openfoam12-paraview510` (wrong OpenFOAM major).

```
openfoam/openfoam11-paraview511:latest  → fence does not catch
openfoam/openfoam11-paraview513:latest  → fence does not catch
openfoam/openfoam12-paraview510:latest  → fence does not catch
totally-unrelated:tag                   → fence catches (different namespace)
```

The opt-in network test (`CFDTRUST_LIVE_NETWORK_TESTS=1`) catches every wrong tag, but a default CI run does not. A future "let me bump paraview to 5.11" patch could ship without anyone running the opt-in.

**Stronger fence (no network needed):**

```python
_KNOWN_GOOD_DEFAULT_IMAGES = frozenset({
    "openfoam/openfoam11-paraview510:latest",
})
assert ofa.DEFAULT_IMAGE in _KNOWN_GOOD_DEFAULT_IMAGES, (
    f"DEFAULT_IMAGE not on the known-good list. If you intentionally bumped "
    f"the image, add it to _KNOWN_GOOD_DEFAULT_IMAGES AND verify "
    f"`docker manifest inspect {ofa.DEFAULT_IMAGE}` succeeds against real Hub."
)
```

This forces any change to the constant through a friction step: edit the test AND verify the new tag against Hub. Same protection as the network test, no network cost in CI.

**Severity LOW — coverage gap, not failure.** The honesty contract still holds via the opt-in test; only the default-CI early-warning is weaker than it could be.

### R11-F-03 — LOW — schema accepts whitespace-only `solver_docker_image`, adapter rejects

**Files:**
- `src/cfdtrust/schemas/case_manifest.schema.json:30-34`
- `src/cfdtrust/backends/openfoam.py:120-138`

Schema:

```json
"solver_docker_image": { "type": "string", "minLength": 1 }
```

`"   "` (three spaces) passes (`type` is string, `len > 0`). The adapter then catches it:

```python
if not isinstance(image, str) or not image.strip():
    return {"status": "BLOCKED", "details": {"reason": "manifest_invalid_solver_docker_image", ...}}
```

Live:

```
schema accepts whitespace-only:  YES (len("   ") = 3)
adapter on whitespace-only:      status=BLOCKED, reason=manifest_invalid_solver_docker_image
```

The user-facing outcome is correct (BLOCKED), but the layer boundary is messy: the schema's job is to make invalid manifests fail at validation, and a whitespace-only image is invalid in the only sense that matters. The adapter has to repeat the check.

**Fix:** add a regex constraint to the schema:

```json
"solver_docker_image": {
  "type": "string",
  "minLength": 1,
  "pattern": "^\\S"
}
```

The `^\\S` (must start with a non-whitespace) is a minimal sieve. A stricter pattern like `^[a-zA-Z0-9][a-zA-Z0-9._/-]*(:[a-zA-Z0-9._-]+)?$` would also reject path traversal-shaped strings, but is over-eager for an image-name field.

**Severity LOW — adapter still rejects, but the schema/adapter contract drifts.** Belt-and-suspenders is fine; an inconsistency where the belt is loose but the suspenders hold is a weak signal worth fixing.

### R11-F-04 — LOW (now) / HIGH at step 2 — symlinks at depth 2+ bypass the case_dir check

**File:** `src/cfdtrust/backends/openfoam.py:_is_openfoam_compatible_case_dir`.

The guard checks `case_dir.is_symlink()` AND each of `(case_dir / "system")`, `(case_dir / "constant")`, `(case_dir / "0")` for `is_symlink()`. **It does NOT recurse.**

Live reproduction:

```bash
$ mkdir -p /tmp/r11-case/{system,constant,0} /tmp/r11-out
$ touch /tmp/r11-out/.secret
$ ln -s /tmp/r11-out /tmp/r11-case/system/sneaky_subpath

>>> ofa._is_openfoam_compatible_case_dir(Path('/tmp/r11-case'))
(True, '')
```

Step-1-only consequence: none — adapter returns `execution_not_implemented_yet` regardless.

**Step-2 consequence**: when the step-2 wiring does `docker run --volume <case_dir>:/case ...`, OpenFOAM's solver runtime will encounter `/case/system/sneaky_subpath/`, follow the symlink, and read/write to `/tmp/r11-out/` on the HOST. This is the same R10-F-03 vector at one level of nesting deeper.

**Why this is LOW now**: step 2 hasn't shipped. The probe demonstrates the gap, not an exploit.
**Why this becomes HIGH at step 2**: the moment `docker run --volume` lands, this is exactly the host-fs-write primitive R10-F-03/F-04 were closed to prevent.

**Fix sketch (apply BEFORE step 2 lands, not after):**

```python
def _has_symlink_descendant(case_dir: Path) -> Tuple[bool, str]:
    """Recursively walk `case_dir`; bail at the first symlink found."""
    for p in case_dir.rglob("*"):
        if p.is_symlink():
            return True, str(p.relative_to(case_dir))
    return False, ""
```

Concern: `rglob` on a large case dir (post-mesh) can be slow. Mitigation: cap to first match (early return) and document the perf budget; or restrict the recursion depth (e.g., `os.walk` with depth cap matching OpenFOAM case structure).

Alternative: rely on `docker run --read-only` for the case dir mount (block writes) + accept that reads of host-fs files into the container are tolerable. This shifts the boundary from "filesystem isolation" to "host-fs is read-only from container." Different security posture; needs explicit decision.

For the round-11 fix recommendation: punt to step 2 design discussion. The defense surface is non-trivial.

---

## What I tried that did NOT break

- **Empty string image (`""`)**: schema rejects with `'' should be non-empty` (schema's own message). Confirms `minLength: 1` works for length-0 case. Distinct from the whitespace-only R11-F-03.
- **Subprocess argument injection** (`"image; rm -rf /"`, `"$(whoami)"`, `"image\nrm"`): subprocess.run with `args=[...]` list form is safe by construction — docker receives the literal string and rejects as invalid image name. No shell interpolation. Tested with `image = "image; rm /tmp/probe-touch"` — docker returns "Invalid reference format" exit non-zero, no shell execution. Good.
- **Broken symlink case_dir** (`ln -s /does/not/exist /tmp/case`): `is_symlink()` returns True → BLOCKED with the new symlink-detail message. Good — broken symlinks don't crash or get mistaken for "missing dir."
- **The new defensive guard handles all six bad shapes** (None / 42 / list / dict / "" / "   "): each produces controlled BLOCKED with `manifest_invalid_solver_docker_image`. Test coverage matches probe coverage.
- **Schema change does not break the sample manifest**: the sample `flat_plate_rans_sst/case_manifest.yaml` does not set `solver_docker_image` — the new schema field is optional. `validate-manifest` still exit 0.
- **R-13..R-16 risk register entries** still apply (these are the *outstanding* LOWs from rounds 6-9). γ didn't introduce them; they're orthogonal.

---

## Pattern observation — the R10 lesson holds, but new code is LESS risky each round

Round 10 added a new module (`backends/openfoam.py`) → surfaced 1 HIGH + 1 MED + 2 LOW.
Round 11 added new code on top of γ (regression fences + schema constraints + is_symlink guards + defensive validation) → surfaced 0 HIGH + 0 MED + 4 LOW.

The R10 lesson "net-new code resets the adversarial clock" is still true. But the *severity* of the new findings has dropped one tier each round:

```
Round 10 (new module):       HIGH (1) + MED (1) + LOW (2)
Round 11 (γ delta only):     LOW (4) — no HIGH, no MED
```

The interpretation: adding ONE small fix at a time keeps the per-round attack surface small. Adding a whole new module (step 2 will be bigger than step 1) expands the surface much more. Translating to step-2 planning:

- step 2 will introduce: `docker run` invocation, log parser, residuals.csv writer, gate computer, NASA TMR fetch + cache + comparison
- expected to surface 1+ HIGH on its first meta scan
- recommend splitting step 2 into sub-commits, each adversarially reviewed before the next

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
| **11 (γ meta)**             | **0**| **0**| **0**| **4**| **4** |

HIGH closed, MED closed, ceiling back to LOW. Findings character: 1 doc drift + 1 fence breadth + 1 schema/adapter inconsistency + 1 step-2-precondition. All four are "small mechanical fixes before step 2 ships" — none requires deep redesign.

---

## Verdict

**FAIL** on the round-11 meta scan.

But — important — **the four findings are all small, mechanical, and step-2-precondition-class**. None block landing step 2 in principle; R11-F-04 must be addressed before the `docker run --volume` line lands, and R11-F-01..F-03 should land in any subsequent commit.

The γ batch succeeded at what it was supposed to do: closed the HIGH + MED from R10, hardened the symlink surface for step 2 prep. The remaining LOWs are the residue of polishing a new code surface — exactly the same pattern rounds 5-9 saw on the trust-loop scaffold, with the same "1-2 rounds of LOW polish, then zero-finding" trajectory expected.

---

## Recommended next options for the owner

1. **(α)** Fix R11-F-01 + R11-F-02 + R11-F-03 only — doc drift + fence breadth + schema regex. All three are <5-line edits. ~15 min.
2. **(β)** Fix all four (R11-F-01..F-04) — also implement recursive `_has_symlink_descendant` guard for R11-F-04. ~30 min. Higher cost because the recursive walk has perf implications. **Recommended only if step 2 is the immediate next move.**
3. **(γ)** Fix α and DEFER R11-F-04 to "step 2 design discussion" — log it as R-17 in `RISK_REGISTER.md` with the explicit note "MUST close before `docker run --volume` ships." ~20 min. **Recommended.** R11-F-04's right resolution is intertwined with step 2's mount-strategy decision (read-only mount vs symlink rejection vs both), so deciding now risks over-fitting.
4. **(δ)** Document all four findings in `RISK_REGISTER.md` and start step 2 with the constraint baked in. ~10 min for the doc; step 2 itself is hours.

My recommendation: **(γ)**. Close the three mechanical fixes, defer R11-F-04 to step 2 where it belongs as a design constraint rather than a band-aid.
