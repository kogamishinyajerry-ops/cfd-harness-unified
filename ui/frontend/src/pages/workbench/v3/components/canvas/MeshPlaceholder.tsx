/**
 * V71-UI-V3 · MeshPlaceholder · wireframe grid pattern + refinement zones
 * Per Image 03/08 · hex-dominant mesh visualization.
 */
interface MeshPlaceholderProps {
  caseId: string;
}

export function MeshPlaceholder({ caseId }: MeshPlaceholderProps) {
  // Generate a 17x17 grid for lid_driven_cavity, 30×15 for others
  const isCavity = caseId.includes("cavity");
  const cols = isCavity ? 17 : 30;
  const rows = isCavity ? 17 : 15;
  const width = 700;
  const height = 350;
  const dx = width / cols;
  const dy = height / rows;
  const xOffset = 50;
  const yOffset = 25;

  // Build grid lines
  const verticals = [];
  for (let i = 0; i <= cols; i++) {
    const x = xOffset + i * dx;
    verticals.push(
      <line
        key={`v-${i}`}
        x1={x}
        y1={yOffset}
        x2={x}
        y2={yOffset + height}
        stroke="#2e2e34"
        strokeWidth="0.5"
      />,
    );
  }
  const horizontals = [];
  for (let i = 0; i <= rows; i++) {
    const y = yOffset + i * dy;
    horizontals.push(
      <line
        key={`h-${i}`}
        x1={xOffset}
        y1={y}
        x2={xOffset + width}
        y2={y}
        stroke="#2e2e34"
        strokeWidth="0.5"
      />,
    );
  }

  return (
    <div
      data-testid="canvas-mesh"
      className="h-full w-full flex flex-col items-center justify-center"
    >
      <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-3">
        {caseId} · {isCavity ? "uniform blockMesh 17×17" : "snappyHexMesh"}
      </div>
      <svg viewBox="0 0 800 400" className="w-[80%] max-w-[700px]">
        {/* Outline rect */}
        <rect
          x={xOffset}
          y={yOffset}
          width={width}
          height={height}
          fill="none"
          stroke="#3a3a42"
          strokeWidth="1"
        />
        {verticals}
        {horizontals}
      </svg>
    </div>
  );
}
