"""Audit-package builder — Phase 5 commercial V&V evidence bundle.

Per DEC-V61-002 Path B, Phase 5 delivers a one-click export of a CFD case's
full verification-and-validation evidence as a signed, byte-reproducible
bundle suitable for regulated-industry reviewers (FDA V&V40, aerospace
airworthiness, nuclear licensing).

Module layout (implemented across PR-5a → PR-5d):

- ``manifest`` (PR-5a, DEC-V61-012) — pure-function builder that assembles
  a deterministic dict from whitelist + gold + run outputs + measurement +
  decision trail. Pin every asset by git commit SHA. This module is the
  source of truth for "what went into the audit package".

- ``serialize`` (PR-5b, DEC-V61-013) — dict → byte-reproducible zip +
  human-readable PDF.

- ``sign`` (PR-5c, DEC-V61-014) — HMAC-SHA256 over manifest + zip with
  environment-var key; sidecar .sig file; round-trip verify.

- ``screen6`` (PR-5d, DEC-V61-015) — FastAPI route + React page wiring
  the above into the UI.

PR-5a public surface:
- :func:`build_manifest` — assemble the deterministic dict
- :data:`SCHEMA_VERSION` — manifest schema version integer

PR-5b public surface:
- :func:`serialize_zip` / :func:`serialize_zip_bytes` — byte-reproducible zip
- :func:`render_html` — deterministic HTML render (no external CDN)
- :func:`serialize_pdf` — optional weasyprint-backed PDF (may raise
  :class:`PdfBackendUnavailable` when native libs missing)
- :func:`is_pdf_backend_available` — non-raising availability probe
"""

from __future__ import annotations

from .manifest import SCHEMA_VERSION, build_manifest
from .serialize import (
    PdfBackendUnavailable,
    is_pdf_backend_available,
    render_html,
    serialize_pdf,
    serialize_zip,
    serialize_zip_bytes,
)

__all__ = [
    "SCHEMA_VERSION",
    "build_manifest",
    "PdfBackendUnavailable",
    "is_pdf_backend_available",
    "render_html",
    "serialize_pdf",
    "serialize_zip",
    "serialize_zip_bytes",
]
