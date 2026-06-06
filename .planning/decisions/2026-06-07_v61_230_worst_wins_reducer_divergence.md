---
decision_id: V61-230
title: Two worst-wins reducers — divergence investigation + unification disposition (HIGHEST correctness-risk roadmap item)
status: Proposed
accepted_date:
parent_dec:
phase: positioning-optimization (multi-agent role taxonomy arc · §5 P1 item)
autonomous_governance: true
confidence: high (ratified disposition = test-only single-contract guard, ZERO production reducer code changed; 29 chars-pinning tests green)
kogami_opt_in: candidate (trust-core honest-spine correctness; user may want strategic eyes)
round_cap: 3
codex_review_relay: pending (CRS gpt-5.4 — 86gs saturated by cross-project reviews this session)
codex_verdict: pending
codex_tool_report_path:
ratified_disposition: single-contract test (guarded non-merge) — user chose full-merge → system-architect consult 2026-06-07 proved single physical core breaks cfdtrust standalone-verifier portability → user ratified the architect-recommended single-contract-test realization
notion_sync_status: N/A (Proposed; syncs only on Accepted)
touches_shared_dec: src/metrics/trust_gate.py (Plane.EVALUATION trust-core) · ui/backend/audit/cfdtrust/audit/report.py (Plane.UI trust report) · .importlinter Contract 2 (plane boundary) · trust_report.json schema · scope-adjacent ui/backend/audit/tools/cwos_status.py (THIRD reducer — explicitly OUT of scope)
investigation_workflow: wf_82bb559f-95b (4 read-only agents · real-execution divergence table · 297K tokens)
---

# DEC-V61-230 · Worst-wins reducer divergence — investigate-first, do NOT naive-merge

## Context

§5 roadmap P1 (highest correctness risk): "unify the two worst-wins reducers into one
canonical core — a fence/fix applied to only one silently misses the other." Read-only
safe-refactor investigation (workflow `wf_82bb559f-95b`, real-execution of both cores)
found this is **NOT a clean mechanical merge** — the cores carry genuinely divergent
semantics outside the shared 3-state alphabet.

## Finding: latent behavioral divergence (real-execution verified)

Both cores **agree on the entire closed `{PASS,WARN,FAIL}` alphabet** (all 13 single/multi
cases: all-PASS→PASS, any-FAIL→FAIL, WARN-no-FAIL→WARN, etc.). They diverge structurally
**outside** it:

| input | Reducer A (`trust_gate.reduce_reports`) | Reducer B (`report._overall_status`) |
|---|---|---|
| `[]` empty | **PASS** (vacuous, by design `:368-369`) | **WARN** (`:34` fallthrough) |
| `{unknown/garbage}` | **PASS** — silently swallowed (counts neither FAIL nor WARN bucket) | **WARN** (catch-all) |
| `{BLOCKED}` | unrepresentable; forced→**PASS** | **BLOCKED** (dedicated tier) |
| `{MOCKED}` | unrepresentable; forced→**PASS** | **MOCKED** (dedicated tier) |
| `{WARN,BLOCKED}` | forced→WARN | **BLOCKED** (B ranks BLOCKED>WARN) |

- **A** = rigid 3-state `{pass,warn,fail}` (lowercase enum, `base.py:37-42`); empty→PASS;
  unknown→silently PASS (**fail-OPEN** — the worst trust-gate failure mode).
- **B** = 5-state `FAIL>BLOCKED>MOCKED>WARN>PASS` (uppercase str); empty→WARN; unknown→WARN;
  missing-status-key→FAIL (**fail-closed**).

**The trap**: naively widening A to accept B's vocabulary makes A return PASS on exactly the
inputs B intentionally flags. A fence written for B (un-witnessed runs can't PASS;
BLOCKED/MOCKED honesty tiers; conservative-unknown default) has NO analogue in A and would
be LOST on a careless merge.

## Live-impact assessment (mitigating)

- **No firing bug today.** A's inputs are physically 3-state (`_ATTEST_VERDICT_TO_STATUS` +
  `comparison.passed`), so A never actually receives BLOCKED/MOCKED/garbage in production.
- A's output (`RunReport.trust_gate_report`) currently has **no production consumer** (not
  compared-to-constant / serialized / keyed / rendered) — dormant audit artifact.
- **B is the live one**: `_overall_status` → `trust_report.json` → Draft7 schema validation
  (5-state enum; `PASS→solver=real` fence). HIGH blast radius.
- Signing path is **isolated** (verified): `audit_package/sign.py` embeds neither reducer's
  output; `comparator_verdict` comes from a separate `comparator_passed` path. Unifying the
  reducers **cannot change signed bytes**.

## Two surprises the roadmap missed

1. **THIRD reducer**: `ui/backend/audit/tools/cwos_status.py::compute_overall_status`
   (phantom-forces-RED integrity logic, `test_red_team_safety.py:566-619`). If we "unify
   A+B" the silent-miss risk merely **relocates** to this third one unless it's explicitly
   scoped + tracked.
2. **Plane boundary** (`.importlinter` Contract 2): `src.metrics` (Plane.EVALUATION) is
   forbidden to be imported by `ui.backend` (Plane.UI). A shared core in `src/metrics/`
   that B imports would **violate the contract**. → controlled duplication of a ~5-line
   generic skeleton may be the SAFER choice on this highest-risk surface.

## Disposition options (require user ratification — divergent-cell canonicality is NOT the implementer's call)

- **Option A (SAFE · recommended)**: Land two golden characterization tests pinning BOTH
  reducers' CURRENT behavior (incl. the divergent cells, documented as known+intentional) →
  divergence becomes **machine-visible** (the silent-miss risk is *killed* — any future
  change to either that flips a verdict now fails CI). Document the divergence + the third
  reducer in this DEC. Keep controlled duplication; **do NOT physically merge** divergent
  semantics. Lowest risk; directly achieves the roadmap's real goal. No canonicality
  decision needed.
- **Option B (FULL merge)**: Extract a generic `worst_wins(order, empty)` skeleton + per-
  reducer adapters (each keeps its own vocabulary/ordering/empty-default + surrounding
  policy). Requires: (1) ratify the canonical disposition of each divergent cell, (2)
  resolve the plane-boundary (plane-neutral module vs accept duplication), (3) golden tests
  green first, (4) Codex APPROVE with both golden files as the oracle. More "complete" but
  higher risk; policies stay separate anyway → marginal benefit over A.
- **Option C (defer)**: keep this DEC draft as the record; no code change now.

## Pre-committed gates (any merge path)

1. Both golden matrix files committed & GREEN before a single reducer line changes.
2. Synchronous Codex review (trust-core / correctness boundary) before merge — NOT async.
3. Third reducer (`cwos_status.py`) explicitly OUT of scope (or a follow-up DEC).
4. Byte-repro tripwire: `serialize_zip_bytes` for a fixed manifest byte-identical pre/post.

## Ratified disposition (2026-06-07)

User picked **full physical merge (Option B)**. Grounding then surfaced a HARD constraint:
`ui/backend/audit/cfdtrust/` imports **zero** from `src.*` — it is a standalone, zero-src-
dependency portable verifier (`ui/backend/audit/pyproject.toml` declares only PyYAML +
jsonschema) so signed audit packages replay air-gapped. **system-architect consult
(2026-06-07)** ruled a single physical `src.*`-imported core INCOMPATIBLE with that
invariant (would break the wheel off-monorepo + byte-repro replay, and `.importlinter`
scope is `src.*`-only so it would NOT catch the breakage). Architect's pick: **guarded
duplication enforced by ONE cross-package consistency test** — "the user's desire for a
single physical core is better satisfied by a single contract-enforcing test than by a
single import that collapses a critical packaging boundary."

User then ratified the **single-contract-test** realization. Final outcome:

- **NO physical merge.** Both reducers keep their own ~6-line worst-wins logic + distinct
  surrounding policy. cfdtrust stays standalone (zero src imports preserved).
- **ONE contract SSOT**: `tests/test_metrics/test_worst_wins_contract_dec_v61_230.py`
  (29 tests, green). It (a) asserts A and B AGREE on every multiset of the shared
  `{PASS,WARN,FAIL}` alphabet — so a fence/fix to one reducer that flips a shared-alphabet
  verdict now turns CI **red** (the roadmap's "围栏只补一处会静默漏" risk is killed by a
  machine guard); (b) pins the divergent cells (empty / BLOCKED / MOCKED / unknown /
  missing) as KNOWN + INTENTIONAL with source lines, so they are documented, never silent.
- Test-only bridge: the contract test imports both packages but ships in **neither** wheel
  (`sys.path.append`, not insert — no top-level shadowing). Zero production reducer code
  changed → no byte-repro / signing risk.

## Deferred (NOT in this DEC — surfaced for the record)

1. **Harden Reducer A to fail-closed** on empty/unknown (currently fail-open but UNREACHABLE
   today: A's enum is 3-state + A's output is dormant). A separate behavior-change decision
   if/when A's input vocabulary is ever widened — the contract test will force the issue.
2. **Third reducer** `ui/backend/audit/tools/cwos_status.py::compute_overall_status` —
   explicitly OUT of scope; candidate follow-up DEC so the silent-miss risk doesn't merely
   relocate.

## Status

Status=**Proposed** pending Codex review of the contract test. No production spine code
changed. Investigation artifact: workflow `wf_82bb559f-95b`; architecture consult:
system-architect 2026-06-07. On Codex APPROVE → Status=Accepted.
