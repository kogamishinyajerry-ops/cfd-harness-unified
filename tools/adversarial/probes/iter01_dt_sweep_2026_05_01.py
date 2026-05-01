"""DEC-V61-106 follow-up — find a stable dt for iter01.

Smaller dt → lower CFL → should be more stable for icoFoam. Sweep
dt ∈ {0.5, 0.1, 0.01, 0.001} and report (cells, end_time_reached,
final_residual_p, NaN_count_in_final_U). Goal: find smallest dt that
runs in a smoke-window-friendly time AND produces a finite U field.
"""

from __future__ import annotations
import io, json, re, sys, time, urllib.error, urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8050"
ITER01_STL = Path("/Users/Zhuanz/Desktop/cfd-harness-unified/tools/adversarial/cases/iter01/geometry.stl")


def _post_multipart(url, file_path):
    boundary = "----dtsweep"
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode())
    body.write(b"Content-Type: application/octet-stream\r\n\r\n")
    body.write(file_path.read_bytes())
    body.write(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        url, data=body.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def _post_json(url, body, timeout=600):
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Content-Length": str(len(data))},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def count_nan_in_final_u(case_dir: Path) -> tuple[int, str]:
    """Return (nan_count, time_dir_name)."""
    candidates = []
    for d in case_dir.iterdir():
        if not d.is_dir(): continue
        try:
            t = float(d.name)
            if t > 0:
                candidates.append((t, d))
        except ValueError:
            pass
    if not candidates:
        return -1, ""
    candidates.sort(reverse=True)
    final_t, final_d = candidates[0]
    u = final_d / "U"
    if not u.is_file():
        return -1, final_d.name
    text = u.read_text()
    nan_count = len(re.findall(r"\bnan\b|\binf\b", text.lower()))
    return nan_count, final_d.name


def trial(dt: float, end_time: float, label: str):
    # Step 1: import
    st, resp = _post_multipart(f"{BASE}/api/import/stl", ITER01_STL)
    if st != 200:
        print(f"{label:<40s} import_failed status={st}")
        return
    case_id = resp["case_id"]

    # Step 2: mesh
    st, resp = _post_json(f"{BASE}/api/import/{case_id}/mesh", {"mesh_mode": "beginner"})
    if st != 200:
        print(f"{label:<40s} mesh_failed")
        return
    cells = resp["mesh_summary"]["cell_count"]
    polymesh = Path(resp["mesh_summary"]["polyMesh_path"])
    case_dir = polymesh.parent.parent

    # Step 3: BC setup
    qs = f"?from_stl_patches=1&inlet_speed=0.8&nu=0.0002&delta_t={dt}&end_time={end_time}"
    st, resp = _post_json(f"{BASE}/api/import/{case_id}/setup-bc{qs}", None)
    if st != 200:
        print(f"{label:<40s} bc_failed status={st}")
        return

    # Step 4: solve
    t0 = time.time()
    st, solve = _post_json(f"{BASE}/api/import/{case_id}/solve", None, timeout=900)
    dt_solve = time.time() - t0
    if st != 200:
        print(f"{label:<40s} solve_failed status={st}")
        return

    res_p = solve.get("last_initial_residual_p")
    res_U = solve.get("last_initial_residual_U", [])
    cont = solve.get("last_continuity_error")
    end_t = solve.get("end_time_reached")
    nsteps = solve.get("n_time_steps_written")

    nan_count, final_t_dir = count_nan_in_final_u(case_dir)

    print(
        f"{label:<40s} cells={cells:>5d} dt={dt:<6} end={end_time:<6} "
        f"wall={dt_solve:.0f}s end_t_reached={end_t} steps={nsteps} "
        f"final_dir={final_t_dir} NaN_in_final_U={nan_count} "
        f"cont={cont} res_p={res_p} res_U={res_U}"
    )


def main():
    # Test dt sweep at modest end_times to keep wall-time reasonable
    for dt, end_t in [
        (1.0,   10.0),    # baseline (current intent dt) — should NaN
        (0.1,   10.0),    # 10x finer
        (0.01,  2.0),     # very fine, short
        (0.001, 0.2),     # ultra fine, very short — ~200 steps
    ]:
        trial(dt, end_t, f"dt={dt} end={end_t}")


if __name__ == "__main__":
    main()
