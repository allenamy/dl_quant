> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 冻结 — 本文在计算任何收益之前写定 | **作废条件:** 出现比 v4 更新且逐门验过的链; 或 E-0911-D 仪器天花板被修

# PREREG r12 · 在役书的 regime 分区规则(先于数字冻结)

## §0 为什么要有这一份
十一轮把「夏普显著大于 3.0」当作**合并样本**的问题回答。用户问的是**不同 regime 下**。这是两个问题。
本文只做一件事: **在看任何收益之前**, 把分区规则、窗口、统计量、判读标准写死。

## §1 仪器(全部 VERIFIED, 本机重算)

| 项 | 值 |
|---|---|
| 书序列 | `r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz` sha256 `352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339` |
| 产它的装置 | `trackA/w10_sleeve.py` sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650` = PIN 指定 |
| 形态 | `PHI=0.45 LEGS=101 WRULE=msharpe LOOK=900 UMASK_SCOPE=m1 W3FIX=None CAL=log FTRIM=zero` = 在役动态席位形态 |
| 成本 | `costb_PWR_G230k.json` K=0.17 α=0.87 (FITTED) |
| 自检 | post-warm(丢前 900)∩ ts≤2026-08-30 20Z ⇒ **n=9138, mean g=+0.6341957, Sharpe=1.2912234** 与收口判决 §7 / r11 §1.1 **逐位一致** |
| 换手口径自检(约束 5a) | RAW `turnover` 均 **0.03032**, 均 `gross_total` **0.6956**, 匹配口径 `turnover/gross_total` 均 **0.0540270**;`cost/gross_total ÷ turnover/gross_total = 3.0999`。若误用 RAW 分母会读成 4.456 = ×1.4375 错误 |
| regime 原料 | pod2 `dev_v4/pod_backup_2026-08-21/{wide_fea_hist_meta.npz -> meta_newprod_v4.npz, wide_panel_4h_hist_v2.npz}` + `masks/umask_UPIT_CRYPTO.npz` — 与书本身读的是**同一批文件**(装置源码 L?? 逐行读出) |

## §2 ★ 已作废的旧 regime 表(必须说清, 否则会被重复使用)
`regime_anchor_table_v4holefix_2022_2026-08.csv` 由 `devices_uplift_pod_regime.py` 产出。逐行读该脚本:
`xs_mean_bps / disp_bps / btc_bps / altmbtc_bps / comov / breadth_pos` 全部由 **`y4[i, m]`** 算出 ——
那是锚 i **向前** 4 小时的实现收益, 即书正在持仓的那个窗口本身。**这些列不是因果的**, 用它们切分 = 用结果切分结果。
本轮**不用**该表的任何收益类列。可用的只有 `fund_*`(锚上已结算费率)、`share_new90 / med_age_d`。
⇒ 本轮**自建**因果表。

## §3 因果原语(只用 k ≤ i−1 的窗口)
锚网格 = v4 meta `E_ts`(10182)。`m_i` = `members[i]` ∩ CRYPTO-m1 掩码(与书同源)。`r_k = y4[k, m_k]` 有限值。
`r_k` 覆盖 `[E_ts[k], E_ts[k]+4h]`, 在 `E_ts[k+1]` 收盘 ⇒ **对锚 i 只有 k ≤ i−1 可用**。

- `A_k = mean(r_k)` 全宇宙等权收益
- `B_k = mean(r_k > 0)` 宽度
- `D_k = 1e4 × popsd(r_k)` 截面离散(bps)
- 锚上直读(因果, 费率在锚时已结算): `rn8_{i,j} = f_fund_now[row(E_ts[i]), j] × 8 / f_fund_iv`
  - `SIGF_i = 1e4 × popsd(rn8 over finite ∩ masked members)` ← **第八轮用的同一口径**(该轮已验与实盘 gauge maxabs 0.0 / 9138 锚)
  - `FMED_i = 1e4 × median(同一集合)`
- 书自身的事前空头 carry(锚上已知: 权重来自工件 `W`, 费率来自面板同一行):
  `SPAY_i = 1e4 × Σ_{j: w_ij<0} w_ij · rn8_ij · (4/8) / gross_total_i` — **正 = 空头半区在付钱**

## §4 分区(五族, 全部冻结于此)

| 族 | 规则 | 单元 |
|---|---|---|
| **(a) YEAR** | `E_ts` 的 UTC 年 | 2022 / 2023 / 2024 / 2025 / 2026 |
| **(b) BREADTH** | `BRD6_i = mean_{k=i−6..i−1} B_k`(过去 24h 宽度)| 三分位 T1(最窄)/T2/T3(最宽) |
| **(c) XSVOL** | `XSV30_i = mean_{k=i−30..i−1} D_k`(过去 5 日截面离散, bps)| 三分位 T1/T2/T3。伴随 `MV30_i = 1e4 × sd_{k=i−30..i−1}(A_k)` 同样切三分位 |
| **(d) SIGF** | `SIGF_i` | 三分位 T1(最低)/T2/T3 |
| **(e) EVENT** | `R24_i = Σ_{k=i−6..i−1} A_k`; `R72_i = Σ_{k=i−18..i−1} A_k` | 见下 |

**(e) 事件窗(互相重叠, 每条与其补集成对报告):**
- `POSTCRASH`: `R24_i ≤ −0.02`
- `BROADRALLY`: `R24_i ≥ +0.02` **且** `BRD6_i ≥ 0.60`
- `ALTSURGE`: `R72_i ≥ +0.08` ← 用户说的「山寨币暴涨」**之后**的那些锚; 回调是我们向前测的结果
- `ALTSURGE_BROAD`: `ALTSURGE` 且 `BRD6_i ≥ 0.60`
- `DEEPNEG_MKT`: `FMED_i` 落在本窗最低十分位(全市场费率深负)
- `DEEPNEG_SHORT`: `SPAY_i` 落在本窗**最高**十分位(书的空头半区事前付费最多)

**阈值来源(必须声明, 免得事后被当成 p-hacking)**: −2% / +2% / 0.60 与本仓既有 `regime_part3_2026-09-11.py` 的实盘分区规则同构(该脚本用 24h ≤ −2%、宽度 0.65);+8%/72h 是「暴涨」的新阈, 无先例, 因此**另报 R72 的五分位阶梯**, 使结论不挂在单一阈值上。十分位用于两条 carry 态是免阈值选择的做法。

**分位切点**: 在分析窗自身分布上切(全样本切点)。这是**描述**在役书, 不是可交易规则, 所以全样本切点合法 —— 但 BREADTH 一族**另报**一条「扩张窗因果切点」(只用 i 之前的历史定切点)的对照, 证明分区不是靠切点存活。

## §5 两个分析窗(★ 不可混用)
- `W_ALPHA` = 丢前 900 锚(E-0911-A)∩ `ts ≤ 2026-08-30 20Z`(E-0911-D)⇒ **n=9138**。
  **只有** mean g / CI / Sharpe / 换手 / 腿归因 用它。
- `W_TAIL` = `ts ≤ 2026-08-30 20Z`, **不丢暖机** ⇒ **n=10038**。
  **所有** maxDD / 最差日 / 止损线频率 用它 —— 丢前 900 会丢掉全样本最差日 2022-06-07 −11.1714%(约束 4)。

## §6 统计量与判读
- `g = net_ex / gross_total`, bps/锚/单位 gross。
- CI95(mean g): **UTC 日块自举 2000 次**, `numpy.default_rng([20260905, k])`, 抽该单元覆盖的 UTC 日(有放回), 每个被抽中的日取该日落在单元内的锚。
- `Sharpe_ann = mean/sd(ddof=1) × sqrt(2190)`; `SE = sqrt(2190 / n_cell)`; CI95 = ±1.96·SE。**单元小 ⇒ CI 必宽, 每格都要把 SE 印出来。**
- 日收益(2.0× NAV): `r_day = Π_{锚∈日} (1 + 2.0 · g_a · 1e-4) − 1`。HALT 线 = `≤ −4.00%`, ALERT = `≤ −2.68%`。
- 单元的日级统计: 一个 UTC 日归属某单元当且仅当该日 **≥4/6** 个锚在该单元内; 不满足的日计入 `mixed` 并单列。
- 单元 maxDD = 把该单元的锚按时间顺序**串接**后的权益曲线峰谷(已 prepend 起点, E-0909-C)。
  **这是 regime 条件下的回撤, 不是可交易回撤**(书在单元外并非空仓) —— 引用必须带这句。
- **主问题**: 有多少单元 Sharpe 点估计 > 3.0; 有多少单元 CI95 下界 > 3.0。

## §7 成本口径(约束 5)
本轮**不给任何新构造定价**, 所以不涉及边际换手。但凡报换手一律用 `turnover/gross_total`(匹配口径),
并在产物里同时印 RAW 与匹配值以及二者之比 1.4375, 使下一位读者无法再犯那个错。
3.2× 重定价若为真: 成本项 `cost_ex/gt` 均 0.1675 → 0.536, mean g 由 +0.634 降至 +0.266(全窗), **每个单元的 g 都下移它自己的 cost×2.2**, 方向一律向下, 不改变单元排序(成本与 regime 的相关另报)。

## §8 ENV 白名单(E-0826-D)
本机: `env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/Users/haosiyu /usr/local/bin/python3 <device>`;
macOS 注入 `LC_CTYPE` `__CF_USER_TEXT_ENCODING`, 已枚举并断言。白名单 =
`{PATH, HOME, PWD, SHLVL, _, LC_CTYPE, __CF_USER_TEXT_ENCODING}`, 其余断言为空集;
且断言 `CAL* JUDGE* UPLIFT* PANEL* PYTHON* OMP* MKL*` 前缀**一个都没有** —— 口径只从工件的 `config_json` 读, 不从环境读。
pod2 侧同构断言写进 `receipts/RECEIPT_r12_causal_regime_build.json`。

## §9 实盘零接触
`~/dl_quant_live` / `~/wide_shadow` 全程只读或不读; 未写、未重启、未下单、未调任何账户 API。pod2 只跑 CPU, 不占 GPU。
