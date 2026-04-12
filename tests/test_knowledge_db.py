"""tests/test_knowledge_db.py — KnowledgeDB 单元测试"""

import pytest
from pathlib import Path
import yaml

from src.knowledge_db import KnowledgeDB
from src.models import (
    CorrectionSpec, ErrorType, ImpactScope,
    Compressibility, FlowType, GeometryType, SteadyState,
)


@pytest.fixture
def tmp_knowledge_dir(tmp_path):
    """创建临时知识库目录，包含最小 whitelist.yaml"""
    wl = {
        "cases": [
            {
                "id": "lid_driven_cavity",
                "name": "Lid-Driven Cavity",
                "reference": "Ghia 1982",
                "flow_type": "INTERNAL",
                "geometry_type": "SIMPLE_GRID",
                "compressibility": "INCOMPRESSIBLE",
                "steady_state": "STEADY",
                "parameters": {"Re": 100},
                "gold_standard": {
                    "quantity": "u_centerline",
                    "reference_values": [{"y": 0.5, "u": 0.025}],
                    "tolerance": 0.05,
                },
            },
            {
                "id": "circular_cylinder",
                "name": "Circular Cylinder Wake",
                "flow_type": "EXTERNAL",
                "geometry_type": "BODY_IN_CHANNEL",
                "compressibility": "INCOMPRESSIBLE",
                "steady_state": "TRANSIENT",
                "parameters": {"Re": 100},
                "gold_standard": {
                    "quantity": "strouhal_number",
                    "reference_values": [{"value": 0.165}],
                    "tolerance": 0.05,
                },
            },
        ]
    }
    wl_path = tmp_path / "whitelist.yaml"
    wl_path.write_text(yaml.dump(wl, allow_unicode=True))
    (tmp_path / "corrections").mkdir()
    return tmp_path


@pytest.fixture
def db(tmp_knowledge_dir):
    return KnowledgeDB(knowledge_dir=tmp_knowledge_dir)


def make_correction(**kwargs):
    defaults = dict(
        error_type=ErrorType.QUANTITY_DEVIATION,
        wrong_output={"u": 0.5},
        correct_output={"u": 0.025},
        human_reason="test",
        evidence="test evidence",
        impact_scope=ImpactScope.LOCAL,
        root_cause="mesh",
        fix_action="refine mesh",
        task_spec_name="Lid-Driven Cavity",
    )
    defaults.update(kwargs)
    return CorrectionSpec(**defaults)


class TestLoadGoldStandard:
    def test_by_name(self, db):
        gold = db.load_gold_standard("Lid-Driven Cavity")
        assert gold is not None
        assert gold["quantity"] == "u_centerline"

    def test_by_id(self, db):
        gold = db.load_gold_standard("lid_driven_cavity")
        assert gold is not None

    def test_not_found(self, db):
        gold = db.load_gold_standard("nonexistent")
        assert gold is None


class TestListWhitelistCases:
    def test_returns_two_cases(self, db):
        cases = db.list_whitelist_cases()
        assert len(cases) == 2

    def test_first_case_fields(self, db):
        cases = db.list_whitelist_cases()
        lid = cases[0]
        assert lid.name == "Lid-Driven Cavity"
        assert lid.Re == 100
        assert lid.flow_type == FlowType.INTERNAL

    def test_second_case_external(self, db):
        cases = db.list_whitelist_cases()
        assert cases[1].flow_type == FlowType.EXTERNAL


class TestSaveAndLoadCorrection:
    def test_save_creates_file(self, db):
        correction = make_correction()
        path = db.save_correction(correction)
        assert path.exists()
        assert path.suffix == ".yaml"

    def test_load_round_trip(self, db):
        correction = make_correction()
        db.save_correction(correction)
        loaded = db.load_corrections()
        assert len(loaded) == 1
        assert loaded[0].error_type == ErrorType.QUANTITY_DEVIATION
        assert loaded[0].task_spec_name == "Lid-Driven Cavity"

    def test_load_filter_by_name(self, db):
        db.save_correction(make_correction(task_spec_name="A"))
        db.save_correction(make_correction(task_spec_name="B"))
        result = db.load_corrections(task_name="A")
        assert len(result) == 1
        assert result[0].task_spec_name == "A"

    def test_multiple_corrections(self, db):
        for _ in range(3):
            db.save_correction(make_correction())
        loaded = db.load_corrections()
        assert len(loaded) == 3


class TestMissingWhitelist:
    def test_returns_empty_when_missing(self, tmp_path):
        (tmp_path / "corrections").mkdir()
        db = KnowledgeDB(knowledge_dir=tmp_path)
        assert db.list_whitelist_cases() == []
        assert db.load_gold_standard("anything") is None
