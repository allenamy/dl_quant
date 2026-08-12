> **创建:** 2026-07-20 JST | **Session:** fable multi-asset-v2 (0C 独立评分) | **状态:** final | **作废条件:** 书重建 / DSL xsec-归一修复后重跑
> 对象: 工厂 batch_001 v3 的 7 个 Stage-1 CANDIDATE。台账 `factory_ledger.jsonl`。独立复算 `exports/eda/batch001_step{1,2,3}.py`。

# 工厂 batch_001 — 0C 独立评分终判

## 判词: **0 进书。** id101 = 归一-宇宙伪影(作废+管线修复 flag); A 组 {104,107,120} = 真正交 IC 增量**但净成本死+容量受限**(存档); B 组 {109,114,115} = king/s2 换皮冗余(存档)。**诚实先验 holds, 但 A 组走的是"真信号-净成本死"路, 非 S1/N1b 的"冗余死"路。**

## 逐候选

| id | 公式 | 判 | 依据 |
|---|---|---|---|
| **101** | neg(mul(xsec_z(lturnover), xsec_z(max_ret))) | **VOID** | 归一-宇宙伪影 (下 §1) |
| 104 | neg(xsec_z(ts_max(abs(ret_1h),24))) | **ARCHIVE** | 真增量, 净成本死 (§3) |
| 107 | neg(xsec_z(power(ret_24h,3))) | **ARCHIVE** | 同上, 更弱 |
| 120 | neg(xsec_z(ts_max(rvol_6h,42))) | **ARCHIVE** | 同上 + 容量受限 |
| 109/114/115 | where(...,king,s2) 腿切换 | **ARCHIVE** | king-corr 0.64-0.68 冗余 (§4) |

## §1 等价性把关 + 逐锚 score 残差专项 (你的硬前提)

- **单-xsec_z 公式 (104/107/120): 残差 BENIGN — 你的假设证实。** 逐锚 rank-order **Spearman = 1.000000 (0 flips / 8741 锚)**; 慢参考路径 inc-IC 与台账**逐值吻合** (104 .01216/.01218, 107 .01260/.01259, 120 .01372/.01373, 4 位)。0B 向量化正确, 残差纯是 xsec_z 尺度/tie (rank 不变)。
- **★ id101 (两 xsec_z 的积) 不 benign —— 但不是 0B 的 score_series bug, 是归一-宇宙伪影。** 逐锚 rank-order **每锚都 flip** (Spearman min −0.30), 慢参考 (按 member&CL 归一) inc-IC = **−0.00003 ≈ 0**, 台账 (fast, 按 all-finite 归一) = 0.0123。**根因: `dsl.xsec_z` 在 `np.isfinite` = 全 140 币宇宙归一 (含 ~31 非-member), 而评分宇宙是 member&CL = 109 币** (实测中位 finite 140 vs member&CL 109)。单-xsec_z rank 不变 (无害); **但非单调组合 (mul 的积) 的 rank 取决于两 z 的相对尺度 → id101 的 0.0123 是"用非交易币污染归一"造出的伪影, 按交易宇宙归一 →0。** VOID。
- **★ 管线修复 flag (超出你 (a) 的 absolute-value 层):** xsec 算子 (xsec_z/xsec_rank/xsec_demean) 必须在**评分宇宙 (member&CL) 归一, 非 all-finite** —— 否则非单调公式持续产归一伪影。修法: DSL eval 前把 ctx 通道 pre-mask 到 member&CL (非-member cell 置 NaN)。**这比"absolute-value 环节口径一致"更根本: rank 本身对非单调公式会变。** 修后 id101 根本不会成 CANDIDATE。**建议 0B 修 + 重跑本批 (预期 id101 消失, 104/107/120 rank-不变仍在)。**

## §2 书级 IC 增量 (suppl-v2 c) — A 组**真过** (反直觉, 但真)

书 4-腿 raw-Y4 rank-IC pooled **0.0776**。A 组加书 (value-blend, 逐年 day-block 配对 bootstrap):

| id | lam0.1 Δrank-IC | CI | 逐年 | 显著 |
|---|---|---|---|---|
| 104 | **+0.0046** | [.0039,.0053] | 全正 .0036-.0057 | **SIG+ 无年差** |
| 120 | **+0.0051** | [.0044,.0058] | 全正 .0043-.0062 | **SIG+ 无年差** |
| 107 | +0.0020 | [.0014,.0026] | 全正 (2024 仅 .0008) | SIG+ |

**⇒ A 组是真正交增量 (非 S1/N1b 换皮): king-corr 仅 0.21-0.27 → lottery/MAX-effect 是 king/s2/funding/size 没吃的独立异象, IC 层加书显著+逐年一致。诚实先验"0.012<S1 会死"错在把 inc-IC 幅度当书级价值 —— A 组低幅度但正交, 故 IC 层加书。** (簇: 104↔120 互 corr 0.75 近重复, 107 较distinct; 有效 ~1-2 正交因子。)

## §3 净成本 decider (suppl-v2 e) — A 组**死在这** ★

L/S 组合 (rank-weight unit-gross, 4h, cost 1.9/5.0bps), 净-Sharpe:

| 组合 | net-Sh@1.9 | net-Sh@5.0 | 换手 |
|---|---|---|---|
| **书 (4-腿)** | **12.46** | 8.65 | 0.617 |
| 书+120 | **12.29** (−0.17) | 8.68 (+0.03) | 0.599 |
| 书+120+107 | **12.08** (−0.38) | 8.54 (−0.11) | 0.602 |

**+0.005 rank-IC 不转化为组合 net-Sharpe —— 加候选后 net-Sh 平到略降 (12.46→12.29@1.9bps)。** rank-IC 改善在截面中段 (L/S 权重小处), 组合极端仓未获益。**容量探针 (120): 小-DVOL 半 IC 0.052 vs 大-DVOL 半 0.034 —— lottery 信号住在流动性尾, 容量受限**, 可交易 (大币) IC 更弱。⇒ **suppl-v2 e 死: 增量被组合/成本/容量抹掉。ARCHIVE。** (S2-doctrine 小权重单调改善也不成立 —— net-Sh 非单调改善, 反降。) forward-decay 120 峰 lag0 (0.045), 前向缓降 (slow 因子持续, 非泄漏), 因果 clean。

## §4 B 组 — 冗余 (省电池)

pred-corr vs king **0.668/0.676/0.640** (台账吻合), vs 4-腿书 0.48。全是 `where(...,king,s2)` 腿切换 = king/s2 加开关。**远高于 N1b 的 0.38 (N1b 都书级死)** → 冗余, ARCHIVE, 免电池。

## 给汇报

**batch_001: 0 进书, 但非空手** —— (1) 抓出并作废 id101 归一-宇宙伪影 + 定位一个真管线设计洞 (xsec 该在评分宇宙归一, 修后防未来非单调伪影); (2) A 组 lottery/MAX-effect 是**真正交异象** (IC 层加书显著), 但**净成本+容量死** (信号在流动性尾, +0.005 IC 不转 net-Sharpe) —— 干净的"真信号-不可交易"存档, 非"冗余"存档; (3) B 组换皮冗余。**诚实先验 (0 进书) holds。** 建议 0B 修 xsec 归一 + 重跑 (id101 消失, 104/107/120 结论不变 → 仍净成本存档)。

---
**产物:** `exports/eda/batch001_step{1,2,3}.py` · `/tmp/0c_b1_step{1,2,3}.json` · `factory_batch001_verdict.md`。
