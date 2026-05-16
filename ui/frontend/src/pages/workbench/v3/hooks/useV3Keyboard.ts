/**
 * V72.2 · useV3Keyboard · global keyboard shortcuts for the v3 shell
 *
 * Bindings:
 *   - ⌘K / Ctrl-K · open shortcut palette (existing global ShortcutPalette)
 *   - 1..5         · jump to pipeline step N (only when no input focused)
 *   - g            · viewport mode geometry
 *   - m            · viewport mode mesh
 *   - b            · viewport mode bc
 *   - r            · viewport mode residuals
 *   - p            · viewport mode report
 *   - f            · viewport mode field
 *   - [            · prev right-panel tab
 *   - ]            · next right-panel tab
 *   - Esc          · close overlays / collapse bottom panel
 *   - ?            · open shortcut palette (existing behavior)
 *
 * The hook skips key handling when the target element is an editable surface
 * (<input>, <textarea>, contentEditable) so engineers can type freely in
 * future form fields without triggering shortcuts.
 */
import { useEffect } from "react";
import type {
  StepId,
  ViewportMode,
  RightPanelTab,
} from "../WorkbenchShellV3";

interface UseV3KeyboardArgs {
  onSetStep: (s: StepId) => void;
  onSetViewport: (m: ViewportMode) => void;
  onSetRightTab: (t: RightPanelTab) => void;
  onEscape: () => void;
  currentTab: RightPanelTab;
}

const VIEWPORT_KEYS: Record<string, ViewportMode> = {
  g: "geometry",
  m: "mesh",
  b: "bc",
  r: "residuals",
  p: "report",
  f: "field",
};

const TAB_ORDER: RightPanelTab[] = ["inspector", "advisor", "truthchain"];

function isEditableTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (el.isContentEditable) return true;
  // role="textbox" / role="combobox" are also editable
  const role = el.getAttribute("role");
  if (role === "textbox" || role === "combobox" || role === "searchbox") {
    return true;
  }
  return false;
}

export function useV3Keyboard({
  onSetStep,
  onSetViewport,
  onSetRightTab,
  onEscape,
  currentTab,
}: UseV3KeyboardArgs) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      // Don't hijack typing
      if (isEditableTarget(e.target)) return;

      // Modifier-bearing shortcuts
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        // ShortcutPalette handles this globally · don't double-fire
        return;
      }

      // Esc · close overlays
      if (e.key === "Escape") {
        onEscape();
        return;
      }

      // Don't act on other modifier-bearing keys
      if (e.altKey || e.metaKey || e.ctrlKey) return;

      // Number 1..5 → step
      if (/^[1-5]$/.test(e.key)) {
        e.preventDefault();
        onSetStep(Number(e.key) as StepId);
        return;
      }

      // Letter → viewport mode
      const vp = VIEWPORT_KEYS[e.key.toLowerCase()];
      if (vp) {
        e.preventDefault();
        onSetViewport(vp);
        return;
      }

      // Bracket → right-panel tab cycle
      if (e.key === "[" || e.key === "]") {
        e.preventDefault();
        const idx = TAB_ORDER.indexOf(currentTab);
        const next =
          e.key === "]"
            ? TAB_ORDER[(idx + 1) % TAB_ORDER.length]
            : TAB_ORDER[(idx - 1 + TAB_ORDER.length) % TAB_ORDER.length];
        onSetRightTab(next);
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onSetStep, onSetViewport, onSetRightTab, onEscape, currentTab]);
}
