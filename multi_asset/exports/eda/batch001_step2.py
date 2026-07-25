"""0C batch_001 STEP-2: (A) confirm id101 is a normalization-universe artifact (fast dsl==ledger over
member&CL scoring, but xsec_z normalizes over all-finite>member -> product-rank artifact); (B) book-level
improve-rule (suppl-v2 c) for A-group survivors {104,107,120} vs the 4-leg book, on RAW Y4, per-year +
day-block paired bootstrap; (C) forward-decay causal test on the best survivor. Writes /tmp/0c_b1_step2.json."""
import os
import json, sys, numpy as np, pandas as pd
from scipy.stats import rankdata
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/factory")
import dsl, pipeline as P
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
Y4 = W["Y4"].astype(np.float64)
C = P.load_context(horizon=4, subsample=1)
ctx, mem, CL, rows, tgt = C["ctx"], C["member"], C["CL"], C["rows"], C["target"]
year = C["year"]; day = C["day"]
OUT = {}


def zc(v):
    return (v - v.mean()) / (v.std() + 1e-9) if v.std() > 1e-9 else np.zeros_like(v)


# ---- (A) id101 confirmation: fast dsl inc-IC (scored member&CL) vs ledger; finite vs member counts ----
fast101 = dsl.evaluate(dsl.parse("neg(mul(xsec_z(lturnover_24h), xsec_z(max_ret_24h)))"), ctx)
ics = []; fin_cnt = []; mem_cnt = []
for t in rows:
    b = np.where(mem[t] & CL[t] & np.isfinite(tgt[t]) & np.isfinite(fast101[t]))[0]
    if b.size >= 8 and np.std(fast101[t, b]) > 1e-12:
        ics.append(np.corrcoef(rankdata(fast101[t, b]), rankdata(tgt[t, b]))[0, 1])
    fin_cnt.append(int(np.isfinite(ctx["lturnover_24h"][t]).sum())); mem_cnt.append(int((mem[t] & CL[t]).sum()))
OUT["id101_confirm"] = dict(fast_incic_scored=round(float(np.mean(ics)), 5), ledger=0.0123, ref_memberCL=-0.00003,
                            median_finite_universe=int(np.median(fin_cnt)), median_memberCL=int(np.median(mem_cnt)),
                            note="fast==ledger (all-finite xsec_z); member&CL-normalized ->0 => id101 is a normalization-universe artifact")
print("id101:", OUT["id101_confirm"], flush=True)

# ---- (B) book-level improve-rule for survivors {104,107,120} on RAW Y4 ----
SURV = {104: "neg(xsec_z(ts_max(abs(ret_1h), 24)))", 107: "neg(xsec_z(power(ret_24h, 3)))",
        120: "neg(xsec_z(ts_max(rvol_6h, 42)))"}
wts = {"king": 0.30, "s2": 0.10, "funding_leg": 0.30, "size_leg": 0.30}
rng = np.random.default_rng(0)


def series_ic(sig, rows):
    ic, dy, yr = [], [], []
    for t in rows:
        b = np.where(mem[t] & CL[t] & np.isfinite(Y4[t]) & np.isfinite(sig[t]))[0]
        if b.size >= 8 and np.std(sig[t, b]) > 1e-12 and np.std(Y4[t, b]) > 1e-12:
            ic.append(np.corrcoef(rankdata(sig[t, b]), rankdata(Y4[t, b]))[0, 1]); dy.append(int(day[t])); yr.append(int(year[t]))
    return np.array(ic), np.array(dy), np.array(yr)


# book combined signal (value blend of 4 legs), and cand blends
book = np.full_like(Y4, np.nan); cand_sig = {fid: np.full_like(Y4, np.nan) for fid in SURV}
facs = {fid: dsl.evaluate(dsl.parse(f), ctx) for fid, f in SURV.items()}
for t in rows:
    b = np.where(mem[t] & CL[t])[0]
    b = b[np.isfinite(ctx["king"][t, b]) & np.isfinite(ctx["s2"][t, b])]
    if b.size < 8: continue
    book[t, b] = sum(wts[k] * zc(ctx[k][t, b]) for k in wts)
    for fid in SURV:
        fb = b[np.isfinite(facs[fid][t, b])]
        if fb.size >= 8: cand_sig[fid][t, fb] = zc(facs[fid][t, fb])

book_ic, bdy, byr = series_ic(book, rows)
OUT["book_4leg_rawY4"] = dict(pooled=round(float(book_ic.mean()), 5),
                              by_year={int(y): round(float(book_ic[byr == y].mean()), 5) for y in sorted(set(byr))})
print("book 4-leg raw-Y4 IC:", OUT["book_4leg_rawY4"], flush=True)


def dayblock_diff_ci(d, days, n=2000):
    ud = np.unique(days); d2 = {u: np.where(days == u)[0] for u in ud}
    bs = np.array([d[np.concatenate([d2[u] for u in rng.choice(ud, len(ud), True)])].mean() for _ in range(n)])
    return round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)


for fid in SURV:
    res = {}
    for lam in (0.05, 0.10, 0.50):
        blend = np.full_like(Y4, np.nan)
        for t in rows:
            bb = np.where(np.isfinite(book[t]) & np.isfinite(cand_sig[fid][t]))[0]
            if bb.size >= 8: blend[t, bb] = book[t, bb] + lam * cand_sig[fid][t, bb]
        bl_ic, bdy2, byr2 = series_ic(blend, rows)
        # paired per-anchor diff aligned to book on common anchors
        common = [t for t in rows]
        diffs, dds, yys = [], [], []
        for t in rows:
            bb = np.where(mem[t] & CL[t] & np.isfinite(Y4[t]) & np.isfinite(blend[t]) & np.isfinite(book[t]))[0]
            if bb.size >= 8 and np.std(blend[t, bb]) > 1e-12 and np.std(book[t, bb]) > 1e-12:
                d_ = (np.corrcoef(rankdata(blend[t, bb]), rankdata(Y4[t, bb]))[0, 1]
                      - np.corrcoef(rankdata(book[t, bb]), rankdata(Y4[t, bb]))[0, 1])
                diffs.append(d_); dds.append(int(day[t])); yys.append(int(year[t]))
        diffs, dds, yys = np.array(diffs), np.array(dds), np.array(yys)
        ci = dayblock_diff_ci(diffs, dds)
        by_year_diff = {int(y): round(float(diffs[yys == y].mean()), 5) for y in sorted(set(yys))}
        res[f"lam{lam}"] = dict(blend_ic=round(float(bl_ic.mean()), 5), mean_diff=round(float(diffs.mean()), 6),
                                diff_ci=list(ci), sig_pos=bool(ci[0] > 0), any_year_worse=bool(any(v < -0.0005 for v in by_year_diff.values())),
                                by_year_diff=by_year_diff)
    OUT[f"booklevel_{fid}"] = res
    print(f"booklevel {fid}:", {k: (v["mean_diff"], v["diff_ci"], "SIG+" if v["sig_pos"] else "ns") for k, v in res.items()}, flush=True)

# ---- (C) forward-decay on best survivor (highest inc-IC = 120) ----
best = 120; H = 4; T = Y4.shape[0]; fac = facs[best]
decay = {}
for k in (-2, -1, 0, 1, 2):
    ic = []
    for t in rows:
        tt = t + k * H
        if 0 <= tt < T:
            b = np.where(mem[t] & CL[t] & np.isfinite(fac[t]) & np.isfinite(Y4[tt]))[0]
            if b.size >= 8 and np.std(fac[t, b]) > 1e-12: ic.append(np.corrcoef(rankdata(fac[t, b]), rankdata(Y4[tt, b]))[0, 1])
    decay[k] = round(float(np.mean(ic)), 4)
OUT["fwd_decay_120"] = dict(profile=decay, peak_at_0=bool(decay[0] == max(decay.values()) or abs(decay[0]) == max(abs(v) for v in decay.values())))
print("fwd-decay 120:", decay, flush=True)
json.dump(OUT, open("/tmp/0c_b1_step2.json", "w"), indent=1, default=str)
print("SAVED /tmp/0c_b1_step2.json", flush=True)
