"""0C batch_002 STEP-2 (decider): book-level improve-rule (raw Y4, per-year) + net-cost portfolio
(book vs book+247[I15] vs book+250[cluster-rep]) net-Sh@{1.9,5.0} + forward-decay(247) + 2025 semester
decay shape (regime drift vs artifact) for 247 vs cluster-rep 250. Writes /tmp/0c_b2_step2.json."""
import json, sys, numpy as np, pandas as pd
from scipy.stats import rankdata
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory")
import dsl, pipeline as P
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
Y4 = W["Y4"].astype(np.float64)
C = P.load_context(horizon=4, subsample=1)
ctx, mem, CL, rows, year, day = C["ctx"], C["member"], C["CL"], C["rows"], C["year"], C["day"]
ts = W["ts"].astype(np.int64); month = pd.to_datetime(ts, unit="ms", utc=True).month.to_numpy()
N = Y4.shape[1]; wts = {"king": 0.30, "s2": 0.10, "funding_leg": 0.30, "size_leg": 0.30}
rng = np.random.default_rng(0)
FORM = {247: "xsec_z(mul(ema(ret_4h, 24), neg(rvol_6h)))", 250: "neg(xsec_z(ema(rvol_72h, 168)))"}
facs = {fid: dsl.evaluate(dsl.parse(f), ctx) for fid, f in FORM.items()}
def zc(v): return (v - v.mean()) / (v.std() + 1e-9) if v.std() > 1e-9 else np.zeros_like(v)
def lsw(s): r = rankdata(s); w = r - r.mean(); g = np.abs(w).sum(); return w / g if g > 1e-9 else w
OUT = {}

# ---- book-level improve-rule (raw Y4) ----
def series_ic(sig, rows):
    ic, yy = [], []
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(Y4[t]) & np.isfinite(sig[t]))[0]
        if b.size >= 8 and np.std(sig[t, b]) > 1e-12 and np.std(Y4[t, b]) > 1e-12:
            ic.append(np.corrcoef(rankdata(sig[t, b]), rankdata(Y4[t, b]))[0, 1]); yy.append(int(year[t]))
    return np.array(ic), np.array(yy)
book = np.full_like(Y4, np.nan)
for t in rows:
    b = np.where(mem[t] & CL[t] & np.isfinite(ctx["king"][t]) & np.isfinite(ctx["s2"][t]))[0]
    if b.size >= 8: book[t, b] = sum(wts[k] * zc(ctx[k][t, b]) for k in wts)
bic, byy = series_ic(book, rows)
OUT["book_rawY4"] = dict(pooled=round(float(bic.mean()), 5), by_year={int(y): round(float(bic[byy == y].mean()), 5) for y in sorted(set(byy))})
for fid in FORM:
    res = {}
    for lam in (0.05, 0.10):
        blend = np.full_like(Y4, np.nan); diffs, yy = [], []
        for t in rows:
            b = np.where(mem[t] & CL[t] & np.isfinite(Y4[t]) & np.isfinite(book[t]) & np.isfinite(facs[fid][t]))[0]
            if b.size >= 8:
                bl = book[t, b] + lam * zc(facs[fid][t, b])
                if np.std(bl) > 1e-12:
                    d = np.corrcoef(rankdata(bl), rankdata(Y4[t, b]))[0, 1] - np.corrcoef(rankdata(book[t, b]), rankdata(Y4[t, b]))[0, 1]
                    diffs.append(d); yy.append(int(year[t]))
        diffs, yy = np.array(diffs), np.array(yy)
        res[f"lam{lam}"] = dict(mean_diff=round(float(diffs.mean()), 6),
                                by_year={int(y): round(float(diffs[yy == y].mean()), 5) for y in sorted(set(yy))})
    OUT[f"booklevel_{fid}"] = res
    print(f"booklevel {fid}:", res, flush=True)

# ---- net-cost portfolio ----
def portfolio(add_fid, lam=0.10):
    prev = np.zeros(N); recs = []
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(Y4[t]) & np.isfinite(ctx["king"][t]) & np.isfinite(ctx["s2"][t]))[0]
        if b.size < 8: continue
        sig = sum(wts[k] * zc(ctx[k][t, b]) for k in wts)
        if add_fid is not None:
            fv = facs[add_fid][t, b]
            if np.isfinite(fv).sum() >= 8:
                z = np.zeros(b.size); ok = np.isfinite(fv); z[ok] = zc(fv[ok]); sig = sig + lam * z
        w = np.zeros(N); w[b] = lsw(sig); gross = float(np.nansum(w[b] * Y4[t, b])); turn = float(np.abs(w - prev).sum()); prev = w
        recs.append((int(year[t]), gross - turn * 1.9e-4, gross - turn * 5.0e-4, turn))
    df = pd.DataFrame(recs, columns=["year", "n19", "n50", "turn"])
    dl = df.groupby(df.index // 6).agg(n19=("n19", "sum"), n50=("n50", "sum"), year=("year", "first")).reset_index()  # ~daily
    def sh(x): return round(float(x.mean() / (x.std() + 1e-12) * np.sqrt(365)), 2)
    return dict(net19=sh(dl["n19"]), net50=sh(dl["n50"]), turn=round(float(df["turn"].mean()), 3),
                by_year_net19={int(y): sh(dl[dl.year == y]["n19"]) for y in sorted(set(dl["year"]))})
for tag, fid in (("book", None), ("book+247_I15", 247), ("book+250_cluster", 250)):
    OUT[f"netcost_{tag}"] = portfolio(fid); print(tag, OUT[f"netcost_{tag}"], flush=True)

# ---- forward-decay 247 ----
H = 4; T = Y4.shape[0]; dec = {}
for k in (-2, -1, 0, 1, 2):
    ic = []
    for t in rows:
        tt = t + k * H
        if 0 <= tt < T:
            b = np.where(mem[t] & CL[t] & np.isfinite(facs[247][t]) & np.isfinite(Y4[tt]))[0]
            if b.size >= 8 and np.std(facs[247][t, b]) > 1e-12: ic.append(np.corrcoef(rankdata(facs[247][t, b]), rankdata(Y4[tt, b]))[0, 1])
    dec[k] = round(float(np.mean(ic)), 4)
OUT["fwd_decay_247"] = dec; print("fwd-decay 247:", dec, flush=True)

# ---- 2025 semester decay shape (regime drift vs artifact): inc-IC vs YR4B by (year, semester) ----
tgt = C["target"]
def semic(fac):
    out = {}
    for y in (2022, 2023, 2024, 2025):
        for sem, mo in (("H1", month <= 6), ("H2", month > 6)):
            rws = [t for t in rows if year[t] == y and mo[t]]
            ic = []
            for t in rws:
                b = np.where(mem[t] & CL[t] & np.isfinite(tgt[t]) & np.isfinite(fac[t]))[0]
                if b.size >= 8 and np.std(fac[t, b]) > 1e-12: ic.append(np.corrcoef(rankdata(fac[t, b]), rankdata(tgt[t, b]))[0, 1])
            out[f"{y}{sem}"] = round(float(np.mean(ic)), 4) if ic else None
    return out
OUT["semester_incic_247"] = semic(facs[247]); OUT["semester_incic_250"] = semic(facs[250])
print("247 semester:", OUT["semester_incic_247"], flush=True)
print("250 semester:", OUT["semester_incic_250"], flush=True)
json.dump(OUT, open("/tmp/0c_b2_step2.json", "w"), indent=1, default=str)
print("SAVED", flush=True)
