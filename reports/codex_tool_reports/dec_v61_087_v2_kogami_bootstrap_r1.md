# DEC-V61-087 v2 R1 Codex Review

**Reviewer**: Codex GPT-5.4 (xhigh reasoning)
**Date**: 2026-04-27
**Round**: v2 R1 (max 3 per DEC self-imposed cap; v1 R1 produced CHANGES_REQUIRED)
**v1 to v2 changes verified**:
- `P0-1` Tier-1 isolation contract: `PARTIALLY_RESOLVED`
- `P0-2` high-risk PR contradiction: `PARTIALLY_RESOLVED`
- `P1-1` deterministic input / manifest proof: `PARTIALLY_RESOLVED`
- `P1-2` truth table / N/A boundary coverage: `RESOLVED`
- `P1-3` mechanical contamination / missing-info acceptance: `PARTIALLY_RESOLVED`
- `P2-1` trigger precedence: `RESOLVED`
- `P2-2` hard boundary on Kogami self-modification: `RESOLVED`
- `P3-1` review output path consistency: `RESOLVED`

## Verdict

`CHANGES_REQUIRED`

## Summary

v2 correctly abandons the v1 prompt-contract model and moves the design toward a real process boundary. That is the right architectural direction.

But on the actual Claude Code `2.1.119` surface available on `2026-04-27`, the proposed Tier 1 boundary is still not runnable or not as strong as claimed: `HOME=clean` drops auth on this machine, `--mcp-config` alone does not disable existing MCP servers, and auto-memory remains enabled unless the launcher moves to a different invocation model. In parallel, the new bundle-hash design is still non-deterministic as written, and the high-risk PR strategic package can still leak Codex framing through author-written summaries.

## v1 R1 Finding 修复状况

Note: the v1 R1 report actually contains `8` findings, not `7`:
`2 P0 + 3 P1 + 2 P2 + 1 P3`.

1. `P0-1` `PARTIALLY_RESOLVED`
   v2 does replace Task sub-agent + prompt whitelist with `claude -p` subprocess + copied bundle + temp cwd (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:88-93`, `132-165`), which is a real architectural correction. But the concrete Tier 1 launcher is still not operationally sound on the current CLI surface: clean `HOME` loses auth, MCP isolation needs a stronger flag than the DEC specifies, and auto-memory remains present. So the old premise is gone, but the new one is not yet executable.

2. `P0-2` `PARTIALLY_RESOLVED`
   The explicit contradiction is fixed: high-risk PR input no longer includes raw diff or Codex report content (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:267-279`). However, `intent_summary.md` and `merge_risk_summary.md` are author-written and unconstrained. Because the author is normally the same agent that already consumed the Codex review, those summaries can still launder Codex findings back into the Kogami package. The direct contradiction is gone; the framing-leak path is not.

3. `P1-1` `PARTIALLY_RESOLVED`
   v2 improves the proof surface by hashing script/rule/version state and by committing a bundle artifact hash (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:169-193`). But the new construction is still broken as written: the manifest contains `generated_at`, and the bundle hash is defined over a tar of the entire bundle that includes the manifest itself and its own `bundle_artifact_hash` field. Q2 therefore cannot satisfy its own 60-second replay criterion as specified (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:366-373`).

4. `P1-2` `RESOLVED`
   The v2 truth table now distinguishes `autonomous_governance:true DEC`, `false DEC`, `Kogami review artifact`, `spawned review`, and `RETRO`, and Q4 now samples the missing `V61-006` / `V61-011` precedents (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:311-336`, `395-405`). The N/A boundary is materially clearer than v1.

5. `P1-3` `PARTIALLY_RESOLVED`
   Q1/Q3/blind control DEC are now mechanical instead of subjective (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:349-428`). But the canary plan still undercovers the real leak surfaces of Claude Code `2.1.119`: it seeds prompt text, temp file, commit message, TODO, and shell history, yet says nothing about `~/.claude` session state, auto-memory, settings, or persisted project state. That means a contaminated launcher can still false-pass Q1.

6. `P2-1` `RESOLVED`
   v2 adds an explicit precedence ladder `arc-size retro > retro draft > phase-close > high-risk PR` plus `superseded_triggers` recording (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:289-300`).

7. `P2-2` `RESOLVED`
   The hard boundary now explicitly bans Kogami self-approval of its own agent prompt, brief script, invoke wrapper, trigger rules, and counter rules, and requires both user ratification and Codex APPROVE (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:459-463`). This is strict enough for the original v1 finding.

8. `P3-1` `RESOLVED`
   The output convention is now consistently directory-based: `.planning/reviews/kogami/<topic>_<date>/review.md` with manifest / bundle artifacts alongside it (`.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:111`, `193`).

## v2 New Findings

### P0 (blocker)

#### P0-1. §3 Tier 1 invocation contract is not runnable on the actual Claude Code 2.1.119 auth surface

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:140-145`, `195-228`, `407-417`.

**Problem**: the DEC treats `HOME=/tmp/kogami_clean_home_*` as a core Tier 1 primitive and only discusses fallback for `CLAUDE.md` / OS sandboxing. On this machine, a real probe on `2026-04-27` shows that changing `HOME` to a fresh temp directory causes `claude -p` to return `Not logged in · Please run /login`. A second probe confirms `ANTHROPIC_API_KEY` is not set in the environment, so there is no existing env-based auth path for the wrapper to inherit. The stronger first-party isolation flag `--bare` is available in `claude --help`, but it also fails on this machine for the same reason: the help text says bare mode only supports `ANTHROPIC_API_KEY` or `apiKeyHelper`, and the live probe returns `Not logged in`.

**Why this blocks**: v2 currently has no auth-preserving isolation story. Its fallback list only says “temporarily move `~/.claude/CLAUDE.md`” or use `unshare` / `bwrap`, but neither of those answers the launch question when clean `HOME` itself breaks the CLI. This is not a patch-level shell issue; it is a broken bootstrap premise.

#### P0-2. §3 overstates MCP and memory isolation; on 2.1.119 the specified flags do not produce the claimed surface

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:143`, `212-228`, `235-250`, `340-342`, `409-417`.

**Problem**: v2 repeatedly claims that `--mcp-config /tmp/kogami_empty_mcp.json` disables MCP and physically prevents Notion access. A real `stream-json` probe on `2026-04-27` shows otherwise:
- Default `claude -p` in an empty `/tmp` directory still booted with 6 connected MCP servers and an `auto` memory path.
- `--mcp-config empty.json` alone still booted with those same 6 MCP servers connected.
- Only `--strict-mcp-config` removed MCP servers.
- Even with `--strict-mcp-config`, the init event still exposed `memory_paths.auto`, so “MCP cleared” is not equivalent to “clean strategic surface”.

**Why this blocks**: the DEC’s core independence claim is that Tier 1 is a materially isolated strategic reviewer. On the actual CLI, the exact wrapper described in §3.4 does not establish that surface. The combination “clean HOME + empty MCP config + temp cwd” is currently neither runnable nor complete.

### P1 (major)

#### P1-1. The v2 bundle-hash design is still non-deterministic and self-referential

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:169-193`, `366-373`.

**Problem**: the manifest includes `generated_at`, and `bundle_artifact_hash` is defined as a hash of a tar of the entire bundle directory. Since the manifest itself is inside that directory and itself contains `bundle_artifact_hash`, the definition is recursive unless special exclusion / two-pass canonicalization is stated. Even if the recursion is resolved implicitly, `generated_at` alone makes the entire tar unstable across the 60-second replay that Q2 expects to pass.

**Impact**: the main carryover from v1 P1-1 is not actually closed. v2 now hashes a better object, but it still does not define a reproducible object.

#### P1-2. The strategic package still has an unbounded Codex-framing laundering path

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:271-279`.

**Problem**: removing raw diff and raw Codex report is necessary, but not sufficient. `intent_summary.md` and `merge_risk_summary.md` are written by the PR author, and the DEC gives them no schema or provenance rule that forbids importing Codex findings or Codex language. In the common case, the “author” is the same development agent that just read the Codex report. That means the high-risk PR path still allows semantic Codex framing to be passed into Kogami, just one level more indirectly.

**Impact**: the explicit contradiction from v1 is fixed, but the “Kogami does not see Codex framing” claim remains overstated.

#### P1-3. Q1 canary coverage does not test the leak surfaces that the live CLI actually exposes

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:349-360`.

**Problem**: the canary plan seeds 5 places, but the live `stream-json` init event on this machine shows other relevant surfaces: connected MCP servers by default, an `auto` memory path under `~/.claude/projects/.../memory/`, and a user-level `~/.claude` state tree with settings/history/projects/session state. None of those are covered by the current canary locations. A launcher could therefore leak through user-level Claude state, pass the current five canary checks, and still violate the design’s independence claim.

**Impact**: Q1 is more mechanical than v1, but still not sufficient evidence for the v2 threat model.

### P2 (minor)

#### P2-1. §3.4 / Q5 are not executable verbatim on 2.1.119 because `stream-json` requires `--verbose`

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:211-216`, `223-228`, `412-417`.

**Problem**: a live probe on `2026-04-27` shows that `claude -p --output-format stream-json ...` errors with `When using --print, --output-format=stream-json requires --verbose`. The current wrapper pseudocode omits `--verbose`, and Q5’s reproducer section does not mention this prerequisite.

**Impact**: this is not the deepest architecture issue, but the DEC currently describes a command line that does not run as written.

#### P2-2. Blind control DEC ownership is undefined, so the yes-and check can be gamed

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:428`.

**Problem**: the acceptance rule says a control DEC should contain 3 seeded mistakes and Kogami must detect at least 2 of them. But it does not define who is allowed to author the control DEC, who validates that the seeded errors are non-trivial, or who adjudicates “detected” versus “vaguely gestured at”. If the same implementation author both writes the control and judges the result, the test can degrade into a yes-and ceremony.

**Impact**: not a reason to reject the whole design alone, but it weakens the claimed mechanical nature of the final gate.

### P3 (nit)

#### P3-1. The repeated “user-level `~/.claude/CLAUDE.md` 217-line leak” claim is stale on the current machine

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:55-56`, `142`, `225`, `414`.

**Problem**: the DEC repeatedly uses a concrete `~/.claude/CLAUDE.md` example as the dominant leak vector. On the machine reviewed on `2026-04-27`, `~/.claude/CLAUDE.md` is not present. The real user-level state surface is the broader `~/.claude/` tree.

**Impact**: this does not change the verdict by itself, but it is another sign that §3.6 and Q1 are anchored to the wrong concrete threat model.

## 整体评估

v2 is materially better than v1. The design no longer relies on prompt ethics and it no longer directly feeds raw diff / Codex report content into the high-risk PR path. Those are real upgrades.

But the self-estimated pass rate `0.70` is not calibrated to the actual `claude` surface on this machine. After live probing Claude Code `2.1.119`, the main unresolved risk is no longer “small flag mismatch”; it is that the chosen isolation primitives do not currently compose into a runnable and trustworthy Tier 1 launcher. Clean `HOME` breaks auth, `--mcp-config` alone is not isolating, `--strict-mcp-config` still leaves auto-memory, and `--bare` is not usable without a different auth path. I would rate the current design below the DEC’s claimed `0.70` until §3 is rewritten around a real runnable bootstrap.

The `max 3 round` cap remains reasonable. This is still a design dispute, not an implementation arc, and it should either converge in one more focused round or go back to user-level premise selection.

## 建议下一步

Because v2 still has architectural-level P0s, I do **not** recommend moving forward with a patch-style W0-W4 implementation based on the current text.

The next step should be a premise discussion, not a generic fix list:
- Choose a **runnable** Tier 1 bootstrap model first.
- The realistic choices on this machine are likely:
  1. normal `HOME` + stronger first-party flags + explicit acceptance of residual memory risk, or
  2. OS/container isolation with a separately defined auth injection path.
- Only after that premise is settled should the author spend an R2 round rewriting §3.1-§3.6 and Q1/Q5 around the real launcher.

If the author is unwilling to revisit the invocation/auth premise and wants to keep “clean HOME + empty MCP + cwd switch” as the load-bearing claim, I would stop here and return the design to user discussion rather than spend the remaining rounds on patchwork.
