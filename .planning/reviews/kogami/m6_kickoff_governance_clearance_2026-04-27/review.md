# Kogami Review · m6_kickoff_governance_clearance · 2026-04-27

**Verdict**: `APPROVE_WITH_COMMENTS`
**Recommended next**: `revise`
**Trigger**: phase_kickoff_strategic_clearance
**Artifact**: `.planning/strategic/m6_kickoff/brief_2026-04-27.md`
**Prompt SHA256**: `b7ea793c1f0c9992e824b45408206a080436826dc63bb9ff1fab8d76ed19bd23`

## Summary

The brief frames two genuine strategic questions (tier classification and M6/M7 relationship) cleanly and proposes a defensible default (path-(a) split mirroring M5.0/M5.1). However, the brief leaves the M6-vs-M7 framing genuinely under-specified — option (iii) reveals the M5 sHM stub already exists, which materially changes the picture and deserves an explicit author-recommended read rather than three equally-weighted options. Two governance-hygiene items also need tightening before kickoff.

## Strategic Assessment

Decision-arc coherence is mostly sound: this brief correctly mirrors the M5 kickoff structure (single-strategic-clearance precedent, deferred D-items inheritance, routine vs trust-core split). It honestly surfaces the FoamAgentExecutor.execute() blockMesh-hardcoding contradiction rather than papering over it — that surfaces real strategic content for Kogami to rule on. ROADMAP fit is good for M6 in isolation (gmsh path is settled per ROADMAP §M6) but the M6/M7 relationship question reveals that ROADMAP itself is under-specified on whether sHM is an alternative engine OR a sequenced second engine OR a fill-in-the-stub continuation. That ambiguity is upstream of this brief and arguably the brief's most valuable contribution — flagging it now rather than discovering it mid-M6. Retrospective completeness is adequate (D4 inheritance from M5 finding 4, M5.0/M5.1 precedent cited). The proposed path-(a) split is the most coherent default given M5 just shipped on that pattern; path-(c) tempting on 'M7=real OpenFOAM run' framing but would orphan M5.0's sHM stub work and leave M6 unable to demonstrate end-to-end value (mesh produced but never run). Path-(b) (single trust-core PR) is the strict-rigor option but contradicts the post-pivot governance降级 standing rule.

## Findings

### [P1] M6/M7 relationship presented as 3 equal options without author recommendation
**Position**: §'Strategic-layer questions for Kogami' question 2 (i)/(ii)/(iii)

**Problem**: The brief asks Kogami to rule among (i) parallel alternatives, (ii) sequential layering with mesh_engine selector, and (iii) M6=gmsh + M7=fill-in M5's sHM stub. These have very different downstream implications: (ii) requires a new schema field (`mesh_engine`) NOW in M6, (iii) means the M5.0 `snappyHexMeshDict.stub` is M7 input not orphan, and (i) requires both engines coexist at M6-close. The brief's own §'Open-but-not-blocking' note that the sHM stub 'becomes orphaned for imported cases that take the gmsh path' contradicts (iii) without resolving it. Kogami's role is decision-arc coherence, not picking from a menu the author hasn't pre-narrowed.

**Recommendation**: Author should pick one read as the recommended default (with rationale) and present the other two as alternatives Kogami may overrule. Recommend: (iii) is most coherent with ROADMAP §M7 'snappyHexMesh execution' phrasing AND with M5.0 already shipping the sHM stub — treating M5 stub as M7 starting point preserves the artifact's purpose. Then (ii)'s `mesh_engine` field is deferred to M7 (when the second engine actually exists), avoiding a per-case selector with only one option in M6.

### [P1] D6 cell-cap enforcement layer ambiguous — beginner default 5M may be too tight
**Position**: §'D6 (binds M6 + M7 per spec v2)' + §'Proposed deliverables' M6.0 'cell_budget.py'

**Problem**: D6 inherits 5M/50M caps from M5 spec v2 but the brief does not justify 5M for typical imported STL geometry. A naive gmsh tetrahedral mesh on a moderately-detailed STL (say cylinder.stl + boundary layer) routinely produces 2-8M cells before refinement; 5M is a hard guard that will misfire on legitimate beginner cases (user uploads STL → 'why does generate-mesh fail?'). Question 3 asks where to enforce but not whether 5M is calibrated.

**Recommendation**: Add a calibration sub-question: 'What is the empirical cell count for the M5 fixture STLs (cylinder, naca0012) under default gmsh settings? If >3M, the 5M beginner cap leaves <2x headroom and should be revisited.' Or: defer cap-tuning to M6.0 implementer with telemetry first run, hard-cap only at 50M power until empirical M6.0 fixtures land.

### [P2] DEC-V61-088 referenced as parent but listed as 'Proposed'
**Position**: frontmatter `parent_decisions` list

**Problem**: DEC-V61-088 (pre-implementation surface scan) is cited as the routine gate authority for this brief but is itself only Proposed (not Accepted). If V61-088 is rejected or amended in review, this brief's framing of 'routine gate analogous to M5's' loses its anchor. M5 kickoff brief did not have this dependency.

**Recommendation**: Either (a) note in frontmatter that this brief proceeds under V61-088's framing on the assumption V61-088 lands as drafted, with rollback path if amended; or (b) reframe the surface scan as ad-hoc 'per Claude Code routine startup discipline (see V61-088 draft)' rather than as a 'routine gate per V61-088'.

### [P2] M6.1 trust-core scope creep risk via case_kind='imported_user'
**Position**: §'M6.1 trust-core' bullet 2 (case_kind dispatch)

**Problem**: Adding a new `case_kind = 'imported_user'` value to FoamAgentExecutor's case-kind dispatch is described as a small change, but case_kind currently keys hardcoded `_generate_*` functions. Introducing a path that reads from `case_manifest.yaml` at runtime crosses a line: trust-core executor now consumes a manifest written by line-A scaffolding. This is a new line-A → trust-core data dependency that did NOT exist in M5. Kogami should explicitly weigh whether this is acceptable or whether case_manifest.yaml needs a trust-core schema lock first.

**Recommendation**: Either (a) add a sub-question for Kogami: 'Is line-A-authored case_manifest.yaml an acceptable input to trust-core executor dispatch, or does the manifest schema need its own DEC + lock first?'; or (b) constrain M6.1 to read only the patches list (already established in M5.0) and route via blockMesh-skip flag alone, deferring case_kind dispatch to M7.

### [P3] meshio dependency open question better belongs in M6.0 implementer note
**Position**: §'Open-but-not-blocking' meshio paragraph

**Problem**: The author already correctly classifies this as 'not strategic' but lists it among open questions. Strategic clearance briefs should not carry implementer-detail open items; they invite Kogami to spend reasoning budget on non-strategic content.

**Recommendation**: Move meshio question to a TODO comment in the future M6.0 implementation plan; remove from this brief.

