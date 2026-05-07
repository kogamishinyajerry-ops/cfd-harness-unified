# Public CAD Source Catalog (Aerospace + Industrial)

> **Purpose**: curated index of public aerospace / industrial CAD
> repositories Codex should consult **before** generating geometry
> from scratch. Each entry rates fidelity, license, format, and
> known V-series-friendly defects.
>
> **2026-05-07 user addendum**: "建议从公开信息源获取优质的航空工业的
> 部件几何、文件，这样可以减轻 Codex 压力，不必总从 0 开始"

## How Codex uses this catalog

When asked to design a case in solver-class X with industrial
flavor, Codex:

1. Scan this catalog for an entry matching solver-class + component
   need
2. If a match exists → fetch geometry → adapt → inject defect →
   write brief
3. If no match exists → fall back to from-scratch CadQuery
   generation per `codex_case_design_protocol.md`

Codex's case-design response declares which tier (Tier 1 / 2 / 3)
the geometry came from + source URL + license.

## Tier 1 · Published reference geometries (NASA / ONERA / DLR / NREL / etc.)

These are research-grade, validated, and most have reference
experimental + CFD data alongside.

### Aircraft external aerodynamics (high-Re external flow)

| ID | Name | Source | Format | License | What it covers | Reference data |
|---|---|---|---|---|---|---|
| T1.A1 | **NASA CRM** (Common Research Model) | https://commonresearchmodel.larc.nasa.gov/ | STEP / IGES + meshes | NASA public | Wing-body-tail transport aircraft, transonic cruise design point | NASA TMR + AIAA DPW (Drag Prediction Workshop) wind tunnel |
| T1.A2 | **DLR-F6 / F15** | DLR aerospace open archives | STEP | DLR open | Wing-body junction validation cases | DPW wind tunnel data |
| T1.A3 | **ONERA M6 wing** | ONERA public dataset | STEP / mesh | ONERA public | Transonic 3D wing — historical CFD validation case | Schmitt-Charpin pressure measurements |
| T1.A4 | **NASA Trap Wing** | NASA TMR | STEP / mesh | NASA public | High-lift configuration with leading-edge slat + flap | AIAA HiLiftPW (High Lift Prediction Workshop) |
| T1.A5 | **DPW-W1 / W2 wing** | NASA DPW | STEP | NASA public | Drag prediction workshop wing-only configurations | DPW cycle data |
| T1.A6 | **NASA X-57 Maxwell** | NASA OpenMDAO | parametric + STEP | NASA public | Distributed electric propulsion testbed wing | Limited but open |

### Engine components (compressible-RANS, CHT, rotating)

| ID | Name | Source | Format | License | What it covers | Reference data |
|---|---|---|---|---|---|---|
| T1.E1 | **NASA E3 (Energy Efficient Engine)** | NASA Glenn historic archive | reports + some STEP | NASA public | Full HP turbine + LP turbine + combustor concepts | E3 program reports (NASA-TM series) |
| T1.E2 | **NASA Stage 35 / Stage 67 transonic compressor** | NASA Glenn | mesh + reports | NASA public | Single-stage transonic axial compressor | NASA-TP series experimental |
| T1.E3 | **TUDa stator passage** | TU Darmstadt | mesh | open academic | Single transonic stator passage | TUDa wind tunnel + LDV |
| T1.E4 | **GE-NASA Energy-Efficient HPT** | NASA-CR archive | reports | NASA public | High-pressure turbine concept | program documentation |
| T1.E5 | **NASA Combustor C3** | NASA TM/CR | reports + some STEP | NASA public | Annular combustor concept | program documentation |

### Wind turbine (rotating + external)

| ID | Name | Source | Format | License | What it covers | Reference data |
|---|---|---|---|---|---|---|
| T1.W1 | **NREL Phase VI / Phase II** | NREL | mesh + STEP | NREL open | Two-blade research wind turbine | NREL wind tunnel pressure + wake LDV |
| T1.W2 | **NREL 5 MW reference turbine** | NREL OpenFAST | STEP / FAST input | NREL open | Standard offshore wind turbine reference geometry | OpenFAST simulation database |
| T1.W3 | **MEXICO rotor (Model rotor EXperiments In COntrolled conditions)** | TU Delft | mesh | open academic | Three-blade model wind turbine | DNW tunnel data |
| T1.W4 | **DTU 10 MW reference** | DTU Wind Energy | open data | DTU open | Larger reference turbine | DTU simulation reference |

### Helicopter / VTOL (rotating + complex 3D)

| ID | Name | Source | Format | License | What it covers | Reference data |
|---|---|---|---|---|---|---|
| T1.H1 | **HART-II (Higher harmonic control Aeroacoustic Rotor Test)** | DLR | mesh | open academic | 4-bladed model rotor in forward flight | DLR/ONERA wind tunnel |
| T1.H2 | **PSP (Pressure-Sensitive Paint) rotor** | NASA Ames | reports | NASA public | Hover + forward flight rotor | NASA wind tunnel PSP |

### Internal flow / diffuser / nozzle

| ID | Name | Source | Format | License | What it covers | Reference data |
|---|---|---|---|---|---|---|
| T1.I1 | **RAE M2129 S-duct** | RAE / NASA TMR | mesh + reports | open academic | S-shaped intake diffuser | RAE wind tunnel pressure + Mach |
| T1.I2 | **NASA Sajben transonic diffuser** | NASA Lewis (Glenn) | reports | NASA public | Converging-diverging diffuser with shock | NASA wall pressure + Mach |
| T1.I3 | **NASA Energy Efficient Engine inlet** | NASA TMR | mesh | NASA public | Subsonic intake | E3 program data |
| T1.I4 | **NACA scoop intake** | NACA reports | reports + figures | public domain | Submerged inlet | NACA TN/TM series |

## Tier 2 · Open community libraries (verify before consuming)

Higher quantity, variable quality. Use when Tier 1 doesn't fit.

| Source | URL | Notes |
|---|---|---|
| **GrabCAD** | https://grabcad.com | Largest open CAD library; filter by "aerospace" / "industrial" tag. License varies per upload — must check. STEP/IGES common |
| **FreeCAD library** | https://github.com/FreeCAD/FreeCAD-library | Maintained library, mostly mechanical parts, MIT-licensed |
| **CFD-Online community** | https://www.cfd-online.com | Tutorial geometries from open and commercial CFD packages, often with reference data |
| **Open Aerospace** | https://github.com/OpenAerospaceEngineering | Open CAD + analysis projects, MIT/BSD |
| **NASA Open Data** | https://data.nasa.gov | Datasets including some CAD; search "STEP" filter |
| **OpenAI Whisper-style aerospace datasets** | (varies) | Depends on what's released — check periodically |
| **Wikimedia 3D files** | https://commons.wikimedia.org | Some technical drawings + 3D files, CC-BY |

**License caution**: Tier 2 sources vary widely. Codex must report
the license of any consumed geometry. CC-BY / MIT / Apache are
fine. If license unclear or restrictive, fall back to Tier 1 or
Tier 3.

## Tier 3 · Codex from-scratch via CadQuery / FreeCAD CLI

Used when Tier 1/2 doesn't fit OR when component is too generic
(simple heat sink, simple manifold) to merit a published
reference. See `codex_case_design_protocol.md` Deliverable 2 for
generation script schema.

## Adapter pipeline (Tier 1/2 → sub-session ready)

Public sources rarely come in the exact format the case-thread
needs. Codex's adapter step:

1. **Download** STEP/IGES from source
2. **Open in FreeCAD** to inspect (CLI script that reports body
   count, bbox, face count per body)
3. **Rename bodies** to match OpenFOAM patch naming rules
   (`^[A-Za-z][A-Za-z0-9_]*$`) — public CAD often has French/
   German/numeric names from origin source
4. **Decimate** if face count > 100k per body (trigger A3
   geometry surgery)
5. **Inject defect(s)** per `component_bank.md` Defect Catalog —
   even on a NASA CRM STEP, deliberate defect injection keeps
   V-series productive
6. **Re-export STEP** to the case sandbox
7. **Write parts manifest** mapping renamed bodies to CFD roles

Codex's CAD generation script (Deliverable 2 of the protocol)
handles the entire chain: download (or use cached) → adapt →
inject → export. The script must be **deterministic** — given
the same source URL + parameters, regenerates byte-identical STEP.

## Defect injection on Tier-1 sources (extra care)

When the geometry comes from a published reference (NASA CRM,
ONERA M6 etc.), the validation community has expectations about
that geometry. Codex must:

1. **Document the unmodified reference**: which exact source URL +
   version was downloaded
2. **Document the injection**: which catalog defects were added,
   where, why
3. **Keep the injection localized**: do NOT modify regions where
   reference experimental data is taken — e.g. on NASA CRM, do
   not inject defects in the wing pressure-tap region; inject at
   wing-body junction or fuselage tail instead
4. **Note in defect manifest**: `"reference_data_validity:
   preserved | partial | invalidated"` — sub-session should NOT
   compare to wind tunnel data on regions affected by defect

## Caching policy

Public-source geometries are cached at:

```
.planning/cad_cache/
├── tier1_nasa_crm_stp.json       ← metadata + cached STEP path
├── tier1_onera_m6_wing.step      ← cached download
└── tier2_grabcad_<hash>.step
```

Cache directory is **gitignored** (large binaries) but metadata
JSONs are committed. Codex's CAD script first checks cache; only
re-downloads if cache miss or version drift.

This avoids redundant downloads across cases AND establishes
reproducibility (case_004 + case_005 both using NASA CRM use the
exact same source revision).

## Update cadence for this catalog

Update when:
- A new public release happens (NASA, ONERA, DLR publish new
  geometry)
- A community source proves consistently high-quality (promote
  Tier 2 → Tier 1-equivalent annotation)
- A source goes offline (mark deprecated)
- A license changes (re-evaluate)
- A case-thread successfully consumes a new Tier-2 source —
  promote it for visibility

## References

- `codex_case_design_protocol.md` — uses this catalog as Tier 1
  source priority
- `component_bank.md` — Tier-3 fallback components
- `case_proposal_queue.md` — Codex-fed case roster

## Quick-start fetch URLs (verify each before use; URLs may move)

- NASA Common Research Model: https://commonresearchmodel.larc.nasa.gov/
- NASA Turbulence Modeling Resource (validation cases): https://turbmodels.larc.nasa.gov/
- ONERA open data: https://www.onera.fr/en/scientific-publications
- NREL National Wind Technology Center: https://www.nrel.gov/wind/
- DLR institutional repository: https://elib.dlr.de/
- NASA Technical Reports Server: https://ntrs.nasa.gov/
- AIAA Drag/HiLift Prediction Workshops: search "AIAA DPW HiLiftPW"
- GrabCAD aerospace tag: https://grabcad.com/library/category/aerospace
- FreeCAD library: https://github.com/FreeCAD/FreeCAD-library

URL accuracy validated 2026-05-07 evening; if a source moved,
update this file.
