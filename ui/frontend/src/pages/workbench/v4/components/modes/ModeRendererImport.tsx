/**
 * V4 · Mode renderer · 导入 (Import)
 *
 * Pre-run empty state · invites STEP / STL / IGES upload. Industrial-
 * minimalist drop-zone: dashed border · single CTA · zero decorative chrome.
 */
import { V4_PALETTE } from "@/theme/industrial_minimalist";

export function ModeRendererImport() {
  return (
    <div
      data-testid="v4-mode-import"
      className="flex h-full w-full items-center justify-center bg-v4-canvas"
    >
      <label
        className="group flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-v4-border bg-v4-shell px-12 py-16 transition-colors hover:border-v4-borderActive"
      >
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 4v12m0 0l-4-4m4 4l4-4M4 20h16"
            stroke={V4_PALETTE.textSecondary}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <div className="flex flex-col items-center gap-1">
          <span className="text-[13px] font-medium text-v4-textPrimary">
            拖入 STEP / STL / IGES
          </span>
          <span className="text-[11px] text-v4-textSecondary">
            或点击选择文件 · 支持 ≤ 500 MB · 中文路径已处理
          </span>
        </div>
        <span className="mt-2 rounded border border-v4-border bg-v4-surfaceRaised px-3 py-1 text-[10px] text-v4-textPrimary">
          选择文件
        </span>
        <input type="file" accept=".step,.stp,.stl,.iges,.igs" className="sr-only" />
      </label>
    </div>
  );
}
