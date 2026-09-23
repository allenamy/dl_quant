> **创建:** 2026-09-23 | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(NEW_S 执行代理,受 lead 派) | **状态:** 手册草稿,**待 lead 审,未执行**。只有同时满足四个条件才执行: 判词 SWAP、候选包最终验收 ACCEPT、用户确认、由 lead 执行或在 lead 监督下执行 | **作废条件:** 下列任一 sha 与 §0.3「执行前核对」不符 —— 生产者源码(shadow_loop_v3.py 6080073b / combo_stage.py fb5a9407 / dlw_features.py 29ae6a98 / f8_higher_order_features.py 2c500c7a)、bundle(config.json 3a8422f3 / MANIFEST.json af61d597 / slow2026.txt 8d79186b / f10_live_s42_np.npz 351ae26b)、执行器运行树 b66257b 及其两个钉、生产者补丁 ed11d731、候选包 `PACKAGE.json`

# 部署手册: 候选包换装(NEW_S 或 FRESH;候选包是参数)

相关文档: 结果 `docs/RESULT_new_servable_models_2026-09-23.md`(判词 SWAP)· 预注册 db0123df7 + 修订 1 63ca0d0bb + 修订 2 f24467c5d · 执行器现行部署协议(隔离 main 检出 → 复制实盘 state → `ops/safe_commit.sh` 离线全电池 → 推送 → 静默窗内持 `anchor.lock` 快进)· 工具与演练收据 `multi_asset/exports/research/news_2026-09-23/deploy/`。

本手册的路径约定(执行前逐个 `export`):
```
export NS=~/cc_tmp/news_20260923                 # 工具与数据层输入的本机目录(不在 iCloud 下)
export PKG=$NS/package_NEW_S                      # 候选包目录;换 FRESH 时只改这一行
export BK=~/cc_tmp/deploy_$(date -u +%Y%m%dT%H%MZ)  # 本次备份根目录;两个窗口共用同一个 $BK(W2 开始时手工设成 W1 的那个值)
export PYP=~/wide_shadow/venv/bin/python          # 生产 venv
```

## 0. 候选包与前置条件

### 0.1 候选包 `$PKG` 必须包含的文件(索引 `PACKAGE.json` 写有每个文件的 sha256 与用途)

| 文件 | 用途 | 缺了怎么办 |
|---|---|---|
| `slow2026.txt` | King 模型(部署;执行器 `booster_sha_pin`) | 必须有 |
| `f10_live_s42_np.npz` | F10 numpy 模型(部署;执行器 `f10_sha_pin`) | 必须有 |
| `P5_DEPLOY_MANIFEST.json` | 导出清单: `VERDICT=BOUND`、`deploy.V1_gate.PASS=true`、`deploy.executor_pins` | 必须有 |
| `added_names.json` | 取数名单要加的名字(`symbols_fetch` = `symbols_live` 原序 + 这些名字按字母序) | `[]` ⇒ 整个窗口 1 跳过, 只做窗口 2(见 §1) |
| `fund_replay_tail.npz` | 资金费 EMA 重播种的起点: 候选训练回放的资金费状态 | 候选若不需要重播种, 包里写明理由, 跳过 B1 |
| 评估行 `*_ACCEPT_ROWS.npz` + 变异对照 F10 | 候选包验收的输入 | 必须有 |
| `crypto_*.npz` | 829 名轴上的加密类标记(A6/B6 检查用) | 必须有 |

NEW_S 的实例: `$PKG = ~/cc_tmp/news_20260923/package_NEW_S`。仓库里有逐字节相同的副本 `multi_asset/exports/research/news_2026-09-23/package_NEW_S/`, `PACKAGE.json` sha256 `faeabb60dd78f2ee…`。

| 文件 | sha256 |
|---|---|
| slow2026.txt | `b521ccdcd045a0975f107fed1e415b22ec72a96fb7f17a30da13f0583bacd0a2` |
| f10_live_s42_np.npz | `6e97dc8afcaff41d672206871f071c4562bd66bf55ec3403d69eb652a2d4e6eb` |
| P5_DEPLOY_MANIFEST.json | `3a648aa6212b48e9563be1746c7da05d66a9249b70b341c08120baa354bed8e0` |
| added_names.json(72 名) | `a216918cbda87ce35a85235ce087a537824acbfc96ff75f73696fb2542369dc7` |
| fund_replay_tail.npz | `8b67ac597037ba135d3c52d61e0edfc15823865e220c51484e21c65f22d48e42` |
| NEWS_ACCEPT_ROWS.npz | `e20c1e6cd106ce3938e530b4368abf0781d024ed74d98081fcad1a4dc169a931` |
| f10_live_s2027_np_MUTATION_ONLY.npz(只作变异对照, 永不部署) | `b83435dde03b48dca1253c583fdd61d22c7a4e0869218822a8e93e61af8b4000` |
| crypto_P1_members_2025H2on.npz | `2323623fda9333710f5834911ab629377ab8c12b056f40ccfc9f7033c0c1f6f1` |

执行器两个钉 = `P5_DEPLOY_MANIFEST.json` 的 `deploy.executor_pins`: NEW_S 为 `booster_sha_pin = b521ccdc…a0a2`、`f10_sha_pin = 6e97dc8a…d4e6eb`。在役是 `8d79186b…1282` / `351ae26b…b3a4`。

**只部署一次**: 如果 FRESH 过了它自己的判据且 NEW_S 还没部署, 就只部署 FRESH, 把 `$PKG` 换成 FRESH 的包目录, 其余步骤不变。

### 0.2 前置条件(任一不满足就不开始)

1. 候选的判词为 SWAP(NEW_S: `NEWS_STATS.json` d86e96f4…, `NEWS_STATS VERDICT=SWAP`)。
2. `P5_DEPLOY_MANIFEST.json` 的 `VERDICT=BOUND`, 且 V1 门 PASS。
3. 对**同一个** `$PKG` 跑候选包验收(命令见 §P1), 判词为 `CANDIDATE_ACCEPTANCE VERDICT=ACCEPT`, 退出码 0。
4. 用户确认两个窗口的书行为变化(§1 表里「书行为」一列)。B3 席位播种另需用户单独的一句话。
5. 由 lead 执行, 或在 lead 监督下执行。

### 0.3 执行前核对(W1 开始的第一条命令;任一不符 ⇒ **停**, 本手册过期)

```
shasum -a 256 ~/wide_shadow/shadow_loop_v3.py ~/wide_shadow/fea171/{combo_stage.py,dlw_features.py,f8_higher_order_features.py} \
  ~/wide_shadow/shadow_bundle/{config.json,MANIFEST.json,slow2026.txt} ~/wide_shadow/fea171/f10_live_s42_np.npz
#   期望前 8 位依次为: 60800739 fb5a9407 29ae6a98 2c500c7a 3a8422f3 af61d597 8d79186b 351ae26b
git -C ~/dl_quant_live rev-parse --short HEAD                       # 期望 b66257b(若已变: 读新提交后再决定是否继续)
/usr/bin/python3 -c "import json;b=json.load(open('$HOME/dl_quant_live/config/book.json'))['external_book'];print(b['booster_sha_pin'][:8],b['f10_sha_pin'][:8])"   # 期望 8d79186b 351ae26b
(cd $PKG && shasum -a 256 -c <(/usr/bin/python3 -c "import json;[print(v['sha256']+'  '+k) for k,v in json.load(open('PACKAGE.json'))['files'].items()]"))   # 全部 OK
```

## 1. 时间线: 为什么要两个静默窗, 每一步多久

静默窗 = [N+1:00, N+3:40] UTC(N = 00/04/08/12/16/20)。锚内时刻: 生产者 N+0:12 运行, combo 在 N+0:17 至 N+0:22:35 之间写出, 执行器 N+0:24 读取(重试到 N+0:29), 下一锚生产者 N+4:12 运行。

**一个窗口放不下**, 原因不在耗时, 在顺序。lead 已裁定: 先扩取数名单并回填, 在**一个真实锚**上用旧模型做逐位检查(A6), 通过后才换模型。这个锚只能是窗口 1 之后的 N+4 锚, 所以最少要两个连续静默窗: W1 = [N+1:00, N+3:40], W2 = [N+5:00, N+7:40]。

| 阶段 | 步骤 | 预计 | 书行为变化 | 截止 |
|---|---|---|---|---|
| **P(任何更早的静默窗)** | P1 候选包最终验收 · P2 EMA 重播种干跑 · P3 回填/安装/回滚在状态副本上演练 · P4 A6/B6 检查装置对照 | 各 5–20 分钟 | **无**(只读或写隔离副本) | — |
| **W1** | A0 停服务 3 · A1 备份 2 · A2 回填取数(隔离副本)约 15–18 · A3 安装 1 · A4 补丁 + `symbols_fetch` 3 · A5 重启 2 | **约 30 分钟** | **有**: 从 N+4 锚起, 旧模型给**新的成员集**打分(400 名成员里约 30 名来自新加的 72 名, King 腿与资金费秩基随之变化)。可持仓仍是 450 名, 新名零持仓 | A2 开始时剩余时间 ≥ 25 分钟(工具强制), 所以 A0 最晚 N+2:30 开始 |
| (锚 N+4) | 生产者用新名单跑一锚, 执行器用旧钉照常交易 | — | 同上 | — |
| **W2** | A6 逐位检查 5 · B0 停服务 + 备份 3 · B1 EMA 重播种 3 · B2 换模型 2 · (B3 席位播种 3, 需用户字) · B4 执行器钉: 隔离检出 + 复制 state 4 + 离线全电池约 17 + 推送 1 + 快进 1 · B5 重启 2 | **约 40–45 分钟** | **有**: 换模型 + 资金费状态(+ 席位) | B4 的 `safe_commit` 最晚 N+6:50 开始(电池约 17 分钟, 要在 N+7:40 前推完并快进); 过了截止就走 §R-B, 不硬赶 |
| (锚 N+8) | B6 首锚验收 | — | — | 执行器 N+8:24 读取后 |

**能在更早窗口先做、而且完全不改线上行为的**: P1–P4 全部。A2 的回填取数本身也不改线上(只调交易所并写隔离副本), 但它必须和 A3 安装在同一窗口、在生产者停着的时候做。原因: 安装时会核对「生产状态没有在取数之后推进」, 而且生产者每锚只往回补 52 根 bar。补丁文件(A4 前半)单独装上时, 输出与原文件逐字节相同(`TEST_FETCHLIST_SPLIT.json`, 5 锚), 也可以提前装。但它要重启生产者, 而且单装没有收益, 所以不建议单独提前。

**候选包 `added_names.json` = `[]` 时**(例如某个 FRESH 包的数据层与在役相同): 跳过 W1 与 A6, 一个窗口 W2 就能做完。

## P. 预备步骤(任何更早的静默窗;不改线上;由操作者执行)

**P1 候选包最终验收**(约 16 分钟, 本机重活, 只能在静默窗跑):
```
cd $NS && $PYP -u devices/mac_candidate_acceptance.py --king $PKG/slow2026.txt --f10 $PKG/f10_live_s42_np.npz --manifest $PKG/P5_DEPLOY_MANIFEST.json \
  --eval $PKG/NEWS_ACCEPT_ROWS.npz --replay $NS/parity/parity_fund_slice.npz --added $PKG/added_names.json --x0918r $NS/parity/parity_cache_slice.npz \
  --holes $NS/parity/parity_holes_slice.npz --producer $NS/deploy/producer_patch/shadow_loop_v3.py --control-f10 $PKG/f10_live_s2027_np_MUTATION_ONLY.npz \
  --start 1789660800 --n 7 --out $NS/accept_final_$(basename $PKG) ; echo "rc=$?"
```
- 通过条件: 末行 `CANDIDATE_ACCEPTANCE VERDICT=ACCEPT`, rc=0。
- 停点: REJECT 或 rc≠0 ⇒ 不部署, 把 `CANDIDATE_ACCEPTANCE.json` 的 `baseline_unexplained` 交给 lead。

**P2 EMA 重播种干跑**(只读, 约 1 分钟): `$PYP $NS/deploy/news_ema_reseed.py $PKG/fund_replay_tail.npz $BK/P2`
- 看 `$BK/P2/EMA_RESEED_REPORT.json`: 拒绝数必须为 0。
- 09-23 08Z 干跑的参考值: 522 名、0 拒绝、相对变化中位 2.6e-11 / p99 8.3e-6 / 最大 0.45%。

**P3 回填安装/回滚演练**(状态副本, 不调交易所): `WIDE_SHADOW_HOME=<副本>` 下跑 `news_backfill.py install` → 生产者加载并用假取数器推进一锚 → `rollback` → 再加载。收据 `deploy/TEST_BACKFILL_INSTALL_REHEARSAL.json`(见 §C;未演练过的路径不进 W1)。

**P4 A6/B6 检查装置的对照**: 在当前实盘锚(尚无 `symbols_fetch`)上跑 `news_live_check.py`, 期望如下:
- C0 / C1 / C3 全绿: 装置能逐位复现生产。
- C2 为红, 差异名都不在取数名单里: 装置看得见「名单没扩」。

收据见 `deploy/NEWS_LIVE_CHECK_control_*.json`。

## A. 窗口 W1(静默窗 [N+1:00, N+3:40];须用户确认;lead 执行或监督)

**A0 停服务**(只停生产者与 combo 写者; 执行器不停):
```
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hsy.shadowloop.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist
launchctl list | egrep 'com.hsy.(shadowloop|combolive)' ; echo "上一行必须为空"
ps aux | egrep 'shadow_loop_v3|combo_stage|combo_live_daemon' | grep -v egrep ; echo "上一行必须为空"
ps -p $(cat ~/wide_shadow/shadow.lock 2>/dev/null) >/dev/null 2>&1 && echo "STOP: lock PID alive" || echo "lock ok"
```
- 停点: 还有进程 ⇒ 停在这里查原因。**不要按名字杀进程**, 只能按 lock / pid 文件里的 PID。
- 侧车、combosnap、comboparity 不用停: 它们只读, 或只写各自的目录。

**A1 备份**(带 sha):
```
mkdir -p $BK/A1 && cp -p ~/wide_shadow/shadow_loop_v3.py ~/wide_shadow/state/{rolling.npz,aux.json,leg_returns_live.json,generation.json} \
  ~/wide_shadow/shadow_bundle/{config.json,MANIFEST.json,slow2026.txt} ~/wide_shadow/fea171/f10_live_s42_np.npz $BK/A1/ && (cd $BK/A1 && shasum -a 256 * > SHA256SUMS && cat SHA256SUMS)
```
- 核对: `$BK/A1/shadow_loop_v3.py` 必须是 60800739(后面 B1 要把它当原版源码用)。

**A2 回填取数到隔离副本**(调交易所 fapi, 与实盘共用每 IP 权重, E-0919-V)。**执行前把下面的命令原文和预计请求数发给 lead。**
```
python3 ~/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py --json ; echo "rc=$?  (必须 0)"
$PYP -u $NS/deploy/news_backfill.py fetch $PKG/added_names.json $NS/parity/parity_cache_slice.npz $NS/parity/parity_holes_slice.npz $BK/A2 ; echo "rc=$?"
```
- 预计请求量: `/fapi/v1/klines` interval 5m, limit 1000, 每次权重 5。每名约 12 次(40 天 = 11,520 根), 72 名共 864 次, 约 4,320 权重。
- 限速: 300 权重/分钟, 约 15 分钟取完(已发布上限 2400 的 12.5%)。
- 保护:
  - 开始前 `require_quiet_window(剩余 ≥ 25 分钟)`; 每次请求前 `wait_for_quiet_window`。
  - 本 IP 用量 `X-MBX-USED-WEIGHT-1M`(含实盘的外部权重)超过 600 就暂停到下一分钟, 超过 1200(上限的 50%)就中止。
  - 逐请求与逐分钟记录到 `$BK/A2/requests.log`。
- 只写 `$BK/A2/isolated_state/`, 不碰 `~/wide_shadow`。
- 通过条件: 末行 `BACKFILL ACCEPT (isolated copy written)`, rc=0。`$BK/A2/BACKFILL_REPORT.json` 里:
  1. 每个名字首根之后没有缺行(缺行按名字列出);
  2. ≤ 2026-09-19T00Z 的行与 x0918r 在非补洞格上 7 个通道逐位相等(同一检查对在役 450 名实测 0 格不同);
  3. 其余 757 列逐字节不变。
- 注意: 判据 (1)「首根之后无缺行」是硬门。交易所对某个 5 分钟区间不返回 kline(暂停交易、维护)时也会判 REJECT。这种情况不放宽, 按停点处理, 缺口按名字列在报告里, 交 lead 裁定。
- 停点:
  - `REJECT` ⇒ 不安装。直接走 A5 重启生产者(此时什么都没改, 线上照旧), 把报告交给 lead。
  - rc≠0 且报 `ABORT: X-MBX-USED-WEIGHT-1M` ⇒ 同上, 并记录外部权重。

**A3 安装回填**(不调交易所; 生产者仍停着; 工具会先核对生产状态自取数以来没有推进):
```
shasum -a 256 ~/wide_shadow/state/{rolling.npz,aux.json,generation.json}        # 前: 应等于 $BK/A1/SHA256SUMS 里的对应行
$PYP $NS/deploy/news_backfill.py install $PKG/added_names.json $BK/A2 ; echo "rc=$?"
shasum -a 256 ~/wide_shadow/state/{rolling.npz,aux.json,generation.json} | tee $BK/A3_SHA256SUMS   # 后: 三个都变
```
- 停点: `REFUSE: production state advanced` ⇒ 重新做 A2。其它失败 ⇒ 走 §R-A。

**A4 生产者补丁 + 取数名单**(R10-B01: 取数名单与可持仓分离):
```
cp $NS/deploy/producer_patch/shadow_loop_v3.py ~/wide_shadow/shadow_loop_v3.py && shasum -a 256 ~/wide_shadow/shadow_loop_v3.py   # 必须 ed11d731…1ec9
$PYP $NS/deploy/news_prod_files.py fetchlist $PKG/added_names.json $BK/A4 ; echo "rc=$?"
```
- 补丁相对 60800739 的逐行 diff 见 `deploy/producer_patch/shadow_loop_v3_R10B01.diff`:
  - 新键 `symbols_fetch` 只用于 L408 取数、L436 覆盖、L450 秩基并集、L540 fund 值;
  - `symbols_live` 仍管目标 universe、live_mask、尾部与 EXIT keep。
- `fetchlist` 做的事: `config.json` 加 `symbols_fetch` = 450(原序)+ 72(字母序), `symbols_live` 与其余键逐字节不变(脚本断言), MANIFEST 同步。脚本打印新旧 sha, 旧文件备份在 `$BK/A4/`。
- 停点: 断言失败 ⇒ 从 `$BK/A1` 恢复 `shadow_loop_v3.py` / `config.json` / `MANIFEST.json`, 再走 §R-A。

**A5 重启**:
```
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.shadowloop.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.combolive.plist
ps eww -p $(cat ~/wide_shadow/shadow.lock) | tr ' ' '\n' | grep SHADOW_OFFSET_MIN     # 必须 SHADOW_OFFSET_MIN=12
tail -2 ~/wide_shadow/loop.out                                                          # 必须出现 next <下一槽>
```

**锚 N+4 之后(不在窗口内, 只读查看)**:
- `~/wide_shadow/shadow_log.jsonl` 最后一条 `signal`: `members`=400、`fetched`=522、`missing`=0。
- `state/target_live/<N+4>.json`: `n_universe`=450, `booster_sha`/`f10_sha` 仍是旧值。
- `combo_live_status.json`: ok。
- 执行器照常读取并交易(旧钉)。

任何一项不符 ⇒ 下一个窗口走 §R-A, 不进 W2。

## A6 + B. 窗口 W2(紧接的下一个静默窗 [N+5:00, N+7:40];须用户确认)

**A6 逐位检查(换模型前的最后一道门;只读)**。等 combosnap 把 `state/snap/<A*>`(A* = N+4)归档完:
```
$PYP $NS/deploy/news_live_check.py --anchor <A*> --king ~/wide_shadow/shadow_bundle/slow2026.txt --f10 ~/wide_shadow/fea171/f10_live_s42_np.npz \
  --crypto $PKG/crypto_P1_members_2025H2on.npz --out $BK/A6 ; echo "rc=$?"
```
- 通过条件: `NEWS_LIVE_CHECK VERDICT=PASS`, rc=0, 即:
  - C0 旧模型身份一致;
  - C1 成员与三条腿 z 逐位复现生产;
  - C2 成员集等于训练规则(候选 = SPEC 合法 ∧ 加密)选出的 400 名; 若不等, 每个差异名都必须是 R1(在取数名单里、被生产者选中、但当锚不合法);
  - C3 在服务输入上重算的 combo 目标与生产 `weights_combo` 逐位相等。
- 停点: FAIL ⇒ 不进 B, 走 §R-A, 把收据交给 lead。

**B0 停服务 + 备份**: 同 A0 的命令, 再执行:
```
mkdir -p $BK/B0 && cp -p ~/wide_shadow/state/{rolling.npz,aux.json,leg_returns_live.json,generation.json} ~/wide_shadow/shadow_bundle/{config.json,MANIFEST.json,slow2026.txt} \
  ~/wide_shadow/fea171/f10_live_s42_np.npz $BK/B0/ && (cd $BK/B0 && shasum -a 256 * > SHA256SUMS && cat SHA256SUMS)
```

**B1 资金费 EMA 重播种**(改生产者状态; 资金费腿是书的主体, 只在本窗口随换模型一起做)。工具断言的是**原版**生产者源码 60800739, 而 A4 之后磁盘上的是补丁版 ed11d731, 所以要用 `NEWS_PRODUCER_SRC` 指向 A1 备份的原版。补丁没有改动工具要编译的 L472–L480 这几行, diff 可证。
```
shasum -a 256 $BK/A1/shadow_loop_v3.py                                                   # 必须 60800739…
NEWS_PRODUCER_SRC=$BK/A1/shadow_loop_v3.py $PYP $NS/deploy/news_ema_reseed.py $PKG/fund_replay_tail.npz $BK/B1 ; echo "rc=$?"          # 干跑
NEWS_PRODUCER_SRC=$BK/A1/shadow_loop_v3.py $PYP $NS/deploy/news_ema_reseed.py $PKG/fund_replay_tail.npz $BK/B1 --write ; echo "rc=$?"  # 写入
shasum -a 256 ~/wide_shadow/state/{aux.json,generation.json}                              # 后: 两个都变
```
- 做的事: 从训练回放 2026-09-19T00Z 的状态出发, 用生产者自己的 EMA 更新行把生产账本其后的每条结算按顺序推进。829 轴外的名字保持原值。
- 停点: 干跑出现任何拒绝 ⇒ 不写, 走 §R-B(此时只停了服务, 直接重启即可)。
- 演练收据: `TEST_EMA_RESEED_REHEARSAL.json` PASS。演练内容: 真实写入 → 生产者重载 → 推进一锚后 522/522 名与独立重算逐位相等。负控: 旧 aux 配新 rolling 时生产者拒绝启动。

**B2 换模型文件**:
```
$PYP $NS/deploy/news_prod_files.py models $PKG/slow2026.txt $PKG/f10_live_s42_np.npz $BK/B2 ; echo "rc=$?"
/usr/bin/python3 -c "import json;print(json.load(open('$PKG/P5_DEPLOY_MANIFEST.json'))['deploy']['executor_pins'])"
```
- 通过条件: 脚本打印的 `booster_sha_pin` / `f10_sha_pin` 与 manifest 的 `executor_pins` 逐字相同。
- 停点: 不同 ⇒ 从 `$BK/B0` 恢复这两个模型文件和 MANIFEST, 走 §R-B。

**B3 席位历史播种(可选; 书行为; 需要用户单独的一句话; 工具未写, 未演练)**:
- 不做的后果: 席位 w3 在约 900 锚(约 150 天)内仍由**旧** King 腿收益决定。实测 09-18T20Z 生产 King 席位是 0.381, 候选评估是 0.331。所以部署的书 ≠ 评估的书(结果文档 R8)。
- 做的话, 播种序列应当是: 评估腿收益截至 09-17T12Z, 再接候选生产者在实盘快照上逐锚自己产出的腿收益, 直到换装锚(验收装置的 baseline 链跑到最后一个快照即可产出), 取最后 950 条, 重签 generation。
- 用户同意后我再写工具, 并在状态副本上演练, 之后才能进窗口。

**B4 执行器钉**(现行协议; 执行器任何套件一律经 `ops/run_acceptance_offline.sh`, 由 `safe_commit.sh` 调用):
```
export XC=~/cc_tmp/exec_pins_$(date -u +%Y%m%dT%H%MZ)
git clone ~/dl_quant_live $XC && git -C $XC remote set-url origin https://github.com/allenamy/dl_quant_live.git && git -C $XC config user.name haosiyu && git -C $XC config user.email siyuhao0702@gmail.com
git -C $XC rev-parse --short HEAD                                                             # 必须等于运行树 HEAD(b66257b 或 §0.3 记下的值)
rsync -a --exclude acceptance/ --exclude quarantine/ --exclude __pycache__/ --exclude pycache_void/ --exclude '/*.log' --exclude '/*.out' --exclude anchor.lock ~/dl_quant_live/state/ $XC/state/
/usr/bin/python3 - "$XC/config/book.json" "$PKG/P5_DEPLOY_MANIFEST.json" <<'EOF'
import json, sys
p, m = sys.argv[1], json.load(open(sys.argv[2]))["deploy"]["executor_pins"]
raw = open(p).read(); b = json.loads(raw); eb = b["external_book"]
old = (eb["booster_sha_pin"], eb["f10_sha_pin"]); assert old == ("8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282", "351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4"), old
new = raw.replace(old[0], m["booster_sha_pin"]).replace(old[1], m["f10_sha_pin"]); nb = json.loads(new)
eb2 = nb["external_book"]; assert eb2["booster_sha_pin"] == m["booster_sha_pin"] and eb2["f10_sha_pin"] == m["f10_sha_pin"]
eb2c = dict(eb2); eb2c["booster_sha_pin"], eb2c["f10_sha_pin"] = old; nb["external_book"] = eb2c; assert nb == b, "other keys changed"
open(p, "w").write(new); print("pins", old[0][:8], old[1][:8], "->", m["booster_sha_pin"][:8], m["f10_sha_pin"][:8])
EOF
git -C $XC diff --stat && git -C $XC diff config/book.json                                   # 只有两行变化
(cd $XC && bash ops/safe_commit.sh "external_book pins -> <候选名> (booster <8位> / f10 <8位>); DEPLOY_new_servable_models_2026-09-23 B4" config/book.json) ; echo "rc=$?"
NEWSHA=$(git -C $XC rev-parse HEAD); echo $NEWSHA
/usr/bin/python3 ~/cc_tmp/lead_deploy_20260923/ff_running_tree.py $NEWSHA ; echo "rc=$?"   # 持 state/anchor.lock 快进运行树
git -C ~/dl_quant_live rev-parse HEAD ; git -C ~/dl_quant_live rev-parse origin/main ; echo $NEWSHA   # 三方相同
git -C ~/dl_quant_live status --porcelain --untracked-files=no | grep -v '^.. \(state\|logs\)/' ; echo "上一行必须为空"
```
- `safe_commit.sh` 在离线内核沙箱里跑全电池(09-23 为 162 套, 约 17 分钟)。全绿才 pathspec 提交并推送 GitHub main。它会拒绝在运行树里运行(exit 78)。
- 停点:
  - 电池红 ⇒ 不推送(脚本自己拒绝)⇒ 走 §R-B(恢复旧模型, 重启), 电池日志交 lead。
  - 快进 ABORT(锁忙 / 代码区脏 / origin 不等于预期)⇒ 不强推、不手改。若已推到 GitHub main 但运行树没快进, 执行器仍是旧钉, 此时生产者若带新模型重启, 下一锚目标会被执行器 HOLD ⇒ 走 §R-B, 并对 main 做正向提交恢复旧钉。
- 顺序约束: **B1–B4 必须落在同一对锚之间**(本锚执行器读取之后, 下一锚生产者 N+8:12 之前), 否则执行器对钉不符的目标 HOLD。

**B5 重启**: 同 A5。

**B6 首锚验收**(锚 A** = N+8, 执行器 N+8:24 读取之后, 只读):
1. 身份: `state/target_live/<A**>.json` 的 `booster_sha` / `f10_sha` = 新钉; `combo_live_status.json` ok, `n_f10_scored` ≥ 380, gross ∈ [0.4, 1.2]。
2. 执行器读者判词 ok: 执行器锚日志里没有 `REFUSED f10_pin` / booster 拒绝, 本锚有下单记录。
3. 逐位检查: 命令同 A6, 换成新模型。通过条件为 VERDICT=PASS。
   ```
   $PYP $NS/deploy/news_live_check.py --anchor <A**> --king $PKG/slow2026.txt --f10 $PKG/f10_live_s42_np.npz --crypto $PKG/crypto_P1_members_2025H2on.npz --out $BK/B6
   ```
   R2 的秩基差只影响评估与服务的对比, 这里比的是服务端与服务端的复现, 因此仍要求逐位相等。
4. EMA 延续: 在 `state/snap/<A**>/aux.json` 的副本上用 B1 同一工具干跑(工具只读 `state/aux.json`), 从 09-19 回放状态重算到 A**。
   ```
   mkdir -p $BK/B6ema/state && cp -p ~/wide_shadow/state/snap/<A**>/aux.json $BK/B6ema/state/
   WIDE_SHADOW_HOME=$BK/B6ema NEWS_PRODUCER_SRC=$BK/A1/shadow_loop_v3.py $PYP $NS/deploy/news_ema_reseed.py $PKG/fund_replay_tail.npz $BK/B6ema/out
   ```
   通过条件: 末行为 `EMA_RESEED ACCEPT … max_rel_change 0.0 (not written)`。这表示生产者自己推进的 EMA 与重算逐位相同。
5. 转换期(单列报告, 不是失败): kc/fc 链状态从在役链热启动, α = 0.1, 半衰期约 6.6 锚。未做 B3 时, 席位仍由旧腿收益决定。

任何一项不符 ⇒ 按 §R-B 回滚, 收据交 lead。

## R. 回滚(只回模型 / 钉 / 配置; 递推状态 aux / rolling / generation / leg_returns 一律继续向前, 不恢复旧文件; 不强推)

**R-B(换装之后, 或 W2 中途失败)**:
1. 同 A0 停服务。
2. `cp -p $BK/B0/{slow2026.txt,MANIFEST.json} ~/wide_shadow/shadow_bundle/ && cp -p $BK/B0/f10_live_s42_np.npz ~/wide_shadow/fea171/`, 然后核 sha(8d79186b / 351ae26b / MANIFEST 与 B0 相同)。
3. 执行器: 若新钉已进运行树, 用 B4 同一流程做正向提交, 把钉改回 `8d79186b…1282` / `351ae26b…b3a4`, 持锁快进; 若新钉还没推送, 跳过这一步。
4. 同 A5 重启。

EMA 重播种不回退。演练已证明两点: 旧 aux 配新 rolling 时生产者拒绝启动; 重播种后的 EMA 与旧模型兼容(资金费状态是数据, 不属于模型)。

**R-A(W1 之后、换模型之前)**:
1. 停服务。
2. `cp -p $BK/A1/{shadow_loop_v3.py} ~/wide_shadow/ && cp -p $BK/A1/{config.json,MANIFEST.json} ~/wide_shadow/shadow_bundle/`, 核 sha(60800739 / 3a8422f3 / af61d597)。
3. `$PYP $NS/deploy/news_backfill.py rollback $PKG/added_names.json $BK/RA`: 72 列整列置 NaN、删掉它们的 prev_close、重签 generation。**不能**用旧的 rolling.npz 覆盖, 那样会丢掉其后的 bar。
4. 重启。

## M. 取数名单的维护(候选池会漂移)

- 训练规则的候选池 ⊆ 829 名轴 ∩ 加密类 ∩ 当时可交易。轴固定, 所以部署后候选池主要会因下架而缩小, 极少因复牌而扩大; 新上市的币不在轴内, 训练和服务都不会选。
- **每月一次**(建议与月度重训同日, 在静默窗内, 经 `venue_quiet_window.py` 放行):
  1. 请求一次 `GET /fapi/v1/exchangeInfo`(权重 1), 取 TRADING 的 USDT 永续 ∩ 829 轴 ∩ 加密类(冻结规则) − `symbols_fetch`, 结果必须为空。
  2. 不空 ⇒ 这些名字按 A2–A4 追加并回填(`fetchlist` 会拒绝已有 `symbols_fetch` 的配置, 追加时先用 `$BK` 备份, 再改为「合并追加」模式, 该模式尚未实现, 需要时另写并演练)。
- 829 轴扩容属于另一个项目, 扩容时同步扩名单。
- 已知残余 R1(本轮接受, 下一轮改特征代码时修): 生产者成员筛没有合法掩码。名单内「已不可交易但仍有冻结行」的名字可能被选入: 2025-07→2026-09 约 4% 的锚差 1 名, 9 月 0 锚。

## C. 本轮工具与收据(`multi_asset/exports/research/news_2026-09-23/deploy/`, 本机工作副本 `$NS/deploy/`)

| 工具 | sha256(前 16) | 演练/测试收据 |
|---|---|---|
| `producer_patch/shadow_loop_v3.py`(补丁) | `ed11d731ffc13ef1` | `TEST_FETCHLIST_SPLIT.json` PASS |
| `news_prod_files.py` | 见 `DEVICES_SHA256SUMS_deploy.txt` | fetchlist 分支由 `TEST_FETCHLIST_SPLIT` 调用; models 分支在 P3 演练中调用 |
| `news_backfill.py` | 同上 | fetch 需要交易所(W1 首跑); install / rollback 见 `TEST_BACKFILL_INSTALL_REHEARSAL.json` |
| `news_ema_reseed.py` | 同上 | `TEST_EMA_RESEED_REHEARSAL.json` PASS |
| `news_live_check.py` | 同上 | `NEWS_LIVE_CHECK_control_*.json`(P4) |
| `mac_candidate_acceptance.py` | 同上 | 试跑 `receipts/acceptance/shakedown_r2/` ACCEPT; 正式包 `receipts/acceptance/final_package_NEW_S/` |
