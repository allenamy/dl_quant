"""simulate_gates.py — dl_monthly_gate step 2 (PREREG §A2; CPU). Per-model × per-month score quantities and the causal swap-rule simulation.
Quantities for model M (test month YM_M, cutoff before its first anchor) and month m >= YM_M, from preds_fold/{TAG}_{YM}.npz (verified against re-inference):
  IC(M, m)  = mean over month-m anchors of the per-anchor rank IC (Spearman over members with finite score and finite y4s, >= 30 pairs)
  LEG(M, m) = mean over month-m anchors of the F10 rank-leg return: z = rank position of the score among members (rankdata/(n-1) - 0.5), 0 where y4s is NaN,
              demeaned over finite y; leg = Σ(z/Σ|z| · y4s)·1e4 bps per unit gross; y4s = Π(1+r5)−1 (accounting caliber); price only (no carry/cost) = the seat-input definition
Arms (decision for month t uses only information up to the end of month t−1; MONTHS = 2025-01..2026-08; F(m) = fold model with test month m):
  R0  always newest: deploy F(t) at month t (age 1)                       [= the live monthly full-history refit form; equals the stitched mE1/mE60 file]
  R1  gate-IC : candidate C = F(t−1); swap iff IC(C, t−1) >= IC(I, t−1) − 0.002 (I = incumbent, scored on t−1 at its current age); else I continues
  R2  gate-leg: swap iff LEG(C, t−1) >= LEG(I, t−1) − 0.10 bps/anchor
  R3  both    : R1 and R2
  R4  absolute: swap iff IC(C, t−1) > 0
  initial incumbent F(2025-01) at t = 2025-01; at t = 2025-02 the candidate F(2025-01) IS the incumbent (no comparison; continues at age 2)
Outputs (under dl_monthly_gate/): series/{TAG}_{ARM}.npy (ext grid, NaN outside 2025-01..2026-08-30), results/decisions_{TAG}.json, results/score_{TAG}.json,
  replay/dev_alt/f8_2026-08-22/preds/f10_gate_{TAG}_{ARM}_s42.npy (0822 grid, spliced: yearly s42 rows before 2025-01-01, arm rows from 2025-01-01).
usage: simulate_gates.py <TAG>"""
import os, sys, json, time, calendar, hashlib
import numpy as np
from scipy.stats import spearmanr, rankdata
W = "/workspace/review_scratch/dl_monthly_wf"; G = "/workspace/review_scratch/dl_monthly_gate"; YEARLY = "/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"
TAG = sys.argv[1]; NB = 2000; SEED = 20260905
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; nA = len(E)
B = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); nB = len(B["E_ts"]); assert np.array_equal(E[:nB], B["E_ts"].astype(np.int64))
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T2503 = calendar.timegm((2025, 3, 1, 0, 0, 0)); T26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
i25 = int(np.searchsorted(E, T25)); assert E[i25] == T25
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E]); days = E // 86400
MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]; K = len(MONTHS); midx = {m: k for k, m in enumerate(MONTHS)}
MB = {m: (int(np.where(ym == m)[0][0]), int(np.where(ym == m)[0][-1])) for m in MONTHS}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def ic_anchor(s, y):
    ok = np.isfinite(s) & np.isfinite(y); return float(spearmanr(s[ok], y[ok]).correlation) if ok.sum() >= 30 else np.nan
def leg_anchor(s, y):
    oks = np.isfinite(s); oky = np.isfinite(y)
    if oks.sum() < 10 or oky.sum() < 10: return np.nan
    z = np.full(len(s), np.nan); z[oks] = rankdata(s[oks]) / max(oks.sum() - 1, 1) - 0.5; z = np.nan_to_num(z); z = np.where(oky, z, 0.0); z -= z[oky].mean()
    g = np.abs(z).sum(); return float((z / g * np.nan_to_num(y)).sum() * 1e4) if g > 1e-9 else np.nan
# ── per-model per-anchor series (anchors >= first_te) ──
PF = {}; ICA = {}; LGA = {}
for m in MONTHS:
    z = np.load(f"{W}/preds_fold/{TAG}_{m}.npz"); f0 = int(z["first_te"]); P = z["P"]; assert f0 == MB[m][0]; PF[m] = (f0, P)
    ic = np.full(nA, np.nan); lg = np.full(nA, np.nan)
    for i in range(f0, nA):
        mm = MEM[i]; s = P[i - f0, mm]; y = Y4[i, mm]; ic[i] = ic_anchor(s, y); lg[i] = leg_anchor(s, y)
    ICA[m] = ic; LGA[m] = lg
print(f"[{TAG}] per-model series done for {len(PF)} models", flush=True)
ICM = np.full((K, K), np.nan); LGM = np.full((K, K), np.nan)   # [model k][month j]
for k, m in enumerate(MONTHS):
    for j in range(k, K):
        f, l = MB[MONTHS[j]]; ICM[k, j] = float(np.nanmean(ICA[m][f:l + 1])); LGM[k, j] = float(np.nanmean(LGA[m][f:l + 1]))
# ── arms ──
RULES = ["R0", "R1", "R2", "R3", "R4"]; SER = {}; DEC = {}
for rule in RULES:
    inc = 0; S = np.full((nA, 829), np.nan, np.float32); rows = []
    for k, t in enumerate(MONTHS):
        if k == 0:
            dep = 0; d = {"month": t, "candidate": MONTHS[0], "incumbent_before": MONTHS[0], "swap": None, "reason": "initial deployment", "ic_cand_tm1": None, "ic_inc_tm1": None, "leg_cand_tm1": None, "leg_inc_tm1": None}
        elif rule == "R0":
            dep = k; d = {"month": t, "candidate": t, "incumbent_before": MONTHS[k - 1], "swap": True, "reason": "always newest (age 1)", "ic_cand_tm1": None, "ic_inc_tm1": None, "leg_cand_tm1": None, "leg_inc_tm1": None}
        else:
            cand = k - 1; pm = k - 1; ic_c, ic_i, lg_c, lg_i = float(ICM[cand, pm]), float(ICM[inc, pm]), float(LGM[cand, pm]), float(LGM[inc, pm])
            d = {"month": t, "candidate": MONTHS[cand], "incumbent_before": MONTHS[inc], "eval_month": MONTHS[pm], "ic_cand_tm1": ic_c, "ic_inc_tm1": ic_i, "leg_cand_tm1": lg_c, "leg_inc_tm1": lg_i, "inc_age_at_eval": pm - inc + 1}
            if cand == inc: swap = None; d["reason"] = "candidate is the incumbent (no comparison)"
            else:
                c1 = ic_c >= ic_i - 0.002; c2 = lg_c >= lg_i - 0.10; c4 = ic_c > 0
                swap = {"R1": c1, "R2": c2, "R3": (c1 and c2), "R4": c4}[rule]
                d["reason"] = {"R1": f"IC_c {ic_c:+.4f} >= IC_i {ic_i:+.4f} - 0.002", "R2": f"LEG_c {lg_c:+.3f} >= LEG_i {lg_i:+.3f} - 0.10", "R3": f"IC: {c1}, LEG: {c2}", "R4": f"IC_c {ic_c:+.4f} > 0"}[rule]
            if swap: inc = cand
            dep = inc; d["swap"] = swap
        f, l = MB[t]; f0, P = PF[MONTHS[dep]]; S[f:l + 1] = P[f - f0:l - f0 + 1]
        d.update({"deployed": MONTHS[dep], "age": k - dep + 1, "ic_month": float(ICM[dep, k]), "leg_month": float(LGM[dep, k]), "ic_newest_month": float(ICM[k, k])}); rows.append(d)
    SER[rule] = S; DEC[rule] = rows
    print(f"[{TAG} {rule}] swaps {sum(1 for r in rows if r['swap'] is True)}/{len(rows)-1} mean age {np.mean([r['age'] for r in rows]):.2f} max age {max(r['age'] for r in rows)}", flush=True)
# consistency: R0 series == stitched file from dl_monthly_wf (bitwise), and R0 spliced == the earlier spliced replay input
S0 = np.load(f"{W}/preds/f10_V2MAIN_{TAG}_s42.npy"); r0_eq = bool(np.array_equal(SER["R0"], S0, equal_nan=True)); print(f"[{TAG}] R0 series == dl_monthly_wf stitched file: {r0_eq}", flush=True)
Y = np.load(YEARLY); assert Y.shape == (nB, 829)
os.makedirs(f"{G}/series", exist_ok=True); os.makedirs(f"{G}/results", exist_ok=True); os.makedirs(f"{G}/replay/dev_alt/f8_2026-08-22/preds", exist_ok=True)
FILES = {}
for rule in RULES:
    p1 = f"{G}/series/{TAG}_{rule}.npy"; np.save(p1, SER[rule]); spl = Y.copy(); spl[i25:] = SER[rule][i25:nB]; p2 = f"{G}/replay/dev_alt/f8_2026-08-22/preds/f10_gate_{TAG}_{rule}_s42.npy"; np.save(p2, spl.astype(np.float32))
    assert np.array_equal(spl[:i25], Y[:i25], equal_nan=True) and int(np.isfinite(SER[rule][:i25]).sum()) == 0
    FILES[rule] = {"series_ext": p1, "series_sha256": sha(p1), "replay_spliced": p2, "replay_sha256": sha(p2)}
old = f"{W}/replay/dev_alt/f8_2026-08-22/preds/f10_V2MAIN_{TAG}spl_s42.npy"
if os.path.exists(old): print(f"[{TAG}] R0 spliced == earlier {TAG}spl replay input: {np.array_equal(np.load(FILES['R0']['replay_spliced']), np.load(old), equal_nan=True)}", flush=True)
# ── score-level evaluation per arm (same anchor set for all arms) ──
PY = np.full((nA, 829), np.nan, np.float32); PY[:nB] = Y
def ic_series(P):
    ic = np.full(nA, np.nan)
    for i in range(i25, nA):
        mm = MEM[i]; ic[i] = ic_anchor(P[i, mm], Y4[i, mm])
    return ic
ICS = {r: ic_series(SER[r]) for r in RULES}; ICS["yearly"] = ic_series(PY)
WIN = {"2025-03->26<=cut": (E >= T2503) & (E <= CUT), "2026<=cut": (E >= T26) & (E <= CUT), "2025-03->12": (E >= T2503) & (E < T26), "2025-03->26-08-30": E >= T2503}
rng = np.random.default_rng(SEED)
def boot(x, mask):
    m = mask & np.isfinite(x); v = x[m]; d = days[m]
    if m.sum() < 10: return {"n": int(m.sum())}
    ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "n_days": int(nd), "mean": float(v.mean()), "se_anchor": float(v.std(ddof=1) / np.sqrt(len(v))), "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))], "p_gt0": float((means > 0).mean())}
SC = {"tag": TAG, "ic_levels": {}, "ic_delta": {}, "monthly_ic": {}, "arms": {}}
common = np.ones(nA, bool)
for r in list(RULES) + ["yearly"]: common &= np.isfinite(ICS[r]) | (E > CUT)   # yearly has no rows after the cut; windows <= cut use the common set
for w, mk in WIN.items():
    for r in list(RULES) + ["yearly"]:
        x = ICS[r]; m = mk & np.isfinite(x) & (common if w != "2025-03->26-08-30" else True)
        if m.sum() < 10: continue
        SC["ic_levels"][f"{w}/{r}"] = {"n": int(m.sum()), "mean": float(x[m].mean()), "se_anchor": float(x[m].std(ddof=1) / np.sqrt(m.sum()))}
    for r in RULES:
        for ref in (["R0", "yearly"] if r != "R0" else ["yearly"]):
            mm = mk & np.isfinite(ICS[r]) & np.isfinite(ICS[ref])
            if mm.sum() >= 10: SC["ic_delta"][f"{w}/{r}-{ref}"] = boot(ICS[r] - ICS[ref], mm)
for m in MONTHS:
    mk = ym == m; SC["monthly_ic"][str(m)] = {r: (float(np.nanmean(ICS[r][mk])) if np.isfinite(ICS[r][mk]).sum() else None) for r in list(RULES) + ["yearly"]}
for r in RULES:
    rows = DEC[r]; SC["arms"][r] = {"swaps": int(sum(1 for x in rows if x["swap"] is True)), "decisions": int(sum(1 for x in rows if x["swap"] is not None)), "mean_age": float(np.mean([x["age"] for x in rows])), "max_age": int(max(x["age"] for x in rows)),
                                    "mean_age_from_2025-03": float(np.mean([x["age"] for x in rows[2:]])), "deployed_models": sorted(set(x["deployed"] for x in rows)), "files": FILES[r]}
json.dump({"tag": TAG, "months": MONTHS, "ic_matrix_model_x_month": ICM.tolist(), "leg_matrix_model_x_month": LGM.tolist(), "rules": {r: DEC[r] for r in RULES}, "r0_equals_stitched": r0_eq,
           "definitions": {"IC": "mean over month anchors of per-anchor Spearman(score, y4s) over members with >=30 finite pairs", "LEG": "mean over month anchors of rank-leg return Σ(z/Σ|z|·y4s)·1e4, y4s=Π(1+r5)−1, price only",
                           "R1": "swap iff IC(C,t-1) >= IC(I,t-1) - 0.002", "R2": "swap iff LEG(C,t-1) >= LEG(I,t-1) - 0.10", "R3": "R1 and R2", "R4": "swap iff IC(C,t-1) > 0", "R0": "F(t) at age 1"}},
          open(f"{G}/results/decisions_{TAG}.json", "w"), indent=1)
json.dump(SC, open(f"{G}/results/score_{TAG}.json", "w"), indent=1)
print(f"\n[{TAG}] decisions (month | R1 dep/age/swap | R2 | R3 | R4 | IC_c/IC_i | LEG_c/LEG_i)")
for k, t in enumerate(MONTHS):
    r1, r2, r3, r4 = (DEC[r][k] for r in ("R1", "R2", "R3", "R4"))
    print(f"  {t} | {r1['deployed']}/{r1['age']}/{r1['swap']} | {r2['deployed']}/{r2['age']}/{r2['swap']} | {r3['deployed']}/{r3['age']}/{r3['swap']} | {r4['deployed']}/{r4['age']}/{r4['swap']} | "
          + (f"{r1['ic_cand_tm1']:+.4f}/{r1['ic_inc_tm1']:+.4f} | {r1['leg_cand_tm1']:+.3f}/{r1['leg_inc_tm1']:+.3f}" if r1.get("ic_cand_tm1") is not None else "n/a"))
print(f"\n[{TAG}] IC levels: " + " | ".join(f"{k} {v['mean']:+.4f}±{v['se_anchor']:.4f} (n{v['n']})" for k, v in SC["ic_levels"].items() if k.startswith("2025-03->26<=cut")))
print(f"[{TAG}] ΔIC (2025-03->26<=cut): " + " | ".join(f"{k.split('/')[1]} {v['mean']:+.4f} [{v['ci95'][0]:+.4f},{v['ci95'][1]:+.4f}]" for k, v in SC["ic_delta"].items() if k.startswith("2025-03->26<=cut") and "mean" in v))
print("SIMULATE_DONE", TAG, flush=True)
