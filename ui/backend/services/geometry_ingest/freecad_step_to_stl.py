"""STEP → per-body ASCII STL via FreeCAD subprocess (V198 4a bridge).

Wraps ``freecadcmd`` to import a STEP file, mesh each named leaf solid via
``MeshPart.meshFromShape``, and emit one ASCII STL per body. Body labels are
preserved (via A1's ``Import.insert()``) and used as STL file names after
sanitization.

F-NEW-5 fix: workbench import routes accept STL only, so STEP cases
(case_003 onward) need a pre-route conversion step.

F-NEW-2 carry-over: positional args go through a sidecar file, not via
``freecadcmd`` argv (which auto-opens any non-script positional as a file
to open).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

DEFAULT_LIN_DEFLECTION = 0.05
DEFAULT_ANG_DEFLECTION = 0.1
DEFAULT_FREECAD_CMD = "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"

_SIDECAR_SCRIPT = Path(__file__).parent / "_freecad_step_to_stl_sidecar.py"
_SANITIZE_PATTERN = re.compile(r"[^a-z0-9]+")


class STEPToSTLBackendUnavailable(RuntimeError):
    """``freecadcmd`` binary not found at the supplied path."""


class STEPToSTLConversionFailed(RuntimeError):
    """``freecadcmd`` ran but did not produce the expected manifest."""


def sanitize_label(label: str) -> str:
    """Map a STEP body label to a filesystem-safe stem.

    Lowercase, alphanumeric + underscore. Empty result → ``body``. Collision
    suffixing (``_2``, ``_3``, ...) is sidecar-side; this is the stem only.
    """
    cleaned = _SANITIZE_PATTERN.sub("_", label.strip().lower()).strip("_")
    return cleaned or "body"


def step_to_per_body_stl(
    step_path: Path | str,
    out_dir: Path | str,
    lin_deflection: float = DEFAULT_LIN_DEFLECTION,
    ang_deflection: float = DEFAULT_ANG_DEFLECTION,
    freecad_cmd: str = DEFAULT_FREECAD_CMD,
) -> list[Path]:
    """Convert STEP to one ASCII STL per named leaf solid.

    Returns the list of produced STL paths in document order.

    Raises
    ------
    STEPToSTLBackendUnavailable
        ``freecad_cmd`` binary missing.
    STEPToSTLConversionFailed
        Subprocess completed but no manifest is found at ``out_dir``.
    """
    step_path = Path(step_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not Path(freecad_cmd).exists():
        raise STEPToSTLBackendUnavailable(
            f"freecadcmd not at {freecad_cmd}. Pass freecad_cmd= to override."
        )

    args_file = out_dir / "_step_to_stl_args.txt"
    args_file.write_text(
        f"{step_path}\n{out_dir}\n{lin_deflection}\n{ang_deflection}\n"
    )
    manifest_path = out_dir / "manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()

    env = {**os.environ, "STEP_TO_STL_ARGS": str(args_file)}
    result = subprocess.run(
        [freecad_cmd, str(_SIDECAR_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
    )
    if not manifest_path.exists():
        raise STEPToSTLConversionFailed(
            f"freecadcmd produced no manifest. exit={result.returncode}; "
            f"stderr tail: {result.stderr[-500:]}"
        )
    manifest = json.loads(manifest_path.read_text())
    return [Path(entry["path"]) for entry in manifest["bodies"]]
