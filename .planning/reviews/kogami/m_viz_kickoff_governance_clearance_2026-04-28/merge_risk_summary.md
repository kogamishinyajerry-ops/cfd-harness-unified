risk_class: medium
reversibility: medium
blast_radius: bounded
rationale: First implementation milestone under Pivot Charter Addendum 3. Adds new frontend dependency vtk.js with roughly two megabyte bundle delta and known WebGL lifecycle risks. Adds new line-A paths under visualization and rendering services. ImportPage integration touches a path inside workbench freeze advisory scope and requires BREAK_FREEZE escape referencing Addendum 3. Reversibility is medium because library choice locks subsequent milestones via shared API conventions even though revert is mechanically possible. Blast radius is bounded to frontend shell plus one tiny backend STL serve endpoint. Backend services and trust core boundary preserved unchanged.
