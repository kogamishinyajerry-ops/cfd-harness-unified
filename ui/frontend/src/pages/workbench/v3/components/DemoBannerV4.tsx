/**
 * V80.2 · DemoBannerV4 · opt-in demo tour banner + first-time hint.
 *
 * Activated by `?demo=1` URL query OR via the first-time hint chip.
 * Reverse-stops:
 *   - opt-in only · no auto-popup modal · no scroll lock (V80 reverse-stop §6.8)
 *   - dismissable permanently via localStorage (V4.A contract)
 *   - tour does NOT auto-execute solver or any mutating action (V130/V132)
 *
 * 6 narrative steps (V4 §1 timeline 0s..30s):
 *   step=1 · "Welcome · 30-second tour of AI-assisted CFD workbench"
 *   step=2 · "Step 1 Import · case geometry loaded · watertight verified"
 *   step=3 · "Step 2 Mesh · quality table · AI advisor flags cells"
 *   step=4 · "Step 3 Physics · color-coded BC patches · materials"
 *   step=5 · "Step 4 Solver · real-time SSE residual streaming · live convergence"
 *   step=6 · "Step 5 Postprocess · Ghia 1982 comparison · TrustGate verdict"
 */

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

// V83.4 · V5.C cinematic mode
const CINEMA_BEAT_MS = 12_000; // 60s / 5 beats (welcome carries the 1st)

const STORAGE_KEY = "v80-demo-banner-dismissed";
const TOUR_STEPS = [
  {
    id: 1,
    title: "Welcome",
    body: "30-second tour of AI-assisted CFD workbench · LLM offline · AI advises, you drive",
    expected_step: null,
  },
  {
    id: 2,
    title: "Step 1 · Import",
    body: "Case geometry loaded · Inspector shows watertight check + bbox",
    expected_step: 1,
  },
  {
    id: 3,
    title: "Step 2 · Mesh",
    body: "Mesh quality table on the right · AI advisor flags high-skewness cells",
    expected_step: 2,
  },
  {
    id: 4,
    title: "Step 3 · Physics",
    body: "Color-coded BC patches · INLET green · WALL red · SYMMETRY amber",
    expected_step: 3,
  },
  {
    id: 5,
    title: "Step 4 · Solver",
    body: "Real-time SSE residual streaming · live convergence · SolverStateBadge flips when done",
    expected_step: 4,
  },
  {
    id: 6,
    title: "Step 5 · Postprocess",
    body: "Gold reference comparison (Ghia 1982) · TrustGate verdict · audit-package downloadable",
    expected_step: 5,
  },
] as const;

export function DemoBannerV4() {
  const [searchParams, setSearchParams] = useSearchParams();
  const demoActive = searchParams.get("demo") === "1";
  const tourStep = Number(searchParams.get("tour")) || 0;
  // V83.4 · V5.C cinematic mode opt-in via ?demo=1&cinema=1
  const cinemaActive = demoActive && searchParams.get("cinema") === "1";

  const [dismissed, setDismissed] = useState<boolean>(false);
  const [mounted, setMounted] = useState<boolean>(false);
  // V83.4 · pause/resume state — only relevant when cinematic is active.
  // Default to playing on cinematic activation; user can pause anytime.
  const [paused, setPaused] = useState<boolean>(false);
  // V83.4 · prefers-reduced-motion respect — if user has reduced-motion
  // preference, auto-advance is disabled entirely (per V83 charter §5
  // reverse-stop #11).
  const [reducedMotion, setReducedMotion] = useState<boolean>(false);
  // V83.4 · ref to latest auto-advance handler so the timer effect can call
  // it without capturing stale closures. Allocated unconditionally to keep
  // hook order stable across all render branches.
  const handleNextRef = useRef<() => void>(() => {});

  useEffect(() => {
    setMounted(true);
    if (typeof window !== "undefined") {
      setDismissed(window.localStorage.getItem(STORAGE_KEY) === "1");
      // Detect prefers-reduced-motion · default to false if matchMedia
      // unavailable (older browsers · jsdom).
      try {
        const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
        setReducedMotion(mq.matches);
        const onChange = (e: MediaQueryListEvent) =>
          setReducedMotion(e.matches);
        // Newer browsers use addEventListener; older Safari needs addListener.
        if (mq.addEventListener) mq.addEventListener("change", onChange);
        return () => {
          if (mq.removeEventListener) mq.removeEventListener("change", onChange);
        };
      } catch {
        /* matchMedia unavailable · keep reducedMotion=false */
      }
    }
  }, []);

  // V83.4 · auto-advance timer (unconditionally registered to keep hook
  // order stable across render branches; the effect body itself guards on
  // cinemaActive + paused + reducedMotion + isLast).
  const safeStepForTimer = Math.max(1, Math.min(TOUR_STEPS.length, tourStep));
  const isLastForTimer = safeStepForTimer === TOUR_STEPS.length;
  useEffect(() => {
    if (!cinemaActive || paused || reducedMotion) return;
    if (isLastForTimer) return;
    const id = setTimeout(() => handleNextRef.current(), CINEMA_BEAT_MS);
    return () => clearTimeout(id);
  }, [cinemaActive, paused, reducedMotion, isLastForTimer, safeStepForTimer]);

  if (!mounted) return null;

  // Permanent dismissal beats everything except an explicit ?demo=1 nav
  if (dismissed && !demoActive) return null;

  // Cold state: show the tiny first-time hint chip (Contract V4.D)
  if (!demoActive) {
    return (
      <div
        data-testid="first-time-hint"
        className="absolute top-1 right-3 z-20 flex items-center gap-2 text-[10px] font-mono text-v3-textTertiary"
      >
        <span>New here?</span>
        <button
          type="button"
          data-testid="first-time-hint-start"
          onClick={() => {
            const next = new URLSearchParams(searchParams);
            next.set("demo", "1");
            next.set("tour", "1");
            setSearchParams(next, { replace: true });
          }}
          className="underline decoration-v3-accent decoration-1 underline-offset-2 hover:text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        >
          30s tour
        </button>
        <button
          type="button"
          data-testid="first-time-hint-dismiss"
          onClick={() => {
            if (typeof window !== "undefined") {
              window.localStorage.setItem(STORAGE_KEY, "1");
            }
            setDismissed(true);
          }}
          aria-label="Dismiss first-time hint"
          className="text-v3-textTertiary hover:text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        >
          ×
        </button>
      </div>
    );
  }

  // Active demo: full banner with step progression
  const safeStep = safeStepForTimer;
  const step = TOUR_STEPS[safeStep - 1];
  const isLast = isLastForTimer;

  const handleNext = () => {
    const next = new URLSearchParams(searchParams);
    if (isLast) {
      next.delete("demo");
      next.delete("tour");
    } else {
      next.set("tour", String(safeStep + 1));
      // Auto-advance the workbench step to match the tour beat when
      // expected_step is defined (V4 §1 timeline keeps tour + pipeline
      // step synchronized).
      const nextStep = TOUR_STEPS[safeStep]?.expected_step;
      if (nextStep) {
        next.set("step", String(nextStep));
      }
    }
    setSearchParams(next, { replace: true });
  };

  const handleSkip = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("demo");
    next.delete("tour");
    next.delete("cinema");
    setSearchParams(next, { replace: true });
  };

  // V83.4 · cinematic controls
  const handleCinemaBack = () => {
    if (safeStep <= 1) return;
    const next = new URLSearchParams(searchParams);
    next.set("tour", String(safeStep - 1));
    const prevExpectedStep = TOUR_STEPS[safeStep - 2]?.expected_step;
    if (prevExpectedStep) next.set("step", String(prevExpectedStep));
    setSearchParams(next, { replace: true });
  };
  const handleCinemaTogglePause = () => setPaused((v) => !v);
  const handleCinemaExit = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("cinema");
    setSearchParams(next, { replace: true });
  };

  // Keep the timer's reference pointed at the latest handler (handleNext
  // captures current tourStep / searchParams via closure). Effect-level
  // setTimeout (declared at top of component) will invoke .current() when
  // it fires.
  handleNextRef.current = handleNext;

  return (
    <div
      data-testid="demo-banner"
      data-tour-step={String(safeStep)}
      data-cinema={cinemaActive ? "active" : "inactive"}
      data-cinema-paused={paused ? "true" : "false"}
      data-reduced-motion={reducedMotion ? "true" : "false"}
      role="region"
      aria-label="Demo tour banner"
      className="relative z-10 flex items-center justify-between gap-4 border-b border-v3-accent/40 bg-v3-bgRaised/30 px-4 py-2 text-[12px]"
    >
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-[10px] font-mono uppercase tracking-[0.08em] text-v3-textTertiary">
          Tour · step {safeStep}/{TOUR_STEPS.length}
        </span>
        <span className="font-medium text-v3-textPrimary truncate">
          {step.title}
        </span>
        <span className="text-v3-textSecondary truncate">{step.body}</span>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        {cinemaActive && (
          <span
            data-testid="cinematic-mode-active"
            className="text-[10px] font-mono uppercase tracking-[0.08em] text-v3-textTertiary border border-v3-border rounded px-1.5 py-0.5"
          >
            cinematic {reducedMotion ? "· manual (reduced-motion)" : ""}
          </span>
        )}
        {cinemaActive && !reducedMotion && (
          <>
            <button
              type="button"
              data-testid="cinematic-back"
              onClick={handleCinemaBack}
              disabled={safeStep <= 1}
              className="text-[11px] text-v3-textTertiary underline decoration-1 underline-offset-2 hover:text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus disabled:opacity-40"
              aria-label="Back to previous tour beat"
            >
              ← back
            </button>
            <button
              type="button"
              data-testid={paused ? "cinematic-resume" : "cinematic-pause"}
              onClick={handleCinemaTogglePause}
              className="text-[11px] text-v3-textTertiary underline decoration-1 underline-offset-2 hover:text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus"
              aria-label={paused ? "Resume auto-advance" : "Pause auto-advance"}
            >
              {paused ? "▶ resume" : "⏸ pause"}
            </button>
            <button
              type="button"
              data-testid="cinematic-exit"
              onClick={handleCinemaExit}
              className="text-[11px] text-v3-textTertiary underline decoration-1 underline-offset-2 hover:text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus"
              aria-label="Exit cinematic mode (manual advance continues)"
            >
              × cinema
            </button>
          </>
        )}
        <button
          type="button"
          data-testid="demo-banner-skip"
          onClick={handleSkip}
          className="text-[11px] text-v3-textTertiary underline decoration-1 underline-offset-2 hover:text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        >
          Skip tour
        </button>
        <button
          type="button"
          data-testid="demo-banner-next"
          onClick={handleNext}
          className="text-[12px] font-mono text-v3-textPrimary underline decoration-v3-accent decoration-1 underline-offset-2 hover:text-v3-accent focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        >
          {isLast ? "Finish ›" : "Next ›"}
        </button>
      </div>
      {/* V83.4 · cinematic progress indicator · sand-coral line · 0-100%
          across CINEMA_BEAT_MS · disabled when paused or reduced-motion */}
      {cinemaActive && !reducedMotion && !paused && !isLast && (
        <div
          data-testid="cinematic-progress"
          aria-hidden="true"
          key={safeStep}
          className="absolute bottom-0 left-0 h-px bg-v3-accent"
          style={{
            width: "100%",
            transformOrigin: "left center",
            animation: `v83-cinematic-progress ${CINEMA_BEAT_MS}ms linear forwards`,
          }}
        />
      )}
    </div>
  );
}
