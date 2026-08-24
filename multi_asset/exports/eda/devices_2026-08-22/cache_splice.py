"""缓存刷新: jpline dlnative(→08-10) + 影子 rolling(07-15→08-24) 拼接; 重叠区逐通道校验为闸。"""
import numpy as np, time
ROOT = "/mnt/storage/private/work_hsy"
Z = np.load(f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]
R = np.load(f"{ROOT}/f8_2026-08-22/data/mac_rolling_20260824.npz", allow_pickle=True)
rts = R["ts"].astype(np.int64); RD = R["data"]
f = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(int(t)))
print("jp", f(CTS[0]), "→", f(CTS[-1]), "| mac", f(rts[0]), "→", f(rts[-1]))
# 重叠校验
common = np.intersect1d(CTS, rts)
ci = np.searchsorted(CTS, common); ri = np.searchsorted(rts, common)
sl = slice(0, len(common), 17)
A = CD[ci[sl]].astype(np.float32); B = RD[ri[sl]].astype(np.float32)
ok = np.isfinite(A) & np.isfinite(B)
d = np.abs(A - B)[ok]
per_ch = [float(np.nanmax(np.where(ok[:, :, c], np.abs(A - B)[:, :, c], 0))) for c in range(A.shape[2])]
mismatch_frac = float((np.isfinite(A) != np.isfinite(B)).mean())
print(f"overlap {len(common)} rows | max|Δ| {d.max():.5f} med {np.median(d):.6f} | per-ch max {['%.4f'%x for x in per_ch]} | finite-mask mismatch {mismatch_frac:.4f}")
assert d.max() < 0.02 and mismatch_frac < 0.02, "重叠区不平价, 拼接中止"
new_mask = rts > CTS[-1]
NCTS = np.concatenate([CTS, rts[new_mask]])
NCD = np.concatenate([CD, RD[new_mask].astype(CD.dtype)])
np.savez(f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16_fresh.npz", ts=NCTS, data=NCD, symbols=Z["symbols"], ch=Z["ch"])
print(f"SPLICE_DONE 新缓存 → {f(NCTS[-1])} 共 {len(NCTS)} 行 (+{int(new_mask.sum())})")
