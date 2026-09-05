"""horizon_six_seed_table.py — six-seed table of the model-level IC on (a) Σ ret5 rows E+1..E+48 (target starting at the E close, = the prod-caliber
window in simple-sum form) and (b) the executable window E+25min→E+4h, for BASE / A1 / A1A2 predictions, with Δ vs BASE per seed and the mean over
seeds. Inputs: horizon_profile.json (seeds 42/2027) + horizon_profile_seeds4.json (7/123/2024/31337). usage: <j1> <j2> <out.json>"""
import sys, json
import numpy as np
J = {}
for p in sys.argv[1:3]: J.update(json.load(open(p))["preds"])
SEEDS = [42, 2027, 7, 123, 2024, 31337]; res = {"seeds": SEEDS, "horizons": {}}
for h, label in (("n48", "sum_rows_E+1..E+48 (start at E close)"), ("exec_25m_4h", "rows E+6..E+48 (E+25min -> E+4h)"), ("n1", "first bar after E"), ("n6", "first 30 min after E")):
    tab = {"label": label, "per_seed": {}, "mean_delta": {}}
    for arm in ("A1", "A1A2"):
        d = []
        for s in SEEDS:
            b = J[f"BASE_s{s}"]["test_rows"][h]; a = J[f"{arm}_s{s}"]["test_rows"][h]; d.append(a - b)
            tab["per_seed"].setdefault(str(s), {})["BASE"] = b; tab["per_seed"][str(s)][arm] = a; tab["per_seed"][str(s)][f"Δ{arm}"] = round(a - b, 4)
        tab["mean_delta"][arm] = {"mean": round(float(np.mean(d)), 4), "n_pos": int(sum(x > 0 for x in d)), "min": round(min(d), 4), "max": round(max(d), 4)}
    res["horizons"][h] = tab
    print(f"[{h}] " + " | ".join(f"s{s}: BASE {tab['per_seed'][str(s)]['BASE']:.4f} A1 {tab['per_seed'][str(s)]['ΔA1']:+.4f} A1A2 {tab['per_seed'][str(s)]['ΔA1A2']:+.4f}" for s in SEEDS))
    print(f"[{h}] mean Δ A1 {tab['mean_delta']['A1']} | A1A2 {tab['mean_delta']['A1A2']}")
json.dump(res, open(sys.argv[3], "w"), indent=1); print("HORIZON_TABLE_DONE")
