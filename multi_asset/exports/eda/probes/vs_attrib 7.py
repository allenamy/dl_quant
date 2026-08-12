"""C2-refute STAGE 4 — decompose each arm's book P&L into a beta-tilt part and the rest, and
split the beta-tilt part into STATIC exposure vs TIMING (audit §11-2's decomposition, applied to
the vol-scaling arms instead of the shadow window).

  w_t          = tilt[t] * bd_t + resid_t          bd_t = xsec-demeaned beta_24h, tilt = OLS slope
  PnL_t        = tilt[t] * M_t + resid_t . Y4_t     M_t  = bd_t . Y4_t   (the beta-spread return)
  tilt[t]      = mean(tilt) + dev[t]
  static PnL   = mean(tilt) * sum(M_t)
  timing PnL   = sum(dev[t] * M_t)                  <- the part a leaked scalar can pay for

Reading rule (stated so it is not over-read): a timing P&L that SHRINKS from TRAIN to SERVE is the
leak being withdrawn. Comparing timing between λ=0 and λ=1 WITHIN an arm says how much of ΔNet
travels through the beta channel at all.
★ All correlations reported here are TIMESERIES across anchors. READ-ONLY; writes only /tmp.
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
COST, FILL = 1.9, 1.0
PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
z = np.load(PANEL, allow_pickle=True)
CHN = list(z["ch_names"]); SIG_IDX = CHN.index("rvol_72h"); BETA_IDX = CHN.index("beta_24h")
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
ym_of = {int(t): pd.to_datetime(src.ts[int(t)], unit="ms", utc=True).strftime("%Y-%m") for t in A}


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


def decompose(lam):
    ch = VolScaled(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lam=lam)
    res = CrossLegNetting(ch, W, cost_bps=COST).run(A, src.ts, year_of=yr)
    tilt, M, other, keep, ics = [], [], [], [], []
    for (t, m, p) in res["net_positions"]:
        ret = src.Y4[t]
        if not np.isfinite(ret).any():
            continue
        w = p / max(float(np.abs(p).sum()), 1e-12)
        # ★ book rank-IC: the SCALE-FREE alpha reading (per-anchor cross-sectional), which
        #   net/gross P&L is not -- P&L is value-weighted and picks up beta-timing that a
        #   cross-sectional rank correlation barely sees.
        gi = np.isfinite(ret[m]) & np.isfinite(p)
        if gi.sum() >= 20:
            from scipy.stats import rankdata as _rd
            ics.append(float(np.corrcoef(_rd(p[gi]), _rd(ret[m][gi]))[0, 1]))
        b = src.CH[t, m, BETA_IDX].astype(np.float64)
        y = np.nan_to_num(ret[m])
        ok = np.isfinite(b) & np.isfinite(w)
        if ok.sum() < 20:
            continue
        bd = np.zeros_like(b); bd[ok] = b[ok] - b[ok].mean()
        den = float(bd @ bd)
        if den <= 1e-18:
            continue
        tl = float((w * bd).sum() / den)
        Mt = float(bd @ y)
        tilt.append(tl); M.append(Mt)
        other.append(float(w @ y) - tl * Mt)          # residual (non-beta) P&L
        keep.append(int(t))
    tilt = np.array(tilt); M = np.array(M); other = np.array(other)
    beta_pnl = tilt * M
    dev = tilt - tilt.mean()
    ics = np.array(ics)
    return dict(t=np.array(keep), tilt=tilt, M=M, beta_pnl=beta_pnl, other=other,
                static=float(tilt.mean() * M.sum()), timing=float((dev * M).sum()),
                beta_total=float(beta_pnl.sum()), other_total=float(other.sum()),
                gross_total=float(beta_pnl.sum() + other.sum()),
                book_rank_ic=float(ics.mean()), book_rank_ic_t=float(ics.mean() / ics.std() * np.sqrt(len(ics))),
                n_ic=int(len(ics)))


out = {}
for arm in ("TRAIN", "SERVE", "CAUSAL"):
    kp = "/tmp/vs_pred_king_%s.npz" % arm
    if not os.path.exists(kp):
        continue
    src.king = np.load(kp)["pred"].astype(np.float64)
    src.s2 = np.load("/tmp/vs_pred_s2_%s.npz" % arm)["pred"].astype(np.float64)
    print("\n" + "=" * 78); print("ARM", arm); print("=" * 78, flush=True)
    rec = {}
    for lam in (0.0, 1.0):
        d = decompose(lam)
        print("  lam=%.0f | gross %.4f = beta-channel %.4f + other %.4f" %
              (lam, d["gross_total"], d["beta_total"], d["other_total"]))
        print("         |   beta-channel %.4f = STATIC %.4f + TIMING %.4f" %
              (d["beta_total"], d["static"], d["timing"]))
        print("         | ★ book rank-IC (per-anchor xsec) %+.5f  t %+.2f  n=%d" %
              (d["book_rank_ic"], d["book_rank_ic_t"], d["n_ic"]))
        rec["lam%d" % int(lam)] = {k: d[k] for k in
                                   ("static", "timing", "beta_total", "other_total", "gross_total",
                                    "book_rank_ic", "book_rank_ic_t", "n_ic")}
    b = rec["lam0"]; a = rec["lam1"]
    print("  --> dGross %+.5f = d(beta-channel) %+.5f + d(other) %+.5f"
          % (a["gross_total"] - b["gross_total"], a["beta_total"] - b["beta_total"],
             a["other_total"] - b["other_total"]))
    print("      d(beta-channel) %+.5f = d(STATIC) %+.5f + d(TIMING) %+.5f"
          % (a["beta_total"] - b["beta_total"], a["static"] - b["static"], a["timing"] - b["timing"]))
    rec["delta"] = {"dGross": a["gross_total"] - b["gross_total"],
                    "dBeta": a["beta_total"] - b["beta_total"],
                    "dOther": a["other_total"] - b["other_total"],
                    "dStatic": a["static"] - b["static"], "dTiming": a["timing"] - b["timing"]}
    out[arm] = rec

if "TRAIN" in out and "SERVE" in out:
    print("\n" + "=" * 78); print("TRAIN -> SERVE : what the leak was paying for"); print("=" * 78)
    for lam in ("lam0", "lam1"):
        print("  %s TIMING  %+.5f -> %+.5f   (withdrawn %+.5f)"
              % (lam, out["TRAIN"][lam]["timing"], out["SERVE"][lam]["timing"],
                 out["SERVE"][lam]["timing"] - out["TRAIN"][lam]["timing"]))
    print("  d(TIMING) contribution to ΔNet: TRAIN %+.5f  SERVE %+.5f"
          % (out["TRAIN"]["delta"]["dTiming"], out["SERVE"]["delta"]["dTiming"]))

json.dump(out, open("/tmp/vs_attrib_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/vs_attrib_result.json", flush=True)
