> **创建:** 2026-09-13 ~08:35Z | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T5, 任务 T5c) | **状态:** 完成; 判据冻结于 `PREREG_T5c_september_replay_vs_deployed_2026-09-13.md` sha256 `a669c627…6a48`(2026-09-13 08:05:22Z, 先于任何 T5c 结果数字); 冻结后未改窗/组/读法; 未经 lead 复跑 | **作废条件:** 部署书存档被改写; x0910 延展产物、T1 回放臂或 KA 数组被替换; 用户改比较层
> **口径:** 目标文件层; king 链; 价格用 x0910 记账元 RAW y4(= RAW 补丁 DL 目标, 逐位核对), carry 同 T1/T5, 成本用 `costb_PWR_G230k`, 净额 = 价格 − carry − 成本; bps / 4h 锚 / 该书单位 gross。全部数字由 `devices/t5c_tables.py` 从收据渲染到 `receipts/TABLES_T5c.md`; §6.3 的逐日表来自事后装置 `devices/t5c_posthoc_days.py`。
> **实盘零接触(VERIFIED):** `~/dl_quant_live` 与 `~/wide_shadow` 只读; 部署文件拷到 `T5c/private/`(gitignored, 739 个文件, `private/COPY_SHA256.txt`); 无任何 API 调用。pod2 只用 CPU, 全部装置在 `nice -n 10` 下运行, 并行 ≤ 16 核, 前后 `nvidia-smi` 0 % / 2 MiB, PID 333197 / 339489 全程 `Tl` 未触碰。未写 T4b / T5b / T6 / T7 / `parity_replay_2026-09-12/phase2`。未提交。
> **后续指针(T5d, 2026-09-13):** 本文延展段的回放读了错误的结算间隔; 用真实间隔重跑、两个差(固定权重 / 重生成权重)与修正后的标签谓词见 `../T5d/RESULT_T5d_iv_corrected_replay_2026-09-13.md`。本文其余内容未改。

# RESULT · T5c · 九月同锚: 回放书是否也亏

## §0 一页

**回答: 是, 在 king 链的目标文件层上, 回放也亏了, 而且亏在同一批空头名上。** 部署 king 链与回放 king 链的价格差, CI 含 0; 按预注册读法标签为「策略自身的亏损(king 链)」。价格、carry、净额在两个种子上一致, 去掉 09-06 后一致, 换另一条回放 king 谱系后也一致。

| 结果量(61 锚, 11 个日块, CI 只作描述) | 部署 king 链 D_K | 回放 king 链 R_K(s42 / s2027) | D_K − R_K(s42) | 标签 |
|---|---|---|---|---|
| 价格 | −5.96 [−15.89, +2.82] | **−4.76 / −5.07** | −1.20 [−4.19, +1.59] | 策略自身的亏损 |
| carry | +1.18 [+0.69, +1.75] | +1.00 / +1.00 | +0.18 [−0.22, +0.63] | 策略自身的亏损 |
| 成本 | +0.082 | +0.107 / +0.106 | −0.024 [−0.038, −0.011] | 部署差异(量级很小) |
| 净额 | −7.23 [−17.03, +1.45] | −5.87 / −6.17 | −1.36 [−4.35, +1.43] | 策略自身的亏损 |

- **同一批名亏钱**: 部署 king 链空头亏损最大的 USELESS、FLOCK、COTI、MINA、ARB、PORTAL、NEAR、INJ, 回放也持有同向空头, 并且亏得一样多或更多(例: FLOCK 部署 −37.0、回放 −52.6)。回放的空头侧价格 **−6.88**, 比部署的 −4.46 更差。
- **差在多头侧**: 部署多头 −1.50, 回放 +2.12; 多头差 −3.62 [−7.21, −0.21](s2027 −3.30 [−6.88, +0.07], CI 含 0); 空头差 +2.42 [+0.83, +3.95](s2027 +2.41 [+0.82, +3.93])。
- **价格差由相互抵消的构造分量组成**(Shapley 均值, bps/锚): 窗内部署在 09-02 12Z 前没有 FTRIM, 这让部署价格更好 +1.32(09-02 12Z 前每锚 +3.52, 之后 +0.60); 回放独有的逐名止损层让回放更好 −1.15 / −0.80; 分数差 −0.62; fund 值 −0.55; 席位 +0.49(播种前 +1.61, 之后 −0.92)。总差 CI 含 0, 各分量**占比**的 CI 跨越正负数百个百分点 —— 预注册的占比读法形式上成立(价格最大分量 = FTRIM, 两种子与固定顺序一致; |REM 占比| ≥ 50% ⇒「分数驱动」), 但没有解释力, 解读应看 bps 均值。
- **king 链能代表整本书**: 部署书与部署 king 链的逐锚价格相关 0.995, 均差 +0.60 [−0.16, +1.34]。
- **事后描述**: 两本 king 链逐锚价格相关 0.853, 78.7% 的锚同号; 最差的日子重合(09-06 部署 −38.2、回放 −33.4; 09-03 −13.0 / −12.4; 09-09 −22.5 / −17.0)。唯一明显的单锚部署特有亏损是 09-01 08Z(−69.4 对 −10.7); 该锚恰是生产者换 booster 的第一个锚, 这只是时间上的重合, 本文没有归因。
- **范围**: 只比 king 链, **V2MAIN 臂 NOT MEASURED**(08-30 20Z 之后没有任何折外 V2MAIN 分数)。比较层 = 目标文件层: 执行器在 `target_live` 之后另有逐名止损(T5b 在查)与 09-06 的单日止损平仓, 都不在本文比较内; **实现账本层的比较不在范围内**。

## §1 门(`receipts/TABLES_T5c.md` T0)
| 门 | 结果 | 标签 |
|---|---|---|
| G-FREEZE / G-ENV / G-POD | 每个装置断言预注册 sha 与 env 白名单; nice, ≤ 16 核, GPU 前后 0 % / 2 MiB, 保护 PID 不变 | VERIFIED |
| G-UM | 延展掩码前 10,039 行与原文件逐位相同, 新增 60 行 = 末行 | VERIFIED |
| **G-X** | KA 两个种子的回放在 ≤ 08-30 20Z 的 10,038 行上, 20 个数组(rec、W、T1 逐腿数组、R18A、S0、legs 序列)与 T1 臂 C0 **逐位相同** ⇒ 九月回放是 A0 的精确延续 | VERIFIED |
| G-KC(不阻断) | 8d79186b 在 v4 研究特征上对 A0 king 的 2026 重叠: 94.0% 格逐位相同, 1–7 月逐锚 Spearman 中位 1.0000, **8 月中位 0.9620**(最小 0.9027) | 已标注: 特征谱系切换 |
| G-RAW | 装置 y4 = x0910 记账元 = dlw RAW `y4s`, 窗内逐位相同 | VERIFIED |
| G-SIM-R | 模拟器全回放节点的 king 链与逐腿态对装置 dump max\|Δ\| = 0.0(KA、KB, 两个种子, 66 锚) | VERIFIED |
| G-T1c | 部署书价格与 carry 在 61 锚上复现 T1 D2(max\|Δ\| 2.2e-14 / 0.0); T5 §6.2 空头价格 −4.5274112841 复现 | VERIFIED |
| G-CLOSE | 价格、carry、成本、净额的 Shapley 与固定顺序分解逐锚闭合, 最大残差 3.6e-14 | VERIFIED |
| G-ARCH-D | 66 锚 target_live = 0.55·kc + 0.45·fc, 差 0.0 | VERIFIED |
| G-ING-S / V / T | sel 计数逐锚等于生产者日志; EMA 逆推复现存储 fund z(0.0); 844 个 FTRIM 记录名的 rn8 逐一复现(0.0) | VERIFIED |
| **G-ING-B(不阻断)** | 09-13 04Z 的 M1 fund z 逐位复现(0.0); 但 M1 冷启动两锚的基分布大小重建 522 名, 生产者日志为 **449(09-04 04Z)与 460(08Z)**, 此后各锚一致 | B 组在这两锚上「重建未验证」 |

## §2 锚集
- 窗 2026-08-31 00Z..09-10 00Z, **61 锚全部合格**, 11 个 UTC 日块(09-10 块只有 00Z 一锚)。RAW y4 到 09-10 20Z, 但 carry 与 fund 值需要的 x0910 面板止于 09-10 00Z, 故终点为 09-10 00Z。
- 窗内每个锚的 target_live 都由 combo_stage 写, kc/fc 状态全部 own(08-30 04Z 暖启动在窗前)。生产改动锚: booster 09-01 08Z、FTRIM 09-02 12Z、M1 09-04 04Z、席位播种 09-05 16Z。
- **09-06**: 目标层照常入主分析; 去掉该日六锚后, 价格差 −0.81 [−3.93, +2.05](s42)/ −0.46(s2027), 全部标签不变。
- **09-12 12:47Z 全书平仓**在窗外, 没有锚受影响。

## §3 分数来源
- **V2MAIN: NOT MEASURED。** V2MAIN 月度折只有 202501..202608(pod2 `f8_v4/mwf/RAW_s42/shard*/preds_fold/`); r6 延展树的 `f10_A0_s{42,2027}.npy` 末个有限锚 08-30 20Z; `r6/out/f8_v4_x0910/preds/` 为空。没有造、没有替代, 所以只比 king 链。
- **回放 king(主, KA)**: ≤ 08-30 20Z 逐位沿用 A0 的 `SLOW_v3_on_v4axis`(连 08-31 六锚在内的 A0 king 本来就是 NaN); 08-31 00Z..09-10 20Z 用 A0 同一 booster **8d79186b**(只用 2026 年前数据训练 ⇒ 窗内全部样本外)在 x0910 v4 研究特征上打分, 格规则逐字照 T4。**INFERRED / 已标注**: A0 的 2026 king 用 v2ext 特征, 该文件没有九月; G-KC 显示两套特征在 1–7 月给出相同排名, 在 8 月分歧(中位 0.962), 所以九月回放 king 是「A0 的 booster + 修补后的研究特征」, 不是 A0 逐字谱系。
- **敏感性 (KB)**: 全史改用 bundle v4 谱系 `SLOW_v4_x0910`: 回放价格 −4.39 / −4.38, 差 −1.57 [−4.56, +1.37], 标签与 KA 相同。

## §4 读法(`TABLES_T5c.md` T1)
- **价格**: SAME-LOSS 成立(回放均值在部署均值 CI 内), DEPLOYMENT-GAP 不成立(配对差 CI 含 0)⇒ **策略自身的亏损(king 链)**, 两个种子、去 09-06、KB 全部相同。
- **必须说清的分辨率**: 部署均值的 CI [−15.9, +2.8] 很宽, 所以 SAME-LOSS 这一半容易成立; 有信息量的是配对差 [−4.19, +1.59] —— 它排除不了最多 −4.2 bps/锚的部署差距, 也排除不了 +1.6。点估计上, 回放复现了部署 king 链价格亏损的约 80%(s42: −4.76 / −5.96)与 85%(s2027: −5.07 / −5.96)。
- carry、净额同为「策略自身的亏损」; 成本为「部署差异」, 但只有 −0.024 bps/锚(部署 king 链换手更少)。
- T1 表的配对差 CI 与 T3 表的总差 CI 数值略不同, 因为预注册给读法与 Shapley 各分配了不同的自举流(k 87 与 k 82)。

## §5 分解(king 链, `TABLES_T5c.md` T3)
| 分量 | 价格 s42 | 价格 s2027 | carry s42 | 净额 s42 |
|---|---|---|---|---|
| T FTRIM(部署 09-02 12Z 前无) | **+1.32** [+0.20, +2.56] | +1.32 | **+0.42** [+0.10, +0.80] | +0.90 |
| W 席位(含 09-05 播种) | +0.49 | +0.48 | −0.02 | +0.52 |
| B fund 秩基(含 09-04 M1) | −0.13 | −0.14 | −0.06 | −0.06 |
| V fund 值与新鲜度 | −0.55 | −0.57 | −0.08 | −0.47 |
| M 成员集 | +0.01 [−3.45, +3.87] | +0.02 | −0.09 | +0.10 |
| X 出场 / S 可交易门 | −0.14 / −0.19 | −0.15 / −0.21 | −0.01 / −0.01 | −0.13 / −0.18 |
| P 回放止损层 | **−1.15** [−3.41, +0.39] | −0.80 | +0.02 | −1.16 |
| H 状态路径(08-30 04Z 暖启动) | −0.24 | −0.24 | +0.04 | −0.28 |
| REM 分数差与未对上部分 | **−0.62** [−1.32, +0.08] | −0.62 | −0.03 | −0.58 |
| **合计 D_K − R_K** | −1.20 [−3.97, +1.54] | −0.90 | +0.18 | −1.36 |
- **分段(价格, s42)**: φ_T 在 09-02 12Z 前每锚 **+3.52**、之后 +0.60 —— 回放的 FTRIM 在生产加上 FTRIM 之前让回放少赚了价格, 与 r15「FTRIM 省下的 carry 大部分以价格归还」同向; 之后两边都有 FTRIM, 差距基本消失。φ_W 播种前 +1.61、之后 −0.92。REM 在 booster 切换前 −0.41、之后 −0.65。
- **解读(描述)**: 部署与回放 king 链之间的价格差不是某一个部署缺陷造成的。几个真实的构造差互相抵消: FTRIM 缺席帮了部署, 止损层与分数差帮了回放。carry 差 +0.18 几乎全部来自 FTRIM(+0.42), 与 T5 八月的机制相同, 但九月已经小得多。

## §6 同一批名(`TABLES_T5c.md` T4–T6)
### §6.1 多空拆分
| 书 | 多头价格 | 空头价格 | 空头 gross 份额 |
|---|---|---|---|
| 部署 king 链 | −1.50 [−17.14, +12.35] | −4.46 [−15.65, +7.59] | 0.530 |
| 回放 king 链 s42 | +2.12 [−12.61, +14.35] | **−6.88** [−17.39, +4.93] | 0.535 |
| 差(部署 − 回放)s42 / s2027 | −3.62 [−7.21, −0.21] / −3.30 [−6.88, +0.07] | +2.42 [+0.83, +3.95] / +2.41 [+0.82, +3.93] | |

### §6.2 部署 king 链空头亏损最大的名(窗内求和, bps; 权重 ×1e3)
| 名 | 部署空头 Σ | 回放空头 Σ | w_D | w_R |
|---|---|---|---|---|
| USELESSUSDT | −47.9 | −64.5 | −0.34 | −3.24 |
| FLOCKUSDT | −37.0 | −52.6 | −5.50 | −3.81 |
| COTIUSDT | −30.3 | −35.0 | −8.00 | −8.01 |
| MINAUSDT | −29.7 | −38.5 | −7.60 | −9.85 |
| ARBUSDT | −28.6 | −31.2 | −4.10 | −4.02 |
| PORTALUSDT | −14.2 | −17.3 | −7.95 | −10.12 |
| NEARUSDT | −13.8 | −17.0 | −3.90 | −4.97 |
| SIGNUSDT | −13.7 | 0.0 | −5.33 | 0.00 |
| INJUSDT | −13.6 | −17.1 | −5.77 | −6.71 |
| WALUSDT | −11.4 | 0.0 | −5.96 | 0.00 |
- 表中十个名里八个回放也做空且亏得更多(前 12 名中是 10 个, 见 `TABLES_T5c.md` T5); SIGN、WAL 只在部署书里(成员集差)。
- **部署比回放差的名**(逐名价格差, bps/锚): CYS −1.14 与 BTR −0.92(只在部署成员集, 部署做多), COLLECT −0.65、STAR −0.52(两边都多, 部署更重), CAP −0.43(只有回放做空)。按分量: 成员集 M 的负向名 BTR、CYS; 止损层 P 的负向名 COLLECT、STAR、VELVET、RIVER(回放封锁了这些多头)。

### §6.3 同锚(事后, 描述; `receipts/RECEIPT_T5c_posthoc_days.json`)
| UTC 日 | 部署 king 链价格 | 回放 king 链价格(s42) |
|---|---|---|
| 08-31 | −9.42 | −4.50 |
| 09-01 | +9.39 | +6.04 |
| 09-02 | +8.88 | +14.98 |
| 09-03 | −13.01 | −12.37 |
| 09-04 | −2.03 | −2.52 |
| 09-05 | +12.88 | +6.34 |
| 09-06 | **−38.18** | **−33.39** |
| 09-07 | +6.35 | +1.41 |
| 09-08 | −8.60 | −7.42 |
| 09-09 | −22.50 | −17.01 |
| 09-10(1 锚) | −26.29 | +0.07 |
逐锚相关 0.853(s2027 0.853), 同号 78.7%。部署 king 链最差五锚: 09-06 04Z −101.5(回放 −88.2)、09-06 00Z −76.7(−75.1)、**09-01 08Z −69.4(−10.7)**、09-09 20Z −67.4(−39.9)、09-08 08Z −45.2(−49.7)。

## §7 king 链与整本书
部署书价格 −5.36, 部署 V2MAIN 链 −4.42, 部署 king 链 −5.96; 书与 king 链逐锚相关 0.995。V2MAIN 链没有回放对照(§3)。

## §8 VERIFIED 与 INFERRED
**VERIFIED(有逐位或逐锚收据)**: 窗终点与覆盖; 记账 y4 为 RAW 补丁口径; 九月无折外 V2MAIN 分数; 各生产改动的首锚; 九月回放是 A0 的逐位延续(G-X); 模拟器与装置逐位相同; 部署书 = 0.55·kc + 0.45·fc; T1 D2 与 T5 §6.2 复现; sel、EMA、FTRIM rn8 的重建逐位成立; 全部分解闭合。
**INFERRED 或已标注**:
- 九月回放 king 是 A0 booster 配修补后的研究特征, 不是 A0 逐字谱系(G-KC 8 月中位 0.962); KB 谱系给出相同标签。
- 回放止损层在窗内新触发 18 次; A0 装置按混合书深度判止损, 而九月的 V2MAIN 链没有 V2MAIN 分数, 所以 P 组的回放版本受这一点影响。
- M1 冷启动两锚的基分布比生产宽(522 对 449 / 460)。
- 「策略自身的亏损」只在 king 链、目标文件层成立; 不是整本书的判决, 也不是实现层的判决。
- 分量的机制解读(FTRIM 以价格归还 carry、止损层帮回放避开多头)是描述, 不是因果检验。

## §9 范围之外
- **执行器层**: 执行器在 `target_live` 之后另有逐名止损(T5b)、09-06 08:46Z 单日止损平仓、09-09 看门狗平仓与 09-10 场所规则锁 —— 这些改变实际持仓, 不改变目标文件, 本文不测。
- **实现账本层**的回放对实盘比较不在范围内。
- **V2MAIN 链**没有回放对照。

## §10 偏离与事后项
- 预注册的窗、组、读法、门全部照做, 无改动。预注册头部时间在任何数字之前从 ~08:40Z 改为 ~08:05Z 并重新冻结(两行记录在 `receipts/PREREG_FREEZE_sha.txt`)。
- `t5c_king_extend.py` 首跑因我写错一个时间常数在断言处停下(打分之前), 改为直接写时间戳后重跑; 首跑日志存 `receipts/failed_first_runs/`。
- §6.3 的逐日表与逐锚相关是看过结果后加的描述(`devices/t5c_posthoc_days.py`), 不参与读法。

## §11 复跑(逐字)
Mac(`T5c` 目录):
```
env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5c_live_ingredients.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
cd .. && /usr/bin/python3 T5c/devices/mk_t5c_device.py T5/devices/w10_sleeve_t5.py T5c/devices/w10_sleeve_t5c.py T5c/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md
```
上传规格、`devices/` 与 `receipts/T5c_live_ingredients.npz`(及其收据)到 pod2 `/workspace/uplift_r2_2026-09-13/T5c/`, 依次:
```
cd /workspace/uplift_r2_2026-09-13/T5c && bash devices/launch_pod2.sh t5c_king_extend.py
cd /workspace/uplift_r2_2026-09-13/T5c && bash devices/launch_pod2.sh t5c_drive.py
cd /workspace/uplift_r2_2026-09-13/T5c && bash devices/launch_pod2.sh t5c_bridge.py
```
`launch_pod2.sh` 内部: `nohup env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python devices/<device> PATH,HOME,LC_CTYPE`。收据拷回 `receipts/pod2/` 后, Mac:
```
/usr/bin/python3 devices/t5c_tables.py "$PWD"
env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5c_posthoc_days.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
```

## §12 产物
- 规格: `PREREG_T5c_september_replay_vs_deployed_2026-09-13.md`、`receipts/PREREG_FREEZE_sha.txt`
- 装置: `devices/t5c_live_ingredients.py`、`t5c_king_extend.py`、`mk_t5c_device.py`、`w10_sleeve_t5c.py`(+ `.diff`)、`t5c_drive.py`、`t5c_bridge.py`、`t5c_tables.py`、`t5c_posthoc_days.py`、`launch_pod2.sh`
- 收据: `receipts/RECEIPT_T5c_live_ingredients.json`、`receipts/T5c_live_ingredients.npz`、`receipts/pod2/RECEIPT_T5c_king_extend.json`、`receipts/pod2/RECEIPT_T5c_drive.json`、`receipts/pod2/RECEIPT_T5c_bridge.json`、`receipts/pod2/T5c_bridge_components.npz`、stdout 日志、`receipts/RECEIPT_T5c_posthoc_days.json`、`receipts/TABLES_T5c.md`、`receipts/failed_first_runs/`
- 只在 pod2(不入库): `arms/KA_s42.npz` 等四个臂(sha 在 drive 收据)、`kings/KA_x0910.npy`(sha `af379984…`)、`masks/umask_UPIT_CRYPTO_cf_x0910.npz`
- 校验和: `SHA256SUMS.txt`
