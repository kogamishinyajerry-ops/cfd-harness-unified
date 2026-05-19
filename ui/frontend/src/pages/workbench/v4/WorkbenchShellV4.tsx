/**
 * V92-UI-V4 · Workbench Shell · Industrial-Minimalist
 *
 * 5-zone grid per `.planning/transitions/2026-05-18_blueprint_read.md` §2:
 *   ┌────────────────────────────────────────────────┐
 *   │ TopBar (32px)                                  │
 *   ├──────┬─────────────────────────────────┬───────┤
 *   │ Left │           MainCanvas            │ Right │
 *   │ Rail │                                 │ Panel │
 *   │ 220px│                                 │ 300px │
 *   │      ├─────────────────────────────────┤       │
 *   │      │ KPI strip (80px)                │       │
 *   ├──────┴─────────────────────────────────┴───────┤
 *   │ BottomBar · 7-step pipeline (56px)             │
 *   └────────────────────────────────────────────────┘
 *
 * Each zone is wrapped in V4ErrorBoundary so one render-time crash
 * doesn't blank the whole workbench. Thin zones (TopBar / KpiStrip /
 * BottomBar) get a compact one-line fallback so the error UI fits the
 * fixed-height row.
 */
import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { V4_PIPELINE_STEPS } from "@/theme/industrial_minimalist";

import { BottomBarV4 } from "./components/BottomBarV4";
import { CommandPaletteV4, useCmdK } from "./components/CommandPaletteV4";
import { KpiStripV4 } from "./components/KpiStripV4";
import { LeftRailV4 } from "./components/LeftRailV4";
import { MainCanvasV4 } from "./components/MainCanvasV4";
import { RightPanelV4 } from "./components/RightPanelV4";
import { TopBarV4 } from "./components/TopBarV4";
import { V4ErrorBoundary } from "./components/V4ErrorBoundary";
import { V4_PALETTE } from "@/theme/industrial_minimalist";
import type { V4PipelineStepId } from "@/theme/industrial_minimalist";

/** Compact 1-line fallback for fixed-height thin zones (TopBar 32px,
 *  KpiStrip 96px, BottomBar 60px) — the default card-style fallback
 *  would clip or break parent flex sizing. */
function thinZoneFallback(zone: string, height: string) {
  return (error: Error, retry: () => void) => (
    <div
      className={`flex ${height} shrink-0 items-center justify-between border-y border-v4-crit/30 bg-v4-surface px-3 text-[11px]`}
      data-testid={`v4-error-boundary-${zone}-thin`}
      role="alert"
    >
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className="h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: V4_PALETTE.crit }}
        />
        <span className="text-v4-textPrimary">{zone} 渲染失败</span>
        <span
          className="max-w-[420px] truncate font-mono text-[10px] text-v4-textTertiary"
          title={error.message}
        >
          · {error.message || "unknown"}
        </span>
      </div>
      <button
        type="button"
        onClick={retry}
        className="rounded border border-v4-border bg-v4-surfaceRaised px-2 py-0.5 text-[10px] text-v4-textPrimary transition-colors hover:border-v4-borderActive"
      >
        重试
      </button>
    </div>
  );
}

/** Valid step ids — derived from V4_PIPELINE_STEPS so the URL ↔ state
 *  contract stays in sync with the canonical pipeline definition. */
const VALID_STEP_IDS = V4_PIPELINE_STEPS.map((s) => s.id) as readonly string[];

function isValidStepId(value: string | null): value is V4PipelineStepId {
  return value !== null && VALID_STEP_IDS.includes(value);
}

export function WorkbenchShellV4() {
  const { caseId } = useParams<{ caseId?: string }>();

  // URL ↔ state sync (2026-05-19 dogfood-driven fix): the prior
  // implementation hard-coded the default to "solver" and never read
  // ?step= — so deep-links like /workbench/case/<id>?step=physics
  // landed silently on Solver and the user couldn't tell whether the
  // navigation worked. Now: URL is the source of truth, setStep also
  // writes URL so reload / share / back / forward all behave.
  const [searchParams, setSearchParams] = useSearchParams();
  const stepFromUrl = searchParams.get("step");
  const initialStep: V4PipelineStepId = isValidStepId(stepFromUrl)
    ? stepFromUrl
    : "solver";
  const [activeStep, setActiveStepRaw] = useState<V4PipelineStepId>(initialStep);
  const [viewportMode, setViewportMode] = useState<V4PipelineStepId>(initialStep);
  const [viewportOverride, setViewportOverride] = useState(false);

  // Keep state in sync with URL when the user uses back/forward / pastes
  // a new URL while on the same shell instance.
  useEffect(() => {
    if (isValidStepId(stepFromUrl) && stepFromUrl !== activeStep) {
      setActiveStepRaw(stepFromUrl);
      if (stepFromUrl === viewportMode) {
        setViewportOverride(false);
      } else if (!viewportOverride) {
        setViewportMode(stepFromUrl);
      }
    }
  }, [stepFromUrl, activeStep, viewportMode, viewportOverride]);

  const setActiveStep = useCallback(
    (next: V4PipelineStepId) => {
      setActiveStepRaw(next);
      if (next === viewportMode) {
        setViewportOverride(false);
      } else if (!viewportOverride) {
        setViewportMode(next);
      }
      setSearchParams(
        (prev) => {
          const out = new URLSearchParams(prev);
          out.set("step", next);
          return out;
        },
        { replace: true },
      );
    },
    [setSearchParams, viewportMode, viewportOverride],
  );

  const handleViewportModeChange = useCallback(
    (next: V4PipelineStepId) => {
      setViewportMode(next);
      setViewportOverride(next !== activeStep);
    },
    [activeStep],
  );

  const [cmdkOpen, setCmdkOpen] = useState(false);
  const toggleCmdk = useCallback(() => setCmdkOpen((v) => !v), []);
  useCmdK(toggleCmdk);

  return (
    <div
      className="flex h-screen w-screen flex-col overflow-hidden bg-v4-shell text-v4-textPrimary"
      data-testid="workbench-shell-v4"
    >
      <V4ErrorBoundary
        zone="TopBar"
        renderFallback={thinZoneFallback("TopBar", "h-8")}
      >
        <TopBarV4 caseId={caseId} activeStep={activeStep} />
      </V4ErrorBoundary>

      <div className="flex min-h-0 flex-1">
        <V4ErrorBoundary zone="LeftRail">
          <LeftRailV4
            activeStep={activeStep}
            onStepChange={setActiveStep}
            caseId={caseId ?? null}
          />
        </V4ErrorBoundary>

        <main className="flex min-w-0 flex-1 flex-col">
          <V4ErrorBoundary zone="MainCanvas">
            <MainCanvasV4
              activeStep={activeStep}
              viewportMode={viewportMode}
              onViewportModeChange={handleViewportModeChange}
              caseId={caseId}
            />
          </V4ErrorBoundary>
          <V4ErrorBoundary
            zone="KpiStrip"
            renderFallback={thinZoneFallback("KpiStrip", "h-24")}
          >
            <KpiStripV4 activeStep={activeStep} caseId={caseId ?? null} />
          </V4ErrorBoundary>
        </main>

        <V4ErrorBoundary zone="RightPanel">
          <RightPanelV4
            activeStep={activeStep}
            viewportMode={viewportMode}
            caseId={caseId ?? null}
          />
        </V4ErrorBoundary>
      </div>

      <V4ErrorBoundary
        zone="BottomBar"
        renderFallback={thinZoneFallback("BottomBar", "h-[60px]")}
      >
        <BottomBarV4
          activeStep={activeStep}
          onStepChange={setActiveStep}
          caseId={caseId ?? null}
        />
      </V4ErrorBoundary>

      {/* Cmd+K command palette · overlays everything when open */}
      <CommandPaletteV4
        open={cmdkOpen}
        onClose={() => setCmdkOpen(false)}
        onStepChange={setActiveStep}
      />
    </div>
  );
}
