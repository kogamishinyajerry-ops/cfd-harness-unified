roadmap_milestone: M9.charter-pivot
business_goal: Adopt an ANSYS-Fluent-class engineer-in-the-loop interaction model where the workbench has a 3D viewport at its center, five independent step panels for geometry / mesh / setup / solve / results, and an opt-in AI co-pilot button per step that never auto-advances.
affected_subsystems:
  - product interaction model
  - frontend shell architecture
  - new viewport renderer
  - new backend rendering endpoints
  - roadmap milestone definitions
rationale: The current agentic-wizard interaction model is incompatible with how working CFD engineers operate and with what a recruited Path A stranger expects to see. The pivot preserves all backend services and the two-track invariant while replacing the discrete-route wizard with a CAE workbench shell. The decision introduces four new milestones in a hard ordering before the redefined M7 and M8.
