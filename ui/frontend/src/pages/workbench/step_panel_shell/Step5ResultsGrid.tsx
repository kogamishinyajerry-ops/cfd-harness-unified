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

import { useState } from "react";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";

interface Step5ResultsGridProps {
  caseId: string;
  height: number;
}

interface FigureCardProps {
  title: string;
  caption: string;
  url: string;
  onStale: () => void;
}

function FigureCard({ title, caption, url, onStale }: FigureCardProps) {
  // Codex round-6 P2 (2026-04-30): the /report/{name}.png route can
  // return 410 Gone if the case was re-solved between the bundle
  // metadata fetch and this image fetch. <img onError> doesn't expose
  // the HTTP status, so probe the URL via fetch() and only set src
  // when we get 200. On 410 (or any non-OK), fire onStale so the
  // grid can drop the bundle from React Query cache and render the
  // empty hint, prompting the user to click [AI 处理] again.
  const [staleHit, setStaleHit] = useState(false);

  if (staleHit) {
    return (
      <figure className="flex min-h-0 flex-col rounded-md border border-amber-700/40 bg-amber-900/10 p-3">
        <figcaption className="text-[10px] font-mono uppercase tracking-wider text-amber-200">
          {title}
        </figcaption>
        <p className="mt-2 text-[11px] text-amber-100">
          Image stale (case was re-solved). Click [AI 处理] in the right
          rail to refresh.
        </p>
      </figure>
    );
  }

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
          onError={() => {
            // Image element's onError fires on any load failure
            // (broken bytes, 4xx, network). Probe the URL to
            // distinguish 410 (stale) from a real failure.
            fetch(url, { method: "HEAD" })
              .then((resp) => {
                if (resp.status === 410) {
                  setStaleHit(true);
                  onStale();
                }
              })
              .catch(() => {
                // Network error — leave the broken-image state as-is;
                // user can still re-click [AI 处理] manually.
              });
          }}
        />
      </div>
    </figure>
  );
}

export function Step5ResultsGrid({ caseId, height }: Step5ResultsGridProps) {
  const queryClient = useQueryClient();
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

  // Codex round-6 P2: when an artifact 410s the bundle is stale.
  // FigureCard probes via fetch(HEAD) and calls onStale to drop the
  // cache entry, which collapses the grid back to its empty hint
  // (the 410 won't recur because the user must click [AI 处理] to
  // re-fetch with the new cache_version).
  const handleStale = () => {
    queryClient.removeQueries({ queryKey: ["report-bundle", caseId] });
  };

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
  // Codex round-7 P3 (2026-04-30): the backend auto-picks non-x-y
  // planes (e.g. x-z for NACA-like meshes), but the previous
  // captions hard-coded U_x/U_y/x/y. Drive captions from
  // data.plane_axes so the right rail matches the rendered plot
  // titles regardless of which plane was picked.
  const [a0, a1] = data.plane_axes;
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
          onStale={handleStale}
        />
        <FigureCard
          title="gauge pressure"
          caption="p / ρ · diverging colormap"
          url={data.artifacts.pressure}
          onStale={handleStale}
        />
        <FigureCard
          title="vorticity"
          caption={`∂U${a1}/∂${a0} − ∂U${a0}/∂${a1}`}
          url={data.artifacts.vorticity}
          onStale={handleStale}
        />
        <FigureCard
          title="centreline profiles"
          caption={`U_${a0}(${a1}) · U_${a1}(${a0}) at midlines`}
          url={data.artifacts.centerline}
          onStale={handleStale}
        />
      </div>
    </div>
  );
}
