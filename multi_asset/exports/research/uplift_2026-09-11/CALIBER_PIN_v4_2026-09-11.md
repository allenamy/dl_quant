# 口径锁 · 本研究分支一律按 v4 链(2026-09-09)· 任何 v3 谱系数字作废

> **创建:** 2026-09-11 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 生效中, 约束本分支 `research/book-uplift-2026-09-11` 的全部产出 | **作废条件:** 出现比 v4 更新的链且逐门验过
> **用户令(2026-09-11):** 「过去两天的工作就是修复了很多历史口径, 数据特征处理的问题, 所以新的调研要按照最新的正确口径来。」
> **正典定义:** `docs/RESULT_v4_chain_retrain_quantify_2026-09-09.md` + 预注册 `docs/PREREG_v4_chain_retrain_quantify_2026-09-09.md` + 装置收据 `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`(5749a821, `receipts/*.json`)

## §1 用这些(v4, 正确)— 全部已在 pod2 核实在位(VERIFIED 2026-09-11)

| 组件 | 路径 / 规则 | 实测 |
|---|---|---|
| 5m 缓存 | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz` | 2.0G ✓ sha16 1d7f459d; 覆盖门 v2 PASS(洞 0 / 宽缺口 0) |
| king 特征元 | `/workspace/data/wide_fea_v4_meta.npz` | 25M ✓ 轴 E_ts **10182**; 由 `pod_fea_ext_clamp.py` PANEL_IN=v2ext 产 |
| DL 目标+特征 | `/workspace/dlw_v4raw/data/{dlw_targets.npz, dlw_fea82.npz}` | 184M / 447M ✓ RAW 臂, raw_patch 952 bar; DL 轴 **10212** |
| CLIP 对照臂 | `/workspace/dlw_hf3/` | ✓ 仅作对照, **记账口径是 RAW** |
| king v4 预测 | `/workspace/shadow_bundle_v4/slow_pred_pinned.npy` | 33M ✓ |
| 记账元 | `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz` | 27M ✓ 自检 vs `meta_newprod_raw`: 洞邻域外 y4 maxabs **9.09e-13**, 成员/qvk 逐位相等 |
| 回放树 | `/workspace/review_scratch/health_check/dev_v4/` | ✓ `BUILD.json`; `dlw_2026-08-22 -> dlw_v4raw`; `probe_artifacts/w10_ablation_summary_V4_*.json` |
| 回放装置 | `/workspace/port_w10/w10_universe.py` | ✓ |
| 判官 | `retrain_2026-09/v4_chain_2026-09-09/judge_v4.py` + 同目录 `ELIGIBILITY_CONTRACT.json`; `JUDGE_HC=/workspace/review_scratch/health_check` | ✓ |
| epoch 规则 | **FIX7**(不是 argmax —— argmax 含 2026 验证片) | — |
| legs | `pod_legs_v4.py` 全行重算(v4 成员 / king v4 / RAW y4s) | — |
| 面板导出步 | v3splice + canoncont, 且**必须显式传 `EXPORT_PANEL` / `EMA_STATE_JSON`** | 漏传曾造成守卫假红 1.96 vs 真读数 2.30(E-0826-D 族) |

## §2 不许用(v3, 已知缺陷 — 由其得出的数字一律作废)

| 产物 | 缺陷 |
|---|---|
| `/workspace/dlw_ext/` 与 `_ext` 5m 缓存 | 被 holefix2 取代(有洞) |
| `pod_fea_ext.py` | **E-0909-A**: 构建器 `E−w` 窗未 clamp, 回绕, 首 138 锚错 |
| 裁剪复利记账 `y4s = Π(1+clip)−1` | **E-0908-B**: 先裁剪再复利, 把真实 −48% 写成 +55%。已由 RAW 记账取代; 尾部数字一律报**下界** |
| `pod_legs_ext.py` | 旧行原样保留, 未随 v4 成员/king 重算 |
| `/workspace/shadow_bundle_v3/slow_pred_pinned.npy`, `/workspace/data/wide_fea_v2ext_meta.npz` | v3 谱系, 只能作显式对照并标注 v3 |
| `engine/panel_source.py` 的**默认**面板 | 是 as-trained **脏面板**; 特征类实验必须显式传因果面板 |
| 对 pod 5m 谱系施 `expm1` | 该谱系 y4/Y4 = **Σ 5 分钟简单收益**; expm1 只属对数面板谱系 `multi_asset/data/build_wide_dl.py`(**E-0904-F** 伪凸性) |

## §3 判官的冻结定义(不得重选)

`g = net_ex / gross_total`, 单位 **bps/锚/单位 gross**。冻结窗 **2025-03-01 → 2026-08-10 20Z**。CRYPTO m1 掩码。
UTC 日块自举 **2000** 次, 基种子 **20260905**, 子流 `[20260905, k]`。严格书合同 `JUDGE_REQUIRE_W=1`。
判官另已定义的窗: `2024-01→2026-08-10 20Z` · `ext 2026-08-11→08-30 20Z` · `2026→08-31 20Z` · `EXTENDED 2025-03-01→2026-08-31 20Z` · `2024-01→2026-08-31 20Z`。
臂的合格性**只经** `ELIGIBILITY_CONTRACT.json`(逐臂 candidacy_gate / 已批准门源 sha256 / 收据绑定该臂 / 每个 REQUIRED_INPUT 逐个哈希)。**本地改过的门重跑出的收据不是被复核的程序。**

## §4 v4 口径下要被超越的基线(A0 = 在役形态)

动态席位, 每 gross 年化: 2022 **+0.8%** | 2023 **−13.7%(负年)** | 2024 **+12.3%** | 2025 **+16.7%** | 2026→08-10 **+81.7%**。
冻结窗 2025-03-01..2026-08-10: **+1.894 bps/锚/gross, Sharpe 3.04**, 年内 maxDD 820 bps gross(2× ≈ 16% NAV)。
A1(king v4 + F10 v4 RAW)冻结窗 +1.954 / +1.945 双种子, Sharpe 3.02 / 2.99。
A1−A0 双种子: 动态 +0.061 [−0.168, +0.287] / +0.048 [−0.171, +0.270]; 固定 +0.005 / −0.010 ⇒ **(C) UNDECIDED**。
固定实盘席位 0.21: **2022–2025 四年皆负**; 2024→08-10 +13.0%/gross/年, 跨年 maxDD 33% gross。
**实盘书用动态席位**(msharpe on live LR), 所以动态行才是对的参照。
**冻结窗上的自举分辨率约 ±0.23 bps/锚 —— 小于它的提升不是结果。**

## §5 v4 文档自带的、同样约束我们的限制

A0 逐年表是**在役形态在正确口径下的期望区间, 不是实盘曲线**; 回放止于 2026-08-31; 九月数据不入该轮; **不主张 v4 提高收益**; V4 跨机门因 jpline 不可达未做。

## §6 本轮已按此更正的我方产出

- `REFRAME_lead_2026-09-11.md` §1 曾以 `AUDIT_live_vs_replay_2026-09-04.md` 臂 C(冻结宇宙 + **固定**席位, v3 谱系)为主参照 ⇒ **已降级为 v3 对照**, 主参照改为本文 §4。该处曾把书说得比实际差, 并据此写出"只在一种 regime 里工作"的过强表述, 一并收回。
- 涉及"2021–2024 连亏四年"的表述收回: 那是固定席位 + 冻结宇宙臂; v4 动态席位下是 2022 +0.8% / 2023 −13.7% / 2024 +12.3%, 只有 2023 是明确负年。
- 实盘侧测量(`GROUNDTRUTH_lead_2026-09-11.md`)不受影响 —— 它只用实盘账本, 不经面板谱系。

## §7 数字标签
§1 全部 **VERIFIED**(2026-09-11 于 pod2 逐文件 `ls`/`du` 核实, BUILD.json 自检值直读)。§2 的缺陷编号引自错题集与 v4 文档 ⇒ **INFERRED**(未逐条复跑)。§3/§4/§5 逐字引自 `judge_v4.py` 与 `RESULT_v4_chain_retrain_quantify_2026-09-09.md` ⇒ 对本轮为 **INFERRED**(未独立复跑判官)。
