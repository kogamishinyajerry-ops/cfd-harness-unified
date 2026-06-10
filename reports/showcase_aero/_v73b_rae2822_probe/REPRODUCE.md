# Reproduce — V73.B RAE 2822 Case 9 transonic SBLI live probe

This is a **real solver run** (rhoSimpleFoam + kOmegaSST, ESI OpenFOAM v2312,
native arm64 docker) of a **generator-authored** RAE 2822 case at the AGARD
AR-138 Case 9 corrected operating point (M=0.734, alpha=2.79 deg, Re=6.5e6).
The extractor + two-tier gate consume only the artifacts frozen here; nothing
is hand-edited. `SHA256SUMS` is the tamper manifest
(`cd <this dir> && shasum -a 256 -c SHA256SUMS`).

## 1. Generate the case (stdlib-only generator, no adapter changes)

```bash
# from the repo root (geometry SSOT: knowledge/geometry/rae2822_selig.dat,
# sha256 88ab8c6b809e1a89057dfade045f97e0348bad510c6cff7747a6584e8d11aa17)
python3 scripts/p4/generate_rae2822_case9.py /path/to/run_dir
```

The generator's module docstring carries the full design provenance (6-block
polyLine C-grid · single merged `farfield` patch · vendor aerofoilNACA0012
schemes + squareBend transonic-SIMPLEC profile + fvOptions limitTemperature ·
vendor k/omega farfield · resolved wall y+ <= 1) **including the five live
debugging lessons** (projection branch-flip on cambered aft section; missed
vendor fvOptions -> thermo SIGFPE; aerofoil relaxation profile limit cycle;
domain sized by measured circulation bias; freestream-turbulence decay
length).

## 2. Solve (fresh ESI --rm container, 8-way parallel)

```bash
# this exact script (log names + RUN_DONE marker) is what
# scripts/p4/freeze_rae2822_probe.sh consumes — Codex R0 P2 alignment
docker run --rm --entrypoint bash -v /path/to/run_dir:/work \
  opencfd/openfoam-default:2312 -c '
source /openfoam/profile.rc >/dev/null 2>&1
cd /work
blockMesh > log.blockMesh 2>&1 || exit 1
checkMesh > log.checkMesh 2>&1
decomposePar -force > log.decomposePar 2>&1 || exit 1
mpirun --allow-run-as-root -np 8 rhoSimpleFoam -parallel > log.rhoSimpleFoam 2>&1
echo "solver exit=$?" >> log.rhoSimpleFoam
reconstructPar -latestTime > log.reconstructPar 2>&1
touch RUN_DONE'
```

The run STOPS ITSELF on `residualControl 5e-5` (SIMPLE convergence statement
in `logs/log.rhoSimpleFoam.headtail`); the snapshot time `t_snap` is whatever
iteration convergence lands on — pre-registered protocol, not selected after
looking at values.

## 3. Freeze the bundle

```bash
bash scripts/p4/freeze_rae2822_probe.sh /path/to/run_dir <t_snap>
```

## 4. Replay the gate offline (what the tests do)

```python
from pathlib import Path
from src.transonic_airfoil_gate import gate_transonic_airfoil_against_gold
res = gate_transonic_airfoil_against_gold(
    Path("reports/showcase_aero/_v73b_rae2822_probe"))
```

Gold SSOT: `knowledge/gold_standards/rae2822_case9.yaml` (tier-2 anchors
numerized 2026-06-10, DEC-V61-240). Verdict semantics: tier-1 == SANITY-PASS
(never "validated"); tier-2 judged only under the VERIFIED+provenance
meta-gate, cl + shock_xc ENFORCED, cd ADVISORY.
