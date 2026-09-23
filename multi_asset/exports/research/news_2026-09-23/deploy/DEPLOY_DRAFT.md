> **创建:** 2026-09-23 | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(NEW_S 执行代理,受 lead 派) | **状态:** 手册 —— **未执行**;仅在判词 SWAP 且用户确认后由操作者执行 | **作废条件:** 生产者源码(shadow_loop_v3.py 6080073b / combo_stage.py fb5a9407 / dlw_features.py 29ae6a98 / f8_higher_order_features.py 2c500c7a)、bundle(config.json 3a8422f3 / MANIFEST af61d597)、执行器运行树(b66257b)或本文列出的任一部署文件 sha 改变

# 部署手册:NEW_S(King 年折 + F10 s42 月折,生产者现行特征代码训练)换装

相关:预注册 `docs/PREREG_new_servable_models_2026-09-23.md`(db0123df7)+ 修订 1 `docs/AMENDMENT_1_new_servable_models_2026-09-23.md`(63ca0d0bb);结果 `docs/RESULT_new_servable_models_2026-09-23.md`;部署文件与脚本 `multi_asset/exports/research/news_2026-09-23/deploy/`。

## 0. 总览(两个窗口,顺序不可换;两个窗口都须用户确认)

| 阶段 | 做什么 | 书行为变化 | 门 |
|---|---|---|---|
| A(窗口 1) | 拉取名单 450→522;72 名 40 天 5m 回填(先写隔离副本、验收、再装入);**模型与 EMA 状态都不动** | 旧模型在新名单上选成员(每锚约 23–41 名不同) | 回填验收;下一锚 A* 逐位平价(§A6)通过才进 B |
| B(窗口 2,即换装本身) | 资金费 EMA 状态重播种;换 King / F10 模型文件与 MANIFEST;席位历史播种(需用户字);执行器 `booster_sha_pin` / `f10_sha_pin` 同步 | 换模型 + 资金费状态 | 首锚验收(§B6) |

生产者特征代码**零改动**(四个源码文件不动);改的只有 bundle 配置 / 模型文件 / 状态文件 / 执行器两个钉。执行器任何套件一律经 `ops/run_acceptance_offline.sh`(E-0923-D;`safe_commit.sh` 已在离线沙箱跑全电池,本手册没有「单独复跑某套件」的步骤)。

## A. 窗口 1(静默窗 [N+1:00, N+3:40],N ∈ {0,4,8,12,16,20} UTC;须用户确认)

A0 停服务(只停生产者与 combo 写者;执行器、页报、看门狗不动):
```
launchctl list | egrep 'com.hsy.(shadowloop|combolive)'
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hsy.shadowloop.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist
ps aux | egrep 'shadow_loop_v3|combo_stage' | grep -v egrep        # 必须为空
ps -p $(cat ~/wide_shadow/shadow.lock) || echo "lock PID not alive (ok)"
```
A0b 备份(带 sha):`mkdir <BK> && cp -p ~/wide_shadow/state/{rolling.npz,aux.json,leg_returns_live.json,generation.json} ~/wide_shadow/shadow_bundle/{config.json,MANIFEST.json,slow2026.txt} ~/wide_shadow/fea171/f10_live_s42_np.npz <BK>/ && (cd <BK> && shasum -a 256 * > SHA256SUMS)`。

A1 拉取名单(数据层,不动特征代码):`~/wide_shadow/venv/bin/python news_prod_files.py fetchlist added_names.json <BK>/A1` —— `shadow_bundle/config.json` 的 `symbols_live` 由 450 名(顺序不变)后接 72 名(字母序),其余键不变(脚本断言);`MANIFEST.json` 的 `config.json` sha 同步;旧→新 sha 由脚本打印并写入 `<BK>/A1/BACKUP_MANIFEST.json`。

A2 回填 72 名 40 天 5m(**调交易所 fapi,与实盘共用每 IP 权重,E-0919-V;执行前把命令原文与预计请求数发给 lead**):
```
cd <deploy_dir> && python3 ~/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py --json   # 退出码 0 才继续
~/wide_shadow/venv/bin/python news_backfill.py fetch added_names.json parity_cache_slice.npz parity_holes_slice.npz <BK>/A2
```
- 预计:`/fapi/v1/klines` 5m limit 1000(权重 5),72 名 × 12 次 = 864 次 ≈ 4,320 权重;限速 300 权重/分钟(已发布上限 2400 的 12.5%,硬上限 50% = 1200 含本 IP 全部客户端),约 15 分钟。开始前 `require_quiet_window(剩余 ≥ 25 分钟)`,每次请求前 `wait_for_quiet_window`;逐请求与逐分钟记录本 IP 用量 `X-MBX-USED-WEIGHT-1M`(即含实盘的外部权重)到 `<BK>/A2/requests.log`;>600 暂停到下一分钟,>1200 立即中止。
- **只写隔离副本** `<BK>/A2/isolated_state/`(rolling.npz / aux.json / generation.json),`~/wide_shadow` 不动。通道由 `shadow_loop_v3.bars_to_channels` + `clipch`(生产文件编译,sha 断言)算,ret5 逐根链接,只填 NaN 行,f16,`prev_close` 置最后一根收盘。
- 验收(全过才写隔离副本,否则 exit 3):①每名首根之后无缺行(缺口具名);② ≤2026-09-19T00Z 的行与研究缓存 x0918r 在非补洞格上 7 通道逐位相等(同一检查对在役 450 名实测 0 格不同);③其余 757 列逐字节不变。
- 备选数据源:`data.binance.vision` 日归档不走 fapi 权重(完整日),当日未归档部分仍须 fapi;若采用,须同样过验收 ②。

A3 装入(**部署动作,用户确认后**;生产者仍停着;A2 的 fetch 必须是在本次停机后取的,否则脚本拒绝):`news_backfill.py install added_names.json <BK>/A2`(核生产状态自 fetch 起未前进,把 72 列与 prev_close 写入 `~/wide_shadow/state`,重签 generation)。

A4 重启:`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.shadowloop.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist`;核 `ps eww -p <新pid>` 含 `SHADOW_OFFSET_MIN=12`、`tail -2 ~/wide_shadow/loop.out` 出现 `next <下一槽>`。

A5 首锚 A* 运行后:`shadow_log.jsonl` 最后一条 `signal` 的 `members`=400、`fetched`=522、`missing`=0;`combo_live_status.json` ok;执行器照常(旧钉)。

A6 **逐位平价门(换模型前,只读)**:`combosnap` 归档 `state/snap/A*/` 后,下一个静默窗跑 `mac_p5_parity.py --live A*`:同一生产代码、同一输入(快照的滚动缓存、账本与**在役** EMA 状态,两侧相同),训练规则一侧的候选 = SPEC 合法函数(已在 9 个历史锚上与 x0918r 掩码 0 名不同)∧ 加密币类;门 = 成员集相等、X78 / X82 / X89 逐位相等,且 King `legz` 用在役 booster 重算与 `prev_rec` 逐位相等(证明重算 = 生产实算)。任何不等 ⇒ 不进入 B,按 §R-A 回滚。

## B. 窗口 2(A6 通过后的静默窗;即换装本身,须用户确认)

B0 同 A0 停服务并备份(带 sha)。

B1 资金费 EMA 重播种(改生产者状态,资金费腿是书的主体 ⇒ 只在本窗口与换模型一起做):
```
~/wide_shadow/venv/bin/python news_ema_reseed.py fund_replay_tail.npz <BK>/B1            # 先干跑:逐名前后差值表 <BK>/B1/EMA_RESEED_REPORT.json
~/wide_shadow/venv/bin/python news_ema_reseed.py fund_replay_tail.npz <BK>/B1 --write    # 确认后写入
```
- 从训练回放在 2026-09-19T00Z 的状态出发,用生产者自己的 EMA 更新行(L472–L480 编译)把生产账本其后的每条结算按序推进;每条推断间隔须等于账本存值,否则拒绝。829 轴外名(DOS/MARSCOIN/PONS)保持原值。
- 逐名前后差值表 = `EMA_RESEED_REPORT.json` 的 `applied`(old_acc / new_acc / rel_change);09-23 08Z 只读干跑:522 名可推进、0 拒绝;相对变化中位 2.6e-11、p99 8.3e-6、最大 0.45%。
- 回滚 = 用 B0 备份的 `aux.json` 覆盖并重签 generation。

B2 模型文件:`news_prod_files.py models slow2026.txt f10_live_s42_np.npz <BK>/B2` —— 替换 `shadow_bundle/slow2026.txt`(NEW_S King 2026 折)与 `fea171/f10_live_s42_np.npz`(NEW_S F10 s42 202609 折 numpy 导出),MANIFEST 同步;脚本打印的两个钉须与 §C 表一致。

B3 席位历史播种(**书行为,需用户字**;不做则席位 w3 在约 900 锚 ≈ 150 天内仍由旧 King 腿收益决定,部署的书 ≠ 评估的书):`state/leg_returns_live.json` 三条腿写入 NEW_S 腿收益序列(`legs.npz` LR 截至 2026-09-19T00Z 的最后 950 条),重签 generation。kc/fc 两条链状态从在役状态热启动,按 α=0.1 收敛(半衰期约 6.6 锚),属预期转换期,单列报告。

B4 执行器钉(现行协议 `executor_deploy_protocol_isolated_checkout_2026_09_23`):隔离 main 检出 → 复制实盘 state → 改 `config/book.json` `external_book.booster_sha_pin` / `f10_sha_pin`(新值 §C)→ `bash ops/safe_commit.sh "<msg>" config/book.json`(离线沙箱全电池约 17 分钟,须在静默窗)→ 推 main → 静默窗内持 `state/anchor.lock` 对运行树 `fetch` + `merge --ff-only <sha>`,核三方 sha 与代码区干净。**B1–B4 必须落在同一对锚之间**(执行器读取 N+24 之后、下一锚生产者 N+4h+12 之前),否则执行器对钉不符的目标 HOLD。

B5 重启(同 A4)。

B6 首锚验收:`target_live/<A>.json` 的 `booster_sha` = 新 King 钉、`f10_sha` = 新 F10 钉;执行器读者判词 ok(非 `REFUSED f10_pin` / booster);`combo_live_status.json` ok、`n_f10_scored` ≥ 380、gross ∈ [0.4, 1.2];aux `ema` 对 B1 写入值按生产更新继续推进(逐名核对 = 用 B1 同一装置从 09-19 状态重算到该锚逐位相等);离线 `mac_p5_parity.py --live <A>` 以新模型重算,成员 / 特征 / 分数 / combo 目标逐位相等(F10 分数为本机 numpy 推理两侧同源)。

## R. 回滚(均为正向操作,不强推)

- R-A(阶段 A 后):停服务 → 恢复 `<BK>` 的 config.json / MANIFEST.json → `news_backfill.py rollback added_names.json <BK>/RA`(72 列整列置 NaN、删其 prev_close、重签 generation;不能用旧 rolling.npz 覆盖:会丢掉其后的 bar)→ 重启。
- R-B(阶段 B 后):停服务 → 恢复 B0 备份的 slow2026.txt / f10 npz / MANIFEST / aux.json(EMA)/ leg_returns_live.json 并重签 generation → 执行器以正向提交恢复旧钉(`8d79186b…` / `351ae26b…`)走同一协议 → 重启。

## M. 拉取名单的维护(候选池会漂移)

- 训练规则的候选池 ⊆ 829 名轴 ∩ 加密币类 ∩ 当时可交易。829 名轴固定 ⇒ 部署后池只会因下架缩小、极少因复牌扩大;新上市币不在轴内,训练与服务都不会选。
- 每月一次(建议与月度重训同日、静默窗内):一次 `GET /fapi/v1/exchangeInfo`(权重 1)取 TRADING 的 USDT 永续,∩ 829 轴 ∩ 加密币类(冻结规则)−拉取名单 ⇒ 必须为空;不空则按 A1/A2 追加并回填。829 轴扩容属另一项目,扩容时同步扩名单。
- 已知残余(本轮接受,下一轮改特征代码时修):生产者成员筛没有合法掩码 ⇒ 名单内「已不可交易但仍有冻结行」的名可能被选入(2025-07→2026-09 约 4% 的锚差 1 名,9 月 0)。

## C. 部署文件与钉(sha256)

(判词 SWAP 后由 P5 导出填写)
