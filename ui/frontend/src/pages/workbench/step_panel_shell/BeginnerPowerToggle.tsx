// BeginnerPowerToggle · UI surface for V67-C.3 (Engineer Control Rail)
//
// Compact 2-state pill renderer. Designed to live in TaskPanel header,
// TopBar, or anywhere visual real-estate is tight. Reads/writes via
// useBeginnerPower().

import { useBeginnerPowerOptional } from "./BeginnerPowerContext";

interface BeginnerPowerToggleProps {
  /** Visual size · "sm" 默认 / "xs" 紧凑场景 */
  size?: "sm" | "xs";
  /** Optional class merge */
  className?: string;
}

export function BeginnerPowerToggle({
  size = "sm",
  className = "",
}: BeginnerPowerToggleProps) {
  // Use optional hook so existing tests / pages that don't wrap in Provider
  // still render the host component (TaskPanel) without crashing. When no
  // provider is present we render a disabled placeholder showing "Beginner".
  const ctx = useBeginnerPowerOptional();
  const mode = ctx?.mode ?? "beginner";
  const setMode = ctx?.setMode;

  const padding = size === "xs" ? "px-1 py-0.5" : "px-1.5 py-1";
  const text = size === "xs" ? "text-[9px]" : "text-[10px]";

  return (
    <div
      data-testid="beginner-power-toggle"
      data-mode={mode}
      role="group"
      aria-label="Engineer mode"
      className={`inline-flex items-center rounded-md border border-surface-700 bg-surface-900/60 font-mono uppercase tracking-wider ${text} ${className}`}
    >
      <button
        type="button"
        data-testid="beginner-power-toggle-beginner"
        aria-pressed={mode === "beginner"}
        disabled={!setMode}
        onClick={() => setMode?.("beginner")}
        className={`${padding} rounded-l-md transition-colors ${
          mode === "beginner"
            ? "bg-emerald-700/40 text-emerald-200"
            : "text-surface-500 hover:text-surface-300"
        }`}
      >
        Beginner
      </button>
      <span className="w-px self-stretch bg-surface-700" />
      <button
        type="button"
        data-testid="beginner-power-toggle-power"
        aria-pressed={mode === "power"}
        disabled={!setMode}
        onClick={() => setMode?.("power")}
        className={`${padding} rounded-r-md transition-colors ${
          mode === "power"
            ? "bg-sky-700/40 text-sky-200"
            : "text-surface-500 hover:text-surface-300"
        }`}
      >
        Power
      </button>
    </div>
  );
}
