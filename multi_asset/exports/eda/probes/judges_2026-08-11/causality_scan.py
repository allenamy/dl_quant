"""全通道因果扫描 — ch31 类泄漏的判别器。

原理: 因果特征对【未来】收益的截面 IC 有 alpha 上界(本项目 ~0.05-0.10); 泄漏特征(如脏 ch31 =
含 11h 未来收益的 betaadj_ret24)对未来的 IC 会到 0.3-0.7 — 高出任何合法 alpha 一个量级。
判读(先写死): 任一通道 |IC(ch_t, fwd24h)| > 0.15 ⇒ 红旗(停用面板取证);
0.10~0.15 ⇒ 黄旗人工复核; 全部 <0.10 ⇒ 本类泄漏排除。
边界(如实): 本扫描抓"特征含未来收益"类; 不覆盖"特征含未来【非收益】信息"(如未来成交量) —
那类靠构建期 truncation 断言(#41 §7-2)兜底。
同时扫【目标 baseline 8 列】—— 它们残差化进 YR 目标, 泄漏会经目标进模型。
"""
import numpy as np

BASE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
P = np.load(f"{BASE}/wide_dl_full_corrfund_causal_0731.npz", allow_pickle=True)
CH = P["CH"]; MEM = P["MEMBER110"]; Y4 = P["Y4"]
names = [str(x) for x in P["ch_names"]]
bcols = [str(x) for x in P["baseline_cols"]]
T = CH.shape[0]


def zr(x):
    m = np.isfinite(x)
    out = np.full(len(x), np.nan)
    if m.sum() < 10:
        return out
    r = np.argsort(np.argsort(x[m])).astype(float)
    out[m] = (r - r.mean()) / (r.std() + 1e-12)
    return out


def xic(a, b):
    za, zb = zr(a), zr(b)
    m = np.isfinite(za) & np.isfinite(zb)
    return float(np.nanmean(za[m] * zb[m])) if m.sum() >= 10 else np.nan


rows = np.arange(200, T - 25, 97)          # ~500 行, 跨全史, 质数步长避周期
fwd24 = np.full((len(rows), CH.shape[1]), np.nan)
past24 = np.full((len(rows), CH.shape[1]), np.nan)
for i, r in enumerate(rows):
    f = np.zeros(CH.shape[1]); p = np.zeros(CH.shape[1])
    okf = np.ones(CH.shape[1], bool); okp = okf.copy()
    for j in range(6):
        vf = Y4[r + 4 * j]; okf &= np.isfinite(vf)
        f += np.log1p(np.where(np.isfinite(vf), np.clip(vf, -.5, .5), 0))
        vp = Y4[r - 4 * (j + 1)]; okp &= np.isfinite(vp)
        p += np.log1p(np.where(np.isfinite(vp), np.clip(vp, -.5, .5), 0))
    fwd24[i] = np.where(MEM[r] & okf, f, np.nan)
    past24[i] = np.where(MEM[r] & okp, p, np.nan)

print(f"{'ch':>3s} {'name':30s} {'IC_fwd24':>9s} {'IC_past24':>10s}  flag")
flags = []
for c in range(CH.shape[1]):
    icf = np.nanmean([xic(np.where(MEM[r], CH[r, :, c], np.nan), fwd24[i])
                      for i, r in enumerate(rows)])
    icp = np.nanmean([xic(np.where(MEM[r], CH[r, :, c], np.nan), past24[i])
                      for i, r in enumerate(rows)])
    fl = "RED" if abs(icf) > 0.15 else ("YELLOW" if abs(icf) > 0.10 else "")
    star = " <== baseline" if names[c] in bcols else ""
    if fl:
        flags.append((c, names[c], round(icf, 3), fl))
    print(f"{c:>3d} {names[c][:30]:30s} {icf:>9.4f} {icp:>10.4f}  {fl}{star}")
print(f"\nbaseline_cols 在 ch_names 中的覆盖: "
      f"{[b for b in bcols if b in names]} | 不在: {[b for b in bcols if b not in names]}")
red = [f for f in flags if f[3] == "RED"]
print("判决:", ("RED " + str(red)) if red else
      (("YELLOW " + str(flags)) if flags else "全部 |IC_fwd|<0.10 — ch31 类泄漏排除"))
