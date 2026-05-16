/**
 * V71-UI-V3 · EmptyCanvasV3 · main canvas empty state when no case loaded
 * Per Image 01.
 */
export function EmptyCanvasV3() {
  return (
    <div
      data-testid="canvas-empty"
      className="h-full w-full flex flex-col items-center justify-center text-center px-8 text-v3-textTertiary"
    >
      <div className="text-[14px] text-v3-textSecondary mb-2">
        Select a case from the left panel to begin
      </div>
      <div className="text-[12px]">
        or press ⌘K to search · ⌘N to create new
      </div>
    </div>
  );
}
