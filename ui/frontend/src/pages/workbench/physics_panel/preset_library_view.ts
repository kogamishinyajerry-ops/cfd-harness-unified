// DEC-V61-142 (N3.3) · Frontend mirror of services/physics/{materials,regimes}_library.py.
//
// Mirroring rationale: the dropdown options need to exist before the
// engineer's first POST, so loading them via a separate fetch would
// flicker the UI on case open. The library is small enough (4 + 4
// entries v0) and changes infrequently enough that mirroring is
// cheaper than a /api/physics/presets fetch round-trip.
//
// PARITY DISCIPLINE: when materials_library.py / regimes_library.py
// change, this file MUST be updated in the same commit. Tests assert
// citation parity per preset_id.

import type {
  MaterialPresetView,
  RegimePresetView,
} from "@/types/physics";

export const MATERIAL_PRESETS_VIEW: MaterialPresetView[] = [
  {
    preset_id: "water_20c",
    display_name: "water · 20°C, 1 atm",
    citation:
      "https://webbook.nist.gov/cgi/fluid.cgi?ID=C7732185&Action=Page",
    fluid: {
      name: "water",
      density: 998.21,
      kinematic_viscosity: 1.0034e-6,
      prandtl: 7.01,
    },
    thermal: { specific_heat: 4184.0, thermal_conductivity: 0.598 },
    notes:
      "Saturated liquid water at 20°C; NIST WebBook reference state.",
  },
  {
    preset_id: "air_20c",
    display_name: "air · 20°C, 1 atm",
    citation:
      "https://webbook.nist.gov/cgi/fluid.cgi?ID=C132259100&Action=Page",
    fluid: {
      name: "air",
      density: 1.2041,
      kinematic_viscosity: 1.516e-5,
      prandtl: 0.7296,
    },
    thermal: { specific_heat: 1005.0, thermal_conductivity: 0.0257 },
    notes: "Dry air at sea-level reference state; NIST WebBook.",
  },
  {
    preset_id: "air_20c_isothermal",
    display_name: "air · 20°C · isothermal (no thermal block)",
    citation:
      "https://webbook.nist.gov/cgi/fluid.cgi?ID=C132259100&Action=Page",
    fluid: {
      name: "air",
      density: 1.2041,
      kinematic_viscosity: 1.516e-5,
      prandtl: null,
    },
    thermal: null,
    notes:
      "Same air @ 20°C with thermal block stripped — for isothermal " +
      "simpleFoam / pisoFoam runs.",
  },
  {
    preset_id: "oil_iso_vg_46_40c",
    display_name: "oil · ISO VG 46 lubricant @ 40°C",
    citation:
      "https://www.machinerylubrication.com/Read/2/Lubricant-Viscosity",
    fluid: {
      name: "oil_vg46",
      density: 860.0,
      kinematic_viscosity: 4.6e-5,
      prandtl: 350.0,
    },
    thermal: { specific_heat: 1900.0, thermal_conductivity: 0.13 },
    notes:
      "ISO Viscosity Grade 46 — representative mineral hydraulic / " +
      "lubricant oil.",
  },
];

export const REGIME_PRESETS_VIEW: RegimePresetView[] = [
  {
    preset_id: "laminar_internal_default",
    display_name: "laminar · internal flow (Re < 2300)",
    citation:
      "https://link.springer.com/book/10.1007/978-3-662-52919-5",
    regime: "laminar",
    applicability: {
      re_min: 0.0,
      re_max: 2300.0,
      mach_max: 0.3,
      y_plus_target: null,
    },
    notes:
      "Pipe-flow laminar/turbulent transition is conventionally Re ≈ 2300.",
  },
  {
    preset_id: "rans_ras_kepsilon_default",
    display_name: "RANS · k-ε (industrial baseline)",
    citation: "https://www.dcwindustries.com/turbulence-modeling-for-cfd",
    regime: "RANS-RAS",
    applicability: {
      re_min: 1.0e3,
      re_max: null,
      mach_max: 0.3,
      y_plus_target: 30.0,
    },
    notes:
      "Standard k-ε with wall functions; valid above Re ≈ 1000 for " +
      "fully turbulent flows.",
  },
  {
    preset_id: "rans_komegasst_default",
    display_name: "RANS · k-ω SST (industrial default)",
    citation: "https://doi.org/10.2514/3.12149",
    regime: "RANS-kOmegaSST",
    applicability: {
      re_min: 1.0e3,
      re_max: null,
      mach_max: 0.3,
      y_plus_target: 1.0,
    },
    notes:
      "Menter's SST blends k-ω near walls with k-ε in free-stream; " +
      "industrial default for wall-bounded incompressible RANS.",
  },
  {
    preset_id: "les_stub_placeholder",
    display_name: "LES · sub-grid model TBD (placeholder)",
    citation: "https://link.springer.com/book/10.1007/b137536",
    regime: "LES-stub",
    applicability: {
      re_min: 1.0e4,
      re_max: null,
      mach_max: 0.3,
      y_plus_target: 1.0,
    },
    notes:
      "Forward-compatibility placeholder — actual sub-grid model " +
      "selection deferred to M3-extend.",
  },
];
