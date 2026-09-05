> **创建:** 2026-09-05 01:0xZ(本地 09:0x +08) | **Session:** b9646a9e | **状态:** 预注册(门冻结, 数字未看) | **用户字:** 09-05 "直接利用真实可靠的源码在pod构建jpline一样的仪表来验证之前回测指标偏差的问题,包括0821版本,这次必要要确保逻辑无误,无任何泄漏,无任何目标简单对数分歧" | **盘点受据:** scratch `review_caliber/jpline_lineage_2026-09-05.md`(481 行, 全部 git-tracked 脚本 文件:行) | **作废条件:** 任一门在看数字后被改; 下载超过 4 req/s 或落入锚窗; 触碰实盘目录

# PREREG · 第二仪器从源码重建(pod2 复现 08-21 jpline 仪表)

## §0 原则
1. **只用 git-tracked 源码**(路径见 §1), 复制到 pod2 `/workspace/review_scratch/jpline_rebuild/`; 任何补丁只允许改输出路径/输入路径/限速, 以 diff 入库并在产物 config 自报。
2. **数据从原始来源重拉**: data.binance.vision 月度/日度 5m K 线 2020-01 → 2026-08-16(829 符号, `panel_symbols_wide.txt`); 限速 **≤4 req/s**(共享节拍器), **锚窗 [N−5min, N+30min](N ∈ 00/04/08/12/16/20Z)内暂停**; funding zip 已在 pod(`/workspace/wide_multisrc/funding/`, 2019-09 起含 interval 列), 不重拉。
3. 实盘书零接触; 不写 `/workspace/data/`, 不写 `/workspace/shadow_bundle_v3/`; jpline 不依赖。
4. 每一步输出 sha256 + 逐字命令进 `logs/commands.txt`; 门的 PASS/FAIL 由脚本打印, 不由人读。

## §1 步骤(逐字脚本, 均在仓内)
| 序 | 脚本 | 参数 | 产物 |
|---|---|---|---|
| 1 | `runpod_scripts/workspace_mirror/pod_hist_dl.py` + `pod_dl_klines.py`(合并为限速版 `dl_klines_paced.py`, 只改线程数/节拍/月份集/日度尾巴) | 2020-01..2026-07 月度 + 2026-08-01..16 日度 | `jpline_rebuild/klines5m/<S>/…zip`(404 哨兵幂等) |
| 2 | `retrain_2026-09/pod_build_wide_ext.py` | `EXT_START=2020-01-01 EXT_END=2026-08-16 EXT_OUT=jpline_rebuild/data/dlnative_5m_wide829_f16_hist.npz` | 5m 缓存(ch0 = clip(pct_change, ±0.3) f16) |
| 3 | `retrain_2026-09/pod_panel_ext.py` | `CACHE_IN=<2> PANEL_OUT=jpline_rebuild/data/wide_panel_4h_hist_v2_rebuilt.npz`(L172 自检读 `/workspace/data/wide_panel_4h_v1.npz`, 只读) | 4h 面板 |
| 4 | `kcurve_2026-08-15/devices_2026-08-21/pod_fea_wide_hist.py` | `CACHE_IN=<2> PANEL_IN=<3> FEA_OUT=… META_OUT=…` | 82 列特征 + meta |
| 5 | `devices_2026-08-21/pod_slow_hist_folds.py`(输出路径改到 rebuild 目录) | 折 YV∈{2022..2026}, `tr = YRA < YV`, 无 embargo(08-21 原样) | `slow_pred_hist_oos_rebuilt.npy` |
| 6 | `devices_2026-08-21/pod_stop_arms_v3.py`(输出路径改) | `TAG=histv2` 输入 = 3/4/5 | `nets_histv2_-30_2_42.npy`, `nets_histv2_0_0_0.npy` |
| 7 | `retrain_2026-09/pod_dlw_targets_ext.py` | 缓存 = 2, 面板 = 3 | `dlw_targets_hist.npz`(y4s, y4old) |
| 8 | `review_caliber_wf/combo_recheck/w10_universe_recheck.py`(dev 布局同 rolling_king/setup_dev.sh, **REF_SKIP 不设**, 参照 = 6 的产物) | 见 §2 G2/G5 | series npz |

## §2 门(冻结)
- **G0 输入身份:** `/workspace/data/wide_panel_4h_v1.npz` sha256 前 16 = `f14bc33d78b24929`(= 08-21 jpline `wide_panel_4h_hist_v2.npz`); 仓内参照 `combo_recheck/nets_histv2_d30_pergross_ts_0821.npy` 形状 (9941,2); 每个被移植脚本 sha256 与 git HEAD 一致(打印)。
- **G1 面板逐位:** 步骤 3 产物 vs `wide_panel_4h_v1.npz`: 每个数组 NaN 位置相同且有限值 array_equal ⇒ PASS。否则按列×年份给出不等格数与最大差, 并分类(数据源修订 / 代码路径 / 浮点不确定性), 不得手工"修正"。**G1b:** 缓存 2022+ 段 vs `/workspace/data/dlnative_5m_wide829_f16_ext.npz` 共同 (ts,symbol) 逐位, 报不等比例(信息, 不设阈)。
- **G2 序列复现:** (a) 步骤 6 两个 nets 文件 vs `/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_*.npy`(若为真件而非 144 字节桩)逐位; (b) 步骤 8 三腿臂(`LEGS=111 PHI=0 WRULE=msharpe LOOK=900 CAL=log SLOW_NPY=<5>`)的 `net/gross_total` vs 仓内 9941 行参照: ts 集合相同且 max|Δ| ≤ 1e-6 bps ⇒ PASS; (c) 装置内 nets_histv2 平价门(L325-334)在 `CAL=log` 下必须 PASS、在 `CAL=simple` 下必须 FAIL(判定 E-0904-F 账本句"pod 原始回放同法"的真伪)。
- **G3 口径身份:** (a) 静态: `pod_stop_arms_v3.py` / `pod_slow_hist_folds.py` / `pod_fea_wide_hist.py` / `pod_panel_ext.py` 中对收益的 expm1/log1p/log 调用数 = 0(量能列除外, 逐行列出); (b) 数值: 面板 `Y4` == Σ_{E..E+47} ret5(全格逐位); `dlw_targets_hist.y4s` vs 原始 zip 收盘价 `c_{N+4h}/c_N − 1`: ≥1000 抽样锚(≥300 在 2020–21)max|Δ| ≤ 2e-5 ⇒ PASS; 同时报 Σ简单 vs Π(1+r)−1 的腿层差(信息)。
- **G4 泄漏电池(重建 king):** (i) 逐折 CAUSALITY ASSERT `max(train E_ts)+48*300 ≤ min(test E_ts)` 且 train∩test=∅, 5/5 True; (ii) 折外泄出: 拼接文件里每折模型只在自己的测试年有值, 2022 前全 NaN; (iii) shuffle-future 零检验: 年内置换标签重训(3 种子 × 5 折), 折外 |IC| < 2·SE 全部成立; (iv) 偏移谱 corr(pred_E, y4_{E+k}) k∈[−6,+6]: 峰在 k=0 且 max|corr(k∈[+1,+3])| < corr(0); (v) embargo 不变性: 2024/2025 折加 60 锚 embargo 重训, |ΔIC| < 0.002; (vi) 特征窗: 从缓存重算 3 个特征于 100 个锚, 最大使用行 == E−1(逐位)。任一失败 ⇒ 该 king 不得进入 G5, 只报失败项。
- **G5 两仪器分离(面板固定 = 重建 hist_v2, 只换 king):** 装置 = 步骤 8; king ∈ {hist OOS(重建, 2020 起训练), pinned(在役, 2022 起)}; 形态 F1 = 08-21 三腿 `LEGS=111 PHI=0` 动态席位; F2 = 在役固定席位 `LEGS=101 PHI=0.45 W3FIX=0.21,0,0.79 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero`; F3 = F2 去 W3FIX(动态); 口径 CAL=log(raw Σ简单)与 prod(y4s 替换, 同 rolling_king dev_alt 法); F2/F3 双种子 42/2027。输出: 逐年表(2022–2026, 负年份显式, Sharpe, maxDD, 最差月, σ_fund 三分位)+ 配对 Δ(hist − pinned)逐年, UTC 日块 bootstrap 2000×, 种子 20260905。**本轴只诊断, 不做采纳判决**(king 训练起点若要上线另立预注册)。
- **G6 报表:** `docs/RESULT_second_instrument_rebuild_2026-09-05.md`, 每个数字带 [第二仪器 pod2 从源码重建] 标签与 file:line/命令收据; 单位链脚本打印。

## §3 预期(数字前写下, 供证伪)
G1 大概率逐位(CDN 历史数据不修订; 同代码同 f16 路径); G2(b) 逐位或 ≤1e-6; G2(c) log PASS/simple FAIL; G4 全过; G5 F1 复现 08-21 逐年(2024 +0.585/2025 +1.471/2026 +2.317 每 gross), F2 hist king 的 2024/2025 高于 pinned、2026 相同量级。若 G1 不逐位, 先分类再往下走, 不得改门。
