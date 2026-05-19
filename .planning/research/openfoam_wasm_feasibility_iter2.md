# OpenFOAM-WASM Feasibility Probe · iter-2 (V68-C.4 spike-class)

**Spike date**: 2026-05-16 (iter-1: 2026-05-16 V68-B.6) · **Author**: Claude Code Opus 4.7 · **Status**: Research only · STILL no compilation attempted · Docker daemon probed but `emscripten/emsdk` image not pulled (would commit ~3 GB to disk without arc-level authorization)

This document supersedes nothing in iter-1 (`openfoam_wasm_feasibility.md`); it **extends** it with:
1. Docker daemon health snapshot
2. Docker-based emsdk path narrowed from "alternative" to "recommended"
3. Updated dependency triage with explicit cost-per-iteration model
4. Concrete go/no-go decision tree for a future V68-D arc

---

## 1 · iter-2 delta · Docker daemon health probe

| Probe | iter-1 (V68-B.6) | iter-2 (V68-C.4) | Notes |
|---|---|---|---|
| `docker --version` | 29.2.1 reported | 29.2.1 reported | unchanged |
| `docker info` exit | not run | exits 0; Server v29.2.1, OSType=linux | daemon HEALTHY |
| `docker images emscripten/emsdk` | not run | empty (not pulled) | ~3 GB pull pending an arc decision |
| Existing containers | 0 catalogued | 3 (`case028v4_sim`, `case028v3_sim`, `buildx_buildkit_cross-build0`) | none related to WASM |
| Existing images | 0 catalogued | 9 | none related to WASM |

**Conclusion**: docker daemon is fully usable on this dev box. The blocker is not infrastructure but the decision to spend ~3 GB disk on an `emscripten/emsdk` image without a charter mandating it.

## 2 · Docker-based emsdk path · upgraded to recommended

iter-1 noted emsdk native install as preferred ("lower per-iteration cost") and Docker as alternative. iter-2 reverses that priority for the cfd-harness-unified context, for three reasons:

1. **Native install pollutes the dev shell** with `~/emsdk/emsdk_env.sh` sourcing requirements; the cfd-harness toolchain already juggles `uv`, `node`, `vite`, `playwright`, `pytest`, `OpenFOAM-native`, and `FreeCAD` — adding emsdk env layering risks cross-contamination (e.g., emsdk's own `python3` shadowing `uv`'s python).
2. **Docker isolation is auditable**: `docker run emscripten/emsdk emcc ...` produces a deterministic compile artifact regardless of dev-box drift. For an advisor product, audit-grade reproducibility matters more than per-compile latency.
3. **CI portability**: any future GitHub Actions WASM build job will use the `emscripten/emsdk` image anyway — keeping local dev on the same image eliminates "works on my machine" cliff.

**iter-2 recommended path**:
```bash
docker pull emscripten/emsdk:3.1.61          # 1× ~3 GB
docker run --rm -v $(pwd):/src -w /src \
  emscripten/emsdk emcc src/hello.cpp -o hello.html  # per-compile invocation
```

## 3 · OpenFOAM dependency triage · iter-2 cost model

iter-1 §3 listed dependencies. iter-2 adds a **per-dependency engineering-week estimate** for porting/working-around:

| Dep | iter-1 status | iter-2 engineering-week estimate | Why |
|---|---|---|---|
| MPI (Open MPI / MPICH) | Blocking · serial-only fallback exists | 4-6 weeks | OpenFOAM's `Pstream` abstraction has serial fallback; biggest cost is verifying the full feature matrix doesn't silently rely on MPI primitives (e.g., parallel I/O codepaths in `polyMesh` constructors) |
| ParMETIS / Scotch | Blocking when running parallel decomposition | 2-3 weeks | Skip for WASM; document "no-decompose" mode. Most edu/demo cases are <100k cells anyway |
| Boost headers (`Boost.Serialization`, `Boost.Filesystem`) | Likely compatible | 1 week | emscripten ships partial Boost; manual feature audit needed for serialization + locale |
| zlib / libgomp | Blocking · libgomp absent in emsdk | 2 weeks | OpenFOAM's `#pragma omp parallel` regions need either OpenMP-on-emscripten (Pthreads) or stub-out for single-thread WASM |
| Filesystem reads (POSIX `open`, `mmap`) | Blocking · sandboxed in WASM | 3-4 weeks | Need MEMFS / IDBFS virtual filesystem + JS-side case-dir-as-zip uploader |
| ParaView / VTK readers | NOT needed for solver-only WASM | 0 weeks | Visualization stays in the existing vite/react vtk.js path; WASM does numerics only |
| GMSH meshing | Optional (could bypass · use pre-meshed cases) | 0-4 weeks | Phase-1 ship with offline-meshed cases; later embed GMSH-WASM (community port exists) |

**iter-2 total**: 12-19 engineering-weeks for a **read-only-cases, serial-only, no-meshing** WASM demo. This is consistent with iter-1's 14-22 week estimate (iter-2 narrowed by 2-3 weeks on the parmetis + paraview triage).

## 4 · iter-2 dependency cliff hunt · new findings

iter-1 missed three dependencies that surface only on deeper read of the OpenFOAM CMake graph:

| Dep | Why it matters | Engineering-week add |
|---|---|---|
| `kahip` (graph partitioner, alt to Scotch/ParMETIS) | OpenFOAM v2406+ optional dep; same skip-on-WASM logic as ParMETIS | 0 (skipped) |
| `cgal` (used by `surfaceCheck`, some sHM stages) | Header-only mostly · should WASM-compile · risk = GMP/MPFR transitive deps that ship as `.so` | 1-2 weeks if GMP/MPFR cause friction; 0 if not used in target solver matrix |
| `fmt` (`spdlog` transitively) | Standard now in OpenFOAM logging | 0 (compatible) |

## 5 · Go/no-go decision tree for a future V68-D arc

A future V68-D arc should answer **yes to all 5 questions** before committing engineering weeks:

1. Is the cfd-harness audience explicit about WASM being a strategic differentiator (vs. "nice-to-have")?
2. Does the canonical use case need ≥ a 100k-cell solve in-browser, or is "demo case ≤ 10k cells" the actual aspiration?
3. Are post-solve viz needs (residuals plot, field render) **separable** from the solver, so the solver-only WASM bundle stays under 30 MB?
4. Is the team committed to ≥ 12 engineering-weeks of focused work (not part-time)?
5. Has the team identified a **single owner** for the WASM build pipeline (CMake → emscripten → distribution)?

If any answer is **no**, defer further. iter-2 evidence is that **no answer is currently yes**:
- (1) the cfd-harness charter doesn't make WASM strategic; the M-AI-COPILOT + V130 advisor-not-driver theses dominate
- (2) demo case scope is undecided
- (3) viz separability is good (existing vtk.js path) but not contractually pinned
- (4) no team committed
- (5) no owner

**iter-2 conclusion**: Defer V68-D to a future arc with explicit charter framing. Continue documenting findings (iter-3 if anything material changes).

## 6 · What changed vs iter-1 in one paragraph

iter-2 didn't compile anything. It verified docker daemon health (HEALTHY), upgraded the Docker emsdk path from alternative to recommended, narrowed the engineering-week estimate from 14-22 weeks to 12-19 weeks via parmetis + paraview triage, surfaced 3 new dependencies (`kahip`, `cgal`, `fmt`) without changing the bottom line, and authored an explicit 5-question go/no-go decision tree for a future V68-D arc to gate against. **No code committed. No image pulled. Spike artifact only.**

— V68-C.4 spike artifact · iter-2 · 2026-05-16
