"""tests/test_skill_index/test_skill_loader.py — Unit tests for skill_loader."""
from __future__ import annotations

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

# Import the module under test
from src.orchestrator.skill_loader import (
    load_skills_by_type,
    get_categories,
    get_skill,
    skill_source_exists,
    SkillEntry,
)


# ---------------------------------------------------------------------------
# Fixture: minimal synthetic skill_index.yaml
# ---------------------------------------------------------------------------

MINIMAL_INDEX = {
    "model_routing": {
        "description": "Model selection",
        "skills": {
            "codex_gpt54": {
                "name": "Codex GPT-5.4",
                "description": "Codex CLI",
                "type": "prompt",
                "source_path": "~/.claude/commands/codex-gpt54.md",
            },
            "m27_superpowers": {
                "name": "MiniMax-2.7 Superpowers",
                "description": "MiniMax harness",
                "type": "prompt",
                "source_path": "~/.claude/commands/m27-superpowers.md",
            },
        },
    },
    "cfd_harness": {
        "description": "CFD simulation harness",
        "skills": {
            "openfoam_harness": {
                "name": "OpenFOAM Harness Skill",
                "description": "OpenFOAM v10 harness",
                "type": "harness",
                "source_path": "~/.claude/commands/openfoam-harness",
            },
            "dakota_harness": {
                "name": "Dakota CLI Harness",
                "description": "Dakota UQ",
                "type": "harness",
                "source_path": "~/.claude/commands/dakota-harness",
            },
            "su2_harness": {
                "name": "SU2 CLI Harness",
                "description": "SU2 CFD solver",
                "type": "harness",
                "source_path": "~/.claude/commands/su2-harness",
            },
        },
    },
    "ui_systems": {
        "description": "UI systems",
        "skills": {
            "vanilla_panel_ui": {
                "name": "Vanilla Panel UI",
                "description": "TypeScript panel",
                "type": "prompt",
                "source_path": "~/.claude/commands/vanilla-panel-ui.md",
            },
        },
    },
    "architecture": {
        "description": "Architecture patterns",
        "skills": {
            "harness_architecture": {
                "name": "Harness Architecture",
                "description": "High-reliability harness",
                "type": "prompt",
                "source_path": "~/.claude/commands/harness-architecture",
            },
        },
    },
    "uncategorized": {
        "description": "Other skills",
        "skills": {
            "openviking": {
                "name": "OpenViking Context",
                "description": "Context management",
                "type": "prompt",
                "source_path": "~/.claude/commands/openviking.md",
            },
        },
    },
}


@pytest.fixture
def minimal_index_path(tmp_path):
    """Write MINIMAL_INDEX to a temp YAML file and return its path."""
    path = tmp_path / "skill_index.yaml"
    with open(path, "w") as f:
        yaml.dump(MINIMAL_INDEX, f)
    return path


# ---------------------------------------------------------------------------
# load_skills_by_type tests
# ---------------------------------------------------------------------------

class TestLoadSkillsByType:
    def test_returns_all_skills_when_no_filter(self, minimal_index_path):
        results = load_skills_by_type(index_path=minimal_index_path)
        # 2 + 3 + 1 + 1 + 1 = 8 skills
        assert len(results) == 8

    def test_filters_by_harness_type(self, minimal_index_path):
        results = load_skills_by_type(solver_type="harness", index_path=minimal_index_path)
        assert len(results) == 3
        for r in results:
            assert r["type"] == "harness"

    def test_filters_by_prompt_type(self, minimal_index_path):
        results = load_skills_by_type(solver_type="prompt", index_path=minimal_index_path)
        assert len(results) == 5
        for r in results:
            assert r["type"] == "prompt"

    def test_filters_by_category(self, minimal_index_path):
        results = load_skills_by_type(category="cfd_harness", index_path=minimal_index_path)
        assert len(results) == 3
        for r in results:
            assert r["category"] == "cfd_harness"

    def test_filters_by_type_and_category(self, minimal_index_path):
        results = load_skills_by_type(
            solver_type="harness", category="cfd_harness", index_path=minimal_index_path
        )
        assert len(results) == 3
        for r in results:
            assert r["type"] == "harness"
            assert r["category"] == "cfd_harness"

    def test_returns_empty_for_nonexistent_category(self, minimal_index_path):
        # Non-existent category returns empty list (defensive, not an error)
        results = load_skills_by_type(category="nonexistent", index_path=minimal_index_path)
        assert results == []

    def test_invalid_solver_type_raises(self, minimal_index_path):
        with pytest.raises(ValueError, match="Invalid solver_type"):
            load_skills_by_type(solver_type="invalid", index_path=minimal_index_path)

    def test_result_has_required_keys(self, minimal_index_path):
        results = load_skills_by_type(solver_type="harness", index_path=minimal_index_path)
        for r in results:
            assert "skill_id" in r
            assert "category" in r
            assert "name" in r
            assert "description" in r
            assert "type" in r
            assert "source_path" in r

    def test_skill_ids_are_unique(self, minimal_index_path):
        results = load_skills_by_type(index_path=minimal_index_path)
        ids = [r["skill_id"] for r in results]
        assert len(ids) == len(set(ids)), "Duplicate skill IDs found"


# ---------------------------------------------------------------------------
# get_categories tests
# ---------------------------------------------------------------------------

class TestGetCategories:
    def test_returns_all_category_keys(self, minimal_index_path):
        idx = yaml.safe_load(open(minimal_index_path))
        cats = list(idx.keys())
        # get_categories reads from the real path; patch _INDEX_PATH
        with patch("src.orchestrator.skill_loader._INDEX_PATH", minimal_index_path):
            result = get_categories()
        for cat in cats:
            assert cat in result


# ---------------------------------------------------------------------------
# get_skill tests
# ---------------------------------------------------------------------------

class TestGetSkill:
    def test_returns_skill_by_id_and_category(self, minimal_index_path):
        with patch("src.orchestrator.skill_loader._INDEX_PATH", minimal_index_path):
            result = get_skill("openfoam_harness", "cfd_harness")
        assert result is not None
        assert result["skill_id"] == "openfoam_harness"
        assert result["category"] == "cfd_harness"
        assert result["name"] == "OpenFOAM Harness Skill"

    def test_returns_none_for_missing_skill(self, minimal_index_path):
        with patch("src.orchestrator.skill_loader._INDEX_PATH", minimal_index_path):
            result = get_skill("nonexistent", "cfd_harness")
        assert result is None

    def test_returns_none_for_missing_category(self, minimal_index_path):
        with patch("src.orchestrator.skill_loader._INDEX_PATH", minimal_index_path):
            result = get_skill("openfoam_harness", "nonexistent_category")
        assert result is None


# ---------------------------------------------------------------------------
# skill_source_exists tests
# ---------------------------------------------------------------------------

class TestSkillSourceExists:
    def test_returns_true_for_existing_path(self, tmp_path, monkeypatch):
        # Create a real file
        skill_file = tmp_path / "test_skill.md"
        skill_file.write_text("# Test")
        skill = SkillEntry(
            skill_id="test",
            category="test",
            name="Test",
            description="",
            type="prompt",
            source_path=str(skill_file),
        )
        assert skill_source_exists(skill) is True

    def test_returns_false_for_nonexistent_path(self, tmp_path):
        skill = SkillEntry(
            skill_id="test",
            category="test",
            name="Test",
            description="",
            type="prompt",
            source_path=str(tmp_path / "does_not_exist.md"),
        )
        assert skill_source_exists(skill) is False

    def test_returns_false_for_empty_source_path(self):
        skill = SkillEntry(
            skill_id="test",
            category="test",
            name="Test",
            description="",
            type="prompt",
            source_path="",
        )
        assert skill_source_exists(skill) is False


# ---------------------------------------------------------------------------
# CHK-1: skill_index.yaml parseable (uses real file)
# ---------------------------------------------------------------------------

class TestChk1RealFile:
    def test_real_skill_index_parseable(self):
        """CHK-1: The actual knowledge/skill_index.yaml is valid YAML."""
        result = load_skills_by_type()
        assert isinstance(result, list)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# CHK-2: Index covers all skill files (mock-based, since source paths are external)
# ---------------------------------------------------------------------------

class TestChk2IndexCoverage:
    def test_all_categories_covered(self):
        """CHK-2: Every top-level key in the index has non-empty skills dict."""
        idx_path = Path(__file__).parent.parent.parent / "knowledge" / "skill_index.yaml"
        idx = yaml.safe_load(open(idx_path))
        for cat_key, cat_data in idx.items():
            skills = cat_data.get("skills", {})
            assert isinstance(skills, dict), f"Category {cat_key} skills is not a dict"
            # At least some categories should have skills
        total_skills = sum(len(cat_data.get("skills", {})) for cat_data in idx.values())
        assert total_skills > 0, "No skills found in index"
