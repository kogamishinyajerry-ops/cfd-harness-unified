// AnnotationPanel — right-rail face form (DEC-V61-098 spec_v2 §A8).

import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AnnotationPanel } from "../AnnotationPanel";

describe("AnnotationPanel", () => {
  it("renders the face_id (truncated) and an empty form", () => {
    render(
      <AnnotationPanel
        faceId="fid_abcdef0123456789"
        onSave={vi.fn()}
      />,
    );
    expect(screen.getByTestId("annotation-panel")).toBeInTheDocument();
    expect(screen.getByTestId("annotation-panel-face-id").textContent).toMatch(
      /^fid_abcdef01/,
    );
    expect(
      (screen.getByTestId("annotation-panel-name") as HTMLInputElement).value,
    ).toBe("");
  });

  it("seeds the form with existing values when provided", () => {
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        existing={{
          face_id: "fid_xxx",
          name: "lid",
          patch_type: "wall",
          physics_notes: "fixedValue U=(1 0 0)",
        }}
        onSave={vi.fn()}
      />,
    );
    expect(
      (screen.getByTestId("annotation-panel-name") as HTMLInputElement).value,
    ).toBe("lid");
    expect(
      (
        screen.getByTestId("annotation-panel-patch-type") as HTMLSelectElement
      ).value,
    ).toBe("wall");
    expect(
      (screen.getByTestId("annotation-panel-notes") as HTMLTextAreaElement)
        .value,
    ).toBe("fixedValue U=(1 0 0)");
  });

  it("dispatches onSave with user_authoritative confidence", async () => {
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(<AnnotationPanel faceId="fid_xxx" onSave={onSave} />);
    await user.type(screen.getByTestId("annotation-panel-name"), "inlet");
    await user.click(screen.getByTestId("annotation-panel-save"));
    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      face_id: "fid_xxx",
      name: "inlet",
      patch_type: "wall",
      physics_notes: undefined,
      confidence: "user_authoritative",
    });
  });

  it("blocks save with an inline error when name is empty", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<AnnotationPanel faceId="fid_xxx" onSave={onSave} />);
    await user.click(screen.getByTestId("annotation-panel-save"));
    expect(screen.getByTestId("annotation-panel-error")).toHaveTextContent(
      /please give the face a name/i,
    );
    expect(onSave).not.toHaveBeenCalled();
  });

  it("surfaces save errors as inline error text", async () => {
    const onSave = vi.fn(() => Promise.reject(new Error("revision conflict")));
    const user = userEvent.setup();
    render(<AnnotationPanel faceId="fid_xxx" onSave={onSave} />);
    await user.type(screen.getByTestId("annotation-panel-name"), "outlet");
    await user.click(screen.getByTestId("annotation-panel-save"));
    await waitFor(() => {
      expect(screen.getByTestId("annotation-panel-error")).toHaveTextContent(
        /revision conflict/,
      );
    });
  });

  it("disables every interactive when disabled is true", () => {
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        disabled
        onSave={vi.fn()}
      />,
    );
    expect(screen.getByTestId("annotation-panel-name")).toBeDisabled();
    expect(screen.getByTestId("annotation-panel-patch-type")).toBeDisabled();
    expect(screen.getByTestId("annotation-panel-notes")).toBeDisabled();
    expect(screen.getByTestId("annotation-panel-save")).toBeDisabled();
  });

  it("re-seeds form state when faceId changes", async () => {
    const { rerender } = render(
      <AnnotationPanel
        faceId="fid_aaa"
        existing={{ face_id: "fid_aaa", name: "lid" }}
        onSave={vi.fn()}
      />,
    );
    expect(
      (screen.getByTestId("annotation-panel-name") as HTMLInputElement).value,
    ).toBe("lid");
    rerender(
      <AnnotationPanel
        faceId="fid_bbb"
        existing={{ face_id: "fid_bbb", name: "outlet" }}
        onSave={vi.fn()}
      />,
    );
    await waitFor(() =>
      expect(
        (screen.getByTestId("annotation-panel-name") as HTMLInputElement).value,
      ).toBe("outlet"),
    );
  });
});
