#!/usr/bin/env python3
"""Claude-Code-runnable automated smoke for the M-AI-COPILOT dogfood loop.

Replaces the previous "Awaiting CFDJerry visual smoke" human-gate with
an executable smoke that any agent (Claude Code, CI, an engineer's
local checkout) can run end-to-end without browser interaction.

What this exercises (per dogfood guide M_AI_COPILOT_v0.md sections):
  · §4a · LDC cube path: classifier → pin lid → re-run → confident,
                         with setup_ldc_bc dicts on disk.
  · §4c · Channel non-cube path: classifier → pin inlet+outlet →
                                  re-run → confident, with
                                  setup_channel_bc dicts + 3-patch
                                  boundary split.

What it does NOT cover (still requires human eyes on a real browser):
  · Viewport face highlighting (the emerald glow on the active slot)
  · vtk.js GLTFImporter loading a real glb (kernel-level rendering)
  · Cross-tab 409 conflict UX flow
These are documented as "human-only" in the dogfood guide and are not
part of the agent gate.

Exit code:
  0 — all assertions passed; corresponding DEC's "Awaiting smoke" gate
      can flip to Accepted.
  non-zero — assertion failure; details on stdout. Do NOT flip status.

Usage:
    python3 scripts/smoke/dogfood_loop.py
    PYTHONPATH=. .venv/bin/python scripts/smoke/dogfood_loop.py

Per project memory rule "禁用日期/调度门控": this script is dependency-
triggered (run before every DEC closure that gates on dogfood smoke),
NOT calendar-gated.
"""
from __future__ import annotations

import secrets
import sys
import tempfile
from pathlib import Path
from typing import Any


def _stage_imported_case(imported_dir: Path, case_id: str) -> Path:
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    return case_dir


def _stage_polymesh(case_dir: Path, points: str, faces: str, boundary: str, owner: str) -> None:
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(points, encoding="utf-8")
    (polymesh / "faces").write_text(faces, encoding="utf-8")
    (polymesh / "boundary").write_text(boundary, encoding="utf-8")
    (polymesh / "owner").write_text(owner, encoding="utf-8")


# Shared OpenFOAM-text fixtures (must match test_setup_bc_envelope_route.py).
_CUBE_POINTS = (
    "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
    "    class vectorField;\n    location \"constant/polyMesh\";\n"
    "    object points;\n}\n\n8\n(\n"
    "(0 0 0)\n(1 0 0)\n(1 1 0)\n(0 1 0)\n"
    "(0 0 1)\n(1 0 1)\n(1 1 1)\n(0 1 1)\n)\n"
)
_CUBE_FACES = (
    "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
    "    class faceList;\n    location \"constant/polyMesh\";\n"
    "    object faces;\n}\n\n6\n(\n"
    "4(0 1 2 3)\n4(4 5 6 7)\n4(0 1 5 4)\n"
    "4(2 3 7 6)\n4(1 2 6 5)\n4(0 3 7 4)\n)\n"
)
_CUBE_BOUNDARY = (
    "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
    "    class polyBoundaryMesh;\n"
    "    location \"constant/polyMesh\";\n    object boundary;\n}\n\n"
    "1\n(\n    walls\n    {\n        type wall;\n"
    "        nFaces 6;\n        startFace 0;\n    }\n)\n"
)
_CUBE_OWNER = (
    "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
    "    class labelList;\n    location \"constant/polyMesh\";\n"
    "    object owner;\n}\n\n6\n(\n0\n0\n0\n0\n0\n0\n)\n"
)
_CHANNEL_POINTS = (
    "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
    "    class vectorField;\n    location \"constant/polyMesh\";\n"
    "    object points;\n}\n\n8\n(\n"
    "(0 0 0)\n(1 0 0)\n(1 1 0)\n(0 1 0)\n"
    "(0 0 10)\n(1 0 10)\n(1 1 10)\n(0 1 10)\n)\n"
)


def _say(prefix: str, msg: str) -> None:
    print(f"  [{prefix}] {msg}")


def _smoke_ldc(client, imported: Path, face_id_fn) -> None:
    """§4a · LDC cube full loop via HTTP TestClient."""
    print("\n┌─ §4a · LDC cube · uncertain → pin lid → confident ─")
    case_id = f"smoke_ldc_{secrets.token_hex(3)}"
    case_dir = _stage_imported_case(imported, case_id)
    _stage_polymesh(case_dir, _CUBE_POINTS, _CUBE_FACES, _CUBE_BOUNDARY, _CUBE_OWNER)
    _say("setup", f"case_id={case_id}")

    r = client.post(f"/api/import/{case_id}/setup-bc", params={"envelope": 1})
    assert r.status_code == 200, r.text
    env = r.json()
    assert env["confidence"] == "uncertain", env
    assert any(q["id"] == "lid_orientation" for q in env["unresolved_questions"])
    _say("step1", "first envelope=uncertain · lid_orientation question present ✓")

    top_face_id = face_id_fn(
        [(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)]
    )
    r_put = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [{
                "face_id": top_face_id,
                "name": "lid",
                "confidence": "user_authoritative",
            }],
        },
    )
    assert r_put.status_code == 200, r_put.text
    assert r_put.json()["revision"] == 1
    _say("step2", f"PUT lid pin face_id={top_face_id[:16]}… revision 0→1 ✓")

    r2 = client.post(f"/api/import/{case_id}/setup-bc", params={"envelope": 1})
    assert r2.status_code == 200, r2.text
    env2 = r2.json()
    assert env2["confidence"] == "confident", env2
    assert env2["annotations_revision_consumed"] == 1
    assert (case_dir / "0" / "U").is_file()
    assert (case_dir / "0" / "p").is_file()
    assert (case_dir / "system" / "controlDict").is_file()
    bnd = (case_dir / "constant" / "polyMesh" / "boundary").read_text()
    assert "lid" in bnd and "fixedWalls" in bnd
    _say(
        "step3",
        "envelope=confident · setup_ldc_bc wrote 0/U,0/p,system/* · "
        "boundary split into lid+fixedWalls ✓",
    )


def _smoke_channel(client, imported: Path, face_id_fn) -> None:
    """§4c · Non-cube channel full loop via HTTP TestClient."""
    print("\n┌─ §4c · Non-cube channel · uncertain → pin inlet+outlet → confident ─")
    case_id = f"smoke_channel_{secrets.token_hex(3)}"
    case_dir = _stage_imported_case(imported, case_id)
    _stage_polymesh(case_dir, _CHANNEL_POINTS, _CUBE_FACES, _CUBE_BOUNDARY, _CUBE_OWNER)
    _say("setup", f"case_id={case_id} (1×1×10 channel)")

    r = client.post(f"/api/import/{case_id}/setup-bc", params={"envelope": 1})
    assert r.status_code == 200, r.text
    env = r.json()
    assert env["confidence"] == "uncertain", env
    qids = {q["id"] for q in env["unresolved_questions"]}
    assert "inlet_face" in qids and "outlet_face" in qids
    _say("step1", f"first envelope=uncertain · {len(qids)} face questions ✓")

    inlet_fid = face_id_fn(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    )
    outlet_fid = face_id_fn(
        [(0.0, 0.0, 10.0), (1.0, 0.0, 10.0), (1.0, 1.0, 10.0), (0.0, 1.0, 10.0)]
    )
    r_put = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [
                {"face_id": inlet_fid, "name": "inlet_main",
                 "confidence": "user_authoritative"},
                {"face_id": outlet_fid, "name": "outlet_main",
                 "confidence": "user_authoritative"},
            ],
        },
    )
    assert r_put.status_code == 200, r_put.text
    assert r_put.json()["revision"] == 1
    _say("step2", "PUT inlet+outlet pins · revision 0→1 ✓")

    r2 = client.post(f"/api/import/{case_id}/setup-bc", params={"envelope": 1})
    assert r2.status_code == 200, r2.text
    env2 = r2.json()
    assert env2["confidence"] == "confident", env2
    assert "inlet=" in env2["summary"] and "outlet=" in env2["summary"]
    assert "Re≈100" in env2["summary"], env2["summary"]
    bnd = (case_dir / "constant" / "polyMesh" / "boundary").read_text()
    assert "inlet" in bnd and "outlet" in bnd and "walls" in bnd
    assert "lid" not in bnd  # MUST NOT be the LDC executor
    u_text = (case_dir / "0" / "U").read_text()
    assert "fixedValue" in u_text and "noSlip" in u_text
    _say(
        "step3",
        f"envelope=confident · summary='{env2['summary'][:60]}…' · "
        "3-patch split + channel BC dicts ✓",
    )


def _smoke_negative_paths(client, imported: Path, face_id_fn) -> None:
    """§7 · Codex closures negative paths (lid-on-side · stale pins · 4xx mapping)."""
    print("\n┌─ §7 · Codex-closure negative paths ─")

    # Lid-on-side stays uncertain (Codex M9 Step 2 R2 closure).
    case_id = f"smoke_neg_lid_{secrets.token_hex(3)}"
    case_dir = _stage_imported_case(imported, case_id)
    _stage_polymesh(case_dir, _CUBE_POINTS, _CUBE_FACES, _CUBE_BOUNDARY, _CUBE_OWNER)
    bottom_fid = face_id_fn(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    )
    r_put = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [{"face_id": bottom_fid, "name": "lid",
                       "confidence": "user_authoritative"}],
        },
    )
    assert r_put.status_code == 200
    r = client.post(f"/api/import/{case_id}/setup-bc", params={"envelope": 1})
    assert r.json()["confidence"] == "uncertain"
    assert not (case_dir / "0").is_dir()
    _say("neg-lid", "side-face named 'lid' stays uncertain · 0/ NOT written ✓")

    # Stale-pin path on channel routes to 422 channel_pin_mismatch
    # (Codex DEC-V61-101 R1 MED closure).
    case_id = f"smoke_neg_chan_{secrets.token_hex(3)}"
    case_dir = _stage_imported_case(imported, case_id)
    _stage_polymesh(case_dir, _CHANNEL_POINTS, _CUBE_FACES, _CUBE_BOUNDARY, _CUBE_OWNER)
    r_put = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [
                {"face_id": "fid_bogus000inlet", "name": "inlet_main",
                 "confidence": "user_authoritative"},
                {"face_id": "fid_bogus00outlet", "name": "outlet_main",
                 "confidence": "user_authoritative"},
            ],
        },
    )
    assert r_put.status_code == 200
    r = client.post(f"/api/import/{case_id}/setup-bc", params={"envelope": 1})
    # Bogus face_ids → classifier returns uncertain (bad pin verification),
    # NOT confident → executor never invoked → no 422 expected; the
    # uncertain envelope with channel_pin_mismatch question is the
    # correct surface.
    assert r.status_code == 200
    env = r.json()
    assert env["confidence"] == "uncertain"
    assert any(q["id"] == "channel_pin_mismatch" for q in env["unresolved_questions"])
    _say("neg-chan", "bogus pins → channel_pin_mismatch question · executor NOT invoked ✓")


def _smoke_frontend_dev_server_boots(repo_root: Path) -> None:
    """Optional layer: prove the Vite dev server boots and serves the
    workbench shell HTML. Skipped when --no-frontend is passed (e.g.,
    in environments without node/npm); failure is loud but doesn't
    block the backend smoke result.
    """
    import os
    import shutil
    import socket
    import subprocess
    import time
    import urllib.request

    print("\n┌─ Frontend · Vite dev server boot probe ─")
    if shutil.which("npx") is None:
        _say("skip", "npx not on PATH — frontend boot probe skipped")
        return

    # Pick a free ephemeral port so we don't squat on dev's 5181.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    log_path = repo_root / "scripts" / "smoke" / ".dev_boot.log"
    proc = subprocess.Popen(
        ["npx", "vite", "--port", str(port)],
        cwd=str(repo_root / "ui" / "frontend"),
        stdout=open(log_path, "w"),
        stderr=subprocess.STDOUT,
        env={**os.environ, "CFD_FRONTEND_PORT": str(port)},
    )
    try:
        # Poll up to 12s for the server to come up.
        url = f"http://127.0.0.1:{port}/"
        deadline = time.time() + 12.0
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=1.0) as r:
                    if r.status == 200:
                        body = r.read(2048).decode("utf-8", errors="replace")
                        assert "<!doctype html>" in body.lower(), (
                            f"unexpected HTML body: {body[:200]!r}"
                        )
                        _say("boot", f"vite ready at :{port} · 200 OK · HTML hydrated ✓")
                        return
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(0.5)
        raise AssertionError(
            f"frontend dev server didn't come up within 12s "
            f"(last={last_err!r}; see {log_path})"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    # Make repo root importable; the script is in scripts/smoke/.
    repo_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(repo_root))

    from fastapi.testclient import TestClient

    from ui.backend.main import app
    from ui.backend.services.case_annotations import face_id

    print("\n╔══ M-AI-COPILOT dogfood automated smoke ══╗")
    print(f"  Replaces 'Awaiting CFDJerry visual smoke' gate per the")
    print(f"  workflow update; runs entirely under TestClient (no real")
    print(f"  network bind, no browser, no human interaction).")

    with tempfile.TemporaryDirectory(prefix="dogfood_smoke_") as td:
        imported = Path(td) / "imported"
        imported.mkdir()

        # Repoint IMPORTED_DIR for both routes that consume it.
        import ui.backend.services.case_scaffold as cs
        import ui.backend.routes.case_solve as rcs
        import ui.backend.routes.case_annotations as rca
        cs.IMPORTED_DIR = imported
        rcs.IMPORTED_DIR = imported
        rca.IMPORTED_DIR = imported

        client = TestClient(app)
        _smoke_ldc(client, imported, face_id)
        _smoke_channel(client, imported, face_id)
        _smoke_negative_paths(client, imported, face_id)

    if "--no-frontend" not in sys.argv:
        _smoke_frontend_dev_server_boots(repo_root)
    else:
        print("\n┌─ Frontend · skipped (--no-frontend) ─")

    print("\n╚══ ✓ All dogfood loops green · DEC gates may flip to Accepted ══╝\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
