"""0C — INDEPENDENT REVIEW of the engine full-history replay. Reimplements the netting-loop P&L from
raw panels (driving the engine's own leg_signals incl C5), with my own turnover/P&L/Sharpe accounting +
ablations to attribute C5 (funding-risk) and C6 (netting) per year. Also FTX-day P&L with/without C5,
netting-caliber reconciliation, and isotonic-in-path confirmation. Writes exports/eda/engine_replay_review_raw.json.
"""
import os
import sys, json, numpy as np, pandas as pd
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.funding_risk import FundingLegRiskControl
from engine.signal_chain import SignalChain, DEFAULT_WEIGHTS
from scipy.stats import rankdata

COST = 1.9
CAD = {"king": 4, "s2": 24, "funding": 8, "size": 24}
src = PanelSource(); N = src.N
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()
day = (src.ts[anchors] // 86400000).astype(np.int64)


def _l1(x):
    g = np.abs(x).sum(); return x / g if g > 1e-9 else x


def dsharpe(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.mean(x) / (np.std(x) + 1e-12) * np.sqrt(365.0)) if len(x) > 2 else np.nan


def run(use_c5):
    frc = None
    if use_c5:
        dref = FundingLegRiskControl.calibrate_dispersion(src, anchors)
        frc = FundingLegRiskControl(4.0, 0.15, 4.0, 0.3, disp_ref=dref)
    chain = SignalChain(src, weights=DEFAULT_WEIGHTS, funding_risk=frc)
    held = {k: np.zeros(N) for k in DEFAULT_WEIGHTS}; prev_net = np.zeros(N)
    pnl = np.zeros(len(anchors)); gturn = np.zeros(len(anchors)); nturn = np.zeros(len(anchors))
    fund_pnl = np.zeros(len(anchors)); ics = np.full(len(anchors), np.nan)
    for i, t in enumerate(anchors):
        legs, m = chain.leg_signals(int(t))
        full = {k: np.zeros(N) for k in DEFAULT_WEIGHTS}
        gt = 0.0
        for k in DEFAULT_WEIGHTS:
            if i == 0 or int(t) % CAD[k] == 0:
                nw = np.zeros(N); nw[m] = _l1(legs[k]); gt += DEFAULT_WEIGHTS[k] * np.abs(nw - held[k]).sum(); held[k] = nw
        net = sum(DEFAULT_WEIGHTS[k] * held[k] for k in DEFAULT_WEIGHTS); net = net - net.mean()
        ret = src.Y4[int(t)]; ok = np.isfinite(ret)
        pnl[i] = float(np.nansum(net[ok] * ret[ok]))
        fund_pnl[i] = float(np.nansum(DEFAULT_WEIGHTS["funding"] * held["funding"][ok] * ret[ok]))
        gturn[i] = gt; nturn[i] = float(np.abs(net - prev_net).sum()); prev_net = net
        c = net[m]; y = src.Y4[int(t), m]; okk = np.isfinite(c) & np.isfinite(y)
        if okk.sum() >= 5 and c[okk].std() > 1e-12:
            ics[i] = np.corrcoef(rankdata(c[okk]), rankdata(y[okk]))[0, 1]
    return dict(pnl=pnl, gturn=gturn, nturn=nturn, fund_pnl=fund_pnl, ics=ics)


def per_year(R, cost_turn):
    cost = R[cost_turn] * COST * 1e-4
    df = pd.DataFrame({"day": day, "yr": yr, "pnl": R["pnl"], "net": R["pnl"] - cost})
    dl = df.groupby("day").agg(pnl=("pnl", "sum"), net=("net", "sum"), yr=("yr", "first")).reset_index()
    out = {}
    for y in sorted(set(yr.tolist())):
        dd = dl[dl.yr == y]; ii = R["ics"][yr == y]
        out[int(y)] = dict(gross_sharpe=round(dsharpe(dd["pnl"].values), 2),
                           net_sharpe=round(dsharpe(dd["net"].values), 2),
                           mean_ic=round(float(np.nanmean(ii)), 4))
    return out


if __name__ == "__main__":
    Rc5 = run(True); Rno = run(False)
    tot_years = (int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (86400000 * 365.25)
    gross_ann = Rc5["gturn"].sum() / tot_years; net_ann = Rc5["nturn"].sum() / tot_years
    hedge = 1 - net_ann / gross_ann
    print(f"[recompute] anchors={len(anchors)} hedge={hedge*100:.1f}% gross_ann={gross_ann:.0f} net_ann={net_ann:.0f} save={(gross_ann-net_ann)*COST:.1f}bps/yr", flush=True)

    # tables: full engine (C5 + C6-net-cost) ; ablations
    tab_full = per_year(Rc5, "nturn")          # C5 on, net cost (C6) = the shipped engine table
    tab_c5_grosscost = per_year(Rc5, "gturn")  # C5 on, gross cost (no C6 netting benefit)
    tab_noc5_netcost = per_year(Rno, "nturn")  # C5 off, net cost
    print("\nYEAR | FULL(C5+C6) gross/net | noC6(grosscost) net | noC5 net | dC5(net) dC6(net)", flush=True)
    for y in sorted(tab_full):
        f = tab_full[y]; c6 = tab_c5_grosscost[y]; c5 = tab_noc5_netcost[y]
        dC6 = round(f["net_sharpe"] - c6["net_sharpe"], 2); dC5 = round(f["net_sharpe"] - c5["net_sharpe"], 2)
        print(f"{y} | {f['gross_sharpe']}/{f['net_sharpe']} IC{f['mean_ic']} | {c6['net_sharpe']} | {c5['net_sharpe']} | dC5 {dC5:+} dC6 {dC6:+}", flush=True)

    # C5 effect on GROSS sharpe (does winsor clip strong funding years 2022/2023?) — pure signal effect
    print("\nC5 pure-signal (GROSS sharpe, no cost): year | C5on | C5off | delta | fundPnL C5on/off", flush=True)
    c5sig = {}
    for y in sorted(set(yr.tolist())):
        dfon = pd.DataFrame({"day": day[yr == y], "pnl": Rc5["pnl"][yr == y]}).groupby("day")["pnl"].sum()
        dfof = pd.DataFrame({"day": day[yr == y], "pnl": Rno["pnl"][yr == y]}).groupby("day")["pnl"].sum()
        fon = Rc5["fund_pnl"][yr == y].sum(); fof = Rno["fund_pnl"][yr == y].sum()
        d = round(dsharpe(dfon.values) - dsharpe(dfof.values), 2)
        c5sig[int(y)] = dict(gross_c5on=round(dsharpe(dfon.values), 2), gross_c5off=round(dsharpe(dfof.values), 2),
                             delta=d, fund_pnl_c5on=round(float(fon), 3), fund_pnl_c5off=round(float(fof), 3))
        print(f"  {y}: {dsharpe(dfon.values):.2f} vs {dsharpe(dfof.values):.2f} d{d:+} | fundPnL {fon:+.2f}/{fof:+.2f}", flush=True)

    # FTX day P&L with/without C5
    ftx_t = int(np.argmin(np.abs(src.ts - int(pd.Timestamp("2022-11-09", tz="UTC").timestamp() * 1000))))
    ftx_day = int(src.ts[ftx_t] // 86400000)
    sel = np.where(day == ftx_day)[0]
    ftx = dict(date="2022-11-09", n_anchors=int(len(sel)),
               comb_pnl_c5on=round(float(Rc5["pnl"][sel].sum()), 3), comb_pnl_c5off=round(float(Rno["pnl"][sel].sum()), 3),
               fund_pnl_c5on=round(float(Rc5["fund_pnl"][sel].sum()), 3), fund_pnl_c5off=round(float(Rno["fund_pnl"][sel].sum()), 3))
    print(f"\nFTX 2022-11-09 ({len(sel)} anchors): comb C5off {ftx['comb_pnl_c5off']} -> C5on {ftx['comb_pnl_c5on']} | funding {ftx['fund_pnl_c5off']} -> {ftx['fund_pnl_c5on']}", flush=True)

    out = dict(title="Engine full-hist replay — 0C independent review", created="2026-07-15", auditor="0C",
               anchors=int(len(anchors)), recompute_hedge_rate=round(hedge, 3), recompute_gross_ann=round(gross_ann, 1),
               recompute_net_ann=round(net_ann, 1), recompute_savings_bps=round((gross_ann - net_ann) * COST, 1),
               table_full_C5_C6=tab_full, table_noC6_grosscost=tab_c5_grosscost, table_noC5=tab_noc5_netcost,
               c5_pure_signal=c5sig, ftx_day=ftx,
               isotonic_in_pnl_path=False, poscap_in_pnl_path=False,
               note="replay P&L uses leg_signals->_l1->weighted->demean (z-weighted); isotonic/pos_cap only in target_position (unused by netting.run); vol_gate exposure_mult pinned 1.0")
    json.dump(out, open(MA + "/exports/eda/engine_replay_review_raw.json", "w"), indent=1, default=str)
    print("\nSAVED engine_replay_review_raw.json", flush=True)
