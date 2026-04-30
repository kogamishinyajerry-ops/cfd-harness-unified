// Smoke test for the M-PANELS shell (DEC-V61-096 spec_v2 §E Steps 2 + 4).
// Asserts the shell mounts cleanly + 5 steps render + URL-driven step
// state works. Component-level tests live in this directory's other
// __tests__ files; per-step wireup tests live in step_panel_shell/steps
// alongside the components.

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { MeshSuccessResponse } from "@/types/mesh_imported";

// vtk.js viewport_kernel mock so jsdom doesn't try to load WebGL.
vi.mock("@/visualization/viewport_kernel", () => ({
  createKernel: () => ({
    attachStl: vi.fn(),
    attachGltf: vi.fn(),
    resetCamera: vi.fn(),
    dispose: vi.fn(),
    setBackground: vi.fn(),
  }),
}));

// Step 1 now queries api.getCase via react-query (Step 4 wireup).
// Mock the api module so the shell tests don't block on a network
// fetch and we don't need to add an msw handler for every test.
const apiMock = vi.hoisted(() => ({
  getCase: vi.fn().mockResolvedValue({
    case_id: "abc",
    name: "Test Case",
    reference: null,
    doi: null,
    flow_type: "incompressible",
    geometry_type: "imported",
    compressibility: null,
    steady_state: null,
    solver: null,
    turbulence_model: "laminar",
    parameters: {},
    gold_standard: null,
    preconditions: [],
    contract_status_narrative: null,
  }),
  meshImported: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: {
      ...actual.api,
      getCase: apiMock.getCase,
      meshImported: apiMock.meshImported,
    },
  };
});

import { StepPanelShell } from "../../StepPanelShell";

function renderShell(initialPath: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route
            path="/workbench/case/:caseId"
            element={<StepPanelShell />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("StepPanelShell · skeleton (M-PANELS Step 2)", () => {
  it("mounts at /workbench/case/:caseId with step 1 active by default", () => {
    renderShell("/workbench/case/abc");

    const shell = screen.getByTestId("step-panel-shell");
    expect(shell).toBeInTheDocument();
    expect(shell).toHaveAttribute("data-current-step-id", "1");
  });

  it("shows the case_id in the top bar", () => {
    renderShell("/workbench/case/imported_2026-04-28T00-00-00Z_demo");
    expect(
      screen.getByTestId("top-bar-case-id"),
    ).toHaveTextContent("imported_2026-04-28T00-00-00Z_demo");
  });

  it("renders all 5 step rows in the step tree", () => {
    renderShell("/workbench/case/abc");
    for (const id of [1, 2, 3, 4, 5]) {
      expect(screen.getByTestId(`step-tree-row-${id}`)).toBeInTheDocument();
    }
  });

  it("highlights the active step via data-step-status='active'", () => {
    renderShell("/workbench/case/abc?step=3");
    const shell = screen.getByTestId("step-panel-shell");
    expect(shell).toHaveAttribute("data-current-step-id", "3");
    expect(screen.getByTestId("step-tree-row-3")).toHaveAttribute(
      "data-step-status",
      "active",
    );
    expect(screen.getByTestId("step-tree-row-1")).not.toHaveAttribute(
      "data-step-status",
      "active",
    );
  });

  it("navigates between steps via URL on step-tree click", async () => {
    const user = userEvent.setup();
    renderShell("/workbench/case/abc");

    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "1",
    );
    await user.click(screen.getByTestId("step-tree-row-2"));
    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "2",
    );
  });

  it("[下一步] button advances; [上一步] retreats", async () => {
    const user = userEvent.setup();
    renderShell("/workbench/case/abc?step=2");

    await user.click(screen.getByTestId("next-button"));
    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "3",
    );
    await user.click(screen.getByTestId("previous-button"));
    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "2",
    );
  });

  it("[上一步] is disabled at step 1; [下一步] is disabled at step 5", () => {
    const { unmount } = renderShell("/workbench/case/abc?step=1");
    expect(screen.getByTestId("previous-button")).toBeDisabled();
    expect(screen.getByTestId("next-button")).not.toBeDisabled();
    unmount();

    renderShell("/workbench/case/abc?step=5");
    expect(screen.getByTestId("previous-button")).not.toBeDisabled();
    expect(screen.getByTestId("next-button")).toBeDisabled();
  });

  it("[AI 处理] is enabled on Step 2 (wired in Step 5) and disabled on Step 1 + Steps 3-5", () => {
    const { unmount } = renderShell("/workbench/case/abc?step=1");
    expect(screen.getByTestId("ai-process-button")).toBeDisabled();
    unmount();

    renderShell("/workbench/case/abc?step=2");
    // Step 2's [AI 处理] is wired to the mesh-trigger action; the button
    // is enabled (Step2Mesh registers the action on mount). aiInFlight
    // remains false because no click has fired yet.
    expect(screen.getByTestId("ai-process-button")).not.toBeDisabled();
  });

  it("renders a real Viewport on Step 1 (geometry/render is unconditional)", () => {
    renderShell("/workbench/case/abc?step=1");
    expect(screen.queryByTestId("viewport-placeholder")).toBeNull();
  });

  it("gates Step 2's mesh viewport on mesh completion to suppress pre-mesh 404 banner", () => {
    // Pre-mesh, Step 2's /mesh/render endpoint returns 404 because the
    // glb hasn't been generated yet. Without the gateOnStepCompletion
    // gate, the Viewport rendered a hostile red error banner ("HTTP
    // 404") which the user reported as a UI 404 bug. The shell now
    // shows the friendly viewportEmptyHint placeholder until Step 2
    // is completed (mesh action returns 200) or the mount-time HEAD
    // probe detects an existing polyMesh.
    renderShell("/workbench/case/abc?step=2");
    const placeholder = screen.getByTestId("viewport-placeholder");
    expect(placeholder).toBeInTheDocument();
    expect(placeholder.textContent).toContain("AI 处理");
  });

  it("still shows the viewport placeholder on Steps 3-5 (not yet wired)", () => {
    renderShell("/workbench/case/abc?step=3");
    expect(screen.getByTestId("viewport-placeholder")).toBeInTheDocument();
  });

  it("falls back to step 1 on out-of-range ?step values", () => {
    renderShell("/workbench/case/abc?step=99");
    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "1",
    );
  });
});

// Round-1 Codex Round 2 fixes (DEC-V61-096): integration coverage that
// exercises the cross-component contracts the isolated unit tests can't.
describe("StepPanelShell · Round-2 fixes (Codex F1 + F2)", () => {
  const FAKE_MESH_RESPONSE: MeshSuccessResponse = {
    case_id: "abc",
    mesh_summary: {
      cell_count: 1234567,
      face_count: 7000000,
      point_count: 234567,
      generation_time_s: 42.5,
      polyMesh_path: "/tmp/case/constant/polyMesh",
      msh_path: "/tmp/case/mesh.msh",
      mesh_mode_used: "beginner",
      warning: null,
    },
  };

  it(
    "F2 · clicking [AI 处理] through the shell on Step 2 triggers Step2Mesh's registered mesh action",
    async () => {
      apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
      const user = userEvent.setup();
      renderShell("/workbench/case/abc?step=2");

      const aiButton = screen.getByTestId("ai-process-button");
      expect(aiButton).not.toBeDisabled();
      await user.click(aiButton);

      // The shell's onAiProcess wrapper dispatched the registered action,
      // which POSTed via api.meshImported.
      await waitFor(() => {
        expect(apiMock.meshImported).toHaveBeenCalledWith("abc", "beginner");
      });
      // And Step2Mesh's success panel rendered after the resolved mock.
      await waitFor(() => {
        expect(screen.getByTestId("step2-mesh-success")).toBeInTheDocument();
      });
    },
  );

  it(
    "Step 2 mesh-viewport gate releases after a successful mesh — placeholder is replaced by Viewport",
    async () => {
      apiMock.meshImported.mockResolvedValueOnce(FAKE_MESH_RESPONSE);
      const user = userEvent.setup();
      renderShell("/workbench/case/abc?step=2");

      // Pre-mesh: the gate suppresses /mesh/render → placeholder visible.
      expect(screen.getByTestId("viewport-placeholder")).toBeInTheDocument();

      await user.click(screen.getByTestId("ai-process-button"));

      // Post-mesh resolution: Step2Mesh fires onStepComplete → stepStates[2]
      // = "completed" → the gate releases → Viewport renders.
      await waitFor(() => {
        expect(screen.queryByTestId("viewport-placeholder")).toBeNull();
      });
    },
  );

  it(
    "F1 · step-tree rows are locked while the AI action is in flight, then unlock after it resolves",
    async () => {
      // Use a deferred promise so the click is observable mid-flight.
      let resolveMesh!: (value: MeshSuccessResponse) => void;
      apiMock.meshImported.mockReturnValueOnce(
        new Promise<MeshSuccessResponse>((resolve) => {
          resolveMesh = resolve;
        }),
      );
      const user = userEvent.setup();
      renderShell("/workbench/case/abc?step=2");

      // Pre-click: rows are clickable.
      expect(screen.getByTestId("step-tree-row-1")).not.toBeDisabled();

      await user.click(screen.getByTestId("ai-process-button"));

      // Mid-flight: every step-tree row is disabled.
      await waitFor(() => {
        expect(screen.getByTestId("step-tree")).toHaveAttribute(
          "data-disabled",
          "true",
        );
      });
      for (const id of [1, 2, 3, 4, 5] as const) {
        expect(screen.getByTestId(`step-tree-row-${id}`)).toBeDisabled();
      }

      // Resolve the in-flight mesh call → shell unwinds aiInFlight.
      resolveMesh(FAKE_MESH_RESPONSE);
      await waitFor(() => {
        expect(screen.getByTestId("step-tree")).not.toHaveAttribute(
          "data-disabled",
        );
      });
      expect(screen.getByTestId("step-tree-row-1")).not.toBeDisabled();
    },
  );

  it(
    "Phase-1A · [AI 处理] is enabled on Steps 3, 4, 5 (DEC-V61-097: setup-bc + solve + results-summary now wired)",
    () => {
      // Steps 3 / 4 / 5 used to be M-AI-COPILOT / M7-redefined /
      // M-VIZ.results placeholders. Phase-1A pulls forward the LDC
      // demo-flow back-half, so all three steps now register their
      // own AI actions with the shell on mount.
      for (const step of [3, 4, 5] as const) {
        const { unmount } = renderShell(`/workbench/case/abc?step=${step}`);
        expect(screen.getByTestId("ai-process-button")).not.toBeDisabled();
        unmount();
      }
    },
  );
});

// Codex round-13 P1 regression: switching from a meshed case to an
// unmeshed one used to leave stepStates[2]="completed" sticky, so
// Step 3's viewport gate trusted the stale flag and 404'd on
// /bc/render. The shell now resets all step states on caseId change
// before the HEAD probe runs.
describe("StepPanelShell · case-switch step-state reset (Codex round-13 P1)", () => {
  // Per-case mesh + case-exists availability for the mocked fetch.
  const meshAvailable = new Map<string, boolean>();
  const caseExists = new Map<string, boolean>();
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    meshAvailable.clear();
    caseExists.clear();
    originalFetch = globalThis.fetch;
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      const meshMatch = url.match(/\/api\/cases\/([^/]+)\/mesh\/render/);
      if (meshMatch) {
        const id = decodeURIComponent(meshMatch[1]);
        return new Response(null, {
          status: meshAvailable.get(id) ? 200 : 404,
        });
      }
      // Case-existence probe — Codex round-17 P2.
      const caseMatch = url.match(/\/api\/cases\/([^/?]+)$/);
      if (caseMatch) {
        const id = decodeURIComponent(caseMatch[1]);
        return new Response(null, {
          status: caseExists.get(id) ? 200 : 404,
        });
      }
      return new Response(null, { status: 404 });
    }) as unknown as typeof globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("Step 3 viewport gate falls back to placeholder after switching to an unmeshed case", async () => {
    meshAvailable.set("meshed_case", true);
    meshAvailable.set("fresh_case", false);
    caseExists.set("meshed_case", true);
    caseExists.set("fresh_case", true);

    function NavHelper() {
      const navigate = useNavigate();
      return (
        <button
          type="button"
          data-testid="nav-to-fresh"
          onClick={() => navigate("/workbench/case/fresh_case?step=3")}
        >
          go fresh
        </button>
      );
    }

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/workbench/case/meshed_case?step=3"]}>
          <NavHelper />
          <Routes>
            <Route
              path="/workbench/case/:caseId"
              element={<StepPanelShell />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Wait for the HEAD probe to lift Step 2 to completed → Step 3
    // viewport unblocks and renders the actual Viewport (no placeholder).
    await waitFor(() => {
      expect(screen.queryByTestId("viewport-placeholder")).toBeNull();
    });

    // Now switch to fresh_case (no mesh). Pre-fix the stale
    // stepStates[2]="completed" carried over and Step 3's gate
    // immediately fetched /bc/render → red error banner. With the
    // round-14 fix the shell resets stepStates synchronously and
    // the placeholder hint comes back.
    const user = userEvent.setup();
    await user.click(screen.getByTestId("nav-to-fresh"));

    await waitFor(() => {
      expect(screen.getByTestId("viewport-placeholder")).toBeInTheDocument();
    });
    // The case_id should also have flipped on the top-bar — sanity
    // check that we did navigate (not just hit some other placeholder
    // path).
    expect(screen.getByTestId("top-bar-case-id")).toHaveTextContent(
      "fresh_case",
    );
  });

  it("Codex round-17 P2: bogus caseId leaves Step 1 pending instead of falsely showing 'completed'", async () => {
    // 404 on GET /api/cases/<bogus> — the case existence probe must
    // NOT lift Step 1 to "completed" for an arbitrary URL string.
    caseExists.set("bogus_id", false);

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/workbench/case/bogus_id?step=2"]}>
          <Routes>
            <Route
              path="/workbench/case/:caseId"
              element={<StepPanelShell />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Wait for the probes to settle — give the GET /api/cases probe
    // enough time to land its 404. We assert NOT-completed (a
    // negative); poll briefly to ensure the 404 had time to flow
    // through.
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });
    // Step 1 row must NOT be marked "completed". With the round-16
    // bug the row would show data-step-status="completed" because
    // the shell unconditionally lifted it on caseId change.
    const step1Row = screen.getByTestId("step-tree-row-1");
    expect(step1Row).not.toHaveAttribute("data-step-status", "completed");

    // Step 2 row must also not be completed (no mesh).
    expect(screen.getByTestId("step-tree-row-2")).not.toHaveAttribute(
      "data-step-status",
      "completed",
    );
  });

  it("Codex round-15 P3: valid caseId lifts Step 1 to 'completed' on mount", async () => {
    caseExists.set("real_case", true);
    meshAvailable.set("real_case", false);

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/workbench/case/real_case?step=2"]}>
          <Routes>
            <Route
              path="/workbench/case/:caseId"
              element={<StepPanelShell />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // After the case-existence probe settles, Step 1 row reaches
    // data-step-status="completed" — so the StepTree truthfully
    // shows "import done" for valid cases when the engineer is on
    // a later step.
    await waitFor(() => {
      expect(screen.getByTestId("step-tree-row-1")).toHaveAttribute(
        "data-step-status",
        "completed",
      );
    });
  });
});
