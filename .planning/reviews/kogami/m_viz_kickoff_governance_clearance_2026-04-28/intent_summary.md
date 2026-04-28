roadmap_milestone: M9.viz
business_goal: Stand up a 3D viewport that renders the imported STL geometry of a workbench case with pan rotate and zoom camera controls, giving the Pivot Charter Addendum 3 product narrative a real on-screen surface for downstream Fluent-style panels.
affected_subsystems:
  - frontend visualization module
  - STL render endpoint
  - ImportPage preview panel
  - line-A isolation contract
  - Path A engagement timeline
rationale: First implementation milestone under Pivot Charter Addendum 3 hard ordering. Library choice vtk.js carries CAE primitives that downstream M-VIZ.results consumes. Line-A line-B contract extension is a prerequisite landing in a separate commit before any implementation. Tier B capabilities including mesh contour and streamline are deferred to M-VIZ.mesh and M-VIZ.results follow ups.
