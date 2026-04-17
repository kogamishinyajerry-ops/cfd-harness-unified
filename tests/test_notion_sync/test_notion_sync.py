from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from notion_sync import (
    SUGGEST_ONLY_BANNER,
    NotionSync,
    OfficialNotionAdapter,
    SyncTargets,
    resolve_official_notion_client,
)


class FakeAdapter:
    def __init__(self) -> None:
        self.updated_pages = []
        self.created_pages = []

    def update_page(self, page_id: str, properties: dict) -> None:
        self.updated_pages.append((page_id, properties))

    def create_page(self, parent_data_source_id: str, properties: dict) -> None:
        self.created_pages.append((parent_data_source_id, properties))


@pytest.fixture
def targets() -> SyncTargets:
    return SyncTargets(
        phase_page_id="df0228eb22774e3ca32b98e022165277",
        auto_verifier_task_page_id="76597c7c257b4734896de2f79213812e",
        report_engine_task_page_id="aad7ed13c1c54716965160d49d70c72c",
        canonical_docs_data_source_id="8ea16a11-68e1-46cd-906b-4a18824a304b",
    )


def test_build_phase8_plan_contains_expected_actions(targets: SyncTargets):
    plan = NotionSync().build_phase8_plan(targets)
    assert len(plan.task_updates) == 2
    assert plan.phase_update.page_id == targets.phase_page_id
    assert len(plan.canonical_doc_creates) == 3


def test_task_and_doc_payloads_preserve_suggest_only_banner(targets: SyncTargets):
    plan = NotionSync().build_phase8_plan(targets)
    for update in plan.task_updates:
        text = update.properties["Next Step"]["rich_text"][0]["text"]["content"]
        assert SUGGEST_ONLY_BANNER in text
    for create_request in plan.canonical_doc_creates:
        text = create_request.properties["Summary"]["rich_text"][0]["text"]["content"]
        assert SUGGEST_ONLY_BANNER in text


def test_sync_plan_is_deterministic(targets: SyncTargets):
    left = NotionSync().build_phase8_plan(targets).stable_repr()
    right = NotionSync().build_phase8_plan(targets).stable_repr()
    assert left == right


def test_apply_phase8_plan_uses_adapter(targets: SyncTargets):
    adapter = FakeAdapter()
    sync = NotionSync(adapter=adapter)
    sync.apply_phase8_plan(targets)
    assert len(adapter.updated_pages) == 3
    assert len(adapter.created_pages) == 3


def test_notion_sync_uses_correct_client_binding(repo_root: Path):
    class ExternalClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def request(self, **kwargs):
            return kwargs

    module = SimpleNamespace(
        __file__="/tmp/site-packages/notion_client/__init__.py",
        Client=ExternalClient,
    )
    client_cls = resolve_official_notion_client(
        import_module=lambda _: module,
        project_root=repo_root,
    )
    adapter = OfficialNotionAdapter(token="fake-token", client_cls=client_cls)
    assert isinstance(adapter._client, ExternalClient)


def test_notion_sync_rejects_local_shadow_client_binding(repo_root: Path):
    module = SimpleNamespace(
        __file__=str(repo_root / "src" / "notion_client.py"),
        Client=object,
    )
    with pytest.raises(ImportError):
        resolve_official_notion_client(
            import_module=lambda _: module,
            project_root=repo_root,
        )


def test_canonical_doc_payloads_use_report_engine_binding(targets: SyncTargets):
    plan = NotionSync().build_phase8_plan(targets)
    for create_request in plan.canonical_doc_creates:
        relations = create_request.properties["Tasks"]["relation"]
        assert relations == [{"id": targets.report_engine_task_page_id}]


def test_missing_suggest_only_banner_raises(tmp_path: Path, targets: SyncTargets, repo_root: Path):
    reports_root = tmp_path / "reports"
    reports_root.mkdir()
    for case_id in (
        "lid_driven_cavity_benchmark",
        "backward_facing_step_steady",
        "cylinder_crossflow",
    ):
        case_dir = reports_root / case_id
        case_dir.mkdir()
        auto_verify = repo_root / "reports" / case_id / "auto_verify_report.yaml"
        case_dir.joinpath("auto_verify_report.yaml").write_text(
            auto_verify.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        case_dir.joinpath("report.md").write_text("## Case Summary\n", encoding="utf-8")

    with pytest.raises(ValueError):
        NotionSync(reports_root=reports_root).build_phase8_plan(targets)
