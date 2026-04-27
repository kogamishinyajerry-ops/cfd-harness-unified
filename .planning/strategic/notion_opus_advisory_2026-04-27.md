---
artifact_kind: notion_opus_advisory_response
date: 2026-04-27
session_link: S-002 (M5/M6 kickoff arc)
prompt_source: session conversation 2026-04-27 · Notion-Opus residual session-shape role
prompt_artifact: in-conversation copy-paste · not committed as own file (transient)
status: ingested · 6 findings · 4 applied mechanically · 1 already-answered · 1 surfaced as strategic question
governance_classification: advisory (NOT a Kogami clearance · NOT a Codex review · NOT a DEC)
---

# Notion-Opus advisory response (S-002 · 2026-04-27)

Per DEC-V61-087 §3.5, Notion-Opus is no longer a formal governance gate
(Kogami subprocess took that role). This response is recorded as an
**advisory** input — non-counted, non-blocking, but high-signal because
it surfaces session-shape gaps that Codex (per-diff scope) and Kogami
(per-milestone-brief scope) do not reach.

---

## Verbatim response (preserved as primary source)

> Reading as Opus 4.7 in the residual session-shape role. Five answers,
> in order.
>
> **1 · Velocity vs governance debt.** The cadence itself isn't the
> problem; the *deferred queue* is. After S-002 you are carrying:
> (a) Codex post-merge on `4a0755e..23bcba6` (gate 1), (b) manual UI
> dogfood of `/workbench/import` (gate 2), (c) M5.1 trust-core (TrustGate
> hard-cap + `audit_package` filter), (d) M6.1 trust-core
> (`mesh_already_provided` boolean). That is **four open items from one
> session, two of which are runtime-invariant carve-outs**. The canary
> I'd watch is *queue-depth-at-session-end*: if S-003 closes with ≥5
> deferred items and the M5.0 Codex review still hasn't run, you've
> tipped. Concretely: refuse to start M6.0 (gate 3) before gate 1
> clears. The roadmap currently says "should wait" — make it "must".
>
> **2 · M5–M8 → user value coherence.** The structural risk Codex and
> Kogami both pass over: **you now have two meshing paths for imported
> geometry**. M5.0 shipped the sHM stub, M6.0 ships gmsh, M7 fills the
> sHM stub. After M7 a user importing an STL has *two* mesh backends
> and no documented routing rule. The 10 canonical cases use sHM;
> imported cases under M6.0 will use gmsh; M7 reintroduces sHM for
> imported. D8's "30 minutes end-to-end" claim implicitly assumes a
> user never has to *choose*. There is no decision in M5/M6/M7 specs
> about who picks (UI? heuristic on STL complexity? cell-budget?).
> That choice has to land somewhere, and right now it's homeless.
>
> **3 · Trust-core micro-PR forcing function.** This is the highest-risk
> item in the session. M5.1 is gated on "M5.0 producing ≥1 real run,"
> which is M7-gated, which is M6-gated. **Two indirections from action.**
> Without a written rule, M5.1 will float into M8 and then into
> post-Beginner-Full-Stack triage. Forcing function suggestion: add to
> ROADMAP that *M7 cannot be marked Done while M5.1 is unmerged*, and
> *M6.0 cannot be marked Done while M6.1 is unmerged*. Make the
> carve-out a blocker on the *parent's* Done state, not on a future
> artifact's existence.
>
> **4 · What Codex and Kogami both missed.**
>
> - **Mesh-backend fork** (see §2 above) — neither scope catches it
>   because Codex reviews per-file diffs and Kogami clears per-milestone
>   briefs.
> - **`trimesh` dependency surface.** M5.0 added a new pip dep + 3
>   binary STL fixtures. The repo has historically resisted committed
>   binary artifacts; did M5 spec v2 explicitly grandfather them, and
>   was `trimesh` pinned against `foam-agent`'s transitive deps?
>   Routine-path skipped DEC, so there's no decision record either way.
> - **D6 5M cell-cap "calibrate from M6.0.1 telemetry"** treats a single
>   PR's run as a calibration set. One sample is anecdote. The unlock
>   should require N≥3 distinct beginner STLs before the soft-warning
>   becomes a hard cap, otherwise M6.0.1 ships a number with the same
>   epistemic weight as the 5M it replaces.
>
> **5 · First-customer reality check.** The pivot framing is misleading.
> CFDJerry-as-developer cannot be the first customer — you can't dogfood
> neutrally on code you wrote yesterday. The 10 canonical cases are
> *test substrate*, not customers. **The actual first customer is the
> stranger at M8's dogfood gate, who does not yet exist.** This matters
> because M5–M8 is currently being designed against an imagined user.
> Recruit (or at minimum *name*) the stranger before M7 ships, not
> after M8. If no stranger is identifiable by M7 kickoff, that's
> evidence the user-as-first-customer pivot is aspirational, and you
> should retreat to "Jerry-as-first-customer with stranger validation
> deferred" — explicitly, not by default.
>
> No signal on anything else.

---

## Triage and actions

### Finding 1 · Queue-depth canary · APPLIED

ROADMAP M6 entry edited: "should wait for gate 1" → **"must wait for
M5.0 Codex APPROVE recorded before M6.0 implementation begins"**.
Telemetry signal recorded: queue-depth-at-session-end. Tipping criterion:
S-003 closes with ≥5 deferred items AND M5.0 Codex still uninvoked →
declare governance debt.

### Finding 2 · Mesh-backend fork · PARTIALLY APPLIED

The "homeless decision" — does an imported case use gmsh (M6) or sHM
(M7) — is real. Cannot resolve here (M7 hasn't been kicked off and the
right resolution depends on M6.0 telemetry). Applied: ROADMAP §M7 now
carries a **MUST RESOLVE at M7 kickoff** flag for backend routing
(UI selector vs heuristic vs cell-budget-driven). The flag prevents
M7 from drifting in without surfacing the question.

### Finding 3 · Forcing function · APPLIED

ROADMAP edited so:

- **M7 Done-gate**: M5.1 must be merged. (Otherwise TrustGate hard-cap
  + audit_package filter never land — runtime invariants violated under
  imported-case verdicts.)
- **M6 Done-gate**: M6.1 must be merged. (Otherwise blockMesh-skip
  flag never lands — gmsh-meshed cases attempt blockMesh and fail at
  M7-runtime.)

Both gates are explicit blockers on the parent phase's Done flip,
not on a hypothetical future artifact.

### Finding 4a · trimesh dep no recorded decision · APPLIED (post-hoc note)

Decision record (recorded here for audit trail):

- **Choice**: `trimesh>=4.0` + transitive `scipy>=1.13` + `python-multipart>=0.0.9`
  in `[project.optional-dependencies].workbench` (NOT default install).
- **Why trimesh over alternatives** (open3d, vtk, meshio): trimesh has
  the simplest watertight check, bbox, and named-solid extraction APIs
  for STL specifically; vtk is overkill, open3d's STL surface is
  weaker, meshio is a converter not an analyzer.
- **foam-agent transitive-dep compatibility**: foam_agent runs in the
  Docker CFD container, not in the host venv. Host-side trimesh +
  scipy do not enter the container. `uv lock --check` confirms no
  host-side conflict with the existing dep tree.
- **Routine-path skipped DEC**: ratified retroactively here as part of
  this advisory ingest. No further DEC needed.

### Finding 4b · binary STL fixtures grandfathered? · ALREADY ANSWERED

D1 in M5 spec v2 (commit `8863234`) explicitly approved committed
binary STL fixtures: "examples/imports/ inline in repo · total budget
≤ 8MB · ship 3 fixtures ldc_box.stl (<50KB) + cylinder.stl (<100KB)
+ naca0012.stl (<300KB) · NO Git LFS · add to .gitattributes if
line-ending issues arise". Total committed: 38.7 KB, well under cap.
Notion-Opus did not have full spec v2 in context.

### Finding 4c · D6 calibration N=1 anecdote · APPLIED

M6 spec v2 §C "D6 cap calibration" amended: calibration unlock requires
**N≥3 distinct STLs (mix of M5 fixtures and real user uploads)**, not
single-PR telemetry. Until N≥3 reached, beginner cap stays at 5M soft
warning. The 50M power-mode hard cap is unaffected (verdict-grade
guard, not a calibrated value).

### Finding 5 · First-customer reality check · STRATEGIC QUESTION (NOT APPLIED)

Notion-Opus's strongest finding. Cannot autonomously rewrite the
Pivot Charter. The framing claim "user-as-first-customer" implies
CFDJerry's daily dogfood = first-customer feedback, but Notion-Opus
correctly notes: a developer cannot dogfood neutrally on code they
wrote yesterday.

Two paths the user must choose between (no third option):

**Path A · Recruit/name a stranger before M7 ships**:
- Identify a CFD-literate non-project-member willing to run end-to-end
  at M8 dogfood gate.
- Their existence becomes a forcing function — without one, M7 cannot
  ship.
- This is the only way the "user-as-first-customer" pivot remains honest.

**Path B · Retreat to "Jerry-as-first-customer · stranger validation deferred"**:
- Update Pivot Charter Addendum 1 to be honest about the current
  audience scope.
- Stranger-validation moves from D8 binding gate to a separate
  post-M8 effort with no fixed timeline.
- The M5–M8 sequence still ships, but the verdict shifts from "we
  validated against a real first customer" to "we built infrastructure
  Jerry uses; external validation is open work".

Either path is defensible. **Default-by-not-deciding is path A but
without recruitment**, which is the failure mode Notion-Opus is
warning about — designing against an imagined user.

### What's NOT applied

No findings outside the 6 above. Notion-Opus closed with "no signal
on anything else" — taken at face value (anti-yes-and discipline).

---

## Closing assessment of the advisory channel

This response was high-signal — finding 2 and finding 5 in particular
are inputs neither Codex nor Kogami's scope reaches. Channel earns
its keep. Future advisory invocations should preserve the same focus
(direction-setting, not code/governance) and the same anti-padding
discipline ("no signal on anything else" rather than filler).
