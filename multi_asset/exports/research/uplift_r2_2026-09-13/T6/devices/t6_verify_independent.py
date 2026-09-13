#!/usr/bin/env python3
"""t6_verify_independent.py -- second implementation (different code path) of the headline F1 s42 numbers.
Recomputes, without the block-sum machinery of t6_compute.py: CSCV logits on 1,000 random splits by explicit row concatenation and
scipy rankdata; PBO over those splits; nested W_FULL selection and its Sharpe; DSR(SEL, N_eff) via numpy moments. Compares to the receipt.
Usage: python3 t6_verify_independent.py <receipts_dir>"""
import sys, os, json, math, itertools, calendar
import numpy as np
from scipy import stats
RD = sys.argv[1]
R = json.load(open(os.path.join(RD, "RECEIPT_T6_compute.json")))["RESULTS"]["F1_s42"]
Z = np.load(os.path.join(RD, "T6_SERIES_s42.npz")); m = Z["F1"].astype(bool); X = Z["G"][:, m]; ts = Z["ts"].astype(np.int64)
lab = np.array(["%s:%s" % (a, b) for a, b in zip(Z["member_id"][m], Z["stem"][m])])
A = math.sqrt(2190)
def sr(x): return x.mean(0) / x.std(0, ddof=1) * A
out = {}
# --- CSCV on W_FULL: explicit rows
T = X.shape[0]; drop = T % 16; Y = X[drop:]; L = Y.shape[0] // 16
combos = list(itertools.combinations(range(16), 8)); rng = np.random.default_rng(12345); pick = rng.choice(len(combos), 1000, replace=False)
lam = []
for c in pick:
    ins = set(combos[c]); ri = np.concatenate([np.arange(b * L, (b + 1) * L) for b in range(16) if b in ins]); ro = np.concatenate([np.arange(b * L, (b + 1) * L) for b in range(16) if b not in ins])
    si = sr(Y[ri]); so = sr(Y[ro]); k = int(np.argmax(si)); rk = stats.rankdata(so, method="average")[k]; w = rk / (X.shape[1] + 1); lam.append(math.log(w / (1 - w)))
lam = np.array(lam); pbo_sub = float((lam <= 0).mean()); se = math.sqrt(pbo_sub * (1 - pbo_sub) / len(lam))
out["PBO_W_FULL_1000_random_splits"] = dict(pbo=pbo_sub, binomial_se=se, receipt_full_12870=R["W_FULL"]["PBO"]["PBO"], within_3se=abs(pbo_sub - R["W_FULL"]["PBO"]["PBO"]) <= 3 * se)
# --- nested W_FULL
segs = [(2023, 2024), (2024, 2025), (2025, 2026), (2026, None)]
ser = []
for y0, y1 in segs:
    lo = calendar.timegm((y0, 1, 1, 0, 0, 0)); hi = calendar.timegm((y1, 1, 1, 0, 0, 0)) if y1 else calendar.timegm((2026, 8, 30, 20, 0, 1))
    tr = ts < lo; sg = (ts >= lo) & (ts < hi); k = int(np.argmax(sr(X[tr]))); ser.append(X[sg, k])
xn = np.concatenate(ser); srn = float(xn.mean() / xn.std(ddof=1) * A)
out["nested_W_FULL"] = dict(sr=srn, receipt=R["W_FULL"]["NESTED"]["SR_nested"], abs_diff=abs(srn - R["W_FULL"]["NESTED"]["SR_nested"]))
# --- DSR SEL at N_eff on W_FULL (moments by hand)
srpp = X.mean(0) / X.std(0, ddof=1); V = srpp.var(ddof=1); C = np.corrcoef(X, rowvar=False); ev = np.linalg.eigvalsh(C); Ne = ev.sum() ** 2 / (ev ** 2).sum()
k = int(np.argmax(srpp)); g = X[:, k]; n = len(g); mu = g.mean(); sd = g.std(ddof=0)
g3 = (((g - mu) / sd) ** 3).mean() * math.sqrt(n * (n - 1)) / (n - 2)          # adjusted Fisher-Pearson skew (bias=False)
m2 = ((g - mu) ** 2).mean(); m4 = ((g - mu) ** 4).mean(); ex = m4 / m2 ** 2 - 3; g4 = ((n + 1) * ex + 6) * (n - 1) / ((n - 2) * (n - 3)) + 3   # bias-corrected kurtosis
N = max(Ne, 2.0); gam = 0.5772156649015329
z0 = math.sqrt(V) * ((1 - gam) * stats.norm.ppf(1 - 1 / N) + gam * stats.norm.ppf(1 - 1 / (N * math.e)))
s = srpp[k]; p0 = stats.norm.cdf((s - z0) * math.sqrt(n - 1) / math.sqrt(1 - g3 * s + (g4 - 1) / 4 * s * s))
p3 = stats.norm.cdf((s - z0 - 3 / A) * math.sqrt(n - 1) / math.sqrt(1 - g3 * s + (g4 - 1) / 4 * s * s))
rd = R["W_FULL"]["DSR"]["SEL"]
out["DSR_SEL_W_FULL_Neff"] = dict(member=str(lab[k]), N_eff=Ne, P_gt0=p0, P_gt3=p3, receipt_P_gt0=rd["P_true_SR_gt_0_N_eff"], receipt_P_gt3=rd["P_true_SR_gt_3_N_eff"], receipt_member=rd["member"],
                                  abs_diff_gt0=abs(p0 - rd["P_true_SR_gt_0_N_eff"]), abs_diff_gt3=abs(p3 - rd["P_true_SR_gt_3_N_eff"]))
ok = out["PBO_W_FULL_1000_random_splits"]["within_3se"] and out["nested_W_FULL"]["abs_diff"] < 1e-9 and out["DSR_SEL_W_FULL_Neff"]["abs_diff_gt0"] < 1e-6 and out["DSR_SEL_W_FULL_Neff"]["abs_diff_gt3"] < 1e-6 and out["DSR_SEL_W_FULL_Neff"]["member"] == rd["member"]
out["PASS"] = bool(ok)
json.dump(out, open(os.path.join(RD, "VERIFY_T6_independent.json"), "w"), indent=1, default=float)
print("SUMMARY t6_verify_independent PBO_sub=%.4f(se %.4f) vs %.4f | nested %.6f vs %.6f | DSR P>0 %.6f vs %.6f P>3 %.6f vs %.6f | PASS=%s" % (
    pbo_sub, se, R["W_FULL"]["PBO"]["PBO"], srn, R["W_FULL"]["NESTED"]["SR_nested"], p0, rd["P_true_SR_gt_0_N_eff"], p3, rd["P_true_SR_gt_3_N_eff"], ok))
sys.exit(0 if ok else 4)
