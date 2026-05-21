# Strategy Review

Owned by `strategy-director`. Updated whenever scope, wedge, or roadmap shifts.

## Strategic posture (v0)

We sell **trust**, not solving. The customer who would care about this product
is the engineer or manager whose career depends on a CFD result not being wrong.

## Three strategic risks we are explicitly underwriting

1. **Over-engineering the workbench.** Mitigated by `SCOPE_FIREWALL.md` and a
   project-governor that has authority to reject scope creep.
2. **Demo theatre.** Mitigated by "no evidence, no progress" in CLAUDE.md and by
   Red Team review.
3. **AI overreach.** Mitigated by "AI is advisor over evidence" — advisor cannot
   modify case files or override gates.

## Three strategic risks we are explicitly NOT underwriting yet

1. **Solver fidelity.** Phase 0 uses a mocked solver. Solver fidelity work belongs
   to Phase 1+, after the trust loop is credible.
2. **Reference dataset licensing.** Acknowledged as open question (OQ-0001). Will
   be resolved before Phase 1 ships.
3. **GTM, pricing, branding.** Out of scope until the technical wedge is real.

## Wedge quality criteria

For the wedge to be considered "real," all of:

- a `case_manifest.yaml` plus a mocked or real solver run produces a `trust_report.json`
  that an outside CFD engineer would find honest;
- the cockpit lets the owner state current state without re-reading any chat;
- the harness catches seeded bad cases (after Phase 2);
- mocked execution is impossible to mistake for validated execution.

If any of those fail, the wedge is not yet real, regardless of feature count.

## Anti-wedges (failure modes we refuse)

- "CFD copilot" that types BCs for the user
- "auto-fix mesh" that reshapes geometry without an artifact trail
- "AI selects turbulence model" with no rationale and no override
- "everything is green" cockpit that hides MOCKED
