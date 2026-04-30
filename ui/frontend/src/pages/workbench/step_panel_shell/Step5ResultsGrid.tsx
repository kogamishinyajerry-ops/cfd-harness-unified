// Step 5 viewport — 2×2 figure grid for the multi-figure post-
// processing bundle (2026-04-30 dogfood-feedback rewrite).
//
// Mounted by StepPanelShell as the Step 5 customViewport. Polls the
// /report-bundle endpoint via React Query; renders four cached PNGs
// side-by-side. The bundle endpoint is idempotent + cached, so this
// is safe to call repeatedly without re-running matplotlib.
//
// Empty state: while the bundle hasn't been fetched yet (Step 4
// solve done but Step 5 [AI 处理] not yet clicked), render a hint
// telling the user where to click. Error state: surface the rejection
// so the user knows whether it's "solve hasn't run" vs. "container
// down" vs. "field malformed".

import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";

interface Step5ResultsGridProps {
  caseId: string;
  height: number;
}

interface FigureCardProps {
  title: string;
  caption: string;
  url: string;
}

function FigureCard({ title, caption, url }: FigureCardProps) {
  return (
    <figure className="flex min-h-0 flex-col rounded-md border border-surface-800 bg-surface-950/60">
      <figcaption className="flex items-baseline justify-between border-b border-surface-800 px-3 py-1.5 text-[10px]">
        <span className="font-mono uppercase tracking-wider text-surface-200">
          {title}
        </span>
        <span className="text-surface-500">{caption}</span>
      </figcaption>
      <div className="flex min-h-0 flex-1 items-center justify-center p-2">
        <img
          src={url}
          alt={title}
          className="max-h-full max-w-full object-contain"
        />
      </div>
    </figure>
  );
}

export function Step5ResultsGrid({ caseId, height }: Step5ResultsGridProps) {
  // The Step 5 right-rail's [AI 处理] populates the cache via
  // queryClient.fetchQuery(['report-bundle', caseId], ...). This grid
  // observes the same key with enabled=false so it never fires its
  // own network request — it simply re-renders when the cache value
  // changes. retry=false so a 409 (solve hasn't run) stays in the
  // error state without backoff churn.
  const { data, isLoading, error } = useQuery({
    queryKey: ["report-bundle", caseId],
    queryFn: () => api.reportBundle(caseId),
    enabled: false,
    retry: false,
    staleTime: Infinity,
  });

  if (isLoading) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center rounded-md border border-dashed border-surface-800 bg-surface-950/40 text-[12px] text-surface-500"
      >
        rendering report bundle…
      </div>
    );
  }

  if (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : error instanceof Error
          ? error.message
          : String(error);
    const status = error instanceof ApiError ? error.status : null;
    // 409 = solve hasn't run yet — friendly empty state, not an error.
    if (status === 409) {
      return (
        <div
          style={{ height }}
          data-testid="step5-grid-empty"
          className="flex items-center justify-center rounded-md border border-dashed border-surface-800 bg-surface-950/40 p-6 text-center text-[12px] text-surface-500"
        >
          <span>
            Step 5 · Results — finish Step 4 (solve), then click{" "}
            <strong className="text-surface-300">[AI 处理]</strong> to
            render the multi-panel report.
          </span>
        </div>
      );
    }
    return (
      <div
        style={{ height }}
        data-testid="step5-grid-error"
        className="flex items-center justify-center rounded-md border border-rose-700/40 bg-rose-900/10 p-4 text-center text-[12px] text-rose-200"
      >
        report-bundle error{status ? ` (HTTP ${status})` : ""}: {message}
      </div>
    );
  }

  if (!data) {
    return (
      <div
        style={{ height }}
        data-testid="step5-grid-empty"
        className="flex items-center justify-center rounded-md border border-dashed border-surface-800 bg-surface-950/40 p-6 text-center text-[12px] text-surface-500"
      >
        <span>
          Step 5 · Results — click{" "}
          <strong className="text-surface-300">[AI 处理]</strong> in the
          right rail to render the report bundle.
        </span>
      </div>
    );
  }

  const cells = data.cell_count.toLocaleString();
  const planeLabel = data.plane_axes.join("-");
  return (
    <div
      style={{ height }}
      data-testid="step5-grid"
      className="flex min-h-0 flex-col gap-2"
    >
      <div className="flex items-baseline justify-between border-b border-surface-800 pb-1 text-[10px]">
        <span className="font-mono uppercase tracking-wider text-surface-200">
          Multi-figure report · t = {data.final_time}s · {cells} cells
        </span>
        <span className="text-surface-500">
          midplane = {planeLabel} · {data.slab_cell_count.toLocaleString()} slab
          cells
        </span>
      </div>
      <div className="grid min-h-0 flex-1 grid-cols-2 grid-rows-2 gap-2">
        <FigureCard
          title="|U| + streamlines"
          caption="velocity magnitude · streamplot"
          url={data.artifacts.contour_streamlines}
        />
        <FigureCard
          title="gauge pressure"
          caption="p / ρ · diverging colormap"
          url={data.artifacts.pressure}
        />
        <FigureCard
          title="vorticity"
          caption="∂Uy/∂x − ∂Ux/∂y"
          url={data.artifacts.vorticity}
        />
        <FigureCard
          title="centreline profiles"
          caption="U_x(y) · U_y(x) at midlines"
          url={data.artifacts.centerline}
        />
      </div>
    </div>
  );
}
