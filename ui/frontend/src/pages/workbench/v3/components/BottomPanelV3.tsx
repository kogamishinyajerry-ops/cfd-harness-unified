/**
 * V71-UI-V3 · BottomPanelV3 · collapsible bottom row 180px
 *
 * Per .planning/blueprints/v3/INDEX.md Image 03/05/08:
 *   - Collapsed → 32px summary bar with toggle + run-state pill +
 *     "expand for residuals / forces / log / console" hint.
 *   - Expanded → 180px height · 4 tabs Console / Residuals / Forces / Log.
 *
 * V71 scope: static layout + tab-content placeholders. Real streaming SSE
 * wiring lands in V71.3. The shell auto-expands on Step 4 entry; engineer
 * can collapse at any time.
 */
import { useState } from "react";
import type { StepId } from "../WorkbenchShellV3";
import { RunSolverButtonV7 } from "./RunSolverButtonV7";
import { SolverConfigEditorV8 } from "./SolverConfigEditorV8";
import type { SolverRunState } from "../hooks/useSolverRunStateV7";
import type {
  ControlDictField,
  ValidationError,
} from "./solver_config_validator";
import type { SolverConfigEditorState } from "./SolverConfigEditorV8";

type BottomTab = "console" | "residuals" | "forces" | "log" | "config";

interface SolverConfigSlice {
  fields: Partial<Record<ControlDictField, string>>;
  baseline: Partial<Record<ControlDictField, string>>;
  state: SolverConfigEditorState;
  validationErrors: ValidationError[];
  errorMessage: string | null;
  readOnlyMode: boolean;
  onFieldChange: (field: ControlDictField, value: string) => void;
  onConfirmCommit: () => void;
  onDiscard: () => void;
  /** V89.2 injection harness · dev/test only · production never sets. */
  forceDiffOpen?: boolean;
  /** V89.2 injection harness · dev/test only · exposed for inspection. */
  injectionKey?: "dirty" | "diff_open" | "error" | null;
}

interface BottomPanelV3Props {
  collapsed: boolean;
  onToggle: () => void;
  stepId: StepId;
  /** V87.1 · V7 substantiation · optional integration props.
   *  When all 5 are supplied, the Run Solver button + state-aware
   *  affordances render in the collapsed bar at Step ≥4. When any are
   *  missing (legacy contexts · tests not exercising V7), the panel
   *  renders unchanged. */
  caseId?: string | null;
  solverRunState?: SolverRunState;
  meshReady?: boolean;
  bcSetup?: boolean;
  onRequestRun?: () => void;
  onCancelRun?: () => void;
  /** V88.2 · V8 substantiation · optional integration props.
   *  When supplied, the "Config" tab mounts SolverConfigEditorV8 in the
   *  expanded panel. When missing (legacy contexts · tests not exercising
   *  V8), the Config tab is hidden and the panel renders unchanged. */
  solverConfig?: SolverConfigSlice;
}

const BASE_TABS: { id: BottomTab; label: string }[] = [
  { id: "console", label: "Console" },
  { id: "residuals", label: "Residuals" },
  { id: "forces", label: "Forces" },
  { id: "log", label: "Log" },
];

const CONFIG_TAB: { id: BottomTab; label: string } = {
  id: "config",
  label: "Config",
};

function CollapsedBar({
  onToggle,
  stepId,
  caseId,
  solverRunState,
  meshReady,
  bcSetup,
  onRequestRun,
  onCancelRun,
}: {
  onToggle: () => void;
  stepId: StepId;
  caseId?: string | null;
  solverRunState?: SolverRunState;
  meshReady?: boolean;
  bcSetup?: boolean;
  onRequestRun?: () => void;
  onCancelRun?: () => void;
}) {
  const hint =
    stepId >= 4
      ? "solver streams · residuals · forces · console"
      : "expand for console / residuals / forces / log";
  // V87.1 · Run button mounts at Step ≥4 when integration props supplied.
  // All 5 V7 props must be present (V87 reverse-stop carry from V86):
  // partial wiring would surface a broken affordance to the user.
  const showRunButton =
    stepId >= 4 &&
    solverRunState !== undefined &&
    meshReady !== undefined &&
    bcSetup !== undefined &&
    onRequestRun !== undefined &&
    onCancelRun !== undefined;
  return (
    <div
      data-testid="bottom-panel-collapsed"
      data-v71-ui-bottom="collapsed"
      className="h-8 border-t border-v3-border bg-v3-surface1 flex items-center px-4 text-[11px] text-v3-textTertiary"
    >
      <button
        type="button"
        data-testid="bottom-panel-toggle"
        onClick={onToggle}
        className="hover:text-v3-textPrimary mr-3 font-mono"
        aria-label="Expand bottom panel"
      >
        ▴
      </button>
      <span className="uppercase tracking-[0.08em]">{hint}</span>
      {showRunButton && (
        <div className="ml-auto flex items-center gap-3">
          <RunSolverButtonV7
            caseId={caseId ?? null}
            meshReady={meshReady!}
            bcSetup={bcSetup!}
            runState={solverRunState!}
            onRequestRun={onRequestRun!}
            onCancelRun={onCancelRun!}
          />
        </div>
      )}
      {!showRunButton && stepId >= 4 && (
        <span className="ml-auto inline-flex items-center text-v3-accent text-[11px]">
          <span
            aria-hidden
            className="inline-block w-1.5 h-1.5 rounded-full bg-v3-accent mr-1.5"
          />
          streaming
        </span>
      )}
    </div>
  );
}

function ConsoleTab({ stepId }: { stepId: StepId }) {
  // Static representative log lines; V71.3 swaps for live SSE buffer.
  const lines =
    stepId >= 4
      ? [
          "[solver] simpleFoam · time = 132 · pCorrector loop",
          "[solver] U: linear · GAMG p · tol 1e-06",
          "[mesh] cellZones {} faceZones {}",
          "[boundaryField] inlet · type fixedValue · value uniform (1 0 0)",
        ]
      : [
          "[ready] workbench v3 mounted · advisor offline OK",
          "[corpus] sha 7c4f8a1e · 1284 chunks indexed",
        ];
  return (
    <pre
      data-testid="bottom-tab-console-content"
      className="text-[11px] text-v3-textSecondary font-mono leading-relaxed whitespace-pre-wrap"
    >
      {lines.join("\n")}
    </pre>
  );
}

function ResidualsTab({ stepId }: { stepId: StepId }) {
  if (stepId < 4) {
    return (
      <p
        data-testid="bottom-tab-residuals-empty"
        className="text-[12px] text-v3-textTertiary"
      >
        Residuals will appear once Step 4 starts the solver.
      </p>
    );
  }
  // Mini-strip: 5 most recent decades at iter 132.
  return (
    <div data-testid="bottom-tab-residuals-content">
      <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
        iter 132 · most recent
      </div>
      <ul className="text-[12px] font-mono space-y-0.5">
        <li className="flex justify-between text-v3-textSecondary">
          <span>Ux</span>
          <span className="tabular-nums">3.7e-4 ↓</span>
        </li>
        <li className="flex justify-between text-v3-textSecondary">
          <span>Uy</span>
          <span className="tabular-nums">2.9e-4 ↓</span>
        </li>
        <li className="flex justify-between text-v3-textSecondary">
          <span>Uz</span>
          <span className="tabular-nums">1.4e-4 ↓</span>
        </li>
        <li className="flex justify-between text-v3-accent">
          <span>p (watched)</span>
          <span className="tabular-nums">5.1e-3 ↓</span>
        </li>
        <li className="flex justify-between text-v3-textSecondary">
          <span>continuity</span>
          <span className="tabular-nums">8.6e-5 ↓</span>
        </li>
      </ul>
    </div>
  );
}

function ForcesTab({ stepId }: { stepId: StepId }) {
  if (stepId < 4) {
    return (
      <p className="text-[12px] text-v3-textTertiary">
        Force coefficients appear once Step 4 starts.
      </p>
    );
  }
  return (
    <div data-testid="bottom-tab-forces-content">
      <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
        force coefficients · iter 132
      </div>
      <ul className="text-[12px] font-mono space-y-0.5">
        <li className="flex justify-between text-v3-textSecondary">
          <span>Cd</span>
          <span className="tabular-nums">0.0421</span>
        </li>
        <li className="flex justify-between text-v3-textSecondary">
          <span>Cl</span>
          <span className="tabular-nums">0.0008</span>
        </li>
        <li className="flex justify-between text-v3-textSecondary">
          <span>Cm</span>
          <span className="tabular-nums">−0.0014</span>
        </li>
      </ul>
    </div>
  );
}

function LogTab({ stepId }: { stepId: StepId }) {
  const log = [
    "10:42:18 [setup] checkMesh OK",
    "10:42:19 [setup] decomposePar n=4",
    "10:42:21 [solve] simpleFoam started",
    `10:42:38 [solve] iter ${stepId >= 4 ? 132 : 0} · stable`,
  ];
  return (
    <pre
      data-testid="bottom-tab-log-content"
      className="text-[11px] text-v3-textSecondary font-mono whitespace-pre-wrap leading-relaxed"
    >
      {log.join("\n")}
    </pre>
  );
}

export function BottomPanelV3({
  collapsed,
  onToggle,
  stepId,
  caseId,
  solverRunState,
  meshReady,
  bcSetup,
  onRequestRun,
  onCancelRun,
  solverConfig,
}: BottomPanelV3Props) {
  const [activeTab, setActiveTab] = useState<BottomTab>("console");
  // V88.2 · Config tab visibility · only when V8 wiring supplied AND the
  // engineer is on a step where solver-config edits matter (≥3 = post-BC).
  // Hidden in read-only modes per V88 reverse-stop #20 (the V8 component
  // also enforces this internally, but suppressing the tab too keeps the
  // tab strip clean).
  const showConfigTab =
    solverConfig !== undefined && stepId >= 3 && !solverConfig.readOnlyMode;
  const TABS = showConfigTab ? [...BASE_TABS, CONFIG_TAB] : BASE_TABS;

  if (collapsed) {
    return (
      <CollapsedBar
        onToggle={onToggle}
        stepId={stepId}
        caseId={caseId}
        solverRunState={solverRunState}
        meshReady={meshReady}
        bcSetup={bcSetup}
        onRequestRun={onRequestRun}
        onCancelRun={onCancelRun}
      />
    );
  }

  return (
    <div
      data-testid="bottom-panel-expanded"
      data-v71-ui-bottom="expanded"
      className="h-[180px] border-t border-v3-border bg-v3-surface1 flex flex-col"
    >
      {/* Tab strip + collapse handle */}
      <div className="h-9 flex items-center px-4 border-b border-v3-border text-[12px]">
        <button
          type="button"
          data-testid="bottom-panel-toggle"
          onClick={onToggle}
          className="text-v3-textTertiary hover:text-v3-textPrimary mr-4 font-mono"
          aria-label="Collapse bottom panel"
        >
          ▾
        </button>
        {/* V73.2 · tablist wrapper so role=tab elements have a valid parent */}
        <div role="tablist" aria-label="Bottom panel sections" className="flex items-center">
        {TABS.map((t) => {
          const isActive = t.id === activeTab;
          return (
            <button
              key={t.id}
              type="button"
              data-testid={`bottom-tab-${t.id}`}
              data-active={isActive ? "true" : "false"}
              onClick={() => setActiveTab(t.id)}
              aria-selected={isActive}
              role="tab"
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
        {stepId >= 4 && (
          <span className="ml-auto inline-flex items-center text-v3-accent text-[11px]">
            <span
              aria-hidden
              className="inline-block w-1.5 h-1.5 rounded-full bg-v3-accent mr-1.5"
            />
            streaming
          </span>
        )}
      </div>
      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 min-h-0">
        {activeTab === "console" && <ConsoleTab stepId={stepId} />}
        {activeTab === "residuals" && <ResidualsTab stepId={stepId} />}
        {activeTab === "forces" && <ForcesTab stepId={stepId} />}
        {activeTab === "log" && <LogTab stepId={stepId} />}
        {activeTab === "config" && solverConfig && (
          <SolverConfigEditorV8
            caseId={caseId ?? null}
            readOnlyMode={solverConfig.readOnlyMode}
            fields={solverConfig.fields}
            baseline={solverConfig.baseline}
            state={solverConfig.state}
            validationErrors={solverConfig.validationErrors}
            errorMessage={solverConfig.errorMessage}
            onFieldChange={solverConfig.onFieldChange}
            onConfirmCommit={solverConfig.onConfirmCommit}
            onDiscard={solverConfig.onDiscard}
            forceDiffOpen={solverConfig.forceDiffOpen}
          />
        )}
      </div>
    </div>
  );
}
