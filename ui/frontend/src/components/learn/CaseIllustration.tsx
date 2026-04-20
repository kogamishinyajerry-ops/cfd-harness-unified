// Line-art SVG illustrations, one per case. Each is a 240×160 viewBox,
// strokes only (no fills except for wall/plate indicators), so they scale
// cleanly on catalog cards and in hero regions.
//
// Design rules:
// - currentColor for primary strokes (picks up text color of container)
// - Contract-pass / contract-hazard / contract-fail kept OUT of here so
//   the illustration stays neutral; status is communicated elsewhere
// - Never render text labels inside the SVG — the learning narrative
//   lives in learnCases.ts, not baked into pictures

import { type ReactNode } from "react";

type IllustrationProps = {
  className?: string;
};

const STROKE = "1.6";
const ACCENT = "text-sky-400";
// Walls / frames use a brighter base. Illustrations sit against a very
// dark surface (surface-950) where surface-200 vanishes; surface-100 is
// the minimum contrast where line-art reads at card size.

function Frame({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <svg
      viewBox="0 0 240 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      {children}
    </svg>
  );
}

function LidDrivenCavity({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* Cavity walls */}
      <rect x="60" y="30" width="120" height="100" stroke="currentColor" strokeWidth={STROKE} />
      {/* Lid motion arrows (top edge) */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        <line x1="75" y1="22" x2="95" y2="22" />
        <polyline points="90,18 95,22 90,26" />
        <line x1="110" y1="22" x2="130" y2="22" />
        <polyline points="125,18 130,22 125,26" />
        <line x1="145" y1="22" x2="165" y2="22" />
        <polyline points="160,18 165,22 160,26" />
      </g>
      {/* Spiral vortex (approx log-spiral arc sequence) */}
      <g stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round" opacity="0.72">
        <path d="M 120 80 C 140 80, 150 100, 130 110 C 105 115, 92 95, 110 78 C 130 62, 160 70, 160 95" />
        <path d="M 120 90 C 130 92, 134 100, 126 103" opacity="0.5" />
      </g>
    </Frame>
  );
}

function BackwardFacingStep({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* Channel (step geometry): upstream duct, then drop, then downstream floor */}
      <path
        d="M 20 55 L 110 55 L 110 110 L 220 110"
        stroke="currentColor"
        strokeWidth={STROKE}
        fill="none"
      />
      <path d="M 20 30 L 220 30" stroke="currentColor" strokeWidth={STROKE} fill="none" />
      {/* Wall hatching at floor (short diagonal ticks) */}
      <g stroke="currentColor" strokeWidth="0.6" opacity="0.5">
        {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
          <line key={i} x1={30 + i * 12} y1="55" x2={34 + i * 12} y2="59" />
        ))}
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
          <line key={`b${i}`} x1={120 + i * 10} y1="110" x2={124 + i * 10} y2="114" />
        ))}
        {[0, 1, 2, 3, 4].map((i) => (
          <line key={`s${i}`} x1="110" y1={60 + i * 10} x2="114" y2={63 + i * 10} />
        ))}
      </g>
      {/* Flow arrows upstream */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        <line x1="30" y1="42" x2="70" y2="42" />
        <polyline points="64,38 70,42 64,46" />
      </g>
      {/* Recirculation arc behind step */}
      <path
        d="M 110 100 C 130 95, 150 100, 160 110"
        stroke="currentColor"
        strokeWidth={STROKE}
        opacity="0.6"
      />
      <path
        d="M 160 108 C 150 105, 135 98, 125 88"
        stroke="currentColor"
        strokeWidth={STROKE}
        opacity="0.6"
      />
      {/* Reattachment marker downstream */}
      <circle cx="175" cy="110" r="2.5" fill="currentColor" opacity="0.9" />
      {/* Downstream flow arrow */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        <line x1="185" y1="85" x2="215" y2="85" />
        <polyline points="209,81 215,85 209,89" />
      </g>
    </Frame>
  );
}

function CircularCylinderWake({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* Inflow arrows */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        {[55, 80, 105].map((y) => (
          <g key={y}>
            <line x1="10" y1={y} x2="45" y2={y} />
            <polyline points={`39,${y - 4} 45,${y} 39,${y + 4}`} />
          </g>
        ))}
      </g>
      {/* Cylinder */}
      <circle cx="75" cy="80" r="14" stroke="currentColor" strokeWidth={STROKE} />
      {/* Vortex street (alternating + / − markers) */}
      <g stroke="currentColor" strokeWidth={STROKE}>
        {[{ x: 110, y: 68, s: "+" }, { x: 130, y: 92, s: "−" }, { x: 150, y: 68, s: "+" }, { x: 170, y: 92, s: "−" }, { x: 190, y: 68, s: "+" }].map(
          (m, i) => (
            <g key={i}>
              <circle cx={m.x} cy={m.y} r="6" fill="none" opacity="0.7" />
              <text
                x={m.x}
                y={m.y + 3.5}
                fontSize="9"
                textAnchor="middle"
                stroke="none"
                fill="currentColor"
                fontFamily="JetBrains Mono, monospace"
                opacity="0.7"
              >
                {m.s}
              </text>
            </g>
          ),
        )}
      </g>
    </Frame>
  );
}

function TurbulentFlatPlate({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* Plate (bottom solid) */}
      <line x1="20" y1="120" x2="220" y2="120" stroke="currentColor" strokeWidth="2" />
      <g stroke="currentColor" strokeWidth="0.6" opacity="0.5">
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
          <line key={i} x1={25 + i * 20} y1="120" x2={30 + i * 20} y2="126" />
        ))}
      </g>
      {/* Boundary-layer profile — multiple U arrows of growing length */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        {[
          { x: 40, h: 25 },
          { x: 75, h: 40 },
          { x: 120, h: 55 },
          { x: 170, h: 70 },
          { x: 210, h: 80 },
        ].map((a, i) => (
          <g key={i}>
            {[0.3, 0.55, 0.8, 1.0].map((frac, j) => {
              const y = 120 - a.h * frac;
              const len = 14 + 10 * frac;
              return (
                <g key={j}>
                  <line x1={a.x} y1={y} x2={a.x + len} y2={y} opacity={0.45 + frac * 0.55} />
                  <polyline
                    points={`${a.x + len - 4},${y - 3} ${a.x + len},${y} ${a.x + len - 4},${y + 3}`}
                    opacity={0.45 + frac * 0.55}
                  />
                </g>
              );
            })}
          </g>
        ))}
      </g>
      {/* Envelope (BL edge) */}
      <path
        d="M 20 115 C 60 105, 110 80, 170 55 C 200 42, 220 38, 225 36"
        stroke="currentColor"
        strokeWidth={STROKE}
        opacity="0.45"
        strokeDasharray="3 3"
      />
    </Frame>
  );
}

function PlaneChannelFlow({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* Two parallel plates */}
      <line x1="20" y1="40" x2="220" y2="40" stroke="currentColor" strokeWidth="2" />
      <line x1="20" y1="120" x2="220" y2="120" stroke="currentColor" strokeWidth="2" />
      {/* Wall hatching */}
      <g stroke="currentColor" strokeWidth="0.6" opacity="0.5">
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
          <line key={`t${i}`} x1={25 + i * 20} y1="40" x2={30 + i * 20} y2="34" />
        ))}
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
          <line key={`b${i}`} x1={25 + i * 20} y1="120" x2={30 + i * 20} y2="126" />
        ))}
      </g>
      {/* Parabolic-ish velocity profile rendered as arrows */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        {[0.12, 0.28, 0.45, 0.6, 0.74, 0.86, 0.94, 0.96, 0.94, 0.86, 0.74, 0.6, 0.45, 0.28, 0.12].map(
          (frac, i) => {
            const y = 48 + i * 4.8;
            const len = 30 + 40 * frac;
            return (
              <g key={i}>
                <line x1="95" y1={y} x2={95 + len} y2={y} opacity={0.3 + frac * 0.6} />
                <polyline
                  points={`${95 + len - 4},${y - 3} ${95 + len},${y} ${95 + len - 4},${y + 3}`}
                  opacity={0.3 + frac * 0.6}
                />
              </g>
            );
          },
        )}
      </g>
    </Frame>
  );
}

function AxisymmetricImpingingJet({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* Nozzle (top) */}
      <path d="M 100 20 L 100 60 M 140 20 L 140 60" stroke="currentColor" strokeWidth={STROKE} />
      <line x1="90" y1="20" x2="150" y2="20" stroke="currentColor" strokeWidth={STROKE} />
      {/* Jet arrows down */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        {[110, 120, 130].map((x) => (
          <g key={x}>
            <line x1={x} y1="65" x2={x} y2="108" />
            <polyline points={`${x - 4},102 ${x},108 ${x + 4},102`} />
          </g>
        ))}
      </g>
      {/* Target plate */}
      <line x1="20" y1="125" x2="220" y2="125" stroke="currentColor" strokeWidth="2" />
      <g stroke="currentColor" strokeWidth="0.6" opacity="0.5">
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
          <line key={i} x1={25 + i * 20} y1="125" x2={30 + i * 20} y2="131" />
        ))}
      </g>
      {/* Stagnation + radial spread arrows */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round" opacity="0.7">
        <path d="M 100 115 C 75 115, 60 115, 40 115" />
        <polyline points="44,111 40,115 44,119" />
        <path d="M 140 115 C 165 115, 180 115, 200 115" />
        <polyline points="196,111 200,115 196,119" />
      </g>
      {/* Stagnation point */}
      <circle cx="120" cy="125" r="2.5" fill="currentColor" opacity="0.8" />
    </Frame>
  );
}

function NacaAirfoil({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* NACA 0012-ish symmetric profile (cubic bezier both sides) */}
      <path
        d="M 40 80 C 60 50, 120 50, 180 70 L 200 80 L 180 90 C 120 110, 60 110, 40 80 Z"
        stroke="currentColor"
        strokeWidth={STROKE}
        fill="none"
      />
      {/* Chord line */}
      <line
        x1="40"
        y1="80"
        x2="200"
        y2="80"
        stroke="currentColor"
        strokeWidth="0.6"
        strokeDasharray="2 3"
        opacity="0.4"
      />
      {/* Inflow arrows */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        {[55, 75, 95].map((y) => (
          <g key={y}>
            <line x1="8" y1={y} x2="28" y2={y} />
            <polyline points={`22,${y - 4} 28,${y} 22,${y + 4}`} />
          </g>
        ))}
      </g>
      {/* Streamline curving over upper surface */}
      <path
        d="M 28 55 C 70 35, 140 38, 210 55"
        stroke="currentColor"
        strokeWidth={STROKE}
        opacity="0.55"
      />
      <path
        d="M 28 100 C 70 120, 140 118, 210 100"
        stroke="currentColor"
        strokeWidth={STROKE}
        opacity="0.4"
      />
    </Frame>
  );
}

function RayleighBenard({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* Top cold plate */}
      <line x1="20" y1="30" x2="220" y2="30" stroke="currentColor" strokeWidth="2" />
      <text
        x="230"
        y="34"
        fontSize="9"
        stroke="none"
        fill="currentColor"
        opacity="0.5"
        fontFamily="JetBrains Mono, monospace"
      >
        c
      </text>
      {/* Bottom hot plate */}
      <line x1="20" y1="130" x2="220" y2="130" stroke="currentColor" strokeWidth="2" />
      <text
        x="230"
        y="134"
        fontSize="9"
        stroke="none"
        fill="currentColor"
        opacity="0.5"
        fontFamily="JetBrains Mono, monospace"
      >
        h
      </text>
      {/* Convection rolls — 3 circular arrows alternating direction */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        {[
          { cx: 55, cy: 80, dir: 1 },
          { cx: 120, cy: 80, dir: -1 },
          { cx: 185, cy: 80, dir: 1 },
        ].map((c, i) => (
          <g key={i}>
            <circle cx={c.cx} cy={c.cy} r="28" fill="none" opacity="0.5" />
            {/* tick at 0° or 180° with a small arrowhead */}
            {c.dir === 1 ? (
              <polyline
                points={`${c.cx + 26},${c.cy - 6} ${c.cx + 28},${c.cy} ${c.cx + 32},${c.cy - 4}`}
                fill="none"
              />
            ) : (
              <polyline
                points={`${c.cx - 26},${c.cy + 6} ${c.cx - 28},${c.cy} ${c.cx - 32},${c.cy + 4}`}
                fill="none"
              />
            )}
          </g>
        ))}
      </g>
    </Frame>
  );
}

function DifferentialHeatedCavity({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* Cavity frame */}
      <rect x="60" y="30" width="120" height="100" stroke="currentColor" strokeWidth={STROKE} />
      {/* Hot wall (left, red) */}
      <line x1="60" y1="30" x2="60" y2="130" stroke="#f87171" strokeWidth="3" />
      <text
        x="46"
        y="86"
        fontSize="10"
        stroke="none"
        fill="#f87171"
        opacity="0.85"
        fontFamily="JetBrains Mono, monospace"
      >
        T_h
      </text>
      {/* Cold wall (right, blue) */}
      <line x1="180" y1="30" x2="180" y2="130" stroke="#60a5fa" strokeWidth="3" />
      <text
        x="190"
        y="86"
        fontSize="10"
        stroke="none"
        fill="#60a5fa"
        opacity="0.85"
        fontFamily="JetBrains Mono, monospace"
      >
        T_c
      </text>
      {/* Circulation arrow inside */}
      <g className={ACCENT} stroke="currentColor" strokeWidth={STROKE} strokeLinecap="round">
        <path d="M 90 60 C 120 45, 150 45, 165 70 C 170 95, 150 118, 120 116 C 85 113, 70 90, 85 65" />
        <polyline points="88 68 85 65 90 62" />
      </g>
    </Frame>
  );
}

function DuctFlow({ className }: IllustrationProps) {
  return (
    <Frame className={className}>
      {/* Square duct cross-section (slightly oblique for depth) */}
      {/* Front face */}
      <rect x="60" y="40" width="90" height="90" stroke="currentColor" strokeWidth={STROKE} />
      {/* Back face (offset) */}
      <rect x="95" y="25" width="90" height="90" stroke="currentColor" strokeWidth={STROKE} opacity="0.45" />
      {/* Connecting edges */}
      <g stroke="currentColor" strokeWidth={STROKE} opacity="0.45">
        <line x1="60" y1="40" x2="95" y2="25" />
        <line x1="150" y1="40" x2="185" y2="25" />
        <line x1="60" y1="130" x2="95" y2="115" />
        <line x1="150" y1="130" x2="185" y2="115" />
      </g>
      {/* Flow-into-page dots (circle-with-dot glyphs = velocity out of page) */}
      <g stroke="currentColor" strokeWidth={STROKE}>
        {[
          [80, 60],
          [105, 60],
          [130, 60],
          [80, 85],
          [105, 85],
          [130, 85],
          [80, 110],
          [105, 110],
          [130, 110],
        ].map(([cx, cy], i) => (
          <g key={i} className={ACCENT}>
            <circle cx={cx} cy={cy} r="4" fill="none" opacity="0.65" />
            <circle cx={cx} cy={cy} r="1.2" fill="currentColor" opacity="0.9" />
          </g>
        ))}
      </g>
      {/* Corner secondary-flow arc (hint at anisotropy) */}
      <path
        d="M 66 46 C 72 52, 78 54, 82 50"
        stroke="currentColor"
        strokeWidth={STROKE}
        opacity="0.45"
      />
    </Frame>
  );
}

const ILLUSTRATIONS: Record<string, (p: IllustrationProps) => ReactNode> = {
  lid_driven_cavity: LidDrivenCavity,
  backward_facing_step: BackwardFacingStep,
  circular_cylinder_wake: CircularCylinderWake,
  turbulent_flat_plate: TurbulentFlatPlate,
  plane_channel_flow: PlaneChannelFlow,
  impinging_jet: AxisymmetricImpingingJet,
  naca0012_airfoil: NacaAirfoil,
  rayleigh_benard_convection: RayleighBenard,
  differential_heated_cavity: DifferentialHeatedCavity,
  duct_flow: DuctFlow,
};

export function CaseIllustration({
  caseId,
  className = "w-full h-auto text-surface-100",
}: {
  caseId: string;
  className?: string;
}) {
  const Cmp = ILLUSTRATIONS[caseId];
  if (!Cmp) {
    return (
      <Frame className={className}>
        <rect x="20" y="20" width="200" height="120" stroke="currentColor" strokeWidth="1" strokeDasharray="4 4" opacity="0.4" />
      </Frame>
    );
  }
  return <>{Cmp({ className })}</>;
}
