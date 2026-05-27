/**
 * V71-UI-V3 · RightPanelV3 · 340px right column with 3-tab strip
 * Per Image 02/03/04/05/06/07/08: tabs Inspector / Advisor / TruthChain.
 * Content depends on active tab + current step + current viewport mode.
 */
import type {
  StepId,
  ViewportMode,
  RightPanelTab,
} from "../WorkbenchShellV3";
import { InspectorContent } from "./right-panel/InspectorContent";
import { AdvisorContent } from "./right-panel/AdvisorContent";
import { TruthChainContent } from "./right-panel/TruthChainContent";
import type { MatchedCommentary } from "@/data/advisor_pattern_matcher";

interface RightPanelV3Props {
  activeTab: RightPanelTab;
  onSetTab: (t: RightPanelTab) => void;
  caseId: string | null;
  stepId: StepId;
  viewportMode: ViewportMode;
  /** V83.3 · V5.B opt-in via ?failmode=1 · plumbed from WorkbenchShellV3 */
  failmodeActive?: boolean;
  /** V90.4 · V9.A post-run advisor props · optional · forwarded to AdvisorContent */
  postRunRunId?: string | null;
  postRunMatches?: MatchedCommentary[];
  postRunRulesetVersion?: string;
}

const TABS: { id: RightPanelTab; label: string }[] = [
  { id: "inspector", label: "Inspector" },
  { id: "advisor", label: "Advisor" },
  { id: "truthchain", label: "TruthChain" },
];

export function RightPanelV3({
  activeTab,
  onSetTab,
  caseId,
  stepId,
  viewportMode,
  failmodeActive = false,
  postRunRunId = null,
  postRunMatches = [],
  postRunRulesetVersion = "v9.1.0",
}: RightPanelV3Props) {
  return (
    <div
      data-testid="right-panel-v3"
      data-v71-ui-shell="true"
      className="h-full flex flex-col"
    >
      {/* Tab strip */}
      <div
        role="tablist"
        aria-label="Right panel sections"
        className="h-10 flex items-center px-4 border-b border-v3-border text-[13px]"
      >
        {TABS.map((t) => {
          const isActive = t.id === activeTab;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onSetTab(t.id)}
              id={`right-tab-${t.id}`}
              role="tab"
              aria-selected={isActive}
              // V73.2 · only reference the panel id when it actually exists
              // in DOM (active tab). Inactive tabs omit aria-controls to
              // pass axe's aria-valid-attr-value rule.
              aria-controls={isActive ? `right-panel-content-${t.id}` : undefined}
              data-testid={`right-tab-${t.id}`}
              data-active={isActive ? "true" : "false"}
              className={`relative mr-5 py-1 motion-safe:transition-colors motion-safe:duration-150 ${
                isActive
                  ? "text-v3-textPrimary"
                  : "text-v3-textSecondary hover:text-v3-textPrimary"
              }`}
            >
              {t.label}
              {isActive && (
                <span
                  aria-hidden
                  className="absolute left-0 right-0 -bottom-[1px] h-[1.5px] bg-v3-accent"
                />
              )}
            </button>
          );
        })}
      </div>
      {/* Tab content · V72.4 ARIA + autoFocus on tab change */}
      <div
        role="tabpanel"
        id={`right-panel-content-${activeTab}`}
        aria-labelledby={`right-tab-${activeTab}`}
        data-testid={`right-panel-content-${activeTab}`}
        tabIndex={0}
        key={activeTab}
        className="flex-1 overflow-y-auto py-5 px-6 motion-safe:transition-opacity motion-safe:duration-150 outline-none"
      >
        {activeTab === "inspector" && (
          <InspectorContent
            caseId={caseId}
            stepId={stepId}
            viewportMode={viewportMode}
          />
        )}
        {activeTab === "advisor" && (
          <AdvisorContent
            caseId={caseId}
            stepId={stepId}
            failmodeActive={failmodeActive}
            postRunRunId={postRunRunId}
            postRunMatches={postRunMatches}
            postRunRulesetVersion={postRunRulesetVersion}
          />
        )}
        {activeTab === "truthchain" && (
          <TruthChainContent caseId={caseId} stepId={stepId} />
        )}
      </div>
    </div>
  );
}
