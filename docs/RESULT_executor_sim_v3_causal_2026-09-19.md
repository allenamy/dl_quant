> **创建:** 2026-09-19 | **Session:** session_01KW6frfphbFmFzx7wUtGhLb(流 E 执行器层子代理, 第五轮复审 R5-01/06/07/13 与复审 5b R5B-01/02/03 修复) | **状态:** 修订版(第二版) —— 模拟器 v3.1 在 V1b 门 v2 下: 历史诊断 HIST_DIAG PASS 12/12; 标定期样本内 CAL FAIL 11/12; 电池 77/77 exit 0; **真前瞻验证已预注册、尚无数据** | **作废条件:** 门 v2 批准表中任一文件改变(exec_sim 29679672 / v1b_gate 4a725921 / calib_v3 14357bba / 标定 fda34243 / simlib / v1_gate / fills_reader / 场所只读输入); 或 LIVE_G_DECOMPOSITION 现金恒等式收据被撤回; 或镜像输入与 INPUT_MANIFEST 不符

> ## ⚠ 修订说明(2026-09-19 10:xxZ, 复审 5b; 本文第一版 = 提交 684891031, 原文在 git 历史)
> 1. 第一版的 V1b 判词是在**修订前的门 31650235** 下算的。独立复审 5b 证明那一版门会对只有标签的收据判 11/11 PASS、对 NaN 窗末判 PASS、对允许的 0.5 s 偏移崩溃(R5B-01/02)。所以第一版的"留出期 PASS 11/11(裁定件)"**不是验证**; 原判词行原样保留在附录 A, 并在三份旧收据里加了 `judged_under: pre-revision gate 31650235` 标签。旧收据在门 v2 下重判为 **UNAVAILABLE**(没有逐种子路径产物、模拟器 v3 未获批)。
> 2. 第一版的 "HOLDOUT / 留出期" **改称"按时间截断重拟合后的历史诊断(HIST_DIAG)"**: 那一周在 v1/v2 的标定与诊断中已被看过, 不是独立验证。**真正的前瞻验证**另行预注册(§6), 冻结之后才有数据。
> 3. 第一版的"框架规则"(把锚 A 的模拟成交挪到 A 自己的锚后回读之前)**撤回**: 它改变了 384 个逐时状态中的 260 个, 不是纯展示(§3)。模拟器改为 v3.1。

# 执行器模拟器 v3.1: 因果时钟、无保证成交、封存起点、V1b 门 v2 的逐窗验收、历史诊断与预注册前瞻验证

**上游:** 第五轮复审 `.claude/worktrees/codex-review-r5-ff3bd08bd/docs/REVIEW_round5_stage1_codex_2026-09-19.md`(R5-01、R5-06、R5-07、R5-13); 复审 5b `.claude/worktrees/codex-review-r5b-221070b58/docs/REVIEW_round5b_codex_2026-09-19.md`(R5B-01、R5B-02、R5B-03)。被修对象: `docs/RESULT_executor_sim_calibration_2026-09-19.md`(v1/v2)。
**装置目录:** `multi_asset/exports/research/replay_exec_2026-09-19/`。
**盲态:** CFG-04 / CFG-06 在停止点前保持盲态。v3 / v3.1 的一切文件只含**跨臂合池**的结果参数; 标定代码读入订单与成交行即删去一切 arm / chase / requote / placement 键; 未打开 `CALIBRATION_FROZEN_2026-09-19.json` 的逐臂字段(v3.1 不读这个文件; 电池里对 v2 的反例只用合成参数)。执行器自己的分臂函数只报**分配计数**。本机未发起任何 fapi 调用(若将来需要, 走 `common/venue_quiet_window.py`, E-0919-V)。

## 0. 一页结论

1. **V1b 门 v2 验的是什么:** 每个 4 小时窗的价格与成交 / 资金费 / 手续费 / 换手的**条件均值**(32 条种子路径的均值)对照唯一一条实盘路径。它**不验证路径风险**(方差、停机/止损发生、尾部、maxDD)—— 这些只作诊断报告。32 条路径是最低计算量, 不是精度保证; 每窗项的蒙特卡洛标准误逐项报出。界是预声明的工程容差, 不是统计等价检验。
2. **历史诊断(HIST_DIAG, 09-11 00Z → 09-18 20Z; 标定只用 08-26 → 09-10 并已冻结; 从 09-10 20:44:27Z 执行器自己的回读重启)。不是独立验证。** 门 v2 判词逐字(退出码 0):
```
V1b[HIST_DIAG] E0 input validity    0 violations  PASS
V1b[HIST_DIAG] E1 population        sim 48 windows, live 48  contiguous True  declared True  in-period True  PASS
V1b[HIST_DIAG] E2 t0 alignment      max |Δt0| 0.000 s ≤ 1 s  PASS
V1b[HIST_DIAG] E3 t1 alignment      max |Δt1| 0.000 s ≤ 1 s  PASS
V1b[HIST_DIAG] W price_and_trading  s=mean|live| 711.78  |e| mean 81.19 (0.114·s ≤ 0.35)  p90 178.11  max 274.78  e/tol p90 0.601 ≤ 1  max 1.106 ≤ 3.0  (2 outside)  PASS
V1b[HIST_DIAG] W funding            s=mean|live| 14.79  |e| mean 0.84 (0.057·s ≤ 0.25)  p90 1.56  max 16.60  e/tol p90 0.302 ≤ 1  max 2.689 ≤ 3.0  (1 outside)  PASS
V1b[HIST_DIAG] W fee                s=mean|live| 6.92  |e| mean 0.84 (0.121·s ≤ 0.25)  p90 0.98  max 18.03  e/tol p90 0.585 ≤ 1  max 1.271 ≤ 3.0  (3 outside)  PASS
V1b[HIST_DIAG] W turnover           s=mean|live| 21,332.17  |e| mean 1,974.67 (0.093·s ≤ 0.25)  p90 2,737.66  max 31,943.60  e/tol p90 0.477 ≤ 1  max 1.629 ≤ 3.0  (2 outside)  PASS
V1b[HIST_DIAG] T fee                sim       308.3610  live       332.1617  ratio 0.9283  band [0.8, 1.25]  PASS
V1b[HIST_DIAG] T turnover_over_gross sim         0.0980  live         0.1007  ratio 0.9728  band [0.8, 1.25]  PASS
V1b[HIST_DIAG] T funding            sim      -732.7169  live      -710.0716  ratio 1.0319  band [0.8, 1.25]  PASS
V1b[HIST_DIAG] T price_and_trading  sim 1,825.14  live 1,530.28  total diff +294.87  tol 1,530.28  daily-diff mean +36.86 CI95 [-100.19, +160.42] (n_days 8)  PASS
V1b[HIST_DIAG] VERDICT: PASS (12/12 items)
```
3. **标定期(CAL, 08-26 04Z → 09-10 20Z, 样本内; 连续跑自 08-26 00:40:08Z 回读 328 名)不通过, 照实记录。** 判词逐字(退出码 1):
```
V1b[CAL] E0 input validity    0 violations  PASS
V1b[CAL] E1 population        sim 93 windows, live 93  contiguous True  declared True  in-period True  PASS
V1b[CAL] E2 t0 alignment      max |Δt0| 0.000 s ≤ 1 s  PASS
V1b[CAL] E3 t1 alignment      max |Δt1| 0.000 s ≤ 1 s  PASS
V1b[CAL] W price_and_trading  s=mean|live| 268.24  |e| mean 57.29 (0.214·s ≤ 0.35)  p90 151.02  max 437.87  e/tol p90 1.005 ≤ 1  max 2.273 ≤ 3.0  (11 outside)  FAIL
V1b[CAL] W funding            s=mean|live| 9.65  |e| mean 0.63 (0.065·s ≤ 0.25)  p90 1.15  max 12.77  e/tol p90 0.296 ≤ 1  max 2.793 ≤ 3.0  (3 outside)  PASS
V1b[CAL] W fee                s=mean|live| 4.77  |e| mean 0.92 (0.193·s ≤ 0.25)  p90 0.91  max 16.92  e/tol p90 0.755 ≤ 1  max 2.447 ≤ 3.0  (8 outside)  PASS
V1b[CAL] W turnover           s=mean|live| 15,307.19  |e| mean 2,586.28 (0.169·s ≤ 0.25)  p90 3,244.08  max 38,770.64  e/tol p90 0.526 ≤ 1  max 2.444 ≤ 3.0  (6 outside)  PASS
V1b[CAL] T fee                sim       442.3645  live       443.9990  ratio 0.9963  band [0.8, 1.25]  PASS
V1b[CAL] T turnover_over_gross sim         0.1577  live         0.1601  ratio 0.9853  band [0.8, 1.25]  PASS
V1b[CAL] T funding            sim      -787.2367  live      -757.4224  ratio 1.0394  band [0.8, 1.25]  PASS
V1b[CAL] T price_and_trading  sim -1,612.29  live -1,633.19  total diff +20.90  tol 1,633.19  daily-diff mean +1.31 CI95 [-81.66, +80.47] (n_days 16)  PASS
V1b[CAL] VERDICT: FAIL (11/12 items)
```
   唯一失败项: 逐窗价格与成交的 p90(|e|/tol) = 1.005 > 1 —— 93 窗里 11 窗越出各自等价界(允许 9 窗)。越界窗集中在 **09-03 入金重建段**(12:41、16:45、20:43)、**09-07 平仓后重建段**(00:39、04:45)与 **09-09 E-0909-G 平仓后到 09-10 重建**(09-09 20:39、09-10 00:45、04:44、08:43), 另有 09-08 12:45、16:44 两个普通窗。大规模重建时的执行节奏与成本是本模型最弱的一环。
4. **连续跑的历史诊断窗(诊断, 含 16 天状态漂移):** `V1b[HIST_DIAG_CONTINUOUS] VERDICT: PASS (12/12 items)`(价格 e/tol p90 0.675、最大 1.682; 全段价格差 +795.79, 重启跑 +294.87 —— 从真实起点重启比连续跑贴得更近, 漂移是真实误差来源)。
5. **两期差别的读法:** 按窗口 gross0 归一的价格误差, 历史诊断期均值 3.59 bps(p90 7.28、最大 11.43), 标定期 5.33 bps(p90 9.89、最大 26.78); 实盘价格幅度 / gross0 是 33.4 vs 27.3 bps。历史诊断那一周**没有入金式大规模重建**, 这是两期差别的主要来源, 不是模型在后一周变好。
6. **蒙特卡洛与路径分布(诊断, 非判词):** 每窗项的标准误 / 等价界, 最大值: HIST_DIAG 价格 0.187、资金费 0.116、手续费 0.122、换手 0.135; CAL 价格 0.599(09-03 这类高离散窗)、资金费 0.471。路径净额在 32 条路径间的标准差: HIST_DIAG 586.09 USDT(p05 −310.84 / p95 +1,657.16, 实盘 +488.04), CAL 620.41(p05 −3,800.21 / p95 −1,899.12, 实盘 −2,834.62)。同一目标书只因成交抽签, 一周净额就能相差上千 USDT —— 这正是"条件均值对上"不能推出"路径风险对上"的原因。
7. **电池 v3.1:** `BATTERY VERDICT: ALL PASS 77/77 checks (baselines green first, every mutation red; reviewer cases red on v2)`, `exit code: 0`, 解释器 `/usr/bin/python3`(Python 3.9.6)。复审 5b 的每个反例在归档门 31650235 上为红、在门 v2 上为绿; 第五轮的四个模拟器反例在归档 v2 上为红、在 v3.1 上为绿(§5)。
8. **尘仓暴露小:** 窗末路径均值, CAL 平均 3.87 名 / 8.97 USDT(最大 57.1 名 / 33.96 USDT; 2.12 bps of gross, 最大 12.69), HIST_DIAG 平均 1.62 名 / 4.20 USDT(最大 3.8 名 / 10.80 USDT; 0.20 bps, 最大 0.45)。
9. **真前瞻验证**已预注册(`docs/PREREG_executor_sim_forward_validation_2026-09-19.md`, 提交 c694705c5, sha256 `73cdd62c39366ed47e7c6812294a86feeb8765c334eed7fa0706f2e49bc94266`): 冻结提交 ca86f383a(09:50:24Z)之后, 起点锚 ≥ 09-19 16Z 的前 42 个完整实盘窗, 门 v2 sha 4a725921, 只读一次。**目前没有任何前瞻数据。**
10. **旧结论的处置:** v1/v2 的 V1 保持为**标定期对账**, 不改名为验证。v2 结果件 §7 的 (b) − (a)(v1 −4,456.37 / v2 −3,551.90 USDT)建立在 R5-01 的决策钟缺陷上, 作废; v3.1 未重跑规则模式, 该量目前没有有效数字。

## 1. 顺序与收据

| 提交 | 内容 | 当时有没有被判的数字 |
|---|---|---|
| `7c5d24772` | V1b 门 v1(sha 31650235)+ v2 装置存档 | 无 |
| `caccafe24` | 合池标定 calib_v3 → CALIBRATION_v3_POOLED(只用 08-26 00Z..09-10 20Z 锚) | 只有标定期参数 |
| `a24137373` | 模拟器 v3(fea90ee9)+ 电池 v3 46/46 | 无 |
| `a1b30c0f7`、`684891031` | v3 运行 + 门 31650235 判词 + 第一版本文 | 有 —— **在修订前的门下判的, 非验证**(附录 A) |
| `ca86f383a` | **冻结**: 模拟器 v3.1(29679672)+ 门 v2(4a725921)+ 电池 v3.1 77/77 + 归档门 31650235 / 模拟器 v3 / 电池 v3 | 无(新门下没有任何判词) |
| `c694705c5` | 前瞻验证预注册 | 无前瞻数据 |
| `795a04caf` | v3.1 两次运行(各 32 条路径产物)+ 门 v2 三份判词 + 旧收据门 v2 重判(UNAVAILABLE)+ 旧门收据加标签 + 时钟前后对比 | 全部 |

**向读者交代的污染:** (a) HIST_DIAG 那一周对研究员不盲(v1/v2 已公布其逐日差), 它只是参数估计意义上的时间截断; (b) 门的界在知道 v2 样本内相关 0.988 之后定; (c) 我在门 v2 冻结之前已经看过 v3(门 31650235)在这两期的读数 —— 门 v2 的**判定项与界没有改动**(只加了可验证性、有限性、零情形与诊断), v3.1 的**模型参数没有改动**(只撤回回读前挪动、加路径产物、改结果环节遍历顺序), 但"看过读数之后再修装置"的事实照实记下; (d) 标定草稿曾以面板链价为滑点参照, 在任何模拟数字之前改为执行器自记中价(§2)。

## 2. 按复审发现逐条: 缺陷的类与修法

| 发现 | 类 | 修法 | 证据(电池 v3.1) |
|---|---|---|---|
| **R5-01** 决策钟与成交钟混用 | 决策量读到决策时刻之后的信息; 库存早于真实成交存在 | 决策在执行器自记读目标时刻 t_dec, 只读 t_dec 时已入账的库存、模拟权益与 t_dec 当时或之前最后一根完整 5 分钟 bar(N+20:00)的价格; 数量由执行器 `plan` 在决策时定死; 每条腿按合池时刻作为事件入账; 资金费按结算时刻持有的库存收; 平仓先撤销未成交的再平衡腿 | A1/A2(合成, v2 红 v3.1 绿)、[4b][10][11] |
| **R5-06** 退出补完 = 保证成交 | 模型外凭空加成交; 期望值表示把"整笔未退出"变成细丝 | 删除补完; 逐请求哈希抽样, 每条路径是可行成交史; 低于地板的尾巴按执行器自身规则留作尘仓并逐窗报告 | A3/A4、[9] |
| **R5-13** "初始人口"写终点数 | 起点描述在运行后生成 | 起点做成规范 JSON 深拷贝 + sha, 运行前落盘、跑后复核; 门 v2 再从清单验证的镜像独立复算执行器 t0 回读与 NAV 核对 | [12]、D 伪造起点 |
| **R5-07** V1 只核 t0、只看全段/逐日和 | 逐窗抵消、端点只核一半、人口可裁 | V1b: 端点双核、完整人口、逐窗误差分布 + 逐窗等价界 + 尾部界 + 原 V1 四项 | A5、[8] |
| **R5B-01** 门把声明当证据 | 收据的身份、封存、种子只是标签 | 门 v2 批准表钉模拟器 / 标定器 / 标定 / 依赖; 收据每个声明对照实物复算; 旋钮缺一即 UNAVAILABLE; 封存起点实物重哈希并与执行器 t0 回读独立复算相等; 每个种子绑定一个路径产物, 均值、覆盖、计数全部由门从产物重算; 用钉住的标定器在原镜像上重跑标定, params / estimands / 人口 / 截止边界逐字节复现; 执行器导出树文件按清单与镜像字节双核(原 `verify_manifest` 不覆盖); 实盘侧每个判窗须 cash_ok | C1、D0、D 十种伪造 |
| **R5B-02** 有限性、时间合同、零情形 | NaN 顺着顺序 max 溜过; E 与 T 两套时间合同; 0/0 写成 Infinity | E0 先验全部数值有限与时间严格递增、窗长为正, 否则 INVALID_INPUT; E 与 T 统一时间合同(T 项由门自算, 与 v1_gate.judge 公式相同, 电池 C6 在真实窗上逐位复现); 零/零 PASS、零/非零 FAIL; 判词 PASS / FAIL / INVALID_INPUT / UNAVAILABLE 稳定命名(退出码 0/1/2/3) | C2(29 种变体 + 实盘侧 + 贯穿真实产物的一致 NaN)、C3、C4、C6 |
| **R5B-03** 历史段不是独立验证; MC 均值不验路径风险; 回读前挪动 | 以改名抹去接触史; 均值与风险混淆; 事件钟被倒挪 | HOLDOUT → HIST_DIAG(代码字符串、收据、本文); 前瞻验证预注册; 每窗报 MC 标准误与路径分布诊断, 明写不验路径风险; 撤回回读前挪动 | C5、[14][15]; §6 |

## 3. 事件时钟(明确声明)

- **v3.1 规则:** 每条成交都记在它自己的模拟时刻 t_dec + 合池偏移(首腿 +19/+45/+80/+182/+433 s, 后续腿 +58/+122/+1,107/+1,163/+1,198 s, 各 1/5 数量), 从不挪动。越过本锚回读(= 下一窗 t0)的成交属于**它实际发生的那个窗**。逐名止损与 §4-2 判定是锚 A 回读时刻的一个事件(执行器就在回读上判), 无回读时在 N+45。
- **窗口快照只是展示:** 电池 [14] 在 384 个整点比较现金、逐名仓位、累计资金费与止损状态(stopped / cooldown / counters), 开着与关掉窗口快照时**逐项相同**; 让快照改动现金的变异使 384 个整点全部不同。
- **撤回的 v3 规则**(锚 A 的成交挪到 A 回读前 1 s)**不是纯展示:** 电池 [15] 实测它使 384 个整点状态中的 260 个改变(第一个在 08-26 09:00Z; 回读时刻的止损判定看到的库存不同, 路径随之分叉), 挪动名义 26,045 / 993,094 USDT。故撤回, 只留作变异旋钮 `--legacy-readback-clamp`(电池 [11] 变异为红)。
- **前后对比**(`DIAG_clock_effect_v3_vs_v31_2026-09-19.json`, 同一纯判官函数, 非判词; v3 一侧在门 v2 下无法验证): v3.1 中落入下一窗的成交名义占 1.57%(连续跑)/ 0.32%(重启跑)。

| 期间 | 项 | v3(挪动) | v3.1(不挪) |
|---|---|---|---|
| CAL | 价格 e/tol p90 / 最大 / 越界窗 | 1.049 / 2.330 / 11 | 1.005 / 2.273 / 11 |
| CAL | 换手 e/tol p90 / 最大 | 0.624 / 2.758 | 0.526 / 2.444 |
| CAL | 手续费 e/tol p90 | 0.767 | 0.755 |
| HIST_DIAG | 四个 W 项 | 0.601 / 0.302 / 0.585 / 0.477 | 同(三位小数内) |
| HIST_DIAG_CONTINUOUS | 四个 W 项 p90 | 0.675 / 0.370 / 0.548 / 0.467 | 0.675 / 0.369 / 0.552 / 0.468 |

## 4. 合池标定与模拟器(未改动部分, 摘要)

- **标定**(`calib_v3.py` 14357bba → `CALIBRATION_v3_POOLED_20260826_20260910.json` fda34243, 12,972 个计划): 首腿被拒 0.2906; 挂上后 满 / 零 / 部分 0.7944 / 0.1601 / 0.0455(部分均值 0.542); 后续腿完成率 π 0.6036、maker 份额 μ 0.4646(拒单与挂上剩余、全部臂合池); 滑点对执行器自记中价: 首腿 −2.66 bps、后续腿 −0.87 bps、平仓 +4.29 bps; 费率同 calib.py 规则(切换 09-07 04:24:09Z)。草稿曾以面板链价为参照, 因 rolling.npz 自身 15 根 ±0.30 裁剪 bar 与链价水平误差, 在任何模拟数字之前改为执行器中价参照。门 v2 每次判定都用钉住的标定器在原镜像上重跑并逐字节复现 params / estimands。
- **模拟器 v3.1**(exec_sim.py 29679672): 除 §3 的事件时钟外, 与 v3 相同的因果决策、逐请求抽样、封存起点; 新增: 每个种子写路径产物(`<收据名>_PATHS/seed_NN.json`, 含窗口、止损、平仓、停机锚、起点 sha、模拟器与标定 sha), 收据登记每个产物 sha 与全部依赖 sha; 前瞻输入(镜像 / 清单 / 实盘窗文件 / 划转文件)走命令行而代码不改; `WideMirror` 让日期范围覆盖镜像全部日子(simlib 默认止于 09-19, 会静默丢掉前瞻期的行)并只读一次成交账本(历史镜像上行人口不变); 结果环节按名排序 —— 执行器 reshape 会遍历集合、同一时刻的成交按排程顺序处理, 未排序时不同进程的浮点和相差 ~1e-14; 排序后不同 PYTHONHASHSEED 下路径产物逐字节相同(电池 [6b])。

## 5. 电池 v3.1(`tests_exec_sim.py` 9458558e; 收据 `BATTERY_tests_exec_sim_v31_2026-09-19.txt`)

判词行逐字: `BATTERY VERDICT: ALL PASS 77/77 checks (baselines green first, every mutation red; reviewer cases red on v2)`; `exit code: 0`; `/usr/bin/python3`(Python 3.9.6)。真实数据项只跑标定期; 夹具是标定期切片(08-26 → 08-28 20Z, 32 条路径, 在本进程装只读守卫之前由子进程生成)。

| 部分 | 内容 | 结果 |
|---|---|---|
| A(第五轮反例, 合成小书) | 未来价 100→200 不动决策; A+24:05 结算按执行前库存; 80% 模型 20 USD 退出期望 16; 零成交概率 4 USD 尘仓不成交; 反相关路径 | 归档 v2 全红(权益 200→300、收 −2/−1.5、执行 20、成交 4; 旧 V1 四项全过), v3.1 全绿(2,000 种子均值 16.15, MC 标准误 0.18) |
| B(真实数据, 各先绿后变异红) | [1] 最小名义 · [2] 逐名止损 · [3] 费用 · [4] 资金费 · [4b] 成交时刻库存(含注入的决策后 +5 s / +600 s 合成结算) · [5] 会计恒等 · [6] 确定性与标定绑定 · [6b] 跨进程逐字节确定 · [7] 只读守卫 · [8] V1b 在真实窗上 · [9] 无保证成交 · [10] 未来价扰动不变 · [11] 成交钟(含 `--legacy-readback-clamp` 变异) · [12] 起点人口 328 = 封存 328(v2 收据 241) · [13] 盲态键 · [14] 窗口快照纯展示 · [15] 撤回的挪动规则改变逐时状态 | 全过 |
| C(复审 5b 反例, 归档门 31650235 红 / 门 v2 绿) | C1 纯标签收据 · C2 第 6 窗 t1 = NaN 及 29 种首/中/尾 NaN/±Inf、重复轴、零长窗、实盘侧 NaN · C3 0.5 s 偏移 · C4 零/零 · C5 同均值不同路径风险 · C6 T 项与 v1_gate.judge 逐位一致 | 旧门: PASS / PASS / AssertionError / Infinity FAIL / 只读种子标签; 门 v2: UNAVAILABLE / INVALID_INPUT / 具名判词(E2 过)/ PASS 与 0/x FAIL / 诊断报出差异(路径净额标准差 0 vs 9,753.6, maxDD 0 vs −0.389)|
| D(真实夹具上的来源核验) | 基线 0 违例; 伪造: 执行器文件声明、路径产物篡改、篡改后重签收据、缺种子、一致伪造起点、模拟器 sha、缺旋钮、换标定、改钉住标定(重跑不复现)、实盘窗 cash_ok 为假; 已入库 v3 收据; 贯穿产物的一致 NaN | 每种伪造 UNAVAILABLE(各自具名); v3 收据 UNAVAILABLE(46 条); 一致 NaN ⇒ INVALID_INPUT |

## 6. 前瞻验证(预注册, 无数据)

`docs/PREREG_executor_sim_forward_validation_2026-09-19.md`(c694705c5, sha256 73cdd62c…): 冻结提交 ca86f383a(2026-09-19 09:50:24Z); 重启状态 = 执行器 09-19 12Z 窗 t0 回读(晚于冻结); 判窗 = 起点锚 ≥ 09-19 16Z 的前 42 个完整实盘窗(不剔除停机、平仓、入金); 每窗 cash_ok; R = 32 种子 0..31; 门 v2(4a725921)判词逐字; 只读一次, 在第 42 窗存在并备好前瞻快照(新清单文件名; 现 `snapshot_inputs.py` 写死日期且会覆盖钉住的清单, 不能原样用)、前瞻 LIVE_G、刷新的划转与原镜像之后。

## 7. 价格层的已知噪声底(未修; 收据 `DIAG_price_chain_v3_2026-09-19.json`)

生产者面板 `rolling.npz` 的 ret5 本身被硬裁在 ±0.30(15 根 bar; V1 区间内 AKE 09-02、BULLA 09-05、WOO 09-06、LSK 09-13、AIN 09-16 ×3)。链价对执行器自记中价偏离中位 0.15%、p99 6.15%、最大 60%。实盘持仓上链价与中价的 4h 价格损益差: 标定期均值 27.2 USDT(最大 377.0, 09-05 00Z BULLA 那一窗), 历史诊断期均值 49.9(最大 215.7)。这是 V1b 价格项的数据层噪声底, 不是执行模型的问题; 恢复原始 bar 需要镜像里没有的未裁剪数据。

## 8. 局限

1. HIST_DIAG 不是独立验证(§1(a))。一周、48 窗、一条实盘路径、1 次平仓与 1 段停机重建; 没有入金式大规模重建 —— 那正是样本内越界最集中的地方。
2. V1b 只验条件均值; 路径风险只作诊断。
3. 合池参数混合了不同政策期(重挂实验 09-05 12Z 起、追单 50/50 09-01 16Z 起都在标定期内部); 单一 π、μ 表达不了大单重建与 09-10 后 −4400 场所锁带来的逐锚完成率变化。
4. 成交与随后价格路径独立(未建模被动单的逆向选择)。
5. 价格层噪声底(§7)。
6. 运行起点在 N+40 回读, 在途补单不模拟, 起点窗为热身窗。
7. 平仓滑点只来自标定期 3 次平仓的定价行(845 行)。
8. 未建模: 场所上限钳、挂单赌博机、限速 / 传输故障、BNB 余额重估(实盘 NAV 为 USD 多资产)。
9. 规则模式 (b) 与 (b) − (a) 未重跑; 旧数作废。
10. 前瞻读数依赖尚未编写的前瞻快照变体与前瞻 LIVE_G; 原镜像若丢失则前瞻读数为 UNAVAILABLE。

## 9. 复跑(逐字; 工作目录 = `multi_asset/exports/research/replay_exec_2026-09-19`; 镜像默认 = 本会话 scratchpad 下 `replay_exec_mirror/`, 启动先按 INPUT_MANIFEST 复核)
```
/usr/bin/python3 tests_exec_sim.py
/usr/bin/python3 v1b_gate.py --selftest
/usr/bin/python3 exec_sim.py --events live --period CAL --out SIM_v31_live_CAL_continuous_20260826_20260918.json
/usr/bin/python3 exec_sim.py --events live --period HIST_DIAG --out SIM_v31_live_HIST_DIAG_20260911_20260918.json
/usr/bin/python3 v1b_gate.py SIM_v31_live_HIST_DIAG_20260911_20260918.json HIST_DIAG V1B2_GATE_v31_HIST_DIAG_20260911_20260918.json
/usr/bin/python3 v1b_gate.py SIM_v31_live_CAL_continuous_20260826_20260918.json CAL V1B2_GATE_v31_CAL_20260826_20260910.json
/usr/bin/python3 v1b_gate.py SIM_v31_live_CAL_continuous_20260826_20260918.json HIST_DIAG_CONTINUOUS V1B2_GATE_v31_HIST_DIAG_CONTINUOUS_20260911_20260918.json
/usr/bin/python3 v1b_gate.py SIM_v3_live_HOLDOUT_20260911_20260918.json HIST_DIAG V1B2_REJUDGE_v3fea90ee9_HIST_DIAG.json
/usr/bin/python3 diag_clock_effect_v31.py DIAG_clock_effect_v3_vs_v31_2026-09-19.json
```
路径产物在不同进程、不同 PYTHONHASHSEED 下逐字节相同; 收据含 `utc` 时间戳, 其余字段复现。

## 10. 需用户裁定

无。本件是研究装置, 不改实盘任何字节, 不构成任何实盘建议。

## 附录 A: 修订前的门 31650235 下的 v3 读数(judged under pre-revision gate 31650235; 非验证; 原样保留)

以下为第一版本文 §0 的判词行, 模拟器 v3(fea90ee9, 含已撤回的回读前挪动), 门 31650235(可被纯标签收据与 NaN 窗末骗过)。其中 "HOLDOUT" 即现在的 HIST_DIAG(历史诊断, 非独立验证)。这些收据在门 v2 下重判为 UNAVAILABLE(`V1B2_REJUDGE_v3fea90ee9_*.json`: 45 / 46 / 45 条违例)。
```
V1b[HOLDOUT] E1 population        sim 48 windows, live 48  contiguous True  declared True  in-period True  PASS
V1b[HOLDOUT] E2 t0 alignment      max |Δt0| 0.000 s ≤ 1 s  PASS
V1b[HOLDOUT] E3 t1 alignment      max |Δt1| 0.000 s ≤ 1 s  PASS
V1b[HOLDOUT] W price_and_trading  s=mean|live| 711.78  |e| mean 81.26 (0.114·s ≤ 0.35)  p90 178.11  max 274.78  e/tol p90 0.601 ≤ 1  max 1.106 ≤ 3.0  (2 outside)  PASS
V1b[HOLDOUT] W funding            s=mean|live| 14.79  |e| mean 0.84 (0.057·s ≤ 0.25)  p90 1.56  max 16.60  e/tol p90 0.302 ≤ 1  max 2.689 ≤ 3.0  (1 outside)  PASS
V1b[HOLDOUT] W fee                s=mean|live| 6.92  |e| mean 0.83 (0.121·s ≤ 0.25)  p90 0.98  max 18.03  e/tol p90 0.585 ≤ 1  max 1.271 ≤ 3.0  (3 outside)  PASS
V1b[HOLDOUT] W turnover           s=mean|live| 21,332.17  |e| mean 1,967.67 (0.092·s ≤ 0.25)  p90 2,737.66  max 31,943.60  e/tol p90 0.477 ≤ 1  max 1.629 ≤ 3.0  (2 outside)  PASS
V1b[HOLDOUT] T fee                sim       308.3610  live       332.1617  ratio 0.9283  band [0.8, 1.25]  PASS
V1b[HOLDOUT] T turnover_over_gross sim         0.0980  live         0.1007  ratio 0.9728  band [0.8, 1.25]  PASS
V1b[HOLDOUT] T funding            sim      -732.7169  live      -710.0716  ratio 1.0319  band [0.8, 1.25]  PASS
V1b[HOLDOUT] T price_and_trading  sim 1,825.14  live 1,530.28  total diff +294.87  tol 1,530.28  daily-diff mean +36.86 CI95 [-100.19, +160.41] (n_days 8)  PASS
V1b[HOLDOUT] VERDICT: PASS (11/11 items)
V1b[CAL] W price_and_trading  s=mean|live| 268.24  |e| mean 58.39 (0.218·s ≤ 0.35)  p90 164.31  max 444.19  e/tol p90 1.049 ≤ 1  max 2.330 ≤ 3.0  (11 outside)  FAIL
V1b[CAL] VERDICT: FAIL (10/11 items)
V1b[HOLDOUT_CONTINUOUS_DIAG] VERDICT: PASS (11/11 items)
```
