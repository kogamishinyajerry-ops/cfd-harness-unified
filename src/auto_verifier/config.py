"""Configuration and frozen thresholds for AutoVerifier."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = REPO_ROOT / "knowledge"
REPORTS_ROOT = REPO_ROOT / "reports"

# Q-2 Path A (DEC-V61-011): `fully_developed_turbulent_pipe_flow` renamed to
# `duct_flow` to match the actual rectangular-duct geometry the adapter emits.
# Old task name mappings retained (to `duct_flow` canonical) for backwards
# compat with any cached TaskSpec / test fixture still using pre-rename strings.
ANCHOR_CASE_IDS = frozenset(
    {
        "lid_driven_cavity_benchmark",
        "backward_facing_step_steady",
        "cylinder_crossflow",
        "turbulent_flat_plate",
        "duct_flow",
        "rayleigh_benard_convection",
        "differential_heated_cavity",
        "naca0012_airfoil",
        "axisymmetric_impinging_jet",
        "fully_developed_plane_channel_flow",
    }
)

TASK_NAME_TO_CASE_ID = {
    "Lid-Driven Cavity": "lid_driven_cavity_benchmark",
    "Backward-Facing Step": "backward_facing_step_steady",
    "Circular Cylinder Wake": "cylinder_crossflow",
    "Turbulent Flat Plate (Zero Pressure Gradient)": "turbulent_flat_plate",
    # Q-2 Path A rename: new canonical name + legacy aliases
    "Fully Developed Turbulent Square-Duct Flow": "duct_flow",
    "Fully Developed Turbulent Pipe Flow": "duct_flow",          # pre-rename legacy
    "Rayleigh-Benard Convection (Ra=10^6)": "rayleigh_benard_convection",
    "Rayleigh-Bénard Convection (Ra=10^6)": "rayleigh_benard_convection",
    "Differential Heated Cavity (Natural Convection)": "differential_heated_cavity",
    "Differential Heated Cavity (Natural Convection, Ra=10^6 benchmark)": "differential_heated_cavity",
    "NACA 0012 Airfoil External Flow": "naca0012_airfoil",
    "Axisymmetric Impinging Jet (Re=10000)": "axisymmetric_impinging_jet",
    "Fully Developed Plane Channel Flow (DNS)": "fully_developed_plane_channel_flow",
}

CASE_ID_TO_GOLD_FILE = {
    "lid_driven_cavity_benchmark": KNOWLEDGE_ROOT / "gold_standards" / "lid_driven_cavity_benchmark.yaml",
    "backward_facing_step_steady": KNOWLEDGE_ROOT / "gold_standards" / "backward_facing_step_steady.yaml",
    "cylinder_crossflow": KNOWLEDGE_ROOT / "gold_standards" / "cylinder_crossflow.yaml",
    "turbulent_flat_plate": KNOWLEDGE_ROOT / "gold_standards" / "turbulent_flat_plate.yaml",
    "duct_flow": KNOWLEDGE_ROOT / "gold_standards" / "duct_flow.yaml",
    "rayleigh_benard_convection": KNOWLEDGE_ROOT / "gold_standards" / "rayleigh_benard_convection.yaml",
    "differential_heated_cavity": KNOWLEDGE_ROOT / "gold_standards" / "differential_heated_cavity.yaml",
    "naca0012_airfoil": KNOWLEDGE_ROOT / "gold_standards" / "naca0012_airfoil.yaml",
    "axisymmetric_impinging_jet": KNOWLEDGE_ROOT / "gold_standards" / "axisymmetric_impinging_jet.yaml",
    "fully_developed_plane_channel_flow": KNOWLEDGE_ROOT / "gold_standards" / "fully_developed_plane_channel_flow.yaml",
}

CASE_ID_TO_SOLVER = {
    "lid_driven_cavity_benchmark": "icoFoam",
    "backward_facing_step_steady": "simpleFoam",
    "cylinder_crossflow": "pimpleFoam",
    "turbulent_flat_plate": "simpleFoam",
    "duct_flow": "simpleFoam",
    "rayleigh_benard_convection": "buoyantFoam",
    "differential_heated_cavity": "buoyantFoam",
    "naca0012_airfoil": "simpleFoam",
    "axisymmetric_impinging_jet": "simpleFoam",
    "fully_developed_plane_channel_flow": "icoFoam",
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
