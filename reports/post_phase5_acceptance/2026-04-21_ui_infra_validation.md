# Post-Phase-5 UI Infrastructure Validation · Part 1

**Date**: 2026-04-21T05:15 local
**Operator**: Claude Opus 4.7 (1M context)
**Main SHA**: `a02c3a2c0f91` (after RETRO-V61-001 ratification)
**Scope**: §5d Part 1 — bring up UI backend + frontend + Docker container, validate PR-5d.1 fixes over live HTTP. **Real-solver 10-case dashboard runs are deferred to Part 2 pending Kogami scope decision.**

---

## Summary

All three PR-5d.1 Codex fixes are **confirmed working in live-HTTP production context**, not just under `pytest + TestClient`:

| Fix | Live HTTP evidence |
|---|---|
| **HIGH #1** · unknown case_id → 404 | `POST /api/cases/nonexistent_case/runs/r1/audit-package/build` returns `HTTP 404` with body `{"detail": "unknown case_id: 'nonexistent_case' (not in knowledge/whitelist.yaml)"}` |
| **HIGH #2** · byte-reproducibility | Two identical POSTs to `lid_driven_cavity/runs/p2-probe` → identical `generated_at` (`2bcf091efc3d3aa9`), identical `signature_hex`, differing `bundle_id` (uuid4 per-request, as designed) |
| **MEDIUM** · evidence_summary rename | Response JSON contains `evidence_summary` (8 areas); legacy `vv40_checklist` key is **absent** |

PDF is unavailable on this host (weasyprint native libs missing — known limitation, not a PR-5d.1 regression). All other download endpoints work:

```
GET /api/audit-packages/{bundle_id}/manifest.json → 200, 2191 bytes
GET /api/audit-packages/{bundle_id}/bundle.zip    → 200, 2278 bytes
GET /api/audit-packages/{bundle_id}/bundle.html   → 200, 4132 bytes
GET /api/audit-packages/{bundle_id}/bundle.sig    → 200, 65 bytes (64-hex + newline)
```

---

## Infrastructure state

| Component | Status | Detail |
|---|---|---|
| Docker daemon | ✅ up | v29.2.1, linux/arm64 (Apple Silicon) |
| OpenFOAM container | ✅ running | `cfd-openfoam` (was stopped; restarted) · image `cfd-workbench/openfoam-v10:arm64` · mount `/tmp/cfd-harness-cases:/tmp/cfd-harness-cases` · `simpleFoam` in PATH |
| FastAPI backend | ✅ up on :8000 | HMAC secret set via env; `/api/cases` returns 10 whitelist cases |
| Vite frontend | ✅ up on :5174 | (port 5173 occupied by unrelated "AI FANTUI Logic" process; rebooted on 5174) |
| Whitelist cases | 10 loaded | lid_driven_cavity · backward_facing_step · circular_cylinder_wake · turbulent_flat_plate · duct_flow · differential_heated_cavity · plane_channel_flow · impinging_jet · naca0012_airfoil · rayleigh_benard_convection |
| Contract status mix | 2 FAIL · 1 HAZARD · 7 UNKNOWN | UNKNOWNs are cases without measurement fixtures — orthogonal to PR-5d.1 |

---

## Bundle probe · skeleton shape

Probed `POST /api/cases/lid_driven_cavity/runs/p2-acceptance-1/audit-package/build`:

- `bundle_id`: `be11b9e09d634b27a28c9a9d77f71433` (uuid4)
- `manifest_id`: `lid_driven_cavity-p2-acceptance-1`
- `generated_at`: `2bcf091efc3d3aa9` (deterministic 16-hex — PR-5d.1 L3 finding acknowledges this is opaque; rename to `build_fingerprint` queued)
- `git_repo_commit_sha`: `a02c3a2c0f91` (main HEAD at probe time)
- `signature_hex`: `5344735bcf3cbca1a94e693ee0bdea284919c39db02d63a9118e9d590ab8ef22`
- `pdf_available`: `False` (weasyprint absent)
- `evidence_summary` length: 8 items

Downloaded `bundle.zip` contents:

```
case/whitelist_entry.json           907 bytes · mtime 1980-01-01 (deterministic)
decisions/DEC-V61-007.txt           152 bytes · mtime 1980-01-01
decisions/DEC-V61-011.txt           182 bytes · mtime 1980-01-01
manifest.json                      2191 bytes · mtime 1980-01-01
```

Skeleton bundle is working as designed: `run.status="no_run_output"`,
`measurement.comparator_verdict=None`, `case.gold_standard=None` (loader
fallback not resolving this particular case — orthogonal to PR-5d.1, may be
a lookup mismatch between `load_case_detail` and `_load_gold_standard` for
`lid_driven_cavity`). The **whitelist_entry and decision_trail (2 DECs)
are correctly included**, demonstrating the bundle is not empty when the
case is known.

---

## Visual verification (manual — live URLs)

The UI is live at the following endpoints while the acceptance session is active. Open in browser + visually confirm the 6 Path-B screens render:

- **http://127.0.0.1:5174/** — Validation Report (Screen 4) for the 10 cases
- **http://127.0.0.1:5174/case-editor** — Case Editor (Screen 1)
- **http://127.0.0.1:5174/decisions** — Decisions Queue (Screen 2)
- **http://127.0.0.1:5174/run-monitor** — Run Monitor (Screen 3)
- **http://127.0.0.1:5174/dashboard** — Dashboard (Screen 5)
- **http://127.0.0.1:5174/audit-package** — Audit Package Builder (Screen 6)

**Screen 6 PR-5d.1 visual checks**:

- Section heading reads "Internal V&V evidence summary" (NOT "FDA V&V40 credibility-evidence mapping")
- Subtitle reads "Not a substitute for a formal FDA/ASME V&V40 template. Fields scoped to run artifacts (run.inputs, run.outputs.*, measurement.*) are empty in skeleton bundles."
- Page-level description no longer mentions FDA/aerospace/nuclear licensing claims
- Building a bundle with case=`duct_flow`, run_id=`test-1` succeeds and shows 5 download links (PDF row disabled with "PDF unavailable" hint)
- Building a bundle for a nonexistent case id surfaces an error to the user (404 path)

*(Screenshots cannot be automated from this environment; operator verifies visually.)*

---

## Regression state (last full matrix)

Run at main `a02c3a2` (post PR-5d.1 + retro):

```
pytest 9-file matrix → 327 passed + 1 skipped in 2.91s
pytest audit_package route (live with HMAC env) → 18 passed
tsc --noEmit on ui/frontend → clean
```

---

## Part 2 scope — pending Kogami decision

§5d Part 2 is the full real-solver dashboard validation originally described in the handoff doc. It requires running all 10 whitelist cases through `FoamAgentExecutor` (real OpenFOAM, not MOCK) and capturing the resulting Screen 4 / 5 / 6 state.

**Estimated runtime by case** (host: Apple Silicon M-series, `simpleFoam` single-threaded inside `cfd-openfoam` container):

| Case | Expected runtime | Acceptance criterion |
|---|---|---|
| `lid_driven_cavity` | 1-3 min | PASS; Ghia 1982 references |
| `backward_facing_step` | 3-8 min | PASS; Driver & Seegmiller 1985 |
| `circular_cylinder_wake` | 5-15 min | PASS; Williamson 1996 |
| `turbulent_flat_plate` | 5-15 min | PASS; Spalding wall fn |
| `plane_channel_flow` | 5-15 min | PASS; Kim 1987 |
| `duct_flow` | 3-10 min | FAIL (documented — Jones 1976 rectangular-duct correlation) |
| `impinging_jet` | 10-30 min | PASS; 2D axisymmetric only |
| `naca0012_airfoil` | 20-60 min | PASS_WITH_DEVIATIONS |
| `differential_heated_cavity` | 10-30 min | PASS_WITH_DEVIATIONS; Ra=1e6 per DEC-V61-006 P-2 |
| `rayleigh_benard_convection` | 30-90 min | PASS_WITH_DEVIATIONS; h URF=0.05 per 2026-04-17 fix |

**Total estimate: 1.5 – 5 hours** wall-clock depending on NACA + Rayleigh-Bénard convergence. Container is single-threaded unless we parallelize runs (not currently wired).

**Scope options for Kogami**:

- **Option A** — full 10 cases. Produces canonical §5d dashboard evidence. 1.5-5 hours of compute. I stream progress via Monitor + write per-case Screen 4/5/6 state snapshots + final acceptance report.
- **Option B** — fast 3-case subset (LDC + backward_facing_step + duct_flow). Covers PASS + PASS + FAIL contract-status diversity. ~15-30 min. Trades coverage for turnaround.
- **Option C** — fast 5-case subset (A + plane_channel_flow + turbulent_flat_plate). Covers PASS / FAIL / HAZARD. ~30-60 min.
- **Option D** — defer Part 2 entirely; Part 1 (this report) is sufficient validation that PR-5d.1 works. Move to Phase 6 scoping.

**Claude's recommendation**: **Option B or C**, because:
- The PR-5d.1 HIGH/MEDIUM fixes have already been validated over live HTTP in Part 1.
- Part 2's value is *dashboard visual acceptance for commercial review*, not PR-5d.1 regression testing.
- A 3-5 case subset gives enough variety to screenshot a non-empty Screen 4 + populated Screen 5 dashboard; the last 5 cases would be repeated visual evidence with diminishing acceptance-value-per-hour.
- 1.5-5 hours of single-threaded CFD for "visual confirmation" is a high cost; if the dashboard is going to get regression-tested continually, that's a separate CI story, not acceptance.

**If Option A is still preferred**, I'll kick it off and monitor — just say "A" and I'll start.

---

## Reversibility

To tear down the Part 1 infra:

```bash
# Stop frontend + backend background tasks
# (handled by Claude's TaskStop on session end; or operator kills :8000 + :5174)

# Stop OpenFOAM container (optional; keep it for Part 2)
docker stop cfd-openfoam

# Staging dir accumulated from build probes (safe to keep or clean)
rm -rf /Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/.audit_package_staging/*
```

No committed artifacts are affected by teardown. The only new repo content is this report and (after Part 2 is scoped/completed) any Part 2 evidence files.

---

## Commits expected from this session

- `docs(acceptance): land post-Phase-5 §5d Part 1 — UI infra validation` (this file, to be committed after user confirms Part 2 scope)

Optional housekeeping (can fold in):
- Cleanup of stray `.stale.*` and `.timestamp-*.mjs` files in repo root (pre-existing; untracked; not PR-5d.1 related).
