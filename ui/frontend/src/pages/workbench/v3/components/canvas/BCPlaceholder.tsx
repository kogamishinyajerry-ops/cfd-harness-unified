/**
 * V71-UI-V3 · BCPlaceholder · color-coded boundary patches
 * Per Image 04 · uses v3 dusty CFD palette (inlet/wall/symmetry/custom).
 *
 * V71.H · BCViewportLayer — locked dusty palette mapped 1:1 to the
 * Tailwind v3.* tokens (defined in ui/frontend/tailwind.config.ts).
 * The SVG strokes use hex inline because SVG attributes can't reference
 * Tailwind classes; the values MUST stay byte-identical to the token
 * definitions or the visual baseline regresses.
 *
 *   inlet     = v3.inlet     #5b8a73 (dusty green)
 *   wall      = v3.wall      #a66060 (dusty red)
 *   symmetry  = v3.symmetry  #a89060 (dusty amber)
 *   custom    = v3.custom    #6f7a96 (dusty steel)
 */
const BC_PALETTE = {
  inlet: "#5b8a73",
  wall: "#a66060",
  symmetry: "#a89060",
  custom: "#6f7a96",
} as const;
interface BCPlaceholderProps {
  caseId: string;
}

export function BCPlaceholder({ caseId }: BCPlaceholderProps) {
  // BFS-style coloring works for any geometry; we draw a simple representative
  // shape annotated with the 4 BC types in v3 dusty palette.
  return (
    <div
      data-testid="canvas-bc"
      className="h-full w-full flex flex-col items-center justify-center"
    >
      <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-3">
        {caseId} · BC patches color-coded
      </div>
      <svg viewBox="0 0 800 400" className="w-[80%] max-w-[700px]">
        {/* main domain */}
        <path
          d="M 100 280 L 350 280 L 350 175 L 700 175 L 700 280 L 100 280 Z"
          fill="none"
          stroke="#3a3a42"
          strokeWidth="1"
        />
        {/* INLET · left vertical (dusty green) */}
        <g data-bc-type="inlet" data-testid="bc-patch-inlet">
          <line x1="100" y1="280" x2="100" y2="175" stroke={BC_PALETTE.inlet} strokeWidth="4" opacity="0.6" />
          <text x="50" y="232" fill={BC_PALETTE.inlet} fontSize="11" fontFamily="Inter">inlet</text>
        </g>

        {/* OUTLET · right vertical (dusty steel blue) */}
        <g data-bc-type="custom" data-testid="bc-patch-outlet">
          <line x1="700" y1="175" x2="700" y2="280" stroke={BC_PALETTE.custom} strokeWidth="4" opacity="0.6" />
          <text x="715" y="232" fill={BC_PALETTE.custom} fontSize="11" fontFamily="Inter">outlet_top</text>
        </g>

        {/* WALLS · floor + step face + ceiling (dusty red) */}
        <g data-bc-type="wall" data-testid="bc-patch-walls">
          <line x1="100" y1="280" x2="700" y2="280" stroke={BC_PALETTE.wall} strokeWidth="4" opacity="0.6" />
          <line x1="350" y1="280" x2="350" y2="175" stroke={BC_PALETTE.wall} strokeWidth="4" opacity="0.6" />
          <line x1="350" y1="175" x2="700" y2="175" stroke={BC_PALETTE.wall} strokeWidth="4" opacity="0.6" />
          <text x="200" y="300" fill={BC_PALETTE.wall} fontSize="11" fontFamily="Inter">wall_floor</text>
          <text x="360" y="225" fill={BC_PALETTE.wall} fontSize="11" fontFamily="Inter">wall_step</text>
        </g>

        {/* SYMMETRY · front face label (dusty amber, hint) */}
        <g data-bc-type="symmetry" data-testid="bc-patch-symmetry">
          <text x="380" y="160" fill={BC_PALETTE.symmetry} fontSize="11" fontFamily="Inter">symmetry_front</text>
        </g>
      </svg>
    </div>
  );
}
