// CaseFrame · Stage 2 MVP first-screen for /learn/cases/<id>.
//
// Per Codex industrial-workbench meeting 2026-04-25 (transcript:
// reports/codex_tool_reports/industrial_workbench_meeting_2026-04-25.md).
// David's Stage 2 directive: "只做 workbench-basics endpoint + CaseFrame
// 首屏" — geometry topology, patch color-coding, materials strip, BC
// pin-map, solver + characteristic Re anchored prominently.
//
// Anti-pattern guard (Codex meeting §5): do NOT mirror StoryTab prose
// here. Long-form pedagogical narrative belongs in StoryTab. CaseFrame
// is the tabular / topological "看就懂" surface. Hints are intentionally
// terse.
//
// Bundle target: ≤12 KB raw. No chart/3D libs — pure SVG + Tailwind.

import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import type {
  BoundaryCondition,
  BoundaryConditionPatch,
  Geometry,
  Patch,
  PatchRole,
  WorkbenchBasics,
} from "@/types/workbench_basics";

// --- Role color palette ---------------------------------------------------
// Color choices follow domain convention (driver = warm/active, walls =
// neutral, empty = de-emphasized) and the harness's existing surface-* /
// contract-pass / amber Tailwind tokens.

const ROLE_FILL: Record<PatchRole, string> = {
  moving_wall: "#06b6d4", // cyan-500 — energy source / driver
  wall: "#475569", // slate-600 — passive no-slip
  inlet: "#10b981", // emerald-500 — incoming flux
  outlet: "#f59e0b", // amber-500 — outgoing flux
  symmetry: "#8b5cf6", // violet-500
  cyclic: "#ec4899", // pink-500 — periodicity pair
  empty: "#1f2937", // slate-800 — 2D virtual face
  airfoil: "#a855f7", // purple-500
  periodic: "#ec4899",
};

const ROLE_LABEL_ZH: Record<PatchRole, string> = {
  moving_wall: "移动壁",
  wall: "壁面",
  inlet: "入口",
  outlet: "出口",
  symmetry: "对称",
  cyclic: "循环",
  empty: "2D empty",
  airfoil: "翼面",
  periodic: "周期",
};

// --- Top-level component --------------------------------------------------

export function CaseFrame({ caseId }: { caseId: string }) {
  const { data, error, isLoading } = useQuery<WorkbenchBasics, ApiError>({
    queryKey: ["workbench-basics", caseId],
    queryFn: () => api.getWorkbenchBasics(caseId),
    enabled: !!caseId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="mb-8 h-[280px] animate-pulse rounded-md border border-surface-800 bg-surface-900/40" />
    );
  }

  // 404 = not yet authored. Soft skip (don't block the rest of the page).
  // Stage 2 trigger close requires ≥8 of 10 cases populated; until then,
  // older cases show the existing hero illustration only.
  if (error?.status === 404) {
    return null;
  }

  if (error) {
    return (
      <div className="mb-8 rounded-md border border-amber-700/60 bg-amber-950/30 p-4 text-[12px] text-amber-200">
        ⚠ workbench-basics 加载失败：{error.message}
      </div>
    );
  }

  if (!data) return null;

  return (
    <section className="mb-10 rounded-lg border border-surface-800 bg-surface-950/40 p-5">
      {data.schema_drift_warning && (
        <div className="mb-3 rounded-sm border border-amber-700/60 bg-amber-950/40 p-2 text-[11px] text-amber-200">
          ⚠ schema drift: {data.schema_drift_warning}
        </div>
      )}

      <div className="mb-4 flex items-baseline justify-between">
        <p className="card-title">工作台 · 案例首屏</p>
        <span className="mono text-[10px] uppercase tracking-wider text-surface-600">
          workbench-basics · v1
        </span>
      </div>

      <div className="grid gap-5 md:grid-cols-[1fr_280px]">
        <GeometryPanel
          geometry={data.geometry}
          patches={data.patches}
          dimension={data.dimension}
        />
        <PhysicsAnchor data={data} />
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <BoundaryConditionTable
          boundaryConditions={data.boundary_conditions}
          patches={data.patches}
        />
        <MaterialsAndSolver data={data} />
      </div>

      {data.hints && <HintsRow hints={data.hints} />}
    </section>
  );
}

// --- Geometry topology panel ---------------------------------------------

function GeometryPanel({
  geometry,
  patches,
  dimension,
}: {
  geometry: Geometry;
  patches: Patch[];
  dimension: number;
}) {
  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <p className="text-[12px] font-medium uppercase tracking-wider text-surface-400">
          几何 · {geometry.shape}
        </p>
        <span className="mono text-[10px] text-surface-500">
          {dimension}D · L={geometry.characteristic_length.value}
          {geometry.characteristic_length.unit}
        </span>
      </div>

      {geometry.shape === "rectangle" ? (
        <RectangleSVG geometry={geometry} patches={patches} />
      ) : (
        <UnsupportedShapeStub shape={geometry.shape} patches={patches} />
      )}

      <PatchLegend patches={patches} />
    </div>
  );
}

// --- Rectangle renderer (LDC, channel, RBC, DHC, ...) --------------------

function RectangleSVG({
  geometry,
  patches,
}: {
  geometry: Geometry;
  patches: Patch[];
}) {
  const VW = 320;
  const VH = 200;
  const PAD = 36;

  const dx = geometry.bbox.x_max - geometry.bbox.x_min;
  const dy = geometry.bbox.y_max - geometry.bbox.y_min;
  const aspect = dx > 0 && dy > 0 ? dx / dy : 1;
  // Fit rectangle into viewport, preserving aspect.
  let rw = VW - 2 * PAD;
  let rh = rw / aspect;
  if (rh > VH - 2 * PAD) {
    rh = VH - 2 * PAD;
    rw = rh * aspect;
  }
  const rx = (VW - rw) / 2;
  const ry = (VH - rh) / 2;

  // Edge centers for label anchoring.
  const edgeCenter = (loc: string) => {
    switch (loc) {
      case "top":
        return { x: rx + rw / 2, y: ry, anchor: "middle", baseline: "auto" };
      case "bottom":
        return {
          x: rx + rw / 2,
          y: ry + rh,
          anchor: "middle",
          baseline: "hanging",
        };
      case "left":
        return { x: rx, y: ry + rh / 2, anchor: "end", baseline: "central" };
      case "right":
        return {
          x: rx + rw,
          y: ry + rh / 2,
          anchor: "start",
          baseline: "central",
        };
      default:
        return null;
    }
  };

  // Find each edge patch (the 4 visible faces of the 2D rectangle).
  const onEdge = patches.filter((p) =>
    ["top", "bottom", "left", "right"].includes(p.location),
  );
  const offEdge = patches.filter(
    (p) => !["top", "bottom", "left", "right"].includes(p.location),
  );

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${VW} ${VH}`}
        className="w-full"
        style={{ maxHeight: "220px" }}
        role="img"
        aria-label={`${geometry.shape} domain topology`}
      >
        {/* Domain fill */}
        <rect
          x={rx}
          y={ry}
          width={rw}
          height={rh}
          fill="#0f172a"
          stroke="#334155"
          strokeWidth="1"
        />

        {/* Each edge colored by its patch role */}
        {onEdge.map((p) => {
          const fill = ROLE_FILL[p.role] ?? "#475569";
          const t = 4; // edge thickness
          if (p.location === "top") {
            return (
              <rect
                key={p.id}
                x={rx}
                y={ry - t / 2}
                width={rw}
                height={t}
                fill={fill}
              />
            );
          }
          if (p.location === "bottom") {
            return (
              <rect
                key={p.id}
                x={rx}
                y={ry + rh - t / 2}
                width={rw}
                height={t}
                fill={fill}
              />
            );
          }
          if (p.location === "left") {
            return (
              <rect
                key={p.id}
                x={rx - t / 2}
                y={ry}
                width={t}
                height={rh}
                fill={fill}
              />
            );
          }
          if (p.location === "right") {
            return (
              <rect
                key={p.id}
                x={rx + rw - t / 2}
                y={ry}
                width={t}
                height={rh}
                fill={fill}
              />
            );
          }
          return null;
        })}

        {/* Driver arrow if any patch is moving_wall — visualizes shear injection */}
        {onEdge
          .filter((p) => p.role === "moving_wall")
          .map((p) => {
            const c = edgeCenter(p.location);
            if (!c) return null;
            // Always draw a horizontal arrow on the edge for now (LDC-style).
            const arrowY = c.y;
            return (
              <g key={`${p.id}-arrow`}>
                <line
                  x1={rx + 12}
                  y1={arrowY}
                  x2={rx + rw - 12}
                  y2={arrowY}
                  stroke="#06b6d4"
                  strokeWidth="1.4"
                  markerEnd="url(#arrowhead)"
                />
              </g>
            );
          })}

        {/* Labels */}
        {onEdge.map((p) => {
          const c = edgeCenter(p.location);
          if (!c) return null;
          const offset = 12;
          const lx =
            p.location === "top"
              ? c.x
              : p.location === "bottom"
                ? c.x
                : p.location === "left"
                  ? c.x - offset
                  : c.x + offset;
          const ly =
            p.location === "top"
              ? c.y - offset
              : p.location === "bottom"
                ? c.y + offset
                : c.y;
          return (
            <text
              key={`${p.id}-label`}
              x={lx}
              y={ly}
              fontSize="11"
              fontWeight="500"
              textAnchor={c.anchor as "start" | "middle" | "end"}
              dominantBaseline={
                c.baseline as "auto" | "hanging" | "central" | "middle"
              }
              fill={ROLE_FILL[p.role] ?? "#cbd5e1"}
              className="select-none"
            >
              {p.label_zh}
            </text>
          );
        })}

        {/* Origin tick + bbox dimensions */}
        <text
          x={rx - 4}
          y={ry + rh + 14}
          fontSize="9"
          textAnchor="end"
          fill="#64748b"
          className="mono"
        >
          ({geometry.bbox.x_min},{geometry.bbox.y_min})
        </text>
        <text
          x={rx + rw + 4}
          y={ry - 4}
          fontSize="9"
          textAnchor="start"
          fill="#64748b"
          className="mono"
        >
          ({geometry.bbox.x_max},{geometry.bbox.y_max})
        </text>

        <defs>
          <marker
            id="arrowhead"
            markerWidth="6"
            markerHeight="6"
            refX="5"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6 Z" fill="#06b6d4" />
          </marker>
        </defs>
      </svg>

      {offEdge.length > 0 && (
        <p className="mt-1 text-[10px] text-surface-500">
          其他面：
          {offEdge.map((p, i) => (
            <span key={p.id}>
              {i > 0 && " / "}
              <span className="mono">{p.id}</span>
              <span className="ml-1 text-surface-600">
                ({ROLE_LABEL_ZH[p.role] ?? p.role})
              </span>
            </span>
          ))}
        </p>
      )}
    </div>
  );
}

function UnsupportedShapeStub({
  shape,
  patches,
}: {
  shape: string;
  patches: Patch[];
}) {
  return (
    <div className="rounded-sm border border-dashed border-surface-700 bg-surface-950 p-6 text-center">
      <p className="mono text-[12px] text-surface-400">
        几何形状 <span className="text-surface-200">{shape}</span> 的 SVG 渲染待
        Stage 2 后续 commit
      </p>
      <p className="mt-2 text-[11px] text-surface-500">
        当前共 {patches.length} 个 patch，已在右下角 BC 表中列出。
      </p>
    </div>
  );
}

function PatchLegend({ patches }: { patches: Patch[] }) {
  // Unique role list, in declaration order.
  const seen = new Set<string>();
  const ordered: Patch[] = [];
  for (const p of patches) {
    if (!seen.has(p.role)) {
      seen.add(p.role);
      ordered.push(p);
    }
  }
  return (
    <div className="mt-3 flex flex-wrap gap-3 text-[10px]">
      {ordered.map((p) => (
        <span key={p.role} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-2 w-3"
            style={{ backgroundColor: ROLE_FILL[p.role] ?? "#475569" }}
          />
          <span className="text-surface-400">
            {ROLE_LABEL_ZH[p.role] ?? p.role}
          </span>
        </span>
      ))}
    </div>
  );
}

// --- Physics anchor (Re, ν, ρ, L, solver) -------------------------------

function PhysicsAnchor({ data }: { data: WorkbenchBasics }) {
  const reCandidate = data.derived.find(
    (d) =>
      d.symbol.toLowerCase() === "re" ||
      d.name.toLowerCase().includes("reynolds"),
  );
  const otherDerived = data.derived.filter((d) => d !== reCandidate);
  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
      <p className="text-[12px] font-medium uppercase tracking-wider text-surface-400">
        物理锚点
      </p>
      {reCandidate && (
        <div className="mt-3">
          <div className="flex items-baseline gap-2">
            <span className="mono text-[11px] text-surface-500">
              {reCandidate.symbol}
            </span>
            <span className="text-3xl font-semibold leading-none text-sky-300">
              {formatNum(reCandidate.value)}
            </span>
          </div>
          <p className="mt-1 mono text-[10px] text-surface-500">
            {reCandidate.formula}
          </p>
          {reCandidate.note_zh && (
            <p className="mt-1 text-[11px] text-surface-400">
              {reCandidate.note_zh}
            </p>
          )}
        </div>
      )}
      {otherDerived.length > 0 && (
        <div className="mt-3 space-y-1.5 border-t border-surface-800 pt-3">
          {otherDerived.map((d) => (
            <div
              key={d.symbol + d.name}
              className="flex items-baseline justify-between text-[11px]"
            >
              <span className="mono text-surface-500">{d.symbol}</span>
              <span className="mono text-surface-200">{formatNum(d.value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Boundary condition pin-map ------------------------------------------

function BoundaryConditionTable({
  boundaryConditions,
  patches,
}: {
  boundaryConditions: BoundaryCondition[];
  patches: Patch[];
}) {
  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
      <p className="mb-3 text-[12px] font-medium uppercase tracking-wider text-surface-400">
        边界条件 · BC pin-map
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[11px]">
          <thead>
            <tr className="border-b border-surface-800">
              <th className="pb-1.5 pr-2 font-normal text-surface-500">patch</th>
              {boundaryConditions.map((bc) => (
                <th
                  key={bc.field}
                  className="pb-1.5 pr-2 font-normal text-surface-500"
                >
                  <span className="mono text-surface-200">{bc.field}</span>
                  <span className="ml-1 text-surface-600">{bc.units}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {patches.map((p) => (
              <tr key={p.id} className="border-b border-surface-900">
                <td className="py-1.5 pr-2">
                  <span className="mono text-surface-200">{p.id}</span>
                  <span
                    className="ml-1.5 inline-block h-2 w-2 rounded-sm align-middle"
                    style={{ backgroundColor: ROLE_FILL[p.role] ?? "#475569" }}
                    title={ROLE_LABEL_ZH[p.role] ?? p.role}
                  />
                </td>
                {boundaryConditions.map((bc) => (
                  <td
                    key={bc.field}
                    className="py-1.5 pr-2 mono text-surface-300"
                  >
                    {renderBcCell(bc.per_patch[p.id])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function renderBcCell(bc: BoundaryConditionPatch | undefined) {
  if (!bc) return <span className="text-surface-700">—</span>;
  if (bc.display_zh) {
    return (
      <span>
        <span className="text-surface-500">{bc.type}</span>
        <span className="mx-1 text-surface-700">·</span>
        <span className="text-surface-200">{bc.display_zh}</span>
      </span>
    );
  }
  return <span className="text-surface-300">{bc.type}</span>;
}

// --- Materials + solver ---------------------------------------------------

function MaterialsAndSolver({ data }: { data: WorkbenchBasics }) {
  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
      <p className="mb-3 text-[12px] font-medium uppercase tracking-wider text-surface-400">
        物性 + 求解器
      </p>
      {data.materials.map((m) => (
        <div key={m.id} className="mb-3 last:mb-0">
          <p className="text-[11px] text-surface-300">{m.label_zh}</p>
          <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1">
            {m.properties.map((prop) => (
              <div
                key={prop.symbol + prop.name}
                className="flex items-baseline justify-between border-b border-surface-900 py-0.5 text-[11px]"
              >
                <span className="mono text-surface-500">{prop.symbol}</span>
                <span className="mono text-surface-200">
                  {formatNum(prop.value)}{" "}
                  <span className="text-surface-600">{prop.unit}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
      {data.solver && (
        <div className="mt-3 border-t border-surface-800 pt-3">
          <p className="text-[11px] text-surface-300">
            <span className="mono text-sky-300">{data.solver.name}</span>
            <span className="mx-1.5 text-surface-700">·</span>
            <span className="text-surface-400">{data.solver.display_zh}</span>
          </p>
          <p className="mt-1 text-[10px] text-surface-500">
            {data.solver.reasoning_zh}
          </p>
        </div>
      )}
    </div>
  );
}

// --- Hints row ------------------------------------------------------------

function HintsRow({
  hints,
}: {
  hints: NonNullable<WorkbenchBasics["hints"]>;
}) {
  const items = [
    { key: "geometry", label: "几何", value: hints.geometry_zh },
    { key: "driver", label: "驱动", value: hints.driver_zh },
    { key: "intuition", label: "直觉", value: hints.physical_intuition_zh },
  ].filter((it): it is { key: string; label: string; value: string } =>
    Boolean(it.value),
  );
  if (items.length === 0) return null;
  return (
    <div className="mt-5 grid gap-3 rounded-sm border border-surface-800 bg-surface-950 p-3 md:grid-cols-3">
      {items.map((it) => (
        <div key={it.key}>
          <p className="text-[10px] uppercase tracking-wider text-surface-600">
            {it.label}
          </p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-surface-400">
            {it.value}
          </p>
        </div>
      ))}
    </div>
  );
}

// --- Helpers --------------------------------------------------------------

function formatNum(v: number): string {
  if (!Number.isFinite(v)) return String(v);
  const abs = Math.abs(v);
  if (abs === 0) return "0";
  if (abs >= 1000 || abs < 0.001) return v.toExponential(2);
  // Trim trailing zeros after at most 4 sig figs.
  return Number(v.toPrecision(4)).toString();
}
