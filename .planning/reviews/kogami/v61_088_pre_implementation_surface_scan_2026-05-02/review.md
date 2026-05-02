# Kogami Review · v61_088_pre_implementation_surface_scan · 2026-05-02

**Verdict**: `APPROVE_WITH_COMMENTS`
**Recommended next**: `merge`
**Trigger**: autonomous_governance_rule_change
**Artifact**: `.planning/decisions/2026-04-27_v61_088_pre_implementation_surface_scan.md`
**Prompt SHA256**: `aa359511570dcbb424a8636bb309d857c1caeb68bc9777556c87a96b54f67fd6`

## Summary

DEC-V61-088 codifies pre-implementation surface scan as routine startup discipline in direct response to a Notion-Opus P1 finding. The decision-arc fit is sound: it generalizes upfront-check discipline already applied to case_profile/DEC-numbering/counter audit, and Alt 4 (soft-but-named, no hooks) is correctly chosen over the rejected alternatives. Three issues warrant attention before Accepted: (1) interaction with §11.1 Workbench freeze + §11.4 quota is unaddressed, (2) the >30 LOC threshold and skip-clause have ambiguous edges that will erode the rule, and (3) §4 Kogami trigger applicability is asserted but the §Hard Boundary self-modification framing deserves explicit acknowledgement.

## Strategic Assessment

Decision-arc coherence is strong. DEC-V61-088 sits cleanly in the post-pivot arc that has been consolidating self-discipline rules (RETRO-V61-001 verbatim exception, RETRO-V61-006 MP-A pre-Codex checklist, §11 anti-drift). It is the natural extension: just as MP-A added 'grep for new public function names from non-test callers' to pre-Codex checklist, this DEC adds 'grep for prior implementation' to pre-implementation. The Notion-Opus P1 framing — 'rationalization risk if accepted as routine excuse' — is exactly the failure-mode pattern the project has been actively defending against (cf. RETRO-V61-006 MP-C 'silent fallback audit'). Roadmap fit is good: the rule applies cleanly across M1-M4 / M5-M8 / M-VIZ work without imposing on trust-core where Codex is already mandatory. Retrospective completeness is solid — the DEC honestly names the framing-as-rationalization risk and adopts the soft-but-named compromise rather than over-engineering hooks. The main residual risk is fuzzy thresholds eroding the rule; the P2 findings above are about tightening that, not about the decision being wrong.

## Findings

### [P1] Kogami Hard Boundary self-modification check not addressed
**Position**: frontmatter `autonomous_governance` rationale + §Counter handling

**Problem**: The DEC modifies Claude Code's own startup discipline, which arguably falls under kogami_triggers.md §Hard Boundary 'meta DEC' clause: 'Any DEC whose subject matter modifies the Kogami isolation contract, counter rules, trigger rules, or Tier 1/Tier 2 boundary — regardless of which file paths are touched.' The DEC's frontmatter explicitly notes 'does NOT modify Kogami contract or files (P-1..P-5)' as the reason §4 skip rule does not fire — but this is the file-level test only. The author should explicitly state whether the Hard Boundary meta-test applies. If it does, this review must return CHANGES_REQUIRED with `out_of_scope_self_modification`. If it does not (because surface-scan is autonomous-side discipline, not Kogami-side), the DEC should say so explicitly so future readers don't have to re-derive.

**Recommendation**: Add a sentence in §Counter handling or §Out of Scope explicitly disposing of the Hard Boundary meta-test: 'This DEC modifies Claude Code's autonomous-side startup discipline only. It does NOT modify the Kogami isolation contract, counter rules, trigger rules, or Tier 1/Tier 2 boundary, so kogami_triggers.md §Hard Boundary meta-DEC clause does NOT apply. Kogami review fires per §4 first item (autonomous_governance rule-change) and may return APPROVE / APPROVE_WITH_COMMENTS / CHANGES_REQUIRED on substantive grounds.'

### [P2] Threshold edges (~30 LOC, ~10 LOC) are fuzzy and will erode under pressure
**Position**: §Decision opening sentence + §Skip clause (d)

**Problem**: '≥ ~30 LOC' and '≤ ~10 LOC' use the tilde to acknowledge fuzziness, but in operation this lets the rule slip: a 28-LOC change with a new top-level file genuinely needs the scan; a 12-LOC trivial edit genuinely doesn't. The current text uses 'OR new top-level page / route / service file' as the disjunction in the trigger but only LOC in the skip-clause (d). This asymmetry means a 9-LOC edit creating a new route file would skip per (d) despite triggering per the main rule. Under §11.1/§11.4 standing rules, threshold ambiguity historically collapses toward 'I judged this trivial' rationalizations — the exact failure mode this DEC is trying to fix.

**Recommendation**: Either (a) sharpen: '≥30 LOC OR new top-level page/route/service file' for trigger; skip-clause (d) becomes '≤10 LOC AND no new top-level file', so the disjunction is preserved on both sides; or (b) explicitly state that when the trigger and skip-clause conflict, the trigger wins. Pick one and state it.

### [P2] Interaction with §11.1 Workbench freeze + §11.4 quota not addressed
**Position**: §Out of Scope

**Problem**: §11.1 (Workbench feature freeze until KOM Active) and §11.4 (≤30 commits per 90-day rolling window on workbench paths) are active anti-drift rules. The surface-scan discipline interacts with both: a scan that finds 'existing X at workbench path' should likely defer to §11.1 (freeze) before choosing extend-or-parallel-or-refactor; a scan that finds nothing but the work IS workbench-territory should consume one §11.4 quota slot. Neither interaction is mentioned. Without it, the surface scan and the standing rules can produce contradictory signals.

**Recommendation**: Add a one-paragraph §Interaction with §11 standing rules: 'When the scan finds existing implementation in a §11.1-frozen surface, default to (a) extend existing or escalate; (b) parallel new is forbidden absent BREAK_FREEZE rationale. When the scan triggers in §11.4 quota territory, the planned commit counts toward quota regardless of whether the scan finds prior work.'

### [P2] Quoted-finding requirement in commit message is under-specified
**Position**: §Impact · Negative · 'requiring the findings to be *quoted* in the commit message when relevant'

**Problem**: 'When relevant' is the loophole. Without a sharper rule, the mitigation against ritual compliance becomes optional. The corresponding session 2026-04-27 case (commit 96e9f46) is the natural negative exemplar — its commit message did not quote a surface-scan result because no scan ran.

**Recommendation**: Tighten to: 'When the scan finds prior implementation, the commit message MUST include a `Surface-scan-found: <path>` trailer naming the prior implementation and the chosen disposition (extend / parallel / refactor). When the scan finds nothing, the commit message SHOULD include `Surface-scan: clean` (optional but encouraged). The trailer is what makes the audit trail machine-parseable for future retro review.'

### [P3] Acceptance Criteria #2 references ~/CLAUDE.md edit needing user confirmation but doesn't bind that confirmation to Kogami review outcome
**Position**: §Acceptance Criteria #2

**Problem**: The criterion says 'User confirms before edit' for ~/CLAUDE.md. This is fine, but the sequencing relative to Kogami APPROVE + Codex APPROVE + user ratification is implicit. A reader could plausibly read this as 'user confirmation of the edit' rather than 'user ratification of the DEC, then user confirmation of the specific edit text.'

**Recommendation**: Reorder: '1. Kogami APPROVE + Codex APPROVE + user ratification of DEC. 2. User confirms specific edit text for ~/CLAUDE.md before that edit lands. 3. Project CLAUDE.md edit follows.' One sentence; eliminates ambiguity.

