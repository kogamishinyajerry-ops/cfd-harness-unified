// Bottom strip · log tail + last-action + validation status.

interface StatusStripProps {
  /** One-line log tail or last-action message; null hides the strip
   *  body but keeps the rail height stable. */
  lastAction?: string | null;
  /** Validation summary surfaced from the active step (e.g. "ready",
   *  "needs mesh", "1 BC unmet"). */
  validation?: string | null;
}

export function StatusStrip({
  lastAction = null,
  validation = null,
}: StatusStripProps) {
  return (
    <footer
      data-testid="status-strip"
      className="flex items-center justify-between border-t border-surface-800 bg-surface-950/80 px-3 py-1.5 text-[11px] text-surface-500"
    >
      <span data-testid="status-strip-last-action" className="truncate">
        {lastAction ?? "—"}
      </span>
      {validation !== null && (
        <span data-testid="status-strip-validation" className="text-surface-400">
          {validation}
        </span>
      )}
    </footer>
  );
}
