#!/usr/bin/env python3
"""Generate ``.importlinter`` from the ``src._plane_assignment`` SSOT.

Usage:

    python scripts/gen_importlinter.py            # regenerate .importlinter
    python scripts/gen_importlinter.py --check    # fail (exit 1) on drift

This script closes ADR-001 AC-A7 (hand-enumerated source/forbidden
lists) and implements ADR-002 §2.2 byte-identical CI check. Both
layers of plane enforcement (static import-linter + future runtime
``sys.meta_path`` guard) consume the same ``PLANE_OF`` table, so
drift between the two is structurally impossible once the
``--check`` step is wired into CI.

Invocation path in CI: runs under ``backend-tests`` before
``lint-imports`` — if this check fails, ``lint-imports`` has stale
input and would produce misleading diagnostics, so hold the line
earlier.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IMPORTLINTER_PATH = REPO_ROOT / ".importlinter"

# Make the SSOT importable whether the script is run via
# ``python scripts/gen_importlinter.py`` (cwd in scripts/) or via
# ``python -m scripts.gen_importlinter`` from the repo root. The
# SSOT module imports only stdlib (ADR-002 §4.1 A12 bootstrap-purity);
# the script itself is outside ``src/`` and not bound by that constraint.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src._plane_assignment import PLANE_OF, Plane, modules_in  # noqa: E402


def _fmt_module_list(modules: tuple[str, ...]) -> str:
    """Render a list of modules as indented lines for import-linter config."""
    return "\n".join(f"    {m}" for m in modules)


def _render_contract(
    *,
    heading_number: int,
    heading_label: str,
    contract_id: str,
    name: str,
    source_modules: tuple[str, ...],
    forbidden_modules: tuple[str, ...],
) -> str:
    """Render a single ``forbidden`` contract section."""
    return (
        f"# ===== Contract {heading_number}: {heading_label} =====\n"
        f"[importlinter:contract:{contract_id}]\n"
        f"name = {name}\n"
        f"type = forbidden\n"
        f"source_modules =\n"
        f"{_fmt_module_list(source_modules)}\n"
        f"forbidden_modules =\n"
        f"{_fmt_module_list(forbidden_modules)}\n"
    )


HEADER = """\
# import-linter contract for cfd-harness-unified four-plane architecture.
# Authority: ADR-001 (docs/adr/ADR-001-four-plane-import-enforcement.md)
# SSOT:      SYSTEM_ARCHITECTURE v1.0 §2
#
# Scope: src.* only. ui.backend / scripts / tests are out of contract scope
# for v1.0 (per ADR-001 §3.2).
#
# To run locally:
#   pip install -e ".[dev]"   # picks up import-linter
#   lint-imports
#
# Contract types used: forbidden (bidirectional Execution ⇄ Evaluation).
# `layers` contract is not enforced top-down because Control already reads
# all planes by design; we only forbid the two HARD NOs and Knowledge
# reverse-import.
#
# This file is GENERATED from src/_plane_assignment.py via
# scripts/gen_importlinter.py. Do not hand-edit; update PLANE_OF and
# re-run the generator instead. CI enforces byte-identical parity
# (ADR-002 §2.2).

[importlinter]
root_package = src
include_external_packages = False
"""


def render_importlinter() -> str:
    """Produce the full ``.importlinter`` file content from ``PLANE_OF``.

    The output format is byte-identical with the hand-written reference
    file that preceded this generator (plus the new contract 5 for
    bootstrap-purity, which is the only semantic addition). Any future
    change to layout or ordering MUST update this function and the
    reference ``.importlinter`` in the same commit.
    """

    control = modules_in(Plane.CONTROL)
    execution = modules_in(Plane.EXECUTION)
    evaluation = modules_in(Plane.EVALUATION)
    knowledge = modules_in(Plane.KNOWLEDGE)
    shared = modules_in(Plane.SHARED)
    bootstrap = modules_in(Plane.BOOTSTRAP)

    # Contract 3 forbids Control + Execution + Evaluation from being
    # imported by Knowledge. Shared (models) is allowed per ADR-001 §2.2.
    knowledge_forbidden = control + execution + evaluation

    # Contract 4 forbids every non-shared src.* module from models.
    models_forbidden = control + execution + evaluation + knowledge

    # Contract 5 (bootstrap-purity, ADR-002 §4.1 A12) forbids the
    # bootstrap module from importing any other src.* module. Bootstrap
    # planes ship stdlib-only code that supports the runtime guard
    # itself; any src.* import here would chain-load through the guard
    # and self-recurse.
    bootstrap_forbidden = control + execution + evaluation + knowledge + shared

    contracts = [
        _render_contract(
            heading_number=1,
            heading_label="Execution must not import Evaluation",
            contract_id="execution-never-imports-evaluation",
            name="Execution Plane may not import Evaluation Plane (HARD NO per SYSTEM_ARCHITECTURE §2)",
            source_modules=execution,
            forbidden_modules=evaluation,
        ),
        _render_contract(
            heading_number=2,
            heading_label="Evaluation must not import Execution",
            contract_id="evaluation-never-imports-execution",
            name="Evaluation Plane may not import Execution Plane (HARD NO per SYSTEM_ARCHITECTURE §2)",
            source_modules=evaluation,
            forbidden_modules=execution,
        ),
        _render_contract(
            heading_number=3,
            heading_label="Knowledge stays downstream (no reverse imports)",
            contract_id="knowledge-no-reverse-import",
            name="Knowledge Plane may not import Control/Execution/Evaluation",
            source_modules=knowledge,
            forbidden_modules=knowledge_forbidden,
        ),
        _render_contract(
            heading_number=4,
            heading_label="shared contracts stay dependency-free",
            contract_id="models-stays-pure",
            name="src.models must not depend on any other src module (type-only escape hatch)",
            source_modules=shared,
            forbidden_modules=models_forbidden,
        ),
        _render_contract(
            heading_number=5,
            heading_label="plane-guard bootstrap stays stdlib-only (ADR-002 §4.1 A12)",
            contract_id="plane-guard-bootstrap-purity",
            name="src._plane_assignment (+ future src._plane_guard) must not import any other src module to avoid meta_path finder self-recursion",
            source_modules=bootstrap,
            forbidden_modules=bootstrap_forbidden,
        ),
    ]

    # Each contract block is preceded by a blank line (matches the
    # reference file's byte layout).
    body = "\n".join(contracts)
    return f"{HEADER}\n{body}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare generated output with existing .importlinter; exit 1 on drift.",
    )
    parser.add_argument(
        "--path",
        default=str(IMPORTLINTER_PATH),
        help="Path to the .importlinter file (default: repo-root/.importlinter).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    path = Path(args.path)
    generated = render_importlinter()

    if args.check:
        if not path.exists():
            print(
                f"ERROR: {path} does not exist; cannot perform byte-identical check.",
                file=sys.stderr,
            )
            return 1
        on_disk = path.read_text(encoding="utf-8")
        if on_disk == generated:
            return 0
        print(
            f"ERROR: {path} has drifted from PLANE_OF in src/_plane_assignment.py.",
            file=sys.stderr,
        )
        print(
            f"Run: python {Path(__file__).relative_to(REPO_ROOT)} to regenerate.",
            file=sys.stderr,
        )
        diff = difflib.unified_diff(
            on_disk.splitlines(keepends=True),
            generated.splitlines(keepends=True),
            fromfile=str(path),
            tofile="<generated>",
        )
        sys.stderr.writelines(diff)
        return 1

    path.write_text(generated, encoding="utf-8")
    print(f"Wrote {path} ({len(generated)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
