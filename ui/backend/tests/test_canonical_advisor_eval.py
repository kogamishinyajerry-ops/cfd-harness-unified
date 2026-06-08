"""V69.2 · canonical advisor eval regression harness.

Loads each of the 20 canonical eval case files in
`.planning/evals/canonical/E*.md`, parses (a) the YAML frontmatter and
(b) the expected-rule-firings table from the body, then asserts:

  1. Frontmatter schema parity with `validate_canonical_eval_schema.py`
  2. Every advisor named in the expected-firings table actually exists
     in `ui/backend/services/advisor_stack.py` (no typos · no removed
     advisors silently breaking the eval's regression protection).
  3. Each case has at least 3 expected rule firings (sanity: a canonical
     case that fires no rules at all isn't anchoring anything).
  4. Aggregate fire count across the 20 cases hits the V66-B INDEX.md
     ≥100-firings target (sentinel against advisor-stack regressions
     that would silently drop dispatches).

The harness is a static-analysis regression layer — it does NOT call
`assemble_stack` per case because the canonical eval files document
*expected* behavior (V-row attribution + rule firings), not full case
YAML/dict inputs. Pairing the harness with `assemble_stack`'s own unit
tests (`test_advisor_stack.py`, 31 tests) gives 2-layer protection:

  - test_advisor_stack.py: each advisor produces the right finding for
    a synthetic input
  - test_canonical_advisor_eval.py (this file): the canonical cases'
    expected advisor set is structurally well-formed and matches the
    actual advisor stack module surface

V69.2 charter §"Eval regression harness" runtime budget: ≤5s for all
20 tests. Static parsing keeps each ~10ms · total <500ms typical.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_DIR = REPO_ROOT / ".planning" / "evals" / "canonical"
ADVISOR_STACK_PATH = (
    REPO_ROOT / "ui" / "backend" / "services" / "advisor_stack.py"
)


def _list_canonical_files() -> list[Path]:
    """Return sorted list of E*.md case files (excludes _archive_batched)."""
    if not CANONICAL_DIR.is_dir():
        return []
    return sorted(
        p
        for p in CANONICAL_DIR.glob("E*.md")
        if p.is_file() and not p.name.startswith("_")
    )


def _parse_frontmatter(text: str) -> dict | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None
    try:
        loaded = yaml.safe_load("\n".join(lines[1:end_idx]))
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


_RULE_LINE_RE = re.compile(
    r"\|\s*`([a-z_][a-z0-9_]*?)(?:_advisor)?`\s*\|\s*(✓|✗)([^|]*)\|"
)


def _parse_rule_firings(text: str) -> list[tuple[str, str, str]]:
    """Extract (advisor_name, fire_or_skip, severity_hint) from body table.

    Lines like:
        | `inlet_outlet_validator` | ✓ info | inlet velocity profile |
        | `cf_canonical_choice_advisor` | ✗ | not flat BL |
    Returns list of tuples; advisor_name normalized without `_advisor` suffix
    so synonymous spellings (e.g. `solver_block` vs `solver_block_advisor`)
    collapse for cross-referencing the advisor stack surface.
    """
    out: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        m = _RULE_LINE_RE.search(line)
        if m:
            advisor = m.group(1)
            fire = m.group(2)
            rest = m.group(3).strip()
            severity = ""
            for tok in ("error", "warn", "info", "ERROR", "ANTI-FIRE", "MISSING"):
                if tok in rest:
                    severity = tok.lower()
                    break
            out.append((advisor, fire, severity))
    return out


# Planned-but-not-landed advisors. Appear in canonical eval case rule
# tables as expected fires; harness must NOT fail on them — they're
# documented F-NEW rule gaps awaiting a future arc to implement.
#
# V69 batch (V66-B inheritance): cf_canonical_choice / yplus_regime_match /
# yplus_target_validation / substrate_inspection / residual_gate_qualifier ·
# tracked in `.planning/followups/v69_v66b_planned_advisors_not_landed.md`.
# Note: low_re_kOmegaSST_trigger REMOVED from this list 2026-06-08 (DEC-V61-235
# landed low_re_komegasst_trigger_advisor; E21 row re-parsed under new
# lowercase token).
#
# V70 batch (V70.2 regime breadth · 11 new advisors anchoring 10 new cases):
# bc_type_validator / compressibility_regime_advisor / dimensionality_check /
# mesh_resolution_advisor / region_coupling_validator /
# separation_resolution_advisor / shock_capture_quality_advisor /
# statistics_averaging_advisor / symmetry_validator / timestep_validator /
# turbulence_model_advisor · tracked in
# `.planning/followups/v70_v70_2_planned_advisors_not_landed.md`.
KNOWN_F_NEW_ADVISORS: frozenset[str] = frozenset(
    {
        # V69 batch
        "cf_canonical_choice",
        "cf_canonical_choice_advisor",
        "yplus_regime_match",
        "yplus_regime_match_advisor",
        "yplus_target_validation",
        "yplus_target_validation_advisor",
        "substrate_inspection",
        "substrate_inspection_advisor",
        "residual_gate_qualifier",
        "residual_gate_qualifier_advisor",
        # V70 batch (V70.2 · regime breadth anchors)
        # Note: parser regex strips `_advisor` suffix when present, so for
        # *_advisor entries we also list the bare form to ensure KNOWN_F_NEW
        # lookup succeeds after suffix stripping.
        "bc_type_validator",
        "compressibility_regime",
        "compressibility_regime_advisor",
        "dimensionality_check",
        "mesh_resolution",
        "mesh_resolution_advisor",
        "region_coupling_validator",
        "separation_resolution",
        "separation_resolution_advisor",
        "shock_capture_quality",
        "shock_capture_quality_advisor",
        "statistics_averaging",
        "statistics_averaging_advisor",
        "symmetry_validator",
        "timestep_validator",
        "turbulence_model",
        "turbulence_model_advisor",
    }
)


@pytest.fixture(scope="module")
def advisor_surface() -> str:
    """Union of advisor_stack.py + every advisor module under
    ui/backend/services/. Used to validate that canonical-eval-referenced
    advisors exist *somewhere* in the codebase — not just inside the
    stack dispatcher.
    """
    chunks: list[str] = [ADVISOR_STACK_PATH.read_text(encoding="utf-8")]
    services_dir = ADVISOR_STACK_PATH.parent
    for advisor_path in services_dir.rglob("*advisor*.py"):
        if "__pycache__" in advisor_path.parts:
            continue
        try:
            chunks.append(advisor_path.read_text(encoding="utf-8"))
        except OSError:
            continue
    # Also fold in directory names (mesh_quality/, etc.)
    for sub in services_dir.iterdir():
        if sub.is_dir():
            chunks.append(sub.name)
    return "\n".join(chunks)


@pytest.fixture(scope="module")
def canonical_files() -> list[Path]:
    files = _list_canonical_files()
    assert len(files) == 30, (
        f"expected exactly 30 canonical eval case files (V70.2 expanded "
        f"from 20 to 30); got {len(files)}"
    )
    return files


# ---- Per-case parametrized tests (30 tests · one per case) ----------


@pytest.mark.parametrize(
    "case_idx",
    range(30),
    ids=[f"E{i + 1:02d}" for i in range(30)],
)
def test_canonical_case_well_formed(
    case_idx: int,
    canonical_files: list[Path],
    advisor_surface: str,
) -> None:
    """Each canonical eval case file passes 4 structural assertions.

    (1) Frontmatter parses + carries required fields.
    (2) eval_case_id matches filename prefix.
    (3) ≥3 expected rule firings parsed from body (anti-empty-anchor).
    (4) Every named advisor exists in advisor_stack.py source — catches
        typos + removed advisors that would silently break regression
        protection.
    """
    path = canonical_files[case_idx]
    text = path.read_text(encoding="utf-8")

    # (1) frontmatter
    fm = _parse_frontmatter(text)
    assert fm is not None, f"{path.name}: malformed YAML frontmatter"
    for field in (
        "eval_case_id",
        "case_id",
        "title",
        "v_row_attribution",
        "physics_regime",
        "status",
        "sandbox_path",
        "substrate_lineage",
        "expected_verdict_signature",
    ):
        assert field in fm, f"{path.name}: missing frontmatter field {field}"

    # (2) eval_case_id matches filename
    expected_prefix = path.stem.split("_")[0]
    assert fm["eval_case_id"] == expected_prefix, (
        f"{path.name}: eval_case_id={fm['eval_case_id']!r} doesn't match "
        f"filename prefix {expected_prefix!r}"
    )

    # (3) ≥3 expected rule firings (active or anti-fire) parsed
    firings = _parse_rule_firings(text)
    assert len(firings) >= 3, (
        f"{path.name}: only {len(firings)} rule firings parsed from body "
        f"table; canonical case should anchor ≥3 (case may be missing a "
        f"firings table or table format drifted)"
    )

    # (4) Every named advisor exists somewhere in the advisor surface
    # (advisor_stack.py + ui/backend/services/**advisor**.py + module dirs).
    # F-NEW MISSING rules tagged in the body or in KNOWN_F_NEW_ADVISORS
    # are intentionally absent — those are documented rule gaps for a
    # future arc to fill. The harness validates the actually-existing
    # advisors are not renamed/removed, NOT that all F-NEW rules have
    # landed.
    for advisor, _fire, _sev in firings:
        # Skip F-NEW MISSING entries (canonical doc convention)
        rule_lines = [
            l
            for l in text.splitlines()
            if f"`{advisor}`" in l or f"`{advisor}_advisor`" in l
        ]
        if any("MISSING" in l for l in rule_lines):
            continue
        if advisor in KNOWN_F_NEW_ADVISORS:
            continue
        candidates = (advisor, f"{advisor}_advisor")
        found = any(c in advisor_surface for c in candidates)
        assert found, (
            f"{path.name}: advisor {advisor!r} named in firings table "
            f"but not found anywhere in advisor surface "
            f"(advisor_stack.py + ui/backend/services/**advisor**.py). "
            f"Either typo / removed advisor, OR a planned F-NEW that "
            f"should be added to KNOWN_F_NEW_ADVISORS in this test file."
        )


# ---- Cross-cutting aggregate invariants -----------------------------


def test_aggregate_firing_count_meets_v66b_target(
    canonical_files: list[Path],
) -> None:
    """V66-B INDEX.md §"Target" mandated cumulative ≥100 firings across
    the original 20 canonical cases. V70.2 expanded to 30; threshold
    re-anchored to ≥140 (honest: new V70 cases average 4 firings each
    versus V66-B's ≈5-7 mean — V70.2 anchored *regime breadth* over
    per-case firing density). Guards against advisor coverage regression
    while preserving honest accounting of what the expansion delivered.
    """
    total_active = 0
    for path in canonical_files:
        firings = _parse_rule_firings(path.read_text(encoding="utf-8"))
        total_active += sum(1 for _adv, fire, _sev in firings if fire == "✓")
    assert total_active >= 140, (
        f"cumulative active firings = {total_active} < V70.2 target of "
        f"140 (was V66-B 100 for 20 cases) · advisor coverage may have regressed"
    )


def test_no_orphan_eval_case_ids(canonical_files: list[Path]) -> None:
    """The 30 canonical cases (V70.2 expanded from 20) must use ids
    E01..E30 with no gaps and no duplicates. Drift here = INDEX.md
    becomes wrong about which V-rows are covered.
    """
    ids = set()
    for path in canonical_files:
        fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
        assert fm is not None
        ids.add(fm["eval_case_id"])
    expected = {f"E{i:02d}" for i in range(1, 31)}
    missing = expected - ids
    extra = ids - expected
    assert not missing, f"missing eval_case_ids: {sorted(missing)}"
    assert not extra, f"unexpected eval_case_ids: {sorted(extra)}"
