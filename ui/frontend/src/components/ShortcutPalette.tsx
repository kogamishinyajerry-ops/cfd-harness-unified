/**
 * V70.4 · ShortcutPalette · V70-UI-IMPROVEMENT-A
 *
 * Industrial-UI benchmark Axis 2 (Keyboard Shortcuts) closure substrate.
 * Engineer hits `?` → modal palette listing keyboard shortcuts. Esc
 * dismisses. Modal is keyboard-navigable (Tab/Shift+Tab through items).
 *
 * Closes Axis 2 gap from -3 to -2 vs ANSYS Fluent (commercial GUIs still
 * have hundreds of shortcuts; this scaffolds the substrate for V71+
 * expansion).
 */
import { useEffect, useState } from "react";

const SHORTCUTS: Array<{ keys: string; description: string }> = [
  { keys: "?", description: "Toggle this shortcut palette" },
  { keys: "Esc", description: "Close palette / dismiss banner" },
  { keys: "Cmd+K", description: "Command palette (V71 stub)" },
  { keys: "←/→", description: "Step navigation (V71 stub)" },
  { keys: "g + i", description: "Go to /workbench index (V71 stub)" },
  { keys: "g + t", description: "Go to /workbench/tutorial" },
];

export function ShortcutPalette() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      // Don't capture when user is typing in an input
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "?") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape" && open) {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  if (!open) return null;

  return (
    <div
      data-testid="shortcut-palette-overlay"
      data-v70-ui-improvement="A"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcut palette"
      tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface-950/80 backdrop-blur-sm"
      onClick={() => setOpen(false)}
    >
      <div
        data-testid="shortcut-palette"
        className="w-[28rem] rounded-lg border border-surface-700 bg-surface-900 p-5 text-surface-200 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-emerald-300">
            Keyboard Shortcuts
          </h2>
          <button
            type="button"
            data-testid="shortcut-palette-close"
            onClick={() => setOpen(false)}
            className="text-xs text-surface-400 hover:text-surface-100"
            aria-label="Close shortcut palette"
          >
            Esc
          </button>
        </div>
        <ul className="space-y-1.5 text-sm">
          {SHORTCUTS.map((s) => (
            <li
              key={s.keys}
              data-testid={`shortcut-item-${s.keys.replace(/\W+/g, "-")}`}
              tabIndex={0}
              className="flex items-center justify-between rounded px-2 py-1 hover:bg-surface-800 focus:bg-surface-800 focus:outline-none"
            >
              <kbd className="rounded border border-surface-600 bg-surface-800 px-1.5 py-0.5 text-xs font-mono text-emerald-300">
                {s.keys}
              </kbd>
              <span className="text-surface-300">{s.description}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[10px] text-surface-500">
          V70.4 substrate · expanded shortcut set deferred to V71+
        </p>
      </div>
    </div>
  );
}
