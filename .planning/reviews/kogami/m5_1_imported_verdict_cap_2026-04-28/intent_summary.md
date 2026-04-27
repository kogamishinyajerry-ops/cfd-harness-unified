roadmap_milestone: M5.1
business_goal: Cap the trust-gate verdict on workbench imported user cases so a run on a geometry the harness has no literature ground truth for cannot reach a literature-validated PASS verdict.
affected_subsystems:
  - TrustGate ceiling routing
  - task runner verdict pipeline
  - imported case verdict envelope
rationale: Workbench imported cases have no whitelist gold standard to validate against, so the trust gate must mark their verdict with a disclaimer note. The smallest viable change reuses the existing PASS-to-WARN ceiling primitive with a new note string and a structural string tag derived from the existing imported-case flag, preserving the trust-core boundary.
