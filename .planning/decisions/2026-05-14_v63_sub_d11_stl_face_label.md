---
decision_id: DEC-V63-A-sub-D11
title: D11 stl_face_label_validator — face-label-loss class advisor (single-case land · V94 evidence · case_011 v1)
status: Accepted
parent_dec: DEC-V63-A-charter
phase: V63-A Tier 1 supplement · driven by V62-A M-STACK-TRACK-1 §8 enhancement #3 carry-over
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed810385c9e88e644458cf)
---

## Status

Accepted · 2026-05-14 · single-case-land per A2 v1 / D6 / D10 precedent ·
pending 2nd-case cross-validation. V94 carries [QUESTIONABLE] marker
until a 2nd industrial case sediments a face-label-loss class
(case_013 / case_015 CHT-LES are forward-loaded candidates per
``.planning/case_proposal_queue.md``).

## Goal (verbatim from V62-A M-STACK-TRACK-1-rerun §8 #3 + V63-A charter carry-over #1)

> **TRACK-1 §8 enhancement #3 — Decide on `stl_face_label_validator`
> advisor**: STILL OPEN — B33 M-D10-PROMOTE landed
> `bc_type_name_validity_advisor` (different scope: BC-type-name
> validity, not STL face-label inventory). V94-family industrial blind
> spot (case_011 STL files lack labeled inlet/outlet face-zones)
> remains uncovered by the stack. D-class candidate still un-promoted.
> The rerun continues to confirm V94 (degenerate pure-conduction from
> missing STL face labels) is **not** caught by any LANDED advisor
> under either path — the stack still has zero visibility into STL
> face-zone inventory. This is the largest remaining case_011-class
> blind spot and is now the only TRACK-1 §8 item not closed by
> upstream work.
>
> — `.planning/retrospectives/2026-05-14_stack_track_c_session_1_rerun_case_011_v5b.md`
> §8 enhancement #3.

D11 closes that gap. Three detection paths surface face-label drift
across the CAD→STL→sHM contract that the rest of the stack is blind to.

## V94 evidence — canonical face-label-loss death class

V94 entry in
``docs/openfoam_corpus/industrial_solver_findings_v_series.md:1250``
(also mirrored at
``.planning/methodology/industrial_case_solver_findings.md:1384``)
documents the case_011 v1 sediment surfaced 2026-05-14 by the v3
sub-session solver e2e attempt:

> STL files emitted by ``cq.exporters.export()`` carry NO face-zone
> labels — single-shell watertight surfaces lose CAD-stage face names;
> downstream sHM creates only one undifferentiated boundary patch per
> region pair, so any case_profile referencing named inlet/outlet/
> external-wall patches cannot host the intended flow physics.

V94's "Fix (3) Cross-case methodology fix (Pillar-2 candidate)"
literally names ``stl_face_label_validator`` as the advisor candidate;
this DEC is the promotion that closes that fix path.

## Three detection paths (algorithm + finding code)

| # | Code | When it fires | Severity |
|---|---|---|---|
| (a) | ``orphan_declared_label`` | ``parts_manifest['parts'][i]['face_labels']`` declares a label X; ``stl_face_normals`` has no key X. Classic V94: manifest claims ``hot_inlet`` but cq.exporters emitted only ``region_hot_fluid``. | warning |
| (b) | ``duplicate_face_label_in_manifest`` | Same face label X appears in ``face_labels`` of ≥2 parts. sHM/BC orchestration cannot disambiguate which part's patch a BC targeting X applies to. Detection at manifest layer because dict-keyed ``stl_face_normals`` cannot itself express duplicate labels — keys are unique. | warning |
| (c) | ``shm_reference_undeclared_in_manifest`` | ``shm_dict.castellatedMeshControls.refinementSurfaces.<surf>.regions.<X>`` or ``castellatedMeshControls.patches[*].name = X`` references a label X that no part declares in ``face_labels``. Detects "engineer wrote sHM dict assuming patches will exist that the manifest never promised the STL would carry". | warning |

Per V130 advisor-not-driver: each detection path requires its
precondition to be met; absent inputs degrade silently (never raise).
``stl_face_normals=None`` suppresses (a) — we cannot prove a label is
missing from an inventory we never saw.

## Scope

**This sub-DEC adds:**

- ``ui/backend/services/geometry_ingest/stl_face_label_validator.py``
  (486 LOC including docstrings + 2 frozen dataclasses
  ``FaceLabelFinding`` / ``FaceLabelReport`` + 3 private collectors +
  1 public function ``validate_face_label_consistency``)
- ``ui/backend/tests/test_stl_face_label_validator.py`` (11 tests
  covering 3 detection-path happy paths · consistent + empty + V130
  silent-skip + shm patches[] idiom + 4Q gate Q1 + Q4 + TrustGate V94
  + case_011 V94 6-orphan regression)
- ``ui/backend/services/advisor_stack.py`` registration:
  - ``stl_face_label_validator = _load_advisor("stl_face_label_validator")``
  - ``_V_ROWS_PER_ADVISOR["stl_face_label_validator"] = ("V94",)``
  - ``_normalize_face_label`` helper translates ``FaceLabelFinding``
    → ``Finding`` (source_advisor / evidence_v_rows / code / message
    / location / raw — mirrors D10 normalize pattern)
  - ``_should_dispatch_face_label_validator`` gate — dispatch iff at
    least one of {non-empty ``shm_stl_face_normals``, ``parts_manifest``
    declares ``face_labels`` on any part, ``shm_dict`` carries
    ``refinementSurfaces.<surf>.regions`` or
    ``castellatedMeshControls.patches[]``}
  - Dispatch block in ``assemble_stack`` after A8 ``shm_dict_validator``
- ``ui/backend/tests/test_advisor_stack.py`` 4 new tests:
  - ``test_stl_face_normals_dispatches_d11_with_v94_evidence``
  - ``test_d11_silently_skipped_when_no_face_label_data``
  - ``test_d11_crash_is_isolated``
  - ``test_evidence_refs_includes_v94_when_d11_dispatches``
- ``ui/backend/routes/ai_review.py`` wire-schema expansion:
  - ``AIReviewRequest.stl_face_normals: Optional[dict[str, list[list[float]]]] = None``
  - Auto-discovery from ``<case_dir>/cad/face_normals.json``
  - Wire-form list-of-list-of-float → tuple-of-float coercion before
    forwarding to stack as ``shm_stl_face_normals`` (the existing
    stack-side name retained for backward compat with A8 V99-widening
    consumers; D11 reads the same physical input)
  - 400 with ``failing_check: stl_face_normals_type`` on malformed
    shape
- ``ui/backend/tests/test_ai_review_route.py`` 2 new tests:
  - ``test_stl_face_normals_explicit_dispatches_d11_with_v94_evidence``
  - ``test_stl_face_normals_autodiscovered_from_case_dir``

**Net advisor counter delta**: LANDED advisor 10 → 11; D-class advisor
2 → 3 (D6 + D10 + D11).

## This sub-DEC does NOT add

- ❌ STL geometric quality checks (watertightness, flipped normals,
  non-manifold edges) — A4 ``face_orientation_advisor`` is the SSOT.
- ❌ Unit / scale validation — ``unit_detector`` is the SSOT.
- ❌ A8 replacement — A8 keys ``refinementSurfaces.<surf>`` against
  ``geometry``; D11 keys ``refinementSurfaces.<surf>.regions.<label>``
  (one level deeper) against face-label declarations. The two
  advisors share NO finding codes.
- ❌ STL parsing — caller-side trimesh / cadquery / FreeCAD MeshPart
  emits ``stl_face_normals`` upstream; D11 consumes the already-parsed
  dict.
- ❌ Numeric BC validity — D10 ``bc_type_name_validity_advisor`` is
  the SSOT for BC name catalog lookup.
- ❌ Any mutation of ``case_dir`` — V130 advisor-not-driver: D11 only
  returns a frozen ``FaceLabelReport``; the caller decides what to do.
- ❌ Notion sync at land time — per v2.3 round-1 loosen rule, Notion
  sync happens at session-end batch only for ``status: Accepted``
  DECs (this DEC will sync next).
- ❌ Pre-merge Codex review — no security boundary touched (advisor
  is pure-dict consumer + route field is non-auth wire expansion).
  Per v2.3 1-sync-trigger, ``confidence: med`` on Opus self-judgment
  for the diff (3 detection paths + 1 stack registration + 1 route
  field) and on V94 single-case-land precedent.
- ❌ ARC-GOAL.md update — left to B38 / next batch to keep the
  parallel-arc boundary clean (V63-A ARC-GOAL skeleton was being
  authored by B38 in parallel · this DEC fires at sub-DEC level only).

## Evidence — V-row provenance

| label | source | provenance |
|---|---|---|
| V94 | ``docs/openfoam_corpus/industrial_solver_findings_v_series.md:1250`` | Sediment author Claude Code Opus 4.7 · Track C session 2 case_011 v3 sub-session · 2026-05-14 · canonical face-label-loss class; "Fix (3) cross-case methodology fix" literally names ``stl_face_label_validator`` as the proposed advisor |

Drift-v2 enforcement: ``v_series_drift_guard`` regex
``^###\s+(V\d+)\b`` matches the ``### V94 ·`` corpus heading; D11
findings' ``evidence_v_rows=("V94",)`` clear the drift guard under
both ``audit`` and ``strict`` modes.

## Backward compatibility

- **0 advisor signature changes**. A4 / A5 / A8 / A10 / D6 / D10
  / thin_wall / unit_detector / virtual_interface_detector dispatch
  paths unchanged.
- **0 wire-contract changes** for existing fields. The 50 prior route
  tests (test_ai_review_route.py) still pass byte-identical — the new
  ``stl_face_normals`` field is ``Optional[…] = None`` and dispatch
  is gated on ``_should_dispatch_face_label_validator`` returning
  True (existing fixtures without face_labels stay quiet).
- **0 V-row mutations** for prior advisors —
  ``_V_ROWS_PER_ADVISOR`` is append-only.
- **Advisor count stability**: legacy ``assemble_stack(parts_manifest=…)``
  callers with no ``face_labels`` declared stay at ``advisor_count=2``
  (A4 + A5); D11 silently skips per V130. Verified by
  ``test_d11_silently_skipped_when_no_face_label_data``.

## Test catalog — boundary evidence

| boundary case | input | expected verdict | observed |
|---|---|---|---|
| canonical V94 single-shell | manifest declares 3 labels, STL has only parent body | 3 orphan_declared_label warnings | ✓ |
| case_011 full V94 replay | 6 labels across hot+cold, STL has 3 parent bodies | 6 orphan warnings citing V94 | ✓ |
| duplicate label in manifest | same label X under 2 parts | 1 duplicate_face_label_in_manifest warning naming both parts | ✓ |
| shm refers undeclared | shm regions.X but no manifest declares X | 1 shm_reference_undeclared_in_manifest warning | ✓ |
| shm patches[] idiom | patches[].name = X undeclared | same warning code, location reflects patches[i].name | ✓ |
| consistent case | every manifest face_label in STL + shm refs all declared | clean, empty findings | ✓ |
| empty / None inputs | all three inputs None | empty findings, no raise | ✓ |
| malformed shapes | non-dict / non-string / non-list values | silent skip per V130, no raise | ✓ |
| silent-skip without STL | stl_face_normals=None | (a) does not fire; (b)+(c) still fire | ✓ |
| 4Q Q1 LLM-offline | inspect.getsource() scans for openai/anthropic/google.generativeai | clean | ✓ |
| 4Q Q4 no writes | builtins.open watcher across all 3 detection paths | 0 write_attempts | ✓ |
| stack: D11 happy path | shm_stl_face_normals + manifest face_labels | advisor_calls includes D11, 2 V94 orphans | ✓ |
| stack: D11 silent skip | parts_manifest without face_labels | D11 not in advisor_calls (advisor_count stays 2) | ✓ |
| stack: D11 crash isolated | monkeypatch validate_face_label_consistency → RuntimeError | other advisors still run, failed_advisor_count == 1, JSON-serializable error payload | ✓ |
| stack: evidence_refs union | D11 dispatches alone | "V94" in evidence_refs, "V79"/"V52" absent | ✓ |
| route: explicit stl_face_normals | POST with wire-form normals | 200, D11 in advisor_calls, 2 orphan findings | ✓ |
| route: case_dir auto-discover | case_dir/cad/face_normals.json on disk only | 200, D11 in advisor_calls, 1 orphan finding | ✓ |

## Surface scan

Per DEC-V61-088 pre-implementation discipline:

1. **ROADMAP scan** — V62-A B34 retro TRACK-1 §8 enhancement #3
   ("STILL OPEN · D-class candidate still un-promoted") + V63-A
   charter 6 carry-over items #1 (D11 stl_face_label_validator)
   explicitly named this advisor as the promotion target.
2. **Existing-implementation grep** —
   ``grep -rin "stl_face_label\|D11" ui/backend/`` at HEAD before
   this DEC returned only ``.audit_package_staging/*`` SHA-prefix
   coincidences (not source code). No prior implementation found
   → clean greenfield.

**Surface-scan trailer**: clean.

## v2.3 compliance

- **Sub-DEC scope**: this DEC touches 5 source paths (advisor module +
  3 tests files + advisor_stack registration + ai_review wire field).
  At the v2.3 ≥3-shared-code-paths sub-DEC threshold but below
  charter-trigger; full sub-DEC body authored under parent
  ``DEC-V63-A-charter``.
- **Codex review**: SKIPPED — per v2.3 1-sync-trigger no auth /
  signing / security-boundary change. Advisor is pure-dict consumer
  (zero external surface); route field is non-auth wire-schema
  expansion identical to REQ-SCHEMA-EXPAND + D10 precedent.
  ``confidence: med`` on Opus self-judgment.
- **Kogami**: NOT invoked — opt-in only per v2.3; no charter scope
  change.
- **Counter**: +1 to ``autonomous_governance_counter_v61`` (autonomous
  governance · land without external gate).
- **Notion sync**: pending — flag ``notion_sync_status: pending``;
  flips to ``synced <date> (<url>)`` at session-end batch sync only
  if this DEC remains ``Status: Accepted``.
- **Round cap**: N/A — no Codex review chain run.

## Promotion gate (single-case-land → [VALIDATED])

D11 lands as ``single-case-land`` per A2 v1 / D6 / D10 precedent:

- **Current evidence**: V94 (case_011 v1 plate-fin compact HX,
  cq.exporters single-shell STL emission losing CAD-stage face names)
  — single case.
- **[QUESTIONABLE] marker**: V94 keeps the
  ``[QUESTIONABLE 2026-05-14 single-case land]`` status until a 2nd
  industrial case sediments a face-label-loss class OR runs a live
  Track C session where D11 fires on an actual case_011-class blind
  spot. Forward-loaded candidates: case_013 (CHT cyclic) / case_015
  (CHT-LES) / case_018 (cyclone) / any case adopting per-region STL
  emission from cadquery.
- **No artificial backfill** — sediment must arise from an actual
  Track C session or industrial reference case running the substrate,
  not synthesized.

## Confidence: med

- **High on the diff correctness** — 74 tests green (11 advisor + 4
  stack-dispatch + 2 route-wire + 22 prior stack regression + 35
  prior route regression); explicit-kwarg-wins precedence matches D10
  pattern; 4Q gate inline-verified for both advisor source + stack
  dispatch + route; ``_should_dispatch_face_label_validator`` gate
  preserves ``advisor_count`` stability on all 22 prior stack
  fixtures.
- **Med on the catalog/detection completeness** — the dispatch-gate
  set is currently the union of three explicit preconditions; future
  case shapes (e.g. polyMesh ``boundary`` parsing as a third source
  of face-label references) may need additional walks. The
  alternative (exhaustive sHM dict region recursion) is out of scope
  for single-case-land and would couple the advisor to specific
  OpenFOAM dict-emission idioms beyond what V94 evidence supports.
- **Med on V94 single-case-land** — A2 v1 / D6 / D10 precedent.
  Pre-existing convention requires a 2nd-case sediment before
  flipping to [VALIDATED]; D11 inherits the same gate.

## Closing reference

- V62-A M-STACK-TRACK-1 §8 enhancement #3 closes (V94 face-label-loss
  D-class candidate → D11 LANDED).
- V63-A charter carry-over #1 closes.
- LANDED advisor counter advances 10 → 11.
- D-class advisor counter advances 2 → 3 (D6 + D10 + D11).
- ARC-GOAL.md update deferred to next batch / parallel B38 arc per
  task brief.
