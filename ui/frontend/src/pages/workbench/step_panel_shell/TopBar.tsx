// Top bar · case identity, save indicator, close.

interface TopBarProps {
  caseId: string;
  saveIndicator?: "idle" | "saving" | "saved" | "error";
}

const INDICATOR_LABEL: Record<NonNullable<TopBarProps["saveIndicator"]>, string> = {
  idle: "ready",
  saving: "saving…",
  saved: "saved",
  error: "save failed",
};

const INDICATOR_TONE: Record<NonNullable<TopBarProps["saveIndicator"]>, string> = {
  idle: "text-surface-500",
  saving: "text-emerald-300",
  saved: "text-emerald-400",
  error: "text-rose-300",
};

export function TopBar({ caseId, saveIndicator = "idle" }: TopBarProps) {
  return (
    <header
      data-testid="top-bar"
      className="flex items-center justify-between border-b border-surface-800 bg-surface-950/80 px-3 py-2"
    >
      <div className="flex items-baseline gap-2">
        <span className="text-[10px] font-mono uppercase tracking-wider text-surface-500">
          Workbench
        </span>
        <h1
          className="font-mono text-sm text-surface-100"
          data-testid="top-bar-case-id"
        >
          {caseId}
        </h1>
      </div>
      <div className="flex items-center gap-3 text-[11px] text-surface-500">
        <span
          data-testid="save-indicator"
          data-state={saveIndicator}
          className={INDICATOR_TONE[saveIndicator]}
        >
          {INDICATOR_LABEL[saveIndicator]}
        </span>
      </div>
    </header>
  );
}
