"""0C batch_001 STEP-3 (decider): net-cost gate (suppl-v2 e) for A-group survivors. Build L/S portfolios
(book 4-leg vs book+120 vs book+120+107), rank-weighted unit-gross, 4h rebalance; turnover + net-Sharpe
@cost{1.9,5.0} per year. + capacity probe: is the candidate's IC concentrated in small-DVOL coins?
Writes /tmp/0c_b1_step3.json."""
import json, sys, numpy as np, pandas as pd
from scipy.stats import rankdata
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory")
import dsl, pipeline as P
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
Y4 = W["Y4"].astype(np.float64); ch = [str(c) for c in W["ch_names"]]
size_dvol = W["CH"][:, :, ch.index("size_dvol")].astype(np.float64)
C = P.load_context(horizon=4, subsample=1)
ctx, mem, CL, rows, year, day = C["ctx"], C["member"], C["CL"], C["rows"], C["year"], C["day"]
N = Y4.shape[1]
wts = {"king": 0.30, "s2": 0.10, "funding_leg": 0.30, "size_leg": 0.30}


def zc(v): return (v - v.mean()) / (v.std() + 1e-9) if v.std() > 1e-9 else np.zeros_like(v)
def lsw(sig_b):  # rank -> demeaned L1-unit-gross L/S weights
    r = rankdata(sig_b); w = r - r.mean(); g = np.abs(w).sum(); return w / g if g > 1e-9 else w


facs = {fid: dsl.evaluate(dsl.parse(f), ctx) for fid, f in
        {120: "neg(xsec_z(ts_max(rvol_6h, 42)))", 107: "neg(xsec_z(power(ret_24h, 3)))"}.items()}


def portfolio(kind, lam=0.10):
    """kind: 'book' | 'book+120' | 'book+120+107'. Returns per-anchor (day, year, net@1.9, net@5.0, turnover)."""
    prev = np.zeros(N); recs = []
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(Y4[t]) & np.isfinite(ctx["king"][t]) & np.isfinite(ctx["s2"][t]))[0]
        if b.size < 8: continue
        sig = sum(wts[k] * zc(ctx[k][t, b]) for k in wts)
        if "120" in kind:
            fb = np.isfinite(facs[120][t, b])
            if fb.sum() >= 8: sig = sig + lam * np.where(fb, zc(np.where(fb, facs[120][t, b], np.nan)[fb]) if False else 0, 0) * 0  # placeholder
        # simpler: rebuild sig with candidate(s) added at lam on the SAME b
        sig = sum(wts[k] * zc(ctx[k][t, b]) for k in wts)
        for fid in ([120] if "120" in kind else []) + ([107] if "107" in kind else []):
            fv = facs[fid][t, b]
            if np.isfinite(fv).sum() >= 8:
                z = np.full(b.size, 0.0); ok = np.isfinite(fv); z[ok] = zc(fv[ok]); sig = sig + lam * z
        w = np.zeros(N); w[b] = lsw(sig)
        gross = float(np.nansum(w[b] * Y4[t, b])); turn = float(np.abs(w - prev).sum()); prev = w
        recs.append((int(day[t]), int(year[t]), gross - turn * 1.9e-4, gross - turn * 5.0e-4, turn))
    df = pd.DataFrame(recs, columns=["day", "year", "net19", "net50", "turn"])
    dl = df.groupby("day").agg(net19=("net19", "sum"), net50=("net50", "sum"), turn=("turn", "sum"), year=("year", "first")).reset_index()
    def sh(x): return round(float(x.mean() / (x.std() + 1e-12) * np.sqrt(365)), 2)
    out = dict(sharpe_net19=sh(dl["net19"]), sharpe_net50=sh(dl["net50"]), mean_turnover_per_anchor=round(float(df["turn"].mean()), 3),
               by_year_net19={int(y): sh(dl[dl.year == y]["net19"]) for y in sorted(set(dl["year"]))})
    return out


OUT = {}
for kind in ("book", "book+120", "book+120+107"):
    OUT[kind] = portfolio(kind)
    print(kind, OUT[kind], flush=True)

# ---- capacity probe: is 120's IC concentrated in small-DVOL (illiquid) coins? ----
ic_small, ic_large = [], []
for t in rows:
    b = np.where(mem[t] & CL[t] & np.isfinite(Y4[t]) & np.isfinite(facs[120][t]) & np.isfinite(size_dvol[t]))[0]
    if b.size >= 20:
        med = np.median(size_dvol[t, b]); sm = b[size_dvol[t, b] <= med]; lg = b[size_dvol[t, b] > med]
        if sm.size >= 8 and np.std(facs[120][t, sm]) > 1e-9: ic_small.append(np.corrcoef(rankdata(facs[120][t, sm]), rankdata(Y4[t, sm]))[0, 1])
        if lg.size >= 8 and np.std(facs[120][t, lg]) > 1e-9: ic_large.append(np.corrcoef(rankdata(facs[120][t, lg]), rankdata(Y4[t, lg]))[0, 1])
OUT["capacity_probe_120"] = dict(ic_small_dvol_half=round(float(np.mean(ic_small)), 4), ic_large_dvol_half=round(float(np.mean(ic_large)), 4),
                                 note="if small-half IC >> large-half -> lottery signal lives in illiquid tail (capacity-limited)")
print("capacity 120:", OUT["capacity_probe_120"], flush=True)
json.dump(OUT, open("/tmp/0c_b1_step3.json", "w"), indent=1, default=str)
print("SAVED /tmp/0c_b1_step3.json", flush=True)
