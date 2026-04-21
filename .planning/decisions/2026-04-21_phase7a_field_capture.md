---
decision_id: DEC-V61-031
timestamp: 2026-04-21T17:00 local
scope: |
  Close Phase 7a — Field post-processing capture (Sprint 1, LDC depth-first
  MVP). Landed the first of 6 Phase 7 sub-phases: extend Phase 5a audit
  pipeline to persist full VTK fields + sampled CSV profiles + residual.log
  to reports/phase5_fields/{case_id}/{timestamp}/, and expose them via a
  new HMAC-less read-only backend route GET /api/runs/{run_id}/field-artifacts.
  Depth-first on LDC (simpleFoam Re=100, laminar) per user election from
  Phase 7 ROADMAP (commit e4dd1d9). Remaining 5 sub-phases (7b rendering,
  7c comparison report, 7d Richardson GCI, 7e signed-zip integration,
  7f frontend live fetch) queued for Sprint 2.

  Impact: Every LDC audit_real_run now produces 8 real post-processing
  artifacts (VTK volume + boundary, 3 iteration sample profiles, residual.csv
  + residuals.dat + log.simpleFoam), HTTP-exposed with SHA256 manifest.
  Current `/validation-report/lid_driven_cavity` page still shows only the
  scalar comparator, but the data infrastructure for Phase 7c's 8-section
  scientific report now exists. 97/97 backend pytest green.
autonomous_governance: true
  (src/foam_agent_adapter.py +244 LOC + scripts/phase5_audit_run.py +71 LOC
  triggered Codex mandatory per RETRO-V61-001 #1 三禁区 #1 + #2 byte-repro
  sensitive path. Codex 3 rounds completed post-merge, see
  codex_tool_report_path.)
claude_signoff: yes
codex_tool_invoked: true
codex_rounds: 3
codex_round_1_verdict: CHANGES_REQUIRED
codex_round_1_findings:
  - HIGH-1: URL basename collision — sample/{0,500,1000}/uCenterline.xy shared one URL, manifest advertised 3 distinct SHA256 but only first file downloadable. FIXED by using POSIX relative path in filename + {filename:path} FastAPI converter.
  - HIGH-2: Traversal via run_id — ..__pwn literal AND %2e%2e__pwn URL-encoded both returned 200 + data leak. FIXED by strict identifier regex in parse_run_id + additional timestamp validation in resolve.
  - MED-3: Phase 7a metadata over-applied to every case, not just LDC; empty artifact_dir produced bogus manifest. FIXED by _PHASE7A_OPTED_IN frozenset + usable-file count in _write_field_artifacts_run_manifest.
  - LOW-4: SHA cache used float st_mtime not st_mtime_ns. FIXED.
codex_round_2_verdict: CHANGES_REQUIRED
codex_round_2_findings:
  - HIGH: list_artifacts() didn't validate manifest timestamp before enumerating — timestamp='../../outside' caused list to hash files outside reports/phase5_fields/. FIXED by extracting _resolve_artifact_dir() shared helper with _TIMESTAMP_RE = r'^\d{8}T\d{6}Z$' shape gate; both list and download paths now route through it.
codex_round_3_verdict: APPROVED_WITH_COMMENTS
codex_round_3_comments:
  - Non-blocking #1: manifest that is valid JSON but non-object (list/string) would 500 on .get(). FIXED in same pass via isinstance(manifest, dict) guard.
  - Non-blocking #2: out-of-dir symlinks inside artifact tree would 500 on relative_to(). FIXED by try/except on rel-path compute, skip silently.
codex_verdict: APPROVED_WITH_COMMENTS (after 3 rounds, all findings closed)
codex_tool_report_path:
  - reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
  - reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round2.md
  - reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review_round3.md
counter_status: |
  v6.1 autonomous_governance counter 16 → 17.
  DEC-V61-031 autonomous_governance=true (src/ + byte-repro path, Codex
  triggered and closed 3 rounds). This is the first counter increment
  since RETRO-V61-001 reset.
reversibility: partially-reversible-by-pr-revert
  (Single atomic commit covers Wave 1+2+3 code + tests + DEC. Revert restores
  Phase 5a-only state. Integration artifacts under reports/phase5_fields/
  are gitignored so revert does not affect them.)
notion_sync_status: synced 2026-04-21 (https://www.notion.so/DEC-V61-031-Phase-7a-Field-post-processing-capture-LDC-MVP-349c68942bed81e2a90af03669957fb0)
github_pr_url: null (direct-to-main per Phase 5b precedent)
github_merge_sha: pending
github_merge_method: direct commit on main
external_gate_self_estimated_pass_rate: 0.75
  (Actual Codex result: CHANGES_REQUIRED → CHANGES_REQUIRED → APPROVED_WITH_COMMENTS
  over 3 rounds. Self-estimate of 0.75 was optimistic — actual first-round pass
  rate was 0%. Calibration insight for RETRO-V61-002: src/ + backend multi-file +
  path-traversal surfaces should default to 0.50, not 0.75. Codex caught 2 real
  security issues (URL collision + run_id traversal) that automated testing
  missed.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-029 (Phase 5b LDC simpleFoam migration complete; audit_real_run fixture baseline)
  - DEC-V61-030 (Q-5 closure; Ghia 1982 gold re-transcription)
  - ROADMAP.md Phase 7 proposal (commit e4dd1d9)
  - Phase 7a planning artifacts: 07a-CONTEXT.md + 07a-RESEARCH.md + 3 PLAN.md files (commit 81907c2)
---

# DEC-V61-031: Phase 7a — Field post-processing capture (LDC MVP)

## Why now

User deep-acceptance feedback on /learn + /validation-report pointed out the
core credibility gap: "所有的 case 都没有真实的仿真结果后处理云图，也没有科研级的
CFD vs gold case 的报告，这导致了你的 report 非常单薄，没有说服力。"

Phase 7 ROADMAP proposed 6 sub-phases to close this gap; Phase 7a lands the
data-capture foundation without which 7b/7c (rendering + comparison report)
cannot produce real visuals. Sprint 1 depth-first on LDC — Sprint 2 fans out
to the other 9 whitelist cases.

## What landed

### Wave 1 (commit 8bf2cfb) — Source-side emission
- `src/foam_agent_adapter.py::_emit_phase7a_function_objects` — new helper emits
  OpenFOAM v10 `controlDict.functions{}` block with:
  - `sample` function object, list-form `sets (uCenterline { type lineUniform; axis y; start (0.05 0.0 0.005); end (0.05 0.1 0.005); nPoints 101; });` — physical coords per convertToMeters 0.1
  - `residuals` function object writing `postProcessing/residuals/0/residuals.dat`
  - `yPlus` stubbed for future turbulent cases (not emitted for LDC laminar)
  - `writeControl timeStep; writeInterval 500` (iteration-based for steady simpleFoam)
- `src/foam_agent_adapter.py::FoamAgentExecutor._capture_field_artifacts` — new
  method, sibling of `_copy_postprocess_fields`. Runs `foamToVTK -latestTime
  -noZero -allPatches` inside Docker container, `docker get_archive` tar-extracts
  VTK/ tree to host, derives `residuals.csv` from `residuals.dat`. Called before
  teardown finally. Exceptions swallowed — comparator still succeeds on capture failure.
- `scripts/phase5_audit_run.py::_phase7a_timestamp + _write_field_artifacts_run_manifest`
  — driver authors single `YYYYMMDDTHHMMSSZ` timestamp, writes per-run manifest
  `reports/phase5_fields/{case_id}/runs/{run_label}.json` only for opted-in cases
  AND only when artifact dir is non-empty.
- `src/models.py::TaskSpec.metadata: Optional[Dict[str, Any]] = None` — new field
  to carry `phase7a_timestamp` + `phase7a_case_id` through the adapter.

### Wave 2 (commit f507b9e) — Backend surface
- `ui/backend/schemas/validation.py` — `FieldArtifact`, `FieldArtifactKind`, `FieldArtifactsResponse` Pydantic models (kind ∈ {vtk, csv, residual_log}).
- `ui/backend/services/run_ids.py` — `parse_run_id("{case}__{label}")` using `rpartition("__")`, strict identifier regex `^[A-Za-z0-9][A-Za-z0-9_\-]*$` on both segments (rejects `.`, `..`, `/`, `\`, `%`, empty, url-encoded forms).
- `ui/backend/services/field_artifacts.py` — `_resolve_artifact_dir` shared validator (enforces `YYYYMMDDTHHMMSSZ` timestamp shape + dir containment check); `list_artifacts` returns sorted manifest with POSIX-relative filenames; `resolve_artifact_path` for file downloads; `sha256_of` with `(path, st_mtime_ns, st_size)` cache key.
- `ui/backend/routes/field_artifacts.py` — `GET /api/runs/{run_id}/field-artifacts` + `GET /api/runs/{run_id}/field-artifacts/{filename:path}` via FileResponse + explicit MIME map. NOT StaticFiles.
- `ui/backend/main.py` — router registration.
- `ui/backend/tests/test_field_artifacts_route.py` — 18 tests covering manifest, download, traversal (filename + run_id + timestamp), subpath collision, non-object manifest, symlink escape.

### Wave 3 (this commit) — Codex closure + integration evidence + governance
- Integration run: real OpenFOAM `cfd-openfoam` Docker container, simpleFoam
  1024 iter / 27s, 8 artifacts produced at
  `reports/phase5_fields/lid_driven_cavity/20260421T082340Z/`.
- HTTP smoke: `GET /api/runs/lid_driven_cavity__audit_real_run/field-artifacts`
  → 200 + 8 artifacts + valid SHA256 + subpath URLs.
- Codex rounds 1-3 resolved 5 findings + 2 hardening comments (see frontmatter).
- `.gitignore` rule excludes `reports/phase5_fields/*/20*/` blobs; `runs/*.json`
  manifest kept (small).
- `ui/backend/tests/fixtures/` updated — 18 field_artifacts tests, fixture VTK
  + sample + residual files committed at `phase7a_sample_fields/`.

## Verification

| Check | Result |
|---|---|
| Backend pytest | ✅ 97/97 (was 79/79 pre-Phase-7a; +18 new tests, zero regression) |
| Frontend tsc --noEmit | ✅ clean (no frontend change in 7a; deferred to 7f) |
| Real OpenFOAM integration run | ✅ LDC simpleFoam 1024 iter, 8 artifacts on disk |
| HTTP manifest endpoint | ✅ 200 + 8 unique subpath URLs + matching SHA256 |
| HTTP download endpoint | ✅ 200 on `sample/500/uCenterline.xy` subpath |
| Path-traversal defense | ✅ 400 on `..__pwn`, `%2e%2e__pwn`, `../../outside` timestamp, symlink escape, `.._etc_passwd` filename |
| Byte-repro test | ✅ 12/12 (subset-check safe — `field_artifacts` is manifest-ref only, no embedded timestamp) |
| Codex 3-round review | ✅ APPROVED_WITH_COMMENTS (all 5 findings + 2 hardening closed) |

## Honest residuals

1. **7a delivers data capture only.** Users visiting `/validation-report/lid_driven_cavity` today see exactly the same scalar table as yesterday. The PNG contours + Plotly profile overlays + 8-section scientific report come in Phase 7b + 7c.
2. **LDC-only.** Other 9 cases' controlDicts don't yet emit the Phase 7a `functions{}` block. Running `phase5_audit_run.py backward_facing_step` etc. will succeed but produce no field-artifacts manifest. Phase 7c Sprint-2 fans this out.
3. **No y+ for turbulent cases.** The yPlus stub is in the code path but not exercised (LDC is laminar). Phase 7c Sprint-2 will first exercise it on the turbulent cases (turbulent_flat_plate, BFS, duct_flow).
4. **No integration test that runs the solver.** pytest uses committed fixture artifacts; the Docker + OpenFOAM integration run is a manual `/gsd-execute-phase` concern — an automated test here would require Docker-in-CI which is out of scope.

## Delta

| Metric | Pre-7a | Post-7a |
|---|---|---|
| Backend pytest | 79/79 | **97/97** (+18) |
| audit_real_run artifacts for LDC | 0 (scalar only) | **8 files on disk + HMAC-ready manifest** |
| Field artifact route | absent | **GET /api/runs/{run_id}/field-artifacts** |
| Codex triggers caught | N/A | **2 HIGH security issues** (URL collision + run_id traversal) |
| v6.1 counter | 16 | **17** |
| External gate queue | 0 open | **0 open** (no new Q-gate filed) |

## Pending closure

- [x] Wave 1 commit (8bf2cfb)
- [x] Wave 2 commit (f507b9e)
- [x] Integration run evidence captured
- [x] Codex 3 rounds closed (APPROVED_WITH_COMMENTS)
- [x] 97/97 pytest green
- [x] DEC-V61-031 drafted
- [ ] Atomic Wave 3 commit (Codex fixes + DEC + STATE + ROADMAP + .gitignore)
- [ ] Push to origin/main
- [x] Notion sync DEC-V61-031 (https://www.notion.so/DEC-V61-031-Phase-7a-Field-post-processing-capture-LDC-MVP-349c68942bed81e2a90af03669957fb0)
- [x] ROADMAP Phase 7a → COMPLETE marker (done in Wave 3 commit 0f74095)
