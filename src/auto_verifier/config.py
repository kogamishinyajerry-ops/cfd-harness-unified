"""Configuration and frozen thresholds for AutoVerifier."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = REPO_ROOT / "knowledge"
REPORTS_ROOT = REPO_ROOT / "reports"

ANCHOR_CASE_IDS = frozenset(
    {
        "lid_driven_cavity_benchmark",
        "backward_facing_step_steady",
        "cylinder_crossflow",
    }
)

TASK_NAME_TO_CASE_ID = {
    "Lid-Driven Cavity": "lid_driven_cavity_benchmark",
    "Backward-Facing Step": "backward_facing_step_steady",
    "Circular Cylinder Wake": "cylinder_crossflow",
}

CASE_ID_TO_GOLD_FILE = {
    "lid_driven_cavity_benchmark": KNOWLEDGE_ROOT / "gold_standards" / "lid_driven_cavity_benchmark.yaml",
    "backward_facing_step_steady": KNOWLEDGE_ROOT / "gold_standards" / "backward_facing_step_steady.yaml",
    "cylinder_crossflow": KNOWLEDGE_ROOT / "gold_standards" / "cylinder_crossflow.yaml",
}

CASE_ID_TO_SOLVER = {
    "lid_driven_cavity_benchmark": "icoFoam",
    "backward_facing_step_steady": "simpleFoam",
    "cylinder_crossflow": "pimpleFoam",
}

DEFAULT_TIMESTAMP = "1970-01-01T00:00:00Z"
ZERO_REFERENCE_EPSILON = 1e-12

# Threshold registry is frozen for Phase 8a per Opus condition C5.
THRESHOLDS = {
    "TH-1": 1.0,      # residual ratio <= 1.0 => converged
    "TH-2": 1e-5,     # default target residual
    "TH-3": 0.4,      # oscillation ratio > 0.4
    "TH-4": 20,       # residual window size
    "TH-5": 0.05,     # default relative tolerance
    "TH-6": 1e-6,     # zero-reference absolute tolerance
    "TH-7-pass": 0.01,
    "TH-7-warn": 0.05,
    "TH-8": 0.70,     # pass-with-deviations cutoff
    "TH-9": 10.0,     # divergence if final > 10 x initial
}

PROFILE_VALUE_KEYS = (
    "value",
    "u",
    "v",
    "w",
    "Nu",
    "Cp",
    "Cf",
    "u_Ubulk",
    "u_Uinf",
    "u_plus",
)

