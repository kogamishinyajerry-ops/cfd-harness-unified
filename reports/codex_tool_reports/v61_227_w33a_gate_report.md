# Codex Review Report — DEC-V61-227 (P3 W3.3a cht_analytical fin gate-wiring)

- **Scope**: QoI extractor + comparator wiring + coverage test for the straight-fin
  CHT benchmark (the production-code follow-on to the 84ce01d live-validated probe).
- **Commits reviewed**: `e38b279` (feat: gate-wiring), `cf2e0e9` (fix: R0 P2).
- **Relay**: CRS (`~/.codex-crs`, gpt-5.4, **effort=high** — 86gs xhigh hangs >1h, so
  CRS fallback per codex-relay skill). `codex_review_relay: crs (effort=high, fallback)`.
- **Round cap**: 3 (R0 + 2 fix). Reached: R1.

---

## R0 — `codex review --commit e38b279` → CHANGES_REQUIRED (1× P2)

**[P2] Keep the new fin gold file compatible with single-doc loaders** —
`knowledge/gold_standards/cht_straight_fin.yaml`.

> `cht_straight_fin.yaml` is multi-document YAML, but several existing repo paths
> still load `knowledge/gold_standards/<case>.yaml` with `yaml.safe_load()` (e.g.
> `auto_verifier.verifier.verify_from_files`, `report_engine.data_collector._load_gold_standard`,
> `audit_package.manifest._load_gold_standard`). Pointing any of those at this new
> case would raise `yaml.composer.ComposerError`, so the benchmark is only usable
> through the bespoke `cht_fin_gate` path.

### Disposition — VALID-BUT-LATENT, fixed constructively (not a regression)

Triaged each named loader against the live tree before fixing:

| Loader | Plane | Behaviour on multi-doc | Routed to cht? |
|---|---|---|---|
| `audit_package.manifest._load_gold_standard` | Control | **Already graceful** — `except (yaml.YAMLError, OSError): continue` catches `ComposerError` (it IS a `YAMLError` subclass) → returns `None`. No crash. | No (case-id keyed) |
| `report_engine.data_collector._load_gold_standard` | Evaluation | bare `safe_load` → **would raise** | No — `collect()` raises earlier on missing `reports/cht_straight_fin/auto_verify_report.yaml` |
| `auto_verifier.verifier.verify_from_files` | Evaluation | bare `safe_load` → **would raise** | No — only `ANCHOR_CASE_IDS` reach it; cht is not an anchor |

Key facts: (a) the multi-doc `quantity`/`reference_values` family **already exists**
(`lid_driven_cavity.yaml`, `circular_cylinder_wake.yaml`, `backward_facing_step.yaml`,
`impinging_jet.yaml`, `plane_channel_flow.yaml`) and has this exact latent property —
my commit added one more file to it, it did NOT introduce a new failure class;
(b) cht is never routed to the two raising loaders in any normal flow; (c) the
`manifest` example Codex named does **not** raise (it catches `YAMLError`).

**Fix applied (cf2e0e9)** — behaviour-preserving hardening of the two loaders that
genuinely raise: `yaml.safe_load(...)` → first non-empty doc of `yaml.safe_load_all(...)`.
- For the single-doc (`observables`) files these loaders actually serve, `safe_load_all`
  yields exactly one doc → identical output → **zero regression**.
- For a multi-doc file (cht + the pre-existing family) it returns the first doc
  instead of an opaque `ComposerError` — a non-crashing, family-wide robustness gain.
- `manifest._load_gold_standard` left unchanged (already graceful).
- Regression test: `tests/p3/test_cht_fin_gate.py::test_generic_gold_loaders_tolerate_multidoc_cht_gold`.
- Verified: 232 passed / 1 skipped across `tests/p3` + `test_auto_verifier` +
  `test_report_engine` + `test_audit_package` (the consumers of the touched loaders).

---

## R1 — `codex review --base ea502f9` (cumulative: e38b279 + cf2e0e9) → CHANGES_REQUIRED (2× P2)

**[P2-A — NEW, valid] Fail the fin gate when fin-surface balance is broken** —
`src/cht_fin_gate.py:93-98`.

> If `finPower` is stale or points at the wrong patch while `basePower` and `tipT`
> still match the analytical values, the gate still returns `passed=True` because
> only the two comparator results participate in the verdict. `energy_residual_w`
> is only used in the summary string.

**Disposition — VALID, good catch.** The W3.3a honesty argument explicitly leans on
dual-channel (flux vs temperature) energy closure, but the verdict did not gate on
it. **Fix (R1):** added a HARD energy-closure gate — `passed` now requires
`energy_residual_w <= 1e-3 * |Q_base|` in addition to both comparator PASSes
(`FinGateResult.energy_closure_ok`). Live probe residual 1.04e-4 W ≪ 0.776 W bound;
a zeroed/wrong `finPower` drives the residual to ~|Q_base| → FAIL. Regression test
`test_energy_closure_is_a_hard_gate_doctored_finpower_fails` doctors `finPower` only
(observables still PASS) and asserts the gate FAILS on energy closure.

**[P2-B — sharper restate of R0] Audit manifests silently drop the multi-doc gold** —
`src/audit_package/manifest._load_gold_standard`.

> `build_manifest()` for `cht_straight_fin` → `manifest._load_gold_standard` uses
> `safe_load`, swallows the `ComposerError`, emits `case.gold_standard = null` — the
> audit package loses its reference contract.

**Disposition — VALID.** At R0 I judged manifest's graceful-None acceptable; R1
correctly sharpens that graceful-None is *silent data loss* for an audit artifact.
**Fix (R1):** `manifest._load_gold_standard` now reads with `safe_load_all`; single-doc
→ unchanged; multi-doc → a wrapper dict `{case_id, multi_document: True, documents:[...],
legacy_case_ids?}` that preserves the FULL per-quantity reference contract (no
observable dropped) and stays `.get()`-/JSON-serialisable for the manifest +
`serialize.py` consumers. Regression test
`test_audit_manifest_loader_preserves_multidoc_cht_gold` asserts both fin documents
survive. Verified: 234 passed across `tests/p3` + `test_audit_package` (incl.
`serialize`/`sign`) + `test_auto_verifier` + `test_report_engine`.

**Fix commit:** `b5bd8f2`.

## R2 — `codex review --base ea502f9` (cumulative: e38b279 + cf2e0e9 + b5bd8f2) → APPROVE

Relay note: CRS suffered a transient **502 Bad Gateway outage** mid-session; the
first two R2 attempts failed (no verdict → round not consumed). Per the
codex-relay fallback rule I switched to **86gs xhigh**, which flapped on
intermittent reconnects (~40 min, no clean verdict — the "86gs slow/hangs" risk).
On CRS recovery (clean `crs-OK` ping) I re-ran R2 on CRS and it completed cleanly
(~28 min, exhaustive: verified the multi-doc/single-doc family split empirically,
the CONJUGATE enum blast radius, all gold-loader consumers, the plane contracts,
and the audit serialize/sign path).

> **Verdict (verbatim):** "I did not identify any discrete, actionable bugs
> introduced by this diff. The new fin-gate code, multi-document gold-loading
> changes, and generated report updates appear internally consistent with the
> existing callers and tests in this repository."

**APPROVE — no findings.** Chain complete at R2 (cap=3): R0 1×P2 → R1 2×P2 → R2 0.
`codex_review_relay`: R0–R1 CRS high; R2 CRS high (after CRS-502 → 86gs-flap →
CRS-recovered). effort=high throughout (xhigh 86gs unavailable/flapping).

---

## Cross-check (independent of Codex)

A read-only mapping workflow (`wnpnped3d`, 3 mappers + synthesis judge) independently
confirmed the architecture before implementation: authoritative comparator =
`ResultComparator` (the `quantity`/`reference_values` family), **not** `auto_verifier`
`GoldStandardComparator` nor `AutoVerifier` (cht is out-of-scope for the anchor set);
surfaceFieldValue.dat parse (skip `#`, last data row, value column); `basePower`
(positive Q_base) not `finPower`; verbatim `key_quantities` keys; extractor must not
import the comparator (plane separation → split into Execution extractor +
Control-plane gate); `T_base` measured not hardcoded; fail-closed on missing inputs.

## Honesty properties verified
- Reference locked against fabrication by `test_cht_straight_fin_gold.py` (re-derives η/tip from inputs).
- QoIs computed from raw solver output, never the closed form (anti-tautology).
- Gate genuineness: doctored `Q_base` → FAIL; doctored `T_tip` → tip ratio changes; extracted value ≠ gold reference; energy closure |Q_base+Q_fin|≈1e-4 W.
- Runnable-coverage stays **1** (solid-side only; W3.3b flips 1→2). No coverage count fabricated.
