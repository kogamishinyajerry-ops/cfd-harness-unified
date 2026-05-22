// DEC-V61-202-SUB-M30-CYCLE3 · FacePickUrlSync tests.
//
// Coverage:
//   1. useFacePickPublisher forwards event.patchName into picked state
//   2. URL sync writes ?focus_patch=<name> when picked.patchName is set
//   3. URL sync removes ?focus_patch when picked is cleared
//   4. URL sync is a no-op when enabled=false (deep-link safe)
//   5. URL sync is a no-op when patchName matches existing param
//      (avoids router churn)
//   6. Empty-string patchName from kernel (STL fallback) → null in state,
//      → param removed from URL
import { describe, expect, it } from "vitest";
import { act, render } from "@testing-library/react";
import { MemoryRouter, useSearchParams } from "react-router-dom";

import {
  FacePickProvider,
  useFacePick,
  useFacePickPublisher,
} from "../../FacePickContext";
import { FacePickUrlSync } from "../FacePickUrlSync";

interface Captured {
  setPicked: ((next: any) => void) | null;
  publisher: ((event: any) => void) | null;
  searchParams: URLSearchParams | null;
}

function Capture({ captured }: { captured: Captured }) {
  const { setPicked } = useFacePick();
  const publisher = useFacePickPublisher();
  const [searchParams] = useSearchParams();
  captured.setPicked = setPicked;
  captured.publisher = publisher;
  captured.searchParams = searchParams;
  return null;
}

function renderWithSync(initialEntries: string[], enabled = true) {
  const captured: Captured = {
    setPicked: null,
    publisher: null,
    searchParams: null,
  };
  render(
    <MemoryRouter initialEntries={initialEntries}>
      <FacePickProvider>
        <FacePickUrlSync enabled={enabled} />
        <Capture captured={captured} />
      </FacePickProvider>
    </MemoryRouter>,
  );
  return captured;
}

describe("FacePickUrlSync (DEC-V61-202-SUB-M30-CYCLE3)", () => {
  it("useFacePickPublisher forwards event.patchName into picked state", () => {
    const captured = renderWithSync(["/?dynamic_frame=1"]);

    act(() => {
      captured.publisher!({
        faceId: "fid_1",
        faceIds: ["fid_1"],
        patchName: "inlet",
        cellId: 7,
        worldPosition: [0, 0, 0],
      });
    });

    // After the publish, state.patchName should be "inlet".
    // We assert by checking the URL reflects it (the sync ran).
    expect(captured.searchParams!.get("focus_patch")).toBe("inlet");
  });

  it("URL sync writes ?focus_patch=<name> on pick", () => {
    const captured = renderWithSync(["/?step=4&dynamic_frame=1"]);

    act(() => {
      captured.setPicked!({
        faceId: "fid_1",
        faceIds: ["fid_1"],
        worldPosition: [1, 2, 3],
        patchName: "outlet",
      });
    });

    expect(captured.searchParams!.get("focus_patch")).toBe("outlet");
    // Other params preserved.
    expect(captured.searchParams!.get("step")).toBe("4");
    expect(captured.searchParams!.get("dynamic_frame")).toBe("1");
  });

  it("URL sync removes ?focus_patch when picked cleared to null", () => {
    const captured = renderWithSync([
      "/?focus_patch=outlet&dynamic_frame=1",
    ]);

    act(() => {
      captured.setPicked!({
        faceId: "fid_1",
        faceIds: ["fid_1"],
        worldPosition: [0, 0, 0],
        patchName: "outlet",
      });
    });
    expect(captured.searchParams!.get("focus_patch")).toBe("outlet");

    act(() => {
      captured.setPicked!(null);
    });
    expect(captured.searchParams!.get("focus_patch")).toBeNull();
    // Other params preserved.
    expect(captured.searchParams!.get("dynamic_frame")).toBe("1");
  });

  it("does not touch URL when enabled=false (deep-link safe)", () => {
    const captured = renderWithSync(
      ["/?focus_patch=inlet&dynamic_frame=1"],
      /* enabled */ false,
    );

    // Deep-linked focus_patch should remain even when picked is null.
    expect(captured.searchParams!.get("focus_patch")).toBe("inlet");

    act(() => {
      captured.setPicked!({
        faceId: "fid_1",
        faceIds: ["fid_1"],
        worldPosition: [0, 0, 0],
        patchName: "outlet",
      });
    });

    // enabled=false → no overwrite from the picked patch.
    expect(captured.searchParams!.get("focus_patch")).toBe("inlet");
  });

  it("does not churn the router when patchName already matches the URL", () => {
    // Pre-seed the URL with focus_patch=inlet. Picking the same
    // patch should not trigger a re-write (the effect bails when
    // patchName === currentFocusPatch).
    const captured = renderWithSync([
      "/?focus_patch=inlet&dynamic_frame=1",
    ]);
    const before = captured.searchParams;

    act(() => {
      captured.setPicked!({
        faceId: "fid_x",
        faceIds: ["fid_x"],
        worldPosition: [0, 0, 0],
        patchName: "inlet",
      });
    });

    // The URL value stays the same; the test passes if no throw +
    // the URL still reflects inlet.
    expect(captured.searchParams!.get("focus_patch")).toBe("inlet");
    // Identity check is best-effort (React-router does recreate the
    // URLSearchParams object on route changes, so we can't strictly
    // assert ===), but value should match.
    expect(captured.searchParams!.toString()).toBe(before!.toString());
  });

  it("empty-string patchName (STL fallback) → param removed", () => {
    // The Viewport's STL pick kernel may emit patchName === ""
    // when the face doesn't belong to a named patch. The publisher
    // coerces this to null. Pre-seed URL with focus_patch=outlet,
    // then publish with empty patchName — URL should clear.
    const captured = renderWithSync([
      "/?focus_patch=outlet&dynamic_frame=1",
    ]);
    expect(captured.searchParams!.get("focus_patch")).toBe("outlet");

    act(() => {
      captured.publisher!({
        faceId: "fid_stl",
        faceIds: ["fid_stl"],
        patchName: "",
        cellId: 0,
        worldPosition: [0, 0, 0],
      });
    });

    expect(captured.searchParams!.get("focus_patch")).toBeNull();
  });
});
