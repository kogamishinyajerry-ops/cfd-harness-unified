/**
 * V71-UI-V3 · InspectorContent · Inspector tab content
 * Adapts to current step + viewport mode (V71.T contextual rule):
 *   - No case loaded → empty state + quick start (Image 01)
 *   - Step 1 → CASE METADATA + GEOMETRY + NEXT STEP (Image 02)
 *   - Step 2 → MESH SUMMARY + REFINEMENT + NEXT STEP (Image 03)
 *   - Step 3 → BOUNDARY CONDITIONS + MATERIALS + NEXT STEP (Image 04)
 *   - Step 4 (active solve, mesh viewport mode) → ACTIVE SOLVE + MESH SUMMARY (Image 08)
 *   - Step 5 → fall through to TruthChain (or compact summary)
 */
import { Link } from "react-router-dom";
import type { StepId, ViewportMode } from "../../WorkbenchShellV3";

interface InspectorContentProps {
  caseId: string | null;
  stepId: StepId;
  viewportMode: ViewportMode;
}

function Section({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-8">
      <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-3">
        {label}
      </div>
      <div className="space-y-2.5 text-[13px]">{children}</div>
    </div>
  );
}

function Row({
  k,
  v,
  note,
}: {
  k: string;
  v: React.ReactNode;
  note?: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-v3-textSecondary truncate">{k}</span>
      <span className="text-v3-textPrimary font-mono text-right tabular-nums">
        {v}
        {note ? <span className="ml-1.5">{note}</span> : null}
      </span>
    </div>
  );
}

function EmptyState() {
  return (
    <>
      <Section label="No case selected">
        <p className="text-v3-textSecondary leading-relaxed">
          Inspector will show case parameters, run state, and material
          properties once a case is opened.
        </p>
      </Section>
      <Section label="Quick start">
        <Link
          to="/workbench/v3/case/lid_driven_cavity?step=1"
          className="block text-v3-textPrimary hover:text-v3-accent"
        >
          Open lid_driven_cavity starter case ›
        </Link>
        <Link
          to="/workbench"
          className="block text-v3-textPrimary hover:text-v3-accent"
        >
          Browse the 11 whitelist cases ›
        </Link>
        <Link
          to="/workbench/tutorial"
          className="block text-v3-textPrimary hover:text-v3-accent"
        >
          Read the 10-minute tutorial ›
        </Link>
      </Section>
    </>
  );
}

function Step1Inspector({ caseId }: { caseId: string }) {
  // Hard-coded canonical content for a few cases · others get generic
  const isNaca = caseId.includes("naca0012");
  const isCavity = caseId.includes("cavity");
  return (
    <>
      <Section label="Case metadata">
        <Row k="case_id" v={caseId} />
        <Row
          k="flow_type"
          v={isNaca ? "EXTERNAL" : isCavity ? "INTERNAL" : "EXTERNAL"}
        />
        <Row
          k="geometry"
          v={isNaca ? "airfoil 2D" : isCavity ? "unit cavity 2D" : "—"}
        />
        <Row
          k="Re"
          v={isNaca ? "3.0×10⁶" : isCavity ? "100" : "—"}
        />
        <Row
          k="Mach"
          v={isNaca ? "0.15 (low-Mach)" : isCavity ? "incompressible" : "—"}
        />
        <Row
          k="classification"
          v={isNaca ? "gold · canonical E16" : isCavity ? "gold · canonical E01" : "canonical"}
        />
      </Section>
      <Section label="Geometry">
        <Row
          k="source"
          v={isNaca ? "airfoil.stl (1.4 MB)" : isCavity ? "intrinsic blockMesh" : "intrinsic"}
        />
        <Row k="bodies" v="1" />
        <Row k="triangles" v={isNaca ? "24,820" : "—"} />
        <Row
          k="watertight"
          v={
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-v3-inlet mr-1.5" />
              PASS
            </span>
          }
        />
        <Row
          k="extents X"
          v={isNaca ? "−2.0 to 6.0 m" : isCavity ? "0.0 to 1.0 m" : "—"}
        />
        <Row
          k="extents Y"
          v={isNaca ? "−3.0 to 3.0 m" : isCavity ? "0.0 to 1.0 m" : "—"}
        />
        <Row
          k="extents Z"
          v={isNaca ? "0.0 to 0.1 m" : isCavity ? "0.0 to 0.1 m" : "—"}
        />
      </Section>
      <Section label="Next step">
        <p className="text-v3-textSecondary leading-relaxed">
          Geometry is loaded and watertight. Continue to Step 2 (Mesh) to
          generate the {isCavity ? "uniform blockMesh" : "snappyHexMesh"} substrate.
        </p>
        <Link
          to={`?step=2`}
          data-testid="next-step-link"
          className="inline-block text-v3-textPrimary hover:text-v3-accent border-b border-v3-accent pb-0.5 mt-2"
        >
          Continue to Mesh ›
        </Link>
      </Section>
    </>
  );
}

function Step2Inspector({ caseId }: { caseId: string }) {
  const isCavity = caseId.includes("cavity");
  return (
    <>
      <Section label="Mesh summary">
        <Row
          k="Total cells"
          v={isCavity ? "289" : "1,237,452"}
        />
        {!isCavity && (
          <>
            <Row k="Hex" v="1,189,022 (96.1%)" />
            <Row k="Prism (BL)" v="48,430 (3.9%)" />
          </>
        )}
        <Row
          k="Min volume"
          v={isCavity ? "3.4×10⁻³ m³" : "3.1×10⁻¹² m³"}
        />
        <Row
          k="Max aspect ratio"
          v={isCavity ? "1.00" : "842"}
          note={
            !isCavity && (
              <span className="inline-block w-2 h-2 rounded-full bg-v3-symmetry ml-1" />
            )
          }
        />
        <Row
          k="Max skewness"
          v={isCavity ? "0.00" : "1.84"}
          note={
            <span className="inline-block w-2 h-2 rounded-full bg-v3-inlet ml-1" />
          }
        />
        <Row
          k="Max non-ortho"
          v={isCavity ? "0.0°" : "62.3°"}
          note={
            <span className="inline-block w-2 h-2 rounded-full bg-v3-inlet ml-1" />
          }
        />
        <Row
          k="y⁺ estimate"
          v={isCavity ? "N/A (laminar)" : "0.6–1.4"}
          note={
            !isCavity && (
              <span className="inline-block w-2 h-2 rounded-full bg-v3-inlet ml-1" />
            )
          }
        />
      </Section>
      <Section label="Refinement">
        <Row k="Refinement levels" v={isCavity ? "—" : "3"} />
        <Row
          k="Surface refinement"
          v={isCavity ? "uniform" : "level 3 near airfoil"}
        />
        <Row
          k="Boundary layer"
          v={isCavity ? "—" : "15 layers · ER 1.2 · 0.4 mm"}
        />
      </Section>
      <Section label="Next step">
        <p className="text-v3-textSecondary leading-relaxed">
          Mesh quality within snappyHexMesh defaults. Continue to Step 3 (Setup BC).
        </p>
        <Link
          to={`?step=3`}
          data-testid="next-step-link"
          className="inline-block text-v3-textPrimary hover:text-v3-accent border-b border-v3-accent pb-0.5 mt-2"
        >
          Continue to Setup BC ›
        </Link>
      </Section>
    </>
  );
}

function Step3Inspector({ caseId }: { caseId: string }) {
  const isCavity = caseId.includes("cavity");
  return (
    <>
      <Section label="Boundary conditions">
        <BCRow color="inlet" name={isCavity ? "moving_lid" : "inlet"} bc={isCavity ? "fixedValue U=(1 0 0)" : "fixedValue U=(7.7 0 0) m/s"} />
        <BCRow color="custom" name="outlet" bc="inletOutlet" />
        <BCRow color="wall" name="walls" bc="noSlip" />
        <BCRow color="symmetry" name="symmetry" bc="symmetry (2D)" />
      </Section>
      <Section label="Materials">
        <div className="flex gap-6 -mx-1">
          <div className="flex-1 px-1">
            <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
              Committed
            </div>
            <div className="space-y-2 text-[13px]">
              <div className="flex justify-between">
                <span className="text-v3-textSecondary">transportModel</span>
                <span className="text-v3-textPrimary">Newtonian</span>
              </div>
              <div className="flex justify-between">
                <span className="text-v3-textSecondary">ν</span>
                <span className="text-v3-textPrimary font-mono">
                  {isCavity ? "1.0×10⁻²" : "1.0×10⁻⁵"} m²/s ›
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-v3-textSecondary">ρ</span>
                <span className="text-v3-textPrimary font-mono">1.225 kg/m³ ›</span>
              </div>
            </div>
          </div>
          <div className="flex-1 px-1 border-l border-v3-border pl-4">
            <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
              Reference (derived)
            </div>
            <div className="space-y-2 text-[13px] text-v3-textSecondary">
              <div className="flex justify-between">
                <span>Re_H</span>
                <span className="font-mono">{isCavity ? "100" : "36,000"}</span>
              </div>
              <div className="flex justify-between">
                <span>y⁺ target</span>
                <span className="font-mono">{isCavity ? "N/A" : "30 (wall-fn)"}</span>
              </div>
              <div className="flex justify-between">
                <span>turbulence</span>
                <span className="font-mono">
                  {isCavity ? "laminar" : "k-ε wallFn"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>solver</span>
                <span className="font-mono">
                  {isCavity ? "icoFoam" : "simpleFoam"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </Section>
      <Section label="Next step">
        <p className="text-v3-textSecondary leading-relaxed">
          All BC types assigned and consistent. Continue to Step 4 (Solve).
        </p>
        <Link
          to={`?step=4`}
          data-testid="next-step-link"
          className="inline-block text-v3-textPrimary hover:text-v3-accent border-b border-v3-accent pb-0.5 mt-2"
        >
          Continue to Solve ›
        </Link>
      </Section>
    </>
  );
}

function BCRow({
  color,
  name,
  bc,
}: {
  color: "inlet" | "wall" | "symmetry" | "custom";
  name: string;
  bc: string;
}) {
  const palette: Record<typeof color, string> = {
    inlet: "bg-v3-inlet",
    wall: "bg-v3-wall",
    symmetry: "bg-v3-symmetry",
    custom: "bg-v3-custom",
  };
  return (
    <div className="flex items-center justify-between text-[13px] py-1">
      <span className="flex items-center gap-2">
        <span className={`inline-block w-2 h-2 rounded-full ${palette[color]}`} />
        <span className="text-v3-textPrimary">{name}</span>
      </span>
      <span className="text-v3-textSecondary text-right truncate">{bc} ›</span>
    </div>
  );
}

function Step4ActiveSolveInspector({ caseId }: { caseId: string }) {
  const isCavity = caseId.includes("cavity");
  return (
    <>
      <Section label="Active solve">
        <Row k="solver" v={isCavity ? "icoFoam" : "simpleFoam"} />
        <Row k="iter" v={isCavity ? "132 / ~200" : "847 / ~2000"} />
        <Row
          k="time"
          v={isCavity ? "t = 0.660 s · Δt = 0.005" : "steady · iter 847"}
        />
        <Row k="Ux" v={<span>3.2×10⁻⁶ <span className="text-v3-inlet">PASS</span></span>} />
        <Row k="Uy" v={<span>2.8×10⁻⁶ <span className="text-v3-inlet">PASS</span></span>} />
        <Row k="p" v="8.1×10⁻⁵" />
        <Row k="ETA" v="~01:12" />
        <Row k="target" v="10⁻⁵" />
      </Section>
      <Section label="Mesh summary">
        <Row k="Total cells" v={isCavity ? "289" : "1,237,452"} />
        <Row k="Grid type" v={isCavity ? "uniform blockMesh" : "snappyHexMesh"} />
        <Row k="Min/max aspect" v={isCavity ? "1.00 / 1.00" : "1.00 / 842"} />
        <Row k="Min/max skewness" v={isCavity ? "0.00 / 0.00" : "0.00 / 1.84"} />
        <Row k="y⁺" v={isCavity ? "N/A (laminar)" : "0.6–1.4"} />
      </Section>
      <Section label="Next">
        <p className="text-v3-textSecondary leading-relaxed">
          Solver running cleanly. Mesh quality verified. Click 'Residuals'
          mode to watch convergence, or stay in current mode.
        </p>
      </Section>
    </>
  );
}

function Step4DefaultInspector({ caseId }: { caseId: string }) {
  return <Step4ActiveSolveInspector caseId={caseId} />;
}

function Step5Inspector({ caseId }: { caseId: string }) {
  return (
    <>
      <Section label="Run summary">
        <Row k="solver" v={caseId.includes("cavity") ? "icoFoam" : "simpleFoam"} />
        <Row k="iter" v="200 / 200" />
        <Row
          k="status"
          v={
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-v3-inlet mr-1" />
              CONVERGED
            </span>
          }
        />
        <Row k="elapsed" v="28 sec" />
      </Section>
      <Section label="See TruthChain tab">
        <p className="text-v3-textSecondary leading-relaxed">
          TrustGate verdict and gold-standard comparison are on the
          TruthChain tab.
        </p>
      </Section>
    </>
  );
}

export function InspectorContent({
  caseId,
  stepId,
  viewportMode,
}: InspectorContentProps) {
  if (!caseId) return <EmptyState />;
  switch (stepId) {
    case 1:
      return <Step1Inspector caseId={caseId} />;
    case 2:
      return <Step2Inspector caseId={caseId} />;
    case 3:
      return <Step3Inspector caseId={caseId} />;
    case 4:
      // V71.T · cross-step inspection: viewport mode influences inspector
      return viewportMode === "mesh" ? (
        <Step4ActiveSolveInspector caseId={caseId} />
      ) : (
        <Step4DefaultInspector caseId={caseId} />
      );
    case 5:
      return <Step5Inspector caseId={caseId} />;
    default:
      return <EmptyState />;
  }
}
