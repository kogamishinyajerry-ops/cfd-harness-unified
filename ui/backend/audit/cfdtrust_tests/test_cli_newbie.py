"""M3 — Newbie-Ready CLI tests.

Covers `cfdtrust init`, `verify-reference`, and `doctor`.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


# ---------- M3.1 init ----------


def test_init_scaffolds_new_case_from_template(tmp_path: Path, repo_root: Path):
    """init must produce a structurally complete case dir whose
    case_manifest.yaml validates against the schema."""
    import shutil
    from cfdtrust.cli_init import cmd_init

    # Stage a cases/ root holding only the flat_plate template (so we test
    # against a known-clean state).
    cases_root = tmp_path / "cases"
    cases_root.mkdir()
    shutil.copytree(
        repo_root / "cases" / "flat_plate_rans_sst",
        cases_root / "flat_plate_rans_sst",
    )

    rc = cmd_init("my_new_case", template_case_id="flat_plate_rans_sst", cases_root=cases_root)
    assert rc == 0
    new = cases_root / "my_new_case"
    assert new.is_dir()
    # case_id must be the new id.
    text = (new / "case_manifest.yaml").read_text()
    assert "\ncase_id: my_new_case\n" in text
    # OpenFOAM dictionaries copied.
    for rel in [
        "system/controlDict", "system/blockMeshDict",
        "constant/transportProperties", "constant/turbulenceProperties",
        "0/U", "0/p", "0/k",
    ]:
        assert (new / rel).is_file(), f"{rel} not cloned"
    # Generated dirs NOT carried over.
    # constant/polyMesh/ should have only .gitkeep
    pm = new / "constant" / "polyMesh"
    assert pm.is_dir()
    assert {p.name for p in pm.iterdir()} == {".gitkeep"}
    # Reference data carried bit-for-bit (with provenance).
    assert (new / "reference" / "cf_reference.csv").is_file()
    assert (new / "reference" / "provenance.md").is_file()
    # Reference CSV hash unchanged (template's reference IS the new case's reference).
    orig_sha = hashlib.sha256(
        (repo_root / "cases" / "flat_plate_rans_sst" / "reference" / "cf_reference.csv").read_bytes()
    ).hexdigest()
    new_sha = hashlib.sha256((new / "reference" / "cf_reference.csv").read_bytes()).hexdigest()
    assert orig_sha == new_sha
    # artifacts/README.md present (F-08 anchor).
    assert (new / "artifacts" / "README.md").is_file()


def test_init_validate_manifest_roundtrip(tmp_path: Path, repo_root: Path):
    """End-to-end: init → validate-manifest succeeds. The new case must
    be structurally complete out of the box."""
    import shutil
    from cfdtrust.cli_init import cmd_init
    from cfdtrust.cli import cmd_validate

    cases_root = tmp_path / "cases"
    cases_root.mkdir()
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", cases_root / "flat_plate_rans_sst")
    assert cmd_init("rt_case", cases_root=cases_root) == 0
    rc = cmd_validate(str(cases_root / "rt_case"))
    assert rc == 0


def test_init_rejects_path_traversal_id(tmp_path: Path, repo_root: Path):
    """case-id must be a safe identifier — no '..', no '/', no leading digit."""
    import shutil
    from cfdtrust.cli_init import cmd_init

    cases_root = tmp_path / "cases"
    cases_root.mkdir()
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", cases_root / "flat_plate_rans_sst")
    for bad in ["../evil", "../../etc", "evil/sub", ".hidden", "1starting_with_digit", "with space"]:
        rc = cmd_init(bad, cases_root=cases_root)
        assert rc == 1, f"must reject {bad!r}"


def test_init_refuses_to_overwrite_existing(tmp_path: Path, repo_root: Path):
    import shutil
    from cfdtrust.cli_init import cmd_init

    cases_root = tmp_path / "cases"
    cases_root.mkdir()
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", cases_root / "flat_plate_rans_sst")
    assert cmd_init("twice", cases_root=cases_root) == 0
    rc = cmd_init("twice", cases_root=cases_root)
    assert rc == 2, "second init with same id must refuse with rc=2"


def test_init_with_missing_template_fails_cleanly(tmp_path: Path):
    from cfdtrust.cli_init import cmd_init

    cases_root = tmp_path / "cases"
    cases_root.mkdir()
    rc = cmd_init("foo", template_case_id="does_not_exist", cases_root=cases_root)
    assert rc == 1


# ---------- M3.2 verify-reference ----------


def test_verify_reference_passes_when_sha_matches(tmp_path: Path, repo_root: Path):
    import shutil
    from cfdtrust.cli_verify import cmd_verify_reference

    case = tmp_path / "vr_case"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    rc = cmd_verify_reference(str(case))
    assert rc == 0


def test_verify_reference_fails_on_drift(tmp_path: Path, repo_root: Path):
    import shutil
    from cfdtrust.cli_verify import cmd_verify_reference

    case = tmp_path / "vr_drift"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    # tamper with the reference CSV
    p = case / "reference" / "cf_reference.csv"
    p.write_text(p.read_text() + "\n0.0,0.0\n")
    rc = cmd_verify_reference(str(case))
    assert rc == 1


def test_verify_reference_fix_updates_manifest_hash(tmp_path: Path, repo_root: Path):
    """--fix must rewrite manifest.reference_csv_sha256 to match the
    on-disk file, then a fresh check passes."""
    import shutil
    from cfdtrust.cli_verify import cmd_verify_reference

    case = tmp_path / "vr_fix"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    p = case / "reference" / "cf_reference.csv"
    p.write_text(p.read_text() + "\n0.5,0.0001\n")
    expected_new_sha = hashlib.sha256(p.read_bytes()).hexdigest()

    rc = cmd_verify_reference(str(case), fix=True)
    assert rc == 0
    # Manifest now carries the new hash.
    manifest_text = (case / "case_manifest.yaml").read_text()
    assert expected_new_sha in manifest_text
    # Subsequent check (no --fix) passes.
    assert cmd_verify_reference(str(case)) == 0


def test_verify_reference_fails_on_missing_manifest(tmp_path: Path):
    from cfdtrust.cli_verify import cmd_verify_reference

    empty = tmp_path / "empty_case"
    empty.mkdir()
    assert cmd_verify_reference(str(empty)) == 1


def test_verify_reference_rejects_absolute_path_in_manifest(tmp_path: Path, repo_root: Path):
    """If a manifest has an absolute reference_csv path, the verify
    command must refuse it (same posture as audit/qoi R16-F-05)."""
    import shutil
    from cfdtrust.cli_verify import cmd_verify_reference

    case = tmp_path / "vr_abs"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    text = (case / "case_manifest.yaml").read_text()
    text = text.replace(
        "reference_csv: reference/cf_reference.csv",
        "reference_csv: /etc/passwd",
    )
    (case / "case_manifest.yaml").write_text(text)
    rc = cmd_verify_reference(str(case))
    assert rc == 1


# ---------- M3.3 doctor ----------


def test_doctor_passes_on_canonical_flat_plate(repo_root: Path):
    from cfdtrust.cli_doctor import cmd_doctor

    rc = cmd_doctor(str(repo_root / "cases" / "flat_plate_rans_sst"))
    assert rc == 0


def test_doctor_passes_on_canonical_bfs(repo_root: Path):
    from cfdtrust.cli_doctor import cmd_doctor

    rc = cmd_doctor(str(repo_root / "cases" / "backward_facing_step"))
    assert rc == 0


def test_doctor_detects_missing_required_dictionary(tmp_path: Path, repo_root: Path):
    """Delete fvSchemes, expect FAIL with the missing-dict reason."""
    import shutil
    from cfdtrust.cli_doctor import cmd_doctor

    case = tmp_path / "doc_missing"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    (case / "system" / "fvSchemes").unlink()
    rc = cmd_doctor(str(case))
    assert rc == 1


def test_doctor_detects_wall_patch_not_in_required_patches(tmp_path: Path, repo_root: Path):
    """M2.3b-style misconfiguration: manifest declares wall_patch=foo but
    foo isn't in geometry_contract.required_patches. Pre-doctor this
    would only surface at run time inside `extract_wall_cf`."""
    import shutil
    from cfdtrust.cli_doctor import cmd_doctor

    case = tmp_path / "doc_wall_patch"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    text = (case / "case_manifest.yaml").read_text()
    # The flat_plate manifest doesn't carry an explicit wall_patch field
    # (it defaults to "wall"). Inject an INCORRECT one to exercise the check.
    text = text.replace(
        "qoi: skin_friction_coefficient",
        "qoi: skin_friction_coefficient\n  wall_patch: doesNotExist",
    )
    (case / "case_manifest.yaml").write_text(text)
    rc = cmd_doctor(str(case))
    assert rc == 1


def test_doctor_detects_reference_csv_sha_drift(tmp_path: Path, repo_root: Path):
    import shutil
    from cfdtrust.cli_doctor import cmd_doctor

    case = tmp_path / "doc_drift"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    p = case / "reference" / "cf_reference.csv"
    p.write_text(p.read_text() + "\n9.9,9.9\n")
    rc = cmd_doctor(str(case))
    assert rc == 1


def test_doctor_warns_on_polluted_polymesh(tmp_path: Path, repo_root: Path):
    """blockMesh output files in source = R14-F-01 hygiene WARN. Should
    NOT cause FAIL (it's documented bad practice, not a structural error)."""
    import shutil
    from cfdtrust.cli_doctor import cmd_doctor

    case = tmp_path / "doc_polluted"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    pm = case / "constant" / "polyMesh"
    pm.mkdir(exist_ok=True)
    (pm / "boundary").write_text("// fake")  # simulated blockMesh output
    rc = cmd_doctor(str(case))
    # 0 (WARN, not FAIL).
    assert rc == 0


def test_doctor_detects_artifacts_readme_missing(tmp_path: Path, repo_root: Path):
    """F-08 evidence anchor — must be present."""
    import shutil
    from cfdtrust.cli_doctor import cmd_doctor

    case = tmp_path / "doc_no_readme"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    (case / "artifacts" / "README.md").unlink()
    rc = cmd_doctor(str(case))
    assert rc == 1


def test_doctor_detects_blockmesh_missing_required_patch(tmp_path: Path, repo_root: Path):
    """Manifest requires `top` patch; if blockMeshDict omits it, doctor must FAIL."""
    import shutil
    from cfdtrust.cli_doctor import cmd_doctor

    case = tmp_path / "doc_patch_mismatch"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", case)
    # Remove the `top` patch block from blockMeshDict so the patch list
    # disagrees with manifest.required_patches.
    import re as _re
    bm = case / "system" / "blockMeshDict"
    text = bm.read_text()
    # Strip the `top` boundary block. Regex-based so it is robust to the
    # block's face-list contents (the flat_plate blockMeshDict gained a NASA
    # pre-plate topology in DEC-V61-209, changing `top` from one face to two).
    stripped = _re.sub(
        r"^[ \t]*top[ \t]*\n[ \t]*\{.*?\n[ \t]*\}[ \t]*\n",
        "",
        text,
        count=1,
        flags=_re.DOTALL | _re.MULTILINE,
    )
    assert stripped != text, "test setup failed to strip the `top` patch block"
    bm.write_text(stripped)
    rc = cmd_doctor(str(case))
    assert rc == 1


def test_doctor_returns_1_on_missing_case_dir(tmp_path: Path):
    from cfdtrust.cli_doctor import cmd_doctor

    rc = cmd_doctor(str(tmp_path / "does_not_exist"))
    assert rc == 1


# ---------- Round-18 R18-F-01..F-02 ----------


def test_r18_f01_template_id_path_traversal_blocked(tmp_path: Path, repo_root: Path):
    """R18-F-01 (MED): `--template ../../etc` MUST be rejected by the
    same validator as new_case_id. Pre-fix, the path traversal would
    have resolved outside cases_root and (if a real dir existed there)
    cloned arbitrary host content into the new case."""
    import shutil
    from cfdtrust.cli_init import cmd_init

    cases_root = tmp_path / "cases"
    cases_root.mkdir()
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", cases_root / "flat_plate_rans_sst")

    for bad in ["../../etc", "../sneaky", "evil/sub", ".hidden", "1_starts_with_digit"]:
        rc = cmd_init("legit_case", template_case_id=bad, cases_root=cases_root)
        assert rc == 1, f"must reject template id {bad!r}"
        # Target dir must not have been created.
        assert not (cases_root / "legit_case").exists(), (
            f"failed init must not leave partial target dir; check {bad!r}"
        )


def test_r18_f02_symlinked_template_refused(tmp_path: Path, repo_root: Path):
    """R18-F-02 (LOW): a template case containing a symlink must be
    refused by cmd_init. Defense-in-depth against future malicious
    templates leaking host file content."""
    import shutil
    from cfdtrust.cli_init import cmd_init

    cases_root = tmp_path / "cases"
    cases_root.mkdir()
    template = cases_root / "evil_template"
    shutil.copytree(repo_root / "cases" / "flat_plate_rans_sst", template)
    # Plant a symlink inside the template.
    outside = tmp_path / "host_secret"
    outside.write_text("hostile content")
    (template / "reference" / "leak_link").symlink_to(outside)

    rc = cmd_init("victim", template_case_id="evil_template", cases_root=cases_root)
    assert rc == 1, "symlinked template must be refused"
    assert not (cases_root / "victim").exists(), "no partial target on refusal"
