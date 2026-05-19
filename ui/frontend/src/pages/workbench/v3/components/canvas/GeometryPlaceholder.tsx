/**
 * V71-UI-V3 · GeometryPlaceholder · SVG wireframe geometry placeholder
 * Per Image 02 (naca0012 airfoil profile) · neutral substrate render.
 * Variant 'field' colors the surface with viridis-style gradient.
 */
import type { ReactNode } from "react";

interface GeometryPlaceholderProps {
  caseId: string;
  variant?: "default" | "field";
}

function shapeForCase(caseId: string): ReactNode {
  if (caseId.includes("airfoil") || caseId.includes("naca")) {
    return (
      <path
        d="M 100 200 Q 200 100, 400 130 Q 600 160, 700 200 Q 600 240, 400 270 Q 200 240, 100 200 Z"
        fill="#16161a"
        stroke="#3a3a42"
        strokeWidth="1"
      />
    );
  }
  if (caseId.includes("cavity")) {
    return (
      <rect
        x="200"
        y="100"
        width="400"
        height="200"
        fill="#16161a"
        stroke="#3a3a42"
        strokeWidth="1"
      />
    );
  }
  if (caseId.includes("backward") || caseId.includes("step")) {
    return (
      <path
        d="M 100 250 L 350 250 L 350 175 L 700 175 L 700 250 L 100 250 Z"
        fill="#16161a"
        stroke="#3a3a42"
        strokeWidth="1"
      />
    );
  }
  if (caseId.includes("cylinder")) {
    return (
      <>
        <rect x="100" y="100" width="600" height="200" fill="none" stroke="#3a3a42" strokeWidth="1" />
        <circle cx="300" cy="200" r="40" fill="#16161a" stroke="#3a3a42" strokeWidth="1" />
      </>
    );
  }
  // Default ellipse
  return (
    <ellipse
      cx="400"
      cy="200"
      rx="220"
      ry="60"
      fill="#16161a"
      stroke="#3a3a42"
      strokeWidth="1"
    />
  );
}

export function GeometryPlaceholder({ caseId, variant = "default" }: GeometryPlaceholderProps) {
  return (
    <div
      data-testid="canvas-geometry"
      data-variant={variant}
      className="h-full w-full flex flex-col items-center justify-center"
    >
      <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-3">
        {caseId} · CAD substrate
      </div>
      <svg viewBox="0 0 800 400" className="w-[80%] max-w-[700px]">
        {shapeForCase(caseId)}
      </svg>
    </div>
  );
}
