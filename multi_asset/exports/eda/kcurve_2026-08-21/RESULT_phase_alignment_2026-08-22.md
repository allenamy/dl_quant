> **创建:** 2026-08-22 0x:xxZ | **Session:** 6737834a-PH | **状态:** 【C 段待 jpline 装置回填】A/B 已定 | **作废条件:** 主线对相位裁定落地(重跑受影响装置或在 STATE 标注相位)由新日期文件取代并互链; STATE.md §3 永远优先

# 相位对齐审计(PH)· 在役离线回放族(9821 锚)的决策时刻 vs 实盘

**一句话:** 【待 C 回填】

---

## 0. 白话三句

【待 C 回填】

---

## 1. 装置与收据(全部可重跑; 脚本入 `devices_2026-08-22/`, 结果入 `devices_2026-08-22/results/`; SHA 见 `SHA256SUMS_PH`)

| 件 | 路径 | 说明 |
|---|---|---|
| 本机装置(A 事实表 + B 实盘量化 + 合并 C) | `phase_alignment_audit.py` | 只读 `~/dl_quant_live`(pilot_log 08-05→08-22, `state/panel_cache/klines_1h.npz`), 写 `results/phase_alignment_audit_2026-08-22.json` |
| 服务器装置(C 相位修正回放) | `phase_alignment_replay_jp.py` @jpline `probe_artifacts/` | GPU 推理 king/s2 五折 OOS 于【实盘相位的行】(行标 hour%4==3)+ 在役书两相位回放; 判据冻结在脚本头; 输出 `probe_artifacts/phase_alignment_jp_2026-08-22.json`(已拷回 `results/`)+ `ph_preds_2026-08-22.npz` / `ph_series_2026-08-22.npz`(服务器单副本) |
| regime/钟点附读 | `phase_alignment_regime_jp.py` @jpline | 最坏五分位(日 BTC 绝对波动 / 日市场方向)、逐名义钟点、2026 单年 CI; 输出 `results/phase_alignment_regime_2026-08-22.json` |

**收据(脚本断言)**: 【待 C 回填: G1 逐折 max|Δ| / G2 net_S0/S1 maxabs / Y4=ΣY1 收据】

---

## 2. A · 事实对齐表(每格从生产代码逐位读出, 带 file:line)

| 项 | 事实 | 证据 |
|---|---|---|
| 面板行标 T 的含义 | **T = 1h K 线 open_time**。行含 bar [T, T+1h) 的 OHLCV(`CLOSE[T]` = T+1h 时刻价格 ⇒ 价格类特征截至 **T+1h**); funding 取最后一次结算 **fts ≤ T**(比价格旧 1h) | 训练: `multi_asset/data/build_wide_panel.py:41-51`(grid=openTime_ms), `:91`(searchsorted side=right−1); 实盘: `signal/fapi_source.py:188`(open_ms), `signal/funding_panel.py:176`(同式), `signal/live_panel.py` `build_live_panel` 传 `until_ms=ts[-1]` |
| 离线 Y4[T] 的窗口 | **Y4[T] = log CLOSE[T+4 行]/CLOSE[T 行] = 价格 (T+1h)→(T+5h)**; 回放面板上 Y4 = Σ_{k=0..3} Y1[T+k] 逐位成立(收据见 §1) | `multi_asset/data/build_wide_dl.py:150-151` `Y[:T-H] = logc[H:] − logc[:-H]`; `data/build_yr168.py:36` 同式; W2b 用 1h K 线独立复算相关 0.99999999996 |
| CL4 / 离线预测所在行 | CL4 = 行索引%4==0 & member & finite Y4, 网格起点 2021-01-01 00:00Z ⇒ **CL4 行 = 行标 00/04/08/12/16/20Z**; `king/s2_pred_newgen.npz` 只在这些行有限(king 1642×6 / s2 1636-1638×6 行, 实测) | `build_wide_dl.py:154-157`; jpline 实测(本会话) |
| ⇒ 离线族的决策时刻 | 行标 T∈{00,04,…,20}Z 的预测 + Y4[T]=[T+1h,T+5h] ⇒ **决策 τ = T+1h = 01/05/09/13/17/21Z**, 持仓窗 [τ, τ+4h] | `engine/replay_fullhist._all_anchors`(CL4 行), `w2_live_replay.py` / `cond_stop_tail.py`(`src.Y4[ti]`) |
| 实盘名义锚 N 用哪一行 | **T = N−1h**: `anchor = len(ts)−1`, `ts[-1] = last_closed = floor(now/1h)−1h`, fapi klines `endTime = closed_end−1` 排除成形 bar ⇒ 行 [N−1h, N) 收于 N; `preds.anchor_ts_ms = ts[-1]` | `signal/compute_preds.py:209,348`; `signal/live_panel.py:115-116`; `signal/fapi_source.py:177-182`; 实测 `preds_latest.json`(08-22 00:00:59Z 计算)`anchor_ts_ms = 2026-08-21 23:00Z`; 记忆 `king_cadence_8h_live`: 16:00Z 锚携带 15:00Z 行 |
| 实盘行 T=N−1h 的内容 | 价格截至 **N**(与离线行 T 的"截至 T+1h"同构), funding 截至 **N−1h**(⇒ 在名义 00/08/16Z 不含 N 时刻刚结算的那笔; 训练行 T=00/08/16 则含 T 时刻的结算 —— funding 通道在实盘刷新锚上比训练同钟行旧一个结算, 4h 结算币每锚如此) | 同上 `funding_panel.py:176` + `until_ms=ts[-1]` |
| 实盘持仓窗 | launchd 每 4h 整点(UTC 00/04/…/20)启动; phase_A 在 **N+0.6~1.9 min**(实测均 1.12)捕获锚价并挂 maker 单, k 窗 900s, 补单/读回 **N+15.8~19.7 min**(实测均 17.2); 下次锚同样节律 ⇒ 持仓 ≈ **[N+1~17min, N+4h+1~17min] ≈ [N, N+4h]** | `~/Library/LaunchAgents/com.dlquant.live.anchor.plist`; `scheduler/run_anchor.py:280-309`; B 段实测偏移(`results/…json` `offsets_min`) |
| 实盘用的行对应的 Y4 | 实盘用行 T=N−1h ⇒ **Y4[N−1h] = 价格 N→N+4h = 实盘窗 ✓(自洽)**; 离线族用行 T=N ⇒ **Y4[N] = N+1h→N+5h ≠ 实盘窗** | 上两行合成 |
| king 8h 相位键 | 实盘: 名义锚 hour%8==0 ⇒ **名义 00/08/16Z 刷新 = 行标 23/07/15Z**; 离线族: `ti%8==0` ⇒ **行标 00/08/16Z = 决策 01/09/17Z** ⇒ 两者相差同一个 1h 相位(离线的"相位 0"实为实盘的"名义 01/09/17Z") | `compute_preds.nominal_anchor_epoch`/`cadence_decision`; `w2_live_replay.py` L45-50 |
| (旁注, 非本任务)s2/funding 刷新 | 实盘 `compute_preds` **每锚重算** s2 与 funding 腿(只有 king 有 hold); 离线族 s2 `ti%24==0` 持 24h、funding `ti%8==0` 持 8h | `signal/compute_preds.py`(仅 `apply_king_cadence`); `w2_live_replay.py` L45-50 —— 记录在案, 不在本任务裁 |

**A 结论**: 两套各自自洽(特征截至 τ, 收益窗 [τ, τ+4h]), **差别只在 τ 的钟点**: 离线族 τ∈{01,05,09,13,17,21}Z, 实盘 τ∈{00,04,08,12,16,20}Z。W2b 发现 (a) **成立**; 后果大小见 B/C。

---

## 3. B · 相位效应的实盘量化(2026-08-05→08-21, 实盘日志只读)

**做法**: 每锚取【场所持仓读回】向量(`position_readback`, `fapi/v3/account@post_anchor`, ≈N+17 min; 100 锚, 去掉 1h K 线缓存末端未覆盖的 1 锚 ⇒ 99; 另给去掉事故日 08-21 的 94 锚为主读), 用实盘仓 1h K 线缓存算同一向量在 (i) 离线族窗 [N+1h, N+5h] (ii) 实盘名义窗 [N, N+4h] (iii) 实盘实测窗 [锚捕获 mid → 下一锚捕获 mid] 下的毛盈亏, 与权益逐锚变化(`daily_nav.nav` 相邻行差, 扣出入金; "毛当量" 再扣 COMMISSION+FUNDING_FEE)比。

| 读数(94 锚, 去 08-21) | (i) 离线窗 | (ii) 实盘 1h 窗 | (iii) 实盘 mid 窗 | 真值 Δnav 毛当量 |
|---|---|---|---|---|
| 期内合计 USDT | **−87.6** | **−185.7** | −192.3 | **−201.6**(扣出入金 −193.4) |
| 均值 bps/锚(÷持仓 gross) | +1.15 | +0.37 | +0.48 | −0.32 |
| 与真值 ρ | **0.718** | **0.959** | 0.951 | — |
| 回归斜率 / MAE(USDT) | 0.79 / 15.9 | 0.91 / 7.7 | 0.91 / 8.3 | — |
| (i)−(ii) 逐锚差 | 均 +0.78 bps, **sd 16.6 bps/锚**(= sd(ii) 的 **0.88×**), 均|差| 12.7 bps, p90 23.8, 最大 56.7 | | corr(i,ii) = **0.68** | |

全部 99 锚(含事故日): ρ(i)=0.814 / ρ(ii)=0.887 / ρ(iii)=0.879, corr(i,ii)=0.66, sd 比 0.80(事故日的平仓使三者与 Δnav 都变差, 方向不变)。

**B 结论**: 实盘书的盈亏是 [N, N+4h] 窗(ρ 0.96, 斜率 0.91, 合计 −186 vs 真值 −194/−202), **不是**离线族的 [N+1h, N+5h] 窗(ρ 0.72, 合计 −88); 同一本书错 1h 相位, 逐锚盈亏相关只有 0.68, 差的 sd 与盈亏本身同量级。⇒ **离线族≠实盘相位是事实, 且不是小量**(对单本书的逐锚记账); 对【全史策略统计量】的影响见 C。

---

## 4. C · 离线族在实盘相位上重算(jpline, 2022-01→2026-06)

【待回填】

---

## 5. D · 四问与三选一结论

【待回填】
