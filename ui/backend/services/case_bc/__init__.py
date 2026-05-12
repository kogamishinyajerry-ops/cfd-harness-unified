"""DEC-V61-146 (N4.1) · structured per-patch BC writer.

Translates :class:`BCContract` into 0.orig/{U, p} dict files. v0
emits incompressible-isothermal cases only (U + p); thermal field
templates land in N4.5 / N4-extend.

Public surface:
    write_bc_dicts(case_dir, contract) -> dict[str, str]
        Atomically writes 0.orig/U + 0.orig/p; returns a dict of
        rel-path → text just written so the route layer can echo
        back to the engineer for verification.

V132 contract: this writer IS a mutator. It appears in
KNOWN_MUTATION_FUNCTIONS so AI dispatch paths cannot call it.
"""
from __future__ import annotations

from ui.backend.services.case_bc.writer import (
    BCWriterError,
    render_p_field,
    render_u_field,
    write_bc_dicts,
)

__all__ = [
    "BCWriterError",
    "render_p_field",
    "render_u_field",
    "write_bc_dicts",
]
