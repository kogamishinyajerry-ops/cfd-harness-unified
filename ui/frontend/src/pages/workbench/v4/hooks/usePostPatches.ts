/**
 * DEC-V61-205 (M5 C2) · resolve the real boundary patch for the Post
 * surface overlay.
 *
 * Bug #2 fix: ModeRendererPost used to hardcode `?patch=engine` (an
 * APU-bay-only patch name), so the surface overlay 404'd on every other
 * case (LDC → fixedWalls/lid, backward_step → its own wall). This hook
 * asks the backend which patches actually exist for the solved case
 * (`GET /post/patches`) and picks the best one to color by |U|.
 *
 * The fetch degrades silently: any failure (409 no run / 503 container /
 * network) resolves to an empty patch list, so the caller renders no
 * surface overlay rather than crashing — the streamline overlay and the
 * residual/report panels still carry the run's truth. Mirrors the
 * fail-soft contract of useGlbAvailability.
 */
import { useQuery } from "@tanstack/react-query";

export interface PostPatch {
  name: string;
  bytes: number;
}

export interface PostPatchesData {
  patches: PostPatch[];
  latestTime: string | null;
}

/** Names that denote a solid wall / body of interest — the surface we
 *  most want to color by |U|. */
const WALL_LIKE =
  /(wall|fixedwall|engine|body|surface|cavity|step|plate|airfoil|foil|hull|cylinder|sphere|building|obstacle)/i;
/** Names that denote a flow boundary (inlet/outlet/etc.) — a poor default
 *  surface because it shows the through-flow plane, not the body. */
const FLOW_BOUNDARY =
  /(inlet|outlet|inflow|outflow|farfield|freestream|atmosphere|symmetry|frontandback|frontback|empty|defaultfaces)/i;

/**
 * Choose which patch to render as the Post surface overlay. Tiered:
 * wall-like names first, flow boundaries last, everything else in the
 * middle; within a tier the larger patch (more surface bytes) wins. Pure
 * + exported for unit testing.
 */
export function pickSurfacePatch(patches: PostPatch[]): string | null {
  if (patches.length === 0) return null;
  const tier = (name: string): number => {
    if (WALL_LIKE.test(name)) return 0;
    if (FLOW_BOUNDARY.test(name)) return 2;
    return 1;
  };
  return [...patches].sort((a, b) => {
    const t = tier(a.name) - tier(b.name);
    return t !== 0 ? t : b.bytes - a.bytes;
  })[0].name;
}

async function fetchPatches(
  caseId: string,
  signal?: AbortSignal,
): Promise<PostPatchesData> {
  try {
    const resp = await fetch(
      `/api/cases/${encodeURIComponent(caseId)}/post/patches`,
      { signal, headers: { Accept: "application/json" } },
    );
    if (!resp.ok) return { patches: [], latestTime: null };
    const body = (await resp.json()) as {
      patches?: PostPatch[];
      latest_time?: string | null;
    };
    return {
      patches: Array.isArray(body.patches) ? body.patches : [],
      latestTime: body.latest_time ?? null,
    };
  } catch {
    return { patches: [], latestTime: null };
  }
}

export function usePostPatches(caseId: string | null | undefined): {
  patches: PostPatch[];
  selectedPatch: string | null;
  isLoading: boolean;
} {
  const q = useQuery<PostPatchesData>({
    queryKey: ["v4-post-patches", caseId ?? "__none__"],
    queryFn: ({ signal }) => fetchPatches(caseId as string, signal),
    enabled: typeof caseId === "string" && caseId.length > 0,
    staleTime: 30_000,
    retry: false,
    refetchOnWindowFocus: false,
  });
  const patches = q.data?.patches ?? [];
  return {
    patches,
    selectedPatch: pickSurfacePatch(patches),
    isLoading: q.isLoading,
  };
}
