---
decision_id: DEC-V61-033
timestamp: 2026-04-21T20:00 local
scope: |
  Close the three remaining Phase 7 sub-phases that DEC-V61-032 explicitly
  deferred: (1) Phase 7b polish — real 2D VTK contour + streamline rendering
  replacing the MVP centerline strip; (2) Phase 7d — Richardson grid-
  convergence index (p_obs + GCI_21 + GCI_32) computed from existing
  mesh_20/40/80/160 fixtures and embedded in §7 of the comparison report;
  (3) Phase 7e — L4 audit-package schema upgrade that embeds real Phase 7
  artifacts (VTK + PNGs + PDF + residuals + samples + log) into the HMAC-
  signed zip while preserving byte-reproducibility.

  Impact: (a) LDC /learn case page now shows a physically meaningful 2D U-
  magnitude contour with overlaid streamlines (replacing the 1D strip MVP);
  (b) §7 "Grid-convergence table" sub-section now shows observed order of
  accuracy p_obs=1.00 + GCI_32=5.68% + asymptotic-range verdict for LDC,
  grounded in Celik 2008 + Roache 1994 methodology; (c) POST /audit-package/
  build returns a 1.97 MB L4 zip containing 14 embedded Phase 7 artifacts
  (up from ~260 KB L3 manifest-only), with byte-identical SHA256 +
  HMAC across re-builds (live-verified: 39990076bfb634d0... × 2 +
  a80a549c3d90590d... × 2).
autonomous_governance: true
  (scripts/render_case_report.py touches an existing autonomous-allowed
  file. ui/backend/services/grid_convergence.py is a new autonomous-allowed
  file. src/audit_package/manifest.py + serialize.py edits are
  **byte-reproducibility-sensitive three-禁区 #1 path** → Codex mandatory
  per RETRO-V61-001 new trigger #2 + #3. Codex review executed with result
  recorded below.)
claude_signoff: yes
codex_tool_invoked: true
codex_rounds: 2
codex_round_1_verdict: CHANGES_REQUIRED
codex_round_1_findings:
  - CRITICAL: build_manifest(repo_root=X) + serialize.serialize_zip_bytes() repo_root drift — serialize hardcoded Path(__file__).parents[2], ignoring caller's repo_root → phase7 entries advertised in manifest but 0 embedded in zip for non-production repo_root callers. Test masked the bug via monkeypatch of _zip_entries_from_manifest.
  - IMPORTANT: Non-uniform-r GCI Celik iteration can raise OverflowError from `r ** p_guess` past the (ValueError, ZeroDivisionError) catch. Concrete reproducer (10, 16, 50) with f_h = 1 + 0.3*h^1.7. Propagates as 500 to comparison_report.
  - MISLEADING: p_obs == 0.0 (exact zero order) fell through with note="ok" and gci_21/gci_32=None, giving reader a false "all good" signal when data did not monotonically converge.
codex_round_2_verdict: APPROVED_WITH_COMMENTS
codex_round_2_findings:
  - NON-BLOCKING: build_manifest(repo_root=X) is not a fully hermetic repo_root override — knowledge/whitelist.yaml, knowledge/gold_standards/, and .planning/decisions/ reads still use module-level _WHITELIST_PATH/_GOLD_STANDARDS_ROOT/_DECISIONS_ROOT constants. Out of scope for this DEC; production route always uses defaults on both sides (verified). Tracked for a future hermetic-mode refactor if custom tmp-repo callers need full isolation.
codex_verdict: APPROVED_WITH_COMMENTS (round 2, zero blocking findings)
codex_tool_report_path:
  - reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round1.md
  - reports/codex_tool_reports/2026-04-21_phase7bde_codex_review_round2.md
counter_status: |
  v6.1 autonomous_governance counter 18 → 19.
  DEC-V61-033 autonomous_governance=true (byte-reproducibility-sensitive
  audit-package paths + multi-file backend + L4 schema spec → Codex
  mandatory per RETRO-V61-001 trigger #2 + #3).
reversibility: fully-reversible-by-pr-revert
  (Single atomic commit. Revert restores DEC-V61-032 Phase 7 state: MVP
  centerline strip contour, no GCI sub-section in comparison report, L3
  manifest-only audit packages. Revert safe because include_phase7 default
  True but returns None when no artifacts exist — non-opted-in cases
  unaffected either way.)
notion_sync_status: synced 2026-04-21 (https://www.notion.so/DEC-V61-033-Phase-7b-polish-7d-GCI-7e-L4-signed-zip-Phase-7-Sprint-1-closure-349c68942bed81c3b131e125f225c946)
github_pr_url: null (direct-to-main per Phase 7a + 7bc precedent)
github_merge_sha: 4399427 (feat) + afb2e5e (docs)
github_merge_method: direct commit on main (2 commits, pushed 2026-04-21)
external_gate_self_estimated_pass_rate: 0.45
  (Higher than DEC-V61-032's 0.35 because: (a) I already learned the
  path-containment pattern from 3 Codex rounds; (b) both the timestamp
  shape gate and resolved-path-under-root check are now defense-in-depth
  at both build_manifest and serialize_zip layers; (c) byte-reproducibility
  verified live before Codex invocation. Still below 70% because
  byte-reproducibility threats are subtle and Codex has a strong track
  record of finding them — PR-5b, PR-5c, PR-5c.1, PR-5c.2 all returned
  CHANGES_REQUIRED on first pass in this region.
  **Actual: round 1 CHANGES_REQUIRED × 3 findings (one CRITICAL zip/manifest
  drift I would not have caught without Codex's real-serialize probe);
  round 2 APPROVED_WITH_COMMENTS. Estimate 0.45 tracks reality within
  noise — honest.**)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-031 (Phase 7a field capture — produces artifacts now embedded in L4 zip)
  - DEC-V61-032 (Phase 7b/7c MVP + 7f MVP — this DEC closes the 7b polish + 7d + 7e remainder)
  - DEC-V61-023 (Phase 6 L3 build_fingerprint rename — this DEC's L4 supersedes L3)
  - RETRO-V61-001 (expanded Codex-per-risky-PR trigger set — this DEC invokes #2 + #3)
---

# DEC-V61-033: Phase 7b polish + Phase 7d + Phase 7e — 2D contour, Richardson GCI, L4 signed-zip

## Why now

DEC-V61-032 landed the user-visible Sprint 1 MVP (real profile + deviation
+ residuals + comparison report HTML/PDF) but explicitly deferred three
items because they did not gate the deep-acceptance user ask:

- 7b polish: the MVP contour was a 1D centerline strip because VTK
  parsing was not yet wired.
- 7d: Richardson GCI is a numerical refinement that changes §7 table
  content but not the overall report shape.
- 7e: L4 signed-zip embedding is audit-package integration; end-users
  already had PDF download via the 7c route.

User directive "接着推进，把你发现的剩余收口项都完成" (continue pushing
until all items close) commits to Phase 7 Sprint 1 full completion. Only
Phase 7c Sprint 2 (fan-out to 9 other cases) remains afterward, and that
work is gated on OpenFOAM integration × 9 + per-case adapter opt-in edits —
a distinct scope from this closure.

## What landed

### Phase 7b polish — 2D VTK contour + streamline (`scripts/render_case_report.py`)

- New `_find_latest_vtk(artifact_dir)` helper walks `VTK/*.vtk` and
  returns the latest file by sorted name (deterministic; last iteration).
- `render_contour_u_magnitude_png` replaced: parses OpenFOAM volume VTK
  via PyVista 0.47.3, extracts cell-centered `U`, `Cx`, `Cy`, reshapes
  into a 129×129 structured grid (LDC mesh), renders matplotlib
  `contourf` of |U| with 20 levels + `streamplot` at density 1.1 with
  white lines.
- Float-precision subtlety: streamplot demands equally-spaced 1D x/y
  axes (internal equality check). VTK cell centers have 8th-digit jitter,
  so we rebuild `x1d = np.linspace(x_min, x_max, side)` from bounding
  box rather than passing raw `Cx[:side]`.
- Graceful fallback: any parse/reshape failure falls back to the MVP 1D
  centerline strip, so non-LDC runs (or corrupted VTK) still produce
  *some* contour output.
- LDC live result: a publication-style cavity contour where the primary
  clockwise vortex is visible with ~3 streamline whorls and U-magnitude
  peaking at the moving lid (≈1.0) and vanishing in the bottom-left
  corner (≈0). Superior to the 1D strip MVP by a wide margin.

### Phase 7d — Richardson GCI (`ui/backend/services/grid_convergence.py`, ~220 LOC, new)

- Celik 2008 + Roache 1994 implementation.
- `compute_richardson_gci(coarse, medium, fine)` with `MeshSolution`
  dataclass (label, n_cells_1d, value) inputs.
- Refinement ratios `r_21 = medium/coarse`, `r_32 = fine/medium` both
  >1 (Celik convention: r = h_coarse / h_fine = N_fine / N_coarse).
- Uniform-r fast path: `p_obs = |ln(|eps_32/eps_21|)| / ln(r)` closed-form.
- Non-uniform-r: Celik iterative method (50 iter cap, relative
  convergence < 1e-6).
- Degenerate cases:
  - `eps_21 * eps_32 < 0` → oscillating convergence, `p_obs=None`,
    note populated.
  - `|eps| < 1e-14` → converged to numerical precision, `p_obs=None`,
    note populated.
- GCI formulae (Fs=1.25 for 3-grid studies per Celik):
  - `GCI_21 = Fs * |eps_21| / (r_21^p - 1)`
  - `GCI_32 = Fs * |eps_32| / (r_32^p - 1)`
- Denominator per Celik Eq.4: `eps_21` uses `|medium.value|` denominator,
  `eps_32` uses `|fine.value|` — the refined/downstream solution, not
  upstream. Guard `abs(x) > 1e-12` before division.
- Asymptotic-range verdict: `GCI_21 / (r_21^p * GCI_32) ∈ [0.8, 1.25]`
  → `asymptotic_range_ok=True`.
- `compute_gci_from_fixtures(case_id, fixture_root)` reads
  `knowledge/gold_standards/cases/{case_id}/mesh_{N}_measurement.yaml`
  for N ∈ {40, 80, 160} and computes GCI. Returns None if <3 meshes
  exist (graceful, non-raising).
- `comparison_report.py::build_report_context` now calls this and
  passes `gci: {p_obs, f_extrapolated, gci_21, gci_32,
  asymptotic_range_ok, note}` via new `_gci_to_template_dict` helper.
- `comparison_report.html.j2` §7 renders the sub-table when GCI is non-
  null. References Celik 2008 JFE paper.
- LDC live result: `p_obs=1.00`, `GCI_32=5.68%`, `asymptotic_range_ok=True`.
  Below the formal scheme order (2nd) but in-family for first-refinement
  behavior on a cavity problem where boundary-layer resolution dominates.

### Phase 7e — L4 signed-zip embedding (`src/audit_package/manifest.py` + `serialize.py`)

- `_PHASE7_TIMESTAMP_RE = ^\d{8}T\d{6}Z$` gate applied to any
  `runs/{run}.json::timestamp` value before filesystem composition.
  Tampered values (`../../outside`, URL-encoded traversal, etc.) rejected.
- `_collect_phase7_artifacts(case_id, run_id, repo_root) -> Optional[Dict]`:
  walks three sanctioned roots (`reports/phase5_fields/{case}/`,
  `reports/phase5_renders/{case}/`, `reports/phase5_reports/{case}/`),
  validates each file's resolved path stays under one of them (else
  silently drop — symlink escape defense), computes SHA256 + size, emits
  entries sorted alphabetically by `zip_path`. VTK files >50 MB
  silently skipped to cap zip bloat on high-res runs.
- `build_manifest(..., include_phase7: bool = True)` kwarg defaults True;
  when True AND `_collect_phase7_artifacts` returns a non-None dict,
  manifest gains a `"phase7"` top-level key with `{schema_level: "L4",
  canonical_spec: "docs/specs/audit_package_canonical_L4.md", entries,
  total_files, total_bytes}`. When False OR no artifacts exist, key is
  omitted entirely (backward compat with L3 consumers + pre-Phase-7
  audit packages).
- `serialize._zip_entries_from_manifest` now iterates
  `manifest["phase7"]["entries"]` and adds every file. Defense-in-depth:
  every `disk_path_rel` is re-resolved via `Path.resolve(strict=True)`
  and verified `.relative_to(repo_root.resolve())` — a tampered manifest
  between build_manifest and serialize_zip still cannot exfiltrate
  outside-repo files.
- Sorted zip entry order + epoch mtime (1980-01-01 per `_fixed_zipinfo`)
  + deterministic compression level preserved from L3 → L4.
- `docs/specs/audit_package_canonical_L4.md` (new) documents schema,
  size characteristics (1.97 MB typical vs ~260 KB L3), byte-repro
  contract, security, backward compat. Supersedes L3 spec.
- Live verification: two consecutive `POST /api/cases/lid_driven_cavity/
  audit-package/build?run_id=audit_real_run` calls produced
  byte-identical `bundle.zip` SHA256 `39990076bfb634d0...` and
  byte-identical HMAC `a80a549c3d905908...`. Byte-reproducibility
  preserved across the schema upgrade.

## Test coverage added

- `ui/backend/tests/test_grid_convergence_gci.py` (7 tests):
  synthetic 2nd-order (p_obs≈2.0), synthetic 1st-order (p_obs≈1.0),
  rejects non-monotone refinement, oscillating convergence note,
  converged-to-precision note, LDC fixtures end-to-end (p_obs ∈ (0.5,
  2.5), GCI_32 ∈ (0, 1.0)), returns None on insufficient fixtures.
- `ui/backend/tests/test_audit_package_phase7e.py` (8 tests): happy path
  + schema_level="L4", no-artifacts → returns None, tampered timestamp
  rejected (no leak to `/etc/passwd_fake` plant), regex shape gate
  adversarial inputs, build_manifest embeds phase7 key, opt-out
  (include_phase7=False → no key), zip embedding byte-equality,
  byte-reproducibility across two build_manifest + serialize_zip calls.

## Codex round 1 findings → fixes applied

1. **CRITICAL — serialize/build_manifest repo_root drift**:
   - `serialize._zip_entries_from_manifest(manifest, repo_root=None)` and
     `serialize_zip_bytes(manifest, repo_root=None)` and `serialize_zip(
     manifest, output_path, repo_root=None)` all now accept a repo_root
     override. Defaults centralized in `_default_repo_root()` matching
     `manifest._REPO_ROOT`.
   - Production route `audit_package.py::POST build` unchanged — uses
     defaults on both sides; both resolve to the same absolute path
     (verified).
   - Test `test_zip_contains_phase7_entries` now calls
     `serialize_zip_bytes(m, repo_root=tmp_path)` directly — monkeypatch
     of `_zip_entries_from_manifest` removed.
   - Test `test_byte_reproducibility_with_phase7` extended to verify
     `z1 == z2` for real zip bytes + `len(phase7_names) == len(manifest[
     "phase7"]["entries"])`.
   - New test `test_zip_omits_phase7_on_repo_root_mismatch` documents
     the silent-drop hazard when a caller passes repo_root to
     build_manifest but forgets it on serialize.

2. **IMPORTANT — non-uniform-r GCI OverflowError**:
   - Inner Celik iteration catch expanded to
     `(ValueError, ZeroDivisionError, OverflowError)` — escape to
     `p_guess=None` + `note="non-uniform refinement iteration diverged
     (numerical overflow on asymmetric mesh triple); p_obs omitted"`.
   - Final GCI + Richardson block wrapped in try/except OverflowError
     for `r_fine ** p_obs`, `r_21 ** p_obs`, `r_32 ** p_obs` — gci
     cleared to None + note populated.
   - `comparison_report.py::build_report_context` boundary catch
     expanded to `(ValueError, ImportError, OverflowError,
     ArithmeticError)` — defense-in-depth against any deep math we
     did not predict.

3. **MISLEADING — p_obs == 0.0 masked by `note="ok"`**:
   - New branch in `grid_convergence.py` sets note to
     `"zero observed order of accuracy — refinement signal does not
     decay; Richardson extrapolation does not apply and GCI is not
     meaningful"` and normalizes `p_obs` to None.
   - Scoped with `and note == "ok" and not diverged` to avoid
     clobbering earlier oscillating / converged-to-precision notes.

## Codex round 2 non-blocking comment (tracked, not fixed in this DEC)

- `build_manifest(repo_root=X)` is not fully hermetic — knowledge/
  whitelist.yaml, knowledge/gold_standards/, and .planning/decisions/
  reads still use module-level constants. This is **pre-existing**
  behavior, not introduced by Phase 7d/e. Production route always
  uses defaults on both sides. A future refactor could plumb
  `whitelist_path`, `gold_root`, `decisions_root` through as optional
  kwargs for fully-hermetic tmp-repo callers — but that's scope for
  a follow-up DEC if/when a use case surfaces.

## Regression gate

`PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q` → **132/132 passed**
(was 114/114 post-DEC-V61-032 → +8 Phase 7e tests + 9 GCI tests + 1
zip_mismatch_hazard test = +18 net; also flushed 3 new tests added
during round 1 fix cycle: overflow_recovery, zero_order_flagged,
repo_root_mismatch_hazard). Zero flakes. ~25s wall.

## Honest residuals (carried / introduced)

- **Phase 7c Sprint 2 fan-out still deferred**: 9 other whitelist cases
  (BFS, TFP, duct_flow, impinging_jet, naca0012, DHC, RBC, cylinder,
  plane_channel) still show old static placeholder PNGs. Unblocked work:
  run OpenFOAM integration × 9 + per-case adapter opt-in edits. Out of
  scope for this DEC per "接着推进" directive interpretation.
- **VTK >50 MB silent skip**: not recorded in manifest for audit
  completeness. Low risk for current LDC 3.1 MB / N=129 scale; revisit
  if high-res runs (N≥400) become routine.
- **Non-LDC L4 bundles are "empty" for phase7 key**: `include_phase7=True`
  default + `_collect_phase7_artifacts` returns None for non-opted-in
  cases → no phase7 key. Graceful but means 9 cases still ship L3-
  equivalent packages until 7c Sprint 2 opts them in.

## Counter arc

Pre: counter 18 (DEC-V61-032).
Post: counter 19 (this DEC, autonomous_governance=true, Codex-mandatory
path + Codex invoked).

## Related decisions

- DEC-V61-023 — L3 `generated_at` → `build_fingerprint` rename (L3→L4 this DEC)
- DEC-V61-031 — Phase 7a field capture (artifacts consumed by L4)
- DEC-V61-032 — Phase 7b MVP + 7c MVP + 7f MVP (this DEC closes the 3 remainders)
- RETRO-V61-001 — Codex-per-risky-PR trigger set (#2 byte-repro + #3 schema rename invoked here)
