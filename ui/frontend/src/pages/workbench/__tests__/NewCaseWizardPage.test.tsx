// Round-2 Q15 minimum smoke test for NewCaseWizardPage.
// Asserts the page mounts without crash + the template grid renders the
// expected three cards (square_cavity / backward_facing_step / pipe_flow).
//
// Full RTL interaction coverage is deferred to Tier-B(2). This test
// catches the regression risk Opus flagged: ~600 LOC of new TSX with
// useEffect / EventSource / useMutation lifecycle, zero CI signal.
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { NewCaseWizardPage } from "../NewCaseWizardPage";

beforeEach(() => {
  // Fake the templates API call. The smoke test only needs the page to
  // mount; we don't assert on full template content beyond the count.
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/api/wizard/templates")) {
        return new Response(
          JSON.stringify({
            templates: [
              {
                template_id: "square_cavity",
                name_zh: "方腔顶盖驱动",
                name_en: "Square lid-driven cavity",
                description_zh: "test desc",
                geometry_type: "SIMPLE_GRID",
                flow_type: "INTERNAL",
                solver: "icoFoam",
                params: [],
              },
              {
                template_id: "backward_facing_step",
                name_zh: "后台阶突扩",
                name_en: "Backward-facing step",
                description_zh: "test desc",
                geometry_type: "SIMPLE_GRID",
                flow_type: "INTERNAL",
                solver: "simpleFoam",
                params: [],
              },
              {
                template_id: "pipe_flow",
                name_zh: "层流圆管",
                name_en: "Laminar pipe flow",
                description_zh: "test desc",
                geometry_type: "AXISYMMETRIC",
                flow_type: "INTERNAL",
                solver: "simpleFoam",
                params: [],
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response("{}", { status: 200 });
    }),
  );
});

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <NewCaseWizardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NewCaseWizardPage", () => {
  it("renders without crash", async () => {
    renderPage();
    // Header has the page title — wait for templates to resolve so we get
    // past the "Loading…" early return.
    expect(await screen.findByText(/新建案例/)).toBeInTheDocument();
  });

  it("loads three starter templates", async () => {
    renderPage();
    expect(await screen.findByText(/方腔顶盖驱动/)).toBeInTheDocument();
    expect(await screen.findByText(/后台阶突扩/)).toBeInTheDocument();
    expect(await screen.findByText(/层流圆管/)).toBeInTheDocument();
  });

  it("starts on step 1 (template grid)", async () => {
    renderPage();
    // Stepper shows the three labels; step 1 is the active one
    expect(await screen.findByText(/1 · 选模板/)).toBeInTheDocument();
  });
});
