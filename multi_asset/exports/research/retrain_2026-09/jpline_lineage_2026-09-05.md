# jpline 仪器血统全图 — 从源码与在库收据重建(pod2 移植用)

> **创建:** 2026-09-05 | **Session:** review_caliber teammate (lineage inventory) | **状态:** READ-ONLY 盘点完成, 未改动任何文件, 未 ssh | **作废条件:** 任一被引脚本改动(以 git blame 为准); 或 jpline 恢复后用原件复核推翻某条 INFERRED

**范围**: 重建「产出 2026-08-21/22 宽书回测数字的 jpline 仪器」的完整血统, 使其能在 pod2 上从源码重建, 零泄漏、零 simple/log 目标分歧。
**证据规则**: 全部来自 `/Users/haosiyu/Desktop/quant_research`(branch `multi-asset-v2`)git-tracked 文件。每条断言带 `文件:行`。凡标 INFERRED 的均注明来源与未证部分。

---

## 0. 三条必须先知道的结论(会改变重建计划)

1. **08-21/22 的装置口径本来就是对的。** `pod_stop_arms_v3.py` L76 与 `w2_wide_replay.py` L80 都是 `yv = np.nan_to_num(y4[i, m], nan=0.0)` — **原始 y4, 无任何 expm1**。`expm1` 只作用于报价额 `qvk`(`pod_stop_arms_v3.py` L59, `w2_wide_replay.py` L63)。E-0904-F 在 `docs/ERROR_LEDGER_2026-08-20.md` L397 写的「pod 原始回放(nets_histv2)同法」**与在库代码矛盾, 代码收据胜**(同一判断见 `review_caliber_wf/wf_results_all.json` L521 / L1607 / L1696)。⇒ 重建不需要为 08-21 数字做口径修正。

2. **08-21/22 的书是三腿, 没有 F10 腿。** `pod_stop_arms_v3.py` L18 只载 `slow_pred_hist_oos.npy`; `w2_wide_replay.py` L22 同。F10/V2MAIN 是 w10 家族才引入的(`w10_universe.py` L92-95, 受 `PHI>0` 控制)。⇒ 把 08-21 数字当「combo(含 V2MAIN)」比较是错的形态对照。

3. **两仪器差距的唯一剩余自由度 = king 训练起点。** 同锚同形态同口径下(`review_caliber_wf/combo_recheck/pod_armA_vs_0821.out`), 2026 一致到 +0.034, 2024/2025 差 −0.258/−0.342, 2022-23 差 −1.86/−1.14 且那两年 pod king 全 NaN。这就是 E-0905-A: 08-21 仪器 king 从 2020 训练, 在役 king 从 2022 训练。

---

## 1. 数据血统总图(阶段 → 脚本 → 输入 → 输出 → 该阶段口径 → 数据在哪台机器)

所有脚本路径相对 `/Users/haosiyu/Desktop/quant_research/`。全部已核 **git-tracked**。

| # | 阶段 | 脚本 | 输入 | 输出 | 该阶段口径 / 关键定义 | 数据位置 |
|---|---|---|---|---|---|---|
| 0 | 宇宙符号轴 | `multi_asset/exports/research/runpod_scripts/workspace_mirror/pod_dl_wide.py` L4-16 | S3 列 `data/futures/um/monthly/klines/` 前缀 | `panel_symbols_wide.txt` | 全部 `*USDT` 排序去重 → `\|` 连接 | **已入库**: `.../workspace_mirror/panel_symbols_wide.txt`, 实测 **829** 个符号, 首五 `0GUSDT / 1000000BOBUSDT / 1000000MOGUSDT / 1000BONKUSDT / 1000BTTCUSDT` |
| 1a | 5m zips 2022+ | `.../workspace_mirror/pod_dl_klines.py` L5, L8, L15, L20 | data.binance.vision monthly + daily | `/workspace/klines5m/<S>/<S>-5m-<期>.zip` | 原始 OHLCV | pod(可重拉) |
| 1b | **5m zips 2020-2021** | `.../workspace_mirror/pod_hist_dl.py` L7-17 | 同 CDN, 仅 monthly | 同树 + `wide_multisrc/funding/<S>/<YYYY-MM>.zip` | 原始 | **jpline 唯一副本(8 GB), 但可重拉 — 见 §7** |
| 1c | funding zips(含真 interval 列) | `multi_asset/exports/research/retrain_2026-09/pod_fund_zips.py` L9-11 | `.../monthly/fundingRate/` 2019-09..2026-08 | `wide_multisrc/funding/<S>/<YYYY-MM>.zip` | 原始 rate + `funding_interval_hours` | pod |
| 1d | funding API 尾巴 | `retrain_2026-09/fund_pull_pod.py` | `/fapi/v1/fundingRate` | `fund_aug.json.gz` | `{rates, intervals}` | pod |
| 2 | **5m 缓存** | `retrain_2026-09/pod_build_wide_ext.py` L10, L26, L28-34, L44-46 | `/workspace/klines5m` | `EXT_OUT`; 2020 起时 = `dlnative_5m_wide829_f16_hist.npz` | ch0 = `np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3)` **float16 简单 5m 收益**; `k['ts'] = open_time + 5min` ⇒ **行 ts = bar 收盘时刻** | jpline `probe_artifacts/f1/dlnative_5m_wide829_f16_hist_f1.npz` |
| 2b | 缓存增量合并 | `retrain_2026-09/pod_merge_cache_ext.py` L24, L27, L46-54, L56-58 | fresh 缓存 + 新 zips | `..._ext.npz` | 公式逐字同 L2; 平价门 `exact_eq >= 0.999` L54 | pod |
| 3 | **4h 面板** | `retrain_2026-09/pod_panel_ext.py` L14, L32, L57-58, L63-166, L168-170 | 缓存 + funding zips + `fund_aug.json.gz` | `PANEL_OUT`; 08-21 用 = `wide_panel_4h_hist_v2.npz` | **`Y4 = (CS_r[E+48] − CS_r[E])` = 行 [E, E+47] 的 48 根简单 5m 收益之和**(`cs()` L18-20 带前导零行); `Y4[y4n<46]=nan` | jpline `pod_backup_2026-08-21/` |
| 3-alt | 早期 hist 面板(**未被 08-21 使用**) | `multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-21/pod_panel_wide_hist.py` L57, L109, L111 | 同 | `wide_panel_4h_hist.npz` | Y4 同式; **只有 `f_fund_now`/`f_fund_ema`, 无 `f_fund_iv`/`f_fund_ema_v1`** | 已被 §3 取代 |
| 4 | **特征面板** | `.../devices_2026-08-21/pod_fea_wide_hist.py` L11, L27-28, L38, L48-62, L64-69, L88-90 | hist 缓存 + hist 面板 | `wide_fea_hist.npy` + `wide_fea_hist_meta.npz` | meta `y4` = `CS["ret5"][0][E+48] − CS["ret5"][0][E]` **与面板 Y4 逐字同式**; 82 列 = 40 值 + 40 秩 + `fund_ema` + `fund_now` | jpline |
| 4b | 生产同构件 | `retrain_2026-09/pod_fea_ext.py` L34, L48-52, L63-64, L83-84 | ext 缓存 + v2ext 面板 | `wide_fea_v2ext.npy` + `_meta.npz` | 公式逐位同 L4 | pod |
| 5 | **DL 目标** | `retrain_2026-09/pod_dlw_targets_ext.py` L24, L75, L79-80, L90-91, L93-94, L96 | ext 缓存 + 面板 | `dlw_targets.npz` | **`y4s = expm1(CS_L[E+49] − CS_L[E+1])` = Π(1+r5)−1 于行 [E+1, E+48]**; `y4old = CS_r[E+48] − CS_r[E]` = Σ简单 [E, E+47] | pod/jpline |
| 6 | 82 列 DL 弹药 | `retrain_2026-09/pod_dlw_features_ext.py` L15-17, L36-45, L54-59 | targets + 缓存 | `dlw_fea82.npz` | 窗 `hi = E+1`, `lo = hi−w` ⇒ **含收盘于 N 的那根 bar**; 断言 L45 `max_feature_row == E` | pod |
| 7 | 89 列扩展 | `retrain_2026-09/pod_f8_build_ext.py` | targets + fea82 + 缓存 | `f8_fea89.npz` | 82+89 = **171 列**(F10 输入) | pod |
| 8 | 面板拼接 v3splice | `retrain_2026-09/pod_panel_splice.py` L11-27, L76-103, L106-114 | v1 正典 + v2ext | `wide_panel_4h_v3splice.npz` + `fund_state_canoncont.json` | ≤cut 全列逐字 = 正典; >cut kline/fund_now/iv = ext, EMA 族以 cut 行为种子续算; 断言 L110/L114 | pod |

### 1.1 08-21 面板的确凿出处(逐字命令)

来自 `retrain_2026-09/review_caliber_wf/wf_results_all.json` L1741 与 L1812, 引用会话转录 **2026-08-21T02:01:44Z**:

```
EXT_START=2020-01-01 EXT_END=2026-08-16 EXT_OUT=/workspace/data/dlnative_5m_wide829_f16_hist.npz python3 pod_build_wide_ext.py
CACHE_IN=/workspace/data/dlnative_5m_wide829_f16_hist.npz PANEL_OUT=/workspace/data/wide_panel_4h_hist_v2.npz nohup python3 pod_panel_ext.py
scp ... $SP/wide_panel_4h_hist_v2.npz root@...:/workspace/data/wide_panel_4h_v1.npz
```

**要点**: `wide_panel_4h_hist_v2.npz` 是 **`pod_panel_ext.py` 跑在 2020 起缓存上**, 不是 `pod_panel_wide_hist.py`。这解释了它为何带 `f_fund_iv` 与 `f_fund_ema_v1`(`pod_panel_ext.py` L165-166), 而 `pod_panel_wide_hist.py` L109 只写两列。下游 `w2_wide_replay.py` L20 与 `w10_universe.py` L59 正是靠这两列做正确 carry。

同一文件 L1741 记: pod 上的 `wide_panel_4h_v1.npz` sha256 `f14bc33d78b24929` **与 Mac 上 `pod_backup/wide_panel_4h_hist_v2.npz` 逐位相同**(247,363,525 字节, Aug 21 11:32), 09-01 ~03:13Z 经 jpline→Mac→pod 中转后改名。

**08-21 整链脚本**: `.../devices_2026-08-21/run_hist_chain.sh` L5-11 —
```
CACHE=/workspace/data/dlnative_5m_wide829_f16_hist.npz
CACHE_IN=$CACHE PANEL_OUT=/workspace/data/wide_panel_4h_hist.npz python3 pod_panel_wide_hist.py
CACHE_IN=$CACHE PANEL_IN=... FEA_OUT=/workspace/data/wide_fea_hist.npy META_OUT=/workspace/data/wide_fea_hist_meta.npz python3 pod_fea_wide_hist.py
python3 pod_slow_hist_folds.py
TAG=hist python3 pod_stop_arms_v3.py
```
注意该 sh 里 `PANEL_OUT` 是 `_hist.npz`(旧两列面板)且 `TAG=hist`; 实际入库的参照文件名是 `nets_histv2_*`, 即最终跑的是 `TAG=histv2` + `PANEL_IN=wide_panel_4h_hist_v2.npz` 的变体。**该变体的逐字命令不在库内(INFERRED, 见 §8 开放问题 1)。**

### 1.2 已入库的小配置件(重建必需, 无需重造)

| 文件 | 路径 | 内容(实测) |
|---|---|---|
| 829 符号轴 | `.../workspace_mirror/panel_symbols_wide.txt` | 829 符号, `\|` 分隔 |
| 在役钉死 | `retrain_2026-09/live_pins.json` | `symbols_live` 450 / `keep_names` 78 / `keep_idx` 78 |
| bundle 门基线 | `retrain_2026-09/slow_scorer_v3base.json` | 2024/2025/2026 折 IC 基线 |
| npz 惰载器 | `retrain_2026-09/zload.py` L6-13 | zipfile 逐 `.npy` 读, `pod_panel_ext.py` L12 / `pod_fea_ext.py` L5 依赖 |

---

## 2. KING 模型血统

| 产物 | 生产脚本 | 训练规则 | 收据 |
|---|---|---|---|
| **`slow_pred_hist_oos.npy`(08-21 装置吃的 king)** | `.../devices_2026-08-21/pod_slow_hist_folds.py` | 逐年扩张折 `YV ∈ {2022,2023,2024,2025,2026}`, `tr = YRA < YV`, `te = YRA == YV`, **无 embargo** | L27-30 训练, L37 保存到 `/workspace/exports_train/slow_pred_hist_oos.npy` |
| `slow2026_hist.txt` + `slow_pred_pinned_hist.npy` | `.../devices_2026-08-21/pod_slow_retrain_hist.py` | `tr = YRA < 2026` 钉定 booster(L34-36); 另跑 2022-25 折(L38-44) | L49-54; 产物入 `/workspace/shadow_bundle_hist/`(明写「未部署」L53) |
| **`slow_pred_pinned.npy`(在役生产 king, 09-01)** | `retrain_2026-09/pod_export_bundle_v3.py` | **读 `wide_fea_v2ext.npy`(2022 起, 元数据 2020/2021 计数为 0)**, `tr = YRA < 2026`; 2024/2025 折只为历史腿收益 | L26-27 输入, L49 训练集, L56-59 折 |

**三者超参完全一致**: `n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8`
(`pod_slow_hist_folds.py` L30 / `pod_slow_retrain_hist.py` L35, L41 / `pod_export_bundle_v3.py` L50-51, L58-59)

**标签**: 成员内 raw `y4` 的秩线性缩放 `rankdata(yv[ok]) / max(ok.sum()−1, 1) − 0.5`
(`pod_slow_hist_folds.py` L21 / `pod_slow_retrain_hist.py` L29 / `pod_export_bundle_v3.py` L43)

**特征**: 82 列去掉 `ret5_sum_48` 与 `ret5_sum_288` ⇒ **78 列**
(`pod_slow_hist_folds.py` L11 / `pod_export_bundle_v3.py` L32; 后者 L33 还断言 `== PINS["keep_names"]`)

**列序守卫**: `pod_slow_retrain_hist.py` L10-18 把 hist meta 的列按 v2ext meta 列序取, 保证 booster 特征序与生产一致。移植时必须保留这段。

**bundle 出口腿收益**(供席位历史): `pod_export_bundle_v3.py` L109
`LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) ...)` — **原始 y4, 无 expm1**。同 L149-153 的书层。

**E-0905-A 的代码级证据**: `docs/RUNBOOK_monthly_retrain_2026-09.md` §1 步骤 3(该文件 L15 行区)写「若 §28 判 ADOPT_FOR_V2 则起点 2020-01, 否则 2022-01」, 而 09-01 实跑的 `pod_export_bundle_v3.py` L26-27 **写死读 `wide_fea_v2ext.npy`**, L49 `tr = YRA < 2026` ⇒ 在役 booster 训练集 = 2022-01..2025-12。条件分支静默走了默认值。

**E-0905-B**: 同 RUNBOOK 行写「2026 折训练集自动加长一个月」, 但 L49 的 `tr = YRA < 2026; te = YRA == 2026` 意味着 **king 完全不用 2026 数据训练**, 每月重训只是在同一 2022-2025 训练集上重训并对延长后的 2026 特征做预测。

---

## 3. F10 / V2MAIN 血统

**训练脚本(在库副本)**: `eda/f10_train_pod_3fac6689d3f3c60f_2026-08-25.py`
(同族另一版 `eda/f10_train_pod_bbd4031d87d5085d_2026-08-26_tree1.py`; 生产 ext 版 `retrain_2026-09/pod_f10_train_ext.py` 与 refit `pod_f10_refit_ext.py`)

| 项 | 值 | 收据 |
|---|---|---|
| walk-forward 折 | `for YV in (2023, 2024, 2025, 2026)` | L253 |
| 训练集 | `tr_idx = [i for i in range(first_te − EMB) if yrs[i] < YV and ST[i+1]−ST[i] >= 50]` | L258 |
| **embargo** | `EMB = 60` 锚 | L21 |
| 窗/燃烧/步长 | `WIN, BURN, STRIDE = 96, 24, 48` | L21 |
| 训练窗二次约束 | `span = [i for i in range(s0−BURN, s0+WIN) if i < first_te−EMB and yrs[i] < YV]` | L276 |
| 折种子 | `torch.manual_seed(SEED + YV)` | L266 |
| 输入 | `dlw_fea82` ⊕ `f8_fea89` = **171 列** | L43-48 |
| 目标 | `y4s`(= Π(1+r)−1) 自 `dlw_targets.npz` | L40-41 |
| V2MAIN 臂 | 需 `V2=1`, 载 `f10v2_legs.npz` | L84-90 |
| 78 列归因臂 | `NCOL=78` 去 89 新列 + 4 根 king 剔除的快列 | L52-55 |
| 产物 | `f8_2026-08-22/preds/f10_{ARM}_s{SEED}.npy` | L353 |
| 种子 | 42 / 2027(`f8_2026-08-22/preds` 只有这两个) | `combo_recheck/REPORT.md` §6 |

**装置消费点**: `retrain_2026-09/w10_universe.py` L92-95 —
```
_fp = os.environ.get("FPRED", f"f10_V2MAIN_s{FSEED}.npy")
_pd = np.load(f"{_R2}/f8_2026-08-22/preds/{_fp}")
_TG = np.load(f"{_R2}/dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True)
```
L101 用 `dlw` 符号列映射回回放符号序, L108 逐锚填 `F10P`。L89-90 有严格因果注释: 全史重训件 `models/f10_live_s*.pt` **不参与任何历史评估**。

**再次强调**: **08-21/22 装置不消费 F10。** `pod_stop_arms_v3.py` L18 `KSRC = {"hist_oos": np.load(... slow_pred_hist_oos.npy)}`; `w2_wide_replay.py` L22 `SLOW = np.load(f"{B}/slow_pred_hist_oos.npy")`。两者代码里没有任何 F10 路径。

---

## 4. 装置血统(口径 / 链条 / 席位 / 命令)

| 装置 | 路径 | 收益口径 | 关键行 |
|---|---|---|---|
| `pod_stop_arms_v3.py`(**权威构造, nets_histv2 的产出者**) | `multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-21/` | **原始 y4** | 腿 L38, 书 L76 `yv = nan_to_num(y4[i,m], nan=0.0)`; expm1 只在 L59 报价额 |
| `w2_wide_replay.py`(08-22 jpline 移植) | `multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-21/` | **原始 y4** | 腿 L42, 书 L80; expm1 只在 L63 |
| `w2b_common.py` / `w2b_build_return_cube.py` | 同上 | **1h kline 对数** | cube L56 `rl = np.log(c4/c0)`, `rw = np.log(c3/cm1)` |
| `w10_universe.py`(09-01 家族) | `retrain_2026-09/` | `CAL` 环境变量, **默认 `simple` ⇒ `np.expm1`** | L17 默认值; L135-136 腿; L277-278 书 |
| `w10_ablation_replay_hardened_9f15dea0131f_2026-08-26.py` | `eda/` | 同, 加 `assert CAL in (simple, log)` | L11 复现收据, L227 臂 |
| `w10_universe_port.py` / `w10_universe_recheck.py` | `retrain_2026-09/review_caliber_wf/combo_recheck/` | 同 w10, 加 `REF_SKIP` | 补丁 `setup_pod.sh` L14-27 |
| `w10_universe_recheck.py`(rolling king 版) | `retrain_2026-09/rolling_king_2026-09-05/` | 同 | 因果注释 L90, L154 |

### 4.1 书链(`w10_universe.py` 绝对行号)

```
xz 秩化 [−0.5, 0.5]                     L112-114
三腿加权 z                               L186 附近(run 块)
KMOD / KMOD_F10 / KTAIL 调制             L189-194
FTRIM 负费率空头置零                     L195-197
选择: qv4h >= 2.5e5, nsel >= 80          L198-200
去均值 → L1 归一                          L205-207
softcap 2.5/n → 再归一                    L207, L209
EMA alpha = 0.1                          L214  (sm = H + 0.1*(tgt − H))
死带 2.5e-4                              L215
成本 COST_B 三档                          L116, L275
carry = rate * 4 / interval              L280
```
`COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]`(maker bps, taker bps, maker 占比), 定义在 `w10_universe.py` L116 / `pod_stop_arms_v3.py` L23 / `w2_wide_replay.py` L27 / `pod_export_bundle_v3.py` L93, **四处逐字相同**。

### 4.2 席位规则

`w10_universe.py` L145-177 `w3_at(i)`:
- `W3FIX` 白名单单值 `"0.21,0,0.79"`(L27-28 断言)
- 否则 `WRULE=msharpe`: `LOOK=900` 锚回看, `shp = max(mean/std, 0)`, 归一
- **严格因果注释 L157**: `sl = slice(p − LOOK, p)  # ★ 严格因果: 只用锚 i 之前的腿收益`
- `LEGS` 掩码(`"111"` 三腿 / `"101"` 去 rev24)在 L169-173 重归一

08-21 装置的同一规则在 `pod_stop_arms_v3.py` L42-48(`look=900` 硬编码)。

### 4.3 nets_histv2 参照文件的产出

`pod_stop_arms_v3.py` L103:
```python
np.save(f"/workspace/exports_train/nets_{TAG}_{int(depth*100) if depth else 0}_{need}_{cool}.npy",
        np.stack([ts_, nets], 1))
```
臂表 L122: `[("S0", None, 0, 0), ("d25_n2_c42", -0.25, 2, 42), ("d30_n2_c42", -0.30, 2, 42), ("d25_n1_c42", -0.25, 1, 42)]`
`TAG = os.environ.get("TAG", "hist")` L124。

⇒ `nets_histv2_-30_2_42.npy` = `TAG=histv2` + 臂 `d30_n2_c42`(depth −0.30, need 2, cool 42)
⇒ `nets_histv2_0_0_0.npy` = `TAG=histv2` + 臂 `S0`(无止损)

这两个文件是全部 w2/w10 装置的复现基准: `w10_universe.py` L11 头注 + L319 `ARMS` + L326-333 平价断言。

### 4.4 `nets_histv2_d30_pergross_ts_0821.npy` — 产出命令(诚实结论: **不在库**)

**在库事实**:
- 文件本身: `retrain_2026-09/review_caliber_wf/combo_recheck/nets_histv2_d30_pergross_ts_0821.npy`, **git-tracked**
- 实测形状 `(9941, 2)` float64; ts 跨 **2022-01-31 08:00Z → 2026-08-15 00:00Z**; 第 1 列均值 **+1.1760 bps/锚/gross**
- 唯一消费者: `combo_recheck/pod_armA_vs_0821.py` L14
  `ref = np.load("/workspace/review_scratch/combo_recheck/nets_histv2_d30_pergross_ts.npy"); rts = ref[:,0].astype(np.int64); rv = ref[:,1]`
- 引入它的 commit `be1e89e`(2026-09-05 00:09:25 +0800)**只含三个文件**: 该 npy、`pod_armA_vs_0821.py`、`pod_armA_vs_0821.out`。

**⇒ 把 jpline 序列除成 per-gross 的那个脚本没有入库。** 全仓 grep `pergross` 除该消费行外无第二处产出点。

**重建配方(从消费者代码倒推, 确定性)**: 它是 08-21/22 jpline 装置的逐锚 npz 里 `net / gross_total` 两列。`pod_armA_vs_0821.py` L4-6 对 pod 侧就是这么做的:
```python
z = np.load(p, allow_pickle=True); cols = [str(c) for c in z["cols"]]; R = z["d30_n2_c42_rec"]
ts = R[:, cols.index("ts")].astype(np.int64); g = R[:, cols.index("gross_total")]
return ts, R[:, cols.index("net")]/g, R[:, cols.index("net_ex")]/g
```
`COLS` 定义在 `w10_universe.py` L320 / `w10_universe_port.py` L320 / `w10_universe_recheck.py` L321:
```
["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires",
 "leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover",
 "net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
```
在 pod2 上重造该参照 = 跑 08-21 形态得到 series npz, 取 `net / gross_total` 两列, 与在库的 9941 行逐位对账。**这是一个可执行的验收门, 建议列为重建的第一个红线。**

### 4.5 pod 侧对照臂的逐字命令(已入库)

`combo_recheck/commands_dev.txt` L1-11 全部 11 条。核心两条:
```
CMD[A_callog]    (cwd=/workspace/review_scratch/combo_recheck/dev): env LOOK=900 WRULE=msharpe \
  SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy LEGS=111 PHI=0 FSEED=42 CAL=log \
  REF_SKIP=1 OUT_TAG=A_callog /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[A_calsimple] (同上, CAL=simple)
```
`setup_pod.sh` L7-12 说明 dev 目录如何把 `pod_backup_2026-08-21/{nets_histv2_*, slow_pred_hist_oos.npy, wide_panel_4h_hist_v2.npz, wide_fea_hist_meta.npz}` 符号链接到 pod 的 port 目录。**注意 `REF_SKIP=1`: pod 上的 nets_histv2 参照是 144 字节占位桩, 平价门被跳过**(`REVIEW_caliber_final_2026-09-04.md` §4 C6 point 7 记为失效门)。pod2 重建必须补上真参照。

### 4.6 两仪器对账结果(`combo_recheck/pod_armA_vs_0821.out`, 9941 共同锚)

```
pod  net/gross    (CAL=log): 2022 −0.483 S−0.84 | 2023 −0.560 S−1.17 | 2024 +0.327 S+0.66 | 2025 +1.129 S+1.93 | 2026 +2.351 S+3.99 | 2024→ +1.111 S+2.01
pod  net_ex/gross (CAL=log): 2022 −0.358 S−0.64 | 2023 −0.542 S−1.14 | 2024 +0.312 S+0.63 | 2025 +0.793 S+1.32 | 2026 +2.268 S+3.90 | 2024→ +0.957 S+1.71
08-21 net/gross           : 2022 +1.379 S+1.97 | 2023 +0.580 S+0.92 | 2024 +0.585 S+1.21 | 2025 +1.471 S+2.92 | 2026 +2.317 S+5.89 | 2024→ +1.332 S+2.83
差(pod − 08-21)           : 2022 −1.862 | 2023 −1.140 | 2024 −0.258 | 2025 −0.342 | 2026 +0.034 | corr(2024→) 0.867
pod CAL=simple(错口径)     : 2022 −1.095 | 2023 −0.856 | 2024 +0.535 | 2025 +0.815 | 2026 +4.013 | 2024→ +1.464 S+2.38
```
`.out` 头两行自述形态: 「同锚(9941, 2022-01-31→2026-08-15)、同形态(三腿 msharpe, d30 止损层)、同列(net/gross_total, bps/锚, 每 gross)」「08-21 装置 = jpline, 原始 y4, hist king(2020 起训练, 2022 起有预测); pod port = 原始 y4(CAL=log), 生产 king(2022 起训练, 2022-23 无预测)」。

---

## 5. 每一处 log ↔ simple 转换(全清单, 带行号与作用对象)

| 文件:行 | 表达式 | 作用于 | 判定 |
|---|---|---|---|
| `pod_build_wide_ext.py` L32-33 | `np.log1p(k.qv)`, `np.log1p(k.cnt)`, `np.log(k.qv/k.cnt)` | 量能通道 ch3/ch4/ch5 | 正确, 与收益无关 |
| `pod_merge_cache_ext.py` L30-31 | 同 | 同 | 正确 |
| `pod_panel_ext.py` L26 | `CS_q = cs(np.expm1(np.clip(qv, 0, 30)))` | 把 log_qv 还原成原量能 | 正确, 只作比值/秩 |
| `pod_panel_wide_hist.py` L24 | 同 | 同 | 正确 |
| `pod_fea_ext.py` | **无任何 log/expm1** | — | 特征与 y4 皆无变换 |
| `pod_fea_wide_hist.py` | **无任何 log/expm1** | — | 同 |
| **`pod_dlw_targets_ext.py` L75** | `CS_L = cumsum(np.log1p(r5z))` | 5m 简单收益 → 对数 | 正确(为复利做准备) |
| **`pod_dlw_targets_ext.py` L93** | `y4s = np.expm1(CS_L[hi_t] − CS_L[lo_t])` | 还原成 Π(1+r)−1 | **本族唯一合法的收益 log↔simple 往返** |
| `pod_dlw_targets_ext.py` L96 | `y4old = CS_r[E+FWD] − CS_r[E]` | Σ 简单 | 无变换, 对照用 |
| `pod_stop_arms_v3.py` L59 / L76 | `expm1(clip(qvk,0,30))*48` / `yv = nan_to_num(y4)` | 量能 / **收益无变换** | 正确 |
| `w2_wide_replay.py` L63 / L80 | 同 | 同 | 正确 |
| `pod_export_bundle_v3.py` L130, L146 | `expm1(clip(qvk,0,30))*48` | 量能; 腿收益 L109 与书 L149 用原始 y4 | 正确 |
| **`w10_universe.py` L136** | `if CAL == "simple": _yy = np.expm1(_yy)`(legs) | **面板 Σ简单 y4** | **伪凸性缺陷** |
| **`w10_universe.py` L278** | `if CAL == "simple": yv = np.expm1(yv)`(run) | 同 | **伪凸性缺陷** |
| `w10_universe.py` L198 | `expm1(clip(qvk,0,30))*48` | 量能 | 正确 |
| `multi_asset/data/build_wide_dl.py` L95 | `logc = np.log(np.where(C>0, C, np.nan))` | 收盘价 | 另一族(真对数) |
| `multi_asset/data/build_wide_dl.py` L151 | `Y[:T−H] = (logc[H:] − logc[:−H])` | **真 H 小时对数收益** | `wide_dl.npz` 族; expm1 对它才成立 |
| `build_wide_dl.py` L103, L105, L118, L125 | `logc − shift(logc,n)`, `log(QV)`, `logc − shift(logc,24)` | 通道 | 同族 |
| `multi_asset/engine/panel_source.py` L34 | `self.Y4 = W["Y4"]  # raw 4h fwd logret` | in-role 9821 锚族 | 对数族 |
| `w2b_build_return_cube.py` L56 | `rl = np.log(c4/c0)`, `rw = np.log(c3/cm1)` | 1h kline | 08-22 独立路径审计用 |
| `pod_panel_lineage.py` L21 | `S=rr.sum(0); L=np.log1p(rr).sum(0); C=np.expm1(L)` | 三候选定义各算一遍 | 诊断装置 |

### 5.1 窗口对齐事实(逐行确认)

| 量 | 行窗 | 时钟窗 | 收据 |
|---|---|---|---|
| 面板 `Y4` / meta `y4` / `y4old` / king 标签 / bundle 腿收益 | `[E, E+47]` | **(N−5m, N+3h55m]** | `pod_panel_ext.py` L58; `pod_fea_ext.py` L34; `pod_fea_wide_hist.py` L38; `pod_dlw_targets_ext.py` L96 |
| DL 目标 `y4s` | `[E+1, E+48]` | **(N, N+4h]** | `pod_dlw_targets_ext.py` L90-91(断言 `lo_t.min() − E.min() == 1`) |
| **king 特征** | `[E−w, E−1]` | 止于收盘于 **N−5m** 的 bar | `pod_fea_ext.py` L48-52(`s_[E] − s_[E−w]`); `pod_fea_wide_hist.py` L55-57 |
| **DL 特征** | `[E−w+1, E]` | 止于收盘于 **N** 的 bar | `pod_dlw_features_ext.py` L44(`hi = E+1`), L54-59; 断言 L45 |

**因果性**: 两组「特征窗 + 标签窗」都是零重叠零间隙。king 侧特征最后一根 bar 覆盖 [N−10m, N−5m], 标签第一根覆盖 [N−5m, N]。DL 侧特征最后一根覆盖 [N−5m, N], 标签第一根覆盖 [N, N+5m]。
**未量化风险**: king 训练特征止于 E−1, 但实盘服务在锚 N 时收盘于 N 的 bar 已可得。若生产者纳入它 ⇒ 训练/服务错一根 bar。`REVIEW_caliber_final_2026-09-04.md` §7 #14 登记为未量化开放项。

**面板锚网格**(三处一致): `grid = np.where(CTS % 14400 == 0)[0]` — `pod_panel_ext.py` L32 / `pod_fea_ext.py` L24 / `pod_dlw_targets_ext.py` L79。
**成员集**: 覆盖率 ≥0.95 ∧ 7 日波动 ≥1e-4 ∧ y4 有数 ∧ 量能 top-400, 成员数 ≥50 — `pod_fea_ext.py` L37-40 / `pod_dlw_targets_ext.py` L100-105(常数在 L24: `NTOP=400, MIN_MEM=50, MIN_FIN=46`)。

---

## 6. 已在库的泄漏电池(可直接移植)

| 类别 | 脚本(绝对路径前缀 `/Users/haosiyu/Desktop/quant_research/`) | 关键行 | 测什么 / 对什么数据 |
|---|---|---|---|
| **shuffle-future 原语(纯 numpy, 可逐字移植)** | `multi_asset/eda/leakage_null.py` | L50-69 `permute_y_null`, L75-89 `_corrupt_future`, L92-144 `shuffle_future_null` | 污染 `cut_second` 之后的全部原始输入并重建, 要求 pred-time ≤ cut 的每个窗逐位相同 |
| 其 TDD 套件 | `multi_asset/eda/test_leakage_null.py` | L46, L99-118 | 泄漏构建必红, 严格过去构建必绿 |
| **在役偏移谱门(V3′)** | `retrain_2026-09/pod_f10_v3_leakcheck_v2.py` | L11-28 `spectrum`, L30-44 三条款 | ① `max\|corr(k∈[+1,+3])\| < \|corr(k=0)\|` ② 谱形与在役代 per-k `\|Δ\| ≤ 0.03` ③ 折外(pre-2023)泄出格点 = 0; 读 `f10_V2MAIN_s{42,2027}.npy` + `dlw_targets.npz`; FAIL 退出码 3 |
| 其字面前身 | `retrain_2026-09/pod_f10_v3_leakcheck.py` | L17-35 | 峰必须在 k=0(字面版, 被 AMENDMENT A1 修订) |
| V2L38 臂同门 | `retrain_2026-09/pod_l38_leakcheck.py` | L8-32 | 同三条款 |
| **正典三件套有效性电池** | `multi_asset/exports/eda/dlw_2026-08-22_devices/dlw_judge.py` | **L122-148**, L194-198 | shuffle null(`\|IC\| < 2·SE`, 3 种子, 年内锚置换) + 偏移谱 k∈[−6,+6] `peak_pass = (peak_k == 0)` + `σŷ/σy ≥ 0.02`; 与 `kcurve_2026-08-21/devices_2026-08-22/dlw_judge.py` 字节相同 |
| R3/R4 收据块(pod 版) | `retrain_2026-09/pod_f8_build_ext.py` | L544-565 | 逐臂 shuffle null + `R4_offset_spectrum` |
| 同块 08-22 原件 | `.../kcurve_2026-08-21/devices_2026-08-22/f8_higher_order_features.py` | L544-565 | 同 |
| 泄漏终审(增量谱 + 封存段) | `.../devices_2026-08-22/f8b_crosswalk_leak.py` | L262-284 | 成对 Δnull 锚聚类 SE + 增量谱 `peak_at_0` + 2026 封存段 |
| 事后重读 | `.../devices_2026-08-22/f8_validity_reread.py` | L1-5, L20-40 | 年内 shuffle ×3 + 偏移谱 + 增量谱 + 逐名年内持久分量 |
| **面板/E 网格相位扫描** | `.../kcurve_2026-08-21/devices_2026-08-21/w2b_offset_check.py` | L21-28(Y4 偏移 k∈[−2,+2]), L30-36(累积 Y1), L37-44 | 读 `pod_backup_2026-08-21/wide_fea_hist_meta.npz` + `wide_panel_4h_hist_v2.npz`; 找相位错配量 |
| 收益源对账(独立路径) | `.../devices_2026-08-22/wide_return_source_audit.py` | L18, L172, L482 | `corr(R_wide, Σ_{E+k..E+k+47} log1p(ret5))` 谱, 峰位 = 窗口错配量 |
| 其同伴 | `.../devices_2026-08-21/w2b_srccheck.py` | L5-20 | meta y4 vs 1h kline 逐符号 corr / mean\|diff\| bps / 回归斜率 |
| **字面 CAUSALITY ASSERT** | `retrain_2026-09/rolling_king_2026-09-05/pod_king_rolling_monthly.py` | **L96**, L87, L90-95, L97 | 每折 `max(train E_ts) + 48*300 < min(test E_ts) − 60*14400`; 另 L97 `assert not np.any(tr & te)` |
| **投毒式面板因果套件** | `multi_asset/exports/eda/tests_panel_causality_train.py` | L106-128 `poison`, L185-190, **L191-196**(ch31 必须恰在 cut+1 反应), L198-200, L202-215 | 双面断言: 因果通道 ≤cut 逐位不动 **且** 前视标签必须按其视界变化 |
| **其正对照(必须同时移植)** | `multi_asset/exports/eda/probe_causality_positive_control.py` | L1-35 | 用未打补丁的 builder 跑同一投毒, 要求相反结果; 缺它则「32/32 因果」与盲测不可区分 |
| embargo 不变性 | `.../workspace_mirror/pod_leak_audit.py` | L63-66 | e0 vs e60 重训, `\|ΔIC\| < 0.002` |
| **端到端四件套电池(路径过期)** | `.../workspace_mirror/pod_leak_audit.py` | L1-6 头注, ①L47-62 ②L63-66 ③L67-81 ④L82-101 | 唯一一个单进程跑完四个装置的; 硬编码上一代产物名(`wide_fea_v1.npy` / `dlnative_5m_wide829_f16.npz` / `slow_lgbm_pred.npy`), **移植需把 5 个路径重指向 v2ext 代**; 只 print 不返回非零码 |
| 面板口径护栏红绿电池 | `multi_asset/exports/eda/assert_panel_caliber_manifest.py` + `tests_panel_caliber_manifest.py` | 后者 L1-15 | 每个用例声明何为红; R1 把真修正重建塞进 trained 槽必须 FAIL |
| 独立路径口径审计 | `.../devices_2026-08-22/wide_full_caliber_audit.py` | L1-12 | 不 import 任何既有装置, 从原始 1h/5m zip + 结算 zip 重建, JSON 里写 `self_sha256` + `input_sha256` |
| walk-forward 折序回归测试 | `tests/test_walk_forward.py` | L23-60, L61, L114 | 折数与 `train_end` 单调递增 |
| embargo 可观测性回归 | `tests/test_v5_embargo_observable.py` | L47-133(L133 `assert gap_yes == gap_no + 1`) | 防 `training.embargo_days` 被静默忽略 |

**没有任何单一脚本能端到端跑完当前这套门。** `docs/RUNBOOK_monthly_retrain_2026-10.md` §4(该文件 L57-66)把门梯列为逐条手工调用: 输入链门 `pod_gate_dlw_ext.py` → V1 `pod_f10_np_export.py` → V2 `jp_w10_v2gate_judge.py` → **V3′ `pod_f10_v3_leakcheck_v2.py`(L64)** → V4-np `jp_v4_np_check.py`。`retrain_2026-09/pod_run_chain.sh` 只串 panel→fea; `pod_f10_inputs_chain.sh` 只串 targets→gate→fea82→fea89。

**pod2 最小移植集(自足, 无归档依赖)**:
1. `multi_asset/eda/leakage_null.py` + `test_leakage_null.py`
2. `.../workspace_mirror/pod_leak_audit.py`(重指 5 个路径)
3. `retrain_2026-09/pod_f10_v3_leakcheck_v2.py`
4. `dlw_judge.py` L122-148 有效性块(提取成可复用三件套)
5. `tests_panel_causality_train.py` **+** `probe_causality_positive_control.py`(两者必须同时)
6. `pod_king_rolling_monthly.py` L87-97 的 CAUSALITY ASSERT(抄进任何新的 walk-forward 训练器)

---

## 7. pod2 重建缺什么

### 7.1 必须重新拉取的数据: 2020-2021 5 分钟 K 线 + funding

**脚本已入库**: `multi_asset/exports/research/runpod_scripts/workspace_mirror/pod_hist_dl.py`(git-tracked)

头注 L1-3 自述: 「§28 回溯下载 @pod: 2020-01..2021-12 月度 5m klines(829 币, 未上市自然 404)+ funding 月度(450 币). 写入既有目录树, 幂等.」

**URL 模式**(L10, L14, L17):
```
BASE = "https://data.binance.vision/data/futures/um/monthly"
klines : {BASE}/klines/{S}/5m/{S}-5m-{YYYY-MM}.zip        → /workspace/klines5m/{S}/{S}-5m-{YYYY-MM}.zip
funding: {BASE}/fundingRate/{S}/{S}-fundingRate-{YYYY-MM}.zip → /workspace/wide_multisrc/funding/{S}/{YYYY-MM}.zip
```
月份集 L7: `MONTHS = [f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)]` = 24 个月
符号集 L8-9: klines 用 `panel_symbols_wide.txt`(829); funding 用 `wide_multisrc/funding/*` 现有目录(450)

**幂等机制** L26-27, L34-36: 已存在的 `.zip` 或 `.404` 哨兵文件直接跳过; 404 落一个空 `.404` 文件不再重试。可安全中断续跑。

**⚠ 限速**: L44 `ths = [threading.Thread(...) for _ in range(8)]` — **8 线程, 无任何节流**。要满足 ≤4 req/s 必须二选一:
- 把 L44 的 `8` 改小(单请求往返 ~0.25s 时, 线程数 ≈ 目标 req/s), 或
- 在 L30 的 `urlretrieve` 前插一个共享节拍器(实盘仓已有同类做法: `ops/backfill_markout.py` 的 `PACE_S=2.0`)

**作业量**: klines 829 × 24 = 19,896; funding 450 × 24 = 10,800; 合计 **30,696 个请求**。@4 req/s ≈ 2.1 小时(未上市月份会大量 404 快跳, 实际更短)。

**相关同族下载器**(按需):
| 脚本 | 用途 | 关键行 |
|---|---|---|
| `.../workspace_mirror/pod_dl_klines.py` | 2022-01..2026-07 monthly + 2026-08 daily | L5, L8, L15-20; 12 线程 |
| `.../workspace_mirror/pod_wide_multisrc_pull.py` | 通用多源(funding/premidx/markpx/idxpx/metrics/spot5m), CLI 化 | L11-19 源表, L55 拉取; **默认 24 workers**, 需限速 |
| `retrain_2026-09/pod_fund_zips.py` | funding 全史 2019-09..2026-08(真 interval 列) | L9-11; 8 线程 |
| `retrain_2026-09/pod_extend_vision.py` | daily 尾巴(月度重训步骤 1) | L8-15; 8 线程 |
| `.../workspace_mirror/pod_dl_wide.py` | 重生成 `panel_symbols_wide.txt` + 补新币 | L4-16 |

**为什么 funding 也要重拉**: `MANIFEST.md` 偏差 D3 记录 — funding zip 缺失时 interval 全靠时间差推断(首行默认 8), Binance 2023+ 多币 8h→4h→1h 切换期必错 ⇒ `f_fund_iv` exact 99.96% → EMA 递归放大 → `f_fund_ema_v1` corr 0.9796 门红。**必须拉带 interval 列的 zip, 不能靠推断。**

### 7.2 需要移植的脚本(按执行顺序)

| 序 | 脚本 | 环境变量 / 参数 |
|---|---|---|
| 1 | `pod_hist_dl.py`(限速后) | — |
| 2 | `pod_fund_zips.py` | — |
| 3 | `pod_build_wide_ext.py` | `EXT_START=2020-01-01 EXT_END=2026-08-16 EXT_OUT=/workspace/data/dlnative_5m_wide829_f16_hist.npz` |
| 4 | `pod_panel_ext.py` | `CACHE_IN=<上一步> PANEL_OUT=/workspace/data/wide_panel_4h_hist_v2.npz` |
| 5 | `pod_fea_ext.py`(或 `pod_fea_wide_hist.py`) | `CACHE_IN=... PANEL_IN=... FEA_OUT=wide_fea_hist.npy META_OUT=wide_fea_hist_meta.npz` |
| 6 | `pod_slow_hist_folds.py` | `FEA_IN` / `META_IN`(L7-8 可覆盖) |
| 7 | `pod_stop_arms_v3.py` | `TAG=histv2 META_IN=wide_fea_hist_meta.npz PANEL_IN=wide_panel_4h_hist_v2.npz KING_IN=slow_pred_hist_oos.npy` |
| 8 | `pod_dlw_targets_ext.py` | `DLWT_CACHE / DLWT_PANEL / DLWT_OUT` |
| 9 | `pod_dlw_features_ext.py` | `F171_CACHE / F171_PANEL / F171_OUT` |
| 10 | `pod_f8_build_ext.py build` | — |
| 11 | F10 训练器 | `V2=1 SEED=42\|2027 ARM=MAIN` |
| 附 | `zload.py` | `pod_panel_ext.py` L12 / `pod_fea_ext.py` L5 依赖 |

### 7.3 ⚠ 链条里的一个硬阻断点

`pod_panel_ext.py` L172 **硬编码** 自检输入:
```python
PW1 = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
```
L182-194 对 7 列做 `corr >= 0.999` 平价, 不过则 `sys.exit(3)`。全新 pod 上该文件尚不存在 ⇒ `FileNotFoundError`。这正是 09-01 转录里记录过的那次失败(`wf_results_all.json` L1741: 「pod_panel_ext.py L172 FileNotFoundError」后才走 jpline→Mac→pod 中转)。**重建时须先备好一个 v1 面板做自检基准, 或显式停用该段并记录。**

### 7.4 环境

`retrain_2026-09/BOOTSTRAP.sh` L8-13 是现成的体检脚本: 装 `numpy scipy pandas lightgbm`, 逐件检查 5 个关键产物存在性。L11 的产物清单需按 hist 代改名。
GPU 侧记录(`MANIFEST.md` f10 重训运行记): torch 2.4.1+cu124 → 2.11.0+cu128, 硬件强制(RTX PRO 4500 Blackwell sm_120, 旧轮只到 sm_90)。

---

## 8. 开放问题(重建前需裁定或补证)

1. **`nets_histv2_d30_pergross_ts_0821.npy` 的产出脚本不在库。** commit `be1e89e` 只含 artifact + 消费者 + 输出。重建配方已在 §4.4 给出(`net / gross_total`), 但需要先在 pod2 复现 08-21 series npz 才能验证。**建议作为第一红线**: 重建序列与在库 9941 行逐位对账。
2. **`TAG=histv2` 那一跑的逐字命令不在库。** `run_hist_chain.sh` L8-11 写的是 `TAG=hist` + `_hist.npz` 面板; 实际产出的是 `nets_histv2_*` + `hist_v2` 面板。两者的差 = `PANEL_IN` 指向带 `f_fund_iv`/`f_fund_ema_v1` 的面板。**INFERRED**, 未见逐字转录。
3. **2020-2021 面板段从未逐位核验。** `wf_results_all.json` L1744: v1 的 14,329 锚里有 **4,206 个(2020-01-31..2021-12-31)** 无任何现存 5m 缓存可对照; 定义仅由脚本副本 + 转录 INFERRED。只做过同配方一致性交叉核对(hist_v2 `Y4` == `wide_fea_hist_meta.npz` `y4`, 296,701 个 pre-2022 格逐位)。
4. **pod 与 jpline 的残差是两个变量, 未分离。** king 来源(2020 起 vs 2022 起)与面板血统(hist vs v2ext)仍纠缠。干净分离 = 固定面板只换 `SLOW_NPY`(`w10_universe.py` L85-88 支持该覆盖并断言形状一致)。
5. **Σ-简单不是交易所口径, Π(1+r)−1 才是。** 模型腿差 ≈0.1 bps/锚以内, **fund 腿高达 +0.27 bps/锚(t 至 3.9)**。重建前先定报哪一个。
6. **pod 上没有逐年 OOS king。** 全部 18 个 `slow_pred_hist_oos.npy` 都是指向 `slow_pred_pinned.npy` 的符号链接(`REVIEW_caliber_final_2026-09-04.md` §5 L179)。重造它 = `pod_slow_hist_folds.py`, 前置 = 2020 缓存。
7. **king 折方案无 embargo。** `pod_slow_hist_folds.py` L28 只做 `tr = YRA < YV`, 与 F10 训练器的 60 锚 embargo(`f10_train_pod...py` L21/L258)不一致。**认证重建 king 前需裁定是否补 embargo**(补了会改变数字, 属判据变更)。
8. **king 训练/服务错一根 bar 未量化**(§5.1)。
9. **2020-2021 没有任何模型分数。** `REVIEW` §5 L179 记 king `slow_pred_pinned.npy` 逐年有限占比 2022 0.0000 / 2023 0.0000 / 2024 0.3304 / 2025 0.4681 / 2026 0.4825; F10 `f10_V2MAIN_s42.npy` 2022 0.0000 / 2023 0.2260。⇒ 2022-23 的 pod 数字是纯 fund 书, 不是在役 combo 形态; 2020-21 在任何仪器上都 **UNAVAILABLE**, 除非重训覆盖。
10. **pod 侧参照桩是 144 字节占位符**, `LEGS=101` 还会绕过断言, 日志曾印「arm anchors 10038 vs ref 1」(`REVIEW` §4 C6 point 7)。pod2 必须补真参照并恢复该门。

---

## 9. 已由口径终审确立、**不要重做**的事项

来源: `docs/RESULT_caliber_revalidation_2026-09-04.md`, `docs/RESULT_caliber_truth_2026-09-04.md`, `docs/REVIEW_caliber_final_2026-09-04.md`, 以及 `.../kcurve_2026-08-21/` 三份 08-22 RESULT。

- **面板血统两族已闭环**(revalidation L79-83; REVIEW §1 L23, §2 表 L50-72, §8 rule 1 L424): `wide_dl*.npz` = 真对数(`build_wide_dl.py` L151), expm1 对它正确; pod 5m 族(`wide_panel_4h_v1/_v2ext/_v3splice`, `wide_fea_*_meta`, `dlw_targets::y4old`, bundle `leg_returns`, king 标签)= Σ 简单, expm1 对它是伪凸性。**口径绑定面板文件, 不绑定变量名。**
- **逐位验证已完成**(REVIEW §1 L23, §4 C1 L122-125): v2ext 3,427,554/3,427,554 格 max|Δ|=0; meta y4 3,446,599/3,446,599; 原始 kline 核对 float16(简单) 100% 命中, float16(对数) 只 26-51%。三个独立反驳者 3/3 存活。
- **缺陷进入时刻已定到秒**(REVIEW §3 L99, L103, L116): 2026-08-25T13:35:07Z, `w7_legweight_replay.py`(jpline only, 从未入 git), 传播 w7→w8→w10; 08-26 `a99bfc3` 泛化进 `CLAUDE.md` L28。
- **08-21/22 装置未被污染**(REVIEW §3 L116): `pod_stop_arms_v3.py` L38/L76、`pod_legweight_arms.py` L37/L85、`pod_kcurve.py` L54 全用原始 y4, 三票一致。
- **Σ-简单是有偏代理**(REVIEW §4 C6, L168): T-GT 原始 kline 恒等式给出 Π(1+r5)−1 vs `c_{N+4h}/c_N−1` max diff 1.15e-5, 而 Σr5 max diff 1.19e-3。
- **正确口径的单仪器全表已产出并三重复现**(REVIEW §5.1-§5.7): 固定席位 0.21/0/0.79 CAL=log 2024→26 **+0.4566 bps/锚, Sharpe 1.017, maxDD 2613.7 bps NAV**; 动态 msharpe **+0.6914, S 1.884**。单位链 `pod_units_table.py`: +0.4566 ÷0.791 = +0.5774/gross ×2190/100 = **+12.65%/gross/年 → +25.3% NAV @2×**。
- **执行时点衰减在书层只有 2-4%**(REVIEW §9 G6 L452), 不是腿层的 5-10%; 执行器读取时点是 **N+24** 不是 N+23(`config/book.json` L153/L163, 08-27 起)。
- **carry 差 +1.21 已闭环为窗内形态错配**(REVIEW §11.1), 非结构性。
- **08-22 三份 RESULT 仍然成立**: WA(独立路径, 宽书 d30 simple 2022-01→2026-06 net 1.785 bps/锚@gross2, Sharpe 1.668); WS(27 bps 缺口 = 一根 5m bar 时间戳偏移 + Jensen 项, **书层窗口偏移效应为零**, ΔS −0.009 [−0.035,+0.018]); SR(in-role 对数 → 简单: 1.063/1.42 → 0.272/0.37, 凸性 −0.825 = −70.1% 对数毛额, 全在空侧)。

**已作废、不得引用的数字**: revalidation L67 的 10 倍单位错族; revalidation L64 的 carry 修正; 「执行时点吃掉 5-10% alpha」; `RESULT_caliber_truth` L24 的 F10 装置偏差行(−1.54/−2.25/−3.29, 混入一根 bar 窗口差)与 L27 结论族; 2026-08-25T13:35:07Z 起全部 CAL=simple 的 w7/w8/w10 数字; `docs/AUDIT_live_vs_replay_2026-09-04.md` §3 整表; σ_fund 阶梯的采纳与撤回两份收据; `w10_universe.py` L325-334 的 nets_histv2 平价门。

---

## 10. 收据索引(本报告引用过的全部文件, 均 git-tracked)

**数据链**
- `multi_asset/exports/research/retrain_2026-09/pod_build_wide_ext.py`
- `multi_asset/exports/research/retrain_2026-09/pod_merge_cache_ext.py`
- `multi_asset/exports/research/retrain_2026-09/pod_panel_ext.py`
- `multi_asset/exports/research/retrain_2026-09/pod_fea_ext.py`
- `multi_asset/exports/research/retrain_2026-09/pod_dlw_targets_ext.py`
- `multi_asset/exports/research/retrain_2026-09/pod_dlw_features_ext.py`
- `multi_asset/exports/research/retrain_2026-09/pod_f8_build_ext.py`
- `multi_asset/exports/research/retrain_2026-09/pod_panel_splice.py`
- `multi_asset/exports/research/retrain_2026-09/pod_panel_lineage.py`
- `multi_asset/exports/research/retrain_2026-09/zload.py`
- `multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-21/pod_panel_wide_hist.py`
- `multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-21/pod_fea_wide_hist.py`
- `multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-21/run_hist_chain.sh`

**下载器**
- `multi_asset/exports/research/runpod_scripts/workspace_mirror/pod_hist_dl.py` ★
- `multi_asset/exports/research/runpod_scripts/workspace_mirror/pod_dl_klines.py`
- `multi_asset/exports/research/runpod_scripts/workspace_mirror/pod_dl_wide.py`
- `multi_asset/exports/research/runpod_scripts/workspace_mirror/pod_wide_multisrc_pull.py`
- `multi_asset/exports/research/retrain_2026-09/pod_fund_zips.py`
- `multi_asset/exports/research/retrain_2026-09/pod_extend_vision.py`
- `multi_asset/exports/research/retrain_2026-09/fund_pull_pod.py`

**模型**
- `multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-21/pod_slow_hist_folds.py` ★
- `multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-21/pod_slow_retrain_hist.py`
- `multi_asset/exports/research/retrain_2026-09/pod_export_bundle_v3.py`
- `eda/f10_train_pod_3fac6689d3f3c60f_2026-08-25.py` ★
- `multi_asset/exports/research/retrain_2026-09/pod_f10_train_ext.py`, `pod_f10_refit_ext.py`

**装置**
- `multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-21/pod_stop_arms_v3.py` ★
- `multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-21/w2_wide_replay.py`
- `multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-21/w2b_common.py`, `w2b_build_return_cube.py`, `w2b_offset_check.py`, `w2b_srccheck.py`
- `multi_asset/exports/research/retrain_2026-09/w10_universe.py`
- `eda/w10_ablation_replay_hardened_9f15dea0131f_2026-08-26.py`
- `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/combo_recheck/{pod_armA_vs_0821.py, pod_armA_vs_0821.out, commands_dev.txt, setup_pod.sh, w10_universe_port.py, w10_universe_recheck.py, nets_histv2_d30_pergross_ts_0821.npy, REPORT.md}`

**配置件**
- `multi_asset/exports/research/runpod_scripts/workspace_mirror/panel_symbols_wide.txt`(829)
- `multi_asset/exports/research/retrain_2026-09/live_pins.json`(450 / 78)
- `multi_asset/exports/research/retrain_2026-09/slow_scorer_v3base.json`
- `multi_asset/exports/research/retrain_2026-09/MANIFEST.md`(脚本清单 + 偏差 D1-D5)
- `multi_asset/exports/research/retrain_2026-09/BOOTSTRAP.sh`, `pod_run_chain.sh`, `pod_f10_inputs_chain.sh`

**对数族(对照)**
- `multi_asset/data/build_wide_dl.py` L95, L151
- `multi_asset/engine/panel_source.py` L11, L34
- `multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-22/wide_full_caliber_audit.py`, `wide_return_source_audit.py`

**文档**
- `docs/RESULT_caliber_revalidation_2026-09-04.md`, `docs/RESULT_caliber_truth_2026-09-04.md`, `docs/REVIEW_caliber_final_2026-09-04.md`
- `docs/ERROR_LEDGER_2026-08-20.md` E-0904-C/E/F/G, E-0905-A/B/C
- `docs/RUNBOOK_monthly_retrain_2026-09.md` / `_2026-10.md`
- `multi_asset/exports/research/retrain_2026-09/review_caliber_wf/wf_results_all.json`(L521, L630, L1353, L1607, L1608, L1611, L1696, L1741, L1744, L1745, L1807-1812)
- `multi_asset/exports/eda/kcurve_2026-08-21/RESULT_wide_full_caliber_audit_2026-08-22.md`, `RESULT_wide_return_source_2026-08-22.md`, `RESULT_inrole_simple_return_2026-08-22.md`
