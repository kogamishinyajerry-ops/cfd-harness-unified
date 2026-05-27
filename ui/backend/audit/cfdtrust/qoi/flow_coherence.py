"""Pre-run flow-coherence advisory — pure functions (DEC-V61-209 follow-up).

P2 W1.0′ (Blueprint v4). A non-circular Reynolds-coherence check in the
**audit namespace** (cfdtrust), where the DEC-V61-209 drift actually happened:
nu was set to 1.5e-5 (Re/L = 2e6) while the case is validated against the NASA
TMR Re/L = 5e6 reference, producing a 15-17% skin-friction error that the gate
attributed to the (wrong-Re) reference.

The check is NON-circular because it compares the case's ACTUAL kinematic
viscosity (read from `constant/transportProperties` — what the solver will run)
against an INDEPENDENTLY-sourced canonical Reynolds number declared in the
manifest (`physics.canonical_reynolds_per_length`, cited to the benchmark).
A self-consistent manifest cannot mask a transportProperties edit.

ADVISORY-ONLY by construction: these functions only READ and return a verdict
dict; the caller stashes it in gate `details` and NEVER lets it change a gate
`status` / the overall verdict. Surfacing it as a hard pre-run gate is a
deliberate, separately-reviewed follow-up (verdict-affecting → Codex).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional


# transportProperties stores nu as a dictionary entry at line start, in one of:
#   `nu              6e-06;`            (simple)
#   `nu [0 2 -1 0 0 0 0] 6e-06;`        (dimensioned)
#   `nu  nu [0 2 -1 0 0 0 0] 6e-06;`    (older dimensionedScalar, name repeated)
# In every form the value is the last numeric token before the `;`. The match
# is ANCHORED to a line-start `nu` key and stays on that line (`[^;\n]`) so it
# never grabs a number out of a `//` / `/* */` comment that merely mentions
# "nu" (e.g. "Re/L = U/nu = 30 / 6e-6 ... x>=0.2;") — the bug an integration
# check against the real flat-plate transportProperties caught.
_NU_RE = re.compile(
    r"(?:^|\n)[ \t]*nu\b[^;\n]*?([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)[ \t]*;",
)


def parse_nu_from_transport_text(text: str) -> Optional[float]:
    """Extract kinematic viscosity (m^2/s) from a transportProperties body.

    Returns None if no `nu ... ;` dictionary entry is found or the value is
    non-positive — refusing to fabricate a viscosity (the caller then SKIPs the
    advisory rather than computing a bogus Reynolds number).
    """
    m = _NU_RE.search(text)
    if m is None:
        return None
    try:
        nu = float(m.group(1))
    except ValueError:
        return None
    return nu if nu > 0 else None


def read_kinematic_viscosity(case_dir: Path) -> Optional[float]:
    """Read nu from `<case_dir>/constant/transportProperties`.

    Returns None on a missing/unreadable/unparseable file — the advisory then
    SKIPs (cannot-compute is not a problem to flag).
    """
    path = case_dir / "constant" / "transportProperties"
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None
    return parse_nu_from_transport_text(text)


def evaluate_reynolds_coherence(
    u_inf: Optional[float],
    nu: Optional[float],
    canonical_re_per_length: Optional[float],
    *,
    advisory_ratio: float = 2.0,
) -> Dict[str, Any]:
    """Advisory: does the case's actual Re/length match the benchmark's canonical?

    `Re_per_length = u_inf / nu` (per-unit-length Reynolds, the convention the
    NASA TMR flat-plate uses: Re/L = U/nu). Compared to the independently-sourced
    `canonical_re_per_length` from the manifest.

    Returns one of:
      - status "skip"      — inputs unavailable (u_inf/nu missing or non-positive,
                             or no canonical declared); cannot compute, not a flag.
      - status "coherent"  — computed Re/L within [1/advisory_ratio, advisory_ratio]
                             of canonical.
      - status "advisory"  — computed Re/L differs from canonical by more than
                             advisory_ratio×; the reference comparison is likely
                             against a different flow regime (see DEC-V61-209).

    `advisory_ratio` default 2.0 is a COARSE "different-regime" flag, NOT a bound
    on Cf tolerance — calibrated against DEC-V61-209 where a 2.5× Re mismatch
    produced a 15-17% Cf error. This is advisory/informational only; it never
    gates the verdict.
    """
    if not (isinstance(u_inf, (int, float)) and u_inf > 0):
        return {"status": "skip", "reason": "u_inf_unavailable"}
    if not (isinstance(nu, (int, float)) and nu > 0):
        return {"status": "skip", "reason": "nu_unavailable"}
    if not (isinstance(canonical_re_per_length, (int, float)) and canonical_re_per_length > 0):
        return {"status": "skip", "reason": "no_canonical_reynolds_declared"}

    re_computed = float(u_inf) / float(nu)
    ratio = re_computed / float(canonical_re_per_length)
    coherent = (1.0 / advisory_ratio) <= ratio <= advisory_ratio
    status = "coherent" if coherent else "advisory"
    result: Dict[str, Any] = {
        "status": status,
        "re_per_length_computed": re_computed,
        "re_per_length_canonical": float(canonical_re_per_length),
        "ratio": ratio,
        "advisory_ratio": advisory_ratio,
        "inputs": {"u_inf_m_s": float(u_inf), "nu_m2_s": float(nu)},
    }
    if status == "advisory":
        result["message"] = (
            f"case Re/length = U/nu = {re_computed:.3g} differs from the benchmark's "
            f"canonical {float(canonical_re_per_length):.3g} by {ratio:.2f}x — the "
            "reference comparison may be against a different flow regime. Verify "
            "constant/transportProperties nu and the inlet velocity before trusting "
            "the gate (DEC-V61-209: a 2.5x Re mismatch produced 15-17% Cf error). "
            "Advisory only — does not change the verdict."
        )
    return result
