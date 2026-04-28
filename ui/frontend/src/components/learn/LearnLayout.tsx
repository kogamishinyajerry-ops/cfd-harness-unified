import { Link, NavLink, Outlet } from "react-router-dom";

// Student-facing shell. Deliberately softer than the internal /
// workbench — top-nav with a text mark, no dense sidebar, warmer
// typographic rhythm. The "Professional" link at top-right is the
// one-way door into the pro workbench (/dashboard), which is where
// audit packages, decisions queue, and run monitor live.

export function LearnLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-surface-950 text-surface-100">
      <header className="border-b border-surface-800/70 bg-surface-900/40 backdrop-blur">
        {/* DEC-V61-092 Codex R1 P1: header was a single-row flex with
            gap-6 between nav items. Adding the import CTA brought
            total to 5 items + dividers, which clips below ~480px and
            hides the entry point this DEC is meant to expose.
            Wrapping + smaller mobile gap restores reachability on
            mobile widths (smoke tested at 375px). */}
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-y-2 px-6 py-3.5">
          <Link to="/learn" className="group flex items-baseline gap-3">
            <span className="mono text-sm font-medium tracking-tight text-surface-100">
              cfd-harness
            </span>
            <span className="text-[11px] uppercase tracking-[0.18em] text-surface-400 group-hover:text-surface-300">
              Learn
            </span>
          </Link>
          <nav className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] sm:gap-x-6">
            {/* DEC-V61-046 round-1 R1-M5: removed two placeholder nav
                items ("学习路径" / "文献") that previously fired window.alert
                "即将上线". Placeholders in a buyer-facing top-nav read as
                "demo not finished". Will re-introduce when the pages are
                actually built (currently not scoped). */}
            <NavLink
              to="/learn"
              end
              className={({ isActive }) =>
                isActive
                  ? "text-surface-100"
                  : "text-surface-400 hover:text-surface-100"
              }
            >
              案例目录
            </NavLink>
            <span className="h-4 w-px bg-surface-700" aria-hidden />
            {/* DEC-V61-092: nav-discoverability fix. Strangers landing
                at /learn need a visible entry point to the workbench so
                they can run their own STL through ingest → mesh → run
                without insider URL knowledge. The existing "Pro
                Workbench →" link points at /pro (Dashboard), which
                doesn't include the import surface. */}
            <Link
              to="/workbench/import"
              className="text-[13px] text-surface-300 hover:text-surface-100"
              title="Import an STL geometry to start a new case"
            >
              导入新 case →
            </Link>
            <span className="h-4 w-px bg-surface-700" aria-hidden />
            <Link
              to="/pro"
              className="text-[11px] uppercase tracking-[0.16em] text-surface-400 hover:text-surface-200"
              title="Pro workbench: audit packages, decisions, run monitor — for reviewers and audit teams"
            >
              Pro Workbench →
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-surface-800/50 px-6 py-6 text-center text-[11px] text-surface-500">
        <p>
          10 个经典 CFD 流动问题 · 每一个都配有黄金标准、历史文献与典型陷阱。
        </p>
        <p className="mt-1 mono text-[10px] text-surface-600">
          Data sourced from knowledge/whitelist.yaml ·
          powered by the same validation engine the Pro Workbench uses.
        </p>
      </footer>
    </div>
  );
}
