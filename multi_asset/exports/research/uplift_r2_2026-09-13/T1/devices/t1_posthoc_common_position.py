#!/usr/bin/env python3
"""t1_posthoc_common_position.py — pod2. POST-HOC DESCRIPTIVE (after the judge: REAL and D2 cover different 11-anchor tails).
Deliverable (5c) recomputed on the 78 anchors common to REAL and D2: window length 78, live state vector = mean state on those anchors,
conditional set = 10% nearest PRE_LIVE windows (same percentile transform as the judge). Replay arm C0_s42 and NW_s2027."""
import os, sys, json, time, hashlib
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T1"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
ST = np.load(R + "/receipts/T1_states.npz", allow_pickle=True); SC = [str(c) for c in ST["cols"]]; SV = ST["S"]; smap = {int(t): i for i, t in enumerate(SV[:, 0].astype(np.int64))}
PRIM = ["DISP24", "BREADTH72", "BTC72", "SIGF", "MUF", "PUMP72"]
D = np.load(R + "/receipts/T1_d2.npz", allow_pickle=True); DC = [str(c) for c in D["cols"]]; DD = D["D"]; dci = {c: i for i, c in enumerate(DC)}
Rz = np.load(R + "/receipts/T1_real_names.npz", allow_pickle=True); RA = Rz["anchors"]; RAC = [str(c) for c in Rz["anchor_cols"]]; rai = {c: i for i, c in enumerate(RAC)}
L0, L1 = 1787716800, 1789156800; TS_WA0 = 1656547200; TS_WA1 = 1788120000
ra = RA[(RA[:, rai["A"]] >= L0) & (RA[:, rai["A"]] <= L1)]
real = {int(r[rai["A"]]): (r[rai["price"]] + r[rai["fund"]] + r[rai["fee"]] + r[rai["timing"]]) / r[rai["gross"]] * 1e4 for r in ra}
real_s = {int(r[rai["A"]]): (r[rai["price"]] / 0.835 + r[rai["fund"]] / 0.733 + r[rai["fee"]] + r[rai["timing"]]) / r[rai["gross"]] * 1e4 for r in ra}
d2 = {int(r[dci["A"]]): r[dci["price"]] - r[dci["carry"]] for r in DD}
common = sorted(set(real) & set(d2)); nL = len(common)
def st(t, s): i = smap.get(int(t)); return SV[i, SC.index(s)] if i is not None else np.nan
live = {s: float(np.nanmean([st(t, s) for t in common])) for s in PRIM}
OUT = dict(label="POST-HOC DESCRIPTIVE", n_common=nL, live_state_common=live, live_REAL_g=float(np.mean([real[a] for a in common])), live_REAL_g_scaled=float(np.mean([real_s[a] for a in common])), live_D2_g_pre=float(np.mean([d2[a] for a in common])), arms={})
for arm in ("C0_s42", "NW_s2027"):
    A = np.load(R + "/arms/%s.npz" % arm, allow_pickle=True); rec = A["d30_n2_c42_rec"]; ts = rec[:, 0].astype(np.int64); gt = rec[:, 5]
    g = rec[:, 18] / gt; gpre = (rec[:, 19] - rec[:, 20]) / gt
    WA = (ts >= TS_WA0) & (ts <= TS_WA1); PRE = WA & (ts < L0)
    SREC = {s: np.array([st(t, s) for t in ts]) for s in PRIM}
    srt = {s: np.sort(SREC[s][PRE][np.isfinite(SREC[s][PRE])]) for s in PRIM}
    ecdf = lambda s, x: np.where(np.isfinite(x), np.searchsorted(srt[s], x, side="right") / len(srt[s]), np.nan)
    lv = np.array([float(ecdf(s, np.array(live[s]))) for s in PRIM])
    idx = np.where(PRE)[0]; starts = [idx[q] for q in range(0, len(idx) - nL + 1, 6) if idx[q + nL - 1] - idx[q] == nL - 1]
    WM = np.column_stack([ecdf(s, np.array([np.nanmean(SREC[s][a:a + nL]) for a in starts])) for s in PRIM])
    gw = np.array([g[a:a + nL].mean() for a in starts]); gpw = np.array([gpre[a:a + nL].mean() for a in starts])
    ok = np.all(np.isfinite(WM), 1); dist = np.sqrt(((WM - lv) ** 2).sum(1)); near = np.where(ok)[0][np.argsort(dist[ok], kind="stable")[:int(round(0.1 * ok.sum()))]]
    OUT["arms"][arm] = dict(n_windows=len(starts), n_cond=int(len(near)), uncond=dict(REAL=float(np.mean(gw <= OUT["live_REAL_g"])), REAL_scaled=float(np.mean(gw <= OUT["live_REAL_g_scaled"])), D2=float(np.mean(gpw <= OUT["live_D2_g_pre"]))),
                            cond=dict(REAL=float(np.mean(gw[near] <= OUT["live_REAL_g"])), REAL_scaled=float(np.mean(gw[near] <= OUT["live_REAL_g_scaled"])), D2=float(np.mean(gpw[near] <= OUT["live_D2_g_pre"]))),
                            cond_years={int(y): int(c) for y, c in zip(*np.unique([time.gmtime(int(ts[starts[q]])).tm_year for q in near], return_counts=True))})
json.dump(dict(self_sha256=sha(os.path.abspath(__file__)), result=OUT), open(R + "/receipts/RECEIPT_T1_posthoc_common_position.json", "w"), indent=1)
print(json.dumps(OUT, indent=1))
