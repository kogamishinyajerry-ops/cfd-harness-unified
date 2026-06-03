# Codex review report · DEC-V61-225 (P3 W3.2b · adapter→OF11 reconciliation)

**Relay**: CRS gpt-5.4 (high) primary — `codex review --base 740f78a` (86gs xhigh
on standby; 86gs `codex review` hung >1h delegating to the desktop app-server, so
CRS was used per the project's W3.x 86gs-instability standing recommendation).
**Round cap**: 3 (R0 + 2 fix iterations). **Outcome**: CLOSED at cap; R2 P1
adjudicated false-premise + user-ratified 2026-06-03.

## Findings & disposition

| Round | Finding | Sev | Disposition |
|---|---|---|---|
| R0 (CRS) | `_read_cht_regions` bare-substring search mis-anchors on commented `fluid(...)`/`solid(...)` | P1 | FIXED `8bdea61` (strip comments + anchor on `regions( ... )` block); regression test `test_read_cht_regions_ignores_comment_substrings` |
| R0 (CRS) | bashrc OF10→OF11 makes buoyantFoam fail cryptically | P1 | FIXED `8bdea61` (honest structured BLOCK naming deferred follow-up); test `test_buoyant_geometry_honest_block_under_of11` |
| R0 (86gs, late) | dup buoyantFoam P1 | P1 | = above |
| R0 (86gs, late) | `_execute_cht_multi_region` ignores `mesh_already_provided` (would blockMesh over an imported mesh) | P2 | FIXED `462128f` (skip blockMesh; M6.1 parity; mesh-presence honest BLOCK); tests added |
| R1 review (CRS) | 3-call CHT pipeline relies on container-side meshes surviving the put_archive re-upload (implicit tar-merge dependency) | P1 | FIXED `6617098` (single `_docker_exec`, steps chained under `set -e` — one upload, no intervening re-upload); live-reverified 9.17s |
| R2 review (CRS) | buoyantFoam guard is "a regression — those geometries previously executed" | P1 | **ADJUDICATED FALSE-PREMISE + user-ratified** (round cap reached) — see below |

## R2 P1 adjudication (false premise · evidence)

Codex's premise: "NATURAL_CONVECTION_CAVITY / IMPINGING_JET previously executed
through buoyantFoam, so blocking them is a regression."

**Disproven from the repo:**
1. Pre-W3.2b (`git show 740f78a:src/foam_agent_adapter.py`) the adapter sourced
   `source /opt/openfoam10/etc/bashrc`.
2. The cfd-openfoam container (the OF11 image the adapter targets) has **no**
   `/opt/openfoam10/etc/bashrc` — `docker exec` → `No such file or directory`.
   ∴ **every** adapter solve failed pre-W3.2b; buoyantFoam never ran in this env
   (matches DEC-V61-224: the whole adapter exec path was dead).
3. `buoyantFoam` is **NOT FOUND** in the OF11 image (ESI solver name; Foundation
   OF11 doesn't ship it) — it cannot run regardless of bashrc.
4. The guard converts a guaranteed cryptic failure into an honest structured BLOCK
   that names the deferred follow-up — TESTED as the intended behavior. Reverting
   would reintroduce the exact silent-failure Codex's own R0 (P1-B) flagged.

Codex reviews the diff in isolation (no DEC-V61-224 history) → a reasonable but
factually wrong "previously executed" inference. **Disposition: do not revert.**
buoyantFoam→OF11 reconciliation = logged deferred follow-up.

## Verification at close

- 334 p3 + 200 adapter unit tests green.
- LIVE OF11 CHT gate (`CFD_LIVE_OF11=1`): PASS 9.17s (real foamMultiRun,
  per-region residuals, reached End).
- RANS proven live (backward-step, AS-IS via `foamRun -solver incompressibleFluid`).
