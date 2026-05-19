/**
 * V86.5 · V7.D Post-Run Hand-off
 *
 * Per .planning/blueprints/v7/INDEX.md Contract V7.D:
 *   - Fires when V7.B state transitions running → done
 *   - Best-effort POST /api/cases/{case_id}/runs/{run_id}/audit-package/build
 *     (fire-and-forget · errors do NOT propagate into solver state)
 *   - Exposes lastCompletedRunId for downstream consumers:
 *       · V6 BridgeModeShowcase + DemoSandboxV5 (via bridgeArtifact prop pipeline)
 *       · TopBarV3 provenance line
 *
 * The hook itself does NOT fetch the run-history detail — it just exposes
 * the (case_id, run_id) tuple so the parent component can wire its
 * existing useQuery to /api/cases/{id}/run-history/{run_id}.
 *
 * V7.D reverse-stops (.planning/blueprints/v7/INDEX.md §3):
 *   #6 V132 stays at 9 (audit-package POST counted in baseline)
 *   #8 V6 bridge READ-ONLY preserved (parent reads the run, hook doesn't
 *      re-trigger anything from the bridge surfaces)
 *   #10 audit-package call is fire-and-forget (failure does NOT propagate
 *       as run state regression)
 *
 * V130 invariant:
 *   - The audit-package POST fires ONLY in response to the V7.B
 *     state-machine transition running → done; the transition itself
 *     fires because of a real solver completion event (server-side),
 *     which fires because the user clicked the Run button. The full
 *     chain is user-initiated · no AI auto-trigger.
 *
 * Test surface:
 *   - The hook accepts a `buildImpl` override so unit tests can inject
 *     a mock (avoid hitting the real /audit-package endpoint).
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import type { AuditPackageBuildResponse } from "@/types/audit_package";

export interface PostRunHandoff {
  /** Most recent successfully-completed run_id (running → done transition). */
  lastCompletedRunId: string | null;
  /** The caseId that produced lastCompletedRunId. */
  lastCompletedCaseId: string | null;
  /** Best-effort audit-package response or null if not yet completed or failed. */
  lastAuditPackage: AuditPackageBuildResponse | null;
  /** True while the audit-package POST is in flight. Consumers can show
   *  a tiny "building audit package …" hint but the solver run state has
   *  already transitioned to done, so this is purely informational. */
  audit_in_flight: boolean;
  /** Audit-package error (last attempt). null until first failure. */
  audit_error: string | null;
  /** Called by V7.B onRunCompleted callback when a real run finishes. */
  notifyCompleted: (runId: string, caseId: string) => void;
  /** Clears the handoff state · used by parent when user dismisses the
   *  completion (e.g., starts another run). */
  reset: () => void;
}

interface UsePostRunHandoffV7Options {
  /** Override audit-package builder for tests · defaults to
   *  `api.buildAuditPackage`. */
  buildImpl?: (caseId: string, runId: string) => Promise<AuditPackageBuildResponse>;
}

export function usePostRunHandoffV7(
  opts: UsePostRunHandoffV7Options = {},
): PostRunHandoff {
  const buildImpl = opts.buildImpl ?? api.buildAuditPackage;

  const [lastCompletedRunId, setLastCompletedRunId] = useState<string | null>(
    null,
  );
  const [lastCompletedCaseId, setLastCompletedCaseId] = useState<string | null>(
    null,
  );
  const [lastAuditPackage, setLastAuditPackage] =
    useState<AuditPackageBuildResponse | null>(null);
  const [audit_in_flight, setAuditInFlight] = useState<boolean>(false);
  const [audit_error, setAuditError] = useState<string | null>(null);

  // Generation counter: if a new completion lands while a prior
  // audit-package POST is in flight, the prior response is ignored.
  const genRef = useRef<number>(0);
  // Snapshot the latest buildImpl so notifyCompleted closure stays stable.
  const buildImplRef = useRef(buildImpl);
  useEffect(() => {
    buildImplRef.current = buildImpl;
  }, [buildImpl]);

  const notifyCompleted = useCallback(
    (runId: string, caseId: string) => {
      if (!runId || !caseId) return;
      genRef.current += 1;
      const myGen = genRef.current;

      setLastCompletedRunId(runId);
      setLastCompletedCaseId(caseId);
      setLastAuditPackage(null);
      setAuditError(null);
      setAuditInFlight(true);

      // Fire-and-forget audit-package POST. Errors swallowed into state,
      // never thrown.
      buildImplRef
        .current(caseId, runId)
        .then((resp) => {
          if (genRef.current !== myGen) return; // stale
          setLastAuditPackage(resp);
          setAuditInFlight(false);
          setAuditError(null);
        })
        .catch((e: unknown) => {
          if (genRef.current !== myGen) return;
          const msg = e instanceof Error ? e.message : String(e);
          setAuditInFlight(false);
          setAuditError(msg);
        });
    },
    [],
  );

  const reset = useCallback(() => {
    genRef.current += 1;
    setLastCompletedRunId(null);
    setLastCompletedCaseId(null);
    setLastAuditPackage(null);
    setAuditInFlight(false);
    setAuditError(null);
  }, []);

  return {
    lastCompletedRunId,
    lastCompletedCaseId,
    lastAuditPackage,
    audit_in_flight,
    audit_error,
    notifyCompleted,
    reset,
  };
}
