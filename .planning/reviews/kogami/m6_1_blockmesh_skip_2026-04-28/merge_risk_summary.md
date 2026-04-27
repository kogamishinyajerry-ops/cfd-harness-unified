risk_class: medium
reversibility: easy
blast_radius: bounded
rationale: The change touches one trust-core file with a small surface — one new dataclass field defaulted to False and one guard around the blockMesh call. Default-False preserves every existing call site. No production caller sets the flag in this milestone, so the new code path is reachable only from explicit test fixtures until a later milestone wires it in. Reversal is a single revert commit. Blast radius is bounded to the executor mesh-generation step; the solver step downstream and the artifact pipeline upstream are untouched.
