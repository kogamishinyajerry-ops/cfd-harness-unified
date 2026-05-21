# Reference data provenance — channel_flow_rans_sst

## Source

NASA Turbulence Modeling Resource (TMR), plane channel flow page —
**Moser, Kim, & Mansour (1999) DNS at Re_tau ≈ 590**.

- TMR page (mirror): https://turbmodels.larc.nasa.gov/Channel/channel.html
- Original DNS dataset publication:
  Moser, R. D., Kim, J., & Mansour, N. N. (1999).
  "Direct numerical simulation of turbulent channel flow up to Re_τ = 590."
  *Physics of Fluids*, 11(4), 943–945.
  https://doi.org/10.1063/1.869966
- Original source: NASA Ames Research Center, Reynolds stress + velocity
  profile database used as the canonical RANS validation reference.
- License: NASA published data, U.S. Government work, public domain
  in the United States. No restrictions on use, modification, or
  redistribution.

## What we kept

The published DNS data is a set of statistical profiles (velocity, Reynolds
stresses, dissipation) versus wall-normal coordinate `y+`. The harness uses
a **scalar derived quantity** — the skin friction coefficient `Cf` based on
the bulk velocity normalization:

```
Cf = 2 * (u_tau / U_bulk)^2
```

For the MKM 1999 dataset at Re_tau = 590:
- u_tau = 1.0 (normalized friction velocity)
- U_bulk = 18.00 (in wall units, integrated from the DNS mean velocity profile)
- **Cf_DNS = 0.00617** (using the standard bulk-velocity normalization)

This single Cf value is replicated along the streamwise coordinate x_m in
the reference CSV — channel flow is by construction homogeneous in x once
fully developed, so the reference is a constant along the streamwise extent
of the comparison window.

Format: 2-column CSV with header `x_m,Cf`. 11 rows (x ∈ [1.5, 2.0] m, step 0.05 m).

## Canonical case conditions (reference)

- Domain: plane channel, half-height H_ref dimensionless = 1.0 (DNS normalization)
- Re_tau = 590 (friction Reynolds number)
- Equivalent Re_2H ≈ 21,500 (bulk Reynolds number)
- Wall-resolved DNS (no wall function)

## Local case conditions vs reference

Our `case_manifest.yaml`:
- Channel half-height H = 0.015 m → 2H = 0.03 m
- Bulk velocity U_bulk = 10 m/s
- Kinematic viscosity ν = 1.5e-5 m²/s
- Re_2H = U_bulk × 2H / ν = **20,000** (vs reference 21,500; ~7% mismatch)
- Turbulence model: k-omega SST (RANS, vs DNS reference)
- Wall treatment: high-Re wall function (vs DNS wall-resolved)

The Re mismatch is small (~7%); the dominant uncertainty is the wall
treatment (RANS+wall-function vs DNS+wall-resolved). Per the harness
honesty convention, the tolerance is widened from the canonical 0.05 to
**0.10** to accommodate these two systematic gaps. A FAIL inside this
tolerance window is then attributable to a real harness / case-setup
defect, not just modeling assumptions.

## Comparison window

`x_min_compare_m: 1.5` (developed region only). The first 1.5 m of the
channel is where the boundary layer is still developing from the uniform
plug-flow inlet; comparing Cf in that region against fully-developed DNS
would conflate two distinct physical states. By restricting comparison
to x ≥ 1.5 m (75% of channel length downstream), we compare DNS-like
fully-developed flow against the simulator's late-domain Cf.

## How to regenerate (in case of upstream data change)

The reference CSV is hand-written from the published Cf scalar. If the
NASA TMR page updates with a different normalization, regenerate via:

```python
# u_tau / U_bulk ratio for MKM 1999 Re_tau=590 (per Table III of paper)
u_tau_over_U_bulk = 1.0 / 18.0
Cf = 2 * u_tau_over_U_bulk**2  # → 0.00617
# Write a constant-value CSV from x_min to channel end
```

The same SHA-256 will then attest to the regenerated file's content.
