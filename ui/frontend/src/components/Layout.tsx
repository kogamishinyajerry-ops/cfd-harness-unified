import { NavLink, Outlet } from "react-router-dom";

// Phase 0..6 shell. Left rail exposes live screens for every phase
// landed. Phase 5 (Audit Package Builder · Screen 6) unblocked
// 2026-04-20 by Q-1 closure (DEC-V61-006) + Q-2 closure (DEC-V61-011).
// Phase 6 (Workbench landing · 60-day extension routes) exposed
// 2026-04-28 by DEC-V61-092 (nav-discoverability defect fix).

interface NavItem {
  label: string;
  to: string;
  enabled: boolean;
  phaseLabel?: string;
}

const NAV: NavItem[] = [
  // Dashboard moved from "/" to "/pro" when /learn became the demo front
  // door (2026-04-22 convergence round). Sidebar order unchanged so the
  // power-user muscle memory still works.
  { label: "Dashboard", to: "/pro", enabled: true, phaseLabel: "Phase 4" },
  // DEC-V61-092: nav-discoverability fix. The 60-day-extension workbench
  // (/workbench, /workbench/import, /workbench/today, ...) was wired in
  // App.tsx 2026-04-26 but never surfaced in the pro-shell sidebar — power
  // users had to know the URLs by heart. This entry exposes the workbench
  // landing one click from any pro-shell page.
  { label: "Workbench", to: "/workbench", enabled: true, phaseLabel: "Phase 6" },
  { label: "Cases", to: "/cases", enabled: true, phaseLabel: "Phase 0" },
  { label: "Decisions", to: "/decisions", enabled: true, phaseLabel: "Phase 2" },
  { label: "Workflow Monitor", to: "/workflow-monitor", enabled: true, phaseLabel: "Preview" },
  { label: "Runs", to: "/runs", enabled: true, phaseLabel: "Phase 3" },
  {
    label: "Audit Package",
    to: "/audit-package",
    enabled: true,
    phaseLabel: "Phase 5",
  },
  // One-click back to the demo / learning catalog.
  { label: "← Learn", to: "/learn", enabled: true, phaseLabel: "Demo" },
];

export function Layout() {
  return (
    // DEC-V61-115 Codex R2 P2 #1: previous draft hid the sidebar entirely
    // below md, which stranded mobile users on routes that don't render
    // their own back-nav (DashboardPage / CaseListPage / DecisionsQueuePage /
    // AuditPackagePage). This iteration reflows the sidebar into a
    // horizontal top-bar below md instead of hiding it: same NavLinks, same
    // active-state styling, but laid out as a scrollable row so every route
    // remains reachable from every Layout-mounted page on any viewport.
    // Phase-label chips + brand subtitle + footer attribution collapse on
    // narrow screens to keep the bar compact; full vertical sidebar
    // restored at md+.
    <div className="flex h-full flex-col md:flex-row">
      <aside
        className="
          shrink-0 border-b border-surface-800 bg-surface-900/60
          md:w-56 md:border-b-0 md:border-r
          px-3 py-2
          md:px-3 md:py-4
        "
      >
        {/* Brand block: full vertical block at md+, compact inline at narrow.
            Hide the buyer-bridge subtitle below md to save horizontal space —
            it's a navigation surface there, not a hero. */}
        <div className="flex items-baseline gap-3 md:block md:px-2 md:pb-6">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
            CFD Harness
          </p>
          <h1 className="text-sm font-semibold text-surface-100 md:mt-0.5">
            V&amp;V Workbench
          </h1>
          {/* DEC-V61-046 round-1 R1-N1: buyer-readable bridge copy. Hidden
              below md so the top-bar stays single-line. */}
          <p className="hidden md:block md:mt-0.5 text-[10px] leading-snug text-surface-500">
            Evidence workbench for reviewers, auditors, and team leads.
          </p>
        </div>
        <nav
          className="
            mt-2 flex gap-1 overflow-x-auto
            md:mt-0 md:flex-col md:gap-0 md:space-y-0.5 md:overflow-visible
          "
        >
          {NAV.map((item) =>
            item.enabled ? (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.to === "/pro"}
                className={({ isActive }) =>
                  `flex shrink-0 items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-sm transition-colors md:shrink ${
                    isActive
                      ? "bg-surface-700 text-surface-100"
                      : "text-surface-300 hover:bg-surface-800 hover:text-surface-100"
                  }`
                }
              >
                <span className="whitespace-nowrap">{item.label}</span>
                {item.phaseLabel && (
                  <span className="hidden md:inline text-[9px] uppercase tracking-wider text-surface-500">
                    {item.phaseLabel}
                  </span>
                )}
              </NavLink>
            ) : (
              <span
                key={item.label}
                aria-disabled
                className="flex shrink-0 cursor-not-allowed items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-sm text-surface-500 md:shrink"
                title={`Coming in ${item.phaseLabel}`}
              >
                <span className="whitespace-nowrap">{item.label}</span>
                {item.phaseLabel && (
                  <span className="hidden md:inline text-[9px] uppercase tracking-wider">
                    {item.phaseLabel}
                  </span>
                )}
              </span>
            ),
          )}
        </nav>
        <footer className="hidden md:block mt-8 border-t border-surface-800 px-2 pt-4 text-[10px] leading-snug text-surface-500">
          Path B · agentic V&amp;V workbench<br />
          Phase 0..6 MVP · DEC-V61-002 / 003 / 092
        </footer>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
