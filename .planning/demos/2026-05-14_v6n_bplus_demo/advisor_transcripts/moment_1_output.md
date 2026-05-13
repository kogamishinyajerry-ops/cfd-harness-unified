**Quick verdict**

(b) Proceed with the current mesh and tuned schemes, with high confidence.

**Corpus citations**

- [V84] `buoyantSimpleFoam` ran cleanly on an industrial mesh with `max_skew 6.87` and 20 skew faces using the same class of “production-tuned” schemes.
- [V8] `max skewness > 4` is a real risk when loose meshing accepts bad cells, but the downstream impact depends on solver/discretization robustness, not the strict meshing gate alone.
- [S3] If you are starting `kOmegaSST` from zero fields, warm-start with `potentialFoam -writePhi` to avoid omega startup blowup.

**Why**

- Your mesh is very close to the positive [V84] precedent: `max_skewness 6.875`, only 20 skew faces, acceptable non-orthogonality, and no other failed checks.
- Your schemes are already in the right stability class for this situation: `cellLimited` gradients, bounded convection, limited laplacians, and `nNonOrthCorrectors 2` match the mitigation pattern from [V84].
- The small count of skew faces matters. This is not a globally poor mesh; it is a mostly clean 3.1M-face mesh with a tiny local defect population.
- Switching to `buoyantPimpleFoam` does not address the main question. This is primarily a mesh-plus-discretization robustness check, not a steady-vs-transient solver selection issue.
- Re-meshing now is hard to justify before a smoke test, because [V84] says the practical gate is “does the solver run cleanly for ~50 iterations with the intended schemes,” not “does strict `checkMesh` pass below 4.”

**Proposed validation step**

If this is a zero-IC `kOmegaSST` start, run:

```bash
potentialFoam -writePhi
```

Then run `buoyantSimpleFoam` for about 50 SIMPLE iterations only. Accept choice (b) if you see no `FATAL`/FPE, no rapid residual blowup, and no persistent boundedness/continuity pathologies in the first few minutes. If it fails, inspect the 20 skew faces and re-mesh locally rather than switching solver first.

**What I'm NOT telling you**

I do not know your boundary conditions, turbulence initialization, or where those 20 skew faces sit relative to recirculation, buoyancy gradients, or solid interfaces. Any of those could still flip the verdict even if the mesh statistics look acceptable.

Advisory only; the engineer decides.
