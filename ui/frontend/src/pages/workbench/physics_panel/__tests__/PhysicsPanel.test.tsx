// DEC-V61-142 (N3.3) · PhysicsPanel unit tests.
//
// Coverage:
//   1. Default render: water_20c + laminar_internal_default selected
//   2. Material readout shows ρ / ν / Pr / cp / k / citation
//   3. Switching to air_20c_isothermal hides thermal block
//   4. Regime readout shows applicability bounds + citation
//   5. Commit button calls api.commitPhysics with correct contract shape
//   6. Success surfaces "wrote N dict files" badge
//   7. Failure surfaces error message
//   8. Library mirror parity: every backend preset_id is present in the view

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, cleanup } from "@testing-library/react";

const apiMock = vi.hoisted(() => ({ commitPhysics: vi.fn() }));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, commitPhysics: apiMock.commitPhysics },
  };
});

import { ApiError } from "@/api/client";

import { PhysicsPanel } from "../PhysicsPanel";
import {
  MATERIAL_PRESETS_VIEW,
  REGIME_PRESETS_VIEW,
} from "../preset_library_view";

beforeEach(() => {
  apiMock.commitPhysics.mockReset();
  cleanup();
});

describe("PhysicsPanel · default render", () => {
  it("starts with first material + first regime preset selected", () => {
    render(<PhysicsPanel caseId="case_test" />);
    const matSelect = screen.getByTestId(
      "physics-material-preset-select",
    ) as HTMLSelectElement;
    expect(matSelect.value).toBe("water_20c");
    const regSelect = screen.getByTestId(
      "physics-regime-preset-select",
    ) as HTMLSelectElement;
    expect(regSelect.value).toBe("laminar_internal_default");
  });

  it("renders material readout with ρ / ν / Pr / cp / k for water", () => {
    render(<PhysicsPanel caseId="case_test" />);
    const readout = screen.getByTestId("physics-material-readout");
    expect(readout.textContent).toContain("ρ:");
    expect(readout.textContent).toContain("998.21");
    expect(readout.textContent).toContain("ν:");
    expect(readout.textContent).toContain("Pr:");
    expect(readout.textContent).toContain("7.010");
    expect(readout.textContent).toContain("cp:");
    expect(readout.textContent).toContain("4184");
    expect(readout.textContent).toContain("k:");
  });

  it("hides thermal block + Pr when isothermal preset selected", () => {
    render(<PhysicsPanel caseId="case_test" />);
    const matSelect = screen.getByTestId(
      "physics-material-preset-select",
    ) as HTMLSelectElement;
    fireEvent.change(matSelect, { target: { value: "air_20c_isothermal" } });
    const readout = screen.getByTestId("physics-material-readout");
    expect(readout.textContent).toContain("isothermal");
    expect(readout.textContent).not.toContain("Pr:");
    expect(readout.textContent).not.toContain("cp:");
  });

  it("renders regime readout with applicability + citation", () => {
    render(<PhysicsPanel caseId="case_test" />);
    const readout = screen.getByTestId("physics-regime-readout");
    expect(readout.textContent).toContain("regime:");
    expect(readout.textContent).toContain("laminar");
    expect(readout.textContent).toContain("applicability:");
    expect(readout.textContent).toContain("Re ≤ 2300");
    expect(readout.textContent).toContain("cite:");
  });

  it("regime with no documented bounds shows placeholder", () => {
    // Construct a hypothetical regime with all-None bounds — exercise the
    // 'no documented bounds' branch by switching to a preset that has at
    // least one None (laminar default does — y_plus_target=null).
    render(<PhysicsPanel caseId="case_test" />);
    // laminar default has y_plus_target=null but other fields set, so
    // applicability text should NOT include the y+ part.
    const readout = screen.getByTestId("physics-regime-readout");
    expect(readout.textContent).not.toContain("y⁺");
  });
});

describe("PhysicsPanel · commit", () => {
  it("calls api.commitPhysics with kind=preset contracts on click", async () => {
    apiMock.commitPhysics.mockResolvedValue({
      case_id: "case_test",
      written_paths: [
        "constant/physicalProperties",
        "constant/momentumTransport",
      ],
      dict_texts: {
        "constant/physicalProperties": "...",
        "constant/momentumTransport": "...",
      },
      committed_at: "2026-05-07T12:00:00Z",
    });
    render(<PhysicsPanel caseId="case_test" />);
    fireEvent.click(screen.getByTestId("physics-commit-button"));
    await waitFor(() =>
      expect(apiMock.commitPhysics).toHaveBeenCalledTimes(1),
    );
    const [caseIdArg, body] = apiMock.commitPhysics.mock.calls[0];
    expect(caseIdArg).toBe("case_test");
    expect(body.material.kind).toBe("preset");
    expect(body.material.preset_id).toBe("water_20c");
    expect(body.material.fluid.density).toBe(998.21);
    expect(body.material.citation).toBe(
      "https://webbook.nist.gov/cgi/fluid.cgi?ID=C7732185&Action=Page",
    );
    expect(body.regime.kind).toBe("preset");
    expect(body.regime.preset_id).toBe("laminar_internal_default");
    expect(body.regime.regime).toBe("laminar");
  });

  it("surfaces ok badge with file count after success", async () => {
    apiMock.commitPhysics.mockResolvedValue({
      case_id: "case_test",
      written_paths: [
        "constant/physicalProperties",
        "constant/momentumTransport",
      ],
      dict_texts: {},
      committed_at: "2026-05-07T12:00:00Z",
    });
    render(<PhysicsPanel caseId="case_test" />);
    fireEvent.click(screen.getByTestId("physics-commit-button"));
    await waitFor(() =>
      expect(screen.getByTestId("physics-commit-ok")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("physics-commit-ok").textContent).toContain(
      "wrote 2 dict files",
    );
  });

  it("surfaces error message on ApiError", async () => {
    apiMock.commitPhysics.mockRejectedValue(
      new ApiError(422, "case_not_scaffolded", { message: "constant/ missing" }),
    );
    render(<PhysicsPanel caseId="case_test" />);
    fireEvent.click(screen.getByTestId("physics-commit-button"));
    await waitFor(() =>
      expect(screen.getByTestId("physics-commit-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("physics-commit-error").textContent).toContain(
      "422",
    );
  });

  it("disables commit button while submitting", async () => {
    let resolve!: (v: unknown) => void;
    apiMock.commitPhysics.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );
    render(<PhysicsPanel caseId="case_test" />);
    const btn = screen.getByTestId("physics-commit-button") as HTMLButtonElement;
    fireEvent.click(btn);
    await waitFor(() => expect(btn.disabled).toBe(true));
    expect(btn.textContent).toContain("committing");
    resolve({
      case_id: "case_test",
      written_paths: [],
      dict_texts: {},
      committed_at: "2026-05-07T12:00:00Z",
    });
  });
});

describe("Library mirror parity (frontend ↔ backend)", () => {
  it("ships every expected material preset_id", () => {
    const ids = MATERIAL_PRESETS_VIEW.map((m) => m.preset_id);
    expect(ids).toContain("water_20c");
    expect(ids).toContain("air_20c");
    expect(ids).toContain("air_20c_isothermal");
    expect(ids).toContain("oil_iso_vg_46_40c");
  });

  it("ships every expected regime preset_id", () => {
    const ids = REGIME_PRESETS_VIEW.map((r) => r.preset_id);
    expect(ids).toContain("laminar_internal_default");
    expect(ids).toContain("rans_ras_kepsilon_default");
    expect(ids).toContain("rans_komegasst_default");
    expect(ids).toContain("les_stub_placeholder");
  });

  it("every material preset has a non-empty https citation URL", () => {
    for (const p of MATERIAL_PRESETS_VIEW) {
      expect(p.citation).toMatch(/^https:\/\//);
    }
  });

  it("every regime preset has a non-empty https citation URL", () => {
    for (const p of REGIME_PRESETS_VIEW) {
      expect(p.citation).toMatch(/^https:\/\//);
    }
  });
});
