> **创建:** 2026-09-23 19:5xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(集成代理 C-4,受 lead 派) | **状态:** **草稿,未执行**。§0.2 的前置门尚未全部取得:news2 判词与部署模型、F-1 实测、E3 正式、F-2 正式、平价门、M3c。工具与机器演练已入库(§C) | **作废条件:** §0.3 执行前核对任一 sha 不符;冻结件 b30e4afa5 / 修订 1 5c89f8d22 改动;发布树 treeNC4 的 PATCH_RECEIPT(0364c28d)改动

# 部署手册:完整修正版(生产者按研究员 NEW 特征合同服务)+ M3 对冲 shadow

相关文档:
- 设计 `docs/DESIGN_producer_new_contract_2026-09-23.md`,本手册对应它的 §A7、§D、§E、§F;
- 冻结件 `docs/FREEZE_new_servable_v2_2026-09-23.md`(b30e4afa5)与修订 1 `docs/FREEZE_new_servable_v2_amendment1_2026-09-23.md`;
- M3:`docs/AMENDMENT_2_m3_beta_overlay_2026-09-23.md` §3、`docs/AMENDMENT_3_m3_beta_overlay_2026-09-24.md`、`docs/IMPL_m3_beta_overlay_2026-09-23.md` §5;
- 前一份手册 `docs/DEPLOY_new_servable_models_2026-09-23.md`(NEW_S,已取消,留作后备)。

**和 NEW_S 手册的根本不同**:
- 生产者代码、状态格式、模型、执行器钉必须同时换,不能分成两个窗口。新合同的模型只认新合同的特征,旧模型不能给新特征打分;反过来也一样。
- 所以只有**一个静默窗**,不设「先扩名单、后换模型」的中间锚。
- 书行为变化(新模型 + 新成员规则 + 新资金费规则)从换装后的第一个锚开始;对冲在两个 shadow 锚之后才可能切 on。

路径约定(执行前逐个 `export`):
```
export NCW=~/cc_tmp/nc_20260923                      # 工具、发布树、种子包的本机目录
export PKG=$NCW/package_NC                            # §P1 打出的部署包
export SEEDPACK=$NCW/seed_pack_0919.npz               # 训练重放导出的种子包(pod2 nc_export_seed.py)
export CRYPTO=~/cc_tmp/news_20260923/package_NEW_S/crypto_P1_members_2025H2on.npz   # 冻结的加密类标记(sha 2323623f…)
export BK=~/cc_tmp/nc_deploy_$(date -u +%Y%m%dT%H%MZ) # 本次备份与收据根目录
export PYP=~/wide_shadow/venv/bin/python
export OLDB=8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282 OLDF=351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4
```

## 0. 部署包与前置条件

### 0.1 部署包 `$PKG`(`nc_package.py` 生成;`INSTALL_CONTRACT.json` 写有每个文件的候选 sha 与基线 sha)

| 目的地(相对 HOME) | 来源 | 新 / 改 |
|---|---|---|
| `wide_shadow/shadow_loop_v3.py` | 发布树 treeNC4(46c52d94) | 改(原 60800739) |
| `wide_shadow/fea171/{combo_stage,dlw_features,f8_higher_order_features,feature_cache_identity}.py` | treeNC4(363dd8c8 / 874c1870 / 98bc036d / e4ec55d1) | 改 |
| `wide_shadow/fea171/{nc_contract,tradability,beta_overlay_producer,stable_trend_reference}.py` | treeNC4(316a0b9b / a9fad82c / b77c180d / 01bf8b3d) | 新 |
| `wide_shadow/fea171/combo_state_snapshot.sh`、`combosnap/combo_parity_replay.sh` | 发布附件(58e58bd1 / d49cd834;DESIGN §A7-5 (2)) | 改 |
| `wide_shadow/fea171/combosnap/generation_files.py` | 发布附件(925481d0) | 新 |
| `regime_dash/regime_dash.py` | 发布附件(8210fe73;§A7-5 (3)) | 改 |
| `wide_shadow/shadow_bundle/crypto_axis.json` | 由 `$CRYPTO` 生成,字节与演练沙箱相同(工具断言) | 新 |
| `wide_shadow/shadow_bundle/slow2026.txt` | news2 的 King 部署模型 | 改 |
| `wide_shadow/shadow_bundle/MANIFEST.json` | 生产 MANIFEST,只把 slow2026.txt 与 crypto_axis.json 两项设成新值 | 改 |
| `wide_shadow/fea171/f10_live_s42_np.npz` | news2 的 F10 s42 部署模型 | 改 |

- 保持不变、安装时再核一次的文件:`config.json`、`xfer_*.npz`、combosnap 其余文件、`combo_live_daemon.sh`、`sidecar_blend.py`。
- 执行器钉 = 合同里的 `executor_pins`,也就是两个模型文件的 sha。

### 0.2 前置条件(硬门;任一不满足就不开始)

1. **换装判词**(FREEZE §2):F10 两个种子**各自**满足 A ∧ B1 ∧ B2。判词由 news2 给出,收据名在它交付时补进来。
2. **§E3 时序门 PASS**。
   - 装置:`nc_timing_gate.py`,在 treeNC4 上跑,不带 `--harness-phase-fix`;≥ 6 个锚,另加最坏回填锚。
   - `--fetch-measured` 与 `--backfill-measured` 取 F-1 的实测值(DESIGN §F-1)。
   - 门:combo 写完 ≤ N+19:35。
3. **§F-2 回滚演练 PASS**。
   - 装置:`test_nc_rollback_rehearsal.py`,在 treeNC4 上跑,输入为真种子包经 `nc_seed_state.py` 播出的状态。
   - (a)(a2)(a3)(b)(c)(d) 全绿;e1–e3 负控都能拦住。
   - (a3) 就是「侧车停掉后 combo 自写 state_H_f10」的一锚推进。
4. **平价门 PASS**(FREEZE §3.3「平价门逐位」)。
   - 装置:`nc_parity_gate.py`,在轴末前 6 个锚上比较 Mac 服务端与 pod2 训练构建,要求 0 格不同;两个负控都能看见差异。
5. **安装 / 回滚机器演练 PASS**:`test_nc_install_rehearsal.py`,已有 7/7 MACHINERY_PASS(§C)。
   - 部署包打好之后,用真包再跑一次。
6. **M3c**(AMENDMENT_3 §2-1):
   - 过 ⇒ 执行器配置 `beta_overlay.mode="shadow"`;
   - 不过 ⇒ `mode="off"`,对冲不随发布上线,新版本照常换装。
7. **用户确认书行为变化**:新模型、新成员规则、新资金费规则;M3 为 shadow。B3 席位播种另需用户单独的一句话(§S)。
8. 由 lead 执行,或在 lead 监督下执行。

### 0.3 执行前核对(W 开始的第一条命令;任一不符 ⇒ 停,手册过期)
```
$PYP $NCW/src/nc_install.py preflight $PKG ; echo "rc=$?"          # 必须 NC_INSTALL PREFLIGHT_PASS, rc=0(生产文件仍是打包时的基线)
git -C ~/dl_quant_live rev-parse --short HEAD                       # 期望 b66257b;变了 ⇒ 读新提交, 与 lead 定是否继续
/usr/bin/python3 -c "import json;b=json.load(open('$HOME/dl_quant_live/config/book.json'))['external_book'];print(b['booster_sha_pin'][:8],b['f10_sha_pin'][:8],b.get('producer_contract'))"   # 期望 8d79186b 351ae26b None
shasum -a 256 $SEEDPACK $CRYPTO                                    # 与种子包收据 NC_SEED_PACK.json、2323623f… 相同
launchctl print-disabled gui/$(id -u) | grep com.hsy.sidecar       # 期望没有 disabled 行(或 => false)
```

## 1. 时间线(一个静默窗 W = [N+1:00, N+3:40])

| 步 | 内容 | 预计 | 截止 / 停点 |
|---|---|---|---|
| A0 | 停生产者侧服务(侧车停用) | 3 分钟 | — |
| A1 | 取数名单 + 实时回填包(调场所) | 3–5 分钟 | 开始时剩余 ≥ 30 分钟(工具强制) |
| A2 | 播种新状态(隔离目录) | 1–2 分钟 | STOP / 未决界值格 ⇒ §R-A |
| A3 | 预检 + 安装(文件 + 状态) | 2 分钟 | 拒绝 ⇒ §R-A |
| A4 | 执行器:隔离检出 → 合 M3 → 补丁 + 钉 + 配置 → `safe_commit`(电池约 17–20 分钟)→ 快进 | 25 分钟 | `safe_commit` 最晚 **N+3:05** 开始;电池红 ⇒ §R-A |
| A5 | 重启四个服务(侧车不起) | 2 分钟 | — |
| (锚 N+4) | 首锚验收 §B | — | 执行器 N+4:24 读取之后 |
| (锚 N+8) | 第二锚验收 + M3 shadow 第二锚 | — | — |

- A0 最晚 N+2:05 开始,否则 A4 赶不上截止。赶不上就放到下一个静默窗,不硬赶。
- 顺序约束:A3(生产者新版)和 A4 的快进(执行器新钉)必须落在同一对锚之间,即本锚执行器读取之后、下一锚生产者 N+4:12 之前。否则执行器会对钉不符的目标 HOLD。
- **执行记录**:每一步把命令原文、开始 / 结束 UTC、输出末行、rc 追加到 `$BK/RUNLOG.md`。窗口结束后,RUNLOG 与收据入库,入库前去掉凭据类内容。

## P. 预备步骤(更早的静默窗;不改线上)

**P1 打包**(news2 交付部署模型之后):
```
$PYP $NCW/src/nc_package.py $PKG --tree $NCW/treeNC4 --extras $NCW/release --king <news2 King slow2026.txt> --f10 <news2 f10_live_s42_np.npz> --crypto $CRYPTO --label NC_RELEASE ; echo "rc=$?"
$PYP $NCW/src/nc_install.py preflight $PKG ; echo "rc=$?"          # PREFLIGHT_PASS
```
- 核对:`INSTALL_CONTRACT.json` 的 `executor_pins` 与 news2 判词收据里的模型 sha 逐字相同。

**P2 用真包做安装演练**(假 HOME,本机轻活):
```
$PYP $NCW/src/test_nc_install_rehearsal.py $NCW/treeNC4 $NCW/release $SEEDPACK <最新快照锚> $NCW/release_tests/install_rehearsal_real
```
- 模型用真包的,不再用替身。
- 通过条件:7/7。收据 `TEST_NC_INSTALL_REHEARSAL.json`。

**P3 执行器候选干跑**(可选,强烈建议;静默窗,约 20 分钟):
- 按 A4 的 1–4 步做出候选检出,不运行 `safe_commit`,改为在候选检出里运行 `bash ops/run_acceptance_offline.sh`,只看结果、不提交。
- 注意:钉与生产者文件的一致性类套件,在生产者尚未安装时可能判红。这一格按「预期红、具名」记录,其余必须全绿。

**P4 前置门收据**:把 §0.2 第 1–6 项的收据路径和 sha 抄进 `$BK/PREREQS.md`。

## A. 窗口 W

**A0 停服务**(生产者、combo、快照、平价、侧车;执行器不停):
```
for L in com.hsy.combosnap com.hsy.comboparity; do            # 周期任务: 等它自己跑完, 绝不在它持锁时杀
  for i in $(seq 1 60); do launchctl print gui/$(id -u)/$L 2>/dev/null | grep -q 'pid = ' || break; sleep 1; done
done
for L in com.hsy.shadowloop com.hsy.combolive com.hsy.combosnap com.hsy.comboparity com.hsy.sidecar; do launchctl bootout gui/$(id -u)/$L ; done
launchctl disable gui/$(id -u)/com.hsy.sidecar                  # 侧车停用(lead 裁定, DESIGN §A7-5 (1)); plist 保留, 供回滚
ps aux | egrep 'shadow_loop_v3|combo_stage|combo_live_daemon|sidecar_daemon|sidecar_blend|combo_state_snapshot|combo_parity' | grep -v egrep ; echo "上一行必须为空"
ls ~/wide_shadow/state/snap/.parity.lock 2>/dev/null ; echo "上一行必须为空(平价锁不在)"
```
- 停点:还有进程 ⇒ 查原因。**不按名字杀进程**,只能按 lock 或 pid 文件里的 PID。
- 不停的任务及理由(16 个 `com.hsy.*` 的普查见 DESIGN §A7-5):
  - regime_dash / anchor_report / universe_shadow 在 N+0:50–N+0:55 跑,窗口内不运行,下一次运行时读到的已是新文件;
  - depthwatch / guardtwin / stopoverlay / c2shadow / w4liqcapture / notary / markout_backfill / regime_weekly 不读生产者状态。

**A1 取数名单 + 实时回填包**(调交易所 fapi 公共端点,与实盘共用每 IP 权重,E-0919-V)。**执行前把命令原文和预计请求数发给 lead。**
```
$PYP $NCW/src/nc_fetch_list.py ~/wide_shadow/state $CRYPTO $BK/fetch_list.json ; echo "rc=$?"     # 期望约 522 名, 其中约 72 名不在 symbols_live
python3 ~/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py --json ; echo "rc=$?  (必须 0)"
$PYP $NCW/src/nc_deploy_fetch.py $NCW/treeNC4 ~/wide_shadow/state $BK/fetch_list.json $(python3 -c "import numpy as np;print(int(np.load('$SEEDPACK')['axis_end']))") $BK/live_pack.npz ; echo "rc=$?"
```
- 预计请求量:
  - 新名 K 线:约 72 名 ×(轴末到当前锚的行数 / 1000,向上取整)次,每次权重 5;
  - 轴末之后的界值格:每格 1 次,权重 1。
  - 以 09-23 为例,约 5 天、1,440 行 ⇒ 每名 2 页,合计约 150 次、约 750 权重。
- 限速与保护(工具内置):
  - 开始前要求静默窗剩余 ≥ 30 分钟,每次请求前再核一次;
  - 截止 N+3:10;
  - 本 IP 用量超过 1200 即中止;任何 429 / 418 即中止,不重试,记下响应头;
  - 逐请求记录在 `$BK/live_pack.npz.requests.jsonl`。
- 通过条件:`VERDICT=PACKED`,rc=0。
- 停点:
  - `PACKED_WITH_FAILURES` 或中止 ⇒ 不装;直接 A5 重启**旧**服务(此时什么都没改),并恢复侧车(§R-A 第 4 步),收据交 lead。

**A2 播种新状态**(不调场所;只写 `$BK/seeded/`):
```
$PYP $NCW/src/nc_seed_state.py $NCW/treeNC4 $SEEDPACK ~/wide_shadow/state $BK/seeded --live-pack $BK/live_pack.npz --fetch-list $BK/fetch_list.json ; echo "rc=$?"
```
- 通过条件:末行 `NC_SEED SEEDED`,rc=0。
- 停点:
  - `STOP_REPORT_TO_LEAD`:生产资金费账本在它自己的覆盖期内漏记超过 1%(lead 裁定);
  - `SEEDED_WITH_UNRESOLVED_BOUND_CELLS`:有界值格没拿到原始收益;
  - 任何拒绝:生产账本与回放不一致、生产有而回放没有的事件,等等。
  - 以上任一 ⇒ 不装,§R-A,收据 `$BK/seeded/SEED_RECEIPT.json` 交 lead。
- 写进部署收据的计数(FREEZE 修订 1 §5、lead 裁定):
  - 窗内的界值格、补值格、ch0 被置 NaN 的格;
  - 覆盖期内回放有、生产无的名单;
  - 轴末后被跨缺口规则置空的 ch0 格数;
  - 成员历史:来自种子包的锚数、重算的锚数。

**A3 预检 + 安装**:
```
$PYP $NCW/src/nc_install.py preflight $PKG --seeded $BK/seeded --seed-pack $SEEDPACK ; echo "rc=$?"
$PYP $NCW/src/nc_install.py apply $PKG $BK/install --seeded $BK/seeded --seed-pack $SEEDPACK ; echo "rc=$?"
```
- preflight 独立核对播种状态:
  - 轴末前的加密列与种子包逐位相同;
  - 非加密列逐字节不变;
  - 轴末后通道 1–6 不变,只有实时包补的行例外;
  - ch0 只允许被置空;
  - 每个加密界值格都在稀疏表里;
  - 状态是由**当前**生产状态播出的。
- apply 的要求与动作:
  - 要求静默窗剩余 ≥ 20 分钟、五个服务都不在跑,并持有执行器 `anchor.lock`;
  - 先把全部目的地与当前状态备份到 `$BK/install/`(含 SHA256SUMS);
  - 然后原子替换文件,再原子替换状态,generation.json 最后写;
  - 最后用**新装的**生产者加载状态验证。
- 通过条件:`NC_INSTALL installed_not_started`,rc=0。收据 `$BK/install/NC_INSTALL_RECEIPT.json`。
- 停点:拒绝或中途失败 ⇒ §R-A。

**A4 执行器**(现行协议;执行器套件一律经 `ops/run_acceptance_offline.sh`,由 `safe_commit.sh` 调用):
```
export XC=~/cc_tmp/nc_exec_$(date -u +%Y%m%dT%H%MZ)
git clone ~/dl_quant_live $XC && git -C $XC remote set-url origin https://github.com/allenamy/dl_quant_live.git && git -C $XC config user.name haosiyu && git -C $XC config user.email siyuhao0702@gmail.com
git -C $XC rev-parse --short HEAD                                                        # 必须 = 运行树 HEAD(b66257b 或 §0.3 记下的值)
git -C ~/dl_quant_live show HEAD:config/book.json > $BK/book.json.pre_nc && cmp $BK/book.json.pre_nc ~/dl_quant_live/config/book.json && cmp $BK/book.json.pre_nc $XC/config/book.json \
  && shasum -a 256 $BK/book.json.pre_nc | tee $BK/book.json.pre_nc.sha256                # 换装前 book.json 的字节与 sha: 回滚时逐字节恢复它(lead 裁定)
git -C $XC fetch ~/cc_tmp/m3_impl_20260923/exec m3-beta-overlay && git -C $XC merge --ff-only FETCH_HEAD && git -C $XC rev-parse --short HEAD   # 5b3d89c(main 若已前移: 改用 rebase, 与 lead 定)
git -C $XC apply --check $NCW/release_executor/anchor_report_producer_contract_on_5b3d89c.diff && git -C $XC apply $NCW/release_executor/anchor_report_producer_contract_on_5b3d89c.diff
mkdir -p $XC/ops/producer_release/20260923_nc && cp -p $PKG/INSTALL_CONTRACT.json $PKG/PATCH_RECEIPT.json $XC/ops/producer_release/20260923_nc/   # 生产者发布归档(先例 20260922)
/usr/bin/python3 $NCW/src/nc_exec_config.py $XC/config/book.json --contract $PKG/INSTALL_CONTRACT.json --expect-old $OLDB $OLDF \
  --beta-mode shadow --max-combined 2.5 --producer-contract nc_v1 ; echo "rc=$?"        # M3c 不过 ⇒ --beta-mode off, 不给 --max-combined
git -C $XC diff --stat
rsync -a --exclude acceptance/ --exclude quarantine/ --exclude __pycache__/ --exclude pycache_void/ --exclude '/*.log' --exclude '/*.out' --exclude anchor.lock ~/dl_quant_live/state/ $XC/state/
(cd $XC && bash ops/safe_commit.sh "NC release: producer_contract nc_v1 + pins (booster <8> / f10 <8>) + M3 beta_overlay shadow 2.5 + anchor_report daemon contract; quant_research DEPLOY_producer_new_contract_2026-09-23 A4" \
   config/book.json ops/anchor_report.py live/tests_anchor_report_builder.py ops/producer_release/20260923_nc/INSTALL_CONTRACT.json ops/producer_release/20260923_nc/PATCH_RECEIPT.json) ; echo "rc=$?"
NEWSHA=$(git -C $XC rev-parse HEAD); echo $NEWSHA
/usr/bin/python3 ~/cc_tmp/lead_deploy_20260923/ff_running_tree.py $NEWSHA ; echo "rc=$?"   # 持 state/anchor.lock 快进运行树
git -C ~/dl_quant_live rev-parse HEAD ; git -C ~/dl_quant_live rev-parse origin/main ; echo $NEWSHA   # 三方相同
git -C ~/dl_quant_live status --porcelain --untracked-files=no | grep -v '^.. \(state\|logs\)/' ; echo "上一行必须为空"
```
- `safe_commit.sh` 的行为:
  - 只允许在 main 上运行,在运行树里会被拒绝(exit 78);
  - 落后 origin 就先 rebase;
  - 在离线内核沙箱里跑全电池,全绿才按 pathspec 提交并推送;
  - M3 的 7 个提交随本次推送进入 main。
- 停点:
  - 电池红 ⇒ 脚本自己拒绝推送 ⇒ §R-A,电池日志 `$XC/state/_safe_commit_acc.log` 交 lead。
  - 快进 ABORT,包括锁忙、代码区脏、origin 与预期不符 ⇒ 不强推、不手改。
    - 若 GitHub main 已有新提交,而运行树没有快进:执行器仍是旧钉,新生产者发出的目标会被 HOLD ⇒ §R-A,并对 main 做正向提交恢复旧钉(§R-B 第 3 步同法)。

**A5 重启**(侧车不起):
```
for L in com.hsy.comboparity com.hsy.combosnap com.hsy.combolive com.hsy.shadowloop; do launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/$L.plist ; done
ps eww -p $(cat ~/wide_shadow/shadow.lock) | tr ' ' '\n' | grep SHADOW_OFFSET_MIN     # 必须 SHADOW_OFFSET_MIN=12
tail -2 ~/wide_shadow/loop.out                                                          # 必须出现 next <下一槽>
launchctl print-disabled gui/$(id -u) | grep com.hsy.sidecar                            # 必须 => disabled(或 true)
launchctl print gui/$(id -u)/com.hsy.sidecar 2>&1 | head -1                             # 必须是「未加载」类报错
```

## B. 换装后验收(锚 N+4 与 N+8;只读)

**B1 身份**:
- `state/target_live/<A>.json` 的 `booster_sha` / `f10_sha` = 新钉;
- 含 `beta_overlay` 字段,`data_cutoff_ts == A`、`n_names == 450`;
- `combo_live_status.json`:`ok`、`reader_ok`、`beta_overlay.ok`,且 reader_verdict 已由执行器的 `live/beta_overlay.py` 校验;
- `target_combo/<A>.json`:`n_f10_scored` ≥ 380(生产发布门是字面 380),kc/fc 来源都是 `own`。

**B2 耗时**(DESIGN §E5;每个换装后的锚都查,至少头两个锚):
- 生产者:`shadow_log.jsonl` 本锚 `signal` 行的 `runtime_s`,以及 `anchor_diagnostics` 的 phase_s(含新的 `exchange_info` 相位);
- `target_live` 的 `written_utc`;
- combo:`combo_live.log` 的 ⑤ 写完时刻。
- **任一锚 combo 写完晚于 N+19:35 ⇒ 按 §R-B 回滚**,收据交 lead。晚于 N+22:35 时守护本身不发布,执行器 HOLD。

**B3 新合同要素**(`signal` 行的 `nc` 块与相关字段):
- `exinfo_ok = true`;`nc.fetch_n` ≈ 522,且与 exchangeInfo 实时名单一致;`nc.fetch_new` 与 `nc.backfill_residual` 如非空须逐名说明;
- `nc.used_weight_1m_max` < 1200;`fund_bulk_ok`;
- `members` = 400;`fund_updates` 在 anchor_report 的期望带内。
- `combo_live_status` 或页报里若有 `nc_backfill_residual` 的 HIGH,逐名记入 RUNLOG。

**B4 执行器**:
- 锚日志里没有 `REFUSED f10_pin` 或 booster 拒绝,本锚有下单;
- anchor_report 显示「守护 2/2」,没有「侧车在跑」;
- anchors 行 `m3_beta_overlay.status == "shadow"`、`field_ok == true`、`hedge_target_usdt` 有限;orders 里没有 BTC 对冲单,也没有 `m3_overlay_leg`(IMPL_m3 §5 C)。
- 盲态约束:执行数据只报合池量。

**B5 快照与平价**:
- `state/snap/<A>/` 含 5 个签名状态文件、generation.json、COMPLETE;
- `state/snap/parity.log` 该锚一行为 `parity <A> rc=0 … PARITY_PARITY`。

**B6 仪表盘**:N+4:50 的 regime_dash 出了本锚行,没有 TypeError;`REGIME_DASH.md` 已更新。

**B7 M3 shadow 验收**(两个锚都做;AMENDMENT_2 §3 第 4 步):
- 字段每锚都存在且校验通过;
- β_exec 与研究侧同锚重算之差在 1% 以内,重算用 M3 的 `beta_parity/RUN_COMMANDS.sh` 装置;
- would-be 对冲量、合计杠杆读数、中性读数(剔除对冲)正常;
- 没有新的告警类。
- 两个锚都过 ⇒ 按 AMENDMENT_2 §3 第 5 步切 on:用 A4 同一路径,把 `nc_exec_config.py --beta-mode on` 做成一个正向提交,首锚按该文第 5 步验收。**对冲不在换模型的同一个锚里下单。**

**B8 转换期**(单列报告,不是失败):
- kc/fc 链从在役链热启动,α = 0.1,半衰期约 6.6 锚;
- 未做 §S 席位播种时,席位 w3 仍由旧腿收益历史决定。

任何一项不符 ⇒ 按 §R-B 回滚,收据交 lead。

## R. 回滚

**R-A(窗口内失败;执行器尚未快进)**:
1. 服务应仍停着(A0 状态)。
2. 若 A3 已运行,执行 `$PYP $NCW/src/nc_install.py rollback $PKG $BK/install ; echo "rc=$?"`。
   - 期望 `rolled_back_not_started`,`state_source` = backup。新生产者没有推进过状态,所以恢复安装前的状态字节,不丢 bar。
3. 若 A4 已推送到 GitHub 但没有快进:对 main 做正向提交,**把 book.json 逐字节恢复成换装前的备份**(lead 裁定:恢复备份并核 sha,不靠删键去逼近原文),路径同 A4(新的隔离检出 → 恢复 → `safe_commit` → 持锁快进)。
   ```
   /usr/bin/python3 $NCW/src/nc_exec_config.py <检出>/config/book.json --restore $BK/book.json.pre_nc --restore-sha $(cut -d' ' -f1 $BK/book.json.pre_nc.sha256) --expect-old <新钉两项>
   shasum -a 256 <检出>/config/book.json      # 必须 == $BK/book.json.pre_nc.sha256 的值
   ```
   - 换装前的 book.json 没有 `beta_overlay` 块。块缺失等于显式 off(`live/beta_overlay.config`),在持的对冲经只减通道撤下;也没有 `producer_contract` 键,缺失即 legacy,anchor_report 回到「守护 3/3」。
4. 恢复侧车:`launchctl enable gui/$(id -u)/com.hsy.sidecar`。
5. 重启全部五个服务:A5 的四个,再加 `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hsy.sidecar.plist`。
6. 核对:生产者加载的是旧版(60800739);侧车在跑;anchor_report 下一锚显示「守护 3/3」。

**R-B(换装之后)**(F-2 已按此路线演练,见 §0.2 第 3 项):
1. A0 停服务(侧车本来就停着)。
2. 状态降级:`$PYP $NCW/src/nc_downgrade_state.py ~/wide_shadow/state $BK/downgraded_$(date -u +%H%MZ) ; echo "rc=$?"`。
   - 期望 `NC_DOWNGRADE_OK`。它把**当前**状态转成旧格式;递推状态继续向前,不恢复换装前的旧文件。
3. `$PYP $NCW/src/nc_install.py rollback $PKG $BK/install --downgraded $BK/downgraded_<时刻> ; echo "rc=$?"`。
   - 期望 `rolled_back_not_started`,`state_source` = downgraded,`producer_load.state_files` 为 3 个。
4. 执行器正向提交,同 R-A 第 3 步:恢复备份的 book.json → 核 sha == 换装前记录值 → `safe_commit` → 持锁快进。钉回到旧值;块缺失即显式 off,在持的对冲经只减通道撤下;anchor_report 回到 legacy。
5. 恢复侧车并重启,同 R-A 第 4–6 步。

**R-M3(只撤对冲)**:`nc_exec_config.py --beta-mode off`,钉与 producer_contract 不动(`--expect-old` 填当前钉,`--pins` 同值,`--producer-contract nc_v1`),经 safe_commit 与快进。生产者不动,字段照写。

## S. 席位历史播种(可选;书行为;需要用户单独的一句话;工具未写)

- 不做的后果:席位 w3 在约 900 锚内,仍由换装前的腿收益历史(旧模型、旧合同)决定。
- 做的话,序列 = 训练构建在 NC 口径下的腿收益(`nc_legs.py` 的 LR,依赖 King OOF,截至轴末),接上新生产者在实盘快照上逐锚产出的腿收益,直到换装锚;取最后 950 条,重签 generation。
- 报给用户的量化:换装锚上旧历史与新历史各自给出的 w3,以及两者在最近 30 天回放上的书层差。
- 用户同意后再写工具,并在状态副本上演练。

## C. 工具与收据(研究仓 `multi_asset/exports/research/nc_2026-09-23/`)

| 工具 | 作用 | 测试 / 演练收据 |
|---|---|---|
| `devices/nc_derive_producer.py` | 发布树派生:唯一补丁实现;默认构建断言;check_a5 / check_phases | `receipts/TEST_NC_DERIVE_GUARDS.json` 20/20;`tree_receipt_release_2026-09-23T1950Z/` |
| `devices/nc_package.py` | 部署包与安装合同 | 安装演练 P1 |
| `devices/nc_install.py` | 预检 / 安装 / 回滚 | `receipts/install_rehearsal_machinery/` 7/7 MACHINERY_PASS |
| `devices/nc_seed_state.py` | 播种新状态 | `receipts/TEST_NC_SEED_FUNDING_GATE.log` 4/4 |
| `devices/nc_fetch_list.py` / `nc_deploy_fetch.py` | 取数名单 / 实时回填包 | F-1(`nc_fetch_test.py`)实测后补 |
| `devices/nc_downgrade_state.py` | 状态降级 | F-2 演练(e1–e3) |
| `devices/nc_exec_config.py` | 执行器配置编辑(正向);回滚 = 逐字节恢复备份并核 sha | 正向 5 例;恢复:错 sha 拒、当前钉不符拒、恢复后与换装前逐字节相同 |
| `release_extras/` | combosnap / comboparity / regime_dash | `receipts/release_extras/` 8/8、4/4,新旧格式平价实测 |
| `release_executor/` | anchor_report 守护合同补丁(基于 5b3d89c) | 套件 23/23 |
| `devices/nc_timing_gate.py` / `test_nc_rollback_rehearsal.py` / `nc_parity_gate.py` | §E3 / §F-2 / 平价门 | 正式收据待补;空跑见 `receipts/dryrun_2026-09-23/` |
