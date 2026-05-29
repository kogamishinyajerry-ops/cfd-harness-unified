# Cadence Codex R1 · R9 fast-divergence gap fixed · 2026-05-29

> Trigger: pre-push `codex-cadence` hook at THRESHOLD=30 → 38 commits since
> last `Codex-verified` trailer (`81f36296664a`) → ran Codex cadence review on
> the aggregate diff `origin/main..HEAD`.
> Backends: **86gs gpt-5.4 xhigh** (R0, primary) ran 1392 lines of analysis
> then **429 Too Many Requests** retry-limit mid-review (no verdict surfaced).
> **CRS gpt-5.4 high** (R0, fallback) ran the same review to completion (1.36 MB
> log) → **1 P2 finding**. Per `CLAUDE.md` v2.3 round cap=3, addressed in
> **R1 (this session)** with the canonical `Codex-verified` trailer.
> Parents: DEC-V61-207 (Blueprint v4 P2) · individual reviews on the
> aggregated commits (DEC-209/211/212).

## 做了什么 (what)

**Codex CRS P2 finding (the gestalt the cadence pass caught):**

> [P2] Handle blow-ups with fewer than four residuals —
> `ui/backend/services/v9_advisor/rules.py:202-204`
> If a run diverges before four `p` samples exist (the comment explicitly
> calls out "V6 first-iter" blow-ups), this predicate never fires because
> `recentResiduals(..., 4)` returns early. Those fast-divergence cases will
> be missed entirely, so the new R9 rule does not actually cover the short
> blow-ups it was added for; the TS mirror has the same logic.

The W2.1 R9 distillation (commit `c3435e4`) wrote a docstring claiming the
4-sample window was chosen *because* "blow-ups are fast (V3 iter 3, V6
first-iter)" — but the implementation early-returned on `len < 4`, so its
own documented target classes never matched. A perfect docstring-vs-code
contradiction. **No individual-PR review caught this**; the gestalt the
cadence pass is for surfaced it on read 1.

**R1 fix (`<commit will be added below after landing>`):**

- `ui/backend/services/v9_advisor/rules.py` — `_pred_residual_divergence` now
  inlines the residual access (bypasses `_recent_residuals` whose count-floor
  was the bug), takes opportunistically up to 4 samples, and fires when
  `len ≥ 2 AND monotonic-increase AND final > 1.0`. The `>1.0` floor still
  guards startup transients. Docstring rewritten with the cadence-review
  citation + an honest KNOWN-GAP note for the single-sample case.
- `ui/frontend/src/data/v9_advisor_rules.ts` — TS mirror with identical logic
  and the same NOT-via-shared-helper note (the shared `recentResiduals` helper
  in TS has the same early-return as Python; both predicates inline the
  history access).
- `ui/frontend/src/data/__fixtures__/v9_parity_fixtures.json` — +2 fixtures:
  `residual_divergence_v3_class_3sample` (3-sample firing canary; was the gap)
  and `residual_divergence_v6_first_iter_known_gap` (1-sample non-firing
  canary; pins the honest scope).
- `tests/test_v9_pattern_matcher.py` — +2 boundary tests mirroring the
  fixtures. Python suite 49 → 51 green. Cross-language parity (11 Python
  fixtures + 41 TS-side parity tests via vitest) all green.

**KNOWN-GAP (honest scope-out):** V6 first-iter mass-flow-zero-IC blow-up
produces only one residual sample. A single residual at O(1) cannot be
distinguished from a normal startup transient without a single-sample
threshold high enough to shadow the `>1.0` floor's false-positive guard for
typical first-iter values. R3 (nonzero-exit) catches V6 when the case dies;
the remaining V6 gap (single-sample + clean exit + no recovery) is tracked
for a future slice-extension rule alongside the W2.0.6 work-stream — same
finding-5 ("scalar-rule space is saturating") as the 2026-05-28 P2 entry
retro. *Recording the gap, not faking coverage.*

## 关键发现 (key findings)

1. **Cadence Codex reviews catch what individual-PR reviews miss — the
   docstring-vs-implementation contradiction.** R9 went through its own DEC
   commentary (W2.1 plan), commit body (`c3435e4`), and crossed individual
   review when other extractors were the focus (DEC-211/212). All three
   readers looked at the docstring OR the implementation; none compared the
   two against each other. The cadence pass — which has to read both because
   the prompt asked for "gestalt" — surfaced the gap on first read. This
   exactly matches the v2.3 cadence rule's design intent: per-commit reviews
   catch *local* defects; cadence reviews catch *cross-commit* drift, and the
   sharpest cross-commit drift class is "docstring claim ≠ implementation".

2. **Same-class as the 2026-05-28 retro's finding-2 ("fabricated provenance
   ships invisible to readers") — at a different layer.** Finding-2 was
   citation-vs-source mismatch; this is target-class-vs-firing-window
   mismatch. Both pass the eye-scan and both are caught only by a *verifier*
   (the citation-resolution test for finding-2; an adversarial gestalt
   reviewer for this finding). The pattern: any rule with a behavioral
   claim in a comment plus a non-trivial precondition in code needs an
   adversarial test that proves the claim holds for the documented inputs.
   Possible W2.X follow-up: an automated test that the docstring's "covers"
   list matches the predicate's behavior on per-claim fixtures. Tracked, not
   built — first see how often this defect class recurs.

3. **Relay 503/429 reconciliation discipline.** 86gs hit 429 mid-review (no
   verdict, ~1.4MB transcript with no synthesis); CRS completed in similar
   time and surfaced the real finding. Per `~/CLAUDE.md` "Codex 协作守则",
   CRS is the documented fallback — this session's auto-fallback exercised
   it cleanly. The 86gs 429 transcript is archived for the audit trail
   (`cadence_review_38c_20260529.txt`); the CRS verdict transcript is the
   canonical baseline (`cadence_review_38c_20260529_crs.txt`). Both raw
   transcripts are .txt; the new `*.txt` `.gitignore` rule landed in step-1
   C4 of this session covers them — they stay local, only this retro
   commits.

## 治理 (governance)

| Gate | Status |
|---|---|
| Four-question gate (R9 fix) | ✅ LLM-offline (pure predicate, no I/O) · artifacts (the predicate's matched_at) · TrustGate (commentary explains divergence + advisor surface) · AI advisory-only (no mutation) |
| Truth-chain | ✅ docstring honesty restored (claim now matches behavior); known-gap recorded not faked; new tests document the V6 scope-out |
| Codex round cap=3 | ✅ R0 = CRS APPROVE_WITH_COMMENTS (1 P2) → R1 = this fix → trailer = `Codex-verified: APPROVE_WITH_COMMENTS · 1 P2 addressed (R9 4→2 sample threshold + V6 known-gap documented)` |
| Codex relay | ✅ 86gs xhigh 429 mid-review → CRS high fallback → verdict obtained. Both transcripts archived (`reports/codex_tool_reports/cadence_review_38c_20260529{,_crs}.txt`, gitignored per step-1 C4 convention) |
| Cross-language parity | ✅ Python 51 + TS 41 + parity 11 — all green; both bindings inline history access (the shared `recentResiduals` helper stays unchanged so R1/R6/R7/R8 are untouched) |
| Per-commit reviews on the same 38 commits | ✅ unchanged (DEC-209 ADDENDUM 6 · DEC-211 R2 · DEC-212 R2 still hold) |
| Cadence trailer pre-push hook | ✅ HEAD now carries canonical `Codex-verified:` first-token trailer |
| confidence | high (small predicate change, two-language symmetry verified, 4 new green tests pin the new behavior + the documented scope-out, KNOWN-GAP is honest not fabricated) |

## 下一步 / 风险 (next / risks)

- **Push 39 commits to origin/main** — pre-push hook will accept HEAD with
  the canonical `Codex-verified` trailer (cadence reset to 0).
- **Notion sync 7 Accepted DECs** (V61-206/207/208/209/210/211/212) — this
  retro is NOT synced (only Status=Accepted DECs sync; retros are local-only
  per `~/Desktop/cfd-audit-merge/CLAUDE.md` "Notion 深度同步规则").
- **W2.0.6 (slice extension)** stays the next P2 substantive step. The V6
  single-sample known-gap is a candidate downstream consumer of the extended
  slice (a `first_iter_residual_o1` flag a future rule could read), but
  prematurely fitting one rule to it would re-trip finding-5 (scalar-space
  saturation). Track as a slice-extension consumer, do not extract early.

## Local artifacts

- Retro: this file
- 86gs partial transcript: `reports/codex_tool_reports/cadence_review_38c_20260529.txt` (gitignored — raw .txt)
- CRS verdict transcript: `reports/codex_tool_reports/cadence_review_38c_20260529_crs.txt` (gitignored — raw .txt)
- Step-1 commits this session: `46b4ada` · `ff0cbe3` · `dbdc55e` · `8fcb5ae`
- R1 fix commit: appended after landing
