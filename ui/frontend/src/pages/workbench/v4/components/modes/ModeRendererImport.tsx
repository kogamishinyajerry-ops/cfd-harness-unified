/**
 * V4 · Mode renderer · 导入 (Import)
 *
 * The original import blueprint page task is not a marketing upload card:
 * it is a provenance cockpit that turns raw engineering files into an
 * auditable case intake ledger. This renderer keeps the V4 density pattern:
 * source queue, real CAD preview, validation matrix, and manual TrustGate.
 */
import { GEOMETRY_REAL_CAD_ASSEMBLY } from "../geometryBlueprint";
import {
  IMPORT_BLUEPRINT_CHECKS,
  IMPORT_BLUEPRINT_KPIS,
  IMPORT_BLUEPRINT_SOURCES,
  IMPORT_BLUEPRINT_TASK,
  type ImportBlueprintCheck,
  type ImportBlueprintSource,
} from "../importBlueprint";
import { useGlbAvailability } from "../../hooks/useGlbAvailability";
import { ViewportV4, type V4CameraPreset } from "../ViewportV4";
import { V4_PALETTE } from "@/theme/industrial_minimalist";

interface Props {
  caseId?: string;
  cameraPreset?: V4CameraPreset;
}

const STATUS_STYLE: Record<
  ImportBlueprintSource["status"] | ImportBlueprintCheck["status"],
  { label: string; className: string; dot: string }
> = {
  accepted: {
    label: "ACCEPTED",
    className: "border-v4-healthy/35 text-v4-healthy",
    dot: V4_PALETTE.healthy,
  },
  review: {
    label: "REVIEW",
    className: "border-v4-warn/35 text-v4-warn",
    dot: V4_PALETTE.warn,
  },
  blocked: {
    label: "BLOCKED",
    className: "border-v4-crit/35 text-v4-crit",
    dot: V4_PALETTE.crit,
  },
  PASS: {
    label: "PASS",
    className: "border-v4-healthy/35 text-v4-healthy",
    dot: V4_PALETTE.healthy,
  },
  REVIEW: {
    label: "REVIEW",
    className: "border-v4-warn/35 text-v4-warn",
    dot: V4_PALETTE.warn,
  },
  BLOCKED: {
    label: "BLOCKED",
    className: "border-v4-crit/35 text-v4-crit",
    dot: V4_PALETTE.crit,
  },
};

function SourceRow({ source }: { source: ImportBlueprintSource }) {
  const status = STATUS_STYLE[source.status];
  return (
    <li
      className="grid grid-cols-[14px_minmax(0,1fr)_44px] items-center gap-1.5 border-b border-v4-border px-2 py-2 last:border-b-0"
      data-testid={`v4-import-source-${source.id}`}
      data-status={source.status}
    >
      <span
        className="h-2.5 w-2.5 rounded-sm"
        style={{ backgroundColor: status.dot }}
        aria-hidden
      />
      <div className="min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="truncate font-mono text-[11px] text-v4-textPrimary">
            {source.name}
          </span>
          <span className="shrink-0 text-[9px] text-v4-textTertiary">
            {source.size}
          </span>
        </div>
        <div className="mt-0.5 truncate text-[10px] text-v4-textSecondary">
          {source.detail}
        </div>
      </div>
      <span className="rounded border border-v4-border px-1.5 py-0.5 text-center font-mono text-[9px] text-v4-textSecondary">
        {source.kind}
      </span>
    </li>
  );
}

function CheckRow({ check }: { check: ImportBlueprintCheck }) {
  const status = STATUS_STYLE[check.status];
  return (
    <li
      className="grid grid-cols-[minmax(0,0.85fr)_minmax(0,0.95fr)_56px] items-center gap-1.5 border-b border-v4-border px-2 py-2 last:border-b-0"
      data-testid={`v4-import-check-${check.label}`}
      data-status={check.status}
    >
      <span className="truncate text-[11px] text-v4-textSecondary">
        {check.label}
      </span>
      <span className="truncate font-mono text-[11px] text-v4-textPrimary">
        {check.value}
      </span>
      <span
        className={[
          "rounded border px-1.5 py-0.5 text-center font-mono text-[9px]",
          status.className,
        ].join(" ")}
        title={check.detail}
      >
        {status.label}
      </span>
    </li>
  );
}

function IntakeMetric({
  value,
  label,
  unit,
  tone = "neutral",
}: {
  value: string;
  label: string;
  unit?: string;
  tone?: "healthy" | "warn" | "neutral";
}) {
  return (
    <div className="min-w-0 border-r border-v4-border px-3 last:border-r-0">
      <div className="flex items-baseline gap-1.5">
        <span
          className={[
            "font-mono text-[22px] font-semibold leading-none tabular-nums",
            tone === "healthy" && "text-v4-healthy",
            tone === "warn" && "text-v4-warn",
            tone === "neutral" && "text-v4-textPrimary",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {value}
        </span>
        {unit && <span className="text-[10px] text-v4-textTertiary">{unit}</span>}
      </div>
      <div className="mt-1 truncate text-[10px] text-v4-textSecondary">
        {label}
      </div>
    </div>
  );
}

export function ModeRendererImport({ caseId, cameraPreset = "iso" }: Props) {
  const cadProbe = useGlbAvailability(GEOMETRY_REAL_CAD_ASSEMBLY.glbUrl);
  const previewReady = cadProbe.available === true;
  const previewLoading = cadProbe.available === null || cadProbe.isLoading;

  return (
    <div
      data-testid="v4-mode-import"
      className="flex h-full w-full flex-col bg-v4-canvas"
      data-source-task={IMPORT_BLUEPRINT_TASK.pageTask}
      data-cad-source={
        previewReady ? GEOMETRY_REAL_CAD_ASSEMBLY.kind : "missing-cad-preview"
      }
    >
      <div className="flex h-11 shrink-0 items-center gap-3 border-b border-v4-border px-3">
        <div className="min-w-[170px] text-[13px] font-medium text-v4-textPrimary">
          导入 · 来源摄入
        </div>
        <div className="flex h-full items-center gap-4 text-[11px]">
          {["源文件", "单位", "拓扑", "分件语义", "TrustGate"].map((label, index) => (
            <span
              key={label}
              className={[
                "flex h-full items-center border-b-2 px-0.5",
                index === 0
                  ? "border-v4-active text-v4-active"
                  : "border-transparent text-v4-textSecondary",
              ].join(" ")}
            >
              {label}
            </span>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2 font-mono text-[10px] text-v4-textTertiary">
          <span>{caseId ?? "staging case"}</span>
          <span className="text-v4-border">|</span>
          <span>advisor only · manual accept</span>
        </div>
      </div>

      <div className="flex h-14 shrink-0 items-center border-b border-v4-border bg-v4-shell/50 px-3">
        <div className="grid w-full grid-cols-5 border border-v4-border bg-v4-surfaceRaised/35">
          <IntakeMetric
            value={String(IMPORT_BLUEPRINT_KPIS.fileCount)}
            label="摄入文件"
            unit="项"
          />
          <IntakeMetric
            value={String(IMPORT_BLUEPRINT_KPIS.acceptedCount)}
            label="已接受"
            unit="项"
            tone="healthy"
          />
          <IntakeMetric
            value={String(IMPORT_BLUEPRINT_KPIS.reviewCount)}
            label="待人工确认"
            unit="项"
            tone="warn"
          />
          <IntakeMetric
            value={String(IMPORT_BLUEPRINT_KPIS.partCount)}
            label="CAD 分件"
            unit="parts"
          />
          <IntakeMetric
            value={IMPORT_BLUEPRINT_KPIS.sourceScale}
            label="scale mm→m"
          />
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[230px_minmax(260px,1fr)_220px] gap-px bg-v4-border">
        <aside
          className="flex min-h-0 flex-col bg-v4-shell"
          data-testid="v4-import-source-queue"
        >
          <div className="flex h-9 items-center justify-between border-b border-v4-border px-3">
            <span className="text-[10px] uppercase tracking-wider text-v4-textTertiary">
              Source queue
            </span>
            <span className="font-mono text-[10px] text-v4-textSecondary">
              {IMPORT_BLUEPRINT_KPIS.fileCount} files
            </span>
          </div>
          <ul className="min-h-0 flex-1 overflow-y-auto text-[11px]">
            {IMPORT_BLUEPRINT_SOURCES.map((source) => (
              <SourceRow key={source.id} source={source} />
            ))}
          </ul>
          <div className="border-t border-v4-border p-3 text-[10px] leading-4 text-v4-textSecondary">
            <div className="flex justify-between">
              <span>source image</span>
              <span className="font-mono text-v4-textTertiary">
                v3/02-import.png
              </span>
            </div>
            <div className="mt-1 flex justify-between">
              <span>primary CAD</span>
              <span className="font-mono text-v4-textPrimary">
                {GEOMETRY_REAL_CAD_ASSEMBLY.partCount} parts
              </span>
            </div>
          </div>
        </aside>

        <section
          className="relative min-h-0 overflow-hidden bg-[radial-gradient(circle_at_50%_35%,rgba(91,180,255,0.08),transparent_42%)]"
          data-testid="v4-import-cad-preview"
        >
          {previewReady ? (
            <ViewportV4
              glbUrl={GEOMETRY_REAL_CAD_ASSEMBLY.glbUrl}
              cameraPreset={cameraPreset}
              showGrid={false}
            />
          ) : previewLoading ? (
            <div
              className="flex h-full items-center justify-center text-center"
              data-testid="v4-import-cad-preview-loading"
            >
              <div className="border border-v4-border bg-v4-surface/85 px-5 py-4">
                <div className="text-[12px] font-medium text-v4-textPrimary">
                  正在加载 CAD 预览
                </div>
                <div className="mt-1 text-[10px] text-v4-textSecondary">
                  检查真实 GLB 资产后再进入视口。
                </div>
              </div>
            </div>
          ) : (
            <div
              className="flex h-full items-center justify-center text-center"
              data-testid="v4-import-cad-preview-missing"
            >
              <div className="border border-v4-border bg-v4-surface/85 px-5 py-4">
                <div className="text-[12px] font-medium text-v4-textPrimary">
                  CAD 预览资产不可用
                </div>
                <div className="mt-1 text-[10px] text-v4-textSecondary">
                  导入页不使用 SVG 或 bitmap 代替真实 CAD。
                </div>
              </div>
            </div>
          )}
          {previewLoading && (
            <div className="pointer-events-none absolute left-3 top-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textTertiary">
              loading CAD preview
            </div>
          )}
          <div className="pointer-events-none absolute bottom-3 left-3 right-3 rounded border border-v4-border bg-v4-surfaceRaised/95 px-2.5 py-1.5 text-[10px]">
            <div className="truncate font-mono text-v4-textPrimary">
              {GEOMETRY_REAL_CAD_ASSEMBLY.sourceStep}
            </div>
            <div className="mt-0.5 text-v4-textTertiary">
              true CAD GLB preview · no SVG fallback
            </div>
          </div>
          <div className="pointer-events-none absolute right-3 top-3 rounded border border-v4-active/50 bg-v4-surfaceRaised/95 px-2 py-1 text-[10px]">
            <span className="text-v4-textTertiary">state </span>
            <span className="font-mono text-v4-active">STAGING</span>
          </div>
        </section>

        <aside
          className="flex min-h-0 flex-col bg-v4-shell"
          data-testid="v4-import-validation-matrix"
        >
          <div className="flex h-9 items-center justify-between border-b border-v4-border px-3">
            <span className="text-[10px] uppercase tracking-wider text-v4-textTertiary">
              Intake checks
            </span>
            <span className="font-mono text-[10px] text-v4-warn">
              manual gate
            </span>
          </div>
          <ul className="text-[11px]">
            {IMPORT_BLUEPRINT_CHECKS.map((check) => (
              <CheckRow key={check.label} check={check} />
            ))}
          </ul>
          <div className="mt-auto border-t border-v4-border p-3">
            <div className="text-[10px] uppercase tracking-wider text-v4-textTertiary">
              Provenance ledger
            </div>
            <div className="mt-2 grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-v4-border bg-v4-border text-[10px]">
              {[
                ["origin", "CATIA + STAR-CCM"],
                ["scale", IMPORT_BLUEPRINT_KPIS.sourceScale],
                ["parts", `${IMPORT_BLUEPRINT_KPIS.partCount}`],
                ["write mode", "manual accept"],
              ].map(([label, value]) => (
                <div key={label} className="bg-v4-surfaceRaised px-2 py-1.5">
                  <div className="text-v4-textTertiary">{label}</div>
                  <div className="mt-0.5 truncate font-mono text-v4-textPrimary">
                    {value}
                  </div>
                </div>
              ))}
            </div>
            <div
              className="mt-3 flex items-center justify-between rounded border border-v4-active/40 bg-v4-canvas px-2 py-1.5"
              data-testid="v4-import-manual-acceptance-gate"
            >
              <span className="text-[10px] text-v4-textSecondary">
                人工采纳后生成 case 草案
              </span>
              <span className="font-mono text-[10px] text-v4-active">
                READY
              </span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
