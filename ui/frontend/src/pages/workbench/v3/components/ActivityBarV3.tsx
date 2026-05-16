/**
 * V71-UI-V3 · ActivityBarV3 · 48px left strip with 6 navigation icons
 * Workbench / Catalog / Runs / Benchmarks / Tutorial / Settings
 * Per Image 01: sand-coral 4px left-border indicator on active item.
 */
interface ActivityBarV3Props {
  active:
    | "workbench"
    | "catalog"
    | "runs"
    | "benchmarks"
    | "tutorial"
    | "settings";
}

const ITEMS = [
  { id: "workbench", icon: "⊞", label: "Workbench" },
  { id: "catalog", icon: "▦", label: "Catalog" },
  { id: "runs", icon: "⟳", label: "Runs" },
  { id: "benchmarks", icon: "△", label: "Benchmarks" },
  { id: "tutorial", icon: "✎", label: "Tutorial" },
  { id: "settings", icon: "⚙", label: "Settings" },
] as const;

export function ActivityBarV3({ active }: ActivityBarV3Props) {
  return (
    <nav
      data-testid="activity-bar-v3"
      aria-label="Activity bar"
      className="h-full flex flex-col items-center pt-4 pb-4 text-base"
    >
      {ITEMS.map((it) => {
        const isActive = active === it.id;
        const isLast = it.id === "settings";
        return (
          <div
            key={it.id}
            data-testid={`activity-${it.id}`}
            data-active={isActive ? "true" : "false"}
            className={`relative w-full flex items-center justify-center h-10 ${
              isLast ? "mt-auto" : ""
            }`}
            title={it.label}
            aria-label={it.label}
          >
            {isActive && (
              <span
                aria-hidden
                className="absolute left-0 top-1 bottom-1 w-[3px] bg-v3-accent rounded-r"
              />
            )}
            <span
              className={
                isActive ? "text-v3-textPrimary" : "text-v3-textSecondary"
              }
            >
              {it.icon}
            </span>
          </div>
        );
      })}
    </nav>
  );
}
