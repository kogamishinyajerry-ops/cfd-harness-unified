# Knowledge Status Convention

> **Established 2026-05-08 by harvest cycle 002**, in response to
> the case_005 V19→V21→V25 chain demonstrating that "advisor PASS"
> can mean two very different things: (a) the algorithm runs cleanly,
> (b) the engineer's question is answered. Confusing (a) with (b)
> produces fast knowledge decay across kickoffs and case profiles.

> **Invoked by**: `cfd-harness-harvest` skill (mode `mark-questionable`),
> harvester 4th-actor session, main session backfill sweeps. Lives
> alongside `industrial_case_solver_findings.md` (V-series) and
> `solver_convergence_playbook.md` (S-series) as the third
> methodology pillar.

## Why this convention exists

V25 (open · 2026-05-08) showed that A2 advisor's `_run_shared`
returns `matched=True` with hardcoded placeholder fields
(`bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0`) regardless
of actual face geometry. Three industrial cases (003 + 004 + 005 v2)
all reported "A2 PASS." All three PASSes confirm only that the
algorithm runs and finds candidate faces. **None** of them validate
the engineer's actual question ("does this defect get detected as a
defect?"). That capability is not implemented.

The kickoff narrative at the time said "exercise the landed advisor;
expect detection." The advisor was indeed landed. But the kickoff
framing implied a capability that did not exist. Three sub-sessions
ran, returned PASS, and the kickoffs propagated the false
implication into the next round of kickoffs (case_006 etc.). The
implication propagated faster than the V-finding chain that
contradicted it.

This convention is the antibody.

## Status field grammar

Every claim in a methodology / kickoff / case-profile / playbook
file falls into one of these states:

| Status | Meaning | When to use |
|---|---|---|
| **confirmed** | ≥2 cases independently produced the claim's result; cross-checked against code | Default state for stable claims |
| **partial** | One case produced; mechanism understood but scope-narrow | Default for new V-row before second case lands |
| **questionable** | Claim implied/inherited from related but distinct evidence; not directly tested | New: prevents cross-contamination |
| **refuted** | Newer evidence contradicts; old claim preserved with strikethrough | Preserves audit trail, doesn't delete |
| **superseded** | Older claim replaced by sharper variant; cross-link to successor | Preserves chain (V19 superseded by V25) |
| **open** | Evidence trail incomplete; verification pending | Default for V-rows awaiting next-case sediment |

## Marker syntax (machine-grep-able)

Inline marker (precedes the claim or wraps a paragraph):

```
> [QUESTIONABLE 2026-05-08]: <claim text>.
> Verification pending: <observable that would resolve>.
> To resolve: <what evidence would settle this>.
```

For refuted claims, use markdown strikethrough + footnote-style
forward link:

```
~~claim text~~ [REFUTED 2026-05-08 by V25; see industrial_case_solver_findings.md#v25]
```

For superseded claims:

```
> [SUPERSEDED 2026-05-08 → V25]: <original claim text>.
> Successor: <where the sharper variant lives>.
```

For confirmed-after-questionable resolution:

```
> [VALIDATED 2026-05-08]: <claim text>. Originally questionable
> 2026-05-08; resolved by <evidence>. Status now: confirmed.
```

The bracketed status keyword (`QUESTIONABLE`, `REFUTED`,
`SUPERSEDED`, `VALIDATED`) at the start of the marker is the
hook for `grep -rn '\[QUESTIONABLE\|\[REFUTED\|\[SUPERSEDED\|\[VALIDATED' .planning/`.

## When to mark something questionable (not confirmed)

A claim is **questionable** if any of:

1. **Inherited implication**: claim says "exercise X; expect Y"
   when the actual code path doesn't surface Y as an output.
   Example: "exercise A2; expect gap detection" — A2 has no
   gap-distance API field; matched=True is silent on gap.
2. **Single-case PASS without code-trace**: one case produced a
   positive result but no one read the code to confirm what the
   PASS actually measures. Example: case_003 A2 PASS reported
   without disambiguating which advisor entry-point ran.
3. **Cross-domain transfer**: claim worked in domain A, applied
   without validation to domain B. Example: thin_wall_advisor
   passed on planar plate (case_003 D8); claim "will pass on
   transom plate above WL" (case_007 D8) is questionable until
   case_007 actually runs.
4. **Stale-by-construction**: claim is anchored to a fact known
   to drift (e.g., "A2 not yet landed" written on day N becomes
   stale on day N+1 when A2 lands).

## Iteration discipline

Each sub-session sediment cycle:

1. **Harvester scan**: `grep -rn '\[QUESTIONABLE'` over `.planning/`
2. For each questionable marker, ask:
   - Did this cycle's sediment touch the verification-pending
     observable?
   - If yes → upgrade to `[VALIDATED ...]` with evidence link, OR
     downgrade to `[REFUTED ...]` if contradicted
   - If no → leave marker, next cycle re-evaluates
3. **Decay-budget alarm**: if any questionable marker is older
   than 5 sub-session sediment cycles without resolution, flag
   in harvest report § "Stale questionable claims"

## Examples

**Original (kickoff for case_005 D1, pre-convention)**:

> "exercise the landed advisor; expect detection of 0.35 mm gap"

**Convention-compliant version**:

> [QUESTIONABLE 2026-05-08]: "exercise the landed advisor;
> expect detection of 0.35 mm gap." A2 LANDED 2026-05-08
> (a09ae0a) for V2 pattern (shared interface confirmation),
> not D1 pattern (gap-as-defect).
> Verification pending: V25 sub-DEC adds `inter_face_gap_mm`
> field to DetectedInterface.
> To resolve: A2-v2 API extension lands AND ≥2 sub-sessions
> exercise it on D1-class defects.

**case_005 V19 (after V25 surfaced)**:

```
| Status | [SUPERSEDED 2026-05-08 → V25]: original mechanism
diagnosis used wrong code-path; conclusion preserved in V25's
sharper form (silent placeholder semantic) |
```

**Successful validation (hypothetical, after case_007 runs)**:

```
| Status | [VALIDATED 2026-05-08]: thin_wall_advisor robust
across (curved CATIA, planar CadQuery aero, planar instrumentation,
planar transom). Originally partial after 3 cases; resolved by
case_007 D8 PASS. Status now: confirmed (4-case cross-topology). |
```

## Anti-patterns to avoid

1. **Don't delete refuted claims** — keep with strikethrough +
   forward link. Audit trail matters for replicating the reasoning
   that led to the refutation.
2. **Don't auto-upgrade** — questionable → confirmed requires
   ≥2 case evidence, not 1. (1-case PASS = partial at best.)
3. **Don't mark everything questionable** — that's noise. Reserve
   for claims meeting the 4 criteria above.
4. **Don't skip verification-pending field** — without it, future
   harvester can't tell what would actually settle the question.

## Relationship to V-series and S-series

- **V-series** = engineer-facing failure modes (what went wrong)
- **S-series** = engineer-facing convergence patterns (what to try)
- **This convention** = META layer for any claim in any methodology
  file (how confident should we be that it's still true?)

V-rows already have a `Status` field that should now use this
convention's grammar. S-rows do not yet — when an S-row gets
sharpened by case-thread evidence, it should adopt this grammar
(see V18→S13 sharpening 2026-05-08 for an example of evidence-
driven status refinement).

## File ownership

This convention is written by harvester (any role can author the
markers, but only harvester promotes/demotes status across cycles).
Main session can mark new claims as `[QUESTIONABLE]` when it
notices an inherited implication. Sub-sessions can record
`[QUESTIONABLE]` in V-finding entries for claims that need cross-
case validation.
