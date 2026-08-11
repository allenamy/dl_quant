> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0C 独立审计/评分员) | **状态:** final (pre-registration, 幂等锁定 — 见任何交接候选/破坏产物评分**之前**冻结) | **作废条件:** 冠军面板/口径重建 (king honest-ensemble 或 4-腿书重建)、目标定义变更 (YR/Yraw)、或引擎 canonical 权重/cadence 变更

# 交接验收电池 — 预注册规格 (0C)

**背景与威胁模型.** 项目进入全栈交接: 合作方拿走全套系统 (含训练链) 在**他们自己的服务器**上**重训**。风险 = 他们没有我们积累的验证直觉 (5 个月踩过的塌缩/泄漏/选择偏差/退化坑), 重训出的模型可能带着这些病**通过他们的自测**并上线。**验收电池 = 自动化防线**: 给定一个重训候选的 OOS 预测面板, 机械地判它 (i) **完整** (未塌缩/未泄漏/口径诚实) 且 (ii) **达标** (复现冠军质量), 或 (iii) **值得取代冠军**。电池的判决必须与 0C 当年的人工判决**方向一致** (S1/N1b 当年判死 → 电池应复现)。

**本规格是给 0B `acceptance_battery.py` 的实现契约 + 阈值来源 + 依据。** 每道门给: 精确定义 · 输入契约 · 判据阈值 · 依据 · 冠军参考常数 · PASS/FAIL 规则 · 硬/软分类。**阈值在见任何候选前锁定**; 任何"因候选表现调门"= 违反预注册, 直接作废本文档另起。

---

## 0. 受测对象 · 冠军参考 · 全局不变量

### 0.1 受测对象 (候选交付契约)
候选重训必须交付一个 **OOS 预测面板** npz, key 与冠军 `king_pred_panel.npz` **逐 key 同构**:

| key | shape | dtype | 含义 |
|---|---|---|---|
| `ts` | (T,) | int64 | ms 时间戳 (锚) |
| `pred` (冠军里叫 `king_pred`) | (T,N) | float32 | 候选逐 cell OOS 预测; 非-OOS/非-member = NaN |
| `member` | (T,N) | bool | point-in-time 成员 (trailing-DVOL 月度刷新) |
| `CL` | (T,N) | bool | clean-anchor 掩码 (stride≥H 非重叠) |
| `YR` | (T,N) | float32 | 残差目标 (逐 ts xsec-OLS 残差, ≤t) |
| `Yraw` | (T,N) | float32 | **原始目标** (未残差化, 未 clip 的部署真值) |
| `day` | (T,) | int64 | day-block id (bootstrap 块 = 自然日) |
| `year` | (T,) | int32 | 日历年 (逐 fold/年符号门用) |

**外加 (完整验收必需, 缺则相关门降级为 conditional+flag):**
- **K 个逐-head OOS 面板** (`pred` 同格式), 用于门 (b)/(g) 的 honest-ensemble 重算与 head-多样性检验。**只交付塌缩后的 ensemble = 门 (b) 的诚实性无法机器核验 → conditional + flag "ensemble caliber asserted-not-verified"。**
- **≥3 seed 的 ensemble 面板** (若提供 → 门 (g) 生效; 单 seed 交付 → (g) SKIP+flag)。
- **装配后系统日 P&L 序列** (逐年, net-of-cost, 用于门 (i) 的净-Sharpe 层与"电池抓不住"的执行边界)。

### 0.2 冠军参考常数 (冻结; 全部来自 0C 已归档产物)
| 量 | 值 | 来源 |
|---|---|---|
| 冠军 = **xattn king** (lam_orth=0 + cross-asset attn), 4h | honest-ensemble rank-IC **0.0944** (3-fold) | `xattn_g2_seeds.json` |
| 冠军 3-seed 带 | seeds [0.0948, 0.0910, 0.0973], **σ=0.0026, CoV 2.7%**, min 0.0910 | `xattn_g2_seeds.json` |
| 冠军逐 fold | 9/9 fold-seed 格全正 + 每 seed fold-单调 (f0<f1<f2) | 同上 |
| KING_FLOOR (fold 地板守卫) | 0.055 | `g2_xattn_seeds.py` |
| 书口径 (4-腿 blend) rank-IC | ~0.084 | `qim_final_verdict.md`, `suppl_factor_gate_prereg.md` |
| 面板 scaffold | shape [48168,140], **OOS 覆盖 9851 ts**, 5 fold (2022:2190 / 2023:2190 / 2024:2196 / 2025:2190 / 2026H1:1085), **cross_fold_overlap=0**, 中位 xsec 密度 109 | `king_pred_panel_report.json` |
| embargo (val-end→test-start) | **9 天** (≫ 4h 标签) | `qim_final_verdict.md` §e |
| ts-order / feature-panel md5 | **185d3b65** | `suppl_factor_gate_prereg.md`, `qim_final_verdict.md` §e |
| 冠军 king-pred 值 md5 | **39f5cc4e** | `xattn_g2_seeds.json` |
| 冠军 dyn-share (shuffle-future) | 逐年 0.86–0.95, **均值 0.92**, 无年<0.5 | `qim_final_verdict.md` §a |
| 冠军 forward-decay (raw 目标) | lag0 **+0.070** / +1h(=+H/4) **+0.063** (0.90×峰) / −4h(=−H) **−0.153** (反号=反转机制) | 团队实测参考 |
| N1b forward-decay (resid 目标, 健康反例) | 0 **+0.068** / +4h(+H) +0.031 (0.46×峰) / −4h −0.277 (反号) / +8h +0.022 / −8h −0.049 | `arm_n1b_verdict.md` §4 |
| 引擎 P&L canonical (结构口径) | **rank+cap ≈ 12.2** 逐年 [9.64/11.77/12.55/16.04/11.05]; 可部署-已校准 (isotonic) 变体 10.84 | `engine_v1_review.md`, `engine_return_table.md` |
| 4-腿书 Sharpe | ~8.06 | `arm_s1_verdict.md` |
| 显性成本 / BE per-side | 1.9bps 显性; BE 4.9–16 bps/side | `qim_final_verdict.md` §b |

### 0.3 全局不变量 (所有门共享, 违反任一 = 未评先 REJECT)
- **口径唯一**: 冠军与候选在**逐字节相同的评分协议**下算 (同 CL 掩码、同 embargo、同 honest-ensemble 定义)。门 (b)(i) 的冠军参考数**在候选提交的同协议下重算**, 不硬编 0.0944 (若候选是不同 horizon/口径, 冠军须在该口径重 benchmark; 阈值随之)。
- **诚实 ensemble**: z-score 每 head per-xsec → 等权平均 K head。**明文禁止 per-fold best-head / best-of-grid 选头** (那是拟合 eval, #14/#15)。
- **raw 与残差双报 + ★跨-target 口径裁定 (rev2)**: 所有 IC 门在 Yraw 与 YR 双口径报。**冠军在场时, gate (b) 的候选-vs-冠军比较以 Yraw (原始前向收益) 为准** —— Yraw 是**目标定义无关的真收益** (实测冠军/N1b/S1 三者 Yraw 逐字节相同, md5 02c03849), 故是唯一 apples-to-apples 基。**残差-YR 是训练-目标依赖的** (N1b=YR4B, S1=YR4K, 冠军=YR4), **跨臂不可比** —— 残差-IC 只在同-target canonical 重训 (同 YR4) 下才可比。实测 Yraw 口径: 冠军 **0.1212**, N1b 0.068, S1 0.0669 → REJECT (承重, 无残差-caliber 混淆)。残差口径 (N1b/S1 own 0.016/0.018 vs 冠军 0.082) 也 REJECT, 但那是**补充因子增量 caliber** (book-marginal 门的问题, 非替换门)。Yraw-on-冠军目标必报 (防目标偷偷重定义, #18)。
- **好得惊人必审**: 任一门"超出冠军带上界"→ 触发泄漏子审计 (门 e+f 强制), 宁 flag 不粉饰。

---

## 1. 门 (a) — σŷ/σy ≥ 0.02 (塌缩守卫) · **硬门**

**定义.** 预测的尺度未塌缩到近-常数。对 point-value 输出 (king DAQH 头): 逐 asset 算 σ(pred_i)/σ(Yraw_i) over 其 OOS ts, 取**跨 asset 中位数**。对 rank/z 输出 (尺度无意义): 改判**横截面离散度非退化** —— σŷ/σy 用两者各自 per-asset z-score 后算, 且**逐 ts 横截面 std(pred_t)>0 的 ts 占比 ≥ 0.99**。

**阈值.** 中位 σŷ/σy **≥ 0.02**; 且**无 head** 塌缩 (每个交付 head 单独过 0.02); 且退化-ts 占比 ≤ 1%。

**依据.** CLAUDE.md 核心铁律 + 单资产 #24 (σ-gate BEST checkpoint: TV channel init-noise → 假高-P 破 ckpt)。σŷ/σy→0 是**唯一真守卫** (β 水平不是)。破 checkpoint 常给假高 IC —— 不 gate σ 就会把它当赢家。**这是 IC 数值可信度的前置条件: 门 (a) 不过 → 后续 IC 全部不可信 → 硬 REJECT, 不再看其余门。**

**实现契约.** 输入 `pred, Yraw, member`; 输出 `sigma_ratio_median, sigma_ratio_min_head, degenerate_ts_frac, PASS`。

---

## 2. 门 (b) — 诚实 ensemble rank-IC 达标 · **软门 (质量)**

**定义.** honest-ensemble rank-IC = { 逐 head per-xsec z-score → 等权平均 → 逐 ts 横截面 rank-IC(ensemble_t, target_t) → 跨 ts 均值 }。**明文禁止 per-fold best-head**。pooled + 逐年都算。候选须 ≥ 冠军 − 容差。

**容差推导 (预注册).** 冠军 3-seed 带 σ=0.0026 (CoV 2.7%)。容差 = **max(0.005, 2·σ_seed_候选口径)**。默认 2·0.0026 = 0.0052 → **0.005**。依据: (i) 覆盖观测到的最差冠军 seed 0.0910 = mean−0.0034, 留 ~1.5× 余量; (ii) 一个落在冠军 seed 流形内的真实重训必过; (iii) 一个**实质退化**的重训必挂 —— 具体: 若重训误重启正交惩罚 (lam_orth 1) → IC 塌到 conformer_ref **0.0327**; 若丢掉 xattn lever → lamorth0 **0.067**; 两者都 < 0.0944−0.005 = **0.0894**, 门 (b) 一眼判死。**这正是交接第一风险 (对方重训误引入我们踩过的 loss-design bug) 的机械捕手。**

**阈值.** candidate honest-ensemble rank-IC **≥ 冠军 − 0.005** (同协议冠军重算值; 3-fold 口径参考 0.0944, 书口径参考 0.084 —— 用哪个取决于交付面板的装配层)。

**依据.** 重训"克隆"应落在 seed 噪声内; 低于容差 = 退化/破损重训。**门 (b) 是"可接受克隆"的达标线, 不是"取代冠军"的升级线 (那是门 i)。**

**实现契约.** 输入 K-head 面板 + target; 若只给塌缩 ensemble → conditional + flag。输出 `ic_pooled, ic_by_year{}, champion_ref, tolerance, PASS`。

---

## 3. 门 (c) — 逐 fold/年符号一致 + day-block bootstrap CI · **软门 (质量)**

**定义.** (1) **逐 fold 且逐日历年** rank-IC **> 0** (无反号 fold/年); (2) **day-block bootstrap** (3000× resample, 块=自然日 `day`, 保 intraday 自相关): pooled rank-IC 95% CI **排除 0**; (3) 逐年点估 > 0, 且无年的 bootstrap CI 落到显著负 (反转脆性)。

**阈值.** 逐 fold 全正 + 逐年全正 + pooled 95% CI 下界 > 0。(冠军: 9/9 fold-seed 正 + fold-单调 + 5/5 年正。)

**依据.** 单 fold/单年可为运气 (#14/#1: regime 差异)。**跨 regime 符号一致才是真鲁棒性**; 一个反号年 = regime-脆, 上线会在该 regime 亏。day-block (非 iid) 是因为 4h 锚 intraday 自相关, iid bootstrap 会低估方差 → 假显著。

**实现契约.** 输入逐 ts IC 序列 + `day, year`; 输出 `ic_by_fold[], ic_by_year{}, boot_ci_pooled, boot_ci_by_year{}, all_signs_positive, PASS`。

---

## 4. 门 (d) — 动态占比 ≥ 0.5 (shuffle-future) · **软门 (质量)**

**定义.** shuffle-future 分解: **static tilt** = 打乱预测的时间索引 (保 per-asset 身份、破 timing) 后残留的 IC (即"永远做多某几个币"的持久偏置)。**dynamic share** = (total_IC − static_IC) / total_IC。pooled + 逐年。

**阈值.** dyn-share **≥ 0.5** pooled 且**无年 < 0.5**。

**依据.** 防**静态 tilt 灌水**: 一个塌缩到"总做多幸存者篮子" (survivor-biased basket) 的重训会有高 raw-IC 但全是静态 —— 不是时变 alpha, 上线随篮子漂移死。冠军 dyn 0.86–0.95 (均值 0.92) = 真时变。metrics/positioning 通道尤其易静态灌水 (慢因子)。

**实现契约.** 输入 `pred, target, member` + shuffle 种子; 输出 `dyn_share_pooled, dyn_share_by_year{}, static_ic, PASS`。

---

## 5. 门 (e) — forward-window-decay 因果签名 · **硬门 (泄漏)**

**定义.** 探针 `IC_k = xsec-rank-IC(pred_t, Yraw over 窗 [t+k·δ, t+k·δ+H])`, k ∈ {−2,−1,0,+1,+2}, 两个粒度: **δ=H** (整-horizon 移位) 与 **δ=H/4** (子-horizon 移位)。判"健康因果签名 vs 泄漏"。

**★ 可判定判据 (三条, 全过=PASS):**
1. **前向峰在 k=0**: IC_0 = max over k≥0 的 IC_k, 且 IC_0 > 0。**任一前向 lag (k≥+1) ≥ IC_0 → FAIL** (信号在未来实现 = lookahead: 应向前衰减不向前生长)。
2. **前向平滑衰减, 无平坦无再-spike**:
   - 子-horizon (δ=H/4) 的 +1 lag **≥ 0.6×IC_0** (防"razor-spike": 只有恰好目标点亮 = 单点 lookahead 伪影; 冠军 +1h=0.063=0.90×峰);
   - 整-horizon (δ=H) 的 +1 lag **< IC_0** 且**衰减** (可正-持续=动量, 但不得 ≈峰; 冠军带 N1b +4h=0.46×峰);
   - **平坦泄漏红旗: 若 IC_{+1}/IC_0 ≥ 0.9 (整-horizon) → FAIL** (未来信息被宽泛泄入整窗, 各前向 lag 近等高)。
3. **负 lag = 机制确认器, 非泄漏门 (反转豁免)**: 负 lag 是**已实现的过去窗** (Yraw_{t−H} 在 t 已知), 因果安全 → **不设 |IC| 上限**。一个反转型模型在负 lag 合法呈**反号大 IC** (冠军 −4h=−0.153, N1b −4h=−0.277 = 买近期 loser 的 reversal, lookahead 的**反面**)。**只有当负 lag 与峰**同号**且**幅度 ≥0.5×峰**且 profile 关于 0 **对称钟形** → 判为窗-重叠污染 FAIL** (对称=stride<horizon 的重叠泄漏; 反号非对称=健康反转)。

**依据.** shuffle-future (门 d) **抓不住 in-context/lookahead 泄漏**; forward-decay 是决定性判别 (v2 gate 架构专项 iii, QIM 用过)。对任何"检索近期样本 / in-context / 跨资产滚动相关"结构**强制**跑。**注意反转豁免**: 团队实测冠军负-lag 反号大 (−0.153), 天真"负 lag |IC|≤0.5×峰"会误杀健康反转 —— 故上文把负-lag 判据改为**同号+对称**才判泄漏。

**实现契约.** 输入 `pred, Yraw, ts, member` + horizon H; 输出 `ic_profile{lag:val}` (两粒度) `peak_at_lag0, fwd_ratio_subH, fwd_ratio_fullH, neg_lag_symmetric_samesign, PASS`。

---

## 6. 门 (f) — panel byte-check + ts/member 对齐 · **硬门 (完整性)**

**定义.** 候选面板的**索引** (非值) 必须与冻结 scaffold 逐字节对齐: (1) `ts` 数组 md5 == 参考 **185d3b65** (顺序+值); (2) `member` 掩码与参考 point-in-time 成员一致 (逐 cell); (3) `CL` 掩码一致; (4) **cross_fold_overlap_cells == 0**; (5) fold 严格时序 + embargo ≥ H (参考 9 天 ≫ 4h); (6) 覆盖 = 参考 9851 OOS ts (或候选声明 span, 但 fold 结构须过 4/5)。值 md5 (39f5cc4e) **不要求相同** (候选是新模型), 但索引必须相同。

**阈值.** 全 6 项通过。**任一不过 = 硬 REJECT** (IC 数值不可信)。

**依据.** 防**静默错位**: 候选被算在被打乱/错位的 ts 索引上 → 假高 IC (经典"行错位=泄漏"bug)。**Task 2 的 shuffle-ts 破坏产物在此门挂。**

**实现契约.** 输入候选 npz + 参考 scaffold; 输出 `ts_md5_match, member_match, CL_match, overlap_cells, embargo_days, coverage_ts, PASS`。

---

## 7. 门 (g) — 3-seed CoV ≤ 10% (若提供) · **软门 (质量, 条件)**

**定义.** 若候选交付 ≥3 seed 的 ensemble 面板: CoV = std/mean of {逐 seed 的 honest-ensemble rank-IC}。**外加 head-多样性: K head 两两 pred-corr < 0.999** (防"复制单头"伪 ensemble)。

**阈值.** CoV **≤ 10%**; head 两两 corr < **0.9999** 且 ensemble ≠ 任一单 head。单 seed 交付 → **SKIP + flag "seed-stability unverified"**。

**★ head-corr 阈 0.9999 裁定 (rev2, 实测踩坑):** 冠军 lam_orth=0 使 6 头**天生近冗余** (实测两两 corr **0.9957**) —— **这个冗余就是 +IC 的杠杆** (lam_orth=1 正交惩罚被证 DILUTIVE, 砍半 IC)。⇒ 门 (g) 必须抓**复制** (欺诈, corr→1.0 机器精度), 不抓**设计性冗余**。**0.999 只留 0.0033 余量, 会误杀漂到 0.999 的合法重训 → 收紧到 0.9999 (只对数值复制触发)。** 承重判据是 **ensemble ≠ 任一单 head** (抓 best-head 替换 + 复制填充, 即使头不全同)。

**依据.** 高 seed 方差 = 模型在不稳定流形/近 variance-collapse; 单 seed 幸运不可上线 (#14)。冠军 2.7%, QIM 7.5% (仍过), 10% = 宽松上限。**Task 2 的"复制单头"破坏产物在此门 + 门 (b) 诚实性挂** (K 个相同 head → corr=1.0 → head-多样性 FAIL; 且 ensemble≡单头 = per-fold best-head 违规的伪装)。

**实现契约.** 输入 K-head + multi-seed 面板; 输出 `seed_cov, head_pairwise_corr_max, ensemble_equals_single_head, PASS_or_SKIP`。

---

## 8. 门 (h) — clean 口径强制 · **硬门 (完整性)**

**定义.** 所有 IC 门在 **CL{H} 非重叠锚** (`CL` 掩码, stride ≥ horizon) 上算。**禁止 stride < horizon 评估** (#2/#19: 重叠标签制造自相关伪样本, inflate IC 与显著性)。dense 口径可作补充报告但**永不作判据**。

**阈值.** eval 掩码 == `CL` (逐 cell); 且实现里锚间距 ≥ H 核验。

**依据.** #2 单资产血泪 (stride<horizon 标签重叠) + #19 (eval 方法一致)。冠军 9851 ts 全是 clean 锚。**这是把"账面 IC"锚到诚实口径的门 —— 不过则门 (b)(c) 的数被 inflate。**

**实现契约.** 断言 eval 用 `CL`; 输出 `used_clean_mask, min_anchor_gap_sec, PASS`。

---

## 9. 门 (i) — 升级门 (取代冠军上线) · **软门 (升级, 仅当候选宣称超越冠军时评)**

**定义.** 候选要**取代**冠军进生产 (非"克隆"补位), 须过双层配对检验:
1. **IC 层**: 逐年 **配对 day-block bootstrap** (候选 − 冠军, 同 ts 对齐): (a) **不劣** —— 无年配对 CI 下界显著负; (b) **≥1 年配对 CI 严格 > 0** (显著优)。
2. **净-Sharpe 层**: 装配后系统逐年 net-of-cost Sharpe 配对不劣 (无年显著变差)。

**阈值.** 逐年不劣 + ≥1 年显著优 (IC 与净-Sharpe 都不劣)。**平局 → 冠军留任** (Occam / 低运营风险)。

**依据.** 防"平局换模型": 换模型引入重训风险 (新 bug、新泄漏面) 却无收益。只有**真·更优**的继任者值得换。冠军是在任者, 平局归在任。**Task 2 的冠军-vs-冠军在此门正确 FAIL "≥1 年严格优" (配对差=0, 无升级) → 结论 = ACCEPT-克隆, 非升级** (冠军不取代自己)。S1/N1b 独立面板在此门 FAIL (不优任何年)。

**实现契约.** 输入候选+冠军 IC 逐 ts + 系统 P&L; 输出 `paired_ci_by_year{}, non_inferior_all, strictly_better_any, net_sharpe_non_inferior, PASS`。

---

## 10. 判决逻辑 (门如何合成)

**硬门 (完整性/泄漏): (a) σ-塌缩 · (f) 对齐 · (h) clean 口径 · (e) 因果签名.** 任一 FAIL → **REJECT (数值不可信)**, 判词 = "重训破损/泄漏, 数不可信, 打回重做", 不再解读质量门。

**软门 (质量): (b) IC 达标 · (c) 符号一致 · (d) dyn-share · (g) CoV.** 硬门全过 + 软门全过 → **ACCEPT-克隆** (重训复现冠军质量, 可在冠军槽位部署)。

**升级门 (i):** 仅当候选宣称超越冠军时评。硬门全过 + 软门全过 + (i) 过 → **ACCEPT-升级** (取代冠军)。

**中间态:** 硬门全过但门 (b) FAIL (IC < 冠军−0.005) → **REJECT-as-replacement + flag "退化重训 (完整但更弱), 查因"** (这是 S1/N1b 独立面板 与 "误重启 lam_orth 惩罚"重训 的路径)。

**默认怀疑 (预注册, 防凑数):** 交接重训的**期望**结果 = ACCEPT-克隆 (对方成功复现)。ACCEPT-升级 应罕见 (需真超越)。任何"超冠军上界"必先过泄漏子审计。**0 通过是合法结论** (证明对方重训破损/退化, 打回)。

---

## 11. ★ 电池抓不住的东西 (诚实边界)

电池 gate 的是**"给定面板与冻结目标, 这个模型完整且达标吗"**。它**不**gate 三类风险 —— 各给一句为什么 + 靠什么补:

1. **新数据轴的构建泄漏.** 电池对着冻结 scaffold + 已知目标验模型; 若对方**新建一条特征轴** (新拉 funding/OI/liquidations 源), 其**构建内部**的 look-ahead (如用已修正/已结算值代替 point-in-time 已发布值) —— 门 (e) 只抓得住粗暴的; **慢特征的小步发布-延迟泄漏会存活** (慢特征本就偏静态, 每步泄漏量小, forward-decay signature 仍可近健康)。*补:* 任何新数据轴入面板**前**须过人工 point-in-time 构建审计 + 发布-延迟对齐文档。**电池 gate 模型给定面板, 不 gate 面板的来源。**

2. **执行侧退化.** 全部 IC/结构-Sharpe 门是**信号质量**; 不度量 fill-rate、逆选择 markout、排队、冲击、容量。一个过全门的重训仍可能实盘亏钱 (对方执行栈不同: maker fill<1、延迟更差)。结构 12.2 Sharpe 是**上界**, 可部署约 1/3–1/2。*补:* live maker-fill pilot ($2-5M) + net-of-execution scorecard; 结构表明示"非可部署净值"。

3. **概念漂移的慢衰减.** 电池在历史 OOS span (2022–2026H1) 上判; **看不见未来 regime 变化**。过历史门的模型会随 lead-lag/corr 结构漂移而衰减 (核心约束 #2 非平稳)。*补:* 上线接 online IC monitor (`engine/ic_monitor.py`) + 定期重-benchmark cadence —— **电池是重-benchmark 仪器, 应滚动跑, 非一次性**。

4. **目标/标签的偷偷重定义.** 若对方微调 y 定义 (不同 clip/不同 horizon 对齐), IC 在他们的 target 上好看但在我们的不。门 (f)+全局不变量 §0.3 的 **Yraw-on-冠军目标双报**抓大部分, 但完全一致的重定义仍需人工核 target 生成码。*补:* 冻结 `Yraw` 定义作 ground-truth, 候选 IC 必在**我们的** Yraw 上复算 (#18: raw-y eval)。

---

## 12. ★ 复现测试矩阵 (预注册, Task 2 用 — 电池判决须与 0C 人工判决方向一致)

0B 交付 `acceptance_battery.py` 后, 0C 用现有产物跑三组对抗测试, 核验电池复现人工判决:

| 测试 | 输入 | 预期判决 | 触发门 |
|---|---|---|---|
| **T1 冠军 vs 冠军** | `king_pred_panel.npz` 作 candidate + reference | **ACCEPT-克隆** (硬+软全过; 门 (i) 的"≥1 年严格优" FAIL = 不升级 → 正确不取代自己) | 全 PASS, (i) 升级=No |
| **T2 冠军 vs 存档 N1b / S1** | `arm_n1b`/`arm_s1` 独立 OOS 面板作 candidate | **REJECT-as-replacement** (独立 rank-IC ~0.068(N1b raw)/0.016(resid) < 0.0944−0.005; 门 (i) 不优任何年) —— 复现 0C 当年判死 | 门 **(b) FAIL** (低于达标线) + 门 **(i) FAIL**; 门 (e) N1b **应 PASS** (健康反转签名, 不误杀) |
| **T3a 冠军 + shuffle-ts** | 冠军面板打乱 `ts` 索引 | **REJECT (不可信)** | 门 **(f) FAIL** (ts md5 失配); 连带 (e) 平坦/无峰、(b) 塌 |
| **T3b 冠军 + 复制单头** | K 个相同 head (= 单头复制) 作 ensemble | **REJECT (口径不诚实)** | 门 **(g) FAIL** (head 两两 corr=1.0) + 门 (b) 诚实性 flag (ensemble≡单头 = best-head 伪装) |
| **T3c 冠军 + 注入 lookahead** | 目标回移使 pred 见未来 (**scale-matched**: z(Yraw_{t+H}) 按权重 w≈0.85 掺入 pred_t) | **REJECT (泄漏)** | 门 **(e) FAIL** (峰移到前向 lag) |

**★ T3c 注入必须 scale-matched (预注册, 实测踩坑):** pred 与 Yraw 尺度差 ~43× (pred z-scaled σ≈1.0, Yraw σ≈0.023)。天真加性注入 `pred + 3·Yraw_{t+H}` 只搅动 ~7% → profile 仍健康 (峰 lag0) → 门 (e) **正确地不触发** (可忽略幅度非 material 泄漏, §11)。要制造**可检测**泄漏, 注入必须**尺度匹配** —— 逐 ts z-score 未来收益后按权重 w≈0.85 混入 (或纯 rank-替换), 使前向窗真正主导排序。实测: 加性 α=3 → 门 (e) PASS (漏检); α=50 或 w=0.85 或纯替换 → 门 (e) FAIL (峰移 +1, IC 0.965)。**破坏产物构造器 (自测) 的注入幅度是自测正确性的一部分, 不是门缺陷。**

**判据: 电池对 S1/N1b 的判决必须是 REJECT (与 0C 当年一致)。** 注意路径差异 (诚实上报): 0C 当年判 S1/N1b **存档**的主因是**书级冗余/换皮** (pred-corr king 0.36/0.38, book-corr 0.48/0.55, 进书 HURT) —— 那是**补充因子 book-marginal 门** (`suppl_factor_gate_prereg.md`) 的判据, 与本验收电池是**两个不同仪器**。本电池测的是**独立取代**场景 → 经门 (b)/(i) 的独立-IC-达标线 REJECT。**方向一致 (都 REJECT), 路径不同** —— 本电池不宣称复现 book-marginal 逻辑, 只复现"独立候选够不够格取代冠军"。若要电池也 gate"进书边际", 须另接 suppl-factor 书级门 (不在本规格范围, §11 之外的第五类"抓不住" = 组合级稀释, 由 book-marginal 门单管)。

---

**产物 (0C 交付):** 本规格 `acceptance_battery_SPEC.md` (预注册锁定)。**0B 实现 `acceptance_battery.py` 须逐门对齐 §1–9 实现契约 + §10 判决逻辑 + §12 复现矩阵**; 0C 收到后按 §12 三组对抗测试审, 判词回报 team-lead。
