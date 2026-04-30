"""DEC-V61-102 Phase 1.4 · bc_setup honors user-overridden dicts.

Codex round-1 P1 closure (8b4e602): the LDC + channel dict-authoring
helpers used to unconditionally overwrite every allowlisted dict on
each [AI 处理] click. Now they consult the manifest and skip any path
flagged source=user, returning ``(written, skipped)`` so the caller
can record AI authorship only for paths actually re-authored.
"""
from __future__ import annotations

from pathlib import Path

from ui.backend.services.case_manifest import (
    CaseManifest,
    mark_user_override,
    read_case_manifest,
    write_case_manifest,
)
from ui.backend.services.case_solve.bc_setup import (
    _author_channel_dicts,
    _author_dicts,
)


def _stage_case(case_dir: Path) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    write_case_manifest(case_dir, CaseManifest(case_id=case_dir.name))


def test_author_dicts_skips_user_overridden_path(tmp_path):
    """If the engineer staged a manual edit on system/controlDict via
    POST /cases/{id}/dicts, a subsequent [AI 处理] click must NOT
    overwrite it. The helper returns the path in ``skipped``."""
    case_dir = tmp_path / "case-ldc"
    _stage_case(case_dir)

    user_content = "FoamFile { class dictionary; }\napplication icoFoam;\nendTime 99;\n"
    (case_dir / "system").mkdir(parents=True, exist_ok=True)
    (case_dir / "system" / "controlDict").write_text(user_content)
    mark_user_override(
        case_dir,
        relative_path="system/controlDict",
        new_content=user_content.encode("utf-8"),
    )

    written, skipped = _author_dicts(case_dir)

    assert "system/controlDict" in skipped
    assert "system/controlDict" not in written
    # File on disk is the user's content, untouched by AI re-author.
    assert (case_dir / "system" / "controlDict").read_text() == user_content
    # Other allowlisted paths are still authored fresh.
    assert "system/fvSchemes" in written
    assert "constant/physicalProperties" in written


def test_author_dicts_writes_all_when_no_overrides(tmp_path):
    """Fresh case with manifest but no overrides — every path is
    authored, ``skipped`` is empty."""
    case_dir = tmp_path / "case-fresh"
    _stage_case(case_dir)

    written, skipped = _author_dicts(case_dir)

    assert skipped == ()
    assert "system/controlDict" in written
    assert "system/fvSchemes" in written
    assert "system/fvSolution" in written
    assert "constant/physicalProperties" in written
    assert "constant/momentumTransport" in written


def test_author_dicts_no_manifest_authors_everything(tmp_path):
    """Case dir with no manifest yet (e.g. mid-import) — is_user_override
    returns False, so AI authors all paths."""
    case_dir = tmp_path / "case-no-manifest"
    case_dir.mkdir()
    # Deliberately no write_case_manifest call.

    written, skipped = _author_dicts(case_dir)

    assert skipped == ()
    assert len(written) >= 5


def test_author_channel_dicts_skips_user_overrides(tmp_path):
    """Channel path mirrors LDC: a user-edited fvSolution survives
    re-running setup_channel_bc."""
    case_dir = tmp_path / "case-channel"
    _stage_case(case_dir)

    user_content = "FoamFile {} solvers {} PIMPLE { nOuterCorrectors 5; }\n"
    (case_dir / "system").mkdir(parents=True, exist_ok=True)
    (case_dir / "system" / "fvSolution").write_text(user_content)
    mark_user_override(
        case_dir,
        relative_path="system/fvSolution",
        new_content=user_content.encode("utf-8"),
    )

    written, skipped = _author_channel_dicts(case_dir)

    assert "system/fvSolution" in skipped
    assert "system/fvSolution" not in written
    assert (case_dir / "system" / "fvSolution").read_text() == user_content


def test_atomic_commit_rolls_back_on_mid_rename_failure(tmp_path, monkeypatch):
    """Codex round-5 MED #2 closure: if a rename fails partway through
    the 7-file batch, already-renamed files must roll back to prior
    bytes and remaining tempfiles must be cleaned up. No partial
    transaction commits.

    Setup: stage prior content for the first dict, fault-inject the
    SECOND os.replace call to raise OSError, then call _author_dicts.
    Expect: OSError surfaces, the first dict still shows its prior
    content (rolled back), and no .tmp files remain in the case dir."""
    from ui.backend.services.case_solve import bc_setup as bc_setup_mod

    case_dir = tmp_path / "case-faulty"
    _stage_case(case_dir)

    prior_content = "PRIOR controlDict\n"
    (case_dir / "system").mkdir(parents=True, exist_ok=True)
    (case_dir / "system" / "controlDict").write_text(prior_content)

    real_replace = bc_setup_mod.os.replace
    call_count = {"n": 0}

    def faulty_replace(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated mid-rename failure (round-5 fault inject)")
        return real_replace(src, dst)

    monkeypatch.setattr(bc_setup_mod.os, "replace", faulty_replace)

    raised = False
    try:
        bc_setup_mod._author_dicts(case_dir)
    except OSError:
        raised = True
    assert raised, "expected the fault-injected OSError to propagate"

    # The critical invariant: regardless of iteration order, the
    # transaction either committed entirely (no faults seen — not
    # this test's path) or rolled back. Since we faulted #2, all
    # already-renamed files must have been rolled back. ControlDict's
    # final content equals its prior content (rollback restored it,
    # OR the iteration order never touched it because it came after
    # the failure).
    final_ctrl = (case_dir / "system" / "controlDict").read_text()
    assert final_ctrl == prior_content, (
        f"controlDict not restored to prior content after rollback: "
        f"got {final_ctrl!r}, expected {prior_content!r}"
    )
    # NO .tmp files leaked — Codex round-5 explicitly fault-injected
    # the prior version and saw 0/p.tmp orphaned. The 2-phase commit
    # must clean up all tempfiles on rollback.
    leftover_tmps = list(case_dir.rglob("*.tmp"))
    assert leftover_tmps == [], f"leaked tempfiles after rollback: {leftover_tmps}"


def test_author_dicts_records_authorship_via_caller(tmp_path):
    """After _author_dicts returns, the caller (setup_ldc_bc) calls
    mark_ai_authored on `written`. We don't invoke setup_ldc_bc here
    (that needs a real polyMesh); instead, verify the contract: the
    helper-level skip path is enough to keep manifest source=user."""
    case_dir = tmp_path / "case-mixed"
    _stage_case(case_dir)

    # Stage two user overrides.
    for rel in ("system/controlDict", "system/fvSchemes"):
        (case_dir / Path(rel).parent).mkdir(parents=True, exist_ok=True)
        (case_dir / rel).write_text(f"USER content for {rel}\n")
        mark_user_override(
            case_dir,
            relative_path=rel,
            new_content=f"USER content for {rel}\n".encode("utf-8"),
        )

    written, skipped = _author_dicts(case_dir)

    assert set(skipped) == {"system/controlDict", "system/fvSchemes"}
    # Manifest still records both as source=user — _author_dicts didn't
    # touch them, so mark_ai_authored (called by setup_ldc_bc) would
    # only see `written`, never the skipped pair. Verify by reading
    # the manifest now.
    manifest = read_case_manifest(case_dir)
    for rel in ("system/controlDict", "system/fvSchemes"):
        entry = manifest.overrides.raw_dict_files[rel]
        assert entry.source == "user", f"{rel} lost user override"
