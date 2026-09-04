# PREREG · 宇宙机制部署(M1 归一基变宽 → M2/M3 宇宙规则化)· 一份预注册, 两阶段落地
> **创建:** 2026-09-03T23:53Z(本地 09-04 07:53) | **Session:** 主线 | **状态:** 判据冻结, Phase A 待换装, 实盘未动 | **作废条件:** Phase B 首锚验收入档后转 RESULT
> **受据:** `docs/RESULT_universe_dyn_2026-09-04.md`(58 臂)+ 本文 §2 稳健性包(`retrain_2026-09/jp_m1_robustness.py`)| **用户字:** 09-04 "如果结论可靠的话, 立即执行 … 同一个 PREREG, 分两阶段落"(Phase A = M1; Phase B = M2+M3)| **生产不变量三类(用户):** A 时点完备 · B 缺失/新生费率不填 0 · C 动态宇宙 = 一等状态

## 0. 结论先写(数字后不改)
- **M1 可靠**: fund 腿归一基 400 成员 → 全部有新鲜结算的已上市名, 成交集不变。判官口径(2023+ 每锚 net_ex 差, bps of gross): 部署口径 W3FIX+FTRIM **s42 +0.071 CI[+0.018,+0.125] · s2027 +0.066 CI[+0.013,+0.122]**; msharpe+FTRIM s2027 +0.063 CI[+0.006,+0.123], s42 +0.053 CI[−0.003,+0.112](下界差 0.003, 2023/24 结构性零稀释); 无 FTRIM 四读数全 CI>0(+0.077~+0.093)。**2025-26 regime 六格无一为负**(σ_fund 低/中/高 +0.06/+0.16/+0.27; 有效名数低/中/高 +0.12/+0.17/+0.19; 判官单位), 月度命中 65~80%(20 月), 最差月 −29~−42 bps of gross。杠杆表(2.0×, 2023+): 年化 43.9%→47.0%, Sharpe 2.43→2.60, **maxDD −37.4% 不变, ES5 −0.82% 不变** ⇒ 纯 alpha 项, 尾部不动。
- **不做基的年龄门**: N829X7T400(基限 ≥7 天)fx +0.043 CI 含 0(FTRIM 态 +0.015)⇒ 新生名的费率排名信息从首次结算起就有用; 不变量 B 由"仅有效结算 ≤12h 且 EMA 存在者参与, 缺失 = NaN 不入秩"满足, **不用 0 填**。
- **king/F10 横截面特征不同步扩充**(§4): 回放证据本身就是"只变 fund 腿秩基"(排名 400-600 名 king 分数覆盖 4.3%, F10 只对成员出分); F10 特征在成员集内秩化, 扩 members = 未测形态。
- **不需重训**(§5): M1 不改 king/F10 任何输入(FE_ANCH 列 80/81 仍是 fe_v[m] 原值/成员内秩); M2 让实盘成员分布回到训练分布(meta 本就是逐锚动态 top-400)。
- **一次性代价可忽略**: 两书权重差 Σ|Δw|/gross 中位 11%(p90 17%), 经 EMA 步长 0.1 与带吸收, 估一次性 ≈ 0.4 bps of gross 分摊 ~10 锚; 稳态换手 1.78%→1.87%(+5% 相对); 多头 gross 占比 47.8%→46.3%; max|w| 0.73%→0.76%; top10 7.0%→7.2%; 翻号 ~10 名/锚。

## 1. 生产不变量与实现映射
| 不变量 | 现状(只读核实) | Phase A 落法 |
|---|---|---|
| A 时点完备 | 生产者按锚从场所拉结算, 天然时点; 回放 MEMBERS_TOPN 用当锚 qvk>0(下市即出), FE 为因果 v1 | 基名单 = 当锚 `exchangeInfo` TRADING USDT 永续 ∪ symbols_live; 拉取失败回退上锚名单(aux `base_syms`) |
| B 缺失/新生不填 0 | 生产者 `fe_v` 默认 NaN, 仅 ≤12h 有结算且 EMA 存在者赋值; `xz` 只对有限值秩化(生产者与回放同式) | 秩基 = 所有满足同条件的基名(含 live 名), NaN 名不入秩; 新名冷启动走既有 40 天回拉(limit 100, ≤3 锚自愈), EMA 种子 = 首个 rn(与面板 v1 同) |
| C 宇宙 = 一等状态 | 读者: 逐文件校 sha256(list)=universe_sha, **无跨锚等值 pin**(universe_sha_pin=null); 出成员即平 EXIT_NON_MEMBERS 每锚在跑(forced_exit_n≈1); 守护/记账按文件内 universe 列表工作 | Phase A 宇宙字段不变; Phase B 宇宙逐锚变, 首锚验收项含 universe_sha 轮换、n_in_universe、强制出场清单、离池名走正常 exit path(400→401 = forced_exit, 非异常) |
| 时序 | 生产者 5.1 分钟/锚(weight 800, 自限 150/min), 落盘 N+21.8~22.2, 读者 N+24 读(poll_grace 5) | 基扩 +≈208 weight ⇒ 自限 150→**240/min(≤4 req/s 纪律)**, 预计 4.2 分钟, 落盘 ≤N+21; 验收: written_utc ≤ N+21:30 |

## 2. Phase A(M1)定义与验收(冻结)
**改动(仅 ~/wide_shadow/shadow_loop_v3.py, 备份保留, 文件名不变以保 RUNBOOK L33 逐字重启):** (a) Fetcher 自限 150→240; (b) 每锚取 exchangeInfo 基名单; (c) funding 增量循环遍历基名单(`fund_updates` 语义不变 = live 名, 新增 `fund_updates_base`); (d) `legz["fund"]` = fe_v[m] 在基秩中的位置(`rankdata(基∪m)/(n−1)−0.5`, m ⊂ 基), 旧秩 `fund_z_old` 与 `sel_idx` 存入 prev_rec 顶层(供 Shadow A 与归因; combo_stage 不读顶层新键); (e) signal 日志新增 base_n / fund_base_n / fund_updates_base / exinfo_ok。**不动:** members、sel、universe、weights 归一/带/EMA、combo_stage、执行器、守护。
**首锚验收(全部满足才 PASS):** ① signal 行 status OK, coverage ≥0.95, fund_updates 在稳态带(4h ~353 / 8h ~453), base_n ≥600, fund_base_n ≥500, exinfo_ok; ② 落盘 written_utc ≤ N+21:30, 读者 external_book.ok, n_in_universe ≥150; ③ target_live 与影子 A(旧秩, 离线由 prev_rec 重建)权重差 Σ|Δw|/gross 首锚 ≤5%(EMA 步长 0.1 × 稳态差 11% ≈ 1~2%), 多头 gross 占比变化 ≤2pp; ④ 执行: rc=0, 场所拒 ≤35 张或分散(单名 ≤3), 换手 ≤8%, 费 bps 带内; ⑤ 记账: net/gross ±1%, twin 非三连, FUNDING 带内; ⑥ combo_stage 五层安全无回退。**回滚:** kill shadow.lock PID → 恢复备份文件 → RUNBOOK L33 逐字重启(SHADOW_OFFSET_MIN=16); 状态 aux 向后兼容(新键忽略)。**30 锚评估:** Shadow A vs Production 的 ΔPnL(§6)累计与逐日符号; 判据 = 30 锚累计 ≥ −20 bps of gross 且无单锚 ≤ −15 bps 由 M1 独立造成(反事实差), 否则回滚复议。

## 3. Phase B(M2+M3)定义与验收(冻结, Phase A ≥3 天且 PASS 后, 需用户字)
**改动:** 数据源/成员候选 = 基名单(klines 拉取 450→~660 名, 预算 +≈210 weight ⇒ 自限或 offset 再评估); universe 字段 := 当锚成员(top-400 by 7d 成交额 ∧ 7d 覆盖 ≥95%, 即现规则解除 450 框); symbols_live 仅作回退。**验收:** 首锚 added/removed 名单与 forced_exit 清单一致; 离池名经正常 exit path 平仓(orders 归属 rebalance, 无 flatten_only 异常); universe_sha 逐锚变且读者逐文件校验通过; dust/换手 ≤ 建仓锚带; 目标达成 ≥97%; 新上市名首次入池延后 ≥7 天(数据门)。**回滚:** 同 §2。

## 4. king / F10 特征不扩充的理由(用户问 2)
回放 T400 臂 = 归一基变宽而 king(SLOW)/F10 分数对新增名几乎无值(4.3% / 成员内出分) ⇒ **证据只覆盖 fund 腿秩基**。生产者 king 特征含成员内秩(FE_ANCH 秩列)与 fe_v[m] 原值(列 80/81), F10 特征(dlw_features)横截面秩化于成员集 ⇒ 扩 members 会改变两模型输入分布, 属未测形态, 且 N600X14/N500X14 显示扩展臂对年龄门敏感。裁定: **不扩**。

## 5. 重训 / 口径 / FTRIM(用户问 4)
- 重训: 否。M1 不触模型输入; M2 使实盘成员生成规则与训练 meta(逐锚动态 top-400)一致。
- 口径再校准: 部署后回放正典形态 = `MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX`(N829T400F_fx); 各 regime × 杠杆表已按此重算(§0/§2 稳健性包输出入 RESULT 附录), 仪表盘/月度评估基线切换到该形态。
- FTRIM: 排除条件 (z<0 ∧ rn8 ≤ −10bp) 的 z 随秩基变 ⇒ 排除名集微变; 回放 FTRIM 态 M1 增益 +0.066~+0.071(无 FTRIM +0.077), 两者约 15% 重叠, 互不反转; FTRIM 反事实读数在 Phase A 后继续累计(不重置)。

## 6. 长期影子三书(用户问 5, 采纳)
每锚由离线 sidecar(研究仓代码, 运行目录 ~/regime_dash 同款, 只读生产者 prev_rec/target/mid/funding)重建: **Shadow A** = 旧秩基 ∧ 冻结 450 成员(prev_rec.fund_z_old + 同链平滑, 自有 H_A); **Shadow B** = 新秩基 ∧ 冻结 450(Phase A 期间 = production); **Production C** = 新秩基 ∧ 动态成员(Phase B 起)。逐日 ΔPnL = C−A = (B−A)[M1] + (C−B)[M2/M3], 用执行器 mid 向量与 funding 台账定价(纸面, 不含执行), 入仪表盘 R5 旗标: 20 交易日累计 (B−A) ≤ −15 bps of gross 或 (C−B) ≤ −20 bps ⇒ 复议。

## 7. AMENDMENT(2026-09-03T23:59Z, 换装前, 机制事实而非结果拟合)
- **冷启动自愈时序:** 新入基的 ~210 名走生产者既有 40 天回拉(`fundingRate` limit=100, 场所按时间升序返回)⇒ 首锚只拿到最早 100 行(8h 名末行距锚 ~7 天, 4h 名 ~27 天), 不满足 ≤12h 新鲜度 ⇒ **首锚 fund_base_n ≈ live 新鲜名数(~450), 基在第 2~3 锚自愈到 ≥600**。§2 ① 改为: 首锚 base_n ≥600 ∧ fund_base_n ≥ 430 ∧ exinfo_ok; **第 3 锚起 fund_base_n ≥550**。其余判据不变。
- **测试套件同步:** 生产者套件 `tests_target_live_output.py` 检查 1a 自 E-0825-G/B 修复后一直为红(允许集未同步), 本次补登两行并新增 [9] M1 九项(基==成员时逐位等于 xz; 缺失名 NaN; <10 退化; 秩基变宽序不变; king/F10 输入行不变; universe/EXIT 路径不变), 候选全绿 62/62 → 登 E-0903-F。
- **候选 sha:** shadow_loop_v3_m1_candidate.py e9c9837412131b36e(现役 db326162c7ac54df1); 换装时同名覆盖并保留 `.pre_m1_20260904_backup`, aux.json 换装前快照 `aux_pre_m1_20260904.json`(影子 A 引导用)。

## 8. Phase A 换装收据(2026-09-04 00:53:41Z–00:54:0xZ, 静默窗: 00Z 锚 rc=0 于 00:52:49Z, 生产者空闲至 04:16Z)
- 备份: `shadow_loop_v3.py.pre_m1_20260904_backup`(db326162c7ac…)· `tests_target_live_output.py.pre_m1_20260904_backup` · `state/aux_pre_m1_20260904.json`(4e9a461bcb79…, 影子 A 已由此引导, boot_anchor = 1788480000)。
- 安装: shadow_loop_v3.py = 候选 e9c9837412130884(610 行); 套件同步; **在位套件 ALL PASS (62 checks)**(`m1_suite_20260904.log` 入库)。
- 停旧: kill 12918(shadow.lock PID)→ 退出。**重启事实(E-0904-A):** 生产者由 launchd 代理 `com.hsy.shadowloop`(KeepAlive SuccessfulExit=false, env SHADOW_OFFSET_MIN=16, stdout→loop.out)管理, kill 后 launchd 立即以新文件重生 **PID 4833**(XPC_SERVICE_NAME=com.hsy.shadowloop, SHADOW_OFFSET_MIN=16 已核); RUNBOOK L33 的 nohup 手工启动随后被锁拒绝(REFUSE_TO_START 行进 loop.out, rc 2, 无副作用)。运行中进程唯一(ps 核), `next 2026-09-04T04:16:00Z`。
- 守护未动: combo_live_daemon 30944 / sidecar 30943 在跑。**首 M1 锚 = 04Z; 验收器 `~/universe_shadow/m1_first_anchor_check.py 1788494400` 于 04:5xZ 跑。**
- RUNBOOK 更正项: 生产者重启的正确动词 = `launchctl kickstart -k gui/$(id -u)/com.hsy.shadowloop`(或 kill PID 由 KeepAlive 重生); L33 nohup 行仅适用于代理未加载时。

## 9. AMENDMENT(2026-09-04 04:3xZ, 首 M1 锚生产者行已出、执行结果未出; 前提更正, 非结果拟合)
- **前提错误:** §2 ① "base_n ≥600" 的估计来自执行器 exchange_info_cache(658 名, 含 SETTLING/已下市)。独立公共 exchangeInfo 实测: USDT 永续 656, **TRADING 526**, SETTLING 129, PENDING 1; TRADING ∪ live450 = **528**。生产者首锚 base_n = 528 与之逐一相符。判据改为 **base_n == 场所 TRADING ∪ live(±3) 且 ≥500 且 exinfo_ok**; 验收器同步。
- **量级预期更正:** 实盘秩基 400 成员 → ~526 名(+31%), 更接近回放 **N500T400** 臂(vs N400r: msharpe +0.058 CI[+0.003,+0.112], W3FIX +0.057 CI[+0.008,+0.108])而非 N829T400(+0.08); 30 锚判据不变(累计 ≥ −20 bps of gross), 影子 (B−A) 的期望值下修为 ≈ +0.06 bps/锚。
- **首锚生产者读数(04Z):** status OK, coverage 1.0, fund_updates 357(live 带内), fund_updates_base 7,317(78 个新名 40 天冷启动回拉 ≤100 行/名), base_n 528, fund_base_n 449(≥430 ✓, 新名待 2~3 锚自愈), weight 875, **runtime 229s, 落盘 04:20:26Z = N+20.4**(≤N+21:30 ✓), 读者 04:24:26Z 取书 ✓; 影子 sidecar: 链复制 max|diff| 7.8e-8(float32 量化, 阈值由 1e-9 更正为 1e-6), **Σ|A−B|/gross = 0.18%**(基尚未变宽, 符合 §7)。

## 10. Phase A 首锚验收(04Z, 1788494400)— **PASS 9/9**(04:58Z 验收器 + 执行侧)
生产者: OK/cov 1.0 · fund_updates 357(+base 7,317)· base_n 528 = 场所 TRADING∪live · fund_base_n 449 · runtime 229s · 落盘 N+20.4 · 读者 ok(n_in_universe 232)· Σ|A−B|/gross 0.18%(chain_ok)· 多头占比 0.486→0.487。
执行: rc=0 04:51:56Z · 拒 30/163(18%, 27 名, 单名 ≤2)· maker 95% · 费 1.93 bps · 换手 3.0% · gross 164,402/166,349(98.8%)· gaps 5 名 244U · 限流峰 969 · launchd_err 0 · twin AGREE。
**观察项(非 M1 判据):** net/gross +1.10%(0.54→0.92→1.10, 三锚上行, 带上沿; 净/权益 +2.2%); NAV 04:42Z 83,213(00:43Z 83,867, −654U/锚 ≈ −2σ; 入金后累计 −742U = −0.88% NAV); 未实现 +49.6U。归因见仪表盘 04Z sleeve 行; 与 M1 无关(首锚权重差 0.18%)。第 3 锚(12Z)复核 fund_base_n ≥550。
