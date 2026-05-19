#!/usr/bin/env python3
"""V84.3 · Hooks-order lint · catch React hooks called AFTER a top-level
conditional return in component function bodies.

Background: V83 caught DemoBannerV4 with this exact bug (`useRef` placed
after `if (!mounted) return null`). The hook-order pattern is silent at
write-time and only surfaces when both branches of the conditional return
get exercised by tests.

Exit code: 0 if clean, 1 if any hook-after-return found at component scope.

Usage:
    python3 scripts/governance/checks/hooks_order_lint.py
    python3 scripts/governance/checks/hooks_order_lint.py ui/frontend/src/path/to/file.tsx
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HOOK_PATTERN = re.compile(
    r"^(?:const\s+)?\[?[^=]*\]?\s*=?\s*use(?:State|Ref|Effect|Memo|Callback|Reducer|LayoutEffect|ImperativeHandle)\b"
)
RETURN_PATTERN = re.compile(r"^(if\s*\([^)]+\)\s*)?return(\s|;|$)")
COMPONENT_PATTERN = re.compile(
    r"^(export\s+)?(?:function|const)\s+([A-Z][A-Za-z0-9]*)\s*[(:=]"
)


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, component_name, code) for every hook found
    AFTER a top-level early return inside the component body."""
    text = path.read_text()
    lines = text.split("\n")
    component_starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = COMPONENT_PATTERN.match(line)
        if m:
            component_starts.append((i, m.group(2)))

    findings: list[tuple[int, str, str]] = []
    for start, comp_name in component_starts:
        depth = 0
        in_body = False
        early_return_line: int | None = None
        for j in range(start, min(len(lines), start + 1500)):
            line = lines[j]
            for ch in line:
                if ch == "{":
                    depth += 1
                    if depth == 1:
                        in_body = True
                elif ch == "}":
                    depth -= 1
                    if depth == 0 and in_body:
                        break
            else:
                if not in_body or depth != 1:
                    continue
                stripped = line.strip()
                if RETURN_PATTERN.match(stripped):
                    if early_return_line is None:
                        early_return_line = j
                elif HOOK_PATTERN.match(stripped) and early_return_line is not None:
                    findings.append((j + 1, comp_name, stripped[:120]))
                continue
            # `for ch in line` broke out → component body ended.
            if depth == 0:
                break
    return findings


def main(args: list[str]) -> int:
    if args:
        paths = [Path(p) for p in args]
    else:
        # Default scan: ui/frontend/src/**/*.tsx excluding tests
        root = Path("ui/frontend/src")
        if not root.exists():
            root = Path("src")
        paths = [
            p
            for p in root.rglob("*.tsx")
            if "__tests__" not in p.parts and ".test." not in p.name
        ]

    total = 0
    for p in paths:
        findings = scan_file(p)
        for line_no, comp, code in findings:
            print(f"HOOK-AFTER-RETURN  {p}:{line_no}  [{comp}]  {code}")
            total += 1
    if total == 0:
        print(f"hooks_order_lint: OK · scanned {len(paths)} files · 0 findings")
        return 0
    else:
        print(f"hooks_order_lint: FAIL · {total} hook(s) after early return")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
