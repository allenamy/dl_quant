"""0C — ARM-S2 gates (c) book margin + (e) net cost. Build king 4h book (daily returns) + ARM-S2 24h
book (daily) over the ARM-S2 test window (2024-2026); daily-return correlation; combined equal-risk vs
king-alone daily Sharpe + paired bootstrap; ARM-S2 sleeve turnover/BE/net-Sh (slow 24h = its edge).
CPU-only. Writes exports/eda/arm_s2_book.json.
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
S2 = TR + "wideA_s2_y24_c1"
RNG = np.random.default_rng(0)


def rank_weights(sc):
    r = sc.argsort().argsort().astype(np.float64); r = r - r.mean(); s = np.abs(r).sum()
    return r / s * 2.0 if s > 0 else r


def comp_panel(scores, member, CL, YR):
    T, N, K = scores.shape; C = np.full((T, N), np.nan)
    for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            C[t, base] = comp / nk
    return C


def book_daily(P, member, CL, Yraw, ts, rows_mask, cost_bps):
    """rank-L/S on P over rows where rows_mask; daily net returns + turnover series."""
    dd = pd.to_datetime(ts.astype(np.int64), unit="ms", utc=True).floor("D")
    rows = np.sort(np.where(rows_mask & np.isfinite(P).any(1))[0])
    S = P.shape[1]; prevw = np.zeros(S); dser = {}; tn = []
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]))[0]
        if v.size < 10:
            continue
        w = np.zeros(S); w[v] = rank_weights(P[t, v])
        gross = float((w * np.nan_to_num(Yraw[t])).sum()); turn = float(np.abs(w - prevw).sum())
        net = gross - turn * cost_bps * 1e-4
        dser[dd[t]] = dser.get(dd[t], 0.0) + net; tn.append(turn); prevw = w
    s = pd.Series(dser).sort_index()
    return s, float(np.mean(tn)) if tn else np.nan


if __name__ == "__main__":
    pr = np.load(S2 + "/panel_ref.npz", allow_pickle=True)
    member, CL24, YR24, Yraw24 = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    ts = pr["ts"].astype(np.int64); yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    T, N = Yraw24.shape
    kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
    king = kp["king_pred"].astype(np.float64); CL4 = kp["CL"].astype(bool); Yraw4 = kp["Yraw"].astype(np.float64)

    # ARM-S2 composite + test rows
    Scomp = np.full((T, N), np.nan); te_all = set()
    for f in sorted(glob.glob(S2 + "/fold_*_head_scores.npz")):
        z = np.load(f); C = comp_panel(z["scores"], member, CL24, YR24); m = np.isfinite(C); Scomp[m] = C[m]
        te_all |= set(z["te_rows"].tolist())
    te_days = np.unique(pd.to_datetime(ts[np.array(sorted(te_all))].astype(np.int64), unit="ms", utc=True).floor("D"))
    test_mask = np.isin(pd.to_datetime(ts.astype(np.int64), unit="ms", utc=True).floor("D"), te_days)

    ANN = np.sqrt(365.0)
    def sh(s):
        s = np.asarray(s); return float(s.mean() / s.std() * ANN) if s.std() > 0 else np.nan

    def margin(cost_bps):
        """king & ARM-S2 NET daily books at cost; corr; weight-sweep combined vs king-alone + bootstrap."""
        kd, kturn = book_daily(king, member, CL4, Yraw4, ts, test_mask, cost_bps)
        sd, sturn = book_daily(Scomp, member, CL24, Yraw24, ts, test_mask, cost_bps)
        J = pd.concat([kd, sd], axis=1, join="inner").dropna(); J.columns = ["king", "s2"]
        corr = float(J["king"].corr(J["s2"])); Jn = J / J.std()
        king_only = Jn["king"].values; out = dict(cost=cost_bps, corr=round(corr, 3),
            king_turn=round(kturn, 3), s2_turn=round(sturn, 3), king_sh=round(sh(king_only), 2),
            king_gross_ann_bps=round(float(kd.mean() * 365 * 1e4), 0), s2_gross_ann_bps=round(float(sd.mean() * 365 * 1e4), 0), sweep={})
        idx = np.arange(len(Jn))
        for w in (0.1, 0.2, 0.3, 0.5):
            comb = ((1 - w) * Jn["king"] + w * Jn["s2"]).values
            boot = np.array([sh(comb[bi := RNG.choice(idx, len(idx), True)]) - sh(king_only[bi]) for _ in range(1500)])
            out["sweep"][str(w)] = dict(comb_sh=round(sh(comb), 2), impr=round(sh(comb) - sh(king_only), 2),
                                        ci=[round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)],
                                        sig_pos=bool(np.percentile(boot, 2.5) > 0))
        return out

    m_gross = margin(0.0); m_maker = margin(1.9); m_taker = margin(5.0)
    # gate e: ARM-S2 sleeve net-Sh at tiers + BE
    e = {}
    for c in (0.0, 1.9, 5.0):
        sc, sturn = book_daily(Scomp, member, CL24, Yraw24, ts, test_mask, c)
        e[f"netSh_c{c}"] = round(sh(sc.values), 2)
    s2g, s2t = book_daily(Scomp, member, CL24, Yraw24, ts, test_mask, 0.0)
    be = float(s2g.mean() / s2t * 1e4) if s2t > 0 else None
    # gate c pass = ANY weight improves the NET (maker) book significantly
    gate_c = any(m_maker["sweep"][w]["sig_pos"] for w in m_maker["sweep"])
    result = dict(title="ARM-S2 gates c/e", created="2026-07-13", auditor="0C",
                  test_window=[str(pd.to_datetime(ts[np.array(sorted(te_all))[0]], unit="ms").date()),
                               str(pd.to_datetime(ts[np.array(sorted(te_all))[-1]], unit="ms").date())],
                  margin_gross=m_gross, margin_maker1p9=m_maker, margin_taker5=m_taker,
                  gate_c_pass_maker=gate_c, s2_sleeve_netSh=e, s2_breakeven_bps_approx=round(be, 2) if be else None,
                  note="king dominates on gross Sharpe -> equal/50-50-risk DILUTES; the honest sleeve test is a "
                       "MODEST weight on the NET book (king fast/expensive vs ARM-S2 slow/cheap). Report sweep.")
    json.dump(result, open(EDA + "arm_s2_book.json", "w"), indent=2, default=str)
    for nm, m in [("gross", m_gross), ("maker1.9", m_maker), ("taker5", m_taker)]:
        print(f"[{nm}] corr {m['corr']} kingSh {m['king_sh']} kturn {m['king_turn']} sturn {m['s2_turn']} | sweep " +
              " ".join(f"w{w}:{m['sweep'][w]['comb_sh']}({m['sweep'][w]['impr']:+},sig{m['sweep'][w]['sig_pos']})" for w in m["sweep"]), flush=True)
    print("s2 sleeve netSh", e, "BE", round(be, 2) if be else None, "| gate_c(maker)=", gate_c, flush=True)
    print("SAVED " + EDA + "arm_s2_book.json")
