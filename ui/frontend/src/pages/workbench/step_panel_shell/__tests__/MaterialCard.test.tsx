/**
 * V68-C.1 · MaterialCard React integration tests.
 *
 * Exercises the four PhysicsView discriminants through the hook:
 *   1. committed (200 with both dict texts) — parsed Newtonian + laminar
 *   2. reference (404 fall-back to CaseDetail) — whitelist case badge
 *   3. loading — spinner copy
 *   4. error — message surfaces
 *
 * Mocks both api.getPhysicsState and api.getCase so the hook's chained
 * react-query path runs end-to-end without network.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

import type { CaseDetail } from "@/types/validation";
import type { PhysicsStateResponse } from "@/types/physics";

const apiMock = vi.hoisted(() => ({
  getPhysicsState: vi.fn(),
  getCase: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: {
      ...actual.api,
      getPhysicsState: apiMock.getPhysicsState,
      getCase: apiMock.getCase,
    },
  };
});

import { MaterialCard } from "../MaterialCard";

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const committedLdc: PhysicsStateResponse = {
  case_id: "case_001",
  material_dict_text: [
    "transportModel  Newtonian;",
    "nu              [0 2 -1 0 0 0 0] 1e-3;",
  ].join("\n"),
  regime_dict_text: "simulationType  laminar;",
};

const naca0012Detail: CaseDetail = {
  case_id: "naca0012_airfoil",
  name: "NACA 0012",
  reference: "Thomas 1979",
  doi: null,
  flow_type: "EXTERNAL",
  geometry_type: "AIRFOIL",
  compressibility: "INCOMPRESSIBLE",
  steady_state: "STEADY",
  solver: "simpleFoam",
  turbulence_model: "k-omega SST",
  parameters: { Re: 3_000_000 },
  gold_standard: null,
  preconditions: [],
  contract_status_narrative: null,
};

beforeEach(() => {
  apiMock.getPhysicsState.mockReset();
  apiMock.getCase.mockReset();
  cleanup();
});

describe("MaterialCard · committed mode (200 with dict texts)", () => {
  it("renders committed badge + parsed Newtonian + laminar + nu", async () => {
    apiMock.getPhysicsState.mockResolvedValue(committedLdc);
    renderWithClient(<MaterialCard caseId="case_001" />);

    await waitFor(() =>
      expect(screen.getByTestId("material-card")).toHaveAttribute(
        "data-status",
        "committed",
      ),
    );
    expect(screen.getByTestId("material-card-badge").textContent).toContain(
      "committed",
    );
    expect(screen.getByTestId("material-card-transport-model").textContent).toContain(
      "Newtonian",
    );
    expect(screen.getByTestId("material-card-nu").textContent).toContain("1.000e-3");
    expect(screen.getByTestId("material-card-regime").textContent).toContain(
      "laminar",
    );
    // Case-detail fallback must NOT fire when committed.
    expect(apiMock.getCase).not.toHaveBeenCalled();
  });

  it("renders raw dict text under disclosure", async () => {
    apiMock.getPhysicsState.mockResolvedValue(committedLdc);
    renderWithClient(<MaterialCard caseId="case_001" />);
    await waitFor(() =>
      expect(screen.getByTestId("material-card-raw-material")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("material-card-raw-material").textContent).toContain(
      "transportModel  Newtonian;",
    );
    expect(screen.getByTestId("material-card-raw-regime").textContent).toContain(
      "simulationType  laminar;",
    );
  });
});

describe("MaterialCard · reference mode (404 → CaseDetail fallback)", () => {
  it("falls back to CaseDetail and renders reference badge + RAS regime", async () => {
    apiMock.getPhysicsState.mockResolvedValue(null);
    apiMock.getCase.mockResolvedValue(naca0012Detail);
    renderWithClient(<MaterialCard caseId="naca0012_airfoil" />);

    await waitFor(() =>
      expect(screen.getByTestId("material-card")).toHaveAttribute(
        "data-status",
        "reference",
      ),
    );
    expect(screen.getByTestId("material-card-badge").textContent).toContain(
      "reference (whitelist)",
    );
    expect(screen.getByTestId("material-card-regime").textContent).toContain("RAS");
    expect(screen.getByTestId("material-card-reynolds").textContent).toContain(
      "3.00e+6",
    );
    expect(apiMock.getCase).toHaveBeenCalledWith("naca0012_airfoil");
  });

  it("raw pane shows whitelist disclaimer (no synthesized dict text)", async () => {
    apiMock.getPhysicsState.mockResolvedValue(null);
    apiMock.getCase.mockResolvedValue(naca0012Detail);
    renderWithClient(<MaterialCard caseId="naca0012_airfoil" />);
    await waitFor(() =>
      expect(
        screen.getByTestId("material-card-raw-reference"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("material-card-raw-reference").textContent).toContain(
      "whitelist case",
    );
    // V130 invariant: no synthesized OpenFOAM dict text leaks through.
    expect(screen.queryByTestId("material-card-raw-material")).toBeNull();
  });
});

describe("MaterialCard · zero / loading / error", () => {
  it("renders no-case copy when caseId is null", () => {
    renderWithClient(<MaterialCard caseId={null} />);
    expect(screen.getByTestId("material-card-no-case")).toBeInTheDocument();
    expect(apiMock.getPhysicsState).not.toHaveBeenCalled();
  });

  it("renders error message when physics fetch throws", async () => {
    apiMock.getPhysicsState.mockRejectedValue(
      new Error("backend unreachable"),
    );
    renderWithClient(<MaterialCard caseId="case_001" />);
    await waitFor(() =>
      expect(screen.getByTestId("material-card-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("material-card-error").textContent).toContain(
      "backend unreachable",
    );
  });
});
