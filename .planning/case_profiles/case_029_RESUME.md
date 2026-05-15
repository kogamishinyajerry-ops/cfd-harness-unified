# case_029 · NACA 0012 stall · RESUME

> Read this in 30 sec → recover full work context.

## Where am I?

V65-A Tier 2 · M-V65A-CASE-NACA-STALL · 2nd net-new industrial case e2e (after case_028 APU bay strong-PARTIAL B74).

Goal: push V65-A Done #3 from 1/2 → 2/2 ✓ MET. V104 promotion path (F-NEW-15 inlet BL separation 2nd witness via NACA stall).

## Last commits (B75)

1. `<sha1>` substrate (this batch)
2. `<sha2>` mesh prep
3. `<sha3>` solver × 3 AoA + advisor + report
4. `<sha4>` sub-DEC + ARC-GOAL

## Where files live

- Substrate spec: `.planning/case_profiles/case_029_naca_stall.md`
- This RESUME: `.planning/case_profiles/case_029_RESUME.md`
- OpenFOAM dicts: `.planning/case_profiles/case_029_naca_stall_dicts/`
- Sandbox (NOT in git): `~/Desktop/case_029_naca_stall/case/`
- STL generator (NOT in git): `~/Desktop/case_029_naca_stall/generate_naca_stl.py`
- Validation report: `.planning/validation_reports/v65_case_029_naca_stall.md`
- Sub-DEC: `.planning/decisions/2026-05-16_v65_sub_case_naca_stall.md`
- Advisor runner: `scripts/case_029_naca_stall/run_advisor_stack.py`

## Quick re-run commands

```bash
# Regenerate STL
cd ~/Desktop/case_029_naca_stall && python3 generate_naca_stl.py naca=0012 chord=1.0 span=0.1 n=200 > airfoil.stl
cp airfoil.stl case/constant/triSurface/naca0012.stl

# Mesh (Docker)
docker run --rm -v ~/Desktop/case_029_naca_stall/case:/case opencfd/openfoam-default:2312 \
  bash -c "cd /case && surfaceFeatureExtract && blockMesh && snappyHexMesh -overwrite && checkMesh"

# Run AoA sweep (after mesh)
for AOA in aoa_10 aoa_15 aoa_18; do
  docker run --rm -v ~/Desktop/case_029_naca_stall/case_$AOA:/case opencfd/openfoam-default:2312 \
    bash -c "cd /case && simpleFoam > log.simpleFoam 2>&1"
done

# Advisor stack
cd ~/Desktop/cfd-harness-unified && .venv/bin/python -m scripts.case_029_naca_stall.run_advisor_stack
```

## Key parameters

- NACA 0012, chord 1m, span 0.1m, 200 chordwise points cosine-clustered
- Re_c = 3 × 10⁶ (NASA TM 4074 range)
- u_∞ = 45 m/s, ν = 1.5e-5 m²/s
- 3 AoA: 10°, 15°, 18° (pre-stall / stall-onset / post-stall)
- kOmegaSST RAS with all-y+ wall functions
- Target y+ < 1 (verify via postProcessing/yPlus)
- Target ≥7/9 advisors fired (close case_028 input gaps)

## Pending follow-ups

- V104 promotion judgment (LANDED / QUESTIONABLE / no-promote · in sub-DEC §V104)
- 4Q gate echo (LLM offline / artifacts / TrustGate / advisory-only) in transcript per goal (k)
- Notion sync (session-end batch only · NOT in /goal scope · only Accepted DECs)
