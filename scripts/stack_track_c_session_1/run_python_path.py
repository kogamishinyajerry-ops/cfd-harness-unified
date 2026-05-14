"""Path (b): Direct import of assemble_stack() for case_011 v5b.

Output: stack_report_python.json with full AdvisorStackReport serialization.

LLM-offline check: this script imports ONLY from advisor_stack +
geometry_ingest. No anthropic/openai/corpus_loader.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.stack_track_c_session_1.build_inputs import assemble_payload  # noqa: E402
from ui.backend.services.advisor_stack import assemble_stack  # noqa: E402
from ui.backend.services.geometry_ingest.thin_wall_advisor import PatchGeometry  # noqa: E402


def _serialize(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        d = dataclasses.asdict(obj)
        return d
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"unserializable: {type(obj).__name__}")


def main() -> int:
    payload = assemble_payload()

    # Rehydrate thin_wall_inputs.patches dicts → PatchGeometry instances
    # (mirroring what ai_review.py route does on the HTTP boundary).
    tw = dict(payload["thin_wall_inputs"])
    tw["patches"] = tuple(
        PatchGeometry(name=p["name"], bbox_dimensions=tuple(p["bbox_dimensions"]))
        for p in tw["patches"]
    )

    report = assemble_stack(
        parts_manifest=payload["parts_manifest"],
        shm_dict=payload["shm_dict"],
        thin_wall_inputs=tw,
        step_path=Path(payload["step_path"]),
        step_bbox_max_extent_raw=payload["step_bbox_max_extent_raw"],
    )

    out_path = Path(__file__).parent / "stack_report_python.json"
    out_path.write_text(json.dumps(dataclasses.asdict(report), indent=2, default=_serialize))

    print(f"=== stack report (python path) ===")
    print(f"advisor_count:        {report.advisor_count}")
    print(f"finding_count:        {len(report.findings)}")
    print(f"critical_count:       {report.critical_count}")
    print(f"warning_count:        {report.warning_count}")
    print(f"failed_advisor_count: {report.failed_advisor_count}")
    print(f"stack_duration_ms:    {report.stack_duration_ms:.2f}")
    print(f"advisors_dispatched:  {[c.advisor_name for c in report.advisor_calls]}")
    print(f"advisor_statuses:     {[(c.advisor_name, c.status) for c in report.advisor_calls]}")
    print(f"evidence_refs:        {sorted(report.evidence_refs)}")
    print(f"out: {out_path}")
    print()
    print("=== findings ===")
    for i, f in enumerate(report.findings, 1):
        print(f"[{i}] [{f.severity.upper()}] advisor={f.source_advisor} code={f.code}")
        print(f"     v_rows={f.evidence_v_rows}")
        print(f"     msg={f.message[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
