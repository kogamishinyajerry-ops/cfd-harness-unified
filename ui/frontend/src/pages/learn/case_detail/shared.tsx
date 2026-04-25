// Tiny shared helpers used across LearnCaseDetailPage tabs.
// Extracted 2026-04-25 from LearnCaseDetailPage.tsx (Stage 1 shell-split,
// per Codex industrial-workbench meeting verdict). Behavior unchanged.

// --- formatNumber utility -----------------------------------------------------
export function formatNumber(v: number | undefined | null): string {
  if (v == null || !Number.isFinite(v)) return "—";
  const abs = Math.abs(v);
  if (abs === 0) return "0";
  if (abs < 0.001) return v.toExponential(2);
  if (abs < 1) return v.toFixed(4);
  if (abs < 100) return v.toFixed(3);
  return v.toFixed(1);
}

// --- callouts -----------------------------------------------------------------
export function ErrorCallout({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-contract-fail/40 bg-contract-fail/10 p-4 text-[13px] text-contract-fail">
      {message}
    </div>
  );
}

export function SkeletonCallout({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/30 p-4 text-[13px] text-surface-400">
      {message}
    </div>
  );
}
