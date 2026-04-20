import { NavLink, Outlet } from "react-router-dom";

// Minimal Phase-0 shell. Left rail exposes only what's live today
// (Cases list + placeholder entries for disabled future screens).
// Disabled nav items link to '#' and carry aria-disabled so screen
// readers announce them as unreachable — they are visual placeholders
// for Phases 1..5 per docs/ui_roadmap.md.

interface NavItem {
  label: string;
  to: string;
  enabled: boolean;
  phaseLabel?: string;
}

const NAV: NavItem[] = [
  { label: "Cases", to: "/cases", enabled: true, phaseLabel: "Phase 0" },
  { label: "Case Editor", to: "#", enabled: false, phaseLabel: "Phase 1" },
  { label: "Decisions Queue", to: "#", enabled: false, phaseLabel: "Phase 2" },
  { label: "Run Monitor", to: "#", enabled: false, phaseLabel: "Phase 3" },
  { label: "Dashboard", to: "#", enabled: false, phaseLabel: "Phase 4" },
  {
    label: "Audit Package Builder",
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
            Phase 0 · MVP in progress
          </p>
        </div>
        <nav className="space-y-0.5">
          {NAV.map((item) =>
            item.enabled ? (
              <NavLink
                key={item.label}
                to={item.to}
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
          DEC-V61-002 · 2026-04-20
        </footer>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
