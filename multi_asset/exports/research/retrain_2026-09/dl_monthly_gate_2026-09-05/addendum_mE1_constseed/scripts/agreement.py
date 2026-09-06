"""agreement.py — addendum §11 diagnostic: how much do consecutive refits agree? Per-anchor Spearman between two models' raw scores over the members of the
same anchor (finite in both). Series:
  monthly s42   : /workspace/review_scratch/dl_monthly_wf/preds_fold/mE1_{YM}.npz         (P = scores for every anchor >= first_te; per-fold seed 42+YM)
  monthly s2027 : allweather_trackB/mwf_s2027/shard*/preds_fold/mE1_{YM}.npz               (per-fold seed 2027+YM)
  monthly const : allweather_trackB/mE1_constseed/shard*/preds_fold/mE1c_{YM}.npz          (seed 42 for every fold)
  yearly s42/s2027: allweather_trackB/mE1_constseed/yearly_out/preds_fold/f10_V2MAIN_YS_s{S}_{YV}.npz (gate form + yearly_save patch)
Adjacent-month agreement at month t = Spearman(model_t on month-t anchors, model_{t-1} on month-t anchors) (age 1 vs age 2), t = 2025-02..2026-08.
Yearly boundary agreement at year Y = Spearman(model_Y on year-Y anchors, model_{Y-1} on year-Y anchors), over the whole year and over its first month.
Seed-to-seed agreement (same month, both age 1): monthly s42 vs s2027; monthly const vs s42; yearly s42 vs s2027 (own test year).
Outputs mE1_constseed/results/agreement.json + agreement_tables.md. usage: agreement.py"""
import os, json, glob, time
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"; W = "/workspace/review_scratch/dl_monthly_wf"
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; yrs = A["yrs"].astype(int); nA = len(E)
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E]); MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
def load_monthly(pattern):
    out = {}
    for p in glob.glob(pattern):
        z = np.load(p); ymk = int(os.path.basename(p).split("_")[-1][:6]); out[ymk] = (int(z["first_te"]), z["P"])
    return out
SER = {"monthly_s42": load_monthly(f"{W}/preds_fold/mE1_*.npz"), "monthly_s2027": load_monthly(f"{B}/mwf_s2027/shard*/preds_fold/mE1_*.npz"), "monthly_const42": load_monthly(f"{B}/mE1_constseed/shard*/preds_fold/mE1c_*.npz")}
for k, v in SER.items(): assert sorted(v) == MONTHS, (k, sorted(v))
YS = {}
for s in ("42", "2027"):
    d = {}
    for yv in (2023, 2024, 2025, 2026):
        p = f"{B}/mE1_constseed/yearly_out/preds_fold/f10_V2MAIN_YS_s{s}_{yv}.npz"
        if os.path.exists(p): z = np.load(p); d[yv] = (int(z["first_te"]), z["P"])
    YS[s] = d
def rho_series(getA, getB, idx):
    out = []
    for i in idx:
        m = MEM[i]; a = getA(i); b = getB(i)
        if a is None or b is None: continue
        a = a[m]; b = b[m]; ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() >= 30: out.append(spearmanr(a[ok], b[ok]).correlation)
    return np.array(out)
def stats(x): return {"n": int(len(x)), "mean": float(np.mean(x)), "median": float(np.median(x)), "p10": float(np.percentile(x, 10)), "p90": float(np.percentile(x, 90))} if len(x) else {"n": 0}
def row_of(series, model_ym, i):
    f0, P = series[model_ym]; r = i - f0; return P[r] if 0 <= r < len(P) else None
OUT = {"adjacent_month": {}, "seed_to_seed_age1": {}, "yearly_boundary": {}, "yearly_seed_to_seed": {}}
T = []
def p(s=""): T.append(s); print(s)
p("## AG-1 · Adjacent-month agreement: per-anchor Spearman(model_t, model_{t−1}) on month t's anchors (age 1 vs age 2); distribution over anchors 2025-02→2026-08 and per month (mean)")
p("| series | n anchors | mean | median | p10 | p90 | " + " | ".join(str(m)[2:] for m in MONTHS[1:]) + " |"); p("|---|---|---|---|---|---|" + "---|" * len(MONTHS[1:]))
for name, S in SER.items():
    allr = []; per = {}
    for k in range(1, len(MONTHS)):
        t, tm1 = MONTHS[k], MONTHS[k - 1]; idx = np.where(ym == t)[0]
        r = rho_series(lambda i: row_of(S, t, i), lambda i: row_of(S, tm1, i), idx); per[str(t)] = stats(r); allr.append(r)
    allr = np.concatenate(allr); OUT["adjacent_month"][name] = {"all": stats(allr), "per_month": per}
    st = OUT["adjacent_month"][name]["all"]; p(f"| {name} | {st['n']} | {st['mean']:+.3f} | {st['median']:+.3f} | {st['p10']:+.3f} | {st['p90']:+.3f} | " + " | ".join(f"{per[str(m)]['mean']:+.2f}" for m in MONTHS[1:]) + " |")
p()
p("## AG-2 · Seed-to-seed agreement at age 1 (same month, model_t vs model_t of the other series) over 2025-01→2026-08 anchors")
p("| pair | n anchors | mean | median | p10 | p90 |"); p("|---|---|---|---|---|---|")
for a, b in (("monthly_s42", "monthly_s2027"), ("monthly_const42", "monthly_s42"), ("monthly_const42", "monthly_s2027")):
    rr = []
    for t in MONTHS:
        idx = np.where(ym == t)[0]; rr.append(rho_series(lambda i: row_of(SER[a], t, i), lambda i: row_of(SER[b], t, i), idx))
    st = stats(np.concatenate(rr)); OUT["seed_to_seed_age1"][f"{a} vs {b}"] = st; p(f"| {a} vs {b} | {st['n']} | {st['mean']:+.3f} | {st['median']:+.3f} | {st['p10']:+.3f} | {st['p90']:+.3f} |")
p()
p("## AG-3 · Yearly-fold boundary agreement: Spearman(model_Y, model_{Y−1}) on year-Y anchors (whole year / first month of Y); yearly_save runs (gate form, seeds 42 and 2027)")
p("| seed | year | n (year) | mean | median | p10 | p90 | n (first month) | mean (first month) | p10 (first month) |"); p("|---|---|---|---|---|---|---|---|---|---|")
for s, d in YS.items():
    OUT["yearly_boundary"][s] = {}
    for yv in (2024, 2025, 2026):
        if yv not in d or yv - 1 not in d: continue
        idx = np.where(yrs == yv)[0]; r = rho_series(lambda i: row_of(d, yv, i), lambda i: row_of(d, yv - 1, i), idx)
        idx1 = np.where(ym == yv * 100 + 1)[0]; r1 = rho_series(lambda i: row_of(d, yv, i), lambda i: row_of(d, yv - 1, i), idx1)
        OUT["yearly_boundary"][s][str(yv)] = {"year": stats(r), "first_month": stats(r1)}; a_, b_ = stats(r), stats(r1)
        p(f"| {s} | {yv} | {a_['n']} | {a_['mean']:+.3f} | {a_['median']:+.3f} | {a_['p10']:+.3f} | {a_['p90']:+.3f} | {b_['n']} | {b_['mean']:+.3f} | {b_['p10']:+.3f} |")
    if all(yv in d for yv in (2024, 2025, 2026)):
        allr = np.concatenate([rho_series(lambda i, yv=yv: row_of(d, yv, i), lambda i, yv=yv: row_of(d, yv - 1, i), np.where(yrs == yv)[0]) for yv in (2024, 2025, 2026)])
        OUT["yearly_boundary"][s]["all_2024_2026"] = stats(allr); st = stats(allr); p(f"| {s} | 2024→26 all | {st['n']} | {st['mean']:+.3f} | {st['median']:+.3f} | {st['p10']:+.3f} | {st['p90']:+.3f} | | | |")
if all(len(YS[s]) == 4 for s in ("42", "2027")):
    rr = [rho_series(lambda i, yv=yv: row_of(YS["42"], yv, i), lambda i, yv=yv: row_of(YS["2027"], yv, i), np.where(yrs == yv)[0]) for yv in (2024, 2025, 2026)]
    st = stats(np.concatenate(rr)); OUT["yearly_seed_to_seed"]["s42 vs s2027 own test year 2024-26"] = st; p(f"\n- yearly seed-to-seed (s42 vs s2027, own test year, 2024→26): n {st['n']} mean {st['mean']:+.3f} median {st['median']:+.3f} p10 {st['p10']:+.3f} p90 {st['p90']:+.3f}")
os.makedirs(f"{B}/mE1_constseed/results", exist_ok=True); json.dump(OUT, open(f"{B}/mE1_constseed/results/agreement.json", "w"), indent=1); open(f"{B}/mE1_constseed/results/agreement_tables.md", "w").write("\n".join(T) + "\n"); print("AGREEMENT_DONE", flush=True)
