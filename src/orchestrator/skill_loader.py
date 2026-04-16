"""Skill loader: dual-view index for skills by category and solver_type."""
from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, TypedDict


class SkillEntry(TypedDict, total=False):
    """A single skill entry from the index."""
    name: str
    description: str
    type: str  # "prompt" or "harness"
    source_path: str


# Canonical path to the skill index
_INDEX_PATH = Path(__file__).parent.parent.parent / "knowledge" / "skill_index.yaml"


def _resolve_path(source_path: str) -> Path:
    """Resolve ~ in source_path to home directory."""
    if source_path.startswith("~/"):
        return Path(os.path.expanduser("~")) / source_path[2:]
    return Path(source_path)


def _load_index() -> Dict:
    """Load and parse the skill index YAML."""
    if not _INDEX_PATH.exists():
        raise FileNotFoundError(
            f"skill_index.yaml not found at {_INDEX_PATH}. "
            "Run: python scripts/gen_skill_index.py"
        )
    with open(_INDEX_PATH) as f:
        return yaml.safe_load(f)


def load_skills_by_type(
    solver_type: Optional[str] = None,
    category: Optional[str] = None,
    index_path: Optional[Path] = None,
) -> List[SkillEntry]:
    """Load skills filtered by solver_type (prompt/harness) and/or category.

    Args:
        solver_type: Filter by skill type. Valid values: "prompt", "harness", None.
                     None returns all skills regardless of type.
        category: Filter by category key in skill_index.yaml.
                  Valid values: "model_routing", "cfd_harness", "ui_systems",
                                 "architecture", "uncategorized", None.
                  None returns skills from all categories.
        index_path: Optional override for testing.

    Returns:
        List of SkillEntry dicts matching the filters.

    Raises:
        FileNotFoundError: If skill_index.yaml does not exist.
        ValueError: If solver_type or category is not a recognized value.

    Example:
        >>> load_skills_by_type("harness")
        [{'name': 'OpenFOAM Harness', 'type': 'harness', ...}, ...]
        >>> load_skills_by_type(category="cfd_harness")
        [{'name': 'OpenFOAM Harness', 'type': 'harness', ...}, ...]
    """
    VALID_TYPES = {"prompt", "harness"}
    VALID_CATEGORIES = {
        "model_routing",
        "cfd_harness",
        "ui_systems",
        "architecture",
        "uncategorized",
    }

    if solver_type is not None and solver_type not in VALID_TYPES:
        raise ValueError(
            f"Invalid solver_type={solver_type!r}. "
            f"Expected one of: {sorted(VALID_TYPES)}"
        )
    # Unknown categories return empty list (not an error) for defensive handling
    if category is not None and category not in VALID_CATEGORIES:
        return []

    idx = _load_index() if index_path is None else yaml.safe_load(open(index_path))
    results: List[SkillEntry] = []

    categories_to_scan = (
        [category] if category is not None else list(idx.keys())
    )

    for cat_key in categories_to_scan:
        if cat_key not in idx:
            continue
        cat = idx[cat_key]
        skills = cat.get("skills", {})
        for skill_id, skill_def in skills.items():
            skill_type = skill_def.get("type")
            if solver_type is not None and skill_type != solver_type:
                continue
            results.append(
                SkillEntry(
                    skill_id=skill_id,
                    category=cat_key,
                    name=skill_def.get("name", ""),
                    description=skill_def.get("description", ""),
                    type=skill_type or "",
                    source_path=skill_def.get("source_path", ""),
                )
            )

    return results


def get_categories() -> List[str]:
    """Return all category keys in the skill index."""
    return list(_load_index().keys())


def get_skill(skill_id: str, category: str) -> Optional[SkillEntry]:
    """Get a single skill by its ID and category.

    Returns None if not found.
    """
    idx = _load_index()
    cat = idx.get(category, {})
    skills = cat.get("skills", {})
    skill_def = skills.get(skill_id)
    if skill_def is None:
        return None
    return SkillEntry(
        skill_id=skill_id,
        category=category,
        name=skill_def.get("name", ""),
        description=skill_def.get("description", ""),
        type=skill_def.get("type", ""),
        source_path=skill_def.get("source_path", ""),
    )


def skill_source_exists(skill: SkillEntry) -> bool:
    """Check if the skill's source_path resolves to an existing file."""
    source = skill.get("source_path", "")
    if not source:
        return False
    return _resolve_path(source).expanduser().exists()
