"""0C — CROSS-LEG ORDER NETTING量化. Build each leg's target-position series (140-axis, native cadence,
fwd-filled to hourly), merge into book weight, measure GROSS (legs traded independently) vs NET (book-level
crossing) turnover = internal hedge rate → cost savings bps/yr (tick-corrected 1.9/2.9) → weight sensitivity.
CPU-only. Writes exports/eda/crossleg_netting_raw.json.
"""
import sys, numpy as np, pandas as pd, json, glob
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from scipy.stats import rankdata
from multi_asset.data.megacap_funding_replay import build_panel, HOUR_MS
TR = "multi_asset/exports/train/"; EDA = "multi_asset/exports/eda/"; WPF = "multi_asset/exports/wide_panel_full.npz"


def norm1(w):
    s = np.abs(w).sum(); return w / s if s > 1e-12 else w


def rank_w(sc):
    r = sc.argsort().argsort().astype(np.float64); r = r - r.mean(); return norm1(r)


def comp_panel(scores, member, CL, YR):
    T, N, K = scores.shape; C = np.full((T, N), np.nan)
    for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
        b = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if b.size < 5: continue
        comp = np.zeros(b.size); nk = 0
        for k in range(K):
            col = scores[t, b, k]
            if np.isfinite(col).all() and col.std() > 1e-12: comp += (col - col.mean()) / col.std(); nk += 1
        if nk: C[t, b] = comp / nk
    return C


def ffill(W):
    """forward-fill rows: hold last non-updated weight. W has NaN where no update; 0-rows stay if never set."""
    out = W.copy(); last = np.zeros(W.shape[1]); has = False
    for t in range(W.shape[0]):
        if np.isfinite(W[t]).any():
            last = np.where(np.isfinite(W[t]), W[t], 0.0); has = True
        out[t] = last if has else 0.0
    return out


if __name__ == "__main__":
    z = np.load(WPF, allow_pickle=True); wts = z["ts"].astype(np.int64); wsyms = list(z["symbols"]); N = len(wsyms)
    T = len(wts); wday = pd.to_datetime(wts, unit="ms", utc=True)
    MEM = z["MEMBER"].astype(bool); DV = z["DVOL30"].astype(np.float64)

    # ---- king (4h) ----
    kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
    king = kp["king_pred"].astype(np.float64); kmem = kp["member"].astype(bool); kcl = kp["CL"].astype(bool)
    Wk = np.full((T, N), np.nan)
    for t in np.where((kmem & kcl & np.isfinite(king)).any(1))[0]:
        v = np.where(kmem[t] & kcl[t] & np.isfinite(king[t]))[0]
        if v.size >= 10:
            w = np.zeros(N); w[v] = rank_w(king[t, v]); Wk[t] = w
    Wk = ffill(Wk)

    # ---- s2 (24h) ----
    prs2 = np.load(TR + "wideA_s2_y24_5yr/panel_ref.npz", allow_pickle=True)
    mem2, cl2, yr2 = prs2["member"].astype(bool), prs2["CL"].astype(bool), prs2["YR"].astype(np.float64)
    S2c = np.full((T, N), np.nan)
    for f in sorted(glob.glob(TR + "wideA_s2_y24_5yr/fold_*_head_scores.npz")):
        C = comp_panel(np.load(f)["scores"], mem2, cl2, yr2); m = np.isfinite(C); S2c[m] = C[m]
    Ws2 = np.full((T, N), np.nan)
    for t in np.where(np.isfinite(S2c).any(1))[0]:
        v = np.where(np.isfinite(S2c[t]))[0]
        if v.size >= 10:
            w = np.zeros(N); w[v] = rank_w(S2c[t, v]); Ws2[t] = w
    Ws2 = ffill(Ws2)

    # ---- size (daily slow) ----
    fac = -np.log(np.where(DV > 0, DV, np.nan)); Wsz = np.full((T, N), np.nan)
    for t in range(T):
        v = MEM[t] & np.isfinite(fac[t]) & np.isfinite(DV[t])
        if v.sum() >= 8:
            f = fac[t, v]; zc = (f - f.mean()) / (f.std() + 1e-12); w = np.zeros(N); w[np.where(v)[0]] = norm1(zc); Wsz[t] = w
    # orient sign to match leg_size (small-minus-big positive) — sign irrelevant for turnover, keep as-is
    Wsz = ffill(Wsz)

    # ---- funding (8h) mapped to 140-axis ----
    grid, fsyms, CLOSE, FUND = build_panel(); fsyms = list(fsyms)
    fmap = {s: wsyms.index(s) for s in fsyms if s in wsyms}
    # build funding weights on funding grid, then reindex to wide ts
    tsidx = {int(t): i for i, t in enumerate(wts)}
    Wf = np.full((T, N), np.nan)
    for gi in range(len(grid)):
        wt = int(grid[gi])
        if wt not in tsidx: continue
        v = np.where(np.isfinite(FUND[gi]))[0]
        if v.size < 5: continue
        f = -FUND[gi, v]; zc = (f - f.mean()) / (f.std() + 1e-12); zc = zc - zc.mean()
        row = np.zeros(N); cols = [fmap[fsyms[j]] for j in v if fsyms[j] in fmap]
        vv = [j for j in v if fsyms[j] in fmap]
        if not vv: continue
        zz = norm1(np.array([zc[list(v).index(j)] for j in vv])); row[cols] = zz
        Wf[tsidx[wt]] = row
    Wf = ffill(Wf)

    # ---- restrict to joint active window (all legs live): 2022-01-01 .. 2026-06-29 ----
    active = (np.abs(Wk).sum(1) > 0) & (np.abs(Ws2).sum(1) > 0) & (np.abs(Wsz).sum(1) > 0) & (np.abs(Wf).sum(1) > 0)
    rows = np.where(active)[0]
    r0, r1 = rows.min(), rows.max() + 1
    Wk, Ws2, Wsz, Wf = Wk[r0:r1], Ws2[r0:r1], Wsz[r0:r1], Wf[r0:r1]
    span_days = (wts[r1 - 1] - wts[r0]) / 86400_000; nyr = span_days / 365.0
    print(f"joint active window rows {r0}..{r1} ({pd.to_datetime(wts[r0],unit='ms',utc=True).date()}..{pd.to_datetime(wts[r1-1],unit='ms',utc=True).date()}) nyr={nyr:.2f}", flush=True)

    def turnover(W):  # annual two-sided sum|dW|
        d = np.abs(np.diff(W, axis=0, prepend=W[:1])).sum()
        return d / nyr
    legs = {"funding": Wf, "king": Wk, "size": Wsz, "s2": Ws2}
    leg_turn = {k: turnover(v) for k, v in legs.items()}
    print("per-leg annual gross turnover (Σ|w|=1 caliber):", {k: round(v, 1) for k, v in leg_turn.items()}, flush=True)

    def netting(weights):
        book = sum(weights[k] * legs[k] for k in legs)
        net = np.abs(np.diff(book, axis=0, prepend=book[:1])).sum() / nyr
        gross = sum(weights[k] * leg_turn[k] for k in legs)
        hedge = 1 - net / gross if gross > 0 else 0.0
        sav = {f"{c}bps": round((gross - net) * c, 1) for c in (1.9, 2.9)}
        return dict(gross_turn=round(gross, 1), net_turn=round(net, 1), hedge_rate=round(hedge, 3),
                    savings_bps_per_yr=sav, net_cost_bps_yr={f"{c}": round(net * c, 1) for c in (1.9, 2.9)},
                    gross_cost_bps_yr={f"{c}": round(gross * c, 1) for c in (1.9, 2.9)})

    book_w = {"funding": 0.30, "king": 0.30, "size": 0.30, "s2": 0.10}
    equal_w = {k: 0.25 for k in legs}
    scen = {"book_0.30/0.30/0.30/0.10": netting(book_w), "equal_0.25": netting(equal_w)}
    # sensitivity: vary king weight (the fast leg dominates turnover)
    for kw in (0.20, 0.40, 0.50):
        rest = (1 - kw) / 3; scen[f"king_{kw}"] = netting({"funding": rest, "king": kw, "size": rest, "s2": rest})

    # batched-clock UPPER BOUND: net all leg orders within a common window (4h = king grid ~free; daily = looser)
    def netting_batched(weights, step_rows):
        book = sum(weights[k] * legs[k] for k in legs)
        idx = np.arange(0, book.shape[0], step_rows)
        bb = book[idx]
        net = np.abs(np.diff(bb, axis=0, prepend=bb[:1])).sum() / nyr
        gross = sum(weights[k] * leg_turn[k] for k in legs)
        hedge = 1 - net / gross if gross > 0 else 0.0
        return dict(gross_turn=round(gross, 1), net_turn=round(net, 1), hedge_rate=round(hedge, 3),
                    savings_bps_per_yr={f"{c}bps": round((gross - net) * c, 1) for c in (1.9, 2.9)})
    batched = {"book_w_4h_grid(king-sync,~free)": netting_batched(book_w, 4),
               "book_w_daily_batch(delays_king,looser)": netting_batched(book_w, 24)}

    res = dict(title="Cross-leg order netting (4-leg)", created="2026-07-15", auditor="0C",
               window=[str(pd.to_datetime(wts[r0], unit="ms", utc=True).date()), str(pd.to_datetime(wts[r1 - 1], unit="ms", utc=True).date())],
               caliber="each leg Σ|w|=1 gross; turnover = annual Σ|Δw| two-sided; cost bps tick-corrected 1.9(normal)/2.9(stress)",
               per_leg_annual_turnover={k: round(v, 1) for k, v in leg_turn.items()},
               rebalance_cadence={"funding": "8h", "king": "4h", "s2": "24h", "size": "daily-slow"}, scenarios=scen,
               batched_upper_bound=batched)
    json.dump(res, open(EDA + "crossleg_netting_raw.json", "w"), indent=2, default=str)
    print("\nSCENARIOS (per-hour crossing = realized free money):", flush=True)
    for k, v in scen.items():
        print(f"  {k}: gross {v['gross_turn']} net {v['net_turn']} hedge {v['hedge_rate']} save@1.9 {v['savings_bps_per_yr']['1.9bps']}bps/yr @2.9 {v['savings_bps_per_yr']['2.9bps']}bps/yr", flush=True)
    print("BATCHED UPPER BOUND (book weights):", flush=True)
    for k, v in batched.items():
        print(f"  {k}: net {v['net_turn']} hedge {v['hedge_rate']} save@1.9 {v['savings_bps_per_yr']['1.9bps']}bps/yr @2.9 {v['savings_bps_per_yr']['2.9bps']}bps/yr", flush=True)
    print("SAVED " + EDA + "crossleg_netting_raw.json", flush=True)
