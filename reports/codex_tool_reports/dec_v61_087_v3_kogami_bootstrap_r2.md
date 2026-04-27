# DEC-V61-087 v3 R2 Codex Review

**Reviewer**: Codex GPT-5.4 (xhigh reasoning)
**Date**: 2026-04-27
**Round**: v3 R2 (max 3 per DEC self-imposed cap; v3 R1 was CHANGES_REQUIRED "worth an R2")
**v3 R1 finding closure**:
- `P1-1` `RESOLVED`
- `P1-2` `RESOLVED`
- `P2-1` `RESOLVED`
- `P2-2` `RESOLVED`

## Verdict

`APPROVE_WITH_COMMENTS`

## Summary

v3 R2 cleanly closes the four issues I called out in v3 R1. The DEC is now explicit that dynamic per-machine metadata is moved rather than removed, the runtime wrapper contract matches the live CLI `json` surface, and the anti-yes-and gate has been upgraded from self-review smoke to a real blind-control check.

What remains is not architecture-level. I found one concrete execution-contract sync bug and one small adjudication-spec gap in the new blind-control wording; both are non-blocking and should be cleaned up as part of W0/W3 implementation.

## v3 R1 Finding 修复状况

1. `P1-1` `RESOLVED`
   **Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:173-195`, `245-259`, `431-451`.

   v3 R2 no longer overclaims zero dynamic-context input. §3.2 now explicitly says `--exclude-dynamic-system-prompt-sections` moves cwd/env/memory-path/git-status metadata into the first user message rather than removing it, §3.5 records that metadata leak as an accepted residual risk, and Q5 now samples both the base system prompt and the dynamic first-user-message section. That is the correction v3 R1 asked for.

2. `P1-2` `RESOLVED`
   **Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:304-347`.

   The internal contradiction is gone. Free prose has been replaced with a structured YAML surface, the `P2-T2` example no longer self-conflicts with the `\bP[0-3]\b` blacklist rule, and the blacklist is now scoped to the only explicitly free-text field (`rationale`). I do not read the remaining paraphrase risk as a reopened R1 blocker here because v3 R2 no longer pretends that regex fully solves semantic laundering; it honestly downgrades that to residual risk.

3. `P2-1` `RESOLVED`
   **Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:142-159`, `203-243`.

   The runtime path has dropped `--verbose`, and §3.4 now describes the actual envelope shape returned by `claude -p --output-format json`: extract `.result`, then validate the decoded Kogami JSON. Keeping `--verbose` only in probe/debug mode is the right split for the live CLI surface I called out in v3 R1.

4. `P2-2` `RESOLVED`
   **Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:455-465`, `502-505`; ground truth source `reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md:23-91`.

   The acceptance gate is now a real blind control instead of "review this same DEC and say at least one critical thing." Using v1 (`4509bb1`) as the hidden review target and the pre-existing v1 R1 report as ground truth is materially stronger anti-yes-and evidence than the old self-review smoke test. The threshold is intentionally light, but it is no longer circular.

## v3 R2 New Findings (if any)

### P2-1. Acceptance / implementation text still contains stale pre-R2 success criteria

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:431-451`, `463-465`, `502-505`.

**Problem**: the R2 patch updated the detailed Q5 and P-2.5 sections, but two downstream execution clauses still reflect the older spec. Q5 now tests total model input and six keyword sets, yet the Acceptance Criteria still say `Q5 base system prompt: 5 个关键词 0 命中` (`463`). Likewise, Acceptance now requires eight P-2.5 manual samples (`464`), but the W2 implementation plan still says `P-2.5 5 测试样本通过` (`504`).

**Why it matters**: these are not theory problems, but they are real execution-contract mismatches. If left as-is, W0/W2 scripts can be written against the wrong success condition while still appearing compliant with some part of the DEC.

**Recommendation**: sync the Acceptance Criteria and Implementation Plan to the R2 definitions before writing the verification scripts. Specifically, line `463` should reference total-input Q5 sampling rather than only the base system prompt, and line `504` should match the eight-sample P-2.5 test matrix.

### P3-1. Blind-control adjudication is now valid, but the regex match table is not fully frozen

**Position**: `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md:465`; ground truth findings at `reports/codex_tool_reports/dec_v61_087_kogami_bootstrap_r1.md:23-91`.

**Problem**: the new blind-control gate says matching is mechanical and regex-based, but the DEC only gives an explicit keyword family example for one of the eight v1 findings. The other seven are still implicitly "to be inferred from the report" rather than predeclared in the acceptance contract.

**Why it matters**: this does not break the blind-control idea, but it leaves a small amount of operator discretion in what counts as a hit. That weakens the "mechanical adjudication" claim more than the review design itself.

**Recommendation**: before W3, freeze an eight-row match table derived from the existing v1 R1 finding titles and keep it in the verification script or a sibling fixture. That will make the gate genuinely mechanical end to end.

## 整体评估

This is ready for W0 implementation. The remaining items are patch-sync comments, not pattern-level or architectural-level blockers.

The self-pass-rate `0.75` is now defensible. I still would not describe semantic Codex-framing laundering as "closed," but v3 R2 no longer hides that limitation, and the current structured surface is good enough to move from DEC debate into implementation and empirical verification.

## 建议下一步

`APPROVE_WITH_COMMENTS`。给绿灯进入 W0 implementation。

进入 W0/W2/W3 时先做两件小清理：

1. 把 Acceptance / W2 plan 里残留的旧 Q5 与旧 sample-count 文案同步到 R2 版本。
2. 把 blind-control 的 8 组 regex 命中规则预先固化，避免 W3 时再做人工解释。
