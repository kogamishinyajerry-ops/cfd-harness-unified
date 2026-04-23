VERDICT: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED | RETRACT

FINDINGS:
  #1 [HIGH|MED|LOW] <title>
      file:line
      evidence: <what you observed>
      suggested fix: <what to change>
      
  #2 [...]
  ...

SUMMARY:
  <one paragraph overall assessment, including whether -37% Xr miss is
  acceptable-with-documentation or requires a retry with different schemes
  before DEC-V61-052 can close>
```

VERDICT: CHANGES_REQUIRED

FINDINGS:

#1 [HIGH] Audit Xr is extracted from the wrong probe path
file: [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:595), [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:8137), [audit_real_run_measurement.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/fixtures/runs/backward_facing_step/audit_real_run_measurement.yaml:20)
evidence: The generated `sampleDict` defines `wallProfile` at `y=0.025`, but runtime only runs `postProcess -funcs '(writeObjects writeCellCentres)'`, not `sample`. The YAML value `1.7256339869` matches the cell-centre fallback at `y=0.5 ± 0.15`, not the near-wall probe. I recomputed from the fixture VTK: fallback `y=0.5±0.15` gives `Xr/H=1.7256`; point probe `y=0.025` gives `Xr/H=3.9523`.
suggested fix: Make the authoritative audit extractor either run and parse `wallProfile`, or replace it with a wall-shear extractor. Store `source`, `probe_height`, and `method` in `key_quantities`/fixture YAML.

#2 [HIGH] Preflight marks an outside-tolerance scalar as “safe to visualize”
file: [knowledge/gold_standards/backward_facing_step.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/knowledge/gold_standards/backward_facing_step.yaml:43), [scripts/preflight_case_visual.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/preflight_case_visual.py:121)
evidence: `contract_status` says `Xr/H≈3.95` is `~37%` below 6.26 and outside 10%, but the status string lacks `fail/hazard/partial/compatible`, so `_check_gold_status()` returns PASS. I ran preflight and it exited 0 with `GREEN · safe to visualize`.
suggested fix: Add a structured scalar-contract check to preflight, or rename status to an explicit fail/open state like `GEOMETRY_GREEN_XR_FAIL_OUTSIDE_TOLERANCE`. Do not let Batch D key only off G3/G4/G5 + geometry.

#3 [MED] Near-wall Ux zero-crossing is a useful proxy, not the true reattachment observable
file: [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:1805), [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:7505)
evidence: The recirculation signal is real, not noise: near-wall `Ux` reaches about `-0.245 U_bulk`, far above the residual floor. But true BFS reattachment is the `tau_w` / `Cf` sign change at the wall. Height sensitivity is material: VTK point probes give `Xr/H≈3.95` at `y=0.025`, `3.88` at `y=0.05`, `3.29` at `y=0.25`, and `1.78` at `y=0.5`.
suggested fix: Emit/parse `wallShearStress` on `lower_wall`, filter downstream floor faces `x>0,y=0`, then find the first `tau_x` sign change. Keep `Ux(y=0.025)` as a diagnostic/SNR cross-check.

#4 [MED] The -37% Xr miss should not be attributed to “known k-epsilon envelope” yet
file: [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:6806), [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:6858), [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:1456)
evidence: The mesh is legal, but still crude for the shear layer: B2 has only 16 uniform cells over `8H`, and all blocks use `simpleGrading (1 1 1)`. The inlet is uniform `U=(1,0,0)` after only `10H` upstream length, with no measured BL, precursor, or mapped inlet. This can plausibly shorten recirculation independently of the turbulence model.
suggested fix: Before blaming standard k-epsilon, run a bounded matrix: graded/refined shear-layer mesh, wall-shear Xr extractor, realistic inlet BL or precursor, then RNG k-epsilon and kOmegaSST comparison.

#5 [LOW] Convergence is stable, but metric stationarity is not yet demonstrated
file: [log.simpleFoam](/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/backward_facing_step/20260423T082933Z/log.simpleFoam:10050)
evidence: This is not the V61-051 false convergence: fields are finite, turbulence scalars are positive, continuity is `7.31e-9`, and residuals are small. But initial residuals still drop about 28-36% over the last 100 iterations, so “genuinely converged” should be limited to “stable, finite, no divergence” unless Xr is shown stationary across late write times.
suggested fix: Add a metric-stationarity gate: compare Xr from `t=800/900/1000` or require late-window residual and Xr drift below a threshold.

SUMMARY:
Geometry Batch A is structurally sound: the 3-block topology, void exclusion, patch normals, and block-interface cell counts check out. Batch B also fixes the catastrophic k/epsilon blow-up. The blocker is measurement and claim discipline: the audit YAML’s `1.7256` is from the wrong fallback probe, the `3.95` near-wall value is a real signal but not wall shear, and the -37% miss is too large to close as “k-epsilon under-prediction” without mesh/BC/model sensitivity. Batch D should not publish the figure yet; among your three stances, choose “do not publish until Xr is measured by wall shear and the tolerance miss is either fixed or deliberately presented as a failed diagnostic case.”

VERDICT: CHANGES_REQUIRED

FINDINGS:

#1 [HIGH] Audit Xr is extracted from the wrong probe path
file: [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:595), [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:8137), [audit_real_run_measurement.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/fixtures/runs/backward_facing_step/audit_real_run_measurement.yaml:20)
evidence: The generated `sampleDict` defines `wallProfile` at `y=0.025`, but runtime only runs `postProcess -funcs '(writeObjects writeCellCentres)'`, not `sample`. The YAML value `1.7256339869` matches the cell-centre fallback at `y=0.5 ± 0.15`, not the near-wall probe. I recomputed from the fixture VTK: fallback `y=0.5±0.15` gives `Xr/H=1.7256`; point probe `y=0.025` gives `Xr/H=3.9523`.
suggested fix: Make the authoritative audit extractor either run and parse `wallProfile`, or replace it with a wall-shear extractor. Store `source`, `probe_height`, and `method` in `key_quantities`/fixture YAML.

#2 [HIGH] Preflight marks an outside-tolerance scalar as “safe to visualize”
file: [knowledge/gold_standards/backward_facing_step.yaml](/Users/Zhuanz/Desktop/cfd-harness-unified/knowledge/gold_standards/backward_facing_step.yaml:43), [scripts/preflight_case_visual.py](/Users/Zhuanz/Desktop/cfd-harness-unified/scripts/preflight_case_visual.py:121)
evidence: `contract_status` says `Xr/H≈3.95` is `~37%` below 6.26 and outside 10%, but the status string lacks `fail/hazard/partial/compatible`, so `_check_gold_status()` returns PASS. I ran preflight and it exited 0 with `GREEN · safe to visualize`.
suggested fix: Add a structured scalar-contract check to preflight, or rename status to an explicit fail/open state like `GEOMETRY_GREEN_XR_FAIL_OUTSIDE_TOLERANCE`. Do not let Batch D key only off G3/G4/G5 + geometry.

#3 [MED] Near-wall Ux zero-crossing is a useful proxy, not the true reattachment observable
file: [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:1805), [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:7505)
evidence: The recirculation signal is real, not noise: near-wall `Ux` reaches about `-0.245 U_bulk`, far above the residual floor. But true BFS reattachment is the `tau_w` / `Cf` sign change at the wall. Height sensitivity is material: VTK point probes give `Xr/H≈3.95` at `y=0.025`, `3.88` at `y=0.05`, `3.29` at `y=0.25`, and `1.78` at `y=0.5`.
suggested fix: Emit/parse `wallShearStress` on `lower_wall`, filter downstream floor faces `x>0,y=0`, then find the first `tau_x` sign change. Keep `Ux(y=0.025)` as a diagnostic/SNR cross-check.

#4 [MED] The -37% Xr miss should not be attributed to “known k-epsilon envelope” yet
file: [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:6806), [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:6858), [src/foam_agent_adapter.py](/Users/Zhuanz/Desktop/cfd-harness-unified/src/foam_agent_adapter.py:1456)
evidence: The mesh is legal, but still crude for the shear layer: B2 has only 16 uniform cells over `8H`, and all blocks use `simpleGrading (1 1 1)`. The inlet is uniform `U=(1,0,0)` after only `10H` upstream length, with no measured BL, precursor, or mapped inlet. This can plausibly shorten recirculation independently of the turbulence model.
suggested fix: Before blaming standard k-epsilon, run a bounded matrix: graded/refined shear-layer mesh, wall-shear Xr extractor, realistic inlet BL or precursor, then RNG k-epsilon and kOmegaSST comparison.

#5 [LOW] Convergence is stable, but metric stationarity is not yet demonstrated
file: [log.simpleFoam](/Users/Zhuanz/Desktop/cfd-harness-unified/reports/phase5_fields/backward_facing_step/20260423T082933Z/log.simpleFoam:10050)
evidence: This is not the V61-051 false convergence: fields are finite, turbulence scalars are positive, continuity is `7.31e-9`, and residuals are small. But initial residuals still drop about 28-36% over the last 100 iterations, so “genuinely converged” should be limited to “stable, finite, no divergence” unless Xr is shown stationary across late write times.
suggested fix: Add a metric-stationarity gate: compare Xr from `t=800/900/1000` or require late-window residual and Xr drift below a threshold.

SUMMARY:
Geometry Batch A is structurally sound: the 3-block topology, void exclusion, patch normals, and block-interface cell counts check out. Batch B also fixes the catastrophic k/epsilon blow-up. The blocker is measurement and claim discipline: the audit YAML’s `1.7256` is from the wrong fallback probe, the `3.95` near-wall value is a real signal but not wall shear, and the -37% miss is too large to close as “k-epsilon under-prediction” without mesh/BC/model sensitivity. Batch D should not publish the figure yet; among your three stances, choose “do not publish until Xr is measured by wall shear and the tolerance miss is either fixed or deliberately presented as a failed diagnostic case.”

