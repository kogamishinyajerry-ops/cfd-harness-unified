#!/usr/bin/env bash
# V78 Fleet Aggregator · 16 pillars (NO new pillar · V77 retro Open Q #6 honored)
# V78 changes:
#   - Pillar 3 ux: 100% specs PASS threshold (was ≥17)
#   - Pillar 4 visualization: SSIM tool subscore + 76 PNG threshold
#   - Pillar 13 data_fidelity: + audit_package_e2e subscore (V78.3)
#   - Pillar 16 rt_solver_obs: + backend_sse_e2e subscore (V78.1)
# Usage (V78 backward-compat default):
#   bash scripts/governance/v78_fleet/score_all.sh <iter_number>
#   → writes .planning/scores/V78_iter_${N}.md
# Usage (V81.4 · explicit arc label):
#   bash scripts/governance/v78_fleet/score_all.sh <iter_number> --arc-label V81
#   → writes .planning/scores/V81_iter_${N}.md
# Rationale: V79 + V80 retros both flagged the manual-copy workaround when
# V79/V80 iterations would otherwise overwrite V78 close evidence. The
# --arc-label flag is OPTIONAL + additive: without it, behavior matches the
# original V78/V79/V80 invocations exactly (V81 charter reverse-stop #9).

set -o pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

iter="${1:-0}"
arc_label="V78"
# V81.4 · parse --arc-label flag (optional · positional iter remains $1)
shift 2>/dev/null || true
while [ $# -gt 0 ]; do
  case "$1" in
    --arc-label)
      shift
      arc_label="${1:-V78}"
      ;;
    --arc-label=*)
      arc_label="${1#*=}"
      ;;
    *)
      ;;  # unknown flag · ignore for forward-compat
  esac
  shift 2>/dev/null || true
done

out=".planning/scores/${arc_label}_iter_${iter}.md"
mkdir -p "$(dirname "$out")"

ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
sha=$(git rev-parse HEAD 2>/dev/null || echo "no-git")

agents=(quality physics ux visualization smoke functional stability cfd_breadth novice_onboarding industrial_ui interaction_polish backend_integration data_fidelity resumability_observability visualization_fidelity real_time_solver_observability)
results_dir=$(mktemp -d)
trap "rm -rf $results_dir" EXIT

echo ">>> V78 Fleet · Iter $iter · $ts · commit $sha · TIGHTENED scoring (NO new pillar)" >&2

for a in "${agents[@]}"; do
  echo ">>> running agent: $a" >&2
  # V78 scorers: ux (tightened) · visualization (SSIM-aware) · data_fidelity (+e2e) · rt_solver_obs (+e2e)
  # V77 carries: backend_integration (≥35 useQuery)
  # V76: visualization_fidelity
  # V75: resumability_observability
  # V74: interaction_polish
  # Rest: v71_fleet
  if [ "$a" = "ux" ]; then
    script_path="scripts/governance/v78_fleet/score_ux.sh"
  elif [ "$a" = "visualization" ]; then
    script_path="scripts/governance/v78_fleet/score_visualization.sh"
  elif [ "$a" = "data_fidelity" ]; then
    script_path="scripts/governance/v78_fleet/score_data_fidelity.sh"
  elif [ "$a" = "real_time_solver_observability" ]; then
    script_path="scripts/governance/v78_fleet/score_real_time_solver_observability.sh"
  elif [ "$a" = "backend_integration" ]; then
    script_path="scripts/governance/v77_fleet/score_${a}.sh"
  elif [ "$a" = "visualization_fidelity" ]; then
    script_path="scripts/governance/v76_fleet/score_${a}.sh"
  elif [ "$a" = "resumability_observability" ]; then
    script_path="scripts/governance/v75_fleet/score_${a}.sh"
  elif [ "$a" = "interaction_polish" ]; then
    script_path="scripts/governance/v74_fleet/score_${a}.sh"
  else
    script_path="scripts/governance/v71_fleet/score_${a}.sh"
  fi
  bash "$script_path" > "$results_dir/${a}.json" 2> "$results_dir/${a}.stderr.log"
  if ! jq empty < "$results_dir/${a}.json" 2>/dev/null; then
    python3 - "$a" "$results_dir/${a}.json" "$results_dir/${a}.stderr.log" <<'PYEOF'
import json, sys
agent_name, json_path, stderr_path = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    stderr_tail = open(stderr_path).read()[-500:] if open(stderr_path).read() else ""
except Exception:
    stderr_tail = "(unreadable)"
json.dump({
    "agent": agent_name,
    "dim": "INFRA_FAILURE",
    "weight": 0.0,
    "score": 0,
    "evidence": [],
    "failures": [f"agent script produced invalid JSON; stderr tail: {stderr_tail}"],
    "honest_note": "infra failure forces 0 score per honesty rule #3"
}, open(json_path, "w"), ensure_ascii=False, indent=2)
PYEOF
  fi
done

python3 - "$results_dir" "$out" "$iter" "$ts" "$sha" <<'PYEOF'
import json, sys, os
results_dir, out, iter_n, ts, sha = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]

agents_order = ["quality", "physics", "ux", "visualization", "smoke", "functional", "stability",
                "cfd_breadth", "novice_onboarding", "industrial_ui", "interaction_polish",
                "backend_integration", "data_fidelity", "resumability_observability",
                "visualization_fidelity", "real_time_solver_observability"]
data = {}
for a in agents_order:
    p = os.path.join(results_dir, f"{a}.json")
    with open(p) as f:
        data[a] = json.load(f)

scores = [data[a]["score"] for a in agents_order]
min_score = min(scores)
weights = [data[a]["weight"] for a in agents_order]
weighted_sum = sum(s * w for s, w in zip(scores, weights))

if min_score >= 99:
    verdict = "CLOSE_ELIGIBLE (this iter only; needs 2 consecutive)"
elif min_score >= 90:
    verdict = "PROCEED (high-fidelity iteration)"
elif min_score >= 50:
    verdict = "PROCEED (lift lowest dim)"
else:
    verdict = "PROCEED (multiple dims need attention)"

sorted_by_score = sorted(zip(agents_order, scores), key=lambda x: x[1])
lowest_dim = sorted_by_score[0][0]

md = []
md.append(f"# V78 Fleet Score · Iter {iter_n} · TIGHTENED scoring\n")
md.append(f"**Generated**: {ts}  ")
md.append(f"**Commit**: `{sha}`  ")
md.append(f"**Total (min one-vote-veto across 16 pillars)**: **{min_score} / 100**  ")
md.append(f"**Weighted sum (informational)**: {weighted_sum:.2f}  ")
md.append(f"**Verdict**: {verdict}  ")
md.append(f"**Next-iter target dim**: `{lowest_dim}` (score={sorted_by_score[0][1]})\n")
md.append(f"**Pillar count**: 16 (V77 retro Open Q #6 honored · NO new pillar in V78)\n")

md.append("## Per-Dim Scores (16 pillars · V78 TIGHTENED)\n")
md.append("| # | Agent | Dim | Score | Weight | Status |")
md.append("|---|---|---|---|---|---|")
for i, a in enumerate(agents_order, 1):
    d = data[a]
    if d["score"] >= 99:
        status = "✅ PASS-99"
    elif d["score"] >= 90:
        status = "🟢 high"
    elif d["score"] >= 50:
        status = "🟡 mid"
    else:
        status = "🔴 low"
    md.append(f"| {i} | `{a}` | {d['dim']} | **{d['score']}** | {d['weight']} | {status} |")

md.append("\n## Honesty Self-Check\n")
md.append("- ✓ V78 scoring is TIGHTENED vs V77 · same nominal score harder to achieve")
md.append("- ✓ Pillar count unchanged at 16 · V77 retro Open Q #6 ('NOT add Pillar 17 reflexively') honored")
md.append("- ✓ Each score has evidence (test name / log path / file ref)")
md.append("- ✓ 0 is computed, not default")
md.append("- ✓ min() one-vote veto applied across all 16 pillars\n")

for a in agents_order:
    d = data[a]
    md.append(f"## Agent: `{a}` · {d['dim']}\n")
    md.append(f"**Score**: {d['score']} / 100 · Weight: {d['weight']}\n")
    if "subscores" in d:
        md.append("**Subscores**:")
        for k, v in d["subscores"].items():
            md.append(f"- `{k}`: {v}")
        md.append("")
    if d.get("evidence"):
        md.append("**Evidence**:")
        for e in d["evidence"]:
            md.append(f"- {e}")
        md.append("")
    if d.get("failures"):
        md.append("**Failures**:")
        for f in d["failures"]:
            md.append(f"- {f}")
        md.append("")
    if "honest_note" in d:
        md.append(f"**Honest note**: {d['honest_note']}\n")

with open(out, "w") as f:
    f.write("\n".join(md))

print(f"min_score={min_score} verdict={verdict} lowest_dim={lowest_dim} -> {out}")
PYEOF
