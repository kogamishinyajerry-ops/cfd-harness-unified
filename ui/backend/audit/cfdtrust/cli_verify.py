"""`cfdtrust verify-reference` — keep manifest.reference_csv_sha256 honest.

R16-F-01 (sub-commit 2d) added runtime SHA-256 verification of the
in-repo reference CSV. The mechanism BLOCKS on drift, which is correct
but inconvenient when the user legitimately wants to update the
reference data (e.g. NASA TMR republishes the dataset). Pre-M3.2 the
fix was a manual `shasum` + manifest edit, error-prone enough that
some users would just unset the field instead.

This subcommand has two modes:

  - Check-only (default): compute the on-disk file's hash, compare it
    to the manifest, exit 0 / 1 accordingly. CI-friendly.
  - `--fix`: rewrite the manifest's hash to match the on-disk file.
    Prints a diff line. CI-friendly side-effect.

Honesty notes:
  - `--fix` is INTERACTIVE-LEVEL trust (i.e. the user is acknowledging
    they want to accept the new reference data). It is NOT a way to
    silence honest mismatches in CI; for that, `--check-only`-style
    failure should drive a code review.
  - We refuse to operate on case dirs whose manifest lacks
    `reference_comparison.reference_csv` — the harness has nothing to
    verify there.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Tuple

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover — PyYAML is a required dep
    _yaml = None


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_manifest(case_dir: Path) -> Tuple[dict, str]:
    mp = case_dir / "case_manifest.yaml"
    if not mp.exists():
        raise FileNotFoundError(f"case_manifest.yaml not found under {case_dir}")
    text = mp.read_text()
    return _yaml.safe_load(text) or {}, text


def _resolve_ref_csv(case_dir: Path, manifest: dict) -> Tuple[Path, str | None]:
    """Return (resolved_ref_csv_path, declared_sha_or_None) given a manifest.
    Raises ValueError on shape problems."""
    ref = manifest.get("reference_comparison") or {}
    rel = ref.get("reference_csv")
    declared = ref.get("reference_csv_sha256")
    if not rel:
        raise ValueError(
            "manifest.reference_comparison.reference_csv is missing; nothing to verify."
        )
    if Path(rel).is_absolute():
        raise ValueError(f"reference_csv must be a relative path, got {rel!r}")
    csv_path = case_dir / rel
    return csv_path, declared


def _rewrite_sha_in_manifest(text: str, new_sha: str) -> str | None:
    """Best-effort in-place rewrite of the manifest's reference_csv_sha256.
    Returns the new text on success, None if the field could not be
    located (in which case the caller falls back to --check-only and
    explains the situation to the user).
    """
    # Match a line like "  reference_csv_sha256: <hex>" with optional comment.
    # We use a moderately strict pattern so we don't accidentally rewrite
    # source_sha256 or some other look-alike field.
    pattern = re.compile(
        r"^(?P<indent>\s*)reference_csv_sha256:\s*[a-fA-F0-9]{0,64}(?P<trailing>.*)$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if m is None:
        return None
    new_line = f"{m.group('indent')}reference_csv_sha256: {new_sha}{m.group('trailing')}"
    return text[: m.start()] + new_line + text[m.end():]


def cmd_verify_reference(case_dir_str: str, *, fix: bool = False) -> int:
    """Returns 0 on OK (or successful --fix), 1 on drift or any error."""
    if _yaml is None:
        print("[cfdtrust] FAIL PyYAML not installed; cannot read manifest.", file=sys.stderr)
        return 1
    case_dir = Path(case_dir_str)
    if not case_dir.is_dir():
        print(f"[cfdtrust] FAIL case dir not found: {case_dir}", file=sys.stderr)
        return 1
    try:
        manifest, manifest_text = _read_manifest(case_dir)
    except FileNotFoundError as e:
        print(f"[cfdtrust] FAIL {e}", file=sys.stderr)
        return 1
    try:
        csv_path, declared = _resolve_ref_csv(case_dir, manifest)
    except ValueError as e:
        print(f"[cfdtrust] FAIL {e}", file=sys.stderr)
        return 1

    if not csv_path.exists():
        print(f"[cfdtrust] FAIL reference CSV missing on disk: {csv_path}", file=sys.stderr)
        return 1

    actual = _file_sha256(csv_path)

    if declared is None or declared in ("", "null"):
        # No hash declared yet — `--fix` becomes "stamp it for the first time".
        if not fix:
            print(
                "[cfdtrust] WARN manifest.reference_comparison.reference_csv_sha256 is not set. "
                f"actual sha256 = {actual}. Re-run with --fix to stamp it into the manifest.",
                file=sys.stderr,
            )
            return 1
        new_text = _rewrite_sha_in_manifest(manifest_text, actual)
        if new_text is None:
            print(
                "[cfdtrust] FAIL cannot locate `reference_csv_sha256:` field in manifest; "
                "add the field manually then re-run --fix.",
                file=sys.stderr,
            )
            return 1
        (case_dir / "case_manifest.yaml").write_text(new_text)
        print(f"[cfdtrust] OK   stamped reference_csv_sha256 = {actual}")
        return 0

    declared = str(declared).lower()
    actual_low = actual.lower()

    if declared == actual_low:
        print(f"[cfdtrust] OK   reference_csv_sha256 matches on-disk file ({actual}).")
        return 0

    # Drift!
    if not fix:
        print(
            f"[cfdtrust] FAIL reference CSV hash drift:\n"
            f"             expected (manifest): {declared}\n"
            f"             actual   (on disk):  {actual}\n"
            f"           If the new data is intended, re-run with --fix to update the manifest.",
            file=sys.stderr,
        )
        return 1

    new_text = _rewrite_sha_in_manifest(manifest_text, actual)
    if new_text is None:
        print(
            "[cfdtrust] FAIL cannot locate `reference_csv_sha256:` line in manifest; "
            "edit the file manually.",
            file=sys.stderr,
        )
        return 1
    (case_dir / "case_manifest.yaml").write_text(new_text)
    print(
        f"[cfdtrust] OK   reference_csv_sha256 updated:\n"
        f"             old: {declared}\n"
        f"             new: {actual}"
    )
    return 0
