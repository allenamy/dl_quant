"""C2-refute STAGE 5 — cost sensitivity of the SERVE-caliber book + baseline-book anatomy.

team-lead's assignment (in priority order):
  1. cost sensitivity: netSum(lam=0) and dNet at cost in {1.9, 2.9, 3.79, 5.92, 8.71} bps, per caliber.
     ★ EXACT, not an approximation: positions never depend on cost (engine/netting.py uses cost_bps
       only for its savings_bps_yr report, never in position construction), so
           netSum(c) = sum(gross) - c*1e-4 * sum(turn)
       is the identity, and the break-even cost c* = 1e4 * sum(gross)/sum(turn) is exact too.
  2. baseline-book anatomy: monthly gross under each caliber -- is the collapse uniform or a few months?
  3. n=6 power: can a 6-anchor sample even see the sign of the vol-scaling tilt effect?
     (team-lead measured L3 on 6 live anchors and got the opposite sign to my 9,821.)

★ Caliber notes carried into the output, because these numbers will be quoted:
  - 1.9 bps / FILL=1.0 is the MODELLED backtest cost (PREREG §4).
  - live fee-only mixed ~2.6-2.9 bps and live realised +3.79 bps are DIFFERENT quantities
    (the latter includes post-anchor drift). They are NOT directly comparable to the modelled
    number; they are listed as reference columns only.
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
COST_GRID = [1.9, 2.9, 3.79, 5.92, 8.71]
PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
z = np.load(PANEL, allow_pickle=True)
CHN = list(z["ch_names"]); SIG_IDX = CHN.index("rvol_72h"); BETA_IDX = CHN.index("beta_24h")
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()


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


def run(lam):
    """per-anchor gross / turn / beta-tilt. Cost is applied AFTERWARDS (positions are cost-free)."""
    ch = VolScaled(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lam=lam)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    ym, gross, turn, tilt = [], [], [], []
    prev = np.zeros(src.N)
    for t in A:
        ti = int(t); ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        w = np.zeros(src.N); w[m] = p
        ok = np.isfinite(ret)
        gross.append(float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum()))
        turn.append(float(np.abs(w - prev).sum())); prev = w
        ym.append(pd.to_datetime(src.ts[ti], unit="ms", utc=True).strftime("%Y-%m"))
        b = src.CH[ti, m, BETA_IDX].astype(np.float64)
        okb = np.isfinite(b) & np.isfinite(p)
        if okb.sum() >= 20:
            bd = b[okb] - b[okb].mean(); den = float(bd @ bd)
            tilt.append(float((p[okb] @ bd) / den) if den > 1e-18 else np.nan)
        else:
            tilt.append(np.nan)
    return pd.DataFrame({"ym": ym, "gross": gross, "turn": turn, "tilt": tilt})


def teff(x):
    x = np.asarray(x, float); n = len(x)
    t = x.mean() / (x.std(ddof=1) + 1e-12) * np.sqrt(n)
    xb = x.mean(); S = ((x - xb) ** 2).sum()
    rA = [float(((x[:-k] - xb) * (x[k:] - xb)).sum() / S) for k in range(1, 13)]
    rB = [float(np.corrcoef(x[:-k], x[k:])[0, 1]) for k in range(1, 13)]
    iA = 1 + 2 * sum(max(v, 0) for v in rA); iB = 1 + 2 * sum(max(v, 0) for v in rB)
    return t, min(t / np.sqrt(iA), t / np.sqrt(iB))


D = {}
for arm in ("TRAIN", "SERVE", "CAUSAL"):
    kp = "/tmp/vs_pred_king_%s.npz" % arm
    if not os.path.exists(kp):
        continue
    src.king = np.load(kp)["pred"].astype(np.float64)
    src.s2 = np.load("/tmp/vs_pred_s2_%s.npz" % arm)["pred"].astype(np.float64)
    D[arm] = {L: run(L) for L in (0.0, 1.0)}
    print("ran", arm, flush=True)

out = {}
# ---------------------------------------------------------------- 1. cost sensitivity
print("\n" + "=" * 96)
print("1. COST SENSITIVITY  (positions are cost-independent => exact recomputation)")
print("=" * 96)
print("%-8s %9s | %s" % ("caliber", "BE bps", "  ".join("%13s" % ("c=%.2f" % c) for c in COST_GRID)))
for arm in D:
    d0, d1 = D[arm][0.0], D[arm][1.0]
    g0, t0 = d0.gross.sum(), d0.turn.sum()
    be = 1e4 * g0 / t0
    cells = []
    for c in COST_GRID:
        cells.append("%13.4f" % (g0 - c * 1e-4 * t0))
    print("%-8s %9.3f | %s   <- netSum(lam=0)" % (arm, be, "  ".join(cells)))
    out.setdefault(arm, {})["breakeven_bps_lam0"] = float(be)
    out[arm]["gross_lam0"] = float(g0); out[arm]["turn_lam0"] = float(t0)
    out[arm]["netSum_lam0_by_cost"] = {str(c): float(g0 - c * 1e-4 * t0) for c in COST_GRID}

print()
print("%-8s %9s | %s" % ("caliber", "BE bps", "  ".join("%13s" % ("c=%.2f" % c) for c in COST_GRID)))
for arm in D:
    d0, d1 = D[arm][0.0], D[arm][1.0]
    g1, t1 = d1.gross.sum(), d1.turn.sum()
    be1 = 1e4 * g1 / t1
    dg = g1 - d0.gross.sum(); dt = t1 - d0.turn.sum()
    cells = ["%13.5f" % (dg - c * 1e-4 * dt) for c in COST_GRID]
    print("%-8s %9.3f | %s   <- dNet(lam1-lam0)" % (arm, be1, "  ".join(cells)))
    out[arm]["breakeven_bps_lam1"] = float(be1)
    out[arm]["dNet_by_cost"] = {str(c): float(dg - c * 1e-4 * dt) for c in COST_GRID}
    # monthly t_eff of dNet at each cost
    m0 = d0.groupby("ym")[["gross", "turn"]].sum(); m1 = d1.groupby("ym")[["gross", "turn"]].sum()
    J = m1.join(m0, lsuffix="_1", rsuffix="_0").dropna()
    out[arm]["dNet_teff_by_cost"] = {}
    for c in COST_GRID:
        dser = (J.gross_1 - c * 1e-4 * J.turn_1) - (J.gross_0 - c * 1e-4 * J.turn_0)
        tr, te = teff(dser.to_numpy())
        out[arm]["dNet_teff_by_cost"][str(c)] = {"t_raw": float(tr), "t_eff_min": float(te)}

print("\n  t_eff(min) of dNet by cost:")
for arm in D:
    print("   %-8s %s" % (arm, "  ".join("c=%.2f: %+.3f" % (c, out[arm]["dNet_teff_by_cost"][str(c)]["t_eff_min"])
                                          for c in COST_GRID)))

# ---------------------------------------------------------------- 2. baseline-book anatomy
print("\n" + "=" * 96)
print("2. BASELINE BOOK (lam=0): is the gross collapse uniform across months, or a few months?")
print("=" * 96)
mg = {arm: D[arm][0.0].groupby("ym").gross.sum() for arm in D}
JM = pd.DataFrame(mg).dropna()
print("  months n=%d" % len(JM))
for arm in D:
    s = JM[arm]
    print("   %-7s  sum %8.4f | mean %+.5f | median %+.5f | %%months>0 %5.1f%% | worst %+.4f | best %+.4f"
          % (arm, s.sum(), s.mean(), s.median(), 100 * (s > 0).mean(), s.min(), s.max()))
JM["ratio_S_over_T"] = JM["SERVE"] / JM["TRAIN"]
frac = (JM["SERVE"] < JM["TRAIN"]).mean()
print("  months where SERVE gross < TRAIN gross: %.1f%%  (uniform collapse => near 100%%)" % (100 * frac))
top5 = (JM["TRAIN"] - JM["SERVE"]).sort_values(ascending=False)
print("  top-5 months by gross withdrawn: %s" % ", ".join("%s %+.3f" % (k, v) for k, v in top5.head(5).items()))
print("  those 5 months = %.1f%% of the total gross withdrawn (uniform => ~9%% for 5/54)"
      % (100 * top5.head(5).sum() / top5.sum()))
out["baseline_monthly"] = {"n_months": int(len(JM)),
                           "frac_months_serve_below_train": float(frac),
                           "top5_share_of_withdrawn": float(top5.head(5).sum() / top5.sum()),
                           "per_month": {k: {a: float(JM[a][k]) for a in D} for k in JM.index}}

# ---------------------------------------------------------------- 3. n=6 power for the L3 sign
print("\n" + "=" * 96)
print("3. CAN n=6 SEE THE SIGN?  (team-lead's live-book L3 used 6 anchors and got the opposite sign)")
print("=" * 96)
for arm in ("TRAIN",):
    a0 = D[arm][0.0].tilt.to_numpy(); a1 = D[arm][1.0].tilt.to_numpy()
    ok = np.isfinite(a0) & np.isfinite(a1)
    d = np.abs(a1[ok]) - np.abs(a0[ok])                     # per-anchor change in |tilt|
    print("  [%s] per-anchor D|tilt| : mean %+.6f  median %+.6f  %%anchors>0 %.1f%%  n=%d"
          % (arm, d.mean(), np.median(d), 100 * (d > 0).mean(), len(d)))
    rng = np.random.default_rng(0)
    for nb in (6, 12, 50, 200):
        means = np.array([d[rng.integers(0, len(d), nb)].mean() for _ in range(20000)])
        print("    random blocks of n=%3d : P(mean<0) = %5.1f%%   (a 6-anchor sample flips sign this often)"
              % (nb, 100 * (means < 0).mean()))
        out.setdefault("power", {})["n%d_P_negative" % nb] = float((means < 0).mean())
    out["power"]["per_anchor_mean_dabs_tilt"] = float(d.mean())
    out["power"]["per_anchor_frac_positive"] = float((d > 0).mean())

json.dump(out, open("/tmp/vs_cost_result.json", "w"), indent=1, default=float)
JM.to_json("/tmp/vs_monthly_gross.json")
print("\nsaved /tmp/vs_cost_result.json + /tmp/vs_monthly_gross.json", flush=True)
