"""Agent Crew Observatory backing service.

Reads .planning/decisions/*.md, reports/codex_tool_reports/*, and
.planning/reviews/kogami/*/ to produce the CrewSnapshot + CrewArc payloads.

Rules per V93_CREW_UI_SPEC.md §3:
- All data parsed from real files; missing fields → UNPARSED / null, never invented.
- No LLM, no subprocess, no network calls.
- verdict extraction is heuristic and fail-closed (§3.3).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ui.backend.services.validation_report import REPO_ROOT

DECISIONS_DIR = REPO_ROOT / ".planning" / "decisions"
CODEX_REPORTS_DIR = REPO_ROOT / "reports" / "codex_tool_reports"
KOGAMI_DIR = REPO_ROOT / ".planning" / "reviews" / "kogami"

# Only arcs with date >= this cutoff OR with loop_auditor/confidence keys.
ARC_DATE_CUTOFF = "2026-05-01"
ARC_LIMIT = 80

# DEC id validation regex (§2 arc detail route)
DEC_ID_RE = re.compile(r"^DEC-[A-Za-z0-9_\-]+$")

# Frontmatter extractor (same as decisions.py)
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# Round number from filename
_ROUND_RE = re.compile(r"[Rr](?:ound)?[_\s\-]?(\d)")

# Verdict tokens ordered by priority (highest to lowest)
_VERDICT_TOKENS = [
    "CHANGES_REQUIRED",
    "APPROVE_WITH_COMMENTS",
    "RESOLVED",
    "APPROVE",
]
_APPROVE_STRICT_RE = re.compile(r"\bAPPROVE\b(?!_WITH_COMMENTS)")

# P1/P2/P3 counter
_PX_RE = re.compile(r"\bP([123])\b")


# ---------- dataclasses (slots=True per spec §3.7) ----------------------------


@dataclass(slots=True)
class RoleNode:
    id: str
    label: str
    model: str | None
    desc: str
    count_label: str | None
    count: int | None


@dataclass(slots=True)
class Edge:
    id: str
    from_: str
    to: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "from": self.from_, "to": self.to, "label": self.label}


@dataclass(slots=True)
class CodexRound:
    round: int
    verdict: str
    p1: int
    p2: int
    p3: int
    report_path: str
    missing: bool


@dataclass(slots=True)
class KogamiRef:
    topic: str
    verdict: str


@dataclass(slots=True)
class CrewArc:
    decision_id: str
    title: str
    date: str
    phase: str | None
    autonomous: bool
    confidence: str | None
    loop_auditor: str | None
    codex_relay: str | None
    codex_rounds: list[CodexRound]
    kogami: KogamiRef | None
    relative_path: str


@dataclass(slots=True)
class CrewStats:
    decisions_total: int
    codex_reports_total: int
    autonomous_total: int
    loop_auditor_total: int
    kogami_total: int


@dataclass(slots=True)
class CrewSnapshot:
    roles: list[RoleNode]
    edges: list[dict[str, Any]]
    arcs: list[CrewArc]
    stats: CrewStats


@dataclass(slots=True)
class ReportExcerpt:
    round: int
    path: str
    excerpt: str
    verdict: str
    missing: bool


@dataclass(slots=True)
class ArcDetail:
    decision_id: str
    frontmatter: dict[str, Any]
    body_excerpt: str
    reports: list[ReportExcerpt]


# ---------- static topology (spec §2, written as literal) ---------------------

_STATIC_ROLES: list[dict[str, Any]] = [
    {"id": "sponsor",      "label": "用户 · Sponsor",          "model": None,                          "desc": "目标设定与最终裁决（DEC Accept / 操作点裁决 / cap=3 溢出仲裁）", "count_label": None,            "count": None},
    {"id": "chief",        "label": "Claude 总师",             "model": "Opus / Fable · 主驱动",        "desc": "方案/实现/跨文件推理/最终把关；autonomous DEC 的签发者",          "count_label": "autonomous DECs", "count": 0},
    {"id": "workers",      "label": "Subagents · 施工/侦察",    "model": "Sonnet / Haiku / Workflow",    "desc": "只读侦察回 ≤2000tok 摘要；隔离 worktree 施工",                    "count_label": None,            "count": None},
    {"id": "codex",        "label": "Codex 异源审查",           "model": "GPT-5.4 xhigh · 86gs relay",   "desc": "盲点审查 · round cap=3 · verbatim 例外",                          "count_label": "审查报告",        "count": 0},
    {"id": "loop_auditor", "label": "loop-auditor 闭环审计",    "model": "只读 agent",                   "desc": "审验证体系本身：oracle 对齐/fail-closed/防篡改（FLAG/BLOCK）",     "count_label": "标注 DECs",       "count": 0},
    {"id": "kogami",       "label": "Kogami 战略层",            "model": "claude -p 隔离子进程",          "desc": "opt-in 独立战略审（V133 后仅用户显式调用）",                       "count_label": "invocations",    "count": 0},
    {"id": "archive",      "label": "Git · DEC 档案",           "model": None,                          "desc": "可验证真值：决策文件 + 审查报告 + commit 链",                      "count_label": "决策文件",        "count": 0},
]

_STATIC_EDGES: list[dict[str, Any]] = [
    {"id": "e1", "from": "sponsor",      "to": "chief",   "label": "目标 / 裁决"},
    {"id": "e2", "from": "chief",        "to": "workers", "label": "自足 prompt 委派"},
    {"id": "e3", "from": "workers",      "to": "chief",   "label": "≤2000 tok 汇报"},
    {"id": "e4", "from": "chief",        "to": "codex",   "label": "commit diff 审查"},
    {"id": "e5", "from": "codex",        "to": "chief",   "label": "verdict（cap=3）"},
    {"id": "e6", "from": "loop_auditor", "to": "chief",   "label": "设计审 FLAG / BLOCK"},
    {"id": "e7", "from": "sponsor",      "to": "kogami",  "label": "opt-in 战略审"},
    {"id": "e8", "from": "chief",        "to": "archive", "label": "DEC + commit + trailer"},
    {"id": "e9", "from": "kogami",       "to": "archive", "label": "review 工件"},
]


# ---------- internal helpers --------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    body = text[match.end():]
    return fm, body


def _extract_title(body: str, limit: int = 160) -> str:
    m = _TITLE_RE.search(body)
    if not m:
        return "(untitled)"
    return m.group(1).strip()[:limit]


def _parse_date(stem: str) -> str | None:
    """Extract YYYY-MM-DD from filename stem; return None if not valid."""
    candidate = stem[:10]
    if re.match(r"^\d{4}-\d{2}-\d{2}$", candidate):
        return candidate
    return None


def _extract_verdict(text: str) -> str:
    """
    Heuristic verdict extraction per spec §3.3.
    For each known token, find the last occurrence position.
    Pick the token with the largest (rightmost) position among those present.
    APPROVE uses word-boundary match to exclude APPROVE_WITH_COMMENTS substrings.
    Returns UNPARSED if no token found.
    """
    positions: dict[str, int] = {}
    for token in _VERDICT_TOKENS:
        if token == "APPROVE":
            # Must match APPROVE as standalone word, not as prefix of APPROVE_WITH_COMMENTS
            matches = list(_APPROVE_STRICT_RE.finditer(text))
            if matches:
                positions[token] = matches[-1].start()
        else:
            idx = text.rfind(token)
            if idx >= 0:
                positions[token] = idx

    if not positions:
        return "UNPARSED"
    # Token with maximum last-occurrence position wins
    return max(positions, key=lambda t: positions[t])


def _count_px(text: str) -> tuple[int, int, int]:
    """Count P1, P2, P3 occurrences heuristically."""
    counts = {1: 0, 2: 0, 3: 0}
    for m in _PX_RE.finditer(text):
        n = int(m.group(1))
        counts[n] = counts.get(n, 0) + 1
    return counts[1], counts[2], counts[3]


def _expand_brace_path(raw: str) -> list[str]:
    """
    Expand paths like `reports/.../foo_R{0,1}.md` into
    `['reports/.../foo_R0.md', 'reports/.../foo_R1.md']`.

    Strategy:
    1. Try to expand brace expressions first.
    2. If no braces found in the full string, split by comma as a fallback
       (for comma-separated plain paths).
    """
    # Check if any braces present
    brace_match = re.search(r"\{([^}]+)\}", raw)
    if brace_match:
        # Expand this single brace expression
        prefix = raw[:brace_match.start()]
        suffix = raw[brace_match.end():]
        results = []
        for val in brace_match.group(1).split(","):
            results.append(prefix + val.strip() + suffix)
        return results
    else:
        # No braces: split by comma for multiple plain paths
        return [part.strip() for part in raw.split(",") if part.strip()]


def _clean_report_refs(raw: str) -> list[str]:
    """Sanitize a `codex_tool_report_path` frontmatter value into bare paths.

    Real DECs carry annotated values — `path1; path2`, `path.md (filled by
    main session ...)`, `/tmp/x.log (last round APPROVE)` — which must not be
    treated as literal filenames (Codex V93 R0 P1). Order matters: strip
    parenthetical annotations FIRST, split on ';' SECOND, and only then run
    brace/comma expansion per fragment (the brace body itself contains commas).
    """
    no_paren = re.sub(r"\([^)]*\)", " ", raw)
    out: list[str] = []
    for fragment in no_paren.split(";"):
        fragment = fragment.strip()
        if not fragment:
            continue
        out.extend(p for p in _expand_brace_path(fragment) if p)
    return out


def _round_from_path(path_str: str) -> int | None:
    """Extract round number from file path/name."""
    m = _ROUND_RE.search(Path(path_str).name)
    if m:
        return int(m.group(1))
    return None


def _build_codex_rounds(fm: dict[str, Any], dec_id: str) -> list[CodexRound]:
    """
    Discover codex rounds via two paths:
    a) frontmatter codex_tool_report_path (with brace expansion)
    b) glob of codex_tool_reports dir matching dec_id slug
    Merge and deduplicate by path; assign round numbers.
    """
    seen_paths: dict[str, CodexRound] = {}  # path -> CodexRound

    # Path (a): frontmatter field (annotation-tolerant, Codex V93 R0 P1)
    fm_path_raw = str(fm.get("codex_tool_report_path") or "").strip()
    if fm_path_raw:
        expanded = _clean_report_refs(fm_path_raw)
        for raw_p in expanded:
            raw_p = raw_p.strip()
            if not raw_p:
                continue
            abs_path = REPO_ROOT / raw_p
            # only repo-internal relative refs are readable; absolute paths
            # (e.g. /tmp/x.log in old DECs) or ../ escapes are reported as
            # missing-from-repo, never read (path-containment guard)
            inside_repo = (
                not Path(raw_p).is_absolute()
                and ".." not in Path(raw_p).parts
            )
            missing = not (inside_repo and abs_path.exists())
            round_num = _round_from_path(raw_p)
            if missing:
                verdict = "MISSING"
                p1, p2, p3 = 0, 0, 0
            else:
                text = abs_path.read_text(encoding="utf-8", errors="replace")
                verdict = _extract_verdict(text)
                p1, p2, p3 = _count_px(text)
            seen_paths[raw_p] = CodexRound(
                round=round_num if round_num is not None else -1,
                verdict=verdict,
                p1=p1, p2=p2, p3=p3,
                report_path=raw_p,
                missing=missing,
            )

    # Path (b): glob
    if CODEX_REPORTS_DIR.exists():
        # Build slug variants: DEC-V61-238 → v61-238, v61_238
        slug_base = dec_id.lower().replace("dec-", "")  # e.g. "v61-238"
        slug_alt = slug_base.replace("-", "_")  # e.g. "v61_238"

        for p in sorted(CODEX_REPORTS_DIR.iterdir()):
            name_lower = p.name.lower()
            if slug_base in name_lower or slug_alt in name_lower:
                rel = str(p.relative_to(REPO_ROOT))
                if rel not in seen_paths:
                    round_num = _round_from_path(p.name)
                    text = p.read_text(encoding="utf-8", errors="replace")
                    verdict = _extract_verdict(text)
                    p1, p2, p3 = _count_px(text)
                    seen_paths[rel] = CodexRound(
                        round=round_num if round_num is not None else -1,
                        verdict=verdict,
                        p1=p1, p2=p2, p3=p3,
                        report_path=rel,
                        missing=False,
                    )

    if not seen_paths:
        return []

    # Assign sequential round numbers to those with round=-1 (no round in name)
    rounds = sorted(seen_paths.values(), key=lambda r: (r.round if r.round >= 0 else 999, r.report_path))
    # For the ones still at -1, assign sequential starting from max explicit + 1
    max_explicit = max((r.round for r in rounds if r.round >= 0), default=-1)
    counter = max_explicit + 1
    result = []
    for r in rounds:
        if r.round < 0:
            # create new dataclass with corrected round
            result.append(CodexRound(
                round=counter, verdict=r.verdict, p1=r.p1, p2=r.p2, p3=r.p3,
                report_path=r.report_path, missing=r.missing,
            ))
            counter += 1
        else:
            result.append(r)

    return sorted(result, key=lambda r: (r.round, r.report_path))


def _count_kogami_invocations() -> int:
    """Count kogami directories that contain invoke_meta.json."""
    if not KOGAMI_DIR.exists():
        return 0
    count = 0
    for subdir in KOGAMI_DIR.iterdir():
        if subdir.is_dir() and (subdir / "invoke_meta.json").exists():
            count += 1
    return count


def _find_kogami_for_dec(dec_id: str, body: str, fm: dict[str, Any]) -> KogamiRef | None:
    """
    Only populate if DEC frontmatter or body mentions 'kogami' AND
    we can fuzzy-match dec slug in a kogami directory name.
    """
    # Stringify fm values to avoid JSON serialization errors with date/datetime objects
    fm_str_values = {k: str(v) for k, v in fm.items()}
    combined = (json.dumps(fm_str_values) + body).lower()
    if "kogami" not in combined:
        return None
    if not KOGAMI_DIR.exists():
        return None

    # Build slug to look for in dir names
    slug = dec_id.lower().replace("dec-", "").replace("-", "_")
    slug_alt = dec_id.lower().replace("dec-", "")

    for subdir in KOGAMI_DIR.iterdir():
        if not subdir.is_dir():
            continue
        dname = subdir.name.lower()
        if slug in dname or slug_alt in dname:
            # Read verdict from review.json if present
            review_json = subdir / "review.json"
            verdict = "UNPARSED"
            if review_json.exists():
                try:
                    data = json.loads(review_json.read_text(encoding="utf-8"))
                    verdict = str(data.get("verdict", "UNPARSED"))
                except (json.JSONDecodeError, OSError):
                    verdict = "UNPARSED"
            return KogamiRef(topic=subdir.name, verdict=verdict)
    return None


def _load_one_arc(path: Path) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """
    Returns (frontmatter, body, date_str) or (None, None, None) on hard failure.
    date_str may be None if filename doesn't start with YYYY-MM-DD.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None, None
    fm, body = _parse_frontmatter(text)
    date_str = _parse_date(path.stem)
    return fm, body, date_str


# ---------- public API --------------------------------------------------------


def build_snapshot() -> CrewSnapshot:
    """Assemble the full CrewSnapshot (spec §2 GET /api/agent-crew)."""
    decisions_total = 0
    autonomous_total = 0
    loop_auditor_total = 0

    arcs: list[CrewArc] = []

    if DECISIONS_DIR.exists():
        for path in sorted(DECISIONS_DIR.glob("*.md")):
            fm, body, date_str = _load_one_arc(path)
            if fm is None:
                continue  # unreadable

            decisions_total += 1

            if fm is not None:
                if fm.get("autonomous_governance") is True:
                    autonomous_total += 1
                if "loop_auditor" in fm:
                    loop_auditor_total += 1

            if body is None:
                continue

            # Determine if this DEC qualifies for arcs list
            has_special_fields = "loop_auditor" in fm or "confidence" in fm
            passes_date = date_str is not None and date_str >= ARC_DATE_CUTOFF

            if not (passes_date or has_special_fields):
                continue

            if date_str is None:
                # Can't sort properly without date; skip for arcs
                continue

            dec_id_raw = str(fm.get("decision_id") or "").strip()
            if not dec_id_raw or not dec_id_raw.startswith("DEC-"):
                # No valid frontmatter decision_id — skip from arcs
                continue
            dec_id = dec_id_raw
            title = _extract_title(body)
            phase = fm.get("phase")
            autonomous = bool(fm.get("autonomous_governance", False))
            confidence = fm.get("confidence")
            loop_aud = fm.get("loop_auditor")
            codex_relay = fm.get("codex_review_relay")

            codex_rounds = _build_codex_rounds(fm, dec_id)
            kogami_ref = _find_kogami_for_dec(dec_id, body, fm)

            relative_path = str(path.relative_to(REPO_ROOT))

            arcs.append(CrewArc(
                decision_id=dec_id,
                title=title,
                date=date_str,
                phase=str(phase) if phase is not None else None,
                autonomous=autonomous,
                confidence=str(confidence) if confidence is not None else None,
                loop_auditor=str(loop_aud) if loop_aud is not None else None,
                codex_relay=str(codex_relay) if codex_relay is not None else None,
                codex_rounds=codex_rounds,
                kogami=kogami_ref,
                relative_path=relative_path,
            ))

    # Sort arcs by date descending, limit 80
    arcs.sort(key=lambda a: a.date, reverse=True)
    arcs = arcs[:ARC_LIMIT]

    # Count codex reports total
    codex_reports_total = 0
    if CODEX_REPORTS_DIR.exists():
        codex_reports_total = sum(1 for p in CODEX_REPORTS_DIR.iterdir() if p.is_file())

    kogami_total = _count_kogami_invocations()

    stats = CrewStats(
        decisions_total=decisions_total,
        codex_reports_total=codex_reports_total,
        autonomous_total=autonomous_total,
        loop_auditor_total=loop_auditor_total,
        kogami_total=kogami_total,
    )

    # Build roles with counts back-filled
    roles = []
    count_map = {
        "chief": autonomous_total,
        "codex": codex_reports_total,
        "loop_auditor": loop_auditor_total,
        "kogami": kogami_total,
        "archive": decisions_total,
    }
    for r in _STATIC_ROLES:
        role_count = count_map.get(r["id"], r["count"])
        roles.append(RoleNode(
            id=r["id"],
            label=r["label"],
            model=r["model"],
            desc=r["desc"],
            count_label=r["count_label"],
            count=role_count,
        ))

    return CrewSnapshot(
        roles=roles,
        edges=list(_STATIC_EDGES),
        arcs=arcs,
        stats=stats,
    )


def get_arc_detail(decision_id: str) -> ArcDetail | None:
    """
    Load full detail for a single DEC by decision_id.
    Returns None if not found. Raises ValueError on invalid id format.
    """
    if not DEC_ID_RE.match(decision_id):
        raise ValueError(f"Invalid decision_id format: {decision_id!r}")

    if not DECISIONS_DIR.exists():
        return None

    # Find the file whose frontmatter decision_id matches, or whose stem matches
    for path in sorted(DECISIONS_DIR.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, body = _parse_frontmatter(text)
        fm_id = str(fm.get("decision_id") or "").strip()
        stem_id = path.stem  # filename without extension

        if fm_id == decision_id or stem_id == decision_id:
            # Stringify all frontmatter values
            fm_str: dict[str, Any] = {k: str(v) for k, v in fm.items()}

            # Body excerpt: first 120 lines
            body_lines = body.splitlines()[:120]
            body_excerpt = "\n".join(body_lines)

            # Build reports
            codex_rounds = _build_codex_rounds(fm, decision_id)
            reports: list[ReportExcerpt] = []
            for cr in codex_rounds:
                abs_path = REPO_ROOT / cr.report_path
                if cr.missing or not abs_path.exists():
                    reports.append(ReportExcerpt(
                        round=cr.round,
                        path=cr.report_path,
                        excerpt="",
                        verdict="MISSING",
                        missing=True,
                    ))
                else:
                    report_text = abs_path.read_text(encoding="utf-8", errors="replace")
                    excerpt_lines = report_text.splitlines()[:100]
                    reports.append(ReportExcerpt(
                        round=cr.round,
                        path=cr.report_path,
                        excerpt="\n".join(excerpt_lines),
                        verdict=cr.verdict,
                        missing=False,
                    ))

            return ArcDetail(
                decision_id=decision_id,
                frontmatter=fm_str,
                body_excerpt=body_excerpt,
                reports=reports,
            )

    return None
