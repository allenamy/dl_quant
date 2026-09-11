> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX (subagent, class = INDEPENDENT UNIVERSE OR VENUE, candidate = OKXRHO) | **状态:** 判决 DEAD, 已收据; 无换装建议, 无臂晋级 | **作废条件:** 买到付费跨场所历史(窗口 >= 2 年) / OKX 公开端点历史深度变化 / A0 参照面板换文件
> **口径 PIN:** v4 chain 2026-09-09 (`CALIBER_PIN_v4_2026-09-11.md`)。g = net_ex/gross_total, bps/4h 锚/单位 gross。成本 = 拟合 `r3k/costb_PWR_G230k.json`。上界 2026-08-30 20:00Z (E-0911-D)。
> **实盘零接触:** `~/dl_quant_live` / `~/wide_shadow` 全程未读写、未重启、未下单。全部计算在 pod2 `/workspace/r9okx/`(新建隔离树), 正典树 `dev_v4/` 未被写入。
> **GPU:** 未用一秒。本轮全 CPU(每臂 9–18 s)。`nvidia-smi` 开工时 0 compute apps / 2 MiB used ⇒ 未排队、未抢占独立研究员。

# OKXRHO — 用免费的 3 个月 OKX 历史回答"要不要买跨场所数据"

## §0 一句话判决

**DEAD。** OKX 资金费动量书对 A0 的 ρ = **+0.3530** [+0.2376, +0.4574],看上去在 0.30 门附近;但三个对照把它拆穿了:
(1) 同样构造、**同样 386 个名**、但用 **币安**资金费的书,ρ 只有 **+0.5634** —— 所以从 0.961 掉到 0.353 的路上,**三分之二是"宇宙变小"而不是"换了场所"**,而"宇宙变小"是币安上免费就能做的事,并且它**本身亏钱**(mean g −0.09 bps)。
(2) **场所纯对比** ρ(OKX 书, 同宇宙币安书) = **+0.6756** [+0.5589, +0.7675] —— **超过测绘员自己写的 0.6 否决线**。
(3) 把同一个 OKX 矩阵**按时间循环平移 53 锚**做成换手匹配零假设,它对 A0 的 ρ = **+0.3162** [+0.2070, +0.4079],与真臂的 CI 大幅重叠,而且它的 mean g(**+1.1209**)和夏普(**+2.033**)**都比真臂好**(+0.7582 / +1.502)。
⇒ 真臂**没打过自己的换手匹配零假设**;它那点"独立性"与"把信号的时间对齐弄坏"制造出来的独立性在统计上分不开。

而且它在 A0 亏的格子里**跟着一起亏**: mean g = **−5.6249** bps,CI95 [−8.9012, −2.2430](**CI 不含零**),最坏五分位 ρ **升到 +0.4338**。这正是 Amihud sleeve 的失败形态,简报点名的"最常骗到本台的方式"。

**对"要不要买数据"的回答: 本轮证据不支持买。** 免费窗确实足以回答相关性问题 —— 这一点测绘员是对的 —— 而它给出的答案是否定的。

## §1 STEP 1 · 可行性(第一手复核, 不信测绘员)

| 断言 | 我的实测 | 标签 |
|---|---|---|
| OKX `/api/v5/public/funding-rate-history` 最老 2026-06-08 | BTC/SOL/WLD 三名各 287 行, 3 页到空, 最老 **2026-06-08T08:00:00Z**, 最新 2026-09-11T16:00Z, 间隔全 **8h** | **VERIFIED** (`devices/okx_probe.py`, pod2) |
| OKX USDT 本位 linear SWAP 数量 | **463** 个 live; 与面板 829 名匹配上 **388**; 其中能建出 EMA 列的 **386** | **VERIFIED** |
| 价格历史够不够 | `history-candles` 4H 翻 25 页 = 2500 根仍未到底, 最老 **2025-07-22** ⇒ **价格比资金费深**, 卡脖子的是资金费 | **VERIFIED** |
| "约 570 个 4h 锚" | **错**。A0 轴上界 2026-08-30 20:00Z(E-0911-D), 2026-06-08 08:00Z → 该上界 = **500 锚**; 再扣 14 天 EMA 冷启动烧机 ⇒ **418 锚** | **VERIFIED** |
| Bybit 被代理拒绝 | 我**没有复测**, 引自 `DATA_PROVENANCE_r5_basis_2026-09-11.md` §B | **INFERRED** |
| 因果可建 | **是**。见 §1.1 | **VERIFIED** |

### §1.1 因果性(逐条对照本项目已登记的泄漏族)

- **构造**: 逐字镜像 `pod_panel_ext.py` L116–162 的 v1 臂 —— 逐笔 interval(OKX 历史响应**没有** interval 字段, 故按结算间距推导并吸附到 `ALLOWED={1,2,4,6,8}h`, 这正是正典构建器在 interval 列缺失时的做法)→ `rate_nf = rate*(8/iv)` → 墙钟 EMA `HL=3d` → 锚点采样 `searchsorted(ft, anchor, "right")-1` → 距上次结算 >12h 置 NaN。**只消费 `ft <= anchor_ts` 的结算, 无前视。**
- **收益腿**: 用钉住的 `meta_newprod_v4.npz` 的 `y4`(RAW Σ5m 简单收益), `CAL=log` ⇒ **不施 expm1**(E-0904-F 已守)。
- **面板**: **没有**走 `panel_source.py` 默认。用的是**归档 A0 臂自己读的那个文件**。
- **stride/horizon**: 4h 锚 / 4h 标的, 无 stride<horizon。
- **betaadj_ret24 / vol-scaling**: 本臂只用一个特征(资金费 EMA), 两者都不在路径上。

### §1.2 一条必须让裁定者看见的口径事实(VERIFIED, 与我的结论无关但影响别人)

`dev_v4/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz` → `dev_alt/.../wide_panel_4h_hist_v2.npz` → **`/workspace/data/wide_panel_4h_v2ext.npz`**。
也就是说 **归档的 A0/A1/A2 臂读的是 v2ext 面板, 不是 `wide_panel_4h_v3splice.npz`**,而 `CALIBER_PIN_v4_2026-09-11.md` §1 那行"面板导出步 = v3splice + canoncont"并不描述这些臂实际读到的文件(`w10_health.py` L57 把路径写死成 `{B}/wide_panel_4h_hist_v2.npz`,没有 env 开关)。
我**跟随归档臂**(同一文件)以保证逐位可比 —— 见 §2 GATE A。这条留给 lead 对账,不是我的结论。

## §2 装置门(全部逐位, 全部 PASS)

| 门 | 内容 | 读数 | 判 |
|---|---|---|---|
| **GATE A** 恒等 | 我的隔离树重跑归档 A0 臂(`V4_A0_dyn_s42` 逐字同 env)是否逐位相同 | `S0_rec` / `d30_n2_c42_rec` / `legs_fund` / `legs_king` / `legs_ts` **全部 bitwise_equal=true, maxabs 0.0** | **PASS** |
| 装置同一性 | `/workspace/r9okx/w10_health.py` sha256 | `8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d` = `dev_v4` 那次运行自报的 `device_sha256` | **PASS** |
| **GATE B** 构建器 | 我的 EMA 构建器**喂币安档案数据**能否复现正典面板列 `f_fund_ema_v1`(2026-08 全月) | n=122,268, Pearson **0.9999998**, 中位 |Δ| **0.0**, max|Δ| 3.37e-5(float32 + 缺 2026-05 前史) | **PASS** |
| **GATE C** 冷启动 | 14 天烧机后, 冷启动是否还残留伪影 | BINCOLD vs 正典暖启动面板, 逐锚横截面 Spearman **中位 1.0**(p10 0.999) | **PASS** ⇒ OKX/币安之差是**场所**, 不是暖机 |

## §3 STEP 2 · 主筛 ρ(全部 VERIFIED, 418 锚, 窗 2026-06-22 08:00Z → 2026-08-30 20:00Z)

书 = `d30_n2_c42_rec`(在役形态)。候选臂 = 纯资金费书(`LEGS=001` ⇒ w3 实测 = [0, 0, **1.0**]), `PHI=0`, 成本 = 拟合模型。

| 臂 | 是什么 | ρ(A0 s42) | CI95 | ρ(A0 s2027) | Spearman |
|---|---|---|---|---|---|
| **OKX** | **候选**: OKX 资金费, 386 名 | **+0.3530** | **[+0.2376, +0.4574]** | +0.3600 | +0.3042 |
| OKX_noFTRIM | 同上, 关掉 FTRIM(去掉币安费率进书的唯一通道) | +0.3163 | [+0.1947, +0.4231] | +0.3230 | +0.2614 |
| **BINCOLD388** | **宇宙对照**: **币安**资金费, **同样 386 名**, 同样冷启动 | **+0.5634** | **[+0.4828, +0.6371]** | +0.5654 | +0.5271 |
| BINWARM388 | 同上但暖启动 | +0.5653 | [+0.4864, +0.6394] | +0.5672 | — |
| **BINCOLD** | **装置天花板**: 币安资金费, 全 688 名 | **+0.9610** | [+0.9433, +0.9741] | +0.9580 | +0.9569 |
| BINPANEL | 正典面板 EMA, 全宇宙 | +0.9705 | [+0.9620, +0.9768] | +0.9670 | +0.9597 |

**分解(这是本轮最重要的一张表):**

```
 0.9610   全宇宙币安资金费书  ←  装置天花板
   │  −0.398   ← 宇宙从 688 名缩到 386 名   (币安上免费, 且本身亏钱)
 0.5634   同宇宙币安资金费书
   │  −0.210   ← 换成 OKX 的资金费数据      (要花钱买的就是这一段)
 0.3530   OKX 资金费书  ←  候选
```

**场所纯对比**: ρ(OKX 书, BINCOLD388) = **+0.6756** [+0.5589, +0.7675]。
一旦把 BINCOLD388 放进回归,OKX 书对 A0 的 β **塌到 −0.0269** —— 它对在役书的全部暴露都**穿过一本币安书**走,场所本身没有增加一条新的暴露,只增加了噪声。

**信号层(不是书层, 不得换算成夏普)**: OKX 资金费 EMA 与币安面板 EMA 的逐锚横截面 Spearman **中位 0.7516** [p10 0.7039, p90 0.7812], 372 个共同名; 逐名时间序列相关中位 **0.7451**(p10 0.166, p90 0.976)。

## §4 STEP 2b · A0 亏损格(简报点名的那个陷阱 —— 候选**没过**)

| 臂 | A0 亏损格 n | 候选在该格的 mean g | CI95 | ρ 无条件 | ρ 亏损格 | **ρ 最坏五分位** | 候选在最坏五分位 |
|---|---|---|---|---|---|---|---|
| **OKX** | 189 | **−5.6249** | **[−8.9012, −2.2430]** | +0.3530 | +0.3056 | **+0.4338 ↑** | −8.9768 |
| BINCOLD388 | 189 | −10.9692 | [−14.2512, −7.8915] | +0.5634 | +0.5015 | +0.5444 ↑ | −19.1084 |
| BINCOLD | 189 | −26.5958 | [−30.6050, −22.8672] | +0.9610 | +0.9354 | +0.9063 | −47.1276 |
| A0 自己 | 189 | −26.0143 | — | — | — | — | −47.0050 |

**读法**: 候选在 A0 亏钱的格子里**自己也亏, 且 CI 不含零**;它的 ρ 在 A0 最坏的五分位**从 0.3530 升到 0.4338**。
这是 Amihud sleeve 的同一个形态(ρ 在 A0 亏损处升到 +0.343/+0.438)。**它不是对冲, 它是一起亏, 只是亏得少一点。**
亏得少的那部分不是技能 —— 是 gross 小(0.8661 vs A0)和宇宙小,同样的减仓在币安上免费。

## §5 STEP 3 · 独立收益(ρ 并不低, 本步按简报不是必需 —— 我照做了, 它不过)

窗内 418 锚, 拟合成本模型 `costb_PWR_G230k.json`(sha16 `295b4e7b462373e4`)。

| 读数 | OKX | OKX_noFTRIM |
|---|---|---|
| mean g (bps/锚/单位 gross) | **+0.7582** | +1.1483 |
| CI95(UTC 日块自举 2000 次, `default_rng([20260905,k])`) | **[−1.2544, +2.9142]** 含零 | [−0.9578, +3.3470] 含零 |
| 年化夏普 | +1.502 | +2.172 |
| **SE(年化夏普) = √(2190/418)** | **2.2889** | 2.2889 |
| 换手 / 锚 | 0.01924 | 0.01731 |
| 成本 (bps/锚) | 0.0690 | 0.0631 |
| carry_ex / gross_total | +0.4704 / 0.8661 | +0.8614 / 0.8646 |

**成本不是杀手**: 毛额 = 0.7582+0.0690 = 0.827, 成本吃掉 **8.3%**。杀手是**没有可测的边**: SE(夏普)=2.29 意味着这个窗对夏普的分辨率是 ±4.5,在这条轴上**永远**测不出 alpha(这点测绘员早就说清楚了)。

### §5.1 换手匹配零假设(用 `r3_attack_b9646/null.py` 的两族, **不用**有缺陷的逐锚置换)

`null.py` 在 pod2 `/workspace/uplift_2026-09-11/r3_attack_b9646/null.py`(简报给的 Mac 路径在本机不存在 —— 见 §8)。
一个装置缺陷先自报: 直接前移(SHIFT_k)会把只有 503 行的 OKX 块推出轴尾, SHIFT503 与 SHIFT1009 的 npz **sha 逐位相同**,这就是 tell。改成**在有值行内循环平移**(CSHIFT_k), 保持存活锚数与真臂一致。

| 臂 | ρ(A0) | CI95 | mean g | CI95 | 夏普 | 换手 |
|---|---|---|---|---|---|---|
| **R9_OKX(真臂)** | **+0.3530** | [+0.2376,+0.4574] | **+0.7582** | [−1.2544,+2.9142] | +1.502 | 0.01924 |
| CSHIFT53 | **+0.3162** | [+0.2070,+0.4079] | **+1.1209** | [−1.0713,+3.2387] | **+2.033** | 0.01879 |
| CSHIFT101 | +0.2666 | [+0.1719,+0.3517] | +0.3618 | [−1.6280,+2.3449] | +0.685 | 0.01975 |
| CSHIFT251 | +0.1977 | [+0.0763,+0.3057] | −1.7873 | [−4.0850,+0.3305] | −3.567 | 0.01820 |
| RELAB1 | +0.0797 | [−0.0360,+0.2013] | +0.3293 | [−2.0134,+2.6199] | +0.565 | 0.02132 |
| RELAB2 | −0.1570 | [−0.2964,−0.0232] | −1.3324 | [−4.6303,+1.6525] | −2.089 | 0.02353 |
| RELAB3 | +0.0029 | [−0.1557,+0.1606] | −1.4472 | [−3.7116,+1.0161] | −2.683 | 0.02094 |

**两条读法, 两条都致命:**
1. **收益**: `CSHIFT53` —— 同一个 OKX 矩阵, 只把时间对齐弄坏 53 个锚 —— mean g **+1.1209 > 真臂 +0.7582**, 夏普 **+2.033 > +1.502**。真臂**在零假设分布内部**。
2. **相关性**: `CSHIFT53` 对 A0 的 ρ = **+0.3162**, 与真臂 +0.3530 的 CI 大幅重叠。**ρ≈0.35 不是"OKX 是另一个下注"的证据, 它是"把这个信号的快分量弄坏之后还剩多少相关"的读数。** RELAB 族(打乱符号映射)掉到 ≈0, 说明 0.2–0.35 那一段来自资金费横截面的**慢结构**, 而慢结构是跨场所共享的 —— 那正是 A0 在赚/在亏的东西。

### §5.2 "买数据到底买到什么" —— 场所专属 alpha

对 `g_OKX` 回归(截距做日块自举, **不是**残差均值 —— 带截距时残差均值恒为 0, 那是恒等式不是结果):

| 回归 | 截距 α (bps/锚) | CI95 | β | R² |
|---|---|---|---|---|
| 对 A0 | +0.0509 | [−1.9354, +2.0854] | β_A0 = +0.2349 | 0.1246 |
| 对 BIN388 | +0.8190 | [−0.8277, +2.6780] | β_388 = +0.6760 | 0.4565 |
| **对 A0 + BIN388** | **+0.9020** | **[−0.7857, +2.7760]** | β_A0 = **−0.0269**, β_388 = +0.6988 | 0.4576 |

**场所专属的那一份 alpha, 三种口径下 CI 全部含零。** 这就是花钱买的那段东西的当前估值。

## §6 STEP 4 · 算术(不往对自己有利的方向取整)

两源最优风险配置: `S = sqrt((s1² + s2² − 2ρ s1 s2)/(1 − ρ²))`, s1 = A0 跨 regime **1.2912**, 目标 **3.966**。

| 情形 | 组合夏普 | 距 3.966 |
|---|---|---|
| 点估计(ρ=0.3530, s2=1.5021) | **1.7081** | **2.2579** |
| 候选真实夏普 = 0(CI 排除不了) | 1.3801 | 2.5859 |
| 候选真实夏普 = CI 下界(负) | < 1.2912 | > 2.67 |

**最能说明问题的一个数**: 要在 **ρ = 0.3530** 下把组合推到 3.966,候选**自己**的夏普要到 **3.9643**;而如果它与 A0 **完全不相关**, 要求是 **3.705**。
⇒ **ρ 从 0 涨到 0.35, 只把门槛抬高 0.21 夏普(同一公式下 ρ=0 的要求是 3.7499; 简报写的 3.705 略低, 差在 s1 的取值) —— 也就是说 ρ≈0.35 这种"独立性"几乎什么都没买到。** 实测值是 1.50 ± 2.29。
点估计口径下它带来 +0.417 夏普,**正落在收口文档给"重新加权"划的 0.2–0.8 带内**。

## §7 判决与它的诚实边界

**DEAD。** 依据(按杀伤力排序):
1. 没打过自己的换手匹配零假设(§5.1), 收益与相关性两条都没打过。
2. A0 亏损格里跟着亏, CI 不含零; 最坏五分位 ρ 反升(§4) —— 简报点名的陷阱, 原样踩中。
3. 场所纯 ρ = 0.6756 > 测绘员自己的 0.6 否决线(§3)。
4. 测得的"独立性"三分之二是宇宙变小(币安上免费, 且亏钱), 不是场所(§3)。
5. 场所专属 alpha 三种口径 CI 全含零(§5.2)。
6. 独立夏普 1.50 ± 2.29, 与零、与 6 都分不开(§5)。

**边界(必须说, 否则这份判决被过度使用):**
- 窗只有 **418 锚 / 一个 regime**(2026-06→08)。ρ 在更长的窗上可以不一样。我杀的是**"买数据"这个论证在当前证据下的形态**, 不是"跨场所永远无用"这个命题。
- ρ 的分辨率**足够**(SE ≈ 0.043–0.11), 夏普的分辨率(SE 2.29)**完全不够** —— 这也正是测绘员设计这个筛子的初衷, 那部分推理是对的。
- Bybit 未复测(INFERRED), Hyperliquid 未进本轮(jpline 不可达, 见 `r9_universe` 同期收据)。
- 本轮**不主张**"跨场所轴关闭"。它现在的状态是: **免费窗能回答的那个问题已经回答了, 答案是否定的。**

**什么样的新证据会重开它:** 拿到 >= 2 年跨场所资金费历史后,ρ(OKX 书, 同宇宙币安书) 在跨 regime 窗上 **< 0.4** 且场所专属 α 的 CI 不含零。低于这个, 不要再花钱。

## §8 未能取到的东西 / 明示偏离

- 简报给的 `/Users/haosiyu/.../r3_attack_b9646/null.py` 与 `.../r3k/costb_PWR_G230k.json` **在 Mac 上不存在**; 两者都在 **pod2** `/workspace/uplift_2026-09-11/` 下。我用了 pod2 的那两份并记了 sha。
- 速率: OKX 公开端点 **1,908 次请求 / 1,365 s = 1.40 req/s**(顺序 + 0.34 s 间隔), 在 <= 4 req/s 之内, 无签名端点, 无凭据, 从 pod2 发起。
  币安侧走 `data.binance.vision` **静态 CDN**(匿名), 8 并发 —— 依据用户裁定 `STATE.md` L196(2026-09-05, CDN 免除 4 req/s)。这是**明示偏离**, 若裁定者不接受, 按 <= 4 req/s 重拉同一批文件即可, 结论不变。
- 未跑: Hyperliquid 臂(jpline 不可达)、OKX 自己的 4H 收益腿(本轮用钉住的 `meta y4` 币安收益;见下)。

**一条我没做而它会往哪个方向偏的自述**: 候选书的收益腿用的是**币安**的 4h 收益(钉住的 `meta_newprod_v4.npz` y4), 不是 OKX 的 K 线。同币种跨场所永续价格被套利钉住, 两者相关 ≈0.99, 所以这个选择**把 ρ 往高里推**(共享收益因子), 对候选**不利**。
但它偏得很小(§3 显示 ρ 的主要落差来自信号而非收益: 同一收益腿下, 币安信号 0.5634 vs OKX 信号 0.3530), 而且**即便 ρ 真的更低也救不了它** —— §6 的算术说 ρ 就算降到 0, 门槛也只从 3.964 降到 3.705, 而候选是 1.50 ± 2.29, 且没打过零假设。

## §9 ENV 白名单(E-0826-D)

**分析/构建脚本**(`okx_probe.py` `okx_pull.py` `bin_fund_pull.py` `build_fe.py` `sigdiag.py` `analyze.py` `final.py` `alpha.py` `mk_u388.py` `mk_nulls.py` `mk_nulls2.py` `nulltab.py` `tab.py`): 白名单 = **空集**; 每个脚本开头 `assert` 了 17 项装置 env 不在环境里; 全部以 `env -i` 运行。

**装置臂**(`w10_health.py`)逐字白名单, 每次运行都 `env -i`:
```
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
LEGS=001 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 PHI=0
UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz
COSTB_JSON=/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json
FTRIM={zero|off}  FEMAT_NPZ={…/femat_<ARM>.npz 或不设}  OUT_TAG=<TAG>
```
**GATE A 那一次**(复现归档 A0)另加, 逐字抄自 `run_v4_arms.sh`:
```
LEGS=101 … PHI=0.45 COSTB_JSON=…/calib/costb_fee_steady.json
SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy FSEED=42 FPRED=f10_A0_s42.npy
```
每一条命令逐字进了 `receipts/commands.txt`。

## §10 逐字复跑

```
scp devices/okx_probe.py    pod2:/workspace/r9okx_probe.py
ssh pod2 'cd /workspace && env -i /usr/bin/python3 r9okx_probe.py'
scp devices/okx_pull.py     pod2:/workspace/r9okx_pull.py
ssh pod2 'cd /workspace && env -i /usr/bin/python3 r9okx_pull.py'          # 1908 req / 1365 s
scp devices/bin_fund_pull.py pod2:/workspace/r9bin_fund_pull.py
ssh pod2 'cd /workspace && env -i /usr/bin/python3 r9bin_fund_pull.py'
scp devices/build_fe.py     pod2:/workspace/r9okx_build_fe.py
ssh pod2 'cd /workspace && env -i /workspace/venv/bin/python r9okx_build_fe.py'    # GATE B
scp devices/mk_u388.py devices/mk_nulls.py devices/mk_nulls2.py pod2:/workspace/
ssh pod2 'cd /workspace && env -i /workspace/venv/bin/python r9okx_mk_u388.py'
ssh pod2 'cd /workspace && env -i /workspace/venv/bin/python r9okx_mk_nulls2.py'
scp devices/run_arms.sh     pod2:/workspace/r9okx_run_arms.sh
ssh pod2 'bash /workspace/r9okx_run_arms.sh'
scp devices/analyze.py devices/final.py devices/alpha.py devices/nulltab.py devices/sigdiag.py pod2:/workspace/
ssh pod2 'cd /workspace && env -i /workspace/venv/bin/python r9okx_analyze.py'
ssh pod2 'cd /workspace && env -i /workspace/venv/bin/python r9okx_final.py'
ssh pod2 'cd /workspace && env -i /workspace/venv/bin/python r9okx_alpha.py'
ssh pod2 'cd /workspace && env -i /workspace/venv/bin/python r9okx_nulltab.py'
ssh pod2 'cd /workspace && env -i /workspace/venv/bin/python r9okx_sigdiag.py'
```

## §11 产物 sha256(前 16)

| 件 | sha16 | 路径(pod2) |
|---|---|---|
| `w10_health.py`(装置, = dev_v4 那次自报) | `8684d9a9f43a8d15` | `/workspace/r9okx/w10_health.py` |
| `costb_PWR_G230k.json`(成本模型) | `295b4e7b462373e4` | `/workspace/uplift_2026-09-11/r3k/` |
| `okx_funding_raw.npz`(388 名原始结算) | `832d02589c1d52be` | `/workspace/r9okx/` |
| `bin_funding_raw.npz`(692 名, CDN 档案) | `cd2caca631fc3c18` | `/workspace/r9okx/` |
| `fe_mats.npz` | `89d18e29bf141a6f` | `/workspace/r9okx/` |
| `femat_OKX.npz` | `b57f52c4427b421d` | `/workspace/r9okx/` |
| `femat_BINCOLD.npz` | `9686d22e185061ff` | `/workspace/r9okx/` |
| `femat_BINCOLD388.npz` | `691858b8321af526` | `/workspace/r9okx/` |
| `femat_BINWARM.npz` | `13a9877a506f4bd0` | `/workspace/r9okx/` |
| CSHIFT 零假设 53/101/251 | `da83d88513e0f223` / `901a973ab3572b1d` / `d6c7af131d86b2b3` | `/workspace/r9okx/` |
| RELAB 零假设 1/2/3 | `111e0593763d637c` / `869cd39365e3e9e3` / `582227d36dac684e` | `/workspace/r9okx/` |

收据 JSON: `receipts/GATES.json`(GATE A 逐位 + 全部 sha256 全长) · `RESULT_okxrho.json`(主表) · `RESULT_final.json`(亏损格 + 算术) · `RESULT_alpha.json`(场所 alpha) · `RESULT_nulls.json`(零假设) · `RESULT_sigdiag.json`(信号层) · `build_fe_report.json`(GATE B) · `u388_report.json` · `commands.txt`(逐条命令)。

## §12 对账缺口(我没能逐位复现简报给的 A0 规划数 —— 明写)

简报的 A0 无条件规划数是 **+0.6342 bps/锚, 夏普 1.2912, n=9138**。我把 `dev_v4/probe_artifacts/` 里**全部** A0/A0p × dyn/fix × s42/s2027 × {S0_rec, d30_n2_c42_rec} 共 16 格按同一读法(post-warm 丢前 900 + 上界 1788120000)跑了一遍, **没有一格给出这两个数**:

| 最接近的几格 | n | mean g | 夏普 |
|---|---|---|---|
| `V4_A0_dyn_s42` · `S0_rec` | 9138 | +0.6285 | **1.2504** |
| `V4_A0p_dyn_s42` · `d30_n2_c42_rec` | 9138 | +0.6552 | 1.3205 |
| `V4_A0p_dyn_s2027` · `S0_rec` | 9138 | +0.6697 | 1.3181 |
| `V4_A0_dyn_s42` · `d30_n2_c42_rec`(**我用的在役形态**) | 9138 | +0.6872 | 1.3991 |
| `V4_A0_dyn_s2027` · `d30_n2_c42_rec` | 9138 | +0.7121 | 1.4393 |

**n=9138 与窗口上界逐位对上**(所以 post-warm 规则与 E-0911-D 上界我读对了), 对不上的是**臂/键的选择**。这条**不改本轮判决**, 但它是一条要交回去的账:
- ρ 是对**我第一手读到的序列**算的(`V4_A0_dyn_s42` 与 `_s2027` 的 `d30_n2_c42_rec`), 两个种子给 +0.3530 / +0.3600 —— 参照换哪个种子都不动。
- §6 的算术对 A0 参照做了敏感性(下表), **结论对参照的选择不敏感**:

| s1 (A0 参照) | ρ=0.2376(CI 下界) | ρ=0.3530(点估计) | ρ=0.4574(CI 上界) |
|---|---|---|---|
| 1.2912(简报) | 组合 1.7837 / 需 3.9493 | 组合 **1.7082** / 需 **3.9643** | 组合 1.6486 / 需 3.9253 |
| 1.3991(我读, s42 在役形态) | 组合 1.8459 / 需 3.9372 | 组合 1.7660 / 需 3.9660 | 组合 1.7022 / 需 3.9400 |
| 1.4393(我读, s2027) | 组合 1.8703 / 需 3.9318 | 组合 1.7889 / 需 3.9658 | 组合 1.7239 / 需 3.9447 |

**九格里组合夏普全部落在 1.65–1.87, 候选自身需要的夏普全部落在 3.93–3.97。** 距 3.966 的缺口在 **2.10–2.32** 之间。没有一个角落让这条候选变得有用。
