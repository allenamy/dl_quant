# 重训战役 2026-09 · 脚本清单(单一真相源 = 本目录; 机器上只放运行副本)
> PREREG: docs/PREREG_retrain_addendum_v2main_2026-09-01.md(sha c24b8d2f8567) + RUNBOOK_monthly_retrain_2026-09

## king/bundle 轨(RUNBOOK 步骤1-4)

| 脚本 | 跑在 | 输入 | 输出 | 门 |
|---|---|---|---|---|
| pod_extend_vision.py(镜像原件) | pod | Vision daily zips 08-22..31 | wide_multisrc/{klines5m,premidx}_daily | 404=新币缺日正常 |
| pod_merge_cache_ext.py(派生 de7a0661) | pod | fresh缓存 + 新zips | dlnative..._ext.npz | **重叠窗逐位 exact_eq≥0.999 → 实测 1.000000 PASS** |
| fund_pull_pod.py(新作) | pod(独立IP, ≤3.5req/s) | /fapi/v1/fundingRate 全史 | fund_aug.json.gz(AUG全量形态) | V-A 对实盘账本 23,146/23,147 偏差 0.00e+00 PASS |
| **pod_fund_zips.py(新作 09-01)** | pod | Vision monthly fundingRate zips 2019-09..2026-08(真 interval 列) | wide_multisrc/funding/SYM/YYYY-MM.zip | 修 ema_v1/v2 normfix 污染(见偏差D3) |
| pod_panel_ext.py(镜像原件) | pod | ext缓存 + funding zips + fund_aug + zload | wide_panel_4h_v2ext.npz | 内建自检 7列 + **pod_gate1_full.py 全列版** |
| **pod_gate1_full.py(新作 09-01)** | pod | v1面板 + v2ext面板 | gate1_full.log | **门① RUNBOOK 冻结口径: 全部 f_* 列重叠锚 corr≥0.999** |
| pod_fea_ext.py(镜像原件) | pod | ext缓存/面板 | wide_fea_v2ext.npy + meta | 同构校验(king 82列特征族) |
| **pod_export_bundle_v3.py(派生装置 09-01)** | pod | wide_fea_v2ext + v2ext面板 + funding zips + live_pins + slow_scorer_v3base | shadow_bundle_v3.tar.gz | 门②(2024/25折IC \|Δ\|≤0.004, Δ3新增) + 门③(ic26 vs 0.0571 ±0.006) + 守卫带 2.27..2.57 |
| live_pins.json(自在役bundle config 抄录) | pod | — | symbols_live 450 + keep_names 78 钉死 | Δ4/Δ5 断言输入 |
| slow_scorer_v3base.json(基线记录) | pod | mirror slow_scorer.json(git) + 在役 provenance | 门②③基线 | 口径已验: scorer 折构造与导出装置逐字同 |

## V2MAIN/f10 轨(PREREG addendum §A)

| 脚本 | 跑在 | 输入 | 输出 | 门 |
|---|---|---|---|---|
| **pod_dlw_targets_ext.py(sed移植, diff=3路径行)** | pod | ext缓存 + v2ext面板 | /workspace/dlw_ext/data/dlw_targets.npz | 内建对齐自检 + **pod_gate_dlw_ext.py** |
| **pod_gate_dlw_ext.py(新作 09-01)** | pod | 旧/新 targets | — | 重叠锚 members 全等 + y4s/YRZ/qvk corr≥0.999 |
| **pod_dlw_features_ext.py(sed移植, diff=1路径行)** | pod | targets_ext + ext缓存 + v2ext面板 | dlw_ext/data/dlw_fea82.npz | 结构断言 max_feature_row==E |
| **pod_f8_build_ext.py(sed移植, diff=3路径行)** | pod | targets_ext + fea82_ext + ext缓存 | f8_ext/data/f8_fea89.npz | build 阶段结构断言 |
| legs_ext(待作, bundle v3 后) | pod | v3 slow_pred_pinned + v2ext面板 + targets_ext | f10v2_legs_ext.npz | 旧行逐字保留+新锚拼接; 重叠公式重建 corr≈1 验证 |
| f10_refit_pod.py(卷上原件) | pod GPU | 171特征ext + legs_ext + 冻结配方 | f10 s42/s2027 .pt + np导出 | 门V1 np≡torch / V2 回放不退化 / V3 泄漏仪器 |

## 偏差记录(09-01, 全部已中和)

- **D1 覆盖偏差**: 首轮链用默认 env ⇒ `wide_fea_v2ext.npy`/`wide_panel_4h_v2ext.npz` 在 pod 上就地覆盖八月代(违 RUNBOOK "_v3 不覆盖")。在役零影响(八月正典=本机在役 bundle+MANIFEST 完好, pod 旧件可由 v1面板+旧缓存重造)。门②③基线改从在役 bundle/git 记录取(slow_scorer_v3base.json)。
- **D2 宇宙旁路**: 原导出脚本 `symbols_live = glob(funding 目录)`, 目录已播 829 ⇒ 原样跑=宇宙刷新静默搭车(违 PREREG §B 分离部署)。v3 装置 Δ4 钉死 450。
- **D3 interval 推断污染**: funding zip 缺失时 interval 全靠时间差推断(首行默认8; Binance 2023+ 多币 8h→4h→1h 切换期必错), f_fund_iv exact 99.96% → EMA 递归放大 → f_fund_ema_v1 corr 0.9796 红(门①全列版捕获; 内建 7 列门看不见)。修复=pod_fund_zips.py 拉真 interval 列, AUG 只补尾。**教训: 门必须按 RUNBOOK 冻结口径全列跑, 装置内建自检≠门。**
- **D4 RUNBOOK step1 替代**: jp_fund_aug.py(funding 尾巴)被 fund_pull_pod.py(全史)替代 — 同产物形态, 验证更强(V-A 0.00e+00 + 与 zip 通路 216万格 corr 1.000000 双向对源)。

**运行副本位置**: pod:/workspace/(scp 自本目录); jpline:/mnt/storage/private/work_hsy/。机器上文件 = 副本, 修改必须回写本目录并重新分发。

## 守卫红归因(09-01 下午, 干预实验闭环)

- **现象**: 门②③ IC 全绿, 守卫 replay 夏普 1.92 ∉ [2.27,2.57] → 装置拒绝换版(正确行为)。
- **对账**(pod_guard_reconcile.py): v3 腿收益 vs 八月 bundle leg_returns 原件 — rev24 corr 1.000000 精确, king 0.89-0.92(LGBM 非确定性, 折 IC 门绿), **fund 0.86-0.94 全史散开** → 分歧全在 funding 口径。
- **干预实验**(RECON_PANEL=v1 正典): 正典面板跑同代码 — fund 腿 vs 八月 **corr 1.000000 逐位** + 守卫 2.49 带内 ⇒ **八月装置=正典忠实; 我的 v2ext ema_v1(对正典 0.9997)才是偏离仪器**。0.03% 格差经秩变换放大 ≈ 0.4 夏普。根因: iv 换档窗 0.04% 格差(zip 逐事件真值 vs 正典口径)经 normfix EMA 递归扩散。
- **教训(D5)**: **corr≥0.999 列门可以放行载荷性偏差; 秩/递归下游必须有行为级守卫**(守卫层这次按设计工作)。
- **修复**(pod_panel_splice.py): ≤正典末锚全列逐字=正典; 尾 96 锚 EMA 族以正典末行为状态种子续算(唯一正典连续构造); kline/fund_now/iv 尾部用 ext(parity 1.0 zip 真值)。断言: cut 行逐位==正典, 尾部 kline==ext。产物 wide_panel_4h_v3splice.npz + fund_state_canoncont.json(bundle §3 EMA 种子覆盖, EMA_STATE_JSON env)。
- **波及面**: f10 轨 targets/fea82 只吃 v0(parity 1.000000 精确)不受影响; legs_ext 新锚 ZFD 改吃 splice 面板(旧行=八月原件本就正典逐位)。

## f10 输入链收据(09-01 下午)
- targets_ext(splice 面板): y4s/qvk corr 1.000000 exact 1.0; YRZ 0.9923→**0.999910**(D5 修复生效); 内建对齐自检 @0 +0.972 ≫ 邻锚。
- **member 单锚豁免(取证型)**: 2026-01-15 08Z 第400席 ACXUSDT↔PROMPTUSDT, 两名 qvk **逐位相等 8.171753**(NTOP 精确平位, numpy 非稳定 argsort 机器差, 零信息)。门加原则性豁免: 仅当交换双方 qvk 逐位相等判 TIE_EXEMPT; 其余仍 REAL_DIFF 红。

## f10 重训运行记(09-01 晚)
- legs_ext: Z24/ZFD 公式自验证 exact 1.0000(逐位复现八月原件); WL max|Δ| 4.8pp(PRED 代际允差记录); copy 10,086 + new 120。
- **torch 2.4.1+cu124 → 2.11.0+cu128(硬件强制: RTX PRO 4500 Blackwell sm_120, 旧轮只到 sm_90)**; 数值代差由门 V2(回放 CI)终审, 版本入 config。
- 双种子 SEED=42/2027 并发 @pod GPU(5.4GB/85%), 输入=targets/fea82/fea89/legs 全 splice 口径(门收据前节)。

## 门V3 案卷(09-01, 字面红+对账受据, 待用户裁定)
- 字面: "谱峰在 k=0" — 新 preds 双种子峰@−1(−0.24/−0.25)⇒ **字面 FAIL 照记**。折外泄出格点=0 ✓。
- 对账(同仪器测旧代): 旧 s42 k−1=−0.2484/新 −0.2375, 全谱逐点重合; 未来侧 k≥+1 两代同为 +0.017→+0.005→~0 因果衰减。
- 结论: 峰@−1 = 反转载荷分数的家族属性(**在役代同样过不了字面判据**); 判据措辞系从特征对齐谱误借。重建无新泄漏证据充分。
- 处置: 不自行改判据; 提请裁定修订为「未来侧 k≥+1 无峰 且 谱形与在役代一致 且 折外泄出=0」。裁定前 f10 不换版。

## 门V4 收据(09-01 傍晚, 双半门 PASS)
- king 半门(jp_king_v4.py, 数学=导出装置§①逐字, jpline conda env): 三折 jpline vs pod IC Δ=±0.0000(0.0548/0.0630/0.0584 逐位同帧)。
- np 半门(jp_v4_np_check.py): jpline 重算 vs pod 样本 30k 行 spearman 1.0000000 maxabs 2.78e-16。
- f10 门线终榜: V1✅(1e-7) V2✅(CI −0.009/−0.030 ≥ −0.10) V3=字面红+判据缺陷案卷呈裁定 V4✅(0.0000/1e-16)。裁定前 f10 不换版。
