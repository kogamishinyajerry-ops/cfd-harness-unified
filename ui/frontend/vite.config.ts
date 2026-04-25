/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Dev server on 127.0.0.1:5180, proxying /api to the FastAPI backend on
// 127.0.0.1:8000. Both bind to loopback — no network exposure during
// Phase 0 per DEC-V61-002.
//
// Port choice: 5180 (not the Vite default 5173). 5173 is a well-known
// default that collides with other React/Vite projects on a dev machine,
// which caused silent "opened the wrong app" incidents in the 2026-04-22
// convergence round. strictPort=true means any future collision will
// fail loudly instead of silently drifting. Override via
// `npm run dev -- --port NNNN` or `CFD_FRONTEND_PORT=NNNN ./scripts/start-ui-dev.sh`.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5180,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 5180,
  },
  // Round-2 Q15: minimum vitest + RTL bring-up so wizard pages don't
  // silently break on next backend response shape change. Full RTL
  // coverage stays in deferred Tier-B(2).
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
