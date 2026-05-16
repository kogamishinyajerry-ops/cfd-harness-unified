/**
 * V71-UI-V3 · TopBarV3 · workbench top bar per Image 01/02/05
 * 40px tall · breadcrumb left · run-state pill center-left · SHA/user/⌘K/gear right
 */
import type { StepId } from "../WorkbenchShellV3";

interface TopBarV3Props {
  caseId: string | null;
  stepId: StepId;
}

export function TopBarV3({ caseId }: TopBarV3Props) {
  return (
    <div
      data-testid="topbar-v3"
      data-v71-ui-shell="true"
      className="h-10 flex items-center px-4 text-[13px]"
    >
      <div className="text-v3-textSecondary">
        Workbench{caseId ? ` / ${caseId}` : ""}
      </div>
      <div className="ml-6 text-v3-textTertiary text-[11px] uppercase tracking-[0.08em]">
        ○ NO RUN ACTIVE
      </div>
      <div className="flex-1" />
      <div className="flex items-center gap-4 text-v3-textTertiary text-[11px]">
        <span className="font-mono">a4f3b21</span>
        <span
          role="img"
          aria-label="user avatar"
          className="w-5 h-5 rounded-full bg-v3-surface2 border border-v3-border"
        />
        <span>⌘K</span>
        <span role="img" aria-label="settings">⚙</span>
      </div>
    </div>
  );
}
