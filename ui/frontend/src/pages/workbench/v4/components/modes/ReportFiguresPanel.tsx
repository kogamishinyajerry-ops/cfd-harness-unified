// DEC-V61-204 · M4 cycle 3 · V4 Post report-bundle figures.
//
// Surfaces the backend matplotlib figure bundle (contour-streamlines /
// pressure / vorticity / centerline) inside the V4 Post right column as
// canonical, provenance-labelled artifacts. Mirrors the retired V3
// Step5ResultsGrid (img cards + 410-stale probe) but:
//   - auto-fetches (no AI-run button; advisor-not-driver UI)
//   - lays out a single narrow column (288px right rail) not a 2×2 grid
//   - classifies error states for graceful fallback (charter requirement):
//       409                → "no run yet" (run the solver first)
//       500 + "matplotlib" → "report unavailable on this build"
//       503                → results service unavailable
//       other              → generic error — NEVER a crash.

import { useEffect, useState } from "react";

import { useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import { useReportBundle } from "../../hooks/useReportBundle";

interface ReportFiguresPanelProps {
  caseId: string | null | undefined;
}

interface FigureSpec {
  name: keyof import("@/types/case_solve").ReportBundle["artifacts"];
  title: string;
  caption: string;
}

// Codex R0 [P2]: vorticity + centerline captions are plane-dependent. The
// backend auto-picks the slab plane and returns plane_axes (x-y / x-z / y-z);
// hardcoding "∂v/∂x − ∂u/∂y" is scientifically wrong on non-x/y geometries.
// Derive them from plane_axes like the retired V3 grid did.
function figuresFor(planeAxes: readonly string[]): readonly FigureSpec[] {
  const [a0 = "x", a1 = "y"] = planeAxes;
  return [
    { name: "contour_streamlines", title: "|U| + 流线", caption: "velocity · streamplot" },
    { name: "pressure", title: "压力 (gauge)", caption: "p/ρ · diverging" },
    { name: "vorticity", title: "涡量", caption: `∂U${a1}/∂${a0} − ∂U${a0}/∂${a1}` },
    { name: "centerline", title: "中线剖面", caption: `U_${a0}(${a1}) · U_${a1}(${a0})` },
  ];
}

/** Shared narrow card frame for the right-rail states. */
function StateCard({
  testid,
  tone,
  children,
}: {
  testid: string;
  tone: "muted" | "warn" | "crit";
  children: React.ReactNode;
}) {
  const toneClass =
    tone === "crit"
      ? "border-v4-crit/40 bg-v4-crit/5 text-rose-200"
      : tone === "warn"
        ? "border-v4-warn/40 bg-v4-warn/5 text-amber-100"
        : "border-dashed border-v4-border bg-v4-canvas text-v4-textTertiary";
  return (
    <div
      data-testid={testid}
      className={`rounded border ${toneClass} p-2.5 text-[10px] leading-relaxed`}
    >
      {children}
    </div>
  );
}

function FigureCard({
  name,
  title,
  caption,
  url,
  onStale,
}: FigureSpec & { url: string; onStale: () => void }) {
  // The /report/{name}.png route can 410 if the case was re-solved
  // between the bundle metadata fetch and this image fetch. <img onError>
  // hides the status, so probe via fetch(HEAD); on 410 ask the panel to
  // refetch the bundle (new cache_version). (Mirrors V3.)
  const [staleHit, setStaleHit] = useState(false);
  // Codex R0 [P2]: when the refetched bundle delivers a fresh url, clear
  // the stale placeholder so the card shows the new figure instead of
  // staying stuck on "将自动刷新".
  useEffect(() => {
    setStaleHit(false);
  }, [url]);

  if (staleHit) {
    return (
      <figure
        data-testid={`v4-report-fig-${name}`}
        data-stale="true"
        className="rounded border border-v4-warn/40 bg-v4-warn/5 p-2 text-[10px] text-amber-100"
      >
        <figcaption className="font-mono uppercase tracking-wider">{title}</figcaption>
        <p className="mt-1">图已过期（算例已重新求解）· 将自动刷新</p>
      </figure>
    );
  }

  return (
    <figure
      data-testid={`v4-report-fig-${name}`}
      className="flex flex-col overflow-hidden rounded border border-v4-border bg-v4-canvas"
    >
      <figcaption className="flex items-baseline justify-between border-b border-v4-border px-2 py-1 text-[9px]">
        <span className="font-mono uppercase tracking-wider text-v4-textSecondary">
          {title}
        </span>
        <span className="text-v4-textTertiary">{caption}</span>
      </figcaption>
      <a href={url} target="_blank" rel="noreferrer" className="flex items-center justify-center p-1.5">
        <img
          src={url}
          alt={title}
          loading="lazy"
          className="max-h-[150px] w-full object-contain"
          onError={() => {
            fetch(url, { method: "HEAD" })
              .then((resp) => {
                if (resp.status === 410) {
                  setStaleHit(true);
                  onStale();
                }
              })
              .catch(() => {
                /* network error — leave broken-image state, no crash */
              });
          }}
        />
      </a>
    </figure>
  );
}

export function ReportFiguresPanel({ caseId }: ReportFiguresPanelProps) {
  const { data, isLoading, error } = useReportBundle(caseId);
  const qc = useQueryClient();
  // Codex R0 [P2]: invalidate (not remove) so the active useReportBundle
  // observer refetches the bundle with the post-re-solve cache_version.
  // removeQueries() in TanStack Query v5 only drops the cache; it does not
  // trigger a refetch for a mounted observer, leaving the card stuck stale.
  const handleStale = () => {
    if (caseId) qc.invalidateQueries({ queryKey: ["v4-report-bundle", caseId] });
  };

  if (!caseId) return null;

  if (isLoading) {
    return (
      <StateCard testid="v4-report-loading" tone="muted">
        结果图渲染中… / rendering report figures…
      </StateCard>
    );
  }

  if (error) {
    const status = error instanceof ApiError ? error.status : null;
    const msg = error.message;

    // 409 — solver hasn't produced results yet. Friendly empty state.
    if (status === 409) {
      return (
        <StateCard testid="v4-report-empty" tone="muted">
          结果图：先在求解步运行求解器，完成后这里会显示后端报告图。
        </StateCard>
      );
    }
    // matplotlib absent on this build (500 + "matplotlib is required").
    // Charter fallback: explicit "unavailable on this build" — not a crash.
    if (status === 500 && /matplotlib/i.test(msg)) {
      return (
        <StateCard testid="v4-report-unavailable" tone="warn">
          报告图在此构建不可用（未安装 matplotlib）。数值结果与残差仍在上方可用。
        </StateCard>
      );
    }
    if (status === 503) {
      return (
        <StateCard testid="v4-report-error" tone="crit">
          结果服务不可用 (503)。
        </StateCard>
      );
    }
    return (
      <StateCard testid="v4-report-error" tone="crit">
        报告图错误{status ? ` (HTTP ${status})` : ""}: {msg}
      </StateCard>
    );
  }

  if (!data) return null;

  const cells = data.cell_count.toLocaleString();
  const version = data.cache_version.slice(0, 8);
  const figures = figuresFor(data.plane_axes);

  return (
    <div data-testid="v4-report-figures" className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between text-[9px]">
        <span className="font-mono uppercase tracking-wider text-v4-textSecondary">
          报告图 / Report figures
        </span>
        <span
          className="font-mono text-v4-textTertiary"
          title={`cache_version=${data.cache_version}`}
        >
          v{version}
        </span>
      </div>
      {/* Provenance line — canonical backend artifacts (four-question gate). */}
      <div className="font-mono text-[9px] text-v4-textTertiary">
        t={data.final_time}s · {cells} cells · {data.case_kind}
      </div>
      {figures.map((fig) => (
        <FigureCard
          key={fig.name}
          {...fig}
          url={data.artifacts[fig.name]}
          onStale={handleStale}
        />
      ))}
    </div>
  );
}
