**Quick verdict**  
This is numerics-first, not physics-first: high confidence (~0.85) that the ~150 K bulk-temperature miss is mainly enthalpy smearing from `Co≈35,000` with first-order energy transport, with missing radiation only a secondary underprediction.

**Corpus citations**  
- `ENGINEERING_CAVEAT.md` already identifies the same three drivers: `Euler` + `dt=1.0 s` at `CFL_max≈35,000`, `limitedLinear 1` collapsing toward upwind across the 615 K / 328 K interface, and fully active `cellLimited grad` flattening the jet shear layer [CAVEAT §Known physical deviation].  
- V12 is relevant procedurally: this kind of mass/energy sanity check should be a configuration-time gate, not something discovered after the run.  
- V15 is relevant diagnostically: when the fluid-side transport numerics are shared, the same dissipation failure mode carries across buoyant solver variants rather than being a one-off postprocessing artifact.

**Root cause decomposition**  
- `Co≈35,000 + Euler`: giant first-order pseudo-time steps make the hot jet behave like convection plus artificial diffusion, so hot enthalpy never propagates cleanly into the bay bulk. Weight: about 65-75 K of the 150 K deficit [CAVEAT §Known physical deviation].  
- `div(phi,h)=limitedLinear 1`: at the strongest combustor/farfield temperature jump, the limiter falls back toward first-order upwind, bleeding plume enthalpy out exactly where second-order transport matters most. Weight: about 45-55 K [CAVEAT §Known physical deviation].  
- `gradSchemes cellLimited 1`: plume-edge and shear-layer gradients are clipped before the convection scheme sees them, so downstream thermal spread stays too cold and too compact. Weight: about 20-30 K [CAVEAT §Known physical deviation].

**What’s still usable from this run**  
You can still use the qualitative flow topology: jet direction, suction path to the intake, recirculation pockets, hotspot localization at the combustor outlet, and relative wall-cooling patterns around the fixed-temperature bodies. I would not use it for absolute bay bulk temperature, downstream thermal penetration length, or any derived `h_conv` / cooling-margin number.

**Four upgrade paths**  
- Minimal rescue rerun: `adjustTimeStep`, `maxCo 5-10`, `backward`, same mesh and BCs. ETA 1-2 days wall on 4-core ARM, roughly 100-200 core-hours. Expected gain: recover about 70-100 K of the missing bulk temperature.  
- Scalar-transport upgrade: replace `limitedLinear 1` on `h` with a bounded second-order scalar scheme and back off full gradient clipping. ETA 0.5 day setup + 1-2 days wall, roughly 60-120 core-hours. Expected gain: another 30-50 K plus a more realistic plume footprint.  
- Resolution upgrade: add 5-6 prism layers and local jet/shear refinement. ETA 1 day meshing + 2-4 days wall, roughly 200-400 core-hours. Expected gain: better wall heat-transfer fidelity and less plume collapse.  
- Physics completion: add radiation first, then CHT only if wall-load decisions depend on it. Radiation is about 1-2 extra days on 4-core ARM, roughly 80-160 core-hours, and likely adds local heating; it compounds the miss, but it does not explain the missing 150 K by itself.

**What I’m NOT telling you**  
I’m not proving global enthalpy conservation from integrated fluxes here; this is a ranked diagnosis from the scheme/time-step signature plus the field pattern. I’m also not saying radiation is negligible, only that it is secondary to the transport numerics for this specific 30% bulk-temperature miss.

Advisory only: use this to choose the rerun, not to declare the thermal balance closed.
