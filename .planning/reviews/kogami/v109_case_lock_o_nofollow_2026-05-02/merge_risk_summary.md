risk_class: high
reversibility: easy
blast_radius: cross-system
rationale: The change touches the shared case_lock primitive every case-mutating route depends on. The new failure mode is symlink_escape raised on a planted or swapped case-directory symlink, which is the same error class downstream callers already translate to a structured 422 response. Reversal is a single revert of one module plus tests. Blast radius is cross-system because the patch classification store, the setup_bc dispatcher, and the raw dictionary editor route all acquire the lock; any regression would surface across all three surfaces simultaneously and trip the smoke baseline plus broader backend suite fast.
