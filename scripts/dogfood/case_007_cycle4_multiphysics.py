"""DEC-V61-202-SUB-M30-CYCLE4 · horizontal multi-physics dogfood.

Stages 4 canonical regime shapes and walks Steps 1-5 via the GET
workbench_frame endpoint for each. The dogfood proves decide() +
dynamic frame degrade gracefully across regime shapes, not just
case_007 KCS VOF (cycles 1-3 baseline).

Regimes:
    1. RANS steady incompressible (flat plate, simpleFoam)
    2. LES (channel WALE, pisoFoam)
    3. Compressible (supersonic wedge, rhoCentralFoam)
    4. Multi-region CHT (chtMultiRegionFoam)

Per regime, for each step N ∈ {1..5}:
    - GET frame returns 200
    - rail_primary.kind ∈ {problem_fix, info_gap, step_default}
    - bottom_cards is a list
    - topbar_cta.kind is a valid enum
    - manifest_state_sha is a non-empty SHA hex string

If any regime triggers an unhandled artifact shape (KeyError / crash /
empty rail_primary), the dogfood FAILs and the regime trace is dumped.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable

import yaml
from fastapi.testclient import TestClient

# Codex R0 P3: manifest_state_sha is the optimistic-concurrency token
# for the PATCH flow. It MUST be a full SHA-256 hex digest (64 chars).
# Anything shorter / non-hex breaks the contract — guard regression.
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _stage_case(
    imported_root: Path,
    case_id: str,
    manifest: dict,
    artifacts: dict,
) -> Path:
    case_dir = imported_root / case_id
    case_dir.mkdir(exist_ok=True)
    (case_dir / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))
    art_dir = case_dir / "artifacts"
    art_dir.mkdir(exist_ok=True)
    for name, payload in artifacts.items():
        (art_dir / name).write_text(json.dumps(payload))
    return case_dir


# ── Regime 1: RANS steady incompressible (clean PASS baseline) ─────
# Codex R0 P2 fix: use the imported-user v2 schema
# (physics.solver, physics.turbulence_model, bc.patches.<name>) so
# the regime-specific completeness paths are actually exercised.
RANS_MANIFEST = {
    "case_id": "case_rans_flatplate_dogfood",
    "case_family": "rans_steady_incompressible",
    "solver_backend": "openfoam",
    "physics": {
        "solver": "simpleFoam",
        "turbulence_model": "kOmegaSST",
    },
    "bc": {
        "patches": {
            "inlet": {
                "patch_type": "fixedValue",
                "fields": {"U": [10.0, 0.0, 0.0]},
            },
            "outlet": {
                "patch_type": "zeroGradient",
                "fields": {"p": "zeroGradient"},
            },
            "wall": {"patch_type": "noSlip", "fields": {}},
        }
    },
}
RANS_ARTIFACTS = {
    "mesh_report.json": {
        "gate_status": "PASS",
        "stats": {"cells": 500_000},
        "quality_dimension": {"dimension_status": "PASS"},
    },
    "bc_audit.json": {
        "gate_status": "PASS",
        "patch_coverage_dimension": {
            "dimension_status": "PASS",
            "matched": [{"field": "U", "resolved_patch": "inlet"}],
        },
        "value_match_dimension": {
            "dimension_status": "PASS",
            "matched": [{"field": "U", "resolved_patch": "inlet"}],
        },
    },
}

# ── Regime 2: LES (sub-grid model gap intentional) ──────────────────
LES_MANIFEST = {
    "case_id": "case_les_channel_dogfood",
    "case_family": "les_transient_incompressible",
    "solver_backend": "openfoam",
    "physics": {
        "solver": "pisoFoam",
        "turbulence_model": "LES",
    },
    "bc": {
        "patches": {
            "inlet": {
                "patch_type": "turbulentInlet",
                "fields": {"U": [5.0, 0.0, 0.0]},
            },
            "outlet": {
                "patch_type": "zeroGradient",
                "fields": {"p": "zeroGradient"},
            },
            "topWall": {"patch_type": "noSlip", "fields": {}},
            "bottomWall": {"patch_type": "noSlip", "fields": {}},
        }
    },
}
LES_ARTIFACTS = {
    "mesh_report.json": {
        "gate_status": "PASS",
        "stats": {"cells": 2_000_000},
        "quality_dimension": {"dimension_status": "PASS"},
    },
    "bc_audit.json": {
        "gate_status": "WARN",
        "patch_coverage_dimension": {
            "dimension_status": "WARN",
            "gaps_by_field": {
                "U": ["inlet"],  # LES needs turbulent inlet generator config
            },
        },
    },
}

# ── Regime 3: Compressible (rhoCentralFoam shape) ───────────────────
COMP_MANIFEST = {
    "case_id": "case_comp_wedge_dogfood",
    "case_family": "compressible_inviscid",
    "solver_backend": "openfoam",
    "physics": {
        "solver": "rhoCentralFoam",
        "turbulence_model": "laminar",
    },
    "bc": {
        "patches": {
            "inlet": {
                "patch_type": "fixedValue",
                "fields": {
                    "U": [680.0, 0.0, 0.0],
                    "p": 101325.0,
                    "T": 288.15,
                },
            },
            "outlet": {
                "patch_type": "waveTransmissive",
                "fields": {},
            },
            "wedge_wall": {"patch_type": "slip", "fields": {}},
        }
    },
}
COMP_ARTIFACTS = {
    "mesh_report.json": {
        "gate_status": "PASS",
        "stats": {"cells": 800_000},
        "quality_dimension": {
            "dimension_status": "WARN",
            "metrics": {
                "max_non_orthogonality": {"actual": 68.5, "max_allowed": 65.0}
            },
        },
    },
    "bc_audit.json": {
        "gate_status": "FAIL",
        "type_match_dimension": {
            "dimension_status": "FAIL",
            "type_mismatches": [
                {
                    "field": "T",
                    "resolved_patch": "outlet",
                    "manifest_type": "fixedValue",
                    "realized_type": "zeroGradient",
                }
            ],
        },
    },
}

# ── Regime 4: Multi-region CHT (chtMultiRegionFoam shape) ───────────
CHT_MANIFEST = {
    "case_id": "case_cht_multiregion_dogfood",
    "case_family": "conjugate_heat_transfer",
    "solver_backend": "openfoam",
    "physics": {
        "solver": "chtMultiRegionFoam",
        "turbulence_model": "kEpsilon",
    },
    "bc": {
        # Real CHT manifests are per-region nested; flatten one level
        # for dogfood — completeness checks operate on the flat dict.
        "patches": {
            "fluid_inlet": {
                "patch_type": "fixedValue",
                "fields": {"U": [1.0, 0.0, 0.0]},
            },
            "fluid_outlet": {
                "patch_type": "zeroGradient",
                "fields": {"p": "zeroGradient"},
            },
            "solid_wall": {
                "patch_type": "fixedValue",
                "fields": {"T": 350.0},
            },
        }
    },
}
CHT_ARTIFACTS = {
    "mesh_report.json": {
        "gate_status": "PASS",
        "stats": {"cells": 1_500_000, "regions": {"fluid": 1_000_000, "solid": 500_000}},
        "quality_dimension": {"dimension_status": "PASS"},
    },
    "bc_audit.json": {
        "gate_status": "WARN",
        # Multi-region auditors may emit nested per-region or flat
        # findings; cycle 4 dogfood uses flat shape (the production
        # auditor flattens per-region findings into a single list).
        #
        # Codex R1 P2 fix: field_path must point at a v2-editable
        # path. Since the manifests now use v2 schema (bc.patches.*),
        # the finding's field_path must also live under bc.patches.*
        # so a CTA wired to navigate-to-field works on the actual
        # workbench surface.
        "findings": [
            {
                "severity": "warn",
                "title": "missing solid-fluid coupling BC",
                "message": "fluid-solid interface 'solid_interface' has no compressible::turbulentTemperatureCoupledBaffleMixed",
                "field_path": "bc.patches.solid_interface",
            }
        ],
    },
}


REGIMES = [
    ("RANS-flatplate", RANS_MANIFEST, RANS_ARTIFACTS),
    ("LES-channel", LES_MANIFEST, LES_ARTIFACTS),
    ("Compressible-wedge", COMP_MANIFEST, COMP_ARTIFACTS),
    ("CHT-multiregion", CHT_MANIFEST, CHT_ARTIFACTS),
]

# Accept enum values per WorkbenchFrame schema
_RAIL_KINDS = {"problem_fix", "info_gap", "step_default"}
_TOPBAR_KINDS = {"next_step", "re_audit", "submit_solve", "step_default"}


def _check_frame_shape(regime: str, step: int, frame: dict) -> list[tuple[str, bool]]:
    """Return list of (check_label, ok) tuples for one frame."""
    rp = frame.get("rail_primary") or {}
    tc = frame.get("topbar_cta") or {}
    bc = frame.get("bottom_cards")
    sha = frame.get("manifest_state_sha")

    return [
        (f"[{regime} step={step}] rail_primary.kind valid",
         rp.get("kind") in _RAIL_KINDS),
        (f"[{regime} step={step}] rail_primary.title non-empty",
         bool(str(rp.get("title") or "").strip())),
        (f"[{regime} step={step}] bottom_cards is list",
         isinstance(bc, list)),
        (f"[{regime} step={step}] topbar_cta.kind valid",
         tc.get("kind") in _TOPBAR_KINDS),
        (f"[{regime} step={step}] manifest_state_sha is full SHA-256 hex (64 chars)",
         isinstance(sha, str) and bool(_SHA256_HEX_RE.match(sha))),
    ]


# Codex R1 P1 fix: lock in the schema-alignment behavior the cycle 4
# DEC is meant to guarantee. Without these semantic assertions, the
# shape-coherence checks would still PASS if decide() regressed to the
# pre-v2 behavior of always surfacing "Fill: physics.solver" /
# "Fill: bc.patches" generic info_gaps for clean manifests.
#
# For each regime where the manifest is COMPLETE (RANS / LES — clean
# fixtures with all required imported-user fields), Steps 3 + 4 must
# NOT show those two specific generic gaps. They should be step_default.
#
# For regimes with audit-surfaced FAILs (Compressible Step 4 outlet T
# mismatch, CHT Step 4 missing coupling BC), rail.primary must be
# problem_fix — not the generic gap.

# (regime_name, step, expected_rail_kind, expected_title_substring,
#  forbidden_title_substring)
# `forbidden_title_substring` guards against regressions to the
# pre-Codex-R0 generic-gap surface.
_SEMANTIC_EXPECTATIONS = [
    # RANS — manifest clean AND audit artifacts all PASS. Step 3+4
    # must reach step_default, NOT fall back to generic Fill: gaps.
    ("RANS-flatplate", 3, "step_default", "物理已设", "Fill: physics.solver"),
    ("RANS-flatplate", 4, "step_default", "边界已设", "Fill: bc.patches"),
    # LES — manifest is clean (Step 3 step_default expected), but the
    # bc_audit.json artifact staged a WARN via patch_coverage gaps. If
    # decide() is later improved to surface that WARN as problem_fix
    # at Step 4, we want this dogfood to still PASS (the UX is
    # better, not worse). So Step 4 only asserts the negative guard:
    # rail must NOT show the generic "Fill: bc.patches" fallback.
    # exp_kind=None means "no kind requirement".
    # Codex R2 P2 fix · refined by R3 P3: exp_kind=("step_default",
    # "problem_fix") explicitly excludes info_gap. The LES manifest
    # has no missing required fields, so info_gap would be a real
    # regression (would disable the topbar CTA on a complete manifest).
    ("LES-channel", 3, "step_default", "物理已设", "Fill: physics.solver"),
    ("LES-channel", 4, ("step_default", "problem_fix"), None, "Fill: bc.patches"),
    # Regimes whose artifacts explicitly carry FAILs at Step 4 — rail
    # must surface the audit signal, not a generic gap.
    ("Compressible-wedge", 4, "problem_fix", None, "Fill: bc.patches"),
    ("CHT-multiregion", 4, "problem_fix", None, "Fill: bc.patches"),
]


def _check_semantic_expectations(
    regime_traces: dict,
) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    for regime, step, exp_kind, exp_title_sub, forbidden_sub in (
        _SEMANTIC_EXPECTATIONS
    ):
        trace = regime_traces.get(regime, {}).get(step)
        if trace is None:
            out.append(
                (f"[semantic {regime} step={step}] trace recorded", False)
            )
            continue
        actual_kind = trace["rail_kind"]
        actual_title = trace["rail_title"] or ""
        if exp_kind is not None:
            if isinstance(exp_kind, (tuple, list, set, frozenset)):
                ok = actual_kind in exp_kind
                label = (
                    f"[semantic {regime} step={step}] rail.kind in "
                    f"{sorted(exp_kind)} (got {actual_kind})"
                )
            else:
                ok = actual_kind == exp_kind
                label = (
                    f"[semantic {regime} step={step}] rail.kind == "
                    f"{exp_kind} (got {actual_kind})"
                )
            out.append((label, ok))
        if exp_title_sub:
            out.append(
                (
                    f"[semantic {regime} step={step}] rail.title contains "
                    f"{exp_title_sub!r} (got {actual_title!r})",
                    exp_title_sub in actual_title,
                )
            )
        if forbidden_sub:
            out.append(
                (
                    f"[semantic {regime} step={step}] rail.title does NOT "
                    f"contain {forbidden_sub!r} (regression guard) "
                    f"(got {actual_title!r})",
                    forbidden_sub not in actual_title,
                )
            )
    return out


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="cycle4_multiphysics_"))
    imported_root = tmpdir / "imported"
    imported_root.mkdir()

    for _regime, manifest, artifacts in REGIMES:
        _stage_case(
            imported_root,
            manifest["case_id"],
            manifest,
            artifacts,
        )

    import ui.backend.routes.workbench_frame as wf
    import ui.backend.services.case_completeness.analyzer as cc_analyzer
    import ui.backend.services.manifest_patch as mp

    wf.IMPORTED_DIR = imported_root
    cc_analyzer.IMPORTED_DIR = imported_root
    mp.IMPORTED_DIR = imported_root

    from ui.backend.main import app
    client = TestClient(app)

    all_checks: list[tuple[str, bool]] = []
    regime_traces: dict[str, dict[int, dict]] = {}

    for regime_name, manifest, _artifacts in REGIMES:
        case_id = manifest["case_id"]
        regime_traces[regime_name] = {}
        for step in range(1, 6):
            r = client.get(
                f"/api/cases/{case_id}/workbench_frame?step={step}"
            )
            try:
                payload = r.json()
            except Exception:
                payload = {"_raw": r.text}

            # Record per-step trace.
            regime_traces[regime_name][step] = {
                "status_code": r.status_code,
                "rail_kind": (payload.get("rail_primary") or {}).get("kind"),
                "rail_title": (payload.get("rail_primary") or {}).get("title"),
                "topbar_kind": (payload.get("topbar_cta") or {}).get("kind"),
                "card_count": len(payload.get("bottom_cards") or []),
            }

            all_checks.append(
                (f"[{regime_name} step={step}] HTTP 200",
                 r.status_code == 200)
            )
            if r.status_code == 200:
                all_checks.extend(_check_frame_shape(regime_name, step, payload))
            else:
                # Server error → dump for triage.
                print(f"[{regime_name} step={step}] status={r.status_code}")
                print(f"  body: {r.text[:400]}")

    # Codex R1 P1: append semantic regression guards after all traces
    # have been collected (semantic checks depend on per-regime traces).
    all_checks.extend(_check_semantic_expectations(regime_traces))

    print("\n=== Multi-physics dogfood verification ===\n")

    # Compact per-regime trace.
    for regime_name in regime_traces:
        print(f"  {regime_name}:")
        for step, trace in regime_traces[regime_name].items():
            print(
                f"    step={step} "
                f"http={trace['status_code']} "
                f"rail.kind={trace['rail_kind']} "
                f"rail.title={trace['rail_title']!r} "
                f"topbar.kind={trace['topbar_kind']} "
                f"cards={trace['card_count']}"
            )
        print()

    fail_count = sum(1 for _, ok in all_checks if not ok)
    pass_count = len(all_checks) - fail_count

    print(f"Total checks: {len(all_checks)} · PASS: {pass_count} · FAIL: {fail_count}")

    if fail_count:
        print("\nFailing checks:")
        for label, ok in all_checks:
            if not ok:
                print(f"  [FAIL] {label}")

    verdict = "PASS" if fail_count == 0 else "FAIL"
    print(f"\nVerdict: {verdict}")
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
