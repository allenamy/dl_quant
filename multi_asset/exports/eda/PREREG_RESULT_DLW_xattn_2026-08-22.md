> **创建:** 2026-08-22 07:3xZ | **Session:** 6737834a-DLW | **状态:** 预注册冻结(§P 段 SHA256 先于任何数字入库, 见 git commit 信息与本文末尾回执); 结果段待回填 | **作废条件:** `docs/DESIGN_dl_wide_targeted_2026-08-22.md` 预门(G0)不过 ⇒ 本线(横截面注意力臂)关闭; pod 2020-21 缓存可达后第 5 折(2022)复核由新日期文件取代并互链; 09-01 重训换代后以新 king 重跑 G1; STATE.md §3 永远优先

# DLW · 宽宇宙(400 名)有针对性 DL — 预门 G0 + 第一臂(横截面注意力)

**任务来源:** `docs/DESIGN_dl_wide_targeted_2026-08-22.md`(§0–§4; 用户令"先进有思考有设计有针对性的 DL model 可以用最深入的思考来进行验证和尝试"); 本文件只做 **G0 预门基准(Ridge82 / LGBM82)+ D0 对照(film2 无横截面注意力)+ D1 第一臂(横截面注意力, 头数 8/4/1)** 三件, 简单收益残差目标, 实盘相位 [N, N+4h], 400 名, jpline 3090 单卡单任务。

**受据(引用前已打开):**
- 训练协议: `multi_asset/exports/eda/kcurve_2026-08-15/pod_kcurve.py`(film2 K400 K 曲线装置, 训练体逐字冻结自 pod_wide/pod_fast2; jpline 副本 `w3lane/kcurve/pod_kcurve_jp.py`); 终判 `pod_kjudge.py`(固定锚 3221 / Q4 = BTC 尾随 7 日波动最坏五分位); 受据 `DESIGN_wide_book_v1_2026-08-15.md` §3-bis(film2 K400 三种子 +0.0645)。
- 弹药: `runpod_scripts/workspace_mirror/pod_fea_wide.py`(wide_fea_v1 82 列 = 7 通道 × 5 窗{48,288,864,2016,8640} 滚动统计 35 + vol 5 窗 = 40 值列 × {值, 逐锚成员内秩} + fund_ema/fund_now)+ `pod_bracketB_lgbm.py`(LGBM82 参数 400/0.05/63/0.8/0.8, 固定锚 2025-26 **+0.0690**)+ `DESIGN_wide_book_v1` §6-bis(B 梯队四方终表: film2 0.0645 < K2W 0.0666 < LGBM82 0.0690 < 堆叠 0.0703; F1 融合 0.0679 FAIL / F2 森林×film2 0.0687 平手)。
- 残差目标基线: `DESIGN_wide_book_v1` §5(YR4_wide = Y4 − 逐锚 xsec 岭回归投影, 基 = 六因子 rev_4h/rev_24h/vol_7d/range_24h/mom_7d/fund_ema 的逐锚 xsec-z, λ=1e-3, ≥60 成员; "不平移 110 基线")+ §3-quinquies(**resid 目标轨 v1 已关闭**: 值空间残差化力度弱 R²≈0.3%, 残差≈原目标; raw 训练+事后投影 0.0330 ≥ resid 训练 0.0306)+ FF `kcurve_2026-08-21/RESULT_funding_factor_deepdive_2026-08-22.md`(地基没歪 ⇒ 残差基准不动)。**本装置按主线令使用残差目标, 并预告: 按 §3-quinquies, 残差秩 IC 与原始秩 IC 预期几乎相同; 两口径并报。**
- 口径: WS `kcurve_2026-08-21/RESULT_wide_return_source_2026-08-22.md`(5m 缓存 ts = bar **收盘**时刻; 旧 y4 = [T−5m, T+3h55m] 含已知 bar; 09-01 重训目标改为对齐窗口 (T, T+4h] 简单收益); PH `RESULT_phase_alignment_2026-08-22.md`(实盘持仓窗 = [N, N+4h]; `ph_preds_2026-08-22.npz` = 在役 king 因果面板/实盘相位推理的参照, 140 名, 本装置不直接使用)。
- 记忆: `champion_baseline_repro`(单变量 A/B 双种子同向且 |Δ|≥0.005 才算测出; 种子噪声 ±0.002) · `feedback_verify_cudnn_not_just_cuda`(cuDNN 校验) · `feedback_no_multi_seed_2026_05_15`(不集成; 三种子只作噪声标定) · `lam_orth_dose_response_flattened_horizon`(本模型无 lam_orth) · `regime_stability_is_horizon_property`(判据必须带 Q4) · `residual_regime_survival_peaks_at_y12`(y12 只在 12h 记账口径内成立, 本装置只做 y4) · `wide_book_kcurve_signal_go` · `wide_book_bracketB_verdict` · `engine_a_wide_factor_miner`(xattn +0.031 于 110 小时级, lam_orth=0 下 +41%) · `ma_v2_champion_dir_trap`(xattn 默认关陷阱 —— 本装置用显式开关, 每臂打印 n_params 与 xattn 状态)。

**★ 先澄清一个前提(代码读出, 非转述):** 宽书 K 曲线用的 `film2` 模型(`pod_kcurve.py` `Model.forward`)**已经带一层顶部横截面注意力**: 逐名池化向量 `z`(维 2·CHW=256)按锚分组 → `LayerNorm` → `nn.MultiheadAttention(256, 8 heads, key_padding_mask)` → 残差相加, 即对同锚全部成员(≤400 名)做一次学习型的跨名混合(另有 `MIDX` 中层跨名注意力, 默认关, 未在 K 曲线中使用)。因此 **"原 film2 K400 协议" = 有 xattn 的形态 = 本文 D1(h=8)**; "无 xattn 对照" D0 必须通过**移除**该层构造。主线任务书写的"原 film2 K400 协议(无 xattn)"与代码不符, 本文按代码事实定义臂, 并已向主线报告。

**主线裁定(08-22 07:5xZ, 收到于 §P 冻结之后, 不改 §P 任何字; `docs/DESIGN_dl_wide_targeted_2026-08-22.md` §1-bis 同步):** ① 按本文臂定义执行(D1 = 原 film2 逐字含顶部 xattn h=8; D0 = 移除; 敏感 h=4/1); 本臂读数 = "顶部横截面注意力贡献几何"(≈0 ⇒ 第四证)。② 横截面注意力臂降为消融; **下一臂 D2 = 多视界多任务**(共享编码器 + y4/y12 残差简单收益双头, 只用 y4 头出分, 与 D1 同设置单变量); MIDX 中层跨名注意力只在 D1−D0 ≥ +0.003 且逐折同号时立臂。③ 4 折读法接受(≥3/4; 恰 3/4 标条件通过); F-1 重建完 2020-21 缓存后补 2022 折。④ G0 先出, DL 臂以它为线(+0.005)。

---

<!-- PREREG-BEGIN -->
## P. 预注册(冻结段; 本段 SHA256 先于任何数字入库)

### P.0 问题与三选一
1. **G0 预门**: 同一 82 列弹药、同一 400 名成员、同一简单收益残差目标、同一走前折上, Ridge82 / LGBM82 的秩 IC 是多少 —— 这是 DL 臂必须跨过的线(+0.005)。
2. **D0 vs D1**: 在 5m 原始序列 DL(film2 协议)上, **横截面注意力这一个归纳偏置**是否带来可分辨的增量(D1 − D0), 以及头数(1/4/8)的剂量曲线。
3. **G0 判定**: D1(h=8)对 max(Ridge82, LGBM82) 的 ΔIC 是否 ≥ +0.005 且逐折同号。
**结论形态(四选一, 先写死)**: (a) **新归纳偏置有增量且过预门**: D1−D0 过增量判据 **且** G0 过 ⇒ 进 G1; (b1) **有增量但不胜树**: D1−D0 过增量判据, G0 不过 ⇒ 关臂(不调参), 记"横截面注意力在 5m 序列 DL 内有效, 但 DL 整体仍不过树线"; (b2) **无增量(第四证)**: D1−D0 落在噪声内 ⇒ 关臂, 记"三方等价定理在宽书横截面注意力维度上复现"; (c) **传闻**: 任一有效性检验(P.6)不过 ⇒ 不出具 (a)/(b), 只报数字并标"传闻"。

### P.1 数据、锚、成员、目标(全部冻结; 唯一真相源 = `dlw_targets.npz`, G0 与 DL 臂共用)
- **5m 缓存**: jpline `/mnt/storage/private/work_hsy/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz`(ts = bar 收盘时刻, 2022-01-01 00:00 → 2026-08-11 00:00, 步长 300 s, 484,705 行 × 829 名 × 7 通道 [ret5, range, cpos, log_qv, log_cnt, log_avgsz, tbf], f16; SHA256 运行时写入结果 JSON)。**jpline 缓存自 2022 起 ⇒ 可用走前折为 2023/2024/2025/2026 共 4 折**; 2022 折需 2020-21 缓存(pod 不可达; F-1 正在 jpline 重建 `probe_artifacts/f1/dlnative_5m_wide829_f16_hist_f1.npz`), **本文不等它**: 4 折先判, 第 5 折(2022)作为后续复核条目(见 P.7)。
- **锚**: E = 缓存行 ts % 14400 == 0(即名义 4h 锚 N = 00/04/…/20Z 的收盘行), 且 E ≥ 576, E + 48 ≤ TT − 1。
- **成员(K400, 与 K 曲线/B 梯队同筛, 统计窗沿袭旧装置 rows [E−2016, E))**: 7 日覆盖 ≥ 0.95 且 7 日 5m 波动 ≥ 1e-4 且目标 y4s 有数, 按 7 日平均 log_qv 取前 400 名; 成员 ≥ 50 的锚才入样。
- **目标(实盘相位, 交易所记账口径)**: `y4s[i,n] = Π_{k=1..48} (1 + ret5[E+k, n]) − 1`(持仓窗 (N, N+4h], 48 根 5m bar 复利 = 1h 收盘→收盘简单持有收益; 缺 bar 视为 0 收益, 有数 bar < 46 ⇒ NaN)。**与旧 y4(Σ ret5 rows [E, E+47], 窗 [N−5m, N+3h55m], 含已知 bar)不同 —— 这是 WS 指定的 09-01 重训口径。**
- **残差目标**: `YR4s[i,n] = y4s[i,n] − X_i β_i`, X_i = 六因子 {f_rev_4h, f_rev_24h, f_vol_7d, f_range_24h, f_mom_7d, f_fund_ema} 在 `w3lane/kcurve/data/wide_panel_4h_v1.npz` 锚行(ts = N; 因子只用 ≤N−5m 数据, 因果)上的成员内秩 z(缺失 ⇒ 0), 岭 λ=1e-3, 有数成员 ≥ 60 才回归(否则该锚 YR NaN ⇒ 不入训练/评估); **与 DESIGN_wide_book_v1 §5 逐字同构, 基不平移**。
- **训练标签(三方同)**: `YRZ` = 成员内 YR4s 的秩, 线性缩放到 [−0.5, 0.5](不训幅度, IC 是 alpha)。
- **特征/输入的行窗(三方同, 与目标零重叠零间隙)**: 一切输入只用缓存行 ≤ E(收盘 ≤ N 的 bar, 含收盘于 N 的那根; 实盘决策在 N 之后, 该 bar 可得); 目标从行 E+1 起。装置内断言: `max_feature_row == E` 且 `min_target_row == E+1`。
- **82 列弹药(G0 用; 定义逐字 pod_fea_wide.py, 仅窗端点按上条对齐为 rows [E−w+1, E+1))**: 7 通道 × 5 窗 {48, 288, 864, 2016, 8640} 的窗内均值(ret5 取窗和)= 35 值 + vol 5 窗(窗内 ret5 标准差)= 40 值列, 每列取 {值(clip ±1e4, nan→0), 逐锚成员内秩 [−0.5, 0.5]} = 80 列 + fund_ema、fund_now(面板锚行, nan→0)= **82 列**; 只对成员计算, 长格式存 f16。
- **DL 输入(film2 协议逐字)**: 每名 576 行 × 8 通道(7 通道成员内按训练折统计标准化 clip ±5 + 1 全有数掩码), 行窗 [E−575, E]; FiLM 条件 8 维 regime ctx(BTC 7 日波动 / 同锚 2 日截面离散度 / 1 日广度 / 7 日平均绝对收益 × 100, 自身 7 日波动 log1p / 波动分位 / 1 日量能 z / 1 日 tbf 偏移; 窗端点同样对齐到 ≤E)。

### P.2 折与评估集(三方同)
- **走前折**(与 pod_kcurve.py 同): 测试年 YV ∈ {2023, 2024, 2025, 2026}; 训练 = 年 < YV 且锚序号 < 该测试年首锚 − 60(60 锚 = 10 天隔离); DL 的验证集 = 训练锚最后 15%(检查点 = 8 个 epoch 中验证 IC 最高者, 协议原样); Ridge/LGBM 用训练锚全部(无验证集)。测试 = 年 == YV 的全部锚。
- **固定锚集 A(主)** = 2023–2026 全部测试锚中, 成员内 YR4s 有数 ≥ 30 且 **本次比较涉及的全部臂**都有有限预测的锚; 逐折 = 集 A 内按测试年分。**固定锚集 B(对照表用)** = 集 A 中成员 ≥ 360 的锚(= K 曲线/B 梯队"固定锚 2025-26"的同构定义), 只为与 0.0645/0.0690 表对位, 不参与门判。
- **噪声标定**: D1(h=8) 三种子 {42, 2027, 3037}, D0 双种子 {42, 2027}(时间允许); 报各臂 IC 的种子 sd; **不集成、不挑种子**; 主臂一律 seed 42。

### P.3 臂(每臂一个变量; 参数量与 xattn 状态每次打印)
| 臂 | 定义 | 唯一变量 |
|---|---|---|
| **R82** | Ridge(α=1.0)on 82 列(训练折均值/标准差标准化, clip ±5), 标签 YRZ | 预门基准 |
| **L82** | LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, random_state=0, n_jobs=8; 参数沿 B 梯队不搜), 标签 YRZ | 预门基准 |
| **D0** | film2 K400 协议(8 层膨胀卷积 CHW=128 + GroupNorm + FiLM(8) + 末 288 行注意力池化 ∥ 末行 → z(256) → QIM 25 分位 pinball 头; EPOCHS 8, LR 1e-3, AdamW wd 1e-4, 余弦, 梯度裁剪 1.0, BATCH=4 锚, seed 42), **顶部横截面 MHA 与其 LayerNorm 移除**(z 直接进头; 名与名只经 FiLM 的固定截面统计耦合, 无学习型跨名混合) | — (对照) |
| **D1(h)** | D0 + 顶部横截面注意力层(z 按锚分组 → LayerNorm → MultiheadAttention(256, h, key_padding_mask) → 残差相加), h ∈ {**8**(主, = 原 film2 K400 逐字), 4, 1} | 横截面注意力(h = 剂量) |
- 参数预算: D1(8) = 原 film2 K400 预算(逐字), D0 比 D1 少恰一层 MHA(≈4·256² + LN); 本文**不**给 D0 另补参数(补参数 = 第二个变量); 若 D1−D0 为正且过门, 后续臂再做"参数对齐的逐名 MLP 对照"(列入 P.7, 本文不跑)。
- 不跑: MIDX 中层跨名注意力、82 列并入 DL(F1 融合已 FAIL)、多视界/状态 token(设计稿另臂)、任何调参。

### P.4 读数(每臂必报)
- **主**: 集 A 逐锚 Spearman(pred, YR4s) 均值(残差秩 IC); 逐折(4 年); 集 B 同; **副**: 逐锚 Spearman(pred, y4s)(原始秩 IC); 逐名时序 Pearson(pred, YR4s)在测试锚 ≥ 200 的名上的均值(双口径之第二口径; 与秩 IC 符号分歧 ⇒ 标危险信号); 4h 锚 = 4h 视界 ⇒ 相邻锚目标不重叠, clean ≡ dense, 只报一套。
- **Q4**: BTC 尾随 7 日 5m 波动(rows [E−2016, E))在集 A 内的五分位, 最高档 = Q4; 报各臂 Q4 IC 与 Q4/全体比。
- **σŷ/σy**: 逐锚 std(pred)/std(YRZ) 中位数(DL 臂塌缩守卫 ≥ 0.02; Ridge/LGBM 并报)。
- **Δ 的配对 t**: 臂间逐锚 IC 差的均值 / (sd/√n)(同锚配对)。

### P.5 门(冻结)
- **G0(预门)**: ΔIC_A = IC_A[D1(8)] − max(IC_A[R82], IC_A[L82]) **≥ +0.005** 且 逐折 Δ > 0 的折数 **≥ 3/4**(设计稿"≥4/5"在 4 折可用下的对应; 4/4 并报; **恰为 3/4 时标"条件通过, 待第 5 折(2022)复核"**, 不得自行升级为通过)。不过 ⇒ 关臂, 不调参续命。
- **归纳偏置增量判据(D1 − D0)**: ΔIC_A[D1(8) − D0] ≥ +0.005 且 逐折同号 ≥ 3/4 且 ≥ 2 × D1 三种子 sd ⇒ "有增量"; |ΔIC_A| ≤ max(0.002, 三种子 sd) ⇒ "无增量"; 其余 ⇒ "未分辨"(照实写, 不升级)。头数 1/4/8 只报剂量曲线, 不设门。
- **G1(仅 G0 过才算)**: 对宽书 slow king K0(pod `slow_pred_hist_oos.npy`, 按 E_ts 对齐到本装置锚; K0 训练口径为旧 y4 秩, 相位/窗口差异照实标注)逐锚成员内 OLS 残差化 D1 分数, ΔIC = 残差分数对 YR4s 的逐锚 Spearman 均值 **≥ +0.003 且逐年(2023–26)≥ 0**; 并报堆叠读数 IC(z(K0) + λ z(D1)) − IC(K0), λ ∈ {0.25, 0.5}(只报不判)。
- **G2(书级)**: 不在本文范围; G0+G1 皆过才立项(宽书同管线 d30 简单口径 3.52, 含去 fund 腿情景)。

### P.6 有效性检验(任一不过 ⇒ 该臂读数标"传闻")
1. **结构断言**: `max_feature_row == E`、`min_target_row == E+1`(三方同源 `dlw_targets.npz`); 训练行全部 < 测试首锚 − 60。
2. **shuffle-future null**: 每臂对集 A 内同年锚随机置换目标行(种子 0–2)重算 IC, 均值须 |IC_null| < 2 SE(SE = 真 IC 的逐锚 sd/√n); 否则评估管线本身漏。
3. **锚→目标行偏移谱**: IC_k = 逐锚 Spearman(pred_i, YR4s_{i+k}) 均值, k ∈ [−6, +6](±24h); **峰必须在 k=0**; k>0 应平滑衰减(4h 预测器的形态), k<0 读作机制旁证(与 Engine A "负 lag 为负 = 截面反转"同读法), 不设门。
4. **σŷ/σy ≥ 0.02**(DL 臂)。
5. **cuDNN 校验**: `torch.backends.cudnn.version() is not None` 写入 JSON; GPU 占用峰值与每折每 epoch 用时写入日志。
6. **复现钩**: 脚本 SHA256 + 输入 SHA256 + 全部常数写入结果 JSON; 预测矩阵(锚 × 829)逐臂逐折落盘。

### P.7 四问与待办(结果段逐条回答)
- **口径**: 简单收益 / 实盘相位 (N, N+4h] / 残差基 F6 / 秩 IC 主、Pearson 副 / 集 A 主、集 B 对照 / 4 折(非 5)。
- **泄漏**: 输入 ≤ E, 目标 ≥ E+1; 折隔离 60 锚; 成员内秩特征逐锚算; 残差基因果; P.6 两检。
- **选择效应**: 判据先冻结; 主臂 seed 42 固定; 不挑种子不挑头数; 检查点选验证最优为协议原样(D0/D1 同受其影响); LGBM 不调参。
- **regime**: 逐年 + Q4 + 2023-24 / 2025-26 分段。
- **待办(不在本文范围)**: 第 5 折(2022)复核(需 2020-21 缓存); 参数对齐的逐名 MLP 对照(仅 D1−D0 为正时); 多视界多任务臂 / 状态 token 臂(设计稿 §1.2/§1.4, pod 回来后); G2 书级(仅 G0+G1 过)。
<!-- PREREG-END -->

---

## R. 结果(回填; 任何数字在本节之前不存在)

(待回填)

---

## 回执
- 冻结段 SHA256(`sed -n '/<!-- PREREG-BEGIN -->/,/<!-- PREREG-END -->/p' | sha256sum`): (commit 信息中给出)
- 装置: `multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-22/dlw_*.py`; 结果: `.../devices_2026-08-22/results/dlw_*.json`; jpline 工作目录 `/mnt/storage/private/work_hsy/dlw_2026-08-22/`(data/preds/results/logs)。
