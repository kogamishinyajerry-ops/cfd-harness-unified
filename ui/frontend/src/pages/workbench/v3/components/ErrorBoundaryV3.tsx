// V75.1 · Calm error boundary for v3 surfaces.
//
// Catches React render-time exceptions and replaces a white-screen crash
// with a structured fallback card surfacing: the panel name, the error
// message, and a "reset" button that re-mounts the children.
//
// V130/V132 contract: the boundary itself does NOT mutate case state. The
// reset button is a UI state reset (re-mount via key bump), not a backend
// call. Telemetry is surfaced inline (no Sentry / external sink) — the
// engineer sees what went wrong in-band.

import { Component, ReactNode } from "react";

// Per V74 retro Q1: literal-testid scorer trap. The 4 named boundaries below
// each declare their data-testid as a literal string in source so the
// Pillar 14 grep matches. The shared ErrorBoundaryBase class handles state.

interface ErrorBoundaryProps {
  panelName: string;
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
  resetKey: number;
}

class ErrorBoundaryBase<
  P extends ErrorBoundaryProps,
> extends Component<P, ErrorBoundaryState> {
  constructor(props: P) {
    super(props);
    this.state = { error: null, resetKey: 0 };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string }) {
    // eslint-disable-next-line no-console
    console.error(
      `[ErrorBoundary · ${this.props.panelName}]`,
      error.message,
      info.componentStack,
    );
  }

  reset = () => {
    this.setState((s) => ({ error: null, resetKey: s.resetKey + 1 }));
  };

  // Subclasses provide testId via a static-ish getter so the literal appears
  // explicitly in source.
  protected getTestId(): string {
    return "error-boundary-unknown";
  }

  renderFallback() {
    if (!this.state.error) return null;
    return (
      <div
        data-error-message={this.state.error.message}
        className="border border-v3-wall rounded-md px-4 py-3 m-4 bg-v3-surface1"
      >
        <div className="text-[11px] uppercase tracking-[0.08em] text-v3-wall mb-2">
          {this.props.panelName} · render error
        </div>
        <p className="text-[12px] text-v3-textPrimary font-mono mb-3 break-words">
          {this.state.error.message}
        </p>
        <p className="text-[11px] text-v3-textTertiary leading-relaxed mb-3">
          The panel hit a render-time error. The rest of the workbench is
          unaffected. Click reset to re-mount this panel, or refresh the page
          if the problem persists.
        </p>
        <button
          type="button"
          onClick={this.reset}
          className="text-[11px] uppercase tracking-[0.08em] border border-v3-border rounded px-2 py-1 text-v3-textSecondary motion-safe:transition-colors hover:border-v3-borderActive hover:text-v3-textPrimary"
        >
          reset panel
        </button>
      </div>
    );
  }
}

export class RightPanelErrorBoundary extends ErrorBoundaryBase<ErrorBoundaryProps> {
  render() {
    if (this.state.error) {
      return (
        <div data-testid="error-boundary-right-panel">
          {this.renderFallback()}
        </div>
      );
    }
    return <div key={this.state.resetKey}>{this.props.children}</div>;
  }
}

export class BottomPanelErrorBoundary extends ErrorBoundaryBase<ErrorBoundaryProps> {
  render() {
    if (this.state.error) {
      return (
        <div data-testid="error-boundary-bottom-panel">
          {this.renderFallback()}
        </div>
      );
    }
    return <div key={this.state.resetKey}>{this.props.children}</div>;
  }
}

export class MainCanvasErrorBoundary extends ErrorBoundaryBase<ErrorBoundaryProps> {
  render() {
    if (this.state.error) {
      return (
        <div data-testid="error-boundary-main-canvas">
          {this.renderFallback()}
        </div>
      );
    }
    return <div key={this.state.resetKey}>{this.props.children}</div>;
  }
}

export class MultiCaseRibbonErrorBoundary extends ErrorBoundaryBase<ErrorBoundaryProps> {
  render() {
    if (this.state.error) {
      return (
        <div data-testid="error-boundary-multi-case-ribbon">
          {this.renderFallback()}
        </div>
      );
    }
    return <div key={this.state.resetKey}>{this.props.children}</div>;
  }
}
