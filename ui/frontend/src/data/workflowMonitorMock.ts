// Workflow Monitor · design-preview MOCK fixture (DEC-V61-226)
// ------------------------------------------------------------
// HONEST DISCLAIMER: this is hand-authored mock data used ONLY to validate the
// WorkflowMonitor interaction/layout before the page is wired to the real
// backend (/api/runs/<id> + solver_stream SSE). It is NOT a real CFD run. The
// page renders `run.isMock === true` as an indelible banner so it can never be
// mistaken for a solve. When the real WorkflowRunner lands, this fixture is
// swapped for a live payload of the SAME WorkflowRun shape.
//
// Scenario: a pure-aerodynamic transport-wing external run (RANS, incompressible
// envelope), captured mid-flight at the solver stage. It deliberately shows an
// HONEST mesh-quality HAZARD (maxSkewness 0.91 at the leading edge) carried
// forward as a caveat, and the report stage BLOCKED pending convergence
// evidence — the project's "evidence-insufficient → BLOCK" principle made
// visible, not an all-green happy path.

import type { WorkflowRun } from "@/types/workflow";

export const WORKFLOW_MONITOR_MOCK: WorkflowRun = {
  runId: "mock-wing-aero-0001",
  caseName: "Transport wing · cruise AoA sweep (RANS, external)",
  isMock: true,
  currentStage: "solver_run",
  edges: [
    { from: "geometry_intake", to: "geometry_validation" },
    { from: "geometry_validation", to: "mesh_generation" },
    { from: "mesh_generation", to: "mesh_quality_check" },
    { from: "mesh_quality_check", to: "solver_run" },
    { from: "solver_run", to: "result_report" },
  ],
  stages: [
    {
      key: "geometry_intake",
      title: "Geometry Intake",
      state: "passed",
      progress: 100,
      currentObject: "wing_clean.step → 1 solid, watertight",
      metrics: [
        { label: "Solids", value: 1 },
        { label: "Bounding box", value: "34.1 × 11.8 × 2.6", unit: "m" },
        { label: "Watertight", value: "yes", verdict: "pass" },
      ],
      warnings: [],
      errors: [],
      artifacts: [
        { name: "wing_clean.step", kind: "geometry" },
        { name: "intake_manifest.json", kind: "table" },
      ],
      advisor:
        "Imported a single watertight solid. Units resolved as metres from the STEP header; no scaling applied.",
      startedAt: "T+00:00",
      durationLabel: "4s",
    },
    {
      key: "geometry_validation",
      title: "Geometry Validation",
      state: "passed",
      progress: 100,
      currentObject: "trailing-edge thickness check",
      metrics: [
        { label: "Min TE thickness", value: 1.9, unit: "mm", verdict: "pass" },
        { label: "Degenerate faces", value: 0, verdict: "pass" },
        { label: "Sharp edges flagged", value: 12, verdict: "info" },
      ],
      warnings: [],
      errors: [],
      artifacts: [{ name: "validation_report.json", kind: "table" }],
      advisor:
        "Trailing edge is finite-thickness (1.9 mm) — safe for a body-fitted mesh. 12 sharp edges noted for feature capture in meshing.",
      startedAt: "T+00:04",
      durationLabel: "3s",
    },
    {
      key: "mesh_generation",
      title: "Mesh Generation",
      state: "passed",
      progress: 100,
      currentObject: "snappyHexMesh · prism layers on wing surface",
      metrics: [
        { label: "Cells", value: "1.24M" },
        { label: "Prism layers", value: 8 },
        { label: "y+ (target)", value: "~45", verdict: "info" },
      ],
      warnings: [],
      errors: [],
      artifacts: [
        { name: "polyMesh/", kind: "mesh" },
        { name: "log.snappyHexMesh", kind: "log" },
      ],
      advisor:
        "Generated 1.24M cells with an 8-layer prism stack. Target y+ ~45 sits in the wall-function-valid band for kOmegaSST.",
      startedAt: "T+00:07",
      durationLabel: "2m 41s",
    },
    {
      key: "mesh_quality_check",
      title: "Mesh Quality Check",
      state: "passed",
      progress: 100,
      currentObject: "leading-edge cells / suction peak region",
      metrics: [
        { label: "Cells", value: "1.24M" },
        { label: "Bad cells", value: 3821, verdict: "hazard" },
        { label: "Max skewness", value: 0.91, unit: "", verdict: "hazard" },
        { label: "Max non-ortho", value: 64, unit: "°", verdict: "info" },
      ],
      warnings: [
        "Local skewness 0.91 at the leading edge (3821 cells > 0.85) — within checkMesh tolerance but flagged for solver robustness.",
      ],
      errors: [],
      artifacts: [
        { name: "log.checkMesh", kind: "log" },
        { name: "mesh_quality.json", kind: "table" },
      ],
      nextAction:
        "Local refinement at the leading edge + lower the layer growth-rate to 1.15 if the solver shows pressure wiggles near the suction peak.",
      advisor:
        "checkMesh PASSES (no errors), but 3821 leading-edge cells exceed skewness 0.85. Carried forward as a HAZARD: the solve may proceed, but convergence near the suction peak is the thing to watch.",
      startedAt: "T+02:48",
      durationLabel: "11s",
    },
    {
      key: "solver_run",
      title: "Solver Run",
      state: "running",
      progress: 62,
      currentObject: "simpleFoam · iteration 1240 / ~2000",
      metrics: [
        { label: "Iteration", value: "1240 / ~2000" },
        { label: "Ux residual", value: "3.1e-4", verdict: "info" },
        { label: "p residual", value: "8.7e-4", verdict: "hazard" },
        { label: "Cl (running)", value: 0.481, verdict: "info" },
        { label: "Cd (running)", value: 0.0193, verdict: "info" },
      ],
      warnings: [
        "Pressure residual plateauing near 9e-4 — consistent with the leading-edge skewness HAZARD from mesh QC.",
      ],
      errors: [],
      artifacts: [
        { name: "log.simpleFoam", kind: "log" },
        { name: "postProcessing/forceCoeffs", kind: "field" },
      ],
      nextAction:
        "Let it run to the residual floor; if p stalls above 1e-3, apply the mesh-QC leading-edge refinement and restart from latestTime.",
      advisor:
        "Solving. Forces are tracking toward Cl≈0.48 / Cd≈0.019. The pressure residual plateau is the predicted consequence of the LE skewness — not yet blocking, but it gates the report stage.",
      startedAt: "T+02:59",
      durationLabel: "running…",
    },
    {
      key: "result_report",
      title: "Result Report",
      state: "blocked",
      progress: 0,
      currentObject: "convergence evidence gate",
      metrics: [
        { label: "Convergence", value: "unproven", verdict: "fail" },
        { label: "Force settling", value: "pending", verdict: "info" },
      ],
      warnings: [],
      errors: [],
      artifacts: [],
      nextAction:
        "Report is HELD until the solver reaches the residual floor AND force coefficients settle over the last 200 iterations. No polar is published on an unconverged solve.",
      advisor:
        "BLOCKED by design: the report stage refuses to emit Cl/Cd until convergence is demonstrated. Evidence-insufficient → BLOCK, never a number dressed up as a result.",
    },
  ],
  advisorLog: [
    { ts: "T+00:00", stage: "geometry_intake", level: "info", message: "Intake: 1 watertight solid, metres." },
    { ts: "T+00:04", stage: "geometry_validation", level: "info", message: "Finite TE (1.9 mm); 12 sharp edges queued for feature capture." },
    { ts: "T+00:07", stage: "mesh_generation", level: "info", message: "1.24M cells, 8 prism layers, y+~45." },
    { ts: "T+02:48", stage: "mesh_quality_check", level: "warn", message: "HAZARD: 3821 LE cells skewness>0.85 (max 0.91). checkMesh passes; carried forward." },
    { ts: "T+02:59", stage: "solver_run", level: "info", message: "simpleFoam started; forces tracking Cl≈0.48." },
    { ts: "T+05:30", stage: "solver_run", level: "warn", message: "p residual plateauing ~9e-4 — predicted from LE skewness." },
    { ts: "T+05:31", stage: "result_report", level: "block", message: "Report BLOCKED: convergence unproven; no polar published on an unconverged solve." },
  ],
  timeline: [
    { stage: "geometry_intake", label: "Intake", state: "passed", at: "T+00:00" },
    { stage: "geometry_validation", label: "Validate", state: "passed", at: "T+00:04" },
    { stage: "mesh_generation", label: "Mesh", state: "passed", at: "T+00:07" },
    { stage: "mesh_quality_check", label: "Mesh QC", state: "passed", at: "T+02:48" },
    { stage: "solver_run", label: "Solve", state: "running", at: "T+02:59" },
    { stage: "result_report", label: "Report", state: "blocked", at: "T+05:31" },
  ],
};
