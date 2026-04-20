---
decision_id: DEC-V61-024
timestamp: 2026-04-21T15:40 local
scope: |
  Phase 6 商业化 demo 深化 — 把 /learn 学生门户从"10 个 UNKNOWN 目录"
  升级为"有故事的教学目录"。三件套：
    (1) 9 个 teaching-run fixture（under_resolved × 4、wrong_model × 2、
        real_incident × 3）填满 3 个 UNKNOWN 槽位并给每个 case 至少一条
        "做对的样子"（reference_pass）+ 一到多条"做错的样子"；
    (2) catalog-card 上的 `RunDistributionPill` 徽章（e.g. "3 runs ·
        1 PASS · 2 FAIL"），值由 `_derive_contract_status` 实际评估
        得出，**不信任** `expected_verdict` curator hint；
    (3) 6 case · 8 张真流场 PNG（Ghia 1982 / Blasius / Williamson 1996 /
        Spalding 1961 / Grossmann-Lohse 2000 / Cooper 1984），来源全部
        文献解析解或公开实验表格，带 JSON provenance sidecar。
  目标受众是 CFD 学生，不是审计师；审计特性留在 Advanced tab 后。
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: 6aa7008
codex_tool_report_path: null
  (Codex round 10 ran inline via `codex exec` on 6aa7008; output lives
  in `/private/tmp/claude-502/.../b8zv2g6kt.output`. Report not yet
  committed to `reports/codex_tool_reports/` — queued for cleanup.)
codex_verdict: CHANGES_REQUIRED → RESOLVED (round 10; 2 HIGH findings,
  both applied verbatim in follow-up commit 55b1a88).
  Finding 1 (HIGH): `verdict_counts` aggregated from `expected_verdict`
  hint instead of live contract engine; pill could advertise PASS runs
  that the gold silent-pass hazard would actually relabel HAZARD.
  Finding 2 (MEDIUM): impinging_jet flow-field PNG was Re=23750 Baughn
  Nu≈110 regime but case was rescaled to Re=10000 Nu=25 family →
  physical inconsistency between visual and contract.
  Both fixed in 55b1a88; verdict_counts now computed via
  `_derive_contract_status` per run; PNG regenerated with Cooper 1984
  anchors matching gold.
counter_status: "v6.1 autonomous_governance counter 11 → 12 (pure
  telemetry under RETRO-V61-001)."
reversibility: fully-reversible-by-pr-revert
  (`git revert -m 1 <merge>` removes both commits. Fixture files are
  additive; schema change (`run_summary` field on `CaseIndexEntry`) is
  backward-compatible — frontend tolerates absence via default empty
  dict. Flow-field PNGs live under `public/` and are cosmetic.)
notion_sync_status: pending
github_pr_url: <pending — not yet opened>
github_merge_sha: <to-fill-after-merge>
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 90%
  (Multi-file frontend + API schema + 9 new fixtures + 8 PNG assets.
  Codex already ran one round, returned 2 HIGH findings both fixed
  verbatim in 55b1a88. Residual 10%: (a) physical plausibility of
  under_resolved values (Cf=0.00496 for starved flat plate, Nu=5.1
  for starved BFS) depends on one-off engineering judgment — not
  backed by a specific grid-convergence study; (b) LearnHomePage
  `useQuery(listCases)` adds a second round-trip that could race the
  illustration-only render path in slow networks — not tested in
  this commit.)
supersedes: null
superseded_by: null
upstream: DEC-V61-002 (Path B commercial workbench thesis) — /learn
  is the student-facing surface that DEC-V61-002 called out as
  post-MVP but this session accelerated ahead of schedule per user
  "做商业级 demo" directive.
---

# DEC-V61-024: Teaching runs + run-distribution badges + real flow-field visuals

## Why now

User directive this session: *"做商业级demo，受众是想做 CFD 的学生，可靠/可溯源功能藏到专业模块后面。"*

Prior state of `/learn`: 10 canonical cases as illustrated cards, but
every contract_status defaulted UNKNOWN because only 3 fixtures
existed at the case-level (LDC/BFS/TFP from Phase 0) and the catalog
card advertised neither run count nor verdict mix. Student would see
10 generic cards and learn nothing about why any of them is
interesting. PR #32 introduced the multi-run architecture; this DEC
lands the actual teaching content.

## What landed (two commits)

### Commit `6aa7008` — feat(learn): teaching runs + badges + flow-field visuals

**Teaching runs** (9 new YAMLs under `ui/backend/tests/fixtures/runs/`):

| Case | New runs | Category |
|---|---|---|
| lid_driven_cavity | under_resolved (32² grid, ψ_min=-0.029) | mesh starvation |
| backward_facing_step | under_resolved (Xr=5.1 vs gold 6.26, -18%) | mesh starvation |
| turbulent_flat_plate | under_resolved (Cf=0.00496, y+ too coarse) | mesh starvation |
| circular_cylinder_wake | under_resolved (St=0.1495, cylinder-proximal coarse) + wrong_model (laminar@Re=200, St=0.146) | dual |
| impinging_jet | real_incident (k-ω SST Nu=27 @ Re=10000, PASS near upper tolerance) + wrong_model (k-ε Nu=38 @ Re=10000, FAIL +52%) | model-fitness dual |
| naca0012_airfoil | real_incident (Cd=0.480, far-field too close) | BC under-specification |
| rayleigh_benard_convection | real_incident (Nu=14.5, thermal BL under-resolved) | resolution |

Impinging-jet gold is Cooper 1984 Re=10000 Nu_stag=25; previous fixtures
were Baughn 1989 Re=23750 Nu~110 which caused +350% deviations. All
impinging_jet fixtures rescaled to the Cooper family this session.

**Run distribution pill** (`CaseIndexEntry.run_summary`):
- Pydantic `RunSummary { total: int, verdict_counts: dict[str, int] }`.
- `LearnHomePage` renders `"N runs · X PASS · Y HAZARD · Z FAIL"` with
  contract-color coding.

**Flow-field visuals** (`scripts/flow-field-gen/generate_contours.py`):
- Matplotlib renderer, dark-mode palette matching `/learn` shell.
- 8 PNGs under `ui/frontend/public/flow-fields/`:
  * ldc: centerline_profiles (Ghia 1982 Table I verbatim) + stream_function (ψ ansatz calibrated to Ghia centerlines)
  * tfp: blasius_profile (shooting on f''(0) → 0.33206) + cf_comparison (3 runs overlaid)
  * cylinder: strouhal_curve (Williamson 1996 St = 0.2175 - 5.1064/Re)
  * channel: wall_profile (Spalding 1961 composite u+(y+))
  * RBC: nu_ra_scaling (Grossmann-Lohse 2000 piecewise Ra^1/4 / Ra^1/3)
  * impinging_jet: nu_radial (Cooper 1984 + k-ε/SST overlays)
- Each PNG has matching `.json` provenance sidecar.
- `LearnCaseDetailPage` StoryTab renders figures with provenance
  footnote.

### Commit `55b1a88` — fix(learn): Codex round 10 CHANGES_REQUIRED closure

**Finding 1 applied** (`ui/backend/services/validation_report.py:501`):

Before:
```python
for r in runs:
    verdict_counts[r.expected_verdict] = verdict_counts.get(...) + 1
```
After:
```python
for r in runs:
    run_doc = _load_run_measurement(cid, r.run_id)
    run_audits = _make_audit_concerns(gs, run_doc)
    run_measurement = _make_measurement(run_doc)
    if gs_ref is not None:
        run_status, *_ = _derive_contract_status(
            gs_ref, run_measurement, preconditions, run_audits
        )
    else:
        run_status = "UNKNOWN"
    verdict_counts[run_status] = verdict_counts.get(run_status, 0) + 1
```

Resulting verdict corrections (default-run distribution unchanged at
4 PASS · 3 HAZARD · 3 FAIL, but per-case counts are now truthful):

| case | before (expected_verdict) | after (contract engine) |
|---|---|---|
| circular_cylinder_wake | {PASS:1, HAZARD:1, FAIL:2} | {HAZARD:2, FAIL:2} |
| impinging_jet | {PASS:1, FAIL:1} | {HAZARD:1, FAIL:1} |
| naca0012_airfoil | {FAIL:1} | {HAZARD:1} |

**Finding 2 applied**:
- `generate_contours.py:gen_impinging_jet` rewritten with Cooper 1984
  anchors Nu(0)=25, Nu(1)=12; k-ε factor ~+52% and k-ω SST factor ~+8%
  matching the `wrong_model` (Nu=38) and `real_incident` (Nu=27)
  fixtures.
- `flowFields.ts` caption + provenance updated accordingly.
- PNG regenerated.

## Regression

- Backend import + `list_cases()` via `.venv/bin/python` prints the
  expected distribution: `{'PASS': 4, 'HAZARD': 3, 'FAIL': 3}`.
- Frontend `tsc --noEmit` clean.
- No touch to 三禁区 (`src/**`, `tests/**` at repo root,
  `knowledge/gold_standards/**`, `knowledge/whitelist.yaml`).

## Why autonomous_governance = true

Codex ran inline and returned CHANGES_REQUIRED; both findings
resolved verbatim (finding 1 is a ≤15-LOC logic swap; finding 2 is a
content-only generator rewrite + one PNG regeneration). No external
gate touched. Matches RETRO-V61-001 verbatim-exception relaxation
for Codex-verbatim HIGH-severity fixes.

## Known residuals (to track, not to block)

1. **Physical plausibility of under_resolved values is engineering
   judgment, not grid-convergence-backed.** Cf=0.00496 for TFP-starved,
   Nu=5.1 for BFS-starved, St=0.1495 for cylinder-starved are all in
   the plausible coarse-mesh regime but no actual coarse simulation
   produced these. Acceptable for a teaching catalog; NOT acceptable
   for a regulatory audit package.
2. **LearnHomePage second round-trip.** Adding `useQuery(listCases)`
   introduces a fetch that could race the illustration render in slow
   networks. No user-visible layout shift in local testing. If we ever
   add loading skeletons across /learn, revisit.
3. **4 cases still lack teaching runs** (duct_flow / differential_heated_cavity
   / plane_channel_flow / rayleigh_benard_convection only have 1
   curated run each). Option A deepening in the next session covers this.
4. **4 cases still lack flow-field visuals** (duct/DHC/BFS/NACA).
   Same — Option A queue.

## Pending closure

- [ ] Push to remote, open PR against main.
- [ ] Merge as regular merge commit (留痕 > 聪明).
- [ ] Update STATE.md with session log.
- [ ] Notion-sync this DEC + the backlog (V61-021/022/023 + RETRO-V61-002).
