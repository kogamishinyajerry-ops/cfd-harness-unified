import { NavLink, Outlet } from "react-router-dom";

// Phase 0..4 shell. Left rail exposes live screens for every phase
// landed so far. Phase 5 (Audit Package Builder) remains disabled
// until Q-1 / Q-2 are externally unblocked per DEC-V61-002.

interface NavItem {
  label: string;
  to: string;
  enabled: boolean;
  phaseLabel?: string;
}

const NAV: NavItem[] = [
  { label: "Dashboard", to: "/", enabled: true, phaseLabel: "Phase 4" },
  { label: "Cases", to: "/cases", enabled: true, phaseLabel: "Phase 0" },
  { label: "Decisions", to: "/decisions", enabled: true, phaseLabel: "Phase 2" },
  { label: "Runs", to: "/runs", enabled: true, phaseLabel: "Phase 3" },
  {
    label: "Audit Package",
    to: "#",
    enabled: false,
    phaseLabel: "Phase 5",
  },
];

export function Layout() {
  return (
    <div className="flex h-full">
      <aside className="w-56 shrink-0 border-r border-surface-800 bg-surface-900/60 px-3 py-4">
        <div className="px-2 pb-6">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
            CFD Harness
          </p>
          <h1 className="mt-0.5 text-sm font-semibold text-surface-100">
            V&amp;V Workbench
          </h1>
          <p className="mt-0.5 text-[10px] text-surface-500">
            Path B · Phase 0..4 MVP
          </p>
        </div>
        <nav className="space-y-0.5">
          {NAV.map((item) =>
            item.enabled ? (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `flex items-center justify-between rounded-sm px-2 py-1.5 text-sm transition-colors ${
                    isActive
                      ? "bg-surface-700 text-surface-100"
                      : "text-surface-300 hover:bg-surface-800 hover:text-surface-100"
                  }`
                }
              >
                <span>{item.label}</span>
                {item.phaseLabel && (
                  <span className="text-[9px] uppercase tracking-wider text-surface-500">
                    {item.phaseLabel}
                  </span>
                )}
              </NavLink>
            ) : (
              <span
                key={item.label}
                aria-disabled
                className="flex cursor-not-allowed items-center justify-between rounded-sm px-2 py-1.5 text-sm text-surface-500"
                title={`Coming in ${item.phaseLabel}`}
              >
                <span>{item.label}</span>
                {item.phaseLabel && (
                  <span className="text-[9px] uppercase tracking-wider">
                    {item.phaseLabel}
                  </span>
                )}
              </span>
            ),
          )}
        </nav>
        <footer className="mt-8 border-t border-surface-800 px-2 pt-4 text-[10px] text-surface-500">
          Path B · agentic V&amp;V workbench<br />
          DEC-V61-002 · DEC-V61-003
        </footer>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
