"""R9 judge: does closing the F10 coverage ceiling move the planning number?
Caliber (frozen before the numbers, copied from r8b2/r8_repro.py):
  g = net_ex / gross_total, bps per 4h anchor per unit gross; post-warm DROP 900 (E-0911-A);
  UTC-day block bootstrap; annualised Sharpe = mean/std(ddof=1)*sqrt(2190).
Two bootstrap estimators are reported side by side, on purpose:
  TASK : B=2000, numpy.default_rng([20260905, k])         (this round's brief)
  R8   : B=4000, numpy.default_rng([20260912, 31])        (the estimator that produced the PINNED
                                                           +0.6342 / [+0.1653,+1.1071] / 1.2912)
ENV whitelist: EMPTY SET."""
import os, json, time, calendar, hashlib
import numpy as np
ENV_WL = []
assert ENV_WL == [] and not any(k in os.environ for k in ("PHI", "LOOK", "FPRED", "FSEED", "LEGS", "CAL"))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
U = "/workspace/uplift_2026-09-11"; ROOT = U + "/r9"; APY = 2190; WARM = 900
CUT_OLD = T(2026, 8, 30, 20)          # E-0911-D, the ceiling this round attacks
ARMS = {
 "A0_archived_s42":   U + "/r3k/arms/A0_PWR230k_s42.npz",
 "A0_archived_s2027": U + "/r3k/arms/A0_PWR230k_s2027.npz",
 "A1_inc_s42":   ROOT + "/dev_inc/probe_artifacts/w10_ablation_series_R9_A1_inc_s42.npz",
 "A1_inc_s2027": ROOT + "/dev_inc/probe_artifacts/w10_ablation_series_R9_A1_inc_s2027.npz",
 "A1x_ext_s42":   ROOT + "/dev_ext/probe_artifacts/w10_ablation_series_R9_A1x_ext_s42.npz",
 "A1x_ext_s2027": ROOT + "/dev_ext/probe_artifacts/w10_ablation_series_R9_A1x_ext_s2027.npz"}
def load(p):
    Z = np.load(p, allow_pickle=True); cc = [str(c) for c in Z["cols"]]; ix = {c: i for i, c in enumerate(cc)}
    k = "rec" if "rec" in Z.files else "d30_n2_c42_rec"
    R = np.asarray(Z[k], float)
    ts = np.round(R[:, ix["ts"]]).astype(np.int64)
    return ts, R, ix, json.loads(str(Z["config_json"]))
def sr(x): return float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(APY)) if len(x) > 5 else float("nan")
def boot(ts, g, B, seedvec):
    d = ts // 86400; ud, inv = np.unique(d, return_inverse=True); nd = len(ud)
    order = np.argsort(inv); st = np.searchsorted(inv[order], np.arange(nd)); en = np.append(st[1:], len(order))
    rng = np.random.default_rng(seedvec); pick = rng.integers(0, nd, size=(B, nd)); out = np.empty(B)
    for b in range(B):
        ii = np.concatenate([order[st[j]:en[j]] for j in pick[b]]); out[b] = g[ii].mean()
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
OUT = {"caliber": "g = net_ex/gross_total, bps/4h anchor/unit gross; post-warm drop 900; annualised Sharpe = mean/sd*sqrt(2190)",
       "cut_old_E0911D": iso(CUT_OLD), "arm_files": {k: v for k, v in ARMS.items()},
       "arm_sha256": {k: sha(v) for k, v in ARMS.items()}, "arms": {}, "self_sha256": sha(os.path.abspath(__file__))}
SER = {}
for nm, p in ARMS.items():
    ts, R, ix, cfg = load(p)
    OUT["arms"][nm] = {"n_rows": int(len(ts)), "first": iso(ts[0]), "last": iso(ts[-1]),
                       "cfg": {k: cfg.get(k) for k in ("LEGS", "PHI", "LOOK", "WRULE", "CAL", "MEMBERS_TOPN",
                                                        "UMASK_SCOPE", "FTRIM", "SLOW_NPY", "FPRED", "COSTB_JSON", "FSEED")}}
    SER[nm] = (ts, R[:, ix["net_ex"]] / R[:, ix["gross_total"]])
# ── GATE X-COV: on every anchor we intend to report, the DL leg must actually be present ──
# (w10_sleeve.py L267 turns an absent F10 score into 0.0 via nan_to_num — that is the E-0911-D defect.)
def cov(dl_path, dlw_targets, ts_list):
    P = np.load(dl_path, mmap_mode="r")
    E = np.load(dlw_targets, allow_pickle=True)["E_ts"].astype(np.int64)
    rm = {int(t): i for i, t in enumerate(E)}
    out = []
    for t in ts_list:
        i = rm.get(int(t))
        out.append(int(np.isfinite(np.asarray(P[i])).sum()) if i is not None else -1)
    return np.array(out)
COVCHK = {}
for nm, dl, tg in [("A0_archived_s42", "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", "/workspace/dlw_v4raw/data/dlw_targets.npz"),
                   ("A1_inc_s42", "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy", "/workspace/dlw_v4raw/data/dlw_targets.npz"),
                   ("A1x_ext_s42", ROOT + "/out/f10_v4RAWx_s42.npy", U + "/r6/out/dlw_targets_x0910.npz")]:
    ts = SER[nm][0][WARM:]
    c = cov(dl, tg, ts)
    bad = np.nonzero(c <= 0)[0]
    COVCHK[nm] = {"dl_leg": dl, "n_postwarm_anchors": int(len(ts)),
                  "n_anchors_with_zero_finite_F10": int((c <= 0).sum()),
                  "first_dead_anchor": iso(ts[bad[0]]) if bad.size else None,
                  "last_live_anchor": iso(ts[np.nonzero(c > 0)[0][-1]]) if (c > 0).any() else None,
                  "median_finite_members_when_live": int(np.median(c[c > 0])) if (c > 0).any() else 0}
OUT["GATE_X_COV"] = COVCHK
# the new upper bound = last anchor whose F10 leg is genuinely present, on the extended instrument
ts_e = SER["A1x_ext_s42"][0][WARM:]
c_e = cov(ROOT + "/out/f10_v4RAWx_s42.npy", U + "/r6/out/dlw_targets_x0910.npz", ts_e)
CUT_NEW = int(ts_e[np.nonzero(c_e > 0)[0][-1]])
OUT["new_upper_bound"] = iso(CUT_NEW)
def stat(nm, cut, tag):
    ts, g = SER[nm]; ts = ts[WARM:]; g = g[WARM:]
    m = ts <= cut; ts, g = ts[m], g[m]
    r = {"window": tag, "cut": iso(cut), "n": int(len(g)), "first": iso(ts[0]), "last": iso(ts[-1]),
         "mean_g": round(float(g.mean()), 4), "sharpe_ann": round(sr(g), 4),
         "CI95_TASK_B2000_rng20260905": [round(x, 4) for x in boot(ts, g, 2000, [20260905, 1])],
         "CI95_R8_B4000_rng20260912_31": [round(x, 4) for x in boot(ts, g, 4000, [20260912, 31])]}
    yy = np.array([time.gmtime(int(t)).tm_year for t in ts])
    r["by_year_mean_g"] = {int(y): round(float(g[yy == y].mean()), 4) for y in sorted(set(yy.tolist()))}
    r["by_year_n"] = {int(y): int((yy == y).sum()) for y in sorted(set(yy.tolist()))}
    return r
OUT["RESULTS"] = {}
for nm in ARMS:
    OUT["RESULTS"][nm + "__OLD_WINDOW"] = stat(nm, CUT_OLD, "post-warm -> 2026-08-30 20Z (E-0911-D ceiling)")
for nm in ("A1x_ext_s42", "A1x_ext_s2027"):
    OUT["RESULTS"][nm + "__NEW_WINDOW"] = stat(nm, CUT_NEW, "post-warm -> " + iso(CUT_NEW) + " (ceiling closed)")
# ── GATE X-REPLAY-PREFIX: the extended replay must reproduce the incumbent replay bitwise on the shared prefix
OUT["GATE_X_REPLAY_PREFIX"] = {}
for s in ("42", "2027"):
    ti, Ri, ixi, _ = load(ARMS[f"A1_inc_s{s}"]); tex, Rex, ixe, _ = load(ARMS[f"A1x_ext_s{s}"])
    n = len(ti); assert list(ixi.keys()) == list(ixe.keys())
    eq_ts = bool(np.array_equal(ti, tex[:n]))
    d = np.abs(Ri - Rex[:n]); mx = float(np.nanmax(d))
    OUT["GATE_X_REPLAY_PREFIX"][f"s{s}"] = {"n_prefix": n, "ts_equal": eq_ts, "maxabs_all_columns": mx,
        "bitwise_equal": bool(np.array_equal(Ri, Rex[:n], equal_nan=True)),
        "per_col_maxabs": {c: float(np.nanmax(d[:, i])) for c, i in ixi.items()},
        "VERDICT": "PASS" if (eq_ts and np.array_equal(Ri, Rex[:n], equal_nan=True)) else "FAIL"}
# ── paired deltas on the common window ──
def paired(a, b, cut):
    ta, ga = SER[a]; tb, gb = SER[b]
    ta, ga = ta[WARM:], ga[WARM:]; tb, gb = tb[WARM:], gb[WARM:]
    ca, cb = ta <= cut, tb <= cut
    ta, ga, tb, gb = ta[ca], ga[ca], tb[cb], gb[cb]
    com, ia, ib = np.intersect1d(ta, tb, return_indices=True)
    d = ga[ia] - gb[ib]
    return {"n_common": int(len(com)), "mean_delta": round(float(d.mean()), 4),
            "CI95_TASK": [round(x, 4) for x in boot(com, d, 2000, [20260905, 7])],
            "sharpe_delta": round(sr(ga[ia]) - sr(gb[ib]), 4),
            "corr": round(float(np.corrcoef(ga[ia], gb[ib])[0, 1]), 4)}
OUT["PAIRED"] = {"A1_inc_minus_A0_archived_s42": paired("A1_inc_s42", "A0_archived_s42", CUT_OLD),
                 "A1_inc_minus_A0_archived_s2027": paired("A1_inc_s2027", "A0_archived_s2027", CUT_OLD),
                 "A1x_ext_minus_A1_inc_s42_oldwindow": paired("A1x_ext_s42", "A1_inc_s42", CUT_OLD)}
json.dump(OUT, open(ROOT + "/out/RECEIPT_r9_judge.json", "w"), indent=1, default=float)
print(json.dumps({"new_upper_bound": OUT["new_upper_bound"], "GATE_X_COV": OUT["GATE_X_COV"],
                  "GATE_X_REPLAY_PREFIX": {k: {kk: v[kk] for kk in ("n_prefix", "ts_equal", "maxabs_all_columns", "VERDICT")} for k, v in OUT["GATE_X_REPLAY_PREFIX"].items()},
                  "RESULTS": {k: {kk: v[kk] for kk in ("window", "n", "first", "last", "mean_g", "sharpe_ann", "CI95_TASK_B2000_rng20260905", "CI95_R8_B4000_rng20260912_31")} for k, v in OUT["RESULTS"].items()},
                  "PAIRED": OUT["PAIRED"]}, indent=1))
print("R9_JUDGE_DONE", flush=True)
