"""DEC-V61-156 · N6 AI advisor stack (RAG-backed).

V130 advisory-only contract — this package is structurally locked OUT
of ``KNOWN_MUTATION_FUNCTIONS`` (V132). Any code path here is
read-only by construction; no symbol in this package writes to the
case directory or invokes a mutation function.

V1 surface (per N6.1 charter):
  * :func:`load_corpus` — walks ``docs/openfoam_corpus/`` +
    ``.planning/decisions/``, chunks markdown by section, returns
    in-memory :class:`Corpus`.
  * :func:`get_default_corpus` — process-singleton accessor; lazy
    on first call. Used by N6.2 / N6.3 routes.

Subsequent sub-DECs add:
  * N6.2 — ``query_review_findings`` route
  * N6.3 — ``query_diagnosis_hypotheses`` route
  * N6.5 — ``rule_based_fallback`` (consumes existing checkMesh /
    URF / timing / issue-list emitters)
"""
from __future__ import annotations

from ui.backend.services.ai_advisor.corpus_loader import (
    Corpus,
    LoadedChunk,
    get_default_corpus,
    load_corpus,
    reset_default_corpus,
)
from ui.backend.services.ai_advisor.diagnose import diagnose_case
from ui.backend.services.ai_advisor.review import review_case

__all__ = [
    "Corpus",
    "LoadedChunk",
    "load_corpus",
    "get_default_corpus",
    "reset_default_corpus",
    "diagnose_case",
    "review_case",
]
