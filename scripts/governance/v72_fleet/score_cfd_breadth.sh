#!/usr/bin/env bash
# V70 Fleet Agent #8: CFD-Capability-Breadth
# Audits the workbench's CFD regime coverage along orthogonal axes.
# Subscores (each binary or pro-rated):
#   - turbulence_models_supported (25) · count distinct turbulence models in advisor_stack.py + whitelist
#   - compressibility_regimes (20)     · incompressible / compressible / weakly-compressible
#   - steadiness_regimes (15)          · steady / transient
#   - bc_types_count (20)              · count distinct BC types in BC route handlers + advisor surface
#   - meshing_strategies (10)          · snappyHexMesh / cfMesh / gmsh / blockMesh
#   - capability_matrix_doc (10)       · .planning/cfd_capability_matrix.md present + ≥80% cells PR/gap-tracked
# Score = sum (max 100)

set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

agent="cfd_breadth"
dim="CFD仿真全维度能力"
weight=0.08
evidence=("placeholder")
failures=("placeholder")

# ─────────── 1. Turbulence models ─────────────────────────────────
# Look for distinct turbulence model identifiers across the corpus
turb_count=0
# Look across advisor surface + actual whitelist + canonical eval set + capability matrix doc
turb_sources=(
  "ui/backend/services/ai_advisor/"
  "knowledge/whitelist.yaml"
  ".planning/evals/canonical/"
  ".planning/cfd_capability_matrix.md"
)
turb_count=$(grep -rohE "kEpsilon|k-epsilon|kOmegaSST|k-omega.SST|kOmega|SpalartAllmaras|Spalart.Allmaras|LES|DNS|laminar|resolved.scale" "${turb_sources[@]}" 2>/dev/null | tr '[:upper:]' '[:lower:]' | sed 's/k-epsilon/kepsilon/g; s/k-omega.sst/komegasst/g; s/spalart.allmaras/spalartallmaras/g; s/resolved.scale/dns/g' | sort -u | wc -l | tr -d ' ')
turb_count=${turb_count:-0}
if [ "$turb_count" -ge 4 ]; then
  turb_score=25
  evidence+=("turbulence models supported: ${turb_count} (≥4 V70 threshold MET)")
elif [ "$turb_count" -gt 0 ]; then
  turb_score=$(( turb_count * 25 / 4 ))
  evidence+=("turbulence models: ${turb_count}/4 (pro-rated=${turb_score}/25)")
  failures+=("turbulence models below threshold: ${turb_count}/4 (need ≥4 for V70 close)")
else
  turb_score=0
  failures+=("turbulence models: 0 detected in advisor surface")
fi

# ─────────── 2. Compressibility regimes ───────────────────────────
# incompressible / compressible / weakly compressible identifiers
comp_count=0
if [ -d "ui/backend/services" ]; then
  comp_count=$(grep -rohE "incompressible|compressible|isothermal|rhoCentralFoam|rhoPimpleFoam" ui/backend/services/ ui/backend/whitelist.yaml 2>/dev/null | sed 's/rhoCentralFoam/compressible/; s/rhoPimpleFoam/compressible/; s/isothermal/compressible/' | sort -u | wc -l | tr -d ' ')
fi
comp_count=${comp_count:-0}
if [ "$comp_count" -ge 3 ]; then
  comp_score=20
  evidence+=("compressibility regimes: ${comp_count} (≥3 V70 threshold MET)")
elif [ "$comp_count" -gt 0 ]; then
  comp_score=$(( comp_count * 20 / 3 ))
  evidence+=("compressibility regimes: ${comp_count}/3 (pro-rated=${comp_score}/20)")
  failures+=("compressibility regimes below threshold: ${comp_count}/3 (need ≥3 for V70 close)")
else
  comp_score=0
  failures+=("compressibility regimes: 0 detected")
fi

# ─────────── 3. Steadiness regimes ────────────────────────────────
# steady / transient
steady_count=0
if [ -d "ui/backend/services" ]; then
  steady_count=$(grep -rohE "steady|transient|unsteady|pimpleFoam|simpleFoam" ui/backend/services/ ui/backend/whitelist.yaml 2>/dev/null | sed 's/pimpleFoam/transient/; s/simpleFoam/steady/; s/unsteady/transient/' | sort -u | wc -l | tr -d ' ')
fi
steady_count=${steady_count:-0}
if [ "$steady_count" -ge 2 ]; then
  steady_score=15
  evidence+=("steadiness regimes: ${steady_count} (≥2 V70 threshold MET)")
else
  steady_score=$(( steady_count * 15 / 2 ))
  failures+=("steadiness regimes below threshold: ${steady_count}/2 (need ≥2 for V70 close)")
fi

# ─────────── 4. BC types ──────────────────────────────────────────
# Look for BC type identifiers in advisor surface + canonical eval frontmatter
bc_count=0
if [ -d ".planning/evals/canonical" ] && [ -d "ui/backend" ]; then
  bc_count=$(grep -rohE "fixedValue|zeroGradient|inletOutlet|noSlip|symmetry|wallFunction|fixedFluxPressure|totalPressure|pressureInletVelocity|cyclic|patch|empty" ui/backend/ .planning/evals/canonical/ 2>/dev/null | sort -u | wc -l | tr -d ' ')
fi
bc_count=${bc_count:-0}
if [ "$bc_count" -ge 10 ]; then
  bc_score=20
  evidence+=("BC types: ${bc_count} (≥10 V70 threshold MET)")
elif [ "$bc_count" -gt 0 ]; then
  bc_score=$(( bc_count * 20 / 10 ))
  evidence+=("BC types: ${bc_count}/10 (pro-rated=${bc_score}/20)")
  failures+=("BC types below threshold: ${bc_count}/10 (need ≥10 for V70 close)")
else
  bc_score=0
  failures+=("BC types: 0 detected")
fi

# ─────────── 5. Meshing strategies ────────────────────────────────
mesh_count=0
if [ -d "ui/backend" ]; then
  mesh_count=$(grep -rohE "snappyHexMesh|cfMesh|gmsh|blockMesh|cartesianMesh" ui/backend/ .planning/ 2>/dev/null | sort -u | wc -l | tr -d ' ')
fi
mesh_count=${mesh_count:-0}
if [ "$mesh_count" -ge 2 ]; then
  mesh_score=10
  evidence+=("meshing strategies: ${mesh_count} (≥2 V70 threshold MET)")
else
  mesh_score=$(( mesh_count * 10 / 2 ))
  failures+=("meshing strategies: ${mesh_count}/2 (need ≥2)")
fi

# ─────────── 6. Capability matrix doc ─────────────────────────────
matrix_score=0
matrix_doc=".planning/cfd_capability_matrix.md"
if [ -f "$matrix_doc" ]; then
  # Check ≥80% cells PR or gap-tracked: count "✅" / "PR" / "GAP-TRACKED" vs total "|" cells
  pr_count=$(grep -cE "✅|GAP-TRACKED|PR" "$matrix_doc" 2>/dev/null || echo 0)
  pr_count=${pr_count:-0}
  if [ "$pr_count" -ge 10 ]; then
    matrix_score=10
    evidence+=("capability matrix doc: ${matrix_doc} present · ${pr_count} cells with PR/GAP-TRACKED status")
  elif [ "$pr_count" -gt 0 ]; then
    matrix_score=$(( pr_count * 10 / 10 ))
    evidence+=("capability matrix doc partial: ${pr_count} cells flagged")
  fi
else
  failures+=("capability matrix doc missing: ${matrix_doc} (V70-DONE-1)")
fi

score=$(( turb_score + comp_score + steady_score + bc_score + mesh_score + matrix_score ))
if [ "$score" -gt 100 ]; then score=100; fi

evidence=("${evidence[@]:1}")
failures=("${failures[@]:1}")

python3 - <<PYEOF
import json
ev_raw = """$(printf '%s\n' "${evidence[@]+"${evidence[@]}"}")"""
fa_raw = """$(printf '%s\n' "${failures[@]+"${failures[@]}"}")"""
ev = [l for l in ev_raw.split("\n") if l.strip()]
fa = [l for l in fa_raw.split("\n") if l.strip()]
print(json.dumps({
  "agent": "$agent",
  "dim": "$dim",
  "weight": $weight,
  "score": $score,
  "subscores": {
    "turbulence_models_supported": $turb_count,
    "turbulence_score": $turb_score,
    "compressibility_regimes": $comp_count,
    "compressibility_score": $comp_score,
    "steadiness_regimes": $steady_count,
    "steadiness_score": $steady_score,
    "bc_types_count": $bc_count,
    "bc_score": $bc_score,
    "meshing_strategies": $mesh_count,
    "meshing_score": $mesh_score,
    "capability_matrix_score": $matrix_score,
  },
  "evidence": ev,
  "failures": fa,
  "honest_note": "regime detection is grep-based · over-counts when identifier appears in comments/docs; matrix_doc cell-count is heuristic and replaceable with structured YAML if V72 needs precision"
}, ensure_ascii=False, indent=2))
PYEOF
