// DEC-V61-102 M-RESCUE Phase 2 · RawDictEditor unit tests.
//
// Round-1 closure of Codex Phase-2 P3 finding: the prior version of
// this file had tests that "expected save" but never clicked save or
// asserted postRawDict. CodeMirror in jsdom doesn't propagate
// keystrokes through its EditorView, so we mock @uiw/react-codemirror
// with a plain <textarea> to make the dirty→save→409/422 flows
// genuinely testable.

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiError } from "@/api/client";

// CodeMirror replacement: a controlled textarea so fireEvent.change
// actually updates the buffer state in the component under test.
vi.mock("@uiw/react-codemirror", () => ({
  default: ({
    value,
    onChange,
  }: {
    value: string;
    onChange: (value: string) => void;
  }) => (
    <textarea
      data-testid="cm-mock"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

const apiMock = vi.hoisted(() => ({
  listRawDicts: vi.fn(),
  getRawDict: vi.fn(),
  postRawDict: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: {
      ...actual.api,
      listRawDicts: apiMock.listRawDicts,
      getRawDict: apiMock.getRawDict,
      postRawDict: apiMock.postRawDict,
    },
  };
});

import { RawDictEditor } from "../RawDictEditor";

function renderEditor(props: {
  caseId?: string;
  allowedPaths?: ReadonlyArray<string>;
}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RawDictEditor
        caseId={props.caseId ?? "case-1"}
        allowedPaths={props.allowedPaths}
      />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiMock.listRawDicts.mockReset();
  apiMock.getRawDict.mockReset();
  apiMock.postRawDict.mockReset();
  // Codex round-2 MED closure introduced sessionStorage persistence
  // across mounts. Clear between tests so a previous case_id+path
  // entry doesn't leak as the initial buffer of the next test.
  sessionStorage.clear();
});

describe("RawDictEditor", () => {
  it("renders one tab per allowlisted path", async () => {
    apiMock.listRawDicts.mockResolvedValueOnce([
      { path: "system/controlDict", exists: true, source: "user", etag: "abcd1234abcd1234" },
      { path: "system/fvSchemes", exists: true, source: "ai", etag: "ef567890ef567890" },
      { path: "system/fvSolution", exists: false, source: "ai", etag: null },
    ]);
    apiMock.getRawDict.mockResolvedValueOnce({
      case_id: "case-1",
      path: "system/controlDict",
      content: "// user-edited\n",
      source: "user",
      etag: "abcd1234abcd1234",
      edited_at: "2026-04-30T12:00:00+00:00",
    });

    renderEditor({});
    await waitFor(() => {
      expect(screen.getByText("system/controlDict")).toBeInTheDocument();
    });
    expect(screen.getByText("system/fvSchemes")).toBeInTheDocument();
    expect(screen.getByText("system/fvSolution")).toBeInTheDocument();
  });

  it("filters tabs by allowedPaths prop", async () => {
    apiMock.listRawDicts.mockResolvedValueOnce([
      { path: "system/controlDict", exists: true, source: "ai", etag: "1111111111111111" },
      { path: "system/fvSchemes", exists: true, source: "ai", etag: "2222222222222222" },
      { path: "system/decomposeParDict", exists: false, source: "ai", etag: null },
    ]);
    apiMock.getRawDict.mockResolvedValueOnce({
      case_id: "case-1",
      path: "system/controlDict",
      content: "ok\n",
      source: "ai",
      etag: "1111111111111111",
      edited_at: null,
    });

    renderEditor({ allowedPaths: ["system/controlDict", "system/fvSchemes"] });
    await waitFor(() => screen.getByText("system/controlDict"));
    expect(screen.queryByText("system/decomposeParDict")).toBeNull();
  });

  it("save button is disabled until the GET completes for an existing file", async () => {
    apiMock.listRawDicts.mockResolvedValueOnce([
      { path: "system/controlDict", exists: true, source: "ai", etag: "deadbeefdeadbeef" },
    ]);
    // Make GET hang so we can observe the gated state.
    let resolveGet: (v: any) => void = () => {};
    apiMock.getRawDict.mockReturnValueOnce(
      new Promise((res) => {
        resolveGet = res;
      }),
    );

    renderEditor({});
    await waitFor(() => screen.getByText("system/controlDict"));

    // Critical invariant: while the GET is in flight, save is
    // DISABLED — even if the user types content into the editor.
    // This guarantees the POST race-protection contract (etag must
    // be known before save) is unconditionally honored.
    const saveBtn = screen.getByTestId("raw-dict-save");
    expect(saveBtn).toBeDisabled();
    const cm = screen.getByTestId("cm-mock");
    fireEvent.change(cm, { target: { value: "premature edit\n" } });
    expect(saveBtn).toBeDisabled();

    // Resolve GET; save unlocks once etag is known.
    await act(async () => {
      resolveGet({
        case_id: "case-1",
        path: "system/controlDict",
        content: "from server\n",
        source: "ai",
        etag: "deadbeefdeadbeef",
        edited_at: null,
      });
    });
    // GET completed, etag known. With Codex round-2 persistence the
    // user's typed draft survives the GET (server content does NOT
    // overwrite it), so save becomes enabled because buffer != server.
    await waitFor(() => {
      expect(screen.getByTestId("raw-dict-save")).not.toBeDisabled();
    });
  });

  it("save POSTs with expected_etag and updates the etag on success", async () => {
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "old00000abcd1234" },
    ]);
    apiMock.getRawDict.mockResolvedValue({
      case_id: "case-1",
      path: "system/controlDict",
      content: "application icoFoam;\n",
      source: "ai",
      etag: "old00000abcd1234",
      edited_at: null,
    });
    apiMock.postRawDict.mockResolvedValueOnce({
      case_id: "case-1",
      path: "system/controlDict",
      new_etag: "new0001122334455",
      source: "user",
      warnings: [],
    });

    renderEditor({});

    // Wait for the GET-loaded buffer to reach the textarea.
    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue("application icoFoam;\n");
    });

    // Type something different → dirty.
    fireEvent.change(screen.getByTestId("cm-mock"), {
      target: { value: "application icoFoam;\n// edited\n" },
    });
    expect(screen.getByTestId("raw-dict-save")).not.toBeDisabled();

    // Click save.
    fireEvent.click(screen.getByTestId("raw-dict-save"));

    await waitFor(() => {
      expect(apiMock.postRawDict).toHaveBeenCalledWith(
        "case-1",
        "system/controlDict",
        {
          content: "application icoFoam;\n// edited\n",
          expected_etag: "old00000abcd1234",
        },
        undefined,
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText(/Saved · source=user · etag=new00011/),
      ).toBeInTheDocument();
    });
  });

  it("409 etag mismatch surfaces refresh-from-server affordance", async () => {
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "stale1111stale22" },
    ]);
    apiMock.getRawDict.mockResolvedValue({
      case_id: "case-1",
      path: "system/controlDict",
      content: "old\n",
      source: "ai",
      etag: "stale1111stale22",
      edited_at: null,
    });
    const conflict = new ApiError(409, "etag_mismatch", {
      failing_check: "etag_mismatch",
      expected_etag: "stale1111stale22",
      current_etag: "newremote44444444",
      hint: "file changed since last GET; re-fetch and merge before retry",
    });
    apiMock.postRawDict.mockRejectedValueOnce(conflict);

    renderEditor({});

    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue("old\n");
    });
    fireEvent.change(screen.getByTestId("cm-mock"), {
      target: { value: "user version\n" },
    });
    fireEvent.click(screen.getByTestId("raw-dict-save"));

    await waitFor(() => {
      expect(
        screen.getByText(/File changed on disk since you opened it/),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/Refresh from server/)).toBeInTheDocument();
  });

  it("422 validation_failed surfaces issues + force-bypass button", async () => {
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "etag00000000aaaa" },
    ]);
    apiMock.getRawDict.mockResolvedValue({
      case_id: "case-1",
      path: "system/controlDict",
      content: "ok\n",
      source: "ai",
      etag: "etag00000000aaaa",
      edited_at: null,
    });
    const validation = new ApiError(422, "validation_failed", {
      failing_check: "validation_failed",
      issues: [
        { severity: "error", message: "missing FoamFile header" },
        { severity: "warning", message: "no application key" },
      ],
      hint: "fix the errors above, or pass ?force=1 to bypass",
    });
    apiMock.postRawDict.mockRejectedValueOnce(validation);

    renderEditor({});

    // Wait for GET to populate the buffer before editing — otherwise
    // the GET-completion useEffect resets buffer to "ok\n" and our
    // typed content is overwritten before save fires.
    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue("ok\n");
    });
    fireEvent.change(screen.getByTestId("cm-mock"), {
      target: { value: "broken content" },
    });
    fireEvent.click(screen.getByTestId("raw-dict-save"));

    await waitFor(() => {
      expect(screen.getByText(/missing FoamFile header/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Force save \(bypass validation\)/)).toBeInTheDocument();
  });

  it("force-bypass click re-issues POST with force=true", async () => {
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "etag00000000aaaa" },
    ]);
    apiMock.getRawDict.mockResolvedValue({
      case_id: "case-1",
      path: "system/controlDict",
      content: "ok\n",
      source: "ai",
      etag: "etag00000000aaaa",
      edited_at: null,
    });
    const validation = new ApiError(422, "validation_failed", {
      failing_check: "validation_failed",
      issues: [{ severity: "error", message: "bad" }],
      hint: "fix the errors above",
    });
    apiMock.postRawDict
      .mockRejectedValueOnce(validation)
      .mockResolvedValueOnce({
        case_id: "case-1",
        path: "system/controlDict",
        new_etag: "forced11111forced",
        source: "user",
        warnings: [{ severity: "warning", message: "bypass recorded" }],
      });

    renderEditor({});
    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue("ok\n");
    });
    fireEvent.change(screen.getByTestId("cm-mock"), {
      target: { value: "broken content" },
    });
    fireEvent.click(screen.getByTestId("raw-dict-save"));

    await waitFor(() => screen.getByText(/Force save \(bypass validation\)/));
    fireEvent.click(screen.getByText(/Force save \(bypass validation\)/));

    await waitFor(() => {
      expect(apiMock.postRawDict).toHaveBeenLastCalledWith(
        "case-1",
        "system/controlDict",
        expect.objectContaining({
          content: "broken content",
          expected_etag: "etag00000000aaaa",
        }),
        { force: true },
      );
    });
  });

  it("surfaces detail.isError when GET fails (Codex round-1 P1 follow-up)", async () => {
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "abcd1234abcd1234" },
    ]);
    apiMock.getRawDict.mockRejectedValueOnce(
      new ApiError(500, "internal error", { hint: "disk full" }),
    );

    renderEditor({});

    await waitFor(() => {
      expect(screen.getByTestId("raw-dict-load-error")).toBeInTheDocument();
    });
  });

  it("preserves unsaved buffer across unmount/remount (Codex round-2 MED — cross-step nav)", async () => {
    // Simulate: user types into the editor, navigates away (parent
    // unmounts), comes back. Without sessionStorage persistence the
    // buffer would reset to server content; with persistence the
    // typed content survives.
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "etag1234567890ab" },
    ]);
    apiMock.getRawDict.mockResolvedValue({
      case_id: "case-persist",
      path: "system/controlDict",
      content: "server content\n",
      source: "ai",
      etag: "etag1234567890ab",
      edited_at: null,
    });

    sessionStorage.clear();
    const first = renderEditor({ caseId: "case-persist" });
    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue("server content\n");
    });
    fireEvent.change(screen.getByTestId("cm-mock"), {
      target: { value: "USER UNSAVED EDIT\n" },
    });
    // Persisted as JSON {content, etag} (Codex round-3 schema).
    await waitFor(() => {
      const raw = sessionStorage.getItem(
        "dec-v61-102:dict-buffer:case-persist:system/controlDict",
      );
      expect(raw).not.toBeNull();
      const parsed = JSON.parse(raw as string);
      expect(parsed.content).toBe("USER UNSAVED EDIT\n");
      expect(parsed.etag).toBe("etag1234567890ab");
    });

    // Unmount (simulates step navigation).
    first.unmount();

    // Remount the editor. Buffer must restore to the persisted draft,
    // not the server content.
    renderEditor({ caseId: "case-persist" });
    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue("USER UNSAVED EDIT\n");
    });

    sessionStorage.clear();
  });

  it("clears persisted draft on successful save (Codex round-2 follow-up)", async () => {
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "etag1111aaaa2222" },
    ]);
    apiMock.getRawDict.mockResolvedValue({
      case_id: "case-cleared",
      path: "system/controlDict",
      content: "old\n",
      source: "ai",
      etag: "etag1111aaaa2222",
      edited_at: null,
    });
    apiMock.postRawDict.mockResolvedValueOnce({
      case_id: "case-cleared",
      path: "system/controlDict",
      new_etag: "newnewnewnewnewn",
      source: "user",
      warnings: [],
    });

    sessionStorage.clear();
    renderEditor({ caseId: "case-cleared" });
    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue("old\n");
    });
    fireEvent.change(screen.getByTestId("cm-mock"), {
      target: { value: "user new\n" },
    });
    await waitFor(() => {
      const raw = sessionStorage.getItem(
        "dec-v61-102:dict-buffer:case-cleared:system/controlDict",
      );
      expect(raw).not.toBeNull();
      expect(JSON.parse(raw as string).content).toBe("user new\n");
    });

    fireEvent.click(screen.getByTestId("raw-dict-save"));
    await waitFor(() => {
      expect(
        sessionStorage.getItem(
          "dec-v61-102:dict-buffer:case-cleared:system/controlDict",
        ),
      ).toBeNull();
    });
  });

  it("ignores detail.data from a different case_id (Codex round-3 MED #1)", async () => {
    // Stale data from case A must NOT populate the editor when the
    // user has switched to case B on the same path. Step 3 shell
    // stays mounted across caseId changes, so the GET cache may
    // still hold case A's response while case B's GET is in flight.
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "caseB_etag123456" },
    ]);
    // GET hangs — we only want to verify that data with the WRONG
    // case_id never populates buffer.
    let resolveGet: (v: any) => void = () => {};
    apiMock.getRawDict.mockReturnValueOnce(
      new Promise((res) => {
        resolveGet = res;
      }),
    );

    sessionStorage.clear();
    renderEditor({ caseId: "case-B" });

    // Resolve GET with a payload whose case_id is FROM A DIFFERENT CASE.
    await waitFor(() => screen.getByText("system/controlDict"));
    await act(async () => {
      resolveGet({
        case_id: "case-A", // wrong! payload from different case
        path: "system/controlDict",
        content: "case A content (must NOT show)\n",
        source: "ai",
        etag: "caseA_etag99999999",
        edited_at: null,
      });
    });

    // Buffer must NOT adopt case A's content.
    expect(screen.getByTestId("cm-mock")).toHaveValue("");
    // No persisted entry should have been written under case B.
    expect(
      sessionStorage.getItem(
        "dec-v61-102:dict-buffer:case-B:system/controlDict",
      ),
    ).toBeNull();
  });

  it("preserves draft etag across remount → save surfaces 409 on server move-on (Codex round-3 MED #2)", async () => {
    // Round-3 finding: the prior version of this code restored the
    // draft content but adopted whatever fresh server etag arrived,
    // so a save POST went out with stale-content + fresh-etag. The
    // server accepted it (etag matched) and the user silently
    // overwrote whatever AI had re-authored while they were away.
    // Fix: persist {content, etag} together; restore both; do NOT
    // overwrite the persisted etag from the fresh GET. Save then
    // surfaces 409.
    sessionStorage.clear();
    sessionStorage.setItem(
      "dec-v61-102:dict-buffer:case-rebase:system/controlDict",
      JSON.stringify({
        content: "USER DRAFT (authored 5min ago)\n",
        etag: "originalEtag1234", // etag at time of draft
      }),
    );

    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "freshServer5678" },
    ]);
    apiMock.getRawDict.mockResolvedValue({
      case_id: "case-rebase",
      path: "system/controlDict",
      content: "AI re-authored while user was away\n",
      source: "ai",
      etag: "freshServer5678", // ← server has moved on
      edited_at: null,
    });
    // Server returns 409 because expected_etag (the OLD persisted
    // one) doesn't match current_etag (server's new one).
    apiMock.postRawDict.mockRejectedValueOnce(
      new ApiError(409, "etag_mismatch", {
        failing_check: "etag_mismatch",
        expected_etag: "originalEtag1234",
        current_etag: "freshServer5678",
        hint: "file changed since last GET; re-fetch and merge before retry",
      }),
    );

    renderEditor({ caseId: "case-rebase" });

    // Restored draft visible (not the AI-re-authored server content).
    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue(
        "USER DRAFT (authored 5min ago)\n",
      );
    });
    // Save unlocks once GET completes (existingFileLoading guard
    // releases). Wait for that before clicking.
    await waitFor(() => {
      expect(screen.getByTestId("raw-dict-save")).not.toBeDisabled();
    });

    fireEvent.click(screen.getByTestId("raw-dict-save"));

    // Save must use the ORIGINAL etag (from persistence), not the
    // fresh server etag. Server returns 409 → user sees conflict UI.
    await waitFor(() => {
      expect(apiMock.postRawDict).toHaveBeenCalledWith(
        "case-rebase",
        "system/controlDict",
        expect.objectContaining({
          content: "USER DRAFT (authored 5min ago)\n",
          expected_etag: "originalEtag1234",
        }),
        undefined,
      );
    });
    await waitFor(() => {
      expect(
        screen.getByText(/File changed on disk since you opened it/),
      ).toBeInTheDocument();
    });

    sessionStorage.clear();
  });

  it("clears buffer immediately on tab switch (no stale content under new path)", async () => {
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "aaaaaaaaaaaaaaaa" },
      { path: "system/fvSchemes", exists: true, source: "ai", etag: "bbbbbbbbbbbbbbbb" },
    ]);
    apiMock.getRawDict
      .mockResolvedValueOnce({
        case_id: "case-1",
        path: "system/controlDict",
        content: "controlDict content\n",
        source: "ai",
        etag: "aaaaaaaaaaaaaaaa",
        edited_at: null,
      });
    // Second GET (fvSchemes) — make it hang so we observe the cleared buffer.
    let resolveSecond: (v: any) => void = () => {};
    apiMock.getRawDict.mockReturnValueOnce(
      new Promise((res) => {
        resolveSecond = res;
      }),
    );

    renderEditor({});
    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue("controlDict content\n");
    });

    // Switch to fvSchemes — buffer must clear immediately, not show
    // controlDict content while the second GET is in flight.
    fireEvent.click(screen.getByText("system/fvSchemes"));
    expect(screen.getByTestId("cm-mock")).toHaveValue("");

    // After the second GET resolves, fvSchemes content shows.
    await act(async () => {
      resolveSecond({
        case_id: "case-1",
        path: "system/fvSchemes",
        content: "fvSchemes content\n",
        source: "ai",
        etag: "bbbbbbbbbbbbbbbb",
        edited_at: null,
      });
    });
    await waitFor(() => {
      expect(screen.getByTestId("cm-mock")).toHaveValue("fvSchemes content\n");
    });
  });
});
