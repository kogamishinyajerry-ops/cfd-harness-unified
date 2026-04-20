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
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
          <Link to="/learn" className="group flex items-baseline gap-3">
            <span className="mono text-sm font-medium tracking-tight text-surface-100">
              cfd-harness
            </span>
            <span className="text-[11px] uppercase tracking-[0.18em] text-surface-400 group-hover:text-surface-300">
              Learn
            </span>
          </Link>
          <nav className="flex items-center gap-6 text-[13px]">
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
            <a
              href="#"
              className="text-surface-500"
              onClick={(e) => {
                e.preventDefault();
                window.alert("学习路径即将上线：按难度、按物理场分类的导读");
              }}
            >
              学习路径
            </a>
            <a
              href="#"
              className="text-surface-500"
              onClick={(e) => {
                e.preventDefault();
                window.alert("参考文献视图即将上线：每个经典案例背后的原始论文");
              }}
            >
              文献
            </a>
            <span className="h-4 w-px bg-surface-700" aria-hidden />
            <Link
              to="/"
              className="text-[11px] uppercase tracking-[0.16em] text-surface-400 hover:text-surface-200"
              title="Pro workbench: audit packages, decisions, run monitor"
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
