#!/usr/bin/env python3
"""§10.5 sampling-audit budget gate.

Authority chain:
  - DEC-V61-072 (sampling-audit anchor first execution · 2026-04-26)
  - DEC-V61-073 H3 (≤100k token cap per fire) + H1/A4 (7 audit-required surfaces)
  - Methodology v2.0 §10.5+§11 draft (`.planning/methodology/2026-04-26_v2_section_10_5_and_11_draft.md`)

This script is a *budget gate*, not the Codex caller. Before an operator
fires a sampling-audit Codex run, this script:

  1. Walks `git log` for the audit window (range arg or auto-detect since
     last `DEC-V61-*sampling.audit*` commit).
  2. Estimates the prompt token cost (rule preamble + per-commit diff load).
  3. Aborts with `EXCEEDS_BUDGET_CAP=<used>/<cap>` (exit 2) if estimate > cap.
  4. Optionally flags commits that touch the 7 §10.5.4a audit-required
     surfaces; the operator must include these in the audit even if the
     baseline window is otherwise quiet.

The cap default (100_000) matches DEC-V61-073 §10.5.4b. Override with `--cap`
or `SAMPLING_AUDIT_CAP` env var (raise temporarily; never lower silently —
lowering must land via DEC update to the methodology doc).

Token estimation uses `tiktoken cl100k_base` if importable, else falls back
to `len(text) / 4` (a conservative char-level proxy — Codex GPT-5.4 uses a
related BPE; the proxy slightly under-counts for code-heavy diffs, which is
why we abort on the estimate before sending).

§10.5.4a audit-required surfaces (7 total, per DEC-V61-073 H1+A4):

  1. `FoamAgentExecutor.execute(` call sites outside trust-core 5 modules
  2. Docker / subprocess reachability changes (`subprocess.`, `docker `, `volumes:`)
  3. `/api/**` route registration under `ui/backend/routes/`
  4. `reports/` durable persistence (path-creation under `reports/`)
  5. `user_drafts/` → `TaskSpec` plumbing (touch on `user_drafts/` + `TaskSpec`)
  6. `correction_spec/` write paths (`reports/{case}/correction_specs/` + `knowledge/correction_patterns/`)
  7. `.planning/case_profiles/` write paths

Trust-core 5 modules (NEVER counted in this audit per §10):
  src/gold_standards/, src/auto_verifier/, src/convergence_attestor.py,
  src/audit_package/, src/foam_agent_adapter.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

DEFAULT_CAP_TOKENS = 100_000

TRUST_CORE_PATHS = (
    "src/gold_standards/",
    "src/auto_verifier/",
    "src/convergence_attestor.py",
    "src/audit_package/",
    "src/foam_agent_adapter.py",
)

# §10.5.4a audit-required surfaces, encoded as (label, regex against unified diff body)
# Order matches the methodology doc surface numbering.
AUDIT_REQUIRED_SURFACES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "1.FoamAgentExecutor_call_sites",
        re.compile(r"FoamAgentExecutor\s*\.\s*execute\s*\("),
    ),
    (
        "2.Docker_subprocess_reachability",
        re.compile(
            r"\bsubprocess\.(run|Popen|call|check_output)\b"
            r"|docker\s+(run|exec|build|compose)"
            r"|^[+-]\s*volumes:\s*$"
            r"|^[+-]\s*(image|container_name):",
            re.MULTILINE,
        ),
    ),
    (
        "3.api_route_registration",
        re.compile(
            r"^[+-]\s*(@router\.(get|post|put|patch|delete)|router\s*=\s*APIRouter)"
            r"|^\+\+\+\s+b/ui/backend/routes/",
            re.MULTILINE,
        ),
    ),
    (
        "4.reports_durable_persistence",
        re.compile(
            r"^\+\+\+\s+b/reports/"
            r"|reports\s*/\s*\{[^}]*case[^}]*\}"
            r"|Path\([^)]*['\"]reports/",
            re.MULTILINE,
        ),
    ),
    (
        "5.user_drafts_to_TaskSpec",
        re.compile(r"user_drafts/.*TaskSpec|TaskSpec.*user_drafts/", re.DOTALL),
    ),
    (
        "6.correction_spec_write_paths",
        re.compile(
            r"^\+\+\+\s+b/reports/[^/]+/correction_specs/"
            r"|^\+\+\+\s+b/knowledge/correction_patterns/"
            r"|reports/[^/\s]+/correction_specs/"
            r"|knowledge/correction_patterns/",
            re.MULTILINE,
        ),
    ),
    (
        "7.case_profiles_write_paths",
        re.compile(
            r"^\+\+\+\s+b/\.planning/case_profiles/"
            r"|\.planning/case_profiles/[^/\s]+\.ya?ml",
            re.MULTILINE,
        ),
    ),
)


@dataclass
class AuditWindow:
    """Result of estimating the sampling-audit prompt cost for a git range."""

    git_range: str
    commits: list[str]
    non_trust_core_commits: list[str]
    diff_chars: int
    estimated_tokens: int
    cap: int
    surfaces_flagged: dict[str, list[str]] = field(default_factory=dict)

    @property
    def verdict(self) -> str:
        return "EXCEEDS_BUDGET_CAP" if self.estimated_tokens > self.cap else "OK"

    @property
    def message(self) -> str:
        if self.verdict == "EXCEEDS_BUDGET_CAP":
            return f"EXCEEDS_BUDGET_CAP={self.estimated_tokens}/{self.cap}"
        return f"OK={self.estimated_tokens}/{self.cap}"


def _git(*args: str, cwd: Path | None = None) -> str:
    """Run a git command and return stdout (raises on non-zero exit)."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _last_sampling_audit_sha(cwd: Path | None = None) -> str | None:
    """Find the most recent commit referencing a DEC-V61-*sampling.audit*."""
    out = _git(
        "log",
        "--format=%H",
        "--grep=DEC-V61-.*sampling.audit",
        "main",
        cwd=cwd,
    ).strip()
    if not out:
        return None
    return out.splitlines()[0]


def _resolve_default_range(cwd: Path | None = None) -> str:
    """Pick the default audit window when --range is not provided.

    Prefer the last sampling-audit DEC commit as the lower bound; otherwise
    fall back to the last 50 commits (matches the GHA reminder fetch-depth).
    """
    sha = _last_sampling_audit_sha(cwd=cwd)
    if sha:
        return f"{sha}..HEAD"
    return "HEAD~50..HEAD"


def _commits_in_range(git_range: str, cwd: Path | None = None) -> list[str]:
    raw = _git("log", git_range, "--format=%H", cwd=cwd).strip()
    return [line for line in raw.splitlines() if line]


def _commit_touches_trust_core(sha: str, cwd: Path | None = None) -> bool:
    """True iff the commit modifies any trust-core 5 module path."""
    files = _git("show", "--name-only", "--format=", sha, cwd=cwd).strip().splitlines()
    for f in files:
        for tc in TRUST_CORE_PATHS:
            if f.startswith(tc):
                return True
    return False


def _commit_diff_text(sha: str, cwd: Path | None = None) -> str:
    """Return the unified diff body for `sha` (used for surface detection +
    char-cost accounting). Excludes the commit message preamble."""
    return _git("show", "--no-color", "--format=", sha, cwd=cwd)


def estimate_tokens(text: str) -> int:
    """Estimate token count.

    Uses `tiktoken cl100k_base` if available; falls back to `len(text) / 4`
    rounded up. The fallback is intentionally conservative (under-counts
    slightly for code) — that matches our cap-as-pre-flight intent: if the
    estimate is at the cap, the actual call may run over, so we abort.
    """
    try:  # pragma: no cover - exercised when tiktoken is installed
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # char/4 fallback (English ≈ 4 chars/token; code slightly fewer).
        return (len(text) + 3) // 4


def detect_surfaces(diff_text: str) -> list[str]:
    """Return list of audit-required surface labels matched in `diff_text`."""
    matched: list[str] = []
    for label, pattern in AUDIT_REQUIRED_SURFACES:
        if pattern.search(diff_text):
            matched.append(label)
    return matched


# Rule preamble — counted toward every fire's token budget. Stable text so
# tokenizer drift across versions doesn't flip the estimate dramatically.
_RULE_PREAMBLE_TEMPLATE = """\
# §10 治理降级 + §10.5 sampling-audit retroactive 1-round Codex audit

You are auditing the following commit window for blind spots in the §10
degradation rule. The trust-core 5 modules are excluded from §10 — they
are reviewed at every commit. This audit looks for:

1. Boundary violations (any commit indirectly mutating trust-core state)
2. Operator-layer security/auth (signed endpoints, /api routes, auth)
3. Cross-file mechanical refactor (rename across ≥3 files)
4. Reproducibility-determinism (timestamps, idempotent overwrite, partial-write)
5. Solver-stability on novel input (user_drafts → TaskSpec, geometry classes)

§10.5.4a pre-flagged audit-required surfaces (7 total):
  1. FoamAgentExecutor call sites outside trust-core 5
  2. Docker / subprocess reachability changes
  3. /api/** route registration
  4. reports/ durable persistence
  5. user_drafts/ → TaskSpec plumbing
  6. correction_spec/ write paths (DEC-V61-073 A4)
  7. .planning/case_profiles/ write paths (DEC-V61-073 A4)

Output verdicts: CLEAN | BLIND_SPOTS_IDENTIFIED | DEGRADATION_RULE_AT_RISK.
Land DEC-V61-XXX-SAMPLING-AUDIT-N. Recall mechanics apply only to verdict 3.

Audit window: {git_range}
Commits in window: {n_commits} ({n_non_trust_core} non-trust-core)
"""


def build_audit_window(
    git_range: str | None = None,
    cap: int = DEFAULT_CAP_TOKENS,
    cwd: Path | None = None,
) -> AuditWindow:
    """Build the AuditWindow for `git_range` (or auto-detect default).

    The returned object's `verdict` field tells the caller whether to proceed.
    """
    if git_range is None:
        git_range = _resolve_default_range(cwd=cwd)

    commits = _commits_in_range(git_range, cwd=cwd)
    non_trust_core: list[str] = []
    diff_text_total = ""
    surfaces_flagged: dict[str, list[str]] = {}

    for sha in commits:
        if _commit_touches_trust_core(sha, cwd=cwd):
            continue
        non_trust_core.append(sha)
        diff = _commit_diff_text(sha, cwd=cwd)
        diff_text_total += diff
        labels = detect_surfaces(diff)
        for label in labels:
            surfaces_flagged.setdefault(label, []).append(sha)

    preamble = _RULE_PREAMBLE_TEMPLATE.format(
        git_range=git_range,
        n_commits=len(commits),
        n_non_trust_core=len(non_trust_core),
    )
    estimated = estimate_tokens(preamble + diff_text_total)

    return AuditWindow(
        git_range=git_range,
        commits=commits,
        non_trust_core_commits=non_trust_core,
        diff_chars=len(diff_text_total),
        estimated_tokens=estimated,
        cap=cap,
        surfaces_flagged=surfaces_flagged,
    )


def _serialize(window: AuditWindow) -> dict:
    """JSON-friendly view of the window result."""
    payload = asdict(window)
    payload["verdict"] = window.verdict
    payload["message"] = window.message
    return payload


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="§10.5 sampling-audit budget gate (DEC-V61-073 H3)."
    )
    parser.add_argument(
        "--range",
        dest="git_range",
        default=None,
        help="Git revision range (e.g. abc123..HEAD). Auto-detects from "
        "last DEC-V61-*sampling.audit* commit if omitted.",
    )
    parser.add_argument(
        "--cap",
        type=int,
        default=int(os.environ.get("SAMPLING_AUDIT_CAP", DEFAULT_CAP_TOKENS)),
        help=f"Token budget cap (default {DEFAULT_CAP_TOKENS}). "
        "Per DEC-V61-073 §10.5.4b, lowering must land via DEC update.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full JSON payload to stdout instead of human-readable summary.",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Repository working directory (defaults to current dir).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    window = build_audit_window(
        git_range=args.git_range, cap=args.cap, cwd=args.cwd
    )

    if args.json:
        print(json.dumps(_serialize(window), indent=2))
    else:
        print(f"sampling-audit budget gate · range={window.git_range}")
        print(
            f"  commits={len(window.commits)} "
            f"non_trust_core={len(window.non_trust_core_commits)} "
            f"diff_chars={window.diff_chars}"
        )
        print(f"  estimated_tokens={window.estimated_tokens} cap={window.cap}")
        if window.surfaces_flagged:
            print("  §10.5.4a surfaces flagged:")
            for label, shas in sorted(window.surfaces_flagged.items()):
                short = ", ".join(s[:7] for s in shas[:5])
                more = "" if len(shas) <= 5 else f" (+{len(shas) - 5} more)"
                print(f"    - {label}: {short}{more}")
        print(f"  verdict={window.verdict}")
        print(f"  {window.message}")

    return 2 if window.verdict == "EXCEEDS_BUDGET_CAP" else 0


if __name__ == "__main__":
    sys.exit(main())
