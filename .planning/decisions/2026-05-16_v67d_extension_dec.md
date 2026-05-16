---
decision_id: DEC-V67-D-extension
title: V67-D extension · manifest scope 10 → 389 files (DEC + methodology + SDK) · multi-OS CI matrix (ubuntu + macos) · Pillar 4 86 → 91
status: Accepted
parent_dec: DEC-V67-D-close
phase: V67-D
notion_sync_status: pending
predecessor: DEC-V67-D-close
batch: B116
confidence: high
autonomous_governance: true
verdict: SPIKE_CLASS_EXTENSION
v_row_landed: V109 2nd witness (canonical manifest method-class · 2nd application = full project audit trail coverage)
substrate: scripts/eval/build_canonical_manifest.py (config edit · TRACKED_DIRS expanded) · .github/workflows/eval-set-integrity.yml (matrix added) · 389 file manifest
---

# DEC-V67-D-extension · manifest scope + multi-OS CI matrix

## 1 · Decision

Extend V67-D Pillar 4 work in spike-class scope (≤30 LOC delta · 0 schema breaks · 0 new abstractions):

1. **Manifest scope expansion**: TRACKED_DIRS extended from `[evals/canonical, evals/runs]` (10 files) to also include `[planning/decisions, planning/methodology, planning/sdk]` (389 files total · +379 files)
2. **CI multi-OS matrix**: workflow `eval-set-integrity.yml` runs on both `ubuntu-latest` and `macos-latest` for true multi-machine byte-repro verification

## 2 · Why spike-class scope per v2.3

- LOC delta: 8 LOC manifest edit + 8 LOC workflow matrix edit = 16 LOC
- Schema breaks: 0 (existing manifest format unchanged · existing workflow trigger unchanged)
- Contract breaks: 0 (consumers still read MANIFEST.sha256 same way)
- Tests: 1 (verifier passes after rebuild · 389 files)
- Confidence: high
- Decision: per v2.3 spike-class rule, single-DEC charter+close on commit-message-quality narrative

## 3 · Pillar 4 advance gauge

Per scoring framework v1.0 Pillar 4 anchors:
- **85-100 zone**: "CI gates pass on every PR · byte-repro across multi-machine · canonical manifest validated"

Post-V67-D base anchor application: 78 → 86 (+8 raw, achieving "CI gate" + "byte-repro contract" + "manifest validated" partial).

V67-D-extension delivers the **remaining 85-100 zone components**:
- ✓ "multi-machine" → CI matrix ubuntu + macos
- ✓ Canonical manifest now covers 389 files (governance audit trail · advisor rules · SDK doc all byte-tracked)
- Still NOT fully delivered: 95+ requires "automated rebuild + verification" semantics (CI workflow runs verify only, not rebuild-and-compare cycle)

Anchor application: **86 → 91** (+5 raw). Reaches 90+ zone of "CI gate + multi-machine + manifest validated" all present.

## 4 · V109 2nd witness LANDED

V109 method-class V-row gets 2nd witness via this extension:
- **1st witness (V67-D close)**: 10-file eval set manifest with SHA-256 + structural verifier + single-OS CI
- **2nd witness (V67-D extension)**: 389-file project manifest covering DEC corpus + methodology + SDK + multi-OS CI matrix

Per V-series 3-criterion gate: 2 witnesses now satisfy the witness count requirement. V109 LANDS more firmly as method-class V-row.

## 5 · Score delta

| Pillar | Pre | Post | Δ raw | Weight | Δ weighted |
|---|---|---|---|---|---|
| 4 Reproducibility | 86 | 91 | +5 | 0.10 | +0.50 |
| 2 Corpus depth | 89 | 90 | +1 (V109 2nd witness · method-class) | 0.20 | +0.20 |
| 5 Governance | 89 | 89 | 0 (no new anti-inflation evidence) | 0.10 | 0 |
| **Total** | **74.60** | **75.30** | | | **+0.70** |

**Weighted advance**: 74.60 → **75.30** (+0.70).
**Distance to 95**: 20.40 → **19.70**.

## 6 · Anti-inflation discipline

- ✗ Did NOT claim Pillar 4 to 95: anchor "automated rebuild + verification" still not implemented
- ✗ Did NOT claim V109 LANDED as advisor-class (still method-class · different V-corpus track)
- ✗ Did NOT inflate Pillar 5: spike-class extensions don't accumulate governance evidence beyond what discipline already shows
- ✓ Tracking 389 files honestly — actual count from verifier output, not estimated
- ✓ +5 raw Pillar 4 within anchor language band

## 7 · v2.3 compliance

- DEC scope: spike-class single-DEC per v2.3 round-1 loosening
- LOC: 16 (within ≤30 spike threshold)
- Schema: unchanged
- Codex 1-sync-trigger: NOT triggered (no security boundary touched · workflow yaml extension is config not security)
- Kogami opt-in: NOT invoked
- Notion sync: pending session-end batch

## 8 · 4Q gate

| Q | A |
|---|---|
| LLM offline | ✓ (pure Python stdlib + yaml) |
| Artifacts | ✓ (manifest 389 · matrix workflow · verifier rerun) |
| TrustGate | ✓ (verifier output enumerates all 389 hashes pass/fail) |
| AI advisory-only | ✓ |

— Claude Code (Opus 4.7 1M) · B116 · V67-D extension spike · 2026-05-16
