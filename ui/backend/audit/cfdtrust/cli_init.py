"""`cfdtrust init` — scaffold a new case from an existing template case.

Why use an existing case as the template (rather than a separate
templates/ dir): every case in cases/ is by definition a complete,
schema-valid, harness-tested example. A separate template directory
would either duplicate that content (drift hazard) or be incomplete.
Using a case as the template means "the templates are validated by
the same tests as the canonical cases."

Honesty contract:
  - Refuse to scaffold over an existing directory (no `--force` in M3.1)
  - Sanitize the new-case-id against a strict alphanumeric+underscore
    pattern: prevents path traversal AND keeps the resulting case_id
    valid as a Python identifier / filesystem name on every platform
  - Carry the reference dataset + provenance bit-for-bit AND keep the
    same `reference_csv_sha256` (the reference data IS the reference;
    cloning the case shouldn't break its honesty contract)
  - Strip generated artifacts (solver.log, residuals.csv, time-step
    dirs, postProcessing/) — the new case starts in a clean state
  - Update `case_manifest.yaml.case_id` to the new id; everything else
    in the manifest stays so a fresh case is structurally complete
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path
from typing import Optional


# A new case id must be a safe filename + a safe Python identifier.
# Refuses path-traversal characters and prevents anything starting with
# a digit (which OpenFOAM and our tooling would not handle well).
_CASE_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")

# Paths to skip when cloning from the template case. These are generated
# at run-time and would pollute the new case with stale state.
_TEMPLATE_SKIP_NAMES = {
    "artifacts",        # cleaned + README restored explicitly below
    "postProcessing",   # OpenFOAM FO output dir
    "constant",         # special-cased: keep system/, BUT clean polyMesh/
}


def _print(stream, msg: str) -> None:
    print(msg, file=stream)


def _is_numeric_time_dir(name: str) -> bool:
    """OpenFOAM time-step dirs are numeric (e.g. `100`, `0.5`). The
    initial-condition dir `0` is preserved because it carries BCs."""
    if name == "0":
        return False
    try:
        float(name)
        return True
    except ValueError:
        return False


def cmd_init(
    new_case_id: str,
    template_case_id: str = "flat_plate_rans_sst",
    cases_root: Optional[Path] = None,
) -> int:
    """Scaffold a new case dir under `cases_root` (default: ./cases/).

    Returns 0 on success, 1 on usage error, 2 on filesystem clash.
    """
    if cases_root is None:
        cases_root = Path.cwd() / "cases"

    # 1) Validate the new id BEFORE touching the filesystem.
    if not _CASE_ID_RE.match(new_case_id):
        _print(sys.stderr,
            f"[cfdtrust] FAIL invalid case id: {new_case_id!r}. Must match "
            f"^[a-zA-Z][a-zA-Z0-9_]{{0,63}}$ (no path separators, no leading digit).")
        return 1

    # R18-F-01 fix: `template_case_id` must be validated against the SAME
    # pattern as new_case_id. Pre-fix, `--template ../../etc` would resolve
    # `cases_root/../../etc` and (if that path was a real dir) clone its
    # content into the new case dir — a copy-in of arbitrary host content.
    if not _CASE_ID_RE.match(template_case_id):
        _print(sys.stderr,
            f"[cfdtrust] FAIL invalid template id: {template_case_id!r}. "
            f"Must match ^[a-zA-Z][a-zA-Z0-9_]{{0,63}}$ — no path traversal allowed.")
        return 1

    template_dir = cases_root / template_case_id
    if not template_dir.is_dir():
        _print(sys.stderr,
            f"[cfdtrust] FAIL template case not found: {template_dir}. "
            f"Available cases: {sorted(p.name for p in cases_root.iterdir() if p.is_dir())}")
        return 1

    target_dir = cases_root / new_case_id
    if target_dir.exists():
        _print(sys.stderr,
            f"[cfdtrust] FAIL target already exists: {target_dir}. "
            f"Refusing to overwrite (no --force in M3.1).")
        return 2

    # R18-F-02 fix: refuse symlinked templates. A future template that
    # contains a symlink (intentional or otherwise) would be followed by
    # shutil.copytree, potentially leaking arbitrary file content into
    # the new case. Same fail-closed posture as R-17 (case-dir symlinks).
    for sub in template_dir.rglob("*"):
        if sub.is_symlink():
            _print(sys.stderr,
                f"[cfdtrust] FAIL template {template_case_id!r} contains a "
                f"symlink at {sub.relative_to(template_dir)}; refusing to follow it. "
                f"Remove the symlink from the template, or copy the underlying "
                f"file in place, and re-run.")
            return 1

    # 2) Clone the template, skipping run-time-generated paths.
    target_dir.mkdir(parents=True)
    for entry in sorted(template_dir.iterdir()):
        if entry.name in _TEMPLATE_SKIP_NAMES:
            continue
        if entry.is_dir() and _is_numeric_time_dir(entry.name):
            continue
        if entry.is_dir():
            shutil.copytree(entry, target_dir / entry.name)
        else:
            shutil.copy2(entry, target_dir / entry.name)

    # 3) Re-create the constant/ tree with only the source dictionaries
    #    (transportProperties + turbulenceProperties) and an empty
    #    polyMesh/ placeholder. Generated mesh files are skipped.
    src_constant = template_dir / "constant"
    if src_constant.is_dir():
        dst_constant = target_dir / "constant"
        dst_constant.mkdir(exist_ok=True)
        for entry in src_constant.iterdir():
            if entry.name == "polyMesh":
                continue
            if entry.is_file():
                shutil.copy2(entry, dst_constant / entry.name)
            elif entry.is_dir():
                shutil.copytree(entry, dst_constant / entry.name)
        # Empty polyMesh/ with .gitkeep so the placeholder dir exists.
        pm = dst_constant / "polyMesh"
        pm.mkdir(exist_ok=True)
        gk_src = template_dir / "constant" / "polyMesh" / ".gitkeep"
        if gk_src.exists():
            shutil.copy2(gk_src, pm / ".gitkeep")
        else:
            (pm / ".gitkeep").write_text(
                "# Empty placeholder so the directory exists in git.\n"
                "# blockMesh populates this directory at runtime.\n"
            )

    # 4) Re-create artifacts/ with just the README anchor (F-08 contract).
    art_dir = target_dir / "artifacts"
    art_dir.mkdir(exist_ok=True)
    art_readme_src = template_dir / "artifacts" / "README.md"
    art_readme = art_dir / "README.md"
    if art_readme_src.exists():
        shutil.copy2(art_readme_src, art_readme)
    else:
        art_readme.write_text(
            f"# Artifacts — {new_case_id}\n\n"
            "Trust harness writes per-run artifacts here. Do not delete this "
            "README (F-08 contract anchor).\n"
        )

    # 5) Rewrite case_manifest.yaml's `case_id` field.
    manifest_path = target_dir / "case_manifest.yaml"
    if not manifest_path.exists():
        _print(sys.stderr,
            f"[cfdtrust] FAIL template case is missing case_manifest.yaml: {manifest_path}")
        # Clean up — refuse to leave a partially-initialized case dir.
        shutil.rmtree(target_dir, ignore_errors=True)
        return 1
    text = manifest_path.read_text()
    new_text = re.sub(
        r"^case_id:\s*\S+",
        f"case_id: {new_case_id}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if new_text == text:
        _print(sys.stderr,
            "[cfdtrust] FAIL could not locate `case_id:` line in manifest; "
            "template case may be malformed.")
        shutil.rmtree(target_dir, ignore_errors=True)
        return 1
    manifest_path.write_text(new_text)

    # 6) Report next steps so a fresh user knows what to do.
    rel = target_dir.relative_to(cases_root.parent) if cases_root.parent.exists() else target_dir
    print(f"[cfdtrust] OK   initialized case {new_case_id!r} at {rel}")
    print(f"             template: {template_case_id}")
    print(f"             next steps:")
    print(f"               1. Edit {rel}/case_manifest.yaml to set your geometry/BCs/QoI")
    print(f"               2. (Optional) Update {rel}/system/ dictionaries for your case")
    print(f"               3. PYTHONPATH=src python -m cfdtrust.cli validate-manifest {rel}")
    print(f"               4. PYTHONPATH=src python -m cfdtrust.cli doctor {rel}")
    print(f"               5. PYTHONPATH=src python -m cfdtrust.cli run {rel}")
    return 0
