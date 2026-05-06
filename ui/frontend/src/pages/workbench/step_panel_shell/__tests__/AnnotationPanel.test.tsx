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

  it("dispatches onSave with user_authoritative confidence (placeholder still selected → patch_type omitted)", async () => {
    // Codex 86gs N1.1 R10/R12 close: when the engineer hasn't picked
    // a real option from the dropdown, both patch_type and the R12
    // explicit-marker stay undefined, so downstream stale-pin
    // recovery in Step3SetupBC can carry stale metadata forward
    // unambiguously. The placeholder "— select patch type —"
    // option holds value="" until the engineer picks something.
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
      patch_type_explicit: undefined,
      physics_notes: undefined,
      confidence: "user_authoritative",
    });
  });

  it("explicit pick (including 'wall') is preserved with patch_type_explicit=true (Codex 86gs N1.1 R12)", async () => {
    // Under the R12 placeholder UX, any non-placeholder pick — even
    // "wall" — counts as explicit. The R12 patch_type_explicit
    // marker tags the persisted record so the resume layer can
    // distinguish post-R12 explicit picks from legacy pre-R11
    // untouched-default "wall" records.
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(<AnnotationPanel faceId="fid_xxx" onSave={onSave} />);
    await user.type(screen.getByTestId("annotation-panel-name"), "inlet");
    const select = screen.getByTestId(
      "annotation-panel-patch-type",
    ) as HTMLSelectElement;
    await user.selectOptions(select, "wall");
    await user.click(screen.getByTestId("annotation-panel-save"));
    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      face_id: "fid_xxx",
      name: "inlet",
      patch_type: "wall",
      patch_type_explicit: true,
      physics_notes: undefined,
      confidence: "user_authoritative",
    });
  });

  it("re-save of an existing record preserves seeded patch_type as explicit (Codex 86gs N1.1 R12)", async () => {
    // When the panel is mounted with an existing.patch_type, the
    // dropdown seeds to that value (not the placeholder), so a
    // re-save without further interaction persists patch_type with
    // patch_type_explicit=true. This means once a record has any
    // patch_type set, downstream re-saves preserve and re-mark it
    // as explicit (idempotent under the R12 contract).
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
      patch_type_explicit: true,
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
