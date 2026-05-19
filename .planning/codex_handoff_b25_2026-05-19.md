# B2.5 Handoff to Codex APP · 2026-05-19

> **Why this exists**: Opus 4.7 (Claude Code session) drove B2.5 (real vtk.js Post viewport)
> from backend exporters through frontend kernel + ViewportV4 wiring, but hit a visual-debugging
> wall: VTP loads 200 OK, but the U-magnitude coloring + streamlines don't render. Handing off
> to Codex APP because Codex has stronger screenshot/image capabilities for diagnosing live
> WebGL/vtk.js state.

---

## 0 · Context for someone walking in cold

**The project**: cfd-harness-unified — an AI-advisor-driven CFD workbench. UI runs at
`http://localhost:5181` (vite proxy → backend at `:8000`). V4 is the current
industrial-minimalist UI shell (parallel to V3, but real data only — no SVG cartoons).

**The session arc**:
1. User asked to dogfood the workbench with a real engine CAD (KJ66 micro-turbojet).
2. Pipeline succeeded: STEP → STL → workbench import → simpleFoam 500 iter, residual Ux=7e-7.
3. User opened browser, saw 4 mode renderers (Post/Solver/DoE/Physics) showing **SVG cartoon
   placeholders** instead of real viewports. **"全都是 SVG，和蓝图严重不符"**.
4. Codex R3-R8 reviews never caught this — they audited test coverage and API contracts but
   never opened a browser to check "is Post mode actually rendering case geometry?".
5. Remediation arc (this session):
   - **A0**: Seal DoE rail (LeftRail comment-out + BottomBar `conditional: true` filter)
   - **A2**: Physics mode → real ViewportV4 (glb)
   - **B1**: Solver mode → real ViewportV4 + real residual chart
   - **B2.5**: Post mode → **hybrid VTP path**: real glb viewport + vtk.js-attached surface.vtp
     (U-magnitude colored) + vtk.js-attached streamlines.vtp (Python/OpenFOAM seeded)

**Where it broke**: B2.5 backend + frontend are wired. Backend serves valid VTP. Frontend
loads VTP (200 OK in logs). But on screen, the engine surface stays white, the velocity
legend reads `0 → 0.00 m/s`, and streamlines are invisible. The base GLB renders fine.

---

## 1 · Working environment

| Thing | Value |
|---|---|
| Repo root | `/Users/Zhuanz/Desktop/cfd-harness-unified` |
| Frontend dev | `cd ui/frontend && npm run dev` → `http://localhost:5181` |
| Backend dev | `cd ui/backend && uv run uvicorn main:app --reload --port 8000` |
| OpenFOAM container | `cfd-openfoam` (docker, image `opencfd/openfoam-default:2312`), case dir bind-mounted |
| KJ66 test case | `ui/backend/user_drafts/imported/imported_2026-05-19T01-15-19Z_69bed2d0/` |
| Standalone KJ66 dir | `/Users/Zhuanz/Desktop/kj66-engine-dogfood/` (source of truth for the case) |
| Browser test URL | `http://localhost:5181/?step=post&case=imported_2026-05-19T01-15-19Z_69bed2d0` |

The KJ66 case has run simpleFoam to 500 iterations; converged fields are at `500/`. VTP
artifacts already generated under `VTK/case_500/` and `postProcessing/sets/streamlines/500/`
on disk — backend serves directly from there, no recompute needed for verification.

---

## 2 · Backend (DONE · works)

Endpoints (mounted in `ui/backend/routes/case_visualize.py`):

| Method | Path | Returns | Status |
|---|---|---|---|
| GET | `/api/cases/{case_id}/post/surface.vtp?patch=engine` | VTP XML (boundary file from foamToVTK, U field on points) | **OK, 200** for KJ66 case |
| GET | `/api/cases/{case_id}/post/streamlines.vtp` | VTP XML (track0.vtp from streamLine functionObject) | **OK, 200** for KJ66 case |

Both verified in `/tmp/backend_b25.log` during this session.

Content-Type: `application/vnd.kitware.vtk-polydata+xml`.

Implementation files:
- `ui/backend/services/case_visualize/vtk_export.py` — `ensure_vtk_output(case_dir, force=False)` wraps foamToVTK in container, caches, invalidates on solver re-run.
- `ui/backend/services/case_visualize/streamline_export.py` — writes `system/streamlinesDict` with cloud seedSampleSet (8-point line at x=-2.95, just upstream of engine inlet), runs `postProcess -func streamlines -latestTime` in container.
- `ui/backend/routes/case_visualize.py` — FastAPI handlers; 409 if no converged run, 404 if patch unknown, 503 if container down.

For KJ66, both files exist on disk so endpoints just stream them — no Docker round-trip
needed during the visual-debug loop.

---

## 3 · Frontend (DONE wiring, BROKEN rendering)

### 3.1 Kernel: `ui/frontend/src/visualization/viewport_kernel.ts`

Added a `attachVtp(url, kind, explicitRange?)` API on the kernel. Returns
`VtpAttachHandle { id, url, kind, scalarRange }`. Cleanup via `detachVtp(handle)`.

**Critical detail — manual magU computation**:
vtk.js mapper has **no built-in magnitude coloring mode** for vector arrays. For
`U` (3-component), we synthesize a `magU` scalar Float32Array on the client and add it
to `polyData.getPointData()` via `vtkDataArray.newInstance(...) + pointData.addArray(...) +
pointData.setActiveScalars("magU")`. Then mapper:
```ts
mapper.setColorModeToMapScalars();
mapper.setScalarModeToUsePointFieldData();
mapper.setScalarVisibility(true);
mapper.setColorByArrayName("magU");
// LUT: 7-stop blue→cyan→green→yellow→red, mapped to scalarRange
```

The async dance (Promise.all of dynamic imports for `XMLPolyDataReader` + `DataArray`)
is in place because `require()` doesn't exist in Vite ESM.

**Where it might be lying**: `reader.setUrl(url)` returns a promise — but vtk.js's
internal "is the binary AppendedData section actually parsed" state isn't 100% guaranteed
to be synchronous after that promise resolves. We `await reader.update()` after, but
I'm not 100% sure that's enough. **This is hypothesis #1 for the bug.**

### 3.2 ViewportV4: `ui/frontend/src/pages/workbench/v4/components/ViewportV4.tsx`

New props:
- `surfaceVtpUrl?: string | null`
- `streamlinesVtpUrl?: string | null`
- `onVtpRangeReady?: (range: [number, number]) => void`

Two useEffects, one per URL, each attaches via kernel and cleans up on URL change /
unmount. `onVtpRangeReady` fires when surface attaches successfully.

### 3.3 Post mode: `ui/frontend/src/pages/workbench/v4/components/modes/ModeRendererPost.tsx`

Wires both URLs:
```tsx
const surfaceVtpUrl = caseId
  ? `/api/cases/${encodeURIComponent(caseId)}/post/surface.vtp?patch=engine`
  : null;
const streamlinesVtpUrl = caseId
  ? `/api/cases/${encodeURIComponent(caseId)}/post/streamlines.vtp`
  : null;
const [vtpScalarRange, setVtpScalarRange] = useState<[number, number] | null>(null);

// passes both URLs + setVtpScalarRange to ViewportV4
// VelocityLegendStrip uses vtpScalarRange[1] as uMax (falls back to detail.key_quantities.u_max)
```

### 3.4 Solver mode: `ModeRendererSolver.tsx`

Wires `surfaceVtpUrl` only — no streamlines mid-run since field is live and streamlines
would be stale. Comment in code explains. **Solver mode is not in scope for the visual-bug
debugging task** — focus is Post mode.

---

## 4 · The bug (what you actually need to fix)

### 4.1 Symptoms

Browse to `http://localhost:5181/?step=post&case=imported_2026-05-19T01-15-19Z_69bed2d0`:

1. **GLB renders correctly** — KJ66 hull visible, can orbit/zoom.
2. **Engine surface is plain white** — should be U-magnitude colored (blue at stagnation,
   red at peak ~40 m/s downstream).
3. **Velocity legend reads `0 → 0.00 m/s`** — meaning `vtpScalarRange` resolved to `[0, 0]`,
   the synthesized magU array is empty or not being read.
4. **Streamlines invisible** — track0.vtp loads (200 OK in network tab) but no lines visible.
5. **No console errors** about VTP failure — attach() promise resolves, `onVtpRangeReady`
   fires (with [0,0]).

### 4.2 Reproduction

```bash
# Terminal 1
cd /Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend
uv run uvicorn main:app --reload --port 8000

# Terminal 2
cd /Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend
npm run dev
```

Open `http://localhost:5181/?step=post&case=imported_2026-05-19T01-15-19Z_69bed2d0`.

Verify backend serves VTPs:
```bash
curl -I "http://localhost:8000/api/cases/imported_2026-05-19T01-15-19Z_69bed2d0/post/surface.vtp?patch=engine"
# expect: HTTP/1.1 200 OK, Content-Type: application/vnd.kitware.vtk-polydata+xml

curl -I "http://localhost:8000/api/cases/imported_2026-05-19T01-15-19Z_69bed2d0/post/streamlines.vtp"
# expect: HTTP/1.1 200 OK
```

Both VTPs on disk:
```bash
ls -la ui/backend/user_drafts/imported/imported_2026-05-19T01-15-19Z_69bed2d0/VTK/case_500/boundary/
# expect: engine.vtp (~336KB)

ls -la ui/backend/user_drafts/imported/imported_2026-05-19T01-15-19Z_69bed2d0/postProcessing/sets/streamlines/500/
# expect: track0.vtp (~80KB)
```

### 4.3 Hypothesis ranking

**H1 (most likely)**: vtk.js `XMLPolyDataReader` async parse — `await reader.setUrl(url)`
resolves before the binary `<AppendedData>` section is fully parsed. We then call
`reader.getOutputData().getPointData().getArrayByName("U").getData()` and get an empty
or zero-filled TypedArray.

How to test: in `attachVtp()` log `polyData.getNumberOfPoints()` and
`uArr.getNumberOfTuples()` and `raw.length` immediately after the await. If those are 0 or
suspiciously small, this is the issue. Fix: try `await reader.update()` after `setUrl`,
or use `parseAsArrayBuffer()` path manually.

**H2**: The `magU` array IS computed correctly, but the mapper is still pulling from `U`
(the vector field) and silently defaulting to component-0 with `scalarRange=[0,0]` because
of some scalar-mode setting still pointing at the original `U` field.

How to test: after `setActiveScalars("magU")`, log
`polyData.getPointData().getScalars().getName()` — should print `"magU"`. If it prints `"U"`,
the activation didn't stick.

**H3**: Z-fight between GLB actor and VTP surface actor (both KJ66 hull at same Z), GLB
renders on top, VTP is hidden behind. Fix: offset VTP actor by 0.5mm normal, or set GLB
actor opacity to 0 in Post mode, or disable depth-test on VTP actor.

How to test: temporarily comment out the glb load in Post mode and see if VTP coloring
shows up.

**H4**: `addArray` doesn't trigger a pipeline update — need `polyData.modified()` or
`mapper.modified()` before `actor.render()`.

How to test: add explicit `polyData.modified()` and `mapper.modified()` calls before
returning from `attachVtp()`.

### 4.4 What's already known good

- The VTP files are valid VTK XML — `head -100 .../engine.vtp` shows correct `<Piece>`,
  `<Points>`, `<PointData>` with `U` array as `Float32` `NumberOfComponents="3"`.
- The fetch succeeds, response body arrives at the browser (verifiable via DevTools network).
- `attachVtp()` does not throw — `onVtpRangeReady` fires (with the bad [0,0] range).
- GLB rendering works in Post mode (so the kernel + WebGL context + camera are fine).
- The Solver mode (which wires only the surface VTP) shows the same white-hull symptom,
  so the bug is in shared kernel code, not in Post-mode wiring.

---

## 5 · What success looks like

When fixed, the Post mode at `?step=post&case=imported_2026-05-19T01-15-19Z_69bed2d0`
should show:

1. KJ66 engine hull, **U-magnitude colored** (blue/cyan around the inlet, ramping to
   yellow/red along the bypass duct and nozzle exit).
2. **VelocityLegendStrip** at top showing `0 → 40 m/s` (or whatever the real range is —
   not `0 → 0.00 m/s`).
3. **Streamlines visible** — ~8 colored polylines flowing from inlet through the bypass.
4. **No console errors**.
5. Can orbit the camera with mouse; all 3 actors (GLB, surface, streamlines) rotate together.

---

## 6 · Files in scope for the fix

Most likely to need surgery:
- `ui/frontend/src/visualization/viewport_kernel.ts` — the `attachVtp()` function

Less likely, but check:
- `ui/frontend/src/pages/workbench/v4/components/ViewportV4.tsx` — the two useEffects that call attachVtp
- `ui/frontend/src/pages/workbench/v4/components/modes/ModeRendererPost.tsx` — props wiring

Do NOT touch:
- `ui/backend/**` — backend works
- The KJ66 case files — already converged

---

## 7 · After the fix

1. Take a screenshot of the fixed Post mode showing colored hull + streamlines.
2. Add a test under `ui/frontend/src/__tests__/v4/` that verifies `attachVtp` resolves with
   a non-degenerate `scalarRange` for the KJ66 engine.vtp (can use a small fixture).
3. Update `.planning/v4_real_viewport_audit_2026-05-19.md` with the fix summary.
4. Optional but recommended: run codex-relay review on the diff:
   `codex-review-relay --base origin/main`
5. Commit with message:
   ```
   fix(b2.5): vtk.js VTP rendering — U-magnitude coloring + streamlines now visible

   <root cause one-liner>

   confidence: <h/m/l>
   ```

---

## 8 · One more thing — the SVG-fakes lesson

The CLAUDE.md rule violated this session was:
> "For UI or frontend changes, start the dev server and use the feature in a browser before
> reporting the task as complete."

R3-R8 Codex reviews didn't catch the SVG-fake regression because Codex reviews diffs +
contracts, not pixels. **The fix for B2.5 needs a browser-visible verification step**, not
just a unit test green. That's why Codex APP (with screenshot tools) is the right
handoff target.
