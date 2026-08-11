"""C2-refute STAGE 3 — MECHANISM diagnostics (built to falsify, not to confirm).

team-lead's directional prediction has three separable links. Each is tested on its own, so the
prediction can fail at a named link rather than as a whole:

  L1  leak is expressed as a beta tilt          -> corr(book beta tilt, leak scalar) > 0
  L2  high beta ~ high sigma                    -> per-anchor xsec corr(beta_24h, rvol_72h) > 0
  L3  vol-scaling downweights those names       -> |beta tilt| and corr(tilt, leak) FALL from λ=0 to λ=1

If L1-L3 all hold, the leaked backtest's ΔNet should be DEPRESSED and ΔNet(SERVE) > ΔNet(TRAIN).
Any link failing means the outcome (whatever it is) does not have the proposed mechanism.

★ Every correlation below is PER-ANCHOR CROSS-SECTIONAL unless the name says TIMESERIES.
READ-ONLY; writes only /tmp.
"""
import sys, json, os
import numpy as np, pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting

W = {"king": .595, "s2": .202, "funding": .202, "size": 0.0}
COST = 1.9
PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
z = np.load(PANEL, allow_pickle=True)
CHN = list(z["ch_names"])
SIG_IDX = CHN.index("rvol_72h"); BETA_IDX = CHN.index("beta_24h")
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()

# ---- the leak scalar and its causal control, exactly as the audit §11 defines them ----
zp = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
Cl = zp["CLOSE"].astype(np.float64)
logc = np.log(np.where(Cl > 0, Cl, np.nan))
ret1 = logc - np.vstack([np.full((1, logc.shape[1]), np.nan), logc[:-1]])
market = np.nan_to_num(np.nanmean(np.where(np.isfinite(ret1), ret1, np.nan), axis=1))
T = len(market)
csum = np.concatenate([[0.0], np.cumsum(market)])


def seg(a, b):
    """sum market[a..b] inclusive, clipped to range."""
    a = max(a, 0); b = min(b, T - 1)
    return csum[b + 1] - csum[a] if b >= a else 0.0


LEAK = np.array([seg(t + 1, t + 11) for t in range(T)])       # the 11 future taps
CAUS = np.array([seg(t - 12, t) for t in range(T)])           # the shared causal core
del zp, Cl, logc, ret1


def sigma_at(ti, m):
    s = src.CH[ti, m, SIG_IDX].astype(np.float64)
    s = np.where(np.isfinite(s) & (s > 0), s, np.nan)
    if np.isfinite(s).sum() < 5:
        return None
    med = np.nanmedian(s)
    s = np.where(np.isfinite(s), s, med)
    return np.maximum(s, np.nanpercentile(s, 5))


class VolScaled(SignalChain):
    def __init__(self, *a, lam=0.0, **k):
        super().__init__(*a, **k); self.lam = lam; self._sig = None

    def leg_signals(self, t):
        legs, m = super().leg_signals(t)
        self._sig = sigma_at(int(t), m) if self.lam else None
        return legs, m

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if self.pos_cap_pct and mag.size >= 10 and np.isfinite(mag).any():
            lo = np.nanpercentile(mag, 100 - self.pos_cap_pct)
            hi = np.nanpercentile(mag, self.pos_cap_pct)
            mag = np.clip(mag, lo, hi)
        if self.lam and self._sig is not None and len(self._sig) == len(mag):
            mag = mag / np.power(self._sig, self.lam)
        return mag - mag.mean()


def book_tilts(lam):
    """per-anchor: beta tilt of the unit-gross book, plus sigma tilt. Returns aligned arrays."""
    ch = VolScaled(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lam=lam)
    res = CrossLegNetting(ch, W, cost_bps=COST).run(A, src.ts, year_of=yr)
    ts_, tilt, stilt, bs_corr = [], [], [], []
    for (t, m, p) in res["net_positions"]:
        g = max(float(np.abs(p).sum()), 1e-12)
        w = p / g
        b = src.CH[t, m, BETA_IDX].astype(np.float64)
        s = src.CH[t, m, SIG_IDX].astype(np.float64)
        ok = np.isfinite(b) & np.isfinite(w)
        if ok.sum() < 20:
            continue
        bd = b[ok] - b[ok].mean()
        den = float(bd @ bd)
        if den <= 1e-18:
            continue
        ts_.append(t)
        tilt.append(float((w[ok] @ bd) / den))                      # OLS slope of w on beta
        ok2 = ok & np.isfinite(s)
        if ok2.sum() >= 20:
            sd_ = s[ok2] - s[ok2].mean()
            d2 = float(sd_ @ sd_)
            stilt.append(float((w[ok2] @ sd_) / d2) if d2 > 1e-18 else np.nan)
            bs_corr.append(float(np.corrcoef(b[ok2], s[ok2])[0, 1]))
        else:
            stilt.append(np.nan); bs_corr.append(np.nan)
    return np.array(ts_), np.array(tilt), np.array(stilt), np.array(bs_corr)


def tcorr(a, b):
    """TIMESERIES correlation across anchors (not cross-sectional) + its naive t."""
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30:
        return np.nan, np.nan, int(ok.sum())
    r = float(np.corrcoef(a[ok], b[ok])[0, 1])
    n = int(ok.sum())
    return r, r * np.sqrt((n - 2) / max(1 - r * r, 1e-12)), n


out = {}
arms = ["STORED"] + [a for a in ("TRAIN", "SERVE", "CAUSAL")
                     if os.path.exists("/tmp/vs_pred_king_%s.npz" % a)]
for arm in arms:
    if arm != "STORED":
        src.king = np.load("/tmp/vs_pred_king_%s.npz" % arm)["pred"].astype(np.float64)
        src.s2 = np.load("/tmp/vs_pred_s2_%s.npz" % arm)["pred"].astype(np.float64)
    print("\n" + "=" * 78); print("ARM", arm); print("=" * 78, flush=True)
    rec = {}
    for lam in (0.0, 1.0):
        tt, tilt, stilt, bsc = book_tilts(lam)
        lk = LEAK[tt]; cs = CAUS[tt]
        r_leak, t_leak, n = tcorr(tilt, lk)
        r_caus, t_caus, _ = tcorr(tilt, cs)
        print("  lam=%.0f | mean tilt %+.4f  mean|tilt| %.4f  mean sigma-tilt %+.4f" %
              (lam, np.nanmean(tilt), np.nanmean(np.abs(tilt)), np.nanmean(stilt)))
        print("         | L2 per-anchor xsec corr(beta_24h, rvol_72h): mean %+.4f median %+.4f" %
              (np.nanmean(bsc), np.nanmedian(bsc)))
        print("         | L1/L3 TIMESERIES corr(tilt, LEAK) %+.4f (t %+.2f, n=%d) | vs CAUSAL-core %+.4f (t %+.2f)" %
              (r_leak, t_leak, n, r_caus, t_caus))
        rec["lam%d" % int(lam)] = dict(
            mean_tilt=float(np.nanmean(tilt)), mean_abs_tilt=float(np.nanmean(np.abs(tilt))),
            mean_sigma_tilt=float(np.nanmean(stilt)),
            xsec_corr_beta_sigma_mean=float(np.nanmean(bsc)),
            xsec_corr_beta_sigma_median=float(np.nanmedian(bsc)),
            ts_corr_tilt_leak=r_leak, t_tilt_leak=t_leak, n=n,
            ts_corr_tilt_causal=r_caus, t_tilt_causal=t_caus)
    a0, a1 = rec["lam0"], rec["lam1"]
    print("  --> L3 check: mean|tilt| %.4f -> %.4f (%+.1f%%) ; corr(tilt,LEAK) %+.4f -> %+.4f (%+.1f%%)"
          % (a0["mean_abs_tilt"], a1["mean_abs_tilt"],
             100 * (a1["mean_abs_tilt"] / a0["mean_abs_tilt"] - 1),
             a0["ts_corr_tilt_leak"], a1["ts_corr_tilt_leak"],
             100 * (a1["ts_corr_tilt_leak"] / a0["ts_corr_tilt_leak"] - 1)
             if a0["ts_corr_tilt_leak"] else float("nan")))
    out[arm] = rec

json.dump(out, open("/tmp/vs_mech_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/vs_mech_result.json", flush=True)
