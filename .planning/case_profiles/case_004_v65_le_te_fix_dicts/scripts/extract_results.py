"""Extract Cp/Ct/|M_x|/sign from case_004 v5 simpleFoam run + delta vs NREL UAE Seq S 7 m/s.

Canonical baseline (NREL/TP-500-29955 + NREL/TP-500-29494 + UAE Phase VI dataset):
- Sequence S, 7 m/s axial wind, 72 RPM, 0° tip pitch, 0° yaw
- Aerodynamic shaft torque: ~787 N·m (rotor only, blade + spinner)
- Mechanical power: ~5930 W (= 787 N·m * 7.54 rad/s)
- Cp: ~0.40 (= P / (0.5 * rho * V^3 * A_rotor))
- Thrust: ~1300-1400 N

v4 (B63) result: M_x = +272 N·m (POSITIVE, wrong sign) | |M_x| = 35% canonical | Cp = ~0.12
v5 (B80) expected: M_x ~ -500 to -700 N·m (NEGATIVE, correct sign) | |M_x| = 64-89% canonical | Cp ~ 0.25-0.40
"""
from __future__ import annotations
import sys
from pathlib import Path

CANONICAL_M_X_NM = -787.0  # NREL UAE Seq S 7 m/s aerodynamic shaft torque (negative per CCW-from-upstream convention)
CANONICAL_THRUST_N = 1340.0
CANONICAL_CP = 0.40
RHO = 1.225
V_INF = 7.0
A_ROTOR = 79.43  # m^2
OMEGA = 7.539822369  # rad/s


def parse_dat(path: Path) -> list[tuple[float, ...]]:
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        rows.append(tuple(float(p) for p in parts))
    return rows


def avg_last_n(rows: list[tuple[float, ...]], n: int = 50, col: int = 1) -> float:
    vals = [r[col] for r in rows[-n:]]
    return sum(vals) / len(vals)


def main(case_dir: str) -> None:
    case = Path(case_dir)
    moment_file = case / "postProcessing/forces_rotor/0/moment.dat"
    force_file = case / "postProcessing/forces_rotor/0/force.dat"
    if not moment_file.exists():
        print(f"ERROR: {moment_file} not found")
        sys.exit(1)

    m_rows = parse_dat(moment_file)
    f_rows = parse_dat(force_file)

    print(f"=== case_004 v5 results · {case} ===")
    print(f"Iterations completed: {int(m_rows[-1][0])}")
    print(f"Sample rows (forces): {len(f_rows)} · (moments): {len(m_rows)}")
    print()

    M_x_avg = avg_last_n(m_rows, n=20, col=1)
    M_y_avg = avg_last_n(m_rows, n=20, col=2)
    M_z_avg = avg_last_n(m_rows, n=20, col=3)
    F_x_avg = avg_last_n(f_rows, n=20, col=1)

    M_x_sign = "+" if M_x_avg > 0 else "-"
    M_x_mag = abs(M_x_avg)
    M_x_pct_canonical = 100.0 * M_x_mag / abs(CANONICAL_M_X_NM)

    P_aero = M_x_mag * OMEGA  # mechanical power magnitude
    Cp = P_aero / (0.5 * RHO * V_INF ** 3 * A_ROTOR)

    sign_correct = M_x_avg < 0  # canonical is negative (CCW from upstream → negative x-moment per RH rule)
    in_full_band = M_x_mag >= 0.85 * abs(CANONICAL_M_X_NM)  # 668 N·m+
    in_marginal_band = 0.50 * abs(CANONICAL_M_X_NM) <= M_x_mag < 0.85 * abs(CANONICAL_M_X_NM)  # 393-668

    print("=== M_x (aerodynamic shaft torque) ===")
    print(f"  v5 averaged (last 20 samples) :  {M_x_avg:+.2f} N·m")
    print(f"  canonical NREL UAE Seq S 7 m/s:  {CANONICAL_M_X_NM:+.2f} N·m")
    print(f"  sign: {'CORRECT (negative)' if sign_correct else 'WRONG (still positive)'}")
    print(f"  magnitude: {M_x_mag:.1f} N·m = {M_x_pct_canonical:.1f}% of canonical")
    print()
    print("=== M_y, M_z ===")
    print(f"  M_y: {M_y_avg:+.2f} N·m  (yaw moment)")
    print(f"  M_z: {M_z_avg:+.2f} N·m  (out-of-plane)")
    print()
    print("=== Thrust ===")
    print(f"  F_x: {F_x_avg:+.2f} N  | canonical: ~{CANONICAL_THRUST_N:.0f} N")
    print()
    print("=== Power coefficient ===")
    print(f"  Cp: {Cp:.4f}  | canonical: ~{CANONICAL_CP:.2f}")
    print(f"  P_aero: {P_aero:.1f} W")
    print()
    print("=== Verdict band ===")
    if sign_correct and in_full_band:
        print("  >>> FULL band (sign + |M_x| ≥85% canonical) <<<")
    elif sign_correct and in_marginal_band:
        print("  >>> marginal-FULL band (sign + 50-85% canonical) <<<")
    elif sign_correct:
        print("  >>> strong-PARTIAL (sign correct but |M_x| <50% canonical) <<<")
    elif not sign_correct:
        print("  >>> PARTIAL/FAIL (sign still wrong · F-NEW-3.1 NOT resolved) <<<")
    print()


if __name__ == "__main__":
    case_dir = sys.argv[1] if len(sys.argv) > 1 else "/Users/Zhuanz/Desktop/case_004_nrel_phase_vi_mrf/case_v5"
    main(case_dir)
