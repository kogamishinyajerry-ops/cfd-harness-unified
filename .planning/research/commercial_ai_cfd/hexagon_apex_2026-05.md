# Commercial Audit · Hexagon MSC Apex (+ Cradle CFD) · 2026-05-11

**Audit purpose**: post-V198 preprocessing-first pivot mandates studying commercial preprocessing leaders to inform what our preprocessing engine should cover. First product in monthly audit rhythm (paired with Phase 1.5 P0 unit detector work; case_003 ramp deferred to Phase 4).

**Audit budget**: ≤2 pages. No code import. No technology dependency. Decision categories per feature: not-borrow / borrow-UX / borrow-code.

**Status**: APPROVE (audit completed, findings codified).

---

## 0. Factual correction surfaced during audit

The recommendation to study "Hexagon MSC Apex as preprocessing leader" was **partially mis-targeted**. The actual landscape:

| Product | Domain | Why we initially picked it |
|---|---|---|
| **Hexagon MSC Apex** | **FEA preprocessing** (midsurface, defeature, mesh-for-Nastran) | Conflated "geometry healing" leader claim; Apex is well-known for that |
| **Hexagon MSC Cradle CFD scFLOW** | **CFD preprocessing + meshing + solver** | Actually the CFD-relevant sibling under same Hexagon CAE umbrella |

Both audited below since they share Hexagon's geometry-prep philosophy. Cradle CFD is the proper comparison; Apex's preprocessing patterns still transfer via the "automated cleanup during import" theme.

---

## 1. Feature inventory

### 1.1 MSC Apex (FEA-pre primary, CFD-pre secondary)

| Feature | Mechanism | Source |
|---|---|---|
| **Automated cleanup during CAD import** | Apex runs auto-repair during the import translation step. Marketing claim: 60% reduction in "corrupt files to re-request from design office" | hexagon.com/products/msc-apex-modeler |
| **Defeature engine** | User specifies feature types (chamfers, holes, cylinders) + dimension ranges; engine batch-removes them. One-click via scripting API | frimann-innoswiss.ch Apex Modeler whitepaper |
| **Midsurface extraction** | Automated midsurface generation with thickness mapping. Aimed at sheet-metal FEA; not directly CFD-applicable | hexagon.com Apex Modeler |
| **Direct modeling** | Geometry editable post-mesh; mesh regenerates on geometry change. Reduces re-import cycles | engineering.com Apex midsurface piece |
| **Scripting API (2025.2)** | Operations like transform/boundary-connection, repeatable processes for assemblies, broader-framework integration | hexagon.com Apex 2025.2 release notes |
| **STEP / IGES / Parasolid / ACIS / STL multi-format I/O** | No-extra-license format coverage | hexagon.com Apex Modeler |

### 1.2 MSC Cradle CFD scFLOW (CFD-native)

| Feature | Mechanism | Source |
|---|---|---|
| **CAD edit functions in Preprocessor** | Close gaps between solid surfaces, delete unnecessary parts, **solidify parts faultily recognized as sheets**. Apply thickness to specific surfaces; modify geometry via plane equation | cradle-cfd.com/product/scflow/function.html |
| **Voxel Fitting Mesher** | Auto voxel-based mesh adapted to complex geometry; vendor positions as flagship preprocessing capability | hexagon.com cradle-cfd-scflow |
| **Polyhedral mesh from unstructured** | Auto polyhedral mesh element generation | engineeringsupport.org cradle-cfd-scflow |
| **Adaptive mesh refinement (AMR)** | Series of calculations to adapt/rebuild mesh while tracking flow nature; vendor claims acceptable cell count without manual iteration | engineeringsupport.org |
| **Multi-CAD-format ingest** | Parasolid XT, STEP, CATIA, NX, Creo, SolidWorks, Inventor, Solid Edge — direct ingest, mesh from original geometry | cradle-cfd.com |

### 1.3 Industry-wide preprocessing patterns (Spatial 3D InterOp whitepaper)

| Pattern | Mechanism | Numbers cited |
|---|---|---|
| **Healing-during-translation** | CAD interop layer performs healing + topology mod + geometry refinement + invalid data repair *during* format translation (not as separate step) | "80% acceleration in preprocessing workflows" claim |
| **CGM Defeaturing** | Automated fillet/hole/chamfer removal by size threshold | (same source) |
| **CSM/CVM coupled meshing** | Mesher accesses geometry kernel via internal API; no intermediate files; mesh nodes sit on exact surface representation | (same source) |
| **Curvature-based + proximity-based + gradation element sizing** | Replaces manual sizing field decisions | (same source) |
| **Auto boundary layer generation** | Replaces manual prism layer config | (same source) |

**Industry baseline claim**: engineers spend ~38% of analysis time on preprocessing. Teams average 3.6 CAD tools × 3.3 solvers → compounded compatibility issues at each handoff.

---

## 2. Substrate gap relevance (V198 §S3 + P0-P9 mapping)

| Commercial feature | Our V198 工件 / P-list mapping | Already shipped? | Gap real? |
|---|---|---|---|
| Auto cleanup during import (Apex/Cradle) | A1 cad_ingest_freecad + P2 watertight/manifold | ✅ A1 just landed (`3227207`); P2 partial in stl_loader | **Partial** — A1 preserves names but doesn't auto-heal yet |
| **No commercial unit detection mentioned** | **P0 unit_detector** | ✅ P0 just landed (`c458d3d`) | **Filled** — commercial leaders evidently leave unit handling to user. Our P0 is a differentiator (small one) |
| Defeature by size threshold (chamfer/hole/cylinder) | A3 geometry_surgery (decimation + axial stretch) | ✅ A3 landed | **Different angle** — A3 decimates triangulation density; commercial defeatures CAD features. Both are valid; complementary not duplicate |
| Voxel Fitting Mesher (Cradle) | N2 sizing field + sHM cell budget | ⚠️ partial (sizing field only, no auto budget feedback) | **Gap** — P7 mesh size budget feedback loop |
| AMR (Cradle adaptive rebuild) | (not in our P-list) | ❌ not shipped | **Gap real, but**: V130 advisor philosophy — we shouldn't auto-rebuild mesh; advisor recommends + engineer accepts. AMR's "automatic algorithm" is exactly the auto-actor pattern we descope'd |
| Multi-CAD-format ingest (Cradle: Parasolid/CATIA/NX/Creo/SW/Solid Edge/Inventor) | P8 STEP source-aware loader | ⚠️ A1 covers CATIA-like STEP only | **Gap real** — P8 is real expansion direction once 2nd-3rd industrial case uses non-CATIA source |
| Healing-during-translation (Spatial) | bundled CAD interop layer | ❌ not in scope (we don't write a CAD kernel) | **Not borrow** — out of project scope. We ride on FreeCAD/Open CASCADE upstream healing |
| Curvature/proximity/gradation auto-sizing | N2 advanced sizing field | ⚠️ N2.1 sizing schema exists; auto-derivation partial | **Gap** — N2 advisor could grow these heuristics |
| Auto boundary layer (Cradle) | N2.3 prism layer | ✅ N2.3 landed | **Different mode** — N2.3 = engineer specifies parameters + advisor warns; commercial = fully auto. Our descope is intentional |

---

## 3. Borrow decisions (per-feature)

| Commercial feature | Decision | Rationale |
|---|---|---|
| **Auto cleanup during import** | **Borrow UX** (not code) | A1 should grow a *companion* `cad_health_check` step that runs at ingest time: count vertex/edge defects, gap topology, non-manifold faces. Report to engineer, do NOT auto-fix. Mirrors A1's read-only contract |
| **Defeature by feature class + size threshold** | **Borrow UX** (not code, defer code) | A3 covers triangulation-level decimation. Commercial covers CAD-feature-level defeaturing (chamfers/holes). To do CAD-feature defeaturing we'd need OpenCASCADE / FreeCAD's BRep edit primitives — non-trivial. Defer until 2-3 industrial cases prove this is a real bottleneck (current cases handled it via A3 decimation) |
| **Voxel Fitting Mesher** | **Not borrow** | We commit to OpenFOAM sHM ecosystem (per V198 substrate). Voxel mesh is a different paradigm; switching would break entire case pipeline. Cradle is a sibling solver with sibling mesher — not directly transplantable |
| **AMR (Cradle adaptive rebuild)** | **Not borrow** | V130 advisor philosophy: AI cannot mutate case. AMR is auto-actor — exactly the pattern we descope'd 2026-05-06. Borrow would re-litigate V130 |
| **Multi-CAD-format ingest** | **Borrow code** (eventually, per case demand) | P8 in our preprocessing P-list. Wait for 2nd-3rd industrial case to surface non-CATIA source as actual blocker, then add format-specific paths. Don't pre-build |
| **Healing-during-translation** | **Not borrow** | Out of scope (no CAD kernel). We piggyback on FreeCAD/Open CASCADE's built-in healing |
| **Curvature/proximity auto-sizing** | **Borrow UX** | N2 advisor can grow heuristics that *suggest* curvature/proximity-driven sizing values to the engineer; engineer accepts/edits. Already partially present in N2.1; expand on next case-driven gap |
| **Auto boundary layer (full auto)** | **Not borrow** | N2.3 prism-layer engineer-driven model is intentional. Cradle's full-auto is the descope'd actor pattern |
| **Unit detection** | **n/a — commercial leaders skip this** | Our P0 fills a niche not addressed by either Apex or Cradle. Confirms substrate-driven gap finding |

**Summary**: 2 borrow-UX (ingest health check, curvature/proximity auto-sizing); 1 conditional borrow-code (multi-format ingest, on demand); 4 not-borrow (voxel mesher, AMR, healing-translation, full-auto BL); 1 confirmation we're ahead (unit detection); 1 defer (CAD-feature defeaturing).

---

## 4. Falsifications + risk notes

- **Apex ≠ CFD preprocessing leader.** Cradle CFD scFLOW is the CFD-native sibling. Future product picks for audit should differentiate FEA-pre vs CFD-pre.
- **38% preprocessing time + 3.6 CAD tools × 3.3 solvers** stats are vendor-friendly — Spatial sells CAD interop. Treat magnitude as directional, not exact.
- **"Years of validation against edge cases"** Spatial quote is a real risk for us: every preprocessing feature we copy has decades of edge-case hardening behind it commercially. Our path is to absorb edge cases via V-series substrate, not match commercial breadth.
- **Cradle's "automatic algorithm" rhetoric is the AI-actor pattern V130 descope'd.** Commercial CFD products will continue to push fully-auto patterns. Our differentiator is "advisor + engineer confirmation", which the commercial sphere does NOT compete on.

---

## 5. What this audit changes in next sprint

- **No charter changes**: P0 + P8 + N2 advisor growth align with both substrate-listening and what commercial leaders do well.
- **One new spike candidate**: `cad_health_check` companion to A1 (ingest-time defect report). ~30-50 LOC + 1 test. Schedule after case_003 ramps and exposes whether A1 alone is sufficient.
- **One deferral confirmed**: CAD-feature-level defeaturing (chamfers/holes/cylinders) stays out of P-list until ≥2 industrial cases demand it.
- **One competitive-differentiator confirmed**: V130 advisor philosophy is a real product position — every commercial CFD product audited so far defaults to auto-actor. Document this in next user-facing materials.

---

## 6. Next audit candidate (Month 2)

Based on this audit's findings:

- **If preprocessing-first sprint exposes mesh-side gaps** → **Cadence Fidelity Pointwise** (mesh-engine commercial leader, public docs richer than competitors)
- **If multi-CAD-format ingest becomes blocker** → **Spatial 3D InterOp** (CAD interop kernel, vendor of the bottleneck article that validated our diagnosis)
- **If engineer-vs-auto-actor positioning needs sharpening** → **SimScale AI Assist** (free tier, can compare advisor UX side-by-side with our N6 panel)

User picks at month 2 sprint open.

---

## Sources

- [MSC Apex Modeler product page (Hexagon)](https://hexagon.com/products/msc-apex-modeler)
- [MSC Apex Modeler whitepaper PDF (Frimann-Innoswiss reseller)](http://www.frimann-innoswiss.ch/uploads/5/0/4/7/50472161/sb_msc-apex_modeler_ltr_w.pdf)
- [Cradle CFD scFLOW (Hexagon)](https://hexagon.com/products/cradle-cfd-scflow)
- [Cradle CFD scFLOW function reference (cradle-cfd.com)](https://www.cradle-cfd.com/product/scflow/function.html)
- [Cradle CFD scFLOW preprocessor overview (engineeringsupport.org)](https://engineeringsupport.org/cradle-cdf/cradle-cfd-scflow/)
- [Spatial Corp · FEM preprocessing is the bottleneck (blog)](https://blog.spatial.com/fem-preprocessing-is-the-bottleneck)
- [Hexagon MSC Apex 2025.2 release notes (third-party mirror)](https://tutbb.com/threads/hexagon-msc-apex-2025-2-win-x64-english.180063/)
- [MSC Apex midsurface piece (engineering.com)](https://www.engineering.com/msc-apex-does-more-than-improve-midsurface-extraction/)
