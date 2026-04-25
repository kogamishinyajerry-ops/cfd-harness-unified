# DEC-V61-059 — Codex round-6 (Stage B sub-arc round 2)

- Branch: dec-v61-059-pc (sub-arc base fb2ea78 → tip eb67a96)
- Reviewed: F7 + F8 fix landings (commit eb67a96)
- Verdict: APPROVE_WITH_COMMENTS
- Findings: 2

## Findings

### P3 — `tests/test_plane_channel_uplus_emitter.py:259-297`
The F7 code path is now correct, but the regression suite still never creates `channelCenter.xy` and `channelCenter_p.xy` in the same directory. Round-5's exact bug was a mixed-file precedence issue; the new tests cover "OF10-only p request" and "legacy-only p request" separately, but not the coexistence case in one fixture.
Suggested fix: add one coexistence test that asserts `field="U"` resolves `channelCenter.xy` and `field="p"` resolves `channelCenter_p.xy` when both files are present.

### P3 — `scripts/render_case_report.py:373-387`; `src/metrics/residual.py:94-104`; `src/audit_package/manifest.py:215-226`
The F8 widening is functionally sufficient for a `log.pisoFoam`-only Stage B artifact dir, but the three helpers still do not share one canonical log-preference order: render/manifest check `icoFoam` before `pisoFoam`, while residual checks `pisoFoam` before `icoFoam`. Mixed-log dirs would therefore resolve different logs depending on the consumer.
Suggested fix: centralize the log-name tuple or at minimum align the local tuples across all three helpers.

## Stage B sub-arc closure
F7's field gating itself looks clean: I do not see a correctness case where the legacy `_U` file should outrank `channelCenter.xy` for `field=="U"`; preferring OF10's packed file is the safer fail-closed choice when it exists. F8 also closes the live-run round-trip for the current plane-channel artifact shape: `log.pisoFoam` and `constant/momentumTransport` are now accepted by the reviewed downstream consumers, and within the allowed scope I did not see another missed consumer beyond the resolver-order divergence above. The post-R3 + sub-arc-r1 stack now satisfies intake section 9's Stage E live-run executable-smoke bar (real solver run, extractor path, truthful FAIL fixture), with the two comments above as post-smoke hardening rather than closure blockers.
