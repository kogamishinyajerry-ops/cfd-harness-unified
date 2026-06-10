// TopologyGraph — pure SVG agent topology. No third-party graph lib.
// V93 · Agent Crew Observatory

import type { CrewRole, CrewEdge } from "@/api/agentCrew";

// Fixed node positions (cx, cy) in a 340×440 viewport
const NODE_POS: Record<string, { cx: number; cy: number }> = {
  sponsor: { cx: 170, cy: 36 },
  chief: { cx: 170, cy: 160 },
  workers: { cx: 70, cy: 300 },
  codex: { cx: 280, cy: 220 },
  loop_auditor: { cx: 290, cy: 80 },
  kogami: { cx: 290, cy: 36 },
  archive: { cx: 170, cy: 400 },
};

const NODE_W = 90;
const NODE_H = 40;

function nodeRect(id: string) {
  const p = NODE_POS[id];
  if (!p) return null;
  return { x: p.cx - NODE_W / 2, y: p.cy - NODE_H / 2, w: NODE_W, h: NODE_H };
}

// Arrow marker path — used by all edges
function ArrowDef() {
  return (
    <defs>
      <marker
        id="arrow-gray"
        markerWidth="8"
        markerHeight="8"
        refX="6"
        refY="3"
        orient="auto"
      >
        <path d="M0,0 L0,6 L8,3 z" fill="#5A6471" />
      </marker>
      <marker
        id="arrow-active"
        markerWidth="8"
        markerHeight="8"
        refX="6"
        refY="3"
        orient="auto"
      >
        <path d="M0,0 L0,6 L8,3 z" fill="#F0A93B" />
      </marker>
    </defs>
  );
}

// Compute a simple cubic bezier from src to dst, slightly curved
function edgePath(fromId: string, toId: string): string {
  const src = NODE_POS[fromId];
  const dst = NODE_POS[toId];
  if (!src || !dst) return "";
  const mx = (src.cx + dst.cx) / 2;
  const my = (src.cy + dst.cy) / 2;
  // Small perpendicular offset for curvature
  const dx = dst.cx - src.cx;
  const dy = dst.cy - src.cy;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const ox = (-dy / len) * 20;
  const oy = (dx / len) * 20;
  return `M${src.cx},${src.cy} Q${mx + ox},${my + oy} ${dst.cx},${dst.cy}`;
}

// Mid-point along a quadratic bezier at t=0.5
function bezierMid(fromId: string, toId: string): { x: number; y: number } {
  const src = NODE_POS[fromId];
  const dst = NODE_POS[toId];
  if (!src || !dst) return { x: 0, y: 0 };
  const mx = (src.cx + dst.cx) / 2;
  const my = (src.cy + dst.cy) / 2;
  const dx = dst.cx - src.cx;
  const dy = dst.cy - src.cy;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const ox = (-dy / len) * 20;
  const oy = (dx / len) * 20;
  // B(0.5) = 0.25*P0 + 0.5*P1 + 0.25*P2
  return {
    x: 0.25 * src.cx + 0.5 * (mx + ox) + 0.25 * dst.cx,
    y: 0.25 * src.cy + 0.5 * (my + oy) + 0.25 * dst.cy,
  };
}

interface TopologyGraphProps {
  roles: CrewRole[];
  edges: CrewEdge[];
  activeEdgeIds: string[];
  onSelectRole?: (id: string) => void;
}

export function TopologyGraph({
  roles,
  edges,
  activeEdgeIds,
  onSelectRole,
}: TopologyGraphProps) {
  return (
    <div className="flex flex-col">
      <h2 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-v4-textSecondary">
        Agent 拓扑
      </h2>
      <svg
        viewBox="0 0 340 440"
        className="w-full max-w-[340px] rounded-md border border-v4-border bg-v4-surface"
        aria-label="Agent crew topology graph"
      >
        <ArrowDef />

        {/* Edges */}
        {edges.map((e) => {
          const active = activeEdgeIds.includes(e.id);
          const d = edgePath(e.from, e.to);
          const mid = bezierMid(e.from, e.to);
          return (
            <g key={e.id}>
              <path
                d={d}
                fill="none"
                strokeWidth={active ? 2 : 1}
                stroke={active ? "#F0A93B" : "#3a495f"}
                markerEnd={`url(#arrow-${active ? "active" : "gray"})`}
                strokeDasharray={active ? "6 3" : undefined}
                className={active ? "animate-pulse" : undefined}
              />
              <text
                x={mid.x}
                y={mid.y}
                fontSize={7}
                fill={active ? "#F0A93B" : "#5A6471"}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {e.label}
              </text>
            </g>
          );
        })}

        {/* Nodes */}
        {roles.map((role) => {
          const rect = nodeRect(role.id);
          if (!rect) return null;
          const isOptIn = role.id === "kogami";
          return (
            <g
              key={role.id}
              onClick={() => onSelectRole?.(role.id)}
              style={{ cursor: onSelectRole ? "pointer" : "default" }}
              role="button"
              aria-label={role.label}
            >
              <rect
                x={rect.x}
                y={rect.y}
                width={rect.w}
                height={rect.h}
                rx={4}
                fill="#161C24"
                stroke={isOptIn ? "#3a495f" : "#222932"}
                strokeWidth={isOptIn ? 1 : 1}
                strokeDasharray={isOptIn ? "4 2" : undefined}
              />
              <text
                x={rect.x + rect.w / 2}
                y={rect.y + 13}
                fontSize={8}
                fontWeight="600"
                fill="#E8ECF1"
                textAnchor="middle"
              >
                {role.label}
              </text>
              {role.model && (
                <text
                  x={rect.x + rect.w / 2}
                  y={rect.y + 23}
                  fontSize={6}
                  fill="#5A6471"
                  textAnchor="middle"
                >
                  {role.model.length > 20
                    ? role.model.slice(0, 19) + "…"
                    : role.model}
                </text>
              )}
              {role.count_label != null && role.count != null && (
                <text
                  x={rect.x + rect.w / 2}
                  y={rect.y + 33}
                  fontSize={6}
                  fill="#3DC97F"
                  textAnchor="middle"
                >
                  {role.count_label}: {role.count}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <p className="mt-1.5 text-[9px] text-v4-textTertiary">
        虚线边框 = opt-in 角色（Kogami 战略层）
      </p>
    </div>
  );
}
