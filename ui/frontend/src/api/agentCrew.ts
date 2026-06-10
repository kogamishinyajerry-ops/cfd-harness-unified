// Agent Crew Observatory API — V93 · DEC-V93-crew-ui
// Read-only. Zero mutating calls. All data parsed from real repo artifacts.

import { ApiError } from "@/api/client";

// ── Type definitions (mirror the backend dataclasses exactly) ─────────────

export interface CrewRole {
  id: string;
  label: string;
  model: string | null;
  desc: string;
  count_label: string | null;
  count: number | null;
}

export interface CrewEdge {
  id: string;
  from: string;
  to: string;
  label: string;
}

export interface CodexRound {
  round: number;
  verdict: string;
  p1: number;
  p2: number;
  p3: number;
  report_path: string;
  missing: boolean;
}

export interface KogamiRef {
  topic: string;
  verdict: string;
}

export interface CrewArc {
  decision_id: string;
  title: string;
  date: string;
  phase: string | null;
  autonomous: boolean;
  confidence: string | null;
  loop_auditor: string | null;
  codex_relay: string | null;
  codex_rounds: CodexRound[];
  kogami: KogamiRef | null;
  relative_path: string;
}

export interface CrewStats {
  decisions_total: number;
  codex_reports_total: number;
  autonomous_total: number;
  loop_auditor_total: number;
  kogami_total: number;
}

export interface CrewSnapshot {
  roles: CrewRole[];
  edges: CrewEdge[];
  arcs: CrewArc[];
  stats: CrewStats;
}

export interface ArcReportEntry {
  round: number;
  path: string;
  excerpt: string;
  verdict: string;
  missing: boolean;
}

export interface ArcDetail {
  decision_id: string;
  frontmatter: Record<string, string>;
  body_excerpt: string;
  reports: ArcReportEntry[];
}

// ── Fetch helpers ─────────────────────────────────────────────────────────

async function request<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, body || response.statusText);
  }
  return (await response.json()) as T;
}

export const agentCrewApi = {
  getCrewSnapshot: () => request<CrewSnapshot>("/api/agent-crew"),
  getArcDetail: (decisionId: string) =>
    request<ArcDetail>(
      `/api/agent-crew/arc/${encodeURIComponent(decisionId)}`,
    ),
};
