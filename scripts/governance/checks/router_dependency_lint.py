#!/usr/bin/env python3
"""V84.4 · Router-dependency lint for shared component classes.

Flags components that import Router hooks (useSearchParams/useNavigate/
useLocation/useParams) AND live in a "shared" location where they should
take Router-derived state as props instead.

Shared component locations (initial list, expandable):
  - ui/frontend/src/pages/workbench/v3/components/right-panel/**
  - ui/frontend/src/pages/workbench/v3/components/canvas/**
  - ui/frontend/src/components/**  (general shared widgets)

EXCLUDED (Router-aware by design):
  - Page components (named *Page.tsx)
  - WorkbenchShellV3 (top-level route shell)
  - DemoBannerV4 / DemoSandboxV5 / ProvenanceCardV5 (mounted ONLY inside
    WorkbenchShellV3, intentionally Router-aware)

Background: V83 caught AdvisorContent using useSearchParams directly,
which broke 7 router-less unit tests. Fix was to lift to a prop. This
script catches regressions of that class.

Exit code: 0 if clean, 1 if any shared component imports Router hooks.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROUTER_HOOK_PATTERN = re.compile(
    r"\b(useSearchParams|useNavigate|useLocation|useParams)\b"
)

EXCLUDE_NAMES = {
    "WorkbenchShellV3.tsx",
    "DemoBannerV4.tsx",
    "DemoSandboxV5.tsx",
    "ProvenanceCardV5.tsx",
}

SHARED_DIRS = [
    "pages/workbench/v3/components/right-panel",
    "pages/workbench/v3/components/canvas",
    "components",
]


def is_shared(path: Path, src_root: Path) -> bool:
    """A file is 'shared' if it's in one of SHARED_DIRS, NOT a Page
    component, NOT in EXCLUDE_NAMES."""
    if path.name in EXCLUDE_NAMES:
        return False
    if path.name.endswith("Page.tsx"):
        return False
    try:
        rel = path.relative_to(src_root)
    except ValueError:
        return False
    rel_str = str(rel.parent).replace("\\", "/")
    return any(rel_str.startswith(d) for d in SHARED_DIRS)


def main(args: list[str]) -> int:
    src = Path("ui/frontend/src")
    if not src.exists():
        src = Path("src")

    if args:
        paths = [Path(p) for p in args]
    else:
        paths = [
            p
            for p in src.rglob("*.tsx")
            if "__tests__" not in p.parts and ".test." not in p.name
        ]

    findings: list[tuple[Path, int, str]] = []
    for p in paths:
        if not is_shared(p, src):
            continue
        text = p.read_text()
        for i, line in enumerate(text.split("\n"), 1):
            m = ROUTER_HOOK_PATTERN.search(line)
            if m:
                findings.append((p, i, line.strip()))
                break  # one finding per file is enough

    if not findings:
        print(
            f"router_dependency_lint: OK · scanned {len(paths)} files · 0 shared-component Router-hook usages"
        )
        return 0
    else:
        for p, i, code in findings:
            print(f"ROUTER-IN-SHARED  {p}:{i}  {code[:120]}")
        print(
            f"router_dependency_lint: FAIL · {len(findings)} shared component(s) using Router hooks directly · lift to props"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
