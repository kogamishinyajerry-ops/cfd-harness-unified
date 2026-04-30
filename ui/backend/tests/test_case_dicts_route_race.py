"""DEC-V61-102 Phase 1 round-3 P1-HIGH closure · route-level race tests.

Codex round-3 (commit 4361ef7) flagged the round-2 race tests as
insufficient: they wrapped ``case_lock`` around hand-built sequences,
proving the lock works in isolation but not that the actual handlers
acquire it. These tests drive the FastAPI handlers via TestClient with
two threads racing POST /cases/{id}/dicts against ``_author_dicts``,
plus exercise the symlink-escape error path.
"""
from __future__ import annotations

import os
import secrets
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from ui.backend.services.case_manifest import (
    CaseManifest,
    read_case_manifest,
    write_case_manifest,
)
from ui.backend.services.case_solve.bc_setup import _author_dicts


def _isolate(monkeypatch, tmp_path: Path) -> Path:
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_dicts.IMPORTED_DIR", target
    )
    return target


def _stage(imported_dir: Path, case_id: str) -> Path:
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    (case_dir / "system").mkdir()
    write_case_manifest(case_dir, CaseManifest(case_id=case_id))
    return case_dir


def _client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def _safe_id() -> str:
    return f"imported_2026-04-30T00-00-00Z_{secrets.token_hex(4)}"


_VALID_BODY = "FoamFile { class dictionary; }\napplication icoFoam;\nendTime 99;\n"


# ---------------------------------------------------------------------------
# 1. Concurrent POST + bc_setup _author_dicts: no manifest+disk divergence
# ---------------------------------------------------------------------------


def test_route_post_dicts_serializes_with_author_dicts(monkeypatch, tmp_path):
    """Drive POST /cases/{id}/dicts/system/controlDict against a
    parallel _author_dicts call. Whatever the interleaving, the final
    state must be self-consistent: manifest.source matches what
    is on disk."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(imported, case_id)
    client = _client()

    user_body = "FoamFile { class dictionary; }\napplication icoFoam;\nendTime 50;\n"

    def hit_post():
        # Slight stagger so the AI side has a chance to enter first
        # in some runs and lose in others. Either order is fine — we
        # only assert the post-condition is consistent.
        time.sleep(0.005)
        client.post(
            f"/api/cases/{case_id}/dicts/system/controlDict",
            json={"content": user_body},
        )

    def hit_author():
        _author_dicts(case_dir)  # Wraps in case_lock via bc_setup helper

    # Run several rounds since racing twice is more diagnostic than once.
    for _round in range(3):
        # Reset state between rounds.
        (case_dir / "system" / "controlDict").unlink(missing_ok=True)
        manifest = read_case_manifest(case_dir)
        manifest.overrides.raw_dict_files.clear()
        write_case_manifest(case_dir, manifest)

        t1 = threading.Thread(target=hit_post)
        t2 = threading.Thread(target=hit_author)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        manifest = read_case_manifest(case_dir)
        entry = manifest.overrides.raw_dict_files.get("system/controlDict")
        on_disk = (case_dir / "system" / "controlDict").read_bytes().decode("utf-8")

        # Invariant: manifest source matches the disk content's authoring
        # side. If user ran first then was clobbered by AI, manifest
        # would say "user" but on_disk would be the AI body — that's
        # the exact divergence the lock prevents.
        if entry and entry.source == "user":
            assert on_disk == user_body, (
                f"Round {_round}: MANIFEST+DISK DIVERGENCE — manifest "
                f"says source=user but on-disk content is the AI re-author."
            )
        else:
            # source=ai (or no entry) → on disk should be the AI body,
            # not the user body.
            assert user_body not in on_disk, (
                f"Round {_round}: MANIFEST+DISK DIVERGENCE — manifest "
                f"says source=ai but on-disk content is the user body."
            )


# ---------------------------------------------------------------------------
# 2. Symlink-escape under O_NOFOLLOW: 422 with failing_check=symlink_escape
# ---------------------------------------------------------------------------


def test_post_dicts_refuses_planted_symlink_at_lock_path(monkeypatch, tmp_path):
    """If an attacker (or a confused workflow) places a symlink at
    case_dir/.case_lock pointing outside the case dir, the O_NOFOLLOW
    open in case_lock() must refuse, surfacing 422 not 500."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(imported, case_id)
    client = _client()

    # Plant the symlink. Target is an absolute path outside the case dir.
    external_target = tmp_path / "external_target_should_not_be_touched"
    lock_path = case_dir / ".case_lock"
    os.symlink(external_target, lock_path)

    resp = client.post(
        f"/api/cases/{case_id}/dicts/system/controlDict",
        json={"content": _VALID_BODY},
    )

    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["detail"]["failing_check"] == "symlink_escape"
    # The external target was never touched.
    assert not external_target.exists()


# ---------------------------------------------------------------------------
# 3. Lock release survives an in-body HTTPException (etag mismatch)
# ---------------------------------------------------------------------------


def test_etag_mismatch_releases_lock(monkeypatch, tmp_path):
    """A 409 etag mismatch raised inside the locked critical section
    must release the lock so the next POST doesn't deadlock."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(imported, case_id)
    (case_dir / "system" / "controlDict").write_text(_VALID_BODY)
    client = _client()

    # First POST with bogus expected_etag → 409 inside the lock.
    bad = client.post(
        f"/api/cases/{case_id}/dicts/system/controlDict",
        json={"content": _VALID_BODY, "expected_etag": "deadbeefdeadbeef"},
    )
    assert bad.status_code == 409

    # Lock should be free now. A second POST without expected_etag
    # should succeed without timing out.
    ok_event = threading.Event()

    def follow_up():
        r = client.post(
            f"/api/cases/{case_id}/dicts/system/controlDict",
            json={"content": _VALID_BODY},
        )
        if r.status_code == 200:
            ok_event.set()

    t = threading.Thread(target=follow_up)
    t.start()
    t.join(timeout=3.0)
    assert ok_event.is_set(), "POST after 409 timed out — lock leaked"
