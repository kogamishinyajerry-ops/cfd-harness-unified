# Phase 5 — Audit Package Builder (kickoff plan, not implementation)

**Status**: PLAN — execution deferred to a dedicated session
**Author**: claude-opus47-app (Sole Primary Driver under v6.1)
**Date**: 2026-04-20T23:10
**Upstream**: DEC-V61-002 (Path B Phase 5 was elected) · DEC-V61-003 (Phase 0–4 landed) · DEC-V61-010 (C3 complete)
**Blockers**: Q-2 R-A-relabel (see `.planning/gates/Q-2_r_a_relabel.md`)

---

## Why this is a plan, not a build

Phase 5 is the commercial differentiator of Path B (per DEC-V61-002): a one-click export that packages a CFD case's full V&V evidence (inputs + gold + run + measurement + decisions + commits + HMAC signature) into a signed zip + PDF. This is significantly larger than the Phase 1–4 scope each one fit in a rolling branch. Phase 5 deserves its own dedicated session with Kogami's full attention on scope decisions.

This plan enumerates the sub-PRs, their dependencies, the gate interactions, and the open design questions so the next session can execute linearly.

---

## What DEC-V61-002 promised

> Phase 5 · Screen 6 Audit Package Builder (one-click export: zip + signed PDF bundling case + gold + run + measurement + audit_concern + decision trail + commit SHA + HMAC signature) · `feat/ui-mvp-phase-5-audit-package` · Export produces byte-reproducible zip from fixed inputs · PDF renders without external CDN · HMAC verifiable from documented procedure · FDA V&V40 reviewer checklist mapping in audit-package README

---

## Why Q-2 blocks Phase 5

DEC-V61-002: "Phase 5 cannot ship signed audit packages while two known gold-accuracy / whitelist-correctness issues are open."

Q-1 closed via DEC-V61-006 Path P-2. Q-2 remains open. Shipping a signed audit bundle that includes `fully_developed_pipe` (labeled as a pipe but actually a duct, per Q-2) means either:
- the signature covers inconsistent metadata (bad faith), OR
- the packaging code has to silently exclude Case 5 (silent scope reduction is worse than an honest gate)

Q-2 must close (any path) before Phase 5 can honestly emit packages that cover all 10 whitelist cases.

---

## Proposed Phase 5 sub-PR decomposition

Split into 4 sequential PRs. Each is independently reviewable and revertible.

### PR-5a — Manifest builder (core, no UI)

**Scope**: `src/audit_package/manifest.py` (new). Pure-function API:

```python
def build_manifest(case_id: str, run_id: str, repo_root: Path = REPO_ROOT) -> dict:
    """Collect ordered evidence for a case run into a canonical dict."""
```

Returns a deterministic dict containing:
- Case metadata (whitelist entry verbatim, pinned by git commit SHA)
- Gold standard file verbatim (pinned by git commit SHA)
- Run inputs: controlDict / blockMeshDict / fvSchemes / fvSolution / 0/ initial fields
- Run outputs: log file tail, residual convergence, postProcessing sets/ output
- Measurement: key_quantities dict from comparator
- Audit concerns: any HAZARD/FAIL flags + reason codes
- Decision trail: all DEC-V61-* referenced by the case (via git log grep)
- Git commit SHA at run time
- Timestamp (ISO-8601 UTC)

No HMAC yet — PR-5a builds the manifest; PR-5c signs it.

**Tests**: synthetic fixtures for each case archetype; assert dict is byte-stable across two identical runs.

**Estimated**: ~150 LOC + 80 LOC test = ~230 LOC.

### PR-5b — Zip + PDF serializer

**Scope**: `src/audit_package/serialize.py` (new).

```python
def serialize_zip(manifest: dict, output_path: Path) -> None:
    """Deterministic zip — ordered files, fixed mtimes, no metadata."""

def serialize_pdf(manifest: dict, output_path: Path) -> None:
    """Static PDF via weasyprint or reportlab — zero external CDNs."""
```

Design decisions needed:
- PDF library: weasyprint (Python, full CSS support, bundled) vs. reportlab (lower-level, more deterministic). **Recommend weasyprint** — the PDF is meant to be human-readable evidence for regulators, not a machine-consumed artifact. CSS styling matters.
- Deterministic zip: set all file mtimes to epoch-zero, order files by canonical path, no system metadata. OpenFOAM's postProcessing/ can contain non-deterministic timestamps — those need normalization before packaging.

**Tests**: identical input → byte-identical zip. PDF renders to PNG and compares pixel-diff within 1% to golden fixture.

**Estimated**: ~250 LOC + 150 LOC test = ~400 LOC.

### PR-5c — HMAC signer + verifier

**Scope**: `src/audit_package/sign.py` (new).

```python
def sign(manifest: dict, zip_path: Path, hmac_secret: bytes) -> str:
    """Sign the (manifest + zip file bytes) with HMAC-SHA256; return hex."""

def verify(manifest: dict, zip_path: Path, signature: str, hmac_secret: bytes) -> bool:
    """Reconstruct signature, constant-time compare."""
```

Design decisions needed:
- HMAC key source: environment variable `CFD_HARNESS_HMAC_SECRET` at runtime; public docs explain rotation procedure. **Absolutely must NOT commit any secret.**
- What goes into the HMAC input: `manifest_canonical_json || zip_bytes`. Canonical JSON means sorted keys, UTF-8, no whitespace.
- Verification is runtime-only: the zip ships with signature in a sidecar `.sig` file; users with the HMAC secret + the documented procedure can verify.

**Tests**: round-trip sign → verify; tamper-detection (flip one byte, verify fails); constant-time compare test.

**Estimated**: ~100 LOC + 80 LOC test = ~180 LOC.

### PR-5d — Screen 6 UI + API route

**Scope**: `ui/backend/routes/audit_package.py` (new) + `ui/frontend/src/pages/AuditPackagePage.tsx` (new).

Backend:
- `POST /api/cases/:case_id/runs/:run_id/audit-package` → builds + signs + returns download links

Frontend:
- Screen 6 in the nav. Per-case "Build Audit Package" button → progress spinner → download links for zip + PDF + .sig
- Display the FDA V&V40 checklist mapping inline (each check ↔ manifest field)

**Tests**: route tests mock the manifest builder; frontend tests use Playwright to click button + verify download.

**Estimated**: ~200 LOC backend + ~250 LOC frontend + ~150 LOC test = ~600 LOC.

### Total Phase 5 estimate: ~1,400 LOC across 4 PRs

---

## Dependencies + sequencing

```
Q-2 resolution (ANY path)
   ↓
PR-5a (manifest)  ────┐
                      ├──→  PR-5c (sign)  ──┐
PR-5b (serialize) ────┘                     ├──→ PR-5d (UI)
                                            │
                 (can parallel-land with)───┘
```

PR-5a and PR-5b are parallelizable. PR-5c depends on both. PR-5d depends on all three + Q-2 resolution (so the UI doesn't ship a broken case in the bundle).

Total session estimate: 2–4 days of focused execution once Q-2 is resolved.

---

## Open design questions (need Kogami decision before starting)

1. **PDF library** — weasyprint vs. reportlab. Default: weasyprint.
2. **HMAC key rotation procedure** — environment variable + docs, or a more formal key-management story?
3. **FDA V&V40 checklist mapping** — do we map all 8 V&V40 areas (applicability, credibility goals, etc.) or a subset? Default: all 8.
4. **Screen 6 UX pattern** — single-case export vs. batch-export-all-cases? Default: single-case for Phase 5; batch in Phase 6.
5. **Pre-merge demo** — do we want a live demo PR build (sample zip + PDF in a test repo) before merging to main? Default: yes, as a PR reviewer artifact.

---

## Current Phase 0–4 status (context)

| Phase | Status | PR | Notes |
|---|---|---|---|
| 0 | ✅ LANDED | PR #2 | FastAPI + Vite + Screen 4 Validation Report |
| 1 | ✅ LANDED (rolling) | PR #3 | Case Editor |
| 2 | ✅ LANDED (rolling) | PR #3 | Decisions Queue Kanban |
| 3 | ✅ LANDED (rolling) | PR #3 | Run Monitor (synthetic SSE — real OpenFOAM invocation is Phase 5 scope) |
| 4 | ✅ LANDED (rolling) | PR #3 | Dashboard 10-case matrix |
| 5 | 🔒 PLANNED (this doc) | — | Blocked on Q-2 |

---

## Non-goals for the Phase 5 kickoff session

- Real-OpenFOAM dashboard validation (`§5d` in kickoff handoff) — orthogonal, awaiting Docker.
- C3 follow-up / Option A upgrades — C3 is complete per DEC-V61-010.
- Case 9/10 literature re-source — HOLD pending paper access.

---

## Handoff instructions for the next driver

1. Read this doc + `.planning/gates/Q-2_r_a_relabel.md`.
2. Confirm Q-2 has been decided by Kogami (any path A/B/C — not D).
3. If approved: land Q-2 per the chosen path first (~4-6 files, one PR, no Phase 5 touches yet).
4. Then start Phase 5 PR-5a (manifest builder) per the decomposition above.
5. Resolve the 5 open design questions with Kogami before PR-5a lands.
6. Expect 2–4 days end-to-end for the 4 Phase 5 PRs.

Phase 5 DECs are earmarked as **DEC-V61-012, -013, -014, -015** (one per PR) — DEC-V61-011 is reserved for the Q-2 resolution itself.

---

## Autonomy considerations

Phase 5 is autonomous turf (no `knowledge/gold_standards/` touches, no `whitelist.yaml reference_values` touches once Q-2 is done). PRs can self-sign. But the scale (~1,400 LOC) exceeds the sort of "small autonomous PR" pattern established by DEC-V61-003. Recommend: each sub-PR gets its own DEC with Codex tool review (`/codex:review`) invoked once per PR to catch blind spots the driver missed. Record each Codex report under `reports/codex_tool_reports/` per v6.1 留痕 convention.

---

**End of kickoff plan.** This doc is a living reference — the executing driver should update it with actual PR URLs and merge SHAs as Phase 5 sub-PRs land, or supersede it with a Phase-5-complete report.
