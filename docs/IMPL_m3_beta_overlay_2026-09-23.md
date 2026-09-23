> **创建:** 2026-09-23 | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(M3 生产实现执行代理, lead 派出) | **状态:** 改动包就绪(含第十轮复审修复 `b81c4cb`+`5b3d89c`, §8), **未部署**, 未推送; 开关默认 `off`; 对冲预算键未设(待用户裁定) | **作废条件:** 预注册 `docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md`(24c3f803f)改动; 执行器运行树离开 `b66257b` 且与本包冲突; 生产者 `~/wide_shadow/fea171/combo_stage.py` 离开 `fb5a9407…`; 或下文任一 sha 改变

# IMPL: M3 BTC-beta 叠加腿(按**执行后**持仓算 β)的生产实现

预注册 §5 的生产线。**本文不含任何收益数字**(评估由另一代理按预注册 R1–R4 做)。改动在隔离副本里完成并测试:
执行器 `~/cc_tmp/m3_impl_20260923/exec`(分支 `m3-beta-overlay` = `8725e7d` → `11aa8d1` → `c71ca7a` → `4dd7d53` → `80ae104`(相对 `4dd7d53` 只改两处注释,编译码逐字节相同,§4.5)→ `b81c4cb`(第十轮复审修复,§8)→ **`5b3d89c`(终版;相对 `b81c4cb` 只改套件夹具)**,基 `b66257b`,**未推送**;前两个提交是 `b7a44eb` / `98423ab` 只改提交说明(补署名行)的重写,树逐位相同;`c71ca7a` 是 AMENDMENT_1 的第一种读法,被 `4dd7d53` 取代以与评估的 M3b 钩子逐条一致),生产者 `~/cc_tmp/m3_impl_20260923/producer_copy`。
交付物: `multi_asset/exports/research/m3_impl_2026-09-23/`(两份 diff、执行器补丁、清单、收据、复跑命令)。

## §0 一页结论(白话)

1. **生产者**在写 target_live 时多写一个字段 `beta_overlay`(版本 `m3_beta_v1`):宇宙 450 名(当前宇宙含 BTC;不含时也强制写 BTC=1)的 β、每名有效观测数、数据截止时刻(= 本锚)、声明的公式参数。其余字段、权重**一个字节都不变** —— 在生产者沙箱里对 08Z 锚重放,改后的 combo_stage 写出的文件与实盘归档文件**除新字段外逐键相等**, 权重 max|Δw| = 0, weights npz sha 相同(收据 §4.4)。计算 0.15 s,失败不阻断发布(只是不写字段)。
2. **执行器**在 POP→RESHAPE→CLAMP **之后**算 β_exec = Σ w_exec,i·β_i, 给 BTCUSDT 加一条独立叠加腿 −β_exec(USDT), 不经 reshape, 之后仍过场所上限截断。三档开关 `config/book.json beta_overlay.mode`:**off(默认)/ shadow(只算只记)/ on(下单)**。
3. **off 与现行执行器逐位相同**:两层证明 —— ① 把三个改动文件里的全部 M3 插入剥掉,得到的源码与 `b66257b` 的 blob **逐字节相同**(收据 §4.3);② 新套件 [Z] 把新代码(开关缺省 / off / shadow)与剥离后的执行器放在同一输入上跑,计划、干跑下单、订单行、锚上下文、loop state、phase-A 记录**全部相同**(4 种输入 × 3 档 = 12 格),并有两个泄漏变异体被同一比较抓住;off 的 anchors 行经真实 PilotLogger 写盘读回也与剥离执行器逐字节相同。
4. **平书诊断(R3 在执行器同码上)**:开关 on,非 BTC 名的执行目标与 off 书**逐位相同**;BTC = 书的 BTC 执行量(碎单被 pop 时为 0)+ (−β_exec);最终目标的事前 β 移动 / 意图 = **1.0(容差 1e-9,测试里独立重算)**;计划层(0.001 BTC 手数向零截断后)0.994,容差一手。构造的锚文件净额 −6%,reshape 后书净额 0,加腿后净额**恰为对冲量** —— 腿没有被摊平;同一对冲写进文件(M2 路线 L)在同一执行器上 β 移动 / 意图 = −0.09(被摊平,红控制)。
5. **缺失即不做**:字段缺失 / 版本错 / 截止时刻不是本锚 / 某个执行目标非零的名没有 β ⇒ 不下 BTC 单、HIGH 页报、已持 BTC 冻结在现值(不当 0 对冲平掉,也不按 β=1 重算)。两个变异体(缺失当「全体 β=1」、缺失当「对冲 0」)在同一输入上**都会下 BTC 单** —— 检查是承重的。
6. **BTC 碎单判定按合计值(AMENDMENT_1 `912788743`,协调者的设计约束;与评估的 M3b 钩子 `c414ca4cf` 逐条一致)**:书这一层照 off 原样跑(非 BTC 名逐位同 off);BTC **仅因**书内分量低于 2×minNotional 而不可交易时,改用合计值 C = BTC 执行量 + 腿 重判:C 不是碎单 ⇒ 下 C 并把 BTC 放出只减名单;C 仍是碎单 ⇒ 不动(记缺口)。套件 N1:书内 BTC 4 USDT(< 2×5)、腿 1,962 USDT ⇒ BTC 单照下;N2 红变异(改回 M2 路线 H「书内碎单拦腿」)⇒ 同一输入不下 BTC 单。评估代理在认证模拟器上 R3 不过的缺口正来自那条旧规则(`14891549c`)。**逐名止损 / 冷却 / 场所撤名 / 场所上限**:腿不下(或被截)时一律 HIGH(持续暂停降为去重的固定文本)并把意图记为「对冲缺口」`hedge_gap_usdt`,见 §3。
7. **上线前必须由人决定的事**见 §7,最要紧的:① 与 M3b 钩子逐条一致带来的两处取舍(持有退出算名字级原因 ⇒ 生产者某锚不目标 BTC 时对冲会被平掉;add_blocked 的 BTC 以持仓作底座值),见 §7-1;② 逐名止损条款目前也作用在对冲腿上(BTC 浮亏 ≤ −30% 连续 2 锚 ⇒ 对冲被 maker 平掉并冷却 7 天无对冲,期间每锚记缺口);③ 追单实验 C 的中性基准改为扣除对冲意图净额(否则 C 会把对冲当倾斜追回去)—— 认证仿真在这里没扣,评估读数与生产在这一点上不一致。
8. **第十轮复审修复(§8)**:① 对冲腿下单前受账户总 gross 预算约束(`max_combined_leverage`,**不给缺省值**,未设则 on 也不下腿),看门狗 cond4b 改判 max(sizing, 合计目标, 读回) gross;② 冻结 BTC 时中性读数只扣冻结造成的增量;③ 配置损坏冻结在持的腿、显式 off/shadow 才撤腿;④ 生产 β 与评估 β 逐名平价:差异只来自缓存 ±0.30 裁剪的 7 个名字,max |Δβ| 0.066,β_exec 相对差 ≤ 0.9%,BTC 手数差 < 0.15 手(G=10k)。

## §1 设计(逐条对应任务书与预注册 §2 / §5)

### 1.1 公式(零自由参数, 与 M2 `m2_lib.betas_at` 同一定义)
- β_i:截至锚 A 已完成的最近 180 根 4h bar(以 A 为终点的那根也算),名 i 的 4h 对数收益对 BTCUSDT 4h 对数收益的 OLS 斜率(带截距),成对有效 ≥120 否则 1.0,截断 [−1, 4],BTC 自身 1。
- β_exec = Σ_i w_exec,i·β_i(USDT;书自己的 BTC 分量按 β=1 计入)。对冲 = −β_exec(USDT)。预注册写「−β_exec × 书 gross 名义」,β_exec 取 gross 单位;归一分母两边相消,所以腿的名义与用哪个 gross 归一无关。
- BTC 目标 = 书的 BTC 执行量(被 pop 则 0)+ 对冲;之后照常过 `clamp_venue_cap`。w_exec 按预注册取 CLAMP 之后、场所上限之前;场所上限若截了别的名,残余 β 记在 `beta_final_usdt`(只记,不回灌)。

### 1.2 生产者字段(`fea171/beta_overlay_producer.py`)
数据 = 生产者本锚打分用的同一代 `state/rolling.npz`(`rts` 为 5 分钟 bar **收盘**时刻,`ret5 = close/prev_close − 1`)。4h 对数收益 = (T−4h, T] 内 48 行 `log1p(ret5)` 之和;**一根 bar 有效当且仅当闭区间 [T−4h, T] 内 49 行全有限**(起点那行缺 ⇒ 下一行的 ret5 跨了缺口,起点价陈旧 —— 与 M2 / 认证引擎 UA-FREEZE-EXCLUDE 同一闭区间规则)。缺测不补零。
**与 M2 认证价表的具名差异**(须由人认可, §7-4):ret5 在缓存里被截到 ±0.30/5 分钟、以 float16 存(单行相对舍入 ~5e-4);缓存只有 40 天(180 bar 需 30 天,足够)。只读锚时刻及以前的行(因果切片)。
字段内容:`version, anchor_ts, data_cutoff_ts(= anchor_ts), first_bar_end_ts, n_win 180, n_min 120, clip [-1,4], fallback 1.0, btc, betas{450}, n_obs{450}, n_names, n_estimated, n_fallback, n_no_cache_column, method, source, prereg`。约 23 KB。

### 1.3 执行器三档与 BTC 归属(`live/beta_overlay.py` + `scheduler/anchor_loop.py` 的 M3 块)
- **off**(缺键 / 缺块 / `"off"`):除读一次开关外什么都不做。
- **shadow**:校验字段、在 off 的书上算 β_exec 与假想对冲并写进 anchors 行 `m3_beta_overlay`;书、订单、loop state 与 off 相同([Z] 证明)。
- **on**:下腿。判定顺序与评估的 M3b 钩子(研究仓 `c414ca4cf`,`multi_asset/exports/research/m3b_2026-09-23/devices/m3_hook.py` 的 `apply_overlay`)逐条一致,M3b 的读数因此就是生产行为的读数:
  1. **书这一层照 off 原样跑**(POP→RESHAPE→CLAMP,真实持仓):每个非 BTC 名逐位等于 off 书。BTC 的书内分量是碎单时:未持有 ⇒ pop,持有 ⇒ clamp —— 与今天相同。在这之前按不可交易来源给 BTC 分类:`hard_block`(名字级原因)与 `dust_only`(唯一原因是 `external_dust`)。
  2. **β_exec** 在这本执行书上算(BTC 的执行量按 β=1 计入);腿 = −β_exec;腿恰为 0 ⇒ 什么都不动。
  3. **名字级原因 ⇒ 暂停**:逐名止损(force_flat)、止损冷却、场所状态/零上限、场所元数据、**持有退出**(持有 BTC 但生产者文件不目标它;近 167 个 combo 文件 0 次)、或 untradable 里没有任何来源记录(fail-closed)。本锚不下腿,BTC 按书的场所规则走真实持仓(只减);首锚 HIGH(带缺口金额),持续中改 INFO 固定文本(`alarm_policy` 对相同正文 24 h 去重,逐名止损的告警疲劳规则 #60);每锚把整笔意图记为 `hedge_gap_usdt`。
  4. **仅碎单 ⇒ 合计值重判**:C = BTC 执行后的底座值(pop 时 0、clamp 后的值)+ 腿;`|C| ≥ min_notional_mult × minNotional`(实盘 2×50 = 100 USDT)⇒ BTC 目标 = C,BTC 从 clamp 的 reduced / add_blocked / flatten_only / popped 名单放出(不再只减),状态 `applied_via_combined`;否则什么都不动(书的决定保留),状态 `combined_dust`,缺口 = 腿,INFO。
  5. **BTC 可交易 ⇒ 目标 = 执行量 + 腿**(`applied`);合计值低于线只记录不动作(与 M3b 相同)。
  6. BTC 恒进定价名单(权重 0 且未持有 ⇒ 被书这一层当碎单 pop,与缺席名无异,然后经第 4 条拿到腿)。腿本身没有另外的尺寸门;唯一的其它尺寸检查是 plan() 对 BTC 订单增量的场所 minNotional(向零截断一手)。
- 为什么是这个语义:实盘 combo 书的 BTC 权重约 0.2% gross,2× NAV 下 BTC 书内分量几乎每锚都低于 2×minNotional;沿用 M2 路线 H「书内碎单拦腿」,实盘上对冲几乎永远不会下(评估在认证模拟器上已测到 R3 缺口正来自这条)。与 M3b 逐条一致的两个代价如实写下(§7-1):持有退出算名字级原因;add_blocked 的 BTC 以持仓作底座值(只在书的 BTC 权重大于近零的对冲时可能)。
- `c71ca7a` 曾用另一种读法(腿可下时把 BTC 书内分量从碎单名单撤下、随书 reshape,再对合计判碎单),会让其它名在 reshape 上与 off 书差一个极小量;为与评估逐位一致,`4dd7d53` 取代了它。

### 1.4 缺失即不做(预注册 §5)
`validate_field` 逐条拒:`field_missing / field_malformed / version_mismatch / anchor_mismatch / cutoff_mismatch / params_mismatch / bad_betas(非有限、越界、n_obs 越界、n_obs<120 却不是 1.0)/ btc_beta_not_one`;`beta_exec` 对**执行目标非零**而无 β 的名拒(`beta_missing_for_targeted`,零目标名乘任何 β 都是 0,不要求)。on 下任一拒绝 ⇒ BTC 目标 = 现持名义(delta 0,不下单),HIGH「缺失即不做」,记 `btc_frozen_at_usdt`;BTC 未持有 ⇒ 只交易书的 BTC 分量(无腿)。

### 1.5 记账
- anchors 行 `m3_beta_overlay`:mode / status(`applied|applied_via_combined|combined_dust|zero_hedge|suspended_btc_untradable|refused|shadow`)/ reason / 字段校验结果 / `data_cutoff_ts` / `betas_sha256` / `n_betas` / `n_fallback` / `beta_exec_usdt` / `beta_exec_gross_units` / `beta_exec_over_book_gross` / `hedge_target_usdt` / `btc_book_target_usdt` / `btc_combined_target_usdt` / `btc_held_usdt` / `overlay_net_usdt` / `diag_target`(β 移动/意图)/ `diag_plan`(计划层)/ `beta_final_usdt` / `venue_capped` / `hedge_gap_usdt` / `hedge_gap_reason` / `btc_dust_only` / `released_from` / `combined_below_threshold` / `prev`。
- orders 行:BTCUSDT 在下腿锚的**每一条**订单行带 `m3_overlay_leg`(`hedge_target_usdt / book_target_usdt / combined_target_usdt / held_usdt / beta_exec_usdt / betas_sha256`),由 `_order_row` 从执行器级记录读取(与追单实验臂同一做法,不写到共享的 plan dict 上)。
- fills 行**不改**(fills 写入合同对事实列有 supersede 校验);按 `(rebalance_id, symbol, order_type, attempt_idx)` 连到带标的订单行即可单算对冲腿的手续费与滑点。资金费按 anchors 行的 `hedge_target_usdt / btc_combined_target_usdt` 比例拆(书内 BTC 分量通常只有几十 USDT,对冲数千 USDT ⇒ 绝大部分归对冲)。
- **对冲缺口**:每个状态都记 `hedge_gap_usdt` 与 `hedge_gap_reason` —— applied 为 0;硬原因暂停 = 整笔意图;字段拒收 = None(意图不可算,缺口未知而不是 0);合计仍碎单 = 整条腿;场所上限截断 = 意图 − 截后实际。
- loop state `m3_overlay_last`(仅 on 写):上一锚的状态与对冲量,供下一锚记 `prev` 与判「持续暂停」。
- 两个中性读者按**扣除对冲意图净额**判:追单实验 C 的 `book_net_usdt`(差恰为对冲量,无腿时与剥离执行器逐字节相同)、收锚中性页报与中性价格(行上保留原始 `net_over_gross`,另记 `net_ex_overlay_*`)。对冲送达 ⇒ 不页报;对冲没送达 ⇒ 页报(那才是偏离意图)。

## §2 改动清单(文件:行,均相对 `b66257b`)

### 2.1 执行器(补丁 `executor_m3_b66257b.patch` = `git diff b66257b 5b3d89c`,sha256 `def807861e152014…`,19 个文件,+2802/−4;分支 `m3-beta-overlay` 七个提交,终版 `5b3d89c`(树 `1082ef7b…`),未推送。⚠ 下表行号是 `4dd7d53`/`80ae104` 的;第十轮修复后的行号见 §8.1)
| 文件 | 行 | 内容 |
|---|---|---|
| `live/beta_overlay.py`(新) | 1–465 | 开关解析、字段校验、β_exec、`hard_block` / `dust_only`(M3b 分类)、`stage`(合计值重判、对冲缺口)/ `after_cap` / `after_plan` / `neutrality_view`、`strip_m3` |
| `scheduler/anchor_loop.py` | 56 | `import beta_overlay as BO`(M3-LINE) |
| 〃 | 1679–1695 | `_trade` 开头:每锚解析开关、重置执行器级记录;非外部书 ⇒ off + HIGH |
| 〃 | 1713–1718 | on:BTC 恒进定价/场所门名单 |
| 〃 | 2066–2070 | 书这一层之前给 BTC 分类(`hard_block` / `dust_only`);`apply_withhold_and_reshape` 调用**原样未改** |
| 〃 | 2094–2119 | 叠加腿(POP→RESHAPE→CLAMP 之后)、合计值下腿时把 BTC 放出 clamp 名单、告警、执行器级记录、loop state |
| 〃 | 2208–2212 | 场所上限之后:BTC 被截 ⇒ HIGH + 缺口;残余 β |
| 〃 | 2220–2224 | 计划层送达诊断(容差一手 / minNotional) |
| 〃 | 2386–2389 | anchors 上下文带 `m3_beta_overlay` |
| 〃 | 3048–3051 / 3056–3059 / 3103 / 3127 | anchors 行写记录;中性读者视图;两个 M3-ORIG 调用 |
| `live/binance_executor.py` | 1628–1642 | 追单实验 C 的净额基准扣对冲意图(M3-LINE ×3 + M3-ORIG ×2) |
| 〃 | 2289, 2362–2363 | `_order_row`:BTC 行带 `m3_overlay_leg`(M3-LINE) |
| `live/external_book.py` | 413–414 | `parse_target` 原样透传 `beta_overlay`(仅字段存在时;M3-LINE) |
| `config/book.json` | 末尾 | `"beta_overlay": {"mode": "off", _basis, _semantics}` |
| `live/tests_beta_overlay.py`(新) | 1–895 | 125 项检查,见 §4.1 |
| `run_acceptance.sh` | SUITES 末 | 登记 `tests_beta_overlay` |
| `ops/gate_coverage.py` | SUITE_SCOPE | `tests_beta_overlay` 的「不证明什么」与五个盲区 |
| `live/tests_imports.py` | PRODUCTION_MODULES | `beta_overlay` |
| `live/tests_external_book.py` / `tests_gross_ladder_retired.py` / `tests_per_name_stop.py` / `tests_signal_and_loop.py` | 各 1 行 | 由真实配置派生的夹具把 `beta_overlay` 钉为 off(与它们对 `book_source` 的既有纪律相同)。**今天不承重**:去掉钉、盘上 mode=on,`tests_external_book` 照样全绿(收据 `targeted/nopin_disk_on_tests_external_book.log`);保留是为了以后这些套件不会随盘上开关变红 |
| `live/tests_rehearsal_anchor.py` | `_EXEMPT` | 登记 `live/beta_overlay.py`(rebalance_id 普查;只在文档串出现,理由写明) |
| `ops/producer_release/20260923_m3/`(新) | — | 生产者发布件:`combo_stage.py`、`beta_overlay_producer.py`、`tests_beta_overlay_producer.py`、`SOURCE_MAP.json`(sha 钉) |

M3 插入全部带标记:块 `# ── M3-BEGIN … # ── M3-END`、单行 `# M3-LINE`、改动行 `… # M3-ORIG: <原行>`。`beta_overlay.strip_m3` 按标记还原。

### 2.2 生产者(diff `producer_m3_fb5a9407.diff`)
| 文件 | 内容 |
|---|---|
| `fea171/beta_overlay_producer.py`(新) | 纯 numpy β 计算(§1.2) |
| `fea171/combo_stage.py` | `_uni` 之后算字段 —— **M3 的每条语句(含 log 与发布后的页报)都在一个 except 不会再抛的 try 里**,任何失败只会让本锚不写该字段,绝不进外层 except(那是 `_bail`「发布中止」);`_doc` 组好后 `if _beta_field is not None: _doc["beta_overlay"] = …`;预发布验收时若执行器树已有 `live/beta_overlay.py`,用它校验**已落暂存的字节**并把判词写进 `combo_live_status.json`(只记不拦) |
| `fea171/tests_beta_overlay_producer.py`(新) | 23 项检查,见 §4.2 |
基: `fb5a94074583b328…`(= `ops/producer_release/20260922/combo_stage.py`)。副本排除项:`state/`、`venv/`、`shadow_bundle*`、`*.tar.gz*`、`fea171/mini/`、`fea171/state_H_*.npz`、`fea171/ref_fea89.npz`、`__pycache__/`、`*.log`、`*.out`、`*.pid`。`fea171/combosnap_m3/` 是本次排演用的重放工具副本(只多了注入 5 行),**不属于发布件**。

## §3 与现有机制的交互(逐一)

| 机制 | 交互 | 处理 / 状态 |
|---|---|---|
| **HOLD**(文件缺失 / 校验失败 / f10 钉 / booster 钉) | 不进 `_trade`,零下单 | 对冲原样保持(套件 P1)。f10_sha_pin 拒收 ⇒ HOLD ⇒ 对冲不动。 |
| **king 形态回退**(`producer_prefix_fallback`,现配置未开) | 回退文件由 shadow_loop 写,无字段 | on ⇒ 「缺失即不做」,BTC 冻结 + HIGH |
| **DERISK / FLATTEN 阶梯** | `_scale_to` / `flatten_all` 按持仓缩放/平仓 | 对冲随书同比例缩 / 一起平(β_exec 本就随书缩放) |
| **逐名止损**(cf40ea21, wide: −30% × 2 锚, 冷却 7 天) | 深度按 BTC 整个仓位(含对冲)算 | 硬原因 ⇒ 暂停,BTC 按止损条款 maker 平仓;冷却期(7 天 = 42 锚)不下腿,每锚记 `hedge_gap_usdt` = 整笔意图,首锚 HIGH、其后 INFO 固定文本(套件 H1/H1b/H2/H3)。**待裁定 §7-2** |
| **比例响应**(EXE-01) | 若 BTC 被点名(≤5 名且 ≤2% gross)⇒ 局部平 BTC + 停开仓 | 停开仓期间对冲建不回来;对冲 >2% gross 时 BTC 被点名会超过比例门 ⇒ 走全书阶梯 |
| **§4-5e 持仓断裂** | 意图 = orders 行 `target_w × target_gross`,已含对冲 | 对冲没成交 = UNDERFILL(只告警,永不平仓);只有拆分**说不出话**(覆盖 <90%)时回到未拆分的 10%/名 规则 —— 对冲本身约 0.08–0.19 gross(M2 RESULT §1.3 路线 H 的 abs(h) 均值 0.083–0.117;预注册 §1 的 2026 事前 β −0.14…−0.19),那时未成交的对冲变动 >10% gross 会被读成断裂。**§7-5** |
| **§4-4b 有效杠杆** | ~~读 daily_nav 的 sizing gross,不含对冲~~ **`b81c4cb` 起(R10-A01)**:on 时 daily_nav 另记合计目标与读回 gross,cond4b 判三者最大值 | 下单前腿受账户预算约束(§8);现行报警 3.0× / 停机 5.0× 不改 |
| **场所上限截断** | 作用于 BTC **合并**目标 | 截了 ⇒ HIGH + `venue_capped` + `hedge_after_cap_usdt` + `hedge_gap_usdt` = 意图 − 截后(套件 P2/P2b/P3) |
| **2×minNotional dust** | M3b:BTC 仅因书内碎单不可交易时按合计值重判 | 书这一层照 off;C 不是碎单 ⇒ 下 C、放出只减;C 仍碎单 ⇒ 不动 + 缺口(套件 N1/N2/CD1/CD2/O1) |
| **持有退出 held_exit**(持有 BTC 但文件不目标 BTC) | M3b:名字级原因 | 暂停 + HIGH + 缺口,BTC 与 off 一样只减平掉(套件 O3/O4;近 167 个 combo 文件 0 次) —— **§7-1** |
| **场所撤名**(`venue_not_trading` / `venue_zero_cap` / `external_meta`) | BTC 被撤 ⇒ 不许开仓 | 硬原因 ⇒ 暂停 + HIGH + 缺口 = 整笔意图;BTC 走真实持仓只减(套件 W1:非 DRY 桩化 loop 里的 exchangeInfo 元数据排除;W2 对照) |
| **追单实验 C** | 投影净额含对冲 ⇒ 不修的话 C 会优先追反向残差去「中和」对冲 | 基准扣对冲意图(套件 R3);BTC 仍在随机化人口里(与其他名同待遇)。**§7-3** |
| **收锚中性页报 / 中性价格** | 原始 net/gross ≈ 对冲/gross,远超 ±3% | 改判扣对冲后的净额(套件 R4/R5);报表读者(`anchor_report` / `cost_drift` / `daily_summary`)仍读原始 `net_over_gross`,开 on 后会出现水平移位 —— **只记录,未改,§7-6** |
| **计划层手数** | BTC 步长 0.001(≈110 USDT @110k),minNotional 50 | `round_qty` 向零截断 ⇒ 计划层最多少一手(≈110 USDT),对冲小于约 2,200 USDT 时计划层交付比可能低于 0.95(目标层恒为 1);增量 < 50 USDT 被 `skipped_min_notional`;记在 `diag_plan`(`tol_usdt` 一手 / minNotional,`ok`) |
| **组合平价代理 comboparity** | 比较「归档 vs 重放」每个键 | 生产者在静默窗安装 ⇒ 同锚两边都有字段 ⇒ PARITY;仅当安装落在某锚的写与重放之间才会出现一次 `beta_overlay: present only in replay` |
| **on 之后切 shadow / 配置写坏** | **`b81c4cb` 起分开**:显式 off / shadow(或非外部书锚)释放并撤腿;配置损坏冻结在持的腿 | 见 §8.1「模式过渡」;原 §7-8 的问题已按此实现 |
| **生产者时间预算** | combo 发布窗 N+17…N+22:35,硬截止 N+22:40 | 字段计算 0.146 s + 校验 <0.1 s;页报放到发布之后 |

## §4 测试判词原文(真实退出码)

### 4.1 新套件 `live/tests_beta_overlay.py`(/usr/bin/python3 3.9.6,DRY_RUN(W 组为桩化的非 DRY);收据 `receipts/tests_beta_overlay_run10.log`,提交 `4dd7d53`,exit 0;`80ae104` 上重跑同判词,`receipts/c5/live_tests_beta_overlay.py.log`)
判词行原文:`TESTS_BETA_OVERLAY ALL PASS checks=125 failed=0`。承重的几行原文:
```
  OK   ★ Z field present, BTC HELD dust + a held untargeted name — mode off: plans / dry-run orders / order rows / ctx / loop state / record IDENTICAL to stripped
  OK   ★ Z-M1 RED-CAPABLE: the on-path-in-off mutant (BTC forced into the symbol set) differs from the stripped reference — ['ctx', 'out']
  OK   ★ Z-M3 RED-CAPABLE: a mutant that runs the ON stage while the switch is off differs in plans — ['plans', 'actions', 'ctx', 'out', 'pending']
  OK   ★ R9 mode off: the anchors row is byte-identical to the stripped executor's (no m3 key)
  OK   ★ D1 every non-BTC target is BITWISE the off-mode target (the leg changes nothing else) — ['BTCUSDT']
  OK   ★ D2 BTC = the book's executed BTC entry + (-beta_exec), beta recomputed HERE from the fixture's betas — (-1961.8216336358578, 0.0, -1961.8216336358578)
  OK   ★ D3 ex-ante beta of the final target moved by exactly -beta_exec: ratio 1 within 1e-9 (prereg R3 band is 0.95-1.05) — (1.0, 0.0)
  OK   D6 plan level: the BTC order leaves the book at book + hedge within ONE lot of BTC at the mid (round_qty floors toward zero) — (-1950.0, -1961.8216336358578, 50.0, None)
  OK   ★ D8 RED control (route L): through the reshape the file hedge is spread — executed net ≈ 0 and the beta move is far from -beta_exec (ratio outside 0.95-1.05) — (-1.1368683772161603e-13, -0.09201097455771025)
  OK   ★ N1 book BTC 4 USDT < 2 x 5 (dust alone: the book stage pops it, executed base 0) and |leg| > 100x that ⇒ the combined value decides: a BTC order is SENT, not reduce-only (applied_via_combined) — (4.0, -1961.8216336358578, 1, 'applied_via_combined')
  OK   ★ N2 RED control (mutant = M2 route H: BTC's dust judged on the book component and dust blocks the leg): the SAME input sends NO BTC order and records the whole intent as the gap — ('suspended_btc_untradable', -1961.8216336358578)
  OK   CD1 unheld: status combined_dust, NOTHING touched (BTC stays popped), NO BTC order, the gap is the (tiny) leg, an INFO line names it — ('combined_dust', -1.7239866643267874)
  OK   CD2 held 1500: nothing touched — the book stage's clamp stands (reduced toward the book's small BTC, reduce-only), recorded — ({'reduced': ['BTCUSDT']}, 3.5087719298245887)
  OK   ★ O1 on: a HELD BTC whose book component alone is dust is neither clamped nor reduce-only; target = book entry + leg = -beta(non-BTC book) (1e-9 rel) — ({}, False)
  OK   O3 on (M3b): a held BTC the file no longer targets IS an external_held_exit — a name-level reason — so the leg is SUSPENDED, the whole intent recorded as the gap, HIGH; BTC exits reduce-only exactly as off (0 of the last 167 combo files dropped BTC) — ('suspended_btc_untradable', ['external_held_exit'])
  OK   H1b the whole intended leg is recorded as the hedge gap, and the HIGH page says so (never a silent drop) — (-1961.8216336358578, -1961.8216336358578)
  OK   ★ W1 venue-withheld BTC (meta: underlyingType≠COIN): status suspended (external_meta), the whole intent is the recorded gap, HIGH names the gap; BTC reduced on its TRUE position, reduce-only — ('TRADE', 'suspended_btc_untradable', ['external_meta'], -1921.7791411042945, True)
  OK   ★ M field absent: refused (field_missing), BTC frozen at 1500 (target == held), NO BTC order, HIGH '缺失即不做' — ('refused', 'field_missing', 1500.0, 0)
  OK   ★ M-RED missing ⇒ every beta 1: with the missing check removed the SAME input SENDS a BTC order (real code: none) — the check is load-bearing — (1, 0, 126.3803680981603)
  OK   ★ M-RED missing ⇒ hedge 0 (unwind): with the missing check removed the SAME input SENDS a BTC order (real code: none) — the check is load-bearing — (1, 0, 126.38036809815951)
```
先断言基线为绿:[B] 三格(剥离执行器在该夹具上 TRADE、gross = NAV×2.0、文件 −6% 净额被 reshape 归零、BTC dust 被 pop、剥离模块里没有 BO)在任何 M3 判断之前通过。[Z] 12 格 × 相同 + 2 个变异体变红;R9 把 off 的 anchors 行经真实 PilotLogger 写盘读回,与剥离执行器写的行逐字节相同;[D] 的比值在测试里用夹具 β 独立重算(不读模块自己的诊断),参照是缺省 off 书;D0 断言该夹具 |β_exec| > 5% gross,诊断才有分辨率;[M] 四种缺失各一格(其余书与同持仓的 off 书逐位相同)+ 两个变异体。

### 4.2 生产者套件 `fea171/tests_beta_overlay_producer.py`(生产者 venv python;收据 `receipts/TESTS_BETA_OVERLAY_PRODUCER.log`,exit 0)
判词行原文:`TESTS_BETA_OVERLAY_PRODUCER ALL PASS checks=23 failed=0`。
```
  OK   T1a every row after the anchor rewritten ⇒ field byte-identical
  OK   T1b control: the row closing AT the anchor changed ⇒ the beta changes (the bar ending at A is in the sample) — (2.0000000000000004, 2.0046438993457274)
  OK   T3a 120 valid pairs ⇒ estimated beta 2.0 — (120, 2.0)
  OK   T3b 119 valid pairs ⇒ fallback exactly 1.0 — (119, 1.0)
  OK   T2b BTC's own beta is exactly 1.0 and it is written first
  OK   T5a both bars sharing the boundary are invalid (178 pairs) and the beta stays 2.0 exactly — (178, 2.0)
  OK   T5b RED control: a mutant without the start-row rule counts 179 pairs and the spike moves the beta — (179, 1.9780679998469834)
  OK   T7a float16 cache field, JSON round-trip ⇒ ACCEPTED by the executor validator — (None, '')
  OK   T8b REAL causality: the field at A-24h from the full cache == from the cache truncated at A-24h (byte-identical)
```
T7(配对)**必需**:没给 `M3_EXECUTOR_ROOT` 时判红,不跳过。T8 读实盘 `~/wide_shadow/state/rolling.npz`(只读),最新锚计算 0.144 s,449 估计 / 0 回落。

### 4.3 剥离收据(`devices/m3_strip_receipt.py`;收据 `receipts/M3_STRIP_RECEIPT_b66257b.json`,exit 0)
`M3_STRIP_RECEIPT VERDICT=IDENTICAL base=b66257b scheduler/anchor_loop.py=== live/binance_executor.py=== live/external_book.py===`
(剥离后 sha256 前缀 = b66257b blob:anchor_loop `5f91aeb4a7268a17`、binance_executor `b4cb9d9cb39c5e56`、external_book `b4b18dc08d5d7f22`;三个提交后各跑一次,均 IDENTICAL。)最终补丁(sha256 `9704200d…`,= `git diff b66257b 80ae104`)在全新的 `~/dl_quant_live` 克隆(检出 b66257b;运行树 HEAD 11:3xZ 仍为 b66257b)上 `git apply --check` 通过,打完 18 个文件 sha 全部对上 `EXECUTOR_FILES_SHA256.txt`(`18 OK`),打完后的树 `git write-tree` = `9d8e619af06fc91b…` = `80ae104^{tree}`(逐位同一棵树),在该克隆上再跑剥离收据仍 `VERDICT=IDENTICAL`。(`4dd7d53` 的补丁 `b9ca43c9…` 同样验过;两者只差两处注释。)

### 4.4 生产者沙箱排演(08Z 锚 1790150400;生产 comboparity 工具的副本只多注入 5 行(`devices/combo_parity_replay_m3inject.diff`),内核沙箱禁网禁写源树;收据 `receipts/M3_PRODUCER_REHEARSAL_1790150400*`)
```
M3_INJECTED combo_stage=41f9174d7d6400f5 beta_overlay_producer=b77c180d69170988
combo_stage rc=0 (sandbox /Users/haosiyu/cc_tmp/m3_impl_20260923/parity_sb/1790150400)
[  32.9s] M3 beta_overlay: {'ok': True, 'version': 'm3_beta_v1', 'n_names': 450, 'n_estimated': 449, 'n_fallback': 0, 'n_no_cache_column': 0, 'elapsed_s': 0.273}
[  33.5s] ⑤ COMBO_LIVE 写者完成 rehearsal=True n=292 gross=0.8377 读者验收 ok age=60.0s
PARITY_MISMATCH anchor 1790150400 why=['beta_overlay: present only in replay'] weights={'n_archived': 292, 'n_replay': 292, 'n_differing': 0, 'max_abs_dw': 0.0}
REPLAY_EXIT=2
```
预期的就是这个 MISMATCH:唯一差异键是新字段;weights 292 名 max|Δw| = 0;重放的 weights npz sha `8f60ca84…` = 归档 `weights_sha`。(这是最终版 combo_stage `41f9174d`;第一版 `03ac1f81` 的排演结果相同、`elapsed_s` 0.146 —— 0.273 是与全电池并行时测的。)沙箱 `combo_live_status.json` 里执行器校验器(本分支 `live/beta_overlay.py`)对已落暂存字节的判词 `reader_verdict.ok = true`,`betas_sha256 0f125b6e…`。(`n_names` 450 = 宇宙 450 名,BTC 就在宇宙里。)

### 4.5 受影响的现有套件(分支 vs 纯净 `b66257b` 同解释器同环境)与全电池
**定向(纯净 b66257b worktree 与分支 worktree,只有 git 跟踪的 state;`/usr/bin/python3` 3.9.6,env -i DRY_RUN;收据 `receipts/targeted/`)**:31 个套件 = 受 M3 触及的 30 个现有套件 + 新套件。
- 基线 `b66257b`:29/30 exit 0;`tests_reject_topup` exit 1 —— 基线自己就红(读实盘账本,干净克隆只有 1 天夹具:`AFTER the fix, the refusals DO receive top-ups — no post-fix anchor in the tree yet — NOT OBSERVABLE`),与 M3 无关;在全电池(复制了实盘账本)里它是绿的。
- 分支第一轮(提交前代码):`tests_signal_and_loop` exit 1 —— 真缺陷,**已修**:该套件用 `executor=None` 构造 loop 直接调 `_trade`,M3 块在重置执行器级记录时 `AttributeError: 'NoneType' object has no attribute '_m3_overlay_leg'`(收据 `run1_exec__tests_signal_and_loop_BEFORE_FIX.log`);修为只在执行器存在时重置。
- 分支第二轮(提交后代码 `b7a44eb` = 现 `8725e7d` 的树,独立 worktree,同样只有 git 跟踪的 state):30/31 exit 0,唯一的 1 是 `tests_reject_topup`(与基线同红同因);与基线逐套件同码,新套件 exit 0(收据 `targeted/run2_summary.txt`)。⚠ 这 31 个是我挑的,**没挑到** `tests_rehearsal_anchor`(rebalance_id 普查)—— 它由全电池第一轮抓到,见下。
**盘开关扫描**(把克隆的 `config/book.json` 依次写成 off / shadow / on,跑 5 个由真实配置派生夹具的套件,之后按字节恢复):15/15 exit 0,`config restored byte-identical`(收据 `targeted/disk_sweep_summary.txt`)。
**全电池(离线内核沙箱,先复制实盘 state:pilot_log 54/54 天)**:
- 第一轮(`b7a44eb` = 现 `8725e7d` 的树,10:11:49Z 起,`/usr/bin/python3` 3.9.6 torch 2.2.2,`.env=false`,notify_audit 2286 行 / 最新 1.4 h;`OFFLINE_LEDGER_COPY: checkout 54 days cover all 53 completed production days`;`OFFLINE_KERNEL_PROBE: credential read/write, outside write, network denied`):**162/163 exit 0**,判词原文 `ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)` / `OFFLINE_ACCEPTANCE_EXIT: 1`(收据 `receipts/OFFLINE_BATTERY_b7a44eb.log`)。新套件 `tests_beta_overlay` 在其中 exit 0。唯一的红 `tests_rehearsal_anchor` exit 1,判词原文 `FAIL  ★★ every file touching rebalance_id is declared either a counting site or exempt  — UNDECLARED: ['live/beta_overlay.py'] — a new counting site must be a decision, not a default`:我的模块文档串里写了连接键 `rebalance_id`,触发 rebalance_id 普查。**修法 = 按普查的设计路径登记为 exempt 并写理由**(它只在文档串里出现,不铸、不存、不计、不按 id 分组;不是把字符串改掉躲过扫描)。同轮另两处改进一并进第二次提交:① 持续暂停的告警改为不含数字的固定文本(`alarm_policy` 对 24 h 内相同正文去重 —— 原来带「现持 xxxU」每锚都不同,会每锚推送);② `diag_plan` 记 `tol_usdt`(当时为半手;终版改为一手,因 `round_qty` 向零截断;被 minNotional 跳过时取 minNotional)与 `ok`,步长/价格未知时 `ok = None`(不测量不判好)。
- 第二轮(`98423ab` = 现 `11aa8d1` 的树,10:33:57Z 起):**`ACCEPTANCE: ALL GREEN (163/163 suites exit 0)`**,`OFFLINE_ACCEPTANCE_EXIT: 0`(收据 `receipts/OFFLINE_BATTERY_98423ab.log`)。
- 第三轮(`c71ca7a`,AMENDMENT_1 第一种读法,10:52Z 起):我在 M3b 钩子提交后决定改为逐条对齐,**主动停掉**(TaskStop,自己的后台任务);停时已跑 118/163 套全部 exit 0(收据 `receipts/OFFLINE_BATTERY_c71ca7a_STOPPED_PARTIAL.log`,**不作判词**)。
- 第四轮(`4dd7d53`,终版代码,11:02:18Z 起、11:19:29Z 止;`INTERPRETER  resolved=/usr/bin/python3 … version=3.9.6  torch=2.2.2  ACCEPT_PY=SET:/usr/bin/python3`;`TREE-STATE   .env=false  notify_audit_lines=2286  notify_audit_newest_age_hours=2.3`;`OFFLINE_LEDGER_COPY: checkout 54 days cover all 53 completed production days (latest production day 20260923 may be in progress)`;`OFFLINE_KERNEL_PROBE: credential read/write, outside write, network denied`):**`ACCEPTANCE: ALL GREEN (163/163 suites exit 0)`**,`OFFLINE_ACCEPTANCE_EXIT: 0`,外层 `OFFLINE_EXIT=0`(收据 `receipts/OFFLINE_BATTERY_4dd7d53.log`);`tests_beta_overlay` 与 `tests_rehearsal_anchor` 两行均 exit 0。
- 第五个提交 `80ae104`(电池之后):只把 `live/beta_overlay.py` 两处 `#` 注释改对 —— `SOFT_SOURCES` 上方的注释还是 `8725e7d`…`c71ca7a` 那几版(held_exit 也算软原因)的措辞(「(too small to trade, or not targeted), and the hedge leg owns the position」),与 `4dd7d53` 起只有 `external_dust` 是软原因不符;计划层容差注释写「half a lot」,而实现自 `c71ca7a` 起是一手。**没有对 `80ae104` 重跑全电池**(静默窗 11:40Z 关,全电池约 17 分钟)。判词转移的依据:① **编译码恒等**(`devices/code_identity.py`:同一文件名编译两版、比 marshal 字节):`CODE_IDENTITY IDENTICAL`,两边 `code_sha ffeb87292a4d899c`、`lines 465`;两个负对照(改一个常量 / 改文档串一个字)都判 `CODE_IDENTITY DIFFERENT` exit 1,比较有分辨率;② 读源码**文本**的套件(普查 / 导入 / 作用域 / 扫描类 + 新套件,16 个)在 `80ae104` 上重跑全部 exit 0,判词行如 `TESTS_BETA_OVERLAY ALL PASS checks=125 failed=0`、`ALL PASS   (132 checks)`(tests_external_book)、`[guard-reach] OK — every guard declares what it cannot stop, …`(收据 `receipts/c5/` 与 `c5_summary.txt`,复跑 `devices/run_c5_textual.sh`)。部署 A5 的 `safe_commit` 会在确切的树上再跑一次全电池 —— 那才是 `80ae104` 本身的全电池判词。
- ⚠ **我的一次越界(如实记录)**:`run_c5_textual.sh` 第一版把 `tests_acceptance_entrypoints` 列进了读文本的套件;它单独运行时会执行 `bash run_acceptance.sh`,即**在离线内核沙箱之外**跑整套电池。它 11:20:03Z 起在克隆里跑(克隆无 `.env` ⇒ 无凭证),约 11:30Z 我发现后用 TaskStop 停掉自己的后台任务,按 PID 核对其进程树(37559/37562/37564/41505/41508)已全部消失;时段在静默窗内。副作用核查:`find -newer` 对 `~/dl_quant_live`、`~/wide_shadow` 只命中生产守护自己的 `stop_overlay.log` 轮询(`2026-09-23T11:30:08Z no new anchor`),克隆外没有写;但那 10 分钟没有内核级禁网,**无法证明没有发出过无签名的公共请求** —— 107 份子日志里只见到桩化/断言文本里的 URL 字样。脚本已改为排除它并写明原因(第一版的摘要留作 `receipts/c5_summary_run1_STOPPED.txt`)。

**盘开关扫描**:`c71ca7a` 15/15 exit 0;`4dd7d53` 15/15 exit 0,`config restored byte-identical`(`targeted/disk_sweep_v4_summary.txt`)。

**生产者发布件的既有测试**(`ops/producer_release/20260922` 的 8 个 unittest 模块,生产者 venv,把其中的 `combo_stage.py` 换成本包版本再跑;收据 `receipts/producer_release_tests/`):基线 8/8 OK;**第一版本包 combo_stage 有 2 个模块失败** —— `tests_combo_publication_boundary` 的 `test_valid_candidate_passes_real_reader_before_live_replacements` 断言 `self.assertFalse(failed)` 失败:它的执行环境里没有 `rts/RD/_page`,我的 `log(...)` 与发布后的 `_page(...)` 在内层 try 之外,NameError 走进了外层 except ⇒ `_bail` ⇒ 一本已经发布的书被报成中止。**真缺陷,已修**(全部移进内层 try,页报再包一层);修后 8/8 OK(`release_tests_summary.txt`)。这组测试在它们的环境里走的正是「M3 失败 ⇒ 不写字段、发布逐字节照旧」这条路。

### 4.6 这些绿**没有**证明的
- 没有交易所:所有执行器测试都是 DRY_RUN + 桩 bookTicker;真实 BTC 手数、minNotional、部分成交、maker/taker 分配、−4400 账户锁下的对冲腿行为都没有被执行过。开 on 的第一锚就是第一次。
- β 数值的正确性只对合成序列与因果性做了证明;生产 β 与 M2/M3 研究用认证价表 β 的差没有测(§7-4)。
- 全电池只在盘上 `mode=off` 下跑过;shadow / on 下只跑了 5 个由真实配置派生夹具的套件(盘开关扫描)。
- 生产者的改动只在排演沙箱与发布件测试的环境里跑过;真实守护在 N+17…N+22:40 窗里的耗时(本机实测 0.146 s,与电池并行 0.273 s)要到安装后的第一锚才是实测。
- 预注册 R1/R2/R4(已实现 β、BTC 大涨日、成本)是研究评估的事,本包不产出也不判。

## §5 部署手册(逐字命令;每一步都在静默窗 [N+1:00, N+3:40] 内;不在 N+12…N+30 跑任何重活)

**阶段 A — 执行器上线(开关 off,行为不变)** 需用户一字(代码进运行树)。
```bash
# A0 前提: 运行树 = b66257b、代码区干净、上一锚已收尾
git -C ~/dl_quant_live rev-parse HEAD                      # 期望 b66257b6e86c18ed27c7971aa7fed64a69d71444
tail -1 ~/dl_quant_live/state/anchor_runs.log               # 期望 上一锚 anchor done rc=0
# A1 隔离 main 检出(按记忆 executor_deploy_protocol_isolated_checkout_2026_09_23 配 git 身份)
D=~/cc_tmp/m3_deploy_$(date -u +%Y%m%dT%H%MZ)
git clone ~/dl_quant_live "$D" && git -C "$D" remote set-url origin https://github.com/allenamy/dl_quant_live.git
git -C "$D" checkout main && git -C "$D" rev-parse HEAD     # 期望 b66257b…
git -C "$D" config user.name "$(git -C ~/dl_quant_live log -1 --format=%an)"; git -C "$D" config user.email "$(git -C ~/dl_quant_live log -1 --format=%ae)"
# A2 打补丁并核 sha
P=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/m3_impl_2026-09-23
git -C "$D" apply --check "$P/executor_m3_b66257b.patch" && git -C "$D" apply "$P/executor_m3_b66257b.patch"
( cd "$D" && shasum -a 256 -c "$P/EXECUTOR_FILES_SHA256.txt" )          # 期望 全部 OK
# A3 剥离收据(off == b66257b 的源码层证明)
/usr/bin/python3 "$P/devices/m3_strip_receipt.py" "$D" b66257b "$D/../m3_strip_receipt_deploy.json"   # 期望 VERDICT=IDENTICAL, exit 0
# A4 复制实盘 state(离线电池强制; 同 lead_deploy_20260923/snapshot_state.sh)
rsync -a --exclude='/acceptance/' --exclude='quarantine/' --exclude='__pycache__/' --exclude='/pycache_void/' \
      --exclude='/*.log' --exclude='/*.out' --exclude='/anchor.lock' ~/dl_quant_live/state/ "$D/state/"
# A5 safe_commit(离线沙箱全电池, 全绿才提交并推 main); 路径逐一列出
cd "$D" && bash ops/safe_commit.sh "M3 BTC-beta overlay leg on the executed book (PREREG_m3 24c3f803f): mode off by default = b66257b behaviour byte for byte" \
  live/beta_overlay.py live/tests_beta_overlay.py scheduler/anchor_loop.py live/binance_executor.py live/external_book.py live/watchdog.py \
  config/book.json run_acceptance.sh ops/gate_coverage.py live/tests_imports.py live/tests_external_book.py \
  live/tests_gross_ladder_retired.py live/tests_per_name_stop.py live/tests_signal_and_loop.py live/tests_rehearsal_anchor.py \
  ops/producer_release/20260923_m3/combo_stage.py ops/producer_release/20260923_m3/beta_overlay_producer.py \
  ops/producer_release/20260923_m3/tests_beta_overlay_producer.py ops/producer_release/20260923_m3/SOURCE_MAP.json
echo "SAFE_COMMIT_RC=$?"; git -C "$D" rev-parse HEAD                          # 记下新 sha = <NEW>
# A6 持 anchor.lock 快进运行树(静默窗; 无 run_anchor 进程)
/usr/bin/python3 ~/cc_tmp/lead_deploy_20260923/ff_running_tree.py <NEW>        # 期望 FF_OK before=b66257b… after=<NEW>
# A7 部署后只读核
git -C ~/dl_quant_live rev-parse --short HEAD origin/main                      # 两行 <NEW>
git -C ~/dl_quant_live diff --stat b66257b HEAD | tail -1                       # 18 files changed
/usr/bin/python3 -c 'import json;print(json.load(open("/Users/haosiyu/dl_quant_live/config/book.json"))["beta_overlay"]["mode"])'   # off
```
**A 的首锚验收(off)**:该锚 anchors 行**没有** `m3_beta_overlay` 键;orders 行没有 `m3_overlay_leg`;无 `M3 ` 开头的告警;其余与前一锚同形(TRADE、下单数、rc=0)。

**阶段 B — 生产者安装(写字段;执行器仍 off,无书行为变化)** 在 A 之后(预发布验收才能用上执行器的校验器)。
```bash
R=~/dl_quant_live/ops/producer_release/20260923_m3; F=~/wide_shadow/fea171
shasum -a 256 "$F/combo_stage.py"                               # 期望 fb5a94074583b328…(基)
TS=$(date -u +%Y%m%dT%H%MZ); cp -p "$F/combo_stage.py" "$F/combo_stage.py.pre_m3_${TS}_fb5a9407"
for f in beta_overlay_producer.py tests_beta_overlay_producer.py combo_stage.py; do
  cp "$R/$f" "$F/.$f.m3tmp" && mv "$F/.$f.m3tmp" "$F/$f"; done           # combo_stage.py 最后换(同目录原子 rename)
( cd "$F" && shasum -a 256 combo_stage.py beta_overlay_producer.py tests_beta_overlay_producer.py )   # 对 SOURCE_MAP.json
PYTHONDONTWRITEBYTECODE=1 M3_EXECUTOR_ROOT=~/dl_quant_live M3_REAL_ROLLING=$HOME/wide_shadow/state/rolling.npz \
  M3_REAL_SYMS=$F/xfer_syms.npz ~/wide_shadow/venv/bin/python "$F/tests_beta_overlay_producer.py"; echo "EXIT=$?"   # ALL PASS, EXIT=0
```
守护每锚新起 python 跑 combo_stage,**不需要重启**。**B 的首锚验收**:`~/wide_shadow/state/combo_live_status.json` 的 `beta_overlay.ok == true`、`reader_verdict.ok == true`、`elapsed_s < 1`;`state/target_live/<A>.json` 含 `beta_overlay`,`data_cutoff_ts == A`,`n_names == 450`(宇宙,BTC 在其中);combo `written_utc` 与前几锚同相位(不晚于 N+22:40);执行器该锚照常 TRADE;comboparity 该锚 PARITY。

**阶段 C — shadow(可选但建议 ≥2 锚)** 同 A 的隔离检出 + safe_commit + FF 路径,只改 `config/book.json` 的 `"mode": "shadow"`。验收:anchors 行 `m3_beta_overlay.status == "shadow"`、`field_ok == true`、`data_cutoff_ts == 名义锚`、`hedge_target_usdt` 有限;orders 与 off 同形(无 BTC 对冲单、无 `m3_overlay_leg`)。shadow 与 on 用同一本书(off 书),记录里 `shadow_would_be` 给出 on 时的状态(`applied` / `applied_via_combined`)。

**阶段 D — on(书行为改动:须预注册 R1–R3 全过 + 用户裁定)** 同路径改 `"mode": "on"`,**并按用户裁定写入 `"max_combined_leverage": <值>`**(§8.3;不写 ⇒ on 也不下腿,`budget_unset` + HIGH)。首锚验收(另加:daily_nav 当锚行带 `base_sizing_gross` / `combined_target_gross` / `readback_gross`,看门狗 `cond4b_leverage.m3_numerator` 存在且 `actual_leverage` = max(三者)/nav;`budget.truncated == false`,除非预期截断):
1. anchors 行 `m3_beta_overlay.status` 为 `applied_via_combined`(实盘 BTC 书内分量几乎总是碎单,预期是这个)或 `applied`;`btc_dust_only` 与之相符;经合计值时 `released_from` 列出 BTC 被放出的名单;`diag_target.ok == true`、`ratio` = 1(1e-9);`diag_plan.ok == true`(容差一手);`hedge_gap_usdt == 0`;`venue_capped == false`;`beta_final_usdt ≈ 0`。
2. BTCUSDT 订单行带 `m3_overlay_leg`,`reduce_only == false`;成交后场所 BTC 持仓 ≈ `btc_combined_target_usdt`(一手以内)。
3. 收锚 `net_ex_overlay_over_gross` 在 ±3% 内(不页报);原始 `net_over_gross` ≈ 对冲/gross。
4. 看门狗未触发;若 BTC 没成交完,§4-5e 记 UNDERFILL 告警而非断裂。
5. loop state `m3_overlay_last.status == "applied"`;下一锚 BTC 不在 clamp 名单、不带 reduce-only。

**回滚**
- **腿**:把 mode 改回 `off`(同路径提交 + FF;**必须是有效配置的显式 off** —— 配置写坏会冻结在持的腿而不是撤下,§8.1)。下一锚持有的 BTC 对冲成为普通「持有的 dust / 不再目标的名」,经既有 clamp/flatten_only 只减通道(maker + 强制补单)平掉 —— 这是一次完整的对冲平仓成本。急停仍是 `bash ops/KILL.sh`。
- **生产者**:先确保 mode 为 off(否则 on 下每锚「缺失即不做」+ HIGH),再 `cp -p "$F/combo_stage.py.pre_m3_<TS>_fb5a9407" "$F/.c.tmp" && mv "$F/.c.tmp" "$F/combo_stage.py"`;`beta_overlay_producer.py` 可留(无人 import)。
- **执行器代码**(通常不需要:mode off 已与 b66257b 行为逐位相同):先 mode off 且对冲已平,再用树替换正向提交回到 b66257b 的树(同 `RUNBOOK_deploy_executor_6661ea3_2026-09-17.md` §4 的做法,但在隔离检出里做;safe_commit 不能提交删除,故不用它):
```bash
git -C "$D" fetch origin main && git -C "$D" checkout -q origin/main
RB=$(git -C "$D" commit-tree "$(git -C "$D" rev-parse 'b66257b^{tree}')" -p "$(git -C "$D" rev-parse origin/main)" -m "rollback M3: executor tree back to b66257b (tree swap, forward commit, no force push)")
git -C "$D" diff --stat b66257b "$RB" | tail -1                                   # 期望 空(树相同)
git -C "$D" push origin "$RB:refs/heads/main" && /usr/bin/python3 ~/cc_tmp/lead_deploy_20260923/ff_running_tree.py "$RB"
```
旧码看到的 BTC 就是普通持仓,效果与 mode off 相同。

## §6 复跑命令(逐字)
见 `multi_asset/exports/research/m3_impl_2026-09-23/devices/run_m3_impl_checks.sh`(1–9 步:新套件、生产者套件、剥离收据、生产者排演、定向套件、盘开关扫描、全电池、发布件测试、补丁生成与全新克隆核对);第五提交的核对是 `devices/run_c5_textual.sh`(调 `devices/code_identity.py`)。

## §7 上线前必须由人决定的事项
1. **生产语义已与评估的 M3b 钩子逐条一致**(`c414ca4cf`;§1.3),M3b 的 R1–R3 读数因此描述生产行为。随之接受的两个取舍需人确认:① **持有退出算名字级原因** —— 某锚生产者文件不再目标 BTC 而我们持有对冲时,腿暂停、BTC 与 off 一样只减平掉(一次对冲平仓成本;近 167 个 combo 文件 0 次发生);② **add_blocked 的 BTC 以持仓作底座值** —— 只在书的 BTC 权重大于近零对冲时可能,合计值会把旧持仓与新腿相加(量级 = 书的 BTC 权重,几十 USDT)。若要改这两条,须评估与生产同步改(新修订)。
2. **逐名止损是否作用于对冲腿**:现在是(BTC 整仓 −30% × 2 锚 ⇒ maker 平仓 + 7 天冷却无对冲;冷却期每锚记整笔意图为对冲缺口,首锚 HIGH、其后去重 INFO —— 不静默,但也不下)。备选:腿存在时 BTC 豁免止损 / 冷却(新条款,需裁定);场所撤名(零上限 / 非 TRADING / 元数据)下不下腿是场所事实,不在此选项内。
3. **追单实验 C**:已改为扣对冲意图的中性基准(否则 C 系统性地优先追反向残差)。认证仿真**确实复刻了 C 且没扣**(`multi_asset/exports/research/replay_exec_2026-09-19/exec_sim.py:632`(sha256 `29679672…` = 认证件)以 `book_net_usdt=prev_sum + first_sum + refused_sum` 调 `plan_experiment`,持仓里的对冲腿算在净额里)⇒ 在这一点上仿真与本包生产语义不一致,M3 评估的 R4/Sharpe 读数里含「C 追反向残差去中和对冲」的效应,生产不会有;BTC 仍参与 50/50 随机化 —— 是否应让对冲腿恒追(不入实验)需裁定。
4. **β 数据源**:生产用生产者滚动缓存(ret5 截 ±0.30、float16),M2/M3 研究用认证价表。建议开 on 前在 pod2 用 09-13…09-18 的重叠锚对比两边 β(不是收益数字),给出最大差。
5. **首锚建仓**:开 on 的第一锚会一次建满对冲(约 0.08–0.19 gross 的单名 BTC 单,量级出处同 §3)。§4-5e 拆分下未成交只是 UNDERFILL,但在拆分说不出话的锚(覆盖 <90%)会按 10%/名 判断裂;另外 −4400 账户锁(已发生 6 次)期间开仓单不发。是否分步建仓(新参数,预注册没有)需裁定。
6. **报表读者**:`anchor_report` / `cost_drift` / `daily_summary` 读原始 `net_over_gross`,开 on 后出现水平移位;本包只改了会页报的两个读者。是否让报表改读 `net_ex_overlay_*` 需裁定。
7. **杠杆(`b81c4cb` 起已实现为预算键,数值待裁定,§8.3)**:实际持仓 gross = sizing gross + |对冲|(2.0× NAV → 约 2.2–2.4×,按上面的对冲量级);§4-4b 用 sizing gross 不受影响;初始保证金地板 gross/20 仍远。是否把对冲算进 `gross_mult` 预算(即缩书让总 gross 不变)是另一个政策问题,预注册没有。
8. ~~**on 期间配置写坏 / 改成 shadow 会平掉对冲**~~(`b81c4cb` 已分开:配置损坏冻结、显式 shadow/off 撤腿;原文保留):两者都按 off 的书层语义处理 BTC(下一锚经只减通道平掉)。若希望「开关无效 ⇒ 冻结 BTC」而不是「⇒ 平掉」,需要记住上一锚的档位(新语义,需裁定)。
9. **计划层手数截断**:`round_qty` 向零截断,BTC 一手 ≈ 110 USDT;对冲小于约 2,200 USDT 时单锚计划层交付比可能低于 0.95(目标层恒为 1)。R3 的判法若看计划层,需知道这一点;是否改成就近取整是执行器的共同规则,不在本包范围。

## §8 第十轮独立复审的修复(提交 `b81c4cb` + `5b3d89c`(只改套件夹具),在 `80ae104` 之上;未推送、未部署,开关缺省仍 off,预算键**不设值**)

复审件:研究员工作树 `.claude/worktrees/codex-strategy-uplift-20260920/docs/REVIEW_round10_core_release_2026-09-23.md` §3 R10-A01 / R10-A02、§5 A.4-4/5/11;lead 已核实源码论据。

### 8.1 改了什么(文件:行,均为 `b81c4cb`;`5b3d89c` 相对它只改 `live/tests_beta_overlay.py` 的非 DRY 桩快照)
| 问题 | 文件:行 | 改法 |
|---|---|---|
| **R10-A01 [P1] 对冲加的杠杆看门狗看不见、也没有上限** | `live/beta_overlay.py:97–122` | 新配置键 `beta_overlay.max_combined_leverage`(单位 ×NAV)。**不给缺省值**:对冲是否占用 2× 预算是政策裁定。on 下缺它 ⇒ 腿被拒(`budget_unset`,HIGH,已持 BTC 冻结);值非法(非正数 / 非有限 / 字符串 / 布尔)⇒ 配置损坏(见下「模式过渡」)。 |
| 〃 | `live/beta_overlay.py:232–254`(`budget_scale`)、`stage` 内 | **下单前**把腿按比例缩到「合计目标 gross ≤ max(预算×NAV, 书自己的 gross)」:书本身已超预算时(那是 sizer 的事),腿只允许不增加 gross。被截 ⇒ HIGH 具名(意图→实下、合计 gross、预算、NAV),截掉的部分记为对冲缺口;缩到 0 ⇒ 状态 `budget_zero`,BTC 按书的决定;NAV 不可得 ⇒ 拒(`nav_unknown`),不当作「无上限」。 |
| 〃 | `scheduler/anchor_loop.py:3231–3233, 3278, 3281–3284`;`live/beta_overlay.py:559–604`(`nav_fields` / `post_fill_check`) | daily_nav 行在 on(或冻结腿)时**另记**三个口径:`base_sizing_gross`(= NAV×gross_mult,= 原 `target_gross`,**不替换**)、`combined_target_gross`(对冲、预算、场所上限之后的最终目标 Σ\|w\|)、`readback_gross`(同一次账户读取的场所持仓 Σ\|名义\|,成交之后;任一名义不可读 ⇒ None,不当 0)。成交后读回超出 max(预算×NAV, sizing gross) 或读不到 ⇒ HIGH。off 时一个键都不加(套件 L10:与剥离执行器的 daily_nav 行逐字节相同)。 |
| 〃 | `live/watchdog.py:2298–2309, 2318–2324, 2356–2361`(cond4b) | 带新键的行:杠杆 = **max(target_gross, combined_target_gross, readback_gross) / nav**,并在 detail 里写明分子;不带新键的行(今天的每一行)判法与输出逐字节不变(套件 L7)。**被判的那一行 `_lev_rows.append(...)` 原样保留**(`tests_guard_calibers` 的变异体钉在这一行上),M3 改动在其后的块里覆盖最后一个元素。报警/停机倍数沿用现行 1.5 / 2.5 × target_leverage,未改。 |
| **R10-A02 [P2] 冻结 BTC 时从中性读数扣掉了整个 BTC** | `live/beta_overlay.py` `stage` 拒收分支、`after_cap`(455–486)、`neutrality_view`(525–557) | 叠加腿的净额**在每一层都定义为「最终 BTC 目标 − 书内 BTC 分量」**:冻结 ⇒ 现持 − 书内 BTC(复审例 +1500 − 500 = 1000,残差 0);场所上限截断 ⇒ 记录与追单基准都跟截后的目标(`anchor_loop.py:2238–2245` 在上限之后重设执行器的 `_m3_overlay_net_usdt`);成交后 ⇒ `m3_overlay_realised_usdt` = 场所 BTC − 书内 BTC,`m3_overlay_fill_gap_usdt` = 目标叠加 − 已实现。计划层 `diag_plan` 原本就是「计划后 BTC − 书内 BTC」,同一口径。 |
| **模式过渡**(§5 A.4-4/11) | `scheduler/anchor_loop.py:1679–1707, 2106–2149`;`live/beta_overlay.py:257–291`(`leg_active` / `config_fault`) | 三种语义分开:① **显式 off / shadow**(配置有效)或**非外部书锚** ⇒ 在持的腿被**释放**(loop state `m3_overlay_last.released_by`),BTC 回到书的只减通道撤下,HIGH 一次;② **配置损坏**(mode 非法、预算值非法、book.json 读不了)且有在持的腿 ⇒ **冻结**在现持(不平掉、不重算),HIGH;若 BTC 此刻有名字级阻断(止损 / 冷却 / 场所 / 元数据 / 持有退出)则按书的规则处理并页报「无法冻结」;③ 已释放的腿不会因之后的配置损坏被「复活」;从未下过腿 ⇒ 与今天的书相同。loop state 新增 `leg_active`(下过腿、或拒收锚冻结了在持腿)。 |
| 其它 | `live/tests_beta_overlay.py`(新组 [L] [F] [T] + [C] 预算解析 + S4 覆盖 watchdog)、`ops/gate_coverage.py`(范围自述)、`config/book.json`(只改 `_semantics` 文字;`mode` 仍 off,**无**预算键) | 剥离镜像树里 `watchdog.py` 写成实文件(不经符号链接写回仓库)。剥离收据装置改为**按标记派生**被剥离文件集合(含 watchdog.py),并写出全部改动文件的普查。 |

### 8.2 判词(修前红 / 修后绿,原文 + 退出码)
**复审反例原样**(`devices/r10_counterexamples.py`,只按路径加载 `beta_overlay.py` 这个纯模块,其余执行器代码不运行;收据 `receipts/r10/`):
```
R10_COUNTEREXAMPLES label=80ae104 A01=GOES_THROUGH A02=GOES_THROUGH      EXIT=1   (修前: 合计 7.0x NAV、看门狗读 2.0x;冻结时 ex-overlay 净额 -500)
R10_COUNTEREXAMPLES label=b81c4cb A01=DEFENDED A02=DEFENDED              EXIT=0   (修后: 预算 3.0 下腿 +25,000→+5,000、合计 3.0x;预算未设 ⇒ refused budget_unset;净额 0)
```
(`beta_overlay.py` 在 `b81c4cb` 与 `5b3d89c` 逐字节相同,sha256 `a5018f49befbfe2d…`。)
**全电池**:两轮,都经 `ops/run_acceptance_offline.sh`、都在 12Z 锚静默窗内、都先复制实盘 state(`OFFLINE_LEDGER_COPY: checkout 54 days cover all 53 completed production days`;`OFFLINE_KERNEL_PROBE: credential read/write, outside write, network denied`;`/usr/bin/python3` 3.9.6,`ACCEPT_PY=SET:/usr/bin/python3`,`.env=false`):
- `b81c4cb`(13:32Z 起):`ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)` / `OFFLINE_ACCEPTANCE_EXIT: 1`,162/163;唯一的红 `tests_beta_overlay` exit 1:`TESTS_BETA_OVERLAY FAILURES checks=159 failed=2`,即 L9 / L10 —— 新代码与剥离执行器**两边都 0 行 daily_nav**(`(0, 0)`):套件的非 DRY 桩快照缺 daily_nav 写入器读的三个余额字段,写入器的 KeyError 被捕获成「daily_nav row failed」。夹具缺陷,不是执行器改动;`5b3d89c` 只在挂 logger 时给桩快照补这三个键(收据 `receipts/OFFLINE_BATTERY_b81c4cb.log`、`receipts/r10/tests_beta_overlay_b81c4cb_battery.log`)。
- **`5b3d89c`(13:50Z 起,终版)**:**`ACCEPTANCE: ALL GREEN (163/163 suites exit 0)`**,`OFFLINE_ACCEPTANCE_EXIT: 0`,外层 `OFFLINE_EXIT=0`;`tests_beta_overlay`、`tests_guard_calibers`、`tests_watchdog` 均 exit 0(收据 `receipts/OFFLINE_BATTERY_5b3d89c.log`)。新套件判词行:`TESTS_BETA_OVERLAY ALL PASS checks=159 failed=0`(`receipts/r10/tests_beta_overlay_5b3d89c_battery.log`)。

**新套件承重行**(`5b3d89c` 电池内 `tests_beta_overlay` 的逐格日志原文;带 RED 的是修前行为的变异体/剥离对照,在同一输入上必须变红):
```
  OK   ★ L1 stress input, fixture budget 3.0 x NAV 5,000: the leg is SCALED (intent +25,000 → +5,000), the combined target gross is 15,000 = 3.0 x NAV, the cut is the recorded gap and pages HIGH naming the budget — ('applied_via_combined', 5000.0, 15000.0, 0.2)
  OK   ★ L1-RED the pre-fix behaviour (no budget: mutant with an infinite limit) on the SAME input: combined gross 35,000 = 7x NAV — above the 5.0x halt line the old gate never saw (the reviewer's counterexample, reproduced) — 7.0
  OK   ★ L2 budget UNSET under on ⇒ refused (budget_unset): no leg, BTC untouched (unheld ⇒ absent), HIGH '缺失即不做' — never 'no limit' — ('refused', 'budget_unset')
  OK   ★ L5 through run_anchor (NAV 10,000, sizing 2.0x, fixture budget 2.05x): the leg is cut to the 500 U of room, the FINAL target gross is exactly 2.05 x NAV, the BTC order is the cut leg, HIGH names the budget — ('applied_via_combined', -499.99999999999636, 20500.0)
  OK   ★ L6 cond4b on a row the leg shaped (sizing 10,000 / combined 35,000 / NAV 5,000): the gate reads 7.0x and TRIGGERS (halt above 5.0x), stating its numerator — (7.0, True)
  OK   ★ L6-RED the STRIPPED watchdog (today's gate) on the SAME rows reads 2.0x and does not trigger — the blind spot the review found — (2.0, False)
  OK   ★ L7 rows WITHOUT the M3 keys (every row today): the new gate's cond4b detail is byte-identical to the stripped gate's
  OK   ★ L9 the daily_nav ROW (pilot_log, read back): target_gross stays the sizing gross (20,000); base_sizing_gross = 20,000; combined_target_gross = sum|final target| incl. the leg; readback_gross = sum|venue positions| (6,500) — {'target_gross': 20000.0, 'base_sizing_gross': 20000.0, 'combined_target_gross': 21669.018404907976, 'readback_gross': 6500.0}
  OK   ★ L10 mode off: the daily_nav row is byte-identical to the stripped executor's (no M3 key)
  OK   ★ F1 the reviewer's case (book BTC +500 / ETH -500, held BTC 1,500, field missing ⇒ frozen): overlay net = 1,000 (the freeze's increment), the ex-overlay net is 0 — (1000.0, 0.0)
  OK   ★ F1-RED the pre-fix definition (the whole held BTC) on the SAME input leaves a -500 residual (the review's finding)
  OK   ★ F2 venue cap: the overlay net and the chase basis follow the CAPPED BTC target (= hedge_after_cap), not the intent — (-961.2926004815703, -961.2926004815703, -1961.8216336358578)
  OK   ★ T1 broken config (mode 'ON') + an active leg: FROZEN — BTC target = held, NO BTC order, HIGH '配置无效'/'冻结', state keeps the leg active; the overlay net = held - the book's BTC — ('frozen_config_invalid', -1961.8216336358578, 0)
  OK   ★ T1-RED the pre-fix behaviour (a broken config treated as off) on the SAME input SENDS a BTC order (unwinds the leg) — (1, 0)
  OK   ★ T2 explicit off + the same active leg: RELEASED — the book's rules unwind BTC (a reduce-only BTC order), HIGH names the explicit off, state marks released_by=off — (1, 'off')
  OK   ★ T2 explicit shadow + the same active leg: RELEASED — the book's rules unwind BTC (a reduce-only BTC order), HIGH names the explicit shadow, state marks released_by=shadow — (1, 'shadow')
  OK   ★ T4 broken config and NO leg ever placed (no loop state): plans / orders / target are the stripped executor's (only the page differs)
  OK   T5 broken config + active leg + a NAME-level block on BTC (stop cooldown): no freeze — the book's rules handle BTC, HIGH says so — ('config_invalid_suspended', 0.0)
```
另:剥离收据装置改为按标记派生文件集合后,在全新克隆(`b66257b` + 补丁)上 `M3_STRIP_RECEIPT VERDICT=IDENTICAL base=b66257b live/binance_executor.py=== live/external_book.py=== live/watchdog.py=== scheduler/anchor_loop.py===`;负对照:在克隆的 watchdog.py 末尾加一行非 M3 注释 ⇒ `VERDICT=DIFFERENT … live/watchdog.py=!=`,exit 1,复原后 IDENTICAL。

### 8.3 杠杆预算表(交用户裁定「对冲是否占用 2× 预算」;`devices/leverage_budget_table.py`,数字从 `b81c4cb` 的 config / watchdog 源码读出,收据 `receipts/r10/LEVERAGE_BUDGET_TABLE_b81c4cb.json`)
现行政策:`target_leverage` 2.0(外部书 `gross_mult` 2.0);cond4b 报警 > 3.0×、停机 > 5.0×(1.5 / 2.5 倍)。假设腿**增加** gross(书内 BTC 分量约 0.2% gross)。

| 对冲 (×NAV) | 合计杠杆 | 今天的门读到 | 修后的门:报警? / 停机? | 预算 = 未设 / 2.0 / 2.2 / 2.3 / 2.5 / 3.0 / 5.0 时实下的腿 (×NAV) |
|---|---|---|---|---|
| 0.1 | 2.1× | 2.0×(永不报) | 否 / 否 | 0 / 0 / 0.1 / 0.1 / 0.1 / 0.1 / 0.1 |
| 0.2 | 2.2× | 2.0× | 否 / 否 | 0 / 0 / 0.2 / 0.2 / 0.2 / 0.2 / 0.2 |
| 0.3 | 2.3× | 2.0× | 否 / 否 | 0 / 0 / 0.2 / 0.3 / 0.3 / 0.3 / 0.3 |
| 0.38(预注册 2026 事前 β −0.19 gross × 2) | 2.38× | 2.0× | 否 / 否 | 0 / 0 / 0.2 / 0.3 / 0.38 / 0.38 / 0.38 |
| 1.0 | 3.0× | 2.0× | 否(恰在线上)/ 否 | 0 / 0 / 0.2 / 0.3 / 0.5 / 1 / 1 |
| 5.0(复审的合法压力输入) | 7.0× | 2.0× | **报警 / 停机** | 0 / 0 / 0.2 / 0.3 / 0.5 / 1 / 3 |

读法:在现行报警 / 停机线下,+0.1 / +0.2 / +0.3 NAV 的对冲**都不触线**(修前修后都一样);修前的问题是极端合法输入(7×)门看不见,修后门看得见并停机,且预算在下单前截断。可选的政策:
- **预算未设(现状)**:on 也不下腿(`budget_unset`)。
- **预算 = 2.0(字面「占用 2× 预算」且不改书)**:书已占满 2.0 ⇒ 腿恒为 0,等于不开。若要「占用」且真的下腿,需要**先缩书**让出空间 —— 那是新的动作规格(sizer 改动),本包没有实现,需预注册。
- **预算 ∈ (2.0, 3.0]**:腿在书之外、上限低于报警线;2.3–2.5 覆盖预注册的 2026 事前量级。
- **预算 = 3.0(报警线)/ 5.0(停机线)**:只挡极端输入;5.0 时压力输入被截到恰好 5.0×(cond4b 用 `>`,不停机)。

### 8.4 β 平价(R10 A.4-5;生产 f16 裁剪缓存 vs 评估认证原始价格表)
(`beta_parity/`;独立执行代理完成,我核过收据自检 `failed: []`、上游 S1/S2 自检均空、每锚 450 名 = BTC + 宇宙。复跑 `beta_parity/RUN_COMMANDS.sh`;评估侧在 pod2 用认证原始价格表 `price_full_raw_x0918r`(sha 钉 `23af32bd…` / meta `d1e49cc9…`)跑 `m2_lib.betas_at`;生产侧在本机用生产者 `compute()` 跑滚动缓存**副本**(sha `73018d36…`,13:20Z 复制;`~/wide_shadow` 只读))
- **锚**:33 个(2026-09-13T16Z … 09-19T00Z;生产缓存完整覆盖 180 根 bar 且认证表覆盖;每锚 target_live 文件 sha 与旁车一致)。
- **β_i 差(生产 − 评估)**:33 锚 × 449 名 = 14,817 对,中位 −2e-15、p5/p95 ±1.6e-14、**max |Δβ| = 0.0663(AINUSDT,09-19T00Z)**;|Δβ| > 0.05 共 10 对、> 0.1 为 0。|Δβ| > 1e-9 的只有 7 个名字(AIN、AKE、BULLA、LSK、TAC、VELVET、WOO),其余全部名字差 ≤ 4.5e-14。
- **机制**:差异**全部**来自缓存的 ±0.30/5 分钟裁剪 —— 窗口里 12 个 5 分钟格被截在 ±0.300049(float16 的 ±0.30),恰是认证表里 5 分钟涨跌超过 30% 的 12 格(原始 0.3006–0.558)。float16 本身不贡献差:认证原始表也由 float16 的 5 分钟缓存构建,不含裁剪格的 4h bar 两边相差 ≤ 7.9e-15 —— 所以**这次比较只隔离了裁剪,没有检验 float16 对真实成交价的误差**。
- **回落人口**:两边**零**差异(每名每锚 180/180 有效 bar,有效性掩码 95,400 格全等;认证表在这些窗口里无 UA / 补缺格)。
- **β_exec 差**(按该锚发布权重、Σ|w|=1):Δβ_exec = +0.00038 … +0.00111(相对 ≤ 0.89%;按执行器 reshape 的近似 ≤ 1.84%),**生产会比评估少对冲一点**;全部来自 6 个有权重的裁剪名。
- **最终 BTC 手数差**:G = 10,000 USDT 时 |Δ| ≤ 0.14 手(0.001 BTC/手),**从不超过 1 手**;只在跨取整边界时差 1 手(发布权重、向零截断:G=10k 6/33 锚、G=20k 7/33 锚)。
- **未验证**:33 锚里 10 个(09-17T12Z 起)有按锚归档的缓存快照,与副本逐格相同、`compute()` 输出逐字节相同;其余 23 个无归档,依据是 shadow_loop_v3 只填空行不改已填行。这些 target_live 文件都不带 `beta_overlay` 字段(生产者尚未装),生产 β 是 `compute()` 会写的值。

### 8.5 限制(如实)
- 非外部书锚的「释放」没有经 `run_anchor` 实跑(内部书锚需要 DL preds 路径),代码与显式 off 同一分支;套件范围自述里写明。
- 预算的**数值**在套件里是夹具(3.0、2.05);生产值未设。
- cond4b 的 `readback_gross` 取自 daily_nav 那一次账户读取(锚末);锚内成交过程中的瞬时杠杆不在任何门里(与今天相同)。
- 本节之前的定向 / 读文本套件装置(`run_targeted*.sh`、`disk_mode_sweep*.sh`、`run_c5_textual.sh`)是在沙箱外单独跑执行器套件,**按 E-0923-D 已不许再这样跑**,只作历史记录;本节全部套件判词都来自离线全电池。
- 冻结语义依赖 loop state 的 `m3_overlay_last`;state 文件本身丢失时,配置损坏按「从未下过腿」处理(与今天的 off 相同,会经书的规则撤腿),HIGH 页报仍在。
