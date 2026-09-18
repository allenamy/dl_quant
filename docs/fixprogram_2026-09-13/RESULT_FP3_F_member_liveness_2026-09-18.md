# FP3 F 结果: 判活规则从普查变成入链资格门(MEMBER_LIVENESS APPLIED)— 2026-09-18

> **创建:** 2026-09-18 09:3xZ | **Session:** b9646a9e(主研究员) | **状态:** 已入合同并接线(用户字 2026-09-18「按最佳建议来」); 十月正跑前未使用过 | **作废条件:** 缓存通道定义变更; 复审否决规则边界或执行方式
> **门:** `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/v4_gate_member_liveness.py` sha256 `6c6b9791f0f1c458…` · **构建侧:** `v4_member_mask_liveness.py` sha256 `0704cde5132ade23…` · **测试:** `tests_member_liveness.py` **29/29 ALL PASS** · **合同:** `ELIGIBILITY_CONTRACT.json` `gates.MEMBER_LIVENESS`(前身 PROPOSED6 留在 `proposed_gates_history`, 冻结前身 `ELIGIBILITY_CONTRACT.r3_c47dd088.json`)

## 1. 规则(合同原文的中文对照)
名 s 是锚 E 的成员, **当且仅当** 在 E 所在缓存行往前数 288 行(即 (E−24h, E])里至少有**一根真实 5 分钟 bar**: 该格**不在补洞清单**里, 且 `log_qv`(缓存通道 3)**有限**(既非 NaN 也非 ±inf)。
**边界(独立复审第七轮已接受)**: 这是**数据活性**, 不是交易所资格真值 —— 零成交但有真实 bar 的名通过; 刚停牌不到 24 小时的名也通过。它不替代停牌即时剔除或退市结算规则。

## 2. 为什么普查器不能当门(独立复审第十一轮 C3, 全部成立)
| 缺陷 | 普查器 `fx_member_liveness.py` 实际行为 | 门的行为 |
|---|---|---|
| finite 规则 | `filled \| np.isnan(...)` ⇒ **+inf 被当成有效数据** | `~np.isfinite` ⇒ ±inf 与 NaN 同样不是真实 bar |
| 缺锚 | `continue`, 空统计仍 rc 0 | **拒测**: 「E_ts 不在缓存时间轴上」写进 refusals, PASS=false |
| 死名 | 只计数, 不拒绝 | dead-but-member > 0 ⇒ **PASS=false rc 3** |
| 轴校验 | 不验 ts 严格递增 / 洞表同缓存 / 成员索引 dtype 与范围 | 五项逐个拒测(未排序轴的反例被挡住) |
| 覆盖 | 只看 king 成员, DL targets 只借符号轴 | **三端各自核**: king meta / DL targets / 出货 bundle 的 `symbols_live` |
| 判词 | 无 PASS/收据合同 | 走 `v4_gate_common.finalize`: gate 名、自身 sha、四个输入 sha 全绑 |

七个复审探针(all_nan / one_zero / one_inf / E−23h55 / E−24h / 未排序未来行 / 缺锚)在测试里逐个复现, **绿基线先断言**。

## 3. 真实数据(pod2, 09-18 09:2xZ)
门跑在现役 FP2-8 构建上(掩码 = 可交易 W24H), 38 秒:

| 成员集 | 锚 | 成员格 | 死名格 | 名数 | 2022 | 2026 |
|---|---|---|---|---|---|---|
| `wide_fea_v4_meta`(king) | 10,212 | 2,751,058 | 5,726 | 135 | 967 | 4,759 |
| `dlw_v4raw_targets`(DL) | 10,212 | 2,751,058 | 5,726 | 135 | 967 | 4,759 |

**判词 FAIL**。**计数更正(复审第十二轮)**: 967 + 4,759 = **5,726 是每一端各自的数**; 收据里的 11,452 是两端检查之和, **不是 11,452 个独立事件**。这**独立复算**了普查收据的 0.314% / 0.816%(复审说没被独立重算的那两个数), 且是用不同装置、finite 规则得到的; 同时证明**可交易 W24H 掩码不蕴含判活** —— 现役 FP2-8 构建按新门不合格。

构建侧掩码(可交易 ∧ 判活)已产出: `masks/member_mask_tradable_AND_live_W24H_cachegrid.npz` sha256 `9b59678b4529246c…`, 10,225 锚 × 829 名, 其中**15,430 格是可交易掩码保留而判活移除的** —— 这是**全掩码格点**上的数(10,225 锚 × 829 名), 不是 15,430 个已用训练样本。

## 4. 接线(改码, 不是声明)
- `chain_v4_monthly.sh` **gates 阶段**: `run_gate` + `require_gate`(gate 名/源 sha/四个输入 sha 全验), 失败 `FAIL_gates_liveness_rc_*`;
- **export 阶段**: 同一门带 `BUNDLE_CONFIG=$BUNDLE_OUT/config.json` 再跑一次, 核出货 `symbols_live`;
- **前置**: king / legs / mwf / refit / arms / member_rule / decision 七个阶段的 `prereq_receipt`;
- **preflight**: 批准位从 3 个门变 4 个门(实测 `approvals=4/4`);
- `v4_gate_common.REQUIRED_INPUTS['MEMBER_LIVENESS']` = cache / hole_cells / wide_fea_v4_meta / dlw_v4raw_targets(`tests_pipeline_gates.py` 的地板钉已同步)。

## 5. 没做 / 边界
- 十月构建**还没有**用判活掩码重跑(需要重跑两个构建器, 属十月链);
- 门不验证「交易所此刻可交易」, 也不做停牌即时剔除;
- 现役九月 FP2-8 产物**保持原样**: 新门是十月链的资格门, 不回改已出的九月收据(复审第七轮 K3 口径);
- 首个写盘的门源码 `65fbd039…` 调了 numpy 私有 API `_read_array_header`(numpy ≥ 2 无此名), 真实缓存必崩 —— 被测试绿基线在任何使用前抓住, 未写过任何收据, 已作为 `superseded_source_sha256` 登记。
