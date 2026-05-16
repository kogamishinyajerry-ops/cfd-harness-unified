/**
 * V68-A.1 · MSW browser worker entry. Started conditionally from main.tsx
 * when import.meta.env.VITE_MSW === "1" (dev / playwright runs), never in
 * production build.
 */
import { setupWorker } from "msw/browser";

import { handlers } from "./handlers";

export const worker = setupWorker(...handlers);
