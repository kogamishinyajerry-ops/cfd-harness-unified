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
    """Codex round-5 MED #2 + round-6 LOW closure: fault-inject the
    SECOND os.replace and verify the FIRST file's prior content was
    actually restored (proving rollback covers already-committed
    renames, not just paths that came after the failure).

    Codex round-6 noted the prior version of this test injected at
    rename #2 but `controlDict` was rename #5, so the test never
    actually proved restoration of an already-renamed file. Fix:
    discover the rename order by spying on os.replace, snapshot the
    FIRST file's prior content before _author_dicts runs, fault-inject
    rename #2, then assert the FIRST file equals its prior bytes."""
    from ui.backend.services.case_solve import bc_setup as bc_setup_mod

    case_dir = tmp_path / "case-faulty"
    _stage_case(case_dir)

    # Pre-seed prior content for ALL 7 dicts so we can verify whichever
    # one ends up as rename #1 has its prior content restored.
    prior_marker = "PRIOR_{rel}_DO_NOT_CLOBBER\n"
    targets = [
        "0/U", "0/p",
        "constant/physicalProperties", "constant/momentumTransport",
        "system/controlDict", "system/fvSchemes", "system/fvSolution",
    ]
    for rel in targets:
        p = case_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(prior_marker.format(rel=rel))

    real_replace = bc_setup_mod.os.replace
    rename_order: list[str] = []
    call_count = {"n": 0}

    def spying_faulty_replace(src, dst):
        call_count["n"] += 1
        # Track the destination so we know which rel was the 1st rename.
        rename_order.append(str(dst))
        if call_count["n"] == 2:
            raise OSError("simulated mid-rename failure (round-6 fault inject)")
        return real_replace(src, dst)

    monkeypatch.setattr(bc_setup_mod.os, "replace", spying_faulty_replace)

    raised = False
    try:
        bc_setup_mod._author_dicts(case_dir)
    except OSError:
        raised = True
    assert raised, "expected the fault-injected OSError to propagate"

    # Critical: rename #1 was committed BEFORE rename #2 raised. Its
    # prior content must have been restored by the rollback.
    assert len(rename_order) >= 1, "expected at least one rename to occur"
    first_renamed_abs = Path(rename_order[0])
    first_renamed_rel = str(first_renamed_abs.relative_to(case_dir))
    actual = first_renamed_abs.read_text()
    expected = prior_marker.format(rel=first_renamed_rel)
    assert actual == expected, (
        f"rollback FAILED to restore rename #1 ({first_renamed_rel}): "
        f"got {actual!r}, expected {expected!r}"
    )

    # NO .tmp files leaked — covers both successful tmp writes that
    # weren't yet renamed AND the partial-write blind spot Codex
    # round-6 flagged.
    leftover_tmps = list(case_dir.rglob("*.tmp"))
    assert leftover_tmps == [], f"leaked tempfiles after rollback: {leftover_tmps}"


def test_atomic_commit_cleans_up_partial_temp_write_failure(tmp_path, monkeypatch):
    """Codex round-6 MED closure: if tmp.write_text fails MID-write
    (creating + truncating the .tmp on disk before raising), the
    cleanup loop must still unlink it. The prior cleanup iterated
    ``tempfiles_written`` (the success list), so a partial write
    leaked the .tmp.

    Setup: monkeypatch Path.write_text to write the first part of the
    content then raise. Confirm no .tmp files remain in the case dir
    after the failure surfaces."""
    from ui.backend.services.case_solve import bc_setup as bc_setup_mod

    case_dir = tmp_path / "case-partial"
    _stage_case(case_dir)

    real_write_text = Path.write_text
    call_count = {"n": 0}

    def partial_write_text(self, data, *args, **kwargs):
        # Only intercept .tmp writes inside our case_dir to avoid
        # nuking other I/O during pytest infrastructure.
        if self.name.endswith(".tmp") and case_dir in self.parents:
            call_count["n"] += 1
            if call_count["n"] == 4:
                # Simulate ENOSPC mid-write: file gets created/truncated
                # then errors.
                real_write_text(self, data[: len(data) // 2], *args, **kwargs)
                raise OSError("simulated partial-write failure (round-6)")
        return real_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", partial_write_text)

    raised = False
    try:
        bc_setup_mod._author_dicts(case_dir)
    except OSError:
        raised = True
    assert raised, "expected the fault-injected OSError to propagate"

    # The torn .tmp from the failed write MUST have been unlinked by
    # the cleanup loop. Codex round-6 reproduced the leak with this
    # exact scenario before the fix.
    leftover_tmps = list(case_dir.rglob("*.tmp"))
    assert leftover_tmps == [], (
        f"partial tmp write leaked: {leftover_tmps} — "
        f"cleanup must iterate the full plan, not just successful writes"
    )


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
