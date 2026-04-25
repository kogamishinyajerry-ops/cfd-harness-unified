# DEC-V61-059 — Codex round-5 review (post-R3 live-run defect stack)

- **Branch**: `dec-v61-059-pc`
- **Reviewed commits**: `a71e8ec`, `4af21a2`, `59198cf`, `42158e2`, plus fixture/doc follow-ups `0a90dea`, `522eaa0`
- **Verdict**: **CHANGES_REQUIRED**

## Findings

### P2 — `src/plane_channel_uplus_emitter.py:177-180,191-197`
The OpenFOAM-10-first reader no longer honors the `field` parameter once `<set_name>.xy` exists. The code always prefers `channelCenter.xy` and always reads column 2 as `Ux`, so a call such as `_read_uline_profile(..., field="p")` silently returns the packed `U` data when both `channelCenter.xy` and `channelCenter_p.xy` coexist. That is a silent wrong-file / wrong-column read, not just a fallback preference issue.

- **Suggested fix**: Either make the function explicitly U-only on the OF10 path (`field != "U"` must skip or reject packed-file parsing), or parse the packed-file header/layout so the requested field is resolved correctly. Add a regression test with both `channelCenter.xy` and `channelCenter_p.xy` present.

### P2 — `scripts/render_case_report.py:373-378`; `src/metrics/residual.py:94-100`; `src/audit_package/manifest.py:51-60,210-212`
The `icoFoam -> pisoFoam` and `turbulenceProperties -> momentumTransport` surface change is not propagated to several downstream consumers. These helpers still hard-code the old log/input names, so current plane-channel Stage B artifact dirs that only contain `log.pisoFoam` no longer round-trip cleanly through report/evidence tooling. On the actual artifact dir `reports/phase5_fields/plane_channel_flow/20260425T121319Z`, `src.metrics.residual._resolve_log_path()` returns `None`, and `src.audit_package.manifest._load_run_outputs()` / `_load_run_inputs()` both return `{}`.

- **Suggested fix**: Teach the downstream helpers to accept `log.pisoFoam` and `constant/momentumTransport`, or better, scan `log.*` generically and accept both `momentumTransport` and `turbulenceProperties` as versioned equivalents. Add focused regression tests that use a minimal plane-channel artifact tree containing only `log.pisoFoam`.

## Requested Checks

- **Adapter**: The dispatch flip at `src/foam_agent_adapter.py:645-648` is correct. `solver_name = "pisoFoam"` is consistent with `controlDict` (`3829`) and the staging whitelist that now includes `log.pisoFoam` (`7943-7949`).
- **F1 trust semantics**: `_emits_rans_path = False` at `3608` is still load-bearing. `effective_turbulence_used` and `_momentum_transport_body` are both gated off the same flag, so the laminar stamp remains honest until A.4.b flips the real RANS path on.
- **Schemes / solver block**: `interpolationSchemes` and `snGradSchemes` are correctly formed, and `div((nuEff*dev2(T(grad(U)))))` matches the `pisoFoam` + `momentumTransport` path rather than the old `icoFoam` path. The GAMG stanza does not appear to be missing any required OF10 keys; the omitted knobs are optional tuning parameters, not correctness requirements.
- **Back-compat**: No extra shim is needed in the main execution path; `src/task_runner.py:500-510` already resolves `log.*` generically. The stale consumers are the helper/report layers called out in the P2 finding above.
- **Emitter ordering**: OF10-form-first is fine for the current U-only production path, but it is not safe as a general `field`-aware API. The current implementation is only correct because the only in-tree call site still uses the default `field="U"`.
- **Tests**: The new direct-generator assertions are good and already include the negative guards the review asked about (`"icoFoam" not in controlDict`, no legacy `turbulenceProperties` file). The remaining coverage gap is downstream helper discovery (`log.pisoFoam`, `momentumTransport`) and OF10 packed-file field selection.
- **Intake / fixture commits**: `.planning/intake/DEC-V61-059_plane_channel_flow.yaml:522-556` accurately describes what shipped. `ui/backend/tests/fixtures/runs/plane_channel_flow/audit_real_run_measurement.yaml:12-25` is consistent with commit `42158e2`, and the `audit_real_run.json` timestamp bump is acceptable under the existing byte-repro contract because timestamp/commit SHA are the explicitly allowed moving fields.

## Methodology Amendment

Yes: this defect class warrants an intake-level flag. I would promote something like `openfoam_version_emitter_api_drift` to **HIGH** risk for any case that depends on OpenFOAM-generated auxiliary files or registry objects (`momentumTransport`, function-object outputs, solver-log naming). This Stage B stack surfaced three variants of the same underlying hazard, and all three are predictable once that class is named explicitly up front.

## Verification Notes

- Review method: source diff inspection, line-by-line file reads, and direct local probes against the current Stage B artifact directory.
- Direct probes confirmed:
  - `_read_uline_profile(..., field="p")` prefers `channelCenter.xy` over `channelCenter_p.xy` when both exist.
  - `src.metrics.residual._resolve_log_path()` returns `None` for the current `log.pisoFoam`-only plane-channel artifact dir.
  - `src.audit_package.manifest` run-input/output loaders return empty dicts for that same artifact dir.
- I also attempted the touched pytest slices, but the host interpreter in this session is missing `PyYAML`, so `tests/test_foam_agent_adapter.py`, `tests/test_metrics/test_residual.py`, and `tests/test_audit_package/test_manifest.py` cannot be fully collected here. `tests/test_plane_channel_uplus_emitter.py::test_read_uline_profile_reads_of10_filename` does run and pass under the available interpreter.
