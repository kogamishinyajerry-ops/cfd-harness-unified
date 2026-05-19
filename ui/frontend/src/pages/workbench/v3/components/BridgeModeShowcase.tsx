/**
 * V85.5 · V6.D Bridge Truth-Gate Disclosure
 *
 * Global truth-gate surface for V6 bridge mode. When `?bridge=1` is
 * active AND a real artifact is loaded, renders a top-left pill that
 * makes the bridge mode + AI passive-observe stance unambiguous, plus
 * a provenance line that surfaces real run_id / commit SHA / checksum /
 * audit-package URL from the artifact (not synthesized).
 *
 * V6 contract V6.D · `.planning/blueprints/v6/INDEX.md`:
 *   - When bridge active: pill "LIVE DATA · advisor in passive mode ·
 *     no AI mutation" at top-LEFT (distinct from V5.A sandbox pill at
 *     top-right · no positional ambiguity)
 *   - Provenance line: case_id · run_id · audit-package URL (when
 *     bundle_id resolvable) · checksum (when artifact carries one)
 *   - Explicit "× exit to curated" link clears ?bridge from URL
 *
 * V130/V132 invariants:
 *   - Read-only · no fetch · no mutation triggers
 *   - "Exit to curated" is URL state mutation only (replace, not push)
 *   - Banner text describes mode; does not recommend solver action
 */

import { useSearchParams } from "react-router-dom";
import type { BridgeArtifact } from "@/data/run_artifact_reader";

interface BridgeModeShowcaseProps {
  /** Bridge artifact loaded from `/api/cases/{id}/run-history/{run_id}`.
   *  When null, the showcase renders nothing (graceful degrade — same
   *  shape as V6.C diff panel). */
  artifact: BridgeArtifact | null;
  /** Optional bundle id for the audit-package link. When provided AND
   *  artifact is non-null, surfaces `/api/audit-packages/{bundle}/manifest.json`
   *  in the provenance line as a navigable href. */
  bundleId?: string | null;
}

export function BridgeModeShowcase({
  artifact,
  bundleId = null,
}: BridgeModeShowcaseProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const bridgeRequested = searchParams.get("bridge") === "1";
  const active = bridgeRequested && artifact != null;

  if (!active) return null;

  const handleExit = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("bridge");
    setSearchParams(next, { replace: true });
  };

  const auditHref = bundleId
    ? `/api/audit-packages/${bundleId}/manifest.json`
    : null;

  return (
    <div
      data-testid="bridge-mode-showcase"
      data-case-id={artifact.case_id}
      data-run-id={artifact.run_id}
      data-artifact-success={String(artifact.success)}
      className="absolute top-1 left-3 z-30 flex flex-col gap-1 text-[10px] font-mono"
    >
      <div className="flex items-center gap-2">
        <span
          data-testid="bridge-mode-pill"
          className="text-v3-accent border border-v3-accent rounded px-2 py-0.5 uppercase tracking-[0.08em]"
        >
          LIVE DATA · advisor in passive mode · no AI mutation
        </span>
        <button
          type="button"
          data-testid="bridge-exit"
          onClick={handleExit}
          className="text-v3-textTertiary underline decoration-1 underline-offset-2 hover:text-v3-textSecondary focus:outline focus:outline-2 focus:outline-v3-borderFocus"
          aria-label="Exit bridge mode (return to curated)"
        >
          × exit to curated
        </button>
      </div>
      <div
        data-testid="bridge-provenance-line"
        className="text-v3-textSecondary flex items-center gap-2 flex-wrap"
      >
        <span data-testid="bridge-provenance-case">
          case · <span className="text-v3-textPrimary">{artifact.case_id}</span>
        </span>
        <span className="text-v3-textTertiary">|</span>
        <span data-testid="bridge-provenance-run">
          run · <span className="text-v3-textPrimary">{artifact.run_id}</span>
        </span>
        {artifact.exit_code !== undefined && (
          <>
            <span className="text-v3-textTertiary">|</span>
            <span data-testid="bridge-provenance-exit">
              exit ·{" "}
              <span
                className={
                  artifact.exit_code === 0
                    ? "text-v3-textPrimary"
                    : "text-v3-accent"
                }
              >
                {artifact.exit_code}
              </span>
            </span>
          </>
        )}
        {auditHref && (
          <>
            <span className="text-v3-textTertiary">|</span>
            <a
              data-testid="bridge-provenance-audit"
              href={auditHref}
              className="underline decoration-dotted text-v3-textSecondary hover:text-v3-accent"
              target="_blank"
              rel="noopener noreferrer"
            >
              audit-package manifest
            </a>
          </>
        )}
      </div>
    </div>
  );
}
