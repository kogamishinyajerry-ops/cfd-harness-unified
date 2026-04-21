---
phase: 07a-field-capture
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/foam_agent_adapter.py
  - scripts/phase5_audit_run.py
autonomous: false   # 三禁区 #1 (src/) + >5 LOC → Codex mandatory in Wave 3
requirements: [DEC-V61-031]   # new DEC authored in Wave 3
user_setup: []

must_haves:
  truths:
    - "After a successful LDC audit_real_run, reports/phase5_fields/lid_driven_cavity/{YYYYMMDDTHHMMSSZ}/ exists with ≥3 files"
    - "controlDict emitted by _generate_lid_driven_cavity contains a top-level `functions` block with `sample` and `residuals` sub-dicts"
    - "reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json maps run_label → timestamp directory"
    - "yPlus function object is NOT emitted for LDC (laminar) but code path is present for future turbulent cases"
    - "foamToVTK failure does NOT fail the outer solver run (comparator scalar extraction still succeeds)"
  artifacts:
    - path: "src/foam_agent_adapter.py"
      provides: "_emit_phase7a_function_objects(case_dir, task_spec) helper + _capture_field_artifacts(container, case_cont_dir, case_host_dir, case_id, timestamp) method on FoamAgentExecutor + controlDict emission updated in _generate_lid_driven_cavity"
      contains: "def _emit_phase7a_function_objects"
    - path: "scripts/phase5_audit_run.py"
      provides: "run_one passes shared timestamp into executor, writes per-run manifest, injects `field_artifacts` key into audit fixture after `decisions_trail`"
      contains: "phase7a_timestamp"
  key_links:
    - from: "scripts/phase5_audit_run.py::run_one"
      to: "FoamAgentExecutor._capture_field_artifacts"
      via: "task_spec.metadata['phase7a_timestamp'] OR new kwarg on execute()"
      pattern: "phase7a_timestamp"
    - from: "FoamAgentExecutor.execute (try-block, between _copy_postprocess_fields and _parse_solver_log)"
      to: "reports/phase5_fields/{case_id}/{timestamp}/"
      via: "docker cp + local tar extract"
      pattern: "_capture_field_artifacts"
---

<objective>
Extend the LDC real-solver path so every `audit_real_run` persists OpenFOAM field artifacts (binary VTK + sampled CSV + structured residuals.dat + log.simpleFoam) to a stable on-disk layout under `reports/phase5_fields/{case_id}/{timestamp}/`, with a per-run manifest at `reports/phase5_fields/{case_id}/runs/{run_label}.json`.

Purpose: Wave 2 (backend route) needs a deterministic `run_label → timestamp` mapping and real artifacts on disk to build an integration test. Wave 3 (Codex review + DEC + commit) needs the final adapter+driver diff to be <100 LOC, defensive (try/except around foamToVTK), and consistent with existing `_copy_postprocess_fields` pattern (src/foam_agent_adapter.py:6729-6776).

Output:
- Edited `src/foam_agent_adapter.py`: new helper `_emit_phase7a_function_objects`, new executor method `_capture_field_artifacts`, call-site wiring inside `FoamAgentExecutor.execute` try-block (between lines 597 and 600), updated `_generate_lid_driven_cavity` controlDict to invoke the helper.
- Edited `scripts/phase5_audit_run.py`: `run_one` pre-computes a shared timestamp, threads it via `task_spec.metadata['phase7a_timestamp']`, writes `reports/phase5_fields/{case_id}/runs/{run_label}.json` at end of successful run, appends a `field_artifacts` block (manifest-relative path only, no timestamps inside YAML) to `_audit_fixture_doc` AFTER the `decisions_trail` key.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/07a-field-capture/07a-CONTEXT.md
@.planning/phases/07a-field-capture/07a-RESEARCH.md
@.planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md
@src/foam_agent_adapter.py
@scripts/phase5_audit_run.py
@ui/backend/tests/test_phase5_byte_repro.py

<interfaces>
<!-- Key types the executor needs from the existing codebase. -->

From src/foam_agent_adapter.py FoamAgentExecutor (existing, verified lines 384-623):
```python
class FoamAgentExecutor:
    _work_dir: str = "/tmp/cfd-harness-cases"
    _timeout: int  # seconds

    def execute(self, task_spec) -> ExecutionResult: ...       # :384
    def _docker_exec(self, cmd: str, cwd: str, timeout: int)
        -> tuple[bool, str]: ...                               # :6612-
    def _copy_file_from_container(container, container_path: str,
                                   dest_path: Path) -> None: ...  # :6710-6727
    def _copy_postprocess_fields(self, container, case_cont_dir: str,
                                 case_host_dir: Path) -> None: ... # :6729-6776
    # In execute()'s try block:
    #   line 576: runs solver
    #   line 590: postProcess writeObjects
    #   line 597: _copy_postprocess_fields  ← insert our capture call RIGHT AFTER
    #   line 600: _parse_solver_log         ← BEFORE this
    #   line 618: finally: shutil.rmtree(case_host_dir)  ← must beat this
```

From src/foam_agent_adapter.py LDC generator (existing, verified lines 716-768):
```python
# The controlDict literal in _generate_lid_driven_cavity ends with:
#   "runTimeModifiable true;\n\n// ***...***//\n"
# ends at line 765. We will append a functions{} block BEFORE the closing
# comment. The convertToMeters is 0.1 (adapter:6545) so sample coords must
# be in post-convertToMeters space: y-axis from 0.0 to 0.1, x=0.05, z=0.005.
```

From scripts/phase5_audit_run.py (existing, verified lines 93-233):
```python
REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR   = REPO_ROOT / "reports" / "phase5_audit"

def _audit_fixture_doc(case_id, report, commit_sha) -> dict:
    # Returns dict with key order:
    #   run_metadata, case_id, source, measurement, audit_concerns, decisions_trail
    # We append `field_artifacts` AFTER decisions_trail.

def run_one(runner: TaskRunner, case_id: str, commit_sha: str) -> dict:
    # Current body at lines 210-233. We insert:
    #   (1) timestamp = datetime.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    #   (2) spec.metadata["phase7a_timestamp"] = timestamp  (if metadata attr exists)
    #   (3) After successful run, write runs/{run_label}.json manifest.
```

From .planning/phases/07a-field-capture/07a-RESEARCH.md §2.7:
```python
# run_id convention: "{case_id}__{run_label}"   e.g. "lid_driven_cavity__audit_real_run"
# Driver writes reports/phase5_fields/{case_id}/runs/{run_label}.json = {"timestamp": "<ts>"}
# Wave 2 backend route will read this manifest.
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Emit controlDict functions{} block in _generate_lid_driven_cavity + add _emit_phase7a_function_objects helper</name>
  <files>src/foam_agent_adapter.py</files>
  <read_first>
    - src/foam_agent_adapter.py (lines 640-1057 for full _generate_lid_driven_cavity; lines 716-768 for exact controlDict literal; lines 6522-6606 for _render_block_mesh_dict convertToMeters context; line 5128 for precedent functions{} block in DHC buoyantFoam)
    - .planning/phases/07a-field-capture/07a-RESEARCH.md (§2.2 copy-paste-ready functions{} block; §3.7 keep existing sampleDict untouched)
    - .planning/phases/07a-field-capture/07a-CONTEXT.md (locked decisions on writeControl timeStep; sample coords in physical post-convertToMeters space)
  </read_first>
  <action>
**Step 1 — Add the helper (new method on module-level or on class, placed between `_render_block_mesh_dict` region and `_generate_lid_driven_cavity`):**

Add this helper near other `_emit_*` / rendering helpers in `src/foam_agent_adapter.py` (exact location: after the `_render_block_mesh_dict` function body, before `_generate_lid_driven_cavity`):

```python
    @staticmethod
    def _emit_phase7a_function_objects(turbulence_model: str = "laminar") -> str:
        """Phase 7a — return the controlDict `functions{}` block as a raw string.

        Called from each case generator that opts into Phase 7a field capture.
        For LDC (laminar) yPlus is omitted; for turbulent cases the yPlus block
        is activated. Sample coordinates are in post-convertToMeters space.

        See .planning/phases/07a-field-capture/07a-RESEARCH.md §2.2 for the
        function-object reference. `writeControl timeStep; writeInterval 500;`
        is correct for steady simpleFoam per research validation
        (CONTEXT.md said `runTime` which is transient-only — ratified by user).
        """
        y_plus_block = ""
        if turbulence_model and turbulence_model != "laminar":
            y_plus_block = (
                "\n    yPlus\n"
                "    {\n"
                "        type            yPlus;\n"
                '        libs            ("libfieldFunctionObjects.so");\n'
                "        writeControl    writeTime;\n"
                "    }\n"
            )

        return (
            "\nfunctions\n"
            "{\n"
            "    sample\n"
            "    {\n"
            "        type            sets;\n"
            '        libs            ("libsampling.so");\n'
            "        writeControl    timeStep;\n"
            "        writeInterval   500;\n"
            "\n"
            "        interpolationScheme cellPoint;\n"
            "        setFormat       raw;\n"
            "\n"
            "        fields          (U p);\n"
            "\n"
            "        sets\n"
            "        {\n"
            "            uCenterline\n"
            "            {\n"
            "                type        uniform;\n"
            "                axis        y;\n"
            "                start       (0.05 0.0   0.005);\n"
            "                end         (0.05 0.1   0.005);\n"
            "                nPoints     129;\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "\n"
            "    residuals\n"
            "    {\n"
            "        type            residuals;\n"
            '        libs            ("libutilityFunctionObjects.so");\n'
            "        writeControl    timeStep;\n"
            "        writeInterval   1;\n"
            "        fields          (U p);\n"
            "    }\n"
            f"{y_plus_block}"
            "}\n"
        )
```

**Step 2 — Inject into the LDC controlDict.**

In `_generate_lid_driven_cavity` (lines 716-768), the controlDict is currently written as a single triple-quoted string ending with:

```
...
runTimeModifiable true;

// ************************************************************************* //
```

Replace the single `write_text(...)` with a concatenation. The existing block ends at line 766 (the comment line). Keep the existing literal up through `"runTimeModifiable true;\n"`, then append the functions block before the closing comment.

Concretely, locate the existing literal (lines 717-767). Change:

```python
        (case_dir / "system" / "controlDict").write_text(
            """\
...existing content through runTimeModifiable true;

// ************************************************************************* //
""",
            encoding="utf-8",
        )
```

to:

```python
        # Phase 7a — functions{} block injected before the closing fence.
        _controldict_head = """\
/*--------------------------------*- C++ -*---------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         2000;

deltaT          1;

writeControl    timeStep;

writeInterval   2000;

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;
"""
        _controldict_tail = "\n// ************************************************************************* //\n"
        _turb_model = getattr(task_spec, "turbulence_model", "laminar") or "laminar"
        (case_dir / "system" / "controlDict").write_text(
            _controldict_head
            + self._emit_phase7a_function_objects(turbulence_model=_turb_model)
            + _controldict_tail,
            encoding="utf-8",
        )
```

**Step 3 — Do NOT touch `system/sampleDict` emission** (lines 1010-1057). The existing comparator reads `postProcessing/sets/<time>/uCenterline_U.xy` — preserving that path avoids regressing the 11/17 PASS comparator result (see 07a-RESEARCH.md §3.7). The new in-controlDict `sample` function object writes to `postProcessing/sample/<time>/uCenterline_U_p.xy` — that is the new Phase 7a artifact captured in Task 2.

**Step 4 — Quick local diff sanity check:**
- Estimated LOC delta: helper ≈ 50 lines; `_generate_lid_driven_cavity` edit ≈ 5 lines (replace write_text args). Total <60 LOC in src/.
- Zero change to `system/sampleDict`, `fvSchemes`, `fvSolution`, boundary conditions, or mesh generation.
  </action>
  <verify>
    <automated>.venv/bin/python -c "import ast, pathlib; src = pathlib.Path('src/foam_agent_adapter.py').read_text(); ast.parse(src); assert '_emit_phase7a_function_objects' in src; assert 'libsampling.so' in src; assert 'libutilityFunctionObjects.so' in src; assert '(0.05 0.0' in src and '(0.05 0.1' in src; assert '_emit_phase7a_function_objects(turbulence_model=' in src; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "_emit_phase7a_function_objects" src/foam_agent_adapter.py` returns ≥2 matches (definition + one call site)
    - `grep -n "libsampling.so" src/foam_agent_adapter.py` returns exactly 1 match (inside the helper)
    - `grep -n "libutilityFunctionObjects.so" src/foam_agent_adapter.py` returns exactly 1 match
    - `grep -n "writeInterval   500" src/foam_agent_adapter.py` returns ≥1 match (sample function object)
    - `grep -n "(0.05 0.0" src/foam_agent_adapter.py` AND `grep -n "(0.05 0.1" src/foam_agent_adapter.py` each return ≥1 match (physical-space coords)
    - `grep -c "sampleDict" src/foam_agent_adapter.py` returns the SAME value as on `main` prior to this task (no change to legacy sampleDict emission — §3.7 preservation)
    - `python -c "import ast, pathlib; ast.parse(pathlib.Path('src/foam_agent_adapter.py').read_text())"` exits 0 (file parses)
    - `grep -n "runTime" src/foam_agent_adapter.py | grep "functions"` returns NO lines (we use `timeStep` not `runTime` per user ratification #2)
  </acceptance_criteria>
  <done>
Helper `_emit_phase7a_function_objects` is defined, returns a string containing `functions { sample { ... } residuals { ... } }` with `libsampling.so` + `libutilityFunctionObjects.so` and `writeControl timeStep; writeInterval 500;`. `_generate_lid_driven_cavity` calls the helper and writes the combined controlDict. yPlus code path is present (for future turbulent cases) but inert for laminar LDC. Legacy `system/sampleDict` emission is untouched.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Add FoamAgentExecutor._capture_field_artifacts + wire call-site in execute() try-block</name>
  <files>src/foam_agent_adapter.py</files>
  <read_first>
    - src/foam_agent_adapter.py (lines 384-623 for FoamAgentExecutor.execute body; lines 575-617 for post-solver sequence; lines 618-623 for finally teardown we must beat; lines 6710-6776 for _copy_file_from_container + _copy_postprocess_fields PRECEDENT we extend)
    - .planning/phases/07a-field-capture/07a-RESEARCH.md (§2.1 capture step 6.6, §2.3 foamToVTK flags, §3.2 empty-patch fallback, §3.5 timestamp authority)
  </read_first>
  <action>
**Step 1 — Add `_capture_field_artifacts` as a sibling of `_copy_postprocess_fields`** (immediately after the existing method at line 6776 so Codex can see the diff co-located with precedent):

```python
    def _capture_field_artifacts(
        self,
        container: Any,
        case_cont_dir: str,
        case_host_dir: Path,
        case_id: str,
        timestamp: str,
    ) -> Path | None:
        """Phase 7a — stage OpenFOAM field artifacts out of the container
        before the finally-block tears down case_host_dir.

        Mirrors _copy_postprocess_fields. Runs foamToVTK inside the container,
        then uses docker `get_archive` to pull VTK/, postProcessing/sample/,
        and postProcessing/residuals/ wholesale via a single tar stream.
        Also copies log.simpleFoam from the host case dir (already on host).

        Returns the host-side artifact_dir on success, None on failure.
        Never raises — field capture is best-effort and must not fail the run.
        """
        import io as _io
        import sys as _sys
        import tarfile as _tarfile

        repo_root = Path(__file__).resolve().parents[1]
        artifact_dir = repo_root / "reports" / "phase5_fields" / case_id / timestamp
        try:
            artifact_dir.mkdir(parents=True, exist_ok=True)

            # (a) foamToVTK — -allPatches merges patches into a single file.
            #     Fallback without -allPatches if it trips empty-patch
            #     assertions (07a-RESEARCH.md §3.2).
            ok, log = self._docker_exec(
                "foamToVTK -latestTime -noZero -allPatches",
                case_cont_dir,
                120,
            )
            if not ok:
                print(
                    f"[WARN] foamToVTK -allPatches failed, retrying without: {log[:200]}",
                    file=_sys.stderr,
                )
                ok, log = self._docker_exec(
                    "foamToVTK -latestTime -noZero", case_cont_dir, 120,
                )
            if not ok:
                print(
                    f"[WARN] foamToVTK failed, field capture skipped: {log[:200]}",
                    file=_sys.stderr,
                )
                return None

            # (b) Tar + get_archive the three subtrees. Missing subtrees are
            #     fine (e.g. postProcessing/residuals only exists if the
            #     residuals function object was emitted).
            for sub in ("VTK", "postProcessing/sample", "postProcessing/residuals"):
                src_in_cont = f"{case_cont_dir}/{sub}"
                # Probe existence cheaply.
                probe = container.exec_run(
                    cmd=["bash", "-c", f'[ -e "{src_in_cont}" ] && echo y || echo n'],
                )
                if probe.output.decode().strip() != "y":
                    continue
                try:
                    bits, _ = container.get_archive(src_in_cont)
                    buf = _io.BytesIO(b"".join(bits))
                    with _tarfile.open(fileobj=buf) as tar:
                        tar.extractall(path=artifact_dir)
                except Exception as e:  # noqa: BLE001
                    print(
                        f"[WARN] staging {sub} failed: {e!r}", file=_sys.stderr,
                    )

            # (c) log.simpleFoam — already on host after _docker_exec.
            for logname in ("log.simpleFoam", "log.icoFoam", "log.buoyantFoam",
                            "log.pimpleFoam"):
                src = case_host_dir / logname
                if src.is_file():
                    (artifact_dir / logname).write_bytes(src.read_bytes())
                    break

            # (d) Derive residuals.csv from postProcessing/residuals/0/residuals.dat
            #     if present. This is per user ratification #3 — structured ASCII,
            #     no log regex.
            residuals_dat_candidates = list(
                artifact_dir.glob("postProcessing/residuals/*/residuals.dat")
            )
            if residuals_dat_candidates:
                try:
                    self._emit_residuals_csv(
                        residuals_dat_candidates[0],
                        artifact_dir / "residuals.csv",
                    )
                except Exception as e:  # noqa: BLE001
                    print(
                        f"[WARN] residuals.csv derivation failed: {e!r}",
                        file=_sys.stderr,
                    )

            return artifact_dir
        except Exception as e:  # noqa: BLE001
            print(
                f"[WARN] _capture_field_artifacts failed: {e!r}", file=_sys.stderr,
            )
            return None

    @staticmethod
    def _emit_residuals_csv(dat_path: Path, csv_path: Path) -> None:
        """Convert OpenFOAM v10 residuals function-object output to CSV.

        The .dat format is whitespace-separated with a header line starting
        with `#`. We passthrough as CSV (comma-separated) with an explicit
        header — downstream tools (Phase 7b render pipeline) consume this.
        """
        lines = dat_path.read_text(encoding="utf-8").splitlines()
        header: list[str] | None = None
        rows: list[list[str]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                # Last `#` line before data is the column header.
                tokens = line.lstrip("#").split()
                if tokens:
                    header = tokens
                continue
            rows.append(line.split())
        if not header or not rows:
            return
        with csv_path.open("w", encoding="utf-8") as fh:
            fh.write(",".join(header) + "\n")
            for r in rows:
                fh.write(",".join(r) + "\n")
```

**Step 2 — Wire the call site inside `FoamAgentExecutor.execute`'s try-block.**

Locate the try-block sequence (lines 575-617). Immediately after line 597 (`self._copy_postprocess_fields(...)`) and BEFORE line 599 (`# 8. 解析 log 文件`), insert:

```python
            # 7.5. [Phase 7a] Stage field artifacts (VTK + sample CSV + residuals)
            #      BEFORE the finally-block tears down case_host_dir.
            #      Best-effort: failure must NOT fail the run (comparator still needs
            #      to work from the scalar extraction below).
            _phase7a_ts = None
            try:
                _phase7a_ts = (task_spec.metadata or {}).get("phase7a_timestamp")
            except Exception:
                _phase7a_ts = None
            if _phase7a_ts:
                self._capture_field_artifacts(
                    container, case_cont_dir, case_host_dir,
                    task_spec.case_id, _phase7a_ts,
                )
```

Note: the guard `if _phase7a_ts:` ensures other 9 cases (not yet opted-in to Phase 7a) skip capture silently. The LDC driver path in Wave 1 Task 3 is the only caller setting this key in MVP.

**Step 3 — Defensive imports**: confirm `from pathlib import Path` is already at module top (it is — verified via existing usage in `_copy_postprocess_fields`). No new top-level imports needed; `io`/`tarfile`/`sys` are imported locally inside the method to match the existing `_copy_file_from_container` style.
  </action>
  <verify>
    <automated>.venv/bin/python -c "
import ast, pathlib
src = pathlib.Path('src/foam_agent_adapter.py').read_text()
tree = ast.parse(src)
# Both methods exist on a class
method_names = set()
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        method_names.add(node.name)
assert '_capture_field_artifacts' in method_names, 'missing _capture_field_artifacts'
assert '_emit_residuals_csv' in method_names, 'missing _emit_residuals_csv'
# Call site exists in execute()
assert 'self._capture_field_artifacts(' in src, 'no call site in execute()'
# Call site is BEFORE the finally block
idx_call = src.index('self._capture_field_artifacts(')
idx_finally = src.index('finally:', idx_call)  # will find NEXT finally after call
assert idx_call < idx_finally
# Timestamp-guard present
assert 'phase7a_timestamp' in src
print('OK')
"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "def _capture_field_artifacts" src/foam_agent_adapter.py` returns exactly 1 match
    - `grep -n "def _emit_residuals_csv" src/foam_agent_adapter.py` returns exactly 1 match
    - `grep -n "self._capture_field_artifacts(" src/foam_agent_adapter.py` returns exactly 1 match (call site in execute)
    - `grep -n "phase7a_timestamp" src/foam_agent_adapter.py` returns ≥1 match
    - `grep -n "foamToVTK -latestTime -noZero" src/foam_agent_adapter.py` returns ≥2 matches (primary + fallback)
    - `grep -n "reports.*phase5_fields" src/foam_agent_adapter.py` returns ≥1 match
    - `python -c "import ast, pathlib; ast.parse(pathlib.Path('src/foam_agent_adapter.py').read_text())"` exits 0
    - The string `self._capture_field_artifacts(` appears textually BEFORE the string `# 8. 解析 log 文件` (insertion after _copy_postprocess_fields, before solver-log parse)
    - `_capture_field_artifacts` catches all exceptions and returns None on failure (grep for `except Exception` inside its body returns ≥2 matches)
  </acceptance_criteria>
  <done>
Two new methods on `FoamAgentExecutor`. Call site is post-`_copy_postprocess_fields`, pre-`_parse_solver_log`, inside the try-block so it runs BEFORE the `finally: shutil.rmtree(case_host_dir)` on line ~619. Gated on `task_spec.metadata["phase7a_timestamp"]` so only Phase 7a opt-in runs stage artifacts. All exceptions are swallowed with `[WARN]` to stderr. Timestamp is authored by the driver (not the executor) per research §3.5.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Driver pre-computes timestamp, writes per-run manifest, appends field_artifacts key to audit fixture</name>
  <files>scripts/phase5_audit_run.py</files>
  <read_first>
    - scripts/phase5_audit_run.py (full file — already read in context; focus lines 93-162 _audit_fixture_doc, 210-233 run_one)
    - ui/backend/tests/test_phase5_byte_repro.py (lines 30-37 _REQUIRED_TOP_KEYS, line 81 subset-check, lines 119-141 _audit_fixtures_nondeterministic_fields_are_isolated)
    - .planning/phases/07a-field-capture/07a-RESEARCH.md (§3.1 byte-repro safety, §2.7 run_id manifest)
  </read_first>
  <action>
**Step 1 — In `scripts/phase5_audit_run.py`, add helpers above `run_one` (i.e. between `_write_raw_capture` and `run_one`, around line 209):**

```python
FIELDS_DIR = REPO_ROOT / "reports" / "phase5_fields"


def _phase7a_timestamp() -> str:
    """Shared timestamp format — matches _write_raw_capture at line ~185."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_field_artifacts_run_manifest(case_id: str, run_label: str, timestamp: str) -> Path | None:
    """Write reports/phase5_fields/{case_id}/runs/{run_label}.json so the
    backend route can resolve run_label -> timestamp directory in O(1)."""
    artifact_dir = FIELDS_DIR / case_id / timestamp
    if not artifact_dir.is_dir():
        print(
            f"[audit] [WARN] field artifact dir missing, skipping manifest: {artifact_dir}",
            flush=True,
        )
        return None
    runs_dir = FIELDS_DIR / case_id / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    manifest = runs_dir / f"{run_label}.json"
    payload = {
        "run_label": run_label,
        "timestamp": timestamp,
        "case_id": case_id,
        "artifact_dir_rel": str(artifact_dir.relative_to(REPO_ROOT)),
    }
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest
```

**Step 2 — Extend `_audit_fixture_doc` to accept an optional `field_artifacts_ref` arg and append it AFTER `decisions_trail`:**

Locate the current signature at line 93:
```python
def _audit_fixture_doc(case_id: str, report, commit_sha: str) -> dict:
```

Change to:
```python
def _audit_fixture_doc(
    case_id: str,
    report,
    commit_sha: str,
    field_artifacts_ref: dict | None = None,
) -> dict:
```

At the very end of the function — AFTER the `if comp is not None:` branch that appends to `audit_concerns` (current line 162 is `return doc`) — insert BEFORE the return:

```python
    # Phase 7a — field artifacts reference (manifest path only; NO timestamps
    # in the YAML itself so byte-repro stays green per 07a-RESEARCH.md §3.1).
    # The manifest at the referenced path contains the timestamp.
    if field_artifacts_ref is not None:
        doc["field_artifacts"] = field_artifacts_ref
```

**Step 3 — Update `run_one` (current body lines 210-233):**

Replace the current body with:

```python
def run_one(runner: TaskRunner, case_id: str, commit_sha: str) -> dict:
    t0 = time.monotonic()
    print(f"[audit] {case_id} → start", flush=True)

    # Phase 7a — author the single shared timestamp up front.
    ts = _phase7a_timestamp()
    try:
        spec = runner._task_spec_from_case_id(case_id)
        # Opt-in signalling to FoamAgentExecutor. Other cases are no-ops on
        # the executor side (guarded by `if _phase7a_ts:`).
        if spec.metadata is None:
            spec.metadata = {}
        spec.metadata["phase7a_timestamp"] = ts
        report = runner.run_task(spec)
    except Exception as e:  # noqa: BLE001
        print(f"[audit] {case_id} EXCEPTION: {e!r}")
        return {"case_id": case_id, "ok": False, "error": repr(e)}

    dt = time.monotonic() - t0

    # Phase 7a — write per-run manifest + build field_artifacts_ref dict
    # iff the artifact dir materialized (best-effort, must not block doc).
    run_label = "audit_real_run"
    manifest_path = _write_field_artifacts_run_manifest(case_id, run_label, ts)
    field_artifacts_ref: dict | None = None
    if manifest_path is not None:
        field_artifacts_ref = {
            "manifest_path_rel": str(manifest_path.relative_to(REPO_ROOT)),
            "run_label": run_label,
            # Deliberately NO timestamp here (byte-repro): resolve via manifest.
        }

    doc = _audit_fixture_doc(
        case_id, report, commit_sha, field_artifacts_ref=field_artifacts_ref,
    )
    fixture_path = _write_audit_fixture(case_id, doc)
    raw_path = _write_raw_capture(case_id, report, dt)
    verdict = doc["run_metadata"]["expected_verdict"]
    print(f"[audit] {case_id} → {verdict} · {dt:.1f}s · {fixture_path.name}", flush=True)
    return {
        "case_id": case_id,
        "ok": True,
        "duration_s": round(dt, 3),
        "verdict": verdict,
        "fixture": str(fixture_path.relative_to(REPO_ROOT)),
        "raw": str(raw_path.relative_to(REPO_ROOT)),
        "field_artifacts_manifest": (
            str(manifest_path.relative_to(REPO_ROOT)) if manifest_path else None
        ),
    }
```

**Step 4 — Byte-repro safety check**: the new `field_artifacts` YAML key contains only `manifest_path_rel` + `run_label` — both deterministic strings given fixed commit. The timestamp lives in `reports/phase5_fields/{case}/runs/{run_label}.json` which is NOT under the fixture directory byte-repro-gates. `test_phase5_byte_repro.py` at line 81 uses subset check (`_REQUIRED_TOP_KEYS - set(doc.keys())`) so adding a new top-level key is safe (verified in research §3.1, §A6).

**Step 5 — Note about other 9 cases**: `spec.metadata["phase7a_timestamp"]` is set for ALL cases by `run_one`, but the executor-side `_capture_field_artifacts` gates behind the key's presence. Other cases' controlDicts do NOT yet emit the functions{} block (that's Phase 7c Sprint-2 scope), so `foamToVTK` will still produce VTK but `postProcessing/sample` + `postProcessing/residuals` will be empty — the code path safely degrades (only `VTK/` is staged). This is acceptable MVP behavior.
  </action>
  <verify>
    <automated>.venv/bin/python -c "
import ast, pathlib
src = pathlib.Path('scripts/phase5_audit_run.py').read_text()
ast.parse(src)
assert '_phase7a_timestamp' in src
assert '_write_field_artifacts_run_manifest' in src
assert 'field_artifacts_ref' in src
assert 'FIELDS_DIR' in src
# The YAML key insertion is after decisions_trail — grep ordering
idx_trail = src.index('decisions_trail')
idx_fa    = src.index('doc[\"field_artifacts\"]')
assert idx_trail < idx_fa, 'field_artifacts must be inserted after decisions_trail'
# run_one sets spec.metadata['phase7a_timestamp']
assert 'spec.metadata[\"phase7a_timestamp\"]' in src
print('OK')
" && .venv/bin/pytest ui/backend/tests/test_phase5_byte_repro.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def _phase7a_timestamp" scripts/phase5_audit_run.py` returns `1`
    - `grep -c "def _write_field_artifacts_run_manifest" scripts/phase5_audit_run.py` returns `1`
    - `grep -n "FIELDS_DIR" scripts/phase5_audit_run.py` returns ≥2 matches (definition + usage)
    - `grep -n "spec.metadata\[.phase7a_timestamp.\]" scripts/phase5_audit_run.py` returns ≥1 match
    - `grep -n "field_artifacts_ref" scripts/phase5_audit_run.py` returns ≥3 matches (param, arg, conditional)
    - `python -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/phase5_audit_run.py').read_text())"` exits 0
    - `.venv/bin/pytest ui/backend/tests/test_phase5_byte_repro.py -x` exits 0 (byte-repro regression guard — required for §3.1 safety)
    - `grep -n "timestamp" scripts/phase5_audit_run.py | grep -v "ts\s*=\s*_phase7a_timestamp" | grep -v "_write_raw_capture" | grep "field_artifacts_ref"` returns NO lines (no timestamp string embedded inside the YAML doc; timestamp lives in runs/{run_label}.json manifest)
    - The run_one return dict contains key `"field_artifacts_manifest"` (grep for that exact string)
  </acceptance_criteria>
  <done>
Driver pre-computes a single `YYYYMMDDTHHMMSSZ` timestamp at the top of `run_one`, threads it to the executor via `spec.metadata["phase7a_timestamp"]`. After a successful run, writes `reports/phase5_fields/{case_id}/runs/audit_real_run.json` manifest. Appends a `field_artifacts` top-level key (containing only `manifest_path_rel` + `run_label` — no embedded timestamp) to the audit fixture YAML, AFTER the `decisions_trail` key per §3.1 byte-repro-safety rule. `test_phase5_byte_repro.py` stays green.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Docker container → host filesystem | `container.get_archive(...)` + tar extract pulls container-controlled bytes into `reports/phase5_fields/{case_id}/{timestamp}/` |
| task_spec metadata → executor | Driver-set `phase7a_timestamp` crosses into `_capture_field_artifacts` and is used as a path segment |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-07a-01 | Tampering | `_capture_field_artifacts` tar extract | mitigate | `artifact_dir` is internally-computed from `REPO_ROOT / "reports" / "phase5_fields" / case_id / timestamp`; `case_id` comes from the internal whitelist (scripts/phase5_audit_run.py:47-58), `timestamp` is computed locally via `datetime.now(UTC).strftime`. No user input reaches the path. Tar extraction into the computed `artifact_dir` is not traversal-safe by itself — ACCEPT: container is locally-built, isolated, and trusted; scope is dev-only pre-Phase-7e signing |
| T-07a-02 | Tampering | `foamToVTK` command string in `_docker_exec` | mitigate | Command is a hard-coded literal (`"foamToVTK -latestTime -noZero -allPatches"`) — no interpolation of user input |
| T-07a-03 | Denial of Service | `foamToVTK` timeout | mitigate | Explicit 120 s timeout passed to `_docker_exec`; matches existing postProcess call at adapter:591 |
| T-07a-04 | Denial of Service | Unbounded disk growth under `reports/phase5_fields/` | accept | MVP scope: 10 cases × ~5 MB each = ~50 MB worst case; Phase 7e rotation not required yet. Documented in 07a-RESEARCH.md §9 metadata |
| T-07a-05 | Information Disclosure | `log.simpleFoam` may contain container-internal paths | accept | Dev-only artifacts; container paths are stable literals (`/tmp/cfd-harness-cases/...`) with no secrets |
| T-07a-06 | Information Disclosure | `field_artifacts` YAML key leaks internal path structure | accept | `manifest_path_rel` is a REPO_ROOT-relative path (e.g. `reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json`), not an absolute path with home dir |
</threat_model>

<verification>
Full phase-level check (runs in Wave 3 anyway but listed here for completeness):

1. `python -c "import ast, pathlib; ast.parse(pathlib.Path('src/foam_agent_adapter.py').read_text())"` — syntax valid
2. `python -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/phase5_audit_run.py').read_text())"` — syntax valid
3. `.venv/bin/pytest ui/backend/tests/ -v -x` — 79/79 stays green (no regressions; Wave 2 adds new tests on top)
4. Integration (gated, deferred to Wave 3): `EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity` produces `reports/phase5_fields/lid_driven_cavity/{ts}/` with ≥3 files + `runs/audit_real_run.json` manifest
</verification>

<success_criteria>
- `src/foam_agent_adapter.py` adds `_emit_phase7a_function_objects` + `_capture_field_artifacts` + `_emit_residuals_csv`, wires call site in `execute()` try-block before finally
- `scripts/phase5_audit_run.py` threads one shared timestamp driver→executor, writes `runs/{run_label}.json` manifest, injects `field_artifacts` YAML key after `decisions_trail`
- `test_phase5_byte_repro.py` stays green (no new byte-repro regressions — verified via acceptance test)
- 79/79 backend pytest remains green
- All edits localized to two files listed in `files_modified`
- Estimated adapter LOC delta: ~130 LOC (helpers + call site). Scripts LOC delta: ~45 LOC. Combined <200 LOC, within Codex review budget.
</success_criteria>

<output>
After Wave 1 completion, Wave 2 (07a-02-PLAN.md) reads the updated files to build the backend route + tests. Wave 3 (07a-03-PLAN.md) runs the integration + Codex review + DEC + commit.

Create `.planning/phases/07a-field-capture/07a-01-SUMMARY.md` documenting:
- Final LOC count per file
- Any deviations from the plan (e.g. foamToVTK timeout tuning)
- Verification that test_phase5_byte_repro.py stayed green
</output>
