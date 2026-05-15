# Codex Review · D11 Cross-Val · Round 1 Summary

**Milestone**: V64-A Tier 3 · M-V64A-D11-CROSS-VAL
**Round**: 1 / 3 (per v2.3 DEC-V61-133 Codex review round cap)
**Triggered by**: pre-push cadence-floor hook (cumulative diff 1993 →
2146 LOC including interleaved case_006 main-session commit), not by
risk-class. Per v2.2 1-sync-trigger rule the diff itself has no
security-boundary touch.
**Tool**: `codex-review-relay --base origin/main` (86gs gpt-5.4 xhigh)
**Date**: 2026-05-15
**Verdict**: APPROVE_WITH_COMMENTS (B60-scope P1 RESOLVED · 1 P2
out-of-scope · routed to parallel chain)

---

## Findings

### P1 (B60 scope · RESOLVED)

> Compare stack-routed findings before marking a case matched —
> `scripts/v64_d11_cross_val/run_d11_cross_val.py:119-126`
>
> If `assemble_stack()` stops dispatching D11, returns `status="error"`,
> or normalizes a different finding set than the direct validator, this
> code still records `verdict.match = true` because the comparison is
> built only from `direct_report.findings`. In that scenario the runner
> exits 0 and the committed evidence claims the cross-val passed, so
> regressions in the stack path this script is supposed to validate are
> silently missed.

**Resolution** (commit `5394846` — `fix(v64-d11-xval): Codex R0 P1 ·
triple-agreement verdict ...`): runner now builds two finding-count
maps (`direct_by_code` + `stack_by_code`) and requires triple-agreement
(`expected == direct == stack` AND `stack_status == "ok"`) before
setting `verdict.match = true`. Evidence JSON records all four sub-
flags individually so divergence is captured rather than masked.

Re-run post-fix: 3 / 3 cases pass triple-agreement
(`d=e:True s=e:True d=s:True` on every case · all `stack_status=ok`).
Section-1 3/3 PASS verdict preserved AND strengthened (now validates
the dispatch gate + normalize pipeline, not just the pure-function
advisor).

### P2 (B60 antithesis · OUT-OF-SCOPE)

> Include the retained `tip_cap` patch in force coefficients —
> `.planning/case_profiles/case_006_v64_val_full_2_dicts/system/controlDict:25-31`
>
> When these dicts are used to reproduce case_006 v2, `forceCoeffs1`
> integrates only `wing_surface_reference`, but the same case keeps
> `tip_cap` as a separate wall patch in `snappyHexMeshDict`. Any
> reported Cl/Cd/Cm will therefore omit the loads on the tip closure,
> biasing the validation numbers against the full-wing ONERA M6
> reference whenever the v2 mesh retains that patch.

**Disposition**: explicitly out of B60 scope. Per the V64-A Tier 3
M-V64A-D11-CROSS-VAL dispatch brief antithesis (verbatim):
> ❌ 不修改 case_004 / case_006 / case_011 任何文件

The `case_006_v64_val_full_2_dicts/` directory was created by a
**parallel main-session commit** (`e3a1a52 feat(v64-case006-full2):
case_006 ONERA M6 rhoSimpleFoam + kOmegaSST + mesh prep · 14 dicts ·
NACA-equivalent ONERA-D semi-span wing geometry verified`) that landed
between this sub-session's session start (HEAD `7a74da6`) and this
sub-session's first commit (`186ca72`). Sub-session never touched
case_006 files and is forbidden from doing so by the dispatch brief.

This finding will surface in the parallel main-session's own DEC chain
(`DEC-V64-A-sub-VAL-FULL-2` working through `M-V64A-VAL-FULL-2 case_006
ONERA M6`). The interleaving was a coincidence of git-history sequencing
on `main`, not a B60 scope concession.

---

## Round budget remaining

- Used: 1 / 3 (per v2.3 DEC-V61-133 cap)
- Remaining: 2 / 3
- Expected use: none. P1 addressed; P2 explicitly out of scope. No
  further rounds expected on B60 work.

If P2 propagates back into B60 scope (e.g., via D11 cross-val being
asked to consume case_006 substrate later), this round budget will
become relevant; not today.

---

## Notion sync

This Codex round summary is part of the B60 sub-DEC's sediment ledger
(`DEC-V64-A-sub-M-V64A-D11-CROSS-VAL`). Notion sync at session-end
batch per v2.3 cadence — `notion_sync_status` on the sub-DEC remains
`pending` until main-session reconciles.
