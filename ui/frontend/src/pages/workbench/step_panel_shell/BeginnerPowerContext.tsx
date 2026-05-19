// BeginnerPowerContext · V67-C.3 (Engineer Control Rail)
//
// Surfaces a single Beginner ⇄ Power mode toggle that step bodies subscribe to
// for "advanced disclosure" patterns (Beginner = preset-driven defaults · Power
// = engineer-driven control surface exposed). Persisted to localStorage so the
// engineer's preference survives reloads.
//
// Per Blueprint v3 §3: every panel must have a "Power toggle" — this context
// is the SSOT for that state. Step bodies read via `useBeginnerPower()` hook
// and gate their advanced sections behind `mode === "power"`.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type BeginnerPowerMode = "beginner" | "power";

const STORAGE_KEY = "v67c_beginner_power_mode";
const DEFAULT_MODE: BeginnerPowerMode = "beginner";

interface BeginnerPowerContextValue {
  mode: BeginnerPowerMode;
  setMode: (m: BeginnerPowerMode) => void;
  toggle: () => void;
  isBeginner: boolean;
  isPower: boolean;
}

const BeginnerPowerContext = createContext<BeginnerPowerContextValue | null>(
  null,
);

function readInitialMode(): BeginnerPowerMode {
  if (typeof window === "undefined") return DEFAULT_MODE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === "beginner" || raw === "power") return raw;
  } catch {
    // localStorage may be blocked (private mode / SSR · ignore)
  }
  return DEFAULT_MODE;
}

export function BeginnerPowerProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<BeginnerPowerMode>(readInitialMode);

  const setMode = useCallback((m: BeginnerPowerMode) => {
    setModeState(m);
    try {
      window.localStorage.setItem(STORAGE_KEY, m);
    } catch {
      // ignore
    }
  }, []);

  const toggle = useCallback(() => {
    setMode(mode === "beginner" ? "power" : "beginner");
  }, [mode, setMode]);

  useEffect(() => {
    // Cross-tab sync · listen to storage events from other windows/tabs.
    function handleStorage(e: StorageEvent) {
      if (e.key !== STORAGE_KEY) return;
      const v = e.newValue;
      if (v === "beginner" || v === "power") setModeState(v);
    }
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const value = useMemo<BeginnerPowerContextValue>(
    () => ({
      mode,
      setMode,
      toggle,
      isBeginner: mode === "beginner",
      isPower: mode === "power",
    }),
    [mode, setMode, toggle],
  );

  return (
    <BeginnerPowerContext.Provider value={value}>
      {children}
    </BeginnerPowerContext.Provider>
  );
}

/**
 * Read-write hook · requires BeginnerPowerProvider in tree.
 * Throws if used outside provider (catches forgot-to-wrap bugs).
 */
export function useBeginnerPower(): BeginnerPowerContextValue {
  const v = useContext(BeginnerPowerContext);
  if (!v) {
    throw new Error(
      "useBeginnerPower must be used within a <BeginnerPowerProvider>",
    );
  }
  return v;
}

/**
 * Read-only hook · returns null when no provider in tree.
 * Useful for components that should render both inside and outside
 * the workbench shell (e.g. shared in tests).
 */
export function useBeginnerPowerOptional(): BeginnerPowerContextValue | null {
  return useContext(BeginnerPowerContext);
}
