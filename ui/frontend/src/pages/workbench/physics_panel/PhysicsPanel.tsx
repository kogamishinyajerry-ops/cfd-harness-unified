// DEC-V61-142 (N3.3) · Step Physics panel — Beginner presets / Power editor.
//
// Engineer fills MaterialContract + RegimeContract via this panel, then
// clicks "Commit physics" which POSTs both to /api/cases/{id}/physics.
//
// V130 Principle B: this panel is engineer-driven only. There is NO AI
// auto-fill action; AI advisor copy may suggest values inline (future
// N6 territory) but never POSTs. The component imports api.commitPhysics
// directly — that import is grep-able + audit-able.
//
// V132 contract: api.commitPhysics is the route call; the panel renders
// applicability bounds as informational hints (NOT auto-rejection).
//
// Placement: standalone component for now — N4.0 (BC + solver merge)
// decides where it sits in the unified Step 3+4 workbench view. The
// charter §"Step 3 panel placement" defers placement to that merge.

import { useState } from "react";

import { api, ApiError } from "@/api/client";
import type {
  ApplicabilityBounds,
  MaterialContract,
  MaterialPresetView,
  PhysicsCommitResponse,
  RegimeContract,
  RegimeKind,
  RegimePresetView,
} from "@/types/physics";

import {
  MATERIAL_PRESETS_VIEW,
  REGIME_PRESETS_VIEW,
} from "./preset_library_view";

interface PhysicsPanelProps {
  caseId: string;
}

type LoadState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "ok"; response: PhysicsCommitResponse }
  | { status: "error"; message: string };

const NOW_ISO = (): string => new Date().toISOString();

function buildContractsFromMaterialPreset(
  preset: MaterialPresetView,
): MaterialContract {
  return {
    kind: "preset",
    preset_id: preset.preset_id,
    fluid: { ...preset.fluid },
    thermal: preset.thermal ? { ...preset.thermal } : null,
    citation: preset.citation,
    authored_at: NOW_ISO(),
  };
}

function buildContractsFromRegimePreset(
  preset: RegimePresetView,
): RegimeContract {
  return {
    kind: "preset",
    preset_id: preset.preset_id,
    regime: preset.regime,
    applicability: { ...preset.applicability },
    citation: preset.citation,
    authored_at: NOW_ISO(),
  };
}

export function PhysicsPanel({ caseId }: PhysicsPanelProps) {
  const [materialPresetId, setMaterialPresetId] = useState<string>(
    MATERIAL_PRESETS_VIEW[0]?.preset_id ?? "",
  );
  const [regimePresetId, setRegimePresetId] = useState<string>(
    REGIME_PRESETS_VIEW[0]?.preset_id ?? "",
  );
  const [state, setState] = useState<LoadState>({ status: "idle" });

  const selectedMaterial = MATERIAL_PRESETS_VIEW.find(
    (m) => m.preset_id === materialPresetId,
  );
  const selectedRegime = REGIME_PRESETS_VIEW.find(
    (r) => r.preset_id === regimePresetId,
  );

  const submit = async () => {
    if (!selectedMaterial || !selectedRegime) return;
    const material = buildContractsFromMaterialPreset(selectedMaterial);
    const regime = buildContractsFromRegimePreset(selectedRegime);
    setState({ status: "submitting" });
    try {
      const response = await api.commitPhysics(caseId, { material, regime });
      setState({ status: "ok", response });
    } catch (err) {
      let message = "physics commit failed";
      if (err instanceof ApiError) {
        message = `${err.status}: ${err.message}`;
      } else if (err instanceof Error) {
        message = err.message;
      }
      setState({ status: "error", message });
    }
  };

  return (
    <section
      data-testid="physics-panel"
      className="rounded-sm border border-surface-700 bg-surface-900/50 p-3"
    >
      <header>
        <h2 className="text-sm font-medium text-surface-100">Physics</h2>
        <p className="mt-0.5 text-[11px] text-surface-500">
          Pick a material + turbulence regime preset, or open the editor for
          custom values. Engineer applies; AI does not auto-write.
        </p>
      </header>

      {/* Material section */}
      <div className="mt-3">
        <label
          htmlFor="physics-material-preset"
          className="block text-[11px] uppercase tracking-wider text-surface-400"
        >
          Material
        </label>
        <select
          id="physics-material-preset"
          data-testid="physics-material-preset-select"
          className="mt-1 w-full rounded-sm border border-surface-700 bg-surface-950 px-2 py-1 font-mono text-[12px] text-surface-100"
          value={materialPresetId}
          onChange={(e) => setMaterialPresetId(e.target.value)}
        >
          {MATERIAL_PRESETS_VIEW.map((p) => (
            <option key={p.preset_id} value={p.preset_id}>
              {p.display_name}
            </option>
          ))}
        </select>
        {selectedMaterial && (
          <MaterialReadout preset={selectedMaterial} />
        )}
      </div>

      {/* Regime section */}
      <div className="mt-3">
        <label
          htmlFor="physics-regime-preset"
          className="block text-[11px] uppercase tracking-wider text-surface-400"
        >
          Turbulence regime
        </label>
        <select
          id="physics-regime-preset"
          data-testid="physics-regime-preset-select"
          className="mt-1 w-full rounded-sm border border-surface-700 bg-surface-950 px-2 py-1 font-mono text-[12px] text-surface-100"
          value={regimePresetId}
          onChange={(e) => setRegimePresetId(e.target.value)}
        >
          {REGIME_PRESETS_VIEW.map((p) => (
            <option key={p.preset_id} value={p.preset_id}>
              {p.display_name}
            </option>
          ))}
        </select>
        {selectedRegime && <RegimeReadout preset={selectedRegime} />}
      </div>

      {/* Commit */}
      <div className="mt-3 flex items-center justify-between">
        <button
          type="button"
          data-testid="physics-commit-button"
          className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 font-mono text-[11px] text-emerald-200 hover:bg-emerald-500/20 disabled:opacity-50"
          onClick={submit}
          disabled={
            !selectedMaterial ||
            !selectedRegime ||
            state.status === "submitting"
          }
        >
          {state.status === "submitting" ? "committing…" : "commit physics"}
        </button>
        {state.status === "ok" && (
          <span
            data-testid="physics-commit-ok"
            className="font-mono text-[11px] text-emerald-300"
          >
            wrote {state.response.written_paths.length} dict files at{" "}
            {state.response.committed_at}
          </span>
        )}
        {state.status === "error" && (
          <span
            data-testid="physics-commit-error"
            className="font-mono text-[11px] text-rose-300"
          >
            {state.message}
          </span>
        )}
      </div>
    </section>
  );
}

function MaterialReadout({ preset }: { preset: MaterialPresetView }) {
  return (
    <div
      data-testid="physics-material-readout"
      className="mt-1 space-y-0.5 rounded-sm border border-surface-800 bg-surface-950/50 p-2 font-mono text-[11px] text-surface-400"
    >
      <Row label="ρ" value={`${preset.fluid.density.toFixed(2)} kg/m³`} />
      <Row
        label="ν"
        value={`${preset.fluid.kinematic_viscosity.toExponential(3)} m²/s`}
      />
      {preset.fluid.prandtl !== null && (
        <Row label="Pr" value={preset.fluid.prandtl.toFixed(3)} />
      )}
      {preset.thermal && (
        <>
          <Row
            label="cp"
            value={`${preset.thermal.specific_heat.toFixed(0)} J/(kg·K)`}
          />
          <Row
            label="k"
            value={`${preset.thermal.thermal_conductivity.toFixed(3)} W/(m·K)`}
          />
        </>
      )}
      {!preset.thermal && (
        <Row label="thermal" value="(isothermal — no energy equation)" />
      )}
      <CitationRow url={preset.citation} />
    </div>
  );
}

function RegimeReadout({ preset }: { preset: RegimePresetView }) {
  return (
    <div
      data-testid="physics-regime-readout"
      className="mt-1 space-y-0.5 rounded-sm border border-surface-800 bg-surface-950/50 p-2 font-mono text-[11px] text-surface-400"
    >
      <Row label="regime" value={preset.regime} />
      <ApplicabilityRow bounds={preset.applicability} />
      <CitationRow url={preset.citation} />
      {preset.notes && (
        <p className="mt-1 text-[10px] italic text-surface-500">
          {preset.notes}
        </p>
      )}
    </div>
  );
}

function ApplicabilityRow({ bounds }: { bounds: ApplicabilityBounds }) {
  const parts: string[] = [];
  if (bounds.re_min !== null) parts.push(`Re ≥ ${bounds.re_min}`);
  if (bounds.re_max !== null) parts.push(`Re ≤ ${bounds.re_max}`);
  if (bounds.mach_max !== null) parts.push(`Ma ≤ ${bounds.mach_max}`);
  if (bounds.y_plus_target !== null) {
    parts.push(`y⁺ ~ ${bounds.y_plus_target}`);
  }
  if (parts.length === 0) {
    return <Row label="applicability" value="(no documented bounds)" />;
  }
  return <Row label="applicability" value={parts.join(" · ")} />;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-surface-500">{label}:</span>
      <span className="text-surface-200">{value}</span>
    </div>
  );
}

function CitationRow({ url }: { url: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-surface-500">cite:</span>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="truncate text-sky-300 hover:underline"
      >
        {url}
      </a>
    </div>
  );
}
