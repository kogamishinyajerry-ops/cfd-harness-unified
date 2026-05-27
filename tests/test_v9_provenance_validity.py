"""V9 advisor-rule provenance VALIDITY guard (RETRO 2026-05-28, finding 2).

RS#32 (test_v9_pattern_matcher) pins that every rule has a NON-EMPTY provenance
string. This file adds the layer it could not: that a provenance *claim* is
VERIFIABLE. The 2026-05-28 retro found 5 of 8 then-shipped rules cited
FABRICATED provenance — non-existent `.md` files and `V<n>` corpus-row numbers
pointing at unrelated topics. They survived every prior review because nobody
dereferences a citation by eye, and the predicate tests only exercise matcher
behavior, not citation truth. A plausible-looking `docs/.../foo.md · V31` is
invisible to a diff read.

What is honestly checkable OFFLINE (and therefore enforced here):
  - Any repo-path token in a provenance string (a `.../something.md`) MUST
    resolve to a real file under the repo root.
  - Any `V<n>` corpus-row reference that co-occurs with a corpus path MUST
    exist as a `### V<n>` heading in one of the cited files.

What is deliberately NOT checked (and NOT faked — the same lesson as the
finding it guards): textbook section numbers (e.g. "Ferziger & Perić · §8.7")
cannot be verified without the book. This guard does not pretend to validate
them. A rule that cites a textbook concept loosely (no repo path) passes —
citing a real concept loosely is honest; citing a fake file *specifically* is
the failure mode this kills. The contract is: **if a provenance makes a
machine-checkable claim, that claim must be true.**
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from ui.backend.services.v9_advisor import V9_ADVISOR_RULES

REPO_ROOT = Path(__file__).resolve().parents[1]

# A repo-relative path token ending in a known doc extension. The class excludes
# the `·` provenance separator and whitespace, so a match stops at the file
# extension and never gobbles the trailing " · V3 (...)" descriptor.
_PATH_RE = re.compile(r"[\w./-]+\.(?:md|csv|json|yaml|yml)")

# A corpus-row reference: capital V followed by digits, on a word boundary.
# Does NOT match "v_series" (lowercase v) or "§8.7" (textbook section).
_VROW_RE = re.compile(r"\bV(\d+)\b")


def _cited_paths(provenance: str) -> list[str]:
    return _PATH_RE.findall(provenance)


def _cited_vrows(provenance: str) -> list[str]:
    return _VROW_RE.findall(provenance)


@pytest.mark.parametrize("rule", V9_ADVISOR_RULES, ids=lambda r: r.id)
def test_provenance_paths_resolve(rule):
    """Every repo-path cited in a rule's provenance must exist on disk.

    This is the exact failure the retro caught: a fabricated `.md` path that
    reads plausibly but resolves to nothing.
    """
    for path in _cited_paths(rule.provenance):
        resolved = REPO_ROOT / path
        assert resolved.is_file(), (
            f"rule {rule.id!r} provenance cites {path!r}, which does not resolve "
            f"to a real file under the repo root ({resolved}). A citation is a "
            f"claim — a path that does not exist is fabricated provenance."
        )


@pytest.mark.parametrize("rule", V9_ADVISOR_RULES, ids=lambda r: r.id)
def test_provenance_vrows_exist_in_cited_corpus(rule):
    """Any `V<n>` row cited alongside a corpus path must be a real heading.

    The retro's second fabrication mode: V-row numbers that point at unrelated
    corpus topics. We only enforce this when the provenance ALSO cites a
    resolvable corpus file (a bare textbook citation may legitimately mention a
    version-like token we cannot dereference).
    """
    paths = _cited_paths(rule.provenance)
    vrows = _cited_vrows(rule.provenance)
    if not vrows:
        return  # nothing to check
    if not paths:
        return  # no corpus file to dereference against; not a machine-checkable claim

    corpus_texts = []
    for path in paths:
        resolved = REPO_ROOT / path
        if resolved.is_file():
            corpus_texts.append(resolved.read_text(encoding="utf-8"))
    haystack = "\n".join(corpus_texts)

    for n in vrows:
        heading = re.compile(rf"^#+\s*V{n}\b", re.MULTILINE)
        assert heading.search(haystack), (
            f"rule {rule.id!r} provenance cites corpus row V{n}, but no "
            f"`### V{n}` heading exists in the cited file(s) {paths}. A V-row "
            f"reference must point at a real corpus finding, not an unrelated one."
        )


def test_at_least_one_rule_exercises_the_path_guard():
    """Guard against the guard silently testing nothing.

    If a future refactor strips all repo-path citations, the two parametrized
    tests above would pass vacuously. This pins that the corpus-path contract
    is actually exercised by >=1 rule (currently R9 cites the V-series corpus).
    """
    with_paths = [r.id for r in V9_ADVISOR_RULES if _cited_paths(r.provenance)]
    assert with_paths, (
        "no v9 rule cites a repo-path provenance — the resolvability guard is "
        "testing nothing. If this is intentional (all rules are textbook-only), "
        "delete this canary; otherwise a citation was dropped."
    )
