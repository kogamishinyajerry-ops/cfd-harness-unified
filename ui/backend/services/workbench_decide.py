"""DEC-V61-202-SUB-M30-CYCLE1 · `decide(CaseState) -> WorkbenchFrame`.

Pure deterministic function. No LLM call (V130 invariant). No I/O
inside `decide()` itself — the route handler loads inputs and passes a
fully-populated `CaseStateSnapshot`. This keeps the function unit-
testable and reproducible from a state SHA alone.

Priority decision tree (top wins):
    1. FAIL-severity audit finding on current step
    2. critical missing manifest field on current step
    3. WARN-severity audit finding on current step
    4. warning/info missing manifest field on current step
    5. step default frame

Step-relevance mapping (which signals belong to which step):
    Step 1 Geometry  -> geometry_contract.*, geometry_report.json
    Step 2 Mesh      -> mesh_contract.*, mesh_report.json
    Step 3 Physics   -> physics.*, *_contract.* (compressible/les/vof),
                        solver_contract.*
    Step 4 BCs       -> bc_contract.*, bc_quality.json, bc_audit.json
    Step 5 Solve+Pp  -> solver_contract.residual_targets.*,
                        qoi_contract.*, trust_report.json
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from ui.backend.schemas.workbench_frame import (
    BottomCard,
    CaseStateSnapshot,
    RailPrimary,
    TopbarCta,
    ViewportOverlay,
    WorkbenchFrame,
)

# Step → JSON-path prefix mapping. Used to route problems + gaps to the
# step on which they should surface. A gap with prefix in multiple
# steps' lists goes to the first matching step.
_STEP_PATH_PREFIXES: dict[int, tuple[str, ...]] = {
    1: ("geometry_contract.", "geometry."),
    2: ("mesh_contract.", "mesh."),
    3: (
        "physics.",
        "compressible_contract.",
        "les_contract.",
        "vof_contract.",
        "solver_contract.",
        "solver",
    ),
    4: ("bc_contract.", "boundary_conditions.", "bc.patches", "bc."),
    5: (
        "solver_contract.residual_targets.",
        "qoi_contract.",
        "qoi_stability",
    ),
}

# Step → audit-artifact filenames that contribute problems to that step.
_STEP_ARTIFACTS: dict[int, tuple[str, ...]] = {
    1: ("geometry_report.json",),
    2: ("mesh_report.json",),
    3: (),  # Physics step problems come from manifest gaps, not artifacts.
    4: ("bc_quality.json", "bc_audit.json"),
    5: ("trust_report.json",),
}


def decide(state: CaseStateSnapshot) -> WorkbenchFrame:
    """Pure function: state → frame. No I/O, no network.

    Frame is deterministic — same state in → same frame out. State SHA
    on the frame lets the frontend skip re-render when nothing changed.

    DEC-V61-202-SUB-M30-CYCLE6: after building the frame, fire a
    best-effort provenance log line. The log writer is itself
    no-raise (audit logging never breaks the engineer's flow), and
    decide() wraps the call in try/except as defense in depth. Gated
    by WORKBENCH_PROVENANCE_DISABLED=1 (e.g., for unit tests that
    don't want sidecar files).
    """

    rail = _pick_rail_primary(state)
    overlays = _pick_overlays(state)
    cards = _pick_bottom_cards(state)
    topbar = _pick_topbar_cta(state, rail)
    frame = WorkbenchFrame(
        case_id=state.case_id,
        step=state.step,
        rail_primary=rail,
        viewport_overlays=overlays,
        bottom_cards=cards,
        topbar_cta=topbar,
        state_sha=_state_sha(state),
        manifest_state_sha=_manifest_state_sha(state.case_id, state.manifest),
        decided_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        from ui.backend.services.workbench_decide_provenance import log_decision

        log_decision(state, frame)
    except Exception:  # noqa: BLE001 — defense in depth
        pass
    return frame


def _manifest_state_sha(case_id: str, manifest: dict) -> str:
    """SHA-256 of manifest-only canonical bytes (DEC-V61-202 cycle 2).

    Frontend sends this on PATCH; backend recomputes it independently
    to validate optimistic concurrency. Excludes step / focus /
    artifacts because a manifest write doesn't depend on those, and
    including them would cause spurious 409s when an unrelated audit
    artifact refreshes.
    """
    import hashlib
    import json
    payload = {"case_id": case_id, "manifest": _canonical(manifest)}
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ────────────────────────── topbar_cta (cycle 2) ──────────────────────────


def _pick_topbar_cta(state: CaseStateSnapshot, rail: RailPrimary) -> TopbarCta:
    """The 4th driver slot. Decides what 'next' means in this state.

    Mapping:
        rail.kind == "problem_fix"  → "复检 / Re-audit"
        rail.kind == "info_gap"     → CTA disabled + reason
        rail.kind == "step_default" + step < 5 → "下一步 / Next step"
        rail.kind == "step_default" + step == 5 → "提交求解 / Submit solve"
    """
    if rail.kind == "problem_fix":
        return TopbarCta(
            kind="re_audit",
            label="复检 / Re-audit",
            target_step=None,
            enabled=True,
            reason=None,
        )

    if rail.kind == "info_gap":
        gap_path = rail.field_path or "上游字段"
        return TopbarCta(
            kind="step_default",
            label="下一步 / Next step",
            target_step=state.step + 1 if state.step < 5 else None,
            enabled=False,
            reason=f"先补齐 {gap_path} 才能进入下一步 / Fill {gap_path} first",
        )

    # step_default branch
    if state.step == 5:
        return TopbarCta(
            kind="submit_solve",
            label="提交求解 / Submit solve",
            target_step=None,
            enabled=True,
            reason=None,
        )

    return TopbarCta(
        kind="next_step",
        label="下一步 / Next step",
        target_step=state.step + 1,
        enabled=True,
        reason=None,
    )


# ────────────────────────── rail_primary ──────────────────────────


def _pick_rail_primary(state: CaseStateSnapshot) -> RailPrimary:
    """Priority decision tree for what goes in the rail's top card.

    Cycle 3: when focus_patch is set, focus-matching problems/gaps
    win the same-severity tie against non-matching ones (driver 4
    per SSOT §3).
    """

    fail_problems = _problems_for_step(state, severities=("fail",))
    if fail_problems:
        return _rail_from_problem(
            _prefer_focus_match(state, fail_problems), state
        )

    crit_gaps = _gaps_for_step(state, severities=("critical",))
    if crit_gaps:
        return _rail_from_gap(_prefer_focus_match(state, crit_gaps), state)

    warn_problems = _problems_for_step(state, severities=("warn",))
    if warn_problems:
        return _rail_from_problem(
            _prefer_focus_match(state, warn_problems), state
        )

    soft_gaps = _gaps_for_step(state, severities=("warning", "info"))
    if soft_gaps:
        return _rail_from_gap(_prefer_focus_match(state, soft_gaps), state)

    return _rail_default(state)


def _prefer_focus_match(state: CaseStateSnapshot, items: list[dict]) -> dict:
    """Cycle 3: same-severity tie-break by focus_patch relevance.

    When focus_patch is set + at least one item mentions the focused
    patch, return that item. Otherwise return items[0] (existing
    severity-sorted behavior).
    """
    if not state.focus_patch or not items:
        return items[0]
    for item in items:
        if _focus_matches(state, item):
            return item
    return items[0]


def _focus_matches(state: CaseStateSnapshot, item: dict) -> bool:
    """True iff `item` references the focused patch.

    Checks three signal channels:
        1. item.field_path contains the patch name (e.g.
           "bc_contract.inlet.velocity.type" when focus_patch="inlet")
        2. item.body / message text mentions the patch name
        3. item is a bc_audit dimension that lists the patch in
           gaps_by_field

    Conservative substring match — false positives (e.g. "inlet" matches
    "inlet_tunnel") are accepted; the alternative is exact-match which
    misses obvious patch-relevant findings.
    """
    if not state.focus_patch:
        return False
    needle = state.focus_patch
    field_path = item.get("field_path") or ""
    body = item.get("body") or item.get("message") or ""
    if needle in str(field_path):
        return True
    if needle in str(body):
        return True
    # Best-effort: if the item's raw payload has a dimension shape with
    # gaps_by_field, look there too.
    raw_gaps = item.get("_raw_gaps_by_field")
    if isinstance(raw_gaps, dict):
        for missing_list in raw_gaps.values():
            if isinstance(missing_list, list) and needle in missing_list:
                return True
    # Codex R0 P2-B fix: bc_audit value_match / type_mismatches forwards
    # concrete patch names via _resolved_patches. The viewport pick uses
    # the concrete patch name (e.g. "topWall"), not the manifest key
    # (e.g. "wall"), so this is the only channel that catches those.
    resolved = item.get("_resolved_patches")
    if isinstance(resolved, (list, tuple, set)) and needle in resolved:
        return True
    return False


_FAILURE_SUBLIST_KEYS = frozenset(
    {
        "value_mismatches",
        "type_mismatches",
        "mismatches",
        "missing",
        # Codex R2 P2 fix: BC audit also emits patch-specific FAIL
        # records under these names. Without them, focus_patch fails
        # to match value/derived BC failures.
        "value_missing",
        "derived_mismatches",
        "derived_missing",
        # Generic finding families used across other dimensions.
        "issues",
        "failures",
        "errors",
        "findings",
        "gaps",
        "violations",
    }
)


def _collect_resolved_patches(dim_value: dict) -> list[str]:
    """Walk a dimension dict's FAIL-class sublists for `resolved_patch`.

    Real bc_audit shapes (channel_flow_rans_sst.bc_audit.json) carry
    concrete patch names inside per-finding dicts:

        {
          "matched":   [{"field": "U", "resolved_patch": "inlet", ...}],   # PASS records
          "checked":   [{"field": "U", "resolved_patch": "topWall", ...}], # passing checks
          "value_mismatches": [
            {"field": "U", "resolved_patch": "inlet", ...},                # FAIL records
            {"field": "p", "resolved_patch": "outlet", ...},
          ],
          "type_mismatches": [
            {"field": "U", "resolved_patch": "topWall", ...},
          ],
        }

    Codex R1 P2 fix: only walk FAIL-class sublists (whitelisted by name).
    Earlier all-list walk over-attributed a failing dimension to patches
    that only appeared in successful ``matched`` / ``checked`` records,
    so focusing such a passing patch incorrectly bubbled an unrelated
    FAIL above the actually related one.

    We collect distinct ``resolved_patch`` strings across all whitelisted
    1-level-deep list-of-dict values inside the dimension. Order is
    preserved (insert order); duplicates dropped via dict.fromkeys.
    """
    out: list[str] = []
    for key, v in dim_value.items():
        if not isinstance(key, str):
            continue
        if key not in _FAILURE_SUBLIST_KEYS:
            continue
        if not isinstance(v, list):
            continue
        for entry in v:
            if not isinstance(entry, dict):
                continue
            patch = entry.get("resolved_patch")
            if isinstance(patch, str) and patch:
                out.append(patch)
    # Preserve insertion order, drop dups.
    return list(dict.fromkeys(out))


def _rail_from_problem(problem: dict, state: CaseStateSnapshot) -> RailPrimary:
    severity = str(problem.get("severity", "info"))
    title = str(problem.get("title") or problem.get("rule") or "Audit finding")
    body = problem.get("message") or problem.get("body") or None
    field_path = problem.get("field_path") or None
    artifact = problem.get("_source_artifact")
    provenance = [
        f"step={state.step} · problem_fix · severity={severity}",
        f"source={artifact or 'unknown'}",
    ]
    if field_path:
        provenance.append(f"field_path={field_path}")
    return RailPrimary(
        kind="problem_fix",
        title=title[:60],
        body_text=body,
        field_path=field_path,
        cta_label="查看 / View",
        provenance=provenance,
    )


def _rail_from_gap(gap: dict, state: CaseStateSnapshot) -> RailPrimary:
    severity = str(gap.get("severity", "info"))
    field_path = gap.get("field_path", "")
    title = f"补充字段 / Fill: {field_path}" if field_path else "缺字段"
    body = gap.get("why") or None
    # DEC-V61-202-SUB-M31-CYCLE1: domain-aware form helper. When the
    # completeness analyzer attached a structural skeleton (e.g. the
    # canonical 3-patch ship_vof bc.patches dict), forward it onto the
    # rail. The frontend renders an "Apply skeleton" CTA when this is
    # non-null. Both `suggested_default` (scalar) and `suggested_skeleton`
    # (dict) are forwarded independently — the frontend picks which
    # CTA(s) to render.
    suggested_default = gap.get("suggested_default")
    suggested_skeleton = gap.get("suggested_skeleton")
    if suggested_default is not None:
        cta_label = "填入 / Apply"
    elif suggested_skeleton is not None:
        # Codex R0 P2 fix (DEC-V61-202-SUB-M31-CYCLE1): when ONLY a
        # skeleton is offered, suppress the primary CTA — the frontend's
        # secondary skeleton button is the action. Otherwise we render
        # two identical "Apply skeleton" buttons (primary disabled
        # because canApply needs suggested_default, secondary live).
        cta_label = None
    else:
        cta_label = "编辑 / Edit"
    provenance = [
        f"step={state.step} · info_gap · severity={severity}",
        f"field_path={field_path}",
    ]
    if suggested_skeleton is not None:
        provenance.append(f"skeleton_keys={sorted(suggested_skeleton.keys())}")
    return RailPrimary(
        kind="info_gap",
        title=title[:60],
        body_text=body,
        field_path=field_path or None,
        suggested_default=suggested_default,
        suggested_skeleton=suggested_skeleton,
        cta_label=cta_label,
        provenance=provenance,
    )


def _rail_default(state: CaseStateSnapshot) -> RailPrimary:
    titles = {
        1: "Step 1 · 几何就绪 / Geometry ready",
        2: "Step 2 · 网格就绪 / Mesh ready",
        3: "Step 3 · 物理已设 / Physics set",
        4: "Step 4 · 边界已设 / BCs set",
        5: "Step 5 · 准备求解 / Ready to solve",
    }
    bodies = {
        1: "当前步无阻塞 — 可以进入下一步。",
        2: "当前步无阻塞 — 可以进入下一步。",
        3: "当前步无阻塞 — 可以进入下一步。",
        4: "当前步无阻塞 — 可以进入下一步。",
        5: "当前步无阻塞 — 可以提交求解。",
    }
    return RailPrimary(
        kind="step_default",
        title=titles.get(state.step, "Step ready"),
        body_text=bodies.get(state.step),
        cta_label="下一步 / Next",
        provenance=[f"step={state.step} · step_default · no blockers"],
    )


# ────────────────────────── viewport_overlays ──────────────────────────


def _pick_overlays(state: CaseStateSnapshot) -> list[ViewportOverlay]:
    overlays: list[ViewportOverlay] = []

    # Focus-driven highlight (driver 4): if engineer focused a patch,
    # paint it. Visible on all steps where patch focus makes sense.
    if state.focus_patch:
        overlays.append(
            ViewportOverlay(
                kind="patch_highlight",
                target=state.focus_patch,
                severity="info",
                label=state.focus_patch,
            )
        )
    if state.focus_region:
        overlays.append(
            ViewportOverlay(
                kind="region_highlight",
                target=state.focus_region,
                severity="info",
                label=state.focus_region,
            )
        )

    # Step 2: cell count badge + checkmesh warning when present.
    #
    # Codex R0 P2: the real `mesh_report.json` shape (from
    # cfdtrust/audit/mesh.py) stores cell count at `stats.cells` and
    # max non-orthogonality at `quality_dimension.metrics.
    # max_non_orthogonality.actual`. Older test fixtures sometimes use
    # flat top-level keys; we honor both for backward compat.
    if state.step == 2:
        mesh_report = state.artifacts.get("mesh_report.json", {}) or {}
        n_cells = _mesh_cell_count(mesh_report)
        if isinstance(n_cells, int) and n_cells > 0:
            overlays.append(
                ViewportOverlay(
                    kind="cell_count_badge",
                    label=_format_cell_count(n_cells),
                    severity="info",
                )
            )
        non_ortho = _mesh_non_orthogonality(mesh_report)
        if isinstance(non_ortho, (int, float)) and non_ortho > 70:
            overlays.append(
                ViewportOverlay(
                    kind="checkmesh_warn",
                    label=f"non-orthogonality {non_ortho:.0f}°",
                    severity="warn" if non_ortho < 85 else "fail",
                )
            )

    return overlays


def _mesh_cell_count(mesh_report: dict) -> int | None:
    """Extract cell count from real cfdtrust/audit/mesh.py shape.

    Real shape: `mesh_report["stats"]["cells"]` (int).
    Backward-compat: flat `n_cells` / `nCells` keys.
    """
    stats = mesh_report.get("stats")
    if isinstance(stats, dict):
        c = stats.get("cells")
        if isinstance(c, int) and c > 0:
            return c
    fallback = mesh_report.get("n_cells") or mesh_report.get("nCells")
    if isinstance(fallback, int) and fallback > 0:
        return fallback
    return None


def _mesh_non_orthogonality(mesh_report: dict) -> float | None:
    """Extract max non-orthogonality from real cfdtrust shape.

    Real shape:
      mesh_report["quality_dimension"]["metrics"]
        ["max_non_orthogonality"]["actual"]  -> float
    Backward-compat: flat `max_non_orthogonality` key.
    """
    qd = mesh_report.get("quality_dimension")
    if isinstance(qd, dict):
        metrics = qd.get("metrics")
        if isinstance(metrics, dict):
            entry = metrics.get("max_non_orthogonality")
            if isinstance(entry, dict):
                actual = entry.get("actual")
                if isinstance(actual, (int, float)):
                    return float(actual)
    fallback = mesh_report.get("max_non_orthogonality")
    if isinstance(fallback, (int, float)):
        return float(fallback)
    return None


def _format_cell_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M cells"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k cells"
    return f"{n} cells"


# ────────────────────────── bottom_cards ──────────────────────────


def _pick_bottom_cards(state: CaseStateSnapshot) -> list[BottomCard]:
    """All step-relevant problems + gaps as cards.

    Bottom cards are the full visible list (sorted FAIL > WARN > info),
    while rail_primary picks just the top one. Cap at 8 cards to keep
    the panel scannable.

    Cycle 3: when focus_patch is set, focus-matching cards bubble to
    the top within their severity bucket (driver 4 per SSOT §3).
    """

    cards: list[BottomCard] = []
    raw_items: list[tuple[dict, BottomCard]] = []

    problems = _problems_for_step(state, severities=("fail", "warn", "info"))
    for p in problems:
        card = BottomCard(
            kind="audit_finding",
            title=str(p.get("title") or p.get("rule") or "Audit finding")[:80],
            body_text=str(p.get("message") or p.get("body") or "")[:400],
            severity=_normalize_severity(p.get("severity", "info")),
            source_artifact=p.get("_source_artifact"),
            field_path=p.get("field_path"),
        )
        raw_items.append((p, card))

    for g in _gaps_for_step(state, severities=("critical", "warning", "info")):
        card = BottomCard(
            kind="missing_field",
            title=f"缺字段 / Missing: {g.get('field_path', '')}"[:80],
            body_text=str(g.get("why") or "")[:400],
            severity=_normalize_severity(g.get("severity", "info")),
            source_artifact="completeness_report",
            field_path=g.get("field_path"),
        )
        raw_items.append((g, card))

    # Cycle 3: re-sort so focus-matching cards bubble up within their
    # severity bucket. Stable sort preserves the existing severity
    # ordering when no focus is set or no matches exist.
    #
    # Codex R0 P2-A fix: focus bias operates WITHIN a (severity, kind)
    # sub-bucket, not across kinds. Audit FAIL findings must still rank
    # ahead of completeness critical gaps at the same severity rank —
    # otherwise a focus-matching critical gap can render above an
    # unrelated FAIL even though _pick_rail_primary still picks the
    # FAIL, which is incoherent UX.
    def _kind_rank(card: BottomCard) -> int:
        # audit_finding ranks ahead of missing_field at the same severity
        return 0 if card.kind == "audit_finding" else 1

    if state.focus_patch:
        raw_items.sort(
            key=lambda t: (
                _severity_rank(t[1].severity),
                _kind_rank(t[1]),
                0 if _focus_matches(state, t[0]) else 1,
            )
        )
    else:
        raw_items.sort(
            key=lambda t: (
                _severity_rank(t[1].severity),
                _kind_rank(t[1]),
            )
        )

    cards = [t[1] for t in raw_items]

    # Step hint cards — surface the "what is this step about" line so
    # the bottom panel is never empty on a clean case.
    if not cards:
        hint = _STEP_HINTS.get(state.step)
        if hint:
            cards.append(
                BottomCard(
                    kind="step_hint",
                    title=hint["title"],
                    body_text=hint["body"],
                    severity="info",
                )
            )

    return cards[:8]


_STEP_HINTS: dict[int, dict[str, str]] = {
    1: {
        "title": "Step 1 · 几何 / Geometry",
        "body": "导入 STL/STEP，验证拓扑封闭与单位，命名 patches。",
    },
    2: {
        "title": "Step 2 · 网格 / Mesh",
        "body": "生成或导入网格，关注 cell 数、非正交度、边界层。",
    },
    3: {
        "title": "Step 3 · 物理 / Physics",
        "body": "选择求解器、湍流模型、流体属性、稳态/瞬态。",
    },
    4: {
        "title": "Step 4 · 边界条件 / BCs",
        "body": "为每个面设置 BC 类型 + 数值；engine 会比对 expected_fields。",
    },
    5: {
        "title": "Step 5 · 求解与后处理 / Solve+Postp",
        "body": "目标残差 / QoI 稳定判据 / 收敛监控 / 提取结果。",
    },
}


# ────────────────────────── problems extraction ──────────────────────────


def _problems_for_step(
    state: CaseStateSnapshot, *, severities: tuple[str, ...]
) -> list[dict]:
    """Extract audit-artifact problems relevant to the current step.

    Source artifacts: per `_STEP_ARTIFACTS`. Each artifact's `findings`
    or `issues` list is normalized to {severity, title, message,
    field_path, _source_artifact} dicts.
    """

    out: list[dict] = []
    for artifact_name in _STEP_ARTIFACTS.get(state.step, ()):
        artifact = state.artifacts.get(artifact_name)
        if not isinstance(artifact, dict):
            continue
        for raw in _iter_problems_from_artifact(artifact, artifact_name):
            sev = _normalize_severity(raw.get("severity", "info"))
            if sev in severities:
                out.append(raw)
    # Stable sort by severity rank (fail > warn > info)
    out.sort(key=lambda p: _severity_rank(p.get("severity", "info")))
    return out


def _iter_problems_from_artifact(
    artifact: dict, artifact_name: str
):
    """Walk a single artifact looking for finding-shaped entries.

    Handles three families of audit-artifact shapes:

    (a) **Real cfdtrust shape** (production) — `gate_status` top-level
        + per-dimension `<X>_dimension.dimension_status`. trust_report
        uses `gates.<name>.status`. Emitted by
        cfdtrust/audit/mesh.py, boundary_conditions.py, geometry.py.

    (b) **Test fixture shape** — top-level `findings` / `issues` /
        `problems` lists. Used by older tests + dogfood fixtures.

    (c) **Simple verdict shape** — top-level `verdict` + `reason`. Used
        by minimal test fixtures (e.g. bc_quality.json shorthand).

    All three shapes normalize to a common dict.
    """

    # (a.1) trust_report.json — gates dict pattern
    gates = artifact.get("gates")
    if isinstance(gates, dict):
        for gate_name, gate in gates.items():
            if not isinstance(gate, dict):
                continue
            status = gate.get("status")
            sev = _gate_status_to_severity(status)
            if sev is None:
                continue
            yield {
                "severity": sev,
                "title": f"{gate_name} {status}",
                "rule": gate_name,
                "message": gate.get("summary"),
                "body": gate.get("summary"),
                "field_path": None,
                "_source_artifact": artifact_name,
            }

    # (a.2) Top-level gate_status + per-dimension dimension_status
    top_gate = artifact.get("gate_status")
    top_sev = _gate_status_to_severity(top_gate)
    if top_sev is not None and not gates:
        # If trust_report's gates list already covered it, don't double-
        # emit. Otherwise surface the top-level gate.
        yield {
            "severity": top_sev,
            "title": f"{artifact_name} {top_gate}",
            "rule": None,
            "message": _first_note(artifact),
            "body": _first_note(artifact),
            "field_path": None,
            "_source_artifact": artifact_name,
        }
    # Per-dimension drill-down (any *_dimension key with dimension_status)
    for key, value in artifact.items():
        if not (isinstance(key, str) and key.endswith("_dimension")):
            continue
        if not isinstance(value, dict):
            continue
        dim_status = value.get("dimension_status")
        sev = _dim_status_to_severity(dim_status)
        if sev is None:
            continue
        # Cycle 3: forward gaps_by_field (real bc_audit patch_coverage
        # shape) so _focus_matches can detect patch-level relevance.
        raw_gaps = value.get("gaps_by_field")
        # Codex R0 P2-B fix: also walk nested arrays for resolved_patch
        # (real bc_audit value_match / type_mismatches shape). The
        # viewport publishes the concrete patch name; without this,
        # focus_patch="topWall" never matches a FAIL surfaced via
        # type_mismatches[].resolved_patch="topWall".
        resolved = _collect_resolved_patches(value)
        yield {
            "severity": sev,
            "title": f"{key.replace('_dimension', '')} {dim_status}",
            "rule": key,
            "message": _dim_reason(value),
            "body": _dim_reason(value),
            "field_path": None,
            "_source_artifact": artifact_name,
            "_raw_gaps_by_field": raw_gaps if isinstance(raw_gaps, dict) else None,
            "_resolved_patches": resolved if resolved else None,
        }

    # (b) findings / issues / problems list
    candidates = []
    for key in ("findings", "issues", "problems"):
        v = artifact.get(key)
        if isinstance(v, list):
            candidates.extend(v)

    for c in candidates:
        if not isinstance(c, dict):
            continue
        yield {
            "severity": c.get("severity") or c.get("level") or "info",
            "title": c.get("title") or c.get("rule") or c.get("code"),
            "rule": c.get("rule") or c.get("code"),
            "message": c.get("message") or c.get("description") or c.get("body"),
            "body": c.get("body"),
            "field_path": c.get("field_path") or c.get("path"),
            "_source_artifact": artifact_name,
        }

    # (c) Simple verdict shape (used by test fixtures + bc_quality.json
    # shorthand). Skip when gate_status already covered it to avoid
    # double-counting.
    if top_sev is None:
        verdict = artifact.get("verdict")
        reason = artifact.get("reason") or artifact.get("why")
        if isinstance(verdict, str) and verdict.lower() in ("fail", "warn"):
            yield {
                "severity": verdict.lower(),
                "title": f"{artifact_name} verdict={verdict}",
                "rule": artifact.get("rule"),
                "message": reason,
                "body": reason,
                "field_path": None,
                "_source_artifact": artifact_name,
            }


def _gate_status_to_severity(status) -> str | None:
    """Map cfdtrust gate_status / gates[].status to severity.

    PASS → None (not a problem)
    FAIL → "fail"
    INCOMPLETE / MOCKED → "warn"
    Anything else → None
    """
    if not isinstance(status, str):
        return None
    s = status.upper()
    if s == "FAIL":
        return "fail"
    if s in ("INCOMPLETE", "MOCKED"):
        return "warn"
    return None


def _dim_status_to_severity(status) -> str | None:
    """Map *_dimension.dimension_status to severity.

    PASS → None
    FAIL → "fail"
    INCOMPLETE → "warn"
    """
    if not isinstance(status, str):
        return None
    s = status.upper()
    if s == "FAIL":
        return "fail"
    if s == "INCOMPLETE":
        return "warn"
    return None


def _first_note(artifact: dict) -> str | None:
    """Surface the first `notes[]` entry as a problem message when
    `gate_status` is FAIL/INCOMPLETE/MOCKED. Real cfdtrust artifacts use
    `notes` as the human-readable explanation channel.
    """
    notes = artifact.get("notes")
    if isinstance(notes, list) and notes:
        first = notes[0]
        if isinstance(first, str):
            return first
    return None


def _dim_reason(dimension: dict) -> str | None:
    """Extract a useful per-dimension reason string.

    Real cfdtrust dimensions store explanation in `reason` (preferred),
    `fails` (list of metric names), or `note`.
    """
    r = dimension.get("reason")
    if isinstance(r, str) and r:
        return r
    fails = dimension.get("fails")
    if isinstance(fails, list) and fails:
        return f"failed: {', '.join(str(f) for f in fails)}"
    note = dimension.get("note")
    if isinstance(note, str) and note:
        return note
    return None


# ────────────────────────── gaps extraction ──────────────────────────


# DEC-V61-202-SUB-M31-CYCLE1: form-helper skeleton registry. Keyed by
# (field_path, case_family) so the lookup is unambiguous. Cycle 1
# registers ship_vof bc.patches only; M3.1 cycle 2+ extends to other
# (family, field) pairs. The skeletons are intentionally placeholder-
# heavy (e.g. U=[1,0,0] is not the KCS Fr=0.26 velocity) so the engineer
# must visit the field post-apply — the helper accelerates dict-shape
# typing, it does not substitute for domain knowledge.
_FORM_HELPER_SKELETONS: dict[tuple[str, str], dict] = {
    ("bc.patches", "ship_vof"): {
        "inlet":  {"patch_type": "fixedValue",   "fields": {"U": [1.0, 0.0, 0.0]}},
        "outlet": {"patch_type": "zeroGradient", "fields": {"p": "zeroGradient"}},
        "wall":   {"patch_type": "noSlip",       "fields": {}},
    },
}


def _resolve_case_family(state: CaseStateSnapshot) -> str | None:
    """Resolve a case_family label for skeleton lookup.

    Tries (1) explicit `case_family` on the manifest dict, then
    (2) solver-based inference for imported cases (the M5 scaffold
    `manifest_writer.py` does NOT persist `case_family`, so production
    imports never carry it). Cycle 1 fallback: `physics.solver ==
    "interFoam"` → `ship_vof`. M3.1 cycle 2+ persists case_family
    properly and removes the inference layer.

    Codex R0 P1 fix (DEC-V61-202-SUB-M31-CYCLE1): without this fallback
    the form-helper CTA appears only in tests/dogfood that hand-inject
    case_family, never in production imports.
    """
    if not isinstance(state.manifest, dict):
        return None
    explicit = state.manifest.get("case_family")
    if isinstance(explicit, str) and explicit:
        return explicit
    physics = state.manifest.get("physics")
    if isinstance(physics, dict):
        solver = physics.get("solver")
        if solver == "interFoam":
            return "ship_vof"
    return None


def _skeleton_for_gap(gap: dict, state: CaseStateSnapshot) -> dict | None:
    """Look up the canonical structural skeleton for this (gap, case_family)
    pair, if one is registered. Returns None when no skeleton applies —
    e.g. case_family unknown, or this field_path has no helper yet.

    Cycle 1 lookup is keyed by (field_path, case_family). case_family
    is resolved via `_resolve_case_family` (explicit field on the
    manifest, or solver-based inference when the imported-case scaffold
    didn't persist a family).
    """
    field_path = str(gap.get("field_path", ""))
    if not field_path:
        return None
    case_family = _resolve_case_family(state)
    if case_family is None:
        return None
    return _FORM_HELPER_SKELETONS.get((field_path, case_family))


def _gaps_for_step(
    state: CaseStateSnapshot, *, severities: tuple[str, ...]
) -> list[dict]:
    """Extract missing-field gaps relevant to the current step.

    Source: state.completeness.missing[]. Each entry's `field_path` is
    matched against `_STEP_PATH_PREFIXES[step]`. Severity from the
    completeness report's vocabulary (critical / warning / info).

    DEC-V61-202-SUB-M31-CYCLE1: when a (field_path, case_family) match
    exists in `_FORM_HELPER_SKELETONS`, attach the skeleton to the gap
    dict before `_rail_from_gap` consumes it. The rail builder stays
    oblivious to family-specific logic — it only reads
    `gap.get("suggested_skeleton")`.
    """

    if not state.completeness:
        return []

    missing = state.completeness.get("missing", [])
    if not isinstance(missing, list):
        return []

    prefixes = _STEP_PATH_PREFIXES.get(state.step, ())
    out: list[dict] = []
    for raw in missing:
        if not isinstance(raw, dict):
            continue
        field_path = str(raw.get("field_path", ""))
        if not field_path:
            continue
        if not any(field_path.startswith(p) for p in prefixes):
            continue
        sev = str(raw.get("severity", "info"))
        if sev not in severities:
            continue
        # Attach skeleton if registered; do not mutate the source list
        # entry so completeness report consumers downstream see the
        # original shape.
        enriched = dict(raw)
        skeleton = _skeleton_for_gap(enriched, state)
        if skeleton is not None and enriched.get("suggested_skeleton") is None:
            enriched["suggested_skeleton"] = skeleton
        out.append(enriched)
    out.sort(key=lambda g: _gap_severity_rank(g.get("severity", "info")))
    return out


# ────────────────────────── severity normalization ──────────────────────────


def _normalize_severity(s) -> str:
    """Map a heterogeneous severity string to {fail, warn, info}.

    Audit artifacts mix `fail` / `FAIL` / `error` / `critical` etc.
    """
    s2 = str(s or "info").lower()
    if s2 in ("fail", "failed", "error", "critical", "blocker"):
        return "fail"
    if s2 in ("warn", "warning"):
        return "warn"
    return "info"


def _severity_rank(s) -> int:
    return {"fail": 0, "warn": 1, "info": 2}.get(_normalize_severity(s), 3)


def _gap_severity_rank(s) -> int:
    s2 = str(s or "info").lower()
    return {"critical": 0, "warning": 1, "info": 2}.get(s2, 3)


# ────────────────────────── state_sha ──────────────────────────


def _state_sha(state: CaseStateSnapshot) -> str:
    """SHA-256 of canonical state bytes. Stable across same inputs."""
    payload = {
        "case_id": state.case_id,
        "step": state.step,
        "manifest": _canonical(state.manifest),
        "artifacts": _canonical(state.artifacts),
        "completeness": _canonical(state.completeness),
        "focus_patch": state.focus_patch,
        "focus_region": state.focus_region,
        "focus_panel": state.focus_panel,
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _canonical(obj):
    """Recursively sort dict keys for stable serialization."""
    if isinstance(obj, dict):
        return {k: _canonical(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_canonical(x) for x in obj]
    return obj
