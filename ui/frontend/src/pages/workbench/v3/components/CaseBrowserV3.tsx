/**
 * V71-UI-V3 · CaseBrowserV3 · left-panel workspace browser
 *
 * V72.1 · Wired to real /api/cases endpoint via react-query useQuery.
 * Falls back to a 4-case mock list when the backend is unreachable so the
 * workbench remains navigable in fully-offline dev (per V130 invariant:
 * v3 surfaces must work LLM-offline AND backend-offline).
 *
 * Per Image 01/02: WORKSPACE section + RECENT section + expandable
 * Whitelist cases with sand-coral left-indicator on active case.
 */
import { Link } from "react-router-dom";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { CaseIndexEntry } from "@/types/validation";

const FALLBACK_WHITELIST = [
  "lid_driven_cavity",
  "backward_facing_step",
  "naca0012_airfoil",
  "naca0012_transonic",
] as const;

interface CaseBrowserV3Props {
  activeCaseId: string | null;
}

function useCaseList() {
  return useQuery<CaseIndexEntry[]>({
    queryKey: ["v3-case-list"],
    queryFn: () => api.listCases(),
    staleTime: 30_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function CaseBrowserV3({ activeCaseId }: CaseBrowserV3Props) {
  const { data: cases, isLoading, isError } = useCaseList();
  const caseIds: string[] =
    cases && cases.length > 0
      ? cases.map((c) => c.case_id)
      : (FALLBACK_WHITELIST as readonly string[]).slice();

  const [whitelistOpen, setWhitelistOpen] = useState<boolean>(
    activeCaseId !== null && caseIds.includes(activeCaseId),
  );

  // Synthesize a "recent" list = last 4 cases (or fewer)
  const recent = caseIds.slice(0, 4).map((id, idx) => ({
    caseId: id,
    age: ["2h ago", "yesterday", "3d ago", "1w ago"][idx] ?? "older",
  }));

  return (
    <div
      data-testid="case-browser-v3"
      data-v71-ui-shell="true"
      data-source={isError ? "fallback" : cases ? "live-api" : "loading"}
      className="h-full flex flex-col text-[14px]"
    >
      <div className="flex-1 overflow-y-auto py-5 px-4">
        {/* WORKSPACE section */}
        <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
          Workspace
        </div>
        <div className="text-v3-textPrimary mb-1 py-1">My Workbench</div>

        <button
          type="button"
          onClick={() => setWhitelistOpen((v) => !v)}
          aria-expanded={whitelistOpen}
          aria-controls="v3-whitelist-cases-list"
          className="flex items-center justify-between w-full text-left text-v3-textPrimary py-1 hover:bg-v3-surface2 rounded px-1 -mx-1 transition-colors duration-150"
        >
          <span>
            Whitelist cases (
            {isLoading ? "…" : caseIds.length}
            {isError ? " · offline" : ""})
          </span>
          <span
            aria-hidden
            className={`text-v3-textTertiary text-xs inline-block transition-transform duration-150 ${
              whitelistOpen ? "rotate-90" : ""
            }`}
          >
            ›
          </span>
        </button>
        {whitelistOpen && (
          <div
            id="v3-whitelist-cases-list"
            role="list"
            className="ml-4 mt-1 mb-2 space-y-0.5"
          >
            {caseIds.map((c) => {
              const isActive = activeCaseId === c;
              return (
                <Link
                  key={c}
                  to={`/workbench/v3/case/${c}?step=1`}
                  role="listitem"
                  data-testid={`case-browser-item-${c}`}
                  data-active={isActive ? "true" : "false"}
                  aria-current={isActive ? "page" : undefined}
                  className={`relative block py-1 px-2 -mx-2 rounded text-[13px] truncate transition-colors duration-150 ${
                    isActive
                      ? "text-v3-textPrimary bg-v3-surface1"
                      : "text-v3-textSecondary hover:text-v3-textPrimary hover:bg-v3-surface2"
                  }`}
                >
                  {isActive && (
                    <span
                      aria-hidden
                      className="absolute left-0 top-1 bottom-1 w-[2px] bg-v3-accent rounded-r"
                    />
                  )}
                  {c}
                </Link>
              );
            })}
          </div>
        )}

        <div className="text-v3-textPrimary py-1">Recent runs (3)</div>
        <div className="text-v3-textPrimary py-1">Canonical evals (30)</div>

        {/* RECENT section */}
        <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mt-8 mb-2">
          Recent
        </div>
        {recent.map((r) => (
          <Link
            key={r.caseId}
            to={`/workbench/v3/case/${r.caseId}?step=1`}
            className="flex items-center justify-between py-1 hover:bg-v3-surface2 rounded px-1 -mx-1 text-v3-textPrimary transition-colors duration-150"
          >
            <span className="truncate text-[13px]">{r.caseId}</span>
            <span className="text-[11px] text-v3-textTertiary">{r.age}</span>
          </Link>
        ))}

        {isError && (
          <div
            data-testid="case-browser-offline-hint"
            className="mt-4 text-[11px] text-v3-textTertiary leading-relaxed"
          >
            Backend unreachable · showing {FALLBACK_WHITELIST.length}-case
            offline fallback. v3 still navigable per V130 invariant.
          </div>
        )}
      </div>
      <div className="border-t border-v3-border py-3 px-4">
        <Link
          to="/workbench/new"
          className="text-v3-textSecondary text-[13px] hover:text-v3-textPrimary transition-colors duration-150"
        >
          + new case ›
        </Link>
      </div>
    </div>
  );
}
