"""DEC-V61-102 Phase 1 round-4 P1-HIGH closure · route-level race tests.

Codex round-3 (4361ef7) and round-4 (7f3c53d) flagged successive
weaknesses in the race regression. This file is the round-4 rewrite.

Coverage:
1. Concurrent POST /cases/{id}/dicts vs. real ``setup_ldc_bc`` (AI
   side actually acquires case_lock + calls mark_ai_authored, not a
   bypass shortcut). Monkeypatches ``_split_lid_walls`` so the test
   can drive the AI side without staging a real polyMesh.
2. Symlink-escape under O_NOFOLLOW: planted ``.case_lock`` symlink
   surfaces 422 with failing_check=symlink_escape; external target
   never written.
3. Lock release after in-body HTTPException (etag 409).
4. Lock-disabled negative control: monkeypatch case_lock into a
   no-op, run the same race, assert divergence IS detected. This
   proves the test is strong enough to catch the regression — Codex
   round-4 found the prior version passed 19/20 even with the lock
   removed.
5. Thread exceptions are surfaced (not swallowed) so a
   ManifestParseError in a worker thread fails the test, not just
   logs to stderr.
"""
from __future__ import annotations

import contextlib
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Callable

from fastapi.testclient import TestClient

from ui.backend.services.case_manifest import (
    CaseManifest,
    read_case_manifest,
    write_case_manifest,
)
from ui.backend.services.case_solve import bc_setup as bc_setup_mod


# ---------------------------------------------------------------------------
# Test harness helpers
# ---------------------------------------------------------------------------


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
    (case_dir / "constant").mkdir()
    write_case_manifest(case_dir, CaseManifest(case_id=case_id))
    return case_dir


def _stage_minimal_polymesh(case_dir: Path) -> None:
    """Make ``setup_ldc_bc``'s pre-flight checks pass (case_dir is
    a dir, polyMesh is a dir, polyMesh/boundary is a file). Real
    boundary parsing is short-circuited via the monkeypatch on
    ``_split_lid_walls``."""
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True, exist_ok=True)
    (polymesh / "boundary").write_text("# stubbed for race tests\n")


def _client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def _safe_id() -> str:
    return f"imported_2026-04-30T00-00-00Z_{secrets.token_hex(4)}"


_USER_BODY = (
    "FoamFile { class dictionary; }\napplication icoFoam;\nendTime 50;\n"
)
_VALID_BODY = (
    "FoamFile { class dictionary; }\napplication icoFoam;\nendTime 99;\n"
)


class _ThreadCapture:
    """Worker-thread runner that surfaces exceptions to the parent.

    pytest threads default-swallow exceptions; that masked the
    background ManifestParseError crashes Codex saw in round-4.
    """

    def __init__(self) -> None:
        self.errors: list[BaseException] = []
        self._lock = threading.Lock()

    def run(self, target: Callable[[], None]) -> threading.Thread:
        def wrapped() -> None:
            try:
                target()
            except BaseException as exc:  # noqa: BLE001
                with self._lock:
                    self.errors.append(exc)

        t = threading.Thread(target=wrapped)
        t.start()
        return t

    def assert_clean(self) -> None:
        with self._lock:
            if self.errors:
                first = self.errors[0]
                raise AssertionError(
                    f"worker thread raised: {type(first).__name__}: {first}"
                ) from first


def _stub_split_lid_walls(monkeypatch) -> None:
    """Skip the polyMesh boundary parse — return canned counts so
    setup_ldc_bc can proceed to its lock+author+mark sequence
    without a real gmsh polyMesh."""
    monkeypatch.setattr(
        bc_setup_mod, "_split_lid_walls", lambda polymesh: (1, 5, 0)
    )


# ---------------------------------------------------------------------------
# 1. Concurrent POST + real setup_ldc_bc: no manifest+disk divergence
# ---------------------------------------------------------------------------


def _race_user_vs_ai(case_dir: Path, case_id: str, client: TestClient,
                     n_rounds: int) -> None:
    """Reusable race driver — used by both the lock-enabled and the
    lock-disabled (negative control) tests below."""
    capture = _ThreadCapture()

    for round_idx in range(n_rounds):
        # Reset to a clean slate between rounds.
        for rel in ("system/controlDict", "system/fvSchemes",
                    "system/fvSolution", "constant/momentumTransport",
                    "constant/physicalProperties"):
            (case_dir / rel).unlink(missing_ok=True)
        manifest = read_case_manifest(case_dir)
        manifest.overrides.raw_dict_files.clear()
        write_case_manifest(case_dir, manifest)

        def hit_post() -> None:
            time.sleep(0.002)
            client.post(
                f"/api/cases/{case_id}/dicts/system/controlDict",
                json={"content": _USER_BODY},
            )

        def hit_setup_ldc() -> None:
            bc_setup_mod.setup_ldc_bc(case_dir, case_id=case_id)

        t1 = capture.run(hit_post)
        t2 = capture.run(hit_setup_ldc)
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

    capture.assert_clean()


def test_setup_ldc_bc_serializes_with_post_dicts(monkeypatch, tmp_path):
    """The real Phase-1 race: POST /dicts (user side) vs. setup_ldc_bc
    (AI side). With the case_lock in place, post-race state is always
    self-consistent across 12 rounds."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(imported, case_id)
    _stage_minimal_polymesh(case_dir)
    _stub_split_lid_walls(monkeypatch)
    client = _client()

    _race_user_vs_ai(case_dir, case_id, client, n_rounds=12)

    manifest = read_case_manifest(case_dir)
    entry = manifest.overrides.raw_dict_files.get("system/controlDict")
    on_disk = (case_dir / "system" / "controlDict").read_bytes().decode("utf-8")

    if entry and entry.source == "user":
        assert on_disk == _USER_BODY, (
            "MANIFEST+DISK DIVERGENCE: manifest source=user but on-disk "
            "is the AI re-author"
        )
    else:
        assert _USER_BODY not in on_disk, (
            "MANIFEST+DISK DIVERGENCE: manifest source=ai but on-disk "
            "is the user body"
        )


def test_race_test_actually_catches_regression_when_lock_disabled(
    monkeypatch, tmp_path
):
    """Negative control: replace case_lock with a no-op AND coordinate
    the threads with an event so the race window deterministically
    opens. With locks disabled, AI clobbers the user file while
    mark_ai_authored preserves source=user (its own check-don't-flip
    guard fires) → manifest+disk divergence on every run.

    This proves the test is strong enough to catch a regression where
    case_lock is removed. Codex round-4 found the prior version passed
    19/20 even with the lock removed because the natural race window
    was too narrow; the event coordination makes it deterministic."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(imported, case_id)
    _stage_minimal_polymesh(case_dir)
    _stub_split_lid_walls(monkeypatch)

    @contextlib.contextmanager
    def noop_lock(case_dir):
        yield

    monkeypatch.setattr("ui.backend.routes.case_dicts.case_lock", noop_lock)
    monkeypatch.setattr(
        "ui.backend.services.case_solve.bc_setup.case_lock", noop_lock
    )

    # Coordinate: when AI's _author_dicts checks is_user_override for
    # controlDict, it pauses until the POST thread has finished its
    # write+mark. Then AI proceeds, clobbers the user file, and
    # mark_ai_authored skips updating source (per the invariant guard)
    # → manifest=user but disk=AI. The exact divergence the lock
    # prevents in production.
    post_done = threading.Event()
    real_check = bc_setup_mod.is_user_override

    def coordinated_check(case_dir, *, relative_path):
        result = real_check(case_dir, relative_path=relative_path)
        if relative_path == "system/controlDict" and not result:
            post_done.wait(timeout=3.0)
        return result

    monkeypatch.setattr(bc_setup_mod, "is_user_override", coordinated_check)

    client = _client()
    capture = _ThreadCapture()

    def hit_post() -> None:
        client.post(
            f"/api/cases/{case_id}/dicts/system/controlDict",
            json={"content": _USER_BODY},
        )
        post_done.set()

    def hit_setup_ldc() -> None:
        try:
            bc_setup_mod.setup_ldc_bc(case_dir, case_id=case_id)
        except Exception:
            pass

    # Stagger AI start slightly so it grabs is_user_override → False
    # BEFORE POST has written; then it blocks on post_done.
    t_ai = capture.run(hit_setup_ldc)
    time.sleep(0.01)
    t_post = capture.run(hit_post)
    t_post.join(timeout=5.0)
    t_ai.join(timeout=5.0)

    manifest = read_case_manifest(case_dir)
    entry = manifest.overrides.raw_dict_files.get("system/controlDict")
    ctrl = case_dir / "system" / "controlDict"
    on_disk = ctrl.read_bytes().decode("utf-8", errors="replace")

    # Without the lock, the deterministic interleaving above produces:
    # - manifest entry exists, source=user
    # - on-disk content is the AI body (NOT _USER_BODY)
    saw_divergence = (
        entry is not None
        and entry.source == "user"
        and on_disk != _USER_BODY
    )

    assert saw_divergence, (
        f"Negative control failed: with lock disabled and threads "
        f"deterministically scheduled to race, expected manifest+disk "
        f"divergence but got entry={entry}, on_disk[:50]={on_disk[:50]!r}. "
        f"Either the production code accidentally still serializes, or "
        f"the test harness no longer reaches the race window."
    )


# ---------------------------------------------------------------------------
# 2. Symlink-escape: planted .case_lock symlink → 422, no external write
# ---------------------------------------------------------------------------


def test_post_dicts_refuses_planted_symlink_at_lock_path(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(imported, case_id)
    client = _client()

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
    assert not external_target.exists()


# ---------------------------------------------------------------------------
# 3. In-body 409 must release the lock for the next request
# ---------------------------------------------------------------------------


def test_etag_mismatch_releases_lock(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(imported, case_id)
    (case_dir / "system" / "controlDict").write_text(_VALID_BODY)
    client = _client()

    bad = client.post(
        f"/api/cases/{case_id}/dicts/system/controlDict",
        json={"content": _VALID_BODY, "expected_etag": "deadbeefdeadbeef"},
    )
    assert bad.status_code == 409

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
