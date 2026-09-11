# PREREG · TRACK B 换手/成本轴 (v4 口径)

> **创建:** 2026-09-11 ~07:0xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 判据冻结, 先于任何臂的数字 | **作废条件:** v4 链被推翻, 或 judge_v4 冻结定义被改

## 装置
- 回放器 `/workspace/uplift_2026-09-11/w10_tb.py`
  = `/workspace/review_scratch/health_check/w10_health.py` (sha256 8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d)
  + 六个 TB_* 旋钮; 自身 sha256 a6bae3a1975c7b325321f798f0e3d46c8bb1e022dc604e2e39d0b0db8a28ea87; 生成器 `make_tb_device.py`。
- **空测已过(先于任何臂)**: 默认旋钮下 `d30_n2_c42_rec / _W / S0_rec / S0_W / legs_*` 与冻结件
  `dev_v4/probe_artifacts/w10_ablation_series_V4_A1_dyn_s42.npz` **逐位相等**。
- 树 `/workspace/uplift_2026-09-11/dev_tb/` = dev_v4 三个输入目录的符号链接 + 自有 probe_artifacts。**dev_v4 只读, 未写入。**
- 环境逐字 = run_v4_arms.sh 的 COMMON: `LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=…umask_UPIT_CRYPTO.npz COSTB_JSON=…costb_fee_steady.json SLOW_NPY=…SLOW_v4.npy`。

## 口径(judge_v4 冻结定义, 不重选)
`g = net_ex / gross_total` bps/锚/单位 gross; 冻结窗 2025-03-01 → 2026-08-10 20Z (n=3168);
UTC 日块 bootstrap 2000 次, `default_rng([20260905, k])`。
**我的对照脚本必须先复现已公布的 A1−A0 dyn 对照(+0.061 [−0.168,+0.287] s42 / +0.048 [−0.171,+0.270] s2027) 才允许出新数字。**

## 基线(v4, 已复现 VERIFIED)
A1_dyn: s42 g=+1.9542 SR 3.018 | s2027 g=+1.9453 SR 2.991。A0_dyn s42 +1.8937 SR 3.043(= 钉住的 +1.894/3.04)。

## 臂 (K = 15, dyn 席位, 两种子)
(a) 带 `TB_BAND` ∈ {5e-4, 1e-3, 2e-3}(现 2.5e-4)
(b) EMA `TB_EMA` ∈ {0.05, 0.03, 0.20}(现 0.10; 0.20 为双侧对照)
(c) 只做最大 N 笔 `TB_TOPD` ∈ {50, 100, 200}
(d) 节奏 `TB_CAD` ∈ {2, 3, 6}(8h / 12h / 24h)
(e) 最短持有 `TB_HOLD` ∈ {2, 3, 6} 锚

## 验收门(冻结)
- **G1 主门**: Δg = g(臂) − g(A1) 在冻结窗 dyn 席位上, **两种子**均 点估计>0 且 bootstrap CI95 下界>0(judge 的 (A) 规则)。
- **G2 分辨率门**: |Δg| 必须 > **0.23 bps/锚**(本窗 bootstrap 分辨率)。不到就报 **NOT A RESULT**, 不论 CI。
- **G3 多重检验**: K=15, 报告 Bonferroni 调整后的要求(CI 取 1−0.05/15 = 99.67%), 最优臂必须同时说明未调整与调整后的结论。
- **G4 跨 regime**: 相对 A1, 任一年(2022/2023/2024/2025/2026→08-10)不得恶化超过 0.23 bps/锚/gross。只在 2026 变好的臂按目标("不同 regime 下 Sharpe 显著 >3.0")**拒绝**。
- **G5 重定价不倒序**: 每臂同时在 `TB_COSTM = 3.52/2.148 = 1.638`(换手成本再审线 3.52 bps/单位意图 ÷ 本装置实测 2.148)下评估。排序反转则该臂不予录取。
  (成本项不影响持仓演化 —— 已按码确认 `cbps` 只进 `rec`, 不进 `sm/H/HB/HF/HR/Pi/su` —— 故重定价为解析式: `net_ex' = pnl_ex − carry_ex − 1.638·cost_ex`, 不需重跑。)

## 先验(先写, 后看数字)
本装置 A0_dyn 冻结窗 **cost_ex = 0.1201 bps/锚/gross, 占 net_ex 的 6.34%**; 成本上限收益(成本归零)= +0.120 < G2 的 0.23。
⇒ **纯成本通道在本窗上不可能产生可测量的提升**。这些臂若赢, 只能靠**改变书的持有视界(alpha)**, 不靠省成本。判定按 G1-G5 走, 不按"省了多少成本"叙事。
