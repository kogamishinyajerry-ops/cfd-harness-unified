# Kogami Review · blind_control_v61_087_v1 · 2026-04-27

**Verdict**: `APPROVE_WITH_COMMENTS`
**Recommended next**: `merge`
**Trigger**: w3-blind-control-test
**Artifact**: `/var/folders/q4/859yhpgn6x3fx6kv4mj5gmv40000gp/T/blind_control_kofs_yz3/dec_under_review_blind_control.md`
**Prompt SHA256**: `a173c41e722daa3ee169bb15f0e3a3119779d50775ecc8d5bf1582caef881a6a`

## Summary

DEC-V61-087 v3 is a substantive, well-reasoned governance evolution that correctly addresses the v1/v2 failure modes identified by Codex and grounds its isolation contract in empirically verified flag behavior. The decision-arc coherence with RETRO-V61-001 (counter rules), Pivot Charter §4.7 (CLASS framework), and DEC-V61-073 (sampling audit/anti-drift) is strong, and the honest residual-risk enumeration in §3.5 plus the Tier-2 escalation triggers in §3.6 make this a falsifiable governance contract rather than a self-congratulatory one. Findings below are P1/P2 — none block ratification, but two should be addressed before W1 implementation begins.

## Strategic Assessment

Decision-arc coherence: STRONG. v3 directly consumes the v1/v2 Codex failures (prompt-contract not enforceable → process boundary still leaky → physical capability removal via `--tools ""`), with each failure mode acknowledged honestly in §Why. The W0 empirical fixes (cwd switch, stdin prompt) show real iteration, not paper-over. Compatibility with RETRO-V61-001 counter rules verified via Q4 dry-run; compatibility with DEC-V61-073 §10.5 sampling audit infrastructure is implicit (kogami_triggers.md Tier-2 list mentions Q5 keyword sampling but doesn't formally bind to §10.5). Roadmap fit: NEUTRAL-TO-POSITIVE. Workbench main-line M1-M4 is COMPLETE per ROADMAP.md, so this governance work doesn't compete with user-facing delivery. The ~1030 LOC estimate (mostly docs) is proportionate; the W0/W1/W2/W3/W4 staging with explicit user-ACK gates between waves is consistent with §10.4 Line-A/B isolation discipline. Retrospective completeness: STRONG. §3.5 enumerates 6 honest residual risks; §3.6 specifies Tier-2 escalation triggers; §Risks table covers 7 distinct failure modes with mitigations. Out-of-scope hygiene: STRONG. §Out of Scope explicitly lists 8 items including the recursion guard (Kogami doesn't review its own reviews) and the counter non-inflation invariant. The Hard Boundary in kogami_triggers.md correctly anticipates anti-self-approval but has a recursion gap (Finding P2 above). Risk-vs-benefit framing: SOUND. Notion-Opus replacement value (faster turnaround, tool access, automatic provenance) is real; the cost (loss of cross-model independence) is honestly acknowledged as 'Codex stays for code-layer; Kogami covers strategic-layer with same-model-but-different-process'. The Tier-1 → Tier-2 escalation path means this is a reversible, falsifiable bet rather than a one-way door.

## Findings

### [P1] Q1 canary verification method underspecified for the actual leak vector
**Position**: §3.6 + Acceptance Criteria Q1 evidence

**Problem**: §Open Questions Q1 (in v1 form) was the dominant unknown that v3 claims to have resolved via `--tools ""`. But the W0 dry-run described in `empirical_probes_completed` and the `Q1 canary regression test (monthly cron)` referenced in §3.6 and kogami_triggers.md §Tier 1 → Tier 2 are not specified concretely in the DEC itself. Specifically: (a) what canary token(s) are seeded into which input channels (cwd files? memory_paths target? env?), (b) what constitutes a 'leak' for sampling purposes (substring? embedding similarity? metadata-only?), (c) what is the sample-size n for monthly cron and how does it interact with the §3.5(3) `--tools ""` semantic-change risk acceptance. Without this specified in the DEC, the load-bearing 'physical capability removal' claim depends on an unspecified test, and Tier-2 escalation triggers can't be evaluated.

**Recommendation**: Add a §3.7 'Q1 canary specification' subsection (or expand AC item Q1) listing: (a) ≥3 distinct canary tokens placed in (i) project CLAUDE.md content, (ii) memory_paths.auto target file, (iii) env var; (b) leak definition = exact-substring match of any canary in subprocess `.result`; (c) n=5 runs per month minimum, all 5 must show 0 hits; (d) re-run mandatory on any `claude` CLI version change. Reference this section from §3.6 and from kogami_triggers.md Tier-2 list.

### [P1] §4.4 paraphrase-laundering residual risk lacks a closure metric
**Position**: §4.4 Honest residual risk paragraph + kogami_triggers.md §Strategic package authoring

**Problem**: §4.4 honestly acknowledges that regex blacklist + structured YAML can be defeated by paraphrase ('prior review identified a blocker'). The mitigation is described as 'sampling audit on accumulated review history can detect systematic paraphrase pattern' and Tier-2 escalation 'can include' ≥3 paraphrase instances. But (a) no concrete sampling cadence is specified (interval? sample size?), (b) the trigger uses 'can include' (advisory) rather than a binding count, (c) no owner is assigned. This is the same anti-pattern §10.5 was created to fix for §10 治理降级 — a falsifiability hole in an advisory rule. Without a concrete sampling rule, the §4.4 'improved, not closed' position drifts toward 'closed by hope'.

**Recommendation**: Bind paraphrase-laundering audit to the existing §10.5 sampling-audit infrastructure: every Nth Kogami review (e.g., N=10) is sampled by the human reviewer (CFDJerry or external Opus session) for paraphrase patterns in author-supplied `rationale` fields. ≥3 confirmed paraphrase instances within a 30-review window → Tier-2 escalation MANDATORY (not advisory). Record cadence in §4.4 + cross-link from kogami_counter_rules.md §5.5.

### [P2] Hard Boundary anti-self-approval rule has a recursion gap
**Position**: §4.2 must-NOT trigger list, last bullet · kogami_triggers.md §Hard Boundary file list

**Problem**: kogami_triggers.md §Hard Boundary lists 7 files (P-1 through P-5 plus this file and kogami_counter_rules.md) that Kogami cannot self-approve. But DEC-V61-087 itself is the governance contract that establishes this boundary. A future DEC modifying DEC-V61-087's §3 (isolation contract) is not explicitly listed in the Hard Boundary file paths — only the implementation artifacts are. A clever framing ('we're not modifying P-1, just amending DEC-V61-087 §3 to relax which flags are required') could route around the rule. The DEC §4.2 'must NOT trigger' list mentions 'Kogami's own P-1/.../P-5 modifications' but not 'modifications to DEC-V61-087 itself or successor DECs that re-architect Kogami'.

**Recommendation**: Extend the Hard Boundary to include 'any DEC whose `parent_dec` includes DEC-V61-087 OR whose subject is the Kogami isolation contract / counter rules / trigger rules'. Update both the DEC §4.2 enumeration and kogami_triggers.md §Hard Boundary. This closes the meta-recursion: Kogami v3.1 / v4 cannot self-approve its own governance evolution.

### [P2] Counter provenance logic conflates Interpretation A and B without a binding tiebreaker
**Position**: frontmatter `autonomous_governance_counter_v61_provenance` + kogami_counter_rules.md §5.6

**Problem**: `autonomous_governance_counter_v61_provenance` says 'Interpretation B (STATE.md = SSOT, established by V61-086 provenance precedent), this DEC advances 52 → 53. Strict-bookkeeping Interpretation A would also yield 53 in this case (no intermediate silent advances since V61-075), so both interpretations agree here.' This is fine for V61-087 specifically but defers the actual choice. If a future DEC has divergent A/B values, there is no binding rule. RETRO-V61-001 says counter is pure telemetry, but provenance disputes are still live (V61-080/081/082/FORENSIC-FLAKE silent advances per STATE.md last_updated). Kogami's counter rules document (§5.6 Q4 dry-run) verifies historical compatibility but doesn't codify which interpretation is canonical going forward.

**Recommendation**: Either (a) add a one-line ratification in §5 of DEC-V61-087: 'Interpretation B (STATE.md last_updated = SSOT) is canonical going forward per V61-086 precedent', OR (b) open a follow-up DEC explicitly choosing. Without canonicalization, any future arc with intermediate silent advances will re-litigate. Low-cost fix; high value for future audit clarity.

### [P3] Process Note's GSD-bypass justification is sound but creates a precedent worth flagging
**Position**: §Process Note

**Problem**: §Process Note explains why this DEC didn't go through `/gsd-discuss-phase` (project's main-line is workbench-closed-loop M1-M4 COMPLETE; no governance phase exists in ROADMAP.md). The reasoning is correct. But this is the second governance-class artifact bypass in a row (DEC-V61-073 sampling audit was similar; ADR-002 W2 G-9 was similar per RETRO-V61-005). A pattern is forming where governance evolution lives outside the GSD phase model. This isn't wrong, but it's worth surfacing as a meta-question for the next arc-size retro.

**Recommendation**: Add one sentence: 'If governance-class DECs continue to accumulate outside the GSD phase model (DEC-V61-073, ADR-002, this DEC), open a follow-up retro at counter ≥ 60 to evaluate whether ROADMAP.md should add a standing 'governance' phase or whether the current pattern is deliberate.' No action needed for V61-087 itself.

