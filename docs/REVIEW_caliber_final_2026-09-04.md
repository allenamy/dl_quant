# REVIEW · 宽书口径全链审计终稿(综合稿)

> **创建:** 2026-09-04 | **Session:** b9646a9e(综合写手; 证据来自 6 个 tracer + 15 个 refuter 投票) | **终稿:** 2026-09-05(草稿 + critic 审查 + 6 个缺口补证 G1–G6 整合; 证据链新增 1 critic + 6 gap-filler) | **状态:** 终稿, 待用户裁定 | **作废条件:** jpline 恢复后对 §7 单仪器条目做第二仪器复核, 任一条目翻转即重写对应小节; §9 开口条目任一关闭后更新对应小节

## 0. 读法与证据代号

- 本稿只使用 tracer/refuter JSON 里的数字; 每个数字带来源。**未被任何人复现的数字, 本稿明说"无人核验"。**
- 结论标签: **VERIFIED**(执行行已读 / 数据逐位核过) · **INFERRED**(由同一代码行或镜像推断, 未开原件) · **UNRESOLVED**(无人核过或两仪器矛盾未对账)。
- 证据代号(scratch 目录均在 `…/scratchpad/review_caliber/`):
  - **T-PANEL** = tracer "Pod 4h panels Y4"(`y4def/`); **T-MODEL** = tracer "MODEL TRAINING TARGETS"(`model_targets/`); **T-LIVE** = tracer "LIVE pipeline"(`live_trace/`); **T-HIST** = tracer "w10_universe.py 历史"(`hist_transform/`); **T-SEAT** = tracer "Seat-history"(`seat_caliber/`); **T-GT** = tracer "Ground truth"(`gt/`)。
  - **R-Cn.k** = 论断 Cn 的第 k 个 refuter(`refute_Cn_k/`), 例 R-C6.2 = `refute_C6_2/`。
  - **G1…G6** = 缺口补证(`gap_1/` carry 口径; `gap_2/` 2022–23 行 + AUDIT §3 对账; `gap_3/` 最差月; `gap_4/` σ_fund 三分位; `gap_5/` 阶梯/仪表盘/测试盲区; `gap_6/` 执行时点平移窗); **CRITIC** = `critic/CRITIC_NOTES.md`(残余风险原文逐字见 §10)。缺口逐条的补证结果与仍开口项见 §9。
  - **未整合**: 同会话并行的 `combo_recheck/`、`gap_live_pnl/`、`gap_units/`(其他 agent 的核查)不在本稿证据内, 本稿未读其结论; 与本稿冲突处以后续对账为准。
- 六条论断原文不在 JSON 里, §4 每条的"论断复述"是从 refuter 的 verified/refuted 段落反推出来的, 标为复述。
- **今日单仪器**: jpline 全程不可达(每个 tracer/refuter 各试一次 `ssh -o ConnectTimeout=8 jpline` → `Operation timed out`)。凡只在 pod port(`/workspace/port_w10/`)上跑出的数字, 本稿标 **[单仪器 pod]**。

**投票总表(TALLY)**: C1 3/3 存活 · C2 0/3 存活(3 票驳) · C3 1/2 存活(1 票驳) · C4 2/2 存活 · C5 0/2 存活(2 票驳) · C6 1/3 存活(2 票驳)。

---

## 1. 一句话真相

**面板 Y4 = float32( Σ_{k=E}^{E+47} r5[k] ), r5 = float16( clip( c_t/c_{t−5m} − 1 , −0.3, 0.3 ) ) 是 5 分钟简单收益, 行 E = 收盘时刻等于锚 N 的那根 K 线, 缺失 bar 记 0, 有限 bar < 46 则 NaN。它是 48 个 5 分钟简单收益的算术和, 既不是对数收益, 也不是复利简单收益 Π(1+r)−1; 窗口是价格时间 (N−5m, N+3h55m], 含锚前已收盘那根 bar, 不含持有期最后一根。** [VERIFIED: `/workspace/pod_panel_ext.py` L18-24, L57-58; `/workspace/pod_merge_cache_ext.py` L24, L27; 全锚逐位: v2ext 3,427,554/3,427,554 格 max|Δ|=0 (T-PANEL, R-C1.0, R-C1.1, R-C1.2); meta y4 3,446,599/3,446,599 (同上); 原始 K 线 zip 上 float16(simple) 匹配 100%, float16(log) 仅 26–51% (T-PANEL `ch0_base_overlap.log`; R-C1.2 `c1_rawprice.log` 2022–2026 七个样本日)]

逐组件对错(细表见 §2):

| 组件 | 口径 | 判定 |
|---|---|---|
| 面板/meta 构建器(pod_panel_ext / pod_fea_ext / splice) | Σ-simple, 窗 [E,E+47] | **口径本身无错**; 但窗口比持有期早一根 bar, 且"Σ 简单"≠交易所记账 Π(1+r)−1(名级最大差 12 bps, T-GT) |
| DL(F10/V2MAIN)目标 y4s | Π(1+r5)−1, 窗 (N,N+4h] | **正确, 即交易所记账口径**(原始 K 线复核 max\|Δ\| 1.15e-5, T-GT) |
| king LGBM 标签 | rank(Σ-simple [E,E+47]) | 无 expm1, **口径无错**; 与 DL 目标差一根 bar 窗口(Spearman 0.967) |
| bundle 出口(pod_export_bundle_v3) | 原始 y4(Σ-simple [E,E+47]) | **无错**(无 expm1) |
| 生产者(shadow_loop_v3) | Σ-simple, 窗 (E,E+4h] | **无错**(无 expm1); 与 bundle 行差一根 bar |
| 执行器(dl_quant_live) | 交易所 USDT 记账(equity/income) | **不接触面板收益, 无口径问题** |
| 执行器 σ_fund gross 阶梯(09-04 09:34Z 上线, dl_quant_live 4b8ca20) | sizing 乘子 g∈{0.5,1.0}; 状态输入 = 8h 归一费率离散(非收益) | **行为零效应**(状态文件缺失 ⇒ g=1.0; 12:24Z anchors 行 `reason: missing`; gross/NAV 1.996→1.942 无台阶); **受据双向作废**: 录取(RESULT_allweather H1)与撤回(E-0904-D)都建立在 CAL=simple + W3FIX 臂上(G5; 臂 npz 的 CAL 由 runner 推断, INFERRED) |
| regime 仪表盘 sleeve 归因 / β-α 拆分(regime_dash) | 钱口径(mid 比值 × 场所名义 + 账本 funding)/ Π(1+r5)−1 (Ta,Tb] | **无口径问题**(G5, 执行行); 不在任何电池 |
| 执行器读取时点 | `config/book.json` `"anchor_offset_min": 24`(08-27 23→24) | **STATE.md L30 / CLAUDE.md 仍写 N+23**(G6; 盘上配置 VERIFIED, 运行中取值 INFERRED) |
| 回放装置 w10_universe.py CAL=simple | expm1(Σ-simple) | **错**: 伪凸性, 每名多加 ≈ Σr²/2(2024/25/26 名级 +3.5/+5.3/+5.1 bps, R-C2.1/R-C2.2) |
| 回放装置 CAL=log | 原始 Σ-simple | 接近但**不等于**交易所记账: 书层比 Π(1+r)−1 高 0.05–0.08 bps/锚(R-C6.1/R-C6.2/R-C6.0) |
| 回放装置 carry 腿(w10 L279-280: 最后已结算费率 × 4h/iv 按比例计提) | 同书对场所实收差 −0.12 ± 0.09 bps/锚 per gross(52 窗) | **口径无错**(G1); RESULT_caliber_revalidation L64 "回放 0.77 vs 实收 1.98 ⇒ −1.2"是**书构成差 + 分母混用**, 不是口径修正(G1: 作为口径修正 REFUTED; 书构成差 +1.21/gross 为 28 锚 INFERRED) |
| 回放持仓窗 (N,N+4h] vs 执行时点(N+24 读, 成交 ≈N+25m) | 平移窗 [E+6,E+53] 书层 Δ −2~−4%(固定席位), 配对 t −0.14 | **§5 不需再打 5–10% 折**(G6; 腿级衰减装置的 5–19% 是代理书每锚全量重建的产物, 机理 INFERRED); 剩余系统性折扣 = 执行保真 −0.3 bps of gross/锚(12 锚引用值, INFERRED) |
| 09-04 08:53Z 席位种子(已撤) | expm1(Σ-simple) + 另一 king 模型 + 只到 08-15 | **错, 三重错**, 未被任何锚消费(R-C3.0/R-C3.1) |

---

## 2. 逐组件口径表

| 组件 | 定义(执行行) | 口径 | 下游变换 | 判定 | 收据 |
|---|---|---|---|---|---|
| 5m 缓存通道 0(pod `dlnative_5m_wide829_f16_ext.npz`) | `A[:,0] = np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3)`; `k['ts'] = open_time + 5min` | simple 5m, float16, 行戳=收盘 | 无 | VERIFIED | `/workspace/pod_merge_cache_ext.py` L27/L24; 原始 zip 逐位 100%(T-PANEL; R-C1.0 `c1_ch0.log` 70,254 格; R-C1.2 七样本日 287/287); base 段构建器 `pod_build_wide_ext.py` L29 同行(镜像, INFERRED, 但 2022-01-05/2022-05-12/2023-06-15/2024-11-12/2025-03-03 样本日逐位验过, R-C1.2) |
| 面板 Y4(`wide_panel_4h_v2ext.npz`) | `Y4 = (CS_r[E + 48] - CS_r[E]).astype(np.float32); Y4[y4n < 46] = np.nan`, CS 带前导零行 | Σ-simple [E,E+47] | 无 | VERIFIED(全锚逐位) | `/workspace/pod_panel_ext.py` L57-58; `panel_ext.log` SHA 5e67c055 == 文件 sha(T-PANEL) |
| meta y4(`wide_fea_v2ext_meta.npz`) | `y4 = (CS["ret5"][0][E + 48] - CS["ret5"][0][E]).astype(np.float32); y4[y4n < 46] = np.nan` | 同上 | 无 | VERIFIED(全锚逐位; == 面板 Y4 10,038 锚 max\|Δ\| 0) | `/workspace/pod_fea_ext.py` L33-34, L83 |
| `wide_panel_4h_v1.npz`(=v3splice 头) | 同 Y4 行, 由 2020 起 hist 缓存构建 | 同上 | 无 | 2022 起 VERIFIED(10,122/10,123 锚逐位; 唯一差异锚 2022-01-01 00:00 是校验缓存左边界 NaN 伪影, 公开 K 线重建证明 v1 亦为 Σ-simple); 2020-21 段 4,206 锚 **部分核验**(R-C1.1 6 名 × 6,316 格 100%; R-C1.2 6 名 × 1,092 锚 100%; 其余 INFERRED) | R-C1.0/1/2; 来源链(transcript 2026-08-21T02:01Z `PANEL_OUT=wide_panel_4h_hist_v2.npz pod_panel_ext.py` → 09-01 scp 改名)INFERRED |
| `wide_panel_4h_v3splice.npz` | `out[k] = np.concatenate([a, b[tail_idx]])` | 同上 | 无 | VERIFIED(头==v1, 尾==v2ext[ts>cut], cut=2026-08-15 00:00Z, 96 行) | `/workspace/pod_panel_splice.py` L25 |
| DL 目标 y4s(`dlw_targets.npz`) | `CS_L = cumsum(log1p(r5z))`; `lo_t = E + 1; hi_t = E + FWD + 1`; `y4s = np.expm1(CS_L[hi_t] - CS_L[lo_t])` | Π(1+r5)−1, 窗 [E+1,E+48] = (N,N+4h] | 无(进 loss 线性) | VERIFIED(3,450,715 格 max\|Δ\| 0.0, T-MODEL; == 直接乘积 max 3.6e-15) | `/workspace/pod_dlw_targets_ext.py` L75/L90/L93; `pod_f10_train_ext.py` L43/L131/L241/L288; `pod_f10_refit_ext.py` L16/L27/L77/L105; 在役权重 `f10_live_s42_np.npz` sha 351ae26b pod==Mac==STATE.md L31 |
| dlw `y4old` | `y4old = (CS_r[E + FWD] - CS_r[E])` | Σ-simple [E,E+47] | 只被诊断脚本读 | VERIFIED(== meta y4 逐位) | `/workspace/pod_dlw_targets_ext.py` L96 |
| king LGBM 标签 | `rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5`, yv = meta y4 | 横截面秩(Σ-simple [E,E+47]) | 无 | VERIFIED; booster `slow2026.txt` sha 8d79186b pod==Mac==MANIFEST; 训练 `tr = YRA < 2026` | `/workspace/pod_export_bundle_v3.py` L28, L41-45, L49-52 |
| bundle leg_returns(出口) | `LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) …)` | Σ-simple [E,E+47], bps/锚, 单位 gross 秩书 | 无(expm1 只作用 qvk 对数量) | VERIFIED(v3 bundle 1098 锚 king/rev24/fund 逐位重算 eq=1.0; fund 列须用 v3splice 面板 ⇒ EXPORT_PANEL=v3splice INFERRED) | `/workspace/pod_export_bundle_v3.py` L109, L130/L146; T-SEAT §A |
| 生产者 leg 行(shadow_loop_v3) | `ret5 = (c / pc - 1)`; `seg = CDf[pi + 1:ai + 1, :, 0]`; `y4v = np.where(fin, seg, 0).sum(0)`; L439 同上公式 | Σ-simple **(E,E+4h]** | 无 | VERIFIED(09-04 00Z 三腿逐位; rev24 106/106 锚逐位; 通道 0 与 venue 公开 K 线 48/48 逐位 ×4 名) | `/Users/haosiyu/wide_shadow/shadow_loop_v3.py` L292, L428-431, L439; T-LIVE, R-C3.0 `mac_3leg.py` |
| 席位 w3 | `shp = r.mean(1) / (r.std(1) + 1e-9); shp = max(shp,0); w3 = shp/shp.sum()`, 900 行 | 直接吃 LR | 无 | VERIFIED(重算 == 日志 @08Z/@12Z) | `shadow_loop_v3.py` L456-460; `fea171/combo_stage.py` L29-34 |
| 执行器 NAV/盈亏/止损 | `equity = totalWalletBalance + totalUnrealizedProfit`; realised = Σ income(REALIZED_PNL+COMMISSION+FUNDING_FEE); `depth = u / n`; `want = nav * tgt_lev` | venue USDT 简单算术 | 无 log/expm1 | VERIFIED(daily_nav 20260904: nav 82963.20 = 83132.79 − 169.58) | `dl_quant_live/live/binance_broker.py` L1325-1326, L1402; `scheduler/anchor_loop.py` L1063, L2362; `live/per_name_stop.py` L122-124; `config/book.json` gross_mult 2.0 |
| 执行器读取时点(external 模式) | `"anchor_offset_min": 24,`(`_timing` 注: ★ 2026-08-27 05:2xZ offset 23→24); `offset = _num("anchor_offset_min", 0.0, 120.0, DEFAULTS["anchor_offset_min"])`; `wake = nominal + float(cfg["anchor_offset_min"]) * 60.0` | 读取 N+24, 成交 ≈N+25m 起 | — | 盘上配置 VERIFIED; 运行中进程取值 INFERRED; STATE.md L30 与 CLAUDE.md "N+23" 为陈旧 | `dl_quant_live/config/book.json` L153/L163; `dl_quant_live/live/external_book.py` L132/L220; G6 |
| σ_fund gross 阶梯(执行器 sizing 乘子, 09-04 09:34Z 上线 4b8ca20; 仪表盘作业 com.hsy.sigma_ladder 已卸载) | `_g, _ginfo = _SLAD.load()`; `_sz = self._size_book(target_leverage=external["gross_mult"] * _g, leverage_source=f"external_book.gross_mult×ladder({_g})")`; `want = nav * tgt_lev`; 读端 `ALLOWED_G = (0.5, 1.0)`, 缺失/陈旧/篡改 → `return 1.0, info`; 写端 `sig_fund_bp = np.std(ff)*1e4`(8h 归一费率) | 乘子 g∈{0.5,1.0}, 状态输入 = 费率离散(非收益) | 无(不触面板收益) | VERIFIED 行为: 状态文件缺失(仅 `.reserve_20260904`), 12:24Z anchors 行 `gross_ladder={'g':1.0,'accepted':False,'reason':'missing'}`, gross/NAV 1.996/1.982/1.971/1.942 无台阶 ⇒ g=1.0 零行为效应; **受据口径: 录取(RESULT_allweather H1)与撤回(E-0904-D)都建立在 `CAL=simple W3FIX=0.21,0,0.79` 臂序列上 ⇒ 双向作废, 待 CAL=log/Π 重判**(臂 npz 在 jpline 未开, CAL 由 runner 推断 INFERRED) | `dl_quant_live/scheduler/anchor_loop.py` L1472/L1477/L1479-1480/L1482/L1063; `dl_quant_live/live/sigma_ladder.py` L10/L13/L23-24/L40-41; `multi_asset/exports/live/regime_dash/sigma_ladder.py` L7/L25-29/L33-35; `regime_dash.py` L19/L33; `retrain_2026-09/jp_allweather.py` L7/L32; `jp_universe2_runner.sh` L12-13; `jp_universe2_round2.sh` L6-7; ERROR_LEDGER L398/L408-411; `launchctl list`(com.hsy.sigma_ladder 不在列); G5 `GAP5_closure.md` §A1-A3, `receipts_computed.txt` |
| regime 仪表盘 sleeve 归因(`~/regime_dash/regime_dash.jsonl`, launchd com.hsy.regime_dash) | `r=float(m1[s_])/float(m0[s_])-1; price=n0*r; car=F1.get(s_,0.0)`(m = 执行器 `mid_at_anchor_vector`, n0 = `venue_position_notional`, F1 = Σ `funding_paid`) | 钱口径: 锚间 mid 比值简单收益 × 场所名义 + 账本 funding | 无 expm1/log1p | VERIFIED(执行行); 不在任何电池 | `multi_asset/exports/live/regime_dash/regime_dash.py` L121, L54-67, L106-112; G5 §A4 |
| β/α 拆分(`~/regime_dash/beta_alpha.jsonl`) | `def btc_ret(Ta,Tb): r=ret5(btc)[row[Ta]+1:row[Tb]+1]; r=np.where(np.isfinite(r),r,0); return float(np.expm1(np.log1p(r).sum()))`, ret5 = `rolling.npz` 通道 0 | Π(1+r5)−1, 窗 (Ta,Tb] = 交易所记账口径(BTC 4h) | 无 | VERIFIED(执行行; 通道 0 = `ret5 = (c / pc - 1)` 见生产者行); 不在任何电池 | `multi_asset/exports/live/regime_dash/beta_alpha_attrib.py` L9-11; G5 §A4 |
| 面板 carry 特征 `f_fund_now`/`f_fund_iv`(pod_panel_ext) | `pos = np.searchsorted(ft, anchor_s, side="right") - 1`; `fund_now[okp, j] = fr[pos[okp]]`; `fund_iv[okp, j] = iv_full[pos[okp]]`; `rate = float(row[-1])`(zip fundingRate 列); 间隔列缺则 `round(diff(ft)/3600)` 吸附到 {1,2,4,6,8}; anchor − ft > 12h → NaN | 锚前最后一次**已结算**费率(回看, 非预测)+ 其结算间隔 | 装置 `nan_to_num` → 0 carry | VERIFIED(31 锚 08-26→08-31 × 16,132 格 vs 生产者账本 0 差, max 4.5e-10 = float32; iv 0 差) | `retrain_2026-09/pod_panel_ext.py` L86, L109-114, L152, L155-159; pod `/workspace/panel_ext.log:10` SHA 5e67c055 == `wide_panel_4h_v2ext.npz`; G1 `panel_vs_ledger_2x2.out` L1 |
| 回放装置 carry(w10_universe) | `FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]`; `car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4`; `car_r` 于去均值 `smr`; `net = pnl − car − cbps`, `net_ex = pnl_r − car_r − cbps_r` | 按最后结算费率 4h/iv 比例计提; + = 书付 | 无 | VERIFIED; 同书(执行器 readback 名义)对场所实收 −0.12 ± 0.09 bps/锚 per gross(52 窗); 结算规则 − 比例计提 −0.02 ± 0.11 | `w10_universe.py` L59, L279-280, L305, L310/L312; G1 `carry_reconcile.out` |
| 生产者 funding 账本 + 纸面 carry(shadow_loop_v3) | `fx.get("/fapi/v1/fundingRate"…)`; `rate = float(row["fundingRate"])`; L341-342 iv 由 diff 吸附; `rn = rate * (8.0 / iv)` **只进 EMA(`f_fund_ema` 特征), 不进 carry**; `fn_v[j] = led[-1][1]; iv_v[j] = led[-1][2]`; L527-528 同装置公式 | 同装置公式(king 链单书) | 无 | VERIFIED(账本 vs 场所公开 API 17,453 共同结算 0 差; 面板 vs 账本 0 差) | `/Users/haosiyu/wide_shadow/shadow_loop_v3.py` L333, L340-349, L411, L527-528; G1 `venue_vs_ledger.out`, `venue_pull.py` + `venue_funding_rates.json`(330 名) |
| 执行器 funding(binance_funding) | `incomeType: FUNDING_FEE`; `settlement_ts = income time`, `funding_paid = income`, `funding_rate` = 最近公开费率, 名义来自自身 readback; 符号规则 `-(pos*rate)`(L218 注释) | 只在结算瞬间对当时持仓收付, 无比例计提; funding_paid < 0 = 账户付 | 无 | 执行行 VERIFIED; G1 汇报另给三项检查(`funding.jsonl` 费率 vs 账本 13,028 行 0 差; 27,660 行 sign(paid) == sign(−notional×rate) 100%, 中位 \|paid\|/\|notional×rate\| 0.9993, 结算时刻整点, 间隔 {1,4,8})——**这三项数字只见于 G1 汇报正文, `gap_1/` 内未找到落盘输出, 标 INFERRED(汇报)** | `dl_quant_live/live/binance_funding.py` L129, L188-199, L218; G1 汇报 §1 |
| 回放装置 w10_universe.py | `CAL = os.environ.get("CAL", "simple")`; `if CAL == "simple": _yy = np.expm1(_yy)`(legs)/`yv = np.expm1(yv)`(run) | CAL=simple: expm1(Σ-simple); CAL=log: 原始 Σ-simple | 后续无 exp/log | VERIFIED; 研究仓 sha 43578158 == pod `w10_universe_orig.py`; pod port 只改 L26/L93 路径 | `multi_asset/exports/research/retrain_2026-09/w10_universe.py` L17, L134-136, L276-278; R-C6.0 diff |
| 09-04 席位种子(已撤) | `yy=np.expm1(np.nan_to_num(y4[i,m],nan=0.0))`, king 来自 `slow_pred_hist_oos.npy` | expm1(Σ-simple) | — | VERIFIED 为错(rev24 行 833/950 与 expm1 重算相等, 0/950 与 Σ-simple 相等) | `retrain_2026-09/jp_build_oos_seed.py` L19/L8; R-C3.0 `pod_withdrawn.py` |
| in-role 老家族面板 `wide_dl_full.npz`(jpline) | `Y[:T - H] = (logc[H:] - logc[:-H])` | **真对数**(1h 收盘) | 08-22 SR 装置 `np.expm1(ylog)` 正确 | 定义 VERIFIED(代码); 文件今日未开(INFERRED, 由 R3 记录 maxabs 1.17e-7 vs 对数立方支持) | `multi_asset/data/build_wide_dl.py` L95/L151; `engine/panel_source.py` L11/L34; R-C5.0/R-C5.1 |

**窗口一览**(同为 Σ-simple 但不同窗, 是本审计最反复出现的混淆源):

| 量 | 行 | 价格时间 |
|---|---|---|
| 面板 Y4 / meta y4 / dlw y4old / bundle leg 行 / king 标签 | [E, E+47] | (N−5m, N+3h55m] |
| dlw y4s / F10 目标 / 生产者 y4v / 生产者 leg 行 | [E+1, E+48] | (N, N+4h] |

窗口差的量级: 名级 median |y4s − y4old| 18.8 bps(T-MODEL), Spearman 0.968; 腿级 corr 0.982–0.988, 均值差 ≈ 0.1 bps/锚(T-SEAT §J; R-C4.1)。

---

## 3. 时间线(规则何时进入、作用于哪张面板、当时对不对)

| 日期(UTC) | commit / 出处 | 装置 | 消费面板 | 该面板 y 定义 | 施加变换 | 当时对否 |
|---|---|---|---|---|---|---|
| 2026-07-11 | 03e4c8b | `multi_asset/data/build_wide_dl.py`(构建器) | 写 wide_dl.npz | log(1h 收盘) | — | 构建器 |
| 2026-07-19 | f6740f9 | `engine/panel_source.py` + `replay_fullhist.py`(in-role 9821 锚族) | wide_dl_full.npz | log | 无(pnl=Σp·Y4 对数) | 对交易所记账 **否**(08-22 SR 量化 −0.79 bps/锚) |
| 2026-08-15..21 | 236a702 / 508ed95 | `pod_kcurve.py` | 5m 缓存 ch0 | y4full = Σ-simple | 无 | 是 |
| 2026-08-20 16:15Z(git f37f660 08-21) | devices_2026-08-20 | `wide_faithful_stage1.py` | 5m 缓存 + v1 面板 | Σ-simple | L38 `Y4_own = expm1(Σ simple)` 只作对齐门; L57 书用面板原始 Y4 | 书: 是; 门量: **否**——谱系里最早的 expm1(Σ-simple) |
| 2026-08-21 | f30df5c / e45a85d / 348e720 | `pod_stop_arms*.py`, `pod_legweight_arms.py`, `pod_fea_wide_hist.py`, `pod_panel_wide_hist.py` | v2ext / hist meta+面板 | Σ-simple | 无(`yv = np.nan_to_num(y4[i, m])`) | 是(nets_histv2 来源) |
| 2026-08-22 | 26b63d6 / f1cb681 / c0bd075 | jpline W2 装置 | pod_backup hist meta | Σ-simple | 无 | 是 |
| 2026-08-22 02:28Z | 57038bd | `inrole_simple_return_rerun.py`(SR) | wide_dl_full.npz(**非** wide_dl.npz) | log | `y = ylog if ret=="log" else np.expm1(ylog)` | **是**(对真对数做 expm1) |
| 2026-08-22 | 70ef4db | `conclusion_reaudit.py` | wide_dl_full.npz | log | expm1 | 是 |
| 2026-08-22 | RESULT_inrole_simple_return L5/L162 | 文档 | — | — | 建议"离线族一律 expm1(Y4)" | 对该面板成立; **被按名字泛化** |
| 2026-08-25 04:53Z | 1150427 | `eda/w3_execcal_replay_2026-08-25.py` | pod_backup hist meta | Σ-simple | 无(L92) | 是 |
| **2026-08-25 13:35:07Z** | transcript(jpline only, 未入 git) | `w7_legweight_replay.py` ← copy of w6 + patch 插入 `CAL = os.environ.get("CAL","simple")` 和 `if CAL == "simple": yv = np.expm1(yv)` | 同上 | Σ-simple | expm1 | **否——错误变换进入宽书回放链的时刻** |
| 2026-08-25 14:47Z | transcript | `w8_blend_replay.py`(copy of w7) | 同上 | Σ-simple | expm1 | 否 |
| 2026-08-25 18:27Z / git ea84425(08-26) | | `eda/w10_ablation_replay_2026-08-25.py`(L17/L76-77/L179-180) | 同上 | Σ-simple | expm1 默认 | 否(18:47Z 的 `CAL=exec` 跑, E-0826-C, 落入 log 分支 = 原始 Σ-simple = 实际更对的口径) |
| 2026-08-26 | 0790296 | hardened w10(加 assert CAL 白名单); E-0826-C 写入 ledger L213-219 | 同上 | Σ-simple | expm1 默认 | 否; ledger 记"CAL=simple(交易所简单收益, expm1)"= 信念 |
| **2026-08-26** | **a99bfc3** | `CLAUDE.md` L28 "一律简单收益口径(expm1)" | — | — | 规则泛化 | 对 wide_dl 对数面板成立, 对 pod Σ-simple 面板 **否**(唯一改过该行的 commit, T-HIST `git log -S`) |
| 2026-08-30 | 84bfe73 | `w10_ftrim_63feb2f7193f_2026-08-30.py` | 同上 | Σ-simple | expm1 默认 | 否 |
| 2026-09-01 | 466192d(后续 40485c4/50d2164/adf6d72/c072500/35520d3 未改 CAL 行), 954c970, 59a4c1a, 3deeb4b, 92bfd91, 6bf6299 | `w10_universe.py` 及 w10_* 姊妹 | 同上 | Σ-simple | expm1 默认 | 否 |
| 2026-09-01 | be24a02 | `pod_dlw_targets_ext.py` | ext 缓存 | y4s=Π(1+r)−1 (N,N+4h]; y4old=Σ-simple | expm1(Σlog1p) | **是** |
| 2026-09-01 | be24a02 | `pod_export_bundle_v3.py` L109/L149 + 生产者 | v2ext meta / rolling.npz | Σ-simple | 无 | 是 |
| 2026-09-04 | c4a37d9 | E-0904-C "对数口径更正"(RUNBOOK §9 提议出口+生产者加 expm1) | — | 信念: meta y4 是对数 | 提议 expm1 | **否**(当日撤回) |
| 2026-09-04 08:53:24Z | `seed_revert_20260904.sh` 之前 | 席位种子换成 expm1 版(sha de0aa38b) | — | expm1(Σ-simple) | — | 否; 11:46:04Z 回滚到 172715ce(PID 58281), 期间无锚 |
| 2026-09-04 | c763361 / c15a9a2 | E-0904-F(`pod_caliber_truth.py`)、E-0904-G(`pod_panel_lineage.py`) | pod meta + dlw | Σ-simple | 仅诊断 | 是 |
| 2026-09-04 06:31:59Z(出表 06:33Z; git 7e5967f) | transcript `6737834a….jsonl` L211810/211811(G2 `transcript_L211811_armC.txt`) | `uni2_F_M7F_fx_s42` 等臂 → `AUDIT_live_vs_replay` §3 / `RESULT_allweather` §0-§1(阶梯 H1 录取候选) | jpline hist meta(止 08-15) | Σ-simple | `CAL=simple LEGS=101 … W3FIX=0.21,0,0.79`(env 逐字) | **否**(CAL=simple-stale, §5.3b) |
| 2026-09-04 09:34Z | dl_quant_live 4b8ca20 | σ_fund gross 阶梯上线(执行器 sizing 乘子; 状态文件缺失 ⇒ g=1.0) | — | 受据 = 上一行 CAL=simple 臂 | — | 行为零效应; 受据双向作废(G5; E-0904-D 撤回亦 CAL=simple, ledger L398 已标作废) |

来源: T-HIST 20 行时间线(git `log -S'expm1'`、`log -S'environ.get("CAL"'`、transcript 流式提取), R-C2.0/R-C2.1/R-C2.2 及 R-C5.0/R-C5.1 独立复核了 08-25T13:35:07Z 与 ea84425 两点。

**根因一句话**: 08-22 在对数面板上得出的"expm1 = 交易所口径"是对的; 08-25 把它按变量名 `y4` 搬到 Σ-simple 面板上, 08-26 写进 CLAUDE.md 成为通则, 之后所有 w8/w10 家族 CAL=simple 数字都带伪凸性。**08-21/22 的 W2 装置和 nets_histv2 用的是原始 y4, 未受影响**(R-C2.0/1/2 三票一致; 这一点与 ERROR_LEDGER L397 "pod 原始回放(nets_histv2)同法"矛盾, 代码收据 `pod_stop_arms_v3.py` L38/L76 胜)。

---

## 4. 六条论断的证伪投票结果

### C1(复述): 所有 pod 构建面板(v1/v2ext/v3splice Y4, meta y4)= 48 个 5 分钟简单收益之和, 逐位验证; 非对数, 非复利。
**投票 3/3 存活。** 三位 refuter 全部独立逐位复现(R-C1.0 3,427,554 格; R-C1.1 同 + 公开 K 线 2020-21 重建; R-C1.2 8,322,331 格含 NaN 模式)。
- 最强修正(非驳倒): (a) "所有 pod 构建"措辞过度——v1 是 08-21 旧 pod 实例由 2020 起 hist 缓存构建, 09-01 经 jpline→Mac→pod 中转改名, 非当前链产物(R-C1.0, transcript 2026-08-21T02:01:44Z); (b) 2020-21 段 4,206 锚只做了样本核验(R-C1.1 6,316 格; R-C1.2 1,092 锚 × 6 名, 全部 100%), 其余 INFERRED; (c) 精度措辞: 求和项是 float16 量化、±0.3 截断的简单收益(953/165,729,335 格触截断), 缺 bar 记 0, 46-47 bar 的和占 0.01-0.02%(R-C1.1 `clip_stats.log`; R-C1.2); "逐位"指 float64 累加再转 float32(float32 累加有 2 格差 1 ulp)。
- **修正后陈述**: 见 §1 第一段。附: 此前仓内"逐位"收据实为容差检验(`pod_panel_lineage.py` L25 `share<1e-6` 40 锚; E-0904-F ② "100% <1e-5" 19 锚), 本轮才是真逐位(R-C1.2)。

### C2(复述): w10_universe.py CAL=simple 对 Σ-simple y4 做 expm1; 导致 king 低估 2–3、F10 低估 2–3、fund 高估 0.3–0.9 bps/锚; CAL=log 原始 Y4 是交易所口径的无偏代理(腿级 ≈0.05 bps 内); 8 月中以来所有宽书回放数字受影响。
**投票 0/3 存活(3 票驳)。** 机制部分三票都 VERIFIED; 被驳的是四个定量/范围子句:
1. **F10 "低估 2–3"被驳**: 同窗 expm1 偏差只有 −0.34/−0.41/−1.68 bps/锚(2024/25/26; R-C2.0, R-C2.1)或 2026 −1.54±0.07(R-C2.2, 两仪器 2026 值差 0.14, 未对账); RESULT_caliber_truth L24 的 −2.25/−3.29 是 expm1(y4old, 窗 [E,E+47]) 减 y4s(窗 [E+1,E+48]), 混入了一根 bar 的窗口差 −1.20/−1.92/−1.53(R-C2.0/1)或 −1.20/−1.83/−1.48(R-C2.2), 而 CAL=log 也带这一窗口差。R-C2.2 进一步定位: F10 腿在锚前那根 bar(行 E)上的收益为 −1.07/−1.85/−1.29 bps, 单独解释了窗口差。
2. **"CAL=log 腿级 0.05 bps 内无偏"被驳**: 同窗 fund 腿 raw−Π = +0.10/+0.11/+0.27(2024on +0.146, se 0.047, t≈3.1; R-C2.1/R-C2.2); rev24 −0.02/−0.07/−0.13; 只对 king(−0.08/−0.01/+0.09)与 F10(−0.00/−0.09/+0.09)成立。名级 Σ−Π 系统性为正(+0.23~+0.73 bps, 窗内负自相关), 腿级只靠零和权重抵消。
3. **"8 月中以来所有回放"被驳**: expm1 于 2026-08-25T13:35:07Z 进入(w7→w8→w10); 08-21 的 `pod_stop_arms_v3.py` L38/L76、`pod_legweight_arms.py` L37/L85 和 08-15 `pod_kcurve.py` L54 用原始 y4——nets_histv2 未污染(三票一致)。
4. **方向遗漏(实质性)**: 腿级看是 king 低估, 但**书层 CAL=simple 是高估**: 固定席位 W3FIX=0.21,0,0.79 且持仓逐位相同(S0_W array_equal True)时, simple−log = −0.40/−0.01/+0.22/+0.84/+1.60 bps/锚(2022..2026; R-C2.0); canon LEGS=101 d30_n2_c42 net_ex +0.144/+0.307/+0.946(2024/25/26; R-C2.1); msharpe 动态席位下差距更大(S0 summary: canon net_2024on 1.11 vs 0.78, Sharpe 2.59 vs 1.93; live 1.49 vs 0.79, Sharpe 3.23 vs 1.85; R-C2.0/R-C2.2)——因 king 席位被压低, 权重流向凸性为正的 fund 腿。**列/臂标签(CRITIC)**: 本点引用的 R-C2.2 书层数字 1.49 vs 0.79 是列 `net`、臂 S0; §5 全部用列 `net_ex`、臂 d30_n2_c42, 二者不可直接并列(`critic/CRITIC_NOTES.md`)。
- **保留的部分**: king −1.03/−2.44/−3.14(2025-26 合并 −2.72 se 0.07); fund +0.30/+0.74/+0.88; rev24 −0.75/−1.53/−1.98; 名级伪项 ≈ Σr²/2(+3.54/+5.31/+5.09 vs RV/2 3.52/5.16/5.02)——三票数字一致到 0.01。
- **修正后陈述**: w10_universe.py(sha 43578158; pod port 只改路径)L135-136/L277-278 在 CAL=simple 默认下对 y4 = Σ-simple[E,E+47] 做 expm1, 名级多加 Σr²/2。腿级偏差(同窗, bps/锚 2024/25/26): king −1.03/−2.44/−3.14; rev24 −0.75/−1.53/−1.98; fund +0.30/+0.74/+0.88; F10 −0.34/−0.41/−1.5~−1.7。CAL=log 对 king/F10 在 ±0.1 内, 对 fund 高 +0.10~+0.27(t 最高 3.9), 对交易所窗 (N,N+4h] 还额外低估 F10 1.2–1.9 bps(窗口差, 非口径)。书层 CAL=simple **高估** +0.14/+0.31/+0.95(canon)至 +0.22/+0.84/+1.60(固定席位)bps/锚。范围: 2026-08-25 起的 w7/w8/w10 家族; 08-21/22 装置与 in-role 对数族不受影响。

### C3(复述): bundle 出口与生产者同口径 ⇒ 在役 king 席位 ≈0.21 合法; 08:53Z expm1 种子错; 11:46Z 回滚正确; 2026 king 行 OOS。
**投票 1/2 存活(R-C3.0 驳, R-C3.1 存)。两位在数字上完全一致, 分歧只在"机制"措辞。**
- 一致 VERIFIED: 种子错(三重: expm1 口径 833/950 rev24 行吻合; king 来自 `slow_pred_hist_oos.npy`; 行止于 08-15, 丢掉 109 条实盘行); 种子下 king 腿翻号(v3 seed 后 900: −0.74 vs +2.83 bps/锚, S/锚 −0.024 vs +0.095)⇒ w3=[0,0,1]; 换入 08:53:24Z、回滚 11:46:04Z(PID 58281 lstart 19:46:01 +08), 期间无锚(target_live 写于 08:21:09Z 与 12:20:34Z); 回滚后 cur[:-1]==pre[1:] 全腿逐位; msharpe 重算 == 日志 w3(08Z [0.1972,0.1218,0.6809]; 12Z [0.1929,0.1184,0.6887]); 2026 king 行由 `tr = YRA < 2026` booster 预测(2026 IC +0.0584 vs 样本内 2025 +0.176, R-C3.0 `pod_aug2.py`)。
- **R-C3.0 驳的部分**: (a) "同口径"过度——两者都是 Σ-simple f16 但窗差一根 bar(MT y4 匹配 [E,E+47] 41/41, [E+1,E+48] 0/41; 生产者行只匹配 [E+1,E+48]); 对席位影响 ≤0.012(2-leg king 席位 0.2246 → 0.2235 生产者窗 → 0.2359 交易所 Π 窗)。(b) **因果链前提为假**: v3 bundle 的 leg_returns.npz 对 900 行席位窗贡献 **0 行**——`ShadowState.__init__` L223-226 拼 bundle+extra, `save()` L236-239 只留最后 950 行, 所以当前文件 0-840 行逐位等于 **08-16 旧 bundle** 第 9102-9942 行(03-28→08-15), 841-949 行是实盘追加(king 用 booster 29ffaf58 至 09-01, 之后 8d79186b)。结论幸存是因为旧出口镜像 `pod_export_shadow_bundle.py` L91 与 v3 同公式且旧行逐位可重算(king max|Δ| 0.0; T-SEAT §A2)。(c) "≈0.21"两种读法: w3[0]=0.1972(08Z; 实盘史 0.1714–0.2144, R-C3.1)或 rev24 屏蔽重归一后 king/(king+fund)=0.2086/0.2246/0.2188(00Z/08Z/12Z, `combo_stage.py` L228-229, R-C3.0)。
- R-C3.1 同样指出机制误归因, 但判"数字成立故不驳"。两票不矛盾——是同一事实的不同判级。**收据方向**: 机制陈述以 R-C3.0/T-SEAT 的行来源图为准(逐位对齐), 数字以两票共同重算为准。
- **修正后陈述**: 在役席位是 900 行 msharpe 的忠实输出(重算==日志), 该 900 行 = 08-16 旧 bundle 790 行(Σ-simple [E,E+47])+ 110 条生产者行(Σ-simple (E,E+4h]), **v3 bundle 行 0 条**; 两来源同口径、差一根 bar 窗口, 席位敏感度 ≤0.012。08:53Z 种子三重错且未被消费; 11:46Z 回滚正确。2026 king 行 OOS(年内 IC 0.0584 处于 OOS 水平), 但 v3 出口有两道读 2026 结果的验收门(L80 |ic26−0.0571|≤0.006; L162 Sharpe 2.27..2.57)——fail-stop 非拟合, 属轻度选择(R-C3.1)。未核: 文件行 841-844(4 行)来源不明(R-C3.0)。**未对账(CRITIC)**: 种子"expm1 口径"的两票收据形态不同——R-C3.0 `pod_withdrawn.py` rev24 行 833/950 与 expm1 重算逐位相等; R-C3.1 `pod_f_seed_replicate.py` L29 的复制品 exact 0/950(其标签落在 `jp_build_oos_seed.py` L19 代码行上, 非逐位); 两票未互相对账(§7 #31)。

### C4(复述): 两个模型(F10/V2MAIN、king)的训练目标都没做过 expm1; king 秩标签对单调变换不变; 只有回放评估与席位历史口径受影响。
**投票 2/2 存活。**
- VERIFIED: y4s 逐位 = Π(1+r5)−1 [E+1,E+48](R-C4.0 10206 锚 max|Δ| 0.0; R-C4.1 3,450,715 格 max 1.1e-7); F10 训练/refit 脚本 grep expm1 无命中; king 标签 `rankdata(y4)`; rank(y4) ≡ rank(expm1(y4)) 10176/10176 锚(R-C4.1); V2 训练链内的席位 WL 也在简单口径(换口径测试: Σ/Π 差 0.024–0.048, expm1(Σ) 差 0.41 ⇒ 席位 [0,0,1]; R-C4.1 `wl_selfcheck_calibers.log`)。
- 最强修正: (a) "秩对单调变换不变"这一推理不适用——Σr → Π(1+r)−1 不是逐元素单调变换(路径依赖); 但数值上可忽略(同窗 Spearman 中位 0.99979, p05 0.99871, 平均 |Δrank| 0.003, |Σ−Π| 中位 1.0 bps; R-C4.0)。king 未受影响是因为训练路径没有 expm1, 不是因为秩不变性。(b) 未陈述的更大差异: king 标签窗 [E,E+47] vs DL 目标窗 [E+1,E+48]——Spearman 中位 0.967(p05 0.937, min 0.72), 平均 |Δrank| 0.047(≈16× 口径效应), 前十分位重叠 88%, |Δ| 中位 16.3 bps(R-C4.0; T-MODEL 18.8 bps)。(c) "只有…受影响"不可穷举核验: eda/ 下 53 个文件、retrain_2026-09/jp_*.py 多个装置对 y4 做 expm1(R-C4.1 抽查均为诊断装置); 更要紧的是 **在役书形态(combo/FTRIM/M1)是在受影响的回放口径上判定的**(`combo_stage.py` L3 "判据装置 = w10 LEGS=101 CAL=simple PHI=0.45")。(d) 实盘 .pt 与 `pod_f10_refit_ext.py` 的联系是一致性(recipe 字串、trained_through、np 权重相等), .pt 无 self_sha256; 08-22 walk-forward JSON self_sha256 93cc2cdf ≠ Mac `base_f10_train_pod.py` bbd4031d(R-C4.1)。
- INFERRED: V2MAIN 训练用的 10,086 条历史 WL 行来自 jpline `f3_zoo_nonfunding_leg.py`(存档 L191 `RET = (C[i1]/C[i0] - 1.0)` 真简单收益, L343-346 无 expm1), 原件未开(R-C4.0)。
- **修正后陈述**: 在役 F10 refit(sha 351ae26b, trained_through 2026-08-30 20:00Z)训练目标 = Π(1+r5)−1 (N,N+4h]; 在役 king booster(sha 8d79186b)标签 = rank(Σ-simple (N−5m,N+3h55m]); 两者均无 expm1。expm1 缺陷只在 w10 家族回放/判官装置和 09-04 08:53–11:46Z 的席位种子里。king 标签与 DL 目标差一根 bar 是窗口差异, 非口径差异, 但量级(16 bps 名级)远大于口径效应。

### C5(复述): 08-22 SR 审计跑在 wide_dl.npz(真对数 Y4)上, expm1 在那里正确; 规则按名字被搬到 pod 家族; R3 收据的容差(相关 ≥0.99 且 |Δ| 中位 <1 bps)分辨不了对数和 Σ-simple(典型差 0.7 bps)。
**投票 0/2 存活(2 票驳)。** 谱系陈述全部 VERIFIED, 被驳的是"R3 分辨不了":
1. **R3 实际记录值本身就分辨了**: maxabs_diff 1.17e-7, median |Δ| 0.00024 bps, frac<1e-6 = 1.0(987,061 格, 9,820 锚), 对手方 `w2b_build_return_cube.py` L56 `rw = np.log(c3 / cm1)` 是代码验证的对数; 而 Σ-simple 面板对对数的差在 140 在役名 2022-01→2026-06 上 median 1.38 bps, mean 2.77–2.92, p95 8.5 bps, max 0.116, 仅 2.2% 格 <1e-6(R-C5.0 9,840 锚 1,133,686 格; R-C5.1 1,962 锚 226,245 格)——差四个数量级。
2. **即使只看阈值对, 中位腿也会拦住 Σ-simple**: 1.38–1.43 bps > 1 bps; 逐年 2022 1.70 / 2023 0.93 / 2024 1.65–1.69 / 2025 1.44–1.45 / 2026 1.02–1.03(两票一致到 0.04); 只有 corr 腿(0.9999)是盲的。"典型差 0.7 bps"只在 2026-07-26→09-04 低波窗(Mac klines_1h 独立收盘: 0.77 bps)和 2023 成立。
3. 名字: SR 读的是 `engine/panel_source.py` L11 的默认 `wide_dl_full.npz`(sha 2e36dda1 = PANELS_MANIFEST L30 行), 不是 `wide_dl.npz`(那是 `build_wide_dl.py` L27-28 的默认 OUT 名)。哪个脚本写了 wide_dl_full.npz 今日不可验(R-C5.0); R-C5.1 复算 `git show efecc05` 版源码到 savez 行的 md5 = `build_wide_dl_causal.py` L58 PRESAVEZ_SHA ca023f9d, 该版 L122 同为对数行。
4. 附加发现(R-C5.0): 若把 R3 直接施于 pod 面板 vs 1h 立方, 会因窗口差一根 bar 而失败(corr 0.982, median 12.2 bps, mean 19.3)——这正是 08-22 W2b VALID2 记录的 27.5 bps"5m 来源差异"(`w2b_cube.log` L13)的主因, 非口径也非 f16。同价格窗下 Σlog1p(r5) 与 1h 对数差 0.017 bps。
5. 附加: 存档 SR 脚本 sha 00fea19e ≠ 结果 JSON 记录的 9a8c1cfd——产出 08-22 收据的字节不在仓里(判官装置寿命问题)。
- **修正后陈述**: SR 装置在 wide_dl_full.npz(对数, 由 R3/PH 记录支持, 文件今日未开)上做 expm1 是正确的; pod 家族是 Σ-simple, w10 对它做 expm1 是按名搬运的错误(08-25T13:35Z, SR 后三天)。但 R3 **确实**分辨了两种口径——它没做的只是检查 pod 家族。

### C6(复述): pod port CAL=log(原始 Y4 = Σ-simple = "正确口径")下, 在役形态 M829/T400/FTRIM=zero, 臂 d30_n2_c42 net_ex: 固定席位 0.21/0/0.79 → 2024 −0.642 / 2025 +0.284 / 2026(→08-30) +2.378 / 2024→26 +0.457(Sharpe 1.02, maxDD 2614); 动态 msharpe → +0.149/+0.359/+2.013/+0.691(Sharpe 1.88); 旧口径 +1.473(3.14)/+1.597(4.00); T3c −0.033/−0.022; M1+T400/FTRIM/T400 与 canon 差在 ±0.04 内; gross_total≈0.6–0.85; 换算 10.0% NAV/yr = 12.65%/gross = 25.3% @2×。
**投票 1/3 存活(R-C6.0、R-C6.2 驳; R-C6.1 存)。三票对所有引用数字都独立逐位复现(自跑装置 vs port 序列 array_equal True, max|Δ| 0.0); 分歧全在"正确口径"标签、gross 范围、换算配方与 2026 尾段。**
1. **"正确口径"被驳(R-C6.0, R-C6.2; R-C6.1 以 caveat 形式给出同一数字)**: Σ-simple 不是交易所记账。同装置只换 y4 为 Π(1+r)−1 (E,E+4h](= 项目自己的 y4s 定义): 固定席位 2024 −0.709 / 2025 +0.254 / 2026 +2.324 / 2024→26 +0.4065, Sharpe 0.899, maxDD 2657(R-C6.1 与 R-C6.2 逐位一致); 动态 +0.116/+0.339/+2.068/+0.685, Sharpe 1.881, maxDD 967(R-C6.2; R-C6.1 +0.6850/1.881)。R-C6.0 用同窗 [E,E+47] 的 Π: 固定 −0.7337/+0.2068/+2.3233/+0.3795, S 0.838, maxDD 2692; 动态 +0.0790/+0.2856/+1.9838/+0.6302, S 1.727, maxDD 999——三票结果不同是因窗口不同, 不矛盾。仅换窗(Σ-simple (E,E+4h]): 固定 +0.4665(S 1.036), 动态 +0.7263(S 1.970)(R-C6.1/R-C6.2)——说明锚前 bar 没有抬高, 是复利把固定席位书压低。2024 差 0.067 bps/锚 > 文档自设 0.05 作废阈值(R-C6.2)。
2. **gross 范围**: 年均 0.531(动态 2025)–0.865(canon 2026)/0.847(固定 2024); 逐锚 0.29–1.00(三票)。
3. **2026(→08-30)含 120 锚无 F10 预测**(dlw E_ts 止于 2026-08-10 20:00; F10P NaN→xz→0, 装置 L228): 2026≤08-10(n=1332)固定 +2.9107(S 5.164, maxDD 458), 动态 +2.5118(S 4.832); 08-11..08-30 段均值 ≈ −3.5 bps/锚(R-C6.0/R-C6.2, `pod_port_followup_stats.json`)。
4. **换算配方歧义(R-C6.2)**: `pod_units_table.py` L10-11 用 mean(net_ex)/mean(gross)(比值之均值); 实盘执行器按恒定 gross 定尺寸(`external_book.py` L464-465 除以 gross_in; `book.json` gross_mult 2.0), 匹配量应是 mean(net_ex/gross)。固定 2024→26: +0.5774 → 12.6%/gross(2× 25.3%) vs +0.6576 → 14.4%(2× 28.8%); 动态 2024: 5.4% vs 13.9%; 动态 2024→26: 24.4% vs 25.1%。per-gross maxDD(cumsum net_ex/gross)3155 bps vs per-NAV 2614。
5. **±0.04 只对三年均值成立**: 逐年 M1+T400 −0.057/−0.086/+0.181; FTRIM −0.044/+0.042/−0.070; T400 +0.000/−0.095/+0.001(R-C6.1/R-C6.2)。
6. **动态席位 2024 是装置伪影(INFERRED)**: slow_pred_pinned 2022–23 全 NaN ⇒ king 腿恒 0 ⇒ 进入 2024 的 900 锚 msharpe 窗全零, 早期 king 席位 0(装置 L152-172)——非 jpline 正典(yearly-OOS king 2022–26 折)(R-C6.0/R-C6.2)。
7. port 的参照平价收据无效: `nets_histv2_*.npy` 是 144 字节 stub, LEGS=101 绕过断言, 日志 "arm anchors 10038 vs ref 1"; 可复现性由 refuter 自跑逐位建立(R-C6.0)。
- **收据裁定(不按偏好)**: "Σ-simple 是否交易所口径"由 T-GT 原始 K 线恒等式判定: Π(1+r5)−1 与 c_{N+4h}/c_N−1 最大差 1.15e-5(f16 极限), Σr5 最大差 1.19e-3(140 名-锚); 代数上 qty×ΔP ≡ notional×(P1/P0−1)。故 **Π(1+r)−1 (N,N+4h] 是记账口径, Σ-simple 是有偏但小偏的代理**——C6 的数字是"装置在 CAL=log 下算出什么"的正确记录, 不是"交易所口径下的书"。
- **修正后陈述**: 见 §5 表(双口径并列)。

---

## 5. 正确口径下的完整评估

**约定**: 单位 = bps/锚, 每单位 NAV 的书(gross_total = Σ|sm|, 年均 0.53–0.85); 臂 d30_n2_c42, 列 net_ex = pnl − carry − cost(`w10_universe.py` L304-312); Sharpe = mean/std(ddof=1)·√2190; maxDD = cumsum 峰谷(`/workspace/port_w10/summarize.py` L15-18)。**全部为 [单仪器 pod]**(jpline 第二仪器不可达); 但每个数字至少两位 refuter 独立自跑装置逐位复现(R-C6.0/1/2: array_equal True)。"Σ-simple"= CAL=log 原始 meta y4(窗 (N−5m,N+3h55m]); "Π(E,E+4h]"= 只换 y4 为 Π(1+r)−1 (N,N+4h] 的同装置重跑(R-C6.1 `alt_stats.out`, R-C6.2 `run_alt.sh`)。

**net_ex 的单位(G4 从执行行读, VERIFIED)**: `pnl_r = float((smr[m] * yv).sum() * 1e4)`, `gt = float(np.abs(sm).sum())`, `net_ex = pnl_r - car_r - cbps_r` ⇒ net_ex 是每单位 NAV 的书(权重不归一, 书 gross = gross_total), per-gross = ÷ gross_total(`pod_units_table.py` L11 `per_g=m/g`); `/workspace/port_w10/summarize.py` L2 docstring 与 port `REPORT.md` §7 L197 写的"bps of gross per anchor"是信念, 与执行行不符(G3 侧注)。**本节 G1/G2/G3/G4/G6 新增数字同为 [单仪器 pod]**; 每个新增数字的装置与打印输出路径随行给出。

**年份覆盖(数据事实, gap_2 补证; 用户规则 ERROR_LEDGER L373 / memory `feedback_report_live_caliber_full_cycle` 要求逐年 2021–2026 且负年份显式)**: pod 港装置的输入在 2024 前是残缺的——king `slow_pred_pinned.npy` 逐年有限占比 2022 0.0000 / 2023 0.0000 / 2024 0.3304 / 2025 0.4681 / 2026 0.4825; F10 `f10_V2MAIN_s42.npy`(s2027 同)按 dlw 年 2022 0.0000 / 2023 0.2260 / 2024 0.3304 [VERIFIED: gap_2 `pod_gap2_stats.py` → `gap2_stats.json` coverage; 与 R-C6.2 `REPORT.md` L45/L47 一致]。装置里 king 分数 NaN → `xz` → 0(`w10_universe.py` L129-133), 故 2022–23 每条序列的 `leg_king` 逐锚恒为 0(|max| = 0.0, 五条 port 序列 + 八条 R-C6.1 alt 序列全部如此, 同上收据), 席位仍按 W3FIX 0.21 或 msharpe 规则分到一条零收益腿上 ⇒ **2022–23 的书 = 0.79×fund(2023 另混入 22.6% 覆盖率的 F10), 是 fund-only 书, 不是在役 combo 形态**。因此下面两表加入 2022/2023 行(双口径)并标注; 它们回答"在役书的 fund 腿 2022–23 会怎样", 不回答"在役 combo 2022–23 会怎样"。**实盘形态的 2024 前数字需要**: ① 年折外 king(jpline `/mnt/storage/private/work_hsy/pod_backup_2026-08-21/slow_pred_hist_oos.npy`, 装置 L86 的默认加载物; pod 上 18 处同名文件全是 → `slow_pred_pinned.npy` 的符号链接, 无一是年折外件 [VERIFIED: gap_2 coverage `slow_pred_files`]); ② F10 2022–23 的 walk-forward 折(dlw 2022 finite 0 / 2023 0.226, 今日不存在)。二者今日均不可得(jpline: `ssh -o ConnectTimeout=8 jpline` → `Operation timed out`, 本条只试一次)。**2020–2021: UNAVAILABLE**——pod 无任何 king/F10 预测覆盖该段(meta E_ts 起 2022-01-08, dlw E_ts 起 2022-01-03, king 起 2022 且全 NaN), 只有 `wide_panel_4h_v1.npz`(ts 2020-01-31 → 2026-08-15, 14,329 行)有面板而无模型分数 [VERIFIED 同上], 书回放无从构造; jpline 链上存在 2021 行(AUDIT §3 2021 −70%), 但那是 CAL=simple + jpline king 的单仪器数字(见 §5.3b), 今日不可复现。

### 5.1 固定席位 0.21/0/0.79(在役 combo 形态)

| 年 | n | Σ-simple [E,E+47](CAL=log) | Sharpe | maxDD(bps NAV) | gross 年均 | Π(1+r)−1 (E,E+4h] | Sharpe | maxDD | Σ-simple (E,E+4h](只换窗) | 旧 expm1(CAL=simple) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2020–2021 | — | **UNAVAILABLE**(无 king/F10 预测; pod 仅 v1 面板) | | | | UNAVAILABLE | | | | |
| 2022 **[king=0, F10 absent ⇒ fund-only 书, 非在役形态]** | 2010 | −0.1203 | −0.322 | 821.9 | 0.886 | −0.098 | −0.267 | 852.7 | −0.094 | −0.430 / S −1.11 / maxDD 1232.8 |
| 2023 **[king=0, F10 仅 22.6% 覆盖 ⇒ fund-only 书, 非在役形态]** | 2190 | −0.3807 | −1.203 | 1238.6 | 0.872 | −0.404 | −1.269 | 1273.8 | −0.360 | −0.284 / S −0.89 / maxDD 1158.1 |
| 2024 | 2196 | −0.6421 | −1.682 | 1814.9 | 0.847 | −0.709 | — | — | −0.633(=−0.642+0.009) | — |
| 2025 | 2190 | +0.2844 | 0.673 | 902 | 0.750 | +0.254 | — | — | +0.313 | — |
| 2026(→08-30) | 1452 | +2.3780 | 4.209 | 774 | 0.767 | +2.324 | — | — | +2.359 | — |
| 2026(≤08-10) | 1332 | +2.9107 | 5.164 | 458 | — | 无人核验 | | | | |
| **2024→26** | 5838 | **+0.4566** | **1.017** | **2613.7**(峰 2024-03-31 → 谷 2025-02-06) | 0.791(0.608–0.975) | **+0.4065** | **0.899** | **2657** | +0.4665 / 1.036 / 2604.7 | **+1.4731 / 3.139** |
| 2022→23(fund-only 段, 非在役形态) | 4200 | −0.2561 | −0.742 | 1249.4 | 0.879 | −0.2573 | −0.752 | 1273.8 | −0.2329 / −0.678 | −0.3539 / −1.002 / 1678.5 |
| 2022→26 全样本(2022–23 为 fund-only, 混合形态, 只作信息) | 10038 | +0.1584 | 0.387 | 3519.1 | — | +0.1287 | 0.314 | 3637.6 | +0.1739 / 0.425 | +0.7087 / 1.667 / 3144.4 |

来源: Σ-simple 列 R-C6.0 `recompute.log`、R-C6.1 `recompute_stats.out`、R-C6.2 `recompute.py`(三票一致); Π 列 R-C6.1 `alt_stats.out` + R-C6.2 `run_alt.sh`(两票逐位一致); 只换窗列 R-C6.1(逐年 Δ +0.009/+0.029/−0.019)+ R-C6.2; 2026≤08-10 行 `pod_port_followup_stats.json`(R-C6.0/R-C6.2)。R-C6.0 的同窗 [E,E+47] Π 变体: 2024→26 +0.3795 / S 0.838 / maxDD 2692(逐年 −0.7337/+0.2068/+2.3233)——不同窗, 列为第三读数。
**2022/2023 行来源(gap_2)**: 均值 = 装置自报 `RECEIPT_EX d30_n2_c42 … "by_year_ex": {"2022": -0.12, "2023": -0.381, …}`(R-C6.1 `pod_outputs/run_alt.out` L3 `alt_sum_old_w3fix`; R-C6.2 `REPORT.md` L431 同一行逐字), Π 列 `run_alt.out` L9 `alt_true_new_w3fix` `{"2022": -0.098, "2023": -0.404}`, 只换窗 L7 `alt_sum_new_w3fix` `{"2022": -0.094, "2023": -0.36}`, 旧 expm1 R-C6.2 `REPORT.md` §9.14 `pod_live_w3fix_calsimple_s42` `{"2022": -0.43, "2023": -0.284}`; n / Sharpe / maxDD / gross / 合段行 = gap_2 `pod_gap2_stats.py` 对 port `w10_ablation_series_pod_live_w3fix_{callog,calsimple}_s42.npz` 与 R-C6.1 `dev/probe_artifacts/w10_ablation_series_alt_*.npz` 直算(`gap2_stats.json`; 同一脚本对 2024–26 复得 −0.6421/−1.682/1814.9 等, 与本表既有格逐位同)[VERIFIED, 单仪器 pod]。
- **最差月**(VERIFIED, 三票; 定义 = 日历月 net_ex 之和, bps of NAV-book: `/workspace/port_w10/summarize.py` L16-18 `msum = {...nx[ym == m].sum()...}; wm_key = min(msum, key=msum.get)`; ÷ 年均 gross_total ÷ 100 = %/gross(`pod_units_table.py` L13); ×2 = % NAV @2×):

| 年 | Σ-simple [E,E+47](CAL=log) | %/gross → 2× NAV | Π(1+r)−1 (E,E+4h] | %/gross → 2× NAV | Σ-simple (E,E+4h](只换窗) | 旧 expm1(CAL=simple) |
|---|---|---|---|---|---|---|
| 2022 [fund-only, 非在役形态] | 2022-04 −467.7 | −5.28% → −10.6% | 2022-04 −478.5 | −5.40% → −10.8% | 2022-04 −478.0 | 2022-04 −467.5(−5.3% → −10.5%) |
| 2023 [fund-only, 非在役形态] | 2023-01 −507.8 | −5.82% → −11.6% | 2023-01 −520.3 | −5.97% → −11.9% | 2023-01 −522.3 | 2023-01 −549.8(−6.3% → −12.6%) |
| 2024 | **2024-11 −717.0** | −8.47% → **−16.9%** | 2024-11 −756.8 | −8.96% → −17.9% | 2024-11 −704.9 | 2024-11 −576.1(−6.8% → −13.6%) |
| 2025 | **2025-01 −634.5** | −8.46% → **−16.9%** | 2025-01 −574.9 | −7.67% → −15.4% | 2025-01 −628.2 | 2025-01 −463.5(−6.2% → −12.3%) |
| 2026(→08-30) | **2026-08 −252.4** | −3.29% → **−6.6%** | 2026-08 −238.0 | −3.12% → −6.2% | 2026-08 −295.8 | 2026-08 +41.5(全年无负月) |
| 2026(≤08-10) | +171(2026-02, 无负月) | — | 无人核验 | | | +324(2026-08) |
| **2024→26** | **2024-11 −717.0** | ÷0.791: −9.07% → **−18.1%** | 2024-11 −756.8 | −9.60% → −19.2% | 2024-11 −704.9 | 2024-11 −576.1(−7.3% → −14.5%) |

  来源: Σ-simple 列三票逐位同——R-C6.0 `recompute_out.txt` L131-134(`worst (np.str_('2024-11'), -717.0)` / `('2025-01'), -634.5` / `('2026-08'), -252.4` / 2024on `-717.0`)、R-C6.1 `recompute_c6.out` L10 `ARM pod_live_w3fix_callog_s42 … "worst_month": [202411, -717.0]`、R-C6.2 `REPORT.md` §9.3 L326-330(≤08-10 行 L328); 旧口径列 R-C6.0 L136-139(`-576.1 / -463.5 / 41.5`)。Π 与只换窗列 = 本轮 gap_3 `worst_months.py`(sha 97e2af02)对 R-C6.2 `altrun/newprod|newsum/probe_artifacts/*.npz` 与 R-C6.1 `dev/alt_true_new_*|alt_sum_new_*`、`rerun_prodnew|rerun_sumnew` 各算一次, 两组逐位同(`gap_3/worst_months.out`)。%/gross 与 2× NAV 由 `gap_3/pod_units_table_gap3.py`(= 仓 `pod_units_table.py` L13-14 补印月份 id / bps NAV / 2×)打印于 `gap_3/pod_units_table_gap3.out`; 原 `pod_units_table.py` 本已打印 `最坏月 −8.5/−8.5/−3.3/−9.1% gross`(`gap_3/pod_units_table_orig.out` L22-25), 只缺 2× 换算。按当月自身 gross(0.821/0.781/0.768)换算为 −8.73% / −8.13% / −3.29%(`worst_months.out` g_month 列)。**注**: 固定席位 2024-11 / 2024-12 / 2025-01 连续三月 −717 / −616 / −635(月序列见 `worst_months.out` MONTHLY 行), 全部落在 maxDD 2614 的峰谷窗 2024-03-31→2025-02-06 内; 三口径(Σ/Π/只换窗)最差月同月, 幅度差 ≤ 40 bps。
2022/2023 最差月来源: gap_2 `pod_gap2_worstmonth.py` → `gap2_worstmonth.json`(同定义 `summarize.py` L16-18, 同一脚本对 2024 复得 2024-11 −717.0 / −756.8 / −704.9 / −576.1 与本表逐位同)[VERIFIED, 单仪器 pod]。
- 复利 NAV 口径 maxDD(固定, Σ-simple)2323 bps(R-C6.0 `maxDD_compound`); per-gross cumsum maxDD 3155 bps(R-C6.2)。
- **carry 口径扣减: 0.00 bps/锚(G1, VERIFIED)** — 装置比例计提 vs 场所实收, **同书**(执行器 readback 名义)52 窗 −0.12 ± 0.09 bps/锚 per gross(结算规则口径 −0.07 ± 0.07): 装置不低估 carry, 略高估; 对 +0.4566 / +0.4065 **无修正**。RESULT_caliber_revalidation L64 "回放 0.77 vs 实收 1.98(重叠 27 锚)⇒ 真钱期望 ≈ 回放 − 1.2 ⇒ 固定 +0.46 → ≈ −0.7" **作为口径修正被驳**: 0.77 是每 NAV(gross 0.759 ⇒ 每 gross 1.02)的**回放书** carry, 1.98 是每 realized gross 的**实盘书** carry——分母不同、书不同(G1 `panel_vs_ledger_2x2.out`, `carry_reconcile.out`)。
- **书构成 carry 差(G1, INFERRED: 单 regime 28 锚 08-26 04Z→08-30 20Z)**: 同费率、同公式下, 实盘 combo 目标书比回放书多付 **+1.21 ± 0.17 bps/锚 per gross**(固定席位)/ +1.20 ± 0.16(动态)≈ +26 %/gross/年(≈ −0.95 bps/锚 per NAV @ gross 0.79); 2×2: 回放W×面板 +0.777 / 回放W×账本 +0.774 / 实盘W×面板 +1.766 / 实盘W×账本 +1.766(每 NAV; 费率效应 0.003, 权重效应 +1.212)。若全史如此, 固定表头 +0.457 → ≈ −0.5, 动态 +0.691 → ≈ −0.3——**4.7 天的差不得外推**; 在役 combo 形态的全史 carry **UNRESOLVED**(需把 combo 书本身过面板, §7 #25)。背景: 实盘书 carry 账单 2.3 bps/锚 per gross(≈ 51 %/gross/年)vs 回放 2026 均 1.19/gross(26%)。

### 5.2 动态 msharpe 席位

| 年 | Σ-simple(CAL=log) | Sharpe | gross 年均 | Π(1+r)−1 (E,E+4h] | Sharpe | maxDD | 旧 expm1 |
|---|---|---|---|---|---|---|---|
| 2020–2021 | **UNAVAILABLE**(同 5.1) | | | UNAVAILABLE | | | |
| 2022 **[king 腿=0, F10 absent; 席位非 fund-only: 前 900 锚 = [⅓,⅓,⅓] 且 LEGS 掩码未施加(含 rev24, 装置 L152), 其后 fund 回看 Sharpe ≤0 时退化为 [0.5,0,0.5](L169-171); w3_king 年均 0.225, 最大 0.5]** | +0.3128 | 0.897 | 0.819 | +0.325 | 0.944 | 467.2(Σ-simple 469.2) | −0.100 / S −0.27 / maxDD 772.0 |
| 2023 **[king 腿=0, F10 仅 22.6% 覆盖; w3_king 年均 0.066 ⇒ ≈ fund-only 书]** | −0.3732 | −1.213 | 0.837 | −0.412 | −1.331 | 1180.4(Σ 1142.7) | −0.295 / S −0.98 / maxDD 1126.2 |
| 2024 | +0.1489 | 0.533 | 0.602 | +0.116 | — | — | — |
| 2025 | +0.3590 | 1.146 | 0.531 | +0.339 | — | — | — |
| 2026(→08-30) | +2.0132 | 3.842 | 0.779 | +2.068 | — | — | — |
| 2026(≤08-10) | +2.5118 | 4.832 | — | 无人核验 | | | |
| **2024→26** | **+0.6914** | **1.884** | 0.620(0.290–0.903) | **+0.685** | **1.881** | **967**(Σ-simple 为 794.9) | **+1.5975 / 3.998** |
| 2022→23(非在役形态) | −0.0449 | −0.137 | 0.828 | −0.0595 | −0.182 | 1180.4(Σ 1142.7) | −0.2014 / −0.605 / 1245.1 |
| 2022→26 全样本(混合形态, 只作信息) | +0.3833 | 1.091 | — | +0.3735 | 1.070 | 1875.2(Σ 1673.3) | +0.8448 / 2.262 / 1282.3 |

来源同 5.1; 动态 Π 列 R-C6.2(逐年)+ R-C6.1(2024→26 +0.6850/1.881); 只换窗 Σ (E,E+4h]: +0.7263 / 1.970(R-C6.1/R-C6.2); R-C6.0 同窗 Π: +0.6302 / 1.727 / maxDD 999。**注意 2024 值受装置伪影影响(§4 C6 第 6 点, INFERRED)。**
- **最差月**(VERIFIED, 定义同 5.1): Σ-simple(CAL=log) **2024-04 −363.1**(−6.03%/gross → −12.1% NAV @2×)/ **2025-12 −294.5**(−5.54% → −11.1%)/ **2026-08 −293.5**(−3.77% → −7.5%)/ 2024→26 −363.1(÷0.620 = −5.86% → **−11.7%**); Π(E,E+4h] 2024-04 −374.9 / 2025-12 −275.2 / 2026-08 −260.8 / 2024→26 −374.9(−6.16% → −12.3%); 只换窗 Σ 2024-04 −381.3 / 2025-12 −281.4 / 2026-08 −294.6; 旧 expm1 2024-07 −343.2 / 2025-04 −369.9 / 2026-08 +85.1(全年无负月)/ 2024→26 −369.9(−6.0% → −12.0%); 2026(≤08-10): +104(2026-02)/ 旧 +343(2026-08)。来源: R-C6.0 `recompute_out.txt` L111-114(CAL=log)/ L116-119(CAL=simple); R-C6.1 `recompute_c6.out` L6 `ARM pod_live_callog_s42 … [202404, -363.1]`; R-C6.2 `REPORT.md` §6 L123-127; Π/只换窗 = gap_3 `worst_months.out`(R-C6.1 与 R-C6.2 两组 npz 逐位同); %/gross、2× 见 `gap_3/pod_units_table_gap3.out` L12-15。**注**: 动态席位最差月(−363)比固定席位(−717)小一半, 与 2024 动态 2024-11 为 +286 而固定为 −717 一致(动态臂 2024 席位受装置伪影, 同上注意)。
- 2022/2023 最差月(gap_2 `gap2_worstmonth.json`, 定义同上): Σ-simple 2022-04 −351.2(−4.29%/gross → −8.6% NAV @2×)/ 2023-01 −496.9(−5.93% → −11.9%); Π 2022-04 −348.3 / 2023-01 −544.7(−6.48% → −13.0%); 旧 expm1 2022-04 −340.2 / 2023-01 −490.1 [VERIFIED, 单仪器 pod]。
- **carry 口径扣减 0.00 / 书构成差 +1.20 ± 0.16 bps/锚 per gross(动态席位, 28 锚, INFERRED)**: 同 §5.1 两条(G1 `panel_vs_ledger_2x2.out` `pod_live_callog_s42` 段: 回放W×面板 +0.774 / 实盘W×账本 +1.766 每 NAV; 每 gross 1.035 vs 2.233)。
2022/2023 行来源: 均值 = R-C6.1 `pod_outputs/run_alt.out` L4 `alt_sum_old_dyn` `{"2022": 0.313, "2023": -0.373}`(R-C6.2 `REPORT.md` L98 `pod_live_callog_s42` 同值), Π 列 L10 `alt_true_new_dyn` `{"2022": 0.325, "2023": -0.412}`, 只换窗 L8 `alt_sum_new_dyn` +0.314/−0.375, 旧 expm1 R-C6.2 `REPORT.md` L100 `pod_live_calsimple_s42` `{"2022": -0.1, "2023": -0.295}`; Sharpe / maxDD / gross / w3_king / 合段行 = gap_2 `gap2_stats.json`(port `w10_ablation_series_pod_live_{callog,calsimple}_s42.npz`, R-C6.1 alt npz)[VERIFIED, 单仪器 pod]。
**2022–23 读法(两表共用)**: ① 这两年在两表里都是**负年份**(固定席位 Σ-simple −0.12/−0.38 bps/锚 ⇒ 按 AUDIT §3 公式 2.0× 复利 −6.4%/−16.2% NAV; CAL=simple 却是 −18.4%/−12.6%: 伪凸性在 2022 把 fund-only 书压低 0.31 bps/锚, 在 2023 抬高 0.10——方向不恒定, §4 C2 "fund 高估 0.3–0.9" 的 2024–26 结论不能外推到 2022–23)[VERIFIED: gap_2 `gap2_auditformula.json`]。② 动态席位 2022 的 +0.31 **不是** fund-only 书的读数: 前 900 锚等权三腿含 rev24(装置 L152 在 `p < LOOK` 分支返回 `[1/3]*3` 且不施 LEGS 掩码), 其后当 fund 回看 Sharpe ≤ 0 时 `msk / max(msk.sum(), 1.0)` 把 0.5 席位放在零收益 king 腿上(L169-171)——2022 年 w3_king 均 0.225/最大 0.5 是这两条机械路径的产物 [VERIFIED: 装置行 + `gap2_stats.json` w3_king]; 2023 w3_king 均 0.066, 基本是 fund-only。③ 在役 combo(king 0.21 + F10 链 + fund)的 2022–23 期望**今日无法给出**(需 jpline 年折外 king + F10 2022–23 折, 见 §5 首段); 用户规则要求的 2021–2026 逐年表在 pod 单仪器下只能给到本表形态, 2021 UNAVAILABLE。

### 5.3 单位换算链(显式)

以固定席位 2024→26 为例, 两种配方并列(R-C6.1 与 R-C6.2 均给出; 本节算术只是把它们排成链):

| 步 | 公式 | Σ-simple, 比值之均值(`pod_units_table.py` L10-11) | Σ-simple, 均值之比值(恒定 gross 匹配, R-C6.2) | Π(E,E+4h], 比值之均值 |
|---|---|---|---|---|
| bps/锚 per NAV-book | net_ex | +0.4566 | +0.4566 | +0.4065 |
| → per gross | ÷ gross_total | 0.4566/0.791 = +0.5774 | mean(net_ex/gross) = +0.6576 | 0.4065/0.791 = +0.514(本文算术) |
| → 年化 %(gross) | × 2190 / 100 | +12.65% | +14.4% | +11.3%(本文算术) |
| → 年化 % NAV @1×(书自身 gross) | net_ex × 21.9 | +10.0% | +10.0% | +8.9%(本文算术) |
| → 2× NAV(在役 gross_mult 2.0) | ×2 | **+25.3%** | **+28.8%** | ≈ **+22.5%**(本文算术; R-C6.0 以其同窗 Π 0.3795 得 ≈8.3% NAV = 10.5%/gross = 21%@2×) |
| maxDD | 2614 bps NAV ÷ 0.791 | 33.1% gross → **66% NAV @2×**(R-C6.1) | per-gross cumsum 3155 bps(R-C6.2) | 2657 bps NAV(未换算) |
| 最差月 | 2024-11 −717.0 bps NAV ÷ 0.791 | −9.07% gross → **−18.1% NAV @2×**(gap_3 `pod_units_table_gap3.out` L25) | 按当月 gross 0.821: −8.73% → −17.5%(`worst_months.out` g_month) | 2024-11 −756.8 → −9.60% → −19.2% |
| → 执行时点(持仓窗 → [E+6,E+53] = (N+25m, N+4h+25m]; 同装置 y4 override 重跑, G6) | 固定席位 net_ex: Σ +0.4665 → +0.4563(S 1.036 → 1.022, maxDD 2605 → 2624); Π +0.4065 → **+0.3888**(S 0.899 → 0.864, maxDD 2657 → 2634); 动态 Π +0.6850 → +0.6711(S 1.881 → 1.794), Σ +0.7263 → +0.7434 | Σ 平移: 0.4563/0.789 = +0.5782(+12.7%; 2× +25.3%) | Σ 平移 mean(net_ex/gross) +0.6625(+14.5%) | Π 平移: 0.3888/0.787 = **+0.4938**(+10.8%; 2× +21.6%); mean(net_ex/gross) +0.5816(+12.7%) |
| → 扣执行保真 −0.3 bps of gross/锚(`docs/AUDIT_live_vs_replay_2026-09-04.md` L10: 12 锚纸面 −240U vs 执行 −333U, 含费 37U ⇒ 时序/滑点 ≈ −0.3; 用户规则 memory `feedback_report_live_caliber_full_cycle` L7; **引用值, G6 未重估, INFERRED**) | 平移窗 per gross − 0.3 | +0.5774 − 0.3 = **+0.2774** ⇒ +6.1%/gross/年 ⇒ 2× **+12.2%**(未平移 Σ 基线) | +0.6576 − 0.3 = **+0.3576** ⇒ +7.8% ⇒ 2× **+15.7%** | +0.4938 − 0.3 = **+0.1938** ⇒ +4.2%/gross/年 ⇒ 2× **+8.5%**(mean(net_ex/gross): +0.5816 − 0.3 = +0.2816 ⇒ +6.2% ⇒ 2× +12.3%) |
| → 扣 carry 口径 | 0.00(G1, 同书 −0.12 ± 0.09 距 0 约 1.3 se) | 不变 | 不变 | 不变 |

逐年 %/gross(比值之均值, R-C6.1): 固定 −16.61 / +8.30 / +67.86; 动态 +5.42 / +14.79 / +56.58。动态 2024 均值之比值 +13.9%(R-C6.2)。2190 = 365×6; 2024 有 2196 锚。
**负年份显式**: 固定席位 2024 为负(−0.64 bps/锚, −16.6%/gross, 年内 maxDD 1815 bps NAV), 两口径皆负。
**逐年扣减链(G6 `final_stats_gap6.out` DEDUCTION CHAIN; per gross 比值之均值, Π 执行窗 [E+6,E+53] → 扣 0.3)**: 固定席位 2024 −0.8405 → **−1.1405**(−25.0%/gross/年, 2× **−50%**); 2025 +0.3365 → +0.0365(+0.8%, 2× +1.6%); 2026(→08-30) +2.9629 → +2.6629(+58.3%, 2× +117%); 2024→26 +0.4938 → +0.1938(+4.2%, 2× +8.5%)。动态席位同链: 2024 +0.2012 → −0.0988(−2.2%, 2× −4.3%); 2025 +0.5266 → +0.2266; 2026 +2.7058 → +2.4058; 2024→26 +1.0913 → **+0.7913**(+17.3%, 2× +34.7%)。Σ 基线(未平移)固定 2024→26 +0.5774 → +0.2774(2× +12.2%); mean(net_ex/gross) +0.6576 → +0.3576(2× +15.7%)。

**执行时点读法(G6, VERIFIED 数字, [单仪器 pod])**: 书层把持仓窗平移 25 分钟只吃掉固定席位 2024→26 均值的 **2–4%**(Π −0.0176 / Σ −0.0102 bps/锚; 配对 Δ 均 −0.019 ± 0.136 SE, t −0.14 / −0.012 ± 0.135; 逐年 |t| ≤ 0.21), 动态席位 −2%~+2%(Π −0.0140 / Σ +0.0171; 配对 t −0.13 / +0.13; 逐年 |t| ≤ 0.38); corr(未平移, 平移) 0.83–0.88; 2024→26 的 Δ 几乎全在 pnl_ex(Δcarry ≤ 0.004, Δcost ≤ 0.007)——与 `pod_alpha_decay_20260904.out` L5-L16 的腿级/代理书 5–19% 衰减(king 81–85%, fund 95–108%, F10 54–107%, 代理书 91–95%)**不同量级**。差异机理(INFERRED): 该脚本的代理书每锚全量重建(`pod_alpha_decay.py` L22-24 `book()` 无 EMA 态, L33), 全部仓位都暴露在前 25 分钟的 alpha 前置里; 装置书 `w10_universe.py` L214 `sm = H + 0.1 * (tgt - H)` 每锚只换 10%, 存量仓位跨锚连续持有, 平移窗只改变增量部分的暴露——与 AUDIT L10 "延迟成本 +0.02 bps/锚, alpha 前置部分由存量捕获"同向。故 §5 数字**不需要**再打 5–10% 折; 实盘系统性折扣 = 执行保真 −0.3 bps of gross/锚(12 锚样本, 未重估)+ carry 书构成差(§5.1, 未定全史)。收据: `gap_6/build_shift_meta.out`(`window check: first row E+6, last row E+53`; shiftprod vs `pod_alpha_decay.py` y4s_shift(E_row,5) 3,374,223 格 exact_eq 1.000000; newprod vs R-C6.2 meta_newprod 3,446,600 格 exact_eq 1.000000; dlw `E_row == 5m row-by-ts: True n 10086`; sha256 meta_shiftsum 55b3bfad…, meta_shiftprod 12621eff…), `final_stats_gap6.out` L1-4(`BITWISE gap_6 base_w3fix vs port: rec array_equal True max|Δ net_ex| 0.0`, dyn 同, vs R-C6.2 base 同), `paired_delta.out`, 命令逐字 `run_shift.out` L19-24(`env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero [W3FIX=0.21,0,0.79] OUT_TAG=… /workspace/venv/bin/python w10_universe.py`, 装置 sha 64c70a44 == `/workspace/port_w10/w10_universe.py`)。**注**: 平移窗使最后一锚 2026-08-30 20:00 因 5m 数据末段 NaN(n<46)被跳过(基线该锚 net_ex −9.23), 故平移臂 2026 n=1451 / 2024on n=5837(基线 1452 / 5838); 配对统计只用共同锚。

**maxDD 换算的分母混用(CRITIC, `critic/CRITIC_NOTES.md`)**: 表中 2614 bps 的峰谷窗是 2024-03-31→2025-02-06, 却除以三年均 gross 0.791(33.1% → 66% @2×, `pod_units_table_gap3.out` L25 "maxDD 33.1% gross ⇒ 2× 66.1% NAV"); 按 2024 年均 gross 0.847 为 30.9%/gross → 61.7% @2×; 按恒定 gross 的 cumsum(net_ex/gross)maxDD 3155 bps = 31.6% → 63.1% @2×(R-C6.2); 三者都是 cumsum 非复利(复利 NAV 口径 2323 bps, R-C6.0)。报法待用户定(§7 #35)。

### 5.3b 对账: `AUDIT_live_vs_replay_2026-09-04.md` §3 / `RESULT_allweather_2026-09-04.md` §1(2024 −8% @2×)vs 本节 §5.1/§5.3(2024 −33% @2×)

**来源判定(VERIFIED)**: AUDIT §3 臂 C = tag `uni2_F_M7F_fx_s42`(`retrain_2026-09/jp_live_caliber_tables.py` L23), 从 jpline `probe_artifacts/w10_uni2_F_M7F_fx_s42.npz` 读 `d30_n2_c42_rec` 的 `net_ex`(L6-7); 该 npz 由 06:31:59Z 的 ssh 命令产出、06:33Z 出表(旧 transcript `6737834a….jsonl` 第 211810/211811 行, gap_2 `transcript_L211811_armC.txt` 逐字; git 7e5967f 14:34+08 = 06:34Z 入库), env 逐字: `env LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=42 FPRED=f10_V2MAIN_s42.npy OUT_TAG=uni2_F_M7F_fx_s42 UMASK_NPZ=$PD/umask_F_M7.npz FTRIM=zero W3FIX=0.21,0,0.79 … w10_universe.py`(模板 = `jp_universe2_runner.sh` L13 / `jp_universe2_round2.sh` L7, 均写死 `CAL=simple LEGS=101`)。`RESULT_allweather` §1 的 C/E 基臂行是同两个 npz 被 `jp_allweather.py` L32 再读一遍(L18-19 同公式), 07:00Z 是文档时间, 不是新批次。故: **① 口径 CAL=simple(expm1 伪凸性, §4 C2)**; **② LEGS=101 而非 111**(此前对账假设"臂 C LEGS=111"不成立; LEGS=111 只出现在 RESULT_allweather §1 的 H3 行); ③ king = 装置 L86 默认 `{B}/slow_pred_hist_oos.npy`(jpline 年折外件, 无 SLOW_NPY 覆盖)而本节 = pod `slow_pred_pinned.npy`; ④ 宇宙 = meta members(top-400 天花板)∩ `umask_F_M7.npz`(冻结 450 月刷 + 7 日门, 只缩不扩, 装置 L70-82; 该掩码不在 pod: `find /workspace -name 'umask_*.npz'` 只有 umask_U0/U1/U2)而本节 = MEMBERS_TOPN=829 TRADE_TOPN=400; ⑤ 面板 = jpline hist meta/panel(止 08-15, 含 2021)而本节 = v2ext(止 08-30, 起 2022); ⑥ 换算 = `jp_live_caliber_tables.py` L19 `x=L*r/1e4; eq=np.cumprod(1+x); ann=eq[-1]**(2190/n)-1`: 2.0× 直接乘在**每单位 NAV** 的 net_ex 上逐锚复利, 不除 gross_total(其 L2 docstring 写的"单位 gross"是信念, 与 §5.3/R-C6.2 的换算链矛盾), 而 §5.3 的 −33% = 每单位 gross(÷0.847)× 2 的单利年化。

**2024 的 4× 差距分解(pod 自跑, 全部 VERIFIED; gap_2 `pod_gap2_armB.sh`(env 逐字见 `dev/logs/commands.txt`)+ `pod_gap2_auditformula.py` → `gap2_auditformula.json`)**:

| 步 | 序列 | 2024 @ AUDIT 公式 2.0× 复利 | Sharpe(ddof=0, 同 AUDIT) | DD 2× | 最差月 2× | 均值 bps/锚 |
|---|---|---|---|---|---|---|
| 0 | §5.3 报法: 固定席位 live 形态 CAL=log, 每 gross ×2 单利 | −33%(§5.3) | −1.68 | — | — | −0.6421 |
| 1 换算路径 | 同一序列, 改用 AUDIT 公式 | **−25.6%** | −1.68 | −31.1% | −13.6% | −0.6421 |
| 2 口径 | 同形态 CAL=simple(port `pod_live_w3fix_calsimple_s42`) | **−15.8%** | −0.92 | −26.4% | −11.2% | −0.3582 |
| 3 形态 | 臂 B 同构: `MEMBERS_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 CAL=simple LEGS=101`(runner env 逐字, king=pinned, 面板 v2ext) | **−15.5%** | −0.91 | −26.3% | −10.9% | −0.3523 |
| 3′ | 同上 CAL=log | −26.1% | −1.74 | −31.3% | −13.2% | −0.6577 |
| 4 jpline 残差 | AUDIT §3 臂 B(jpline, 同 env 同口径, king=hist_oos, 面板 hist) | **−8%** | −0.42 | −25% | −7.6% | — |
| 4′ | AUDIT §3 臂 C(= 臂 B + umask_F_M7) | **−8%** | −0.44 | −28% | −9.7% | — |

读法: −33 → −25.6 是换算路径(每 gross 单利 vs 每 NAV 复利, ×0.78); −25.6 → −15.8 是 expm1 伪凸性(2024 固定席位书 +0.284 bps/锚, ×0.62); −15.8 → −15.5 是 M829/T400 vs N400(2024 几乎不绑定, 与 R-C6.2 §9.11 一致); **−15.5 → −8(Sharpe −0.91 → −0.42)是 jpline 与 pod 的残差**——同 env、同口径、同装置语义下只剩 king 来源(jpline 年折外 vs pod pinned 2024 折)与面板谱系(jpline hist vs v2ext)两个变量, 今日 jpline 不可达, **UNRESOLVED**; 臂 C 的 umask_F_M7 在 2024 几乎不改变结果(臂 B −8%/−0.42 vs 臂 C −8%/−0.44, AUDIT §3 自身)。同一残差在其他年份更大且方向不恒定(2025: pod 臂 B 同构 CAL=simple +61.8%/S 2.39 vs jpline 臂 B +45%/S 2.09; 2022: −18.6%/−1.13 vs −22%/−1.40; 2023: −12.3%/−0.86 vs −1%/−0.04——jpline 2022–23 有 king 预测而 pod 没有)。

**裁定**: AUDIT §3 全表、RESULT_allweather §1 全表及其 §0 结论(H1 σ_fund 阶梯"录取候选"、"2024 −8→+3"、H2/H3 逐年)都建立在 **CAL=simple(伪凸性)+ jpline 单仪器 + 面板止 08-15** 之上, 本稿标为 **CAL=simple-stale**(§7 #20): 相对判决(臂 vs 臂)是否存活需在 CAL=log 下重判, 绝对数字不得再引作实盘口径期望; `jp_callog_revalidate.sh` L6 已把复跑固定为 `LEGS=101 CAL=log`, 但其 L8-12 只覆盖 canon / N829T400F / T3c 五个 tag, **不含** AUDIT §3 的 `uni2_{F_M7F,F_QF,N400rF,N829T400F}_fx`(W3FIX+FTRIM+umask)臂——jpline 恢复后需按 `jp_universe2_runner.sh` 模板加 `CAL=log` 重产这四个 npz 再跑 `jp_live_caliber_tables.py` / `jp_allweather.py`。用户规则(ERROR_LEDGER L373; memory `feedback_report_live_caliber_full_cycle` "引用前先查 AUDIT §3 表")所指向的那张表本身即是陈旧口径, "引用前先查"应改指本节 §5.1/§5.2(含 2022–23 标注行)直至 jpline 复跑。

### 5.4 T3c 与孤立臂(CAL=log, Σ-simple; **未在 Π 口径下重跑, UNRESOLVED**)

| 臂 | 基线 | Δ2024 | Δ2025 | Δ2026 | Δ2024→26 | ΔSharpe |
|---|---|---|---|---|---|---|
| T3c KMOD_F10=0.5, s42 | live s42 | −0.040 | −0.031 | −0.024 | **−0.0328** | −0.08 |
| T3c, s2027 | live s2027 | −0.039 | −0.027 | +0.013 | **−0.0216** | −0.05 |
| M1+T400 | canon +0.7304 | −0.057 | −0.086 | +0.181 | −0.0090 | +0.09 |
| FTRIM | canon | −0.044 | +0.042 | −0.070 | −0.0180 | −0.08 |
| T400 | canon | +0.000(2024 序列逐位同) | −0.095 | +0.001 | −0.0356 | +0.01 |

来源: R-C6.0 `recompute.log` DELTAS、R-C6.1 `recompute_stats.out` DELTAS、R-C6.2 `recompute.py`(三票一致)。

### 5.5 腿级四口径(T-GT, pod, dlw 10,056 共同锚, 单位 gross 秩书, bps/锚)

| 腿 | 口径 | 2024 | 2025 | 2026(→08-10) | last900 均值 | last900 S/锚 |
|---|---|---|---|---|---|---|
| king | y4old Σ-simple | +1.533 | +2.381 | +3.198 | +2.925 | +0.0996 |
| king | y4s Π(1+r)−1 | +1.618 | +2.280 | +3.071 | +2.912 | +0.0978 |
| king | expm1(y4old)(装置 CAL=simple) | +0.577 | −0.048 | −0.093 | −0.598 | **−0.0196** |
| king | log1p(y4s) | +2.552 | +4.634 | +6.246 | +6.298 | +0.2130 |
| fund | y4old Σ-simple | −0.361 | +1.712 | +6.344 | +7.411 | +0.2516 |
| fund | y4s Π | −0.448 | +1.600 | +6.027 | +6.949 | +0.2296 |
| fund | expm1(y4old) | −0.157 | +2.339 | +6.925 | +8.141 | +0.2610 |
| fund | log1p(y4s) | −0.652 | +0.990 | +5.503 | +6.295 | +0.2134 |

R-C2.x 独立重算 king Σ-simple +1.533/+2.381/+3.130(2026 至 08-30 的 meta 栅格)与 expm1 +0.577/−0.048/−0.105——与 T-GT 一致到 0.03。名级 Σ−Π: 均值 +0.43 bps, std 36.3, p99|Δ| 39.6(2,741,477 名-锚); 对数−Π: −3.80 ± 41.1。

### 5.6 席位受口径影响的读数(T-SEAT / R-C3)

- 在役 900 行 msharpe 窗 → w3 [0.1972,0.1218,0.6809](08Z), 2-leg king 席位 0.2246; 全改生产者窗 0.2235; 全改交易所 Π 窗 0.2359(R-C3.0 `pod_aug.py`)。
- v3 seed 后 900 行(未进实盘窗): Σ[E,E+47] king/(king+fund) 0.3228; Σ[E+1,E+48] 0.3165; Π 0.3361; expm1(Σ) → w3 [0,0,1](R-C3.0 `pod_window.py`)。

### 5.7 σ_fund 三分位(regime 分档期望; G4, VERIFIED 脚本打印, [单仪器 pod])

**定义(执行行)**: σ_fund = `retrain_2026-09/jp_allweather.py` L15-16 `iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); r=f*(8.0/iv); r=r[np.isfinite(r)]` / `if len(r)>50: out[k]=np.std(r)*1e4`(取**全部有限面板名**, 非 members——脚本如此, 本节照跑并附 members-only 敏感性), 30 锚滚动均值 L40 `roll=np.array([np.nanmean(sf[max(0,i-29):i+1]) …])`; 面板 = `/workspace/port_w10/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz` → realpath `/workspace/data/wide_panel_4h_v2ext.npz`(10039 行 2022-01-31→2026-08-31, `f_fund_now`/`f_fund_iv` (10039,829))。三分位切点 = `np.quantile(roll[sel],[1/3,2/3])` 于 2024→26(n=5838, 无 roll-NaN, 各档 1946): **5.75 / 13.47 bp**; CI = 6 锚块 bootstrap(`jp_allweather.py` L29-31); Sharpe = mean/std(ddof=1)·√2190; 单位 net_ex bps/锚 per NAV → %/gross/年 = ÷ 档内均 gross × 21.9; "2× 复利" = 逐锚 2·net_ex/gross 复利。装置 `gap_4/gap4_sigfund_terciles.py`(pod `/workspace/review_scratch/gap_4/`, 命令 `cd /workspace/review_scratch/gap_4 && OMP_NUM_THREADS=4 /workspace/venv/bin/python gap4_sigfund_terciles.py` → `GAP4_DONE`), 输出 `gap4_sigfund_terciles.out/.json`; 敏感性 `gap4_sens.py` → `gap4_sens.out`(members-only 一版因 members 形状报错, 见文件末 Traceback)、`gap4_sens2.out`(修正后)。

| 序列(CONFIG 自报) | LOW σ_fund≈3.4bp(n 1946; 其中 2024 占 1812) | MID ≈9.7bp | HIGH ≈19.6bp |
|---|---|---|---|
| `pod_live_w3fix_callog_s42`(W3FIX 0.21/0/0.79, M829/T400/FTRIM=zero, CAL=log = Σ-simple) | **−0.822 CI95[−1.589,−0.114] ⇒ −21.3 %/gross/年(2×: −42.6 单利 / −35.1 复利, maxDD −37.1%), S −2.22** | +0.596 CI[−0.426,+1.698] ⇒ +17.0, S +1.28 | +1.596 CI[+0.547,+2.588] ⇒ +46.0, S +3.19 |
| `alt_true_new_w3fix`(同形态, y4 = Π(1+r)−1 (E,E+4h]) | **−0.859 CI[−1.620,−0.159] ⇒ −22.3, S −2.32**(2× 复利 −36.3%, maxDD −37.6%) | +0.506 ⇒ +14.5, S +1.07 | +1.572 ⇒ +45.5, S +3.13 |
| `pod_live_callog_s42`(动态 msharpe, CAL=log; LOW 档 w3_king 0.62) | +0.165 CI[−0.389,+0.698] ⇒ +6.0, S +0.58 | +0.872 CI[+0.069,+1.727] ⇒ +32.5, S +2.33 | +1.037 ⇒ +34.1, S +2.42 |
| `alt_true_new_dyn`(动态, Π) | +0.107 CI[−0.426,+0.635] ⇒ +4.0, S +0.39 | +0.833 ⇒ +31.5, S +2.20 | +1.116 ⇒ +37.1, S +2.63 |
| `pod_live_w3fix_calsimple_s42` [旧 CAL=simple 口径, 仅参照] | −0.476 CI[−1.271,+0.246] ⇒ −12.4, S −1.27 | +1.712 ⇒ +48.6, S +3.48 | +3.183 ⇒ +91.4, S +6.06 |

- 2023→26 补充(切点 4.33/11.31, 各档 2676; **2023 是 fund-only 书, §5 首段**): 固定 CAL=log LOW −0.471 CI[−1.121,+0.178] ⇒ −12.0 %/gross/年, S −1.33(2× 复利 −22.6%); MID −0.331 ⇒ −9.0, S −0.80; HIGH +1.486 ⇒ +42.2, S +3.12; 动态 LOW −0.012 ⇒ −0.3, S −0.04。
- 敏感性: 未滚动 raw σ_fund p33/p67 = 4.33/12.26(同 `jp_live_caliber_tables.py` L44 做法): 固定 LOW −0.641 ⇒ −16.7, S −1.69(`gap4_sigfund_terciles.out` [sens] 行); members-only σ_fund(切点 5.45/13.67, `gap4_sens2.out`): 固定 LOW −0.786 ⇒ −20.4, S −2.12; Π 固定 −0.855 ⇒ −22.3, S −2.30; 动态 +0.084 ⇒ +3.0, S +0.29。固定席位书 LOW<MID<HIGH 在所有变体成立。
- LOW 档日历(`gap4_sens.out`): 1812/1946 锚在 2024(≥30 锚区块 2024-01-26→04-27(552)、05-02→06-24(319)、07-16→08-13(170)、08-24→09-16(139)、09-18→10-17(176)、10-19→11-10(132)…)+ 134 在 2025(01-17..22, 05-19..29); 月滚动 σ_fund 2024-02..11 = 3.0–6.0 bp vs 2025-10..2026-04 = 16.7–21.1 bp。交叉核: 固定 CAL=log 2024 年均 −0.642(`/workspace/port_w10/probe_artifacts/pod_port_receipts_ex_followup.txt:2`), LOW 档 −0.822 = 2024 去掉少数高 σ_fund 月, 自洽。
- **低档期望, 明说**(用户规则 memory L7 "低 σ_fund 档期望必须说出来"): 在役固定席位书在 LOW 档(30 锚横截面费率离散 ≲5.75 bp, 2024 型)的期望 **≈ −0.8 bps/锚 per NAV = −21~−22 %/gross/年(2× ≈ −35~−45 % NAV/年, maxDD ≈ −37%), Sharpe ≈ −2.2, bootstrap CI 不含 0**, Π 口径同。这比 memory 里的"≈0 至 −8%/年"(来自 CAL=simple jpline 表: 2023+ LOW −7%/S −0.45)差得多——CAL=simple 伪凸性把 LOW 档亏损减半(−0.476 vs −0.822)、把 HIGH 档翻倍(+3.18 vs +1.60)。只有动态席位把 LOW 档保持在 ≈0(+0.1~+0.2, CI 跨 0, S 0.4–0.6), 而那是 E-0902-D/E-0904-F 判定的非实盘席位路径。HIGH 档(2025-11→2026-04 型)撑起整本书: +1.6 bps/锚, +46 %/gross/年, S 3.1–3.2。
- 旧三分位表(AUDIT §3 / memory)的 CAL=simple 污染(**INFERRED**, 强): `jp_universe2_round2.sh` L7 以 `CAL=simple` 启动 uni2 家族; 装置默认 `w10_universe.py` L17 `CAL = os.environ.get("CAL", "simple")`; CAL=log 臂带 `_callog_` 标签(`jp_callog_revalidate.sh` L6/L9), 而 AUDIT §3 用的是 `uni2_F_M7F_fx_s42`/`uni2_N829T400F_fx_s42`(`jp_live_caliber_tables.py` L23); `_F_M7F_fx_` 的确切启动行不在任何入库 runner 里(G2 从 transcript 找到的 06:31:59Z 那次为 `CAL=simple`, §5.3b)⇒ 旧表判为 CAL=simple 是强推断, 未逐位核(臂 npz 在 jpline)。

---

## 6. 真钱对账(2026-08-26 00Z → 09-04 08Z; T-GT `mac_live_reconcile.py` → `live_reconcile_report.json`)

| 量(bps/锚, 52 个窗; 08-26 16Z 空书跳过) | 均值 | sd |
|---|---|---|
| paper Π(1+r)−1 (N,N+4h], w = target_live, Σw·R/Σ\|w\| | +1.957 | 33.40 |
| paper Σ-simple 同窗 | +0.818 | — |
| paper 对数 | −1.751 | — |
| paper Π, venue 对齐窗 (N+20m, N+4h+20m] | +0.669 | — |
| paper Σ-simple, venue 对齐窗 | +0.101 | — |
| **venue twin** Σqty·(mid_{N+4h}−mid_N)/realized_gross(position_readback + anchors.jsonl mid_at_anchor_vector) | **+0.029** | 32.72 |
| funding(income, settlement∈(N,N+4h]) | −1.909 | 0.689 |
| twin + funding | −1.880 | — |

- corr(paper_Π, twin) 0.769; corr(paper_Π_shift, twin) 0.776; corr(paper_Σ, twin) 0.781; corr 差 bootstrap 4000× 95% CI [−0.036, +0.077] ⇒ **书层分辨不了 Σ 与 Π**(名级才分得开); 斜率 twin~paper_Π_shift 0.848(时间错位: 持仓 ~N+44min 读、mid 于 ~N+24min 定价)。
- 实盘书 Σ−Π: −1.14 ± 6.42 bps/锚((N,N+4h]); −0.57 ± 4.96(venue 对齐窗); 对数−Π −3.71 ± 6.67。
- 名级(13,324 持仓名-窗): 缓存 Π_shift vs venue mid 比值 均值 −0.39 bps, std 69.5, corr 0.977。
- **日级**(equity = totalWalletBalance + totalUnrealizedProfit, 扣 TRANSFER): 10 日 corr(ΔequityNet, twin+funding) 0.942, 对 paper+funding 0.876; Σ ΔequityNet −$540.9 vs Σ twin+funding −$1,307.8 vs Σ paper+funding −$1,559.4(缺口来自缺窗日 08-26/08-29/08-30/09-02/09-04 与 09-03 入金 $62,997.81 后 gross ×4 重建)。**四个完整 6 窗日**(08-27/08-28/08-31/09-01)残差 +41.1 / +3.3 / −25.7 / +25.7 USD, Σ +$44.4, 平均 |残差| 6.43 bps of gross/日; venue COMMISSION 当日 −$0.001…−0.008。
- 执行器记账收据(T-LIVE, 数据行): `pilot_log/20260904/daily_nav.jsonl` nav 82963.20 = wallet 83132.79 + unrealised −169.58; realised −26.91 = FUNDING_FEE −79.15 + REALIZED_PNL 52.24 + COMMISSION −0.003; `per_name_stop.json` USELESSUSDT 止于 1788525812(与 nav_ts 同快照)。
- 生产者行对账(T-LIVE/R-C3): 09-04 00Z 锚 king 15.377265684306625 / rev24 21.472903437912468 / fund −16.861735276877877 逐位; gross −11.229 == shadow_log; 通道 0 与 venue 公开 5m K 线 BTC/ETH/DOGE/STAR 48/48 逐位。
- 结论: 实盘 paper(Π)对 venue twin 均值差 −1.93 ± 22.5 bps/锚(venue 对齐窗 −0.50 ± 21.3), 日级 corr 0.94——**记账口径 Π(1+r)−1 与真钱一致; Σ-simple 在书层的偏差(≈−1 bps/锚)淹没在 21–33 bps 的执行噪声里**。
- **carry 对账(G1; 52 窗 08-26 00Z→09-04 08Z, + = 书付, bps/锚 per gross)**。费率仪器三方逐位同: 面板 `f_fund_now`/`f_fund_iv` vs 生产者账本(31 锚 16,132 格 0 差, max 4.47e-10; iv 0 差; 账本无而面板有 4,842 格未核), 账本 vs 场所公开 API(≥08-25 20Z 17,453 共同结算 0 差, 场所少 6 行; 间隔 330 名中 2 名 SCRT/STORJ 账本 4h vs fundingInfo 8h), 装置公式用场所费率 vs 用账本费率 max 差 0(`panel_vs_ledger_2x2.out` L1, `venue_vs_ledger.out`)。

| 量 | 均值 ± se | %/gross/年(×21.9) |
|---|---|---|
| 装置公式 × `target_live` 权重(账本费率; 场所费率逐位同) | +2.343 ± 0.160 | 51.3 |
| 结算规则 Σ w·rate, settlement∈(N,N+4h] × target 权重 | +2.320 ± 0.156 | 50.8 |
| 装置公式 × 实际 readback 名义 | +2.033 ± 0.132 | 44.5 |
| 结算规则 × 实际名义 | +1.975 ± 0.101 | 43.3 |
| **场所实收**(T-GT −funding_usd/realized_gross) | **+1.909 ± 0.096**(sd 0.696; 本节表首的 "0.689" 是 sd, 非 se) | 41.8 |
| 比例计提/陈旧偏差(结算 − 装置, target 权重) | −0.024 ± 0.109 | ≈0 |
| 权重: realized − target(同公式) | −0.311 ± 0.084 | −6.8 |
| **同书公式偏差: 实收 − 装置×realized** | **−0.124 ± 0.093** | −2.7 |
| 实收 − 结算×realized | −0.066 ± 0.067 | −1.4 |
| 实收 − 装置×target | −0.435 ± 0.117 | −9.5 |

  收据 `gap_1/carry_reconcile.py/.out`(逐窗 52 行含 stale/miss 名计数; stale 名均 0.13, miss 0), `carry_reconcile_rows.json`; ×1 期(47 窗, rg<100k): 实收 +1.988, 装置×target +2.483; 重叠 26 窗(08-26 04Z→08-30 20Z): 装置×target +2.229, 实收 +1.977。**读法(VERIFIED)**: 装置的比例计提**不低估** carry; 同仓位下略高估(−0.12, 距 0 约 1.3 se)。
- **既往 carry 数字对账(G1)**: RESULT_caliber_revalidation L64 "回放 0.77" = `pod_live_w3fix_callog_s42` carry_ex 29 锚(08-26 04Z→08-30 20Z)均 +0.774, 每 NAV(gross 0.759 ⇒ 每 gross 1.02)[VERIFIED 复跑; 2×2 用 28 共同锚得 +0.777/+0.774]; "实收 1.98" = −Σfunding_paid/realized_gross 47 个 ×1 窗 = 1.988 / 26 重叠窗 1.977, 每 realized gross [INFERRED, 两位数吻合]; "−1.2 ⇒ +0.457 → −0.7" = 分母混用 + 书混用 ⇒ **作为口径修正 REFUTED**, 正确的书构成差 −1.21/gross(公式偏差 0)。AUDIT §3 行 11 "装置 ≈0.5" = RECEIPT_EX `carry_ex_mean 0.5053` 全史 2022→08-30(port `REPORT.md` L431, 每 NAV)[VERIFIED]; "生产者纸面 2.65" = `shadow_log.jsonl` signal 行 carry_bps/gross_pos 08-26→09-04 = 2.68(每 NAV 2.25; king 链单书)[INFERRED, 2.65 vs 2.68]; "执行实现 1.2" = Σfunding_paid/Σrealized_gross 全 pilot_log 08-01→09-04 194 锚(含 $2k NAV 影子期)= 1.158(sum/sum, 混合书)[INFERRED]; T-GT "−1.909 ± 0.689" = 逐窗均值, income 符号(− = 付), ± 为 sd [VERIFIED]。
- **G1 未决**: ① 哪个 combo 组件(冻结 450 / M1 秩基 / V2MAIN 混 / king 席位)使 carry 暴露翻倍(回放 1.02 vs 实盘 2.23 每 gross); ② 执行器持有的 carry 暴露比 target 少 13%(−0.31 ± 0.08; dust 跳单/止损?)未查; ③ 4,842 个面板格(生产者 524 名账本之外的名)未交叉核。
- **日级样本选择(CRITIC)**: "四个完整 6 窗日"之外, 09-03 亦为 6 窗日但被排除(残差 −219.8 USD; 理由 = $62,997.81 入金后 gross 41k→165k 重建, `gt/live_reconcile_report.json` daily 段), 而 08-27 是入金日(STATE.md L28 "08-27 入金后"; critic 记 $5.4k, 金额本稿未核)仍计入——四日 Σ +$44.4 的"干净"集是有选择的(`critic/CRITIC_NOTES.md`)。

---

## 7. 仍未解决 / 单仪器 / 待复核

| # | 条目 | 状态 | 谁需要做什么 |
|---|---|---|---|
| 1 | v1/v3splice 2020-01-31→2021-12-31 共 4,206 锚 Y4 | 部分核验(R-C1.1 6,316 格; R-C1.2 1,092 锚×6 名, 均 100%); 其余 INFERRED | jpline 恢复后开 hist 缓存全锚逐位 |
| 2 | 产出 v1 的确切脚本调用 | INFERRED(transcript 2026-08-21T02:01Z; pod 无日志) | 接受为谱系记录, 或 jpline 找 panel_hist_v2.log |
| 3 | jpline 原件: `pod_backup_2026-08-21/wide_fea_hist_meta.npz`(w10 在 jpline 读的)、`wide_dl_full.npz`、nets_histv2 收据 | 未开; pod port 用 symlink→v2ext 代替 | 第二仪器复核 §5 全表 |
| 4 | §5 全部数字(含 G2 2022–23 行、G3 最差月、G4 三分位、G6 平移窗) | **[单仪器 pod]**; 三票逐位自复现; G4/G6 单 agent 自跑 + 基线序列与 port 逐位同 | jpline CAL=log 批复跑 |
| 5 | 最差月 | **已解决(VERIFIED, 三票逐位同)**: 固定 CAL=log 2024-11 −717.0 / 2025-01 −634.5 / 2026-08 −252.4(= −8.5/−8.5/−3.3% gross → −16.9/−16.9/−6.6% NAV @2×); 动态 2024-04 −363.1 / 2025-12 −294.5 / 2026-08 −293.5; Π 与旧口径见 §5.1/§5.2 | 原稿"无人计算"为误(critic 抓出): R-C6.0 `recompute_out.txt` L131-134、R-C6.1 `recompute_c6.out` L10、R-C6.2 `REPORT.md` §6/§9.3、`/workspace/port_w10/summarize.py` L16-18、`pod_units_table.py` L13-14(已印 %/gross)、`docs/RESULT_caliber_revalidation_2026-09-04.md` L34-38/L69-75 均已列; 本轮 gap_3 补 Π 口径最差月 + 2× NAV 换算(`worst_months.out`, `pod_units_table_gap3.out`); 仓 `pod_units_table.py` L13-14 已补印 id/bps/2×(未提交) |
| 6 | T3c 与 M1/FTRIM/T400 在 Π(1+r)−1 口径下 | 未重跑 | 用 R-C6.2 `run_alt.sh` 方式加臂 |
| 7 | 动态席位 2024 装置伪影(2022-23 king 腿恒 0 ⇒ msharpe 窗全零) | INFERRED, 未量化 | 用 yearly-OOS king(jpline `slow_pred_hist_oos.npy`)重跑动态臂 |
| 8 | 2026 08-11..08-30 的 120 锚无 F10 预测 | VERIFIED 事实, 影响已分段报 | 报 2026 时注明 ≤08-10 与 →08-30 两段 |
| 9 | 换算配方(比值之均值 vs 均值之比值)| 两读数并列, 未裁定 | 用户定: 报告口径绑定恒定 gross 时应用 mean(net_ex/gross) |
| 10 | F10 同窗 expm1 偏差 2026: −1.68(R-C2.0/1)vs −1.54(R-C2.2) | 两仪器差 0.14, 未对账 | 核锚集是否同(meta 栅格 vs dlw 栅格) |
| 11 | 旧 08-16 bundle 出口脚本原文 | INFERRED(镜像 236a702; 行逐位可重算) | 接受 |
| 12 | `leg_returns_live.json` 行 841-844(4 行, 08-16 12Z→08-17 00Z) | 来源不明, 无 weights 文件 | 可忽略(4/900)或从旧 aux 恢复 |
| 13 | 最后一条追加行的 king/fund 腿 | 不可独立重算(prev_rec 每锚覆盖) | 建议生产者把 prev_rec 按锚存档 |
| 14 | king 特征 train/serve 一根 bar 偏差(训练特征止于 E−1, 实盘含 E; T-LIVE FEA 99.90% vs 2.0%) | 执行行 VERIFIED, 后果 INFERRED 未量化 | 单独预注册 |
| 15 | pod 缓存 ext 段(>08-24 04:00Z)与生产者 NaN 掩码不一致 43.5%(有限格逐位同) | 观察到, 未查因 | 排查 08-24→09-01 尾段 |
| 16 | 08-22 SR 脚本 sha 00fea19e ≠ 结果 JSON 9a8c1cfd; F10 08-22 训练脚本 93cc2cdf ≠ Mac bbd4031d | 产出收据的字节不在仓 | 判官装置同寿命纪律(§8) |
| 17 | E-0904-F 声称的书层 −0.04 bps/锚 偏差 | 无人复跑(T-HIST caveat 3) | 用 §5 数字替换该表述 |
| 18 | 在役书形态(combo/FTRIM/M1/PHI=0.45)是在 CAL=simple 上判定的; **同样: σ_fund gross 阶梯 = 实盘 sizing 乘子(`anchor_loop.py` L1479 `target_leverage = external["gross_mult"] * _g`), 其受据 RESULT_allweather H1 = CAL=simple + 固定席位 W3FIX 0.21/0/0.79(`jp_allweather.py` L32 臂 `uni2_F_M7F_fx_s42`/`uni2_N829T400F_fx_s42` ← `jp_universe2_runner.sh` L13 `CAL=simple … W3FIX=0.21,0,0.79`), 撤回受据(E-0904-D, `jp_allweather_ms.py` L5 臂, 09:5xZ, 早于 E-0904-F)亦为 CAL=simple; 当前 g=1.0(状态文件缺失, 12:24Z anchors 行 `reason: missing`; 仪表盘作业已卸载)⇒ 零行为效应; 受据状态: 双向作废, 直到在 CAL=log/Π 口径重判(pod port `probe_artifacts/` 无 allweather 输出; `jp_callog_revalidate.sh` L8-18 无 `jp_allweather` 步)** | VERIFIED 事实(`combo_stage.py` L3; 阶梯执行行 + anchors 行, G5); 臂文件 CAL INFERRED(jpline 未开) | 用户裁定是否需在 Π 口径重判; 阶梯: 在 CAL=log 臂上重跑 `jp_allweather.py`(固定 + 动态两席位口径)后再决定复活/永久撤回 |
| 19 | 5m 缓存 base 段(2022→2026-08-24)ch0=pct_change | 样本日 2022/2023/2024/2025 逐位 VERIFIED(R-C1.2)+ 平价门 assert(L54); 全段 INFERRED | 接受 |
| 20 | `AUDIT_live_vs_replay` §3 全表 + `RESULT_allweather` §0/§1(含 H1 阶梯录取候选、"2024 −8→+3")| **CAL=simple-stale**: 来源 env `CAL=simple LEGS=101`(`jp_universe2_runner.sh` L13; transcript 06:31:59Z)VERIFIED; jpline 单仪器; 面板止 08-15; 2024 −8% vs 本稿同 env 同口径 pod 复跑 −15.5%, 残差 = king 来源 + 面板谱系, UNRESOLVED(§5.3b) | jpline 恢复后按 runner 模板加 `CAL=log` 重产 `uni2_{F_M7F,F_QF,N400rF,N829T400F}_fx_s42.npz`, 重跑 `jp_live_caliber_tables.py`/`jp_allweather.py`; 两文档横幅先标 stale; memory `feedback_report_live_caliber_full_cycle` 的"先查 AUDIT §3"改指本稿 §5 |
| 21 | 在役形态 2022–23 与 2020–21 逐年数字(用户规则要求 2021–2026 全表) | 2022–23 只有 fund-only 书(king 腿恒 0 / F10 0%·22.6% 覆盖, §5.1/§5.2 标注行, VERIFIED); 在役 combo 形态需 jpline `slow_pred_hist_oos.npy` + F10 2022–23 折, 今日 UNAVAILABLE; 2020–21 pod 无任何模型分数(仅 v1 面板), UNAVAILABLE | jpline 恢复: 用年折外 king 重跑 §5 两表 2022–23; F10 2022–23 折需训练 → 单独预注册; 2020–21 需 king/F10 训练覆盖, 否则永久标 UNAVAILABLE |
| 22 | pod 臂 B 同构 vs jpline 臂 B 的逐年残差(2024 −15.5% vs −8%, 2023 −12.3% vs −1%, Sharpe 差 0.4–0.8) | 观察到, 变量只剩 king 来源与面板谱系, 未分离 | jpline 恢复后: 同 env 在 jpline 跑 `SLOW_NPY=slow_pred_pinned.npy`(king 单变量), 再换面板 |
| 23 | 口径链上无门的环节(G5): (a) bundle 出口 `/workspace/pod_export_bundle_v3.py` L109 的 leg_returns 口径——pod 无任何测试(`ls /workspace/*test*` 空), 仅 `pod_guard_reconcile.py` L40 同式重算作诊断; (b) `combo_stage.py` L29-34 msharpe 输入 `state/leg_returns_live.json`——无测试断言其行口径或其 w3 == 生产者 w3(仅 tracer T-LIVE 一次性重算); (c) 生产者测试 `tests_target_live_output.py` [10b] L281-282 只 grep `st.LR[leg].append(` 一行(L439), 对 L428-431 的 `seg/y4v` 变换盲; [10d] L288-289 仅 WARN 不 FAIL; (d) 执行器 `tests_sigma_ladder.py` L21-38 13 项只证 evaluate/load 合约与 `2.0×0.5`, `ops/gate_coverage.py` L222 未声明盲区——阶梯的受据口径不在任何电池可见范围; (e) `regime_dash.py` L121 / `beta_alpha_attrib.py` L11 无测试; 执行器全仓 `grep -rln 'expm1\|log1p'` 为空 | VERIFIED(grep 收据 `gap_5/GAP5_closure.md` §A5) | 三件套登记(测试 + SUITES + 盲区字典): 出口/合并阶段加"从 5m 缓存重算 ≥30 行逐位 == leg_returns"断言; gate_coverage L222 补盲区句 |
| 24 | σ_fund gross 阶梯本身的裁定(录取 H1 与撤回 E-0904-D 双向作废后无有效受据) | UNRESOLVED(G5); 今日无 CAL=log/Π 复跑存在 | jpline 恢复: CAL=log 重产 `uni2_*_fx/_ms` 臂 → `jp_allweather.py` + `jp_allweather_ms.py`; 或 pod 上用 R-C6.2 `run_alt.sh` 方式加阶梯臂 |
| 25 | 在役 combo 形态的**全史 carry**(实盘目标书比回放书多付 +1.21 ± 0.17 bps/锚 per gross, 仅 28 锚; 若全史如此固定表头 +0.457 → ≈ −0.5) | INFERRED(G1, 单 regime); 组件归因(冻结 450 / M1 秩基 / V2MAIN 混 / king 席位)未做 | 把 combo 书(FTRIM/M1/φ0.45)本身过面板 `f_fund_now`×4h/iv 全史; 逐组件 ablation 看 carry 暴露 |
| 26 | 执行器持有的 carry 暴露比 target 少 13%(realized − target 同公式 −0.311 ± 0.084 bps/锚 per gross) | 观察到(G1 `carry_reconcile.out`), 原因未查(dust 跳单/止损?) | 对 readback vs target 名级差做归因 |
| 27 | 面板 `f_fund_now` 在生产者 524 名账本之外的 4,842 格 | 未交叉核(G1 `panel_vs_ledger_2x2.out` L1 `ledger-None-but-panel-has 4842`) | 用场所公开 API 补核 |
| 28 | G1 汇报的执行器三项检查(`funding.jsonl` 27,660 行符号/比值 0.9993; 费率 vs 账本 13,028 行 0 差) | 数字只在 G1 汇报正文, `gap_1/` 无落盘输出 | 重跑落盘到 `gap_1/`, 否则维持 INFERRED(汇报) |
| 29 | 执行器读取时点: `config/book.json` L153 `anchor_offset_min: 24`(08-27 起)vs STATE.md L30 / CLAUDE.md "N+23" | 盘上配置 VERIFIED(G6); 运行中进程取值 INFERRED | 改 STATE/CLAUDE 抄字段值; 运行中进程用 anchors.jsonl 读取时刻核 |
| 30 | 执行保真 −0.3 bps of gross/锚(AUDIT L10 12 锚: −240U vs −333U 含费 37U) | 引用值, 未重估(G6 明示 INFERRED); §5.3 扣减链依赖它 | 在更长实盘样本上按同定义(纸面孪生 vs 执行, 扣费)重估后再入表头 |
| 31 | 09-04 种子口径两票收据形态不同: R-C3.0 `pod_withdrawn.py` rev24 行 833/950 逐位 == expm1 重算 vs R-C3.1 `pod_f_seed_replicate.py` L29 复制品 exact 0/950(标签靠 `jp_build_oos_seed.py` L19 代码行) | 未互相对账(CRITIC) | 两复制品同锚集同面板重跑一次, 报 n_eq / max\|Δ\| |
| 32 | 旧 σ_fund 三分位表 / AUDIT §3 的 CAL=simple 判定 | INFERRED(G4/G2: runner `CAL=simple` + 装置默认 + 标签命名 + transcript 06:31:59Z 启动行; `_F_M7F_fx_` 无入库 runner) | jpline 恢复开臂 npz 读 CONFIG 自报 |
| 33 | 陈旧规则/记忆指针: `STATE.md` L53 "收益一律简单口径(expm1…)"; memory `feedback_report_live_caliber_full_cycle` L7 "引用前先查 AUDIT §3 表"与"低 σ_fund 档期望 ≈0 至 −8%/年"(均来自 CAL=simple 表) | VERIFIED 文本(CRITIC / G2 / G4) | 改指本稿 §5.1/§5.2/§5.7; STATE L53 与 CLAUDE.md L28 同步改(§8 规则 1) |
| 34 | T-GT 日级"四个干净 6 窗日"的样本选择(09-03 6 窗 −219.8 被排除, 08-27 入金日计入) | 观察到(CRITIC; `gt/live_reconcile_report.json` daily 段) | 报法改为全部 6 窗日 + 排除理由逐日列出 |
| 35 | maxDD 换算分母(三年 gross 0.791 → 66% @2× vs 2024 gross 0.847 → 61.7% vs 恒定 gross cumsum 3155 → 63.1%; 均非复利) | 三读数并列(CRITIC / R-C6.2 / R-C6.0), 未裁定 | 用户定报法; 建议与 §7 #9 一起定为恒定 gross 口径 |
| 36 | G6 平移臂丢弃最后一锚 2026-08-30 20:00(5m 末段 NaN, n<46; 基线该锚 net_ex −9.23)⇒ 2026 n=1451 / 2024on n=5837 | VERIFIED 事实(`paired_delta.out` 末行); 配对统计只用共同锚 | 报平移窗数字时注明 |
| 37 | G6 机理("装置书 EMA 持仓 ⇒ 平移只影响 10% 增量")与 G3 的 newprod/newsum ↔ Π/只换窗列对应(按年均值匹配, 未开 `build_alt_meta.py`) | INFERRED | 前者可用"每锚全量重建"臂对照实测; 后者开 `refute_C6_2/altrun/build_alt_meta.py` 核 |
| 38 | critic 残余风险 3 的"cost model (COST_B) far below the re-audited 3.52 bps line" | 未派发缺口, 本轮未核(§10) | 单独对账 `w10_universe.py` 成本行与 `turnover_cost_reaudit_2026_08_21` 受据 |

---

## 8. 规则(防复发, 绑定到具体文件)

1. **口径规则绑定面板文件, 不绑定变量名。** `CLAUDE.md` L28 "一律简单收益口径(expm1)"改为: "expm1 只施于 `multi_asset/data/build_wide_dl.py` L151 谱系(对数面板 wide_dl*.npz); pod 5m 缓存谱系(`pod_panel_ext.py` L58 / `pod_fea_ext.py` L34 / `pod_dlw_targets_ext.py` L96)的 y4 是 Σ-simple, 禁 expm1; 记账口径 = `pod_dlw_targets_ext.py` L93 的 y4s"。同步改 ERROR_LEDGER E-0826-C L214 与 L397, 以及 `STATE.md` L53 "收益一律简单口径(expm1; …)"(CRITIC: 原稿只改 CLAUDE.md/ledger 而漏 STATE)。
2. **装置自报口径且断言输入谱系。** `w10_universe.py` 在 L48 读 y4 后加自检: 抽 ≥30 锚, 从 5m 缓存重算 Σ-simple[E,E+47] 与 Π[E+1,E+48], 断言 y4 逐位等于其一, 并把命中的定义写进 `_CFG`; CAL 白名单改为 `{"sum_simple","compound"}`, 删除 `"simple"→expm1` 分支(或仅对断言为对数的输入放行)。
3. **窗口是定义的一部分。** 所有 y4 产物在 npz meta_json 写 `window_rows`(`[E,E+47]` / `[E+1,E+48]`)与 `caliber`(`sum_simple` / `compound` / `log`); `pod_export_bundle_v3.py` L165 与 `shadow_loop_v3.py` L237-239 写 leg_returns 时附同字段; 席位窗混两种窗要在 `combo_stage.py` msharpe 前记录比例。
4. **"逐位"只能指 uint32/float32 逐位。** 禁止把 `share<1e-6`(`pod_panel_lineage.py` L25)或 `<1e-5`(E-0904-F ②)写成"逐位"; 收据须报 n_cells、n_neq、max|Δ|、NaN 模式。
5. **书层数字必报双口径 + 双配方。** 任何回放表(§5 格式)同时给 Σ-simple 与 Π(1+r)−1 (E,E+4h], 换算同时给 mean/mean 与 mean(ratio); 2026 分段报 ≤08-10 与 →08-30; 负年份显式。`pod_units_table.py` L10-11 加第二配方列。
6. **判官装置同寿命**: 产出结果 JSON 的脚本字节必须入库(`inrole_simple_return_rerun.py` 00fea19e≠9a8c1cfd, `base_f10_train_pod.py` bbd4031d≠93cc2cdf 是两例); 结果 JSON 的 self_sha256 与仓内文件 sha 不等即判"收据不可复现"。
7. **参照平价门不得被路由绕过。** `w10_universe.py` L325-334 的 nets_histv2 断言在 LEGS=101 下失效且 stub 文件 144 字节仍打印 NOTE——改为 stub/缺参照即硬失败, 或显式 `REF=none` 并写进 `_CFG`。
8. **种子/席位历史换入需三门**: 口径断言(与 `shadow_loop_v3.py` L430 同公式重算 ≥30 行逐位)、模型一致(king 来源 sha == 在役 booster)、覆盖到最近锚; 任一不过禁写 `state/leg_returns_live.json`。09-04 种子三门全红。**同规则适用于 `combo_stage.py` L29 的读端与 `pod_export_bundle_v3.py` L109 的出口: 无逐位重算断言即为盲区(§7 #23, G5)。**
9. **新结论与既有受据反向先对账**: E-0904-F 断言"nets_histv2 同法"与 `pod_stop_arms_v3.py` L38/L76 反向, 本轮才发现; 以后 ledger 条目引用他装置口径必须附该装置的执行行。
10. **单仪器标注**: jpline 不可达期间产出的所有数字在文档和 STATE 横幅带 `[单仪器 pod]` 标签, jpline 恢复后 §7 #3/#4 逐项清除; G4 三分位与 G6 平移窗数字同标。
11. **受据臂的口径必须从臂文件 CONFIG 自报读出并写进裁定文档。** 阶梯 H1 录取与 E-0904-D 撤回两次裁定都没写臂的 CAL, 今日只能从 runner 推断(G5, §7 #32); 以后任何以 w10 系列 npz 为受据的裁定附该 npz 的 `CONFIG` 行原文(CAL / W3FIX / LEGS / MEMBERS_TOPN / FTRIM)。
12. **carry 对账必须同书同分母。** 回放 carry_ex(每 NAV)与实盘 −funding/realized_gross(每 gross)并列前先换到同一分母、同一持仓(G1 的 2×2 表格式: 权重 × 费率来源两轴); 两书之差不得写成口径修正(RESULT_caliber_revalidation L64 "−1.2"即此错)。
13. **书层执行时点折扣以持仓连续的装置实测为准**(G6 平移窗方法: 5m 缓存重建 [E+6,E+53] 的 y4 override, 同装置重跑, 配对 Δ 报 SE/t); 腿级或"每锚全量重建"代理书的衰减数字(`pod_alpha_decay.py`)不得直接当书层折扣; 执行保真扣减(−0.3)入表头前须在更长实盘样本上按同定义重估(§7 #30)。
14. **时点常数以 `dl_quant_live/config/book.json` `anchor_offset_min` 为唯一真相**, STATE/CLAUDE 引用时抄字段值并附改动日期(现值 24, 08-27 起; §7 #29)。

---

## 9. 缺口审查与补证

critic(`critic/CRITIC_NOTES.md`)对草稿做完整性审查后派发 6 个缺口, 各由一位 gap-filler 在 read-only 约束下补证(jpline 各试一次 `ssh -o ConnectTimeout=8 jpline` → `Operation timed out`; 全部 pod 写入限于 `/workspace/review_scratch/gap_*/`, Mac 写入限于 `review_caliber/gap_*/`; 无实盘系统/launchd/GPU 触碰)。每个缺口: 原稿状态 → 装置与收据 → 结果 → 标签变化 → 仍开口。

| 缺口 | 原稿状态(critic 指摘) | 补证装置与收据 | 结果 | 标签变化 | 仍开口(→ §7) |
|---|---|---|---|---|---|
| **G1 carry 腿口径** | §6 只列实盘 funding −1.909 ± 0.689, 未与回放 carry 对账; critic 残余风险 1 称回放低估 ≈1.0–1.2 bps/锚 ⇒ 固定表头翻号 | `gap_1/carry_reconcile.py/.out/_rows.json`(52 窗重算, 账本费率), `venue_pull.py` + `venue_funding_rates.json`(330 名公开 API), `venue_vs_ledger.py/.out`, `pod_extract.py` → `panel_fund_tail.npz` + `replay_tail_rows.json`(pod 只读), `panel_vs_ledger_2x2.py/.out`; 执行行 §2 四行 | 费率三仪器逐位同; 装置比例计提 vs 场所实收**同书** −0.12 ± 0.09 bps/锚 per gross ⇒ 口径无错; "0.77 vs 1.98 ⇒ −1.2"是分母混用(每 NAV vs 每 gross)+ 书混用(回放书 vs 实盘 combo 书), 重归因为**书构成差 +1.21 ± 0.17/gross**(28 锚) | 装置 carry: VERIFIED 无错; "−1.2 口径修正": **REFUTED**; 书构成差: INFERRED(单 regime); §5.1/§5.2 扣减 0.00 | #25 全史 combo carry 与组件归因; #26 执行器 −13% 暴露; #27 4,842 格; #28 执行器三项检查无落盘输出 |
| **G2 2022–23 行 + AUDIT §3 对账** | 用户规则要求 2021–2026 逐年表, 草稿只有 2024–26; AUDIT §3 2024 −8% vs §5.3 −33% 未对账 | `gap_2/pod_gap2_stats.py` → `gap2_stats.json`(覆盖率/n/S/maxDD/gross/w3_king, 复得 2024–26 既有格逐位同), `pod_gap2_worstmonth.py` → `gap2_worstmonth.json`, `pod_gap2_armB.sh`(env 逐字 `commands.txt`)+ `pod_gap2_auditformula.py` → `gap2_auditformula.json`, `scan_transcript_m7f.py` → `transcript_L211811_armC.txt`; 已写入 §5 首段、§5.1/§5.2 行、§5.3b、§7 #20-22 | 2022–23 行给出(双口径 + 最差月), 但 king 腿恒 0(pinned 2022–23 NaN)/ F10 0%·22.6% 覆盖 ⇒ fund-only 书, **非在役形态**; AUDIT §3 臂 C = `CAL=simple LEGS=101`(非 111)jpline 单仪器, 公式为每 NAV 复利不除 gross; 2024 −33 → −25.6(换算)→ −15.8(口径)→ −15.5(形态)→ −8(jpline 残差) | 2022–23 数字 VERIFIED(pod); AUDIT 来源/env/公式 VERIFIED; AUDIT §3 与 RESULT_allweather 标 **CAL=simple-stale**; jpline 残差 UNRESOLVED | #21 在役 combo 2022–23(需 jpline 年折外 king + F10 折), 2020–21 UNAVAILABLE; #22 king 来源 vs 面板谱系分离; #20 四臂 CAL=log 重产 |
| **G3 最差月** | §5.1 写"UNRESOLVED——无任何 tracer/refuter 计算月度序列" | 五个既有产出者(R-C6.0 `recompute_out.txt` L131-134/L136-139/L111-114, R-C6.1 `recompute_c6.out` L10/L6, R-C6.2 `REPORT.md` §9.3/§6, `/workspace/port_w10/summarize.py` L16-18, `pod_units_table.py` L13-14, `docs/RESULT_caliber_revalidation` L34-38/L69-75)+ `gap_3/worst_months.py`(34 序列)→ `worst_months.out/.json`, `pod_units_table_gap3.py/.out`, 仓 `pod_units_table.py` L13-15 补印 id/bps/2×(未提交; diff `pod_units_table.gap3.diff`, 复跑 `pod_units_table.repo.out` 逐字同) | 原稿声明为误; 固定 2024-11 −717 / 2025-01 −634.5 / 2026-08 −252.4(三年 −9.07%/gross → −18.1% NAV @2×); Π −756.8/−574.9/−238.0(−19.2%); 动态 −363.1/−294.5/−293.5(−11.7%); 固定书 2024-11/12、2025-01 连续三月 −717/−616/−635 | UNRESOLVED → **VERIFIED**(三票逐位同; Π 列两组 npz 逐位同) | 无实质开口; #37 newprod/newsum ↔ Π/只换窗列对应按年均值匹配(INFERRED 一项) |
| **G4 σ_fund 三分位** | 用户规则要求 regime 分档, 草稿无; memory "低档 ≈0 至 −8%/年"来自 CAL=simple 表 | `gap_4/gap4_sigfund_terciles.py` → `.out/.json`(pod 执行, `GAP4_DONE`), `gap4_sens.py` → `gap4_sens.out`/`gap4_sens2.out`; 执行行 `jp_allweather.py` L15-16/L40, `w10_universe.py` pnl_r/gt 行 | 固定席位 LOW 档 −0.822 CI[−1.589,−0.114] ⇒ −21~−22 %/gross/年(2× −35~−45%), S −2.2, Π 同; 动态 LOW ≈0(+0.1~+0.2, CI 跨 0); HIGH +1.6 ⇒ +46%, S 3.1–3.2; CAL=simple 把 LOW 亏损减半、HIGH 翻倍 | 新增 §5.7 VERIFIED(脚本打印); 旧表 CAL=simple 污染 INFERRED; memory 低档期望句作废(#33) | #32 旧表 CONFIG 自报; jpline 第二仪器(#4) |
| **G5 阶梯 / 仪表盘 / 测试盲区** | 09-04 09:34Z 上线的 σ_fund gross 阶梯(执行器 sizing)、regime 仪表盘、β/α 拆分与各电池的口径覆盖不在 §2/§7 | `gap_5/GAP5_closure.md` §A1-A5(执行行 + `launchctl list` + anchors.jsonl 12:24Z 行 + 只读 import `SL.load()` + grep), `receipts_computed.txt`; 已写入 §2 三行、§7 #18 改写、#23 新增、§8 规则 8 补句 | 阶梯 g=1.0 零行为效应(状态文件缺失); 状态输入是费率离散非收益 ⇒ 口径暴露全在受据; 录取 H1 与撤回 E-0904-D 都是 CAL=simple + W3FIX ⇒ **双向作废**; 仪表盘 L121 钱口径、β/α L11 Π 口径均正确; 五处无门 | 行为/执行行 VERIFIED; 臂 npz CAL INFERRED | #24 阶梯裁定需 CAL=log 复跑; #23 三件套登记 |
| **G6 执行时点衰减 + 扣减链** | 草稿引用"全史执行时点衰减 5–10%"(腿级装置 `pod_alpha_decay`), 书层未测; §5.3 无保真/carry 扣减行 | `gap_6/build_shift_meta.py/.out`(平价: shiftprod vs `pod_alpha_decay.py` y4s_shift 3,374,223 格逐位; newprod vs R-C6.2 3,446,600 格逐位), `run_shift.sh/.out`(6 跑 CMD 逐字, 装置 sha 64c70a44), `final_stats_gap6.py/.out/.json`(基线 vs port `array_equal True`), `paired_delta.py/.out`, `section_5_3_patch.md`; 执行器 `book.json` L153/L163, `external_book.py` L132/L220 | 书层平移 25 分钟折 2–4%(固定; Π −0.0176 / Σ −0.0102), 配对 t −0.14, 逐年 \|t\| ≤ 0.38 ⇒ 与 0 不可分; §5 不需再打 5–10% 折; 扣 −0.3 后固定 2024→26 Π +0.1938/gross(2× +8.5%; 2024 −1.14 ⇒ 2× −50%), 动态 +0.7913(2× +34.7%); 执行器实为 N+24 非 N+23 | "5–10% 书层折" **REFUTED**(书层); 平移数字 VERIFIED; 机理 INFERRED; −0.3 INFERRED(引用 12 锚) | #30 −0.3 重估; #29 STATE/CLAUDE N+23 陈旧 + 运行中取值; #36 平移臂丢最后一锚; #37 机理 |

**critic 其他指摘(未派发缺口)的处置**: (a) R-C2.2 书层 1.49 vs 0.79 是列 `net`/臂 S0 → §4 C2 第 4 点加标签; (b) R-C3.0 833/950 vs R-C3.1 0/950 → §4 C3 注 + §7 #31 开口; (c) T-GT 日级"四个干净日"选择 → §6 注 + §7 #34; (d) STATE.md L53 仍是 expm1 规则 → §8 规则 1 + §7 #33; (e) maxDD 分母混用 → §5.3 注 + §7 #35; (f) 残余风险 3 的 COST_B → 未核, §7 #38。

**并行核查, 本版未整合**: `review_caliber/combo_recheck/`(REPORT.md)、`gap_live_pnl/`(canon_report.json)、`gap_units/`(REPORT.md)由同会话其他 agent 产出, 不在本稿输入内, 本稿未读其结论; 若其与 §5/§6 数字冲突, 以后续对账为准, 本稿不预判。

**标签总结(补证后)**: 新增 VERIFIED——G1 装置 carry 无错、G2 2022–23 行与 AUDIT 来源、G3 最差月、G4 三分位、G5 阶梯行为与仪表盘口径、G6 平移窗数字; 新增 REFUTED——"回放低估 carry 1.0–1.2 ⇒ 表头翻号"(作为口径修正)、"书层执行时点折 5–10%"; 新增 INFERRED——书构成 carry 差(28 锚)、旧表/臂 CAL=simple、G6 机理、−0.3 保真值; 仍 UNRESOLVED——全史 combo carry、阶梯裁定、jpline vs pod 残差、在役 combo 2022–23、T3c/孤立臂 Π 口径(#6)、动态 2024 伪影量化(#7)、换算配方(#9)。

---

## 10. 残余风险(critic 原文, 逐字)

以下三条为 critic 在草稿阶段给出的残余风险, **原文逐字保留**; 每条之后附本稿补证后的状态(不删、不改写原文)。

1. > Carry leg: the replay accrues funding pro-rata (w10 L280) and under-charges it by ≈1.0–1.2 bps/anchor versus live settlement accounting (RESULT_caliber_revalidation L64: 0.77 vs 1.98 on 27 anchors; T-GT live −1.91 bps/anchor). Applied to the §5 fixed-seat headline (+0.457 bps/anchor, +12.6%/gross) this flips the sign (≈ −0.7 bps/anchor), so the 'positive expectation under the correct caliber' conclusion can reverse once the funding caliber is traced.

   **补证后状态(G1)**: "回放比例计提低估 1.0–1.2"作为**口径**陈述被驳——同书(执行器 readback 名义)52 窗装置计提比实收高 0.12 ± 0.09 bps/锚 per gross, 结算规则 vs 比例计提差 −0.02 ± 0.11; 0.77 与 1.98 分母不同(每 NAV vs 每 gross)且书不同(§5.1, §6)。**但表头翻号的可能性没有消失, 只是原因换了**: 实盘 combo 目标书比回放书多付 carry +1.21 ± 0.17/gross(28 锚, 单 regime, INFERRED), 若全史如此固定表头 +0.457 → ≈ −0.5——在役 combo 形态的全史 carry 未测(§7 #25), "正确口径下期望为正"仍不能宣称。

2. > Single instrument and stand-in inputs: every §5 number comes from the pod port reading /workspace/data/wide_fea_v2ext_meta.npz through a symlink named wide_fea_hist_meta.npz, F10 preds from a script whose bytes are not in the repo, and king preds that are NaN before 2024; the jpline files that produced all previously documented numbers (pod_backup_2026-08-21 meta, yearly-OOS king, 2020–23 coverage) were never opened today. A jpline rerun that differs by >0.05 bps/anchor (the RESULT doc's own void threshold, already exceeded by the Σ-vs-Π 2024 gap of 0.067) voids §5.

   **补证后状态**: 未消除, 反而加重——G2 证实 pod 上 18 个 `slow_pred_hist_oos.npy` 全是 → `slow_pred_pinned.npy` 的符号链接(无一年折外件), 且同 env 同口径下 pod 臂 B 同构 2024 −15.5%/S −0.91 vs jpline 臂 B −8%/S −0.42, 残差只剩 king 来源与面板谱系两个变量, 今日不可分离(§5.3b, §7 #22); G4/G6 新增数字同为单仪器(§7 #4)。jpline 恢复前 §5 全表维持 [单仪器 pod] 标签, 作废条件不变。

3. > Replay form ≠ live book: F10 fold models instead of the live refit, 120 anchors of 2026 with no F10 leg (averaging −3.5 bps/anchor), dynamic-seat 2024 artefact from the zero king window, unquantified one-bar train/serve feature skew (features through E live vs E−1 in training), holding window (N,N+4h] vs live (N+23m,…] with 5–10% alpha decay, and a cost model (COST_B) far below the re-audited 3.52 bps line — any of these can move the fixed-seat 2024→26 mean (+0.46) by more than its own magnitude.

   **补证后状态**: 部分收窄。(i) 持仓窗/alpha 衰减: G6 实测书层平移 25 分钟折 2–4%, 配对 t −0.14, 与 0 不可分——"5–10%"在书层不成立(VERIFIED); 执行器实为 N+24(§7 #29); 剩余系统性折扣是 −0.3 保真(引用值, #30)。(ii) 120 锚无 F10: 已分段报 ≤08-10 / →08-30(§5.1/§5.2)。(iii) 动态 2024 伪影: 仍 INFERRED 未量化(#7)。(iv) 一根 bar train/serve 偏差: 仍未量化(#14)。(v) F10 折模型 vs 在役 refit: 未派发, 开口。(vi) COST_B vs 3.52 bps 成本线: 未派发, 本轮未核(#38)。(vii) 新增: 书构成 carry 差(#25)是又一条同量级的未定项。结论: "任一项都可能移动 +0.46 超过其自身量级"在 (iii)(iv)(v)(vi)(vii) 上仍成立。
