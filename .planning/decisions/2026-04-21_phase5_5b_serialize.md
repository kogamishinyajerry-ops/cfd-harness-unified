---
decision_id: DEC-V61-013
timestamp: 2026-04-21T00:50 local
scope: Path B · Phase 5 · PR-5b · Serialize module. Adds src/audit_package/serialize.py with three outputs from a manifest dict — byte-reproducible zip (PR-5c HMAC target), deterministic semantic HTML (no external CDN), guarded weasyprint PDF (raises actionable PdfBackendUnavailable when native libs missing). No HMAC yet.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
counter_warning: "This DEC lands the v6.1 autonomous_governance counter at 10 — hits the hard-floor-4 review threshold. STOP before PR-5c for Kogami/Codex review."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 abfdfbec` removes serialize.py + tests. manifest.py
  from PR-5a remains intact and has no dependency on serialize.py. No
  consumers exist yet (PR-5c/5d queued). Clean revert.)
notion_sync_status: synced 2026-04-21T01:00 (https://www.notion.so/348c68942bed81f2a3ffc6c8ee088ee6) — Decisions DB page created with Scope=Project, Status=Accepted, Canonical Follow-up=PR #13 URL, counter-warning included in body
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/13
github_merge_sha: abfdfbec0d238cd5ddee9e3bb7cf2d49fbe428f5
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 94%
  (Pure src/ + tests/. 251 passed + 1 skipped. Determinism property
  asserted with SHA-256 equality between two independent invocations.
  HTML-escape safety tested. Minor residual risk: weasyprint PDF output
  might not be strictly byte-identical across invocations due to font
  subsetting / embedded timestamps — not tested here, will be exercised
  in PR-5c HMAC round-trip tests.)
supersedes: null
superseded_by: null
upstream: DEC-V61-012 (manifest builder — provides input dict)
kickoff_plan: .planning/phase5_audit_package_builder_kickoff.md
---

# DEC-V61-013: Phase 5 PR-5b — Serialize (zip + HTML + guarded PDF)

## Decision summary

Second of 4 Phase 5 PRs. Consumes a manifest dict from `build_manifest` and produces three serialized outputs suitable for the audit package:

1. **Byte-reproducible zip** — the machine-verifiable evidence bundle. Identical manifest → identical zip bytes (asserted by SHA-256 equality across two invocations). PR-5c will HMAC-sign this.
2. **Semantic HTML** — deterministic human-readable render with bundled CSS and zero external CDN links. Safe for offline regulatory review. `html.escape`s user-controlled fields (case.id, decision titles).
3. **PDF via weasyprint** — optional, guarded by `is_pdf_backend_available()` probe. On hosts without `pango`/`cairo`/`glib` native libs, `serialize_pdf()` raises `PdfBackendUnavailable` with platform-specific install hints (`brew install weasyprint` on macOS, `apt install libpango-1.0-0` on Debian).

## Zip determinism (HMAC-critical)

```
ZipInfo.date_time        = (1980, 1, 1, 0, 0, 0)   # zip epoch minimum
external_attr            = 0o644 << 16  (files)
                         = 0o755 << 16  (dirs)
create_system            = 3  (UNIX)
compress_type            = ZIP_DEFLATED
compresslevel            = 6  (zlib default)
entry order              = sorted path ascending
allowZip64               = False
zip comment              = (none)
ZipInfo.extra            = (none)
```

Test `test_byte_identical_across_calls` builds two zips from the same manifest and asserts:
- `b1 == b2` (exact byte equality)
- `sha256(b1) == sha256(b2)` (independent hash verification)

## Zip layout

| Path | Content |
|---|---|
| `manifest.json` | Canonical JSON (sort_keys=True, indent=2, UTF-8, trailing `\n`) |
| `case/whitelist_entry.json` | Canonical JSON dump of `manifest.case.whitelist_entry` |
| `case/gold_standard.json` | Canonical JSON dump of `manifest.case.gold_standard` |
| `run/inputs/system/<file>` | Verbatim solver input files (controlDict, blockMeshDict, …) |
| `run/inputs/0/<field>` | Verbatim initial-field files (U, p, T, k, …) |
| `run/outputs/solver_log_tail.txt` | Log tail (bounded at 120 lines by manifest builder) |
| `decisions/<DEC-ID>.txt` | One-line pointer per decision-trail entry |

## HTML render

- **Bundled CSS inline** (no `<link>` tags, no `<script>` tags, no font-family URLs)
- **Deterministic**: two identical manifests → identical HTML bytes (asserted)
- **Safe**: all user-controlled fields escaped via `html.escape`, including XSS-attempt fields in `case.id`
- **Graceful** empty states: no decision trail / no measurement / no audit concerns → renders a gray note instead of blank

Verdict styling via CSS classes `verdict-pass` (green), `verdict-fail` (red), `verdict-hazard` (amber). Caller's `comparator_verdict` is the sole driver.

## PDF (guarded)

Weasyprint is imported lazily. Three failure modes caught:

1. `ImportError` — Python pkg not installed → `pip install weasyprint` hint
2. `OSError` — native libs missing → `brew install weasyprint` (macOS) / `apt install libpango-1.0-0` (Debian) hint
3. Any other exception during weasyprint init → generic "initialization failed" hint

All three raise `PdfBackendUnavailable` with a clear message. `is_pdf_backend_available() -> bool` lets the UI render a "PDF unavailable on this host" badge without exception handling.

On this host: weasyprint native libs are installed. Tests verified PDF renders to a `%PDF`-prefixed file with non-zero size.

## Test surface (+29)

| Class | Count | Covers |
|---|---|---|
| `TestCanonicalJson` | 4 | Sort, newline, UTF-8, byte stability |
| `TestZipBytesDeterministic` | 9 | Byte-identical, layout, mtimes, sort, minimal-manifest survival |
| `TestSerializeZipWriter` | 2 | Path write, parent dir creation |
| `TestRenderHtml` | 12 | Content, verdict styling (×3), legacy ids, determinism, no-CDN, escape, empty states |
| `TestPdfBackendAvailability` | 3 | Bool probe, skipif-guarded raise-path + render-path |

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` | YES — new `serialize.py` in existing `src/audit_package/` |
| `tests/` | YES — 29 new tests |
| `knowledge/**` | NOT TOUCHED |
| Notion DB destruction | NOT TOUCHED |

## Regression

```
pytest 8-file matrix (including tests/test_audit_package) → 251 passed + 1 skipped in 1.58s
```

1 skip is `test_serialize_pdf_raises_when_unavailable` — unreachable on this host where weasyprint works. On hosts without weasyprint native libs, that test runs and `test_serialize_pdf_writes_file_when_available` skips instead.

## Counter status — **HARD-FLOOR-4 THRESHOLD REACHED**

v6.1 autonomous_governance counter: 9 → **10**. This is the v6.1 trigger for a mandatory self-review-of-autonomy + optional external review before further autonomous DECs. Per `CLAUDE.md` and session handoff §7, the discipline is:

1. **PR-5c should go through Codex tool review** (`codex` CLI on the diff) — HMAC signing is security-critical and deserves independent eyes regardless of counter.
2. Kogami should confirm the 5 open design questions are still OK given what landed in PR-5a/5b (PDF library choice validated; HMAC key management still to-be-designed in PR-5c).
3. After PR-5c lands, counter is 11 — continue review discipline for PR-5d.

**Action**: the driver will pause before starting PR-5c to ping Kogami. If Kogami green-lights auto-proceed with Codex review, driver will invoke `codex review` on the PR-5c diff before merging.

## Reversibility

One `git revert -m 1 abfdfbec` removes `serialize.py` + `tests/test_audit_package/test_serialize.py`. `manifest.py` from PR-5a remains intact — it has no dependency on serialize. No consumers exist yet (PR-5c uses `_canonical_json` + `serialize_zip_bytes`; PR-5d uses all of the above — neither landed).

## Next steps

1. Mirror this DEC to Notion.
2. Update STATE.md.
3. **STOP** — ping Kogami for Codex review invocation strategy before PR-5c.
