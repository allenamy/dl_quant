"""Step 1 of the tiered decision tree: what does net-beta NEUTRALISATION cost, and what does it fix?

> **创建:** 2026-08-04 02:2x UTC | **Session:** B4-retrain | **状态:** final
> **裁定(阈值先于数据):** team-lead 2026-08-04 —— 采纳门 = **rank-IC 相对降幅 ≤ 2%**
>   **且 TIMING 拖累消除 ≥ 80%**。采纳 ⇒ 在中性化书下重跑 tilt 判据(plain 有望复位);
>   否决 ⇒ 回退生效(xattn-clean 转正)。
> **作废条件:** 中性化定义(投影因子集)改变 ⇒ 重跑

WHY. Pricing the tilt channel showed the problem is not plain's quirk but a **shared structural
drag**: both clean models lose on beta timing (−560 / −352 bps/yr of gross), plain merely more. That
makes "which architecture" the wrong first question. The prior one is whether the deployed book
should carry any net beta at all.

NEUTRALISATION, and why it projects out TWO vectors not one. Per anchor, regress the weights on
`[1, beta_24h]` and keep the residual, then renormalise to unit gross:

    w_neut = w − proj_{span(1, β)} w      ⇒  Σ w_neut = 0  AND  Σ w_neut·β = 0

Projecting out β alone would break dollar-neutrality, because β has a non-zero cross-sectional mean —
so removing a multiple of β silently reintroduces a net long/short. Both constraints or neither.

★ ONE ARM OF THE GATE IS TRUE BY CONSTRUCTION, AND SAYING SO IS THE POINT. After this projection
  `netβ ≡ 0`, so the timing channel is eliminated by definition — that arm cannot fail and is not
  evidence of anything. **The gate's whole informational content is the OTHER arm: what rank-IC the
  projection destroys.** Reporting "timing drag eliminated 100%" as if it were a finding would be
  reporting the definition back as a result.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os.path as _p
import sys

import numpy as np
from scipy.stats import rankdata

_HERE = _p.dirname(_p.abspath(__file__))
sys.path.insert(0, _p.dirname(_p.dirname(_p.dirname(_HERE))))

_spec = importlib.util.spec_from_file_location(
    "pt", _p.join(_HERE, "price_tilt_timing_channel.py"))
PT = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PT)

ANCHORS_PER_YEAR = 365 * 6


def unit_gross(w):
    s = np.abs(w).sum()
    return w / s if s > 1e-12 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    z = np.load(a.panel, allow_pickle=True)
    chn = [str(x) for x in z["ch_names"]]
    beta = z["CH"][:, :, chn.index("beta_24h")]
    member, CL, YR, Y4 = z["MEMBER110"], z["CL4"], z["YR4"], z["Y4"]
    m = PT.LX.market_series(a.source)
    hold = PT.window(m, PT.HOLD_LO, PT.HOLD_HI)

    rec = {}
    for spec in a.runs:
        name, d = spec.split("=", 1)
        rows, nb0, nb1 = [], [], []
        ic0, ic1, icr0, icr1, p0, p1 = [], [], [], [], [], []
        f = 0
        while _p.exists(_p.join(d, f"fold_{f}_head_scores.npz")):
            zz = np.load(_p.join(d, f"fold_{f}_head_scores.npz"))
            sc, te = zz["scores"], zz["te_rows"]
            for i in te:
                base = np.where(member[i] & CL[i] & np.isfinite(YR[i]) & np.isfinite(Y4[i])
                                & np.isfinite(beta[i]))[0]
                if base.size < 5:
                    continue
                comp = np.zeros(base.size); nk = 0
                for k in range(sc.shape[2]):
                    col = sc[i, base, k]
                    if np.isfinite(col).all() and col.std() > 1e-12:
                        comp += (col - col.mean()) / col.std(); nk += 1
                if nk == 0:
                    continue
                w = unit_gross(comp / nk - (comp / nk).mean())
                if w is None:
                    continue
                b = beta[i, base].astype(np.float64)
                X = np.column_stack([np.ones(len(b)), b])
                coef, *_ = np.linalg.lstsq(X, w, rcond=None)
                wn = unit_gross(w - X @ coef)
                if wn is None:
                    continue
                y4, yr = Y4[i, base].astype(np.float64), YR[i, base].astype(np.float64)
                rows.append(int(i))
                nb0.append(float((w * b).sum())); nb1.append(float((wn * b).sum()))
                ic0.append(np.corrcoef(rankdata(w), rankdata(yr))[0, 1])
                ic1.append(np.corrcoef(rankdata(wn), rankdata(yr))[0, 1])
                icr0.append(np.corrcoef(rankdata(w), rankdata(y4))[0, 1])
                icr1.append(np.corrcoef(rankdata(wn), rankdata(y4))[0, 1])
                p0.append(float((w * y4).sum())); p1.append(float((wn * y4).sum()))
            f += 1
        rows = np.array(rows)
        nb0, nb1 = np.array(nb0), np.array(nb1)
        h = hold[rows]

        def split(nb):
            st = float(nb.mean() * h.mean()) * ANCHORS_PER_YEAR * 1e4
            tm = float(np.mean((nb - nb.mean()) * (h - h.mean()))) * ANCHORS_PER_YEAR * 1e4
            return st, tm

        s0, t0 = split(nb0)
        s1, t1 = split(nb1)
        IC0, IC1 = float(np.nanmean(ic0)), float(np.nanmean(ic1))
        R0, R1 = float(np.nanmean(icr0)), float(np.nanmean(icr1))
        L0 = float(np.mean(p0)) * ANCHORS_PER_YEAR * 1e4
        L1 = float(np.mean(p1)) * ANCHORS_PER_YEAR * 1e4
        d_ic = (IC1 - IC0) / abs(IC0) * 100
        elim = (1 - abs(t1) / abs(t0)) * 100 if abs(t0) > 1e-12 else float("nan")
        print(f"\n===== {name} =====  n={len(rows)}")
        print(f"  netβ            {nb0.mean():+.6f}  ->  {nb1.mean():+.6f}  (|max| after "
              f"{np.abs(nb1).max():.2e})")
        print(f"  rank-IC vs YR4  {IC0:+.5f}  ->  {IC1:+.5f}   ({d_ic:+.2f}%)   ← THE INFORMATIVE ARM")
        print(f"  rank-IC vs Y4   {R0:+.5f}  ->  {R1:+.5f}   ({(R1-R0)/abs(R0)*100:+.2f}%)")
        print(f"  TIMING bps/yr   {t0:+.1f}  ->  {t1:+.1f}   (eliminated {elim:.1f}% — TRUE BY "
              f"CONSTRUCTION, not evidence)")
        print(f"  STATIC bps/yr   {s0:+.1f}  ->  {s1:+.1f}")
        print(f"  leg P&L bps/yr  {L0:+.1f}  ->  {L1:+.1f}   (Σw·Y4, gross)")
        gate = (d_ic >= -2.0) and (elim >= 80.0)
        print(f"  ⇒ adoption gate (ΔrankIC ≥ −2% AND timing eliminated ≥80%): "
              f"{'PASS' if gate else 'FAIL'}")
        rec[name] = dict(n=len(rows), netbeta_before=round(float(nb0.mean()), 6),
                         netbeta_after=round(float(nb1.mean()), 8),
                         rank_ic_YR_before=round(IC0, 5), rank_ic_YR_after=round(IC1, 5),
                         rank_ic_YR_pct_change=round(d_ic, 3),
                         rank_ic_Y4_before=round(R0, 5), rank_ic_Y4_after=round(R1, 5),
                         timing_before=round(t0, 2), timing_after=round(t1, 2),
                         timing_eliminated_pct=round(float(elim), 2),
                         static_before=round(s0, 2), static_after=round(s1, 2),
                         leg_pnl_bps_before=round(L0, 2), leg_pnl_bps_after=round(L1, 2),
                         gate_pass=bool(gate))
    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"\nrecord -> {a.out}")


if __name__ == "__main__":
    main()
