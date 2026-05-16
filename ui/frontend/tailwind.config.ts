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
          textTertiary: "#4a4a52",
          accent: "#b78b65",      // SINGLE accent · sand-coral · <2% pixels
          // CFD-domain semantic (low-saturation only)
          inlet: "#5b8a73",       // dusty green
          wall: "#a66060",        // dusty red
          symmetry: "#a89060",    // dusty amber
          custom: "#6f7a96",      // dusty steel blue
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
