"""R9 addendum: (1) where exactly are the F10-dead anchors inside the PINNED A0 window?
(2) what do the 61 newly-covered anchors themselves say? ENV whitelist = EMPTY SET."""
import os, json, time, calendar, hashlib
import numpy as np
assert not any(k in os.environ for k in ("PHI", "FPRED", "LEGS"))
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
U = "/workspace/uplift_2026-09-11"; ROOT = U + "/r9"; APY = 2190; WARM = 900; CUT_OLD = T(2026, 8, 30, 20)
def load(p):
    Z = np.load(p, allow_pickle=True); cc = [str(c) for c in Z["cols"]]; ix = {c: i for i, c in enumerate(cc)}
    k = "rec" if "rec" in Z.files else "d30_n2_c42_rec"
    R = np.asarray(Z[k], float); return np.round(R[:, ix["ts"]]).astype(np.int64), R, ix
def sr(x): return float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(APY)) if len(x) > 5 else float("nan")
def boot(ts, g, B, sv):
    d = ts // 86400; ud, inv = np.unique(d, return_inverse=True); nd = len(ud)
    o = np.argsort(inv); st = np.searchsorted(inv[o], np.arange(nd)); en = np.append(st[1:], len(o))
    rng = np.random.default_rng(sv); pk = rng.integers(0, nd, size=(B, nd)); out = np.empty(B)
    for b in range(B): out[b] = g[np.concatenate([o[st[j]:en[j]] for j in pk[b]])].mean()
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
OUT = {}
# (1) F10-dead anchors inside the pinned A0 window
ts, R, ix = load(U + "/r3k/arms/A0_PWR230k_s42.npz"); ts = ts[WARM:]; g = (R[:, ix["net_ex"]] / R[:, ix["gross_total"]])[WARM:]
m = ts <= CUT_OLD; ts, g = ts[m], g[m]
P = np.load("/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", mmap_mode="r")
E = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
rm = {int(t): i for i, t in enumerate(E)}
c = np.array([int(np.isfinite(np.asarray(P[rm[int(t)]])).sum()) if int(t) in rm else -1 for t in ts])
dead = c <= 0
yy = np.array([time.gmtime(int(t)).tm_year for t in ts])
OUT["A0_pinned_window_F10_dead_anchors"] = {
    "n_total": int(len(ts)), "n_dead": int(dead.sum()), "frac_dead": round(float(dead.mean()), 4),
    "dead_by_year": {int(y): int((dead & (yy == y)).sum()) for y in sorted(set(yy.tolist()))},
    "total_by_year": {int(y): int((yy == y).sum()) for y in sorted(set(yy.tolist()))},
    "first_dead": iso(ts[dead][0]), "last_dead": iso(ts[dead][-1]),
    "dead_contiguous_prefix": bool(np.array_equal(np.nonzero(dead)[0], np.arange(int(dead.sum())))),
    "mean_g_on_dead": round(float(g[dead].mean()), 4), "mean_g_on_live": round(float(g[~dead].mean()), 4),
    "sharpe_on_live_only": round(sr(g[~dead]), 4), "n_live": int((~dead).sum()),
    "note": "on a dead anchor w10_sleeve.py L267 np.nan_to_num(xz(F10P[i,m])) makes the F10 leg identically 0 "
            "=> the F10 chain is the 2-leg book with w3[0] weight on nothing. Silent, no flag."}
# (2) the 61 newly covered anchors, on their own
for s in ("42", "2027"):
    tsx, Rx, ixx = load(ROOT + f"/dev_ext/probe_artifacts/w10_ablation_series_R9_A1x_ext_s{s}.npz")
    tsx = tsx[WARM:]; gx = (Rx[:, ixx["net_ex"]] / Rx[:, ixx["gross_total"]])[WARM:]
    new = tsx > CUT_OLD
    OUT[f"newly_covered_anchors_s{s}"] = {
        "n": int(new.sum()), "first": iso(tsx[new][0]), "last": iso(tsx[new][-1]),
        "mean_g": round(float(gx[new].mean()), 4), "sd_g": round(float(gx[new].std(ddof=1)), 4),
        "sharpe_ann_on_these": round(sr(gx[new]), 4),
        "CI95_TASK_B2000": [round(x, 4) for x in boot(tsx[new], gx[new], 2000, [20260905, 9])],
        "mean_turnover": round(float(Rx[WARM:][new, ixx["turnover"]].mean()), 5),
        "mean_gross_total": round(float(Rx[WARM:][new, ixx["gross_total"]].mean()), 4),
        "daily_mean_g": {iso(int(d) * 86400): round(float(gx[new][(tsx[new] // 86400) == d].mean()), 4)
                         for d in sorted(set((tsx[new] // 86400).tolist()))}}
json.dump(OUT, open(ROOT + "/out/RECEIPT_r9_addendum.json", "w"), indent=1, default=float)
print(json.dumps(OUT, indent=1))
