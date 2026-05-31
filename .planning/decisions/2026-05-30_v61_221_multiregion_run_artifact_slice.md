---
decision_id: V61-221
title: multi-region RunArtifactSlice extension (RegionSlice + CoupledPatch) — P3 W3.0.6 sub-DEC
status: Accepted
parent_dec: V61-217
phase: P3 (Blueprint v4 · CHT)
autonomous_governance: true
confidence: high
kogami_opt_in: false
round_cap: 3
codex_review_relay: 86gs gpt-5.4 xhigh (R0+R1) → CRS gpt-5.4 high (R2; 86gs R2 hung/killed, fallback per DEC-V61-214; effort xhigh→high on R2 noted)
codex_verdict: APPROVE at R2 (clean gate, within cap=3) — R0 1×P2 (TS parity mirror) + R1 2×P3 (test hygiene; R1 explicitly found NO production regression) fixed+verified; R2 found no bug. No overflow record needed.
codex_tool_report_path: reports/codex_tool_reports/v61_221_chain_report.md
notion_sync_status: synced 2026-05-31 (https://www.notion.so/371c68942bed8100bf9dc83739c37b45)
touches_shared_dec: V61-215 (RunArtifactSlice base contract in pattern_matcher.py — extended additively, mirroring its W2.0.6 nested-dataclass pattern)
sibling_dec_contract_for: V61-217 W3.1 (CHT rule distillation consumes RunArtifactSlice.regions — schema frozen here)
---

# DEC-V61-221 · multi-region RunArtifactSlice extension for CHT (P3 W3.0.6)

## Context

DEC-V61-217 W3.0.6 — the multi-region extension of `RunArtifactSlice`
(DEC-V61-215), the fourth and final P3-prep item. Depends on **all four** of
{W3.0 (DEC-V61-218), W3.0.1 (DEC-V61-219), W3.0.2 (DEC-V61-220), W3.0.3 (spike)},
all now LANDED. The charter flags W3.0.6 **"MUST land BEFORE any CHT rule
distillation"** (W3.1) — the slice is the frozen contract W3.1's rules consume.

Surface scan (V61-088): `RunArtifactSlice` is a frozen dataclass in
`ui/backend/services/v9_advisor/pattern_matcher.py` (DEC-V61-215, W2.0.6 added 3
optional nested-dataclass fields all default None); ~59 legacy `RunArtifactSlice(`
construction sites. **Extend** disposition (additive, mirrors the W2.0.6 pattern).

## Decision

Add to `pattern_matcher.py` two frozen nested dataclasses + one optional field on
`RunArtifactSlice`, mirroring the DEC-V61-215 additive-non-breaking pattern:

```python
@dataclass(frozen=True)
class CoupledPatch:
    patch_name: str
    coupling_type: str            # a known CHT wall-coupling BC type name
    neighbour_region: Optional[str] = None

@dataclass(frozen=True)
class RegionSlice:
    name: str
    kind: Literal["fluid", "solid"]
    thermo_type: Optional[str] = None          # ← W3.0.2 RegionThermoSnapshot.thermo_type
    coupled_patches: Optional[tuple[CoupledPatch, ...]] = None
    shm_snapshot_ref: Optional[str] = None      # opaque ref → W3.0.1 RegionShmSnapshot
    thermo_snapshot_ref: Optional[str] = None   # opaque ref → W3.0.2 RegionThermoSnapshot

# on RunArtifactSlice (appended after the W2.0.6 fields):
    regions: Optional[List[RegionSlice]] = None
```

### Load-bearing design choices

1. **Refs, not embedding** — `shm_snapshot_ref` / `thermo_snapshot_ref` are
   OPAQUE STRINGS, not embedded `RegionShmSnapshot` / `RegionThermoSnapshot`
   objects. This keeps `v9_advisor` DECOUPLED from `case_extractors` (no import
   coupling, no transitive `trimesh`); the caller resolves refs. `thermo_type` is
   denormalized onto `RegionSlice` (a cheap str) so the most common W3.1 predicate
   (per-region-thermo-missing, R14) needs no ref resolution.
2. **Additive-non-breaking** — `regions` defaults `None`; all ~59 legacy
   construction sites + the W2.0.6 fields are unchanged. No field reordered.
3. **DEC-V61-213 presence-vs-payload independence** — `regions=None` (no region
   info) / `regions=[]` (present, zero regions) / `regions=[RegionSlice(...)]`
   (populated) are three distinct states; each `RegionSlice` payload field is
   independently optional (region-list presence vs per-region payload tracked
   separately).
4. **Byte-reproducibility (RS#36)** — the audit sidecar zip serializes only
   matched commentary (`commentary/matched.json`), NOT the slice; the new field
   cannot change zip bytes. Verified, not assumed.

### Frozen W3.1 sibling-DEC contract

`RegionSlice` field names + types are FROZEN here for W3.1 CHT rule distillation.
W3.1 rules R13–R16 read: R13 wall-coupling-type-mismatch ← `coupled_patches[].coupling_type`;
R14 per-region-thermo-missing ← `thermo_type` / `thermo_snapshot_ref`;
R15 conduction-vs-convection-dominance ← `kind` + `thermo_type`;
R16 face-zone-loss ← `shm_snapshot_ref`. Documented in the `RegionSlice` docstring.

## Build trail

Produced by the 3-phase workflow (`wf_56d45bc2-783`): understand (slice round-trip
path + sidecar boundary + coupling vocab + case topology, `Explore`) →
`backend-engineer` implement → 2-lens `test-red-team` (backward-compat/byte-repro +
contract-honesty/presence-vs-payload). Main session verified diffs + ran the Codex
chain.

## Open-question resolutions

1. **Manifest-adapter auto-population of `regions`** — DEFERRED (documented
   scope-out): no real CHT manifest exists yet (W3.2 generates them); the deriver
   leaves `regions=None`. W3.0.6 delivers the SCHEMA + round-trip + frozen
   contract; population wiring lands when W3.2 produces CHT manifest data.
2. **3rd nested dataclass** — the charter says "3+ nested dataclasses per the
   W2.0.6 pattern"; honored by the 3-level nesting (RunArtifactSlice → list[RegionSlice]
   → tuple[CoupledPatch]) using the nested-dataclass idiom. Two NEW dataclasses
   (RegionSlice + CoupledPatch) — no artificial 3rd forced.

## Passes-criteria

1. `pytest -q tests/p3/test_run_artifact_slice_multi_region.py` → all green.
2. case_002b-shaped (7 regions) + case_011-shaped (3 regions) round-trip through
   `dataclasses.asdict` losslessly (None vs [] vs populated preserved).
3. Backward-compat: legacy + W2.0.6-shaped construction unchanged; ~59 sites compile.
4. Byte-reproducibility: audit sidecar zip bytes unchanged (slice not serialized).
5. Frozen immutability enforced; `kind` constrained to fluid/solid.
6. Existing v9 suite (`test_v9_advisor_rules` / `test_v9_pattern_matcher` /
   `test_v9_audit_sidecar`) — no regression. Stdlib-only.
7. Codex APPROVE — **gate pending R0**.

## Governance (DEC-level meta)

- `autonomous_governance: true` (counter +1 on Accept).
- Kogami opt-in: false (sub-DEC class; reversible additive schema change).
- Codex round cap = 3; pre-merge mandatory (extends a shared DEC-V61-215 contract +
  freezes a W3.1 sibling contract).
- Four-question gate (V130): LLM offline ✓ · artifacts canonical ✓ (pure data
  schema; no inference) · TrustGate-explainable ✓ (frozen immutable slice; pure
  predicates downstream; presence-vs-payload honest, no fabrication) · advisory-only ✓.
- Surface-scan-found: `ui/backend/services/v9_advisor/pattern_matcher.py` ·
  disposition: extend (additive nested dataclasses + 1 optional field).

## Ratification

**Codex chain R0→R1→R2 — APPROVE at R2 (clean gate, within cap=3).** Chain report
`reports/codex_tool_reports/v61_221_chain_report.md`. The cleanest W3.0.x close
this session — converged P2 → P3 → APPROVE with no un-re-reviewed residual.

- **R0** (86gs xhigh) 1×P2 — the Python↔TS RS#38 parity mirror was missed: the
  Python-only schema extension left `advisor_pattern_matcher.ts` on the pre-W3.0.6
  slice. **Fixed**: added `CoupledPatch` + `RegionSlice` TS interfaces + optional
  `regions` field; `tsc -b`/`tsc --noEmit` clean (DEC-V61-203 gate).
- **R1** (86gs xhigh) 2×P3 — **explicitly NO production regression**; two
  newly-added regression tests didn't exercise their claims (RS#36 byte-invariance
  was a serialize-same-dict-twice tautology · a regions=None test built a populated
  slice). **Fixed**: byte-invariance now runs the REAL matcher + `_canonical_json`
  on regions-vs-no-regions; the None-branch test covers both None and populated.
- **R2** (CRS high; 86gs R2 hung/killed → fallback) **APPROVE** — "additive and
  backward-compatible; existing construction sites keep working; cross-language
  type surfaces updated consistently; no concrete bug."

**Pre-Codex**: the 2-lens `test-red-team` caught P2×3 + P3 (kind-None domain
narrowing — RegionSlice.kind widened to `Optional[Literal[...]]` to match W3.0.2's
`RegionThermoSnapshot.kind` domain · coupled_patches None-vs-() now pinned ·
tuple-vs-list JSON boundary re-labeled + a JSON-boundary test added · runtime-
enforcement doc gap clarified as caller-validated) — all fixed before R0.

Status flipped Proposed → **Accepted** (`confidence: high` — earned by a clean
APPROVE gate). Counter +1. Session-end Notion sync.

Tests: **295+ passed** (p3 multi-region/json-roundtrip + v9 advisor/pattern/sidecar/
cross-language parity) · no regression. Stdlib-only (Python); `tsc` clean (TS).

**Calibration notes (RETRO-V61-001 intake)**:
1. **Cross-language parity is part of the v9_advisor contract** — any
   `RunArtifactSlice` schema change MUST update the TS mirror in the same commit
   (R0 P2; DEC-V61-215 precedent). W3.1 understand phase must scan for the TS
   mirror up front.
2. **Upstream-domain match** — a slice field mirroring an extractor field must
   match its full domain incl. None, or it forces downstream fabrication
   (RegionSlice.kind; same lesson as W3.0.2 Contract-A).
3. **86gs instability is now 3-for-3 this session** (W3.0.1 502×2 · W3.0.2
   stream-fail · W3.0.6 R2 hang); CRS was the reliable fallback every time.
   **Recommend evaluating CRS-primary for governance review** — carried to retro.
