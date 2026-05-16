// V75.2 · Skeleton placeholders that hold layout shape during async fetch.
//
// Replaces "Loading…" text shimmies on 4 v3 surfaces:
//   - skeleton-advisor       advisor consult button area
//   - skeleton-inspector     right-panel inspector
//   - skeleton-truthchain    TruthChain provenance + delta surface
//   - skeleton-multi-case    Step-5 multi-case ribbon
//
// Linear/Notion/STAR-CCM+ DNA — perceived latency improves dramatically
// when the layout doesn't shift on fetch settle.
//
// Visual: low-opacity rounded bars with motion-safe pulse. Respects
// prefers-reduced-motion (the pulse stops, the bars remain).

import type { ReactNode } from "react";

function Bar({ w, h = 12, className = "" }: { w: string; h?: number; className?: string }) {
  return (
    <div
      aria-hidden
      style={{ width: w, height: h }}
      className={`bg-v3-surface2 rounded motion-safe:animate-pulse ${className}`}
    />
  );
}

function SkeletonRow({ children }: { children: ReactNode }) {
  return <div className="flex items-center justify-between gap-2">{children}</div>;
}

export function SkeletonAdvisor() {
  return (
    <div
      data-testid="skeleton-advisor"
      data-source="skeleton"
      className="space-y-3 px-1"
    >
      <Bar w="40%" h={10} />
      <Bar w="100%" h={32} />
      <Bar w="80%" h={10} />
      <Bar w="60%" h={10} />
    </div>
  );
}

export function SkeletonInspector() {
  return (
    <div
      data-testid="skeleton-inspector"
      data-source="skeleton"
      className="space-y-4 px-1"
    >
      <Bar w="35%" h={10} />
      <div className="space-y-2">
        <SkeletonRow>
          <Bar w="30%" h={10} />
          <Bar w="40%" h={10} />
        </SkeletonRow>
        <SkeletonRow>
          <Bar w="30%" h={10} />
          <Bar w="50%" h={10} />
        </SkeletonRow>
        <SkeletonRow>
          <Bar w="30%" h={10} />
          <Bar w="35%" h={10} />
        </SkeletonRow>
      </div>
    </div>
  );
}

export function SkeletonTruthChain() {
  return (
    <div
      data-testid="skeleton-truthchain"
      data-source="skeleton"
      className="space-y-4 px-1"
    >
      <Bar w="30%" h={10} />
      <Bar w="100%" h={28} />
      <div className="space-y-1.5">
        <Bar w="100%" h={24} />
        <Bar w="100%" h={24} />
        <Bar w="100%" h={24} />
        <Bar w="100%" h={24} />
      </div>
    </div>
  );
}

export function SkeletonMultiCase() {
  return (
    <div
      data-testid="skeleton-multi-case"
      data-source="skeleton"
      className="border-t border-v3-border bg-v3-bg px-4 py-2 space-y-2"
    >
      <Bar w="35%" h={10} />
      <div className="flex gap-2">
        <Bar w="20%" h={58} />
        <Bar w="20%" h={58} />
        <Bar w="20%" h={58} />
        <Bar w="20%" h={58} />
        <Bar w="20%" h={58} />
      </div>
    </div>
  );
}
