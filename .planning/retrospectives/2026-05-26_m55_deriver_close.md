# M5.5 follow-up close · solver streamlines + manifest→WorkbenchBasics deriver · 2026-05-26

> Parent: DEC-V61-206 · the root-cause fix the C4 retro deferred.
> Commits: `1f9512f` (R0: streamline removal + deriver) → `db1c220` (R1: 4
> faithfulness fixes) → `ed310c7` (R2: dimension degrade + provenance wording).
> Codex arc (86gs gpt-5.4 xhigh, code-only · round cap=3 reached):
>   R0 CHANGES_REQUIRED (2 P1 + 2 P2) →
>   R1 CHANGES_REQUIRED (3 of 4 resolved; 1 P1 dimension partial + 2 P2) →
>   R2 (round 3 · the cap).
> Reports: reports/codex_tool_reports/m55_deriver_{R0,R1,R2}_20260526.txt

## 做了什么 (what)

Two user-reported gaps after the C4 boundary de-fake:

1. **求解界面 still had a fake SVG streamline cartoon.** `ModeRendererSolver`
   painted a hand-drawn `StreamlineField` (`SolverFlowOverlay`) on top of the
   real 3D viewport. Deleted it + the dead `SOLVER_BLUEPRINT_STREAMLINE_COUNT`.
   The real integrated streamlines (`post/streamlines.vtp`, 1.6 MB) still
   render in `ViewportV4`. The file header had ALREADY claimed StreamlineField
   was removed in the 2026-05-19 dogfood retrofit — it wasn't (the overlay
   survived). Same incomplete-de-fake pattern as the C4 boundary shell leak.

2. **"边界条件设置如果你做了的话，要标注出来".** The dogfood DID set real BCs
   (inlet `fixedValue (1 0 0)`, outlet `zeroGradient`, walls `noSlip`) but the
   UI showed `待识别` because `workbench-basics` only served hand-authored
   `knowledge/workbench_basics/<id>.yaml` (absent for imported cases). Built the
   **manifest→WorkbenchBasics deriver** (the C4-retro-deferred root fix):
   - `ui/backend/services/workbench_basics_deriver`: mirrors the OpenFOAM case
     on disk — patches (`polyMesh/boundary`) + per-field BCs (`0/<field>`) +
     material (`physicalProperties`) + solver (`controlDict`) + geometry bbox.
   - route falls back to the deriver (`provenance="derived"`) when no authored
     yaml; still 404 when there's no OpenFOAM case.
   - frontend boundary step surfaces the **real per-patch BC values** + a
     `派生自算例` provenance badge.
   Verified end-to-end on the real turbine over live HTTP.

## 关键发现 (key findings)

1. **The faithful-mirror contract is easy to state and easy to violate in the
   fallback paths.** I built the happy path correctly (real case → real data),
   but Codex R0 caught FOUR places where a *degraded* input produced a
   *confident* output:
   - no `0/U` → guessed role from the patch NAME (still badged 派生自算例);
   - no `momentumTransport` → asserted `层流` + cited a file it never read;
   - hardcoded `dimension=3` → a 2D case mislabeled;
   - a parser charset broader than the reused reader → silent patch loss.
   **Lesson**: "never fabricate" has to hold on the *worst* input, not the
   representative one. For every derived field, the test that matters is
   "what does this emit when the source file is absent/garbage?" — the answer
   must be *omit / None / unknown*, never a plausible-looking default. This is
   the same class as the C4 `setup-bc` false-provenance, now generalized:
   **a default value is a claim.** Codex's independent read was load-bearing
   again — the happy-path tests + live HTTP check all passed and would NOT
   have caught any of the four (they all used a complete case).

   **The lesson needed THREE rounds to fully land — itself the proof.** My R1
   fix for the hardcoded `dimension=3` replaced it with "derive from the empty
   marker, else 3" — which *still* asserted 3D when `0/U` was unreadable
   (Codex R1 P1). I'd swapped one default for another. Only R2 made it honest:
   dimension is emitted *only* when `0/U` was read AND covers every patch, else
   `None`. The "a default is a claim" rule is genuinely hard to internalize —
   even while consciously fixing it I re-introduced it. The durable guard is a
   test per field that feeds the *degraded* input and asserts omission. R1 also
   left two narrower instances (a desc that said "无 0/U" for a partial file; a
   reasoning string citing `momentumTransport` for a legacy
   `turbulenceProperties`) — both "the wording claims more than disk proves."

2. **"Reflect on disk" beats "infer intent".** Deriving patch role from the
   ACTUAL `0/U` BC type (not the name) means a `periodic_*` patch written
   `noSlip` honestly shows as `wall` — the solver ran it as a wall. The name
   would have lied. The faithful rule also surfaced a real engineering smell
   (periodics should be `cyclic`) as a side effect — truth is diagnostic.

3. **The deriver retires a whole class of fakes at once.** Because the frontend
   already consumed `WorkbenchBasics`, one backend deriver flips boundary +
   material + solver (+ bbox) from `待识别` to real data for every imported
   case — no per-component frontend change. The C4 arc fixed the *symptom*
   (honest placeholder); this fixed the *cause* (no data source for imported
   cases).

## 治理 (governance)

| Gate | Status |
|---|---|
| Four-question gate | ✅ read-only mirror of solver-input files; no LLM; no AI mutation; provenance labelled |
| Faithful-mirror contract | ✅ R1: every section omits/None when source absent; +3 regression tests pin worst-input behavior |
| Codex round cap=3 | ✅ R0 → R1 (round 2). |
| Codex relay | ✅ 86gs gpt-5.4 xhigh, code-only |
| Tests | ✅ backend 10 deriver + 6 route; frontend tsc clean + 134 V4 (+1 derived-BC render guard) |
| Live verification | ✅ real turbine over HTTP: provenance=derived, 6 patches, real U/p BCs, pimpleFoam·瞬态, ν=0.001 |
| No cadence override | ✅ push gated on real Codex review + canonical trailer |
| confidence | high |

## 下一步 / 风险 (next / risks)

- **Dotted/dashed patch names** (`wall.001`) are unsupported by the shared
  `_read_patch_ranges` reader app-wide → such a case derives no patches (404).
  Out of scope here; a `_PATCH_RE` widening would touch the shared reader.
- **`geometry.shape="imported"`** is an honest literal (uncategorized import);
  `/learn` renders it via the existing `UnsupportedShapeStub`. The V4 workbench
  renders the real GLB regardless.
- **Periodic patches set to `noSlip`** (turbine dogfood) — a real physics fix
  (should be `cyclic`) the deriver faithfully surfaced. Separate from this arc.
- **Live `:8001` backend is not `--reload`** → users must restart it to see
  derived data in the browser (verified on a throwaway port instead).
