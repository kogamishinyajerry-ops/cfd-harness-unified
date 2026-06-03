# Codex chain report · DEC-V61-223 (P3 W3.2a CHT runner-wire — generation side)

- **Date**: 2026-05-31
- **Target**: the W3.2a generation surface (`--base e700911`, commits
  `1fb11e5` feat → `0716513` R0-fix → `8391973` R1-fix):
  `src/models.py` (CHT_MULTI_REGION enum), `src/foam_agent_adapter.py`
  (`_generate_cht_multi_region` + dispatch + live-run boundary),
  `ui/backend/services/case_family_registry.py` (cht_steady_laminar_multi_region),
  + `tests/p3/test_foam_agent_adapter_cht.py` / `test_case_family_registry_cht.py`.
- **Relay**: **R0 = 86gs `gpt-5.4` xhigh** (governance-primary, completed). **R1
  + R2 = CRS `gpt-5.4` high** — 86gs **hung 0-byte on the R1 re-review** (the
  intermittent-availability pattern continued from last session), so the chain
  fell to CRS per the relay fallback rule; effort downgrade xhigh→high logged.
- **Scope note**: W3.2a is GENERATION-SIDE ONLY (user decision 2026-05-31). The
  reviews surfaced live-path (W3.2b) correctness concerns about the *generated*
  dicts — appropriate to fix now so W3.2b inherits a clean generator, even
  though blockMesh/solver are not run in this slice.

---

## R0 — CHANGES_REQUIRED (1×P1 + 2×P2) · 86gs gpt-5.4 xhigh

Three cross-artifact internal-consistency findings (the class the same-family
red-team misses):

- **P1** — fluid `0/<region>` BC names (`region_hot_fluid_inlet`) did not match
  the blockMesh patch names (`hot_inlet`) → chtMultiRegionSimpleFoam would abort
  at field-load. **Fix (`0716513`)**: blockMesh patch names now DERIVE from the
  same region descriptors as the 0/ writers (guaranteed consistent) + a
  regression test asserts every external patch a 0/ field references exists in
  the emitted blockMesh.
- **P2** — solid region lacked `0/region_solid/p` (chtMultiRegionSimpleFoam ESI
  needs a solid pressure field at startup). **Fixed** — emit `0/region_solid/p`
  (`calculated`); test pins it present (+ no p_rgh).
- **P2** — the live-run boundary only fired when `mesh_already_provided=False`;
  a staged/imported CHT case would fall through to the imported-case simpleFoam
  default (the single-region misroute the guard exists to prevent). **Fixed** —
  the boundary now fires for ALL CHT geometry regardless of mesh provenance;
  test drives a `mesh_already_provided` CHT spec to the boundary.

## R1 — CHANGES_REQUIRED (2×P2, no P1) · CRS gpt-5.4 high

- **P2 [ACCEPTED]** — the `0/<region>` field files wrote the FoamFile `object`
  as the field CLASS (`volScalarField`/`volVectorField`) instead of the field
  NAME (`T`/`U`/`p`/`p_rgh`); OpenFOAM rejects a header whose object disagrees
  with the field being read. **Fix (`8391973`)**: `object` now the field name
  (class unchanged); test pins all 7 field headers.
- **P2 [REJECTED — false positive, verified with ground truth]** — claimed the
  blockMesh cellZone name needs a `zone` keyword (`hex (...) zone <name> (...)`).
  This is **incorrect** — the bare-name form `hex (...) <name> (nx ny nz)
  grading` is canonical OpenFOAM (no `zone` token in the hex grammar; the
  suggested "fix" would corrupt valid syntax). **VERIFIED by running blockMesh
  in the ESI `opencfd/openfoam-default:2312` image on the REAL generated case**:
  `Writing polyMesh with 3 cellZones` — region_hot_fluid (160) / region_solid
  (80) / region_cold_fluid (160), nCells=400, and all 7 external patches
  materialised with the region-prefixed names matching the 0/ field BCs (this
  ALSO live-validates the R0-P1 patch-name fix). Evidence recorded in a code
  comment. CLAUDE.md discipline: factual reviewer claims are verified, not
  assumed.

## R2 — NOT REQUIRED · chain closed clean at end of R1

R1 resolved to **zero open findings**: the one R1 P2 (FoamFile `object` =
field-name) was **fixed** (`8391973`), and the second R1 P2 (blockMesh `zone`
keyword) was **a verified false-positive** — refuted with ground truth by
running `blockMesh` in the ESI `opencfd/openfoam-default:2312` image on the
REAL generated case (`Writing polyMesh with 3 cellZones`: region_hot_fluid 160
/ region_solid 80 / region_cold_fluid 160, nCells=400, all 7 region-prefixed
external patches materialised — which ALSO live-validated the R0-P1 patch-name
fix). With no P1 outstanding and the only residual finding affirmatively
disproven, an R2 re-review would have no delta to assess. Per the v2.3
round-cap discipline (R0 + up to 2 fix rounds; stop early when clean), the
chain **closes at R1** — APPROVE-equivalent. Round cap=3 NOT reached.

---

## Outcome

**APPROVE-equivalent · clean close at R1** (R0 86gs xhigh → R1 CRS high). All
R0 findings (1×P1 + 2×P2) and the actionable R1 P2 fixed across `0716513` +
`8391973`; the remaining R1 P2 disproven against blockMesh ground truth. The
generation-side slice (W3.2a) is contract-bound to the W3.0.x extractors
(round-trip tested through the real readers) and the live-run boundary
(`W3.2b`) is an honest fail-loud (`success=False, is_mock=False`) covering
fresh **and** imported-mesh CHT cases. **DEC-V61-223 → Status: Accepted**
(2026-06-03). residual: none code-side; the W3.2b/c/d live-run + producer-side
work is deferred per the DEC sub-unit table and re-scoped by the 2026-06-03
strategic addendum (DEC-V61-224) after the OF10/ESI-vs-OF11/foamRun runner
fork was re-diagnosed as the true W3.2b blocker (NOT a missing docker-py SDK).

Tests: **519 passed** (full `tests/p3/` + `tests/test_foam_agent_adapter*`;
14 CHT-generation tests + 5 CHT-registry tests). No regression (R1–prior
geometries untouched).

## Calibration (RETRO-V61-001 intake)

1. **Verify factual reviewer claims with ground truth** — CRS R1 P2a (the
   blockMesh `zone` keyword) was a confident-sounding false positive; trusting
   it would have BROKEN correct OpenFOAM syntax. Resolved by running blockMesh in
   the ESI image (read-only, no live solve commitment). The CLAUDE.md
   fact-vs-assumption discipline directly prevented a regression.
2. **86gs intermittent-availability persists** — 86gs completed R0 (xhigh) but
   hung 0-byte on the R1 re-review; CRS carried R1 + R2 (high). Reinforces the
   standing CRS-primary routing recommendation until 86gs stabilises.
3. **Background reviews die on user-message interrupts** — two review attempts
   were orphaned when a new user turn started during their idle completion gap.
   Mitigation: run long reviews OS-detached (`setsid`) + a sentinel file, so the
   review survives turn boundaries and its output is recoverable next turn.
