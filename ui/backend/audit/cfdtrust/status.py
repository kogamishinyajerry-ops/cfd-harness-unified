"""Small helpers shared by audit modules and CLI."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_artifacts_dir(case_dir: Path) -> Path:
    art = case_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    return art


def mocked_gate(name: str, summary: str, artifact: str | None = None) -> Dict[str, Any]:
    gate: Dict[str, Any] = {
        "status": "MOCKED",
        "summary": summary,
        "details": {"name": name, "note": "Phase 0 placeholder — not real evidence."},
    }
    if artifact:
        gate["artifact"] = artifact
    return gate
