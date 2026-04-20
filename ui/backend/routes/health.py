"""Liveness probe."""

from __future__ import annotations

from fastapi import APIRouter

from ui.backend import __version__

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Return liveness status and backend version.

    Phase 0 gate criterion: responds 200 with {"status": "ok"}.
    """

    return {"status": "ok", "version": __version__}
