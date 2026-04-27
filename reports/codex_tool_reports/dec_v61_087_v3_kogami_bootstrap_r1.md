# DEC-V61-087 v3 R1 Codex Review

**Reviewer**: Codex GPT-5.4 (xhigh reasoning)
**Date**: 2026-04-27
**Round**: v3 R1 (max 3 per DEC self-imposed cap; v1 R1 + v2 R1 both CHANGES_REQUIRED)
**v2 R1 finding closure**:
- `P0-1` Tier-1 auth/runnability: `RESOLVED`
- `P0-2` MCP/memory isolation overclaim: `PARTIALLY`
- `P1-1` deterministic input / bundle-hash recursion: `RESOLVED`
- `P1-2` strategic-package Codex-framing laundering: `PARTIALLY`
- `P1-3` mechanical contamination / missing-info / yes-and gate: `PARTIALLY`
- `P2-1` `--verbose` prerequisite: `RESOLVED`
- `P2-2` blind-control ownership / adjudication: `NOT`
- `P3-1` stale `~/.claude/CLAUDE.md` leak-vector framing: `RESOLVED`

## Verdict

`CHANGES_REQUIRED`

## Summary

v3 is materially closer than v2. The core bootstrap premise is now credible: on the live Claude Code `2.1.119` surface I verified `claude --help` documents `--tools ""` as "disable all tools", and an independent live probe with normal `HOME` + `--tools ""` + `--strict-mcp-config` returned `tools: []`, `mcp_servers: []`, and no canary-content leak.

But v3 still has two major design gaps before implementation: it overstates what `--exclude-dynamic-system-prompt-sections` buys, and P-2.5's validator contract is both internally inconsistent and still too weak to close semantic Codex-framing laundering. There is also a smaller but real wrapper-contract mismatch: `--output-format json --verbose` does not yield the "single schema object" that §3.3/§3.4 currently describe.

## v2 R1 Finding 修复状况

1. `P0-1` `RESOLVED`
   v3 drops the clean-`HOME` premise that broke auth in v2 and standardizes on normal `HOME` with the Tier-1 flags (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:137-158`). I independently re-ran `claude -p` on commit `db92d04`; the command executed successfully on Claude Code `2.1.119`, so the specific v2 bootstrap blocker is gone.

2. `P0-2` `PARTIALLY`
   The MCP half is fixed: v3 now requires `--strict-mcp-config --mcp-config empty.json` (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:139-156`), and my live probe showed `mcp_servers: []`. But the memory/dynamic-context claim is still overstated. `--exclude-dynamic-system-prompt-sections` does not remove those sections; `claude --help` says it moves them into the first user message. In addition, the live `--verbose` probe still exposed `memory_paths.auto` in init metadata. So "MCP cleared" is now true, while "only prompt string + generic base prompt remain" is not yet fully true as written.

3. `P1-1` `RESOLVED`
   v3 removes the self-referential bundle/manifest design entirely and shifts the reproducibility target to `prompt_sha256` over the generated prompt plus a direct determinism test (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:111`, `314-326`). That closes the specific v2 recursion / `generated_at` instability bug.

4. `P1-2` `PARTIALLY`
   The high-risk PR path is tighter than v2: it now passes `intent_summary.md`, `merge_risk_summary.md`, and a final verdict enum rather than raw diff / raw Codex report (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:239`, `262-274`). But the current blacklist only blocks literal tokens and file:line citations; it does not prevent semantic laundering via paraphrase. This is improved, not closed.

5. `P1-3` `PARTIALLY`
   Q1 is now a real canary regression test and Q3 is now a fixed classification table (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:300-367`), which is a real upgrade over v2. But the acceptance-side anti-yes-and evidence is still weak because the remaining self-review gate only asks Kogami to find at least one issue in this same DEC (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:381`). That is not equivalent to a blind control sample.

6. `P2-1` `RESOLVED`
   v3 does add `--verbose` to the launcher (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:144-145`), so the narrow v2 complaint about the missing verbose prerequisite is closed. A separate v3 wrapper-contract issue remains and is listed below.

7. `P2-2` `NOT`
   The frontmatter claims a fix ("control DEC authored by user"), but the body no longer specifies a blind-control artifact or an adjudication rule. Instead, the acceptance gate uses self-review of the same DEC (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:36`, `381`). That does not actually carry the v2 fix into the executable spec.

8. `P3-1` `RESOLVED`
   v3 no longer anchors the threat model to the stale `~/.claude/CLAUDE.md` example. The residual-risk section is now framed in broader terms (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:205-217`).

## v3 New Findings

### P1-1. §3.1/§3.2/Q5 still overclaim dynamic-context isolation

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:142-174`, `358-369`.

**Problem**: v3 treats `--exclude-dynamic-system-prompt-sections` as if it removes cwd/env/memory/git context from the model input. The live CLI help says otherwise: it moves those per-machine sections from the system prompt into the first user message. That matters because v3's central claim is now "the subprocess input space is only the embedded prompt string plus a generic base system prompt". On the reviewed `2.1.119` surface, that statement is too strong. My independent `--tools ""` live probe also showed `cwd` and `memory_paths.auto` in the verbose init envelope, which further confirms the dynamic surface still exists even though tools are removed.

**Why it matters**: this is no longer a v2-style P0 because built-in tool removal materially changes the threat model. But it does mean Q5 is checking the wrong object: sampling the verbatim system prompt is not the same as validating the total effective model input. As written, v3 still overstates its isolation guarantee.

**Recommendation**: rewrite §3.2 and Q5 to say "no external content access, but some dynamic path/status metadata may still be injected by Claude Code unless an auth-compatible `--bare` path exists". If zero dynamic-context input is still required, the DEC needs a different launcher premise, not just the current flag wording.

### P1-2. P-2.5 validator is internally contradictory and still too porous to close semantic Codex framing

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:264-274`.

**Problem**: the contract forbids `P0`, `P1`, `P2`, `P3`, but then gives `P2-T2` as a valid required milestone-reference example. A naive regex implementation will reject its own example. Even if that contradiction is fixed with word boundaries, the blacklist still only blocks literal strings. It does not block paraphrases like "one blocker remains around isolation", "the previous review already identified...", path-only references without `:line`, or lowercased / space-separated variants such as `changes required`.

**Why it matters**: v3's own closure argument for the high-risk PR path depends on P-2.5 being the mechanical shield against Codex-framing laundering. In its current form, it is neither precise enough nor strong enough to carry that load.

**Recommendation**: replace the two prose files with a strict structured schema and allowlist validation, for example enumerated fields for milestone, business goal, risk class, reversibility, blast radius, and a tightly bounded free-text rationale. If prose must remain, specify case-insensitive word-boundary matching and explicit exemptions for roadmap identifiers like `P2-T2`.

### P2-1. §3.3/§3.4 wrapper contract does not match the actual `json` output surface

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:143-145`, `176-203`.

**Problem**: the spec says stdout is a single JSON object matching the Kogami review schema and that the wrapper `jq`-validates that schema. On the live CLI surface, `--output-format json --verbose` does not produce that shape; it produces verbose event objects before the final result. Without `--verbose`, the CLI does return a single outer result object, but the assistant's actual JSON payload is then nested as a string in `.result`, not emitted as the top-level object itself.

**Why it matters**: this is not an architectural blocker, but the wrapper behavior is underspecified and currently wrong as written. A literal implementation of §3.3/§3.4 will parse the wrong object.

**Recommendation**: either remove `--verbose` from the runtime review path and validate `.result | fromjson`, or keep `--verbose` only for probe/debug mode and explicitly extract the final event payload before schema validation.

### P2-2. The self-review dry-run is still too weak to serve as the anti-yes-and gate

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:371-381`.

**Problem**: "review this DEC and emit at least one non-empty finding" is too easy to satisfy with shallow criticism that merely mirrors the DEC's own Open Questions or already acknowledged caveats. It is a useful smoke test, but it is not strong evidence that the strategic reviewer resists yes-and failure on blind input.

**Recommendation**: restore a genuine blind-control artifact with predeclared seeded faults and an external adjudication rule, or explicitly downgrade this acceptance item from "anti-yes-and evidence" to "basic non-empty-output smoke test".

## 整体评估

Architecturally, v3 is the first version that I would call directionally sound. The move from "prompt discipline" to "remove built-in tools from the subprocess entirely" is real, and it resolves the v2 premise-level blockers around clean `HOME` and MCP-only isolation. I would not send this back to user-level premise discussion.

`--tools ""` is credible enough to build on, but the evidence should be interpreted narrowly. The strongest points are: `claude --help` explicitly documents the flag, the live init event showed `tools: []`, and an independent read-canary probe did not leak file content. The one nuance is that the model can still emit faux strings like `[Read tool call for ...]` even when tools are absent, so future Q1 automation should key off `tools: []` / token non-leak rather than natural-language narration.

The self-pass-rate `0.80` is not calibrated. Given the current state, I would rate it closer to `0.60-0.65`: the main architecture is now plausible, but the DEC still overclaims zero dynamic-context input, underspecifies the actual output contract, and has not yet closed the semantic-laundering and anti-yes-and acceptance gaps.

`--max-turns 1` is acceptable for now. With tools physically removed, extra turns do not open new evidence channels; they mostly buy more reflection. If later testing shows review quality is too shallow, that should be treated as quality tuning, not as evidence that the isolation premise is wrong.

The base system-prompt cost is real but not disqualifying. My live probes came back around `$0.06` each. That is noticeable if review volume is high, but acceptable for an occasional strategic gate. The bigger immediate issue is correctness of the contract, not token price.

## 建议下一步

This is worth an `R2`. The remaining issues are real, but they are patch-level design corrections, not a premise collapse.

R2 should be tightly scoped:

1. Rewrite §3.2 / §3.5 / Q5 so the DEC no longer claims zero dynamic-context input unless it has a launcher that truly guarantees that.
2. Redesign P-2.5 as an allowlist-first structured schema, or at minimum fix the `P2-T2` contradiction and specify case-insensitive boundary rules.
3. Clarify the runtime wrapper contract for `json` output and either remove `--verbose` from the main review path or specify exact extraction of the final payload.
4. Replace the self-review acceptance item with a real blind-control sample, or demote it to smoke-test status.

If those four points are fixed cleanly, I would expect a v3 R2 pass to be realistic. W0 implementation should wait until then.
