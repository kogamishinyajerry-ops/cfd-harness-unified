// Mirrors ui/backend/schemas/decisions.py + dashboard.py

import type { CaseIndexEntry } from "@/types/validation";

export type DecisionColumn = "Accepted" | "Closed" | "Open" | "Superseded";
export type GateState = "OPEN" | "CLOSED";

export interface DecisionCard {
  decision_id: string;
  title: string;
  timestamp: string;
  scope: string;
  autonomous: boolean;
  reversibility: string;
  notion_sync_status: string;
  notion_url: string | null;
  github_pr_url: string | null;
  relative_path: string;
  column: DecisionColumn;
  superseded_by: string | null;
  supersedes: string | null;
}

export interface GateQueueItem {
  qid: string;
  title: string;
  state: GateState;
  summary: string;
}

export interface DecisionsQueueResponse {
  cards: DecisionCard[];
  gate_queue: GateQueueItem[];
  counts: Record<string, number>;
}

export interface DashboardTimelineEvent {
  date: string;
  decision_id: string;
  title: string;
  column: string;
  autonomous: boolean;
  github_pr_url: string | null;
  notion_url: string | null;
}

export interface DashboardResponse {
  cases: CaseIndexEntry[];
  gate_queue: GateQueueItem[];
  timeline: DashboardTimelineEvent[];
  summary: Record<string, number>;
  current_phase: string;
  autonomous_governance_counter: number | null;
}

export interface RunCheckpoint {
  iter: number;
  t_sec: number;
  residual_Ux: number;
  residual_Uy: number;
  residual_p: number;
  phase: string;
}

export interface RunCheckpointsResponse {
  case_id: string;
  source: string;
  checkpoints: RunCheckpoint[];
}

// SSE event shape
export interface RunStreamEvent {
  iter: number;
  t_sec: number;
  residuals: { Ux: number; Uy: number; p: number } | null;
  phase: "init" | "linear_solver" | "checkpoint" | "done" | string;
  message: string;
}
