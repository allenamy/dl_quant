"""agreement3.py — PREREG_incremental_retrain §1 secondary reading (warm-start arms W1/W2): adjacent-month agreement (per-anchor Spearman model_t vs model_{t−1} on month t's anchors)
for the two early-stop arms (FLOOR5 = mE1cF5, FIX7 = mE1cX7) next to CONST (mE1c), monthly s42 (seed per fold) and monthly s2027; plus same-month agreement
of each arm vs CONST and vs yearly s42 (own test year rows of the yearly file). Same method as §11 agreement.py. → warmstart/results/agreement3.json + agreement2_tables.md"""
import os, json, glob, time
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"; W = "/workspace/review_scratch/dl_monthly_wf"
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; nA = len(E)
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E]); MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
def load_monthly(pattern):
    out = {}
    for p in glob.glob(pattern):
        z = np.load(p); ymk = int(os.path.basename(p).split("_")[-1][:6]); out[ymk] = (int(z["first_te"]), z["P"])
    return out
SER = {"monthly_s42": load_monthly(f"{W}/preds_fold/mE1_*.npz"), "monthly_s2027": load_monthly(f"{B}/mwf_s2027/shard*/preds_fold/mE1_*.npz"), "CONST42": load_monthly(f"{B}/mE1_constseed/shard*/preds_fold/mE1c_*.npz"),
       "W1": load_monthly(f"{B}/warmstart/W1/preds_fold/mE1w1_*.npz"), "W2": load_monthly(f"{B}/warmstart/W2/preds_fold/mE1w2_*.npz")}
_w1f5 = load_monthly(f"{B}/warmstart/W1F5/preds_fold/mE1w1F5_*.npz")
if sorted(_w1f5) == MONTHS: SER["W1F5"] = _w1f5
_f5 = load_monthly(f"{B}/earlystop/FLOOR5/shard*/preds_fold/mE1cF5_*.npz")
if sorted(_f5) == MONTHS: SER["FLOOR5"] = _f5
for k, v in SER.items(): assert sorted(v) == MONTHS, (k, sorted(v))
nB = len(np.load("/workspace/data/dlw_targets.npz", allow_pickle=True)["E_ts"]); YE = np.full((nA, 829), np.nan, np.float32); YE[:nB] = np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy")
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
OUT = {"adjacent_month": {}, "same_month_vs": {}}; T = []
def p(s=""): T.append(s); print(s)
p("## AG3-1 · Adjacent-month agreement: per-anchor Spearman(model_t, model_{t−1}) on month t's anchors; distribution over anchors 2025-02→2026-08 and per-month means")
p("| series | n | mean | median | p10 | p90 | " + " | ".join(str(m)[2:] for m in MONTHS[1:]) + " |"); p("|---|---|---|---|---|---|" + "---|" * len(MONTHS[1:]))
for name, S in SER.items():
    allr = []; per = {}
    for k in range(1, len(MONTHS)):
        t, tm1 = MONTHS[k], MONTHS[k - 1]; idx = np.where(ym == t)[0]; r = rho_series(lambda i: row_of(S, t, i), lambda i: row_of(S, tm1, i), idx); per[str(t)] = stats(r); allr.append(r)
    allr = np.concatenate(allr); OUT["adjacent_month"][name] = {"all": stats(allr), "per_month": per}; st = OUT["adjacent_month"][name]["all"]
    p(f"| {name} | {st['n']} | {st['mean']:+.3f} | {st['median']:+.3f} | {st['p10']:+.3f} | {st['p90']:+.3f} | " + " | ".join(f"{per[str(m)]['mean']:+.2f}" for m in MONTHS[1:]) + " |")
p()
p("## AG3-2 · Same-month agreement (age 1) of each arm vs CONST42, vs monthly s42, and vs the yearly s42 file (own test year rows), 2025-01→2026-08 anchors")
p("| pair | n | mean | median | p10 | p90 |"); p("|---|---|---|---|---|---|")
for a in [x for x in ("W1", "W2", "W1F5", "CONST42") if x in SER]:
    for b in ("CONST42", "monthly_s42", "yearly_s42"):
        if a == b: continue
        rr = []
        for t in MONTHS:
            idx = np.where(ym == t)[0]
            if b == "yearly_s42": rr.append(rho_series(lambda i: row_of(SER[a], t, i), lambda i: (YE[i] if np.isfinite(YE[i]).any() else None), idx))
            else: rr.append(rho_series(lambda i: row_of(SER[a], t, i), lambda i: row_of(SER[b], t, i), idx))
        st = stats(np.concatenate(rr)); OUT["same_month_vs"][f"{a} vs {b}"] = st; p(f"| {a} vs {b} | {st['n']} | {st['mean']:+.3f} | {st['median']:+.3f} | {st['p10']:+.3f} | {st['p90']:+.3f} |")
os.makedirs(f"{B}/warmstart/results", exist_ok=True); json.dump(OUT, open(f"{B}/warmstart/results/agreement3.json", "w"), indent=1); open(f"{B}/warmstart/results/agreement3_tables.md", "w").write("\n".join(T) + "\n"); print("AGREEMENT3_DONE", flush=True)
