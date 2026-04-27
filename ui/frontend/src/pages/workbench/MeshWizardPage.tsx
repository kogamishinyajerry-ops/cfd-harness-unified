import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import type {
  MeshMode,
  MeshRejectionDetail,
  MeshSuccessResponse,
} from "@/types/mesh_imported";

// M6.0 · Mesh Wizard.
// Workflow: pick mesh mode → POST /api/import/:caseId/mesh →
// gmsh runs (host) → gmshToFoam runs (cfd-openfoam container) →
// constant/polyMesh/ written → return summary.
//
// gmsh on a real geometry typically takes 30-300s; the request stays
// open during that window. The button shows "Generating mesh…" so the
// user knows nothing is hung.
//
// "Continue to run" navigation links into M7 once that lands. Until
// then the link is rendered as disabled-styled copy.

export function MeshWizardPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [meshMode, setMeshMode] = useState<MeshMode>("beginner");
  const [running, setRunning] = useState(false);
  const [response, setResponse] = useState<MeshSuccessResponse | null>(null);
  const [rejection, setRejection] = useState<MeshRejectionDetail | null>(null);
  const [networkError, setNetworkError] = useState<string>("");

  function reset() {
    setResponse(null);
    setRejection(null);
    setNetworkError("");
  }

  async function onGenerate() {
    if (!caseId) return;
    setRunning(true);
    reset();
    try {
      const r = await api.meshImported(caseId, meshMode);
      setResponse(r);
    } catch (e) {
      if (e instanceof ApiError && e.detail && typeof e.detail === "object") {
        setRejection(e.detail as MeshRejectionDetail);
      } else if (e instanceof Error) {
        setNetworkError(e.message);
      } else {
        setNetworkError(String(e));
      }
    } finally {
      setRunning(false);
    }
  }

  if (!caseId) {
    return (
      <section className="mx-auto max-w-3xl px-8 py-8">
        <p className="text-sm text-contract-fail">missing :caseId path param</p>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-3xl px-8 py-8">
      <header className="mb-6">
        <div className="flex items-baseline justify-between">
          <h1 className="text-2xl font-semibold text-surface-100">Mesh Wizard</h1>
          <Link
            to={`/workbench/case/${encodeURIComponent(caseId)}/edit`}
            className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1 text-xs text-surface-300 transition hover:bg-surface-800"
          >
            ← Back to editor
          </Link>
        </div>
        <p className="mt-1 text-[13px] text-surface-400">
          Generate an unstructured tetrahedral mesh for case{" "}
          <code className="rounded-sm bg-surface-900 px-1 font-mono text-[11px]">
            {caseId}
          </code>{" "}
          using gmsh. Output: <code>constant/polyMesh/</code> ready for the M7
          run path. gmsh can take 30–300 seconds on real geometry.
        </p>
      </header>

      {!response && (
        <div className="rounded-md border border-surface-800 bg-surface-900/40 p-6">
          <fieldset className="border-0 p-0">
            <legend className="mb-2 block text-xs font-mono uppercase tracking-wider text-surface-500">
              Mesh sizing tier
            </legend>
            <div className="flex gap-3">
              <ModeOption
                value="beginner"
                label="Beginner"
                hint="Coarser default · ≈5M-cell sizing target"
                checked={meshMode === "beginner"}
                onChange={() => setMeshMode("beginner")}
              />
              <ModeOption
                value="power"
                label="Power"
                hint="Finer sizing · 50M hard cap"
                checked={meshMode === "power"}
                onChange={() => setMeshMode("power")}
              />
            </div>
          </fieldset>

          <div className="mt-6 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onGenerate}
              disabled={running}
              className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-4 py-1.5 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {running ? "Generating mesh…" : "Generate mesh"}
            </button>
          </div>

          {rejection && <RejectionPanel rejection={rejection} />}
          {networkError && (
            <p className="mt-4 rounded-sm border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
              Network error: {networkError}
            </p>
          )}
        </div>
      )}

      {response && (
        <div className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-6">
          <div className="flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-emerald-300">
              Mesh generated
            </h2>
            <span className="font-mono text-[11px] text-surface-500">
              {response.mesh_summary.mesh_mode_used}
            </span>
          </div>
          <SummaryCard summary={response.mesh_summary} />
          {response.mesh_summary.warning && (
            <p className="mt-3 rounded-sm border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              {response.mesh_summary.warning}
            </p>
          )}
          <div className="mt-5 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={reset}
              className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1.5 text-xs text-surface-300 transition hover:bg-surface-800"
            >
              Re-run mesh
            </button>
            <span
              className="cursor-not-allowed rounded-sm border border-surface-800 bg-surface-900/20 px-4 py-1.5 text-xs font-semibold text-surface-500"
              title="M7 will land OpenFOAM run path"
            >
              Continue to run (M7)
            </span>
          </div>
        </div>
      )}
    </section>
  );
}

function ModeOption({
  value,
  label,
  hint,
  checked,
  onChange,
}: {
  value: MeshMode;
  label: string;
  hint: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label
      className={`flex flex-1 cursor-pointer flex-col gap-1 rounded-sm border px-3 py-2 transition ${
        checked
          ? "border-emerald-500/60 bg-emerald-500/10"
          : "border-surface-800 bg-surface-950/40 hover:border-surface-700"
      }`}
    >
      <span className="flex items-center gap-2 text-xs font-semibold text-surface-100">
        <input
          type="radio"
          name="mesh-mode"
          value={value}
          checked={checked}
          onChange={onChange}
          className="accent-emerald-400"
        />
        {label}
      </span>
      <span className="text-[11px] text-surface-400">{hint}</span>
    </label>
  );
}

function RejectionPanel({ rejection }: { rejection: MeshRejectionDetail }) {
  const hint = REJECTION_HINTS[rejection.failing_check] ?? null;
  return (
    <div className="mt-4 rounded-sm border border-rose-500/40 bg-rose-500/10 p-3 text-xs">
      <div className="flex items-baseline justify-between">
        <strong className="text-rose-200">Mesh rejected</strong>
        <code className="font-mono text-[11px] text-rose-300">
          failing_check = {rejection.failing_check}
        </code>
      </div>
      <p className="mt-1 text-rose-200/90">{rejection.reason}</p>
      {hint && <p className="mt-2 text-rose-200/80">{hint}</p>}
    </div>
  );
}

const REJECTION_HINTS: Record<string, string> = {
  cell_cap_exceeded:
    "Coarsen the geometry or pick a different mesh tier. The 50M-cell hard cap is a resource guard, not a quality threshold.",
  gmsh_diverged:
    "gmsh failed to converge on this geometry. Verify the STL is watertight and free of self-intersections in your CAD.",
  gmshToFoam_failed:
    "The OpenFOAM container could not convert the mesh. Confirm cfd-openfoam is running (docker ps | grep cfd-openfoam).",
  source_not_imported:
    "This case has no triSurface/ STL to mesh — only imported cases can use the gmsh path.",
};

function SummaryCard({ summary }: { summary: MeshSuccessResponse["mesh_summary"] }) {
  return (
    <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-[11px]">
      <Row k="cells" v={summary.cell_count.toLocaleString()} />
      <Row k="faces" v={summary.face_count.toLocaleString()} />
      <Row k="points" v={summary.point_count.toLocaleString()} />
      <Row k="generation time" v={`${summary.generation_time_s.toFixed(2)}s`} />
      <Row k="polyMesh path" v={summary.polyMesh_path} />
    </dl>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="font-mono text-surface-500">{k}</dt>
      <dd className="font-mono text-surface-200 break-all">{v}</dd>
    </>
  );
}
