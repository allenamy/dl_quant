"""A6 — is the book's BAB tilt COMPENSATED, or an uncompensated exposure we are about to amplify 2.3x?

Exact additive split of the book's gross P&L, per anchor, on the book's own cells:
    bt   = xsec-demeaned beta_24h over m
    tilt = (w . bt) / (bt . bt)            the book's beta loading
    w    = tilt*bt + w_resid               (w_resid . bt == 0 by construction)
    P&L  = tilt*M      +  w_resid . y      with M = bt . y   -> exact, no residual term left over
           ^tilt part      ^idiosyncratic part

Also rebuilds the BETA-NEUTRALISED book (w_resid renormalised to unit gross) and runs full turnover
accounting on it, so the question "what does neutralising cost?" gets a net-P&L answer, not just an
attribution.

Judgement (pre-stated by team-lead):
  tilt component significantly POSITIVE in the clean caliber -> compensated exposure (risk-register it)
  tilt component ~0 or NEGATIVE                              -> uncompensated, and we are amplifying it
★ This is an attribution, i.e. CORRELATIONAL. It does not establish that removing the tilt would
  leave the rest unchanged. READ-ONLY; /tmp only.
"""
import sys, json
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
zz = np.load(PANEL, allow_pickle=True)
chn = [str(c) for c in zz["ch_names"]]
BETA = zz["CH"][:, :, chn.index("beta_24h")].astype(np.float64)
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
day = np.arange(len(src.ts)) // 24
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
RNG = np.random.default_rng(0)
CUR = {"king": .595, "s2": .202, "funding": .202, "size": 0.0}
KO = {"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.0}
ck = np.load("/tmp/vs_a1_cleanking.npz")


def dayblock(rows, vals, nb=3000):
    dd = day[rows]; ud = np.unique(dd); idx = {u: np.where(dd == u)[0] for u in ud}
    bs = np.array([vals[np.concatenate([idx[u] for u in RNG.choice(ud, len(ud), True)])].sum()
                   for _ in range(nb)])
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def analyse(tag, W):
    ch = SignalChain(src, weights=W, funding_mode="rank", pos_cap_pct=99.0)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    rows, tilts, tp, rp, tot = [], [], [], [], []
    prevF = np.zeros(src.N); prevN = np.zeros(src.N)
    gF = tnF = gN = tnN = 0.0
    for t in A:
        ti = int(t); ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        y = np.nan_to_num(ret[m]); okb = np.isfinite(BETA[ti, m])
        if okb.sum() < 20:
            continue
        bt = np.zeros(len(m)); bt[okb] = BETA[ti, m][okb] - BETA[ti, m][okb].mean()
        den = float(bt @ bt)
        if den <= 1e-18:
            continue
        tl = float((p @ bt) / den)
        Mt = float(bt @ y)
        wres = p - tl * bt                                  # beta-neutral by construction
        rows.append(ti); tilts.append(tl); tp.append(tl * Mt)
        rp.append(float(wres @ y)); tot.append(float(p @ y))
        # full book turnover
        wF = np.zeros(src.N); wF[m] = p
        gF += float(p @ y); tnF += float(np.abs(wF - prevF).sum()); prevF = wF
        # neutralised book, renormalised to unit gross
        gn = np.abs(wres).sum()
        wn = wres / gn if gn > 1e-12 else wres
        wN = np.zeros(src.N); wN[m] = wn
        gN += float(wn @ y); tnN += float(np.abs(wN - prevN).sum()); prevN = wN
    rows = np.array(rows); tilts = np.array(tilts)
    tp = np.array(tp); rp = np.array(rp); tot = np.array(tot)
    chk = float(np.abs(tp + rp - tot).max())
    S = 1e4 / YEARS
    lo_t, hi_t = dayblock(rows, tp * S)
    lo_r, hi_r = dayblock(rows, rp * S)
    out = dict(
        n=int(len(rows)), identity_max_err=chk,
        gross_total=float(tot.sum() * S), gross_tilt=float(tp.sum() * S), gross_resid=float(rp.sum() * S),
        tilt_share=float(tp.sum() / tot.sum()) if tot.sum() != 0 else np.nan,
        tilt_t=float(tp.mean() / tp.std() * np.sqrt(len(tp))),
        resid_t=float(rp.mean() / rp.std() * np.sqrt(len(rp))),
        tilt_ci=[lo_t, hi_t], resid_ci=[lo_r, hi_r],
        mean_tilt=float(tilts.mean()), mean_abs_tilt=float(np.abs(tilts).mean()),
        corr_pnl_tilt=float(np.corrcoef(tot, tilts)[0, 1]),
        corr_tiltpnl_tilt=float(np.corrcoef(tp, tilts)[0, 1]),
        full_gross=float(gF * S), full_turn=float(tnF / YEARS),
        neut_gross=float(gN * S), neut_turn=float(tnN / YEARS))
    out["full_net19"] = out["full_gross"] - out["full_turn"] * 1.9
    out["full_net379"] = out["full_gross"] - out["full_turn"] * 3.79
    out["full_be"] = out["full_gross"] / out["full_turn"]
    out["neut_net19"] = out["neut_gross"] - out["neut_turn"] * 1.9
    out["neut_net379"] = out["neut_gross"] - out["neut_turn"] * 3.79
    out["neut_be"] = out["neut_gross"] / out["neut_turn"]
    print("\n" + "=" * 96); print("CONFIG %s   (n=%d anchors)" % (tag, out["n"])); print("=" * 96)
    print("  identity check max|tilt+resid-total| = %.3e  (exact split)" % chk)
    print("  mean tilt %+.4f | mean|tilt| %.4f" % (out["mean_tilt"], out["mean_abs_tilt"]))
    print("  GROSS bps/yr   total %8.1f  =  BETA-TILT %8.1f  +  IDIO %8.1f   (tilt share %.1f%%)"
          % (out["gross_total"], out["gross_tilt"], out["gross_resid"], 100 * out["tilt_share"]))
    print("     beta-tilt  t %+.2f   dayblock95 [%+.1f, %+.1f]" % (out["tilt_t"], lo_t, hi_t))
    print("     idio       t %+.2f   dayblock95 [%+.1f, %+.1f]" % (out["resid_t"], lo_r, hi_r))
    print("  per-anchor corr(book P&L, tilt) %+.4f | corr(tilt-P&L, tilt) %+.4f"
          % (out["corr_pnl_tilt"], out["corr_tiltpnl_tilt"]))
    print("  FULL book        gross %8.1f turn %7.0f BE %6.3f | net@1.9 %8.1f net@3.79 %8.1f"
          % (out["full_gross"], out["full_turn"], out["full_be"], out["full_net19"], out["full_net379"]))
    print("  BETA-NEUTRALISED gross %8.1f turn %7.0f BE %6.3f | net@1.9 %8.1f net@3.79 %8.1f"
          % (out["neut_gross"], out["neut_turn"], out["neut_be"], out["neut_net19"], out["neut_net379"]))
    return out


res = {}
src.king = np.load("/tmp/vs_pred_king_SERVE.npz")["pred"].astype(np.float64)
src.s2 = np.load("/tmp/vs_pred_s2_SERVE.npz")["pred"].astype(np.float64)
res["SERVE_4leg"] = analyse("SERVE 4-leg (running book)", CUR)
src.king = ck["xattn"].astype(np.float64)
res["CLEANxattn_kingonly"] = analyse("CLEAN_xattn king-only", KO)
src.king = ck["plain"].astype(np.float64)
res["CLEANplain_kingonly"] = analyse("CLEAN_plain king-only", KO)
json.dump(res, open("/tmp/vs_a6_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/vs_a6_result.json", flush=True)
