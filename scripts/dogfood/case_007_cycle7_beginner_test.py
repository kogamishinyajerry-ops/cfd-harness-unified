"""DEC-V61-202-SUB-M30-CYCLE7 · junior-engineer beginner-test litmus surrogate.

Simulates a programmatic engineer who follows whatever the rail says at
each step, applies the suggested fix, and advances when the topbar CTA
is enabled. Measures whether the dynamic workbench drives monotonic
forward progress from a sparse starting state to a solveable case.

Acceptance:
    - ≤20 decide() calls total (junior 30-min budget proxy at 1.5 min/action)
    - Each step exited at most once (no back-edges)
    - rail severity monotonically decreases within each step
    - Provenance log captures the journey faithfully
    - Replay reader shows step arc as 1→2→3→4→5

This is a *programmatic* surrogate; real-engineer eval is M3.1 scope.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml
from fastapi.testclient import TestClient


CASE_ID = "case_007_cycle7_beginner"
MAX_DECIDE_CALLS = 20  # 30 min / 1.5 min per UI action

# Codex R0 P2 #1 fix: ranks must cover both severity vocabularies emitted
# by decide() — `_rail_from_problem` uses fail/warn/info,
# `_rail_from_gap` uses critical/warning/info. Without `critical` and
# `warning` in the map, every gap-driven frame falls to rank 0 and the
# monotonicity check is vacuous.
SEVERITY_RANK = {
    "fail": 3,
    "critical": 3,
    "warn": 2,
    "warning": 2,
    "info": 1,
    None: 0,
}

# Severity lives inside RailPrimary.provenance traces like
# `step=4 · problem_fix · severity=fail`. Match cycle 6's log-writer
# extraction so test + log agree on what severity each frame surfaced.
_SEVERITY_TOKEN_RE = re.compile(r"\bseverity=([A-Za-z_]+)\b")


def _rail_severity(provenance) -> str | None:
    """Best-effort parse severity token from a list of provenance lines.
    Returns None when no token is present (step_default rails)."""
    if not provenance:
        return None
    for line in provenance:
        match = _SEVERITY_TOKEN_RE.search(str(line))
        if match:
            return match.group(1)
    return None


# Sparse starting state: just enough for the case to register.
STARTING_MANIFEST = {
    "case_id": CASE_ID,
    "case_family": "ship_vof",
    "solver_backend": "openfoam",
}


def _synthesize_value(field_path: str):
    """When the rail asks for a field but suggests no default, an engineer
    types something. Our synthesized values mirror the kinds of writes a
    junior engineer would commit on first pass — not domain-correct
    necessarily, but plausible enough to satisfy schema-level completeness.
    """
    if "patch_type" in field_path:
        return "fixedValue"
    if field_path.endswith(".solver"):
        return "interFoam"
    if field_path.endswith(".turbulence_model"):
        return "kOmegaSST"
    if "fields" in field_path:
        return {}
    if field_path == "bc.patches" or field_path.endswith(".patches"):
        # Canonical ship-VOF 3-patch skeleton. Real UI would have a
        # "add inlet / outlet / wall" form helper; this stub mirrors
        # the same engineer affordance.
        return {
            "inlet": {
                "patch_type": "fixedValue",
                "fields": {"U": [1.0, 0.0, 0.0]},
            },
            "outlet": {
                "patch_type": "zeroGradient",
                "fields": {"p": "zeroGradient"},
            },
            "wall": {"patch_type": "noSlip", "fields": {}},
        }
    if "y_plus" in field_path:
        return 30.0
    if "phases" in field_path:
        return ["water", "air"]
    # Generic fallback — empty dict acts as "stub", schema-permissive.
    return {}


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="cycle7_beginner_"))
    imported_root = tmpdir / "imported"
    drafts_root = tmpdir / "user_drafts"
    audit_root = tmpdir / "audit_v2"
    for p in (imported_root, drafts_root, audit_root):
        p.mkdir(parents=True)

    case_dir = imported_root / CASE_ID
    case_dir.mkdir()
    (case_dir / "case_manifest.yaml").write_text(yaml.safe_dump(STARTING_MANIFEST))

    os.environ.pop("WORKBENCH_PROVENANCE_DISABLED", None)

    import ui.backend.routes.workbench_frame as wf
    import ui.backend.services.case_completeness.analyzer as cc_analyzer
    import ui.backend.services.manifest_patch as mp
    import ui.backend.services.workbench_decide_provenance as wp

    wf.IMPORTED_DIR = imported_root
    cc_analyzer.IMPORTED_DIR = imported_root
    mp.IMPORTED_DIR = imported_root
    wp.AUDIT_V2_DIR = audit_root

    from ui.backend.main import app
    client = TestClient(app)

    # Per-step trace: list of (call_idx, severity_rank, rail_kind, field_path).
    step_traces: dict[int, list[tuple[int, int, str, str | None]]] = {
        1: [], 2: [], 3: [], 4: [], 5: [],
    }
    steps_visited_order: list[int] = []
    # Codex R0 P2 #2 fix: capture every (from, to) backend-driven step
    # transition so the dogfood validates the topbar.target_step
    # contract instead of manufacturing the arc client-side.
    step_transitions: list[tuple[int, int]] = []
    decide_calls = 0
    current_step = 1
    last_field_seen_per_step: dict[int, str | None] = {}

    def fetch_frame(step: int):
        nonlocal decide_calls
        decide_calls += 1
        r = client.get(f"/api/cases/{CASE_ID}/workbench_frame?step={step}")
        assert r.status_code == 200, f"GET frame step={step}: {r.status_code} / {r.text[:200]}"
        return r.json()

    def patch_field(field_path: str, value, expected_sha: str) -> bool:
        r = client.patch(
            f"/api/cases/{CASE_ID}/manifest",
            json={
                "field_path": field_path,
                "value": value,
                "op": "set",
                "expected_state_sha": expected_sha,
            },
        )
        return r.status_code == 200 and r.json().get("success", False)

    # ── The journey ────────────────────────────────────────────────────
    while current_step <= 5 and decide_calls < MAX_DECIDE_CALLS:
        if current_step not in steps_visited_order:
            steps_visited_order.append(current_step)
        frame = fetch_frame(current_step)
        rail = frame["rail_primary"]
        topbar = frame["topbar_cta"]
        # Codex R0 P2 #1 fix: parse severity from rail.provenance (where
        # decide() actually encodes it), not from rail.severity (which
        # does not exist on the wire schema).
        sev = _rail_severity(rail.get("provenance"))
        sev_rank = SEVERITY_RANK.get(sev, 0)
        step_traces[current_step].append(
            (decide_calls, sev_rank, rail["kind"], rail.get("field_path"))
        )
        print(
            f"  [call {decide_calls}] step={current_step} kind={rail['kind']:<12} "
            f"sev={sev} field={rail.get('field_path')} "
            f"topbar.kind={topbar['kind']} topbar.enabled={topbar.get('enabled')} "
            f"target_step={topbar.get('target_step')}"
        )

        if rail["kind"] == "step_default" and topbar.get("enabled"):
            # Engineer clicks next_step / submit_solve.
            if topbar["kind"] == "submit_solve" or current_step == 5:
                break
            # Codex R0 P2 #2 fix: trust the backend's target_step rather
            # than incrementing manually. If decide() ever returns a
            # wrong target (back-edge, skip, None on next_step), this
            # harness must surface that — record the transition and
            # let the forward-only acceptance check catch any regression.
            target = topbar.get("target_step")
            if topbar["kind"] == "next_step" and isinstance(target, int):
                step_transitions.append((current_step, target))
                current_step = target
            else:
                # Malformed next_step — record an obviously-invalid
                # transition so the forward-only check fails loudly.
                step_transitions.append((current_step, -1))
                break
            continue

        # Rail says "fix this" or "fill this" — apply suggested or
        # synthesize.
        field_path = rail.get("field_path")
        if not field_path:
            # No field to act on — try to advance anyway if enabled, else
            # give up to avoid an infinite spin.
            if topbar.get("enabled") and current_step < 5:
                current_step += 1
                continue
            break

        # Avoid spinning on the same field twice in a row at one step.
        if last_field_seen_per_step.get(current_step) == field_path:
            # The fix didn't move the rail; engineer would escalate. We
            # break here so the test surfaces the stuck-state honestly.
            break
        last_field_seen_per_step[current_step] = field_path

        suggested = rail.get("suggested_default")
        value = suggested if suggested is not None else _synthesize_value(field_path)
        ok = patch_field(field_path, value, frame["manifest_state_sha"])
        if not ok:
            # Even a stub-write was rejected by validation — engineer
            # gives up.
            break

    # ── Checks ────────────────────────────────────────────────────────
    print("\n=== Cycle 7 junior-engineer beginner test ===\n")
    print(f"Total decide() calls: {decide_calls}")
    print(f"Steps visited: {steps_visited_order}")
    print(f"Step transitions (backend-driven, from→to): {step_transitions}")
    for s in (1, 2, 3, 4, 5):
        if step_traces[s]:
            print(f"  step {s}: {len(step_traces[s])} frame(s), severities {[t[1] for t in step_traces[s]]}")
    print()

    log_path = audit_root / CASE_ID / "decisions.jsonl"
    log_lines = []
    if log_path.exists():
        for raw in log_path.read_text().splitlines():
            if raw.strip():
                log_lines.append(json.loads(raw))

    # Severity monotonicity per step: within a step the severity_rank
    # should never INCREASE between consecutive frames (engineer keeps
    # making things less broken, not more).
    severity_monotonic = True
    for s, trace in step_traces.items():
        ranks = [t[1] for t in trace]
        for i in range(1, len(ranks)):
            if ranks[i] > ranks[i - 1]:
                severity_monotonic = False
                break
        if not severity_monotonic:
            break

    # Step arc forward-only (no back-edges).
    forward_only = steps_visited_order == sorted(steps_visited_order) and \
        len(steps_visited_order) == len(set(steps_visited_order))

    # Codex R0 P2 #2 fix: every backend-driven step transition must be
    # strictly forward (to > from) and one-step (to == from + 1 — the
    # backend should not skip steps or back-edge). If decide() ever
    # returns a malformed target_step, this fails loudly.
    transitions_well_formed = all(
        (frm > 0 and to > frm and to <= 5 and to == frm + 1)
        for frm, to in step_transitions
    )

    checks = [
        (f"≤{MAX_DECIDE_CALLS} decide() calls (junior 30-min budget)",
         decide_calls <= MAX_DECIDE_CALLS),
        ("Forward-only step arc (no back-edges, no repeats)",
         forward_only),
        ("Backend topbar.target_step is well-formed (frm+1, ≤5, never -1)",
         transitions_well_formed and len(step_transitions) >= 1),
        ("Reached step 5 (proves engine drives all the way to solveable)",
         max(steps_visited_order) >= 5),
        ("Rail severity monotonically non-increasing within each step",
         severity_monotonic),
        ("Provenance log exists with one line per decide() call",
         len(log_lines) == decide_calls),
        ("Log lines record the step the agent was on (1..5)",
         all(1 <= line["step"] <= 5 for line in log_lines)),
    ]

    all_pass = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {label}")

    print()
    print(f"Verdict: {'PASS' if all_pass else 'FAIL'}")

    if all_pass:
        shutil.rmtree(tmpdir, ignore_errors=True)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
