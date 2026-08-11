"""C2-refute STAGE 2 — run the SAME assembly chain per (arm, lambda) and report ΔNet.

Uses the production engine classes (PanelSource / SignalChain / CrossLegNetting) and the same
VolScaled subclass as /tmp/vol_scale.py, so the λ=1 vs λ=0 contrast is produced by the original
code path; only the injected king/s2 prediction arrays differ between arms.

Consistency anchor FIRST: with the STORED pred panels this must give netSum(λ=0)=9.8773 and
ΔNet=+1.81420 / t_raw +10.3826 / p+ 0.9630. If it does not, the chain is not the original one and
nothing downstream should be read.
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
COST, FILL = 1.9, 1.0
SIG_CH = "rvol_72h"
PANEL = MA + "/exports/wide_dl_full_fundfix.npz"

src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
z = np.load(PANEL, allow_pickle=True)
CHN = list(z["ch_names"]); SIG_IDX = CHN.index(SIG_CH)
KING_STORED = src.king.copy(); S2_STORED = src.s2.copy()

A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
print("anchors:", len(A), " (expect 9821)", flush=True)


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
            mag = np.clip(mag, lo, hi)                       # cap FIRST
        if self.lam and self._sig is not None and len(self._sig) == len(mag):
            mag = mag / np.power(self._sig, self.lam)        # then sigma
        return mag - mag.mean()                              # then demean


def run_lam(lam):
    ch = VolScaled(src, weights=W, funding_mode="rank", pos_cap_pct=99.0, lam=lam)
    res = CrossLegNetting(ch, W, cost_bps=COST).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    rows, prev = [], np.zeros(src.N)
    risk_top1, cw_sig, maxw = [], [], []
    for t in A:
        ti = int(t); ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        w = np.zeros(src.N); w[m] = p
        ok = np.isfinite(ret)
        contrib = np.where(ok, w * np.nan_to_num(ret), 0.0)
        gr = float(contrib.sum())
        tn = float(np.abs(w - prev).sum()); prev = w
        rows.append((pd.to_datetime(src.ts[ti], unit="ms", utc=True).strftime("%Y-%m"),
                     FILL * (gr - tn * COST * 1e-4), gr, tn))
        s = sigma_at(ti, m)
        if s is not None:
            aw = np.abs(p); okc = np.isfinite(aw) & np.isfinite(s)
            rc = aw * s
            if rc.sum() > 0:
                risk_top1.append(float(rc.max() / rc.sum()))
            if okc.sum() > 10:
                cw_sig.append(float(np.corrcoef(aw[okc], s[okc])[0, 1]))
        maxw.append(float(np.abs(p).max()))
    df = pd.DataFrame(rows, columns=["ym", "net", "gross", "turn"])
    g = df.groupby("ym").net.sum()
    return {"lam": lam, "monthly": g, "net": float(df.net.sum()),
            "gross_sum": float(df.gross.sum()), "turn": float(df.turn.sum()),
            "risk_top1": float(np.mean(risk_top1)), "corr_w_sigma": float(np.mean(cw_sig)),
            "maxw": float(np.mean(maxw))}


def teff(x):
    """REPRO §2.8/§2.8.1 — t_raw, estimator A (biased ACF), estimator B (pairwise Pearson), min."""
    x = np.asarray(x, float); n = len(x)
    t = x.mean() / (x.std(ddof=1) + 1e-12) * np.sqrt(n)
    xb = x.mean(); S = ((x - xb) ** 2).sum()
    rA = [float(((x[:-k] - xb) * (x[k:] - xb)).sum() / S) for k in range(1, 13)]
    rB = [float(np.corrcoef(x[:-k], x[k:])[0, 1]) for k in range(1, 13)]
    iA = 1.0 + 2.0 * sum(max(v, 0.0) for v in rA)
    iB = 1.0 + 2.0 * sum(max(v, 0.0) for v in rB)
    return dict(t_raw=t, infl_A=iA, infl_B=iB, t_eff_A=t / np.sqrt(iA), t_eff_B=t / np.sqrt(iB),
                t_eff_min=min(t / np.sqrt(iA), t / np.sqrt(iB)), n=n, p_pos=float((x > 0).mean()))


# ----------------------------------------------------------------- consistency anchor
print("\n" + "=" * 78)
print("CONSISTENCY ANCHOR — stored pred panels (must reproduce REPRO §1/§3.3)")
print("=" * 78, flush=True)
R0 = {l: run_lam(l) for l in (0.0, 1.0)}
d0 = (R0[1.0]["monthly"] - R0[0.0]["monthly"]).to_numpy()
st0 = teff(d0)
print("netSum(lam=0) = %.4f      [expect 9.8773]" % R0[0.0]["net"])
print("netSum(lam=1) = %.4f" % R0[1.0]["net"])
print("dNet          = %+.5f     [expect +1.81420]" % d0.sum())
print("t_raw         = %+.4f     [expect +10.3826]" % st0["t_raw"])
print("p+            = %.4f      [expect 0.9630]" % st0["p_pos"])
print("t_eff A/B/min = %+.4f / %+.4f / %+.4f   [expect +3.3142 / +3.0895 / +3.0895]"
      % (st0["t_eff_A"], st0["t_eff_B"], st0["t_eff_min"]))
print("risk_top1 lam0/lam1 = %.4f / %.4f   [expect 0.0556 / 0.0338]"
      % (R0[0.0]["risk_top1"], R0[1.0]["risk_top1"]))
print("corr(|w|,sigma) lam0/lam1 = %+.3f / %+.3f   [X1 expect +0.097 / -0.199]"
      % (R0[0.0]["corr_w_sigma"], R0[1.0]["corr_w_sigma"]))
ok_anchor = abs(R0[0.0]["net"] - 9.8773) < 1e-2 and abs(d0.sum() - 1.81420) < 0.05
print("ANCHOR %s" % ("PASS" if ok_anchor else "*** FAIL ***"), flush=True)

# ----------------------------------------------------------------- three calibers
out = {"anchor": {"netSum_lam0": R0[0.0]["net"], "dNet": float(d0.sum()), **{k: v for k, v in st0.items()},
                  "risk_top1_lam0": R0[0.0]["risk_top1"], "risk_top1_lam1": R0[1.0]["risk_top1"],
                  "corr_w_sigma_lam0": R0[0.0]["corr_w_sigma"], "corr_w_sigma_lam1": R0[1.0]["corr_w_sigma"],
                  "pass": bool(ok_anchor)},
       "arms": {}}
monthly_store = {"STORED": {"lam0": R0[0.0]["monthly"], "lam1": R0[1.0]["monthly"]}}

for arm in ("TRAIN", "SERVE", "CAUSAL"):
    kp = "/tmp/vs_pred_king_%s.npz" % arm; sp = "/tmp/vs_pred_s2_%s.npz" % arm
    if not (os.path.exists(kp) and os.path.exists(sp)):
        print("missing arm", arm); continue
    kk = np.load(kp)["pred"].astype(np.float64); ss = np.load(sp)["pred"].astype(np.float64)
    # universe must be caliber-invariant: assert the finite pattern is unchanged
    fk = np.isfinite(kk); fs = np.isfinite(ss)
    if arm == "TRAIN":
        base_fk, base_fs = fk.copy(), fs.copy()
        print("\n[TRAIN] finite-pattern vs STORED: king %s  s2 %s"
              % (np.array_equal(fk, np.isfinite(KING_STORED)), np.array_equal(fs, np.isfinite(S2_STORED))))
    same_u = np.array_equal(fk, base_fk) and np.array_equal(fs, base_fs)
    src.king = kk; src.s2 = ss
    A2 = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                           & np.isfinite(src.s2)).any(1))[0])
    same_A = np.array_equal(A2, A)
    if not same_A:
        print("*** WARNING arm %s: anchor set changed (%d vs %d). The book still uses the ORIGINAL A "
              "so the arms stay paired; reporting this as a finding." % (arm, len(A2), len(A)))
    print("\n" + "=" * 78)
    print("ARM %s   (universe identical to TRAIN: %s | anchor set identical: %s)" % (arm, same_u, same_A))
    print("=" * 78, flush=True)
    R = {l: run_lam(l) for l in (0.0, 1.0)}
    dd = (R[1.0]["monthly"] - R[0.0]["monthly"]).to_numpy()
    st = teff(dd)
    print("  netSum lam0 %.4f | lam1 %.4f | dNet %+.5f" % (R[0.0]["net"], R[1.0]["net"], dd.sum()))
    print("  t_raw %+.3f  t_eff A %+.3f  B %+.3f  min %+.3f  p+ %.3f"
          % (st["t_raw"], st["t_eff_A"], st["t_eff_B"], st["t_eff_min"], st["p_pos"]))
    print("  risk_top1 lam0 %.4f -> lam1 %.4f (%+.1f%%)"
          % (R[0.0]["risk_top1"], R[1.0]["risk_top1"],
             100 * (R[1.0]["risk_top1"] / R[0.0]["risk_top1"] - 1)))
    print("  corr(|w|,sigma) lam0 %+.3f lam1 %+.3f" % (R[0.0]["corr_w_sigma"], R[1.0]["corr_w_sigma"]))
    monthly_store[arm] = {"lam0": R[0.0]["monthly"], "lam1": R[1.0]["monthly"]}
    out["arms"][arm] = {"netSum_lam0": R[0.0]["net"], "netSum_lam1": R[1.0]["net"],
                        "dNet": float(dd.sum()), "turn_lam0": R[0.0]["turn"], "turn_lam1": R[1.0]["turn"],
                        "gross_lam0": R[0.0]["gross_sum"], "gross_lam1": R[1.0]["gross_sum"],
                        "risk_top1_lam0": R[0.0]["risk_top1"], "risk_top1_lam1": R[1.0]["risk_top1"],
                        "corr_w_sigma_lam0": R[0.0]["corr_w_sigma"], "corr_w_sigma_lam1": R[1.0]["corr_w_sigma"],
                        "universe_identical_to_TRAIN": bool(same_u),
                        "anchor_set_identical": bool(same_A), **st}
    print("  dGross %+.5f | dTurnCost %+.5f  (dNet = dGross - dTurnCost)"
          % (R[1.0]["gross_sum"] - R[0.0]["gross_sum"],
             (R[1.0]["turn"] - R[0.0]["turn"]) * COST * 1e-4))

# ----------------------------------------------------------------- paired caliber contrasts
print("\n" + "=" * 78); print("PAIRED CALIBER CONTRASTS  (monthly, same months, n=%d)" % len(d0))
print("=" * 78)
if all(a in monthly_store for a in ("TRAIN", "SERVE", "CAUSAL")):
    dser = {a: (monthly_store[a]["lam1"] - monthly_store[a]["lam0"]) for a in ("TRAIN", "SERVE", "CAUSAL")}
    J = pd.concat(dser, axis=1).dropna()
    out["paired"] = {}
    for a, b in (("SERVE", "TRAIN"), ("CAUSAL", "TRAIN"), ("CAUSAL", "SERVE")):
        diff = (J[a] - J[b]).to_numpy()
        s = teff(diff)
        print("  ΔNet(%s) − ΔNet(%s) = %+.5f   t_raw %+.3f  t_eff_min %+.3f  p+ %.3f"
              % (a, b, diff.sum(), s["t_raw"], s["t_eff_min"], s["p_pos"]))
        out["paired"]["%s_minus_%s" % (a, b)] = {"sum": float(diff.sum()), **s}
    J.to_json("/tmp/vs_monthly_dnet.json")

json.dump(out, open("/tmp/vs_book_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/vs_book_result.json + /tmp/vs_monthly_dnet.json", flush=True)
