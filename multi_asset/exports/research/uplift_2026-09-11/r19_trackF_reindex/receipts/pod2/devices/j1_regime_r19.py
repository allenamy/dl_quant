"""R6 JUDGE-1 Q4: regime-cell composition of the LIVE period, on the EXTENDED v4 axis.
Variables and labelling copied verbatim from trackF/build_regime.py + label_and_arsenal.py
(sig_fund = 1e4*xsec sd of 8h-equiv funding; disp24 = xsec sd of f_rev_24h; expanding-median, BURN=2190).
Only two things change and both are stated: (1) the axis is the x0910 meta/panel, (2) the CRYPTO m1 umask
stops at 2026-08-31 00Z so its LAST ROW is carried forward for the 60 September anchors (flagged).
"""
import numpy as np, time, json, calendar, hashlib, os
B  = "/workspace/review_scratch/health_check/dev_v4_x0910/pod_backup_2026-08-21"
B0 = "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
OUT = "/workspace/uplift_2026-09-11/r19_trackF_reindex/out_r6j1"
ENV_WL = ["R6J1_OUT"]; ENV = {k: os.environ.get(k) for k in ENV_WL}
def run(tag, base):
    MT = np.load(f"{base}/wide_fea_hist_meta.npz", allow_pickle=True)
    E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]
    PW = np.load(f"{base}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    SYM = [str(s) for s in PW["symbols"]]
    UM = np.load("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", allow_pickle=True)
    assert [str(x) for x in UM["symbols"]] == SYM
    umap = {int(t): k for k, t in enumerate(UM["ts"].astype(np.int64))}; UMM = np.asarray(UM["mask"])
    last_mask_ts = int(UM["ts"].astype(np.int64)[-1]); carried = 0
    FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]
    _IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); RN8 = FN * (8.0 / _IVf)
    rows = []
    for i, t in enumerate(E_ts):
        j = pw_row.get(int(t))
        if j is None: continue
        m = members[i]; k = umap.get(int(t))
        if k is not None: m = m[UMM[k][m]]
        elif int(t) > last_mask_ts: m = m[UMM[-1][m]]; carried += 1
        if len(m) < 50: continue
        f = RN8[j, m]; f = f[np.isfinite(f)]; r = R24[j, m]; r = r[np.isfinite(r)]
        nn = lambda a, fn: (float(fn(a)) if len(a) > 50 else np.nan)
        rows.append((int(t), len(m), nn(f, lambda a: 1e4*np.std(a)), nn(r, np.std)))
    A = np.array(rows, float); ts = A[:, 0].astype(np.int64)
    BURN = 2190
    def lab1(x):
        L = np.full(len(x), -1, np.int8)
        for i in range(len(x)):
            if i < BURN: continue
            p = x[:i]; p = p[np.isfinite(p)]
            if len(p) < BURN//2 or not np.isfinite(x[i]): continue
            L[i] = 1 if x[i] > np.median(p) else 0
        return L
    LF = lab1(A[:, 2]); LD = lab1(A[:, 3])
    LAB = np.full(len(ts), -1, np.int8); ok = (LF >= 0) & (LD >= 0); LAB[ok] = LF[ok]*2 + LD[ok]
    return ts, LAB, A, carried
ts_x, LAB_x, A_x, carried = run("x0910", B)
ts_0, LAB_0, A_0, _       = run("incumbent", B0)
# regression: the incumbent prefix must be reproduced bitwise by the extended run
n0 = len(ts_0); assert np.array_equal(ts_x[:n0], ts_0), "axis prefix mismatch"
same = int((LAB_x[:n0] == LAB_0).sum())
print(f"LABEL REGRESSION: incumbent anchors {n0}, identical labels {same} ({same/n0:.6f}); carried-forward umask rows {carried}")
T = lambda y,m,d,h=0: calendar.timegm((y,m,d,h,0,0))
NM = {-1:"UNLAB",0:"LL",1:"LH",2:"HL",3:"HH"}
WINS = {
 "FROZEN 2025-03-01..2026-08-10 20Z": (T(2025,3,1), T(2026,8,10,20)),
 "NEW 2026-08-11..2026-09-10 00Z":    (T(2026,8,11), T(2026,9,10,0)),
 "LIVE_ALL 2026-08-01..2026-09-10 00Z": (T(2026,8,1), T(2026,9,10,0)),
 "LIVE_COMBO 2026-08-26 04Z..09-10 00Z": (T(2026,8,26,4), T(2026,9,10,0)),
 "SEP 2026-09-01..09-10 00Z":         (T(2026,9,1), T(2026,9,10,0)),
 "GIVEBACK 2026-08-19..08-21 20Z":    (T(2026,8,19), T(2026,8,21,20)),
 "FULLCYCLE postwarm..2026-09-10 00Z":(int(ts_x[900]), T(2026,9,10,0)),
 "REF all anchors (extended)":        (int(ts_x[0]), int(ts_x[-1])),
}
res = {}
for nm,(lo,hi) in WINS.items():
    m = (ts_x >= lo) & (ts_x <= hi); n = int(m.sum()); L = LAB_x[m]
    nl = int((L>=0).sum())
    res[nm] = dict(n=n, n_labelled=nl,
                   shares={NM[k]: (round(float((L==k).mean()),4) if n else None) for k in (-1,0,1,2,3)},
                   HH_of_labelled=(round(float((L==3).sum()/nl),4) if nl else None),
                   sig_fund_mean=round(float(np.nanmean(A_x[m,2])),4), sig_fund_med=round(float(np.nanmedian(A_x[m,2])),4),
                   disp24_mean=round(float(np.nanmean(A_x[m,3])),6), disp24_med=round(float(np.nanmedian(A_x[m,3])),6))
    print(f"{nm:40s} n={n:5d} lab={nl:5d} HH={res[nm]['HH_of_labelled']} shares={res[nm]['shares']} sig_fund med={res[nm]['sig_fund_med']}")
# L1 distance vs the full-history reference over the 4 labelled cells
ref = res["REF all anchors (extended)"]
def dist(a):
    ra = [a['shares'][c] for c in ("LL","LH","HL","HH")]; rb = [ref['shares'][c] for c in ("LL","LH","HL","HH")]
    sa, sb = sum(ra), sum(rb)
    return round(float(sum(abs(x/sa - y/sb) for x, y in zip(ra, rb))), 4)
for nm in res: res[nm]["L1_vs_full_history"] = dist(res[nm])
print("\nL1 vs full history (labelled cells):")
for nm, v in res.items(): print(f"  {nm:40s} {v['L1_vs_full_history']}")
json.dump(dict(meta=dict(read_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         label_regression_identical=same, label_regression_n=n0,
                         umask_rows_carried_forward=carried, env_effective=ENV,
                         self_sha256=hashlib.sha256(open(__file__,"rb").read()).hexdigest()),
               windows=res), open(f"{OUT}/j1_regime.json","w"), indent=1)
