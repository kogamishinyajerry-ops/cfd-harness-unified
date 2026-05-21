"""Shared utility for parsing `.claude/agents/*.md` frontmatter.

Single source of truth for the project's set of known agent identities. Used by:

  - tools/cwos_event.py             (F-07: --agent allowlist at write time)
  - tools/cwos_render_dashboard.py  (Agent Matrix derivation)
  - tests/test_red_team_safety.py   (agent-set integrity)

Centralizing this avoids the round-3 lesson: two places re-implementing the
same parse drifted apart.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> Dict[str, Any]:
    """
    Return a dict of frontmatter key→value, or {} on missing/malformed input.
    Uses yaml.safe_load so multi-line block scalars and quoted strings are
    handled correctly (Red Team T1-F-02).
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _safe_md_files(agents_dir: Path) -> List[Path]:
    """Return the real, non-symlinked `*.md` files under `agents_dir`, sorted.

    Single chokepoint for the symlink-class safety guards. ANY caller that
    needs to enumerate agent files MUST go through here so a new safety
    predicate only ever needs to land in one place (round-4 pattern-break
    principle applied to agent enumeration).

    Guards:
      - missing dir → []
      - `agents_dir` itself is a symlink (R7-F-01) → []
      - individual `.md` is a symlink (R8-F-01) → skipped silently
    """
    if not agents_dir.exists():
        return []
    if agents_dir.is_symlink():
        return []
    out: List[Path] = []
    for p in sorted(agents_dir.glob("*.md")):
        if p.is_symlink():
            continue
        out.append(p)
    return out


def known_agent_names(agents_dir: Path) -> Set[str]:
    """
    Return the set of agent `name:` values declared in `<agents_dir>/*.md`.

    An agent file whose frontmatter is missing or whose `name:` is empty is
    silently skipped — the file is not yet a valid agent declaration.

    Symlink safety (R7-F-01 + R8-F-01) handled by `_safe_md_files`. The
    caller (cwos_event.py R6-F-01 guard) BLOCKs on an empty allowlist, so
    a dir-symlink or all-files-symlinked layout collapses to the same
    hard-error path.

    Legitimate symlink use (e.g. shared monorepo agent registry) is not
    expected in Phase 0; if it ever arrives, an explicit opt-in env-var
    (`CWOS_AGENTS_DIR_ALLOW_SYMLINK=1`) is the right escape hatch.
    """
    return {entry["name"] for entry in declared_agents(agents_dir)}


def declared_agents(agents_dir: Path) -> List[Dict[str, Any]]:
    """
    Canonical source-of-truth for agent metadata. Returns
    `[{name, description, path}]` for every valid agent file.

    Used by:
      - `cwos_event.py`              (via `known_agent_names` — F-07 allowlist)
      - `cwos_render_dashboard.py`   (Agent Matrix rows in cockpit)

    Round-8 R8-F-02 fix: previously the cockpit re-implemented this
    enumeration independently and missed the symlink guards. Centralizing
    here means any future safety predicate (e.g. "agent file must be
    tracked in git") only needs to land in `_safe_md_files`.

    Behavior:
      - frontmatter missing or no `name:` field → entry skipped
      - description missing → "(no description in frontmatter)"
      - non-string description (YAML may return list/int) → coerced via str()
    """
    out: List[Dict[str, Any]] = []
    for p in _safe_md_files(agents_dir):
        fm = parse_frontmatter(p.read_text())
        name = fm.get("name")
        if not (isinstance(name, str) and name.strip()):
            continue
        desc = fm.get("description")
        if desc is None:
            desc = "(no description in frontmatter)"
        elif not isinstance(desc, str):
            desc = str(desc)
        out.append({"name": name.strip(), "description": desc, "path": p})
    return out
