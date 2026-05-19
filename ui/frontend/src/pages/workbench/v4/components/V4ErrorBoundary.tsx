/**
 * V4 · ErrorBoundary · zone-level crash isolation.
 *
 * Each shell zone (TopBar / LeftRail / MainCanvas / KpiStrip / RightPanel
 * / BottomBar) is wrapped so a render-time throw in one renderer doesn't
 * blank the whole workbench. On crash the boundary renders a compact
 * v4-styled fallback card with the zone label + retry button.
 *
 * Why a class component: React's componentDidCatch lifecycle is still
 * only available on class components in 19.x. The functional
 * react-error-boundary wrapper exists but is a third-party dependency
 * we don't otherwise carry; ~60 LOC of zero-dep code is cheaper.
 *
 * Reset behaviour: the retry button bumps an internal ``resetKey`` that
 * the boundary uses to remount its children. This works for transient
 * issues (race on first paint, network blip on mounted query). Persistent
 * issues will re-throw immediately — that's the correct semantics; the
 * UI should not pretend the bug is fixed.
 */
import { Component, Fragment, type ErrorInfo, type ReactNode } from "react";

import { V4_PALETTE } from "@/theme/industrial_minimalist";

interface V4ErrorBoundaryProps {
  /** Short label shown in the fallback card. Examples: "TopBar" /
   *  "MainCanvas". Used as the test-id suffix and the error console
   *  tag so a downstream crash report can be triaged quickly. */
  zone: string;
  children: ReactNode;
  /** Optional render override — useful for zones where the default
   *  card is too tall (e.g. TopBar = 32px). */
  renderFallback?: (error: Error, retry: () => void) => ReactNode;
}

interface V4ErrorBoundaryState {
  error: Error | null;
  resetKey: number;
}

export class V4ErrorBoundary extends Component<
  V4ErrorBoundaryProps,
  V4ErrorBoundaryState
> {
  state: V4ErrorBoundaryState = { error: null, resetKey: 0 };

  static getDerivedStateFromError(error: Error): Partial<V4ErrorBoundaryState> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Tag the error with the zone so the console diff is actionable.
    // eslint-disable-next-line no-console
    console.error(
      `[V4ErrorBoundary · ${this.props.zone}] render crash`,
      error,
      info.componentStack,
    );
  }

  retry = (): void => {
    this.setState((s) => ({ error: null, resetKey: s.resetKey + 1 }));
  };

  render(): ReactNode {
    const { error, resetKey } = this.state;
    const { zone, children, renderFallback } = this.props;

    if (error) {
      if (renderFallback) return renderFallback(error, this.retry);
      return (
        <div
          className="flex h-full min-h-[48px] w-full items-center justify-center bg-v4-surface p-3"
          data-testid={`v4-error-boundary-${zone}`}
          data-zone={zone}
          role="alert"
        >
          <div className="flex flex-col items-start gap-2 rounded border border-v4-crit/40 bg-v4-surfaceRaised px-3 py-2 text-[11px]">
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: V4_PALETTE.crit }}
              />
              <span className="font-medium text-v4-textPrimary">
                {zone} 区域渲染失败
              </span>
            </div>
            <div
              className="max-w-[280px] truncate font-mono text-[10px] text-v4-textTertiary"
              title={error.message}
            >
              {error.message || "unknown error"}
            </div>
            <button
              type="button"
              onClick={this.retry}
              className="self-end rounded border border-v4-border bg-v4-surface px-2 py-0.5 text-[10px] text-v4-textPrimary transition-colors hover:border-v4-borderActive"
              data-testid={`v4-error-boundary-${zone}-retry`}
            >
              重试
            </button>
          </div>
        </div>
      );
    }

    // Fragment + key: avoid adding a wrapper <div> that would break
    // flex-row/flex-col layout in parent containers (LeftRail must
    // remain a direct flex item of its row, TopBar of its column).
    // Bumping resetKey on retry forces React to unmount the previous
    // subtree and remount fresh so transient state (failed queries,
    // half-bound vtk kernels) is reset.
    return <Fragment key={resetKey}>{children}</Fragment>;
  }
}
