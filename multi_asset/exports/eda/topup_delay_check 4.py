"""0C — does the +32pp "residual taker top-up" number survive the M1 benchmark problem?

> created 2026-07-25 | Session: 0C | 状态: final

THE PROBLEM (team-lead): in fee_fill_sensitivity.py the 'topup' convention sets `w = target` and
scores it against `RET = Y4[anchor]` -- the FULL anchor-to-anchor 4h return. So the residual taker
top-up is priced AT THE ANCHOR, while in reality it executes ~900s later, by which time part of the
predicted move has already happened. Delay cost here is NOT symmetric noise: we buy what we predict
will rise, so waiting is systematically adverse. That is alpha decaying into our own execution.

WHAT DECIDES THE MAGNITUDE: how front-loaded the book's alpha is. Rather than assume, measure it --
the panel carries both Y1 (1h fwd) and Y4 (4h fwd), so the share of the 4h P&L earned in hour 1 is
directly observable on the ACTUAL book positions.

  f1        = E[book P&L over hour 1] / E[book P&L over 4h]      (0.25 would be linear accrual)
  share_900 = fraction of the 4h alpha already gone at +900s
              central : f1/4    (linear WITHIN hour 1)
              upper   : f1      (all of hour-1 alpha in the first 900s -- extreme front-loading)
  delay cost on the delayed notional, per unit traded:
              alpha_per_anchor_bps * share_900
  added effective cost across ALL turnover, for the top-up leg only:
              (1-phi) * alpha_per_anchor_bps * share_900
  revision to the +32pp claim:
              added_c_bps * 14.66 pp/bps      (§5 slope, dimension-fixed)

Writes exports/eda/topup_delay_check.json.
"""
import os
import sys, json
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
EDA = MA + "/exports/eda/"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource

CAD = {"king": 4, "s2": 24, "funding": 8, "size": 24}
LEGS = ["king", "s2", "funding", "size"]
W = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
PP_PER_BPS = 14.66            # §5 slope, dimension-fixed current weights
PHI_REF = 0.51                # the phi at which the +32pp comparison was made

src = PanelSource(); N = src.N
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
day = (src.ts[anchors] // 86400000).astype(np.int64)
YRS = (int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (86400000 * 365.25)
n = len(anchors)


def _z(x):
    x = np.asarray(x, float); m = np.isfinite(x); o = np.zeros_like(x)
    if m.sum() >= 3 and x[m].std() > 1e-12:
        o[m] = (x[m] - x[m].mean()) / x[m].std()
    return o


def _rank(x):
    x = np.asarray(x, float); m = np.isfinite(x); o = np.zeros_like(x)
    if m.sum() >= 3:
        r = rankdata(x[m]); k = len(r); o[m] = 2.0 * (r - 1) / (k - 1) - 1.0 if k > 1 else 0.0
    return o


def _l1(x):
    g = np.abs(x).sum(); return x / g if g > 1e-9 else x


held = {k: np.zeros(N) for k in LEGS}; prev = np.zeros(N)
p1 = np.zeros(n); p4 = np.zeros(n); turn = np.zeros(n)
# delta-only P&L: alpha earned specifically by the NEWLY TRADED portion (the part a top-up delays)
d1 = np.zeros(n); d4 = np.zeros(n)
for i, t in enumerate(anchors):
    ti = int(t); m = src.tradeable(ti)
    lp = {"king": _l1(_z(src.king[ti, m])), "s2": _l1(_z(src.s2[ti, m])),
          "funding": _l1(-_rank(src.CH[ti, m, src.fund_idx].astype(float))),
          "size": _l1(_z(src.CH[ti, m, src.size_idx].astype(float)))}
    for k in LEGS:
        if i == 0 or ti % CAD[k] == 0:
            nw = np.zeros(N); nw[m] = lp[k]; held[k] = nw
    combo = sum(W[k] * held[k] for k in LEGS)
    base = combo - combo.mean()
    lo, hi = np.percentile(base, 1), np.percentile(base, 99)
    pos = np.clip(base, lo, hi); pos = pos - pos.mean(); g = np.abs(pos).sum()
    unit = pos / g if g > 1e-9 else pos
    r1 = src.Y1[ti]; r4 = src.Y4[ti]
    ok1 = np.isfinite(r1); ok4 = np.isfinite(r4)
    p1[i] = float(np.nansum(unit[ok1] * r1[ok1])); p4[i] = float(np.nansum(unit[ok4] * r4[ok4]))
    d = unit - prev
    d1[i] = float(np.nansum(d[ok1] * r1[ok1])); d4[i] = float(np.nansum(d[ok4] * r4[ok4]))
    turn[i] = float(np.abs(d).sum())
    prev = unit

alpha4_bps = float(np.mean(p4)) * 1e4
alpha1_bps = float(np.mean(p1)) * 1e4
f1_book = alpha1_bps / alpha4_bps
d4_bps = float(np.mean(d4)) * 1e4
d1_bps = float(np.mean(d1)) * 1e4
f1_delta = d1_bps / d4_bps if d4_bps != 0 else np.nan
turn_anchor = float(np.mean(turn))
print(f"anchors {n} | turnover/anchor {turn_anchor:.4f} (ann {turn.sum()/YRS:.0f})", flush=True)
print(f"book  P&L/anchor: 1h {alpha1_bps:+.3f} bps | 4h {alpha4_bps:+.3f} bps -> f1 = {f1_book:.3f} "
      f"(0.25 = linear accrual)", flush=True)
print(f"delta P&L/anchor: 1h {d1_bps:+.3f} bps | 4h {d4_bps:+.3f} bps -> f1_delta = {f1_delta:.3f}  "
      f"<- the newly traded portion is what a top-up delays", flush=True)

# alpha per unit of TRADED notional over 4h (the delta leg's own alpha density)
alpha_per_traded_bps = d4_bps / turn_anchor
print(f"alpha per unit TRADED notional over 4h: {alpha_per_traded_bps:.3f} bps", flush=True)

out = {}
for label, f1 in [("book_wide", f1_book), ("delta_only(preferred)", f1_delta)]:
    for sh_label, share in [("central: linear within hour1 (f1/4)", f1 / 4.0),
                            ("upper: all of hour-1 alpha in first 900s (f1)", f1)]:
        lost_per_traded = alpha_per_traded_bps * share
        added_c = (1 - PHI_REF) * lost_per_traded
        pp = added_c * PP_PER_BPS
        out[f"{label} | {sh_label}"] = dict(
            share_of_4h_alpha_gone_at_900s=round(float(share), 4),
            forfeited_bps_per_unit_traded=round(float(lost_per_traded), 4),
            added_effective_cost_bps=round(float(added_c), 4),
            revision_pp_per_yr=round(float(-pp), 2),
            topup_value_revised_pp=round(32.0 - float(pp), 1))
        print(f"  [{label:22s}] {sh_label:48s} -> added c {added_c:.3f} bps, "
              f"+32pp becomes {32.0-pp:+.1f}pp", flush=True)

# does the qualitative conclusion (top-up mandatory) survive even at the extreme?
worst = min(v["topup_value_revised_pp"] for v in out.values())
print(f"\n  worst-case revised top-up value: +{worst:.1f} pp/yr -> "
      f"{'CONCLUSION SURVIVES (top-up still mandatory)' if worst > 0 else 'CONCLUSION BREAKS'}", flush=True)

json.dump(dict(title="Does the +32pp top-up claim survive the anchor-price execution assumption?",
               created="2026-07-25", auditor="0C",
               confirmed_defect=("fee_fill_sensitivity.py L142-143 sets w = target and L152 scores it "
                                 "against Y4[anchor] -- the residual taker top-up is priced AT THE ANCHOR "
                                 "while it really executes ~900s later. Delay is systematically adverse "
                                 "(we buy what we predict rises), so the +32pp is OVERSTATED."),
               measured=dict(alpha_4h_bps_per_anchor=round(alpha4_bps, 4),
                             alpha_1h_bps_per_anchor=round(alpha1_bps, 4),
                             f1_book=round(f1_book, 4), f1_delta=round(f1_delta, 4),
                             delta_4h_bps=round(d4_bps, 4),
                             alpha_per_unit_traded_bps=round(alpha_per_traded_bps, 4),
                             turnover_per_anchor=round(turn_anchor, 4)),
               phi_reference=PHI_REF, pp_per_bps=PP_PER_BPS, scenarios=out,
               worst_case_revised_topup_pp=round(worst, 1),
               caveats=["hour-1 is the finest horizon in the panel; the 900s share within hour 1 cannot be "
                        "measured here, hence the central/upper bracket",
                        "the maker leg is ALSO filled with delay in reality; that cost is common to both "
                        "conventions and largely cancels in the DIFFERENCE, so it is not charged here",
                        "first-order: assumes the traded delta has the alpha density measured on the delta "
                        "leg itself (f1_delta / alpha_per_unit_traded), not the book average",
                        "pilot measures this directly once mid_at_anchor is in the schema (schema v2) -- "
                        "this estimate is superseded the moment real fills exist"]),
          open(EDA + "topup_delay_check.json", "w"), indent=1, default=str)
print("SAVED exports/eda/topup_delay_check.json", flush=True)
