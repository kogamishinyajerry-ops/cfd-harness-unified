/**
 * V85.4 · V6.C Live-vs-Curated Diff Panel
 *
 * Side-by-side display of curated banner (V5.A getSandboxStepState) vs
 * real-artifact banner (V6.A getBridgeStepState) for the current step.
 * Surfaces divergences as PASSIVE AI advisor observations — V130
 * invariant forbids action affordances here.
 *
 * V6 contract V6.C · `.planning/blueprints/v6/INDEX.md`:
 *   - Hidden when bridge mode is OFF (default curated path preserved)
 *   - Two-column layout: curated left, bridge right
 *   - Divergence badge `[divergence]` when significant differences detected
 *   - Observations describe (not recommend) — denylist enforced by tests
 *
 * Significant divergences this panel currently surfaces:
 *   - artifact reports FAIL but curated narrative implies PASS
 *   - failure_category present (curated has none)
 *   - placeholder Re = 99999999 (real run with mock task spec)
 *
 * V130/V132:
 *   - Pure render from props · no fetch · no side effects
 *   - Zero buttons (so no auto-fix surface) · zero form/input/select
 *   - Observations are <span> labels, not actionable affordances
 */

import type { StepId } from "../WorkbenchShellV3";
import { getSandboxStepState } from "@/data/sandbox_step_states";
import {
  getBridgeStepState,
  type BridgeArtifact,
} from "@/data/run_artifact_reader";

interface LiveVsCuratedDiffV6Props {
  /** Bridge mode active flag (parent decides; usually
   *  `searchParams.get("bridge") === "1" && artifact != null`). */
  active: boolean;
  caseId: string | null;
  stepId: StepId;
  bridgeArtifact: BridgeArtifact | null;
}

interface Divergence {
  kind:
    | "verdict_mismatch"
    | "failure_category_present"
    | "placeholder_re";
  /** Passive descriptive note. Does NOT include "fix" / "click" / "run". */
  note: string;
}

function detectDivergences(
  bridge: ReturnType<typeof getBridgeStepState>,
  curated: ReturnType<typeof getSandboxStepState>,
  artifact: BridgeArtifact | null,
): Divergence[] {
  if (!bridge || !artifact) return [];
  const out: Divergence[] = [];

  // (a) verdict mismatch — curated narratives describe successful runs;
  // when the real artifact failed, surface that as a clear difference.
  if (!bridge.artifactSuccess) {
    out.push({
      kind: "verdict_mismatch",
      note: "Real run did not pass; curated narrative shows the expected-pass path.",
    });
  }

  // (b) failure category present
  if (bridge.failureCategory) {
    out.push({
      kind: "failure_category_present",
      note: `Real run failure_category = "${bridge.failureCategory}". Curated narrative has no failure category.`,
    });
  }

  // (c) placeholder Re — real artifacts sometimes carry Re=99999999 from
  // draft task spec scaffolding. Flag for awareness, do not act.
  const re = artifact.task_spec?.["Re"];
  if (typeof re === "number" && re >= 1e6) {
    out.push({
      kind: "placeholder_re",
      note: `Real run task_spec Re=${re} appears to be a placeholder; curated narrative uses canonical Re for this case.`,
    });
  }

  // Curated state is needed for caller-side alignment but not directly
  // compared here; future V7+ could add numeric-field deltas (e.g.,
  // curated "skewness 0.32" vs real artifact key_quantities skewness).
  void curated;

  return out;
}

export function LiveVsCuratedDiffV6({
  active,
  caseId,
  stepId,
  bridgeArtifact,
}: LiveVsCuratedDiffV6Props) {
  if (!active) return null;

  const curated = getSandboxStepState(caseId, stepId);
  const bridge = getBridgeStepState(bridgeArtifact, stepId);

  // If bridge is null even when mode is active, the parent shouldn't
  // have set active=true. Guard rather than crash.
  if (!bridge) return null;

  const divergences = detectDivergences(bridge, curated, bridgeArtifact);

  return (
    <div
      data-testid="live-vs-curated-diff"
      data-step-id={String(stepId)}
      data-case-id={caseId ?? "__fallback__"}
      data-divergence-count={String(divergences.length)}
      className="grid grid-cols-2 gap-3 mt-2 p-3 border border-v3-border rounded text-xs font-mono"
    >
      <div
        data-testid="diff-column-curated"
        className="flex flex-col gap-1 border-r border-v3-border pr-3"
      >
        <span className="text-v3-textTertiary uppercase tracking-[0.08em] text-[10px]">
          curated · V5
        </span>
        <span className="text-v3-textPrimary">
          Step {stepId} · {curated.banner}
        </span>
      </div>
      <div
        data-testid="diff-column-bridge"
        className="flex flex-col gap-1 pl-1"
      >
        <span className="text-v3-accent uppercase tracking-[0.08em] text-[10px]">
          live · V6 bridge · run {bridge.runId}
        </span>
        <span className="text-v3-textPrimary">{bridge.banner}</span>
      </div>
      {divergences.length > 0 && (
        <div
          data-testid="diff-divergences"
          data-divergence-kinds={divergences.map((d) => d.kind).join(",")}
          className="col-span-2 mt-2 pt-2 border-t border-v3-border flex flex-col gap-1"
        >
          <span
            data-testid="divergence-badge"
            className="self-start text-[10px] uppercase tracking-[0.08em] border border-v3-accent rounded px-1.5 py-0 text-v3-accent"
          >
            [divergence × {divergences.length}]
          </span>
          {divergences.map((d, i) => (
            <span
              key={`${d.kind}-${i}`}
              data-testid={`divergence-note-${d.kind}`}
              className="text-v3-textSecondary"
            >
              · {d.note}
            </span>
          ))}
          <span className="text-v3-textTertiary text-[10px] mt-1">
            (AI advisor passive · observations only · no remediation action available here)
          </span>
        </div>
      )}
    </div>
  );
}
