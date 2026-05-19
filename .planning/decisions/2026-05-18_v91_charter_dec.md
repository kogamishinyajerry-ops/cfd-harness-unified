---
decision_id: DEC-V91-charter
title: V91 V9 Substantiation Arc · Audit-Package Commentary Sidecar + Python Matcher Port · 14-arc streak target
status: Accepted
parent_dec: DEC-V90-close (2026-05-18_v90_close_dec.md)
phase: V91 (advisor-class arc · 27th in V110 lineage · 5th "CFD能力" verbatim re-issue · V9 substantiate · cohort pattern: verbatim AFTER LAND = substantiate)
notion_sync_status: pending (session-end batch · per v2.3 Accepted-only)
autonomous_governance: true
confidence: med
date: 2026-05-18
---

# DEC-V91-charter · V9 Substantiation · Audit-Package Commentary Sidecar

## TL;DR

V90 LANDED V9 as a pure-presentational frontend surface. V91 substantiates
V9 by closing the **AFTER-RUN axis end-to-end**: the same human-curated
rules that drive the live UI also emit a `commentary/matched.json`
sidecar inside `audit_package.zip`, byte-reproducibly. CFD researchers
who download an audit bundle now see exactly what the Curated Diagnostic
Patterns surface showed at run time — same rules, same provenance, same
matched-text, byte-pinned by HMAC.

This arc is **V9 substantiate**, not V10 LAND, per the 27th-mandate
cohort observation: V86→V87 (V7 LAND→sub) · V88→V89 (V8 LAND→sub) ·
V90→**V91** (V9 LAND→sub). The verbatim "CFD能力" mandate immediately
after a LAND arc consistently means substantiate; immediately after a
substantiate arc consistently means next LAND. Five cohort halves now
support this pattern.

## North Star

Make V9 fully cross-cut the runtime AND the audit trail. Today the
advisor only shows commentary in the frontend at runtime; if a user
downloads an audit package for offline review or compliance archiving,
the matched commentary is lost. V91 closes that gap.

Secondary: extract the rule corpus (commentary text + provenance) into a
JSON SSOT so TS and Python bindings share one source of truth. This
eliminates drift risk between frontend rules and backend rules — a known
hazard of cross-language rule duplication.

Tertiary: extend the V130 BY-CONSTRUCTION discipline class to the
backend sidecar emitter (the Python matcher must be deterministic + pure
+ no I/O beyond reading the manifest dict passed in).

## Scope (4 sub-DECs)

| Sub-DEC | Surface | Bullet | LOC est | Risk |
|---|---|---|---|---|
| **V91.1** | `ui/backend/data/v9_advisor_rules.json` (new) · `ui/frontend/src/data/v9_advisor_rules.ts` (modified · TS imports from JSON) | Extract commentary + provenance into JSON SSOT · TS rebinds to JSON-loaded data with type assertions · contract test asserts byte-identical content | ~80 | low |
| **V91.2** | `ui/backend/services/v9_advisor/pattern_matcher.py` (new) · `ui/backend/services/v9_advisor/__init__.py` · `ui/backend/tests/test_v9_pattern_matcher.py` | Python port of `advisor_pattern_matcher.ts` · pure function · graceful predicate-throw degrade · deterministic severity-sort · 26 contract tests mirror TS fixtures · same byte-identical commentary output as TS | ~250 | med |
| **V91.3** | `src/audit_package/manifest.py` (extend) · `src/audit_package/serialize.py` (extend) · `ui/backend/services/v9_advisor/manifest_adapter.py` (new) | Manifest carries `commentary: list[matched]` field populated from log-tail + measurement parse · `_zip_entries_from_manifest` writes `commentary/matched.json` as canonical JSON · byte-reproducibility test ensures HMAC stays stable across re-emission | ~200 | **med-high** (byte-reproducibility-sensitive — per v2.2 = async post-merge Codex trigger) |
| **V91.4** | Fleet score + DEC-V91-close + retro | Run V78 16-pillar to 2-consec ≥99 · close + retro · 14-arc streak target | (scoring) | low |

**Total est**: ~530 LOC backend + Python tests + minimal frontend rebind
(V91.1's TS side ≤30 LOC of import-rebinding · no logic change).

## V132 lock + 4Q gate

- **V132 endpoints**: 9 unchanged. V91.3 extends `POST /api/cases/{case_id}/runs/{run_id}/audit-package/build` (existing route) — does not add a new mutating route. ✓
- **4Q gate**:
  1. LLM-offline runnable? ✅ Python matcher is pure-function · no LLM call · runs offline
  2. Artifacts emitted? ✅ `commentary/matched.json` inside audit_package.zip · byte-reproducible
  3. TrustGate intact? ✅ HMAC signature continues to cover full zip bytes including new sidecar entry
  4. AI advisory only? ✅ Rules are human-curated; matcher is mechanical pattern-match; provenance cites V-series + textbook

## V130 BY-CONSTRUCTION class extension

V90 established literal-source absence as the strongest V130 class
(advisor surface CAN'T mount a fetch — assertion is over `.tsx` source).
V91 extends this to backend:

- **Pure-function Python matcher**: `pattern_matcher.py` takes a dict + a
  rule list and returns a list. No I/O. No network. No subprocess. No
  filesystem read beyond what the caller passed in. Contract test asserts
  module imports are limited to stdlib + typing.
- **Manifest adapter is read-only over manifest dict**: derives
  RunArtifactSlice purely from `manifest["run"]["outputs"]["solver_log_tail"]`,
  `manifest["measurement"]["key_quantities"]`, `manifest["measurement"]
  ["comparator_verdict"]`. No new data sources.
- **JSON SSOT byte-deterministic**: `v9_advisor_rules.json` is canonical
  JSON (sorted keys, no trailing whitespace, UTF-8) — same content read
  by TS + Python produces identical commentary strings.

## Reverse-stops (NEW in V91)

35. V9.D sidecar matcher MUST NOT add network I/O · subprocess · filesystem
    read beyond manifest-dict argument (grep enforced module-import allowlist
    test on `pattern_matcher.py` and `manifest_adapter.py`)
36. V9.D MUST be byte-reproducible: `serialize_zip_bytes(manifest)` called
    twice on identical manifest dict MUST produce identical bytes including
    new sidecar (extends existing byte-reproducibility test from PR-5c)
37. JSON SSOT MUST be canonical (sorted keys · UTF-8 · trailing newline) —
    contract test asserts `json.dumps(json.loads(file_bytes), sort_keys=True,
    ensure_ascii=False) + "\n" == file_bytes.decode("utf-8")`
38. V91.2 Python matcher's output MUST be byte-identical to V90 TS
    matcher's output given identical RunArtifactSlice fixtures (cross-language
    parity test using a shared fixture file)
39. Manifest adapter MUST gracefully degrade when log_tail parse fails (no
    final_iter, no max_iters_reached) · commentary list returns empty rather
    than crashing manifest build

## Mandate-tracking table (27th-mandate cohort)

| Mandate # | Date | Arc | Class | Closes |
|---|---|---|---|---|
| 16 | (earlier) | V77 | substantiate | (per memory) |
| ... | ... | ... | ... | ... |
| 26 | 2026-05-18 | V90 | V9 LAND | V90 close |
| **27** | **2026-05-18** | **V91** | **V9 substantiate** | **this arc** |

Pattern observation reinforced 6th time (V86→V87, V88→V89, V90→V91 LAND→sub
+ V87→V88, V89→V90 sub→LAND): cohort behavior is now treated as a stable
predictor for V92.

## Risks

- **Byte-reproducibility regression** is the primary technical risk. The
  audit-package zip is HMAC-signed; if matcher output varies even by
  whitespace, signature verification breaks. Mitigation: contract test in
  V91.3 calls `serialize_zip_bytes` 3 times on identical manifest and
  asserts SHA-256 equality across all 3 outputs.
- **Cross-language parity regression**. TS matcher and Python matcher may
  drift in edge cases (number formatting, sort stability). Mitigation:
  V91.2 contract test loads a shared JSON fixture of (slice, expected_output)
  pairs that BOTH bindings must reproduce.
- **Manifest schema break** could invalidate prior bundles. Mitigation:
  `commentary` field is purely additive — old bundles without it remain
  valid; new bundles include it.
- **Codex async post-merge trigger** (per v2.2 byte-repro-sensitive path) —
  plan to invoke `codex-review-relay --base origin/main` post-merge.
  Not a sync blocker.

## Done dim checklist

- [ ] V91.1 rule corpus JSON SSOT landed · TS rebound · contract green
- [ ] V91.2 Python matcher landed · 26 contract tests green · cross-language parity fixture green
- [ ] V91.3 sidecar emission landed · byte-reproducibility verified across 3 emissions · existing audit_package tests green
- [ ] V91.4 V78 fleet 2-consec ≥99 close gate MET · 14-arc no-scoring-change streak ATTAINED
- [ ] V91 close DEC + retro written
- [ ] Task #186-#190 all completed

— DEC-V91-charter · 2026-05-18 · `autonomous_governance: true` · counter +1
