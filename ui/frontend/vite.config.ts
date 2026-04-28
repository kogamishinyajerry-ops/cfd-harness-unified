/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Dev server on 127.0.0.1:${CFD_FRONTEND_PORT|5180}, proxying /api to
// FastAPI backend on 127.0.0.1:${CFD_BACKEND_PORT|8000}. Both bind to
// loopback — no network exposure during Phase 0 per DEC-V61-002.
//
// Port choice: 5180 (not the Vite default 5173). 5173 is a well-known
// default that collides with other React/Vite projects on a dev machine,
// which caused silent "opened the wrong app" incidents in the 2026-04-22
// convergence round. strictPort=true means any future collision will
// fail loudly instead of silently drifting. Override via
// `npm run dev -- --port NNNN` or `CFD_FRONTEND_PORT=NNNN ./scripts/start-ui-dev.sh`.
//
// Backend port is also env-driven (added 2026-04-27 anchor #2 dogfood):
// when 8000 is owned by another project on the dev box, set
// `CFD_BACKEND_PORT=8010` (or any free port) and the proxy follows.
const FRONTEND_PORT = Number(process.env.CFD_FRONTEND_PORT ?? "5180");
const BACKEND_PORT = process.env.CFD_BACKEND_PORT ?? "8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "127.0.0.1",
    port: FRONTEND_PORT,
    strictPort: true,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: false,
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: FRONTEND_PORT,
  },
  // Round-2 Q15: minimum vitest + RTL bring-up so wizard pages don't
  // silently break on next backend response shape change. Full RTL
  // coverage stays in deferred Tier-B(2).
  //
  // M-VIZ note (DEC-V61-094): vtk.js is a heavy module tree whose
  // Profiles/* side-effect imports crash vitest workers under jsdom
  // even when individual modules are vi.mock'd. Aliasing the whole
  // `@kitware/vtk.js/*` namespace to a tiny stub in test-only
  // resolution keeps the worker heap small. Production builds skip
  // this alias entirely.
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
    alias: [
      {
        find: /^@kitware\/vtk\.js\/.*$/,
        replacement: path.resolve(__dirname, "./src/test/vtk-stub.ts"),
      },
    ],
  },
});
