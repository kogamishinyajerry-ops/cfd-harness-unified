# Plane-Guard Dogfood Window 5/9 Review Template

> **Purpose**: Drive the W4 toggle PR GO/NO-GO decision per ADR-002 §5 + Opus G-9 binding 2 (target ≤ 2026-05-11).
>
> **Authority**: ADR-002 §5 W4 stage-1 timeline · OPS-2026-04-25-001 §7 · RETRO-V61-006 baseline anchor (`reports/plane_guard/baseline_2026-04-25.md`).
>
> **Window**: 2026-04-25 → 2026-05-09 (≥5 days · Opus risk-buffer).

## Pre-flight (do first · 5 min)

- [ ] CI infrastructure healthy: `gh run list --limit=5` shows recent runs are NOT all failing on `numpy` / `jinja2` import errors. (RETRO-V61-006 deps fix landed 2026-04-25; if CI is broken again, deferred fix BEFORE doing dogfood review.)
- [ ] Verify last successful CI run head SHA matches `git rev-parse origin/main`.
- [ ] Confirm `.github/workflows/ci.yml` "Plane-guard WARN-mode dogfood" step exists and is non-blocking (`continue-on-error: true`).

## Step 1 · Aggregate dogfood artifacts (10 min)

> **CRITICAL · Gap #6 distinction (RETRO-V61-006 audit Item a)**: an empty `.jsonl` artifact has TWO possible meanings:
> - **(a)** the dogfood pytest ran cleanly with zero plane-guard violations (correct interpretation, "0 incidents = GO")
> - **(b)** the dogfood pytest never executed (e.g., import error before pytest collection) → "0 incidents" is an artifact of process death, not a real signal
>
> The W4 prep arc had this exact ambiguity from 2026-04-25T00:00 to 2026-04-25T20:50 (40 consecutive CI failures with empty .jsonl artifacts that would have read as "0 incidents = GO" without further verification).
>
> **Mandatory pre-aggregation check**: every artifact's `ci_warn_pytest.log` MUST show `<N> passed` (process actually ran) before its `.jsonl` count is admitted as evidence. An artifact missing `ci_warn_pytest.log` OR showing pytest collection error is INDETERMINATE, not "0 incidents".

```bash
# Step 1a: List all CI runs since the FIRST genuine dogfood signal anchor (commit 0229af9 · 2026-04-25T06:55)
# CI runs before 0229af9 are instrumentation-only (numpy/jinja2 missing) and MUST be excluded
gh run list --created='>=2026-04-25T06:55' --limit=200 --json databaseId,headSha,conclusion,createdAt > /tmp/dogfood_runs.json

# Step 1b: Download artifacts for each completed run (success OR failure — the dogfood pytest step has continue-on-error: true so a failed overall run may still have the dogfood artifact)
mkdir -p /tmp/dogfood_artifacts
python3 -c "
import json, subprocess, os
runs = json.load(open('/tmp/dogfood_runs.json'))
for r in runs:
    if r['conclusion'] in ('success', 'failure'):
        rid = r['databaseId']
        sha = r['headSha'][:7]
        os.makedirs(f'/tmp/dogfood_artifacts/{sha}', exist_ok=True)
        try:
            subprocess.run([
                'gh', 'run', 'download', str(rid),
                '-n', f'plane-guard-dogfood-{r[\"headSha\"]}',
                '-D', f'/tmp/dogfood_artifacts/{sha}',
            ], check=True, timeout=60)
        except Exception as e:
            print(f'  skip {sha}: {e}')
"

# Step 1c: Gap #6 sanity — only artifacts whose ci_warn_pytest.log shows '<N> passed' are valid
mkdir -p /tmp/dogfood_validated
for d in /tmp/dogfood_artifacts/*/; do
  sha=$(basename "$d")
  log="$d/ci_warn_pytest.log"
  if [ ! -f "$log" ]; then
    echo "INDETERMINATE $sha: ci_warn_pytest.log missing"
    continue
  fi
  if ! grep -qE "[0-9]+ passed" "$log"; then
    echo "INDETERMINATE $sha: pytest did not report passed (likely collection error)"
    continue
  fi
  # Valid run — copy .jsonl files (or note absence as 0-incidents)
  cp "$d/"*.jsonl /tmp/dogfood_validated/ 2>/dev/null || echo "  $sha: 0-incident clean"
done

# Step 1d: Aggregate validated jsonl
find /tmp/dogfood_validated -name 'fixture_frame_confusion.jsonl' -exec cat {} \; \
  > /tmp/dogfood_aggregated_ffc.jsonl
find /tmp/dogfood_validated -name 'sys_modules_pollution.jsonl' -exec cat {} \; \
  > /tmp/dogfood_aggregated_smp.jsonl

echo "----- Validated dogfood signal -----"
echo "fixture_frame_confusion lines: $(wc -l < /tmp/dogfood_aggregated_ffc.jsonl)"
echo "sys_modules_pollution lines:   $(wc -l < /tmp/dogfood_aggregated_smp.jsonl)"
echo "INDETERMINATE runs (excluded from decision): $(grep -c INDETERMINATE <(grep INDETERMINATE /tmp/dogfood_aggregated_*.jsonl 2>/dev/null) || echo 0)"
```

## Step 2 · Run rollback evaluator (2 min)

```bash
python scripts/plane_guard_rollback_eval.py \
  --log-path /tmp/dogfood_aggregated_ffc.jsonl

# Expected: "OK: 0 fixture-frame confusion incidents in last 14d (threshold 3)"
# Acceptable: ≤2 incidents (below threshold but worth investigation)
# BLOCKER: ≥3 incidents (§2.4 trigger fires; opens follow-up DEC per spec)
```

## Step 3 · Decision matrix

| Aggregated incidents | Decision | Action |
|---|---|---|
| **0** | ✅ GO | Land W4 toggle PR (one-line `continue-on-error: true → false`). Tag `[line-a]`. Update OPS §7 + ADR-002 §5 timeline. |
| **1-2** | ⚠️ INVESTIGATE | Read each incident's `test_path` + `source_module` + `target_module`. If all are test-allowlist legitimate exercises → false positives, GO with `--threshold 5` override + RETRO addendum. If any are real production-path violations → defer toggle, open DEC-V61-XXX for plane re-classification. |
| **≥3** | 🛑 §2.4 TRIGGER | Per ADR-002 §2.4 spec: human-driven follow-up DEC opens within 1 week. **Do NOT** land W4 toggle PR. RETRO-V61-XXX captures Option A→B rollback decision. Re-evaluate ADR-002 plane assignment. |

## Step 4 · If GO · W4 toggle PR (10 min)

The PR is intentionally minimal — single `continue-on-error: true → false` line + commit message + Notion sync.

### Commit message draft

```
ci(plane-guard): W4 hard-fail toggle · ADR-002 §5 final flip [line-a]

Closes Opus G-9 binding 2 (W4 hard-fail toggle PR target ≤ 2026-05-11).
Dogfood window 2026-04-25 → 2026-05-09 produced 0 fixture-frame
confusion incidents across N CI runs; baseline anchor
reports/plane_guard/baseline_2026-04-25.md confirmed expected 0/0.

Single-line change: .github/workflows/ci.yml "Plane-guard WARN-mode
dogfood" step continue-on-error: true → false. PR-time forbidden
plane-crossing imports now block the build. CI runs already produce
the proper artifacts via plane_guard_rollback_cron.yml weekly cron;
this commit just makes signals enforced rather than observed.

Verification:
  * gh run list --created='>=2026-04-25' aggregated 0 incidents in
    /tmp/dogfood_aggregated_ffc.jsonl over N runs (see review at
    .planning/dogfood/2026-05-09_review.md)
  * scripts/plane_guard_rollback_eval.py --log-path <agg> exits 0
  * Local pytest with CFD_HARNESS_PLANE_GUARD=on still passes
    (production behavior already validated via dogfood)

Refs:
  * ADR-002 §5 W4 hard-fail timeline row updated to LANDED
  * OPS-2026-04-25-001 §7 W4 toggle deadline closed
  * RETRO-V61-006 baseline anchor

Per RETRO-V61-001 verbatim 5/5 exception eligibility (≤20 LOC,
1 file, no public API surface change, references review log) — no
Codex round required for the toggle flip itself; Codex audit window
reset begins after this commit.

Self-estimate: 0.70 (binding cap per RETRO-V61-006 audit Item b ·
MP-C-revised cap 0.70 for instrumentation+CI-workflow PRs ·
combined with stair-anchor probationary drop 0.85 the binding cap
is min(0.85, 0.70) = 0.70). A clean Codex APPROVE on this PR
auto-recovers stair-anchor 0.87 ceiling per Opus 4.7 audit Item c.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Notion sync after toggle lands

- ADR-002 page: append "W4 toggle LANDED · 2026-05-XX (commit YYYYYY)" block
- OPS-2026-04-25-001 page: flip W4 toggle row from PENDING to LANDED
- Decisions DB: no DEC required (pure timeline closeout, no new governance commitment)

## Step 5 · Persist review record

After completing review, copy this template to `.planning/dogfood/2026-05-09_review.md` (drop `_template`), fill in actual numbers / observations / decision, and commit `[line-a]`. The template stays clean for any future dogfood-window pattern reuse.

## Failure-mode pre-mortem (for use during review)

If aggregated incidents are unexpected, check these in order:
1. **CI infrastructure regression** — did some commit break pytest collection again? (numpy/jinja2 went missing? new test failure that taints the WARN run?)
2. **Test pollution leak** — did MP-2026-04-25-D's session-tmp redirect get reverted in `tests/conftest.py`? (Verify via `grep -n "_find_repo_root" tests/conftest.py`.)
3. **Path resolution regression** — did F3 fix in `_resolve_jsonl_path` get reverted? (Verify via inspecting `src/_plane_guard.py:_find_repo_root` exists.)
4. **A18 wiring regression** — did F1 fix in `find_spec` bypass path get reverted? (Verify via `grep -n "record_fixture_frame_confusion" src/_plane_guard.py` shows callsite around line 480-510.)
5. **Real plane-crossing import added during window** — read each incident's `target_module`; check if line B added a forbidden import that tests caught.

## Cross-references

- `docs/adr/ADR-002-four-plane-runtime-enforcement.md` §5 timeline
- `.planning/ops/2026-04-25_dual_track_plan.md` §7
- `.planning/retrospectives/2026-04-25_retro_w4_prep_r1_incident.md` (RETRO-V61-006)
- `reports/plane_guard/baseline_2026-04-25.md` (baseline anchor)
- `.github/workflows/plane_guard_rollback_cron.yml` (weekly cron)
- `scripts/plane_guard_rollback_eval.py` (evaluator CLI)
