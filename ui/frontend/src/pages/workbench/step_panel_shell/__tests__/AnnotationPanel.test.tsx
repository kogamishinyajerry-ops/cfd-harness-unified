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

  it("re-save of legacy record (no marker) does NOT upgrade to explicit (Codex 86gs N1.1 R13)", async () => {
    // R13 contract close: pre-R12 case files persisted untouched-
    // default saves as patch_type="wall" with no patch_type_explicit
    // marker. If the engineer reopens such a face just to edit the
    // name/notes (without touching the dropdown), we MUST NOT upgrade
    // the ambiguous legacy record to an explicit wall — that would
    // defeat the resume layer's legacy-aware disambiguation and
    // recreate the original downgrade-to-wall bug for stale-pin
    // recovery on legacy data after a re-save.
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        existing={{
          face_id: "fid_xxx",
          name: "inlet",
          patch_type: "wall",
          // no patch_type_explicit → legacy ambiguous record
        }}
        onSave={onSave}
      />,
    );
    // Engineer edits only the name; never opens the dropdown.
    const nameInput = screen.getByTestId(
      "annotation-panel-name",
    ) as HTMLInputElement;
    await user.clear(nameInput);
    await user.type(nameInput, "inlet_renamed");
    await user.click(screen.getByTestId("annotation-panel-save"));
    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      face_id: "fid_xxx",
      name: "inlet_renamed",
      patch_type: "wall",
      patch_type_explicit: undefined,
      physics_notes: undefined,
      confidence: "user_authoritative",
    });
  });

  it("re-save of already-explicit record preserves the explicit marker (Codex 86gs N1.1 R12 idempotency)", async () => {
    // Symmetric guard: when the seeded existing record was already
    // explicit (patch_type_explicit=true from a prior post-R12 pick
    // or AI write), re-saving without dropdown interaction must
    // PRESERVE the marker. This is the idempotent re-save path —
    // engineer edits name/notes on a previously-explicit record.
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        existing={{
          face_id: "fid_xxx",
          name: "inlet",
          patch_type: "patch",
          patch_type_explicit: true,
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

  it("unmatched printable keystroke on focused select does NOT upgrade (Codex 86gs N1.1 R16)", async () => {
    // R16 close: an unmatched typeahead key (e.g., 'z' when no
    // option starts with z) doesn't change the select's value, so
    // it must NOT count as a patch-type interaction. R15's
    // typeahead heuristic (key.length === 1) over-counted these.
    // Real typeahead matches (e.g., 'p' jumping to "patch") still
    // fire onChange and get caught by the change handler.
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        existing={{
          face_id: "fid_xxx",
          name: "inlet",
          patch_type: "wall",
        }}
        onSave={onSave}
      />,
    );
    const select = screen.getByTestId(
      "annotation-panel-patch-type",
    ) as HTMLSelectElement;
    select.focus();
    // 'z' has no matching option in PATCH_TYPES (wall, patch,
    // symmetry, empty, cyclic) — typeahead is a no-op.
    await user.keyboard("z");
    await user.click(screen.getByTestId("annotation-panel-save"));
    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      face_id: "fid_xxx",
      name: "inlet",
      patch_type: "wall",
      patch_type_explicit: undefined,
      physics_notes: undefined,
      confidence: "user_authoritative",
    });
  });

  it("Tab-through select on legacy record does NOT upgrade to explicit (Codex 86gs N1.1 R15)", async () => {
    // R15 close: a keyboard user tabbing through the form passes
    // focus through the patch_type select. Pressing Tab to move
    // on must NOT count as patch-type interaction — that's
    // pure navigation, not engagement with the dropdown's value.
    // Same for Escape / Shift / Ctrl / Alt / Meta.
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        existing={{
          face_id: "fid_xxx",
          name: "inlet",
          patch_type: "wall",
          // No patch_type_explicit → legacy ambiguous record.
        }}
        onSave={onSave}
      />,
    );
    const select = screen.getByTestId(
      "annotation-panel-patch-type",
    ) as HTMLSelectElement;
    // Focus the select WITHOUT clicking it (so onClick doesn't fire),
    // then send a Tab keystroke as if the user is moving past it.
    select.focus();
    await user.keyboard("{Tab}");
    await user.click(screen.getByTestId("annotation-panel-save"));
    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      face_id: "fid_xxx",
      name: "inlet",
      patch_type: "wall",
      patch_type_explicit: undefined,
      physics_notes: undefined,
      confidence: "user_authoritative",
    });
  });

  it("Enter-confirm via keyboard upgrades legacy 'wall' to explicit (Codex 86gs N1.1 R15)", async () => {
    // Symmetric to the Tab-through guard: a keyboard user who
    // focuses the select and presses Enter to commit the seeded
    // value HAS expressed patch-type intent (the commit gesture).
    // That counts as an interaction.
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        existing={{
          face_id: "fid_xxx",
          name: "inlet",
          patch_type: "wall",
        }}
        onSave={onSave}
      />,
    );
    const select = screen.getByTestId(
      "annotation-panel-patch-type",
    ) as HTMLSelectElement;
    select.focus();
    await user.keyboard("{Enter}");
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

  it("same-value re-confirm on legacy 'wall' upgrades to explicit (Codex 86gs N1.1 R14)", async () => {
    // R14 close: <select> doesn't fire onChange when the engineer
    // reopens the dropdown and re-picks the SAME value, so the R13
    // onChange-only interaction tracking missed the legacy-promotion
    // path. Adding onClick (any mouse engagement with the control)
    // captures same-value confirmations as positive signal — the
    // engineer has clearly re-considered patch_type and chosen wall.
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        existing={{
          face_id: "fid_xxx",
          name: "inlet",
          patch_type: "wall",
          // No patch_type_explicit → legacy ambiguous record.
        }}
        onSave={onSave}
      />,
    );
    const select = screen.getByTestId(
      "annotation-panel-patch-type",
    ) as HTMLSelectElement;
    // Engineer clicks the dropdown (engages, but doesn't change
    // value). userEvent.click on a closed select fires onClick.
    await user.click(select);
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

  it("dropdown interaction upgrades legacy ambiguous to explicit (Codex 86gs N1.1 R13)", async () => {
    // The other half of the legacy-handling: if the engineer DOES
    // open the dropdown and reconfirm/change the value, that's a
    // positive signal of intent and the save legitimately persists
    // patch_type_explicit=true. (This is the path engineers take
    // when they want to "promote" a legacy ambiguous record to
    // explicit without changing the value.)
    const onSave = vi.fn(() => Promise.resolve());
    const user = userEvent.setup();
    render(
      <AnnotationPanel
        faceId="fid_xxx"
        existing={{
          face_id: "fid_xxx",
          name: "inlet",
          patch_type: "wall",
        }}
        onSave={onSave}
      />,
    );
    const select = screen.getByTestId(
      "annotation-panel-patch-type",
    ) as HTMLSelectElement;
    // Cycle through "patch" then back to "wall" so the engineer's
    // interaction is unambiguous (a same-value re-pick wouldn't
    // fire onChange in some browser engines, so the user-event
    // selectOptions chain ensures a real transition).
    await user.selectOptions(select, "patch");
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
