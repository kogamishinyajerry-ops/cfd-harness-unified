#!/usr/bin/env python3
"""case_035 NASA TMR turbulentFlatPlate · Cf extraction at Re_x stations vs Wieghardt benchmark."""
import os, re, math, sys

U_INF = 69.4
NU = 1.388e-5

def cf_wieghardt(re_x):
    """OpenFOAM tutorial canonical Wieghardt empirical: 0.288*(log10(Re_x))^(-2.45)."""
    return 0.288 * (math.log10(re_x)) ** (-2.45)

def cf_schultz_grunow(re_x):
    return (2.0 * math.log10(re_x) - 0.65) ** (-2.3)

def parse_patch_vectors(path, patch_name):
    with open(path) as f:
        text = f.read()
    m = re.search(rf"{patch_name}\s*\{{(.*?)^\s*\}}", text, re.DOTALL | re.MULTILINE)
    if not m: raise RuntimeError(f"Could not find {patch_name} block in {path}")
    body = m.group(1)
    vecs = re.findall(r"\(([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)", body)
    return [(float(a), float(b), float(c)) for a, b, c in vecs]

def parse_patch_scalars(path, patch_name):
    with open(path) as f:
        text = f.read()
    m = re.search(rf"{patch_name}\s*\{{(.*?)^\s*\}}", text, re.DOTALL | re.MULTILINE)
    if not m: raise RuntimeError(f"Could not find {patch_name} block in {path}")
    body = m.group(1)
    vals_match = re.search(r"List<scalar>\s*\d+\s*\((.*?)\)", body, re.DOTALL)
    if vals_match:
        body = vals_match.group(1)
    nums = re.findall(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?", body)
    # Filter out plausible scalars (skip leading non-number tokens)
    return [float(n) for n in nums]

def main():
    case = sys.argv[1] if len(sys.argv) > 1 else "."
    t_dir = sys.argv[2] if len(sys.argv) > 2 else "5000"
    wss_path = os.path.join(case, t_dir, "wallShearStress")
    cx_path = os.path.join(case, t_dir, "Cx")

    vecs = parse_patch_vectors(wss_path, "bottomWall")
    cxs = parse_patch_scalars(cx_path, "bottomWall")
    # cxs may include leading garbage (uniform value, etc); take last N entries matching len(vecs)
    if len(cxs) > len(vecs):
        cxs = cxs[-len(vecs):]
    n = min(len(vecs), len(cxs))
    print(f"parsed {len(vecs)} wallShearStress vectors + {len(cxs)} Cx scalars; using {n}")

    stations = [
        ("S1", 1.0e6),
        ("S2", 2.0e6),
        ("S3", 3.0e6),
        ("S4", 4.0e6),
        ("S5", 5.0e6),
    ]

    print(f"\n{'Stn':<5} {'Re_x':>10} {'x_tgt[m]':>10} {'x_act[m]':>10} {'tau_kin':>10} "
          f"{'Cf_act':>11} {'Cf_W':>11} {'d%_W':>8} {'Cf_SG':>11} {'d%_SG':>8}")
    print("-" * 110)
    rows = []
    for name, re_x in stations:
        x_tgt = NU * re_x / U_INF
        # find closest x in cxs[:n] to x_tgt
        best_i, best_d = 0, abs(cxs[0] - x_tgt)
        for i in range(1, n):
            d = abs(cxs[i] - x_tgt)
            if d < best_d:
                best_d, best_i = d, i
        v = vecs[best_i]
        tau_kin = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
        cf_act = 2.0 * tau_kin / (U_INF ** 2)
        x_act = cxs[best_i]
        re_x_act = U_INF * x_act / NU
        cf_w = cf_wieghardt(re_x_act)
        cf_s = cf_schultz_grunow(re_x_act)
        d_w = (cf_act - cf_w) / cf_w * 100
        d_s = (cf_act - cf_s) / cf_s * 100
        print(f"{name:<5} {re_x:>10.2e} {x_tgt:>10.4f} {x_act:>10.4f} {tau_kin:>10.5f} "
              f"{cf_act:>11.6f} {cf_w:>11.6f} {d_w:>8.2f} {cf_s:>11.6f} {d_s:>8.2f}")
        rows.append((name, re_x_act, x_act, tau_kin, cf_act, cf_w, d_w, cf_s, d_s))

    with open(os.path.join(case, "Cf_results.csv"), "w") as f:
        f.write("station,Re_x,x_m,tau_kin,Cf_actual,Cf_Wieghardt,Delta_pct_W,Cf_SG,Delta_pct_SG\n")
        for r in rows:
            f.write(",".join(s if isinstance(s, str) else f"{s:.6f}" for s in r) + "\n")
    print(f"\nWrote Cf_results.csv")

    max_w = max(abs(r[6]) for r in rows)
    max_s = max(abs(r[8]) for r in rows)
    print(f"\nMax |d%| vs Wieghardt:      {max_w:.2f}%")
    print(f"Max |d%| vs Schultz-Grunow: {max_s:.2f}%")
    if max_w < 10.0 and max_s < 10.0:
        print("\n*** FULL gate MET on both canonicals (max |d%| < 10%) → Done #4 candidate ***")
    elif max_w < 10.0 or max_s < 10.0:
        print("\n*** FULL gate MET on one canonical → §3.2-class candidate ***")
    else:
        print("\n*** strong-PARTIAL (max |d%| in [10%, 20%]) or FAIL ***")

if __name__ == "__main__":
    main()
