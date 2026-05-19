/**
 * V83.2 · DemoSandboxV5 · V5.A contract · interactive click-through demo
 *
 * Per .planning/blueprints/v5/INDEX.md Contract V5.A:
 *   - `?demo=2` activates sandbox mode
 *   - Status pill in top-right: "SANDBOX MODE · curated state · no real solver"
 *   - Step-transition banner appears for 1s then fades when stepId changes
 *   - Exit link clears the demo query param
 *   - NO mutating backend call · NO runtime LLM call · LLM-offline 4Q gate
 *
 * V83 reverse-stops:
 *   #11 cinematic auto-advance must be cancellable — N/A (this is sandbox, not cinematic)
 *   #12 sandbox MUST NOT call mutating backend endpoints — enforced structurally
 *                                                          (no fetch/POST in component)
 *
 * V130/V132 invariants:
 *   - Component is pure render from URL state · no side-effects beyond URL writes
 *   - Step transitions go through existing pipeline strip (which is read-only)
 *   - Status pill is a label, not a control
 */

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { StepId } from "../WorkbenchShellV3";
import {
  getSandboxStepState,
  SANDBOX_CURATED_CASES,
} from "@/data/sandbox_step_states";
import {
  getBridgeStepState,
  type BridgeArtifact,
} from "@/data/run_artifact_reader";

interface DemoSandboxV5Props {
  stepId: StepId;
  /** V84.5 · case identifier for per-case curated step state. When null
   *  OR not in the SANDBOX_CURATED_CASES list, the component falls back
   *  to generic labels. */
  caseId?: string | null;
  /** V85.3 · V6.B · real-run artifact for bridge mode. When `?bridge=1`
   *  is active AND this is non-null, the banner renders REAL data from
   *  the run via V6.A getBridgeStepState. When null OR ?bridge absent,
   *  curated V5.A getSandboxStepState is used (graceful degrade). */
  bridgeArtifact?: BridgeArtifact | null;
}

const STEP_BANNER_FADE_MS = 1000;

export function DemoSandboxV5({
  stepId,
  caseId = null,
  bridgeArtifact = null,
}: DemoSandboxV5Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const sandboxActive = searchParams.get("demo") === "2";
  // V85.3 · V6.B · bridge mode opt-in via ?bridge=1.
  // bridgeOn = URL says bridge is requested AND we have a real artifact.
  // When URL requests bridge but artifact is null → falls back to curated
  // (graceful degrade per V6 reverse-stop #6).
  const bridgeRequested = searchParams.get("bridge") === "1";
  const bridgeOn = bridgeRequested && bridgeArtifact != null;

  // Banner fades after STEP_BANNER_FADE_MS. We track the step that produced
  // the most recent banner so a rapid click sequence doesn't stack timers.
  const [bannerStep, setBannerStep] = useState<StepId | null>(null);
  const fadeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevStep = useRef<StepId | null>(null);

  useEffect(() => {
    if (!sandboxActive) {
      setBannerStep(null);
      if (fadeTimer.current) {
        clearTimeout(fadeTimer.current);
        fadeTimer.current = null;
      }
      return;
    }
    if (prevStep.current === stepId) return;
    prevStep.current = stepId;

    setBannerStep(stepId);
    if (fadeTimer.current) clearTimeout(fadeTimer.current);
    fadeTimer.current = setTimeout(() => {
      setBannerStep(null);
      fadeTimer.current = null;
    }, STEP_BANNER_FADE_MS);
  }, [sandboxActive, stepId]);

  useEffect(
    () => () => {
      if (fadeTimer.current) clearTimeout(fadeTimer.current);
    },
    [],
  );

  if (!sandboxActive) return null;

  const handleExit = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("demo");
    setSearchParams(next, { replace: true });
  };

  return (
    <div
      data-testid="demo-sandbox-v5"
      data-step-id={String(stepId)}
      className="absolute top-1 right-3 z-30 flex items-center gap-2 text-[10px] font-mono"
    >
      <span
        data-testid="sandbox-mode-pill"
        className="text-v3-textTertiary border border-v3-border rounded px-2 py-0.5 uppercase tracking-[0.08em]"
      >
        SANDBOX MODE · curated state · no real solver
      </span>
      <button
        type="button"
        data-testid="sandbox-exit"
        onClick={handleExit}
        className="text-v3-textTertiary underline decoration-1 underline-offset-2 hover:text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        aria-label="Exit sandbox mode"
      >
        × exit
      </button>

      {bannerStep !== null && (() => {
        // V85.3 · V6.B · bridge takes precedence when active + artifact
        // present, else curated fallback. The data-source attribute
        // makes the active path inspectable for V6.C diff panel + tests.
        const bridgeState = bridgeOn
          ? getBridgeStepState(bridgeArtifact, bannerStep)
          : null;
        const isBridge = bridgeState != null;
        const banner = isBridge
          ? bridgeState.banner
          : `Step ${bannerStep} · ${getSandboxStepState(caseId, bannerStep).banner}`;
        return (
          <span
            data-testid="sandbox-step-banner"
            data-step-id={String(bannerStep)}
            data-case-id={caseId ?? "__fallback__"}
            data-case-curated={
              caseId && SANDBOX_CURATED_CASES.includes(caseId) ? "true" : "false"
            }
            data-source={isBridge ? "bridge" : "curated"}
            data-bridge-run-id={isBridge ? bridgeState.runId : undefined}
            // Banner sits below the pill, animates opacity to 0 via inline
            // style so we don't need a CSS transition class (keeps the
            // animation cancellable when sandbox exits).
            className="absolute top-6 right-0 mt-1 text-v3-textPrimary bg-v3-bgRaised border border-v3-accent/40 rounded px-2 py-1 whitespace-nowrap"
            style={{ opacity: 1, transition: `opacity ${STEP_BANNER_FADE_MS}ms` }}
          >
            {isBridge && (
              <span
                data-testid="bridge-live-badge"
                className="inline-block mr-2 px-1.5 py-0 text-[9px] uppercase tracking-[0.08em] border border-v3-accent rounded text-v3-accent"
              >
                LIVE
              </span>
            )}
            {banner}
          </span>
        );
      })()}
    </div>
  );
}
