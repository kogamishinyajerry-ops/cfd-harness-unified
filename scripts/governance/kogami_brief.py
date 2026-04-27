#!/usr/bin/env python3
"""P-2: build a Kogami subprocess prompt from a target artifact + canonical context bundle.

Per DEC-V61-087 §3.2: subprocess input space = (embedded prompt string) + base 31k system prompt.
This script builds the embedded prompt string deterministically.

Inputs (whitelist — anything else is forbidden by §3.2):
  - .planning/PROJECT.md (if exists)
  - .planning/ROADMAP.md
  - .planning/STATE.md (frontmatter + body summary ≤500 tokens)
  - the artifact under review (full text)
  - last N=5 DECs (Why + Decision sections only, not frontmatter or Codex round details)
  - all RETROs in the current milestone
  - methodology files marked "Active" in STATE.md frontmatter
  - .claude/agents/kogami-claude-cosplay.md (P-1 system prompt)

Outputs:
  - prompt.txt          (the full prompt to feed claude -p stdin)
  - briefing_manifest.json (sources + hashes for reproducibility)
  - prompt_sha256.txt   (sha256 of prompt.txt for deterministic-input proof)

Usage:
    python3 scripts/governance/kogami_brief.py \
        --artifact <path> \
        --output-dir <out_dir> \
        --trigger <trigger_reason>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BRIEFING_VERSION = "1.0"
SCRIPT_PATH = Path(__file__).resolve()


# ──────────────────────────────────────────────────────────────────────────
# File loaders (each is a single deterministic transform)
# ──────────────────────────────────────────────────────────────────────────


def file_sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def script_self_sha256() -> str:
    return file_sha256(SCRIPT_PATH)


def load_text(p: Path) -> str:
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body) for a markdown file. Empty fm if none."""
    if not text.startswith("---\n"):
        return "", text
    try:
        end = text.index("\n---\n", 4)
    except ValueError:
        return "", text
    return text[4:end], text[end + 5 :]


def state_summary(state_md: Path, max_chars: int = 2000) -> str:
    """Extract STATE.md frontmatter (full) + body head (capped). Stable across runs."""
    text = load_text(state_md)
    fm, body = parse_frontmatter(text)
    return f"---\n{fm}\n---\n\n{body[:max_chars]}"


def methodology_active(state_md: Path) -> list[Path]:
    """Resolve `methodology_active_sections` references from STATE.md frontmatter to file paths."""
    text = load_text(state_md)
    fm, _ = parse_frontmatter(text)
    paths = []
    for line in fm.splitlines():
        # Matches: `  - "§10.5 sampling audit anchor (Active · DEC-V61-073 PC-3 closure 2026-04-26)"`
        m = re.match(r'\s*-\s+"(§[\d\.a-z]+)\s+', line)
        if not m:
            continue
        # Active sections live under .planning/methodology/. Best-effort glob.
        for f in sorted(Path(".planning/methodology").glob("*.md")):
            paths.append(f)
        break  # all methodology files captured once
    # dedupe preserve order
    seen = set()
    out = []
    for p in paths:
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out


def recent_decs(n: int = 5, exclude_path: Path | None = None) -> list[Path]:
    """Return the N most recent DEC files by filename sort (which is date-prefixed)."""
    decs = sorted(Path(".planning/decisions").glob("*.md"), reverse=True)
    decs = [d for d in decs if not d.name.startswith("g9_") and not d.name.endswith("_DRAFT.md")]
    if exclude_path:
        decs = [d for d in decs if d.resolve() != exclude_path.resolve()]
    return decs[:n]


def dec_why_decision(dec_path: Path) -> str:
    """Extract just the ## Why and ## Decision sections from a DEC. Drop frontmatter, drop later sections."""
    text = load_text(dec_path)
    _, body = parse_frontmatter(text)
    # Find ## Why ... and ## Decision ... up to next H2
    out = []
    sections = re.split(r"(^##\s+\S.*$)", body, flags=re.MULTILINE)
    keep = False
    keep_titles = ("## Why", "## Decision")
    for chunk in sections:
        if chunk.startswith("##"):
            keep = chunk.strip().startswith(keep_titles)
            if keep:
                out.append(chunk)
        elif keep:
            out.append(chunk)
    return "".join(out).strip() or f"<DEC {dec_path.name} has no extractable Why/Decision section>"


def current_milestone_retros(state_md: Path) -> list[Path]:
    """Return all RETRO files for the current milestone (best effort: all .planning/retrospectives/*.md
    since milestone start)."""
    text = load_text(state_md)
    fm, _ = parse_frontmatter(text)
    # Identify milestone — best-effort, not critical
    return sorted(Path(".planning/retrospectives").glob("*.md"))


# ──────────────────────────────────────────────────────────────────────────
# Prompt assembly
# ──────────────────────────────────────────────────────────────────────────


def build_prompt(
    artifact_path: Path,
    trigger: str,
    p1_system_prompt: Path = Path(".claude/agents/kogami-claude-cosplay.md"),
) -> tuple[str, dict]:
    """Build the full Kogami subprocess prompt + manifest.

    Returns (prompt_text, manifest_dict).
    """
    sources: list[dict] = []

    def add_source(label: str, p: Path, content: str) -> str:
        """Record source in manifest, return content for embedding."""
        if not p.exists():
            sources.append({"label": label, "original_path": str(p), "present": False})
            return ""
        sources.append(
            {
                "label": label,
                "original_path": str(p),
                "present": True,
                "sha256": file_sha256(p),
                "bytes": p.stat().st_size,
            }
        )
        return content

    p1_text = add_source("P-1 system prompt", p1_system_prompt, load_text(p1_system_prompt))
    if not p1_text:
        sys.exit(f"FATAL: P-1 system prompt not found at {p1_system_prompt}")

    artifact_text = add_source("artifact_under_review", artifact_path, load_text(artifact_path))
    if not artifact_text:
        sys.exit(f"FATAL: artifact not found at {artifact_path}")

    project_text = add_source("PROJECT.md", Path(".planning/PROJECT.md"), load_text(Path(".planning/PROJECT.md")))
    roadmap_text = add_source("ROADMAP.md", Path(".planning/ROADMAP.md"), load_text(Path(".planning/ROADMAP.md")))
    state_text = add_source("STATE.md (summary)", Path(".planning/STATE.md"), state_summary(Path(".planning/STATE.md")))

    recent_dec_paths = recent_decs(n=5, exclude_path=artifact_path)
    recent_dec_blocks = []
    for p in recent_dec_paths:
        block_text = dec_why_decision(p)
        recorded = add_source(f"recent_dec_{p.name}", p, block_text)
        if recorded:
            recent_dec_blocks.append(f"### {p.name}\n\n{recorded}\n")

    retro_paths = current_milestone_retros(Path(".planning/STATE.md"))
    retro_blocks = []
    for p in retro_paths:
        recorded = add_source(f"retro_{p.name}", p, load_text(p))
        if recorded:
            retro_blocks.append(f"### {p.name}\n\n{recorded}\n")

    methodology_paths = methodology_active(Path(".planning/STATE.md"))
    methodology_blocks = []
    for p in methodology_paths:
        recorded = add_source(f"methodology_{p.name}", p, load_text(p))
        if recorded:
            methodology_blocks.append(f"### {p.name}\n\n{recorded}\n")

    # Assemble prompt — system prompt first, then user message body.
    # NOTE: claude -p doesn't have a separate --system-prompt flag here; we embed P-1
    # into the prompt as a leading "ROLE BRIEFING" block, and rely on Kogami's own
    # adherence (per P-1 instructions). If --append-system-prompt is later useful,
    # P-1.5 wrapper can pivot.
    prompt = f"""=== ROLE BRIEFING (P-1) ===
{p1_text}

=== TRIGGER ===
{trigger}

=== ARTIFACT UNDER REVIEW ===
File: {artifact_path}
SHA256: {file_sha256(artifact_path)}

```
{artifact_text}
```

=== CONTEXT BUNDLE ===

#### PROJECT.md (if present)
{project_text or '<not present>'}

#### ROADMAP.md
{roadmap_text or '<not present>'}

#### STATE.md (frontmatter + body summary)
{state_text or '<not present>'}

#### Recent DECs (Why + Decision sections only)

{chr(10).join(recent_dec_blocks) if recent_dec_blocks else '<no recent DECs found>'}

#### Current milestone RETROs

{chr(10).join(retro_blocks) if retro_blocks else '<no RETROs found>'}

#### Active methodology sections

{chr(10).join(methodology_blocks) if methodology_blocks else '<no methodology files found>'}

=== END BRIEFING ===

Now produce your review as a single JSON object on stdout, matching the schema in
the ROLE BRIEFING. No prose outside the JSON. No code fences.
"""

    manifest = {
        "kogami_briefing_version": BRIEFING_VERSION,
        "briefing_script_sha256": script_self_sha256(),
        "section_selection_rules_version": "1.0",
        "summary_algorithm_version": "1.0",
        "trigger": trigger,
        "artifact_under_review": str(artifact_path),
        "sources": sources,
    }

    return prompt, manifest


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", type=Path, required=True, help="path to artifact under review")
    ap.add_argument("--output-dir", type=Path, required=True, help="where to write prompt.txt + manifest")
    ap.add_argument("--trigger", type=str, required=True, help="trigger reason (e.g. 'phase-close', 'retro-draft', 'pr-review')")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    prompt, manifest = build_prompt(args.artifact, args.trigger)

    prompt_path = args.output_dir / "prompt.txt"
    manifest_path = args.output_dir / "briefing_manifest.json"
    sha_path = args.output_dir / "prompt_sha256.txt"

    prompt_path.write_text(prompt, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    sha_path.write_text(prompt_sha + "\n")

    print(f"[brief] artifact: {args.artifact}")
    print(f"[brief] sources counted: {len(manifest['sources'])}")
    print(f"[brief] prompt bytes: {len(prompt)}")
    print(f"[brief] prompt sha256: {prompt_sha}")
    print(f"[brief] output: {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
