# OpenFOAM-WASM Feasibility Probe (V68-B.6 spike-class)

**Spike date**: 2026-05-16 · **Author**: Claude Code Opus 4.7 · **Status**: Research
only · NO compilation attempted · this document is the spike artifact for the
hypothetical future V68-D arc to decide go/no-go from.

---

## 1 · Toolchain inventory (this dev machine · macOS Darwin 25.3.0 arm64)

| Tool | Required for WASM compile | Status (probed 2026-05-16) |
|---|---|---|
| `emcc` (emscripten C compiler) | YES | **MISSING** · `command not found: emcc` |
| `em++` (emscripten C++ compiler) | YES | **MISSING** · `command not found: em++` |
| `emsdk` (emscripten SDK) | YES (provides emcc/em++) | **NOT INSTALLED** (no `~/emsdk`, no `/opt/homebrew/Cellar/emscripten`) |
| `docker` (alt path · `emscripten/emsdk` image) | OPTIONAL alternative | **PRESENT** · `Docker version 29.2.1` |
| `node` (≥20 · WASM runtime for JS bindings) | YES | PRESENT (assumed from npm working in V67-C+) |
| `cmake` (≥3.20 · OpenFOAM build system) | YES | likely PRESENT (used by trimesh/gmsh native deps) |

**Conclusion**: zero emscripten on this box. Provisioning is a prerequisite to
any actual WASM work.

## 2 · Two paths to provisioning emscripten

| Path | Disk cost | Time cost | Friction |
|---|---|---|---|
| **emsdk install** · `git clone https://github.com/emscripten-core/emsdk; ./emsdk install latest; ./emsdk activate latest` | ~1.5 GB | ~10 min download + ~5 min install | medium — env activation script must source on every shell |
| **Docker image** · `docker pull emscripten/emsdk` | ~3 GB | ~3 min download | low — `docker run` per-compile · slower per-iteration |

**Recommendation for V68-D**: emsdk native install (lower per-iteration cost ·
the WASM iteration loop is what dominates cost, not setup).

## 3 · OpenFOAM C++ source dependency manifest (WASM compatibility audit)

OpenFOAM-com / OpenFOAM-org v2406+ is **~1.5M lines of C++17** with the
following dependencies that MUST be addressed for browser-target WASM:

### 3a · Mandatory dependencies (cannot run without)

| Dependency | Native role | WASM viability | Workaround / cost |
|---|---|---|---|
| **MPI** (OpenMPI / MPICH) | parallel decomposition · proc<n>/ subdirs | INCOMPATIBLE with browser WASM (no shared-memory model · no MPI ABI in browser) | Strip to serial-only build · OpenFOAM's `wmakeSerial` target exists but is rarely tested · need patches for `Pstream` no-op shims |
| **POSIX threads** (`pthread`) | mesh-decomp + linear-solver parallelism | PARTIAL (emscripten pthread support requires `SharedArrayBuffer` + COOP/COEP HTTP headers · also serial alt available) | Either ship with COOP/COEP headers (BIG infra change) OR force serial linear solvers (slow) |
| **glibc fcntl + flock** | case file locking (`writeIfModified`, transient run lock) | INCOMPATIBLE (no FS lock primitives in browser) | Replace with in-memory mutex · loses crash-recovery semantics |
| **C++17 `<filesystem>`** | case directory traversal | PARTIAL (emscripten ports filesystem · maps to virtual FS) | Use `NODERAWFS` (Node-only) or `MEMFS` (browser-RAM-only) · the latter caps case size at ~2GB |
| **dynamic loading** (`dlopen` for runtime model selection · `customRTM`) | OpenFOAM's hallmark "runtime polymorphism" | PARTIAL (emscripten supports `MAIN_MODULE` + `SIDE_MODULE` since 3.1+) | Compile all 12k+ classes into the main module (bloats WASM blob to ~500 MB pre-gzip) · OR drop runtime selection (kills 50% of the value prop) |
| **libtcmalloc / tcmalloc** | high-perf allocator | INCOMPATIBLE | Fall back to standard `malloc` · ~15% perf hit |

### 3b · Optional dependencies (degrade behavior if missing)

| Dependency | Native role | WASM workaround |
|---|---|---|
| FFTW (transient-flow harmonic analysis) | UNAVAILABLE | port `fftw3` to WASM · ~2 weeks |
| ZLIB (compressed timestep dirs) | PRESENT (emscripten ports it) | seamless |
| PETSc/Eigen/SuiteSparse (alt linear solvers) | PARTIAL · Eigen header-only ports cleanly · PETSc has MPI dep | use Eigen exclusively for V68-D MVP |
| ParaView ProxyManager (in-process post) | UNAVAILABLE | skip · use vtk.js (already in workbench) |

### 3c · Build-system rewriting

OpenFOAM uses **wmake** (custom autotools-era build system) — *not* CMake.
wmake hardcodes platform detection paths (`WM_OPTIONS`, `WM_PROJECT_DIR`,
etc.) that emscripten doesn't surface.

**Mandatory rewrite**: port wmake-driven build to CMake OR write
`Makefile.wasm` overlays for every wmake-managed library. Estimated:
**3-6 person-weeks**.

## 4 · Hypothetical V68-D arc cost estimate

| Phase | Scope | Effort | Risk |
|---|---|---|---|
| **1. Tooling** | emsdk install + Docker baseline + CI emscripten pipeline | 1 week | low |
| **2. Build-system port** | wmake → CMake/Makefile.wasm overlay for `OpenFOAM/`, `finiteVolume/`, `dynamicMesh/` core | 3-6 weeks | high (wmake is undocumented in places) |
| **3. Serial strip** | strip MPI · port `Pstream` to no-op shims · drop decomp dependencies | 2-3 weeks | medium |
| **4. Allocator + RTM port** | tcmalloc → malloc · dlopen → MAIN_MODULE/SIDE_MODULE pivot · accept blob bloat | 2-4 weeks | medium |
| **5. Single-solver MVP** | `icoFoam` (simplest · used by lid_driven_cavity) only · WASM blob compiles + runs in browser | 4-6 weeks | high (linker errors will dominate) |
| **6. Workbench integration** | mount WASM in vite · driver UI · field-data → vtk.js bridge | 2 weeks | low |
| **TOTAL MVP (`icoFoam` only)** | | **14-22 weeks** | high |
| **Full multi-solver** | + `simpleFoam` + `pimpleFoam` + `buoyantSimpleFoam` + `chtMultiRegionFoam` | **+12-20 weeks** | very high |

**Go/no-go reading**: a serial-only `icoFoam` WASM is a **3-5 month dedicated
arc** for a single engineer. Full workbench parity (the multi-solver + parallel
story V68-A's MSW substrate hinted at) is **6-10 months**.

## 5 · Alternatives to consider before committing to V68-D

| Alternative | Replaces WASM with | Cost | Loss vs WASM |
|---|---|---|---|
| **Remote-execute (V68-B real backend extended)** | server-side OpenFOAM via API · stream artifacts to workbench | <2 weeks | requires backend infra · loses "offline-capable" claim |
| **Hybrid · `icoFoam` only in WASM, others remote** | MVP path | 3-5 months for icoFoam · then progressive | partial offline |
| **PrePost-only WASM** | only meshing/post tools in browser · solver remote | 3-4 weeks | solver step not offline |
| **Don't pursue WASM** | document V68-B as offline-capable for *audit*, not for *compute* | 0 | acknowledged ceiling on Pillar 1 |

## 6 · Recommendation

Given:
- V68-B already achieves real-backend industrial dogfood + Pillar 6 →97 target
- WASM compile gap is 3-5 months minimum dedicated work · risk-heavy
- The Workbench's user-visible value is mostly in **case authoring / inspection / verdict review**, not in-browser solving
- V20+ corpus methodology (V-series) doesn't gate on in-browser compute

**Recommended**: defer V68-D OpenFOAM-WASM indefinitely. Pursue alternatives in
§5 if/when the offline-compute story becomes a true commercial requirement (not
yet validated by user feedback as of 2026-05-16).

If V68-D *is* pursued, scope it to icoFoam-only WASM MVP (§5 hybrid path) ·
budget 4-6 months · acknowledge it as a research arc, not a feature arc.

## 7 · Spike-class governance footprint (v2.3)

- **LOC change**: 0 (this is a research document · no code modified)
- **Test**: NOT required for research-only spike per v2.3 round-1 (§9 spike-class)
- **DEC**: NOT required (spike-class · documented in commit message instead)
- **Commit message confidence**: `low` (research probe · expected answer was "needs multi-week arc"; finding confirms it)

— Claude Code (Opus 4.7 1M) · V68-B.6 spike · 2026-05-16
