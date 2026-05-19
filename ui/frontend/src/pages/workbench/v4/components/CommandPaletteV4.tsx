/**
 * V4 · Command palette · ⌘K (mac) / Ctrl+K (win/linux).
 *
 * Pure navigation primitive — zero mutation surface. Two sections:
 *   1. Algorithm: case picker — filters `api.listCases()` by case_id +
 *      display name; Enter navigates to /workbench/v4/case/<id>.
 *   2. Pipeline jump — 7 steps from V4_PIPELINE_STEPS; Enter switches
 *      the active step without navigation (calls onStepChange).
 *
 * Keyboard contract:
 *   - ⌘K / Ctrl+K — toggle open/close (handled by parent's hook)
 *   - ↑ / ↓        — move selection
 *   - Enter        — activate selection
 *   - Esc          — close
 *   - Click backdrop — close
 *
 * 4Q gate:
 *   - LLM offline: pure-function filter, no fetch beyond api.listCases
 *   - Artifacts: every result row carries case_id / step_id for audit
 *   - TrustGate: navigation only, no state mutation
 *   - Advisory only: footer microcopy
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import {
  V4_PALETTE,
  V4_PIPELINE_STEPS,
  type V4PipelineStepId,
} from "@/theme/industrial_minimalist";
import type { CaseIndexEntry } from "@/types/validation";

interface CommandPaletteV4Props {
  open: boolean;
  onClose: () => void;
  onStepChange: (step: V4PipelineStepId) => void;
}

type Row =
  | { kind: "case"; case_id: string; label: string; sublabel?: string }
  | { kind: "step"; step_id: V4PipelineStepId; label: string };

export function CommandPaletteV4({
  open,
  onClose,
  onStepChange,
}: CommandPaletteV4Props) {
  const [query, setQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const navigate = useNavigate();

  const casesQ = useQuery<CaseIndexEntry[]>({
    queryKey: ["v4-cmdk-cases"],
    queryFn: () => api.listCases(),
    enabled: open,
    staleTime: 60_000,
    retry: 0,
  });

  // Build the row list. Cases first (filtered), then steps (always shown
  // when the query matches the step label or its zh name).
  const rows = useMemo<Row[]>(() => {
    const q = query.trim().toLowerCase();
    const caseRows: Row[] = (casesQ.data ?? [])
      .filter((c) => {
        if (!q) return true;
        return (
          c.case_id.toLowerCase().includes(q) ||
          (c.name ?? "").toLowerCase().includes(q)
        );
      })
      .slice(0, 8)
      .map((c) => ({
        kind: "case",
        case_id: c.case_id,
        label: c.name ?? c.case_id,
        sublabel: c.case_id,
      }));
    const stepRows: Row[] = V4_PIPELINE_STEPS.filter((s) => {
      if (!q) return true;
      return (
        s.id.toLowerCase().includes(q) ||
        s.label.toLowerCase().includes(q)
      );
    }).map((s) => ({ kind: "step", step_id: s.id, label: s.label }));
    return [...caseRows, ...stepRows];
  }, [casesQ.data, query]);

  // Reset selection when query changes.
  useEffect(() => {
    setSelectedIdx(0);
  }, [query, rows.length]);

  // Reset state on open.
  useEffect(() => {
    if (!open) return;
    setQuery("");
    setSelectedIdx(0);
    // Defer focus so the input is mounted.
    requestAnimationFrame(() => inputRef.current?.focus());
  }, [open]);

  // Keyboard handling inside the palette. ⌘K toggle lives in the parent
  // hook; we only handle navigation/selection here.
  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(rows.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      activate(rows[selectedIdx]);
    }
  }

  function activate(row: Row | undefined) {
    if (!row) return;
    if (row.kind === "case") {
      navigate(`/workbench/case/${encodeURIComponent(row.case_id)}`);
    } else {
      onStepChange(row.step_id);
    }
    onClose();
  }

  if (!open) return null;

  const caseCount = rows.filter((r) => r.kind === "case").length;
  const stepCount = rows.filter((r) => r.kind === "step").length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]"
      data-testid="v4-cmdk-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="命令栏"
    >
      {/* Backdrop */}
      <button
        type="button"
        aria-label="关闭命令栏"
        onClick={onClose}
        className="absolute inset-0 bg-v4-canvas/80 backdrop-blur-sm"
        data-testid="v4-cmdk-backdrop"
      />
      {/* Panel */}
      <div className="relative z-10 flex w-[520px] max-w-[90vw] flex-col overflow-hidden rounded-md border border-v4-border bg-v4-surface shadow-2xl">
        {/* Input */}
        <div className="flex items-center gap-2 border-b border-v4-border px-3 py-2.5">
          <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden>
            <circle
              cx="11"
              cy="11"
              r="7"
              fill="none"
              stroke={V4_PALETTE.textTertiary}
              strokeWidth="2"
            />
            <path
              d="M16.5 16.5L21 21"
              stroke={V4_PALETTE.textTertiary}
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="搜索算例 / 流水线步骤…"
            className="flex-1 bg-transparent text-[13px] text-v4-textPrimary placeholder-v4-textTertiary outline-none"
            data-testid="v4-cmdk-input"
            autoComplete="off"
            spellCheck={false}
          />
          <span className="font-mono text-[10px] text-v4-textTertiary">
            Esc
          </span>
        </div>

        {/* Results */}
        <div
          className="max-h-[60vh] overflow-y-auto"
          data-testid="v4-cmdk-results"
        >
          {casesQ.isLoading && rows.length === 0 && (
            <div className="px-3 py-3 text-[11px] text-v4-textTertiary">
              加载算例索引…
            </div>
          )}
          {!casesQ.isLoading && rows.length === 0 && (
            <div className="px-3 py-3 text-[11px] text-v4-textTertiary">
              无匹配 · 试试 "ldc" 或 "post"
            </div>
          )}
          {caseCount > 0 && (
            <div className="border-b border-v4-border px-3 py-1 text-[10px] uppercase tracking-wider text-v4-textTertiary">
              算例 · {caseCount}
            </div>
          )}
          {rows.map((row, i) => {
            const isSelected = i === selectedIdx;
            const isStepBoundary =
              row.kind === "step" &&
              i > 0 &&
              rows[i - 1]?.kind === "case";
            return (
              <div key={`${row.kind}-${i}`}>
                {isStepBoundary && (
                  <div className="border-y border-v4-border px-3 py-1 text-[10px] uppercase tracking-wider text-v4-textTertiary">
                    流水线步骤 · {stepCount}
                  </div>
                )}
                <button
                  type="button"
                  onMouseEnter={() => setSelectedIdx(i)}
                  onClick={() => activate(row)}
                  className={[
                    "flex w-full items-center gap-3 px-3 py-2 text-left text-[12px] transition-colors",
                    isSelected
                      ? "bg-v4-surfaceRaised text-v4-textPrimary"
                      : "text-v4-textSecondary hover:bg-v4-surfaceRaised",
                  ].join(" ")}
                  data-testid={`v4-cmdk-row-${row.kind}-${i}`}
                  data-selected={isSelected ? "true" : "false"}
                >
                  <span
                    aria-hidden
                    className="font-mono text-[10px]"
                    style={{
                      color:
                        row.kind === "case"
                          ? V4_PALETTE.brand
                          : V4_PALETTE.active,
                    }}
                  >
                    {row.kind === "case" ? "▦" : "↳"}
                  </span>
                  <span className="flex-1 truncate text-v4-textPrimary">
                    {row.label}
                  </span>
                  {row.kind === "case" && row.sublabel && (
                    <span className="truncate font-mono text-[10px] text-v4-textTertiary">
                      {row.sublabel}
                    </span>
                  )}
                  {row.kind === "step" && (
                    <span className="font-mono text-[10px] text-v4-textTertiary">
                      {row.step_id}
                    </span>
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-v4-border bg-v4-shell px-3 py-1.5 text-[10px] text-v4-textTertiary">
          <span>
            <span className="font-mono">↑↓</span> 选择 ·{" "}
            <span className="font-mono">Enter</span> 跳转
          </span>
          <span>advisory only · 仅导航</span>
        </div>
      </div>
    </div>
  );
}

/** Global keyboard hook · Cmd+K (mac) or Ctrl+K (others) toggles open. */
export function useCmdK(toggle: () => void): void {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const isCmd = e.metaKey || e.ctrlKey;
      if (isCmd && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        toggle();
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggle]);
}
