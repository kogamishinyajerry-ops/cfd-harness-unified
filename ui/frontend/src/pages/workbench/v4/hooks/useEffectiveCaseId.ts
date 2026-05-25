/**
 * DEC-V61-202 M3.8 cycle 1 · DRY hook for V4 shell blueprint-vs-case gating.
 *
 * Three V4 shell components (TopBarV4 / LeftRailV4 / KpiStripV4) all need the
 * same logic for deciding whether to render the static teaching blueprint
 * (DoE library or geometry APU placeholder) vs the real case-driven view.
 * Before M3.8 each had its own copy of `activeStep === "geometry" && !caseId`
 * inlined three different ways — a janitorial DRY hazard that masked B7
 * (workbench chrome stuck in blueprint mode regardless of caseId · closed M3.7
 * with 3-file fix). This hook centralizes the decision so future shell
 * components inherit the same gate.
 *
 * Behavior contract:
 * - DoE step: ALWAYS blueprint mode (no per-case DoE wiring exists yet)
 * - Geometry step + no case: blueprint mode (APU teaching preview)
 * - Geometry step + case loaded: case mode (real basics-driven render)
 * - Any other step: case mode (caseId passed through; null falls back to em-dash placeholder)
 */
import { useMemo } from "react";
import type { V4PipelineStepId } from "@/theme/industrial_minimalist";

export interface EffectiveCaseId {
  /** caseId to pass to useV4WorkbenchContext / useResidualSeries. Null in blueprint mode so those hooks don't fetch. */
  effectiveCaseId: string | null;
  /** True when chrome should render the static teaching blueprint (DoE or no-case-geometry). */
  isBlueprintMode: boolean;
  /** Convenience flag — DoE step. */
  isDoe: boolean;
  /** Convenience flag — geometry blueprint preview (geometry step AND no case). */
  isGeometryBlueprint: boolean;
}

export function useEffectiveCaseId(
  caseId: string | null | undefined,
  activeStep: V4PipelineStepId,
): EffectiveCaseId {
  return useMemo(() => {
    const isDoe = activeStep === "doe";
    const isGeometryBlueprint = activeStep === "geometry" && !caseId;
    const isBlueprintMode = isDoe || isGeometryBlueprint;
    return {
      effectiveCaseId: isBlueprintMode ? null : (caseId ?? null),
      isBlueprintMode,
      isDoe,
      isGeometryBlueprint,
    };
  }, [caseId, activeStep]);
}
