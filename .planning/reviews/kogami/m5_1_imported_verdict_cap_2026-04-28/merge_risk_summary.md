risk_class: medium
reversibility: easy
blast_radius: bounded
rationale: The change touches one trust-core file with a small surface — one new pure function plus two new string constants — and one wiring call in the task runner. Worst-wins monotone composition with the existing executor-mode ceiling guarantees the cap only lowers a PASS verdict to WARN, never raises severity. No production caller currently sets the source-origin signal, so the new path is reachable from whitelist runs only via test fixtures until later milestones wire it. Reversal is a single revert. Blast radius is bounded to the verdict envelope.
