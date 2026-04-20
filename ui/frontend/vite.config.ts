import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Phase 0: dev server on 127.0.0.1:5173, proxying /api to the FastAPI
// backend on 127.0.0.1:8000. Both bind to loopback — no network
// exposure during Phase 0 per DEC-V61-002.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
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
    port: 5173,
  },
});
