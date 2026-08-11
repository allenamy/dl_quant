"""zoo v2: +23 个人工特征(klines+funding 可导出, 不含 book 结构) → 32+23=55ch。
用户令: 有效维度 7.5 喂不饱模型, 人工特征拉到 50+。设计原则: 每个特征一行机制, 
瞄准现 32ch 缺席的四个轴: ①日内季节 ②高低价域 ③量价结构 ④funding 动力学。"""
import numpy as np, pandas as pd, sys
sys.path.insert(0, "/workspace/code")
from multi_asset.data.wide_factory import _shift, _roll

G = np.load("/workspace/data/ohlcv_grid.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
C = G["CLOSE"].astype(np.float64); H = G["HIGH"].astype(np.float64)
L = G["LOW"].astype(np.float64); O = G["OPEN"].astype(np.float64)
V = G["VOL"].astype(np.float64); QV = G["QVOL"].astype(np.float64)
TS = np.asarray(G["ts"]).astype(np.int64)
T, N = C.shape
logc = np.log(np.where(C > 0, C, np.nan))
ret1 = logc - _shift(logc, 1)
F = {}
# ① 高低价域(现32ch完全缺席 OHLC 域)
with np.errstate(all="ignore"):
    lh = np.log(np.where((H > 0) & (L > 0), H / L, np.nan))
    F["park_24h"] = np.sqrt(_roll(lh**2, 24, "mean") / (4*np.log(2)))     # Parkinson 波动
    F["park_ratio"] = F["park_24h"] / np.maximum(_roll(ret1, 24, "std"), 1e-9)  # 域内/收盘波动比=跳跃度
    F["clv_24h"] = _roll(np.where(H > L, (2*C - H - L) / (H - L), np.nan), 24, "mean")  # 收位(吸筹/派发)
    F["hl_pos_72h"] = (C - _roll(L, 72, "min")) / np.maximum(_roll(H, 72, "max") - _roll(L, 72, "min"), 1e-12)  # 72h 区间位置
# ② 量价结构
    lv = np.log(np.where(V > 0, V, np.nan))
    F["vol_trend_24h"] = lv - _roll(lv, 24, "mean")                       # 量能相对水平
    F["vol_accel"] = _roll(lv, 6, "mean") - _roll(lv, 24, "mean")         # 量能加速
    F["vp_corr_24h"] = np.column_stack([pd.Series(ret1[:, j]).rolling(24, min_periods=12)
                        .corr(pd.Series(np.diff(lv[:, j], prepend=np.nan))) for j in range(N)])  # 量价共振
    F["amihud_24h"] = _roll(np.abs(ret1) / np.where(QV > 0, QV, np.nan), 24, "mean")  # 短窗 Amihud
    F["ret_skew_72h"] = _roll(ret1, 72, "skew")                           # 收益偏度(彩票/崩塌)
    F["ret_kurt_72h"] = _roll(ret1, 72, "kurt")                           # 尖峰度
    F["dd_from_high72"] = logc - np.log(np.maximum(_roll(H, 72, "max"), 1e-12))  # 距 72h 高点
    F["vov_72h"] = _roll(_roll(ret1, 24, "std"), 72, "std")               # 波动的波动
    F["volratio_6_72"] = _roll(ret1, 6, "std") / np.maximum(_roll(ret1, 72, "std"), 1e-9)  # 波动 regime 比
# ③ 日内季节(24/7 市场的时段结构: 亚/欧/美盘)
    hod = ((TS // 3600000) % 24).astype(int)
    for nm, hrs in (("asia", range(0, 8)), ("eu", range(8, 16)), ("us", range(16, 24))):
        m = np.isin(hod, list(hrs)).astype(float)[:, None]
        F[f"sess_{nm}_mom"] = _roll(ret1 * m, 168, "sum")                 # 分时段周动量
    F["hod_sin"] = np.repeat(np.sin(2*np.pi*hod/24)[:, None], N, 1)      # 时刻编码(模型自学时段效应)
    F["hod_cos"] = np.repeat(np.cos(2*np.pi*hod/24)[:, None], N, 1)
# ④ funding 动力学(现 32ch 只有 funding_ema 一个静态量)
    names32 = [str(x) for x in R["ch_names"]]
    fe = R["CH"][:, :, names32.index("funding_ema")].astype(np.float64)
    fe[fe == 0] = np.nan
    F["fund_chg24"] = fe - _shift(fe, 24)                                 # funding 动量
    F["fund_x_mom"] = fe * (logc - _shift(logc, 72))                      # 拥挤趋势交互
    F["fund_absdev"] = np.abs(fe - _roll(fe, 168, "mean"))                # funding 偏离度
# ⑤ 横截面结构
    mkt = np.nanmean(np.where(ret1 != 0, ret1, np.nan), axis=1)
    mkt = np.nan_to_num(mkt)[:, None]
    resid = ret1 - mkt                                                    # 粗残差
    F["idio_share_72h"] = _roll(resid**2, 72, "mean") / np.maximum(_roll(ret1**2, 72, "mean"), 1e-12)  # 特质占比
    F["mom_12h"] = logc - _shift(logc, 12)                                # 补缺窗口
    F["mom_48h"] = logc - _shift(logc, 48)
NEW = list(F)
print("新特征 %d: %s" % (len(NEW), NEW))
CH_new = np.stack([np.nan_to_num(np.asarray(F[k], np.float32), nan=0.0, posinf=0.0, neginf=0.0)
                   for k in NEW], axis=2)
CH55 = np.concatenate([R["CH"], CH_new], axis=2)
d = {k: R[k] for k in R.files if k not in ("CH", "ch_names")}
d["CH"] = CH55
d["ch_names"] = np.array(names32 + NEW, object)
np.savez("/workspace/data/wide_dl_55ch.npz", **d)
print("55ch 面板: %s" % (CH55.shape,))
