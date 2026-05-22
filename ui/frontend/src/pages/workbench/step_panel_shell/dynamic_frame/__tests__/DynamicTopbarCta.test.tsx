// DEC-V61-202-SUB-M30-CYCLE2 · DynamicTopbarCta tests.

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DynamicTopbarCta } from "../DynamicTopbarCta";
import type { TopbarCta } from "@/types/workbench_frame";

function cta(
  overrides: Partial<TopbarCta> & { kind: TopbarCta["kind"] },
): TopbarCta {
  return {
    label: "下一步 / Next step",
    target_step: 2,
    enabled: true,
    reason: null,
    ...overrides,
  };
}

describe("DynamicTopbarCta", () => {
  it("renders next_step kind with sky-toned enabled style", () => {
    render(<DynamicTopbarCta cta={cta({ kind: "next_step" })} />);
    const btn = screen.getByTestId("dynamic-topbar-cta");
    expect(btn.dataset.kind).toBe("next_step");
    expect(btn.dataset.enabled).toBe("true");
    expect(btn).not.toBeDisabled();
  });

  it("renders re_audit kind", () => {
    render(<DynamicTopbarCta cta={cta({ kind: "re_audit", label: "复检" })} />);
    const btn = screen.getByTestId("dynamic-topbar-cta");
    expect(btn.dataset.kind).toBe("re_audit");
  });

  it("renders submit_solve kind", () => {
    render(
      <DynamicTopbarCta
        cta={cta({ kind: "submit_solve", label: "提交求解" })}
      />,
    );
    const btn = screen.getByTestId("dynamic-topbar-cta");
    expect(btn.dataset.kind).toBe("submit_solve");
  });

  it("disabled state surfaces tooltip reason", () => {
    render(
      <DynamicTopbarCta
        cta={cta({
          kind: "step_default",
          enabled: false,
          reason: "先补齐 vof_contract.phases 才能进入下一步",
        })}
      />,
    );
    const btn = screen.getByTestId("dynamic-topbar-cta");
    expect(btn).toBeDisabled();
    expect(btn.title).toBe("先补齐 vof_contract.phases 才能进入下一步");
  });

  it("calls onClick when enabled + clicked", async () => {
    const onClick = vi.fn();
    render(
      <DynamicTopbarCta
        cta={cta({ kind: "next_step" })}
        onClick={onClick}
      />,
    );
    await userEvent.click(screen.getByTestId("dynamic-topbar-cta"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("does NOT call onClick when disabled", async () => {
    const onClick = vi.fn();
    render(
      <DynamicTopbarCta
        cta={cta({
          kind: "step_default",
          enabled: false,
          reason: "blocked",
        })}
        onClick={onClick}
      />,
    );
    // Disabled button: click is a no-op browser-side; explicitly assert
    // our handler wasn't passed-through.
    const btn = screen.getByTestId("dynamic-topbar-cta");
    expect(btn).toBeDisabled();
    // userEvent.click on a disabled button is a no-op
    await userEvent.click(btn).catch(() => {
      /* expected */
    });
    expect(onClick).not.toHaveBeenCalled();
  });
});
