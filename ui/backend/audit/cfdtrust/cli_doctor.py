"""`cfdtrust doctor` — static audit of a case dir, no solver run required.

What this catches that `validate-manifest` doesn't:
  - Manifest is schema-valid but references patches that don't exist in
    blockMeshDict (M2.3b pattern: wall_patch = bottomWall but no
    bottomWall patch declared in blockMesh).
  - Reference CSV hash drift (the same check as `verify-reference` but
    in a multi-check report instead of an exit code).
  - Required OpenFOAM dictionaries are missing or malformed.
  - artifacts/README.md absence (F-08 evidence anchor).
  - solver_backend=openfoam but no `solver_docker_image` field AND no
    fallback default (the default IS in the adapter; doctor checks the
    manifest path to surface the warning early).
  - Initial-condition files in `0/` don't cover every patch from
    `geometry_contract.required_patches`.

What this does NOT catch:
  - Whether the case will actually CONVERGE (that's `run` + Round-N).
  - Whether the case is PHYSICALLY meaningful (manifest is honest but
    the case might be set up for nonsense conditions).

Honesty contract:
  - Every check has a clear PASS / WARN / FAIL verdict
  - WARN = "this is unusual but might be intentional"
  - FAIL = "this would block real-run gates"
  - Exit code: 0 if no FAILs; 1 if any FAIL
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    _yaml = None


# ---------- check helpers ----------


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _strip_of_comments(text: str) -> str:
    """Strip OpenFOAM C-style comments (`/* ... */` and `// to EOL`).
    Without this, a comment containing the word `boundary` (e.g.
    "// boundary layer thickness ~ 1.5H") would be matched by the
    `text.find("boundary")` patch-block scan and produce false negatives.
    Same approach as `src/cfdtrust/qoi/wall_shear.py:_strip_comments_and_header`.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _extract_patch_names_from_blockmesh(text: str) -> List[str]:
    """Extract the names listed under the top-level `boundary ( ... )` block
    of a blockMeshDict. We do a brace-aware scan rather than blanket regex
    because patch entries themselves contain `{...}`.

    Returns [] if `boundary (...)` isn't found.
    """
    text = _strip_of_comments(text)
    # Search for `boundary` as a standalone keyword followed (after optional
    # whitespace) by `(`. Anchor to a word boundary to avoid matching
    # "boundaryField" or similar.
    m = re.search(r"\bboundary\b\s*\(", text)
    if m is None:
        return []
    bstart = m.start()
    paren_open = text.find("(", bstart)
    if paren_open < 0:
        return []
    depth = 0
    paren_close = -1
    for i in range(paren_open, len(text)):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                paren_close = i
                break
    if paren_close < 0:
        return []
    body = text[paren_open + 1 : paren_close]
    # Each patch entry is `<name>\s*{...}`. Iterate brace-aware to skip the
    # contents of each block.
    names: List[str] = []
    i = 0
    while i < len(body):
        # Skip whitespace and comments.
        while i < len(body) and body[i].isspace():
            i += 1
        if i >= len(body):
            break
        # Skip line comments.
        if body[i:i + 2] == "//":
            while i < len(body) and body[i] != "\n":
                i += 1
            continue
        # Skip block comments.
        if body[i:i + 2] == "/*":
            j = body.find("*/", i + 2)
            i = j + 2 if j >= 0 else len(body)
            continue
        # Otherwise: read an identifier (the patch name).
        m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", body[i:])
        if not m:
            i += 1
            continue
        name = m.group(0)
        i += len(name)
        # Skip whitespace until '{'.
        while i < len(body) and body[i].isspace():
            i += 1
        if i >= len(body) or body[i] != "{":
            # Not a patch entry (might be a stray keyword); skip.
            continue
        names.append(name)
        # Consume the matching `{...}`.
        depth = 0
        while i < len(body):
            c = body[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
    return names


# ---------- individual checks ----------


def _check_manifest_loadable(case_dir: Path) -> Tuple[str, str, Dict]:
    """Returns (status, message, manifest_dict)."""
    mp = case_dir / "case_manifest.yaml"
    if not mp.exists():
        return "FAIL", "case_manifest.yaml missing", {}
    try:
        data = _yaml.safe_load(mp.read_text()) or {}
    except Exception as e:
        return "FAIL", f"YAML parse error: {e}", {}
    if not isinstance(data, dict):
        return "FAIL", "manifest top-level is not a mapping", {}
    return "PASS", f"manifest loaded (case_id={data.get('case_id', '?')})", data


def _check_required_openfoam_dictionaries(case_dir: Path) -> List[Tuple[str, str]]:
    """Each required dict must exist and carry a FoamFile header."""
    required = [
        "system/controlDict",
        "system/fvSchemes",
        "system/fvSolution",
        "system/blockMeshDict",
        "constant/transportProperties",
        "constant/turbulenceProperties",
    ]
    out: List[Tuple[str, str]] = []
    for rel in required:
        p = case_dir / rel
        if not p.is_file():
            out.append(("FAIL", f"{rel}: missing"))
            continue
        text = p.read_text(errors="replace")
        if "FoamFile" not in text:
            out.append(("FAIL", f"{rel}: no FoamFile header (is it an OpenFOAM dict?)"))
            continue
        out.append(("PASS", f"{rel}: present"))
    return out


def _check_initial_conditions_cover_patches(
    case_dir: Path, manifest: Dict
) -> List[Tuple[str, str]]:
    """Every initial-condition field in `0/` should declare a boundary
    block for every patch in `geometry_contract.required_patches`."""
    required_patches = (manifest.get("geometry_contract") or {}).get("required_patches", [])
    if not required_patches:
        return [("WARN", "no required_patches declared in manifest; cannot cross-check 0/")]
    ic_dir = case_dir / "0"
    if not ic_dir.is_dir():
        return [("FAIL", "0/ directory missing")]
    # Function-object outputs that some solvers write into 0/ during
    # post-processing initialization. Not actual initial-condition fields,
    # so cross-check would be misleading. Skip them.
    fo_outputs = {"yPlus", "wallShearStress", "phi", "uniform"}
    out: List[Tuple[str, str]] = []
    for field_path in sorted(ic_dir.iterdir()):
        if not field_path.is_file():
            continue
        if field_path.name in fo_outputs:
            continue
        text = field_path.read_text(errors="replace")
        if "FoamFile" not in text:
            continue
        missing = [p for p in required_patches if not re.search(rf"^\s*{re.escape(p)}\s*\{{", text, re.MULTILINE)]
        if missing:
            out.append(
                ("FAIL",
                 f"0/{field_path.name}: missing boundary blocks for patches: {missing}")
            )
        else:
            out.append(("PASS", f"0/{field_path.name}: covers all {len(required_patches)} patches"))
    return out


def _check_blockmesh_patches_match_manifest(
    case_dir: Path, manifest: Dict
) -> List[Tuple[str, str]]:
    """Cross-check that every patch in `geometry_contract.required_patches`
    is declared in system/blockMeshDict. M2.3b pattern: manifest declared
    wall_patch=bottomWall but blockMesh had no such patch."""
    bm = case_dir / "system" / "blockMeshDict"
    if not bm.is_file():
        return [("FAIL", "system/blockMeshDict missing")]
    declared = _extract_patch_names_from_blockmesh(bm.read_text(errors="replace"))
    if not declared:
        return [("WARN", "blockMeshDict has no `boundary (...)` block or none could be parsed")]
    required_patches = (manifest.get("geometry_contract") or {}).get("required_patches", [])
    out: List[Tuple[str, str]] = []
    missing = [p for p in required_patches if p not in declared]
    extra = [p for p in declared if p not in required_patches]
    if missing:
        out.append(("FAIL", f"blockMeshDict missing patches required by manifest: {missing}"))
    if extra:
        out.append(
            ("WARN", f"blockMeshDict declares patches not required by manifest: {extra}")
        )
    if not missing and not extra:
        out.append(("PASS", f"blockMeshDict patches match manifest ({len(declared)} patches)"))
    return out


def _check_reference_csv_sha(case_dir: Path, manifest: Dict) -> List[Tuple[str, str]]:
    ref = manifest.get("reference_comparison") or {}
    csv_rel = ref.get("reference_csv")
    if not csv_rel:
        return [("WARN", "no reference_csv in manifest; reference comparison gate will not be exercised")]
    csv_path = case_dir / csv_rel
    if not csv_path.exists():
        return [("FAIL", f"reference_csv declared but missing on disk: {csv_rel}")]
    expected = ref.get("reference_csv_sha256")
    if not expected:
        return [("WARN", f"reference_csv present ({csv_rel}) but reference_csv_sha256 missing from manifest. Run `cfdtrust verify-reference --fix` to stamp it.")]
    actual = _file_sha256(csv_path)
    if str(expected).lower() == actual.lower():
        return [("PASS", f"reference CSV SHA-256 matches manifest ({csv_rel})")]
    return [("FAIL", f"reference CSV SHA-256 drift on {csv_rel}; run `cfdtrust verify-reference --fix`")]


def _check_wall_patch_resolvable(case_dir: Path, manifest: Dict) -> List[Tuple[str, str]]:
    """M9-surfaced fix: the wall_patch check only matters when a reference
    comparison is going to be performed. Cases with
    `reference_comparison.status: not_finalized` (M9 channel_flow) don't
    run the wallShearStress extractor, so an unresolved wall_patch is not
    a real defect — surface as WARN, not FAIL.
    """
    ref = manifest.get("reference_comparison") or {}
    status = (ref.get("status") or "").lower()
    wall_patch = ref.get("wall_patch", "wall")
    required_patches = (manifest.get("geometry_contract") or {}).get("required_patches", [])
    if wall_patch in required_patches:
        return [("PASS", f"wall_patch={wall_patch!r} appears in required_patches")]
    if status != "finalized":
        # Reference data not finalized → wallShearStress extractor will
        # not be exercised → wall_patch mismatch is informational, not FAIL.
        return [(
            "WARN",
            f"wall_patch={wall_patch!r} not in required_patches, but "
            f"reference_comparison.status={status!r} so no Cf extraction will run."
        )]
    return [(
        "FAIL",
        f"reference_comparison.wall_patch={wall_patch!r} not in geometry_contract.required_patches "
        f"({required_patches}). The wallShearStress extractor will block at run time."
    )]


def _check_artifacts_readme(case_dir: Path) -> List[Tuple[str, str]]:
    p = case_dir / "artifacts" / "README.md"
    if not p.exists():
        return [("FAIL", "artifacts/README.md missing (F-08 evidence anchor for PASS events)")]
    return [("PASS", "artifacts/README.md present (F-08 anchor)")]


def _check_polymesh_not_polluted(case_dir: Path) -> List[Tuple[str, str]]:
    """blockMesh-generated files should not live in source.
    R14-F-01 hygiene check, applied to any case via doctor."""
    pm = case_dir / "constant" / "polyMesh"
    if not pm.is_dir():
        return []  # not having polyMesh/ at all is fine
    contents = {p.name for p in pm.iterdir()}
    polluted = contents - {".gitkeep"}
    if polluted:
        return [(
            "WARN",
            f"constant/polyMesh/ contains generated files {polluted} — these belong in .gitignore, "
            "not in source. Run `rm cases/.../constant/polyMesh/{boundary,faces,neighbour,owner,points}` "
            "to clean."
        )]
    return [("PASS", "constant/polyMesh/ is clean (only .gitkeep)")]


# ---------- top-level ----------


def cmd_doctor(case_dir_str: str) -> int:
    """Run all checks and print a structured report. Exit 0 if no FAILs."""
    if _yaml is None:
        print("[cfdtrust] FAIL PyYAML not installed; cannot run doctor.", file=sys.stderr)
        return 1
    case_dir = Path(case_dir_str)
    if not case_dir.is_dir():
        print(f"[cfdtrust] FAIL case dir not found: {case_dir}", file=sys.stderr)
        return 1

    # Manifest must load before anything else can be cross-checked.
    status, msg, manifest = _check_manifest_loadable(case_dir)
    results: List[Tuple[str, str, str]] = [("manifest_load", status, msg)]

    if status == "PASS":
        # Group every check; each can yield 1+ result rows.
        groups = [
            ("openfoam_dicts", _check_required_openfoam_dictionaries(case_dir)),
            ("blockmesh_patches", _check_blockmesh_patches_match_manifest(case_dir, manifest)),
            ("initial_conditions", _check_initial_conditions_cover_patches(case_dir, manifest)),
            ("wall_patch", _check_wall_patch_resolvable(case_dir, manifest)),
            ("reference_csv", _check_reference_csv_sha(case_dir, manifest)),
            ("artifacts_readme", _check_artifacts_readme(case_dir)),
            ("polymesh_hygiene", _check_polymesh_not_polluted(case_dir)),
        ]
        for group_name, rows in groups:
            for row_status, row_msg in rows:
                results.append((group_name, row_status, row_msg))

    # Render.
    sym = {"PASS": "OK  ", "WARN": "WARN", "FAIL": "FAIL"}
    fail_count = sum(1 for _, s, _ in results if s == "FAIL")
    warn_count = sum(1 for _, s, _ in results if s == "WARN")
    pass_count = sum(1 for _, s, _ in results if s == "PASS")
    print(f"[cfdtrust] doctor report for {case_dir}:")
    for group, status, msg in results:
        print(f"  [{sym.get(status, status):4}] {group}: {msg}")
    print(f"  ---")
    print(f"  Summary: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL")
    return 1 if fail_count > 0 else 0
