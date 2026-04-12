#!/usr/bin/env python3
"""
run_notion_hub_sync.py — Notion 控制台双向同步脚本

用法:
    python run_notion_hub_sync.py --dry-run
    python run_notion_hub_sync.py --apply --token-env NOTION_API_KEY
    python run_notion_hub_sync.py --dry-run --token-env NOTION_API_KEY --config config/notion_config.yaml

同步逻辑:
    1. knowledge/whitelist.yaml  →  Tasks 数据库（同步任务名称/状态）
    2. knowledge/gold_standards/  →  Canonical Docs 数据库（type=GoldStandard）
    3. knowledge/corrections/     →  Canonical Docs 数据库（type=Spec）
    4. Sessions 数据库最新记录  →  标记已完成任务
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# ---------------------------------------------------------------------------
# PYTHONPATH setup — 让脚本可以从任意工作目录运行
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).parent.resolve()
_SRC_DIR = _SCRIPT_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from src.knowledge_db import KnowledgeDB
from src.models import CorrectionSpec, ErrorType, ImpactScope

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("notion_hub_sync")

# ---------------------------------------------------------------------------
# Notion API 常量
# ---------------------------------------------------------------------------
NOTION_VERSION = "2022-06-28"
_HEADERS = {
    "Authorization": "Bearer {token}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}

# ---------------------------------------------------------------------------
# Console emoji helpers
# ---------------------------------------------------------------------------
def _ok(msg: str) -> None:
    print(f"  ✅ {msg}")

def _skip(msg: str) -> None:
    print(f"  🔄 {msg}")

def _warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")

def _err(msg: str) -> None:
    print(f"  ❌ {msg}")

def _info(msg: str) -> None:
    print(f"  ℹ️  {msg}")

def _hdr(msg: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print("=" * 60)

# ---------------------------------------------------------------------------
# Notion HTTP client (直接用 httpx，不绑死在 NotionClient 上)
# ---------------------------------------------------------------------------

class NotionHTTP:
    """轻量 Notion API HTTP 客户端，支持所有数据库操作"""

    def __init__(self, token: str) -> None:
        self._token = token
        self._base = "https://api.notion.com/v1"
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    # --- HTTP verbs ---------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求到 Notion API"""
        import httpx

        url = f"{self._base}{path}"
        timeout = 30.0

        try:
            with httpx.Client(timeout=timeout) as client:
                req = client.build_request(
                    method=method,
                    url=url,
                    headers=self._headers,
                    json=body,
                    params=params,
                )
                resp = client.send(req)
                data = resp.json()
                if resp.status_code >= 400:
                    raise NotionAPIError(
                        f"Notion API {resp.status_code}: {data.get('message', resp.text)}",
                        status_code=resp.status_code,
                        response=data,
                    )
                return data
        except httpx.HTTPError as e:
            raise NotionAPIError(f"HTTP error: {e}") from e

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("POST", path, body=body)

    def patch(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("PATCH", path, body=body)

    # --- Database queries ---------------------------------------------------

    def query_db(
        self,
        db_id: str,
        filter_: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询数据库，支持自动翻页，返回所有页面结果"""
        results: List[Dict[str, Any]] = []
        body: Dict[str, Any] = {"page_size": page_size}
        if filter_:
            body["filter"] = filter_
        if sorts:
            body["sorts"] = sorts

        while True:
            resp = self.post(f"/databases/{db_id}/query", body=body)
            results.extend(resp.get("results", []))
            next_cursor = resp.get("next_cursor")
            if not next_cursor:
                break
            body["start_cursor"] = next_cursor

        return results

    # --- Page operations ----------------------------------------------------

    def create_page(self, parent_id: str, properties: Dict[str, Any], children: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "parent": {"database_id": parent_id},
            "properties": properties,
        }
        if children:
            body["children"] = children
        return self.post("/pages", body=body)

    def update_page(self, page_id: str, properties: Optional[Dict[str, Any]] = None, archived: bool = False) -> Dict[str, Any]:
        body: Dict[str, Any] = {"archived": archived}
        if properties:
            body["properties"] = properties
        return self.patch(f"/pages/{page_id}", body=body)

    # --- Database info ------------------------------------------------------

    def get_database(self, db_id: str) -> Dict[str, Any]:
        return self.get(f"/databases/{db_id}")


class NotionAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0, response: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(config_path: str | Path) -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    token = data.get("notion_token", "")
    db_ids = data.get("database_ids", {})
    return {"token": token, "database_ids": db_ids}


# ---------------------------------------------------------------------------
# Property builders (Notion API 格式)
# ---------------------------------------------------------------------------

def prop_title(name: str, text: str) -> Dict[str, Any]:
    return {"Name": {"title": [{"text": {"content": text}}]}}

def prop_rich_text(name: str, text: str) -> Dict[str, Any]:
    return {name: {"rich_text": [{"text": {"content": text}}]}}

def prop_select(name: str, value: str) -> Dict[str, Any]:
    return {name: {"select": {"name": value}}}

def prop_status(name: str, value: str) -> Dict[str, Any]:
    return {name: {"status": {"name": value}}}

def prop_number(name: str, value: float) -> Dict[str, Any]:
    return {name: {"number": value}}

def prop_checkbox(name: str, checked: bool) -> Dict[str, Any]:
    return {name: {"checkbox": checked}}

def prop_date(name: str, iso: str) -> Dict[str, Any]:
    return {name: {"date": {"start": iso}}}

def prop_multi_select(name: str, values: List[str]) -> Dict[str, Any]:
    return {name: {"multi_select": [{"name": v} for v in values]}}


# ---------------------------------------------------------------------------
# Notion page parsers
# ---------------------------------------------------------------------------

def _title(props: Dict[str, Any], field: str) -> str:
    return "".join(t.get("plain_text", "") for t in props.get(field, {}).get("title", []))

def _rich(props: Dict[str, Any], field: str) -> str:
    return "".join(t.get("plain_text", "") for t in props.get(field, {}).get("rich_text", []))

def _sel(props: Dict[str, Any], field: str) -> Optional[str]:
    s = props.get(field, {}).get("select")
    return s.get("name") if s else None

def _status(props: Dict[str, Any], field: str) -> Optional[str]:
    s = props.get(field, {}).get("status")
    return s.get("name") if s else None

def _num(props: Dict[str, Any], field: str) -> Optional[float]:
    return props.get(field, {}).get("number")

def _cb(props: Dict[str, Any], field: str) -> bool:
    return props.get(field, {}).get("checkbox", False)


# ---------------------------------------------------------------------------
# Sync: whitelist.yaml → Tasks
# ---------------------------------------------------------------------------

def _build_whitelist_task_props(case: Dict[str, Any], status: str = "Ready") -> Dict[str, Any]:
    """从 whitelist case 构建 Notion Tasks 页面属性

    Tasks DB schema: Name(title), Status(status), Acceptance Criteria(rich_text),
    Type(select), Priority(select), Branch/PR(rich_text), Next Step(rich_text),
    Repo Paths(rich_text), Phase(relation), Canonical Docs(relation), Last Session(relation)
    """
    params = case.get("parameters", {})
    props: Dict[str, Any] = {}
    props.update(prop_title("Name", case.get("name", "")))
    props.update(prop_status("Status", status))
    # Acceptance Criteria ← reference field
    ref = case.get("reference", "")
    if ref:
        props.update(prop_rich_text("Acceptance Criteria", ref))
    # Type ← map flow_type to valid Tasks DB select values
    # Valid Type values: Planning, Implementation, Review, Governance, Sync, Integration
    flow_type = case.get("flow_type", "")
    type_map = {"INTERNAL": "Implementation", "EXTERNAL": "Implementation",
                "NATURAL_CONVECTION": "Implementation"}
    if flow_type:
        props.update(prop_select("Type", type_map.get(flow_type, "Implementation")))
    # Priority ← derived from Re magnitude
    Re = params.get("Re")
    if Re is not None:
        priority = "P0" if Re >= 10000 else "P1" if Re >= 1000 else "P2"
        props.update(prop_select("Priority", priority))
    # Repo Paths ← optional, skip
    return props


def sync_whitelist_to_tasks(
    notion: NotionHTTP,
    db_ids: Dict[str, str],
    kdb: KnowledgeDB,
    dry_run: bool = False,
) -> None:
    """将 whitelist.yaml 中的案例同步到 Tasks 数据库"""
    db_id = db_ids.get("tasks")
    if not db_id:
        _warn("Tasks database ID not configured — skipping whitelist sync")
        return

    whitelist = kdb._load_whitelist()
    local_cases = {c["id"]: c for c in whitelist.get("cases", [])}

    # 读取 Notion Tasks 中所有页面
    try:
        notion_tasks = notion.query_db(db_id)
    except NotionAPIError as e:
        _err(f"Failed to query Tasks DB: {e}")
        return

    notion_names = {_title(p["properties"], "Name") for p in notion_tasks}
    notion_by_name = {_title(p["properties"], "Name"): p for p in notion_tasks}

    to_create: List[Dict[str, Any]] = []
    to_update: List[tuple[str, Dict[str, Any]]] = []  # (page_id, props)

    for case_id, case in local_cases.items():
        name = case.get("name", "")
        if not name:
            continue
        if name not in notion_names:
            to_create.append(_build_whitelist_task_props(case))
        else:
            # 检查状态是否一致（本地无状态字段，只需确保 Notion 中有对应条目即可）
            page = notion_by_name[name]
            status = _status(page["properties"], "Status")
            if status is None:
                to_update.append((page["id"], prop_status("Status", "Ready")))

    if dry_run:
        if to_create:
            for props in to_create:
                title = props["Name"]["title"][0]["text"]["content"]
                _skip(f"[DRY] Would CREATE task: {title}")
        else:
            _ok("No new tasks to create")
        if to_update:
            for page_id, props in to_update:
                _skip(f"[DRY] Would UPDATE task {page_id[:8]}… status → Ready")
        else:
            _ok("No tasks to update")
    else:
        created, updated = 0, 0
        for props in to_create:
            try:
                notion.create_page(db_id, props)
                title = props["Name"]["title"][0]["text"]["content"]
                _ok(f"Created task: {title}")
                created += 1
            except NotionAPIError as e:
                _err(f"Failed to create task: {e}")
        for page_id, props in to_update:
            try:
                notion.update_page(page_id, properties=props)
                _ok(f"Updated task {page_id[:8]}…")
                updated += 1
            except NotionAPIError as e:
                _err(f"Failed to update task {page_id[:8]}…: {e}")
        _info(f"Whitelist sync done — created: {created}, updated: {updated}")


# ---------------------------------------------------------------------------
# Sync: gold_standards/*.yaml → Canonical Docs (type=GoldStandard)
# ---------------------------------------------------------------------------

def _gold_standard_page_props(gs: Dict[str, Any], case_id: str) -> Dict[str, Any]:
    """构建 Gold Standard 页面的 Notion 属性

    Canonical Docs DB schema: Name(title), Type(select), Version(rich_text),
    Status(select), Summary(rich_text), Repo Path(rich_text), Tasks(relation), Phases(relation)
    """
    # Derive human-readable name from case_id (e.g. lid_driven_cavity → Lid Driven Cavity)
    display_name = case_id.replace("_", " ").title()
    gs_name = f"{display_name} — GoldStandard"
    props: Dict[str, Any] = {}
    props.update(prop_title("Name", gs_name))
    props.update(prop_select("Type", "Reference"))
    props.update(prop_select("Status", "Active"))

    # Version ← source/literature_doi
    doi = gs.get("literature_doi", "")
    source = gs.get("source", "")
    version_str = doi if doi else (source or "")
    if version_str:
        props.update(prop_rich_text("Version", version_str))

    # Summary ← key GS fields
    quantity = gs.get("quantity", "")
    tol = gs.get("tolerance")
    ref_count = len(gs.get("reference_values", []))
    summary_parts = [f"quantity: {quantity}"] if quantity else []
    if tol is not None:
        summary_parts.append(f"tolerance: {tol}")
    summary_parts.append(f"reference_values: {ref_count} points")
    if "case_info" in gs and isinstance(gs["case_info"], dict):
        ci = gs["case_info"]
        summary_parts.append(f"Re={ci.get('Re', 'N/A')}")
    props.update(prop_rich_text("Summary", "; ".join(summary_parts)))
    return props


def sync_gold_standards(
    notion: NotionHTTP,
    db_ids: Dict[str, str],
    kdb: KnowledgeDB,
    dry_run: bool = False,
) -> None:
    """将 knowledge/gold_standards/*.yaml 同步到 Canonical Docs"""
    db_id = db_ids.get("canonical_docs")
    if not db_id:
        _warn("Canonical Docs database ID not configured — skipping gold_standards sync")
        return

    gs_dir = kdb._root / "gold_standards"
    if not gs_dir.exists():
        _info("knowledge/gold_standards/ does not exist — skipping")
        return

    # 读取 Notion Canonical Docs 中已有的 Reference 页面（GoldStandard → Reference）
    try:
        existing = notion.query_db(
            db_id,
            filter_={"property": "Type", "select": {"equals": "Reference"}},
        )
    except NotionAPIError as e:
        _err(f"Failed to query Canonical Docs DB: {e}")
        return

    existing_names = {_title(p["properties"], "Name") for p in existing}
    gs_files = list(gs_dir.glob("*.yaml"))

    if not gs_files:
        _info("No gold_standards/*.yaml files found")
        return

    created, skipped = 0, 0
    for gs_path in gs_files:
        # case_id derived from filename (without extension)
        case_id = gs_path.stem
        try:
            with open(gs_path, encoding="utf-8") as f:
                # gold_standards YAML may contain --- multi-document separators;
                # load all documents and merge
                docs = list(yaml.safe_load_all(f))
                gs_data: Dict[str, Any] = {}
                for doc in docs:
                    if doc:
                        gs_data.update(doc)
        except yaml.YAMLError as e:
            _warn(f"Skipping malformed YAML {gs_path.name}: {e}")
            skipped += 1
            continue

        props = _gold_standard_page_props(gs_data, case_id)
        page_name = props["Name"]["title"][0]["text"]["content"]

        if page_name in existing_names:
            _ok(f"GoldStandard already exists in Notion: {page_name} — skipping")
            skipped += 1
            continue

        if dry_run:
            _skip(f"[DRY] Would CREATE GoldStandard: {page_name}")
        else:
            try:
                notion.create_page(db_id, props)
                _ok(f"Created GoldStandard: {page_name}")
                created += 1
            except NotionAPIError as e:
                _err(f"Failed to create GoldStandard page {page_name}: {e}")

    _info(f"Gold Standards sync done — created: {created}, skipped: {skipped}")


# ---------------------------------------------------------------------------
# Sync: corrections/*.yaml → Canonical Docs (type=Spec)
# ---------------------------------------------------------------------------

def _correction_page_props(corr: CorrectionSpec, filename: str) -> Dict[str, Any]:
    """构建 CorrectionSpec 页面的 Notion 属性

    Canonical Docs DB schema: Name(title), Type(select), Version(rich_text),
    Status(select), Summary(rich_text), Repo Path(rich_text), Tasks(relation), Phases(relation)
    """
    task_name = corr.task_spec_name or filename.replace(".yaml", "")
    title = f"{task_name} — {corr.error_type.value}"
    props: Dict[str, Any] = {}
    props.update(prop_title("Name", title))
    props.update(prop_select("Type", "Spec"))
    props.update(prop_select("Status", "Active"))
    # Summary ← all key fields concatenated
    summary_lines = [
        f"error_type: {corr.error_type.value}",
        f"impact_scope: {corr.impact_scope.value}",
        f"root_cause: {corr.root_cause}",
        f"fix_action: {corr.fix_action}",
        f"needs_replay: {corr.needs_replay}",
    ]
    if corr.evidence:
        summary_lines.append(f"evidence: {corr.evidence}")
    props.update(prop_rich_text("Summary", "\n".join(summary_lines)))
    # Version ← created_at timestamp
    if corr.created_at:
        props.update(prop_rich_text("Version", f"created: {corr.created_at}"))
    return props


def sync_corrections(
    notion: NotionHTTP,
    db_ids: Dict[str, str],
    kdb: KnowledgeDB,
    dry_run: bool = False,
) -> None:
    """将 knowledge/corrections/*.yaml 同步到 Canonical Docs"""
    db_id = db_ids.get("canonical_docs")
    if not db_id:
        _warn("Canonical Docs database ID not configured — skipping corrections sync")
        return

    corrections = kdb.load_corrections()
    if not corrections:
        _ok("No correction files found")
        return

    created, skipped = 0, 0
    for corr in corrections:
        # 用文件名作为 task_spec_name 回填（从 created_at 推断不准确，用 save_correction 的逻辑）
        # 其实 load_corrections 已经从 YAML 文件加载了 task_spec_name
        filename = f"{corr.created_at}_{corr.task_spec_name}_{corr.error_type.value}.yaml"
        props = _correction_page_props(corr, filename)
        page_name = props["Name"]["title"][0]["text"]["content"]

        if dry_run:
            _skip(f"[DRY] Would CREATE Spec: {page_name}")
        else:
            try:
                notion.create_page(db_id, props)
                _ok(f"Created Spec: {page_name}")
                created += 1
            except NotionAPIError as e:
                _err(f"Failed to create Spec page {page_name}: {e}")

    _info(f"Corrections sync done — created: {created}, skipped: {skipped}")


# ---------------------------------------------------------------------------
# Sessions → 标记已完成任务
# ---------------------------------------------------------------------------

def reconcile_sessions_with_tasks(
    notion: NotionHTTP,
    db_ids: Dict[str, str],
    dry_run: bool = False,
) -> None:
    """从 Sessions 数据库读取最新会话记录，找出 Closed 状态的会话，
    通过 Primary Task 关系找到对应的任务并更新状态"""
    tasks_db = db_ids.get("tasks")
    sessions_db = db_ids.get("sessions")
    if not tasks_db or not sessions_db:
        _warn("Tasks or Sessions DB ID missing — skipping session reconciliation")
        return

    # Sessions DB sort by Name (no Date field); filter by Closed status
    try:
        sessions = notion.query_db(
            sessions_db,
            filter_={"property": "Status", "select": {"equals": "Closed"}},
            page_size=50,
        )
    except NotionAPIError as e:
        _err(f"Failed to query Sessions DB: {e}")
        return

    if not sessions:
        _ok("No closed sessions found")
        return

    # 读取所有 Ready 状态的任务
    try:
        ready_tasks = notion.query_db(
            tasks_db,
            filter_={"property": "Status", "status": {"equals": "Ready"}},
        )
    except NotionAPIError as e:
        _err(f"Failed to query Tasks DB: {e}")
        return

    ready_by_id = {t["id"]: t for t in ready_tasks}
    updated = 0

    for s in sessions:
        props = s.get("properties", {})
        # Sessions DB has "Primary Task" relation field
        primary_task_rel = props.get("Primary Task", {}).get("relation", [])
        for rel_entry in primary_task_rel:
            task_id = rel_entry.get("id")
            if task_id and task_id in ready_by_id:
                task_name = _title(ready_by_id[task_id]["properties"], "Name")
                if dry_run:
                    _skip(f"[DRY] Would mark task '{task_name}' as Done (from Session '{_title(props, 'Name')}')")
                else:
                    try:
                        notion.update_page(task_id, properties=prop_status("Status", "Done"))
                        _ok(f"Marked task '{task_name}' as Done (Session: {_title(props, 'Name')})")
                        updated += 1
                    except NotionAPIError as e:
                        _err(f"Failed to update task {task_name}: {e}")

    if dry_run:
        _info(f"Session reconciliation: checked {len(sessions)} closed session(s)")
    else:
        _info(f"Session reconciliation done — updated: {updated}")


# ---------------------------------------------------------------------------
# Write session record to Sessions DB
# ---------------------------------------------------------------------------

def write_session_record(
    notion: NotionHTTP,
    db_ids: Dict[str, str],
    session_data: Dict[str, Any],
    dry_run: bool = False,
) -> None:
    """将本次同步会话记录写入 Sessions 数据库

    Sessions DB schema: Name(title), Status(select: Active/Paused/Closed),
    Goal(rich_text), Handoff(rich_text), Startup Prompt(rich_text),
    Next Step(rich_text), Outputs(rich_text), Primary Task(relation),
    Decisions Made(relation), Phase(relation)
    """
    db_id = db_ids.get("sessions")
    if not db_id:
        _warn("Sessions database ID not configured — skipping session write")
        return

    props: Dict[str, Any] = {}
    props.update(prop_title("Name", session_data.get("name", "Sync Session")))
    # Sessions Status is a select field, not a status field
    status_val = session_data.get("status", "Closed")
    if status_val not in ("Active", "Paused", "Closed"):
        status_val = "Closed"  # default for sync sessions
    props.update(prop_select("Status", status_val))
    # Use Handoff rich_text to store sync summary
    summary = session_data.get("summary", "")
    tasks_synced = session_data.get("tasks_synced", 0)
    if summary:
        props.update(prop_rich_text("Handoff", summary))
    if tasks_synced is not None:
        props.update(prop_rich_text("Outputs", f"tasks_synced: {tasks_synced}"))
    # Use Goal to store date info
    date_str = session_data.get("date", datetime.date.today().isoformat())
    props.update(prop_rich_text("Goal", f"sync_date: {date_str}"))

    if dry_run:
        _skip(f"[DRY] Would WRITE session record: {session_data.get('name', 'Sync Session')}")
    else:
        try:
            page = notion.create_page(db_id, props)
            _ok(f"Session record written: {page.get('id', 'unknown')[:8]}…")
        except NotionAPIError as e:
            _err(f"Failed to write session record: {e}")


# ---------------------------------------------------------------------------
# Dry-run report
# ---------------------------------------------------------------------------

def generate_dry_run_report(
    notion: NotionHTTP,
    db_ids: Dict[str, str],
    kdb: KnowledgeDB,
) -> None:
    """生成 --dry-run 对比报告"""
    _hdr("DRY-RUN REPORT")

    # 1. Tasks vs whitelist
    tasks_db = db_ids.get("tasks")
    if tasks_db:
        try:
            notion_tasks = notion.query_db(tasks_db)
        except NotionAPIError as e:
            _err(f"Failed to query Tasks DB: {e}")
            notion_tasks = []

        whitelist = kdb._load_whitelist()
        local_names = {c["name"] for c in whitelist.get("cases", []) if c.get("name")}
        notion_names = {_title(t["properties"], "Name") for t in notion_tasks}
        notion_by_name = {_title(t["properties"], "Name"): t for t in notion_tasks}

        missing_in_notion = local_names - notion_names
        extra_in_notion = notion_names - local_names

        print("\n  [Tasks DB vs whitelist.yaml]")
        if missing_in_notion:
            for n in sorted(missing_in_notion):
                _skip(f"  Missing in Notion (whitelist has): {n}")
        else:
            _ok("All whitelist cases exist in Notion Tasks")

        if extra_in_notion:
            for n in sorted(extra_in_notion):
                status = _status(notion_by_name[n]["properties"], "Status")
                _warn(f"  Extra in Notion (not in whitelist): {n} [Status={status}]")

        # 任务状态不一致检查
        inconsistent = []
        for t in notion_tasks:
            props = t["properties"]
            name = _title(props, "Name")
            status = _status(props, "Status") or _sel(props, "Status")
            if name in local_names and status not in ("Ready", "In Progress", "Done", "Completed"):
                inconsistent.append((name, status))
        if inconsistent:
            print("\n  [Task Status Inconsistencies]")
            for name, status in inconsistent:
                _warn(f"  Unexpected status '{status}' for task: {name}")
        else:
            _ok("No task status inconsistencies")

    # 2. Gold Standards
    gs_dir = kdb._root / "gold_standards"
    cd_db = db_ids.get("canonical_docs")
    if gs_dir.exists() and cd_db:
        local_gs = list(gs_dir.glob("*.yaml"))
        print(f"\n  [Gold Standards] {len(local_gs)} local file(s)")
        if local_gs:
            try:
                # GoldStandard pages use Type=Reference in Canonical Docs
                existing = notion.query_db(
                    cd_db,
                    filter_={"property": "Type", "select": {"equals": "Reference"}},
                )
            except NotionAPIError as e:
                _err(f"Failed to query Canonical Docs DB: {e}")
                existing = []
            existing_names = {_title(p["properties"], "Name") for p in existing}
            for gs_path in local_gs:
                case_id = gs_path.stem
                display_name = case_id.replace("_", " ").title()
                page_name = f"{display_name} — GoldStandard"
                if page_name in existing_names:
                    _ok(f"  {gs_path.name}: synced")
                else:
                    _skip(f"  {gs_path.name}: NOT in Notion ({page_name})")
        else:
            _warn("  knowledge/gold_standards/ is empty")
    elif not gs_dir.exists():
        _warn("  knowledge/gold_standards/ does not exist")

    # 3. Corrections
    corrections = kdb.load_corrections()
    print(f"\n  [CorrectionSpecs] {len(corrections)} file(s) loaded")
    if corrections:
        if cd_db:
            try:
                existing = notion.query_db(
                    cd_db,
                    filter_={"property": "Type", "select": {"equals": "Spec"}},
                )
            except NotionAPIError as e:
                _err(f"Failed to query Canonical Docs DB: {e}")
                existing = []
            existing_titles = {_title(p["properties"], "Name") for p in existing}
            for corr in corrections:
                fname = f"{corr.task_spec_name or '?'} — {corr.error_type.value}"
                if fname in existing_titles:
                    _ok(f"  {fname}: synced")
                else:
                    _skip(f"  {fname}: NOT in Notion")
        else:
            _warn("  Canonical Docs DB not configured — cannot verify sync status")
    else:
        _warn("  knowledge/corrections/ is empty")

    # 4. Sessions reconciliation
    reconcile_sessions_with_tasks(notion, db_ids, dry_run=True)

    _hdr("DRY-RUN COMPLETE — no changes written")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Notion Hub Sync — 双向同步 cfd-harness-unified ↔ Notion 控制台",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            示例:
              python run_notion_hub_sync.py --dry-run
              python run_notion_hub_sync.py --apply --token-env NOTION_API_KEY
              python run_notion_hub_sync.py --apply --token "ntn_xxx" --config config/notion_config.yaml
        """),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅报告差异，不写入 Notion",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="执行同步（写入 Notion）",
    )
    parser.add_argument(
        "--config", type=str, default="config/notion_config.yaml",
        help="notion_config.yaml 路径（默认: config/notion_config.yaml）",
    )
    parser.add_argument(
        "--token-env", type=str,
        help="NOTION_API_KEY 环境变量名（优先级高于 --config 中的 token）",
    )
    parser.add_argument(
        "--token", type=str,
        help="直接传入 Notion API Token（优先级最高）",
    )
    parser.add_argument(
        "--skip-whitelist", action="store_true",
        help="跳过 whitelist → Tasks 同步",
    )
    parser.add_argument(
        "--skip-gold-standards", action="store_true",
        help="跳过 gold_standards → Canonical Docs 同步",
    )
    parser.add_argument(
        "--skip-corrections", action="store_true",
        help="跳过 corrections → Canonical Docs 同步",
    )
    parser.add_argument(
        "--skip-sessions", action="store_true",
        help="跳过 Sessions  reconciliation",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="输出详细调试信息",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not (args.dry_run or args.apply):
        parser.error("请指定 --dry-run 或 --apply（可同时指定）")
    if args.apply and not (args.token or args.token_env or os.getenv("NOTION_API_KEY")):
        # 若 --config 存在，直接从配置文件读取 token
        pass  # 由 load_config 兜底

    # --- 确定 token ----------------------------------------------------------
    token: Optional[str] = None
    if args.token:
        token = args.token
    elif args.token_env:
        env_val = os.getenv(args.token_env)
        if not env_val:
            _err(f"Environment variable {args.token_env} is not set")
            sys.exit(1)
        token = env_val

    # --- 加载配置 -----------------------------------------------------------
    try:
        config_path = _SCRIPT_DIR / args.config
        cfg = load_config(config_path)
    except FileNotFoundError as e:
        _err(str(e))
        sys.exit(1)
    except Exception as e:
        _err(f"Failed to load config: {e}")
        sys.exit(1)

    if not token:
        token = cfg.get("token", "")
    if not token:
        _err("No Notion token found — set --token, --token-env NOTION_API_KEY, or notion_token in config")
        sys.exit(1)

    db_ids: Dict[str, str] = cfg.get("database_ids", {})

    # --- 初始化组件 ---------------------------------------------------------
    notion = NotionHTTP(token)
    kdb = KnowledgeDB()

    # --- Dry-run 报告 -------------------------------------------------------
    if args.dry_run:
        generate_dry_run_report(notion, db_ids, kdb)

    # --- Apply 同步 ---------------------------------------------------------
    if args.apply:
        _hdr("APPLY SYNC")
        session_start = datetime.datetime.utcnow()
        stats = {"tasks_synced": 0}

        if not args.skip_whitelist:
            _info("=== Syncing whitelist → Tasks ===")
            sync_whitelist_to_tasks(notion, db_ids, kdb, dry_run=False)
            stats["tasks_synced"] = len(kdb._load_whitelist().get("cases", []))

        if not args.skip_gold_standards:
            _info("=== Syncing gold_standards → Canonical Docs ===")
            sync_gold_standards(notion, db_ids, kdb, dry_run=False)

        if not args.skip_corrections:
            _info("=== Syncing corrections → Canonical Docs ===")
            sync_corrections(notion, db_ids, kdb, dry_run=False)

        if not args.skip_sessions:
            _info("=== Reconciling Sessions → Tasks ===")
            reconcile_sessions_with_tasks(notion, db_ids, dry_run=False)

        # 写入本次会话记录
        session_data = {
            "name": f"Hub Sync {datetime.date.today().isoformat()}",
            "status": "Done",
            "date": session_start.isoformat()[:10],
            "summary": "cfd-harness-unified ↔ Notion Hub sync completed",
            "tasks_synced": stats["tasks_synced"],
        }
        write_session_record(notion, db_ids, session_data, dry_run=False)

        _hdr("SYNC COMPLETE")


if __name__ == "__main__":
    main()
