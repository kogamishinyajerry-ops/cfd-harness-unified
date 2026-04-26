Verdict: REQUEST_CHANGES

Findings:

F1-HIGH — `extract_profile_at_stations` can fabricate a fully resolved 6-station profile from a sparse mesh by reusing the same radial bin for every target and then computing shape diagnostics on duplicated data (`src/impinging_jet_extractors.py:308-359`). Repro: a slice with only one valid `r/D=2.0` bin currently returns `num_stations_resolved=6`, `is_monotonic_decay_first_segment=True`, and `has_local_minimum_in_band=True`. That means a sparse/diverged run can look like a valid profile instead of degrading to `MISSING_TARGET_QUANTITY`.

verbatim_fix
```python
    profile = _full_nu_profile(slice_, bc)
    if not profile or len(profile) < len(target_r_over_d):
        return {}

    stations: List[Dict[str, Any]] = []
    used_indices: set[int] = set()
    for target in target_r_over_d:
        remaining = [
            (idx, pair) for idx, pair in enumerate(profile)
            if idx not in used_indices
        ]
        if not remaining:
            return {}
        best_idx, best = min(
            remaining,
            key=lambda item: abs(item[1][0] - float(target)),
        )
        used_indices.add(best_idx)
        stations.append({
            "target_r_over_D": float(target),
            "matched_r_over_D": float(best[0]),
            "matched_r": float(best[0]) * float(bc.D_nozzle),
            "Nu_local": float(best[1]),
            "abs_residual_r_over_D": float(abs(best[0] - float(target))),
        })
```

F2-HIGH — `extract_secondary_peak_status` only accepts a strict interior maximum of the truncated in-band slice (`src/impinging_jet_extractors.py:398-449`). That drops valid peaks that land on `r/D=1.5` or `2.5` after binning, and it also drops broad/flat maxima even though the gold spec says the Re=23000 feature “just needs to be detectable as a local maximum ... not a sharp double-peak” (`knowledge/gold_standards/axisymmetric_impinging_jet.yaml:69-74`). Repro: `[(1.5, 8.0), (2.0, 9.9), (2.5, 10.0), (3.0, 9.8)]` currently returns `ABSENT` because the maximum sits on the band edge.

verbatim_fix
```python
    in_band = [
        (global_idx, r_val, nu_val)
        for global_idx, (r_val, nu_val) in enumerate(profile)
        if lo <= r_val <= hi
    ]
    if len(in_band) < 3:
        return {
            "value": "ABSENT",
            "peak_r_over_D": None,
            "peak_Nu_local": None,
            "search_band_r_over_D": [lo, hi],
            "num_bins_in_band": len(in_band),
            "monotonic_in_band": True,
            "source": "radial_local_max_search",
        }

    monotonic = all(in_band[i + 1][2] <= in_band[i][2] for i in range(len(in_band) - 1))
    peak_idx: Optional[int] = None
    for global_idx, _, nu_val in in_band:
        if global_idx == 0 or global_idx == len(profile) - 1:
            continue
        left = profile[global_idx - 1][1]
        right = profile[global_idx + 1][1]
        if nu_val >= left and nu_val >= right and (nu_val > left or nu_val > right):
            if peak_idx is None or nu_val > profile[peak_idx][1]:
                peak_idx = global_idx

    if peak_idx is None:
        return {
            "value": "ABSENT",
            "peak_r_over_D": None,
            "peak_Nu_local": None,
            "search_band_r_over_D": [lo, hi],
            "num_bins_in_band": len(in_band),
            "monotonic_in_band": monotonic,
            "source": "radial_local_max_search",
        }

    return {
        "value": "PRESENT",
        "peak_r_over_D": float(profile[peak_idx][0]),
        "peak_Nu_local": float(profile[peak_idx][1]),
        "search_band_r_over_D": [lo, hi],
        "num_bins_in_band": len(in_band),
        "monotonic_in_band": monotonic,
        "source": "radial_local_max_search",
    }
```

F3-MED — `has_local_minimum_in_band` does not actually enforce an interior-in-band minimum despite the comment saying it does (`src/impinging_jet_extractors.py:336-349`). It sorts the whole band by `Nu`, picks the lowest target even if that is the band edge (`1.0` or `2.0`), then compares it against neighbors from the full target list. Repro: `0.5:12, 1.0:10, 1.5:11, 2.0:12` reports `has_local_minimum_in_band=True`, even though the minimum is at the band edge and there is no valley near `r/D≈1.5`. The current tests also miss this edge/tie regime (`tests/test_impinging_jet_extractors.py:176-245`).

verbatim_fix
```python
    band = [(t, n) for (t, n) in by_target if 1.0 <= t <= 2.0]
    has_local_minimum_in_band = (
        len(band) >= 3
        and any(
            band[i][1] <= band[i - 1][1] and band[i][1] <= band[i + 1][1]
            for i in range(1, len(band) - 1)
        )
    )
```

self_pass_rate_estimate: 0.41
