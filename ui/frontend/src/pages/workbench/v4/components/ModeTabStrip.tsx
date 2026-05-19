/**
 * V4 · MainCanvas secondary tab strip · 28px · per UI-SPEC §2.3
 *
 * Sits at top of MainCanvas inside the canvas area. Blueprint shows this
 * in 5 of 8 modes (geometry · physics · mesh · post · doe). Defines a
 * thin sub-navigation tier (active = 2px underline in active orange).
 *
 * Right side optionally carries micro-controls (e.g. "时间格式 · 重力 g=9.8")
 * via `trailing` slot.
 */
import type { ReactNode } from "react";

export interface ModeTab {
  id: string;
  label: string;
}

interface ModeTabStripProps {
  tabs: ModeTab[];
  activeTabId?: string;
  onChange?: (id: string) => void;
  trailing?: ReactNode;
}

export function ModeTabStrip({
  tabs,
  activeTabId,
  onChange,
  trailing,
}: ModeTabStripProps) {
  const active = activeTabId ?? tabs[0]?.id;
  return (
    <div
      className="flex h-7 shrink-0 items-center justify-between border-b border-v4-border bg-v4-shell/80 px-3 text-[11px]"
      data-testid="modetab-strip"
    >
      <nav className="flex items-center gap-1">
        {tabs.map((t) => {
          const isActive = t.id === active;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onChange?.(t.id)}
              className={[
                "relative px-2 py-1 transition-colors",
                isActive
                  ? "text-v4-textPrimary"
                  : "text-v4-textSecondary hover:text-v4-textPrimary",
              ].join(" ")}
              data-testid={`modetab-${t.id}`}
              data-active={isActive ? "true" : "false"}
            >
              {t.label}
              {isActive && (
                <span
                  aria-hidden
                  className="absolute inset-x-1.5 bottom-[-1px] h-[2px] bg-v4-active"
                />
              )}
            </button>
          );
        })}
      </nav>
      {trailing && (
        <div className="flex items-center gap-3 text-v4-textTertiary">
          {trailing}
        </div>
      )}
    </div>
  );
}
