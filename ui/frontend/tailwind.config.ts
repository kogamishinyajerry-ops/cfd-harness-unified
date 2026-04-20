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
