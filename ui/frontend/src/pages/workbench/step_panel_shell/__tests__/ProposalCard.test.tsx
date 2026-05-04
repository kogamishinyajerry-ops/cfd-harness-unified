// DEC-V61-121 · ProposalCard tests.

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { ApplyAIProposalResponse } from "@/api/client";
import { ApiError } from "@/api/client";

import type { ParsedProposal } from "../proposal_parser";

const apiMock = vi.hoisted(() => ({
  applyAIProposal: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    applyAIProposal: apiMock.applyAIProposal,
  };
});

import { ProposalCard } from "../ProposalCard";

beforeEach(() => {
  apiMock.applyAIProposal.mockReset();
});

function buildProposal(
  overrides: Partial<ParsedProposal> = {},
): ParsedProposal {
  return {
    index: 0,
    tool: "set_patch_bc_type",
    args: { patch_name: "walls", bc_class: "no_slip_wall" },
    reason: "walls should be no-slip",
    ok: true,
    rawYaml: "tool: set_patch_bc_type\nargs:\n  patch_name: walls\n",
    ...overrides,
  };
}

function buildOkResponse(
  overrides: Partial<ApplyAIProposalResponse> = {},
): ApplyAIProposalResponse {
  return {
    applied: true,
    tool: "set_patch_bc_type",
    summary: "Set patch 'walls' BC class to 'no_slip_wall'.",
    state_after: { overrides: { walls: "no_slip_wall" } },
    audit_id: "abc123",
    ...overrides,
  };
}

describe("ProposalCard", () => {
  it("renders tool, reason, and args by default", () => {
    render(
      <ProposalCard
        caseId="ldc"
        proposal={buildProposal()}
        modelUsed="deepseek-v4-pro"
        turnId="a-1"
      />,
    );
    const card = screen.getByTestId("proposal-card-0");
    expect(card).toHaveAttribute("data-card-state", "idle");
    expect(card).toHaveAttribute("data-tool", "set_patch_bc_type");
    expect(card).toHaveTextContent("walls should be no-slip");
    expect(screen.getByTestId("proposal-card-args-0")).toHaveTextContent(
      "patch_name",
    );
  });

  it("renders malformed warning when proposal.ok is false", () => {
    render(
      <ProposalCard
        caseId="ldc"
        proposal={buildProposal({
          ok: false,
          tool: null,
          args: null,
          malformedReason: "PROPOSAL missing required keys: tool, args",
        })}
        modelUsed={null}
        turnId="a-1"
      />,
    );
    const card = screen.getByTestId("proposal-card-0");
    expect(card).toHaveAttribute("data-card-state", "malformed");
    expect(card).toHaveTextContent("AI 提案格式有误");
    expect(card).toHaveTextContent("missing required keys");
    expect(screen.queryByTestId("proposal-card-accept-0")).not.toBeInTheDocument();
  });

  it("Accept transitions idle → applying → applied and shows the summary", async () => {
    let resolveApply: (val: ApplyAIProposalResponse) => void = () => {};
    apiMock.applyAIProposal.mockImplementation(
      () => new Promise((res) => (resolveApply = res)),
    );

    const user = userEvent.setup();
    const onApplied = vi.fn();
    render(
      <ProposalCard
        caseId="ldc"
        proposal={buildProposal()}
        modelUsed="deepseek-v4-pro"
        turnId="a-1"
        onApplied={onApplied}
      />,
    );

    await user.click(screen.getByTestId("proposal-card-accept-0"));
    await waitFor(() =>
      expect(screen.getByTestId("proposal-card-0")).toHaveAttribute(
        "data-card-state",
        "applying",
      ),
    );
    expect(apiMock.applyAIProposal).toHaveBeenCalledWith({
      case_id: "ldc",
      tool: "set_patch_bc_type",
      args: { patch_name: "walls", bc_class: "no_slip_wall" },
      model_used: "deepseek-v4-pro",
      conversation_turn_id: "a-1",
    });

    resolveApply(buildOkResponse());
    await waitFor(() =>
      expect(screen.getByTestId("proposal-card-0")).toHaveAttribute(
        "data-card-state",
        "applied",
      ),
    );
    expect(screen.getByTestId(`proposal-card-applied-pill-0`)).toBeInTheDocument();
    expect(screen.getByTestId("proposal-card-summary-0")).toHaveTextContent(
      "no_slip_wall",
    );
    // Accept / Reject buttons are gone in the terminal state.
    expect(screen.queryByTestId("proposal-card-accept-0")).not.toBeInTheDocument();
    expect(screen.queryByTestId("proposal-card-reject-0")).not.toBeInTheDocument();
    expect(onApplied).toHaveBeenCalledTimes(1);
  });

  it("Reject transitions idle → rejected (terminal) without invoking applyAIProposal", async () => {
    const user = userEvent.setup();
    render(
      <ProposalCard
        caseId="ldc"
        proposal={buildProposal()}
        modelUsed={null}
        turnId="a-1"
      />,
    );
    await user.click(screen.getByTestId("proposal-card-reject-0"));
    expect(screen.getByTestId("proposal-card-0")).toHaveAttribute(
      "data-card-state",
      "rejected",
    );
    expect(apiMock.applyAIProposal).not.toHaveBeenCalled();
    expect(screen.queryByTestId("proposal-card-accept-0")).not.toBeInTheDocument();
  });

  it("Accept double-click only invokes apply once (idempotency · DEC R3)", async () => {
    let resolveApply: (val: ApplyAIProposalResponse) => void = () => {};
    apiMock.applyAIProposal.mockImplementation(
      () => new Promise((res) => (resolveApply = res)),
    );

    const user = userEvent.setup();
    render(
      <ProposalCard
        caseId="ldc"
        proposal={buildProposal()}
        modelUsed={null}
        turnId="a-1"
      />,
    );
    const accept = screen.getByTestId("proposal-card-accept-0");
    await user.click(accept);
    // Card is now in applying state; the Accept button has been
    // removed (only "applying…" text shows). A second double-click
    // therefore CAN'T trigger another applyAIProposal call.
    expect(screen.queryByTestId("proposal-card-accept-0")).not.toBeInTheDocument();
    expect(apiMock.applyAIProposal).toHaveBeenCalledTimes(1);

    resolveApply(buildOkResponse());
    await waitFor(() =>
      expect(screen.getByTestId("proposal-card-0")).toHaveAttribute(
        "data-card-state",
        "applied",
      ),
    );
  });

  it("Apply error renders the failing_check and offers retry", async () => {
    apiMock.applyAIProposal.mockRejectedValueOnce(
      new ApiError(400, "apply-proposal failed", {
        failing_check: "arg_validation_failed",
        tool: "set_patch_bc_type",
        errors: [{}],
      }),
    );
    const user = userEvent.setup();
    render(
      <ProposalCard
        caseId="ldc"
        proposal={buildProposal()}
        modelUsed={null}
        turnId="a-1"
      />,
    );
    await user.click(screen.getByTestId("proposal-card-accept-0"));
    await waitFor(() =>
      expect(screen.getByTestId("proposal-card-0")).toHaveAttribute(
        "data-card-state",
        "error",
      ),
    );
    expect(screen.getByTestId("proposal-card-error-0")).toHaveTextContent(
      "arg_validation_failed",
    );
    // Retry button is back, labelled "重试".
    const retry = screen.getByTestId("proposal-card-accept-0");
    expect(retry).toHaveTextContent("重试");
  });

  it("Apply error prefers inner_failing_check when present (V123 R2 P2-2)", async () => {
    apiMock.applyAIProposal.mockRejectedValueOnce(
      new ApiError(422, "apply-proposal failed: cell_cap_exceeded", {
        failing_check: "underlying_service_error",
        inner_failing_check: "cell_cap_exceeded",
        tool: "regenerate_mesh",
        message:
          "mesh pipeline failed: cell_cap_exceeded: hard cap exceeded",
      }),
    );
    const user = userEvent.setup();
    render(
      <ProposalCard
        caseId="ldc"
        proposal={buildProposal()}
        modelUsed={null}
        turnId="a-2"
      />,
    );
    await user.click(screen.getByTestId("proposal-card-accept-0"));
    await waitFor(() =>
      expect(screen.getByTestId("proposal-card-0")).toHaveAttribute(
        "data-card-state",
        "error",
      ),
    );
    // The actionable inner code surfaces, NOT the wrapping
    // 'underlying_service_error' string the engineer can't act on.
    expect(screen.getByTestId("proposal-card-error-0")).toHaveTextContent(
      "cell_cap_exceeded",
    );
    expect(screen.getByTestId("proposal-card-error-0")).not.toHaveTextContent(
      "underlying_service_error",
    );
  });

  it("renders audit_warning when the response includes one", async () => {
    apiMock.applyAIProposal.mockResolvedValueOnce(
      buildOkResponse({
        audit_id: null,
        audit_warning: "audit log write failed: simulated disk full.",
      }),
    );
    const user = userEvent.setup();
    render(
      <ProposalCard
        caseId="ldc"
        proposal={buildProposal()}
        modelUsed={null}
        turnId="a-1"
      />,
    );
    await user.click(screen.getByTestId("proposal-card-accept-0"));
    await waitFor(() =>
      expect(screen.getByTestId("proposal-card-0")).toHaveAttribute(
        "data-card-state",
        "applied",
      ),
    );
    expect(screen.getByTestId("proposal-card-summary-0")).toHaveTextContent(
      "simulated disk full",
    );
  });
});
