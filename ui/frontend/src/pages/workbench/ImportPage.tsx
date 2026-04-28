import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import type {
  ImportRejectionDetail,
  ImportSTLResponse,
  IngestReport,
} from "@/types/import_geometry";
import { Viewport } from "@/visualization/Viewport";

// Probe the import endpoint to confirm the backend was installed with the
// `[workbench]` extra (trimesh + python-multipart + scipy). The base `[ui]`
// install soft-skips the route, so navigating here would 404 every upload
// without any indication of why. A GET probe returns 405 (Method Not
// Allowed) when the POST-only route is mounted, 404 when it is not.
//
// A confirmed 404 locks "unavailable"; a 2xx/4xx (≠404) locks "available";
// only network errors warrant retry — bounded backoff so a slow backend
// startup or dev-proxy hiccup is absorbed but a permanent "no [workbench]"
// install eventually returns the actionable 404 banner. After retries are
// exhausted with only network errors, fall through to "available" so the
// actual upload attempt surfaces the true error (not a misleading
// "install [workbench]" banner that would not apply if the backend itself
// is down).
type ImportFeatureState = "probing" | "available" | "unavailable";

async function probeImportEndpoint(
  signal: AbortSignal,
  maxAttempts = 4,
): Promise<ImportFeatureState | null> {
  // Returns null when the caller aborted (component unmounted) so the
  // effect can drop the result instead of writing to a dead component.
  // Honors the signal both inside fetch() and during the backoff sleep —
  // important under React.StrictMode where the effect double-mounts.
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (signal.aborted) return null;
    try {
      const res = await fetch("/api/import/stl", { method: "GET", signal });
      return res.status === 404 ? "unavailable" : "available";
    } catch (err) {
      if ((err as { name?: string })?.name === "AbortError") return null;
      if (attempt < maxAttempts - 1) {
        // 200ms → 400ms → 800ms (~1.4s total, above typical dev startup race).
        const delay = 200 * 2 ** attempt;
        const aborted = await new Promise<boolean>((resolve) => {
          const timer = setTimeout(() => {
            signal.removeEventListener("abort", onAbort);
            resolve(false);
          }, delay);
          const onAbort = () => {
            clearTimeout(timer);
            resolve(true);
          };
          signal.addEventListener("abort", onAbort, { once: true });
        });
        if (aborted) return null;
      }
    }
  }
  return "available";
}

// M5.0 · STL Case Import (routine path).
// Single-page upload flow: file picker → POST /api/import/stl →
// shows ingest report card → "Continue to editor" → /workbench/case/:caseId/edit.
//
// 4xx rejections (non-watertight, parse failure, oversize) surface the
// failing_check + reason inline so the user can fix the source STL and
// re-upload without leaving the page.

const ACCEPT = ".stl,application/octet-stream,application/sla";
const MAX_DISPLAY_MB = 50;

export function ImportPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [response, setResponse] = useState<ImportSTLResponse | null>(null);
  const [rejection, setRejection] = useState<ImportRejectionDetail | null>(null);
  const [networkError, setNetworkError] = useState<string>("");
  const [featureState, setFeatureState] = useState<ImportFeatureState>("probing");

  useEffect(() => {
    const controller = new AbortController();
    probeImportEndpoint(controller.signal).then((state) => {
      if (state !== null) setFeatureState(state);
    });
    return () => {
      controller.abort();
    };
  }, []);

  function reset() {
    setFile(null);
    setResponse(null);
    setRejection(null);
    setNetworkError("");
  }

  async function onUpload() {
    if (!file) return;
    setUploading(true);
    setResponse(null);
    setRejection(null);
    setNetworkError("");
    try {
      const r = await api.importStl(file);
      setResponse(r);
    } catch (e) {
      if (e instanceof ApiError && e.detail && typeof e.detail === "object") {
        setRejection(e.detail as ImportRejectionDetail);
      } else if (e instanceof Error) {
        setNetworkError(e.message);
      } else {
        setNetworkError(String(e));
      }
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="mx-auto max-w-3xl px-8 py-8">
      <header className="mb-6">
        <div className="flex items-baseline justify-between">
          <h1 className="text-2xl font-semibold text-surface-100">
            Import case from STL
          </h1>
          <Link
            to="/workbench"
            className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1 text-xs text-surface-300 transition hover:bg-surface-800"
          >
            ← Workbench
          </Link>
        </div>
        <p className="mt-1 text-[13px] text-surface-400">
          Upload a watertight STL. M5.0 ingests + scaffolds an OpenFOAM case
          directory and routes you into the editor. Real meshing runs at M7.
          Imported cases cannot reach a literature-anchored{" "}
          <code className="rounded-sm bg-surface-900 px-1 font-mono text-[11px]">PASS</code>{" "}
          verdict (M5.1 caps them at PASS_WITH_DISCLAIMER).
        </p>
      </header>

      {featureState === "unavailable" && (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-6 text-sm text-amber-100">
          <strong className="block text-amber-200">
            STL import is not enabled on this backend.
          </strong>
          <p className="mt-2 text-[13px] text-amber-100/90">
            The import route requires the optional <code>[workbench]</code>{" "}
            extras (<code>trimesh</code>, <code>scipy</code>,{" "}
            <code>python-multipart</code>). Reinstall with{" "}
            <code className="font-mono">uv pip install -e ".[workbench]"</code>{" "}
            to enable uploads.
          </p>
        </div>
      )}

      {featureState !== "unavailable" && !response && (
        <div className="rounded-md border border-surface-800 bg-surface-900/40 p-6">
          <label className="block text-xs font-mono uppercase tracking-wider text-surface-500">
            STL file (max {MAX_DISPLAY_MB} MB)
          </label>
          <input
            type="file"
            accept={ACCEPT}
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setFile(f);
              setRejection(null);
              setNetworkError("");
            }}
            className="mt-3 block w-full text-sm text-surface-200 file:mr-4 file:rounded-sm file:border-0 file:bg-emerald-500/10 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-emerald-300 file:transition hover:file:bg-emerald-500/20"
          />

          {file && (
            <div className="mt-4 flex items-center justify-between rounded-sm border border-surface-800 bg-surface-950/60 px-3 py-2 text-xs">
              <div className="font-mono">
                <span className="text-surface-200">{file.name}</span>
                <span className="ml-2 text-surface-500">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              </div>
              <button
                type="button"
                onClick={reset}
                className="text-[11px] text-surface-500 underline transition hover:text-surface-300"
              >
                clear
              </button>
            </div>
          )}

          <div className="mt-4 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onUpload}
              disabled={!file || uploading || featureState !== "available"}
              className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-4 py-1.5 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {featureState === "probing"
                ? "Checking backend…"
                : uploading
                ? "Uploading…"
                : "Upload & create case"}
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
        <>
          <div className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-6">
            <div className="flex items-baseline justify-between">
              <h2 className="text-sm font-semibold text-emerald-300">
                Case created
              </h2>
              <span className="font-mono text-[11px] text-surface-500">
                {response.case_id}
              </span>
            </div>
            <IngestReportCard report={response.ingest_report} />
            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={reset}
                className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1.5 text-xs text-surface-300 transition hover:bg-surface-800"
              >
                Import another
              </button>
              <button
                type="button"
                onClick={() => navigate(response.edit_url)}
                className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-4 py-1.5 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/20"
              >
                Continue to editor →
              </button>
            </div>
          </div>
          {/* M-VIZ Step 6 (DEC-V61-094 spec_v2 §A.2): Geometry preview panel
              ADDED below the existing report card. Not a Fluent-style layout
              replacement — that's M-PANELS. M-VIZ uses ImportPage as the
              smoke-test home so the Viewport gets a real consumer immediately.
              The report card + "Continue to editor" link above are unchanged. */}
          <div className="mt-6">
            <Viewport
              stlUrl={`/api/cases/${encodeURIComponent(response.case_id)}/geometry/stl`}
            />
          </div>
        </>
      )}
    </section>
  );
}

function RejectionPanel({ rejection }: { rejection: ImportRejectionDetail }) {
  return (
    <div className="mt-4 rounded-sm border border-rose-500/40 bg-rose-500/10 p-3 text-xs">
      <div className="flex items-baseline justify-between">
        <strong className="text-rose-200">Upload rejected</strong>
        <code className="font-mono text-[11px] text-rose-300">
          failing_check = {rejection.failing_check}
        </code>
      </div>
      <p className="mt-1 text-rose-200/90">{rejection.reason}</p>
      {rejection.failing_check === "watertight" && (
        <p className="mt-2 text-rose-200/80">
          Heal the geometry in the source CAD (close all gaps, weld duplicate
          vertices) before re-uploading.
        </p>
      )}
      {rejection.failing_check === "stl_parse" && (
        <p className="mt-2 text-rose-200/80">
          The file may be empty, corrupted, or not a valid STL. Re-export from
          the source CAD as ASCII or binary STL.
        </p>
      )}
      {rejection.ingest_report && <IngestReportCard report={rejection.ingest_report} />}
    </div>
  );
}

function IngestReportCard({ report }: { report: IngestReport }) {
  const dims = report.bbox_extent;
  return (
    <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-[11px]">
      <Row k="watertight" v={report.is_watertight ? "✓ yes" : "✗ no"} />
      <Row k="bbox extent" v={`${dims[0].toFixed(3)} × ${dims[1].toFixed(3)} × ${dims[2].toFixed(3)}`} />
      <Row k="unit guess" v={report.unit_guess} />
      <Row k="solids" v={`${report.solid_count}`} />
      <Row k="faces" v={`${report.face_count}`} />
      <Row k="single shell" v={report.is_single_shell ? "✓ yes" : "✗ no (multi-body)"} />
      <Row
        k="patches"
        v={
          report.all_default_faces
            ? `${report.patches.length} (all defaultFaces — no named solids)`
            : report.patches.map((p) => `${p.name} (${p.face_count})`).join(", ")
        }
      />
      {report.warnings.length > 0 && (
        <>
          <dt className="font-mono text-amber-400">warnings</dt>
          <dd>
            <ul className="list-disc pl-4 text-amber-200/90">
              {report.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </dd>
        </>
      )}
    </dl>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="font-mono text-surface-500">{k}</dt>
      <dd className="font-mono text-surface-200">{v}</dd>
    </>
  );
}
