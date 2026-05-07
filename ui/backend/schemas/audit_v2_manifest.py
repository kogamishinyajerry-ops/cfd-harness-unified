"""DEC-V61-154 (N5.3) · audit package V2 provenance manifest.

Captures per-case provenance: case state SHA + solver log SHA +
figure SHAs + DEC trail. Designed for byte-reproducibility — same
case state on disk produces identical manifest SHA across two
builds (excluding wall-clock fields, which are explicitly excluded
from the canonical-bytes representation).

Reuses the existing HMAC infrastructure in `src/audit_package/sign.py`
(DEC-V61-014) — does NOT introduce a new secret per charter §threat-
model row 3.

Wire shape:

    ProvenanceManifest
      schema_version: Literal["v2"]
      case_id: str
      case_state_sha: str          # SHA-256 of canonical case-state bytes
      solver_log_sha: str | None   # SHA-256 of run-log file (None when
                                   # solver hasn't run yet)
      figure_shas: dict[str, str]  # filename → SHA for every figure
                                   # in postProcessing/<case>/figures/
      dec_trail: list[str]         # ordered list of DEC IDs that
                                   # produced this case state
      authored_at: str             # ISO 8601 UTC (NOT in canonical bytes)
      authored_at_excluded_from_canonical: bool = True
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


_SHA256_HEX_LEN = 64
_SHA256_HEX_RE_HINT = "must be 64-char lowercase hex (SHA-256 hex digest)"


class ProvenanceManifest(BaseModel):
    """Audit V2 manifest. Carries enough provenance to reproduce or
    audit the case state without re-running the solver."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["v2"] = "v2"
    case_id: str = Field(..., min_length=1)
    case_state_sha: str = Field(
        ...,
        description=(
            "SHA-256 hex digest of the canonical case-state bytes — "
            "deterministically built from polyMesh + physics dicts + "
            "BC dicts in stable file/key order. Same case state → "
            "identical SHA across machines."
        ),
    )
    solver_log_sha: str | None = Field(
        default=None,
        description=(
            "SHA-256 hex of `log.<solver>` if present; None when "
            "solver hasn't run."
        ),
    )
    figure_shas: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map from figure filename → SHA-256 hex. Empty when no "
            "post-processed figures exist yet."
        ),
    )
    dec_trail: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of DEC IDs that produced this case state. "
            "Engineer-curated or automatically derived (N5.3 v0 leaves "
            "this empty; N5-extend will populate from the manifest "
            "writers' authored_at trails)."
        ),
    )
    authored_at: str = Field(
        ...,
        min_length=10,
        max_length=40,
        description=(
            "ISO 8601 UTC timestamp. Excluded from canonical-bytes "
            "computation so re-builds at different times produce the "
            "same case_state_sha."
        ),
    )

    @field_validator("case_state_sha", "solver_log_sha")
    @classmethod
    def _sha_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) != _SHA256_HEX_LEN or not all(
            c in "0123456789abcdef" for c in v
        ):
            raise ValueError(f"sha {v[:8]}... {_SHA256_HEX_RE_HINT}")
        return v

    @field_validator("figure_shas")
    @classmethod
    def _figure_shas_format(cls, v: dict[str, str]) -> dict[str, str]:
        for filename, sha in v.items():
            if not filename:
                raise ValueError("figure filename must be non-empty")
            if len(sha) != _SHA256_HEX_LEN or not all(
                c in "0123456789abcdef" for c in sha
            ):
                raise ValueError(
                    f"figure_shas[{filename!r}] {_SHA256_HEX_RE_HINT}"
                )
        return v

    @field_validator("dec_trail")
    @classmethod
    def _dec_id_format(cls, v: list[str]) -> list[str]:
        for dec_id in v:
            if not dec_id.startswith("DEC-V61-"):
                raise ValueError(
                    f"dec_trail entry {dec_id!r} must start with 'DEC-V61-'"
                )
        return v


__all__ = ["ProvenanceManifest"]
