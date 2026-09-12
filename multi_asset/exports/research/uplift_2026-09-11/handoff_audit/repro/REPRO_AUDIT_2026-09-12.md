> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 交接前可复现性审计, 供独立复核员先读 | **作废条件:** ELIGIBILITY_CONTRACT 被裁定填入 / 任一钉住输入被重建 / jpline 恢复可达后 V4 跨机门补做
> **口径 PIN:** `CALIBER_PIN_v4_2026-09-11.md`(v4 链 2026-09-09)。g = net_ex/gross_total, bps/4h 锚/单位 gross。
> **ENV(E-0826-D):** 本文与其两份同目录收据的环境变量白名单 = **空集**; 全部 sha256 本会话 **重算**, 无一处抄自文档。
> **实盘零接触:** `~/dl_quant_live` / `~/wide_shadow` 只读(仅 `ls`); pod2 只读(未写任何文件, 未占 GPU); jpline 不可达。

# 能不能真的复跑? — uplift_2026-09-11 交接可复现性审计

## §0 先读这一段(硬闸)

**`ELIGIBILITY_CONTRACT.json` 的 `BUNDLE_export.approved_source_sha256` 现在仍然是空列表, 因此没有任何臂能经 `judge_v4.py` 晋级。** VERIFIED —— 本会话打开三份同内容副本(repo `retrain_2026-09/v4_chain_2026-09-09/`、pod2 `infra2/v4chain/`、pod2 `review_scratch/`), 三者 sha256 完全相同 `3299dc97ab0c90d5…`, 其中 `gates.BUNDLE_export.source = null`、`approved_source_sha256 = []`, 而 `arms` 里 **A1 / A1s / A1e / A2 / A3 五条全部** 把 `candidacy_gate` 指向 `BUNDLE_export`。按该文件自己的 rules[4]:「空的 approved_source_sha256 列表意味着该门没有被批准的程序: 任何收据都不能满足它, 任何臂都不能经它成为候选。」

已经写好但**没有被应用**的补丁在 pod2 `/workspace/uplift_2026-09-11/infra2/v4chain_PROPOSED/ELIGIBILITY_CONTRACT.json`(sha256 `3780ae5f223b82b8…`), 它把 `BUNDLE_export.source = v4e_gate_export.py` 且 `approved_source_sha256 = [f814c728938482b8…]`, 并新增臂 `XIBLAG50`。我**重算了** `infra2/v4e_gate_export.py`(repo 与 pod2 两份): 都是 `f814c728938482b876cbcaa31f200832d207a0f89387d58ed3e2d0d45448e214`, 与该提案值逐位相同 —— 也与 `RULINGS_OUTSTANDING` L48 / `DOCKET_r7` L218 的提案值相同。提案文件自己写着「NOT APPLIED — the frozen file is unchanged; a human must approve」。

⇒ **给复核员的话: 晋级路径是断的, 且断点只需一次人类裁定即可接上。在它接上之前, 本 program 里任何"某臂过了/没过判官"的说法都不是经合同验证的说法。** 这与 `CLOSEOUT §6` 自己列的硬闸 #5 一致。

**第二条同级的闸**: pod2 上有 **三份互不相同的 `judge_v4.py`**(`7f1aa5d6…` = repo 正典副本, `62e9da3a…` = PROPOSED, `634ecce0…` = `review_scratch/r3_check/v4_chain/`)。复核员若不带全路径地运行 "judge_v4.py", 会静默跑到另一个程序。这正是本台记过的按名推断语义(E-0825-H/G)形态。

---

## §1 机器地图 —— 哪台机器上有什么, 现在可不可达

| 机器 | 现在可达? | 本会话实测 | 上面有什么(与本 program 相关) |
|---|---|---|---|
| 本机 Mac | 是 | — | git 仓 `research/book-uplift-2026-09-11`; 全部文档、全部**本地归档的**装置与收据; `~/dl_quant_live`(实盘执行器, git)与 `~/wide_shadow`(生产者, 非 git) |
| **pod2** | **是** | `hostname f4530321c9b8`, up 43 天, `/workspace` 2.1P mfs, GPU RTX PRO 4500 Blackwell **2 MiB / 32623 MiB 已用(检查时空闲)** | **几乎全部计算都在这里**: 5m 缓存 / dlw_v4raw / meta_newprod_v4 / dev_v4 回放树 / 全部 arm npz / 全部 pod-only 装置 / `w10_sleeve.py` / `costb_PWR_G230k.json` / judge 与合同 |
| **jpline** | **否** | `ssh: connect to host 212.50.244.62 port 31999: Operation timed out`(15s) | 宽面板与判官的另一路; `CALIBER_PIN §5` 记的「V4 跨机门因 jpline 不可达未做」**今天仍然成立** |

**INFERRED 但重要**: `CLOSEOUT` 修订 A-6 指出, jpline 的两次 ssh 超时被转成了「Hyperliquid 整类不可验证」的**研究结论**。本次实测确认这台机器**还是**不可达 —— 也就是说那条结论至今没有被任何可达的证据支撑, 它是一个基建故障的影子。复核员应把它当作"未测", 不是"已否"。

**逐轮机器归属(VERIFIED, 由每轮受据里的绝对路径读出, 不是按目录名推断):**

- **输入与回放装置**: 全部 `pod2:/workspace/`。没有任何一轮的书层计算能在 Mac 上跑 —— `w10_sleeve.py` 以**相对路径**读 `pod_backup_2026-08-21/{wide_fea_hist_meta.npz, wide_panel_4h_hist_v2.npz, slow_pred_hist_oos.npy, nets_histv2_*}`(L68/L78/L112/L114)与 `./f8_2026-08-22/preds/<FPRED>`、`./dlw_2026-08-22/data/dlw_targets.npz`(L120-123), 这些在各轮都是指向 `/workspace/...` 的 symlink 树。
- **训练(GPU)**: 仅 R4(`r4_nondet`)、R5 ANGLE-3(`r5_seeds`)、R9 右端扩窗(`GATE X-P`)。全部 pod2。其余各轮都是**回放 + 判官**, CPU。
- **LOB 立方**: pod2(`r3k_impact/LOBCUBE_COV.json` 记 matched_symbols 811; 2022–2025 每年均名 **0.0**, 只有 2026 有 525.12 —— 即 LOB 证据只覆盖 2026)。
- **实盘账本 / fills / markout**: 本机 `~/dl_quant_live`(R6 judge1、R11 cost-truth、R11 income 的输入)。`ops/backfill_markout.py` 在位(VERIFIED, 本会话 `ls`)。
- **纯本地文档算术**: `gap_arith.py`(CLOSEOUT §2 的夏普预算)、`r11_verdict/devices/*`、`r13_*/devices/_env.py` 等。

---

## §2 钉住输入存在性与 sha256(全部本会话重算)

机器可读版本: 同目录 `PINNED_INPUTS_SHA256_2026-09-12.json`。

| 钉住件 | 在位? | 重算 sha256 | 与文档的对账 |
|---|---|---|---|
| holefix2 5m 缓存 | 是 (2,087,655,898 B) | `1d7f459dee434ec4…` | **MATCH** `CALIBER_PIN §1` 的 sha16 `1d7f459d`; 并与 `lineage_A0.json.dlw_v4raw_fea82_meta.cache_sha256` 逐位同 |
| `wide_fea_v4_meta.npz` | 是 (25,477,849 B) | `12ea42c4557093f1…` | 文档只记了大小, **从未钉过 sha** —— 本文是第一次留痕 |
| `dlw_v4raw/dlw_targets.npz` | 是 (192,038,760 B) | `d1976cf6246cdc25…` | **MATCH** `r9_coverage/receipts/lineage_A0.json` |
| `dlw_v4raw/dlw_fea82.npz` | 是 (468,075,570 B) | `40608701cad1aea1…` | **MATCH** 同上 |
| `meta_newprod_v4.npz` | 是 (27,497,999 B) | `0e3c09ac86c727ac…` | 从未钉过 sha |
| `shadow_bundle_v4/slow_pred_pinned.npy` | 是 (33,763,640 B) | `dde19142d017c37d…` | 从未钉过 sha。**⚠ 它不是规划数那本书的 king 腿 —— 见 F2** |
| `dev_v4` 回放树 | 是 | `BUILD.json` 在位, `dlw_2026-08-22 -> /workspace/dlw_v4raw`, `probe_artifacts/` 57 项 | 与 `CALIBER_PIN §1` 相符 |
| `w10_universe.py` | 是 (26,085 B) | `64c70a44ee88b795…` | 从未钉过 sha |
| `w10_sleeve.py` (pod2 与 repo `trackA/`) | 是 | `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650` | **MATCH** 全 64 位, 两机一致 |
| `judge_v4.py` | 是 | `7f1aa5d63ea37d67…` (repo = pod2 `infra2/v4chain` = pod2 `review_scratch`) | 一致; **但 pod2 另有两份不同的同名程序** |
| `ELIGIBILITY_CONTRACT.json` | 是 | `3299dc97ab0c90d5…` (三处一致) | **`approved_source_sha256` 仍为空** |
| `pod_legs_v4.py` | 是 | `ce0d985315991feb…` (repo = pod2 两处) | 一致 |
| `costb_PWR_G230k.json` | 是 | `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53` | **MATCH** repo 与 pod2 逐位同, 也与 `PREREG_r6` L204 / `RESULT_r6_judge2` L248 相同 |
| `r3_attack_b9646/null.py` (repo `r3_attack_RESID_SHARPE/null.py`) | 是 | `91d4c91cb92a64404f8e635a76969b435b86ab7840fc110564d9509a1b0c7fa9` | **MATCH** |
| `r3_gates/devices/rs_conc.py` | 是 | `3fd2f76496a593ba5342bbf8dd21d9f52473a52fe55657b7592f30d06143ab11` | **MATCH** 全 64 位 |

**没有任何一个钉住输入缺失, 没有任何一个 sha 对不上。** 这是本次审计最干净的一块。

**一处需要复核员自己判的不一致(VERIFIED, 未定性)**: `lineage_A0.json.dlw_v4raw_fea82_meta.targets_sha256 = 720f03a447278b4b…`, 但同一文件里 `dlw_v4raw_targets.sha256 = d1976cf6246cdc25…`(我重算磁盘上的 targets 也是 `d1976cf6…`)。即**钉住的 DL 特征矩阵, 是对着一个与今天磁盘上不同的 targets 文件构建的**。同一 meta 还记 `anchors_without_panel_row = 5`(ext 谱系是 0)。这可能是 `raw_patch` 之后 targets 被重建的正常结果, 也可能不是 —— 文档里没有任何一处解释它。**复核员应在引用任何 DL 侧数字之前先把这条问清楚。**

**本地全部 SHA256SUMS 清单逐条 `shasum -c` 通过**(19 份), 两份"失败"是我的 cwd 错误, 从正确根目录重跑全 OK。唯一真实缺陷: `r13_B_withinhalf/SHA256SUMS.txt` **把自己列进了自己**(`2867b87f…  SHA256SUMS.txt`), 这一行在数学上永远不可能验证通过, 该清单因此恒报 1 FAILED。其余 16 行全 OK。

---

## §3 最承重那个数, 我从钉住输入端到端跑出来了 —— 以及它坐在什么上面

配方见同目录 `MINIMAL_RECIPE_planning_number.sh`(逐字可抄)。

### F1 · 规划数复现成功, 逐位级 — VERIFIED

`CLOSEOUT §7` 的「A0 无条件 +0.6342 bps/锚, CI95 [+0.1653,+1.1071], 夏普 1.2912」, 我在 pod2 上**只读**重算(不写文件、不占 GPU):

```
arm sha256 352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339
n_raw 10039 → post_warm 9139 → cut 9138 → finite-sigma 9138
span 2022-06-30 00Z → 2026-08-30 20Z
mean_g 0.634196   SR 1.291223   CI95 [0.165290, 1.107099]
mean(turnover) 0.0303158   mean(gross_total) 0.6956440
```
机器受据是 `RECEIPT_r8_BUILD2_2026-09-12.json` → `step1_reproduction_of_motivating_numbers.A0_unconditional.mine`, 装置 `r8b2_receipts/r8_repro.py`(repo 与 pod2 两份 sha 都是 `afb839ecbec873ae…`, 且等于受据自报的 `self_sha256` —— 三方对齐)。arm 文件 sha 前 16 位与 `R8_REPRO.json.file_sha16.A0_s42` 相同。**这个数不是故事, 它是真的。**

### F2 ★ 但它那本书的两条腿都不在 v4 谱系上 — VERIFIED(读产它的源码)

产 arm 的是 `r3k_impact/r3k_reprice3.py`。我读了它的 env 构造(L36-46):

```
BOOK = LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45
       UMASK_SCOPE=m1 UMASK_NPZ=<HC>/masks/umask_UPIT_CRYPTO.npz
       SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy      ← king 腿
A0 臂再加 FSEED=42  FPRED=f10_A0_s42.npy                                     ← F10 腿
```
- **king 腿 = `SLOW_v3_on_v4axis.npy`**, 按 `build_dev_v4.py` L4 的自述, 它是 **v3 pinned 按 E_ts 对齐到 v4 轴**的东西 —— **不是** `CALIBER_PIN §1` 钉的 `shadow_bundle_v4/slow_pred_pinned.npy`。
- **F10 腿 = `f10_A0_s42.npy`**, 按 `build_dev_v4.py` L42/L44/L45 逐字: 读 `/workspace/dlw_ext/data/dlw_targets.npz` 与 `/workspace/f8_ext/preds/f10_V2MAIN_s{42,2027}.npy` 再对齐。`dlw_ext` 与 `_ext` 是 `CALIBER_PIN §2` **明令作废**的谱系(E-0909-A 回绕)。
- 机器受据独立佐证: `r9_coverage/receipts/lineage_A0.json.f8_ext_report_s42.targets_sha256 = 31d043e8f160a1d4…` = 同文件里 `dlw_ext_targets.sha256`。

⇒ **本 program 全程当基线、当 ρ 筛选参照、当 §2 夏普缺口算术输入的 A0, 自己坐在被本轮口径锁禁用的谱系上。** `CLOSEOUT` 修订 A-1 已经自曝了这一条 —— 复核员必须知道它是**修订**里的, 正文 §7 引的仍是 A0。

### F3 · 口径正确的那个规划数也复现了 — VERIFIED

`r11_verdict/receipts/RECEIPT_r11_cost_estimand_reconciliation.json.planning_number` 给的是 **A1x_ext_s42**(v4 原生, 覆盖天花板已关闭)。我同样只读重算:

```
arm sha256 57d18ca50e3a30bb798ec3626e0b3c71e6f6bf72a6e376cfbfb5365a45d6d3b8  ← 与 RECEIPT_r9_judge.json 相同
n 9199   span 2022-06-30 00Z → 2026-09-10 00Z
mean_g 0.660154   SR 1.285667   CI95(B=4000, [20260912,31]) [0.1772, 1.1540]
```
与 `r9_coverage/SUMMARY_r9.json.A1x_ext_s42_NEW_WINDOW` **逐位相同**。它的腿是 `SLOW_v4_x0910.npy` + `f10_v4RAWx_s42.npy` + `meta_newprod_v4_x0910.npz` + `dlw_v4raw_x0910` —— 全 v4。

⇒ **给复核员的建议: 引规划数就引 A1x(0.6602 / 1.2857 / n 9199), 不要引 A0。两者实质相同, 但只有一个在钉住的口径上。**

### F4 ★ 已发表的 CI95 不是钉住的自举口径 — VERIFIED

任务书与 `CALIBER_PIN §3` 钉的是 **B=2000, `default_rng([20260905, k])`**。但产规划数的 `r8_repro.py` 用的是 **B=4000, `default_rng([20260912, seed])`**。我两种都跑了同一段数据:

| 估计器 | A0 CI95 |
|---|---|
| 已发表(`[20260912,31]`, B=4000) | [0.16529, 1.10710] |
| **钉住口径**(`[20260905,31]`, B=2000) | **[0.15209, 1.08429]** |

受据自己也承认「CI bounds differ in the 3rd decimal because the day-block bootstrap seed differs from round 7's」。点估计与符号不受影响, **但"CI95 [+0.1653,+1.1071]"这个具体区间不是钉住口径下的区间**。另外, 钉住口径的 **k 索引在任何收据里都没被钉**; 我是在 `r9_coverage/devices/r9_judge.py` L88 里读到 R9 用的是 `k=1`(L6-7 还写明了两套估计器的区别)。**装置里有, 收据里没有。**

### F5 ★ 换手单位陷阱有**三**张脸, 任务书写的那一版对不上自己的乘数 — VERIFIED

我在同一段数据上把三种算法都算了:

| 口径 | 值 | 相对 raw 的倍数 |
|---|---|---|
| `turnover_mean`(raw Σ\|dw\|) | **0.0303158** | 1× |
| `mean(turnover) / mean(gross_total)`(比之比) | **0.0435795** | **1.4375×** = 1/0.6956 |
| `mean(turnover / gross_total)`(逐锚比再平均) | **0.0540270** | **1.7822×** |

任务书说「与 g 匹配的口径 = turnover/gross_total = 0.0540270, 混用是 1.4375 倍误差」—— **这两半来自不同的算法**: 1.4375 属于比之比(得 0.04358), 0.0540270 属于逐锚比。真正与本 program 下游一致的是 **0.0540270**(逐锚比): `r11_costtruth` 收据的 `second_unreconciled_gap.replay_turnover_per_gross = 0.05402` 就是这一版, 我重算到第 5 位相同。⇒ **复核员用 0.0540270, 但不要同时引 1.4375; 正确乘数是 1.7822。**

### F6 · 两个窗口的分界, 第一手确认 — VERIFIED

同一 arm 上实测: `W_TAIL`(不丢暖机, 截到 2026-08-30 20Z)**n = 10038**; `W_ALPHA`(丢前 900)**n = 9138**。最差 UTC 日:

| 窗 | 最差日 | 逐锚 g 求和(%/单位 gross) |
|---|---|---|
| W_TAIL | **2022-06-07** | −5.6661 |
| W_ALPHA | 2022-11-10 | −2.3248 |

⇒ **丢掉 900 个暖机锚确实把样本最差的那一天丢掉了**, 任务书的警告在这份数据上成立。注意口径: 任务书记的 −11.1714% 约为我这个读数的 2 倍(= 2.0× gross 的 NAV 口径), 但不是精确 2 倍(−11.1714/2 = −5.5857 vs −5.6661, 差 1.4%) —— 差额可能来自日内**复利 vs 求和**。**日期 VERIFIED; 幅度请找它自己的收据再引, 不要照抄。**

---

## §4 成本模型争议 —— 复核员必须知道它已经被打了两轮, 而且结论反号

任务书说这条争议"未决"。**本 program 后来又打了两轮, 两轮结论互相反号, 而且都有机器受据。** 这一段直接决定 F1/F3 的数字要不要打折。

| 轮 | 受据 | 结论 |
|---|---|---|
| INFRA-1 / R3K | `r3k_impact/costb_PWR_G230k.json`(K=0.17 拟合, α=0.87) | 钉住的成本书。**注意: `RESULT_INFRA1 §5` 原文承认 K 是文献中心值、从未对本书拟合** |
| R11 cost-truth | `r11_costtruth/RECEIPT_r11_cost_truth_2026-09-12.json`(全清单 `shasum -c` 通过) | **markout 不回复**: 60s −3.2026 → 5m −6.6424 → 15m −6.3044 → 1h −7.7831 → 4h −6.1359(4h 的 CI 含零), 平台期 −6.7164。`ratio_steady = 3.2167`。据此重定价: A0 g 0.6342 → **0.2717**, Sharpe 1.2912 → **0.5532**, NAV 27.78%/年 → **11.9%** |
| R11 verdict | `r11_verdict/receipts/RECEIPT_r11_cost_estimand_reconciliation.json` | **推翻上面的重定价**, 判为 estimand 错配: `[fill, fill+D]` 落在 `[anchor_i, anchor_i+1]` **内部**, 回放自己的 `sm*y4[i]` 已经吃了这段价格路径, 再收一次是重复计价。它改测"相对决策价"的量: trackB 实测 **0.286** bps/单位成交 vs 模型收 **2.9537** ⇒ 模型**多收** 2.6677。三角验证: 2.6677 × **实盘** turnover 0.2898 = 0.2767 bps/锚, 与 judge1 独立测的 0.2767 [0.075, 0.653] **吻合到 4.74%**; 用**回放** turnover 只得一半, 两者之比正好是 2.01× 的实盘/回放换手缺口 |

**⇒ 在你的复核里, 凡判决依赖成本模型, 请同时报两个符号:**
- 按 **3.2167× 重定价**(R11 cost-truth): 规划数 **向下** 0.6342 → 0.2717(−57%), Sharpe → 0.5532; `trackB` 的成本通道天花板从 0.120 抬到 **0.3863** > G2 分辨率 0.23 ⇒ **该轴会被重新打开**; BUILD 1(basis 入书)的边际 dg 约**三倍**(它是唯一价值随成本墙上升的族)。
- 按 **R11 verdict 的更正**(模型多收 2.6677): 规划数 **向上** —— `withdrawn_repricing.corrected_delta_g_bps_per_anchor_on_replay_turnover = −0.1441`, 符号是 **CREDIT**。两种读数之间的跨度 **0.5066 bps/锚**, 比冻结窗自举分辨率 ±0.23 还大一倍。`trackB` 轴反而**关得更死**, BUILD 1 也**关得更死**。
- **仍然未决的**: `second_unreconciled_gap` —— 实盘每单位 gross 成交 **0.10864** vs 回放换手 **0.05402**, 比 **2.01×**, 收据自己写「NOT folded into the repricing … whether this is the same thing as the on-file raw-turnover ×1.94 is NOT decided here」。**这条缺口会同时改动上面两种读数, 谁都没把它算进去。**

R11 的去重按 `(symbol, trade_id)` 且**保留带 `mid_at_fill_plus_60s` 的那一行**(84158 → 34921, 丢弃 49237 行全部 payload 相同, 0 行 payload 不同)—— 与任务书的 LAST-WINS 要求一致, VERIFIED。

---

## §5 每一轮的复现路径缺口(GAPS)

判据: **(a)** 装置是否本地归档 · **(b)** 命令是否逐字留痕 · **(c)** env 白名单是否在**机器可读收据**里(不是散文里) · **(d)** 输入是否在可达机器上。

### 严重 —— 本地什么都没有, 只有散文

| 轮 | 缺什么 | 证据 |
|---|---|---|
| **R2 时序 sleeve**(`r2_timeseries/`) | **本地只有 2 个 .md, 0 装置 0 收据**。全部在 pod2 `/workspace/uplift_2026-09-11/r2_ts/`(文档 L195-198 自陈)。本地这一轮的**每一个数字都是 UNRECEIPTED** | 本会话 `ls` |
| **R5 ND-2 清算/持仓量** | 本地 **0 收据**; 装置 `fetch2.py/repair.py/merge3.py/build_feats.py/arms.py/nulls.py/judge.py` 全 pod-only | 提取表已记; 本会话确认 pod2 有 `r5_oi/` |
| **R5 ANGLE-1 固定席位** | 本地 **0 收据**; 装置在 pod2 `/workspace/uplift_2026-09-11/seatladder` 与根目录 `ANGLE1_*.py`。`w10_seatladder.py` 本地缺失, 其 sha `f5dc76fb…` **不可重算** | 本会话 pod2 `ls` 见 `ANGLE1_*.py`、`w10_seatladder.py` |
| **R9 独立数据源普查** | 本地只有 1 个 json, **0 装置**。且其中 `NV1_upbit_kimchi` 是被"不得调交易所 API"的约束挡掉的, 不是被测负 | `r9_indep_source/` |
| **R7 fuel / SHIP-1** | `r7f2_receipts/`(9 json)与 `ship1_receipts/`(5 json)**只有收据, 0 装置**; 装置在 pod2 `r7f2/`、`ship1/` | 本会话两机 `ls` |

### 中等 —— 装置在, 但命令或 env 只在散文/代码里(E-0826-D)

| 轮 | 状态 |
|---|---|
| `r3k_impact`(**最被引用的成本书**) | 无 run.sh / 无 commands.txt / 无 RUN_ENV。env 白名单只能从 `r3k_reprice3.py` 源码读出。**E-0826-D 缺口落在整个 program 最承重的单件上** |
| `r3_placebo` / `r3_attack_RESID_SHARPE` / `r3_receipts` / `r3_gates` | 只有 `gateP.sh`; 逐臂命令与 env 收据缺失。`PREREG_gateA §8` 给了 run 行但 `$COMMON` **未展开** ⇒ 照抄跑不起来 |
| `trackC` / `trackF` / `attack_trackA_carry` / `attack_trackD_newalpha` | 无 run 脚本 / 无 env 收据(trackF 有 `arsenal.sh`/`setup_tree.sh` 但无 env) |
| `trackD_v4` | `device_commands.txt` 只有 566 B, 而该轮 **78 臂**; env 只在结果文档散文里 |
| `r4p3` | 无命令、无 env 收据(`RESULT_P3*.json` 无 env/cmd/config 键); 只能读 `p3_run.py` |
| `r4_nondet` | 命令逐字转录在 `RESULT_r4 §10`(本 block 最好的转录之一), **但** 本地装置 **无 sha 清单**; 训练器 env 白名单 17 缺 7 |
| `r5_seeds` | `train_v2_seeds.sh` 显式设全 17 个训练 env(本 block 典范), `DEVICE_SHAS.txt` 九件我全部重算 **全 MATCH**; **但没有任何一份 r5_seeds 收据带 env 块** —— 机器校验必须回去读脚本。`setup_tree.py` 在盘但**不在清单里** |
| `trackA` / `trackB` / `trackE` | trackA 有 67 KB `commands.txt` + `SHA256SUMS.txt`(本地项我已逐条验过), **但** env 写「verbatim from run_v4_arms.sh COMMON」而 `run_v4_arms.sh` **不在本地快照里**; trackE 全部 sha 在 `SHA256SUMS_pod.txt` 但那些文件是 REMOTE, 本机不可重算 |

### 轻微 / 已达标

`r9_coverage`、`r10_*`、`r11_*`、`r12_*`、`r13_*`、`klass_independent_objective` 这些**后段轮次普遍带 `SHA256SUMS.txt` + 收据内 `env_whitelist` 键**, 是本 program 纪律的高点。`r5_basis_receipts/GATE_PS.json` 逐条存了**逐字命令行**(round 5 最强的复跑件), 但 `RUN_ENV_arms.json` 只记**被设置**的 13 个键、不记留默认的键(`r5_angle2/GATE_P_r5a2.json` 两者都记, 那才是正确形态)。`r5_basis_receipts/SIG_MANIFEST.json` **只有路径没有哈希**。

### 本地/远端割裂的总账

**大量装置的 sha 在文档里是"claimed REMOTE"**: `w10_health.py`(`8684d9a9f43a8d15…`, 是 `w10_sleeve.py` 自报的父件)、`w10_seat.py`、`w10_trackF.py`、`w10_seatladder.py`、`w10_sleeve_seatgrid.py`、训练器 `pod_f10_train_ext.py`(`93cc2cdf925a1dad…`)。这些**在本机不可重算**。pod2 可达时它们可验; **jpline 不可达使 V4 跨机门永远缺一块**。

---

## §6 一句话给复核员

**输入端是干净的**(15 件钉住输入全部在位、sha 全对、`shasum -c` 全过), **最承重的两个数我端到端第一手复现到小数点后四位**, 但:
1. **晋级路径是断的**(合同空列表), 没有任何臂真正过过判官;
2. **发表的规划数坐在被本轮口径禁用的谱系上**(A0 的两条腿都是 v3/`_ext`), 口径正确的替身是 A1x;
3. **发表的 CI 不是钉住的自举口径**, 且钉住口径的 k 索引只写在装置里;
4. **成本模型被本台自己的两台仪器判成反号**, 跨度 0.5066 bps/锚 > 分辨率 0.23, 且两者都没算进 2.01× 的实盘/回放换手缺口;
5. **前六轮的 E-0826-D 纪律普遍不达标**(命令与 env 在散文或源码里, 不在收据里), 后七轮达标 —— **这条纪律梯度本身就是复核的地图: 先打前六轮。**
