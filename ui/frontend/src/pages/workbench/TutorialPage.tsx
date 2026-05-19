/**
 * V70.3 · TutorialPage · /workbench/tutorial
 *
 * Self-contained novice onboarding tour walking through the 5-step
 * pipeline using lid_driven_cavity as the running example. Static
 * markdown-style content rendered as React for now; can be migrated
 * to MDX or react-tour-style overlays in V71+.
 *
 * V70-DONE-3 anchor: route exists + reachable + content explains all
 * 5 pipeline steps in <10 minute read time.
 */
import { Link } from "react-router-dom";

export function TutorialPage() {
  return (
    <div
      data-testid="workbench-tutorial-page"
      className="mx-auto max-w-3xl px-6 py-10 text-surface-200"
    >
      <h1 className="text-2xl font-bold text-emerald-300">
        Workbench Tutorial · 10-minute walkthrough
      </h1>
      <p className="mt-2 text-sm text-surface-400">
        New to the workbench? This tour walks through the 5-step CFD pipeline
        using <code className="text-emerald-300">lid_driven_cavity</code> as
        the running example. Total read time: ~10 min. Total execution time
        for a working run: ~2 min.
      </p>

      <nav
        aria-label="Tutorial step navigation"
        className="mt-6 flex flex-wrap gap-2 text-xs"
      >
        <a href="#step-1" className="rounded bg-surface-800 px-2 py-1">
          1 · Import
        </a>
        <a href="#step-2" className="rounded bg-surface-800 px-2 py-1">
          2 · Mesh
        </a>
        <a href="#step-3" className="rounded bg-surface-800 px-2 py-1">
          3 · BC
        </a>
        <a href="#step-4" className="rounded bg-surface-800 px-2 py-1">
          4 · Solve
        </a>
        <a href="#step-5" className="rounded bg-surface-800 px-2 py-1">
          5 · Results
        </a>
      </nav>

      <section id="step-1" className="mt-8 border-t border-surface-800 pt-6">
        <h2 className="text-lg font-semibold text-emerald-300">Step 1 · Import</h2>
        <p className="mt-2 text-sm">
          Pick a case from the workbench index. For first-time use, choose{" "}
          <code className="text-emerald-300">lid_driven_cavity</code> — the
          fastest convergence path and the most-studied benchmark in CFD
          (Ghia et al. 1982).
        </p>
        <p className="mt-2 text-sm">
          Engineer Control Rail (top-right of viewport): the{" "}
          <strong>Geometry</strong> mode shows raw substrate.
        </p>
      </section>

      <section id="step-2" className="mt-6 border-t border-surface-800 pt-6">
        <h2 className="text-lg font-semibold text-emerald-300">Step 2 · Mesh</h2>
        <p className="mt-2 text-sm">
          For lid_driven_cavity, the mesh is a 17×17 uniform blockMesh. No
          STL or sHM needed. Switch the Engineer Control Rail to{" "}
          <strong>Mesh</strong> to inspect the wireframe.
        </p>
        <p className="mt-2 text-sm">
          For industrial cases (NACA0012, APU bay), this step runs
          snappyHexMesh against an STL substrate.
        </p>
      </section>

      <section id="step-3" className="mt-6 border-t border-surface-800 pt-6">
        <h2 className="text-lg font-semibold text-emerald-300">Step 3 · Boundary Conditions</h2>
        <p className="mt-2 text-sm">
          MaterialCard surfaces the fluid properties (ν, ρ). For
          lid_driven_cavity: ν=0.01 m²/s, Re=100. The 4 walls are noSlip;
          the moving top wall sets U=(1, 0, 0).
        </p>
        <p className="mt-2 text-sm">
          Engineer Control Rail <strong>BC</strong> mode color-codes each
          boundary patch by type.
        </p>
      </section>

      <section id="step-4" className="mt-6 border-t border-surface-800 pt-6">
        <h2 className="text-lg font-semibold text-emerald-300">Step 4 · Solve</h2>
        <p className="mt-2 text-sm">
          Click <strong>Run</strong>. icoFoam (laminar incompressible
          transient) iterates to steady state in ~30 seconds. Engineer
          Control Rail <strong>Residuals</strong> mode shows log10
          convergence — expect U, p residuals dropping below 1e-5.
        </p>
        <p className="mt-2 text-sm">
          For RANS cases, switch to <strong>Field</strong> mode mid-run to
          preview the velocity slice while solver iterates.
        </p>
      </section>

      <section id="step-5" className="mt-6 border-t border-surface-800 pt-6">
        <h2 className="text-lg font-semibold text-emerald-300">Step 5 · Results</h2>
        <p className="mt-2 text-sm">
          The workbench's gold-standard pipeline compares your solution
          against Ghia's 1982 u-centerline reference. TrustGate badge =
          PASS if your max |u(y)| error vs Ghia is &lt;5%. Engineer Control
          Rail <strong>Report</strong> mode shows the full grid of forces /
          surface plots.
        </p>
        <p className="mt-2 text-sm">
          The AI advisor (✓ advisory, never driver) suggests next moves —
          refine mesh? change solver? Engineer decides.
        </p>
      </section>

      <section className="mt-8 border-t border-surface-800 pt-6">
        <h2 className="text-lg font-semibold text-emerald-300">Where to go next</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
          <li>
            <Link
              to="/workbench/case/lid_driven_cavity?step=1"
              data-testid="tutorial-start-link"
              className="text-emerald-400 underline"
            >
              Start the lid_driven_cavity tour
            </Link>
          </li>
          <li>
            <Link to="/workbench" className="text-emerald-400 underline">
              Browse the full case catalog (11 entries)
            </Link>
          </li>
          <li>
            Read the full{" "}
            <code className="text-emerald-300">.planning/onboarding_guide.md</code>{" "}
            for deeper background
          </li>
        </ul>
      </section>
    </div>
  );
}
