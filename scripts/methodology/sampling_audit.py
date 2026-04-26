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
            # check_call added per Codex PC-3 R1 false-negative finding.
            r"\bsubprocess\.(run|Popen|call|check_call|check_output)\b"
            r"|docker\s+(run|exec|build|compose)"
            r"|^[+-]\s*volumes:\s*$"
            r"|^[+-]\s*(image|container_name):",
            re.MULTILINE,
        ),
    ),
    (
        # Surface 3 detects route registration by *body* signal (decorator
        # or APIRouter call) so that doc-only edits in ui/backend/routes/
        # do not trigger a false-positive flag (Codex PC-3 R1 finding).
        # The diff-header path was the cause of the false positive.
        "3.api_route_registration",
        re.compile(
            r"^[+-]\s*(@router\.(get|post|put|patch|delete)"
            r"|router\s*=\s*APIRouter"
            r"|router\s*\.\s*add_api_route"
            r"|app\s*\.\s*include_router)",
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
    """Result of estimating the sampling-audit prompt cost for a git range.

    `non_trust_core_commits` includes both pure-non-trust-core commits AND
    "mixed" commits (touching both layers). For mixed commits, only the
    non-trust-core file portion of the diff contributes to `diff_chars` and
    surface detection — the trust-core portion is excluded per §10 baseline
    (it is reviewed at every commit, not via §10.5 sampling).

    `mixed_commits` lists the SHAs of mixed commits so the operator can
    audit them with awareness of the partial-diff scope.
    """

    git_range: str
    commits: list[str]
    non_trust_core_commits: list[str]
    diff_chars: int
    estimated_tokens: int
    cap: int
    surfaces_flagged: dict[str, list[str]] = field(default_factory=dict)
    mixed_commits: list[str] = field(default_factory=list)

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
    """Find the most recent commit referencing a DEC-V61-*sampling.audit*.

    Tries `main` first; falls back to walking from `HEAD` if `main` is not
    available (worktrees, detached state, repos without a main branch —
    Codex PC-3 R1 robustness finding).
    """
    for revision in ("main", "HEAD"):
        try:
            out = _git(
                "log",
                "--format=%H",
                "--grep=DEC-V61-.*sampling.audit",
                revision,
                cwd=cwd,
            ).strip()
        except subprocess.CalledProcessError:
            continue
        if out:
            return out.splitlines()[0]
    return None


def _resolve_default_range(cwd: Path | None = None) -> str:
    """Pick the default audit window when --range is not provided.

    Prefer the last sampling-audit DEC commit as the lower bound; otherwise
    fall back to the last 50 commits (matches the GHA reminder fetch-depth),
    capped at the actual commit count to avoid `git log HEAD~50..HEAD`
    crashing on shallow / short histories (Codex PC-3 R1 finding).
    """
    sha = _last_sampling_audit_sha(cwd=cwd)
    if sha:
        return f"{sha}..HEAD"
    try:
        total = int(_git("rev-list", "--count", "HEAD", cwd=cwd).strip() or "0")
    except subprocess.CalledProcessError:
        total = 0
    if total <= 1:
        return "HEAD"
    lookback = min(50, max(total - 1, 1))
    return f"HEAD~{lookback}..HEAD"


def _commits_in_range(git_range: str, cwd: Path | None = None) -> list[str]:
    # `log <range>` for a single ref (e.g. "HEAD") returns the full history;
    # we only want the tip in that case so the audit window stays sized.
    if git_range == "HEAD":
        try:
            sha = _git("rev-parse", "HEAD", cwd=cwd).strip()
        except subprocess.CalledProcessError:
            return []
        return [sha] if sha else []
    raw = _git("log", git_range, "--format=%H", cwd=cwd).strip()
    return [line for line in raw.splitlines() if line]


def _commit_touched_files(sha: str, cwd: Path | None = None) -> list[str]:
    """List of repo-relative file paths the commit modified."""
    raw = _git("show", "--name-only", "--format=", sha, cwd=cwd).strip()
    return [line for line in raw.splitlines() if line]


def _is_trust_core_path(file_path: str) -> bool:
    """True iff file_path is under any TRUST_CORE_PATHS entry."""
    return any(file_path.startswith(tc) for tc in TRUST_CORE_PATHS)


def _commit_classification(sha: str, cwd: Path | None = None) -> tuple[bool, bool]:
    """Return (touches_non_trust_core, touches_trust_core) for `sha`.

    A "mixed" commit returns (True, True) — Codex PC-3 R1 HIGH finding fix:
    we no longer drop mixed commits entirely; the non-trust-core portion is
    audited and the trust-core portion is excluded from the diff load.
    """
    touches_ntc = touches_tc = False
    for f in _commit_touched_files(sha, cwd=cwd):
        if _is_trust_core_path(f):
            touches_tc = True
        else:
            touches_ntc = True
        if touches_ntc and touches_tc:
            break
    return touches_ntc, touches_tc


def _commit_non_trust_core_diff(sha: str, cwd: Path | None = None) -> str:
    """Return the unified diff body for `sha`, restricted to the
    non-trust-core file set.

    Trust-core file diffs are excluded from the audit window (they are
    reviewed at every commit per §10 baseline). Files outside trust-core
    are passed straight to `git show` via pathspec exclusion magic.
    """
    pathspec_excludes = [f":(exclude){tc}" for tc in TRUST_CORE_PATHS]
    return _git(
        "show",
        "--no-color",
        "--format=",
        sha,
        "--",
        ".",
        *pathspec_excludes,
        cwd=cwd,
    )


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
    mixed: list[str] = []
    diff_text_total = ""
    surfaces_flagged: dict[str, list[str]] = {}

    for sha in commits:
        touches_ntc, touches_tc = _commit_classification(sha, cwd=cwd)
        if not touches_ntc:
            # Pure trust-core commit — excluded from §10.5 sampling per §10
            # baseline (reviewed at every commit anyway).
            continue
        non_trust_core.append(sha)
        if touches_tc:
            mixed.append(sha)
        diff = _commit_non_trust_core_diff(sha, cwd=cwd)
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
        mixed_commits=mixed,
    )


def _serialize(window: AuditWindow) -> dict:
    """JSON-friendly view of the window result."""
    payload = asdict(window)
    payload["verdict"] = window.verdict
    payload["message"] = window.message
    return payload


CAP_LOWER_REJECTED_EXIT = 3


def _resolve_and_validate_cap(arg_cap: int | None) -> tuple[int, str | None]:
    """Resolve the effective cap from --cap > env > default, and refuse
    values lower than DEFAULT_CAP_TOKENS (Codex PC-3 R1 LOW finding).

    Returns (cap, error_message). error_message is non-None iff the
    caller-supplied value violated the raise-only policy; the caller
    must surface it to stderr and exit with CAP_LOWER_REJECTED_EXIT.
    """
    env_raw = os.environ.get("SAMPLING_AUDIT_CAP")
    env_cap: int | None = None
    if env_raw is not None:
        try:
            env_cap = int(env_raw)
        except ValueError:
            return DEFAULT_CAP_TOKENS, (
                f"SAMPLING_AUDIT_CAP={env_raw!r} is not an integer"
            )

    # Precedence: --cap (if explicitly given) > env > default.
    effective = arg_cap if arg_cap is not None else (
        env_cap if env_cap is not None else DEFAULT_CAP_TOKENS
    )
    if effective < DEFAULT_CAP_TOKENS:
        source = "--cap" if arg_cap is not None else "SAMPLING_AUDIT_CAP env"
        return DEFAULT_CAP_TOKENS, (
            f"{source}={effective} is below DEFAULT_CAP_TOKENS={DEFAULT_CAP_TOKENS}; "
            f"per DEC-V61-073 §10.5.4b, lowering the cap must land via a "
            f"methodology DEC update — overrides are raise-only."
        )
    return effective, None


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
        default=None,
        help=f"Token budget cap (default {DEFAULT_CAP_TOKENS}; also via "
        "SAMPLING_AUDIT_CAP env). Per DEC-V61-073 §10.5.4b, raise-only — "
        f"values below {DEFAULT_CAP_TOKENS} are rejected.",
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

    effective_cap, cap_error = _resolve_and_validate_cap(args.cap)
    if cap_error is not None:
        print(f"ERROR: {cap_error}", file=sys.stderr)
        return CAP_LOWER_REJECTED_EXIT

    window = build_audit_window(
        git_range=args.git_range, cap=effective_cap, cwd=args.cwd
    )

    is_over_cap = window.verdict == "EXCEEDS_BUDGET_CAP"

    if args.json:
        # In JSON mode the literal contract message
        # `EXCEEDS_BUDGET_CAP=<used>/<cap>` MUST still appear on stderr so
        # log scrapers and CI gates can grep it without parsing JSON
        # (Codex PC-3 R1 MED finding).
        print(json.dumps(_serialize(window), indent=2))
        if is_over_cap:
            print(window.message, file=sys.stderr)
    else:
        print(f"sampling-audit budget gate · range={window.git_range}")
        ntc_count = len(window.non_trust_core_commits)
        mixed_count = len(window.mixed_commits)
        if mixed_count:
            print(
                f"  commits={len(window.commits)} "
                f"non_trust_core={ntc_count} (mixed={mixed_count}) "
                f"diff_chars={window.diff_chars}"
            )
        else:
            print(
                f"  commits={len(window.commits)} "
                f"non_trust_core={ntc_count} "
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

    return 2 if is_over_cap else 0


if __name__ == "__main__":
    sys.exit(main())
