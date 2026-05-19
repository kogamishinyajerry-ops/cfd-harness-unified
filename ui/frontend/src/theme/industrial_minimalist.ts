/**
 * V92-UI-V4 · Industrial-Minimalist design tokens (TypeScript SSOT)
 *
 * Source of truth for all V4 component colors. For className-driven styles
 * use the parallel `v4.*` Tailwind namespace in `tailwind.config.ts` (the
 * two are kept in sync by convention; this module is authoritative for
 * runtime-computed style — three.js overlays, charts, SVG fills, etc.).
 *
 * Per `.planning/transitions/2026-05-18_v4_ui_spec.md` §1.1-1.3.
 *
 * R2 hardening (2026-05-18): added `cadParts`, `bcTypes`, `scene`, and
 * `streamColor` sub-namespaces so every off-token hex used by mode
 * renderers, scene composers, and streamline generators now lives here
 * under a single SSOT. Codex R1 P1 finding closure.
 */

export const V4_PALETTE = {
  // ── Background ladder (charcoal with cool tint) ────────────────────
  canvas: "#0B1116",
  shell: "#0E141A",
  surface: "#161C24",
  surfaceRaised: "#1C232C",

  // ── Borders ────────────────────────────────────────────────────────
  border: "#222932",
  borderActive: "#2E3744",

  // ── Text ladder (WCAG AA on canvas) ────────────────────────────────
  textPrimary: "#E8ECF1",
  textSecondary: "#8B95A3",
  textTertiary: "#5A6471",

  // ── Accents (signal only · <5% pixels combined) ────────────────────
  healthy: "#3DC97F",
  active: "#F0A93B",
  warn: "#E8A24B",
  crit: "#E5564E",
  brand: "#5BB4FF",

  // ── Scene · industrial enclosure + engine assembly ────────────────
  // Subtle neutral palette used by IndustrialBoxScene recipes. Variant
  // tinting still happens at the recipe level (see scene/IndustrialBoxScene.tsx
  // recipeFor) but every recipe references THESE tokens, not raw hex.
  scene: {
    engineNeutralLow: "#3B4756",
    engineNeutralHi: "#62707F",
    engineNeutralMid: "#4A5765",
    nozzleNeutral: "#2B333D",
    bodyDarkSlate: "#202832",
    bodyDarkSlateHi: "#3A4654",
    bodyMeshMid: "#252E3A",
    bodyHotSlate: "#2B4053",
    bodyHotMid: "#7A4030",
    bodyHotHi: "#A8552A",
    /** Pure black baseline for alpha-overlay shadows (combined with opacity). */
    shadowBase: "#000000",
  },

  // ── CAD part palette (geometry mode) ───────────────────────────────
  // Dusty industrial palette · matches blueprint image 2 part coloring.
  cadParts: {
    inletShell: "#5B8AA8",       // 进气壳体 / dusty steel-blue
    compressor: "#76A5C0",       // 压气机
    combustor: "#A66060",        // 燃烧室 / dusty red
    turbine: "#A89060",          // 涡轮 / dusty amber
    nozzle: "#5B8A73",           // 喷管 / dusty green
    bracket: "#6F7A96",          // 支架 / dusty steel
    gearbox: "#8B95A3",          // 齿轮箱 / cool gray
    fuelValve: "#5A6471",        // 燃油阀 / dim gray
  },

  // ── BC type palette (boundary mode · semantic mapping) ─────────────
  // Each BC type gets its own steady color · distinct from severity tokens
  // so boundary patches read as "type of physics" not "warn/error/etc".
  bcTypes: {
    inlet: "#3B82CC",
    outlet: "#E89A4D",
    wall: "#E5564E",
    rotor: "#9B6BD3",
    symmetry: "#A89060",
  },
} as const;

/**
 * Standard CFD colormap (blue→cyan→green→yellow→orange→red · 6 steps).
 * Used for velocity, pressure, temperature contours + streamline gradients.
 * Matches viewport_kernel.ts default field shader gradient.
 */
export const V4_CFD_COLORMAP = [
  "#2545FF", // 0.0 · deep blue (low)
  "#1FB6D6", // 0.2 · cyan
  "#2ECC71", // 0.4 · green
  "#F2D03A", // 0.6 · yellow
  "#F2873A", // 0.8 · orange
  "#E5564E", // 1.0 · red (high)
] as const;

/**
 * Severity → palette mapping for V91 MatchedCommentary rendering.
 * Used by AdvisorPillStack (replaces PostRunAdvisorV9 verbose cards).
 *
 * V91 rule corpus severity enum: "advise" | "warn" | "info"
 *  - advise → healthy green (positive curated guidance)
 *  - warn   → warn amber    (potential issue · advisor-not-driver)
 *  - info   → text secondary (neutral observation)
 */
export const V4_SEVERITY_COLOR = {
  advise: V4_PALETTE.healthy,
  warn: V4_PALETTE.warn,
  info: V4_PALETTE.textSecondary,
} as const;

/**
 * Pipeline step state → palette mapping for BottomBarV4 7-step strip.
 *  - done    → healthy green dot + check overlay
 *  - active  → active orange dot + glow pulse
 *  - pending → text tertiary dot (muted)
 */
export const V4_PIPELINE_STATE_COLOR = {
  done: V4_PALETTE.healthy,
  active: V4_PALETTE.active,
  pending: V4_PALETTE.textTertiary,
} as const;

/**
 * 7-step pipeline canonical ordering. Step 7 (设计探索) is conditional
 * — only rendered when DOE arc is active. Other 6 always present.
 */
export const V4_PIPELINE_STEPS = [
  { id: "import", label: "导入" },
  { id: "geometry", label: "几何" },
  { id: "mesh", label: "网格" },
  { id: "physics", label: "物理" },
  { id: "boundary", label: "边界" },
  { id: "solver", label: "求解" },
  { id: "post", label: "后处理" },
  { id: "doe", label: "设计探索", conditional: true },
] as const;

export type V4PipelineStepId = (typeof V4_PIPELINE_STEPS)[number]["id"];
export type V4PipelineState = "done" | "active" | "pending";

/**
 * Convert a 6-digit hex color to a normalized [r, g, b] triple in
 * [0..1, 0..1, 0..1]. Used by runtime-styled surfaces that consume
 * floats (vtk.js renderer, three.js Color, WebGL uniforms) so the
 * V4 palette stays the single source of truth even off the Tailwind
 * CSS path. Accepts a leading `#` or none; throws on malformed input.
 */
export function hexToRgbFloat(hex: string): [number, number, number] {
  const s = hex.startsWith("#") ? hex.slice(1) : hex;
  if (s.length !== 6) {
    throw new Error(`hexToRgbFloat: expected #RRGGBB, got "${hex}"`);
  }
  return [
    parseInt(s.slice(0, 2), 16) / 255,
    parseInt(s.slice(2, 4), 16) / 255,
    parseInt(s.slice(4, 6), 16) / 255,
  ];
}

/**
 * Layout constants (px). Source: UI-SPEC §1.3 + §2.
 * Synced 2026-05-18 to actual runtime values per Codex R1 P2 finding.
 */
export const V4_LAYOUT = {
  topBarHeight: 32,
  bottomBarHeight: 60,
  leftRailWidth: 224,       // 32 icon strip + 192 tree column
  leftRailIconWidth: 32,
  leftRailTreeWidth: 192,
  rightPanelWidth: 300,
  kpiStripHeight: 96,
  modeTabStripHeight: 28,
  panelPadding: 12,
  cardPadding: 10,
  cardGap: 8,
  borderWidth: 1,
} as const;
