> **创建:** 2026-09-13 ~05:55Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T1) | **状态:** 定义性修订, 冻结先于任何 H2b 比对数字 | **修订对象:** `PREREG_T1_edge_diagnosis_2026-09-13.md` §6 H2b(+ AMENDMENT 1 `a7628a72…`, AMENDMENT 2 `12b262fd…`) | **作废条件:** 同主文

# AMENDMENT 3 · H2b 的比对规则: 训练特征以 float16 存储, 1e-5 相对差门在构造上不可达

**发现方式**: 读两个特征构建器写出矩阵的那一行(没有打开任何特征文件的数值): king 构建器 `FEA = np.full((len(E), NW, NF), np.nan, np.float16)`(`v4_chain_2026-09-09/pod_fea_ext_clamp.py` L73)、DL 构建器 `X = np.zeros((n_pairs, NF), np.float16)`(`fea171/dlw_features.py` L79)。fund_ema 量级 1e-4, float16 的量化误差远大于主文 H2b 写的「相对差中位 ≤ 1e-5」—— 那条门在构造上永远不过, 不是判据。

**修订(定义性)**:
1. **比对 = 施加构建器自己的转换后逐值相等**: 对面板 E 行名 n, 取 cast0 = float16(nan→0(f_fund_ema[j,n]))(v0)、cast1 = float16(nan→0(f_fund_ema_v1[j,n]))(v1); 训练矩阵该名-锚的 `fund_ema` 列存值 s。只在 f_fund_iv[j,n] = 4 且 cast0 ≠ cast1 的格上比; s0 = mean(s == cast0), s1 = mean(s == cast1)。
2. **受检文件**(pod2, 只读): 9 月 1 日月度重训所用谱系 `/workspace/data/wide_fea_v2ext.npy`(king; 在役 booster 8d79186b 于 2026-09-01 由当日数据链训练, 记忆 `retrain_2026_09_first_run`)与 `/workspace/dlw_ext/data/dlw_fea82.npz`(DL); v4 谱系 `/workspace/data/wide_fea_v4.npy` 与 `/workspace/dlw_v4raw/data/dlw_fea82.npz`。面板 `/workspace/data/wide_panel_4h_v2ext.npz`。**「在役模型确实由这两个 9 月 1 日文件训练」是转引(INFERRED), 不是本轮核实**; RESULT 必须如此标注。
3. **H2b 判读**: 四个文件都 s0 ≥ 0.99 且 s1 ≤ 0.01 ⇒ 训练口径 = v0; 四个都 s1 ≥ 0.99 且 s0 ≤ 0.01 ⇒ 训练口径 = v1; 其余 = 不可判(写出各文件 s0/s1)。
4. **服务端实测**(补代码读法 F5 的数据证据, 本机只读副本): 生产者每锚写出的 `~/wide_shadow/fea171/xfer_panel_live.npz` 末行 `f_fund_ema` 与生产者账本副本按 v0(原始费率)与 v1(rate×8/iv)各自重算的 EMA 比较, 在账本 iv = 4 的名上报 served/v0 与 served/v1 的中位比。服务口径判为 v1 ⇔ served/v1 中位 ∈ [0.99, 1.01] 且 served/v0 中位 ∈ [1.9, 2.1]。
5. **H2b 存活** ⇔ 训练口径 = v0 且 服务口径 = v1。**H2b 证伪** ⇔ 训练口径 = 服务口径。其余不可判。存活时的量化与「不主张亏损归因」同主文。
