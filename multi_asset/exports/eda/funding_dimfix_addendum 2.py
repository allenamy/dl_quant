"""0C addendum — (a) book-level funding P&L + per-leg attribution on the CORRECTED factor;
(b) ★ the test that makes the "do not retrain the DL" ruling FALSIFIABLE.

(b) rationale: funding_ema is an INPUT CHANNEL to king/s2. The dimension bug gives the channel a
group structure (4h-settled coins sit ~0.37 rank-units below 8h coins) that is an artifact, drifts
over time as coins migrate, and is therefore a potential free "which settlement group am I" indicator
the DL could have latched onto. The ruling not to retrain is defensible ONLY IF that structure did
not propagate into the DL predictions. Cheap decisive test, no retraining required:

  per anchor, over the tradeable set, compute the rank-centred group gap
      gap(x) = mean(rank_centred(x) | 4h coins) - mean(rank_centred(x) | 8h coins)
  for x in {shipped funding_ema, normalised funding_ema, king_pred, s2_pred, realised Y4}.

  - gap(king) ~ 0  and uncorrelated with gap(funding_shipped)  -> artifact did NOT propagate; ruling safe.
  - gap(king) tracks gap(funding_shipped) and is NOT matched by gap(Y4) -> the DL priced a group
    artifact; the caveat is materially worse than a caliber note and retraining moves up the queue.

gap(Y4) is the control: if the 4h group genuinely out/under-performs, a model SHOULD tilt.

Merges into funding_dimfix_rerun_raw.json.
"""
import os
import sys, json
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
EDA = MA + "/exports/eda/"
sys.path.insert(0, MA)
sys.path.insert(0, EDA)
import funding_dimfix_rerun as R      # reuses HELD/run/ev/anchors/day/yr and the panels

src, N, n = R.src, R.N, R.n
anchors, day, yr, years = R.anchors, R.day, R.yr, R.years

# ---------------- (a) book funding P&L + per-leg attribution, corrected ----------------
def book_funding(var):
    W = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
    H = R.HELD[(var, 1.0)]
    prev_unit = np.zeros(N); prev_c = {k: np.zeros(N) for k in W}; prev_res = np.zeros(N)
    F = np.zeros(n); FL = {k: np.zeros(n) for k in W}; FRES = np.zeros(n)
    for i in range(n):
        wv = np.array([W[k] for k in R.LEGS])
        combo = (H[i].astype(np.float64) * wv[:, None]).sum(0)
        base = combo - combo.mean()
        lo, hi = np.percentile(base, 1), np.percentile(base, 99)
        pos = np.clip(base, lo, hi); pos = pos - pos.mean(); g = np.abs(pos).sum()
        unit = pos / g if g > 1e-9 else pos
        contrib = {}
        for a, k in enumerate(R.LEGS):
            c = W[k] * H[i, a].astype(np.float64)
            contrib[k] = (c - c.mean()) / g if g > 1e-9 else c * 0.0
        res = unit - sum(contrib.values())
        fr = R.FRZ[i]
        F[i] = -float(np.sum(prev_unit * fr))
        for k in W:
            FL[k][i] = -float(np.sum(prev_c[k] * fr))
        FRES[i] = -float(np.sum(prev_res * fr))
        prev_unit, prev_c, prev_res = unit, contrib, res
    ann = lambda x: round(float(pd.DataFrame(dict(day=day, x=x)).groupby("day")["x"].sum().mean() * 365), 4)
    return dict(total_ann=ann(F), legs={k: ann(FL[k]) for k in W}, cap_resid=ann(FRES))


BF = {v: book_funding(v) for v in R.FUND}
for v, d in BF.items():
    print(f"  [{v}] book funding P&L {d['total_ann']*100:+.2f}%/yr | legs " +
          " ".join(f"{k}:{x*100:+.2f}" for k, x in d["legs"].items()) +
          f" | cap_resid {d['cap_resid']*100:+.3f}", flush=True)

# ---------------- (b) DL group-artifact propagation test ----------------
IH = R.IH
FS = R.FUND["shipped"]; FN = R.FUND["normfix"]


def rc(x):
    x = np.asarray(x, float); r = rankdata(x); k = len(r)
    return 2.0 * (r - 1) / (k - 1) - 1.0 if k > 1 else np.zeros_like(x)


rows = {"fund_shipped": [], "fund_norm": [], "king": [], "s2": [], "Y4": [], "yr": [], "n4": []}
for i, t in enumerate(anchors):
    ti = int(t); m = src.tradeable(ti)
    ih = IH[ti, m]
    ok = np.isfinite(ih)
    if ok.sum() < 20:
        continue
    is4 = (ih <= 4.0) & ok; is8 = (ih > 4.0) & ok
    if is4.sum() < 3 or is8.sum() < 3:
        continue
    y = src.Y4[ti, m]
    def gap(x):
        v = np.isfinite(x)
        if (v & is4).sum() < 3 or (v & is8).sum() < 3:
            return np.nan
        z = np.full(len(x), np.nan); z[v] = rc(x[v])
        return float(np.nanmean(z[is4]) - np.nanmean(z[is8]))
    rows["fund_shipped"].append(gap(FS[ti, m])); rows["fund_norm"].append(gap(FN[ti, m]))
    rows["king"].append(gap(src.king[ti, m])); rows["s2"].append(gap(src.s2[ti, m]))
    rows["Y4"].append(gap(y)); rows["yr"].append(int(yr[i])); rows["n4"].append(int(is4.sum()))

G = pd.DataFrame(rows).dropna()
print(f"\n[group-gap test] {len(G)} anchors with both groups present", flush=True)


def tstat(x):
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


SIG = {}
for k in ["fund_shipped", "fund_norm", "king", "s2", "Y4"]:
    SIG[k] = dict(mean=round(float(G[k].mean()), 4), t=round(tstat(G[k].values), 2),
                  by_year={int(y): round(float(g[k].mean()), 4) for y, g in G.groupby("yr")})
    print(f"  gap({k:13s}) mean {SIG[k]['mean']:+.4f}  t={SIG[k]['t']:+7.2f}  by-year " +
          " ".join(f"{y}:{v:+.3f}" for y, v in SIG[k]["by_year"].items()), flush=True)

CORR = {}
for k in ["king", "s2"]:
    CORR[k] = dict(vs_fund_shipped=round(float(np.corrcoef(G[k], G["fund_shipped"])[0, 1]), 4),
                   vs_fund_norm=round(float(np.corrcoef(G[k], G["fund_norm"])[0, 1]), 4),
                   vs_Y4=round(float(np.corrcoef(G[k], G["Y4"])[0, 1]), 4))
    print(f"  corr(gap({k}), gap(fund_shipped))={CORR[k]['vs_fund_shipped']:+.4f} | "
          f"vs gap(Y4)={CORR[k]['vs_Y4']:+.4f}", flush=True)

# how much of the DL leg's P&L would a pure group tilt explain? (bound the damage)
gk = G["king"].values; gy = G["Y4"].values
beta = float(np.polyfit(gk, gy, 1)[0]) if gk.std() > 0 else np.nan
verdict = ("SAFE: king's group tilt is small and not driven by the artifact channel"
           if abs(SIG["king"]["mean"]) < 0.05 and abs(CORR["king"]["vs_fund_shipped"]) < 0.15
           else "ESCALATE: king carries a group tilt aligned with the artifact")
print(f"\n  VERDICT: {verdict}", flush=True)

j = json.load(open(EDA + "funding_dimfix_rerun_raw.json"))
j["book_funding_attribution"] = BF
j["dl_group_artifact_test"] = dict(
    spec=("per anchor, rank-centred group gap = mean(4h-settled) - mean(8h-settled) over the tradeable "
          "cross-section; computed for the shipped funding channel, the normalised channel, king_pred, "
          "s2_pred and realised Y4. gap(Y4) is the control -- a real group return difference legitimises "
          "a model tilt. Contamination = gap(king) tracks gap(fund_shipped) without matching gap(Y4)."),
    n_anchors=int(len(G)), per_series=SIG, correlations=CORR,
    y4_on_king_gap_beta=round(beta, 4) if np.isfinite(beta) else None, verdict=verdict)
json.dump(j, open(EDA + "funding_dimfix_rerun_raw.json", "w"), indent=1, default=str)
print("MERGED addendum into funding_dimfix_rerun_raw.json", flush=True)
