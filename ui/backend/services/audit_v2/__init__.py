"""DEC-V61-154 (N5.3) · audit package V2 builder.

Public surface:
    build_provenance_manifest(case_dir) -> ProvenanceManifest
        Walk case state, compute all SHAs, return manifest.
    canonical_manifest_bytes(manifest) -> bytes
        Byte-reproducible serialization of the manifest (for HMAC
        signing). Excludes wall-clock authored_at field.
"""
from __future__ import annotations

from ui.backend.services.audit_v2.builder import (
    build_provenance_manifest,
    canonical_manifest_bytes,
)

__all__ = [
    "build_provenance_manifest",
    "canonical_manifest_bytes",
]
