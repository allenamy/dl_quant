"""迷你缓存法自平价 @jpline: 用 jpline 缓存的最后 11520 行(=影子滚动缓存形制)重跑
dlw_features + f8 build, 与全史存档在共同锚上逐列比对。闸: 每列秩相关 >0.999 且 max|Δ|<1e-3。"""
import os, sys, json, subprocess, time
import numpy as np
ROOT = "/mnt/storage/private/work_hsy"
DLW = f"{ROOT}/dlw_2026-08-22"; F8 = f"{ROOT}/f8_2026-08-22"
MINI = f"{F8}/data/mini171"
os.makedirs(MINI, exist_ok=True)
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)
Z = np.load(f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]
s0 = CD.shape[0] - 11520
np.savez(f"{MINI}/cache.npz", ts=CTS[s0:], data=CD[s0:], symbols=Z["symbols"], ch=Z["ch"])
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
E = TG["E_row"].astype(np.int64); E_ts = TG["E_ts"].astype(np.int64)
sel = np.where((E >= s0 + 48) & (E < CD.shape[0]))[0]          # targets=全尾锚(H 状态序列/J i−6 需上下文)
cmp_sel = np.where((E >= s0 + 8880) & (E < CD.shape[0]))[0]     # 比较集=窗口完整的末段锚
log(f"tail anchors {len(sel)} (compare {len(cmp_sel)})")
os.makedirs(f"{MINI}/data", exist_ok=True)
np.savez(f"{MINI}/data/dlw_targets.npz", E_row=(E[sel] - s0), E_ts=E_ts[sel], members=TG["members"][sel],
         y4s=TG["y4s"][sel], YR4s=TG["YR4s"][sel], YRZ=TG["YRZ"][sel], yrs=TG["yrs"][sel],
         qvk=TG["qvk"][sel], btcv=TG["btcv"][sel], has_panel=TG["has_panel"][sel],
         symbols=TG["symbols"], y4old=TG["y4old"][sel], meta_json=TG["meta_json"])
del Z, CD
env = dict(os.environ)
env.update({"F171_CACHE": f"{MINI}/cache.npz", "F171_TARGETS": f"{MINI}/data/dlw_targets.npz", "F171_OUT": MINI,
            "F171_FEA82": f"{MINI}/data/dlw_fea82.npz"})
os.makedirs(f"{MINI}/data", exist_ok=True)
PY = "/root/miniconda3/envs/hsy_v5push/bin/python"
r = subprocess.run([PY, f"{DLW}/dlw_features.py"], env=env, capture_output=True, text=True)
log("dlw_features rc", r.returncode, r.stdout[-200:] if r.returncode else "")
assert r.returncode == 0, r.stderr[-800:]
r = subprocess.run([PY, "-c", f"import os,sys; sys.path.insert(0,'{F8}'); os.chdir('{F8}'); import f8_higher_order_features as m; m.build()"], env=env, capture_output=True, text=True)
log("f8 build rc", r.returncode)
assert r.returncode == 0, r.stderr[-800:]
# 比对
from scipy.stats import spearmanr
FULL9 = np.load(f"{F8}/data/f8_fea89.npz", allow_pickle=True)
MIN9 = np.load(f"{MINI}/data/f8_fea89.npz", allow_pickle=True)
names = [str(n) for n in MIN9["names"]]
fp, fs = FULL9["pair_a"].astype(np.int64), FULL9["pair_s"].astype(np.int64)
mp, ms = MIN9["pair_a"].astype(np.int64), MIN9["pair_s"].astype(np.int64)
selset = {int(x): k for k, x in enumerate(sel)}
mask = np.isin(fp, cmp_sel)
key_full = (np.array([selset[int(a)] for a in fp[mask]]) << 12) + fs[mask]
key_mini = (mp.astype(np.int64) << 12) + ms
om = {int(k): i for i, k in enumerate(key_mini)}
rows = np.array([om.get(int(k), -1) for k in key_full])
ok = rows >= 0
XF = FULL9["X"][mask][ok]; XM = MIN9["X"][rows[ok]]
bad = []
for j, n in enumerate(names):
    a, b = XF[:, j], XM[:, j]
    m2 = np.isfinite(a) & np.isfinite(b)
    if m2.sum() < 500:
        bad.append((n, "n<500")); continue
    rho = spearmanr(a[m2], b[m2]).correlation
    dmax = float(np.max(np.abs(a[m2] - b[m2])))
    if not (rho > 0.999 and dmax < 1e-3):
        bad.append((n, round(float(rho), 5), round(dmax, 5)))
print("PARITY", "PASS" if not bad else f"FAIL {len(bad)}", flush=True)
for b_ in bad[:12]:
    print("  ", b_, flush=True)
json.dump({"n_anchors": len(sel), "n_rows": int(ok.sum()), "n_cols": len(names), "n_bad": len(bad), "bad": bad[:30]},
          open(f"{F8}/results/parity171_tail.json", "w"), indent=1, default=str)
log("PARITY171_DONE")
