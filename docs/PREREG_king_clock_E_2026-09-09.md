# PREREG · E-0909-F king 特征时钟对齐生产(窗止于 E 而非 E−1)+ 标签窗 [E+1, E+48]

> **创建:** 2026-09-09 16:0xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 判据冻结(数字未出) | **作废条件:** 生产 `shadow_loop_v3.py` 特征算子改动, 或缓存时钟定义改动 | **分支:** review/b0a573a1-pipeline(研究仓); 复审 b0a573a1 P1-CONTRACT 的收口件

## §1 事实(受据: 复审 `codex_v4_pipeline_review_2026-09-09/features/REVIEW.md` §4 + 我方读码)

- 缓存行 ts = 5 分钟 bar 的**收盘**边界(复审 9 根 BTC 官方 bar 9/9 位等)。行 E = 收盘于锚时刻 E 的那根 bar。
- **生产 king**(`shadow_loop_v3.py` L356–358): `seg = CDf[max(ai+1−w,0) : ai+1]` ⇒ 窗 **[E−w+1, E]**, 含行 E; float32 归约; 成员统计同窗。
- **离线 king**(`pod_fea_ext_clamp.py` L48–58): `CS[E] − CS[max(E−w,0)]`(CS 前置零行)⇒ 窗 **[E−w, E−1]**, 不含行 E; float64 归约; 存 float16。成员统计 `[E−2016, E−1]`。标签 `y4 = CS[E+48] − CS[E]` = 行 **[E, E+47]**(含锚前那根 bar, 缺锚后最后一根)。
- **DL 侧无此偏差**: `pod_dlw_features_ext.py` / 生产 `fea171/dlw_features.py` 同源, `hi = E+1`(窗 [E−w+1, E]); 目标 `pod_dlw_targets_*.py` 行 **[E+1, E+48]**(结构断言 min_target_row_offset=+1); fea89 构建器 `hi = E+1` 同。回放记账 y4 取自 dlw y4s([E+1,E+48]), 不受影响。
- 复审实测(固定同成员三锚, 80 列, float16 计): 现 live vs 离线 4,731 / 14,666 / 15,850 格不等; live 退一 bar 后 2 / 10 / 15; 再统一 float64 后 0。
- ⇒ 缺陷范围 = **king 腿一根 bar 的训练/服务偏差 + king 标签窗早一根 bar**; 不是收益前视泄漏(两侧都未读 E 之后的 bar)。

## §2 干预(单变量: 时钟; 数值口径不动)

`pod_fea_ext_e.py` = `pod_fea_ext_clamp.py` 逐字, 只改:
1. 所有窗口统计与成员统计的半开上界 `hi = E + 1`(`s_[hi] − s_[max(hi−w,0)]`), 与生产同窗 [E−w+1, E];
2. 标签 `y4 = CS[E+49] − CS[E+1]` = 行 [E+1, E+48], 与 DL/记账同窗; 轴条件 `E + 49 ≤ TT`;
3. 其余逐字(float64 累积、float16 存储、秩、fund 两列取自面板行 E、clamp ≥0、NTOP 400、cov≥0.95、vol≥1e−4)。
不改生产端(生产改动 = 部署裁定, 归用户)。

## §3 门(每步一门; 先冻结再看数)

- **G1 平价门**(`v4e_gate_parity.py`): 锚 = 复审三锚(2022-01-08 00Z / 2025-04-05 04Z / 2026-08-20 00Z)+ 预定三锚(2023-06-01 00Z / 2024-11-15 08Z / 2025-12-01 16Z); 生产算子 = 从 `prod_shadow_loop_v3_readonly.py`(sha 与 `~/wide_shadow/shadow_loop_v3.py` 相同, 写入收据)AST 抽出的纯 `wstat`, float32, 同缓存同成员(取新 meta 成员); 80 列(40 值 + 40 秩)float16 位比较。
  - (a) 新构建器存档 vs 生产算子: 不等格 ≤ **0.1%**(复审残差 2/10/15 ≈0.02–0.05% 系 float32/64 归约差); 且生产算子改用 float64 归约后 vs 新存档 **0 格**不等。
  - (b) 阳性对照: 旧构建器存档(wide_fea_v4)vs 生产算子 在同三锚必须 **≥1,000 格**不等(门看得见缺陷)。
  - (c) 轴: 新 meta E_ts ⊆ 旧 meta E_ts ∪ {尾锚差 ≤1}; 成员变化只允许来自成员窗后移一 bar(报数, 不设阈)。
  - 任一 (a)/(b) 不满足 ⇒ 停, 不进 G2。
- **G2 导出门**: `pod_export_bundle_v4.py` 逐字, env 逐字同 AMD2 run2(`EXPORT_PANEL=v3splice EMA_STATE_JSON=canoncont BUNDLE_BASE=slow_scorer_v4base.json`), 仅换 BUNDLE_FEA/META/OUT/TAR; RUNBOOK 门②③ + 守卫带 [2.27, 2.57] 原样; 守卫红先复现 v4 已发表 2.30 再报。
- **G3 书层**: 臂 **A1e** = king v4e(pinned 预测对齐 dev_v4 轴)+ F10 v4 RAW(s42/s2027, 不重训 DL); 判官 `judge_v4.py` 冻结 §4 原样, 新增对照 **A1e−A1**(纯时钟效应)与 **A1e−A0**; 冻结窗主判, 扩展窗次级, 双种子双席位; 读法 (A)/(B)/(C), (C) 只写「未检出差异」。
- **G4 量化门(只报不判)**: v4 booster 对同一锚同成员的 float16 往返特征 vs float32 直送特征的预测 Spearman(逐锚中位数)与 IC 差; 用于决定生产是否需要「送 booster 前 float16 往返」(生产改动, 归用户)。

## §4 不主张

- 不主张收益提升; 这是训练/服务合同纠正。A1e−A1 若 (C) ⇒ 「在本合同与窗内未检出差异」, 纠正仍成立(平价门是它的存在条件, 不是收益)。
- DL 腿 legs 文件对新锚用 king v4e 预测的影响(6 锚)本轮不重训 DL; 若换装 king v4e 需按 RUNBOOK §v4 全链重跑。
- 生产 float32 归约与送 booster 前的量化差异本轮只量化不改生产。
