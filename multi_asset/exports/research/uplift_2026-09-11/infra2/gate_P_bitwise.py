"""GATE P-BITWISE (book layer): the knobs-off / parity injection must reproduce the ARCHIVED A0
arrays BITWISE, on every judged cell (seat x seed), for BOTH rec and W, and the round-1 ORDINAL
build of the SAME arm must fail the same test."""
import numpy as np, json, sys, os
A = "/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
M = "/workspace/uplift_2026-09-11/infra2/arms"
KEYS = ("d30_n2_c42_rec", "d30_n2_c42_W", "S0_rec", "S0_W", "legs_king", "legs_rev24", "legs_fund", "legs_ts")
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}


def cmp(pa, pb):
    a = np.load(pa, allow_pickle=True); b = np.load(pb, allow_pickle=True)
    r = {}
    for k in KEYS:
        if k not in a.files or k not in b.files: r[k] = "missing"; continue
        x = np.asarray(a[k], float); y = np.asarray(b[k], float)
        if x.shape != y.shape: r[k] = f"shape {x.shape} vs {y.shape}"; continue
        nx = np.isnan(x); ny = np.isnan(y)
        bw = bool(np.array_equal(nx, ny) and np.array_equal(x[~nx], y[~ny]))
        r[k] = {"bitwise": bw, "n_diff": int(((x != y) & ~(nx & ny)).sum()), "maxabs": float(np.nanmax(np.abs(x - y))) if not bw else 0.0}
    x = np.asarray(a["d30_n2_c42_rec"], float); y = np.asarray(b["d30_n2_c42_rec"], float)
    if x.shape == y.shape:
        gx = x[:, C["net_ex"]] / x[:, C["gross_total"]]; gy = y[:, C["net_ex"]] / y[:, C["gross_total"]]
        d = gx - gy
        r["g"] = {"n": int(len(d)), "mean_dg": float(d.mean()), "mean_abs_dg": float(np.abs(d).mean()),
                  "max_abs_dg": float(np.abs(d).max()), "frac_exact": float((d == 0).mean())}
    r["symbols_equal"] = bool([str(s) for s in a["symbols"]] == [str(s) for s in b["symbols"]])
    return r


OUT = {"gate": "P_BITWISE_book"}
allbw = True
for arm in ("XIBPAR", "XIBOLD50", "XIBLAG50"):
    for seat in ("dyn", "fix"):
        for s in ("42", "2027"):
            pm = f"{M}/w10_ablation_series_V4_{arm}_{seat}_s{s}.npz"
            pa = f"{A}/w10_ablation_series_V4_A0_{seat}_s{s}.npz"
            if not os.path.exists(pm): OUT[f"{arm}_{seat}_s{s}"] = "not built"; continue
            r = cmp(pm, pa); OUT[f"{arm}_{seat}_s{s}"] = r
            if arm == "XIBPAR":
                allbw &= all(isinstance(r[k], dict) and r[k].get("bitwise") for k in KEYS)
OUT["PASS"] = bool(allbw)
print(json.dumps(OUT, indent=1))
json.dump(OUT, open(os.environ.get("PGATE_OUT", "/workspace/uplift_2026-09-11/infra2/GATE_P_bitwise.json"), "w"), indent=1)
sys.exit(0 if OUT["PASS"] else 3)
