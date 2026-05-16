/**
 * V71-UI-V3 · CaseBrowserV3 · left-panel workspace browser
 * Per Image 01/02: WORKSPACE section + RECENT section + expandable
 * Whitelist cases with sand-coral left-indicator on active case.
 */
import { Link } from "react-router-dom";
import { useState } from "react";

const WHITELIST_CASES = [
  "lid_driven_cavity",
  "backward_facing_step",
  "naca0012_airfoil",
  "naca0012_transonic",
  "circular_cylinder_wake",
  "plane_channel_flow",
  "rayleigh_benard_convection",
  "case_002a",
  "case_039_SA_stall",
  "case_038_buffet",
  "case_037_supersonic",
] as const;

const RECENT = [
  { caseId: "lid_driven_cavity", age: "2h ago" },
  { caseId: "naca0012_airfoil", age: "yesterday" },
  { caseId: "backward_facing_step", age: "3d ago" },
  { caseId: "apu_bay_ventilation", age: "1w ago" },
];

interface CaseBrowserV3Props {
  activeCaseId: string | null;
}

export function CaseBrowserV3({ activeCaseId }: CaseBrowserV3Props) {
  const [whitelistOpen, setWhitelistOpen] = useState<boolean>(
    activeCaseId !== null && WHITELIST_CASES.some((c) => c === activeCaseId),
  );

  return (
    <div
      data-testid="case-browser-v3"
      data-v71-ui-shell="true"
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
          className="flex items-center justify-between w-full text-left text-v3-textPrimary py-1 hover:bg-v3-surface2 rounded px-1 -mx-1"
        >
          <span>Whitelist cases (11)</span>
          <span className="text-v3-textTertiary text-xs">
            {whitelistOpen ? "˅" : "›"}
          </span>
        </button>
        {whitelistOpen && (
          <div className="ml-4 mt-1 mb-2 space-y-0.5">
            {WHITELIST_CASES.map((c) => {
              const isActive = activeCaseId === c;
              return (
                <Link
                  key={c}
                  to={`/workbench/v3/case/${c}?step=1`}
                  data-testid={`case-browser-item-${c}`}
                  data-active={isActive ? "true" : "false"}
                  className={`relative block py-1 px-2 -mx-2 rounded text-[13px] truncate ${
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
        {RECENT.map((r) => (
          <Link
            key={r.caseId}
            to={`/workbench/v3/case/${r.caseId}?step=1`}
            className="flex items-center justify-between py-1 hover:bg-v3-surface2 rounded px-1 -mx-1 text-v3-textPrimary"
          >
            <span className="truncate text-[13px]">{r.caseId}</span>
            <span className="text-[11px] text-v3-textTertiary">{r.age}</span>
          </Link>
        ))}
      </div>
      <div className="border-t border-v3-border py-3 px-4">
        <Link
          to="/workbench/new"
          className="text-v3-textSecondary text-[13px] hover:text-v3-textPrimary"
        >
          + new case ›
        </Link>
      </div>
    </div>
  );
}
