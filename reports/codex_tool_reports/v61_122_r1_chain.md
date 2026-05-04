# DEC-V61-122 · Mesh-quality adviser foundation · Codex pre-merge chain

**Backend**: CRS `gpt-5.4` high (default per V61-119 §L2 protocol; 86gs not attempted)
**Trigger**: RETRO-V61-001 multi-file backend + new operator endpoint + AI-system-prompt extension triggers
**Scope**: 9 files · ~700 LOC across new `services/mesh_quality/` package (analyzer + schemas + __init__), new `routes/mesh_quality.py`, extensions to `services/llm_coach/prompts.py` and `routes/ai_coach.py`, registration in `main.py`, and 3 test files (new analyzer + new route + extended llm_coach)
**Self-estimated pass rate**: 65% (predicted 2-3 rounds)
**Actual**: 2 rounds — within prediction; V1 scope-down (no Docker, no skewness/orthogonality, no remediation tool, no frontend card) collapsed the surface to two pure-analyzer findings

---

## Round-by-round summary

| Round | Commit | Findings | Severity | Verdict | Backend |
|---|---|---|---|---|---|
| R1 | 150fe3e | 2 | P1 + P2 | CHANGES_REQUIRED | CRS gpt-5.4 high (retry after one transient skill-resolution interrupt) |
| R2 | 7b368dd | 0 | — | **APPROVE clean** | CRS gpt-5.4 high |

---

## Round 1 · CHANGES_REQUIRED · 1 P1 + 1 P2

- **P1 · symlink-escape via plain `read_text()` in analyzer.** The new `analyze_mesh_quality` opened `polyMesh/{points,owner,neighbour,boundary}` with `Path.read_text()`, which silently follows symlinks. A planted symlink at any of those paths would let the operator endpoint (and via the AI-coach prefetch, the LLM's system prompt) read arbitrary host files outside `IMPORTED_DIR`. The project's reference containment helper is `services.case_manifest.locking._open_or_create_lock_fd` — `os.open(O_RDONLY|O_NOFOLLOW)` + `os.fstat`/`os.read`, ELOOP errno mapped to a structured failing_check. **Fix**: introduced `_read_text_no_symlink(path, *, failing_check)` matching the V108 locking-module pattern; ELOOP raises `MeshQualityParseError(failing_check="symlink_escape")` so the route surfaces a stable detail. All four polyMesh files now route through the safe reader. Test: symlink planted at `points` → `MeshQualityParseError(failing_check="symlink_escape")`.

- **P2 · only `points` validated declared count vs parsed entries.** `_split_foam_block` parses the header count and the body, but `analyze_mesh_quality` only checked `declared_pt_count == len(parsed_points)`. Owner / neighbour / boundary accepted truncated bodies — an aborted gmshToFoam or partial-write scenario could produce a 200 with `cell_count = max(parsed_owner_subset)+1` (clearly wrong) and an undersized `patch_face_counts` map. The DEC documents "corrupt file → 500", but the implementation didn't enforce that on three of four files. **Fix**: renamed `_max_int_in_body` → `_parse_int_body` returning the full integer list. Owner now validates `owner_face_count == len(owner_entries)` → `owner_count_mismatch`; neighbour → `neighbour_count_mismatch`; boundary's `_read_patch_face_counts` validates the declared header count against parsed patches → `boundary_count_mismatch` (only when the header is present, since some boundary files omit the count header). Tests: 3 truncated-body fixtures, one per file, each producing the matching `failing_check`.

## Round 2 · APPROVE clean · 0 findings

**Backend**: CRS `gpt-5.4` high. Verbatim verdict (Codex):

> "The change closes the documented symlink-following and truncated-block cases without introducing a clear regression in the analyzer's happy path or route behavior. I didn't find a discrete, actionable bug that would reliably break existing usage."

86gs not attempted on R1 or R2 — V61-119 §L2 default-to-CRS protocol continues to apply. R1 hit a single transient skill-resolution interrupt that resolved on retry without further fallback.

---

## Methodology lessons

### L1 · V1-scope-down anti-cascade pattern · 4 consecutive arcs at ≤3 rounds

V119 (1 round APPROVE), V120 (1 round APPROVE), V121 (2 rounds), V122 (2 rounds). The pattern — explicit DEC scope-down with deliberately-excluded axes pushed to successor DECs — has now held across 4 consecutive arcs. V122's prediction (65% / 2-3 rounds) calibrated to the actual outcome within the lower bound. The pattern is no longer experimental; treat as the default DEC discipline going forward.

### L2 · Reuse of project's reference containment helpers

V122 P1 was caught because the analyzer was new code that didn't yet use the project's containment idioms. The `services.case_manifest.locking` module documents the `O_NOFOLLOW + ELOOP → symlink_escape` contract. New top-level operator-facing readers should adopt this pattern by default; reviewers should grep for `Path.read_text()` / `Path.read_bytes()` in any new operator endpoint as a routine pre-Codex pass.

### L3 · Declared-count-vs-parsed-count is a per-file invariant

V122 P2 caught that the original implementation extended the count-validation only to the points file. The lesson generalizes: every parens-list-with-header file in the polyMesh family (and analogous formats elsewhere) MUST validate the declared count against the parsed entry count. A single point of validation in one file but not the siblings is a classic same-class-different-file omission. The fix's symmetric application across owner / neighbour / boundary is the correct discipline.

---

## Counter / governance

- counter +1 (V122 = 81 pre-Notion, autonomous_governance: true)
- Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter 80→81 (counter ≥ 20 trigger continues to be deferred per ongoing user mandate "按你的顺序和建议，继续推进"), not governance-rule change → Kogami **NOT** triggered
- Notion sync: pending (MCP server still disconnected since V119; V118-V122 all carry `notion_sync_status: pending`)
- Self-pass-rate calibration: predicted 65% / 2-3 rounds; actual 2 rounds — within prediction band, no calibration adjustment needed

## Anchor

R2 APPROVE-clean commit: `7b368dd`
