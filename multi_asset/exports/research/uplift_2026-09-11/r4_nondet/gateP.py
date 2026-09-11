"""GATE P (P4). My device instance, knobs OFF, riding the ARCHIVED s42/s2027 preds, must reproduce the
ARCHIVED A0 arrays BITWISE on both seats and both seeds, for d30_n2_c42_rec AND d30_n2_c42_W.
Comparison code copied VERBATIM from r3_xib/gateP.py."""
import numpy as np, json, sys, os, time, calendar
A = "/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
M = "/workspace/uplift_2026-09-11/r4_nondet/arms"
KEYS = ("d30_n2_c42_rec", "d30_n2_c42_W", "S0_rec", "S0_W", "legs_king", "legs_rev24", "legs_fund", "legs_ts")


def cmp(pa, pb):
    a = np.load(pa, allow_pickle=True); b = np.load(pb, allow_pickle=True); r = {}
    for k in KEYS:
        if k not in a.files or k not in b.files: r[k] = "missing"; continue
        x = np.asarray(a[k], float); y = np.asarray(b[k], float)
        if x.shape != y.shape: r[k] = "shape %s vs %s" % (x.shape, y.shape); continue
        nx = np.isnan(x); ny = np.isnan(y)
        bw = bool(np.array_equal(nx, ny) and np.array_equal(x[~nx], y[~ny]))
        r[k] = {"bitwise": bw, "n_diff": int(((x != y) & ~(nx & ny)).sum()),
                "maxabs": 0.0 if bw else float(np.nanmax(np.abs(x - y)))}
    r["symbols_equal"] = bool([str(s) for s in a["symbols"]] == [str(s) for s in b["symbols"]])
    if "config_json" in a.files:
        r["self_sha256_cfg"] = json.loads(str(a["config_json"]))["HEALTH"]["device_sha256"]
    return r


OUT = {"gate": "P_BITWISE_book_P4", "device": "/workspace/uplift_2026-09-11/w10_sleeve.py"}
ok = True
for seat in ("dyn", "fix"):
    for s in ("42", "2027"):
        pm = "%s/w10_ablation_series_R4_A0_STD_%s_s%s.npz" % (M, seat, s)
        pa = "%s/w10_ablation_series_V4_A0_%s_s%s.npz" % (A, seat, s)
        r = cmp(pm, pa); OUT["%s_s%s" % (seat, s)] = r
        ok &= all(isinstance(r[k], dict) and r[k]["bitwise"] for k in KEYS) and r["symbols_equal"]
        print(seat, s, "bitwise_all=", all(isinstance(r[k], dict) and r[k]["bitwise"] for k in KEYS),
              "mean|dg|=0.0" if r["d30_n2_c42_rec"]["bitwise"] else r["d30_n2_c42_rec"], flush=True)
# E-0911-A warm-up non-overlap, same code as r3
Z = np.load("%s/w10_ablation_series_R4_A0_STD_dyn_s42.npz" % M, allow_pickle=True)
cols = [str(c) for c in Z["cols"]]; R = np.asarray(Z["d30_n2_c42_rec"], float)
ts = np.round(R[:, cols.index("ts")]).astype(np.int64)
OUT["E0911A"] = {"n_anchors": int(len(ts)), "n_postwarm": int(len(ts) - 900),
                 "warm_last_ts": time.strftime("%F %HZ", time.gmtime(int(ts[899])))}
OUT["PASS"] = bool(ok)
print(json.dumps(OUT, indent=1))
json.dump(OUT, open("/workspace/uplift_2026-09-11/r4_nondet/receipts/GATE_P.json", "w"), indent=1)
sys.exit(0 if ok else 3)
