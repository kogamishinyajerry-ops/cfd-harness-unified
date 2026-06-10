// AgentCrewPage tests — V93 · Agent Crew Observatory
// Locks: 7 role nodes visible · stats chips · arc replay steps ·
// verdict badge colors · UNPARSED grey badge · read-only (no POST).

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { CrewSnapshot, ArcDetail } from "@/api/agentCrew";

// Hoist mock before any imports that use @/api/agentCrew
const agentCrewMock = vi.hoisted(() => ({
  getCrewSnapshot: vi.fn(),
  getArcDetail: vi.fn(),
}));
vi.mock("@/api/agentCrew", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/agentCrew")>();
  return {
    ...actual,
    agentCrewApi: agentCrewMock,
  };
});

import { AgentCrewPage } from "../AgentCrewPage";

function makeSnapshot(overrides: Partial<CrewSnapshot> = {}): CrewSnapshot {
  return {
    roles: [
      { id: "sponsor", label: "用户 · Sponsor", model: null, desc: "d", count_label: null, count: null },
      { id: "chief", label: "Claude 总师", model: "Opus / Fable · 主驱动", desc: "d", count_label: "autonomous DECs", count: 5 },
      { id: "workers", label: "Subagents · 施工/侦察", model: "Sonnet / Haiku / Workflow", desc: "d", count_label: null, count: null },
      { id: "codex", label: "Codex 异源审查", model: "GPT-5.4 xhigh · 86gs relay", desc: "d", count_label: "审查报告", count: 10 },
      { id: "loop_auditor", label: "loop-auditor 闭环审计", model: "只读 agent", desc: "d", count_label: "标注 DECs", count: 3 },
      { id: "kogami", label: "Kogami 战略层", model: "claude -p 隔离子进程", desc: "d", count_label: "invocations", count: 1 },
      { id: "archive", label: "Git · DEC 档案", model: null, desc: "d", count_label: "决策文件", count: 443 },
    ],
    edges: [
      { id: "e1", from: "sponsor", to: "chief", label: "目标 / 裁决" },
      { id: "e2", from: "chief", to: "workers", label: "委派" },
      { id: "e3", from: "workers", to: "chief", label: "汇报" },
      { id: "e4", from: "chief", to: "codex", label: "审查" },
      { id: "e5", from: "codex", to: "chief", label: "verdict" },
      { id: "e6", from: "loop_auditor", to: "chief", label: "FLAG" },
      { id: "e7", from: "sponsor", to: "kogami", label: "opt-in" },
      { id: "e8", from: "chief", to: "archive", label: "DEC + commit" },
      { id: "e9", from: "kogami", to: "archive", label: "review" },
    ],
    arcs: [
      {
        decision_id: "DEC-V61-238",
        title: "Test Arc Title",
        date: "2026-06-10",
        phase: "phase-test",
        autonomous: true,
        confidence: "high",
        loop_auditor: "FLAG",
        codex_relay: "yes",
        codex_rounds: [
          { round: 0, verdict: "CHANGES_REQUIRED", p1: 1, p2: 2, p3: 0, report_path: "reports/x_R0.md", missing: false },
          { round: 1, verdict: "APPROVE", p1: 0, p2: 0, p3: 0, report_path: "reports/x_R1.md", missing: false },
        ],
        kogami: null,
        relative_path: ".planning/decisions/2026-06-10_test.md",
      },
      {
        decision_id: "DEC-V61-239",
        title: "Another Arc with UNPARSED verdict",
        date: "2026-06-09",
        phase: null,
        autonomous: false,
        confidence: null,
        loop_auditor: null,
        codex_relay: null,
        codex_rounds: [
          { round: 0, verdict: "UNPARSED", p1: 0, p2: 0, p3: 0, report_path: "reports/y_R0.md", missing: false },
        ],
        kogami: null,
        relative_path: ".planning/decisions/2026-06-09_test.md",
      },
    ],
    stats: {
      decisions_total: 443,
      codex_reports_total: 154,
      autonomous_total: 42,
      loop_auditor_total: 7,
      kogami_total: 2,
    },
    ...overrides,
  };
}

function makeDetail(): ArcDetail {
  return {
    decision_id: "DEC-V61-238",
    frontmatter: { status: "Accepted", autonomous_governance: "true" },
    body_excerpt: "# Test DEC\nBody text here.",
    reports: [
      { round: 0, path: "reports/x_R0.md", excerpt: "CHANGES_REQUIRED found 1 P1", verdict: "CHANGES_REQUIRED", missing: false },
      { round: 1, path: "reports/x_R1.md", excerpt: "APPROVE all fixed", verdict: "APPROVE", missing: false },
    ],
  };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AgentCrewPage />
    </QueryClientProvider>,
  );
}

describe("AgentCrewPage", () => {
  beforeEach(() => {
    agentCrewMock.getCrewSnapshot.mockReset();
    agentCrewMock.getArcDetail.mockReset();
  });

  it("renders all 7 role node labels from the snapshot", async () => {
    agentCrewMock.getCrewSnapshot.mockResolvedValue(makeSnapshot());
    renderPage();
    const labels = [
      "用户 · Sponsor",
      "Claude 总师",
      "Subagents · 施工/侦察",
      "Codex 异源审查",
      "loop-auditor 闭环审计",
      "Kogami 战略层",
      "Git · DEC 档案",
    ];
    for (const label of labels) {
      await waitFor(() =>
        expect(screen.getByText(label)).toBeInTheDocument(),
      );
    }
  });

  it("displays stats chips with mock numbers (no hardcoding)", async () => {
    agentCrewMock.getCrewSnapshot.mockResolvedValue(makeSnapshot());
    renderPage();
    // The stats numbers come from the mock, not hardcoded
    await waitFor(() => {
      expect(screen.getByText("443")).toBeInTheDocument();
      expect(screen.getByText("154")).toBeInTheDocument();
      expect(screen.getByText("42")).toBeInTheDocument();
    });
  });

  it("clicking an arc row shows the replay with R0 / R1 steps", async () => {
    agentCrewMock.getCrewSnapshot.mockResolvedValue(makeSnapshot());
    agentCrewMock.getArcDetail.mockResolvedValue(makeDetail());
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("DEC-V61-238")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText("DEC-V61-238"));

    // ArcReplay should appear — it has a "协作回路回放" heading
    await waitFor(() =>
      expect(screen.getByText(/协作回路回放/)).toBeInTheDocument(),
    );

    // Codex step labels should be present
    expect(screen.getByText(/Codex R0/)).toBeInTheDocument();
    expect(screen.getByText(/Codex R1/)).toBeInTheDocument();
  });

  it("CHANGES_REQUIRED verdict shows amber badge; APPROVE shows healthy badge", async () => {
    agentCrewMock.getCrewSnapshot.mockResolvedValue(makeSnapshot());
    agentCrewMock.getArcDetail.mockResolvedValue(makeDetail());
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("DEC-V61-238")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText("DEC-V61-238"));

    await waitFor(() =>
      expect(screen.getByText(/Codex R0/)).toBeInTheDocument(),
    );

    // CHANGES_REQUIRED badge should have amber class
    const crBadge = screen.getAllByText("CHANGES_REQUIRED")[0];
    expect(crBadge.className).toMatch(/v4-active/);

    // APPROVE badge should have healthy class
    const approveBadge = screen.getAllByText("APPROVE")[0];
    expect(approveBadge.className).toMatch(/v4-healthy/);
  });

  it("UNPARSED verdict shows a grey badge", async () => {
    agentCrewMock.getCrewSnapshot.mockResolvedValue(makeSnapshot());
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("DEC-V61-239")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText("DEC-V61-239"));

    await waitFor(() =>
      expect(screen.getByText(/協作回路回放|协作回路回放/)).toBeInTheDocument(),
    );

    // VerdictDot for UNPARSED should be grey (bg-surface-500)
    const dots = document.querySelectorAll(".bg-surface-500");
    expect(dots.length).toBeGreaterThan(0);
  });

  it("page has no button that would trigger a POST request", async () => {
    agentCrewMock.getCrewSnapshot.mockResolvedValue(makeSnapshot());
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("用户 · Sponsor")).toBeInTheDocument(),
    );

    // No form submit button, no element with data-method="post"
    const forms = document.querySelectorAll("form");
    for (const form of forms) {
      expect(form.getAttribute("method")?.toLowerCase() ?? "get").not.toBe("post");
    }

    // All buttons should be type="button" (not submit), or no buttons at all
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    expect(submitButtons.length).toBe(0);
  });
});

// ---------- step honesty (Codex V93 R0 P2) ----------------------------------
// 步骤只从真实工件推导：末轮非放行 verdict 之后不得虚构「总师修复」，
// 也不得显示「收口」。
import { ArcReplay } from "../components/ArcReplay";
import type { CrewArc } from "@/api/agentCrew";

function arcWithRounds(rounds: CrewArc["codex_rounds"]): CrewArc {
  return {
    decision_id: "DEC-TEST-1",
    title: "t",
    date: "2026-06-10",
    phase: null,
    autonomous: true,
    confidence: "high",
    loop_auditor: null,
    codex_relay: null,
    codex_rounds: rounds,
    kogami: null,
    relative_path: "x.md",
  };
}

describe("ArcReplay step honesty", () => {
  it("does NOT fabricate a fix step after a final CHANGES_REQUIRED round", () => {
    render(
      <ArcReplay
        arc={arcWithRounds([
          { round: 0, verdict: "CHANGES_REQUIRED", p1: 1, p2: 0, p3: 0, report_path: "r0.md", missing: false },
        ])}
        onActiveEdgesChange={() => {}}
      />,
    );
    expect(screen.queryByText(/总师修复/)).toBeNull();
    expect(screen.queryByText(/收口 \/ 归档/)).toBeNull();
    expect(screen.getByText(/未收口 · 最后一轮 CHANGES_REQUIRED/)).toBeTruthy();
  });

  it("inserts a fix step only BETWEEN rounds and closes on final APPROVE", () => {
    render(
      <ArcReplay
        arc={arcWithRounds([
          { round: 0, verdict: "CHANGES_REQUIRED", p1: 1, p2: 0, p3: 0, report_path: "r0.md", missing: false },
          { round: 1, verdict: "APPROVE", p1: 0, p2: 0, p3: 0, report_path: "r1.md", missing: false },
        ])}
        onActiveEdgesChange={() => {}}
      />,
    );
    expect(screen.getAllByText(/总师修复 \(after R0\)/).length).toBe(1);
    expect(screen.getByText(/收口 \/ 归档/)).toBeTruthy();
    expect(screen.queryByText(/未收口/)).toBeNull();
  });

  it("a final MISSING round is reported unresolved, never closed", () => {
    render(
      <ArcReplay
        arc={arcWithRounds([
          { round: 0, verdict: "MISSING", p1: 0, p2: 0, p3: 0, report_path: "gone.md", missing: true },
        ])}
        onActiveEdgesChange={() => {}}
      />,
    );
    expect(screen.queryByText(/总师修复/)).toBeNull();
    expect(screen.getByText(/未收口 · 最后一轮 MISSING/)).toBeTruthy();
  });
});
