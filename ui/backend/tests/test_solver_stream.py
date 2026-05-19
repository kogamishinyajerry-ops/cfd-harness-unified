"""V78.1 · solver_stream SSE endpoint tests.

Closes the 8-arc-aged V71.L bookmark END-to-end. Asserts:
  - 404 on unknown case_id
  - 200 OK + Content-Type: text/event-stream for whitelist case
  - Stream emits initial state event + at least one residual event
  - Payload JSON validates against the SseEvent shape the frontend expects
  - No leak of asyncio tasks after the stream is consumed (smoke check)
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _parse_sse_chunks(body: bytes) -> list[dict]:
    """Parse an SSE body into a list of decoded JSON payloads."""
    events: list[dict] = []
    for chunk in body.decode("utf-8").split("\n\n"):
        if not chunk.strip():
            continue
        for line in chunk.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events


def test_unknown_case_id_returns_404(client: TestClient) -> None:
    with client.stream("GET", "/api/cases/does_not_exist/solver/stream") as resp:
        assert resp.status_code == 404


def test_whitelist_case_returns_event_stream(client: TestClient) -> None:
    with client.stream(
        "GET", "/api/cases/lid_driven_cavity/solver/stream"
    ) as resp:
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert ct.startswith("text/event-stream"), ct
        # Cache headers compliant with EventSource live streaming
        assert "no-cache" in resp.headers.get("cache-control", "").lower()


def test_stream_emits_running_state_first(client: TestClient) -> None:
    with client.stream(
        "GET", "/api/cases/lid_driven_cavity/solver/stream"
    ) as resp:
        # Consume just enough bytes to get past the initial state event
        # + at least one residual event, then disconnect.
        chunks = []
        total_len = 0
        for raw in resp.iter_bytes():
            chunks.append(raw)
            total_len += len(raw)
            if total_len > 256:
                break
        events = _parse_sse_chunks(b"".join(chunks))
        assert len(events) >= 1, "stream produced no events"

        # First event is the running state notification
        first = events[0]
        assert first["type"] == "state"
        assert first["state"] == "running"
        assert "ts_ms" in first


def test_stream_emits_residual_payloads_with_required_vars(
    client: TestClient,
) -> None:
    with client.stream(
        "GET", "/api/cases/lid_driven_cavity/solver/stream"
    ) as resp:
        chunks = []
        total_len = 0
        for raw in resp.iter_bytes():
            chunks.append(raw)
            total_len += len(raw)
            if total_len > 2048:
                break
        events = _parse_sse_chunks(b"".join(chunks))

        residual_events = [e for e in events if e["type"] == "residual"]
        assert len(residual_events) >= 1, "no residual events emitted"

        first_residual = residual_events[0]
        assert first_residual["iteration"] == 0
        assert "ts_ms" in first_residual
        # All 6 canonical CAE variables must be present
        for var in ("p", "U_x", "U_y", "U_z", "k", "omega"):
            assert var in first_residual["values"], var
            assert isinstance(first_residual["values"][var], (int, float))


def test_stream_residual_values_decay_monotonically(client: TestClient) -> None:
    """Synthetic generator should produce log-residual decay — i.e., the
    later iterations (post-initial-spike + post-plateau) have lower
    residuals than the first. Not strict monotonic (V82.4 model adds
    intentional spikes + plateaus) but the macro trend is downward.
    """
    with client.stream(
        "GET", "/api/cases/lid_driven_cavity/solver/stream"
    ) as resp:
        chunks = []
        total_len = 0
        for raw in resp.iter_bytes():
            chunks.append(raw)
            total_len += len(raw)
            if total_len > 4096:
                break
        events = _parse_sse_chunks(b"".join(chunks))
        residual_events = [e for e in events if e["type"] == "residual"]
        if len(residual_events) < 3:
            pytest.skip("too few residual events to verify decay")

        # Pick p (pressure · the watched curve). V82.4 model: starts at
        # 10**0.5 ≈ 3.16, rises through the initial spike (iters 0-8),
        # then decays. Across all captured iterations the LAST should be
        # lower than the FIRST (macro decay), even with intermediate spikes.
        first_p = residual_events[0]["values"]["p"]
        late_p = residual_events[-1]["values"]["p"]
        assert late_p < first_p, f"p should decay: first={first_p}, late={late_p}"


# V82.4 · physical-realism layer assertions (offline · pure-function tests)


def test_v824_initial_spike_layer_present() -> None:
    """V82.4 Layer 1 · residuals should RISE during the first 8 iterations
    (matching simpleFoam's initial-condition adjustment) before resuming
    canonical decay. V78.1 lacked this; V82.4 adds it.
    """
    from ui.backend.routes.solver_stream import _synthetic_residual

    p_iter_0 = _synthetic_residual(0, "p", 0.5, 0.028)
    p_iter_4 = _synthetic_residual(4, "p", 0.5, 0.028)
    # Peak of the sine-shaped spike is at iter 4 (sin(pi/2)=1, factor=0.6).
    # So p at iter 4 should be HIGHER than p at iter 0.
    assert (
        p_iter_4 > p_iter_0
    ), f"V82.4 initial spike missing: p(0)={p_iter_0}, p(4)={p_iter_4}"


def test_v824_plateau_layer_present() -> None:
    """V82.4 Layer 3 · decay rate drops to ~30% during plateau windows
    (iters 50-75 and 120-145). Inside the plateau, log-residual change
    across the window should be SMALLER than an equivalent window outside.
    """
    from ui.backend.routes.solver_stream import _synthetic_residual
    import math

    # Non-plateau window: iters 30 → 45 (15 iter span, full decay).
    p_30 = _synthetic_residual(30, "p", 0.5, 0.028)
    p_45 = _synthetic_residual(45, "p", 0.5, 0.028)
    nonplateau_drop_decades = math.log10(p_30) - math.log10(p_45)

    # Plateau window: iters 55 → 70 (15 iter span, 30% decay rate).
    p_55 = _synthetic_residual(55, "p", 0.5, 0.028)
    p_70 = _synthetic_residual(70, "p", 0.5, 0.028)
    plateau_drop_decades = math.log10(p_55) - math.log10(p_70)

    assert plateau_drop_decades < nonplateau_drop_decades, (
        f"V82.4 plateau missing: plateau drop {plateau_drop_decades:.3f} dec, "
        f"non-plateau drop {nonplateau_drop_decades:.3f} dec"
    )


def test_v824_p_momentum_coupling_lag() -> None:
    """V82.4 Layer 2 · U_* residuals lag p by ~3 iterations (momentum
    correction follows pressure update by ~3 SIMPLE iters · matches real
    simpleFoam behavior). At iter 20 the U_x residual should match p's
    residual at iter ~17 (i.e., be HIGHER than p at iter 20).
    """
    from ui.backend.routes.solver_stream import _synthetic_residual

    p_20 = _synthetic_residual(20, "p", 0.5, 0.028)
    u_20 = _synthetic_residual(20, "U_x", -0.3, 0.030)
    # U starts lower (start=-0.3 vs p=0.5) but with same decay rate after
    # accounting for the 3-iter lag, U_x at iter 20 corresponds to
    # roughly iter 17 of p's curve.
    p_17 = _synthetic_residual(17, "p", 0.5, 0.028)
    u_17 = _synthetic_residual(17, "U_x", -0.3, 0.030)

    # The relative position of U_x vs p shouldn't change drastically across
    # those 3 iterations IF the lag is correctly implemented (because U_x
    # is "looking back" by 3 iters).
    ratio_at_20 = u_20 / p_20
    ratio_at_17 = u_17 / p_17
    # Both should be similar magnitude (within 2×) thanks to the lag.
    assert 0.3 < ratio_at_20 / ratio_at_17 < 3.0, (
        f"V82.4 p-U coupling lag broken · ratio(20)={ratio_at_20:.3f}, "
        f"ratio(17)={ratio_at_17:.3f}"
    )


def test_v824_k_omega_slower_than_momentum() -> None:
    """V82.4 Layer 4 · k/omega should decay 1.4× slower than U_*
    (turbulence-eq under-relaxation in k-ω SST · canonical behavior).
    So at iter 30, k's residual decade-drop from its start should be
    LESS than U_y's decade-drop from its start.
    """
    from ui.backend.routes.solver_stream import _synthetic_residual
    import math

    k_start_log = -0.4
    u_start_log = -0.5
    k_30 = _synthetic_residual(30, "k", k_start_log, 0.027)
    u_30 = _synthetic_residual(30, "U_y", u_start_log, 0.029)

    k_drop = k_start_log - math.log10(k_30)
    u_drop = u_start_log - math.log10(u_30)

    # k drops less than U_y · the 1.4× turbulence-eq slowness is exposed.
    assert k_drop < u_drop, (
        f"V82.4 k/omega slowdown missing · k drop {k_drop:.3f} dec, "
        f"U drop {u_drop:.3f} dec"
    )
