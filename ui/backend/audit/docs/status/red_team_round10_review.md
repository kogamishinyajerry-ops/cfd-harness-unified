# Red Team Round-10 Review — Phase 1 Step 1 Meta Scan

**Scope:** adversarial probe of the new `src/cfdtrust/backends/openfoam.py` Docker adapter, the integration with `cfdtrust.audit.solver._execute_openfoam`, and the related decisions DEC-0005 + DEC-0006.
**Author:** test-red-team agent.
**Date:** 2026-05-20.
**Previous round:** `red_team_round9_review.md` (FAIL, 3 LOW — all polish/debt).
**Verdict:** FAIL — 1 **HIGH** (factual error in the user-visible next-step) + 1 MEDIUM (crash on bad input) + 2 LOW (symlink-class, same shape as R7/R8).

---

## Method

Four probes against the new code surface:

| # | Probe                                                        | Expected           | Observed          |
|---|--------------------------------------------------------------|--------------------|-------------------|
| 1 | `manifest.solver_docker_image` set to non-string (None/int/list/dict) | controlled BLOCKED | **uncaught `TypeError` crash** |
| 2 | `case_dir/system/` is a symlink pointing OUTSIDE `case_dir`  | not compatible     | **compatible (followed silently)** |
| 3 | Default `DEFAULT_IMAGE` tag exists on Docker Hub             | yes                | **404 — typo** |
| 4 | `case_dir` itself is a symlink to outside the repo           | not compatible     | **compatible** |

Three out of four probes broke. The HIGH is probe 3 — a factual error in the "exact next step" string the adapter promised the user. The MED is probe 1 — uncontrolled crash. The two LOWs are symlink-class issues that re-emerge in this new code surface (the round-8 SSOT fix lives in `cwos_agents`, not in `backends`).

---

## Findings

### R10-F-01 — HIGH — `DEFAULT_IMAGE` tag does not exist on Docker Hub

**File:** `src/cfdtrust/backends/openfoam.py:33`.

```python
DEFAULT_IMAGE = "openfoam/openfoam11-paraview512:latest"
```

This tag does not exist. `docker manifest inspect openfoam/openfoam11-paraview512:latest` returns "denied / unauthorized" (the standard Hub error for non-existent images). `docker search openfoam` confirms the real tag is `openfoam/openfoam11-paraview510` — **ParaView 5.10**, not 5.12.

**Live reproduction:**

```bash
$ docker search openfoam --limit 8
NAME                              DESCRIPTION                              STARS  OFFICIAL
openfoam/openfoam11-paraview510   Image of OpenFOAM v11 and ParaView 5.10.1 on U…   4
openfoam/openfoam7-paraview56     Image of OpenFOAM v7 and ParaView 5.6.0 on U…    13
...
(no openfoam11-paraview512 line)

$ docker manifest inspect openfoam/openfoam11-paraview512:latest
errors:
  denied: requested access to the resource is denied
  unauthorized: authentication required
```

The "denied / unauthorized" error is Hub's standard response for non-existent paths. The conventional valid tag is `openfoam/openfoam11-paraview510`.

**Why this matters:** the adapter's design promise is "structured BLOCKED with the *exact* next step a user can copy-paste." On the current code, the cockpit and the trust report would tell a user:

```
Run `docker pull openfoam/openfoam11-paraview512:latest` once, then retry.
```

The user runs the command. It fails with "manifest unknown / image not found." They are now stuck with no recovery path the harness gave them — the "honesty rule" the adapter loudly defends ships a factually wrong instruction at the top.

This is a HIGH because:
1. **First-contact failure**: this is the FIRST instruction a real user sees when they actually try Phase 1.
2. **Silent until-execution**: no test caught it because the tests monkeypatch out the subprocess — they verify the *shape* of the BLOCKED gate but not the *correctness* of the image name.
3. **Contradicts the design intent**: an adapter that proudly refuses to silently mock cannot itself ship a silently broken next-step.
4. **Single-line fix**: `DEFAULT_IMAGE = "openfoam/openfoam11-paraview510"` (with or without `:latest`) closes it.

**Severity rationale — HIGH (not CRITICAL):** the harness still BLOCKs the run; no false PASS is possible from this bug alone. A user who reads the next_step and tries the command discovers the typo within seconds. But it is the first regression of the project's "evidence is honest at the user-facing boundary" promise since round-3, and that promise is the entire wedge.

**Test gap that allowed this:** the existing tests mock subprocess to simulate the `image not pulled` path but never verify that the *string* in the next_step is a real image. A test that calls `docker manifest inspect` against `DEFAULT_IMAGE` (skipped if docker is absent, network-permitting) would have caught this. Recommend adding it as a `@pytest.mark.network` opt-in test.

---

### R10-F-02 — MEDIUM — non-string `solver_docker_image` crashes with uncaught `TypeError`

**File:** `src/cfdtrust/backends/openfoam.py:65-69`.

```python
def _image_present(image: str) -> bool:
    try:
        res = subprocess.run(
            ["docker", "image", "inspect", image],
            ...
```

If `manifest.solver_docker_image` is `None`, `42`, `['list']`, or `{'dict': 'value'}`, `subprocess.run` receives a non-string in `args` and raises `TypeError: expected str, bytes or os.PathLike object, not <type>`. The exception is not caught by the `(TimeoutExpired, OSError)` handler.

**Live reproduction:**

```python
>>> ofa.run(Path('/tmp'), {'solver_docker_image': None})
TypeError: expected str, bytes or os.PathLike object, not NoneType

>>> ofa.run(Path('/tmp'), {'solver_docker_image': 42})
TypeError: expected str, bytes or os.PathLike object, not int

>>> ofa.run(Path('/tmp'), {'solver_docker_image': ['list']})
TypeError: expected str, bytes or os.PathLike object, not list

>>> ofa.run(Path('/tmp'), {'solver_docker_image': {'dict': 'thing'}})
TypeError: expected str, bytes or os.PathLike object, not dict
```

When invoked through `cfdtrust run`, this propagates as an unhandled traceback to the user, not as a structured BLOCKED gate. The honesty contract of the adapter ("every failure mode is a typed BLOCKED with a reason") is broken at the input-validation boundary.

**Root cause:** the case_manifest schema does not validate `solver_docker_image`. It's a NEW field added in step 1 but the schema was not updated, and `additionalProperties: true` lets anything through.

**Fix sketch — pick one:**

Option A (defensive, in adapter):

```python
image = manifest.get("solver_docker_image", DEFAULT_IMAGE)
if not isinstance(image, str) or not image.strip():
    return {
        "status": "BLOCKED",
        "summary": "manifest.solver_docker_image is not a non-empty string.",
        "details": {"reason": "manifest_invalid_solver_docker_image", "value": repr(image)},
    }
```

Option B (schema, in `case_manifest.schema.json`):

```json
"solver_docker_image": { "type": "string", "minLength": 1 }
```

Option B is structurally cleaner — invalid manifests fail at `validate-manifest` time, never reaching the adapter. Recommend B alone; A is unnecessary belt-and-suspenders if B holds.

**Severity rationale — MEDIUM (not HIGH):** the crash exposes Python stack to the user, but no false PASS is possible. Trips on a typo in the manifest, not on hostile input. Easy fix.

---

### R10-F-03 — LOW — `case_dir/system/` as symlink to outside the repo passes the compatibility check

**File:** `src/cfdtrust/backends/openfoam.py:_is_openfoam_compatible_case_dir:78-83`.

```python
def _is_openfoam_compatible_case_dir(case_dir: Path) -> Tuple[bool, str]:
    missing = [d for d in _OPENFOAM_REQUIRED_DIRS if not (case_dir / d).is_dir()]
    ...
```

`Path.is_dir()` follows symlinks. If a user constructs `case_dir/system/ → /tmp/somewhere/`, the check passes. Live:

```bash
$ mkdir /tmp/r10-case /tmp/r10-host && touch /tmp/r10-host/.secret
$ ln -s /tmp/r10-host /tmp/r10-case/system
$ mkdir /tmp/r10-case/constant /tmp/r10-case/0
>>> ofa._is_openfoam_compatible_case_dir(Path('/tmp/r10-case'))
(True, '')
```

**Step-1-only consequence:** none — the adapter immediately returns `execution_not_implemented_yet`. The symlink is read but never executed against.

**Step-2 consequence (must be addressed BEFORE step 2 lands):** the planned `docker run` would `--volume` the symlinked path into the container. Anything `simpleFoam` writes to `/case/system/` would land in `/tmp/r10-host/` on the host. If a user is tricked into running a manifest from an untrusted source, this is a host filesystem write primitive via Docker.

Same shape as R7-F-01 / R8-F-01 in `cwos_agents`. The round-8 SSOT chokepoint (`_safe_md_files`) lives in `cwos_agents` and is not reusable here — `_safe_md_files` filters .md files, not OpenFOAM case subdirectories.

**Fix sketch:**

```python
for d in _OPENFOAM_REQUIRED_DIRS:
    p = case_dir / d
    if p.is_symlink():
        return False, f"required dir {d} is a symlink (not allowed)"
    if not p.is_dir():
        ...
```

**Severity rationale — LOW (currently):** step 1 doesn't execute, so no exploit today. Becomes a HIGH the moment step 2 ships `docker run --volume`. Flagging now so step 2 lands with the guard, not as an aftermath.

---

### R10-F-04 — LOW — `case_dir` itself as a symlink to outside the repo passes the compatibility check

**File:** same — `_is_openfoam_compatible_case_dir` doesn't check `case_dir.is_symlink()`.

Live:

```bash
$ mkdir /tmp/r10-real && for s in system constant 0; do mkdir /tmp/r10-real/$s; done
$ ln -s /tmp/r10-real /tmp/r10-link
>>> ofa._is_openfoam_compatible_case_dir(Path('/tmp/r10-link'))
(True, '')
```

This is the outer-level twin of R10-F-03 — and `cfdtrust run` itself accepts an arbitrary `case_path` from argv. A user passing `cfdtrust run /tmp/symlink-to-anywhere` would have the docker run mount that symlink target in step 2.

Same severity (LOW now, HIGH at step 2). Fix is checking `case_dir.is_symlink()` at the entry of `run()`.

---

## What I tried that did NOT break

- **`docker version` slow / timeout (5s)**: adapter returns `docker_not_available` with "timed out after 5s" — controlled BLOCKED, no crash. Good.
- **`docker version` returns stderr with unicode / long strings**: adapter truncates to 200 chars via `[:200]`. Good.
- **`shutil.which("docker")` returning a path that no longer exists (race)**: subprocess.run raises `FileNotFoundError` which is a subclass of `OSError`, caught by `except OSError`. Good.
- **Honesty rule**: when every env probe is forced to succeed via monkeypatching, the final return is still `BLOCKED` with `execution_not_implemented_yet`. The corresponding test `test_openfoam_adapter_blocks_when_env_ready_but_execution_not_implemented` asserts `status != "MOCKED"` and `status != "PASS"`. Test prevents the most dangerous regression (silent mocked fallback).
- **F-04 contract**: flipping the sample manifest to `solver_backend: openfoam` now produces a structured BLOCKED gate from the real adapter (not the ImportError fallback). `cmd_run` exits 1. Cockpit + trust_report surface the BLOCKED reason.
- **Schema check on `solver_backend` enum**: schema already constrains the field to `{openfoam, mocked}`. A manifest with `solver_backend: bogus` fails `validate-manifest` before reaching the adapter.

---

## Pattern observation — the "diminishing returns" prediction from round-9 was wrong

Round-9 concluded:

> "There is no exploitable bypass in the round-8 β code. ... Phase 0 DoD has been met. Round-10 hardening yields diminishing security returns vs Phase 1 OpenFOAM adapter delivering real wedge value."

That conclusion held **for the round-8 code surface**. But round-9's prediction was applied wrongly to "round-10 in general." Phase 1 step 1 added a brand-new code surface, and an adversarial pass on that surface immediately surfaced **the first HIGH since round-3**.

The lesson for the project memory:

- "Diminishing returns" applies to **stable** code. Every NEW code surface (new module, new contract, new external dependency like Docker) resets the clock.
- The round-9 line "the harness is hardened enough" was correct about the trust-loop scaffold. It said nothing about future net-new code.
- The right policy is: **adversarial review is mandatory after any new code surface**, even when the previous round was 0-finding. Continuing to red-team STABLE code yields diminishing returns; red-teaming NEW code does not.

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
| **10 (step 1 meta)**        | **0**| **1**| **1**| **2**| **4** |

**Severity ceiling reset:** first HIGH since round-3 (R3-F-01 path traversal). Net-new code introduced new attack surface, exactly as the pattern observation above predicts.

---

## Verdict

**FAIL** on the round-10 meta scan.

R10-F-01 (default image typo) is a real HIGH — it breaks the adapter's central design promise at the user-facing boundary. R10-F-02 (TypeError crash) is a real MEDIUM — schema gap leads to uncontrolled exception. R10-F-03 + R10-F-04 are LOW today but pre-position for HIGH at step 2 (docker mount of host filesystem).

Phase 1 step 1 cannot be considered "done" while R10-F-01 ships the wrong `docker pull` command in cockpit output. R10-F-02 should be closed at the schema level. R10-F-03 + R10-F-04 should be closed BEFORE step 2 lands, not as cleanup after.

---

## Recommended next options for the owner

1. **(α)** Fix R10-F-01 only — one-line correct the default image tag (`paraview510` not `paraview512`), add a `@pytest.mark.network` opt-in test that verifies `DEFAULT_IMAGE` resolves via `docker manifest inspect`. ~10 min.
2. **(β)** Fix R10-F-01 + R10-F-02 — also add `solver_docker_image: {type: string, minLength: 1}` to the case_manifest schema + a schema-validation test. ~20 min.
3. **(γ)** Fix R10-F-01 + R10-F-02 + R10-F-03 + R10-F-04 — also add `is_symlink()` guards on `case_dir` and each required subdir; close all four R10 findings in one batch. ~30 min. **Recommended** — R10-F-03/04 become HIGH at step 2; closing them now means step 2 is safe by construction, not by post-hoc audit.
4. **(δ)** Document the HIGH + MED in `RISK_REGISTER.md`, proceed to step 2 anyway, accept that step 2 will need its own R10-F-03/04 fix.

My recommendation: **(γ)**. The cost gap between (β) and (γ) is small; the safety gap is large (R10-F-03/04 become exploits the moment step 2 ships).
