# Codex review summary — M5 C2 overlay wiring (DEC-V61-205)

Backend: 86gs gpt-5.4 xhigh · `codex review --base origin/main` · 2026-05-25
Round cap = 3 (R0 + 2 fix iterations) per DEC-V61-133. All findings RESOLVED.
Raw transcripts (with full diff context) were not committed — they embed
minified bundle source that trips the pre-push security-pattern scanner; this
verdict-only digest is the archived artifact.

## R0 (commit 60a72f1) — 3 findings, all addressed in c06ca2f

- **[P1]** Bust cached streamline VTPs when the seed policy changes —
  `ensure_streamlines` reused a track0.vtp newer than U, so a pre-existing
  degenerate VTP stayed "fresh" and the seed fix was invisible. → `.seed_policy`
  version marker; reuse only when it matches `_SEED_POLICY_VERSION`.
- **[P2]** Don't use the ingest STL bbox as a seeding fallback — it's the solid
  body for external-flow cases (seeds inside the obstacle). → `_mesh_bbox` uses
  only `polyMesh/points`; binary/unreadable → legacy seeds, never the manifest.
- **[P2]** Invalidate `v4-post-patches` after a solve — a pre-solve open cached
  an empty list 30s, leaving the surface overlay disabled post-solve. → added to
  `useSolveRun` POST_RUN_QUERY_PREFIXES.

## R1 (commit c06ca2f) — 2×P1, all addressed in 731cd34

- **[P1-A]** VTP-base viewport still rendered nothing — `ViewportV4` render body
  had `if (!glbUrl) return null` BEFORE the container div, so the no-GLB mount
  effect found no containerRef. → render guard mirrors the mount gate
  (`!glbUrl && !surfaceVtpUrl && !streamlinesVtpUrl`).
- **[P1-B]** AABB-diagonal seeds land inside the solid on non-convex domains
  (backward-step step at x<2,y<1). → 3D seed grid (5×4×3); streamLine drops
  in-solid seeds, so coverage guarantees fluid seeds survive.

## R2 (commit 731cd34) — 2×P2, applied verbatim in 12b36df (round cap reached)

- **[P2]** Gate the VTP-base path on `successfulRunDetail`, not any `runDetail`
  — a FAILED no-GLB solve mounted a blank canvas instead of the empty state.
- **[P2]** `surface.vtp` guard rejected `.` but `/post/patches` advertises dotted
  names (e.g. `domain.0`) → 400. Guard now allows `.` while rejecting `..`.

## Post-review (commit b6c8209) — bug #5 root cause (self-found, not a Codex finding)

streamLine "seeded 1 particles" was a functionObject filename mismatch
(`system/streamlinesDict` vs the `-func streamlines` lookup of `system/streamlines`),
NOT the suspected ESI-2312-vs-OF10 cross-fork issue. Renaming the written file →
54 tracks / 43336 samples; V4 Post renders |U|-colored streamlines, legend
driven by the real VTP range (0→0.86 m/s). confidence: high (verified live).
This small post-Codex fix was verified end-to-end rather than re-reviewed
(round cap=3 reached; not a security boundary).
