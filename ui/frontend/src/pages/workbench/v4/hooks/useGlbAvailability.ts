/**
 * Cheap probe for `<case>/geometry/render` and `<case>/mesh/render`
 * availability. The backend route /geometry/render only allows GET
 * (405 on HEAD), so we issue a Range-limited GET that the FastAPI
 * FileResponse honours — server reads at most the first 64 bytes off
 * disk. /mesh/render advertises HEAD; we still send the same GET so
 * one helper covers both surfaces.
 *
 * On success (2xx/206) we resolve `true`; on 4xx/5xx or network error
 * we resolve `false`. The query is React-Query-cached keyed by the
 * URL so a mode switch (geometry → mesh → boundary) over the same
 * case_id pays the probe cost once.
 *
 * Why not just attach the kernel and let it 404?
 *   • kernel mount = WebGL context + dynamic GLTFImporter chunk fetch,
 *     both of which leak ~150 KB into the page even on failure
 *   • the SVG fallback path is the "no geometry" empty state UX —
 *     we want to show it directly, not after a flash of "loading…"
 */
import { useQuery } from "@tanstack/react-query";

async function probeUrl(url: string, signal?: AbortSignal): Promise<boolean> {
  try {
    const resp = await fetch(url, {
      signal,
      headers: { Range: "bytes=0-63" },
    });
    return resp.ok || resp.status === 206;
  } catch {
    return false;
  }
}

/**
 * `enabled: false` is honoured when url is null/undefined (caseId
 * missing). Returned `available` is null while loading, then boolean.
 */
export function useGlbAvailability(url: string | null | undefined): {
  available: boolean | null;
  isLoading: boolean;
} {
  const q = useQuery<boolean>({
    queryKey: ["glb-availability", url ?? "__none__"],
    queryFn: ({ signal }) => probeUrl(url as string, signal),
    enabled: typeof url === "string" && url.length > 0,
    staleTime: 60_000,
    retry: false,
  });

  if (!url) return { available: false, isLoading: false };
  if (q.isLoading || q.data === undefined) {
    return { available: null, isLoading: true };
  }
  return { available: q.data, isLoading: false };
}

export function geometryGlbUrl(caseId: string | null | undefined): string | null {
  if (!caseId) return null;
  return `/api/cases/${encodeURIComponent(caseId)}/geometry/render`;
}

export function meshGlbUrl(caseId: string | null | undefined): string | null {
  if (!caseId) return null;
  return `/api/cases/${encodeURIComponent(caseId)}/mesh/render`;
}
