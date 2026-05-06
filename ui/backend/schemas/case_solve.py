"""Wire types for the LDC solve pipeline (Phase-1A demo)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SetupBcSummary(BaseModel):
    """Response shape for POST /api/import/{case_id}/setup-bc.

    DEC-V61-131 N1.1 extended this schema to cover both the LDC
    (``bc_kind='ldc'``) and channel (``bc_kind='channel'``) executors
    so the engineer's [应用 AI 建议] click can apply either via a
    single endpoint. Lid-specific fields are optional; channel
    responses populate ``n_inlet_faces`` / ``n_outlet_faces`` instead.
    """

    case_id: str
    bc_kind: str = Field(
        default="ldc",
        description=(
            "Which executor wrote the BC dicts: 'ldc' (lid-driven "
            "cavity) or 'channel' (inlet/outlet/walls)."
        ),
    )
    n_lid_faces: int | None = Field(
        default=None,
        description="LDC: boundary faces classified as the moving lid.",
    )
    n_wall_faces: int = Field(
        ..., description="Boundary faces classified as no-slip walls."
    )
    n_inlet_faces: int | None = Field(
        default=None,
        description="Channel: boundary faces classified as the inlet.",
    )
    n_outlet_faces: int | None = Field(
        default=None,
        description="Channel: boundary faces classified as the outlet.",
    )
    lid_velocity: tuple[float, float, float] | None = Field(
        default=None,
        description="LDC: U vector applied at lid.",
    )
    nu: float = Field(..., description="Kinematic viscosity ν (m²/s).")
    reynolds: float = Field(..., description="Reynolds number U·L/ν.")
    written_files: list[str] = Field(
        ..., description="Relative paths of dicts written."
    )


class SetupBcRejection(BaseModel):
    failing_check: str  # mesh_missing | classify_failed | write_failed
    detail: str


class SolveSummary(BaseModel):
    case_id: str
    end_time_reached: float
    last_initial_residual_p: float | None
    last_initial_residual_U: tuple[float | None, float | None, float | None]
    last_continuity_error: float | None
    n_time_steps_written: int
    time_directories: list[str]
    wall_time_s: float
    converged: bool


class SolveRejection(BaseModel):
    failing_check: str  # bc_not_setup | container_unavailable | solver_diverged | post_stage_failed
    detail: str


class ResultsSummaryWire(BaseModel):
    case_id: str
    final_time: float
    cell_count: int
    u_magnitude_min: float
    u_magnitude_max: float
    u_magnitude_mean: float
    u_x_mean: float
    u_x_min: float
    u_x_max: float
    is_recirculating: bool


class ResultsRejection(BaseModel):
    failing_check: str  # solve_not_run | results_malformed
    detail: str
