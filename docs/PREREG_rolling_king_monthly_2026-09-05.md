> **创建:** 2026-09-05 01:3xZ | **Session:** b9646a9e | **状态:** 预注册(判据冻结, 数字未看) | **用户字:** 09-05 "king tree 目前的做法太滞后… 应该按照 DL 的方式滚动学习最新的数据, 但是解决样本外权重确定的问题, 然后用这种滚动最新的方式去做严格因果地离线评估看是否有帮助" | **作废条件:** 因果断言失败(训练标签窗与测试窗重叠)或装置默认路径与 pod port 基线不逐位等价

# PREREG · king 树月度滚动重训(生产配方) 的严格因果离线评估

## §0 背景与穷尽清单
- 在役 king booster 训练集 = 2022-01→2025-12(导出器 L49 `tr = YRA < 2026`), 每月重训不含 2026 数据(E-0905-B); DL refit 每月训至 T−1(末 15% 早停)。
- 本周已有一次"滚动季度 king"(RESULT_rolling_king_2026-09-04): **配方不同**(171 列、残差目标 YRZ、季度折)、**口径错**(CAL=simple), 其"IC↑书↓"结论作废待重立。本预注册不是复跑它, 而是用**生产配方**在**正确口径**下测"新鲜度"这一个变量。

## §1 装置(全部 pod, 只读输入, 产物入 /workspace/review_scratch/rolling_king/)
- 训练数据与配方与导出器逐字同: `wide_fea_v2ext.npy` + meta, `keep` 78 列, 标签 = 成员内 `rankdata(y4)/(n−1)−0.5`(y4 = Σ5m 简单收益 [E,E+47]), `LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8)`; 每折 seed 固定 = 20260905 + 折序号。
- **月度滚动折**: 对 M ∈ 2024-01 … 2026-08: 训练集 = E_ts < (M 首锚 − EMB) 的全部锚, EMB = 60 锚(10 天; 标签窗只到 E+4h, 60 锚远超); 预测 M 内全部锚。拼接为 `slow_pred_rollm.npy`(shape 同 meta, 2024 前 NaN)。
- **对照**: (a) 生产 pinned(年折: 2024/2025 年折外 + 2026 用 <2026 训练), 即 port 现有 `slow_pred_pinned.npy`; (b) 季度滚动同法 `slow_pred_rollq.npy`(形状核, 非选型)。
- **因果断言(装置内 assert, 失败即停)**: 每折 max(train E_ts) + 48×300 s < min(test E_ts) − EMB×14400 s; 特征列均以 E−1 收盘为止(构建器既有); 预测文件 2024 前全 NaN 与 pinned 同。
- 评估装置: `/workspace/review_scratch/combo_recheck/w10_universe_recheck.py`(= port 副本 + REF_SKIP 自报), `SLOW_NPY=<预测文件>`, 其余 env 与基线逐字同; 先跑 SLOW_NPY=pinned 复现 port 基线逐位(array_equal)作等价收据。
- 口径: CAL=log(原始 y4)与复利持仓窗目标(R-C6.2 `meta_newprod.npz` 机制), 两口径都报。

## §2 臂(每臂 3 个 king 源 × 2 口径; F10 s42, 动态臂加 s2027)
| 臂 | 形态 | 席位 |
|---|---|---|
| L-fix | MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero, W3FIX=0.21,0,0.79 | 固定(最接近实盘) |
| L-dyn | 同上, msharpe LOOK 900 | 动态(生产规则; 各月行均由该月之前训练的模型产生 ⇒ 席位输入逐行样本外) |
| C-dyn | canon(无 M1/T400/FTRIM), msharpe | 动态 |

## §3 判据(冻结)
主判 = **L-fix, 2024→26, 配对锚 Δnet_ex(滚动月 − pinned), 逐日块 bootstrap 2000 次 CI95**, 两口径各一:
- **ADMIT 候选**(进入部署预注册, 仍需用户字): 两口径 CI95 下界 > 0, 且 2025→26 Δ ≥ 0, 且逐年最坏 Δ ≥ −0.05, 且换手增量 ≤ +15%, 且 L-dyn 两种子 Δ 同号非负。
- **REJECT**: 任一口径 CI95 上界 < 0, 或换手 > +25%。
- 其余 = UNDECIDED(记录, 不部署)。
辅判(不选型): IC 逐年(raw y4 与 Π 目标各一), king 腿原始收益逐年(生产 legs() 定义), 席位轨迹, 季度折形状, σ_fund 三分位。
- 不做: 多种子集成、按结果挑 EMB/折长、事后改判据。
