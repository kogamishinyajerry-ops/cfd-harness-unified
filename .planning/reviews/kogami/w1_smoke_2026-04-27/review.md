# Kogami Review · w1_smoke · 2026-04-27

**Verdict**: `APPROVE_WITH_COMMENTS`
**Recommended next**: `merge`
**Trigger**: w1-smoke-test
**Artifact**: `.planning/reviews/kogami/README.md`
**Prompt SHA256**: `cf4c41c865ac9b1cb675334e60a2963cd34bbed52a778dec1ab2943801993af8`

## Summary

The README accurately captures the DEC-V61-087 contract for Kogami review artifacts: directory layout, JSON schema, counter rules, hard boundary, and Tier 1→2 escalation. Two specifics drift from the DEC text (§3.1 flag list and §3.4 wrapper extraction semantics), and a few items are under-specified relative to what the wrapper actually enforces. None block adoption, but they should be tightened so this README does not become a rival source of truth that drifts from DEC §3.

## Strategic Assessment

This README sits cleanly within the post-2026-04-26 governance trajectory: Pivot Charter Addendum 1 (user-as-first-customer), RETRO-V61-001 (counter as telemetry, risk-tier-driven Codex), RETRO-V61-005 (independent-context Opus Gate as gate not source-of-truth), and DEC-V61-087's three-layer architecture (Kogami strategic / Codex code / Notion archive). The 'advisory gate, no counter impact' framing is correct and consistent with how Notion-Opus-4.7 reviews have historically operated. Roadmap-fit is good: the file is a P-3 deliverable in the W1 wave, ~40 LOC matches DEC §2, and it does not pre-empt P-4 (triggers) or P-5 (counter rules) which intentionally live in `.planning/methodology/`. The main strategic risk is documentation drift: this README paraphrases DEC §3 in several places, and paraphrases of physical-isolation contracts have historically been the v1/v2 failure mode (per DEC §Why). Tightening the cross-references rather than re-stating the contract would harden it.

## Findings

### [P2] Flag enumeration omits two empirically-required isolation flags from DEC §3.1
**Position**: §'What Kogami is' (top of file)

**Problem**: The README summarizes the isolation contract as 'claude -p subprocess invoked with --tools "" (no tools), --strict-mcp-config (no MCP), and an empty cwd'. DEC-V61-087 §3.1 lists six runtime flags as load-bearing for the verified isolation: --mcp-config <empty.json>, --tools "", --strict-mcp-config, --exclude-dynamic-system-prompt-sections, --no-session-persistence, --output-format json --max-turns 1, plus the empty-cwd switch and stdin-prompt requirement (variadic --mcp-config workaround). Dropping --exclude-dynamic-system-prompt-sections, --no-session-persistence, and the stdin-prompt note from the README invites a future contributor to 'simplify' the wrapper and break verified isolation.

**Recommendation**: Either reproduce the DEC §3.1 flag table verbatim, or replace the prose with a single sentence saying 'see DEC-V61-087 §3.1 for the full empirically-verified flag combo; do not modify the wrapper without re-running W0 Q1/Q5 probes', and link to the DEC.

### [P2] Review-JSON schema description elides the wrapper extraction step (envelope vs. inner JSON)
**Position**: §'Review JSON schema'

**Problem**: The README presents the schema as 'every review.json MUST satisfy [the inner schema]' and shows the jq validator. But per DEC-V61-087 §3.4, the subprocess returns an outer envelope `{"type":"result",...,"result":"<Kogami JSON as STRING>",...}` and the wrapper must `jq -r '.result'` before validating the inner object. A reader implementing tooling against this README alone would attempt to jq the envelope directly and fail. The §3.4 also specifies the INCONCLUSIVE fallback shape on 2x schema failure, which is omitted here.

**Recommendation**: Add one sentence noting the two-step extraction (`jq -r '.result'` from envelope, then schema-validate the inner JSON) and one sentence on the INCONCLUSIVE fallback `{"verdict":"INCONCLUSIVE","reason":"schema_validation_failed_2x"}` shape. Reference DEC §3.4.

### [P2] Hard-boundary list contains a dangling section reference
**Position**: §'Hard boundary (Out of Scope per DEC §)'

**Problem**: The header reads 'Out of Scope per DEC §' with the section number missing. Readers can't tell which DEC section authoritatively defines the boundary list. DEC-V61-087 places this in §2 (8-product table) and §4.2 (anti-recursion triggers); the README's protected list (P-1, P-1.5, P-2, P-2.5, P-3, P-4, P-5) matches §2 product IDs.

**Recommendation**: Fill in the section reference, e.g., 'Hard boundary (Out of Scope per DEC §2 / §4.2)'. Cosmetic but it's a normative anchor.

### [P3] P-3 self-reference is correct but easy to miss
**Position**: §'Hard boundary' bullet 'This file (P-3)'

**Problem**: Self-protection of this README is correct per DEC §2 (P-3 = `.planning/reviews/kogami/README.md`), but a future Kogami review of a DEC that proposes editing this file might not realize the review itself is barred from approving it. The current wording is accurate; the risk is reader confusion.

**Recommendation**: Optional: append '(Kogami review of any DEC modifying P-3 must return CHANGES_REQUIRED on out-of-scope grounds)' to that bullet.

### [P3] Frontmatter convention for review.md / invoke_meta.json not specified
**Position**: §'Directory layout'

**Problem**: The directory layout lists six files plus the W0 root artifacts but does not specify the frontmatter contract for `review.md` (human rendering) nor the field set for `invoke_meta.json` (cost, turns, claude version, flag combo). DEC §5 references `kogami_review_metadata: {prompt_sha256, trigger, ...}` as the canonical frontmatter on the artifact. Without that anchor here, downstream Notion sync tooling has to re-derive the contract.

**Recommendation**: Add a one-line pointer: 'See DEC-V61-087 §3.4 + §5 for review.md frontmatter (kogami_review_metadata) and invoke_meta.json field set.'

