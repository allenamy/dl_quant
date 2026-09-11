> **创建:** 2026-09-11 | **Session:** round-4 P6 (book-uplift-2026-09-11) | **状态:** 预注册草案, 未裁定, 未改任何在役件 | **作废条件:** (a) 用户裁定 ADMIT/REJECT; (b) 面板/口径再换代(v4 链被 v5 取代); (c) §3.4 的 `external_book.target_vector` 重归一化事实被修改或证伪

# PREREG P6 — 独立 Amihud sleeve 的可执行性与录取门

**问的是什么**: 回放里最好的对象(standalone orthogonalised Amihud sleeve)能不能端到端跑到真钱上, 以及它到底买到什么。
**结论先行**: 位级复现的前提 **不是** 障碍(已实测解决); **书层收益** 比之前记的小; **真正的拦路虎在执行侧的一行重归一化代码**。
**本文不改任何东西**, 只给裁定用的门 + 建议 diff(§7 为提议, 未施加)。

---

## 0. 口径钉与前置门

| 项 | 值 | 标签 |
|---|---|---|
| 面板/立方 | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz` (490753×829×7, f16) | VERIFIED (`p6_amihud_parity.log` 首行 `cube 490753 829`) |
| 装置 | `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712…` | VERIFIED |
| 成本 | `r3k/costb_PWR_G230k.json` sha256 `295b4e7b462373e4…` (fitted K=0.17) | VERIFIED (`sha256sum`) |
| 统计量 | g = net_ex/gross_total, bps/锚/单位 gross; 逐锚配对; UTC-日 block bootstrap 2000, `default_rng([20260905,k])`, k∈{0,9} | — |
| 窗 | FULL post-warm: 丢前 LOOK=900 device 锚, 截至 2026-08-10 20Z, **n=9018**(与 E-0911-A 一致) | VERIFIED (逐臂打印 n=9018) |
| 冻结窗 | 2025-03-01 00Z → 2026-08-10 20Z, n=3168 | VERIFIED |

**GATE P(必过, 已过)**: 我的装置 knobs-off 全新跑(非缓存)对四格 `w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027}` 的 `d30_n2_c42_rec` 与 `_W` **全部 bitwise=true, maxabs=0.0**。
收据: `p6_receipts/GATE_P_p6.json`; 复跑命令逐字: `ssh pod2 'cd /workspace/uplift_2026-09-11/p6 && /workspace/venv/bin/python gateP_p6.py'`(日志显示四格 rc=0, 25–27 s, 为真跑)。

**GATE S(信号链同一性, 必过, 已过)**: 我用自己的链重建 round-3 的 `SL_ORTHLAGA_STD_s42`, 与归档件 `d30_n2_c42_rec`/`_W` **bitwise=true, maxabs=0.0**。
收据: `p6_receipts/P6_SLEEVE_PARITY.json`。含义: 下面所有"换一个 Amihud 列"的对照, 换的只有那一列。

---

## 1. 位级复现前提 — **已解决, 且残差在书层值零**

### 1.1 面板那一列到底是什么(逐字)

`pod_panel_ext.py`(pod2:`/workspace/pod_panel_ext.py`):

```
L20  def cs(x): xz = np.where(np.isfinite(x), x, 0).astype(np.float64)
              return np.concatenate([np.zeros((1,NW)), np.cumsum(xz,0)])
L23  r5 = CD[:,:,0].astype(np.float32)                 # ch0 = ret5
L25  CS_r = cs(r5)
L26  qv = np.where(np.isfinite(CD[:,:,3]), CD[:,:,3], np.nan).astype(np.float32)   # ch3 = log_qv
L27  CS_q = cs(np.expm1(np.clip(qv, 0, 30)))
L40  def wsum(CSx, w): return (CSx[E]-CSx[E-w]).astype(np.float32)
L44  F["rev_24h"] = wsum(CS_r, 288)
L48  qv24 = wsum(CS_q, 288)
L54  F["amihud_24h"] = np.where(qv24>0, np.abs(F["rev_24h"])/qv24*1e6, np.nan).astype(np.float32)
```

即: **|Σ288 ch0| / Σ288 expm1(clip(ch3,0,30)) × 1e6**, 两个和都在 float64 全史 cumsum 上做差, 然后 **在 wsum 处落回 float32**, 除法在 float32 里做。

### 1.2 生产者手上有什么

`~/wide_shadow/shadow_loop_v3.py`(只读):

- L355 `CDf = st.cd.astype(np.float32)`; L184 `CACHE_ROWS = 11520`(40 天 ≫ 288 根)
- L357-362 `wstat(ch, w, kind)`: 对 `CDf[ai+1-w:ai+1,:,ch]` 做 `sum`/`mean`, NaN→0
- L385 `CH_NAMES = ["ret5","range","cpos","log_qv","log_cnt","log_avgsz","tbf"]` — **ch0 与 ch3 都在**
- L247 `lqv = math.log1p(qv)`(与 `pod_build_wide` 逐字同式); L150 `CHN_CLIPS[3]=(0.0,25.0)`
- L466 `rev24 = wstat(0, 288, "sum")[m]` — **分子已经在生产者里算好了**

**唯一缺的是分母**: 生产者当前只把 ch3 聚成 `mean`(L387 `kind="mean"`), 而面板要的是 `Σ expm1(ch3)`。`expm1(mean(log qv))` ≠ `mean(expm1(log qv))` —— 这个 Jensen 缺口就是 round-2 "七种定义只到 0.820 秩相关" 的根, **不是信息缺失**。

裁剪口径差(生产者 25 / 面板 30)在全史上**从不咬**: 立方 ch3 全局最大 **22.1875** < 25。VERIFIED(逐块 `np.nanmax`)。

### 1.3 实测四种定义 vs 面板列(同一立方, n=3,140,350 个有限格, 10039 锚)

| 定义 | 位级相等比例 | 最大相对差 | 逐锚 Spearman 均值 | 最小 |
|---|---|---|---|---|
| **Q64** 直接 288 窗求和, float64 累加(仅用 ch0/ch3) | **0.9999996816**(3,140,350 格中 **1 格**不等) | 1.2046e-07 = **1 个 float32 ULP** | **1.0000000** | 0.99999999999999978 |
| Q32 同上但 float32 累加(照抄 wstat 当前写法) | 0.1567 | 1.985e-06 | 0.9999999986 | 0.9999957 |
| R2 生产者现状(mean(log_qv) 再 expm1) | 1.75e-05 | 8.0e+05 | 0.98902 | 0.87363 |
| 研究列(`wide_panel_4h_v2ext.npz`, **ext 立方谱系**) | 0.99878 (NaN 图样**不同**: 3,125,890 vs 3,140,350 有限格) | 4.1e+04 | 0.99954 | 0.55659 |

收据: `p6_receipts/P6_PARITY.json`, `p6_amihud_parity.py`(sha256 `9af3d500…`)。

**读法**: 生产者只要把 ch3 的窗聚合从 `mean` 换成 `Σexpm1(clip(·,0,30))` 并用 float64 累加, 就能逐位重现面板列(3.14M 格里差 1 格 1 ULP), 且**逐锚秩完全相同**。所谓 0.820 是定义错误, 不是通道限制。

### 1.4 残差在书层值多少 —— **零**

独立 sleeve(LEGS=001, PHI=0, FTRIM=off, fitted 成本 G=230k, post-warm n=9018):

| Amihud 列 | Sharpe | mean g | 对照(配对 delta_g) |
|---|---|---|---|
| 研究列(ext 谱系) | 1.4721 | 0.676440 | 基准 |
| 面板重建(holefix2/v4) | 1.4721 | 0.676440 | **+1.68e-17** |
| Q64 生产者形态 | 1.4721 | 0.676440 | **+1.68e-17** |
| Q32 float32 累加 | 1.4720 | 0.676432 | −7.68e-06, CI95 [−3.0e-5, +0.6e-5] |
| R2 生产者现状(错定义) | 1.4153 | 0.656207 | −0.0202, CI95 k0 [−0.0821,+0.0468] k9 [−0.0847,+0.0449] |

收据: `p6_receipts/P6_BOOK.json`, `p6_book.py`。

三条要说清:
1. **秩→正交→sel→cap→EMA→带** 这条链把列级差异吃干净了: ext 谱系与 v4 谱系的列在 0.12% 的格上不同(且有锚的 Spearman 低到 0.556), 书层差 1.68e-17 bps/锚。**研究列建在被禁的 ext 立方上这件事, 在书层不改变任何结论** —— 但它必须被写下来, 因为"位级相等"是在 v4 立方上验的, 不是在 ext 列上验的。
2. 连**错**定义(R2)也只值 −0.057 Sharpe, 且 CI 含 0。所以 §1 的门不是"能不能做到", 而是"做到它几乎白送"。
3. Q32 与 Q64 的差是 float32 累加, 值 −0.000016 Sharpe。建议仍用 float64 累加(§7 diff), 理由是可审计, 不是收益。

### 1.5 这一段的缺口(诚实)

上面的"位级"是**同一个立方**内的位级。生产者的立方是**自己从 REST klines 现搭的**(L276 `for s in st.live`, L294 只填 NaN 行、不覆盖已有行), 与归档立方(monthly zip → holefix2 补洞)在内容上不是同一份。跨数据源的位级相等 **没有被本轮验证, 也无法在 pod 上验证**(需要生产者侧的历史 `rolling.npz`)。见 §6 首锚检查 C1。

---

## 2. 部署形态

### 2.1 不建议做成第四条 msharpe 腿

生产者 L525-533: `w3 = shp/shp.sum()` 由 `st.LR` 三腿 900 锚的 msharpe 决定, 不足 900 锚时 `w3 = [1/3,1/3,1/3]`。加第四条腿意味着:
- 新腿的 `LR` 从零开始 ⇒ 首 900 锚(150 天)退化成 `[1/4]×4`, **新 sleeve 上来就拿 25% 的书**, 且没有任何 msharpe 证据;
- 这正是 E-0911-A 说的 warm-up 区(那里席位返回 [1/3,1/3,1/3] 并绕过 LEGS 掩码), 回放里我们**丢掉**这 900 锚不读, 实盘却要真金白银地走过去;
- 若改成从回放回灌 `LR` 历史, 那是把研究口径的腿收益塞进实盘状态, 属于"回放席位路径 ≠ 实盘席位路径"的已知错误形态。

**建议形态 = 固定配额**, 在 z 合成处一行:

```
z3 = w3[0]*legz["king"] + w3[1]*legz["rev24"] + w3[2]*legz["fund"]     # 不动
z  = (1 - AMI_ALLOC) * z3 + AMI_ALLOC * xz(ami_orth)                    # 新增
```

`AMI_ALLOC` 从 `shadow_bundle/config.json` 读, **默认 0.0**, 裁定通过才改成 0.20。默认 0.0 时全链逐位不变(与 w10_sleeve.py 的 knobs-off 同构, 可以用同一种"默认关=位级不变"的验收)。

### 2.2 信号本体(必须逐字复制, 否则不是被检验的那个对象)

```
ZF  = xz_rows(f_fund_ema_v1)           # scipy.stats.rankdata, AVERAGE ranks
ZA  = xz_rows(amihud_24h)
ZAL = ZA 向后错一个锚 (ZAL[t] = ZA[t-1])
b   = Σ(ZF·ZAL)/Σ(ZF·ZF)  逐锚 OLS(无截距)
sig = ZAL − b·ZF
```
两处刀口:
- **RANK 必须用 `scipy.stats.rankdata`(AVERAGE)**, 不是 `np.argsort(np.argsort(.))` —— `f_fund_ema_v1` 在 10039 行里有 9031 行存在并列, round-1 的 ordinal 排名就是旧口径残差的根。
- **ZAL 的一锚滞后是信号定义的一部分**, 不是保守处理: 生产者必须把上一锚的 `ZA` 持久化(§3.1), 首锚没有它。

### 2.3 与在役各层的交互(逐条)

| 层 | 位置 | 与 sleeve 的关系 |
|---|---|---|
| FTRIM(空头费率剪) | L? `FTRIM=zero` 在 A0; 本 sleeve 回放用 **FTRIM=off** | **未联合检验**。在役书是 FTRIM=zero; 把 sleeve 塞进在役 z 之后, FTRIM 会作用在合成后的 z 上, 这不是我跑过的对象。列为 §8 第一个空洞。 |
| 流动性门 `qv4h ≥ 2.5e5` | 生产者 L474 / 装置 L235 | Amihud 是**非流动性**因子, 门直接砍它的多头尾。已在全部回放数字里(装置逐字同构)。 |
| 中性带 `\|trade\|<band(2.5e-4)` + `alpha=0.1` EMA | L491-493 | sleeve 换手 0.0387/锚 vs A0 0.0304/锚(**+27%**), 带与 EMA 已计入。 |
| 逐名 cap `2.5/nsel` | L484 | sleeve top1 权重占 gross 1.20%(A0 1.10%), top10 10.05%(A0 10.01%) — 不触 cap 结构。 |
| 强制出场(出宇宙/不合格) | L497-513 | 已计入。 |
| 逐名止损 | **已经在数字里**: 我读的 key 是 `d30_n2_c42_rec`, 即 depth −30% / 连续 2 锚 / 冷却 42 锚那一层(装置 L381 `ARMS=[("S0",…),("d30_n2_c42",-0.30,2,42,…)]`) | sleeve 的 1.4721 是**止损后**的数。 |
| 净额(neutrality) | `w[sel] -= w[sel].mean()` | sleeve \|netlong\| 均值 **0.0513** vs A0 **0.0377** — sleeve 更不中性 36%。 |
| 最小名义额地板 | 执行器侧 | **未检验**(回放无 min-notional 层)。sleeve 持名 250.8(A0 249.8), 名数相当, 但权重分布更偏尾。 |

### 2.4 gross / 换手 / 成本 / 容量

post-warm n=9018, fitted 成本 G=230k, seed 42:

| | sleeve | A0 |
|---|---|---|
| 实现 gross(\|sm\|求和, 目标归一到 1) | 0.7173 | 0.6939 |
| 换手/锚 | 0.03871 | 0.03037 |
| 成本 bps/锚 | 0.1232 | 0.0947 |
| 成本 bps/单位换手 | **3.183** | **3.1195** |
| 持名数 | 250.8 | 249.8 |
| carry bps/锚(正=付) | **−0.0358**(收) | **+0.3549**(付) |

**容量阶梯**(同一族 POWER 拟合成本 json, seed 42, FULL post-warm):

| G (USD gross) | sleeve Sharpe (mean g) | A0 Sharpe (mean g) |
|---|---|---|
| 230k | 1.4721 (0.6764) | **1.4150** (0.6890) |
| 460k | 1.4308 (0.6575) | 1.3820 (0.6730) |
| 920k | 1.3542 (0.6223) | 1.3203 (0.6429) |
| 1380k | 1.2798 (0.5881) | 1.2599 (0.6135) |
| 2300k | 1.1334 (0.5208) | 1.1411 (0.5556) |
| 4600k | 0.7736 (0.3555) | 0.8481 (0.4129) |

A0 在 G=230k 读 **1.4150**, 与钉住的 round-3 值**逐位一致** —— 这是我这条分析链的第三个对账点。
读法: sleeve 的 mean g 从 230k→4600k 掉 **−47.4%**, A0 掉 **−40.1%**; sleeve 的容量比 A0 **略差但不致命**, 交叉点在 ~2.3M gross(今日 10×)。收据 `p6_receipts/P6_CAPACITY.json`。

### 2.5 live 宇宙宽度(NTOP=400)不伤它

在役 `shadow_bundle/config.json` 是 `NTOP=400`, 回放用 `MEMBERS_TOPN=829`。把装置改成 400:

| | Sharpe | mean g | delta_g vs 829 |
|---|---|---|---|
| MEMBERS_TOPN=400 | **1.5224** | 0.7314 | +0.0549, CI95 k0 [−0.1656,+0.2974] k9 [−0.1696,+0.2861] |
| MEMBERS_TOPN=600 | 1.4720 | 0.6764 | −0.000024 |

**不显著, 但不是负的**。Amihud sleeve 的 alpha 不住在 400 名之外的尾巴里 —— 这是本轮最重要的正面可部署性证据之一。

---

## 3. 操作路径

### 3.1 `~/wide_shadow` 里必须新增什么

1. `shadow_bundle/config.json` → `params`: `ami_alloc`(默认 **0.0**), `ami_cov_min`(0.95), `ami_clip_hi`(30.0), `ami_lag`(1)。
2. `shadow_loop_v3.py`: `wstat` 增加 `kind="expsum"`; 在 L466 `rev24` 之后算 `qv24`/`ami`; 正交化; z 合成加一项(§7 diff)。
3. **新状态** `state/ami_prev.json`: `{"anchor_ts": int, "z": {panel_idx: float}}` —— 一锚滞后的 ZA。必须随 `rolling.npz`/`prev_rec` 一起原子落盘, 否则重启后首锚无滞后量。
4. `tests_target_live_output.py`: 增加"`ami_alloc=0` ⇒ 权重向量与旧码逐位相等"的断言(这是整个改动的安全底座)。
5. 告警行: `{"e":"ami_degraded", ...}` 进 `shadow_log.jsonl`, 并进 `heartbeat.json`。

### 3.2 延迟预算 —— 不是问题

- 新增计算量: 对 `CDf[ai+1-288:ai+1,:,:]` 的 ch3 做一次 `expm1+clip+sum`。实测(11520×400 的立方形状, pod2): **0.285 ms**(中位, 20 次)。`CDf` 的 f16→f32 转换本来每锚就做一次(L355), 不是新增。收据 `p6_receipts/P6_OPS.json`。
- **不需要任何新 API 调用**: ch3 已在既有 klines 拉取里。venue weight 预算(L123 上限 240/min)不变。
- 现状预算(最近 155 个 `e=="signal"` 锚, `~/wide_shadow/shadow_log.jsonl`): 起跑偏移 `SHADOW_OFFSET_MIN=16`(launchd plist), runtime 中位 **315.8 s** → N+21:16; p90 **340.9 s** → N+21:41; p99 **516.3 s**; max **570.8 s**。
- 对 N+22:40 硬线(=锚后 1360 s)的余量: p90 剩 **59 s**; **155 锚里已有 4 锚(2.6%)超线**(1786881600/498.1s, 1787083200/516.3s, 1787385600/570.8s, 1788048000/507.7s)。
- 结论: sleeve 加的 0.285 ms 在这个预算里是噪声; **但这个预算本来就已经在 2.6% 的锚上破线**, 那是一个独立的、先于本提案存在的问题, 不应该被本提案的验收吞掉。

### 3.3 输入陈旧/缺失时的行为(实测 + 代码读)

**实测(不是推测)**: 288 窗覆盖率 <100% 的格占有限格的 **0.137%**, <95% 占 0.129%, <50% 占 0.068%, 最低覆盖 0.35%(288 根里 1 根)。这些低覆盖格的 Amihud 逐锚 z-秩均值是 **−0.0847**(满覆盖格 +0.0042) —— 即**偏向流动端**, 不是我事先猜的"分母塌陷⇒假装极度非流动"。我的先验错了, 记在这里。收据 `P6_OPS.json`。

**代码读(INFERRED from source, 未实测)**: 真正的 fail-open 在别处, 有两层:

- **L471** `z = w3[0]*np.nan_to_num(legz["king"]) + …`。若 sleeve 那一项全 NaN, `nan_to_num` 把它变成 0 向量; 随后 **L482 `w /= g`** 把整本书重新归一到 gross 1。结果: **sleeve 静默消失, 其余三腿被放大回满仓, 无任何告警**。这就是 sigma_ladder 的同一形态。
- **`~/dl_quant_live/live/external_book.py` L483-490 `target_vector`**: `gn = ext["gross_in"]; return w/gn` —— 执行器**无条件**把生产者写的 gross 除掉, 注释自陈 "sum|.| == 1 over the IN-UNIVERSE book, so to_notional(., gross) gives a live gross of exactly NAV × gross_mult"。
  **含义(本轮最重要的操作发现)**: **生产者根本无法通过 target_live 表达"降风险"**。任何"降级时少跑 20% gross"的设计在当前契约下都会被执行器重新拉满。

**第三层, 也是最难看的一层(VERIFIED by grep)**: 生产者**根本没有"还在跑但降级了"的告警通道**。
`~/dl_quant_live` 里没有任何代码读 `~/wide_shadow/heartbeat.json`(全仓 grep `heartbeat` 只命中 `live/telegram_notify.py` 自己的 token 自检)。生产者已接线的升级通道只有两条:
(i) **不写 target_live** —— 触发执行器逐名门平仓(E-0909-G 那条路), 为了一条死掉的 sleeve 去平掉整本书, 过激;
(ii) `~/wide_shadow/KILL` 文件 —— 停循环, 于是退化成 (i)。
所以"写一行 `e=ami_degraded` 到 `shadow_log.jsonl`"是一个**没有人看的标记**。只上标记不上看守, 正是"声明的盲区≠关闭"。

因此 fail-safe 三选一, 且都要裁定:
- **(A) 告警 + 看守(不改执行器)**: 降级锚 `ami_alloc=0` 写书, 写 `e=ami_degraded` 与 `heartbeat.ami_status="DEGRADED"`, **并新建一个看守进程去读它**。代价: 书在那一锚退回 A0 形态的满仓三腿书 —— 可接受的降级目标, 但**看守必须先存在并被演练响过**(门 C4), 否则 (A) 等于没有。
- **(B) 改 `wide_target_v1` schema 加 `risk_scale`**: 执行器 `target_vector` 改成 `w/gn * risk_scale`。这是真钱仓的改动, 必须走 `ops/safe_commit.sh` + 全绿电池, 且本身就是一次独立的书行为改动, **应当单独预注册**, 不搭本提案的车。
- **(C) 不部署**: 承认在没有 (A) 的看守或 (B) 的 schema 之前, 这条 sleeve 没有可接受的失败形态。

**建议: (A), 且看守先于 `ami_alloc=0.20` 上线。** (B) 单开一案。

### 3.4 回滚

`ami_alloc` 从 0.20 改回 **0.0** 即逐位回到今天的书(前提: §6 的 C0 位级不变门通过)。不需要回滚 `rolling.npz`, 不需要重启执行器, 下一锚生效。`state/ami_prev.json` 留着无害。

---

## 4. 冻结验收门(裁定就按这个读, 先于任何新数字)

**对象**: A0(在役形态)与独立 Amihud sleeve 的**固定配额组合**, 配额 a=0.20。
**统计量**: 逐锚配对, g = net_ex/gross_total; UTC-日 block bootstrap 2000, `default_rng([20260905,k])`, k∈{0,9}。
**成本**: `costb_PWR_G230k.json`(fitted K=0.17), **不是**部署成本模型, 不是 K=1。
**窗**: FULL post-warm n=9018 **与** 冻结窗 n=3168, **两个都要报**。
**种子**: 42 与 2027(LEGS=001/PHI=0 下 sleeve 对种子逐位不变, 但 A0 侧不是, 所以配对必须同种子)。

**ADMIT 需要同时**:
- **G1** FULL post-warm 的 **ΔSharpe** 下界 > 0, **两个 k、两个种子共 4 格全过**;
- **G2** 冻结窗 ΔSharpe 点估计 > 0, 且 4 格中 ≥3 格下界 > 0;
- **G3** FULL post-warm 的 **Δg 点估计 ≥ −0.010 bps/锚/单位 gross**(见 §5: 这是**负**的, 门必须显式承认);
- **G4** 位级不变门 C0(§6)通过;
- **G5** §3.3 的 fail-safe 走的是 (A), **且那个看守进程已经存在并在 C4 演练中真的报过警**(今天它不存在 ⇒ 今天 G5 必然 FAIL)。

**A0 一侧的定义(避免拿错对照)**: `A0_PWR230k_s42` 的 config 自报 `LEGS=101, PHI=0.45, FTRIM=zero, FTRIM_TH=-0.001, CAL=log, WRULE=msharpe, LOOK=900, MEMBERS_TOPN=829, UMASK_SCOPE=m1, W3FIX=None(dyn), FEMAT_NPZ=None` —— 即在役形态。VERIFIED(读 npz 的 `config_json`)。

**REJECT** 若 G1 任一格下界 ≤ 0, 或 G3 破 −0.010, 或 C0 不位级相等。
**UNDECIDED** 其余。

**已经跑出来的这四格(预注册前的实测, 按上表读)**:

| a | 种子 | ΔSharpe 点 | CI95 k=0 | CI95 k=9 | 冻结 ΔSharpe 点 | 冻结 CI95 k=0 | Δg 点 |
|---|---|---|---|---|---|---|---|
| 0.20 | 42 | **+0.2458** | [+0.0336, +0.4587] | [+0.0315, +0.4719] | +0.3290 | [+0.0180, +0.6523] | **−0.00252** |
| 0.20 | 2027 | **+0.2407** | [+0.0319, +0.4553] | [+0.0305, +0.4638] | +0.3009 | [**−0.0046**, +0.6204] | **−0.00581** |
| 0.30 | 42 | +0.3591 | [+0.0195, +0.7016] | [+0.0089, +0.7195] | +0.4795 | [−0.0381, +1.0263] | −0.00377 |
| 0.30 | 2027 | +0.3512 | [+0.0142, +0.6931] | [+0.0034, +0.7077] | +0.4354 | [−0.0685, +0.9736] | −0.00872 |
| 0.40 | 42 | +0.4456 | [**−0.0356**, +0.9313] | [−0.0604, +0.9694] | +0.5796 | [−0.1961, +1.3918] | −0.00503 |
| 0.50 | 42 | +0.4878 | [**−0.1449**, +1.1253] | [−0.1761, +1.1481] | +0.5814 | [−0.4642, +1.6653] | −0.00629 |

收据: `p6_receipts/P6_COMBO_PAIRED.json`, `p6_combo2.py`。

**按这张表**: a=0.20 过 G1(4/4)、过 G3; **G2 只有 3/4**(s2027 冻结下界 −0.0046, 差一点) ⇒ 恰好落在 "≥3 格" 的边上。a=0.30 过 G1 但 **G2 0/4**。a≥0.40 连 G1 都不过。
**所以预注册的配额是 a=0.20, 不是 0.50。** 这一点必须在看数字之前就钉死 —— 它已经钉死了(本表就是钉子; 我不再去找更好的 a)。

---

## 5. 它到底买到什么 —— 诚实版

post-warm n=9018, fitted 成本 G=230k:

| | seed 42 | seed 2027 |
|---|---|---|
| A0 Sharpe | **1.4150** | 1.4370 |
| sleeve 独立 Sharpe | 1.4721 | 1.4721 |
| ρ(A0, sleeve) FULL | **+0.1490** | +0.1553 |
| ρ 冻结窗 | −0.0124 | +0.0292 |
| 组合 a=0.20 | **1.6608** | 1.6777 |
| 组合 a=0.50 | **1.9028** | 1.9122 |

**"1.42 → 约 1.90" 是真的, 但只在 a=0.50 上成立, 而 a=0.50 的配对 ΔSharpe CI 含 0(P(Δ>0)=0.93)。** 在能过门的 a=0.20 上, 它买到的是 **1.4150 → 1.6608, 即 +0.246 Sharpe**。

**更要紧的一句**: 每一个配额上 **Δg 都是负的**(−0.0025 ~ −0.0145 bps/锚/单位 gross), 且 P(Δg>0) ≈ 0.48。
**sleeve 不是来赚钱的, 是来降波动的。** 在 gross 被政策钉死在 2.0×NAV 的世界里, 这等于**用一点点钱换夏普**: a=0.20 大约 −0.0025 bps/锚 × 2190 锚 × 2.0 gross ≈ **−11 bps/年的 NAV**(INFERRED, 线性外推)。如果将来能按夏普再加杠杆, 这笔交易划算; 如果 gross 永远是 2.0, 这笔交易**在纯收益口径上是亏的**, 买的是回撤。

**逐年(seed 42, fitted 成本)**:

| | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| A0 | 0.480 | **−1.936** | 1.088 | 1.187 | 5.433 |
| sleeve | 0.168 | **+1.861** | 1.197 | 1.379 | 2.407 |
| 组合 a=0.20 | — | **−1.237** | 1.239 | 1.408 | 5.944 |
| 组合 a=0.50 | — | **+0.137** | 1.364 | 1.702 | 6.100 |

sleeve 的全部卖点在 **2023**(A0 的死年)。2022 它自己只有 **0.168** —— round-3 说它 "HAS 2022"(不像 RESID_SHARPE), 字面为真, 但 0.168 不是证据, 只是不为负; 而且 2022 前 900 锚(到 2022-05-31)按 E-0911-A 已被丢掉。

**组合的成本项是上界**(INFERRED): 我把两本书在 g 层线性组合, 等于假设总 gross 不变、成本按 gross 加权平均。真实的合成书会**净掉**两腿的对冲交易, 换手只会更低, 所以真书的成本 ≤ 这里的成本。但 alpha 项只有在两腿不在中性带内互相抵消时才精确 —— **这不是一本跑过的书**, 是两组合计算。要把它变成跑过的书, 需要把 sleeve 接进装置的 z 合成里再跑一遍(§8 空洞 1)。

---

## 6. 首锚检查(上线当锚必须逐条打勾, 缺一条就回滚)

- **C0 位级不变门(上线前)**: `ami_alloc=0.0` 跑一个历史锚, 权重向量与旧码 **逐位相等**(`tests_target_live_output.py` 断言)。不等 ⇒ 停, 不上线。
- **C1 跨源列对账**: 当锚生产者算出的 `ami[m]` 与用同一锚归档立方按 §1.1 recipe 算出的值, 报 **逐锚 Spearman 与位级相等比例**。门: Spearman ≥ 0.999。低于 ⇒ 只告警不回滚(这是跨数据源差, 不是代码差), 但要进当日日志。
- **C2 滞后正确性**: 日志里 `ami_prev.anchor_ts == anchor − 14400`。不等 ⇒ 该锚 `ami_alloc=0` + 告警。
- **C3 覆盖门**: 报 `frac(cov288 < 0.95)` 在成员集上的值。回放基线 0.129%; 若 >2% ⇒ 告警。
- **C4 降级演练(硬门)**: 上线当锚**人为**把 `ami` 置空跑一次(影子, 不落 target_live), 确认 (a) 日志出现 `e=ami_degraded`, (b) `heartbeat.json.ami_status=="DEGRADED"`, (c) **新建的看守进程真的报了警**(不是"应该会报"), (d) 权重向量等于 `ami_alloc=0` 的向量。**没响 = 不上线**。今天这个看守**不存在**(§3.3 第三层), 所以 C4 现在必然失败 —— 这是 ADMIT 前必须先补的工程, 不是验收时再看的细节。
- **C5 gross 对账**: `target_live.gross_norm` 与上一锚的比值落在 [0.9, 1.1]; 且提醒读者 —— 执行器会把它除掉(§3.3), 所以这个数只是生产者侧的自检, **不是风险控制**。
- **C6 换手**: 当锚 turnover 相对上一锚 ≤ +40%(回放 sleeve 比 A0 高 27%, 首锚会有一次性重构)。

---

## 7. 提议的 diff(**未施加**, 仅供裁定; 真钱仓一律不碰)

见 `PROPOSED_DIFF_p6_amihud_producer_2026-09-11.txt`(同目录)。要点:
1. `wstat` 加 `kind="expsum"`(float64 累加);
2. `rev24` 之后算 `qv24` / `cov288` / `ami`(带 `cov288 >= ami_cov_min` 的 **fail-CLOSED** 掩码);
3. `ami_prev` 状态 + 一锚滞后 + 逐锚无截距 OLS 正交化;
4. z 合成一行, `AMI_ALLOC` 默认 0.0;
5. 降级路径: `ami_alloc=0` **并且**写 `e=ami_degraded` 告警行(不静默)。

`ELIGIBILITY_CONTRACT.json` / `judge_v4.py` 无需改动。

---

## 8. 本文没有证明的(空洞, 按重要性排)

1. **合成书没跑过**。§5 的 1.66/1.90 是 g 层两组合计算, 不是一本跑过的书。ADMIT 之前应当把 sleeve 接进装置 z 合成再跑一次(装置改动 + 新 GATE P)。
2. **FTRIM 联合未检验**。sleeve 的全部回放是 `FTRIM=off`; 在役书是 `FTRIM=zero`。合成后 FTRIM 作用在合成 z 上, 是没测过的对象。
3. **跨数据源位级未验**(§1.5)。只能在生产者侧首锚验(C1)。
4. **min-notional 地板未检验**(回放层不存在)。
5. **round-1/2 的 placebo 折价**: round-3 说每个 round-1/2 的 placebo margin 要按 53–448% 向臂有利方向折。本 sleeve 在 round-3 的 repaired placebo 上 **SURVIVE on FULL**(与 Amihud 家族一起, K=12 Bonferroni), 但**冻结窗上的 placebo 没有单独复验**, 而 §4 的 G2 正好落在冻结窗上。
6. **ρ=0.149 是全周期值**; 冻结窗 ρ 是 −0.012/+0.029。低相关在两个窗上都成立, 但样本不同, 不要当成一个数。
7. **2026 年 sleeve 只有 2.407 而 A0 有 5.433** —— 组合在 2026 是靠 A0 抬的; 如果 2026 的 A0 表现本身是 regime rent(round-3: 冻结窗付 2.07× 跨 regime 均值), 那么组合在正常 regime 下的样子更接近 2023-2025 那三年, 而不是这张表的加权平均。
