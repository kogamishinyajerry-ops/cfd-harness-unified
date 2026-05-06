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

  it("dispatches onSave with user_authoritative confidence (untouched patch_type omitted)", async () => {
    // Codex 86gs N1.1 R10 P2 close: when the engineer hasn't touched
    // the patch_type dropdown, the save persists patch_type=undefined
    // so downstream stale-pin recovery can carry stale metadata
    // forward unambiguously. An explicit save of "wall" still
    // persists "wall" (see touched-flag test below).
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(<AnnotationPanel faceId="fid_xxx" onSave={onSave} />);
    await user.type(screen.getByTestId("annotation-panel-name"), "inlet");
    await user.click(screen.getByTestId("annotation-panel-save"));
    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      face_id: "fid_xxx",
      name: "inlet",
      patch_type: undefined,
      physics_notes: undefined,
      confidence: "user_authoritative",
    });
  });

  it("persists patch_type once the dropdown is touched (Codex 86gs N1.1 R10 P2)", async () => {
    // Even when the touched value equals the default "wall", an
    // explicit selection counts — without this, an intentional wall
    // override would be impossible to express and stale-pin recovery
    // would silently re-classify it.
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(<AnnotationPanel faceId="fid_xxx" onSave={onSave} />);
    await user.type(screen.getByTestId("annotation-panel-name"), "inlet");
    // Touch the dropdown by selecting a value (any change marks
    // touched; we cycle through to "wall" to assert explicit-wall
    // is preserved).
    const select = screen.getByTestId(
      "annotation-panel-patch-type",
    ) as HTMLSelectElement;
    await user.selectOptions(select, "patch");
    await user.selectOptions(select, "wall");
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

  it("treats existing patch_type seed as touched (subsequent save persists it)", async () => {
    // When the panel is mounted with an existing.patch_type, that
    // value came from a previous explicit save (or AI write) — it
    // counts as already-touched so a re-save (e.g., engineer
    // changing only physics_notes) preserves the patch_type.
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        existing={{
          face_id: "fid_xxx",
          name: "inlet",
          patch_type: "patch",
        }}
        onSave={onSave}
      />,
    );
    await user.click(screen.getByTestId("annotation-panel-save"));
    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      face_id: "fid_xxx",
      name: "inlet",
      patch_type: "patch",
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
