/**
 * V4 · BottomBar · 60px · per UI-SPEC §2.5 · Phase B real backend wiring.
 *
 * Pipeline step state derived from useV4WorkbenchContext data presence:
 *   - import:   case exists (basics OR caseId+latestRun resolved)
 *   - geometry: basics.patches.length > 0
 *   - mesh:     meshMetrics.densities.length > 0
 *   - physics:  basics.solver != null
 *   - boundary: basics.boundary_conditions.length > 0
 *   - solver:   latestRun != null
 *   - post:     latestRun.success === true (case completed cleanly)
 *   - doe:      stays pending (no DOE backend yet)
 *
 * activeIndex = max of (activeStep passed by user) and (first incomplete
 * pipeline step) so the rail naturally tracks where the user is + where
 * data ends. Per-dot state derives from this combined cursor.
 */
import {
  V4_PALETTE,
  V4_PIPELINE_STATE_COLOR,
  V4_PIPELINE_STEPS,
  type V4PipelineStepId,
  type V4PipelineState,
} from "@/theme/industrial_minimalist";
import { useV4WorkbenchContext } from "../hooks/useV4WorkbenchContext";
import type { V4Context } from "../hooks/useV4WorkbenchContext";

interface BottomBarV4Props {
  activeStep: V4PipelineStepId;
  onStepChange: (step: V4PipelineStepId) => void;
  caseId?: string | null;
}

/** Return the set of pipeline step ids that backend data shows as "done". */
function deriveDoneSteps(ctx: V4Context): Set<V4PipelineStepId> {
  const done = new Set<V4PipelineStepId>();
  if (!ctx.caseId) return done;
  if (!ctx.hasBackend) return done;

  // import = a case is identifiable (caseId set and backend confirmed something)
  if (ctx.basics != null || ctx.latestRun != null) {
    done.add("import");
  }

  const basics = ctx.basics;
  if (basics?.patches && basics.patches.length > 0) done.add("geometry");
  if (basics?.solver != null) done.add("physics");
  if (basics?.boundary_conditions && basics.boundary_conditions.length > 0) {
    done.add("boundary");
  }

  if (ctx.meshMetrics?.densities && ctx.meshMetrics.densities.length > 0) {
    done.add("mesh");
  }

  if (ctx.latestRun != null) done.add("solver");
  if (ctx.latestRun?.success === true) done.add("post");

  return done;
}

interface DotProps {
  state: V4PipelineState;
}

function PipelineDot({ state }: DotProps) {
  const color = V4_PIPELINE_STATE_COLOR[state];

  if (state === "active") {
    return (
      <span className="relative flex h-3.5 w-3.5 items-center justify-center">
        <span
          aria-hidden
          className="absolute inset-0 animate-ping rounded-full"
          style={{
            backgroundColor: color,
            opacity: 0.35,
            animationDuration: "2.4s",
          }}
        />
        <span
          aria-hidden
          className="relative h-3 w-3 rounded-full"
          style={{
            backgroundColor: color,
            boxShadow: `0 0 0 3px ${color}55, 0 0 10px ${color}88`,
          }}
        />
      </span>
    );
  }

  if (state === "done") {
    return (
      <span
        className="flex h-2.5 w-2.5 items-center justify-center rounded-full"
        style={{ backgroundColor: color }}
      >
        <svg viewBox="0 0 24 24" width="7" height="7" aria-hidden>
          <path
            d="M5 12l4 4 10-10"
            stroke={V4_PALETTE.shell}
            strokeWidth="3"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    );
  }

  return (
    <span
      className="h-2 w-2 rounded-full border border-v4-textTertiary/70"
      aria-hidden
    />
  );
}

export function BottomBarV4({
  activeStep,
  onStepChange,
  caseId = null,
}: BottomBarV4Props) {
  const isDoe = activeStep === "doe";
  const ctx = useV4WorkbenchContext(isDoe ? null : caseId);
  const doneSteps = isDoe
    ? new Set<V4PipelineStepId>([
        "import",
        "geometry",
        "mesh",
        "physics",
        "boundary",
        "solver",
        "post",
      ])
    : deriveDoneSteps(ctx);

  // DOE remains conditional: include it only when the DOE cockpit is active.
  const VISIBLE_STEPS = V4_PIPELINE_STEPS.filter(
    (s) => !("conditional" in s && s.conditional) || isDoe,
  );

  const activeIndex = VISIBLE_STEPS.findIndex((s) => s.id === activeStep);
  const totalSteps = VISIBLE_STEPS.length;

  // Done-portion runs up to the LAST consecutive done step from the start.
  let lastDoneIndex = -1;
  for (let i = 0; i < VISIBLE_STEPS.length; i++) {
    if (doneSteps.has(VISIBLE_STEPS[i].id)) lastDoneIndex = i;
    else break;
  }
  const completedFraction = (lastDoneIndex + 1) / Math.max(1, totalSteps - 1);

  function stateFor(idx: number, id: V4PipelineStepId): V4PipelineState {
    if (idx === activeIndex) return "active";
    if (doneSteps.has(id)) return "done";
    return "pending";
  }

  return (
    <footer
      className="relative flex h-[60px] shrink-0 items-center border-t border-v4-border bg-v4-surface px-8"
      data-testid="bottombar-v4"
      data-backend-connected={ctx.hasBackend ? "true" : "false"}
    >
      <div className="relative flex flex-1 items-center">
        {/* Background hairline */}
        <span
          aria-hidden
          className="absolute left-0 right-0 top-1/2 h-px -translate-y-[1px] bg-v4-border"
        />
        {/* Completed-portion rail · green up to lastDoneIndex */}
        {lastDoneIndex > 0 && (
          <span
            aria-hidden
            className="absolute left-0 top-1/2 h-px -translate-y-[1px] bg-v4-healthy/70"
            style={{
              width: `${Math.min(1, completedFraction) * 100}%`,
            }}
          />
        )}

        {VISIBLE_STEPS.map((step, i) => {
          const state = stateFor(i, step.id);
          return (
            <button
              key={step.id}
              type="button"
              onClick={() => onStepChange(step.id)}
              className="group relative z-10 flex flex-1 flex-col items-center gap-1.5 py-1 transition-colors"
              data-testid={`bottombar-v4-step-${step.id}`}
              data-state={state}
            >
              <span
                className="absolute -top-0.5 font-mono text-[9px] text-v4-textTertiary"
                aria-hidden
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="mt-3 flex h-4 items-center justify-center">
                <PipelineDot state={state} />
              </span>
              <span
                className={[
                  "text-[10px] font-medium leading-none",
                  state === "active" && "text-v4-textPrimary",
                  state === "done" && "text-v4-textSecondary",
                  state === "pending" && "text-v4-textTertiary",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {step.label}
              </span>
            </button>
          );
        })}
      </div>
    </footer>
  );
}
