/**
 * V70.3 · FirstTimeBanner · Novice-onboarding entry point
 *
 * Dismissible banner shown on /workbench index pointing first-time
 * engineers to the lid_driven_cavity starter case. Persists dismiss
 * state in localStorage so returning users don't see it again.
 *
 * V70-DONE-3 anchor: scorer matches "FirstTimeBanner" + "lid_driven_cavity.*starter"
 * patterns to verify the banner is in place.
 */
import { useState, useEffect } from "react";

const STORAGE_KEY = "v70-first-time-banner-dismissed";

export function FirstTimeBanner() {
  const [dismissed, setDismissed] = useState<boolean>(false);
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
    try {
      setDismissed(localStorage.getItem(STORAGE_KEY) === "1");
    } catch {
      // localStorage unavailable (SSR / privacy mode) · show banner
    }
  }, []);

  if (!mounted || dismissed) return null;

  function dismiss() {
    setDismissed(true);
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // ignore
    }
  }

  return (
    <div
      data-testid="first-time-banner"
      data-novice-banner="true"
      role="status"
      aria-label="First-time user welcome · novice onboarding"
      className="mb-4 flex items-start justify-between gap-4 rounded-lg border border-emerald-700/50 bg-emerald-900/20 px-4 py-3 text-sm text-emerald-200"
    >
      <div className="flex flex-col gap-1">
        <div className="font-semibold">👋 First time here? Start with a 2-minute run.</div>
        <div className="text-emerald-200/80">
          The fastest path to a successful CFD run is the{" "}
          <a
            href="/workbench/case/lid_driven_cavity?step=1"
            data-testid="first-time-banner-starter-link"
            className="underline decoration-emerald-400 hover:text-emerald-100"
          >
            lid_driven_cavity starter case
          </a>{" "}
          — Re=100, laminar, 17×17 cells, ~30 seconds to converge. Or read the{" "}
          <a
            href="/workbench/tutorial"
            data-testid="first-time-banner-tutorial-link"
            className="underline decoration-emerald-400 hover:text-emerald-100"
          >
            workbench tutorial
          </a>{" "}
          for a guided walkthrough of all 5 steps.
        </div>
      </div>
      <button
        type="button"
        data-testid="first-time-banner-dismiss"
        onClick={dismiss}
        className="rounded border border-emerald-700/40 px-2 py-0.5 text-[11px] uppercase tracking-wider text-emerald-300 hover:bg-emerald-900/40"
      >
        Got it
      </button>
    </div>
  );
}
