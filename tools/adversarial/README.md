# Adversarial CFD test loop

Catches structural defects in the cfd-harness pipeline (import → mesh → BC → solve) by driving plausible CAD geometries through every stage and asserting convergence. Every defect found in this loop becomes a regression case for future PRs.

## Why this exists

The 2026-04-30/05-01 adversarial arc surfaced 8 critical/high defects (1, 2a, 4, 5, 6, 7, 8 fixed; 2b deferred to DEC-V61-104). Several were post-R3 defects — Codex APPROVE'd code that failed at runtime — exactly the gap RETRO-V61-053's `executable_smoke_test` risk flag was raised to address. **Defect 8 (iter06 symmetry constraint type) was discovered during a manual smoke test.** Without a permanent runner, the next backend PR could regress symmetry handling and we wouldn't know until someone re-ran the case.

`run_smoke.py` is that permanent runner. It drives every case in `cases/iter*/` through the live backend and asserts each case's declared expected outcome.

## Layout

```
tools/adversarial/
├── README.md                      ← this file
├── run_smoke.py                   ← executable smoke runner (CLI)
├── cases/
│   ├── iter01/                    ← thin-blade plenum (interior obstacle, expected_failure_v61_104)
│   ├── iter02/                    ← axis-aligned duct, 3 patches
│   ├── iter03/                    ← manual-BC baseline (skipped by runner)
│   ├── iter04/                    ← rotated L-bend (Euler 15/30/20°), 3 patches
│   ├── iter05/                    ← rotated T-junction (Euler 21/-28/17°), 4 patches inc. 2 inlets
│   ├── iter06/                    ← half-pipe with symmetry plane, 4 patches inc. SYMMETRY
│   └── iter*/intent.json          ← per-case BC intent + smoke_runner config
└── results/
    └── iter0X_findings.md         ← human-readable defect logs from each iteration
```

Each case directory typically contains:

- `geometry.stl` — multi-solid ASCII STL (one solid per named patch)
- `intent.json` — patch BC intent + solver params + `smoke_runner` block
- `generate.py` — (optional) regenerator script for the STL
- `case_id.txt` — last imported case_id (for reproducing local debug runs)

## Smoke runner usage

Prerequisites: backend on `http://127.0.0.1:8003` with the cfd-openfoam container running. Override the URL via `--base-url` or `CFD_BACKEND_URL`.

```bash
# Start backend (one-time per session)
source .venv/bin/activate
uvicorn ui.backend.main:app --host 127.0.0.1 --port 8003 --log-level warning &

# Run the full suite
python tools/adversarial/run_smoke.py

# Filter to one case
python tools/adversarial/run_smoke.py --filter iter06

# Machine-readable output
python tools/adversarial/run_smoke.py --json > results.json
```

Exit codes:

- `0` — all cases met their declared expected outcome (PASS or EXPECTED_FAILURE)
- `1` — one or more cases failed unexpectedly (FAIL or UNEXPECTED_PASS)
- `2` — backend not reachable, or no cases matched the filter

## Per-case expected_status

Each case's `intent.json` declares a `smoke_runner.expected_status`:

| status | semantics |
|---|---|
| `converged` | full pipeline must complete and `last_continuity_error` indicates convergence (the default) |
| `manual_bc_baseline` | uses author_dicts.py / a case-specific driver, not the standard from_stl_patches mode — runner skips |
| `physics_validation_required` | case converges numerically at smoke scale (no divergence, finite residuals) but the underlying physics is wrong (e.g. iter01's interior-obstacle plenum where gmsh fills the void with fluid). The convergence-based smoke can't catch this defect class; needs analytical or experimental comparison. Skipped here; kept as adversarial canary for the future analytical-comparator runner. |
| `expected_failure_v61_104` | known to fail (divergence, not wrong-physics) until DEC-V61-104 ships. Failure logged but doesn't fail the suite. UNEXPECTED_PASS triggers an investigation (probably means V61-104 silently landed). |

## Adding a new case

1. Drop a multi-solid ASCII STL at `tools/adversarial/cases/iter<N>/geometry.stl` (use `tools/adversarial/cases/iter06/generate.py` as a hand-crafted template, or have Codex generate one).
2. Author `intent.json` describing patches + solver intent. Add a `smoke_runner` block with the appropriate `expected_status`.
3. Run `python tools/adversarial/run_smoke.py --filter iter<N>` to validate.
4. Document the result in `tools/adversarial/results/iter<N>_findings.md` (or extend the existing index).
5. Commit the case + findings together.

## Pre-push hook integration

For backend changes touching the import / mesh / BC / solve hot paths, run the smoke suite before pushing. Wrapper script:

```bash
# .git/hooks/pre-push (project-local)
if git diff --name-only HEAD~..HEAD | grep -qE "ui/backend/(services/(meshing_gmsh|case_solve|geometry_ingest)|routes/(import_geometry|mesh_imported|case_solve))"; then
  echo "Backend hot-path changed — running adversarial smoke suite."
  source .venv/bin/activate
  python tools/adversarial/run_smoke.py || {
    echo "✗ adversarial smoke FAILED — fix or bypass with CFD_SMOKE_OVERRIDE=1"
    [ "$CFD_SMOKE_OVERRIDE" = "1" ] || exit 1
  }
fi
```

(Currently advisory — not auto-installed. Drop into `.git/hooks/pre-push` to enable locally; promote to a `pre-commit-config.yaml` entry once the runner has soaked.)

## Defects fixed by this loop

| # | severity | case | fix commit |
|---|----------|------|------------|
| 1 | critical | iter01 | b8053f9 — weld seam vertices in stl_loader.combine |
| 2a | critical | iter02 | 3b811c2 + fa76b53 — preserve STL solid names as gmsh physical groups |
| 2b | high | iter01 | DEFERRED → DEC-V61-104 (interior obstacle topology) |
| 3 | critical | iter02 | DEC-V61-103 Phase 1 cacda9f — BC mapper from named patches |
| 4 | high | iter04 | 5ca1e2e — numbered-patch prefix matching |
| 5 | high | iter04 | db438c2 + 40a7ada (Codex R2) — area-weighted per-triangle voting |
| 6 | critical | iter04 | 2c99b80 — patch-normal-aware inlet velocity |
| 7 | high | iter05 | c979a2c + 40a7ada (Codex R2) — canonical role-token classification |
| 8 | critical | iter06 | a6f40f2 + e1559b9 (Codex R4) — polyMesh boundary constraint type rewrite for symmetry |
