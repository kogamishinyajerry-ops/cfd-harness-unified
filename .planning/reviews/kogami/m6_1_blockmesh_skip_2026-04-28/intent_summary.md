roadmap_milestone: M6.1
business_goal: Allow the executor to skip blockMesh when a case already has a polyMesh on disk, so imported user geometry meshed by an upstream stage can flow into the solver without re-meshing.
affected_subsystems:
  - TaskSpec dataclass
  - FoamAgentExecutor execute path
  - blockMesh invocation guard
  - polyMesh existence check
rationale: A structural boolean flag on TaskSpec plus a guard at the blockMesh call site is the minimum patch needed to make the executor aware of pre-existing polyMesh artifacts. Default-False keeps every existing call site backward-compatible, and a defensive filesystem check fails fast when the flag is set without a polyMesh on disk.
