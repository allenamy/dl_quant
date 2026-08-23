"""F-11 · 价带特征构建 @jpline(2026-08-23)。预注册 PREREG_F11(SHA 650f3742…, commit a9b5f6d)先于任何数字。
输入 lob_bookdepth/npz/<SYM>.npz(30s × 12带 log1p 名义额); 输出 f8_2026-08-22/data/f11_lob_fea.npz(nA×829×36, dlw 网格)。
结构因果: 每锚只用 ts ≤ 锚 的行。用法: python f11_lob_features.py <shard> <nshards>"""
import os, sys, glob, time
import numpy as np
B = "/mnt/storage/private/work_hsy/lob_bookdepth"
DLW = "/mnt/storage/private/work_hsy/dlw_2026-08-22"
OUT = "/mnt/storage/private/work_hsy/f8_2026-08-22"
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64); syms = [str(s) for s in TG["symbols"]]
SM = {s: i for i, s in enumerate(syms)}
nA = len(E_ts)
# 带序: [-5,-4,-3,-2,-1,-0.2, +0.2,+1,+2,+3,+4,+5]; bid=负带, ask=正带
BI = {5.0: 0, 4.0: 1, 3.0: 2, 2.0: 3, 1.0: 4, 0.2: 5}   # 距离→(bid idx, ask 对称 11-idx)
NF = 36
shard, nsh = int(sys.argv[1]), int(sys.argv[2])
T0 = time.time()


from scipy.signal import lfilter


def ema_irr(vals, ts, hl):
    """规则 30s 网格近似 EMA(半衰期 hl 秒), lfilter 向量化; NaN 前向填充(缺口稀少, 偏差可忽略, 如实标注)。"""
    v = np.asarray(vals, np.float64)
    ok = np.isfinite(v)
    if ok.sum() < 10:
        return np.full(len(v), np.nan)
    idx = np.where(ok, np.arange(len(v)), 0)
    np.maximum.accumulate(idx, out=idx)
    vf = v[idx]
    first = np.argmax(ok)
    vf[:first] = v[ok][0]
    al = 1 - np.exp(-np.log(2) * 30.0 / hl)
    o = lfilter([al], [1, -(1 - al)], vf, zi=[vf[0] * (1 - al)])[0]
    o[:first] = np.nan
    return o


files = sorted(glob.glob(f"{B}/npz/*.npz"))
os.makedirs(f"{OUT}/data/f11_parts", exist_ok=True)
for fi, f in enumerate(files):
    if fi % nsh != shard:
        continue
    sym = os.path.basename(f)[:-4]
    if sym not in SM:
        continue
    op = f"{OUT}/data/f11_parts/{sym}.npz"
    if os.path.exists(op):
        continue
    z = np.load(f)
    ts = z["ts"].astype(np.int64); L = z["lnot"].astype(np.float32)   # (T,12)
    NOT = np.expm1(L)                                                  # 名义额
    bidN = NOT[:, [0, 1, 2, 3, 4, 5]]                                  # -5..-0.2
    askN = NOT[:, [11, 10, 9, 8, 7, 6]]                                # +5..+0.2 (同距序)
    with np.errstate(all="ignore"):
        # S 族
        I = (bidN - askN) / (bidN + askN + 1e-9)                       # (T,6) 距序 5,4,3,2,1,0.2
        Inear = I[:, 5]; I1 = I[:, 4]; I3 = I[:, 2]; I5 = I[:, 0]
        x = np.array([5, 4, 3, 2, 1, 0.2]); xc = x - x.mean(); den = (xc ** 2).sum()
        s_bid = (np.log1p(bidN) * xc).sum(1) / den
        s_ask = (np.log1p(askN) * xc).sum(1) / den
        s_asym = s_bid - s_ask
        # F 族: 30s 差
        dB = np.vstack([np.zeros((1, 6)), np.diff(bidN, axis=0)])
        dA = np.vstack([np.zeros((1, 6)), np.diff(askN, axis=0)])
        tot = bidN.sum(1) + askN.sum(1) + 1e-9
        ofi_near = (dB[:, 5] - dA[:, 5]) / tot
        ofi_int = (dB - dA).sum(1) / tot
        wd = np.minimum(dB[:, 5] + dA[:, 5], 0) / tot                  # 近带撤退(负)
        wd_asym = (np.minimum(dB[:, 5], 0) - np.minimum(dA[:, 5], 0)) / tot
    core = {"Inear": Inear, "I1": I1, "I3": I3, "I5": I5, "s_asym": s_asym,
            "ofi_near": ofi_near, "ofi_int": ofi_int, "wd": wd, "wd_asym": wd_asym}
    E = {}
    for k in ("Inear", "s_asym", "ofi_near", "ofi_int", "wd", "wd_asym"):
        for hl, tag in ((3600, "1h"), (14400, "4h"), (86400, "24h")):
            E[f"{k}_e{tag}"] = ema_irr(core[k], ts, hl)
    # 锚提取: searchsorted 右端 ≤ 锚
    pos = np.searchsorted(ts, E_ts, side="right") - 1
    ok = pos >= 0
    ok &= np.where(ok, (E_ts - ts[np.maximum(pos, 0)]) <= 3600, False)   # 最近行需在锚前 1h 内
    FE = np.full((nA, NF), np.nan, np.float32)
    names = []
    ci = 0
    for k in ("Inear", "I1", "I3", "I5", "s_asym", "ofi_near", "ofi_int", "wd", "wd_asym"):
        FE[ok, ci] = core[k][pos[ok]]; names.append(f"{k}_last"); ci += 1
    for k, v in E.items():
        FE[ok, ci] = v[pos[ok]]; names.append(k); ci += 1
    # 24h 趋势(6 核心量: e4h − e24h)与 1h 稳定度
    for k in ("Inear", "s_asym", "ofi_near", "ofi_int", "wd", "wd_asym"):
        FE[:, ci] = FE[:, names.index(f"{k}_e4h")] - FE[:, names.index(f"{k}_e24h")]
        names.append(f"{k}_tr"); ci += 1
    # I_near 1h 稳定度(滚动 120 行 std)
    st = np.full(len(ts), np.nan, np.float32)
    w = 120
    if len(ts) > w:
        c1 = np.cumsum(np.nan_to_num(Inear)); c2 = np.cumsum(np.nan_to_num(Inear) ** 2)
        m = (c1[w:] - c1[:-w]) / w; v2 = (c2[w:] - c2[:-w]) / w - m ** 2
        st[w:] = np.sqrt(np.maximum(v2, 0))
    FE[ok, ci] = st[pos[ok]]; names.append("Inear_std1h"); ci += 1
    np.savez_compressed(op, fe=FE[:, :ci], names=np.array(names[:ci]), sym=sym, scol=SM[sym])
    print(f"[{time.time()-T0:6.0f}s] {sym} cols={ci} cover={np.isfinite(FE[:,0]).mean():.2f}", flush=True)
print("F11_SHARD_DONE", shard, flush=True)
