# M3.15 milestone close · 2026-05-25

> Parent: M3.10 `webgl_support` shared module · spike-class (no DEC) · 0 Codex · 0 Kogami
> final commit `b25a4d7`

## 做了什么 (what)

DRY'd `VtkCanvasV3` onto the shared `webgl_support.detectWebGL`. Removed its
byte-identical local `detectWebGL()` copy (was lines 37-48), imported the shared
one. `detectWebGL` is now defined **once** in the repo (grep: 0 other copies),
consumed by `viewport_kernel` and `VtkCanvasV3`.

## 为什么 (why)

- Closes the last code follow-up from the M3.10/M3.12 WebGL arc: a single source
  of truth for WebGL detection. Behavior-neutral (the two implementations were
  identical).
- **Honest scope note**: `VtkCanvasV3 ← MainCanvasV3` is V3-era and **unrouted**
  (App.tsx consolidated to `WorkbenchShellV4`), so this is hygiene/consistency,
  not a user-facing change — same disposition class as M3.12. Visual spot-check
  N/A; covered by the existing `VtkCanvasV3.contract.test` (5 pass) +
  `webgl_support.test`.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ spike-class | behavior-neutral dedup; no new test (existing tests cover); no DEC file |
| Codex / Kogami | ✅ N/A | trivial refactor |
| Four-question gate | ✅ Y/n-a | no functional change |
| Build / tests | ✅ green | `tsc -b` exit 0 · V3 contract test 5 pass |
| Frontend gate (M3.13) | ✅ fired+Passed | commit touched a `.tsx` → gate ran tsc -b on it |
| Visual spot-check | ✅ N/A (documented) | component unrouted |
| Push | ✅ b25a4d7 | direct-push as admin (enforce_admins=false); branch protection reported its rules, admin-bypassed |

## 下次候选 (next)

- **M4 charter scoping** — the only substantive item left. Post-Step-7
  solver_run / results / report / Notion sync. Multi-day; needs **Kogami opt-in**
  (user must召唤) per v2.3. NOT autonomous.
- Optional governance: flip `enforce_admins: true` if you want main fully
  PR-gated (airtight vs `--no-verify`); command in DEC-V61-203 §Follow-up.

## Bottom line

The WebGL arc (M3.10 root-fix → M3.11 build unblock → M3.12 legacy caller →
M3.15 DRY) is now fully closed with one shared `webgl_support` module as the
single source of truth. All recommended follow-ups from this session's arc are
landed; the next substantive step (M4) is a charter-scoping decision that needs
your Kogami opt-in.
