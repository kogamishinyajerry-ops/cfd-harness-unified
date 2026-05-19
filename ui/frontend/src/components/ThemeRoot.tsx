/**
 * V70.4 · ThemeRoot · V70-UI-IMPROVEMENT-C
 *
 * Industrial-UI benchmark Axis 6 (Dark Mode / Theme) substrate. Sets
 * `data-theme="dark"` on document body so future light-mode toggle (V71)
 * can swap themes without ripping through Tailwind config — token names
 * reference `data-theme` selectors per Tailwind v4 forward-compat pattern.
 *
 * Currently constant (dark default); the architectural hook is the lift.
 */
import { useEffect } from "react";

export function ThemeRoot() {
  useEffect(() => {
    const body = document.body;
    body.setAttribute("data-theme", "dark");
    body.setAttribute("data-v70-ui-improvement", "C");
    return () => {
      body.removeAttribute("data-theme");
      body.removeAttribute("data-v70-ui-improvement");
    };
  }, []);

  return null;
}
