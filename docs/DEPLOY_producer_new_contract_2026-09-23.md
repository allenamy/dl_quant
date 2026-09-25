> **创建:** 2026-09-23 19:5xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(集成代理 C-4,受 lead 派) | **状态:** **草稿,未执行**。判词 `VERDICT=NO_DEPLOY`,用户放行 s42(`USER_OVERRIDE=053d50f4…`,`docs/RULING_user_NC_s42_override_2026-09-24.md`)。§0.2 清单(2026-09-24 02:5xZ):部署包 §P1 已打,真包安装演练 §P2 `REAL_PACKAGE_PASS` 14/14;E3 / F-1 / F-2 / 平价门 / P3 全过(treeNC5)。用户已确认 §0.4(`docs/RULING_user_NC_s42_final_confirm_2026-09-24.md`,e6d9605ba),05:00Z 窗部署,lead 监督。M3c(s42)判 PASS(dcd054a7c)⇒ A4 带 shadow 2.5。§0.2 全部满足,待窗口执行。工具与演练已入库(§C) | **作废条件:** §0.3 执行前核对任一 sha 不符;冻结件 b30e4afa5 / 修订 1 5c89f8d22 改动;发布树 **treeNC5** 的 PATCH_RECEIPT(3135cf8b)改动(~~treeNC4 0364c28d~~,已被 treeNC5 取代:A4 资金费跳过规则修复,冻结修订 2 = 778ba7324)

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
export PKG=$NCW/package_NC                            # §P1 打出的部署包(2026-09-24 02:39Z 已打, INSTALL_CONTRACT 00238e4b…)
export MODELS=$NCW/models_s42                         # news2 交接件: HANDOFF_deploy_s42.json(e24231fb)、P5_DEPLOY_MANIFEST.json(64abda0d)、两个模型
export RULING=~/Desktop/quant_research/docs/RULING_user_NC_s42_override_2026-09-24.md   # sha 053d50f4… = USER_OVERRIDE
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
| `wide_shadow/shadow_loop_v3.py` | 发布树 treeNC5(a68c7a5f;与 treeNC4 46c52d94 只差 L633 的 A4 修复) | 改(原 60800739) |
| `wide_shadow/fea171/{combo_stage,dlw_features,f8_higher_order_features,feature_cache_identity}.py` | treeNC5(363dd8c8 / 874c1870 / 98bc036d / e4ec55d1,与 treeNC4 相同) | 改 |
| `wide_shadow/fea171/{nc_contract,tradability,beta_overlay_producer,stable_trend_reference}.py` | treeNC5(316a0b9b / a9fad82c / b77c180d / 01bf8b3d,与 treeNC4 相同) | 新 |
| `wide_shadow/fea171/combo_state_snapshot.sh`、`combosnap/combo_parity_replay.sh` | 发布附件(58e58bd1 / d49cd834;DESIGN §A7-5 (2)) | 改 |
| `wide_shadow/fea171/combosnap/generation_files.py` | 发布附件(925481d0) | 新 |
| `regime_dash/regime_dash.py` | 发布附件(8210fe73;§A7-5 (3)) | 改 |
| `wide_shadow/shadow_bundle/crypto_axis.json` | 由 `$CRYPTO` 生成,字节与演练沙箱相同(工具断言) | 新 |
| `wide_shadow/shadow_bundle/slow2026.txt` | news2 的 King 部署模型(`700d9e7b…`,取自 HANDOFF_deploy_s42.json) | 改(原 8d79186b) |
| `wide_shadow/shadow_bundle/MANIFEST.json` | 生产 MANIFEST,只把 slow2026.txt 与 crypto_axis.json 两项设成新值 | 改 |
| `wide_shadow/fea171/f10_live_s42_np.npz` | news2 的 F10 s42 部署模型(`3d7d050f…`,取自 HANDOFF_deploy_s42.json) | 改(原 351ae26b) |

- 保持不变、安装时再核一次的文件:`config.json`、`xfer_*.npz`、combosnap 其余文件、`combo_live_daemon.sh`、`sidecar_blend.py`。
- 执行器钉 = 合同里的 `executor_pins`,也就是两个模型文件的 sha。

### 0.2 前置条件清单(硬门;任一项不是「已满足」就不开始)

2026-09-24 02:5xZ 集成代理整理。收据路径都相对研究仓 `multi_asset/exports/research/`,另注明的除外。
判词照写 `VERDICT=NO_DEPLOY` 加 `USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b`。这是用户在判词之上的放行,不是判词通过。

| # | 项 | 状态 | 收据 | 还缺什么 |
|---|---|---|---|---|
| 1 | 换装判词与用户放行(FREEZE §2;裁定 §4) | **判词 `VERDICT=NO_DEPLOY`,未改写**。s42:B1 不过,对 NEW_S −0.477 bps/日;s2027:A:S2 不过。**用户放行 s42**,`USER_OVERRIDE=053d50f4…`。s2027 不导出,也不作备选 | 判词 `news2_2026-09-23/receipts/engine/NEWS2_STATS.json`(6d689c9a);裁定 `docs/RULING_user_NC_s42_override_2026-09-24.md`(053d50f4,提交 b9c7a933d);news2 交接 `nc_2026-09-23/receipts/p1_p2_real_2026-09-24T0240Z/inputs_from_news2/HANDOFF_deploy_s42.json`(e24231fb)与 `P5_DEPLOY_MANIFEST.json`(64abda0d) | 不挡部署。裁定 §5 的必报项(N1–N5 全表、对研究员 NEW 的差距、30 日块原句、修订 1 两项诊断、逐修复书层归因)发布后补齐,owner news2 |
| 2 | 部署包 §P1 | **已打包**(02:39Z,treeNC5):`INSTALL_CONTRACT.json` sha 00238e4b…,17 个文件。执行器钉 = HANDOFF 的钉,逐字相同:King `700d9e7b7ee992a786528477ff9007ec93c3d16654f1abc52766e5406654020d`,F10 s42 `3d7d050f78a98cb09586ac9c75c0c12526bfd54b5d9f4c6d151f6121b333139f`。合同里写有 `VERDICT=NO_DEPLOY` 与 `USER_OVERRIDE=053d50f4…`。真 HOME 只读预检 `NC_INSTALL PREFLIGHT_PASS`,rc=0 | `nc_2026-09-23/receipts/p1_p2_real_2026-09-24T0240Z/p1_package/`(合同、打包与预检日志、`HANDOFF_CHECK.json`) | 无。W 开始时 §0.3 再预检一次:生产文件必须仍是打包时的基线 |
| 3 | 真包安装 / 回滚演练 §P2 | **`TEST_NC_INSTALL_REHEARSAL REAL_PACKAGE_PASS`,14/14,rc=0**(02:40:23–02:42:19Z,静默窗内,启动脚本自检)。输入:treeNC5(3135cf8b);真种子包 600d760e;最新快照 1790208000(09-24 00Z);真模型,sha 由 `nc_handoff_check.py` 从 HANDOFF 取。演练包与 §P1 包的 17 个候选 sha 逐个相同,基线也逐个相同。安装收据顶层写 `VERDICT=NO_DEPLOY`、`USER_OVERRIDE=053d50f4…` | `…/p1_p2_real_2026-09-24T0240Z/p2_rehearsal/`(`TEST_NC_INSTALL_REHEARSAL.json`、运行日志、`bk1_NC_INSTALL_RECEIPT.json`) | 无。具名限定:轴末之后的 3 个界值格用的是替身原始收益(演练不调场所)。部署时由 A1 实时取数补真值;没补上的,A2 按 `SEEDED_WITH_UNRESOLVED_BOUND_CELLS` 停 |
| 4 | §E3 时序门 | **`NC_TIMING_GATE PASS`**,7/7。combo 写完于 N+17:44.3,余量 110.7 s | `nc_2026-09-23/receipts/e3_nc5_2026-09-23/`(e54c60809) | 无。具名限定:沙箱用的是在役旧模型文件。真模型格式相同:King 文件小 0.1%,F10 字节数相同、网络形状相同。King 推理实测最多 2.2 s,相对 110.7 s 的余量可以忽略。真模型的耗时由换装后 §B2 逐锚实测 |
| 5 | §F-1 实时取数实测 | **`NC_FETCH_TEST VERDICT=PASS anchors=3 fetch_n=520`**。取数加计算最多 36.72 s,本 IP 每分钟权重峰值 684,无 429 / 418 | `nc_2026-09-23/receipts/f1_2026-09-23T2119Z/`(4d548b0f6) | 无 |
| 6 | §F-2 回滚演练 | **`NC_ROLLBACK PASS`**。a/a2/a3/b/c/d 全绿;e1–e3 三个负控都拦住 | `nc_2026-09-23/receipts/f2_nc5_2026-09-23/`(e54c60809) | 无 |
| 7 | 平价门(FREEZE §3.3) | **treeNC5 `NC_PARITY_GATE PASS`**:6 锚 × 11 量,0 格不同;两个负控都测出差异 | `nc_2026-09-23/receipts/parity_formal_2026-09-23/`(5fe0cf11c) | 无 |
| 8 | §P3 执行器候选全电池 | **`ACCEPTANCE: ALL GREEN (163/163 suites exit 0)`**,首次在 `mode=shadow` 配置下跑全电池 | `nc_2026-09-23/receipts/p3_2026-09-23T2100Z/`(2bec89bb3) | 无。当时的钉是替身;A4 的 `safe_commit` 会用真钉在真归档上再跑一次全电池,红了就不推 |
| 9 | M3c(AMENDMENT_3 §2-1) | **已满足**:判定底座 s42 判 PASS。判词行原文 `M3_READOUT NC_s42 VERDICT=PASS failing=[] undecided=[] R1=+0.0476 R2_diff=0.00853053275874803 R3_D=0.9995 out_sha256=091f8a041248ac81974f98274e477b65dbc27195c0e214f0fae3e60cfe4c5b42`。装置与口径先于数字提交(3df05f205、0e6d6b7c4);零对冲对照与底座逐位相等 | `m3c_2026-09-24/receipts/pod2/M3C_READOUT_s42.json`(提交 dcd054a7c;集成代理本机重算 sha = 091f8a04…,与判词行的 out_sha256 相同) | 无。A4 用 `--beta-mode shadow --max-combined 2.5`。s2027 是旁报,不参与判定,不等它 |
| 10 | 用户确认书行为改动(裁定 §4-3) | **已确认**(2026-09-24 02:5xZ):确认 §0.4(621033c0d)并定 05:00Z 窗部署 s42 | `docs/RULING_user_NC_s42_final_confirm_2026-09-24.md`(a1b44207,提交 e6d9605ba) | 无。§S 席位播种不在确认范围内。部署前还要报用户两项:席位差距量化(§0.5)与 M3c 判词 |
| 11 | lead 执行或监督 | **已定**:05:00Z 窗(N = 04Z),集成代理执行,lead 监督;每步报判词行原文与 rc,lead 确认后进下一步;停点一律按 §R | lead 消息(2026-09-24 02:5xZ) | A0 最晚 06:05Z 开始;A4 最晚 07:05Z 开始 |

- 第 1 项的 HANDOFF 里有一个键叫 `V1_gate.PASS`。它是 numpy 推理与 torch 推理的数值等价门(spearman ≥ 0.99999 且 maxabs ≤ 1e-5;实测 0.999999999997 / 6.55e-08),**不是书层录取**。
- 本清单之外,W 开始时还要跑 §0.3 执行前核对,其中含执行器健康检查。

### 0.3 执行前核对(W 开始的第一条命令;任一不符 ⇒ 停,手册过期)
```
$PYP $NCW/src/nc_install.py preflight $PKG ; echo "rc=$?"          # 必须 NC_INSTALL PREFLIGHT_PASS, rc=0(生产文件仍是打包时的基线)
git -C ~/dl_quant_live rev-parse --short HEAD                       # 期望 b66257b;变了 ⇒ 读新提交, 与 lead 定是否继续
/usr/bin/python3 -c "import json;b=json.load(open('$HOME/dl_quant_live/config/book.json'))['external_book'];print(b['booster_sha_pin'][:8],b['f10_sha_pin'][:8],b.get('producer_contract'))"   # 期望 8d79186b 351ae26b None
shasum -a 256 $SEEDPACK $CRYPTO                                    # 与种子包收据 NC_SEED_PACK.json、2323623f… 相同
launchctl print-disabled gui/$(id -u) | grep com.hsy.sidecar       # 期望没有 disabled 行(或 => false)
# 执行器状态正常(lead 裁定;任一不满足就不开窗 —— 否则 §B4「本锚有下单」必红, 换装会被误判失败)
grep "anchor done" ~/dl_quant_live/state/anchor_runs.log | tail -1  # 必须是本锚(N+0:2x)的一行且 rc=0
/usr/bin/python3 - <<'PYCHK'
import json, os, glob
L = os.path.expanduser("~/dl_quant_live/state/live")
w = json.load(open(f"{L}/watchdog/state.json")); e = json.load(open(f"{L}/watchdog/last_eval.json"))
r = [json.loads(x) for x in open(sorted(glob.glob(f"{L}/pilot_log/2*/anchors.jsonl"))[-1])][-1]
print("watchdog tripped_at", w.get("tripped_at"), "reduce_only", w.get("reduce_only"), "| last_eval tripped", e.get("tripped"), "triggers", e.get("triggers"), e.get("evaluated_utc"))
print("last anchors row nominal", (r.get("external_book") or {}).get("nominal_ts"), "opening_halted", r.get("opening_halted"))
PYCHK
# 期望: tripped_at None · reduce_only False · tripped False · triggers [](任何触发都不在, 含 §4-2 日止损)· 本锚行 nominal = 本锚且 opening_halted False
grep -E "4-2|DAY_STOP" ~/dl_quant_live/state/live/watchdog/ALARM.log | tail -2   # 当日有 §4-2 日止损生效记录 ⇒ 不开窗
/usr/bin/python3 $NCW/src/nc_handoff_check.py $MODELS/HANDOFF_deploy_s42.json $MODELS/P5_DEPLOY_MANIFEST.json $MODELS/slow2026.txt $MODELS/f10_live_s42_np.npz $RULING ; echo "rc=$?"   # HANDOFF_CHECK OK, rc=0
```
- **预核(2026-09-24 02:57Z,窗前,只读)**:
  - lead 在 26905a4b5 改过裁定文件的字节,又在 e6d9605ba 恢复成 b9c7a933d 的原字节。改动发生在 02:56:59Z,恢复在 02:57:21Z,都晚于 P1 / P2(02:39–02:42Z),所以 P1 / P2 不受影响。
  - 对工作树里的裁定文件重跑 `nc_handoff_check.py`:`HANDOFF_CHECK OK`,rc=0。
  - 工作树、HEAD、b9c7a933d 三处的裁定文件 sha 都是 053d50f4…,与包内副本 `$PKG/verdict/ruling.md` 字节相同。
  - 真 HOME 只读预检:`NC_INSTALL PREFLIGHT_PASS VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4…`,rc=0。
  - 收据在 `receipts/p0_3_prechecks_2026-09-24/`。W 开始时整节 §0.3 照样再跑一遍。

### 0.4 这次上线改变的书行为(交用户最后确认;§0.2 第 10 项)

2026-09-24 集成代理整理,用白话写。每条后面注明依据的文件。除第 9 条外,各条都从换装后的第一个锚起生效。

**背景**
- 这个版本的判词是 `VERDICT=NO_DEPLOY`:s42 在 B1 上对 NEW_S 差 −0.477 bps/日,30 日块区间 [−4.11, +2.52]。
- 这次上线是用户在判词之上放行 s42,`USER_OVERRIDE=053d50f4…`,不是判词通过(`docs/RULING_user_NC_s42_override_2026-09-24.md` §1、§4)。

**会改变下单结果的**

1. **两个打分模型都换掉。**
   - King 从 `8d79186b` 换成 `700d9e7b`,F10 从 `351ae26b` 换成 s42 的 `3d7d050f`。
   - 两个新模型都是在修正后的特征上重训的,训练方案与 NEW_S 相同。
   - 模型看到的最后一个训练标签:King 是 2025-12-22,F10 是 2026-01-07。
   - s2027 不上,也不作备选。
   - 依据:news2 `HANDOFF_deploy_s42.json`(e24231fb)、FREEZE §3-2、裁定 §4-1。
2. **成员只从加密币里选。**
   - 每锚打分的 400 名成员,不再包括代币化股票、商品这类 TradFi 永续。829 名轴上有 680 名算加密。
   - 可以持仓的仍是原来的 450 名。
   - 依据:DESIGN 开头「唯一例外」、FREEZE 修订 1 §3.2 的冻结规则、`P1_MEMBERS.json`。
3. **成员筛选加上「能交易、还活着」两道门;候选池改为逐锚从交易所名单生成。**
   - 过去 24 小时里一根真实成交 bar 都没有的名,不能当成员。
   - 候选池每锚取「交易所当前在交易的 USDT 永续 ∩ 829 名轴 ∩ 加密」,约 520 名,比现在的 450 名多约 70 名。
   - 多出来的名参加成员筛选和横截面排序,但仍然不能持仓。
   - 依据:DESIGN §A1(D1)。
4. **5 分钟收益不再截断,也不跨缺口。**
   - 过去单根 bar 的收益超过 ±30% 会被截到 ±30%,现在保留原值。
   - 缺口之后的第一根 bar,过去记的是跨缺口的收益,现在记为缺失。
   - 部署时,轴末以前的历史行换成训练重放的行,两边一致。
   - 依据:DESIGN §A3(D3)、FREEZE 修订 1 §2。
5. **资金费的结算周期和新鲜度改了。**
   - 结算周期按相邻两次结算的实际时差来判(1/2/4/6/8 小时),不再在不确定时默认 8 小时。
   - 最近 12 小时内没有结算的名,资金费特征一律当缺失。King、F10、FTRIM 三处用同一个规则。
   - 结算周期变短的名(例:ONEUSDT 从 8h 改成 1h)不再被旧周期的预测跳过。
   - 具名残余:某锚批量取资金费失败、回退到逐名取时,周期刚变短的名会晚一个旧周期。这种情况逐次记数。
   - 依据:DESIGN §A4(D10)、§A5(D11 / D13)、FREEZE 修订 2(778ba7324,A4 跳过规则修复)、平价门收据 `PARITY_RESULT_and_A4_skip_fix.md`。
6. **资金费动量腿的排序范围改了。**
   - 这条腿是书的主体,约六到八成权重,占比按锚滚动。
   - 它的排序范围只剩「能交易 ∧ 加密 ∧ 829 名轴 ∧ 12 小时内有新鲜资金费」的名。
   - 轴外的名不再进来,例:DOSUSDT、MARSCOINUSDT、PONSUSDT。
   - 依据:DESIGN §A6(D12)。
7. **特征计算的七项修正**(依据:DESIGN §B1–§B7):
   - D4:F10 的 82 列改存 32 位(过去 16 位),模型读到的数更精细;
   - D5:窗口统计改用 64 位累加,影响 King 的 X78 特征块;成员筛选用同一个修正;
   - D6:窗口里没有数据时,均值和标准差记为缺失,不再记 0 去参加排序;
   - D7:F89 趋势块换成稳定算法,并按整窗检查;窗内缺 bar 的名,这列记缺失;
   - D8:F89 的缺失判定修正 18 处。部分列的有效比例下降,最明显的 `dhi/dlo_8640` 从 0.82 降到 0.25;
   - D9:BTC 波动序列的窗口包含当前 bar;覆盖不足 95% 记缺失,不再回填。影响 5 列;
   - D14:流动性排名并列时用稳定排序。9 月的锚上,成员集与改前逐名相同。
8. **组合链换装后有一段过渡期。**
   - combo 的 kc / fc 两条链从现在的在役链接着算(α = 0.1,半衰期约 6.6 锚),头几十个锚里新旧成分混在一起。
   - 席位(King 与资金费腿的配比)仍按换装前、旧模型的腿收益历史计算,要约 900 锚才会被新历史替换完。
   - 用新历史重新播种席位是另一项书行为改动,需要用户另说一句(§S)。本次不做。
   - 依据:本手册 §B8、§S,DESIGN §A8。

**不改变下单结果、但会变的**

9. **执行器新增 BTC beta 对冲,先用 shadow 模式。**
   - shadow 只计算、只记录「假如对冲会下多少」,不下 BTC 对冲单。
   - 书、订单和循环状态与关闭时逐位相同,执行器套件 [Z] 证明了这一点。
   - 合计杠杆上限 2.5× 在 shadow 下不起作用。
   - 换装后两个锚的 shadow 验收都过,才切到 on;切 on 以后才开始下对冲单。对冲不在换模型的同一个锚里下单。
   - M3c 不过,就用 off,对冲不随发布上线,换装照常。
   - 依据:AMENDMENT_3 §2、`docs/IMPL_m3_beta_overlay_2026-09-23.md` §0 第 2–3 条与 §1.3(三档开关)、本手册 §B7。
10. **侧车停用。**
    - 侧车过去每锚用旧格式特征重算 F10,覆写 combo 的暖启动文件。停用后由 combo 自己写。
    - 两者今天只差 2.63e-8,没有可测的书效应。
    - 不停的话,新格式下侧车会崩溃,或把旧格式特征静默写进链里。
    - 依据:DESIGN §A7-5 (1)。
11. **页报、仪表盘、快照工具跟着新状态格式改。**
    - anchor_report 的守护检查从「3/3」改为「2/2」,侧车在跑时会告警。
    - regime_dash 加了一个空值保护;快照 / 平价工具改为按新的状态文件清单拷贝。
    - 这些都只影响监控,不影响下单。
    - 依据:DESIGN §A7-5 (2)–(4)。

**不变的**
- 总杠杆 gross 2.0。
- 可持仓的 450 名。
- 成员数 400,生产发布门(字面 380 名)。
- 组合与席位的规则本身。它们的输入(模型分数、资金费状态)按上面几条变了。
- 执行器的逐名止损、看门狗阈值、maker 优先执行。

### 0.5 席位差距量化(用户确认 §0.4 之后补充;§0.4 原文不改)

lead 2026-09-24 要求,只读、不调场所。收据 `receipts/seat_quant_2026-09-24/SEAT_QUANT.json`,装置 `devices/nc_seat_quant.py`(41106a29)。

**席位怎么算,「约 900 锚」从哪来**
- 生产者与 combo 用同一个公式:取 `leg_returns_live.json` 三条腿(king / rev24 / fund)**最近 900 条**逐锚收益,各算均值 / 标准差,负值截成 0,再归一。
- 这是等权的矩形窗,没有衰减;combo 再去掉 rev24,在 king 与 fund 之间重新归一(掩码席位)。
- 代码行:
  - 生产者 `shadow_loop_v3.py`(treeNC5)L783–789;
  - combo `combo_stage.py` L61–69、掩码 L282–283;
  - 窗长 `shadow_bundle/config.json` L1453 `msharpe_look: 900`;
  - 每锚追加一条收益 L765(只在上一锚恰好早 4 小时时追加);
  - 状态文件保留 950 条 L426–428。
- 换装之后,每个锚挤掉一条旧口径收益、加入一条新口径收益。n 个锚之后,窗里还剩 (900 − n)/900 是旧的。
- 900 锚 = 150 天(每天 6 锚)。跳过的锚不追加,实际还会更长。

**同一锚上的席位(2026-09-19 00Z,回放能覆盖的最后一锚)**
- 实盘:king 0.3834 / fund 0.6166(`~/wide_shadow/state/target_combo/1789776000.json` 的 `w3_masked`)。
- NC s42 回放:king 0.3655 / fund 0.6345。
  - 来源:news2 `work/legs.npz`(sha 9ee5886f…,即 HANDOFF 谱系里的 legs)第 10332 行(E_ts = 1789776000)的 `WL` = [0.2878, 0.2125, 0.4997],掩码后得到上面的值。
  - 这份腿收益就是 §S 播种要用的「NC 口径腿收益截至轴末」。
- 差:实盘的 king 席位高 +0.0179。
- 09-02 到 09-19 重叠的 101 个锚上,实盘减回放的 king 席位:均值 +0.016,范围 [−0.066, +0.069]。实盘这段历史包含 09-05 的席位播种。
- 部署时点:实盘最新 09-24 00Z 为 king 0.4003 / fund 0.5997(`target_combo/1790208000.json`)。回放轴末是 09-19 00Z,**覆盖不到 09-24**。以回放最后一锚为参照,差为 +0.0348。

**对持仓的影响**(只换席位。输入固定为 NC s42 回放在 09-19 00Z 的 King 秩、F10 s42 分数、资金费秩、qv 门与 rn8,公式抄 combo_stage)
- 各链内按暴露算的 king 份额:
  - kc 链:实盘席位 35.8%,回放席位 34.1%(差 1.7 个百分点);
  - fc 链的 F10 份额:37.2% 对 35.5%。
- 目标差:两种席位下的 combo 目标(0.55 kc + 0.45 fc,每条链归一到 gross 1)L1 差为 **2.9% gross**,有 1 个名翻号。
- 首锚持仓差:链是 EMA,α = 0.1,首锚只移动目标差的 1/10,即约 **0.29% gross**。
- 以部署时点的实盘席位(09-24)对回放 09-19 的席位:目标差 5.8% gross,首锚约 0.58% gross,4 个名翻号。
- 参照:实盘席位自己从 09-19 到 09-24 的变化,就造成 2.9% gross 的目标差。
- **没有算的,不估**:
  - 回放在部署锚上的席位:回放轴末是 09-19,§S 要接的「新生产者在实盘快照上逐锚产出的腿收益」这段没有产物;
  - 部署锚本身的输入:这里用的是 09-19 的回放输入;
  - EMA 的 band(0.00025)、执行器 reshape、LIVE_MASK 离场规则:都依赖状态,没有施加。上面的 α 乘积不是这些非线性步骤之后的持仓差。

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

**P1 打包**(news2 交付部署模型之后;**已做**,2026-09-24 02:39Z):
```
/usr/bin/python3 $NCW/src/nc_handoff_check.py $MODELS/HANDOFF_deploy_s42.json $MODELS/P5_DEPLOY_MANIFEST.json $MODELS/slow2026.txt $MODELS/f10_live_s42_np.npz $RULING --out $MODELS/HANDOFF_CHECK.json ; echo "rc=$?"   # HANDOFF_CHECK OK
$PYP $NCW/src/nc_package.py $PKG --tree $NCW/treeNC5 --extras $NCW/release --king $MODELS/slow2026.txt --f10 $MODELS/f10_live_s42_np.npz --crypto $CRYPTO --label NC_RELEASE \
  --export-manifest $MODELS/P5_DEPLOY_MANIFEST.json --ruling $RULING ; echo "rc=$?"
$PYP $NCW/src/nc_install.py preflight $PKG ; echo "rc=$?"          # NC_INSTALL PREFLIGHT_PASS VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4…
```
- 模型从 pod2 `/dev/shm/news2_2026-09-23/{deploy,receipts}/` 拷来后,先在本机重算 sha 再用。sha 一律取自 HANDOFF,不从消息里抄。
- `nc_handoff_check.py` 逐项核对,任一不符就拒绝(exit 3):
  - HANDOFF 里记的 manifest sha 等于 manifest 文件的 sha;
  - FROZEN_VERDICT 等于 manifest 的 VERDICT;
  - HANDOFF 的 USER_OVERRIDE、manifest 的 USER_OVERRIDE、裁定文件的实测 sha 三者相同;
  - seed 为 s42;
  - HANDOFF、manifest、本机文件三处的钉与导出文件 sha 相同。
- `nc_package.py --export-manifest --ruling`:
  - 核对 manifest 的谱系、seed s42、导出文件 sha 与钉等于 `--king` / `--f10` 的 sha,且 USER_OVERRIDE 等于裁定文件的实测 sha,不符就拒绝;
  - 合同写入 `verdict` 块与顶层 `VERDICT` / `USER_OVERRIDE` 原文;
  - 把 manifest 和裁定拷进 `$PKG/verdict/`,供 `nc_install.py` 从包内复核。
- 没有 `verdict` 绑定的合同,`nc_install.py` 在真 HOME 上拒绝(演练格 NU)。
- 结果:
  - `INSTALL_CONTRACT.json` sha 00238e4b…;
  - 执行器钉等于 HANDOFF 的 `executor_pins`,逐字相同(King 700d9e7b…、F10 3d7d050f…);
  - 预检 `NC_INSTALL PREFLIGHT_PASS`,rc=0;
  - 收据在 `receipts/p1_p2_real_2026-09-24T0240Z/p1_package/`。

**P2 用真包做安装演练**(假 HOME;静默窗内、剩余 ≥ 15 分钟,由启动脚本自检;**已做**):
```
bash $NCW/src/run_install_rehearsal_p2.sh $MODELS ; echo "rc=$?"
```
- 启动脚本先核对三样输入,再跑演练:
  - treeNC5 PATCH_RECEIPT 的 sha(3135cf8b…);
  - 种子包 sha 等于 `NC_SEED_PACK.json` 的记录(600d760e…);
  - HANDOFF 核对(同 P1)。
- 快照取最新一个带 COMPLETE 的;King 与 F10 的 sha 取自核对结果,即 HANDOFF。
- 然后跑 `test_nc_install_rehearsal.py`,带 `--king/--king-sha/--f10/--f10-sha/--export-manifest/--ruling`。
- 格:
  - P0:合同钉等于声明 sha;
  - V0:合同 VERDICT / USER_OVERRIDE 等于 manifest,且 USER_OVERRIDE 等于裁定文件的实测 sha;
  - P1、N1、A1;
  - V1:安装收据顶层写有 VERDICT / USER_OVERRIDE;
  - R1、A2、N2、R2;
  - NK、NF:声明错的钉 ⇒ 拒绝;
  - NR:裁定文件字节不同 ⇒ 打包拒绝;
  - NU:未绑定的合同在「真 HOME」上预检 ⇒ 拒绝。
- 结果:
  - **`TEST_NC_INSTALL_REHEARSAL REAL_PACKAGE_PASS`,14/14,rc=0**(02:40:23–02:42:19Z);
  - 快照 1790208000;
  - 演练包与 $PKG 的候选 sha、基线 sha 都逐个相同;
  - 收据在 `receipts/p1_p2_real_2026-09-24T0240Z/p2_rehearsal/`。
- 同一装置先在合成 manifest 与替身模型上跑过一次(`MACHINERY_PASS` 14/14,02:32–02:38Z,`…/device_test_synthetic_manifest/`)。那一次只认证装置本身。

**P3 执行器候选干跑**(**必做**,lead 裁定;静默窗,约 20 分钟):
- 按 A4 的条件做出候选检出:M3 合入、anchor_report 补丁、生产者发布归档、`nc_exec_config.py` 改好钉与配置(shadow、2.5、nc_v1),并 rsync 实盘 state。
- 不运行 `safe_commit`,改为在候选检出里运行 `bash ops/run_acceptance_offline.sh`,只看结果、不提交、不推送。
- 读源码普查的结论(2026-09-23,候选 = b66257b + 5b3d89c + 补丁):
  - 电池里读 `booster_sha_pin` / `f10_sha_pin` / target_live 的套件只有 5 个:`tests_external_book`、`tests_beta_overlay`、`tests_gross_ladder_retired`、`tests_per_name_stop`、`tests_arm_margin_scope`。
  - 它们比较的都是**自己在临时目录里造的**目标文件与夹具钉,不读检出里 book.json 的钉,也不读生产者的真实文件。
  - 离线沙箱允许读 `~/wide_shadow`,但没有套件去读它。只有 fixture 构建器 `build_fixture_0913_08z.py` 读,它不在电池里。
  - 所以换钉本身不会让任何套件变红。
- 真正的未知是另一件事:全电池从来没有在检出里 `beta_overlay.mode="shadow"` 的配置下跑过。IMPL_m3 §7 写明:全电池只在 off 下跑过,shadow / on 只跑过 5 个套件。
  - 另外约 20 个套件读检出里的真实 book.json(例如 `tests_external_book` 的 BASE_BOOK)。
  - P3 就是为了在部署前实测这一点。
- 判定:全绿 ⇒ A4 可按原样执行;有红格 ⇒ 读逐格日志归因,交 lead 裁定,**不放宽判据**。
- **已取得(2026-09-23 21:00:50–21:18:34Z)**:`ACCEPTANCE: ALL GREEN (163/163 suites exit 0)` / `OFFLINE_ACCEPTANCE_EXIT: 0`;这是首次在检出配置 mode=shadow 下跑的全电池(`receipts/p3_2026-09-23T2100Z/`,2bec89bb3)。
  - 当时的候选归档用的是 treeNC4 的 PATCH_RECEIPT,钉是替身。执行器侧不含生产者代码,换成 treeNC5 不影响结论;部署当晚 A4 的 safe_commit 电池会在真归档、真钉上再跑一次。

**P4 前置门收据**:把 §0.2 清单第 1–9 项的收据路径和 sha 抄进 `$BK/PREREQS.md`。第一行照写 `VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b`(用户放行,不是判词通过)。

## A. 窗口 W

> **Same-window order for the vendored upstream (added 2026-09-25, E-0925-D; applies to every later executor release that changes the files in drift_gate's A_SET)**: first, inside the window, `git cherry-pick` the held patch into the research repo's `multi_asset/engine/live/` (this time: 8bde2f8dc) → then run the candidate battery in the candidate checkout (drift_gate must be green) → then deploy the executor. **Outside a release window, never commit these files in the research repo**: the deployed executor's drift_gate reads the working tree of that directory directly, so any such commit turns the deployed battery red (measured, E-0925-D). On rollback, run it in reverse: roll back the executor first, then `git revert` the upstream patch.

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
$PYP $NCW/src/nc_deploy_fetch.py $NCW/treeNC5 ~/wide_shadow/state $BK/fetch_list.json $(python3 -c "import numpy as np;print(int(np.load('$SEEDPACK')['axis_end']))") $BK/live_pack.npz ; echo "rc=$?"
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
$PYP $NCW/src/nc_seed_state.py $NCW/treeNC5 $SEEDPACK ~/wide_shadow/state $BK/seeded --live-pack $BK/live_pack.npz --fetch-list $BK/fetch_list.json ; echo "rc=$?"
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
- **版本实测 A3**(lead 2026-09-24,用户要求「绝不能跑错代码版本」;`devices/nc_version_probe.py` 33cd1d15,只读;逐项打印实测值与对照值,不符的点名列出;正负对照见 `receipts/version_probe_controls_2026-09-24/`):
  ```
  /usr/bin/python3 $NCW/src/nc_version_probe.py --out $BK/VP_after_a3.txt after-a3 $PKG ; echo "rc=$?"      # 17 个目的地逐个重算 sha == 候选值;末行必须 VERSION_PROBE after-a3 OK n=0
  ```
  不符 ⇒ §R-A。

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
(cd $XC && bash ops/safe_commit.sh "NC release: producer_contract nc_v1 + pins (booster 700d9e7b / f10 3d7d050f) + M3 beta_overlay shadow 2.5 + anchor_report daemon contract; VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b (user release over the verdict); quant_research DEPLOY_producer_new_contract_2026-09-23 A4" \
   config/book.json ops/anchor_report.py live/tests_anchor_report_builder.py ops/producer_release/20260923_nc/INSTALL_CONTRACT.json ops/producer_release/20260923_nc/PATCH_RECEIPT.json) ; echo "rc=$?"
NEWSHA=$(git -C $XC rev-parse HEAD); echo $NEWSHA
/usr/bin/python3 ~/cc_tmp/lead_deploy_20260923/ff_running_tree.py $NEWSHA ; echo "rc=$?"   # 持 state/anchor.lock 快进运行树
git -C ~/dl_quant_live rev-parse HEAD ; git -C ~/dl_quant_live rev-parse origin/main ; echo $NEWSHA   # 三方相同
git -C ~/dl_quant_live status --porcelain --untracked-files=no | grep -v '^.. \(state\|logs\)/' ; echo "上一行必须为空"
/usr/bin/python3 $NCW/src/nc_version_probe.py --out $BK/VP_after_a4.txt after-a4 $PKG $NEWSHA --beta-mode shadow --max-combined 2.5 ; echo "rc=$?"   # 版本实测 A4
```
- **版本实测 A4**:打印运行树 HEAD、origin/main(本地引用与 GitHub ls-remote)、NEWSHA 三方;`git show NEWSHA` 的文件清单必须恰好是 pathspec 那 5 个;运行树 book.json 的 booster_sha_pin、f10_sha_pin、beta_overlay.mode、beta_overlay.max_combined_leverage、external_book.producer_contract 五个值,且字节等于 NEWSHA 里提交的 book.json。末行必须 `VERSION_PROBE after-a4 OK n=0`;不符 ⇒ 停,交 lead(已快进则按 §R-B)。
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
/usr/bin/python3 $NCW/src/nc_version_probe.py --out $BK/VP_after_a5.txt after-a5 $PKG $BK/install/NC_INSTALL_RECEIPT.json ; echo "rc=$?"   # 版本实测 A5
```
- **版本实测 A5**:
  - 生产者(com.hsy.shadowloop)与 combo 守护(com.hsy.combolive)的进程启动时刻必须晚于 A3 apply 的 `completed_utc`;
  - 按进程实际运行的路径(lsof 取 cwd,加上 argv;combo 守护每锚在自己的 cwd 里跑 `combo_stage.py`)重算 sha,必须是 a68c7a5f… 与 363dd8c8…;
  - 侧车:未加载、已 disabled、没有进程。
  - 末行必须 `VERSION_PROBE after-a5 OK n=0`;不符 ⇒ 停,交 lead。

## B. 换装后验收(锚 N+4 与 N+8;只读)

**B0 版本实测**(首锚;执行器 N+4:24 读取并记下 anchors 行之后):
```
/usr/bin/python3 $NCW/src/nc_version_probe.py --out $BK/VP_first_anchor_<A>.txt first-anchor $PKG <A> ; echo "rc=$?"
```
- 打印并核对:
  - target_live/<A>.json 的 booster_sha / f10_sha(f10_sha 是 combo 按实际载入的字节算的);
  - shadow_log 本锚 signal 行的 booster_sha;
  - MANIFEST,以及磁盘上两个模型的 sha(生产者启动时逐项校验 MANIFEST,不符就拒启动);
  - generation.json 的 schema_version、锚与签名文件集:NC 合同是 5 个文件。它没有显式的合同版本字段,合同由文件集识别;
  - 执行器 anchors 行 external_book 的 ok / reason 与读到的 sha,必须等于 book.json 的钉;
  - anchor_runs.log 本锚没有 REFUSED / HOLD。
- 末行必须 `VERSION_PROBE first-anchor OK n=0`;不符 ⇒ §R-B,交 lead。

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
- `nc.used_weight_1m_max` < 1200;`fund_bulk_ok` 为 true;`nc.fund_per_symbol` 很小(E3 在实盘快照锚上为 2);
- **具名残余(A4 修复的剩余部分)**:若本锚 `fund_bulk_ok` 为 false(批量 10 页全满或失败,回退逐名),按预测周期跳过的规则仍然生效,缩短了结算周期的名会滞后一个旧周期。逐事件计数写进首锚验收与月度报告,格式同冻结修订 1 §2-4。
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
| `devices/nc_package.py` | 部署包与安装合同;`--export-manifest --ruling` 绑定判词与放行(8c5fbd1d) | 安装演练 P0 / V0 / NR;`receipts/p1_p2_real_2026-09-24T0240Z/` |
| `devices/nc_handoff_check.py` | HANDOFF ↔ manifest ↔ 本机模型 ↔ 裁定 sha 的逐项核对(db14dea2) | 正例 OK;两个负例(换错 F10、换错裁定)exit 3 |
| `devices/run_install_rehearsal_p2.sh` | §P2 启动脚本(静默窗自检 + 输入 sha 断言) | `receipts/p1_p2_real_2026-09-24T0240Z/p2_rehearsal/` |
| `devices/nc_install.py` | 预检 / 安装 / 回滚;预检先从包内复核判词块,真 HOME 拒未绑定合同;收据顶层写 VERDICT / USER_OVERRIDE(4ec71b91) | `receipts/install_rehearsal_machinery/` 7/7 MACHINERY_PASS;真包 `receipts/p1_p2_real_2026-09-24T0240Z/` 14/14 REAL_PACKAGE_PASS |
| `devices/nc_seed_state.py` | 播种新状态 | `receipts/TEST_NC_SEED_FUNDING_GATE.log` 4/4 |
| `devices/nc_fetch_list.py` / `nc_deploy_fetch.py` | 取数名单 / 实时回填包 | F-1(`nc_fetch_test.py`)实测后补 |
| `devices/nc_downgrade_state.py` | 状态降级 | F-2 演练(e1–e3) |
| `devices/nc_exec_config.py` | 执行器配置编辑(正向);回滚 = 逐字节恢复备份并核 sha | 正向 5 例;恢复:错 sha 拒、当前钉不符拒、恢复后与换装前逐字节相同 |
| `release_extras/` | combosnap / comboparity / regime_dash | `receipts/release_extras/` 8/8、4/4,新旧格式平价实测 |
| `release_executor/` | anchor_report 守护合同补丁(基于 5b3d89c) | 套件 23/23 |
| `devices/nc_timing_gate.py` / `test_nc_rollback_rehearsal.py` / `nc_parity_gate.py` | §E3 / §F-2 / 平价门 | 正式收据待补;空跑见 `receipts/dryrun_2026-09-23/` |
