> **创建:** 2026-09-23 | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(NEW_S 执行代理,受 lead 派) | **状态:** 手册 —— **未执行**;只在判词 SWAP、候选包验收 ACCEPT 且用户确认后由操作者执行 | **作废条件:** 生产者源码(shadow_loop_v3.py 6080073b / combo_stage.py fb5a9407 / dlw_features.py 29ae6a98 / f8_higher_order_features.py 2c500c7a)、bundle(config.json 3a8422f3 / MANIFEST af61d597)、执行器运行树(b66257b)、生产者补丁(ed11d731)或候选包 manifest 改变

# 部署手册:候选包换装(NEW_S 或 FRESH;候选包作为参数)

相关:预注册 `docs/PREREG_new_servable_models_2026-09-23.md`(db0123df7)+ 修订 1(63ca0d0bb)+ 修订 2(f24467c5d);结果 `docs/RESULT_new_servable_models_2026-09-23.md`;工具与门收据 `multi_asset/exports/research/news_2026-09-23/deploy/`。

## 0. 候选包(参数,不在手册里硬写)

候选包 = 一个目录 `<PKG>`,内含 `slow2026.txt`(King)、`f10_live_s42_np.npz`(F10,生产 numpy 格式)与 `P5_DEPLOY_MANIFEST.json`(`news_export_models.py` 写出:把这两个文件与评估所用的特征 / King / 腿 / F10 / 组合 / 适配 / 配置 / 统计逐环 sha 绑在一起,任一环不符即拒绝导出)。换装前必须同时满足:
1. manifest `VERDICT = BOUND`,`deploy.V1_gate.PASS = true`;
2. 候选包验收 `mac_candidate_acceptance.py`(R10-B02)对**同一** `<PKG>` 出 `VERDICT=ACCEPT`,退出码 0;
3. 判词为 SWAP,用户确认。
执行器两个钉 = manifest `deploy.executor_pins`(`booster_sha_pin` = slow2026.txt 的 sha256,`f10_sha_pin` = f10 npz 字节的 sha256)。NEW_S 与 FRESH 用同一手册,只换 `<PKG>`;若 FRESH 胜出而 NEW_S 未部署,只部署一次 FRESH。

## 1. 总览(两个窗口,顺序不可换;两个窗口都须用户确认)

| 阶段 | 做什么 | 书行为变化 | 门 |
|---|---|---|---|
| A(窗口 1) | 生产者补丁(取数名单与可持仓分离,R10-B01)+ `symbols_fetch` = 450 + 72;72 名 40 天 5m 回填(先隔离副本、验收、再装入);**模型、EMA、席位都不动** | 旧模型在新成员集上打分;**可持仓仍是 450**(新增名零持仓) | 回填验收;下一锚 A* 逐位平价(§A6)通过才进 B |
| B(窗口 2,即换装本身) | 资金费 EMA 重播种;换 King / F10 文件与 MANIFEST;席位历史播种(需用户字);执行器钉同步 | 换模型 + 资金费状态 + 席位 | 首锚验收(§B6) |

执行器任何套件一律经 `ops/run_acceptance_offline.sh`(E-0923-D;`safe_commit.sh` 已在离线沙箱跑全电池,本手册没有单独复跑套件的步骤)。M3 不随本次换装打开。

## A. 窗口 1(静默窗 [N+1:00, N+3:40];须用户确认)

A0 停服务(只停生产者与 combo 写者):
```
launchctl list | egrep 'com.hsy.(shadowloop|combolive)'
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hsy.shadowloop.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist
ps aux | egrep 'shadow_loop_v3|combo_stage' | grep -v egrep        # 必须为空
ps -p $(cat ~/wide_shadow/shadow.lock) || echo "lock PID not alive (ok)"
```
A0b 备份(带 sha):`mkdir <BK> && cp -p ~/wide_shadow/shadow_loop_v3.py ~/wide_shadow/state/{rolling.npz,aux.json,leg_returns_live.json,generation.json} ~/wide_shadow/shadow_bundle/{config.json,MANIFEST.json,slow2026.txt} ~/wide_shadow/fea171/f10_live_s42_np.npz <BK>/ && (cd <BK> && shasum -a 256 * > SHA256SUMS)`。

A1 生产者补丁 + 取数名单(R10-B01):
- `cp deploy/producer_patch/shadow_loop_v3.patched.py ~/wide_shadow/shadow_loop_v3.py`,核 sha256 = `ed11d731ffc13ef1333c3fabe044bc209485ba237fd9b8ae11aeccb014be1ec9`(相对 6080073b 的逐行 diff `producer_patch/shadow_loop_v3_R10B01.diff`:新键 `symbols_fetch` 只用于 L406 取数 / L434 覆盖 / L448 秩基并集 / L538 fund 值与 base 缺省;`symbols_live` 仍管 L77 目标 universe / L276 live_mask / L580 尾部 / L634 EXIT keep)。
- `~/wide_shadow/venv/bin/python deploy/news_prod_files.py fetchlist deploy/added_names.json <BK>/A1` —— `config.json` 加 `symbols_fetch` = 450(原序)+ 72(字母序),`symbols_live` 与其余键逐字节不变(脚本断言),MANIFEST 同步;旧→新 sha 打印并存 `<BK>/A1/BACKUP_MANIFEST.json`。
- 门(已过,收据 `TEST_FETCHLIST_SPLIT.json` VERDICT=PASS):无 `symbols_fetch` 时补丁与原文件输出逐字节同(5 锚);有时成员 = 训练回放、新增名零持仓、universe 仍 450;红控:旧稿(扩 `symbols_live`)会持有新增名。

A2 回填 72 名 40 天 5m(**调交易所 fapi,与实盘共用每 IP 权重,E-0919-V;执行前把命令原文与预计请求数发给 lead**):
```
python3 ~/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py --json     # 退出码 0 才继续
~/wide_shadow/venv/bin/python deploy/news_backfill.py fetch deploy/added_names.json parity_cache_slice.npz parity_holes_slice.npz <BK>/A2
```
- 预计 `/fapi/v1/klines` 5m limit 1000(权重 5)× 72 名 × 12 次 = 864 次 ≈ 4,320 权重;限速 300 权重/分钟(已发布上限 2400 的 12.5%;硬上限 50% = 1200,含本 IP 全部客户端),约 15 分钟;开始前 `require_quiet_window(剩余 ≥ 25 分钟)`,每次请求前 `wait_for_quiet_window`;逐请求与逐分钟记录本 IP 用量 `X-MBX-USED-WEIGHT-1M`(含实盘的外部权重)到 `<BK>/A2/requests.log`;>600 暂停到下一分钟,>1200 中止。
- **只写隔离副本** `<BK>/A2/isolated_state/`;验收(全过才写):每名首根之后无缺行(缺口具名);≤ 2026-09-19T00Z 的行与 x0918r 在非补洞格 7 通道逐位相等(同一检查对在役 450 名实测 0 格不同);其余 757 列逐字节不变。备选源 `data.binance.vision` 日归档(不走 fapi 权重),当日部分仍须 fapi,同一验收。

A3 装入(**部署动作,用户确认后**;生产者仍停着;A2 的 fetch 必须在本次停机后取,否则拒绝):`news_backfill.py install deploy/added_names.json <BK>/A2`。

A4 重启:`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.shadowloop.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist`;核 `ps eww -p <新pid>` 含 `SHADOW_OFFSET_MIN=12`、`tail -2 ~/wide_shadow/loop.out` 出现 `next <下一槽>`。

A5 首锚 A* 运行后:`shadow_log.jsonl` 最后一条 `signal`:`members`=400、`fetched`=522、`missing`=0;`target_live/<A*>.json` `n_universe`=450;`combo_live_status.json` ok;执行器照常(旧钉)。

A6 逐位平价门(换模型前,只读,下一个静默窗):`combosnap` 归档 `state/snap/<A*>` 后,`mac_candidate_acceptance.py` 的 live 读法(成员、X78/X82/X89 用生产代码在快照状态上重算、King `legz` 用在役 booster 重算 = `prev_rec`)对训练规则(SPEC 合法函数 ∧ 加密币类,已在 9 个历史锚上与 x0918r 掩码 0 名不同):成员集相等、特征逐位相等。不等 ⇒ 不进 B,§R-A 回滚。

## B. 窗口 2(A6 通过后的静默窗;换装本身,须用户确认)

B0 同 A0 停服务并备份(带 sha)。

B1 资金费 EMA 重播种(改生产者状态;资金费腿是书的主体 ⇒ 只在本窗口随换模型一起做):
```
~/wide_shadow/venv/bin/python deploy/news_ema_reseed.py fund_replay_tail.npz <BK>/B1           # 干跑:逐名前后差值表 <BK>/B1/EMA_RESEED_REPORT.json
~/wide_shadow/venv/bin/python deploy/news_ema_reseed.py fund_replay_tail.npz <BK>/B1 --write   # 确认后写入
```
- 从训练回放 2026-09-19T00Z 的状态出发,用生产者自己的 EMA 更新行(L472–L480 编译)把生产账本其后的每条结算按序推进;每条推断间隔须等于账本存值,否则拒绝;829 轴外名保持原值。09-23 08Z 只读干跑:522 名、0 拒绝、相对变化中位 2.6e-11 / p99 8.3e-6 / 最大 0.45%。
- 状态副本全演练已过(`TEST_EMA_RESEED_REHEARSAL.json` PASS):真实写入 → 生产 ShadowState 重载 → 生产代码推进一锚后 522/522 名 EMA 与独立重算逐位相等 → 保存重载 → 只回滚模型/配置可加载;负控:旧 aux 配新 rolling 被生产者拒绝启动。

B2 模型文件:`deploy/news_prod_files.py models <PKG>/slow2026.txt <PKG>/f10_live_s42_np.npz <BK>/B2` —— 替换 `shadow_bundle/slow2026.txt` 与 `fea171/f10_live_s42_np.npz`,MANIFEST 同步;脚本打印的两个钉须等于 `<PKG>/P5_DEPLOY_MANIFEST.json` 的 `deploy.executor_pins`。

B3 席位历史播种(**书行为,需用户字**;不做则 w3 在约 900 锚 ≈ 150 天内仍由旧 King 腿收益决定,部署的书 ≠ 评估的书):`state/leg_returns_live.json` 三条腿写入候选包评估的腿收益序列(截至其最后一锚的最后 950 条),重签 generation。kc/fc 链状态从在役状态热启动,按 α = 0.1 收敛(半衰期约 6.6 锚),属预期转换期,单列报告。

B4 执行器钉(现行协议 `executor_deploy_protocol_isolated_checkout_2026_09_23`):隔离 main 检出 → 复制实盘 state → 改 `config/book.json` `external_book.booster_sha_pin` / `f10_sha_pin` = manifest 值 → `bash ops/safe_commit.sh "<msg>" config/book.json`(离线沙箱全电池约 17 分钟,须在静默窗)→ 推 main → 静默窗内持 `state/anchor.lock` 对运行树 `fetch` + `merge --ff-only <sha>`,核三方 sha 与代码区干净。**B1–B4 必须落在同一对锚之间**(执行器读取 N+24 之后、下一锚生产者 N+4h+12 之前),否则执行器对钉不符的目标 HOLD。

B5 重启(同 A4)。

B6 首锚验收:`target_live/<A>.json` `booster_sha` / `f10_sha` = 新钉;执行器读者判词 ok(非 `REFUSED f10_pin` / booster);`combo_live_status.json` ok、`n_f10_scored` ≥ 380、gross ∈ [0.4, 1.2];aux `ema` 按生产更新继续推进(用 B1 同一装置从 09-19 状态重算到该锚逐位相等);`mac_candidate_acceptance.py` live 读法以新模型重算,成员 / 特征 / King 预测逐位相等,F10 numpy 分数与评估的差在 1e-5 内,combo 目标 = 在服务输入上重算的 combo_target.step 逐位相等(转换期内 kc/fc 与评估链不同属预期)。

## R. 回滚(均为正向操作,不强推;递推状态 aux / rolling / generation / leg_returns 一律继续向前,不恢复)

- R-A(阶段 A 后):停服务 → 恢复 `<BK>` 的 shadow_loop_v3.py / config.json / MANIFEST.json → `news_backfill.py rollback deploy/added_names.json <BK>/RA`(72 列整列置 NaN、删其 prev_close、重签 generation;不能用旧 rolling.npz 覆盖:会丢其后的 bar)→ 重启。
- R-B(阶段 B 后):停服务 → 恢复 B0 备份的 slow2026.txt / f10 npz / MANIFEST(模型与配置)→ 执行器以正向提交恢复旧钉(`8d79186b…` / `351ae26b…`)走同一协议 → 重启。EMA 重播种与席位播种不回退(演练已证:旧 aux 配新 rolling 生产者拒绝启动;重播种后的 EMA 与旧模型兼容)。

## M. 取数名单的维护(候选池会漂移)

- 训练规则的候选池 ⊆ 829 名轴 ∩ 加密币类 ∩ 当时可交易。829 名轴固定 ⇒ 部署后池只会因下架缩小、极少因复牌扩大;新上市币不在轴内,训练与服务都不会选。
- 每月一次(建议与月度重训同日、静默窗内):一次 `GET /fapi/v1/exchangeInfo`(权重 1)取 TRADING 的 USDT 永续 ∩ 829 轴 ∩ 加密币类(冻结规则)− `symbols_fetch` ⇒ 必须为空;不空则按 A1/A2 追加并回填。829 轴扩容属另一项目,扩容时同步扩名单。
- 已知残余(本轮接受,下一轮改特征代码时修):生产者成员筛没有合法掩码 ⇒ 名单内「已不可交易但仍有冻结行」的名可能被选入(2025-07→2026-09 约 4% 的锚差 1 名,9 月 0)。

## C. 本轮文件 sha

| 文件 | sha256 |
|---|---|
| 生产者补丁 `shadow_loop_v3.patched.py` | `ed11d731ffc13ef1333c3fabe044bc209485ba237fd9b8ae11aeccb014be1ec9` |
| 候选包 King / F10 / manifest | 见 `<PKG>/P5_DEPLOY_MANIFEST.json`(NEW_S 在 SWAP 后由 P5 导出填入结果文档) |
