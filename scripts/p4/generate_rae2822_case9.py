#!/usr/bin/env python3
"""P4 V73.B · RAE 2822 Case 9 live-probe case generator (stdlib only).

Produces a complete ESI v2312 rhoSimpleFoam + kOmegaSST case for the AGARD
AR-138 Case 9 operating point (wall-interference-corrected free-air
convention: M=0.734, alpha=2.79 deg, Re_c=6.5e6 — gold SSOT
knowledge/gold_standards/rae2822_case9.yaml).

DESIGN PROVENANCE (every block has an in-repo or vendor precedent)
------------------------------------------------------------------
- Geometry: knowledge/geometry/rae2822_selig.dat — UIUC Airfoil Coordinates
  Database (m-selig.ae.illinois.edu/ads/coord/rae2822.dat, fetched via the
  airfoiltools.com Selig mirror 2026-06-10, sha256 88ab8c6b...). 65+65 pts,
  validated: t/c max 0.1220 @ x/c=0.4266; sharp TE at (1,0); the lower
  surface crosses z=0 at x/c~0.916 (the aft-loading that motivated the
  contour-split extractor, loop-auditor V73.A F6).
- Mesh: the in-repo 6-block C-grid topology proven by the naca0012
  showcase (src/foam_agent_adapter.py blockMeshDict, 4 live AoA runs), with:
  domain enlarged to x in [-15c, +20c], z in +/-15c (transonic far-field +
  circulation decay), wall-normal cells 220 with geometric grading sized for
  y+ <= 1 at Re 6.5e6 (B109 spec), the two far-field patches MERGED into a
  single `farfield` patch, and the surface edges as spline-sampled polyLine
  (NOT triSurface projection — see below).
- WHY polyLine not `project`: the naca0012 dict seeds edge points on the
  straight chord between block vertices and closest-point-projects them onto
  the triSurface. On the CAMBERED RAE 2822 aft section the upper-edge chord
  runs closer to the LOWER surface (rear loading), so projection flips
  branch around x/c~0.886 — observed as 606 severely-non-orthogonal faces
  (max 89.8 deg) along one grid line at first build. polyLine samples the
  airfoil spline directly per branch: no projection, no ambiguity
  (vendor precedent: tutorials/incompressible/pimpleFoam/LES/wallMountedHump;
  v2312 polyLineEdge.C: dict points are INTERMEDIATE, endpoints come from
  block vertices — so vertex anchors are evaluated on the same spline).
- WHY one farfield patch: the freestreamProbe (gate C0, measured-freestream
  three-way check) area-averages the SOLVED boundary field. A lifting
  airfoil's bound vortex induces ~0.37 deg of upwash at 10c upstream —
  enough to trip the 0.2-deg alpha gate if the probe reads only an upstream
  face. Averaged over the FULL closed outer boundary the circulation term
  cancels to dipole order (vector mean of a point-vortex field over a
  closed contour around it is ~0), so the probe reads the true freestream.
- Schemes/solution/thermo/BC families: ESI v2312 vendor tutorial
  compressible/rhoSimpleFoam/aerofoilNACA0012 (transonic-airfoil-tuned:
  linearUpwind limited momentum/energy, upwind turbulence, rho relax 0.01,
  pMin/MaxFactor) — lifted verbatim, with two deliberate deviations:
    (a) transport const -> sutherland (B109 spec; As/Ts standard air);
    (b) nutkWallFunction -> nutUSpaldingWallFunction (continuous-blend,
        valid at y+<1 — V71.B resolved-wall precedent, DEC-V61-235).
- FO contract: exactly what src/transonic_airfoil_extractor.py consumes —
  forceCoeffs1/coefficient.dat (alpha-rotated lift/drag dirs), surfaces-FO
  raw airfoilSurface/<t>/p_aerofoil.raw, surfaceFieldValue freestreamProbe
  with Time + areaAverage(p/T/U) columns.

Usage:  python3 scripts/p4/generate_rae2822_case9.py <output_case_dir>
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COORDS = REPO / "knowledge" / "geometry" / "rae2822_selig.dat"

# ---- operating point (matches the gold SSOT; gate C0 checks all 3 legs) ----
MACH = 0.734
ALPHA_DEG = 2.79
RE_C = 6.5e6
CHORD = 1.0
T_INF = 288.15
GAMMA = 1.4
MOL_WEIGHT = 28.96                      # R = 8314.46/28.96 = 287.06 J/(kg K)
R_SPECIFIC = 8314.46261815324 / MOL_WEIGHT
CP = 1004.5
SUTH_AS, SUTH_TS = 1.4792e-06, 116.0    # standard air Sutherland

# ---- mesh parameters --------------------------------------------------------
# Domain sized by the MEASURED farfield-probe alpha bias: with freestream BCs
# (no point-vortex correction) the bound vortex leaves a residual ~Gamma/2piR
# in the closed-boundary average — measured 0.217 deg at the first 15c build
# (vs declared 2.79, gate C0b atol 0.2: FAIL). The bias scales ~1/R; 30c
# halves it to ~0.1 deg. Published uncorrected RAE 2822 setups use 50-100c;
# 30c is the smallest domain that clears the gate with ~2x margin.
X_MIN, X_MAX = -30.0, 35.0
Z_FAR = 30.0
Y_LO, Y_HI = -0.001, 0.001
N_WRAP = 160            # cells per surface block (4 surface blocks); 100 at
                        # first build put ~0.007c streamwise cells through the
                        # SBLI — one principled refinement to 0.0044c before
                        # freezing (shock position is the streamwise-resolution
                        # -sensitive QoI)
N_WAKE = 100            # streamwise cells in each wake block
N_NORMAL = 220          # wall-normal cells
WAKE_X_GRADING = 12.0
N_EDGE = 800            # intermediate polyLine points per block edge:
                        # front-edge arc ~0.31c -> spacing ~3.9e-4c -> LE
                        # sagitta h^2/8R ~ 2.4e-6 c (R_LE~0.008c), below the
                        # first-cell height

# wall-normal grading sized for y+ <= 1: solve r so that the first cell is
# ~3.6e-6 c (flat-plate u_tau estimate at Re 6.5e6 gives y+~0.8 there)
FIRST_CELL = 3.6e-6


def derived_freestream():
    mu = SUTH_AS * math.sqrt(T_INF) / (1.0 + SUTH_TS / T_INF)
    a = math.sqrt(GAMMA * R_SPECIFIC * T_INF)
    u = MACH * a
    rho = RE_C * mu / (u * CHORD)
    p = rho * R_SPECIFIC * T_INF
    ar = math.radians(ALPHA_DEG)
    ux, uz = u * math.cos(ar), u * math.sin(ar)
    # far-field turbulence: vendor aerofoilNACA0012 tutorial VERBATIM
    # (k=0.01, omega=10 — defined at U=250 m/s, chord 1, i.e. exactly this
    # velocity scale). The first build derived omega=k/nu (nu_t/nu=1): right
    # ratio, absurd magnitude — decay length U/(beta* omega) = 4.6 cm, so
    # the turbulence seed died 30c upstream and the SST boundary layer ran
    # pseudo-laminar (live 2026-06-10: y+_avg 0.31 vs ~0.9 turbulent, shock
    # x/c 0.598 vs 0.525 anchor, Cl 0.864). Vendor values: decay length
    # 278 m >> domain, nu_t/nu ~ 26 ignition seed.
    k = 0.01
    omega = 10.0
    return dict(mu=mu, a=a, u=u, rho=rho, p=p, ux=ux, uz=uz, k=k, omega=omega)


def normal_grading() -> float:
    """Total expansion ratio G = last/first for the wall-normal direction,
    solved so the first of N_NORMAL geometric cells spanning Z_FAR is
    FIRST_CELL."""
    lo, hi = 1.0 + 1e-9, 1.5
    for _ in range(200):
        r = 0.5 * (lo + hi)
        first = Z_FAR * (r - 1.0) / (r ** N_NORMAL - 1.0)
        if first > FIRST_CELL:
            lo = r
        else:
            hi = r
    return r ** (N_NORMAL - 1)


# --------------------------------------------------------------------------
# geometry: read Selig wrap, cubic-spline resample, write OBJ
# --------------------------------------------------------------------------

def read_selig():
    pts = []
    for line in COORDS.read_text().splitlines()[1:]:
        s = line.split()
        if len(s) == 2:
            pts.append((float(s[0]), float(s[1])))
    if len(pts) < 100 or pts[0] != (1.0, 0.0) or pts[-1] != (1.0, 0.0):
        raise SystemExit(f"unexpected Selig wrap in {COORDS}")
    return pts


def natural_cubic(xs, ys):
    """Natural cubic spline coefficients; returns evaluator f(x) (xs ascending)."""
    n = len(xs) - 1
    h = [xs[i + 1] - xs[i] for i in range(n)]
    al = [0.0] * (n + 1)
    for i in range(1, n):
        al[i] = 3.0 / h[i] * (ys[i + 1] - ys[i]) - 3.0 / h[i - 1] * (ys[i] - ys[i - 1])
    l = [1.0] + [0.0] * n
    mu = [0.0] * (n + 1)
    z = [0.0] * (n + 1)
    for i in range(1, n):
        l[i] = 2.0 * (xs[i + 1] - xs[i - 1]) - h[i - 1] * mu[i - 1]
        mu[i] = h[i] / l[i]
        z[i] = (al[i] - h[i - 1] * z[i - 1]) / l[i]
    l[n] = 1.0
    b = [0.0] * n
    c = [0.0] * (n + 1)
    d = [0.0] * n
    for j in range(n - 1, -1, -1):
        c[j] = z[j] - mu[j] * c[j + 1]
        b[j] = (ys[j + 1] - ys[j]) / h[j] - h[j] * (c[j + 1] + 2.0 * c[j]) / 3.0
        d[j] = (c[j + 1] - c[j]) / (3.0 * h[j])

    def f(x):
        i = max(0, min(n - 1, _bisect(xs, x) - 1))
        dx = x - xs[i]
        return ys[i] + b[i] * dx + c[i] * dx * dx + d[i] * dx ** 3
    return f


def _bisect(xs, x):
    lo, hi = 0, len(xs)
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def build_wrap_spline(pts):
    """Arc-length-parametric cubic spline through the full Selig wrap
    (TE -> upper -> LE -> lower -> TE). Returns (fx, fz, t_knots)."""
    t = [0.0]
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        t.append(t[-1] + math.dist((x0, z0), (x1, z1)))
    return natural_cubic(t, [p[0] for p in pts]), natural_cubic(t, [p[1] for p in pts]), t


def t_at_x(fx, t_lo, t_hi, x_target):
    """Bisection for fx(t) == x_target on a branch where x is monotone."""
    lo, hi = t_lo, t_hi
    f_lo = fx(lo) - x_target
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        f_mid = fx(mid) - x_target
        if (f_lo < 0) == (f_mid < 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def edge_points(fx, fz, t0, t1, n=N_EDGE):
    """n INTERMEDIATE points strictly between params t0 and t1 (polyLineEdge
    convention: endpoints come from the block vertices)."""
    return [(fx(t0 + (t1 - t0) * i / (n + 1)), fz(t0 + (t1 - t0) * i / (n + 1)))
            for i in range(1, n + 1)]


# --------------------------------------------------------------------------
# OpenFOAM dictionaries
# --------------------------------------------------------------------------

HEADER = """\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    {loc}object      {obj};
}}
// generated by scripts/p4/generate_rae2822_case9.py (V73.B · DEC-V61-240)
"""


def _hdr(cls, obj, loc=None):
    return HEADER.format(cls=cls, obj=obj, loc=f'location    "{loc}";\n    ' if loc else "")


def write_blockmesh(case: Path, z_up03: float, z_lo03: float, grading: float,
                    edge_xz: dict):
    """edge_xz maps base-layer vertex pairs (4,7)/(7,5)/(4,8)/(8,5) to the
    spline-sampled INTERMEDIATE (x, z) points of that airfoil edge."""
    g = f"{grading:.1f}"
    v = []
    for y in (Y_LO, Y_HI):
        v += [
            (0.3, y, -Z_FAR), (1.0, y, -Z_FAR), (X_MAX, y, -Z_FAR),
            (X_MIN, y, 0.0), (0.0, y, 0.0), (1.0, y, 0.0), (X_MAX, y, 0.0),
            (0.3, y, z_lo03), (0.3, y, z_up03),
            (0.3, y, Z_FAR), (1.0, y, Z_FAR), (X_MAX, y, Z_FAR),
        ]
    verts = "\n".join(f"    ({x:.6f} {y:.6f} {z:.6f})" for x, y, z in v)

    def poly(a, b, pts, y):
        body = "\n".join(f"        ({x:.8f} {y:.6f} {z:.8f})" for x, z in pts)
        return f"    polyLine {a} {b}\n    (\n{body}\n    )"

    edge_lines = []
    for (a, b), pts in edge_xz.items():
        edge_lines.append(poly(a, b, pts, Y_LO))
        edge_lines.append(poly(a + 12, b + 12, pts, Y_HI))
    edges_txt = "\n".join(edge_lines)
    (case / "system").mkdir(parents=True, exist_ok=True)
    (case / "system" / "blockMeshDict").write_text(_hdr("dictionary", "blockMeshDict", "system") + f"""
convertToMeters 1;

vertices
(
{verts}
);

blocks
(
    // identical 6-block topology to the in-repo naca0012 showcase dict
    // (src/foam_agent_adapter.py), re-dimensioned for the transonic domain:
    // x in [{X_MIN}, {X_MAX}], z in +/-{Z_FAR}, {N_NORMAL} wall-normal cells,
    // grading {g} -> first cell ~{FIRST_CELL:.1e} c (y+ <= 1 target, B109)
    hex ( 7 4 16 19 0 3 15 12)  ({N_WRAP} 1 {N_NORMAL})  simpleGrading (1 1 {g})
    hex ( 5 7 19 17 1 0 12 13)  ({N_WRAP} 1 {N_NORMAL})  simpleGrading (1 1 {g})
    hex ( 17 18 6 5 13 14 2 1)  ({N_WAKE} 1 {N_NORMAL})  simpleGrading ({WAKE_X_GRADING} 1 {g})
    hex ( 20 16 4 8 21 15 3 9)  ({N_WRAP} 1 {N_NORMAL})  simpleGrading (1 1 {g})
    hex ( 17 20 8 5 22 21 9 10) ({N_WRAP} 1 {N_NORMAL})  simpleGrading (1 1 {g})
    hex ( 5 6 18 17 10 11 23 22) ({N_WAKE} 1 {N_NORMAL}) simpleGrading ({WAKE_X_GRADING} 1 {g})
);

edges
(
{edges_txt}
);

boundary
(
    aerofoil
    {{
        type            wall;
        faces
        (
            (4 7 19 16)
            (7 5 17 19)
            (5 8 20 17)
            (8 4 16 20)
        );
    }}
    farfield
    {{
        // SINGLE merged outer patch: the freestreamProbe area-averages the
        // whole closed outer boundary so the bound-vortex induction cancels
        // (see module docstring) — and the freestream BC family handles
        // local in/outflow per-face.
        type            patch;
        inGroups        (freestream);
        faces
        (
            (3 0 12 15)
            (0 1 13 12)
            (1 2 14 13)
            (11 10 22 23)
            (10 9 21 22)
            (9 3 15 21)
            (2 6 18 14)
            (6 11 23 18)
        );
    }}
    back
    {{
        type            empty;
        faces
        (
            (3 4 7 0)
            (7 5 1 0)
            (5 6 2 1)
            (3 9 8 4)
            (9 10 5 8)
            (10 11 6 5)
        );
    }}
    front
    {{
        type            empty;
        faces
        (
            (15 16 19 12)
            (19 17 13 12)
            (17 18 14 13)
            (15 16 20 21)
            (20 17 22 21)
            (17 18 23 22)
        );
    }}
);

mergePatchPairs ();
""")


def write_zero(case: Path, fs):
    z = case / "0"
    z.mkdir(parents=True, exist_ok=True)
    uvec = f"({fs['ux']:.6f} 0 {fs['uz']:.6f})"

    def field(obj, cls, dims, internal, farfield, wall):
        (z / obj).write_text(_hdr(cls, obj) + f"""
dimensions      {dims};

internalField   uniform {internal};

boundaryField
{{
    farfield
    {{
{farfield}
    }}
    aerofoil
    {{
{wall}
    }}
    "(front|back)"
    {{
        type            empty;
    }}
}}
""")

    field("U", "volVectorField", "[0 1 -1 0 0 0 0]", uvec,
          f"        type            freestreamVelocity;\n"
          f"        freestreamValue uniform {uvec};\n"
          f"        value           uniform {uvec};",
          "        type            noSlip;")
    field("p", "volScalarField", "[1 -1 -2 0 0 0 0]", f"{fs['p']:.4f}",
          f"        type            freestreamPressure;\n"
          f"        freestreamValue uniform {fs['p']:.4f};\n"
          f"        value           uniform {fs['p']:.4f};",
          "        type            zeroGradient;")
    field("T", "volScalarField", "[0 0 0 1 0 0 0]", f"{T_INF}",
          f"        type            inletOutlet;\n"
          f"        inletValue      uniform {T_INF};\n"
          f"        value           uniform {T_INF};",
          "        type            zeroGradient;")
    field("k", "volScalarField", "[0 2 -2 0 0 0 0]", f"{fs['k']:.6f}",
          f"        type            inletOutlet;\n"
          f"        inletValue      uniform {fs['k']:.6f};\n"
          f"        value           uniform {fs['k']:.6f};",
          f"        type            kqRWallFunction;\n"
          f"        value           uniform {fs['k']:.6f};")
    field("omega", "volScalarField", "[0 0 -1 0 0 0 0]", f"{fs['omega']:.2f}",
          f"        type            inletOutlet;\n"
          f"        inletValue      uniform {fs['omega']:.2f};\n"
          f"        value           uniform {fs['omega']:.2f};",
          f"        type            omegaWallFunction;\n"
          f"        value           uniform {fs['omega']:.2f};")
    field("nut", "volScalarField", "[0 2 -1 0 0 0 0]", "0",
          "        type            calculated;\n"
          "        value           uniform 0;",
          "        // continuous Spalding blend — valid at y+ < 1 (V71.B\n"
          "        // resolved-wall precedent, DEC-V61-235)\n"
          "        type            nutUSpaldingWallFunction;\n"
          "        value           uniform 0;")
    field("alphat", "volScalarField", "[1 -1 -1 0 0 0 0]", "0",
          "        type            calculated;\n"
          "        value           uniform 0;",
          "        type            compressible::alphatWallFunction;\n"
          "        Prt             0.85;\n"
          "        value           uniform 0;")


def write_constant(case: Path):
    c = case / "constant"
    c.mkdir(parents=True, exist_ok=True)
    (c / "thermophysicalProperties").write_text(_hdr("dictionary", "thermophysicalProperties", "constant") + f"""
thermoType
{{
    type            hePsiThermo;
    mixture         pureMixture;
    transport       sutherland;     // B109 spec (vendor tutorial uses const)
    thermo          hConst;
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleInternalEnergy;
}}

mixture
{{
    specie
    {{
        molWeight   {MOL_WEIGHT};
    }}
    thermodynamics
    {{
        Cp          {CP};
        Hf          0;
    }}
    transport
    {{
        As          {SUTH_AS};
        Ts          {SUTH_TS};
    }}
}}
""")
    (c / "turbulenceProperties").write_text(_hdr("dictionary", "turbulenceProperties", "constant") + """
simulationType  RAS;

RAS
{
    RASModel        kOmegaSST;
    turbulence      on;
    printCoeffs     on;
}
""")


def write_system(case: Path, fs):
    s = case / "system"
    s.mkdir(parents=True, exist_ok=True)
    ar = math.radians(ALPHA_DEG)
    lift = f"({-math.sin(ar):.8f} 0 {math.cos(ar):.8f})"
    drag = f"({math.cos(ar):.8f} 0 {math.sin(ar):.8f})"

    (s / "controlDict").write_text(_hdr("dictionary", "controlDict", "system") + f"""
application     rhoSimpleFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         6000;
deltaT          1;
writeControl    timeStep;
writeInterval   1000;
purgeWrite      0;
writeFormat     ascii;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

functions
{{
    forceCoeffs1
    {{
        type            forceCoeffs;
        libs            (forces);
        writeControl    timeStep;
        writeInterval   1;
        patches         (aerofoil);
        rho             rho;
        rhoInf          {fs['rho']:.6f};
        CofR            (0.25 0 0);
        liftDir         {lift};
        dragDir         {drag};
        pitchAxis       (0 1 0);
        magUInf         {fs['u']:.6f};
        lRef            {CHORD};
        Aref            {CHORD * (Y_HI - Y_LO)};
    }}

    airfoilSurface
    {{
        // V73.A extractor contract: postProcessing/airfoilSurface/<t>/
        // p_aerofoil.raw, columns `x y z p` per face centre
        type            surfaces;
        libs            (sampling);
        writeControl    writeTime;
        surfaceFormat   raw;
        fields          (p);
        interpolationScheme cellPoint;
        surfaces
        (
            aerofoil
            {{
                type            patch;
                patches         (aerofoil);
                interpolate     false;
            }}
        );
    }}

    freestreamProbe
    {{
        // V73.A extractor contract: measured freestream = areaAverage of
        // the SOLVED field over the FULL closed outer boundary (circulation
        // cancels; a doctored 0/ file cannot move this)
        type            surfaceFieldValue;
        libs            (fieldFunctionObjects);
        regionType      patch;
        name            farfield;
        operation       areaAverage;
        fields          (p T U);
        writeFields     false;
        writeControl    timeStep;
        // every step: residualControl can stop the run at ANY iteration and
        // the extractor needs the probe row AT t_snap (a 100-step interval
        // missed the convergence write at t=956, observed live 2026-06-10)
        writeInterval   1;
        log             false;
    }}

    yPlus1
    {{
        type            yPlus;
        libs            (fieldFunctionObjects);
        writeControl    writeTime;
    }}

    MachNo1
    {{
        type            MachNo;
        libs            (fieldFunctionObjects);
        executeControl  writeTime;
        writeControl    writeTime;
    }}
}}
""")

    (s / "fvSchemes").write_text(_hdr("dictionary", "fvSchemes", "system") + """
// ESI v2312 vendor tutorial compressible/rhoSimpleFoam/aerofoilNACA0012,
// lifted verbatim (transonic-airfoil-tuned)
ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;

    limited         cellLimited Gauss linear 1;
    grad(U)         $limited;
    grad(k)         $limited;
    grad(omega)     $limited;
}

divSchemes
{
    default         none;

    div(phi,U)      bounded Gauss linearUpwind limited;

    energy          bounded Gauss linearUpwind limited;
    div(phi,e)      $energy;
    div(phi,K)      $energy;
    div(phi,Ekp)    $energy;

    turbulence      bounded Gauss upwind;
    div(phi,k)      $turbulence;
    div(phi,omega)  $turbulence;

    div(phid,p)     Gauss upwind;
    div((phi|interpolate(rho)),p)  bounded Gauss upwind;

    div(((rho*nuEff)*dev2(T(grad(U)))))    Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

wallDist
{
    method          meshWave;
}
""")

    (s / "fvSolution").write_text(_hdr("dictionary", "fvSolution", "system") + """
// solvers block: vendor aerofoilNACA0012 tutorial verbatim.
// SIMPLE/relaxation: vendor squareBend tutorial (the v2312 rhoSimpleFoam
// `transonic yes` precedent) — the aerofoilNACA0012 profile (transonic no,
// p 0.7 / rho 0.01 / U 0.3) limit-cycles on THIS stiffer mesh (y+<=1 wall,
// 15c domain): observed live 2026-06-10 as a period-~6 Cl oscillation of
// amplitude ~2.4 at iter 4500+ while the farfield probe stayed steady to
// +/-0.3% — a shock-local cycle, the canonical cure for which is the phid
// (transonic) pressure formulation + SIMPLEC. residualControl tightened
// 1e-3/1e-4 -> 5e-5 for force-quality convergence.
solvers
{
    p
    {
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-6;
        relTol          0.01;
    }

    "(U|k|omega|e)"
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-6;
        relTol          0.1;
    }
}

SIMPLE
{
    // 1 corrector (vendor uses 0): this mesh has max non-orthogonality 63
    // deg at the LE/TE block seams; the corrector removes the per-iteration
    // p-equation splitting error that feeds the shock limit cycle
    nNonOrthogonalCorrectors 1;
    pMinFactor      0.1;
    pMaxFactor      2;
    transonic       yes;
    consistent      yes;

    residualControl
    {
        p               5e-5;
        U               5e-5;
        "(k|omega|e)"   5e-5;
    }
}

relaxationFactors
{
    fields
    {
        p               1;
    }
    equations
    {
        p               1;
        // squareBend's U=0.9 kept: dropping to 0.5 was tried live and made
        // the cycle WORSE (Cl std 1.4% -> 22% — SIMPLEC's consistency
        // derivation assumes near-unity relaxation)
        U               0.9;
        e               0.8;
        "(k|omega)"     0.9;
    }
}
""")

    (s / "fvOptions").write_text(_hdr("dictionary", "fvOptions", "system") + """
// vendor tutorial aerofoilNACA0012 system/fvOptions VERBATIM — the transonic
// startup stabilizer (without it the run hits SIGFPE in the thermo library
// around iter ~190: a transient cell T goes out of range and sutherland's
// sqrt(T) faults; observed live 2026-06-10)
limitT
{
    type       limitTemperature;
    min        101;
    max        1000;
    selectionMode all;
}
""")

    (s / "decomposeParDict").write_text(_hdr("dictionary", "decomposeParDict", "system") + """
numberOfSubdomains 8;
method          scotch;
""")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    case = Path(sys.argv[1])
    case.mkdir(parents=True, exist_ok=True)

    fs = derived_freestream()
    pts = read_selig()
    fx, fz, t_knots = build_wrap_spline(pts)
    i_le = min(range(len(pts)), key=lambda i: pts[i][0])
    if pts[i_le] != (0.0, 0.0):
        raise SystemExit(f"LE knot is {pts[i_le]}, expected (0, 0)")
    t_le, t_end = t_knots[i_le], t_knots[-1]
    # branch params at x=0.3 (upper branch: t in [0, t_le], TE->LE;
    # lower branch: t in [t_le, t_end], LE->TE)
    t_up03 = t_at_x(fx, 0.0, t_le, 0.3)
    t_lo03 = t_at_x(fx, t_le, t_end, 0.3)
    z_up03, z_lo03 = fz(t_up03), fz(t_lo03)
    if not (0.05 < z_up03 < 0.07 and -0.07 < z_lo03 < -0.05):
        raise SystemExit(f"implausible 0.3c anchors: {z_up03}, {z_lo03}")
    grading = normal_grading()

    # block-edge intermediate points, ordered first-vertex -> second-vertex
    edge_xz = {
        (4, 7): edge_points(fx, fz, t_le, t_lo03),    # LE -> 0.3 lower
        (7, 5): edge_points(fx, fz, t_lo03, t_end),   # 0.3 lower -> TE
        (4, 8): edge_points(fx, fz, t_le, t_up03),    # LE -> 0.3 upper
        (8, 5): edge_points(fx, fz, t_up03, 0.0),     # 0.3 upper -> TE
    }
    for pair, exz in edge_xz.items():
        xs = [x for x, _ in exz]
        if not all(b > a for a, b in zip(xs, xs[1:])) and \
           not all(b < a for a, b in zip(xs, xs[1:])):
            raise SystemExit(f"edge {pair} not monotone in x")

    write_blockmesh(case, z_up03, z_lo03, grading, edge_xz)
    write_zero(case, fs)
    write_constant(case)
    write_system(case, fs)

    first = Z_FAR * (grading ** (1.0 / (N_NORMAL - 1)) - 1.0) / (grading ** (N_NORMAL / (N_NORMAL - 1.0)) - 1.0)
    print(f"case written to {case}")
    print(f"freestream: p={fs['p']:.2f} Pa  T={T_INF} K  U=({fs['ux']:.4f}, 0, {fs['uz']:.4f}) m/s"
          f"  |U|={fs['u']:.4f}  M={MACH}  rho={fs['rho']:.6f}  mu={fs['mu']:.4e}")
    print(f"Re check: {fs['rho'] * fs['u'] * CHORD / fs['mu']:.6e} (target {RE_C:.1e})")
    print(f"k={fs['k']:.4f}  omega={fs['omega']:.1f}")
    print(f"mesh: blocks 6 x ({N_WRAP}|{N_WAKE} x 1 x {N_NORMAL}), normal grading {grading:.0f}"
          f"  (first cell ~{first:.2e} c)")
    print(f"airfoil vertex anchors: z_upper(0.3)={z_up03:.6f}  z_lower(0.3)={z_lo03:.6f}")


if __name__ == "__main__":
    main()
