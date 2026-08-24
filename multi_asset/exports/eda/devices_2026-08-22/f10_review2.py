"""复审阶段2 独立重算: 标准 Bailey-LdP DSR(家族方差式 SR0)+ 诊断量全打印。输入=已存净额矩阵。"""
import json, math
import numpy as np
from scipy.stats import skew, kurtosis, norm
OUT = "/mnt/storage/private/work_hsy/f8_2026-08-22"
Z = np.load(f"{OUT}/results/f10_review_nets.npz", allow_pickle=True)
names = [k for k in Z.files if k != "ts"]
NET = {k: Z[k] for k in names}
common = np.ones(len(Z["ts"]), bool)
for v in NET.values():
    common &= np.isfinite(v)
# ★ 窗净化: F10 分数只存在于 2023-01→2026-08-10; 之前的"混合"是退化两腿书, 必须剔除
ts = Z["ts"].astype(np.int64)
common &= (ts >= 1672531200) & (ts <= 1786694400)
print("family", len(names), "common anchors(净化后)", int(common.sum()))
C = NET["C3r"][common]
# 家族 Δ夏普(每锚单位)
fam_sr = {}
for k in names:
    if k == "C3r":
        continue
    d = NET[k][common] - C
    fam_sr[k] = float(d.mean() / (d.std() + 1e-12))
vals = np.array(list(fam_sr.values()))
sdSR = float(vals.std())
N = len(vals)
g = 0.5772
sr0 = sdSR * ((1 - g) * norm.ppf(1 - 1 / N) + g * norm.ppf(1 - 1 / (N * math.e)))
print(f"family N={N} sd(SR)={sdSR:.4f} SR0={sr0:.4f} max={vals.max():.4f}")
# PBO 重算(净化窗)
import itertools
M = np.stack([NET[k][common] for k in sorted(names)], 1)
S = 12; L = len(M) // S; Mr = M[:S * L].reshape(S, L, -1)
pbo_cnt = tot = 0; cand_pct = []
snames = sorted(names)
for tr_ in itertools.combinations(range(S), S // 2):
    te_ = [i for i in range(S) if i not in tr_]
    mtr = Mr[list(tr_)].reshape(-1, Mr.shape[-1]).mean(0); mte = Mr[te_].reshape(-1, Mr.shape[-1]).mean(0)
    best = int(np.argmax(mtr)); pbo_cnt += (mte > mte[best]).mean() > 0.5; tot += 1
    for cd0 in snames:
        if "V2MAIN" in cd0 and "0.45" in cd0:
            cand_pct.append(float((mte <= mte[snames.index(cd0)]).mean()))
print(f"PBO(净化窗)={pbo_cnt/tot:.3f} 候选OOS分位均值={np.mean(cand_pct):.3f}")
for cd in ("BL_V2MAIN_42_0_45", "BL_V2MAIN_2027_0_45"):
    key = [k for k in names if k.replace(".", "_") == cd or k == cd]
    if not key:
        cands = [k for k in names if "V2MAIN" in k and "0.45" in k]
        key = cands
    for k in key:
        d = NET[k][common] - C
        n = len(d); sr = float(d.mean() / d.std()); sk = float(skew(d)); ku = float(kurtosis(d, fisher=False))
        z = ((sr - sr0) * math.sqrt(n - 1)) / math.sqrt(max(1 - sk * sr + (ku - 1) / 4 * sr * sr, 1e-9))
        print(f"{k}: Δmean {d.mean():.3f} Δstd {d.std():.3f} SR/锚 {sr:.4f} ann~{sr*math.sqrt(2190):.2f} skew {sk:.2f} kurt {ku:.1f} z {z:.2f} DSR {norm.cdf(z):.3f}")
