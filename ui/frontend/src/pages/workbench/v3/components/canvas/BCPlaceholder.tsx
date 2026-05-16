/**
 * V71-UI-V3 · BCPlaceholder · color-coded boundary patches
 * Per Image 04 · uses v3 dusty CFD palette (inlet/wall/symmetry/custom).
 */
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
        <line x1="100" y1="280" x2="100" y2="280" stroke="#5b8a73" strokeWidth="6" />
        <line x1="100" y1="280" x2="100" y2="175" stroke="#5b8a73" strokeWidth="4" opacity="0.6" />
        <text x="50" y="232" fill="#5b8a73" fontSize="11" fontFamily="Inter">inlet</text>

        {/* OUTLET · right vertical (dusty steel blue) */}
        <line x1="700" y1="175" x2="700" y2="280" stroke="#6f7a96" strokeWidth="4" opacity="0.6" />
        <text x="715" y="232" fill="#6f7a96" fontSize="11" fontFamily="Inter">outlet_top</text>

        {/* WALLS · floor + step face + ceiling (dusty red) */}
        <line x1="100" y1="280" x2="700" y2="280" stroke="#a66060" strokeWidth="4" opacity="0.6" />
        <line x1="350" y1="280" x2="350" y2="175" stroke="#a66060" strokeWidth="4" opacity="0.6" />
        <line x1="350" y1="175" x2="700" y2="175" stroke="#a66060" strokeWidth="4" opacity="0.6" />
        <text x="200" y="300" fill="#a66060" fontSize="11" fontFamily="Inter">wall_floor</text>
        <text x="360" y="225" fill="#a66060" fontSize="11" fontFamily="Inter">wall_step</text>

        {/* SYMMETRY · front face label (dusty amber, hint) */}
        <text x="380" y="160" fill="#a89060" fontSize="11" fontFamily="Inter">symmetry_front</text>
      </svg>
    </div>
  );
}
