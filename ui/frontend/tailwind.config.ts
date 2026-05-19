import type { Config } from "tailwindcss";

// Design tokens pulled from docs/ui_design.md (v0.1).
// - Dark-first surface palette (-950 → -100)
// - Three-state contract colors: pass #4ade80, hazard #fbbf24, fail #f87171
// - 8px base grid (Tailwind default spacing already aligns)
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          950: "#0a0e14",
          900: "#0f1620",
          800: "#141c28",
          700: "#1c2736",
          600: "#263345",
          500: "#3a495f",
          400: "#5a6c82",
          300: "#7f8fa4",
          200: "#a9b4c2",
          100: "#d5dbe2",
        },
        contract: {
          pass: "#4ade80",
          hazard: "#fbbf24",
          fail: "#f87171",
          unknown: "#7f8fa4",
        },
        // V71-UI-V3 · Claude-tier industrial workbench design tokens
        // per .planning/blueprints/v3/INDEX.md visual contract
        // Sand-coral single accent + dusty CFD semantic palette
        v3: {
          bg: "#0e0e10",          // background
          surface1: "#16161a",    // surface elev1 (panels)
          surface2: "#1c1c20",    // surface elev2 (hover / focus only)
          border: "#232328",      // subtle border (1px hairlines)
          borderActive: "#2e2e34", // active element border
          textPrimary: "#e8e8eb",
          textSecondary: "#82828a",
          textTertiary: "#9a9aa0", // V73.2 · raised from #4a4a52 to clear WCAG 2.1 AA 4.5:1 on #0e0e10 (~7.3:1)
          accent: "#b78b65",      // SINGLE accent · sand-coral · <2% pixels
          // CFD-domain semantic (low-saturation only)
          inlet: "#5b8a73",       // dusty green
          wall: "#a66060",        // dusty red
          symmetry: "#a89060",    // dusty amber
          custom: "#6f7a96",      // dusty steel blue
        },
        // V92-UI-V4 · Industrial-minimalist workbench design tokens
        // per .planning/transitions/2026-05-18_blueprint_read.md §1.1
        // STAR-CCM+ / Fluent / Bloomberg parity · dual-accent (healthy + active)
        // Replaces V3 single-sand-coral; accent total <5% pixels, grayscale dominates.
        v4: {
          // background ladder (charcoal with cool tint)
          canvas: "#0B1116",        // 3D viewport background
          shell: "#0E141A",         // page background outside panels
          surface: "#161C24",       // panel base (left rail · right rail)
          surfaceRaised: "#1C232C", // KPI chips · status cards · BottomBar
          // borders
          border: "#222932",        // 1px subtle dividers
          borderActive: "#2E3744",  // selected / focused borders
          // text ladder (WCAG AA on canvas: 14.3:1 / 6.1:1 / 3.6:1)
          textPrimary: "#E8ECF1",
          textSecondary: "#8B95A3",
          textTertiary: "#5A6471",
          // accents (signal only · <5% pixels combined)
          healthy: "#3DC97F",       // ✓ check · "通过" · active-step done · healthy KPI delta
          active: "#F0A93B",        // current pipeline step glow · selection ring
          warn: "#E8A24B",          // ⚠ caution · drift warning
          crit: "#E5564E",          // error · failure verdict (sparingly used)
          brand: "#5BB4FF",         // links · AI assistant icon · hover
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
        math: ["STIX Two Math", "Latin Modern Math", "serif"],
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(0 0 0 / 0.40), 0 1px 6px -1px rgb(0 0 0 / 0.30)",
      },
    },
  },
  plugins: [],
} satisfies Config;
