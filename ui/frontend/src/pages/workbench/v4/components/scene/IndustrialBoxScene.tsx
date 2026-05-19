/**
 * V4 · IndustrialBoxScene · stylized isometric SVG · per UI-SPEC §3
 *
 * Glass-walled enclosure + central engine assembly. Variants tune visual
 * treatment per mode (CAD color · wireframe · velocity wash · contour · etc).
 *
 * Composition rules:
 *   - Walls are translucent (12-18% fill opacity) so engine is visible.
 *   - Ground plane has subtle radial shadow beneath engine.
 *   - Engine has ≥3 visual zones (compressor / combustor / turbine) to
 *     suggest mechanical detail rather than a single bare cylinder.
 *   - Rotor disc shows ≥6 blade lines (rotating in solver mode).
 *   - Two mounting struts to ground for grounded mass feel.
 *   - SVG nodes per scene ≤600 for browser perf.
 *
 * Pure SVG · zero deps · server-renderable. Real three.js integration is
 * a later arc.
 */
import type { ReactNode } from "react";

import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";

export type SceneVariant =
  | "geometry"
  | "mesh"
  | "physics"
  | "boundary"
  | "solver"
  | "post"
  | "doe";

interface IndustrialBoxSceneProps {
  variant: SceneVariant;
  /** Optional overlay slot · BC labels · streamlines · contour overlays. */
  children?: ReactNode;
  /** Slot rendered BENEATH engine but above floor · ground shadows etc. */
  underEngine?: ReactNode;
  /** Slot rendered AS engine body fill · contour mode paints colormap here. */
  bodyOverlay?: ReactNode;
  className?: string;
  /** Whether the rotor disc animates (solver mode). */
  rotorSpin?: boolean;
}

interface Recipe {
  // body
  bodyCompressor: string;
  bodyCombustor: string;
  bodyTurbine: string;
  bodyHighlight: string;
  nozzle: string;
  rotor: string;
  rotorRing: string;
  // box
  wallFill: string;
  wallOpacity: number;
  boxEdge: string;
  boxFloor: string;
  floorGrid: string;
  // accent
  panelLight: string;
}

function recipeFor(variant: SceneVariant): Recipe {
  // All scene-fill values now reference V4_PALETTE tokens (scene · cadParts ·
  // CFD colormap entries). No off-token hex below this line.
  const cm = V4_CFD_COLORMAP;
  const base: Recipe = {
    bodyCompressor: V4_PALETTE.scene.engineNeutralLow,
    bodyCombustor: V4_PALETTE.scene.engineNeutralMid,
    bodyTurbine: V4_PALETTE.scene.engineNeutralLow,
    bodyHighlight: V4_PALETTE.scene.engineNeutralHi,
    nozzle: V4_PALETTE.scene.nozzleNeutral,
    rotor: V4_PALETTE.textTertiary,
    rotorRing: V4_PALETTE.border,
    wallFill: V4_PALETTE.surfaceRaised,
    wallOpacity: 0.18,
    boxEdge: V4_PALETTE.border,
    boxFloor: V4_PALETTE.surface,
    floorGrid: V4_PALETTE.border,
    panelLight: V4_PALETTE.borderActive,
  };

  switch (variant) {
    case "geometry":
      return {
        ...base,
        bodyCompressor: V4_PALETTE.cadParts.inletShell,
        bodyCombustor: V4_PALETTE.cadParts.combustor,
        bodyTurbine: V4_PALETTE.cadParts.turbine,
        bodyHighlight: V4_PALETTE.cadParts.compressor,
        nozzle: V4_PALETTE.cadParts.nozzle,
        wallOpacity: 0.14,
      };
    case "mesh":
      return {
        ...base,
        bodyCompressor: V4_PALETTE.scene.bodyDarkSlate,
        bodyCombustor: V4_PALETTE.scene.bodyMeshMid,
        bodyTurbine: V4_PALETTE.scene.bodyDarkSlate,
        bodyHighlight: V4_PALETTE.scene.bodyDarkSlateHi,
      };
    case "physics":
      return {
        ...base,
        bodyCompressor: cm[1], // cyan
        bodyCombustor: cm[3], // yellow
        bodyTurbine: cm[4], // orange
        bodyHighlight: cm[2], // green
        nozzle: cm[5], // red
        wallOpacity: 0.12,
      };
    case "boundary":
      return base;
    case "solver":
      return {
        ...base,
        bodyCompressor: V4_PALETTE.scene.bodyHotSlate,
        bodyCombustor: V4_PALETTE.scene.bodyHotMid,
        bodyTurbine: V4_PALETTE.scene.bodyHotHi,
        bodyHighlight: cm[4], // orange
        nozzle: cm[5], // red
      };
    case "post":
      return {
        ...base,
        bodyCompressor: cm[0], // deep blue
        bodyCombustor: cm[2], // green
        bodyTurbine: cm[3], // yellow
        bodyHighlight: cm[4], // orange
        nozzle: cm[5], // red
        wallOpacity: 0.10,
      };
    case "doe":
      return base;
  }
}

export function IndustrialBoxScene({
  variant,
  children,
  underEngine,
  bodyOverlay,
  className,
  rotorSpin = false,
}: IndustrialBoxSceneProps) {
  const p = recipeFor(variant);
  const isMesh = variant === "mesh";

  // ViewBox 640×360.
  // Iso projection corners.
  // Front face: rectangle from (80,230) to (480,70) — actually we use a
  // slanted hexagonal outline so the box reads as 3D.
  // Box vertices: F=front, B=back. L=left, R=right. T=top, b=bottom.
  const FbL = { x: 80, y: 240 };
  const FbR = { x: 480, y: 240 };
  const FtL = { x: 80, y: 60 };
  const FtR = { x: 480, y: 60 };
  const BbL = { x: 200, y: 190 };
  const BbR = { x: 600, y: 190 };
  const BtL = { x: 200, y: 10 };
  const BtR = { x: 600, y: 10 };

  return (
    <svg
      viewBox="0 0 640 360"
      preserveAspectRatio="xMidYMid meet"
      className={className}
      data-testid="v4-industrial-box-scene"
      data-variant={variant}
    >
      <defs>
        {/* Floor grid */}
        <pattern
          id={`floor-grid-${variant}`}
          width="22"
          height="22"
          patternUnits="userSpaceOnUse"
          patternTransform="skewX(-30) skewY(0)"
        >
          <path
            d="M22 0H0v22"
            fill="none"
            stroke={p.floorGrid}
            strokeWidth="0.4"
            opacity="0.45"
          />
        </pattern>
        {/* Mesh-mode hatching */}
        <pattern id="mesh-hatch" width="5" height="5" patternUnits="userSpaceOnUse">
          <path d="M5 0L0 5" stroke={V4_PALETTE.border} strokeWidth="0.35" />
        </pattern>
        {/* Engine gradient */}
        <linearGradient id={`engine-grad-${variant}`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor={p.bodyCompressor} />
          <stop offset="35%" stopColor={p.bodyHighlight} />
          <stop offset="65%" stopColor={p.bodyHighlight} />
          <stop offset="100%" stopColor={p.bodyTurbine} />
        </linearGradient>
        {/* Wall gradient · slight top-to-bottom shading */}
        <linearGradient id={`wall-grad-${variant}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={p.wallFill} stopOpacity={p.wallOpacity * 0.6} />
          <stop offset="100%" stopColor={p.wallFill} stopOpacity={p.wallOpacity * 1.4} />
        </linearGradient>
        {/* Ground shadow gradient */}
        <radialGradient id={`ground-shadow-${variant}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor={V4_PALETTE.scene.shadowBase} stopOpacity="0.55" />
          <stop offset="100%" stopColor={V4_PALETTE.scene.shadowBase} stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Floor */}
      <polygon
        points={`${FbL.x},${FbL.y} ${FbR.x},${FbR.y} ${BbR.x},${BbR.y} ${BbL.x},${BbL.y}`}
        fill={p.boxFloor}
        stroke={p.boxEdge}
        strokeWidth="0.6"
      />
      <polygon
        points={`${FbL.x},${FbL.y} ${FbR.x},${FbR.y} ${BbR.x},${BbR.y} ${BbL.x},${BbL.y}`}
        fill={`url(#floor-grid-${variant})`}
      />

      {/* Ground shadow ellipse under engine */}
      <ellipse
        cx="330"
        cy="226"
        rx="170"
        ry="14"
        fill={`url(#ground-shadow-${variant})`}
      />

      {/* Back wall · translucent */}
      <polygon
        points={`${BbL.x},${BbL.y} ${BbR.x},${BbR.y} ${BtR.x},${BtR.y} ${BtL.x},${BtL.y}`}
        fill={`url(#wall-grad-${variant})`}
        stroke={p.boxEdge}
        strokeWidth="0.6"
      />
      {/* Left wall · translucent */}
      <polygon
        points={`${FbL.x},${FbL.y} ${BbL.x},${BbL.y} ${BtL.x},${BtL.y} ${FtL.x},${FtL.y}`}
        fill={`url(#wall-grad-${variant})`}
        stroke={p.boxEdge}
        strokeWidth="0.6"
      />
      {/* Top edges (dashed outline only) */}
      <polyline
        points={`${FtL.x},${FtL.y} ${BtL.x},${BtL.y} ${BtR.x},${BtR.y} ${FtR.x},${FtR.y}`}
        fill="none"
        stroke={p.boxEdge}
        strokeWidth="0.5"
        strokeDasharray="3 4"
      />
      {/* Right wall outline (dashed · cutaway) */}
      <polyline
        points={`${FbR.x},${FbR.y} ${BbR.x},${BbR.y} ${BtR.x},${BtR.y} ${FtR.x},${FtR.y}`}
        fill="none"
        stroke={p.boxEdge}
        strokeWidth="0.5"
        strokeDasharray="3 4"
      />
      {/* Front outline · solid (open face) */}
      <polyline
        points={`${FtL.x},${FtL.y} ${FbL.x},${FbL.y} ${FbR.x},${FbR.y} ${FtR.x},${FtR.y}`}
        fill="none"
        stroke={p.boxEdge}
        strokeWidth="0.6"
      />

      {/* Service panels on left wall · subtle rectangles for industrial feel */}
      <g opacity="0.55">
        <rect x="100" y="200" width="36" height="22" fill={p.panelLight} opacity="0.4" />
        <rect x="142" y="200" width="22" height="22" fill={p.panelLight} opacity="0.3" />
        <rect x="100" y="90" width="60" height="14" fill={p.panelLight} opacity="0.35" />
      </g>

      {/* Slot: under-engine overlays (e.g. extra shadows) */}
      {underEngine}

      {/* Engine assembly */}
      <g data-testid="v4-scene-engine">
        {/* Nozzle cone (right tail) */}
        <polygon
          points="430,135 478,118 478,182 430,165 430,135"
          fill={p.nozzle}
          stroke={p.boxEdge}
          strokeWidth="0.45"
        />
        <polygon
          points="478,118 478,182 488,170 488,130 478,118"
          fill={p.nozzle}
          stroke={p.boxEdge}
          strokeWidth="0.4"
          opacity="0.7"
        />

        {/* Body (3 visual zones · gradient overlaps zones) */}
        {/* Compressor section */}
        <rect
          x="230"
          y="120"
          width="70"
          height="60"
          fill={`url(#engine-grad-${variant})`}
          stroke={p.boxEdge}
          strokeWidth="0.5"
        />
        {/* Combustor section */}
        <rect
          x="300"
          y="115"
          width="60"
          height="70"
          fill={p.bodyCombustor}
          stroke={p.boxEdge}
          strokeWidth="0.5"
        />
        {/* Turbine section */}
        <rect
          x="360"
          y="120"
          width="70"
          height="60"
          fill={`url(#engine-grad-${variant})`}
          stroke={p.boxEdge}
          strokeWidth="0.5"
        />
        {/* Body shading band · top highlight */}
        <rect x="230" y="120" width="200" height="6" fill={p.bodyHighlight} opacity="0.32" />
        {/* Body shading · bottom shadow */}
        <rect x="230" y="174" width="200" height="6" fill={V4_PALETTE.scene.shadowBase} opacity="0.18" />

        {/* Slot for caller-supplied body overlay (e.g. velocity contour) */}
        {bodyOverlay}

        {/* Mesh hatching on body */}
        {isMesh && (
          <rect
            x="230"
            y="120"
            width="200"
            height="60"
            fill="url(#mesh-hatch)"
            opacity="0.55"
            pointerEvents="none"
          />
        )}

        {/* Inter-section ribs */}
        <line x1="300" y1="115" x2="300" y2="185" stroke={p.boxEdge} strokeWidth="0.5" />
        <line x1="360" y1="115" x2="360" y2="185" stroke={p.boxEdge} strokeWidth="0.5" />

        {/* Right body cap before nozzle */}
        <ellipse cx="430" cy="150" rx="5" ry="30" fill={p.bodyHighlight} stroke={p.boxEdge} strokeWidth="0.4" />

        {/* Rotor disc (left intake) */}
        <g
          style={
            rotorSpin
              ? { transformOrigin: "230px 150px", animation: "v4-rotor 4s linear infinite" }
              : undefined
          }
        >
          <ellipse cx="230" cy="150" rx="10" ry="36" fill={p.rotor} stroke={p.rotorRing} strokeWidth="0.7" />
          <ellipse cx="230" cy="150" rx="4" ry="32" fill={V4_PALETTE.scene.shadowBase} opacity="0.18" />
          {/* 8 blade lines */}
          {[
            { x1: 230, y1: 114, x2: 218, y2: 100 },
            { x1: 230, y1: 186, x2: 218, y2: 200 },
            { x1: 225, y1: 120, x2: 214, y2: 110 },
            { x1: 225, y1: 180, x2: 214, y2: 190 },
            { x1: 222, y1: 130, x2: 210, y2: 122 },
            { x1: 222, y1: 170, x2: 210, y2: 178 },
            { x1: 220, y1: 140, x2: 208, y2: 134 },
            { x1: 220, y1: 160, x2: 208, y2: 166 },
          ].map((bl, i) => (
            <line
              key={i}
              x1={bl.x1}
              y1={bl.y1}
              x2={bl.x2}
              y2={bl.y2}
              stroke={p.rotorRing}
              strokeWidth="0.6"
              opacity="0.85"
            />
          ))}
          {/* Hub */}
          <circle cx="230" cy="150" r="4" fill={p.rotorRing} opacity="0.8" />
        </g>

        {/* Mounting struts to ground */}
        <polygon
          points="265,180 278,180 280,222 263,222"
          fill={p.bodyCompressor}
          stroke={p.boxEdge}
          strokeWidth="0.4"
          opacity="0.85"
        />
        <polygon
          points="382,180 395,180 397,222 380,222"
          fill={p.bodyCompressor}
          stroke={p.boxEdge}
          strokeWidth="0.4"
          opacity="0.85"
        />
        {/* Strut base shadow */}
        <rect x="261" y="221" width="22" height="2" fill={V4_PALETTE.scene.shadowBase} opacity="0.35" />
        <rect x="378" y="221" width="22" height="2" fill={V4_PALETTE.scene.shadowBase} opacity="0.35" />
      </g>

      {/* Caller-supplied overlay (streamlines · BC labels · etc) */}
      {children}

      {/* CSS keyframes (scoped to this SVG) */}
      <style>{`@keyframes v4-rotor { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </svg>
  );
}
