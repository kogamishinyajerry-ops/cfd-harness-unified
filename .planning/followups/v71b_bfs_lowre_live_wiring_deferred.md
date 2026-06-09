---
followup_id: V71B-FOLLOWUP-1
title: V71.B low-Re BFS — live execute()/TaskRunner gate wiring + advisor live-caller wiring (deferred)
opened: 2026-06-08
opened_by: Codex R0 review of DEC-V61-235 (86gs gpt-5.4 xhigh · 1 P1 + 1 P2 dispositioned as deferred wiring)
priority: medium
status: item-1-LANDED (DEC-V61-236, 2026-06-09) · item-2 still open
parent_dec: V61-235
closing_dec: V61-236 (item 1 — the gate live-wiring slice)
---

# V71B-FOLLOWUP-1 · low-Re BFS live wiring (deferred from the V&V-anchor slice)

> **Item 1 LANDED — DEC-V61-236 (2026-06-09).** The gate live-wiring exists:
> `foam_agent_adapter._execute_backward_facing_step_lowre` (fresh `--rm` OF11,
> persistent `raw_output_path`) + identity-keyed `execute()` dispatch +
> `TaskRunner._verify_bfs_lowre` branch + the `backward_facing_step_lowre`
> `specialized_gate_anchor` whitelist entry, all landed together (the wedge
> precedent). Backend-e2e evidence + tamper manifest:
> `reports/showcase_aero/_v71b_bfs_lowre_backend_e2e/` — `execute()` launched a
> REAL OF11 solve (Xr/H=5.8812, floor y+ max=0.0661<1), the Control gate PASSED
> on the backend output, and the surface VTK is **byte-identical** to the
> DEC-V61-235 hand-typed probe (SHA `fd25bfce…`). Opt-in live test
> `tests/p4/test_bfs_lowre_live.py`; offline dispatch/collision/whitelist-load
> regression `tests/p4/test_bfs_lowre_wiring.py`. **Item 2 (advisor live-caller
> wiring) remains OPEN** — see below.

DEC-V61-235 landed the **V&V-anchor** half of the wall-RESOLVED low-Re kOmegaSST
backward_facing_step: the gate (`src.bfs_lowre_gate`), gold, whitelist
`specialized_gate_anchor`, frozen LIVE probe, offline gate tests, and the
`low_re_komegasst_trigger_advisor` (registered + dispatch-tested + behaviorally
firing on the E21 config). It deliberately does **NOT** wire the live execution
paths — mirroring the wedge arc, where DEC-V61-233 landed the V&V validation and
DEC-V61-234 (a separate slice) wired the workbench backend. Codex R0 on V61-235
correctly flagged the two live-path gaps below; both are deferred here, not hidden.

## Deferred item 1 — gate live wiring (Codex R0 P1) — ✅ LANDED (DEC-V61-236, 2026-06-09)

A `TaskRunner` verification branch + an adapter runner that produces a **persistent**
`raw_output_path` containing `proof/floor_faces.csv` + `VTK/allPatches` (so
`gate_bfs_lowre_against_gold` runs on real solver output, not the frozen fixture).

Required pieces (analogous to the wedge's DEC-V61-234):
- `foam_agent_adapter._execute_backward_facing_step_lowre`: stage the resolved
  case, `blockMesh && checkMesh && foamRun -solver incompressibleFluid &&
  foamToVTK -latestTime -allPatches`, derive `proof/floor_faces.csv` via
  `src.bfs_lowre_extractor.write_floor_faces_csv`, return a persistent work_dir
  (NO `finally: rmtree` of the output) — exactly the wedge persistence pattern.
- An early dispatch in `execute()` keyed on case identity (NOT BC passthrough —
  Notion specs set `boundary_conditions={}`; key on the whitelist
  `case_kind=specialized_gate_anchor` + name `backward_facing_step_lowre`, or a
  dedicated `GeometryType`, so the Notion-driven path is also covered — Codex R0 P2).
- A `TaskRunner` branch (re-add the `_verify_bfs_lowre` equivalent removed from
  V61-235) gated on that same case identity, plus a live opt-in Docker test
  mirroring `tests/p4/test_supersonic_wedge_live.py`.
- The **`knowledge/whitelist.yaml` `specialized_gate_anchor` entry** for
  `backward_facing_step_lowre` (removed from V61-235 per Codex R1 P1, currently a
  deferral comment). It MUST land WITH the dispatch + branch above — a selectable
  whitelist entry without a verification path is exposed-but-unverifiable
  (`load_gold_standard` → None → "No gold standard found"). This is the wedge pattern:
  whitelist + branch both landed in DEC-V61-234, not the V&V slice 233.

This does NOT flip runnable-coverage (still incompressible RANS — turbulence-
treatment breadth, not a new compute type).

## Deferred item 2 — advisor live-caller wiring (Codex R0 P2)

`low_re_komegasst_trigger_advisor` is reachable only via the `low_re_komegasst_inputs`
kwarg of `assemble_stack`; no production caller populates it yet (`/api/ai-review`'s
request model + `/api/ai-diagnose` have no such field). Its **stated** V71.B scope —
closing the V69.2 canonical-eval KNOWN_F_NEW skip — is met (the eval harness checks
advisor-surface registration; the new `test_e21_case_036_documented_config_fires_one_info_finding`
pins the behavioral firing). Live-API surfacing is the remaining work:
- extract `RASModel` from `constant/turbulenceProperties` + a wall-treatment / first-cell-y+
  estimate at the geometry-ingest / `/api/ai-review` call site, build a
  `LowReKOmegaSSTSnapshot`, and pass it to `assemble_stack` so the V104 INFO finding
  appears in live advisor-stack responses.
- (DEC-V61-088: this adds an extraction to a top-level route surface → its own
  surface-scan + review.)

## Done-when

Both live paths exercised end-to-end against a real solve / live request, with
evidence, under a dedicated wiring DEC (the "V71.B-wire" slice).
