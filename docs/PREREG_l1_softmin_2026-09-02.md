# PREREG · L1SM: 半年块 SoftMin(EVaR)可微书目标(2026-09-02)
> **创建:** 2026-09-02 10:4xZ | **Session:** 主线(用户令: pod 无空闲 GPU, 先用 jpline 3090) | **状态:** 判据冻结, 数字未见 | **作废条件:** RESULT 入档
> **动机受据:** RESULT_xregime_2026-09-02 §3.1 — 本战役所有正臂裕量堆在 2026(高离散年), 基线 V2MAIN 同样 2026 夏普 ≫ 2024; 损失对全史锚等权 ⇒ 高离散年主导梯度。SURVEY_spectral_graph 轴 7 臂 spec(DeePM SoftMin / group-DRO), **从未跑过**(f8 preds 无 L1/DRO 件; 阶梯只跑过 R1/R1CTX/RECB)。穷尽清单: R1CTX(上下文)无增益、T 多塔不立、择时五形态关 —— 本臂是**训练加权**, 无任何 gross 择时输出。

## 装置(单一 sha, 基线与臂同脚本)
`multi_asset/exports/research/retrain_2026-09/pod_f10_train_ext.py` sha **f3c1e3cf3afc**: `SM_TAU` 白名单 {0, 0.5, 1.0, 2.0}(bps/锚); SM_TAU=0 ⇒ 原训练步逐位同(单窗/步, −mean+LDD·ES5)。SM_TAU>0 ⇒ 每步每个**半年块**各抽一窗, 块均值 m_b, 损失 = −SoftMin_τ(m) + LDD·ES5(全部窗净额), SoftMin_τ(m) = −τ·log(mean_b exp(−m_b/τ))(τ→0 最差块, τ→∞ 均值); 每 epoch 总窗数与基线同。验证选模 va = mean − LDD·ES5 **不变**(单变量 = 训练目标)。单变量断言: LPP=LDC=0。
- 机器: jpline RTX 3090, torch 2.7.1+cu126; 数据 = `dlw_2026-08-22` + `f8_2026-08-22`(与 jpline 上 canon f10_V2MAIN preds 同一数据代)。
- **同装置基线**: ARM=V2MAINJP V2=1 SM_TAU=0(jpline 重训, 不覆盖 pod 产 canon 件); 跨机对照 = w10 书层 V2MAINJP vs canon V2MAIN 的 Δ(预期 |Δ| ≤ 0.10, 同 V2 门线; 超出 ⇒ 先查装置再看臂)。
- 复跑命令(逐字): `cd /mnt/storage/private/work_hsy && V2=1 F10_DLW=/mnt/storage/private/work_hsy/dlw_2026-08-22 F10_OUT=/mnt/storage/private/work_hsy/f8_2026-08-22 SEED=<s> ARM=<V2MAINJP|L1SM_t05|L1SM_t10|L1SM_t20> SM_TAU=<0|0.5|1.0|2.0> /root/miniconda3/envs/hsy_v5push/bin/python pod_f10_train_ext.py`
- 书层判官: w10_ftrim_band.py(FTRIM off, 9b76e62bc820 族)FPRED=各 preds → jp_regime_arms_judge.py BASE=w10_canonpred_jp_s42。

## 判据(冻结)
录取 τ*(单个)须同时: ① 2023+ ΔNet_ex 块自举 95%CI **下界 ≥ −0.05**(目标是稳健化, 允许总量持平)且点估 ≥ 0; ② **2024 年块 Δ ≥ +0.10 bps/锚**(低离散年 = 目标本体)且四年中最差年的 Sharpe 不降; ③ 换手 ≤ +25%, ES5 不劣化 >10%; ④ 剂量-反应: 2024 Δ 沿 τ 2.0→1.0→0.5 单调不降, 或至少两个相邻 τ 同时满足 ①②(单点满足 = 不录取); ⑤ s2027 复跑 τ* 同向(①② 同时成立); ⑥ 中间机制观测(不作门, 必报): s42 vs s2027 分年 Sharpe 剖面相关从基线的负值向 ≥0 移动。任何部署另走 V1-V4 全门 + 用户裁定。
## 时序声明
本文 commit 先于任何训练启动; 训练队列: lane A = V2MAINJP s42 → L1SM_t05 s42 → V2MAINJP s2027; lane B = L1SM_t10 s42 → L1SM_t20 s42; s2027 只跑 τ*(若有)。

## 口径追记(09-02 ~10:0xZ, 先于固定席位数字)
1. **同机复跑逐位一致**: jpline 重训 ARM=V2MAINJP s42 的 preds sha256 与 canon f10_V2MAIN_s42.npy **完全相同**(7fa3cc9f…)⇒ (a) 8 月 F-10 战役的 canon preds 本就产自 jpline 3090(脚本头注 "@jpline"), 本次是同机同种子复跑; (b) 装置 f3c1e3cf3afc 的 SM_TAU=0 路径(重构后的 step_list 训练步)与原训练循环**逐位等价** —— 基线未被补丁改变, 收据在此。"跨机对照"改称"同机复跑对照"。
2. **E-0902-D 对模型侧臂的含义**: msharpe 回放 2026 的模型腿席位≈0.01 ⇒ 任何 f10 改动在 2026 回放里近似不可见(L1SM τ1.0: 2026 Δ +0.005, 而 preds 相关只 0.87)。**主判口径追加**: 模型侧臂的书层读数以**固定实盘席位(W3FIX 0.21/0/0.79)**为主, msharpe 口径并报; 判据数字不变(①②③④ 同), 只是在两个口径上都算。此条写于任何固定席位数字之前。
3. τ=1.0 msharpe 口径早读: Δ −0.021 CI[−0.060,+0.019], 2024 Δ −0.024, 2023 −0.099 ⇒ 该口径下不过 ①②。
