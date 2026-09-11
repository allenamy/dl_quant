> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX (round 9, coverage) | **状态:** 一手测量, 未经独立复核 | **作废条件:** v4 链谱系变更; 或前沿越过 2026-09-10; 或 `w10_sleeve.py` sha 变更

# R9 — 关闭 E-0911-D 覆盖天花板: 重建 F10/V2MAIN 前向推理装置

**这是工程轮, 不是策略轮。** 目标: 让任何 `PHI>0` 的臂能被回放到 2026-08-30 20Z 之后。

口径锁 `CALIBER_PIN_v4_2026-09-11.md`(v4 链 2026-09-09)。上游 `RESULT_r6_coverage_extension_2026-09-11.md` §5 / §13.1 把这条退路的门写死在先: **重建的前向装置必须先逐位复现折自己的 `preds_fold/mE1cX7_202608.npz` 里的 `P` 才准用。**

---

## §0 一句话结论

| | |
|---|---|
| **GATE X-P(硬门, 逐位)** | **PASS**, `maxabs = 0.0`, NaN 图样逐位相同, 三个折全过(mwf_v4b s42 / mwf_v4b s2027 / mwf s42) |
| **GATE X-OVERLAP(谱系正确形)** | **PASS**, `maxabs = 0.0`, 在役 `f10_v4RAW_s{42,2027}.npy` 的 186 个锚逐位 |
| **GATE X-OVERLAP(任务字面形, 对 `f10_A0`)** | **FAIL**, `maxabs 0.3849 / 0.3922`, ρ 0.842 / 0.831 —— **按构造不可能过**, 见 §3 |
| **新回放上界** | `2026-08-30 20:00Z` → **`2026-09-10 00:00Z`**(n 9138 → **9199**, +61 锚) |
| **A0 在钉死窗上一手复现** | n=9138, mean g **+0.6342**, Sharpe **1.2912**, CI95 **[+0.1653, +1.1071]** —— 与钉死数字**逐位相同** |
| **延展后的计划数字** | A1x 新窗 n=9199: **+0.6602 / +0.6828** bps/锚, Sharpe **1.2857 / 1.3288**(双种子) |
| **结论是否改变** | **否。** 关掉覆盖缺口没有把计划数字挪动到统计上可分辨的程度; 离 3.0 的差距一格未动。 |

---

## §1 装置: 它是什么, 为什么这样建

v4 的月度 walk-forward 训练器 `/workspace/review_scratch/pod_f10_train_monthly_v4.py`(`self_sha256 2147a7dd128be180…`)每折只存两样东西:

- `models/mE1cX7_<YM>.pt` —— **裸 state_dict**, keys 实测 `['a','f.0.bias','f.0.weight','f.3.bias','f.3.weight','f.6.bias','f.6.weight']`, **没有 mu/sd**;
- `preds_fold/mE1cX7_<YM>.npz` —— 该折模型对 **first_te 之后每一个锚**的原始分数 `P`(训练器 L416-424 的诊断块)。

所以前向装置唯一缺的是**逐折标准化**。它不是失传的: 训练器 L317-L328 的标定是**完全确定性**的函数 —— 折的训练锚集 → `tr1 = tr_idx[:int(0.85·len)]` → `rowsel = concat(arange(ST[i],ST[i+1]) for i in tr1[::7])` → `mu/sd = nan_to_num(XT[rowsel[::3]]).mean(0)/std(0)+1e-6`。本轮把这段**逐字抄**进装置重算, 再把训练器 L423-L424 的打分行**逐字抄**过来, 于是服务端与训练端逐算子同序(E-0826 族)。

**装置**: `devices/r9_extend2.py`(`sha256 6bc095ef3baebb75…`)。先导版 `devices/r9_device.py`(`f0b831f6df41de3d…`)只跑 X-P。

**折的身份先被断言, 再被使用**(CLAUDE.md 规则 6 —— 工件当输入前先开产它的代码, 且逐个哈希 REQUIRED_INPUT):

```
targets_sha256 d1976cf6246cdc25…  == fold config
fea82_sha256   40608701cad1aea1…  == fold config
fea89_sha256   f7363889fa823a97…  == fold config
trainer sha256 2147a7dd128be180…  == fold config self_sha256
torch 2.11.0+cu128, GPU "NVIDIA RTX PRO 4500 Blackwell"  == fold config
重建的折: n_train 10025 / n_val 1504 / n_test 186 / cutoff 2026-07-31 20:00 / max_train_label_end 2026-07-31 20:00
          —— 5 项逐个与折自己的 config 相等(断言, 不是比对后人工看)
```

---

## §2 GATE X-P —— 硬门, 逐位, **PASS**

重新推理折自己的测试片(锚 10026..10211 = 2026-08-01 00Z..2026-08-31 20Z)。

| 折 | ckpt sha16 | legs sha16 | `maxabs` | NaN 图样 | 逐位 | 判决 |
|---|---|---|---|---|---|---|
| `mwf_v4b/RAW_s42/shard3` (**在役谱系**) | `7859072d24db` | `c535decd6524` | **0.0** | 相同 | 是 | **PASS** |
| `mwf_v4b/RAW_s2027/shard3` (**在役谱系**) | `fbd1ff28e1aa` | `c535decd6524` | **0.0** | 相同 | 是 | **PASS** |
| `mwf/RAW_s42/shard3` (被取代) | `efd5c1c420b1` | `561fc1475bfd` | **0.0** | 相同 | 是 | **PASS** |

74,400 个双侧有限单元, 0 个单侧有限。s42 的 `P` 字节 sha16 `20a2c0d349965596` 两边相同。

**★ 一处差点踩进去的坑(E-0825-G/H)。** `preds_fold/mE1cX7_202608.npz` 在 pod2 上有**两棵树**: `/workspace/f8_v4/mwf/` 与 `/workspace/f8_v4/mwf_v4b/`。名字看不出哪棵是正典。打开 `merge_mwf_v4b.py` 的收据才知道: 在役回放数组 `f10_v4RAW_s42.npy`(盘上 sha16 `58d64a6ff9684589`)来自 **mwf_v4b** 的 merge(`merge.json` splice sha `58d64a6ff9684589`), 不是 mwf(`d7d38b76b23f7027`)。两棵树的唯一差别是训练时读的 legs 文件(`561fc1475bfd` vs `c535decd6524` = 在役 `/workspace/f8_v4/data/f10v2_legs.npz`; 前者的残迹叫 `/workspace/f8_v4/models/bad_legs_20260909`)。**三棵都过了门**, 但只有 mwf_v4b 那两个被用来产延展。

**GATE X-OVERLAP-B(谱系正确形)**: 重新推理出的 `P` 与**在役数组** `f10_v4RAW_s{42,2027}.npy` 在 186 个锚上 `maxabs = 0.0`, NaN 图样相同, 逐位相等。这独立验了 merge 步没有改动 `P`。

---

## §3 GATE X-OVERLAP(任务字面形)—— **FAIL**, 且**按构造不可能过**

任务要求"与归档的 `f10_A0_s{42,2027}.npy` 逐位相符"。实测 **FAIL**: `maxabs 0.3849`(s42)/ `0.3922`(s2027), Pearson `0.842 / 0.831`。

**这不是装置的问题, 是两条不同谱系。** 逐条受据(`receipts/lineage_A0.json`, `receipts/recon.json`):

1. `build_dev_v4.py` 明文写着 `f10_A0` 的来源: `EX = np.load("/workspace/dlw_ext/data/dlw_targets.npz")["E_ts"]; Y = np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{s}.npy")`, 按 E_ts 对齐到 v4 轴。
2. 那批预测由 **`/workspace/pod_f10_train_ext.py`(年度四折 walk-forward, embargo 60, 折 = 2023/2024/2025/2026)** 产出, 读的是 `dlw_ext`: `targets_sha256 31d043e8f160a1d4…`, 轴 **10206**, 末锚 **2026-08-30 20:00Z**, `cache_sha256 72eb784949e90a09…`。
   → **`_ext` 缓存正是口径锁 §2 明令禁用的谱系**(E-0909-A 回绕 / 未经 holefix2)。
3. **该训练器从不保存任何逐折模型。** 实测 `/workspace/f8_ext/models/` 只有 `f10_live_s{42,2027}.pt`(+np 导出), 那是 `pod_f10_refit_ext.py` 的**全史重训件**, 而 `w10_sleeve.py` L110 的注释自己写着"**全史重训件不参与任何历史评估 —— 它见过全部历史**"。
   → **`f10_A0` 的 2026 折权重在盘上不存在。任何装置都不可能逐位复现它, 除非重训。**

**因此 E-0911-D 的真面目是**: 一条 **v3 谱系的工件漏进了 v4 回放树**, 它的轴比 v4 轴短 6 个锚, 于是 `w10_sleeve.py` L267 的 `np.nan_to_num` 把 2026-08-31 之后的 F10 腿静默变成 0。在 v4 口径下, DL 腿的正确工件本来就是 `f10_v4RAW`(月度 WF, v4 数据链), 它已经覆盖到 2026-08-31 20Z, 现在被本轮的装置推到 **2026-09-10 20Z**。

> A0 与 A1 不是同一本书, 但差别是被量过的: 本轮一手配对读数 **A1 − A0 = +0.0562 [−0.0778, +0.1894](s42) / +0.0554 [−0.0801, +0.1886](s2027)**, ρ = 0.953, CI 含零 ⇒ **UNDECIDED**, 与 `CALIBER_PIN_v4` §4 记的 `+0.061 [−0.168,+0.287]` 同号同量级。

---

## §4 ★ 新缺陷 E-0911-D 其实是**两头**的, 不是一头 —— 这是本轮的新发现

前几轮只记了右端截断。本轮量了左端(`receipts/RECEIPT_r9_addendum.json`):

**在被钉死的 A0 计划数字那 9,138 个锚里, 有 1,110 个(12.15%)的 F10 腿是静默为零的。**

| | |
|---|---|
| 死锚区间 | **`2022-06-30 00:00Z` .. `2022-12-31 20:00Z`**, 是窗的**连续前缀**(实测 `dead_contiguous_prefix: true`) |
| 逐年 | 2022: **1110/1110 全死**; 2023: 0/2190; 2024: 0/2196; 2025: 0/2190; 2026: 0/1452 |
| 机制 | F10 的第一折测试片从 2023-01-01 开始, 2022 整段没有 OOS 预测 ⇒ `F10P` 全 NaN ⇒ `w10_sleeve.py` L267 `np.nan_to_num(xz(F10P[i,m]))` **= 0**, 没有任何旗标 |
| 后果 | 那 1,110 个锚上"77% funding + 13% king + 10% V2MAIN"的三腿书**不是那本书**: F10 链的第一项恒为 0, `w3[0]` 压在空信号上 |
| 量级 | 死锚段 mean g **+0.1586**; 活锚段 mean g **+0.7000**; 只用活锚的 Sharpe **1.3741**(vs 全窗 1.2912) |

**这不是本轮造成的, 是对 incumbent 的勘误。** 它也说明 `LOOK=900` 的 post-warm 规则**没有**覆盖这个洞 —— warm-up 900 个锚结束于 2022-06-30, F10 的第一折要到 2022-12-31 之后才开始。

---

## §5 GATE X-PRE —— 严格形 **FAIL**, 分解后三个子门全 PASS; 失败处**恰好**是已知的 E-0911-B

要把装置向前跑, 用的是 r6 的延展特征矩阵。我加了一道 r6 没有的门: **延展特征矩阵必须是 incumbent 的逐位前缀延展**。

**严格形 FAIL**: `X_prefix_maxabs = 0.0115966796875`。这一门**按设计让第一版脚本 `r9_extend.py` 直接停在那里, 没有产出任何延展**(`receipts/extend.log` 末行 `GATE X-PRE FAILED — STOP.`)。

诊断(`receipts/GATE_X_PRE_diag.json`, 装置 `devices/r9_prediag.py`), **明细逐项打出来, 可独立验算**(r6 §11 的教训: 断言不会检验出定义它自己范围的那个常量错了, 抓住这类错的是门打出明细):

| | |
|---|---|
| 差异单元 | **3,866** / 2,753,289×171 |
| 触及列 | **只有 2 列**: `fund_ema`(col 80, 2000 格, maxabs 0.00277)、`fund_now`(col 81, 1866 格, maxabs 0.01160) |
| 触及锚 | **恰好 5 个**: `2026-08-31 04/08/12/16/20Z`(idx 10207..10211) |
| 算术核对 | 5 锚 × 400 成员 × 2 列 = **4000** 上界; 实际 3866; 差 **134** = 延展侧本来就恰好为 0.0 的格 |
| `fea89` | **0 个差异**, 逐位相同 |
| NaN 图样 | 0 处不同 |

**机制(开源码读出来的, 不是推断)**: `/workspace/pod_dlw_features_ext.py` L93
```python
j = pw_row.get(int(E_ts[i]))
if j is None: n_nofund += 1
for fv in FUND:
    X[sl, col] = 0.0 if j is None else np.nan_to_num(fv[j, m], nan=0.0); col += 1
```
面板没有该锚的行时, **两列 funding 被硬写 0.0, 无旗标**。incumbent 的 v3splice 面板止于 `2026-08-31 00:00Z`, 而 DL 轴到 `2026-08-31 20:00Z` ⇒ 最后 5 个锚的 `fund_ema/fund_now` 对**全部 400 个成员**都是 0.0。r6 的延展面板(到 2026-09-10 00Z)有这些行, 所以延展侧是真值。

> **这是 E-0911-B 的第三张脸。** r6 记了它在 king 特征张量(`fund_ema` 0/400 有限)和腿产物(WL 塌回 [1/3,1/3,1/3])上的样子; **本轮第一次记它在 DL 特征 `fea82` 上的样子**, 且机制是不同的一行代码(king 侧是 NaN, DL 侧是硬 0.0)。差异是**修复**, 不是新缺陷。

**分解后的三个子门(全 PASS)**, 它们才是这台装置真正依赖的:

| 子门 | 内容 | 读数 | 判决 |
|---|---|---|---|
| X-PRE/exempt | 每一个差异单元都落在**事先声明**的 E-0911-B 集合内(5 锚 × {fund_ema, fund_now}) | `matches_declared_E0911B: true` | **PASS** |
| X-PRE/calib | mu/sd 取样的 98,963 行逐位相同(最大行号 2,076,486, 远在 2026-08 之前) | `bitwise_equal: true` | **PASS** |
| X-PRE/disjoint | 装置前向读的行 `[2753289, 2777289)` 与差异行 `[…, 2753288]` **不相交**; 标定行也与差异行不相交 | 两项皆 true | **PASS** |

外加: 在延展矩阵上**重算** mu/sd, 与 incumbent 的 mu/sd **逐位相等**(`torch.equal` 两项)。
→ **本轮产出的延展工件在数学上与那 3,866 个格无关**: incumbent 行是逐位拷贝, 新锚是全新行, mu/sd 逐位相同。

---

## §6 延展产物

| 产物 | 形状 / 轴 | sha256 | 说明 |
|---|---|---|---|
| `out/f10_v4RAWx_s42.npy` | (10272, 829), 末锚 **2026-09-10 20:00Z** | `d41fcc933dfe3033…` | 前 10212 行 = 在役 `f10_v4RAW_s42.npy` **逐位拷贝**(已断言); 后 60 行 = 202608 折前向 |
| `out/f10_v4RAWx_s2027.npy` | 同 | `01180436a573fef2…` | 同 |
| `out/mu_202608.npy` / `sd_202608.npy` | (171,) | — | 门验过的逐折标定, 落盘备复现 |

- **60 个新锚全部打分成功**(无一被 `<50 成员` 规则跳过), 每锚有限成员数中位 **300**。
- **没有任何插值**: 装置真产不出来的锚一律 NaN(本轮为空集), 洞在产物里看得见。
- 打分折 = `mE1cX7_202608`, `cutoff 2026-07-31 20:00Z`, embargo 1 ⇒ **对每一个新锚都是因果的**, 但**比月度规则陈旧一个月**(2026-09 需要 202609 折 = 重训, 本轮不做)。这是这批分数最大的局限, 见 §8。

### §6.1 `repair5` 变体 —— **需要用户裁定, 本轮不替用户选**

既然延展面板补齐了 08-31 那 5 个锚的 funding, 那 5 个**既有**锚的 DL 分数也可以重打:

| 产物 | sha256 | 改了什么 |
|---|---|---|
| `out/f10_v4RAWx_repair5_s42.npy` | `6eb8a757eed33328…` | 只改 `2026-08-31 04/08/12/16/20Z` 五行(2000 格, maxabs 0.0618), 其余行逐位不变(已断言) |
| `out/f10_v4RAWx_repair5_s2027.npy` | `e3a9bf17f8ddebd4…` | 同(maxabs 0.0940) |

**改既有行 = 书行为口径 ⇒ 按铁律必须用户裁定。** 与 r6 的 `f10v2_legs_x0910_repair5.npz` 是同一类选择, 应一起裁。**本文 §7 的全部数字用的是未修复的主产物。**

---

## §7 延展后的读数

### §7.1 装置回归: 延展回放必须逐位复现 incumbent 回放

**GATE X-REPLAY-PREFIX: PASS。** 延展树上的回放, 前 10,039 个面板锚 × **23 列全部** `maxabs = 0.0`, ts 逐位相同, 两个种子都是。配对读数 `A1x_ext − A1_inc` 在旧窗上 `mean_delta = 0.0`, `CI95 [0.0, 0.0]`, `corr = 1.0`。
→ 延展是**纯前缀延展**, 没有扰动任何历史锚。

### §7.2 A0 钉死数字, 一手复现(验我方测量栈)

口径: `g = net_ex/gross_total` bps/锚/单位 gross; post-warm 丢 900(E-0911-A); 截 2026-08-30 20Z(E-0911-D); 拟合成本 `r3k/costb_PWR_G230k.json`(`295b4e7b462373e4…`, K=0.17, α=0.87); 装置 `w10_sleeve.py` **`b88e35a46b93d712…`**。

| 臂 | n | mean g | Sharpe | CI95 (B=4000, rng[20260912,31]) | CI95 (B=2000, rng[20260905,1]) |
|---|---|---|---|---|---|
| **A0 归档 s42(钉死数)** | **9138** | **+0.6342** | **1.2912** | **[+0.1653, +1.1071]** | [+0.1774, +1.1136] |
| A0 归档 s2027 | 9138 | +0.6579 | 1.3299 | [+0.1800, +1.1390] | [+0.1959, +1.1445] |

**逐位复现了钉死的 +0.6342 / [+0.1653, +1.1071] / 1.2912 / n=9138。** 测量栈可信。

### §7.3 旧窗 vs 新窗

| 臂 | 窗 | n | mean g | Sharpe | CI95 (B=2000, rng[20260905,1]) |
|---|---|---|---|---|---|
| A0 归档 s42 | post-warm → 08-30 20Z | 9138 | +0.6342 | 1.2912 | [+0.1774, +1.1136] |
| A1 incumbent s42 | post-warm → 08-30 20Z | 9138 | +0.6904 | 1.3474 | [+0.1966, +1.1912] |
| A1 incumbent s2027 | post-warm → 08-30 20Z | 9138 | +0.7133 | 1.3906 | [+0.2242, +1.2060] |
| **A1x 延展 s42** | **post-warm → 09-10 00Z** | **9199** | **+0.6602** | **1.2857** | **[+0.1673, +1.1472]** |
| **A1x 延展 s2027** | **post-warm → 09-10 00Z** | **9199** | **+0.6828** | **1.3288** | **[+0.1911, +1.1717]** |

**没有一格翻。** 新增 61 个锚(+0.67% 样本)把 Sharpe 从 1.347 / 1.391 拉到 1.286 / 1.329, 挪动 ≈ 0.06, 远小于 CI 宽度(≈0.98 bps/锚)。**离"跨 regime Sharpe 显著高于 3.0"仍差 ~2.6 个 Sharpe; 本轮是仪器修复, 不是策略结果。**

### §7.4 新覆盖的 61 个锚本身(2026-08-31 00Z .. 2026-09-10 00Z)

| 种子 | n | mean g | Sharpe(该片) | CI95 (B=2000) | 换手 | gross_total |
|---|---|---|---|---|---|---|
| s42 | 61 | **−3.8739** | −5.95 | [−12.19, +3.53] | 0.02684 | 0.8042 |
| s2027 | 61 | **−3.8869** | −6.13 | [−12.02, +3.19] | 0.02402…0.02728 | 0.8040 |

逐日(s42): 09-01 **+8.25** · 09-02 **+12.35** · 09-03 −0.33 · 09-04 −6.43 · 09-05 **+14.07** · 09-06 **−29.42** · 09-07 −2.17 · 09-08 −11.08 · 09-09 −13.75 · 09-10 **−32.87**。

**读法纪律**: n=61, CI 含零 ⇒ **这不是一个 regime 结论**, 只是"新窗覆盖到的这段是负的"。
两条值得记的观察(观察, 非主张):
- 09-06 的 −29.4 与实盘那天的首次单日止损(memory `live_stop_loss_2026_09_06_resume_and_flowday`)方向一致 —— 但**回放 ≠ 实盘书**(`engine_replay_is_not_the_live_book`), 不作对账用。
- **对照臂 PHI=0(完全去掉 DL 腿)在同 61 锚上是 −4.2649 / Sharpe −7.27, 比带 DL 腿的 −3.8739 更差。** 所以这段的负不是"折陈旧一个月"造成的; 陈旧的 DL 腿在这 61 个锚上**帮了 +0.39 bps/锚**。(`receipts/RECEIPT_r9_control_phi0.json`)

---

## §8 本轮**没有**做到什么

1. **`f10_A0` 本身没有被延展, 也不可能被延展**(§3): 它的年度折权重从未落盘。要它就必须重训 = 另一个预注册。
2. **A0 的 king 腿同样不可延展**: A0 用 `SLOW_v3_on_v4axis.npy`(v3 booster 对齐到 v4 轴), r6 只建了 v4 的延展 king(`SLOW_v4_x0910`)。所以 **A0 的两条模型腿都是 v3 谱系工件**, 在 v4 口径下本就该被 A1 取代。
3. **打分折陈旧一个月**: 2026-09 按月度 WF 规则需要 202609 折。本轮用 202608 折前向(因果成立, cutoff 2026-07-31 20:00)。§7.4 的 PHI=0 对照说明这不是那段亏损的成因, 但它仍是**这批分数的已知偏差**, 任何用它做判决的人必须写进局限。
4. **末端 5 个锚(2026-09-10 04Z..20Z)不进任何窗**(r6 §13.3 的结构性面板/king 错位), 新上界因此是 **2026-09-10 00:00Z** 而不是 20:00Z。
5. **没有做判官 `judge_v4.py` 的正式裁定**: 本轮用的是 r8 的同口径估计器, 判官与 `ELIGIBILITY_CONTRACT.json` **一个字节没碰**。判决窗是否前移仍是**用户裁定**(r6 §0 的 (a) 类缺口)。
6. **§4 的 1,110 个 F10 死锚没有被修**。修它需要给 2022 造 OOS 分数 = 重训, 本轮禁止。**但所有历史读数都该带上这条勘误。**

---

## §9 ENV 白名单(E-0826-D)

**分析/门装置**(`r9_recon.py` `r9_device.py` `r9_extend.py` `r9_extend2.py` `r9_prediag.py` `r9_lineage.py` `r9_judge.py` `r9_adden.py`): **白名单 = 空集**, 每个脚本里显式 `READ_ENV = []` 并断言, 另断言训练器/回放器的全部旋钮**未泄漏进进程环境**(`ARM V2 SEED COST LDD AFIX LDC CTXA REC PLE EPOCHS LR NCOL EXTRA LPP F10_DLW F10_OUT MWF_OUT EMBARGO MWF_TAG MONTHS FORCE BEST_EP_FLOOR BEST_EP_FIX F10_GATE_JSON MWF_ROOT PHI LOOK FPRED FSEED LEGS CAL SLOW_NPY F171_PANEL`)。全部路径与常数是脚本内字面量, `CONFIG` 与脚本自身 `sha256` 写进产物。

**回放子进程**(`r9_replay.py` / `r9_ctrl.py` → `w10_sleeve.py`): 白名单 = 恰好 14 项, 逐条断言在**有效字符串**上, 白名单外的键直接 `assert` 失败:
```
LEGS CAL WRULE LOOK MEMBERS_TOPN FTRIM PHI UMASK_SCOPE UMASK_NPZ SLOW_NPY FSEED FPRED COSTB_JSON OUT_TAG
```
有效值(A1 臂):
```
LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1
UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz
COSTB_JSON=/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json
SLOW_NPY=<SLOW_v4.npy | SLOW_v4_x0910.npy>  FSEED=<42|2027>  FPRED=<f10_v4RAW_s*.npy | f10_v4RAWx_s*.npy>
```
父进程另把这 14 项 + 全部 `TILT*` + `W3FIX SEATF10 KMOD KTAIL KMOD_F10 KMOD_AGREE SEATNET FUNDSCALE FEMAT_NPZ TRADE_TOPN REF_SKIP RNSM FTPOS LTRIM_TH CDAMP FTRIM_TH SLEEVE` 从子环境里 **pop 掉**再重设, 免得继承污染。
`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=3`(仅性能, 不进口径)。

**本轮没有训练任何东西**, 所以不适用 V2 类训练旗标(那正是曾经漏 `V2=1` 训出 −0.219 Sharpe 的那个洞)。

---

## §10 安全 / GPU

- **`~/dl_quant_live` 与 `~/wide_shadow` 一个字节没碰**, 没重启任何进程, 没调任何交易所 API, 没下任何单。
- **没有修改 r6 的任何产物**: 回放树是本轮新建的 `r9/dev_inc` 与 `r9/dev_ext`(全是符号链接), r6 的 `dev_v4_x0910` 原样未动。`judge_v4.py` / `ELIGIBILITY_CONTRACT.json` 未改。
- **GPU**: 开工前实测 `nvidia-smi --query-compute-apps` **无任何计算进程**(0%, 2 MiB), 独立研究员当时在跑的 4 个作业(`collect_oi.py` / `sample_visibility.py` / 两个 launcher)**全是 CPU 数据采集**。本轮 GPU 用量 = 2 次前向推理, 各 ~30 秒。**没有排队等待, 没有 kill, 没有 pkill, 没有抢占。** 收工后复查: GPU 仍 0% / 2 MiB, 那 4 个作业**全部仍在运行**(etime 连续)。

---

## §11 收据

| 文件 | 内容 |
|---|---|
| `receipts/RECEIPT_r9_gates.json` | X-P × 3 折 / X-OVERLAP-B / X-PRE 四子门 + 豁免明细 / 延展 / repair5 / X-OVERLAP-A |
| `receipts/RECEIPT_r9_gateXP.json` | 先导 X-P(mwf s42)独立一跑 |
| `receipts/GATE_X_PRE_diag.json` | X-PRE 失败的逐列逐锚诊断 |
| `receipts/RECEIPT_r9_judge.json` | X-COV / X-REPLAY-PREFIX / 全部窗读数 / 配对 delta |
| `receipts/RECEIPT_r9_addendum.json` | 1,110 个 F10 死锚的取证 + 61 个新锚逐日 |
| `receipts/RECEIPT_r9_control_phi0.json` | PHI=0 对照 |
| `receipts/RECEIPT_r9_replay_runs.json` | 回放树链接表 + env 白名单 + 每跑 rc/wall |
| `receipts/lineage_A0.json` `receipts/recon.json` | f10_A0 谱系取证 / 轴与 sha 清单 |
| `receipts/*.log` | 每一步的原始 stdout |
| `devices/*.py` + `SHA256SUMS_devices.txt` | 全部装置源码与 sha256 |
| pod2 产物 | `/workspace/uplift_2026-09-11/r9/out/` (`f10_v4RAWx_s{42,2027}.npy`, `repair5`, `mu/sd_202608.npy`) |

## §12 数字标签

§2 / §3 / §4 / §5 / §6 / §7 全部 **VERIFIED**(本会话在 pod2 上跑出, 每个数字能指到上表的某个收据文件与日志行)。§3 关于"v3 谱系被禁用"的定性引自 `CALIBER_PIN_v4_2026-09-11.md` §2 ⇒ 对本轮为 **INFERRED**。§8.4 的"末端 5 锚结构性错位"引自 r6 §13.3 ⇒ **INFERRED**(本轮未独立复跑该机制)。
