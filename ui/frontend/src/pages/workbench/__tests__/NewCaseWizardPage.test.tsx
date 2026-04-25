// Round-2 Q15 minimum smoke test for NewCaseWizardPage.
// Asserts the page mounts without crash + the template grid renders the
// expected three cards (square_cavity / backward_facing_step / pipe_flow).
//
// Full RTL interaction coverage is deferred to Tier-B(2). This test
// catches the regression risk Opus flagged: ~600 LOC of new TSX with
// useEffect / EventSource / useMutation lifecycle, zero CI signal.
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { NewCaseWizardPage } from "../NewCaseWizardPage";

// Tier-B(2) interaction coverage uses params on the square_cavity template
// so caseId / form / preview interactions can be verified end-to-end.
const TEMPLATES_FIXTURE = {
  templates: [
    {
      template_id: "square_cavity",
      name_zh: "方腔顶盖驱动",
      name_en: "Square lid-driven cavity",
      description_zh: "test desc",
      geometry_type: "SIMPLE_GRID",
      flow_type: "INTERNAL",
      solver: "icoFoam",
      params: [
        {
          key: "Re",
          label_zh: "雷诺数",
          label_en: "Reynolds number",
          type: "float",
          default: 100.0,
          min: 10.0,
          max: 10000.0,
        },
        {
          key: "lid_velocity",
          label_zh: "顶盖速度",
          label_en: "Lid velocity",
          type: "float",
          default: 1.0,
          min: 0.01,
          max: 10.0,
        },
      ],
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
};

const PREVIEW_FIXTURE = {
  yaml_text:
    "id: my_first_cavity\nname: 方腔顶盖驱动 · my_first_cavity\nflow_type: INTERNAL\ngeometry_type: SIMPLE_GRID\nsolver: icoFoam\n",
};

let _failPreview = false;

beforeEach(() => {
  _failPreview = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/api/wizard/templates")) {
        return new Response(JSON.stringify(TEMPLATES_FIXTURE), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/api/wizard/preview")) {
        if (_failPreview) {
          return new Response(
            JSON.stringify({ detail: "param 'Re': above max 10000.0" }),
            {
              status: 400,
              headers: { "content-type": "application/json" },
            },
          );
        }
        return new Response(JSON.stringify(PREVIEW_FIXTURE), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
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

describe("NewCaseWizardPage · smoke", () => {
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
    expect(await screen.findByText(/1 · 选模板/)).toBeInTheDocument();
  });
});

describe("NewCaseWizardPage · interaction (Tier-B(2))", () => {
  it("Step-1 → Step-2: clicking template advances stepper", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByText(/方腔顶盖驱动/));
    await user.click(screen.getByRole("button", { name: /下一步.*配参数/ }));
    expect(screen.getByText(/2 · 配参数/)).toBeInTheDocument();
    // Param fields rendered
    expect(screen.getByText(/雷诺数/)).toBeInTheDocument();
    expect(screen.getByText(/顶盖速度/)).toBeInTheDocument();
  });

  it("Step-2 → Step-3 disabled until valid case_id entered", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByText(/方腔顶盖驱动/));
    await user.click(screen.getByRole("button", { name: /下一步.*配参数/ }));
    const next = screen.getByRole("button", { name: /下一步.*看 YAML/ });
    expect(next).toBeDisabled();

    // Type a valid id
    const caseIdInput = screen.getByPlaceholderText("my_first_cavity");
    await user.type(caseIdInput, "my_first_cavity");
    expect(next).toBeEnabled();
  });

  it("invalid case_id (non-alphanum) shows error + keeps Next disabled", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByText(/方腔顶盖驱动/));
    await user.click(screen.getByRole("button", { name: /下一步.*配参数/ }));
    const caseIdInput = screen.getByPlaceholderText("my_first_cavity");
    await user.type(caseIdInput, "../escape!");
    expect(await screen.findByText(/非法字符/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /下一步.*看 YAML/ }),
    ).toBeDisabled();
  });

  it("Step-3 renders server-rendered YAML preview", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByText(/方腔顶盖驱动/));
    await user.click(screen.getByRole("button", { name: /下一步.*配参数/ }));
    await user.type(
      screen.getByPlaceholderText("my_first_cavity"),
      "my_first_cavity",
    );
    await user.click(screen.getByRole("button", { name: /下一步.*看 YAML/ }));
    // Wait for debounced preview fetch (150ms) + render
    expect(
      await screen.findByText(
        /server-rendered.*byte-exact/,
        {},
        { timeout: 2000 },
      ),
    ).toBeInTheDocument();
    // Server-rendered YAML body present — find the <pre> element and
    // assert it contains the unique id line. Substring match within the
    // pre's textContent avoids the "matched too many ancestor elements"
    // failure mode of generic getByText against multiline content.
    const pre = document.querySelector("pre");
    expect(pre).not.toBeNull();
    expect(pre!.textContent).toContain("id: my_first_cavity");
  });

  it("F3 closure: previewError disables Create button (round-3 fix)", async () => {
    _failPreview = true;
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByText(/方腔顶盖驱动/));
    await user.click(screen.getByRole("button", { name: /下一步.*配参数/ }));
    await user.type(
      screen.getByPlaceholderText("my_first_cavity"),
      "my_first_cavity",
    );
    await user.click(screen.getByRole("button", { name: /下一步.*看 YAML/ }));
    // Wait for preview to fail
    expect(
      await screen.findByText(/render error/, {}, { timeout: 1000 }),
    ).toBeInTheDocument();
    // Round-3 F3: Create button must be disabled when preview failed
    expect(
      screen.getByRole("button", { name: /创建并跑/ }),
    ).toBeDisabled();
  });
});
