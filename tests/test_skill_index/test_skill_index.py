from __future__ import annotations

from pathlib import Path

import yaml

from orchestrator.skill_loader import get_categories, get_skill, load_skills_by_type


def test_skill_index_parseable(repo_root: Path):
    data = yaml.safe_load((repo_root / "knowledge" / "skill_index.yaml").read_text(encoding="utf-8"))
    assert "by_category" in data
    assert "by_solver_type" in data
    assert "inventory" in data


def test_dual_view_is_consistent(repo_root: Path):
    data = yaml.safe_load((repo_root / "knowledge" / "skill_index.yaml").read_text(encoding="utf-8"))
    by_category = {
        (category, skill_id)
        for category, payload in data["by_category"].items()
        for skill_id in payload.get("skills", {})
    }
    by_type = {
        (skill["category"], skill["skill_id"])
        for payload in data["by_solver_type"].values()
        for skill in payload.get("skills", {}).values()
    }
    assert by_category == by_type


def test_inventory_covers_all_indexed_source_paths(repo_root: Path):
    data = yaml.safe_load((repo_root / "knowledge" / "skill_index.yaml").read_text(encoding="utf-8"))
    inventory = set(data["inventory"]["source_paths"])
    indexed = {
        skill["source_path"]
        for payload in data["by_solver_type"].values()
        for skill in payload.get("skills", {}).values()
    }
    assert inventory == indexed


def test_load_skills_by_type_filters_deterministically():
    prompt_skills = load_skills_by_type("prompt")
    harness_skills = load_skills_by_type("harness")
    assert prompt_skills
    assert harness_skills
    assert all(skill["type"] == "prompt" for skill in prompt_skills)
    assert all(skill["type"] == "harness" for skill in harness_skills)
    assert prompt_skills == load_skills_by_type("prompt")


def test_load_skills_by_category_and_lookup():
    categories = get_categories()
    assert "cfd_harness" in categories
    cfd_skills = load_skills_by_type(category="cfd_harness")
    assert any(skill["skill_id"] == "openfoam_harness" for skill in cfd_skills)
    skill = get_skill("openfoam_harness", "cfd_harness")
    assert skill is not None
    assert skill["type"] == "harness"


def test_unknown_category_returns_empty():
    assert load_skills_by_type(category="missing-category") == []


def test_existing_skill_files_remain_untouched(repo_root: Path):
    assert not (repo_root / "knowledge" / "skills").exists()
